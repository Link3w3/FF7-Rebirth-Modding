"""Young Sephiroth's KawaiiPhysics entry (compat\\YoungSephirothKawaii.json) for Create a Character System 3.14.3.

His hair, coat, collar and wing swing with KawaiiPhysics; his model has no BNM any more (YoungSephiroth_P's PC0010_13:
its Bonamik list emptied, bnm_off.py) and keeps its KDI (PC0010_13_KDI, the wing's KineDriver: it places the wing's
spokes and helper bones, and bends feathers A-D, as the wing opens and folds). KawaiiPhysics runs on the pose the game
has made, the KDI's work included, so each chain swings about the pose the KDI gives it. A node a chain (a strand,
strip, collar piece, feather), each with settings a little its own. The head, neck and hip colliders are his old BNM's;
(3.14.3) the coat's leg colliders are sized from his mesh (the trousers 8 - 10 cm from the thigh's axis; the BNM's
7.05 let the coat into the legs): tapered capsules from 5 cm below the hip joint to past the knee, and the calves; the
coat's bones 2 - 3.25 cm round (its cloth sits up to 1.5 cm inside the line of its bones), its swing limit 85 degrees
(it must swing over a raised thigh: 55 held it in the leg). The chains feel 10 - 15 % of the character's own moves
(world damping 0.85 - 0.9; 0.55 - 0.65 had the coat fly out and the hair lie on its limit when running). Checked
offline (tests/ys_skirt.cpp, ys_skirt_check.py: his coat's vertices skinned with the result against his legs' mesh as he
walks, runs and sprints). The settings can be changed for a test with the environment (THIGH_TOP, COAT_RADIUS, HAIR_WD,
... below).

  python make_ys_kawaii.py <rig_wing.json (342 bones)> <pc0010_13_bnm_spec.json> <pc0010_13_wing_bnm_spec.json> <out.json>
"""
import hashlib
import json
import math
import sys

rig = json.load(open(sys.argv[1], encoding='utf-8'))
import os
THIGH_TOP = float(os.environ.get('THIGH_TOP', '9.3'))
THIGH_KNEE = float(os.environ.get('THIGH_KNEE', '10.3'))
CALF_TOP = float(os.environ.get('CALF_TOP', '8.0'))
CALF_ANKLE = float(os.environ.get('CALF_ANKLE', '6.0'))
COAT_RADIUS = float(os.environ.get('COAT_RADIUS', '2.6'))
COAT_LIMIT = float(os.environ.get('COAT_LIMIT', '85'))
COAT_WD = float(os.environ.get('COAT_WD', '0.9'))
COAT_DAMP = float(os.environ.get('COAT_DAMP', '0.2'))
COAT_STIFF = float(os.environ.get('COAT_STIFF', '0.05'))
COAT_GRAV = float(os.environ.get('COAT_GRAV', '-450'))
THIGH_SKIP = float(os.environ.get('THIGH_SKIP', '5.0'))
COAT_SUBDIV = int(os.environ.get('COAT_SUBDIV', '0'))
HAIR_WD = float(os.environ.get('HAIR_WD', '0.85'))
HAIR_DAMP = float(os.environ.get('HAIR_DAMP', '0.25'))
HAIR_STIFF = float(os.environ.get('HAIR_STIFF', '0.2'))
HAIR_LIMIT = float(os.environ.get('HAIR_LIMIT', '35'))
WING_STIFF = float(os.environ.get('WING_STIFF', '0.2'))
COLLAR_DAMP = float(os.environ.get('COLLAR_DAMP', '0.3'))
COLLAR_WD = float(os.environ.get('COLLAR_WD', '0.9'))
WING_WD = float(os.environ.get('WING_WD', '0.85'))
WING_DAMP = float(os.environ.get('WING_DAMP', '0.3'))
COAT_SUBSTEP = os.environ.get('COAT_SUBSTEP', '')
bnm = json.load(open(sys.argv[2], encoding='utf-8'))
wing_bnm = json.load(open(sys.argv[3], encoding='utf-8'))
out_path = sys.argv[4]

bones = {b['name']: b for b in rig['bones']}


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


def local_of(name, parent):
    """`name`'s place in `parent`'s space (the reference pose)."""
    b, p = bones[name], bones[parent]
    d = [b['t'][i] - p['t'][i] for i in range(3)]
    return qrot(qinv(p['q']), d)


