import sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, '/work/bfs17')
from zbuf import view_matrix, raster_tex
r = np.load('bfs17_rerig.npz', allow_pickle=True)
d = np.load(sys.argv[1], allow_pickle=True)
cov = np.load('hair/tex/coverage.npy'); colr = np.clip(np.load('hair/tex/color_srgb.npy') * 1.6, 0, 1)
pos_b, tri_b, tm = r['pos'], r['tri'], r['tmat']
slots = [str(s) for s in r['slots']]
face = np.array([s.startswith('PC0010_00') or s == 'Common_Mouth' for s in slots])
names = list(r['bone_names']); centre = r['bone_ct'][names.index('C_Head_a')] + [0, 0, 2]
cb = np.tile([0.62, 0.63, 0.68], (len(tri_b), 1)); cb[face[tm]] = [0.95, 0.72, 0.62]
nearb = (np.linalg.norm(pos_b[tri_b].mean(1) - centre, axis=1) < 90)
uv = d['uv'][:, 0].copy(); uv[:, 1] = 1 - uv[:, 1]
off = len(pos_b)
pos = np.concatenate([pos_b, d['pos']]); tri = np.concatenate([tri_b[nearb], d['tri'] + off])
cols = np.concatenate([cb[nearb], np.zeros((len(d['tri']), 3))])
UV = np.concatenate([np.zeros((len(pos_b), 2)), uv])
textured = np.r_[np.zeros(nearb.sum(), bool), np.ones(len(d['tri']), bool)]
fig, axes = plt.subplots(1, 3, figsize=(27, 11))
for ax, (yaw, pitch, t, box) in zip(axes, [(0, -8, 'front', (22, 30, 14)), (30, -5, 'front, a little to his left', (24, 32, 14)), (165, 12, 'back', (40, 75, 25))]):
    M = view_matrix(yaw, pitch); c = centre @ M.T
    img = raster_tex(pos, tri, cols, M, ((c[0] - box[0], c[0] + box[0]), (c[1] - box[1], c[1] + box[2])), W=900, uv=UV, textured=textured, cov=cov, color=colr)
    ax.imshow(img); ax.set_title(t, fontsize=12); ax.axis('off')
plt.tight_layout(); plt.savefig(sys.argv[2], dpi=60)
print('wrote', sys.argv[2])
