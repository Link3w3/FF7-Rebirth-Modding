"""Imports the toonier textures (Saved/ModExtract/anime1025/toon/*_Toon.png) for Anime Sephiroth and his Masamune,
puts them on Anime Sephiroth's toon material instances in place of the game textures they were made from, and makes the
Masamune's toon material instance (M_UKing_Mat_Toon, its toon textures). Run in the editor (editor link)."""
import os
import unreal

HERE = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'ModExtract', 'anime1025', 'toon')
SEPH_DIR = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_10/ToonTextures'
MASA_DIR = '/Game/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Anime'
MIC_DIR = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_10/'
MICS = ['PC0010_00_BodyA', 'PC0010_00_BodyB', 'PC0010_00_Eye', 'PC0010_00_Eyebrow', 'PC0010_00_Eyelash', 'PC0010_00_Hair',
        'PC0010_00_HairCore', 'PC0010_00_Head', 'PC0010_00_Skin', 'PC0010_10_Wing']
SOURCES = {
    'PC0010_00_BodyA_C': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Texture/PC0010_00_BodyA_C',
    'PC0010_00_BodyA_N': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Texture/PC0010_00_BodyA_N',
    'PC0010_00_BodyB_C': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Texture/PC0010_00_BodyB_C',
    'PC0010_00_BodyB_N': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Texture/PC0010_00_BodyB_N',
    'PC0010_00_Hair_C': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Texture/PC0010_00_Hair_C',
    'PC0010_00_Hair_N': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Texture/PC0010_00_Hair_N',
    'PC0010_00_Head_C': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Texture/PC0010_00_Head_C',
    'PC0010_00_Head_N': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Texture/PC0010_00_Head_N',
    'PC0010_00_Eye_C': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Texture/PC0010_00_Eye_C',
    'PC0010_10_Wing_C': '/Game/Character/Player/PC0010_10_Sephiroth_Transform/Texture/PC0010_10_Wing_C',
    'PC0010_10_Wing_N': '/Game/Character/Player/PC0010_10_Sephiroth_Transform/Texture/PC0010_10_Wing_N',
    'WE1021_00_Body_C': '/Game/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Texture/WE1021_00_Body_C',
    'WE1021_00_Body_N': '/Game/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Texture/WE1021_00_Body_N',
}
TOON = '/Game/UKing/Materials/M_UKing_Mat_Toon'
WHITE1 = '/Game/UKing/Materials/T_UKing_White1'
MASA_MIC = 'WE1021_00_Body_Toon'

MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
result = {'imported': {}, 'mics': {}, 'errors': []}

# 1. the textures
tasks = []
for base in sorted(SOURCES):
    f = os.path.join(HERE, base + '_Toon.png')
    if not os.path.isfile(f):
        result['errors'].append('missing ' + f)
        continue
    t = unreal.AssetImportTask()
    t.set_editor_property('filename', f)
    t.set_editor_property('destination_path', MASA_DIR if base.startswith('WE1021') else SEPH_DIR)
    t.set_editor_property('destination_name', base + '_Toon')
    t.set_editor_property('replace_existing', True)
    t.set_editor_property('automated', True)
    t.set_editor_property('save', False)
    tasks.append(t)
AT.import_asset_tasks(tasks)
toon_of = {}
for base in sorted(SOURCES):
    path = (MASA_DIR if base.startswith('WE1021') else SEPH_DIR) + '/' + base + '_Toon'
    tex = unreal.load_asset(path)
    if tex is None:
        result['errors'].append('not imported: ' + path)
        continue
    normal = base.endswith('_N')
    tex.set_editor_property('srgb', not normal)
    tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP if normal
                            else unreal.TextureCompressionSettings.TC_DEFAULT)
    tex.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if normal
                            else unreal.TextureGroup.TEXTUREGROUP_CHARACTER)
    EAL.save_loaded_asset(tex)
    toon_of[SOURCES[base]] = tex
    result['imported'][path] = dict(w=tex.blueprint_get_size_x(), h=tex.blueprint_get_size_y(),
                                    srgb=tex.get_editor_property('srgb'),
                                    compression=str(tex.get_editor_property('compression_settings')))

# 2. Anime Sephiroth's material instances: each game texture they use that has a toon version, swapped
for name in MICS:
    mic = unreal.load_asset(MIC_DIR + name)
    if mic is None:
        result['errors'].append('no material instance ' + name)
        continue
    swapped = []
    for tv in mic.get_editor_property('texture_parameter_values'):
        pname = tv.get_editor_property('parameter_info').get_editor_property('name')
        val = tv.get_editor_property('parameter_value')
        if val is None:
            continue
        key = val.get_path_name().split('.', 1)[0]
        if key in toon_of:
            MEL.set_material_instance_texture_parameter_value(mic, pname, toon_of[key])
            swapped.append('%s: %s -> %s' % (pname, key.rsplit('/', 1)[-1], toon_of[key].get_name()))
    if swapped:
        MEL.update_material_instance(mic)
        EAL.save_loaded_asset(mic)
    result['mics'][name] = swapped

# 3. the Masamune's toon material instance
full = MASA_DIR + '/' + MASA_MIC
mic = unreal.load_asset(full) if EAL.does_asset_exist(full) else \
    AT.create_asset(MASA_MIC, MASA_DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
MEL.set_material_instance_parent(mic, unreal.load_asset(TOON))
MEL.set_material_instance_texture_parameter_value(mic, 'Coverage', unreal.load_asset(WHITE1))
MEL.set_material_instance_texture_parameter_value(mic, '_a0', toon_of[SOURCES['WE1021_00_Body_C']])
MEL.set_material_instance_texture_parameter_value(mic, '_n0', toon_of[SOURCES['WE1021_00_Body_N']])
MEL.update_material_instance(mic)
result['masamune_mic'] = dict(path=full, saved=EAL.save_loaded_asset(mic),
                              parent=mic.get_editor_property('parent').get_path_name())
