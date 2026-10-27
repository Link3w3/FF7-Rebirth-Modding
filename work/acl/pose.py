"""Decoded ACL clip -> component-space bone positions on PC0010_00_Skeleton (ref pose for bones without tracks)."""
import sys
sys.path[:0] = ['/work/acl', '/work/rootmotion', '/tmp/scratch/kh2turn', '/work/bnm/tools']
import numpy as np
import acl13, tracks
import skel as SK
SKP = '/work/bnm/Content/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00_Skeleton'
_off, BL = SK.load_cooked(SKP + '.uasset', SKP + '.uexp')
NAMES = [b[0] for b in BL]
PARENTS = [b[1] for b in BL]
IDX = {n: i for i, n in enumerate(NAMES)}
REF_Q = np.array([b[2] for b in BL]); REF_T = np.array([b[3] for b in BL])

def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0); bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw*bx + ax*bw + ay*bz - az*by, aw*by - ax*bz + ay*bw + az*bx, aw*bz + ax*by - ay*bx + az*bw, aw*bw - ax*bx - ay*by - az*bz], -1)
def qrot(q, v):
    x, y, z, w = np.moveaxis(q, -1, 0); vx, vy, vz = np.moveaxis(v, -1, 0)
    tx = 2*(y*vz - z*vy); ty = 2*(z*vx - x*vz); tz = 2*(x*vy - y*vx)
    return np.stack([vx + w*tx + (y*tz - z*ty), vy + w*ty + (z*tx - x*tz), vz + w*tz + (x*ty - y*tx)], -1)

def track_map(data, n):
    """The compressed track -> bone index table: int32 n then n distinct bone indices (anywhere in the package)."""
    import struct
    pat = struct.pack('<i', n)
    p = data.find(pat)
    while p >= 0:
        if p + 4 + 4 * n <= len(data):
            vals = struct.unpack_from('<%di' % n, data, p + 4)
            if all(0 <= v < len(NAMES) for v in vals) and len(set(vals)) == n and vals[0] == 0:
                return list(vals)
        p = data.find(pat, p + 1)
    return None

def load(data):
    c = acl13.Clip(data)
    rot, trans, scale = c.decompress()
    bones = track_map(data, c.num_bones)
    if not bones:
        raise ValueError('no track map')
    S = c.num_samples
    LQ = np.repeat(REF_Q[None], S, 0).astype(np.float64); LT = np.repeat(REF_T[None], S, 0).astype(np.float64)
    for t, b in enumerate(bones):
        if 0 <= b < len(NAMES):
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
