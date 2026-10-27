"""Pure Python/numpy decompressor for ACL 1.x uniformly sampled clips (as cooked by FF7 Rebirth's UE4 ACL plugin):
variable/fixed rotation and vector formats, clip and segment range reduction, default/constant/animated tracks."""
import struct
import numpy as np

TAG = 0xac10ac10
BIT_RATE_BITS = [0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 32]
RAW_BIT_RATE = len(BIT_RATE_BITS) - 1
# rotation formats: 0 Quat_128, 1 QuatDropW_96, 2 QuatDropW_48, 3 QuatDropW_32, 4 QuatDropW_Variable
# vector formats: 0 Vector3_96, 1 Vector3_48, 2 Vector3_32, 3 Vector3_Variable


class Bits:
    def __init__(self, data):
        self.d = data

    def read(self, bit_offset, num_bits):
        """MSB-first bit stream (ACL packs big-endian)."""
        byte = bit_offset >> 3
        chunk = self.d[byte:byte + 9].ljust(9, b'\0')
        v = int.from_bytes(chunk, 'big')
        shift = 72 - (bit_offset & 7) - num_bits
        return (v >> shift) & ((1 << num_bits) - 1)


def _bit(words, i):
    return (words[i >> 5] >> (31 - (i & 31))) & 1


