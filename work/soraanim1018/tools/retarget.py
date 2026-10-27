"""Cloud's cooked field animations (Neutral00, Neutral20) onto Sora's KH3 skeleton (PC0000_00_S_Skeleton), as key
animations (.cacanim) for Create a Character System's Import Key Animations.

  decode   the clip's ACL data (acl13) on Cloud's skeleton (PC0000_00_Skeleton), ref pose for bones without tracks
  transfer for every mapped Sora bone, Cloud's bone's component-space rotation change from its rest pose, applied to
           Sora's bone in a rest pose turned to point its bones the way Cloud's rest bones point (so the A-poses meet);
           Sora keeps his own bone lengths. The hips (center) take Cloud's pelvis travel (scaled by the hip heights), the
           root (kh_sk) takes Cloud's root (Trans) motion as it is (the game moves the character by it), turned through
           kh_sk's own rest rotation (KH3's axes) and keeping its 0.01 scale
  keep     every other Sora bone (hair, hood, coat tails, face, the Keyblade bones) at its rest pose
Bone names (KH3): koshi hips, hara1 spine, mune chest, kubi neck, atama head, kata shoulder, ude1 arm, ude2 elbow, te
wrist, momo leg, sune knee, ashi1 ankle, ashi2 toe, yubiA thumb, B index, C middle, D ring, E little (the user's
KHModelScript); center is the parent of koshi and hara1.
    retarget.py <pkgs dir> <out dir>"""
import glob
import json
import os
import struct
import sys

import numpy as np

sys.path[:0] = ['/work/acl']
import acl13  # noqa: E402

DATA = '/work/sora1018/data'

MAP = {   # Sora bone <- Cloud bone
    'center': 'C_Hip_a', 'hara1': 'C_Spine_a', 'hara2': 'C_Spine_b', 'mune': 'C_Spine_d', 'kubi': 'C_Neck_a',
    'atama': 'C_Head_a',
}
for s, c in (('L', 'L'), ('R', 'R')):
    MAP.update({
        s + '_kata': c + '_Shoulder_a', s + '_ude1': c + '_UpperArm_a', s + '_ude2': c + '_Forearm_a', s + '_te': c + '_Hand_a',
        s + '_momo': c + '_UpperLeg_a', s + '_sune': c + '_Foreleg_a', s + '_ashi1': c + '_Foot_a', s + '_ashi2': c + '_Toe_a',
    })
    for kh3, cl in (('A', 'Thumb'), ('B', 'Index'), ('C', 'Middle'), ('D', 'Ring'), ('E', 'Pinky')):
        for n, l in ((1, 'a'), (2, 'b'), (3, 'c')):
            MAP['%s_yubi%s%d' % (s, kh3, n)] = '%s_%s_%s' % (c, cl, l)
# the bone each one points at (rest-pose direction), Sora side and Cloud side
AIM = {'hara1': ('hara2', 'C_Spine_b'), 'hara2': ('mune', 'C_Spine_d'), 'mune': ('kubi', 'C_Neck_a'),
       'kubi': ('atama', 'C_Head_a')}
for s in 'LR':
    AIM.update({s + '_kata': (s + '_ude1', s + '_UpperArm_a'), s + '_ude1': (s + '_ude2', s + '_Forearm_a'),
                s + '_ude2': (s + '_te', s + '_Hand_a'), s + '_te': (s + '_yubiC1', s + '_Middle_a'),
                s + '_momo': (s + '_sune', s + '_Foreleg_a'), s + '_sune': (s + '_ashi1', s + '_Foot_a'),
                s + '_ashi1': (s + '_ashi2', s + '_Toe_a')})
    for kh3, cl in (('A', 'Thumb'), ('B', 'Index'), ('C', 'Middle'), ('D', 'Ring'), ('E', 'Pinky')):
        AIM['%s_yubi%s1' % (s, kh3)] = ('%s_yubi%s2' % (s, kh3), '%s_%s_b' % (s, cl))
        AIM['%s_yubi%s2' % (s, kh3)] = ('%s_yubi%s3' % (s, kh3), '%s_%s_c' % (s, cl))


