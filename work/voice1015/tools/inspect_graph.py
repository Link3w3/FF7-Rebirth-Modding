import struct, sys
sys.path[:0] = ['/work/neutral20/tools', '/work/iostore', '/work/cs', '/work/hang1012/tools',
                '/work/weap1012/tools', '/work/vincentfix']
import drop_pack_asset as D
from iostore import Toc
from zen import Zen
import hdr, gameids
NULL = 0xFFFFFFFFFFFFFFFF
MOUNT = '../../../End/Content/'
t = Toc(sys.argv[1])
_, store = hdr.parse_header(t.read([i for i in range(t.entries) if t.chunk_type(i) == 10][0]))
by = {t.files.get(i): i for i in range(t.entries)}
PKG, OBJ = gameids.load()
import iostore_write as W
row = sys.argv[2]
i = by[MOUNT + 'DataAsset/Game/CharaSpec/CharaSpec_%s.uasset' % row]
data = t.read(i)
z = Zen(data)
# package of each import
pk = {}
for k, v in enumerate(z.imports):
    if v == NULL or v >> 62 != 2: continue
    n = OBJ.get(v & ~(3 << 62))
    if n: pk.setdefault(W.package_id(n.split('.', 1)[0]), []).append((k, n.rsplit('/', 1)[-1]))
names = lambda p: PKG.get(p) or ','.join(x[1] for x in pk.get(p, [])) or '?'
g = D.graph_entries(data, z)
print('graph:')
for p, b in g:
    print('  %016x %-70s arcs %s' % (p, names(p)[:70], b[8:].hex()))
se = store[t.chunk_id64(i)]
print('store imports:')
for p in se['imports']:
    print('  %016x %s %s' % (p, names(p)[:80], '' if p in [q for q, _ in g] else '<- not in graph'))
print('imports:')
for k, v in enumerate(z.imports):
    print('  %2d %s %s' % (k, '%016x' % v if v != NULL else 'null', (OBJ.get(v & ~(3 << 62)) or '') if v != NULL else ''))
print('summary', struct.unpack_from('<QQII10i', data, 0))
