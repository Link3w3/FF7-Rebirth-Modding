"""The Nameless's own regular (3.x) Bonamik: its string, phy_string_01 (kinematic, at the guard) -> phy_string_02 ->
phy_string_03 (swinging), hanging with full gravity and loose cones (45 degrees, a weak pull to the animation), the
other values Young Sephiroth's front hair's (PC0010_13_BNM: HairF). Solver settings and the scene as PC0010_13_BNM's.
    make_nameless_bnm.py <pc0010_13_bnm_spec.json> <out spec.json>"""
import json, sys

def main(template, out):
    T = json.load(open(template))
    kin = [b for b in T['mBodies'] if b['mGroupName'] == 'HairF' and b['m_IsKinematic']][0]
    swing = [b for b in T['mBodies'] if b['mGroupName'] == 'HairF' and not b['m_IsKinematic']][0]
    cone = [c for c in T['mCones'] if c['mA'] == kin['mName']][0]
    group = dict([g for g in T['mGroups'] if g['m_GroupName'] == 'HairF'][0], m_GroupName='String')
    bodies = [dict(kin, mName='Bdy_phy_string_01', mParentName='phy_string_01', mGroupName='String', m_Radius=0.6)]
    for n in ('phy_string_02', 'phy_string_03'):
        bodies.append(dict(swing, mName='Bdy_' + n, mParentName=n, mGroupName='String', m_Radius=0.6, mGravityScale=1.0,
                           m_Mass=0.3, m_Damping=1.0, mVelocityDamping=0.5))
    cones = [dict(cone, mA=a, mB=b, mLimitY=45.0, mLimitZ=45.0, mInnerConeStr=0.1, mOuterConeStr=0.8, mConeParentStr=0.5,
                  mLinkParentStrength=1.0, bEnableConeAnimation=True)
             for a, b in (('Bdy_phy_string_01', 'Bdy_phy_string_02'), ('Bdy_phy_string_02', 'Bdy_phy_string_03'))]
    spec = dict(m_VersionNo=T['m_VersionNo'], mSceneManager=T['mSceneManager'], mGroups=[dict(T['mGroups'][0]), group], mBodies=bodies,
                mLinks=[], mCones=cones, mShapes=[], mCollisionCliques=[])
    json.dump(spec, open(out, 'w'), indent=1)
    print('%s: %d bodies, %d cones, version %d' % (out, len(bodies), len(cones), spec['m_VersionNo']))

if __name__ == '__main__':
    main(*sys.argv[1:3])
