"""PC0010_18's Kawaii Dynamic Motions (Create a Character System's "kawaii" entry for his model on Rebirth's bones, from
pc18_rerig.py's npz), with Neo Bahamut BlackFeeler's own motion on his wings and tail:

  * his wings and tail move as Neo Bahamut's do: each node's "pose_animation" is a loop of Neo Bahamut's own motion (the
    game's /Game/Motion/Summon/SU2050_NeoBahamut/Neutral00/N_Idle01_1: the summon's hovering idle, 6 s, its wings
    breathing, their blades and thrusters flexing, its tail swaying) on the same bones (his wing and tail bones are Neo
    Bahamut's, their frames Neo Bahamut's own), additive (each bone turns by what Neo Bahamut's turns from the loop's
    first frame: his wings and tail keep the shape the model gives them), the physics on top (a little lag and sway behind
    his moves). Three nodes a side for the wings: the wing arm (WingArmRoot: the long jointed arm with its blades and
    fingers), the blade wing (WingARoot: the six thrusters and the two short blades), the upper wing (WingBRoot: the
    clawed upper wing over his head and the membrane that hangs from it); the tail one node, kept out of his legs and off
    the floor;
  * the crest (Neo Bahamut's tentacle bones, the long spike back from his headdress; Neo Bahamut's motions do not move
    it): stiff, a slight slow wave;
  * his hair (Rebirth Sephiroth's, the Rebirth preset's own settings for each strand): kept off his head (the preset's
    head shapes), off the armour of his back and chest (spheres just inside its surface where the hair lies), off his
    shoulders and arms, the wing arms' shafts beside his head and, for the long hair, his legs. Each shape is shrunk
    where a strand's bone sits inside it at rest (nothing is pushed out standing still). Strands the model does not
    skin (no weights) are left out.
The model has no Bonamik of its own (a skin's model): disable_bonamik for safety.
    make_pc18_kawaii.py <rerig.npz> <model object path> <out dir> [clip, default Neutral00__N_Idle01_1]
        writes rig.json (component space, for the offline runs) and entry.json (the compat file's one entry)"""
import json
import os
import sys
import numpy as np
sys.path[:0] = ['/work/kawaii_preset/tools', '/work/pc18', '/work/ccseph/tools', '/work/bfs17']
from make_kawaii_preset import Rig, capsule, cap_points, sphere, r
from make_bfs_kawaii import write_rig, fit_to_rest, chain_bones, shape_dist
import anim_zen as A

SIDES = ('L', 'R')
NB_SKELETON = '/work/pc18/nb/game/Character__Summon__SU2050_00_NeoBahamut_Standard__Model__SU2050_00_Skeleton.uasset'
NB_MOTION = '/work/pc18/nb/game/Motion__Summon__SU2050_NeoBahamut__%s.uasset'
CLIP = 'Neutral00__N_Idle01_1'
# the parts held as Neo Bahamut holds them in the loop (his pose and moves), the rest only moved as he moves (additive)
ABSOLUTE = set(x for x in os.environ.get('PC18_ABSOLUTE', '').split(',') if x)
# (game mod 3.20.0) the wings and tail play Neo Bahamut's own animation sets: the motion of the name of what Sephiroth
# plays, else the pair below; his own pose (from Neo Bahamut's reference pose: the model's wing and tail bones are in it)
NB_SETS = ['/Game/Motion/Summon/SU2050_NeoBahamut/Neutral00.Neutral00', '/Game/Motion/Summon/SU2050_NeoBahamut/Battle00.Battle00',
           '/Game/Motion/Summon/SU2050_NeoBahamut/Battle00_Boss.Battle00_Boss']
