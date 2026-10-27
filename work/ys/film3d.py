import sys, os
sys.path.insert(0, '/work/ys')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sheets import CHAIN, ix, d, mw
SW = 180.0


def proj(P, az=-55.0, el=18.0):
    a, e = np.radians(az), np.radians(el)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    Q = P @ (Rx @ Rz).T
    return Q[..., 0], Q[..., 2], Q[..., 1]   # screen x, screen y, depth


def film(name, t0, t1, step=3, cols=8, az=-55.0, out=None, W=None, fps=None, label=None):
    if W is None:
        c = d['clips'][name]; W = c['W']; fps = c['fps']
    f0, f1 = int(round(t0 * fps)), min(len(W) - 1, int(round(t1 * fps)))
    frames = list(range(f0, f1 + 1, step))
    rows = (len(frames) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(2.0 * cols, 2.4 * rows), squeeze=False)
    for a in axes.flat:
        a.axis('off')
    root0 = W[f0, ix['root'], :3, 3].copy(); root0[2] = 0
    for k, f in enumerate(frames):
        ax = axes[divmod(k, cols)]
        # ground grid
        for g in range(-200, 401, 100):
            for seg in (np.array([[g, -200, 0], [g, 200, 0]]), np.array([[-200, g if g <= 200 else 200, 0], [400, g if g <= 200 else 200, 0]])):
                x, y, _ = proj(seg, az)
                ax.plot(x, y, '-', color='0.88', lw=0.5)
        # target
        th = np.linspace(0, 2 * np.pi, 30)
        x, y, _ = proj(np.stack([150 + 40 * np.cos(th), 40 * np.sin(th), 0 * th], -1), az); ax.plot(x, y, '-', color='0.6', lw=0.7)
        x, y, _ = proj(np.array([[150, 0, 0], [150, 0, 170]]), az); ax.plot(x, y, '-', color='0.6', lw=0.7)
        for ch in CHAIN:
            p = np.array([W[f, ix[b], :3, 3] for b in ch]) - root0
            x, y, _ = proj(p, az)
            ax.plot(x, y, '-', color='tab:blue' if 'left' in ch[-1] else ('tab:orange' if 'right' in ch[-1] else 'k'), lw=1.6)
        hd = W[f, ix['head'], :3, 3] - root0
        x, y, _ = proj(hd[None], az); ax.plot(x, y, 'o', color='k', ms=4)
        b = W[f, mw, :3, 3] - root0; t = b + W[f, mw, :3, 1] * SW
        x, y, _ = proj(np.stack([b, t]), az)
        ax.plot(x, y, '-', color='tab:red', lw=2.2); ax.plot(x[1:], y[1:], 'o', color='tab:red', ms=2.5)
        ax.set_xlim(-260, 320); ax.set_ylim(-120, 330); ax.set_aspect('equal')
        ax.set_title('%.2f' % (f / fps), fontsize=8)
    fig.suptitle('%s %.2f-%.2f s (seen from front-left; grey post = a target 1.5 m ahead)' % (label or name, t0, t1), fontsize=9)
    plt.tight_layout(h_pad=0.1, w_pad=0.05)
    out = out or 'film3d/%s_%.2f.png' % (name, t0)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    plt.savefig(out, dpi=55)
    plt.close(fig)
    return out


if __name__ == '__main__':
    print(film(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 3,
               az=float(sys.argv[5]) if len(sys.argv) > 5 else -55.0))
