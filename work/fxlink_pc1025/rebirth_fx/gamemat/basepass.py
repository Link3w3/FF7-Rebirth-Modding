"""The game base pass pixel shader around an editor material: the carrier's inputs (GPU skin vertex factory interpolants)
become the engine's FMaterialPixelParameters, the material's own CalcMaterialParameters / GetMaterial* run as the engine
compiled them, and the GBuffer is written the way the carrier writes it (SQEX's deferred base pass, 7 targets: see the
carrier analysis in anime/std_93.txt).

The GBuffer is the one of the game's surface family the material is drawn as (GAME_FAMILY: the shading model the game's
deferred lighting reads, the reflectance it encodes in the normal target's alpha, its specular and custom data), as the
game's own RM_Surface instances of that family write it (read out of their pixel shaders: Saved/RebirthGameMaterials/
analysis): 1 standard, 3 skin, 5 subsurface, 7 hair, 8 fabric, 9 eye. GAME_DITHERED_MASK: a masked material's own mask is cut out against the
blue noise, as the game's coverage materials cut out theirs (soft edges the temporal AA resolves), not at a clip value.
"""

FAMILIES = {'standard': 1, 'skin': 3, 'subsurface': 5, 'hair': 7, 'fabric': 8, 'eye': 9}

TEMPLATE = r'''// %(title)s
// The game's base pass for %(carrier)s (%(variant)s) around the editor's own material code.
#define GAME_HAS_TEXCOORD1 %(has_tc1)d
#define GAME_DYNAMIC_COVERAGE %(dyncov)d
#define GAME_COVERAGE_TEXTURE %(coverage)d
#define GAME_FAMILY %(family)d
#define GAME_DITHERED_MASK %(dithered)d

#include "Engine/Private/Common.ush"

// the blue noise the game's surfaces dither with, for the material's code (set in MainPS before the material runs):
// GAME_BLUE_NOISE; GAME_HAIR_STRAND_NOISE the one the game's cylindrical hair normal breaks its views along the strand with
static float4 GameBlueNoise = 0.5;
#define GAME_BLUE_NOISE GameBlueNoise
#define GAME_HAIR_STRAND_NOISE GameBlueNoise.x

#include "Engine/Generated/Material.ush"

struct FGameBasePassInterpolants
{
    float4 TangentToWorld0 : TEXCOORD10;
    float4 TangentToWorld2 : TEXCOORD11;
    float4 TexCoords0 : TEXCOORD0;
#if GAME_HAS_TEXCOORD1
    float4 TexCoords1 : TEXCOORD1;
#endif
    nointerpolation float ConstantContext : CONSTANT_CONTEXT0;
    float4 CurrentClip : CURRENT_CLIP_SPACE_POSITION0;
    float4 PreviousClip : PREVIOUS_CLIP_SPACE_POSITION0;
};

%(coverage_decl)s

// the carrier's GBuffer normal encoding: n * 0.5 + 0.5, dithered by triangular blue noise away from the extremes
float3 GameEncodeNormalDithered(float3 N, float3 Dither, float Threshold, float Scale)
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

float GameTriangularNoise(float U)
{
    float X = U * 2.0 - 1.0;
    return sign(X) * (1.0 - sqrt(1.0 - abs(X)));
}

void MainPS(FGameBasePassInterpolants In,
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
    // the view the material reads (ResolvedView: world position, camera vector, culling sign of two-sided normals),
    // set first as the engine's base pass does
    ResolvedView = ResolveView();

    const uint Slice = ((uint)round(In.ConstantContext) + (View.StateFrameIndex & 7u)) & 63u;
    const float4 BlueNoise = View.SpatiotemporalBlueNoiseVolumeTexture.Load(int4(int(SvPosition.x) & 127, int(SvPosition.y) & 127, int(Slice), 0));
    GameBlueNoise = BlueNoise;

#if GAME_DYNAMIC_COVERAGE || GAME_COVERAGE_TEXTURE
    {
        // the carrier's own coverage test (distance fade-out dithering, and its coverage texture where it has one)
        bool bKeep = Primitive.DynamicCoverage > BlueNoise.w * 0.99609375 + 0.001953125;
#if GAME_COVERAGE_TEXTURE
        if (bKeep)
        {
            const float Coverage = GameCoverageTexture.SampleBias(View.SharedAnisotropic4XWrappedSampler, In.TexCoords0.xy, View.TemporalSamplerBias.w).r;
            bKeep = Coverage > BlueNoise.x * 0.99609375 + 0.001953125;
        }
#endif
        if (!bKeep)
            discard;
    }
#endif

    // the vertex factory's part (GPU skin): texture coordinates and the tangent basis
    FMaterialPixelParameters MaterialParameters = MakeInitializedMaterialPixelParameters();
#if NUM_TEX_COORD_INTERPOLATORS
    MaterialParameters.TexCoords[0] = In.TexCoords0.xy;
#endif
#if NUM_TEX_COORD_INTERPOLATORS > 1
    MaterialParameters.TexCoords[1] = In.TexCoords0.zw;
#endif
#if NUM_TEX_COORD_INTERPOLATORS > 2
#if GAME_HAS_TEXCOORD1
    MaterialParameters.TexCoords[2] = In.TexCoords1.xy;
#else
    MaterialParameters.TexCoords[2] = In.TexCoords0.xy;
#endif
#endif
#if NUM_TEX_COORD_INTERPOLATORS > 3
#if GAME_HAS_TEXCOORD1
    MaterialParameters.TexCoords[3] = In.TexCoords1.zw;
#else
    MaterialParameters.TexCoords[3] = In.TexCoords0.zw;
#endif
#endif
    MaterialParameters.VertexColor = 1;
    const half3 TangentToWorld0 = In.TangentToWorld0.xyz;
    const half4 TangentToWorld2 = In.TangentToWorld2;
    MaterialParameters.UnMirrored = TangentToWorld2.w;
    MaterialParameters.TangentToWorld = half3x3(TangentToWorld0, cross(TangentToWorld2.xyz, TangentToWorld0) * TangentToWorld2.w, TangentToWorld2.xyz);
    MaterialParameters.PrimitiveId = 0;

    // the material, as the editor compiled it
    FPixelMaterialInputs PixelMaterialInputs;
    CalcMaterialParameters(MaterialParameters, PixelMaterialInputs, SvPosition, bIsFrontFace);
#if MATERIALBLENDING_MASKED
#if GAME_DITHERED_MASK
    // the material's own mask, cut out as the game's coverage materials cut theirs: against the blue noise
    if (!(GetMaterialMaskInputRaw(PixelMaterialInputs) > BlueNoise.x * 0.99609375 + 0.001953125))
        discard;
#else
    GetMaterialCoverageAndClipping(MaterialParameters, PixelMaterialInputs);
#endif
#endif

    float3 BaseColor = GetMaterialBaseColor(PixelMaterialInputs);
    float Metallic = GetMaterialMetallic(PixelMaterialInputs);
    float Specular = GetMaterialSpecular(PixelMaterialInputs);
    float Roughness = GetMaterialRoughness(PixelMaterialInputs);
    float AO = GetMaterialAmbientOcclusion(PixelMaterialInputs);
#if GAMESH_EMISSIVE_SCREEN
    // a material that makes up for the camera's exposure itself (EyeAdaptationLookup): shown as the editor shows it at
    // a fixed exposure (GAMESH_EYE_ADAPTATION_CONST), the same on screen in bright and dark places (the game's
    // tonemapper undoes its own pre-exposure: scene colour * EyeAdaptation / PreExposure)
    float3 Emissive = GetMaterialEmissive(PixelMaterialInputs) * (GAMESH_EYE_ADAPTATION_CONST * GAME_EMISSIVE_SCALE);
#else
    // the game's own emissive carriers scale emissive by the camera's exposure (View.PreExposure), as the engine does:
    // the glow keeps its strength against the scene in bright and dark places alike
    float3 Emissive = GetMaterialEmissive(PixelMaterialInputs) * (View.PreExposure * GAME_EMISSIVE_SCALE);
#endif
    float3 N = normalize(MaterialParameters.WorldNormal);
#if MATERIAL_SHADINGMODEL_UNLIT && MATERIAL_SINGLE_SHADINGMODEL
    // unlit: only the emissive colour shows (no base colour, no reflectance)
    BaseColor = 0;
    Metallic = 0;
    Specular = 0;
    Roughness = 1;
#endif
    // the family's GBuffer (its carrier's own pixel shader writes these)
#if GAME_FAMILY == 7
    // hair (RMI_Surface_Hair_Wide): the game's hair lighting, reflectance 0.0465 (in the normal target's alpha), no
    // metal or specular; custom data: the bent normal (world, * 0.5 + 0.5: the material's Rebirth Hair Data)
    const float ModelParam = 0.684779345989227294921875;
    const float GameSpecular = 0.0;
    Metallic = 0.0;
    float4 Custom = 0.0;
#if NUM_MATERIAL_OUTPUTS_REBIRTHHAIRBRIDGE > 0
    Custom = float4(saturate(RebirthHairBridge0(MaterialParameters)), 0.0);
#endif
#elif GAME_FAMILY == 3
    // skin (RMI_Surface_Skin_*): the game's skin lighting, reflectance 0.0465, specular 0.15, no metal; custom data x: the
    // pores (the material's Rebirth Surface Data diffusion input; else Remake's skin reflectance F0 = 0.0325 * pores,
    // its Specular input being sqrt(F0 / 0.16))
    const float ModelParam = 0.684779345989227294921875;
    const float GameSpecular = 0.15000000596046448;
    Metallic = 0.0;
#if NUM_MATERIAL_OUTPUTS_REBIRTHSURFACEBRIDGE > 3
    const float Pores = saturate(RebirthSurfaceBridge3(MaterialParameters));
#else
    const float Pores = saturate(0.16 * Specular * Specular / 0.0325);
#endif
    float4 Custom = float4(Pores, 0.0, 0.0, 0.0);
#elif GAME_FAMILY == 8
    // fabric (RMI_Surface_Fabric_*): the game's cloth lighting, reflectance 0.0672, at least 0.5 rough, no metal or
    // specular; custom data x: the diffusion (the material's Rebirth Surface Data diffusion input, else none)
    const float ModelParam = 0.742264926433563232421875;
    const float GameSpecular = 0.0;
    Metallic = 0.0;
    Roughness = max(0.5, Roughness);
#if NUM_MATERIAL_OUTPUTS_REBIRTHSURFACEBRIDGE > 3
    float4 Custom = float4(saturate(RebirthSurfaceBridge3(MaterialParameters)), 0.0, 0.0, 0.0);
#else
    float4 Custom = 0.0;
#endif
#elif GAME_FAMILY == 5
    // subsurface (RMI_Surface_Subsurface_*): the game's subsurface lighting, reflectance 0.04; its specular target holds
    // the scattering distribution (the material's Distribution, 1 where it has none: Remake's default), no custom data
    const float ModelParam = 0.6666666269302368;
#if GAME_MATERIAL_HAS_DISTRIBUTION
    const float GameSpecular = saturate(PixelMaterialInputs.Distribution);
#else
    const float GameSpecular = 1.0;
#endif
    float4 Custom = 0.0;
#elif GAME_FAMILY == 9
    // eye (RMI_Surface_Eye_*): the game's eye lighting, reflectance 0.0387; its metallic target holds the sclera mask, its
    // specular the iris occlusion, its AO the radial distance, its custom data the radial direction and the packed iris
    // normal, its second normal the inner one (the material's Recovered Rebirth Eye Surface, all six); the material's own
    // occlusion darkens its colour instead (the game's eye has no occlusion target of its own)
#if NUM_MATERIAL_OUTPUTS_REBIRTHEYEBRIDGE < 6
#error the eye family needs the material's Recovered Rebirth Eye Surface (six outputs)
#endif
    const float ModelParam = 0.645419657230377197265625;
    const float3 EyeInner = normalize(RebirthEyeBridge0(MaterialParameters));
    BaseColor *= saturate(AO);
    Metallic = saturate(RebirthEyeBridge3(MaterialParameters));
    const float GameSpecular = saturate(RebirthEyeBridge4(MaterialParameters));
    AO = saturate(RebirthEyeBridge5(MaterialParameters));
    float4 Custom = float4(saturate(RebirthEyeBridge1(MaterialParameters) * 0.5 + 0.5), saturate(RebirthEyeBridge2(MaterialParameters)));
#define GAME_SECOND_NORMAL EyeInner
#else
    // standard (RMI_Surface_Standard_*): reflectance 0.04, custom data: film structure 0.4
    const float ModelParam = 0.6666666269302368;
    const float GameSpecular = 0.0;
    float4 Custom = float4(0.0, 0.4000000059604645, 0.0, 0.0);
    // the game's GBuffer has no specular input (its non-metal reflectance is fixed, GAME_DIELECTRIC_F0): a material with
    // no base colour (its look all in emissive) keeps the editor's reflectance F0 = 0.08 * Specular * (1 - Metallic)
    // as a black metal of that reflectance, so the scene's lights add to it what they add in the editor
    if (max(BaseColor.r, max(BaseColor.g, BaseColor.b)) <= 0.0)
        Metallic = saturate(1.0 - 0.08 * Specular * (1.0 - saturate(Metallic)) / GAME_DIELECTRIC_F0);
#endif

    const float3 Dither = float3(GameTriangularNoise(BlueNoise.x), GameTriangularNoise(BlueNoise.y), GameTriangularNoise(BlueNoise.z));

    // specular anti-aliasing of the roughness, as the carrier
    const float3 Ndx = ddx_fine(N);
    const float3 Ndy = ddy_fine(N);
    const float Variance = min((dot(Ndx, Ndx) + dot(Ndy, Ndy)) * 0.15915493667125702, 0.18000000715255737);
    const float R = saturate(Roughness);
    const float FilteredRoughness = sqrt(saturate(Variance + R * R));

    const float ShadingModelBits = float(((Primitive.PixelAttribute << 4) & 48u) | (uint)GAME_FAMILY) * 0.003921568859368563;

    float2 Velocity = 0;
    if (In.CurrentClip.w != 0.0)
    {
        const float2 Current = In.CurrentClip.xy / In.CurrentClip.w;
        const float2 Previous = In.PreviousClip.xy / In.PreviousClip.w;
        const float2 V = clamp((View.TemporalAAJitter.zw - View.TemporalAAJitter.xy) + Current - Previous, -2.0, 2.0);
        Velocity = V * 0.24998855590820312 + 0.5000076293945312;
    }

    OutTarget0 = float4(max(Emissive, 0.0), 0.0);
    OutTarget1 = float4(GameEncodeNormalDithered(N, Dither, -0.9980449676513672, 0.0009775171056389809), ModelParam);
    OutTarget2 = float4(saturate(Metallic), GameSpecular, FilteredRoughness, ShadingModelBits);
    OutTarget3 = float4(saturate(BaseColor), saturate(AO));
    OutTarget4 = Custom;
#if defined(GAME_SECOND_NORMAL)
    OutTarget5 = float4(GameEncodeNormalDithered(GAME_SECOND_NORMAL, Dither, -0.9921568632125854, 0.003921568859368563), 0.0);
#else
    OutTarget5 = float4(GameEncodeNormalDithered(N, Dither, -0.9921568632125854, 0.003921568859368563), 0.0);
#endif
    OutTarget6 = float4(Velocity, 0.0, 0.0);
}
'''


