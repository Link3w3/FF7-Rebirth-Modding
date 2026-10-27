"""A container with some packages taken out: every chunk of each package named (its export chunk and any bulk chunks)
leaves the table of contents and the header's package store; every other chunk's blocks stay as they are (the .ucas is
the old one plus the new header's blocks: <out>.ucas.tail is what to append to a copy of it). The container keeps its id.
    drop_from_container.py <base .utoc> <out dir (new)> <package path> [...]"""
import hashlib, os, shutil, struct, sys
sys.path[:0] = ['/work/evilboss1016/data', '/work/iostore', '/work/cs', '/work/weap1012/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix']
from iostore import Toc
import iostore_write as W
import hdr
import build_evilcloud_data as BED

MOUNT = BED.MOUNT
BLOCK = BED.BLOCK


def main(base_utoc, out, *packages):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    base_ucas = base_utoc[:-len('.utoc')] + '.ucas'
    old = Toc(base_utoc)
    name = os.path.basename(base_utoc)[:-len('.utoc')]
    heads = [i for i in range(old.entries) if old.chunk_type(i) == 10]
    assert heads == [0], heads
    cid, store = hdr.parse_header(old.read(0))
    order = [old.chunk_id64(i) for i in range(old.entries) if old.chunk_type(i) == 2]
    entries = [dict(id=p, size=store[p]['size'], export_count=store[p]['export_count'], export_bundle_count=store[p]['export_bundle_count'],
                    load_order=store[p]['load_order'], imports=list(store[p]['imports'])) for p in order]
    assert W.container_header(cid, entries) == old.read(0), 'the header does not write back as it is'
    drop_ids = {W.package_id(p): p for p in packages}
    missing = [p for i, p in drop_ids.items() if i not in store]
    assert not missing, ('not in the container', missing)
    drop = sorted(i for i in range(1, old.entries) if old.chunk_id64(i) in drop_ids)
    # what imports them (they then load the game's, or another mod's)
    importers = sorted({'%016x' % e['id'] for e in entries if e['id'] not in drop_ids and any(x in drop_ids for x in e['imports'])})
    keep_entries = [e for e in entries if e['id'] not in drop_ids]
    new_head = W.container_header(cid, keep_entries)
    # the table of contents without them
    b = old.b
    size = os.path.getsize(base_ucas)
    last = old.blocks[-1]
    assert size % 16 == 0 and last[0] + ((last[1] + 15) & ~15) == size, 'the .ucas does not end with its last block'
    blocks = list(old.blocks)
    metas_all = b[old.metas_off:]
    assert len(metas_all) == 33 * old.entries
    tail = bytearray()

    def put(data):
        start = len(blocks) * BLOCK
        for k in range(0, len(data), BLOCK):
            piece = data[k:k + BLOCK]
            blocks.append((size + len(tail), len(piece), len(piece), 0))
            tail.extend(piece)
            while len(tail) % 16:
                tail.append(0)
        return start, len(data)
    ids, offlen, metas, files = [], [], bytearray(), {}
    for i in range(old.entries):
        if i in drop:
            continue
        k = len(ids)
        ids.append(bytes(old.chunk_ids[i]) if isinstance(old.chunk_ids[i], (bytes, bytearray)) else old.chunk_ids[i])
        if i == 0:
            offlen.append(put(new_head))
            metas += hashlib.sha1(new_head).digest() + metas_all[33 * i + 20:33 * i + 33]
        else:
            offlen.append(old.offlen[i])
            metas += metas_all[33 * i:33 * i + 33]
        if i in old.files:
            files[k] = old.files[i]
    dindex = W.directory_index(MOUNT, [(files[i][len(MOUNT):], i) for i in sorted(files)])
    head = bytearray(b[:old.hdrsize])
    struct.pack_into('<I', head, 24, len(ids))
    struct.pack_into('<I', head, 28, len(blocks))
    struct.pack_into('<I', head, 48, len(dindex))
    toc = bytearray(head)
    for x in ids:
        toc += x
    for off, ln in offlen:
        toc += off.to_bytes(5, 'big') + ln.to_bytes(5, 'big')
    for pos, cs, us, m in blocks:
        toc += pos.to_bytes(5, 'little') + cs.to_bytes(3, 'little') + us.to_bytes(3, 'little') + bytes([m])
    toc += dindex + metas
    os.makedirs(out)
    path = os.path.join(out, name)
    open(path + '.utoc', 'wb').write(toc)
    open(path + '.ucas.tail', 'wb').write(tail)
    with open(path + '.ucas', 'wb') as f:
        with open(base_ucas, 'rb') as g:
            shutil.copyfileobj(g, f, 1 << 24)
        f.write(tail)
    shutil.copy(base_utoc[:-len('.utoc')] + '.pak', path + '.pak')
    # read back
    new = Toc(path + '.utoc')
    assert new.container_id == old.container_id and new.entries == old.entries - len(drop)
    k = 0
    for i in range(old.entries):
        if i in drop:
            continue
        data = new.read(k)
        assert data == (new_head if i == 0 else old.read(i)), i
        assert new.chunk_id64(k) == old.chunk_id64(i) and new.chunk_type(k) == old.chunk_type(i)
        assert new.files.get(k) == old.files.get(i), (k, i)
        assert hashlib.sha1(data).digest() == new.b[new.metas_off + 33 * k:new.metas_off + 33 * k + 20], k
        k += 1
    cid2, store2 = hdr.parse_header(new.read(0))
    assert cid2 == cid and set(store2) == {e['id'] for e in keep_entries}
    print('%s: %d chunks out (%s), %d left; imported by %d package(s) left here (they take the game\'s or another mod\'s now); '
          'the .ucas is the old one plus %d bytes' % (name, len(drop), ', '.join(p.rsplit('/', 1)[1] for p in packages), new.entries, len(importers),
                                                      len(tail)))
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        print('  %-48s %10d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], *sys.argv[3:])
