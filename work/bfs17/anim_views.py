"""His tail from above (its bones, several frames of a run) and his blade wings from behind at two frames: the pose
animation at a glance.
    anim_views.py merged.npz rig.json frames.bin out.png f_tail0,f_tail1,... f_wing_a,f_wing_b"""
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
m = np.load(sys.argv[1]); rig = json.load(open(sys.argv[2])); frames = sys.argv[3]; out = sys.argv[4]
tail_frames = [int(x) for x in sys.argv[5].split(',')]; wing_frames = [int(x) for x in sys.argv[6].split(',')]
names = [b['name'] for b in rig['bones']]; ix = {n: i for i, n in enumerate(names)}
refq = np.array([b['q'] for b in rig['bones']]); reft = np.array([b['t'] for b in rig['bones']])
raw = np.fromfile(frames, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
fig = plt.figure(figsize=(6.5 * (1 + len(wing_frames)), 6.5))
ax = fig.add_subplot(1, 1 + len(wing_frames), 1)
tail = [ix['Tail%d' % k] for k in range(1, 29)]
cm = plt.cm.viridis(np.linspace(0, 1, len(tail_frames)))
for c, f in zip(cm, tail_frames):
    p = F[f, tail, 4:] - F[f, ix['C_Hip_a'], 4:]
    ax.plot(p[:, 1], p[:, 0], '-o', ms=2, color=c, label='%.1f s' % (f / 60.0))
ax.set_aspect('equal'); ax.set_title('tail from above (his front up)'); ax.legend(fontsize=7); ax.grid(alpha=0.3)
pos = m['pos']; wb = m['wbone']; ww = m['wweight']; tri = m['tri']; tm = m['tmat']
slots = [str(s) for s in m['slots']]
pal = [[0.55, 0.12, 0.12] if 'Mantle' in s else [0.95, 0.85, 0.35] if 'Hair' in s else [0.75, 0.8, 0.95] if 'Blade' in s else [0.6, 0.6, 0.64] for s in slots]
cols = np.array(pal)[tm]
for k, f in enumerate(wing_frames):
    q = F[f, :, :4]; t = F[f, :, 4:]
    sk = np.zeros_like(pos)
    for j in range(wb.shape[1]):
        b = wb[:, j]; w = ww[:, j][:, None]
        if not w.any():
            continue
        sk += w * (qrot(qmul(q[b], qinv(refq[b])), pos - reft[b]) + t[b])
    a2 = fig.add_subplot(1, 1 + len(wing_frames), 2 + k)
    render(a2, sk, tri, cols, 180, 'from behind, %.1f s' % (f / 60.0), zoom=((-260, 260), (60, 330)))
plt.tight_layout(); plt.savefig(out, dpi=55); print('wrote', out)
