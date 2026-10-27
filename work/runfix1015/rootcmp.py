import sys
sys.path[:0] = ['/work/acl', '/work/iostore']
import numpy as np, pose
from iostore import Toc
I = pose.IDX
def qrot(q, v):
    return pose.qrot(q, v)
def yaw_of(q):
    x = pose.qrot(q, np.broadcast_to(np.array([1.0, 0, 0]), q.shape[:-1] + (3,)))
    return np.degrees(np.arctan2(x[..., 1], x[..., 0]))
def info(data):
    c, bones, LQ, LT = pose.load(data)
    S = c.num_samples
    q0 = LQ[0, 0]
    # root yaw relative to the first frame (the game's Trans carries a constant tilt q: remove it)
    rel = pose.qmul(LQ[:, 0], np.array([q0[0] * -1, q0[1] * -1, q0[2] * -1, q0[3]])[None].repeat(S, 0))
    ryaw = yaw_of(rel)
    tr = LT[:, 0] - LT[0, 0]
    # facing: nose in component space with the root's current rotation applied relative to the first frame
    LQ2 = LQ.copy(); LQ2[:, 0] = rel; LT2 = LT.copy(); LT2[:, 0] = tr
    GQ, GT = pose.component(LQ2, LT2)
    nose = GT[:, I['C_Nose_A']] - GT[:, I['C_Head_a']]
    face = np.degrees(np.arctan2(nose[:, 1], nose[:, 0]))
    hip = GT[:, I['C_Hip_a']]
    return c, ryaw, tr, face, hip
def show(label, data):
    c, ryaw, tr, face, hip = info(data)
    S = c.num_samples
    idx = [0, S // 4, S // 2, 3 * S // 4, S - 1]
    print('%-34s %5.2fs root yaw %s | root xy %s | face %s' % (label, (S - 1) / c.sample_rate,
          ' '.join('%+5.0f' % ryaw[i] for i in idx), ' '.join('(%+4.0f,%+4.0f)' % (tr[i, 0], tr[i, 1]) for i in idx),
          ' '.join('%+5.0f' % face[i] for i in idx)))
if __name__ == '__main__':
    L = '/work/fly1014/loco/'
    t = Toc('/work/kh2data1015/moves/SephirothForms_P.utoc')
    byname = {p.split('Content/')[-1]: i for i, p in t.files.items()}
    B = 'RebirthSkelCompat/Built/SephirothForms/'
    names = sys.argv[1:] or ['B_Run01_0_L0', 'B_Run01_0_L90', 'B_Run01_0_R90', 'B_Run01_0_L180', 'B_Run01_0_R180', 'B_Run01_1', 'B_Run01_1_L180', 'B_Run01_1_R180', 'B_Run01_2l', 'B_Turn01_L90', 'B_Turn01_R90', 'B_Turn01_L180', 'B_Walk01_0_L90', 'B_Walk01_0_R90', 'B_Walk01_0_L180', 'B_Walk01_1', 'B_WalkL01_1', 'B_WalkB01_1']
    for n in names:
        try:
            show('GAME ' + n, open(L + n + '.uasset', 'rb').read() + open(L + n + '.uexp', 'rb').read())
        except Exception as ex:
            print('GAME', n, '-', ex)
        for s in ('Battle04', 'Battle03'):
            k = B + s + '/' + n + '.uasset'
            if k in byname:
                show(s + ' ' + n, t.read(byname[k]))
