"""Safer Sephiroth's Bonamik, made as a regular Bonamik.

This builds the same Bonamik 3.x data that the game's own characters carry (Sephiroth's PC0010_00_BNM, Vincent's
PC0011_00_BNM): bodies, cone links, links, collision shapes and groups. It does not use the v2 sub-object that the
transformed Sephiroth's wings use. Every value comes from Sephiroth's own Bonamik, scaled to Safer's size where it
is a size:
  * hair: his three locks (C_HairM a..j, L_HairE a..h, R_HairD a..h). The value along each lock (damping, wind, the
    body's own drag, the forces from his moves, cone limits and strengths) is Sephiroth's long hair (L_HairLongA)
    at the same point along the lock. Gravity is turned well down so the hair keeps floating as his animations
    show it, and swings and trails as he moves.
  * feathers: the 30 feathers of his six wings (each feather's a_Phy follows the wing, the rest swing), stiff like
    Sephiroth's collar pieces, following the wing's animation.
  * collisions: his head, neck, back, shoulders and arms push his hair away, so it does not pass through him.

Run it in the End editor: File > Execute Python Script... > pick this file.
(With the editor closed: run_safer_bonamik.cmd next to this file does this and packages the project.)

It creates /Game/Character/Player/PC0010_999_Safer_Sephiroth/Model/PC0010_999_BNM_Regular (or rebuilds it), puts it
in the PC0010_999 mesh's Asset User Data (SQEX_KBD_AssetUserData > Bonamik Data List) in place of PC0010_999_BNM (the
v2 one: it stays in the folder, unused), checks everything it wrote, saves both assets and writes
Saved/SaferBonamik/report.json. Running it again rebuilds the same asset. The editor's Bonamik preview shows it.
"""
import json
import os
import traceback

try:
    import unreal
except ImportError:  # imported outside the editor for the offline checks
    unreal = None

MODEL_DIR = '/Game/Character/Player/PC0010_999_Safer_Sephiroth/Model'
MESH_PATH = MODEL_DIR + '/PC0010_999'
ASSET_NAME = 'PC0010_999_BNM_Regular'
ASSET_PATH = MODEL_DIR + '/' + ASSET_NAME
OLD_ASSET_PATH = MODEL_DIR + '/PC0010_999_BNM'   # the v2 one this replaces on the mesh
VERSION_NO = 30713                                # Bonamik 3.7.13, as the game's own regular Bonamik assets

# ---------------------------------------------------------------------------------------------------------------
# TUNING (change, then run it again)
HAIR_GRAVITY = 0.05      # Sephiroth's hair: 0.35. Lower keeps Safer's hair floating as animated; 0 = no gravity.
FEATHER_GRAVITY = 0.1    # Sephiroth's collar: 0.3.
HAIR_RADIUS = 6.0        # thickness of a hair body for collisions (Safer's units; Sephiroth's hair 0.5-0.8 at his size)
FEATHER_INNER = 0.5      # how hard a feather is pulled back to the wing's animation (Sephiroth's collar 0.6, hair 0.05-0.3)
FEATHER_LIMIT = 12.0     # how far a feather may swing from the animation, in degrees
HAIR_LIMIT_SCALE = 1.0   # 1 = Sephiroth's hair cone limits (15 at the root to 45 at the tip); smaller = stiffer hair
# Collision bodies on his body: bone -> radius (Safer's units: his head is about 30 across from its middle).
COLLIDER_RADIUS = {
    'C_Spine_b': 38.0, 'C_Spine_c': 40.0, 'C_Spine_d': 40.0, 'C_Neck_a': 24.0, 'C_Head_a': 24.0,
    'L_Shoulder_a': 28.0, 'R_Shoulder_a': 28.0,
    'L_UpperArm_a': 22.0, 'L_Forearm_a': 18.0, 'L_Hand_a': 14.0,
    'R_UpperArm_a': 22.0, 'R_Forearm_a': 18.0, 'R_Hand_a': 14.0,
}
SKULL_RADIUS = 30.0
SKULL_OFFSET = (23.0, 0.0, 0.0)   # from C_Head_a to the middle of his skull, in the head bone's axes (X is up there)

