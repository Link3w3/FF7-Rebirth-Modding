"""AnimeShader (/Game/Shader/KadeMats/Materials/AnimeShader with MF_RebirthOfsoulsShader) as HLSL for anime_ps.

The graph, with the material's parameter defaults (no instance overrides it):
  MF: C0 = NS4_ToonLighting (Custom_0), C1 = Custom_1 (Bleach / Rebirth of Souls toon), Facing = If(saturate(
      dot(VertexNormalWS, CameraVectorWS)) >= OutlineThickness, 1, 0), M6 = C0 * (Brightness * Facing * C1),
      Emissive = M6 * Specular / EyeAdaptation, Metallic = M6 * Metal, Specular = M6, Roughness = M6 * Roughness,
      AO = AO Map * M6 * Ambient Occlusion, Normal = the Normal texture, OpacityMask = OpacityFade.
  AnimeShader: Emissive = MF.Emissive / (EyeAdaptation * EyeAdaptionMultiplier), BaseColor = MF.BaseColor (not set:
      black), OpacityMask = BaseColor texture alpha * MF.OpacityMask, the rest from the MF.
The custom nodes' code is the user's, verbatim. The two EyeAdaptation divisions keep the toon colour independent of the
editor's exposure; in the game the colour is written as it shows in the editor (the game's exposure is physical, a
division by it would blow the colour out). Texture parameters the game material has (Color, Normal) take the game
instance's textures; the KadeMats template masks (ShadowMask, FaceMaskR, HairMask A/B, RimLightMask) are drawn for
another model's layout and are off (0), the ramps (BaseMapTexture: white) are 1.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CODE0 = open(os.path.join(HERE, 'anime/hlsl/MaterialExpressionCustom_0.code.hlsl')).read()
CODE1 = open(os.path.join(HERE, 'anime/hlsl/MaterialExpressionCustom_1.code.hlsl')).read()

PARAMS = dict(
    # scalars (MF defaults)
    ShadowIntensity=0.4, MidIntensity=0.8, LitIntensity=1.1, ShadowThreshold=0.3, MidThreshold=0.65,
    SpecIntensity=1.0, SpecSharpness=16.0, SpecThreshold=0.4, SpecRampVal=0.0, SpecPower=32.0, RimStrength=0.0,
    RimPower=1.0, HairSpecIntensity=0.0, HairSpecWidth=0.0, OutlineStrength=0.0, OutlineWidth=0.0, DyeStrength=0.0,
    Brightness=1.0, OpacityFade=1.0, MaskColor=0.0, OutlineThickness=0.0, HairIntensityA=0.0, HairIntensityB=0.0,
    HairRimStrength=0.0, HairRimPower=0.0, HairShineIntensity=1.0, ShineWidth=0.15, ShineCenter=0.55,
    FaceCutoff=0.35, FaceSoftness=0.15, UseHairShine=0.0, Metal=1.0, Specular=0.7, Roughness=1.0,
    AmbientOcclusion=0.0, EyeAdaptionMultiplier=1.0,
    # vectors (rgb)
    OutlineColor=(0.0, 0.0, 0.0), HairColorA=(0.0, 0.0, 0.0), HairColorB=(0.0, 0.0, 0.0), BaseColorTint=(1.0, 1.0, 1.0),
    ShadowColorMul=(1.0, 1.0, 1.0), MidColorMul=(1.0, 1.0, 1.0), LitColorMul=(1.0, 1.0, 1.0), SpecColor=(1.0, 1.0, 1.0),
    RimColor=(1.0, 1.0, 1.0), DyeColor=(1.0, 1.0, 1.0), BaseColor2=(1.0, 1.0, 1.0), HairRimColor=(1.0, 1.0, 1.0),
    LightDirWS=(1.0, 1.0, 1.0), ViewDirWS=(1.0, 1.0, 1.0),
)

SIG0 = ('float3 NormalWS, float3 LightDirWS, float3 ViewDirWS, float3 BaseColor, float3 ShadowColorMul, float3 MidColorMul, '
        'float3 LitColorMul, float3 SpecColor, float3 RimColor, float ShadowThreshold, float MidThreshold, float SpecIntensity, '
        'float SpecSharpness, float SpecThreshold, float RimStrength, float RimPower, float3 BaseTex, float3 ShadowRampTex, '
        'float3 SpecRampTex, float2 UVs, float HairSpecIntensity, float HairSpecWidth, float OutlineStrength, float DyeStrength, '
        'float3 DyeColor, float DyeMask, float3 ShadowRampRGB, float SpecRampVal')
SIG1 = ('float3 BaseColor, float3 NormalWS, float3 LightDirWS, float3 ViewDirWS, float3 DyeColor, float3 DyeMask, '
        'float DyeStrength, float ShadowThreshold, float MidThreshold, float ShadowIntensity, float MidIntensity, '
        'float LitIntensity, float SpecIntensity, float SpecPower, float RimStrength, float RimPower, float OutlineStrength, '
        'float ShadowMask, float3 OutlineColor, float3 RimMask, float OutlineWidth, float3 HairColorA, float3 HairColorB, '
        'float HairIntensityA, float HairIntensityB, float HairMaskA_input, float HairMaskB_input, float3 HairRimColor, '
        'float HairRimStrength, float HairRimPower, float3 RimColor, float HairShineIntensity, float ShineWidth, '
        'float ShineCenter, float FaceSoftness, float FaceCutoff, float FaceMaskR, float UseHairShine')


def _f(v):
    return repr(float(v)) if not isinstance(v, tuple) else 'float3(%s)' % ', '.join(repr(float(x)) for x in v)


def material(slots, params=None):
    p = dict(PARAMS)
    p.update(params or {})
    defs = '\n'.join('static const %s P_%s = %s;' % ('float3' if isinstance(v, tuple) else 'float', k, _f(v)) for k, v in sorted(p.items()))
    color = 'Material_Texture2D_%d' % slots['Color'][0]
    normal = 'Material_Texture2D_%d' % slots['Normal'][0]
    return r'''// ---- AnimeShader (KadeMats), parameters at their material defaults ----
%(defs)s

float3 CustomExpression0(%(sig0)s)
{
%(code0)s
}

float3 CustomExpression1(%(sig1)s)
{
%(code1)s
}

float3 MaterialTangentNormal(FMaterialInput M)
{
    // 'Normal' texture parameter (SAMPLERTYPE_Normal): the game instance's normal map, BC5
    float2 XY = %(normal)s.SampleBias(TEXTURE_SAMPLER, M.UV0, M.MipBias).rg * 2.0 - 1.0;
    return float3(XY, sqrt(max(0.0, 1.0 - dot(XY, XY))));
}

FMaterialOutput EvaluateMaterial(FMaterialInput M)
{
    // 'BaseColor' texture parameter: the game instance's Color texture
    const float4 BaseColorTex = %(color)s.SampleBias(TEXTURE_SAMPLER, M.UV0, M.MipBias);
    const float3 ShadowRampRGB = float3(1.0, 1.0, 1.0);         // ShadowRampSampler: BaseMapTexture (white)
    const float3 SpecRampRGB = float3(1.0, 1.0, 1.0);           // SpecRampSampler: BaseMapTexture (white)
    const float ShadowMaskR = 0.0, ShadowMaskG = 0.0;           // ShadowMask template: off
    const float3 RimLightMask = float3(0.0, 0.0, 0.0);          // RimLightMask template: off
    const float HairMaskA = 0.0, HairMaskB = 0.0, FaceMask = 0.0;
    const float3 AOMap = float3(1.0, 1.0, 1.0);                 // AO Map: BaseAOTex (white)

    const float3 BaseTex = BaseColorTex.rgb * P_BaseColorTint;                                   // Multiply_5
    const float3 ShadowRampTex = 1.0 - lerp(1.0 - ShadowRampRGB, P_BaseColor2, P_MaskColor);       // OneMinus_2(Lerp_1)
    const float3 C0 = CustomExpression0(M.WorldNormal, P_LightDirWS, P_ViewDirWS, BaseColorTex.rgb,
        P_ShadowColorMul, P_MidColorMul, P_LitColorMul, P_SpecColor, P_RimColor, P_ShadowThreshold, P_MidThreshold,
        P_SpecIntensity, P_SpecSharpness, P_SpecThreshold, P_RimStrength, P_RimPower, BaseTex, ShadowRampTex, SpecRampRGB,
        M.UV0, P_HairSpecIntensity, P_HairSpecWidth, P_OutlineStrength, P_DyeStrength, P_DyeColor, BaseColorTex.r,
        ShadowRampRGB, P_SpecRampVal);
    const float3 C1 = CustomExpression1(BaseColorTex.rgb, M.WorldNormal, P_LightDirWS, M.CameraVector, P_DyeColor,
        ShadowRampRGB, P_DyeStrength, P_ShadowThreshold, P_MidThreshold, P_ShadowIntensity, P_MidIntensity,
        P_LitIntensity, P_SpecIntensity, P_SpecPower, P_RimStrength, P_RimPower, P_OutlineStrength,
        max(ShadowMaskR, ShadowMaskG), P_OutlineColor, RimLightMask, P_OutlineWidth, P_HairColorA, P_HairColorB,
        P_HairIntensityA, P_HairIntensityB, HairMaskA, HairMaskB, P_HairRimColor, P_HairRimStrength, P_HairRimPower,
        P_HairRimColor, P_HairShineIntensity, P_ShineWidth, P_ShineCenter, P_FaceSoftness, P_FaceCutoff, FaceMask,
        P_UseHairShine);
    const float Facing = (saturate(dot(M.VertexNormal, M.CameraVector)) >= P_OutlineThickness) ? 1.0 : 0.0;   // If_0
    const float3 M6 = C0 * ((P_Brightness * Facing) * C1);                                                 // Multiply_6

    FMaterialOutput O;
    O.BaseColor = float3(0.0, 0.0, 0.0);
    O.Metallic = (M6 * P_Metal).r;
    O.Roughness = (M6 * P_Roughness).r;
    O.AmbientOcclusion = ((AOMap * M6) * P_AmbientOcclusion).r;
    O.Emissive = (M6 * P_Specular) / P_EyeAdaptionMultiplier;
    O.WorldNormal = M.WorldNormal;
    return O;
}
''' % dict(defs=defs, sig0=SIG0, sig1=SIG1, code0=CODE0, code1=CODE1, color=color, normal=normal)
