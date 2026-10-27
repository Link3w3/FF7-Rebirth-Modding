"""The new Cloud's mods container CreateACharacterCloud_P (.utoc, .ucas and the empty stub .pak) from make_newcloud.py's
packages, read back after it is written: every chunk's id, type, path and bytes, and every header entry.
    make_container_newcloud.py <make_newcloud out dir> <container out dir> [name]"""
import hashlib, json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, '/work/iostore', '/work/cs', '/work/swap1012/tools']
from iostore import Toc
import iostore_write as W
from hdr import parse_header

MOUNT = '../../../End/Content/'
FIELDS = ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports')


def main(src, out, name='CreateACharacterCloud_P'):
    entries = json.load(open(os.path.join(src, 'entries.json')))['entries']
    # (the voice fix, 2026-10-26) a store entry must not list another voice language's package (/Game/Sound/Voice/US|FR|DE/...,
    # /Game/LipSync/Lsd/US|FR|DE/...): the game's own packs list the JP ones only, and loading every language of Cloud's
    # voice crashed the game. make_newcloud.py's entries take them from the packages' graphs: run
    # ../fixloc/fix_store_imports.py on its out dir first (the game's own store entries, renamed).
    variants = {int(k, 16) for k in json.load(open(os.path.join(HERE, '..', 'fixloc', 'variants.json')))}
    bad = sorted({e['path'] for e in entries if any(x in variants for x in e.get('imports', []))})
    assert not bad, ('store entries list other voice languages\' packages (run fixloc/fix_store_imports.py first)', bad[:5])
    cid = W.container_id_from_name(name)
    header = W.container_header(cid, [{f: e[f] for f in ('id',) + FIELDS} for e in entries])
    chunks = [dict(id64=cid, type=10, data=header, path=None)]
    for e in entries:
        data = open(os.path.join(src, 'pkgs', e['path'].replace('/', '__')), 'rb').read()
        assert hashlib.md5(data).hexdigest() == e['md5'] and len(data) == e['size'], e['path']
        assert W.package_id('/Game/' + e['path'][:-len('.uasset')]) == e['id'], e['path']
        chunks.append(dict(id64=e['id'], type=2, data=data, path=e['path']))
    os.makedirs(out, exist_ok=True)
    base = os.path.join(out, name)
    for ext in ('.utoc', '.ucas', '.pak'):
        assert not os.path.exists(base + ext), base + ext
    W.write_container(base, name, chunks, mount=MOUNT)
    shutil.copyfile(os.path.join(HERE, 'stub.pak'), base + '.pak')

    # read back
    t = Toc(base + '.utoc')
    assert t.entries == len(chunks) and t.container_id == cid
    for i, c in enumerate(chunks):
        assert t.chunk_id64(i) == c['id64'] and t.chunk_type(i) == c['type'], i
        assert t.read(i) == c['data'], ('chunk reads back different', c['path'])
        if c['path']:
            assert t.files.get(i) == MOUNT + c['path'], (i, t.files.get(i), c['path'])
    hcid, hents = parse_header(t.read(0))
    assert hcid == cid and len(hents) == len(entries)
    for e in entries:
        got = hents[e['id']]
        assert all(got[f] == e[f] for f in FIELDS), e['path']
    sums = {ext: hashlib.md5(open(base + ext, 'rb').read()).hexdigest() for ext in ('.utoc', '.ucas', '.pak')}
    for ext, s in sums.items():
        print('%s%s %d bytes md5 %s' % (name, ext, os.path.getsize(base + ext), s))
    print('%d packages, read back the same' % len(entries))
    json.dump(sums, open(base + '.md5.json', 'w'), indent=1)


if __name__ == '__main__':
    main(*sys.argv[1:])
