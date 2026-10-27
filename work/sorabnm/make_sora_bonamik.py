"""Sora's Bonamik (hair, necklace, hood, sleeves, jacket hem, belt, shoe zips), made as a regular Bonamik.

The same Bonamik 3.x data the game's own characters carry (Cloud's PC0000_00_BNM): bodies, cones, links, collision
shapes and groups; no v2 sub-object (his KH3 Bonamik, p_ex011_Bonamik, is v2 data, which the game does not run).
Which bones move comes from his KH3 Bonamik (the same chains, roots following the animation); every value is Cloud's:
  * hair: his spikes (C_kami_a..f, L_kami_a..c, R_kami_a..c, two or three bones each): Cloud's top hair (Hair_Top),
    its root body and its swinging bodies, cones a little stiffer than Cloud's (Sora's spikes barely bend);
  * cloth (jacket hem, hood, sleeves, belt, shoe zips, the zip pull): Cloud's pants flaps (Bottom_R), with the hem's
    neighbouring pieces linked the way Cloud's flaps are;
  * necklace: the chain and crown follow the chest loosely (Cloud's pants values, heavier, pulled back harder);
  * collisions: his thighs and shins push the jacket hem away.

Run it in the End editor (File > Execute Python Script, or through the editor link). It creates (or rebuilds)
/Game/Character/Player/PC0000_00_Sora_KH2/Model/PC0000_00_S_BNM, checks every value it wrote and every bone it names on
his mesh, saves it and writes Saved/SoraBonamik/report.json. It does not change his mesh: the cooked mesh is pointed at
this asset when the mod is packaged (soradata/build_sora_assets.py, SORA_BONAMIK=1).
"""
import json
import os
import traceback

try:
    import unreal
except ImportError:  # imported outside the editor for the offline checks
    unreal = None

MODEL_DIR = '/Game/Character/Player/PC0000_00_Sora_KH2/Model'
MESH_PATH = MODEL_DIR + '/PC0000_00_S'
ASSET_NAME = 'PC0000_00_S_BNM'
ASSET_PATH = MODEL_DIR + '/' + ASSET_NAME
VERSION_NO = 30713                                # Bonamik 3.7.13, as Cloud's PC0000_00_BNM

# ---------------------------------------------------------------------------------------------------------------
# TUNING (change, then run it again)
HAIR_LIMITS = [(12.0, 12.0, 0.25), (20.0, 20.0, 0.15)]   # per depth: cone limit Y, Z (degrees), inner strength
CLOTH_LIMITS = [(15.0, 15.0, 0.35), (20.0, 20.0, 0.3)]
NECKLACE_LIMITS = [(20.0, 20.0, 0.3), (25.0, 25.0, 0.25), (25.0, 25.0, 0.25)]
LEG_RADIUS = {'L_momo': 7.5, 'L_sune': 5.5, 'R_momo': 7.5, 'R_sune': 5.5}
HEM_RADIUS = 1.5

# ---------------------------------------------------------------------------------------------------------------
# Sora's chains (checked against the mesh when it runs): each [root, ...]: the root follows the animation


def chain(prefix, letters, depth):
    return [['%s%s%d' % (prefix, c, i) for i in range(1, depth + 1)] for c in letters]


HAIR = [['C_kami_a1', 'C_kami_a2'], ['C_kami_b1', 'C_kami_b2', 'C_kami_b3'], ['C_kami_c1', 'C_kami_c2', 'C_kami_c3'],
        ['C_kami_d1', 'C_kami_d2'], ['C_kami_e1', 'C_kami_e2', 'C_kami_e3'], ['C_kami_f1', 'C_kami_f2', 'C_kami_f3'],
        ['L_kami_a1', 'L_kami_a2'], ['L_kami_b1', 'L_kami_b2', 'L_kami_b3'], ['L_kami_c1', 'L_kami_c2'],
        ['R_kami_a1', 'R_kami_a2'], ['R_kami_b1', 'R_kami_b2', 'R_kami_b3'], ['R_kami_c1', 'R_kami_c2']]
