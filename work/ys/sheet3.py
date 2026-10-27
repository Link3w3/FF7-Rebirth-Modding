import sys, os
sys.path.insert(0, '/work/ys')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sheets import CHAIN, tip, ix, d, mw
from sheet2 import peaks


def multi(names, out, cols=14):
    fig, axes = plt.subplots(2 * len(names), cols + 1, figsize=(1.25 * (cols + 1), 2.0 * 2 * len(names)), squeeze=False,
                             gridspec_kw=dict(width_ratios=[1] * cols + [2.2]))
    for r, name in enumerate(names):
        c = d['clips'][name]; W = c['W']; fps = c['fps']; nf = len(W)
        fr = [int(round(k * (nf - 1) / (cols - 1))) for k in range(cols)]
        root = W[:, ix['root'], :3, 3]
        tp = tip(W)
        for k, f in enumerate(fr):
            for row, u in enumerate((0, 1)):
                ax = axes[2 * r + row, k]
                o = root[f]
                for ch in CHAIN:
                    p = np.array([W[f, ix[bn], :3, 3] for bn in ch]) - [0, 0, 0]
                    ax.plot(p[:, u], p[:, 2], '-', color='tab:blue' if 'left' in ch[-1] else ('tab:orange' if 'right' in ch[-1] else 'k'), lw=1.3)
                bb = W[f, mw, :3, 3]; t = tp[f]
                ax.plot([bb[u], t[u]], [bb[2], t[2]], '-', color='tab:red', lw=2.0)
                ax.axhline(0, color='0.8', lw=0.5); ax.axvline(0, color='0.9', lw=0.5)
                cx = o[u]
                ax.set_xlim(cx - 150, cx + 170); ax.set_ylim(-40, 260); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
                if row == 0:
                    ax.set_title('%.2f %+.0f' % (f / fps, root[f, 0] - root[0, 0]), fontsize=7)
                if k == 0:
                    ax.set_ylabel(name if row == 0 else 'front', fontsize=8)
        sp = np.r_[0, np.linalg.norm(np.diff(tp, axis=0), axis=-1) * fps] / 100.0
        t = np.arange(nf) / fps
        ax = axes[2 * r, cols]; ax.plot(t, sp, 'tab:red', lw=1); ax.tick_params(labelsize=6); ax.set_title('tip m/s', fontsize=7)
        ax.grid(alpha=0.3)
        ax = axes[2 * r + 1, cols]
        ax.plot(t, (root[:, 0] - root[0, 0]) / 100, 'tab:green', lw=1, label='fwd m'); ax.plot(t, (root[:, 1] - root[0, 1]) / 100, 'tab:olive', lw=1, label='side m')
        ax.plot(t, W[:, ix['hip'], 2, 3] / 100, 'k', lw=0.8, label='hip z m')
        ax.tick_params(labelsize=6); ax.grid(alpha=0.3); ax.legend(fontsize=5)
    plt.tight_layout(h_pad=0.2, w_pad=0.1)
    plt.savefig(out, dpi=52)
    plt.close(fig)


if __name__ == '__main__':
    os.makedirs('multi', exist_ok=True)
    names = sys.argv[2:]
    multi(names, 'multi/%s.png' % sys.argv[1])