NB_MOTIONS = [
    # standing, moving (the field's walks and runs are the AnimBlueprint's, no montage: "moving" picks then)
    ('N_Idle*', 'N_Idle01_1'), ('N_MenuIdle*', 'N_Idle01_1'), ('B_Idle*', 'B_Idle01_1'), ('B_Run*', 'B_Walk01_1'), ('N_Run*', 'B_Walk01_1'),
    ('N_Walk*', 'B_Walk01_1'), ('N_Dash*', 'B_Walk01_1'), ('N_Accel*', 'B_Walk01_1'), ('B_StrafingWalk*', 'B_Walk01_1'),
    ('N_ClimbOver*', 'B_Walk01_1'), ('N_Over*', 'B_Walk01_1'), ('N_Jump*', 'B_Warp01_0'), ('N_Fall*', 'B_Warp01_0'), ('B_Fall*', 'B_Warp01_0'),
    ('N_MenuAct*', 'N_Act01_0'), ('N_MenuPTIN*', 'N_Act01_1'), ('N_ItemCure*', 'B_EnergyCharge01_0'), ('N_MagCure*', 'B_EnergyCharge01_0'),
    # his attacks: the Square chain, the jumping ones, the strong ones, parries
    ('B_NAttack01*', 'B_AtkBladeCombo01_0'), ('B_NAttack02*', 'B_AtkSpinSlash01'), ('B_NAttack03*', 'B_AtkUpperSlash01_0'),
    ('B_NAttack04*', 'B_AtkKickCombo01'), ('B_NAttack2*', 'B_AtkJumpSlash01'), ('B_NAttackJ*', 'B_AtkJumpSlash01'), ('B_NPAttack*', 'B_AtkStinger01_0'),
    ('B_SAttack*', 'B_AtkWingAttack01_0'), ('B_ParryAttack*', 'B_AtkTailSpinR01_1'),
    # abilities, limits, magic, items
    ('B_AtkWarp*', 'B_Warp01_0'), ('B_AtkSFlare*', 'B_AtkBreathMove01_0'), ('B_AtkLimit*', 'B_AtkSatelliteCanon01_0'),
    ('B_AtkBurst*', 'B_EnergyCharge01_0'), ('B_Atk*', 'B_AtkNeoHeavyStilke01'), ('B_MagAttack*', 'B_AtkStunLaser01_0'),
    ('B_MagCure*', 'B_EnergyCharge01_0'), ('B_Item*', 'B_ModeChange01'), ('B_Chain*', 'B_EnergyCharge01_1'), ('B_Win*', 'B_ModeChange01'),
    # dodges, guards
    ('B_Avoid*', 'B_Warp02_0'), ('B_Step*', 'B_Warp02_0'), ('B_GuardTurn*', 'B_ModeChange02'), ('B_Guard*', 'B_ModeChange02'),
    # hits he has and Neo Bahamut does not (the ones both have play by their name)
    ('*_Add', 'B_DmgF01'), ('B_DmgF02', 'B_DmgF01'), ('B_DmgB02', 'B_DmgB01'), ('B_DmgBlow*', 'B_DmgF03_0'), ('B_DmgStrike*', 'B_DmgF03_0'),
    ('B_DmgUpper*', 'B_DmgB03_0'), ('B_DmgDownB*', 'B_DmgDownF01_0'), ('B_DmgRecover*', 'B_DmgDownF01_2'), ('B_DmgReflect*', 'B_DmgF01'),
    ('B_DmgGuard*', 'B_DmgF01'), ('B_Abnormal*', 'B_DmgF03_1'), ('B_DownAbnormal*', 'B_DmgDownF01_1'), ('B_DownDie*', 'B_Die01_1'),
    ('B_Die01_2', 'B_Die01_1'),
]
NB_ANIMSET = dict(sets=NB_SETS, motions=dict(NB_MOTIONS), idle='N_Idle01_1', battle_idle='B_Idle01_1', moving='B_Walk01_1', moving_speed=40,
                  blend_seconds=0.3, additive=True, additive_base='reference_pose')
USE_ANIMSET = os.environ.get('PC18_ANIMSET', '1') == '1'
HAIR_PRESET = '/work/kawaii_preset/out/SephirothKawaii.json'
SHAPES = ('spheres', 'capsules', 'tapered_capsules', 'boxes', 'planes', 'bone_constraints')
BODY_SLOTS = ('SU2050_02_UnderFlow', 'SU2050_02_BodyAFlow', 'SU2050_02_NeckFlow', 'SU2050_02_ArmFlow')
SURFACE_SLOTS = ('SU2050_02_UnderFlow', 'SU2050_02_BodyAFlow', 'SU2050_02_NeckFlow')

