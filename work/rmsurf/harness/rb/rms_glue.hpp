// The rebuilt RM_Surface as the checker runs it: the Custom node's inputs and outputs, the engine's pixel parameters,
// and View (only the members the material reads).
#pragma once
#include "../hlsl_cpu.hpp"
#include "rms_params.inc"

namespace rms
{
using namespace hlslcpu;
struct FMaterialPixelParameters
{
    float3x3 TangentToWorld;
    vec3 CameraVector;
    vec4 SvPosition;
    D TwoSidedSign = D(1.0);
    vec4 VertexColor;
    vec3 AbsoluteWorldPosition;
    vec3 WorldPosition_CamRelative;
};
struct FViewParams
{
    D PreExposure, OneOverPreExposure, GameTime, RealTime;
    vec3 WorldCameraOrigin, PreViewTranslation;
    Texture3D PerlinNoise3DTexture{Tex3D{cpuglsl::texid("View_PerlinNoiseVolumeTexture")}};
    SamplerState PerlinNoise3DTextureSampler;
    vec4 InvDeviceZToWorldZTransform, ViewRectMin, ViewSizeAndInvSize;
};
inline FViewParams View;
// what the code asks of whoever runs it: the game's own noise textures (the editor substitutes its own)
struct RMS_Env
{
    vec4 BlueNoise3D(ivec3 p) const { return texelFetch(Tex3D{cpuglsl::texid("View_BlueNoiseVolumeTexture")}, p, 0); }
};
#include "RMS_Lib.cpp"

#define RMS_TEX_INDEX(n) k_##n,
enum TextureIndex { RMS_TEXTURES(RMS_TEX_INDEX) k_NumTextures };
#define RMS_SW_INDEX(n) s_##n,
enum SwitchIndex { RMS_SWITCHES(RMS_SW_INDEX) s_NumSwitches };

struct In
{
    FMaterialPixelParameters P;
    vec2 UV[4];
    vec4 Noise;
    D DynamicCoverage = D(1.0);
    vec4 VertexExpression;
    vec4 EBuffer;
    vec4 LocalToWorld[3];
    Texture2D tex[k_NumTextures];
    vec4 vec[9];
    D sw[s_NumSwitches];
};
struct Out
{
    vec3 BaseColor;
    D Metallic, Specular, Roughness, AO, OpacityMask, Opacity, ShadingModel, ModelParam, Reflectance;
    vec3 Normal, Emissive, WetNormal, ColoredOpacity;
    vec4 Custom;
    vec2 WetLayer;
    // the medium of a lit translucent surface (glass, crystal, water)
    vec3 Muddiness, TransmittanceLog2;
    D TransparencyLog2, Thickness, PhaseG, MediumPath, Foam;
};
void evaluate(const In& in, Out& o);
}
