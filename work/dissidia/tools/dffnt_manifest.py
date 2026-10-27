"""Reads the Dissidia NT package table that Cethleann's DataExporter wrote with --yshtola-manifest-only
(manifest-COMMON.dissidiant: the decrypted PKGINFO = RESPACK(... BTIF ...), laid out as in Cethleann's
Cethleann.Archive.PKGINFO / BTIF / Cethleann.Pack.RESPACK and Cethleann.Structure.Archive.BTIFHeader / BTIFEntry).
The table here is an IDTable (Cethleann.Structure.Archive.IDTableHeader / IDTableEntry). Writes a CSV of every
entry: index, original name, path on disk, packed and unpacked size, flags, unique id.
    dffnt_manifest.py <manifest file> <game dir> <out csv>"""
import csv
import os
import struct
import sys
from collections import Counter

FLAGS = {0x80000000: 'Encrypted', 0x40000000: 'Compressed', 0x20000000: 'Streamed'}


def read_string(b, p):
    e = b.index(b'\0', p)
    return b[p:e].decode('utf-8', 'replace')


def main(manifest, game, out_csv):
    b = open(manifest, 'rb').read()
    # IDTableHeader {Offset, Count, Block, Padding}, then IDTableEntry[Count] {PathOffset, OriginalPathOffset, Flags,
    # UniqueId, CompressedSize, DecompressedSize, Padding1, Padding2}; names at Offset + (Original)PathOffset
    off, count, block, pad = struct.unpack_from('<iiII', b, 0)
    print('IDTable offset %d entries %d block %d' % (off, count, block))
    rows = []
    for i in range(count):
        po, opo, flags, uid, csize, dsize, p1, p2 = struct.unpack_from('<iiIIIIII', b, 16 + 32 * i)
        path = read_string(b, off + po)
        orig = read_string(b, off + opo) if opo > -1 else ''
        disk = os.path.join(game, path.replace('\\', '/'))
        exists = os.path.exists(disk)
        rows.append(dict(index=i, original=orig, path=path, csize=csize, dsize=dsize,
                         flags='|'.join(v for k, v in FLAGS.items() if flags & k) or '%x' % flags,
                         uid='%08x' % uid, p1=p1, p2=p2, exists=int(exists),
                         disk_size=os.path.getsize(disk) if exists else -1))
    with open(out_csv, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print('%d entries; on disk %d; packed %.2f GB; unpacked %.2f GB' % (
        len(rows), sum(r['exists'] for r in rows), sum(r['csize'] for r in rows) / 1e9, sum(r['dsize'] for r in rows) / 1e9))
    ext = Counter(os.path.splitext(r['original'])[1].lower() for r in rows)
    print('extensions:', ', '.join('%s:%d' % kv for kv in ext.most_common(40)))
    top = Counter(r['original'].replace('\\', '/').split('/')[0] for r in rows)
    print('top folders:', ', '.join('%s:%d' % kv for kv in top.most_common(40)))
    for r in rows[:12]:
        print(r)


if __name__ == '__main__':
    main(*sys.argv[1:4])
