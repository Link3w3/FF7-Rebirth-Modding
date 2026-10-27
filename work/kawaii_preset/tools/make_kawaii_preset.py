"""Create a Character System: the Rebirth preset for KawaiiPhysics. It sets KawaiiPhysics up on a FINAL FANTASY VII
REBIRTH-style model (the game's own, or a Remake model on the same skeleton) from its bone names alone:

  * the chains: every physics chain the model has (its bones ending in _Phy; a chain's root is the _Phy bone whose parent
    is not one, its bones the root's _Phy descendants), a node each, sorted by what they are:
      hair (Hair*), long hair (HairLong* and any hair chain of 8 bones or more), coat (Coat*, Skirt*: the coat's tails),
      belt (Belt*), collar (Collar*, Eri*), wing (Feather*: the feathers of Sephiroth's wing), other;
  * each kind's settings: those tuned on Young Sephiroth (3.14.3: no flicker, the coat out of the legs, calm when running),
    each chain a little off them (stiffness, damping, world damping, gravity, limit), so no two strands swing as one;
  * the colliders each kind needs, sized from the model's mesh when it is given (its legs, back, neck, head, shoulder
    pads, in the reference pose), else from the skeleton: the legs as tapered capsules (thigh, calf) and the hips for the
    coat and belts; the head, neck, back and shoulders for the hair and collars;
  * the model's Bonamik (BNM) switched off while it is shown ("disable_bonamik"), KawaiiPhysics moving those bones instead.

    make_kawaii_preset.py --rig rig.json [--mesh body.npz] --model PATH [--model PATH ...] [--requires PAK ...]
                          [--bonamik true|NAME,...] --name TEXT --out entry.json
The rig: tools/mesh_bones.py's (component space); the mesh: tools/cooked_mesh.py's npz. The output is one "kawaii"
entry ({"kawaii": [entry]}); tools/merge_kawaii.py puts entries into one compat file."""
import argparse, hashlib, json, math, os, re, sys
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
import numpy as np

PRESET = 'rebirth'

# ---- each kind's settings (Young Sephiroth's, 3.14.3) -------------------------------------------------------
HAIR = dict(damping=0.25, stiffness=0.2, world_damping_location=0.85, world_damping_rotation=0.85, radius=0.75, limit_angle=35,
            stiffness_curve=[[0, 1.6], [1, 0.8]], dummy_bone_length=4, gravity=[0, 0, -150], teleport_rotation_threshold=30,
            use_fixed_substepping=False)
LONG_HAIR = dict(damping=0.28, stiffness=0.08, world_damping_location=0.88, world_damping_rotation=0.88, radius=1.2,
                 radius_curve=[[0, 0.8], [1, 1.2]], limit_angle=55, stiffness_curve=[[0, 2.0], [1, 0.6]], dummy_bone_length=6,
                 gravity=[0, 0, -320], teleport_rotation_threshold=30, use_fixed_substepping=False)
COAT = dict(damping=0.2, stiffness=0.05, world_damping_location=0.985, world_damping_rotation=0.95, radius=2.2, _wd_cap=0.99, _wd_spread=0.02,
            radius_curve=[[0, 0.45], [1, 1.0]], limit_angle=85, stiffness_curve=[[0, 1.8], [1, 0.7]], dummy_bone_length=10,
            gravity=[0, 0, -950], teleport_rotation_threshold=30, use_fixed_substepping=False,
            # (2026-10-25: gravity -700, was -450: the coat's lower half hangs down instead of flaring on from where the
            # thighs hold it out, half the flare standing; the adult coat's bones are 11 - 25 cm apart: two collision points between each two keep a leg from passing
            # between them)
            # (2026-10-26: gravity -950: with the strips tied (COAT_TIES) and the legs padded 1 cm, the coat hangs about 1 cm
            # further in than the 2026-10-25 file, its hem 1 - 1.2 cm)
            bone_subdivision_count=2, bone_subdivision_collision_only=True)
# (2026-10-25) The strands that hang down his front onto the chest (Rebirth's HairLongA - D, Remake's L/R_HairA and
# C_HairA/B): held closer to the animation and lagging less behind his moves than the back hair; loose as the long hair,
# a battle run's start pushed them back into his chest and neck (offline: 22 - 37 % of their vertex-frames over 2 cm deep)
FRONT_HAIR = dict(damping=0.35, stiffness=0.3, world_damping_location=0.97, world_damping_rotation=0.95, radius=1.2,
                  limit_angle=25, stiffness_curve=[[0, 1.4], [1, 0.8]], dummy_bone_length=4, gravity=[0, 0, -200],
                  teleport_rotation_threshold=30, use_fixed_substepping=False)
BELT = dict(damping=0.3, stiffness=0.15, world_damping_location=0.9, world_damping_rotation=0.9, radius=1.5, limit_angle=45,
            dummy_bone_length=4, gravity=[0, 0, -350], teleport_rotation_threshold=30, use_fixed_substepping=False)
COLLAR = dict(damping=0.3, stiffness=0.35, world_damping_location=0.9, world_damping_rotation=0.9, radius=1, limit_angle=20,
              dummy_bone_length=4, teleport_rotation_threshold=30, use_fixed_substepping=False)
WING = dict(damping=0.3, stiffness=0.2, world_damping_location=0.85, world_damping_rotation=0.85, radius=2.24, limit_angle=30,
            dummy_bone_length=12, gravity=[0, 0, -300], teleport_rotation_threshold=30, use_fixed_substepping=False)
OTHER = dict(COLLAR)
# (2026-10-26) Cloud's pants: short flaps on the trouser legs (two bones each, hung from the KineDriver's spokes on the
# thigh and the calf: his Bonamik's Bottom_L / Bottom_R): a little sway, held near the animation, kept out of the legs
PANTS = dict(damping=0.3, stiffness=0.4, world_damping_location=0.9, world_damping_rotation=0.9, radius=1.0, limit_angle=15,
             dummy_bone_length=3, gravity=[0, 0, -100], teleport_rotation_threshold=30, use_fixed_substepping=False)
FIT_SHAPES = set(os.environ.get('FIT_SHAPES', 'hair,long hair,front hair,collar,belt,other').split(','))
RADIUS_FROM_MESH = {'coat': (2.0, 7.0), 'belt': (1.0, 4.0), 'long hair': (1.0, 3.0), 'hair': (0.6, 3.0), 'front hair': (0.8, 3.0), 'collar': (1.0, 4.0)}
KINDS = {'hair': HAIR, 'long hair': LONG_HAIR, 'front hair': FRONT_HAIR, 'coat': COAT, 'belt': BELT, 'collar': COLLAR, 'wing': WING, 'pants': PANTS, 'other': OTHER}


