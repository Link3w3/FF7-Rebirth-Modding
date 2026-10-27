"""Chaos Vincent wing Bonamik (PC0011_10_BNM).

Wing physics for Chaos Vincent (mesh PC0011_10) built from Sephiroth's transformed form (PC0010_10_BNM, group
"Wing"). Only the numbered wing bones 2F..58 get physics: no hair, cape or collar.

Run it in the End editor: File > Execute Python Script... > pick this file.
(With the editor closed: make_chaos_vincent_wing_bonamik.cmd next to this file does the same.)

It creates /Game/Character/Player/PC011_10_Chaos/Model/PC0011_10_BNM (or rebuilds it when it exists), puts it in
the PC0011_10 mesh's Asset User Data (SQEX_KBD_AssetUserData > Bonamik Data List), checks everything it wrote,
saves both assets and writes Saved/ChaosVincentBonamik/report.json. Running it again rebuilds the same asset.

The asset uses Bonamik 2.x data like Sephiroth's (SQEX_BonamikAsset with a SQEX_BonamikAsset_v2 inside). The
editor's Bonamik preview only shows 3.x data, so test the wings in game.
"""
import json
import os
import traceback

try:
    import unreal
except ImportError:  # imported outside the editor for the offline checks
    unreal = None

ASSET_DIR = '/Game/Character/Player/PC011_10_Chaos/Model'
ASSET_NAME = 'PC0011_10_BNM'
ASSET_PATH = ASSET_DIR + '/' + ASSET_NAME
MESH_PATH = ASSET_DIR + '/PC0011_10'
V2_NAME = 'SQEX_BonamikAsset_v2_0'
VERSION_NO = 2401  # Bonamik 2.4.01, as in PC0010_10_BNM

# ---------------------------------------------------------------------------------------------------------------
# The wing chains. The first bone of a chain is its animated root (kinematic body); the bones after it swing
# (dynamic bodies) and turn the bone above them toward where they swing. A root only has one child, so turning
# it moves nothing but its own chain. Bones without a body (2F 30 31 34 35 39 3A 3D and 44 45 46 49 4A 4E 4F 52)
# follow the animation as before.
LEFT_WING = [['32', '33'], ['36', '37', '38'], ['3B', '3C'], ['3E', '3F', '40'], ['41', '42', '43']]
RIGHT_WING = [['%X' % (int(bone, 16) + 0x15) for bone in chain] for chain in LEFT_WING]  # 47..58, mirror of 32..43
CHAINS = LEFT_WING + RIGHT_WING
WING_BONES = ['%X' % number for number in range(0x2F, 0x59)]  # every numbered bone: 2F..58

GROUPS = ['default', 'Wing']
WING_GROUP = 1

# Cone limits (degrees). Chaos's wing lies in its bones' X/Y plane (bone Z is the wing's normal); Sephiroth's
# feathers lie in their X/Z plane (bone Y is the normal). Sephiroth uses LimitY 10 / LimitZ 25, so here the two
# trade places to give the wings the same freedom relative to the wing surface.
LIMIT_Y = 25.0
LIMIT_Z = 10.0
# Inner cone strength along a chain, as in Sephiroth's feathers (0.3 0.3 0.25 / 0.3 0.3 0.275 0.25).
CONE_INNER_FIRST = 0.3
CONE_INNER_LAST = 0.25

NO_ID = 0xFFFFFFFF


class Enum(object):
    """An entry of a C++ enum: the enum's name, the entry's value and its full name."""

    def __init__(self, enum, value, entry):
        self.enum, self.value, self.entry = enum, value, entry

    def __eq__(self, other):
        return isinstance(other, Enum) and (self.enum, self.value) == (other.enum, other.value)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return self.entry


class Vec(tuple):
    """FVector"""


class Quat(tuple):
    """FQuat (x, y, z, w)"""


SPHERE = Enum('ESQEX_Bonamik_CollisionShape_v2', 1, 'ESQEX_Bonamik_CollisionShape_v2_Sphere')
CAPSULE = Enum('ESQEX_Bonamik_CollisionShape_v2', 2, 'ESQEX_Bonamik_CollisionShape_v2_Capsule')
NO_CONSTRAINT = Enum('ESQEX_Bonamik_ConstraintType_v2', 0, 'ESQEX_Bonamik_ConstraintType_v2_None')
LATERAL = Enum('ESQEX_Bonamik_LinkType_v2', 0, 'ESQEX_Bonamik_LinkType_v2_Lateral')
PARENT_CHILD = Enum('ESQEX_Bonamik_LinkType_v2', 1, 'ESQEX_Bonamik_LinkType_v2_ParentChild')
BENDING = Enum('ESQEX_Bonamik_LinkType_v2', 2, 'ESQEX_Bonamik_LinkType_v2_Bending')
LOCAL_FORCE = Enum('ESQEX_Bonamik_FastMotionHandling_v2', 1, 'ESQEX_Bonamik_FMH_v2_LOCAL_FORCE')