HAIR_PARENT = 'atama'
NECKLACE = [['neckla_chain1', 'neckla_chain2', 'neckla_chain3', 'neckla_head']]
HOOD = [['hood', 'hood1', 'hood2']]
SLEEVES = chain('L_sode', 'ABCD', 2) + chain('R_sode', 'ABCD', 2)
# the hem, around him from the front right to the front left (the jacket is open in front)
HEM_ORDER = ['R_susoA', 'R_susoB', 'R_susoC', 'R_susoD', 'B_suso', 'L_susoD', 'L_susoC', 'L_susoB', 'L_susoA']
JACKET = [['%s%d' % (p, i) for i in (1, 2, 3)] for p in HEM_ORDER]
ZIP_PULL = ['R_susoA2', 'jip1', 'jip2']           # hangs from the hem's swinging body, so no root of its own
BELT = [['belt', 'belt1']]
SHOE_ZIPS = [['L_shoe_jip', 'L_shoe_jip1'], ['R_shoe_jip', 'R_shoe_jip1']]
LEGS = [('L_momo', 'L_sune'), ('R_momo', 'R_sune')]

GROUPS = ['default', 'Col_leg', 'Hair', 'Necklace', 'Hood', 'Sleeve', 'Jacket', 'Belt', 'ShoeZip']


class Vec(tuple):
    """FVector"""


class Quat(tuple):
    """FQuat (x, y, z, w)"""


ZERO = Vec((0.0, 0.0, 0.0))
IDENTITY = Quat((0.0, 0.0, 0.0, 1.0))

# ---------------------------------------------------------------------------------------------------------------
# Cloud's PC0000_00_BNM (Bonamik 3.7.13): the values this copies.
FPS_CORRECTION = dict(
    mFramerate=30.0, mWindDrag=1.0, mWindLift=1.0, mLocalForceDrag=1.0, mLocalForceLift=1.0, mDamping=1.0,
    mConstraintDamping=1.0, mVelocityDamping=1.0, mGroundAttach=1.0, mGravityScale=1.0, mPossessionTime=1.0,
    mFriction=1.0, mBounce=1.0, mChainLink=1.0, mLateralLink=1.0, mBendingLink=1.0, mLongRangeAttachment=1.0,
    mCone=1.0, mActorFictitiousForce=1.0, mActorCentrifugal=1.0, mActorImpulse=1.0, mActorRotDrag=1.0,
    mActorTransDrag=1.0, mChainRootFictitiousForce=1.0, mChainRootCentrifugal=1.0, mChainRootImpulse=1.0,
    mChainRootRotDrag=1.0, mChainRootTransDrag=1.0, mBodyDrag=1.0, mBodyLift=1.0)
# His scene. mCollisionCachableRange is 0 in his asset; a 0 here would not be saved (the editor's default is 0 and
# the game's is not), so it takes the 10 Vincent's PC0011_00_BNM has.
SCENE = dict(
    m_IsEnable=True, m_EnableGroundCollision=True, mAccurateGroundCollision=True, mCollisionBVH=True, m_SubStep=2,
    mNetworkIter=2, mLateralIter=2, mCollisionIter=1, mCollisionCachableRange=10.0, m_Dt=1.0 / 30.0,
    m_Gravity=Vec((0.0, -981.0, 0.0)), mFpsCorrection=[FPS_CORRECTION])
# every group: his hair and pants groups' solver settings (the same)
GROUP = dict(
    m_IsEnable=True, m_EnableGround=False, mReferenceFrameUpdateMode=3, m_RefUpVec=3, mIsCollisionResampleCapsule=2,
    mCollisionResampleCapsuleStep=0.0, mCollisionBalance=1.0, mWindScale=1.0, mLocalForceScale=1.0,
    mParkRateScale=1.0, mActorFictitiousForceScale=1.0, mActorCentrifugalScale=1.0, mActorImpulseScale=1.0,
    mActorRotDragScale=1.0, mActorTransDragScale=1.0, mChainRootFictitiousForceScale=1.0,
    mChainRootCentrifugalScale=1.0, mChainRootImpulseScale=1.0, mChainRootRotDragScale=1.0,
    mChainRootTransDragScale=1.0, mBodyDragScale=1.0, mBodyLiftScale=1.0, mFpsCorrection=[FPS_CORRECTION])
