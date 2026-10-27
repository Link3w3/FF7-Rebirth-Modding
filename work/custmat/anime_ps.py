"""Custom base pass pixel shaders for the game's surface materials (RMI_Surface_* carriers).

A carrier's base pass pixel shader (SQEX's deferred base pass: 7 render targets) is replaced by one generated here: the
same inputs, outputs and resource slots as the carrier's, the carrier's coverage test and GBuffer encoding reproduced
from its DXIL (see anime/std_93.txt: normal 10:10:10 + 8:8:8 with blue noise dithering, metallic / roughness with
specular anti-aliasing, shading model bits, base colour + AO, velocity), and the material's own logic in between.
"""
import os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psinfo
from dxbc import container, signature

DXC = '/home/user/microsoft/dxc-build/bin/dxc'
ENV = dict(os.environ, LD_LIBRARY_PATH='/home/user/microsoft/dxc-build/lib')

TEMPLATE = r'''// %(title)s
// Generated for the game's %(carrier)s base pass (%(variant)s): inputs, outputs and resource slots are the carrier's.
#define HAS_TEXCOORD1 %(has_tc1)d
#define HAS_DYNAMIC_COVERAGE %(dyncov)d
#define HAS_COVERAGE %(coverage)d

cbuffer View : register(b0)
{
    row_major float4x4 View_SVPositionToTranslatedWorld : packoffset(c52);
    float3 View_TranslatedWorldCameraOrigin : packoffset(c76);
    float4 View_TemporalAAJitter : packoffset(c154);
    float4 View_TemporalSamplerBias : packoffset(c155);
    float View_PreExposure : packoffset(c164.y);
    float View_GameTime : packoffset(c172.z);
    uint View_StateFrameIndex : packoffset(c175);
    float3 View_DirectionalLightDirection : packoffset(c178);
};

cbuffer Primitive : register(b1)
{
    uint Primitive_PixelAttribute : packoffset(c27.z);
    float Primitive_DynamicCoverage : packoffset(c27.w);
};

SamplerState View_SharedAnisotropic4XWrappedSampler : register(s0);
Texture3D<float4> View_SpatiotemporalBlueNoiseVolumeTexture : register(t0);
%(textures)s

struct FPSInput
{
    float4 TangentToWorld0 : TEXCOORD10;
    float4 TangentToWorld2 : TEXCOORD11;
    float4 TexCoords0 : TEXCOORD0;
#if HAS_TEXCOORD1
    float4 TexCoords1 : TEXCOORD1;
#endif
    nointerpolation float ConstantContext : CONSTANT_CONTEXT0;
    float4 CurrentClip : CURRENT_CLIP_SPACE_POSITION0;
    float4 PreviousClip : PREVIOUS_CLIP_SPACE_POSITION0;
};

// what the material computes (the game's GBuffer is written from these)
struct FMaterialOutput
{
    float3 BaseColor;
    float Metallic;
    float Roughness;
    float AmbientOcclusion;
    float3 Emissive;
    float3 WorldNormal;
};

struct FMaterialInput
{
    float2 UV0;
    float2 UV1;
    float3 WorldNormal;        // vertex normal with the normal map applied (PixelNormalWS)
    float3 VertexNormal;       // VertexNormalWS
    float3 CameraVector;       // CameraVectorWS: from the pixel to the camera
    float3 TranslatedWorldPosition;
    float4 SvPosition;
    float Time;
    float MipBias;
};

#define TEXTURE_SAMPLER View_SharedAnisotropic4XWrappedSampler

%(material)s

// the carrier's GBuffer normal encoding: n * 0.5 + 0.5, dithered by triangular blue noise away from the extremes
float3 EncodeNormalDithered(float3 N, float3 Dither, float Threshold, float Scale)
{
    float3 E = saturate(N * 0.5 + 0.5);
    float3 Out;
    [unroll] for (int i = 0; i < 3; i++)
    {
        float V = E[i];
        if (abs(V * 2.0 - 1.0) + Threshold < 0.0)
            V = V + Dither[i] * Scale;
        Out[i] = saturate(V);
    }
    return Out;
}

float TriangularNoise(float U)
{
    float X = U * 2.0 - 1.0;
    return sign(X) * (1.0 - sqrt(1.0 - abs(X)));
}

void MainPS(FPSInput In,
    float4 SvPosition : SV_Position,
    bool bIsFrontFace : SV_IsFrontFace,
    out float4 OutTarget0 : SV_Target0,
    out float4 OutTarget1 : SV_Target1,
    out float4 OutTarget2 : SV_Target2,
    out float4 OutTarget3 : SV_Target3,
    out float4 OutTarget4 : SV_Target4,
    out float4 OutTarget5 : SV_Target5,
    out float4 OutTarget6 : SV_Target6)
{
    const float3 TangentX = In.TangentToWorld0.xyz;
    const float3 TangentZ = In.TangentToWorld2.xyz;
    const float3 TangentY = cross(TangentZ, TangentX) * In.TangentToWorld2.w;
    const float MipBias = View_TemporalSamplerBias.y;

    const uint Slice = ((uint)round(In.ConstantContext) + (View_StateFrameIndex & 7u)) & 63u;
    const float4 BlueNoise = View_SpatiotemporalBlueNoiseVolumeTexture.Load(int4(int(SvPosition.x) & 127, int(SvPosition.y) & 127, int(Slice), 0));

#if HAS_DYNAMIC_COVERAGE || HAS_COVERAGE
    {
        bool bKeep = Primitive_DynamicCoverage > BlueNoise.w * 0.99609375 + 0.001953125;
#if HAS_COVERAGE
        if (bKeep)
        {
            const float Coverage = %(coverage_texture)s.SampleBias(View_SharedAnisotropic4XWrappedSampler, In.TexCoords0.xy, View_TemporalSamplerBias.w).r;
            bKeep = Coverage > BlueNoise.x * 0.99609375 + 0.001953125;
        }
#endif
        if (!bKeep)
            discard;
    }
#endif

    FMaterialInput M;
    M.UV0 = In.TexCoords0.xy;
    M.UV1 = In.TexCoords0.zw;
    M.MipBias = MipBias;
    M.SvPosition = SvPosition;
    M.Time = View_GameTime;
    const float4 HomWorld = mul(float4(SvPosition.xyz, 1.0), View_SVPositionToTranslatedWorld);
    M.TranslatedWorldPosition = HomWorld.xyz / HomWorld.w;
    M.CameraVector = normalize(View_TranslatedWorldCameraOrigin - M.TranslatedWorldPosition);
    M.VertexNormal = normalize(TangentZ);
    // the material's tangent space normal (MaterialNormal) to world space, as the carrier does it
    const float3 TangentNormal = normalize(MaterialTangentNormal(M));
    M.WorldNormal = normalize(TangentNormal.x * TangentX + TangentNormal.y * TangentY + TangentNormal.z * TangentZ);

    FMaterialOutput O = EvaluateMaterial(M);

    const float3 Dither = float3(TriangularNoise(BlueNoise.x), TriangularNoise(BlueNoise.y), TriangularNoise(BlueNoise.z));
    const float3 N = O.WorldNormal;

    // specular anti-aliasing of the roughness, as the carrier
    const float Roughness = saturate(O.Roughness);
    const float3 Ndx = ddx_fine(N);
    const float3 Ndy = ddy_fine(N);
    const float Variance = min((dot(Ndx, Ndx) + dot(Ndy, Ndy)) * 0.15915493667125702, 0.18000000715255737);
    const float FilteredRoughness = sqrt(saturate(Variance + Roughness * Roughness));

    const float ShadingModelBits = float(((Primitive_PixelAttribute << 4) & 48u) | 1u) * 0.003921568859368563;

    float2 Velocity = 0;
    if (In.CurrentClip.w != 0.0)
    {
        const float2 Current = In.CurrentClip.xy / In.CurrentClip.w;
        const float2 Previous = In.PreviousClip.xy / In.PreviousClip.w;
        const float2 V = clamp((View_TemporalAAJitter.zw - View_TemporalAAJitter.xy) + Current - Previous, -2.0, 2.0);
        Velocity = V * 0.24998855590820312 + 0.5000076293945312;
    }

    OutTarget0 = float4(O.Emissive, 0.0);
    OutTarget1 = float4(EncodeNormalDithered(N, Dither, -0.9980449676513672, 0.0009775171056389809), 0.6666666269302368);
    OutTarget2 = float4(saturate(O.Metallic), 0.0, FilteredRoughness, ShadingModelBits);
    OutTarget3 = float4(saturate(O.BaseColor), saturate(O.AmbientOcclusion));
    OutTarget4 = float4(0.0, 0.4000000059604645, 0.0, 0.0);
    OutTarget5 = float4(EncodeNormalDithered(N, Dither, -0.9921568632125854, 0.003921568859368563), 0.0);
    OutTarget6 = float4(Velocity, 0.0, 0.0);
}
'''


