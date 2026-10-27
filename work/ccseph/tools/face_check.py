"""Renders the face of a face_rig.py npz in Sephiroth's own facial animations from the game (decoded ACL clips: each face
bone's local transform set as the clip has it, as the game does): rest, blink, smile, surprise, angry, sneer and two
frames of cutscene lip sync (the widest jaw), front and three-quarter views, hair hidden.
    face_check.py <npz> <decoded clips .npy> <out png>"""
import sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path[:0] = ['/work/ccseph/tools', '/work/acl']
import shade
import pose as ACL
from face_rig import qmul, qinv, qrot


def pose_cs(par, local_q, local_t):
    n = len(local_q)
    gq = np.zeros((n, 4)); gt = np.zeros((n, 3))
    for i in range(n):
        p = par[i]
        if p < 0:
            gq[i], gt[i] = local_q[i], local_t[i]
        else:
            gq[i] = qmul(gq[p], local_q[i]); gt[i] = gt[p] + qrot(gq[p], local_t[i])
    return gq, gt


def skin(m, gq, gt):
    bq, bt = m['bone_cq'], m['bone_ct']
    P = m['pos']; out = np.zeros_like(P)
    for k in range(m['wbone'].shape[1]):
        w = m['wweight'][:, k]; nz = np.nonzero(w > 0)[0]
        if not len(nz):
            continue
        b = m['wbone'][nz, k]
        rel = np.array([qrot(qinv(bq[j]), P[v] - bt[j]) for j, v in zip(b, nz)])
        moved = np.array([qrot(gq[j], r) + gt[j] for j, r in zip(b, rel)])
        out[nz] += w[nz, None] * moved
    return out


def face_pose(m, clip, frame):
    """The rest locals with every face bone (under C_FaceBase_a) set from the clip's frame."""
    names = [str(n) for n in m['bone_names']]; par = list(m['bone_parents'])
    lq, lt = m['bone_lq'].copy(), m['bone_lt'].copy()
    fb = names.index('C_FaceBase_a')

    def under(i):
        while i >= 0:
            if i == fb:
                return True
            i = par[i]
        return False
    for i, n in enumerate(names):
        if i != fb and under(i) and n in clip['tracked']:
            j = ACL.IDX[n]
            lq[i] = clip['LQ'][frame, j]; lt[i] = clip['LT'][frame, j]
    return lq, lt


def main(npz, clips_npy, out_png):
    m = dict(np.load(npz))
    A = np.load(clips_npy, allow_pickle=True).item()
    names = [str(n) for n in m['bone_names']]; par = list(m['bone_parents'])
    i_dt = ACL.IDX['C_Dteeth']

    def widest(key):
        q = A[key]['LQ'][:, i_dt]
        a = 2 * np.degrees(np.arccos(np.clip(np.abs((q * ACL.REF_Q[i_dt]).sum(-1)), 0, 1)))
        return int(a.argmax())
    poses = [('rest', None, 0)] + [(k[2:], k, 0) for k in ('F_Eyelid_blink01', 'F_Smile01', 'F_Surprise01', 'F_Angry01', 'F_Sneer01')]
    for k in ('EV_JUNOE_8210_PC0010_00_C0440_FA', 'EV_JUNOE_8210_PC0010_00_C0500_FA'):
        f = widest(k); poses.append(('cut %s f%d' % (k.split('_')[-2], f), k, f))
    tri, tmat = m['tri'], m['tmat']
    slots = [str(s) for s in m['slots']]
    keep = np.isin(tmat, [slots.index(s) for s in ('CH_head', 'CH_eye', 'CH_mouth', 'CH_eyelash')])
    cen = m['bone_ct'][names.index('C_FaceBase_a')] + np.array([5.0, 0, 2.0])
    T, TM = tri[keep], tmat[keep]
    fig, axs = plt.subplots(2, len(poses), figsize=(3.4 * len(poses), 7.6))
    for c, (title, key, frame) in enumerate(poses):
        lq, lt = (m['bone_lq'], m['bone_lt']) if key is None else face_pose(m, A[key], frame)
        gq, gt = pose_cs(par, lq, lt)
        X = skin(m, gq, gt)
        for r, yaw in enumerate((0, 40)):
            shade.render(axs[r, c], X, T, TM, yaw, '%s (%d)' % (title, yaw))
            sx = np.sin(np.radians(yaw)) * cen[0]
            axs[r, c].set_xlim(sx - 7.5, sx + 7.5); axs[r, c].set_ylim(cen[2] - 9, cen[2] + 7)
    plt.tight_layout(); plt.savefig(out_png, dpi=80)
    print('wrote', out_png)


if __name__ == '__main__':
    main(*sys.argv[1:4])
