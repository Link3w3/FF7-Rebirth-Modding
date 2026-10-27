"""Renders of the Bahamut head with Rebirth Sephiroth's hair laid in (bind pose): front, side, back, top-ish."""
import sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, '/work/bfs17')
from bfs_render import render

r = np.load('bfs17_rerig.npz', allow_pickle=True)
d = np.load('hair/pc00.npz', allow_pickle=True)
out = sys.argv[1] if len(sys.argv) > 1 else 'renders/hair_overlay.png'
hair_tri_mask = d['mat'] == list(d['mat_names']).index('PC0010_00_Hair')
pos_b, tri_b, tm = r['pos'], r['tri'], r['tmat']
slots = [str(s) for s in r['slots']]
cols_b = np.tile([0.55, 0.55, 0.6], (len(tri_b), 1))
for k, s in enumerate(slots):
    if s.startswith('PC0010_00') or s == 'Common_Mouth':
        cols_b[tm == k] = [0.95, 0.75, 0.65]
tri_h = d['tri'][hair_tri_mask]
pos_h = d['pos']
off = len(pos_b)
pos = np.concatenate([pos_b, pos_h])
tri = np.concatenate([tri_b, tri_h + off])
cols = np.concatenate([cols_b, np.tile([1.0, 0.85, 0.2], (len(tri_h), 1))])
views = [(0, 'front'), (90, 'side (his left)'), (180, 'back'), (270, 'side (his right)')]
fig, axes = plt.subplots(2, 4, figsize=(20, 12))
for ax, (yaw, t) in zip(axes[0], views):
    render(ax, pos, tri, cols, yaw, t + ': helmet + hair', zoom=((-45, 45), (130, 235)))
# the hair alone vs the helmet alone (the helmet: Bahamut's own slots near the head)
for ax, (yaw, t) in zip(axes[1], views):
    near = (pos_b[tri_b][:, :, 2].mean(1) > 160)
    keep = near & (cols_b[:, 0] < 0.6)
    render(ax, np.concatenate([pos_b, pos_h]), np.concatenate([tri_b[keep], tri_h + off]),
           np.concatenate([cols_b[keep], np.tile([1.0, 0.85, 0.2], (len(tri_h), 1))]), yaw, t + ': hair over the helmet (helmet drawn first)', zoom=((-45, 45), (130, 235)))
plt.tight_layout(); plt.savefig(out, dpi=80)
print('wrote', out)
