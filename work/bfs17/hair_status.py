import sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, '/work/bfs17')
from bfs_render import render
from helmet_map import lookup
r = np.load('bfs17_rerig.npz', allow_pickle=True)
d = np.load('hair/pc00.npz', allow_pickle=True)
hm = np.load('hair/helmet_map.npz')
depth, centre, res = hm['depth'], hm['centre'], float(hm['res'])
H = list(d['mat_names']).index('PC0010_00_Hair')
tri_h = d['tri'][d['mat'] == H]
pos_h = d['pos']
rr, dd, it, ip = lookup(depth, centre, pos_h, res)
inside = rr < dd
covered = np.isfinite(dd)
st = np.where(inside, 0, np.where(covered, 1, 2))      # 0 inside, 1 through the helmet, 2 open direction
hv = np.unique(tri_h)
import collections
print('hair verts', len(hv), collections.Counter(st[hv].tolist()))
# where are the through ones
th = hv[st[hv] == 1]
print('through: z range %.1f..%.1f, x %.1f..%.1f, depth over %.2f (median) max %.2f' % (pos_h[th, 2].min(), pos_h[th, 2].max(), pos_h[th, 0].min(), pos_h[th, 0].max(), np.median(rr[th] - dd[th]), (rr[th] - dd[th]).max()))
# head skin vs helmet
Hd = list(d['mat_names']).index('PC0010_00_Head')
hv2 = np.unique(d['tri'][d['mat'] == Hd])
r2, d2, _, _ = lookup(depth, centre, pos_h[hv2], res)
print('Rebirth head skin verts through the helmet: %d of %d (max %.2f cm)' % (((r2 > d2) & np.isfinite(d2)).sum(), len(hv2), np.nanmax(np.where(np.isfinite(d2), r2 - d2, np.nan))))
# render: helmet (Bahamut own, near head) + hair coloured by status (triangle = worst vertex)
pos_b, tri_b, tm = r['pos'], r['tri'], r['tmat']
slots = [str(s) for s in r['slots']]
face = np.array([s.startswith('PC0010_00') or s == 'Common_Mouth' for s in slots])
nearb = (np.linalg.norm(pos_b[tri_b].mean(1) - centre, axis=1) < 40)
cb = np.tile([0.55, 0.55, 0.6], (len(tri_b), 1)); cb[face[tm]] = [0.95, 0.75, 0.65]
ts = st[tri_h].max(1)
pal = np.array([[1.0, 0.85, 0.2], [0.9, 0.1, 0.1], [0.2, 0.75, 0.3]])
ch = pal[ts]
off = len(pos_b)
fig, axes = plt.subplots(2, 4, figsize=(20, 11))
views = [(0, 'front'), (90, 'his left'), (180, 'back'), (270, 'his right')]
for ax, (yaw, t) in zip(axes[0], views):
    render(ax, np.concatenate([pos_b, pos_h]), np.concatenate([tri_b[nearb], tri_h + off]), np.concatenate([cb[nearb], ch]), yaw,
           t + ': red = hair through the helmet, green = open', zoom=((-30, 30), (165, 225)))
for ax, (yaw, t) in zip(axes[1], views):
    render(ax, pos_h, tri_h, ch, yaw, t + ': the hair alone', zoom=((-30, 30), (150, 225)))
plt.tight_layout(); plt.savefig('renders/hair_status.png', dpi=80)
