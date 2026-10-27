"""KH2_1017_Run.cacanim: his KH2 run loop (1017, in place) moving him forward at Cloud's battle run speed (7 m/s:
B_Run01_1 travels 373 cm in 0.53 s), the root as the game's animations carry it (make_keys.root_track)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import make_keys as K
from kh2raw import Anim

SPEED = 700.0   # cm/s


class Moving:
    """1017 with root travel added (before make_keys turns the travel from +Y to +X: added on +Y here)"""
    def __init__(self, a, speed):
        self.name, self.frames, self.length = a.name + '_Run', a.frames, a.length
        self.tracks = dict(a.tracks)
        pos, rot, scl = a.tracks['kh_sk']
        P = np.repeat(pos, a.frames, 0) if len(pos) == 1 else pos.copy()
        t = np.arange(a.frames) / K.FPS
        P[:, 1] += speed * t
        self.tracks['kh_sk'] = (P, rot, scl)

    def local(self, track, frame):
        pos, rot, scl = self.tracks[track]
        return rot[min(frame, len(rot) - 1)], pos[min(frame, len(pos) - 1)]


if __name__ == '__main__':
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    m = Moving(Anim('1017'), SPEED)
    path = os.path.join(out, 'KH2_1017_Run.cacanim')
    k = K.write(m, path, loop=True)
    fps, frames, flags, back = K.read_back(path)
    root = back['kh_sk']
    print(path, frames, 'frames', fps, 'fps, flags', flags, k, 'tracks; root', root[0, :3], '->', root[-1, :3], 'q', root[0, 3:7])
    print('speed %.1f cm/s' % ((root[-1, 0] - root[0, 0]) / ((frames - 1) / fps)))
