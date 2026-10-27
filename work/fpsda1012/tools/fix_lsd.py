"""Patch the user's FullyPlayableSephirothDataAssets_P: the Sephiroth packs ask for Cloud's ordinary lip sync
(LSD_PC0000_00_Cloud) instead of LSD_PC0000_02_Cloud_Insanity, which crashes the loader when a CharaSpec pack loads it.
Everything else stays byte for byte; the container keeps the user's header entries (import lists mapped).
    fix_lsd.py <in dir> <out dir>"""
import hashlib, os, shutil, struct, sys
sys.path.insert(0, '/work/seph1012/tools'); sys.path.insert(0, '/work/swap1012/tools')
import build_cos_test as cos
from build_cos_test import W, Zen, Toc, PKG, OBJ
from hdr import parse_header

NAME = 'FullyPlayableSephirothDataAssets_P'
MOUNT = '../../../End/Content/'
OLD, NEW = 'LSD_PC0000_02_Cloud_Insanity', 'LSD_PC0000_00_Cloud'
LSD = '/Game/LipSync/Lsd/%s/Character/Player/%s'

def main():
    src, out = sys.argv[1], sys.argv[2]
    t = Toc(os.path.join(src, NAME + '.utoc'))
    heads = [i for i in range(t.entries) if t.chunk_type(i) == 10]
    assert len(heads) == 1
    _, ents = parse_header(t.read(heads[0]))
    objs = {LSD % ('JP', OLD) + '.' + OLD: LSD % ('JP', NEW) + '.' + NEW}
    pkgs = {LSD % (lang, OLD): LSD % (lang, NEW) for lang in cos.LANGS}
    idmap = {W.package_id(o): W.package_id(n) for o, n in pkgs.items()}
    chunks, entries, patched = [None], [], []
    for i in range(t.entries):
        if t.chunk_type(i) != 2:
            assert t.chunk_type(i) == 10, t.chunk_type(i)
            continue
        path = t.files[i].replace(MOUNT, '', 1)
        pid = t.chunk_id64(i)
        assert pid == W.package_id('/Game/' + path[:-len('.uasset')]), path
        data = t.read(i)
        e = dict(ents[pid])
        names = [OBJ.get(v & ~(3 << 62), '') for v in Zen(data).imports if v != 0xFFFFFFFFFFFFFFFF]
        if any(OLD in n for n in names):
            new, count, missing, swapped, deps = cos.patch_pack(data, objs, pkgs, [])
            assert not missing and count == 1, (path, missing, count)
            assert len(new) == len(data)
            left = [n for n in (OBJ.get(v & ~(3 << 62), '') for v in Zen(new).imports if v != 0xFFFFFFFFFFFFFFFF) if OLD in n]
            assert not left, left
            imports = [idmap.get(x, x) for x in e['imports']]
            assert len(set(imports)) == len(imports)
            assert set(deps) <= set(imports), 'graph package missing from the header entry'
            e['imports'] = imports
            patched.append((path.rsplit('/', 1)[1], sorted(s.split('/')[4] for s in swapped if '/Lsd/' in s)))
            data = new
        chunks.append(dict(id64=pid, type=2, data=data, path=path))
        entries.append(dict(id=pid, size=e['size'], export_count=e['export_count'], export_bundle_count=e['export_bundle_count'],
                            load_order=e['load_order'], imports=e['imports']))
    cid = t.container_id
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    os.makedirs(out, exist_ok=True)
    base = os.path.join(out, NAME)
    W.write_container(base, NAME, chunks, mount=MOUNT)
    if W.container_id_from_name(NAME) != cid:
        # write_container names the container after NAME; keep the user's id if it differs
        raise SystemExit('container id differs from the name-derived one: %x vs %x' % (cid, W.container_id_from_name(NAME)))
    shutil.copy(os.path.join(src, NAME + '.pak'), base + '.pak')
    back = Toc(base + '.utoc')
    assert back.container_id == cid and back.entries == len(chunks)
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        if c['path']: assert back.files.get(i) == MOUNT + c['path']
    _, e2 = parse_header(back.read(0))
    assert set(e2) == {c['id64'] for c in chunks[1:]}
    for name, langs in patched: print('patched', name, 'lip sync ->', NEW, langs)
    print(len(chunks) - 1, 'packages,', len(patched), 'patched')
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        print('%-44s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))

if __name__ == '__main__':
    main()
