"""Contact sheets of Remake Sephiroth's motions (motion_eb0021.json, 15 fps samples): side and top views per frame, the
Masamune drawn from the sword hand along L_Weapon_a's +Z (240 cm), damage windows (notifies_eb0021.json) in red."""
import json, sys, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
d = json.load(open('motion_eb0021.json'))
N = json.load(open('notifies_eb0021.json'))
B = d['bones']; A = d['animations']
I = {b: i for i, b in enumerate(B)}
LINKS = [('C_Hip_a', 'C_Spine_d'), ('C_Spine_d', 'C_Neck_a'), ('C_Neck_a', 'C_Head_a'), ('C_Spine_d', 'L_UpperArm_a'), ('L_UpperArm_a', 'L_Forearm_a'),
         ('L_Forearm_a', 'L_Hand_a'), ('C_Spine_d', 'R_UpperArm_a'), ('R_UpperArm_a', 'R_Forearm_a'), ('R_Forearm_a', 'R_Hand_a'),
         ('C_Hip_a', 'L_UpperLeg_a'), ('L_UpperLeg_a', 'L_Foreleg_a'), ('L_Foreleg_a', 'L_Foot_a'), ('L_Foot_a', 'L_Toe_a'),
         ('C_Hip_a', 'R_UpperLeg_a'), ('R_UpperLeg_a', 'R_Foreleg_a'), ('R_Foreleg_a', 'R_Foot_a'), ('R_Foot_a', 'R_Toe_a')]
LEFT = {'L_UpperArm_a', 'L_Forearm_a', 'L_Hand_a', 'L_UpperLeg_a', 'L_Foreleg_a', 'L_Foot_a', 'L_Toe_a'}


def rot(q, v):
    x, y, z, w = q
    u = np.array([x, y, z])
    return v + 2 * np.cross(u, np.cross(u, v) + w * v)


def yawrot(deg, p):
    r = np.radians(deg)
    c, s = np.cos(r), np.sin(r)
    return np.array([c * p[0] - s * p[1], s * p[0] + c * p[1], p[2]])


def frame(s):
    root = np.array(s[1:4]); yaw = s[4]
    pos = np.array(s[5:5 + 3 * len(B)]).reshape(-1, 3)
    q = s[5 + 3 * len(B):]
    tip = pos[I['L_Weapon_a']] + rot(q, np.array([0, 0, 1.0])) * 240
    pts = {b: root + yawrot(yaw, pos[i]) for b, i in I.items()}
    pts['tip'] = root + yawrot(yaw, tip)
    return pts


def windows(name):
    out = []
    for n in N.get(name, {}).get('notifies', []):
        if 'BattleDamage' in n['cls']:
            out.append((n['time'], n['time'] + max(n['dur'], 1 / 15.0)))
    return out


def sheet(names, path, every=2):
    rows = []
    for name in names:
        a = A[name]
        ss = a['samples'][::every]
        rows.append((name, a['length'], ss, windows(name)))
    cols = max(len(r[2]) for r in rows)
    fig, axes = plt.subplots(2 * len(rows), cols, figsize=(cols * 1.6, 2 * len(rows) * 1.6), squeeze=False)
    for r, (name, length, ss, win) in enumerate(rows):
        allp = [frame(s) for s in ss]
        xs = [p[k][0] for p in allp for k in p]; ys = [p[k][1] for p in allp for k in p]; zs = [p[k][2] for p in allp for k in p]
        cx = (max(xs) + min(xs)) / 2; cy = (max(ys) + min(ys)) / 2; cz = (max(zs) + min(zs)) / 2
        span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 300) / 2 + 30
        for c in range(cols):
            for v in range(2):
                ax = axes[2 * r + v][c]
                ax.set_xticks([]); ax.set_yticks([])
                if c >= len(ss):
                    ax.axis('off'); continue
                p = allp[c]; t = ss[c][0]
                hit = any(a0 - 0.035 <= t <= a1 + 0.035 for a0, a1 in win)
                for a_, b_ in LINKS + [('L_Hand_a', 'tip')]:
                    col = 'tab:red' if b_ == 'tip' else ('tab:blue' if b_ in LEFT else 'k')
                    if v == 0:
                        ax.plot([p[a_][0], p[b_][0]], [p[a_][2], p[b_][2]], color=col, lw=1)
                    else:
                        ax.plot([p[a_][1], p[b_][1]], [p[a_][0], p[b_][0]], color=col, lw=1)
                if v == 0:
                    ax.set_xlim(cx - span, cx + span); ax.set_ylim(min(-20, cz - span), max(cz + span, 2 * span - 20))
                    ax.axhline(0, color='0.7', lw=0.5)
                    ax.set_title('%.2f' % t, fontsize=6, color='red' if hit else 'k')
                else:
                    ax.set_xlim(cy - span, cy + span); ax.set_ylim(cx - span, cx + span)
                ax.set_aspect('equal')
                if hit:
                    for sp in ax.spines.values():
                        sp.set_color('red'); sp.set_linewidth(1.5)
                if c == 0:
                    ax.set_ylabel(('%s %.2fs' % (name.split('/')[1], length)) if v == 0 else 'top', fontsize=6)
    plt.tight_layout(pad=0.2)
    plt.savefig(path, dpi=70)
    plt.close(fig)


if __name__ == '__main__':
    out = sys.argv[1]
    every = int(sys.argv[2])
    sheet(sys.argv[3:], out, every)
