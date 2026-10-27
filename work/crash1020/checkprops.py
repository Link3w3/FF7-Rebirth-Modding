"""Parse every export of a zen container with a .usmap (the game's class layouts) and report where each export's
unversioned properties end versus the export's size, and any parse error."""
import sys, traceback
sys.path[:0] = ['/work/fxlink/src/Content/Python', '/work/iostore', '/work/cs']
from rebirth_fx import uprops
from rebirth_fx.usmap import Usmap
from iostore import Toc
from zen import Zen
import scriptobjs
USMAP = sys.argv[2] if len(sys.argv) > 2 else '/data/uploads/FF7R2UProj/Saved/ModExtract/usmap/Rebirth_Mappings.usmap'
u = Usmap(USMAP)
so = scriptobjs.load()
paths = so[0] if isinstance(so, tuple) else so
t = Toc(sys.argv[1])
only = sys.argv[3] if len(sys.argv) > 3 else None
for i in range(t.entries):
    if t.chunk_type(i) != 2: continue
    fn = t.files.get(i, '').split('/')[-1]
    if only and only not in fn: continue
    z = Zen(t.read(i))
    for k, e in enumerate(z.exports):
        try:
            cls, v, end, data = uprops.read_export(u, z, k, paths)
            print('%-34s %-28s %-36s props end %7d of %7d' % (fn[:34], e['name'][:28], cls, end, len(data)))
        except Exception as ex:
            print('%-34s %-28s ERROR %s' % (fn[:34], e['name'][:28], str(ex)[:400]))
