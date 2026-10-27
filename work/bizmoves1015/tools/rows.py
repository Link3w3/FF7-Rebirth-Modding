"""Rows of a frozen table package (zen) through build_atb.Table: rows whose key contains a filter, with non-empty fields."""
import io, contextlib, sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools']
import build_atb as B
def table(path):
    with contextlib.redirect_stdout(io.StringIO()):
        return B.Table(open(path, 'rb').read())
if __name__ == '__main__':
    t = table(sys.argv[1])
    names = [f[0][0] for f in t.fields]
    want = sys.argv[2] if len(sys.argv) > 2 else ''
    print(len(t.keys), 'rows')
    for key in t.at:
        if want in key:
            row = t.row(key)
            vals = {f: t.get(row, f) for f in names}
            print('==', key, {k: v for k, v in vals.items() if v not in (None, [], '', 0, 0.0)})
