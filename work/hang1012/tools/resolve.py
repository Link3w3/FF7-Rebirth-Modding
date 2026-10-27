"""Resolve the package-import object indices of zen packages to object paths from their own name maps."""
import sys, struct
sys.path.insert(0, '/work/cs'); sys.path.insert(0, '/work/iostore'); sys.path.insert(0, '/work/gunmoves')
from zen import Zen
from iostore import Toc
import cityhash, tagged

def objhash(path):
    s = ''.join('/' if c in '.:' else c.lower() for c in path)
    return cityhash.CityHash64(s.encode('utf-16-le')) & ~(3 << 62)

def candidates(z):
    paths = [n for n in z.names if n.startswith('/')]
    plain = [n for n in z.names if not n.startswith('/')]
    out = {}
    for p in paths:
        out[objhash(p)] = p
        for n in plain:
            out[objhash(p + '.' + n)] = p + '.' + n
            for m in plain:
                out[objhash(p + '.' + n + ':' + m)] = p + '.' + n + ':' + m
    return out

def describe(label, data):
    z = Zen(data)
    cand = candidates(z)
    print('==', label)
    for i, v in enumerate(z.imports):
        typ = v >> 62
        h = v & ~(3 << 62)
        print('  import[%d] type %d %s' % (i, typ, cand.get(h, '?%016x' % v) if typ == 2 else ('script %016x' % v if typ == 1 else 'null')))
    d = z.export_data(0)
    try:
        r = tagged.Reader(z, d); props = tagged.read_props(r)
        for lst in ('AssetDataList', 'AssetClassList'):
            for ent in props.get(lst, []):
                print('  %s %s:' % (lst, ent.get('AssetName')))
                for x in ent.get('AssetUserData', []):
                    idx = -x[1] - 1
                    v = z.imports[idx]
                    print('     ', cand.get(v & ~(3 << 62), '?%016x' % v))
    except Exception as ex:
        print('  (properties not tagged: %s)' % ex)

if __name__ == '__main__':
    for a in sys.argv[1:]:
        label, spec = a.split('=', 1)
        if '.utoc:' in spec:
            utoc, idx = spec.rsplit(':', 1); data = Toc(utoc).read(int(idx))
        else:
            data = open(spec, 'rb').read()
        describe(label, data)
