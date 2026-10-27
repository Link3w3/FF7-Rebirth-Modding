"""(Editor link) Builds KH3 materials and material instances in the End project from specs.json (build_specs.py):
a material is unlit, KH3's blend mode / two-sidedness / usage, and one Custom node running KH3's own pixel shader
code with the material's parameters, textures and engine inputs wired in; an instance gets KH3's parent, values and
overrides. FIRST/COUNT pick the specs this run builds (filled in by the caller)."""
import json
import os
import unreal

SPECS = r'C:\FF7R2UProj\Saved\ModExtract\kh3fx_limit\specs.json'
FIRST, COUNT = __FIRST__, __COUNT__
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
result = {}


def load_or_create(path, cls, factory):
    pkg, name = path.split('.', 1)[0].rsplit('/', 1)
    full = '%s/%s' % (pkg, name)
    if unreal.EditorAssetLibrary.does_asset_exist(full):
        a = unreal.load_asset(full)
        if a and a.get_class() == cls.static_class():
            return a, False
        raise RuntimeError('%s exists as %s' % (full, a.get_class().get_name() if a else None))
    a = TOOLS.create_asset(name, pkg, cls, factory)
    if a is None:
        raise RuntimeError('could not create %s' % full)
    return a, True


def tex(path):
    if not path:
        return None
    t = unreal.load_asset(path.split('.', 1)[0])
    if t is None:
        raise RuntimeError('texture %s not in the project' % path)
    return t


def build_material(s):
    mat, new = load_or_create(s['path'], unreal.Material, unreal.MaterialFactoryNew())
    if not new:
        MEL.delete_all_material_expressions(mat)
    B = unreal.BlendMode
    mat.set_editor_property('blend_mode', {'BLEND_Translucent': B.BLEND_TRANSLUCENT, 'BLEND_Additive': B.BLEND_ADDITIVE,
                                           'BLEND_Opaque': B.BLEND_OPAQUE, 'BLEND_Masked': B.BLEND_MASKED}.get(s['blend'], B.BLEND_TRANSLUCENT))
    mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', bool(s['two_sided']))
    for flag in ('used_with_particle_sprites', 'used_with_mesh_particles', 'used_with_beam_trails',
                 'used_with_niagara_sprites', 'used_with_niagara_ribbons', 'used_with_niagara_mesh_particles'):
        try:
            mat.set_editor_property(flag, True)
        except Exception:
            pass
    custom = MEL.create_material_expression(mat, unreal.MaterialExpressionCustom, -500, 0)
    custom.set_editor_property('code', s['code'])
    custom.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    custom.set_editor_property('description', 'KH3 ' + s['path'].rsplit('.', 1)[-1])
    ins = []
    for i in s['inputs']:
        ci = unreal.CustomInput()
        ci.set_editor_property('input_name', i['name'])
        ins.append(ci)
    custom.set_editor_property('inputs', ins)
    y = -600
    for i in s['inputs']:
        k = i['kind']
        x = -1100
        if k == 'texcoord':
            n = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, x, y)
            n.set_editor_property('coordinate_index', int(i['index']))
            src, out = n, ''
        elif k in ('vertexcolor', 'particlecolor', 'dynamicparameter', 'scenedepth', 'eyeadaptation', 'particletime',
                   'particleposition'):
            cls = {'vertexcolor': unreal.MaterialExpressionVertexColor,
                   'particlecolor': unreal.MaterialExpressionParticleColor,
                   'dynamicparameter': unreal.MaterialExpressionDynamicParameter,
                   'scenedepth': unreal.MaterialExpressionSceneDepth,
                   'eyeadaptation': unreal.MaterialExpressionEyeAdaptation,
                   'particletime': unreal.MaterialExpressionParticleRelativeTime,
                   'particleposition': unreal.MaterialExpressionParticlePositionWS}[k]
            src, out = MEL.create_material_expression(mat, cls, x, y), ''
        elif k == 'scalar':
            src = MEL.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, x, y)
            src.set_editor_property('parameter_name', i['param'])
            src.set_editor_property('default_value', float(i['default']))
            out = ''
        elif k == 'vector':
            p = MEL.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, x - 300, y)
            p.set_editor_property('parameter_name', i['param'])
            d = i['default']
            p.set_editor_property('default_value', unreal.LinearColor(d[0], d[1], d[2], d[3]))
            src = MEL.create_material_expression(mat, unreal.MaterialExpressionAppendVector, x, y)
            MEL.connect_material_expressions(p, '', src, 'A')
            MEL.connect_material_expressions(p, 'A', src, 'B')
            out = ''
        elif k == 'textureparam':
            src = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureObjectParameter, x, y)
            src.set_editor_property('parameter_name', i['param'])
            t = tex(i.get('texture'))
            if t:
                src.set_editor_property('texture', t)
            out = ''
        elif k == 'texture':
            src = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureObject, x, y)
            t = tex(i.get('texture'))
            if t:
                src.set_editor_property('texture', t)
            out = ''
        else:
            raise RuntimeError('input kind %s' % k)
        if not MEL.connect_material_expressions(src, out, custom, i['name']):
            raise RuntimeError('could not connect %s' % i['name'])
        y += 120
    rgb = MEL.create_material_expression(mat, unreal.MaterialExpressionComponentMask, -200, -60)
    for c in ('r', 'g', 'b'):
        rgb.set_editor_property(c, True)
    a = MEL.create_material_expression(mat, unreal.MaterialExpressionComponentMask, -200, 60)
    a.set_editor_property('a', True)
    MEL.connect_material_expressions(custom, '', rgb, '')
    MEL.connect_material_expressions(custom, '', a, '')
    P = unreal.MaterialProperty
    if s.get('distortion'):
        MEL.connect_material_property(rgb, '', P.MP_NORMAL)
        MEL.connect_material_property(a, '', P.MP_REFRACTION)
        zero = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -200, 200)
        MEL.connect_material_property(zero, '', P.MP_EMISSIVE_COLOR)
    else:
        MEL.connect_material_property(rgb, '', P.MP_EMISSIVE_COLOR)
        if s['blend'] == 'BLEND_Masked':
            MEL.connect_material_property(a, '', P.MP_OPACITY_MASK)
        elif s['blend'] != 'BLEND_Opaque':
            MEL.connect_material_property(a, '', P.MP_OPACITY)
    MEL.recompile_material(mat)
    ok = unreal.EditorAssetLibrary.save_loaded_asset(mat, False)
    return 'built' if ok else 'built, not saved'


