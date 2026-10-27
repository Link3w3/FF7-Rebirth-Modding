"""Makes /Game/UKing/Materials/M_UKing_Mat_Toon_Eye: a Rebirth eye drawn with M_UKing_Mat_Toon's light (one Custom node,
the code in uking_toon_eye.hlsl). Its texture parameters are named as Rebirth's eye materials name them (Color = the
sclera, IrisColor, GazeNormal, IrisEmissive), so an instance takes a Rebirth eye's textures as they are; the light is
MPC_UKing's (SunDirection, SunColor, AmbientColor, ToonParams), read as M_UKing_Mat_Toon reads it. Opaque, Default Lit,
the colour in Emissive and Base Color black, as M_UKing_Mat_Toon. Run in the editor (editor link)."""
import os
import unreal

PATH = '/Game/UKing/Materials'
NAME = 'M_UKing_Mat_Toon_Eye'
HERE = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'ModExtract', 'anime1025')
CODE = open(os.path.join(HERE, 'uking_toon_eye.hlsl'), encoding='utf-8').read()
MPC = '/Game/UKing/Materials/MPC_UKing'
TEX_SCLERA = '/Game/Character/Common/Eye/Texture/Common_Eye_Player_C'
TEX_GAZE = '/Game/Character/Common/Eye/Texture/Common_Eye_Player_NG'
TEX_IRIS = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Texture/PC0010_00_Eye_C'

MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
result = {}
full = PATH + '/' + NAME
if EAL.does_asset_exist(full):
    mat = unreal.load_asset(full)
    MEL.delete_all_material_expressions(mat)
    result['redone'] = True
else:
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(NAME, PATH, unreal.Material, unreal.MaterialFactoryNew())
mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_OPAQUE)
mat.set_editor_property('two_sided', False)
mat.set_editor_property('used_with_skeletal_mesh', True)
mat.set_editor_property('used_with_morph_targets', True)
mpc = unreal.load_asset(MPC)
if mpc is None:
    raise RuntimeError('MPC_UKing is not there')


def node(cls, x, y):
    return MEL.create_material_expression(mat, cls, x, y)


def texobj(name, path, sampler, x, y):
    e = node(unreal.MaterialExpressionTextureObjectParameter, x, y)
    e.set_editor_property('parameter_name', name)
    t = unreal.load_asset(path)
    if t is None:
        raise RuntimeError('no texture ' + path)
    e.set_editor_property('texture', t)
    e.set_editor_property('sampler_type', sampler)
    e.set_editor_property('group', 'Eye Textures')
    return e


