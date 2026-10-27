#!/usr/bin/env python3
"""Crisis Core Reunion (UE 4.27, IoStore "zen" package, unversioned properties) cooked AnimSequence decoder.

Decodes a cooked UAnimSequence compressed with UE's per-track codec (AnimCompress_PerTrackCompression_N, key
encoding AKF_PerTrackCompression) into per-frame LOCAL bone transforms on the USkeleton's FReferenceSkeleton.

    ccanim.py <clip.uasset> <skeleton.uasset> <out.npz>
    ccanim.py --batch <clip folder> [<clip folder> ...] --skeleton <skeleton.uasset> --out <out folder>
              [--summary <summary.json>]
  e.g. (from /work/ccanim)
    python3 tools/ccanim.py --batch in/Animation/Battle in/Animation/General --skeleton in/Mesh/SKL_CH_sephiroth.uasset \
        --out out --summary out/summary.json
    python3 tools/cccheck.py            # numerical checks + contact sheets (out/checks.json, out/check_*.png)

Output npz keys (UE component space conventions, cm, quaternions x,y,z,w; transforms stored as float32, the precision
the engine decodes at):
    bone_names, bone_parents, ref_q, ref_t, ref_s   skeleton order and local ref pose (USkeleton FReferenceSkeleton)
    num_frames, play_length (s), fps                 fps = (num_frames - 1) / play_length, snapped to the integer rate
                                                     when within 1e-4 (play_length is the stored float32 value)
    q (F,B,4), t (F,B,3), s (F,B,3)                  local transforms per frame, every bone filled
    tracked                                          skeleton bone indices that have a track in the clip
    notifies                                         JSON string (list of notify events, see decode_notifies)
  extra keys:
    animated                                         tracked bones whose value changes over the clip
    additive_type, ref_pose_type                     EAdditiveAnimationType / EAdditiveBasePoseType values
    add_q, add_t, add_s                              (additive clips only) the raw additive deltas per frame;
                                                     q/t/s then hold the deltas applied to the skeleton ref pose
    track_info                                       JSON: per track, bone + translation/rotation/scale formats
    info                                             JSON: header fields, offsets, warnings

Interpretation (matches UE 4.27 UAnimSequence::GetBonePose -> DecompressPose for the skeleton's own mesh, all bones in
EBoneTranslationRetargetingMode::Animation, which is what this skeleton's BoneTree says):
  * frame f is sampled at time f * play_length / (num_frames - 1)  (RelativePos = f / (num_frames - 1)).
  * a bone with a track gets the track's rotation (identity if the rotation stream is empty), translation (zero if the
    translation stream is empty) and, only when the clip stores scale streams, scale (zero if empty); otherwise scale
    keeps the reference pose value, exactly as the engine's pose starts from the ref pose.
  * a bone without a track keeps the reference pose (non-additive) / additive identity (additive).
  * quaternions are normalised (the engine normalises after decoding) and then made sign-continuous over time
    (q and -q are the same rotation; the codec stores every key with w >= 0).
"""
import json
import os
import re
import struct
import sys

import numpy as np

# ---------------------------------------------------------------------------------------------------------------------
# zen package (UE 4.26/4.27 IoStore package header), after ref/zen.py
# ---------------------------------------------------------------------------------------------------------------------


