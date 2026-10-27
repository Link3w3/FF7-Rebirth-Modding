import sys
sys.path[:0] = ['/work/acl', '/work/iostore']
import numpy as np, pose
from iostore import Toc
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
I = pose.IDX
CH = [(['C_Hip_a', 'C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d', 'C_Neck_a', 'C_Head_a'], 'k'),
      (['C_Spine_d', 'R_Shoulder_a', 'R_UpperArm_a', 'R_Forearm_a', 'R_Hand_a'], 'r'),
      (['C_Spine_d', 'L_Shoulder_a', 'L_UpperArm_a', 'L_Forearm_a', 'L_Hand_a'], 'b'),
      (['C_Hip_a', 'R_UpperLeg_a', 'R_Foreleg_a', 'R_Foot_a', 'R_Toe_a'], 'r'),
      (['C_Hip_a', 'L_UpperLeg_a', 'L_Foreleg_a', 'L_Foot_a', 'L_Toe_a'], 'b')]
def load(data):
    c, bones, LQ, LT = pose.load(data)
    LQ = LQ.copy(); LT = LT.copy()
    LQ[:, 0] = [0, 0, 0, 1]
    tr = LT[:, 0].copy()
    LT[:, 0] = 0
    GQ, GT = pose.component(LQ, LT)
    return c, GT, tr
def draw(items, out, cols=6):
    fig, axes = plt.subplots(len(items) * 2, cols, figsize=(1.9 * cols, 2.0 * 2 * len(items)))
    for r, (label, data) in enumerate(items):
        c, GT, tr = load(data)
        S = c.num_samples
        frames = [int(x) for x in np.linspace(0, S - 1, cols)]
        for k, f in enumerate(frames):
            for view in range(2):
                ax = axes[2 * r + view][k]; ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect('equal')
                def P(p):
                    return (p[0], p[2]) if view == 0 else (p[0], p[1])   # side: X right, Z up; top: X right, Y up
                for ch, col in CH:
                    pts = np.array([P(GT[f, I[b]]) for b in ch])
                    ax.plot(pts[:, 0], pts[:, 1], col + '-', lw=1.3)
                h = GT[f, I['C_Head_a']]; n = GT[f, I['C_Nose_A']]
                ax.annotate('', xy=P(h + (n - h) * 6), xytext=P(h), arrowprops=dict(arrowstyle='->', color='g'))
                ax.annotate('', xy=(60, 0 if view else -10), xytext=(0, 0 if view else -10), arrowprops=dict(arrowstyle='->', color='m'))
                if view == 0:
                    ax.set_xlim(-130, 130); ax.set_ylim(-20, 220)
                else:
                    ax.set_xlim(-130, 130); ax.set_ylim(-110, 110)
                if view == 0:
                    ax.set_title('%s f%d' % (label, f), fontsize=6)
    fig.tight_layout(); fig.savefig(out, dpi=70)
if __name__ == '__main__':
    L = '/work/fly1014/loco/'
    t = Toc('/work/kh2data1015/moves/SephirothForms_P.utoc')
    byname = {p.split('Content/')[-1]: i for i, p in t.files.items()}
    B = 'RebirthSkelCompat/Built/SephirothForms/'
    items = [('GAME Run01_1', open(L + 'B_Run01_1.uasset', 'rb').read() + open(L + 'B_Run01_1.uexp', 'rb').read()),
             ('KH2 Run01_1', t.read(byname[B + 'Battle04/B_Run01_1.uasset'])),
             ('FLY Run01_1', t.read(byname[B + 'Battle03/B_Run01_1.uasset']))]
    draw(items, sys.argv[1])
