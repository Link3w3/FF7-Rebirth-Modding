"""Views of offline runs (anim_run frames) of Bahamut Fused Sephiroth: a row per run, a column per view (yaw).
    render_poses.py out.png frame yaw1,yaw2,... label=frames.bin ..."""
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

m = np.load('/work/bfs17/hair/rerig_hair6_uv1.npz'); rig = json.load(open('/work/bfs17/tune/a3/rig.json'))
out, frame = sys.argv[1], int(sys.argv[2]); yaws = [float(x) for x in sys.argv[3].split(',')]
runs = [a.split('=', 1) for a in sys.argv[4:]]
refq = np.array([b['q'] for b in rig['bones']]); reft = np.array([b['t'] for b in rig['bones']])
pos = m['pos']; wb = m['wbone']; ww = m['wweight']; tri = m['tri']; tm = m['tmat']
slots = [str(s) for s in m['slots']]
pal = [[0.55, 0.12, 0.12] if 'Mantle' in s else [0.95, 0.85, 0.35] if 'Hair' in s else [0.75, 0.8, 0.95] if 'Blade' in s else [0.6, 0.6, 0.64] for s in slots]
cols = np.array(pal)[tm]
fig, axs = plt.subplots(len(runs), len(yaws), figsize=(5.0 * len(yaws), 5.5 * len(runs)), squeeze=False)
for r_, (label, frames) in enumerate(runs):
    raw = np.fromfile(frames, dtype=np.float32)
    nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
    F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
    q = F[frame, :, :4]; t = F[frame, :, 4:]
    sk = np.zeros_like(pos)
    for j in range(wb.shape[1]):
        b = wb[:, j]; w = ww[:, j][:, None]
        if not w.any():
            continue
        qb = qmul(q[b], qinv(refq[b]))
        sk += w * (qrot(qb, pos - reft[b]) + t[b])
    for c, yaw in enumerate(yaws):
        render(axs[r_, c], sk, tri, cols, yaw, '%s, yaw %d, %.1f s' % (label, yaw, frame / 60.0))
plt.tight_layout(); plt.savefig(out, dpi=50); print('wrote', out)
