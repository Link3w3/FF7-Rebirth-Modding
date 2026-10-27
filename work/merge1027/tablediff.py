"""Rows a container's table adds or changes against the game's, and the fields each change touches.
    tablediff.py <game table .uasset> <mod table .uasset> [json out]"""
import sys, contextlib, io, json
sys.path[:0]=['/work/sephatb/tools','/work/iostore','/work/cs','/work/tools','/work/evil1013/tools','/work/swap1012/tools','/work/vincentfix','/work/weap1012/tools']
import build_atb as B

def T(p):
    with contextlib.redirect_stdout(io.StringIO()):
        return B.Table(open(p,'rb').read())

def jsonable(v):
    if isinstance(v, bytes): return v.hex()
    if isinstance(v, (list, tuple)): return [jsonable(x) for x in v]
    return v

def diff(van_path, mod_path):
    van, mod = T(van_path), T(mod_path)
    fields = [f[0][0] for f in van.fields]
    assert fields == [f[0][0] for f in mod.fields], 'fields differ'
    added = [k for k in mod.at if k not in van.at]
    removed = [k for k in van.at if k not in mod.at]
    changed = {}
    for k in mod.at:
        if k in van.at and mod.row(k) != van.row(k):
            a, b = van.row(k), mod.row(k)
            changed[k] = {f: [jsonable(van.get(a, f)), jsonable(mod.get(b, f))] for f in fields if van.get(a, f) != mod.get(b, f)}
    return dict(fields=fields, added=added, removed=removed, changed=changed)

if __name__ == '__main__':
    d = diff(sys.argv[1], sys.argv[2])
    if len(sys.argv) > 3:
        json.dump(d, open(sys.argv[3], 'w'), indent=1, ensure_ascii=False)
    print('added %d, changed %d, removed %d' % (len(d['added']), len(d['changed']), len(d['removed'])))