# ---- quaternions [x, y, z, w], Hamilton product (a * b: b first, then a), as Unreal composes bone rotations
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
    tx = 2 * (y * vz - z * vy)
    ty = 2 * (z * vx - x * vz)
    tz = 2 * (x * vy - y * vx)
    return np.stack([vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx)], -1)


def qnorm(q):
    return q / np.linalg.norm(q, axis=-1, keepdims=True)


def arc(u, v):
    """The shortest rotation taking direction u onto direction v."""
    u = u / np.linalg.norm(u)
    v = v / np.linalg.norm(v)
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


class Skeleton:
    def __init__(self, path, root_scale_one=False):
        bones = json.load(open(path))
        if root_scale_one:
            # Sora's Skeleton asset keeps a 0.01 scale on kh_sk, but his mesh and every animation he plays have 1 there
            # (KH3's Battle00 clips: kh_sk scale 1). Its rest rotation (-0.5, 0.5, -0.5, 0.5) stands him up facing +X like
            # Cloud (the KH3 clips' (-0.7071, 0, 0, 0.7071) faces him +Y): the root keeps that rest rotation here.
            bones[0] = dict(bones[0], s=[1.0, 1.0, 1.0])
        self.names = [b['name'] for b in bones]
        self.parents = [b['parent'] for b in bones]
        self.index = {n: i for i, n in enumerate(self.names)}
        self.q = np.array([b['q'] for b in bones], dtype=np.float64)
        self.t = np.array([b['t'] for b in bones], dtype=np.float64)
        self.s = np.array([b.get('s', [1, 1, 1]) for b in bones], dtype=np.float64)
        assert all(p < i for i, p in enumerate(self.parents)), 'parents come first'
        self.gq, self.gt, self.gs = fk(self.q[None], self.t[None], self.s[None], self.parents)
        self.gq, self.gt, self.gs = self.gq[0], self.gt[0], self.gs[0]


def fk(LQ, LT, LS, parents):
    """Component space of local arrays [frames, bones, ...] (uniform scale is enough for both skeletons)."""
    GQ = np.zeros_like(LQ)
    GT = np.zeros_like(LT)
    GS = np.zeros_like(LS)
    for i, p in enumerate(parents):
        if p < 0:
            GQ[:, i], GT[:, i], GS[:, i] = LQ[:, i], LT[:, i], LS[:, i]
        else:
            GQ[:, i] = qmul(GQ[:, p], LQ[:, i])
            GT[:, i] = GT[:, p] + qrot(GQ[:, p], LT[:, i] * GS[:, p])
            GS[:, i] = GS[:, p] * LS[:, i]
    return GQ, GT, GS


CLOUD = Skeleton(os.path.join(DATA, 'cloud_bones.json'))
SORA = Skeleton(os.path.join(DATA, 'sora_bones.json'), root_scale_one=True)


def track_map(data, n):
    pat = struct.pack('<i', n)
    p = data.find(pat)
    while p >= 0:
        if p + 4 + 4 * n <= len(data):
            vals = struct.unpack_from('<%di' % n, data, p + 4)
            if all(0 <= v < len(CLOUD.names) for v in vals) and len(set(vals)) == n and vals[0] == 0:
                return list(vals)
        p = data.find(pat, p + 1)
    raise ValueError('no track map')


def decode(data):
    c = acl13.Clip(data)
    rot, trans, scale = c.decompress()
    bones = track_map(data, c.num_bones)
    S = c.num_samples
    LQ = np.repeat(CLOUD.q[None], S, 0)
    LT = np.repeat(CLOUD.t[None], S, 0)
    for k, b in enumerate(bones):
        LQ[:, b] = rot[:, k]
        LT[:, b] = trans[:, k]
    return c.sample_rate, S, qnorm(LQ), LT