BODY_KEYS = ['m_IsKinematic', 'm_IsCollision', 'm_Damping', 'mVelocityDamping', 'mConstraintDamping', 'm_Bounciness',
             'm_Friction', 'mGroundAttach', 'm_Mass', 'mGravityScale', 'm_Radius', 'm_WindDrag', 'm_WindLift',
             'mLFRootRotWeight', 'm_ParkRate', 'm_MaxLF', 'm_LFdrag', 'm_LFlift', 'mActorFictitiousForce',
             'mActorCentrifugal', 'mActorImpulse', 'mActorRotDrag', 'mActorTransDrag', 'mChainRootFictitiousForce',
             'mChainRootCentrifugal', 'mChainRootImpulse', 'mChainRootRotDrag', 'mChainRootTransDrag', 'mBodyDrag',
             'mBodyLift']


def body_values(*values):
    assert len(values) == len(BODY_KEYS)
    return dict(zip(BODY_KEYS, values))


# his top hair (Hair_Top: C_HairFL_a_Phy, its root; b and c, its swinging bodies)
HAIR_ROOT = body_values(True, False, 6.0, 0.0, 0.6, 0.0, 0.2, 0.0, 0.1, 1.0, 1.0, 0.0, 0.1, 1.0, 0.5, 1.0, 0.5, 0.15,
                        1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.5, 1.0)
HAIR_SWING = [
    body_values(False, False, 2.0, 0.843, 0.711, 0.0, 0.1, 0.0, 0.1, 0.2, 0.5, 0.034, 0.495, 1.0, 0.25, 1.0, 0.0625,
                0.08, 0.25, 0.0, -0.1, 0.75, 0.188, 0.25, 0.0, 0.0, 0.75, 0.125, 0.071, 1.0),
    body_values(False, False, 2.0, 0.562, 0.627, 0.0, 0.1, 0.0, 0.04, 0.2, 0.5, 0.072, 0.396, 1.0, 0.13, 1.0, 0.0169,
                0.08, 0.25, 0.0, -0.1, 0.75, 0.375, 0.25, 0.0, 0.0, 0.75, 0.25, 0.038, 1.0),
]
HAIR_CONE = dict(bEnableConeAnimation=True, mOuterConeStr=0.8, mConeParentStr=0.5, mOuterOffset=ZERO,
                 mInnerOffset=ZERO, mStretchedStrength=1.0, mCompressedStrength=1.0, mLinkParentStrength=1.0,
                 bIsBending=False, bEnableJointTwist=False, bEnableLengthAnimation=False)
# his pants flaps (Bottom_R: R_StduPantsC a and b, both swinging; a root that follows the animation like his
# collider bodies' values with the flap's own damping)
CLOTH_ROOT = body_values(True, False, 3.0, 0.0, 0.6, 0.0, 0.2, 0.0, 0.5, 1.0, 1.0, 1.0, 0.15, 1.0, 1.0, 15.0, 1.0,
                         0.15, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0)
CLOTH_SWING = [
    body_values(False, False, 3.0, 0.3, 0.6, 0.0, 0.2, 0.0, 0.7, 0.35, 1.0, 0.022, 2.25, 1.0, 1.0, 15.0, 1.0, 0.15,
                0.35, 0.0, 0.3, 0.1, 0.1, 0.35, 0.0, 0.3, 0.1, 0.1, 0.15, 0.2),
    body_values(False, False, 3.0, 0.3, 0.6, 0.0, 0.2, 0.0, 0.25, 0.35, 2.3, 0.252, 0.45, 1.0, 0.1, 3.0, 0.1, 0.15,
                0.35, 0.0, 0.3, 0.1, 0.1, 0.35, 0.0, 0.3, 0.1, 0.1, 0.15, 0.2),
]
CLOTH_CONE = dict(bEnableConeAnimation=True, mOuterConeStr=0.8, mConeParentStr=0.6, mOuterOffset=ZERO,
                  mInnerOffset=ZERO, mStretchedStrength=1.0, mCompressedStrength=1.0, mLinkParentStrength=1.0,
                  bIsBending=False, bEnableJointTwist=False, bEnableLengthAnimation=False)