def kind_of(root, length):
    part = re.match(r'^[LRC]_([A-Za-z]+)', root).group(1)
    if part.startswith('Feather'):
        return 'wing'
    if part.startswith('Coat') or part.startswith('Skirt'):
        return 'coat'
    if part.startswith('Belt'):
        return 'belt'
    if 'Pants' in part:
        return 'pants'
    if part.startswith('Collar') or part.startswith('Eri'):
        return 'collar'
    if part.startswith('Hair'):
        return 'long hair' if (part.startswith('HairLong') or length >= 8) else 'hair'
    return 'other'


# ---- quaternions (x, y, z, w), UE's conventions ----------------------------------------------------------
def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def qinv(q):
    return (-q[0], -q[1], -q[2], q[3])


def qrot(q, v):
    qv = q[:3]
    t = [2 * (qv[1] * v[2] - qv[2] * v[1]), 2 * (qv[2] * v[0] - qv[0] * v[2]), 2 * (qv[0] * v[1] - qv[1] * v[0])]
    c = [qv[1] * t[2] - qv[2] * t[1], qv[2] * t[0] - qv[0] * t[2], qv[0] * t[1] - qv[1] * t[0]]
    return [v[i] + q[3] * t[i] + c[i] for i in range(3)]


def from_rotator(pitch, yaw, roll):
    half = math.pi / 180.0 / 2.0
    p, y, rl = pitch * half, yaw * half, roll * half
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(rl), math.cos(rl)
    return (cr * sp * sy - sr * cp * cy, -cr * sp * cy - sr * cp * sy, cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy)


def rotator_for_z(d):
    n = math.sqrt(sum(c * c for c in d))
    dx, dy, dz = (c / n for c in d)
    pitch = math.degrees(math.atan2(math.hypot(dx, dy), dz))
    yaw = math.degrees(math.atan2(-dy, -dx)) if math.hypot(dx, dy) > 1e-9 else 0.0
    z = qrot(from_rotator(pitch, yaw, 0.0), [0, 0, 1])
    assert all(abs(z[i] - (dx, dy, dz)[i]) < 1e-4 for i in range(3)), (d, z)
    return [r(pitch, 2), r(yaw, 2), 0.0]


def r(x, n=3):
    return round(float(x), n)


class Rig:
    def __init__(self, path):
        data = json.load(open(path))
        self.bones = data['bones']
        self.by = {b['name']: b for b in self.bones}
        self.kids = {}
        for b in self.bones:
            if b['parent']:
                self.kids.setdefault(b['parent'], []).append(b['name'])

    def has(self, *names):
        return all(n in self.by for n in names)

    def local_point(self, bone, p):
        """A component-space point in `bone`'s space (the reference pose)."""
        b = self.by[bone]
        return qrot(qinv(b['q']), [p[i] - b['t'][i] for i in range(3)])

    def local_of(self, name, parent):
        return self.local_point(parent, self.by[name]['t'])

    def chains(self):
        out = []
        for b in self.bones:
            n = b['name']
            if n.endswith('_Phy') and not (b['parent'] and b['parent'].endswith('_Phy')):
                members, stack = [], [n]
                while stack:
                    x = stack.pop()
                    members.append(x)
                    stack.extend(k for k in self.kids.get(x, []) if k.endswith('_Phy'))
                depth = 1
                at = n
                while True:
                    nxt = [k for k in self.kids.get(at, []) if k.endswith('_Phy')]
                    if not nxt:
                        break
                    at = nxt[0]
                    depth += 1
                out.append((n, members, depth))
        return out


# ---- the body's sizes -----------------------------------------------------------------------------------
LEG_PAD_DEFAULT = '1.0'   # (2026-10-25: see measure(); 2026-10-26: 1, was 4: the tied strips' bridges keep the legs out of
# the cloth between strips, so the legs need no padding to hold the coat off them; the coat hangs closer to the legs)
DEFAULT_BODY = {   # Rebirth's Sephiroth (PC0010_00) as measured from his mesh (legs padded), for a model given without one
    'thigh_top': 17.74, 'thigh_knee': 14.48, 'calf_top': 12.66, 'calf_ankle': 10.49, 'back_low': 16.06, 'back_mid': 18.5, 'back_high': 20.64, 'hip_back': 19.46, 'neck_low': 6.29, 'neck_high': 9.1, 'head': [2.8, 0.0, 190.59, 8.71], 'pad': [-0.81, -19.86, 167.42, 11.58], 'thigh_len': 50.26,
}


def measure(rig, npz):
    import body_fit
    B = body_fit.Body(npz, rig=rig.by)
    out = dict(DEFAULT_BODY)

    def p90(L_out, ks, default):
        vals = [o[2] for k, o in enumerate(L_out) if o and k in ks]
        return max(vals) if vals else default

    th, ca = [], []
    for s in 'LR':
        if not rig.has(s + '_UpperLeg_a', s + '_Foreleg_a', s + '_Foot_a'):
            continue
        L, o = B.segment(s + '_UpperLeg_a', s + '_Foreleg_a', B.verts(r'^%s_(UpperLeg_a|Femoris[A-Z]_Spo|Knee_Spo)$' % s))
        th.append((p90(o, range(0, 7), DEFAULT_BODY['thigh_top']), p90(o, (8, 9), DEFAULT_BODY['thigh_knee'])))
        out['thigh_len'] = L
        L, o = B.segment(s + '_Foreleg_a', s + '_Foot_a', B.verts(r'^%s_(Foreleg_a|Calf[A-Z]?_Spo|Knee_Spo|Foot_a)$' % s))
        ca.append((p90(o, range(0, 6), DEFAULT_BODY['calf_top']), p90(o, (7, 8, 9), DEFAULT_BODY['calf_ankle'])))
    pad = float(os.environ.get('LEG_PAD', LEG_PAD_DEFAULT))   # (offline runs: the coat's cloth out of the thighs; 2026-10-25: 5 with thin coat bones, then 4
    # with the coat lagging less behind his moves and hanging heavier: it flares half as much standing and goes into his legs
    # no more running)
    if th:
        out['thigh_top'] = max(t for t, _ in th) + pad
        out['thigh_knee'] = max(k for _, k in th) + pad
    cpad = float(os.environ.get('CALF_PAD', '2.5'))
    if ca:
        out['calf_top'] = max(t for t, _ in ca) + cpad
        out['calf_ankle'] = max(k for _, k in ca) + cpad
    back = [-1, 0, 0]
    spine = B.verts(r'^C_(Spine_[a-d]|Hip_a|Spine1W_Spo|BeltRoot[A-Z]?_a)$')
    if rig.has('C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d', 'C_Neck_a', 'C_Hip_a'):
        L, o = B.segment('C_Spine_a', 'C_Spine_c', spine, toward=back)
        out['back_low'] = p90(o, range(10), out['back_low'])
        L, o = B.segment('C_Spine_c', 'C_Spine_d', spine, toward=back)
        out['back_mid'] = p90(o, range(10), out['back_mid'])
        L, o = B.segment('C_Spine_d', 'C_Neck_a', B.verts(r'^(C_Spine_d|C_Neck_a|[LR]_Shoulder_a|C_Collar.*)$'), toward=back)
        out['back_high'] = p90(o, range(10), out['back_high'])
        L, o = B.segment('C_Hip_a', 'C_Spine_a', B.verts(r'^C_(Hip_a|Spine_a)$'), toward=back)
        out['hip_back'] = p90(o, range(10), out['hip_back'])
    if rig.has('C_Neck_a', 'C_Head_a'):
        L, o = B.segment('C_Neck_a', 'C_Head_a', B.verts(r'^C_(Neck_a|Head_a)$'))
        out['neck_low'] = p90(o, range(1, 5), out['neck_low'])
        out['neck_high'] = p90(o, range(6, 10), out['neck_high'])
    if rig.has('C_Head_a'):
        c0 = np.array(rig.by['C_Head_a']['t'])
        head = B.verts(r'^C_Head_a$') & (B.pos[:, 2] > c0[2] + 3)
        H = B.pos[head]
        if len(H) > 50:
            A = np.c_[2 * H, np.ones(len(H))]
            f = (H ** 2).sum(1)
            sol = np.linalg.lstsq(A, f, rcond=None)[0]
            cen = sol[:3]
            out['head'] = [float(cen[0]), float(cen[1]), float(cen[2]), float(np.sqrt(sol[3] + cen @ cen))]
    if rig.has('L_ShoulderpadA_a'):
        m = B.verts(r'^L_ShoulderpadA_a$')
        Q = B.pos[m]
        if len(Q) > 50:
            c = Q.mean(0)
            out['pad'] = [float(c[0]), float(c[1]), float(c[2]), float(np.percentile(np.linalg.norm(Q - c, axis=1), 85))]
    return out


