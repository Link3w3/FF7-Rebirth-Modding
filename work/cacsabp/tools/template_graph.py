"""A decoded AnimBlueprint (abpgraph.py's JSON) as a template the editor's AnimBlueprint builder (RebirthSkelCompat
editor 1.19, EndAnimBlueprintTemplate.cpp) makes an editable AnimBlueprint from: the AnimGraph's nodes and pose links,
each state machine's states (their graphs), conduits and transitions with their rules as expression trees that name
states, the pin bindings and the class defaults.

The game's Control Rig node is left out (its rig is one of the game's own Control Rig blueprints, which the editor
cannot make), and the space conversion pair it leaves behind (to component space straight back to local space, or the
reverse) is taken out too.

    template_graph.py <decoded graph .json> <out template .json> [--name NAME]
"""
import json, re, sys

VERSION = 1
SKIP = {'AnimNode_ControlRig'}
L2C, C2L = 'AnimNode_ConvertLocalToComponentSpace', 'AnimNode_ConvertComponentToLocalSpace'
# node members the compiler or the running game sets, never the AnimBlueprint's author
RUNTIME = {
    '*': {'BlendWeight', 'InternalTimeAccumulator', 'ActualAlpha', 'PreviousBlendSpace', 'bInitialized'},
    'AnimNode_StateMachine': {'StateMachineIndexInClass'},
    'AnimNode_Root': {'Name', 'Group'},
    'AnimNode_StateResult': {'Name', 'Group'},
}
SUPPORTED_CALLS = {
    ('KismetMathLibrary', 'EqualEqual_ByteByte'), ('KismetMathLibrary', 'NotEqual_ByteByte'),
    ('KismetMathLibrary', 'Less_FloatFloat'), ('KismetMathLibrary', 'Greater_FloatFloat'),
    ('KismetMathLibrary', 'LessEqual_FloatFloat'), ('KismetMathLibrary', 'GreaterEqual_FloatFloat'),
    ('KismetMathLibrary', 'EqualEqual_FloatFloat'), ('KismetMathLibrary', 'NotEqual_FloatFloat'),
    ('KismetMathLibrary', 'BooleanAND'), ('KismetMathLibrary', 'BooleanOR'), ('KismetMathLibrary', 'BooleanXOR'),
    ('KismetMathLibrary', 'BooleanNAND'), ('KismetMathLibrary', 'BooleanNOR'), ('KismetMathLibrary', 'Not_PreBool'),
    ('KismetMathLibrary', 'SelectFloat'), ('KismetMathLibrary', 'SelectInt'),
    ('KismetMathLibrary', 'EqualEqual_IntInt'), ('KismetMathLibrary', 'NotEqual_IntInt'),
    ('KismetMathLibrary', 'Less_IntInt'), ('KismetMathLibrary', 'Greater_IntInt'),
    ('KismetMathLibrary', 'EqualEqual_BoolBool'), ('KismetMathLibrary', 'NotEqual_BoolBool'),
}
TIME_GETTERS = {'GetRelevantAnimTimeRemaining', 'GetRelevantAnimTimeRemainingFraction', 'GetRelevantAnimTimeFraction',
                'GetRelevantAnimLength', 'GetRelevantAnimTime'}


def node_class(name):
    return re.sub(r'_\d+$', '', name)


