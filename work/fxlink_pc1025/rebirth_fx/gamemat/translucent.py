"""Translucent Game Materials: an editor material whose blend mode is translucent (Translucent, AlphaComposite or
Additive: the Remake masters EndMaterial_Glass, _Tear, _Thin, _Jewel, _Water and the unlit _Hologram, _InvisibleBody,
_Particle, _Directional are AlphaComposite) compiled onto one of the game's translucent character carriers, so the game
draws it in its translucency pass with its own shader code. The opaque path (carrier_build, basepass, depthpass) is not
used for them and is unchanged.

What the game's translucent carriers are (read out of their packages and shaders: Saved/RebirthGameMaterials/
translucent/analysis_v2): every translucent RMI_Surface_* (Glass_*, Crystal_*, Water_*, Unlit_*) is drawn with SQEX's
BLEND_AlphaCompositeColored, a depth pre-pass of its own (PreDepth: the carrier's TDepthOnlyPS, dynamic coverage only)
and its own velocity pass; neither reads a material texture, so they stay the carrier's. Their base pass pixel shaders
(TBasePassPS{No,With}DynamicCoverage and the lighter fa99734846c7227e variant) read the forward pass's
TranslucentBasePass buffer and write two targets:
  SV_Target0  rgb  the light the surface sends to the camera (premultiplied, * View.PreExposure)
              a    the luminance (0.2126, 0.7152, 0.0722) of SV_Target1
  SV_Target1  rgb  its coloured opacity (how much of what is behind it it takes away), a 0
(the glass writes its coloured opacity there, the hologram 0: it only adds light). This shader writes them the same way.

Kinds (convert.CARRIERS):
  translucent        lit materials on RMI_Surface_Glass_Thin_Wide_Character: the game's thin glass for characters
                     (TLM_Surface: lit per pixel in the translucency pass, its pass binds the translucency lighting volume
                     and the forward directional light, which this shader reads). Thin glass suits what the lit masters
                     are on a character: a tear film, a lens, a thin veil, a jewel's facets, a wet surface; the thick
                     carriers (Crystal, Water) differ only in the game's own glass model, which these shaders replace.
  translucent_unlit  unlit materials on RMI_Surface_Unlit_Hologram_Wide_Character: the game's unlit glow for characters
                     (no lighting, its base pass binds the scene depth, so a material's depth fade works); a material with
                     more textures than its four texture parameters goes on the glass carrier instead.

Lighting (lit kinds): the material's own surface values (base colour, metallic, specular, roughness, normal, ambient
occlusion) lit with what the carrier's own shader of that variant reads from the pass:
  environment  the game's translucency lighting volume (View.TranslucencyLightingVolume[1]; colour in EnvironmentA, the
               luminance towards +x/+y/+z in B and -x/-y/-z in C, pre-exposed: an ambient cube, decoded as the game's
               glass decodes it), for the diffuse light at the normal and the specular one at the reflection direction
               (EnvBRDF); in the lighter variant only A (no direction), as the game's own lighter variant has it
  sun          the forward directional light (TranslucentBasePass.Shared.Forward: Lambert diffuse, GGX specular), with the
               game's directional light modifier for primitives that ask for it (Primitive.PixelAttribute & 2)
Not taken (the game's glass has them): shadows (its shadow maps are bindless arrays), local lights, the reflection
captures, fog, refraction. The material's ambient occlusion darkens the sun as well, in place of the shadows.

Blending: AlphaComposite (premultiplied, the Remake masters): diffuse * opacity + specular + emissive over the scene,
which keeps (1 - opacity) * (1 - reflectance) of itself; Translucent: (diffuse + specular + emissive) * opacity, opacity;
Additive: everything added, nothing taken.

Every texture or buffer of the translucency pass's own buffer (TranslucentBasePass) this shader reads is one the
carrier's own shader for that variant binds, at the resource the carrier's resource table names (catalog): nothing is
read that the game does not provide in that pass. View members (its samplers, noise volumes) are the View's, which every
pass has.

The game's noise volumes: Remake's masters read the engine's 3D noise (the hologram's), which the editor has only as a
stand-in, RemakeEditorVolumeNoise (Tools/RemakeMaterials/README.txt). On the game it is the View's own noise volumes
(game_noise_volumes): a material that loads texels of it (its 64-texel cells, as the game's own hologram reads
View.BlueNoiseVolumeTexture) reads View.BlueNoiseVolumeTexture, one that samples it reads View.PerlinNoiseVolumeTexture
with the View's wrapping sampler. Other volume textures are not supported (the carrier's texture parameters are 2D).
REBIRTHFX_TRANSLUCENT=0 (convert.kind_of): translucent materials are refused as before.
"""
import os
import re

