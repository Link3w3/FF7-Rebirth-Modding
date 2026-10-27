// The Custom node "RMS" as a C++ function: its inputs as locals named like the node's pins, its body the translated
// rebuild/RMS_Surface.ush (rb/RMS_Surface.cpp).
#include "rms_glue.hpp"

namespace rms
{
void evaluate(const In& in, Out& o)
{
    const FMaterialPixelParameters& Parameters = in.P;
    const vec2 UV0 = in.UV[0], UV1 = in.UV[1], UV2 = in.UV[2], UV3 = in.UV[3];
    const vec4 RMS_Noise = in.Noise;
    const D RMS_DynamicCoverage = in.DynamicCoverage;
    const vec4 RMS_VertexExpression = in.VertexExpression;
    const vec4 RMS_EBuffer = in.EBuffer;
    const vec4 RMS_LocalToWorld0 = in.LocalToWorld[0], RMS_LocalToWorld1 = in.LocalToWorld[1], RMS_LocalToWorld2 = in.LocalToWorld[2];
#define RMS_TEX_LOCAL(n) const Texture2D T_##n = in.tex[k_##n]; const SamplerState T_##n##Sampler{};
    RMS_TEXTURES(RMS_TEX_LOCAL)
#define RMS_VEC_LOCAL(n, i) const vec4 V_##n = in.vec[i];
    RMS_VECTORS(RMS_VEC_LOCAL)
#define RMS_SW_LOCAL(n) const D S_##n = in.sw[s_##n];
    RMS_SWITCHES(RMS_SW_LOCAL)
    D& RMS_Metallic = o.Metallic;
    D& RMS_Specular = o.Specular;
    D& RMS_Roughness = o.Roughness;
    D& RMS_AO = o.AO;
    vec3& RMS_Normal = o.Normal;
    vec3& RMS_Emissive = o.Emissive;
    D& RMS_OpacityMask = o.OpacityMask;
    D& RMS_Opacity = o.Opacity;
    D& RMS_ShadingModel = o.ShadingModel;
    D& RMS_ModelParam = o.ModelParam;
    D& RMS_Reflectance = o.Reflectance;
    vec4& RMS_Custom = o.Custom;
    vec3& RMS_WetNormal = o.WetNormal;
    vec3& RMS_ColoredOpacity = o.ColoredOpacity;
    vec2& RMS_WetLayer = o.WetLayer;
    vec3& RMS_Muddiness = o.Muddiness;
    D& RMS_TransparencyLog2 = o.TransparencyLog2;
    vec3& RMS_TransmittanceLog2 = o.TransmittanceLog2;
    D& RMS_Thickness = o.Thickness;
    D& RMS_PhaseG = o.PhaseG;
    D& RMS_MediumPath = o.MediumPath;
    D& RMS_Foam = o.Foam;
    auto body = [&]() -> vec3 {
#include "RMS_Surface.cpp"
    };
    o.BaseColor = body();
}
}
