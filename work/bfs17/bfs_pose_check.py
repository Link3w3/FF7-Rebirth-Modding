"""Renders of the re-rigged model: its rest pose next to his original, and test poses (head turned and tilted, the
spine bent, arms and legs moved) skinned with the new weights, to check what follows what."""
import sys, numpy as np
sys.path[:0] = ['/work/bfs17', '/work/ccseph/tools']
from bfs_render import render
from rerig import q2m, axis_angle
import matplotlib.pyplot as plt

def pose(m, rots):
    names = [str(n) for n in m['bone_names']]; par = [int(p) for p in m['bone_parents']]
    ix = {n: i for i, n in enumerate(names)}
    Rb = np.array([q2m(q) for q in m['bone_cq']]); Pb = m['bone_ct'].copy()
    R = Rb.copy(); P = Pb.copy()
    kids = [[] for _ in names]
    for i, p in enumerate(par):
        if p >= 0: kids[p].append(i)
    def sub(i):
        out = [i]; k = 0
        while k < len(out):
            out += kids[out[k]]; k += 1
        return out
    for n, (ax, deg) in rots:
        i = ix[n]; M = axis_angle(np.array(ax, float), np.radians(deg)); o = P[i].copy()
        for j in sub(i):
            P[j] = o + M @ (P[j] - o); R[j] = M @ R[j]
    wb, ww = m['wbone'], m['wweight']
    out = np.zeros_like(m['pos'])
    for j in range(wb.shape[1]):
        b = wb[:, j]; w = ww[:, j][:, None]
        Mr = np.einsum('vij,vkj->vik', R[b], Rb[b])
        out += w * (np.einsum('vij,vj->vi', Mr, m['pos'] - Pb[b]) + P[b])
    return out, P, ix

if __name__ == '__main__':
    m = np.load(sys.argv[1]); o = np.load(sys.argv[2]); out = sys.argv[3]
    tri, mat = m['tri'], m['tmat']
    PAL = np.array([[0.9, 0.9, 1.0], [0.4, 0.3, 0.2], [0.2, 0.2, 0.2], [0.95, 0.8, 0.7], [0.8, 0.4, 0.4], [0.55, 0.55, 0.6], [0.35, 0.25, 0.5], [0.7, 0.75, 0.85]])
    cm = PAL[mat]
    nowing = mat != 7
    rots_head = [('C_Head_a', ([0, 0, 1], 40)), ('C_Head_a', ([0, 1, 0], 25))]
    rots_body = [('C_Spine_c', ([0, 1, 0], 25)), ('C_Neck_a', ([1, 0, 0], 15)), ('L_UpperArm_a', ([1, 0, 0], -70)), ('R_Forearm_a', ([0, 0, 1], 70)),
                 ('L_UpperLeg_a', ([0, 1, 0], -45)), ('L_Foreleg_a', ([0, 1, 0], 70)), ('C_Head_a', ([0, 0, 1], -35))]
    ph, Ph, ix = pose(m, rots_head)
    pb, Pb2, _ = pose(m, rots_body)
    fig, axs = plt.subplots(2, 4, figsize=(28, 20))
    render(axs[0, 0], o['pos'], tri[nowing], cm[nowing], 0, 'his original (no wings shown), front')
    render(axs[0, 1], m['pos'], tri[nowing], cm[nowing], 0, 're-rigged rest, front')
    render(axs[0, 2], o['pos'], tri[nowing], cm[nowing], 90, 'his original, side')
    render(axs[0, 3], m['pos'], tri[nowing], cm[nowing], 90, 're-rigged rest, side')
    z = ((-50, 50), (130, 225))
    render(axs[1, 0], ph, tri[nowing], cm[nowing], 0, 'head turned 40 and tilted 25: front', zoom=z)
    render(axs[1, 1], ph, tri[nowing], cm[nowing], 90, 'head turned and tilted: side', zoom=z)
    render(axs[1, 2], pb, tri[nowing], cm[nowing], 0, 'spine bent, neck, arm up, elbow, leg, head turned: front')
    render(axs[1, 3], pb, tri[nowing], cm[nowing], 90, 'same: side')
    plt.tight_layout(); plt.savefig(out, dpi=55)
    print('ok')