def r(x, n=3):
    return round(float(x), n)


# UE's FRotator -> FQuat (as the solver: KawaiiSolver.hpp FromRotator)
def from_rotator(pitch, yaw, roll):
    half = math.pi / 180.0 / 2.0
    p, y, rl = pitch * half, yaw * half, roll * half
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(rl), math.cos(rl)
    return (cr * sp * sy - sr * cp * cy, -cr * sp * cy - sr * cp * sy, cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy)


def rotator_for_z(d):
    """A rotation (pitch, yaw, roll) taking the shape's Z axis (a capsule's) to the direction d (in the bone's space)."""
    n = math.sqrt(sum(c * c for c in d))
    dx, dy, dz = (c / n for c in d)
    pitch = math.degrees(math.atan2(math.hypot(dx, dy), dz))
    yaw = math.degrees(math.atan2(-dy, -dx)) if math.hypot(dx, dy) > 1e-9 else 0.0
    rot = (pitch, yaw, 0.0)
    z = qrot(from_rotator(*rot), [0, 0, 1])
    assert all(abs(z[i] - (dx, dy, dz)[i]) < 1e-4 for i in range(3)), (d, z)
    return [r(pitch, 2), r(yaw, 2), 0.0]


body = {b['mName']: b for b in bnm['mBodies']}


def capsule(bone_a, bone_b, radius):
    """A capsule on bone_a from its joint to bone_b's (rigid in bone_a: bone_b is its child)."""
    d = local_of(bone_b, bone_a)
    length = math.sqrt(sum(c * c for c in d))
    return {'bone': bone_a, 'offset': [r(c / 2) for c in d], 'rotation': rotator_for_z(d), 'radius': r(radius, 2), 'length': r(length, 2)}


def collider(name):
    b = body[name]
    assert b['m_IsKinematic'], name
    return b


# ---- the BNM's colliders as KawaiiPhysics shapes
head = collider('Bdy_Sta_head_0_2')                      # Col_head: a sphere on C_Head_a
neck = collider('Bdy_Sta_neck_0_1')
spine4 = collider('Bdy_Sta_spine4_0_1')
hip = collider('Bdy_Sta_hip_0_1')                        # Col_leg: a sphere on C_Hip_a
upleg = collider('Bdy_Sta_left_upleg_0_1')
leg = collider('Bdy_Sta_left_leg_0_1')

hair_spheres = [{'bone': head['mParentName'], 'offset': [r(c) for c in head['m_LocalTransform']], 'radius': r(head['m_Radius'], 2)}]
hair_capsules = [capsule('C_Neck_a', 'C_Head_a', neck['m_Radius']), capsule('C_Spine_d', 'C_Neck_a', spine4['m_Radius'])]
coat_spheres = [{'bone': hip['mParentName'], 'offset': [r(c) for c in hip['m_LocalTransform']], 'radius': r(hip['m_Radius'], 2)}]


def tapered(bone_a, bone_b, r_a, r_b, skip_a=0.0, past_b=0.0):
    """A tapered capsule on bone_a along it to bone_b's joint: radius r_a at bone_a's end, r_b at bone_b's; it starts skip_a cm
    after bone_a's joint and ends past_b cm past bone_b's (KawaiiPhysics' radius0 is at its +Z end: bone_b's)."""
    d = local_of(bone_b, bone_a)
    length = math.sqrt(sum(c * c for c in d))
    u = [c / length for c in d]
    start = [u[i] * skip_a for i in range(3)]
    end = [d[i] + u[i] * past_b for i in range(3)]
    return {'bone': bone_a, 'offset': [r((start[i] + end[i]) / 2) for i in range(3)], 'rotation': rotator_for_z(d), 'radius0': r(r_b, 2),
            'radius1': r(r_a, 2), 'length': r(length - skip_a + past_b, 2)}


# (3.14.3) the legs as the mesh has them (his trousers: 8 - 10 cm from the thigh's axis, the BNM's colliders 7.05): the
# thighs from 5 cm below the hip joint (the coat's top hangs there at rest) to 3 cm past the knee; the calves to the ankle
coat_capsules = []
coat_tapered = []
for side in 'LR':
    coat_tapered.append(tapered(side + '_UpperLeg_a', side + '_Foreleg_a', THIGH_TOP, THIGH_KNEE, skip_a=THIGH_SKIP, past_b=3.0))
    coat_tapered.append(tapered(side + '_Foreleg_a', side + '_Foot_a', CALF_TOP, CALF_ANKLE))

