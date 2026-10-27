#define MaterialFloat float
#define MaterialFloat2 float2
#define MaterialFloat3 float3
#define MaterialFloat4 float4
#define Texture2DSample(t, s, uv) t.Sample(s, uv)
struct FMaterialPixelParameters { float3x3 TangentToWorld; float3 CameraVector; float3 WorldNormal; };
Texture2D TSclera; SamplerState SSclera; Texture2D TIris; SamplerState SIris; Texture2D TGaze; SamplerState SGaze;
Texture2D TGlow; SamplerState SGlow;
MaterialFloat3 CustomExpression0(FMaterialPixelParameters Parameters, MaterialFloat2 UV,
    Texture2D Sclera, SamplerState ScleraSampler, Texture2D Iris, SamplerState IrisSampler, Texture2D Gaze, SamplerState GazeSampler,
    Texture2D IrisGlow, SamplerState IrisGlowSampler,
    MaterialFloat RefractionIndex, MaterialFloat IrisDepth, MaterialFloat IrisRimDarken, MaterialFloat LidShadow, MaterialFloat LidSoftness,
    MaterialFloat LidShadowStrength, MaterialFloat EyeShadowLift, MaterialFloat GlowIntensity, MaterialFloat HighlightIntensity,
    MaterialFloat HighlightSize, MaterialFloat HighlightX, MaterialFloat HighlightY, MaterialFloat3 GlowColor,
    MaterialFloat3 SunDirection, MaterialFloat3 SunColor, MaterialFloat3 AmbientColor, MaterialFloat4 ToonParams)
{
#include "uking_toon_eye.hlsl"
}
float4 main(float2 uv : TEXCOORD0, float3 n : NORMAL, float3 t : TANGENT, float3 b : BINORMAL, float3 v : TEXCOORD1) : SV_Target
{
    FMaterialPixelParameters P;
    P.TangentToWorld = float3x3(t, b, n); P.CameraVector = normalize(v); P.WorldNormal = n;
    float3 c = CustomExpression0(P, uv, TSclera, SSclera, TIris, SIris, TGaze, SGaze, TGlow, SGlow, 1.49, 1.0, 0.35, 0.3, 0.04, 0.35, 0.35,
                                 0.35, 1.0, 0.06, 0.9, 0.9, float3(1, 1, 1), float3(0.35, 0.45, -0.82), float3(1, 0.95, 0.85),
                                 float3(0.28, 0.32, 0.4), float4(0.4, 75, 0, 0));
    return float4(c, 1);
}
