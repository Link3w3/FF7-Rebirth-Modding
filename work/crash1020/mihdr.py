import sys
sys.path[:0] = ['/work/fxlink/src/Content/Python', '/work/iostore', '/work/cs']
from rebirth_fx import uprops
from rebirth_fx.usmap import Usmap
from iostore import Toc
from zen import Zen
U = Usmap('/data/uploads/FF7R2UProj/Saved/ModExtract/usmap/Rebirth_Mappings.usmap')
t = Toc(sys.argv[1]); want = sys.argv[2]
for i in range(t.entries):
    if t.chunk_type(i) != 2 or want not in t.files.get(i, ''): continue
    z = Zen(t.read(i))
    data = z.export_bytes(0)
    r = uprops.Reader(U, z.names, data, 0, len(data))
    hdr = r.header()
    print(t.files[i].split('/')[-1], 'header ends at', r.p, 'props', len(hdr))
    for idx, zero in hdr:
        prop, elem, owner = U.prop_at('MaterialInstanceConstant', idx)
        print('  idx %3d %-5s %-40s %-30s %s' % (idx, 'zero' if zero else '', prop.name if prop else None, owner, prop.ptype if prop else ''))
    print('  data:', data[r.p:r.p+96].hex())
