"""ch049's Unity clips (character.049.motion) -> key animations (.cacanim, for Create a Character System's Import Key
Animations) on two skeletons:

  ch049   his own skeleton in the End project (CH049_001_Skeleton): every bone's track as the clip moves it, in the
          imported skeleton's frames (Unity -> Blender -> turned to face +X -> Unreal, centimetres; the root bone at
          rest is identity and carries his root motion).
  seph    Sephiroth's PC0010_00_Skeleton: his body bones take ch049's component-space rotation changes from ch049's
          rest pose, applied to Sephiroth's rest pose turned so each mapped bone points the way ch049's rest bone
          points (T-pose against Sephiroth's rest); the hips take ch049's pelvis travel scaled by the hip heights; the
          Masamune socket (L_Weapon_a: both hold their sword in the left hand) follows ch049's sword (main_weapon)
          relative to his left-hand socket; Trans carries the root motion the way the game's clips do (yaw * the
          exporter's axis change (-0.5, 0.5, -0.5, 0.5), translation in centimetres) with the body posed against
          Trans at rest; every other Sephiroth bone (face, hair, coat, helper bones) keeps its rest pose.

    convert_ch049_anims.py <character bundle> <motion bundle> <model dir> <seph_bones.json> <out dir>
Writes <out>/ch049/<job>/*.cacanim, <out>/seph/<job>/*.cacanim (jobs of 25), jobs.json and report.json.
"""
import json, os, struct, sys
import numpy as np
sys.path.insert(0, '/work/ch049anim')
import unity_anim as U

C = np.array([[-1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])          # Unity -> Blender
TZ = np.array([[0.0, -1.0, 0], [1.0, 0, 0], [0, 0, 1.0]])        # 90 degrees about Z (the import's turn)
M = np.diag([1.0, -1.0, 1.0])                                     # Blender -> Unreal
A = M @ TZ @ C                                                    # Unity world axes -> Unreal (turned to face +X)
B = C.T @ M                                                       # Unity bone axes -> the imported bones' axes
# (the import built every bone but the root as M T (C W C^T) M = A W B; the root is identity at rest and its motion
#  is turned with the body: A W A^T)
G = np.array([-0.5, 0.5, -0.5, 0.5])                              # the game's root axis change
JOB = 25

# ---- quaternions [x, y, z, w], Hamilton (a * b: b first)
def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0)
    bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz], -1)

def qinv(q):
    return q * np.array([-1, -1, -1, 1.0])

def qrot(q, v):
    x, y, z, w = np.moveaxis(q, -1, 0)
    vx, vy, vz = np.moveaxis(v, -1, 0)
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return np.stack([vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx)], -1)

def qnorm(q):
    return q / np.linalg.norm(q, axis=-1, keepdims=True)

def mat2quat(R):
    """rotation matrices [..., 3, 3] -> quaternions [..., 4] (x, y, z, w)"""
    m = R
    t = m[..., 0, 0] + m[..., 1, 1] + m[..., 2, 2]
    q = np.zeros(R.shape[:-2] + (4,))
    c0 = t > 0
    s = np.sqrt(np.maximum(t + 1.0, 1e-12)) * 2
    q0 = np.stack([(m[..., 2, 1] - m[..., 1, 2]) / s, (m[..., 0, 2] - m[..., 2, 0]) / s, (m[..., 1, 0] - m[..., 0, 1]) / s, 0.25 * s], -1)
    c1 = (~c0) & (m[..., 0, 0] > m[..., 1, 1]) & (m[..., 0, 0] > m[..., 2, 2])
    s1 = np.sqrt(np.maximum(1.0 + m[..., 0, 0] - m[..., 1, 1] - m[..., 2, 2], 1e-12)) * 2
    q1 = np.stack([0.25 * s1, (m[..., 0, 1] + m[..., 1, 0]) / s1, (m[..., 0, 2] + m[..., 2, 0]) / s1, (m[..., 2, 1] - m[..., 1, 2]) / s1], -1)
    c2 = (~c0) & (~c1) & (m[..., 1, 1] > m[..., 2, 2])
    s2 = np.sqrt(np.maximum(1.0 + m[..., 1, 1] - m[..., 0, 0] - m[..., 2, 2], 1e-12)) * 2
    q2 = np.stack([(m[..., 0, 1] + m[..., 1, 0]) / s2, 0.25 * s2, (m[..., 1, 2] + m[..., 2, 1]) / s2, (m[..., 0, 2] - m[..., 2, 0]) / s2], -1)
    s3 = np.sqrt(np.maximum(1.0 + m[..., 2, 2] - m[..., 0, 0] - m[..., 1, 1], 1e-12)) * 2
    q3 = np.stack([(m[..., 0, 2] + m[..., 2, 0]) / s3, (m[..., 1, 2] + m[..., 2, 1]) / s3, 0.25 * s3, (m[..., 1, 0] - m[..., 0, 1]) / s3], -1)
    q = np.where(c0[..., None], q0, np.where(c1[..., None], q1, np.where(c2[..., None], q2, q3)))
    return qnorm(q)