from . import env
from . import gbuild as build
from . import basepass
from . import depthpass
from . import psinfo
from . import shaderblob
from . import ub
from . import carrier_build as cb
from .verify import verify

BLENDS = {'BLEND_AlphaComposite': 0, 'BLEND_Translucent': 1, 'BLEND_Additive': 2}
TBP = 'TranslucentBasePass'
ENV = ['TranslucentBasePass_TranslucencyLightingVolumeEnvironment' + x for x in 'ABC']
SCENE_DEPTH = 'TranslucentBasePass_SceneTextures_SceneDepthTexture'
# the TranslucentBasePass constants this shader reads: (member, HLSL type, the offset it must have in the game's buffer)
TBP_CONSTANTS = (('TranslucentBasePass_Shared_Forward_HasDirectionalLight', 'uint', 8),
                 ('TranslucentBasePass_Shared_Forward_DirectionalLightColor', 'float3', 64),
                 ('TranslucentBasePass_Shared_Forward_DirectionalLightDirection', 'float3', 80))

TEMPLATE = r'''// %(title)s
// The game's translucent base pass for %(carrier)s (%(variant)s) around the editor's own material code: two targets, as
// the game's BLEND_AlphaCompositeColored surfaces write them (gamemat/translucent.py).
#define GAME_HAS_TEXCOORD1 %(has_tc1)d
#define GAME_DYNAMIC_COVERAGE %(dyncov)d
#define GAME_TRANSLUCENT_LIT %(lit)d
#define GAME_ENV_VOLUME %(env)d
#define GAME_ENV_DIRECTIONAL %(envdir)d
#define GAME_DIRECTIONAL_LIGHT %(dirlight)d
#define GAME_BLEND %(blend)d

#include "Engine/Private/Common.ush"

// the blue noise the game's surfaces dither with, for the material's code (set in MainPS before the material runs)
static float4 GameBlueNoise = 0.5;
#define GAME_BLUE_NOISE GameBlueNoise
#define GAME_HAIR_STRAND_NOISE GameBlueNoise.x

#include "Engine/Generated/Material.ush"

// the carrier's interpolants, as its own pixel shader takes them (its input signature)
struct FGameTranslucentInterpolants
{
%(interpolants)s
};

float GameLuminance(float3 C)
{
    return dot(C, float3(0.2126, 0.7152, 0.0722));
}

float3 GameSafeNormalize(float3 V, float3 Fallback)
{
    const float L2 = dot(V, V);
    return L2 > 1e-12 ? V * rsqrt(L2) : Fallback;
}

#if GAME_ENV_VOLUME
// the game's translucency lighting volume, as its glass reads it: colour in A; the luminance towards +x, +y, +z in B and
// towards -x, -y, -z in C (an ambient cube; the lighter variant has A only), pre-exposed
float3 GameEnvironmentLight(float3 WorldPosition, float3 Dir)
{
    const float3 UVW = (WorldPosition - View.TranslucencyLightingVolumeMin[1].xyz) * View.TranslucencyLightingVolumeInvSize[1].xyz;
    const float3 A = TranslucentBasePass_TranslucencyLightingVolumeEnvironmentA.SampleLevel(View.SharedBilinearClampedSampler, UVW, 0).rgb;
#if GAME_ENV_DIRECTIONAL
    const float3 B = TranslucentBasePass_TranslucencyLightingVolumeEnvironmentB.SampleLevel(View.SharedBilinearClampedSampler, UVW, 0).rgb;
    const float3 C = TranslucentBasePass_TranslucencyLightingVolumeEnvironmentC.SampleLevel(View.SharedBilinearClampedSampler, UVW, 0).rgb;
    const float3 P = saturate(Dir);
    const float3 M = saturate(-Dir);
    const float L = dot(B, P * P) + dot(C, M * M);
    const float LA = GameLuminance(A);
    return LA > 0.0 ? A * (L / LA) * View.OneOverPreExposure : (float3)0.0;
#else
    return A * View.OneOverPreExposure;
#endif
}
#endif

float GameD_GGX(float a2, float NoH)
{
    const float d = (NoH * a2 - NoH) * NoH + 1.0;
    return a2 / (PI * d * d);
}

float GameVis_SmithJointApprox(float a2, float NoV, float NoL)
{
    const float a = sqrt(a2);
    const float V = NoL * (NoV * (1.0 - a) + a);
    const float L = NoV * (NoL * (1.0 - a) + a);
    return 0.5 * rcp(V + L);
}

float3 GameF_Schlick(float3 SpecularColor, float VoH)
{
    const float Fc = Pow5(1.0 - VoH);
    return saturate(50.0 * SpecularColor.g) * Fc + (1.0 - Fc) * SpecularColor;
}

float3 GameEnvBRDFApprox(float3 SpecularColor, float Roughness, float NoV)
{
    const float4 c0 = float4(-1.0, -0.0275, -0.572, 0.022);
    const float4 c1 = float4(1.0, 0.0425, 1.04, -0.04);
    const float4 r = Roughness * c0 + c1;
    const float a004 = min(r.x * r.x, exp2(-9.28 * NoV)) * r.x + r.y;
    float2 AB = float2(-1.04, 1.04) * a004 + r.zw;
    AB.y *= saturate(50.0 * SpecularColor.g);
    return SpecularColor * AB.x + AB.y;
}

void MainPS(FGameTranslucentInterpolants In,
    float4 SvPosition : SV_Position,
    bool bIsFrontFace : SV_IsFrontFace,
    out float4 OutTarget0 : SV_Target0,
    out float4 OutTarget1 : SV_Target1)
{
    // the view the material reads (ResolvedView), set first as the engine's base pass does
    ResolvedView = ResolveView();

    const uint Slice = ((uint)round(In.ConstantContext) + (View.StateFrameIndex & 7u)) & 63u;
    const float4 BlueNoise = View.SpatiotemporalBlueNoiseVolumeTexture.Load(int4(int(SvPosition.x) & 127, int(SvPosition.y) & 127, int(Slice), 0));
    GameBlueNoise = BlueNoise;

#if GAME_DYNAMIC_COVERAGE
    // the carrier's own coverage test (its distance fade-out dithering)
    if (!(Primitive.DynamicCoverage > BlueNoise.w * 0.99609375 + 0.001953125))
        discard;
#endif

%(vf_part)s
    // the material, as the editor compiled it
    FPixelMaterialInputs PixelMaterialInputs;
    CalcMaterialParameters(MaterialParameters, PixelMaterialInputs, SvPosition, bIsFrontFace);

    const float Opacity = saturate(GetMaterialOpacity(PixelMaterialInputs));
#if GAMESH_EMISSIVE_SCREEN
    // a material that makes up for the camera's exposure itself: shown as the editor shows it at a fixed exposure
    const float3 Emissive = GetMaterialEmissive(PixelMaterialInputs) * (GAMESH_EYE_ADAPTATION_CONST * GAME_EMISSIVE_SCALE);
#else
    const float3 Emissive = GetMaterialEmissive(PixelMaterialInputs) * (View.PreExposure * GAME_EMISSIVE_SCALE);
#endif
    float3 Diffuse = 0.0;
    float3 Specular = 0.0;
    float3 Reflectance = 0.0;
#if GAME_TRANSLUCENT_LIT && !(MATERIAL_SHADINGMODEL_UNLIT && MATERIAL_SINGLE_SHADINGMODEL)
    {
        const float3 BaseColor = GetMaterialBaseColor(PixelMaterialInputs);
        const float Metallic = GetMaterialMetallic(PixelMaterialInputs);
        const float SpecularInput = GetMaterialSpecular(PixelMaterialInputs);
        const float AO = saturate(GetMaterialAmbientOcclusion(PixelMaterialInputs));
        const float3 N = GameSafeNormalize(MaterialParameters.WorldNormal, MaterialParameters.TangentToWorld[2]);
        const float3 V = MaterialParameters.CameraVector;
        // specular anti-aliasing of the roughness, as the game's glass does it
        const float3 Ndx = ddx_fine(N);
        const float3 Ndy = ddy_fine(N);
        const float Variance = min((dot(Ndx, Ndx) + dot(Ndy, Ndy)) * 0.15915493667125702, 0.18000000715255737);
        const float R0 = saturate(GetMaterialRoughness(PixelMaterialInputs));
        const float Roughness = max(sqrt(saturate(Variance + R0 * R0)), 0.02);
        const float a = Roughness * Roughness;
        const float NoV = saturate(abs(dot(N, V)) + 1e-5);
        const float3 DiffuseColor = BaseColor - BaseColor * Metallic;
        const float3 SpecularColor = lerp((0.08 * SpecularInput).xxx, BaseColor, Metallic);
        Reflectance = GameEnvBRDFApprox(SpecularColor, Roughness, NoV);
        float3 DiffuseLight = 0.0;
        float3 SpecularLight = 0.0;
#if GAME_ENV_VOLUME
        const float3 R = 2.0 * dot(V, N) * N - V;
        const float3 RDom = GameSafeNormalize(lerp(N, R, (1.0 - a) * (sqrt(1.0 - a) + a)), N);
        DiffuseLight += GameEnvironmentLight(MaterialParameters.AbsoluteWorldPosition, N) * AO;
        SpecularLight += Reflectance * GameEnvironmentLight(MaterialParameters.AbsoluteWorldPosition, RDom) * AO;
#endif
#if GAME_DIRECTIONAL_LIGHT
        if (TranslucentBasePass_Shared_Forward_HasDirectionalLight != 0u)
        {
            // the sun (no shadows: the material's ambient occlusion stands in for them)
            const float3 L = TranslucentBasePass_Shared_Forward_DirectionalLightDirection;
            float3 LightColor = TranslucentBasePass_Shared_Forward_DirectionalLightColor * AO;
            if ((Primitive.PixelAttribute & 2u) != 0u)
                LightColor *= View.LightModifierDirectionalLight;
            const float NoL = saturate(dot(N, L));
            const float3 H = GameSafeNormalize(V + L, N);
            const float NoH = saturate(dot(N, H));
            const float VoH = saturate(dot(V, H));
            // (the sun's highlight no sharper than roughness 0.08: the sun is no point, and a sharper one only flickers)
            const float SunA = Square(max(Roughness, 0.08));
            const float SunA2 = SunA * SunA;
            DiffuseLight += LightColor * (NoL / PI);
            SpecularLight += LightColor * (NoL * GameD_GGX(SunA2, NoH) * GameVis_SmithJointApprox(SunA2, NoV, NoL)) * GameF_Schlick(SpecularColor, VoH);
        }
#endif
        Diffuse = DiffuseColor * DiffuseLight * View.PreExposure;
        Specular = SpecularLight * View.PreExposure;
    }
#endif
#if GAME_BLEND == 2
    // additive: adds its light, takes nothing from behind
    const float3 Color = Diffuse + Specular + Emissive;
    const float3 Taken = 0.0;
#elif GAME_BLEND == 1
    // translucent: all of its light at its opacity
    const float3 Color = (Diffuse + Specular + Emissive) * Opacity;
    const float3 Taken = Opacity.xxx;
#else
    // alpha composite (premultiplied): the light it scatters at its opacity, the light it reflects and emits as they are;
    // what is behind shows through what it neither covers nor reflects
    const float3 Color = Diffuse * Opacity + Specular + Emissive;
    const float3 Taken = saturate(Opacity + (1.0 - Opacity) * Reflectance);
#endif
    // (kept inside the half-float range of the game's scene colour)
    OutTarget0 = float4(clamp(Color, 0.0, 65000.0), GameLuminance(Taken));
    OutTarget1 = float4(Taken, 0.0);
}
'''

