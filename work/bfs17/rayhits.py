import numpy as np
def ray_hits(orig, dirn, V):
    """All hits of a ray with triangles V (T,3,3): distances t>0 (Moller-Trumbore, vectorised)"""
    e1 = V[:, 1] - V[:, 0]; e2 = V[:, 2] - V[:, 0]
    pv = np.cross(dirn, e2)
    det = (e1 * pv).sum(1)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1), 0)
    tv = orig - V[:, 0]
    u = (tv * pv).sum(1) * inv
    qv = np.cross(tv, e1)
    v = (qv @ dirn) * inv
    t = (qv * e2).sum(1) * inv
    hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-6)
    return t[hit], np.nonzero(hit)[0]
