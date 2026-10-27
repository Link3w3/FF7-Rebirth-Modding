"""A cooked (zen, UE 4.26) AnimBlueprint described as a graph to build again in the editor: its anim nodes (type,
settings, pose links), its state machines (states, conduits, transitions with their rules as expression trees taken
from the ubergraph's bytecode), its pin bindings (property access copies) and notifies.

Index conventions found in the game's AnimBlueprints (UE 4.26): the anim node list is the generated class's anim node
properties in their serialized order (S); a pose link's LinkID is a position in S; a state machine's node indices
(state root, players, transition rules, the machine index the time getters take) count from the end of S
(S[len - 1 - index]).

    abpgraph.py <AnimBlueprint .uasset> <out.json>
"""
import json, struct, sys
sys.path[:0] = ['/work/cacsabp/tools']
import abpread, kismet, fxlib, uprops

NULL = 0xFFFFFFFFFFFFFFFF

# binary structs (uprops.BINARY): their members, in serialized order
BINARY_FIELDS = {
    'Vector': ('X', 'Y', 'Z'), 'Vector2D': ('X', 'Y'), 'Vector4': ('X', 'Y', 'Z', 'W'), 'IntPoint': ('X', 'Y'),
    'IntVector': ('X', 'Y', 'Z'), 'LinearColor': ('R', 'G', 'B', 'A'), 'Quat': ('X', 'Y', 'Z', 'W'),
    'Rotator': ('Pitch', 'Yaw', 'Roll'), 'Plane': ('X', 'Y', 'Z', 'W'), 'Color': ('B', 'G', 'R', 'A'),
    'FloatInterval': ('Min', 'Max'), 'Int32Interval': ('Min', 'Max'), 'FrameNumber': ('Value',),
    'IntVector4': ('X', 'Y', 'Z', 'W'), 'Vector3f': ('X', 'Y', 'Z'), 'Vector2f': ('X', 'Y'), 'Vector4f': ('X', 'Y', 'Z', 'W'),
    'Vector_NetQuantize': ('X', 'Y', 'Z'), 'Vector_NetQuantize10': ('X', 'Y', 'Z'), 'Vector_NetQuantize100': ('X', 'Y', 'Z'),
    'Vector_NetQuantizeNormal': ('X', 'Y', 'Z'), 'SimpleCurveKey': ('Time', 'Value'),
    'RichCurveKey': ('InterpMode', 'TangentMode', 'TangentWeightMode', 'Time', 'Value', 'ArriveTangent', 'ArriveTangentWeight',
                     'LeaveTangent', 'LeaveTangentWeight'),
}
INT_BINARY = {'IntPoint', 'IntVector', 'Color', 'Int32Interval', 'FrameNumber', 'IntVector4'}
# struct members that are Transient (runtime state, never saved): ImportText refuses them, so they are not written
TRANSIENT = {'InputAlphaBoolBlend': ('bInitialized', 'AlphaBlend'), 'InputScaleBiasClamp': ('bInitialized', 'InterpolatedResult')}
OBJ_TYPES = {'ObjectProperty', 'ClassProperty', 'WeakObjectProperty', 'LazyObjectProperty', 'InterfaceProperty', 'ObjectPtrProperty'}
SOFT_TYPES = {'SoftObjectProperty', 'SoftClassProperty', 'AssetObjectProperty'}


def f32text(x):
    """The shortest text that reads back as the same 32-bit float."""
    x = float(x)
    if x != x or x in (float('inf'), float('-inf')):
        return '0.0'
    want = struct.pack('<f', x)
    for p in range(0, 10):
        s = '%.*f' % (p, x)
        if struct.pack('<f', float(s)) == want:
            break
    else:
        for p in range(1, 10):
            s = '%.*g' % (p, x)
            if struct.pack('<f', float(s)) == want:
                break
    if s.startswith('-0') and float(s) == 0:
        s = s[1:]
    if 'e' not in s and '.' not in s:
        s += '.0'
    return s


def members(u, sname):
    """A struct's (or class's) properties by name, its supers' included."""
    out = {}
    s = u.structs.get(sname)
    seen = 0
    while s is not None and seen < 64:
        seen += 1
        for p in s.props:
            out.setdefault(p.name, p)
        s = u.structs.get(s.super) if s.super else None
    return out


def quoted(s):
    return '"%s"' % s.replace('\\', '\\\\').replace('"', '\\"')


