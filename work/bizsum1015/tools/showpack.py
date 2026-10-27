import sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix', '/work/weap1012/tools']
from zen import Zen
import gameids
PKG, OBJ = gameids.load()
def show(label, d):
    z = Zen(d)
    print('==', label, len(d), 'names', len(z.names), 'imports', len(z.imports), 'exports', len(z.exports))
    for n in z.names: print('   name', n)
    for v in z.imports:
        print('   imp %016x %s' % (v, OBJ.get(v & ((1 << 62) - 1), OBJ.get(v, '?'))))
    for e in z.exports: print('   exp', e)
for f in sys.argv[1:]:
    show(f.split('/')[-1], open(f, 'rb').read())
