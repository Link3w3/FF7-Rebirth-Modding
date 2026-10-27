"""The game's weapon blueprints (cooked, zen): each one's class (its own variables), parent, class defaults and component
templates decoded with the game's usmap, the blueprint classes registered as structs (parents first) so that their
class defaults read.
    wbpread.py <dir of BluePrint__Character__Weapon__*.uasset> [names ...]"""
import glob, io, os, sys
sys.path[:0] = ['/work/fx1018/tools', '/work/iostore', '/work/cs', '/work/weap1012/tools',
                '/work/swap1012/tools', '/work/weaponbp/tools', '/work/cacsabp/tools']
import fxlib, uprops, scriptobjs, zeninfo, abpread, gameids
from usmap import Struct, Prop
from zen import Zen

PATHS, _ = scriptobjs.load()
PKG_IDS, OBJS = gameids.load()
NULL = 0xFFFFFFFFFFFFFFFF


def import_path(z, v):
    """An import index value's object path: a script path, a game object path, or None."""
    kind = v >> 62
    if kind == 1:
        return PATHS.get(v)
    if kind == 2:
        return OBJS.get(v & ~(3 << 62))
    return None


class BP:
    def __init__(self, path):
        self.file = path
        self.d = open(path, 'rb').read()
        self.z = Zen(self.d)
        z = self.z
        self.package = z.mapped(z.name_mapped)
        self.cls_index = [i for i, e in enumerate(z.exports) if PATHS.get(e['cls'], '').endswith('.BlueprintGeneratedClass')]
        assert len(self.cls_index) == 1, (path, self.cls_index)
        self.cls_index = self.cls_index[0]
        self.cls_name = z.exports[self.cls_index]['name']
        self.info = abpread.read_class(z, self.cls_index)
        sup = z.exports[self.cls_index]['super']
        self.parent = import_path(z, sup)
        self.parent_is_bp = (sup >> 62) == 2
        self.parent_name = self.parent.rsplit('.', 1)[-1] if self.parent else None

    def register(self):
        u = fxlib.usmap()
        props, idx = [], 0
        for f in self.info['properties']:
            props.append(Prop(idx, f['array_dim'], f['name'], abpread.ptype_of(f)))
            idx += f['array_dim']
        u.structs[self.cls_name] = Struct(self.cls_name, self.parent_name, idx, props)

    def read(self):
        """[(export index, name, class path, outer index or None, value V)]"""
        z = self.z
        out = []
        for i, e in enumerate(z.exports):
            if i == self.cls_index:
                continue
            data = z.export_bytes(i)
            if e['cls'] >> 62 == 0:            # the class default object (its class is this package's class)
                sname = z.exports[e['cls']]['name']
                cpath = self.package + '.' + sname
            else:
                cpath = PATHS.get(e['cls']) or import_path(z, e['cls'])
                sname = cpath.rsplit('.', 1)[-1]
            r = uprops.Reader(fxlib.usmap(), z.names, data, 0, len(data))
            v = r.props(sname)
            outer = None if e['outer'] == NULL else e['outer']
            out.append((i, e['name'], cpath, outer, v, r.p, len(data)))
        return out

    def ref(self, v):
        """An FPackageIndex value (int) as ('export', name) / ('import', path) / None."""
        if v == 0:
            return None
        if v > 0:
            return ('export', self.z.exports[v - 1]['name'])
        return ('import', import_path(self.z, self.z.imports[-v - 1]) or '%016x' % self.z.imports[-v - 1])


def load_all(folder):
    bps = {}
    for f in sorted(glob.glob(os.path.join(folder, 'BluePrint__Character__Weapon__*.uasset'))):
        b = BP(f)
        bps[b.package] = b
    # parents first
    done = set()
    def reg(b):
        if b.package in done:
            return
        if b.parent_is_bp:
            pp = b.parent.rsplit('.', 1)[0]
            if pp in bps:
                reg(bps[pp])
        b.register()
        done.add(b.package)
    for b in bps.values():
        reg(b)
    return bps


if __name__ == '__main__':
    bps = load_all(sys.argv[1])
    want = sys.argv[2:]
    for pkg, b in bps.items():
        if want and not any(w in pkg for w in want):
            continue
        print('=' * 20, pkg, '| parent', b.parent, '| vars', [(p['name'], p['type']) for p in b.info['properties']])
        for i, name, cpath, outer, v, end, size in b.read():
            s = io.StringIO()
            uprops.dump(v, '      ', out=s)
            print('  [%d] %s (%s) outer=%s read %d/%d' % (i, name, cpath, outer, end, size))
            print('\n'.join(l for l in s.getvalue().splitlines()[1:] if 'ResponseChannel' not in l and 'Channel:' not in l and 'Response:' not in l and not l.strip().startswith('[')))