class Texter:
    """Decoded values as UE text (FProperty::ExportText style) for ImportText in the editor, typed by the usmap schema:
    zero values (unversioned zero-mask: never serialized) take their type's zero, binary structs their members."""

    def __init__(self, u, resolve):
        self.u, self.resolve = u, resolve
        self.problems = []
        self.refs = set()

    def text(self, v, pt):
        if v is None:
            return None
        if getattr(v, 'zero', False):
            return self.zero(pt)
        t = pt.type if pt is not None else v.type
        if t == 'StructProperty':
            return self.struct(v, pt.struct if pt is not None else v.type)
        if t in ('ArrayProperty', 'SetProperty'):
            inner = pt.inner if pt is not None else None
            # (an empty array is no text at all: UE 4.26's array ImportText makes "()" one default element; a set
            # reads "()" as empty and refuses no text)
            if not v.value:
                return '' if t == 'ArrayProperty' else '()'
            return '(%s)' % ','.join(self.text(x, inner) or '' for x in v.value)
        if t == 'MapProperty':
            return '(%s)' % ','.join('(%s, %s)' % (self.text(a, pt.inner), self.text(b, pt.value)) for a, b in v.value)
        if t in SOFT_TYPES:
            n, sub = v.value if isinstance(v.value, (tuple, list)) else (v.value, '')
            path = n if n not in (None, 'None') else ''
            if path and sub:
                path += ':' + sub
            if path.startswith('/Game/'):
                self.refs.add(path)
            return quoted(path) if path else 'None'
        if t in OBJ_TYPES:
            if v.kind == 'obj' and isinstance(v.value, int):
                r = self.resolve(v.value)
                if r is None:
                    return 'None'
                if r.startswith('export:'):
                    self.problems.append('a reference to %s (an object of the AnimBlueprint itself) is left out' % r[7:])
                    return None
                if r.startswith('/Game/'):
                    self.refs.add(r)
                return r
            return 'None'
        if t == 'NameProperty':
            return 'None' if v.value in (None, 'None') else quoted(v.value)
        if t in ('StrProperty', 'Utf8StrProperty', 'AnsiStrProperty'):
            return quoted(v.value or '')
        if t == 'TextProperty':
            tv = v.value
            if isinstance(tv, tuple):
                if tv[0] == 'base':
                    return 'NSLOCTEXT(%s, %s, %s)' % (quoted(tv[1] or ''), quoted(tv[2] or ''), quoted(tv[3] or ''))
                if tv[0] == 'table':
                    return 'LOCTABLE(%s, %s)' % (quoted(tv[1] or ''), quoted(tv[2] or ''))
                if tv[0] == 'none':
                    return 'INVTEXT(%s)' % quoted(tv[1] or '')
            return '""'
        if t == 'EnumProperty':
            val = v.value
            return val.split('::')[-1] if isinstance(val, str) else str(val)
        if t == 'ByteProperty':
            if isinstance(v.value, str):          # (a versioned package's enum byte: by name)
                return v.value.split('::')[-1]
            if pt is not None and pt.enum and isinstance(v.value, int):
                names = self.u.enums.get(pt.enum, [])
                if 0 <= v.value < len(names):
                    return names[v.value].split('::')[-1]
            return str(v.value)
        if t == 'BoolProperty':
            return 'True' if v.value else 'False'
        if t == 'FloatProperty':
            return f32text(v.value)
        if t == 'DoubleProperty':
            return repr(float(v.value))
        if t in ('DelegateProperty', 'MulticastDelegateProperty', 'MulticastInlineDelegateProperty', 'MulticastSparseDelegateProperty',
                 'FieldPathProperty'):
            return None
        if v.kind == 'prim':
            return str(v.value)
        self.problems.append('a %s value is left out' % t)
        return None

    def top(self, v, pt):
        """The text of a property set on its own (the editor's ImportText without PPF_Delimited): a name or a string as
        it is, without quotes (quoted, the quotes would be part of it); anything else as text() writes it."""
        t = pt.type if pt is not None else (v.type if v is not None else None)
        if v is not None and t in ('NameProperty', 'StrProperty', 'Utf8StrProperty', 'AnsiStrProperty'):
            if getattr(v, 'zero', False):
                return 'None' if t == 'NameProperty' else ''
            if t == 'NameProperty':
                return 'None' if v.value in (None, 'None') else v.value
            return v.value or ''
        return self.text(v, pt)

    def struct(self, v, sname):
        if v.kind == 'native':
            fields = BINARY_FIELDS.get(sname)
            if fields and isinstance(v.value, (list, tuple)) and len(v.value) == len(fields):
                num = (lambda x: str(int(x))) if sname in INT_BINARY else f32text
                if sname == 'RichCurveKey':
                    vals = [str(int(x)) for x in v.value[:3]] + [f32text(x) for x in v.value[3:]]
                else:
                    vals = [num(x) for x in v.value]
                return '(%s)' % ','.join('%s=%s' % (f, x) for f, x in zip(fields, vals))
            if sname == 'Guid' and isinstance(v.value, (list, tuple)):
                return ''.join('%08X' % (x & 0xFFFFFFFF) for x in v.value)
            if sname in ('Box', 'Box2D') and isinstance(v.value, (list, tuple)):
                n = 3 if sname == 'Box' else 2
                axes = ('X', 'Y', 'Z')[:n]
                mn = ','.join('%s=%s' % (a, f32text(x)) for a, x in zip(axes, v.value[:n]))
                mx = ','.join('%s=%s' % (a, f32text(x)) for a, x in zip(axes, v.value[n:2 * n]))
                return '(Min=(%s),Max=(%s),IsValid=%d)' % (mn, mx, int(v.value[2 * n]))
            self.problems.append('a %s value is left out' % sname)
            return None
        if v.kind != 'struct':
            self.problems.append('a %s value read as %s is left out' % (sname, v.kind))
            return None
        mem = members(self.u, sname)
        parts = []
        for name, x in v.value.items():
            if name.startswith('@') or name in TRANSIENT.get(sname, ()):
                continue
            base, _, idx = name.partition('[')
            p = mem.get(base)
            t = self.text(x, p.ptype if p is not None else None)
            if t is None:
                continue
            parts.append('%s=%s' % ('%s(%s)' % (base, idx[:-1]) if idx else base, t))
        return '(%s)' % ','.join(parts)

    def zero(self, pt, depth=0):
        if pt is None:
            return None
        t = pt.type
        if t == 'BoolProperty':
            return 'False'
        if t == 'NameProperty':
            return 'None'
        if t in ('StrProperty', 'Utf8StrProperty', 'AnsiStrProperty', 'TextProperty'):
            return '""'
        if t in OBJ_TYPES or t in SOFT_TYPES:
            return 'None'
        if t == 'ArrayProperty':
            return ''
        if t in ('SetProperty', 'MapProperty'):
            return '()'
        if t in ('EnumProperty', 'ByteProperty'):
            names = self.u.enums.get(pt.enum, []) if pt.enum else []
            return names[0].split('::')[-1] if names else '0'
        if t == 'StructProperty':
            return self.zero_struct(pt.struct, depth)
        if t in ('FloatProperty', 'DoubleProperty'):
            return '0.0'
        if t in ('DelegateProperty', 'MulticastDelegateProperty', 'MulticastInlineDelegateProperty', 'MulticastSparseDelegateProperty',
                 'FieldPathProperty'):
            return None
        return '0'

    def zero_struct(self, sname, depth=0):
        fields = BINARY_FIELDS.get(sname)
        if fields:
            return '(%s)' % ','.join('%s=0' % f for f in fields)
        if sname == 'Guid':
            return '0' * 32
        if depth > 12:
            return '()'
        parts = []
        for name, p in members(self.u, sname).items():
            if name in TRANSIENT.get(sname, ()):
                continue
            t = self.zero(p.ptype, depth + 1)
            if t is not None:
                parts.append('%s=%s' % (name, t))
        return '(%s)' % ','.join(parts)


