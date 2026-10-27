"""The checker for the rebuilt Remake masters: every permutation of a master graph (remake_graphs.py, translated by
ue_mat.py for that permutation's static switches) put through a transcription of the game's 4.18 base pass and compiled
again with Microsoft's compiler, against the game's own shader for that permutation, on the same random inputs (both
run in C++, dxbc2cpp.py). The material's uniform buffer the game's shader reads is filled from the same random parameter
values through the game's own uniform expressions.

    remake_check.py <master> [-n cases] [-v] [permutation filters...]"""
import json
import os
import re
import subprocess
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dxbc2cpp
import dxbc2hlsl
import lift_check
import remake_ue
import ue_mat
import remake_graphs

ROOT = remake_ue.ROOT
DIS = remake_ue.DIS
PINS = {'BaseColor': (3, 'float3(0.0, 0.0, 0.0)'), 'Metallic': (1, '0.0'), 'Specular': (1, '0.5'), 'Roughness': (1, '0.5'),
        'Normal': (3, 'float3(0.0, 0.0, 1.0)'), 'EmissiveColor': (3, 'float3(0.0, 0.0, 0.0)'), 'AmbientOcclusion': (1, '1.0'),
        'OpacityMask': (1, '1.0'), 'Opacity': (1, '1.0'), 'TangentOutput': (3, 'T2W2.xyz'), 'IrisMask': (1, '0.0'),
        'CameraRelativeDepth': (1, '0.0'), 'ClearCoat': (1, '0.0'), 'ClothData': (3, 'float3(0.0, 0.0, 0.0)'),
        'Selective': (1, '0.0'), 'Distribution': (1, '0.0'), 'PixelIndependentVector0': (4, 'float4(0.0, 0.0, 0.0, 0.0)'),
        'PixelContextVector0': (4, 'float4(0.0, 0.0, 0.0, 0.0)'), 'PixelContextVector1': (4, 'float4(0.0, 0.0, 0.0, 0.0)')}
# the particle values the material can read (FMaterialParticleParameters)
PARTICLE_STRUCT = ('struct FMaterialParticleParameters { float4 Color; float4 DynamicParameter; float2 SubUVCoords[2]; float SubUVLerp; '
                   'float4 TranslatedWorldPositionAndSize; };')
HELPERS = r'''
float4 ProcessMaterialAlphaTextureLookup(float4 X) { return float4(0.0, 0.0, 0.0, X.r); }
float4 ProcessMaterialGreyscaleTextureLookup(float4 X) { return float4(X.r, X.r, X.r, 1.0); }
float3 UnpackNormalMap(float4 X) { float2 XY = X.rg * 2.0 - 1.0; return float3(XY, sqrt(saturate(1.0 - dot(XY, XY)))); }
float ClampedPow(float X, float Y) { return pow(max(abs(X), 0.000001), Y); }
float2 ClampedPow(float2 X, float2 Y) { return pow(max(abs(X), float2(0.000001, 0.000001)), Y); }
float3 ClampedPow(float3 X, float3 Y) { return pow(max(abs(X), float3(0.000001, 0.000001, 0.000001)), Y); }
float4 ClampedPow(float4 X, float4 Y) { return pow(max(abs(X), float4(0.000001, 0.000001, 0.000001, 0.000001)), Y); }
''' + PARTICLE_STRUCT + r'''
struct FMaterialPixelParameters { float4 SvPosition; float3 WorldNormal; float3x3 TangentToWorld; float3 CameraVector; float UnMirrored; uint PrimitiveId;
                                  FMaterialParticleParameters Particle; };
'''

# the game's 4.18 base pass before the material: the tangent frame, the camera vector, the blue noise
BASE_PASS_PROLOGUE = r'''
    float3 T2W1 = cross(T2W2.xyz, T2W0) * T2W2.w;
    int Ctx = (int)floor(VertexContext + 0.5);
    float4 HP = SvPosition.y * View[37] + (SvPosition.x * View[36] + (SvPosition.z * View[38])) + View[39];
    float3 TWP = HP.xyz / HP.w;
    float3 V = normalize(-TWP);
    uint NZ = (uint)Ctx + (asuint(View[139].z) << 3);
    float4 NoiseW = Noise3D.Load(int4(int(SvPosition.x) & 63, int(SvPosition.y) & 63, NZ & 63u, 0));
    float3 Noise = NoiseW.xyz;
    Parameters.TangentToWorld = float3x3(T2W0, T2W1, T2W2.xyz);
    Parameters.CameraVector = V;
    Parameters.UnMirrored = T2W2.w;
'''

# the game's 4.18 base pass after the material (EndMaterial_Standard's Default Lit one), transcribed from its shader
BASE_PASS_DEFAULT_LIT = r'''
    float3 MN = P_Normal * View[134].w + View[134].xyz;
    MN = normalize(MN);
    float3 N = normalize(MN.x * T2W0 + MN.y * T2W1 + MN.z * T2W2.xyz);
    float3 BaseColor = saturate(P_BaseColor);
    float Metallic = saturate(P_Metallic);
    float Specular = saturate(P_Specular);
    float Rough = saturate(P_Roughness) * View[135].y + View[135].x;
    float AO = saturate(P_AmbientOcclusion);
    float3 Emissive = max(P_EmissiveColor + SelectionColor, float3(0.0, 0.0, 0.0));
    float Threshold = (0.0 < Prim[11].y) ? PLB[5].x : 1.0;
    uint Mask = ((Noise.x * 0.99609375 + 0.001953125) < Threshold) ? 32u : 0u;
    uint Flags = asuint(Prim[11].x);
    Mask += ((Flags & 2u) != 0u ? 64u : 0u) + ((Flags & 4u) != 0u ? 128u : 0u);
    float3 DX = ddx_coarse(N);
    float3 DY = ddy_coarse(N);
    float K = min((dot(DX, DX) + dot(DY, DY)) * 0.5, 0.18);
    float FRough = sqrt(min(Rough * Rough + K, 1.0));
#if STATIC_SWITCH_LITE_DECAL
    float2 NzC = float2(NoiseW.w, NoiseW.x) * 0.99609375 + 0.001953125;
    if (!((NzC.y < P_OpacityMask) && (NzC.x < Globals[2].x))) discard;
#endif
    float3 VN = P_TangentOutput * 0.5 + 0.5;
    float3 Diffuse = BaseColor * (1.0 - Metallic);
    float F0s = Specular * Specular * 0.16;
    float3 SpecColor = (BaseColor - F0s) * Metallic + F0s;
    Diffuse = Diffuse * View[132].w + View[132].xyz;
    SpecColor = SpecColor * View[133].w + View[133].xyz;
    float3 Debug = SpecColor * 0.45 + Diffuse;
    float NoV = max(abs(dot(N, V)), 0.00001);
    float F0 = dot(SpecColor, float3(0.33333334, 0.33333334, 0.33333334));
    float4 R = FRough * float4(-1.0, -0.0275, -0.572, 0.022) + float4(1.0, 0.0425, 1.04, -0.04);
    float A004 = min(R.x * R.x, exp2(NoV * -9.28)) * R.x + R.y;
    float2 AB = A004 * float2(-1.04, 1.04) + R.zw;
    F0 = dot(float3(F0, F0, F0), float3(0.33333334, 0.33333334, 0.33333334));
    float Env = saturate(F0 * AB.x + AB.y * saturate(F0 * 50.0));
    float Att = (1.0 - Env) * (1.0 - Env);
    Att = Att - Metallic * Att;
    float4 E = float4(Att * Emissive, 0.0);
    if (0.0 < View[140].z) E = float4(Debug, dot(Debug, float3(0.2126, 0.7152, 0.0722)));
    if (0.0 < View[136].x)
    {
        float3 WP = TWP - View[62].xyz;
        float3 D = WP - Prim[8].xyz;
        float3 Ext = Prim[9].xyz + 1.0;
        bool Outside = any(Ext < abs(D));
        float H = frac(dot(WP, float3(0.57735026, 0.57735026, 0.57735026)) * 0.002);
        float3 C = (0.5 < H) ? float3(0.0, 1.0, 1.0) : float3(1.0, 1.0, 0.0);
        if (Outside) E = float4(C, dot(C, float3(0.2126, 0.7152, 0.0722)));
    }
    o0 = E * View[128].x;
    float3 EN = N * 0.5 + 0.5;
    o1.w = (Flags & 1u) != 0u ? 0.33333334 : 0.0;
    o2.w = float(Mask + 1u) * 0.003921569;
    float4 Tri = float4(Noise.xyz, Noise.x) * 2.0 - 1.0;
    float4 Sgn = float4(int4(0.0 < Tri) - int4(Tri < 0.0));
    Tri = (1.0 - sqrt(1.0 - abs(Tri))) * Sgn;
    bool3 In1 = (abs(EN * 2.0 - 1.0) - 0.99804688) < 0.0;
    o1.xyz = saturate(In1 ? Tri.xyz * 0.0009775171 + EN : EN);
    bool3 In4 = (abs(VN * 2.0 - 1.0) - 0.99215686) < 0.0;
    o4.x = saturate(In4.x ? Tri.w * 0.003921569 + VN.x : VN.x);
    o4.yz = saturate(In4.yz ? Tri.yz * 0.003921569 + VN.yz : VN.yz);
    o2.xyz = float3(Metallic, Specular, FRough);
    o3 = float4(BaseColor, AO);
    o4.w = 0.0;
    o5 = float4(0.0, 0.0, 0.0, 0.0);
'''

