"""ch049_001's Bonamik (3.x, version 30713: a regular Bonamik like the game's own characters'), as plain data for the
editor step (apply_ch049_bnm.py). Every physics value is Sephiroth's (PC0010_00_BNM), whose outfit this one copies:
  * coat: the 11 coat tails (back, left 01-05, right 01-05: base + 4 bones each) are Sephiroth's 11 coat tails, each
    taking the values of his tail at the nearest angle around the hips, his 6 swinging bodies spread over its 4;
    his bending links along a tail, his links between neighbouring tails and his weak tie across the front opening;
    capsules along each tail that his legs push away (thigh, shin and foot capsules fitted to this mesh).
  * hair: the front, side and back locks: Sephiroth's front locks (C_HairFRA) and side lock (L_HairSideA), the first
    bone following the head; spheres on the swinging bodies that the skull, neck and upper back push away.
  * collar: the four collar pieces swing like his collar (L_CollarA).
The cones are his limits and strengths without his per-axis offsets (his bones' axes are not this skeleton's), so each
piece rests where the animation puts it.

Bone frames are Unreal's after the import (centimetres, facing +X, the root at rest): the Blender rest matrices turned
90 degrees about Z below the root, Y mirrored, x100 (checked against the editor's reference pose).

    make_ch049_bnm_spec.py <model dir> <PC0010_00_BNM.json> <seph_bones.json> <out spec.json>
"""
import json, math, sys
import numpy as np

VERSION_NO = 30713
M = np.diag([1.0, -1.0, 1.0])
T = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])     # 90 degrees about Z (Blender)

BODY_KEYS = ['m_IsKinematic', 'm_IsCollision', 'm_Damping', 'mVelocityDamping', 'mConstraintDamping', 'm_Bounciness',
             'm_Friction', 'mGroundAttach', 'm_Mass', 'mGravityScale', 'm_Radius', 'm_WindDrag', 'm_WindLift',
             'mLFRootRotWeight', 'm_ParkRate', 'm_MaxLF', 'm_LFdrag', 'm_LFlift', 'mActorFictitiousForce',
             'mActorCentrifugal', 'mActorImpulse', 'mActorRotDrag', 'mActorTransDrag', 'mChainRootFictitiousForce',
             'mChainRootCentrifugal', 'mChainRootImpulse', 'mChainRootRotDrag', 'mChainRootTransDrag', 'mBodyDrag',
             'mBodyLift']
CONE_KEYS = ['bEnableConeAnimation', 'mLimitY', 'mLimitZ', 'mInnerConeStr', 'mOuterConeStr', 'mConeParentStr',
             'mStretchedStrength', 'mCompressedStrength', 'mLinkParentStrength', 'bIsBending', 'bEnableJointTwist',
             'bEnableLengthAnimation']
LINK_KEYS = ['mStretchedStrength', 'mCompressedStrength', 'mLinkParentStrength', 'bIsBending', 'bEnableJointTwist',
             'bEnableLengthAnimation']
GROUP_KEYS = ['m_IsEnable', 'm_EnableGround', 'mReferenceFrameUpdateMode', 'm_RefUpVec', 'mIsCollisionResampleCapsule',
              'mCollisionResampleCapsuleStep', 'mCollisionBalance', 'mWindScale', 'mLocalForceScale', 'mParkRateScale',
              'mActorFictitiousForceScale', 'mActorCentrifugalScale', 'mActorImpulseScale', 'mActorRotDragScale',
              'mActorTransDragScale', 'mChainRootFictitiousForceScale', 'mChainRootCentrifugalScale',
              'mChainRootImpulseScale', 'mChainRootRotDragScale', 'mChainRootTransDragScale', 'mBodyDragScale',
              'mBodyLiftScale', 'mFpsCorrection']
SHAPE = dict(mPlaneThickness=0.0, mPlaneOffset=0.0, mCapsuleConcaveRatio=0.0, bIsInverse=False, bIsInfinity=False,
             bResampleStart=False)

