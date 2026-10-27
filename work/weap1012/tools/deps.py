"""deps.py <zen package> ... : imported packages (graph) and resolved import objects."""
import struct, sys
sys.path.insert(0, '/work/cs'); sys.path.insert(0, '/work/weap1012/tools')
from zen import Zen
import gameids
pk, ob = gameids.load()
for f in sys.argv[1:]:
    z = Zen(open(f, 'rb').read())
    d = z.d; o = z.graph_off
    n = struct.unpack_from('<i', d, o)[0]; o += 4
    print('==', f.rsplit('/', 1)[-1], 'imported packages', n)
    for _ in range(n):
        pid, arcs = struct.unpack_from('<Qi', d, o); o += 12 + 8 * arcs
        print('   pkg', pk.get(pid, '?%016x' % pid))
    for i, v in enumerate(z.imports):
        typ = v >> 62
        if typ == 2:
            print('   import[%d] %s' % (i, ob.get(v & ~(3 << 62), '?%016x' % v)))