# interpolant names the vertex factory part (depthpass.VF_PART) reads
MEMBERS = {('TEXCOORD', 10): 'TangentToWorld0', ('TEXCOORD', 11): 'TangentToWorld2', ('TEXCOORD', 0): 'TexCoords0',
           ('TEXCOORD', 1): 'TexCoords1', ('CONSTANT_CONTEXT', 0): 'ConstantContext'}
NOINTERPOLATION = ('CONSTANT_CONTEXT',)


def interpolants(isg):
    """The members of the interpolant struct for a carrier pixel shader's input signature [(semantic, index, register,
    mask, sysvalue, type, stream)]: its own elements in its order (the system values are MainPS's parameters)."""
    lines = []
    for name, index, reg, mask, sysval, comptype, stream in isg:
        if sysval != 0:
            continue
        n = bin(mask).count('1')
        if mask != (1 << n) - 1:
            raise ValueError('%s%d: mask %d is not from x' % (name, index, mask))
        typ = {0: 'float', 1: 'uint', 2: 'int', 3: 'float'}.get(comptype, 'float')
        if n > 1:
            typ += str(n)
        member = MEMBERS.get((name, index), 'Carrier%s%d' % (re.sub(r'[^A-Za-z]', '', name.title()), index))
        lines.append('    %s%s %s : %s%d;' % ('nointerpolation ' if name in NOINTERPOLATION else '', typ, member, name, index))
    return '\n'.join(lines)


