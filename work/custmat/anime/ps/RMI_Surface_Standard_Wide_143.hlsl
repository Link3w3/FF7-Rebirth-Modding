// AnimeShader (KadeMats) on RMI_Surface_Standard_Wide
// Generated for the game's RMI_Surface_Standard_Wide base pass (TBasePassPSWithDynamicCoverageFNoLightMapPolicy): inputs, outputs and resource slots are the carrier's.
#define HAS_TEXCOORD1 0
#define HAS_DYNAMIC_COVERAGE 1
#define HAS_COVERAGE 0

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
Texture2D<float4> Material_Texture2D_0 : register(t1);    // Color
Texture2D<float4> Material_Texture2D_1 : register(t2);    // Metallic
Texture2D<float4> Material_Texture2D_2 : register(t3);    // Normal
Texture2D<float4> Material_Texture2D_3 : register(t4);    // Roughness
Texture2D<float4> Material_Texture2D_4 : register(t5);    // Occlusion
Texture2D<float4> Material_Texture2D_13 : register(t6);    // WideOcclusion

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

// ---- AnimeShader (KadeMats), parameters at their material defaults ----
static const float P_AmbientOcclusion = 0.0;
static const float3 P_BaseColor2 = float3(1.0, 1.0, 1.0);
static const float3 P_BaseColorTint = float3(1.0, 1.0, 1.0);
static const float P_Brightness = 1.0;
static const float3 P_DyeColor = float3(1.0, 1.0, 1.0);
static const float P_DyeStrength = 0.0;
static const float P_EyeAdaptionMultiplier = 1.0;
static const float P_FaceCutoff = 0.35;
static const float P_FaceSoftness = 0.15;
static const float3 P_HairColorA = float3(0.0, 0.0, 0.0);
static const float3 P_HairColorB = float3(0.0, 0.0, 0.0);
static const float P_HairIntensityA = 0.0;
static const float P_HairIntensityB = 0.0;
static const float3 P_HairRimColor = float3(1.0, 1.0, 1.0);
static const float P_HairRimPower = 0.0;
static const float P_HairRimStrength = 0.0;
static const float P_HairShineIntensity = 1.0;
static const float P_HairSpecIntensity = 0.0;
static const float P_HairSpecWidth = 0.0;
static const float3 P_LightDirWS = float3(1.0, 1.0, 1.0);
static const float3 P_LitColorMul = float3(1.0, 1.0, 1.0);
static const float P_LitIntensity = 1.1;
static const float P_MaskColor = 0.0;
static const float P_Metal = 1.0;
static const float3 P_MidColorMul = float3(1.0, 1.0, 1.0);
static const float P_MidIntensity = 0.8;
static const float P_MidThreshold = 0.65;
static const float P_OpacityFade = 1.0;
static const float3 P_OutlineColor = float3(0.0, 0.0, 0.0);
static const float P_OutlineStrength = 0.0;
static const float P_OutlineThickness = 0.0;
static const float P_OutlineWidth = 0.0;
static const float3 P_RimColor = float3(1.0, 1.0, 1.0);
static const float P_RimPower = 1.0;
static const float P_RimStrength = 0.0;
static const float P_Roughness = 1.0;
static const float3 P_ShadowColorMul = float3(1.0, 1.0, 1.0);
static const float P_ShadowIntensity = 0.4;
static const float P_ShadowThreshold = 0.3;
static const float P_ShineCenter = 0.55;
static const float P_ShineWidth = 0.15;
static const float3 P_SpecColor = float3(1.0, 1.0, 1.0);
static const float P_SpecIntensity = 1.0;
static const float P_SpecPower = 32.0;
static const float P_SpecRampVal = 0.0;
static const float P_SpecSharpness = 16.0;
static const float P_SpecThreshold = 0.4;
static const float P_Specular = 0.7;
static const float P_UseHairShine = 0.0;
static const float3 P_ViewDirWS = float3(1.0, 1.0, 1.0);

