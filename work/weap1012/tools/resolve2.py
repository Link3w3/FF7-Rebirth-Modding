"""resolve2.py <zen package> ...: imports resolved against the package's own name map and every game package."""
import struct, sys
sys.path.insert(0, '/work/cs'); sys.path.insert(0, '/work/weap1012/tools'); sys.path.insert(0, '/work/gunmoves')
from zen import Zen
import gameids
pk, ob = gameids.load()
objhash = gameids.objhash

def candidates(z):
    out = dict()
    paths = [n for n in z.names if n.startswith('/')]
    plain = [n for n in z.names if not n.startswith('/')]
    for p in paths:
        out[objhash(p)] = p
        for n in plain:
            out[objhash(p + '.' + n)] = p + '.' + n
            for m in plain:
                out[objhash(p + '.' + n + ':' + m)] = p + '.' + n + ':' + m
    return out

def imports_of(z):
    cand = candidates(z)
    res = []
    for i, v in enumerate(z.imports):
        typ = v >> 62
        h = v & ~(3 << 62)
        if typ == 2:
            res.append((i, v, cand.get(h) or ob.get(h) or '?%016x' % v))
        elif typ == 1:
            res.append((i, v, 'script %016x' % v))
        else:
            res.append((i, v, 'null'))
    return res

def graph_of(z):
    d = z.d; o = z.graph_off
    n = struct.unpack_from('<i', d, o)[0]; o += 4
    out = []
    for _ in range(n):
        pid, arcs = struct.unpack_from('<Qi', d, o); o += 12 + 8 * arcs
        out.append(pk.get(pid, '?%016x' % pid))
    return out

if __name__ == '__main__':
    for f in sys.argv[1:]:
        z = Zen(open(f, 'rb').read())
        print('==', f.rsplit('/', 1)[-1].replace('Game__DataAsset__Game__CharaSpec__', ''), 'exports', [(e['name'], e['serial_size']) for e in z.exports][:6])
        for i, v, p in imports_of(z):
            if not p.startswith('script') and p != 'null':
                print('   import[%d] %s' % (i, p))
        print('   graph:', graph_of(z))
