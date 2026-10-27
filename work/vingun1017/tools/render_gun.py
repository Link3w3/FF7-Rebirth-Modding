"""Contact sheet of Vincent's gun motions: each row a motion, frames at its key moments (shots marked), drawn from his
right side (left) and from the front (right) in his own frame, the gun as a grey line from his hand."""
import sys, os, json, glob
sys.path.append('/work/vingun1017/tools')
import numpy as np
import vpose
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
I = vpose.IDX
CH = [(['C_Hip_a', 'C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d', 'C_Neck_a', 'C_Head_a'], 'k'),
      (['C_Spine_d', 'R_Shoulder_a', 'R_UpperArm_a', 'R_Forearm_a', 'R_Hand_a'], 'r'),
      (['C_Spine_d', 'L_Shoulder_a', 'L_UpperArm_a', 'L_Forearm_a', 'L_Hand_a'], 'b'),
      (['C_Hip_a', 'R_UpperLeg_a', 'R_Foreleg_a', 'R_Foot_a', 'R_Toe_a'], 'r'),
      (['C_Hip_a', 'L_UpperLeg_a', 'L_Foreleg_a', 'L_Foot_a', 'L_Toe_a'], 'b')]


def body(path):
    c, bones, LQ, LT = vpose.load(open(path, 'rb').read())
    GQ, GT = vpose.component(LQ, LT)
    tq = GQ[:, I['Trans']] * np.array([-1.0, -1.0, -1.0, 1.0])
    tt = GT[:, I['Trans']]
    root = GT[:, I['Trans']].copy()
    GT = vpose.qrot(np.repeat(tq[:, None], GT.shape[1], 1), GT - tt[:, None])
    return c, GT, root


def draw(rows, out):
    cols = max(len(r['frames']) for r in rows)
    fig, axes = plt.subplots(len(rows), cols * 2, figsize=(1.55 * cols * 2, 1.9 * len(rows)))
    if len(rows) == 1:
        axes = [axes]
    for r, row in enumerate(rows):
        c, GT, root = body(row['path'])
        for k in range(cols * 2):
            axes[r][k].axis('off')
        for k, f in enumerate(row['frames']):
            hip = GT[f, I['C_Hip_a']]
            up = np.array([0.0, 0.0, 1.0])
            right = GT[f, I['R_UpperArm_a']] - GT[f, I['L_UpperArm_a']]
            right[2] = 0
            right /= max(1e-6, np.linalg.norm(right))
            fwd = np.cross(right, up)
            for view in (0, 1):
                ax = axes[r][k * 2 + view]
                ax.set_aspect('equal')
                axis = fwd if view == 0 else right
                P = lambda p: (np.dot(p - hip, axis), np.dot(p - hip, up))
                for ch, col in CH:
                    pts = np.array([P(GT[f, I[b]]) for b in ch])
                    ax.plot(pts[:, 0], pts[:, 1], col + '-', lw=1.2)
                # the gun: from the hand's weapon bone along the forearm, 30 cm
                el, we = GT[f, I['R_Forearm_a']], GT[f, I['R_Weapon_a']]
                d = (we - el) / max(1e-6, np.linalg.norm(we - el))
                a, b = P(we), P(we + d * 30)
                ax.plot([a[0], b[0]], [a[1], b[1]], '-', color='0.35', lw=2.4)
                h = P(GT[f, I['C_Head_a']])
                ax.plot([h[0]], [h[1]], 'ko', ms=4, mfc='w')
                ax.set_xlim(-110, 110); ax.set_ylim(-110, 90)
                mark = ' SHOT' if f in row.get('shots', []) else ''
                ax.set_title(('side' if view == 0 else 'front') + ' f%d%s' % (f, mark), fontsize=6, color='r' if mark else 'k')
        axes[r][0].text(-0.15, 0.5, row['label'], transform=axes[r][0].transAxes, fontsize=7, rotation=90, va='center', ha='right')
    fig.tight_layout()
    fig.savefig(out, dpi=72)


if __name__ == '__main__':
    rows = json.load(open(sys.argv[1]))
    draw(rows, sys.argv[2])
