# Nameless in the game's own material: his textures in Rebirth's layout (WE1021_49_Body_C / _N / _Mr / _Mg, made from his
# AAAX / NNNX / MROX like ch049_001's), a WE1021_49_Body material instance of the retail RMI_Surface_Standard_Wide (the
# Masamune's family; texture parameters only, so the game's shaders serve it), assigned to his mesh's slot. His
# WE1021_49_Mat00 (M_UnityToon) stays in the folder, unassigned. Re-running skips what exists. No dialogs.
import unreal, json, os
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
MEL = unreal.MaterialEditingLibrary
SRC = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'ModExtract', 'ys13', 'nameless_ue')
F = '/Game/Character/Weapon/WE1021_49_Nameless'
out = {'textures': {}, 'steps': []}
tasks = []
for f in sorted(os.listdir(SRC)):
    if not f.endswith('.png') or EAL.does_asset_exist(F + '/Texture/' + f[:-4]):
        continue
    t = unreal.AssetImportTask()
    t.set_editor_property('filename', os.path.join(SRC, f))
    t.set_editor_property('destination_path', F + '/Texture')
    t.set_editor_property('destination_name', f[:-4])
    t.set_editor_property('automated', True)
    t.set_editor_property('save', False)
    t.set_editor_property('replace_existing', False)
    tasks.append(t)
if tasks:
    AT.import_asset_tasks(tasks)
    out['steps'].append('imported %d textures' % len(tasks))
for f in sorted(os.listdir(SRC)):
    if not f.endswith('.png'):
        continue
    name = f[:-4]
    tex = unreal.load_asset(F + '/Texture/' + name)
    assert tex is not None, name
    kind = name.split('_')[-1]
    if kind == 'C':
        tex.set_editor_property('srgb', True)
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_DEFAULT)
    elif kind == 'N':
        tex.set_editor_property('srgb', False)
        tex.set_editor_property('flip_green_channel', True)          # (Unity's maps are OpenGL / Y+)
        tex.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP)
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
    else:                                                           # Mr, Mg: single channel like the game's BC4 maps
        tex.set_editor_property('srgb', False)
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_ALPHA)
    EAL.save_loaded_asset(tex, False)
    out['textures'][name] = '%s srgb=%s flipg=%s %dx%d' % (str(tex.get_editor_property('compression_settings')).split('.')[-1].split(':')[0],
                                                       tex.get_editor_property('srgb'), tex.get_editor_property('flip_green_channel'),
                                                       tex.blueprint_get_size_x(), tex.blueprint_get_size_y())
path = F + '/Material/WE1021_49_Body'
mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else \
    AT.create_asset('WE1021_49_Body', F + '/Material', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
parent = unreal.load_asset('/Game/Renderer/MaterialInstance/Surface/RMI_Surface_Standard_Wide')
assert parent is not None
MEL.set_material_instance_parent(mi, parent)
res = {}
for p, v in {'Color': 'WE1021_49_Body_C', 'Normal': 'WE1021_49_Body_N', 'Metallic': 'WE1021_49_Body_Mr', 'Roughness': 'WE1021_49_Body_Mg'}.items():
    t = unreal.load_asset(F + '/Texture/' + v)
    res[p] = (v, MEL.set_material_instance_texture_parameter_value(mi, p, t))
MEL.update_material_instance(mi)
EAL.save_loaded_asset(mi, False)
out['mi'] = dict(path=path, parent=mi.get_editor_property('parent').get_path_name(), params=res)
sm = unreal.load_asset(F + '/Model/WE1021_49')
mats = sm.get_editor_property('materials')
slots = []
for m in mats:
    m.set_editor_property('material_interface', mi)
    slots.append(str(m.get_editor_property('material_slot_name')))
sm.set_editor_property('materials', mats)
EAL.save_loaded_asset(sm, False)
out['mesh'] = dict(slots=slots, now=[m.get_editor_property('material_interface').get_path_name() for m in sm.get_editor_property('materials')])
result = json.dumps(out, indent=1)