# ch049's physics bones
COAT = [('CoatC', 'phy_back_coat_base', ['phy_back_coat_%02d' % i for i in range(1, 5)])]
for _side, _g in (('left', 'CoatL'), ('right', 'CoatR')):
    for _n in range(1, 6):
        COAT.append((_g, 'phy_%s_coat_%02d_base' % (_side, _n), ['phy_%s_coat_%02d_%02d' % (_side, _n, i) for i in range(1, 5)]))
HAIR = [('HairF', ['phy_front_hair_01_01', 'phy_front_hair_01_02', 'phy_front_hair_01_03']),
        ('HairF', ['phy_front_hair_02_01', 'phy_front_hair_02_02']),
        ('HairF', ['phy_front_hair_03_01', 'phy_front_hair_03_02', 'phy_front_hair_03_03']),
        ('HairF', ['phy_front_hair_04_01', 'phy_front_hair_04_02', 'phy_front_hair_04_03']),
        ('HairF', ['phy_front_hair_05_01', 'phy_front_hair_05_02', 'phy_front_hair_05_03']),
        ('HairL', ['phy_left_side_hair_01_01', 'phy_left_side_hair_01_02', 'phy_left_side_hair_01_03']),
        ('HairL', ['phy_left_side_hair_02_01', 'phy_left_side_hair_02_02']),
        ('HairL', ['phy_left_side_hair_03_01', 'phy_left_side_hair_03_02', 'phy_left_side_hair_03_03']),
        ('HairR', ['phy_right_side_hair_01_01', 'phy_right_side_hair_01_02', 'phy_right_side_hair_01_03']),
        ('HairR', ['phy_right_side_hair_02_01', 'phy_right_side_hair_02_02', 'phy_right_side_hair_02_03']),
        ('HairB', ['phy_back_hair_01_base', 'phy_back_hair_01_01', 'phy_back_hair_01_02']),
        ('HairB', ['phy_back_hair_02_base', 'phy_back_hair_02_01', 'phy_back_hair_02_02']),
        ('HairB', ['phy_back_hair_03_base', 'phy_back_hair_03_01', 'phy_back_hair_03_02'])]
COLLAR = [('Collar', ['phy_%s_collar_%02d_base' % (s, n), 'phy_%s_collar_%02d_01' % (s, n)]) for s in ('left', 'right') for n in (1, 2)]
# which of Sephiroth's chains each kind copies
SEPH_HAIR = {'HairF': ('HairFA', 'C_HairFRA'), 'HairL': ('HairLD', 'L_HairSideA'), 'HairR': ('HairRD', 'R_HairSideA'),
             'HairB': ('HairLD', 'L_HairSideA')}
SEPH_COLLAR = ('Eri', 'L_CollarA')
SEPH_COATS = ['L_CoatA', 'L_CoatB', 'L_CoatC', 'L_CoatD', 'L_CoatE', 'R_CoatA', 'R_CoatB', 'R_CoatC', 'R_CoatD', 'R_CoatE', 'C_CoatA']
GROUP_FROM = {'CoatC': 'CortC', 'CoatL': 'CortL', 'CoatR': 'CortR', 'HairF': 'HairFA', 'HairL': 'HairLD', 'HairR': 'HairRD',
              'HairB': 'HairLD', 'Collar': 'Eri', 'Col_leg': 'Col_leg', 'Col_body': 'Col_body', 'Col_head': 'Col_headB'}
GROUPS = ['default', 'Col_leg', 'Col_body', 'Col_head', 'CoatC', 'CoatL', 'CoatR', 'HairF', 'HairL', 'HairR', 'HairB', 'Collar']


def along(n_from, k, n_to):
    """index into a chain of n_from swinging bodies for swinging body k of n_to (spread over its length)"""
    if n_to <= 1:
        return 0
    return int(round(k * (n_from - 1) / float(n_to - 1)))


