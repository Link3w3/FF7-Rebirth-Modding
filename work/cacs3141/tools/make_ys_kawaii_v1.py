"""Young Sephiroth's KawaiiPhysics entry (compat\\YoungSephirothKawaii.json) for Create a Character System 3.14.0.

His hair, coat and collar swing with KawaiiPhysics in place of his body BNM (PC0010_13_BNM: those chains); the wing keeps
its own BNM (PC0010_13_Wing_BNM) and KDI. The collision shapes are his BNM's colliders (the same bones, places and sizes),
the coat's strips are tied side by side as the BNM's links tie them.

  python make_ys_kawaii.py <rig.json> <pc0010_13_bnm_spec.json> <out.json>
"""
import json
import math
import sys

rig = json.load(open(sys.argv[1], encoding='utf-8'))
bnm = json.load(open(sys.argv[2], encoding='utf-8'))
out_path = sys.argv[3]

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
coat_capsules = []
for side in 'LR':
    coat_capsules.append(capsule(side + '_UpperLeg_a', side + '_Foreleg_a', upleg['m_Radius']))
    coat_capsules.append(capsule(side + '_Foreleg_a', side + '_Foot_a', leg['m_Radius'] * 0.85))

# ---- the chains: each from the bone the BNM keeps on the animation (its kinematic body, or the one at its base), down
hair_roots = ['C_HairF_a_Phy', 'C_HairB_a_Phy', 'C_HairJ_a_Phy', 'C_HairE_a_Phy', 'C_HairA_a_Phy',        # front
              'L_HairA_a_Phy', 'L_HairC_a_Phy', 'C_HairH_a_Phy', 'R_HairA_a_Phy', 'C_HairD_a_Phy',         # sides
              'R_HairD_a_Phy', 'C_HairL_a_Phy', 'L_HairD_a_Phy']                                          # back
around = ['L_CoatA', 'L_CoatB', 'L_CoatC', 'L_CoatD', 'L_CoatE', 'C_CoatA', 'R_CoatE', 'R_CoatD', 'R_CoatC', 'R_CoatB', 'R_CoatA']
coat_roots = [s + '_a_Phy' for s in around]
collar_roots = ['L_CollarA_a_Phy', 'L_CollarB_a_Phy', 'R_CollarA_a_Phy', 'R_CollarB_a_Phy']
for name in hair_roots + coat_roots + collar_roots:
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
    n = {'name': name, 'root_bone': roots[0], 'additional_root_bones': roots[1:]}
    n.update(settings)
    return n


entry = {
    'name': 'Young Sephiroth: hair, coat and collar',
    'models': ['/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13.PC0010_13'],
    'requires_paks': ['YoungSephiroth_P'],
    'disable_bonamik': ['PC0010_13_BNM'],
    'nodes': [
        node('hair', hair_roots, damping=0.15, stiffness=0.12, world_damping_location=0.65, world_damping_rotation=0.65, radius=0.75,
             limit_angle=40, stiffness_curve=[[0, 1.6], [1, 0.8]], dummy_bone_length=4, gravity=[0, 0, -150],
             teleport_rotation_threshold=30, spheres=hair_spheres, capsules=hair_capsules),
        # (the BNM's coat bodies: 1 cm at the top, 2.25 at the hem)
        node('coat', coat_roots, damping=0.12, stiffness=0.04, world_damping_location=0.55, world_damping_rotation=0.55, radius=1.5,
             radius_curve=[[0, 0.67], [0.5, 0.75], [1, 1.5]], limit_angle=55, stiffness_curve=[[0, 1.8], [1, 0.7]], dummy_bone_length=10,
             gravity=[0, 0, -450],
             teleport_rotation_threshold=30, spheres=coat_spheres, capsules=coat_capsules, bone_constraints=coat_ties),
        node('collar', collar_roots, damping=0.2, stiffness=0.35, world_damping_location=0.8, world_damping_rotation=0.8, radius=1,
             limit_angle=20, dummy_bone_length=4, teleport_rotation_threshold=30),
    ],
}
doc = {
    'schema': 'RebirthSkelCompat/1',
    'note': ("Create a Character System 3.14.0: Young Sephiroth's hair, coat and collar swing with KawaiiPhysics in place of his "
             "body BNM (PC0010_13_BNM, off while his model is shown); his wing keeps its own BNM and KDI. Delete this file to "
             "have his BNM back. Settings: the README's KawaiiPhysics part."),
    'kawaii': [entry],
}
with open(out_path, 'w', encoding='utf-8', newline='\r\n') as f:
    json.dump(doc, f, indent=1)
    f.write('\n')
print('wrote', out_path, '-', sum(1 for _ in hair_roots), 'hair chains,', len(coat_roots), 'coat strips,', len(coat_ties), 'ties,',
      len(collar_roots), 'collar pieces')