# the game's 4.18 base pass for its Preintegrated Skin model (EndMaterial_Skin's): no specular override, no vertex normal,
# the shading model id 3 with the game's flag 16, the subsurface data zero with the opacity
BASE_PASS_SKIN = r'''
    float3 MN = P_Normal * View[134].w + View[134].xyz;
    MN = normalize(MN);
    float3 N = normalize(MN.x * T2W0 + MN.y * T2W1 + MN.z * T2W2.xyz);
    float3 BaseColor = saturate(P_BaseColor);
    float Metallic = saturate(P_Metallic);
    float Specular = saturate(P_Specular);
    float Rough = saturate(P_Roughness) * View[135].y + View[135].x;
    float AO = saturate(P_AmbientOcclusion);
    float Opacity = saturate(P_Opacity);
    float3 Emissive = max(P_EmissiveColor + SelectionColor, float3(0.0, 0.0, 0.0));
    float Threshold = (0.0 < Prim[11].y) ? PLB[5].x : 1.0;
    uint Mask = ((Noise.x * 0.99609375 + 0.001953125) < Threshold) ? 32u : 0u;
    uint Flags = asuint(Prim[11].x);
    Mask += ((Flags & 2u) != 0u ? 64u : 0u) + ((Flags & 4u) != 0u ? 128u : 0u);
    float3 DX = ddx_coarse(N);
    float3 DY = ddy_coarse(N);
    float K = min((dot(DX, DX) + dot(DY, DY)) * 0.5, 0.18);
    float FRough = sqrt(min(Rough * Rough + K, 1.0));
#if STATIC_SWITCH_LITE_DECAL
    float2 NzC = float2(NoiseW.w, NoiseW.x) * 0.99609375 + 0.001953125;
    if (!((NzC.y < P_OpacityMask) && (NzC.x < Globals[2].x))) discard;
#endif
    float3 Diffuse = BaseColor * (1.0 - Metallic);
    float F0s = Specular * Specular * 0.16;
    float3 SpecColor = (BaseColor - F0s) * Metallic + F0s;
    Diffuse = Diffuse * View[132].w + View[132].xyz;
    float3 Debug = SpecColor * 0.45 + Diffuse;
    float NoV = max(abs(dot(N, V)), 0.00001);
    float F0 = dot(SpecColor, float3(0.33333334, 0.33333334, 0.33333334));
    float4 R = FRough * float4(-1.0, -0.0275, -0.572, 0.022) + float4(1.0, 0.0425, 1.04, -0.04);
    float A004 = min(R.x * R.x, exp2(NoV * -9.28)) * R.x + R.y;
    float2 AB = A004 * float2(-1.04, 1.04) + R.zw;
    F0 = dot(float3(F0, F0, F0), float3(0.33333334, 0.33333334, 0.33333334));
    float Env = saturate(F0 * AB.x + AB.y * saturate(F0 * 50.0));
    float Att = (1.0 - Env) * (1.0 - Env);
    Att = Att - Metallic * Att;
    float4 E = float4(Att * Emissive, 0.0);
    if (0.0 < View[140].z) E = float4(Debug, dot(Debug, float3(0.2126, 0.7152, 0.0722)));
    if (0.0 < View[136].x)
    {
        float3 WP = TWP - View[62].xyz;
        float3 D = WP - Prim[8].xyz;
        float3 Ext = Prim[9].xyz + 1.0;
        bool Outside = any(Ext < abs(D));
        float H = frac(dot(WP, float3(0.57735026, 0.57735026, 0.57735026)) * 0.002);
        float3 C = (0.5 < H) ? float3(0.0, 1.0, 1.0) : float3(1.0, 1.0, 0.0);
        if (Outside) E = float4(C, dot(C, float3(0.2126, 0.7152, 0.0722)));
    }
    o0 = E * View[128].x;
    float3 EN = N * 0.5 + 0.5;
    o1.w = (Flags & 1u) != 0u ? 0.33333334 : 0.0;
    o2.w = float(Mask + 19u) * 0.003921569;
    float4 Tri = float4(Noise.xyz, Noise.x) * 2.0 - 1.0;
    float4 Sgn = float4(int4(0.0 < Tri) - int4(Tri < 0.0));
    Tri = (1.0 - sqrt(1.0 - abs(Tri))) * Sgn;
    bool3 In1 = (abs(EN * 2.0 - 1.0) - 0.99804688) < 0.0;
    o1.xyz = saturate(In1 ? Tri.xyz * 0.0009775171 + EN : EN);
    o2.xyz = float3(Metallic, Specular, FRough);
    o3 = float4(BaseColor, AO);
    o4 = float4(0.0, 0.0, 0.0, Opacity);
    o5 = float4(0.0, 0.0, 0.0, 0.0);
'''
# the game's 4.18 base pass for its hair model (EndMaterial_Hair's, with TransformedNormal: the material's normal is in world
# space): no specular override, the bent normal (the material's) in the vertex normal's place, the shading model id 7
BASE_PASS_HAIR = r'''
    float3 MN = P_Normal * View[134].w + View[134].xyz;
    float3 N = normalize(MN);
    float3 BaseColor = saturate(P_BaseColor);
    float Metallic = saturate(P_Metallic);
    float Specular = saturate(P_Specular);
    float Rough = saturate(P_Roughness) * View[135].y + View[135].x;
    float AO = saturate(P_AmbientOcclusion);
    float3 Emissive = max(P_EmissiveColor + SelectionColor, float3(0.0, 0.0, 0.0));
    float Threshold = (0.0 < Prim[11].y) ? PLB[5].x : 1.0;
    uint Mask = ((Noise.x * 0.99609375 + 0.001953125) < Threshold) ? 32u : 0u;
    uint Flags = asuint(Prim[11].x);
    Mask += ((Flags & 2u) != 0u ? 64u : 0u) + ((Flags & 4u) != 0u ? 128u : 0u);
    float3 DX = ddx_coarse(N);
    float3 DY = ddy_coarse(N);
    float K = min((dot(DX, DX) + dot(DY, DY)) * 0.5, 0.18);
    float FRough = sqrt(min(Rough * Rough + K, 1.0));
    float3 VN = P_TangentOutput * 0.5 + 0.5;
    float3 Diffuse = BaseColor * (1.0 - Metallic);
    float F0s = Specular * Specular * 0.16;
    float3 SpecColor = (BaseColor - F0s) * Metallic + F0s;
    Diffuse = Diffuse * View[132].w + View[132].xyz;
    float3 Debug = SpecColor * 0.45 + Diffuse;
    float NoV = max(abs(dot(N, V)), 0.00001);
    float F0 = dot(SpecColor, float3(0.33333334, 0.33333334, 0.33333334));
    float4 R = FRough * float4(-1.0, -0.0275, -0.572, 0.022) + float4(1.0, 0.0425, 1.04, -0.04);
    float A004 = min(R.x * R.x, exp2(NoV * -9.28)) * R.x + R.y;
    float2 AB = A004 * float2(-1.04, 1.04) + R.zw;
    F0 = dot(float3(F0, F0, F0), float3(0.33333334, 0.33333334, 0.33333334));
    float Env = saturate(F0 * AB.x + AB.y * saturate(F0 * 50.0));
    float Att = (1.0 - Env) * (1.0 - Env);
    Att = Att - Metallic * Att;
    float4 E = float4(Att * Emissive, 0.0);
    if (0.0 < View[140].z) E = float4(Debug, dot(Debug, float3(0.2126, 0.7152, 0.0722)));
    if (0.0 < View[136].x)
    {
        float3 WP = TWP - View[62].xyz;
        float3 D = WP - Prim[8].xyz;
        float3 Ext = Prim[9].xyz + 1.0;
        bool Outside = any(Ext < abs(D));
        float H = frac(dot(WP, float3(0.57735026, 0.57735026, 0.57735026)) * 0.002);
        float3 C = (0.5 < H) ? float3(0.0, 1.0, 1.0) : float3(1.0, 1.0, 0.0);
        if (Outside) E = float4(C, dot(C, float3(0.2126, 0.7152, 0.0722)));
    }
    o0 = E * View[128].x;
    float3 EN = N * 0.5 + 0.5;
    o1.w = (Flags & 1u) != 0u ? 0.33333334 : 0.0;
    o2.w = float(Mask + 7u) * 0.003921569;
    float4 Tri = float4(Noise.xyz, Noise.x) * 2.0 - 1.0;
    float4 Sgn = float4(int4(0.0 < Tri) - int4(Tri < 0.0));
    Tri = (1.0 - sqrt(1.0 - abs(Tri))) * Sgn;
    bool3 In1 = (abs(EN * 2.0 - 1.0) - 0.99804688) < 0.0;
    o1.xyz = saturate(In1 ? Tri.xyz * 0.0009775171 + EN : EN);
    bool3 In4 = (abs(VN * 2.0 - 1.0) - 0.99215686) < 0.0;
    o4.x = saturate(In4.x ? Tri.w * 0.003921569 + VN.x : VN.x);
    o4.yz = saturate(In4.yz ? Tri.yz * 0.003921569 + VN.yz : VN.yz);
    o2.xyz = float3(Metallic, Specular, FRough);
    o3 = float4(BaseColor, AO);
    o4.w = 0.0;
    o5 = float4(0.0, 0.0, 0.0, 0.0);
'''
# the game's 4.18 base pass for its eye model (EndMaterial_Eye's, with TransformedNormal): as the hair's, the tangent
# output (the iris normal) in GBuffer D with one minus the iris mask, the shading model id 9 with the game's flag 16
BASE_PASS_EYE = r'''
    float3 MN = P_Normal * View[134].w + View[134].xyz;
    float3 N = normalize(MN);
    float3 BaseColor = saturate(P_BaseColor);
    float Metallic = saturate(P_Metallic);
    float Specular = saturate(P_Specular);
    float Rough = saturate(P_Roughness) * View[135].y + View[135].x;
    float AO = saturate(P_AmbientOcclusion);
    float3 Emissive = max(P_EmissiveColor + SelectionColor, float3(0.0, 0.0, 0.0));
    float Threshold = (0.0 < Prim[11].y) ? PLB[5].x : 1.0;
    uint Mask = ((Noise.x * 0.99609375 + 0.001953125) < Threshold) ? 32u : 0u;
    uint Flags = asuint(Prim[11].x);
    Mask += ((Flags & 2u) != 0u ? 64u : 0u) + ((Flags & 4u) != 0u ? 128u : 0u);
    float3 DX = ddx_coarse(N);
    float3 DY = ddy_coarse(N);
    float K = min((dot(DX, DX) + dot(DY, DY)) * 0.5, 0.18);
    float FRough = sqrt(min(Rough * Rough + K, 1.0));
    float3 VN = P_TangentOutput * 0.5 + 0.5;
    float3 Diffuse = BaseColor * (1.0 - Metallic);
    float F0s = Specular * Specular * 0.16;
    float3 SpecColor = (BaseColor - F0s) * Metallic + F0s;
    Diffuse = Diffuse * View[132].w + View[132].xyz;
    float3 Debug = SpecColor * 0.45 + Diffuse;
    float NoV = max(abs(dot(N, V)), 0.00001);
    float F0 = dot(SpecColor, float3(0.33333334, 0.33333334, 0.33333334));
    float4 R = FRough * float4(-1.0, -0.0275, -0.572, 0.022) + float4(1.0, 0.0425, 1.04, -0.04);
    float A004 = min(R.x * R.x, exp2(NoV * -9.28)) * R.x + R.y;
    float2 AB = A004 * float2(-1.04, 1.04) + R.zw;
    F0 = dot(float3(F0, F0, F0), float3(0.33333334, 0.33333334, 0.33333334));
    float Env = saturate(F0 * AB.x + AB.y * saturate(F0 * 50.0));
    float Att = (1.0 - Env) * (1.0 - Env);
    Att = Att - Metallic * Att;
    float4 E = float4(Att * Emissive, 0.0);
    if (0.0 < View[140].z) E = float4(Debug, dot(Debug, float3(0.2126, 0.7152, 0.0722)));
    if (0.0 < View[136].x)
    {
        float3 WP = TWP - View[62].xyz;
        float3 D = WP - Prim[8].xyz;
        float3 Ext = Prim[9].xyz + 1.0;
        bool Outside = any(Ext < abs(D));
        float H = frac(dot(WP, float3(0.57735026, 0.57735026, 0.57735026)) * 0.002);
        float3 C = (0.5 < H) ? float3(0.0, 1.0, 1.0) : float3(1.0, 1.0, 0.0);
        if (Outside) E = float4(C, dot(C, float3(0.2126, 0.7152, 0.0722)));
    }
    o0 = E * View[128].x;
    float3 EN = N * 0.5 + 0.5;
    o1.w = (Flags & 1u) != 0u ? 0.33333334 : 0.0;
    o2.w = float(Mask + 25u) * 0.003921569;
    float4 Tri = float4(Noise.xyz, Noise.x) * 2.0 - 1.0;
    float4 Sgn = float4(int4(0.0 < Tri) - int4(Tri < 0.0));
    Tri = (1.0 - sqrt(1.0 - abs(Tri))) * Sgn;
    bool3 In1 = (abs(EN * 2.0 - 1.0) - 0.99804688) < 0.0;
    o1.xyz = saturate(In1 ? Tri.xyz * 0.0009775171 + EN : EN);
    bool3 In4 = (abs(VN * 2.0 - 1.0) - 0.99215686) < 0.0;
    o4.x = saturate(In4.x ? Tri.w * 0.003921569 + VN.x : VN.x);
    o4.yz = saturate(In4.yz ? Tri.yz * 0.003921569 + VN.yz : VN.yz);
    o2.xyz = float3(Metallic, Specular, FRough);
    o3 = float4(BaseColor, AO);
    o4.w = 1.0 - saturate(P_IrisMask);
    o5 = float4(0.0, 0.0, 0.0, 0.0);
'''
# the game's 4.18 base pass for its cloth model (EndMaterial_Fabric's): as Default Lit's without the specular override, the
# shading model id 8 with the game's flag 16, GBuffer D the cloth data (the fur, the gloss and the fluff, dithered as the
# vertex normal is) and the clear coat (the distribution); with Selective each pixel cloth or Default Lit by the noise
BASE_PASS_CLOTH = r'''
    float3 MN = P_Normal * View[134].w + View[134].xyz;
    MN = normalize(MN);
    float3 N = normalize(MN.x * T2W0 + MN.y * T2W1 + MN.z * T2W2.xyz);
    float3 BaseColor = saturate(P_BaseColor);
    float Metallic = saturate(P_Metallic);
    float Specular = saturate(P_Specular);
    float Rough = saturate(P_Roughness) * View[135].y + View[135].x;
    float AO = saturate(P_AmbientOcclusion);
    float3 Emissive = max(P_EmissiveColor + SelectionColor, float3(0.0, 0.0, 0.0));
    float Threshold = (0.0 < Prim[11].y) ? PLB[5].x : 1.0;
    float Dither = Noise.x * 0.99609375 + 0.001953125;
    uint Mask = (Dither < Threshold) ? 32u : 0u;
    uint Flags = asuint(Prim[11].x);
    Mask += ((Flags & 2u) != 0u ? 64u : 0u) + ((Flags & 4u) != 0u ? 128u : 0u);
    float3 DX = ddx_coarse(N);
    float3 DY = ddy_coarse(N);
    float K = min((dot(DX, DX) + dot(DY, DY)) * 0.5, 0.18);
    float FRough = sqrt(min(Rough * Rough + K, 1.0));
    float3 VN = P_ClothData;
    float3 Diffuse = BaseColor * (1.0 - Metallic);
    float F0s = Specular * Specular * 0.16;
    float3 SpecColor = (BaseColor - F0s) * Metallic + F0s;
    Diffuse = Diffuse * View[132].w + View[132].xyz;
    float3 Debug = SpecColor * 0.45 + Diffuse;
    float NoV = max(abs(dot(N, V)), 0.00001);
    float F0 = dot(SpecColor, float3(0.33333334, 0.33333334, 0.33333334));
    float4 R = FRough * float4(-1.0, -0.0275, -0.572, 0.022) + float4(1.0, 0.0425, 1.04, -0.04);
    float A004 = min(R.x * R.x, exp2(NoV * -9.28)) * R.x + R.y;
    float2 AB = A004 * float2(-1.04, 1.04) + R.zw;
    F0 = dot(float3(F0, F0, F0), float3(0.33333334, 0.33333334, 0.33333334));
    float Env = saturate(F0 * AB.x + AB.y * saturate(F0 * 50.0));
    float Att = (1.0 - Env) * (1.0 - Env);
    Att = Att - Metallic * Att;
    float4 E = float4(Att * Emissive, 0.0);
    if (0.0 < View[140].z) E = float4(Debug, dot(Debug, float3(0.2126, 0.7152, 0.0722)));
    if (0.0 < View[136].x)
    {
        float3 WP = TWP - View[62].xyz;
        float3 D = WP - Prim[8].xyz;
        float3 Ext = Prim[9].xyz + 1.0;
        bool Outside = any(Ext < abs(D));
        float H = frac(dot(WP, float3(0.57735026, 0.57735026, 0.57735026)) * 0.002);
        float3 C = (0.5 < H) ? float3(0.0, 1.0, 1.0) : float3(1.0, 1.0, 0.0);
        if (Outside) E = float4(C, dot(C, float3(0.2126, 0.7152, 0.0722)));
    }
    o0 = E * View[128].x;
    float3 EN = N * 0.5 + 0.5;
    o1.w = (Flags & 1u) != 0u ? 0.33333334 : 0.0;
#if STATIC_SWITCH_SELECTIVE
    o2.w = float(Mask + 16u + ((Dither < P_Selective) ? 8u : 1u)) * 0.003921569;
#else
    o2.w = float(Mask + 24u) * 0.003921569;
#endif
    float4 Tri = float4(Noise.xyz, Noise.x) * 2.0 - 1.0;
    float4 Sgn = float4(int4(0.0 < Tri) - int4(Tri < 0.0));
    Tri = (1.0 - sqrt(1.0 - abs(Tri))) * Sgn;
    bool3 In1 = (abs(EN * 2.0 - 1.0) - 0.99804688) < 0.0;
    o1.xyz = saturate(In1 ? Tri.xyz * 0.0009775171 + EN : EN);
    bool3 In4 = (abs(VN * 2.0 - 1.0) - 0.99215686) < 0.0;
    o4.x = saturate(In4.x ? Tri.w * 0.003921569 + VN.x : VN.x);
    o4.yz = saturate(In4.yz ? Tri.yz * 0.003921569 + VN.yz : VN.yz);
    o2.xyz = float3(Metallic, Specular, FRough);
    o3 = float4(BaseColor, AO);
    o4.w = P_ClearCoat;
    o5 = float4(0.0, 0.0, 0.0, 0.0);
'''
# the game's 4.18 base pass for its subsurface profile model (EndMaterial_Subsurface's): as Default Lit's without the
# specular override, the shading model id 5 with the game's flag 16, the distribution in GBuffer D's w
BASE_PASS_SUBSURFACE = r'''
    float3 MN = P_Normal * View[134].w + View[134].xyz;
    MN = normalize(MN);
    float3 N = normalize(MN.x * T2W0 + MN.y * T2W1 + MN.z * T2W2.xyz);
    float3 BaseColor = saturate(P_BaseColor);
    float Metallic = saturate(P_Metallic);
    float Specular = saturate(P_Specular);
    float Rough = saturate(P_Roughness) * View[135].y + View[135].x;
    float AO = saturate(P_AmbientOcclusion);
    float3 Emissive = max(P_EmissiveColor + SelectionColor, float3(0.0, 0.0, 0.0));
    float Threshold = (0.0 < Prim[11].y) ? PLB[5].x : 1.0;
    uint Mask = ((Noise.x * 0.99609375 + 0.001953125) < Threshold) ? 32u : 0u;
    uint Flags = asuint(Prim[11].x);
    Mask += ((Flags & 2u) != 0u ? 64u : 0u) + ((Flags & 4u) != 0u ? 128u : 0u);
    float3 DX = ddx_coarse(N);
    float3 DY = ddy_coarse(N);
    float K = min((dot(DX, DX) + dot(DY, DY)) * 0.5, 0.18);
    float FRough = sqrt(min(Rough * Rough + K, 1.0));
    float3 VN = P_TangentOutput * 0.5 + 0.5;
    float3 Diffuse = BaseColor * (1.0 - Metallic);
    float F0s = Specular * Specular * 0.16;
    float3 SpecColor = (BaseColor - F0s) * Metallic + F0s;
    Diffuse = Diffuse * View[132].w + View[132].xyz;
    float3 Debug = SpecColor * 0.45 + Diffuse;
    float NoV = max(abs(dot(N, V)), 0.00001);
    float F0 = dot(SpecColor, float3(0.33333334, 0.33333334, 0.33333334));
    float4 R = FRough * float4(-1.0, -0.0275, -0.572, 0.022) + float4(1.0, 0.0425, 1.04, -0.04);
    float A004 = min(R.x * R.x, exp2(NoV * -9.28)) * R.x + R.y;
    float2 AB = A004 * float2(-1.04, 1.04) + R.zw;
    F0 = dot(float3(F0, F0, F0), float3(0.33333334, 0.33333334, 0.33333334));
    float Env = saturate(F0 * AB.x + AB.y * saturate(F0 * 50.0));
    float Att = (1.0 - Env) * (1.0 - Env);
    Att = Att - Metallic * Att;
    float4 E = float4(Att * Emissive, 0.0);
    if (0.0 < View[140].z) E = float4(Debug, dot(Debug, float3(0.2126, 0.7152, 0.0722)));
    if (0.0 < View[136].x)
    {
        float3 WP = TWP - View[62].xyz;
        float3 D = WP - Prim[8].xyz;
        float3 Ext = Prim[9].xyz + 1.0;
        bool Outside = any(Ext < abs(D));
        float H = frac(dot(WP, float3(0.57735026, 0.57735026, 0.57735026)) * 0.002);
        float3 C = (0.5 < H) ? float3(0.0, 1.0, 1.0) : float3(1.0, 1.0, 0.0);
        if (Outside) E = float4(C, dot(C, float3(0.2126, 0.7152, 0.0722)));
    }
    o0 = E * View[128].x;
    float3 EN = N * 0.5 + 0.5;
    o1.w = (Flags & 1u) != 0u ? 0.33333334 : 0.0;
    o2.w = float(Mask + 21u) * 0.003921569;
    float4 Tri = float4(Noise.xyz, Noise.x) * 2.0 - 1.0;
    float4 Sgn = float4(int4(0.0 < Tri) - int4(Tri < 0.0));
    Tri = (1.0 - sqrt(1.0 - abs(Tri))) * Sgn;
    bool3 In1 = (abs(EN * 2.0 - 1.0) - 0.99804688) < 0.0;
    o1.xyz = saturate(In1 ? Tri.xyz * 0.0009775171 + EN : EN);
    bool3 In4 = (abs(VN * 2.0 - 1.0) - 0.99215686) < 0.0;
    o4.x = saturate(In4.x ? Tri.w * 0.003921569 + VN.x : VN.x);
    o4.yz = saturate(In4.yz ? Tri.yz * 0.003921569 + VN.yz : VN.yz);
    o2.xyz = float3(Metallic, Specular, FRough);
    o3 = float4(BaseColor, AO);
    o4.w = P_Distribution;
    o5 = float4(0.0, 0.0, 0.0, 0.0);
'''
# the game's 4.18 translucent base pass (alpha composite) for Unlit (EndMaterial_Hologram's, EndMaterial_Particle's): the
# emissive and the fog's inscattering by the opacity (the colour composited over what is behind): the height fog (the
# engine's line integral; its inscattering the fog's cubemap toward the camera and the directional inscattering, a
# Cornette-Shanks phase, g = -0.6) and the volumetric fog, per pixel or from the vertex shader; with the game's particle
# visibility (PARTICLE_VISIBILITY): the particle's visibility (PixelContextVector1.x) dims the colour by its 8th power
# and the opacity by itself, and its coverage (the opacity mask) the whole
BASE_PASS_TRANSLUCENT_UNLIT = r"""
#if BASE_PASS_DRAWS_NOTHING
    float3 Color = float3(0.0, 0.0, 0.0);
#else
    float3 Color = max(P_EmissiveColor + SelectionColor, float3(0.0, 0.0, 0.0));
#endif
#if MASKED_BASE_PASS
    float2 NzC = float2(NoiseW.w, NoiseW.x) * 0.99609375 + 0.001953125;
    if (!((NzC.y < P_OpacityMask) && (NzC.x < Globals[2].x))) discard;
#endif
    float Fog = 1.0;
    float3 FogColor = float3(0.0, 0.0, 0.0);
#if TRANSLUCENT_FOG_PER_PIXEL
    {
    float FogLen = sqrt(dot(TWP, TWP));
    float Ex = max(FogLen * View[187].w / dot(TWP, View[52].xyz), 0.0);
    float FogInv = 1.0 / FogLen;
    float3 FogDir = -TWP * FogInv;
    float CosT = dot(Globals[FOG_GLOBALS + 5].xyz, FogDir);
    float HG = -CosT * -1.2 + 1.36;
    float Phase = (CosT * CosT + 1.0) * (HG < 0.000001 ? 0.0 : pow(abs(HG), -1.5)) * 0.03237049;
    float3 Inscat = FogCube.SampleLevel(FogCubeSampler, FogDir, 0.0).xyz + Globals[FOG_GLOBALS + 6].xyz * Phase;
    Ex = max(Ex, Globals[FOG_GLOBALS].w);
    bool Excl = 0.0 < Ex;
    float ExT = FogInv * Ex;
    float ExZ = ExT * TWP.z + View[59].z;
    float ExToZ = -ExT * TWP.z + TWP.z;
    float ExLen = FogLen * (-Ex * FogInv + 1.0);
    float Expo = max((ExZ - Globals[FOG_GLOBALS + 2].y) * Globals[FOG_GLOBALS].y, -127.0);
    float RayOrigin = Excl ? exp2(-Expo) * Globals[FOG_GLOBALS + 2].x : Globals[FOG_GLOBALS].x;
    float RayLen = Excl ? ExLen : FogLen;
    float RayZ = Excl ? ExToZ : TWP.z;
    float Fall = max(RayZ * Globals[FOG_GLOBALS].y, -127.0);
    float Shared = (0.01 < abs(Fall)) ? (1.0 - exp2(-Fall)) / Fall : (0.6931472 - 0.2402265 * Fall);
    Fog = min(exp2(Shared * (RayOrigin * -RayLen)), 1.0);
    FogColor = Inscat * Globals[FOG_GLOBALS + 1].xyz * (1.0 - Fog);
    if (0.0 < Globals[FOG_GLOBALS + 7].y)
    {
        float3 FP = (TWP + View[60].xyz) - View[62].xyz;
        float3 FC = FP.y * View[5].xyw + FP.x * View[4].xyw + FP.z * View[6].xyw + View[7].xyw;
        float2 FUV = FC.xy * (1.0 / FC.z) * float2(0.5, -0.5) + 0.5;
        float FZ = log2(FC.z * View[187].x + View[187].y) * View[187].z;
        float2 FG = min(max(FUV * View[183].xy, 0.5), View[183].xy - 0.5);
        float4 VF = VolumetricFog.SampleLevel(VolumetricFogSampler, float3(FG * View[186].xy, FZ * View[185].z), 0.0);
        FogColor = FogColor * VF.w + VF.xyz * View[128].y;
        Fog *= VF.w;
    }
    FogColor *= Globals[FOG_GLOBALS + 2].w;
    Fog = Globals[FOG_GLOBALS + 2].w * (Fog - 1.0) + 1.0;
    }
#elif TRANSLUCENT_VERTEX_FOG
    Fog = VertexFog.w;
    FogColor = VertexFog.xyz;
#endif
    float Opacity = saturate(P_Opacity);
#if PARTICLE_VISIBILITY
    float Vis = P_PixelContextVector1.x;
    float Vis8 = Vis * Vis;
    Vis8 *= Vis8;
    Vis8 *= Vis8;
    float4 E = float4((Color * Vis8) * Fog + (FogColor * Opacity) * Vis, Opacity * Vis) * saturate(P_OpacityMask);
#else
    float4 E = float4(Color * Fog + FogColor * Opacity, Opacity);
#endif
    if (0.0 < View[136].x)
    {
        float3 WP = TWP - View[62].xyz;
        float3 D = WP - Prim[8].xyz;
        float3 Ext = Prim[9].xyz + 1.0;
        bool Outside = any(Ext < abs(D));
        float H = frac(dot(WP, float3(0.57735026, 0.57735026, 0.57735026)) * 0.002);
        float3 C = (0.5 < H) ? float3(0.0, 1.0, 1.0) : float3(1.0, 1.0, 0.0);
        if (Outside) E = float4(C, dot(C, float3(0.2126, 0.7152, 0.0722)));
    }
    o0 = float4(E.xyz * View[128].x, E.w);
    o5 = float4(0.0, 0.0, 0.0, 0.0);
"""
# the game's 4.18 base pass for Unlit (EndMaterial_BlackBody's): only the emissive, the flags, the shading model id 0
BASE_PASS_UNLIT = r'''
    float3 Emissive = max(P_EmissiveColor + SelectionColor, float3(0.0, 0.0, 0.0));
    float Threshold = (0.0 < Prim[11].y) ? PLB[5].x : 1.0;
    uint Mask = ((Noise.x * 0.99609375 + 0.001953125) < Threshold) ? 32u : 0u;
    uint Flags = asuint(Prim[11].x);
    Mask += ((Flags & 2u) != 0u ? 64u : 0u) + ((Flags & 4u) != 0u ? 128u : 0u);
    float4 E = float4(Emissive, 0.0);
    if (0.0 < View[136].x)
    {
        float3 WP = TWP - View[62].xyz;
        float3 D = WP - Prim[8].xyz;
        float3 Ext = Prim[9].xyz + 1.0;
        bool Outside = any(Ext < abs(D));
        float H = frac(dot(WP, float3(0.57735026, 0.57735026, 0.57735026)) * 0.002);
        float3 C = (0.5 < H) ? float3(0.0, 1.0, 1.0) : float3(1.0, 1.0, 0.0);
        if (Outside) E = float4(C, dot(C, float3(0.2126, 0.7152, 0.0722)));
    }
    o0 = E * View[128].x;
    o1 = float4(0.0, 0.0, 0.0, (Flags & 1u) != 0u ? 0.33333334 : 0.0);
    o2 = float4(0.0, 0.0, 0.0, float(Mask) * 0.003921569);
    o3 = float4(0.0, 0.0, 0.0, 0.0);
    o4 = float4(0.0, 0.0, 0.0, 0.0);
#if STATIC_SWITCH_CAMERA_RELATIVE_DEPTH
    o5 = float4(0.0, 0.0, 0.0, P_CameraRelativeDepth);
#else
    o5 = float4(0.0, 0.0, 0.0, 0.0);
#endif
'''
# the game's lit translucent base pass (alpha composite, EndMaterial_Particle's lit instances): the diffuse lit by the
# translucency lighting volume (its inner and outer cascades: the ambient and directional SH) as the game's volumetric
# modes have it - Average the ambient alone, Rough toward the camera, Scatter from behind, Refract along the view refracted
# into the surface (index 1.5); Gloss and Refract add the reflection capture's specular (the geometric roughness), and
# Refract the capture behind the surface through it; the game's multi-bounce occlusion; the colour premultiplied by the
# opacity (not the specular, nor the emissive), then as the unlit one (the fog, the particle's visibility and coverage)
BASE_PASS_TRANSLUCENT_LIT = r"""
    float3 MN = P_Normal * View[134].w + View[134].xyz;
    MN = normalize(MN);
    float3 N = normalize(MN.x * T2W0 + MN.y * T2W1 + MN.z * T2W2.xyz);
    float3 BaseColor = saturate(P_BaseColor);
    float Metallic = saturate(P_Metallic);
    float Specular = saturate(P_Specular);
    float AO = saturate(P_AmbientOcclusion);
    float3 Color = max(P_EmissiveColor + SelectionColor, float3(0.0, 0.0, 0.0));
    float3 Diffuse = BaseColor * (1.0 - Metallic);
    float F0s = Specular * Specular * 0.16;
    float3 SpecColor = (BaseColor - F0s) * Metallic + F0s;
    Diffuse = Diffuse * View[132].w + View[132].xyz;
    SpecColor = SpecColor * View[133].w + View[133].xyz;
    float3 Debug = SpecColor * 0.45 + Diffuse;
    float3 MB = max(AO, ((AO * (Debug * 2.0404 - 0.3324) + (Debug * -4.7951 + 0.6417)) * AO + (Debug * 2.7552 + 0.6903)) * AO);
    float3 WPL = TWP - View[62].xyz + LightingPositionOffset;
    float3 IUV = (WPL - View[143].xyz) * View[145].xyz;
    float3 OUV = (WPL - View[144].xyz) * View[146].xyz;
    float3 CB = saturate((0.5 - abs(IUV - 0.5)) * 6.0);
    float CW = CB.x * CB.y * CB.z;
    float3 OAmb = min(AmbientOuterVolume.SampleLevel(TranslucencyVolumeSampler, OUV, 0.0).xyz, 65504.0) * View[128].y;
    float3 Amb = lerp(OAmb, min(AmbientInnerVolume.SampleLevel(TranslucencyVolumeSampler, IUV, 0.0).xyz, 65504.0) * View[128].y, CW);
#if TLM_AVERAGE
    float3 Lighting = Amb * 0.886227;
#else
    float3 ODir = min(DirectionalOuterVolume.SampleLevel(TranslucencyVolumeSampler, OUV, 0.0).xyz, 65504.0) * View[128].y;
    float3 Dir = lerp(ODir, min(DirectionalInnerVolume.SampleLevel(TranslucencyVolumeSampler, IUV, 0.0).xyz, 65504.0) * View[128].y, CW);
    float3 SHS = Amb / max(dot(Amb, float3(0.2126, 0.7152, 0.0722)), 0.00001);
  #if TLM_SCATTER
    float3 LD = -V;
    float LC = 0.7531692;
  #elif TLM_REFRACT
    float NoVr = dot(N, V);
    float3 LD = normalize((N * NoVr - V) * 0.6666667 - N * sqrt(1.0 - (1.0 - NoVr * NoVr) * 0.44444445));
    float LC = 0.7531692;
  #else
    float3 LD = V;
    float LC = 1.0233267;
  #endif
    float4 ST = float4(0.886227, -LC * LD.y, LC * LD.z, -LC * LD.x);
    float3 Lighting = max(float3(dot(float4(Amb.r, Dir * SHS.r), ST), dot(float4(Amb.g, Dir * SHS.g), ST), dot(float4(Amb.b, Dir * SHS.b), ST)), 0.0);
#endif
    float Opacity = saturate(P_Opacity);
    float3 Lit = Diffuse * Lighting * MB * Opacity;
#if TLM_GLOSS || TLM_REFRACT
    {
    float NoV = dot(N, V);
    float3 NDX = ddx_coarse(N);
    float3 NDY = ddy_coarse(N);
    float GR2 = min((dot(NDX, NDX) + dot(NDY, NDY)) * 0.5, 0.18);
    float GR = sqrt(GR2);
    // the specular occlusion (the occlusion and the view angle, against the geometric roughness)
    float SOB = saturate(NoV) + AO;
    float SpecOcc = saturate(AO + (SOB < 0.000001 ? 0.0 : pow(SOB, GR2)) - 1.0);
    float FlagScale = (asuint(Prim[11].x) & 2u) != 0u ? View[130].x : 1.0;
    float3 Refl = normalize(N * NoV * 2.0 - V);
    float2 RC = GR * float2(-1.0, -0.0275) + float2(1.0, 0.0425);
    float Env = min(min(RC.x * RC.x, exp2(saturate(NoV) * -9.28)) * RC.x + RC.y, 1.0);
    float Lod = GR * (7.0 - 3.0 * GR);
    float3 CaptureScale = Globals[FOG_GLOBALS + 13].x * View[153].xyz;
    float CaptureIndex = float(asint(Globals[FOG_GLOBALS + 10].x));
    float3 Spec = ReflectionCaptures.SampleLevel(ReflectionCaptureSampler, float4(Refl, CaptureIndex), Lod).xyz * CaptureScale * Env;
    Lit += Spec * FlagScale * SpecOcc;
  #if TLM_REFRACT
    float Env2 = min(min(RC.x * RC.x, exp2(abs(NoV) * -9.28)) * RC.x + RC.y, 1.0);
    float3 Through = ReflectionCaptures.SampleLevel(ReflectionCaptureSampler, float4(-N, CaptureIndex), Lod).xyz * CaptureScale;
    Lit += Through * ((1.0 - Env2) * (1.0 - Env2)) * (Diffuse * FlagScale) * lerp(float3(1.0, 1.0, 1.0), MB, Opacity);
  #endif
    }
#endif
    float Fog = 1.0;
    float3 FogColor = float3(0.0, 0.0, 0.0);
""" + BASE_PASS_TRANSLUCENT_UNLIT[BASE_PASS_TRANSLUCENT_UNLIT.index('#if TRANSLUCENT_FOG_PER_PIXEL'):BASE_PASS_TRANSLUCENT_UNLIT.index('    float Opacity = saturate(P_Opacity);')] + r"""
    float Vis = P_PixelContextVector1.x;
    float Vis8 = Vis * Vis;
    Vis8 *= Vis8;
    Vis8 *= Vis8;
#if TLM_REFRACT
    float Cover = 1.0;
#else
    float Cover = Opacity;
#endif
    float4 E = float4((Lit * Vis + Color * Vis8) * Fog + (FogColor * Cover) * Vis, Cover * Vis) * saturate(P_OpacityMask);
    if (0.0 < View[140].z) E = float4(Debug, dot(Debug, float3(0.2126, 0.7152, 0.0722)));
    if (0.0 < View[136].x)
    {
        float3 WP = TWP - View[62].xyz;
        float3 D = WP - Prim[8].xyz;
        float3 Ext = Prim[9].xyz + 1.0;
        bool Outside = any(Ext < abs(D));
        float H = frac(dot(WP, float3(0.57735026, 0.57735026, 0.57735026)) * 0.002);
        float3 C = (0.5 < H) ? float3(0.0, 1.0, 1.0) : float3(1.0, 1.0, 0.0);
        if (Outside) E = float4(C, dot(C, float3(0.2126, 0.7152, 0.0722)));
    }
    o0 = float4(E.xyz * View[128].x, E.w);
    o5 = float4(0.0, 0.0, 0.0, 0.0);
"""
# the game's forward-lit translucent base pass (EndMaterial_Glass, Tear, Thin, Jewel and Water): the light grid's lights
# (the directional light with its cascaded shadow, the local lights with theirs, their IES profiles, the sun and the
# lights as spheres), the reflection captures (and their mip 4 as the irradiance the reflections are normalized by), the
# multi-bounce and specular occlusions, then the master's own composition (its type switch: STATIC_SWITCH_GLASS, _TEAR...)
FORWARD_HELPERS = r'''
float3 FwdMultiBounce(float A, float3 D)
{
    return A * max(((D * 2.0404 - 0.3324) * A + (D * -4.7951 + 0.6417)) * A + (D * 2.7552 + 0.6903), 1.0);
}
float FwdSpecOcc(float A, float NoVs, float A1)
{
    float B = A + NoVs;
    return saturate(A + (B < 0.000001 ? 0.0 : pow(B, A1)) - 1.0);
}
float2 FwdEnvAB(float R, float NoV)
{
    float4 C = R * float4(-1.0, -0.0275, -0.572, 0.022) + float4(1.0, 0.0425, 1.04, -0.04);
    float A004 = min(C.x * C.x, exp2(NoV * -9.28)) * C.x + C.y;
    return A004 * float2(-1.04, 1.04) + C.zw;
}
// the light as a sphere (its sine seen from the surface): the half vector that gives the most reflection (a Newton step)
void FwdSphereMaxNoH(float NoV, float NoL, float VoL, float SinAlpha, float NoVc, out float NoH, out float VoH)
{
    bool Flat = false;
    if (0.0 < SinAlpha)
    {
        float CosAlpha = sqrt(1.0 - SinAlpha * SinAlpha);
        float RoL = 2.0 * NoL * NoV - VoL;
        if (RoL < CosAlpha)
        {
            float Inv = SinAlpha * rsqrt(max(1.0 - RoL * RoL, 0.00001));
            float NoTr = Inv * (NoV - RoL * NoL);
            float VoTr = Inv * (2.0 * NoV * NoV - 1.0 - RoL * VoL);
            float NxLoV = sqrt(saturate(2.0 * NoL * NoV * VoL + (1.0 - NoL * NoL - NoV * NoV - VoL * VoL)));
            float NoBr = Inv * NxLoV;
            float VoBr = 2.0 * (NoV * NoBr);
            float NoLVTr = NoL * CosAlpha + NoV + NoTr;
            float VoLVTr = VoL * CosAlpha + VoTr + 1.0;
            float p = NoBr * VoLVTr;
            float q = NoLVTr * VoLVTr;
            float s = VoBr * NoLVTr;
            float xNum = q * (-0.5 * p + 0.5 * (NoV * NoBr * NoLVTr));
            float xDenom = p * p + s * (s - 2.0 * p) + NoLVTr * ((NoL * CosAlpha + NoV) * (VoLVTr * VoLVTr) + q * (-0.5 * (VoL * CosAlpha + VoLVTr) - 0.5));
            float N2 = xNum * xNum;
            float Rcp = 1.0 / max((xDenom * xDenom - N2) * 0.5 + N2, 0.00001);
            float SinTheta = max(min(xDenom * xNum * Rcp, 1.0), -1.0);
            float CosTheta = max(1.0 - N2 * Rcp, -1.0);
            NoTr = CosTheta * NoTr + SinTheta * NoBr;
            VoTr = CosTheta * VoTr + SinTheta * VoBr;
            NoL = NoL * CosAlpha + NoTr;
            VoL = VoL * CosAlpha + VoTr;
        }
        else
            Flat = true;
    }
    float InvLenH = rsqrt(max(2.0 + 2.0 * VoL, 0.00001));
    NoH = saturate((NoV + NoL) * InvLenH);
    VoH = saturate(InvLenH + InvLenH * VoL);
    if (Flat)
    {
        NoH = 1.0;
        VoH = NoVc;
    }
}
// one light's specular (GGX, the sphere's energy) and diffuse (Lambert less what the specular reflects at the light)
void FwdLight(float3 N, float3 V, float3 L, float NoV, float NoVc, float NoVv, float SinA, float SinH, float Ap, float Ap2, float Rp,
              float3 SpecColor, float F0a, float F90, float3 Diffuse, out float3 Spec, out float3 Diff)
{
    float NoL = dot(N, L);
    float VoL = dot(V, L);
    float NoH, VoH;
    FwdSphereMaxNoH(NoV, NoL, VoL, SinA, NoVc, NoH, VoH);
    float W = max(NoL, -SinH) + SinH;
    float NoLs = saturate(max(NoL, 0.0) < SinH ? W * W / (SinH * 4.0) : NoL);
    float Dd = NoH * NoH * (Ap * Ap - 1.0) + 1.0;
    float Dg = (Ap2 * 0.31830987) / (Dd * Dd);
    float Vis = 0.5 / (Ap * (NoVv + NoLs - 2.0 * NoVv * NoLs) + 2.0 * NoVv * NoLs);
    float Fx = 1.0 - VoH;
    float Fc = Fx * ((Fx * Fx) * (Fx * Fx));
    float3 F = Fc * (F90 - SpecColor) + SpecColor;
    float2 AB = FwdEnvAB(Rp, NoLs);
    float EnvL = saturate(F0a * AB.x + F90 * AB.y);
    float Energy = (0.0 < SinA) ? Ap2 / ((Ap * 3.0 + SinA) * (SinA * 0.25) * (1.0 / max(VoH, 0.00001)) + Ap2) : 1.0;
    Spec = F * (Vis * (NoLs * Dg)) * Energy;
    Diff = Diffuse * ((1.0 - EnvL) * NoLs * 0.31830987);
}
// a shadow map lookup: the position's depth against the atlas slice's, jittered by the blue noise; 1 past the map's far end
// a device depth as the scene's linear depth
float SceneDepthLinear(float Z)
{
    return Z * View[57].x + View[57].y + 1.0 / (Z * View[57].z - View[57].w);
}
float FwdShadow(float3 SP, float2 Size, float2 InvSize, float2 J, float Slice, float Sharp)
{
    float2 UV = (SP.xy * Size + J) * InvSize;
    float S = ShadowAtlas.SampleLevel(ShadowSampler, float3(UV, Slice), 0.0).x;
    return min(saturate((S - SP.z) * Sharp + 1.0) + (0.99 < S ? 1.0 : 0.0), 1.0);
}
'''
BASE_PASS_FORWARD = r'''
#if MASKED_BASE_PASS
    float2 NzC = float2(NoiseW.w, NoiseW.x) * 0.99609375 + 0.001953125;
    if (!((NzC.y < P_OpacityMask) && (NzC.x < Globals[2].x))) discard;
#endif
    float3 MN = P_Normal * View[134].w + View[134].xyz;
    MN = normalize(MN);
    float3 N = normalize(MN.x * T2W0 + MN.y * T2W1 + MN.z * T2W2.xyz);
    float3 BaseColor = saturate(P_BaseColor);
    float Metallic = saturate(P_Metallic);
    float Specular = saturate(P_Specular);
    float Rough = saturate(P_Roughness) * View[135].y + View[135].x;
    float AO = saturate(P_AmbientOcclusion);
    float Opacity = saturate(P_Opacity);
    float3 Emissive = max(P_EmissiveColor + SelectionColor, float3(0.0, 0.0, 0.0));
    float Threshold = (0.0 < Prim[11].y) ? PLB[5].x : 1.0;
    uint Mask = ((NoiseW.x * 0.99609375 + 0.001953125) < Threshold) ? 32u : 0u;
    uint Flags = asuint(Prim[11].x);
    Mask += ((Flags & 2u) != 0u ? 64u : 0u) + ((Flags & 4u) != 0u ? 128u : 0u);
    float3 DX = ddx_coarse(N);
    float3 DY = ddy_coarse(N);
    float K = min((dot(DX, DX) + dot(DY, DY)) * 0.5, 0.18);
    float A1 = min(Rough * Rough + K, 1.0);
    float FRough = sqrt(A1);
    float3 Diffuse = BaseColor * (1.0 - Metallic);
    float F0s = Specular * Specular * 0.16;
    float3 SpecColor = (BaseColor - F0s) * Metallic + F0s;
    Diffuse = Diffuse * View[132].w + View[132].xyz;
    SpecColor = SpecColor * View[133].w + View[133].xyz;
    float3 Debug = SpecColor * 0.45 + Diffuse;
    float3 WP = TWP - View[62].xyz;
    float NoV = dot(N, V);
    float NoVc = max(abs(NoV), 0.00001);
    float NoVs = saturate(NoV);
    float NoVv = min(NoVc, 1.0);
    float SpecOcc = FwdSpecOcc(AO, NoVs, A1);
    float3 MB = FwdMultiBounce(AO, Debug);
    float FlagScale = (Mask & 64u) != 0u ? View[130].x : 1.0;
    float F0a = dot(SpecColor, float3(0.33333334, 0.33333334, 0.33333334));
    float F90 = saturate(F0a * 50.0);
    float Rp = max(FRough, 0.04);
    float Ap = Rp * Rp;
    float Ap2 = Ap * Ap;
#if STATIC_SWITCH_WATER
    // the water's reflections (the captures, the screen's): roughened toward fully rough by its foam
    // (PixelContextVector0.w); its lights keep the surface's roughness
    float FRoughI = min(sqrt(lerp(A1, 1.0, P_PixelContextVector0.w)), 1.0);
    float A1s = FRoughI * FRoughI;
#else
    float FRoughI = FRough;
    float A1s = A1;
#endif
    float RpI = max(FRoughI, 0.04);
    float ApI = RpI * RpI;
    float Ap2I = ApI * ApI;
    float2 ABw = FwdEnvAB(FRough, NoVs);
    float4 EnvW = saturate(float4(SpecColor, F0a) * ABw.x + ABw.y * F90);
    // the light grid's cell
    uint2 Pix = (uint2)(SvPosition.xy - View[121].xy);
    float Zs = log2(SvPosition.w * FLD[3].x + FLD[3].y) * FLD[3].z;
    Zs = min(float(asint(FLD[1].z) - 1), max(Zs, 0.0));
    uint2 Cell = Pix >> asuint(FLD[2].x);
    uint GridIndex = ((uint)Zs * asuint(FLD[1].y) + Cell.y) * asuint(FLD[1].x) + Cell.x;
    float3 Rv = normalize(N * NoV * 2.0 - V);
#if STATIC_SWITCH_JEWEL || STATIC_SWITCH_WATER
    // (the reflection turned back above the surface's geometric normal)
    float RvD = dot(T2W2.xyz, Rv);
    Rv = normalize(Rv + (abs(RvD) - RvD) * T2W2.xyz);
#endif
    // the reflection captures (sphere or box), nearest first, until they cover the point
    uint CapCell = (GridIndex + asuint(FLD[0].w)) * 2u;
    uint NumCaps = NumCulledLightsGrid[CapCell];
    uint CapStart = NumCulledLightsGrid[CapCell + 1u];
    float CapLod = min(FRoughI * (7.0 - 3.0 * FRoughI), 4.0);
    float SpecW = 1.0;
    float DiffW = 1.0;
    float3 SpecAcc = float3(0.0, 0.0, 0.0);
    float3 DiffAcc = float3(0.0, 0.0, 0.0);
    for (uint ci = 0; ci < NumCaps; ci++)
    {
        uint c = CulledLightDataGrid[CapStart + ci];
        float3 CD = WP - RCU[c].xyz;
        float CD2 = dot(CD, CD);
        if (CD2 < RCU[c].w * RCU[c].w)
        {
            float Fade;
            // the reflection's lookup (the water pass's parallax corrected: toward where the reflection leaves the
            // capture's box or sphere, from the capture's centre and offset)
            float3 LV = Rv;
            if (0.0 < RCU[341 + c].z)
            {
                float3 BP = mul(float4(WP, 1.0), float4x4(RCU[1023 + 4 * c], RCU[1024 + 4 * c], RCU[1025 + 4 * c], RCU[1026 + 4 * c])).xyz;
                float4 BS = RCU[2387 + c];
                float3 Inner = BS.xyz - BS.w * 0.5;
                float3 Out = max(BP * BS.xyz - Inner, 0.0) - min(BP * BS.xyz + Inner, 0.0);
                float X = saturate((Out.x + Out.y + Out.z) * (1.0 / (0.7 * BS.w)));
                Fade = 1.0 - X * X * (3.0 - 2.0 * X);
#if STATIC_SWITCH_WATER_ENVIRONMENT
                if (0.0 < Fade)
                {
                    float3 LD = Rv.y * RCU[1024 + 4 * c].xyz;
                    LD = Rv.x * RCU[1023 + 4 * c].xyz + LD;
                    LD = Rv.z * RCU[1025 + 4 * c].xyz + LD;
                    float3 Inv = rcp(LD);
                    float3 Near = min(BP * Inv - Inv, BP * Inv + Inv);
                    float T = max(max(Near.z, Near.y), Near.x);
                    LV = -T * Rv + (CD - RCU[682 + c].xyz);
                }
#endif
            }
            else
            {
                float X = saturate(sqrt(CD2) / RCU[c].w);
                X = max(X * 2.5 - 1.5, 0.0);
                Fade = 1.0 - X * X * (3.0 - 2.0 * X);
#if STATIC_SWITCH_WATER_ENVIRONMENT
                if (0.0 < Fade)
                {
                    float RD = dot(Rv, CD);
                    float Det = RCU[c].w * RCU[c].w + (RD * RD - CD2);
                    if (0.0 <= Det)
                        LV = (sqrt(Det) - RD) * Rv + (CD - RCU[682 + c].xyz);
                }
#endif
            }
            if (0.0 < Fade)
            {
                float Wt = Fade * RCU[341 + c].x;
                SpecAcc = ReflectionCaptures.SampleLevel(ReflectionCaptureSampler, float4(LV, RCU[341 + c].y), CapLod).xyz * (SpecW * Wt) + SpecAcc;
                SpecW *= 1.0 - Fade;
                DiffAcc = ReflectionCaptures.SampleLevel(ReflectionCaptureSampler, float4(N, RCU[341 + c].y), 4.0).xyz * (DiffW * Wt) + DiffAcc;
                DiffW *= 1.0 - Fade;
                if (SpecW < 0.001)
                    break;
            }
        }
    }
    float3 SpecIBL = SpecAcc * View[153].xyz;
    float3 DiffIBL = DiffAcc * View[153].xyz;
    float LDI = max(dot(DiffIBL, float3(0.2126, 0.7152, 0.0722)), 0.00001);
    float3 AmbN = float3(0.0, 0.0, 0.0);
#if STATIC_SWITCH_THIN
    // the ambient cube (its average colour, its light along +x/y/z and along -x/y/z; the global override blended over
    // it): along the normal, and from behind (along the view) blended toward the average
    float3 A0 = AmbientCube0.SampleLevel(TranslucencyVolumeSampler, float3(0.0, 0.0, 0.0), 0.0).xyz * 0.31830987;
    float3 Pc = AmbientCubeP.SampleLevel(TranslucencyVolumeSampler, float3(0.0, 0.0, 0.0), 0.0).xyz * 0.31830987;
    float3 Nc = AmbientCubeN.SampleLevel(TranslucencyVolumeSampler, float3(0.0, 0.0, 0.0), 0.0).xyz * 0.31830987;
    float3 Chroma = A0 / max(dot(A0, float3(0.2126, 0.7152, 0.0722)), 0.0001);
    float3 Chroma2 = Globals[10].xyz / max(dot(Globals[10].xyz, float3(0.2126, 0.7152, 0.0722)), 0.0001);
    float3 SN = saturate(N);
    SN *= SN;
    float3 SNn = saturate(-N);
    SNn *= SNn;
    AmbN = (dot(Pc, SN) + dot(Nc, SNn)) * Chroma;
    if (0.0 < Globals[10].w)
        AmbN = lerp(AmbN, (dot(Globals[11].xyz, SN) + dot(Globals[12].xyz, SNn)) * Chroma2, Globals[10].w);
    float3 SV = saturate(-V);
    SV *= SV;
    float3 SVn = saturate(V);
    SVn *= SVn;
    float3 AmbV = (dot(Pc, SV) + dot(Nc, SVn)) * Chroma;
    float3 A0b = A0;
    if (0.0 < Globals[10].w)
    {
        A0b = lerp(A0, Globals[10].xyz, Globals[10].w);
        AmbV = lerp(AmbV, (dot(Globals[11].xyz, SV) + dot(Globals[12].xyz, SVn)) * Chroma2, Globals[10].w);
    }
    float3 AmbB = lerp(A0b, AmbV, asfloat(0x3f7a9fbeu));
    // the translucency volume's light from behind (along the view)
    float3 IUV = (WP - View[143].xyz) * View[145].xyz;
    float3 OUV = (WP - View[144].xyz) * View[146].xyz;
    float3 CB = saturate((0.5 - abs(IUV - 0.5)) * 6.0);
    float CW = CB.x * CB.y * CB.z;
    float3 OAmb = min(AmbientOuterVolume.SampleLevel(TranslucencyVolumeSampler, OUV, 0.0).xyz, 65504.0) * View[128].y;
    float3 VAmb = lerp(OAmb, min(AmbientInnerVolume.SampleLevel(TranslucencyVolumeSampler, IUV, 0.0).xyz, 65504.0) * View[128].y, CW);
    float3 ODir = min(DirectionalOuterVolume.SampleLevel(TranslucencyVolumeSampler, OUV, 0.0).xyz, 65504.0) * View[128].y;
    float3 VDir = lerp(ODir, min(DirectionalInnerVolume.SampleLevel(TranslucencyVolumeSampler, IUV, 0.0).xyz, 65504.0) * View[128].y, CW);
    float3 SHS = VAmb / max(dot(VAmb, float3(0.2126, 0.7152, 0.0722)), 0.00001);
    float LC = asfloat(0x3f803c39u);
    float4 ST = float4(0.886227, LC * V.y, -LC * V.z, LC * V.x);
    float3 VolSH = max(float3(dot(float4(VAmb.r, VDir * SHS.r), ST), dot(float4(VAmb.g, VDir * SHS.g), ST), dot(float4(VAmb.b, VDir * SHS.b), ST)), 0.0);
    float4 AmbR = max(float4(AmbN, dot(AmbN, float3(0.2126, 0.7152, 0.0722))), 0.00001) / LDI;
    float3 MixS = lerp(SpecIBL * AmbR.w, AmbR.xyz * dot(SpecIBL, float3(0.2126, 0.7152, 0.0722)), saturate(AmbR.w - 1.0));
    float NoVi = NoVv;
#elif STATIC_SWITCH_JEWEL || STATIC_SWITCH_WATER
    // the ambient cube's average (the global override blended over it), the translucency volume's ambient
    float3 A0b = AmbientCube0.SampleLevel(TranslucencyVolumeSampler, float3(0.0, 0.0, 0.0), 0.0).xyz * 0.31830987;
    if (0.0 < Globals[10].w)
        A0b = lerp(A0b, Globals[10].xyz, Globals[10].w);
    AmbN = A0b;
    float3 IUV = (WP - View[143].xyz) * View[145].xyz;
    float3 OUV = (WP - View[144].xyz) * View[146].xyz;
    float3 CB = saturate((0.5 - abs(IUV - 0.5)) * 6.0);
    float CW = CB.x * CB.y * CB.z;
    float3 OAmb = min(AmbientOuterVolume.SampleLevel(TranslucencyVolumeSampler, OUV, 0.0).xyz, 65504.0) * View[128].y;
    float3 VolA = lerp(OAmb, min(AmbientInnerVolume.SampleLevel(TranslucencyVolumeSampler, IUV, 0.0).xyz, 65504.0) * View[128].y, CW) * 0.886227;
    float4 AmbR = max(float4(AmbN, dot(AmbN, float3(0.2126, 0.7152, 0.0722))), 0.00001) / LDI;
    float3 MixS = lerp(SpecIBL * AmbR.w, AmbR.xyz * dot(SpecIBL, float3(0.2126, 0.7152, 0.0722)), saturate(AmbR.w - 1.0));
    float NoVi = NoVv;
#else
    float3 MixS = SpecIBL * (0.00001 / LDI);
    float NoVi = NoVs;
#endif
    SpecIBL = lerp(SpecIBL, MixS, min(RpI + RpI, 1.0));
    SpecIBL = lerp(SpecIBL, AmbN, Ap2I);
#if STATIC_SWITCH_WATER
    // (the water's own reflectance, not the view's override of it)
    SpecIBL = lerp(SpecIBL, F0s * 0.45 * AmbN, View[159].w);
#elif STATIC_SWITCH_JEWEL
    SpecIBL = lerp(SpecIBL, F0a * 0.45 * AmbN, View[159].w);
#else
    SpecIBL = lerp(SpecIBL, SpecColor * 0.45 * AmbN, View[159].w);
#endif
    float2 ABv = FwdEnvAB(FRoughI, NoVi);
    float3 EnvS = saturate(SpecColor * ABv.x + ABv.y * F90);
    float EnvVa = saturate(F0a * ABv.x + ABv.y * F90);
#if STATIC_SWITCH_JEWEL || STATIC_SWITCH_WATER
    // (the environment's water falls back to the unscaled reflection where the screen's reflection is far)
    float3 SpecIBLu = SpecIBL;
    SpecIBL = SpecIBL * FlagScale;
#else
    SpecIBL = SpecIBL * EnvS * FlagScale;
#endif
    // the direct lights (none for the environment's water: the water pass draws it lit by the reflections alone)
    float3 DirSpec = float3(0.0, 0.0, 0.0);
    float3 DirDiff = float3(0.0, 0.0, 0.0);
    float3 LocSpec = float3(0.0, 0.0, 0.0);
    float3 LocDiff = float3(0.0, 0.0, 0.0);
#if !STATIC_SWITCH_WATER_ENVIRONMENT
    // the shadow atlas, the blue noise's jitter
    float2 SSize;
    float SElems;
    ShadowAtlas.GetDimensions(SSize.x, SSize.y, SElems);
    float2 SInv = 1.0 / SSize;
    float2 Nz = NoiseW.xy * 2.0 - 1.0;
    float2 Jit = (1.0 - sqrt(1.0 - abs(Nz))) * sign(Nz);
    // the directional light
    if (asuint(FLD[0].z) != 0u && ((asuint(FLD[7].x) >> 8) & asuint(Prim[16].w)) != 0u)
    {
        float StaticF = (asuint(FLD[7].x) & 1u) != 0u ? 1.0 : 0.0;
        uint NC = asuint(FLD[8].x);
        uint CI = NC;
        for (uint i = 0; i < NC; i++)
        {
            if (SvPosition.w < FLD[9][i])
            {
                CI = i;
                break;
            }
        }
        bool HasSh = false;
        float DSh = 1.0;
        if (CI < NC)
        {
            float4 SP = mul(float4(WP, 1.0), float4x4(FLD[10 + 4 * CI], FLD[11 + 4 * CI], FLD[12 + 4 * CI], FLD[13 + 4 * CI]));
            SP.xy /= SP.w;
            float4 MM = FLD[26 + CI];
            if (all(SP.xy >= MM.xy) && all(MM.zw >= SP.xy))
            {
                DSh = FwdShadow(SP.xyz, SSize, SInv, Jit * max(1.0 - FLD[40].y, 0.0) * 3.0, FLD[30 + CI].x, FLD[40].x);
                HasSh = true;
            }
        }
        float3 L = normalize(FLD[5].xyz);
        float DAO = AO;
        if (HasSh)
        {
            float Static = StaticF * (Threshold - 1.0) + 1.0;
            float Fd = saturate(SvPosition.w * FLD[7].z + FLD[7].w);
            Fd *= Fd;
            float SScale = (Mask & 128u) != 0u ? View[131].x : 1.0;
            DAO = min(AO, SScale * ((Static - DSh) * Fd + DSh));
        }
        if (0.0 < DAO)
        {
            float3 MBd = FwdMultiBounce(DAO, Debug);
            float SOd = FwdSpecOcc(DAO, NoVs, A1);
            float3 S, D;
            FwdLight(N, V, L, NoV, NoVc, NoVv, (1.0 - Ap) * 0.0047, 0.0047, Ap, Ap2, Rp, SpecColor, F0a, F90, Diffuse, S, D);
            DirSpec = S * FLD[6].xyz * SOd;
            DirDiff = D * FLD[6].xyz * MBd;
        }
    }
    // the local lights (spot or point, a sphere or a tube; with the soft radius set, a wrapped diffuse and no shadow)
    uint NumLights = NumCulledLightsGrid[GridIndex * 2u];
    uint LStart = NumCulledLightsGrid[GridIndex * 2u + 1u];
    for (uint li = 0; li < NumLights; li++)
    {
        uint LI = CulledLightDataGrid[LStart + li] * 11u;
        uint4 L2r = ForwardLocalLightBuffer[LI + 2u];
        if (((L2r.w >> 8) & asuint(Prim[16].w)) == 0u)
            continue;
        float4 L0 = asfloat(ForwardLocalLightBuffer[LI]);
        float4 L1 = asfloat(ForwardLocalLightBuffer[LI + 1u]);
        float3 LDir = asfloat(L2r.xyz);
        float4 L3 = asfloat(ForwardLocalLightBuffer[LI + 3u]);
        uint4 L4r = ForwardLocalLightBuffer[LI + 4u];
        float4 L5 = asfloat(ForwardLocalLightBuffer[LI + 5u]);
        bool Soft = 0u < L4r.w;
        float StaticF = (L2r.w & 1u) != 0u ? 1.0 : 0.0;
        bool HasSh = 0.0 <= L5.x;
        bool Spot = -2.0 < L3.x;
        float LSh = 1.0;
        if (HasSh)
        {
            float4 SB = asfloat(ForwardLocalLightBuffer[LI + 6u]);
            float4 SP = mul(float4(WP, 1.0), float4x4(asfloat(ForwardLocalLightBuffer[LI + 7u]), asfloat(ForwardLocalLightBuffer[LI + 8u]),
                                                      asfloat(ForwardLocalLightBuffer[LI + 9u]), asfloat(ForwardLocalLightBuffer[LI + 10u])));
            SP.xy /= SP.w;
            if (all(SP.xy >= SB.xy) && all(SB.zw >= SP.xy))
                LSh = FwdShadow(SP.xyz, SSize, SInv, (Jit * 3.0) * max(1.0 - L5.w, 0.0), L5.x, L5.z);
        }
        float3 ToL = L0.xyz - WP;
        float DistSq = dot(ToL, ToL);
        float3 Ln = ToL * rsqrt(DistSq);
        float Ang = acos(clamp(dot(Ln, -LDir), -1.0, 1.0));
        float IES = IESAtlas.SampleLevel(IESSampler, float2(1.0 - Ang * 0.31830987, (float(asuint(L5.y)) + 0.5) * Globals[FWD_IES_ROW].w), 0.0).x;
        float3 LColor = L1.xyz * IES;
        float Att = 1.0;
        if (asuint(L1.w) == 0u)
        {
            float SrcLen = f16tof32(asuint(L3.w));
            float M = L0.w * L0.w * DistSq;
            M = max(1.0 - M * M, 0.0);
            M *= M;
            if (0.0 < SrcLen && Soft)
            {
                float3 Lp = SrcLen * 0.5 * asfloat(L4r.xyz) + ToL;
                float3 Lm = -(SrcLen * 0.5) * asfloat(L4r.xyz) + ToL;
                float lp = sqrt(dot(Lp, Lp));
                float lm = sqrt(dot(Lm, Lm));
                ToL = (lp * Lm + Lp * lm) / max(lp + lm, 0.00001);
                DistSq = dot(ToL, ToL);
            }
            Att = M / (L3.z * L3.z + (DistSq + 1.0));
        }
        float LD2 = dot(ToL, ToL);
        float3 Ld = ToL * rsqrt(LD2);
        float SpotF = saturate((dot(Ld, LDir) - L3.x) * L3.y);
        float LMask = Spot ? SpotF * SpotF * Att : Att;
        if (0.0 < LMask)
        {
            float3 LS = float3(0.0, 0.0, 0.0);
            float3 LDf = float3(0.0, 0.0, 0.0);
            if (!Soft)
            {
                float LAO = HasSh ? min(AO, LSh * (StaticF * (Threshold - 1.0) + 1.0)) : AO;
                if (0.0 < LAO)
                {
                    float3 MBl = FwdMultiBounce(LAO, Debug);
                    float SOl = FwdSpecOcc(LAO, NoVs, A1);
                    float SinR = L3.z / max(sqrt(LD2), 0.001);
                    float3 S, D;
                    FwdLight(N, V, Ld, NoV, NoVc, NoVv, saturate((1.0 - Ap) * SinR), saturate(SinR), Ap, Ap2, Rp, SpecColor, F0a, F90, Diffuse, S, D);
                    LS = LColor * S * LMask * SOl;
                    LDf = LColor * D * LMask * MBl;
                }
            }
            else
            {
                float Wr = max((dot(N, Ld) + 1.2) * 0.20661157, 0.0) * 0.31830987;
                LS = LColor * (EnvW.xyz * Wr) * LMask * SpecOcc;
                LDf = LColor * (Diffuse * ((1.0 - EnvW.w) * Wr)) * LMask * MB;
            }
            LocSpec += LS;
            LocDiff += LDf;
        }
    }
#endif
#if !STATIC_SWITCH_WATER_ENVIRONMENT
''' + BASE_PASS_TRANSLUCENT_UNLIT[BASE_PASS_TRANSLUCENT_UNLIT.index('    float Fog = 1.0;'):BASE_PASS_TRANSLUCENT_UNLIT.index('    float Opacity = saturate(P_Opacity);')] + r'''
#else
    // (no fog in the water pass)
    float Fog = 1.0;
    float3 FogColor = float3(0.0, 0.0, 0.0);
#endif
    float3 SpecT = SpecIBL * SpecOcc + (DirSpec + LocSpec);
    float3 DiffT = DirDiff + LocDiff;
    float F0b = dot(float3(F0a, F0a, F0a), float3(0.33333334, 0.33333334, 0.33333334));
    float2 ABc = FwdEnvAB(FRough, NoVc);
    float Ec = saturate(F0b * ABc.x + ABc.y * saturate(F0b * 50.0));
    float Att2 = (1.0 - Ec) * (1.0 - Ec);
    Att2 = Att2 - Metallic * Att2;
    float4 E;
#if STATIC_SWITCH_TEAR
    // a tear: only the specular, the emissive through it, by the visibility (the colour by its 8th power)
    float Vis = P_PixelContextVector1.x;
    float Vis8 = Vis * Vis;
    Vis8 *= Vis8;
    Vis8 *= Vis8;
    float T = (1.0 - Opacity) * (1.0 - F0a);
    float3 C = SpecT * Vis + Emissive * T * Vis8;
    E = float4(C * Fog + FogColor * (1.0 - T) * Vis, Vis * (1.0 - T));
#elif STATIC_SWITCH_THIN
    // a thin surface: the light through it (the volume's and the ambient from behind) blended with the light on it by
    // its thickness (PixelContextVector0); opaque
    float Th = P_PixelContextVector0.x;
    float3 VolDiff = Diffuse * VolSH * (1.0 - EnvVa);
    float3 D1 = lerp(VolDiff * MB, DiffT, Th);
    float3 D2 = lerp(AmbB, AmbN, Th) * (Diffuse * FlagScale) * (1.0 - EnvVa);
    float3 C = SpecT + (D2 * MB + D1) + Emissive * Att2;
    E = float4(C * Fog + FogColor, 1.0);
#elif STATIC_SWITCH_JEWEL || STATIC_SWITCH_WATER
    // a jewel, or water: the scene behind it (its extra scene colour) seen through it, refracted (a jewel's index 1.925,
    // water's 1.333) and limited to its thickness, absorbed along the way by its colour (the extinction, the
    // transparency distance) and lit inside by the ambient; the reflection from the screen (a short ray march of the
    // scene's depth) over the captures'
    float4 Vol = P_PixelContextVector0;
#if STATIC_SWITCH_WATER
    float3 Tdir = normalize((NoV * N - V) * asfloat(0x3f40001fu) - N * sqrt(1.0 - (1.0 - NoV * NoV) * asfloat(0x3f10002fu)));
#else
    float Thick = max(Vol.z, 0.01);
    float3 Tdir = normalize((NoV * N - V) * asfloat(0x3f04fcadu) - N * sqrt(1.0 - (1.0 - NoV * NoV) * asfloat(0x3e8a2b18u)));
#endif
    float2 SUV = SvPosition.xy * View[126].zw;
    float D0 = SceneDepthLinear(ExtraSceneDepthTexture.SampleLevel(ExtraSceneDepthSampler, SUV, 0.0).x);
#if STATIC_SWITCH_WATER && !STATIC_SWITCH_WATER_THICKNESS
    // (water as deep as the scene behind it)
    float L0 = D0 - SvPosition.w;
    float Exit0 = D0;
#elif STATIC_SWITCH_WATER
    float L0 = min(D0 - SvPosition.w, Vol.z);
    float Exit0 = SvPosition.w + L0;
#else
    float L0 = min(Thick, D0 - SvPosition.w);
    float Exit0 = SvPosition.w + L0;
#endif
    L0 = max(L0, 0.0);
    float3 TV = Tdir.y * View[9].xyz + Tdir.x * View[8].xyz + Tdir.z * View[10].xyz;
    float2 Off = normalize(TV).xy * min(L0 * 0.05, 1.0) * 10.0;
    float Wc = max(SvPosition.w, 100.0);
    float2 RUV = Off * ((1.0 / float2(Wc * View[28].x, Wc * View[29].y)) * View[58].xy) + SUV;
    RUV = (RUV * View[126].xy - View[121].xy) * View[122].zw;
    RUV = RUV * 2.0 - 1.0;
    RUV = RUV - 2.0 * sign(RUV) * max(abs(RUV) - 1.0, 0.0);
    RUV = RUV * 0.5 + 0.5;
    RUV = min(max(RUV * View[122].xy, 0.5), View[122].xy - 0.5);
    RUV = (RUV + View[121].xy) * View[126].zw;
    float D1 = SceneDepthLinear(ExtraSceneDepthTexture.SampleLevel(ExtraSceneDepthSampler, RUV, 0.0).x);
#if STATIC_SWITCH_WATER && !STATIC_SWITCH_WATER_THICKNESS
    float Exit1 = D1;
#elif STATIC_SWITCH_WATER
    float Exit1 = SvPosition.w + min(D1 - SvPosition.w, Vol.z);
#else
    float Exit1 = SvPosition.w + min(Thick, D1 - SvPosition.w);
#endif
    bool Ok = SvPosition.w <= Exit1;
    float2 UVc = Ok ? RUV : SUV;
    float Lr = (Ok ? Exit1 : Exit0) - SvPosition.w;
    float Lp = saturate(Lr * 0.05) * (max(Lr, 0.0) - L0) + L0;
    float3 SC0 = min(ExtraSceneColorTexture.SampleLevel(ExtraSceneColorSampler, UVc, 0.0).xyz, 65504.0) * View[128].y;
#if STATIC_SWITCH_WATER_ENVIRONMENT
    // (the water pass has the one scene colour)
    float3 SCol = SC0;
#else
    float3 SC1 = ExtraSceneColor2Texture.SampleLevel(ExtraSceneColor2Sampler, UVc, 0.0).xyz * View[128].y;
    float3 SCol = lerp(SC0, SC1, saturate((SvPosition.w + Lp) * (1.0 / max(D1, 0.0001))));
#endif
    float Ext = max(Vol.x, 0.01);
    float3 Med = (1.0 - Ext) * BaseColor;
    float Pw = (1.0 / max(Vol.y, 0.0001)) * Lp;
    float3 AbsC = float3(Med.x < 0.000001 ? 0.0 : pow(abs(Med.x), Pw), Med.y < 0.000001 ? 0.0 : pow(abs(Med.y), Pw),
                         Med.z < 0.000001 ? 0.0 : pow(abs(Med.z), Pw));
    float3 Trans = SCol * AbsC;
    float3 Sca = BaseColor * Ext * max(1.0 - dot(AbsC, float3(0.2126, 0.7152, 0.0722)), 0.0);
    float3 Scatter = VolA * Sca + Sca * A0b * FlagScale;
#if STATIC_SWITCH_WATER
    // water: its own reflectance's share of the light through it; the shallow water's fade to the scene behind it (none
    // with WaterEdge); the foam's share of the surface (PixelContextVector0.w), lit by the ambient
    float EnvVaW = saturate(F0s * ABv.x + ABv.y * saturate(F0s * 50.0));
    float AttW = (1.0 - EnvVaW) * (1.0 - EnvVaW);
    float3 AmbF = (VolA + A0b * FlagScale) * 0.6;
    float FormV = Vol.w;
#if STATIC_SWITCH_WATER_EDGE
    float EdgeW = 1.0;
#else
    float EdgeS = saturate(Lp * 0.05);
    float EdgeW = EdgeS * EdgeS * (3.0 - 2.0 * EdgeS);
#endif
#else
    float AttJ = 1.0 - saturate(F0b * ABv.x + ABv.y * saturate(F0b * 50.0));
    AttJ *= AttJ;
#endif
    // the screen-space reflection
    float4 C0 = TWP.y * View[1] + (TWP.x * View[0] + (TWP.z * View[2] + View[3]));
    float3 Rd = SvPosition.w * Rv;
    float4 C1 = C0 + (Rd.y * View[1] + (Rd.x * View[0] + Rd.z * View[2]));
    float3 C2 = (10.0 / max(A1s, 0.00001)) * View[24].xyw + C0.xyw;
    float2 C3 = SvPosition.w * View[26].zw + C0.zw;
    float3 N0 = C0.xyz / C0.w;
    float3 Dl = C1.xyz / C1.w - N0;
    float2 D2 = C2.xy / C2.z - N0.xy;
    float Zt = C3.x / C3.y;
    float Len = sqrt(dot(Dl.xy, Dl.xy));
    float Hl = Len * 0.5;
    float2 Q = max(abs(N0.xy * Hl + Dl.xy) - Len * 0.5, 0.0);
    Q = (abs(Dl.xy) - Q) / abs(Dl.xy);
    Dl = Dl * min(Q.y, Q.x) / Hl;
    uint Steps = min(max((uint)ceil(min(sqrt(dot(D2, D2)) * (1.0 / max(sqrt(dot(Dl.xy, Dl.xy)), 0.0001)), 1.0) * 8.0 + NoiseW.x), 1u), 8u);
    float2 UVs = (N0.xy * float2(0.5, -0.5) + 0.5) * Globals[35].xy;
    float3 Dlt = float3(Dl.xy * Globals[35].xy, Dl.z) * float3(0.0625, -0.0625, 0.125);
    float Zr = max(N0.z - Zt, abs(Dl.z));
    float Thr = Zr * 0.125;
    float2 DS;
    SSRDepthTexture.GetDimensions(DS.x, DS.y);
    float4 Hit = float4(0.0, 0.0, 0.0, 0.0);
    float PrevZ = 0.0;
    for (uint si = 0; si < Steps; si++)
    {
        float t = float(si) + NoiseW.x;
        float3 P = Dlt * t + float3(UVs, N0.z);
        float2 Px = min(max(DS * P.xy, 0.0), DS - 1.0);
        float Dz = P.z - SSRDepthTexture.Load(int3((uint2)Px, 0)).x;
        if (abs(-Zr * 0.125 - Dz) < Thr)
        {
            float Pz = si != 0u ? PrevZ : (-Dl.z * 0.125 + Dz);
            float Tt = (t - 1.0) + saturate(Pz / (Pz - Dz));
            Hit.xyz = Dlt * abs(Tt) + float3(UVs, N0.z);
            float a = min(abs(Tt) * 0.125, 1.0);
            Hit.w = 1.0 - a * a;
            break;
        }
        PrevZ = Dz;
    }
    if (0.0 < Hit.w)
    {
        float2 HN = Hit.xy * Globals[35].zw * float2(2.0, -2.0) + float2(-1.0, 1.0);
        // the hit's colour, near (HCa) to far (HCb) from the surface; HE: where on the screen the edge fade measures it
        float3 HCa, HCb;
        float2 HE = HN;
#if STATIC_SWITCH_WATER_ENVIRONMENT
        if (View[140].y == 0.0)
        {
            // the water pass: the previous frame's two scene colours where the hit was then (within the view)
            float3 PC = HN.y * View[115].xyw;
            PC = HN.x * View[114].xyw + PC;
            PC = Hit.z * View[116].xyw + PC;
            PC = PC + View[117].xyw;
            HE = PC.xy / PC.z;
            int2 PP = (int2)((HE * View[123].xy + View[123].wz) * View[126].xy + 0.5);
            PP = min((int2)(View[124].xy + View[125].xy - 1.0), max(PP, (int2)View[124].xy));
            HCb = min(PrevSceneColorTexture.Load(int3(PP, 0)).xyz, 65504.0) * Globals[37].y;
            HCa = min(PrevSceneColor2Texture.Load(int3(PP, 0)).xyz, 65504.0) * Globals[37].y;
        }
        else
        {
            // (otherwise this frame's scene colour, and far off the reflection captures')
            float2 BUV = HN * View[58].xy + View[58].wz;
            HCa = min(ExtraSceneColorTexture.SampleLevel(ExtraSceneColorSampler, BUV, 0.0).xyz, 65504.0) * View[128].y;
            HCb = SpecIBLu;
        }
#else
        float2 BUV = HN * View[58].xy + View[58].wz;
        HCb = min(ExtraSceneColorTexture.SampleLevel(ExtraSceneColorSampler, BUV, 0.0).xyz, 65504.0) * View[128].y;
        HCa = ExtraSceneColor2Texture.SampleLevel(ExtraSceneColor2Sampler, BUV, 0.0).xyz * View[128].y;
#endif
        float Dh = SceneDepthLinear(Hit.z);
        float2 HP = Dh * HN;
        float3 HW = HP.y * View[45].xyz + (HP.x * View[44].xyz + (Dh * View[46].xyz + View[47].xyz));
        float Fd = min(sqrt(dot(HW - TWP, HW - TWP)) * (1.0 / max(sqrt(dot(HW, HW)), 0.0001)), 1.0);
        float4 HC = float4(lerp(HCa, HCb, Fd), 1.0) * Hit.w;
        float2 PixN = ((SvPosition.xy - View[121].xy) * View[122].zw - 0.5) * float2(2.0, -2.0);
        float2 Ed = saturate(abs((HE - PixN) * 0.5) * 5.0 - 4.0);
        HC *= max(1.0 - dot(Ed, Ed), 0.0);
        SpecIBL = SpecIBL * (1.0 - HC.w * View[129].x) + HC.xyz * View[129].x;
    }
#if STATIC_SWITCH_WATER
    // water: the scene behind it at the shallow edge, the light through it elsewhere (less the foam's share); its
    // reflections (less the foam's), the foam, its lights' highlights; opaque
    float3 TW = Trans * AttW * (1.0 - FormV) * EdgeW;
    TW = SCol * (1.0 - EdgeW) + TW;
    TW = (Scatter * AttW * (1.0 - FormV) * EdgeW) * MB + TW;
    float3 SW = SpecIBL * EnvVaW * (1.0 - FormV);
    SW = SW * EdgeW + (1.0 - EnvVaW) * AmbF * FormV * EdgeW * MB;
    SW = SW + (DirSpec + LocSpec);
    float3 C = Emissive * Att2 + SW;
    C = TW + C;
#if STATIC_SWITCH_WATER_ENVIRONMENT
    // (the water pass leaves the fog to the scene)
    E = float4(C, 1.0);
#else
    E = float4(C * Fog + FogColor, 1.0);
#endif
#else
    SpecT = SpecIBL * EnvVa * SpecOcc + (DirSpec + LocSpec);
    float3 C = SpecT + Emissive * Att2 + (Trans * AttJ + Scatter * AttJ * MB);
    E = float4(C * Fog + FogColor, 1.0);
#endif
#else
    // glass: the diffuse premultiplied by the opacity, the emissive through both faces of the surface
    float Alpha = 1.0 - Att2 * (1.0 - Opacity);
    float3 C = SpecT + DiffT * Opacity + Emissive * Att2;
    E = float4(C * Fog + FogColor * Alpha, Alpha);
#endif
    if (0.0 < View[140].z) E = float4(Debug, dot(Debug, float3(0.2126, 0.7152, 0.0722)));
    if (0.0 < View[136].x)
    {
        float3 D = WP - Prim[8].xyz;
        float3 Ext = Prim[9].xyz + 1.0;
        bool Outside = any(Ext < abs(D));
        float H = frac(dot(WP, float3(0.57735026, 0.57735026, 0.57735026)) * 0.002);
        float3 C = (0.5 < H) ? float3(0.0, 1.0, 1.0) : float3(1.0, 1.0, 0.0);
        if (Outside) E = float4(C, dot(C, float3(0.2126, 0.7152, 0.0722)));
    }
    o0 = float4(E.xyz * View[128].x, E.w);
    o5 = float4(0.0, 0.0, 0.0, 0.0);
'''
BASE_PASS = {'MSM_DefaultLit': BASE_PASS_DEFAULT_LIT, 'MSM_PreintegratedSkin': BASE_PASS_SKIN, 'Unknown': BASE_PASS_HAIR,
             'MSM_Eye': BASE_PASS_EYE, 'MSM_Unlit': BASE_PASS_UNLIT, 'MSM_Cloth': BASE_PASS_CLOTH,
             'MSM_SubsurfaceProfile': BASE_PASS_SUBSURFACE, 'Translucent_MSM_Unlit': BASE_PASS_TRANSLUCENT_UNLIT,
             'Translucent_MSM_DefaultLit': BASE_PASS_TRANSLUCENT_LIT, 'Forward_MSM_DefaultLit': BASE_PASS_FORWARD}

