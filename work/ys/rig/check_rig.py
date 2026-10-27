"""Pose the new skeleton with one of Sephiroth's clips (his local rotations by name; lengths from the new skeleton, the
hips' travel scaled) and compare every body bone's direction (to its aim child) with Sephiroth's own in the same pose."""
import json, sys
sys.path[:0] = ['/work/acl', '/work/ch049anim', '/work/ys']
import numpy as np
import retarget_from_seph as RS
import pose
SE, CV = RS.SE, RS.CV
qmul, qinv, qrot, qnorm = CV.qmul, CV.qinv, CV.qrot, CV.qnorm
rig = json.load(open(sys.argv[1]))
key = sys.argv[2] if len(sys.argv) > 2 else 'B_NAttack01_0'
B = rig['bones']
names = [b['name'] for b in B]
ix = {n: i for i, n in enumerate(names)}
par = [ix[b['parent']] if b['parent'] else -1 for b in B]
Q = np.array([b['q'] for b in B]); T = np.array([b['t'] for b in B])
lq = np.zeros_like(Q); lt = np.zeros_like(T)
for i in range(len(B)):
    p = par[i]
    if p < 0:
        lq[i], lt[i] = Q[i], T[i]
    else:
        lq[i] = qmul(qinv(Q[p]), Q[i]); lt[i] = qrot(qinv(Q[p]), T[i] - T[p])
c, bones, LQs, LTs = pose.load(open(RS.PKG % key, 'rb').read())
nf = LQs.shape[0]
tr = SE.index['Trans']
LQs = LQs.copy(); LTs = LTs.copy()
LQs[:, tr] = SE.q[tr]; LTs[:, tr] = SE.t[tr]
GQs, GTs, _ = CV.fk(LQs, LTs, np.ones(LTs.shape), SE.parents)
# the new skeleton under the clip
LQn = np.repeat(lq[None], nf, 0); LTn = np.repeat(lt[None], nf, 0)
for i, n in enumerate(names):
    if n in SE.index and n != 'Trans':
        LQn[:, i] = LQs[:, SE.index[n]]
h = ix['C_Hip_a']
LTn[:, h] = lt[h] + (LTs[:, SE.index['C_Hip_a']] - SE.t[SE.index['C_Hip_a']]) * rig['scale']
GQn, GTn, _ = CV.fk(LQn, LTn, np.ones(LTn.shape), par)
worst = []
for s, (s_child, c_child) in CV.AIM.items():
    i, j = ix[s], ix[s_child]
    a = GTn[:, j] - GTn[:, i]; b = GTs[:, SE.index[s_child]] - GTs[:, SE.index[s]]
    a /= np.linalg.norm(a, axis=-1, keepdims=True); b /= np.linalg.norm(b, axis=-1, keepdims=True)
    ang = np.degrees(np.arccos(np.clip((a * b).sum(-1), -1, 1))).max()
    worst.append((round(float(ang), 3), s))
worst.sort(reverse=True)
print(key, nf, 'frames; largest direction difference from Sephiroth over the clip (deg):', worst[:6])
# the coat: tail directions in Sephiroth's clip vs the new skeleton (where both have the segment)
cw = []
for n in names:
    if 'Coat' in n and n.endswith('_a_Phy'):
        stem = n[:-6]
        i, j = ix[n], ix.get(stem + '_b_Phy')
        if j is None: continue
        a = GTn[:, j] - GTn[:, i]; b = GTs[:, SE.index[stem + '_b_Phy']] - GTs[:, SE.index[n]]
        a /= np.linalg.norm(a, axis=-1, keepdims=True); b /= np.linalg.norm(b, axis=-1, keepdims=True)
        cw.append((round(float(np.degrees(np.arccos(np.clip((a * b).sum(-1), -1, 1))).max()), 2), stem))
print('coat tails (first segment), largest difference (deg):', sorted(cw, reverse=True)[:5])
