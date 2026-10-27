"""Sora's HSF lip maps (Cloud_Default / Cloud_Loud / Cloud_Smile, the ones Cloud's animation blueprint names), from his
KH3 mouth shapes, as JSON for the editor (make_lipmaps.py), plus a contact sheet of every viseme as the game would pose it.

How the game reads a lip map (from Cloud's): each shape lists, per bone, the bone's local transform (relative to its
parent) in a right-handed copy of Unreal's axes (Y negated): TranslateX/Y/Z = (x, -y, z) of the local translation,
RotateX/Y/Z = Euler angles in degrees (rotate X, then Y, then Z) of the local rotation mirrored the same way; channels a
shape leaves out are the DefaultShape's. Cloud's DefaultShape is exactly his reference pose read that way (C_Chin
(0, 4.713, 8.936) -> TranslateY -4.713), and his open jaw is RotateX +14.8 (front of the jaw down).

    python3 build_lipmaps.py <out.json> [sheet.png]
"""
import json
import sys
import numpy as np
sys.path[:0] = ['/work/soraface']
import facerender as fr
import build_poses as B
import lipmap

CLOUD = '/work/fx1018/pkgs/LipSync__LipMap__Player__PC0000_Cloud__Cloud_%s.uasset'
MOUTH = ['CU_lip', 'RU_lip', 'LU_lip', 'RU_cor', 'LU_cor', 'RD_cor', 'LD_cor', 'C_jaw', 'CD_lip', 'RD_lip', 'LD_lip',
         'CD_teeth', 'CU_teeth', 'C_chin', 'C_tongroot', 'C_tongtip', 'R_cheek_a', 'L_cheek_a', 'R_cheek_b', 'L_cheek_b',
         'R_puff', 'L_puff', 'C_nose', 'R_nose', 'L_nose']
CORNERS = ['RU_cor', 'LU_cor', 'RD_cor', 'LD_cor', 'R_cheek_a', 'L_cheek_a', 'R_cheek_b', 'L_cheek_b', 'R_puff', 'L_puff']
VISEMES = {          # Cloud's shape -> (KH3 animation, frame)
    'aa': ('F_0052M', 0),     # open, jaw 12 degrees
    'bmp': ('F_0001EM', 0),   # lips closed
    'ee': ('F_0004M', 6),     # wide, teeth, a little open
    'fv': ('F_0050M', 0),     # barely open
    'ln': ('F_0051M', 0),     # a little open
    'oo': ('F_0002M', 3),     # rounded, lips forward
    'sh': ('F_0004M', 11),    # teeth, lips forward
}
LOUD_AA = ('F_0004M', 0)      # Loud: a wider aa, the rest opened 15% more
CHANNELS = ['TranslateX', 'TranslateY', 'TranslateZ', 'RotateX', 'RotateY', 'RotateZ', 'ScaleX', 'ScaleY', 'ScaleZ']
M = np.diag([1.0, -1.0, 1.0])


def qmat(q):
    return fr.qmat(np.asarray(q, np.float64) / np.linalg.norm(q))


