"""SoraAssets_P with some of its packages replaced by new cooks of the same packages (cooked by the End editor, converted
to zen by retoc), each made ready the way build_sora_assets.main makes animation packages ready (realigned, its reads and
ACL blocks checked); everything else exactly as it was. Read back chunk by chunk.

    replace_packages.py <SoraAssets_P.utoc> <retoc .utoc with the new cooks> <out dir> [name]"""
import hashlib, os, shutil, sys
sys.path[:0] = ['/work/soradata', '/work/iostore', '/work/cs', '/work/swap1012/tools',
                '/work/sephforms/tools', '/work/shooter1016/tools', '/work/fx1018/editor/Python']
import build_sora_assets as B
from build_sora_assets import A, W, hdr, Toc, Zen, Package


def main(base_utoc, new_utoc, out, name='SoraAssets_P'):
    chunks, store = B.read(base_utoc)
    new_chunks, new_store = B.read(new_utoc)
    by_id = {(c['id64'], c['type']): c for c in chunks}
    report = []
    replaced = {}
    for c in new_chunks:
        if c['type'] != 2:
            raise ValueError('%s: only packages without bulk data here' % c['path'])
        old = by_id.get((c['id64'], 2))
        if old is None or old['path'] != c['path']:
            raise ValueError('%s is not in %s' % (c['path'], base_utoc))
        e = B.entry(c, new_store[c['id64']])
        data = c['data']
        z = Zen(data)
        blocks = None
        if z.flags & A.PKG_ALIGNED_EXPORTS:
            data = A.realign(data)
            blocks = B.verify_anim(data, c['path'], need_block=False)
            if any(cls == 'AnimSequence' for cls, v, b in Package(data, c['path']).exports.values()):
                assert blocks >= 1, (c['path'], 'no ACL block')
            e['size'] = len(data) | (A.SHIFT << 60)
        oe = store[c['id64']]
        assert list(e['imports']) == list(oe['imports']), (c['path'], 'imports changed')
        e['load_order'] = oe['load_order']
        replaced[c['id64']] = (data, e)
        report.append((c['path'], len(old['data']), len(data), blocks))
    entries = []
    for c in chunks:
        if c['type'] == 2:
            if c['id64'] in replaced:
                c['data'], e = replaced[c['id64']]
            else:
                e = B.entry(c, store[c['id64']])
            entries.append(e)
    os.makedirs(out, exist_ok=True)
    cid = W.container_id_from_name(name)
    allc = [dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)] + chunks
    base = os.path.join(out, name)
    W.write_container(base, name, allc, mount=B.MOUNT)
    shutil.copy(base_utoc[:-5] + '.pak', base + '.pak')
    back = Toc(base + '.utoc')
    assert back.entries == len(allc)
    cid2, ents = hdr.parse_header(back.read(0))
    assert cid2 == cid and len(ents) == len(entries)
    by = {e['id']: e for e in entries}
    for i in range(1, back.entries):
        c = allc[i]
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type'], c['path']
        assert back.files.get(i) == B.MOUNT + c['path'], c['path']
        if c['type'] == 2:
            e, b = by[c['id64']], ents[c['id64']]
            assert (b['size'], b['export_count'], b['export_bundle_count'], b['load_order'], list(b['imports'])) == \
                   (e['size'], e['export_count'], e['export_bundle_count'], e['load_order'], e['imports']), c['path']
    # the packages not replaced are byte for byte the base container's
    base_back = Toc(base_utoc)
    old_data = {(base_back.chunk_id64(i), base_back.chunk_type(i)): i for i in range(1, base_back.entries)}
    same = 0
    for i in range(1, back.entries):
        key = (back.chunk_id64(i), back.chunk_type(i))
        if key[0] in replaced and key[1] == 2:
            continue
        assert back.read(i) == base_back.read(old_data[key]), back.files.get(i)
        same += 1
    for r in report:
        print('replaced %-75s %7d -> %7d bytes, ACL blocks %s' % r)
    print('unchanged chunks:', same)
    for ext in ('utoc', 'ucas', 'pak'):
        p = base + '.' + ext
        print('%-22s %10d %s' % (os.path.basename(p), os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:5])