def variant_catalog(info, ubs):
    """{binding name: (uniform buffer name, map ('tex', 'srv', 'samp', 'uav'), resource index)} of a carrier pixel
    shader (psinfo.info, its uniform buffer names): every resource it binds from a uniform buffer other than View and
    Material (those two are found by name: ub.resource_index, the slot plan)."""
    reg_name = {}
    for name, typ, dim, bind in info['bindings']:
        reg_name[bind] = name
    out = {}
    for kind, prefix in (('tex', 't'), ('srv', 't'), ('samp', 's'), ('uav', 'u')):
        for slot, res, reg in info[kind]:
            name = reg_name.get('%s%d' % (prefix, reg))
            if not name or slot >= len(ubs) or not ubs[slot]:
                continue
            if ubs[slot] in ('View', 'Material'):
                continue
            if name in out and out[name] != (ubs[slot], kind, res):
                raise ValueError('%s is bound twice differently' % name)
            out[name] = (ubs[slot], kind, res)
    return out


def aliases(catalog):
    """The engine's names for what the material code may read that the pass gives under the game's names: the scene
    depth (CalcSceneDepth: SceneTexturesStruct.SceneDepthTexture with its PointClampSampler) where the carrier's variant
    binds it, with the View's point sampler."""
    out = {}
    if SCENE_DEPTH in catalog:
        out['SceneTexturesStruct_SceneDepthTexture'] = catalog[SCENE_DEPTH]
        out['SceneTexturesStruct_PointClampSampler'] = ('View', 'samp', ub.resource_index('View', 'SharedPointClampedSampler'))
    return out


