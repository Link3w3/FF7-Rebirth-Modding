import sys
sys.path.insert(0, '/work/evilboss1016/data')
import common as C
chunks, store, ab, ds = C.tables()
names = [f[0][0] for f in ds.fields]
def vals(key):
    r = ds.row(key)
    return {n: ds.get(r, n) for n in names}
out = []
for key in ds.at:
    v = vals(key)
    if v['ControlType'] == 3 and not v['Flag0'] and v['EnemyHitCategoryTypeBit'] == 31 and v['HitTarget2'] == 1 and v['Power'] > 0:
        out.append((key, v['CreatePartName'], v['CreateBasePos'], v['Power'], v['CreatePhysicsObjectCharaSpecID'], v['BindEffectResourceName'], v['HitEffectResourceName_Array'], v['ControlParameter_Array'][:3], v['CollisionParameter_Array'], v['LifeTime'], v['HitCount']))
print(len(out))
for o in out:
    if o[0].startswith(('PC', 'EB', 'NP', 'Chain')):
        print(o)
