"""The game's own EZ param link curves of PC0010_10_KDI (legacy tagged package: every field by name), in array order:
[{PX0, VX1_0, VX2_1, Grad0, Grad1, PY0, PY0A, PY0B, PY1, PY1A, PY1B, PY2, ByCoef}]. The editor dump (PC0010_10_KDI.json)
lost VX1_0 and VX2_1 (all zero): their tags are the literal names "VX1_0"/"VX2_1" (number 0), which the reconstructed
plugin's properties (FName "VX1" number 1, "VX2" number 2) do not match by name."""
import json, struct, sys
sys.path.insert(0, '/work/bnm/tools')
from uncooked_skel import summary_names
import tagged

D = '/work/bnm/Content/Character/Player/PC0010_10_Sephiroth_Transform/Model/'
FIELDS = ['PX0', 'VX1_0', 'VX2_1', 'Grad0', 'Grad1', 'PY0', 'PY0A', 'PY0B', 'PY1', 'PY1A', 'PY1B', 'PY2', 'ByCoef']


def main(out):
    names, _ = summary_names(open(D + 'PC0010_10_KDI.uasset', 'rb').read())
    ux = open(D + 'PC0010_10_KDI.uexp', 'rb').read()
    # the array property EffectorEZParamLinkBody: tag, then int32 count, then (for an array of structs) the inner struct tag, then the elements
    ni = names.index('EffectorEZParamLinkBody')
    p = 0
    hits = []
    while True:
        p = ux.find(struct.pack('<ii', ni, 0), p)
        if p < 0:
            break
        r = tagged.Reader(ux, names, p)
        try:
            t = tagged.read_tag(r)
        except Exception:
            p += 1
            continue
        if t.get('type') == 'ArrayProperty' and t.get('inner') == 'StructProperty':
            hits.append((p, t, r.p))
        p += 1
    assert len(hits) == 1, [h[0] for h in hits]
    p, t, q = hits[0]
    r = tagged.Reader(ux, names, q)
    n = r.unpack('<i')
    inner = tagged.read_tag(r)   # the inner struct tag of an array of structs
    assert inner['type'] == 'StructProperty' and inner['struct'] == 'SQEX_KineDriverEffectorEZParamLink', inner
    curves = []
    for k in range(n):
        c = {f: 0.0 for f in FIELDS}
        c['ByCoef'] = False
        while True:
            tg = tagged.read_tag(r)
            if tg['name'] == 'None':
                break
            assert tg['name'] in FIELDS, tg
            if tg['type'] == 'BoolProperty':
                c[tg['name']] = bool(tg['bool'])
            else:
                assert tg['type'] == 'FloatProperty', tg
                c[tg['name']] = tagged.read_scalar(r, 'FloatProperty')
        curves.append(c)
    assert r.p == q + t['size'], (r.p, q, t['size'])
    json.dump(curves, open(out, 'w'), indent=0)
    import collections
    print('%d curves; VX1_0 nonzero in %d, VX2_1 nonzero in %d' % (n, sum(1 for c in curves if c['VX1_0']), sum(1 for c in curves if c['VX2_1'])))


if __name__ == '__main__':
    main(sys.argv[1])
