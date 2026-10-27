"""Sora's facial set (Cloud's in-game Facial00 keys) from his KH3 face animations: 2-frame poses and a few longer
animations, face bones only (the bones under 'facial'), as key animation files (.cacanim) for the editor's
Import Key Animations, plus a contact sheet.

    python3 build_poses.py <out dir>
"""
import json
import os
import struct
import sys
import numpy as np
import facerender as fr
import feats

TRACKS = '/work/soraface/all/tracks'
FACE = [b for b in feats.FACE if b not in ('realtimeA', 'realtimeB')]
EYES = ['L_eye', 'R_eye']
LIDS = ['L_hole', 'R_hole', 'LU_eyelid_a', 'RU_eyelid_a', 'LU_eyelid_b', 'RU_eyelid_b', 'LU_eyelid_c', 'RU_eyelid_c',
        'LU_eyelash_a', 'RU_eyelash_a', 'LU_eyelash_b', 'RU_eyelash_b', 'LD_eyelid_a', 'RD_eyelid_a', 'LD_eyelid_b',
        'RD_eyelid_b', 'LD_eyelid_c', 'RD_eyelid_c']
BROWS_L = ['L_brow_a', 'L_brow_b', 'L_brow_c', 'L_brow_d']
BROWS_R = ['R_brow_a', 'R_brow_b', 'R_brow_c', 'R_brow_d']
BROWS = ['C_brow'] + BROWS_L + BROWS_R
_cache = {}


def track(name):
    if name not in _cache:
        _cache[name] = json.load(open(os.path.join(TRACKS, name + '.json')))
    return _cache[name]


def frame(name, f):
    """{bone: (q, t)} of every face bone at a frame (bones the animation lacks at the reference pose)."""
    t = track(name)
    out = {}
    for b in FACE:
        tr = t['bones'].get(b)
        if tr is None:
            i = fr.IDX[b]; out[b] = (fr.REFQ[i].copy(), fr.REFT[i].copy())
        else:
            q = np.array(tr['q'][min(f, len(tr['q']) - 1)], np.float64); p = np.array(tr['p'][min(f, len(tr['p']) - 1)], np.float64)
            out[b] = (q / np.linalg.norm(q), p)
    return out


def slerp(a, b, w):
    if np.dot(a, b) < 0:
        b = -b
    d = np.clip(np.dot(a, b), -1, 1)
    if d > 0.9995:
        r = a + w * (b - a)
    else:
        th = np.arccos(d); r = (np.sin((1 - w) * th) * a + np.sin(w * th) * b) / np.sin(th)
    return r / np.linalg.norm(r)


def mix(base, src, bones, w=1.0):
    out = dict(base)
    for b in bones:
        out[b] = (slerp(base[b][0], src[b][0], w), base[b][1] + w * (src[b][1] - base[b][1]))
    return out


def axis_q(axis, deg):
    a = np.radians(deg) / 2
    v = np.array(axis, np.float64); v /= np.linalg.norm(v)
    return np.array([*(v * np.sin(a)), np.cos(a)])


def turn_eyes(pose, yaw=0.0, pitch=0.0):
    """Eyes turned in component space: yaw > 0 toward Sora's left, pitch > 0 up (forward is +X, his right +Y, up +Z)."""
    out = dict(pose)
    R = fr.qmul(axis_q([0, 0, 1], -yaw), axis_q([0, 1, 0], -pitch))
    for b in EYES:
        i = fr.IDX[b]
        Qp = fr.REF_CQ[fr.PAR[i]]
        q, t = pose[b]
        out[b] = (fr.qmul(fr.qmul(fr.qinv(Qp), fr.qmul(R, Qp)), q), t)
    return out


def with_eyes(pose, eyes_from):
    return mix(pose, eyes_from, EYES)


# ---------------------------------------------------------------------------------------------------------------
REF = {b: (fr.REFQ[fr.IDX[b]].copy(), fr.REFT[fr.IDX[b]].copy()) for b in FACE}
IDLE = mix(frame('F_1011EM', 115), REF, EYES)     # eyes straight ahead (the reference)
BROW_UP = mix(IDLE, frame('F_1221EM', 72), BROWS, 0.45)
BROW_DOWN = mix(IDLE, frame('F_1310EM', 75), BROWS, 0.75)
CLOSED = frame('F_0001EM', 0)


def expression(name, f, brows=1.0):
    p = with_eyes(frame(name, f), IDLE)
    if brows != 1.0:
        p = mix(p, IDLE, BROWS, 1 - brows)
    return p