# ---------------------------------------------------------------------------------------------------------------
# Sephiroth's PC0010_10_BNM, group "Wing": all 11 feather roots share these values, all 36 swinging feather
# bodies share SWING_BODY and all 36 feather links share LINK (apart from names, ids and the cone values above).
BODY_COMMON = dict(
    m_IsCollision=False, m_IsMultipleCollisionObject=False, m_Inertia=0.0, m_Radius=2.8, m_Bounciness=0.0,
    m_Friction=0.2, m_LocalTransCoeff=0.5, m_MaxLocalTrans=1.0, m_AddiConstType=NO_CONSTRAINT, m_AddiConstStr=0.5,
    m_AddiConstRad=0.5, m_LocalTransform=Vec((0.0, -0.0, 0.0)), m_LocalRotation=Quat((0.0, 0.0, 0.0, 1.0)),
    m_LocalScale=Vec((1.0, 1.0, 1.0)), m_ConcaveRatio=0.0, m_ParkRate=0.0, m_MaxLF=14.999999, m_LFlift=0.15)
ROOT_BODY = dict(BODY_COMMON, m_IsKinematic=True, m_ColShape=SPHERE, m_Mass=0.5, m_Damping=0.0, m_WindDrag=1.0,
                 m_WindLift=0.15, m_LFcoeff=1.0, m_LFdrag=1.0)
SWING_BODY = dict(BODY_COMMON, m_IsKinematic=False, m_ColShape=CAPSULE, m_Mass=0.05, m_Damping=1.0, m_WindDrag=0.1,
                  m_WindLift=0.25, m_LFcoeff=0.1, m_LFdrag=0.1)
LINK = dict(
    m_LinkType=PARENT_CHILD, m_IsSelfCollision=False, m_EnableJointTwist=False, m_EnableCone=True,
    m_EnableConeAnimation=True, m_LinkStr=0.8, m_LinkParentStr=0.5, m_ConeOuterStr=0.8, m_ConeParentStr=0.8,
    m_ConeOffsetY=0.0, m_ConeOffsetZ=-0.0, m_LimitOffsetY=0.0, m_LimitOffsetZ=-0.0, m_IsCollisionReceiver=False,
    m_IsCollisionRepulsor=False, m_IsLRA=False, m_LRAstr=1.0, m_LRAdamping=0.0, m_LinkBatchNo=NO_ID,
    m_CollisionBatchNo=0, m_PinRadius=0.0, m_PinStr=0.0, m_KdiTrans=0.0, m_KdiRot=0.0, m_ConcaveRatio=0.0)
SOLVER = dict(
    m_IsEnable=True, m_IsUseConeSEQ=True, m_IsEnableDraw=False, m_ColIter=1, m_ConsIter=0, m_ConeIter=2,
    m_LinkIter=2, m_SolverIter=2, m_TagId=0, m_CollisionTagId=0, m_EnableGround=False, m_LODdistance=150.0,
    m_RefUpVec=0)
# Scene settings Sephiroth's asset sets; everything else stays at the game's defaults, as there.
SCENE = dict(
    m_IsEnable=True, m_SubStep=1, m_LSScoeff_tran=1.0, m_LSScoeff_rot=1.0, m_RootName='Trans',
    m_Gravity=Vec((0.0, -9.809999, 0.0)), m_FastMotionHandlingMode=LOCAL_FORCE, m_EnableGroundCollision=True)


def cone_inner(link, links):
    """Inner cone strength of link number `link` (0 = at the root) in a chain of `links` links."""
    if link == 0:
        return CONE_INNER_FIRST
    if links <= 2:
        return CONE_INNER_LAST
    return CONE_INNER_FIRST + (CONE_INNER_LAST - CONE_INNER_FIRST) * (link - 1) / float(links - 2)


