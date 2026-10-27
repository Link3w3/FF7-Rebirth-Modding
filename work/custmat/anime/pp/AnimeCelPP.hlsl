// AnimeCelPP
// FINAL FANTASY VII REBIRTH post-process material (after tonemapping), written for the game's FPostProcessMaterialPS slot:
// scene colour from PostProcessInput0, scene depth from SceneTexturesStruct.
cbuffer _Globals : register(b0)
{
    uint2 PostProcessOutput_ViewportMin : packoffset(c37);
    float2 PostProcessOutput_ViewportSizeInverse : packoffset(c38.z);
};
cbuffer View : register(b1)
{
    float4 View_InvDeviceZToWorldZTransform : packoffset(c73);
    float4 View_ViewRectMin : packoffset(c158);
    float4 View_ViewSizeAndInvSize : packoffset(c159);
    float4 View_BufferSizeAndInvSize : packoffset(c161);
    float View_GameTime : packoffset(c172.z);
};
Texture2D PostProcessInput_0_Texture : register(t1);
SamplerState PostProcessInput_0_Sampler : register(s1);
Texture2D<float> SceneTexturesStruct_SceneDepthTexture : register(t2);

static const float P_BandMix = 0.5;
static const float P_BandSoftness = 0.12;
static const float P_Bands = 4.0;
static const float P_ColorEdgeHigh = 0.35;
static const float P_ColorEdgeLow = 0.12;
static const float P_ColorEdgeStrength = 0.35;
static const float3 P_OutlineColor = float3(0.03, 0.025, 0.04);
static const float P_OutlineDepthThreshold = 0.06;
static const float P_OutlineFadeEnd = 9000.0;
static const float P_OutlineFadeStart = 1500.0;
static const float P_OutlineStrength = 0.9;
static const float P_OutlineThickness = 1.0;
static const float P_Saturation = 1.2;
static const float P_Vignette = 0.2;

float3 SceneColorAt(float2 Pixel)
{
    return PostProcessInput_0_Texture.SampleLevel(PostProcessInput_0_Sampler, Pixel * View_BufferSizeAndInvSize.zw, 0).rgb;
}

float SceneDepthAt(float2 Pixel)
{
    const float DeviceZ = SceneTexturesStruct_SceneDepthTexture.Load(int3(int2(Pixel), 0));
    const float Depth = DeviceZ * View_InvDeviceZToWorldZTransform[0] + View_InvDeviceZToWorldZTransform[1]
        + 1.0 / (DeviceZ * View_InvDeviceZToWorldZTransform[2] - View_InvDeviceZToWorldZTransform[3]);
    return min(abs(Depth), 1.0e7);
}

float Luma(float3 C) { return dot(C, float3(0.299, 0.587, 0.114)); }

float4 MainPS(float4 SvPosition : SV_Position) : SV_Target0
{
    const float2 ViewportUV = (SvPosition.xy - float2(PostProcessOutput_ViewportMin)) * PostProcessOutput_ViewportSizeInverse;
    const float2 Pixel = ViewportUV * View_ViewSizeAndInvSize.xy + View_ViewRectMin.xy;
    float3 Color = SceneColorAt(Pixel);

    // outlines where the depth jumps (silhouettes): this pixel is in front of a neighbour that is much farther away
    const float R = P_OutlineThickness * max(1.0, View_ViewSizeAndInvSize.y / 1080.0);
    const float Depth = SceneDepthAt(Pixel);
    const float Far = max(max(SceneDepthAt(Pixel + float2(R, 0)), SceneDepthAt(Pixel - float2(R, 0))),
                          max(SceneDepthAt(Pixel + float2(0, R)), SceneDepthAt(Pixel - float2(0, R))));
    const float Jump = (Far - Depth) / max(Depth, 1.0);
    float DepthEdge = saturate((Jump - P_OutlineDepthThreshold) / P_OutlineDepthThreshold);
    DepthEdge *= 1.0 - smoothstep(P_OutlineFadeStart, P_OutlineFadeEnd, Depth);

    // thin lines on strong brightness edges (Sobel)
    float L[9];
    [unroll] for (int y = -1; y <= 1; y++)
        [unroll] for (int x = -1; x <= 1; x++)
            L[(y + 1) * 3 + (x + 1)] = Luma(SceneColorAt(Pixel + float2(x, y) * R));
    const float Gx = (L[2] + 2.0 * L[5] + L[8]) - (L[0] + 2.0 * L[3] + L[6]);
    const float Gy = (L[6] + 2.0 * L[7] + L[8]) - (L[0] + 2.0 * L[1] + L[2]);
    float ColorEdge = smoothstep(P_ColorEdgeLow, P_ColorEdgeHigh, sqrt(Gx * Gx + Gy * Gy));
    ColorEdge *= 1.0 - smoothstep(P_OutlineFadeStart, P_OutlineFadeEnd, Depth);

    // cel bands
    const float Y = Luma(Color);
    const float X = Y * P_Bands;
    const float F = floor(X);
    const float Banded = (F + smoothstep(0.5 - P_BandSoftness, 0.5 + P_BandSoftness, X - F)) / P_Bands;
    Color = lerp(Color, Color * (Banded / max(Y, 1.0e-4)), P_BandMix);

    // colour punch
    const float Y2 = Luma(Color);
    Color = max(0.0, lerp(Y2.xxx, Color, P_Saturation));

    // lines
    const float Edge = max(DepthEdge, ColorEdge * P_ColorEdgeStrength);
    Color = lerp(Color, P_OutlineColor, saturate(Edge * P_OutlineStrength));

    // vignette
    const float2 V = ViewportUV * 2.0 - 1.0;
    Color *= 1.0 - P_Vignette * saturate(dot(V, V) * 0.5);
    return float4(Color, 1.0);
}

