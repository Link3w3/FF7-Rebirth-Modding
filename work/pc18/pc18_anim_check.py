"""The re-rigged PC0010_18 in Rebirth Sephiroth's motions (decoded from the game's packages): each bone with Rebirth's
name turned as the motion turns Sephiroth's (its local rotation), his own bone lengths kept (Keep Proportions), the hips
moved as the motion moves them scaled to his hip height, the root (Trans) at rest (the game locks it: root motion); his
own bones (wings, tail, horns) carried along stiffly.
    pc18_anim_check.py <rerig.npz> <out.png> motion:frame ..."""
import sys, json, glob, os
import numpy as np
sys.path[:0] = ['/work/pc18', '/work/ccseph/tools']
import anim_zen as A
import pc18_render as PR
from rerig import q2m
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

SEPH = '/work/pc18/seph/'
SK = A.Skeleton(open(SEPH + 'Character__Player__PC0010_00_Sephiroth_Standard__Model__PC0010_00_Skeleton.uasset', 'rb').read())

def motion(name):
    f = glob.glob(SEPH + 'Motion__*__' + name + '.uasset')[0]
    return A.decode(open(f, 'rb').read(), SK)

def pose(m, LQ, LT, frame):
    names = [str(n) for n in m['bone_names']]; par = [int(p) for p in m['bone_parents']]
    Rl = [q2m(q) for q in m['bone_lq']]; tl = [np.array(t) for t in m['bone_lt']]
    hip_ratio = tl[names.index('C_Hip_a')][2] / SK.ref_t[SK.index['C_Hip_a']][2]
    R = [None] * len(names); P = [None] * len(names)
    for i, n in enumerate(names):
        L = Rl[i]; t = tl[i]
        k = SK.index.get(n)
        if k is not None and n != 'Trans':
            L = q2m(LQ[frame, k])
            if n == 'C_Hip_a':
                t = LT[frame, k] * hip_ratio
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
    m = np.load(sys.argv[1]); out = sys.argv[2]
    picks = [(a.split(':')[0], int(a.split(':')[1])) for a in sys.argv[3:]]
    pos, tri, tmat, mats, names, joints = PR.load(sys.argv[1])
    cm = PR.colours(mats)
    # the big wings (WingD: the blades, WingB: the back spikes) hidden: they hide the body
    hide = [i for i, n in enumerate(mats) if n in ('SU2050_02_WingDFlow', 'SU2050_02_WingBFlow')]
    sel = ~np.isin(tmat, hide)
    n = len(picks)
    fig, axs = plt.subplots(2, n, figsize=(7 * n, 20))
    for c, (name, fr) in enumerate(picks):
        LQ, LT, fps, _ = motion(name)
        fr = min(fr, len(LQ) - 1)
        R, P = pose(m, LQ, LT, fr)
        pp = skin(m, R, P)
        for r, yaw in enumerate((0, 90)):
            PR.draw(axs[r, c], pp, tri[sel], tmat[sel], cm, yaw, None, None, None, '%s f%d (%s)' % (name, fr, 'front' if yaw == 0 else 'side'))
    plt.tight_layout(); plt.savefig(out, dpi=50); print('saved', out)