def tbp_layout_ok(info):
    """The game's TranslucentBasePass constants this shader reads, checked at their offsets in the carrier shader's own
    buffer layout (its reflection). Returns a list of problems."""
    members = psinfo.cbuffer_members(info['text'], TBP)
    problems = []
    for name, typ, offset in TBP_CONSTANTS:
        got = members.get(name)
        if got is None:
            problems.append('%s is not in the carrier\'s %s' % (name, TBP))
        elif got[0] != offset or got[1] != typ:
            problems.append('%s is at %s, wanted %s %d' % (name, got[:2], typ, offset))
    return problems


def tbp_declaration(register, constants, textures):
    """Engine/Generated/UniformBuffers/TranslucentBasePass.ush: the game's buffer at its register with the constants
    this shader reads at their offsets, and the textures it may read (unbound unless used)."""
    lines = ['#ifndef __UniformBuffer_TranslucentBasePass_Definition__', '#define __UniformBuffer_TranslucentBasePass_Definition__']
    if constants:
        lines.append('cbuffer TranslucentBasePass : register(b%d)' % register)
        lines.append('{')
        for name, typ, offset in TBP_CONSTANTS:
            lines.append('    %s %s : packoffset(%s);' % (typ, name, ub.packoffset(offset)))
        lines.append('};')
    for name, typ in textures:
        lines.append('%s %s;' % (typ, name))
    lines.append('#endif')
    return '\n'.join(lines) + '\n'