class Graph:
    def __init__(self, path):
        self.a = abpread.load(path)
        self.z = self.a['z']
        info = self.a['info']
        self.props = info['props']
        self.nodes = [f for f in info['properties'] if f['type'] == 'StructProperty' and f['struct'] and abpread.short(f['struct'][2]).startswith('AnimNode_')]
        self.n = len(self.nodes)
        self.cdo = self.a['cdo'].value
        self.u = fxlib.usmap()
        self.texter = Texter(self.u, self.resolve)

    def from_end(self, index):
        return self.n - 1 - index if index is not None and index >= 0 else None

    def resolve(self, v):
        """An object reference value (package index) as a path."""
        if not isinstance(v, int) or v == 0:
            return None
        nm = abpread.index_name(self.z, v)
        if nm[0] == 'export':
            return 'export:' + nm[2]
        h = self.z.imports[nm[1]]
        # a /Game object: one of the package's /Game names and its leaf (the class, its CDO, the asset)
        for name in self.z.names:
            if name.startswith('/Game/'):
                leaf = name.rsplit('/', 1)[1]
                for cand in (name + '.' + leaf, name + '.' + leaf + '_C', name + '.Default__' + leaf + '_C'):
                    if (2 << 62) | kismet_objhash(cand) == h:
                        return cand
        return nm[2]

    def node_values(self, i):
        """(UE text of each property the cooked node sets, its pose links)."""
        f = self.nodes[i]
        v = self.cdo.get(f['name'])
        texts, links = {}, {}
        if v is None:
            return texts, links
        mem = members(self.u, abpread.short(f['struct'][2]))
        for name, x in v.value.items():
            if name.startswith('@'):
                continue
            p = mem.get(name.partition('[')[0])
            if p is not None and p.ptype.type == 'StructProperty' and p.ptype.struct in ('PoseLink', 'ComponentSpacePoseLink', 'PoseLinkBase'):
                links[name] = x.value['LinkID'].value if x.kind == 'struct' and 'LinkID' in x.value else (0 if getattr(x, 'zero', False) else -1)
                continue
            if x.kind == 'struct' and set(x.value.keys()) == {'LinkID'}:
                links[name] = x.value['LinkID'].value
                continue
            t = self.texter.top(x, p.ptype if p is not None else None)
            if t is not None:
                texts[name] = t
        return texts, links

    def defaults(self):
        """The class default object's settings of the parent class's properties (not the anim nodes)."""
        nodes = {f['name'] for f in self.nodes}
        mem = members(self.u, self.a['cls_name'])
        out = {}
        for name, x in self.cdo.items():
            if name in nodes or name.startswith('@') or name == 'UberGraphFrame':
                continue
            p = mem.get(name.partition('[')[0])
            t = self.texter.top(x, p.ptype if p is not None else None)
            if t is not None:
                out[name] = t
        return out

    # --- the ubergraph's rule blocks
    def rules(self):
        ub = [k for k, e in enumerate(self.z.exports) if e['name'].startswith('ExecuteUbergraph_')]
        if not ub:
            return {}, {}
        exprs, mem, props = kismet.decode_function(self.z, ub[0])
        local_types = {p['name']: p for p in props}
        at = {e.mem: k for k, e in enumerate(exprs)}
        end_mem = exprs[-2].mem if len(exprs) >= 2 and exprs[-2].op == 'Return' else None
        # the EvaluateGraphExposedInputs functions: their entry point into the ubergraph
        entries = {}
        for k, e in enumerate(self.z.exports):
            if e['name'].startswith('EvaluateGraphExposedInputs_'):
                fx, _, _ = kismet.decode_function(self.z, k)
                call = fx[0]
                if call.op in ('FinalFunction', 'LocalFinalFunction') and call.args[1] and call.args[1][0].op == 'IntConst':
                    entries[e['name']] = call.args[1][0].args[0]
        out = {}
        for fname, entry in entries.items():
            k = at.get(entry)
            temps = {}
            seen = 0
            while k is not None and k < len(exprs) and seen < 400:
                seen += 1
                e = exprs[k]
                if e.op == 'Jump':
                    if e.args[0] == end_mem:
                        break
                    k = at.get(e.args[0])
                    continue
                if e.op in ('Let', 'LetBool', 'LetObj'):
                    dst = e.args[1] if e.op == 'Let' else e.args[0]
                    src = e.args[2] if e.op == 'Let' else e.args[1]
                    target = self.target(dst)
                    tree = self.tree(src, temps, local_types)
                    if target[0] == 'local':
                        temps[target[1]] = tree
                    elif target[0] == 'node':
                        out[fname] = dict(node=target[1], member=target[2], rule=tree)
                k += 1
        return out, entries

    def target(self, e):
        if e.op == 'LocalVariable':
            return ('local', e.args[0][1])
        if e.op == 'Context' and e.args[0].op == 'InstanceVariable' and e.args[3].op in ('LocalVariable', 'InstanceVariable', 'DefaultVariable'):
            # self.Node.Member (StructMemberContext appears as Context in cooked code for nodes)
            return ('node', e.args[0].args[0][1], e.args[3].args[0][1])
        if e.op == 'StructMemberContext' and e.args[1].op == 'InstanceVariable':
            return ('node', e.args[1].args[0][1], e.args[0][1])
        if e.op == 'InstanceVariable':
            return ('self', e.args[0][1])
        return ('other', kismet.fmt(e))

    def tree(self, e, temps, local_types):
        op = e.op
        a = e.args
        if op == 'LocalVariable':
            name = a[0][1]
            if name in temps:
                return temps[name]
            return dict(op='default', name=name)          # (a select's default local: never set)
        if op == 'InstanceVariable':
            return dict(op='var', name=a[0][1])
        if op in ('CallMath', 'FinalFunction', 'LocalFinalFunction'):
            fn = a[0][2] if isinstance(a[0], tuple) else str(a[0])
            cls, _, func = fn.rpartition(':')
            args = [self.tree(x, temps, local_types) for x in a[1]]
            if func in ('GetRelevantAnimTimeRemaining', 'GetRelevantAnimTimeFraction', 'GetRelevantAnimTimeRemainingFraction',
                        'GetRelevantAnimLength', 'GetRelevantAnimTime') and len(args) == 2 and all(x['op'] == 'const' for x in args):
                machine = self.from_end(args[0]['value'])
                return dict(op='time', func=func, machine_node=machine, state=args[1]['value'])
            return dict(op='call', cls=cls.rsplit('.', 1)[-1], func=func, args=args)
        if op == 'VirtualFunction':
            return dict(op='call', cls='self', func=a[0], args=[self.tree(x, temps, local_types) for x in a[1]])
        if op == 'Context' and a[0].op == 'Self':
            return self.tree(a[3], temps, local_types)
        if op == 'IntConst':
            return dict(op='const', type='int', value=a[0])
        if op in ('ByteConst', 'IntConstByte'):
            return dict(op='const', type='byte', value=a[0])
        if op == 'FloatConst':
            return dict(op='const', type='float', value=a[0])
        if op == 'True':
            return dict(op='const', type='bool', value=True)
        if op == 'False':
            return dict(op='const', type='bool', value=False)
        if op == 'IntZero':
            return dict(op='const', type='int', value=0)
        if op == 'IntOne':
            return dict(op='const', type='int', value=1)
        if op == 'NameConst':
            return dict(op='const', type='name', value=a[0])
        if op == 'SwitchValue':
            return dict(op='select', index=self.tree(a[1], temps, local_types),
                        options=[(self.tree(t, temps, local_types), self.tree(v, temps, local_types)) for t, _, v in a[2]],
                        default=self.tree(a[3], temps, local_types))
        if op == 'PrimitiveCast':
            return dict(op='cast', kind=a[0], value=self.tree(a[1], temps, local_types))
        return dict(op='raw', text=kismet.fmt(e))

    def build(self):
        S = []
        for i, f in enumerate(self.nodes):
            texts, links = self.node_values(i)
            S.append(dict(index=i, name=f['name'], struct=abpread.short(f['struct'][2]), values=texts, links=links))
        rules, entries = self.rules()
        by_node = {}
        for fname, r in rules.items():
            by_node[r['node']] = r
        # a transition result with no bound rule: its constant (the class default's bCanEnterTransition; absent: false)
        for s in S:
            if s['struct'] == 'AnimNode_TransitionResult' and s['name'] not in by_node:
                by_node[s['name']] = dict(node=s['name'], member='bCanEnterTransition',
                                          rule=dict(op='const', type='bool', value=s['values'].get('bCanEnterTransition') == 'True'))
        machines = []
        for m in self.props.value['BakedStateMachines'].value:
            mv = m.value
            states = []
            for s in mv['States'].value:
                sv = s.value
                root = self.from_end(sv['StateRootNodeIndex'].value)
                entry = self.from_end(sv['EntryRuleNodeIndex'].value)
                players = [self.from_end(x.value) for x in sv['PlayerNodeIndices'].value] if sv['PlayerNodeIndices'].kind == 'array' else []
                exits = []
                for prio, t in enumerate(sv['Transitions'].value if sv['Transitions'].kind == 'array' else []):
                    tv = t.value
                    rule_node = self.from_end(tv['CanTakeDelegateIndex'].value)
                    exits.append(dict(transition=tv['TransitionIndex'].value, priority=prio, rule_node=rule_node,
                                      rule_node_name=S[rule_node]['name'] if rule_node is not None else None,
                                      rule=by_node.get(S[rule_node]['name'], {}).get('rule') if rule_node is not None else None,
                                      custom_result=self.from_end(tv['CustomResultNodeIndex'].value),
                                      desired=bool(tv['bDesiredTransitionReturnValue'].value),
                                      automatic=bool(tv['bAutomaticRemainingTimeRule'].value)))
                states.append(dict(name=sv['StateName'].value, conduit=bool(sv['bIsAConduit'].value), root=root, players=players,
                                   entry_rule_node=entry, entry_rule=by_node.get(S[entry]['name'], {}).get('rule') if entry is not None else None,
                                   reset_on_entry=bool(sv['bAlwaysResetOnEntry'].value), exits=exits,
                                   notifies=[sv[k].value for k in ('StartNotify', 'EndNotify', 'FullyBlendedNotify')]))
            transitions = []
            for t in mv['Transitions'].value:
                tv = t.value
                transitions.append({k: plain(tv[k]) for k in tv})
            machines.append(dict(name=mv['MachineName'].value, initial=mv['InitialState'].value, states=states, transitions=transitions))
        # the machine nodes (the time getters name them; each machine node's StateMachineIndexInClass)
        for i, s in enumerate(S):
            if s['struct'] == 'AnimNode_StateMachine':
                idx = self.cdo[s['name']].value.get('StateMachineIndexInClass')
                k = idx.value if idx is not None else 0
                machines[k]['node'] = i
        # bindings: property access copies of the exposed value handlers
        bindings = []
        pal = self.props.value.get('PropertyAccessLibrary')
        segs = pal.value['PathSegments'].value if pal else []
        src = pal.value['SrcPaths'].value if pal else []
        dst = pal.value['DestPaths'].value if pal else []

        def path(p):
            pv = p.value
            start, count = pv['PathSegmentStartIndex'].value, pv['PathSegmentCount'].value
            return [segs[k].value['Name'].value for k in range(start, start + count)]
        for h in self.props.value['EvaluateGraphExposedInputs'].value:
            hv = h.value
            node = plain(hv['ValueHandlerNodeProperty'])
            node_name = node[0][0] if node else None
            recs = hv['CopyRecords'].value if hv['CopyRecords'].kind == 'array' else []
            for r in recs:
                ci = r.value['CopyIndex'].value
                copies = pal.value['CopyBatches[0]'].value['Copies'].value if pal else []
                c = copies[ci].value
                sp = path(src[c['AccessIndex'].value])
                dp = [path(dst[k]) for k in range(c['DestAccessStartIndex'].value, c['DestAccessEndIndex'].value)]
                for d in dp:
                    bindings.append(dict(node=node_name, pin='.'.join(d[1:]) if d and d[0] == node_name else '.'.join(d), source='.'.join(sp)))
        notifies = plain(self.props.value.get('AnimNotifies'))
        info = self.a['info']
        own_vars = [f for f in info['properties'] if f not in self.nodes and f['name'] != 'UberGraphFrame']
        defaults = self.defaults()
        return dict(cls=self.a['cls_name'], package=self.z.mapped(self.z.name_mapped), parent=info['super'][2],
                    skeleton=self.resolve(self.props.value['TargetSkeleton'].value), nodes=S, root=0, machines=machines,
                    bindings=bindings, notifies=notifies, variables=[dict(name=f['name'], type=f['type']) for f in own_vars],
                    defaults=defaults, refs=sorted(self.texter.refs), problems=self.texter.problems,
                    unresolved_rules=[n for n in by_node if not any(n == st.get('rule_node_name') for m in machines for s in m['states'] for st in s['exits'])
                                      and not any(n == (S[s['entry_rule_node']]['name'] if s['entry_rule_node'] is not None else None)
                                                  for m in machines for s in m['states'])])


def plain(v):
    return abpread.plain(v)


def kismet_objhash(path):
    from cityhash import CityHash64
    s = ''.join('/' if c in '.:' else c.lower() for c in path)
    return CityHash64(s.encode('utf-16-le')) & ~(3 << 62)


if __name__ == '__main__':
    g = Graph(sys.argv[1]).build()
    json.dump(g, open(sys.argv[2], 'w'), indent=1, default=str)
    nodes = g['nodes']
    print('%s: %d nodes, %d machine(s), %d binding(s)' % (g['cls'], len(nodes), len(g['machines']), len(g['bindings'])))
    for m in g['machines']:
        missing = [(s['name'], e['transition']) for s in m['states'] for e in s['exits'] if e['rule'] is None and not e['automatic']]
        conduits = [s['name'] for s in m['states'] if s['conduit'] and s['entry_rule'] is None]
        print('  %s (node %s): %d states, %d transitions; exits without a rule: %d %s; conduits without an entry rule: %s' % (
            m['name'], m.get('node'), len(m['states']), len(m['transitions']), len(missing), missing[:5], conduits))