# ---------------------------------------------------------------------------------------------------------------
# Safer's bones (checked against the mesh when it runs)
HAIR_LOCKS = [
    ('HairM', ['C_HairM_%s_Phy' % c for c in 'abcdefghij']),
    ('HairE', ['L_HairE_%s_Phy' % c for c in 'abcdefgh']),
    ('HairD', ['R_HairD_%s_Phy' % c for c in 'abcdefgh']),
]
HAIR_PARENT = 'C_Head_a'
FEATHER_BONES = {
    # feather -> its bones (a_Phy follows the wing; the rest swing)
    'A01': 'ab', 'A02': 'ab', 'A03': 'abc', 'A04': 'abc', 'A05': 'abcd',
    'B01': 'ab', 'B02': 'ab', 'B03': 'ab', 'B04': 'ab', 'B05': 'ab',
    'C01': 'ab', 'C02': 'ab', 'C03': 'ab', 'C04': 'ab', 'C05': 'ab',
}
FEATHER_CHAINS = []   # (group, bones)
for _side in 'LR':
    for _wing in 'ABC':
        for _n in range(1, 6):
            _key = '%s%02d' % (_wing, _n)
            FEATHER_CHAINS.append(('Feather%s%s' % (_wing, _side),
                                   ['%s_Feather%s_%s_Phy' % (_side, _key, c) for c in FEATHER_BONES[_key]]))
# collision capsules between bones (each end is that bone's collision body), and the group they make
CAPSULES = [
    ('Col_body', 'C_Spine_b', 'C_Spine_c'), ('Col_body', 'C_Spine_c', 'C_Spine_d'), ('Col_body', 'C_Spine_d', 'C_Neck_a'),
    ('Col_body', 'C_Neck_a', 'C_Head_a'),
    ('Col_body', 'L_Shoulder_a', 'L_UpperArm_a'), ('Col_body', 'R_Shoulder_a', 'R_UpperArm_a'),
    ('Col_arm', 'L_UpperArm_a', 'L_Forearm_a'), ('Col_arm', 'L_Forearm_a', 'L_Hand_a'),
    ('Col_arm', 'R_UpperArm_a', 'R_Forearm_a'), ('Col_arm', 'R_Forearm_a', 'R_Hand_a'),
]
COLLIDER_GROUP = {'L_UpperArm_a': 'Col_arm', 'L_Forearm_a': 'Col_arm', 'L_Hand_a': 'Col_arm',
                  'R_UpperArm_a': 'Col_arm', 'R_Forearm_a': 'Col_arm', 'R_Hand_a': 'Col_arm'}
HAIR_RECEIVES = ['Col_body', 'Col_head', 'Col_arm']
GROUPS = (['default', 'Col_body', 'Col_head', 'Col_arm'] + [g for g, _ in HAIR_LOCKS] +
          ['FeatherAL', 'FeatherBL', 'FeatherCL', 'FeatherAR', 'FeatherBR', 'FeatherCR'])


class Vec(tuple):
    """FVector"""


class Quat(tuple):
    """FQuat (x, y, z, w)"""


ZERO = Vec((0.0, 0.0, 0.0))
IDENTITY = Quat((0.0, 0.0, 0.0, 1.0))

# ---------------------------------------------------------------------------------------------------------------
# Sephiroth's PC0010_00_BNM (Bonamik 3.7.13), the values this copies. Only the fields the game's regular Bonamik
# data carries are set; the rest stay at the editor's defaults as in his asset.
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
    m_IsEnable=True, m_EnableGroundCollision=True, mAccurateGroundCollision=True, mPerJointWindSample=True,
    mCollisionBVH=True, m_SubStep=2, mNetworkIter=2, mLateralIter=2, mCollisionIter=1, mCollisionCachableRange=10.0,
    m_Dt=1.0 / 30.0, m_Gravity=Vec((0.0, -981.0, 0.0)), mFpsCorrection=[FPS_CORRECTION])
