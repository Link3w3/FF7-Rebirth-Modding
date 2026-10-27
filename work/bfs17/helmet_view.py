import sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, '/work/bfs17')
from bfs_render import render
r = np.load('bfs17_rerig.npz', allow_pickle=True)
pos_b, tri_b, tm = r['pos'], r['tri'], r['tmat']
slots = [str(s) for s in r['slots']]
face = np.array([s.startswith('PC0010_00') or s == 'Common_Mouth' for s in slots])
names = list(r['bone_names']); centre = r['bone_ct'][names.index('C_Head_a')] + [0, 0, 9]
nearb = (np.linalg.norm(pos_b[tri_b].mean(1) - centre, axis=1) < 35)
cb = np.tile([0.55, 0.55, 0.6], (len(tri_b), 1)); cb[face[tm]] = [0.95, 0.6, 0.5]
fig, axes = plt.subplots(2, 4, figsize=(20, 11))
views = [(0, 'front'), (90, 'his left'), (180, 'back'), (270, 'his right'), (135, 'back-left'), (225, 'back-right'), (45, 'front-left'), (315, 'front-right')]
for ax, (yaw, t) in zip(axes.flat, views):
    render(ax, pos_b, tri_b[nearb], cb[nearb], yaw, t + ': helmet (grey) and Rebirth head (pink)', zoom=((-30, 30), (165, 225)))
plt.tight_layout(); plt.savefig('renders/helmet_only.png', dpi=80)
# top view: look down (rotate so z -> depth): swap axes
fig, ax = plt.subplots(1, 2, figsize=(14, 7))
P = pos_b.copy()
for a, (sign, t) in zip(ax, [(1, 'from above (front up)'), (-1, 'from below')]):
    Q = np.stack([sign * P[:, 2], P[:, 1], P[:, 0]], 1)   # depth = z, screen = (y, x)
    render(a, Q, tri_b[nearb], cb[nearb], 0, t, zoom=((-30, 30), (-25, 35)))
plt.tight_layout(); plt.savefig('renders/helmet_top.png', dpi=80)
