import sys, os
sys.path.insert(0, '/work/ys')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import clipdata
from sheets import CHAIN, tip, ix, d, mw


def peaks(sp, fps, thr=12.0):
    out = []
    for f in range(1, len(sp) - 1):
        if sp[f] >= thr and sp[f] >= sp[f - 1] and sp[f] > sp[f + 1]:
            out.append((round(f / fps, 2), round(float(sp[f]), 1)))
    return out


def strip(name, out, frames=None, cols=12, t0=None, t1=None):
    c = d['clips'][name]; W = c['W']; fps = c['fps']; nf = len(W)
    a = 0 if t0 is None else int(t0 * fps); b = nf - 1 if t1 is None else min(nf - 1, int(t1 * fps))
    fr = frames or [int(round(a + k * (b - a) / (cols - 1))) for k in range(cols)]
    fig, axes = plt.subplots(2, len(fr), figsize=(1.6 * len(fr), 4.4), squeeze=False)
    root = W[:, ix['root'], :3, 3]
    tp = tip(W)
    for k, f in enumerate(fr):
        for row, (u, lab) in enumerate(((0, 'side'), (1, 'front'))):
            ax = axes[row, k]
            o = root[f]
            for ch in CHAIN:
                p = np.array([W[f, ix[bn], :3, 3] for bn in ch]) - [o[0], o[1], 0]
                ax.plot(p[:, u], p[:, 2], '-', color='tab:blue' if 'left' in ch[-1] else ('tab:orange' if 'right' in ch[-1] else 'k'), lw=1.5)
            bb = W[f, mw, :3, 3] - [o[0], o[1], 0]; t = tp[f] - [o[0], o[1], 0]
            ax.plot([bb[u], t[u]], [bb[2], t[2]], '-', color='tab:red', lw=2.2)
            ax.axhline(0, color='0.8', lw=0.5); ax.axvline(0, color='0.9', lw=0.5)
            ax.set_xlim(-130, 190); ax.set_ylim(-40, 250); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
            if row == 0:
                ax.set_title('%.2fs fwd%+.0f' % (f / fps, root[f, 0] - root[0, 0]), fontsize=8)
    fig.suptitle(name + ' (blue: left arm/leg; side view facing right, front view: +Y right)', fontsize=9)
    plt.tight_layout()
    plt.savefig(out, dpi=60)
    plt.close(fig)


if __name__ == '__main__':
    os.makedirs('strips', exist_ok=True)
    for name in sys.argv[1:]:
        strip(name, 'strips/%s.png' % name)