DEFAULT_LEGS_MESH = {'thigh_top': 13.74, 'thigh_knee': 10.48, 'calf_top': 10.16, 'calf_ankle': 7.99}   # (PC0010_00's mesh, unpadded)


def scaled_default(rig):
    """The default body scaled by the model's thigh length to Sephiroth's (the legs padded as LEG_PAD and CALF_PAD say,
    as a measured body's are)."""
    out = dict(DEFAULT_BODY)
    pad = float(os.environ.get('LEG_PAD', LEG_PAD_DEFAULT))
    cpad = float(os.environ.get('CALF_PAD', '2.5'))
    for k, v in DEFAULT_LEGS_MESH.items():
        out[k] = v + (pad if k.startswith('thigh') else cpad)
    if rig.has('L_UpperLeg_a', 'L_Foreleg_a'):
        a, b = rig.by['L_UpperLeg_a']['t'], rig.by['L_Foreleg_a']['t']
        L = math.dist(a, b)
        s = L / DEFAULT_BODY['thigh_len']
        for k, v in list(out.items()):
            if isinstance(v, float) and k != 'thigh_len':
                out[k] = v * s
        out['thigh_len'] = L
    return out


def chain_radii(B, rig, root, members):
    """Each bone's size from the mesh: how far the vertices skinned mostly to it reach from the chain's line (90 %),
    in chain order (the root first). None where a bone has too few vertices."""
    order = [root]
    at = root
    while True:
        nxt = [k for k in rig.kids.get(at, []) if k.endswith('_Phy')]
        if not nxt:
            break
        at = nxt[0]
        order.append(at)
    pts = np.array([rig.by[b]['t'] for b in order])
    out = []
    for b in order:
        m = B.domname == b
        Q = B.pos[m]
        if len(Q) < 8 or len(pts) < 2:
            out.append(None)
            continue
        best = np.full(len(Q), 1e9)
        for a, c in zip(pts, pts[1:]):
            ab = c - a
            t = np.clip((Q - a) @ ab / max(ab @ ab, 1e-9), 0, 1)
            best = np.minimum(best, np.linalg.norm(Q - (a + t[:, None] * ab), axis=1))
        out.append(float(np.percentile(best, 90)))
    return order, out


# ---- collider shapes -----------------------------------------------------------------------------------------
def capsule(rig, a, b, radius, skip=0.0, past=0.0, r_b=None):
    """A capsule (tapered when r_b is given: radius at a's end, r_b at b's) on bone a, along it to b's joint."""
    d = rig.local_of(b, a)
    length = math.sqrt(sum(c * c for c in d))
    u = [c / length for c in d]
    start = [u[i] * skip for i in range(3)]
    end = [d[i] + u[i] * past for i in range(3)]
    shape = {'bone': a, 'offset': [r((start[i] + end[i]) / 2) for i in range(3)], 'rotation': rotator_for_z(d),
             'length': r(length - skip + past, 2)}
    if r_b is None:
        shape['radius'] = r(radius, 2)
    else:
        shape['radius0'] = r(r_b, 2)   # KawaiiPhysics' radius0: its +Z end (b's)
        shape['radius1'] = r(radius, 2)
    return shape


def flattened(rig, shape, side):
    """A leg capsule as two, `side` cm in front of and behind its axis (his +X in the reference pose), each `side` cm
    thinner: as deep front to back, `side` cm narrower at its sides (the coat's side panels hang closer standing; the
    front and back panels, which the legs hit in a stride, are held off as far). The tapered capsules' order (thigh,
    calf) is kept: [front, back] for each."""
    if side <= 0:
        return [shape]
    bone = shape['bone']
    b = rig.by[bone]
    fwd = qrot(qinv(b['q']), [1.0, 0.0, 0.0])
    ax = qrot(from_rotator(*shape['rotation']), [0, 0, 1])
    d = sum(fwd[i] * ax[i] for i in range(3))
    f = [fwd[i] - d * ax[i] for i in range(3)]
    n = math.sqrt(sum(c * c for c in f))
    f = [c / n for c in f]
    out = []
    for sign in (1.0, -1.0):
        sh = dict(shape)
        sh['offset'] = [r(shape['offset'][i] + sign * side * f[i]) for i in range(3)]
        for k in ('radius', 'radius0', 'radius1'):
            if k in sh:
                sh[k] = r(max(1.0, sh[k] - side), 2)
        out.append(sh)
    return out


def sphere(rig, bone, point, radius):
    return {'bone': bone, 'offset': [r(c) for c in rig.local_point(bone, point)], 'radius': r(radius, 2)}


def cap_points(rig, bone, p0, p1, r0, r1):
    """A tapered capsule on `bone` between two points of the reference pose (component space): r0 at p0, r1 at p1."""
    a = rig.local_point(bone, p0)
    b = rig.local_point(bone, p1)
    d = [b[i] - a[i] for i in range(3)]
    length = math.sqrt(sum(c * c for c in d))
    return {'bone': bone, 'offset': [r((a[i] + b[i]) / 2) for i in range(3)], 'rotation': rotator_for_z(d), 'length': r(length, 2),
            'radius0': r(r1, 2), 'radius1': r(r0, 2)}   # (KawaiiPhysics' radius0: its +Z end, toward p1)