# the tail: Neo Bahamut's sway, the physics a little behind it (stiffer at the root, looser toward the tip)
TAIL = dict(damping=0.22, stiffness=0.22, world_damping_location=0.9, world_damping_rotation=0.9, radius=8.0,
            radius_curve=[[0, 1.1], [1, 0.6]], limit_angle=20, limit_angle_curve=[[0, 0.5], [1, 1.5]],
            stiffness_curve=[[0, 1.7], [1, 0.6]], damping_curve=[[0, 1.0], [1, 0.8]], dummy_bone_length=0,
            gravity=[0, 0, -200], teleport_rotation_threshold=30, use_fixed_substepping=False)
CREST = dict(damping=0.3, stiffness=0.45, world_damping_location=0.95, world_damping_rotation=0.95, radius=3.0, limit_angle=8,
             stiffness_curve=[[0, 1.5], [1, 0.8]], dummy_bone_length=0, gravity=[0, 0, -60], teleport_rotation_threshold=30,
             use_fixed_substepping=False)
CREST_WAVES = [dict(axis=[0, 0, 1], degrees=1.2, seconds=4.6, phase_per_bone=14.0, degrees_curve=[[0, 0.3], [1, 1.0]])]
# the wings: stiff (armoured, bladed: they hold their shape), following the motion with a little lag; a light gravity
WING = {
    'wing arm': dict(damping=0.2, stiffness=0.3, world_damping_location=0.92, world_damping_rotation=0.9, radius=4.0, limit_angle=14,
                     stiffness_curve=[[0, 1.4], [1, 0.8]], dummy_bone_length=0, gravity=[0, 0, -60], teleport_rotation_threshold=30,
                     use_fixed_substepping=False),
    'blade wing': dict(damping=0.16, stiffness=0.25, world_damping_location=0.9, world_damping_rotation=0.88, radius=4.0, limit_angle=18,
                       stiffness_curve=[[0, 1.4], [1, 0.7]], dummy_bone_length=0, gravity=[0, 0, -60], teleport_rotation_threshold=30,
                       use_fixed_substepping=False),
    'upper wing': dict(damping=0.2, stiffness=0.3, world_damping_location=0.92, world_damping_rotation=0.9, radius=4.0, limit_angle=14,
                       stiffness_curve=[[0, 1.4], [1, 0.8]], dummy_bone_length=0, gravity=[0, 0, -60], teleport_rotation_threshold=30,
                       use_fixed_substepping=False),
}
WING_ROOTS = {'wing arm': '%s_WingArmRoot_Spo', 'blade wing': '%s_WingARoot_Spo', 'upper wing': '%s_WingBRoot_Spo'}
# the body's parts the shapes are fitted to (each body vertex taken by the part whose bone segment is nearest)
SEGMENTS = {'hips': ('C_Hip_a', 'C_Spine_a'), 'spine': ('C_Spine_a', 'C_Spine_d'), 'collar': ('C_Spine_d', 'C_Neck_a'),
            'neck': ('C_Neck_a', 'C_Head_a')}
for _s in SIDES:
    SEGMENTS.update({_s + ' thigh': (_s + '_UpperLeg_a', _s + '_Foreleg_a'), _s + ' calf': (_s + '_Foreleg_a', _s + '_Foot_a'),
                     _s + ' foot': (_s + '_Foot_a', _s + '_Toe_a'), _s + ' clavicle': (_s + '_Shoulder_a', _s + '_UpperArm_a'),
                     _s + ' upper arm': (_s + '_UpperArm_a', _s + '_Forearm_a'), _s + ' forearm': (_s + '_Forearm_a', _s + '_Hand_a')})
