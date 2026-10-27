"""Contact sheets of ch049's clips: stick figures (side view: forward +X right, up +Z; front view: Y), the Masamune along
main_weapon's +X (150 cm), plus the sword tip speed and the root's forward travel over time."""
import sys, os
sys.path.insert(0, '/work/ys')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import clipdata

d = clipdata.load(); names = d['names']; ix = {k: i for i, k in enumerate(names)}; par = d['parents']
CHAIN = [['root', 'hip'], ['hip', 'spine1', 'spine2', 'spine3', 'spine4', 'neck', 'head'],
         ['spine4', 'left_shoulder', 'left_arm', 'left_forearm', 'left_hand'], ['spine4', 'right_shoulder', 'right_arm', 'right_forearm', 'right_hand'],
         ['hip', 'left_upleg', 'left_leg', 'left_foot', 'left_toe'], ['hip', 'right_upleg', 'right_leg', 'right_foot', 'right_toe']]
SW = 150.0
mw = ix['main_weapon']


def tip(W):
    return W[:, mw, :3, 3] + W[:, mw, :3, 1] * SW


def sheet(clips, out, cols=10):
    rows = len(clips)
    fig, axes = plt.subplots(rows, cols + 1, figsize=(2.0 * (cols + 1), 2.3 * rows), squeeze=False)
    for r, name in enumerate(clips):
        c = d['clips'][name]; W = c['W']; fps = c['fps']; nf = len(W)
        tp = tip(W)
        sp = np.r_[0, np.linalg.norm(np.diff(tp, axis=0), axis=-1) * fps] / 100.0   # m/s
        root = W[:, ix['root'], :3, 3]
        for k in range(cols):
            f = int(round(k * (nf - 1) / (cols - 1)))
            ax = axes[r, k]
            o = root[f]
            for ch in CHAIN:
                p = np.array([W[f, ix[b], :3, 3] for b in ch]) - [o[0], o[1], 0]
                ax.plot(p[:, 0], p[:, 2], '-', color='k' if 'left' not in ch[-1] else 'tab:blue', lw=1.2)
                ax.plot(p[:, 1] + 260, p[:, 2], '-', color='0.6' if 'left' not in ch[-1] else 'tab:cyan', lw=0.8)
            b = W[f, mw, :3, 3] - [o[0], o[1], 0]; t = tp[f] - [o[0], o[1], 0]
            ax.plot([b[0], t[0]], [b[2], t[2]], '-', color='tab:red', lw=2)
            ax.plot([b[1] + 260, t[1] + 260], [b[2], t[2]], '-', color='salmon', lw=1.2)
            ax.axhline(0, color='0.85', lw=0.5)
            ax.set_xlim(-170, 420); ax.set_ylim(-60, 260); ax.set_aspect('equal'); ax.axis('off')
            ax.set_title('%s %.2fs' % (name if k == 0 else '', f / fps), fontsize=7)
        ax = axes[r, cols]
        t = np.arange(nf) / fps
        ax.plot(t, sp, color='tab:red', lw=1); ax.set_ylabel('tip m/s', fontsize=6)
        ax2 = ax.twinx(); ax2.plot(t, (root[:, 0] - root[0, 0]) / 100, color='tab:green', lw=1)
        ax2.plot(t, (root[:, 1] - root[0, 1]) / 100, color='tab:olive', lw=0.7)
        ax.tick_params(labelsize=5); ax2.tick_params(labelsize=5)
    plt.tight_layout()
    plt.savefig(out, dpi=55)
    plt.close(fig)


if __name__ == '__main__':
    os.makedirs('sheets', exist_ok=True)
    allc = sorted(d['clips'])
    groups = {'skills_a': [c for c in allc if c.startswith('skill_')][:10], 'skills_b': [c for c in allc if c.startswith('skill_')][10:20],
              'skills_c': [c for c in allc if c.startswith('skill_')][20:30], 'skills_d': [c for c in allc if c.startswith('skill_')][30:],
              'basic': [c for c in allc if not c.startswith(('skill_', 'outgame', 'facial'))]}
    for g, cl in groups.items():
        if len(cl) > 12:
            for i in range(0, len(cl), 12):
                sheet(cl[i:i + 12], 'sheets/%s_%d.png' % (g, i // 12))
        else:
            sheet(cl, 'sheets/%s.png' % g)
    print(os.listdir('sheets'))
