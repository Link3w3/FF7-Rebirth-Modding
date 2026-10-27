"""Flat-shaded renders of the Bahamut Fused Sephiroth npz (per-triangle colours)."""
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

def render(ax, pos, tri, cols, yaw_deg, title, zoom=None, joints=None, jlabels=None, maxtri=None):
    yaw = np.radians(yaw_deg)
    c, s = np.cos(yaw), np.sin(yaw)
    Rz = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    p = pos @ Rz.T
    v = p[tri]
    if zoom:
        (x0, x1), (z0, z1) = zoom
        keep = (v[:, :, 1].max(1) > x0) & (v[:, :, 1].min(1) < x1) & (v[:, :, 2].max(1) > z0) & (v[:, :, 2].min(1) < z1)
        v = v[keep]; cols = cols[keep]
    n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    light = np.array([0.6, -0.3, 0.75]); light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.abs(n @ light)
    depth = v[:, :, 0].mean(1)
    order = np.argsort(depth)
    cc = np.clip(cols * shade[:, None], 0, 1)
    pc = PolyCollection(v[order][:, :, [1, 2]], facecolors=cc[order], edgecolors='none', antialiased=False)
    ax.add_collection(pc)
    if joints is not None:
        jp = joints @ Rz.T
        ax.scatter(jp[:, 1], jp[:, 2], s=6, c='red', zorder=5)
        if jlabels is not None:
            for (x, y, z), t in zip(jp, jlabels):
                ax.text(y, z, t, fontsize=5, color='darkred', zorder=6)
    if zoom:
        ax.set_xlim(x0, x1); ax.set_ylim(z0, z1)
    else:
        ax.set_xlim(p[:, 1].min() - 5, p[:, 1].max() + 5); ax.set_ylim(p[:, 2].min() - 5, p[:, 2].max() + 5)
    ax.set_aspect('equal'); ax.set_title(title, fontsize=8); ax.axis('off')