def build_bodies_and_links(chains):
    bodies, links = [], []
    per_joint = {}
    body_name = {}
    for chain in chains:
        ids = []
        for joint in chain:
            index = len(bodies)
            body_name[index] = '%s_Body%d' % (joint, per_joint.get(joint, 0))
            per_joint[joint] = per_joint.get(joint, 0) + 1
            ids.append(index)
            bodies.append(None)
        for k, joint in enumerate(chain):
            index = ids[k]
            body = dict(ROOT_BODY if k == 0 else SWING_BODY)
            body.update(
                m_Index=index, m_JointName=joint,
                m_ParentBodyName=body_name[ids[k - 1]] if k > 0 else '',
                m_ChildBodyName=body_name[ids[k + 1]] if k + 1 < len(chain) else '',
                m_ParentId=ids[k - 1] if k > 0 else -1,
                m_ChildId=ids[k + 1] if k + 1 < len(chain) else -1,
                m_GroupId=WING_GROUP, m_ColId=[-1] * 8, m_CollisionBatchNo=0)
            bodies[index] = body
        count = len(chain) - 1
        for k in range(count):
            link = dict(LINK)
            link.update(
                m_ParentBodyName=chain[k], m_ChildBodyName=chain[k + 1], m_ParentId=ids[k], m_ChildId=ids[k + 1],
                m_ConeInnerStr=cone_inner(k, count), m_ConeBatchNo=k % 2, m_LimitY=LIMIT_Y, m_LimitZ=LIMIT_Z)
            links.append(link)
    return bodies, links


def batch_counts(numbers):
    """Per-batch counts (15 slots) and the number of batches, from the batch number of every entry."""
    counts = [0] * 15
    used = [n for n in numbers if n != NO_ID]
    for n in used:
        if n >= 15:
            raise ValueError('batch number %d is beyond the 15 batches Bonamik has' % n)
        counts[n] += 1
    return counts, (max(used) + 1 if used else 0)


def compute_totals(bodies, links):
    """The precomputed counts Bonamik 2.x keeps (formulas checked against every count in PC0010_10_BNM).
    Collisions are not computed: this asset has none, and that is checked."""
    by_index = dict((b['m_Index'], b) for b in bodies)
    self_links = [l for l in links if l['m_IsSelfCollision']]
    roots = set()
    for l in links:
        a, c = by_index[l['m_ParentId']], by_index[l['m_ChildId']]
        if a['m_IsKinematic'] and not c['m_IsKinematic']:
            roots.add(a['m_Index'])
        if c['m_IsKinematic'] and not a['m_IsKinematic']:
            roots.add(c['m_Index'])
    lateral = sum(1 for l in links if l['m_LinkType'] in (LATERAL, BENDING))
    totals = dict(
        m_TotalKinematics=sum(1 for b in bodies if b['m_IsKinematic']),
        m_TotalConstraints=sum(1 for b in bodies if b['m_AddiConstType'] != NO_CONSTRAINT),
        m_TotalCones=sum(1 for l in links if l['m_EnableCone']),
        m_TotalLinks=len(links) - len(self_links),
        m_TotalCollisions=0,
        m_TotalSelfCollisions=len(self_links),
        m_TotalChainRootParticles=len(roots),
        m_TotalPCLinkCones=0,
        m_TotalLateralLinkCones=lateral - len(self_links))
    link_counts, link_batches = batch_counts([l['m_LinkBatchNo'] for l in links if not l['m_IsSelfCollision']])
    cone_counts, cone_batches = batch_counts([l['m_ConeBatchNo'] for l in links if l['m_EnableCone']])
    scene = dict(
        m_TotalLinkBatches=link_batches, m_TotalLinksInBatch=link_counts,
        m_TotalConeBatches=cone_batches, m_TotalConesInBatch=cone_counts,
        m_TotalCollisionBatches=0, m_TotalCollisionsInBatch=[0] * 15,
        m_TotalSelfCollisionBatches=0, m_TotalSelfCollisionsInBatch=[0] * 15)
    return totals, scene


def build_spec():
    """Everything the asset gets, as plain data."""
    bodies, links = build_bodies_and_links(CHAINS)
    solvers = [dict(SOLVER, m_GroupId=i, m_GroupName=name) for i, name in enumerate(GROUPS)]
    totals, batches = compute_totals(bodies, links)
    scene = dict(SCENE, m_TotalGroup=len(solvers))
    scene.update(batches)
    v2 = dict(m_VersionNo=VERSION_NO, m_SceneManager=scene, m_Solvers=solvers, m_Bodies=bodies, m_Links=links,
              m_Planes=[], m_ShapeMatchings=[])
    v2.update(totals)
    check_spec(v2)
    return v2


