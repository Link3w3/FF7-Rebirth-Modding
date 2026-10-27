"""Frames of an offline run skinned, the chest and the front strands drawn (z-buffer), side and front-side views.
    sim_frame_view.py merged.npz rig.json frames.bin out.png f1,f2,..."""
import json, sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, '/work/bfs17')
from zbuf import view_matrix, raster
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
refq = np.array([b['q'] for b in rig['bones']]); reft = np.array([b['t'] for b in rig['bones']])
raw = np.fromfile(frames, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
pos = m['pos']; wb = m['wbone']; ww = m['wweight']; tri = m['tri']; tm = m['tmat']
slots = [str(s) for s in m['slots']]
hair = np.isin(tm, [slots.index('PC0010_00_Hair'), slots.index('PC0010_00_HairCore')])
body = tm == slots.index('PC0010_17_Body_Inst')
c0 = pos[tri].mean(1)
keep = (hair | body) & (c0[:, 2] > 100) & (c0[:, 2] < 215) & (np.abs(c0[:, 1]) < 45) & (c0[:, 0] > -40)
tri_k = tri[keep]
used = np.unique(tri_k)
remap = -np.ones(len(pos), np.int64); remap[used] = np.arange(len(used))
cols = np.where(hair[keep][:, None], np.array([[1.0, 0.85, 0.2]]), np.array([[0.62, 0.63, 0.68]]))
fig, axes = plt.subplots(2, len(picks), figsize=(7 * len(picks), 14), squeeze=False)
for c, f in enumerate(picks):
    q = F[f, :, :4]; t = F[f, :, 4:]
    P = pos[used]; B = wb[used]; W = ww[used]
    qb = qmul(q[B], qinv(refq[B]))
    sk = ((qrot(qb, P[:, None, :] - reft[B]) + t[B]) * W[..., None]).sum(axis=1)
    ctr = sk[:, :].mean(0)
    for r_, (yaw, pitch) in enumerate([(90, 0), (35, 0)]):
        M = view_matrix(yaw, pitch); cc = np.array([ctr[0], ctr[1], 160.0]) @ M.T
        img = raster(sk, remap[tri_k], cols, M, ((cc[0] - 40, cc[0] + 40), (cc[1] - 55, cc[1] + 50)), W=420)
        axes[r_, c].imshow(img); axes[r_, c].set_title('frame %d, yaw %d' % (f, yaw)); axes[r_, c].axis('off')
plt.tight_layout(); plt.savefig(out, dpi=60)
print('wrote', out)