LEG_PAD = 1.0
NOTE = ("Create a Character System: Kawaii Dynamic Motions (KawaiiPhysics) for Bahamut Fused Sephiroth Whisper (PC0010_18, the "
        "Bahamut Fused Sephiroth Whisper skins' model). His wings and tail move with Neo Bahamut BlackFeeler's own motion (the "
        "summon's hovering idle, /Game/Motion/Summon/SU2050_NeoBahamut/Neutral00/N_Idle01_1, looped on his wing and tail bones, "
        "which are Neo Bahamut's; additive: the model's own shape kept) with the physics on top: the wing arms, the blade wings "
        "with their thrusters, the clawed upper wings and their membranes, the tail (kept out of his legs and off the floor); his "
        "crest (a stiff slow wave); his hair (Rebirth Sephiroth's, the Rebirth preset's settings for each strand, kept off his "
        "head, back, chest, shoulders, arms, the wing arms' shafts and, the long hair, his legs). Bonamik off on this model. "
        "Needs the game mod 3.20.0 or later (pose_animset, one-sided floors).")


class Body:
    """his mesh in the reference pose: each control point's dominant bone and material"""
    def __init__(self, m, names):
        self.pos = m['pos']
        wb, ww = m['wbone'], m['wweight']
        self.dom = np.array(names)[wb[np.arange(len(wb)), np.argmax(ww, axis=1)]]
        tri_cp = m['corner_cp'][m['tri']]
        self.mat = np.full(len(self.pos), -1, dtype=np.int32)
        for c in range(3):
            self.mat[tri_cp[:, c]] = m['tmat']
        self.slots = [str(s) for s in m['slots']]
        dom = self.dom.astype(str)
        own = np.zeros(len(dom), dtype=bool)
        for prefix in ('C_Tail', 'L_Wing', 'R_Wing', 'C_Hair', 'L_Hair', 'R_Hair'):
            own |= np.char.startswith(dom, prefix)
        self.body = self.in_slots(BODY_SLOTS) & ~own
        self.surface = self.in_slots(SURFACE_SLOTS) & ~own

    def in_slots(self, slots):
        return np.isin(self.mat, [self.slots.index(s) for s in slots if s in self.slots])

    def parts(self, T, pct=85, ends=0.25):
        """each body part's radii at its two ends: the body vertices nearest its segment, their pct % distance from its
        axis in its first and last quarter"""
        P = self.pos[self.body]
        keys = list(SEGMENTS)
        dist = np.empty((len(keys), len(P)))
        geo = []
        for k, key in enumerate(keys):
            a, b = T(SEGMENTS[key][0]), T(SEGMENTS[key][1])
            d = b - a
            L = np.linalg.norm(d)
            u = d / L
            rel = P - a
            t = rel @ u / L
            rad = np.linalg.norm(rel - np.outer(rel @ u, u), axis=1)
            tc = np.clip(t, 0, 1)
            dist[k] = np.linalg.norm(P - (a + np.outer(tc * L, u)), axis=1)
            geo.append((t, rad))
        near = np.argmin(dist, axis=0)
        out = {}
        self.part_points = {}
        for k, key in enumerate(keys):
            t, rad = geo[k]
            mine = near == k
            self.part_points[key] = P[mine]
            lo, hi = mine & (t >= -0.05) & (t < ends), mine & (t > 1 - ends) & (t <= 1.05)
            ra = float(np.percentile(rad[lo], pct)) if lo.sum() > 20 else None
            rb = float(np.percentile(rad[hi], pct)) if hi.sum() > 20 else None
            out[key] = (ra, rb)
        return out

    def depth_capsule(self, rig, key, T, pad=0.0, skip=0.0, pct=85, ends=0.25):
        """a part's capsule as deep as the part front to back (its back and front, his +X across its axis, at each end;
        the sides left out: the legs' armour flares out at the hips), its axis moved forward or back to the middle"""
        a, b = SEGMENTS[key]
        pa, pb = T(a), T(b)
        d = pb - pa
        L = np.linalg.norm(d)
        u = d / L
        f = np.array([1.0, 0.0, 0.0]) - u[0] * u
        f /= np.linalg.norm(f)
        Q = self.part_points[key]
        rel = Q - pa
        t = rel @ u / L
        x = rel @ f
        ends_out = []
        for sel in ((t >= -0.05) & (t < ends), (t > 1 - ends) & (t <= 1.05)):
            fr, bk = x[sel & (x > 0)], -x[sel & (x < 0)]
            front = float(np.percentile(fr, pct)) if len(fr) > 10 else None
            back = float(np.percentile(bk, pct)) if len(bk) > 10 else None
            if front is None or back is None:
                return None
            ends_out.append(((front + back) / 2 + pad, (front - back) / 2))
        (r0, s0), (r1, s1) = ends_out
        p0 = pa + u * skip + f * (s0 + (s1 - s0) * skip / L)
        p1 = pb + f * s1
        return cap_points(rig, a, p0, p1, r0 + (r1 - r0) * skip / L, r1), [r(r0, 1), r(s0, 1), r(r1, 1), r(s1, 1)]

    def surface_x(self, y, z, side, win=3.0):
        """the armour's surface behind (side -1) or in front of (side +1) the line through (y, z) along X"""
        P = self.pos[self.surface]
        sel = (np.abs(P[:, 1] - y) < win) & (np.abs(P[:, 2] - z) < win)
        if sel.sum() < 3:
            return None
        return float(P[sel, 0].max() if side > 0 else P[sel, 0].min())


