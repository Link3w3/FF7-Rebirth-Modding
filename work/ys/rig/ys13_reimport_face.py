# PC0010_13 reimported over itself from PC0010_13_v2.fbx (his face on Rebirth's face rig: rig_ys.py FACE): the mesh asset
# stays (replace_existing), so its sockets and Asset User Data (his Bonamik) should come through (checked against what it
# had before). His material slots get his Unity materials (the user's choice: mat_ch049_001_* on M_UnityToon, in the
# outfit's Material/Unity folder; the Game Materials converter makes them for the game), and the Nameless's slot its own
# WE1021_49_Mat00 again. Bones, parents and rest places checked against rig.json (expected_locals_v2.json). No dialogs.
import unreal, json, os
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
HERE = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'ModExtract', 'ys13')
BASE = '/Game/Character/Player/PC0010_13_Young_Sephiroth'
MESH = BASE + '/Model/PC0010_13'
out = {}


def state(sm):
    socks = []
    for i in range(sm.num_sockets()):
        s = sm.get_socket_by_index(i)
        l, r = s.get_editor_property('relative_location'), s.get_editor_property('relative_rotation')
        socks.append([str(s.get_editor_property('socket_name')), str(s.get_editor_property('bone_name')),
                      [round(l.x, 3), round(l.y, 3), round(l.z, 3)], [round(r.roll, 2), round(r.pitch, 2), round(r.yaw, 2)]])
    kbd = []
    for d in (sm.get_editor_property('asset_user_data') or []):
        if d is None:
            continue
        e = {'class': d.get_class().get_name()}
        for prop in ('BonamikDataList', 'KineDriverDataList'):
            try:
                e[prop] = [x.get_path_name() if x else None for x in d.get_editor_property(prop)]
            except Exception:
                pass
        kbd.append(e)
    mats = {str(m.get_editor_property('material_slot_name')): (m.get_editor_property('material_interface').get_path_name().split('.')[0]
                                                               if m.get_editor_property('material_interface') else None)
            for m in sm.get_editor_property('materials')}
    return dict(sockets=socks, kbd=kbd, materials=mats)


before = state(unreal.load_asset(MESH))
json.dump(before, open(os.path.join(HERE, 'pc0010_13_before_face.json'), 'w'), indent=1)
ui = unreal.FbxImportUI()
ui.set_editor_property('import_mesh', True)
ui.set_editor_property('import_as_skeletal', True)
ui.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_SKELETAL_MESH)
ui.set_editor_property('import_animations', False)
ui.set_editor_property('import_materials', False)
ui.set_editor_property('import_textures', False)
ui.set_editor_property('create_physics_asset', False)
ui.set_editor_property('skeleton', unreal.load_asset(BASE + '/Model/PC0010_13_Skeleton'))
sk = ui.get_editor_property('skeletal_mesh_import_data')
sk.set_editor_property('import_morph_targets', False)
sk.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
sk.set_editor_property('normal_generation_method', unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
sk.set_editor_property('vertex_color_import_option', unreal.VertexColorImportOption.REPLACE)
sk.set_editor_property('convert_scene', True)
sk.set_editor_property('preserve_smoothing_groups', True)
sk.set_editor_property('use_t0_as_ref_pose', False)
sk.set_editor_property('update_skeleton_reference_pose', True)
t = unreal.AssetImportTask()
t.set_editor_property('filename', os.path.join(HERE, 'PC0010_13_v2.fbx'))
t.set_editor_property('destination_path', BASE + '/Model')
t.set_editor_property('destination_name', 'PC0010_13')
t.set_editor_property('automated', True)
t.set_editor_property('save', False)
t.set_editor_property('replace_existing', True)
t.set_editor_property('options', ui)
AT.import_asset_tasks([t])
out['imported'] = [str(p) for p in t.get_editor_property('imported_object_paths')]
sm = unreal.load_asset(MESH)
after = state(sm)
# material slots: his Unity materials, by slot name
UNITY = '/Game/Character/Player/PC0010_10_Young_Sephiroth_Outfit_Transformed/Material/Unity/'
fixed = []
mats = sm.get_editor_property('materials')
for i in range(len(mats)):
    m = mats[i]
    slot = str(m.get_editor_property('material_slot_name'))
    want = UNITY + slot
    assert EAL.does_asset_exist(want), want
    have = m.get_editor_property('material_interface')
    if have is None or have.get_path_name().split('.')[0] != want:
        m.set_editor_property('material_interface', unreal.load_asset(want))
        mats[i] = m
        fixed.append(slot)
sm.set_editor_property('materials', mats)
# the Nameless: its own material again
wm = unreal.load_asset('/Game/Character/Weapon/WE1021_49_Nameless/Model/WE1021_49')
wmats = wm.get_editor_property('materials')
for i in range(len(wmats)):
    m = wmats[i]
    m.set_editor_property('material_interface', unreal.load_asset('/Game/Character/Weapon/WE1021_49_Nameless/Material/WE1021_49_Mat00'))
    wmats[i] = m
wm.set_editor_property('materials', wmats)
wm.modify()
EAL.save_loaded_asset(wm, False)
out['nameless_material'] = [m.get_editor_property('material_interface').get_path_name() for m in
                            unreal.load_asset('/Game/Character/Weapon/WE1021_49_Nameless/Model/WE1021_49').get_editor_property('materials')]
# the Bonamik in the user data
kb = [d for d in (sm.get_editor_property('asset_user_data') or []) if d is not None and isinstance(d, unreal.SQEX_KBD_AssetUserData)]
if not kb:
    k = unreal.new_object(unreal.SQEX_KBD_AssetUserData, sm)
    k.set_editor_property('BonamikDataList', [unreal.load_asset(BASE + '/Model/PC0010_13_BNM')])
    sm.set_editor_property('asset_user_data', [d for d in (sm.get_editor_property('asset_user_data') or [])] + [k])
    fixed.append('KBD user data')
sm.modify()
EAL.save_loaded_asset(sm, False)
EAL.save_asset(BASE + '/Model/PC0010_13_Skeleton', False)
after = state(unreal.load_asset(MESH))
out['fixed'] = fixed
out['sockets'] = [len(before['sockets']), len(after['sockets']), before['sockets'] == after['sockets']]
out['kbd'] = after['kbd']
out['materials'] = after['materials']
# bones against rig.json
exp = json.load(open(os.path.join(HERE, 'expected_locals_v2.json')))
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