def check_spec(v2):
    bodies, links = v2['m_Bodies'], v2['m_Links']
    problems = []
    for b in bodies:
        if b['m_JointName'] not in WING_BONES:
            problems.append('body %d is on %s, which is not a numbered wing bone' % (b['m_Index'], b['m_JointName']))
        if any(c != -1 for c in b['m_ColId']):
            problems.append('body %d has collisions' % b['m_Index'])
    if [b['m_Index'] for b in bodies] != list(range(len(bodies))):
        problems.append('body indices are not 0..%d in order' % (len(bodies) - 1))
    joints = [b['m_JointName'] for b in bodies]
    if len(set(joints)) != len(joints):
        problems.append('a bone has two bodies')
    for l in links:
        parent, child = bodies[l['m_ParentId']], bodies[l['m_ChildId']]
        if (parent['m_JointName'], child['m_JointName']) != (l['m_ParentBodyName'], l['m_ChildBodyName']):
            problems.append('link %s-%s ids do not match its names' % (l['m_ParentBodyName'], l['m_ChildBodyName']))
        if child['m_ParentId'] != parent['m_Index'] or parent['m_ChildId'] != child['m_Index']:
            problems.append('link %s-%s is not the bodies\' parent/child' % (l['m_ParentBodyName'], l['m_ChildBodyName']))
    for b in bodies:
        if b['m_IsKinematic'] and b['m_ParentId'] != -1:
            problems.append('root %s has a parent body' % b['m_JointName'])
        if not b['m_IsKinematic'] and b['m_ParentId'] == -1:
            problems.append('swinging body %s has no parent body' % b['m_JointName'])
    scene = v2['m_SceneManager']
    if sum(scene['m_TotalConesInBatch']) != v2['m_TotalCones']:
        problems.append('cone batch counts do not add up')
    if sum(scene['m_TotalLinksInBatch']) + sum(1 for l in links if l['m_LinkBatchNo'] == NO_ID) != v2['m_TotalLinks']:
        problems.append('link batch counts do not add up')
    if problems:
        raise ValueError('wing Bonamik spec: ' + '; '.join(problems))


# ---------------------------------------------------------------------------------------------------------------
# Editor part

def say(text):
    unreal.log('ChaosWingBonamik: ' + text)


def ue_enum(value):
    cls = getattr(unreal, value.enum[1:], None) or getattr(unreal, value.enum, None)
    if cls is None:
        raise RuntimeError('enum %s is not available in Python (is the BonamikPlugin loaded?)' % value.enum)
    entry = cls.cast(value.value)
    want = value.entry.split('_')[-1].replace('_', '').upper()
    got = str(entry.name).replace('_', '').upper()
    if not got.endswith(want):
        raise RuntimeError('%s value %d is %s here, expected %s' % (value.enum, value.value, entry.name, value.entry))
    return entry


def to_ue(value):
    if isinstance(value, Enum):
        return ue_enum(value)
    if isinstance(value, Quat):
        return unreal.Quat(*value)
    if isinstance(value, Vec):
        return unreal.Vector(*value)
    if isinstance(value, list):
        return [to_ue(v) for v in value]
    return value


def make_struct(name, fields):
    struct = getattr(unreal, name)()
    for key, value in fields.items():
        struct.set_editor_property(key, to_ue(value))
    return struct


def same(expected, actual):
    if isinstance(expected, Enum):
        return actual is not None and int(actual.value) == expected.value
    if isinstance(expected, Quat):
        return all(same(e, a) for e, a in zip(expected, (actual.x, actual.y, actual.z, actual.w)))
    if isinstance(expected, Vec):
        return all(same(e, a) for e, a in zip(expected, (actual.x, actual.y, actual.z)))
    if isinstance(expected, list):
        actual = list(actual)
        return len(actual) == len(expected) and all(same(e, a) for e, a in zip(expected, actual))
    if isinstance(expected, bool):
        return bool(actual) == expected
    if isinstance(expected, float):
        return abs(float(actual) - expected) <= 1e-5 * max(1.0, abs(expected))
    if isinstance(expected, int):
        return int(actual) == expected
    return str(actual) == str(expected)