def exposure_defines(code, exposure='auto', editor_exposure=1.0):
    """How the material's emissive meets the game's camera exposure.
    'engine': as the engine does it, emissive * View.PreExposure (scene light, like the game's own glows) and
              EyeAdaptationLookup() = View.PreExposure (the game's base pass has no eye adaptation texture);
    'editor': as the editor shows it at the exposure `editor_exposure`, the same on screen everywhere
              (EyeAdaptationLookup() = editor_exposure, emissive * editor_exposure): a material that divides by the
              exposure once looks the same at any value; one that divides twice (AnimeShader) is brighter at a lower one;
    'auto':   'editor' for a material that makes up for the exposure itself (it calls EyeAdaptationLookup: anime and
              other screen-coloured looks), 'engine' otherwise."""
    if exposure == 'auto':
        exposure = 'editor' if 'EyeAdaptationLookup()' in code else 'engine'
    if exposure == 'editor':
        return exposure, {'GAMESH_EYE_ADAPTATION_CONST': float(editor_exposure), 'GAMESH_EMISSIVE_SCREEN': 1}
    if exposure == 'engine':
        return exposure, {'GAMESH_EYE_ADAPTATION_PREEXPOSURE': 1, 'GAMESH_EMISSIVE_SCREEN': 0}
    raise ValueError('exposure: auto, engine or editor, not %r' % exposure)


