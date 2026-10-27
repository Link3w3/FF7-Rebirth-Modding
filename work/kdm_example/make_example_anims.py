"""Key animations (.cacanim, Create a Character System's Import Key Animations) for the Kawaii Dynamic Motions example on
Bahamut Fused Sephiroth (PC0010_17_Compat_Skeleton), from the game clips sampled in the editor (Remake Sephiroth's
EB0021 walk, bfs17/kawaii/samples_scaled.json), applied as the offline runs apply them (anim_run): each clip bone's
rotation, the hips' translation too, every other translation the model's own (its rig's reference), the root still:
  Bahamut_KDM_Stand  standing: the neutral walk's mean pose, breathing (the chest rises a little every 4 s), 121 frames
                     at 30 fps, a loop
  Bahamut_KDM_Walk   the neutral walk (N_Walk01_1) in place, 75 frames at 60 fps, a loop
    make_example_anims.py <out folder>"""
import json
import os
import struct
import sys

import numpy as np

S = json.load(open('/work/bfs17/kawaii/samples_scaled.json'))
RIG = json.load(open('/work/bfs17/tune/a3/rig.json'))
REF = {b['name']: b for b in RIG['bones']}
PARENT = {b['name']: b['parent'] for b in RIG['bones']}


def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(np.asarray(a, float), -1, 0); bx, by, bz, bw = np.moveaxis(np.asarray(b, float), -1, 0)
    return np.stack([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz], axis=-1)


def qinv(q):
    q = np.asarray(q, float)
    return np.concatenate([-q[..., :3], q[..., 3:4]], axis=-1)


def qaxis(axis, deg):
    axis = np.asarray(axis, float); axis = axis / np.linalg.norm(axis)
    h = np.radians(deg) / 2.0
    return np.concatenate([axis * np.sin(h), [np.cos(h)]])


def write_cacanim(path, tracks, frames, fps, loop=True):
    """tracks: [(bone, T (k,3), Q (k,4))], k = 1 (still) or frames"""
    with open(path, 'wb') as f:
        f.write(b'CACANIM1')
        f.write(struct.pack('<IfiIi', 1, float(fps), frames, 1 if loop else 0, len(tracks)))
        for bone, T, Q in tracks:
            T = np.asarray(T, float).reshape(-1, 3); Q = np.asarray(Q, float).reshape(-1, 4)
            Q = Q / np.linalg.norm(Q, axis=1, keepdims=True)
            if np.ptp(T, 0).max() < 1e-5 and np.ptp(Q, 0).max() < 1e-7:
                T, Q = T[:1], Q[:1]
            assert len(T) in (1, frames) and len(Q) == len(T), (bone, len(T), len(Q))
            nb = bone.encode('ascii')
            f.write(struct.pack('<H', len(nb)) + nb)
            f.write(struct.pack('<i', len(T)))
            f.write(np.concatenate([T, Q, np.ones_like(T)], -1).astype('<f4').tobytes())
    return len(tracks)


def clip_locals(clip):
    """per clip bone: (T frames x 3, Q frames x 4) as the runs apply them"""
    P = np.array(clip['poses'], float)
    out = {}
    for k, name in enumerate(clip['bones']):
        Q = P[:, k, :4].copy()
        for f in range(1, len(Q)):                     # (one hemisphere: smooth keys)
            if np.dot(Q[f], Q[f - 1]) < 0:
                Q[f] = -Q[f]
        if name == 'Trans':
            T = np.zeros((len(P), 3)); Q = np.tile([0.0, 0.0, 0.0, 1.0], (len(P), 1))
        elif name == 'C_Hip_a':
            T = P[:, k, 4:]
        else:
            T = np.tile(REF[name]['local_t'], (len(P), 1))
        out[name] = (T, Q)
    return out


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    report = {}
    # the walk, in place
    walk = S['Neutral00/N_Walk01_1']
    W = clip_locals(walk)
    frames = walk['frames']
    n = write_cacanim(os.path.join(out, 'Bahamut_KDM_Walk.cacanim'), [(b, T, Q) for b, (T, Q) in W.items()], frames, 60.0)
    report['Bahamut_KDM_Walk'] = {'frames': frames, 'fps': 60.0, 'tracks': n}
    # standing: the walk's mean pose (rotations averaged in one hemisphere, the hips' place too)
    mean = {}
    for b, (T, Q) in W.items():
        q = Q.mean(0); q /= np.linalg.norm(q)
        mean[b] = (T.mean(0), q)
    # breathing: the chest (C_Spine_c, C_Spine_d) turned a little about the model's side axis (+Y), every 4 s
    F = 121
    ph = np.sin(2 * np.pi * np.arange(F) / (F - 1))
    # component rotations of the stand pose's spine bones (the clip bones above them are all clip bones or the root)
    comp = {}
    def comp_rot(b):
        if b in comp:
            return comp[b]
        p = PARENT[b]
        local = mean[b][1] if b in mean else np.array(REF[b]['local_q'], float)
        comp[b] = local if p is None else qmul(comp_rot(p), local)
        return comp[b]
    tracks = []
    for b, (t, q) in mean.items():
        if b in ('C_Spine_c', 'C_Spine_d'):
            parent_c = comp_rot(PARENT[b])
            Qs = []
            for s in ph:
                turn = qaxis([0, 1, 0], -0.6 * s)        # (component space, about the bone)
                Qs.append(qmul(qinv(parent_c), qmul(turn, qmul(parent_c, q))))
            tracks.append((b, np.tile(t, (F, 1)), np.array(Qs)))
        else:
            tracks.append((b, t, q))
    n = write_cacanim(os.path.join(out, 'Bahamut_KDM_Stand.cacanim'), tracks, F, 30.0)
    report['Bahamut_KDM_Stand'] = {'frames': F, 'fps': 30.0, 'tracks': n}
    json.dump(report, open(os.path.join(out, 'anims.json'), 'w'), indent=1)
    print(report)


main()
