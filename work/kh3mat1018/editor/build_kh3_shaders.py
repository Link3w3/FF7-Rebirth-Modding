"""(Editor link) Builds rebuilt KH3 materials in the End project from kh3_specs.json (kh3matspec.py).

A lit KH3 material becomes an End material with KH3's blend mode, shading model and two-sidedness, its normal in
world space (KH3 writes a world normal), and two Custom nodes running KH3's own compiled shader code:
  KH3 Main   -> BaseColor (return), Metallic, Specular, Roughness, Emissive, Subsurface colour, Opacity, Opacity Mask
  KH3 Normal -> Normal (world space)
fed by parameters with KH3's names and defaults, KH3's textures, the parameter collections, and the engine inputs.
A material instance gets its parent and KH3's values. FIRST/COUNT pick the specs this run builds."""
import json
import unreal

SPECS = r'C:\FF7R2UProj\Saved\ModExtract\kh3shader\kh3_specs.json'
FIRST, COUNT = __FIRST__, __COUNT__
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
P = unreal.MaterialProperty
result = {}
QUIET = unreal.PropertyAccessChangeNotifyMode.NEVER

DEFAULT_COLOR = '/Engine/EngineResources/DefaultTexture'
DEFAULT_NORMAL = '/Engine/EngineMaterials/DefaultNormal'
OUTPUTS = (('KHMetallic', 'CMOT_FLOAT1'), ('KHSpecular', 'CMOT_FLOAT1'), ('KHRoughness', 'CMOT_FLOAT1'),
           ('KHEmissive', 'CMOT_FLOAT3'), ('KHSubsurface', 'CMOT_FLOAT3'), ('KHOpacity', 'CMOT_FLOAT1'),
           ('KHMask', 'CMOT_FLOAT1'))


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
    return unreal.load_asset(path.split('.', 1)[0])


def sampler_type(t):
    S = unreal.MaterialSamplerType
    C = unreal.TextureCompressionSettings
    comp = t.get_editor_property('compression_settings')
    srgb = t.get_editor_property('srgb')
    if comp == C.TC_NORMALMAP:
        return S.SAMPLERTYPE_NORMAL
    if comp == C.TC_GRAYSCALE:
        return S.SAMPLERTYPE_GRAYSCALE if srgb else S.SAMPLERTYPE_LINEAR_GRAYSCALE
    if comp == C.TC_ALPHA:
        return S.SAMPLERTYPE_ALPHA
    if comp == C.TC_MASKS:
        return S.SAMPLERTYPE_MASKS
    return S.SAMPLERTYPE_COLOR if srgb else S.SAMPLERTYPE_LINEAR_COLOR


def make_custom(mat, code, inputs, out_type, outputs, desc, x, y):
    c = MEL.create_material_expression(mat, unreal.MaterialExpressionCustom, x, y)
    c.set_editor_property('code', code, QUIET)
    c.set_editor_property('output_type', getattr(unreal.CustomMaterialOutputType, out_type), QUIET)
    c.set_editor_property('description', desc, QUIET)
    ins = []
    for i in inputs:
        ci = unreal.CustomInput()
        ci.set_editor_property('input_name', i['name'], QUIET)
        ins.append(ci)
    c.set_editor_property('inputs', ins, QUIET)
    if outputs:
        outs = []
        for n, t in outputs:
            co = unreal.CustomOutput()
            co.set_editor_property('output_name', n, QUIET)
            co.set_editor_property('output_type', getattr(unreal.CustomMaterialOutputType, t), QUIET)
            outs.append(co)
        # (announced: the node makes its output pins from these only when told; the material it recompiles then
        #  is still a bare post process material, so that costs little)
        c.set_editor_property('additional_outputs', outs)
    return c


