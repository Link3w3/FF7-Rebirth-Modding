"""The editable RM_Surface for the End editor, from the checked rebuild (rebuild/RMS_Surface.ush):
  out/RMS_Surface_Editor.hlsl   the Custom node "RMS" (the rebuild's own code; the editor's samplers and noise)
  out/RMS_Engine_Editor.hlsl    the Custom node "RMS Engine": what the game's base pass does with the material's values
                                (world normal, the curvature roughness filter, emissive through the specular layer) for the
                                editor's pins and the Rebirth preview bridges
  out/RMS_Noise_Editor.hlsl     the Custom node "RMS Noise": the dither noise, from the engine's spatiotemporal blue noise
  out/RM_SurfaceRebuilt.json    the graph for build_rm_surface.py (the parameters, switches, inputs, outputs and wiring)
    make_editor_material.py"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out')
SRC = open(os.path.join(R, 'rebuild', 'RMS_Surface.ush')).read()
PARAMS = json.load(open('/work/remake_mat/rm/RM_Surface_params.json'))
SWITCHES = json.load(open(os.path.join(R, 'harness', 'switches.json')))['names']
MARK = '// ==== body ===='

# the game's samplers (the decompiled shaders): anisotropic wrapped unless listed
CLAMPED = {'Muddiness', 'Transparency', 'TransparencyCoefficient', 'Transmittance', 'TransmittanceCoefficient'}
BILINEAR_CLAMPED = {'OceanGeometry'}
BILINEAR_WRAPPED = {'ExtraColor', 'ExtraEmissive'}

OUTPUTS = [  # the node's additional outputs, as the rebuild writes them
    ('RMS_Metallic', 1), ('RMS_Specular', 1), ('RMS_Roughness', 1), ('RMS_AO', 1), ('RMS_Normal', 3), ('RMS_Emissive', 3),
    ('RMS_OpacityMask', 1), ('RMS_Opacity', 1), ('RMS_ShadingModel', 1), ('RMS_ModelParam', 1), ('RMS_Reflectance', 1),
    ('RMS_Custom', 4), ('RMS_WetLayer', 2), ('RMS_WetNormal', 3), ('RMS_ColoredOpacity', 3), ('RMS_Muddiness', 3),
    ('RMS_TransparencyLog2', 1), ('RMS_TransmittanceLog2', 3), ('RMS_Thickness', 1), ('RMS_PhaseG', 1), ('RMS_MediumPath', 1),
    ('RMS_Foam', 1)]


def editor_code():
    lib, body = SRC.split(MARK)
    # (the header comment stays: it documents the node)
    used_tex = sorted(set(re.findall(r'\bT_([A-Za-z0-9]+)\b', SRC)) - {''})
    used_tex = [t for t in used_tex if not t.endswith('Sampler')]

    def sampler_for(tex, line):
        if tex in CLAMPED:
            return 'RMS_CLAMP'
        if tex in BILINEAR_CLAMPED:
            return 'RMS_BILINEAR_CLAMP'
        if tex in BILINEAR_WRAPPED:
            return 'RMS_BILINEAR_WRAP'
        if tex == 'Emissive' and 'fit.x' in line:
            return 'RMS_BILINEAR_CLAMP'   # the full-screen image (ViewCoordinate)
        return 'RMS_WRAP'

    def fix(text):
        out = []
        for line in text.split('\n'):
            line = re.sub(r'\bT_([A-Za-z0-9]+)Sampler\b', lambda m: sampler_for(m.group(1), line), line)
            out.append(line)
        return '\n'.join(out)

    lib, body = fix(lib), fix(body)
    # The editor's Unlit. UE can't take Unlit as one of this material's shading models: UMaterial::RebuildShadingModelField
    # adds every ShadingModel node in the graph, and one Unlit among them makes UE treat the whole material as unlit
    # (FMaterialShadingModelField::IsLit), so UMaterialInterface::CompileProperty compiles BaseColor, Metallic, Specular,
    # Roughness, Normal and AO as their defaults in every permutation. So the Unlit permutations are Default Lit here with
    # nothing for the lights to reflect (no base colour, metal or reflectance): emissive only, as the game's unlit base pass
    # writes it (the rebuild's code above is the checked one; this is added for the editor only).
    assert body.count('return BaseColor;') == 1
    body = body.replace('return BaseColor;', '''if (S_Unlit > 0.5)
{
    BaseColor = float3(0.0, 0.0, 0.0);
    RMS_Metallic = 0.0;
    RMS_Reflectance = 0.0;
}
return BaseColor;''')
    defaults = '\n'.join('%s = %s;' % (n, '0.0' if k == 1 else 'float%d(%s)' % (k, ', '.join(['0.0'] * k))) for n, k in OUTPUTS)
    code = '''// RM_Surface rebuilt (Create a Character System). The node "RMS": the code is the rebuild checked against all 104 of the
// game's RMI_Surface_* shaders (the same text runs in the checker); only the samplers and the dither noise are the editor's.
#if PIXELSHADER
#define RMS_WRAP Material.Wrap_WorldGroupSettings
#define RMS_CLAMP Material.Clamp_WorldGroupSettings
#define RMS_BILINEAR_WRAP View.SharedBilinearWrappedSampler
#define RMS_BILINEAR_CLAMP View.SharedBilinearClampedSampler
struct RMS_Env
{
    // the game's 3D blue noise (the hologram's sparkle) is not in the editor: the engine's Perlin noise volume stands in
    float4 BlueNoise3D(int3 p)
    {
        return View.PerlinNoise3DTexture.Load(int4(p.x & 15, p.y & 15, p.z & 15, 0));
    }
};
''' + lib + MARK + body + '''
#else
''' + defaults + '''
return float3(0.0, 0.0, 0.0);
#endif
'''
    return code, used_tex


ENGINE = r'''// RM_Surface rebuilt: what the game's base pass does with the material's values, for the editor's pins and the Rebirth
// preview bridges (the same arithmetic as the checked base pass): the world normal, the roughness widened by the normal's
// screen-space curvature, emissive light through the dielectric specular layer (the Standard model), the reflectance as
// the engine's Specular (F0 = 0.08 x Specular), and the eye's inner normal and radial direction in world space.
#if PIXELSHADER
float3x3 T2W = Parameters.TangentToWorld;
float3 m = normalize(RMS_N);
float3 raw = mul(m, T2W);
float3 Nw = raw * rsqrt(dot(raw, raw));
float3 dx = ddx_fine(Nw);
float3 dy = ddy_fine(Nw);
float r = saturate(RMS_R);
FilteredRoughness = sqrt(saturate(min((dot(dy, dy) + dot(dx, dx)) * 0.15915493667125701904296875, 0.180000007152557373046875) + r * r));
float3 e = max(RMS_E, float3(0.0, 0.0, 0.0));
if (abs(RMS_SM - 1.0) < 0.5)
{
    float NoV = saturate(dot(Nw, Parameters.CameraVector));
    float a = 1.0 - FilteredRoughness;
    float a004 = (min(a * a, exp2(NoV * -9.27999973297119140625)) * a + (0.0425000004470348358154296875 - FilteredRoughness * 0.0274999998509883880615234375)) * 1.03999996185302734375;
    float t = 1.0 - saturate(((FilteredRoughness * 0.02199999988079071044921875 + -0.039999999105930328369140625) + a004) + ((1.03999996185302734375 - FilteredRoughness * 0.572000026702880859375) - a004) * 0.0400000028312206268310546875);
    float k = (t * t) * exp2(max(0.001000000047497451305389404296875, 0.300000011920928955078125 / max(0.0333333350718021392822265625, NoV)) * -0.0291463173925876617431640625);
    e = e * (k - k * saturate(RMS_M));
}
EmissiveOut = e;
SpecularOut = saturate(RMS_F0 / 0.08);
AOOut = (abs(RMS_SM - 9.0) < 0.5) ? 1.0 : RMS_AO;
float3 wm = normalize(RMS_W);
float3 wr = mul(wm, T2W);
InnerNormalWS = wr * rsqrt(dot(wr, wr));
RadialDirectionWS = RMS_C.xyz * 2.0 - 1.0;
return Nw;
#else
FilteredRoughness = saturate(RMS_R);
EmissiveOut = RMS_E;
SpecularOut = 0.5;
AOOut = RMS_AO;
InnerNormalWS = float3(0.0, 0.0, 1.0);
RadialDirectionWS = float3(0.0, 0.0, 1.0);
return float3(0.0, 0.0, 1.0);
#endif
'''
ENGINE_INPUTS = [('RMS_N', 'RMS_Normal'), ('RMS_R', 'RMS_Roughness'), ('RMS_M', 'RMS_Metallic'), ('RMS_E', 'RMS_Emissive'),
                 ('RMS_SM', 'RMS_ShadingModel'), ('RMS_AO', 'RMS_AO'), ('RMS_F0', 'RMS_Reflectance'), ('RMS_W', 'RMS_WetNormal'),
                 ('RMS_C', 'RMS_Custom')]
ENGINE_OUTPUTS = [('FilteredRoughness', 1), ('EmissiveOut', 3), ('SpecularOut', 1), ('AOOut', 1), ('InnerNormalWS', 3), ('RadialDirectionWS', 3)]

NOISE = r'''// RM_Surface rebuilt: the dither noise. The game reads its spatiotemporal blue noise (128 x 128 x 64) at
// (pixel x & 127, pixel y & 127, (frame & 7) + the primitive's context); the engine's copy of that noise is stored as a
// 128 x 8192 image (the 64 slices stacked).
#if PIXELSHADER
uint2 p = uint2(Parameters.SvPosition.xy) & 127u;
uint z = (View.FrameNumber & 7u) & 63u;
return STBN.Load(int3(p.x, p.y + z * 128u, 0));
#else
return float4(0.5, 0.5, 0.5, 0.5);
#endif
'''


def sampler_type_of(default):
    s = default.upper()
    if s.endswith('_BC5'):
        return 'SAMPLERTYPE_NORMAL'
    if s.endswith('_BC4'):
        return 'SAMPLERTYPE_ALPHA'
    if s.endswith('_SRGB'):
        return 'SAMPLERTYPE_COLOR'
    return 'SAMPLERTYPE_LINEAR_COLOR'


def main():
    os.makedirs(OUT, exist_ok=True)
    code, used_tex = editor_code()
    open(os.path.join(OUT, 'RMS_Surface_Editor.hlsl'), 'w').write(code)
    open(os.path.join(OUT, 'RMS_Engine_Editor.hlsl'), 'w').write(ENGINE)
    open(os.path.join(OUT, 'RMS_Noise_Editor.hlsl'), 'w').write(NOISE)
    used_sw = sorted(set(re.findall(r'\bS_([A-Za-z0-9]+)\b', SRC)))
    used_vec = sorted(set(re.findall(r'\bV_([A-Za-z0-9]+)\b', SRC)))
    textures = [{'name': n, 'default': '/Game/Renderer/Texture/%s.%s' % (d, d), 'sampler_type': sampler_type_of(d),
                 'connected': n in used_tex} for n, d in PARAMS['textures']]
    names = {t['name'] for t in textures}
    missing = [t for t in used_tex if t not in names]
    if missing:
        raise SystemExit('textures the rebuild reads that RM_Surface lacks: %s' % missing)
    vectors = [{'name': n, 'default': [float(x) for x in d], 'connected': n in used_vec} for n, d in PARAMS['vectors']]
    spec = {
        'asset': '/Game/Renderer/Material/RM_Surface',
        'material': {'shading_model': 'MSM_FROM_MATERIAL_EXPRESSION', 'blend_mode': 'BLEND_OPAQUE', 'opacity_mask_clip_value': 0.33329999446868896,
                     'tangent_space_normal': False, 'two_sided': False,
                     'usage': ['skeletal_mesh', 'morph_targets', 'instanced_static_meshes', 'niagara_mesh_particles', 'static_lighting']},
        'textures': textures,
        'vectors': vectors,
        'buffers': [{'name': n, 'default': '/Engine/EngineResources/DefaultBuffer.DefaultBuffer'} for n, d in PARAMS['srbs']],
        'scalars': [{'name': 'RefractionDepthBias', 'default': 0.0}],
        'switches': [{'name': s + '_', 'input': 'S_' + s, 'connected': s in used_sw} for s in SWITCHES],
        'node': {'code_file': 'RMS_Surface_Editor.hlsl', 'outputs': [{'name': n, 'size': k} for n, k in OUTPUTS],
                 'inputs': ['UV0', 'UV1', 'UV2', 'UV3', 'RMS_Noise', 'RMS_DynamicCoverage', 'RMS_VertexExpression', 'RMS_EBuffer',
                            'RMS_LocalToWorld0', 'RMS_LocalToWorld1', 'RMS_LocalToWorld2']
                           + ['T_' + t['name'] for t in textures if t['connected']]
                           + ['V_' + v['name'] for v in vectors if v['connected']]
                           + ['S_' + s for s in SWITCHES if s in used_sw]},
        'engine': {'code_file': 'RMS_Engine_Editor.hlsl', 'inputs': ENGINE_INPUTS, 'outputs': [{'name': n, 'size': k} for n, k in ENGINE_OUTPUTS]},
        'noise': {'code_file': 'RMS_Noise_Editor.hlsl', 'texture': '/Engine/EngineResources/SpatiotemporalBlueNoiseVolumeSource.SpatiotemporalBlueNoiseVolumeSource'},
        # the game's static shading model choice, as the rebuild assigns it (later in the list wins); Layered picks Fabric per
        # pixel where the rebuild's model says 8
        # (Unlit is Default Lit with no lit inputs here: see editor_code; an Unlit ShadingModel node would make UE compile
        # every permutation's lit inputs as constants)
        'shading_models': [['Eye_', 'MSM_EYE'], ['Unlit_', 'MSM_DEFAULT_LIT'], ['Standard_', 'MSM_DEFAULT_LIT'], ['Skin_', 'MSM_PREINTEGRATED_SKIN'],
                           ['Subsurface_', 'MSM_SUBSURFACE_PROFILE'], ['Hair_', 'MSM_HAIR'], ['Fabric_', 'MSM_CLOTH']],
        'pins': {'BaseColor': ['RMS', ''], 'Metallic': ['RMS', 'RMS_Metallic'], 'Specular': ['Engine', 'SpecularOut'],
                 'Roughness': ['Engine', 'FilteredRoughness'], 'AmbientOcclusion': ['Engine', 'AOOut'], 'Normal': ['Engine', ''],
                 'EmissiveColor': ['Engine', 'EmissiveOut'], 'Opacity': ['RMS', 'RMS_Opacity'], 'OpacityMask': ['RMS', 'RMS_OpacityMask']},
        'bridges': {
            'RebirthSurfaceOutput': {'NormalWS': ['Engine', ''], 'Roughness': ['Engine', 'FilteredRoughness'], 'MaterialAO': ['RMS', 'RMS_AO'],
                                     'SurfaceDiffusion': ['RMS', 'RMS_Custom', 'x'], 'Sentinel': ['Const', 1.0]},
            'RebirthHairOutput': {'EncodedWideBentNormal': ['RMS', 'RMS_Custom', 'xyz']},
            'RebirthEyeOutput': {'ScleraNormalWS': ['Engine', 'InnerNormalWS'], 'RadialDirectionWS': ['Engine', 'RadialDirectionWS'],
                                 'IrisNormalPacked': ['RMS', 'RMS_Custom', 'w'], 'ScleraMask': ['RMS', 'RMS_Metallic'],
                                 'IrisOcclusion': ['RMS', 'RMS_Specular'], 'RadialDistance': ['RMS', 'RMS_AO']},
        },
        'vertex_expression': {'position_switch': 'VertexExpressionPosition_', 'normal_switch': 'VertexExpressionNormal_'},
    }
    json.dump(spec, open(os.path.join(OUT, 'RM_SurfaceRebuilt.json'), 'w'), indent=1)
    print('code %d lines; %d textures (%d connected), %d vectors (%d connected), %d switches (%d connected), %d node inputs' % (
        code.count('\n'), len(textures), sum(t['connected'] for t in textures), len(vectors), sum(v['connected'] for v in vectors),
        len(SWITCHES), len(used_sw), len(spec['node']['inputs'])))


if __name__ == '__main__':
    main()