def texture_slots(info, names):
    """{parameter name: (k, t slot)} of the material textures the carrier's shader binds."""
    by_k = {k: n for k, n, _ in names}
    out = {}
    for ub, res, bind in info['tex']:
        if ub == 2 and res % 2 == 0:
            k = res // 2
            if by_k.get(k):
                out[by_k[k]] = (k, bind)
    return out


def generate(info, names, material, title, carrier, variant):
    slots = texture_slots(info, names)
    decl = []
    for pname, (k, bind) in sorted(slots.items(), key=lambda kv: kv[1][1]):
        decl.append('Texture2D<float4> Material_Texture2D_%d : register(t%d);    // %s' % (k, bind, pname))
    has_tc1 = any(e[0] == 'TEXCOORD' and e[1] == 1 for e in info['isg'])
    coverage = info['discard'] and 'Coverage' in slots and 'WithDynamicCoverage' not in variant or ('Coverage' in slots and info['discard'])
    src = TEMPLATE % dict(title=title, carrier=carrier, variant=variant, has_tc1=has_tc1, dyncov=1 if info['discard'] else 0,
                          coverage=1 if coverage else 0, textures='\n'.join(decl),
                          coverage_texture='Material_Texture2D_%d' % slots['Coverage'][0] if 'Coverage' in slots else 'NONE',
                          material=material(slots))
    return src


