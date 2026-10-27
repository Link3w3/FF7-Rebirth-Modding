"""Map zen package ids and object import hashes to game paths (from the game file list)."""
import gzip, os, pickle, struct, sys
sys.path.insert(0, '/work/cs')
import cityhash
LIST = '/work/gamelist/gamefiles.txt.gz'
CACHE = '/work/weap1012/tools/gameids.pickle'

def pkgid(path):
    return cityhash.CityHash64(path.lower().encode('utf-16-le'))

def objhash(path):
    s = ''.join('/' if c in '.:' else c.lower() for c in path)
    return cityhash.CityHash64(s.encode('utf-16-le')) & ~(3 << 62)

def load():
    if os.path.exists(CACHE):
        return pickle.load(open(CACHE, 'rb'))
    pk, ob = {}, {}
    for line in gzip.open(LIST, 'rt'):
        p = line.rstrip('\n').split('\t')[1]
        for pre, root in (('../../../End/Content/', '/Game/'), ('../../../Engine/Content/', '/Engine/')):
            if p.startswith(pre):
                p = root + p[len(pre):]
                break
        else:
            continue
        if not p.endswith('.uasset') and not p.endswith('.umap'):
            continue
        p = p.rsplit('.', 1)[0]
        short = p.rsplit('/', 1)[1]
        pk[pkgid(p)] = p
        for o in (p + '.' + short, p + '.' + short + '_C', p + '.Default__' + short + '_C'):
            ob[objhash(o)] = o
    pickle.dump((pk, ob), open(CACHE, 'wb'))
    return pk, ob

if __name__ == '__main__':
    pk, ob = load()
    print(len(pk), len(ob))
