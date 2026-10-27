"""The re-rigged model in Rebirth Sephiroth's animations (samples of his battle idle, combo and run): each Rebirth bone
turned as the animation turns it (its local rotation), his own bone lengths kept (Keep Proportions), the hips moved
as the animation moves them scaled to his hip height; his own bones (mantles, wings, tail) carried along stiffly."""
import sys, json, numpy as np
sys.path[:0] = ['/work/bfs17', '/work/ccseph/tools']
from bfs_render import render
from rerig import q2m
import matplotlib.pyplot as plt

def anim_pose(m, RB, bones):
    names = [str(n) for n in m['bone_names']]; par = list(m['bone_parents'])
    Rl = [q2m(q) for q in m['bone_lq']]; tl = [np.array(t) for t in m['bone_lt']]
    hip_ratio = tl[names.index('C_Hip_a')][2] / RB['C_Hip_a']['local_t'][2]
    R = [None] * len(names); P = [None] * len(names)
    for i, n in enumerate(names):
        L = Rl[i]; t = tl[i]
        b = bones.get(n) if n != 'Trans' else None
        if b is not None:
            L = q2m(b[:4])
            if n == 'C_Hip_a':
                t = np.array(b[4:7]) * hip_ratio
        if par[i] < 0: R[i] = L; P[i] = t
        else: R[i] = R[par[i]] @ L; P[i] = P[par[i]] + R[par[i]] @ t
    return np.array(R), np.array(P)

def skin(m, R, P):
    Rb = np.array([q2m(q) for q in m['bone_cq']]); Pb = m['bone_ct']
    out = np.zeros_like(m['pos'])
    for j in range(m['wbone'].shape[1]):
        b = m['wbone'][:, j]; w = m['wweight'][:, j][:, None]
        Mr = np.einsum('vij,vkj->vik', R[b], Rb[b])
        out += w * (np.einsum('vij,vj->vi', Mr, m['pos'] - Pb[b]) + P[b])
    return out

if __name__ == '__main__':
    m = np.load(sys.argv[1]); S = json.load(open(sys.argv[2])); out = sys.argv[3]
    RB = {b['name']: b for b in json.load(open('/work/kawaii_preset/rigs/PC0010_00.json'))['bones']}
    PAL = np.array([[0.9, 0.9, 1.0], [0.4, 0.3, 0.2], [0.2, 0.2, 0.2], [0.95, 0.75, 0.6], [0.8, 0.4, 0.4], [0.55, 0.55, 0.6], [0.35, 0.25, 0.5], [0.7, 0.75, 0.85]])
    tri, mat = m['tri'], m['tmat']
    sel = ~np.isin(mat, [6, 7])     # without the mantles and wings (no physics here)
    cm = PAL[mat]
    picks = [('B_Idle01_1', 0), ('B_NAttack01_0', 2), ('B_NAttack01_0', 4), ('B_NAttack03_0', 2), ('N_Run01_1', 1), ('N_Run01_1', 3)]
    fig, axs = plt.subplots(2, 3, figsize=(24, 18))
    for ax, (a, k) in zip(axs.ravel(), picks):
        key = [x for x in S if x.endswith(a)][0]
        fr = S[key]['frames'][min(k, len(S[key]['frames']) - 1)]
        R, P = anim_pose(m, RB, fr['bones'])
        pp = skin(m, R, P)
        render(ax, pp, tri[sel], cm[sel], 30, '%s t=%.2f (mantles, wings hidden)' % (a, fr['time']))
    plt.tight_layout(); plt.savefig(out, dpi=55); print('saved')
