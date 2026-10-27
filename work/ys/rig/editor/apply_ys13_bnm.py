# PC0010_13 (Young Sephiroth on Rebirth's bone names): (1) the hair textures the Hair MI still took from the outfit folder
# copied in as PC0010_13_* and the MI repointed; (2) his regular (3.x) Bonamik from pc0010_13_bnm_spec.json
# (make_bnm_spec.py: ch049_001's Bonamik moved onto the renamed bones): creates or rebuilds
# /Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13_BNM, checks every value it wrote and every bone it
# names on the mesh, puts it in the mesh's Asset User Data (SQEX_KBD_AssetUserData > Bonamik Data List) and saves both;
# (3) what Sephiroth's own mesh carries in its Asset User Data (for the helper bones). No dialogs.
import unreal, json, os

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
HERE = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'ModExtract', 'ys13')
BASE = '/Game/Character/Player/PC0010_13_Young_Sephiroth'
OUTFIT = '/Game/Character/Player/PC0010_10_Young_Sephiroth_Outfit_Transformed'
MODEL_DIR = BASE + '/Model'
MESH_PATH = MODEL_DIR + '/PC0010_13'
ASSET_NAME = 'PC0010_13_BNM'
ASSET_PATH = MODEL_DIR + '/' + ASSET_NAME
SPEC = json.load(open(os.path.join(HERE, 'pc0010_13_bnm_spec.json')))
VECTORS = ('m_LocalTransform', 'm_Gravity', 'mOuterOffset', 'mInnerOffset')
QUATS = ('m_LocalRotation',)
STRUCT_OF_LIST = {'mGroups': 'SQEX_BonamikSolverDesc', 'mBodies': 'SQEX_BonamikBodyDesc',
                  'mLinks': 'SQEX_BonamikSimpleLinkDesc', 'mCones': 'SQEX_BonamikConeLinkDesc',
                  'mShapes': 'SQEX_BonamikShapeDesc', 'mCollisionCliques': 'SQEX_BonamikCollisionCliqueDesc',
                  'mFpsCorrection': 'SQEX_BonamikFpsCorrectionDesc', 'mBodyConstraints': 'SQEX_BonamikBodyConstraintDesc'}
LISTS = ['mGroups', 'mBodies', 'mLinks', 'mCones', 'mShapes', 'mCollisionCliques']
EMPTY_REGULAR = ['mLRAs', 'mKDIs', 'mPossessions']
EMPTY_LEGACY = ['m_Solvers', 'm_Bodies', 'm_Links', 'm_Planes', 'm_ShapeMatchings', 'm_Possessions']
out = {'warnings': [], 'saved': [], 'hair': {}}

# (1) the hair MI's remaining outfit textures
mi = unreal.load_asset(BASE + '/Material/PC0010_13_Hair')
for tp in mi.get_editor_property('texture_parameter_values'):
    t = tp.get_editor_property('parameter_value')
    if t is None or not t.get_path_name().startswith(OUTFIT):
        continue
    name = tp.get_editor_property('parameter_info').get_editor_property('name')
    src_pkg = t.get_path_name().split('.')[0]
    new = BASE + '/Texture/' + src_pkg.rsplit('/', 1)[-1].replace('tex_ch049_001_', 'PC0010_13_')
    if not EAL.does_asset_exist(new):
        EAL.duplicate_asset(src_pkg, new)
    EAL.save_asset(new, False)
    MEL.set_material_instance_texture_parameter_value(mi, name, unreal.load_asset(new))
    out['hair'][str(name)] = new.rsplit('/', 1)[-1]
MEL.update_material_instance(mi)
EAL.save_loaded_asset(mi, False)
left = []
for part in ('Body', 'Head', 'Hair', 'Eyelash', 'EyeShadow', 'Eye'):
    m = unreal.load_asset(BASE + '/Material/PC0010_13_' + part)
    for tp in m.get_editor_property('texture_parameter_values'):
        t = tp.get_editor_property('parameter_value')
        if t is not None and not t.get_path_name().startswith(BASE) and not t.get_path_name().startswith('/Game/Maps/') and '/Engine' not in t.get_path_name():
            left.append((part, str(tp.get_editor_property('parameter_info').get_editor_property('name')), t.get_path_name()))
out['textures_outside_his_folder'] = left


def to_ue(key, value):
    if key in QUATS:
        return unreal.Quat(*value)
    if key in VECTORS:
        return unreal.Vector(*value)
    if isinstance(value, list):
        if any(isinstance(v, dict) for v in value):
            return [make_struct(STRUCT_OF_LIST[key], v) for v in value]
        return list(value)
    return value


def make_struct(name, fields):
    s = getattr(unreal, name)()
    for k, v in fields.items():
        s.set_editor_property(k, to_ue(k, v))
    return s


def same(key, expected, actual):
    if key in QUATS:
        return all(abs(e - a) < 1e-5 for e, a in zip(expected, (actual.x, actual.y, actual.z, actual.w)))
    if key in VECTORS:
        return all(abs(e - a) < 1e-4 * max(1.0, abs(e)) for e, a in zip(expected, (actual.x, actual.y, actual.z)))
    if isinstance(expected, list):
        actual = list(actual)
        if len(actual) != len(expected):
            return False
        return all((check_ok(e, a) if isinstance(e, dict) else same(None, e, a)) for e, a in zip(expected, actual))
    if isinstance(expected, bool):
        return bool(actual) == expected
    if isinstance(expected, float):
        return abs(float(actual) - expected) <= 1e-5 * max(1.0, abs(expected))
    if isinstance(expected, int):
        return int(actual) == expected
    return str(actual) == str(expected)


