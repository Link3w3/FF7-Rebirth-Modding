import sys, os, json
sys.path.insert(0, '/work/ys')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sheets import CHAIN, ix, d, mw
from film3d import proj
SW = 180.0


def draw(ax, W, f, root0, az, hit=False):
    for g in range(-200, 401, 100):
        for seg in (np.array([[g, -200, 0], [g, 200, 0]]), np.array([[-200, min(g, 200), 0], [400, min(g, 200), 0]])):
            x, y, _ = proj(seg, az); ax.plot(x, y, '-', color='0.9', lw=0.4)
    x, y, _ = proj(np.array([[150, 0, 0], [150, 0, 170]]), az); ax.plot(x, y, '-', color='0.6', lw=0.8)
    for ch in CHAIN:
        p = np.array([W[f, ix[b], :3, 3] for b in ch]) - root0
        x, y, _ = proj(p, az)
        ax.plot(x, y, '-', color='tab:blue' if 'left' in ch[-1] else ('tab:orange' if 'right' in ch[-1] else 'k'), lw=1.4)
    b = W[f, mw, :3, 3] - root0; t = b + W[f, mw, :3, 1] * SW
    x, y, _ = proj(np.stack([b, t]), az)
    ax.plot(x, y, '-', color='magenta' if hit else 'tab:red', lw=2.4 if hit else 2.0)
    ax.set_xlim(-260, 380); ax.set_ylim(-120, 330); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color('magenta' if hit else '0.8')


def moves_film(moves, out, cols=10, az=-55.0):
    fig, axes = plt.subplots(len(moves), cols, figsize=(1.5 * cols, 1.25 * len(moves)), squeeze=False)
    for r, m in enumerate(moves):
        c = d['clips'][m['source']]; W = c['W']; fps = c['fps']; L = (len(W) - 1) / fps
        t0, t1 = m.get('clip', [0, 0]); t1 = t1 or L; sp = m.get('speed', 1.0)
        n_out = (t1 - t0) / sp
        hits = [h['time'] for h in m['hits']]
        times = list(np.linspace(0, n_out, cols))
        # snap the nearest frame to each hit
        for h in hits:
            k = int(np.argmin([abs(t - h) for t in times])); times[k] = h
        root0 = W[int(round(t0 * fps)), ix['root'], :3, 3].copy(); root0[2] = 0
        for k, t in enumerate(times):
            f = min(len(W) - 1, int(round((t0 + t * sp) * fps)))
            ax = axes[r, k]
            draw(ax, W, f, root0, az, hit=any(abs(t - h) < 1e-6 for h in hits))
            ax.set_title('%.2f' % t, fontsize=6, pad=1)
            if k == 0:
                ax.set_ylabel('%s\n%s' % (m['name'].replace('B_', ''), m['source'].replace('skill_', 's')), fontsize=6)
    plt.tight_layout(h_pad=0.05, w_pad=0.05)
    plt.savefig(out, dpi=55); plt.close(fig)


if __name__ == '__main__':
    plan = json.load(open('ys_moves.json'))
    by = {m['name']: m for m in plan['moves']}
    names = sys.argv[2:]
    moves_film([by[n] for n in names], sys.argv[1])
    print(sys.argv[1])