# ---- the chains: each from the bone the BNM keeps on the animation (its kinematic body, or the one at its base), down
hair_roots = ['C_HairF_a_Phy', 'C_HairB_a_Phy', 'C_HairJ_a_Phy', 'C_HairE_a_Phy', 'C_HairA_a_Phy',        # front
              'L_HairA_a_Phy', 'L_HairC_a_Phy', 'C_HairH_a_Phy', 'R_HairA_a_Phy', 'C_HairD_a_Phy',         # sides
              'R_HairD_a_Phy', 'C_HairL_a_Phy', 'L_HairD_a_Phy']                                          # back
around = ['L_CoatA', 'L_CoatB', 'L_CoatC', 'L_CoatD', 'L_CoatE', 'C_CoatA', 'R_CoatE', 'R_CoatD', 'R_CoatC', 'R_CoatB', 'R_CoatA']
coat_roots = [s + '_a_Phy' for s in around]
collar_roots = ['L_CollarA_a_Phy', 'L_CollarB_a_Phy', 'R_CollarA_a_Phy', 'R_CollarB_a_Phy']
# the wing: each feather from its a bone (on the spoke the KDI places) down, as its old BNM swung them
wing_roots = ['R_Feather%s_a_Phy' % f for f in 'ABCDEFGHIJK']
swung = {b['mParentName'] for b in wing_bnm['mBodies'] if not b['m_IsKinematic']}
held = {b['mParentName'] for b in wing_bnm['mBodies'] if b['m_IsKinematic']}
assert held == set(wing_roots), sorted(held)
below = set()
for name in bones:
    at = name
    while at and at not in wing_roots:
        at = bones[at]['parent']
    if at and name != at:
        below.add(name)
assert below == swung, (sorted(below - swung), sorted(swung - below))
for name in hair_roots + coat_roots + collar_roots + wing_roots:
    assert name in bones, name
# the coat's strips tied to their neighbours as the BNM ties them (at each of the bones that swing)
coat_ties = []
for a, b in zip(around, around[1:]):
    for level in 'bcd':
        coat_ties.append([a + '_' + level + '_Phy', b + '_' + level + '_Phy'])
for pair in coat_ties:
    assert all(p in bones for p in pair), pair
# the BNM's links say the same
links = {(body[l['mA']]['mParentName'], body[l['mB']]['mParentName']) for l in bnm['mLinks'] if not l.get('bIsBending')}
for a, b in coat_ties:
    assert (a, b) in links or (b, a) in links, (a, b)


def node(name, roots, **settings):
    n = {'name': name, 'root_bone': roots[0]}
    if roots[1:]:
        n['additional_root_bones'] = roots[1:]
    n.update(settings)
    return n


def spread(root, salt):
    """A number in [0, 1) of the chain's own (the same every time this runs): each chain's settings differ a little, so
    the chains do not all swing as one."""
    h = hashlib.md5((root + '/' + salt).encode('utf-8')).digest()
    return int.from_bytes(h[:4], 'little') / 2 ** 32


def per_chain(group, roots, base, short):
    """One node a chain (each its own settings: stiffness, damping, how much of the character's motion it feels, gravity
    and its swing limit each a little off the group's), so no two strands move as one."""
    nodes = []
    for root in roots:
        s = dict(base)
        s['stiffness'] = r(base['stiffness'] * (0.7 + 0.6 * spread(root, 'stiffness')), 4)
        s['damping'] = r(base['damping'] * (0.75 + 0.5 * spread(root, 'damping')), 4)
        for key in ('world_damping_location', 'world_damping_rotation'):
            s[key] = r(min(0.97, max(0.3, base[key] + (spread(root, key) - 0.5) * 0.16)), 4)
        if 'gravity' in base:
            s['gravity'] = [0, 0, r(base['gravity'][2] * (0.75 + 0.5 * spread(root, 'gravity')), 1)]
        if base.get('limit_angle'):
            s['limit_angle'] = r(base['limit_angle'] * (0.85 + 0.3 * spread(root, 'limit')), 2)
        nodes.append(node(group + ' ' + short(root), [root], **s))
    return nodes