# the game's 4.18 depth-only pass (the coverage clip, against the blue noise and the LOD fade)
DEPTH_PROLOGUE = r'''
    int Ctx = (int)floor(VertexContext + 0.5);
    uint NZ = (uint)Ctx + (asuint(View[139].z) << 3);
    float4 NS = Noise3D.Load(int4(int(SvPosition.x) & 63, int(SvPosition.y) & 63, NZ & 63u, 0));
    float3 Noise = NS.xyz;
'''
DEPTH_PASS = r'''
    float2 Nz = float2(NoiseW.w, NoiseW.x) * 0.99609375 + 0.001953125;
    if (!((Nz.y < P_OpacityMask) && (Nz.x < Globals[2].x))) discard;
    o0 = float4(0.0, 0.0, 0.0, 0.0);
'''

# the game's 4.18 distortion pass (its directional one, EndMaterial_Directional's): the screen offset from where the
# vertex shader put the surface to where it moved it, by the material's intensity (PixelIndependentVector0)
DISTORTION_PASS = r'''
    float2 Destination = DestinationClip.xy / DestinationClip.w;
    float2 Source = SourceClip.xy / SourceClip.w;
    o0 = float4(P_PixelIndependentVector0.x * (Destination - Source), 0.0, 0.0);
'''