class Skel:
    def __init__(self, model_dir):
        info = json.load(open(model_dir + '/model.json'))
        self.bones = info['bones']
        self.index = {b['name']: i for i, b in enumerate(self.bones)}
        self.R, self.t = {}, {}
        for i, b in enumerate(self.bones):
            W = np.array(b['world'])
            R, t = W[:3, :3], W[:3, 3]
            if i > 0:
                R, t = T @ R, T @ t
            self.R[b['name']] = M @ R @ M
            self.t[b['name']] = M @ t * 100.0
        self.parent = {b['name']: (self.bones[b['parent']]['name'] if b['parent'] >= 0 else None) for b in self.bones}
        A = np.load(model_dir + '/model.npz')
        self.meshes = {}
        for m in info['meshes']:
            k = m['name']
            co = (M @ (T @ (A[k + '/co'].astype(np.float64).T))).T * 100.0
            self.meshes[k] = (co, A[k + '/w_vert'], A[k + '/w_bone'], A[k + '/w_val'])

    def local(self, bone, p):
        """a component-space point in bone's frame"""
        return self.R[bone].T @ (np.asarray(p) - self.t[bone])

    def verts_of(self, bone, min_w=0.6, meshes=None):
        i = self.index[bone]
        pts = []
        for k, (co, v, b, w) in self.meshes.items():
            if meshes and k not in meshes:
                continue
            sel = (b == i) & (w >= min_w)
            pts.append(co[v[sel]])
        return np.concatenate(pts) if pts else np.zeros((0, 3))


def seg_dist(p, a, b):
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-9), 0.0, 1.0)
    return np.linalg.norm(p - (a + t[:, None] * ab[None, :]), axis=1), t


