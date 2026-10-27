"""(3.17.0) A closer look at a kick run's frame: the coat's vertices of the chains given (by bone-name part), their bones
(dots) and the leg capsules of the entry (outlines, from the frame's leg bones), from the front (Y-Z) and side (X-Z),
around the left leg.
    python3 kick_view2.py body.npz rig.json entry.json frames.bin out.png part frame [frame ...]"""
import json, sys, re
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, '/work/cacs3151/tools')
from kawaii_feet_sync import qrot as qrot1, qmul as qmul1, from_rotator
body_path, rig_path, entry_path, frames_path, out_path, part = sys.argv[1:7]
frames = [int(x) for x in sys.argv[7:]]
d = np.load(body_path, allow_pickle=True)
pos = d['pos']; wb = d['w_bone']; wv = d['w_vert']; ww = d['w_weight']; bnames = [str(b) for b in d['bones']]
rig = json.load(open(rig_path)); names = [b['name'] for b in rig['bones']]; index = {n: i for i, n in enumerate(names)}
refq = np.array([b['q'] for b in rig['bones']]); reft = np.array([b['t'] for b in rig['bones']])
def qrot(q, v):
    qv = q[..., :3]; t = 2.0 * np.cross(qv, v); return v + q[..., 3:4] * t + np.cross(qv, t)
def qinv(q): return np.concatenate([-q[..., :3], q[..., 3:4]], axis=-1)
def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0); bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz], axis=-1)
vw = defaultdict(dict)
for b, v, w in zip(wb, wv, ww): vw[int(v)][bnames[b]] = vw[int(v)].get(bnames[b], 0) + float(w)
rx = re.compile(part)
cv = np.array([v for v in range(len(pos)) if sum(w for n, w in vw[v].items() if rx.search(n)) > 0.5])
lv = np.array([v for v in range(len(pos)) if sum(w for n, w in vw[v].items() if re.search(r'^L_(UpperLeg|Foreleg|Foot|Toe|Femoris|Knee|Calf)', n)) > 0.5])
def sset(vs):
    K = 6; cb = np.zeros((len(vs), K), dtype=np.int64); cw = np.zeros((len(vs), K))
    for i, v in enumerate(vs):
        items = sorted(vw[v].items(), key=lambda x: -x[1])[:K]; s = sum(w for _, w in items)
        for k, (n, w) in enumerate(items): cb[i, k] = index[n]; cw[i, k] = w / s
    return cb, cw, pos[vs]
C = sset(cv); L = sset(lv)
raw = np.fromfile(frames_path, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
def skin(S, f):
    cb, cw, ref = S; q = F[f, :, :4]; t = F[f, :, 4:]
    qb = qmul(q[cb], qinv(refq[cb])); vv = qrot(qb, ref[:, None, :] - reft[cb]) + t[cb]
    return (vv * cw[..., None]).sum(axis=1)
entry = json.load(open(entry_path))['kawaii'][0]
shapes = []
for n in entry['nodes']:
    for s in n.get('tapered_capsules', []):
        if s['bone'].startswith('L_') and s not in shapes: shapes.append(s)
cbones = [n for n in names if rx.search(n)]
fig, axes = plt.subplots(2, len(frames), figsize=(3.6 * len(frames), 8))
if len(frames) == 1: axes = axes.reshape(2, 1)
for j, f in enumerate(frames):
    c = skin(C, f); l = skin(L, f)
    bp = np.array([F[f, index[b], 4:] for b in cbones])
    for row, (a, b) in enumerate([(1, 2), (0, 2)]):
        ax = axes[row, j]
        ax.scatter(l[:, a], l[:, b], s=0.3, c='0.65')
        ax.scatter(c[:, a], c[:, b], s=0.8, c='crimson')
        ax.scatter(bp[:, a], bp[:, b], s=10, c='navy')
        for s in shapes:
            q = list(F[f, index[s['bone']], :4]); t = F[f, index[s['bone']], 4:]
            off = qrot1(q, s['offset']); cc = np.array([t[i] + off[i] for i in range(3)])
            axz = np.array(qrot1(qmul1(q, from_rotator(*s['rotation'])), [0, 0, 1]))
            p0 = cc + axz * s['length'] / 2; p1 = cc - axz * s['length'] / 2
            ax.plot([p0[a], p1[a]], [p0[b], p1[b]], 'g-', lw=1)
            for pp, rr in ((p0, s['radius0']), (p1, s['radius1'])):
                ax.add_patch(plt.Circle((pp[a], pp[b]), rr, fill=False, ec='g', lw=0.6))
        ax.set_aspect('equal'); ax.set_xlim((-45, 45) if a == 1 else (-50, 90)); ax.set_ylim(-5, 135)
        ax.set_title('f%d %s' % (f, 'front' if a == 1 else 'side'), fontsize=8)
plt.tight_layout(); plt.savefig(out_path, dpi=80); print('wrote', out_path)
