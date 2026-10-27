import sys, os, json
sys.path.insert(0, '/work/sephatb/tools')
import build_atb as B
for f in sys.argv[1:]:
    t = B.Table(open(f, 'rb').read())
    print('==', os.path.basename(f), len(t.rows), 'rows')
    print('   fields:', [(x[0][0], x[1], x[2]) if isinstance(x[0], tuple) else x for x in t.fields])
    for k in list(t.at)[:4]:
        r = t.row(k)
        print('  ', k, {x[0][0]: t.get(r, x[0][0]) for x in t.fields})