LEG_RANK = [('C_Hip_a', 0), ('C_Spine', 0), ('UpperLeg', 1), ('Foreleg', 2), ('Foot', 3), ('Toe', 4)]


def leg_rank(bone):
    for key, rank in LEG_RANK:
        if key in bone:
            return rank
    return 9


def bnm_leg_shapes(rig, bnm_path):
    """(LEGS=bnm) The legs and hips as the model's BNM has them for its cloth: its Col_leg capsules (two bodies each, a
    radius each), as KawaiiPhysics tapered capsules, each on the leg bone that moves it (the thigh's for hip-to-thigh and
    thigh-to-knee, the calf's below; the hips' own between the hips and the spine); the feet's left out."""
    d = json.load(open(bnm_path))
    bodies = {b['mName']: b for b in d['mBodies']}
    out = []
    for s in d['mShapes']:
        if s['mType'] != 'capsule' or len(s['mBodies']) != 2:
            continue
        b0, b1 = (bodies.get(n) for n in s['mBodies'])
        if not b0 or not b1 or b0['mGroupName'] != 'Col_leg' or b1['mGroupName'] != 'Col_leg':
            continue
        bones = [b0['mParentName'], b1['mParentName']]
        if not all(rig.has(b) for b in bones) or any('Toe' in b for b in bones) or all('Foot' in b for b in bones):
            continue
        ranks = [leg_rank(b) for b in bones]
        if min(ranks) == 0 and max(ranks) == 0:
            on = 'C_Hip_a' if 'C_Hip_a' in bones else bones[0]
        elif min(ranks) == 0:
            on = bones[ranks.index(max(ranks))]
        else:
            on = bones[ranks.index(min(ranks))]
        pts = []
        for b in (b0, b1):
            pb = rig.by[b['mParentName']]
            pts.append([pb['t'][i] + v for i, v in enumerate(qrot(pb['q'], b['m_LocalTransform']))])
        out.append(cap_points(rig, on, pts[0], pts[1], b0['m_Radius'] + LEG_BNM_PAD, b1['m_Radius'] + LEG_BNM_PAD))
    return out


LEG_BNM_PAD = float(os.environ.get('LEG_BNM_PAD', '0.5'))


# ---- the hair's body (2026-10-25): Square's own for Rebirth Sephiroth's hair, from his PC0010_00_BNM (offsets in each
# bone's own space, as the BNM keeps them): its Col_body (the front hair's: the spine's sphere pairs and the shoulders,
# capsules between them) and its arms (Col_arm for the front hair, Col_hairB_arm, a little bigger, for the back hair).
# Before, the hair had the spine capsules (15 - 19 cm about the spine) that the rest fit shrank to as little as 6.6 cm
# (the hair lies on the chest and the back): the chest and upper back were open, and in a battle run (leaning, the arms
# swinging) the front strands went into his chest (offline, tests/hair_check.py: up to 12 cm).
SQ_BODY = {
    'a+': ('C_Spine_a', (0.0, 0.0, 3.3), 11.0), 'a-': ('C_Spine_a', (0.0, 0.0, -3.3), 11.0),
    'b+': ('C_Spine_b', (0.0, 0.7, 4.6), 10.5), 'b-': ('C_Spine_b', (0.0, 0.7, -4.6), 10.5),
    'c+': ('C_Spine_c', (0.0, 0.8, 3.2), 11.5), 'c-': ('C_Spine_c', (0.0, 0.8, -3.2), 11.5),
    'd+': ('C_Spine_d', (5.5, 1.4, 8.4), 12.0), 'd-': ('C_Spine_d', (5.5, 1.4, -8.4), 12.0),
    'sR': ('R_Shoulder_a', (5.5, 0.0, 0.0), 8.0), 'sL': ('L_Shoulder_a', (5.5, 0.0, 0.0), 8.0),
}
# (each capsule on the first body's bone: + is his right, - his left)
SQ_BODY_CAPS = [('a+', 'b+'), ('a-', 'b-'), ('b+', 'c+'), ('b-', 'c-'), ('c+', 'c-'), ('c+', 'd+'), ('c-', 'd-'), ('d+', 'd-'),
                ('d+', 'sR'), ('d-', 'sL')]
SQ_ARMS = {   # kind -> capsules ((bone, offset, radius) at each end, on the first end's bone)
    'front': [(('{s}_Shoulder_a', (5.5, 0.0, 0.0), 8.0), ('{s}_UpperArm_a', (2.0, 0.0, 0.0), 9.25)),
              (('{s}_UpperArm_a', (2.0, 0.0, 0.0), 9.25), ('{s}_Forearm_a', (0.0, 0.0, '-0.9'), 6.0)),
              (('{s}_Forearm_a', (0.0, 0.0, '-0.9'), 6.0), ('{s}_Hand_a', (0.0, 0.0, 0.0), 4.5)),
              (('{s}_Hand_a', (0.0, 0.0, 0.0), 4.5), ('{s}_Hand_a', (8.2, 0.4, '0.3'), 4.0))],
    'back': [(('{s}_Shoulder_a', (5.0, 0.0, '-1.0'), 10.0), ('{s}_UpperArm_a', (0.0, 0.0, 0.0), 8.5)),
             (('{s}_UpperArm_a', (0.0, 0.0, 0.0), 8.5), ('{s}_Forearm_a', (0.0, 0.0, 0.0), 7.0)),
             (('{s}_Forearm_a', (0.0, 0.0, 0.0), 7.0), ('{s}_Hand_a', (0.0, 0.0, 0.0), 7.0)),
             (('{s}_Hand_a', (0.0, 0.0, 0.0), 7.0), ('{s}_Hand_a', (15.0, 0.0, 0.0), 7.0))],
}
NECK_FIT_LEAST = float(os.environ.get('NECK_FIT_LEAST', '0.9'))
HAIR_BODY = os.environ.get('HAIR_BODY', 'sq')   # ('spine': the old spine capsules)
BODY_FIT_LEAST = float(os.environ.get('BODY_FIT_LEAST', '0.9'))   # (the rest fit leaves the body and arms at least this much of their size)


def sq_point(rig, bone, offset):
    """A body's place in the reference pose (component space): its bone's place and turn, its offset in the bone's space."""
    b = rig.by[bone]
    return [b['t'][i] + v for i, v in enumerate(qrot(b['q'], offset))]


def sq_offset(side, offset):
    """An arm body's offset for a side: the BNM's left offsets as given ('-0.9' strings flip for the right: the BNM's
    right bodies have them the other way round)."""
    out = []
    for v in offset:
        if isinstance(v, str):
            v = float(v)
            out.append(v if side == 'L' else -v)
        else:
            out.append(v)
    return out


