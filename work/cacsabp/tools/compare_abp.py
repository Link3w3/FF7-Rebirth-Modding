"""Compares two decoded AnimBlueprints (abpgraph.py's JSON): the game's and one cooked from an editable AnimBlueprint the
editor built from its template. What the template leaves out (the Control Rig node and the space conversion pair it
leaves) is left out of the game's side first; states and transitions are compared by name (their indices differ).

    compare_abp.py <game graph .json> <cooked graph .json>
Exit 0: the same; 1: differences (listed)."""
import json, sys
sys.path[:0] = ['/work/cacsabp/tools']
from template_graph import Template

RUNTIME = {'BlendWeight', 'InternalTimeAccumulator', 'ActualAlpha', 'PreviousBlendSpace', 'bInitialized', 'StateMachineIndexInClass'}


def chain(g, links_of):
    """The AnimGraph's nodes from the root, through each node's first pose link, as their structs."""
    N = g['nodes']
    out, i, seen = [], links_of(N[0]).get('Result'), set()
    while i is not None and i not in seen:
        seen.add(i)
        n = N[i]
        out.append(n['struct'])
        if n['struct'] == 'AnimNode_StateMachine':
            break
        nxt = list(links_of(n).values())
        i = nxt[0] if nxt else None
    return out


def norm_rule(t, states):
    if t is None:
        return None
    op = t.get('op')
    if op == 'const':
        v = t['value']
        if t['type'] == 'float':
            v = round(float(v), 5)
        elif t['type'] in ('int', 'byte'):
            v = int(v)
        return ('const', 'bool' if t['type'] == 'bool' else ('num' if t['type'] in ('int', 'byte') else t['type']), v)
    if op == 'var':
        return ('var', t['name'])
    if op == 'call':
        cls = 'self' if t['cls'] in ('self', 'EndCharacterAnimInstance', 'AnimInstance') else t['cls']
        return ('call', cls, t['func'], tuple(norm_rule(a, states) for a in t['args']))
    if op == 'time':
        s = t['state']
        name = states[s]['name'] if isinstance(s, int) and 0 <= s < len(states) else s
        return ('time', t['func'], name)
    if op == 'select':
        # an option that gives its type's zero is the same as no option there (the select's default term: the zero); the
        # editor's select on an enum has an option for each of its entries the editor shows, so it may have more of them
        opts = [(int(a['value']) if isinstance(a, dict) else int(a), norm_rule(b, states)) for a, b in t['options']]
        opts = [(k, r) for k, r in opts if not (r and r[0] == 'const' and r[2] in (0, 0.0, False))]
        return ('select', norm_rule(t['index'], states), tuple(sorted(opts)))
    if op == 'default':
        return ('default',)
    return (op, json.dumps(t, sort_keys=True))


def values(n):
    return {k: v for k, v in n['values'].items() if k not in RUNTIME}


