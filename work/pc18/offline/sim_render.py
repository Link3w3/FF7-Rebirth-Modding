"""Renders of PC0010_18 skinned with an offline kawaii run's bone transforms (anim_run's bin: component space).
    sim_render.py <rerig.npz> <run.bin> <out.png> frame,frame,... [--yaws=0,90,180] [--hide=slot,slot] [--z=zmin,zmax]"""
import sys
import numpy as np
sys.path[:0] = ['/work/pc18', '/work/ccseph/tools', '/work/pc18/offline']
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pc18_render as PR
from rerig import q2m
from analyze import load_run


def skin(m, R, P):
    Rb = np.array([q2m(q) for q in m['bone_cq']])
    Pb = m['bone_ct']
    out = np.zeros_like(m['pos'])
    for j in range(m['wbone'].shape[1]):
        b = m['wbone'][:, j]
        w = m['wweight'][:, j][:, None]
        Mr = np.einsum('vij,vkj->vik', R[b], Rb[b])
        out += w * (np.einsum('vij,vj->vi', Mr, m['pos'] - Pb[b]) + P[b])
    return out


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    opt = dict(x[2:].split('=', 1) for x in sys.argv[1:] if x.startswith('--'))
    m = np.load(a[0])
    run = load_run(a[1])
    frames = [int(x) for x in a[3].split(',')]
    yaws = [float(x) for x in opt.get('yaws', '0,90,180').split(',')]
    hide = opt.get('hide', '').split(',') if opt.get('hide') else []
    zr = tuple(float(x) for x in opt['z'].split(',')) if 'z' in opt else None
    pos, tri, tmat, mats, names, joints = PR.load(a[0])
    cm = PR.colours(mats)
    sel = ~np.isin(tmat, [i for i, n in enumerate(mats) if n in hide])
    fig, axs = plt.subplots(len(yaws), len(frames), figsize=(6 * len(frames), 7 * len(yaws)), squeeze=False)
    for c, f in enumerate(frames):
        R = np.array([q2m(q) for q in run[f, :, :4]])
        P = run[f, :, 4:].astype(float)
        pp = skin(m, R, P)
        for r, yaw in enumerate(yaws):
            PR.draw(axs[r, c], pp, tri[sel], tmat[sel], cm, yaw, zr, None, None, 'frame %d (%.2f s) yaw %d' % (f, f / 60.0, yaw))
    plt.tight_layout()
    plt.savefig(a[2], dpi=int(opt.get("dpi", "45")))
    print('saved', a[2])


if __name__ == '__main__':
    main()
