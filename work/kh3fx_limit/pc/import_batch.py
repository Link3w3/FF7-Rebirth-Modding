"""(Editor link) Imports one batch of KH3 meshes (FBX) or textures (PNG) under /Game/KH3/Effects/<KH3 folder>, with the
settings KH3 had; skips what is already there. KIND and KEYS are filled in by the caller."""
import json
import os
import unreal

HERE = r'C:\FF7R2UProj\Saved\ModExtract\kh3fx_limit'
KIND = __KIND__
KEYS = __KEYS__
result = {}


def dest_of(path):
    pkg = path.split('.', 1)[0]
    return '/Game/KH3/Effects/' + '/'.join(pkg[len('/Game/Effects/'):].split('/')[:-1])


def enum(e, name, default):
    try:
        return getattr(e, name.upper())
    except AttributeError:
        return default


def mesh_options():
    ui = unreal.FbxImportUI()
    for k, v in (('import_mesh', True), ('import_as_skeletal', False), ('import_materials', False),
                 ('import_textures', False), ('import_animations', False), ('create_physics_asset', False),
                 ('automated_import_should_detect_type', False),
                 ('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH)):
        ui.set_editor_property(k, v)
    sm = ui.get_editor_property('static_mesh_import_data')
    for k, v in (('combine_meshes', True), ('auto_generate_collision', False), ('generate_lightmap_u_vs', False),
                 ('remove_degenerates', False), ('build_adjacency_buffer', False),
                 ('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS),
                 ('vertex_color_import_option', unreal.VertexColorImportOption.REPLACE),
                 ('convert_scene', True), ('force_front_x_axis', False), ('convert_scene_unit', False),
                 ('import_uniform_scale', 1.0), ('reorder_material_to_fbx_order', True)):
        sm.set_editor_property(k, v)
    return ui


info = json.load(open(os.path.join(HERE, 'mesh_info.json' if KIND == 'mesh' else 'tex_settings.json')))
tasks = []
for key in KEYS:
    i = info[key]
    dest = dest_of(key)
    name = i['name']
    if unreal.EditorAssetLibrary.does_asset_exist('%s/%s' % (dest, name)):
        result[name] = 'already there'
        continue
    t = unreal.AssetImportTask()
    t.set_editor_property('filename', os.path.join(HERE, (i['fbx'] if KIND == 'mesh' else i['png']).replace('/', '\\')))
    t.set_editor_property('destination_path', dest)
    t.set_editor_property('destination_name', name)
    t.set_editor_property('automated', True)
    t.set_editor_property('replace_existing', True)
    t.set_editor_property('save', KIND == 'mesh')
    if KIND == 'mesh':
        t.set_editor_property('options', mesh_options())
    tasks.append((key, t))
if tasks:
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t for _, t in tasks])
for key, t in tasks:
    i = info[key]
    asset = unreal.load_asset('%s/%s' % (dest_of(key), i['name']))
    if not asset:
        result[i['name']] = 'NOT IMPORTED'
        continue
    if KIND == 'tex':
        T = unreal.TextureCompressionSettings
        asset.set_editor_property('srgb', bool(i['SRGB']))
        asset.set_editor_property('compression_settings', enum(T, i['CompressionSettings'], T.TC_DEFAULT))
        lod = i['LODGroup'] if i['LODGroup'] != 'TEXTUREGROUP_SQEXEffectNormalMap' else 'TEXTUREGROUP_WorldNormalMap'
        asset.set_editor_property('lod_group', enum(unreal.TextureGroup, lod, unreal.TextureGroup.TEXTUREGROUP_EFFECTS))
        asset.set_editor_property('address_x', enum(unreal.TextureAddress, i['AddressX'], unreal.TextureAddress.TA_WRAP))
        asset.set_editor_property('address_y', enum(unreal.TextureAddress, i['AddressY'], unreal.TextureAddress.TA_WRAP))
        asset.set_editor_property('filter', enum(unreal.TextureFilter, i['Filter'], unreal.TextureFilter.TF_DEFAULT))
        ok = unreal.EditorAssetLibrary.save_loaded_asset(asset, False)
        result[i['name']] = 'ok' if ok else 'not saved'
    else:
        result[i['name']] = 'ok'