POSES = {
    'F_Idle01': IDLE,
    'F_Eyelid_blink01': mix(IDLE, CLOSED, LIDS),
    'F_Eyelid_up01': mix(turn_eyes(IDLE, pitch=4.0), frame('F_0020EM', 0), LIDS, 0.5),
    'F_Eyelid_down01': mix(mix(turn_eyes(IDLE, pitch=-5.0), frame('F_0021EM', 60), LIDS, 0.6), BROW_DOWN, BROWS, 0.3),
    'F_Eyelid_left01': turn_eyes(IDLE, yaw=7.0),
    'F_Eyelid_right01': turn_eyes(IDLE, yaw=-7.0),
    'F_Brow_up01': BROW_UP,
    'F_Brow_down01': BROW_DOWN,
    'F_Brow_up_left01': mix(IDLE, BROW_UP, BROWS_L),
    'F_Brow_up_right01': mix(IDLE, BROW_UP, BROWS_R),
    'F_Smile01': expression('F_0830EM', 32),
    'F_Glad01': expression('F_0553EM', 19),
    'F_Sad01': expression('F_1873EM', 58),
    'F_Angry01': expression('F_1310EM', 75),
    'F_Disgust01': expression('F_1610EM', 31),
    'F_Surprise01': expression('F_1745EM', 28),
    'F_Sneer01': expression('F_1715EM', 24),
    'F_Tired01': expression('F_0103EM', 4),
    'F_Tired02': expression('F_1243EM', 14),
    'F_Serious01': expression('F_0104EM', 0),
    'F_Attack01': expression('F_0100EM', 67),
    'F_Attack02': expression('F_1102EM', 26),
    'F_Dmg01': expression('F_1610EM', 12),
    'F_Dmg02': expression('F_1102EM', 31),
    'F_CallChocobo': expression('F_0852EM', 34),
    'F_PoseC': expression('F_0801EM', 23),
}

# longer ones: (KH3 animation, first frame, last frame) played as they are (eyes too)
SEQUENCES = {
    'F_idle02': ('F_1011EM', 0, None),
    'F_idle03': ('F_1010EM', 0, None),
    'F_idle03_2': ('F_0006EM', 0, None),
    'F_idle04': ('F_0005EM', 0, None),
    'F_Talk_idle01': ('F_1141EM', 0, None),
    'F_PoseA2C': ('F_0830EM', 0, None),
    'B_AtkLimit01_0_FA': ('F_1151EM', 0, None),
    'F_Limit003': ('F_1150EM', 0, None),
    'F_BurstChain_10': ('F_2302EM', 0, None),
}


def write_cacanim(path, frames, fps=30.0, loop=False):
    """frames: list of {bone: (q, t)}; a bone still for the whole clip gets one key."""
    S = len(frames)
    assert S >= 2
    with open(path, 'wb') as f:
        f.write(b'CACANIM1')
        f.write(struct.pack('<IfiIi', 1, float(fps), S, 1 if loop else 0, len(FACE)))
        for b in FACE:
            Q = np.array([fr_[b][0] for fr_ in frames]); T = np.array([fr_[b][1] for fr_ in frames])
            for k in range(1, S):
                if np.dot(Q[k], Q[k - 1]) < 0:
                    Q[k] = -Q[k]
            const = np.abs(Q - Q[:1]).max() < 1e-7 and np.abs(T - T[:1]).max() < 1e-6
            if const:
                Q, T = Q[:1], T[:1]
            Sc = np.ones((len(Q), 3))
            nb = b.encode('ascii')
            f.write(struct.pack('<H', len(nb)) + nb + struct.pack('<i', len(Q)))
            f.write(np.concatenate([T, Q, Sc], -1).astype('<f4').tobytes())


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    report = {}
    for name, pose in POSES.items():
        write_cacanim(os.path.join(out_dir, name + '.cacanim'), [pose, pose])
        report[name] = 'pose'
    for name, (src, a, b) in SEQUENCES.items():
        n = track(src)['frames']
        b = n - 1 if b is None else b
        frames = [frame(src, f) for f in range(a, b + 1)]
        write_cacanim(os.path.join(out_dir, name + '.cacanim'), frames, loop=name.startswith('F_idle') or name == 'F_Talk_idle01')
        report[name] = '%s frames %d-%d (%d)' % (src, a, b, len(frames))
    json.dump(report, open(os.path.join(out_dir, 'report.json'), 'w'), indent=1)
    return report


def sheet(path, scale=14):
    F = fr.Face()
    ims = []
    for name, pose in POSES.items():
        ims.append(F.render(pose, scale=scale, label=name[2:] if name.startswith('F_') else name))
    for name, (src, a, b) in SEQUENCES.items():
        n = track(src)['frames']
        ims.append(F.render(frame(src, (n - 1) // 2), scale=scale, label='%s (%s mid)' % (name, src[2:])))
    return fr.sheet(ims, 7, path)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '/work/soraface/facial00_cacanim'
    print(json.dumps(main(out), indent=1))
    if len(sys.argv) > 2:
        print(sheet(sys.argv[2]))
