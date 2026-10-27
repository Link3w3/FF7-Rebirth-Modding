"""Rebirth Sephiroth's motions (decoded from the game's packages) as the offline runner's samples for PC0010_18: each clip's
keyed bones that PC0010_18 has, their local rotations a frame, the hips' translation scaled to his hip height (Keep
Proportions), the root (Trans) translation as the clip's root motion.
    pc18_samples.py <rerig.npz> <out.json> [clip ...]"""
import glob
import json
import sys
import numpy as np
sys.path[:0] = ['/work/pc18', '/work/ccseph/tools']
import anim_zen as A

SEPH = '/work/pc18/seph/'
CLIPS = ['N_Idle01_1', 'N_Walk01_1', 'N_Run01_1', 'B_Idle01_1', 'B_Walk01_1', 'B_NAttack01_0', 'B_NAttack03_0']


def main(src, out, clips):
    SK = A.Skeleton(open(glob.glob(SEPH + '*PC0010_00_Skeleton.uasset')[0], 'rb').read())
    m = np.load(src)
    names = [str(n) for n in m['bone_names']]
    hip_ratio = float(m['bone_lt'][names.index('C_Hip_a')][2] / SK.ref_t[SK.index['C_Hip_a']][2])
    data = {}
    for clip in clips:
        f = glob.glob(SEPH + 'Motion__*__' + clip + '.uasset')[0]
        LQ, LT, fps, keyed = A.decode(open(f, 'rb').read(), SK)
        bones = [SK.names[k] for k in keyed if SK.names[k] in names]
        if 'Trans' not in bones:
            bones.insert(0, 'Trans')
        poses = []
        for fr in range(LQ.shape[0]):
            row = []
            for b in bones:
                k = SK.index[b]
                t = LT[fr, k] * (hip_ratio if b == 'C_Hip_a' else 1.0)
                row.append([round(float(x), 6) for x in LQ[fr, k]] + [round(float(x), 4) for x in t])
            poses.append(row)
        data[clip] = dict(length=(LQ.shape[0] - 1) / fps, frames=LQ.shape[0], skeleton='PC0010_00_Skeleton', bones=bones, poses=poses)
        print(clip, LQ.shape[0], 'frames', fps, 'fps', len(bones), 'bones', 'root travel', np.round(LT[-1, SK.index['Trans']] - LT[0, SK.index['Trans']], 1))
    json.dump(data, open(out, 'w'))
    print('hip ratio', round(hip_ratio, 4))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3:] or CLIPS)