def arc(u, v):
    u = u / np.linalg.norm(u); v = v / np.linalg.norm(v)
    d = float(np.dot(u, v))
    if d > 1 - 1e-9:
        return np.array([0, 0, 0, 1.0])
    if d < -1 + 1e-9:
        a = np.cross(u, [1, 0, 0])
        if np.linalg.norm(a) < 1e-6:
            a = np.cross(u, [0, 1, 0])
        a /= np.linalg.norm(a)
        return np.array([a[0], a[1], a[2], 0.0])
    c = np.cross(u, v)
    q = np.array([c[0], c[1], c[2], 1 + d])
    return q / np.linalg.norm(q)

def fk(LQ, LT, LS, parents):
    GQ, GT, GS = np.zeros_like(LQ), np.zeros_like(LT), np.zeros_like(LS)
    for i, p in enumerate(parents):
        if p < 0:
            GQ[:, i], GT[:, i], GS[:, i] = LQ[:, i], LT[:, i], LS[:, i]
        else:
            GQ[:, i] = qmul(GQ[:, p], LQ[:, i])
            GT[:, i] = GT[:, p] + qrot(GQ[:, p], LT[:, i] * GS[:, p])
            GS[:, i] = GS[:, p] * LS[:, i]
    return GQ, GT, GS

def hemisphere(Q):
    for i in range(Q.shape[1]):
        q = Q[:, i]
        for f in range(1, len(q)):
            if np.dot(q[f], q[f - 1]) < 0:
                q[f] = -q[f]
    return Q

def write_cacanim(path, names, fps, LQ, LT, LS, loop):
    """'CACANIM1', u32 version 1, f32 fps, i32 frames, u32 flags (1 = loop), i32 tracks, then per track u16 name length +
    name, i32 keys (1 or frames), keys x (T xyz, Q xyzw, S xyz) float32 (Unreal axes, local to the parent bone)."""
    S = LQ.shape[0]
    with open(path, 'wb') as f:
        f.write(b'CACANIM1')
        f.write(struct.pack('<IfiIi', 1, float(fps), S, 1 if loop else 0, len(names)))
        for i, n in enumerate(names):
            T, Q, Sc = LT[:, i], LQ[:, i], LS[:, i]
            if np.abs(T - T[:1]).max() < 1e-4 and np.abs(Q - Q[:1]).max() < 1e-6 and np.abs(Sc - Sc[:1]).max() < 1e-6:
                T, Q, Sc = T[:1], Q[:1], Sc[:1]
            nb = n.encode('ascii')
            f.write(struct.pack('<H', len(nb)) + nb)
            f.write(struct.pack('<i', len(T)))
            f.write(np.concatenate([T, Q, Sc], -1).astype('<f4').tobytes())


