"""FF7 Remake (UE 4.18 SQEX) cooked AnimSequence and Skeleton reading; the game compresses its animations with the
Animation Compression Library (ACL 1.x, compressed clip format version 3, uniformly sampled), decoded here with numpy.

    skeleton(path)  -> dict(names, parents, poses[(qx,qy,qz,qw, tx,ty,tz, sx,sy,sz)])   (the USkeleton's reference skeleton)
    read(path)      -> dict(props, key_encoding, track_map, curves, acl)                  (one AnimSequence)
    acl_decode(buf) -> dict(num_samples, sample_rate, rot[B,S,4], trans[B,S,3], scale[B,S,3] or None, ...)"""
import sys, os, struct, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkg418, uprops, skm
from binr import B
from schema import Schema

_S = None


def schema():
    global _S
    if _S is None:
        _S = Schema()
    return _S


def skeleton(path):
    p = pkg418.Package(path)
    k = next(i for i, e in enumerate(p.exports) if p.classname(e) == 'Skeleton')
    cls, V, end = uprops.read_export(schema(), p, k)
    e = p.exports[k]
    r = B(p.d, end, p.names, e['off'] + e['size'])
    if r.i32():
        r.raw(16)     # (UObject: a GUID mapped to it)
    ref = skm.ref_skeleton(r)
    return dict(names=[b[0] for b in ref['bones']], parents=[b[1] for b in ref['bones']], poses=ref['poses'],
                props=V.py())


def read(path):
    p = pkg418.Package(path)
    k = next(i for i, e in enumerate(p.exports) if p.classname(e) in ('AnimSequence',))
    cls, V, end = uprops.read_export(schema(), p, k)
    e = p.exports[k]
    stop = e['off'] + e['size']
    r = uprops.Reader(schema(), p.names, p.d, end, stop)
    out = {'name': e['name'], 'props': V.py()}
    if r.i32():
        r.raw(16)                    # (UObject: a GUID mapped to it)
    out['skeleton_guid'] = r.raw(16).hex()
    out['strip'] = r.raw(2)
    out['compressed'] = r.i32()      # (bSerializeCompressedData)
    if not out['compressed']:
        raise ValueError('%s: no compressed data' % path)
    kef = r.raw(4)                   # key encoding, translation / rotation / scale compression formats
    out['key_encoding'] = list(kef)
    out['track_offsets'] = [r.i32() for _ in range(r.i32())]
    out['scale_offsets'] = [r.i32() for _ in range(r.i32())]
    out['scale_strip'] = r.i32()
    out['track_map'] = [r.i32() for _ in range(r.i32())]
    curves = r.struct('RawCurveTracks').py()
    fc = curves.get('FloatCurves') if isinstance(curves, dict) else None
    out['curves'] = fc if isinstance(fc, list) else []     # (an empty array reads as a zero property)
    out['raw_size'] = r.i32()        # (CompressedRawDataSize)
    n = r.i32()
    out['acl'] = bytes(p.d[r.p:r.p + n])
    r.p += n
    out['use_raw_only'] = r.i32() if r.p + 4 <= stop else None
    out['tail'] = stop - r.p
    return out


# ---- ACL 1.x (compressed clip version 3), uniformly sampled ---------------------------------------------------------
NUM_BITS = [0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 32]   # by bit rate
ROT_QUAT_128, ROT_DROPW_96, ROT_DROPW_48, ROT_DROPW_32, ROT_DROPW_VAR = range(5)
VEC_96, VEC_48, VEC_32, VEC_VAR = range(4)
RR_ROT, RR_TRANS, RR_SCALE = 1, 2, 4


class Bits:
    """ACL's packed bits: most significant bit first"""
    def __init__(self, data):
        self.b = np.unpackbits(np.frombuffer(data, np.uint8))

    def uint(self, offset, n):
        v = 0
        for bit in self.b[offset:offset + n]:
            v = (v << 1) | int(bit)
        return v