class Clip:
    def __init__(self, data, at=None):
        if at is None:
            at = data.find(struct.pack('<I', TAG))
            if at < 0:
                raise ValueError('no ACL clip')
            at -= 8
        self.d = data
        self.base = at
        size, h, tag, ver, alg = struct.unpack_from('<IIIHB', data, at)
        assert tag == TAG, hex(tag)
        self.version, self.size = ver, size
        ch = at + 16
        self.ch = ch
        (self.num_bones, self.num_segments, self.rot_fmt, self.trans_fmt, self.scale_fmt, self.clip_rr, self.seg_rr,
         self.has_scale, self.default_scale, _pad, self.num_samples, self.sample_rate, self.seg_start,
         self.seg_hdr, self.def_bs, self.const_bs, self.const_data, self.clip_range) = struct.unpack_from('<HHBBBBBBBBIfHHHHHH', data, ch)
        self.per = 3 if self.has_scale else 2
        nbits = self.num_bones * self.per
        words = (nbits + 31) // 32
        self.dw = struct.unpack_from('<%dI' % words, data, ch + self.def_bs)
        self.cw = struct.unpack_from('<%dI' % words, data, ch + self.const_bs)
        self.kind = []  # per bone, per component: 'D', 'C', 'A'
        for b in range(self.num_bones):
            k = []
            for s in range(self.per):
                i = b * self.per + s
                k.append('D' if _bit(self.dw, i) else ('C' if _bit(self.cw, i) else 'A'))
            self.kind.append(k)
        self.segments = []
        # segment start sample indices (one segment: none stored), then a 16-byte header each
        if self.num_segments > 1 and self.seg_start != 0xFFFF:
            starts = list(struct.unpack_from('<%dI' % self.num_segments, data, ch + self.seg_start))
        else:
            starts = [0]
        starts.append(self.num_samples)
        p = ch + self.seg_hdr
        for s in range(self.num_segments):
            bits, fmt_off, range_off, track_off = struct.unpack_from('<IIII', data, p)
            p += 16
            self.segments.append(dict(start=starts[s], samples=starts[s + 1] - starts[s], bits=bits, fmt=ch + fmt_off,
                                      range=ch + range_off, track=ch + track_off))

    def _rot_dropw(self, fmt):
        return fmt != 0

    def decompress(self):
        """(rot (S, B, 4) xyzw, trans (S, B, 3), scale (S, B, 3)) for every sample."""
        S, B = self.num_samples, self.num_bones
        rot = np.zeros((S, B, 4)); rot[..., 3] = 1.0
        trans = np.zeros((S, B, 3))
        scale = np.ones((S, B, 3))
        if self.has_scale and not self.default_scale:
            scale[:] = 0.0
        d = self.d
        # constant tracks
        p = self.ch + self.const_data
        for b in range(B):
            for s in range(self.per):
                if self.kind[b][s] != 'C':
                    continue
                if s == 0:
                    if self.rot_fmt == 0:
                        q = struct.unpack_from('<4f', d, p); p += 16
                    else:
                        x, y, z = struct.unpack_from('<3f', d, p); p += 12
                        w = np.sqrt(max(0.0, 1.0 - x * x - y * y - z * z))
                        q = (x, y, z, w)
                    rot[:, b] = q
                else:
                    v = struct.unpack_from('<3f', d, p); p += 12
                    (trans if s == 1 else scale)[:, b] = v
        # clip range data: per animated component in bone order
        clip_ranges = {}
        p = self.ch + self.clip_range
        for b in range(B):
            for s in range(self.per):
                if self.kind[b][s] != 'A':
                    continue
                flag = 1 << s
                if self.clip_rr & flag:
                    if s == 0 and self.rot_fmt == 0:
                        mn = struct.unpack_from('<4f', d, p); ex = struct.unpack_from('<4f', d, p + 16); p += 32
                    else:
                        mn = struct.unpack_from('<3f', d, p); ex = struct.unpack_from('<3f', d, p + 12); p += 24
                    clip_ranges[(b, s)] = (np.array(mn), np.array(ex))
        animated = [(b, s) for b in range(B) for s in range(self.per) if self.kind[b][s] == 'A']
        bits = Bits(d)
        for seg in self.segments:
            fmt_bytes = d[seg['fmt']:seg['fmt'] + len(animated)]
            # segment range data, per animated component (6 bytes each when segment range reduction is on for its kind)
            seg_ranges = {}
            q = seg['range']
            variable = {0: self.rot_fmt == 4, 1: self.trans_fmt == 3, 2: self.scale_fmt == 3}
            fi = 0
            rates = {}
            for (b, s) in animated:
                if variable[s]:
                    rates[(b, s)] = fmt_bytes[fi]
                    fi += 1
            for (b, s) in animated:
                if (self.seg_rr & (1 << s)) and variable[s]:
                    seg_ranges[(b, s)] = d[q:q + 6]
                    q += 6
            track_base = seg['track'] * 8
            for k in range(seg['samples']):
                bit = track_base + k * seg['bits']
                for (b, s) in animated:
                    rate = rates.get((b, s))
                    dropw = s != 0 or self._rot_dropw(self.rot_fmt)
                    if rate is not None:
                        nb = BIT_RATE_BITS[rate]
                        if rate == 0:          # constant in this segment: the value is in the segment range data (3 x u16)
                            raw = seg_ranges.get((b, s), b'\0' * 6)
                            v = np.array(struct.unpack('>3H', raw), dtype=np.float64) / 65535.0
                            seg_applied = True
                        elif rate == RAW_BIT_RATE:  # full floats
                            v = np.array([struct.unpack('>f', bits.read(bit + 32 * i, 32).to_bytes(4, 'big'))[0] for i in range(3)])
                            bit += 96
                            seg_applied = True
                            raw_value = True
                        else:
                            v = np.array([bits.read(bit + nb * i, nb) for i in range(3)], dtype=np.float64) / ((1 << nb) - 1)
                            bit += nb * 3
                            seg_applied = False
                        if rate == RAW_BIT_RATE:
                            value = v
                        else:
                            if not seg_applied and (b, s) in seg_ranges:
                                r = seg_ranges[(b, s)]
                                rb = np.frombuffer(r, dtype=np.uint8).astype(np.float64)
                                mn = rb[0:3] / 255.0
                                ex = rb[3:6] / 255.0
                                v = v * ex + mn
                            value = v
                            if (b, s) in clip_ranges:
                                mn, ex = clip_ranges[(b, s)]
                                value = value * ex + mn
                    else:
                        # fixed formats: whole floats as they are in memory (little-endian), each sample of the track
                        # starting on a 4-byte boundary of the track data (ACL's memcpy of the packed sample)
                        fmt = self.rot_fmt if s == 0 else (self.trans_fmt if s == 1 else self.scale_fmt)
                        bit = track_base + ((bit - track_base + 31) // 32) * 32
                        if s == 0 and fmt == 0:
                            value = np.array([struct.unpack('<f', bits.read(bit + 32 * i, 32).to_bytes(4, 'big'))[0] for i in range(4)])
                            bit += 128
                        elif (s == 0 and fmt == 1) or (s != 0 and fmt == 0):
                            value = np.array([struct.unpack('<f', bits.read(bit + 32 * i, 32).to_bytes(4, 'big'))[0] for i in range(3)])
                            bit += 96
                        else:
                            raise NotImplementedError('fixed format %d' % fmt)
                        if (b, s) in clip_ranges:
                            mn, ex = clip_ranges[(b, s)]
                            value = value * ex + mn
                    t = seg['start'] + k
                    if s == 0:
                        if len(value) == 4:
                            rot[t, b] = value
                        else:
                            x, y, z = value
                            rot[t, b] = (x, y, z, np.sqrt(max(0.0, 1.0 - x * x - y * y - z * z)))
                    elif s == 1:
                        trans[t, b] = value
                    else:
                        scale[t, b] = value
        return rot, trans, scale
