"""Forward kinematics for Sora's skeleton (the cooked, flattened one: sora_skeleton_now.json) with KH2 anim tracks."""
import json
import numpy as np

SK = json.load(open('/work/sorakh2/sora_skeleton_now.json'))
NAMES = [b[0] for b in SK]
PARENTS = [b[1] for b in SK]
REF_T = np.array([b[2] for b in SK])
REF_Q = np.array([b[3] for b in SK])
INDEX = {n: i for i, n in enumerate(NAMES)}


def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return np.array([aw * bx + ax * bw + ay * bz - az * by,
                     aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz])


def qrot(q, v):
    x, y, z, w = q
    u = np.array([x, y, z])
    return v + 2.0 * np.cross(u, np.cross(u, v) + w * v)


def pose(anim, frame, ref_for_missing=True):
    """component-space (q, t) per bone"""
    n = len(NAMES)
    CQ = np.zeros((n, 4)); CT = np.zeros((n, 3))
    for i in range(n):
        name = NAMES[i]
        if name in anim.tracks:
            q, t = anim.local(name, frame)
        else:
            q, t = REF_Q[i], REF_T[i]
        q = q / np.linalg.norm(q)
        p = PARENTS[i]
        if p < 0:
            CQ[i], CT[i] = q, t
        else:
            CQ[i] = qmul(CQ[p], q)
            CT[i] = CT[p] + qrot(CQ[p], t)
    return CQ, CT


def ref_pose():
    class R: tracks = {}
    return pose(R, 0)


def pose_flat_root(anim, frame):
    """as the game shows it: the root's animated rotation left out (the game consumes it), its translation kept"""
    class Wrap:
        pass
    w = Wrap()
    w.tracks = dict(anim.tracks)
    pos, rot, scl = anim.tracks['kh_sk']
    w.tracks['kh_sk'] = (pos, np.array([[0.0, 0.0, 0.0, 1.0]]), scl)
    w.local = lambda track, f: (lambda p, r: (r[min(f, len(r) - 1)], p[min(f, len(p) - 1)]))(w.tracks[track][0], w.tracks[track][1])
    return pose(w, frame)
