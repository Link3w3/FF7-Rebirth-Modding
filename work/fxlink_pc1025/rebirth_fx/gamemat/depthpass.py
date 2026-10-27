"""The game's depth-only and shadow depth pixel shaders around an editor material, for masked materials on a carrier
whose own depth and shadow shaders cut out with its coverage texture (RMI_Surface_*Coverage*).

Without these, a masked material's cut-outs exist in the base pass only: the depth pre-pass (the carrier's own shader,
coverage texture white) writes the whole card, the base pass then draws nothing where the material cuts out (black
holes where the scene behind should show), and shadows are cast by the whole card. With them, every pass the carrier
draws cuts out exactly where the material does (the same code on the same inputs: same discard per pixel).

  depth    TDepthOnlyPS{No,With}DynamicCoverage   the base pass interpolants; SV_Target0 = 0
  shadow   TShadowDepthPS NonPerspectiveCorrect /  + PixelPosition (TEXCOORD7, translated world: the shadow view's
           OnePassPointLight                       SvPosition does not give the world position); SV_Target0 = 0
  shadow_pc TShadowDepthPS PerspectiveCorrect      + ShadowDepth (TEXCOORD6); SV_Depth = saturate(ShadowParams.w * it)

The carrier's own coverage tests are kept as the carrier does them (read out of its shaders, fcwd_197/30/277):
depth-only: dynamic coverage and the coverage texture against the blue noise (as the base pass); shadows: dynamic
coverage against a 2x2 checker, the coverage texture at 0.5. A material cut out the game's way (GAME_DITHERED_MASK, as
its base pass) is cut out the same way here: its mask against the blue noise in the depth pass, at 0.5 in the shadows
(the game's own coverage shaders, fcwd_197/30 and Hair_Wide 272/119).
"""
from . import basepass

# the vertex factory's part of the base pass (texture coordinates, tangent basis), the same in every pass
_start = basepass.TEMPLATE.index("    // the vertex factory's part")
_end = basepass.TEMPLATE.index('    MaterialParameters.PrimitiveId = 0;\n') + len('    MaterialParameters.PrimitiveId = 0;\n')
VF_PART = basepass.TEMPLATE[_start:_end]

HEADER = r'''// %(title)s
// The game's %(pass_name)s for %(carrier)s (%(variant)s) around the editor's own material code.
#define GAME_HAS_TEXCOORD1 %(has_tc1)d
#define GAME_COVERAGE_TEXTURE %(coverage)d
#define GAME_PERSPECTIVE_CORRECT %(perspective)d
#define GAME_DITHERED_MASK %(dithered)d

#include "Engine/Private/Common.ush"

static float4 GameBlueNoise = 0.5;
#define GAME_BLUE_NOISE GameBlueNoise
#define GAME_HAIR_STRAND_NOISE GameBlueNoise.x

#include "Engine/Generated/Material.ush"

%(coverage_decl)s
'''

DEPTH = HEADER + r'''
struct FGameDepthInterpolants
{
    float4 TangentToWorld0 : TEXCOORD10;
    float4 TangentToWorld2 : TEXCOORD11;
    float4 TexCoords0 : TEXCOORD0;
#if GAME_HAS_TEXCOORD1
    float4 TexCoords1 : TEXCOORD1;
#endif
    nointerpolation float ConstantContext : CONSTANT_CONTEXT0;
};

void MainPS(FGameDepthInterpolants In,
    float4 SvPosition : SV_Position,
    bool bIsFrontFace : SV_IsFrontFace,
    out float4 OutColor : SV_Target0)
{
    ResolvedView = ResolveView();

    const uint Slice = ((uint)round(In.ConstantContext) + (View.StateFrameIndex & 7u)) & 63u;
    const float4 BlueNoise = View.SpatiotemporalBlueNoiseVolumeTexture.Load(int4(int(SvPosition.x) & 127, int(SvPosition.y) & 127, int(Slice), 0));
    GameBlueNoise = BlueNoise;
    {
        // the carrier's own coverage test, as its base pass does it
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

''' + VF_PART + r'''
    // the material's own cut-out, the same test on the same inputs as its base pass
    FPixelMaterialInputs PixelMaterialInputs;
    CalcMaterialParameters(MaterialParameters, PixelMaterialInputs, SvPosition, bIsFrontFace);
#if MATERIALBLENDING_MASKED
#if GAME_DITHERED_MASK
    if (!(GetMaterialMaskInputRaw(PixelMaterialInputs) > BlueNoise.x * 0.99609375 + 0.001953125))
        discard;
#else
    GetMaterialCoverageAndClipping(MaterialParameters, PixelMaterialInputs);
#endif
#endif
    OutColor = 0;
}
'''

