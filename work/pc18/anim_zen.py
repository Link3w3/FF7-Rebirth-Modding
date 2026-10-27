"""A cooked (zen) AnimSequence of FF7 Rebirth (ACL) -> each bone's local rotation and translation per frame, on the
skeleton it was made for (its reference skeleton read from the skeleton's own package: bones without a track keep the
reference pose).
    from anim_zen import Skeleton, decode
    sk = Skeleton(skeleton_package_bytes); LQ, LT, fps = decode(anim_package_bytes, sk)   # (frames, bones, 4/3)"""
import struct, sys
import numpy as np
sys.path[:0] = ['/work/acl', '/work/cs', '/work/iostore', '/work/seraph1026/mesh/tools']
import acl13
from zen import Zen
import meshskel


class Skeleton:
    def __init__(self, data):
        z = Zen(data)
        _off, bones, pose, _end = meshskel.find_refskel(data, z)
        self.names = [n for n, p in bones]
        self.parents = [p for n, p in bones]
        self.ref_q = np.array([q for q, t, s in pose], dtype=np.float64)
        self.ref_t = np.array([t for q, t, s in pose], dtype=np.float64)
        self.index = {n: i for i, n in enumerate(self.names)}


def track_map(data, n, nbones):
    """the compressed tracks' bones: an int32 count n, then n distinct bone indices, the first 0 (Trans)"""
    pat = struct.pack('<i', n)
    p = data.find(pat)
    found = []
    while p >= 0:
        if p + 4 + 4 * n <= len(data):
            vals = struct.unpack_from('<%di' % n, data, p + 4)
            if all(0 <= v < nbones for v in vals) and len(set(vals)) == n and vals[0] == 0:
                found.append(list(vals))
        p = data.find(pat, p + 1)
    if not found:
        raise ValueError('no track map for %d tracks' % n)
    return found[0]


def decode(data, sk):
    c = acl13.Clip(data)
    rot, trans, scale = c.decompress()
    bones = track_map(data, c.num_bones, len(sk.names))
    S = c.num_samples
    LQ = np.repeat(sk.ref_q[None], S, 0).copy()
    LT = np.repeat(sk.ref_t[None], S, 0).copy()
    for t, b in enumerate(bones):
        LQ[:, b] = rot[:, t]
        LT[:, b] = trans[:, t]
    # (quaternions on one hemisphere through time, for blending)
    for b in range(LQ.shape[1]):
        q = LQ[:, b]
        for f in range(1, S):
            if np.dot(q[f], q[f - 1]) < 0:
                q[f] = -q[f]
    return LQ, LT, float(c.sample_rate), bones


def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0); bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz], -1)


def qrot(q, v):
    x, y, z, w = np.moveaxis(q, -1, 0); vx, vy, vz = np.moveaxis(v, -1, 0)
    tx = 2 * (y * vz - z * vy); ty = 2 * (z * vx - x * vz); tz = 2 * (x * vy - y * vx)
    return np.stack([vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx)], -1)


def component(LQ, LT, parents):
    GQ = np.zeros_like(LQ); GT = np.zeros_like(LT)
    for i, p in enumerate(parents):
        if p < 0:
            GQ[:, i] = LQ[:, i]; GT[:, i] = LT[:, i]
        else:
            GQ[:, i] = qmul(GQ[:, p], LQ[:, i]); GT[:, i] = GT[:, p] + qrot(GQ[:, p], LT[:, i])
    return GQ, GT