def main(model_dir, seph_path, seph_bones_path, out):
    S = Skel(model_dir)
    seph = json.load(open(seph_path))
    SB = {b['mName']: b for b in seph['mBodies']}
    by_bone = {b['mParentName']: b for b in seph['mBodies'] if not b['mName'].startswith('Bdy_Sta_C_') or True}
    sgroups = {g['m_GroupName']: g for g in seph['mGroups']}

    def seph_body(bone):
        hits = [b for b in seph['mBodies'] if b['mParentName'] == bone and not b['m_IsCollision']]
        assert hits, bone
        return hits[0]

    def seph_cone(a_bone, b_bone):
        a, b = seph_body(a_bone)['mName'], seph_body(b_bone)['mName']
        hits = [c for c in seph['mCones'] if c['mA'] == a and c['mB'] == b]
        assert len(hits) == 1, (a_bone, b_bone)
        return hits[0]

    def seph_link(a_bone, b_bone):
        a, b = seph_body(a_bone)['mName'], seph_body(b_bone)['mName']
        hits = [l for l in seph['mLinks'] if {l['mA'], l['mB']} == {a, b}]
        return hits[0] if hits else None

    # Sephiroth's coat tails: angle around his hips (front +X, left -Y)
    sb = json.load(open(seph_bones_path))
    snames = [b[0] for b in sb['bones']]
    spos = lambda n: np.array(sb['cs'][snames.index(n)][1])
    shp = spos('C_Hip_a')

    def ang(p, hip):
        d = p - hip
        return math.degrees(math.atan2(-d[1], d[0]))
    seph_ang = {c: ang(spos(c + '_a_Phy'), shp) for c in SEPH_COATS}
    hip = S.t['hip']

    bodies, cones, links, shapes, report = [], [], [], [], {'coat_map': {}, 'radii': {}}

    def add_body(name, bone, group, values, **extra):
        b = {'mName': name, 'mParentName': bone, 'mGroupName': group, 'm_LocalTransform': [0.0, 0.0, 0.0],
             'm_LocalRotation': [0.0, 0.0, 0.0, 1.0], 'mBodyConstraints': []}
        b.update({k: values[k] for k in BODY_KEYS})
        b.update(extra)
        bodies.append(b)
        return name

    def add_shape(kind, members, receivers=(), repulsors=()):
        s = dict(SHAPE, mShapeId=len(shapes), mType=kind, mBodies=list(members), mReceiverGroups=list(receivers),
                 mRepulsorGroups=list(repulsors))
        shapes.append(s)

    def cone(src, a, b, **extra):
        c = {k: src[k] for k in CONE_KEYS}
        c.update(mA=a, mB=b, mOuterOffset=[0.0, 0.0, 0.0], mInnerOffset=[0.0, 0.0, 0.0])
        c.update(extra)
        cones.append(c)

    def link(src, a, b):
        l = {k: src[k] for k in LINK_KEYS}
        l.update(mA=a, mB=b)
        links.append(l)

    def check_chain(root, chain):
        for p, c in zip([root] + chain, chain):
            assert S.parent[c] == p, ('%s hangs under %s, not %s' % (c, S.parent[c], p))

    # ---- colliders: legs (thigh, shin, foot), pelvis; upper back, neck, skull
    def fit_segment(bone, child, meshes=('body_geo',), pct=80):
        pts = S.verts_of(bone, meshes=meshes)
        d, t = seg_dist(pts, S.t[bone], S.t[child])
        d = d[(t > 0.15) & (t < 0.85)]
        return float(np.percentile(d, pct)) if len(d) else None
    col = {}
    for side in ('left', 'right'):
        thigh = fit_segment(side + '_upleg', side + '_leg')
        shin = fit_segment(side + '_leg', side + '_foot')
        foot = fit_segment(side + '_foot', side + '_toe', pct=70)
        report['radii'][side] = dict(thigh=round(thigh, 2), shin=round(shin, 2), foot=round(foot, 2))
        legv = seph_body('L_UpperLeg_a') if False else None
        base = [b for b in seph['mBodies'] if b['mGroupName'] == 'Col_leg'][0]
        col[side + '_upleg'] = add_body('Bdy_Sta_%s_upleg_0_1' % side, side + '_upleg', 'Col_leg', base, m_Radius=round(thigh, 2))
        col[side + '_leg'] = add_body('Bdy_Sta_%s_leg_0_1' % side, side + '_leg', 'Col_leg', base, m_Radius=round(min(thigh, shin * 1.1), 2))
        col[side + '_foot'] = add_body('Bdy_Sta_%s_foot_0_1' % side, side + '_foot', 'Col_leg', base, m_Radius=round(shin, 2))
        col[side + '_toe'] = add_body('Bdy_Sta_%s_toe_0_1' % side, side + '_toe', 'Col_leg', base, m_Radius=round(foot, 2))
        add_shape('capsule', [col[side + '_upleg'], col[side + '_leg']], repulsors=['Col_leg'])
        add_shape('capsule', [col[side + '_leg'], col[side + '_foot']], repulsors=['Col_leg'])
        add_shape('capsule', [col[side + '_foot'], col[side + '_toe']], repulsors=['Col_leg'])
    # pelvis: one sphere between the hip joints
    pel = S.verts_of('hip', meshes=('body_geo',), min_w=0.5)
    mid = (S.t['left_upleg'] + S.t['right_upleg']) / 2.0
    pr = float(np.percentile(np.linalg.norm(pel - mid, axis=1), 60)) if len(pel) else 12.0
    report['radii']['pelvis'] = round(pr, 2)
    base_leg = [b for b in seph['mBodies'] if b['mGroupName'] == 'Col_leg'][0]
    pelvis = add_body('Bdy_Sta_hip_0_1', 'hip', 'Col_leg', base_leg, m_Radius=round(pr, 2),
                      m_LocalTransform=[round(float(x), 3) for x in S.local('hip', mid)])
    add_shape('sphere', [pelvis], repulsors=['Col_leg'])
    # upper back and neck capsules, skull sphere
    base_body = [b for b in seph['mBodies'] if b['mGroupName'] == 'Col_body'][0]
    def fit_bone(bone, child, meshes, pct=60):
        pts = S.verts_of(bone, meshes=meshes, min_w=0.5)
        d, t = seg_dist(pts, S.t[bone], S.t[child])
        return float(np.percentile(d, pct)) if len(pts) else None
    r_sp3 = fit_bone('spine3', 'spine4', ('body_geo',))
    r_sp4 = fit_bone('spine4', 'neck', ('body_geo',))
    r_neck = fit_bone('neck', 'head', ('body_geo', 'head_geo'))
    report['radii'].update(spine3=round(r_sp3, 2), spine4=round(r_sp4, 2), neck=round(r_neck, 2))
    b_sp3 = add_body('Bdy_Sta_spine3_0_1', 'spine3', 'Col_body', base_body, m_Radius=round(r_sp3, 2))
    b_sp4 = add_body('Bdy_Sta_spine4_0_1', 'spine4', 'Col_body', base_body, m_Radius=round(r_sp4, 2))
    b_neck = add_body('Bdy_Sta_neck_0_1', 'neck', 'Col_body', base_body, m_Radius=round(r_neck, 2))
    b_head = add_body('Bdy_Sta_head_0_1', 'head', 'Col_body', base_body, m_Radius=round(r_neck, 2))
    add_shape('capsule', [b_sp3, b_sp4], repulsors=['Col_body'])
    add_shape('capsule', [b_sp4, b_neck], repulsors=['Col_body'])
    add_shape('capsule', [b_neck, b_head], repulsors=['Col_body'])
    # skull: the head mesh's vertices on the head bone, centre of their bounds; radius kept clear of every hair body
    hv = S.verts_of('head', meshes=('head_geo',), min_w=0.9)
    lo, hi = hv.min(0), hv.max(0)
    centre = (lo + hi) / 2.0
    r_fit = float(np.percentile(np.linalg.norm(hv - centre, axis=1), 50))
    hair_pts = [S.t[c] for _g, ch in HAIR for c in ch[1:]]
    clear = min(float(np.linalg.norm(p - centre)) for p in hair_pts) - 1.0
    r_skull = max(4.0, min(r_fit, clear))
    report['radii'].update(skull_fit=round(r_fit, 2), skull_clear=round(clear, 2), skull=round(r_skull, 2))
    base_head = [b for b in seph['mBodies'] if b['mGroupName'] == 'Col_headB'][0]
    skull = add_body('Bdy_Sta_head_0_2', 'head', 'Col_head', base_head, m_Radius=round(r_skull, 2),
                     m_LocalTransform=[round(float(x), 3) for x in S.local('head', centre)])
    add_shape('sphere', [skull], repulsors=['Col_head'])

    # ---- coat
    bend0, bend1 = seph_link('L_CoatA_a_Phy', 'L_CoatA_c_Phy'), seph_link('L_CoatA_b_Phy', 'L_CoatA_d_Phy')
    assert bend0 and bend1
    names_by_chain = {}
    for group, root, chain in COAT:
        check_chain(root, chain)
        a = ang(S.t[root], hip)
        src = min(SEPH_COATS, key=lambda c: abs((seph_ang[c] - a + 180) % 360 - 180))
        report['coat_map'][root] = '%s (%.0f deg; his %.0f)' % (src, a, seph_ang[src])
        sbones = [src + '_%s_Phy' % c for c in 'abcdefg']
        names = [add_body('Bdy_%s_0_1' % root, root, group, seph_body(sbones[0]))]
        for k, bone in enumerate(chain):
            names.append(add_body('Bdy_%s_0_1' % bone, bone, group, seph_body(sbones[1 + along(6, k, len(chain))])))
        for k in range(len(chain)):
            j = along(6, k, len(chain))
            cone(seph_cone(sbones[j], sbones[j + 1]), names[k], names[k + 1])
        # bending along the tail: his L_CoatA a-c and b-d values
        for k in range(len(names) - 2):
            link(bend0 if k == 0 else bend1, names[k], names[k + 2])
        for k in range(1, len(names)):
            add_shape('capsule', [names[k - 1], names[k]], receivers=['Col_leg'])
        names_by_chain[root] = (a, names, src)
    # neighbouring tails, by angle around the hips (not across the front opening)
    order = sorted(names_by_chain, key=lambda r: names_by_chain[r][0])
    lateral = seph_link('L_CoatA_b_Phy', 'L_CoatB_b_Phy')
    tie = seph_link('R_CoatA_b_Phy', 'L_CoatA_b_Phy')
    pairs = []
    for i in range(len(order)):
        a, b = order[i], order[(i + 1) % len(order)]
        aa, ab = names_by_chain[a][0], names_by_chain[b][0]
        gap = (ab - aa) % 360
        front = (aa < 0 <= ab) or (ab - aa) < 0 and False
        pairs.append((a, b, gap))
    for a, b, gap in pairs:
        na, nb = names_by_chain[a][1], names_by_chain[b][1]
        across_front = names_by_chain[a][0] < 0 < names_by_chain[b][0]
        if across_front:
            link(tie, na[1], nb[1])
            report['front_tie'] = [na[1], nb[1]]
            continue
        for k in range(1, len(na)):
            link(lateral, na[k], nb[k])
    report['coat_neighbours'] = [(a, b) for a, b, _ in pairs]

    # ---- hair
    for group, chain in HAIR:
        check_chain(S.parent[chain[0]], chain)
        sgroup, sprefix = SEPH_HAIR[group]
        sbones = [sprefix + '_%s_Phy' % c for c in 'abc']
        names = [add_body('Bdy_%s_0_1' % chain[0], chain[0], group, seph_body(sbones[0]))]
        for k, bone in enumerate(chain[1:]):
            names.append(add_body('Bdy_%s_0_1' % bone, bone, group, seph_body(sbones[1 + along(2, k, len(chain) - 1)])))
        for k in range(len(chain) - 1):
            j = along(2, k, len(chain) - 1)
            cone(seph_cone(sbones[j], sbones[j + 1]), names[k], names[k + 1])
        for n in names[1:]:
            add_shape('sphere', [n], receivers=['Col_body', 'Col_head'])

    # ---- collar
    for group, chain in COLLAR:
        check_chain(S.parent[chain[0]], chain)
        sgroup, sprefix = SEPH_COLLAR
        names = [add_body('Bdy_%s_0_1' % chain[0], chain[0], group, seph_body(sprefix + '_a_Phy')),
                 add_body('Bdy_%s_0_1' % chain[1], chain[1], group, seph_body(sprefix + '_b_Phy'))]
        cone(seph_cone(sprefix + '_a_Phy', sprefix + '_b_Phy'), names[0], names[1])

    report['clearance'] = clear_rest(bodies, shapes, S)

    groups = []
    for g in GROUPS:
        if g == 'default':
            src = sgroups['default']
        else:
            src = sgroups[GROUP_FROM[g]]
        d = {k: src[k] for k in GROUP_KEYS}
        d['m_GroupName'] = g
        groups.append(d)
    scene = dict(seph['mSceneManager'])
    scene['mCollisionCachableRange'] = 10.0       # (0 in his; a 0 is not saved by the editor, the game's default is not 0)
    spec = dict(m_VersionNo=VERSION_NO, mSceneManager=scene, mGroups=groups, mBodies=bodies, mLinks=links, mCones=cones,
                mShapes=shapes, mCollisionCliques=[])
    check(spec, S)
    json.dump(spec, open(out, 'w'), indent=0)
    report.update(bodies=len(bodies), swinging=sum(1 for b in bodies if not b['m_IsKinematic']), cones=len(cones),
                  links=len(links), shapes=len(shapes), groups=[g['m_GroupName'] for g in groups])
    print(json.dumps(report, indent=1))