# the editor's stand-in for the engine's 3D noise (Remake's masters, Tools/RemakeMaterials)
NOISE_STAND_IN = '/Game/GameContents/Renderer/Texture/RemakeEditorVolumeNoise'


def game_noise_volumes(code, exported):
    """The material's code with its volume textures that are the editor's stand-in for the engine's noise
    (NOISE_STAND_IN) read from the game's View noise volumes: View.BlueNoiseVolumeTexture where the custom expression
    it is given to loads texels (.Load, the game hologram's own way), else View.PerlinNoiseVolumeTexture sampled with
    View.SharedBilinearWrappedSampler. Returns (code, {volume texture index: View member})."""
    chosen = {}
    for t in exported.textures:
        if t.get('type') != 'VolumeTexture' or (t.get('texture') or '').split('.')[0] != NOISE_STAND_IN:
            continue
        k = t['index']
        member = 'PerlinNoiseVolumeTexture'
        for m in re.finditer(r'(CustomExpression\d+)\(([^;]*?)Material\.VolumeTexture_%d\b' % k, code):
            body = re.search(r'\b%s\([^)]*\)\s*\{(.*?)\n\}' % m.group(1), code, re.S)
            if body and '.Load(' in body.group(1):
                member = 'BlueNoiseVolumeTexture'
        chosen[k] = member
    for k, member in chosen.items():
        code = re.sub(r'\bMaterial\.VolumeTexture_%dSampler\b' % k, 'View.SharedBilinearWrappedSampler', code)
        code = re.sub(r'\bMaterial\.VolumeTexture_%d\b' % k, 'View.' + member, code)
    return code, chosen


def blend_defines(exported):
    """The material environment's defines with its translucent blend mode (as FMaterial::SetupMaterialEnvironment sets
    them: AlphaComposite sets TRANSLUCENT too)."""
    d = exported.defines()
    blend = exported.info.get('blend_mode')
    for k in ('MATERIALBLENDING_SOLID', 'MATERIALBLENDING_MASKED', 'MATERIALBLENDING_TRANSLUCENT',
              'MATERIALBLENDING_ADDITIVE', 'MATERIALBLENDING_MODULATE', 'MATERIALBLENDING_ALPHACOMPOSITE'):
        d.pop(k, None)
    if blend == 'BLEND_AlphaComposite':
        d['MATERIALBLENDING_TRANSLUCENT'] = 1
        d['MATERIALBLENDING_ALPHACOMPOSITE'] = 1
    elif blend == 'BLEND_Translucent':
        d['MATERIALBLENDING_TRANSLUCENT'] = 1
    elif blend == 'BLEND_Additive':
        d['MATERIALBLENDING_ADDITIVE'] = 1
    else:
        raise ValueError('%s is not a translucent blend mode' % blend)
    return d