# the links between his neighbouring flaps' tips
HEM_LINK = dict(mStretchedStrength=0.8, mCompressedStrength=0.8, mLinkParentStrength=0.5, bIsBending=False,
                bEnableJointTwist=False, bEnableLengthAnimation=False)
# his leg collision bodies (Bottom_R_Col: R_UpperLeg_a)
COLLIDER = body_values(True, True, 0.0, 0.0, 0.6, 0.0, 0.2, 0.0, 0.5, 1.0, 9.0, 1.0, 0.15, 1.0, 1.0, 15.0, 1.0, 0.15,
                       1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0)
SHAPE = dict(mPlaneThickness=0.0, mPlaneOffset=0.0, mCapsuleConcaveRatio=0.0, bIsInverse=False, bIsInfinity=False,
             bResampleStart=False)


# ---------------------------------------------------------------------------------------------------------------
def body_name(bone):
    return 'Bdy_%s_0_1' % bone


def body(name, parent, group, values, **extra):
    b = dict(mName=name, mParentName=parent, mGroupName=group, m_LocalTransform=ZERO, m_LocalRotation=IDENTITY,
             mBodyConstraints=[])
    b.update(values)
    b.update(extra)
    return b


def at_depth(profile, k):
    return profile[min(k, len(profile) - 1)]


def build_spec():
    """Everything the asset gets, as plain data."""
    bodies, cones, links, shapes = [], [], [], []

    def shape(kind, members, receivers=(), repulsors=()):
        shapes.append(dict(SHAPE, mShapeId=len(shapes), mType=kind, mBodies=list(members),
                           mReceiverGroups=list(receivers), mRepulsorGroups=list(repulsors)))

    def add_chain(group, bones, root_values, swing_profile, cone_base, limits, receivers=(), radius=None):
        names = [body_name(b) for b in bones]
        bodies.append(body(names[0], bones[0], group, root_values))
        for k, bone in enumerate(bones[1:]):
            values = dict(at_depth(swing_profile, k))
            if radius is not None:
                values['m_Radius'] = radius
            bodies.append(body(names[k + 1], bone, group, values))
            limit_y, limit_z, inner = at_depth(limits, k)
            cones.append(dict(cone_base, mA=names[k], mB=names[k + 1], mLimitY=limit_y, mLimitZ=limit_z, mInnerConeStr=inner))
            if receivers:
                shape('sphere', [names[k + 1]], receivers=receivers)
        return names

    # his legs push the jacket hem away
    for upper, lower in LEGS:
        for bone in (upper, lower):
            bodies.append(body('Bdy_Sta_%s_0_1' % bone, bone, 'Col_leg', COLLIDER, m_Radius=LEG_RADIUS[bone]))
        shape('capsule', ['Bdy_Sta_%s_0_1' % upper, 'Bdy_Sta_%s_0_1' % lower], repulsors=['Col_leg'])
    for bones in HAIR:
        add_chain('Hair', bones, HAIR_ROOT, HAIR_SWING, HAIR_CONE, HAIR_LIMITS)
    for bones in NECKLACE:
        heavy = [dict(v, m_Mass=v['m_Mass'] * 2.0, mGravityScale=0.6) for v in CLOTH_SWING]
        add_chain('Necklace', bones, CLOTH_ROOT, heavy, CLOTH_CONE, NECKLACE_LIMITS, radius=1.0)
    for bones in HOOD:
        add_chain('Hood', bones, CLOTH_ROOT, CLOTH_SWING, CLOTH_CONE, CLOTH_LIMITS)
    for bones in SLEEVES:
        add_chain('Sleeve', bones, CLOTH_ROOT, CLOTH_SWING, CLOTH_CONE, CLOTH_LIMITS)
    hem = []
    for bones in JACKET:
        hem.append(add_chain('Jacket', bones, CLOTH_ROOT, CLOTH_SWING, CLOTH_CONE, CLOTH_LIMITS, receivers=['Col_leg'],
                             radius=HEM_RADIUS))
    for a, b in zip(hem, hem[1:]):                   # neighbouring pieces, at each swinging depth
        for k in (1, 2):
            links.append(dict(HEM_LINK, mA=a[k], mB=b[k]))
    # the zip pull hangs from the hem's swinging R_susoA2
    names = [body_name(b) for b in ZIP_PULL]
    for k, bone in enumerate(ZIP_PULL[1:]):
        values = dict(at_depth(CLOTH_SWING, 1), m_Mass=0.1, m_Radius=0.5)
        bodies.append(body(names[k + 1], bone, 'Jacket', values))
        limit_y, limit_z, inner = at_depth(CLOTH_LIMITS, 1)
        cones.append(dict(CLOTH_CONE, mA=names[k], mB=names[k + 1], mLimitY=limit_y, mLimitZ=limit_z, mInnerConeStr=inner))
    for bones in BELT:
        add_chain('Belt', bones, CLOTH_ROOT, CLOTH_SWING, CLOTH_CONE, CLOTH_LIMITS)
    for bones in SHOE_ZIPS:
        light = [dict(v, m_Mass=0.1, m_Radius=0.5) for v in CLOTH_SWING]
        add_chain('ShoeZip', bones, CLOTH_ROOT, light, CLOTH_CONE, [(30.0, 30.0, 0.3)])

    groups = [dict(GROUP, m_GroupName=name) for name in GROUPS]
    spec = dict(m_VersionNo=VERSION_NO, mSceneManager=dict(SCENE), mGroups=groups, mBodies=bodies, mLinks=links,
                mCones=cones, mShapes=shapes, mCollisionCliques=[])
    check_spec(spec)
    return spec


