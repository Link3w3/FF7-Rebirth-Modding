import sys
sys.path.insert(0, '/work/evilboss1016/data')
import common as C
chunks, store, ab, ds = C.tables()
names = [f[0][0] for f in ds.fields]
for key in sys.argv[1:]:
    if key not in ds.at:
        print('NOT IN TABLE', key); continue
    r = ds.row(key)
    vals = {n: ds.get(r, n) for n in names}
    print(key, {k: v for k, v in vals.items() if v not in (None, [], '', 0, 0.0, False)})