def check_struct(where, struct, fields, problems):
    for key, value in fields.items():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            continue
        actual = struct.get_editor_property(key)
        if not same(value, actual):
            problems.append('%s.%s is %r, expected %r' % (where, key, actual, value))


def mesh_bones(mesh):
    """Bone names and parents of the mesh, read through a temporary component."""
    component = unreal.new_object(unreal.SkeletalMeshComponent)
    component.set_skeletal_mesh(mesh)
    names = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
    parents = dict((name, str(component.get_parent_bone(name))) for name in names)
    return names, parents


def check_mesh(mesh, report):
    try:
        names, parents = mesh_bones(mesh)
    except Exception as error:  # the asset does not depend on this check: the bones were checked offline too
        report['warnings'].append('could not read the mesh bones in Python: %s' % error)
        return
    report['mesh_bones'] = len(names)
    if not names:
        report['warnings'].append('the mesh bone list came back empty; bone check skipped')
        return
    missing = [b for b in WING_BONES if b not in parents]
    if missing:
        raise RuntimeError('PC0011_10 has no bones named %s' % ', '.join(missing))
    for chain in CHAINS:
        for parent, child in zip(chain, chain[1:]):
            if parents[child] != parent:
                raise RuntimeError('bone %s hangs under %s in PC0011_10, not under %s' % (child, parents[child], parent))
    for chain in CHAINS:
        children = [n for n in names if parents[n] == chain[0]]
        if children != [chain[1]]:
            raise RuntimeError('chain root %s has children %s; it must have only %s' % (chain[0], children, chain[1]))


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
    asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(ASSET_NAME, ASSET_DIR, unreal.SQEX_BonamikAsset, factory)
    if asset is None:
        raise RuntimeError('could not create ' + ASSET_PATH)
    report['asset_action'] = 'created'
    return asset


def fill_asset(asset, spec):
    v2 = asset.get_editor_property('v2')
    if v2 is None:
        existing = unreal.find_object(asset, V2_NAME)
        if isinstance(existing, unreal.SQEX_BonamikAsset_v2):
            v2 = existing
        elif existing is None:
            v2 = unreal.new_object(unreal.SQEX_BonamikAsset_v2, asset, V2_NAME)
        else:  # the name is taken by something else: let the editor pick one
            v2 = unreal.new_object(unreal.SQEX_BonamikAsset_v2, asset)
    v2.set_editor_property('m_VersionNo', spec['m_VersionNo'])
    v2.set_editor_property('m_SceneManager', make_struct('SQEX_BonamikSceneManagerDesc_v2', spec['m_SceneManager']))
    v2.set_editor_property('m_Solvers', [make_struct('SQEX_BonamikSolverDesc_v2', s) for s in spec['m_Solvers']])
    v2.set_editor_property('m_Bodies', [make_struct('SQEX_BonamikBodyDesc_v2', b) for b in spec['m_Bodies']])
    v2.set_editor_property('m_Links', [make_struct('SQEX_BonamikLinkDesc_v2', l) for l in spec['m_Links']])
    v2.set_editor_property('m_Planes', [])
    v2.set_editor_property('m_ShapeMatchings', [])
    for key, value in spec.items():
        if key.startswith('m_Total'):
            v2.set_editor_property(key, value)
    asset.set_editor_property('m_VersionNo', VERSION_NO)
    asset.set_editor_property('v2', v2)
    return v2


def verify_asset(asset, spec):
    problems = []
    v2 = asset.get_editor_property('v2')
    if v2 is None:
        return ['the asset has no v2 data']
    if v2.get_outer() != asset:
        problems.append('the v2 data does not live inside the asset')
    if int(asset.get_editor_property('m_VersionNo')) != VERSION_NO:
        problems.append('asset m_VersionNo is wrong')
    check_struct('v2', v2, dict((k, v) for k, v in spec.items() if not isinstance(v, (dict, list))), problems)
    check_struct('m_SceneManager', v2.get_editor_property('m_SceneManager'), spec['m_SceneManager'], problems)
    for key, struct_fields in (('m_Solvers', spec['m_Solvers']), ('m_Bodies', spec['m_Bodies']), ('m_Links', spec['m_Links'])):
        items = list(v2.get_editor_property(key))
        if len(items) != len(struct_fields):
            problems.append('%s has %d entries, expected %d' % (key, len(items), len(struct_fields)))
            continue
        for i, (item, fields) in enumerate(zip(items, struct_fields)):
            check_struct('%s[%d]' % (key, i), item, fields, problems)
    for key in ('m_Planes', 'm_ShapeMatchings'):
        if len(v2.get_editor_property(key)):
            problems.append(key + ' is not empty')
    return problems


