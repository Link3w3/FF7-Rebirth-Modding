"""Print a Rebirth zen package's imports, resolved to object paths where possible.
    rbimports.py <package.uasset>..."""
import sys
sys.path[:0] = ['/work/fx1018/editor/Python', '/work/cs', '/work/iostore']
from zen import Zen
from rebirth_fx.matcore import resolve_imports


def imports(path):
    z = Zen(open(path, 'rb').read())
    r = resolve_imports(z)
    return z, r


if __name__ == '__main__':
    for p in sys.argv[1:]:
        z, r = imports(p)
        print('##', p)
        for i, h in enumerate(z.imports):
            print('  %d  %016x  %s' % (-(i + 1), h, r.get(i, '?')))
