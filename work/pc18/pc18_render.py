"""Flat-shaded matplotlib renders of a PC0010_18 npz (pc18_load / pc18_rerig layout): per-material colours, views by yaw.
    pc18_render.py <npz> <out.png> [zmin zmax] [--joints name,name,...]"""
import sys, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
sys.path.insert(0, '/work/bfs17')

def load(path):
    m = np.load(path)
    if 'cp' in m:      # pc18_load
        pos = m['cp']; tri = m['corner_cp'][m['tri']]; tmat = m['tmat']; mats = [str(x) for x in m['mat_names']]
        names = [str(n) for n in m['names']]; joints = m['P']
    else:              # pc18_rerig
        pos = m['pos']; tri = m['corner_cp'][m['tri']]; tmat = m['tmat']; mats = [str(x) for x in m['slots']]
        names = [str(n) for n in m['bone_names']]; joints = m['bone_ct']
    return pos, tri, tmat, mats, names, joints

def colours(mats):
    rng = np.random.RandomState(7)
    out = {}
    for i, n in enumerate(mats):
        if n.startswith('PC0010_00_Hair'): out[i] = (0.85, 0.85, 0.9)
        elif n.startswith('PC0010_00') or n == 'Common_Mouth': out[i] = (0.95, 0.75, 0.6)
        else: out[i] = tuple(0.25 + 0.6 * rng.rand(3))
    return out

def draw(ax, pos, tri, tmat, cmap, yaw, zr=None, joints=None, labels=None, title=''):
    y = np.radians(yaw); c, s = np.cos(y), np.sin(y)
    # camera on +X rotated by yaw about Z: screen x = -(p . right), we look from the camera toward the model
    d = np.array([c, s, 0.0]); right = np.array([-s, c, 0.0])
    sx = pos @ right; sz = pos[:, 2]; depth = pos @ d
    v = np.stack([sx[tri], sz[tri]], -1)
    keep = np.ones(len(tri), bool)
    if zr:
        keep &= (sz[tri].max(1) >= zr[0]) & (sz[tri].min(1) <= zr[1])
    v3 = pos[tri]
    n = np.cross(v3[:, 1] - v3[:, 0], v3[:, 2] - v3[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    L = d * 0.7 + np.array([0, 0, 0.6]) + right * 0.3; L /= np.linalg.norm(L)
    shade = 0.35 + 0.65 * np.abs(n @ L)
    base = np.array([cmap[int(k)] for k in tmat])
    col = np.clip(base * shade[:, None], 0, 1)
    dep = depth[tri].mean(1)
    idx = np.nonzero(keep)[0]
    idx = idx[np.argsort(dep[idx])]
    ax.add_collection(PolyCollection(v[idx], facecolors=col[idx], edgecolors='none', antialiased=False))
    if joints is not None:
        jx = joints @ right; jz = joints[:, 2]
        ax.scatter(jx, jz, s=8, c='red', zorder=5)
        for x, z, t in zip(jx, jz, labels): ax.text(x, z, t, fontsize=6, color='darkred', zorder=6)
    xs = sx[tri[keep]]; zs = sz[tri[keep]]
    ax.set_xlim(xs.min() - 3, xs.max() + 3); ax.set_ylim(zs.min() - 3, zs.max() + 3)
    ax.set_aspect('equal'); ax.axis('off'); ax.set_title(title, fontsize=9)

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    jn = [x.split('=', 1)[1] for x in sys.argv[1:] if x.startswith('--joints=')]
    pos, tri, tmat, mats, names, joints = load(a[0])
    zr = (float(a[2]), float(a[3])) if len(a) > 3 else None
    cmap = colours(mats)
    J = L = None
    if jn:
        want = jn[0].split(',')
        sel = [names.index(w) for w in want if w in names]
        J = joints[sel]; L = [names[i] for i in sel]
    fig, axs = plt.subplots(1, 4, figsize=(28, 11))
    for ax, (yaw, t) in zip(axs, ((0, 'front'), (90, 'right side (from +Y)'), (180, 'back'), (-35, 'three quarter'))):
        draw(ax, pos, tri, tmat, cmap, yaw, zr, J, L, t)
    plt.tight_layout(); plt.savefig(a[1], dpi=60)
    print('saved', a[1])
