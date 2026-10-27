"""Standing poses for the Kawaii Dynamic Motions example, from the sampled game clips (kawaii/samples_scaled.json):
each clip's mean pose (its frames' rotations averaged, translations too; the root kept at the origin), and the battle
walk's first frame (the offline "Stand" run's). Written as one-pose clips (75 frames) in a samples file for anim_run."""
import json
import numpy as np

S = json.load(open('/work/bfs17/kawaii/samples_scaled.json'))


def mean_pose(clip):
    P = np.array(clip['poses'], dtype=float)          # frames, bones, 7 (qx qy qz qw tx ty tz)
    Q = P[:, :, :4].copy()
    ref = Q[0]
    sign = np.sign(np.sum(Q * ref[None], axis=-1, keepdims=True))
    sign[sign == 0] = 1
    q = (Q * sign).mean(0)
    q /= np.linalg.norm(q, axis=-1, keepdims=True)
    t = P[:, :, 4:].mean(0)
    return np.concatenate([q, t], -1)


out = {}
for name, src in (('Example/StandN', 'Neutral00/N_Walk01_1'), ('Example/StandB', 'Battle00/B_Walk01_1')):
    pose = mean_pose(S[src])
    pose[0, 4:] = 0.0                                   # the root at the origin (no root motion)
    out[name] = {'length': 74 / 60.0, 'frames': 75, 'skeleton': S[src]['skeleton'], 'bones': S[src]['bones'],
                 'poses': [pose.tolist()] * 75}
first = np.array(S['Battle00/B_Walk01_1']['poses'][0], dtype=float)
first[0, 4:] = 0.0
out['Example/StandB0'] = {'length': 74 / 60.0, 'frames': 75, 'skeleton': S['Battle00/B_Walk01_1']['skeleton'],
                          'bones': S['Battle00/B_Walk01_1']['bones'], 'poses': [first.tolist()] * 75}
json.dump(out, open('stand_candidates.json', 'w'))
print({k: v['frames'] for k, v in out.items()})