# every group: his hair groups' solver settings
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
    return dict(zip(BODY_KEYS, values))


# his long hair's root (L_HairLongA_a_Phy) and its seven swinging bodies (b..h), root to tip
HAIR_ROOT = body_values(True, False, 0.2, 0.0, 0.6, 0.1, 0.05, 0.0, 1.0, 1.0, 1.0, 1.0, 0.15, 0.0, 0.0, 1000000.0,
                        0.1, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0)
HAIR_SWING = [
    body_values(False, False, 1.0, 0.75, 0.6, 0.1, 0.075, 0.0, 1.0, 0.35, 0.75, 0.002, 0.084, 0.0, 0.0, 1000000.0,
                0.1, 1.0, 0.04, 0.3, -0.03, 0.02, 0.015, 0.04, 0.3, -0.05, 0.02, 0.015, 0.01, 0.005),
    body_values(False, False, 1.0, 0.75, 0.6, 0.1, 0.075, 0.0, 1.0, 0.35, 0.55, 0.004, 0.168, 0.0, 0.0, 1000000.0,
                0.1, 1.0, 0.09, 0.3, -0.05, 0.045, 0.04, 0.09, 0.3, -0.05, 0.045, 0.04, 0.13, 0.065),
    body_values(False, False, 1.0, 0.75, 0.6, 0.1, 0.075, 0.0, 1.0, 0.35, 0.75, 0.007, 0.337, 0.0, 0.0, 1000000.0,
                0.1, 1.0, 0.16, 0.3, -0.07, 0.08, 0.06, 0.16, 0.3, -0.05, 0.08, 0.06, 0.25, 0.125),
    body_values(False, False, 1.0, 0.75, 0.6, 0.1, 0.075, 0.0, 1.0, 0.35, 0.8, 0.013, 0.675, 0.0, 0.0, 1000000.0,
                0.1, 1.0, 0.23, 0.3, -0.09, 0.115, 0.08, 0.23, 0.3, -0.05, 0.115, 0.08, 0.37, 0.185),
    body_values(False, False, 1.0, 0.75, 0.6, 0.1, 0.075, 0.0, 1.0, 0.35, 0.8, 0.026, 1.35, 0.0, 0.0, 1000000.0,
                0.1, 1.0, 0.3, 0.3, -0.05, 0.15, 0.1, 0.3, 0.3, -0.05, 0.15, 0.1, 0.5, 0.25),
    body_values(False, False, 1.0, 0.75, 0.6, 0.1, 0.075, 0.0, 1.0, 0.35, 0.8, 0.04, 2.025, 0.0, 0.0, 1000000.0,
                0.1, 1.0, 0.3, 0.3, -0.05, 0.15, 0.1, 0.3, 0.3, -0.05, 0.15, 0.1, 0.5, 0.25),
    body_values(False, False, 1.0, 0.75, 0.6, 0.1, 0.075, 0.0, 1.0, 0.35, 0.8, 0.06, 3.038, 0.0, 0.0, 1000000.0,
                0.1, 1.0, 0.3, 0.3, -0.05, 0.15, 0.1, 0.3, 0.3, -0.05, 0.15, 0.1, 0.5, 0.25),
]
# his long hair's cones, root to tip: (limit Y, limit Z, inner strength)
HAIR_CONE_STEPS = [(15.0, 20.0, 0.3), (20.0, 20.0, 0.15), (35.0, 35.0, 0.1), (35.0, 35.0, 0.05), (45.0, 45.0, 0.05),
                   (45.0, 45.0, 0.05), (45.0, 45.0, 0.05)]
HAIR_CONE = dict(bEnableConeAnimation=True, mOuterConeStr=0.8, mConeParentStr=0.5, mOuterOffset=ZERO,
                 mInnerOffset=ZERO, mStretchedStrength=1.0, mCompressedStrength=0.8, mLinkParentStrength=0.95,
                 bIsBending=False, bEnableJointTwist=False, bEnableLengthAnimation=False)
