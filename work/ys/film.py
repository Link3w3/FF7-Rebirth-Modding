import sys, os
sys.path.insert(0, '/work/ys')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sheets import CHAIN, ix, d, mw
SW = 180.0


def film(name, t0, t1, step=2, out=None, cols=16):
    c = d['clips'][name]; W = c['W']; fps = c['fps']
    f0, f1 = int(round(t0 * fps)), min(len(W) - 1, int(round(t1 * fps)))
    frames = list(range(f0, f1 + 1, step))
    rows = (len(frames) + cols - 1) // cols
    fig, axes = plt.subplots(2 * rows, cols, figsize=(1.15 * cols, 2.3 * rows), squeeze=False)
    for a in axes.flat:
        a.axis('off')
    root0 = W[f0, ix['root'], :3, 3]
    for k, f in enumerate(frames):
        r, col = divmod(k, cols)
        for v, (u, vv) in enumerate(((0, 2), (0, 1))):
            ax = axes[2 * r + v, col]
            ax.axis('on'); ax.set_xticks([]); ax.set_yticks([])
            for ch in CHAIN:
                p = np.array([W[f, ix[b], :3, 3] for b in ch]) - root0
                ax.plot(p[:, u], p[:, vv], '-', color='tab:blue' if 'left' in ch[-1] else ('tab:orange' if 'right' in ch[-1] else 'k'), lw=1.2)
            b = W[f, mw, :3, 3] - root0; t = b + W[f, mw, :3, 1] * SW
            ax.plot([b[u], t[u]], [b[vv], t[vv]], '-', color='tab:red', lw=2)
            ax.plot([t[u]], [t[vv]], 'o', color='tab:red', ms=2)
            if v == 0:
                ax.axhline(0, color='0.8', lw=0.5)
                ax.set_xlim(-200, 320); ax.set_ylim(-60, 300)
                ax.set_title('%.2f' % (f / fps), fontsize=7)
            else:
                ax.add_patch(plt.Circle((150, 0), 50, fill=False, color='0.7', lw=0.6))
                ax.set_xlim(-200, 320); ax.set_ylim(-200, 200)
            ax.set_aspect('equal')
    fig.suptitle('%s %.2f-%.2f s (top row side view, bottom row top view; +X forward, left arm blue)' % (name, t0, t1), fontsize=8)
    plt.tight_layout(h_pad=0.1, w_pad=0.05)
    out = out or 'film/%s_%.2f.png' % (name, t0)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    plt.savefig(out, dpi=55)
    plt.close(fig)
    return out


if __name__ == '__main__':
    print(film(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 2))
