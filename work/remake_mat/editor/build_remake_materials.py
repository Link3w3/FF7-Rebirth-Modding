# FF7 Remake's material masters for the End editor (Remake mats 5/5): builds, at Remake's own paths and names,
#   /Game/GameContents/Renderer/Texture/<colour>          the masters' default textures (4x4 single colours)
#   /Game/GameContents/Renderer/MaterialFunction/<name>  the 22 material functions (and LocalPosition, a helper)
#   /Game/GameContents/Renderer/Material/EndMaterial_*   the 21 masters
# from remake_editor_spec.json (remake_editor_spec.py: the graphs checked against the game's own shaders), then compiles
# each master and every one of the game's static permutations of it (transient instances) and lists any compile errors.
# What the 4.26 editor has no counterpart for is kept in the graph and labelled: the game's vertex transforms and context
# vectors on boxed reroutes (not connected), its engine values (blue noise, baking, ...) as the editor's nearest.
# Run in the End editor: run_build_remake_materials.cmd starts it (UE4Editor.exe -ExecutePythonScript), editor closed.
# Results: Saved\RemakeMaterials\build_result.json and permutations.json.
import json
import math
import os
import re
import struct
import tempfile
import time
import traceback
import zlib
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = json.load(open(os.path.join(HERE, 'remake_editor_spec.json')))
ROOT = SPEC['root']
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RemakeMaterials')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, os.environ.get('REMAKEMATERIALS_RESULT', 'build_result.json'))
ONLY = [x for x in os.environ.get('REMAKEMATERIALS_ONLY', '').split(',') if x]
# (a few masters again: the default textures and material functions a full build made, reused as they are)
REUSE = os.environ.get('REMAKEMATERIALS_REUSE', '0') == '1'
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
LIB = getattr(unreal, 'RebirthMaterialDiagnosticsLibrary', None)
results = {'steps': [], 'warnings': [], 'functions': {}, 'materials': {}}


def save_results():
    json.dump(results, open(RESULT, 'w'), indent=1)


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('REMAKEMATERIALS %s: %s' % (key, str(value)[:2000]))
    save_results()


def warn(text):
    results['warnings'].append(text)
    unreal.log_warning('REMAKEMATERIALS ' + text)
    save_results()