def hair_body(rig, arms):
    """The hair's body: the spine's capsules (and the shoulders) and the arms ('front' or 'back' sizes), as tapered
    capsules on their bones, each marked with the least the rest fit may leave of it."""
    out = []
    if all(rig.has(b) for b, _, _ in SQ_BODY.values()):
        for a, b in SQ_BODY_CAPS:
            (ba, oa, ra), (bb, ob, rb) = SQ_BODY[a], SQ_BODY[b]
            shape = cap_points(rig, ba, sq_point(rig, ba, oa), sq_point(rig, bb, ob), ra, rb)
            shape['_least'] = BODY_FIT_LEAST
            out.append(shape)
    if rig.has('C_Neck_a', 'C_Head_a'):   # (the BNM's neck, 6 cm to 5.3 - 5.8 at the head's joint: the measured one, 6.3 - 9.1 cm, held the
        # front strands off the jaw and the rest fit shrank it to 3.6 cm; they went through his neck)
        shape = cap_points(rig, 'C_Neck_a', sq_point(rig, 'C_Neck_a', (0.0, 0.0, 0.0)), sq_point(rig, 'C_Head_a', (0.0, 0.0, 0.0)), 6.0,
                           5.3 if arms == 'front' else 5.8)
        shape['_least'] = NECK_FIT_LEAST
        out.append(shape)
    for s in 'LR':
        for (ba, oa, ra), (bb, ob, rb) in SQ_ARMS[arms]:
            ba, bb = ba.format(s=s), bb.format(s=s)
            if not rig.has(ba, bb):
                continue
            shape = cap_points(rig, ba, sq_point(rig, ba, sq_offset(s, oa)), sq_point(rig, bb, sq_offset(s, ob)), ra, rb)
            shape['_least'] = BODY_FIT_LEAST
            out.append(shape)
    return out


def colliders(rig, body):
    """The shapes each kind needs: {'legs': {...}, 'hair': {...}, ...} as KawaiiPhysics limit lists."""
    legs_t, hips = [], []
    thighs_round = []
    side = float(os.environ.get('THIGH_SIDE', '0'))   # (2026-10-25: the thigh narrower at its sides, as deep front to back)
    cside = float(os.environ.get('CALF_SIDE', '0'))
    for s in 'LR':
        if rig.has(s + '_UpperLeg_a', s + '_Foreleg_a', s + '_Foot_a'):
            # (2026-10-26: from 8 cm below the hip joint, was 15: running, the top of the thigh came up into the front strips)
            thigh = capsule(rig, s + '_UpperLeg_a', s + '_Foreleg_a', body['thigh_top'], skip=float(os.environ.get('THIGH_SKIP', '8.0')), past=3.0, r_b=body['thigh_knee'])
            thighs_round.append(thigh)
            legs_t += flattened(rig, thigh, side)
            legs_t += flattened(rig, capsule(rig, s + '_Foreleg_a', s + '_Foot_a', body['calf_top'], r_b=body['calf_ankle']), cside)
            # the top of the thigh (the coat's top hangs over it): a sphere at the hip joint
            if os.environ.get('HIPS', 'joint') != 'bnm':
                hips.append(sphere(rig, s + '_UpperLeg_a', rig.by[s + '_UpperLeg_a']['t'], body['thigh_top'] * 0.95))
    if os.environ.get('HIPS', 'joint') == 'bnm' and rig.has('C_Hip_a'):
        # (Rebirth Sephiroth's PC0010_00_BNM: its Col_leg bodies on C_Hip_a, the hips' sides and the tops of the thighs;
        # offsets in C_Hip_a's own space, as the BNM keeps them)
        for off, rad in (([-5.6, -1.3, 8.6], 9.0), ([-5.6, -1.3, -8.6], 9.0), ([-3.5, 2.3, 6.8], 11.0), ([-3.5, 2.3, -6.4], 11.0)):
            hips.append({'bone': 'C_Hip_a', 'offset': off, 'radius': rad})
    back_caps = []
    if rig.has('C_Hip_a', 'C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d', 'C_Neck_a'):
        back_caps.append(capsule(rig, 'C_Hip_a', 'C_Spine_a', body['hip_back']))
        back_caps.append(capsule(rig, 'C_Spine_a', 'C_Spine_c', body['back_low']))
        back_caps.append(capsule(rig, 'C_Spine_c', 'C_Spine_d', body['back_mid']))
        back_caps.append(capsule(rig, 'C_Spine_d', 'C_Neck_a', body['back_high'] * 0.92))
    neck_caps, head_sph = [], []
    if rig.has('C_Neck_a', 'C_Head_a'):
        neck_caps.append(capsule(rig, 'C_Neck_a', 'C_Head_a', body['neck_low'], r_b=body['neck_high']))
        hx, hy, hz, hr = body['head']
        head_sph.append(sphere(rig, 'C_Head_a', [hx, hy, hz], hr))
        # the face and jaw below the cranium
        c = rig.by['C_Head_a']['t']
        head_sph.append(sphere(rig, 'C_Head_a', [hx + 2.0, hy, (hz + c[2]) / 2 - 2.0], hr * 0.82))
    pads = []
    px, py, pz, pr = body['pad']
    for s, sy in (('L', 1.0), ('R', -1.0)):
        bone = s + '_ShoulderpadA_a' if rig.has(s + '_ShoulderpadA_a') else (s + '_Shoulder_a' if rig.has(s + '_Shoulder_a') else None)
        if bone:
            pads.append(sphere(rig, bone, [px, py * sy, pz], pr))
    out = {'legs_tapered': legs_t, 'thighs': thighs_round, 'hips': hips, 'back': back_caps, 'neck': neck_caps, 'head': head_sph, 'pads': pads}
    if rig.has('C_Hip_a', 'C_Spine_a'):   # (the coat's own: the BNM's hips are 9 - 11 cm; the mesh's p90 pushed the coat's back out)
        out['coat_back'] = [capsule(rig, 'C_Hip_a', 'C_Spine_a', float(os.environ.get('COAT_BACK_R', '11.0')))]
    if os.environ.get('LEGS') == 'bnm':
        out['legs_bnm'] = bnm_leg_shapes(rig, os.environ['BNM_JSON'])
    out['hair_body_front'] = hair_body(rig, 'front')
    out['hair_body_back'] = hair_body(rig, 'back')
    return out


