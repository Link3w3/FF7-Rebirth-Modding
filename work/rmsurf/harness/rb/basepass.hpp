// The game's base pass around RM_Surface (checker only): its pixel parameters from the vertex factory's interpolants,
// and its GBuffer (7 targets) from the material's outputs. Written from the decompiled shaders, in their order.
#pragma once
#include "rms_glue.hpp"

namespace basepass
{
using namespace rms;

// the uniform buffers by byte offset (cbuffer_layouts.json)
inline D ubo_f(const UBO& b, int off) { const vec4& v = b._m0[off / 16]; return v[(off % 16) / 4]; }
inline vec3 ubo_f3(const UBO& b, int off) { return vec3(ubo_f(b, off), ubo_f(b, off + 4), ubo_f(b, off + 8)); }
inline vec4 ubo_f4(const UBO& b, int off) { return vec4(ubo_f(b, off), ubo_f(b, off + 4), ubo_f(b, off + 8), ubo_f(b, off + 12)); }
enum
{
    V_SVPositionToTranslatedWorld = 832, V_WorldCameraOrigin = 1200, V_PreViewTranslation = 1248, V_TemporalAAJitter = 2464,
    V_PreExposure = 2628, V_OneOverPreExposure = 2632, V_GameTime = 2760, V_RealTime = 2764, V_StateFrameIndex = 2800,
    P_PixelAttribute = 440, P_DynamicCoverage = 444,
};

struct Interp
{
    vec4 TEXCOORD, TEXCOORD_1, TEXCOORD_10, TEXCOORD_11, CURRENT_CLIP_SPACE_POSITION, PREVIOUS_CLIP_SPACE_POSITION, VERTEX_EXPRESSION;
    D CONSTANT_CONTEXT;
    vec4 FragCoord;
};

// CalcMaterialParameters for the GPU-skin / local vertex factories (TEXCOORD_10 = TangentToWorld0, TEXCOORD_11 =
// TangentToWorld2 with the basis sign in w)
inline FMaterialPixelParameters pixel_parameters(const Interp& I, const UBO& View_)
{
    FMaterialPixelParameters P;
    const vec3 t0 = I.TEXCOORD_10.xyz(), t2 = I.TEXCOORD_11.xyz();
    P.TangentToWorld = float3x3(t0, cross(t2, t0) * I.TEXCOORD_11.w, t2);
    P.SvPosition = vec4(I.FragCoord.x, I.FragCoord.y, I.FragCoord.z, D(1.0) / I.FragCoord.w);   // SV_Position.w: the clip w
    const vec4 m0 = ubo_f4(View_, V_SVPositionToTranslatedWorld), m1 = ubo_f4(View_, V_SVPositionToTranslatedWorld + 16),
               m2 = ubo_f4(View_, V_SVPositionToTranslatedWorld + 32), m3 = ubo_f4(View_, V_SVPositionToTranslatedWorld + 48);
    const vec4& s = I.FragCoord;
    const vec4 hom = ((m0 * s.x + m1 * s.y) + m2 * s.z) + m3;
    const vec3 tw = vec3(hom.x / hom.w, hom.y / hom.w, hom.z / hom.w);
    P.CameraVector = normalize(-tw);
    P.WorldPosition_CamRelative = tw;
    P.AbsoluteWorldPosition = tw - ubo_f3(View_, V_PreViewTranslation);
    P.TwoSidedSign = D(1.0);
    P.VertexColor = vec4(D(1.0));
    return P;
}

inline void load_view(const UBO& View_)
{
    rms::View.PreExposure = ubo_f(View_, V_PreExposure);
    rms::View.OneOverPreExposure = ubo_f(View_, V_OneOverPreExposure);
    rms::View.GameTime = ubo_f(View_, V_GameTime);
    rms::View.RealTime = ubo_f(View_, V_RealTime);
    rms::View.WorldCameraOrigin = ubo_f3(View_, V_WorldCameraOrigin);
    rms::View.PreViewTranslation = ubo_f3(View_, V_PreViewTranslation);
    rms::View.InvDeviceZToWorldZTransform = ubo_f4(View_, 1168);
    rms::View.ViewRectMin = ubo_f4(View_, 2528);
    rms::View.ViewSizeAndInvSize = ubo_f4(View_, 2544);
}

// the spatiotemporal blue noise the base pass dithers with
inline vec4 blue_noise(const Interp& I, const UBO& View_, uint64_t texture_id)
{
    const uint fi = floatBitsToUint(ubo_f(View_, V_StateFrameIndex));
    const uint z = ((fi & 7u) + uint(roundEven(I.CONSTANT_CONTEXT))) & 63u;
    return texelFetch(Tex3D{texture_id}, ivec3((int)(uint(int(I.FragCoord.x)) & 127u), (int)(uint(int(I.FragCoord.y)) & 127u), (int)z), 0);
}

// a noise channel as the encode's signed triangular dither
inline D tri(D n)
{
    const D s = (n * D(2.0)) + D(-1.0);
    return (D(1.0) - sqrt(D(1.0) - abs(s))) * D((double)(int)((s > D(0.0) ? 1u : 0u) - (s < D(0.0) ? 1u : 0u)));
}

struct GBuffer
{
    vec4 t[7];
};

// Target1.w: a constant per shading model
inline D per_model_w(int sm)
{
    switch (sm)
    {
    case 8: return D(0.742264926433563232421875);
    case 3: case 7: return D(0.684779345989227294921875);
    case 9: return D(0.645419657230377197265625);
    default: return D(0.66666662693023681640625);
    }
}

// translucency (the forward pass): premultiplied colour and the per-channel opacity the game's "colored" blend uses
inline GBuffer encode_translucent(const UBO& View_, const Out& o)
{
    GBuffer g;
    const D pe = ubo_f(View_, V_PreExposure);
    for (int i = 0; i < 3; ++i)
        g.t[0][i] = (max(D(0.0), o.Emissive[i]) * o.Opacity) * pe;
    g.t[0].w = dot(o.ColoredOpacity, vec3(D(0.2125999927520751953125), D(0.715200006961822509765625), D(0.072200000286102294921875)));
    g.t[1] = vec4(o.ColoredOpacity, D(0.0));
    for (int t = 2; t < 7; ++t) g.t[t] = vec4(D(0.0));
    return g;
}

inline GBuffer encode(const Interp& I, const UBO& View_, const UBO& Prim, const FMaterialPixelParameters& P, const Out& o, const vec4& noise)
{
    GBuffer g;
    RMS_Lib L;
    const int sm = (int)o.ShadingModel.v;
    // the world normal (MaterialTemplate), both the normalized one and the raw transform with its 1/length
    const vec3 m = normalize(o.Normal);
    const vec3 raw = mul(m, P.TangentToWorld);
    const D rs = inversesqrt(dot(raw, raw));
    const vec3 N = vec3(rs * raw.x, rs * raw.y, rs * raw.z);
    const D d[3] = {tri(noise.x), tri(noise.y), tri(noise.z)};
    const D rough = L.FilterRoughness(o.Roughness, N);
    const D metal = saturate(o.Metallic);
    // Target0: emissive (lit models: through the specular layer)
    {
        const D pe = ubo_f(View_, V_PreExposure);
        if (sm == 1)
        {
            const D atten = L.EmissiveTransmission(N, P.CameraVector, rough, o.Metallic);
            for (int i = 0; i < 3; ++i)
                g.t[0][i] = (pe * max(D(0.0), o.Emissive[i])) * atten;
        }
        else
        {
            for (int i = 0; i < 3; ++i)
                g.t[0][i] = pe * max(D(0.0), o.Emissive[i]);
        }
        g.t[0].w = D(0.0);
    }
    // Target5: the wet layer's normal (the surface's own where there is no wetness), 8 bits, and the layer's two 4-bit flags
    const vec3 wm = normalize(o.WetNormal);
    const vec3 wraw = mul(wm, P.TangentToWorld);
    const D wrs = inversesqrt(dot(wraw, wraw));
    for (int i = 0; i < 3; ++i)
    {
        const D n01 = saturate((N[i] * D(0.5)) + D(0.5));
        g.t[1][i] = saturate(((abs((n01 * D(2.0)) + D(-1.0)) + D(-0.9980449676513671875)) < D(0.0)) ? (n01 + (d[i] * D(0.000977517105638980865478515625))) : n01);
        const D m01 = saturate(((wraw[i] * D(0.5)) * wrs) + D(0.5));
        g.t[5][i] = saturate(((abs((m01 * D(2.0)) + D(-1.0)) + D(-0.99215686321258544921875)) < D(0.0)) ? (m01 + (d[i] * D(0.0039215688593685626983642578125))) : m01);
    }
    g.t[1].w = o.ModelParam;
    {
        const uint hi = uint(roundEven(saturate(o.WetLayer.x) * D(15.0))), lo = uint(roundEven(saturate(o.WetLayer.y) * D(15.0)));
        const uint packed = uint(roundEven(saturate(D((double)((hi << 4u) | lo)) * D(0.0039215688593685626983642578125)) * D(255.0)));
        const uint h2 = uint(roundEven(saturate(D((double)((packed >> 4u) & 15u)) * D(0.066666670143604278564453125)) * D(15.0)));
        const uint l2 = uint(roundEven(saturate(D((double)(packed & 15u)) * D(0.066666670143604278564453125)) * D(15.0)));
        g.t[5].w = D((double)((h2 << 4u) | l2)) * D(0.0039215688593685626983642578125);
    }
    const uint pa = floatBitsToUint(ubo_f(Prim, P_PixelAttribute));
    g.t[2] = vec4(metal, o.Specular, rough, D((double)(((pa << 4u) & 48u) | (uint)sm)) * D(0.0039215688593685626983642578125));
    g.t[3] = vec4(saturate(o.BaseColor.x), saturate(o.BaseColor.y), saturate(o.BaseColor.z), saturate(o.AO));
    g.t[4] = o.Custom;
    // Target6: velocity
    if (I.CURRENT_CLIP_SPACE_POSITION.w != D(0.0))
    {
        const vec4 j = ubo_f4(View_, V_TemporalAAJitter);
        const D a = D(1.0) / I.CURRENT_CLIP_SPACE_POSITION.w, b = D(1.0) / I.PREVIOUS_CLIP_SPACE_POSITION.w;
        g.t[6].x = (spvNMin(spvNMax(((j.z - j.x) + (a * I.CURRENT_CLIP_SPACE_POSITION.x)) - (b * I.PREVIOUS_CLIP_SPACE_POSITION.x), D(-2.0)), D(2.0)) * D(0.249988555908203125)) + D(0.50000762939453125);
        g.t[6].y = (spvNMin(spvNMax(((j.w - j.y) + (a * I.CURRENT_CLIP_SPACE_POSITION.y)) - (b * I.PREVIOUS_CLIP_SPACE_POSITION.y), D(-2.0)), D(2.0)) * D(0.249988555908203125)) + D(0.50000762939453125);
    }
    else
    {
        g.t[6].x = D(0.0);
        g.t[6].y = D(0.0);
    }
    g.t[6].z = D(0.0);
    g.t[6].w = D(0.0);
    if (sm == 0)
    {
        // unlit: emissive and velocity only
        for (int t = 1; t < 6; ++t) g.t[t] = vec4(D(0.0));
    }
    return g;
}
}
