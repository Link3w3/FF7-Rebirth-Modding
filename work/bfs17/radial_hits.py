"""All hits of rays from one centre (through given points) with a triangle set, grouped by angular cells for speed.
    hits(centre, points, V) -> list (per point) of sorted hit distances along the ray from the centre."""
import numpy as np

def _dirs(P):
    n = np.linalg.norm(P, axis=-1, keepdims=True)
    return P / np.maximum(n, 1e-12)

def hits(centre, points, V, cell_deg=3.0):
    U = _dirs(points - centre)                                  # (N,3)
    C = V - centre                                              # (T,3,3)
    cd = _dirs(C.mean(1))                                       # centroid directions
    vd = _dirs(C)
    rad = np.degrees(np.arccos(np.clip((vd * cd[:, None, :]).sum(2), -1, 1))).max(1)   # angular radius of each triangle
    th = np.degrees(np.arccos(np.clip(U[:, 2], -1, 1)))
    ph = np.degrees(np.arctan2(U[:, 1], U[:, 0]))
    key = (np.floor(th / cell_deg).astype(int) * 1000 + np.floor((ph + 180) / cell_deg).astype(int))
    out = [None] * len(points)
    e1 = C[:, 1] - C[:, 0]; e2 = C[:, 2] - C[:, 0]
    order = np.argsort(key)
    ks, starts = np.unique(key[order], return_index=True)
    ends = np.r_[starts[1:], len(order)]
    half = cell_deg * 0.75 + 0.01
    for k, s, e in zip(ks, starts, ends):
        idx = order[s:e]
        cdir = _dirs(U[idx].mean(0))
        spread = np.degrees(np.arccos(np.clip(U[idx] @ cdir, -1, 1))).max()
        ang = np.degrees(np.arccos(np.clip(cd @ cdir, -1, 1)))
        cand = np.nonzero(ang <= rad + spread + 0.05)[0]
        if len(cand) == 0:
            for i in idx:
                out[i] = np.zeros(0)
            continue
        D = U[idx]                                               # (n,3)
        E1, E2, V0 = e1[cand], e2[cand], C[cand, 0]              # (m,3)
        pv = np.cross(D[:, None, :], E2[None, :, :])             # (n,m,3)
        det = (E1[None] * pv).sum(2)
        ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        tv = -V0[None]                                           # origin (0) - V0
        u = (tv * pv).sum(2) * inv
        qv = np.cross(np.broadcast_to(tv, pv.shape), E1[None])
        v = (qv * D[:, None, :]).sum(2) * inv
        t = (qv * E2[None]).sum(2) * inv
        hit = ok & (u >= -1e-7) & (v >= -1e-7) & (u + v <= 1 + 1e-7) & (t > 1e-6)
        for a, i in enumerate(idx):
            out[i] = np.sort(t[a][hit[a]])
    return out
