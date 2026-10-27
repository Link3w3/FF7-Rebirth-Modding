"""Remake MaterialInstanceConstant -> plain dict (parent, parameters, overrides, static parameters)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkg418, uprops
from binr import B

def objpath(p, i):
    if i == 0: return None
    if i < 0: return p.import_path(i)
    return 'export:' + p.exports[i - 1]['name']

def static_params(r):
    sw = r.arr(lambda: dict(name=r.name(), value=r.b32(), override=r.b32(), guid=r.raw(16).hex()))
    cm = r.arr(lambda: dict(name=r.name(), r=r.b32(), g=r.b32(), b=r.b32(), a=r.b32(), override=r.b32(), guid=r.raw(16).hex()))
    tl = r.arr(lambda: dict(name=r.name(), index=r.i32(), override=r.b32(), guid=r.raw(16).hex()))
    return dict(switches=sw, masks=cm, layers=tl)

def read(path, schema):
    p = pkg418.Package(path)
    out = []
    for i, e in enumerate(p.exports):
        cls = p.classname(e)
        if cls != 'MaterialInstanceConstant':
            continue
        c, v, end = uprops.read_export(schema, p, i)
        P = v.py()
        mi = dict(name=e['name'], parent=objpath(p, P.get('Parent', 0)))
        mi['scalars'] = [(x['ParameterName'], x.get('ParameterValue', 0.0)) for x in P.get('ScalarParameterValues', [])]
        mi['vectors'] = [(x['ParameterName'], [x.get('ParameterValue', {}).get(k, 0.0) for k in 'RGBA'] if isinstance(x.get('ParameterValue'), dict) else [0, 0, 0, 0]) for x in P.get('VectorParameterValues', [])]
        mi['textures'] = [(x['ParameterName'], objpath(p, x.get('ParameterValue', 0))) for x in P.get('TextureParameterValues', [])]
        mi['overrides'] = P.get('BasePropertyOverrides', {})
        mi['static_resource'] = bool(P.get('bHasStaticPermutationResource'))
        mi['props'] = sorted(P.keys())
        r = B(p.d, end, p.names, e['off'] + e['size'])
        r.u32()  # object guid flag
        if mi['static_resource']:
            mi['static'] = static_params(r)
        mi['native_left'] = e['off'] + e['size'] - r.p
        out.append(mi)
    return out

if __name__ == '__main__':
    import json, glob
    from schema import Schema
    S = Schema()
    res = {}
    for f in sys.argv[1:]:
        for mi in read(f, S):
            res[mi['name']] = mi
    print(json.dumps(res, indent=1, default=str))
