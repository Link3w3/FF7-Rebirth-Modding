"""Flat-shaded triangle renders (painter's order) of a mesh from a few angles."""
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

PAL = np.array([[0.75, 0.75, 0.8], [0.85, 0.85, 0.9], [0.8, 0.4, 0.4], [0.95, 0.8, 0.7], [0.3, 0.3, 0.35], [0.25, 0.25, 0.28],
                [0.95, 0.82, 0.72], [0.1, 0.1, 0.1], [0.35, 0.35, 0.4], [0.5, 0.5, 0.6]])

def render(ax, pos, tri, tmat, yaw_deg, title, zoom=None, joints=None):
    yaw = np.radians(yaw_deg)
    # view: camera looking along -X' after turning the model by yaw about Z; screen x = Y', screen y = Z
    c, s = np.cos(yaw), np.sin(yaw)
    Rz = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    p = pos @ Rz.T
    v = p[tri]
    n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    light = np.array([0.6, -0.3, 0.75]); light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.abs(n @ light)
    depth = v[:, :, 0].mean(1)
    order = np.argsort(depth)        # far (small x) first: the camera sits at +x
    cols = PAL[tmat % len(PAL)] * shade[:, None]
    polys = v[order][:, :, [1, 2]]
    pc = PolyCollection(polys, facecolors=np.clip(cols[order], 0, 1), edgecolors='none', antialiased=False)
    ax.add_collection(pc)
    if joints is not None:
        jp = joints @ Rz.T
        ax.scatter(jp[:, 1], jp[:, 2], s=3, c='red', zorder=5)
    if zoom:
        (x0, x1), (z0, z1) = zoom
        ax.set_xlim(x0, x1); ax.set_ylim(z0, z1)
    else:
        ax.set_xlim(p[:, 1].min() - 5, p[:, 1].max() + 5); ax.set_ylim(p[:, 2].min() - 5, p[:, 2].max() + 5)
    ax.set_aspect('equal'); ax.set_title(title, fontsize=8); ax.axis('off')