# the pixel shaders each check reads: (pass, vertex factory suffix) -> the shader's key
SHADER_KEYS = {'base': remake_ue.BASE_PS, 'coverage': remake_ue.DEPTH_PS, 'distortion': 'TDistortionMeshPS_FDistortMeshAccumulatePolicy_'}

SEM = {('TEXCOORD', '0'): ['float2 UV0 = IN.xy;', 'float2 UV1 = IN.zw;'],
       ('TEXCOORD', '1'): ['float2 UV2 = IN.xy;', 'float2 UV3 = IN.zw;'],
       ('TEXCOORD', '6'): ['float3 T2W0 = IN.xyz;'],
       ('TEXCOORD', '7'): ['float4 T2W2 = IN;'],
       ('VertexContextVector', '0'): ['float VertexContext = IN.w;'],
       ('PixelPosition', '0'): ['float4 PixelPosition = IN;'],
       # (with PreSkinnedNormal: the vertex's unskinned tangent frame, in the mesh's space)
       ('PreSkinnedMatrix', '0'): ['float3 PreSkinnedTangentX = IN.xyz;'], ('PreSkinnedMatrix', '2'): ['float4 PreSkinnedTangentZ = IN;'],
       ('VertexFog', '0'): ['float4 VertexFog = IN;'],
       # (the distortion pass: the surface's clip position and where the vertex shader moved it)
       ('SourceClipPosition', '0'): ['float4 SourceClip = IN;'], ('DestinationClipPosition', '0'): ['float4 DestinationClip = IN;']}
