"""Quick textured previews of a dnt_model.py npz (or any npz with pos/tri/tmat/uv): painter's-order triangles coloured by
each material's albedo (type 1 texture) at the triangle's UV centroid, lit by a fixed light. Y up, Z forward.
    dnt_render.py <model npz> <texture dir with tNN.png> <out png> [yaw degrees ...]"""
import json
import sys

import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection


def albedo_lookup(m, texdir):
    mats = [json.loads(s) for s in m['materials']]
    texs = []
    for mt in mats:
        t1 = [t['index'] for t in mt['textures'] if t['type'] == 1]
        img = None
        if t1:
            try:
                img = np.asarray(Image.open('%s/t%02d.png' % (texdir, t1[0])).convert('RGBA')).astype(np.float32) / 255
            except OSError:
                img = None
        texs.append(img)
    return texs


def render(ax, m, texs, yaw, title, pos=None, hide=()):
    pos = m['pos'] if pos is None else pos
    tri, tmat, uv = m['tri'], m['tmat'], m['uv']
    keep = ~np.isin(tmat, list(hide))
    tri, tmat = tri[keep], tmat[keep]
    c, s = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])      # turn about Y
    p = pos @ R.T
    v = p[tri]
    n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    L = np.array([0.4, 0.5, 0.75]); L /= np.linalg.norm(L)
    shade = 0.45 + 0.55 * np.abs(n @ L)
    cuv = uv[tri].mean(1)
    col = np.zeros((len(tri), 4)); col[:, 3] = 1
    for k, img in enumerate(texs):
        sel = tmat == k
        if not sel.any():
            continue
        if img is None:
            col[sel, :3] = 0.6
            continue
        h, w = img.shape[:2]
        x = np.clip((cuv[sel, 0] % 1) * w, 0, w - 1).astype(int)
        y = np.clip((cuv[sel, 1] % 1) * h, 0, h - 1).astype(int)
        col[sel] = img[y, x]
    a = col[:, 3]
    col[:, :3] *= shade[:, None]
    order = np.argsort(v[:, :, 2].mean(1))        # far (small z) first: the camera looks down -Z
    draw = order[a[order] > 0.25]
    pc = PolyCollection(v[draw][:, :, :2], facecolors=np.clip(col[draw, :3], 0, 1), edgecolors='none',
                        antialiased=False)
    ax.add_collection(pc)
    ax.set_xlim(p[:, 0].min() - 5, p[:, 0].max() + 5); ax.set_ylim(p[:, 1].min() - 5, p[:, 1].max() + 5)
    ax.set_aspect('equal'); ax.set_title(title, fontsize=9); ax.axis('off')
    ax.set_facecolor((0.85, 0.85, 0.85))


def main():
    m = np.load(sys.argv[1])
    texs = albedo_lookup(m, sys.argv[2])
    yaws = [float(x) for x in sys.argv[4:]] or [0, 90, 180]
    fig, axs = plt.subplots(1, len(yaws), figsize=(6 * len(yaws), 9))
    for ax, y in zip(np.atleast_1d(axs), yaws):
        render(ax, m, texs, y, 'yaw %g' % y)
    plt.tight_layout()
    plt.savefig(sys.argv[3], dpi=70, facecolor=(0.85, 0.85, 0.85))


if __name__ == '__main__':
    main()