class Template:
    def __init__(self, g):
        self.g = g
        self.N = g['nodes']
        self.problems = list(g.get('problems', []))
        self.notes = []

    # --- pose links, with the left-out nodes passed through
    def through(self, i, seen=None):
        seen = seen or set()
        while i is not None and 0 <= i < len(self.N) and self.N[i]['struct'] in SKIP:
            if i in seen:
                return None
            seen.add(i)
            src = self.N[i]['links'].get('Source')
            note = '%s (%s) is left out: its input goes straight on' % (self.N[i]['name'], self.N[i]['struct'])
            if note not in self.notes:
                self.notes.append(note)
            i = src
        return i

    def link(self, i):
        """The node a pose link to node i really comes from: left-out nodes and conversion pairs passed through."""
        for _ in range(64):
            i = self.through(i)
            if i is None or i < 0 or i >= len(self.N):
                return None
            n = self.N[i]
            if n['struct'] == L2C:
                inner = self.through(n['links'].get('LocalPose'))
                if inner is not None and 0 <= inner < len(self.N) and self.N[inner]['struct'] == C2L:
                    note = '%s and %s (a conversion pair the left-out node leaves) are taken out' % (n['name'], self.N[inner]['name'])
                    if note not in self.notes:
                        self.notes.append(note)
                    i = self.N[inner]['links'].get('ComponentPose')
                    continue
            if n['struct'] == C2L:
                inner = self.through(n['links'].get('ComponentPose'))
                if inner is not None and 0 <= inner < len(self.N) and self.N[inner]['struct'] == L2C:
                    note = '%s and %s (a conversion pair the left-out node leaves) are taken out' % (n['name'], self.N[inner]['name'])
                    if note not in self.notes:
                        self.notes.append(note)
                    i = self.N[inner]['links'].get('LocalPose')
                    continue
            return i
        return None

    def node(self, i):
        n = self.N[i]
        skip = RUNTIME['*'] | RUNTIME.get(n['struct'], set())
        values = {k: v for k, v in n['values'].items() if k not in skip}
        links = {}
        for pin, child in n['links'].items():
            c = self.link(child) if child is not None and child >= 0 else None
            if c is not None:
                links[pin] = self.N[c]['name']
        return dict(id=n['name'], cls=node_class(n['name']), struct=n['struct'], values=values, links=links)

    def subgraph(self, start):
        """The nodes a pose link chain from node `start` reaches (state machines end it: their states are their own)."""
        order, seen, todo = [], set(), [start]
        while todo:
            i = todo.pop(0)
            if i is None or i in seen:
                continue
            seen.add(i)
            order.append(i)
            if self.N[i]['struct'] == 'AnimNode_StateMachine':
                continue
            for child in self.N[i]['links'].values():
                c = self.link(child) if child is not None and child >= 0 else None
                if c is not None and c not in seen:
                    todo.append(c)
        return order

    # --- rule expressions
    def expr(self, t, machine, where):
        if t is None:
            return None
        op = t.get('op')
        if op == 'const':
            v = t['value']
            if t['type'] == 'bool':
                return dict(op='const', type='bool', value=bool(v))
            if t['type'] in ('int', 'byte'):
                return dict(op='const', type=t['type'], value=int(v))
            if t['type'] == 'float':
                return dict(op='const', type='float', value=float(v))
            return dict(op='const', type=t['type'], value=v)
        if op == 'var':
            return dict(op='var', name=t['name'])
        if op == 'call':
            key = (t['cls'], t['func'])
            if t['cls'] not in ('self', 'EndCharacterAnimInstance', 'AnimInstance') and key not in SUPPORTED_CALLS:
                self.problems.append('%s: the call %s.%s is not one the builder makes' % (where, t['cls'], t['func']))
            cls = 'self' if t['cls'] in ('self', 'EndCharacterAnimInstance', 'AnimInstance') else t['cls']
            return dict(op='call', cls=cls, func=t['func'], args=[self.expr(a, machine, where) for a in t['args']])
        if op == 'time':
            if t['func'] not in TIME_GETTERS:
                self.problems.append('%s: the getter %s is not one the builder makes' % (where, t['func']))
            states = machine['states']
            idx = t['state']
            state = states[idx]['name'] if isinstance(idx, int) and 0 <= idx < len(states) else None
            if state is None:
                self.problems.append('%s: %s names state %r, which the machine does not have' % (where, t['func'], idx))
            if t.get('machine_node') is not None and t['machine_node'] != machine.get('node'):
                self.problems.append('%s: %s asks about another state machine (node %s)' % (where, t['func'], t['machine_node']))
            return dict(op='time', func=t['func'], state=state)
        if op == 'select':
            options = []
            for value, x in t['options']:
                if value.get('op') != 'const':
                    self.problems.append('%s: a select option with a value that is not a constant' % where)
                    continue
                options.append([int(value['value']), self.expr(x, machine, where)])
            return dict(op='select', index=self.expr(t['index'], machine, where), options=options)
        if op == 'cast':
            return dict(op='cast', kind=t['kind'], value=self.expr(t['value'], machine, where))
        self.problems.append('%s: a rule part the builder cannot make: %s' % (where, json.dumps(t)[:200]))
        return dict(op='const', type='bool', value=False)

    # --- the whole template
    def build(self, name=None):
        g = self.g
        root = self.N[0]
        assert root['struct'] == 'AnimNode_Root', root
        main_ids = self.subgraph(self.link(root['links'].get('Result')))
        bindings = g.get('bindings', [])
        by_node = {}
        for b in bindings:
            by_node.setdefault(b['node'], []).append(dict(pin=b['pin'], var=b['source']))
        used = set()

        def graph(ids):
            nodes = []
            for i in ids:
                nd = self.node(i)
                nd['bindings'] = by_node.get(nd['id'], [])
                used.add(nd['id'])
                nodes.append(nd)
            return nodes
        main = graph(main_ids)
        machines = []
        for m in g['machines']:
            mnode = self.N[m['node']]['name']
            states, transitions = [], []
            names = [s['name'] for s in m['states']]
            for si, s in enumerate(m['states']):
                where = '%s/%s' % (m['name'], s['name'])
                notify = g.get('notifies') or []

                def notify_name(k):
                    return notify[k]['NotifyName'] if isinstance(k, int) and 0 <= k < len(notify) else None
                st = dict(name=s['name'], conduit=s['conduit'], reset_on_entry=s['reset_on_entry'],
                          entered=notify_name(s['notifies'][0]), left=notify_name(s['notifies'][1]),
                          fully_blended=notify_name(s['notifies'][2]))
                if s['conduit']:
                    st['rule'] = self.expr(s['entry_rule'], m, where) if s['entry_rule'] is not None else dict(op='const', type='bool', value=True)
                else:
                    res = self.N[s['root']] if s['root'] is not None else None
                    first = self.link(res['links'].get('Result')) if res is not None else None
                    st['result'] = self.N[first]['name'] if first is not None else None
                    st['nodes'] = graph(self.subgraph(first)) if first is not None else []
                states.append(st)
                for e in s['exits']:
                    t = m['transitions'][e['transition']]
                    to = t['NextState']
                    if e.get('custom_result') is not None:
                        self.problems.append('%s: transition %d has a custom blend graph, which the builder does not make' % (where, e['transition']))
                    rule = None
                    if not e['automatic']:
                        rule = self.expr(e['rule'], m, '%s -> %s' % (where, names[to])) if e['rule'] is not None else dict(op='const', type='bool', value=False)
                        if not e['desired']:
                            rule = dict(op='call', cls='KismetMathLibrary', func='Not_PreBool', args=[rule])
                    notify = g.get('notifies') or []
                    transitions.append(dict(source=s['name'], target=names[to], priority=e['priority'],
                                            crossfade=t['CrossfadeDuration'], blend_mode=t['BlendMode'], logic=t['LogicType'],
                                            custom_curve=t['CustomCurve'] or None, blend_profile=t['BlendProfile'] or None,
                                            automatic=e['automatic'], rule=rule,
                                            start=notify_name(t['StartNotify']), end=notify_name(t['EndNotify']),
                                            interrupt=notify_name(t['InterruptNotify'])))
            machines.append(dict(node=mnode, name=m['name'], initial=names[m['initial']], states=states, transitions=transitions))
        for b in bindings:
            if b['node'] not in used:
                self.problems.append('the binding of %s.%s to %s: its node is not in the template' % (b['node'], b['pin'], b['source']))
        layout(main, machines)
        return dict(version=VERSION, name=name or g['cls'].rsplit('_C', 1)[0], source=g['package'], source_class=g['cls'],
                    parent=g['parent'], source_skeleton=g['skeleton'], anim_graph=dict(nodes=main, result=main[0]['id'] if main else None),
                    machines=machines, defaults=g.get('defaults', {}), refs=[r for r in g.get('refs', []) if 'ControlRig' not in r],
                    variables=g.get('variables', []), notes=self.notes, problems=self.problems)


