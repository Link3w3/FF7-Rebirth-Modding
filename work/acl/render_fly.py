import sys
sys.path.insert(0, '/work/acl')
import numpy as np, pose
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
I = pose.IDX
CH = [(['C_Hip_a', 'C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d', 'C_Neck_a', 'C_Head_a'], 'k'),
      (['C_Spine_d', 'R_Shoulder_a', 'R_UpperArm_a', 'R_Forearm_a', 'R_Hand_a'], 'r'),
      (['C_Spine_d', 'L_Shoulder_a', 'L_UpperArm_a', 'L_Forearm_a', 'L_Hand_a'], 'b'),
      (['C_Hip_a', 'R_UpperLeg_a', 'R_Foreleg_a', 'R_Foot_a', 'R_Toe_a'], 'r'),
      (['C_Hip_a', 'L_UpperLeg_a', 'L_Foreleg_a', 'L_Foot_a', 'L_Toe_a'], 'b')]
def chain_of(bone):
    out = []
    while bone >= 0:
        out.append(bone)
        bone = pose.PARENTS[bone]
    return out
def draw(names, out, cols=6):
    fig, axes = plt.subplots(len(names), cols, figsize=(2.0 * cols, 2.3 * len(names)))
    for r, name in enumerate(names):
        d = open('/work/fly1014/pkgs/%s.bin' % name, 'rb').read()
        c, bones, LQ, LT = pose.load(d)
        LQ[:, 0] = [0, 0, 0, 1]
        GQ, GT = pose.component(LQ, LT)
        wing = [b for b in bones if 'Feather' in pose.NAMES[b] or 'Wing' in pose.NAMES[b]]
        S = c.num_samples
        frames = [int(x) for x in np.linspace(0, S - 1, cols)]
        for k, f in enumerate(frames):
            ax = axes[r][k]; ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect('equal')
            hip = GT[f, I['C_Hip_a']]
            nose = GT[f, I['C_Nose_A']] - GT[f, I['C_Head_a']]
            yaw = np.arctan2(nose[1], nose[0])
            # view from his right side: forward (his facing) to the right of the image
            fwd = np.array([np.cos(yaw), np.sin(yaw), 0.0])
            def P(p):
                v = p - hip
                return np.dot(v, fwd), v[2]
            for ch, col in CH:
                pts = np.array([P(GT[f, I[b]]) for b in ch])
                ax.plot(pts[:, 0], pts[:, 1], col + '-', lw=1.4)
            for b in wing:
                par = pose.PARENTS[b]
                a, bb = P(GT[f, par]), P(GT[f, b])
                ax.plot([a[0], bb[0]], [a[1], bb[1]], '-', color='0.5', lw=0.8)
            h = P(GT[f, I['C_Head_a']])
            ax.plot([h[0]], [h[1]], 'ko', ms=5, mfc='w')
            ax.set_xlim(-160, 160); ax.set_ylim(-150, 170)
            vel = (GT[min(f + 1, S - 1), I['C_Hip_a']] - GT[max(f - 1, 0), I['C_Hip_a']]) * c.sample_rate / 2
            ax.set_title('%s f%d v%.0f' % (name.replace('EV_FOREE_', '').replace('_PC0010_10_', ' '), f, np.linalg.norm(vel)), fontsize=6)
    fig.tight_layout(); fig.savefig(out, dpi=60)
draw(sys.argv[2].split(','), sys.argv[1])
