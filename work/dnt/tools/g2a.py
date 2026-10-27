"""Koei Tecmo G2A motions (Dissidia NT's .g1a files, chunk 'G2A_' version 0030; also 0400 / 0500).

Each animated joint (by G1MS global id) has up to 3 splines: 0 rotation, 1 translation, 2 scale. A spline has key
times (frames) and per segment a cubic, quantized in 32 bytes: 4 rows (constant, linear, quadratic, cubic terms), each
row three 20-bit mantissas plus a shared 4-bit exponent. Rotations are rotation vectors (axis * angle). Decoded the way
Project G1M (G2A.h / Utils.h function1, function2) does; rotations are in the G1MS quaternion convention (Project G1M
conjugates both the G1MS rest and the G2A keys for Noesis, so the raw values match each other).

    read(path) -> Motion(fps, length, tracks{global id: {'rot': (N,4) xyzw, 'pos': (N,3), 'scl': (N,3)}})
    N = length + 1 frames (frame `length` is the end of the last segment)."""
import struct
import sys

import numpy as np


class Motion:
    def __init__(self, fps, length, tracks, version):
        self.fps, self.length, self.tracks, self.version = fps, length, tracks, version

    @property
    def frames(self):
        return self.length + 1


def _cubic(q, t):
    """q: (K, 4) uint64 rows (constant, linear, quadratic, cubic); t: (K, L) fractions -> (K, L, 3)."""
    q = q.astype(np.uint64)
    e = (((q >> np.uint64(0x25)) & np.uint64(0x7800000)) + np.uint64(0x32000000)).astype(np.uint32).view(np.float32)
    v0 = ((q >> np.uint64(28)) & np.uint64(0xFFFFF000)).astype(np.uint32).view(np.int32).astype(np.float64)
    v1 = ((q >> np.uint64(8)) & np.uint64(0xFFFFF000)).astype(np.uint32).view(np.int32).astype(np.float64)
    v2 = ((q << np.uint64(12)) & np.uint64(0xFFFFFFFF)).astype(np.uint32).view(np.int32).astype(np.float64)
    c = np.stack([v0, v1, v2], -1) * e.astype(np.float64)[..., None]       # (K, 4, 3)
    t = t[..., None]
    return c[:, None, 0] + c[:, None, 1] * t + c[:, None, 2] * t * t + c[:, None, 3] * t * t * t


def _rotvec_quat(v):
    a = np.linalg.norm(v, axis=-1, keepdims=True)
    s, c = np.sin(a * 0.5), np.cos(a * 0.5)
    k = np.where(a > 0.000011920929, s / np.maximum(a, 1e-30), 0.5)
    return np.concatenate([v * k, c], -1)


def read(path):
    b = open(path, 'rb').read() if isinstance(path, str) else path
    magic, ver, size = struct.unpack_from('<4s4sI', b, 0)
    assert magic in (b'G2A_', b'_A2G'), magic
    vnum = struct.unpack_from('<I', b, 4)[0]
    g2a5 = vnum == 0x30303530
    g2a4 = vnum == 0x30303430
    fps, packed, timing_size, entry_count = struct.unpack_from('<fIII', b, 12)
    length = packed & 0x3FFF
    info_size = (packed >> 18) & 0x3FFC
    cp = 28 + (4 if (g2a5 or g2a4) else 0)
    tracks = {}
    last_id, gofs = 0, 0
    nfr = length + 1
    for i in range(info_size >> 2):
        p = struct.unpack_from('<I', b, cp + 4 * i)[0]
        nspl = p & 0xF
        bid = (p >> 4) & (0xFF if g2a5 else 0x3FF)
        toff = (p >> 12) if g2a5 else (p >> 14)
        if bid < last_id:
            gofs += 1
        last_id = bid
        bid += gofs * (256 if g2a5 else 1024)
        off = cp + info_size + toff
        off -= off % 4
        tr = {}
        for _ in range(nspl):
            op, nk, first = struct.unpack_from('<HHI', b, off)
            off += 8
            times = list(struct.unpack_from('<%dH' % nk, b, off))
            off += 2 * nk
            off += (-off) % 4
            q = np.frombuffer(b, np.uint64, 4 * nk, cp + info_size + timing_size + first * 32).reshape(nk, 4)
            out = np.zeros((nfr, 3))
            if nk == 1:
                out[:] = _cubic(q[:1], np.zeros((1, 1)))[0, 0]
            else:
                if times[-1] != length:
                    times.append(length)
                for k in range(len(times) - 1):
                    k1, k2 = times[k], times[k + 1]
                    if k2 <= k1:
                        continue
                    n = k2 - k1
                    last = (k == len(times) - 2)
                    ls = np.arange(n + (1 if last else 0))
                    vals = _cubic(q[k:k + 1], (ls / n)[None, :])[0]
                    out[k1:k1 + len(ls)] = vals
                if times[0] > 0:
                    out[:times[0]] = out[times[0]]
            name = {0: 'rot', 1: 'pos', 2: 'scl'}.get(op)
            if name == 'rot':
                tr['rot'] = _rotvec_quat(out)
            elif name:
                tr[name] = out
        tracks[bid] = tr
    return Motion(fps, length, tracks, ver)


if __name__ == '__main__':
    for f in sys.argv[1:]:
        m = read(f)
        kinds = {}
        for g, tr in m.tracks.items():
            for k in tr:
                kinds[k] = kinds.get(k, 0) + 1
        print('%s: %.0f fps, %d frames, %d joints (ids %d-%d), splines %s' % (
            f.split('/')[-1], m.fps, m.frames, len(m.tracks), min(m.tracks), max(m.tracks), kinds))
