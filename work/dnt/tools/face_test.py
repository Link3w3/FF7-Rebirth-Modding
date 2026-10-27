"""Quick face rig test without the game's clips: opens the jaw (C_Dteeth turned 18 deg about the left-right axis at its
joint), closes the upper lids (L/R_Ulid*, L/R_Ulash* moved 0.45 cm down) and smiles (corners L/R_Ucor, L/R_Dcor moved
0.4 cm up and back), skinned from the npz's weights; front and three-quarter renders of the head.
    face_test.py <face npz (check: CH_* slots)> <out png>"""
import sys
import numpy as np
sys.path[:0] = ['/work/ccseph/tools']
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import shade
from face_rig import qmul, qinv, qrot


def axis_q(axis, deg):
    a = np.radians(deg) / 2; axis = np.asarray(axis, float) / np.linalg.norm(axis)
    return np.array([*(axis * np.sin(a)), np.cos(a)])


def qmat(q):
    x, y, z, w = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    return np.stack([np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], -1),
                     np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], -1),
                     np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1)], -2)


def skin(m, gq, gt, verts):
    """linear blend skinning of the given vertices (vectorized): bone matrix = posed * bind^-1"""
    R1, R0 = qmat(gq), qmat(m['bone_cq'])
    Mr = np.einsum('bij,bkj->bik', R1, R0)
    t = gt - np.einsum('bij,bj->bi', Mr, m['bone_ct'])
    P = m['pos'][verts]; out = np.zeros_like(P)
    for k in range(m['wbone'].shape[1]):
        b = m['wbone'][verts, k]; w = m['wweight'][verts, k][:, None]
        out += w * (np.einsum('vij,vj->vi', Mr[b], P) + t[b])
    return out


def main(npz, out_png):
    m = dict(np.load(npz))
    names = [str(n) for n in m['bone_names']]; par = list(m['bone_parents'])
    kids = {}
    for i, p in enumerate(par):
        kids.setdefault(p, []).append(i)

    def sub(i):
        out = [i]; k = 0
        while k < len(out):
            out += kids.get(out[k], []); k += 1
        return out
    poses = []
    gq0, gt0 = m['bone_cq'].copy(), m['bone_ct'].copy()
    poses.append(('rest', gq0, gt0))
    gq, gt = gq0.copy(), gt0.copy()
    j = names.index('C_Dteeth'); q = axis_q([0, 1, 0], 18); o = gt[j].copy()
    for i in sub(j):
        gq[i] = qmul(q, gq[i]); gt[i] = o + qrot(q, gt[i] - o)
    poses.append(('jaw open', gq, gt))
    gq, gt = gq0.copy(), gt0.copy()
    for i, n in enumerate(names):
        if n.startswith(('L_Ulid', 'R_Ulid', 'L_Ulash', 'R_Ulash')):
            gt[i] = gt[i] + np.array([0, 0, -0.45])
    poses.append(('blink', gq, gt))
    gq, gt = gq0.copy(), gt0.copy()
    for i, n in enumerate(names):
        if n.startswith(('L_Ucor', 'R_Ucor', 'L_Dcor', 'R_Dcor')):
            gt[i] = gt[i] + np.array([-0.3, 0, 0.4])
    poses.append(('smile', gq, gt))
    slots = [str(s) for s in m['slots']]
    keep = np.isin(m['tmat'], [slots.index(s) for s in ('CH_head', 'CH_eye', 'CH_mouth', 'CH_eyelash')])
    T, TM = m['tri'][keep], m['tmat'][keep]
    verts = np.unique(T.ravel())
    remap = -np.ones(len(m['pos']), int); remap[verts] = np.arange(len(verts))
    T = remap[T]
    cen = m['bone_ct'][names.index('C_FaceBase_a')] + np.array([5.0, 0, 2.0])
    fig, axs = plt.subplots(2, len(poses), figsize=(3.4 * len(poses), 7.6))
    for c, (title, gq, gt) in enumerate(poses):
        X = skin(m, gq, gt, verts)
        for r, yaw in enumerate((0, 40)):
            shade.render(axs[r, c], X, T, TM, yaw, '%s (%d)' % (title, yaw))
            sx = np.sin(np.radians(yaw)) * cen[0]
            axs[r, c].set_xlim(sx - 7.5, sx + 7.5); axs[r, c].set_ylim(cen[2] - 9, cen[2] + 7)
    plt.tight_layout(); plt.savefig(out_png, dpi=80)


if __name__ == '__main__':
    main(*sys.argv[1:3])
