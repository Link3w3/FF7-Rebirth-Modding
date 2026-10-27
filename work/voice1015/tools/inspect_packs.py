import struct, sys
sys.path[:0] = ['/work/neutral20/tools', '/work/iostore', '/work/cs', '/work/hang1012/tools',
                '/work/weap1012/tools', '/work/vincentfix']
import drop_pack_asset as D
from iostore import Toc
from zen import Zen
import hdr, gameids, resolve
NULL = 0xFFFFFFFFFFFFFFFF
MOUNT = '../../../End/Content/'
ROWS = ['PC0000_00_Cloud_Standard', 'PC0000_04_Cloud_ZackCostume', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing',
        'PC0000_10_Cloud_CostaClothing2', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
        'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']
t = Toc(sys.argv[1])
_, store = hdr.parse_header(t.read([i for i in range(t.entries) if t.chunk_type(i) == 10][0]))
by = {t.files.get(i): i for i in range(t.entries)}
PKG, OBJ = gameids.load()
for row in ROWS:
    p = MOUNT + 'DataAsset/Game/CharaSpec/CharaSpec_%s.uasset' % row
    i = by[p]
    data = t.read(i)
    z = Zen(data)
    cand = resolve.candidates(z)
    nm = lambda v: (OBJ.get(v & ~(3 << 62)) or cand.get(v & ~(3 << 62)) or '?%016x' % v) if v != NULL else None
    nulls = [k for k, v in enumerate(z.imports) if v == NULL]
    e = bytes(z.export_data(0))
    r = D.tagged.Reader(z, e)
    top = D.tags(r, len(e))
    print('==', row, 'size', len(data), 'exports', len(z.exports), 'imports', len(z.imports), 'null', len(nulls), 'export bytes', len(e))
    print('   top tags', [(x.name, x.type, x.inner, x.size) for x in top])
    adl = [x for x in top if x.name == 'AssetDataList'][0]
    r.p = adl.value_at
    n = r.i32()
    inner = D.Tag(r)
    print('   AssetDataList', n, 'inner', inner.name, inner.type, inner.struct, inner.size)
    for k in range(n):
        el = D.tags(r, adl.end)
        for x in el:
            if x.type == 'ArrayProperty' and x.inner == 'ObjectProperty':
                c = struct.unpack_from('<i', e, x.value_at)[0]
                vals = struct.unpack_from('<%di' % c, e, x.value_at + 4)
                print('   [%d] %s (%d):' % (k, x.name, c), [nm(z.imports[-v - 1]).rsplit('/', 1)[-1] if v < 0 else v for v in vals])
            else:
                print('   [%d] %s %s %s size %d' % (k, x.name, x.type, x.inner or x.struct or '', x.size))
    g = D.graph_entries(data, z)
    se = store[t.chunk_id64(i)]
    gp = [p for p, _ in g]
    print('   graph', len(g), 'sorted' if gp == sorted(gp) else 'NOT sorted', 'arcs', sorted(set(b[8:].hex() for _, b in g)))
    print('   store imports', len(se['imports']), 'sorted' if list(se['imports']) == sorted(se['imports']) else 'NOT sorted',
          'same set as graph' if set(se['imports']) == set(gp) else 'DIFFERENT from graph', 'load_order', se['load_order'])
    vo = [nm(v) for v in z.imports if v != NULL and 'Voice' in (nm(v) or '')]
    print('   voice imports', vo)