def nb_motion(clip):
    sk = A.Skeleton(open(NB_SKELETON, 'rb').read())
    LQ, LT, fps, _ = A.decode(open(NB_MOTION % clip, 'rb').read(), sk)
    return sk, LQ, fps


def motion_tracks(motion, bones, rig, absolute=False, min_degrees=0.05):
    """Neo Bahamut's loop: each of the node's bones that moves in it, its local rotation a frame (the game's quaternions).
    absolute: the bones held as Neo Bahamut holds them (his pose in the loop, not only its moves): each bone's rotation
    from its parent as Neo Bahamut's in the loop (from his reference pose's: the model's wing and tail bones are in Neo
    Bahamut's reference pose, their roots under Sephiroth's shoulders and hips), the bones he holds still but away from
    his reference pose given that one key"""
    sk, LQ, fps = motion
    out = {}
    for n in bones:
        k = sk.index.get(n)
        if k is None:
            continue
        q = LQ[:, k]
        qm = q.mean(0)
        qm /= np.linalg.norm(qm)
        moves = float(np.degrees(2 * np.arccos(np.clip(np.abs(q @ qm), -1, 1))).max()) >= min_degrees
        if not absolute:
            if moves:
                out[n] = [[r(x, 5) for x in f] for f in q]
            continue
        bind = np.array(sk.ref_q[k], dtype=float)
        rest = np.array(rig.by[n]['local_q'], dtype=float)
        keys = A.qmul(rest[None], A.qmul((bind * np.array([-1, -1, -1, 1.0]))[None], q))
        keys /= np.linalg.norm(keys, axis=1, keepdims=True)
        away = float(np.degrees(2 * np.arccos(np.clip(np.abs(keys @ rest), -1, 1))).max())
        if not moves and away < min_degrees:
            continue
        if not moves:
            keys = keys[:1]
        for i in range(1, len(keys)):
            if keys[i] @ keys[i - 1] < 0:
                keys[i] = -keys[i]
        out[n] = [[r(x, 5) for x in f] for f in keys]
    return out


def hair_nodes_from_preset():
    """the Rebirth preset's PC0010_15 entry (Rebirth Sephiroth's own hair): each strand node's settings and its head shapes"""
    d = json.load(open(HAIR_PRESET))
    e = d['kawaii'][0]
    out = {}
    for n in e['nodes']:
        if 'Hair' not in n['root_bone']:
            continue
        keep = {k: v for k, v in n.items() if k not in SHAPES}
        head = [s for s in n.get('spheres', []) if s.get('bone') == 'C_Head_a']
        out[n['root_bone']] = (keep, head)
    return out


def within_reach(rig, node, bones, margin=2.0):
    """drop the shapes a chain cannot reach (farther from its root than its length, its tip's dummy bone and its radius)"""
    root = np.array(rig.by[node['root_bone']]['t'])
    length = sum(np.linalg.norm(np.array(rig.by[b]['t']) - np.array(rig.by[rig.by[b]['parent']]['t'])) for b in bones
                 if rig.by[b]['parent'] in rig.by)
    reach = length + node.get('dummy_bone_length', 0.0) + node.get('radius', 0.0) * 1.2 + margin
    for kind in ('spheres', 'capsules', 'tapered_capsules'):
        if kind in node:
            node[kind] = [sh for sh in node[kind] if shape_dist(rig, sh, kind, root) <= reach]
            if not node[kind]:
                del node[kind]
    return node