# the game's sprite particle vertex factory's interpolants: the texture coordinate, the sub-image coordinates, the dynamic
# parameter, the particle's colour and its position and size, the tangent frame
SEM_SPRITE = dict(SEM)
SEM_SPRITE.update({('TEXCOORD', '0'): ['float2 UV0 = IN.xy;'],
                   ('TEXCOORD', '2'): ['Parameters.Particle.SubUVCoords[0] = IN.xy;', 'Parameters.Particle.SubUVCoords[1] = IN.zw;'],
                   ('TEXCOORD', '3'): ['Parameters.Particle.DynamicParameter = IN;'],
                   ('TEXCOORD', '5'): ['Parameters.Particle.Color = IN;'],
                   ('TEXCOORD', '6'): ['Parameters.Particle.TranslatedWorldPositionAndSize = IN;'],
                   ('TEXCOORD', '8'): ['LightingPositionOffset = IN.xyz;'],
                   ('TEXCOORD', '10'): ['float3 T2W0 = IN.xyz;', 'Parameters.Particle.SubUVLerp = IN.w;'],
                   ('TEXCOORD', '11'): ['float4 T2W2 = IN;']})
SEM_BY_VF = {'': SEM, '__Sprite': SEM_SPRITE}


def translucency_volumes(asm, view_cb):
    """the lit translucent pass's lighting volume registers: the texture3d samples at the inner cascade's coordinate
    (View[145]-scaled) and the outer's (View[146]), each the ambient first, then the directional; their sampler"""
    if view_cb < 0:
        return {}
    lines = [l.strip() for l in asm.splitlines() if not l.startswith('//')]
    out, inner, outer = {}, None, None
    for l in lines:
        m = re.match(r'mul (r\d+)\.[xyzw]{3}, r\d+\.[xyzw]{4}, cb%d\[(145|146)\]\.[xyzw]{4}' % view_cb, l)
        if m:
            if m.group(2) == '145':
                inner = m.group(1)
            else:
                outer = m.group(1)
            continue
        m = re.match(r'sample_l_indexable\(texture3d\)\([^)]*\) r\d+\.\w+, (r\d+)\.\w+, t(\d+)\.\w+, s(\d+)', l)
        if m and m.group(1) in (inner, outer):
            which = 'Inner' if m.group(1) == inner else 'Outer'
            nm = ('Ambient' if 'Ambient%sVolume' % which not in out else 'Directional') + which + 'Volume'
            if nm not in out:
                out[nm] = int(m.group(2))
                out['sampler'] = int(m.group(3))
        # (a coordinate register written again is no longer the cascade's coordinate)
        d = re.match(r'\w+ (r\d+)\.', l)
        if d and d.group(1) in (inner, outer):
            if d.group(1) == inner:
                inner = None
            else:
                outer = None
    return out


