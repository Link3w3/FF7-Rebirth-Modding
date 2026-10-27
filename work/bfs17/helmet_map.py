"""The helmet's inner surface seen from inside the head: a spherical depth map (first surface along each direction from
a centre in the head) of the Bahamut's own triangles near the head (Rebirth's face slots left out).
    helmet_map.py <rerig.npz> <out.npz> [res_deg]"""
import sys
import numpy as np

def build(pos, tri, keep, centre, res=1.0, rmax=60.0):
    nt, npp = int(round(180 / res)), int(round(360 / res))
    depth = np.full((nt, npp), np.inf)
    owner = np.full((nt, npp), -1, dtype=np.int64)
    V = pos[tri[keep]] - centre                      # (T,3,3)
    ids = np.nonzero(keep)[0]
    near = np.linalg.norm(V, axis=2).min(1) < rmax
    V, ids = V[near], ids[near]
    # samples per triangle from its angular size
    dirs = V / np.linalg.norm(V, axis=2, keepdims=True)
    ang = np.degrees(np.arccos(np.clip(np.einsum('tij,tkj->tik', dirs, dirs), -1, 1))).reshape(len(V), -1).max(1)
    k = np.clip(np.ceil(ang / (res * 0.5)).astype(int) + 1, 2, 200)
    for kk in np.unique(k):
        sel = np.nonzero(k == kk)[0]
        a, b = np.meshgrid(np.arange(kk + 1), np.arange(kk + 1), indexing='ij')
        m = (a + b) <= kk
        u, v = a[m] / kk, b[m] / kk
        w = 1 - u - v
        P = (w[None, :, None] * V[sel, 0][:, None, :] + u[None, :, None] * V[sel, 1][:, None, :] + v[None, :, None] * V[sel, 2][:, None, :])
        P = P.reshape(-1, 3)
        own = np.repeat(ids[sel], m.sum())
        r = np.linalg.norm(P, axis=1)
        th = np.degrees(np.arccos(np.clip(P[:, 2] / np.maximum(r, 1e-9), -1, 1)))
        ph = np.degrees(np.arctan2(P[:, 1], P[:, 0])) % 360
        it = np.minimum((th / res).astype(int), nt - 1)
        ip = np.minimum((ph / res).astype(int), npp - 1)
        flat = it * npp + ip
        order = np.lexsort((r, flat))
        flat, r, own = flat[order], r[order], own[order]
        first = np.r_[True, flat[1:] != flat[:-1]]
        f, rr, oo = flat[first], r[first], own[first]
        cur = depth.reshape(-1)[f]
        better = rr < cur
        depth.reshape(-1)[f[better]] = rr[better]
        owner.reshape(-1)[f[better]] = oo[better]
    return depth, owner

def lookup(depth, centre, pts, res=1.0):
    P = pts - centre
    r = np.linalg.norm(P, axis=1)
    th = np.degrees(np.arccos(np.clip(P[:, 2] / np.maximum(r, 1e-9), -1, 1)))
    ph = np.degrees(np.arctan2(P[:, 1], P[:, 0])) % 360
    nt, npp = depth.shape
    it = np.minimum((th / res).astype(int), nt - 1)
    ip = np.minimum((ph / res).astype(int), npp - 1)
    return r, depth[it, ip], it, ip

if __name__ == '__main__':
    r = np.load(sys.argv[1], allow_pickle=True)
    res = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    slots = [str(s) for s in r['slots']]
    face = np.array([s.startswith('PC0010_00') or s == 'Common_Mouth' for s in slots])
    keep = ~face[r['tmat']]
    names = list(r['bone_names'])
    head = r['bone_ct'][names.index('C_Head_a')]
    centre = head + np.array([0.0, 0.0, 9.0])     # about the middle of the skull
    depth, owner = build(r['pos'], r['tri'], keep, centre, res)
    np.savez_compressed(sys.argv[2], depth=depth, owner=owner, centre=centre, res=res)
    cov = np.isfinite(depth)
    print('centre', centre, 'covered %.1f %% of directions' % (100 * cov.mean()))
    nt = depth.shape[0]
    for t0 in range(0, 180, 15):
        row = depth[int(t0 / res):int((t0 + 15) / res)]
        fin = row[np.isfinite(row)]
        print('theta %3d-%3d: covered %5.1f %%  depth median %.1f min %.1f' % (t0, t0 + 15, 100 * np.isfinite(row).mean(),
              np.median(fin) if len(fin) else -1, fin.min() if len(fin) else -1))
