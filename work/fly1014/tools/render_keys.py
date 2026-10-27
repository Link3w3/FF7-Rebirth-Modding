import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from aclclip import Clip, SK_NAMES, SK_INDEX
sys.path.insert(0, '/work/kh2/tools')
import clip as CL

def read_cacanim(path):
    d = open(path, 'rb').read()
    assert d[:8] == b'CACANIM1'
    ver, fps, frames, flags, ntracks = struct.unpack_from('<IfiIi', d, 8)
    p = 28
    bones, T, Q = [], [], []
    for _ in range(ntracks):
        n = struct.unpack_from('<H', d, p)[0]; p += 2
        bones.append(d[p:p + n].decode()); p += n
        k = struct.unpack_from('<i', d, p)[0]; p += 4
        keys = np.frombuffer(d, dtype='<f4', count=k * 10, offset=p).reshape(k, 10).astype(np.float64); p += k * 40
        if k == 1: keys = np.repeat(keys, frames, 0)
        T.append(keys[:, 0:3]); Q.append(keys[:, 3:7])
    T = np.stack(T, 1); Q = np.stack(Q, 1)
    return Clip(bones, T, Q, np.ones_like(T), fps, os.path.basename(path))

CH = [(['C_Hip_a', 'C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d', 'C_Neck_a', 'C_Head_a'], 'k'),
      (['C_Spine_d', 'R_Shoulder_a', 'R_UpperArm_a', 'R_Forearm_a', 'R_Hand_a'], 'r'),
      (['C_Spine_d', 'L_Shoulder_a', 'L_UpperArm_a', 'L_Forearm_a', 'L_Hand_a'], 'b'),
      (['C_Hip_a', 'R_UpperLeg_a', 'R_Foreleg_a', 'R_Foot_a', 'R_Toe_a'], 'r'),
      (['C_Hip_a', 'L_UpperLeg_a', 'L_Foreleg_a', 'L_Foot_a', 'L_Toe_a'], 'b')]
WING = [n for n in SK_NAMES if 'Feather' in n]

def draw(paths, out, cols=6):
    fig, axes = plt.subplots(len(paths), cols, figsize=(2.0 * cols, 2.4 * len(paths)))
    for r, path in enumerate(paths):
        c = read_cacanim(path)
        want = sorted({b for ch, _ in CH for b in ch} | set(WING) | {'Trans', 'C_Nose_A'})
        w = c.world(want)
        frames = [int(x) for x in np.linspace(0, c.frames - 1, cols)]
        for k, f in enumerate(frames):
            ax = axes[r][k]; ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect('equal')
            root = w['Trans'][0][f]
            for ch, col in CH:
                pts = np.array([w[b][0][f] for b in ch]) - root
                ax.plot(pts[:, 0], pts[:, 2], col + '-', lw=1.4)
            for b in WING:
                par = SK_NAMES[CL.SK_PARENTS[SK_INDEX[b]]]
                if par in w:
                    a, bb = w[par][0][f] - root, w[b][0][f] - root
                    ax.plot([a[0], bb[0]], [a[2], bb[2]], '-', color='0.6', lw=0.6)
            h = w['C_Head_a'][0][f] - root
            ax.plot([h[0]], [h[2]], 'ko', ms=5, mfc='w')
            ax.axhline(0, color='g', lw=0.6)
            ax.set_xlim(-170, 170); ax.set_ylim(-20, 300)
            ax.set_title('%s f%d' % (os.path.basename(path).replace('FLY_', '').replace('.cacanim', ''), f), fontsize=7)
    fig.suptitle('side view: his forward (+X) to the right; green line = the ground (root); grey = wing feathers', fontsize=9)
    fig.tight_layout(); fig.savefig(out, dpi=58)

if __name__ == '__main__':
    draw(sys.argv[2:], sys.argv[1])
