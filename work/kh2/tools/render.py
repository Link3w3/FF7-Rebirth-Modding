"""Contact sheets of the KH2 animations: side (X-Z) and front (Y-Z) stick figures at evenly spaced frames."""
import os, sys, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pose import Anim
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

CHAINS = [
    (['C_Hip_a', 'C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d', 'C_Neck_a', 'C_Head_a'], 'k'),
    (['C_Spine_d', 'R_Shoulder_a', 'R_UpperArm_a', 'R_Forearm_a', 'R_Hand_a'], 'r'),
    (['C_Spine_d', 'L_Shoulder_a', 'L_UpperArm_a', 'L_Forearm_a', 'L_Hand_a'], 'b'),
    (['C_Hip_a', 'R_UpperLeg_a', 'R_Foreleg_a', 'R_Foot_a', 'R_Toe_a'], 'r'),
    (['C_Hip_a', 'L_UpperLeg_a', 'L_Foreleg_a', 'L_Foot_a', 'L_Toe_a'], 'b'),
]
COLS = 8


def name_of(path):
    return os.path.basename(path).replace('_001_remap_remap.fbx', '').replace('_remap_remap.fbx', '').replace('.fbx', '')


def frames_of(a):
    return sorted(set(int(round(x)) for x in np.linspace(0, a.n - 1, COLS)))


def draw(path, out_png, blade_axis):
    a = Anim(path)
    fr = frames_of(a)
    P = {b: a.pos(b) for ch, _ in CHAINS for b in ch if b in a.byname}
    wr, wl = a.pos('R_Weapon_a'), a.pos('L_Weapon_a')
    blade = a.axis('R_Weapon_a', blade_axis) * 150.0
    root = a.pos('Trans')
    right = a.pos('R_UpperLeg_a') - a.pos('L_UpperLeg_a')
    fwd = np.cross(right, np.array([0.0, 0.0, 1.0]))
    yaw = np.degrees(np.arctan2(fwd[:, 1], fwd[:, 0]))
    fig, axes = plt.subplots(2, len(fr), figsize=(2.1 * len(fr), 5.6))
    allp = np.concatenate([v for v in P.values()] + [wr + blade])
    zlo, zhi = min(0, allp[:, 2].min()) - 10, allp[:, 2].max() + 10
    for c, f in enumerate(fr):
        for r, (hx, sign, label) in enumerate(((0, 1, 'side'), (1, -1, 'front'))):
            ax = axes[r][c] if len(fr) > 1 else axes[r]
            cx = root[f, hx]
            for ch, col in CHAINS:
                pts = np.array([P[b][f] for b in ch if b in P])
                ax.plot(sign * (pts[:, hx] - cx), pts[:, 2], col + '-', lw=1.6)
            ax.plot(sign * (P['C_Head_a'][f, hx] - cx), P['C_Head_a'][f, 2] + 12, 'ko', ms=7, mfc='w')
            b0, b1 = wr[f], wr[f] + blade[f]
            ax.plot([sign * (b0[hx] - cx), sign * (b1[hx] - cx)], [b0[2], b1[2]], '-', color='orange', lw=2.2)
            ax.axhline(0, color='0.7', lw=0.8)
            ax.plot([0], [root[f, 2]], 'g^', ms=6)
            hp = P['C_Hip_a'][f]
            ax.annotate('', xy=(sign * (hp[hx] - cx + 35 * fwd[f, hx] / max(1e-6, np.linalg.norm(fwd[f]))), hp[2]), xytext=(sign * (hp[hx] - cx), hp[2]),
                        arrowprops=dict(arrowstyle='->', color='g', lw=1.5))
            ax.set_xlim(-140, 140)
            ax.set_ylim(zlo, max(zhi, 240))
            ax.set_aspect('equal')
            ax.set_xticks([]); ax.set_yticks([])
            if r == 0:
                ax.set_title('f%d  yaw %+.0f  z %+.0f' % (f, yaw[f], root[f, 2]), fontsize=8)
            if c == 0:
                ax.set_ylabel(label + (' (fwd ->)' if r == 0 else ' (facing you)'), fontsize=7)
    rm = root[-1] - root[0]
    fig.suptitle('%s   %d frames %.2fs   root %+.0f %+.0f %+.0f   hipZ %.0f..%.0f' % (
        name_of(path), a.n, (a.n - 1) / a.fps, rm[0], rm[1], rm[2], P['C_Hip_a'][:, 2].min(), P['C_Hip_a'][:, 2].max()), fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out_png, dpi=72)
    plt.close(fig)


if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    axis = tuple(float(x) for x in sys.argv[3].split(',')) if len(sys.argv) > 3 else (1.0, 0.0, 0.0)
    names = sys.argv[4].split(',') if len(sys.argv) > 4 else None
    os.makedirs(out, exist_ok=True)
    files = sorted(glob.glob(src + '/*.fbx'))
    if names:
        files = [f for f in files if name_of(f) in names]
    import multiprocessing as mp
    with mp.Pool(8) as pool:
        pool.starmap(draw, [(f, os.path.join(out, name_of(f) + '.png'), axis) for f in files])
    print('drew', len(files))
