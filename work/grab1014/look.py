import sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix', '/work/weap1012/tools']
import build_atb as B
ab = B.Table(open(B.GAME_ABILITY, 'rb').read())
dm = B.Table(open(B.GAME_DAMAGE, 'rb').read())
print('ability fields:', [f[0][0] for f in ab.fields])
print('damage fields:', [f[0][0] for f in dm.fields])
for name in ['PC0010_10_BindFeeler', 'PC0010_10_WarpStab']:
    r = ab.row(name)
    print('==', name)
    for f in ab.fields:
        v = ab.get(r, f[0][0])
        if v not in (None, 0, 0.0, [], ''):
            print('   %-32s %r' % (f[0][0], v))