float3 CustomExpression0(float3 NormalWS, float3 LightDirWS, float3 ViewDirWS, float3 BaseColor, float3 ShadowColorMul, float3 MidColorMul, float3 LitColorMul, float3 SpecColor, float3 RimColor, float ShadowThreshold, float MidThreshold, float SpecIntensity, float SpecSharpness, float SpecThreshold, float RimStrength, float RimPower, float3 BaseTex, float3 ShadowRampTex, float3 SpecRampTex, float2 UVs, float HairSpecIntensity, float HairSpecWidth, float OutlineStrength, float DyeStrength, float3 DyeColor, float DyeMask, float3 ShadowRampRGB, float SpecRampVal)
{
// ------------------------------------------------------------
// 1. Base color & normals
// ------------------------------------------------------------
float3 BC   = BaseColor;
float3 Nrm  = normalize(NormalWS);
float3 Ldir = normalize(-LightDirWS);
float3 Vdir = normalize(ViewDirWS);

// ------------------------------------------------------------
// 2. Dye application (Storm-style)
// ------------------------------------------------------------
float3 DyedBC = lerp(BC, BC * DyeColor, saturate(DyeMask * DyeStrength));
BC = DyedBC;

// ------------------------------------------------------------
// 3. NdotL
// ------------------------------------------------------------
float NdotL = saturate(dot(Nrm, Ldir));

// ------------------------------------------------------------
// 4. Storm 4–style 3-band toon via ramp
// ------------------------------------------------------------
float ShadowMul = ShadowRampRGB.r;
float MidMul    = ShadowRampRGB.g;
float LitMul    = ShadowRampRGB.b;

float3 ColShadow = BC * ShadowMul;
float3 ColMid    = BC * MidMul;
float3 ColLit    = BC * LitMul;

float3 ToonCol = ColShadow;

if (NdotL >= ShadowThreshold && NdotL < MidThreshold)
    ToonCol = ColMid;

if (NdotL >= MidThreshold)
    ToonCol = ColLit;

// ------------------------------------------------------------
// 5. Specular band (Storm-style)
// ------------------------------------------------------------
float3 H = normalize(Ldir + Vdir);
float NdotH = saturate(dot(Nrm, H));
float SpecTerm = pow(NdotH, SpecSharpness) * SpecIntensity;

float SpecBand = step(SpecThreshold, SpecTerm) * SpecRampVal;
float3 SpecCol = SpecBand;

// ------------------------------------------------------------
// 6. Hair / metal anisotropic highlight
// ------------------------------------------------------------
float3 T = normalize(cross(float3(0,0,1), Nrm));
float HairDot = abs(dot(Vdir, T));
float HairStrip = smoothstep(1.0 - HairSpecWidth, 1.0, HairDot);
float HairSpec = HairStrip * HairSpecIntensity;

// ------------------------------------------------------------
// 7. Rim light
// ------------------------------------------------------------
float RimBase = 1.0 - saturate(dot(Vdir, Nrm));
float Rim = pow(RimBase, RimPower) * RimStrength;

// ------------------------------------------------------------
// 8. Internal outline darkening
// ------------------------------------------------------------
float OutlineMask = pow(1.0 - saturate(dot(Vdir, Nrm)), 3.0) * OutlineStrength;

// ------------------------------------------------------------
// 9. Combine
// ------------------------------------------------------------
float3 Final = ToonCol;
Final += SpecCol;
Final += HairSpec;
Final += Rim;
Final -= OutlineMask;

return Final;

}

