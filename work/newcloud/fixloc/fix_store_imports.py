"""CLOUD's container packages with the store entries the game's own packages have: each package's imported packages are
those of the game's package it was made from (its container header's store entry), the renamed packages' ids made the
new ones. make_newcloud.py took them from each package's export bundle graph, which also names the other voice
languages' packages (/Game/Sound/Voice/US|FR|DE/..., /Game/LipSync/Lsd/US|FR|DE/...): the game then loaded every
language of Cloud's voice into the one package it plays (the crashes; his voice in another language). The packages
themselves are unchanged (copied).
    fix_store_imports.py <make_newcloud out dir> <new out dir> <vanilla header .bin> [...]"""
import hashlib, json, os, shutil, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools']
import iostore_write as W
from hdr import parse_header


def source_of(path):
    pkg = '/Game/' + path[:-len('.uasset')]
    return pkg.replace('_CACS', '') if '_CACS' in pkg else pkg


def main(src, out, *headers):
    entries = json.load(open(os.path.join(src, 'entries.json')))['entries']
    van = {}
    for f in headers:
        cid, ents = parse_header(open(f, 'rb').read())
        for pid, e in ents.items():
            van.setdefault(pid, []).append(e['imports'])
    pid_map = {}
    for e in entries:
        s = source_of(e['path'])
        if s != '/Game/' + e['path'][:-len('.uasset')]:
            pid_map[W.package_id(s)] = e['id']
    variants = {int(k, 16) for k in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'variants.json')))}
    os.makedirs(os.path.join(out, 'pkgs'), exist_ok=False)
    changed, dropped, added = 0, {}, {}
    new_entries = []
    for e in entries:
        sid = W.package_id(source_of(e['path']))
        lists = van.get(sid)
        assert lists, ('no store entry of the game for', e['path'])
        assert all(sorted(x) == sorted(lists[0]) for x in lists), ('the game\'s containers differ for', e['path'])
        imports = [pid_map.get(x, x) for x in lists[0]]
        assert len(set(imports)) == len(imports), e['path']
        assert not any(x in variants for x in imports), e['path']
        old = set(e['imports'])
        for x in old - set(imports):
            assert x in variants, ('an import dropped that is not another language\'s package', e['path'], '%016x' % x)
            dropped[x] = dropped.get(x, 0) + 1
        for x in set(imports) - old:
            added[x] = added.get(x, 0) + 1
        if sorted(imports) != sorted(e['imports']):
            changed += 1
        new_entries.append(dict(e, imports=imports))
        name = e['path'].replace('/', '__')
        shutil.copyfile(os.path.join(src, 'pkgs', name), os.path.join(out, 'pkgs', name))
        assert hashlib.md5(open(os.path.join(out, 'pkgs', name), 'rb').read()).hexdigest() == e['md5']
    json.dump(dict(entries=new_entries), open(os.path.join(out, 'entries.json'), 'w'), indent=1)
    shutil.copyfile(os.path.join(src, 'report.txt'), os.path.join(out, 'report.txt'))
    print('%d packages, %d store entries changed' % (len(entries), changed))
    print('imports dropped (other languages\' packages):', {'%016x' % k: v for k, v in dropped.items()})
    print('imports added (the game\'s own entries list them):', {'%016x' % k: v for k, v in added.items()})


if __name__ == '__main__':
    main(*sys.argv[1:])
