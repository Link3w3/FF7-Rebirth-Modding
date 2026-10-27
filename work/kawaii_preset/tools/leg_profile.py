"""The legs' surface around their bones (thigh: UpperLeg -> Foreleg, calf: Foreleg -> Foot) from a mesh section in the
reference pose: per place along the bone (t = 0 at the joint, 1 at the next) the largest / the 90 % distance of its
vertices from the bone's axis, over 16 directions round it."""
import json, sys
import numpy as np


def profile(P, a, b, bins=10, maxr=25.0, side=None):
    a, b = np.array(a), np.array(b)
    d = b - a
    L = np.linalg.norm(d)
    u = d / L
    rel = P - a
    t = rel @ u / L
    radial = rel - np.outer(rel @ u, u)
    r = np.linalg.norm(radial, axis=1)
    ok = (t >= 0) & (t <= 1) & (r < maxr)
    if side is not None:
        ok &= side(P)
    out = []
    for k in range(bins):
        m = ok & (t >= k / bins) & (t < (k + 1) / bins)
        if m.sum() < 10:
            out.append((k, int(m.sum()), None, None, None))
            continue
        rr = r[m]
        out.append((k, int(m.sum()), float(np.percentile(rr, 50)), float(np.percentile(rr, 90)), float(rr.max())))
    return L, out


if __name__ == '__main__':
    npz, rig_path, section = sys.argv[1:4]
    A = np.load(npz)
    names = [str(n) for n in A['names']]
    base, nt, vb, nv = [int(v) for v in A['secs'][names.index(section)]]
    P = A['pos'][vb:vb + nv]
    rig = {b['name']: b for b in json.load(open(rig_path))['bones']}
    for side in 'LR':
        s = (lambda Q: Q[:, 1] < -1.0) if side == 'L' else (lambda Q: Q[:, 1] > 1.0)
        for name, (x, y) in (('thigh', ('_UpperLeg_a', '_Foreleg_a')), ('calf', ('_Foreleg_a', '_Foot_a'))):
            L, out = profile(P, rig[side + x]['t'], rig[side + y]['t'], side=s)
            print('%s %-5s %.1f cm: ' % (side, name, L) + '  '.join('%d:%s' % (k, ('%.1f/%.1f/%.1f' % (m50, m90, mx)) if m50 else '-') for k, n, m50, m90, mx in out))
