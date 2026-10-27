# (follow-up after the save: skeleton, Nameless, checks) PC0010_13 reimported over itself from PC0010_13_v4.fbx: the v3 scene (his rig, face, the wing) unchanged, plus his hair
# core (PC0010_13_HairCore_geo: an opaque shell over his scalp and the back of his neck, under his hair cards; weights on
# C_Head_a / C_Neck_a / C_Spine_d; material slot PC0010_13_HairCore). The mesh asset stays (replace_existing): sockets,
# Asset User Data (his Bonamik, the wing's Bonamik, the wing's KineDriver) checked against what it had; every slot gets
# back the material it had. New: the material instance PC0010_13_HairCore (a copy of PC0010_13_Hair, RMI_Surface_Hair_Wide,
# with its Coverage white, so the core is opaque wherever its UVs fall) on the new slot. Bones, parents and rest places
# checked against expected_locals_v3.json. No dialogs.
import unreal, json, os
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
HERE = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'ModExtract', 'ys13')
BASE = '/Game/Character/Player/PC0010_13_Young_Sephiroth'
MESH = BASE + '/Model/PC0010_13'
SKEL = BASE + '/Model/PC0010_13_Skeleton'
HAIR_MI = BASE + '/Material/PC0010_13_Hair'
CORE_MI = BASE + '/Material/PC0010_13_HairCore'
CORE_SLOT = 'PC0010_13_HairCore'
WHITE = '/Game/Renderer/Texture/FFFFFFFF_BC4'
FBX = os.path.join(HERE, 'PC0010_13_v4.fbx')
NAMELESS = '/Game/Character/Weapon/WE1021_49_Nameless/Model/WE1021_49'
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


def verts(sm):
    try:
        return unreal.EditorSkeletalMeshLibrary.get_num_verts(sm, 0)
    except Exception as e:
        return 'n/a: %s' % e


before = json.load(open(os.path.join(HERE, 'pc0010_13_before_core.json')))
sm = unreal.load_asset(MESH)
fixed = []
nameless_before = ['/Game/Character/Weapon/WE1021_49_Nameless/Material/WE1021_49_Body.WE1021_49_Body']
dirty = [str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
out['dirty_before_saves'] = dirty
if SKEL in dirty:
    assert EAL.save_asset(SKEL, False), 'could not save ' + SKEL
    fixed.append('skeleton saved')
wm = unreal.load_asset(NAMELESS)
wmats = wm.get_editor_property('materials')
if [m.get_editor_property('material_interface').get_path_name() for m in wmats] != nameless_before:
    for i in range(len(wmats)):
        m = wmats[i]
        m.set_editor_property('material_interface', unreal.load_asset(nameless_before[i].split('.')[0]))
        wmats[i] = m
    wm.set_editor_property('materials', wmats)
    wm.modify()
    EAL.save_loaded_asset(wm, False)
    fixed.append('Nameless material')
after = state(unreal.load_asset(MESH))
out['fixed'] = fixed
out['sockets'] = [len(before['sockets']), len(after['sockets']), before['sockets'] == after['sockets']]
out['kbd'] = after['kbd']
out['kbd_same'] = before['kbd'] == after['kbd']
out['materials'] = after['materials']
out['verts_after'] = verts(sm)
exp = json.load(open(os.path.join(HERE, 'expected_locals_v3.json')))
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
b = sm.get_bounds()
out['bounds'] = dict(origin=[round(b.origin.x, 1), round(b.origin.y, 1), round(b.origin.z, 1)], extent=[round(b.box_extent.x, 1), round(b.box_extent.y, 1), round(b.box_extent.z, 1)])
out['dirty_after'] = [str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
json.dump(out, open(os.path.join(HERE, 'ys13_reimport_core.out'), 'w'), indent=1)
result = json.dumps(out, indent=1)
