"""World-space bone transforms per frame for the retargeted KH2 FBXs (UE space)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fbxbin import Scene, props70
from xform import quat_from_euler_xyz_deg, qmul, qrot, to_ue
import numpy as np


class Anim:
    def __init__(self, path):
        s = Scene(path)
        self.scene = s
        self.curves = s.curves()
        self.fps = s.settings.get('CustomFrameRate', [30.0])[0]
        n = 1
        for c in self.curves.values():
            for ch in c.values():
                for comp in ch.values():
                    n = max(n, len(comp[0]))
        self.n = n
        ms = s.models()
        self.byname = {v[1]: k for k, v in ms.items()}
        self.parent = {}
        for k, v in ms.items():
            p = s.parent.get(k)
            self.parent[v[1]] = ms[p][1] if p and p in ms else None
        self.defaults = {name: props70(ms[k][3]) for name, k in self.byname.items()}
        self._local, self._world = {}, {}

    def chan(self, bone, channel, default=(0.0, 0.0, 0.0)):
        n = self.n
        out = np.zeros((n, 3))
        c = self.curves.get(bone, {}).get(channel)
        d = self.defaults[bone].get(channel, list(default))
        for i, a in enumerate('XYZ'):
            if c and ('d|' + a) in c:
                vals = list(c['d|' + a][1])
                vals = vals + [vals[-1]] * max(0, n - len(vals))
                out[:, i] = vals[:n]
            else:
                out[:, i] = d[i] if i < len(d) else default[i]
        return out

    def local(self, bone):
        if bone not in self._local:
            T, R = self.chan(bone, 'Lcl Translation'), self.chan(bone, 'Lcl Rotation')
            self._local[bone] = [to_ue(tuple(T[f]), quat_from_euler_xyz_deg(*R[f])) for f in range(self.n)]
        return self._local[bone]

    def world(self, bone):
        if bone in self._world:
            return self._world[bone]
        loc = self.local(bone)
        p = self.parent.get(bone)
        if p is None or p == 'Armature':
            res = loc
        else:
            res = []
            for (pt, pq), (lt, lq) in zip(self.world(p), loc):
                t = qrot(pq, lt)
                res.append(((pt[0] + t[0], pt[1] + t[1], pt[2] + t[2]), qmul(pq, lq)))
        self._world[bone] = res
        return res

    def pos(self, bone):
        return np.array([t for t, q in self.world(bone)])

    def axis(self, bone, v):
        return np.array([qrot(q, v) for t, q in self.world(bone)])
