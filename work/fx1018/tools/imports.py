"""Resolve a zen package's package imports to object paths using the game file list and its name map.
    imports.py <zen package>"""
import gzip, os, sys
sys.path[:0] = ['/work/iostore', '/work/cs']
from zen import Zen
import scriptobjs

_files = None


def game_files():
    """{package name (no dir) lowercase: [(utoc, '/Game/...package path')]}"""
    global _files
    if _files is None:
        _files = {}
        with gzip.open('/work/gamelist/gamefiles.txt.gz', 'rt', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.rstrip('\n')
                if '\t' not in line:
                    continue
                toc, p = line.split('\t', 1)
                if not p.endswith('.uasset') and not p.endswith('.umap'):
                    continue
                p = p.replace('../../../', '/')
                parts = p.split('/')
                # /End/Content/X -> /Game/X ; /End/Plugins/.../Content/X -> /<Plugin>/X ; /Engine/Content/X -> /Engine/X
                if p.startswith('/End/Content/'):
                    gp = '/Game/' + p[len('/End/Content/'):]
                elif p.startswith('/Engine/Content/'):
                    gp = '/Engine/' + p[len('/Engine/Content/'):]
                elif '/Content/' in p:
                    pre, post = p.split('/Content/', 1)
                    gp = '/' + pre.rstrip('/').split('/')[-1] + '/' + post
                else:
                    continue
                gp = gp.rsplit('.', 1)[0]
                _files.setdefault(gp.split('/')[-1].lower(), []).append((toc, gp))
    return _files


def resolve(z):
    """{import index: object path or None} for package imports; script imports resolved too."""
    paths, _ = scriptobjs.load()
    files = game_files()
    want = {v: k for k, v in enumerate(z.imports) if (v >> 62) == 2}
    out = {}
    for k, v in enumerate(z.imports):
        if (v >> 62) == 1:
            out[k] = paths.get(v)
    names = set(z.names)
    cands = []
    for nm in names:
        for toc, gp in files.get(nm.lower(), []):
            obj = gp + '.' + gp.split('/')[-1]
            cands.append((toc, obj))
    found = {}
    for toc, obj in cands:
        h = scriptobjs.import_hash(obj)
        if h in want:
            found[want[h]] = (obj, toc)
    # subobjects: Package.Object:Sub (names in the name map)
    for k, v in want.items():
        pass
    for v, k in want.items():
        out[k] = found.get(k)
    return out


if __name__ == '__main__':
    z = Zen(open(sys.argv[1], 'rb').read())
    for k, v in sorted(resolve(z).items()):
        print(k, '%016x' % z.imports[k], v)
