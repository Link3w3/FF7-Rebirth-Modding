"""(3.17.0) Pictures of a kick run's frames: the coat's vertices (skinned) and the body's leg vertices, from the side
(X forward, Z up) and from the front (Y, Z), for frames given.
    python3 kick_view.py body.npz rig.json frames.bin out.png frame [frame ...]"""
import json, sys
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

body_path, rig_path, frames_path, out_path = sys.argv[1:5]
frames = [int(x) for x in sys.argv[5:]]
d = np.load(body_path, allow_pickle=True)
pos = d['pos']; wb = d['w_bone']; wv = d['w_vert']; ww = d['w_weight']; bnames = list(d['bones']); vmat = d['vmat']; mats = list(d['mats'])
rig = json.load(open(rig_path))
names = [b['name'] for b in rig['bones']]
index = {n: i for i, n in enumerate(names)}
refq = np.array([b['q'] for b in rig['bones']], dtype=np.float64)
reft = np.array([b['t'] for b in rig['bones']], dtype=np.float64)
def qrot(q, v):
    qv = q[..., :3]; t = 2.0 * np.cross(qv, v); return v + q[..., 3:4] * t + np.cross(qv, t)
def qinv(q): return np.concatenate([-q[..., :3], q[..., 3:4]], axis=-1)
def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0); bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz], axis=-1)
nv = len(pos)
vw = defaultdict(dict)
for b, v, w in zip(wb, wv, ww):
    vw[int(v)][str(bnames[b])] = float(w)
import re
YS = any(str(m).startswith('body_geo') for m in mats)
isbody = np.array([mats[m].startswith('body_geo') if m >= 0 else False for m in vmat]) if YS else np.ones(nv, dtype=bool)
COAT = re.compile(r'(Coat|Skirt|Mantle|Cape)[A-Z]*_[a-z]_Phy$')
def skin_set(vs):
    K = 6
    cb = np.zeros((len(vs), K), dtype=np.int64); cw = np.zeros((len(vs), K))
    for i, v in enumerate(vs):
        items = sorted(vw[v].items(), key=lambda x: -x[1])[:K]
        s = sum(w for _, w in items)
        for k, (n, w) in enumerate(items):
            cb[i, k] = index[n]; cw[i, k] = w / s
    return cb, cw, pos[vs]
coat_v = np.array([v for v in range(nv) if isbody[v] and (any('Coat' in n for n in vw[v]) if YS else sum(w for n, w in vw[v].items() if COAT.search(n)) > 0.5)])
legs = [v for v in range(nv) if isbody[v] and not any(('Coat' in n or 'Belt' in n) for n in vw[v]) and
        sum(w for n, w in vw[v].items() if ('Leg' in n or 'Foreleg' in n or 'Foot' in n or 'Toe' in n or 'Knee' in n or 'Femoris' in n)) > 0.5]
legs = np.array(legs)
C = skin_set(coat_v); L = skin_set(legs)
raw = np.fromfile(frames_path, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
def skin(S, f):
    cb, cw, ref = S
    q = F[f, :, :4]; t = F[f, :, 4:]
    qb = qmul(q[cb], qinv(refq[cb]))
    vv = qrot(qb, ref[:, None, :] - reft[cb]) + t[cb]
    return (vv * cw[..., None]).sum(axis=1)
fig, axes = plt.subplots(2, len(frames), figsize=(3.2 * len(frames), 7.5))
if len(frames) == 1: axes = axes.reshape(2, 1)
for j, f in enumerate(frames):
    c = skin(C, f); l = skin(L, f)
    for row, (a, b, nm) in enumerate([(0, 2, 'side X-Z'), (1, 2, 'front Y-Z')]):
        ax = axes[row, j]
        ax.scatter(l[:, a], l[:, b], s=0.3, c='0.6')
        ax.scatter(c[:, a], c[:, b], s=0.6, c='crimson')
        ax.set_aspect('equal'); ax.set_xlim(-70, 100 if a == 0 else 70); ax.set_ylim(-5, 190)
        ax.set_title('frame %d %s' % (f, nm), fontsize=8)
plt.tight_layout(); plt.savefig(out_path, dpi=80)
print('wrote', out_path)