def enum_value(cls_name, name):
    """a UE enum value from its C++ name (SAMPLERTYPE_LinearColor, MSM_DefaultLit, ...), Python's spelling or not"""
    cls = getattr(unreal, cls_name)
    name = name.split('::')[-1]
    for cand in (name, re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', name).upper(), name.upper()):
        if hasattr(cls, cand):
            return getattr(cls, cand)
    flat = name.replace('_', '').upper()
    for k in dir(cls):
        if k.replace('_', '').upper() == flat:
            return getattr(cls, k)
    raise KeyError('%s.%s' % (cls_name, name))


def setp(obj, prop, value, quiet=False):
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception as ex:
        if not quiet:
            warn('could not set %s.%s: %s' % (obj.get_name(), prop, ex))
        return False


# ---- default textures --------------------------------------------------------------------------------------------
def png(w, h, rgba):
    raw = b''.join(b'\x00' + bytes(rgba) * w for _ in range(h))

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def png_rgba(w, h, pixels):
    raw = b''.join(b'\x00' + b''.join(bytes(p) for p in pixels[y * w:(y + 1) * w]) for y in range(h))

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def dds_cube(size, rgba):
    """an uncompressed (B8G8R8A8) cube map, all six faces one colour"""
    r, g, b, a = rgba
    header = struct.pack('<4sIIIIIII44xIIIIIIIIIIIII', b'DDS ', 124, 0x1 | 0x2 | 0x4 | 0x8 | 0x1000, size, size, size * 4, 0, 1,
                         32, 0x40 | 0x1, 0, 32, 0x00ff0000, 0x0000ff00, 0x000000ff, 0xff000000,
                         0x1000 | 0x8, 0x200 | 0xfc00, 0, 0, 0)
    assert len(header) == 128
    face = bytes([b, g, r, a]) * (size * size)
    return header + face * 6


def import_file(path, folder, name):
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', path)
    task.set_editor_property('destination_path', folder)
    task.set_editor_property('destination_name', name)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('automated', True)
    task.set_editor_property('save', False)
    AT.import_asset_tasks([task])
    return unreal.load_asset('%s/%s.%s' % (folder, name, name))


TEXTURES = {}


def build_textures():
    folder = ROOT + '/Texture'
    tmp = tempfile.mkdtemp(prefix='remake_tex_')
    made = []
    for t in SPEC['textures']:
        rgba = t['rgba']
        if t['compression'] == 'TC_Alpha':
            rgba = [rgba[0]] * 4   # (BC4: one channel, the colour's red; the same in every channel)
        if t['kind'] == 'cube':
            path = os.path.join(tmp, t['name'] + '.dds')
            open(path, 'wb').write(dds_cube(4, rgba))
        else:
            path = os.path.join(tmp, t['name'] + '.png')
            open(path, 'wb').write(png(4, 4, rgba))
        tex = import_file(path, folder, t['name'])
        if tex is None:
            warn('texture %s did not import' % t['name'])
            continue
        setp(tex, 'srgb', t['srgb'])
        try:
            setp(tex, 'compression_settings', enum_value('TextureCompressionSettings', t['compression']))
        except KeyError:
            warn('no compression setting %s for %s' % (t['compression'], t['name']))
        EAL.save_loaded_asset(tex)
        TEXTURES[t['name']] = tex
        made.append(t['name'])
    log('textures', '%d made' % len(made))
    # the editor's stand-in for the game's 3D noise textures (the View's volume noise, the tilt noise, the blue noise
    # volume): a 16x16x16 white-noise volume, from a 2D image of its slices
    name = 'RemakeEditorVolumeNoise'
    try:
        import random
        rnd = random.Random(1234)
        w = h = 64
        pixels = [[rnd.randrange(256), rnd.randrange(256), rnd.randrange(256), rnd.randrange(256)] for _ in range(w * h)]
        path = os.path.join(tmp, name + '_Slices.png')
        open(path, 'wb').write(png_rgba(w, h, pixels))
        src = import_file(path, folder, name + '_Slices')
        setp(src, 'srgb', False)
        setp(src, 'compression_settings', enum_value('TextureCompressionSettings', 'TC_VectorDisplacementmap'), quiet=True)
        EAL.save_loaded_asset(src)
        vt = unreal.load_asset('%s/%s.%s' % (folder, name, name)) if EAL.does_asset_exist('%s/%s' % (folder, name)) else None
        if vt is None:
            vt = AT.create_asset(name, folder, unreal.VolumeTexture, unreal.VolumeTextureFactory())
        setp(vt, 'source2d_tile_size_x', 16)
        setp(vt, 'source2d_tile_size_y', 16)
        setp(vt, 'source2d_texture', src)
        setp(vt, 'srgb', False)
        EAL.save_loaded_asset(vt)
        TEXTURES[name] = vt
        log('volume_noise', 'made %s/%s' % (folder, name))
    except Exception as ex:
        warn('the volume noise texture could not be made (%s): using the engine\'s blue noise volume' % ex)
        TEXTURES[name] = unreal.load_asset('/Engine/EngineResources/SpatiotemporalBlueNoiseVolumeSource.SpatiotemporalBlueNoiseVolumeSource')


def reuse_existing():
    """the default textures and material functions a full build made, loaded instead of rebuilt"""
    for t in SPEC['textures']:
        path = '%s/Texture/%s' % (ROOT, t['name'])
        tex = unreal.load_asset(path) if EAL.does_asset_exist(path) else None
        if tex is None:
            raise RuntimeError('no %s: run the full build (run_build_remake_materials.cmd) first' % path)
        TEXTURES[t['name']] = tex
    path = '%s/Texture/RemakeEditorVolumeNoise' % ROOT
    TEXTURES['RemakeEditorVolumeNoise'] = unreal.load_asset(path) if EAL.does_asset_exist(path) else unreal.load_asset(
        '/Engine/EngineResources/SpatiotemporalBlueNoiseVolumeSource.SpatiotemporalBlueNoiseVolumeSource')
    for f in SPEC['functions']:
        mf = unreal.load_asset(f['path']) if EAL.does_asset_exist(f['path']) else None
        if mf is None:
            raise RuntimeError('no %s: run the full build (run_build_remake_materials.cmd) first' % f['path'])
        FUNCTIONS[f['name']] = mf
        results['functions'][f['name']] = 'reused'
    log('reused', '%d default textures and %d functions as they are' % (len(SPEC['textures']), len(SPEC['functions'])))


# ---- graphs ------------------------------------------------------------------------------------------------------
CMOT = {1: 'CMOT_FLOAT1', 2: 'CMOT_FLOAT2', 3: 'CMOT_FLOAT3', 4: 'CMOT_FLOAT4'}
FIT = {'Scalar': 'FunctionInput_Scalar', 'Vector2': 'FunctionInput_Vector2', 'Vector3': 'FunctionInput_Vector3',
       'Vector4': 'FunctionInput_Vector4', 'Texture2D': 'FunctionInput_Texture2D', 'TextureCube': 'FunctionInput_TextureCube',
       'Texture3D': 'FunctionInput_VolumeTexture'}
FUNCTIONS = {}

# the game's engine values, as the editor's nearest
HOOK_CODE = {
    'BakingMask': ('return View.RenderingReflectionCaptureMask;', 1, 'Remake BakingMask (the editor: rendering a reflection capture)'),
    'BlueNoise': ('float2 P = floor(Parameters.SvPosition.xy);\n'
                  'return frac(sin(float3(dot(P, float2(12.9898, 78.233)), dot(P, float2(39.3468, 11.135)), dot(P, float2(73.156, 52.235)))) * 43758.5453);',
                  3, 'Remake BlueNoise (the editor: a per-pixel hash)'),
    'NearPlane': ('return View.NearPlane;', 1, 'Remake NearPlane'),
    # (the game draws its sand after the base pass, so even an opaque one reads the depth behind it; the editor lets only
    # translucent materials do that: an opaque one sees the scene far behind, no fade)
    'ExtraSceneDepth': ('#if MATERIALBLENDING_ANY_TRANSLUCENT\n'
                        'return CalcSceneDepth(ScreenAlignedPosition(GetScreenPosition(Parameters)));\n'
                        '#else\n'
                        'return 1000000.0;\n'
                        '#endif', 1, 'Remake ExtraSceneDepth (the scene depth behind; far for an opaque material)'),
    'PreSkinnedTangentX': ('return normalize(mul(Parameters.TangentToWorld[0], (float3x3)GetPrimitiveData(Parameters.PrimitiveId).WorldToLocal));',
                           3, 'Remake PreSkinnedTangentX (the editor: the local tangent)'),
    'PreSkinnedTangentZ': ('return float4(normalize(mul(Parameters.TangentToWorld[2], (float3x3)GetPrimitiveData(Parameters.PrimitiveId).WorldToLocal)), 1.0);',
                           4, 'Remake PreSkinnedTangentZ (the editor: the local normal)'),
}


class Graph:
    def __init__(self, owner, is_function):
        self.owner = owner
        self.is_function = is_function
        self.made = {}
        self.out_name = {}
        self.failed = []

    def create(self, cls, x, y):
        uclass = getattr(unreal, 'MaterialExpression' + cls)
        if self.is_function:
            e = MEL.create_material_expression_in_function(self.owner, uclass, x, y)
        else:
            e = MEL.create_material_expression(self.owner, uclass, x, y)
        if e is None:
            raise RuntimeError('could not create %s' % cls)
        return e

    def node(self, n):
        cls, p, x, y = n['cls'], n['props'], n.get('x', 0), n.get('y', 0)
        out = ''
        if cls == 'ExternalHook':
            hook = p['Hook']
            if hook in HOOK_CODE:
                code, size, desc = HOOK_CODE[hook]
                e = self.create('Custom', x, y)
                setp(e, 'code', code)
                setp(e, 'output_type', enum_value('CustomMaterialOutputType', CMOT[size]))
                setp(e, 'description', desc)
                setp(e, 'inputs', [])
            elif hook == 'ConditionalEmissive':
                e = self.create('Constant', x, y)
                setp(e, 'r', 1.0)
                setp(e, 'desc', 'Remake ConditionalEmissive (the editor: 1)')
            elif hook == 'PixelDepth':
                e = self.create('PixelDepth', x, y)
            elif hook == 'ViewportUV':
                e = self.create('ScreenPosition', x, y)
                out = 'ViewportUV'
            elif p.get('Type') == 'Texture3D':
                e = self.create('TextureObject', x, y)
                setp(e, 'texture', TEXTURES.get('RemakeEditorVolumeNoise'))
                setp(e, 'sampler_type', enum_value('MaterialSamplerType', 'SAMPLERTYPE_LinearColor'))
                setp(e, 'desc', 'Remake %s (the editor: a white-noise volume)' % hook)
            else:
                raise RuntimeError('no editor value for the hook %s' % hook)
            return e, out
        e = self.create(cls, x, y)
        for k, v in p.items():
            self.prop(e, cls, k, v)
        return e, out

    def prop(self, e, cls, k, v):
        if k in ('Cube',):
            return
        if cls == 'Custom':
            if k == 'Code':
                setp(e, 'code', v)
            elif k == 'InputNames':
                ins = []
                for name in v:
                    ci = unreal.CustomInput()
                    ci.set_editor_property('input_name', name)
                    ins.append(ci)
                setp(e, 'inputs', ins)
            elif k == 'OutputType':
                setp(e, 'output_type', enum_value('CustomMaterialOutputType', CMOT[int(v)]))
            elif k == 'Description':
                setp(e, 'description', v)
            elif k == 'AdditionalOutputs':
                outs = []
                for name, size in v:
                    co = unreal.CustomOutput()
                    co.set_editor_property('output_name', name)
                    co.set_editor_property('output_type', enum_value('CustomMaterialOutputType', CMOT[int(size)]))
                    outs.append(co)
                setp(e, 'additional_outputs', outs)
            return
        if k == 'Function':
            fn = FUNCTIONS.get(v)
            if fn is None:
                raise RuntimeError('the function %s is not built' % v)
            setp(e, 'material_function', fn)
            return
        if k in ('R', 'G', 'B', 'A') and cls == 'ComponentMask':
            setp(e, k.lower(), bool(v))
            return
        if k in ('R', 'G') and cls in ('Constant', 'Constant2Vector'):
            setp(e, k.lower(), float(v))
            return
        if k == 'Constant':
            c = list(v) + [0.0] * (4 - len(v))
            setp(e, 'constant', unreal.LinearColor(c[0], c[1], c[2], c[3]))
            return
        if k == 'DefaultValue':
            if cls == 'VectorParameter':
                c = list(v) + [0.0] * (4 - len(v))
                setp(e, 'default_value', unreal.LinearColor(c[0], c[1], c[2], c[3]))
            elif cls == 'StaticSwitchParameter':
                setp(e, 'default_value', bool(v))
            else:
                setp(e, 'default_value', float(v))
            return
        if k == 'ParameterName':
            setp(e, 'parameter_name', v)
            return
        if k == 'Group':
            if v:
                setp(e, 'group', v)
            return
        if k == 'Texture':
            if v is None:
                return
            tex = TEXTURES.get(v)
            if tex is None:
                warn('no default texture %s' % v)
                return
            setp(e, 'texture', tex)
            return
        if k == 'SamplerType':
            setp(e, 'sampler_type', enum_value('MaterialSamplerType', 'SAMPLERTYPE_' + v.split('SAMPLERTYPE_')[-1]))
            return
        if k == 'SamplerSource':
            setp(e, 'sampler_source', enum_value('SamplerSourceMode', v))
            return
        if k == 'MipValueMode':
            setp(e, 'mip_value_mode', enum_value('TextureMipValueMode', v))
            return
        if k == 'ConstMipValue':
            setp(e, 'const_mip_value', int(v))
            return
        if k == 'CoordinateIndex':
            setp(e, 'coordinate_index', int(v))
            return
        if k in ('ConstA', 'ConstB'):
            setp(e, 'const_' + k[-1].lower(), float(v))
            return
        if k == 'TransformSourceType':
            setp(e, 'transform_source_type', enum_value('MaterialVectorCoordTransformSource', v))
            return
        if k == 'TransformType':
            setp(e, 'transform_type', enum_value('MaterialVectorCoordTransform', v))
            return
        if k == 'Property' and cls == 'TextureProperty':
            # (4.18's TMTP_ is 4.26's TMTM_; the texture size is the default)
            v = v.replace('TMTP_', 'TMTM_')
            if v != 'TMTM_TextureSize':
                setp(e, 'property', enum_value('MaterialExposedTextureProperty', v))
            return
        if k == 'ParamNames':
            setp(e, 'param_names', list(v))
            return
        if cls == 'FunctionInput':
            if k == 'InputName':
                setp(e, 'input_name', v)
            elif k == 'InputType':
                setp(e, 'input_type', enum_value('FunctionInputType', FIT[v]))
            elif k == 'SortPriority':
                setp(e, 'sort_priority', int(v))
            elif k == 'PreviewValue' and v is not None:
                c = list(v) + [0.0] * (4 - len(v))
                setp(e, 'preview_value', unreal.Vector4(c[0], c[1], c[2], c[3]))
                setp(e, 'use_preview_value_as_default', True)
            return
        if cls == 'FunctionOutput':
            if k == 'OutputName':
                setp(e, 'output_name', v)
            elif k == 'SortPriority':
                setp(e, 'sort_priority', int(v))
            return
        warn('%s: property %s=%r not set' % (cls, k, v))

    def build(self, nodes):
        # the function calls' functions first (their pins come with them), then every node, then the links
        self.skipped = []
        for n in nodes:
            if n.get('optional') and not hasattr(unreal, 'MaterialExpression' + n['cls']):
                # (an expression from a plugin this editor has not loaded: left out, with what feeds it)
                self.skipped.append(n['cls'])
                continue
            e, out = self.node(n)
            self.made[n['id']] = e
            self.out_name[n['id']] = out
        if self.skipped:
            warn('%s: no %s in this editor (its plugin is not loaded): left out' % (self.owner.get_name(), ', '.join(self.skipped)))
        for n in nodes:
            if n['id'] not in self.made:
                continue
            to = self.made[n['id']]
            for inp, (src, out) in n['inputs'].items():
                fr = self.made[src]
                name = self.out_name.get(src) if out == '' and self.out_name.get(src) else out
                if not MEL.connect_material_expressions(fr, name, to, inp):
                    self.failed.append('%s[%s] -> %s.%s' % (fr.get_name(), name, n['cls'], inp))
        if self.failed:
            warn('%s: %d links could not be made, e.g. %s' % (self.owner.get_name(), len(self.failed), '; '.join(self.failed[:6])))


def asset_for(path, cls, factory):
    folder, name = path.rsplit('/', 1)
    if EAL.does_asset_exist(path):
        a = unreal.load_asset(path)
        if a is not None and isinstance(a, cls):
            return a, False
        raise RuntimeError('%s exists and is not a %s' % (path, cls.__name__))
    a = AT.create_asset(name, folder, cls, factory)
    if a is None:
        raise RuntimeError('could not create ' + path)
    return a, True


def build_function(f):
    mf, new = asset_for(f['path'], unreal.MaterialFunction, unreal.MaterialFunctionFactoryNew())
    if not new:
        MEL.delete_all_material_expressions_in_function(mf)
    setp(mf, 'description', f['description'], quiet=True)
    setp(mf, 'expose_to_library', True, quiet=True)
    Graph(mf, True).build(f['nodes'])
    MEL.update_material_function(mf)
    EAL.save_loaded_asset(mf)
    FUNCTIONS[f['name']] = mf
    results['functions'][f['name']] = 'built' if new else 'rebuilt'


def material_settings(m, spec):
    p = spec['props']
    shading = p.get('ShadingModel', 'MSM_DefaultLit')
    setp(m, 'shading_model', enum_value('MaterialShadingModel', shading))
    blend = p.get('BlendMode')
    if not blend:
        blend = 'BLEND_Masked' if p.get('Masked') else 'BLEND_Opaque'
    setp(m, 'blend_mode', enum_value('BlendMode', blend))
    if 'MaterialDomain' in p:
        setp(m, 'material_domain', enum_value('MaterialDomain', p['MaterialDomain']))
    if 'TranslucencyLightingMode' in p:
        try:
            setp(m, 'translucency_lighting_mode', enum_value('TranslucencyLightingMode', p['TranslucencyLightingMode']))
        except KeyError:
            warn('%s: no translucency lighting mode %s in this engine' % (spec['name'], p['TranslucencyLightingMode']))
    for k, prop in (('bComputeFogPerPixel', 'compute_fog_per_pixel'), ('bEnableSeparateTranslucency', 'enable_separate_translucency'),
                    ('bUseTranslucencyVertexFog', 'use_translucency_vertex_fog'), ('bCanMaskedBeAssumedOpaque', 'can_masked_be_assumed_opaque')):
        if k in p:
            setp(m, prop, bool(p[k]), quiet=True)
    for k, usage in (('bUsedWithSkeletalMesh', 'MATUSAGE_SkeletalMesh'), ('bUsedWithMeshParticles', 'MATUSAGE_MeshParticles'),
                     ('bUsedWithParticleSprites', 'MATUSAGE_ParticleSprites'), ('bUsedWithBeamTrails', 'MATUSAGE_BeamTrails'),
                     ('bUsedWithInstancedStaticMeshes', 'MATUSAGE_InstancedStaticMeshes'), ('bUsedWithStaticLighting', 'MATUSAGE_StaticLighting')):
        if p.get(k):
            try:
                MEL.set_material_usage(m, enum_value('MaterialUsage', usage))
            except Exception as ex:
                warn('%s: usage %s: %s' % (spec['name'], usage, ex))
    if spec['graph_props'].get('tangent_space_normal') is False:
        setp(m, 'tangent_space_normal', False)
    # (the game's Niagara-less editor: meshes in Niagara too, as RM_Surface)
    try:
        MEL.set_material_usage(m, enum_value('MaterialUsage', 'MATUSAGE_NiagaraMeshParticles'))
    except Exception:
        pass


def build_material(spec):
    m, new = asset_for(spec['path'], unreal.Material, unreal.MaterialFactoryNew())
    if not new:
        MEL.delete_all_material_expressions(m)
        if LIB is not None and hasattr(LIB, 'clear_material_comments'):
            LIB.clear_material_comments(m)
    material_settings(m, spec)
    g = Graph(m, False)
    g.build(spec['nodes'])
    for pin, d in sorted(spec['pins'].items()):
        src, out = d['from']
        if src not in g.made:
            warn('%s: the %s pin\'s source was left out' % (spec['name'], pin))
            continue
        fr = g.made[src]
        name = g.out_name.get(src) if out == '' and g.out_name.get(src) else out
        ok = False
        try:
            ok = MEL.connect_material_property(fr, name, enum_value('MaterialProperty', d['property']))
        except KeyError:
            ok = False
        if not ok and LIB is not None:
            ok = LIB.connect_material_property_by_name(fr, name, d['property'])
        if not ok:
            warn('%s: could not connect the %s pin (%s)' % (spec['name'], pin, d['property']))
    # the game's pins this engine has no counterpart for: boxed and labelled
    if LIB is not None and hasattr(LIB, 'add_material_comment'):
        pos = {n['id']: (n.get('x', 0), n.get('y', 0)) for n in spec['nodes']}
        for pin, k in sorted(spec['remake_pins'].items()):
            x, y = pos[k]
            LIB.add_material_comment(m, x - 30, y - 70, 300, 120, 'Remake pin %s (no pin for it in this engine; the game reads it)' % pin)
        # what the editor adds to the game's graph, and why
        for note in spec.get('editor_notes', []):
            if note['node'] in g.made:
                x, y = pos[note['node']]
                LIB.add_material_comment(m, x - 30, y - 90, 380, 160, note['text'])
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    results['materials'][spec['name']] = {'built': 'built' if new else 'rebuilt', 'nodes': len(spec['nodes'])}
    save_results()
    return m


def diagnose(material):
    if LIB is None:
        return {'ok': None, 'errors': ['no RebirthMaterialDiagnosticsLibrary (the Rebirth preview plugin)']}
    try:
        d = json.loads(LIB.get_material_diagnostics(material, True))
    except Exception as ex:
        return {'ok': False, 'errors': [str(ex)]}
    errors, ok = [], True
    for key in ('resources', 'material_resources'):
        for r in d.get(key, []) or []:
            errors += r.get('compile_errors', []) or []
            if r.get('has_shader_map') and not r.get('compiled_successfully', True):
                ok = False
    return {'ok': ok and not errors, 'errors': sorted(set(errors))[:20]}


def test_permutations(built):
    if LIB is None or not hasattr(LIB, 'create_static_permutation'):
        warn('the Rebirth preview plugin has no create_static_permutation: the permutations were not compiled here')
        return
    start = time.time()
    made = []
    for spec, m in built:
        blend_default = spec['props'].get('BlendMode') or ('BLEND_Masked' if spec['props'].get('Masked') else 'BLEND_Opaque')
        for p in spec['permutations']:
            blend = 'BLEND_Masked' if p['masked'] and blend_default == 'BLEND_Opaque' else ''
            made.append((spec['name'], p['name'], LIB.create_static_permutation(m, p['on'], blend)))
    log('permutations_started', '%d instances (%.0f s)' % (len(made), time.time() - start))
    report, bad = [], 0
    for k, (master, name, mic) in enumerate(made):
        d = diagnose(mic) if mic is not None else {'ok': False, 'errors': ['could not create the instance']}
        d['name'], d['master'] = name, master
        report.append(d)
        if not d.get('ok'):
            bad += 1
        if k % 10 == 0 or not d.get('ok'):
            json.dump(report, open(os.path.join(OUT, 'permutations.json'), 'w'), indent=1)
        unreal.log('REMAKEMATERIALS permutation %d/%d %s: %s' % (k + 1, len(made), name, 'ok' if d.get('ok') else d))
    json.dump(report, open(os.path.join(OUT, 'permutations.json'), 'w'), indent=1)
    log('permutations', '%d of %d compiled without errors (%.0f s)' % (len(made) - bad, len(made), time.time() - start))


try:
    if REUSE:
        reuse_existing()
    else:
        build_textures()
        for f in SPEC['functions']:
            try:
                build_function(f)
            except Exception:
                results['functions'][f['name']] = 'FAILED: ' + traceback.format_exc()[-1500:]
                warn('function %s failed' % f['name'])
    log('functions_built', sum(1 for v in results['functions'].values() if not v.startswith('FAILED')))
    built = []
    for spec in SPEC['materials']:
        if ONLY and spec['name'] not in ONLY:
            continue
        try:
            m = build_material(spec)
            d = diagnose(m)
            results['materials'][spec['name']]['compile'] = d
            built.append((spec, m))
        except Exception:
            results['materials'][spec['name']] = {'built': 'FAILED', 'error': traceback.format_exc()[-2000:]}
            warn('master %s failed' % spec['name'])
        save_results()
    log('masters_built', '%d of %d' % (len(built), len(SPEC['materials'])))
    if os.environ.get('REMAKEMATERIALS_PERMUTATIONS', '1') == '1':
        test_permutations(built)
    results['done'] = True
    log('finished', True)
except Exception:
    results['error'] = traceback.format_exc()
    results['done'] = False
    save_results()
    unreal.log_error('REMAKEMATERIALS failed: ' + results['error'])
finally:
    if os.environ.get('REMAKEMATERIALS_QUIT', '1') == '1':
        # (quit a few seconds after the script has returned: quitting from inside it crashed the editor on its way out)
        _quit = {'t': 0.0, 'h': None}

        def _quit_later(dt):
            _quit['t'] += dt
            if _quit['t'] > 3.0 and _quit['h'] is not None:
                unreal.unregister_slate_post_tick_callback(_quit['h'])
                _quit['h'] = None
                unreal.SystemLibrary.quit_editor()

        _quit['h'] = unreal.register_slate_post_tick_callback(_quit_later)
