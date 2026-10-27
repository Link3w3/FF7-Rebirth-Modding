"""Show CharaSpec fields of rows in a FullyPlayableSephirothDataAssets_P container (or the retail table).
    show_rows.py <utoc or retail uasset> <field,...|all> <row> [<row> ...]"""
import io, contextlib, sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools']
import build_atb as B
from iostore import Toc
src, fields, rows = sys.argv[1], sys.argv[2], sys.argv[3:]
if src.endswith('.utoc'):
    t = Toc(src)
    i = [k for k, v in t.files.items() if v == B.MOUNT + B.CHARASPEC_TABLE][0]
    data = t.read(i)
else:
    data = open(src, 'rb').read()
with contextlib.redirect_stdout(io.StringIO()):
    cs = B.Table(data)
names = [f[0][0] for f in cs.fields]
want = names if fields == 'all' else fields.split(',')
for r in rows:
    row = cs.row(r)
    print('==', r)
    for f in want:
        v = cs.get(row, f)
        if fields != 'all' or v not in (None, [], '', 0):
            print('   %-36s %s' % (f, v))