def scalar(name, value, x, y, group='Toon Eye'):
    e = node(unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property('parameter_name', name)
    e.set_editor_property('default_value', value)
    e.set_editor_property('group', group)
    return e


def vector(name, value, x, y, group='Toon Eye'):
    e = node(unreal.MaterialExpressionVectorParameter, x, y)
    e.set_editor_property('parameter_name', name)
    e.set_editor_property('default_value', unreal.LinearColor(*value))
    e.set_editor_property('group', group)
    return e


def collection(name, x, y, rgb):
    e = node(unreal.MaterialExpressionCollectionParameter, x, y)
    e.set_editor_property('collection', mpc)
    e.set_editor_property('parameter_name', name)
    if not rgb:
        return e
    m = node(unreal.MaterialExpressionComponentMask, x + 260, y)
    for c, on in (('r', True), ('g', True), ('b', True), ('a', False)):
        m.set_editor_property(c, on)
    MEL.connect_material_expressions(e, '', m, '')
    return m


def screen_marker(src, x, y):
    """src * (EyeAdaptation * 0 + 1): the same value in the editor, and the mark Game Materials reads (EyeAdaptationLookup in
    the material's code) to show the material in the game at a fixed exposure, the brightness the editor shows at exposure 1,
    instead of as light of the game's scene (whose daylight exposure would leave an emissive toon colour near black)."""
    ea = node(unreal.MaterialExpressionEyeAdaptation, x, y + 200)
    zero = node(unreal.MaterialExpressionConstant, x, y + 300)
    zero.set_editor_property('r', 0.0)
    one = node(unreal.MaterialExpressionConstant, x + 150, y + 300)
    one.set_editor_property('r', 1.0)
    m0 = node(unreal.MaterialExpressionMultiply, x + 150, y + 200)
    MEL.connect_material_expressions(ea, '', m0, 'A')
    MEL.connect_material_expressions(zero, '', m0, 'B')
    a1 = node(unreal.MaterialExpressionAdd, x + 300, y + 200)
    MEL.connect_material_expressions(m0, '', a1, 'A')
    MEL.connect_material_expressions(one, '', a1, 'B')
    out = node(unreal.MaterialExpressionMultiply, x + 450, y)
    MEL.connect_material_expressions(src, '', out, 'A')
    MEL.connect_material_expressions(a1, '', out, 'B')
    return out


ST = unreal.MaterialSamplerType
inputs = []                      # (custom input name, expression), in the order the code's function takes them
inputs.append(('UV', node(unreal.MaterialExpressionTextureCoordinate, -1500, -400)))
inputs.append(('Sclera', texobj('Color', TEX_SCLERA, ST.SAMPLERTYPE_COLOR, -1500, -300)))
inputs.append(('Iris', texobj('IrisColor', TEX_IRIS, ST.SAMPLERTYPE_COLOR, -1500, -100)))
inputs.append(('Gaze', texobj('GazeNormal', TEX_GAZE, ST.SAMPLERTYPE_NORMAL, -1500, 100)))
inputs.append(('IrisGlow', texobj('IrisEmissive', TEX_IRIS, ST.SAMPLERTYPE_COLOR, -1500, 300)))
params = [('RefractionIndex', 1.49), ('IrisDepth', 1.0), ('IrisRimDarken', 0.35), ('LidShadow', 0.3), ('LidSoftness', 0.04),
          ('LidShadowStrength', 0.3), ('EyeShadowLift', 0.35), ('GlowIntensity', 0.35), ('HighlightIntensity', 1.0),
          ('HighlightSize', 0.06), ('HighlightX', 0.9), ('HighlightY', 0.9)]
y = 500
for name, value in params:
    inputs.append((name, scalar(name, value, -1500, y)))
    y += 90
inputs.append(('GlowColor', vector('GlowColor', (1.0, 1.0, 1.0, 1.0), -1500, y)))
y += 200
inputs.append(('SunDirection', collection('SunDirection', -1800, y, True)))
inputs.append(('SunColor', collection('SunColor', -1800, y + 120, True)))
inputs.append(('AmbientColor', collection('AmbientColor', -1800, y + 240, True)))
inputs.append(('ToonParams', collection('ToonParams', -1800, y + 360, False)))

custom = node(unreal.MaterialExpressionCustom, -900, 200)
custom.set_editor_property('code', CODE)
custom.set_editor_property('description', 'UKing Toon Eye')
custom.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
custom_inputs = []
for n, _ in inputs:
    ci = unreal.CustomInput()
    ci.set_editor_property('input_name', n)
    custom_inputs.append(ci)
custom.set_editor_property('inputs', custom_inputs)
for n, e in inputs:
    MEL.connect_material_expressions(e, '', custom, n)
MEL.connect_material_property(screen_marker(custom, -650, 200), '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
black = node(unreal.MaterialExpressionConstant, -500, -100)
black.set_editor_property('r', 0.0)
MEL.connect_material_property(black, '', unreal.MaterialProperty.MP_BASE_COLOR)

MEL.recompile_material(mat)
result['saved'] = EAL.save_loaded_asset(mat)
result['material'] = full
result['scalars'] = [str(n) for n in MEL.get_scalar_parameter_names(mat)]
result['vectors'] = [str(n) for n in MEL.get_vector_parameter_names(mat)]
result['textures'] = [str(n) for n in MEL.get_texture_parameter_names(mat)]