def features(v, lit):
    """What the shader for carrier variant v reads from the pass: only what the carrier's own shader of the variant
    binds (or, for constants, the buffer it binds with them where the game has them)."""
    ubs = cb.ub_names(v['blob'])
    cat = variant_catalog(v['info'], ubs)
    tbp_bound = any(b[0] == TBP and b[3].startswith('cb') for b in v['info']['bindings'])
    f = dict(ubs=ubs, catalog=cat, env=False, envdir=False, dirlight=False, scene_depth=SCENE_DEPTH in cat,
             tbp_register=ubs.index(TBP) if TBP in ubs else None)
    if lit:
        f['env'] = ENV[0] in cat
        f['envdir'] = f['env'] and ENV[1] in cat and ENV[2] in cat
        f['dirlight'] = tbp_bound and not tbp_layout_ok(v['info'])     # (bound, and the constants where they should be)
    return f


def compile_variant(exported, carrier, res, work, lit=True, exposure='auto', editor_exposure=1.0):
    """(dxbc bytes, bindings, problems, features) of the material compiled for the carrier's base pass variant res."""
    v = carrier.variants[res]
    v = dict(v, blob=carrier.shaders[res]['code'])
    f = features(v, lit)
    blend = BLENDS.get(exported.info.get('blend_mode'))
    if blend is None:
        raise ValueError('%s materials are not translucent' % exported.info.get('blend_mode'))
    variant = '/'.join(t for t in v['types'] if t != 'fa99734846c7227e') or 'fa99734846c7227e'
    src = TEMPLATE % dict(title='%s on %s' % (exported.name, carrier.name), carrier=carrier.name, variant=variant,
                          has_tc1=1 if v['has_tc1'] else 0, dyncov=1 if v['info']['discard'] else 0, lit=1 if lit else 0,
                          env=1 if f['env'] else 0, envdir=1 if f['envdir'] else 0, dirlight=1 if f['dirlight'] else 0,
                          blend=blend, interpolants=interpolants(v['info']['isg']), vf_part=depthpass.VF_PART)
    textures = []
    if f['env']:
        textures += [(ENV[0], 'Texture3D')]
    if f['envdir']:
        textures += [(ENV[1], 'Texture3D'), (ENV[2], 'Texture3D')]
    tbp = tbp_declaration(f['tbp_register'] if f['tbp_register'] is not None else 2, f['dirlight'], textures)
    os.makedirs(work, exist_ok=True)
    code, noise = game_noise_volumes(cb.game_material_code(exported.code), exported)
    f['noise'] = noise
    usf = build.stage(work, code, exported.material_ub(), src,
                      extra_generated={'UniformBuffers/TranslucentBasePass.ush': tbp}, registers=v['registers'])
    defines = dict(basepass.BASE_DEFINES)
    defines.update(blend_defines(exported))
    defines.update(basepass.exposure_defines(exported.code, exposure, editor_exposure)[1])
    if not f['scene_depth']:
        # (the carrier's variant has no scene depth: CalcSceneDepth gives the far plane, so a depth fade does nothing)
        defines['SCENE_TEXTURES_DISABLED'] = 1
    pre = build.preprocess(work, usf, defines)
    names = set(build.GAME_UBS) | set(exported.uniform_buffer_names()) | set(build.STUB_UBS)
    final = build.rewrite_uniform_buffers(pre, names)
    dxbc, dump, warnings = build.compile_ps(work, final)
    problems, _ = verify(v['info'], dxbc)
    problems = [p for p in problems if not p.startswith('binding ')]
    return dxbc, build.bindings(dump), problems, f