class Sources(object):
    """One expression per input name, shared by the Custom nodes."""

    def __init__(self, mat):
        self.mat, self.made, self.y, self.notes = mat, {}, -1600, []

    def get(self, i):
        key = i['name']
        if key in self.made:
            return self.made[key]
        mat, k, x, y = self.mat, i['kind'], -1700, self.y
        self.y += 110
        out = ''
        if k == 'texcoord':
            src = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, x, y)
            src.set_editor_property('coordinate_index', int(i['index']), QUIET)
        elif k == 'vertexcolor':
            src = MEL.create_material_expression(mat, unreal.MaterialExpressionVertexColor, x, y)
        elif k == 'eyeadaptation':
            src = MEL.create_material_expression(mat, unreal.MaterialExpressionEyeAdaptation, x, y)
        elif k == 'worldpos_noofs':
            src = MEL.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, x, y)
            src.set_editor_property('world_position_shader_offset',
                                    unreal.WorldPositionIncludedOffsets.WPT_CAMERA_RELATIVE_NO_OFFSETS, QUIET)
        elif k == 'scalar':
            src = MEL.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, x, y)
            src.set_editor_property('parameter_name', i['param'], QUIET)
            src.set_editor_property('default_value', float(i['default']), QUIET)
        elif k == 'vector':
            p = MEL.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, x - 300, y)
            p.set_editor_property('parameter_name', i['param'], QUIET)
            d = i['default']
            p.set_editor_property('default_value', unreal.LinearColor(d[0], d[1], d[2], d[3]), QUIET)
            src = MEL.create_material_expression(mat, unreal.MaterialExpressionAppendVector, x, y)
            MEL.connect_material_expressions(p, '', src, 'A')
            MEL.connect_material_expressions(p, 'A', src, 'B')
        elif k in ('textureparam', 'texture'):
            cls = unreal.MaterialExpressionTextureObjectParameter if k == 'textureparam' else \
                unreal.MaterialExpressionTextureObject
            src = MEL.create_material_expression(mat, cls, x, y)
            if k == 'textureparam':
                src.set_editor_property('parameter_name', i['param'], QUIET)
            t = tex(i.get('texture'))
            if t is None:
                guess = DEFAULT_NORMAL if 'normal' in (i.get('param') or '').lower() else DEFAULT_COLOR
                if i.get('texture'):
                    self.notes.append('%s: %s not in the project, %s instead' % (key, i['texture'], guess))
                t = unreal.load_asset(guess)
            src.set_editor_property('texture', t, QUIET)
            src.set_editor_property('sampler_type', sampler_type(t), QUIET)
        elif k == 'collection':
            src = MEL.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, x, y)
            src.set_editor_property('collection', unreal.load_asset(i['collection'].split('.', 1)[0]), QUIET)
            # (its parameter id is looked up from the name only when the change is announced)
            src.set_editor_property('parameter_name', i['param'])
            if i.get('comps', 1) == 1:
                m = MEL.create_material_expression(mat, unreal.MaterialExpressionComponentMask, x + 200, y)
                m.set_editor_property('r', True, QUIET)
                MEL.connect_material_expressions(src, '', m, '')
                src = m
        else:
            raise RuntimeError('input kind %s' % k)
        self.made[key] = (src, out)
        return src, out


def wire(srcs, custom, inputs):
    for i in inputs:
        src, out = srcs.get(i)
        if not MEL.connect_material_expressions(src, out, custom, i['name']):
            raise RuntimeError('could not connect %s' % i['name'])


import time as _time
TIMES = {}