def seg_seg(a0, a1, b0, b1, n=24):
    """closest distance between two segments (sampled along the first, exact to the second)"""
    t = np.linspace(0.0, 1.0, n)[:, None]
    pts = a0[None, :] + t * (a1 - a0)[None, :]
    d, _ = seg_dist(pts, b0, b1)
    return float(d.min())


def clear_rest(bodies, shapes, S, margin=0.5, floor=2.0):
    """Shrinks collider radii that the swinging pieces already touch in the rest pose (they would be shoved out the
    moment the physics starts): each repulsor ends clear of every receiver shape that collides with it."""
    by = {b['mName']: b for b in bodies}
    pos = {n: S.t[b['mParentName']] + S.R[b['mParentName']] @ np.array(b['m_LocalTransform']) for n, b in by.items()}
    def ends(sh):
        m = sh['mBodies']
        return (pos[m[0]], pos[m[-1]])
    changes = {}
    for _ in range(3):
        moved = False
        for rep in shapes:
            if not rep['mRepulsorGroups']:
                continue
            for rec in shapes:
                if not rec['mReceiverGroups'] or not set(rec['mReceiverGroups']) & set(rep['mRepulsorGroups']):
                    continue
                a0, a1 = ends(rec)
                b0, b1 = ends(rep)
                d = seg_seg(a0, a1, b0, b1)
                r_rec = max(by[m]['m_Radius'] for m in rec['mBodies'])
                need = d - r_rec - margin
                for m in rep['mBodies']:
                    if by[m]['m_Radius'] > need:
                        new = max(floor, round(need, 2))
                        if new < by[m]['m_Radius']:
                            changes.setdefault(m, [by[m]['m_Radius']])
                            by[m]['m_Radius'] = new
                            moved = True
        if not moved:
            break
    left = []
    for rep in shapes:
        for rec in shapes:
            if rep['mRepulsorGroups'] and rec['mReceiverGroups'] and set(rec['mReceiverGroups']) & set(rep['mRepulsorGroups']):
                a0, a1 = ends(rec); b0, b1 = ends(rep)
                d = seg_seg(a0, a1, b0, b1) - max(by[m]['m_Radius'] for m in rec['mBodies']) - max(by[m]['m_Radius'] for m in rep['mBodies'])
                if d < 0:
                    left.append((rec['mBodies'], rep['mBodies'], round(d, 2)))
    return dict(shrunk={m: [v[0], by[m]['m_Radius']] for m, v in changes.items()}, still_touching=left[:10])


