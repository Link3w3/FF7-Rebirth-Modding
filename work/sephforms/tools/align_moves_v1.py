"""Lay out moves packaged by the End editor the way FINAL FANTASY VII REBIRTH lays out its own animations.

The game reads an animation's ACL data in place (a memory-mapped block inside the export), so its cooker:
  - pads every export of an animation package to 16 bytes and puts it at a 16-aligned cooked offset,
  - flags the package PKG_Cooked (0x200) as well as 0x800000 (aligned exports),
  - stores the alignment as a shift (4 = 16 bytes) in the top 4 bits of the package's ExportBundlesSize in the
    container header.
After each export the game's loader (FAsyncPackage2, ff7rebirth_.exe 0x9219b9) skips to the next aligned cooked
offset, but only when the package has both flags; the shift comes from the store entry (0x9eabd7).

The editor writes an animation export already padded to 16 bytes, but without PKG_Cooked and with shift 0. The game then
does not skip the padding, the next export starts inside it, reads garbage and runs off the end of the package (the
fatal error of 2026-10-13 17:54: B_DmgDownB01_2, export 3 EndAnimNotifyBattleStateChange_0). This tool rewrites each
package (header end aligned, every export padded and at an aligned cooked offset, PKG_Cooked) and the container header
(shift 4), and checks every export against an emulation of the game's reader.

    align_moves.py <in.utoc> <out folder> <out name> [<in .pak stub>]
"""
import os, shutil, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools', HERE]
from iostore import Toc
from zen import Zen
import iostore_write as W
import hdr

ALIGN = 16
SHIFT = 4
PKG_COOKED = 0x200
PKG_ALIGNED_EXPORTS = 0x800000
SKELETON_GUID_LEN = 16