SHADOW = HEADER + r'''
#if GAME_PERSPECTIVE_CORRECT
cbuffer ShadowDepthPass : register(b%(shadow_pass_register)d)
{
    float4 ShadowDepthPass_ShadowParams : packoffset(c17);
};
#endif

struct FGameShadowInterpolants
{
    float4 TangentToWorld0 : TEXCOORD10;
    float4 TangentToWorld2 : TEXCOORD11;
    float4 TexCoords0 : TEXCOORD0;
#if GAME_HAS_TEXCOORD1
    float4 TexCoords1 : TEXCOORD1;
#endif
    nointerpolation float ConstantContext : CONSTANT_CONTEXT0;
#if GAME_PERSPECTIVE_CORRECT
    float ShadowDepth : TEXCOORD6;
#endif
    float3 PixelPosition : TEXCOORD7;
};

void MainPS(FGameShadowInterpolants In,
    float4 SvPosition : SV_Position,
    out float4 OutColor : SV_Target0
#if GAME_PERSPECTIVE_CORRECT
    , out float OutDepth : SV_Depth
#endif
    )
{
    ResolvedView = ResolveView();
    {
        // the carrier's own coverage test in shadows: dynamic coverage against a 2x2 checker, its coverage texture at 0.5
        const bool bOdd = ((int(SvPosition.x) ^ int(SvPosition.y)) & 1) != 0;
        bool bKeep = Primitive.DynamicCoverage > (bOdd ? 0.666015625 : 0.333984375);
#if GAME_COVERAGE_TEXTURE
        bKeep = bKeep && GameCoverageTexture.SampleBias(View.SharedAnisotropic4XWrappedSampler, In.TexCoords0.xy, 0.0).r >= 0.5;
#endif
        if (!bKeep)
            discard;
    }

''' + VF_PART + r'''
    // the material's own cut-out; the world position comes from the interpolant (the shadow view's SvPosition does not
    // give it), as the engine's shadow depth pass does it
    FPixelMaterialInputs PixelMaterialInputs;
    {
        const float4 ScreenPosition = SvPositionToResolvedScreenPosition(SvPosition);
        const float3 TranslatedWorld = In.PixelPosition.xyz;
        CalcMaterialParametersEx(MaterialParameters, PixelMaterialInputs, SvPosition, ScreenPosition, true, TranslatedWorld, TranslatedWorld);
    }
#if GAME_DITHERED_MASK && MATERIALBLENDING_MASKED
    // the game's coverage materials cast shadows where they are covered at least half
    if (!(GetMaterialMaskInputRaw(PixelMaterialInputs) >= 0.5))
        discard;
#else
    GetMaterialClippingShadowDepth(MaterialParameters, PixelMaterialInputs);
#endif
    OutColor = 0;
#if GAME_PERSPECTIVE_CORRECT
    OutDepth = saturate(ShadowDepthPass_ShadowParams.w * In.ShadowDepth);
#endif
}
'''

PASS_NAMES = {'depth': 'depth-only pass', 'shadow': 'shadow depth pass', 'shadow_pc': 'perspective-correct shadow depth pass'}


def kind_of(types):
    """'depth', 'shadow', 'shadow_pc' or None for a carrier pixel shader's type names."""
    if any(t.startswith('TDepthOnlyPS') for t in types):
        return 'depth'
    if any(t.startswith('TShadowDepthPSPixelShadowDepth_PerspectiveCorrect') for t in types):
        return 'shadow_pc'
    if any(t.startswith('TShadowDepthPSPixelShadowDepth_') for t in types):
        return 'shadow'
    return None


def source(kind, title, carrier, variant, has_tc1, coverage_texture, registers, dithered=False):
    decl = 'Texture2D GameCoverageTexture;' if coverage_texture else ''
    values = dict(title=title, carrier=carrier, variant=variant, has_tc1=1 if has_tc1 else 0, dithered=1 if dithered else 0,
                  coverage=1 if coverage_texture else 0, coverage_decl=decl, pass_name=PASS_NAMES[kind],
                  perspective=1 if kind == 'shadow_pc' else 0, shadow_pass_register=registers.get('ShadowDepthPass', 0))
    if kind == 'depth':
        return DEPTH % values
    if kind in ('shadow', 'shadow_pc'):
        if kind == 'shadow_pc' and 'ShadowDepthPass' not in registers:
            raise ValueError('%s: the perspective-correct shadow shader has no ShadowDepthPass buffer' % carrier)
        return SHADOW % values
    raise ValueError(kind)