def check_blob(carrier_blob, blob, carrier_named, catalog):
    """The new blob against the carrier shader it replaces: the same uniform buffers (names, layout hashes), and every
    resource it binds one the pass has: a View member of the right kind, a texture or sampler of the carrier's Material
    buffer (one of its texture parameters), or a resource the carrier's own shader binds from its other buffers (same
    buffer, map and index). Returns a list of problems (empty when it matches)."""
    problems = []
    t0, at0, total0, data0 = shaderblob.parse(carrier_blob)
    t1, at1, total1, data1 = shaderblob.parse(blob)
    ubs0, ubs1 = shaderblob._ub_names(data0), shaderblob._ub_names(data1)
    if ubs0 != ubs1:
        problems.append('uniform buffers %s != the carrier\'s %s' % (ubs1, ubs0))
    if t0['maps']['LayoutHashes'] != t1['maps']['LayoutHashes']:
        problems.append('layout hashes differ from the carrier\'s')
    nub = len(t1['maps']['LayoutHashes'])
    allowed = set(catalog.values())
    view = [m for m in ub.layouts()['View'] if not ub.is_constant(m)]
    n_material = 2 * len(carrier_named[1])
    named_k = set(k for k, n in carrier_named[0])
    for kind, mname in (('tex', 'TextureMap'), ('samp', 'SamplerMap'), ('srv', 'SRVMap'), ('uav', 'UAVMap')):
        for slot, res, reg in psinfo.entries(t1['maps'][mname], nub):
            ubname = ubs1[slot] if slot < len(ubs1) else None
            if not ubname:
                problems.append('%s entry on uniform buffer slot %d, which has no buffer' % (kind, slot))
            elif ubname == 'View':
                if res >= len(view):
                    problems.append('View resource %d does not exist' % res)
                else:
                    want = {'tex': 'TEXTURE', 'samp': 'SAMPLER', 'srv': 'SRV', 'uav': 'UAV'}[kind]
                    if view[res]['base_name'] != want:
                        problems.append('View resource %d (%s) is a %s, bound as %s' % (res, view[res]['name'], view[res]['base_name'], kind))
            elif ubname == 'Material':
                if kind not in ('tex', 'samp') or res >= n_material or (res % 2) != (1 if kind == 'samp' else 0):
                    problems.append('Material resource %d bound as %s' % (res, kind))
                elif res // 2 not in named_k:
                    problems.append('Material resource %d is not one of the carrier\'s texture parameters' % res)
            elif (ubname, kind, res) not in allowed:
                problems.append('%s resource %d (%s) is not one the carrier\'s shader binds' % (ubname, res, kind))
    if data0 and [k for k, _ in data0] != [k for k, _ in data1]:
        problems.append('optional data keys %s != the carrier\'s %s' % ([k for k, _ in data1], [k for k, _ in data0]))
    return problems


def build_blobs(exported, carrier, work_root, prefer=(), keep=(), lit=True, exposure='auto', editor_exposure=1.0):
    """({resource index: dict(blob, dxbc, bindings, problems, types, kind, features)}, slot plan) for every skinned base
    pass variant of the carrier (cb.CarrierShaders), as carrier_build.build_blobs gives them for the opaque path."""
    compiled = {}
    for res in sorted(carrier.variants):
        compiled[res] = compile_variant(exported, carrier, res, os.path.join(work_root, '%s_%d' % (carrier.name, res)),
                                        lit=lit, exposure=exposure, editor_exposure=editor_exposure)
    live = sorted(set(k for dxbc, binds, problems, f in compiled.values() for k in cb.live_textures(binds)))
    plan = cb.slot_plan(exported, carrier, live, keep=keep, prefer=prefer)
    out = {}
    for res, (dxbc, binds, problems, f) in sorted(compiled.items()):
        v = carrier.variants[res]
        blob, blob_problems = (None, [])
        cat = dict(f['catalog'])
        cat.update(aliases(f['catalog']))
        if not problems:
            blob, blob_problems = shaderblob.build(carrier.shaders[res]['code'], dxbc, binds, cb.material_resource_fn(plan, v),
                                                   '%s_%s_%d' % (exported.name, carrier.name, res), catalog=cat)
            if blob is not None:
                blob_problems += check_blob(carrier.shaders[res]['code'], blob, (carrier.named, carrier.params), cat)
        out[res] = dict(blob=blob, dxbc=dxbc, bindings=binds, problems=problems + blob_problems, types=v['types'],
                        kind='base', features=dict(env=f['env'], envdir=f['envdir'], dirlight=f['dirlight'],
                                                   scene_depth=f['scene_depth'],
                                                   noise={str(k): m for k, m in sorted(f.get('noise', {}).items())}))
    return out, plan