def build_instance(s):
    mi, new = load_or_create(s['path'], unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    parent = unreal.load_asset(s['parent'].split('.', 1)[0]) if s.get('parent') else None
    if parent is None:
        raise RuntimeError('parent %s not in the project' % s.get('parent'))
    MEL.set_material_instance_parent(mi, parent)
    # (this engine's Set*ParameterValue always answers False, so the values are read back instead)
    missing = []
    for n, v in s['scalars'].items():
        MEL.set_material_instance_scalar_parameter_value(mi, n, float(v))
    for n, v in s['vectors'].items():
        MEL.set_material_instance_vector_parameter_value(mi, n, unreal.LinearColor(v[0], v[1], v[2], v[3]))
    for n, v in s['textures'].items():
        t = tex(v) if v and v.startswith('/Game/') else None
        if t is None:
            missing.append(n)
            continue
        MEL.set_material_instance_texture_parameter_value(mi, n, t)
        got = MEL.get_material_instance_texture_parameter_value(mi, n)
        if got != t and n in [str(x) for x in MEL.get_texture_parameter_names(parent)]:
            missing.append(n)
    ov = s.get('overrides') or {}
    if ov:
        bpo = mi.get_editor_property('base_property_overrides')
        B = unreal.BlendMode
        if 'BlendMode' in ov:
            bpo.set_editor_property('override_blend_mode', True)
            bpo.set_editor_property('blend_mode', {'BLEND_Translucent': B.BLEND_TRANSLUCENT,
                                                   'BLEND_Additive': B.BLEND_ADDITIVE,
                                                   'BLEND_Opaque': B.BLEND_OPAQUE}.get(ov['BlendMode'], B.BLEND_TRANSLUCENT))
        if 'TwoSided' in ov:
            bpo.set_editor_property('override_two_sided', True)
            bpo.set_editor_property('two_sided', bool(ov['TwoSided']))
        if 'ShadingModel' in ov:
            bpo.set_editor_property('override_shading_model', True)
            bpo.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        mi.set_editor_property('base_property_overrides', bpo)
    MEL.update_material_instance(mi)
    ok = unreal.EditorAssetLibrary.save_loaded_asset(mi, False)
    return ('built' if ok else 'built, not saved') + (' (textures not set: %s)' % ', '.join(missing) if missing else '')


specs = json.load(open(SPECS))['specs'][FIRST:FIRST + COUNT]
for s in specs:
    name = s['path'].rsplit('.', 1)[-1]
    try:
        result[name] = build_material(s) if s['cls'] == 'Material' else build_instance(s)
    except Exception as e:
        result[name] = 'ERROR %s' % str(e)[:300]
