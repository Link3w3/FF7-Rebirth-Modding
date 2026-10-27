"""How his blade wings move in an offline run (anim_run's frames): each blade's turn away from where the animation alone
puts it (the chest bone times the blade's rest under it) and how far its bone moves from there, over the frames after the
first second and a half: mean, 95th percentile and most, over every blade.
    blade_metrics.py rig.json frames.bin [label]"""
import json, sys
import numpy as np


def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0); bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz], axis=-1)


def qrot(q, v):
    qv = q[..., :3]; t = 2.0 * np.cross(qv, v)
    return v + q[..., 3:4] * t + np.cross(qv, t)


rig = json.load(open(sys.argv[1]))
frames = sys.argv[2]
label = sys.argv[3] if len(sys.argv) > 3 else frames
bones = rig['bones']
index = {b['name']: i for i, b in enumerate(bones)}
raw = np.fromfile(frames, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
start = int(nf / 7.0 * 1.5)
Q, T = F[start:, :, :4], F[start:, :, 4:]
sp = index['C_Spine_d']
blades = [b['name'] for b in bones if 'SwordWing' in b['name']]
angles, moves = [], []
for n in blades:
    i = index[n]
    lq = np.array(bones[i]['local_q']); lt = np.array(bones[i]['local_t'])
    aq = qmul(Q[:, sp], np.broadcast_to(lq, Q[:, sp].shape))
    at = T[:, sp] + qrot(Q[:, sp], np.broadcast_to(lt, T[:, sp].shape))
    d = np.abs(np.sum(aq * Q[:, i], axis=-1)).clip(0, 1)
    angles.append(np.degrees(2 * np.arccos(d)))
    moves.append(np.linalg.norm(T[:, i] - at, axis=-1))
A = np.concatenate(angles); M = np.concatenate(moves)
print('%-24s NaN %s | blade turn mean %4.1f deg, p95 %4.1f, max %4.1f | blade bone moves mean %4.1f cm, p95 %4.1f, max %4.1f' % (
    label, bool(np.isnan(F).any()), A.mean(), np.percentile(A, 95), A.max(), M.mean(), np.percentile(M, 95), M.max()))
