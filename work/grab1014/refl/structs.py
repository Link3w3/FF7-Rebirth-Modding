"""Struct / class property layouts from UHT params: finds FPropertyParams arrays whose properties include given names."""
import struct, sys
sys.path.insert(0, '/work/grab1014/refl')
from refl import Refl
r = Refl('/data/uploads/FINAL FANTASY VII REBIRTH/End/Binaries/Win64/ff7rebirth_.exe')
p = r.p
want = sys.argv[1]
# every FPropertyParams whose name is `want`; then find the pointer array containing it (PropPointers) and print all
seen = set()
for s in r.strings(want):
    for o in r.refs(s):
        va = p.va(o)
        if va is None: continue
        prm = r.prop(va)
        if not prm or prm['name'] != want: continue
        # find arrays of pointers that contain va
        for o2 in r.refs(va):
            arr = p.va(o2)
            # walk back/forward over pointers to props
            def isprop(a):
                q = p.u64(a)
                if not q or not p.is_data(q): return False
                x = r.prop(q)
                return bool(x and x['name'] and x['name'].replace('_','a').isalnum())
            start = arr
            while isprop(start - 8): start -= 8
            end = arr
            while isprop(end + 8): end += 8
            if start in seen: continue
            seen.add(start)
            props = [r.prop(p.u64(a)) for a in range(start, end + 8, 8)]
            print('# array at %s: %d props' % (hex(start), len(props)))
            for x in sorted(props, key=lambda x: (x['offset'] if x['offset'] is not None else -1)):
                print('   %5s %-12s %s' % (hex(x['offset']) if x['offset'] is not None else 'bool', x['kind'], x['name']))
