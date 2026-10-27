"""What a cooked Remake (4.18) material or function still says about its graph: every kept expression (parameters, static
switches, function calls) with what feeds each of its inputs - by expression name, also when that expression itself was
stripped - and what feeds each of the material's pins.   skeleton.py <export.json> [--json]"""
import json, re, sys


def inp_ref(v):
    if not isinstance(v, dict) or 'ExpressionName' not in v:
        return None
    name = v.get('ExpressionName')
    if not name or name == 'None':
        return None
    mask = ''.join(c for c in 'RGBA' if v.get('Mask') and v.get('Mask' + c))
    return {'from': name, 'out': v.get('OutputIndex', 0), 'mask': mask or None}


def skeleton(path):
    d = json.load(open(path))
    nodes, pins = {}, {}
    owner = None
    for x in d:
        t, p = x.get('Type'), x.get('Properties', {})
        if t in ('Material', 'MaterialFunction'):
            owner = {'type': t, 'name': x.get('Name')}
            for k, v in p.items():
                r = inp_ref(v)
                if r:
                    pins[k] = r
            continue
        n = {'type': t[len('MaterialExpression'):] if t.startswith('MaterialExpression') else t, 'inputs': {}, 'props': {}}
        for k, v in p.items():
            if k in ('Material', 'Function', 'Outputs', 'EditorX', 'EditorY', 'MaterialExpressionGuid', 'MaterialExpressionEditorX',
                     'MaterialExpressionEditorY', 'ExpressionGUID', 'Desc', 'bCollapsed'):
                continue
            r = inp_ref(v)
            if r:
                n['inputs'][k] = r
            elif k == 'FunctionInputs':
                for i, fi in enumerate(v):
                    rr = inp_ref(fi.get('Input'))
                    nm = (fi.get('Input') or {}).get('InputName') or 'In%d' % i
                    n['inputs'][nm] = rr
            elif k == 'FunctionOutputs':
                n['props']['outputs'] = [(fo.get('Output') or {}).get('OutputName') for fo in v]
            elif k == 'MaterialFunction':
                n['props']['function'] = (v or {}).get('ObjectPath', '').split('/')[-1].split('.')[0]
            elif k in ('Texture',):
                n['props']['texture'] = (v or {}).get('ObjectPath', '').split('/')[-1].split('.')[0] if isinstance(v, dict) else v
            elif not isinstance(v, (dict, list)):
                n['props'][k] = v
        nodes[x.get('Name')] = n
    # every stripped expression something refers to
    stripped = {}
    for nm, n in list(nodes.items()) + [('<pins>', {'inputs': pins})]:
        for k, r in n['inputs'].items():
            if r and r['from'] not in nodes:
                stripped.setdefault(r['from'], []).append('%s.%s' % (nm, k))
    return {'owner': owner, 'pins': pins, 'nodes': nodes, 'stripped': stripped}


def show(s):
    print('%s %s' % (s['owner']['type'], s['owner']['name']))
    for k, r in s['pins'].items():
        print('  PIN %-22s <- %s[%s]%s' % (k, r['from'], r['out'], '.' + r['mask'] if r['mask'] else ''))
    for nm in sorted(s['nodes'], key=lambda x: (re.sub(r'_\d+$', '', x), int(re.search(r'(\d+)$', x).group(1)) if re.search(r'\d+$', x) else 0)):
        n = s['nodes'][nm]
        pr = {k: v for k, v in n['props'].items() if k not in ('outputs',)}
        print('  %s (%s) %s' % (nm, n['type'], json.dumps(pr)))
        for k, r in n['inputs'].items():
            if r:
                print('      %-16s <- %s[%s]%s' % (k, r['from'], r['out'], '.' + r['mask'] if r['mask'] else ''))
    print('  stripped expressions referred to:', len(s['stripped']))
    for k in sorted(s['stripped']):
        print('    %-45s <- used by %s' % (k, ', '.join(s['stripped'][k])))


if __name__ == '__main__':
    s = skeleton(sys.argv[1])
    if '--json' in sys.argv:
        print(json.dumps(s, indent=1))
    else:
        show(s)
