"""Frames of an offline run (anim_run's .bin) skinned and drawn: what the physics does to his mantles, tail and wings."""
import json, sys
import numpy as np
sys.path[:0] = ['/work/bfs17']
from bfs_render import render
import matplotlib.pyplot as plt

def qrot(q, v):
    qv = q[..., :3]; t = 2.0 * np.cross(qv, v)
    return v + q[..., 3:4] * t + np.cross(qv, t)
def qinv(q):
    return np.concatenate([-q[..., :3], q[..., 3:4]], axis=-1)
def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0); bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz], axis=-1)

m = np.load(sys.argv[1]); rig = json.load(open(sys.argv[2])); frames = sys.argv[3]; out = sys.argv[4]
picks = [int(x) for x in sys.argv[5].split(',')]
views = [float(x) for x in (sys.argv[6] if len(sys.argv) > 6 else '90,180').split(',')]
refq = np.array([b['q'] for b in rig['bones']]); reft = np.array([b['t'] for b in rig['bones']])
raw = np.fromfile(frames, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
pos = m['pos']; wb = m['wbone']; ww = m['wweight']; tri = m['tri']; mat = m['tmat']
PAL = np.array([[0.9, 0.9, 1.0], [0.4, 0.3, 0.2], [0.2, 0.2, 0.2], [0.95, 0.75, 0.6], [0.8, 0.4, 0.4], [0.55, 0.55, 0.6], [0.35, 0.25, 0.5], [0.7, 0.75, 0.85]])
fig, axs = plt.subplots(len(views), len(picks), figsize=(8 * len(picks), 8 * len(views)), squeeze=False)
for c, f in enumerate(picks):
    q = F[f, :, :4]; t = F[f, :, 4:]
    sk = np.zeros_like(pos)
    for j in range(wb.shape[1]):
        b = wb[:, j]; w = ww[:, j][:, None]
        qb = qmul(q[b], qinv(refq[b]))
        sk += w * (qrot(qb, pos - reft[b]) + t[b])
    for r_, yaw in enumerate(views):
        render(axs[r_, c], sk, tri, PAL[mat], yaw, '%s frame %d, view %d' % (frames.split('/')[-1], f, yaw))
plt.tight_layout(); plt.savefig(out, dpi=45); print('ok')
