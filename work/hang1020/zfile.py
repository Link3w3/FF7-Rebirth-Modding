import sys
sys.path.insert(0, '/work/hang1020')
from zdump import dump
for p in sys.argv[1:]:
    dump(open(p, 'rb').read(), p.rsplit('/', 1)[-1])
