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
    print('export size', len(data))
    r = uprops.Reader(U, z.names, data, 0, len(data))
    hdr = r.header()
    for idx, zero in hdr:
        prop, elem, owner = U.prop_at('MaterialInstanceConstant', idx)
        at = r.p
        try:
            v = r.value(prop.ptype)
            print('%-28s @%d..%d' % (prop.name, at, r.p))
            if prop.name == 'BasePropertyOverrides':
                uprops.dump(v)
        except Exception as e:
            print('%-28s @%d FAIL %s' % (prop.name, at, e))
            print(data[at-40:at+60].hex())
            break
    print('tail:', data[r.p:].hex())