def shapes_for(kind, C):
    sph, cap, tap = [], [], []
    if kind in ('hair', 'front hair', 'long hair', 'collar', 'other'):
        sph += C['head'] + C['pads']
        body = C['hair_body_back' if kind == 'long hair' else 'hair_body_front'] if kind in ('hair', 'front hair', 'long hair') and HAIR_BODY == 'sq' else []
        if body:   # (2026-10-25: Square's neck, body and arms for the hair)
            tap += body
        else:
            cap += [c for c in C['neck'] if 'radius' in c]
            tap += [c for c in C['neck'] if 'radius0' in c]
            cap += C['back'][-2:] if kind != 'long hair' else C['back']
    if kind == 'long hair':
        sph += C['hips']
        tap += C['thighs']   # the thighs (sitting, running)
    if kind == 'pants':
        tap += C['legs_tapered']
    if kind in ('coat', 'belt'):
        if 'legs_bnm' in C:   # (the BNM's legs and hips: its own hip capsules too)
            tap += C['legs_bnm']
        else:
            if os.environ.get('COAT_HIPS', '0') == '1':   # (2026-10-25: off: they pushed the coat's top out, the coat flared)
                sph += C['hips']
            tap += C['legs_tapered']
        if os.environ.get('COAT_BACK', '1') == '1':   # (the hips' back: keeps the coat's back from folding in)
            cap += C.get('coat_back') or C['back'][:1]
    out = {}
    if sph:
        out['spheres'] = sph
    if cap:
        out['capsules'] = cap
    if tap:
        out['tapered_capsules'] = tap
    return out


WD_CAP = float(os.environ.get('WD_CAP', '0.97'))
WD_SPREAD = float(os.environ.get('WD_SPREAD', '0.16'))


def spread(root, salt):
    h = hashlib.md5((root + '/' + salt).encode('utf-8')).digest()
    return int.from_bytes(h[:4], 'little') / 2 ** 32


def node(kind, root, base, shapes):
    s = dict(base)
    s['stiffness'] = r(base['stiffness'] * (0.7 + 0.6 * spread(root, 'stiffness')), 4)
    s['damping'] = r(base['damping'] * (0.75 + 0.5 * spread(root, 'damping')), 4)
    for key in ('world_damping_location', 'world_damping_rotation'):
        s[key] = r(min(base.get('_wd_cap', WD_CAP), max(0.3, base[key] + (spread(root, key) - 0.5) * base.get('_wd_spread', WD_SPREAD))), 4)
    if 'gravity' in base:
        s['gravity'] = [0, 0, r(base['gravity'][2] * (0.75 + 0.5 * spread(root, 'gravity')), 1)]
    if base.get('limit_angle'):
        s['limit_angle'] = r(base['limit_angle'] * (0.85 + 0.3 * spread(root, 'limit')), 2)
    n = {'name': kind + ' ' + root.replace('_a_Phy', ''), 'root_bone': root}
    n.update({k: v for k, v in s.items() if not k.startswith('_')})
    n.update(shapes)
    return n


def curve_at(curve, x):
    if not curve:
        return 1.0
    pts = sorted(curve)
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / max(x1 - x0, 1e-9)
    return pts[-1][1]


def shape_parts(rig, n):
    """The node's shapes in component space (the reference pose): ('sphere', c, r) / ('capsule', a, b, r_a, r_b)."""
    out = []
    for sh in n.get('spheres', []):
        b = rig.by[sh['bone']]
        c = [b['t'][i] + v for i, v in enumerate(qrot(b['q'], sh['offset']))]
        out.append(('sphere', np.array(c), sh['radius']))
    for key in ('capsules', 'tapered_capsules'):
        for sh in n.get(key, []):
            b = rig.by[sh['bone']]
            c = np.array([b['t'][i] + v for i, v in enumerate(qrot(b['q'], sh['offset']))])
            ax = np.array(qrot(b['q'], qrot(from_rotator(*sh['rotation']), [0, 0, 1])))
            half = sh['length'] / 2
            r0 = sh.get('radius0', sh.get('radius'))   # +Z end
            r1 = sh.get('radius1', sh.get('radius'))   # -Z end
            out.append(('capsule', c - ax * half, c + ax * half, r1, r0))
    return out


def clearance(p, parts):
    best = 1e9
    for part in parts:
        if part[0] == 'sphere':
            best = min(best, float(np.linalg.norm(p - part[1]) - part[2]))
        else:
            _, a, b, ra, rb = part
            ab = b - a
            t = float(np.clip((p - a) @ ab / max(ab @ ab, 1e-9), 0, 1))
            best = min(best, float(np.linalg.norm(p - (a + t * ab)) - (ra + (rb - ra) * t)))
    return best


def fit_to_rest(rig, n, margin=0.3, floor=0.3):
    """Each bone's radius at most its room in the reference pose (its distance to the nearest of the node's shapes less
    a margin): no bone starts inside a shape (one that did was thrown out of it as the chain started, and the chain
    hung off its pose). Returns the bones it made smaller."""
    parts = shape_parts(rig, n)
    if not parts:
        return 0
    order = [n['root_bone']]
    at = order[0]
    while True:
        nxt = [k for k in rig.kids.get(at, []) if k.endswith('_Phy')]
        if not nxt:
            break
        at = nxt[0]
        order.append(at)
    if len(order) < 2:
        return 0
    top = n['radius']
    vals = []
    changed = 0
    for k, b in enumerate(order):
        x = k / (len(order) - 1)
        want = top * curve_at(n.get('radius_curve'), x)
        room = clearance(np.array(rig.by[b]['t']), parts) - margin
        if k > 0 and room < want:   # (the root does not move)
            want = max(floor, room)
            changed += 1
        vals.append(want)
    if changed:
        new_top = max(vals[1:])
        n['radius'] = r(new_top, 2)
        n['radius_curve'] = [[r(k / (len(order) - 1), 3), r(v / new_top, 3)] for k, v in enumerate(vals)]
    return changed


def fit_shapes_to_rest(rig, n, margin=0.5, least=0.35):
    """The node's shapes made smaller where its bones are, in the reference pose, closer to them than their radius (the
    shape would throw them out as the chain starts and hold the chain off its pose: hair standing off the head). Each
    shape's radii scaled down so every bone below the root clears it by its radius and a margin; not below `least` of
    their size. Returns how many shapes it changed."""
    order = [n['root_bone']]
    at = order[0]
    while True:
        nxt = [k for k in rig.kids.get(at, []) if k.endswith('_Phy')]
        if not nxt:
            break
        at = nxt[0]
        order.append(at)
    if len(order) < 2:
        return 0
    bones = []
    for k, b in enumerate(order[1:], 1):
        rb = n['radius'] * curve_at(n.get('radius_curve'), k / (len(order) - 1))
        bones.append((np.array(rig.by[b]['t']), rb))
    changed = 0
    for key in ('spheres', 'capsules', 'tapered_capsules'):
        new = []
        for sh in n.get(key, []):
            part = shape_parts(rig, {key: [sh]})[0]
            scale = 1.0
            for p, rb in bones:
                if part[0] == 'sphere':
                    need = float(np.linalg.norm(p - part[1])) - rb - margin
                    have = part[2]
                else:
                    _, a, b, ra, rb2 = part
                    ab = b - a
                    t = float(np.clip((p - a) @ ab / max(ab @ ab, 1e-9), 0, 1))
                    need = float(np.linalg.norm(p - (a + t * ab))) - rb - margin
                    have = ra + (rb2 - ra) * t
                if have > 1e-6 and need < have:
                    scale = min(scale, max(sh.get('_least', least), need / have))
            sh = dict(sh)
            sh.pop('_least', None)
            if scale < 0.999:
                changed += 1
                for rk in ('radius', 'radius0', 'radius1'):
                    if rk in sh:
                        sh[rk] = r(sh[rk] * scale, 2)
            new.append(sh)
        if new:
            n[key] = new
    return changed


