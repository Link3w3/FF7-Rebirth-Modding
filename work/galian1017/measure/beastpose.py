"""The Galian Beast's animations decoded offline (the project's legacy cooked copies: ACL 1.x): component-space bone
transforms on EB2160_00_Skeleton, for measuring root travel, facing and turns."""
import sys, struct, os
sys.path[:0] = ['/work/acl', '/work/rootmotion', '/tmp/scratch/kh2turn',
                '/work/bnm/tools']
import numpy as np
import acl13
import skel as SK
ROOT = '/work/galian1017/legacy'
SKP = ROOT + '/Character/Enemy/EB2160_00_VincentValentine_Standard/Model/EB2160_00_Skeleton'
_off, BL = SK.load_cooked(SKP + '.uasset', SKP + '.uexp')
NAMES = [b[0] for b in BL]
PARENTS = [b[1] for b in BL]
IDX = {n: i for i, n in enumerate(NAMES)}
REF_Q = np.array([b[2] for b in BL], dtype=np.float64)
REF_T = np.array([b[3] for b in BL], dtype=np.float64)


def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0); bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw*bx + ax*bw + ay*bz - az*by, aw*by - ax*bz + ay*bw + az*bx, aw*bz + ax*by - ay*bx + az*bw, aw*bw - ax*bx - ay*by - az*bz], -1)


def qrot(q, v):
    x, y, z, w = np.moveaxis(q, -1, 0); vx, vy, vz = np.moveaxis(v, -1, 0)
    tx = 2*(y*vz - z*vy); ty = 2*(z*vx - x*vz); tz = 2*(x*vy - y*vx)
    return np.stack([vx + w*tx + (y*tz - z*ty), vy + w*ty + (z*tx - x*tz), vz + w*tz + (x*ty - y*tx)], -1)


def track_map(data, n):
    pat = struct.pack('<i', n)
    p = data.find(pat)
    tag = data.find(struct.pack('<I', acl13.TAG))
    best = None
    while p >= 0:
        if p + 4 + 4 * n <= len(data):
            vals = struct.unpack_from('<%di' % n, data, p + 4)
            if all(0 <= v < len(NAMES) for v in vals) and len(set(vals)) == n and vals[0] == 0:
                best = list(vals)
                if tag < 0 or p < tag:
                    pass
        p = data.find(pat, p + 1)
    return best


def load(key):
    """'Battle00/B_Walk01_1' -> (clip, local quats [S,B,4], local trans [S,B,3], sample rate)."""
    base = ROOT + '/Motion/Enemy/EB2160_VincentValentine/' + key
    data = open(base + '.uasset', 'rb').read() + open(base + '.uexp', 'rb').read()
    c = acl13.Clip(data)
    rot, trans, scale = c.decompress()
    bones = track_map(data, c.num_bones)
    if not bones:
        raise ValueError('no track map: ' + key)
    S = c.num_samples
    LQ = np.repeat(REF_Q[None], S, 0)
    LT = np.repeat(REF_T[None], S, 0)
    for t, b in enumerate(bones):
        LQ[:, b] = rot[:, t]
        LT[:, b] = trans[:, t]
    return c, LQ, LT


def component(LQ, LT):
    S, B = LQ.shape[:2]
    GQ = np.zeros_like(LQ); GT = np.zeros_like(LT)
    for i in range(B):
        p = PARENTS[i]
        if p < 0:
            GQ[:, i] = LQ[:, i]; GT[:, i] = LT[:, i]
        else:
            GQ[:, i] = qmul(GQ[:, p], LQ[:, i]); GT[:, i] = GT[:, p] + qrot(GQ[:, p], LT[:, i])
    return GQ, GT


def yaw_of(q):
    """Yaw (degrees, about +Z, +X towards +Y) of the bone's X axis."""
    x = qrot(q, np.array([1.0, 0.0, 0.0]))
    return np.degrees(np.arctan2(x[..., 1], x[..., 0]))


def unwrap(a):
    return np.degrees(np.unwrap(np.radians(a)))