def shader_key(kind):
    """a check's kind (its pass, '__<vertex factory>' after it for another vertex factory's) -> the shader's key"""
    p, _, vf = kind.partition('__')
    return SHADER_KEYS[p] + ('__' + vf if vf else '')
BUFFER_NAMES = {'View': 'View', 'Primitive': 'Prim', 'PrecomputedLightingBuffer': 'PLB', 'Material': 'MatUB', '': 'Globals',
                'ForwardGlobalLightData': 'FLD', 'ReflectionCapture': 'RCU'}
RAW_SLOT = 9


# the pixel normal in world space (Parameters.WorldNormal) as the game's base pass makes it from the material's normal
WORLD_NORMAL = '''float3 WorldNormalOf(float3 MaterialNormal, float3 T0, float3 T1, float3 T2)
{
    float3 MN = MaterialNormal * View[134].w + View[134].xyz;
#if STATIC_SWITCH_TRANSFORMED_NORMAL
    return normalize(MN);
#else
    MN = normalize(MN);
    return normalize(MN.x * T0 + MN.y * T1 + MN.z * T2);
#endif
}'''

# the hooks both checkers give the graph: the primitive's position, the material's shared samplers
SHARED_HOOKS = {'ObjectPositionWS': 'GetPrimitiveData(0u).ObjectWorldPositionAndRadius.xyz',
                'Wrap_WorldGroupSettings': 'WrapWorldGroupSampler', 'Clamp_WorldGroupSettings': 'ClampWorldGroupSampler'}


def shared_decls(shared, have_prim):
    """the shared samplers (at the registers the game's shader has them, if it does) and the 4.26 primitive data accessor
    the graph's Custom nodes use (from the game's Primitive buffer)"""
    out = []
    for k in ('Wrap', 'Clamp'):
        out.append('SamplerState %sWorldGroupSampler%s;' % (k, ' : register(s%d)' % shared[k] if k in shared else ''))
    out.append('struct FPrimitiveSceneData { float4x4 LocalToWorld; float4x4 WorldToLocal; float4 ObjectWorldPositionAndRadius; };')
    if have_prim:
        out.append('FPrimitiveSceneData GetPrimitiveData(uint Id) { FPrimitiveSceneData D; '
                   'D.LocalToWorld = float4x4(Prim[0], Prim[1], Prim[2], Prim[3]); D.WorldToLocal = float4x4(Prim[4], Prim[5], Prim[6], Prim[7]); '
                   'D.ObjectWorldPositionAndRadius = Prim[8]; return D; }')
    else:
        out.append('FPrimitiveSceneData GetPrimitiveData(uint Id) { return (FPrimitiveSceneData)0; }')
    return out


def raw_layout(uset, material):
    """a slot (float4) for each scalar and vector parameter the permutation can read (the game's uniform expressions'
    and the graph's), SelectionColor first"""
    names = ['SelectionColor']

    def walk(e):
        if isinstance(e, dict):
            if e.get('op') in ('vparam', 'sparam') and e['name'] not in names:
                names.append(e['name'])
            if e.get('op') == 'texprop' and 'TEXSIZE:' + e['texture']['name'] not in names:
                names.append('TEXSIZE:' + e['texture']['name'])
            for v in e.values():
                walk(v)
        elif isinstance(e, list):
            for v in e:
                walk(v)
    walk(uset['vectors'])
    walk(uset['scalars'])
    return names


def vector_params(uset):
    """the names of the vector parameters the permutation's uniform expressions read (read as float4s)"""
    out = set()

    def walk(e):
        if isinstance(e, dict):
            if e.get('op') == 'vparam':
                out.add(e['name'])
            for v in e.values():
                walk(v)
        elif isinstance(e, list):
            for v in e:
                walk(v)
    walk(uset['vectors'])
    walk(uset['scalars'])
    return out


def texture_sizes(uset):
    """a made-up size for each texture whose size the game's uniform expressions read (by the texture's index): never
    wider than tall (the classify texture's rows are its height in widths)"""
    out = {}

    def walk(e):
        if isinstance(e, dict):
            if e.get('op') == 'texprop':
                t = e['texture'].get('index', 0)
                w = 16 << (t % 2)
                out[e['texture']['name']] = (float(w), float(w << (t % 3)))
            for v in e.values():
                walk(v)
        elif isinstance(e, list):
            for v in e:
                walk(v)
    walk(uset['vectors'])
    walk(uset['scalars'])
    return out