# his long hair's bending link to his head (keeps a lock's base from folding into the head)
BEND_LINK = dict(mStretchedStrength=0.2, mCompressedStrength=0.8, mLinkParentStrength=0.1, bIsBending=True,
                 bEnableJointTwist=False, bEnableLengthAnimation=False)
# his collar (L_CollarA): the piece's root and its swinging body; its cone, following the animation here
FEATHER_ROOT = body_values(True, False, 0.0, 0.0, 0.6, 0.0, 0.2, 0.0, 0.5, 1.0, 1.5, 1.0, 0.15, 1.0, 1.0, 15.0,
                           1.0, 0.15, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0)
FEATHER_SWING = body_values(False, False, 0.5, 0.1, 0.6, 0.1, 0.1, 0.0, 0.5, 0.3, 0.75, 0.025, 0.15, 1.0, 0.1, 15.0,
                            0.01, 0.15, 0.2, 0.1, -0.1, 0.2, 0.2, 0.2, 0.1, -0.1, 0.2, 0.2, 1.0, 1.0)
FEATHER_CONE = dict(bEnableConeAnimation=True, mOuterConeStr=0.8, mConeParentStr=0.8, mOuterOffset=ZERO,
                    mInnerOffset=ZERO, mStretchedStrength=1.0, mCompressedStrength=1.0, mLinkParentStrength=0.85,
                    bIsBending=False, bEnableJointTwist=False, bEnableLengthAnimation=True)
# his body's collision bodies (Col_body: C_Spine_b)
COLLIDER = body_values(True, True, 0.0, 0.0, 0.6, 0.0, 0.2, 0.0, 0.5, 1.0, 1.0, 1.0, 0.15, 1.0, 1.0, 15.0,
                       1.0, 0.15, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0)
SHAPE = dict(mPlaneThickness=0.0, mPlaneOffset=0.0, mCapsuleConcaveRatio=0.0, bIsInverse=False, bIsInfinity=False,
             bResampleStart=False)


# ---------------------------------------------------------------------------------------------------------------
def chain_body_name(bone):
    return 'Bdy_%s_0_1' % bone


def body(name, parent, group, values, **extra):
    b = dict(mName=name, mParentName=parent, mGroupName=group, m_LocalTransform=ZERO, m_LocalRotation=IDENTITY,
             mBodyConstraints=[])
    b.update(values)
    b.update(extra)
    return b


def along(profile, k, n):
    """The entry of a root-to-tip profile at swinging body k of n (spread over the profile's length)."""
    if n <= 1:
        return profile[0]
    return profile[int(round(k * (len(profile) - 1) / float(n - 1)))]


