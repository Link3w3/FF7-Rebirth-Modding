"""Renders of the helmet with hair, the hair's coverage applied (alpha-tested) and its colour texture.
    hair_tview.py <hair npz> <out.png> [flipv 0|1] [views: head|full]"""
import sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, '/work/bfs17')
from zbuf import view_matrix, raster_tex
r = np.load('bfs17_rerig.npz', allow_pickle=True)
d = np.load(sys.argv[1], allow_pickle=True)
out = sys.argv[2]
flipv = len(sys.argv) > 3 and sys.argv[3] == '1'
mode = sys.argv[4] if len(sys.argv) > 4 else 'head'
cov = np.load('hair/tex/coverage.npy'); colr = np.load('hair/tex/color_srgb.npy')
colr = np.clip(colr * 1.6, 0, 1)        # (the colour map is mid grey; brightened to read as Sephiroth's silver)
pos_b, tri_b, tm = r['pos'], r['tri'], r['tmat']
slots = [str(s) for s in r['slots']]
face = np.array([s.startswith('PC0010_00') or s == 'Common_Mouth' for s in slots])
names = list(r['bone_names']); centre = r['bone_ct'][names.index('C_Head_a')] + [0, 0, 9]
cb = np.tile([0.45, 0.47, 0.55], (len(tri_b), 1)); cb[face[tm]] = [0.95, 0.65, 0.55]
if mode == 'head':
    nearb = (np.linalg.norm(pos_b[tri_b].mean(1) - centre, axis=1) < 70)
else:
    nearb = np.ones(len(tri_b), bool)
if 'mat_names' in d.files:
    hs = [k for k, n in enumerate(d['mat_names']) if 'Hair' in str(n)]
    tri_h = d['tri'][np.isin(d['mat'], hs)]
    uv = d['uv0']
else:
    tri_h = d['tri']; uv = d['uv'][:, 0]
uv = uv.copy()
if flipv:
    uv[:, 1] = 1 - uv[:, 1]
pos_h = d['pos']; off = len(pos_b)
pos = np.concatenate([pos_b, pos_h]); tri = np.concatenate([tri_b[nearb], tri_h + off])
cols = np.concatenate([cb[nearb], np.tile([1.0, 0.86, 0.25], (len(tri_h), 1))])
UV = np.concatenate([np.zeros((len(pos_b), 2)), uv])
textured = np.r_[np.zeros(nearb.sum(), bool), np.ones(len(tri_h), bool)]
if mode == 'head':
    views = [(0, 5, 'front'), (60, 10, 'front-left'), (90, 5, 'left'), (135, 15, 'back-left'), (180, 15, 'back'), (225, 15, 'back-right'), (180, 60, 'back, from above'), (0, 70, 'from above')]
    fig, axes = plt.subplots(2, 4, figsize=(24, 13))
    for ax, (yaw, pitch, t) in zip(axes.flat, views):
        M = view_matrix(yaw, pitch); c = centre @ M.T
        img = raster_tex(pos, tri, cols, M, ((c[0] - 32, c[0] + 32), (c[1] - 42, c[1] + 26)), W=560, uv=UV, textured=textured, cov=cov, color=colr)
        ax.imshow(img); ax.set_title(t, fontsize=10); ax.axis('off')
else:
    views = [(180, 10, 'back'), (135, 10, 'back-left'), (90, 0, 'left'), (0, 0, 'front')]
    fig, axes = plt.subplots(1, 4, figsize=(28, 12))
    for ax, (yaw, pitch, t) in zip(axes, views):
        M = view_matrix(yaw, pitch); c = np.array([0, 0, 120.0]) @ M.T
        img = raster_tex(pos, tri, cols, M, ((c[0] - 110, c[0] + 110), (c[1] - 125, c[1] + 125)), W=640, uv=UV, textured=textured, cov=cov, color=colr)
        ax.imshow(img); ax.set_title(t); ax.axis('off')
plt.tight_layout(); plt.savefig(out, dpi=70)
print('wrote', out)
