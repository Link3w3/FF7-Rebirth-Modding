import sys
sys.path.insert(0, '/work/evilboss1016/data')
import common as C
chunks, store, ab, ds = C.tables()
names = [f[0][0] for f in ds.fields]
def vals(key):
    r = ds.row(key)
    return {n: ds.get(r, n) for n in names}
pairs = [(k, k.replace('_NPC', '')) for k in ds.at if '_NPC' in k and k.replace('_NPC', '') in ds.at]
print(len(pairs), 'NPC/enemy pairs')
import collections
diff = collections.Counter()
ex = {}
for a, b in pairs:
    va, vb = vals(a), vals(b)
    for n in names:
        if va[n] != vb[n]:
            diff[n] += 1
            ex.setdefault(n, (a, va[n], vb[n]))
for n, c in diff.most_common(30):
    print(n, c, ex[n])
print([k for k in ds.at if '_NPC' in k][:40])
