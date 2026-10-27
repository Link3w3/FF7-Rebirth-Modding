import json, sys, re
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
slots = [str(s) for s in m['slots']]; bn = [str(b) for b in m['bone_names']]
dom = np.array(bn)[wb[np.arange(len(wb)), ww.argmax(1)]]
hair = np.isin(tm, [slots.index('PC0010_00_Hair'), slots.index('PC0010_00_HairCore')])
body = tm == slots.index('PC0010_17_Body_Inst')
face = np.array([s.startswith('PC0010_00') and 'Hair' not in s for s in slots])[tm] | (tm == slots.index('Common_Mouth'))
c0 = pos[tri].mean(1)
keep = (hair | body | face) & (c0[:, 2] > 120) & (c0[:, 2] < 205) & (np.abs(c0[:, 1]) < 30) & (c0[:, 0] > -12)
tri_k = tri[keep]
used = np.unique(tri_k); remap = -np.ones(len(pos), np.int64); remap[used] = np.arange(len(used))
td = dom[tri_k[:, 0]]
cols = np.tile([0.62, 0.63, 0.68], (len(tri_k), 1))
cols[face[keep]] = [0.95, 0.7, 0.6]
for rx, c in ((r'^C_Hair[AB]_', [0.9, 0.2, 0.2]), (r'^[LR]_HairA_', [0.2, 0.4, 0.95]), (r'Hair', None)):
    sel = np.array([bool(re.match(rx, d)) if c is not None else False for d in td]) & hair[keep]
    if c is not None:
        cols[sel] = c
oth = hair[keep] & (cols[:, 0] == 0.62)
cols[oth] = [1.0, 0.85, 0.2]
fig, axes = plt.subplots(2, len(picks), figsize=(7 * len(picks), 14), squeeze=False)
for c_, f in enumerate(picks):
    if f < 0:
        q, t = refq, reft
    else:
        q = F[f, :, :4]; t = F[f, :, 4:]
    P = pos[used]; B = wb[used]; W = ww[used]
    qb = qmul(q[B], qinv(refq[B]))
    sk = ((qrot(qb, P[:, None, :] - reft[B]) + t[B]) * W[..., None]).sum(axis=1)
    head = t[bn.index('C_Head_a')] if f >= 0 else reft[bn.index('C_Head_a')]
    for r_, (yaw, pitch) in enumerate([(0, 0), (70, 0)]):
        M = view_matrix(yaw, pitch); cc = np.array([head[0], head[1], head[2] - 20]) @ M.T
        img = raster(sk, remap[tri_k], cols, M, ((cc[0] - 28, cc[0] + 28), (cc[1] - 35, cc[1] + 30)), W=420)
        axes[r_, c_].imshow(img); axes[r_, c_].set_title('%s, yaw %d' % ('rest' if f < 0 else 'frame %d' % f, yaw)); axes[r_, c_].axis('off')
plt.tight_layout(); plt.savefig(out, dpi=60)
print('wrote', out)
