MaterialFloat4 CustomExpression2(FMaterialPixelParameters Parameters,MaterialFloat2 ukUV0,MaterialFloat2 ukUV1,MaterialFloat2 ukUV2,MaterialFloat2 ukUV3,MaterialFloat3 ukVCol,MaterialFloat3 ukNV,MaterialFloat3 ukTV,MaterialFloat3 ukBV,MaterialFloat3 ukPV,MaterialFloat3 ukPW,MaterialFloat3 ukLV,MaterialFloat3 ukQ0V,MaterialFloat3 ukQ1V,MaterialFloat ukTime,MaterialFloat4 ukParams0,MaterialFloat4 ukParams1,MaterialFloat4 ukParams2,MaterialFloat4 ukSun,MaterialFloat4 ukAmb,MaterialFloat4 ukToon,Texture2D _a0, SamplerState _a0Sampler ,Texture2D _s0, SamplerState _s0Sampler ,Texture2D _n0, SamplerState _n0Sampler ,Texture2D _e0, SamplerState _e0Sampler ,Texture2D _t0, SamplerState _t0Sampler ,Texture2D _a1, SamplerState _a1Sampler ,MaterialFloat4 opt_texcoord0,MaterialFloat4 opt_texcoord1,MaterialFloat4 opt_texcoord2,MaterialFloat4 opt_texcoord3,MaterialFloat4 opt_texcoord4,MaterialFloat4 opt_texcoord5,MaterialFloat4 opt_texcoord_toon,MaterialFloat4 opt_proctexcoord01,MaterialFloat4 opt_proctexcoord2,MaterialFloat4 opt_texture0,MaterialFloat4 opt_texture1,MaterialFloat4 opt_texture2,MaterialFloat4 opt_texture3,MaterialFloat4 opt_texture4,MaterialFloat4 opt_texture5,MaterialFloat4 opt_texture6,MaterialFloat4 opt_texture7,MaterialFloat4 opt_indirect0,MaterialFloat4 opt_indirect1,MaterialFloat4 opt_indirect2,MaterialFloat4 opt_indirect3,MaterialFloat4 opt_indirect4,MaterialFloat4 opt_indirect5,MaterialFloat4 opt_indirect_world_scaling,MaterialFloat4 opt_color0_cfg,MaterialFloat4 opt_color1_cfg,MaterialFloat4 opt_color2_cfg,MaterialFloat4 opt_color3_cfg,MaterialFloat4 opt_color4_cfg,MaterialFloat4 opt_color5_cfg,MaterialFloat4 opt_color6_cfg,MaterialFloat4 opt_color7_cfg,MaterialFloat4 opt_color8_cfg,MaterialFloat4 opt_color9_cfg,MaterialFloat4 opt_color10_cfg,MaterialFloat4 opt_color11_cfg,MaterialFloat4 opt_color0_src,MaterialFloat4 opt_color1_src,MaterialFloat4 opt_color2_src,MaterialFloat4 opt_color3_src,MaterialFloat4 opt_color4_src,MaterialFloat4 opt_color5_src,MaterialFloat4 opt_color6_src,MaterialFloat4 opt_color7_src,MaterialFloat4 opt_color8_src,MaterialFloat4 opt_color9_src,MaterialFloat4 opt_color10_src,MaterialFloat4 opt_color11_src,MaterialFloat4 opt_color0_ch,MaterialFloat4 opt_color1_ch,MaterialFloat4 opt_color2_ch,MaterialFloat4 opt_color3_ch,MaterialFloat4 opt_color4_ch,MaterialFloat4 opt_color5_ch,MaterialFloat4 opt_color6_ch,MaterialFloat4 opt_color7_ch,MaterialFloat4 opt_color8_ch,MaterialFloat4 opt_color9_ch,MaterialFloat4 opt_color10_ch,MaterialFloat4 opt_color11_ch,MaterialFloat4 opt_normal,MaterialFloat4 opt_normal2,MaterialFloat4 opt_out0,MaterialFloat4 opt_out1,MaterialFloat4 opt_out2,MaterialFloat4 opt_out3,MaterialFloat4 opt_out4,MaterialFloat4 opt_out5,MaterialFloat4 opt_wind,MaterialFloat4 opt_vtxmod0,MaterialFloat4 opt_vtxmod1,MaterialFloat4 opt_vtxmod2,MaterialFloat4 opt_inner0,MaterialFloat4 opt_inner1,MaterialFloat4 opt_normal_modify,MaterialFloat4 const_color0,MaterialFloat4 const_color1,MaterialFloat4 const_color2,MaterialFloat4 const_color3,MaterialFloat4 const_color4,MaterialFloat4 const_color5,MaterialFloat4 const_value0_3,MaterialFloat4 const_value4_7,MaterialFloat4 const_vector0,MaterialFloat4 const_vector1,MaterialFloat4 tex_srt0_m,MaterialFloat4 tex_srt0_t,MaterialFloat4 tex_srt1_m,MaterialFloat4 tex_srt1_t,MaterialFloat4 tex_srt2_m,MaterialFloat4 tex_srt2_t,MaterialFloat4 tex_srt3_m,MaterialFloat4 tex_srt3_t,MaterialFloat4 tex_srt4_m,MaterialFloat4 tex_srt4_t,MaterialFloat4 tex_srt5_m,MaterialFloat4 tex_srt5_t,MaterialFloat4 indirect_scale0,MaterialFloat4 indirect_scale1,MaterialFloat4 indirect_scale2,MaterialFloat4 indirect_scale3,MaterialFloat4 indirect_scale4,MaterialFloat4 indirect_scale5,MaterialFloat4 texture_array_index0_3,MaterialFloat4 texture_array_index4_5,MaterialFloat4 gsys_bake_st0,MaterialFloat4 gsys_bake_st1,MaterialFloat4 uking_wind)
{
#ifndef UK_UE
#define UK_UE 1
#endif
#ifndef UK_SLOT
#define UK_SLOTG(s_, uv_, dx_, dy_, dst_) { int uks_ = (s_); if (uks_ == 1) dst_ = _s0.SampleGrad(_s0Sampler, uv_, dx_, dy_); else if (uks_ == 2) dst_ = _n0.SampleGrad(_n0Sampler, uv_, dx_, dy_); else if (uks_ == 3) dst_ = _e0.SampleGrad(_e0Sampler, uv_, dx_, dy_); else if (uks_ == 4) dst_ = _t0.SampleGrad(_t0Sampler, uv_, dx_, dy_); else if (uks_ == 5) dst_ = _a1.SampleGrad(_a1Sampler, uv_, dx_, dy_); else dst_ = _a0.SampleGrad(_a0Sampler, uv_, dx_, dy_); }
#define UK_SLOT(s_, uv_, dst_) { float2 uku_ = (uv_); float2 ukdx_ = ddx(uku_); float2 ukdy_ = ddy(uku_); UK_SLOTG(s_, uku_, ukdx_, ukdy_, dst_) }
#endif
struct UKFn
{
// =====================================================================================
//  UKingMat core  -  re-implementation of Breath of the Wild's "uking_mat" material shader
//
//  Portable subset: the same text compiles as HLSL (Unreal custom nodes, wrapped in a
//  struct so the functions become methods) and as GLSL (verification harness, via a few
//  #defines).  Rules followed here: explicit vector constructors only, scalar ternaries
//  only, no structs, no static, no casts other than int()/float(), callees before callers,
//  array results passed as inout (callers initialise them, so FXC never sees a partly
//  written out parameter), no method call used directly as another call's argument.
//
//  Coordinate frame used by every pixel function ("BotW view space"): right-handed view
//  space, x right, y up, z towards the viewer (so view depth = -Vpos.z).  Distances are in
//  BotW units (1 unit = 1 m).  The Unreal wrapper converts to/from this frame.
//
//  Options (BotW static shader options) arrive packed in an int4 array O[UKO_COUNT];
//  material uniforms (gsys_material block) in a float4 array U[UKU_COUNT].  See the
//  UKO_* / UKU_* layout below.  Every option is a plain runtime value, so constant inputs
//  let the shader compiler fold everything away (specialised material) and parameter
//  inputs give one master material that covers every option combination.
// =====================================================================================

#ifndef UK_CORE_DEFINES
#define UK_CORE_DEFINES 1

#define UK_DEC_S 2.007874
#define UK_DEC_B -1.007874
#define UK_ENC_S 0.4980392
#define UK_ENC_B 0.5019608

// ---- option layout (int4 slots) ----
#define UKO_TC        0    // 0..5  texcoordN: (enable, mapping, srt, offset_srt)
#define UKO_TCTOON    6    // texcoord_toon_spec: (mapping, srt, offset_srt, -)
#define UKO_PTC       7    // proctexcoord0/1: (enable0, mapping0, enable1, mapping1)
#define UKO_PTC2      8    // proctexcoord2: (enable2, mapping2, -, -)
#define UKO_TEX       9    // 9..16 textureN (N=0..7): (texcoord select, decode, texture (6/7: source slot) / array (0..5), post)
#define UKO_IND       17   // 17..22 indirectK: (enable, texcoord, type, signed_fetch)
#define UKO_INDWS     23   // (world_scaling bitmask K0..K5, -, -, -)
#define UKO_CCFG      24   // 24..35 colorK: (enable, calc_type, clamp01, before_normal)
#define UKO_CSRC      36   // 36..47 colorK: (A, B, C, D)
#define UKO_CCH       48   // 48..59 colorK: (A_ch, B_ch, C_ch, D_ch)
#define UKO_NRM       60   // (enable_normalmap, normal_color, enable_decode_normalmap, enable_normalmap2)
#define UKO_NRM2      61   // (normal_color2, normalmap_blend_ratio, normalmap_blend_channel, normalmap_blend_method)
#define UKO_OUT0      62   // (albedo_color, enable_emission, emission_color, material_behave)
#define UKO_OUT1      63   // (enable_ao, ao_color, ao_channel, gsys_renderstate)
#define UKO_OUT2      64   // (transparency_color, transparency_channel, specmask_scaler, specular_channel)
#define UKO_OUT3      65   // (metal_color, metal_channel, grossy_color, grossy_channel)
#define UKO_OUT4      66   // (grossy_intensity, enable_transmission, transmission_color, transmission_channel)
#define UKO_OUT5      67   // (enable_bake_texture, bake_shadow_type, toon_spec (texcoord_toon_spec_srt >= 0), -)
#define UKO_WIND      68   // (enable_wind_vtx_transform, wind_vtx_transform_channel, flags(1 lock,2 lie,4 height,8 coreinfo,16 scale), -)
#define UKO_VMOD0     69   // (modify_position_type, vtx_position_modify_calc_type, vtx_position_modify_shadow_only, vtx_texture0_texcoord)
#define UKO_VMOD1     70   // (vtx_position_modify_A, B, C, D)
#define UKO_VMOD2     71   // (A_channel, B_channel, C_channel, D_channel)
#define UKO_INNER0    72   // (enable_inner_light, inner_light_mode, enable_inner_light_line, inner_light_source_position)
#define UKO_INNER1    73   // (inner_light_source_radius, inner_light_diffusivity, source_position_end, source_radius_end)
#define UKO_NMOD      74   // (modify_normal_type, vtx_normal_modify_A, enable_backface_modify, -)
#define UKO_COUNT     75

// ---- uniform layout (float4 slots) ----
#define UKU_CC        0    // 0..5 const_color0..5
#define UKU_CV        6    // 6: const_value0..3, 7: const_value4..7
#define UKU_VEC       8    // 8..9 const_vector0..1
#define UKU_SRT       10   // 10+2k: tex_srtk[0] = (m00, m01, m10, m11), 11+2k: tex_srtk[1] = (tx, ty, -, -)
#define UKU_INDSC     22   // 22..27 indirect_scale0..5 (x, y, -, -)
#define UKU_ARRIDX    28   // 28: texture_array_index0..3, 29: 4..5
#define UKU_BAKE      30   // 30: gsys_bake_st0, 31: gsys_bake_st1
#define UKU_MISC      32   // (gsys_alpha_test_ref_value, dynamic_exposure, time, object_random)
#define UKU_LIGHT     33   // light direction (BotW view space, direction the light travels) xyz, w = base_light_change_ratio
#define UKU_WIND      34   // (wind_vtx_transform_intensity, lie_intensity, lie_height, -)
#define UKU_ENV32     35   // wind env: (strength, dir.x, dir.z, time)
#define UKU_ENV33     36   // wind env: (blend, dir2.x, dir2.z, -)
#define UKU_DEPTH     37   // (projection scale for 508 / world-scaled indirect, scene linear depth (BotW units), -, -)
#define UKU_SCENE0    38   // scene colour 0 (source 8)
#define UKU_SCENE1    39   // scene colour 1 (source 9)
#define UKU_ENV34     40   // lie map transform: uv = (z + W.x * x, w + W.z * y)
#define UKU_COUNT     41

// ---- source table ----
#define UKS_TEX       0    // texture slots 0..7
#define UKS_CC        8    // const_color0..5
#define UKS_CV        14   // const_value0..7 (broadcast)
#define UKS_VEC       22   // const_vector0..1
#define UKS_COL       24   // combiner outputs 0..13
#define UKS_VC        38   // vertex colour _c0
#define UKS_K         39   // 400..406 constants
#define UKS_SYS       46   // 500..518 system values
#define UKS_SCENE     65   // 8, 9 scene colour
#define UKS_ZERO      67
#define UKS_COUNT     68

#endif

// ------------------------------------------------------------------ small helpers
float4 ukS4(float x) { return float4(x, x, x, x); }

float ukLog2(float x) { return x > 0.0 ? log2(x) : -126.0; }

float4 ukPow(float4 a, float4 b)
{
    return float4(exp2(b.x * ukLog2(a.x)), exp2(b.y * ukLog2(a.y)), exp2(b.z * ukLog2(a.z)), exp2(b.w * ukLog2(a.w)));
}

float4 ukLerp(float4 a, float4 b, float4 t) { return a + (b - a) * t; }

float4 ukSigned(float4 v) { return v * UK_DEC_S + ukS4(UK_DEC_B); }

// BotW normal-map decode: signed xy, z rebuilt, w passed through
float4 ukNrmDecode(float4 v)
{
    float x = v.x * UK_DEC_S + UK_DEC_B;
    float y = v.y * UK_DEC_S + UK_DEC_B;
    float z = sqrt(1.0 - saturate(x * x + y * y));
    return float4(x, y, z, v.w);
}

// texture decode option (uking_textureN_decode): 0 raw, 1 signed, 2 normal map
float4 ukTexDecode(float4 v, int dec)
{
    if (dec == 1) return ukSigned(v);
    if (dec == 2) return ukNrmDecode(v);
    return v;
}

// source code (SET0) -> source table index
int ukSrcIndex(int code)
{
    if (code >= 0 && code <= 7) return UKS_TEX + code;
    if (code >= 100 && code <= 103) return UKS_CC + (code - 100);
    if (code >= 104 && code <= 111) return UKS_CV + (code - 104);
    if (code >= 112 && code <= 113) return UKS_CC + 4 + (code - 112);
    if (code >= 114 && code <= 115) return UKS_VEC + (code - 114);
    if (code >= 200 && code <= 213) return UKS_COL + (code - 200);
    if (code == 300) return UKS_VC;
    if (code >= 400 && code <= 406) return UKS_K + (code - 400);
    if (code >= 500 && code <= 518) return UKS_SYS + (code - 500);
    if (code == 8 || code == 9) return UKS_SCENE + (code - 8);
    return UKS_ZERO;
}

// channel select / modifier (SET2): code = comp*10 + mod; comp 0 rgba, 1..4 r,g,b,a broadcast;
// mod 0 x, 1 1-x, 2 -x, 3 x-1.  2000 = normal-map decode.  (1000-series treated as 0-series.)
float4 ukChannel(float4 v, int ch)
{
    if (ch == 2000) return ukNrmDecode(v);
    if (ch >= 1000) ch = ch - 1000;
    int comp = ch / 10;
    int md = ch - comp * 10;
    float4 r = v;
    if (comp == 1) r = ukS4(v.x);
    else if (comp == 2) r = ukS4(v.y);
    else if (comp == 3) r = ukS4(v.z);
    else if (comp == 4) r = ukS4(v.w);
    if (md == 1) r = ukS4(1.0) - r;
    else if (md == 2) r = -r;
    else if (md == 3) r = r - ukS4(1.0);
    return r;
}

// combiner calc types (SET1)
float4 ukCalc(int ct, float4 A, float4 B, float4 C, float4 D)
{
    if (ct == 0) return A;
    if (ct == 1) return A + B;
    if (ct == 2) return A * B;
    if (ct == 3) return A - B;                       // never used by BotW assets (guess)
    if (ct == 4) return ukLerp(A, B, C);
    if (ct == 5) return (A + B) * C;
    if (ct == 6) return A * B + C * D;
    if (ct == 7) return ukPow(A, B);
    if (ct == 8) return A * B + C;
    if (ct == 9) return A * B * C;
    if (ct == 10) return A + B + C + D;
    if (ct == 11) return A * B * C * D;
    if (ct == 12) return ukLerp(A, B, C) * D;
    if (ct == 13) return A * UK_ENC_S + ukS4(UK_ENC_B);   // signed -> unorm encode
    if (ct == 14) return A * UK_DEC_S + ukS4(UK_DEC_B);   // unorm -> signed decode
    if (ct == 15) return ukLerp(A, B, C) + D;
    if (ct == 16) return (A + B) * C + D;
    if (ct == 17) return A + B + C;
    if (ct == 18) return (A + B) * C * D;
    if (ct == 19) return (A + B + C) * D;
    if (ct == 21) return (A * B + C) * D;
    if (ct == 25)
    {
        float4 l = ukLerp(A, B, C);
        return float4(normalize(l.xyz), l.w);
    }
    if (ct == 26)
    {
        float3 n = normalize(float3(A.x + B.x * C.x, A.y + B.y * C.y, A.z));
        return float4(n, A.w);
    }
    if (ct == 27) return ukLerp(A * D, B, C);
    if (ct == 28) return ukPow(A, B) * C + D;
    if (ct == 29) return float4(sin((A.x * B.x + C.x) * 6.2831853), sin((A.y * B.y + C.y) * 6.2831853),
                                sin((A.z * B.z + C.z) * 6.2831853), sin((A.w * B.w + C.w) * 6.2831853)) * D;
    if (ct == 30) return float4(cos((A.x * B.x + C.x) * 6.2831853), cos((A.y * B.y + C.y) * 6.2831853),
                                cos((A.z * B.z + C.z) * 6.2831853), cos((A.w * B.w + C.w) * 6.2831853)) * D;
    return A;                                        // 20, 22-24, 31, 32: never used by BotW assets
}

// --------------------------------------------------------------- texture coordinates
float2 ukSRT(float2 uv, float4 m0, float4 m1)
{
    return float2(uv.x * m0.x + uv.y * m0.z + m1.x, uv.x * m0.y + uv.y * m0.w + m1.y);
}

// const-colour style sources usable as texcoords (mapping 100..115)
float4 ukConstSrc(int code, float4 U[UKU_COUNT])
{
    if (code >= 100 && code <= 103) return U[UKU_CC + code - 100];
    if (code >= 112 && code <= 113) return U[UKU_CC + 4 + code - 112];
    if (code >= 114 && code <= 115) return U[UKU_VEC + code - 114];
    if (code >= 104 && code <= 107) return ukS4(U[UKU_CV][code - 104]);
    if (code >= 108 && code <= 111) return ukS4(U[UKU_CV + 1][code - 108]);
    if (code >= 400 && code <= 406)
    {
        float k = 0.0;
        if (code == 401) k = 0.5;
        if (code == 402) k = 1.0;
        if (code == 403) k = 2.0;
        if (code == 404) k = 4.0;
        if (code == 405) k = 0.25;
        if (code == 406) k = 0.75;
        return ukS4(k);
    }
    return ukS4(0.0);
}

float2 ukApplySRT(float2 uv, int srt, int osrt, float4 U[UKU_COUNT])
{
    if (srt >= 0 && srt <= 5)
    {
        float4 m0 = U[UKU_SRT + 2 * srt];
        float4 m1 = U[UKU_SRT + 2 * srt + 1];
        if (osrt >= 0 && osrt <= 5)
        {
            float r = U[UKU_MISC].w;
            m0 = U[UKU_SRT + 2 * osrt] * r + m0;
            m1 = U[UKU_SRT + 2 * osrt + 1] * r + m1;
        }
        uv = ukSRT(uv, m0, m1);
    }
    return uv;
}

// mesh uv channel / world xz / constant -> one texcoord set (mapping SET4)
float2 ukMapUV(int mp, float2 uv0, float2 uv1, float2 uv2, float2 uv3, float3 wpos, float4 U[UKU_COUNT])
{
    if (mp == 1) return uv1;
    if (mp == 2) return uv2;
    if (mp == 3) return uv3;
    if (mp == 11) return float2(wpos.x, wpos.z);
    if (mp >= 100 && mp <= 115) return ukConstSrc(mp, U).xy;
    return uv0;                                       // 0, 10 (unknown) and anything else
}

// the six texcoord sets (uking_texcoord0..5) + toon-spec coordinate
void ukTexcoordSets(int4 O[UKO_COUNT], float4 U[UKU_COUNT], float2 uv0, float2 uv1, float2 uv2, float2 uv3, float3 wpos,
                    inout float2 tc[6], out float toonT)
{
    for (int z = 0; z < 6; z++) tc[z] = uv0;
    for (int k = 0; k < 6; k++)
    {
        int mp = O[UKO_TC + k].y;
        float2 uv = ukMapUV(mp, uv0, uv1, uv2, uv3, wpos, U);
        if (mp >= 20 && mp <= 25)
        {
            int j = mp - 20;
            uv = uv0;
            for (int i = 0; i < 6; i++)
                if (i == j && i < k) uv = tc[i];
        }
        tc[k] = ukApplySRT(uv, O[UKO_TC + k].z, O[UKO_TC + k].w, U);
    }
    int tmp = O[UKO_TCTOON].x;
    float2 tuv = ukMapUV(tmp, uv0, uv1, uv2, uv3, wpos, U);
    if (tmp >= 20 && tmp <= 25)
    {
        tuv = uv0;
        for (int i = 0; i < 6; i++)
            if (i == tmp - 20) tuv = tc[i];
    }
    toonT = ukApplySRT(tuv, O[UKO_TCTOON].y, O[UKO_TCTOON].z, U).x;
}

// texture texcoord select (0,1,2 -> sets 0-2; 6,7,8 -> sets 3-5; 3,4,5 -> proctexcoord 0-2)
int ukSelSet(int sel)
{
    if (sel >= 0 && sel <= 2) return sel;
    if (sel >= 6 && sel <= 8) return sel - 3;
    return -1;
}

float2 ukSetUV(int set, float2 tc[6])
{
    float2 r = tc[0];
    for (int i = 0; i < 6; i++)
        if (i == set) r = tc[i];
    return r;
}

// ---------------------------------------------------------------- stage 1
// texcoord sets + undistorted uv of each indirect texture (slots 0..5)
void ukStage1(int4 O[UKO_COUNT], float4 U[UKU_COUNT], float2 uv0, float2 uv1, float2 uv2, float2 uv3, float3 wpos,
              inout float2 tc[6], out float toonT, inout float2 uvInd[6])
{
    ukTexcoordSets(O, U, uv0, uv1, uv2, uv3, wpos, tc, toonT);
    for (int K = 0; K < 6; K++)
    {
        int set = ukSelSet(O[UKO_TEX + K].x);
        uvInd[K] = ukSetUV(set < 0 ? 0 : set, tc);
    }
}

// ---------------------------------------------------------------- stage 2
// indirect (distortion / parallax) offsets -> final uv of texture slots 0..7 + bake uv.
//   indRaw[K]: raw sample of slot K at uvInd[K].
//   Nv, Tv: interpolated geometric normal/tangent; Vpos: view position (BotW view space).
void ukStage2(int4 O[UKO_COUNT], float4 U[UKU_COUNT], float2 tc[6], float4 indRaw[6], float3 Nv, float3 Tv, float3 Vpos,
              float2 uv1, inout float2 uvSlot[8], out float2 uvBake)
{
    float2 tcd[6];
    for (int i = 0; i < 6; i++) tcd[i] = tc[i];
    float3 e2s = normalize(Vpos);
    float depth = -Vpos.z;
    int wsMask = O[UKO_INDWS].x;
    for (int K = 0; K < 6; K++)
    {
        if (O[UKO_IND + K].x != 1) continue;
        int dset = ukSelSet(O[UKO_IND + K].y);
        if (dset < 0) continue;
        int dec = O[UKO_TEX + K].y;
        float4 t = ukTexDecode(indRaw[K], dec);
        float2 sc = U[UKU_INDSC + K].xy;
        float2 off = float2(0.0, 0.0);
        if (O[UKO_IND + K].z == 1)
        {
            // parallax: height (raw .x) along tangent-plane eye vector
            float3 Bp = cross(Nv, Tv);
            off = sc * t.x * float2(dot(Tv, e2s), dot(Bp, e2s));
        }
        else
        {
            float2 v = t.xy;
            if (O[UKO_IND + K].w == 1 && dec == 0) v = v * UK_DEC_S + float2(UK_DEC_B, UK_DEC_B);
            off = sc * v;
        }
        if (((wsMask / (1 << K)) % 2) == 1) off = off * (1.0 / (depth * U[UKU_DEPTH].x));
        for (int s2 = 0; s2 < 6; s2++)
            if (s2 == dset) tcd[s2] = tcd[s2] + off;
    }
    for (int s = 0; s < 8; s++)
    {
        int set = ukSelSet(O[UKO_TEX + s].x);
        uvSlot[s] = set < 0 ? float2(0.0, 0.0) : ukSetUV(set, tcd);
    }
    uvBake = uv1 * U[UKU_BAKE].xy + U[UKU_BAKE].zw;
}

// ---------------------------------------------------------------- normals
// tangent-space normal from the source table (uking_normal_color [+ normalmap2])
float3 ukDecodeNM(float4 nm, int decodeOpt)
{
    if (decodeOpt == 1) return ukNrmDecode(nm).xyz;
    return nm.xyz;
}

float3 ukNormalTS(int4 O[UKO_COUNT], float4 S[UKS_COUNT])
{
    int dec = O[UKO_NRM].z;
    float3 n = ukDecodeNM(S[ukSrcIndex(O[UKO_NRM].y)], dec);
    if (O[UKO_NRM].w == 1)
    {
        float r = ukChannel(S[ukSrcIndex(O[UKO_NRM2].y)], O[UKO_NRM2].z).x;
        float4 s2 = S[ukSrcIndex(O[UKO_NRM2].x)];
        if (O[UKO_NRM2].w == 0)
        {
            float3 n2 = ukDecodeNM(s2, dec);
            n = normalize(n + (n2 - n) * r);
        }
        else
        {
            float x2 = s2.x * UK_DEC_S + UK_DEC_B;
            float y2 = s2.y * UK_DEC_S + UK_DEC_B;
            n = normalize(float3(r * x2 + n.x, r * y2 + n.y, n.z));
        }
    }
    return n;
}

// unnormalized view-space normal after normal mapping (T, B, N = interpolated basis)
float3 ukNormalRaw(int4 O[UKO_COUNT], float4 S[UKS_COUNT], float3 Nv, float3 Tv, float3 Bv)
{
    if (O[UKO_NRM].x == 1)
    {
        float3 n = ukNormalTS(O, S);
        return Tv * n.x + Bv * n.y + Nv * n.z;
    }
    return normalize(Nv);
}

// inner light (source 511): a sphere (or capsule, line mode) light inside the object, seen through
// the surface with refraction (IOR 1.5).
//   Q: vector surface -> light (segment start); D: segment vector (zero for a point light)
//   r0/r1: radius at start/end; k: diffusivity; e2s: eye->surface; Nr: normal
float ukInnerLight(float3 Q, float3 D, float r0, float r1, float k, float3 e2s, float3 Nr)
{
    float dd = dot(D, D);
    float tc = dd > 0.0 ? saturate(-dot(D, Q) / dd) : 0.0;
    float rc = r0 + (r1 - r0) * tc;
    float3 Lc = Q + D * tc;
    float l2 = dot(Lc, Lc);
    float c = dot(e2s, Nr);
    float k2 = c * c * 2.25 - 1.25;
    float3 T = k2 < 0.0 ? float3(0.0, 0.0, 0.0) : Nr * (1.5 * (-c) - sqrt(max(k2, 0.0))) + e2s * 1.5;
    float tr = 0.0;
    if (dd > 0.0)
    {
        float a = dot(D, T);
        float b = dot(D, Q);
        float e = dot(Q, T);
        tr = saturate((-dot(Q, Q) * a + b * e) * (1.0 / (-dd * e + b * a)));
    }
    float3 Lv = D * tr + Q;
    float rr = r0 + (r1 - r0) * tr;
    float3 off = T * dot(T, Lv) - Lv;
    float f = saturate(rr * rsqrt(max(dot(off, off), 1e-20)));
    float3 Pn = off * f + Lv;
    float ct = saturate(dot(T, normalize(Pn)));
    float p2 = ct * ct;
    float p4 = p2 * p2;
    float p8 = p4 * p4;
    float att = saturate(rc * rc / l2);
    return (1.0 / (rc * rc)) * att * (k * saturate(dot(-Nr, Lc * rsqrt(l2))) + p8 * (1.0 - k));
}

// ---------------------------------------------------------------- combiners
void ukCombiners(int4 O[UKO_COUNT], inout float4 S[UKS_COUNT], int passB)
{
    for (int k = 0; k < 12; k++)
    {
        int4 cfg = O[UKO_CCFG + k];
        if (cfg.x != 1) continue;
        if (passB == 1 && cfg.w != 1) continue;
        int4 src = O[UKO_CSRC + k];
        int4 ch = O[UKO_CCH + k];
        float4 A = ukChannel(S[ukSrcIndex(src.x)], ch.x);
        float4 B = ukChannel(S[ukSrcIndex(src.y)], ch.y);
        float4 C = ukChannel(S[ukSrcIndex(src.z)], ch.z);
        float4 D = ukChannel(S[ukSrcIndex(src.w)], ch.w);
        float4 r = ukCalc(cfg.y, A, B, C, D);
        if (cfg.z == 1) r = saturate(r);
        S[UKS_COL + k] = r;
    }
}

// ---------------------------------------------------------------- stage 3
// Fill the source table, run the before-normal combiner pass, build the normal, evaluate the
// normal-dependent system values, and return the uv of slots that use procedural texcoords.
//   raw[s]: raw sample of slot s (0..7) at uvSlot[s];  vc: vertex colour
//   Nv/Tv/Bv: interpolated basis (BotW view space); Vpos: view position; Lvec/ldist: inner light
void ukStage3(int4 O[UKO_COUNT], float4 U[UKU_COUNT], float4 raw[8], float4 vc, float3 Nv, float3 Tv, float3 Bv,
              float3 Vpos, inout float4 S[UKS_COUNT], out float3 Nraw, inout float2 uvProc[8])
{
    for (int i = 0; i < UKS_COUNT; i++) S[i] = float4(0.0, 0.0, 0.0, 0.0);
    for (int s = 0; s < 8; s++) S[UKS_TEX + s] = ukTexDecode(raw[s], O[UKO_TEX + s].y);
    for (int c = 0; c < 6; c++) S[UKS_CC + c] = U[UKU_CC + c];
    for (int v = 0; v < 4; v++)
    {
        S[UKS_CV + v] = ukS4(U[UKU_CV][v]);
        S[UKS_CV + 4 + v] = ukS4(U[UKU_CV + 1][v]);
    }
    S[UKS_VEC] = U[UKU_VEC];
    S[UKS_VEC + 1] = U[UKU_VEC + 1];
    S[UKS_VC] = vc;
    S[UKS_K + 0] = ukS4(0.0);
    S[UKS_K + 1] = ukS4(0.5);
    S[UKS_K + 2] = ukS4(1.0);
    S[UKS_K + 3] = ukS4(2.0);
    S[UKS_K + 4] = ukS4(4.0);
    S[UKS_K + 5] = ukS4(0.25);
    S[UKS_K + 6] = ukS4(0.75);

    float3 e2s = normalize(Vpos);
    float depth = -Vpos.z;
    float3 L = U[UKU_LIGHT].xyz;
    // system values that do not need the final normal
    S[UKS_SYS + 0] = ukS4(U[UKU_DEPTH].y - depth);                       // 500 scene depth - pixel depth
    S[UKS_SYS + 2] = ukS4(saturate(1.0 + dot(Nv, e2s)));                  // 502 rim (geometric normal)
    S[UKS_SYS + 4] = ukS4(depth);                                         // 504 view depth
    S[UKS_SYS + 7] = ukS4(U[UKU_MISC].y);                                 // 507 exposure
    S[UKS_SYS + 8] = ukS4(1.0 / (depth * U[UKU_DEPTH].x));               // 508 inverse depth
    S[UKS_SYS + 9] = ukS4(U[UKU_MISC].z);                                 // 509 time
    S[UKS_SYS + 10] = ukS4(U[UKU_MISC].w);                                // 510 per-object random
    S[UKS_SYS + 15] = ukS4(dot(e2s, L));                                  // 515 V.L
    S[UKS_SCENE] = U[UKU_SCENE0];
    S[UKS_SCENE + 1] = U[UKU_SCENE1];

    // pass A: every enabled combiner, normal-dependent sources still 0
    ukCombiners(O, S, 0);

    Nraw = ukNormalRaw(O, S, Nv, Tv, Bv);
    if (O[UKO_NMOD].x == 1 && O[UKO_NRM].x == 1) Nraw = normalize(Nraw);   // modified basis path normalizes
    float3 N = normalize(Nraw);

    // procedural texcoords (proctexcoord mapping 0 = matcap, 3 = reflection sphere map, 1/2 = screen)
    float2 ptc[3];
    for (int p = 0; p < 3; p++)
    {
        int mp = p == 0 ? O[UKO_PTC].y : (p == 1 ? O[UKO_PTC].w : O[UKO_PTC2].y);
        float2 r = float2(N.x * 0.5 + 0.5, -N.y * 0.5 + 0.5);
        if (mp == 3)
        {
            float3 R = e2s - Nraw * (2.0 * dot(e2s, Nraw));
            r = float2(R.x * 0.5 + 0.5, -R.y * 0.5 + 0.5);
        }
        ptc[p] = r;
    }
    for (int s2 = 0; s2 < 8; s2++)
    {
        int sel = O[UKO_TEX + s2].x;
        uvProc[s2] = (sel >= 3 && sel <= 5) ? ptc[sel - 3] : float2(0.0, 0.0);
    }
}

// ---------------------------------------------------------------- stage 4
// Re-sampled procedural-texcoord slots, normal-dependent sources, after-normal combiner pass,
// final material outputs.
//   rawProc[s]: sample of slot s at uvProc[s] (only used when that slot selects a proctexcoord)
//   bakeRaw: sample of slot 4 (_t0) at uvBake
// outputs: albedo = G-buffer albedo (vertex AO / bake shadow premultiplied as BotW does)
void ukStage4(int4 O[UKO_COUNT], float4 U[UKU_COUNT], float4 rawProc[8], float4 bakeRaw, float3 Vpos,
              float3 innerQ, float3 innerD, float toonT, inout float4 S[UKS_COUNT], float3 Nraw,
              out float3 albedo, out float alpha, out float3 N, out float ao, out float3 emission,
              out float spec, out float metal, out float gloss, out float transmission)
{
    for (int s = 0; s < 8; s++)
    {
        int sel = O[UKO_TEX + s].x;
        if (sel >= 3 && sel <= 5) S[UKS_TEX + s] = ukTexDecode(rawProc[s], O[UKO_TEX + s].y);
    }
    float3 e2s = normalize(Vpos);
    float3 L = U[UKU_LIGHT].xyz;
    float ratio = U[UKU_LIGHT].w;
    S[UKS_SYS + 3] = ukS4(saturate(1.0 + dot(Nraw, e2s)));               // 503 rim (normal mapped)
    S[UKS_SYS + 13] = ukS4(-dot(L, Nraw));                                // 513 N.L
    float3 Lr = ratio != 0.0 ? L * (1.0 / ratio) : L;
    S[UKS_SYS + 14] = ukS4(-dot(Nraw, normalize(e2s + Lr)) * ratio);      // 514 N.H
    if (O[UKO_INNER0].x == 1)
    {
        float r0 = S[ukSrcIndex(O[UKO_INNER1].x)].x;
        float r1 = O[UKO_INNER0].z == 1 ? S[ukSrcIndex(O[UKO_INNER1].w)].x : r0;
        float kd = S[ukSrcIndex(O[UKO_INNER1].y)].x;
        float il = ukInnerLight(innerQ, innerD, r0, r1, kd, e2s, Nraw);
        S[UKS_SYS + 11] = ukS4(il);                                       // 511
    }

    // pass B: combiners flagged before_normal = 1 see the final normal
    ukCombiners(O, S, 1);

    N = normalize(Nraw);
    float4 al = S[ukSrcIndex(O[UKO_OUT0].x)];
    albedo = al.xyz;
    ao = 1.0;
    if (O[UKO_OUT1].x == 1)
    {
        ao = ukChannel(S[ukSrcIndex(O[UKO_OUT1].y)], O[UKO_OUT1].z).x;
        if (O[UKO_OUT1].y == 300)
        {
            float f = ao;
            if (O[UKO_OUT5].x == 1 && O[UKO_OUT5].y == 0) f = f * bakeRaw.x;
            albedo = albedo * f;
            ao = 1.0;                                   // vertex AO is baked into albedo
        }
    }
    emission = float3(0.0, 0.0, 0.0);
    if (O[UKO_OUT0].y == 1) emission = S[ukSrcIndex(O[UKO_OUT0].z)].xyz;
    alpha = ukChannel(S[ukSrcIndex(O[UKO_OUT2].x)], O[UKO_OUT2].y).w;
    metal = ukChannel(S[ukSrcIndex(O[UKO_OUT3].x)], O[UKO_OUT3].y).x;
    gloss = ukChannel(S[ukSrcIndex(O[UKO_OUT3].z)], O[UKO_OUT3].w).x;
    transmission = 0.0;
    if (O[UKO_OUT4].y == 1) transmission = ukChannel(S[ukSrcIndex(O[UKO_OUT4].z)], O[UKO_OUT4].w).x;
    spec = ukChannel(S[ukSrcIndex(O[UKO_OUT2].z)], O[UKO_OUT2].w).x;
    // toon-spec "glint" pattern on the specular mask (behave 0 generic, 2/10 keep it where metal)
    int behave = O[UKO_OUT0].w;
    if (O[UKO_OUT5].z == 1)
    {
        float fx = frac(toonT) - 0.5;
        float fy = frac(toonT * 0.7) - 0.5;
        float pt = saturate(1.0 - fx * fx) * saturate(1.0 - fy * fy);
        pt = pt * pt;
        if (behave == 0) spec = spec * pt;
        else if (behave == 2 || behave == 10) spec = spec * saturate(pt + metal);
    }
}

// ---------------------------------------------------------------- toon look (optional)
// BotW forward-pass lighting, simplified (no shadow maps / ambient LUT): albedo remap, hard
// N.L step, and the behave-1 ("toon chara") view-space specular glint.
//   L: direction the light travels (BotW view space); tp = (edge 0.4, sharpness 75, -, -)
float3 ukToonLight(int behave, float3 albedo, float3 N, float3 L, float3 sunColor, float3 ambient, float spec, float4 tp)
{
    float3 a = saturate(albedo * 1.0732098 - float3(0.000528556, 0.000528556, 0.000528556)) * 0.9317843
               + float3(0.0004925, 0.0004925, 0.0004925);
    float ndl = -dot(L, N);
    float stepv = saturate((saturate(ndl) - tp.x) * tp.y);
    float3 lit = a * (ambient + sunColor * stepv);
    if (behave == 1)
    {
        float3 H = normalize(float3(-1.5 * L.x, 0.6, 1.0));
        float p = exp2(exp(spec * spec + 3.0) * ukLog2(saturate(dot(N, H))));
        float st = saturate(saturate((p - 0.005) * 100.0) * 0.2 + saturate((p - 0.14) * 70.0) * 0.3) * spec * spec * 8.0;
        lit = lit + sunColor * (st * 3.0 * saturate(ndl + 0.9));
    }
    return lit;
}

// =====================================================================================
//  Vertex stage
// =====================================================================================

// gust lookup (BotW samples a system texture gsys_user1 here; procedural stand-in)
float ukWindLUT(float u, float s)
{
    float a = sin(u * 6.2831853) * 0.5 + sin(u * 14.5221 + 1.7) * 0.3 + sin(u * 25.949 + 0.4) * 0.2;
    return s * 0.15 * (0.6 + 0.4 * a);
}
#ifndef UK_WIND_LUT
#define UK_WIND_LUT(u, s) ukWindLUT(u, s)
#endif
#ifndef UK_LIE_MAP
#define UK_LIE_MAP(uv) float2(0.5, 0.5)
#endif

// Wind vertex animation (uking_enable_wind_vtx_transform), BotW world space / units.
//   W: world position, Nw: normalized world normal, Pl: local position, vc: vertex colour,
//   core: _c1 core offset (coreinfo; zero when unavailable), objPhase: frac(m00 + tx*0.4142136),
//   scaleY: |object Y axis| (edit scale).  Returns the displaced world position.
float3 ukWind(int4 O[UKO_COUNT], float4 U[UKU_COUNT], float3 W, float3 Nw, float3 Pl, float4 vc, float3 coreW,
              float coreX, float objPhase, float scaleY)
{
    if (O[UKO_WIND].x != 1) return W;
    int flags = O[UKO_WIND].z;
    bool lockN = (flags % 2) == 1;
    bool lie = ((flags / 2) % 2) == 1;
    bool height = ((flags / 4) % 2) == 1;
    bool coreinfo = ((flags / 8) % 2) == 1;
    bool scl = ((flags / 16) % 2) == 1;
    float4 e32 = U[UKU_ENV32];
    float4 e33 = U[UKU_ENV33];
    float intensity = U[UKU_WIND].x;
    float lieH = U[UKU_WIND].z;
    float w = height ? max(Pl.y, 0.0) : ukChannel(vc, O[UKO_WIND].y).x;
    float t4 = (e32.w + w * 0.5) * 100.0 * 3.1415;
    float flutter = saturate(e32.x - 0.5) * (sin(t4 * 7.0) * (sin(t4 * 5.0) * sin(t4 * 3.0))) * 0.05;
    float amp = (w * intensity + (lie ? saturate(w - lieH) : w) * flutter) * 20.0;
    float ph = objPhase + (coreinfo ? (coreX + Pl.x) * 0.02 : 0.0);
    float t8 = (e32.w + ph) * 3.0;
    float t9 = frac(t8) - 0.5;
    float t10 = e32.x * (max(t9, -t9) + 0.5);
    float t11 = t8 * 157.07964;
    float jit = saturate(t10 - 0.3) * 0.057144 * sin(t11 * 4.0) + saturate(min(t10, 1.0 - t10) * 2.0) * 0.02 * sin(t11);
    float3 Ws = coreinfo ? W + coreW : W;
    float base = ph * 0.22426553 + e32.w * 403.67795;
    float g1 = jit + UK_WIND_LUT((base - (Ws.x * e32.y + Ws.z * e32.z)) * 0.022295, e32.x);
    float g2 = jit + UK_WIND_LUT((base - (Ws.x * e33.y + Ws.z * e33.z)) * 0.022295, e32.x);
    float dx = amp * ((e33.y * g2 - e32.y * g1) * e33.x + e32.y * g1);
    float dz = amp * ((e33.z * g2 - e32.z * g1) * e33.x + e32.z * g1);
    float bend = ((g2 - g1) * e33.x + g1) * amp;
    float dy = -max(bend * bend * bend * 0.16, 0.0);
    float3 d = float3(dx, dy, dz);
    if (scl) d = d * scaleY;
    if (lockN)
    {
        float s = dot(Nw, d);
        d = d - Nw * min(s, 0.0);
    }
    if (lie)
    {
        // grass "lie down" map (BotW: gsys_depth_shadow_half); neutral (0.5) when unavailable
        float4 e34 = U[UKU_ENV34];
        float2 lm = UK_LIE_MAP(float2(e34.z + W.x * e34.x, e34.w + W.z * e34.y));
        float li = U[UKU_WIND].y * w * intensity;
        float lx = (lm.x * 2.0 - 1.0) * li;
        float lz = -(lm.y * 2.0 - 1.0) * li;
        d = d + float3(lx, -(lieH - sqrt(max(lieH * lieH - (lx * lx + lz * lz), 0.0))), lz);
    }
    return W + d;
}

// Normal modify type 1 (uking_modify_normal_type, foliage "sphere" normals):
//   mdir = const_vector.w * normalize(P - centre) in the same frame as Nv/Tv/Bv.
void ukModifyBasis(int4 O[UKO_COUNT], float3 mdir, inout float3 Nv, inout float3 Tv, inout float3 Bv)
{
    if (O[UKO_NMOD].x != 1 || O[UKO_NRM].x != 1) return;   // only applied together with a normal map
    float tw = dot(cross(Nv, Tv), Bv) >= 0.0 ? 1.0 : -1.0;
    float3 N2 = normalize(Nv + mdir);
    float3 Bp = cross(N2, Tv);
    Tv = cross(Bp, N2);
    Bv = Bp * tw;
    Nv = N2;
}

// Position modify type 1 (local displacement along the vertex normal).
//   vtxTex: sample of the vertex texture (_v0) at its texcoord.  Returns the local offset.
float3 ukVertexModify(int4 O[UKO_COUNT], float4 U[UKU_COUNT], float3 nLocal, float4 vc, float4 vtxTex)
{
    if (O[UKO_VMOD0].x != 1 || O[UKO_VMOD0].z == 1) return float3(0.0, 0.0, 0.0);
    float4 srcs[4];
    for (int i = 0; i < 4; i++)
    {
        int code = O[UKO_VMOD1][i];
        float4 v = ukConstSrc(code, U);
        if (code == 0) v = vtxTex;
        if (code == 300) v = vc;
        srcs[i] = ukChannel(v, O[UKO_VMOD2][i]);
    }
    float4 d = ukCalc(O[UKO_VMOD0].y, srcs[0], srcs[1], srcs[2], srcs[3]);
    return nLocal * d.xyz;
}

};
UKFn ukF;
int4 ukO[UKO_COUNT];
ukO[0] = int4(round(opt_texcoord0));
ukO[1] = int4(round(opt_texcoord1));
ukO[2] = int4(round(opt_texcoord2));
ukO[3] = int4(round(opt_texcoord3));
ukO[4] = int4(round(opt_texcoord4));
ukO[5] = int4(round(opt_texcoord5));
ukO[6] = int4(round(opt_texcoord_toon));
ukO[7] = int4(round(opt_proctexcoord01));
ukO[8] = int4(round(opt_proctexcoord2));
ukO[9] = int4(round(opt_texture0));
ukO[10] = int4(round(opt_texture1));
ukO[11] = int4(round(opt_texture2));
ukO[12] = int4(round(opt_texture3));
ukO[13] = int4(round(opt_texture4));
ukO[14] = int4(round(opt_texture5));
ukO[15] = int4(round(opt_texture6));
ukO[16] = int4(round(opt_texture7));
ukO[17] = int4(round(opt_indirect0));
ukO[18] = int4(round(opt_indirect1));
ukO[19] = int4(round(opt_indirect2));
ukO[20] = int4(round(opt_indirect3));
ukO[21] = int4(round(opt_indirect4));
ukO[22] = int4(round(opt_indirect5));
ukO[23] = int4(round(opt_indirect_world_scaling));
ukO[24] = int4(round(opt_color0_cfg));
ukO[25] = int4(round(opt_color1_cfg));
ukO[26] = int4(round(opt_color2_cfg));
ukO[27] = int4(round(opt_color3_cfg));
ukO[28] = int4(round(opt_color4_cfg));
ukO[29] = int4(round(opt_color5_cfg));
ukO[30] = int4(round(opt_color6_cfg));
ukO[31] = int4(round(opt_color7_cfg));
ukO[32] = int4(round(opt_color8_cfg));
ukO[33] = int4(round(opt_color9_cfg));
ukO[34] = int4(round(opt_color10_cfg));
ukO[35] = int4(round(opt_color11_cfg));
ukO[36] = int4(round(opt_color0_src));
ukO[37] = int4(round(opt_color1_src));
ukO[38] = int4(round(opt_color2_src));
ukO[39] = int4(round(opt_color3_src));
ukO[40] = int4(round(opt_color4_src));
ukO[41] = int4(round(opt_color5_src));
ukO[42] = int4(round(opt_color6_src));
ukO[43] = int4(round(opt_color7_src));
ukO[44] = int4(round(opt_color8_src));
ukO[45] = int4(round(opt_color9_src));
ukO[46] = int4(round(opt_color10_src));
ukO[47] = int4(round(opt_color11_src));
ukO[48] = int4(round(opt_color0_ch));
ukO[49] = int4(round(opt_color1_ch));
ukO[50] = int4(round(opt_color2_ch));
ukO[51] = int4(round(opt_color3_ch));
ukO[52] = int4(round(opt_color4_ch));
ukO[53] = int4(round(opt_color5_ch));
ukO[54] = int4(round(opt_color6_ch));
ukO[55] = int4(round(opt_color7_ch));
ukO[56] = int4(round(opt_color8_ch));
ukO[57] = int4(round(opt_color9_ch));
ukO[58] = int4(round(opt_color10_ch));
ukO[59] = int4(round(opt_color11_ch));
ukO[60] = int4(round(opt_normal));
ukO[61] = int4(round(opt_normal2));
ukO[62] = int4(round(opt_out0));
ukO[63] = int4(round(opt_out1));
ukO[64] = int4(round(opt_out2));
ukO[65] = int4(round(opt_out3));
ukO[66] = int4(round(opt_out4));
ukO[67] = int4(round(opt_out5));
ukO[68] = int4(round(opt_wind));
ukO[69] = int4(round(opt_vtxmod0));
ukO[70] = int4(round(opt_vtxmod1));
ukO[71] = int4(round(opt_vtxmod2));
ukO[72] = int4(round(opt_inner0));
ukO[73] = int4(round(opt_inner1));
ukO[74] = int4(round(opt_normal_modify));
float4 ukU[UKU_COUNT] = {float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0)};
ukU[0] = const_color0;
ukU[1] = const_color1;
ukU[2] = const_color2;
ukU[3] = const_color3;
ukU[4] = const_color4;
ukU[5] = const_color5;
ukU[6] = const_value0_3;
ukU[7] = const_value4_7;
ukU[8] = const_vector0;
ukU[9] = const_vector1;
ukU[10] = tex_srt0_m;
ukU[11] = tex_srt0_t;
ukU[12] = tex_srt1_m;
ukU[13] = tex_srt1_t;
ukU[14] = tex_srt2_m;
ukU[15] = tex_srt2_t;
ukU[16] = tex_srt3_m;
ukU[17] = tex_srt3_t;
ukU[18] = tex_srt4_m;
ukU[19] = tex_srt4_t;
ukU[20] = tex_srt5_m;
ukU[21] = tex_srt5_t;
ukU[22] = indirect_scale0;
ukU[23] = indirect_scale1;
ukU[24] = indirect_scale2;
ukU[25] = indirect_scale3;
ukU[26] = indirect_scale4;
ukU[27] = indirect_scale5;
ukU[28] = texture_array_index0_3;
ukU[29] = texture_array_index4_5;
ukU[30] = gsys_bake_st0;
ukU[31] = gsys_bake_st1;
ukU[34] = uking_wind;
float ukS = 1.0 / max(ukParams0.x, 0.000001);
ukU[UKU_MISC] = float4(ukParams0.y, ukParams0.z, ukTime * ukParams1.x, ukParams0.w);
ukU[UKU_LIGHT] = float4(ukLV.x, ukLV.y, -ukLV.z, 1.0);
ukU[UKU_DEPTH] = float4(1.0, 10000.0, 0.0, 0.0);
float3 ukVpos = float3(ukPV.x, ukPV.y, -ukPV.z) * ukS;
float3 ukNv = float3(ukNV.x, ukNV.y, -ukNV.z);
float3 ukTv = float3(ukTV.x, ukTV.y, -ukTV.z);
float3 ukBv = float3(ukBV.x, ukBV.y, -ukBV.z) * (ukParams1.w > 0.5 ? -1.0 : 1.0);
float3 ukWb = float3(ukPW.x, ukPW.z, ukPW.y) * ukS;
float4 ukVc = Parameters.VertexColor;
float3 ukQ0 = float3(ukQ0V.x, ukQ0V.y, -ukQ0V.z) * ukS;
float3 ukQ1 = float3(ukQ1V.x, ukQ1V.y, -ukQ1V.z) * ukS;
if (ukO[UKO_NMOD].x == 1)
{
    float4 ukCv = ukF.ukConstSrc(ukO[UKO_NMOD].y, ukU);
    float3 ukQc = ukO[UKO_NMOD].y == 115 ? ukQ1 : ukQ0;
    ukF.ukModifyBasis(ukO, ukCv.w * normalize(-ukQc), ukNv, ukTv, ukBv);
}
float3 ukInQ = ukO[UKO_INNER0].w == 115 ? ukQ1 : ukQ0;
float3 ukInD = float3(0.0, 0.0, 0.0);
if (ukO[UKO_INNER0].z == 1) ukInD = (ukO[UKO_INNER1].z == 114 ? ukQ0 : ukQ1) - ukInQ;
float2 ukTc[6] = {float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0)}; float ukToonT = 0.0; float2 ukUvInd[6] = {float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0)};
ukF.ukStage1(ukO, ukU, ukUV0, ukUV1, ukUV2, ukUV3, ukWb, ukTc, ukToonT, ukUvInd);
float4 ukInd[6] = {float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0)};
UK_SLOT(0, ukUvInd[0], ukInd[0])
UK_SLOT(1, ukUvInd[1], ukInd[1])
UK_SLOT(2, ukUvInd[2], ukInd[2])
UK_SLOT(3, ukUvInd[3], ukInd[3])
UK_SLOT(4, ukUvInd[4], ukInd[4])
UK_SLOT(5, ukUvInd[5], ukInd[5])
float2 ukUvSlot[8] = {float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0)}; float2 ukUvBake = float2(0.0, 0.0);
ukF.ukStage2(ukO, ukU, ukTc, ukInd, ukNv, ukTv, ukVpos, ukUV1, ukUvSlot, ukUvBake);
float4 ukRaw[8] = {float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0)};
UK_SLOT(0, ukUvSlot[0], ukRaw[0])
UK_SLOT(1, ukUvSlot[1], ukRaw[1])
UK_SLOT(2, ukUvSlot[2], ukRaw[2])
UK_SLOT(3, ukUvSlot[3], ukRaw[3])
UK_SLOT(4, ukUvSlot[4], ukRaw[4])
UK_SLOT(5, ukUvSlot[5], ukRaw[5])
UK_SLOT(ukO[UKO_TEX + 6].z, ukUvSlot[6], ukRaw[6])
UK_SLOT(ukO[UKO_TEX + 7].z, ukUvSlot[7], ukRaw[7])
float4 ukBake = float4(0.0, 0.0, 0.0, 0.0);
UK_SLOT(4, ukUvBake, ukBake)
float4 ukS3[UKS_COUNT] = {float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0)};
float3 ukNraw = float3(0.0, 0.0, 1.0); float2 ukUvProc[8] = {float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0), float2(0.0, 0.0)};
ukF.ukStage3(ukO, ukU, ukRaw, ukVc, ukNv, ukTv, ukBv, ukVpos, ukS3, ukNraw, ukUvProc);
float4 ukRawP[8] = {float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0), float4(0.0, 0.0, 0.0, 0.0)};
float2 ukPdx0 = ddx(ukUvProc[0]); float2 ukPdy0 = ddy(ukUvProc[0]);
if (ukO[UKO_TEX + 0].x >= 3 && ukO[UKO_TEX + 0].x <= 5) UK_SLOTG(0, ukUvProc[0], ukPdx0, ukPdy0, ukRawP[0])
float2 ukPdx1 = ddx(ukUvProc[1]); float2 ukPdy1 = ddy(ukUvProc[1]);
if (ukO[UKO_TEX + 1].x >= 3 && ukO[UKO_TEX + 1].x <= 5) UK_SLOTG(1, ukUvProc[1], ukPdx1, ukPdy1, ukRawP[1])
float2 ukPdx2 = ddx(ukUvProc[2]); float2 ukPdy2 = ddy(ukUvProc[2]);
if (ukO[UKO_TEX + 2].x >= 3 && ukO[UKO_TEX + 2].x <= 5) UK_SLOTG(2, ukUvProc[2], ukPdx2, ukPdy2, ukRawP[2])
float2 ukPdx3 = ddx(ukUvProc[3]); float2 ukPdy3 = ddy(ukUvProc[3]);
if (ukO[UKO_TEX + 3].x >= 3 && ukO[UKO_TEX + 3].x <= 5) UK_SLOTG(3, ukUvProc[3], ukPdx3, ukPdy3, ukRawP[3])
float2 ukPdx4 = ddx(ukUvProc[4]); float2 ukPdy4 = ddy(ukUvProc[4]);
if (ukO[UKO_TEX + 4].x >= 3 && ukO[UKO_TEX + 4].x <= 5) UK_SLOTG(4, ukUvProc[4], ukPdx4, ukPdy4, ukRawP[4])
float2 ukPdx5 = ddx(ukUvProc[5]); float2 ukPdy5 = ddy(ukUvProc[5]);
if (ukO[UKO_TEX + 5].x >= 3 && ukO[UKO_TEX + 5].x <= 5) UK_SLOTG(5, ukUvProc[5], ukPdx5, ukPdy5, ukRawP[5])
float2 ukPdx6 = ddx(ukUvProc[6]); float2 ukPdy6 = ddy(ukUvProc[6]);
if (ukO[UKO_TEX + 6].x >= 3 && ukO[UKO_TEX + 6].x <= 5) UK_SLOTG(ukO[UKO_TEX + 6].z, ukUvProc[6], ukPdx6, ukPdy6, ukRawP[6])
float2 ukPdx7 = ddx(ukUvProc[7]); float2 ukPdy7 = ddy(ukUvProc[7]);
if (ukO[UKO_TEX + 7].x >= 3 && ukO[UKO_TEX + 7].x <= 5) UK_SLOTG(ukO[UKO_TEX + 7].z, ukUvProc[7], ukPdx7, ukPdy7, ukRawP[7])
float3 ukAlb; float ukAlpha; float3 ukN; float ukAo; float3 ukEm; float ukSpec; float ukMetal; float ukGloss; float ukTrans;
ukF.ukStage4(ukO, ukU, ukRawP, ukBake, ukVpos, ukInQ, ukInD, ukToonT, ukS3, ukNraw,
           ukAlb, ukAlpha, ukN, ukAo, ukEm, ukSpec, ukMetal, ukGloss, ukTrans);
int ukBehave = ukO[UKO_OUT0].w;
float ukMask = ukAlpha - ukParams0.y + 0.5;
float3 ukLit = ukF.ukToonLight(ukBehave, ukAlb * ukAo, ukN, ukU[UKU_LIGHT].xyz, ukSun.xyz, ukAmb.xyz, saturate(ukSpec), ukToon);
return float4(ukLit + ukEm * ukParams1.z, ukMask);

}