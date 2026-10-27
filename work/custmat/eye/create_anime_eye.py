"""Makes /Game/Shader/KadeMats/Materials/AnimeShaderEye: Rebirth's eye mapping with AnimeShader's toon look (one Custom
node, the code in anime_eye.hlsl). Its texture parameters have Rebirth's eye names (Color = sclera, IrisColor,
GazeNormal), so an instance of it takes a Rebirth eye's textures as they are; its brightness works as AnimeShader's
(Specular, EyeAdaptionMultiplier, divided by the eye adaptation twice). Run in the editor (editor link)."""
import os
import unreal

PATH = '/Game/Shader/KadeMats/Materials'
NAME = 'AnimeShaderEye'
HERE = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'ModExtract', 'seph1018', 'eye')
CODE = open(os.path.join(HERE, 'anime_eye.hlsl'), encoding='utf-8').read()

MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
result = {}
full = PATH + '/' + NAME
if EAL.does_asset_exist(full) or unreal.find_object(None, full + '.' + NAME):
    # (made by the first run of this script, which stopped part way: it did not exist before) redone from scratch
    mat = unreal.load_asset(full)
    MEL.delete_all_material_expressions(mat)
    result['redone'] = True
else:
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(NAME, PATH, unreal.Material, unreal.MaterialFactoryNew())
mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_OPAQUE)


def node(cls, x, y):
    return MEL.create_material_expression(mat, cls, x, y)


def texobj(name, path, sampler, x, y):
    e = node(unreal.MaterialExpressionTextureObjectParameter, x, y)
    e.set_editor_property('parameter_name', name)
    e.set_editor_property('texture', unreal.load_asset(path))
    e.set_editor_property('sampler_type', sampler)
    e.set_editor_property('group', 'Eye Textures')
    return e


def scalar(name, value, x, y, group='Anime Eye'):
    e = node(unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property('parameter_name', name)
    e.set_editor_property('default_value', value)
    e.set_editor_property('group', group)
    return e


def vector(name, value, x, y, group='Anime Eye'):
    e = node(unreal.MaterialExpressionVectorParameter, x, y)
    e.set_editor_property('parameter_name', name)
    e.set_editor_property('default_value', unreal.LinearColor(*value))
    e.set_editor_property('group', group)
    return e


ST = unreal.MaterialSamplerType
inputs = []                      # (custom input name, expression)
uv = node(unreal.MaterialExpressionTextureCoordinate, -1400, -200)
inputs.append(('UV', uv))
inputs.append(('Sclera', texobj('Color', '/Engine/EngineResources/WhiteSquareTexture', ST.SAMPLERTYPE_COLOR, -1400, -80)))
inputs.append(('Iris', texobj('IrisColor', '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Texture/PC0010_00_Eye_C',
                              ST.SAMPLERTYPE_COLOR, -1400, 120)))
inputs.append(('Gaze', texobj('GazeNormal', '/Engine/EngineMaterials/DefaultNormal', ST.SAMPLERTYPE_NORMAL, -1400, 320)))
params = [('RefractionIndex', 1.49), ('IrisDepth', 1.0), ('IrisRimDarken', 0.35), ('LidShadow', 0.3), ('LidSoftness', 0.04),
          ('ShadowIntensity', 0.4), ('MidIntensity', 0.8), ('HighlightIntensity', 0.45), ('HighlightSize', 0.06),
          ('HighlightX', 0.9), ('HighlightY', 0.9)]
y = 520
for name, value in params:
    inputs.append((name, scalar(name, value, -1400, y)))
    y += 90
inputs.append(('ShadowTint', vector('ShadowTint', (0.75, 0.85, 1.1, 1.0), -1400, y)))

custom = node(unreal.MaterialExpressionCustom, -900, 200)
custom.set_editor_property('code', CODE)
custom.set_editor_property('description', 'AnimeEye')
custom.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
custom_inputs = []
for n, _ in inputs:
    ci = unreal.CustomInput()
    ci.set_editor_property('input_name', n)
    custom_inputs.append(ci)
custom.set_editor_property('inputs', custom_inputs)
for n, e in inputs:
    MEL.connect_material_expressions(e, '', custom, n)

# brightness as AnimeShader: * Specular / EyeAdaptation / (EyeAdaptation * EyeAdaptionMultiplier)
spec = scalar('Specular', 0.7, -900, 520, 'Brightness')
mult = scalar('EyeAdaptionMultiplier', 1.0, -900, 620, 'Brightness')
ea = node(unreal.MaterialExpressionEyeAdaptation, -900, 720)
m1 = node(unreal.MaterialExpressionMultiply, -600, 300)
MEL.connect_material_expressions(custom, '', m1, 'A')
MEL.connect_material_expressions(spec, '', m1, 'B')
d1 = node(unreal.MaterialExpressionDivide, -450, 300)
MEL.connect_material_expressions(m1, '', d1, 'A')
MEL.connect_material_expressions(ea, '', d1, 'B')
m2 = node(unreal.MaterialExpressionMultiply, -600, 650)
MEL.connect_material_expressions(ea, '', m2, 'A')
MEL.connect_material_expressions(mult, '', m2, 'B')
d2 = node(unreal.MaterialExpressionDivide, -300, 300)
MEL.connect_material_expressions(d1, '', d2, 'A')
MEL.connect_material_expressions(m2, '', d2, 'B')
MEL.connect_material_property(d2, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
zero = node(unreal.MaterialExpressionConstant, -300, 500)
zero.set_editor_property('r', 0.0)
one = node(unreal.MaterialExpressionConstant, -300, 580)
one.set_editor_property('r', 1.0)
MEL.connect_material_property(zero, '', unreal.MaterialProperty.MP_BASE_COLOR)
MEL.connect_material_property(zero, '', unreal.MaterialProperty.MP_SPECULAR)
MEL.connect_material_property(zero, '', unreal.MaterialProperty.MP_METALLIC)
MEL.connect_material_property(one, '', unreal.MaterialProperty.MP_ROUGHNESS)

MEL.recompile_material(mat)
saved = EAL.save_loaded_asset(mat)
result['created'] = full
result['saved'] = saved
result['scalars'] = [str(n) for n in MEL.get_scalar_parameter_names(mat)]
result['textures'] = [str(n) for n in MEL.get_texture_parameter_names(mat)]
