"""Name map, exports and imported packages of zen packages; flags path names that exist nowhere.
   zeninfo.py <label>=<file or utoc:index> ..."""
import sys, gzip, struct
sys.path.insert(0, '/work/cs'); sys.path.insert(0, '/work/iostore')
from zen import Zen
from iostore import Toc
import iostore_write as W

GAME = set()
for line in gzip.open('/work/gamelist/gamefiles.txt.gz', 'rt'):
    p = line.rstrip('\n').split('\t')[1]
    for pre, root in (('../../../End/Content/', '/Game/'), ('../../../Engine/Content/', '/Engine/')):
        if p.startswith(pre):
            p = root + p[len(pre):]
            break
    else:
        continue
    p = p.rsplit('.', 1)[0]
    GAME.add(p.lower())
EXTRA = set()

def load(spec):
    if ':' in spec and spec.split(':')[0].endswith('.utoc'):
        utoc, idx = spec.rsplit(':', 1)
        t = Toc(utoc)
        return t.read(int(idx))
    return open(spec, 'rb').read()

def graph_packages(z):
    d = z.d; o = z.graph_off
    n = struct.unpack_from('<i', d, o)[0]; o += 4
    ids = []
    for _ in range(n):
        pid, arcs = struct.unpack_from('<Qi', d, o); o += 12 + 8 * arcs
        ids.append(pid)
    return ids

def main():
    pakfiles = {}
    for a in sys.argv[1:]:
        if a.startswith('pak='):
            t = Toc(a[4:])
            for i in range(t.entries):
                f = t.files.get(i)
                if f:
                    p = '/Game/' + f.split('/End/Content/', 1)[1].rsplit('.', 1)[0]
                    EXTRA.add(p.lower())
    idmap = {}
    for p in GAME | EXTRA:
        pass
    for a in sys.argv[1:]:
        if a.startswith('pak='):
            continue
        label, spec = a.split('=', 1)
        z = Zen(load(spec))
        print('==', label, 'names', len(z.names), 'imports', len(z.imports), 'exports', len(z.exports))
        for e in z.exports:
            print('   export', e['name'], 'size', e['serial_size'])
        paths = sorted(n for n in z.names if n.startswith('/'))
        for n in paths:
            pkg = n.split('.', 1)[0].lower()
            where = 'game' if pkg in GAME else ('pak' if pkg in EXTRA else ('script' if pkg.startswith('/script/') else 'MISSING'))
            print('   %-8s %s' % (where, n))
        pids = graph_packages(z)
        print('   imported packages (graph):', len(pids))

main()
