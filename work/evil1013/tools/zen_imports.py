"""Print a Zen (IoStore) package's name, exports and resolved imports."""
import sys, struct
sys.path.insert(0, '/work/iostore'); sys.path.insert(0, '/work/cs')
sys.path.insert(0, '/work/vincentfix'); sys.path.insert(0, '/work/weap1012/tools')
from zen import Zen
import gameids
PKG, OBJ = gameids.load()
NULL = 0xFFFFFFFFFFFFFFFF
for path in sys.argv[1:]:
    d = open(path, 'rb').read()
    z = Zen(d)
    print('==', path.rsplit('/', 1)[-1], 'bytes', len(d))
    for attr in ('name', 'package_name'):
        if hasattr(z, attr): print('  name:', getattr(z, attr))
    for v in z.imports:
        if v == NULL: print('   null'); continue
        kind = v >> 62
        print('   %d %s' % (kind, OBJ.get(v & ~(3 << 62), '?%x' % v)))
    ex = getattr(z, 'exports', [])
    print('  exports:', len(ex))
    for e in ex[:30]:
        print('   ', e if not isinstance(e, dict) else {k: e[k] for k in list(e)[:8]})