def shader_source(perm, kind, material):
    """the checker's HLSL for one permutation: the original's signature, buffers and registers; the rebuilt graph's
    material code; the transcribed pass"""
    key = shader_key(kind)
    pass_, _, vf = kind.partition('__')
    sem = SEM_BY_VF['__' + vf if vf else '']
    asm = open(os.path.join(DIS, perm, key + '.asm'), encoding='latin-1').read()
    bind = json.load(open(os.path.join(DIS, perm, 'bindings.json')))[key]
    uset = remake_ue.uniform_sets()[perm]
    info = remake_ue.parse_debug(uset['debug'])
    L = dxbc2hlsl.Lifter(asm)
    out = [HELPERS]
    cbnames = bind['cb']
    for b, n in sorted(L.cbs.items()):
        nm = BUFFER_NAMES.get(cbnames[b] if b < len(cbnames) else '', 'CB%d' % b)
        # the View buffer as far as the game's values the graph may name (an unused branch still has to compile)
        out.append('cbuffer CB%d : register(b%d) { float4 %s[%d]; };' % (b, b, nm, max(n, 160) if nm == 'View' else n))
    if 'Globals' not in ''.join(out):
        out.append('static const float4 Globals[3] = { float4(0, 0, 0, 0), float4(0, 0, 0, 0), float4(1, 1, 1, 1) };')
    raw = raw_layout(uset, material)
    out.append('cbuffer CBRaw : register(b%d) { float4 Raw[%d]; };' % (RAW_SLOT, max(1, len(raw))))
    textures = list(uset['textures2d']) + list(uset['texturescube'])
    tex_regs, smp_regs = {}, {}
    for t, (ub, res) in bind['t'].items():
        if ub == 'Material' and res // 2 < len(textures):
            tex_regs[textures[res // 2]['name']] = int(t)
        elif ub == 'View' and res == 29:
            tex_regs['__noise__'] = int(t)
    shared = {}
    for s, (ub, res) in bind['s'].items():
        # the material's samplers: each texture's after it (2k + 1), then the shared wrap and clamp ones
        if ub == 'Material' and res % 2 == 1 and (res - 1) // 2 < len(textures):
            smp_regs[textures[(res - 1) // 2]['name']] = int(s)
        elif ub == 'Material' and res in (2 * len(textures), 2 * len(textures) + 1):
            shared['Wrap' if res == 2 * len(textures) else 'Clamp'] = int(s)
    texmap = {}
    for k, tp in enumerate(textures):
        nm = tp['name']
        if nm in tex_regs:
            ident = 'MT%d' % k
            cube = k >= len(uset['textures2d'])
            out.append('%s %s : register(t%d);' % ('TextureCube' if cube else 'Texture2D', ident, tex_regs[nm]))
            sreg = smp_regs.get(nm)
            if sreg is None:
                out.append('SamplerState %sSampler;' % ident)
            else:
                out.append('SamplerState %sSampler : register(s%d);' % (ident, sreg))
            texmap[nm] = (ident, ident + 'Sampler')
    if '__noise__' in tex_regs:
        out.append('Texture3D Noise3D : register(t%d);' % tex_regs['__noise__'])
    else:
        out.append('Texture3D Noise3D;')
    out.extend(shared_decls(shared, any(l.startswith('cbuffer') and ' Prim[' in l for l in out)))
    view_t = {res: int(t) for t, (ub, res) in bind['t'].items() if ub == 'View'}
    view_s = {res: int(s_) for s_, (ub, res) in bind['s'].items() if ub == 'View'}
    # the translucency lighting volumes (the 3D textures sampled at the inner and outer cascades' coordinates: the
    # ambient, then the directional) and the reflection capture array
    lit_vol = translucency_volumes(asm, cbnames.index('View') if 'View' in cbnames else -1)
    for nm in ('AmbientInnerVolume', 'AmbientOuterVolume', 'DirectionalInnerVolume', 'DirectionalOuterVolume'):
        out.append('Texture3D %s%s;' % (nm, ' : register(t%d)' % lit_vol[nm] if nm in lit_vol else ''))
    out.append('SamplerState TranslucencyVolumeSampler%s;' % (' : register(s%d)' % lit_vol['sampler'] if 'sampler' in lit_vol else ''))
    m = re.search(r'sample\w*\(texturecubearray\)\([^)]*\) [^,]+, [^,]+, t(\d+)\.\w+, s(\d+)', asm)
    out.append('TextureCubeArray ReflectionCaptures%s;' % (' : register(t%s)' % m.group(1) if m else ''))
    out.append('SamplerState ReflectionCaptureSampler%s;' % (' : register(s%s)' % m.group(2) if m else ''))
    # the forward pass's ambient cube: the 3D textures it samples at the origin (its average, its +axes', its -axes')
    amb = re.findall(r'sample_l_indexable\(texture3d\)\([^)]*\) r\d+\.\w+, l\(0x00000000, 0x00000000, 0x00000000, 0x00000000\), t(\d+)\.\w+, s(\d+)', asm)
    for nm, (t, smp) in zip(('AmbientCube0', 'AmbientCubeP', 'AmbientCubeN'), amb):
        out.append('Texture3D %s : register(t%s);' % (nm, t))
    for nm in ('AmbientCube0', 'AmbientCubeP', 'AmbientCubeN')[len(amb):]:
        out.append('Texture3D %s;' % nm)
    amb_t = {int(t) for t, _ in amb}
    # the volumetric fog (a 3D texture of the shader's that is none of the View's noise volumes, nor a lighting volume)
    vol = [int(t) for t in re.findall(r'dcl_resource_texture3d \(float,float,float,float\) t(\d+)', asm)
           if bind['t'].get(t, ['', 0])[0] != 'View' and int(t) not in lit_vol.values() and int(t) not in amb_t]
    if vol:
        m = re.search(r'sample\w*\(texture3d\)\([^)]*\) [^,]+, [^,]+, t%d\.\w+, s(\d+)' % vol[0], asm)
        out.append('Texture3D VolumetricFog : register(t%d);' % vol[0])
        out.append('SamplerState VolumetricFogSampler%s;' % (' : register(s%s)' % m.group(1) if m else ''))
    else:
        out.append('Texture3D VolumetricFog;')
        out.append('SamplerState VolumetricFogSampler;')
    # the height fog's inscattering cubemap (a cube texture of the shader's that is no one's else)
    cubes = [int(t) for t in re.findall(r'dcl_resource_texturecube \(float,float,float,float\) t(\d+)', asm)
             if bind['t'].get(t, ['', 0])[0] not in ('View', 'Material')]
    if cubes:
        m = re.search(r'sample\w*\(texturecube\)\([^)]*\) [^,]+, [^,]+, t%d\.\w+, s(\d+)' % cubes[0], asm)
        out.append('TextureCube FogCube : register(t%d);' % cubes[0])
        out.append('SamplerState FogCubeSampler%s;' % (' : register(s%s)' % m.group(1) if m else ''))
    else:
        out.append('TextureCube FogCube;')
        out.append('SamplerState FogCubeSampler;')
    out.append('SamplerState Noise3DSampler;')
    out.append('Texture3D VolumeNoise3D%s;' % (' : register(t%d)' % view_t[30] if 30 in view_t else ''))
    out.append('SamplerState VolumeNoise3DSampler%s;' % (' : register(s%d)' % view_s[27] if 27 in view_s else ''))
    # the forward-lit pass (the light grid's buffers): the grid, the culled lists, the local lights' data; the shadow atlas;
    # the lights' IES profiles (the 2D texture declared last before the buffers) and their row of the global buffer
    forward = 'dcl_resource_buffer' in asm
    fwd_t = set()
    fwd_defs = {}
    if forward:
        bufs = re.findall(r'dcl_resource_buffer \(uint,uint,uint,uint\) t(\d+)', asm)
        # (the environment's water, drawn in the water pass, has the grid's lists for its reflection captures only: no
        # local lights, no shadows)
        for i, (ty, nm) in enumerate((('Buffer<uint>', 'NumCulledLightsGrid'), ('Buffer<uint>', 'CulledLightDataGrid'),
                                      ('Buffer<uint4>', 'ForwardLocalLightBuffer'))):
            out.append('%s %s%s;' % (ty, nm, ' : register(t%s)' % bufs[i] if i < len(bufs) else ''))
        m = re.search(r'dcl_resource_texture2darray \(float,float,float,float\) t(\d+)', asm)
        sh_t = m.group(1) if m else None
        m = sh_t and re.search(r'sample\w*\(texture2darray\)\([^)]*\) [^,]+, [^,]+, t%s\.\w+, s(\d+)' % sh_t, asm)
        out.append('Texture2DArray ShadowAtlas%s;' % (' : register(t%s)' % sh_t if sh_t else ''))
        out.append('SamplerState ShadowSampler%s;' % (' : register(s%s)' % m.group(1) if m else ''))
        decls = re.findall(r'dcl_resource_(\w+) \([^)]*\) t(\d+)', asm)
        first_buf = next(i for i, (ty, t) in enumerate(decls) if ty == 'buffer')
        ies_t = next(t for ty, t in reversed(decls[:first_buf]) if ty == 'texture2d') if len(bufs) > 2 else None
        m = ies_t and re.search(r'mul r\d+\.\w, r\d+\.\w, cb(\d+)\[(\d+)\]\.w\s*\n\s*sample_l_indexable\(texture2d\)\([^)]*\) [^,]+, [^,]+, t%s\.\w+, s(\d+)'
                                % ies_t, asm)
        out.append('Texture2D IESAtlas%s;' % (' : register(t%s)' % ies_t if ies_t else ''))
        out.append('SamplerState IESSampler%s;' % (' : register(s%s)' % m.group(3) if m else ''))
        fwd_defs['FWD_IES_ROW'] = m.group(2) if m else '0'
        fwd_t |= {int(t) for t in (sh_t, ies_t) if t} | {int(b) for b in bufs}
        # the jewel's and the water's scene behind: the extra scene depth (linearized right after its sample), the
        # extra scene colour (limited to 65504 right after), the second colour (the other one sampled), the depth the
        # screen-space reflection loads
        vc = cbnames.index('View') if 'View' in cbnames else 1
        fwd_extra = {}
        m = re.search(r'sample_l_indexable\(texture2d\)\([^)]*\) (r\d+)\.(\w), [^,]+, t(\d+)\.\w+, s(\d+), l\(0x00000000\)\s*\n\s*mad r\d+\.\w, \1\.\2, cb%d\[57\]\.x' % vc, asm)
        if m:
            fwd_extra['depth'] = (m.group(3), m.group(4))
        m = re.search(r'sample_l_indexable\(texture2d\)\([^)]*\) (r\d+)\.\w+, [^,]+, t(\d+)\.\w+, s(\d+), l\(0x00000000\)\s*\n\s*min \1\.\w+, \1\.\w+, l\(0x477fe000', asm)
        if m:
            fwd_extra['color'] = (m.group(2), m.group(3))
        m = re.search(r'resinfo_indexable\(texture2d\)\([^)]*\) [^,]+, l\(0x00000000\), t(\d+)', asm)
        if m:
            fwd_extra['ssr'] = (m.group(1), None)
        used = {int(v[0]) for v in fwd_extra.values()} | set(tex_regs.values()) | fwd_t
        for t, smp in re.findall(r'sample_l_indexable\(texture2d\)\([^)]*\) [^,]+, [^,]+, t(\d+)\.\w+, s(\d+)', asm):
            if int(t) not in used and 'color' in fwd_extra:
                fwd_extra['color2'] = (t, smp)
                break
        # the water pass's previous frame's scene colours (the textures it loads besides the reflection's depth)
        loads = []
        for t in re.findall(r'ld_indexable\(texture2d\)\([^)]*\) [^,]+, [^,]+, t(\d+)\.', asm):
            if t not in loads and t != fwd_extra.get('ssr', (None,))[0] and int(t) not in tex_regs.values():
                loads.append(t)
        for key, t in zip(('prev', 'prev2'), loads):
            fwd_extra[key] = (t, None)
        for key, nm in (('color', 'ExtraSceneColor'), ('color2', 'ExtraSceneColor2'), ('ssr', 'SSRDepth'),
                        ('prev', 'PrevSceneColor'), ('prev2', 'PrevSceneColor2')):
            t, smp = fwd_extra.get(key, (None, None))
            out.append('Texture2D %sTexture%s;' % (nm, ' : register(t%s)' % t if t else ''))
            if key in ('color', 'color2'):
                out.append('SamplerState %sSampler%s;' % (nm, ' : register(s%s)' % smp if smp else ''))
        fwd_t |= {int(v[0]) for v in fwd_extra.values()}
    # the game's extra scene depth (a 2D texture of the shader's that is none of the material's): its linear depth here
    declared = [int(m) for m in re.findall(r'dcl_resource_texture2d \(float,float,float,float\) t(\d+)', asm)]
    extra_t = [t for t in declared if t not in tex_regs.values() and t not in fwd_t]
    if forward and 'depth' in fwd_extra:
        out.append('Texture2D ExtraSceneDepthTexture : register(t%s);' % fwd_extra['depth'][0])
        out.append('SamplerState ExtraSceneDepthSampler : register(s%s);' % fwd_extra['depth'][1])
    elif extra_t and not forward:
        m = re.search(r'sample\w*\([^)]*\)\([^)]*\) [^,]+, [^,]+, t%d\.\w+, s(\d+)' % extra_t[0], asm)
        out.append('Texture2D ExtraSceneDepthTexture : register(t%d);' % extra_t[0])
        out.append('SamplerState ExtraSceneDepthSampler%s;' % (' : register(s%s)' % m.group(1) if m else ''))
    else:
        out.append('Texture2D ExtraSceneDepthTexture;')
        out.append('SamplerState ExtraSceneDepthSampler;')
    out.append('''float ExtraSceneDepthAt(float4 SvPosition)
{
    float Z = ExtraSceneDepthTexture.SampleLevel(ExtraSceneDepthSampler, SvPosition.xy * View[126].zw, 0.0).r;
    return Z * View[57].x + View[57].y + 1.0 / (Z * View[57].z - View[57].w);
}''')

    extra_decl = []

    class Missing(dict):
        # a texture the game's shader does not read (where its result is dead there, as an unlit material's normal):
        # declared without a register; if the rebuilt shader's output did depend on it, its made-up texture would differ
        def __missing__(self, k):
            ident = 'XT%d' % len(extra_decl)
            extra_decl.append('Texture2D %s; SamplerState %sSampler;' % (ident, ident))
            self[k] = (ident, ident + 'Sampler')
            return self[k]
    params = {n: ('Raw[%d]' % i if n != 'SelectionColor' else 'Raw[0]') for i, n in enumerate(raw)}
    params_scalar = {n: 'Raw[%d].x' % i for i, n in enumerate(raw)}

    class Params(dict):
        def __missing__(self, k):
            raise KeyError('parameter %s is not in the uniform set of %s' % (k, perm))
    pv = Params()
    vnames = vector_params(uset)
    for n, i in zip(raw, range(len(raw))):
        pv[n] = ('Raw[%d]' if n in vnames else 'Raw[%d].x') % i
    uvs = {0: 'UV0', 1: 'UV1', 2: 'UV2', 3: 'UV3'}
    # the game's base pass leaves the coverage to the depth-only pass (masking in the depth pass only)
    lite = ue_mat.definitions(material, info['switches']).get('STATIC_SWITCH_LITE_DECAL', False)
    # (a masked translucent material clips in its base pass too)
    masked_translucent = material.props.get('blend') == 'AlphaComposite' and bool(info['masked'])
    particle = bool(material.props.get('particle_visibility'))
    pins = {k: v for k, v in PINS.items()
            if (k == 'OpacityMask') == (pass_ == 'coverage') or (k == 'OpacityMask' and (lite or masked_translucent or particle))}
    if pass_ == 'distortion':
        pins = {k: PINS[k] for k in ('Normal', 'PixelIndependentVector0')}
    # (the pixel normal, which the other inputs may read, in every pass)
    pins.setdefault('Normal', PINS['Normal'])
    lines, res, tr = ue_mat.translate(material, info['switches'], Missing(texmap), pv, uvs, pins,
                                      extra={'TwoSidedSign': '1.0', 'CameraVectorWS': 'Parameters.CameraVector',
                                             # the game's own view values (its View buffer)
                                             'BakingMask': 'View[159].w', 'ConditionalEmissive': 'View[128].y',
                                             'BlueNoise': 'Noise', 'ExtraSceneDepth': 'ExtraSceneDepthAt(SvPosition)',
                                             'PixelDepth': 'SvPosition.w', 'ViewportUV': '((SvPosition.xy - View[121].xy) * View[122].zw)',
                                             'PixelNormalWS': 'Parameters.WorldNormal', 'VolumeNoise': ('VolumeNoise3D', 'VolumeNoise3DSampler'),
                                             'WorldPosition': '(TWP - View[62].xyz)', 'BlueNoiseVolume': ('Noise3D', 'Noise3DSampler'),
                                             'PreSkinnedTangentX': 'PreSkinnedTangentX', 'PreSkinnedTangentZ': 'PreSkinnedTangentZ',
                                             'NearPlane': 'View[138].x', 'PreViewTranslation': 'View[62].xyz', 'CameraPositionWS': 'View[59].xyz',
                                             **SHARED_HOOKS},
                                      after_normal='Parameters.WorldNormal = WorldNormalOf({normal}, T2W0, cross(T2W2.xyz, T2W0) * T2W2.w, T2W2.xyz);')
    # vector parameters read as float4
    for n in tr.used_params:
        pass
    for k, v in sorted(ue_mat.definitions(material, info['switches']).items()):
        out.append('#define %s %d' % (k, int(v)))
    out.append('#define TRANSLUCENT_FOG_PER_PIXEL %d' % int(material.props.get('fog') == 'pixel'))
    # (the particle's visibility and coverage, EndMaterial_Particle's; the height fog's values in the shader's global
    # buffer: four rows earlier in the sprite vertex factory's shaders)
    out.append('#define PARTICLE_VISIBILITY %d' % int(bool(material.props.get('particle_visibility'))))
    out.append('#define FOG_GLOBALS %d' % (32 if vf == 'Sprite' else 36))
    # (the lit translucent instances' lighting mode, the game's volumetric ones)
    tlm = json.load(open(os.path.join(ROOT, 'remake_inst.json'))).get(perm, {}).get('ovr', {}).get('TranslucencyLightingMode', '')
    for k in ('Average', 'Rough', 'Gloss', 'Refract', 'Scatter'):
        out.append('#define TLM_%s %d' % (k.upper(), int(tlm.endswith('TLM_Volumetric' + k))))
    out.append('#define TRANSLUCENT_VERTEX_FOG %d' % int(material.props.get('fog') == 'vertex'))
    out.append('#define MASKED_BASE_PASS %d' % int(masked_translucent))
    # (a distortion-only material's base pass - EndMaterial_Directional's: the game's draws nothing, not even the
    # editor's selection colour)
    out.append('#define BASE_PASS_DRAWS_NOTHING %d' % int(bool(material.props.get('base_pass_draws_nothing'))))
    if forward:
        fwd_defs.setdefault('FWD_AMBIENT', '0')
        fwd_defs.setdefault('FWD_IBL_NOV', 'NoVs')
        for k, v in sorted(fwd_defs.items()):
            out.append('#define %s %s' % (k, v))
        out.append(FORWARD_HELPERS)
    out.append(WORLD_NORMAL)
    out.extend(extra_decl)
    out.extend(tr.custom_funcs)
    params_sig = []
    decl = {x[0]: x for x in L.inputs}
    setup = []
    for r in L.input_sig:
        reg = int(r[3])
        sem_, idx, sysv = r[0], r[1], r[4]
        interp = decl[reg][2] if reg in decl else ''
        q = interp.replace('linear noperspective centroid', 'noperspective centroid').replace('linear noperspective', 'noperspective')
        q = q.replace('constant', 'nointerpolation').replace('linear centroid', 'centroid').replace('linear sample', 'sample')
        q = re.sub(r'^linear\b', '', q).strip()
        if sysv == 'POS':
            params_sig.append(('%s float4 in_v%d : SV_Position' % (q, reg)).strip())
            setup.append('float4 SvPosition = in_v%d;' % reg)
        elif sysv == 'FFACE':
            params_sig.append('bool in_v%d : SV_IsFrontFace' % reg)
        else:
            params_sig.append(('%s float4 in_v%d : %s%s' % (q, reg, sem_, idx)).strip())
            for s in sem.get((sem_, idx), []):
                setup.append(s.replace('IN', 'in_v%d' % reg))
    for r in L.output_sig:
        params_sig.append('out float4 o%s : SV_Target%s' % (r[3], r[1]))
    body = ['void main(%s)' % ',\n          '.join(params_sig), '{']
    for r in L.output_sig:
        body.append('    o%s = float4(0.0, 0.0, 0.0, 0.0);' % r[3])
    # (the local vertex factory's particle values: the engine's defaults, the colour white)
    body.append('    FMaterialPixelParameters Parameters = (FMaterialPixelParameters)0;')
    body.append('    Parameters.Particle.Color = float4(1.0, 1.0, 1.0, 1.0);')
    body.append('    Parameters.Particle.DynamicParameter = float4(1.0, 1.0, 1.0, 1.0);')
    # (the sprite vertex factory's offset of the translucency lighting position: a particle's random jitter)
    body.append('    float3 LightingPositionOffset = float3(0.0, 0.0, 0.0);')
    for s in setup:
        body.append('    ' + s)
    for nm in ('UV0', 'UV1', 'UV2', 'UV3'):
        if not any(s.startswith('float2 %s ' % nm) for s in setup):
            body.append('    float2 %s = float2(0.0, 0.0);' % nm)
    if not any(s.startswith('float3 T2W0 ') for s in setup):
        body.append('    float3 T2W0 = float3(1.0, 0.0, 0.0);')
    if not any(s.startswith('float4 T2W2 ') for s in setup):
        body.append('    float4 T2W2 = float4(0.0, 0.0, 1.0, 1.0);')
    if not any(s.startswith('float VertexContext ') for s in setup):
        body.append('    float VertexContext = 0.0;')
    body.append('    float3 SelectionColor = Raw[0].xyz;')
    # (the depth pass's coverage may need the camera vector and the tangent frame too: the base pass's prologue)
    body.append(BASE_PASS_PROLOGUE)
    body.extend('    ' + l for l in lines)
    for pin, (t, d) in pins.items():
        body.append('    %s P_%s = %s;' % (ue_mat.TYPE_NAMES[t], pin, res[pin].code))
    if pass_ == 'base':
        model = info['shading_model']
        if material.props.get('blend') == 'AlphaComposite':
            model = ('Forward_' if forward else 'Translucent_') + model
        if model not in BASE_PASS:
            raise NotImplementedError('the base pass of %s (%s) is not transcribed' % (perm, model))
        body.append(BASE_PASS[model])
    elif pass_ == 'distortion':
        body.append(DISTORTION_PASS)
    else:
        body.append(DEPTH_PASS)
    body.append('}')
    return '\n'.join(out + body), raw, info


def uniform_cpp(uset, raw, mat_slot):
    """C++ that fills the game's Material uniform buffer (slot mat_slot) from the raw parameter rows"""
    idx = {n: i for i, n in enumerate(raw)}

    def e(x):
        op = x['op']
        if op == 'const':
            v = (list(x['value']) + [0.0] * 4)[:4]
            return 'F4(%s)' % ', '.join(repr(float(c)) for c in v)
        if op == 'vparam':
            return 'RAW(%d)' % idx[x['name']]
        if op == 'sparam':
            return 'BC(RAW(%d).c[0])' % idx[x['name']]
        if op == 'swizzle':
            a = e(x['x'])
            comps = ['%s.c[%d]' % ('T', i) if i >= 0 else '0.0' for i in x['index'][:x.get('n', 4)]]
            comps = (comps + ['0.0'] * 4)[:4]
            return '[&]{ F4 T = %s; return F4(%s); }()' % (a, ', '.join(comps))
        if op == 'append':
            na = x['na']
            comps = ['A.c[%d]' % i for i in range(na)] + ['B.c[%d]' % i for i in range(4 - na)]
            return '[&]{ F4 A = %s; F4 B = %s; return F4(%s); }()' % (e(x['a']), e(x['b']), ', '.join(comps))
        if op == 'math':
            m = x['math']
            if m == 'dot':
                # the engine's folded dot product: as many components as its type (MCT_Float1/2/3/4 = 1/2/4/8)
                n = {1: 1, 2: 2, 4: 3, 8: 4}.get(x.get('type'), 4)
                return '[&]{ F4 A = %s; F4 B = %s; double D = 0; for (int i = 0; i < %d; ++i) D += A.c[i] * B.c[i]; return BC(D); }()' % (
                    e(x['a']), e(x['b']), n)
            return '(%s %s %s)' % (e(x['a']), m, e(x['b']))
        if op == 'clamp':
            return 'clamp4(%s, %s, %s)' % (e(x['x']), e(x['lo']), e(x['hi']))
        if op == 'max':
            return 'max4(%s, %s)' % (e(x['a']), e(x['b']))
        if op == 'frac':
            return 'frac4(%s)' % e(x['x'])
        if op == 'squareroot':
            return 'sqrt4(%s)' % e(x['x'])
        if op == 'texprop':
            # a texture's size (the game's animation textures): any size, the same for both shaders
            w, h = texture_sizes({'vectors': [x], 'scalars': []})[x['texture']['name']]
            return 'F4(%s, %s, 0.0, 0.0)' % (w, h)
        raise NotImplementedError(op)
    raw_fill = []
    for nm, (w, h) in texture_sizes(uset).items():
        if 'TEXSIZE:' + nm in idx:
            raw_fill.append('    { auto& R = a.cb[RAWSLOT][%d]; R[0] = fbits(%sf); R[1] = fbits(%sf); R[2] = 0; R[3] = 0; }' % (idx['TEXSIZE:' + nm], w, h))
    rows = [e(x) for x in uset['vectors']]
    sc = [e(x) + '.c[0]' for x in uset['scalars']]
    for j in range(0, len(sc), 4):
        part = (sc[j:j + 4] + ['0.0'] * 4)[:4]
        rows.append('F4(%s)' % ', '.join(part))
    lines = raw_fill + ['    { auto& U = a.cb[%d]; if (U.size() < %d) U.resize(%d);' % (mat_slot, len(rows), len(rows))]
    for i, r in enumerate(rows):
        lines.append('      { F4 X = %s; for (int c = 0; c < 4; ++c) U[%d][c] = fbits((float)X.c[c]); }' % (r, i))
    lines.append('    }')
    return '\n'.join(lines)


DRIVER = r'''
#include <random>
#include <cstdio>
#include <cstring>
#include <cmath>
struct F4 { double c[4]; F4(double x = 0, double y = 0, double z = 0, double w = 0) { c[0] = x; c[1] = y; c[2] = z; c[3] = w; } };
static F4 operator+(F4 a, F4 b) { return F4(a.c[0] + b.c[0], a.c[1] + b.c[1], a.c[2] + b.c[2], a.c[3] + b.c[3]); }
static F4 operator-(F4 a, F4 b) { return F4(a.c[0] - b.c[0], a.c[1] - b.c[1], a.c[2] - b.c[2], a.c[3] - b.c[3]); }
static F4 operator*(F4 a, F4 b) { return F4(a.c[0] * b.c[0], a.c[1] * b.c[1], a.c[2] * b.c[2], a.c[3] * b.c[3]); }
static F4 operator/(F4 a, F4 b) { return F4(a.c[0] / b.c[0], a.c[1] / b.c[1], a.c[2] / b.c[2], a.c[3] / b.c[3]); }
static double dot4(F4 a, F4 b) { return a.c[0] * b.c[0] + a.c[1] * b.c[1] + a.c[2] * b.c[2] + a.c[3] * b.c[3]; }
static F4 BC(double x) { return F4(x, x, x, x); }
static F4 clamp4(F4 x, F4 lo, F4 hi) { F4 r; for (int i = 0; i < 4; ++i) r.c[i] = std::min(std::max(x.c[i], lo.c[i]), hi.c[i]); return r; }
static F4 max4(F4 a, F4 b) { F4 r; for (int i = 0; i < 4; ++i) r.c[i] = std::max(a.c[i], b.c[i]); return r; }
static F4 frac4(F4 a) { F4 r; for (int i = 0; i < 4; ++i) r.c[i] = a.c[i] - std::floor(a.c[i]); return r; }
static F4 sqrt4(F4 a) { F4 r; for (int i = 0; i < 4; ++i) r.c[i] = std::sqrt(a.c[i]); return r; }
static std::mt19937_64 rng;
static double U(double a, double b) { return a + (b - a) * std::uniform_real_distribution<double>(0, 1)(rng); }
static uint32_t fbits(float f) { uint32_t u; std::memcpy(&u, &f, 4); return u; }
static float bitsf(uint32_t u) { float f; std::memcpy(&f, &u, 4); return f; }
#ifndef CBSIZE_INIT
#define CBSIZE_INIT 0
#endif
static const int CBSIZE[16] = {CBSIZE_INIT};
int main(int argc, char** argv)
{
    const int N = argc > 1 ? atoi(argv[1]) : 200;
    double maxd[10][4] = {};
    int nanmis[10][4] = {};
    int discard_mis = 0, discards = 0;
    for (int k = 0; k < N; ++k)
    {
        rng.seed(7000 + k);
        DXIO a;
        for (int r = 0; r < 40; ++r)
            for (int c = 0; c < 4; ++c)
                a.v[r][c] = LF(D(U(-1.0, 1.0), U(-0.02, 0.02), U(-0.02, 0.02)));
        // the interpolants as the base pass expects them: UVs anywhere, the tangent frame unit length
        a.v[POSREG][0] = LF(D(std::floor(U(0, 1920)) + 0.5, 1.0, 0.0));
        a.v[POSREG][1] = LF(D(std::floor(U(0, 1080)) + 0.5, 0.0, 1.0));
        a.v[POSREG][2] = LF(D(U(0.001, 1.0), 0, 0));
        a.v[POSREG][3] = LF(D(U(0.01, 1.0), 0, 0));
        for (int b = 0; b < 16; ++b)
        {
            a.cb[b].resize(CBSIZE[b] > 256 ? CBSIZE[b] : 256);
            for (auto& row : a.cb[b])
                for (int c = 0; c < 4; ++c)
                {
                    const double x = U(0, 1);
                    row[c] = x < 0.75 ? fbits((float)U(-2.0, 2.0)) : x < 0.85 ? (uint32_t)(int)U(0, 64) : x < 0.93 ? 0u : fbits(1.0f);
                }
        }
        // View: the debug views off most of the time, the overrides mostly identity (as in game)
        {
            auto& V = a.cb[VIEWSLOT];
            if (U(0, 1) < 0.8) { V[140][2] = 0; V[136][0] = 0; }
#ifdef FORWARD_SCENE
            // (the screen reflection's own debug switch off half the time: the water pass's reprojection then)
            if (U(0, 1) < 0.5) V[140][1] = 0;
#endif
            if (U(0, 1) < 0.7) { V[134][0] = V[134][1] = V[134][2] = 0; V[134][3] = fbits(1.0f); }
            if (U(0, 1) < 0.7) { V[132][0] = V[132][1] = V[132][2] = 0; V[132][3] = fbits(1.0f); }
            if (U(0, 1) < 0.7) { V[133][0] = V[133][1] = V[133][2] = 0; V[133][3] = fbits(1.0f); }
            if (U(0, 1) < 0.7) { V[135][0] = 0; V[135][1] = fbits(1.0f); }
            V[139][2] = (uint32_t)(int)U(0, 8);
            // the scene depth conversion: mostly depths 1..101 from the depth texture's 0..1 (the soft fades in range)
            if (U(0, 1) < 0.8) { V[57][0] = fbits(100.0f); V[57][1] = 0; V[57][2] = 0; V[57][3] = fbits(-1.0f); }
        }
        // the raw parameters (mostly in 0..1, as the game's)
        for (auto& row : a.cb[RAWSLOT])
            for (int c = 0; c < 4; ++c)
                row[c] = fbits((float)U(-0.2, 1.5));
#ifdef FORWARD_SCENE
        // (the editor's selection colour off half the time: the lighting not drowned by it)
        if (U(0, 1) < 0.5) a.cb[RAWSLOT][0] = {0u, 0u, 0u, 0u};
#endif
        auto RAW = [&](int i) { return F4(bitsf(a.cb[RAWSLOT][i][0]), bitsf(a.cb[RAWSLOT][i][1]), bitsf(a.cb[RAWSLOT][i][2]), bitsf(a.cb[RAWSLOT][i][3])); };
        (void)RAW;
FILL_MATERIAL
#ifdef FORWARD_SCENE
        // the forward pass's scene: lights and reflection captures around the shaded point (its world position as the
        // shader finds it), the light grid's lists of them, the directional light's cascades
        {
            auto& V = a.cb[VIEWSLOT];
            auto vf = [&](int r, int c) { return (double)bitsf(V[r][c]); };
            const double sx = a.v[POSREG][0].f.v, sy = a.v[POSREG][1].f.v, sz = a.v[POSREG][2].f.v;
            double hp[4];
            for (int c = 0; c < 4; ++c) hp[c] = sx * vf(36, c) + sy * vf(37, c) + sz * vf(38, c) + vf(39, c);
            const double wp[3] = {hp[0] / hp[3] - vf(62, 0), hp[1] / hp[3] - vf(62, 1), hp[2] / hp[3] - vf(62, 2)};
            auto put = [&](std::array<uint32_t, 4>& row, double x, double y, double z, double w)
            { row[0] = fbits((float)x); row[1] = fbits((float)y); row[2] = fbits((float)z); row[3] = fbits((float)w); };
            auto unit = [&](double* d) { d[0] = U(-1, 1); d[1] = U(-1, 1); d[2] = U(-1, 1);
                                         const double l = std::sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]) + 1e-9; d[0] /= l; d[1] /= l; d[2] /= l; };
            // a projection that takes the shaded point near the origin (its shadow map's coordinates and depth in range)
            auto shadow_rows = [&](std::array<uint32_t, 4>* rows, double w)
            {
                double m[3][3];
                for (int i = 0; i < 3; ++i) { for (int j = 0; j < 3; ++j) m[i][j] = U(-1, 1); put(rows[i], m[i][0], m[i][1], m[i][2], 0.0); }
                double t[3];
                for (int j = 0; j < 3; ++j) t[j] = -(wp[0] * m[0][j] + wp[1] * m[1][j] + wp[2] * m[2][j]);
                put(rows[3], t[0] + U(-1, 1) * w, t[1] + U(-1, 1) * w, t[2] + U(0, 1) * w, w);
            };
            auto& G = a.buf[GRID_T];
            G.assign(64, {0u, 0u, 0u, 0u});
            for (int i = 0; i < 64; ++i) G[i][0] = (i & 1) ? (uint32_t)U(0, 56) : (uint32_t)U(0, 4);
            auto& CL = a.buf[CULL_T];
            CL.assign(64, {0u, 0u, 0u, 0u});
            for (int i = 0; i < 64; ++i) CL[i][0] = (uint32_t)U(0, 8);
            auto& LB = a.buf[LOCAL_T];
            LB.assign(88, {0u, 0u, 0u, 0u});
            for (int l = 0; l < 8; ++l)
            {
                std::array<uint32_t, 4>* L = &LB[l * 11];
                const double R = U(1.0, 10.0), dist = R * U(0.05, 1.1);
                double d[3];
                unit(d);
                put(L[0], wp[0] + d[0] * dist, wp[1] + d[1] * dist, wp[2] + d[2] * dist, 1.0 / R);
                put(L[1], U(0, 3), U(0, 3), U(0, 3), U(0, 1) < 0.8 ? 0.0 : 8.0);
                unit(d);
                put(L[2], d[0], d[1], d[2], 0.0);
                L[2][3] = ((uint32_t)U(1, 8) << 8) | (U(0, 1) < 0.5 ? 1u : 0u);
                if (U(0, 1) < 0.15) L[2][3] &= 1u;
                put(L[3], U(0, 1) < 0.3 ? -3.0 : U(-1.0, 0.9), U(0.5, 5.0), U(0, 1) < 0.2 ? 0.0 : U(0.0, 1.0), 0.0);
                L[3][3] = U(0, 1) < 0.5 ? 0u : f32tof16_(D(U(0.1, 2.0), 0, 0));
                unit(d);
                put(L[4], d[0], d[1], d[2], U(0, 1) < 0.7 ? 0.0 : U(0.1, 1.0));
                put(L[5], U(0, 1) < 0.6 ? std::floor(U(0, 4)) : -1.0, 0.0, U(1.0, 50.0), U(0.0, 1.0));
                L[5][1] = (uint32_t)U(0, 8);
                if (U(0, 1) < 0.6) put(L[6], -1e9, -1e9, 1e9, 1e9); else put(L[6], U(-1, 0), U(-1, 0), U(0, 1), U(0, 1));
                shadow_rows(&L[7], U(0.5, 2.0));
            }
            auto& F = a.cb[FLDSLOT];
            F[0][2] = U(0, 1) < 0.85 ? 1u : 0u;
            F[0][3] = (uint32_t)U(0, 1000);
            F[1] = {(uint32_t)U(1, 64), (uint32_t)U(1, 64), (uint32_t)U(1, 32), 0u};
            F[2][0] = (uint32_t)U(0, 7);
            put(F[3], U(0.5, 2.0), U(0.5, 2.0), U(1.0, 8.0), 0.0);
            double d[3];
            unit(d);
            put(F[5], d[0] * U(0.5, 2), d[1] * U(0.5, 2), d[2] * U(0.5, 2), 0.0);
            put(F[6], U(0, 3), U(0, 3), U(0, 3), 0.0);
            put(F[7], 0.0, 0.0, U(-2.0, 2.0), U(-1.0, 2.0));
            F[7][0] = ((uint32_t)U(1, 8) << 8) | (U(0, 1) < 0.5 ? 1u : 0u);
            F[8][0] = (uint32_t)U(0, 5);
            {
                const double d0 = U(0, 0.4), d1 = d0 + U(0, 0.4), d2 = d1 + U(0, 0.4), d3 = d2 + U(0, 0.4);
                put(F[9], d0, d1, d2, d3);
            }
            for (int c = 0; c < 4; ++c) shadow_rows(&F[10 + 4 * c], 1.0);
            for (int r = 26; r < 30; ++r) { if (U(0, 1) < 0.6) put(F[r], -1e9, -1e9, 1e9, 1e9); else put(F[r], U(-1, 0), U(-1, 0), U(0, 1), U(0, 1)); }
            for (int r = 30; r < 34; ++r) put(F[r], std::floor(U(0, 4)), 0.0, 0.0, 0.0);
            put(F[40], U(0.5, 50.0), U(0.0, 1.0), 0.0, 0.0);
            a.cb[PRIMSLOT][16][3] = (uint32_t)U(1, 8);
            // the view's exposure and the height fog in range (no division by a zero clip w, no log of a negative)
            put(V[128], U(0.5, 2.0), U(0.5, 2.0), bitsf(V[128][2]), bitsf(V[128][3]));
            for (int r = 4; r < 7; ++r) V[r][3] = fbits(0.0f);
            V[7][3] = fbits((float)U(0.5, 2.0));
            put(V[183], U(8, 64), U(8, 64), bitsf(V[183][2]), bitsf(V[183][3]));
            put(V[185], bitsf(V[185][0]), bitsf(V[185][1]), U(0.01, 0.1), bitsf(V[185][3]));
            put(V[186], U(0.01, 0.1), U(0.01, 0.1), bitsf(V[186][2]), bitsf(V[186][3]));
            put(V[187], U(0.5, 2.0), U(0.5, 2.0), U(0.5, 4.0), U(0.0, 2.0));
            // the point's clip position (translated world to clip): its depth in 0..1 (the screen-space reflection's
            // ray then meets the scene's depth)
            {
                const double twp[3] = {hp[0] / hp[3], hp[1] / hp[3], hp[2] / hp[3]};
                const double cw = U(0.5, 2.0), cz = U(0.05, 0.95) * cw;
                double sw = 0, sz2 = 0;
                for (int i = 0; i < 3; ++i) { sw += twp[i] * vf(i, 3); sz2 += twp[i] * vf(i, 2); }
                V[3][2] = fbits((float)(cz - sz2));
                V[3][3] = fbits((float)(cw - sw));
            }
#ifdef GLOBSLOT
            {
                auto& Gl = a.cb[GLOBSLOT];
                put(Gl[FOGROW], U(0.0, 0.2), U(0.0, 0.2), bitsf(Gl[FOGROW][2]), U(0.0, 1.0));
                put(Gl[FOGROW + 1], U(0, 1), U(0, 1), U(0, 1), bitsf(Gl[FOGROW + 1][3]));
                put(Gl[FOGROW + 2], U(0.0, 0.5), U(-1.0, 1.0), bitsf(Gl[FOGROW + 2][2]), U(0.0, 1.0));
                unit(d);
                put(Gl[FOGROW + 5], d[0], d[1], d[2], bitsf(Gl[FOGROW + 5][3]));
                put(Gl[FOGROW + 6], U(0, 1), U(0, 1), U(0, 1), bitsf(Gl[FOGROW + 6][3]));
                // the ambient cube's override: its colours in range, on half the time
                put(Gl[10], U(0, 1), U(0, 1), U(0, 1), U(0, 1) < 0.5 ? 0.0 : U(0, 1));
                put(Gl[11], U(0, 1), U(0, 1), U(0, 1), bitsf(Gl[11][3]));
                put(Gl[12], U(0, 1), U(0, 1), U(0, 1), bitsf(Gl[12][3]));
            }
#endif
            auto& RC = a.cb[RCSLOT];
            for (int c = 0; c < 8; ++c)
            {
                const double R = U(0.5, 5.0), dist = R * U(0.0, 1.05);
                unit(d);
                put(RC[c], wp[0] + d[0] * dist, wp[1] + d[1] * dist, wp[2] + d[2] * dist, R);
                put(RC[341 + c], U(0.2, 2.0), std::floor(U(0, 4)), U(0, 1) < 0.5 ? 1.0 : 0.0, 0.0);
                shadow_rows(&RC[1023 + 4 * c], 1.0);
                put(RC[2387 + c], U(0.2, 2.0), U(0.2, 2.0), U(0.2, 2.0), U(0.1, 2.0));
            }
        }
#endif
        for (int t = 0; t < 128; ++t) a.tex[t] = 0x1234567ULL * (t + 1) + k * 7919ULL;
        for (int s = 0; s < 16; ++s) a.samp[s] = s + 1;
        DXIO b = a;
        shader_orig(a);
        shader_rebuilt(b);
        if (a.discarded != b.discarded) { ++discard_mis; continue; }
        if (a.discarded) { ++discards; continue; }
        for (int o = 0; o < 10; ++o)
            for (int c = 0; c < 4; ++c)
            {
                const double x = a.o[o][c].f.v, y = b.o[o][c].f.v;
                if (std::isnan(x) || std::isnan(y)) { if (std::isnan(x) != std::isnan(y)) ++nanmis[o][c]; continue; }
                const double d = std::fabs(x - y) / std::max(1.0, std::fabs(x));
                if (d > maxd[o][c]) maxd[o][c] = d;
            }
    }
    double worst = 0;
    for (int o = 0; o < 10; ++o)
        for (int c = 0; c < 4; ++c)
            if (maxd[o][c] > worst) worst = maxd[o][c];
    printf("cases %d discards %d discard_mismatch %d worst %.3g\n", N, discards, discard_mis, worst);
    for (int o = 0; o < 10; ++o)
    {
        bool any = false;
        for (int c = 0; c < 4; ++c) any |= maxd[o][c] > 1e-4 || nanmis[o][c];
        if (any)
            printf("  o%d: %.3g %.3g %.3g %.3g  nan-mismatch %d %d %d %d\n", o, maxd[o][0], maxd[o][1], maxd[o][2], maxd[o][3],
                   nanmis[o][0], nanmis[o][1], nanmis[o][2], nanmis[o][3]);
    }
    return 0;
}
'''


def check(master, perm, kind, n=200, keep=None):
    material = remake_graphs.MASTERS[master]()
    src, raw, info = shader_source(perm, kind, material)
    work = keep or tempfile.mkdtemp(prefix='rchk_', dir='/tmp/scratch')
    hp = os.path.join(work, '%s_%s.hlsl' % (perm, kind))
    open(hp, 'w').write(src)
    key = shader_key(kind)
    asm_orig = open(os.path.join(DIS, perm, key + '.asm'), encoding='latin-1').read()
    try:
        asm_new = lift_check.fxc(hp, 'ps_5_0', hp[:-5] + '.dxbc')
    except RuntimeError as ex:
        return {'error': str(ex)[-3000:], 'hlsl': hp}
    bind = json.load(open(os.path.join(DIS, perm, 'bindings.json')))[key]
    cbn = bind['cb']
    view_slot = cbn.index('View') if 'View' in cbn else 0
    mat_slot = cbn.index('Material') if 'Material' in cbn else 15
    L = dxbc2hlsl.Lifter(asm_orig)
    pos = next((int(r[3]) for r in L.input_sig if r[4] == 'POS'), 39)
    uset = remake_ue.uniform_sets()[perm]
    fill = uniform_cpp(uset, raw, mat_slot)
    sizes = {int(b): int(n) for b, n in re.findall(r'dcl_constantbuffer CB(\d+)\[(\d+)\]', asm_orig)}
    defs = ['#define CBSIZE_INIT %s' % ', '.join(str(sizes.get(b, 0)) for b in range(16))]
    if 'dcl_resource_buffer' in asm_orig:
        bufs = re.findall(r'dcl_resource_buffer \(uint,uint,uint,uint\) t(\d+)', asm_orig)
        # (the water pass's shader has no local lights' buffer: theirs then goes to an unused slot)
        defs += ['#define FORWARD_SCENE 1', '#define GRID_T %s' % bufs[0], '#define CULL_T %s' % bufs[1],
                 '#define LOCAL_T %s' % (bufs[2] if len(bufs) > 2 else 127),
                 '#define FLDSLOT %d' % cbn.index('ForwardGlobalLightData'), '#define RCSLOT %d' % cbn.index('ReflectionCapture'),
                 '#define PRIMSLOT %d' % cbn.index('Primitive')]
        if '' in cbn:
            defs += ['#define GLOBSLOT %d' % cbn.index(''), '#define FOGROW %d' % (32 if kind.endswith('__Sprite') else 36)]
    cpp = ['#include "dxbc_cpu.hpp"', '#define POSREG %d' % pos, '#define VIEWSLOT %d' % view_slot, '#define RAWSLOT %d' % RAW_SLOT] + defs + [
           dxbc2cpp.translate(asm_orig, 'shader_orig'), dxbc2cpp.translate(asm_new, 'shader_rebuilt'),
           DRIVER.replace('FILL_MATERIAL', fill)]
    cp = os.path.join(work, '%s_%s.cpp' % (perm, kind))
    open(cp, 'w').write('\n'.join(cpp))
    exe = cp[:-4]
    p = subprocess.run(['g++', '-std=c++17', '-O1', '-w', '-I' + lift_check.HERE, '-I' + lift_check.HARNESS, cp, '-o', exe],
                       capture_output=True, text=True)
    if p.returncode:
        return {'error': 'g++: ' + p.stderr[-3000:], 'hlsl': hp}
    p = subprocess.run([exe, str(n)], capture_output=True, text=True)
    if not keep:
        # (each check's files are megabytes: only a failed one's are kept, to look at)
        import shutil
        shutil.rmtree(work, ignore_errors=True)
    return {'result': p.stdout.strip(), 'hlsl': hp}


def permutations(master):
    """the master's own permutation and its instances' (each one with a shader map of its own), with whether each is
    masked (its coverage in the depth-only pass)"""
    inst = json.load(open(os.path.join(ROOT, 'remake_inst.json')))
    # (the particles' depth pass clips by their coverage too, masked or not)
    depth_coverage = bool(remake_graphs.MASTERS[master]().props.get('particle_visibility')) if master in remake_graphs.MASTERS else False
    out = []
    for name in [master] + sorted(k for k, v in inst.items() if v['parent'] == master):
        if not os.path.exists(os.path.join(DIS, name, remake_ue.BASE_PS + '.asm')):
            continue
        info = remake_ue.parse_debug(remake_ue.uniform_sets()[name]['debug'])
        kinds = ['base']
        if (info['masked'] or depth_coverage) and os.path.exists(os.path.join(DIS, name, remake_ue.DEPTH_PS + '.asm')):
            kinds.append('coverage')
        # the distortion pass (a distorting material's), and the other vertex factories' shaders dumped next to them
        for pass_ in ('base', 'distortion'):
            for f in sorted(os.listdir(os.path.join(DIS, name))):
                if f.startswith(SHADER_KEYS[pass_]) and f.endswith('.asm'):
                    rest = f[len(SHADER_KEYS[pass_]):-4]
                    if rest == '' and pass_ == 'distortion' or rest in ('__Sprite',) and rest in SEM_BY_VF:
                        kinds.append(pass_ + rest)
        out.append({'name': name, 'coverage': 'coverage' in kinds, 'kinds': kinds})
    return out


def main():
    args = sys.argv[1:]
    n = 200
    if '-n' in args:
        i = args.index('-n'); n = int(args[i + 1]); del args[i:i + 2]
    after = None
    if '--after' in args:
        i = args.index('--after'); after = args[i + 1]; del args[i:i + 2]
    master = args[0]
    flt = [f for f in args[1:] if not f.startswith('!')]
    excl = [f[1:] for f in args[1:] if f.startswith('!')]
    for p in permutations(master):
        if flt and not any(f in p['name'] for f in flt) or any(f in p['name'] for f in excl) or (after and p['name'] <= after):
            continue
        for kind in p['kinds']:
            r = check(master, p['name'], kind, n)
            tag = '%-70s %-8s' % (p['name'], kind)
            if 'error' in r:
                print(tag, 'ERROR', r['error'].strip().splitlines()[-1][:300], '(%s)' % r['hlsl'])
            else:
                print(tag, r['result'].replace('\n', '\n' + ' ' * 80))


if __name__ == '__main__':
    main()