FRONT_STRANDS = os.environ.get('FRONT_STRANDS', '1') == '1'

# (2026-10-26) The coat's strips tied in pairs: the strips each side whose letters are named here ("A-B": L_SkirtA with
# L_SkirtB, R_SkirtA with R_SkirtB; "A-B,B-C" ties A, B and C) go into one node, their bones kept at their distance level by
# level (XPBD bone constraints, KawaiiPhysics' skirt strands) with collision points along each constraint ("bridges",
# bone_constraint_subdivision_count) whose pushes move both strips. Untied, the cloth between two strips collided with
# nothing: walking forward, the front of each thigh (between the front strip, A, and the strip beside it, B: 53 degrees,
# 20 cm apart at the hem) went through it (Remake Sephiroth's N_Walk01_1 on the winged model, offline: 2.7 % of the coat's
# vertex-frames inside a leg, all of them skinned to two strips). The other strips stay a node each.
# (the defaults: each side's front strip with the one beside it (A-B) and the back two (D-E), and the back middle strip
# with both back strips beside it (LE-CA, CA-RE); the sides (B-C, C-D) and the coat's front opening (LA-RA) stay free)
COAT_TIES = [t.split('-') for t in os.environ.get('COAT_TIES', 'A-B,D-E,LE-CA,CA-RE').split(',') if '-' in t]
COAT_BRIDGES = int(os.environ.get('COAT_BRIDGES', '3'))
COAT_COMPLIANCE = os.environ.get('COAT_COMPLIANCE', '')


def tie_coat(rig, nodes):
    """The coat's tied strips (COAT_TIES, pairs of strips: "A-B" is each side's A with its B, "LE-CA" the left E with the
    centre's A) merged into one node a group of tied strips: the first strip's node (its settings) with the others as
    additional roots, constraints between each tied pair's bones level by level (below the roots, which follow the
    animation) and bridges along them. Returns the nodes (the tied strips' own nodes gone) and the merged nodes' names."""
    if not COAT_TIES:
        return nodes, []
    def strip_of(root):
        m = re.match(r'^([LRC])_(Coat|Skirt)([A-Z]+)_a_Phy$', root)
        return (m.group(1), m.group(2), m.group(3)) if m else None
    def members(root):
        order, at = [root], root
        while True:
            nxt = [k for k in rig.kids.get(at, []) if k.endswith('_Phy')]
            if not nxt:
                return order
            at = nxt[0]
            order.append(at)
    by_root = {n['root_bone']: n for n in nodes}
    kinds = sorted({strip_of(r)[1] for r in by_root if strip_of(r)})
    pairs = []
    for kind in kinds:
        def root_of(token, side):
            if len(token) >= 2 and token[0] in 'LRC' and token[1:].isalpha() and token[1:].isupper():
                return '%s_%s%s_a_Phy' % (token[0], kind, token[1:])
            return '%s_%s%s_a_Phy' % (side, kind, token)
        for a, b in COAT_TIES:
            for side in ('LR' if not (a[0] in 'LRC' and len(a) >= 2) else 'X'):
                ra, rb = root_of(a, side), root_of(b, side)
                if ra in by_root and rb in by_root and (ra, rb) not in pairs:
                    pairs.append((ra, rb))
    groups = []
    for ra, rb in pairs:
        hit = [g for g in groups if ra in g or rb in g]
        g = [x for h in hit for x in h]
        for x in (ra, rb):
            if x not in g:
                g.append(x)
        groups = [h for h in groups if h not in hit] + [g]
    merged, gone = [], set()
    for g in groups:
        n = dict(by_root[g[0]])
        n['name'] = 'coat ' + '+'.join(x.replace('_a_Phy', '') if k == 0 else (strip_of(x)[0] + strip_of(x)[2]) for k, x in enumerate(g))
        n['additional_root_bones'] = g[1:]
        ex = [b for x in g for b in by_root[x].get('exclude_bones', [])]
        if ex:
            n['exclude_bones'] = sorted(set(ex))
        cons = []
        for ra, rb in pairs:
            if ra in g and rb in g:
                ma, mb = members(ra), members(rb)
                cons += [[x, y] for x, y in zip(ma[1:], mb[1:])]
        n['bone_constraints'] = cons
        if COAT_BRIDGES:
            n['bone_constraint_subdivision_count'] = COAT_BRIDGES
            n['bone_constraint_subdivision_feedback_scale'] = 1.0
        if COAT_COMPLIANCE:
            n['bone_constraint_global_compliance'] = COAT_COMPLIANCE
        merged.append((g, n))
        gone.update(g)
    out = []
    for n in nodes:
        hit = [m for g, m in merged if n['root_bone'] in g]
        if hit:
            if hit[0] not in out:
                out.append(hit[0])
        else:
            out.append(n)
    return out, [m['name'] for _, m in merged]


def is_front_strand(rig, root):
    """A hair chain that hangs down his front past the neck (onto the chest): its bones in front of the body (+X) on
    average and its end below the neck's joint."""
    if not rig.has('C_Neck_a'):
        return False
    order = [root]
    at = root
    while True:
        nxt = [k for k in rig.kids.get(at, []) if k.endswith('_Phy')]
        if not nxt:
            break
        at = nxt[0]
        order.append(at)
    pts = [rig.by[b]['t'] for b in order]
    return len(order) >= 5 and sum(p[0] for p in pts) / len(pts) > 3.0 and pts[-1][2] < rig.by['C_Neck_a']['t'][2]