def check_ok(fields, struct):
    return all(same(k, v, struct.get_editor_property(k)) for k, v in fields.items())


def check_struct(where, struct, fields, problems):
    for k, v in fields.items():
        a = struct.get_editor_property(k)
        if not same(k, v, a):
            problems.append('%s.%s is %r, expected %r' % (where, k, a, v))


# (2) the Bonamik
mesh = unreal.load_asset(MESH_PATH)
assert isinstance(mesh, unreal.SkeletalMesh), MESH_PATH
c = unreal.new_object(unreal.SkeletalMeshComponent)
c.set_skeletal_mesh(mesh)
bones = set(str(c.get_bone_name(i)) for i in range(c.get_num_bones()))
missing = sorted(set(b['mParentName'] for b in SPEC['mBodies']) - bones)
assert not missing, 'the mesh has no bones named ' + ', '.join(missing)
if EAL.does_asset_exist(ASSET_PATH):
    asset = EAL.load_asset(ASSET_PATH)
    assert isinstance(asset, unreal.SQEX_BonamikAsset), type(asset).__name__
    out['asset_action'] = 'rebuilt'
else:
    factory = unreal.DataAssetFactory()
    try:
        factory.set_editor_property('data_asset_class', unreal.SQEX_BonamikAsset.static_class())
    except Exception:
        pass
    asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(ASSET_NAME, MODEL_DIR, unreal.SQEX_BonamikAsset, factory)
    assert asset is not None, 'could not create ' + ASSET_PATH
    out['asset_action'] = 'created'
asset.set_editor_property('m_VersionNo', SPEC['m_VersionNo'])
asset.set_editor_property('mSceneManager', make_struct('SQEX_BonamikSceneManagerDesc', SPEC['mSceneManager']))
for key in LISTS:
    asset.set_editor_property(key, [make_struct(STRUCT_OF_LIST[key], v) for v in SPEC[key]])
for key in EMPTY_REGULAR + EMPTY_LEGACY:
    asset.set_editor_property(key, [])
asset.set_editor_property('v2', None)
problems = []
if int(asset.get_editor_property('m_VersionNo')) != SPEC['m_VersionNo']:
    problems.append('m_VersionNo')
if asset.get_editor_property('v2') is not None:
    problems.append('v2 data left')
check_struct('mSceneManager', asset.get_editor_property('mSceneManager'), SPEC['mSceneManager'], problems)
for key in LISTS:
    items = list(asset.get_editor_property(key))
    if len(items) != len(SPEC[key]):
        problems.append('%s has %d entries, expected %d' % (key, len(items), len(SPEC[key])))
        continue
    for i, (item, fields) in enumerate(zip(items, SPEC[key])):
        check_struct('%s[%d]' % (key, i), item, fields, problems)
assert not problems, '%d values did not come back as written, first: %s' % (len(problems), problems[:3])
kbd = None
for d in (mesh.get_editor_property('asset_user_data') or []):
    if d is not None and isinstance(d, unreal.SQEX_KBD_AssetUserData):
        kbd = d
if kbd is None:
    kbd = unreal.new_object(unreal.SQEX_KBD_AssetUserData, mesh)
    kbd.set_editor_property('BonamikDataList', [asset])
    mesh.set_editor_property('asset_user_data', [d for d in (mesh.get_editor_property('asset_user_data') or [])] + [kbd])
    out['mesh_action'] = 'added a SQEX_KBD_AssetUserData with it'
else:
    cur = [d for d in (kbd.get_editor_property('BonamikDataList') or []) if d is not None]
    if any(d.get_path_name().split('.')[0] == ASSET_PATH for d in cur):
        out['mesh_action'] = 'already its Bonamik'
    else:
        kbd.set_editor_property('BonamikDataList', cur + [asset])
        out['mesh_action'] = 'added to its Bonamik list'
listed = [d.get_path_name().split('.')[0] for d in (kbd.get_editor_property('BonamikDataList') or []) if d is not None]
assert ASSET_PATH in listed, 'the mesh does not list the Bonamik'
assert EAL.save_loaded_asset(asset, False), 'could not save ' + ASSET_PATH
out['saved'].append(ASSET_PATH)
if out['mesh_action'] != 'already its Bonamik':
    assert EAL.save_loaded_asset(mesh, False), 'could not save ' + MESH_PATH
    out['saved'].append(MESH_PATH)
out.update(bodies=len(SPEC['mBodies']), swinging=sum(1 for b in SPEC['mBodies'] if not b['m_IsKinematic']),
           cones=len(SPEC['mCones']), links=len(SPEC['mLinks']), shapes=len(SPEC['mShapes']),
           groups=[g['m_GroupName'] for g in SPEC['mGroups']], mesh_bonamiks=listed)

# (3) Sephiroth's mesh's Asset User Data, for comparison
seph = {}
for path in ('/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00', OUTFIT + '/Model/PC0010_10'):
    m = unreal.load_asset(path) if EAL.does_asset_exist(path) else None
    if m is None:
        seph[path] = 'not in the project'
        continue
    items = []
    for d in (m.get_editor_property('asset_user_data') or []):
        if d is None:
            continue
        entry = {'class': d.get_class().get_name()}
        for prop in ('BonamikDataList', 'KineDriverDataList', 'KineDriverList', 'KDIDataList'):
            try:
                v = d.get_editor_property(prop)
                entry[prop] = [x.get_path_name() if x else None for x in v]
            except Exception:
                pass
        items.append(entry)
    seph[path] = items
out['others'] = seph
result = json.dumps(out, indent=1)
