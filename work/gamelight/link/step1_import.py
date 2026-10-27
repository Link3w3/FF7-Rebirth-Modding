import os
SRC = 'C:/FF7R2UProj/Saved/SandalphonStage/gamelight_1023'
DEST = '/Game/RebirthLighting/Textures'
names = ['T_RebirthLUT_SLUM7_day', 'T_RebirthLUT_Default_day', 'T_RebirthLUT_ACES_sRGB', 'T_MenuSky_Day_Ambient0', 'T_MenuSky_Day_Ambient1']
tasks = []
for n in names:
    t = unreal.AssetImportTask()
    t.set_editor_property('filename', SRC + '/' + n + '.dds')
    t.set_editor_property('destination_path', DEST)
    t.set_editor_property('destination_name', n)
    t.set_editor_property('automated', True)
    t.set_editor_property('replace_existing', True)
    t.set_editor_property('save', False)
    tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
out = {}
for n in names:
    a = unreal.load_asset(DEST + '/' + n)
    if a is None:
        out[n] = 'not imported'
        continue
    a.set_editor_property('srgb', False)
    a.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_HDR)
    if n.startswith('T_RebirthLUT'):
        a.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        a.set_editor_property('filter', unreal.TextureFilter.TF_BILINEAR)
        a.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
        a.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
        a.set_editor_property('never_stream', True)
        a.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_COLOR_LOOKUP_TABLE)
    else:
        a.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_SKYBOX)
    unreal.EditorAssetLibrary.save_loaded_asset(a)
    out[n] = [a.get_class().get_name(), a.blueprint_get_size_x(), a.blueprint_get_size_y()] if hasattr(a, 'blueprint_get_size_x') else a.get_class().get_name()
result = out
