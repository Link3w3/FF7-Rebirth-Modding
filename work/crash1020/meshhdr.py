import sys
sys.path[:0] = ['/work/fxlink/src/Content/Python', '/work/iostore', '/work/cs', '/work/custmat']
from rebirth_fx import uprops
from rebirth_fx.usmap import Usmap
from iostore import Toc
from zen import Zen
import micfix
U = Usmap(micfix.USMAP)
t = Toc(sys.argv[1]); want = sys.argv[2]; cls = sys.argv[3] if len(sys.argv) > 3 else 'SkeletalMesh'
for i in range(t.entries):
    if t.chunk_type(i) != 2 or not t.files.get(i, '').endswith('/' + want): continue
    z = Zen(t.read(i))
    k = [n for n, e in enumerate(z.exports) if e['name'] == want.split('.')[0]][0]
    data = z.export_bytes(k)
    hdr, p = micfix.read_header(data, 0)
    r = uprops.Reader(U, z.names, data, p, len(data))
    for idx, zero in hdr:
        prop, elem, owner = U.prop_at(cls, idx)
        at = r.p
        if zero:
            print('  %3d %-36s zero' % (idx, prop.name)); continue
        try:
            v = r.value(prop.ptype)
            print('  %3d %-36s %-44s @%d+%d' % (idx, prop.name, prop.ptype, at, r.p - at))
        except Exception as e:
            print('  %3d %-36s %-44s @%d FAIL %s' % (idx, prop.name, prop.ptype, at, str(e)[:150])); break
