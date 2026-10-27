"""Makes /Game/UKing/Materials/M_UKing_Mat_Toon_Lite: what M_UKing_Mat_Toon draws with its default options, without its
interpreter of every BotW option (one small Custom node, uking_toon_lite.hlsl): the same parameters an instance of it
sets (Coverage, _a0, _n0), Masked at 0.5, Default Lit, the colour in Emissive and Base Color black, the light from
MPC_UKing as M_UKing_Mat_Toon reads it. Then puts Anime Sephiroth's toon material instances (all but the eye's) and the
Masamune's on it. Run in the editor (editor link)."""
import os
import unreal

PATH = '/Game/UKing/Materials'
NAME = 'M_UKing_Mat_Toon_Lite'
HERE = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'ModExtract', 'anime1025')
CODE = open(os.path.join(HERE, 'uking_toon_lite.hlsl'), encoding='utf-8').read()
MPC = '/Game/UKing/Materials/MPC_UKing'
D = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_10/'
MICS = [D + n for n in ('PC0010_00_BodyA', 'PC0010_00_BodyB', 'PC0010_00_Eyebrow', 'PC0010_00_Eyelash', 'PC0010_00_Hair',
                        'PC0010_00_HairCore', 'PC0010_00_Head', 'PC0010_00_Skin', 'PC0010_10_Wing')]
MICS.append('/Game/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Anime/WE1021_00_Body_Toon')
TOON = '/Game/UKing/Materials/M_UKing_Mat_Toon'

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
mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
mat.set_editor_property('opacity_mask_clip_value', 0.5)
mat.set_editor_property('two_sided', False)
mat.set_editor_property('used_with_skeletal_mesh', True)
mpc = unreal.load_asset(MPC)
ST = unreal.MaterialSamplerType


def node(cls, x, y):
    return MEL.create_material_expression(mat, cls, x, y)


def texobj(name, path, sampler, x, y):
    e = node(unreal.MaterialExpressionTextureObjectParameter, x, y)
    e.set_editor_property('parameter_name', name)
    e.set_editor_property('texture', unreal.load_asset(path))
    e.set_editor_property('sampler_type', sampler)
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


uv = node(unreal.MaterialExpressionTextureCoordinate, -1400, -300)
inputs = [('UV', uv),
          ('A0', texobj('_a0', '/Game/UKing/Materials/T_UKing_White', ST.SAMPLERTYPE_COLOR, -1400, -180)),
          ('N0', texobj('_n0', '/Game/UKing/Materials/T_UKing_FlatNormal', ST.SAMPLERTYPE_NORMAL, -1400, 20)),
          ('SunDirection', collection('SunDirection', -1700, 250, True)),
          ('SunColor', collection('SunColor', -1700, 370, True)),
          ('AmbientColor', collection('AmbientColor', -1700, 490, True)),
          ('ToonParams', collection('ToonParams', -1700, 610, False))]
custom = node(unreal.MaterialExpressionCustom, -800, 100)
custom.set_editor_property('code', CODE)
custom.set_editor_property('description', 'UKing Toon Lite')
custom.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
cis = []
for n, _ in inputs:
    ci = unreal.CustomInput()
    ci.set_editor_property('input_name', n)
    cis.append(ci)
custom.set_editor_property('inputs', cis)
for n, e in inputs:
    MEL.connect_material_expressions(e, '', custom, n)
MEL.connect_material_property(screen_marker(custom, -550, 100), '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
black = node(unreal.MaterialExpressionConstant, -500, -150)
black.set_editor_property('r', 0.0)
MEL.connect_material_property(black, '', unreal.MaterialProperty.MP_BASE_COLOR)
cov = node(unreal.MaterialExpressionTextureSampleParameter2D, -800, 400)
cov.set_editor_property('parameter_name', 'Coverage')
cov.set_editor_property('texture', unreal.load_asset('/Game/UKing/Materials/T_UKing_White1'))
cov.set_editor_property('sampler_type', ST.SAMPLERTYPE_ALPHA)
MEL.connect_material_expressions(uv, '', cov, 'UVs')
MEL.connect_material_property(cov, 'R', unreal.MaterialProperty.MP_OPACITY_MASK)
MEL.recompile_material(mat)
result['saved'] = EAL.save_loaded_asset(mat)
result['textures'] = [str(n) for n in MEL.get_texture_parameter_names(mat)]

# the material instances: on the lite material, their textures kept (each one checked against the sampler it lands on)
moved = {}
for p in MICS:
    mic = unreal.load_asset(p)
    before = mic.get_editor_property('parent').get_path_name()
    if not before.startswith(TOON + '.') and not before.startswith(full + '.'):
        moved[p.rsplit('/', 1)[-1]] = 'left alone: its parent is ' + before
        continue
    MEL.set_material_instance_parent(mic, mat)
    MEL.update_material_instance(mic)
    tex = {}
    for n in ('_a0', '_n0', 'Coverage'):
        t = MEL.get_material_instance_texture_parameter_value(mic, n)
        tex[n] = '%s (%s)' % (t.get_name(), str(t.get_editor_property('compression_settings')).split('.')[-1].split(':')[0]) if t else None
    moved[p.rsplit('/', 1)[-1]] = dict(saved=EAL.save_loaded_asset(mic), textures=tex)
result['instances'] = moved
