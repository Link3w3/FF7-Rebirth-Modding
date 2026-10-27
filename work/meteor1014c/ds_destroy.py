import sys, io, contextlib, collections
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools']
import build_atb as B
with contextlib.redirect_stdout(io.StringIO()):
    dm = B.Table(open(B.GAME_DAMAGE, 'rb').read())
F = ['CollisionType','CollisionParameter_Array','HitDestroyType','HitDestroyTargetType','HitCount','HitCountTotal','HitInterval','LifeTime','ControlType','CreateBasePos','TargetBase','HitTarget2','EnemyHitCategoryTypeBit','DisableHitBackground','MoveOnTerrain','Property']
def show(k):
    r = dm.row(k)
    print('%-42s ' % k + ' '.join('%s=%s' % (f.replace('_Array',''), dm.get(r, f)) for f in F))
print(collections.Counter(dm.get(dm.rows[i], 'HitDestroyType') for i in range(len(dm.rows))))
big = []
for k, i in dm.at.items():
    r = dm.rows[i]
    p = dm.get(r, 'CollisionParameter_Array')
    if dm.get(r, 'CollisionType') == 2 and p and p[0] >= 2000:
        big.append((p[0], k))
for _, k in sorted(big, reverse=True)[:45]:
    show(k)
print()
for k in ['PC0010_10_ShadowFlare_02', 'PC0010_10_Tenshi_01', 'PC0010_Limit_1'] + [k for k in dm.at if k.startswith('SU2050_01_AtkMegaflare') or k.startswith('SU2050_01_AtkGigaflare')][:6]:
    if k in dm.at: show(k)
