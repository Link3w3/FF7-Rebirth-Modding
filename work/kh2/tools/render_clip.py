"""Stick-figure sheet of a Clip (after edits): side and front views at evenly spaced frames, with the ground."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from clip import Clip

CHAINS = [
    (['C_Hip_a', 'C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d', 'C_Neck_a', 'C_Head_a'], 'k'),
    (['C_Spine_d', 'R_Shoulder_a', 'R_UpperArm_a', 'R_Forearm_a', 'R_Hand_a'], 'r'),
    (['C_Spine_d', 'L_Shoulder_a', 'L_UpperArm_a', 'L_Forearm_a', 'L_Hand_a'], 'b'),
    (['C_Hip_a', 'R_UpperLeg_a', 'R_Foreleg_a', 'R_Foot_a', 'R_Toe_a'], 'r'),
    (['C_Hip_a', 'L_UpperLeg_a', 'L_Foreleg_a', 'L_Foot_a', 'L_Toe_a'], 'b'),
]


def draw(clip, out_png, cols=8, title=''):
    bones = sorted({b for ch, _ in CHAINS for b in ch} | {'Trans', 'R_Weapon_a'})
    w = clip.world(bones)
    P = {b: w[b][0] for b in bones}
    fr = sorted(set(int(round(x)) for x in np.linspace(0, clip.frames - 1, cols)))
    fig, axes = plt.subplots(2, len(fr), figsize=(2.1 * len(fr), 5.6))
    root = P['Trans']
    for c, f in enumerate(fr):
        for r, (hx, sign, label) in enumerate(((0, 1, 'side'), (1, -1, 'front'))):
            ax = axes[r][c]
            cx = root[f, hx]
            for ch, col in CHAINS:
                pts = np.array([P[b][f] for b in ch])
                ax.plot(sign * (pts[:, hx] - cx), pts[:, 2], col + '-', lw=1.6)
            ax.plot(sign * (P['C_Head_a'][f, hx] - cx), P['C_Head_a'][f, 2] + 12, 'ko', ms=7, mfc='w')
            ax.axhline(root[f, 2], color='0.6', lw=0.8)
            ax.set_xlim(-140, 140); ax.set_ylim(root[:, 2].min() - 10, root[:, 2].max() + 240)
            ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
            if r == 0:
                ax.set_title('f%d (%.2fs)' % (f, f / clip.fps), fontsize=8)
    rm = root[-1] - root[0]
    fig.suptitle('%s  %d frames %.2fs  root %+.0f %+.0f %+.0f  %s' % (clip.name, clip.frames, clip.seconds, rm[0], rm[1], rm[2], title), fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out_png, dpi=72)
    plt.close(fig)
