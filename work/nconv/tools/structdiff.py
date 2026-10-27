"""Which properties the game's own Niagara packages set that a converted package does not (and the reverse), per class.
    structdiff.py <converted .zen> <game package>..."""
import collections, os, sys
sys.path[:0] = ['/work/fx1018/editor/Python', '/work/cs', '/work/iostore']
import nio
from zen import Zen
import scriptobjs


def paths(v, pre='', out=None):
    out = set() if out is None else out
    if v is None:
        return out
    k = v.kind
    if k == 'struct':
        for name, x in v.value.items():
            p = pre + '.' + name
            out.add(p + ('=0' if getattr(x, 'zero', False) else ''))
            paths(x, p, out)
    elif k == 'array' or k == 'set':
        for x in v.value:
            if hasattr(x, 'kind'):
                paths(x, pre + '[]', out)
    elif k == 'map':
        for a, b in (v.value.items() if isinstance(v.value, dict) else v.value):
            if hasattr(a, 'kind'):
                paths(a, pre + '{k}', out)
            if hasattr(b, 'kind'):
                paths(b, pre + '{v}', out)
    elif k == 'native':
        val = v.value
        if isinstance(val, dict):
            for name, x in val.items():
                if hasattr(x, 'kind'):
                    out.add(pre + '.' + name)
                    paths(x, pre + '.' + name, out)
                elif isinstance(x, dict) and 'props' in x:
                    out.add(pre + '.' + name)
                    if hasattr(x['props'], 'kind'):
                        paths(x['props'], pre + '.' + name, out)
            if 'props' in val and hasattr(val['props'], 'kind'):
                paths(val['props'], pre, out)
    return out


def load(path, sp):
    z = Zen(open(path, 'rb').read())
    res = []
    for i in range(len(z.exports)):
        try:
            cls, v, extra, data = nio.read_export(z, i, sp)
        except Exception as ex:
            continue
        res.append((cls, paths(v), extra, z.exports[i]['name']))
    return res


def main(ours, games):
    sp, _ = scriptobjs.load()
    game = collections.defaultdict(list)
    for g in games:
        for cls, ps, extra, name in load(g, sp):
            game[cls].append(ps)
    mine = collections.defaultdict(list)
    for cls, ps, extra, name in load(ours, sp):
        mine[cls].append((name, ps))
    for cls, items in sorted(mine.items()):
        gs = game.get(cls)
        if not gs:
            print('== %s: no game export of this class' % cls)
            continue
        cnt = collections.Counter(p for ps in gs for p in ps)
        n = len(gs)
        print('== %s (%d ours, %d game)' % (cls, len(items), n))
        always = {p for p, c in cnt.items() if c >= 0.9 * n}
        seen = set(cnt)
        lack = collections.Counter()
        extra_ = collections.Counter()
        for name, ps in items:
            for p in always - ps:
                lack[p] += 1
            for p in ps - seen:
                extra_[p] += 1
        for p, c in sorted(lack.items()):
            print('   game sets (%d/%d), ours lack (%d/%d): %s' % (cnt[p], n, c, len(items), p))
        for p, c in sorted(extra_.items()):
            print('   ours set (%d/%d), game never: %s' % (c, len(items), p))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