def chains():
    return HAIR + NECKLACE + HOOD + SLEEVES + JACKET + BELT + SHOE_ZIPS + [ZIP_PULL]


def bones_used():
    used = set([HAIR_PARENT]) | set(LEG_RADIUS)
    for bones in chains():
        used |= set(bones)
    return used


def check_spec(spec):
    problems = []
    groups = [g['m_GroupName'] for g in spec['mGroups']]
    if groups[0] != 'default' or len(set(groups)) != len(groups):
        problems.append('groups must start with default and be unique')
    names = [b['mName'] for b in spec['mBodies']]
    if len(set(names)) != len(names):
        problems.append('two bodies share a name')
    dynamic_bones = [b['mParentName'] for b in spec['mBodies'] if not b['m_IsKinematic']]
    if len(set(dynamic_bones)) != len(dynamic_bones):
        problems.append('a bone has two swinging bodies')
    for b in spec['mBodies']:
        if b['mGroupName'] not in groups:
            problems.append('body %s is in group %s, which is not a group' % (b['mName'], b['mGroupName']))
        if b['mParentName'] not in bones_used():
            problems.append('body %s hangs on %s, which this does not check on the mesh' % (b['mName'], b['mParentName']))
    known = set(names)
    for c in spec['mCones'] + spec['mLinks']:
        if c['mA'] not in known or c['mB'] not in known:
            problems.append('link %s-%s names a body that is not there' % (c['mA'], c['mB']))
    by_name = dict((b['mName'], b) for b in spec['mBodies'])
    for c in spec['mCones']:
        if by_name[c['mB']]['m_IsKinematic']:
            problems.append('cone %s-%s ends on a body that follows the animation' % (c['mA'], c['mB']))
    swinging = [b['mName'] for b in spec['mBodies'] if not b['m_IsKinematic']]
    ends = [c['mB'] for c in spec['mCones']]
    if sorted(ends) != sorted(swinging):
        problems.append('every swinging body must hang on exactly one cone')
    for s in spec['mShapes']:
        if any(m not in known for m in s['mBodies']):
            problems.append('shape %d names a body that is not there' % s['mShapeId'])
        if any(g not in groups for g in s['mReceiverGroups'] + s['mRepulsorGroups']):
            problems.append('shape %d names a group that is not there' % s['mShapeId'])
        if s['mType'] not in ('sphere', 'capsule') or len(s['mBodies']) != (1 if s['mType'] == 'sphere' else 2):
            problems.append('shape %d is not a sphere on one body or a capsule between two' % s['mShapeId'])
    if [s['mShapeId'] for s in spec['mShapes']] != list(range(len(spec['mShapes']))):
        problems.append('shape ids are not 0..n-1')
    if problems:
        raise ValueError('Sora Bonamik spec: ' + '; '.join(problems))


