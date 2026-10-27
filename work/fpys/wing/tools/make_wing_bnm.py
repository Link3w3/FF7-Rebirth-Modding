"""The wing's own regular (3.x) Bonamik: the transformed Sephiroth's wing physics (his PC0010_10_BNM is v2: its "Wing"
solver) as Bonamik 3.x data, the format of his PC0010_00_BNM and of PC0010_13_BNM:
  * 11 feathers (R_FeatherA..K): each feather's a_Phy kinematic (it follows the wing's animation and its KineDriver),
    b..e swinging; masses, damping, wind and local-force values, radii (x SCALE) from the v2 bodies;
  * one cone per parent-child link (limits 10 / 25 degrees, inner strength 0.25-0.3, outer and parent 0.8, the link's
    strengths), the cone following the animation as in v2;
  * the 33 lateral links between neighbouring feathers (weak, 0.05) as simple links.
The values 3.x has and v2 does not (velocity and constraint damping, gravity scale, the actor and chain-root forces, the
solver's settings) are PC0010_13_BNM's (his coat's) - except gravity, turned down so the feathers keep their shape.
    make_wing_bnm.py <PC0010_10_BNM legacy package (bnm/Content path)> <pc0010_13_bnm_spec.json> <out spec.json> [SCALE]"""
import json, sys, collections
sys.path[:0] = ['/work/cs', '/work/bnm/tools']
from load import load

GRAVITY_SCALE = 0.3
VERSION_NO = 30713


def body_name(joint):
    return 'Bdy_' + joint


def main(v2_rel, template_path, out, scale=1.0):
    L, objs = load(v2_rel)
    v2 = objs[1]
    B, S, K = v2['m_Bodies'], v2['m_Solvers'], v2['m_Links']
    gname = {s['m_GroupId']: s['m_GroupName'] for s in S}
    wing = [b for b in B if gname[b['m_GroupId']] == 'Wing']
    by_index = {b['m_Index']: b for b in B}
    T = json.load(open(template_path))
    kin_t = [b for b in T['mBodies'] if b['m_IsKinematic']][0]
    swing_t = [b for b in T['mBodies'] if not b['m_IsKinematic'] and b['mGroupName'].startswith('Coat')][0]
    group = dict(T['mGroups'][0], m_GroupName='Wing')
    bodies = []
    for b in wing:
        t = dict(kin_t if b['m_IsKinematic'] else swing_t)
        t.update(mName=body_name(b['m_JointName']), mParentName=b['m_JointName'], mGroupName='Wing',
                 m_LocalTransform=[x * scale for x in json.loads(b['m_LocalTransform'])] if isinstance(b['m_LocalTransform'], str) else [x * scale for x in b['m_LocalTransform']],
                 m_LocalRotation=json.loads(b['m_LocalRotation']) if isinstance(b['m_LocalRotation'], str) else b['m_LocalRotation'],
                 mBodyConstraints=[], m_IsKinematic=bool(b['m_IsKinematic']), m_IsCollision=False,
                 m_Damping=b['m_Damping'], m_Bounciness=b['m_Bounciness'], m_Friction=b['m_Friction'], m_Mass=b['m_Mass'],
                 m_Radius=round(b['m_Radius'] * scale, 4), m_WindDrag=b['m_WindDrag'], m_WindLift=b['m_WindLift'],
                 m_ParkRate=b['m_ParkRate'], m_MaxLF=b['m_MaxLF'], m_LFdrag=b['m_LFdrag'], m_LFlift=b['m_LFlift'])
        if not b['m_IsKinematic']:
            t['mGravityScale'] = GRAVITY_SCALE
        bodies.append(t)
    names = {b['m_Index']: body_name(b['m_JointName']) for b in wing}
    cone_t = T['mCones'][0]
    link_t = T['mLinks'][0]
    cones, links = [], []
    for k in K:
        if k['m_ParentId'] not in names or k['m_ChildId'] not in names:
            continue
        a, b = names[k['m_ParentId']], names[k['m_ChildId']]
        if k['m_LinkType'].endswith('ParentChild'):
            assert k['m_EnableCone']
            cones.append(dict(cone_t, bEnableConeAnimation=bool(k['m_EnableConeAnimation']), mLimitY=k['m_LimitY'], mLimitZ=k['m_LimitZ'],
                              mInnerConeStr=k['m_ConeInnerStr'], mOuterConeStr=k['m_ConeOuterStr'], mConeParentStr=k['m_ConeParentStr'],
                              mStretchedStrength=k['m_LinkStr'], mCompressedStrength=k['m_LinkStr'], mLinkParentStrength=k['m_LinkParentStr'],
                              bIsBending=False, bEnableJointTwist=bool(k['m_EnableJointTwist']), bEnableLengthAnimation=True, mA=a, mB=b,
                              mOuterOffset=[0.0, 0.0, 0.0], mInnerOffset=[0.0, 0.0, 0.0]))
        else:
            links.append(dict(link_t, mStretchedStrength=k['m_LinkStr'], mCompressedStrength=k['m_LinkStr'], mLinkParentStrength=k['m_LinkParentStr'],
                              bIsBending=False, bEnableJointTwist=bool(k['m_EnableJointTwist']), bEnableLengthAnimation=True, mA=a, mB=b))
    swinging = sorted(b['mName'] for b in bodies if not b['m_IsKinematic'])
    assert sorted(c['mB'] for c in cones) == swinging, 'every swinging body needs exactly one cone to its parent'
    spec = dict(m_VersionNo=VERSION_NO, mSceneManager=T['mSceneManager'], mGroups=[dict(T['mGroups'][0]), group], mBodies=bodies,
                mLinks=links, mCones=cones, mShapes=[], mCollisionCliques=[])
    json.dump(spec, open(out, 'w'), indent=1)
    print('%s: %d bodies (%d kinematic, %d swinging), %d cones, %d lateral links, scale %.2f; bones %s' % (
        out.rsplit('/', 1)[-1], len(bodies), sum(b['m_IsKinematic'] for b in bodies), len(swinging), len(cones), len(links), scale,
        sorted({b['mParentName'] for b in bodies})[:6]))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], *(float(x) for x in sys.argv[4:5]))
