import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from kh2raw import Anim
import fk
from render_kh2 import positions

FPS = 60.0


def features(name):
    a = Anim(name)
    Ps = positions(a)
    root = np.array([P['kh_sk'] for P in Ps])
    tip = np.array([P['blade_tip'] for P in Ps]) - root
    hand = np.array([P['R_te'] for P in Ps]) - root
    feet = np.array([[P['L_ashi1'][2], P['R_ashi1'][2]] for P in Ps]) - root[:, 2:3]
    hips = np.array([P['center'] for P in Ps]) - root
    v = np.linalg.norm(np.diff(tip, axis=0), axis=1) * FPS / 100.0     # m/s
    # swing peaks: local maxima of tip speed above 6 m/s, at least 5 frames apart
    peaks = []
    for i in range(1, len(v) - 1):
        if v[i] >= v[i - 1] and v[i] >= v[i + 1] and v[i] > 6.0:
            if peaks and i - peaks[-1] < 5:
                if v[i] > v[peaks[-1]]:
                    peaks[-1] = i
                continue
            peaks.append(i)
    return dict(name=name, frames=a.frames, seconds=round((a.frames - 1) / FPS, 2), travel=np.round(root[-1] - root[0]).tolist(),
                max_fwd=round(float(root[:, 0].max() - root[0, 0])), min_fwd=round(float(root[:, 0].min() - root[0, 0])),
                feet_min=round(float(feet.min()), 1), feet_max=round(float(feet.min(axis=1).max()), 1),
                hips_z=[round(float(hips[:, 2].min())), round(float(hips[:, 2].max()))],
                peaks=[(round((p + 0.5) / FPS, 2), round(float(v[p]), 1)) for p in peaks], vmax=round(float(v.max()), 1))


if __name__ == '__main__':
    for n in sys.argv[1:]:
        f = features(n)
        print('%-14s %3d f %5.2fs travel %-22s fwd[%5d,%5d] feet[%6.1f,%6.1f] hips %-10s swings %s' % (
            f['name'], f['frames'], f['seconds'], f['travel'], f['min_fwd'], f['max_fwd'], f['feet_min'], f['feet_max'], f['hips_z'], f['peaks']))
