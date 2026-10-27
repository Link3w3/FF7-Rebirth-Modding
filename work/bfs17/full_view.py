import sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, '/work/bfs17')
from zbuf import view_matrix, raster
r = np.load('bfs17_rerig.npz', allow_pickle=True)
d = np.load(sys.argv[1], allow_pickle=True)
out = sys.argv[2]
pos_b, tri_b, tm = r['pos'], r['tri'], r['tmat']
slots = [str(s) for s in r['slots']]
pal = {'PC0010_17_Body_Inst': [0.6, 0.6, 0.66], 'PC0010_17_Mantle_Inst': [0.45, 0.5, 0.7], 'PC0010_17_BladeWings_Inst': [0.7, 0.55, 0.5]}
cb = np.tile([0.95, 0.65, 0.55], (len(tri_b), 1))
for k, s in enumerate(slots):
    if not (s.startswith('PC0010_00') or s == 'Common_Mouth'):
        cb[tm == k] = [0.6, 0.6, 0.66]
if 'mat_names' in d.files:
    hs = [k for k, n in enumerate(d['mat_names']) if 'Hair' in str(n)]; tri_h = d['tri'][np.isin(d['mat'], hs)]
else:
    tri_h = d['tri']
pos_h = d['pos']; off = len(pos_b)
pos = np.concatenate([pos_b, pos_h]); tri = np.concatenate([tri_b, tri_h + off])
cols = np.concatenate([cb, np.tile([1.0, 0.86, 0.25], (len(tri_h), 1))])
views = [(180, 10, 'back'), (135, 10, 'back-left'), (90, 0, 'left'), (0, 0, 'front')]
fig, axes = plt.subplots(1, 4, figsize=(28, 12))
for ax, (yaw, pitch, t) in zip(axes, views):
    M = view_matrix(yaw, pitch)
    c = np.array([0, 0, 120.0]) @ M.T
    img = raster(pos, tri, cols, M, ((c[0] - 110, c[0] + 110), (c[1] - 125, c[1] + 125)), W=520)
    ax.imshow(img); ax.set_title(t); ax.axis('off')
plt.tight_layout(); plt.savefig(out, dpi=60)
