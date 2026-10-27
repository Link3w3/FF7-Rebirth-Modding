import sys, glob
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix', '/work/weap1012/tools']
import build_atb as B
def load(p):
    try:
        return B.Table(open(p, 'rb').read())
    except Exception as e:
        print('cannot decode', p, e); return None
def dump(t, name, label=''):
    r = t.row(name)
    print('==', label, name)
    for f in t.fields:
        v = t.get(r, f[0][0])
        if v not in (None, 0, 0.0, [], ''):
            print('   %-40s %r' % (f[0][0], v))
for p in sorted(glob.glob('p3/pkgs/*.uasset') + glob.glob('p20/pkgs/*.uasset')):
    t = load(p)
    if not t: continue
    keys = [k for k in t.at if 'PC0010' in k or 'Sephiroth' in k]
    print('#', p.split('/')[-1], len(t.keys), 'rows; fields:', [f[0][0] for f in t.fields][:60])
    print('   sephiroth rows:', keys[:40])