def _bitset(words, i):
    return (words[i // 32] >> (31 - i % 32)) & 1


def acl_decode(buf):
    u16 = lambda o: struct.unpack_from('<H', buf, o)[0]
    u32 = lambda o: struct.unpack_from('<I', buf, o)[0]
    size, hsh, tag, version, algo = struct.unpack_from('<IIIHB', buf, 0)
    if tag != 0xac10ac10:
        raise ValueError('not an ACL compressed clip (tag %08x)' % tag)
    if version != 3 or algo != 0:
        raise NotImplementedError('ACL clip version %d algorithm %d' % (version, algo))
    H = 16
    num_bones, num_segments = u16(H), u16(H + 2)
    rot_fmt, trans_fmt, scale_fmt, clip_rr, seg_rr, has_scale, default_scale = buf[H + 4:H + 11]
    num_samples, sample_rate = u32(H + 12), u32(H + 16)
    seg_off, default_off, constant_off, const_data_off, clip_range_off = (u16(H + 20 + 2 * i) for i in range(5))
    tracks_per_bone = 3 if has_scale else 2
    num_tracks = num_bones * tracks_per_bone
    nwords = (num_tracks + 31) // 32
    default_bits = struct.unpack_from('<%dI' % nwords, buf, H + default_off)
    constant_bits = struct.unpack_from('<%dI' % nwords, buf, H + constant_off)
    kinds = []      # per track: 'default' / 'constant' / 'animated'
    for t in range(num_tracks):
        kinds.append('default' if _bitset(default_bits, t) else 'constant' if _bitset(constant_bits, t) else 'animated')
    drop_w = rot_fmt != ROT_QUAT_128
    rot_comp = 3 if drop_w else 4

    def comps(t):
        return rot_comp if t % tracks_per_bone == 0 else 3

    def rr_flag(t):
        return (RR_ROT, RR_TRANS, RR_SCALE)[t % tracks_per_bone]

    # constant track values (full precision)
    const = {}
    o = H + const_data_off
    for t in range(num_tracks):
        if kinds[t] == 'constant':
            n = comps(t)
            const[t] = np.array(struct.unpack_from('<%df' % n, buf, o), np.float64)
            o += 4 * n
    # clip range data: min and extent per animated, range-reduced track
    clip_range = {}
    o = H + clip_range_off
    for t in range(num_tracks):
        if kinds[t] == 'animated' and clip_rr & rr_flag(t):
            n = comps(t)
            v = struct.unpack_from('<%df' % (2 * n), buf, o)
            clip_range[t] = (np.array(v[:n], np.float64), np.array(v[n:], np.float64))
            o += 8 * n
    animated = [t for t in range(num_tracks) if kinds[t] == 'animated']
    fmt_of = lambda t: rot_fmt if t % tracks_per_bone == 0 else (trans_fmt if t % tracks_per_bone == 1 else scale_fmt)
    values = {t: np.zeros((num_samples, comps(t))) for t in animated}
    sample0 = 0
    segments = []
    for s in range(num_segments):
        so = H + seg_off + 20 * s
        seg_samples, pose_bits, fmt_off, range_off, data_off = struct.unpack_from('<IIIII', buf, so)
        segments.append((seg_samples, pose_bits))
        rates = {}
        k = 0
        for t in animated:
            if fmt_of(t) in (ROT_DROPW_VAR, VEC_VAR) and (t % tracks_per_bone != 0 or fmt_of(t) == ROT_DROPW_VAR):
                rates[t] = buf[H + fmt_off + k]
                k += 1
        # segment range data: per animated, range-reduced track, 8 bits a component (min, then extent)
        seg_range = {}
        if seg_rr and range_off != 0xffffffff:
            ro = H + range_off
            for t in animated:
                if seg_rr & rr_flag(t):
                    n = comps(t)
                    raw = buf[ro:ro + 2 * n]
                    seg_range[t] = raw
                    ro += 2 * n
        bits = Bits(buf[H + data_off:H + data_off + (pose_bits * seg_samples + 7) // 8 + 8])
        for i in range(seg_samples):
            off = i * pose_bits
            for t in animated:
                n = comps(t)
                rate = rates.get(t)
                f = fmt_of(t)
                ignore_clip, ignore_seg = False, False
                if rate is not None:
                    nb = NUM_BITS[rate]
                    if nb == 0:
                        # (constant in this segment: its value in the segment range data, 16 bits a component)
                        raw = seg_range[t]
                        v = np.array([(raw[2 * c] << 8 | raw[2 * c + 1]) / 65535.0 for c in range(n)])
                        ignore_seg = True
                    elif nb == 32:
                        v = np.array([struct.unpack('>f', struct.pack('>I', bits.uint(off + 32 * c, 32)))[0] for c in range(n)])
                        off += 32 * n
                        ignore_clip = ignore_seg = True
                    else:
                        v = np.array([bits.uint(off + nb * c, nb) / float((1 << nb) - 1) for c in range(n)])
                        off += nb * n
                elif f in (ROT_QUAT_128, ROT_DROPW_96, VEC_96):
                    v = np.array([struct.unpack('>f', struct.pack('>I', bits.uint(off + 32 * c, 32)))[0] for c in range(n)])
                    off += 32 * n
                    ignore_clip = ignore_seg = True   # (full precision: never range reduced)
                else:
                    raise NotImplementedError('fixed format %d' % f)
                if t in seg_range and not ignore_seg:
                    raw = seg_range[t]
                    mn = np.array([raw[c] / 255.0 for c in range(n)])
                    ex = np.array([raw[n + c] / 255.0 for c in range(n)])
                    v = v * ex + mn
                if t in clip_range and not ignore_clip:
                    mn, ex = clip_range[t]
                    v = v * ex + mn
                values[t][sample0 + i] = v
        sample0 += seg_samples
    if sample0 != num_samples:
        raise ValueError('segments hold %d samples, the clip %d' % (sample0, num_samples))
    rot = np.zeros((num_bones, num_samples, 4)); rot[..., 3] = 1.0
    trans = np.zeros((num_bones, num_samples, 3))
    scale = np.full((num_bones, num_samples, 3), 1.0 if default_scale else 0.0) if has_scale else None
    for b in range(num_bones):
        for j in range(tracks_per_bone):
            t = b * tracks_per_bone + j
            if kinds[t] == 'default':
                continue
            v = np.broadcast_to(const[t], (num_samples, comps(t))) if kinds[t] == 'constant' else values[t]
            if j == 0:
                if drop_w:
                    xyz = v[:, :3]
                    w = np.sqrt(np.clip(1.0 - (xyz * xyz).sum(1), 0.0, None))
                    q = np.concatenate([xyz, w[:, None]], 1)
                else:
                    q = np.array(v)
                rot[b] = q / np.linalg.norm(q, axis=1, keepdims=True)
            elif j == 1:
                trans[b] = v
            else:
                scale[b] = v
    return dict(num_bones=num_bones, num_samples=num_samples, sample_rate=sample_rate, rot=rot, trans=trans, scale=scale,
                formats=(rot_fmt, trans_fmt, scale_fmt), clip_rr=clip_rr, seg_rr=seg_rr, segments=segments,
                kinds=kinds, has_scale=bool(has_scale))
