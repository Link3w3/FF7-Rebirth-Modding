"""The front strands against his chest armour's front surface: a height field of the armour toward +X (forward) in the
chest bone's space (C_Spine_d: the most forward armour point in each 1 cm cell of side and height), the strand vertices
skinned per frame and put in the same space; inside = more than 0.5 cm behind the surface (deeper than at rest)."""
import json, re, sys
from collections import defaultdict
import numpy as np
def qrot(q, v):
    qv = q[..., :3]; t = 2.0 * np.cross(qv, v)
    return v + q[..., 3:4] * t + np.cross(qv, t)
def qinv(q):
    return np.concatenate([-q[..., :3], q[..., 3:4]], axis=-1)
def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0); bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz], axis=-1)
m = np.load(sys.argv[1]); rig = json.load(open(sys.argv[2])); frames = sys.argv[3:]
names = [b['name'] for b in rig['bones']]; index = {n: i for i, n in enumerate(names)}
refq = np.array([b['q'] for b in rig['bones']]); reft = np.array([b['t'] for b in rig['bones']])
pos, wb, ww, tri, tm = m['pos'], m['wbone'], m['wweight'], m['tri'], m['tmat']
slots = [str(s) for s in m['slots']]
bn = list(m['bone_names'])
dom = np.array(bn)[wb[np.arange(len(wb)), ww.argmax(1)]]
body_v = np.unique(tri[tm == slots.index('PC0010_17_Body_Inst')])
torso = body_v[np.isin(dom[body_v], ['C_Spine_b', 'C_Spine_c', 'C_Spine_d', 'C_Neck_a', 'NeckSub', 'Spine1W', 'Abs1', 'Abs2', 'Abs3', 'Abs4', 'Abs5'])]
CH = index['C_Spine_d']
def to_chest(P, q, t):
    return qrot(qinv(q[CH])[None, :], P - t[CH])
A = to_chest(pos[torso], refq, reft)       # (chest space: which axis is forward? find it from the component +X)
fwd_local = qrot(qinv(refq[CH]), np.array([1.0, 0, 0]))
ax = int(np.argmax(np.abs(fwd_local))); sgn = np.sign(fwd_local[ax])
others = [k for k in range(3) if k != ax]
cell = 1.0
key = lambda P: (np.floor(P[:, others[0]] / cell).astype(int), np.floor(P[:, others[1]] / cell).astype(int))
surf = defaultdict(lambda: -1e9)
for a_, b_, x in zip(*key(A), sgn * A[:, ax]):
    if x > surf[(a_, b_)]:
        surf[(a_, b_)] = x
hair = re.compile(r'^(C_HairA|C_HairB|[LR]_HairA)_[a-z]_Phy$')
fv = np.array([v for v in range(len(pos)) if sum(ww[v, k] for k in range(8) if ww[v, k] > 0 and hair.match(bn[wb[v, k]])) > 0.5])
B = wb[fv]; W = ww[fv]
def depth(P_chest):
    a_, b_ = key(P_chest)
    s = np.array([surf.get((i, j), -1e9) for i, j in zip(a_, b_)])
    return s - sgn * P_chest[:, ax]          # > 0: behind the armour's front surface
d0 = depth(to_chest(pos[fv], refq, reft))
print('front strand verts %d; at rest behind the surface by > 0.5 cm: %.1f%%' % (len(fv), 100 * (d0 > 0.5).mean()))
for fr in frames:
    raw = np.fromfile(fr, dtype=np.float32)
    nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
    F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
    deeper = []
    for f in range(int(nf / 7 * 1.5), nf, 3):
        q = F[f, :, :4]; t = F[f, :, 4:]
        qb = qmul(q[B], qinv(refq[B]))
        sk = ((qrot(qb, pos[fv][:, None, :] - reft[B]) + t[B]) * W[..., None]).sum(axis=1)
        dd = depth(to_chest(sk, q, t))
        deeper.append(np.where(dd > 0.5, dd - np.maximum(d0, 0), 0))
    D = np.concatenate(deeper)
    print('  %s: deeper than rest by > 0.5 cm %.2f%% of vertex-frames, by > 2 cm %.2f%%, max %.1f cm' % (fr.split('/')[-1], 100 * (D > 0.5).mean(), 100 * (D > 2).mean(), D.max()))
