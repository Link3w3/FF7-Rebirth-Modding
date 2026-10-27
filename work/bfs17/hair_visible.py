"""Which hair shows around the helmet: ID-buffer renders from views around the head (coverage alpha-tested), the visible
hair triangles counted by chain and by where they are (above the mask's lower edge or below it)."""
import sys, collections
import numpy as np
sys.path.insert(0, '/work/bfs17')
from zbuf import view_matrix, raster_ids
r = np.load('bfs17_rerig.npz', allow_pickle=True)
h = np.load(sys.argv[1], allow_pickle=True)
cov = np.load('hair/tex/coverage.npy')
pos_b, tri_b, tm = r['pos'], r['tri'], r['tmat']
names = list(r['bone_names']); centre = r['bone_ct'][names.index('C_Head_a')] + [0, 0, 9]
nearb = (np.linalg.norm(pos_b[tri_b].mean(1) - centre, axis=1) < 60)
tri_h = h['tri']; pos_h = h['pos']; uv = h['uv'][:, 0].copy(); uv[:, 1] = 1 - uv[:, 1]
off = len(pos_b)
pos = np.concatenate([pos_b, pos_h]); tri = np.concatenate([tri_b[nearb], tri_h + off])
UV = np.concatenate([np.zeros((len(pos_b), 2)), uv])
nb = nearb.sum()
textured = np.r_[np.zeros(nb, bool), np.ones(len(tri_h), bool)]
chain = h['chain']
vis_tris = collections.Counter()
seen = set()
for yaw in range(0, 360, 30):
    for pitch in (-20, 5, 35, 70):
        M = view_matrix(yaw, pitch); c = centre @ M.T
        ids = raster_ids(pos, tri, M, ((c[0] - 30, c[0] + 30), (c[1] - 30, c[1] + 30)), W=300, uv=UV, textured=textured, cov=cov)
        hit = ids[ids >= nb] - nb
        for t in np.unique(hit):
            seen.add(int(t))
seen = np.array(sorted(seen))
tc = pos_h[tri_h[seen]].mean(1)
# the hair that shows in the head region (above the jaw), by chain
head = tc[:, 2] > 176
by = collections.Counter(chain[tri_h[seen[head], 0]].tolist())
print('visible hair triangles near the head: %d (above z 176: %d)' % (len(seen), head.sum()))
print('above z 176 by chain:', by.most_common())
front = head & (tc[:, 0] > centre[0] - 2)
print('above z 176 and in front of the head centre: %d' % front.sum(), collections.Counter(chain[tri_h[seen[front], 0]].tolist()).most_common())
np.save(sys.argv[2], seen[front])
