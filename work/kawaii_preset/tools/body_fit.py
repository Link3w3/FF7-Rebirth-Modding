"""Body collider sizes from a skinned mesh in its reference pose (body npz + rig): for a bone segment (a -> b), the
distances of the vertices skinned mostly to the given bones from the segment's axis, per tenth along it (percentiles),
optionally only those on one side (a direction)."""
import json, re
import numpy as np


class Body:
    def __init__(self, npz, rig_path=None, rig=None):
        d = np.load(npz, allow_pickle=True)
        self.pos = d['pos']
        self.names = [str(n) for n in d['bones']]
        n = len(self.pos)
        self.dom = np.zeros(n, dtype=np.int64)
        best = np.zeros(n)
        for b, v, w in zip(d['w_bone'], d['w_vert'], d['w_weight']):
            if w > best[v]:
                best[v] = w
                self.dom[v] = b
        self.domname = np.array(self.names)[self.dom]
        self.rig = rig if rig is not None else {b['name']: b for b in json.load(open(rig_path))['bones']}

    def verts(self, pattern):
        rx = re.compile(pattern)
        return np.array([rx.search(n) is not None for n in self.domname])

    def segment(self, a, b, mask, bins=10, toward=None, pcts=(50, 80, 90, 95)):
        A = np.array(self.rig[a]['t'])
        B = np.array(self.rig[b]['t'])
        d = B - A
        L = np.linalg.norm(d)
        u = d / L
        rel = self.pos - A
        t = rel @ u / L
        radial = rel - np.outer(rel @ u, u)
        r = np.linalg.norm(radial, axis=1)
        ok = mask & (t >= 0) & (t <= 1)
        if toward is not None:
            w = np.array(toward, dtype=float)
            w = w - (w @ u) * u
            w /= np.linalg.norm(w)
            ok &= (radial @ w) > 0.3 * r
        out = []
        for k in range(bins):
            m = ok & (t >= k / bins) & (t < (k + 1) / bins)
            if m.sum() < 5:
                out.append(None)
                continue
            out.append([float(np.percentile(r[m], p)) for p in pcts])
        return L, out
