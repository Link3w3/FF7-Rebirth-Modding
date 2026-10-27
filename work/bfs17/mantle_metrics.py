"""How heavy his mantles look in an offline run (anim_run's frames, component space; the floor at z 0): the long strips'
train (their bones past the knee, ~z 30 at rest) - how much of it lies on the floor (below 4 cm), how high it is on
average and at most (90th percentile); how far the strips' tips trail behind his hips and how much they swing (their
spread over the run, in the hips' frame); the shoulder strips' swing; NaN.
    mantle_metrics.py rig.json frames.bin [label]"""
import json, re, sys
import numpy as np


def qrot(q, v):
    qv = q[..., :3]; t = 2.0 * np.cross(qv, v)
    return v + q[..., 3:4] * t + np.cross(qv, t)


def qinv(q):
    return np.concatenate([-q[..., :3], q[..., 3:4]], axis=-1)


rig = json.load(open(sys.argv[1]))
frames = sys.argv[2]
label = sys.argv[3] if len(sys.argv) > 3 else frames
names = [b['name'] for b in rig['bones']]
index = {n: i for i, n in enumerate(names)}
reft = np.array([b['t'] for b in rig['bones']])
raw = np.fromfile(frames, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
start = int(nf / 7.0 * 1.5)          # (the first second stands still; half a second more to settle into the clip)
Q, T = F[start:, :, :4], F[start:, :, 4:]
hip = index['C_Hip_a']


def strip(side, c):
    out = [n for n in names if re.match(r'^%s_%s\d+$' % (side, c), n)]
    return sorted(out, key=lambda n: int(re.findall(r'\d+$', n)[0]))


train, tips, shoulder_tips = [], [], []
for s in 'LR':
    for c in ('MantLgA', 'MantLgB', 'MantLgD', 'MantLgE'):
        bones = strip(s, c)
        train += [index[n] for n in bones if reft[index[n]][2] < 32]
        if bones:
            tips.append(index[bones[-1]])
    for c in ('MantSmA', 'MantSmB', 'MantSmC', 'MantSmD'):
        bones = strip(s, c)
        if bones:
            shoulder_tips.append(index[bones[-1]])
z = T[:, train, 2]
lying = z < reft[train, 2][None, :] + 3.0          # (at rest the train lies on the floor at its collision radius)
rel = T[:, tips] - T[:, hip][:, None, :]          # tips from the hips, component space (+X his front, +Z up)
sh = T[:, shoulder_tips] - T[:, hip][:, None, :]
rest_rel = reft[tips] - reft[hip]
print('%-24s NaN %s | train lying %4.1f%%, height mean %5.1f cm, p90 %5.1f, max %5.1f | tips behind the hips %5.1f cm (rest %5.1f), '
      'tip height %5.1f cm (rest %4.1f), spread %4.1f cm | shoulder spread %4.1f cm' % (
          label, bool(np.isnan(F).any()), 100 * lying.mean(), z.mean(), np.percentile(z, 90), z.max(),
          -rel[..., 0].mean(), -rest_rel[:, 0].mean(), T[:, tips, 2].mean(), reft[tips, 2].mean(),
          np.linalg.norm(rel - rel.mean(0), axis=-1).mean(), np.linalg.norm(sh - sh.mean(0), axis=-1).mean()))
