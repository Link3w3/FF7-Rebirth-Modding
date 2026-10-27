"""Which packages of a container import a given object (by global object id)."""
import sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/evil1013/tools', '/work/swap1012/tools',
                '/work/vincentfix', '/work/weap1012/tools']
from iostore import Toc
from zen import Zen
import gameids
utoc, objs = sys.argv[1], sys.argv[2:]
want = {gameids.objhash(o) & ~(3 << 62): o for o in objs}
t = Toc(utoc)
for i, f in sorted(t.files.items(), key=lambda x: x[1]):
    if t.chunk_type(i) != 2:
        continue
    z = Zen(t.read(i))
    hits = [(k, want[v & ~(3 << 62)]) for k, v in enumerate(z.imports) if v != 0xFFFFFFFFFFFFFFFF and (v & ~(3 << 62)) in want]
    if hits:
        print(f.replace('../../../End/Content/', ''), hits, 'imports', len(z.imports))
