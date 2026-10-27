"""Which ucas byte ranges hold the menu textures' packages and bulk data (main + optional containers)."""
import sys, json, struct
sys.path.insert(0, '/work/iostore')
from iostore import Toc
P = '/data/uploads/FINAL FANTASY VII REBIRTH/End/Content/Paks/'
want = sys.argv[1].split(',')
out = []
for name in ('pakchunk3-WindowsNoEditor', 'pakchunk3optional-WindowsNoEditor'):
    t = Toc(P + name + '.utoc')
    print(name, 'entries', t.entries, 'blocksz', t.blocksz, 'methods', t.methods, 'files', len(t.files))
    # package ids of the wanted packages (from the main container's file names)
    ids = {}
    for i, path in t.files.items():
        base = path.rsplit('/', 1)[-1].replace('.uasset', '').replace('.ubulk', '').replace('.uptnl', '')
        if any(base == w for w in want):
            ids[t.chunk_id64(i)] = (base, path)
    for i in range(t.entries):
        pid = t.chunk_id64(i)
        hit = ids.get(pid)
        if not hit:
            continue
        off, ln = t.offlen[i]
        first, last = off // t.blocksz, (off + ln - 1) // t.blocksz
        blocks = [list(t.blocks[b]) for b in range(first, last + 1)]
        out.append(dict(container=name, chunk=i, type=t.chunk_type(i), name=hit[0], path=hit[1], off=off, len=ln,
                        first=first, blocks=blocks, blocksz=t.blocksz))
        print('  %-24s type %d len %7d blocks %d %s' % (hit[0], t.chunk_type(i), ln, len(blocks), t.files.get(i, '')))
json.dump(out, open('plan.json', 'w'), indent=0)
