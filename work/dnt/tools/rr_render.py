"""Renders a re-rigged (Unreal space) npz with dnt_render: front, side, back. rr_render.py <npz> <texdir> <out> [yaw...]"""
import sys, json, numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
import dnt_render as R
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
m = dict(np.load(sys.argv[1]))
p = m['pos']
m['pos'] = np.stack([-p[:, 1], p[:, 2], p[:, 0]], 1)
texs = R.albedo_lookup(m, sys.argv[2])
yaws = [float(x) for x in sys.argv[4:]] or [0, 90, 180]
fig, axs = plt.subplots(1, len(yaws), figsize=(6 * len(yaws), 9))
for ax, y in zip(np.atleast_1d(axs), yaws):
    R.render(ax, m, texs, y, 'yaw %g' % y)
plt.tight_layout(); plt.savefig(sys.argv[3], dpi=60, facecolor=(0.85, 0.85, 0.85))