def family_id(family):
    """GAME_FAMILY of a family name ('standard', 'skin', 'hair', 'fabric') or id."""
    if isinstance(family, int):
        if family not in FAMILIES.values():
            raise ValueError('no game surface family %d' % family)
        return family
    return FAMILIES[family or 'standard']


def source(title, carrier, variant, has_tc1, dynamic_coverage, coverage_texture, family='standard', dithered=False):
    decl = 'Texture2D GameCoverageTexture;' if coverage_texture else ''
    return TEMPLATE % dict(title=title, carrier=carrier, variant=variant, has_tc1=1 if has_tc1 else 0,
                           dyncov=1 if dynamic_coverage else 0, coverage=1 if coverage_texture else 0, coverage_decl=decl,
                           family=family_id(family), dithered=1 if dithered else 0)


# defines of the shader itself (the engine's for a deferred SM5 base pass pixel shader compiled by its D3D backend)
BASE_DEFINES = {
    'PIXELSHADER': 1, 'SM5_PROFILE': 1, 'COMPILER_HLSL': 1, 'COMPILER_DXC': 1,
    'SHADING_PATH_DEFERRED': 1, 'SHADING_PATH_MOBILE': 0, 'PLATFORM_SUPPORTS_SRV_UB': 1,
    'COMPILE_SHADERS_FOR_DEVELOPMENT': 0, 'GAME_EMISSIVE_SCALE': 1.0, 'GAME_DIELECTRIC_F0': 0.04,
    'VF_SUPPORTS_PRIMITIVE_SCENE_DATA': 0, 'GPU_SKINNED_MESH_FACTORY': 1, 'NUM_MATERIAL_OUTPUTS_GETBENTNORMAL': 0,
    'COMPILER_SUPPORTS_ATTRIBUTES': 1, 'SUPPORTS_INDEPENDENT_SAMPLERS': 1,
    'HAS_PRIMITIVE_UNIFORM_BUFFER': 1,
}