# ---------------------------------------------------------------------------------------------------------------
# Editor part (as make_safer_bonamik.py)

def say(text):
    unreal.log('SoraBonamik: ' + text)


STRUCT_OF_LIST = {'mGroups': 'SQEX_BonamikSolverDesc', 'mBodies': 'SQEX_BonamikBodyDesc',
                  'mLinks': 'SQEX_BonamikSimpleLinkDesc', 'mCones': 'SQEX_BonamikConeLinkDesc',
                  'mShapes': 'SQEX_BonamikShapeDesc', 'mCollisionCliques': 'SQEX_BonamikCollisionCliqueDesc',
                  'mFpsCorrection': 'SQEX_BonamikFpsCorrectionDesc', 'mBodyConstraints': 'SQEX_BonamikBodyConstraintDesc'}


def to_ue(key, value):
    if isinstance(value, Quat):
        return unreal.Quat(*value)
    if isinstance(value, Vec):
        return unreal.Vector(*value)
    if isinstance(value, list):
        if any(isinstance(v, dict) for v in value):
            return [make_struct(STRUCT_OF_LIST[key], v) for v in value]
        if key in ('mFpsCorrection', 'mBodyConstraints', 'mCollisionCliques') and value:
            raise ValueError('%s: struct entries expected' % key)
        return list(value)
    return value


def make_struct(name, fields):
    struct = getattr(unreal, name)()
    for key, value in fields.items():
        struct.set_editor_property(key, to_ue(key, value))
    return struct


def same(expected, actual):
    if isinstance(expected, Quat):
        return all(same(e, a) for e, a in zip(expected, (actual.x, actual.y, actual.z, actual.w)))
    if isinstance(expected, Vec):
        return all(same(e, a) for e, a in zip(expected, (actual.x, actual.y, actual.z)))
    if isinstance(expected, list):
        actual = list(actual)
        if len(actual) != len(expected):
            return False
        return all(check_struct_ok(e, a) if isinstance(e, dict) else same(e, a) for e, a in zip(expected, actual))
    if isinstance(expected, bool):
        return bool(actual) == expected
    if isinstance(expected, float):
        return abs(float(actual) - expected) <= 1e-5 * max(1.0, abs(expected))
    if isinstance(expected, int):
        return int(actual) == expected
    return str(actual) == str(expected)


def check_struct_ok(fields, struct):
    return all(same(v, struct.get_editor_property(k)) for k, v in fields.items())


def check_struct(where, struct, fields, problems):
    for key, value in fields.items():
        actual = struct.get_editor_property(key)
        if not same(value, actual):
            problems.append('%s.%s is %r, expected %r' % (where, key, actual, value))


def mesh_bones(mesh):
    component = unreal.new_object(unreal.SkeletalMeshComponent)
    component.set_skeletal_mesh(mesh)
    names = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
    parents = dict((name, str(component.get_parent_bone(name))) for name in names)
    return names, parents


def check_mesh(mesh, report):
    names, parents = mesh_bones(mesh)
    report['mesh_bones'] = len(names)
    if not names:
        raise RuntimeError('the mesh bone list came back empty')
    missing = sorted(b for b in bones_used() if b not in parents)
    if missing:
        raise RuntimeError('PC0000_00_S has no bones named %s' % ', '.join(missing))
    for bones in chains():
        for parent, child in zip(bones, bones[1:]):
            if parents[child] != parent:
                raise RuntimeError('bone %s hangs under %s in PC0000_00_S, not under %s' % (child, parents[child], parent))
    for bones in HAIR:
        if parents[bones[0]] != HAIR_PARENT:
            raise RuntimeError('hair %s hangs under %s, not under %s' % (bones[0], parents[bones[0]], HAIR_PARENT))