def rest_match():
    """Sora's component-space rest rotations, each mapped bone turned to point the way its Cloud bone points at rest
    (bones without an aim keep their parent's turn)."""
    turn = {}
    out = SORA.gq.copy()
    for i, n in enumerate(SORA.names):
        if n not in MAP:
            continue
        if n in AIM:
            s_child, c_child = AIM[n]
            u = SORA.gt[SORA.index[s_child]] - SORA.gt[i]
            v = CLOUD.gt[CLOUD.index[c_child]] - CLOUD.gt[CLOUD.index[MAP[n]]]
            turn[n] = arc(u, v)
        else:
            p = SORA.parents[i]
            turn[n] = turn.get(SORA.names[p], np.array([0, 0, 0, 1.0])) if p >= 0 else np.array([0, 0, 0, 1.0])
        out[i] = qnorm(qmul(turn[n], SORA.gq[i]))
    return out, turn


MATCHED, TURNS = rest_match()
HIP_SCALE = SORA.gt[SORA.index['center']][2] / CLOUD.gt[CLOUD.index['C_Hip_a']][2]


def retarget(LQc, LTc):
    """Sora's local tracks for Cloud's clip. The game's clips carry the root (Trans) as root motion only: its rotation
    is the yaw times GAME_ROOT_Q (-0.5, 0.5, -0.5, 0.5), an exporter's axis change, and the body under it is posed
    against the root's rest (identity for Cloud), so the pose is taken with the root at rest and the root track is
    passed on as it is. Sora's mesh has that same GAME_ROOT_Q as kh_sk's rest (scale 1), so his body is posed against
    it and his kh_sk track is Cloud's Trans track."""
    S = LQc.shape[0]
    root_c = CLOUD.index['Trans']
    LQr, LTr = LQc.copy(), LTc.copy()
    LQr[:, root_c] = CLOUD.q[root_c]
    LTr[:, root_c] = CLOUD.t[root_c]
    GQc, GTc, _ = fk(LQr, LTr, np.ones(LTr.shape), CLOUD.parents)
    nb = len(SORA.names)
    LQ = np.repeat(SORA.q[None], S, 0)
    LT = np.repeat(SORA.t[None], S, 0)
    LS = np.repeat(SORA.s[None], S, 0)
    GQ = np.zeros((S, nb, 4))
    GT = np.zeros((S, nb, 3))
    GS = np.zeros((S, nb, 3))
    hip_c = CLOUD.index['C_Hip_a']
    for i, n in enumerate(SORA.names):
        p = SORA.parents[i]
        if p < 0:   # kh_sk: posed at its rest; its track is Cloud's root track
            GQ[:, i] = SORA.q[i]
            GT[:, i] = SORA.t[i]
            GS[:, i] = SORA.s[i]
            continue
        if n in MAP:
            c = CLOUD.index[MAP[n]]
            D = qmul(GQc[:, c], qinv(CLOUD.gq[c])[None])
            GQ[:, i] = qnorm(qmul(D, np.repeat(MATCHED[i][None], S, 0)))
            LQ[:, i] = qnorm(qmul(qinv(GQ[:, p]), GQ[:, i]))
        else:
            GQ[:, i] = qnorm(qmul(GQ[:, p], LQ[:, i]))
        if n == 'center':   # the hips' travel: Cloud's pelvis offset, scaled by the hip heights
            want = SORA.gt[i] + (GTc[:, hip_c] - CLOUD.gt[hip_c]) * HIP_SCALE
            LT[:, i] = qrot(qinv(GQ[:, p]), want - GT[:, p]) / GS[:, p]
        GT[:, i] = GT[:, p] + qrot(GQ[:, p], LT[:, i] * GS[:, p])
        GS[:, i] = GS[:, p] * LS[:, i]
    LQ[:, 0] = LQc[:, root_c]
    LT[:, 0] = LTc[:, root_c]
    # keep each quaternion track on one hemisphere (no flips between frames)
    for i in range(nb):
        q = LQ[:, i]
        for f in range(1, S):
            if np.dot(q[f], q[f - 1]) < 0:
                q[f] = -q[f]
    return LQ, LT, LS, GT


