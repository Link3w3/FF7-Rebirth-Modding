#define MaterialFloat float
#define MaterialFloat2 float2
#define MaterialFloat3 float3
#define MaterialFloat4 float4
#define Texture2DSample(t, s, uv) t.Sample(s, uv)
struct FMaterialPixelParameters { float3x3 TangentToWorld; float3 CameraVector; float3 WorldNormal; };
Texture2D TA; SamplerState SA; Texture2D TN; SamplerState SN;
MaterialFloat3 CustomExpression0(FMaterialPixelParameters Parameters, MaterialFloat2 UV, Texture2D A0, SamplerState A0Sampler,
    Texture2D N0, SamplerState N0Sampler, MaterialFloat3 SunDirection, MaterialFloat3 SunColor, MaterialFloat3 AmbientColor, MaterialFloat4 ToonParams)
{
#include "uking_toon_lite.hlsl"
}
float4 main(float2 uv : TEXCOORD0, float3 n : NORMAL, float3 t : TANGENT, float3 b : BINORMAL) : SV_Target
{
    FMaterialPixelParameters P; P.TangentToWorld = float3x3(t, b, n); P.CameraVector = 0; P.WorldNormal = n;
    return float4(CustomExpression0(P, uv, TA, SA, TN, SN, float3(0.35, 0.45, -0.82), float3(1, 0.95, 0.85), float3(0.28, 0.32, 0.4), float4(0.4, 75, 0, 0)), 1);
}
