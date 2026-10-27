"""Sword swing peaks of a clip: angular speed of R_Weapon_a and the speed of a point 120 cm along the blade
(either way along X), in component space."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from clip import Clip, qmul, qconj, qrot


def swing_curve(c):
    w = c.world(['R_Weapon_a', 'Trans'])
    pos, rot = w['R_Weapon_a']
    root = w['Trans'][0]
    rel = pos - root           # the root's own travel is not a swing
    d = qmul(rot[1:], qconj(rot[:-1]))
    ang = 2 * np.arccos(np.clip(np.abs(d[:, 3]), -1, 1)) * c.fps          # rad/s
    tipA = rel + qrot(rot, np.array([[0, 0, 150.0]] * len(rot)))
    tipB = rel + qrot(rot, np.array([[0, 0, 75.0]] * len(rot)))
    va = np.linalg.norm(np.diff(tipA, axis=0), axis=1) * c.fps / 100   # m/s
    vb = np.linalg.norm(np.diff(tipB, axis=0), axis=1) * c.fps / 100
    t = (np.arange(len(ang)) + 0.5) / c.fps
    return t, ang, va, vb


def peaks(t, v, min_value, min_gap):
    out = []
    for i in range(1, len(v) - 1):
        if v[i] >= v[i - 1] and v[i] >= v[i + 1] and v[i] >= min_value:
            if out and t[i] - out[-1][0] < min_gap:
                if v[i] > out[-1][1]:
                    out[-1] = (t[i], v[i])
                continue
            out.append((t[i], v[i]))
    return out


if __name__ == '__main__':
    import glob
    files = {os.path.basename(f).split('_')[0]: f for f in glob.glob('/data/uploads/Kh2Rebirth/Remap/*.fbx')}
    for name in sys.argv[1:]:
        c = Clip.from_fbx(files[name])
        t, ang, va, vb = swing_curve(c)
        pk = peaks(t, ang, max(8.0, 0.45 * ang.max()), 0.1)
        print('%-16s %.2fs  max ang %.0f rad/s  tipA %.0f  tipB %.0f m/s  peaks: %s' % (
            name, c.seconds, ang.max(), va.max(), vb.max(), ', '.join('%.2fs(%.0f|A%.0f B%.0f)' % (tt, vv, va[np.argmin(abs(t - tt))], vb[np.argmin(abs(t - tt))]) for tt, vv in pk)))
