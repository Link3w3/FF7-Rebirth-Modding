"""Stick-figure sheets of Sora's KH2 move animations (raw keys from the editor) as the game would show them: the root's
animated rotation left out (the body then stands Z-up facing +X, as the game's animations) and the root's travel, which
the KH2 imports keep on +Y, put on +X (forward). Side view (X, Z) and front view (Y, Z) at evenly spaced frames, times at
KH2's 60 fps."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from kh2raw import Anim
import fk

CHAINS = [
    (['center', 'koshi', 'hara1', 'hara2', 'mune', 'kubi', 'atama'], 'k'),
    (['mune', 'R_kata', 'R_ude1', 'R_ude2', 'R_te'], 'r'),
    (['mune', 'L_kata', 'L_ude1', 'L_ude2', 'L_te'], 'b'),
    (['koshi', 'R_momo', 'R_sune', 'R_ashi1', 'R_ashi2'], 'r'),
    (['koshi', 'L_momo', 'L_sune', 'L_ashi1', 'L_ashi2'], 'b'),
]
TURN = np.array([[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])   # +Y -> +X (yaw -90): the root's travel only
BLADE = 75.0


def positions(a, turn=True):
    out = []
    for f in range(a.frames):
        CQ, CT = fk.pose_flat_root(a, f)
        P = {b: CT[fk.INDEX[b]] for b in fk.NAMES}
        q = CQ[fk.INDEX['R_buki']]
        P['blade_tip'] = P['R_buki'] + fk.qrot(q, np.array([0.0, BLADE, 0.0]))
        P['blade_tipx'] = P['R_buki'] + fk.qrot(q, np.array([BLADE, 0.0, 0.0]))
        P['blade_tipz'] = P['R_buki'] + fk.qrot(q, np.array([0.0, 0.0, BLADE]))
        if turn:          # the root's travel (+Y in the import) forward; the body keeps its own frame
            r = P['kh_sk'].copy()
            d = TURN @ r - r
            P = {k: v + d for k, v in P.items()}
        out.append(P)
    return out


def draw(a, out_png, cols=8, blade='blade_tip', fps=60.0):
    Ps = positions(a)
    root = np.array([P['kh_sk'] for P in Ps])
    fr = sorted(set(int(round(x)) for x in np.linspace(0, a.frames - 1, cols)))
    fig, axes = plt.subplots(2, len(fr), figsize=(2.1 * len(fr), 5.6))
    for c, f in enumerate(fr):
        P = Ps[f]
        for r, (hx, sign) in enumerate(((0, 1), (1, -1))):
            ax = axes[r][c]
            cx = root[f, hx]
            for ch, col in CHAINS:
                pts = np.array([P[b] for b in ch])
                ax.plot(sign * (pts[:, hx] - cx), pts[:, 2], col + '-', lw=1.6)
            bl = np.array([P['R_buki'], P[blade]])
            ax.plot(sign * (bl[:, hx] - cx), bl[:, 2], '-', color='orange', lw=2.2)
            ax.plot(sign * (P['atama'][hx] - cx), P['atama'][2] + 8, 'ko', ms=7, mfc='w')
            ax.axhline(root[f, 2], color='0.6', lw=0.8)
            ax.set_xlim(-150, 150); ax.set_ylim(root[:, 2].min() - 10, root[:, 2].max() + 230)
            ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
            if r == 0:
                ax.set_title('f%d (%.2fs)' % (f, f / fps), fontsize=8)
    rm = root[-1] - root[0]
    fig.suptitle('%s  %d frames %.2fs at 60 fps  root %+.0f %+.0f %+.0f (fwd, right, up)' % (a.name, a.frames, (a.frames - 1) / fps, rm[0], rm[1], rm[2]), fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out_png, dpi=60)
    plt.close(fig)
    return out_png


if __name__ == '__main__':
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for n in sys.argv[2:]:
        print(draw(Anim(n), os.path.join(out, n + '.png')))
