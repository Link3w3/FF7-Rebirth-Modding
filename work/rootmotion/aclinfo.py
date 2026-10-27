"""Per-track default/constant/animated flags of ACL 1.x compressed clips inside cooked FF7R animation packages."""
import struct, sys, glob, os
TAG10 = struct.pack('<I', 0xac10ac10)
TAG11 = struct.pack('<I', 0xac11ac11)

def bit(bs, i):
    return (bs[i // 32] >> (31 - i % 32)) & 1

def clip_info(d):
    p = d.find(TAG10)
    if p < 0:
        return None
    base = p - 8                     # m_size, m_hash, m_tag
    size, h, tag, ver, typ = struct.unpack_from('<IIIHB', d, base)
    ch = base + 16
    (nb, nseg, rf, tf, sf, crr, srr, has_scale, def_scale, pad, nsamp, rate,
     seg_start, seg_hdr, def_bs, const_bs, const_data, clip_range) = struct.unpack_from('<HHBBBBBBBBIfHHHHHH', d, ch)
    per = 3 if has_scale else 2
    nbits = nb * per
    words = (nbits + 31) // 32
    dbs = struct.unpack_from('<%dI' % words, d, ch + def_bs)
    cbs = struct.unpack_from('<%dI' % words, d, ch + const_bs)
    tracks = []
    for b in range(nb):
        kinds = []
        for s in range(per):
            i = b * per + s
            kinds.append('D' if bit(dbs, i) else ('C' if bit(cbs, i) else 'A'))
        tracks.append(''.join(kinds))
    return dict(size=size, version=ver, bones=nb, samples=nsamp, rate=rate, has_scale=has_scale, tracks=tracks,
                rot_fmt=rf, trans_fmt=tf, const_data=ch + const_data, header=ch, def_bs=def_bs)

if __name__ == '__main__':
    for p in sys.argv[1:]:
        d = open(p, 'rb').read()
        info = clip_info(d)
        name = os.path.basename(p).split('__')[-1].replace('.uasset', '')
        if not info:
            print(name, 'no ACL clip', d.find(TAG11))
            continue
        print('%-22s bones %d samples %d @%.0f  track0 %s  track1 %s  track2 %s' % (name, info['bones'], info['samples'], info['rate'], info['tracks'][0], info['tracks'][1], info['tracks'][2]))


def root_translation_range(d):
    """(min xyz, extent xyz) of track 0's translation when it is animated and clip range reduced, else its kind."""
    info = clip_info(d)
    if not info:
        return None
    ch = info['header']
    (nb, nseg, rf, tf, sf, crr, srr, has_scale, def_scale, pad, nsamp, rate,
     seg_start, seg_hdr, def_bs, const_bs, const_data, clip_range) = struct.unpack_from('<HHBBBBBBBBIfHHHHHH', d, ch)
    kind = info['tracks'][0]
    if kind[1] != 'A':
        return kind, None
    p = ch + clip_range
    # track 0 rotation first, when animated and rotations are range reduced
    if kind[0] == 'A' and (crr & 1):
        p += 2 * (16 if rf == 0 else 12)
    if not (crr & 2):
        return kind, 'no range reduction (fmt %d crr %d)' % (tf, crr)
    mn = struct.unpack_from('<3f', d, p)
    ex = struct.unpack_from('<3f', d, p + 12)
    return kind, (mn, ex)