class Skel:
    def __init__(self, names, parents, q, t, s):
        self.names, self.parents = names, parents
        self.index = {n: i for i, n in enumerate(names)}
        self.q, self.t, self.s = np.asarray(q, float), np.asarray(t, float), np.asarray(s, float)
        assert all(p < i for i, p in enumerate(parents))
        gq, gt, gs = fk(self.q[None], self.t[None], self.s[None], parents)
        self.gq, self.gt, self.gs = gq[0], gt[0], gs[0]


def ue_world(Wu, bones_rig, is_root):
    """Unity world matrices [f, n, 4, 4] of the skeleton's bones -> Unreal component-space [f, n, 4, 4] (cm), in the
    imported skeleton's bone axes"""
    out = np.zeros_like(Wu)
    for k in range(Wu.shape[1]):
        out[:, k, :3, :3] = A @ Wu[:, k, :3, :3] @ (A.T if is_root[k] else B)
        out[:, k, :3, 3] = (Wu[:, k, :3, 3] @ A.T) * 100.0
        out[:, k, 3, 3] = 1
    return out


def locals_of(W, parents):
    """component-space matrices -> local T, Q, S"""
    f, n = W.shape[:2]
    L = np.zeros_like(W)
    for i, p in enumerate(parents):
        L[:, i] = W[:, i] if p < 0 else np.linalg.inv(W[:, p]) @ W[:, i]
    T = L[..., :3, 3]
    Rs = L[..., :3, :3]
    S = np.linalg.norm(Rs, axis=-2)
    R = Rs / S[..., None, :]
    return T, hemisphere(mat2quat(R)), S


# ---- ch049 -> Sephiroth
MAP = {'C_Hip_a': 'hip', 'C_Spine_a': 'spine1', 'C_Spine_b': 'spine2', 'C_Spine_c': 'spine3', 'C_Spine_d': 'spine4',
       'C_Neck_a': 'neck', 'C_Head_a': 'head'}
AIM = {'C_Spine_a': ('C_Spine_b', 'spine2'), 'C_Spine_b': ('C_Spine_c', 'spine3'), 'C_Spine_c': ('C_Spine_d', 'spine4'),
       'C_Spine_d': ('C_Neck_a', 'neck'), 'C_Neck_a': ('C_Head_a', 'head')}
for s, u in (('L', 'left'), ('R', 'right')):
    MAP.update({s + '_Shoulder_a': u + '_shoulder', s + '_UpperArm_a': u + '_arm', s + '_Forearm_a': u + '_forearm',
                s + '_Hand_a': u + '_hand', s + '_UpperLeg_a': u + '_upleg', s + '_Foreleg_a': u + '_leg',
                s + '_Foot_a': u + '_foot', s + '_Toe_a': u + '_toe'})
    AIM.update({s + '_Shoulder_a': (s + '_UpperArm_a', u + '_arm'), s + '_UpperArm_a': (s + '_Forearm_a', u + '_forearm'),
                s + '_Forearm_a': (s + '_Hand_a', u + '_hand'), s + '_Hand_a': (s + '_Middle_a', u + '_hand_middle1'),
                s + '_UpperLeg_a': (s + '_Foreleg_a', u + '_leg'), s + '_Foreleg_a': (s + '_Foot_a', u + '_foot'),
                s + '_Foot_a': (s + '_Toe_a', u + '_toe')})
    for fs, fu in (('Thumb', 'thumb'), ('Index', 'index'), ('Middle', 'middle'), ('Ring', 'ring'), ('Pinky', 'pinky')):
        for k, l in enumerate('abc'):
            MAP['%s_%s_%s' % (s, fs, l)] = '%s_hand_%s%d' % (u, fu, k + 1)
        AIM['%s_%s_a' % (s, fs)] = ('%s_%s_b' % (s, fs), '%s_hand_%s2' % (u, fu))
        AIM['%s_%s_b' % (s, fs)] = ('%s_%s_c' % (s, fs), '%s_hand_%s3' % (u, fu))


