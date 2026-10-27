"""The Bahamut with his FFXV textures on (a check of which texture set and which UV each material uses).
    tex_view.py <npz> <out.png> <uv channel> <flipv 0|1> <body tex> <mantle tex> <wings tex> [views]"""
import sys
import numpy as np
from PIL import Image
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, '/work/bfs17')
from zbuf import view_matrix, raster_multi
m = np.load(sys.argv[1], allow_pickle=True)
out, ch, flip = sys.argv[2], int(sys.argv[3]), sys.argv[4] == '1'
T = '/data/uploads/FF7R2UProj/Saved/ModExtract/bfs17/ffxvtex/thumbs/'
texs = [np.asarray(Image.open(T + f + '.png').convert('RGB')).astype(np.float64) / 255.0 for f in sys.argv[5:8]]
views = sys.argv[8] if len(sys.argv) > 8 else 'full'
slots = [str(s) for s in m['slots']]
tm = m['tmat']; tri = m['tri']; pos = m['pos']
uv = m['uv'][:, ch].copy()
if flip:
    uv[:, 1] = 1 - uv[:, 1]
tex_of = np.full(len(tri), -1)
for k, nm in enumerate(('PC0010_17_Body_Inst', 'PC0010_17_Mantle_Inst', 'PC0010_17_BladeWings_Inst')):
    tex_of[tm == slots.index(nm)] = k
flat = np.tile([0.9, 0.75, 0.65], (len(tri), 1))
for k, s in enumerate(slots):
    if 'Hair' in s:
        flat[tm == k] = [0.95, 0.95, 0.9]
if views == 'full':
    V = [(0, 0, 'front', (0, 0, 120), (110, 125, 125)), (180, 10, 'back', (0, 0, 120), (110, 125, 125)), (90, 0, 'left', (0, 0, 120), (110, 125, 125))]
else:
    V = [(0, 5, 'front', (2.6, 0, 185), (32, 42, 26)), (90, 5, 'left', (2.6, 0, 185), (32, 42, 26)), (180, 15, 'back', (2.6, 0, 185), (32, 42, 26))]
fig, axes = plt.subplots(1, len(V), figsize=(9 * len(V), 11))
for ax, (yaw, pitch, t, ctr, b) in zip(axes, V):
    M = view_matrix(yaw, pitch); c = np.array(ctr, float) @ M.T
    img = raster_multi(pos, tri, M, ((c[0] - b[0], c[0] + b[0]), (c[1] - b[1], c[1] + b[2])), 520, uv, tex_of, texs, flat)
    ax.imshow(img); ax.set_title(t); ax.axis('off')
plt.tight_layout(); plt.savefig(out, dpi=60)
print('wrote', out)