def mat_q(R):
    """rotation matrix -> quaternion (x, y, z, w)"""
    t = np.trace(R)
    if t > 0:
        s = np.sqrt(t + 1.0) * 2
        w = 0.25 * s; x = (R[2, 1] - R[1, 2]) / s; y = (R[0, 2] - R[2, 0]) / s; z = (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        w = (R[2, 1] - R[1, 2]) / s; x = 0.25 * s; y = (R[0, 1] + R[1, 0]) / s; z = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        w = (R[0, 2] - R[2, 0]) / s; x = (R[0, 1] + R[1, 0]) / s; y = 0.25 * s; z = (R[1, 2] + R[2, 1]) / s
    else:
        s = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        w = (R[1, 0] - R[0, 1]) / s; x = (R[0, 2] + R[2, 0]) / s; y = (R[1, 2] + R[2, 1]) / s; z = 0.25 * s
    q = np.array([x, y, z, w])
    return q / np.linalg.norm(q)


def euler_xyz(R):
    """R = Rz(g) Ry(b) Rx(a) -> (a, b, g) degrees"""
    b = np.arcsin(np.clip(-R[2, 0], -1, 1))
    a = np.arctan2(R[2, 1], R[2, 2])
    g = np.arctan2(R[1, 0], R[0, 0])
    return np.degrees([a, b, g])


def rot_xyz(a, b, g):
    a, b, g = np.radians([a, b, g])
    Rx = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    Ry = np.array([[np.cos(b), 0, np.sin(b)], [0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
    Rz = np.array([[np.cos(g), -np.sin(g), 0], [np.sin(g), np.cos(g), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def to_lip(q, t):
    R = M @ qmat(q) @ M
    rx, ry, rz = euler_xyz(R)
    return {'TranslateX': float(t[0]), 'TranslateY': float(-t[1]), 'TranslateZ': float(t[2]),
            'RotateX': float(rx), 'RotateY': float(ry), 'RotateZ': float(rz), 'ScaleX': 1.0, 'ScaleY': 1.0, 'ScaleZ': 1.0}


def from_lip(a):
    R = M @ rot_xyz(a['RotateX'], a['RotateY'], a['RotateZ']) @ M
    return mat_q(R), np.array([a['TranslateX'], -a['TranslateY'], a['TranslateZ']])


def pose_of(name, f):
    return B.mix(B.IDLE, B.frame(name, f), MOUTH)


def scaled(pose, base, k):
    """base + k * (pose - base) on the mouth bones"""
    out = dict(base)
    for b in MOUTH:
        q0, t0 = base[b]; q1, t1 = pose[b]
        out[b] = (B.slerp(q0, q1, k) if k <= 1 else extrap(q0, q1, k), t0 + k * (t1 - t0))
    return out


def extrap(q0, q1, k):
    d = fr.qmul(q1, fr.qinv(q0))
    if d[3] < 0:
        d = -d
    ang = 2 * np.arccos(np.clip(d[3], -1, 1))
    if ang < 1e-9:
        return q1
    axis = d[:3] / np.sin(ang / 2)
    a = ang * k
    dk = np.array([*(axis * np.sin(a / 2)), np.cos(a / 2)])
    return fr.qmul(dk, q0)


def add_delta(pose, base, delta_pose, bones):
    """pose with (delta_pose - base) added on bones"""
    out = dict(pose)
    for b in bones:
        q0, t0 = base[b]; qd, td = delta_pose[b]
        dq = fr.qmul(qd, fr.qinv(q0))
        q, t = pose[b]
        out[b] = (fr.qmul(dq, q), t + (td - t0))
    return out


def attrs(pose):
    return {b: to_lip(*pose[b]) for b in MOUTH}


def diff(shape, default):
    out = {}
    for b, a in shape.items():
        d = default[b]
        keep = {}
        for c in CHANNELS:
            tol = 0.05 if c.startswith('Rotate') else (1e-4 if c.startswith('Scale') else 2e-3)
            if abs(a[c] - d[c]) > tol:
                keep[c] = a[c]
        if keep:
            out[b] = keep
    return out


def max_difference(shapes, default):
    out = {}
    for b in default:
        for c in CHANNELS:
            best = 0.0
            for s in shapes.values():
                v = s.get(b, {}).get(c)
                if v is not None and abs(v - default[b][c]) > abs(best):
                    best = v - default[b][c]
            if abs(best) > 1e-6:
                out.setdefault(b, {})[c] = best
    return out


def cloud_params(kind):
    p, cls, v = lipmap.read(CLOUD % kind)
    d = {k: lipmap.plain(x) for k, x in v.value.items()}
    params = {s: {k: sh[k] for k in sh if k != 'Attributes'} for s, sh in d['Shapes']}
    default = {k: d['DefaultShape'][k] for k in d['DefaultShape'] if k != 'Attributes'}
    return d['Version'], params, default


def build():
    base = B.IDLE
    smile = B.POSES['F_Smile01']
    maps = {}
    for kind in ('Default', 'Loud', 'Smile'):
        version, params, dparams = cloud_params(kind)
        poses = {s: pose_of(*VISEMES[s]) for s in VISEMES}
        default_pose = base
        if kind == 'Loud':
            poses = {s: scaled(p, base, 1.15) for s, p in poses.items()}
            poses['aa'] = pose_of(*LOUD_AA)
        if kind == 'Smile':
            poses = {s: add_delta(p, base, smile, CORNERS) for s, p in poses.items()}
            default_pose = add_delta(base, base, smile, CORNERS)
        default = attrs(default_pose)
        full = {s: attrs(p) for s, p in poses.items()}
        shapes = {s: diff(full[s], default) for s in VISEMES}
        maps['Cloud_' + kind] = dict(version=version, default=default, default_params=dparams,
                                     shapes={s: dict(attributes=shapes[s], params=params[s]) for s in VISEMES},
                                     max_difference=max_difference(shapes, default),
                                     poses={s: {b: (list(map(float, q)), list(map(float, t))) for b, (q, t) in p.items() if b in MOUTH} for s, p in poses.items()})
    return maps


def check_round_trip(maps):
    """every shape, read back the way the game reads it, is the pose it came from"""
    worst = 0.0
    for name, m in maps.items():
        for s, sh in m['shapes'].items():
            for b in MOUTH:
                a = dict(m['default'][b]); a.update(sh['attributes'].get(b, {}))
                q, t = from_lip(a)
                q0, t0 = m['poses'][s][b]
                dq = 2 * np.degrees(np.arccos(min(1, abs(float(np.dot(q, q0))))))
                worst = max(worst, dq, float(np.linalg.norm(t - np.array(t0))) * 10)
    return worst


def sheet(maps, path):
    F = fr.Face()
    ims = []
    for name in ('Cloud_Default', 'Cloud_Loud', 'Cloud_Smile'):
        m = maps[name]
        for s in ['default'] + list(VISEMES):
            pose = dict(B.IDLE)
            for b in MOUTH:
                a = dict(m['default'][b])
                if s != 'default':
                    a.update(m['shapes'][s]['attributes'].get(b, {}))
                pose[b] = from_lip(a)
            ims.append(F.render(pose, scale=15, box=(-6.5, 6.5, 134.5, 149.0), label='%s %s' % (name[6:], s)))
    return fr.sheet(ims, 8, path)


if __name__ == '__main__':
    maps = build()
    print('round trip worst (deg / 0.1 units):', round(check_round_trip(maps), 4))
    out = {k: {kk: vv for kk, vv in v.items() if kk != 'poses'} for k, v in maps.items()}
    json.dump(out, open(sys.argv[1], 'w'), indent=1)
    for k, v in out.items():
        print(k, {s: len(sh['attributes']) for s, sh in v['shapes'].items()}, 'maxdiff bones', len(v['max_difference']))
    if len(sys.argv) > 2:
        print(sheet(maps, sys.argv[2]))
