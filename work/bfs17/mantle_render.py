"""Side views of offline runs of his KawaiiPhysics, a row per run, a column per frame: his mantles (dark red) against his
body (grey), the floor drawn.
    mantle_render.py merged.npz rig.json out.png f1,f2,... label1=frames1.bin label2=frames2.bin ..."""
import json, sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, '/work/bfs17')
from bfs_render import render


def qrot(q, v):
    qv = q[..., :3]; t = 2.0 * np.cross(qv, v)
    return v + q[..., 3:4] * t + np.cross(qv, t)


def qinv(q):
    return np.concatenate([-q[..., :3], q[..., 3:4]], axis=-1)


def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0); bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz], axis=-1)


m = np.load(sys.argv[1]); rig = json.load(open(sys.argv[2])); out = sys.argv[3]
picks = [int(x) for x in sys.argv[4].split(',')]
runs = [a.split('=', 1) for a in sys.argv[5:]]
refq = np.array([b['q'] for b in rig['bones']]); reft = np.array([b['t'] for b in rig['bones']])
pos = m['pos']; wb = m['wbone']; ww = m['wweight']; tri = m['tri']; tm = m['tmat']
slots = [str(s) for s in m['slots']]
pal = []
for s in slots:
    pal.append([0.55, 0.12, 0.12] if 'Mantle' in s else [0.95, 0.85, 0.35] if 'Hair' in s else [0.75, 0.8, 0.95] if 'Blade' in s else [0.6, 0.6, 0.64])
cols = np.array(pal)[tm]
fig, axs = plt.subplots(len(runs), len(picks), figsize=(6.5 * len(picks), 4.2 * len(runs)), squeeze=False)
for r_, (label, frames) in enumerate(runs):
    raw = np.fromfile(frames, dtype=np.float32)
    nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
    F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
    for c, f in enumerate(picks):
        q = F[f, :, :4]; t = F[f, :, 4:]
        sk = np.zeros_like(pos)
        for j in range(wb.shape[1]):
            b = wb[:, j]; w = ww[:, j][:, None]
            if not w.any():
                continue
            qb = qmul(q[b], qinv(refq[b]))
            sk += w * (qrot(qb, pos - reft[b]) + t[b])
        ax = axs[r_, c]
        render(ax, sk, tri, cols, 90, '%s, %.1f s' % (label, f / 60.0), zoom=((-330, 90), (-5, 250)))
        ax.plot([-330, 90], [0, 0], color='k', lw=0.8)
plt.tight_layout(); plt.savefig(out, dpi=55); print('wrote', out)