def check(spec, S):
    problems = []
    groups = [g['m_GroupName'] for g in spec['mGroups']]
    if groups[0] != 'default' or len(set(groups)) != len(groups):
        problems.append('groups')
    names = [b['mName'] for b in spec['mBodies']]
    if len(set(names)) != len(names):
        problems.append('duplicate body names')
    dyn = [b['mParentName'] for b in spec['mBodies'] if not b['m_IsKinematic']]
    if len(set(dyn)) != len(dyn):
        problems.append('a bone has two swinging bodies')
    by = {b['mName']: b for b in spec['mBodies']}
    for b in spec['mBodies']:
        if b['mGroupName'] not in groups:
            problems.append('group of ' + b['mName'])
        if b['mParentName'] not in S.index:
            problems.append('no bone ' + b['mParentName'])
        if not b['m_IsKinematic']:
            # a swinging body turns the bone above it: never a bone the rest of the body hangs from
            p = S.parent[b['mParentName']]
            if not p.startswith('phy_'):
                problems.append('%s would turn %s' % (b['mName'], p))
    for c in spec['mCones'] + spec['mLinks']:
        if c['mA'] not in by or c['mB'] not in by:
            problems.append('link %s-%s' % (c['mA'], c['mB']))
    for c in spec['mCones']:
        if by[c['mB']]['m_IsKinematic']:
            problems.append('cone ends on a kinematic body ' + c['mB'])
    for s in spec['mShapes']:
        if any(m not in by for m in s['mBodies']) or any(g not in groups for g in s['mReceiverGroups'] + s['mRepulsorGroups']):
            problems.append('shape %d' % s['mShapeId'])
    if [s['mShapeId'] for s in spec['mShapes']] != list(range(len(spec['mShapes']))):
        problems.append('shape ids')
    if problems:
        raise SystemExit('spec problems: ' + '; '.join(problems[:20]))


if __name__ == '__main__':
    main(*sys.argv[1:])
