import sys
sys.path.insert(0, '/work/evilboss1016/data')
import common as C
chunks, store, ab, ds = C.tables()
for key in ds.at:
    if key.startswith('EB2020') or key.startswith('PC0011') or 'Renkei' in key and key.startswith('EB'):
        r = ds.row(key)
        names = [f[0][0] for f in ds.fields]
        vals = {n: ds.get(r, n) for n in names}
        print(key, {k: v for k, v in vals.items() if v not in (None, [], '', 0, 0.0, False)})
print(len(ds.at), 'damage source rows in the Resident table')