def rest_match(SE, CH):
    out = SE.gq.copy()
    turn = {}
    for i, n in enumerate(SE.names):
        if n not in MAP:
            continue
        if n in AIM:
            s_child, c_child = AIM[n]
            u = SE.gt[SE.index[s_child]] - SE.gt[i]
            v = CH.gt[CH.index[c_child]] - CH.gt[CH.index[MAP[n]]]
            turn[n] = arc(u, v)
        else:
            p = SE.parents[i]
            turn[n] = turn.get(SE.names[p], np.array([0, 0, 0, 1.0])) if p >= 0 else np.array([0, 0, 0, 1.0])
        out[i] = qnorm(qmul(turn[n], SE.gq[i]))
    return out


def retarget(SE, CH, MATCHED, hip_scale, T, Q, S):
    """Sephiroth's local tracks for ch049's (T, Q, S local tracks on CH)"""
    nf = T.shape[0]
    r = CH.index['root']
    Tb, Qb = T.copy(), Q.copy()
    Tb[:, r], Qb[:, r] = CH.t[r], CH.q[r]                 # the body against the root at rest
    GQc, GTc, _ = fk(Qb, Tb, S, CH.parents)
    GQr, GTr, _ = fk(Q, T, S, CH.parents)                  # (for the root motion)
    nb = len(SE.names)
    LQ = np.repeat(SE.q[None], nf, 0)
    LT = np.repeat(SE.t[None], nf, 0)
    LS = np.repeat(SE.s[None], nf, 0)
    GQ, GT, GS = np.zeros((nf, nb, 4)), np.zeros((nf, nb, 3)), np.zeros((nf, nb, 3))
    hip_c = CH.index['hip']
    mw, sock = CH.index['main_weapon'], CH.index['left_hand_weapon']
    for i, n in enumerate(SE.names):
        p = SE.parents[i]
        if p < 0:
            GQ[:, i], GT[:, i], GS[:, i] = SE.q[i], SE.t[i], SE.s[i]
            continue
        if n in MAP:
            c = CH.index[MAP[n]]
            D = qmul(GQc[:, c], qinv(CH.gq[c])[None])
            GQ[:, i] = qnorm(qmul(D, np.repeat(MATCHED[i][None], nf, 0)))
            LQ[:, i] = qnorm(qmul(qinv(GQ[:, p]), GQ[:, i]))
        elif n == 'L_Weapon_a':
            # Sephiroth's socket where his hand now is, then ch049's sword's offset from his own socket
            sq = qmul(GQ[:, p], np.repeat(SE.q[i][None], nf, 0))
            st = GT[:, p] + qrot(GQ[:, p], np.repeat((SE.t[i] * 1.0)[None], nf, 0) * GS[:, p])
            Rq = qmul(GQc[:, mw], qinv(GQc[:, sock]))
            d = (GTc[:, mw] - GTc[:, sock]) * hip_scale
            GQ[:, i] = qnorm(qmul(Rq, sq))
            want = st + d
            LQ[:, i] = qnorm(qmul(qinv(GQ[:, p]), GQ[:, i]))
            LT[:, i] = qrot(qinv(GQ[:, p]), want - GT[:, p]) / GS[:, p]
        else:
            GQ[:, i] = qnorm(qmul(GQ[:, p], LQ[:, i]))
        if n == 'C_Hip_a':
            want = SE.gt[i] + (GTc[:, hip_c] - CH.gt[hip_c]) * hip_scale
            LT[:, i] = qrot(qinv(GQ[:, p]), want - GT[:, p]) / GS[:, p]
        GT[:, i] = GT[:, p] + qrot(GQ[:, p], LT[:, i] * GS[:, p])
        GS[:, i] = GS[:, p] * LS[:, i]
    # Trans: the root motion, as the game's clips carry it
    t = SE.index['Trans']
    fwd = qrot(GQr[:, r], np.array([1.0, 0, 0])[None].repeat(nf, 0))
    yaw = np.arctan2(fwd[:, 1], fwd[:, 0])
    qy = np.stack([np.zeros(nf), np.zeros(nf), np.sin(yaw / 2), np.cos(yaw / 2)], -1)
    LQ[:, t] = qnorm(qmul(qy, np.repeat(G[None], nf, 0)))
    LT[:, t] = GTr[:, r] * hip_scale
    return hemisphere(LQ), LT, LS, GT


