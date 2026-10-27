"""The five Dissidia NT Masamunes (item/w_sev200_00*) side by side, textured (albedo at each triangle's UV centre, lit),
seen from the flat of the blade: for choosing which of Cloud's weapon rows each one stands in for.
    dnt_weapons_sheet.py <item dir> <out png>"""
import os, sys
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import g1m, dnt_tex

NAMES = ['w_sev200_00', 'w_sev200_00_2p1c', 'w_sev200_00_3p1c', 'w_sev200_00_4p1c', 'w_sev200_00_5p1c']

def load(item, w):
    b = open(os.path.join(item, w, w + '.g1m'), 'rb').read()
    tb = open(os.path.join(item, w, w + '.g1t'), 'rb').read()
    tex = dnt_tex.entries(tb)
    G = g1m.Geometry(g1m.chunk(b, 'G1MG')[0])
    polys, cols = [], []
    for si in range(len(G.submeshes)):
        a, t = G.submesh_arrays(si)
        P = np.asarray(a[[k for k in a if 'POSITION' in str(k)][0]], float)[:, :3]
        uvk = [k for k in a if 'TEXCOORD' in str(k)]
        UV = np.asarray(a[uvk[0]], float)[:, :2] if uvk else np.zeros((len(P), 2))
        sm = G.submeshes[si]
        mi = sm['material'] if isinstance(sm, dict) else getattr(sm, 'material', 0)
        mat = G.materials[mi]
        t1 = [x['index'] for x in mat['textures'] if x['type'] == 1]
        img = dnt_tex.decode(tb, tex[t1[0]]).astype(np.float32) / 255 if t1 else None
        tri = np.asarray(t)
        v = P[tri]
        n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
        light = 0.45 + 0.55 * np.abs(n @ np.array([0.2, 0.9, 0.3]) / np.linalg.norm([0.2, 0.9, 0.3]))
        c = UV[tri].mean(1)
        if img is not None:
            h, w_ = img.shape[:2]
            x = np.clip((c[:, 0] % 1) * w_, 0, w_ - 1).astype(int); y = np.clip((c[:, 1] % 1) * h, 0, h - 1).astype(int)
            col = img[y, x, :3]
        else:
            col = np.full((len(tri), 3), 0.6)
        depth = v[:, :, 1].mean(1)
        order = np.argsort(depth)
        polys += [v[k][:, [0, 2]] for k in order]
        cols += [np.clip(col[k] * light[k], 0, 1) for k in order]
    return polys, cols

def main(item, out):
    fig, axes = plt.subplots(len(NAMES), 1, figsize=(16, 2.2 * len(NAMES)))
    for ax, w in zip(axes, NAMES):
        polys, cols = load(item, w)
        ax.add_collection(PolyCollection(polys, facecolors=cols, edgecolors='none'))
        ax.set_xlim(-60, 360); ax.set_ylim(-40, 40); ax.set_aspect('equal'); ax.axis('off')
        ax.set_title(w, loc='left', fontsize=11)
    fig.tight_layout(); fig.savefig(out, dpi=80, facecolor='white')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