def build_material(s):
    t0 = _time.time()
    mat, new = load_or_create(s['path'], unreal.Material, unreal.MaterialFactoryNew())
    if not new:
        MEL.delete_all_material_expressions(mat)
    # While the graph is made the material is a post process material with nothing connected: the few changes that
    # have to be announced (Custom node outputs, collection parameter names) each recompile the material, and that
    # costs a couple of shaders this way instead of a full surface material's set.
    mat.set_editor_property('material_domain', unreal.MaterialDomain.MD_POST_PROCESS, QUIET)
    t_props = []
    B = unreal.BlendMode
    M = unreal.MaterialShadingModel
    blend = {'BLEND_Translucent': B.BLEND_TRANSLUCENT, 'BLEND_Additive': B.BLEND_ADDITIVE, 'BLEND_Opaque': B.BLEND_OPAQUE,
             'BLEND_Masked': B.BLEND_MASKED}.get(s['blend'], B.BLEND_OPAQUE)
    shading = {'MSM_Subsurface': M.MSM_SUBSURFACE, 'MSM_SubsurfaceProfile': M.MSM_SUBSURFACE_PROFILE,
               'MSM_DefaultLit': M.MSM_DEFAULT_LIT, 'MSM_Unlit': M.MSM_UNLIT,
               'MSM_PreintegratedSkin': M.MSM_PREINTEGRATED_SKIN, 'MSM_ClearCoat': M.MSM_CLEAR_COAT,
               'MSM_TwoSidedFoliage': M.MSM_TWO_SIDED_FOLIAGE, 'MSM_Hair': M.MSM_HAIR, 'MSM_Cloth': M.MSM_CLOTH,
               'MSM_Eye': M.MSM_EYE}.get(s['shading'], M.MSM_DEFAULT_LIT)
    t_props = [('blend_mode', blend), ('shading_model', shading), ('two_sided', bool(s['two_sided'])),
               ('tangent_space_normal', False), ('opacity_mask_clip_value', 0.5)]
    for flag, on in (('used_with_skeletal_mesh', True), ('used_with_morph_targets', s.get('morph')),
                     ('used_with_clothing', s.get('cloth'))):
        if on:
            t_props.append((flag, True))

    def surface(extra=()):
        mat.set_editor_property('material_domain', unreal.MaterialDomain.MD_SURFACE, QUIET)
        for k, v in list(t_props) + list(extra):
            mat.set_editor_property(k, v, QUIET)

    srcs = Sources(mat)
    name = s['path'].rsplit('.', 1)[-1]
    if s.get('translucent'):
        # KH3 draws these unlit: its translucent base pass outputs the material's emissive and opacity only
        main = make_custom(mat, s['main']['code'], s['main']['inputs'], 'CMOT_FLOAT3',
                           (('KHOpacity', 'CMOT_FLOAT1'), ('KHMask', 'CMOT_FLOAT1')), 'KH3 %s main' % name, -600, 0)
        wire(srcs, main, s['main']['inputs'])
        bad = [o for o, prop in (('return', P.MP_EMISSIVE_COLOR), ('KHOpacity', P.MP_OPACITY))
               if not MEL.connect_material_property(main, o, prop)]
        if bad:
            raise RuntimeError('could not connect outputs %s' % bad)
        surface((('shading_model', M.MSM_UNLIT),))
        t1 = _time.time()
        MEL.recompile_material(mat)
        t2 = _time.time()
        ok = unreal.EditorAssetLibrary.save_loaded_asset(mat, False)
        TIMES[name] = '%.1f graph, %.1f recompile, %.1f save' % (t1 - t0, t2 - t1, _time.time() - t2)
        return ('built' if ok else 'built, not saved') + ('; ' + '; '.join(srcs.notes) if srcs.notes else '')
    main = make_custom(mat, s['main']['code'], s['main']['inputs'], 'CMOT_FLOAT3', OUTPUTS, 'KH3 %s main' % name,
                       -600, 0)
    wire(srcs, main, s['main']['inputs'])
    normal = make_custom(mat, s['normal']['code'], s['normal']['inputs'], 'CMOT_FLOAT3', None,
                         'KH3 %s normal' % name, -600, 400)
    wire(srcs, normal, s['normal']['inputs'])
    links = [('return', P.MP_BASE_COLOR), ('KHMetallic', P.MP_METALLIC), ('KHSpecular', P.MP_SPECULAR),
             ('KHRoughness', P.MP_ROUGHNESS), ('KHEmissive', P.MP_EMISSIVE_COLOR)]
    if blend == B.BLEND_MASKED:
        links.append(('KHMask', P.MP_OPACITY_MASK))
    if shading in (M.MSM_SUBSURFACE, M.MSM_PREINTEGRATED_SKIN, M.MSM_TWO_SIDED_FOLIAGE, M.MSM_CLOTH):
        links += [('KHSubsurface', P.MP_SUBSURFACE_COLOR), ('KHOpacity', P.MP_OPACITY)]
    elif shading == M.MSM_SUBSURFACE_PROFILE:
        links.append(('KHOpacity', P.MP_OPACITY))
    bad = []
    for out, prop in links:
        if not MEL.connect_material_property(main, out, prop):
            bad.append(out)
    if not MEL.connect_material_property(normal, '', P.MP_NORMAL):
        bad.append('normal')
    if bad:
        raise RuntimeError('could not connect outputs %s' % bad)
    surface()
    t1 = _time.time()
    MEL.recompile_material(mat)
    t2 = _time.time()
    ok = unreal.EditorAssetLibrary.save_loaded_asset(mat, False)
    TIMES[name] = '%.1f graph, %.1f recompile, %.1f save' % (t1 - t0, t2 - t1, _time.time() - t2)
    return ('built' if ok else 'built, not saved') + ('; ' + '; '.join(srcs.notes) if srcs.notes else '')


def build_instance(s):
    mi, new = load_or_create(s['path'], unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    parent = unreal.load_asset(s['parent'].split('.', 1)[0]) if s.get('parent') else None
    if parent is None:
        raise RuntimeError('parent %s not in the project' % s.get('parent'))
    MEL.set_material_instance_parent(mi, parent)
    # (this engine's Set*ParameterValue always answers False, so values are read back instead)
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
    ov = s.get('overrides') or {}
    if ov:
        bpo = mi.get_editor_property('base_property_overrides')
        B = unreal.BlendMode
        if 'BlendMode' in ov:
            bpo.set_editor_property('override_blend_mode', True, QUIET)
            bpo.set_editor_property('blend_mode', {'BLEND_Translucent': B.BLEND_TRANSLUCENT,
                                                   'BLEND_Additive': B.BLEND_ADDITIVE, 'BLEND_Masked': B.BLEND_MASKED,
                                                   'BLEND_Opaque': B.BLEND_OPAQUE}.get(ov['BlendMode'], B.BLEND_MASKED), QUIET)
        if 'TwoSided' in ov:
            bpo.set_editor_property('override_two_sided', True, QUIET)
            bpo.set_editor_property('two_sided', bool(ov['TwoSided']), QUIET)
        mi.set_editor_property('base_property_overrides', bpo, QUIET)
    MEL.update_material_instance(mi)
    ok = unreal.EditorAssetLibrary.save_loaded_asset(mi, False)
    return ('built' if ok else 'built, not saved') + (' (textures not set: %s)' % ', '.join(missing) if missing else '')


unreal.log('KH3SHADERS BEGIN %d %d' % (FIRST, COUNT))
specs = json.load(open(SPECS))['specs'][FIRST:FIRST + COUNT]
for s in specs:
    name = s['path'].rsplit('.', 1)[-1]
    try:
        result[name] = build_material(s) if s['cls'] == 'Material' else build_instance(s)
    except Exception as e:
        result[name] = 'ERROR %s' % str(e)[:400]
unreal.log('KH3SHADERS END %d %d' % (FIRST, COUNT))
if TIMES:
    result['_times'] = TIMES
