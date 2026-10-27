"""For every package of the new Cloud's container (make_newcloud.py's entries.json): its store entry's imported packages
against the game's own store entry of the package it was made from (the vanilla container headers), with the renamed
packages' ids made new. Prints what differs.
    compare_imports.py <entries.json> <vanilla header .bin> [...]"""
import json, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools']
import iostore_write as W
from hdr import parse_header

SUFFIX = '_CACS'


def source_of(path):
    """Game-relative path of a new package (DataAsset/.../X_CACS....uasset) -> the game's package it was made from."""
    pkg = '/Game/' + path[:-len('.uasset')]
    if '_CACS' not in pkg:
        return pkg
    return pkg.replace('_CACS', '')


entries = json.load(open(sys.argv[1]))['entries']
van = {}
for f in sys.argv[2:]:
    cid, ents = parse_header(open(f, 'rb').read())
    for pid, e in ents.items():
        van.setdefault(pid, []).append((f, e))
mine = {e['id'] for e in entries}
pid_map = {}
for e in entries:
    src = source_of(e['path'])
    if src != '/Game/' + e['path'][:-len('.uasset')]:
        pid_map[W.package_id(src)] = e['id']
langs = ['US', 'JP', 'FR', 'DE', 'ES', 'IT', 'KO', 'CN', 'TW', 'BR']
same = diff = missing = 0
extra_all = {}
for e in entries:
    src = source_of(e['path'])
    sid = W.package_id(src)
    v = van.get(sid)
    if not v:
        missing += 1
        print('NO VANILLA ENTRY', e['path'])
        continue
    imps = [set(x['imports']) for _, x in v]
    if any(i != imps[0] for i in imps):
        print('vanilla entries differ between containers for', src)
    want = sorted(pid_map.get(x, x) for x in v[0][1]['imports'])
    have = sorted(e['imports'])
    if want == have:
        same += 1
        continue
    diff += 1
    extra = sorted(set(have) - set(want))
    lack = sorted(set(want) - set(have))
    for x in extra:
        extra_all[x] = extra_all.get(x, 0) + 1
    if diff <= 5:
        print('DIFF', e['path'], 'extra', ['%016x' % x for x in extra], 'lacking', ['%016x' % x for x in lack])
print('same', same, 'differ', diff, 'no vanilla entry', missing)
print('extra ids over all packages:')
for x, n in sorted(extra_all.items(), key=lambda kv: -kv[1]):
    print('  %016x in %d package(s)' % (x, n))
