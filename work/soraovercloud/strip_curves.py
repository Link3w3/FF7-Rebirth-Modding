"""Take the animation curves off Sora's animations in a container, in their cooked packages (no editor), so each one is laid
out like his animations that play without trouble (every one of the earlier ones has no curves):

  * the memory-mapped block (a header, two self-relative pointers {offset << 1 | 1, count, max} to the bone bytes and the
    curve bytes, 16 marker bytes, the bone bytes, the curve bytes, each padded to 16): the curve pointer nulled, the curve
    bytes dropped and the block's size set again;
  * the compressed curve names (FSmartName list after the track map): none.

Why: Copy Notifies Onto gave the area actions and event animations Cloud's curves (AutoSaccadeX/Y, Attach_Item), whose names
Sora's game skeleton does not have, and the game read past the end of a buffer on them (EXCEPTION_ACCESS_VIOLATION at
ff7rebirth_+0x17eadcb from +0x144d392, opening a door, twice). The End editor kept the curves in its cooks after they were
gone from the raw data (its derived data cache key did not change), so they come off here.

    strip_curves.py <in .utoc> <out dir (new)> <name> [path substring ...]   (default: every animation with curves)
"""
import hashlib, os, shutil, struct, sys
sys.path[:0] = ['/work/soraovercloud', '/work/soradata', '/work/iostore', '/work/cs',
                '/work/swap1012/tools', '/work/sephforms/tools', '/work/fx1018/editor/Python']
import build_sora_assets as B
from build_sora_assets import A, W, hdr, Toc, Zen, Package
from rebirth_fx import matcore
import build_overcloud as O
import sync_settings as S
import anim_curves


def padded(n):
    return n + (16 - n % 16) % 16 if n > 0 else 0


def strip(data, label):
    """(package bytes without curves, number of curves taken off); the input itself when it has none."""
    si, sv, ex = S.anim_export(data, label)
    q = sv.size + 4 + 16                                  # guid flag, SkeletonGuid
    frozen, tag = struct.unpack_from('<II', ex, q)
    align, pad = struct.unpack_from('<HH', ex, q + 8)
    assert tag == 0x10000 and align == 16, (label, tag, align)
    P = q + 12 + pad                                      # the block (its pointers)
    o1, c1, m1, o2, c2, m2 = struct.unpack_from('<QiiQii', ex, P)
    assert o1 == (48 << 1) | 1 and c1 == m1 and frozen == 48 + padded(c1) + padded(c2), (label, o1, c1, m1, frozen, c2)
    e = P + frozen
    n1, n2, n3 = struct.unpack_from('<III', ex, e)
    assert (n1, n2, n3) == (0, 0, 0), (label, 'fixups')
    t = e + 12
    t += 2                                                # FStripDataFlags
    bser, = struct.unpack_from('<I', ex, t); t += 4
    assert bser, label
    t += 4                                                # CompressedRawDataSize
    nt, = struct.unpack_from('<i', ex, t); t += 4 + 4 * nt
    nc_at = t
    nc, = struct.unpack_from('<i', ex, t)
    if nc == 0 and c2 == 0:
        return data, 0
    assert c2 > 0 and o2 == ((48 + padded(c1) - 16) << 1) | 1 and c2 == m2, (label, o2, c2, m2)   # (self-relative, from the curve pointer)
    new = bytearray(ex[:P])
    new += struct.pack('<QiiQii', o1, c1, m1, 0, 0, 0)
    new += ex[P + 32:P + 48 + padded(c1)]                 # marker, bone bytes
    struct.pack_into('<I', new, q, 48 + padded(c1))       # the block's size
    # (the export's zero padding after what the game reads goes too: realign pads it again for its new length)
    z0 = Zen(data)
    s0, e0 = [(s_, e_) for i_, s_, e_ in A.export_spans(data, z0) if i_ == si][0]
    used, _ = B.anim_consumes(Package(data, label), data, si, s0, e0)
    assert used is not None and not any(ex[used:]), (label, 'bytes after what the game reads')
    new += ex[e:nc_at] + struct.pack('<i', 0) + ex[nc_at + 4 + 8 * nc:used]
    out = matcore.replace_export(O.no_pad(data), si, bytes(new))
    out = A.realign(out)
    # checks: no curves now, the bone bytes and everything else as they were
    r = anim_curves.curves(out, label)
    assert r is not None and r[1] == [] and r[0] == 48 + padded(c1), (label, r)
    ni, nv, nex = S.anim_export(out, label)
    assert nex[:nv.size] == ex[:sv.size], label
    np_ = nv.size + 4 + 16 + 12 + pad
    assert nex[np_ + 32:np_ + 48 + padded(c1)] == ex[P + 32:P + 48 + padded(c1)], label
    zs, zo = Zen(data), Zen(out)
    assert zo.names == zs.names and zo.imports == zs.imports and len(zo.exports) == len(zs.exports), label
    ps, po = zs.bundle_positions(), zo.bundle_positions()
    for j in range(len(zs.exports)):
        if j != si:
            a, b = data[ps[j][0]:ps[j][0] + ps[j][1]], out[po[j][0]:po[j][0] + po[j][1]]
            assert b[:len(a)] == a and not any(b[len(a):]), (label, j)
    assert B.verify_anim(out, label, need_block=True) >= 1, label
    return out, nc


def main(in_utoc, out, name, *subs):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    chunks, store = B.read(in_utoc)
    entries, done, total = [], [], 0
    for c in chunks:
        if c['type'] != 2:
            continue
        e = B.entry(c, store[c['id64']])
        if Zen(c['data']).flags & A.PKG_ALIGNED_EXPORTS and (not subs or any(s in c['path'] for s in subs)):
            try:
                S.anim_export(c['data'], c['path'])
                is_seq = True
            except AssertionError:
                is_seq = False
            if is_seq:
                new, n = strip(c['data'], c['path'])
                if n:
                    c['data'] = new
                    e['size'] = len(new) | (A.SHIFT << 60)
                    done.append(c['path'])
                    total += n
        entries.append(e)
    os.makedirs(out)
    cid = W.container_id_from_name(name)
    allc = [dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)] + chunks
    base = os.path.join(out, name)
    W.write_container(base, name, allc, mount=B.MOUNT)
    shutil.copy(in_utoc[:-5] + '.pak', base + '.pak')
    back = Toc(base + '.utoc')
    assert back.entries == len(allc)
    cid2, ents = hdr.parse_header(back.read(0))
    by = {e['id']: e for e in entries}
    for i in range(1, back.entries):
        c = allc[i]
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'], c['path']
        if c['type'] == 2:
            e, b = by[c['id64']], ents[c['id64']]
            assert (b['size'], b['export_count'], b['export_bundle_count'], b['load_order'], list(b['imports'])) == \
                   (e['size'], e['export_count'], e['export_bundle_count'], e['load_order'], e['imports']), c['path']
    files = {}
    for ext in ('utoc', 'ucas', 'pak'):
        p = base + '.' + ext
        files[ext] = (os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest())
    return dict(stripped=len(done), curves=total, files=files)


if __name__ == '__main__':
    print(main(*sys.argv[1:]))