def align_up(v, a=ALIGN):
    return -(-v // a) * a


def export_spans(d, z):
    """[(export index, start, end)] in export bundle serialize order (the order of the export data)."""
    region = d[z.eb_off:z.graph_off]
    n = len(z.exports)
    for nb in range(1, 9):
        hdrs = [struct.unpack_from('<II', region, 8 * i) for i in range(nb)]
        total = sum(c for f, c in hdrs)
        if 8 * nb + 8 * total == len(region):
            break
    else:
        raise ValueError('export bundles do not parse')
    ents = [struct.unpack_from('<II', region, 8 * nb + 8 * i) for i in range(total)]
    order = [ents[k][0] for f, c in hdrs for k in range(f, f + c) if ents[k][1] == 1]
    assert sorted(order) == list(range(n)), order
    p = z.header_end
    spans = []
    for idx in order:
        size = z.exports[idx]['serial_size']
        spans.append((idx, p, p + size))
        p += size
    assert p == len(d), (p, len(d))
    return spans


# ---------------------------------------------------------------- what the game reads of each export
def fname(z, d, p):
    idx, num = struct.unpack_from('<Ii', d, p)
    return z.names[idx & 0x3fffffff], p + 8


def tagged_end(z, d, p, end):
    """End of a tagged property stream (after its None), as UE 4.26's FPropertyTag reader walks it."""
    while True:
        assert p + 8 <= end, 'tagged properties run past the export'
        name, p = fname(z, d, p)
        if name == 'None':
            return p
        typ, p = fname(z, d, p)
        size, _ = struct.unpack_from('<ii', d, p); p += 8
        if typ == 'StructProperty':
            p += 8 + 16
        elif typ == 'BoolProperty':
            p += 1
        elif typ in ('ByteProperty', 'EnumProperty', 'ArrayProperty', 'SetProperty'):
            p += 8
        elif typ == 'MapProperty':
            p += 16
        if d[p]:
            p += 16
        p += 1 + size


def game_consumes(z, d, idx, s, e):
    """Bytes the game's Serialize reads of this export (and, for an animation, where its ACL block sits)."""
    p = tagged_end(z, d, s, e) + 4                         # + UObject guid flag
    name = z.exports[idx]['name']
    if not (name.startswith('B_') or name.startswith('N_') or name.startswith('F_')):
        return p - s, None
    p += SKELETON_GUID_LEN                                 # UAnimationAsset: SkeletonGuid
    size, = struct.unpack_from('<I', d, p); p += 4         # ff7rebirth 0x7bc124: memory-mapped block
    block = None
    if size:
        tag, = struct.unpack_from('<I', d, p); p += 4
        if tag > 0xffff:
            _align, pad = struct.unpack_from('<HH', d, p); p += 4 + pad
        block = p
        p += size
        n1, n2, n3 = struct.unpack_from('<III', d, p); p += 12   # 0xc22f50: fixups
        for _ in range(n1):
            p += 8; cnt, = struct.unpack_from('<I', d, p); p += 4 + 8 * cnt
        for _ in range(n2 + n3):
            p += 8; cnt, = struct.unpack_from('<I', d, p); p += 4 + 4 * cnt
    p += 2                                                 # FStripDataFlags
    bser, = struct.unpack_from('<I', d, p); p += 4         # bSerializeCompressedData
    if bser:
        p += 4                                             # CompressedRawDataSize (0x7bc7fc)
        ntracks, = struct.unpack_from('<i', d, p); p += 4 + 4 * ntracks
        ncurves, = struct.unpack_from('<i', d, p); p += 4 + 8 * ncurves
        p += 4                                             # codec data: CompressedNumberOfFrames
        p += 4                                             # bUseRawDataOnly
    assert p <= e, ('reads past the export', name, p - e)
    return p - s, block


# ---------------------------------------------------------------- the rewrite
def realign(d):
    z = Zen(d)
    assert z.flags & PKG_ALIGNED_EXPORTS, 'not an aligned-export (animation) package: %08x' % z.flags
    spans = export_spans(d, z)
    pad_header = (-(z.graph_off + z.graph_size)) % ALIGN
    graph_off = z.graph_off + pad_header
    header = bytearray(d[:z.graph_off]) + b'\0' * pad_header + d[z.graph_off:z.graph_off + z.graph_size]
    real = {idx: e - s for idx, s, e in spans}
    padded = {idx: align_up(n) for idx, n in real.items()}
    first = align_up(z.cooked_header_size)
    offsets, off = {}, first
    for i in range(len(z.exports)):
        offsets[i] = off
        off += padded[i]
    body = bytearray()
    for idx, s, e in spans:
        body += d[s:e] + b'\0' * (padded[idx] - real[idx])
    struct.pack_into('<I', header, 16, z.flags | PKG_COOKED)
    struct.pack_into('<I', header, 20, first)               # CookedHeaderSize
    struct.pack_into('<i', header, 52, graph_off)           # GraphDataOffset
    for i in range(len(z.exports)):
        struct.pack_into('<QQ', header, z.exp_off + 72 * i, offsets[i], padded[i])
    return bytes(header) + bytes(body)


def verify(d, label):
    """Emulate the game's loader over the rewritten package: each export from where the previous one ended, aligned."""
    z = Zen(d)
    assert z.flags & PKG_COOKED and z.flags & PKG_ALIGNED_EXPORTS, label
    assert z.header_end % ALIGN == 0, label
    spans = export_spans(d, z)
    pos = z.header_end
    blocks = 0
    for idx, s, e in spans:
        assert pos == s, (label, 'export %d starts at %d, the game reads it from %d' % (idx, s, pos))
        ex = z.exports[idx]
        assert ex['serial_offset'] % ALIGN == 0 and ex['serial_size'] % ALIGN == 0, (label, idx)
        used, block = game_consumes(z, d, idx, s, e)
        cooked = ex['serial_offset'] + used
        pos = s + (align_up(cooked) - ex['serial_offset'])   # ff7rebirth 0x9219b9
        if block is not None:
            assert block % ALIGN == 0, (label, 'ACL block not 16-aligned in memory', block)
            blocks += 1
    assert pos == len(d), (label, pos, len(d))
    return blocks


def main():
    in_utoc, out_dir, out_name = sys.argv[1:4]
    pak_stub = sys.argv[4] if len(sys.argv) > 4 else in_utoc[:-5] + '.pak'
    src = Toc(in_utoc)
    header_chunk = [i for i in range(src.entries) if src.chunk_type(i) == 10]
    assert len(header_chunk) == 1
    _, store = hdr.parse_header(src.read(header_chunk[0]))
    mount = '../../../End/Content/'
    chunks = [None]
    entries = []
    blocks = 0
    for i in range(src.entries):
        if src.chunk_type(i) == 10:
            continue
        assert src.chunk_type(i) == 2, ('unexpected chunk type', src.chunk_type(i))
        pid = src.chunk_id64(i)
        path = src.files[i]
        assert path.startswith(mount), path
        new = realign(src.read(i))
        blocks += verify(new, path)
        se = store[pid]
        assert se['size'] >> 60 == 0, path
        chunks.append(dict(id64=pid, type=2, data=new, path=path[len(mount):]))
        entries.append(dict(id=pid, size=len(new) | (SHIFT << 60), export_count=se['export_count'],
                            export_bundle_count=se['export_bundle_count'], load_order=se['load_order'], imports=se['imports']))
    cid = W.container_id_from_name(out_name)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, out_name)
    W.write_container(base, out_name, chunks, mount=mount)
    shutil.copy(pak_stub, base + '.pak')
    # read everything back
    back = Toc(base + '.utoc')
    assert back.entries == len(chunks)
    _, ents = hdr.parse_header(back.read(0))
    for i in range(1, back.entries):
        c = chunks[i]
        data = back.read(i)
        assert data == c['data'] and back.chunk_id64(i) == c['id64'] and back.files.get(i) == mount + c['path']
        assert ents[c['id64']]['size'] == len(data) | (SHIFT << 60)
        verify(data, c['path'])
    print('%d packages laid out like the game\'s (PKG_Cooked, 16-byte exports, shift %d); %d ACL blocks 16-aligned; container %s (%016x)'
          % (len(chunks) - 1, SHIFT, blocks, out_name, cid))


if __name__ == '__main__':
    main()