def build_spec():
    """Everything the asset gets, as plain data."""
    bodies, cones, links, shapes = [], [], [], []

    def shape(kind, members, receivers=(), repulsors=()):
        s = dict(SHAPE, mShapeId=len(shapes), mType=kind, mBodies=list(members), mReceiverGroups=list(receivers),
                 mRepulsorGroups=list(repulsors))
        shapes.append(s)

    # his body's collision bodies, one on each bone the capsules use, and his skull
    collider = {}
    for _group, a, b in CAPSULES:
        for bone in (a, b):
            if bone not in collider:
                collider[bone] = 'Bdy_Sta_%s_0_1' % bone
                bodies.append(body(collider[bone], bone, COLLIDER_GROUP.get(bone, 'Col_body'), COLLIDER,
                                   m_Radius=COLLIDER_RADIUS[bone]))
    skull = 'Bdy_Sta_%s_0_2' % HAIR_PARENT
    bodies.append(body(skull, HAIR_PARENT, 'Col_head', COLLIDER, m_Radius=SKULL_RADIUS, m_LocalTransform=Vec(SKULL_OFFSET)))
    for group, a, b in CAPSULES:
        shape('capsule', [collider[a], collider[b]], repulsors=[group])
    shape('sphere', [skull], repulsors=['Col_head'])

    # hair
    for group, bones in HAIR_LOCKS:
        names = [chain_body_name(b) for b in bones]
        bodies.append(body(names[0], bones[0], group, HAIR_ROOT))
        swinging = len(bones) - 1
        for k, bone in enumerate(bones[1:]):
            values = dict(along(HAIR_SWING, k, swinging))
            values.update(mGravityScale=HAIR_GRAVITY, m_Radius=HAIR_RADIUS)
            bodies.append(body(names[k + 1], bone, group, values))
        for k in range(swinging):
            limit_y, limit_z, inner = along(HAIR_CONE_STEPS, k, swinging)
            cone = dict(HAIR_CONE, mA=names[k], mB=names[k + 1], mLimitY=limit_y * HAIR_LIMIT_SCALE,
                        mLimitZ=limit_z * HAIR_LIMIT_SCALE, mInnerConeStr=inner)
            cones.append(cone)
        links.append(dict(BEND_LINK, mA=names[2], mB=skull))
        shape('sphere', [names[1]], receivers=HAIR_RECEIVES)
        for k in range(1, swinging):
            shape('capsule', [names[k], names[k + 1]], receivers=HAIR_RECEIVES)

    # feathers
    for group, bones in FEATHER_CHAINS:
        names = [chain_body_name(b) for b in bones]
        bodies.append(body(names[0], bones[0], group, FEATHER_ROOT))
        for k, bone in enumerate(bones[1:]):
            values = dict(FEATHER_SWING)
            values.update(mGravityScale=FEATHER_GRAVITY)
            bodies.append(body(names[k + 1], bone, group, values))
        for k in range(len(bones) - 1):
            cones.append(dict(FEATHER_CONE, mA=names[k], mB=names[k + 1], mLimitY=FEATHER_LIMIT, mLimitZ=FEATHER_LIMIT,
                              mInnerConeStr=FEATHER_INNER))

    groups = [dict(GROUP, m_GroupName=name) for name in GROUPS]
    spec = dict(m_VersionNo=VERSION_NO, mSceneManager=dict(SCENE), mGroups=groups, mBodies=bodies, mLinks=links,
                mCones=cones, mShapes=shapes, mCollisionCliques=[])
    check_spec(spec)
    return spec


def bones_used():
    used = set([HAIR_PARENT]) | set(COLLIDER_RADIUS)
    for _g, bones in HAIR_LOCKS + FEATHER_CHAINS:
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
        raise ValueError('Safer Bonamik spec: ' + '; '.join(problems))


# ---------------------------------------------------------------------------------------------------------------
# Editor part

def say(text):
    unreal.log('SaferBonamik: ' + text)


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
        if any(isinstance(v, dict) for v in value):   # (a shape's mBodies is a list of names, the asset's of structs)
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
    try:
        names, parents = mesh_bones(mesh)
    except Exception as error:  # the bones were checked offline against the skeleton too
        report['warnings'].append('could not read the mesh bones in Python: %s' % error)
        return
    report['mesh_bones'] = len(names)
    if not names:
        report['warnings'].append('the mesh bone list came back empty; bone check skipped')
        return
    missing = sorted(b for b in bones_used() if b not in parents)
    if missing:
        raise RuntimeError('PC0010_999 has no bones named %s' % ', '.join(missing))
    for _g, bones in HAIR_LOCKS + FEATHER_CHAINS:
        for parent, child in zip(bones, bones[1:]):
            if parents[child] != parent:
                raise RuntimeError('bone %s hangs under %s in PC0010_999, not under %s' % (child, parents[child], parent))
    for _g, bones in HAIR_LOCKS:
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
    except Exception:  # the factory then makes the class passed to create_asset, which is the same
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


def kbd_of(mesh):
    for data in mesh.get_editor_property('asset_user_data') or []:
        if data is not None and isinstance(data, unreal.SQEX_KBD_AssetUserData):
            return data
    return None