def build(rig, body, name, models, requires, bonamik, measured=None, kinedriver=None):
    C = colliders(rig, body)
    nodes, counts = [], {}
    order = ['hair', 'front hair', 'long hair', 'collar', 'coat', 'belt', 'wing', 'pants', 'other']
    chains = rig.chains()
    roots = {c[0] for c in chains}
    chains.sort(key=lambda c: (order.index(kind_of(c[0], c[2])), c[0]))
    carriers = []
    for root, members, depth in chains:
        kind = kind_of(root, depth)
        if kind in ('hair', 'long hair') and FRONT_STRANDS and is_front_strand(rig, root):
            kind = 'front hair'
        # the bones below the chain that are not physics bones (a spoke, a part's own bones): left out of the node
        # (KawaiiPhysics moves every bone below its root), with what hangs from them
        exclude = [k for mb in members for k in rig.kids.get(mb, []) if not k.endswith('_Phy')]
        under, stack = set(), list(exclude)
        while stack:
            x = stack.pop()
            if x in roots:
                under.add(x)
            stack.extend(rig.kids.get(x, []))
        if under:
            # a chain other chains hang from (Sephiroth's C_CoatAA, the front panels' carrier): its Bonamik keeps it on
            # the animation, and so does this
            carriers.append(root)
            continue
        n = node(kind, root, KINDS[kind], shapes_for(kind, C))
        if exclude:
            n['exclude_bones'] = sorted(exclude)
        radii = (measured or {}).get(root)
        if radii and kind in RADIUS_FROM_MESH and not (kind == 'coat' and os.environ.get('COAT_RADIUS_FROM_MESH', '0') == '0'):
            lo, hi = RADIUS_FROM_MESH[kind]
            vals = [min(hi, max(lo, v)) for v in radii if v is not None]
            if vals:
                top = max(vals)
                n['radius'] = r(top, 2)
                keys = [[r(k / max(1, len(radii) - 1), 3), r(min(hi, max(lo, v)) / top, 3)] for k, v in enumerate(radii) if v is not None]
                n['radius_curve'] = keys if len(keys) > 1 else [[0, 1.0], [1, 1.0]]
        if os.environ.get('FIT_REST', '0') == '1':
            fit_to_rest(rig, n)
        if kind in FIT_SHAPES:
            fit_shapes_to_rest(rig, n)
        for key in ('spheres', 'capsules', 'tapered_capsules'):   # (the fit's marks never go into the file)
            if key in n:
                n[key] = [{k: v for k, v in sh.items() if not k.startswith('_')} for sh in n[key]]
        nodes.append(n)
        counts[kind] = counts.get(kind, 0) + 1
    nodes = group_pants(nodes)
    nodes, tied = tie_coat(rig, nodes)
    if tied:
        counts['(coat strips tied: %s)' % ', '.join(tied)] = 0
    assert len(nodes) <= 64, ('more than 64 chains', len(nodes))
    if carriers:
        counts['(carriers kept on the animation: %s)' % ', '.join(carriers)] = 0
    entry = {'name': name, 'models': models}
    if requires:
        entry['requires_paks'] = requires
    if bonamik:
        entry['disable_bonamik'] = True if bonamik == ['true'] else bonamik
    if kinedriver:   # (3.14.5: the model's KDIs write the chains' bones after KawaiiPhysics)
        entry['disable_kinedriver'] = True if kinedriver == ['true'] else kinedriver
    entry['preset'] = PRESET
    entry['nodes'] = nodes
    return entry, counts, C


def group_pants(nodes):
    """(2026-10-26) The pants' flaps, a node per trouser leg and height (Cloud's 32 two-bone chains: L/R x thigh/calf),
    each node simulating its chains from its root bone and additional root bones: a model's nodes stay within the mod's
    64 (Cloud: 44 hair strands and 4 pants nodes)."""
    out, groups = [], {}
    for n in nodes:
        if not n['name'].startswith('pants '):
            out.append(n)
            continue
        m = re.match(r'^([LRC])_(Stdb|Stdu|b|u)?', n['root_bone'])
        key = (m.group(1), {'b': 'Stdb', 'u': 'Stdu'}.get(m.group(2), m.group(2))) if m else (n['root_bone'], None)
        g = groups.get(key)
        if g is None:
            g = dict(n)
            g['name'] = 'pants %s_%s' % key if key[1] else n['name']
            g['additional_root_bones'] = []
            groups[key] = g
            out.append(g)
        else:
            g['additional_root_bones'].append(n['root_bone'])
            if n.get('exclude_bones'):
                g['exclude_bones'] = sorted(set(g.get('exclude_bones', [])) | set(n['exclude_bones']))
    for g in groups.values():
        if not g['additional_root_bones']:
            del g['additional_root_bones']
    return out


def tune_from_env():
    """(tests) KIND_KEY=value overrides from the environment, e.g. COAT_bone_subdivision_count=2."""
    for kind, base in (('HAIR', HAIR), ('LONG_HAIR', LONG_HAIR), ('FRONT_HAIR', FRONT_HAIR), ('COAT', COAT), ('BELT', BELT), ('COLLAR', COLLAR), ('WING', WING)):
        for k, v in os.environ.items():
            if k.startswith(kind + '__'):
                key = k[len(kind) + 2:]
                base[key] = json.loads(v)


def main():
    tune_from_env()
    ap = argparse.ArgumentParser()
    ap.add_argument('--rig', required=True)
    ap.add_argument('--mesh')
    ap.add_argument('--model', action='append', required=True)
    ap.add_argument('--requires', action='append', default=[])
    ap.add_argument('--bonamik', default='true')
    ap.add_argument('--kinedriver', default='true', help='KDIs to take off the model (3.14.5): true, names, or false')
    ap.add_argument('--name', required=True)
    ap.add_argument('--radii-from')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    rig = Rig(a.rig)
    body = measure(rig, a.mesh) if a.mesh else scaled_default(rig)
    for k, v in os.environ.items():   # (BODY__thigh_top=9: a measured size replaced, e.g. by the model's BNM's)
        if k.startswith('BODY__') and k[6:] in body:
            body[k[6:]] = json.loads(v)
    bonamik = [] if a.bonamik in ('', 'false') else a.bonamik.split(',')
    measured = {}
    if a.mesh:
        import body_fit
        B = body_fit.Body(a.mesh, rig=rig.by)
        for root, members, depth in rig.chains():
            measured[root] = chain_radii(B, rig, root, members)[1]
        json.dump(measured, open(a.out[:-5] + '.radii.json', 'w'), indent=0)
    elif a.radii_from:
        measured = json.load(open(a.radii_from))
    kinedriver = [] if a.kinedriver in ('', 'false') else a.kinedriver.split(',')
    entry, counts, C = build(rig, body, a.name, a.model, a.requires, bonamik, measured, kinedriver)
    doc = {'schema': 'RebirthSkelCompat/1',
           'note': 'KawaiiPhysics from the Rebirth preset (Create a Character System): ' + a.name,
           'kawaii': [entry]}
    with open(a.out, 'w', encoding='utf-8', newline='\r\n') as f:
        json.dump(doc, f, indent=1)
        f.write('\n')
    json.dump({k: (r(v, 2) if isinstance(v, float) else [r(x, 2) for x in v] if isinstance(v, list) else v) for k, v in body.items()},
              open(a.out[:-5] + '.body.json', 'w'), indent=1)
    print('%s: %d nodes (%s); body %s' % (a.out, len(entry['nodes']), ', '.join('%d %s' % (n, k) for k, n in counts.items()),
          ', '.join('%s %s' % (k, ('%.1f' % v) if isinstance(v, float) else v) for k, v in body.items() if k != 'thigh_len')))


if __name__ == '__main__':
    main()
