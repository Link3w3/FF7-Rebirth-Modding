# PC0010_13_Young_Sephiroth into the End project (editor link, no dialogs): ch049_001 re-rigged on Rebirth's PC0010 bones
# (rig_ys.py / build_rig_fbx.py), with his Rebirth materials and textures copied into its own folder (renamed PC0010_13_*),
# his Bonamik on the new bones (PC0010_13_BNM, make_bnm_spec.py), and checks of the imported skeleton against rig.json.
# Nothing of CH049_001 or the outfit is changed. Re-running skips what already exists (the mesh is not re-imported).
import unreal, json, os
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
MEL = unreal.MaterialEditingLibrary
HERE = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'ModExtract', 'ys13')
SRC = '/Game/Character/Player/PC0010_10_Young_Sephiroth_Outfit_Transformed'
BASE = '/Game/Character/Player/PC0010_13_Young_Sephiroth'
MESH = BASE + '/Model/PC0010_13'
out = {'steps': [], 'textures': {}, 'mis': {}}

# 1. textures: copies under PC0010_13_ names
tex_map = {}
for a in EAL.list_assets(SRC + '/Texture', recursive=False, include_folder=False):
    pkg = a.split('.')[0]
    name = pkg.rsplit('/', 1)[-1]
    if not name.startswith('CH049_001_'):
        continue
    new = BASE + '/Texture/' + name.replace('CH049_001_', 'PC0010_13_')
    if not EAL.does_asset_exist(new):
        EAL.duplicate_asset(pkg, new)
    tex_map[pkg] = new
    out['textures'][name] = new.rsplit('/', 1)[-1]

# 2. material instances: copies whose textures are the copies
SLOT_MI = {'mat_ch049_001_body': 'Body', 'mat_ch049_001_head': 'Head', 'mat_ch049_001_hair': 'Hair', 'mat_ch049_001_hair_tp': 'Hair',
           'mat_ch049_001_eyelash': 'Eyelash', 'mat_ch049_001_eye_shadow': 'EyeShadow', 'mat_ch049_001_eye': 'Eye'}
mis = {}
for part in sorted(set(SLOT_MI.values())):
    src = SRC + '/Material/CH049_001_' + part
    new = BASE + '/Material/PC0010_13_' + part
    if not EAL.does_asset_exist(new):
        EAL.duplicate_asset(src, new)
    mi = unreal.load_asset(new)
    changed = []
    for tp in mi.get_editor_property('texture_parameter_values'):
        name = tp.get_editor_property('parameter_info').get_editor_property('name')
        t = tp.get_editor_property('parameter_value')
        if t is None:
            continue
        p = t.get_path_name().split('.')[0]
        if p in tex_map:
            MEL.set_material_instance_texture_parameter_value(mi, name, unreal.load_asset(tex_map[p]))
            changed.append(str(name))
    MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi, False)
    left = [str(tp.get_editor_property('parameter_value').get_path_name()) for tp in mi.get_editor_property('texture_parameter_values')
            if tp.get_editor_property('parameter_value') is not None and tp.get_editor_property('parameter_value').get_path_name().startswith(SRC)]
    parent = mi.get_editor_property('parent')
    mis[part] = mi
    out['mis'][part] = dict(parent=parent.get_name() if parent else None, textures_repointed=changed, still_outfit=left)
for t in tex_map.values():
    EAL.save_asset(t, False)

# 3. the mesh (a new skeleton, PC0010_13_Skeleton)
if not EAL.does_asset_exist(MESH):
    ui = unreal.FbxImportUI()
    ui.set_editor_property('import_mesh', True)
    ui.set_editor_property('import_as_skeletal', True)
    ui.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    ui.set_editor_property('import_animations', False)
    ui.set_editor_property('import_materials', False)
    ui.set_editor_property('import_textures', False)
    ui.set_editor_property('create_physics_asset', False)
    sk = ui.get_editor_property('skeletal_mesh_import_data')
    sk.set_editor_property('import_morph_targets', False)
    sk.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    sk.set_editor_property('normal_generation_method', unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
    sk.set_editor_property('vertex_color_import_option', unreal.VertexColorImportOption.REPLACE)
    sk.set_editor_property('convert_scene', True)
    sk.set_editor_property('preserve_smoothing_groups', True)
    sk.set_editor_property('use_t0_as_ref_pose', False)
    sk.set_editor_property('update_skeleton_reference_pose', False)
    t = unreal.AssetImportTask()
    t.set_editor_property('filename', os.path.join(HERE, 'PC0010_13.fbx'))
    t.set_editor_property('destination_path', BASE + '/Model')
    t.set_editor_property('destination_name', 'PC0010_13')
    t.set_editor_property('automated', True)
    t.set_editor_property('save', True)
    t.set_editor_property('replace_existing', False)
    t.set_editor_property('options', ui)
    AT.import_asset_tasks([t])
    out['steps'].append('imported: ' + ', '.join(str(p) for p in t.get_editor_property('imported_object_paths')))
sm = unreal.load_asset(MESH)
assert sm is not None, 'the FBX import made no skeletal mesh'
mats = sm.get_editor_property('materials')
slots = []
for m in mats:
    s = str(m.get_editor_property('material_slot_name'))
    key = s if s in SLOT_MI else str(m.get_editor_property('imported_material_slot_name'))
    if key in SLOT_MI:
        m.set_editor_property('material_interface', mis[SLOT_MI[key]])
    mi = m.get_editor_property('material_interface')
    slots.append((s, mi.get_name() if mi else None))
sm.set_editor_property('materials', mats)
EAL.save_loaded_asset(sm, False)
skel = sm.get_editor_property('skeleton')
out['mesh'] = dict(path=sm.get_path_name(), skeleton=skel.get_path_name() if skel else None, slots=slots,
                   bounds=str(sm.get_bounds().box_extent))

# 4. checks: every bone, its parent and its rest place against rig.json
exp = json.load(open(os.path.join(HERE, 'expected_locals.json')))
c = unreal.new_object(unreal.SkeletalMeshComponent)
c.set_skeletal_mesh(sm)
n = c.get_num_bones()
names = [str(c.get_bone_name(i)) for i in range(n)]
bad_parent, worst = [], (0.0, None)
for i, nm in enumerate(names):
    want = exp['parents'].get(nm, 'MISSING')
    par = str(c.get_parent_bone(nm))
    if (want or 'None') != par:
        bad_parent.append((nm, par, want))
    p = c.get_ref_pose_position(i)
    e = exp['local_positions'].get(nm)
    if e:
        d = max(abs(p.x - e[0]), abs(p.y - e[1]), abs(p.z - e[2]))
        if d > worst[0]:
            worst = (d, nm)
out['check'] = dict(bones=n, expected=len(exp['parents']), missing=sorted(set(exp['parents']) - set(names))[:10],
                    extra=sorted(set(names) - set(exp['parents']))[:10], bad_parents=bad_parent[:10],
                    largest_rest_place_difference=[round(worst[0], 4), worst[1]])
result = json.dumps(out, indent=1)
