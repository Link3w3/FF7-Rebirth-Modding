"""A zen package's exports and imports with names: script imports from the game's global.utoc, package imports from the
game's file list (main objects, classes, CDOs), else the raw index.
    zeninfo.py <pkg.uasset>"""
import struct, sys
sys.path[:0] = ['/work/cs', '/work/iostore', '/work/weap1012/tools']
from zen import Zen
import scriptobjs, gameids

NULL = 0xFFFFFFFFFFFFFFFF
_script = None
_game = None


def names():
    global _script, _game
    if _script is None:
        s = scriptobjs.load()
        _script = s[0] if isinstance(s, tuple) else s
        _game = gameids.load()[1]
    return _script, _game


def index_name(z, v, local=None):
    if v == NULL or v is None:
        return 'null'
    script, game = names()
    kind = v >> 62
    if kind == 0:
        e = z.exports[v]
        return 'export[%d] %s' % (v, e['name'])
    if kind == 1:
        return 'script %s' % script.get(v, hex(v))
    if kind == 2:
        h = v & ~(3 << 62)
        return 'pkg %s' % game.get(h, hex(v))
    return hex(v)


def main(path):
    d = open(path, 'rb').read()
    z = Zen(d)
    print(path.split('/')[-1], 'size', len(d), 'names', len(z.names), 'exports', len(z.exports), 'imports', len(z.imports))
    print('imports:')
    for i, v in enumerate(z.imports):
        print('  [%d] %s' % (i, index_name(z, v)))
    pos = z.bundle_positions()
    print('exports:')
    for i, e in enumerate(z.exports):
        print('  [%d] %-50s size %5d outer=%s class=%s super=%s template=%s flags=%x' % (
            i, e['name'], e['serial_size'], 'null' if e['outer'] == NULL else e['outer'], index_name(z, e['cls']),
            index_name(z, e['super']), index_name(z, e['template']), e['oflags']))
    print('names:', z.names)


if __name__ == '__main__':
    main(sys.argv[1])