float3 CustomExpression1(float3 BaseColor, float3 NormalWS, float3 LightDirWS, float3 ViewDirWS, float3 DyeColor, float3 DyeMask, float DyeStrength, float ShadowThreshold, float MidThreshold, float ShadowIntensity, float MidIntensity, float LitIntensity, float SpecIntensity, float SpecPower, float RimStrength, float RimPower, float OutlineStrength, float ShadowMask, float3 OutlineColor, float3 RimMask, float OutlineWidth, float3 HairColorA, float3 HairColorB, float HairIntensityA, float HairIntensityB, float HairMaskA_input, float HairMaskB_input, float3 HairRimColor, float HairRimStrength, float HairRimPower, float3 RimColor, float HairShineIntensity, float ShineWidth, float ShineCenter, float FaceSoftness, float FaceCutoff, float FaceMaskR, float UseHairShine)
{
// ------------------------------------------------------------
// 1. Normalize vectors
// ------------------------------------------------------------
float3 N = normalize(NormalWS);
float3 L = normalize(-LightDirWS);
float3 V = normalize(ViewDirWS);

// ------------------------------------------------------------
// 2. Hair Masks (two independent channels)
// ------------------------------------------------------------
float HairMaskA_local = saturate(HairMaskA_input);   // Texture R
float HairMaskB_local = saturate(HairMaskB_input);   // Texture G
float HairMaskCombined = saturate(max(HairMaskA_local, HairMaskB_local));

// ------------------------------------------------------------
// 3. Hair Dye A
// ------------------------------------------------------------
float HairAWeight = saturate(HairMaskA_local * HairIntensityA);
float3 DyedA = lerp(BaseColor, HairColorA, HairAWeight);

// ------------------------------------------------------------
// 4. Hair Dye B
// ------------------------------------------------------------
float HairBWeight = saturate(HairMaskB_local * HairIntensityB);
float3 DyedAB = lerp(DyedA, HairColorB, HairBWeight);

// ------------------------------------------------------------
// 5. Global Dye (does NOT affect hair)
// ------------------------------------------------------------
float DyeWeight = saturate(DyeMask * DyeStrength);
float NonHairDyeWeight = DyeWeight * (1.0 - HairMaskCombined);
float3 BC = lerp(DyedAB, DyeColor, NonHairDyeWeight);

// ------------------------------------------------------------
// 6. NdotL
// ------------------------------------------------------------
float NdotL = saturate(dot(N, L));

// ------------------------------------------------------------
// 7. Blue‑Tinted Shadows (Bleach color grade)
// ------------------------------------------------------------
float3 ShadowTint = float3(0.75, 0.85, 1.10); // subtle blue
float3 ColShadow = BC * ShadowIntensity * ShadowTint;
float3 ColMid    = BC * MidIntensity;
float3 ColLit    = BC * LitIntensity;

// ------------------------------------------------------------
// 8. 3‑Band Toon Shading
// ------------------------------------------------------------
float3 ToonCol = ColShadow;
if (NdotL >= ShadowThreshold && NdotL < MidThreshold) ToonCol = ColMid;
if (NdotL >= MidThreshold) ToonCol = ColLit;

// ------------------------------------------------------------
// 9. Specular
// ------------------------------------------------------------
float3 H = normalize(L + V);
float NdotH = saturate(dot(N, H));
float Spec = pow(NdotH, SpecPower) * SpecIntensity;

// ------------------------------------------------------------
// 10. Directional Rim Light
// ------------------------------------------------------------
float Fres = 1.0 - saturate(dot(N, V));

// Top‑rim bias
float TopMask = saturate(dot(N, float3(0,1,0)));

// Back‑rim bias
float BackMask = saturate(dot(N, -L));

// Final directional rim mask
float DirRimMask = saturate(TopMask * 0.6 + BackMask * 0.4);

// Colored rim
float RimColoredRaw = pow(Fres, RimPower) * RimStrength * DirRimMask;
float3 RimColored = RimColoredRaw * RimMask * RimColor;

// Hair rim (white)
float HairRimRaw = pow(Fres, HairRimPower) * HairRimStrength * DirRimMask;
float3 RimHair = HairRimRaw * HairMaskCombined * HairRimColor;

// Base rim fallback
float RimBaseRaw = pow(Fres, RimPower) * (RimStrength * 0.25);
float3 RimBase = RimBaseRaw * (1.0 - RimMask);

// Final rim
float3 Rim = RimColored + RimHair + RimBase;

// ------------------------------------------------------------
// 11. Hair Shine Strip (ROS‑style) WITH TOGGLE
// ------------------------------------------------------------
float3 HairNormal = normalize(N);
float ShineDot = saturate(dot(HairNormal, normalize(float3(0,1,0))));
float ShineBand = smoothstep(ShineCenter - ShineWidth, ShineCenter + ShineWidth, ShineDot);

// Toggle: 1 = ON, 0 = OFF
float3 HairShine = (UseHairShine > 0.5)
    ? (ShineBand * HairShineIntensity * HairMaskCombined)
    : 0;

// ------------------------------------------------------------
// 12. Face Shadow Cutoff (Bleach style)
// ------------------------------------------------------------
float FaceMask = saturate(FaceMaskR); // face + neck + ears
float FaceCut = saturate(dot(N, L));
float FaceShadow = smoothstep(FaceCutoff - FaceSoftness, FaceCutoff + FaceSoftness, FaceCut);
float3 FaceShade = lerp(ColShadow, BC, FaceShadow);
float3 FaceResult = lerp(ToonCol, FaceShade, FaceMask);

// ------------------------------------------------------------
// 13. Colored internal outline
// ------------------------------------------------------------
float OutlineFactor = pow(1.0 - saturate(dot(N, V)), OutlineWidth);
OutlineFactor *= OutlineStrength;
float3 OutlineCol = OutlineColor * OutlineFactor;

// ------------------------------------------------------------
// 14. Combine lighting
// ------------------------------------------------------------
float3 Final = FaceResult + Spec + Rim + HairShine;
Final -= OutlineCol;

// ------------------------------------------------------------
// 15. ROS forced fold shading
// ------------------------------------------------------------
Final = lerp(Final, ColShadow, saturate(ShadowMask));

// ------------------------------------------------------------
// 16. Output
// ------------------------------------------------------------
return saturate(Final);

}

float3 MaterialTangentNormal(FMaterialInput M)
{
    // 'Normal' texture parameter (SAMPLERTYPE_Normal): the game instance's normal map, BC5
    float2 XY = Material_Texture2D_2.SampleBias(TEXTURE_SAMPLER, M.UV0, M.MipBias).rg * 2.0 - 1.0;
    return float3(XY, sqrt(max(0.0, 1.0 - dot(XY, XY))));
}

FMaterialOutput EvaluateMaterial(FMaterialInput M)
{
    // 'BaseColor' texture parameter: the game instance's Color texture
    const float4 BaseColorTex = Material_Texture2D_0.SampleBias(TEXTURE_SAMPLER, M.UV0, M.MipBias);
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
            const float Coverage = NONE.SampleBias(View_SharedAnisotropic4XWrappedSampler, In.TexCoords0.xy, View_TemporalSamplerBias.w).r;
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
