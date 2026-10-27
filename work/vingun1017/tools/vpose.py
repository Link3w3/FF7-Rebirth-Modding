"""Vincent's cutscene motions (ACL, on PC0011_00_Skeleton) -> component-space bone transforms per frame."""
import sys, struct
sys.path += ['/work/acl', '/work/evil1013/tools']
import numpy as np
import acl13, zenskel

SKEL = '/work/gunmoves/pkgs2/Character__Player__PC0011_00_Vincent_Standard__Model__PC0011_00_Skeleton.uasset'
BL = zenskel.bones(open(SKEL, 'rb').read())
NAMES = [b[0] for b in BL]
PARENTS = [b[1] for b in BL]
IDX = {n: i for i, n in enumerate(NAMES)}
REF_T = np.array([b[2] for b in BL], dtype=np.float64)
REF_Q = np.array([b[3] for b in BL], dtype=np.float64)


def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0); bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw*bx + ax*bw + ay*bz - az*by, aw*by - ax*bz + ay*bw + az*bx, aw*bz + ax*by - ay*bx + az*bw, aw*bw - ax*bx - ay*by - az*bz], -1)


def qrot(q, v):
    x, y, z, w = np.moveaxis(q, -1, 0); vx, vy, vz = np.moveaxis(v, -1, 0)
    tx = 2*(y*vz - z*vy); ty = 2*(z*vx - x*vz); tz = 2*(x*vy - y*vx)
    return np.stack([vx + w*tx + (y*tz - z*ty), vy + w*ty + (z*tx - x*tz), vz + w*tz + (x*ty - y*tx)], -1)


def track_map(data, n, nbones):
    pat = struct.pack('<i', n)
    p = data.find(pat)
    while p >= 0:
        if p + 4 + 4 * n <= len(data):
            vals = struct.unpack_from('<%di' % n, data, p + 4)
            if all(0 <= v < nbones for v in vals) and len(set(vals)) == n and vals[0] == 0:
                return list(vals)
        p = data.find(pat, p + 1)
    return None


def load(data):
    c = acl13.Clip(data)
    rot, trans, scale = c.decompress()
    bones = track_map(data, c.num_bones, len(NAMES))
    if not bones:
        raise ValueError('no track map')
    S = c.num_samples
    LQ = np.repeat(REF_Q[None], S, 0).copy(); LT = np.repeat(REF_T[None], S, 0).copy()
    for t, b in enumerate(bones):
        LQ[:, b] = rot[:, t]; LT[:, b] = trans[:, t]
    return c, bones, LQ, LT


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
