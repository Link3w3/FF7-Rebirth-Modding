
#define PIXELSHADER 1
struct FMaterialPixelParameters
{
    float3x3 TangentToWorld;
    float3 CameraVector;
    float4 SvPosition;
    float3 WorldPosition_CamRelative;
    float TwoSidedSign;
    float4 VertexColor;
};
Texture3D View_PerlinNoise3DTexture;
SamplerState View_PerlinNoise3DTextureSampler;
SamplerState View_SharedBilinearWrappedSampler;
SamplerState View_SharedBilinearClampedSampler;
SamplerState Material_Wrap_WorldGroupSettings;
SamplerState Material_Clamp_WorldGroupSettings;
cbuffer ViewCB
{
    float4 View_InvDeviceZToWorldZTransform;
    float4 View_ViewRectMin;
    float4 View_ViewSizeAndInvSize;
    float View_OneOverPreExposure;
    float3 View_PreViewTranslation;
    uint View_FrameNumber;
};
float4 Texture2DSample(Texture2D Tex, SamplerState Sampler, float2 UV) { return Tex.Sample(Sampler, UV); }
float4 Texture2DSampleLevel(Texture2D Tex, SamplerState Sampler, float2 UV, float Mip) { return Tex.SampleLevel(Sampler, UV, Mip); }
float4 Texture3DSample(Texture3D Tex, SamplerState Sampler, float3 UV) { return Tex.Sample(Sampler, UV); }
cbuffer Inputs
{
    float4 GRMS_Noise;
    float4 GRMS_VertexExpression;
    float4 GRMS_EBuffer;
    float4 GRMS_LocalToWorld0;
    float4 GRMS_LocalToWorld1;
    float4 GRMS_LocalToWorld2;
    float4 GV_ExtraPixelCoordinateContext;
    float4 GV_GenericVector0Context;
    float4 GV_ExternalEmissiveContext;
    float4 GV_ExtraNormalizedCoordinateContext;
    float4 GV_AnimateTimeContext;
    float4 GV_GenericVector1Context;
};
Texture2D GT_PositiveTransitionNormal;
SamplerState GT_PositiveTransitionNormalSampler;
Texture2D GT_Roughness;
SamplerState GT_RoughnessSampler;
Texture2D GT_DetailNormal;
SamplerState GT_DetailNormalSampler;
Texture2D GT_DetailRoughness;
SamplerState GT_DetailRoughnessSampler;
Texture2D GT_WideBentNormal;
SamplerState GT_WideBentNormalSampler;
Texture2D GT_WideFlowPhase;
SamplerState GT_WideFlowPhaseSampler;
Texture2D GT_DetailFoam;
SamplerState GT_DetailFoamSampler;
Texture2D GT_WideFlowDirectivity;
SamplerState GT_WideFlowDirectivitySampler;
Texture2D GT_Wetness;
SamplerState GT_WetnessSampler;
Texture2D GT_ExtraEmissive;
SamplerState GT_ExtraEmissiveSampler;
Texture2D GT_ExtraColor;
SamplerState GT_ExtraColorSampler;
Texture2D GT_Metallic;
SamplerState GT_MetallicSampler;
Texture2D GT_SegmentLayer1;
SamplerState GT_SegmentLayer1Sampler;
Texture2D GT_WideOcclusion;
SamplerState GT_WideOcclusionSampler;
Texture2D GT_Thickness;
SamplerState GT_ThicknessSampler;
Texture2D GT_DetailColor;
SamplerState GT_DetailColorSampler;
Texture2D GT_Emissive;
SamplerState GT_EmissiveSampler;
Texture2D GT_BrokenFlowEmissive0;
SamplerState GT_BrokenFlowEmissive0Sampler;
Texture2D GT_BrokenFlowEmissive1;
SamplerState GT_BrokenFlowEmissive1Sampler;
Texture2D GT_FilmStructure;
SamplerState GT_FilmStructureSampler;
Texture2D GT_Normal;
SamplerState GT_NormalSampler;
Texture2D GT_OceanGeometry;
SamplerState GT_OceanGeometrySampler;
Texture2D GT_Occlusion;
SamplerState GT_OcclusionSampler;
Texture2D GT_WideFoamThreshold;
SamplerState GT_WideFoamThresholdSampler;
Texture2D GT_Detail;
SamplerState GT_DetailSampler;
Texture2D GT_WideFlowDirection;
SamplerState GT_WideFlowDirectionSampler;
Texture2D GT_FilmThickness;
SamplerState GT_FilmThicknessSampler;
Texture2D GT_Foam;
SamplerState GT_FoamSampler;
Texture2D GT_GradientRoughness;
SamplerState GT_GradientRoughnessSampler;
Texture2D GT_IrisColor;
SamplerState GT_IrisColorSampler;
Texture2D GT_GazeNormal;
SamplerState GT_GazeNormalSampler;
Texture2D GT_Distribution;
SamplerState GT_DistributionSampler;
Texture2D GT_DetailOcclusion;
SamplerState GT_DetailOcclusionSampler;
Texture2D GT_IrisOcclusion;
SamplerState GT_IrisOcclusionSampler;
Texture2D GT_DetailCoverage;
SamplerState GT_DetailCoverageSampler;
Texture2D GT_MateriaContext;
SamplerState GT_MateriaContextSampler;
Texture2D GT_LayeredColor;
SamplerState GT_LayeredColorSampler;
Texture2D GT_Muddiness;
SamplerState GT_MuddinessSampler;
Texture2D GT_TransparencyCoefficient;
SamplerState GT_TransparencyCoefficientSampler;
Texture2D GT_IrisNormal;
SamplerState GT_IrisNormalSampler;
Texture2D GT_ShadingLayer;
SamplerState GT_ShadingLayerSampler;
Texture2D GT_Thinness;
SamplerState GT_ThinnessSampler;
Texture2D GT_Color;
SamplerState GT_ColorSampler;
Texture2D GT_Isotropy;
SamplerState GT_IsotropySampler;
Texture2D GT_OxygenSaturation;
SamplerState GT_OxygenSaturationSampler;
Texture2D GT_Pores;
SamplerState GT_PoresSampler;
Texture2D GT_Diffusion;
SamplerState GT_DiffusionSampler;
Texture2D GT_GradientOcclusion;
SamplerState GT_GradientOcclusionSampler;
Texture2D GT_SegmentLayer0;
SamplerState GT_SegmentLayer0Sampler;
Texture2D GT_GradientNormal;
SamplerState GT_GradientNormalSampler;
Texture2D GT_ToneGradient;
SamplerState GT_ToneGradientSampler;
Texture2D GT_Transmittance;
SamplerState GT_TransmittanceSampler;
Texture2D GT_Opacity;
SamplerState GT_OpacitySampler;
Texture2D GT_Coverage;
SamplerState GT_CoverageSampler;
Texture2D GT_IrisEmissive;
SamplerState GT_IrisEmissiveSampler;
Texture2D GT_TransmittanceCoefficient;
SamplerState GT_TransmittanceCoefficientSampler;
Texture2D GT_ScrelaNormal;
SamplerState GT_ScrelaNormalSampler;
Texture2D GT_GradientPhase;
SamplerState GT_GradientPhaseSampler;
Texture2D GT_Transparency;
SamplerState GT_TransparencySampler;
float3 CustomExpression0(FMaterialPixelParameters Parameters, float2 UV0, float2 UV1, float2 UV2, float2 UV3, float4 RMS_Noise, float RMS_DynamicCoverage, float4 RMS_VertexExpression, float4 RMS_EBuffer, float4 RMS_LocalToWorld0, float4 RMS_LocalToWorld1, float4 RMS_LocalToWorld2, Texture2D T_PositiveTransitionNormal, SamplerState T_PositiveTransitionNormalSampler, Texture2D T_Roughness, SamplerState T_RoughnessSampler, Texture2D T_DetailNormal, SamplerState T_DetailNormalSampler, Texture2D T_DetailRoughness, SamplerState T_DetailRoughnessSampler, Texture2D T_WideBentNormal, SamplerState T_WideBentNormalSampler, Texture2D T_WideFlowPhase, SamplerState T_WideFlowPhaseSampler, Texture2D T_DetailFoam, SamplerState T_DetailFoamSampler, Texture2D T_WideFlowDirectivity, SamplerState T_WideFlowDirectivitySampler, Texture2D T_Wetness, SamplerState T_WetnessSampler, Texture2D T_ExtraEmissive, SamplerState T_ExtraEmissiveSampler, Texture2D T_ExtraColor, SamplerState T_ExtraColorSampler, Texture2D T_Metallic, SamplerState T_MetallicSampler, Texture2D T_SegmentLayer1, SamplerState T_SegmentLayer1Sampler, Texture2D T_WideOcclusion, SamplerState T_WideOcclusionSampler, Texture2D T_Thickness, SamplerState T_ThicknessSampler, Texture2D T_DetailColor, SamplerState T_DetailColorSampler, Texture2D T_Emissive, SamplerState T_EmissiveSampler, Texture2D T_BrokenFlowEmissive0, SamplerState T_BrokenFlowEmissive0Sampler, Texture2D T_BrokenFlowEmissive1, SamplerState T_BrokenFlowEmissive1Sampler, Texture2D T_FilmStructure, SamplerState T_FilmStructureSampler, Texture2D T_Normal, SamplerState T_NormalSampler, Texture2D T_OceanGeometry, SamplerState T_OceanGeometrySampler, Texture2D T_Occlusion, SamplerState T_OcclusionSampler, Texture2D T_WideFoamThreshold, SamplerState T_WideFoamThresholdSampler, Texture2D T_Detail, SamplerState T_DetailSampler, Texture2D T_WideFlowDirection, SamplerState T_WideFlowDirectionSampler, Texture2D T_FilmThickness, SamplerState T_FilmThicknessSampler, Texture2D T_Foam, SamplerState T_FoamSampler, Texture2D T_GradientRoughness, SamplerState T_GradientRoughnessSampler, Texture2D T_IrisColor, SamplerState T_IrisColorSampler, Texture2D T_GazeNormal, SamplerState T_GazeNormalSampler, Texture2D T_Distribution, SamplerState T_DistributionSampler, Texture2D T_DetailOcclusion, SamplerState T_DetailOcclusionSampler, Texture2D T_IrisOcclusion, SamplerState T_IrisOcclusionSampler, Texture2D T_DetailCoverage, SamplerState T_DetailCoverageSampler, Texture2D T_MateriaContext, SamplerState T_MateriaContextSampler, Texture2D T_LayeredColor, SamplerState T_LayeredColorSampler, Texture2D T_Muddiness, SamplerState T_MuddinessSampler, Texture2D T_TransparencyCoefficient, SamplerState T_TransparencyCoefficientSampler, Texture2D T_IrisNormal, SamplerState T_IrisNormalSampler, Texture2D T_ShadingLayer, SamplerState T_ShadingLayerSampler, Texture2D T_Thinness, SamplerState T_ThinnessSampler, Texture2D T_Color, SamplerState T_ColorSampler, Texture2D T_Isotropy, SamplerState T_IsotropySampler, Texture2D T_OxygenSaturation, SamplerState T_OxygenSaturationSampler, Texture2D T_Pores, SamplerState T_PoresSampler, Texture2D T_Diffusion, SamplerState T_DiffusionSampler, Texture2D T_GradientOcclusion, SamplerState T_GradientOcclusionSampler, Texture2D T_SegmentLayer0, SamplerState T_SegmentLayer0Sampler, Texture2D T_GradientNormal, SamplerState T_GradientNormalSampler, Texture2D T_ToneGradient, SamplerState T_ToneGradientSampler, Texture2D T_Transmittance, SamplerState T_TransmittanceSampler, Texture2D T_Opacity, SamplerState T_OpacitySampler, Texture2D T_Coverage, SamplerState T_CoverageSampler, Texture2D T_IrisEmissive, SamplerState T_IrisEmissiveSampler, Texture2D T_TransmittanceCoefficient, SamplerState T_TransmittanceCoefficientSampler, Texture2D T_ScrelaNormal, SamplerState T_ScrelaNormalSampler, Texture2D T_GradientPhase, SamplerState T_GradientPhaseSampler, Texture2D T_Transparency, SamplerState T_TransparencySampler, float4 V_ExtraPixelCoordinateContext, float4 V_GenericVector0Context, float4 V_ExternalEmissiveContext, float4 V_ExtraNormalizedCoordinateContext, float4 V_AnimateTimeContext, float4 V_GenericVector1Context, float S_AnimateTime, float S_Blood, float S_BrokenFlow, float S_BrokenFlowEmissive0, float S_BrokenFlowEmissive1, float S_Color, float S_Convex, float S_Coverage, float S_CylindricalNormal, float S_Detail, float S_DetailColor, float S_DetailCoverage, float S_DetailFoam, float S_DetailNormal, float S_DetailOcclusion, float S_DetailRoughness, float S_Diffusion, float S_Distribution, float S_Emissive, float S_ExternalEmissive, float S_ExtraColor, float S_ExtraEmissive, float S_ExtraNormalizedCoordinate, float S_ExtraPixelCoordinate, float S_Eye, float S_EyeMigration, float S_Fabric, float S_Film, float S_FilmStructure, float S_FilmThickness, float S_Flow, float S_FlowDetailFoam, float S_FlowDetailNormal, float S_FlowDetailRoughness, float S_FlowDirection, float S_FlowFoam, float S_FlowNormal, float S_FlowRoughness, float S_Foam, float S_GazeNormal, float S_Ghost, float S_Gradient, float S_GradientNormal, float S_GradientOcclusion, float S_GradientPhase, float S_GradientRoughness, float S_Hair, float S_Hologram, float S_HologramEye, float S_IrisColor, float S_IrisEmissive, float S_IrisNormal, float S_IrisOcclusion, float S_Isotropy, float S_Layered, float S_LayeredColor, float S_Materia, float S_MateriaIndexed, float S_Metallic, float S_Muddiness, float S_Normal, float S_Occlusion, float S_Ocean, float S_OceanGeometry, float S_Opacity, float S_OxygenSaturation, float S_Phantom, float S_PhaseGWater, float S_Pool, float S_Pores, float S_PositiveTransitionNormal, float S_ReflectanceCrystal, float S_ReflectanceGlass, float S_ReflectanceWater, float S_Roughness, float S_ScleraNormal, float S_SegmentLayer0, float S_SegmentLayer1, float S_Segmented, float S_ShadingLayer, float S_Skin, float S_Standard, float S_Subsurface, float S_Thick, float S_Thickness, float S_Thin, float S_Thinness, float S_ToneGradient, float S_Transmittance, float S_TransmittanceCoefficient, float S_Transparency, float S_TransparencyCoefficient, float S_Unlit, float S_ViewCoordinate, float S_Wetness, float S_WetnessTrickle, float S_WideBentNormal, float S_WideFlowDirection, float S_WideFlowDirectivity, float S_WideFlowPhase, float S_WideFoamThreshold, float S_WideOcclusion, inout float RMS_Metallic, inout float RMS_Specular, inout float RMS_Roughness, inout float RMS_AO, inout float3 RMS_Normal, inout float3 RMS_Emissive, inout float RMS_OpacityMask, inout float RMS_Opacity, inout float RMS_ShadingModel, inout float RMS_ModelParam, inout float RMS_Reflectance, inout float4 RMS_Custom, inout float2 RMS_WetLayer, inout float3 RMS_WetNormal, inout float3 RMS_ColoredOpacity, inout float3 RMS_Muddiness, inout float RMS_TransparencyLog2, inout float3 RMS_TransmittanceLog2, inout float RMS_Thickness, inout float RMS_PhaseG, inout float RMS_MediumPath, inout float RMS_Foam)
{
// RM_Surface rebuilt (Create a Character System). The node "RMS": the code is the rebuild checked against all 104 of the
// game's RMI_Surface_* shaders (the same text runs in the checker); only the samplers and the dither noise are the editor's.
#if PIXELSHADER
#define RMS_WRAP Material_Wrap_WorldGroupSettings
#define RMS_CLAMP Material_Clamp_WorldGroupSettings
#define RMS_BILINEAR_WRAP View_SharedBilinearWrappedSampler
#define RMS_BILINEAR_CLAMP View_SharedBilinearClampedSampler
struct RMS_Env
{
    // the game's 3D blue noise (the hologram's sparkle) is not in the editor: the engine's Perlin noise volume stands in
    float4 BlueNoise3D(int3 p)
    {
        return View_PerlinNoise3DTexture.Load(int4(p.x & 15, p.y & 15, p.z & 15, 0));
    }
};
// RM_Surface, rebuilt from Final Fantasy VII Rebirth's compiled shaders (the 104 RMI_Surface_* permutations).
//
// This is the code of the material's Custom node "RMS". The same text is compiled by the checker (harness/hlsl2cpp.py
// makes it C++) and run beside the game's own decompiled shaders on the same inputs, so every feature here is the
// game's arithmetic, in the game's order.
//
// Custom node inputs:
//   UV0..UV3          float2   texture coordinates (Coordinate0..3)
//   RMS_Noise         float4   the dither noise (the game: its spatiotemporal blue noise; the editor: a stand-in)
//   RMS_DynamicCoverage float  the per-object fade (the game's Primitive DynamicCoverage; 1 = fully there)
//   RMS_VertexExpression float4 what the vertex shader works out for the pixels (VertexExpression*: x = the wrinkle weight
//                      of VertexExpressionBone, ...); the editor: a vertex interpolator, 0 without the game's bone data
//   RMS_EBuffer       float4   the engine's screen-space weather at this pixel (z = rain, w > 0 = sheltered?, xy = a 16-bit
//                      half: puddle depth); the editor: 0 (dry weather)
//   T_<Texture>       Texture2D (+ T_<Texture>Sampler) the 67 texture parameters
//   V_<Vector>        float4   the 9 *Context vector parameters
//   S_<Switch>        float    the 126 static switches (1 or 0; constants after the static permutation)
// Outputs: the return value is the base colour; the rest are the node's additional outputs (RMS_*), every one written.
//   (RMS_ModelParam: the game's GBuffer A.w, its encoding of the model's reflectance; RMS_Reflectance: that F0 itself)
//   Translucent permutations: RMS_Emissive is premultiplied by RMS_Opacity in the forward pass; RMS_ColoredOpacity is the
//   per-channel share of the background the surface blocks (the game's "colored" alpha composite).
//   Lit translucent ones (Glass, Crystal, Water): RMS_Muddiness, RMS_TransparencyLog2, RMS_TransmittanceLog2, RMS_Thickness
//   describe the medium for the game's translucent lighting; RMS_Reflectance, RMS_PhaseG and RMS_MediumPath its model; RMS_Foam
//   the foam on water.
// The environment (RMS_Env, defined by whoever runs this code) supplies the noise textures the editor doesn't have.
//
// "Material" values are what RM_Surface's graph hands the engine (unsaturated, like any material's pins). The game's
// base pass then does a few things the stock engine doesn't (curvature roughness filter, emissive seen through the
// specular layer); RMS_Engine does those the game's way, for the editor's pins (RMS_RoughnessOut, RMS_EmissiveOut).

struct RMS_Lib
{
    // a two-channel (BC5) normal map: xy in [-1,1], z rebuilt, normalized
    float3 NormalXY(float4 t)
    {
        float x = t.x * 2.0 - 1.0;
        float y = t.y * 2.0 - 1.0;
        float z = sqrt(max(0.0, 1.0 - dot(float2(x, y), float2(x, y))));
        return normalize(float3(x, y, z));
    }

    // the engine's tangent-space normal to world (MaterialTemplate: normalize, transform, normalize, two-sided sign)
    float3 WorldNormal(float3 n, float3x3 TangentToWorld, float TwoSidedSign)
    {
        float3 m = normalize(n);
        float3 w = normalize(mul(m, TangentToWorld));
        return w * TwoSidedSign;
    }

    // the game's base pass: roughness widened by the screen-space curvature of the world normal (specular AA)
    float FilterRoughness(float Roughness, float3 N)
    {
        float3 dx = ddx_fine(N);
        float3 dy = ddy_fine(N);
        float r = saturate(Roughness);
        return sqrt(saturate(min((dot(dy, dy) + dot(dx, dx)) * 0.15915493667125701904296875, 0.180000007152557373046875) + r * r));
    }

    // the game's base pass: emissive light leaving through the dielectric specular layer (in and out: (1 - F)^2, a thin
    // absorbing coat along the view path), none through metal
    float EmissiveTransmission(float3 N, float3 V, float Roughness, float Metallic)
    {
        float NoV = saturate(dot(N, V));
        float a = 1.0 - Roughness;
        float a004 = (min(a * a, exp2(NoV * -9.27999973297119140625)) * a + (0.0425000004470348358154296875 - Roughness * 0.0274999998509883880615234375)) * 1.03999996185302734375;
        float t = 1.0 - saturate(((Roughness * 0.02199999988079071044921875 + -0.039999999105930328369140625) + a004) + ((1.03999996185302734375 - Roughness * 0.572000026702880859375) - a004) * 0.0400000028312206268310546875);
        float k = (t * t) * exp2(max(0.001000000047497451305389404296875, 0.300000011920928955078125 / max(0.0333333350718021392822265625, NoV)) * -0.0291463173925876617431640625);
        return k - k * saturate(Metallic);
    }

    // a second occlusion multiplied in, softly (WideOcclusion, DetailOcclusion): near min(o, w) where they disagree
    float CombineOcclusion(float o, float w)
    {
        float p = o * w;
        float m = min(o, w);
        float a = (1.0 - m) + p;
        float a2 = a * a;
        float c = 1.0 - (a2 * a2) * a;
        float c2 = c * c;
        return (c2 * c2) * (c * (p - m)) + m;
    }

    // a unit direction, or zero where it has none (the game's guard: the reciprocal length is NaN)
    float2 SafeDirection(float2 v)
    {
        float r = rsqrt(dot(v, v));
        return isnan(r) ? float2(0.0, 0.0) : float2(r * v.x, r * v.y);
    }

    // a normal map on another UV set turned into this one's tangent space: the screen-space rotation between the two
    // UV sets' directions of travel
    float3 RotateToUV(float3 d, float2 uvThis, float2 uvOther)
    {
        float2 g0 = SafeDirection(ddy_fine(uvThis) + ddx_fine(uvThis));
        float2 g1 = SafeDirection(ddy_fine(uvOther) + ddx_fine(uvOther));
        float c = dot(g1, g0);
        float s = g1.x * g0.y - g1.y * g0.x;
        return float3(dot(float2(d.x, d.y), float2(c, -s)), dot(float2(d.x, d.y), float2(s, c)), d.z);
    }

    // reoriented normal mapping (Barre-Brisebois & Hill): detail d on base b
    float3 Reoriented(float3 b, float3 d)
    {
        float3 t = float3(b.x, b.y, b.z + 1.0);
        float3 u = float3(-d.x, -d.y, d.z);
        float k = dot(t, u);
        return normalize(t * k - u * t.z);
    }

    // from normal a toward normal b by t along the arc (unnormalized sine weights; the guards the game has)
    float3 ArcBlend(float3 a, float3 b, float tIn)
    {
        float t = saturate(tIn);
        float c = dot(a, b);
        float sg = (c >= 0.0) ? 1.0 : -1.0;
        float th = acos(saturate(abs(c)));
        float3 r = ((b * sg) * sin(th * t)) + (a * sin(th * (1.0 - t)));
        if (dot(r, r) < 9.9999999747524270787835121154785e-07)
        {
            r = lerp(a, b, t);
        }
        if (dot(r, r) < 9.9999999747524270787835121154785e-07)
        {
            r = (t < 0.5) ? a : b;
        }
        return normalize(r);
    }

    // a 16-bit half float kept in two 8-bit channels (lo, hi)
    float Half8x2(float lo, float hi)
    {
        return f16tof32((uint(round(hi * 255.0)) << 8) | uint(round(lo * 255.0)));
    }

    // the game's ease for its rain amount
    float RainEase(float e)
    {
        if (e < 0.5)
        {
            float e2 = e * e;
            return (e2 * e2) * 8.0;
        }
        float f = 1.0 - e;
        float f2 = f * f;
        return 1.0 - (f2 * f2) * 8.0;
    }

    // where an Extra* image is read: a rectangle of it in pixels (kept half a texel inside), or 0..1, or plainly UV2
    float2 ExtraCoordinate(float2 uv, float usePixel, float4 pix, float useNormalized, float4 nrm, uint w, uint h)
    {
        float2 r = uv;
        if (usePixel > 0.5 && dot(pix, float4(1.0, 1.0, 1.0, 1.0)) > 0.0)
        {
            r = float2(min(max((pix.z - pix.x) * uv.x + pix.x, pix.x + 0.5), pix.z + -0.5) * (1.0 / float(w)),
                       min(max((pix.w - pix.y) * uv.y + pix.y, pix.y + 0.5), pix.w + -0.5) * (1.0 / float(h)));
        }
        if (useNormalized > 0.5 && dot(nrm, float4(1.0, 1.0, 1.0, 1.0)) > 0.0)
        {
            r = float2((nrm.z - nrm.x) * uv.x + nrm.x, (nrm.w - nrm.y) * uv.y + nrm.y);
        }
        return r;
    }

    // the game's sRGB curves (its own thresholds)
    float LinearToSrgb1(float c)
    {
        return (c < 0.003130800090730190277099609375) ? c * 12.9200000762939453125 : pow(c, 0.4166666567325592041015625) * 1.05499994754791259765625 + -0.054999999701976776123046875;
    }
    float SrgbToLinear1(float c)
    {
        return (c < 0.040449999272823333740234375) ? c * 0.077399380505084991455078125 : pow((c + 0.054999999701976776123046875) * 0.947867333889007568359375, 2.400000095367431640625);
    }
    float3 LinearToSrgb(float3 c)
    {
        return float3(LinearToSrgb1(c.x), LinearToSrgb1(c.y), LinearToSrgb1(c.z));
    }
    float3 SrgbToLinear(float3 c)
    {
        return float3(SrgbToLinear1(c.x), SrgbToLinear1(c.y), SrgbToLinear1(c.z));
    }
    // "overlay" (as in paint programs) of tint t on base b, both sRGB-encoded
    float Overlay1(float b, float t)
    {
        return saturate((b < 0.5) ? (b * 2.0) * t : 1.0 - ((1.0 - b) * 2.0) * (1.0 - t));
    }
    // a segment layer: the base colour (linear) overlaid with a tint, in sRGB, back to linear
    float3 SegmentTint(float3 baseSrgb, float3 tint)
    {
        float3 t = LinearToSrgb(saturate(tint));
        return SrgbToLinear(float3(Overlay1(baseSrgb.x, t.x), Overlay1(baseSrgb.y, t.y), Overlay1(baseSrgb.z, t.z)));
    }

    // the game's GBuffer encoding of a reflectance F0 (0..0.16; finer below 0.04)
    float EncodeReflectance(float f0)
    {
        float a = max(0.0, min(saturate(f0), 0.1599999964237213134765625));
        return saturate((a < 0.039999999105930328369140625) ? a * 16.6666660308837890625 : a * 2.77777767181396484375 + 0.5555555820465087890625);
    }

    // the game's fade toward the depth of the far plane over 50 units (smoothstep, then ^8): its "ghost" opacity
    float FarFade(float sceneDepth, float4 invDeviceZToWorldZ)
    {
        float f = saturate(saturate(((invDeviceZToWorldZ.y - sceneDepth) + 1.0 / -invDeviceZToWorldZ.w) * 0.0199999995529651641845703125));
        float s = (f * f) * (3.0 - f * 2.0);
        float s2 = s * s;
        float s4 = s2 * s2;
        return s4 * s4;
    }

    // one flow-mapped image: slid along the flow field (dir x directivity x gv.y = how far over a cycle) as the cycle runs
    // (the texel's phase + time x gv.x), cross-faded into the next cycle's copy one length ahead so it never jumps
    float3 FlowLayer(Texture2D Tex, SamplerState TexSampler, float2 uv, float2 dir, float phase, float directivity, float time, float4 gv)
    {
        float len = directivity * gv.y;
        float t = frac(phase + time * gv.x);
        float2 off = float2(len * dir.x, len * dir.y);
        float2 o = float2(t * off.x, t * off.y);
        float3 a = Texture2DSample(Tex, TexSampler, float2(uv.x - o.x, uv.y - o.y)).rgb;
        float3 b = Texture2DSample(Tex, TexSampler, float2((off.x + uv.x) - o.x, (off.y + uv.y) - o.y)).rgb;
        float c = saturate(t);
        float w = (c * c) * (3.0 - c * 2.0);
        return lerp(a, b, w);
    }

    // two-phase flow mapping: the two places a map is read this cycle (a, b: one flow length apart) and how far to fade
    // from the first to the second
    void FlowUV(float2 uv, float2 dir, float phase, float directivity, float time, float4 gv, out float2 a, out float2 b, out float w)
    {
        float len = directivity * gv.y;
        float t = frac(phase + time * gv.x);
        float2 off = float2(len * dir.x, len * dir.y);
        float2 o = float2(t * off.x, t * off.y);
        a = float2(uv.x - o.x, uv.y - o.y);
        b = float2((off.x + uv.x) - o.x, (off.y + uv.y) - o.y);
        float c = saturate(t);
        w = (c * c) * (3.0 - c * 2.0);
    }

    // the dithered coverage test: kept when the coverage beats the noise
    float Dithered(float Coverage, float Noise)
    {
        return (Coverage > Noise * 0.99609375 + 0.001953125) ? 1.0 : -1.0;
    }
};
// ==== body ====
RMS_Lib L;
RMS_Env Env;

// ---------------------------------------------------------------- every output defined
float3 BaseColor = float3(0.0, 0.0, 0.0);
RMS_Metallic = 0.0;
RMS_Specular = 0.0;
RMS_Roughness = 0.5;
RMS_AO = 1.0;
RMS_Normal = float3(0.0, 0.0, 1.0);
RMS_Emissive = float3(0.0, 0.0, 0.0);
RMS_OpacityMask = 1.0;
RMS_Opacity = 1.0;
RMS_ShadingModel = 1.0;
RMS_ModelParam = 0.66666662693023681640625;
RMS_Reflectance = 0.0400000028312206268310546875;
RMS_Custom = float4(0.0, 0.0, 0.0, 0.0);
RMS_WetLayer = float2(0.0, 0.0);
RMS_ColoredOpacity = float3(0.0, 0.0, 0.0);
RMS_Muddiness = float3(0.0, 0.0, 0.0);
RMS_TransparencyLog2 = 0.0;
RMS_TransmittanceLog2 = float3(0.0, 0.0, 0.0);
RMS_Thickness = 1.0;
RMS_PhaseG = 0.0;
RMS_MediumPath = 0.0;
RMS_Foam = 0.0;
bool HasWetNormal = false;
float3 WetNormal = float3(0.0, 0.0, 1.0);

// ---------------------------------------------------------------- Flow (water): the surface's maps stream along a flow
// field, read twice one cycle apart and cross-faded (two-phase flow mapping). The direction per vertex (Coordinate3,
// FlowDirection), per texel a phase (WideFlowPhase) and how far the maps travel (WideFlowDirectivity), both on
// Coordinate1; the base maps (Coordinate0) at GenericVector0Context's speed (x, along AnimateTimeContext.z) and travel (y),
// the detail maps (Coordinate2) at GenericVector1Context's
bool Flowing = S_Flow > 0.5;
float2 FlowA0 = UV0;
float2 FlowB0 = UV0;
float2 FlowA2 = UV2;
float2 FlowB2 = UV2;
float FlowW0 = 0.0;
float FlowW2 = 0.0;
if (Flowing)
{
    float2 dir = (S_FlowDirection > 0.5) ? UV3 : float2(0.0, 0.0);
    float ph = 0.0;
    if (S_WideFlowPhase > 0.5)
    {
        ph = Texture2DSample(T_WideFlowPhase, RMS_WRAP, UV1).r;
    }
    float dv = 1.0;
    if (S_WideFlowDirectivity > 0.5)
    {
        dv = Texture2DSample(T_WideFlowDirectivity, RMS_WRAP, UV1).r;
    }
    float tm = (S_AnimateTime > 0.5) ? V_AnimateTimeContext.z : 0.0;
    L.FlowUV(UV0, dir, ph, dv, tm, V_GenericVector0Context, FlowA0, FlowB0, FlowW0);
    L.FlowUV(UV2, dir, ph, dv, tm, V_GenericVector1Context, FlowA2, FlowB2, FlowW2);
}

// ---------------------------------------------------------------- base layer (Coordinate0)
if (S_Color > 0.5)
{
    BaseColor = Texture2DSample(T_Color, RMS_WRAP, UV0).rgb;
}
if (S_Metallic > 0.5)
{
    RMS_Metallic = Texture2DSample(T_Metallic, RMS_WRAP, UV0).r;
}
if (S_Normal > 0.5)
{
    if (Flowing && S_FlowNormal > 0.5)
    {
        float3 a = L.NormalXY(Texture2DSample(T_Normal, RMS_WRAP, FlowA0));
        float3 b = L.NormalXY(Texture2DSample(T_Normal, RMS_WRAP, FlowB0));
        RMS_Normal = normalize(lerp(a, b, FlowW0));
    }
    else
    {
        RMS_Normal = L.NormalXY(Texture2DSample(T_Normal, RMS_WRAP, UV0));
    }
}
// wrinkles: toward the stretched-skin normal by the bone-driven weight
if (S_PositiveTransitionNormal > 0.5)
{
    float3 w = L.NormalXY(Texture2DSample(T_PositiveTransitionNormal, RMS_WRAP, UV0));
    RMS_Normal = L.ArcBlend(RMS_Normal, w, saturate(RMS_VertexExpression.x));
}
if (S_Roughness > 0.5)
{
    if (Flowing && S_FlowRoughness > 0.5)
    {
        // (cross-faded as squares)
        float a = Texture2DSample(T_Roughness, RMS_WRAP, FlowA0).r;
        float b = Texture2DSample(T_Roughness, RMS_WRAP, FlowB0).r;
        float a2 = a * a;
        RMS_Roughness = sqrt(saturate((b * b - a2) * FlowW0 + a2));
    }
    else
    {
        RMS_Roughness = Texture2DSample(T_Roughness, RMS_WRAP, UV0).r;
    }
}
if (S_Occlusion > 0.5)
{
    RMS_AO = Texture2DSample(T_Occlusion, RMS_WRAP, UV0).r;
}
if (S_Opacity > 0.5)
{
    RMS_Opacity = Texture2DSample(T_Opacity, RMS_WRAP, UV0).r;
}
// foam on water (the base layer's; the detail layer's joins it below)
float Foam = 0.0;
if (S_Foam > 0.5)
{
    if (Flowing && S_FlowFoam > 0.5)
    {
        float a = Texture2DSample(T_Foam, RMS_WRAP, FlowA0).r;
        float b = Texture2DSample(T_Foam, RMS_WRAP, FlowB0).r;
        Foam = saturate((b - a) * FlowW0 + a);
    }
    else
    {
        Foam = saturate(Texture2DSample(T_Foam, RMS_WRAP, UV0).r);
    }
}

// ---------------------------------------------------------------- the medium of a lit translucent surface (Glass, Crystal,
// Water), for the game's translucent lighting. Transparency: what is left of the light after 100 x TransparencyCoefficient
// units of it (grey); Transmittance: the colour it takes on over 100 x TransmittanceCoefficient units; both as log2 per unit
// length. Muddiness: the colour it scatters back (cloudy water). Thickness: how far the light goes through it (Thinness for
// thin glass, on Coordinate0; Thickness for a solid body, on Coordinate1). The game reads the first five through clamped
// samplers.
if (S_Muddiness > 0.5)
{
    RMS_Muddiness = Texture2DSample(T_Muddiness, RMS_CLAMP, UV0).rgb;
}
if (S_Transparency > 0.5)
{
    float c = 1.0;
    if (S_TransparencyCoefficient > 0.5)
    {
        c = Texture2DSample(T_TransparencyCoefficient, RMS_CLAMP, UV0).r;
    }
    RMS_TransparencyLog2 = log2(saturate(Texture2DSample(T_Transparency, RMS_CLAMP, UV0).r)) * (1.0 / max(9.9999999747524270787835121154785e-07, c * 100.0));
}
if (S_Transmittance > 0.5)
{
    float c = 1.0;
    if (S_TransmittanceCoefficient > 0.5)
    {
        c = Texture2DSample(T_TransmittanceCoefficient, RMS_CLAMP, UV0).r;
    }
    float k = 1.0 / max(9.9999999747524270787835121154785e-07, c * 100.0);
    float3 t = saturate(Texture2DSample(T_Transmittance, RMS_CLAMP, UV0).rgb);
    RMS_TransmittanceLog2 = float3(log2(t.x) * k, log2(t.y) * k, log2(t.z) * k);
}
if (S_Thinness > 0.5)
{
    RMS_Thickness = Texture2DSample(T_Thinness, RMS_WRAP, UV0).r;
}
if (S_Thickness > 0.5)
{
    RMS_Thickness = Texture2DSample(T_Thickness, RMS_WRAP, UV1).r;
}

// ---------------------------------------------------------------- Eye: a procedural eyeball on UV0 (the iris disc in the
// middle of the 0..1 square). The cornea bulges over the iris, the view refracts through it (IOR 1.49) and the iris maps
// slide under it with the depth of the anterior chamber; the sclera (white) takes over outside radius ~1 (smoothly,
// 0.9..1.1). Two normals: the outer surface (cornea / sclera) and the inner one (iris plane / sclera) for the game's eye
// lighting; the custom data carry the iris's radial direction and its normal in that frame (3 bits + sign each).
float3 EyeGlow = float3(0.0, 0.0, 0.0);
bool EyeInner = false;
float EyeAO = 1.0;
float3 EyeInnerNormal = float3(0.0, 0.0, 1.0);
float EyeScl = 0.0;
float EyeCv = 0.0;
float3 EyeG = float3(0.0, 0.0, 1.0);
float2 EyePi = float2(0.0, 0.0);
float EyeR2 = 0.0;
if (S_Eye > 0.5 || S_HologramEye > 0.5)
{
    float3x3 T2W = Parameters.TangentToWorld;
    float3 V = Parameters.CameraVector;
    float w = 1.0;
    {
        // the basis sign (the bitangent's handedness)
        float3 c = cross(T2W[2], T2W[0]);
        w = (dot(c, T2W[1]) < 0.0) ? -1.0 : 1.0;
    }
    float3 gz = float3(0.0, 0.0, 1.0);
    if (S_GazeNormal > 0.5)
    {
        gz = L.NormalXY(Texture2DSample(T_GazeNormal, RMS_WRAP, UV0));
    }
    float3 G = mul(gz, T2W);
    float3 F1 = normalize(cross(G, T2W[0])) * w;
    float3 F2 = normalize(cross(F1, G)) * w;
    float2 p = float2(UV0.x * 4.0 + -2.0, UV0.y * 4.0 + -2.0);
    float r = sqrt(p.y * p.y + p.x * p.x);
    float sc = saturate((r + -0.89999997615814208984375) * 4.99999904632568359375);
    float scl = (sc * sc) * (3.0 - sc * 2.0);
    float pp = dot(p, p);
    float2 d = p * rsqrt(pp);
    float3 nc = normalize(float3((r * 0.911536872386932373046875) * d.x, (r * -0.911536872386932373046875) * -d.y, d.x * d.x - d.y * -d.y));
    float3 Nc = mul(nc, float3x3(F2, F1, G));
    float cv = dot(Nc, V);
    float k2 = sqrt(max(0.0, 1.0 - (1.0 - cv * cv) * 0.4504301249980926513671875));
    float3 Rf = normalize((Nc * cv - V) * 0.6711409091949462890625 - Nc * k2);
    float gR = dot(G, Rf);
    float depth = max(0.0, 0.37349998950958251953125 - pp * 0.27950000762939453125) * 0.4076640605926513671875;
    float2 uvI = float2(UV0.x - (dot(F2, Rf) / gR) * depth, UV0.y - (dot(F1, Rf) / gR) * depth);
    float2 p2 = float2(uvI.x * 4.0 + -2.0, uvI.y * 4.0 + -2.0);
    float r2 = sqrt(p2.y * p2.y + p2.x * p2.x);
    float rc = saturate(saturate(r2));
    float q2 = rsqrt(dot(p2, p2));
    float2 pi = float2((rc * p2.x) * q2, (p2.y * rc) * q2);
    EyeScl = scl;
    EyeCv = cv;
    EyeG = G;
    EyePi = pi;
    EyeR2 = r2;
    if (S_Eye > 0.5)
    {
    float2 irisUV = (S_EyeMigration > 0.5) ? float2(pi.x * 0.5 + 0.5, pi.y * 0.5 + 0.5) : float2(pi.x * 0.25 + 0.5, pi.y * 0.25 + 0.5);
    float2 irisUVn = float2(pi.x * 0.5 + 0.5, pi.y * 0.5 + 0.5);
    float3 iris = float3(0.0, 0.0, 0.0);
    if (S_IrisColor > 0.5)
    {
        iris = Texture2DSample(T_IrisColor, RMS_WRAP, irisUV).rgb;
    }
    float3 nI = float3(0.0, 0.0, 1.0);
    if (S_IrisNormal > 0.5)
    {
        nI = L.NormalXY(Texture2DSample(T_IrisNormal, RMS_WRAP, irisUVn));
    }
    float io = 1.0;
    if (S_IrisOcclusion > 0.5)
    {
        io = Texture2DSample(T_IrisOcclusion, RMS_WRAP, irisUVn).r;
    }
    if (S_IrisEmissive > 0.5)
    {
        float3 g = Texture2DSample(T_IrisEmissive, RMS_WRAP, irisUVn).rgb;
        EyeGlow = g - g * scl;
    }
    float3 rad = normalize(F1 * p2.y + F2 * p2.x);
    float3 NIw = mul(nI, float3x3(F2, F1, G));
    float3 perp = normalize(cross(G, rad));
    float c0 = (sign(RMS_Noise.x * 2.0 + -1.0) * 0.14285714924335479736328125) * (1.0 - sqrt(1.0 - abs(RMS_Noise.x * 2.0 + -1.0))) + dot(NIw, rad);
    float c1 = (sign(RMS_Noise.y * 2.0 + -1.0) * 0.14285714924335479736328125) * (1.0 - sqrt(1.0 - abs(RMS_Noise.y * 2.0 + -1.0))) + dot(NIw, perp);
    // the outer surface: cornea over the iris, the Normal map's sclera outside; the inner: iris plane / ScleraNormal
    float3 Nm = mul(RMS_Normal, T2W);
    RMS_Normal = mul(T2W, normalize(lerp(Nc, Nm, scl)));
    float3 Ns = G;
    if (S_ScleraNormal > 0.5)
    {
        Ns = mul(L.NormalXY(Texture2DSample(T_ScrelaNormal, RMS_WRAP, UV0)), T2W);
    }
    EyeInner = true;
    EyeInnerNormal = mul(T2W, normalize(lerp(G, Ns, scl)));
    BaseColor = lerp(iris, BaseColor, scl);
    RMS_ShadingModel = 9.0;
    RMS_ModelParam = 0.645419657230377197265625;
    RMS_Metallic = scl;
    RMS_Specular = io;
    RMS_Roughness = 0.07999999821186065673828125;
    EyeAO = r2 * 0.5;
    uint qy = uint(clamp(int(abs(c1 * 7.0) + 0.5), 0, 7));
    uint qx = uint(clamp(int(abs(c0 * 7.0) + 0.5), 0, 7));
    uint sy = uint(c1 > 0.0) - uint(c1 < 0.0);
    uint sx = uint(c0 > 0.0) - uint(c0 < 0.0);
    RMS_Custom = float4(saturate(rad * 0.5 + 0.5), float((((qy << 4) * sy) + 128u) | ((qx * sx) + 8u)) * 0.0039215688593685626983642578125);
    }
}

// ---------------------------------------------------------------- Gradient: the surface goes back and forth between its
// own maps and the Gradient* ones, each texel at its own phase (GradientPhase) along AnimateTimeContext.x
if (S_Gradient > 0.5)
{
    float phase = 0.0;
    if (S_GradientPhase > 0.5)
    {
        phase = saturate(Texture2DSample(T_GradientPhase, RMS_WRAP, UV0).r) * 0.99609375;
    }
    if (S_AnimateTime > 0.5)
    {
        phase = phase + V_AnimateTimeContext.x;
    }
    float tri = saturate(abs(frac(phase) * 2.0 + -1.0));
    float g = (tri * tri) * (3.0 - tri * 2.0);
    if (S_GradientNormal > 0.5)
    {
        RMS_Normal = normalize(lerp(RMS_Normal, L.NormalXY(Texture2DSample(T_GradientNormal, RMS_WRAP, UV0)), g));
    }
    if (S_GradientRoughness > 0.5)
    {
        float rg = Texture2DSample(T_GradientRoughness, RMS_WRAP, UV0).r;
        RMS_Roughness = sqrt(saturate(lerp(RMS_Roughness * RMS_Roughness, rg * rg, g)));
    }
    if (S_GradientOcclusion > 0.5)
    {
        RMS_AO = saturate(lerp(RMS_AO, Texture2DSample(T_GradientOcclusion, RMS_WRAP, UV0).r, g));
    }
}

float Coverage = 1.0;
if (S_Coverage > 0.5)
{
    Coverage = Texture2DSample(T_Coverage, RMS_WRAP, UV0).r;
}

// ---------------------------------------------------------------- WideOcclusion (Coordinate1): a second, wide AO
if (S_WideOcclusion > 0.5)
{
    RMS_AO = L.CombineOcclusion(RMS_AO, Texture2DSample(T_WideOcclusion, RMS_WRAP, UV1).r);
}

// ---------------------------------------------------------------- Detail (Coordinate2): finer maps, faded in by the Detail
// mask (without the Detail switch they apply fully)
float DetailMask = 1.0;
bool DetailFade = S_Detail > 0.5;
if (DetailFade)
{
    DetailMask = Texture2DSample(T_Detail, RMS_WRAP, UV0).r;
}
if (S_DetailColor > 0.5)
{
    float3 dc = saturate(Texture2DSample(T_DetailColor, RMS_WRAP, UV2).rgb * BaseColor);
    BaseColor = DetailFade ? lerp(BaseColor, dc, DetailMask) : dc;
}
if (S_DetailNormal > 0.5)
{
    float3 d = float3(0.0, 0.0, 1.0);
    if (Flowing && S_FlowDetailNormal > 0.5)
    {
        // (each read turned into Coordinate0's frame by its own flowing coordinates)
        float3 a = L.RotateToUV(L.NormalXY(Texture2DSample(T_DetailNormal, RMS_WRAP, FlowA2)), UV0, FlowA2);
        float3 b = L.RotateToUV(L.NormalXY(Texture2DSample(T_DetailNormal, RMS_WRAP, FlowB2)), UV0, FlowB2);
        d = normalize(lerp(a, b, FlowW2));
    }
    else
    {
        d = L.RotateToUV(L.NormalXY(Texture2DSample(T_DetailNormal, RMS_WRAP, UV2)), UV0, UV2);
    }
    RMS_Normal = L.ArcBlend(RMS_Normal, L.Reoriented(RMS_Normal, d), DetailMask);
}
if (S_DetailRoughness > 0.5)
{
    float rd = 0.0;
    if (Flowing && S_FlowDetailRoughness > 0.5)
    {
        float a = Texture2DSample(T_DetailRoughness, RMS_WRAP, FlowA2).r;
        float b = Texture2DSample(T_DetailRoughness, RMS_WRAP, FlowB2).r;
        float a2 = a * a;
        rd = sqrt(saturate((b * b - a2) * FlowW2 + a2));
    }
    else
    {
        rd = Texture2DSample(T_DetailRoughness, RMS_WRAP, UV2).r;
    }
    float r = sqrt(saturate(rd * rd + RMS_Roughness * RMS_Roughness));
    RMS_Roughness = DetailFade ? lerp(RMS_Roughness, r, DetailMask) : r;
}
if (S_DetailFoam > 0.5)
{
    // the detail foam joins the base foam where the base has none ("screen"), by the Detail mask
    float df = 0.0;
    if (Flowing && S_FlowDetailFoam > 0.5)
    {
        float a = Texture2DSample(T_DetailFoam, RMS_WRAP, FlowA2).r;
        float b = Texture2DSample(T_DetailFoam, RMS_WRAP, FlowB2).r;
        df = saturate((b - a) * FlowW2 + a);
    }
    else
    {
        df = saturate(Texture2DSample(T_DetailFoam, RMS_WRAP, UV2).r);
    }
    float inv = 1.0 - Foam;
    Foam = (inv - (1.0 - df) * inv) * DetailMask + Foam;
}
// how much of it shows (WideFoamThreshold, Coordinate1); the game fades it out in shallow water (over 50 units of depth)
if (S_WideFoamThreshold > 0.5)
{
    Foam = Foam * Texture2DSample(T_WideFoamThreshold, RMS_WRAP, UV1).r;
}
RMS_Foam = saturate(Foam);

// ---------------------------------------------------------------- Ocean: open water. Its height is six octaves of crossing
// waves in world space (each half as high and twice as fine as the last, turned 126 degrees, running at the speed deep-water
// waves of that size have, along AnimateTimeContext.z; a hashed value noise shifts their phase). Foam breaks out where the
// waves pile up over shallow ground: OceanGeometry gives the sea floor under the point (xy: its offset, z x 100: its
// height), the vertex expression the ocean's origin (xy) and two depths from the ocean's vertex factory (zw), and two
// Perlin noises drifting with time break it up. Waves and foam lift the surface (its normal from the lifted position's
// screen-space slopes), flattening with distance. The foam is the surface's diffuse, opaque, rough part (a near-white 0.81).
if (S_Ocean > 0.5)
{
    float3 P = Parameters.WorldPosition_CamRelative;
    float t = V_AnimateTimeContext.z;
    float2 pp = float2((P.x - RMS_VertexExpression.x) * 0.0024999999441206455230712890625, (P.y - RMS_VertexExpression.y) * 0.0024999999441206455230712890625);
    float2 pq = float2(View_PreViewTranslation.x * -0.0024999999441206455230712890625, View_PreViewTranslation.y * -0.0024999999441206455230712890625);
    float amp = 0.5;
    float freq = 1.0;
    float wave = 0.0;
    for (int i = 0; i < 6; ++i)
    {
        float2 a = float2(pq.x * freq, pq.y * freq);
        float2 b = float2(pp.x * freq, pp.y * freq);
        float gx = frac(frac(a.x * 0.00999999977648258209228515625) + frac(b.x * 0.00999999977648258209228515625)) * 256.0;
        float gy = frac(frac(a.y * 0.00999999977648258209228515625) + frac(b.y * 0.00999999977648258209228515625)) * 256.0;
        uint cx = uint(int(floor(gx)));
        uint cy = uint(int(floor(gy)));
        float fx = float(int(cx & 255u));
        float fy = float(int(cy & 255u));
        float fx1 = float(int((cx + 1u) & 255u));
        float fy1 = float(int((cy + 1u) & 255u));
        float h00 = frac(sin(dot(float2(fx, fy), float2(127.09999847412109375, 311.70001220703125))) * 43758.546875);
        float h01 = frac(sin(dot(float2(fx, fy1), float2(127.09999847412109375, 311.70001220703125))) * 43758.546875);
        float h10 = frac(sin(dot(float2(fx1, fy), float2(127.09999847412109375, 311.70001220703125))) * 43758.546875);
        float h11 = frac(sin(dot(float2(fx1, fy1), float2(127.09999847412109375, 311.70001220703125))) * 43758.546875);
        float sx = saturate(frac(gx));
        float wx = (sx * sx) * (3.0 - sx * 2.0);
        float sy = saturate(frac(gy));
        float wy = (sy * sy) * (3.0 - sy * 2.0);
        float n0 = wx * (h10 - h00) + h00;
        float n1 = wx * (h11 - h01) + h01;
        float nz = (wy * (n1 - n0) + n0) * 0.5;
        float ph = frac((t * 7.957746982574462890625) * sqrt(freq * 0.00153938052244484424591064453125));
        float ax = frac(((frac(a.x) + frac(b.x)) + ph) + nz) * 6.283185482025146484375;
        float ay = frac(((frac(a.y) + frac(b.y)) + ph) + nz) * 6.283185482025146484375;
        float kx = 1.0 - abs(sin(ax));
        float ky = 1.0 - abs(sin(ay));
        wave = (1.0 - sqrt(((abs(cos(ay)) - ky) * ky + ky) * ((abs(cos(ax)) - kx) * kx + kx))) * amp + wave;
        amp = amp * 0.5;
        freq = freq * 2.0;
        pp = float2(pp.y * 0.809017121791839599609375 + pp.x * -0.587785065174102783203125, pp.y * -0.587785065174102783203125 + pp.x * -0.809017121791839599609375);
        pq = float2(pq.y * 0.809017121791839599609375 + pq.x * -0.587785065174102783203125, pq.y * -0.587785065174102783203125 + pq.x * -0.809017121791839599609375);
    }
    float3 W = float3(P.x - View_PreViewTranslation.x, P.y - View_PreViewTranslation.y, P.z - View_PreViewTranslation.z);
    float4 g = float4(0.0, 0.0, 0.0, 0.0);
    if (S_OceanGeometry > 0.5)
    {
        g = Texture2DSampleLevel(T_OceanGeometry, RMS_BILINEAR_CLAMP, UV0, 0.0);
    }
    float rx = W.x - RMS_VertexExpression.x;
    float ry = W.y - RMS_VertexExpression.y;
    float above = W.z - g.z * 100.0;
    float shore = (saturate(1.0 - above * 0.0033333334140479564666748046875) * saturate(1.0 - above * 0.0024999999441206455230712890625)) * saturate(1.0 - sqrt(g.x * g.x + g.y * g.y) * 0.00166666670702397823333740234375);
    float s2 = shore * shore;
    float d1 = saturate((RMS_VertexExpression.z - RMS_VertexExpression.w) * 0.0333333350718021392822265625);
    float d2 = saturate(abs(RMS_VertexExpression.w) * 0.01666666753590106964111328125);
    float c = saturate(wave * 0.100000001490116119384765625) * 0.050000011920928955078125 + 0.949999988079071044921875;
    float c2 = c * c;
    float c4 = c2 * c2;
    float na = Texture3DSample(View_PerlinNoise3DTexture, View_PerlinNoise3DTextureSampler, float3(t * 0.125, rx * 0.001953125, ry * 0.001953125)).x;
    float nb = Texture3DSample(View_PerlinNoise3DTexture, View_PerlinNoise3DTextureSampler, float3(rx * 0.00390625, ry * 0.00390625, t * 0.0625)).x;
    float crest = saturate((c4 * c4) * (sqrt(na * nb) * 0.5 + 0.5));
    float br = saturate((sqrt(saturate(((s2 + -1.0) + crest) * crest)) * ((d1 * d1) * (1.0 - d2) + d2)) * (((crest + s2) > 1.0) ? 1.0 : 0.0));
    float foam = (br * br) * (3.0 - br * 2.0);
    float f2 = foam * foam;
    float op = saturate(f2 * f2);
    float lift = (sqrt(s2) * (crest * 4.0 - wave) + wave) + foam * 6.0;
    float3 ng = normalize(cross(ddx_fine(P), ddy_fine(P)));
    float3 Pd = ng * lift + P;
    float3 nd = normalize(cross(ddx_fine(Pd), ddy_fine(Pd)));
    float3x3 T2W = Parameters.TangentToWorld;
    float3 wn = normalize((T2W[2] - ng) + nd);
    float fd = Parameters.SvPosition.w * 9.9999997473787516355514526367188e-06;
    float fade = 1.0 / (fd * fd + 1.0);
    // (far off: straight up)
    RMS_Normal = normalize(float3(lerp(T2W[0].z, dot(T2W[0], wn), fade), lerp(T2W[1].z, dot(T2W[1], wn), fade), lerp(T2W[2].z, dot(T2W[2], wn), fade)));
    BaseColor = float3(0.810000002384185791015625, 0.810000002384185791015625, 0.810000002384185791015625);
    RMS_Metallic = 0.0;
    RMS_AO = 1.0;
    RMS_Opacity = op;
    RMS_Roughness = sqrt(op);
    RMS_Foam = saturate(foam);
}
if (S_DetailOcclusion > 0.5)
{
    float od = L.CombineOcclusion(RMS_AO, Texture2DSample(T_DetailOcclusion, RMS_WRAP, UV2).r);
    RMS_AO = DetailFade ? lerp(RMS_AO, od, DetailMask) : od;
}
if (S_DetailCoverage > 0.5)
{
    float dc = saturate(Texture2DSample(T_DetailCoverage, RMS_WRAP, UV2).r * Coverage);
    Coverage = DetailFade ? lerp(Coverage, dc, DetailMask) : dc;
}
// (DetailMetallic: switched on in the two Overlay permutations, but the game's base pass reads no metallic detail)

// ---------------------------------------------------------------- LayeredColor: the base colour overlaid onto a layer
// colour (paint-program "overlay", in sRGB)
if (S_LayeredColor > 0.5)
{
    float3 lc = L.LinearToSrgb(Texture2DSample(T_LayeredColor, RMS_WRAP, UV0).rgb);
    float3 cs = L.LinearToSrgb(BaseColor);
    BaseColor = L.SrgbToLinear(float3(L.Overlay1(lc.x, cs.x), L.Overlay1(lc.y, cs.y), L.Overlay1(lc.z, cs.z)));
}

// ---------------------------------------------------------------- CylindricalNormal (hair): the view direction made
// perpendicular to the strand (dithered where the strand points at the camera); before the wet layer, which starts from it
if (S_CylindricalNormal > 0.5)
{
    float3 n = RMS_Normal;
    float3 a = normalize(float3(n.z, 0.0, -n.x));
    float3 t = normalize(cross(a, n));
    float3 v = mul(Parameters.TangentToWorld, Parameters.CameraVector);
    float d = dot(v, t);
    if (abs(d) < 0.0500000007450580596923828125)
    {
        d = sign((RMS_Noise.x * 2.0 + -1.0) + d * 20.0) * 0.0500000007450580596923828125;
    }
    RMS_Normal = normalize(v - t * d);
}

// ---------------------------------------------------------------- Wetness: a water film (its own, smoother normal for the
// game's wet layer, and two 4-bit flags); rain on the sides and puddles on top displace it, from the engine's EBuffer
if (S_Wetness > 0.5)
{
    float wet = 0.0;
    if (S_WetnessTrickle > 0.5)
    {
        // trickles: the Wetness map is a column of frames (as many as it is tall over wide), cross-faded along
        // AnimateTimeContext.z
        uint ww;
        uint wh;
        T_Wetness.GetDimensions(ww, wh);
        float aspect = float(ww) / float(wh);
        uint frames = max(1u, uint(max(1.0, round(float(wh) / float(ww)))));
        float t = V_AnimateTimeContext.z + 0.5;
        float ft = trunc(t);
        uint f = uint(int(ft)) + frames;
        float a = Texture2DSample(T_Wetness, RMS_WRAP, float2(UV0.x, (float((f + 4294967295u) % frames) + UV0.y) * aspect)).r;
        float b = Texture2DSample(T_Wetness, RMS_WRAP, float2(UV0.x, (float(f % frames) + UV0.y) * aspect)).r;
        float fr = saturate(t - ft);
        wet = lerp(a, b, (fr * fr) * (3.0 - fr * 2.0));
    }
    else
    {
        wet = Texture2DSample(T_Wetness, RMS_WRAP, UV0).r;
    }
    float rain = L.RainEase(saturate(saturate(RMS_EBuffer.z)));
    float flag = (RMS_EBuffer.w > 0.0) ? 1.0 : 0.0;
    float3 vn = Parameters.TangentToWorld[2];
    float up = saturate(vn.z);
    float up2 = up * up;
    float up4 = up2 * up2;
    float side = sqrt(max(0.0, 1.0 - vn.z * vn.z));
    float side2 = side * side;
    float puddle = L.Half8x2(RMS_EBuffer.x, RMS_EBuffer.y);
    float disp = 0.0;
    if (S_WetnessTrickle > 0.5)
    {
        // (the trickles themselves stand out of the film: + 0.2)
        disp = ((((puddle * 0.20000000298023223876953125) * saturate(up4 * up4)) + 0.20000000298023223876953125) + ((saturate(rain) * 0.4000000059604644775390625) * saturate((side2 * side2) * side))) * wet;
    }
    else
    {
        disp = (wet * 0.20000000298023223876953125) * (((saturate(rain) * 2.0) * saturate((side2 * side2) * side)) + saturate(up4 * up4) * puddle);
    }
    float3 P = Parameters.WorldPosition_CamRelative;
    float3 ng = normalize(cross(ddx_fine(P), ddy_fine(P)));
    float3 Pd = ng * disp + P;
    float3 nd = normalize(cross(ddx_fine(Pd), ddy_fine(Pd)));
    float3 wn = normalize((vn - ng) + nd);
    WetNormal = normalize(lerp(RMS_Normal, mul(Parameters.TangentToWorld, wn), pow(saturate(wet), 0.25)));
    HasWetNormal = true;
    float w16 = saturate(wet * 16.0);
    RMS_WetLayer = float2((1.0 - w16) * flag + w16, w16 * (1.0 - flag));
}

// ---------------------------------------------------------------- Materia: the magic orb. Black, mirror-smooth glass whose
// glow is turbulence in a spinning cloud of Perlin noise, seen through the sphere (the vertex expression: the sphere's own
// direction at the vertex); brighter facing the camera. MateriaIndexed: one of eight orbs (UV2.x's whole part) takes its
// type from GenericVector0/1Context, its colour and coverage from that column of the MateriaContext strip, and its own
// phase.
float3 MateriaGlow = float3(0.0, 0.0, 0.0);
bool HasMateria = false;
if (S_Materia > 0.5)
{
    BaseColor = float3(0.0, 0.0, 0.0);
    RMS_Metallic = 0.0;
    RMS_Roughness = 0.0;
    float phase = 0.0;
    float4 mc = float4(1.0, 1.0, 1.0, 1.0);
    if (S_MateriaIndexed > 0.5)
    {
        uint idx = uint(int(min(max(0.0, floor(UV2.x)), 7.0)));
        float4 gv = (idx < 4u) ? V_GenericVector0Context : V_GenericVector1Context;
        uint kind = uint(int(gv[idx & 3u]));
        mc = T_MateriaContext.Load(int3(int(kind), 0, 0));
        phase = float(int(idx)) * 0.125;
        Coverage = mc.a;
    }
    float a = frac(phase + V_AnimateTimeContext.x) * 6.283185482025146484375;
    float s = sin(a);
    float c = cos(a);
    float3 ve = float3(RMS_VertexExpression.x, RMS_VertexExpression.y, RMS_VertexExpression.z);
    float3 q0 = ve * 0.5 + 0.5;
    // Rz(a) Ry(a) Rx(a)
    float3x3 R = float3x3(float3(c * c, -s * c + (s * s) * c, -s * -s + (s * c) * c),
                          float3(s * c, c * c + (s * s) * s, c * -s + (s * c) * s),
                          float3(-s, c * s, c * c));
    float n1 = Texture3DSample(View_PerlinNoise3DTexture, View_PerlinNoise3DTextureSampler, mul(R, q0) * 0.5).x;
    float3 dir = -Parameters.CameraVector;
    float3 qa = (dir * n1 + ve) * 0.25 + 0.25;
    float3 qb = ((dir * 1.2000000476837158203125) * n1 + ve) * 0.5 + 0.5;
    float3 qc = ((dir * 0.800000011920928955078125) * n1 + ve) * 0.125 + 0.125;
    float na = Texture3DSample(View_PerlinNoise3DTexture, View_PerlinNoise3DTextureSampler, float3(s * qa.z + qa.x * c, qa.y, c * qa.z + qa.x * -s)).x;
    float nb = Texture3DSample(View_PerlinNoise3DTexture, View_PerlinNoise3DTextureSampler, float3(qb.x, -s * qb.z + c * qb.y, c * qb.z + s * qb.y)).x;
    float nc = Texture3DSample(View_PerlinNoise3DTexture, View_PerlinNoise3DTextureSampler, float3(-s * qc.y + qc.x * c, c * qc.y + qc.x * s, qc.z)).x;
    float g = (na * nb) * nc;
    float facing = saturate(dot(mul(RMS_Normal, Parameters.TangentToWorld), Parameters.CameraVector)) * (g * g);
    float glow = (facing * facing) * 4096.0;
    MateriaGlow = (S_MateriaIndexed > 0.5) ? float3(mc.x * glow, mc.y * glow, mc.z * glow) : float3(glow, glow, glow);
    HasMateria = true;
}

// ---------------------------------------------------------------- Hologram: a see-through glow: rim and face-on light,
// stronger on upward faces, broken into sparkles by a 3D blue noise fixed to the body (the vertex expression: its own
// position), dimmed by the occlusion (as specular occlusion); fades in from the far plane
float3 HologramGlow = float3(0.0, 0.0, 0.0);
bool HasHologram = false;
float HoloG = 0.0;
if (S_Hologram > 0.5 || S_Phantom > 0.5)
{
    float3 Nw = mul(RMS_Normal, Parameters.TangentToWorld);
    float NoV = saturate(dot(Nw, Parameters.CameraVector));
    float a = 1.0 - NoV;
    float a2 = a * a;
    float b2 = NoV * NoV;
    float3 ve = float3(RMS_VertexExpression.x, RMS_VertexExpression.y, RMS_VertexExpression.z);
    float sparkle = Env.BlueNoise3D(int3(int(round(frac(ve.x * 0.5) * 64.0)) & 63, int(round(frac(ve.y * 0.5) * 64.0)) & 63, int(round(frac(ve.z * 0.5) * 64.0)) & 255)).x;
    float rim = (a2 * a2) * a + (b2 * b2) * NoV;
    float rough = RMS_Roughness;
    if (S_HologramEye > 0.5)
    {
        // the eye: the pupil and iris seen through the cornea (with its Fresnel), the gaze's rim; the sclera outside
        float cvs = saturate(EyeCv);
        float gv = saturate(dot(EyeG, Parameters.CameraVector));
        float pupil = saturate((sqrt(EyePi.x * EyePi.x + EyePi.y * EyePi.y) + -0.2899999916553497314453125) * 49.999973297119140625);
        float ir = saturate((EyeR2 + -1.0) * -1.4285714626312255859375);
        float irs = (ir * ir) * (3.0 - ir * 2.0);
        float irs2 = irs * irs;
        float io = 1.0;
        if (S_IrisOcclusion > 0.5)
        {
            io = Texture2DSample(T_IrisOcclusion, RMS_WRAP, float2(EyePi.x * 0.5 + 0.5, EyePi.y * 0.5 + 0.5)).r;
        }
        float m = (((pupil * pupil) * io) * (3.0 - pupil * 2.0)) * ((irs2 * irs2 - irs) * 0.5 + irs);
        float ga = 1.0 - gv;
        float ga2 = ga * ga;
        float gv2 = gv * gv;
        float g5 = ((ga2 * ga2) * ga + (gv2 * gv2) * gv) * saturate((pow(m + gv, 7.62939453125e-06) + -1.0) + m);
        float ca = 1.0 - cvs;
        float ca2 = ca * ca;
        float ca4 = ca2 * ca2;
        float cvs2 = cvs * cvs;
        float c5 = ca4 * ca + (cvs2 * cvs2) * cvs;
        float eyeRim = lerp(g5, c5, ca4 * (ca * 0.961274802684783935546875) + 0.03872518241405487060546875);
        rim = lerp(eyeRim, rim, EyeScl);
        rough = 0.07999999821186065673828125;
    }
    float so = saturate((RMS_AO + -1.0) + pow(RMS_AO + NoV, exp2(-1.0 - rough * 16.0)));
    HoloG = ((rim * (Nw.z * 0.5 + 0.5)) * sparkle) * so;
    if (S_Hologram > 0.5)
    {
        HologramGlow = float3(HoloG, HoloG, HoloG);
        HasHologram = true;
        RMS_Opacity = L.FarFade(Parameters.SvPosition.w, View_InvDeviceZToWorldZTransform);
    }
}

// ---------------------------------------------------------------- Phantom: the hologram's light as a colour between the
// ToneGradient's first two texels, over a body that fades in from the far plane over GenericVector0Context.x x 50 units
// (50 by default), blocking the background as much as it shows
float3 PhantomGlow = float3(0.0, 0.0, 0.0);
bool HasPhantom = false;
if (S_Phantom > 0.5)
{
    float g = saturate(HoloG);
    float3 t0 = float3(1.0, 1.0, 1.0);
    float3 t1 = float3(1.0, 1.0, 1.0);
    if (S_ToneGradient > 0.5)
    {
        t0 = T_ToneGradient.Load(int3(0, 0, 0)).rgb;
        t1 = T_ToneGradient.Load(int3(1, 0, 0)).rgb;
    }
    PhantomGlow = lerp(t0, t1, g);
    HasPhantom = true;
    float dist = (V_GenericVector0Context.x > 0.0) ? V_GenericVector0Context.x * 50.0 : 50.0;
    float f = saturate(saturate((1.0 / max(1.0, dist)) * ((View_InvDeviceZToWorldZTransform.y - Parameters.SvPosition.w) + 1.0 / -View_InvDeviceZToWorldZTransform.w)));
    float fade = (f * f) * (3.0 - f * 2.0);
    float f2 = fade * fade;
    float f4 = f2 * f2;
    RMS_Opacity = f4 * f4;
    RMS_ColoredOpacity = float3(fade, fade, fade);
}

// ---------------------------------------------------------------- Ghost: a glow at grazing... no: face-on (N.V^5), in the
// colour of a ToneGradient picked by turbulence: three Perlin noises streaming along the object's axes (looped over 1, 1/2
// and 1/4 of AnimateTimeContext.x), their geometric mean; brightness from the occlusion; fades in from the far plane
float3 GhostGlow = float3(0.0, 0.0, 0.0);
bool HasGhost = false;
if (S_Ghost > 0.5)
{
    float3 Nw = mul(RMS_Normal, Parameters.TangentToWorld);
    float NoV = saturate(dot(Nw, Parameters.CameraVector));
    float3 q = float3(RMS_VertexExpression.x, RMS_VertexExpression.y, RMS_VertexExpression.z) * 0.00999999977648258209228515625;
    float t = V_AnimateTimeContext.x;
    float f4 = frac(t * 4.0);
    float f2 = frac(t * 2.0);
    float f1 = frac(t);
    float3 cx = float3(RMS_LocalToWorld0.x, RMS_LocalToWorld1.x, RMS_LocalToWorld2.x);
    float3 cy = float3(RMS_LocalToWorld0.y, RMS_LocalToWorld1.y, RMS_LocalToWorld2.y);
    float3 cz = float3(RMS_LocalToWorld0.z, RMS_LocalToWorld1.z, RMS_LocalToWorld2.z);
    float pa = Texture3DSample(View_PerlinNoise3DTexture, View_PerlinNoise3DTextureSampler, q - cz * f4).x;
    float pb = Texture3DSample(View_PerlinNoise3DTexture, View_PerlinNoise3DTextureSampler, (cz + q) - cz * f4).x;
    float3 qy = q + 0.3300000131130218505859375;
    float pc = Texture3DSample(View_PerlinNoise3DTexture, View_PerlinNoise3DTextureSampler, (qy - cy * f2) * 0.5).x;
    float pd = Texture3DSample(View_PerlinNoise3DTexture, View_PerlinNoise3DTextureSampler, ((qy + cy) - cy * f2) * 0.5).x;
    float3 qx = q + 0.660000026226043701171875;
    float pe = Texture3DSample(View_PerlinNoise3DTexture, View_PerlinNoise3DTextureSampler, (qx - cx * f1) * 0.25).x;
    float pf = Texture3DSample(View_PerlinNoise3DTexture, View_PerlinNoise3DTextureSampler, ((qx + cx) - cx * f1) * 0.25).x;
    float turb = saturate(exp2(log2((lerp(pc, pd, f2) * lerp(pa, pb, f4)) * lerp(pe, pf, f1)) * 0.3333333432674407958984375));
    float3 tone = float3(1.0, 1.0, 1.0);
    if (S_ToneGradient > 0.5)
    {
        uint tw;
        uint th;
        T_ToneGradient.GetDimensions(tw, th);
        float w = float(tw);
        tone = Texture2DSampleLevel(T_ToneGradient, RMS_WRAP, float2(((w + -1.0) * turb + 0.5) * (1.0 / w), 0.5 / float(th)), 0.0).rgb;
    }
    float n2 = NoV * NoV;
    float n5 = (n2 * n2) * NoV;
    GhostGlow = tone * (RMS_AO * n5);
    HasGhost = true;
    RMS_Opacity = L.FarFade(Parameters.SvPosition.w, View_InvDeviceZToWorldZTransform);
}

// ---------------------------------------------------------------- Coverage: dithered cut-out (the per-object fade first).
// Always worked out; the instance's blend mode decides whether it is applied (masked and translucent ones: discarded below 0)
RMS_OpacityMask = (RMS_DynamicCoverage > RMS_Noise.w * 0.99609375 + 0.001953125) ? L.Dithered(Coverage, RMS_Noise.x) : -1.0;

// ---------------------------------------------------------------- Segmented: two masked recolours of the base colour
// (GenericVector0/1Context: rgb = the tint, a = how much), then albedo kept in the physically plausible range
if (S_Segmented > 0.5)
{
    float3 c = BaseColor;
    float3 cs = L.LinearToSrgb(c);
    if (S_SegmentLayer0 > 0.5)
    {
        float w = saturate(V_GenericVector0Context.w) * Texture2DSample(T_SegmentLayer0, RMS_WRAP, UV0).r;
        c = lerp(c, L.SegmentTint(cs, V_GenericVector0Context.xyz), w);
    }
    if (S_SegmentLayer1 > 0.5)
    {
        float w = saturate(V_GenericVector1Context.w) * Texture2DSample(T_SegmentLayer1, RMS_WRAP, UV0).r;
        c = lerp(c, L.SegmentTint(cs, V_GenericVector1Context.xyz), w);
    }
    float3 dielectric = min(max(c, float3(0.00604883022606372833251953125, 0.00604883022606372833251953125, 0.00604883022606372833251953125)), float3(1.0, 1.0, 1.0));
    float3 metal = min(max(c, float3(0.2581828534603118896484375, 0.2581828534603118896484375, 0.2581828534603118896484375)), float3(1.0, 1.0, 1.0));
    BaseColor = lerp(dielectric, metal, RMS_Metallic);
}

// ---------------------------------------------------------------- Extra layers (Coordinate2): a decal-like colour / glow
// image placed by the Extra*CoordinateContext rectangles (pixels, kept half a texel inside; or 0..1)
if (S_ExtraColor > 0.5)
{
    uint ew;
    uint eh;
    T_ExtraColor.GetDimensions(ew, eh);
    float2 uv = L.ExtraCoordinate(UV2, S_ExtraPixelCoordinate, V_ExtraPixelCoordinateContext, S_ExtraNormalizedCoordinate, V_ExtraNormalizedCoordinateContext, ew, eh);
    float4 x = Texture2DSampleLevel(T_ExtraColor, RMS_BILINEAR_WRAP, uv, 0.0);
    BaseColor = BaseColor * x.a + x.rgb;
}

// ---------------------------------------------------------------- Emissive (with the eye's iris glow; the materia's glow)
if (S_Emissive > 0.5 || HasMateria || HasHologram || HasGhost || HasPhantom)
{
    float3 e = float3(0.0, 0.0, 0.0);
    if (HasMateria)
    {
        e = MateriaGlow;
    }
    else if (HasPhantom)
    {
        e = PhantomGlow;
    }
    else if (HasHologram)
    {
        e = HologramGlow;
    }
    else if (HasGhost)
    {
        e = GhostGlow;
    }
    else if (S_ViewCoordinate > 0.5)
    {
        // a full-screen image (fitted to 16:9), not on the surface
        float2 sv = float2((Parameters.SvPosition.x - View_ViewRectMin.x) * View_ViewSizeAndInvSize.z + -0.5, (Parameters.SvPosition.y - View_ViewRectMin.y) * View_ViewSizeAndInvSize.w + -0.5);
        float2 fit = float2(min((View_ViewSizeAndInvSize.x * 0.5625) * View_ViewSizeAndInvSize.w, 1.0), min((View_ViewSizeAndInvSize.y * 1.77777779102325439453125) * View_ViewSizeAndInvSize.z, 1.0));
        e = Texture2DSampleLevel(T_Emissive, RMS_BILINEAR_CLAMP, float2(sv.x * fit.x + 0.5, fit.y * sv.y + 0.5), 0.0).rgb;
    }
    else
    {
        e = Texture2DSample(T_Emissive, RMS_WRAP, UV0).rgb + EyeGlow;
    }
    float k = 1.0;
    if (S_ExternalEmissive > 0.5)
    {
        k = (V_ExternalEmissiveContext.w > 0.0) ? View_OneOverPreExposure : 1.0;
        e = e * V_ExternalEmissiveContext.xyz;
    }
    // BrokenFlow: the glow modulated by two images streaming over the surface (Coordinate2) along the WideFlow field
    // (Coordinate1: direction map, per-texel phase, directivity), each at its GenericVector*Context (x = speed along
    // AnimateTimeContext.z, y = travel per cycle)
    if (S_BrokenFlow > 0.5)
    {
        float2 dir = float2(0.0, 0.0);
        if (S_WideFlowDirection > 0.5)
        {
            float3 fd = L.NormalXY(Texture2DSample(T_WideFlowDirection, RMS_WRAP, UV1));
            dir = float2(fd.x, fd.y);
        }
        float ph = 0.0;
        if (S_WideFlowPhase > 0.5)
        {
            ph = Texture2DSample(T_WideFlowPhase, RMS_WRAP, UV1).r;
        }
        float dv = 1.0;
        if (S_WideFlowDirectivity > 0.5)
        {
            dv = Texture2DSample(T_WideFlowDirectivity, RMS_WRAP, UV1).r;
        }
        float tm = (S_AnimateTime > 0.5) ? V_AnimateTimeContext.z : 0.0;
        if (S_BrokenFlowEmissive0 > 0.5)
        {
            e = e * L.FlowLayer(T_BrokenFlowEmissive0, RMS_WRAP, UV2, dir, ph, dv, tm, V_GenericVector0Context);
        }
        if (S_BrokenFlowEmissive1 > 0.5)
        {
            e = e * L.FlowLayer(T_BrokenFlowEmissive1, RMS_WRAP, UV2, dir, ph, dv, tm, V_GenericVector1Context);
        }
    }
    if (S_ExtraEmissive > 0.5)
    {
        uint ew;
        uint eh;
        T_ExtraEmissive.GetDimensions(ew, eh);
        float2 uv = L.ExtraCoordinate(UV2, S_ExtraPixelCoordinate, V_ExtraPixelCoordinateContext, S_ExtraNormalizedCoordinate, V_ExtraNormalizedCoordinateContext, ew, eh);
        e = e * Texture2DSampleLevel(T_ExtraEmissive, RMS_BILINEAR_WRAP, uv, 0.0).rgb;
    }
    RMS_Emissive = e * k;
}

// ---------------------------------------------------------------- shading models
// Each model sets the game's shading model id, its dielectric reflectance F0 (RMS_Reflectance; the editor's Specular is
// F0 / 0.08) and the GBuffer value the game keeps for it, and fills the custom data its lighting reads.
// Layered: two models in one material, chosen per pixel by the ShadingLayer map against the dither noise (the first of
// Standard / Skin where the map is below the noise, Fabric where above).
bool LayerB = false;
if (S_Layered > 0.5 && S_ShadingLayer > 0.5)
{
    LayerB = Texture2DSample(T_ShadingLayer, RMS_WRAP, UV0).r > RMS_Noise.x * 0.99609375 + 0.001953125;
}
bool FirstLayer = !(S_Layered > 0.5 && LayerB);
// Unlit: emissive only (the GBuffer's other targets stay empty)
if (S_Unlit > 0.5)
{
    RMS_ShadingModel = 0.0;
}
// Eye: the occlusion slot holds the distance from the iris centre (after any occlusion maps)
if (S_Eye > 0.5)
{
    RMS_AO = EyeAO;
    RMS_Reflectance = 0.03872518241405487060546875;
}
// Standard (default lit): custom data = (film thickness, film structure, isotropy, 0); the film's structure is 0.4 without one
if (S_Standard > 0.5 && FirstLayer)
{
    RMS_ShadingModel = 1.0;
    RMS_Reflectance = 0.0400000028312206268310546875;
    RMS_Custom.y = 0.4000000059604644775390625;
    if (S_Film > 0.5)
    {
        if (S_FilmThickness > 0.5)
        {
            RMS_Custom.x = Texture2DSample(T_FilmThickness, RMS_WRAP, UV0).r;
        }
        if (S_FilmStructure > 0.5)
        {
            RMS_Custom.y = Texture2DSample(T_FilmStructure, RMS_WRAP, UV0).r;
        }
    }
    if (S_Isotropy > 0.5)
    {
        RMS_Custom.z = Texture2DSample(T_Isotropy, RMS_WRAP, UV0).r;
    }
}
// Skin: the pores map in the custom data, a fixed specular
if (S_Skin > 0.5 && FirstLayer)
{
    RMS_ShadingModel = 3.0;
    RMS_Reflectance = 0.0465205647051334381103515625;
    RMS_ModelParam = 0.684779345989227294921875;
    RMS_Metallic = 0.0;
    RMS_Specular = 0.1500000059604644775390625;
    if (S_Pores > 0.5)
    {
        RMS_Custom.x = Texture2DSample(T_Pores, RMS_WRAP, UV0).r;
    }
}
// Subsurface (the game's subsurface profile model): the Distribution map where the specular would be
if (S_Subsurface > 0.5)
{
    RMS_ShadingModel = 5.0;
    if (S_Distribution > 0.5)
    {
        RMS_Specular = Texture2DSample(T_Distribution, RMS_WRAP, UV0).r;
    }
}
// Blood: its colour from how much oxygen it carries (dark venous to bright arterial), skin-like specular
if (S_Blood > 0.5)
{
    float o2 = 1.0;
    if (S_OxygenSaturation > 0.5)
    {
        o2 = Texture2DSample(T_OxygenSaturation, RMS_WRAP, UV0).r;
    }
    BaseColor = lerp(float3(0.0802, 0.00368, 0.00802), float3(0.913, 0.0, 0.00152), o2);
    RMS_Metallic = 0.0;
    RMS_Specular = 0.1500000059604644775390625;
    RMS_Reflectance = 0.0266276858747005462646484375;
    RMS_ModelParam = 0.4437947571277618408203125;
}
// Hair: (its normal: CylindricalNormal, above) and a wide bent normal for the game's hair lighting in the custom data
if (S_Hair > 0.5)
{
    RMS_ShadingModel = 7.0;
    RMS_Reflectance = 0.0465205647051334381103515625;
    RMS_ModelParam = 0.684779345989227294921875;
    RMS_Metallic = 0.0;
    RMS_Specular = 0.0;
    if (S_WideBentNormal > 0.5)
    {
        float4 b = Texture2DSample(T_WideBentNormal, RMS_WRAP, UV1);
        float3 bn = normalize(float3(b.x * 2.0 + -1.0, b.y * 2.0 + -1.0, b.z * 2.0 + -1.0));
        RMS_Custom = float4(saturate(mul(bn, Parameters.TangentToWorld) * 0.5 + 0.5), 0.0);
    }
}
// Fabric (cloth): never metal, never smoother than 0.5; the Diffusion map in the custom data
if (S_Fabric > 0.5 && (S_Layered < 0.5 || LayerB))
{
    RMS_ShadingModel = 8.0;
    RMS_Reflectance = 0.067215375602245330810546875;
    RMS_ModelParam = 0.742264926433563232421875;
    RMS_Roughness = max(0.5, RMS_Roughness);
    RMS_Metallic = 0.0;
    RMS_Specular = 0.0;
    RMS_Custom = float4(0.0, 0.0, 0.0, 0.0);
    if (S_Diffusion > 0.5)
    {
        RMS_Custom.x = Texture2DSample(T_Diffusion, RMS_WRAP, UV0).r;
    }
}
// (a layered material works the GBuffer value out from the reflectance per pixel)
if (S_Layered > 0.5)
{
    RMS_ModelParam = L.EncodeReflectance(RMS_Reflectance);
}
// The lit translucent ones, for the game's translucent lighting (it works these in as constants): the reflectance at
// normal incidence of the dielectric (ReflectanceGlass 0.04, an IOR of 1.5; ReflectanceWater 0.0204, 1.333;
// ReflectanceCrystal 0.16, ~2.33; metal takes the base colour as usual), how its medium scatters (PhaseG*: the
// Cornette-Shanks asymmetry, 0 for glass and crystal, -0.6 for water as the game measures it), and how far the light goes
// through the medium (RMS_MediumPath: 1 Thin = Thinness / N.V; 2 Thick = the depth behind the surface, at most
// Thickness x 100; 3 Convex = the depth behind; 4 Pool: a body of water, its depth up to Thickness x 100; 5 Ocean)
if (S_ReflectanceGlass > 0.5)
{
    RMS_Reflectance = 0.0400000028312206268310546875;
}
if (S_ReflectanceWater > 0.5)
{
    RMS_Reflectance = 0.0203731842339038848876953125;
}
if (S_ReflectanceCrystal > 0.5)
{
    RMS_Reflectance = 0.159951984882354736328125;
}
if (S_PhaseGWater > 0.5)
{
    RMS_PhaseG = -0.60000002384185791015625;
}
if (S_Thin > 0.5)
{
    RMS_MediumPath = 1.0;
}
if (S_Thick > 0.5)
{
    RMS_MediumPath = 2.0;
}
if (S_Convex > 0.5)
{
    RMS_MediumPath = 3.0;
}
if (S_Pool > 0.5)
{
    RMS_MediumPath = (S_Ocean > 0.5) ? 5.0 : 4.0;
}

RMS_WetNormal = HasWetNormal ? WetNormal : (EyeInner ? EyeInnerNormal : RMS_Normal);
return BaseColor;

#else
RMS_Metallic = 0.0;
RMS_Specular = 0.0;
RMS_Roughness = 0.0;
RMS_AO = 0.0;
RMS_Normal = float3(0.0, 0.0, 0.0);
RMS_Emissive = float3(0.0, 0.0, 0.0);
RMS_OpacityMask = 0.0;
RMS_Opacity = 0.0;
RMS_ShadingModel = 0.0;
RMS_ModelParam = 0.0;
RMS_Reflectance = 0.0;
RMS_Custom = float4(0.0, 0.0, 0.0, 0.0);
RMS_WetLayer = float2(0.0, 0.0);
RMS_WetNormal = float3(0.0, 0.0, 0.0);
RMS_ColoredOpacity = float3(0.0, 0.0, 0.0);
RMS_Muddiness = float3(0.0, 0.0, 0.0);
RMS_TransparencyLog2 = 0.0;
RMS_TransmittanceLog2 = float3(0.0, 0.0, 0.0);
RMS_Thickness = 0.0;
RMS_PhaseG = 0.0;
RMS_MediumPath = 0.0;
RMS_Foam = 0.0;
return float3(0.0, 0.0, 0.0);
#endif

}
float4 main(float4 pos : SV_Position, float4 uv01 : TEXCOORD0, float4 uv23 : TEXCOORD1, float3 t0 : TEXCOORD2, float3 t2 : TEXCOORD3, float3 wp : TEXCOORD4) : SV_Target
{
    FMaterialPixelParameters P = (FMaterialPixelParameters)0;
    P.SvPosition = pos;
    P.TangentToWorld = float3x3(t0, cross(t2, t0), t2);
    P.WorldPosition_CamRelative = wp;
    P.CameraVector = normalize(-wp);
    P.TwoSidedSign = 1.0;
    float RMS_Metallic = (float)0;
    float RMS_Specular = (float)0;
    float RMS_Roughness = (float)0;
    float RMS_AO = (float)0;
    float3 RMS_Normal = (float3)0;
    float3 RMS_Emissive = (float3)0;
    float RMS_OpacityMask = (float)0;
    float RMS_Opacity = (float)0;
    float RMS_ShadingModel = (float)0;
    float RMS_ModelParam = (float)0;
    float RMS_Reflectance = (float)0;
    float4 RMS_Custom = (float4)0;
    float2 RMS_WetLayer = (float2)0;
    float3 RMS_WetNormal = (float3)0;
    float3 RMS_ColoredOpacity = (float3)0;
    float3 RMS_Muddiness = (float3)0;
    float RMS_TransparencyLog2 = (float)0;
    float3 RMS_TransmittanceLog2 = (float3)0;
    float RMS_Thickness = (float)0;
    float RMS_PhaseG = (float)0;
    float RMS_MediumPath = (float)0;
    float RMS_Foam = (float)0;
    float3 bc = CustomExpression0(P, uv01.xy, uv01.zw, uv23.xy, uv23.zw, GRMS_Noise, 1.0, GRMS_VertexExpression, GRMS_EBuffer, GRMS_LocalToWorld0, GRMS_LocalToWorld1, GRMS_LocalToWorld2, GT_PositiveTransitionNormal, GT_PositiveTransitionNormalSampler, GT_Roughness, GT_RoughnessSampler, GT_DetailNormal, GT_DetailNormalSampler, GT_DetailRoughness, GT_DetailRoughnessSampler, GT_WideBentNormal, GT_WideBentNormalSampler, GT_WideFlowPhase, GT_WideFlowPhaseSampler, GT_DetailFoam, GT_DetailFoamSampler, GT_WideFlowDirectivity, GT_WideFlowDirectivitySampler, GT_Wetness, GT_WetnessSampler, GT_ExtraEmissive, GT_ExtraEmissiveSampler, GT_ExtraColor, GT_ExtraColorSampler, GT_Metallic, GT_MetallicSampler, GT_SegmentLayer1, GT_SegmentLayer1Sampler, GT_WideOcclusion, GT_WideOcclusionSampler, GT_Thickness, GT_ThicknessSampler, GT_DetailColor, GT_DetailColorSampler, GT_Emissive, GT_EmissiveSampler, GT_BrokenFlowEmissive0, GT_BrokenFlowEmissive0Sampler, GT_BrokenFlowEmissive1, GT_BrokenFlowEmissive1Sampler, GT_FilmStructure, GT_FilmStructureSampler, GT_Normal, GT_NormalSampler, GT_OceanGeometry, GT_OceanGeometrySampler, GT_Occlusion, GT_OcclusionSampler, GT_WideFoamThreshold, GT_WideFoamThresholdSampler, GT_Detail, GT_DetailSampler, GT_WideFlowDirection, GT_WideFlowDirectionSampler, GT_FilmThickness, GT_FilmThicknessSampler, GT_Foam, GT_FoamSampler, GT_GradientRoughness, GT_GradientRoughnessSampler, GT_IrisColor, GT_IrisColorSampler, GT_GazeNormal, GT_GazeNormalSampler, GT_Distribution, GT_DistributionSampler, GT_DetailOcclusion, GT_DetailOcclusionSampler, GT_IrisOcclusion, GT_IrisOcclusionSampler, GT_DetailCoverage, GT_DetailCoverageSampler, GT_MateriaContext, GT_MateriaContextSampler, GT_LayeredColor, GT_LayeredColorSampler, GT_Muddiness, GT_MuddinessSampler, GT_TransparencyCoefficient, GT_TransparencyCoefficientSampler, GT_IrisNormal, GT_IrisNormalSampler, GT_ShadingLayer, GT_ShadingLayerSampler, GT_Thinness, GT_ThinnessSampler, GT_Color, GT_ColorSampler, GT_Isotropy, GT_IsotropySampler, GT_OxygenSaturation, GT_OxygenSaturationSampler, GT_Pores, GT_PoresSampler, GT_Diffusion, GT_DiffusionSampler, GT_GradientOcclusion, GT_GradientOcclusionSampler, GT_SegmentLayer0, GT_SegmentLayer0Sampler, GT_GradientNormal, GT_GradientNormalSampler, GT_ToneGradient, GT_ToneGradientSampler, GT_Transmittance, GT_TransmittanceSampler, GT_Opacity, GT_OpacitySampler, GT_Coverage, GT_CoverageSampler, GT_IrisEmissive, GT_IrisEmissiveSampler, GT_TransmittanceCoefficient, GT_TransmittanceCoefficientSampler, GT_ScrelaNormal, GT_ScrelaNormalSampler, GT_GradientPhase, GT_GradientPhaseSampler, GT_Transparency, GT_TransparencySampler, GV_ExtraPixelCoordinateContext, GV_GenericVector0Context, GV_ExternalEmissiveContext, GV_ExtraNormalizedCoordinateContext, GV_AnimateTimeContext, GV_GenericVector1Context, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 1.00000000, 0.00000000, 1.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 1.00000000, 1.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 1.00000000, 0.00000000, 1.00000000, 1.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 1.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 1.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, RMS_Metallic, RMS_Specular, RMS_Roughness, RMS_AO, RMS_Normal, RMS_Emissive, RMS_OpacityMask, RMS_Opacity, RMS_ShadingModel, RMS_ModelParam, RMS_Reflectance, RMS_Custom, RMS_WetLayer, RMS_WetNormal, RMS_ColoredOpacity, RMS_Muddiness, RMS_TransparencyLog2, RMS_TransmittanceLog2, RMS_Thickness, RMS_PhaseG, RMS_MediumPath, RMS_Foam);
    return float4(bc, dot(RMS_Metallic, RMS_Metallic) + dot(RMS_Specular, RMS_Specular) + dot(RMS_Roughness, RMS_Roughness) + dot(RMS_AO, RMS_AO) + dot(RMS_Normal, RMS_Normal) + dot(RMS_Emissive, RMS_Emissive) + dot(RMS_OpacityMask, RMS_OpacityMask) + dot(RMS_Opacity, RMS_Opacity) + dot(RMS_ShadingModel, RMS_ShadingModel) + dot(RMS_ModelParam, RMS_ModelParam) + dot(RMS_Reflectance, RMS_Reflectance) + dot(RMS_Custom, RMS_Custom) + dot(RMS_WetLayer, RMS_WetLayer) + dot(RMS_WetNormal, RMS_WetNormal) + dot(RMS_ColoredOpacity, RMS_ColoredOpacity) + dot(RMS_Muddiness, RMS_Muddiness) + dot(RMS_TransparencyLog2, RMS_TransparencyLog2) + dot(RMS_TransmittanceLog2, RMS_TransmittanceLog2) + dot(RMS_Thickness, RMS_Thickness) + dot(RMS_PhaseG, RMS_PhaseG) + dot(RMS_MediumPath, RMS_MediumPath) + dot(RMS_Foam, RMS_Foam));
}
