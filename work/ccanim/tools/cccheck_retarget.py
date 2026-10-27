"""Side-by-side check of ccretarget.py: the Crisis Core mesh skinned by the Crisis Core clip (left) and the re-rigged
PC0010_16 model skinned by the retargeted bones (right), with the Crisis Core sword drawn on R_Weapon_a through
Rebirth's weapon socket (if the convention is right it lies where the Crisis Core sword is), at a few frames, front
and side views. Also prints the per-frame distance between the two swords' tips and grips.
    cccheck_retarget.py <clip npz> <cc.npz> <re-rig pose npz> <model npz> <out png> [frames...]"""
import sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path[:0] = ['/work/ccanim/tools', '/work/ccseph/tools']
import ccretarget as C
import shade


def skin(pos, wb, ww, Rb, Pb, R0, P0):
    out = np.zeros_like(pos)
    for k in range(wb.shape[1]):
        w = ww[:, k]
        nz = np.nonzero(w > 0)[0]
        if not len(nz):
            continue
        b = wb[nz, k]
        rel = np.einsum('vji,vj->vi', R0[b], pos[nz] - P0[b])
        out[nz] += w[nz, None] * (np.einsum('vij,vj->vi', Rb[b], rel) + Pb[b])
    return out


def main(clip, cc_path, pose_path, model_path, out_png, *frames):
    A = np.load(clip)
    cc = np.load(cc_path, allow_pickle=True)
    rig = C.Rig(pose_path, model_path)
    LQ, LT, G, T, rep = rig.retarget(A)
    F = LQ.shape[0]
    frames = [int(f) for f in frames] or list(np.linspace(0, F - 1, 4).astype(int))
    an = [str(n) for n in A['bone_names']]
    Rcs, Pcs = C.clip_cs(A)
    conv = rig.conv
    Ra = np.einsum('ij,fbjk->fbik', conv, Rcs); Pa = np.einsum('ij,fbj->fbi', conv, Pcs)
    # the Crisis Core mesh in Rebirth's frame, its bones in the clip's order
    cnames = [str(n) for n in cc['bone_names']]
    to_clip = np.array([an.index(n) for n in cnames])
    to_pose = np.array([rig.cc_ix[n] for n in cnames])
    pos_cc = cc['pos'] @ conv.T
    slots = [str(s) for s in cc['mat_slots']]
    keep_cc = ~np.isin(cc['tmat'], [slots.index('CH_hair_StackTranslucent')])
    tri_cc, tm_cc = cc['tri'][keep_cc], cc['tmat'][keep_cc]
    sword_t = cc['tri'][cc['tmat'] == slots.index('CH_wepA')]
    sv = np.unique(sword_t.ravel())
    s_ix = rig.cc_ix['wpn_body']
    sword_local = np.einsum('ji,vj->vi', rig.cR0[s_ix], pos_cc[sv] - rig.cP0[s_ix])     # in wpn_body's frame
    sword_w = sword_local @ C.SWORD_A.T                                                # Rebirth weapon mesh axes
    remap = -np.ones(len(pos_cc), int); remap[sv] = np.arange(len(sv))
    sword_tri = remap[sword_t]
    M = np.load(model_path)
    names = rig.names
    tri_n, tm_n = M['tri'], M['tmat']
    w_ix = names.index('R_Weapon_a')
    tip = np.argmax(sword_local[:, 2]); grip = np.argmin(np.linalg.norm(sword_local, axis=1))
    fig, axs = plt.subplots(2, 2 * len(frames), figsize=(3.2 * 2 * len(frames), 8))
    for c, f in enumerate(frames):
        Xcc = skin(pos_cc, cc['wbone'], cc['wweight'], Ra[f][to_clip], Pa[f][to_clip], rig.cR0[to_pose], rig.cP0[to_pose])
        Xn = skin(M['pos'].astype(float), M['wbone'], M['wweight'], G[f], T[f], rig.Rn, rig.Pn)
        Wr = G[f, w_ix] @ C.SOCKET_R
        Xs = sword_w @ Wr.T + T[f, w_ix]
        d_tip = np.linalg.norm(Xs[tip] - Xcc[sv[tip]]); d_grip = np.linalg.norm(Xs[grip] - Xcc[sv[grip]])
        print('frame %3d: sword tip %.1f cm, grip %.1f cm apart' % (f, d_tip, d_grip))
        allX = np.r_[Xn, Xs]
        allT = np.r_[tri_n, sword_tri + len(Xn)]
        allM = np.r_[tm_n, np.full(len(sword_tri), 7)]
        for r, yaw in enumerate((0, 90)):
            shade.render(axs[r, 2 * c], Xcc, tri_cc, tm_cc, yaw, 'CC f%d (%d)' % (f, yaw))
            shade.render(axs[r, 2 * c + 1], allX, allT, allM, yaw, 'PC0010_16 f%d' % f)
            for a in (axs[r, 2 * c], axs[r, 2 * c + 1]):
                ctr = Pa[f, an.index('Hips')]
                cx = (ctr @ np.array([[np.cos(np.radians(yaw)), -np.sin(np.radians(yaw)), 0], [np.sin(np.radians(yaw)), np.cos(np.radians(yaw)), 0], [0, 0, 1]]).T)[1]
                a.set_xlim(cx - 160, cx + 160); a.set_ylim(-10, 300)
    plt.tight_layout(); plt.savefig(out_png, dpi=70)
    print(rep)


if __name__ == '__main__':
    main(*sys.argv[1:])
