"""Contact sheets of Crisis Core clips: the Crisis Core mesh posed by the clip (in Rebirth's frame), N frames per row,
side view, a fixed window that follows the hips (the frame time and the sword trail windows in the titles).
    ccsheet.py <out png> <frames per clip> <clip npz> [...]"""
import json
import sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path[:0] = ['/work/ccanim/tools', '/work/ccseph/tools']
import ccretarget as C
import shade
from cccheck_retarget import skin

CC = '/work/ccseph/cc.npz'
POSE = '/work/ccseph/cc_rerig_v4_pose.npz'


def main(out_png, per, *clips):
    per = int(per)
    cc = np.load(CC, allow_pickle=True)
    P = np.load(POSE)
    conv = P['cc_conv']; cR0, cP0 = P['cc_R0'], P['cc_P0']
    pnames = [str(n) for n in P['cc_names']]
    cnames = [str(n) for n in cc['bone_names']]
    to_pose = np.array([pnames.index(n) for n in cnames])
    pos = cc['pos'] @ conv.T
    slots = [str(s) for s in cc['mat_slots']]
    keep = ~np.isin(cc['tmat'], [slots.index('CH_hair_StackTranslucent')])
    tri, tm = cc['tri'][keep], cc['tmat'][keep]
    fig, axs = plt.subplots(len(clips), per, figsize=(2.0 * per, 2.6 * len(clips)))
    axs = np.atleast_2d(axs)
    for r, path in enumerate(clips):
        A = np.load(path)
        an = [str(n) for n in A['bone_names']]
        to_clip = np.array([an.index(n) for n in cnames])
        Rcs, Pcs = C.clip_cs(A)
        Ra = np.einsum('ij,fbjk->fbik', conv, Rcs); Pa = np.einsum('ij,fbj->fbi', conv, Pcs)
        F = Ra.shape[0]; L = float(A['play_length'])
        n = json.loads(str(A['notifies']))
        trails = [(x['time'], x['end_time']) for x in n if x['cls'] == 'FairAnimNotifyStateTrail']
        hips = an.index('Hips')
        for c, f in enumerate(np.linspace(0, F - 1, per).astype(int)):
            X = skin(pos, cc['wbone'], cc['wweight'], Ra[f][to_clip], Pa[f][to_clip], cR0[to_pose], cP0[to_pose])
            t = f * L / max(F - 1, 1)
            on = any(a - 0.02 <= t <= b + 0.02 for a, b in trails)
            ax = axs[r, c]
            shade.render(ax, X, tri, tm, 90, '%s %.2fs%s' % (path.split('AS_sephiroth_')[-1][:-4] if c == 0 else '', t, ' *' if on else ''))
            h = Pa[f, hips]
            ax.set_xlim(h[0] - 170, h[0] + 170) if False else None
            cx = h[0]                                 # side view (yaw 90): screen x = world x
            ax.set_xlim(cx - 170, cx + 170); ax.set_ylim(h[2] - 130, h[2] + 210)
    plt.tight_layout(); plt.savefig(out_png, dpi=55)
    print('wrote', out_png)


if __name__ == '__main__':
    main(*sys.argv[1:])
