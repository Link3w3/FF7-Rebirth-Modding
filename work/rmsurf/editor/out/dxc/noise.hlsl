
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
Texture2D GSTBN; SamplerState GSTBNSampler;
float4 CustomExpression2(FMaterialPixelParameters Parameters, Texture2D STBN, SamplerState STBNSampler)
{
// RM_Surface rebuilt: the dither noise. The game reads its spatiotemporal blue noise (128 x 128 x 64) at
// (pixel x & 127, pixel y & 127, (frame & 7) + the primitive's context); the engine's copy of that noise is stored as a
// 128 x 8192 image (the 64 slices stacked).
#if PIXELSHADER
uint2 p = uint2(Parameters.SvPosition.xy) & 127u;
uint z = (View_FrameNumber & 7u) & 63u;
return STBN.Load(int3(p.x, p.y + z * 128u, 0));
#else
return float4(0.5, 0.5, 0.5, 0.5);
#endif

}
float4 main(float4 pos : SV_Position) : SV_Target
{
    FMaterialPixelParameters P = (FMaterialPixelParameters)0;
    P.SvPosition = pos;
    return CustomExpression2(P, GSTBN, GSTBNSampler);
}
