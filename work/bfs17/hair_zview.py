import sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, '/work/bfs17')
from zbuf import view_matrix, raster
r = np.load('bfs17_rerig.npz', allow_pickle=True)
d = np.load(sys.argv[1] if len(sys.argv) > 1 else 'hair/pc00.npz', allow_pickle=True)
out = sys.argv[2] if len(sys.argv) > 2 else 'renders/hair_z.png'
pos_b, tri_b, tm = r['pos'], r['tri'], r['tmat']
slots = [str(s) for s in r['slots']]
face = np.array([s.startswith('PC0010_00') or s == 'Common_Mouth' for s in slots])
names = list(r['bone_names']); centre = r['bone_ct'][names.index('C_Head_a')] + [0, 0, 9]
nearb = (np.linalg.norm(pos_b[tri_b].mean(1) - centre, axis=1) < 70)
cb = np.tile([0.6, 0.6, 0.66], (len(tri_b), 1)); cb[face[tm]] = [0.95, 0.65, 0.55]
if 'mat_names' in d.files:
    hs = [k for k, n in enumerate(d['mat_names']) if 'Hair' in str(n)]; tri_h = d['tri'][np.isin(d['mat'], hs)]
else:
    tri_h = d['tri']
pos_h = d['pos']
off = len(pos_b)
pos = np.concatenate([pos_b, pos_h]); tri = np.concatenate([tri_b[nearb], tri_h + off])
cols = np.concatenate([cb[nearb], np.tile([1.0, 0.86, 0.25], (len(tri_h), 1))])
views = [(0, 5, 'front'), (60, 10, 'front-left'), (90, 5, 'left'), (135, 15, 'back-left'), (180, 15, 'back'), (225, 15, 'back-right'), (180, 60, 'back, from above'), (0, 70, 'from above')]
fig, axes = plt.subplots(2, 4, figsize=(24, 13))
for ax, (yaw, pitch, t) in zip(axes.flat, views):
    M = view_matrix(yaw, pitch)
    c = centre @ M.T
    img = raster(pos, tri, cols, M, ((c[0] - 32, c[0] + 32), (c[1] - 42, c[1] + 26)), W=560)
    ax.imshow(img); ax.set_title(t, fontsize=10); ax.axis('off')
plt.tight_layout(); plt.savefig(out, dpi=70)
print('wrote', out)