def compile_ps(src, out_dxbc):
    with tempfile.NamedTemporaryFile('w', suffix='.hlsl', delete=False) as f:
        f.write(src)
        path = f.name
    try:
        r = subprocess.run([DXC, '-T', 'ps_6_6', '-E', 'MainPS', '-O3', '-HV', '2018', path, '-Fo', out_dxbc],
                           capture_output=True, text=True, env=ENV)
        if r.returncode != 0:
            raise RuntimeError('dxc failed:\n' + r.stderr)
        return open(out_dxbc, 'rb').read(), r.stderr
    finally:
        os.unlink(path)


def interp_modes(text):
    """[(semantic, index, mode)] of the dumpbin's input signature interpolation table."""
    out = []
    sec = text.split('; Input signature:\n;\n; Name                 Index             InterpMode DynIdx', 1)
    if len(sec) < 2:
        return out
    for line in sec[1].splitlines()[2:]:
        if line.strip() == ';':
            break
        parts = line[2:].split()
        out.append(tuple(parts[:3]))
    return out


def verify(carrier_info, dxbc):
    """Differences between the carrier's interface and the new shader's (an empty list when they match)."""
    mine = dict(isg=[], osg=[])
    c = container(dxbc, 0)
    for fourcc, o, size in c['parts']:
        if fourcc == 'ISG1':
            mine['isg'] = signature(dxbc, o)
        if fourcc == 'OSG1':
            mine['osg'] = signature(dxbc, o)
    text = psinfo.dump(dxbc)
    problems = []
    if mine['isg'] != carrier_info['isg']:
        problems.append('input signature: %r != %r' % (mine['isg'], carrier_info['isg']))
    if mine['osg'] != carrier_info['osg']:
        problems.append('output signature: %r != %r' % (mine['osg'], carrier_info['osg']))
    a, b = interp_modes(text), interp_modes(carrier_info['text'])
    if a != b:
        problems.append('interpolation: %r != %r' % (a, b))
    carrier_binds = {(x[3]) for x in carrier_info['bindings'] if x[3].startswith(('cb', 't', 's', 'u'))}
    for name, typ, dim, bind in psinfo.bindings(text):
        if bind.startswith(('cb', 't', 's', 'u')) and bind not in carrier_binds:
            problems.append('binding %s (%s) is not one of the carrier\'s' % (bind, name))
    return problems, text