def layout(main, machines):
    """Node positions: each pose chain right to left from its sink; states in columns by their distance from the first."""
    def chain(nodes, x0, y0):
        ids = {n['id']: n for n in nodes}
        depth = {}
        if not nodes:
            return
        todo = [(nodes[0]['id'], 1)]
        while todo:
            i, d = todo.pop(0)
            if i in depth:
                continue
            depth[i] = d
            for c in ids[i]['links'].values():
                if c in ids:
                    todo.append((c, d + 1))
        rows = {}
        for n in nodes:
            d = depth.get(n['id'], 1)
            r = rows.get(d, 0)
            rows[d] = r + 1
            n['pos'] = [x0 - 320 * d, y0 + 200 * r]
    chain(main, 0, 0)
    for m in machines:
        names = [s['name'] for s in m['states']]
        out = {}
        for t in m['transitions']:
            out.setdefault(t['source'], []).append(t['target'])
        layer = {m['initial']: 0}
        todo = [m['initial']]
        while todo:
            s = todo.pop(0)
            for t in out.get(s, []):
                if t not in layer:
                    layer[t] = layer[s] + 1
                    todo.append(t)
        rows = {}
        for s in m['states']:
            k = layer.get(s['name'], max(layer.values()) + 1 if layer else 0)
            r = rows.get(k, 0)
            rows[k] = r + 1
            s['pos'] = [200 + 420 * k, 180 * r]
            if not s['conduit']:
                chain(s.get('nodes', []), 0, 0)


if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    name = sys.argv[sys.argv.index('--name') + 1] if '--name' in sys.argv else None
    tpl = Template(json.load(open(src))).build(name)
    json.dump(tpl, open(out, 'w'), indent=1)
    n_states = sum(len(m['states']) for m in tpl['machines'])
    n_trans = sum(len(m['transitions']) for m in tpl['machines'])
    print('%s: %d AnimGraph node(s), %d machine(s), %d state(s)/conduit(s), %d transition(s), %d default(s); notes %d, problems %d' % (
        out, len(tpl['anim_graph']['nodes']), len(tpl['machines']), n_states, n_trans, len(tpl['defaults']), len(tpl['notes']), len(tpl['problems'])))
    for n in tpl['notes']:
        print('  note:', n)
    for p in tpl['problems']:
        print('  PROBLEM:', p)
