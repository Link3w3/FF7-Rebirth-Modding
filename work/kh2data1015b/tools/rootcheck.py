"""Root check of the built moves in a SephirothForms_P container: frame-0 Trans rotation (the game's is q0 =
(-0.5, 0.5, -0.5, 0.5) times a yaw), root travel and facing, next to the game's own animation of the same name."""
import sys
sys.path[:0] = ['/work/runfix1015', '/work/acl', '/work/iostore']
import numpy as np, pose
from iostore import Toc
from rootcmp import info
Q0 = np.array([-0.5, 0.5, -0.5, 0.5])
def yaw_free(q):
    """the Trans rotation with its yaw taken out (q = R_yaw * q0 -> q0): angle (deg) between q*conj(q0)'s axis and Z"""
    c = pose.qmul(q, np.array([0.5, -0.5, 0.5, 0.5]))   # q * conj(q0)
    c = c / np.linalg.norm(c)
    # a pure yaw has x = y = 0
    return np.degrees(2 * np.arcsin(min(1.0, np.linalg.norm(c[:2]))))
def row(label, data):
    c, bones, LQ, LT = pose.load(data)
    _, ryaw, tr, face, hip = info(data)
    S = c.num_samples
    q = LQ[0, 0]
    tilt = yaw_free(q)
    d = tr[-1]
    travel = np.degrees(np.arctan2(d[1], d[0])) if np.hypot(d[0], d[1]) > 1 else float('nan')
    print('%-30s q0=(%+.2f %+.2f %+.2f %+.2f) off-game-tilt %5.1f deg | travel (%+5.0f,%+5.0f) dir %+5.0f | face %+5.0f..%+5.0f' % (
        label, q[0], q[1], q[2], q[3], tilt, d[0], d[1], travel, face[0], face[-1]))
    return tilt
if __name__ == '__main__':
    utoc = sys.argv[1]
    L = '/work/fly1014/loco/'
    t = Toc(utoc)
    byname = {p.split('Content/')[-1]: i for i, p in t.files.items()}
    B = 'RebirthSkelCompat/Built/SephirothForms/'
    names = sys.argv[2:]
    worst = 0
    for s in ('Battle04', 'Battle03'):
        for k in sorted(byname):
            if not k.startswith(B + s + '/') or not k.endswith('.uasset'):
                continue
            n = k.split('/')[-1][:-7]
            if names and n not in names:
                continue
            try:
                worst = max(worst, row(s + ' ' + n, t.read(byname[k])))
            except Exception as ex:
                print(s, n, 'ERR', ex)
    print('worst off-game tilt %.1f deg' % worst)
