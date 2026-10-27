import io, contextlib, sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools']
import build_atb as B
from iostore import Toc
t = Toc('/work/bizsum1015/data1/FullyPlayableSephirothDataAssets_P.utoc')
def table(path):
    i = [k for k, v in t.files.items() if v == B.MOUNT + path][0]
    with contextlib.redirect_stdout(io.StringIO()):
        return B.Table(t.read(i))
ab = table('DataObject/Resident/BattleAbility.uasset')
names = [f[0][0] for f in ab.fields]
print(len(ab.keys), 'abilities; fields:', names)
want = sys.argv[1:]
for key in ab.at:
    if any(w in key for w in want):
        row = ab.row(key)
        vals = {f: ab.get(row, f) for f in names}
        print('==', key)
        print('   ', {k: v for k, v in vals.items() if v not in (None, [], '', 0, 0.0)})