class Zen:
    def __init__(self, d):
        self.d = d
        (self.name_mapped, self.srcname_mapped, self.flags, self.cooked_header_size, self.nm_off, self.nm_size,
         self.nh_off, self.nh_size, self.imp_off, self.exp_off, self.eb_off, self.graph_off, self.graph_size,
         self.pad) = struct.unpack_from('<QQIIiiiiiiiiii', d, 0)
        self.names = []
        p, end = self.nm_off, self.nm_off + self.nm_size
        while p < end:
            h0, h1 = d[p], d[p + 1]
            p += 2
            wide = h0 & 0x80
            ln = ((h0 & 0x7f) << 8) | h1
            if wide:
                if p & 1:
                    p += 1
                s = d[p:p + ln * 2].decode('utf-16-le')
                p += ln * 2
            else:
                s = d[p:p + ln].decode('latin-1')
                p += ln
            self.names.append(s)
        self.imports = list(struct.unpack_from('<%dQ' % ((self.exp_off - self.imp_off) // 8), d, self.imp_off))
        self.exports = []
        for i in range((self.eb_off - self.exp_off) // 72):
            so, ss, objname, outer, cls, sup, tmpl, gimp, oflags, fflags = struct.unpack_from('<QQQQQQQQIB', d,
                                                                                              self.exp_off + i * 72)
            self.exports.append(dict(serial_offset=so, serial_size=ss, name=self.mapped(objname), outer=outer, cls=cls,
                                     template=tmpl, global_import=gimp, oflags=oflags))
        self.header_end = self.graph_off + self.graph_size
        self._pos = None

    def mapped(self, v):
        idx, num = v & 0x3fffffff, v >> 32
        s = self.names[idx] if idx < len(self.names) else '?%d' % idx
        return s if num == 0 else '%s_%d' % (s, num - 1)

    def bundle_positions(self):
        """{export index: (start, size)}: export data follows the header in export-bundle order (not export order)."""
        if self._pos is None:
            total = 2 * len(self.exports)
            heads, seen, p = [], 0, self.eb_off
            while seen < total:
                first, count = struct.unpack_from('<II', self.d, p)
                p += 8
                heads.append((first, count))
                seen += count
            ents = [struct.unpack_from('<II', self.d, p + 8 * k) for k in range(total)]
            pos, at = {}, self.header_end
            for first, count in heads:
                for idx, cmd in ents[first:first + count]:
                    if cmd == 1:   # serialize command
                        size = self.exports[idx]['serial_size']
                        pos[idx] = (at, size)
                        at += size
            assert at == len(self.d), ('export bundles do not end at file end', at, len(self.d))
            self._pos = pos
        return self._pos

    def export_bytes(self, i):
        start, size = self.bundle_positions()[i]
        return self.d[start:start + size]

    def export_index(self, name):
        for i, e in enumerate(self.exports):
            if e['name'] == name:
                return i
        return None


# ---------------------------------------------------------------------------------------------------------------------
# reader + unversioned property serialization (UE 4.26+ FUnversionedHeader)
# ---------------------------------------------------------------------------------------------------------------------


class DecodeError(Exception):
    pass


class R:
    def __init__(self, b, p=0, end=None):
        self.b, self.p = b, p
        self.end = len(b) if end is None else end

    def need(self, n):
        if self.p + n > self.end:
            raise DecodeError('read past end at %d (+%d > %d)' % (self.p, n, self.end))

    def u8(self):
        self.need(1)
        v = self.b[self.p]
        self.p += 1
        return v

    def u16(self):
        self.need(2)
        v = struct.unpack_from('<H', self.b, self.p)[0]
        self.p += 2
        return v

    def i32(self):
        self.need(4)
        v = struct.unpack_from('<i', self.b, self.p)[0]
        self.p += 4
        return v

    def u32(self):
        self.need(4)
        v = struct.unpack_from('<I', self.b, self.p)[0]
        self.p += 4
        return v

    def f32(self):
        self.need(4)
        v = struct.unpack_from('<f', self.b, self.p)[0]
        self.p += 4
        return v

    def floats(self, n):
        self.need(4 * n)
        v = struct.unpack_from('<%df' % n, self.b, self.p)
        self.p += 4 * n
        return list(v)

    def raw(self, n):
        self.need(n)
        v = self.b[self.p:self.p + n]
        self.p += n
        return v

    def fstring(self):
        n = self.i32()
        if n == 0:
            return ''
        if n > 0:
            if n > 65536:
                raise DecodeError('bad FString length %d at %d' % (n, self.p - 4))
            s = self.raw(n)
            return s[:-1].decode('latin-1')
        n = -n
        if n > 65536:
            raise DecodeError('bad FString length %d at %d' % (-n, self.p - 4))
        return self.raw(2 * n)[:-2].decode('utf-16-le')


def read_unversioned_header(r):
    """FUnversionedHeader: uint16 fragments (SkipNum:7, bHasAnyZeroes:1, bIsLast:1, ValueNum:7), then the zero mask.
    Returns [(property index, is_zero)] for the serialized properties, in order."""
    frags = []
    while True:
        h = r.u16()
        frags.append((h & 0x7f, bool(h & 0x80), h >> 9))
        if h & 0x100:
            break
    nzero = sum(vn for _, hz, vn in frags if hz)
    mask = 0
    if nzero:
        if nzero <= 8:
            mask = r.u8()
        elif nzero <= 16:
            mask = r.u16()
        else:
            for w in range((nzero + 31) // 32):
                mask |= r.u32() << (32 * w)
    out, idx, bit = [], 0, 0
    for skip, hz, vn in frags:
        idx += skip
        for k in range(vn):
            z = False
            if hz:
                z = bool((mask >> bit) & 1)
                bit += 1
            out.append((idx, z))
            idx += 1
    return out


# property types: 'i32' 'u32' 'f32' 'bool' (1 byte) 'u8' (byte / TEnumAsByte: 1 byte) 'name' (FName: index + number)
# 'obj' (FPackageIndex) 'soft' (FSoftObjectPath: FName + FString) 'str' 'vec' 'rot' 'quat' 'guid'
# ('arr', T) ('struct', schema name).  None = unknown type (parse stops).
SCHEMAS = {
    # UE 4.27 UAnimSequence (own properties first, then UAnimSequenceBase, then UAnimationAsset: unversioned schema
    # order = PropertyLink order).  Non-editor (cooked) properties only.  Indices 0-3, 4, 5, 18, 19, 22 are the ones the
    # CC clips use and are verified against the bytes; the rest follow the 4.27 headers.
    'AnimSequence': [
        ('NumFrames', 'i32'), ('TrackToSkeletonMapTable', ('arr', ('struct', 'TrackToSkeletonMap'))),
        ('BoneCompressionSettings', 'obj'), ('CurveCompressionSettings', 'obj'),
        ('AdditiveAnimType', 'u8'), ('RefPoseType', 'u8'), ('RefPoseSeq', 'obj'), ('RefFrameIndex', 'i32'),
        ('RetargetSource', 'name'), ('RetargetSourceAssetReferencePose', None), ('Interpolation', 'u8'),
        ('bEnableRootMotion', 'bool'), ('RootMotionRootLock', 'u8'), ('bForceRootLock', 'bool'),
        ('bUseNormalizedRootMotionScale', 'bool'), ('bRootMotionSettingsCopiedFromMontage', 'bool'),
        ('AuthoredSyncMarkers', ('arr', ('struct', 'AnimSyncMarker'))), ('BakedPerBoneCustomAttributeData', None),
        # UAnimSequenceBase
        ('Notifies', ('arr', ('struct', 'AnimNotifyEvent'))), ('SequenceLength', 'f32'), ('RateScale', 'f32'),
        ('RawCurveData', None),
        # UAnimationAsset
        ('Skeleton', 'obj'), ('MetaData', ('arr', 'obj')), ('AssetUserData', ('arr', 'obj')),
    ],
    'TrackToSkeletonMap': [('BoneTreeIndex', 'i32')],
    'AnimSyncMarker': [('MarkerName', 'name'), ('Time', 'f32')],
    # FAnimNotifyEvent (own, then FAnimLinkableElement)
    'AnimNotifyEvent': [
        ('DisplayTime_DEPRECATED', 'f32'), ('TriggerTimeOffset', 'f32'), ('EndTriggerTimeOffset', 'f32'),
        ('TriggerWeightThreshold', 'f32'), ('NotifyName', 'name'), ('Notify', 'obj'), ('NotifyStateClass', 'obj'),
        ('Duration', 'f32'), ('EndLink', ('struct', 'AnimLinkableElement')), ('bConvertedFromBranchingPoint', 'bool'),
        ('MontageTickType', 'u8'), ('NotifyTriggerChance', 'f32'), ('NotifyFilterType', 'u8'),
        ('NotifyFilterLOD', 'i32'), ('bTriggerOnDedicatedServer', 'bool'), ('bTriggerOnFollower', 'bool'),
        ('TrackIndex', 'i32'),
        ('LinkedMontage', 'obj'), ('SlotIndex', 'i32'), ('SegmentIndex', 'i32'), ('LinkMethod', 'u8'),
        ('CachedLinkMethod', 'u8'), ('SegmentBeginTime', 'f32'), ('SegmentLength', 'f32'), ('LinkValue', 'f32'),
        ('LinkedSequence', 'obj'),
    ],
    'AnimLinkableElement': [
        ('LinkedMontage', 'obj'), ('SlotIndex', 'i32'), ('SegmentIndex', 'i32'), ('LinkMethod', 'u8'),
        ('CachedLinkMethod', 'u8'), ('SegmentBeginTime', 'f32'), ('SegmentLength', 'f32'), ('LinkValue', 'f32'),
        ('LinkedSequence', 'obj'),
    ],
    # USkeleton (own properties; only the leading ones are needed: BoneTree and Sockets are what the CC skeleton has)
    'Skeleton': [
        ('BoneTree', ('arr', ('struct', 'BoneNode'))), ('RefLocalPoses_DEPRECATED', None), ('VirtualBoneGuid', 'guid'),
        ('VirtualBones', ('arr', ('struct', 'VirtualBone'))), ('Sockets', ('arr', 'obj')),
    ],
    'BoneNode': [('Name_DEPRECATED', 'name'), ('ParentIndex_DEPRECATED', 'i32'), ('TranslationRetargetingMode', 'u8')],
    'VirtualBone': [('SourceBoneName', 'name'), ('TargetBoneName', 'name'), ('VirtualBoneName', 'name')],
}

# values of properties that are absent from the header (= equal to the class / struct default)
DEFAULTS = {
    'AnimSequence': {'RateScale': 1.0, 'Interpolation': 0, 'AdditiveAnimType': 0, 'RefPoseType': 0},
    'AnimNotifyEvent': {'TriggerWeightThreshold': 1e-5, 'NotifyTriggerChance': 1.0, 'bTriggerOnDedicatedServer': True,
                        'SegmentIndex': -1, 'SlotIndex': 0},
}


def zero_value(t):
    if t in ('i32', 'u32', 'u8', 'obj'):
        return 0
    if t == 'f32':
        return 0.0
    if t == 'bool':
        return False
    if t == 'name':
        return 'None'
    if t in ('str', 'soft'):
        return ''
    if t in ('vec', 'rot'):
        return [0.0, 0.0, 0.0]
    if t == 'quat':
        return [0.0, 0.0, 0.0, 0.0]
    if t == 'guid':
        return '0' * 32
    if isinstance(t, tuple) and t[0] == 'arr':
        return []
    if isinstance(t, tuple) and t[0] == 'struct':
        return {n: zero_value(tt) for n, tt in SCHEMAS[t[1]]}
    return None


class Unversioned:
    """Parses unversioned property blocks with the SCHEMAS above; FName values resolve through the package name map."""

    def __init__(self, z):
        self.z = z

    def name(self, r):
        i, n = r.u32(), r.u32()
        if i >= len(self.z.names):
            raise DecodeError('name index %d out of range at %d' % (i, r.p - 8))
        s = self.z.names[i]
        return s if n == 0 else '%s_%d' % (s, n - 1)

    def value(self, r, t):
        if t == 'i32':
            return r.i32()
        if t == 'u32':
            return r.u32()
        if t == 'f32':
            return r.f32()
        if t == 'bool':
            v = r.u8()
            if v not in (0, 1):
                raise DecodeError('bool byte %d at %d' % (v, r.p - 1))
            return bool(v)
        if t == 'u8':
            return r.u8()
        if t == 'name':
            return self.name(r)
        if t == 'obj':
            return r.i32()
        if t == 'soft':
            a = self.name(r)
            s = r.fstring()
            return a if not s else a + ':' + s
        if t == 'str':
            return r.fstring()
        if t in ('vec', 'rot'):
            return r.floats(3)
        if t == 'quat':
            return r.floats(4)
        if t == 'guid':
            return r.raw(16).hex()
        if isinstance(t, tuple) and t[0] == 'arr':
            n = r.i32()
            if not (0 <= n <= 1000000):
                raise DecodeError('bad array count %d at %d' % (n, r.p - 4))
            return [self.value(r, t[1]) for _ in range(n)]
        if isinstance(t, tuple) and t[0] == 'struct':
            return self.struct(r, t[1])
        raise DecodeError('unknown property type %r' % (t,))

    def struct(self, r, schema):
        sch = SCHEMAS[schema]
        out = {n: zero_value(t) for n, t in sch}
        out.update(DEFAULTS.get(schema, {}))
        present = []
        for idx, is_zero in read_unversioned_header(r):
            if idx >= len(sch):
                raise DecodeError('%s: property index %d beyond the known schema' % (schema, idx))
            n, t = sch[idx]
            present.append(n)
            if is_zero:
                out[n] = zero_value(t)
                continue
            if t is None:
                raise DecodeError('%s: property %d (%s) present, but its layout is unknown' % (schema, idx, n))
            out[n] = self.value(r, t)
        out['_present'] = present
        return out


# ---------------------------------------------------------------------------------------------------------------------
# per-track codec (AnimEncoding_PerTrackCompression + AnimationCompression.h, UE 4.26/4.27)
# ---------------------------------------------------------------------------------------------------------------------

ACF = ['None', 'Float96NoW', 'Fixed48NoW', 'IntervalFixed32NoW', 'Fixed32NoW', 'Float32NoW', 'Identity']
COMPRESSED_ROTATION_STRIDES = [4, 4, 2, 4, 4, 4, 0]
PER_TRACK_NUM_COMPONENT_TABLE = [
    4, 4, 4, 4, 4, 4, 4, 4,   # ACF_None
    3, 1, 1, 2, 1, 2, 2, 3,   # ACF_Float96NoW
    3, 1, 1, 2, 1, 2, 2, 3,   # ACF_Fixed48NoW
    6, 2, 2, 4, 2, 4, 4, 6,   # ACF_IntervalFixed32NoW (number of fixed floats: min/range pairs)
    1, 1, 1, 1, 1, 1, 1, 1,   # ACF_Fixed32NoW
    1, 1, 1, 1, 1, 1, 1, 1,   # ACF_Float32NoW
    0, 0, 0, 0, 0, 0, 0, 0,   # ACF_Identity
]


def track_sizes(fmt, flags):
    """GetByteSizesFromFormat: (bytes per key, fixed bytes)."""
    comp_size = COMPRESSED_ROTATION_STRIDES[fmt]
    lookup = PER_TRACK_NUM_COMPONENT_TABLE[(flags & 7) | (fmt << 3)]
    if fmt != 3:
        return lookup * comp_size, 0
    return comp_size, lookup * 4


def _float_packer_decode(v, nexp, nman):
    """TFloatPacker<nexp, nman, true>::Decode (IEEE32), used by ACF_Float32NoW."""
    v = v.astype(np.int64)
    man = v & ((1 << nman) - 1)
    ex = (v >> nman) & ((1 << nexp) - 1)
    sign = v >> (nexp + nman)
    min_exp = -(1 << (nexp - 1)) + 1
    bits = (sign << 31) | ((ex + min_exp + 127) << 23) | (man << (23 - nman))
    out = bits.astype(np.uint32).view(np.float32).astype(np.float64)
    out[v == 0] = 0.0
    return out


def _bounds(fixed, flags):
    """Interval formats: (min, range) pairs for the flagged components, in x, y, z order."""
    mins, ranges, k = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], 0
    for c in range(3):
        if flags & (1 << c):
            mins[c], ranges[c] = fixed[k], fixed[k + 1]
            k += 2
    return np.array(mins), np.array(ranges)


def decode_keys(kind, fmt, flags, nkeys, fixed, keybytes):
    """All keys of one track as float64 arrays: rotation (n,4) x,y,z,w (w from the unit-length constraint, not yet
    normalised) or translation / scale (n,3).  Returns (keys, raw_xyz_sq) where raw_xyz_sq is |xyz|^2 for rotations."""
    n = nkeys
    if kind == 'rot':
        if fmt == 1:   # Float96NoW: three floats, flags ignored by the decoder
            xyz = np.frombuffer(keybytes, '<f4').reshape(n, 3).astype(np.float64)
        elif fmt == 2:   # Fixed48NoW: uint16 per flagged component, (v - 32767) / 32767, missing = 0
            cnt = PER_TRACK_NUM_COMPONENT_TABLE[(flags & 7) | (2 << 3)]
            v = np.frombuffer(keybytes, '<u2').reshape(n, cnt).astype(np.float64)
            xyz, k = np.zeros((n, 3)), 0
            for c in range(3):
                if flags & (1 << c):
                    xyz[:, c] = (v[:, k] - 32767.0) * 3.0518509475997192297128208258309e-5
                    k += 1
        elif fmt == 3:   # IntervalFixed32NoW: X 11 bits (31..21), Y 11 bits (20..10), Z 10 bits (9..0)
            mins, ranges = _bounds(fixed, flags)
            p = np.frombuffer(keybytes, '<u4').astype(np.int64)
            ux, uy, uz = p >> 21, (p & 0x001ffc00) >> 10, p & 0x3ff
            xyz = np.stack([((ux - 1023) / 1023.0) * ranges[0] + mins[0], ((uy - 1023) / 1023.0) * ranges[1] + mins[1],
                            ((uz - 511) / 511.0) * ranges[2] + mins[2]], 1)
        elif fmt == 4:   # Fixed32NoW: 11-11-10 fixed point over -1..1
            p = np.frombuffer(keybytes, '<u4').astype(np.int64)
            ux, uy, uz = p >> 21, (p & 0x001ffc00) >> 10, p & 0x3ff
            xyz = np.stack([(ux - 1023) / 1023.0, (uy - 1023) / 1023.0, (uz - 511) / 511.0], 1)
        elif fmt == 5:   # Float32NoW: 11-11-10 small floats
            p = np.frombuffer(keybytes, '<u4').astype(np.int64)
            xyz = np.stack([_float_packer_decode(p >> 21, 3, 7), _float_packer_decode((p & 0x001ffc00) >> 10, 3, 7),
                            _float_packer_decode(p & 0x3ff, 3, 6)], 1)
        else:
            raise DecodeError('rotation format %d (%s) is not decodable by the per-track codec' % (fmt, ACF[fmt]))
        sq = (xyz ** 2).sum(1)
        w = np.sqrt(np.maximum(1.0 - sq, 0.0))
        return np.concatenate([xyz, w[:, None]], 1), sq
    # translation / scale
    if fmt == 1:   # Float96NoW: flags 0 = legacy (all three), else one float per flagged component
        if flags & 7 == 0:
            return np.frombuffer(keybytes, '<f4').reshape(n, 3).astype(np.float64), None
        cnt = PER_TRACK_NUM_COMPONENT_TABLE[(flags & 7) | (1 << 3)]
        v = np.frombuffer(keybytes, '<f4').reshape(n, cnt).astype(np.float64)
        out, k = np.zeros((n, 3)), 0
        for c in range(3):
            if flags & (1 << c):
                out[:, c] = v[:, k]
                k += 1
        return out, None
    if fmt == 2:   # Fixed48NoW: DecompressFixed16<LogScale=7>: QuantOffset 255, factor 1 (as the 4.26/4.27 engine)
        cnt = PER_TRACK_NUM_COMPONENT_TABLE[(flags & 7) | (2 << 3)]
        v = np.frombuffer(keybytes, '<u2').reshape(n, cnt).astype(np.float64)
        out, k = np.zeros((n, 3)), 0
        for c in range(3):
            if flags & (1 << c):
                out[:, c] = (v[:, k] - 255.0) / 1.0
                k += 1
        return out, None
    if fmt == 3:   # IntervalFixed32NoW: X 10 bits (9..0), Y 11 bits (20..10), Z 11 bits (31..21)
        mins, ranges = _bounds(fixed, flags)
        p = np.frombuffer(keybytes, '<u4').astype(np.int64)
        uz, uy, ux = p >> 21, (p & 0x001ffc00) >> 10, p & 0x3ff
        return np.stack([((ux - 511) / 511.0) * ranges[0] + mins[0], ((uy - 1023) / 1023.0) * ranges[1] + mins[1],
                         ((uz - 1023) / 1023.0) * ranges[2] + mins[2]], 1), None
    raise DecodeError('%s format %d (%s) is not decodable by the per-track codec' % (kind, fmt, ACF[fmt]))


def parse_track(bs, off, kind, num_frames):
    """One per-track stream at byte offset `off` of the compressed byte stream."""
    if off + 4 > len(bs):
        raise DecodeError('%s track offset %d beyond byte stream (%d)' % (kind, off, len(bs)))
    if off % 4:
        raise DecodeError('%s track offset %d not 4-byte aligned' % (kind, off))
    header = struct.unpack_from('<I', bs, off)[0]
    nkeys, flags, fmt = header & 0xffffff, (header >> 24) & 0xf, (header >> 28) & 0xf
    if fmt >= len(ACF) or fmt in (0, 6) or nkeys == 0:
        raise DecodeError('%s track at %d: bad header %08x (format %d, %d keys)' % (kind, off, header, fmt, nkeys))
    bpk, fixed_bytes = track_sizes(fmt, flags)
    p = off + 4
    fixed = list(struct.unpack_from('<%df' % (fixed_bytes // 4), bs, p)) if fixed_bytes else []
    p += fixed_bytes
    if p + bpk * nkeys > len(bs):
        raise DecodeError('%s track at %d: %d keys of %d bytes overrun the byte stream' % (kind, off, nkeys, bpk))
    keys, sq = decode_keys(kind, fmt, flags, nkeys, fixed, bs[p:p + bpk * nkeys])
    p += bpk * nkeys
    p = (p + 3) & ~3
    frames = None
    if flags & 8:
        es = 1 if num_frames <= 0xff else 2
        frames = np.frombuffer(bs[p:p + es * nkeys], '<u1' if es == 1 else '<u2').astype(np.int64)
        if len(frames) != nkeys:
            raise DecodeError('%s track at %d: frame table overruns the byte stream' % (kind, off))
        p += es * nkeys
        p = (p + 3) & ~3
    return dict(kind=kind, offset=off, end=p, format=fmt, flags=flags & 7, frame_table=bool(flags & 8), nkeys=nkeys,
                keys=keys, frames=frames, xyz_sq=sq)


def sample_indices(tr, num_frames):
    """For every frame f: (index0, index1, alpha) exactly as AnimEncoding::TimeToIndex evaluates RelativePos =
    f / (num_frames - 1) (uniform keys, or the key->frame table when the track has one)."""
    F, n = num_frames, tr['nkeys']
    f = np.arange(F, dtype=np.float64)
    i0 = np.zeros(F, np.int64)
    i1 = np.zeros(F, np.int64)
    a = np.zeros(F)
    if n < 2 or F < 2:
        return i0, i1, a
    rel = f / (F - 1)
    inner = (rel > 0) & (rel < 1)
    last = rel >= 1
    if not tr['frame_table']:
        kp = rel * (n - 1)
        fl = np.floor(kp)
        i0 = np.where(inner, np.minimum(fl.astype(np.int64), n - 1), 0)
        i1 = np.where(inner, np.minimum(i0 + 1, n - 1), 0)
        a = np.where(inner, kp - fl, 0.0)
        i0 = np.where(last, n - 1, i0)
        i1 = np.where(last, n - 1, i1)
        a = np.where(last, 0.0, a)
        return i0, i1, a
    frames = tr['frames']
    for k in range(F):
        if rel[k] <= 0:
            continue
        if rel[k] >= 1:
            i0[k] = i1[k] = n - 1
            continue
        fp = f[k]   # FramePos = RelativePos * (NumFrames - 1)
        fpf = min(max(int(fp), 0), F - 2)
        lo = int(np.searchsorted(frames, fpf, side='right')) - 1   # last key with frame <= target (FindLowKeyIndex)
        lo = max(lo, 0)
        hi = min(lo + 1, n - 1)
        delta = max(int(frames[hi]) - int(frames[lo]), 1)
        i0[k], i1[k] = lo, hi
        a[k] = (fp - frames[lo]) / delta if lo != hi else 0.0
    return i0, i1, a


def sample_track(tr, num_frames):
    i0, i1, a = sample_indices(tr, num_frames)
    k0, k1 = tr['keys'][i0], tr['keys'][i1]
    if tr['kind'] != 'rot':
        return k0 + (k1 - k0) * a[:, None]
    # FQuat::FastLerp (flips the first key towards the second) + Normalize
    dot = (k0 * k1).sum(1)
    bias = np.where(dot >= 0, 1.0, -1.0)
    q = k1 * a[:, None] + k0 * (bias * (1.0 - a))[:, None]
    nrm = np.linalg.norm(q, axis=1)
    bad = nrm < 1e-8
    q[bad] = [0, 0, 0, 1]
    nrm[bad] = 1
    return q / nrm[:, None]


# ---------------------------------------------------------------------------------------------------------------------
# skeleton
# ---------------------------------------------------------------------------------------------------------------------


def _ref_skeleton_at(z, x, p):
    """FReferenceSkeleton at p: RawRefBoneInfo (FName + parent), RawRefBonePose (FTransform: quat, translation, scale),
    RawNameToIndexMap.  Returns (bones, end) or None."""
    try:
        r = R(x, p)
        n = r.i32()
        if not (1 <= n <= 65535):
            return None
        names, parents = [], []
        for k in range(n):
            ni, num, par = r.u32(), r.u32(), r.i32()
            if ni >= len(z.names) or num > 1000 or not (-1 <= par < k) or ((k == 0) != (par == -1)):
                return None
            names.append(z.names[ni] if num == 0 else '%s_%d' % (z.names[ni], num - 1))
            parents.append(par)
        if r.i32() != n:
            return None
        pose = np.array(r.floats(10 * n), dtype=np.float64).reshape(n, 10)
        if np.abs(np.linalg.norm(pose[:, :4], axis=1) - 1).max() > 1e-3:
            return None
        m = r.i32()
        if m != n:
            return None
        for _ in range(m):
            ni, num, idx = r.u32(), r.u32(), r.i32()
            nm = z.names[ni] if ni < len(z.names) else None
            if nm is None or not (0 <= idx < n) or names[idx] != (nm if num == 0 else '%s_%d' % (nm, num - 1)):
                return None
        return dict(names=names, parents=np.array(parents), q=pose[:, :4], t=pose[:, 4:7], s=pose[:, 7:10]), r.p
    except (DecodeError, struct.error):
        return None


def load_skeleton(path):
    """USkeleton from its zen package: BoneTree (unversioned) + FReferenceSkeleton + retarget sources + Guid."""
    d = open(path, 'rb').read()
    z = Zen(d)
    cands = [i for i, e in enumerate(z.exports) if not e['name'].startswith('Default__')]
    best = None
    for i in cands:
        x = z.export_bytes(i)
        if len(x) < 64:
            continue
        info = dict(export=z.exports[i]['name'], warnings=[])
        props, p0 = None, None
        try:
            r = R(x)
            props = Unversioned(z).struct(r, 'Skeleton')
            has_guid = r.i32()
            if has_guid not in (0, 1):
                raise DecodeError('HasGuid %d' % has_guid)
            if has_guid:
                r.raw(16)
            p0 = r.p
        except DecodeError as e:
            info['warnings'].append('skeleton property block not parsed (%s); reference skeleton found by search' % e)
        res = _ref_skeleton_at(z, x, p0) if p0 is not None else None
        if res is None:   # structural search fallback
            for p in range(0, len(x) - 16):
                res = _ref_skeleton_at(z, x, p)
                if res:
                    p0 = p
                    break
        if not res:
            continue
        bones, q = res
        r = R(x, q)
        nsrc = r.i32()
        if nsrc != 0:
            info['warnings'].append('skeleton has %d retarget sources (not parsed)' % nsrc)
            guid = None
        else:
            guid = r.raw(16).hex()
        bones.update(info, guid=guid, ref_skeleton_at=p0, props=props)
        if props is not None and len(props['BoneTree']) == len(bones['names']):
            bones['retarget_modes'] = [b['TranslationRetargetingMode'] for b in props['BoneTree']]
        else:
            bones['retarget_modes'] = None
        if best is None or len(bones['names']) > len(best['names']):
            best = bones
    if best is None:
        raise DecodeError('no reference skeleton found in %s' % path)
    best['path'] = path
    return best


# ---------------------------------------------------------------------------------------------------------------------
# anim sequence
# ---------------------------------------------------------------------------------------------------------------------


def find_compressed_block(x):
    """Locate FCompressedAnimSequence::SerializeCompressedData by its structure, from the end of the export:
         int32 CompressedRawDataSize
         TArray<int32> CompressedTrackToSkeletonMapTable
         TArray<FSmartName> CompressedCurveNames            (FSmartName = FName in 4.27)
         int32 NumBytes, bool32 bUseBulkDataForLoad
         uint8 SerializedData[NumBytes] = int32 TrackOffsets[nTO] | int32 ScaleOffsets[nSO] | uint8 ByteStream[nBS]
         FString BoneCodecDDCHandle, FString CurveCodecPath, int32 NumCurveBytes, uint8 CurveBytes[NumCurveBytes]
         FUECompressedAnimData::SerializeCompressedData:
             int32 CompressedNumberOfFrames, uint8 KeyEncodingFormat, TranslationCompressionFormat,
             RotationCompressionFormat, ScaleCompressionFormat, int32 nBS, int32 nTO, int32 nSO, int32 StripSize
       then UAnimSequence: bool32 bUseRawDataOnly == end of export."""
    k = x.rfind(b'AnimCompress_')
    if k < 4:
        raise DecodeError('bone codec DDC handle (AnimCompress_*) not found')
    sp = k - 4
    r = R(x, sp)
    codec = r.fstring()
    curve_codec = r.fstring()
    ncb = r.i32()
    if not (0 <= ncb <= len(x)):
        raise DecodeError('bad NumCurveBytes %d' % ncb)
    curve_bytes = r.raw(ncb)
    nframes = r.i32()
    key_fmt, t_fmt, r_fmt, s_fmt = r.u8(), r.u8(), r.u8(), r.u8()
    nbs, nto, nso, strip = r.i32(), r.i32(), r.i32(), r.i32()
    use_raw = r.i32()
    if r.p != len(x):
        raise DecodeError('compressed data tail ends at %d, export is %d bytes' % (r.p, len(x)))
    nbytes = 4 * (nto + nso) + nbs
    start = sp - nbytes
    if start < 8 or struct.unpack_from('<i', x, start - 8)[0] != nbytes:
        raise DecodeError('NumBytes before the serialized data does not match the view sizes')
    bulk = struct.unpack_from('<i', x, start - 4)[0]
    if bulk != 0:
        raise DecodeError('bUseBulkDataForLoad = %d (bulk animation data not supported)' % bulk)
    ntracks = nto // 2
    found = None
    for c in range(0, 4096):   # curve names (8 bytes each) then the track map, walking backward
        cp = start - 8 - 8 * c - 4
        mp = cp - 4 - 4 * ntracks
        if mp < 4:
            break
        if struct.unpack_from('<i', x, cp)[0] == c and struct.unpack_from('<i', x, mp)[0] == ntracks:
            found = (c, cp, mp)
            break
    if not found:
        raise DecodeError('CompressedTrackToSkeletonMapTable not found before the serialized data')
    c, cp, mp = found
    track_map = list(struct.unpack_from('<%di' % ntracks, x, mp + 4))
    curve_names = [struct.unpack_from('<II', x, cp + 4 + 8 * i) for i in range(c)]
    raw_size = struct.unpack_from('<i', x, mp - 4)[0]
    sd = x[start:start + nbytes]
    to = np.frombuffer(sd[:4 * nto], '<i4').astype(np.int64)
    so = np.frombuffer(sd[4 * nto:4 * (nto + nso)], '<i4').astype(np.int64)
    bs = sd[4 * (nto + nso):]
    return dict(block_start=mp - 4, map_at=mp, data_at=start, codec=codec, curve_codec=curve_codec,
                num_curve_bytes=ncb, curve_bytes=curve_bytes, num_frames=nframes,
                formats=(key_fmt, t_fmt, r_fmt, s_fmt), nbs=nbs, nto=nto, nso=nso, strip=strip, use_raw=use_raw,
                ntracks=ntracks, track_map=track_map, curve_names=curve_names, raw_size=raw_size, track_offsets=to,
                scale_offsets=so, byte_stream=bs)


def parse_tracks(cd):
    """Parse every stream; check the streams tile the byte stream in compressor order (scale, translation, rotation per
    track) with nothing left over."""
    bs, F = cd['byte_stream'], cd['num_frames']
    to, so, strip = cd['track_offsets'], cd['scale_offsets'], cd['strip']
    has_scale = len(so) > 0
    tracks, spans = [], []
    for ti in range(cd['ntracks']):
        e = {}
        offs = [('scale', so[ti * strip] if has_scale else -1), ('trans', to[2 * ti]), ('rot', to[2 * ti + 1])]
        for kind, off in offs:
            if off == -1:
                e[kind] = None
                continue
            tr = parse_track(bs, int(off), kind, F)
            e[kind] = tr
            spans.append((tr['offset'], tr['end'], ti, kind))
        tracks.append(e)
    spans.sort()
    pos, gaps, bad_pad = 0, [], 0
    for a, b, ti, kind in spans:
        if a != pos:
            gaps.append((pos, a, ti, kind))
        pos = b
    # alignment padding written by the compressor is the sentinel 0x55 (PadSentinel = 85)
    for e in tracks:
        for tr in e.values():
            if tr is None:
                continue
            bpk, fixed = track_sizes(tr['format'], tr['flags'] | (8 if tr['frame_table'] else 0))
            p = tr['offset'] + 4 + fixed + bpk * tr['nkeys']
            pads = list(range(p, (p + 3) & ~3))
            if tr['frame_table']:
                es = 1 if F <= 0xff else 2
                q = ((p + 3) & ~3) + es * tr['nkeys']
                pads += list(range(q, (q + 3) & ~3))
            bad_pad += sum(1 for k in pads if bs[k] != 0x55)
    tiling = dict(ok=(not gaps and pos == len(bs)), gaps=gaps[:8], end=pos, size=len(bs), bad_pad_bytes=bad_pad)
    return tracks, tiling


def resolve_object(z, idx):
    if idx > 0 and idx - 1 < len(z.exports):
        return 'export:' + z.exports[idx - 1]['name']
    if idx < 0:
        return 'import:%d' % (-idx - 1)
    return None


# Notify objects are game classes (Fair*) whose property schemas are not available.  The value types per property index
# below were inferred from the byte patterns of all 78 CC Sephiroth clips (every instance parses to exactly the end of
# its property block); names marked '?' are guesses by analogy with the stock UE notify they resemble, 'pN' = unknown.
NOTIFY_SCHEMAS = {
    'FairAnimNotifyPlayParticleEffect': {0: ('PSTemplate?', 'soft'), 1: ('LocationOffset?', 'vec'),
                                         2: ('RotationOffset?', 'rot'), 3: ('Scale?', 'vec'), 4: ('Attached?', 'bool'),
                                         5: ('SocketName?', 'name')},
    'FairAnimNotifyStateTimedParticle': {0: ('PSTemplate?', 'soft'), 1: ('SocketName?', 'name'),
                                         2: ('LocationOffset?', 'vec'), 3: ('RotationOffset?', 'rot')},
    'FairAnimNotifyStateTrail': {0: ('PSTemplate?', 'soft'), 1: ('FirstSocketName?', 'name'),
                                 2: ('SecondSocketName?', 'name')},
    'FairMotEventNotify': {0: ('p0', 'u8'), 1: ('p1', 'u8'), 2: ('p2', 'i32'), 3: ('p3', 'i32'), 4: ('p4', 'bool'),
                           6: ('p6', 'bool')},
    'FairMotLookAtNotify': {0: ('p0', 'bool')},
    'FairMotLookAtNotifyState': {},
    'FairMotWepAttachNotify': {2: ('p2_attach_name', 'name')},
    'FairMotWepAttachNotifyState': {3: ('p3_attach_name', 'name')},
    'FairMotKeyInterChangeNotifyState': {},
}


def _notify_payload(z, i):
    """The notify object's own (game class) properties, typed by NOTIFY_SCHEMAS.  'decoded' is False (and the raw
    bytes are kept) when the class or a property index is not covered or the parse does not end at the object's
    trailing HasGuid."""
    x = z.export_bytes(i)
    name = z.exports[i]['name']
    cls = re.sub(r'_\d+$', '', name)
    out = dict(object=name, raw=x.hex())
    try:
        r = R(x)
        hdr = read_unversioned_header(r)
        out['present'] = [idx for idx, zr in hdr]
        sch = NOTIFY_SCHEMAS.get(cls)
        if sch is None:
            raise DecodeError('no layout known for %s' % cls)
        uv = Unversioned(z)
        vals = {}
        for idx, zr in hdr:
            if idx not in sch:
                raise DecodeError('%s property %d not covered' % (cls, idx))
            nm, t = sch[idx]
            vals[nm] = zero_value(t) if zr else uv.value(r, t)
        if r.p != len(x) - 4 or struct.unpack_from('<i', x, r.p)[0] != 0:
            raise DecodeError('did not end at HasGuid')
        out['values'] = vals
        out['decoded'] = True
    except (DecodeError, struct.error) as e:
        out['decoded'] = False
        out['why'] = str(e)
    return out


def decode_notifies(z, props, fps):
    out = []
    for k, ev in enumerate(props.get('Notifies') or []):
        obj = ev['NotifyStateClass'] or ev['Notify']
        is_state = bool(ev['NotifyStateClass'])
        oname = z.exports[obj - 1]['name'] if 0 < obj <= len(z.exports) else None
        cls = re.sub(r'_\d+$', '', oname) if oname else None
        t0 = ev['LinkValue'] + ev['TriggerTimeOffset']
        dur = ev['Duration'] if is_state else 0.0
        end_link = ev['EndLink']['LinkValue'] if isinstance(ev['EndLink'], dict) else None
        e = dict(index=k, notify_name=ev['NotifyName'], cls=cls, object=oname, is_state=is_state,
                 time=ev['LinkValue'], trigger_time=t0, duration=dur,
                 end_time=(t0 + dur + ev['EndTriggerTimeOffset']) if is_state else None,
                 frame=ev['LinkValue'] * fps, end_frame=((ev['LinkValue'] + dur) * fps) if is_state else None,
                 trigger_time_offset=ev['TriggerTimeOffset'], end_trigger_time_offset=ev['EndTriggerTimeOffset'],
                 end_link_value=end_link, link_method=ev['LinkMethod'], track_index=ev['TrackIndex'],
                 trigger_chance=ev['NotifyTriggerChance'], trigger_weight_threshold=ev['TriggerWeightThreshold'],
                 linked_sequence=resolve_object(z, ev['LinkedSequence']))
        if obj > 0:
            e['payload'] = _notify_payload(z, obj - 1)
        out.append(e)
    return out


def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0)
    bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz], -1)


def qrot(q, v):
    u = q[..., :3]
    t = 2 * np.cross(u, v)
    return v + q[..., 3:4] * t + np.cross(u, t)


def make_continuous(q, return_flips=False):
    """Flip signs so consecutive frames' quaternions have a non-negative dot product (per bone)."""
    q = q.copy()
    flips = 0
    for f in range(1, len(q)):
        neg = (q[f] * q[f - 1]).sum(-1) < 0
        flips += int(neg.sum())
        q[f, neg] *= -1
    return (q, flips) if return_flips else q


def decode_clip(path, skel):
    d = open(path, 'rb').read()
    z = Zen(d)
    base = os.path.splitext(os.path.basename(path))[0]
    ai = z.export_index(base)
    if ai is None:
        ai = max(range(len(z.exports)), key=lambda i: z.exports[i]['serial_size'])
    x = z.export_bytes(ai)
    warnings = []
    cd = find_compressed_block(x)
    if not cd['codec'].startswith('AnimCompress_PerTrackCompression'):
        raise DecodeError('bone codec %s is not the per-track codec' % cd['codec'])
    if cd['formats'][0] != 2:
        raise DecodeError('KeyEncodingFormat %d is not AKF_PerTrackCompression (2)' % cd['formats'][0])
    # property block, then UObject HasGuid, UAnimationAsset SkeletonGuid, UAnimSequence strip flags and
    # bSerializeCompressedData, which must land exactly on the compressed block
    props, prop_err = None, None
    try:
        r = R(x)
        props = Unversioned(z).struct(r, 'AnimSequence')
        prop_end = r.p
        has_guid = r.i32()
        if has_guid:
            r.raw(16)
        skel_guid = r.raw(16).hex()
        strip = (r.u8(), r.u8())
        ser = r.i32()
        if r.p != cd['block_start']:
            raise DecodeError('property block ends at %d, native data expected at %d' % (r.p, cd['block_start'] - 26))
        if ser != 1:
            raise DecodeError('bSerializeCompressedData = %d' % ser)
    except DecodeError as e:
        prop_err = str(e)
        props = None
    if props is None:
        # fall back to the native data only; the frame rate is then assumed
        warnings.append('property block not parsed (%s): SequenceLength assumed (NumFrames-1)/30' % prop_err)
        skel_guid, strip, prop_end = None, None, None
        props = {'NumFrames': cd['num_frames'], 'SequenceLength': (cd['num_frames'] - 1) / 30.0, 'RateScale': 1.0,
                 'AdditiveAnimType': 0, 'RefPoseType': 0, 'Notifies': [], '_present': []}
    F = cd['num_frames']
    if props['NumFrames'] != F:
        warnings.append('NumFrames property %d != CompressedNumberOfFrames %d' % (props['NumFrames'], F))
    length = float(props['SequenceLength'])
    fps_exact = (F - 1) / length if F > 1 and length > 0 else 0.0
    # SequenceLength is a float32; snap the rate to the integer it was authored at when it is that close
    fps = float(round(fps_exact)) if fps_exact and abs(fps_exact - round(fps_exact)) < 1e-4 * fps_exact else fps_exact
    if props.get('RateScale', 1.0) != 1.0:
        warnings.append('RateScale %.4g (play_length is the unscaled SequenceLength)' % props['RateScale'])
    if skel_guid is not None and skel.get('guid') and skel_guid != skel['guid']:
        warnings.append('SkeletonGuid %s differs from the skeleton Guid %s' % (skel_guid, skel['guid']))
    prop_map = [m['BoneTreeIndex'] for m in props.get('TrackToSkeletonMapTable') or []]
    if prop_map and prop_map != cd['track_map']:
        warnings.append('TrackToSkeletonMapTable property (%d tracks) differs from the compressed map (%d tracks); '
                        'the compressed map is used' % (len(prop_map), len(cd['track_map'])))
    if cd['num_curve_bytes'] or cd['curve_names']:
        warnings.append('clip has %d compressed curves (%d bytes): not decoded' % (len(cd['curve_names']),
                                                                                    cd['num_curve_bytes']))
    tracks, tiling = parse_tracks(cd)
    if not tiling['ok']:
        raise DecodeError('track streams do not tile the byte stream: %s' % tiling)
    if tiling['bad_pad_bytes']:
        warnings.append('%d alignment pad bytes are not the 0x55 sentinel' % tiling['bad_pad_bytes'])
    for e in tracks:
        for tr in e.values():
            if tr is not None and tr['frame_table']:
                fr = tr['frames']
                if not (np.all(np.diff(fr) > 0) and fr[0] == 0 and fr[-1] == F - 1):
                    warnings.append('a key->frame table is not increasing from 0 to %d' % (F - 1))
                    break
    NB = len(skel['names'])
    bad = [b for b in cd['track_map'] if not 0 <= b < NB]
    if bad:
        raise DecodeError('track map references bones %s beyond the skeleton (%d bones)' % (bad[:5], NB))
    if len(set(cd['track_map'])) != len(cd['track_map']):
        raise DecodeError('track map has duplicate bones')
    additive = int(props.get('AdditiveAnimType', 0))
    has_scale = cd['nso'] > 0
    refq, reft, refs = skel['q'], skel['t'], skel['s']
    if additive:
        q = np.zeros((F, NB, 4))
        q[..., 3] = 1
        t = np.zeros((F, NB, 3))
        s = np.zeros((F, NB, 3))
    else:
        q = np.repeat(refq[None], F, 0).copy()
        t = np.repeat(reft[None], F, 0).copy()
        s = np.repeat(refs[None], F, 0).copy()
    info_tracks = []
    xyz_sq_max, xyz_sq_over, nkeys_rot, raw_flips = 0.0, 0, 0, 0
    for ti, bone in enumerate(cd['track_map']):
        e = tracks[ti]
        rec = dict(track=ti, bone=bone, name=skel['names'][bone])
        for kind in ('trans', 'rot', 'scale'):
            tr = e[kind]
            if tr is None:
                rec[kind] = None if (kind != 'scale' or has_scale) else 'no scale streams'
                continue
            rec[kind] = '%s/%d keys=%d%s' % (ACF[tr['format']], tr['flags'], tr['nkeys'],
                                              ' +frametable' if tr['frame_table'] else '')
            if tr['xyz_sq'] is not None:
                xyz_sq_max = max(xyz_sq_max, float(tr['xyz_sq'].max()))
                xyz_sq_over += int((tr['xyz_sq'] > 1 + 1e-5).sum())
                nkeys_rot += tr['nkeys']
                raw_flips += int(((tr['keys'][1:] * tr['keys'][:-1]).sum(1) < 0).sum())
        info_tracks.append(rec)
        # rotation
        if e['rot'] is not None:
            q[:, bone] = sample_track(e['rot'], F)
        else:
            q[:, bone] = [0, 0, 0, 1]
        if e['trans'] is not None:
            t[:, bone] = sample_track(e['trans'], F)
        else:
            t[:, bone] = 0
        if has_scale:
            s[:, bone] = sample_track(e['scale'], F) if e['scale'] is not None else 0
    q, sign_flips = make_continuous(q, return_flips=True)
    f32 = np.float32
    out = dict(bone_names=np.array(skel['names']), bone_parents=np.array(skel['parents'], dtype=np.int32),
               ref_q=refq.astype(f32), ref_t=reft.astype(f32), ref_s=refs.astype(f32), num_frames=np.int64(F),
               play_length=np.float64(length), fps=np.float64(fps))
    if additive:
        # additive (LocalSpaceBase): delta rotation pre-multiplies, translation adds, scale multiplies by (1 + delta).
        # q/t/s hold the deltas applied to the skeleton ref pose; add_* hold the deltas themselves.
        out.update(add_q=q.astype(f32), add_t=t.astype(f32), add_s=s.astype(f32))
        qa = make_continuous(qmul(q, refq[None]))
        qa /= np.linalg.norm(qa, axis=-1, keepdims=True)
        out.update(q=qa.astype(f32), t=(reft[None] + t).astype(f32), s=(refs[None] * (1 + s)).astype(f32))
        if additive != 1:
            warnings.append('AdditiveAnimType %d (not LocalSpaceBase): q/t/s apply the deltas as local-space '
                            'additive anyway' % additive)
    else:
        out.update(q=q.astype(f32), t=t.astype(f32), s=s.astype(f32))
    tracked = np.array(sorted(cd['track_map']), dtype=np.int64)
    var = (np.ptp(out['q'], 0).max(-1) > 1e-5) | (np.ptp(out['t'], 0).max(-1) > 1e-4) | (np.ptp(out['s'], 0).max(-1) > 1e-5)
    animated = np.nonzero(var)[0]
    notifies, notify_err = [], None
    try:
        notifies = decode_notifies(z, props, fps)
    except Exception as e:   # notifies are secondary; never fail the clip on them
        notify_err = 'notifies not decoded: %s' % e
        warnings.append(notify_err)
    info = dict(file=os.path.basename(path), export=z.exports[ai]['name'], export_size=len(x),
                package_flags='%08x' % z.flags, properties_present=props.get('_present'), property_block_end=prop_end,
                skeleton_guid=skel_guid, strip_flags=strip, compressed_block_at=cd['block_start'],
                serialized_data_at=cd['data_at'], codec=cd['codec'], curve_codec=cd['curve_codec'],
                key_encoding_format=cd['formats'][0], interface_formats=cd['formats'][1:],
                compressed_raw_data_size=cd['raw_size'], num_tracks=cd['ntracks'], byte_stream_size=cd['nbs'],
                track_offsets=cd['nto'], scale_offsets=cd['nso'], scale_strip_size=cd['strip'],
                use_raw_data_only=cd['use_raw'], tiling=tiling, additive_type=additive,
                ref_pose_type=int(props.get('RefPoseType', 0)), rate_scale=props.get('RateScale', 1.0),
                interpolation=props.get('Interpolation', 0), root_motion=bool(props.get('bEnableRootMotion', False)),
                fps_exact=fps_exact, max_raw_xyz_sq=xyz_sq_max, raw_keys_xyz_sq_over_1=xyz_sq_over,
                raw_rotation_keys=nkeys_rot, raw_key_hemisphere_flips=raw_flips, output_sign_flips=sign_flips,
                warnings=warnings)
    out.update(tracked=tracked, animated=animated, additive_type=np.int64(additive),
               ref_pose_type=np.int64(info['ref_pose_type']), notifies=json.dumps(notifies),
               track_info=json.dumps(info_tracks), info=json.dumps(info, default=str))
    return out, info, notifies, tracks


def save_npz(path, out):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    np.savez_compressed(path, **out)


def clip_name(path):
    n = os.path.splitext(os.path.basename(path))[0]
    return n


def summarize(out, info, notifies):
    """Per-clip summary.  Travel is measured on component-space bone positions (cm): 'net' = |end - start|,
    'path' = summed per-frame displacement, 'horizontal_net' = net travel in the XY (ground) plane."""
    names = [str(n) for n in out['bone_names']]
    P = component_positions(out)
    fps = float(out['fps'])
    warnings = list(info['warnings'])

    def travel(b):
        if b not in names:
            return None
        p = P[:, names.index(b)]
        step = np.linalg.norm(np.diff(p, axis=0), axis=1) if len(p) > 1 else np.zeros(1)
        return dict(start=p[0].round(3).tolist(), end=p[-1].round(3).tolist(), net=round(float(np.linalg.norm(p[-1] - p[0])), 3),
                    horizontal_net=round(float(np.linalg.norm(p[-1, :2] - p[0, :2])), 3), path=round(float(step.sum()), 3),
                    max_step=round(float(step.max()), 3), max_step_frame=int(step.argmax()))
    hips = travel('Hips')
    if hips and fps and hips['max_step'] * fps > 3000:   # > 30 m/s for the pelvis: a cut / teleport in the data
        warnings.append('Hips jumps %.0f cm between frames %d and %d (%.0f m/s): discontinuity in the animation data' % (
            hips['max_step'], hips['max_step_frame'], hips['max_step_frame'] + 1, hips['max_step'] * fps / 100))
    root_bones = {b: travel(b) for b in ('root', 'joint_root', 'Reference', 'pivot')}
    return dict(num_frames=int(out['num_frames']), play_length=float(out['play_length']), fps=fps,
                tracks=int(info['num_tracks']), tracked_bones=int(len(out['tracked'])),
                animated_bones=int(len(out['animated'])), codec=info['codec'], scale_streams=info['scale_offsets'] > 0,
                additive_type=info['additive_type'], ref_pose_type=info['ref_pose_type'],
                root_motion_enabled=info['root_motion'], root_travel=root_bones['root'], hips_travel=hips,
                other_root_bones_travel={k: v for k, v in root_bones.items() if k != 'root'},
                notify_count=len(notifies),
                notify_payloads_decoded=sum(1 for n in notifies if n.get('payload', {}).get('decoded')),
                notify_classes=sorted(set(n['cls'] for n in notifies if n['cls'])), warnings=warnings)


def component_positions(out, frames=None):
    """Component-space bone positions (F,B,3) from the local q/t/s (parent-first order)."""
    q, t, s, par = out['q'], out['t'], out['s'], out['bone_parents']
    if frames is not None:
        q, t, s = q[frames], t[frames], s[frames]
    F, B = q.shape[:2]
    cq = np.zeros((F, B, 4))
    ct = np.zeros((F, B, 3))
    cs = np.zeros((F, B, 3))
    for b in range(B):
        p = par[b]
        if p < 0:
            cq[:, b], ct[:, b], cs[:, b] = q[:, b], t[:, b], s[:, b]
        else:
            cq[:, b] = qmul(cq[:, p], q[:, b])
            ct[:, b] = ct[:, p] + qrot(cq[:, p], cs[:, p] * t[:, b])
            cs[:, b] = cs[:, p] * s[:, b]
    return ct


def main(argv):
    if len(argv) >= 2 and argv[1] == '--batch':
        args = argv[2:]
        dirs, skel_path, out_dir, summary_path = [], None, None, None
        i = 0
        while i < len(args):
            if args[i] == '--skeleton':
                skel_path = args[i + 1]
                i += 2
            elif args[i] == '--out':
                out_dir = args[i + 1]
                i += 2
            elif args[i] == '--summary':
                summary_path = args[i + 1]
                i += 2
            else:
                dirs.append(args[i])
                i += 1
        if not dirs or not skel_path or not out_dir:
            print(__doc__)
            return 2
        skel = load_skeleton(skel_path)
        summary = {}
        nfail = 0
        for dd in dirs:
            for f in sorted(os.listdir(dd)):
                if not f.endswith('.uasset'):
                    continue
                path = os.path.join(dd, f)
                name = clip_name(path)
                try:
                    out, info, notifies, _ = decode_clip(path, skel)
                    save_npz(os.path.join(out_dir, name + '.npz'), out)
                    sm = summarize(out, info, notifies)
                    summary[name] = dict(folder=os.path.basename(os.path.normpath(dd)), ok=True, **sm)
                    print('%-44s ok  %4d frames %6.3fs %3d tracks %2d notifies%s' % (
                        name, out['num_frames'], out['play_length'], info['num_tracks'], len(notifies),
                        ('  WARN: ' + '; '.join(sm['warnings'])) if sm['warnings'] else ''))
                except Exception as e:
                    nfail += 1
                    summary[name] = dict(folder=os.path.basename(os.path.normpath(dd)), ok=False, error=str(e))
                    print('%-44s FAILED: %s' % (name, e))
        if summary_path:
            with open(summary_path, 'w') as fh:
                json.dump(summary, fh, indent=1)
        print('%d clips, %d failed' % (len(summary), nfail))
        return 1 if nfail else 0
    if len(argv) != 4:
        print(__doc__)
        return 2
    skel = load_skeleton(argv[2])
    out, info, notifies, _ = decode_clip(argv[1], skel)
    save_npz(argv[3], out)
    print(json.dumps(summarize(out, info, notifies), indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