def short_name(root):
    return root.replace('_a_Phy', '')


hair = dict(damping=HAIR_DAMP, stiffness=HAIR_STIFF, world_damping_location=HAIR_WD, world_damping_rotation=HAIR_WD, radius=0.75, limit_angle=HAIR_LIMIT,
            stiffness_curve=[[0, 1.6], [1, 0.8]], dummy_bone_length=4, gravity=[0, 0, -150], teleport_rotation_threshold=30,
            use_fixed_substepping=False, spheres=hair_spheres, capsules=hair_capsules)
# (the old BNM's coat bodies: 1 cm at the top, 2.25 at the hem; the strips are not tied to each other: each swings alone)
# (3.14.3) the coat's bones 1.5 cm round at the top to 2.5 at the hem (its cloth sits up to 1.5 cm inside the line of its
# bones), against the legs' tapered capsules
coat = dict(damping=COAT_DAMP, stiffness=COAT_STIFF, world_damping_location=COAT_WD, world_damping_rotation=COAT_WD, radius=COAT_RADIUS,
            radius_curve=[[0, 0.75], [0.5, 1.0], [1, 1.25]], limit_angle=COAT_LIMIT, stiffness_curve=[[0, 1.8], [1, 0.7]], dummy_bone_length=10,
            gravity=[0, 0, COAT_GRAV], teleport_rotation_threshold=30, use_fixed_substepping=False, spheres=coat_spheres,
            tapered_capsules=coat_tapered)
if COAT_SUBDIV:
    coat.update(bone_subdivision_count=COAT_SUBDIV, bone_subdivision_collision_only=False)
if COAT_SUBSTEP:
    coat.update(use_fixed_substepping=True, target_framerate=int(COAT_SUBSTEP), max_substeps=4)
collar = dict(damping=COLLAR_DAMP, stiffness=0.35, world_damping_location=COLLAR_WD, world_damping_rotation=COLLAR_WD, radius=1, limit_angle=20,
              dummy_bone_length=4, teleport_rotation_threshold=30, use_fixed_substepping=False)
# (its old BNM: cones of 10 / 25 degrees, heavy damping, gravity at 0.3; the feathers 11 - 38 cm a bone; looser than that, so
# the feathers swing where the KDI and the animation move the wing)
wing = dict(damping=WING_DAMP, stiffness=WING_STIFF, world_damping_location=WING_WD, world_damping_rotation=WING_WD, radius=2.24, limit_angle=30,
            dummy_bone_length=12, gravity=[0, 0, -300], teleport_rotation_threshold=30, use_fixed_substepping=False)
nodes = (per_chain('hair', hair_roots, hair, short_name) + per_chain('coat', coat_roots, coat, short_name) +
         per_chain('collar', collar_roots, collar, short_name) + per_chain('wing', wing_roots, wing, lambda n: n.replace('R_Feather', '').replace('_a_Phy', '')))
assert len(nodes) <= 64, len(nodes)
entry = {
    'name': 'Young Sephiroth: hair, coat, collar and wing',
    'models': ['/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13.PC0010_13'],
    'requires_paks': ['YoungSephiroth_P'],
    'nodes': nodes,
}
doc = {
    'schema': 'RebirthSkelCompat/1',
    'note': ("Create a Character System 3.14.3: Young Sephiroth's hair, coat, collar and wing swing with KawaiiPhysics, a node "
             "a strand, strip, collar piece and feather, each with settings a little its own, so they swing apart. His model "
             "(YoungSephiroth_P) has no BNM; it keeps its KDI (the wing's KineDriver), and each chain swings about the pose the "
             "KDI gives it. 3.14.3: the coat kept out of his legs (leg colliders the size of his legs, rounder coat bones, a "
             "wider swing), every chain calmer when he runs. Needs the game mod 3.14.3. Settings: the README's KawaiiPhysics part."),
    'kawaii': [entry],
}
with open(out_path, 'w', encoding='utf-8', newline='\r\n') as f:
    json.dump(doc, f, indent=1)
    f.write('\n')
print('wrote', out_path, '-', len(nodes), 'nodes:', len(hair_roots), 'hair strands,', len(coat_roots), 'coat strips (untied),',
      len(collar_roots), 'collar pieces,', len(wing_roots), 'feathers (%d bones swinging)' % len(swung))