def main():
    a, b = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
    diffs, same = [], []
    # 1. the AnimGraph, with what the template leaves out taken out of the game's
    ta, tb = Template(a), Template(b)
    la = lambda n: {k: ta.link(v) for k, v in n['links'].items() if v is not None and v >= 0 and ta.link(v) is not None}
    lb = lambda n: {k: tb.link(v) for k, v in n['links'].items() if v is not None and v >= 0 and tb.link(v) is not None}
    ca = chain(a, la)
    cb = chain(b, lb)
    (same if ca == cb else diffs).append('AnimGraph chain: %s%s' % (' <- '.join(s.replace('AnimNode_', '') for s in ca),
                                                                   '' if ca == cb else '\n      cooked: ' + ' <- '.join(s.replace('AnimNode_', '') for s in cb)))
    # the AnimGraph's nodes' settings, by struct in chain order
    def chain_nodes(g, links_of):
        N = g['nodes']
        out, i, seen = [], links_of(N[0]).get('Result'), set()
        while i is not None and i not in seen:
            seen.add(i)
            out.append(N[i])
            if N[i]['struct'] == 'AnimNode_StateMachine':
                break
            nxt = list(links_of(N[i]).values())
            i = nxt[0] if nxt else None
        return out
    na = chain_nodes(a, la)
    nb = chain_nodes(b, lb)
    for x, y in zip(na, nb):
        va, vb = values(x), values(y)
        bad = sorted(k for k in set(va) & set(vb) if va[k] != vb[k])
        missing = sorted(set(va) - set(vb))
        if bad or missing:
            diffs.append('%s: %s%s' % (x['struct'], '; '.join('%s: %s / cooked %s' % (k, va[k][:80], vb[k][:80]) for k in bad),
                                       (' missing in the cooked one: %s' % missing) if missing else ''))
        else:
            same.append('%s: all %d settings' % (x['struct'], len(va)))
    # 2. the state machines, by name
    ma = {m['name']: m for m in a['machines']}
    mb = {m['name']: m for m in b['machines']}
    if set(ma) != set(mb):
        diffs.append('machines: %s / cooked %s' % (sorted(ma), sorted(mb)))
    for name in sorted(set(ma) & set(mb)):
        A, B = ma[name], mb[name]
        sa = {s['name']: s for s in A['states']}
        sb = {s['name']: s for s in B['states']}
        if set(sa) != set(sb):
            diffs.append('%s states: only the game\'s %s; only the cooked %s' % (name, sorted(set(sa) - set(sb)), sorted(set(sb) - set(sa))))
        ia = A['states'][A['initial']]['name']
        ib = B['states'][B['initial']]['name']
        (same if ia == ib else diffs).append('%s initial state: %s%s' % (name, ia, '' if ia == ib else ' / cooked ' + ib))
        nA = {n['index']: n for n in a['nodes']}
        nB = {n['index']: n for n in b['nodes']}
        state_ok = 0
        for s in sorted(set(sa) & set(sb)):
            x, y = sa[s], sb[s]
            problems = []
            for key in ('conduit', 'reset_on_entry'):
                if x[key] != y[key]:
                    problems.append('%s %s / %s' % (key, x[key], y[key]))
            na_ = [notify_name(a, k) for k in x['notifies']]
            nb_ = [notify_name(b, k) for k in y['notifies']]
            if na_ != nb_:
                problems.append('notifies %s / %s' % (na_, nb_))
            if x['conduit']:
                ra, rb = norm_rule(x['entry_rule'], A['states']), norm_rule(y['entry_rule'], B['states'])
                if ra != rb:
                    problems.append('entry rule %s / %s' % (ra, rb))
            else:
                pa = [nA[i]['struct'] for i in x['players']]
                pb = [nB[i]['struct'] for i in y['players']]
                if pa != pb:
                    problems.append('players %s / %s' % (pa, pb))
                for i, j in zip(x['players'], y['players']):
                    va, vb = values(nA[i]), values(nB[j])
                    bad = sorted(k for k in set(va) & set(vb) if va[k] != vb[k])
                    if bad:
                        problems.append('player settings ' + '; '.join('%s: %s / %s' % (k, va[k][:60], vb[k][:60]) for k in bad))
            if problems:
                diffs.append('%s/%s: %s' % (name, s, '; '.join(problems)))
            else:
                state_ok += 1
        same.append('%s: %d states and conduits the same' % (name, state_ok))
        # transitions: by (source, target, priority)
        def trans(M, g):
            out = {}
            for s in M['states']:
                for e in s['exits']:
                    t = M['transitions'][e['transition']]
                    key = (s['name'], M['states'][t['NextState']]['name'], e['priority'])
                    out[key] = dict(crossfade=round(float(t['CrossfadeDuration']), 5), blend=t['BlendMode'], logic=t['LogicType'],
                                    automatic=e['automatic'], desired=e['desired'],
                                    rule=None if e['automatic'] else norm_rule(e['rule'], M['states']))
            return out
        txa, txb = trans(A, a), trans(B, b)
        if set(txa) != set(txb):
            diffs.append('%s transitions: only the game\'s %s; only the cooked %s' % (name, sorted(set(txa) - set(txb))[:8], sorted(set(txb) - set(txa))[:8]))
        t_ok = 0
        for key in sorted(set(txa) & set(txb)):
            x, y = txa[key], txb[key]
            bad = [k for k in x if x[k] != y[k]]
            if bad:
                diffs.append('%s %s -> %s (priority %d): %s' % (name, key[0], key[1], key[2], '; '.join('%s %s / %s' % (k, x[k], y[k]) for k in bad)))
            else:
                t_ok += 1
        same.append('%s: %d of %d transitions the same (rules, crossfade, blend, logic)' % (name, t_ok, len(txa)))
    # 3. bindings, class defaults
    def binds(g):
        N = {n['name']: n for n in g['nodes']}
        return sorted((N[x['node']]['struct'] if x['node'] in N else x['node'], x['pin'], x['source']) for x in g['bindings'])
    ba, bb = binds(a), binds(b)
    (same if ba == bb else diffs).append('bindings: %s%s' % (ba, '' if ba == bb else ' / cooked %s' % bb))
    da, db = a.get('defaults', {}), b.get('defaults', {})
    for k in sorted(set(da) | set(db)):
        if 'ControlRig' in k:
            continue
        if da.get(k) != db.get(k):
            diffs.append('class default %s: %s / cooked %s' % (k, (da.get(k) or '-')[:120], (db.get(k) or '-')[:120]))
    same.append('class defaults: %d of %d the same' % (sum(1 for k in da if da.get(k) == db.get(k)), len(da)))
    print('THE SAME:')
    for s in same:
        print('  ' + s)
    print('DIFFERENT:' if diffs else 'DIFFERENT: nothing')
    for d in diffs:
        print('  ' + d)
    return 1 if diffs else 0


def notify_name(g, k):
    n = g.get('notifies') or []
    return n[k]['NotifyName'] if isinstance(k, int) and 0 <= k < len(n) else None


if __name__ == '__main__':
    sys.exit(main())