def spine_bone(z):
    for bone, top in (('C_Hip_a', 112.3), ('C_Spine_a', 126.8), ('C_Spine_b', 142.2), ('C_Spine_c', 156.8), ('C_Spine_d', 160.7),
                      ('C_Neck_a', 170.0)):
        if z < top:
            return bone
    return 'C_Neck_b'


def main(src, model, out, clip=CLIP):
    os.makedirs(out, exist_ok=True)
    m = np.load(src)
    names = write_rig(m, os.path.join(out, 'rig.json'))
    rig = Rig(os.path.join(out, 'rig.json'))
    body = Body(m, names)
    T = lambda n: np.array(rig.by[n]['t'])
    weight = np.bincount(m['wbone'][m['wweight'] > 0], weights=m['wweight'][m['wweight'] > 0], minlength=len(names))
    W = {n: float(weight[i]) for i, n in enumerate(names)}
    report = {}
    # (game mod 3.20.0) a solid floor: Neo Bahamut's motions (a summon's, made in the air) swing his tail and wings down
    floor = [{'offset': [0.0, 0.0, 0.5], 'rotation': [0.0, 0.0, 0.0], 'one_sided': True}]

    # ---- shapes from his mesh
    parts = body.parts(T)
    report['part radii'] = {k: [r(x or 0, 1) for x in v] for k, v in parts.items()}

    def part_capsule(key, default_a, default_b, pad=0.0, skip=0.0):
        a, b = SEGMENTS[key]
        ra, rb = parts[key]
        return capsule(rig, a, b, (ra or default_a) + pad, r_b=(rb or default_b) + pad, skip=skip)

    legs, shoulders, arms, pillars = [], [], [], []
    for s in SIDES:
        for key, skip in ((s + ' thigh', 4.0), (s + ' calf', 0.0)):
            got = body.depth_capsule(rig, key, T, LEG_PAD, skip=skip)
            if got:
                legs.append(got[0])
                report[key + ' depth (r0, shift0, r1, shift1)'] = got[1]
            else:
                legs.append(part_capsule(key, 12, 9, LEG_PAD, skip=skip))
        shoulders.append(part_capsule(s + ' clavicle', 12, 14))
        arms.append(part_capsule(s + ' upper arm', 14, 11))
        # the wing arms' shafts beside his head (their own vertices: the shafts' thickness)
        for a, b in (('%s_WingArmA_b' % s, '%s_WingArmA_c' % s), ('%s_WingArmA_c' % s, '%s_WingArmA_d' % s)):
            sel = np.isin(body.dom, [a, b])
            pa, pb = T(a), T(b)
            u = (pb - pa) / np.linalg.norm(pb - pa)
            rel = body.pos[sel] - pa
            rad = np.linalg.norm(rel - np.outer(rel @ u, u), axis=1)
            rr = float(np.percentile(rad, 85)) if sel.sum() > 20 else 5.0
            pillars.append(capsule(rig, a, b, rr))
    report['wing shaft radius'] = [p['radius'] for p in pillars]
    # the armour's surface under the hair: spheres just inside it on his back (under the long hair) and chest (under the
    # long front strands), each on the spine bone at its height
    back, chest = [], []
    RB, RC = 8.0, 7.0
    for z in np.arange(180.0, 99.0, -7.0):
        for y in (-8.0, 0.0, 8.0):
            xs = body.surface_x(y, z, -1)
            if xs is not None:
                back.append(sphere(rig, spine_bone(z), np.array([xs + RB, y, z]), RB))
    for z in np.arange(172.0, 133.0, -6.0):
        for y in (-6.0, 0.0, 6.0):
            xs = body.surface_x(y, z, +1)
            if xs is not None:
                chest.append(sphere(rig, spine_bone(z), np.array([xs - RC, y, z]), RC))
    report['surface spheres (back, chest)'] = [len(back), len(chest)]

    motion = nb_motion(clip)
    nodes = []
    # ---- the tail
    tail_bones = chain_bones(rig, 'C_Tail_a')
    tail = dict(name='tail', root_bone='C_Tail_a', **TAIL)
    if USE_ANIMSET:
        tail['pose_animset'] = dict(NB_ANIMSET)
        tracks = {}
    else:
        tracks = motion_tracks(motion, tail_bones, rig, 'tail' in ABSOLUTE)
    if tracks:
        tail['pose_animation'] = dict(tracks=tracks, fps=r(motion[2], 3), speed=1.0, weight=1.0, additive='tail' not in ABSOLUTE)
    tail['tapered_capsules'] = [dict(x) for x in legs]
    tail['planes'] = floor
    nodes.append(within_reach(rig, fit_to_rest(rig, tail, [n for n in tail_bones if n != 'C_Tail_a']), tail_bones))
    report['tail tracks'] = len(tracks)
    # ---- the crest
    crest = dict(name='crest', root_bone='C_Tentacle_a', **CREST)
    crest['pose_waves'] = [dict(w) for w in CREST_WAVES]
    nodes.append(crest)
    # ---- the wings
    motion_report = {}
    for s in SIDES:
        for kind, root_fmt in WING_ROOTS.items():
            root = root_fmt % s
            bones = chain_bones(rig, root)
            tracks = {} if USE_ANIMSET else motion_tracks(motion, bones, rig, 'wings' in ABSOLUTE)
            n = dict(name='%s %s' % (kind, s), root_bone=root, **WING[kind])
            if USE_ANIMSET:
                n['pose_animset'] = dict(NB_ANIMSET)
            if tracks:
                n['pose_animation'] = dict(tracks=tracks, fps=r(motion[2], 3), speed=1.0, weight=1.0, additive='wings' not in ABSOLUTE)
            if kind in ('upper wing', 'blade wing'):
                n['planes'] = [dict(x) for x in floor]   # (the membrane hangs to the floor; the motions swing the blades down)
            motion_report['%s %s' % (kind, s)] = [len(bones), len(tracks)]
            nodes.append(n)
    report['wing motion (bones, tracks)'] = motion_report
    # ---- the hair
    preset = hair_nodes_from_preset()
    hair_report = {}
    head_x = T('C_Head_a')[0]
    for root, (settings, head) in sorted(preset.items()):
        if root not in rig.by:
            continue
        bones = [x for x in chain_bones(rig, root) if x != root]
        if sum(W.get(x, 0.0) for x in [root] + bones) <= 0.0:
            hair_report[root] = 'no weights: left out'
            continue
        n = dict(settings)
        n['root_bone'] = root
        n['spheres'] = [dict(x) for x in head]
        P = np.array([T(x) for x in bones])
        front = P[:, 0].mean() > head_x
        long_ = P[:, 2].min() < 110.0
        if front:
            n['spheres'] += [dict(x) for x in chest]
            n['tapered_capsules'] = [dict(x) for x in shoulders + arms]
        else:
            n['spheres'] += [dict(x) for x in back]
            n['tapered_capsules'] = [dict(x) for x in shoulders + arms + pillars + (legs if long_ else [])]
        within_reach(rig, fit_to_rest(rig, n, bones), [root] + bones)
        hair_report[root] = '%s: %d spheres, %d capsules' % ('front' if front else ('long' if long_ else 'back'), len(n.get('spheres', [])),
                                                             len(n.get('tapered_capsules', [])))
        nodes.append(n)
    report['hair'] = hair_report
    entry = dict(name="Bahamut Fused Sephiroth Whisper (PC0010_18): his wings and tail with Neo Bahamut's own motion, his crest and his hair",
                 models=[model], preset='bahamut fused sephiroth whisper', nodes=nodes, disable_bonamik=True)
    json.dump({'kawaii': [entry]}, open(os.path.join(out, 'entry.json'), 'w'), indent=1)
    json.dump({'schema': 'RebirthSkelCompat/1', 'note': NOTE, 'kawaii': [entry]}, open(os.path.join(out, 'compat.json'), 'w'), indent=1)
    report['nodes'] = len(nodes)
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main(*sys.argv[1:5])