def load_or_create_asset(report):
    library = unreal.EditorAssetLibrary
    if library.does_asset_exist(ASSET_PATH):
        asset = library.load_asset(ASSET_PATH)
        if not isinstance(asset, unreal.SQEX_BonamikAsset):
            raise RuntimeError('%s exists but is a %s, not a SQEX_BonamikAsset' % (ASSET_PATH, type(asset).__name__))
        report['asset_action'] = 'rebuilt'
        return asset
    factory = unreal.DataAssetFactory()
    try:
        factory.set_editor_property('data_asset_class', unreal.SQEX_BonamikAsset.static_class())
    except Exception:
        pass
    asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(ASSET_NAME, MODEL_DIR, unreal.SQEX_BonamikAsset, factory)
    if asset is None:
        raise RuntimeError('could not create ' + ASSET_PATH)
    report['asset_action'] = 'created'
    return asset


LISTS = ['mGroups', 'mBodies', 'mLinks', 'mCones', 'mShapes', 'mCollisionCliques']
EMPTY_REGULAR = ['mLRAs', 'mKDIs', 'mPossessions']
EMPTY_LEGACY = ['m_Solvers', 'm_Bodies', 'm_Links', 'm_Planes', 'm_ShapeMatchings', 'm_Possessions']


def fill_asset(asset, spec):
    asset.set_editor_property('m_VersionNo', spec['m_VersionNo'])
    asset.set_editor_property('mSceneManager', make_struct('SQEX_BonamikSceneManagerDesc', spec['mSceneManager']))
    for key in LISTS:
        asset.set_editor_property(key, [make_struct(STRUCT_OF_LIST[key], v) for v in spec[key]])
    for key in EMPTY_REGULAR + EMPTY_LEGACY:
        asset.set_editor_property(key, [])
    asset.set_editor_property('v2', None)


def verify_asset(asset, spec):
    problems = []
    if int(asset.get_editor_property('m_VersionNo')) != VERSION_NO:
        problems.append('m_VersionNo is wrong')
    if asset.get_editor_property('v2') is not None:
        problems.append('the asset still has v2 data')
    check_struct('mSceneManager', asset.get_editor_property('mSceneManager'), spec['mSceneManager'], problems)
    for key in LISTS:
        items = list(asset.get_editor_property(key))
        if len(items) != len(spec[key]):
            problems.append('%s has %d entries, expected %d' % (key, len(items), len(spec[key])))
            continue
        for i, (item, fields) in enumerate(zip(items, spec[key])):
            check_struct('%s[%d]' % (key, i), item, fields, problems)
    for key in EMPTY_REGULAR + EMPTY_LEGACY:
        if len(asset.get_editor_property(key)):
            problems.append(key + ' is not empty')
    return problems


def main():
    saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
    out = os.path.join(saved, 'SoraBonamik')
    if not os.path.isdir(out):
        os.makedirs(out)
    report = dict(ok=False, asset=ASSET_PATH, mesh=MESH_PATH, warnings=[], saved=[])
    try:
        spec = build_spec()
        report['bodies'] = len(spec['mBodies'])
        report['swinging'] = sum(1 for b in spec['mBodies'] if not b['m_IsKinematic'])
        report['cones'] = len(spec['mCones'])
        report['links'] = len(spec['mLinks'])
        report['shapes'] = len(spec['mShapes'])
        report['groups'] = [g['m_GroupName'] for g in spec['mGroups']]
        mesh = unreal.EditorAssetLibrary.load_asset(MESH_PATH)
        if not isinstance(mesh, unreal.SkeletalMesh):
            raise RuntimeError('could not load the skeletal mesh ' + MESH_PATH)
        check_mesh(mesh, report)
        asset = load_or_create_asset(report)
        fill_asset(asset, spec)
        problems = verify_asset(asset, spec)
        if problems:
            report['problems'] = problems[:50]
            raise RuntimeError('%d values did not come back as written, first: %s' % (len(problems), problems[0]))
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset, False):
            raise RuntimeError('could not save ' + ASSET_PATH)
        report['saved'].append(ASSET_PATH)
        report['ok'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        unreal.log_error('SoraBonamik: ' + report['error'])
    report['done'] = True
    with open(os.path.join(out, 'report.json'), 'w') as f:
        json.dump(report, f, indent=1)
    return report


if unreal is not None and __name__ == '__main__':
    result = json.dumps(main(), indent=1)
