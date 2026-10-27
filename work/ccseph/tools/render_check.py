"""Rest-pose and test-pose renders of the re-rigged mesh: point views from the front and side, its joints, and Rebirth
Sephiroth's mesh behind it for scale."""
import sys, json
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, '/work/ccseph/tools')
from rerig import q2m

def skin(m, Rcs, Pcs):
    """pose: component-space rotations/positions per new bone"""
    names = list(m['bone_names']); n = len(names)
    R0 = np.array([q2m(q) for q in m['bone_cq']]); P0 = m['bone_ct']
    out = np.zeros_like(m['pos'])
    for j in range(8):
        b = m['wbone'][:, j]; w = m['wweight'][:, j][:, None]
        Mr = np.einsum('vij,vkj->vik', Rcs[b], R0[b])
        out += w * (np.einsum('vij,vj->vi', Mr, m['pos'] - P0[b]) + Pcs[b])
    return out

def fk(m, local_rot):
    """local_rot: {bone: 3x3 local rotation replacing the reference one}; translations from the model (its proportions)"""
    names = list(m['bone_names']); par = list(m['bone_parents'])
    Rl = [q2m(q) for q in m['bone_lq']]; tl = [np.array(t) for t in m['bone_lt']]
    R = [None] * len(names); P = [None] * len(names)
    for i, nm in enumerate(names):
        L = local_rot.get(nm, Rl[i])
        if par[i] < 0: R[i] = L; P[i] = tl[i]
        else: R[i] = R[par[i]] @ L; P[i] = P[par[i]] + R[par[i]] @ tl[i]
    return np.array(R), np.array(P)

def draw(ax, pts, mat, view, title, joints=None, bg=None):
    a, b = (1, 2) if view == 'front' else (0, 2)
    if bg is not None:
        ax.scatter(bg[::7, a], bg[::7, 2], s=0.2, c='#bbbbbb')
    cols = plt.cm.tab10(mat % 10)
    ax.scatter(pts[::3, a], pts[::3, 2], s=0.25, c=cols[::3])
    if joints is not None:
        ax.scatter(joints[:, a], joints[:, 2], s=4, c='red')
    ax.set_aspect('equal'); ax.set_title(title, fontsize=8); ax.axis('off')

if __name__ == '__main__':
    m = np.load(sys.argv[1]); out = sys.argv[2]
    vm = np.zeros(len(m['pos']), dtype=int)
    for t, k in zip(m['tri'], m['tmat']): vm[t] = k
    bg = np.load('/work/kawaii_preset/meshes/PC0010_00.npz')['pos'] if len(sys.argv) < 4 else None
    fig, axs = plt.subplots(1, 4, figsize=(16, 9))
    draw(axs[0], m['pos'], vm, 'front', 'rest (front) + Rebirth Sephiroth', m['bone_ct'], bg)
    draw(axs[1], m['pos'], vm, 'side', 'rest (side) + Rebirth Sephiroth', m['bone_ct'], bg)
    # a test pose in Rebirth's bone frames: arm raised, elbow bent, knee bent, spine twist
    from rerig import axis_angle
    names = list(m['bone_names'])
    Rl = {n: q2m(q) for n, q in zip(names, m['bone_lq'])}
    lr = {}
    lr['L_UpperArm_a'] = Rl['L_UpperArm_a'] @ axis_angle([0, 0, 1], np.radians(-50))
    lr['L_Forearm_a'] = Rl['L_Forearm_a'] @ axis_angle([0, 0, 1], np.radians(-70))
    lr['R_Foreleg_a'] = Rl['R_Foreleg_a'] @ axis_angle([0, 0, 1], np.radians(70))
    lr['C_Spine_b'] = Rl['C_Spine_b'] @ axis_angle([1, 0, 0], np.radians(20))
    lr['C_Head_a'] = Rl['C_Head_a'] @ axis_angle([1, 0, 0], np.radians(25))
    R, P = fk(m, lr)
    pp = skin(m, R, P)
    draw(axs[2], pp, vm, 'front', 'test pose (front)', P)
    draw(axs[3], pp, vm, 'side', 'test pose (side)', P)
    plt.tight_layout(); plt.savefig(out, dpi=110)
    print('saved', out)
