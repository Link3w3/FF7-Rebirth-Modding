import sys, collections
sys.path.insert(0, '/work/evilboss1016/data')
import common as C
chunks, store, ab, ds = C.tables()
stats = collections.defaultdict(collections.Counter)
fields = ['EnemyHitCategoryTypeBit', 'HitTarget0', 'HitTarget1', 'HitTarget2', 'HitTarget3', 'HitTarget4', 'HitTarget5', 'HitTarget6', 'Property']
ex = collections.defaultdict(list)
for key in ds.at:
    kind = key[:2] if key[:2] in ('PC', 'EB', 'EN', 'SU', 'WE') else 'other'
    r = ds.row(key)
    sig = tuple(ds.get(r, f) for f in fields)
    stats[kind][sig] += 1
    if len(ex[(kind, sig)]) < 3: ex[(kind, sig)].append(key)
print(fields)
for kind, c in stats.items():
    print('==', kind, sum(c.values()))
    for sig, n in c.most_common(12):
        print('  ', sig, n, ex[(kind, sig)])
