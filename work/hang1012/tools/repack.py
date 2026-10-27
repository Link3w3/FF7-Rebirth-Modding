"""Rewrites a mod IoStore container without some packages (or with replaced package data), rebuilding the container
header from the existing store entries. Same container id, mount point and paths.
    repack.py <base path without extension> <output dir> --drop <substring>... """
import hashlib, os, shutil, struct, sys
sys.path.insert(0, '/work/iostore'); sys.path.insert(0, '/work/cs')
from iostore import Toc
import iostore_write as W

def parse_header(h):
    cid, count, zero = struct.unpack_from('<QII', h, 0)
    o = 16
    n = struct.unpack_from('<i', h, o)[0]; names = h[o + 4:o + 4 + n]; o += 4 + n
    n = struct.unpack_from('<i', h, o)[0]; hashes = h[o + 4:o + 4 + n]; o += 4 + n
    count = struct.unpack_from('<i', h, o)[0]; o += 4
    ids = list(struct.unpack_from('<%dQ' % count, h, o)); o += 8 * count
    size = struct.unpack_from('<i', h, o)[0]; o += 4
    base = o
    entries = []
    for k, pid in enumerate(ids):
        e = base + 32 * k
        psize, ec, bc, lo, pad, num, off = struct.unpack_from('<QiiIIII', h, e)
        deps = list(struct.unpack_from('<%dQ' % num, h, e + 24 + off)) if num else []
        entries.append(dict(id=pid, size=psize, export_count=ec, export_bundle_count=bc, load_order=lo, pad=pad, imports=deps))
    rest = h[base + size:]
    return cid, names, hashes, entries, rest

def main():
    src, out_dir = sys.argv[1], sys.argv[2]
    drop = sys.argv[sys.argv.index('--drop') + 1:] if '--drop' in sys.argv else []
    name = os.path.basename(src)
    toc = Toc(src + '.utoc')
    chunks = [dict(id64=toc.chunk_id64(i), type=toc.chunk_type(i), data=toc.read(i), path=toc.files.get(i)) for i in range(toc.entries)]
    hi = next(i for i, c in enumerate(chunks) if c['type'] == 10)
    cid, names, hashes, entries, rest = parse_header(chunks[hi]['data'])
    assert names == b'' and hashes == struct.pack('<Q', 0xC1640000) and rest.strip(b'\0') == b'', 'unexpected header layout'
    # The writer reproduces the header exactly before anything is dropped.
    assert W.container_header(cid, entries) == chunks[hi]['data'][:len(W.container_header(cid, entries))], 'header round trip differs'
    keep, gone = [], []
    for c in chunks:
        if c['type'] != 10 and c['path'] and any(d in c['path'] for d in drop):
            gone.append(c)
        else:
            keep.append(c)
    gone_ids = {W.package_id('/Game/' + c['path'].split('/End/Content/', 1)[1].rsplit('.', 1)[0]) for c in gone}
    entries = [e for e in entries if e['id'] not in gone_ids]
    for e in entries:
        missing = [d for d in e['imports'] if d in gone_ids]
        assert not missing, 'a kept package imports a dropped one'
    header = W.container_header(cid, entries)
    pad = len(chunks[hi]['data']) - len(header)
    for c in keep:
        if c['type'] == 10:
            c['data'] = header + b'\0' * max(pad, 0)
    print('dropped:', [os.path.basename(c['path']) for c in gone])
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, name)
    real = W.container_id_from_name
    W.container_id_from_name = lambda _n: toc.container_id
    mount = '../../../End/Content/'
    for c in keep:
        if c['path']:
            c['path'] = c['path'][len(mount):]
    W.write_container(base, name, keep, mount=mount)
    W.container_id_from_name = real
    shutil.copy(src + '.pak', base + '.pak')
    back = Toc(base + '.utoc')
    assert back.container_id == toc.container_id and back.entries == len(keep)
    for i, c in enumerate(keep):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64']
    bh = parse_header(back.read(next(i for i in range(back.entries) if back.chunk_type(i) == 10)))
    print('packages in header:', len(bh[3]), 'chunks:', back.entries)
    for f in sorted(os.listdir(out_dir)):
        p = os.path.join(out_dir, f)
        print('%-40s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))

if __name__ == '__main__':
    main()