def attach_to_mesh(mesh, asset):
    """Adds the asset to the mesh's SQEX_KBD_AssetUserData (made when the mesh has none)."""
    user_data = [d for d in (mesh.get_editor_property('asset_user_data') or [])]
    kbd = None
    for data in user_data:
        if data is not None and isinstance(data, unreal.SQEX_KBD_AssetUserData):
            kbd = data
            break
    if kbd is None:
        kbd = unreal.new_object(unreal.SQEX_KBD_AssetUserData, mesh)
        kbd.set_editor_property('BonamikDataList', [asset])
        mesh.set_editor_property('asset_user_data', user_data + [kbd])
        return 'added a SQEX_KBD_AssetUserData with it'
    current = [d for d in (kbd.get_editor_property('BonamikDataList') or [])]
    if any(d is not None and d.get_path_name() == asset.get_path_name() for d in current):
        return 'already in its SQEX_KBD_AssetUserData'
    kbd.set_editor_property('BonamikDataList', current + [asset])
    return 'added to its existing SQEX_KBD_AssetUserData (now %d Bonamik assets)' % (len(current) + 1)


def verify_mesh(mesh, asset):
    for data in mesh.get_editor_property('asset_user_data') or []:
        if data is not None and isinstance(data, unreal.SQEX_KBD_AssetUserData):
            for d in data.get_editor_property('BonamikDataList') or []:
                if d is not None and d.get_path_name() == asset.get_path_name():
                    return []
    return ['the mesh does not list the asset in its SQEX_KBD_AssetUserData']


def in_commandlet():
    try:
        return '-run=' in unreal.SystemLibrary.get_command_line().lower()
    except Exception:
        return False


def main():
    saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
    out = os.path.join(saved, 'ChaosVincentBonamik')
    if not os.path.isdir(out):
        os.makedirs(out)
    report = dict(ok=False, asset=ASSET_PATH, mesh=MESH_PATH, warnings=[], saved=[])
    try:
        spec = build_spec()
        report['bodies'] = len(spec['m_Bodies'])
        report['links'] = len(spec['m_Links'])
        report['totals'] = dict((k, v) for k, v in spec.items() if k.startswith('m_Total'))
        mesh = unreal.EditorAssetLibrary.load_asset(MESH_PATH)
        if not isinstance(mesh, unreal.SkeletalMesh):
            raise RuntimeError('could not load the skeletal mesh ' + MESH_PATH)
        check_mesh(mesh, report)
        asset = load_or_create_asset(report)
        fill_asset(asset, spec)
        problems = verify_asset(asset, spec)
        if problems:
            report['problems'] = problems
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
        if library is not None:  # a cooked copy, to compare with the game's own Bonamik files
            cooked = os.path.join(out, 'cooked', ASSET_NAME + '.uasset')
            message = library.cook_asset_to_file(ASSET_PATH, cooked)
            report['cooked_copy'] = cooked if message is not None else None
            report['cook_message'] = message if message is not None else 'cook failed (see the Output Log)'
        report['ok'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        unreal.log_error('ChaosWingBonamik: ' + report['error'])
    with open(os.path.join(out, 'report.json'), 'w') as f:
        json.dump(report, f, indent=1)
    if report['ok']:
        text = ('%s %s: %d bodies on the numbered wing bones (%d roots, %d swinging), %d links.\n'
                'PC0011_10 mesh: %s.\nSaved: %s.' % (
                    ASSET_NAME, report['asset_action'], report['bodies'], report['totals']['m_TotalKinematics'],
                    report['bodies'] - report['totals']['m_TotalKinematics'], report['links'], report['mesh_action'],
                    ', '.join(p.rsplit('/', 1)[-1] for p in report['saved'])))
        for warning in report['warnings']:
            text += '\nNote: ' + warning
    else:
        text = ('Something failed (%s):\n%s' % (
            'saved before it: ' + ', '.join(report['saved']) if report['saved'] else 'nothing was saved',
            report['error'].strip().splitlines()[-1]))
    say(text.replace('\n', ' | '))
    if not in_commandlet():
        unreal.EditorDialog.show_message('Chaos Vincent wing Bonamik', text, unreal.AppMsgType.OK)


if unreal is not None and __name__ == '__main__':
    main()