def write_cacanim(path, fps, LQ, LT, LS, loop):
    """'CACANIM1', u32 version 1, f32 fps, i32 frames, u32 flags (1 = loop), i32 tracks, then per track u16 name length +
    name, i32 keys (1 or frames), keys x (T xyz, Q xyzw, S xyz) float32 (Unreal axes, local to the parent bone)."""
    S = LQ.shape[0]
    tracks = []
    for i, n in enumerate(SORA.names):
        T, Q, Sc = LT[:, i], LQ[:, i], LS[:, i]
        const = (np.abs(T - T[:1]).max() < 1e-4 and np.abs(Q - Q[:1]).max() < 1e-6 and np.abs(Sc - Sc[:1]).max() < 1e-6)
        if const:
            T, Q, Sc = T[:1], Q[:1], Sc[:1]
        tracks.append((n, T, Q, Sc))
    with open(path, 'wb') as f:
        f.write(b'CACANIM1')
        f.write(struct.pack('<IfiIi', 1, float(fps), S, 1 if loop else 0, len(tracks)))
        for n, T, Q, Sc in tracks:
            nb = n.encode('ascii')
            f.write(struct.pack('<H', len(nb)) + nb)
            f.write(struct.pack('<i', len(T)))
            f.write(np.concatenate([T, Q, Sc], -1).astype('<f4').tobytes())
    return len(tracks)


def main(pkgs, out):
    report = {}
    sets = os.environ.get('SETS', 'Neutral*')
    kind = os.environ.get('KIND', 'Player')   # Player: Motion/Player/PC0000_Cloud/<set>; FieldAction, Level: Motion/<kind>/<set>/PC0000_Cloud
    files = []
    for pat in sets.split(','):
        if kind == 'Player':
            files += glob.glob(os.path.join(pkgs, 'Motion__Player__PC0000_Cloud__%s__*.uasset' % pat))
        else:
            files += glob.glob(os.path.join(pkgs, 'Motion__%s__%s__PC0000_Cloud__*.uasset' % (kind, pat)))
    for f in sorted(set(files)):
        parts = os.path.basename(f)[:-7].split('__')
        if kind == 'Player':
            sset, name = parts[-2], parts[-1]
        else:
            sset, name = parts[2], parts[-1]
        data = open(f, 'rb').read()
        try:
            fps, S, LQc, LTc = decode(data)
        except Exception as e:
            report['%s/%s' % (sset, name)] = 'ERROR %s' % e
            continue
        LQ, LT, LS, GT = retarget(LQc, LTc)
        odir = os.path.join(out, sset) if kind == 'Player' else os.path.join(out, kind, sset)
        os.makedirs(odir, exist_ok=True)
        loop = name.endswith('_1') or 'Loop' in name
        n = write_cacanim(os.path.join(odir, name + '.cacanim'), fps, LQ, LT, LS, loop)
        # feet height at the lowest frame vs Cloud's (a sanity number)
        fl = min(GT[:, SORA.index['L_ashi1'], 2].min(), GT[:, SORA.index['R_ashi1'], 2].min())
        report['%s/%s' % (sset, name)] = dict(fps=fps, frames=S, tracks=n, sora_ankle_min_z=round(float(fl), 2))
    json.dump(report, open(os.path.join(out, 'report_%s%s.json' % ('' if kind == 'Player' else kind + '_', sets.replace('*', '').replace(',', '_'))), 'w'), indent=1)
    return report


if __name__ == '__main__':
    r = main(sys.argv[1], sys.argv[2])
    errs = {k: v for k, v in r.items() if isinstance(v, str)}
    print(len(r), 'clips,', len(errs), 'errors')
    for k, v in list(errs.items())[:10]:
        print(' ', k, v)
