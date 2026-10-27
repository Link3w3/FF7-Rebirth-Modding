import sys, glob
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix', '/work/weap1012/tools']
import build_atb as B
import io, contextlib
def load(p):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return B.Table(open(p, 'rb').read())
    except Exception as e:
        return None
tables = {}
for p in sorted(glob.glob('/work/grab1014/p3/pkgs/*.uasset') + glob.glob('/work/grab1014/p20/pkgs/*.uasset')):
    t = load(p)
    if t: tables[p.split('/')[-1].replace('DataObject__Resident__', '').replace('.uasset', '')] = t
def dump(tname, row, all_fields=False):
    t = tables[tname]
    r = t.row(row)
    print('==', tname, row)
    for f in t.fields:
        v = t.get(r, f[0][0])
        if all_fields or v not in (None, 0, 0.0, [], '', False, 'None'):
            print('   %-44s %r' % (f[0][0], v))
if __name__ == '__main__':
    tname = sys.argv[1]
    for row in sys.argv[2:]:
        if row.endswith('*'):
            for k in tables[tname].keys:
                if k.startswith(row[:-1]): dump(tname, k)
        else:
            dump(tname, row)