def attach_to_mesh(mesh, asset):
    """Puts the asset in the mesh's SQEX_KBD_AssetUserData in place of the v2 PC0010_999_BNM."""
    kbd = kbd_of(mesh)
    if kbd is None:
        kbd = unreal.new_object(unreal.SQEX_KBD_AssetUserData, mesh)
        kbd.set_editor_property('BonamikDataList', [asset])
        mesh.set_editor_property('asset_user_data', [d for d in (mesh.get_editor_property('asset_user_data') or [])] + [kbd])
        return 'added a SQEX_KBD_AssetUserData with it'
    current = [d for d in (kbd.get_editor_property('BonamikDataList') or []) if d is not None]
    paths = [d.get_path_name().split('.')[0] for d in current]
    kept = [d for d, p in zip(current, paths) if p not in (OLD_ASSET_PATH, ASSET_PATH)]
    wanted = kept + [asset]
    if [d.get_path_name() for d in current] == [d.get_path_name() for d in wanted]:
        return 'already its Bonamik'
    kbd.set_editor_property('BonamikDataList', wanted)
    replaced = OLD_ASSET_PATH in paths
    return ('in place of PC0010_999_BNM' if replaced else 'added') + ' (its Bonamik list now: %s)' % ', '.join(
        d.get_name() for d in wanted)


def verify_mesh(mesh, asset):
    kbd = kbd_of(mesh)
    if kbd is None:
        return ['the mesh has no SQEX_KBD_AssetUserData']
    paths = [d.get_path_name().split('.')[0] for d in (kbd.get_editor_property('BonamikDataList') or []) if d is not None]
    problems = []
    if ASSET_PATH not in paths:
        problems.append('the mesh does not list ' + ASSET_NAME)
    if OLD_ASSET_PATH in paths:
        problems.append('the mesh still lists PC0010_999_BNM')
    return problems


def in_commandlet():
    try:
        return '-run=' in unreal.SystemLibrary.get_command_line().lower()
    except Exception:
        return False


def main():
    saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
    out = os.path.join(saved, 'SaferBonamik')
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
        report['mesh_action'] = attach_to_mesh(mesh, asset)
        problems = verify_mesh(mesh, asset)
        if problems:
            raise RuntimeError(problems[0])
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset, False):
            raise RuntimeError('could not save ' + ASSET_PATH)
        report['saved'].append(ASSET_PATH)
        if not report['mesh_action'].startswith('already'):
            if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, False):
                raise RuntimeError('could not save ' + MESH_PATH)
            report['saved'].append(MESH_PATH)
        library = getattr(unreal, 'RebirthAssetLibrary', None)
        if library is not None and hasattr(library, 'cook_asset_to_file'):  # a cooked copy, to compare with the game's
            cooked = os.path.join(out, 'cooked', ASSET_NAME + '.uasset')
            try:
                message = library.cook_asset_to_file(ASSET_PATH, cooked)
                report['cooked_copy'] = cooked if message is not None else None
                report['cook_message'] = message if message is not None else 'cook failed (see the Output Log)'
            except Exception as error:
                report['warnings'].append('no cooked copy: %s' % error)
        report['ok'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        unreal.log_error('SaferBonamik: ' + report['error'])
    report['done'] = True
    with open(os.path.join(out, 'report.json'), 'w') as f:
        json.dump(report, f, indent=1)
    if report['ok']:
        text = ('%s %s: %d bodies (%d swinging: hair and feathers), %d cones, %d links, %d collision shapes.\n'
                'PC0010_999 mesh: %s.\nSaved: %s.' % (
                    ASSET_NAME, report['asset_action'], report['bodies'], report['swinging'], report['cones'],
                    report['links'], report['shapes'], report['mesh_action'],
                    ', '.join(p.rsplit('/', 1)[-1] for p in report['saved'])))
        for warning in report['warnings']:
            text += '\nNote: ' + warning
    else:
        text = ('Something failed (%s):\n%s' % (
            'saved before it: ' + ', '.join(report['saved']) if report['saved'] else 'nothing was saved',
            report['error'].strip().splitlines()[-1]))
    say(text.replace('\n', ' | '))
    if not in_commandlet():
        unreal.EditorDialog.show_message('Safer Bonamik', text, unreal.AppMsgType.OK)


if unreal is not None and __name__ == '__main__':
    main()
