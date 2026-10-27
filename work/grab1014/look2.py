import sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix', '/work/weap1012/tools']
import build_atb as B
ab = B.Table(open(B.GAME_ABILITY, 'rb').read())
dm = B.Table(open(B.GAME_DAMAGE, 'rb').read())
def dump(t, name):
    r = t.row(name)
    print('==', name)
    for f in t.fields:
        v = t.get(r, f[0][0])
        if v not in (None, 0, 0.0, [], ''):
            print('   %-36s %r' % (f[0][0], v))
dump(ab, 'PC0010_10_Stab')
# damage sources named like the abilities
names = sorted(k for k in dm.at if k.startswith('PC0010_10_BindFeeler') or k.startswith('PC0010_10_Stab'))
print(names)
for n in names: dump(dm, n)
