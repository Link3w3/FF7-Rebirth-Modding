"""How close the coat hangs to the legs in a run: for the coat's vertices near a leg (within 12 cm of its surface: the
height map clip_check uses), the gap to the leg's surface (cm, + outside), median and 25th percentile over the
vertex-frames after the first 1.5 s, and the share inside (gap < 0).
    coat_gap.py body.npz rig.json frames.bin [label]"""
import json, re, sys
import numpy as np
exec(open('/work/kawaii_preset/tests/clip_check.py').read().split("maps = {(s, p)")[0])
maps = {(s, p): height_map(s, p) for s in 'LR' for p in ('thigh', 'calf')}
raw = np.fromfile(frames_path, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
gaps = []
for f in range(90, nf, 2):
    q = F[f, :, :4]; t = F[f, :, 4:]
    qb = qmul(q[cb], qinv(refq[cb]))
    vv = qrot(qb, coat_ref[:, None, :] - reft[cb]) + t[cb]
    sk = (vv * cw[..., None]).sum(axis=1)
    g = np.full(len(coat_v), 1e9)
    for (s, p), (bi, length, ax, e1, e2, m) in maps.items():
        local = qrot(qinv(q[bi])[None, :], sk - t[bi])
        tt = local @ ax / length
        radial = local - np.outer(local @ ax, ax)
        r = np.linalg.norm(radial, axis=1)
        ang = np.arctan2(radial @ e2, radial @ e1)
        ok = (tt >= 0.05) & (tt <= 0.95)
        ti = np.clip((tt * m.shape[0]).astype(int), 0, m.shape[0] - 1); ai = ((ang + np.pi) / (2 * np.pi) * m.shape[1]).astype(int) % m.shape[1]
        g = np.where(ok, np.minimum(g, r - m[ti, ai]), g)
    gaps.append(g[g < 12])
G = np.concatenate(gaps)
print('%-24s coat near the legs: gap median %.2f cm, 25%% %.2f, inside %.2f%%' % (sys.argv[4] if len(sys.argv) > 4 else '', np.median(G), np.percentile(G, 25), 100 * (G < 0).mean()))