def main(char_bundle, motion_bundle, model_dir, seph_bones, out):
    rig = U.load_rig(char_bundle)
    info = json.load(open(os.path.join(model_dir, 'model.json')))
    bones = info['bones']
    names = [b['name'] for b in bones]
    parents = [b['parent'] for b in bones]
    rig_of = [rig.index[n] for n in names]
    is_root = [b['parent'] < 0 for b in bones]
    # ch049's Unreal rest (the imported skeleton's reference pose: bind worlds, turned, mirrored, cm)
    Wb = np.array([np.array(b['world']) for b in bones])
    Wr = np.zeros_like(Wb)
    for k in range(len(bones)):
        R, tt = Wb[k, :3, :3], Wb[k, :3, 3]
        if not is_root[k]:
            R, tt = TZ @ R, TZ @ tt
        Wr[k, :3, :3] = M @ R @ M
        Wr[k, :3, 3] = M @ tt * 100.0
        Wr[k, 3, 3] = 1
    rT, rQ, rS = locals_of(Wr[None], parents)
    CH = Skel(names, parents, rQ[0], rT[0], rS[0])
    sb = json.load(open(seph_bones))
    SE = Skel([b[0] for b in sb['bones']], [b[1] for b in sb['bones']], [b[2] for b in sb['bones']],
              [b[3] for b in sb['bones']], [b[4] for b in sb['bones']])
    MATCHED = rest_match(SE, CH)
    hip_scale = SE.gt[SE.index['C_Hip_a']][2] / CH.gt[CH.index['hip']][2]
    report = {'hip_scale': round(float(hip_scale), 4), 'clips': {}}
    jobs = {'ch049': [], 'seph': []}
    for k, a in enumerate(U.clips(motion_bundle)):
        d = U.decode(a, rig)
        Wu = U.world(d['T'], d['Q'], d['S'], rig.parents)[:, rig_of]
        T, Q, S = locals_of(ue_world(Wu, rig_of, is_root), parents)
        job = 'job%02d' % (k // JOB)
        for kind in ('ch049', 'seph'):
            os.makedirs(os.path.join(out, kind, job), exist_ok=True)
            if job not in jobs[kind]:
                jobs[kind].append(job)
        write_cacanim(os.path.join(out, 'ch049', job, a.m_Name + '.cacanim'), names, d['fps'], Q, T, S, d['loop'])
        LQ, LT, LS, GT = retarget(SE, CH, MATCHED, hip_scale, T, Q, S)
        sname = a.m_Name.replace('anim_ch049_', 'PC0010_CH049_')
        write_cacanim(os.path.join(out, 'seph', job, sname + '.cacanim'), SE.names, d['fps'], LQ, LT, LS, d['loop'])
        GQc, GTc, _ = fk(Q, T, S, parents)
        lf, sf = CH.index['left_foot'], SE.index['L_Foot_a']
        report['clips'][a.m_Name] = dict(seph=sname, fps=d['fps'], frames=len(d['times']), loop=d['loop'],
                                         ch049_ankle_min_z=round(float(GTc[:, lf, 2].min()), 2), seph_ankle_min_z=round(float(GT[:, sf, 2].min()), 2),
                                         root_travel=[round(float(x), 1) for x in (T[-1, 0] - T[0, 0])])
    report['rest_ankles'] = dict(ch049=round(float(CH.gt[CH.index['left_foot']][2]), 2), seph=round(float(SE.gt[SE.index['L_Foot_a']][2]), 2))
    json.dump(jobs, open(os.path.join(out, 'jobs.json'), 'w'), indent=1)
    json.dump(report, open(os.path.join(out, 'report.json'), 'w'), indent=1)
    print(len(report['clips']), 'clips', report['hip_scale'], report['rest_ankles'])


if __name__ == '__main__':
    main(*sys.argv[1:])
