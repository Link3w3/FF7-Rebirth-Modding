namespace S_lass_Thin_Environment {
using namespace cpuglsl;
static D _4299;
static D _4295;
static D _4296;
static D _4297;
static UBO& View = ubo("View");
static UBO& Primitive = ubo("Primitive");
static UBOF& TranslucentBasePass = uboF("b0_2");
static UBO& TranslucentBasePass_2 = ubo("b0_2");
static Tex3D View_SpatiotemporalBlueNoiseVolumeTexture{texid("View_SpatiotemporalBlueNoiseVolumeTexture")};
static TexBufI TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileIndices{texid("TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileIndices")};
static TexBufF TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthRanges{texid("TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthRanges")};
static TexBufU TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowLoadedTileData{texid("TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowLoadedTileData")};
static TexBufU TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileData{texid("TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileData")};
static TexBufF TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer{texid("TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer")};
static TexBufU TranslucentBasePass_Shared_Forward_NumCulledLightsGrid{texid("TranslucentBasePass_Shared_Forward_NumCulledLightsGrid")};
static Tex2D TranslucentBasePass_Shared_Fog_FarIntegratedScatteringTexture{texid("TranslucentBasePass_Shared_Fog_FarIntegratedScatteringTexture")};
static Tex3D TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeATexture{texid("TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeATexture")};
static Tex3D TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeBTexture{texid("TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeBTexture")};
static Tex2D TranslucentBasePass_HZBTexture{texid("TranslucentBasePass_HZBTexture")};
static Tex2D TranslucentBasePass_PrevSceneColor{texid("TranslucentBasePass_PrevSceneColor")};
static Tex3D TranslucentBasePass_TranslucencyLightingVolumeEnvironmentA{texid("TranslucentBasePass_TranslucencyLightingVolumeEnvironmentA")};
static Tex2D Material_Texture2D_0{texid("junk:T_Color")};
static Tex2D Material_Texture2D_1{texid("junk:T_Metallic")};
static Tex2D Material_Texture2D_2{texid("junk:T_Normal")};
static Tex2D Material_Texture2D_3{texid("junk:T_Roughness")};
static Tex2D Material_Texture2D_4{texid("junk:T_Occlusion")};
static Tex2D Material_Texture2D_7{texid("junk:T_Opacity")};
static Tex2D Material_Texture2D_17{texid("junk:T_Muddiness")};
static Tex2D Material_Texture2D_18{texid("junk:T_Transparency")};
static Tex2D Material_Texture2D_19{texid("junk:T_TransparencyCoefficient")};
static Tex2D Material_Texture2D_20{texid("junk:T_Transmittance")};
static Tex2D Material_Texture2D_21{texid("junk:T_TransmittanceCoefficient")};
static Tex2D Material_Texture2D_23{texid("junk:T_Thinness")};
static Tex2D ForwardLightProfileTextures[64];
static Tex2D ShadowMaps[64];
static Samp View_SharedPointClampedSampler{texid("View_SharedPointClampedSampler")};
static Samp View_SharedBilinearWrappedSampler{texid("View_SharedBilinearWrappedSampler")};
static Samp View_SharedBilinearClampedSampler{texid("View_SharedBilinearClampedSampler")};
static Samp View_SharedAnisotropic4XWrappedSampler{texid("View_SharedAnisotropic4XWrappedSampler")};
static Samp View_SharedAnisotropic4XClampedSampler{texid("View_SharedAnisotropic4XClampedSampler")};
static vec4 TEXCOORD_10;
static vec4 TEXCOORD_11;
static vec4 TEXCOORD;
static D CONSTANT_CONTEXT;
static vec4 SV_Target;
static vec4 SV_Target_1;
static bool discard_state;









void discard_cond(bool _4285)
{
    if (_4285)
    {
        discard_state = true;
    }
}

void discard_exit()
{
    if (discard_state)
    {
        { g_discarded = true; return; }
    }
}

void run()
{
    discard_state = false;
    D _102 = 1.0 / gl_FragCoord.w;
    D _221 = fma(gl_FragCoord.z, View._m0[54u].w, fma(gl_FragCoord.y, View._m0[53u].w, View._m0[52u].w * gl_FragCoord.x)) + View._m0[55u].w;
    D _222 = (fma(gl_FragCoord.z, View._m0[54u].x, fma(gl_FragCoord.y, View._m0[53u].x, View._m0[52u].x * gl_FragCoord.x)) + View._m0[55u].x) / _221;
    D _223 = (fma(gl_FragCoord.z, View._m0[54u].y, fma(gl_FragCoord.y, View._m0[53u].y, View._m0[52u].y * gl_FragCoord.x)) + View._m0[55u].y) / _221;
    D _224 = (fma(gl_FragCoord.z, View._m0[54u].z, fma(gl_FragCoord.y, View._m0[53u].z, View._m0[52u].z * gl_FragCoord.x)) + View._m0[55u].z) / _221;
    D _225 = _222 - View._m0[78u].x;
    D _226 = _223 - View._m0[78u].y;
    D _227 = _224 - View._m0[78u].z;
    D _232 = inversesqrt(dot(vec3(_222, _223, _224), vec3(_222, _223, _224)));
    D _233 = _232 * _222;
    D _234 = _232 * _223;
    D _235 = _232 * _224;
    D _236 = (-0.0) - _233;
    D _238 = (-0.0) - _234;
    D _239 = (-0.0) - _235;
    vec4 _257 = texelFetch(View_SpatiotemporalBlueNoiseVolumeTexture, ivec3_(uvec3(uint(int(gl_FragCoord.x)) & 127u, uint(int(gl_FragCoord.y)) & 127u, ((floatBitsToUint(View._m0[175u]).x & 7u) + uint(roundEven(CONSTANT_CONTEXT))) & 63u)), int(0u));
    D _260 = _257.x;
    D _261 = _257.y;
    vec4 _267 = texture(sampler2D(Material_Texture2D_0, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _275 = texture(sampler2D(Material_Texture2D_1, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _280 = texture(sampler2D(Material_Texture2D_2, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _287 = (_280.x * 2.0) + (-1.0);
    D _289 = (_280.y * 2.0) + (-1.0);
    D _296 = sqrt(spvNMax(0.0, 1.0 - dot(vec2(_287, _289), vec2(_287, _289))));
    D _300 = inversesqrt(dot(vec3(_287, _289, _296), vec3(_287, _289, _296)));
    D _301 = _300 * _287;
    D _302 = _300 * _289;
    D _303 = _300 * _296;
    vec4 _306 = texture(sampler2D(Material_Texture2D_3, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _311 = texture(sampler2D(Material_Texture2D_4, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _316 = texture(sampler2D(Material_Texture2D_7, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _322 = vec4(g_R.Muddiness.x, g_R.Muddiness.y, g_R.Muddiness.z, 0.0);
    vec4 _329 = texture(sampler2D(Material_Texture2D_18, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _334 = texture(sampler2D(Material_Texture2D_19, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _344 = g_R.TransparencyLog2;
    D _345 = exp2(_344);
    vec4 _348 = texture(sampler2D(Material_Texture2D_20, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _355 = texture(sampler2D(Material_Texture2D_21, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _360 = 1.0 / spvNMax(9.9999999747524270787835121154785e-07, _355.x * 100.0);
    D _367 = g_R.TransmittanceLog2.x;
    D _368 = g_R.TransmittanceLog2.y;
    D _369 = g_R.TransmittanceLog2.z;
    vec4 _375 = vec4(g_R.Thickness);
    D _381 = inversesqrt(dot(vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z), vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z)));
    D _382 = _381 * g_R.Normal.x;
    D _383 = _381 * g_R.Normal.y;
    D _384 = _381 * g_R.Normal.z;
    D _387 = fma(_384, TEXCOORD_11.x, fma(_383, ((TEXCOORD_10.z * TEXCOORD_11.y) - (TEXCOORD_10.y * TEXCOORD_11.z)) * TEXCOORD_11.w, _382 * TEXCOORD_10.x));
    D _390 = fma(_384, TEXCOORD_11.y, fma(_383, ((TEXCOORD_10.x * TEXCOORD_11.z) - (TEXCOORD_10.z * TEXCOORD_11.x)) * TEXCOORD_11.w, _382 * TEXCOORD_10.y));
    D _393 = fma(_384, TEXCOORD_11.z, fma(_383, ((TEXCOORD_10.y * TEXCOORD_11.x) - (TEXCOORD_10.x * TEXCOORD_11.y)) * TEXCOORD_11.w, _382 * TEXCOORD_10.z));
    D _397 = inversesqrt(dot(vec3(_387, _390, _393), vec3(_387, _390, _393)));
    D _398 = _397 * _387;
    D _399 = _397 * _390;
    D _400 = _397 * _393;
    bool _413;
    if (Primitive._m0[27u].w > ((_257.w * 0.99609375) + 0.001953125))
    {
        _413 = ((_260 * 0.99609375) + 0.001953125) < 1.0;
    }
    else
    {
        _413 = false;
    }
    (void)((_413 ? 1.0 : (-1.0)) < 0.0);
    D _419 = spvNClamp(g_R.BaseColor.x, 0.0, 1.0);
    D _420 = spvNClamp(g_R.BaseColor.y, 0.0, 1.0);
    D _421 = spvNClamp(g_R.BaseColor.z, 0.0, 1.0);
    D _422 = spvNClamp(g_R.Metallic, 0.0, 1.0);
    D _423 = spvNClamp(g_R.Roughness, 0.0, 1.0);
    D _424 = spvNClamp(g_R.AO, 0.0, 1.0);
    D _425 = spvNClamp(g_R.Opacity, 0.0, 1.0);
    D _427 = dFdxFine(_398);
    D _428 = dFdxFine(_399);
    D _429 = dFdxFine(_400);
    D _433 = dFdyFine(_398);
    D _434 = dFdyFine(_399);
    D _435 = dFdyFine(_400);
    D _446 = sqrt(spvNClamp(spvNMin((dot(vec3(_433, _434, _435), vec3(_433, _434, _435)) + dot(vec3(_427, _428, _429), vec3(_427, _428, _429))) * 0.15915493667125701904296875, 0.180000007152557373046875) + (_423 * _423), 0.0, 1.0));
    D _447 = 1.0 - _422;
    D _448 = _447 * _419;
    D _449 = _447 * _420;
    D _450 = _447 * _421;
    D _455 = _422 * (_419 + (-0.0400000028312206268310546875));
    D _456 = _422 * (_420 + (-0.0400000028312206268310546875));
    D _457 = _422 * (_421 + (-0.0400000028312206268310546875));
    D _458 = _455 + 0.0400000028312206268310546875;
    D _460 = _456 + 0.0400000028312206268310546875;
    D _461 = _457 + 0.0400000028312206268310546875;
    D _468 = spvNClamp(D(View._m0[220u].x > 1.0), 0.0, 1.0);
    D _496 = ((exp2(log2(spvNMax(0.0, _455 + 0.020000003278255462646484375) * 1.020408153533935546875) * 1.39999997615814208984375) - _458) * _468) + _458;
    D _497 = ((exp2(log2(spvNMax(0.0, _456 + 0.020000003278255462646484375) * 1.020408153533935546875) * 1.39999997615814208984375) - _460) * _468) + _460;
    D _498 = ((exp2(log2(spvNMax(0.0, _457 + 0.020000003278255462646484375) * 1.020408153533935546875) * 1.39999997615814208984375) - _461) * _468) + _461;
    D _503 = (_496 * 0.449999988079071044921875) + _448;
    D _504 = (_497 * 0.449999988079071044921875) + _449;
    D _505 = (_498 * 0.449999988079071044921875) + _450;
    D _512 = dot(vec3(_398, _399, _400), vec3(_236, _238, _239));
    D _518 = (_512 * _398) + _233;
    D _519 = (_512 * _399) + _234;
    D _520 = (_512 * _400) + _235;
    D _524 = abs(_512);
    D _528 = (_518 * 2.0) + (_524 * _398);
    D _529 = (_519 * 2.0) + (_524 * _399);
    D _530 = (_520 * 2.0) + (_524 * _400);
    D _534 = inversesqrt(dot(vec3(_528, _529, _530), vec3(_528, _529, _530)));
    D _535 = _528 * _534;
    D _536 = _529 * _534;
    D _537 = _530 * _534;
    D _538 = spvNMax(9.9999997473787516355514526367188e-06, _524);
    D _550 = 1.0 - _446;
    D _564 = ((spvNMin(_550 * _550, exp2(_538 * (-9.27999973297119140625))) * _550) + (0.0425000004470348358154296875 - (_446 * 0.0274999998509883880615234375))) * 1.03999996185302734375;
    D _570 = 1.0 - spvNClamp((((_446 * 0.02199999988079071044921875) + (-0.039999999105930328369140625)) + _564) + (((1.03999996185302734375 - (_446 * 0.572000026702880859375)) - _564) * 0.0400000028312206268310546875), 0.0, 1.0);
    D _571 = _570 * _570;
    D _572 = spvNMax(0.001000000047497451305389404296875, (1.0 / spvNMax(0.0333333350718021392822265625, _538)) * _375.x);
    D _575 = log2(spvNMax(0.0, _345));
    D _577 = exp2(_575 * _572);
    D _581 = log2(spvNMax(0.0, exp2(_367)));
    D _582 = log2(spvNMax(0.0, exp2(_368)));
    D _583 = log2(spvNMax(0.0, exp2(_369)));
    D _587 = exp2(_581 * _572);
    D _588 = exp2(_582 * _572);
    D _589 = exp2(_583 * _572);
    D _591 = exp2(_575 * 0.001000000047497451305389404296875);
    D _598 = 1.0 - _425;
    D _600 = (_571 * _598) * _577;
    D _603 = ((_600 * _587) * _591) * exp2(_581 * 0.001000000047497451305389404296875);
    D _606 = ((_600 * _588) * _591) * exp2(_582 * 0.001000000047497451305389404296875);
    D _609 = ((_600 * _589) * _591) * exp2(_583 * 0.001000000047497451305389404296875);
    D _616 = spvNMax(0.039999999105930328369140625, _446);
    D _632 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_616 * _538) + 0.02669160068035125732421875) / (_538 + 0.4664950072765350341796875)) * exp2(((1.0 / _616) * _538) * log2(_616)), 0.0, 1.0));
    D _633 = 1.0 - _538;
    D _634 = _633 * _633;
    D _647 = _634 * _634;
    D _649 = (_647 * _633) * exp2(log2((exp2((_616 * 4.7702999114990234375) * log2(_538)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _616);
    D _652 = (1.0 / _632) * (1.0 - _632);
    D _659 = _632 - _649;
    D _666 = ((_652 * _496) + 1.0) * ((_659 * _496) + _649);
    D _667 = ((_652 * _497) + 1.0) * ((_659 * _497) + _649);
    D _668 = ((_652 * _498) + 1.0) * ((_659 * _498) + _649);
    D _674 = spvNClamp(1.0 - dot(vec3(_666, _667, _668), vec3(0.3333333432674407958984375)), 0.0, 1.0);
    D _688 = spvNClamp((_424 + (-1.0)) + exp2(log2(_538 + _424) * exp2((-1.0) - (_446 * 16.0))), 0.0, 1.0);
    D _748;
    D _750;
    D _752;
    D _754;
    D _756;
    D _758;
    D _760;
    D _762;
    D _764;
    if (floatBitsToUint(TranslucentBasePass_2._m0[0u]).z == 0u)
    {
        _748 = 0.0;
        _750 = 0.0;
        _752 = 0.0;
        _754 = 0.0;
        _756 = 0.0;
        _758 = 0.0;
        _760 = 0.0;
        _762 = 0.0;
        _764 = 0.0;
    }
    else
    {
        D _1198;
        uint _779;
        bool _780;
        for (;;)
        {
            _779 = floatBitsToUint(TranslucentBasePass_2._m0[7u]).z;
            _780 = _779 == 0u;
            if (!_780)
            {
                uint _1363;
                uint _1266 = 0u;
                for (;;)
                {
                    if (_102 < TranslucentBasePass._m0[_1266 + 32u])
                    {
                        _1363 = _1266;
                        break;
                    }
                    else
                    {
                        uint _1267 = _1266 + 1u;
                        if (_1267 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                        {
                            _1266 = _1267;
                            continue;
                        }
                        else
                        {
                            _1363 = _779;
                            break;
                        }
                    }
                }
                if (_1363 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                {
                    uint _1714 = _1363 << 2u;
                    uint _1715 = _1714 + 9u;
                    uint _1722 = _1714 + 10u;
                    uint _1729 = _1714 + 11u;
                    uint _1736 = _1714 + 12u;
                    uint _1743 = _1363 + 25u;
                    D _1769 = fma(_227, TranslucentBasePass_2._m0[_1729].z, fma(_226, TranslucentBasePass_2._m0[_1722].z, TranslucentBasePass_2._m0[_1715].z * _225)) + TranslucentBasePass_2._m0[_1736].z;
                    D _1773 = fma(_227, TranslucentBasePass_2._m0[_1729].w, fma(_226, TranslucentBasePass_2._m0[_1722].w, TranslucentBasePass_2._m0[_1715].w * _225)) + TranslucentBasePass_2._m0[_1736].w;
                    D _1774 = (fma(_227, TranslucentBasePass_2._m0[_1729].x, fma(_226, TranslucentBasePass_2._m0[_1722].x, TranslucentBasePass_2._m0[_1715].x * _225)) + TranslucentBasePass_2._m0[_1736].x) / _1773;
                    D _1775 = (fma(_227, TranslucentBasePass_2._m0[_1729].y, fma(_226, TranslucentBasePass_2._m0[_1722].y, TranslucentBasePass_2._m0[_1715].y * _225)) + TranslucentBasePass_2._m0[_1736].y) / _1773;
                    bool _1782 = (_1775 <= TranslucentBasePass_2._m0[_1743].w) && ((_1774 <= TranslucentBasePass_2._m0[_1743].z) && ((_1774 >= TranslucentBasePass_2._m0[_1743].x) && (_1775 >= TranslucentBasePass_2._m0[_1743].y)));
                    D _1199;
                    if (_1782)
                    {
                        D _2139 = dFdyFine(_1774);
                        D _2140 = dFdyFine(_1775);
                        D _2141 = dFdyFine(_1769);
                        D _2142 = dFdxFine(_1774);
                        D _2143 = dFdxFine(_1775);
                        D _2144 = dFdxFine(_1769);
                        D _2147 = (_2143 * _2141) - (_2144 * _2140);
                        D _2150 = (_2144 * _2139) - (_2142 * _2141);
                        D _2153 = (_2142 * _2140) - (_2143 * _2139);
                        D _2163 = 1.0 / spvNMax(abs(_2153), sqrt(((_2150 * _2150) + (_2153 * _2153)) + (_2147 * _2147)) * 0.100000001490116119384765625);
                        D _2169 = D(int(uint(_2153 > 0.0) - uint(_2153 < 0.0)));
                        D _2170 = _2147 * TranslucentBasePass_2._m0[29u].z;
                        D _2172 = (_2170 * _2163) * _2169;
                        D _2173 = _2150 * TranslucentBasePass_2._m0[29u].w;
                        D _2175 = (_2173 * _2163) * _2169;
                        D _2767;
                        D _2769;
                        if (dot(vec2(_2147, _2150), vec2(_2147, _2150)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2767 = 0.0;
                            _2769 = 0.0;
                        }
                        else
                        {
                            D _3137 = (-0.0) - _2147;
                            D _3138 = (-0.0) - _2150;
                            D _3142 = inversesqrt(dot(vec2(_3137, _3138), vec2(_3137, _3138)));
                            _2767 = _3142 * _3137;
                            _2769 = _3142 * _3138;
                        }
                        D _2771 = _261 + (-0.5);
                        D _2776 = _260 + 0.5;
                        D _2779 = ((_2769 * _2771) + (_1774 * TranslucentBasePass_2._m0[29u].x)) + (_2767 * _2776);
                        D _2782 = ((_2767 * _2771) + (_1775 * TranslucentBasePass_2._m0[29u].y)) + (_2769 * _2776);
                        D _2783 = _2779 + (-0.5);
                        D _2784 = _2782 + (-0.5);
                        D _2785 = trunc(_2783);
                        D _2786 = trunc(_2784);
                        D _2787 = _2783 - _2785;
                        D _2788 = _2784 - _2786;
                        D _2789 = _2785 * TranslucentBasePass_2._m0[29u].z;
                        D _2790 = _2786 * TranslucentBasePass_2._m0[29u].w;
                        D _2793 = (_2785 + (-0.5)) - _2779;
                        D _2794 = (_2786 + (-0.5)) - _2782;
                        D _2795 = dot(vec2(_2793, _2794), vec2(_2172, _2175));
                        D _2798 = _2795 + _2175;
                        D _2801 = _2169 * (_2163 * (_2173 + _2170));
                        D _2802 = _2801 + _2795;
                        D _2803 = _2795 + _2172;
                        vec4 _2809 = textureGather((sampler2D(ShadowMaps[_1363 + 0u], View_SharedPointClampedSampler)), vec2(_2789, _2790));
                        D _2810 = _2809.x;
                        D _2811 = _2809.y;
                        D _2812 = _2809.z;
                        D _2813 = _2809.w;
                        D _2850 = 1.525902189314365386962890625e-05 - _1769;
                        D _2881 = (_2785 + 1.5) - _2779;
                        D _2882 = dot(vec2(_2881, _2794), vec2(_2172, _2175));
                        D _2885 = _2882 + _2175;
                        D _2886 = _2801 + _2882;
                        D _2887 = _2882 + _2172;
                        vec4 _2889 = textureGatherOffset((sampler2D(ShadowMaps[_1363 + 0u], View_SharedPointClampedSampler)), vec2(_2789, _2790), ivec2(2, 0));
                        D _2890 = _2889.x;
                        D _2891 = _2889.y;
                        D _2892 = _2889.z;
                        D _2893 = _2889.w;
                        D _2959 = (_2786 + 1.5) - _2782;
                        D _2960 = dot(vec2(_2793, _2959), vec2(_2172, _2175));
                        D _2963 = _2960 + _2175;
                        D _2964 = _2801 + _2960;
                        D _2965 = _2960 + _2172;
                        vec4 _2967 = textureGatherOffset((sampler2D(ShadowMaps[_1363 + 0u], View_SharedPointClampedSampler)), vec2(_2789, _2790), ivec2(0, 2));
                        D _2968 = _2967.x;
                        D _2969 = _2967.y;
                        D _2970 = _2967.z;
                        D _2971 = _2967.w;
                        D _3036 = dot(vec2(_2881, _2959), vec2(_2172, _2175));
                        D _3039 = _3036 + _2175;
                        D _3040 = _2801 + _3036;
                        D _3041 = _3036 + _2172;
                        vec4 _3043 = textureGatherOffset((sampler2D(ShadowMaps[_1363 + 0u], View_SharedPointClampedSampler)), vec2(_2789, _2790), ivec2(2));
                        D _3044 = _3043.x;
                        D _3045 = _3043.y;
                        D _3046 = _3043.z;
                        D _3047 = _3043.w;
                        D _3112 = 1.0 - _2787;
                        vec4 _3135 = vec4((((((_2813 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2850 + _2813) + (spvNMin(abs(_2795), 0.0) * D(int(uint(_2795 > 0.0) - uint(_2795 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3112) + ((_2812 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2850 + _2812) + (spvNMin(abs(_2803), 0.0) * D(int(uint(_2803 > 0.0) - uint(_2803 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2893 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2850 + _2893) + (spvNMin(abs(_2882), 0.0) * D(int(uint(_2882 > 0.0) - uint(_2882 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2892 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2850 + _2892) + (spvNMin(abs(_2887), 0.0) * D(int(uint(_2887 > 0.0) - uint(_2887 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2787), (((((_2810 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2850 + _2810) + (spvNMin(abs(_2798), 0.0) * D(int(uint(_2798 > 0.0) - uint(_2798 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3112) + ((_2811 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2850 + _2811) + (spvNMin(abs(_2802), 0.0) * D(int(uint(_2802 > 0.0) - uint(_2802 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2890 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2850 + _2890) + (spvNMin(abs(_2885), 0.0) * D(int(uint(_2885 > 0.0) - uint(_2885 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2891 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2850 + _2891) + (spvNMin(abs(_2886), 0.0) * D(int(uint(_2886 > 0.0) - uint(_2886 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2787), (((((_2971 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2850 + _2971) + (spvNMin(abs(_2960), 0.0) * D(int(uint(_2960 > 0.0) - uint(_2960 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3112) + ((_2970 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2850 + _2970) + (spvNMin(abs(_2965), 0.0) * D(int(uint(_2965 > 0.0) - uint(_2965 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3047 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2850 + _3047) + (spvNMin(abs(_3036), 0.0) * D(int(uint(_3036 > 0.0) - uint(_3036 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3046 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2850 + _3046) + (spvNMin(abs(_3041), 0.0) * D(int(uint(_3041 > 0.0) - uint(_3041 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2787), (((((_2968 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2850 + _2968) + (spvNMin(abs(_2963), 0.0) * D(int(uint(_2963 > 0.0) - uint(_2963 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3112) + ((_2969 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2850 + _2969) + (spvNMin(abs(_2964), 0.0) * D(int(uint(_2964 > 0.0) - uint(_2964 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3044 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2850 + _3044) + (spvNMin(abs(_3039), 0.0) * D(int(uint(_3039 > 0.0) - uint(_3039 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3045 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2850 + _3045) + (spvNMin(abs(_3040), 0.0) * D(int(uint(_3040 > 0.0) - uint(_3040 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2787));
                        _1199 = dot(_3135, vec4(1.0 - _2788, 1.0, 1.0, _2788)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        _1199 = 1.0;
                    }
                    if (_1782)
                    {
                        _1198 = _1199;
                        break;
                    }
                }
            }
            if (floatBitsToUint(TranslucentBasePass_2._m0[30u]).y == 0u)
            {
                _1198 = 1.0;
                break;
            }
            D _1239 = fma(_227, TranslucentBasePass_2._m0[35u].z, fma(_226, TranslucentBasePass_2._m0[34u].z, TranslucentBasePass_2._m0[33u].z * _225)) + TranslucentBasePass_2._m0[36u].z;
            D _1243 = fma(_227, TranslucentBasePass_2._m0[35u].w, fma(_226, TranslucentBasePass_2._m0[34u].w, TranslucentBasePass_2._m0[33u].w * _225)) + TranslucentBasePass_2._m0[36u].w;
            D _1244 = (fma(_227, TranslucentBasePass_2._m0[35u].x, fma(_226, TranslucentBasePass_2._m0[34u].x, TranslucentBasePass_2._m0[33u].x * _225)) + TranslucentBasePass_2._m0[36u].x) / _1243;
            D _1245 = (fma(_227, TranslucentBasePass_2._m0[35u].y, fma(_226, TranslucentBasePass_2._m0[34u].y, TranslucentBasePass_2._m0[33u].y * _225)) + TranslucentBasePass_2._m0[36u].y) / _1243;
            uvec4 _1249 = floatBitsToUint(TranslucentBasePass_2._m0[32u]);
            uint _1250 = _1249.x;
            uint _1251 = _1249.y;
            uint _1252 = _1249.z;
            uint _1257 = uint(int(floor(_1244)));
            uint _1258 = uint(int((-0.0) - floor(_1245)));
            if (!((int(_1258) < int(_1249.w)) && ((int(_1257) < int(_1252)) && ((int(_1257) >= int(_1250)) && (int(_1258) >= int(_1251))))))
            {
                _1198 = 1.0;
                break;
            }
            D _1326 = dFdyFine(_1244);
            D _1327 = dFdyFine(_1245);
            D _1328 = dFdyFine(_1239);
            D _1329 = dFdxFine(_1244);
            D _1330 = dFdxFine(_1245);
            D _1331 = dFdxFine(_1239);
            D _1334 = (_1330 * _1328) - (_1331 * _1327);
            D _1337 = (_1331 * _1326) - (_1329 * _1328);
            D _1340 = (_1329 * _1327) - (_1330 * _1326);
            D _1351 = 1.0 / spvNMax(abs(_1340), sqrt(((_1337 * _1337) + (_1340 * _1340)) + (_1334 * _1334)) * 0.100000001490116119384765625);
            D _1357 = D(int(uint(_1340 > 0.0) - uint(_1340 < 0.0)));
            D _1641;
            D _1643;
            if (dot(vec2(_1334, _1337), vec2(_1334, _1337)) < 1.0000000195414813782625560981111e-24)
            {
                _1641 = 0.0;
                _1643 = 0.0;
            }
            else
            {
                D _1707 = (-0.0) - _1334;
                D _1708 = (-0.0) - _1337;
                D _1712 = inversesqrt(dot(vec2(_1707, _1708), vec2(_1707, _1708)));
                _1641 = _1712 * _1707;
                _1643 = _1712 * _1708;
            }
            D _1649 = _261 + (-0.5);
            D _1657 = (((_1643 * _1649) + (_1641 * _260)) * 2.0) + (_1641 * 0.5);
            D _1658 = (((_1643 * _260) + (_1641 * _1649)) * 2.0) + (_1643 * 0.5);
            D _1664 = _1657 + (fract(_1244) * 256.0);
            D _1665 = _1658 + (fract(_1245) * 256.0);
            D _1678 = dot(vec2((floor(_1664) + 0.5) - _1664, (floor(_1665) + 0.5) - _1665), vec2(((_1334 * 256.0) * _1351) * _1357, ((_1337 * 256.0) * _1351) * _1357));
            D _1684 = (_1657 * 0.00390625) + _1244;
            D _1685 = (_1658 * 0.00390625) + _1245;
            uint _1697 = ((uint(int((-0.0) - floor(_1685))) - _1251) * (_1252 - _1250)) + (uint(int(floor(_1684))) - _1250);
            D _2111;
            D _2114;
            if ((texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowLoadedTileData, int(_1697 >> 5u)).x & (1u << (_1697 & 31u))) == 0u)
            {
                _2111 = 3.0000000054977557577780399428115e+38;
                _2114 = 0.0;
            }
            else
            {
                uvec4 _2136 = uvec4(texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileIndices, int(_1697)));
                uint _2137 = _2136.x;
                D frontier_phi_51_52_ladder;
                D frontier_phi_51_52_ladder_1;
                if (int(_2137) > int(4294967295u))
                {
                    uint _2753 = (uint(floor(fract(_1684) * 256.0)) + (_2137 << 16u)) + (uint(floor(fract(_1685) * 256.0)) << 8u);
                    uvec4 _2756 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileData, int(_2753 >> 1u));
                    uint _2757 = _2756.x;
                    D _2765 = D((((_2753 & 1u) == 0u) ? _2757 : (_2757 >> 16u)) & 65535u) * 1.525902189314365386962890625e-05;
                    D frontier_phi_51_52_ladder_73_ladder;
                    D frontier_phi_51_52_ladder_73_ladder_1;
                    if (_2765 != 1.0)
                    {
                        vec4 _3566 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthRanges, int(_2137));
                        D _3568 = _3566.y;
                        frontier_phi_51_52_ladder_73_ladder = 1.0 / _3568;
                        frontier_phi_51_52_ladder_73_ladder_1 = (_3568 * _2765) + _3566.x;
                    }
                    else
                    {
                        frontier_phi_51_52_ladder_73_ladder = 0.0;
                        frontier_phi_51_52_ladder_73_ladder_1 = 3.0000000054977557577780399428115e+38;
                    }
                    frontier_phi_51_52_ladder = frontier_phi_51_52_ladder_73_ladder;
                    frontier_phi_51_52_ladder_1 = frontier_phi_51_52_ladder_73_ladder_1;
                }
                else
                {
                    frontier_phi_51_52_ladder = 0.0;
                    frontier_phi_51_52_ladder_1 = 3.0000000054977557577780399428115e+38;
                }
                _2111 = frontier_phi_51_52_ladder_1;
                _2114 = frontier_phi_51_52_ladder;
            }
            _1198 = spvNClamp(((((1.525902189314365386962890625e-05 - _1239) + _2111) + (spvNMin(abs(_1678), _2114 * 10.0) * D(int(uint(_1678 > 0.0) - uint(_1678 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0);
            break;
        }
        D _1313;
        if ((floatBitsToUint(Primitive._m0[27u]).z & 2u) == 0u)
        {
            _1313 = 1.0;
        }
        else
        {
            _1313 = View._m0[188u].y;
        }
        uvec4 _1317 = floatBitsToUint(View._m0[220u]);
        uint _1318 = _1317.y;
        uint _1321 = (_1318 != 1u) ? 4294967295u : 0u;
        uint _1639;
        if (_1318 > 1u)
        {
            D _126[4];
            _126[0u] = 0.0;
            _126[1u] = 0.0;
            _126[2u] = 0.0;
            _126[3u] = 0.0;
            uint _2096 = 0u;
            bool _2102;
            for (;;)
            {
                _2102 = _2096 < floatBitsToUint(View._m0[220u]).y;
                if (_2102)
                {
                    uint _2704 = _2096 + 237u;
                    D _2718 = View._m0[_2704].x - View._m0[75u].x;
                    D _2719 = View._m0[_2704].y - View._m0[75u].y;
                    D _2720 = View._m0[_2704].z - View._m0[75u].z;
                    D _2721 = dot(vec3(_2718, _2719, _2720), vec3(_233, _234, _235));
                    D _2728 = dot(vec3(_2718, _2719, _2720), vec3(_2718, _2719, _2720)) - (View._m0[_2704].w * View._m0[_2704].w);
                    D _2730 = (_2721 * _2721) - _2728;
                    D _3342;
                    if ((_2728 < 0.0) && (!(_2730 < 0.0)))
                    {
                        D _3336 = sqrt(_2730);
                        _3342 = spvNMin(abs(_3336 + _2721), abs(_2721 - _3336));
                    }
                    else
                    {
                        _3342 = 0.0;
                    }
                    _126[_2096] = _3342;
                }
                uint _2097 = _2096 + 1u;
                if (_2097 == 4u)
                {
                    break;
                }
                else
                {
                    _2096 = _2097;
                    continue;
                }
            }
            D _3353 = (_260 * 0.99989998340606689453125) * dot(vec4(_126[0u], _126[1u], _126[2u], _126[3u]), vec4(1.0));
            uint frontier_phi_32_83_ladder;
            if (_126[0u] > _3353)
            {
                frontier_phi_32_83_ladder = 0u;
            }
            else
            {
                D _3704 = _126[1u] + _126[0u];
                uint frontier_phi_32_83_ladder_94_ladder;
                if (_3704 > _3353)
                {
                    frontier_phi_32_83_ladder_94_ladder = 1u;
                }
                else
                {
                    D _3788 = _3704 + _126[2u];
                    uint frontier_phi_32_83_ladder_94_ladder_102_ladder;
                    if (_3788 > _3353)
                    {
                        frontier_phi_32_83_ladder_94_ladder_102_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder;
                        if ((_3788 + _126[3u]) > _3353)
                        {
                            frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder = _1321;
                        }
                        frontier_phi_32_83_ladder_94_ladder_102_ladder = frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder;
                    }
                    frontier_phi_32_83_ladder_94_ladder = frontier_phi_32_83_ladder_94_ladder_102_ladder;
                }
                frontier_phi_32_83_ladder = frontier_phi_32_83_ladder_94_ladder;
            }
            _1639 = frontier_phi_32_83_ladder;
        }
        else
        {
            _1639 = _1321;
        }
        D _2103;
        if (_1639 == 4294967295u)
        {
            _2103 = _1313;
        }
        else
        {
            _2103 = View._m0[_1639 + 241u].x * _1313;
        }
        D frontier_phi_3_49_ladder;
        D frontier_phi_3_49_ladder_1;
        D frontier_phi_3_49_ladder_2;
        D frontier_phi_3_49_ladder_3;
        D frontier_phi_3_49_ladder_4;
        D frontier_phi_3_49_ladder_5;
        D frontier_phi_3_49_ladder_6;
        D frontier_phi_3_49_ladder_7;
        D frontier_phi_3_49_ladder_8;
        if (_2103 > 0.0)
        {
            D _2737 = spvNClamp((TranslucentBasePass_2._m0[7u].x * _102) + TranslucentBasePass_2._m0[7u].y, 0.0, 1.0);
            D _2741 = ((_2737 * _2737) * (1.0 - _1198)) + _1198;
            D frontier_phi_3_49_ladder_72_ladder;
            D frontier_phi_3_49_ladder_72_ladder_1;
            D frontier_phi_3_49_ladder_72_ladder_2;
            D frontier_phi_3_49_ladder_72_ladder_3;
            D frontier_phi_3_49_ladder_72_ladder_4;
            D frontier_phi_3_49_ladder_72_ladder_5;
            D frontier_phi_3_49_ladder_72_ladder_6;
            D frontier_phi_3_49_ladder_72_ladder_7;
            D frontier_phi_3_49_ladder_72_ladder_8;
            if (_2741 > 0.0)
            {
                D _3355 = dot(vec3(_398, _399, _400), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3358 = spvNMax(0.0, _3355);
                D _3359 = dot(vec3(_236, _238, _239), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3365 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3359 * 2.0) + 2.0));
                D _3368 = spvNClamp(_3365 * (_512 + _3355), 0.0, 1.0);
                D _3383 = sqrt(spvNMax(0.0, 1.0 - ((1.0 - (_512 * _512)) * 0.444444477558135986328125)));
                D _3387 = (_518 * 0.666666686534881591796875) - (_3383 * _398);
                D _3388 = (_519 * 0.666666686534881591796875) - (_3383 * _399);
                D _3389 = (_520 * 0.666666686534881591796875) - (_3383 * _400);
                D _3393 = inversesqrt(dot(vec3(_3387, _3388, _3389), vec3(_3387, _3388, _3389)));
                D _3400 = dot(vec3((-0.0) - (_3393 * _3387), (-0.0) - (_3393 * _3388), (-0.0) - (_3393 * _3389)), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3403 = _616 * _616;
                D _3404 = _3403 * _3403;
                D _3408 = ((_3368 * _3368) * (_3404 + (-1.0))) + 1.0;
                D _3414 = (_3358 * 2.0) * _538;
                D _3419 = 1.0 - spvNMax(9.9999997473787516355514526367188e-06, spvNMin(_3365 * (_3359 + 1.0), 1.0));
                D _3420 = _3419 * _3419;
                D _3422 = (_3420 * _3420) * _3419;
                D _3427 = spvNMin(dot(vec3(_496, _497, _498), vec3(16.666667938232421875)), 1.0);
                D _3440 = spvNMax(0.039999999105930328369140625, _616);
                D _3453 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_3440 * _3358) + 0.02669160068035125732421875) / (_3358 + 0.4664950072765350341796875)) * exp2(((1.0 / _3440) * _3358) * log2(_3440)), 0.0, 1.0));
                D _3454 = 1.0 - _3358;
                D _3455 = _3454 * _3454;
                D _3467 = ((_3455 * _3455) * _3454) * exp2(log2((exp2((_3440 * 4.7702999114990234375) * log2(_3358)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _3440);
                D _3470 = (1.0 / _3453) * (1.0 - _3453);
                D _3474 = (_3470 * _496) + 1.0;
                D _3475 = (_3470 * _497) + 1.0;
                D _3476 = (_3470 * _498) + 1.0;
                D _3477 = _3453 - _3467;
                D _3491 = spvNClamp(1.0 - dot(vec3(_3474 * ((_3477 * _496) + _3467), _3475 * ((_3477 * _497) + _3467), _3476 * ((_3477 * _498) + _3467)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                D _3494 = (((_3404 * 0.3183098733425140380859375) * _3358) * (1.0 / (_3408 * _3408))) * (0.5 / ((_3403 * ((_538 + _3358) - _3414)) + _3414));
                D _3495 = _3358 * 0.3183098733425140380859375;
                D _3498 = ((_3400 * _3400) + 1.0) * 0.05968309938907623291015625;
                D _3500 = spvNMin(1.0, _424);
                D _3502 = (_424 + 1.0) - _3500;
                D _3503 = _3502 * _3502;
                D _3506 = 1.0 - ((_3503 * _3503) * _3502);
                D _3507 = _3506 * _3506;
                D _3512 = ((_3507 * _3507) * (_3506 * (_424 - _3500))) + _3500;
                D _3515 = sqrt(spvNMax(0.0, 1.0 - _3512));
                D _3520 = 1.0 - spvNClamp((_616 * 3.5) + (-0.5), 0.0, 1.0);
                D _3521 = _3520 * _3520;
                D _3531 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_647 * _3515) * spvNClamp(1.0 - ((_3521 * _3521) * _3520), 0.0, 1.0))) * _3358, 0.0, 1.0);
                D _3536 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _3515)) * _3358, 0.0, 1.0);
                D _3538 = spvNMin(_2741, _3531 * _3531);
                D _3539 = spvNMin(_2741, _3536 * _3536);
                D _3540 = spvNMin(_2741, _3512);
                D _3541 = _2103 * TranslucentBasePass_2._m0[4u].x;
                D _3542 = _2103 * TranslucentBasePass_2._m0[4u].y;
                D _3543 = _2103 * TranslucentBasePass_2._m0[4u].z;
                frontier_phi_3_49_ladder_72_ladder = (_3498 * _3543) * _3540;
                frontier_phi_3_49_ladder_72_ladder_1 = (((_3541 * _448) * _3495) * _3491) * _3539;
                frontier_phi_3_49_ladder_72_ladder_2 = (((_3542 * _449) * _3495) * _3491) * _3539;
                frontier_phi_3_49_ladder_72_ladder_3 = (((_3543 * _450) * _3495) * _3491) * _3539;
                frontier_phi_3_49_ladder_72_ladder_4 = (((_3494 * _3541) * spvNClamp(((_3427 - _496) * _3422) + _496, 0.0, 1.0)) * _3474) * _3538;
                frontier_phi_3_49_ladder_72_ladder_5 = (((_3494 * _3542) * spvNClamp(((_3427 - _497) * _3422) + _497, 0.0, 1.0)) * _3475) * _3538;
                frontier_phi_3_49_ladder_72_ladder_6 = (((_3494 * _3543) * spvNClamp(((_3427 - _498) * _3422) + _498, 0.0, 1.0)) * _3476) * _3538;
                frontier_phi_3_49_ladder_72_ladder_7 = (_3498 * _3541) * _3540;
                frontier_phi_3_49_ladder_72_ladder_8 = (_3498 * _3542) * _3540;
            }
            else
            {
                frontier_phi_3_49_ladder_72_ladder = 0.0;
                frontier_phi_3_49_ladder_72_ladder_1 = 0.0;
                frontier_phi_3_49_ladder_72_ladder_2 = 0.0;
                frontier_phi_3_49_ladder_72_ladder_3 = 0.0;
                frontier_phi_3_49_ladder_72_ladder_4 = 0.0;
                frontier_phi_3_49_ladder_72_ladder_5 = 0.0;
                frontier_phi_3_49_ladder_72_ladder_6 = 0.0;
                frontier_phi_3_49_ladder_72_ladder_7 = 0.0;
                frontier_phi_3_49_ladder_72_ladder_8 = 0.0;
            }
            frontier_phi_3_49_ladder = frontier_phi_3_49_ladder_72_ladder;
            frontier_phi_3_49_ladder_1 = frontier_phi_3_49_ladder_72_ladder_1;
            frontier_phi_3_49_ladder_2 = frontier_phi_3_49_ladder_72_ladder_2;
            frontier_phi_3_49_ladder_3 = frontier_phi_3_49_ladder_72_ladder_3;
            frontier_phi_3_49_ladder_4 = frontier_phi_3_49_ladder_72_ladder_4;
            frontier_phi_3_49_ladder_5 = frontier_phi_3_49_ladder_72_ladder_5;
            frontier_phi_3_49_ladder_6 = frontier_phi_3_49_ladder_72_ladder_6;
            frontier_phi_3_49_ladder_7 = frontier_phi_3_49_ladder_72_ladder_7;
            frontier_phi_3_49_ladder_8 = frontier_phi_3_49_ladder_72_ladder_8;
        }
        else
        {
            frontier_phi_3_49_ladder = 0.0;
            frontier_phi_3_49_ladder_1 = 0.0;
            frontier_phi_3_49_ladder_2 = 0.0;
            frontier_phi_3_49_ladder_3 = 0.0;
            frontier_phi_3_49_ladder_4 = 0.0;
            frontier_phi_3_49_ladder_5 = 0.0;
            frontier_phi_3_49_ladder_6 = 0.0;
            frontier_phi_3_49_ladder_7 = 0.0;
            frontier_phi_3_49_ladder_8 = 0.0;
        }
        _748 = frontier_phi_3_49_ladder_1;
        _750 = frontier_phi_3_49_ladder_2;
        _752 = frontier_phi_3_49_ladder_3;
        _754 = frontier_phi_3_49_ladder_4;
        _756 = frontier_phi_3_49_ladder_5;
        _758 = frontier_phi_3_49_ladder_6;
        _760 = frontier_phi_3_49_ladder_7;
        _762 = frontier_phi_3_49_ladder_8;
        _764 = frontier_phi_3_49_ladder;
    }
    uvec4 _768 = floatBitsToUint(TranslucentBasePass_2._m0[0u]);
    uint _769 = _768.x;
    uint _774 = min(min(texelFetch(TranslucentBasePass_Shared_Forward_NumCulledLightsGrid, int(0u)).x, _769), _769);
    D _781;
    D _783;
    D _785;
    D _787;
    D _789;
    D _791;
    D _793;
    D _795;
    D _797;
    D _799;
    D _801;
    D _803;
    D _805;
    D _807;
    D _809;
    if (_774 == 0u)
    {
        _781 = _748;
        _783 = _750;
        _785 = _752;
        _787 = _754;
        _789 = _756;
        _791 = _758;
        _793 = _760;
        _795 = _762;
        _797 = _764;
        _799 = 0.0;
        _801 = 0.0;
        _803 = 0.0;
        _805 = 0.0;
        _807 = 0.0;
        _809 = 0.0;
    }
    else
    {
        D _782;
        D _784;
        D _786;
        D _788;
        D _790;
        D _792;
        D _794;
        D _796;
        D _798;
        D _800;
        D _802;
        D _804;
        D _806;
        D _808;
        D _810;
        D _1113 = _748;
        D _1114 = _750;
        D _1115 = _752;
        D _1116 = _754;
        D _1117 = _756;
        D _1118 = _758;
        D _1119 = _760;
        D _1120 = _762;
        D _1121 = _764;
        D _1122 = 0.0;
        D _1123 = 0.0;
        D _1124 = 0.0;
        D _1125 = 0.0;
        D _1126 = 0.0;
        D _1127 = 0.0;
        uint _1128 = 0u;
        D _1132;
        D _1133;
        D _1134;
        D _1135;
        D _1137;
        D _1138;
        D _1139;
        D _1141;
        D _1142;
        D _1143;
        uint _1145;
        D _1147;
        D _1148;
        D _1150;
        D _1151;
        D _1152;
        D _1154;
        D _1155;
        uint _1157;
        D _1160;
        D _1161;
        D _1162;
        D _1163;
        uint _1166;
        D _1168;
        D _1169;
        D _1170;
        D _1171;
        D _1174;
        D _1175;
        D _1176;
        D _1177;
        D _1180;
        D _1181;
        D _1182;
        D _1183;
        D _1186;
        D _1187;
        D _1188;
        D _1189;
        bool _1192;
        bool _1193;
        bool _1197;
        for (;;)
        {
            vec4 _1131 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(0u));
            _1132 = _1131.x;
            _1133 = _1131.y;
            _1134 = _1131.z;
            _1135 = _1131.w;
            vec4 _1136 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(1u));
            _1137 = _1136.x;
            _1138 = _1136.y;
            _1139 = _1136.z;
            vec4 _1140 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(2u));
            _1141 = _1140.x;
            _1142 = _1140.y;
            _1143 = _1140.z;
            _1145 = floatBitsToUint(_1140.w);
            vec4 _1146 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(3u));
            _1147 = _1146.x;
            _1148 = _1146.y;
            vec4 _1149 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(4u));
            _1150 = _1149.x;
            _1151 = _1149.y;
            _1152 = _1149.z;
            vec4 _1153 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(5u));
            _1154 = _1153.x;
            _1155 = _1153.y;
            _1157 = floatBitsToUint(_1153.z);
            vec4 _1159 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(6u));
            _1160 = _1159.x;
            _1161 = _1159.y;
            _1162 = _1159.z;
            _1163 = _1159.w;
            _1166 = floatBitsToUint(texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(7u)).x);
            vec4 _1167 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(8u));
            _1168 = _1167.x;
            _1169 = _1167.y;
            _1170 = _1167.z;
            _1171 = _1167.w;
            vec4 _1173 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(9u));
            _1174 = _1173.x;
            _1175 = _1173.y;
            _1176 = _1173.z;
            _1177 = _1173.w;
            vec4 _1179 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(10u));
            _1180 = _1179.x;
            _1181 = _1179.y;
            _1182 = _1179.z;
            _1183 = _1179.w;
            vec4 _1185 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(11u));
            _1186 = _1185.x;
            _1187 = _1185.y;
            _1188 = _1185.z;
            _1189 = _1185.w;
            _1192 = (_1145 & 131072u) != 0u;
            _1193 = _1147 > (-2.0);
            _1197 = (_1145 & 16384u) == 0u;
            D frontier_phi_47_pred;
            D frontier_phi_47_pred_1;
            D frontier_phi_47_pred_2;
            D frontier_phi_47_pred_3;
            D frontier_phi_47_pred_4;
            D frontier_phi_47_pred_5;
            D frontier_phi_47_pred_6;
            D frontier_phi_47_pred_7;
            D frontier_phi_47_pred_8;
            D frontier_phi_47_pred_9;
            D frontier_phi_47_pred_10;
            D frontier_phi_47_pred_11;
            D frontier_phi_47_pred_12;
            D frontier_phi_47_pred_13;
            D frontier_phi_47_pred_14;
            if (_1197)
            {
                D _1592;
                if (_1192)
                {
                    uint _1557 = _1166 + 0u;
                    uvec2 _1560 = uvec2(textureSize(ShadowMaps[(_1557)], int(0u)));
                    D _1562 = D(int(_1560.x));
                    D _1564 = D(int(_1560.y));
                    D _1565 = 1.0 / _1562;
                    D _1566 = 1.0 / _1564;
                    D _1578 = fma(_227, _1182, fma(_226, _1176, _1170 * _225)) + _1188;
                    D _1582 = fma(_227, _1183, fma(_226, _1177, _1171 * _225)) + _1189;
                    D _1583 = (fma(_227, _1180, fma(_226, _1174, _1168 * _225)) + _1186) / _1582;
                    D _1584 = (fma(_227, _1181, fma(_226, _1175, _1169 * _225)) + _1187) / _1582;
                    D frontier_phi_28_27_ladder;
                    if ((_1584 <= _1163) && ((_1583 <= _1162) && ((_1583 >= _1160) && (_1584 >= _1161))))
                    {
                        D _1980 = dFdyFine(_1583);
                        D _1981 = dFdyFine(_1584);
                        D _1982 = dFdyFine(_1578);
                        D _1983 = dFdxFine(_1583);
                        D _1984 = dFdxFine(_1584);
                        D _1985 = dFdxFine(_1578);
                        D _1988 = (_1984 * _1982) - (_1985 * _1981);
                        D _1991 = (_1985 * _1980) - (_1983 * _1982);
                        D _1994 = (_1983 * _1981) - (_1984 * _1980);
                        D _2004 = 1.0 / spvNMax(abs(_1994), sqrt(((_1991 * _1991) + (_1994 * _1994)) + (_1988 * _1988)) * 0.100000001490116119384765625);
                        D _2010 = D(int(uint(_1994 > 0.0) - uint(_1994 < 0.0)));
                        D _2011 = _1988 * _1565;
                        D _2013 = (_2011 * _2004) * _2010;
                        D _2014 = _1991 * _1566;
                        D _2016 = (_2014 * _2004) * _2010;
                        D _2299;
                        D _2301;
                        if (dot(vec2(_1988, _1991), vec2(_1988, _1991)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2299 = 0.0;
                            _2301 = 0.0;
                        }
                        else
                        {
                            D _2642 = (-0.0) - _1988;
                            D _2643 = (-0.0) - _1991;
                            D _2647 = inversesqrt(dot(vec2(_2642, _2643), vec2(_2642, _2643)));
                            _2299 = _2647 * _2642;
                            _2301 = _2647 * _2643;
                        }
                        D _2303 = _261 + (-0.5);
                        D _2308 = _260 + 0.5;
                        D _2311 = ((_2301 * _2303) + (_1583 * _1562)) + (_2299 * _2308);
                        D _2314 = ((_2299 * _2303) + (_1584 * _1564)) + (_2301 * _2308);
                        D _2315 = _2311 + (-0.5);
                        D _2316 = _2314 + (-0.5);
                        D _2317 = trunc(_2315);
                        D _2318 = trunc(_2316);
                        D _2319 = _2315 - _2317;
                        D _2320 = _2316 - _2318;
                        D _2321 = _2317 * _1565;
                        D _2322 = _2318 * _1566;
                        D _2325 = (_2317 + (-0.5)) - _2311;
                        D _2326 = (_2318 + (-0.5)) - _2314;
                        D _2327 = dot(vec2(_2325, _2326), vec2(_2013, _2016));
                        D _2330 = _2327 + _2016;
                        D _2333 = _2010 * (_2004 * (_2014 + _2011));
                        D _2334 = _2333 + _2327;
                        D _2335 = _2327 + _2013;
                        vec4 _2339 = textureGather((sampler2D(ShadowMaps[_1557], View_SharedPointClampedSampler)), vec2(_2321, _2322));
                        D _2380 = 1.525902189314365386962890625e-05 - _1578;
                        D _2403 = (_2317 + 1.5) - _2311;
                        D _2404 = dot(vec2(_2403, _2326), vec2(_2013, _2016));
                        D _2407 = _2404 + _2016;
                        D _2408 = _2333 + _2404;
                        D _2409 = _2404 + _2013;
                        vec4 _2413 = textureGatherOffset((sampler2D(ShadowMaps[_1557], View_SharedPointClampedSampler)), vec2(_2321, _2322), ivec2(2, 0));
                        D _2477 = (_2318 + 1.5) - _2314;
                        D _2478 = dot(vec2(_2325, _2477), vec2(_2013, _2016));
                        D _2481 = _2478 + _2016;
                        D _2482 = _2333 + _2478;
                        D _2483 = _2478 + _2013;
                        vec4 _2485 = textureGatherOffset((sampler2D(ShadowMaps[_1557], View_SharedPointClampedSampler)), vec2(_2321, _2322), ivec2(0, 2));
                        D _2547 = dot(vec2(_2403, _2477), vec2(_2013, _2016));
                        D _2550 = _2547 + _2016;
                        D _2551 = _2333 + _2547;
                        D _2552 = _2547 + _2013;
                        vec4 _2554 = textureGatherOffset((sampler2D(ShadowMaps[_1557], View_SharedPointClampedSampler)), vec2(_2321, _2322), ivec2(2));
                        D _2616 = 1.0 - _2319;
                        vec4 _2639 = vec4((((spvNClamp((((_2380 + _2339.w) + (spvNMin(abs(_2327), 0.0) * D(int(uint(_2327 > 0.0) - uint(_2327 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2616) + spvNClamp((((_2380 + _2339.z) + (spvNMin(abs(_2335), 0.0) * D(int(uint(_2335 > 0.0) - uint(_2335 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2380 + _2413.w) + (spvNMin(abs(_2404), 0.0) * D(int(uint(_2404 > 0.0) - uint(_2404 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2380 + _2413.z) + (spvNMin(abs(_2409), 0.0) * D(int(uint(_2409 > 0.0) - uint(_2409 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2319), (((spvNClamp((((_2380 + _2339.x) + (spvNMin(abs(_2330), 0.0) * D(int(uint(_2330 > 0.0) - uint(_2330 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2616) + spvNClamp((((_2380 + _2339.y) + (spvNMin(abs(_2334), 0.0) * D(int(uint(_2334 > 0.0) - uint(_2334 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2380 + _2413.x) + (spvNMin(abs(_2407), 0.0) * D(int(uint(_2407 > 0.0) - uint(_2407 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2380 + _2413.y) + (spvNMin(abs(_2408), 0.0) * D(int(uint(_2408 > 0.0) - uint(_2408 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2319), (((spvNClamp((((_2380 + _2485.w) + (spvNMin(abs(_2478), 0.0) * D(int(uint(_2478 > 0.0) - uint(_2478 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2616) + spvNClamp((((_2380 + _2485.z) + (spvNMin(abs(_2483), 0.0) * D(int(uint(_2483 > 0.0) - uint(_2483 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2380 + _2554.w) + (spvNMin(abs(_2547), 0.0) * D(int(uint(_2547 > 0.0) - uint(_2547 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2380 + _2554.z) + (spvNMin(abs(_2552), 0.0) * D(int(uint(_2552 > 0.0) - uint(_2552 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2319), (((spvNClamp((((_2380 + _2485.x) + (spvNMin(abs(_2481), 0.0) * D(int(uint(_2481 > 0.0) - uint(_2481 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2616) + spvNClamp((((_2380 + _2485.y) + (spvNMin(abs(_2482), 0.0) * D(int(uint(_2482 > 0.0) - uint(_2482 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2380 + _2554.x) + (spvNMin(abs(_2550), 0.0) * D(int(uint(_2550 > 0.0) - uint(_2550 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2380 + _2554.y) + (spvNMin(abs(_2551), 0.0) * D(int(uint(_2551 > 0.0) - uint(_2551 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2319));
                        frontier_phi_28_27_ladder = dot(_2639, vec4(1.0 - _2320, 1.0, 1.0, _2320)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        frontier_phi_28_27_ladder = 1.0;
                    }
                    _1592 = frontier_phi_28_27_ladder;
                }
                else
                {
                    _1592 = 1.0;
                }
                D _1598 = _1132 - _225;
                D _1599 = _1133 - _226;
                D _1600 = _1134 - _227;
                D _1601 = dot(vec3(_1598, _1599, _1600), vec3(_1598, _1599, _1600));
                D _2025;
                D _2026;
                D _2027;
                if (_1601 > 9.9999997473787516355514526367188e-05)
                {
                    D _2021 = inversesqrt(_1601);
                    _2025 = _2021 * _1598;
                    _2026 = _2021 * _1599;
                    _2027 = _2021 * _1600;
                }
                else
                {
                    _2025 = 0.0;
                    _2026 = 0.0;
                    _2027 = 0.0;
                }
                D _2028 = _1154 * _1154;
                D _2032 = (_1135 * _1135) * _1601;
                D _2035 = spvNClamp(1.0 - (_2032 * _2032), 0.0, 1.0);
                D _2655;
                if (_1193)
                {
                    D _2653 = spvNClamp((dot(vec3(_2025, _2026, _2027), vec3(_1141, _1142, _1143)) - _1147) * _1148, 0.0, 1.0);
                    _2655 = _2653 * _2653;
                }
                else
                {
                    _2655 = 1.0;
                }
                D _2656 = ((_2035 * _2035) * D(_1601 >= _2028)) * _2655;
                D _3199;
                D _3201;
                D _3203;
                if ((_1145 & 262144u) == 0u)
                {
                    _3199 = 1.0;
                    _3201 = 1.0;
                    _3203 = 1.0;
                }
                else
                {
                    D _3206 = (-0.0) - _1142;
                    D _3207 = (-0.0) - _1143;
                    D _3208 = (-0.0) - _1141;
                    D _3218 = (-0.0) - _2025;
                    D _3219 = (-0.0) - _2026;
                    D _3220 = (-0.0) - _2027;
                    D _3223 = fma(_3207, _3220, fma(_3206, _3219, _2025 * _1141));
                    D _3226 = fma(_1152, _3220, fma(_1151, _3219, _1150 * _3218));
                    D _3234 = atan(((-0.0) - _3226) / ((-0.0) - _3223));
                    bool _3239 = _3223 > (-0.0);
                    bool _3240 = _3223 == (-0.0);
                    bool _3241 = _3226 <= (-0.0);
                    bool _3242 = _3226 > (-0.0);
                    vec4 _3264 = texture((sampler2D(ForwardLightProfileTextures[_1157 + 0u], View_SharedBilinearWrappedSampler)), vec2(fract((_3240 && _3241) ? 1.25 : ((_3240 && _3242) ? 0.75 : ((((_3239 && _3242) ? (_3234 + (-3.1415927410125732421875)) : ((_3239 && _3241) ? (_3234 + 3.1415927410125732421875) : _3234)) * 0.15915493667125701904296875) + 1.0))), (asin((-0.0) - fma((_1151 * _3208) - (_1150 * _3206), _3220, fma((_1150 * _3207) - (_1152 * _3208), _3219, ((_1152 * _3206) - (_1151 * _3207)) * _3218))) * 0.3183098733425140380859375) + 0.5));
                    _3199 = _3264.x;
                    _3201 = _3264.y;
                    _3203 = _3264.z;
                }
                D _3655;
                D _3657;
                D _3659;
                D _3661;
                D _3663;
                D _3665;
                D _3667;
                D _3669;
                D _3671;
                for (;;)
                {
                    if (_2656 > 0.0)
                    {
                        D _3780;
                        if (_1192)
                        {
                            if (!(_1592 > 0.0))
                            {
                                _3655 = 0.0;
                                _3657 = 0.0;
                                _3659 = 0.0;
                                _3661 = 0.0;
                                _3663 = 0.0;
                                _3665 = 0.0;
                                _3667 = 0.0;
                                _3669 = 0.0;
                                _3671 = 0.0;
                                break;
                            }
                            _3780 = _1592;
                        }
                        else
                        {
                            _3780 = 1.0;
                        }
                        D _3782 = spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1601));
                        D _3783 = 1.0 / _3782;
                        D _3784 = dot(vec3(_398, _399, _400), vec3(_2025, _2026, _2027));
                        D _3805;
                        if (_1154 > 0.0)
                        {
                            D _3802 = sqrt(spvNClamp(_2028 * _3783, 0.0, 1.0));
                            D frontier_phi_107_106_ladder;
                            if (_3802 > spvNMax(9.9999997473787516355514526367188e-06, _3784))
                            {
                                D _3824 = spvNMax((-0.0) - _3802, _3784) + _3802;
                                frontier_phi_107_106_ladder = (_3824 * _3824) * (0.25 / _3802);
                            }
                            else
                            {
                                frontier_phi_107_106_ladder = _3784;
                            }
                            _3805 = frontier_phi_107_106_ladder;
                        }
                        else
                        {
                            _3805 = _3784;
                        }
                        D _3867;
                        D _3868;
                        D _3807;
                        D _3809;
                        D _3813;
                        D _3814;
                        bool _3817;
                        for (;;)
                        {
                            _3807 = spvNMax(0.0, _3805);
                            _3809 = _616 * _616;
                            _3813 = spvNClamp(((1.0 - _3809) * _1154) * inversesqrt(_3782), 0.0, 1.0);
                            _3814 = dot(vec3(_236, _238, _239), vec3(_2025, _2026, _2027));
                            _3817 = _3813 > 0.0;
                            D _3835;
                            D _3837;
                            if (_3817)
                            {
                                D _3830 = sqrt(spvNMax(0.0, 1.0 - (_3813 * _3813)));
                                D _3833 = ((_3784 * 2.0) * _512) - _3814;
                                if (!(!(_3833 >= _3830)))
                                {
                                    _3867 = _524;
                                    _3868 = 1.0;
                                    break;
                                }
                                D _3855 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, 1.0 - (_3833 * _3833))) * _3813;
                                _3835 = (_3855 * ((((_512 * _512) * 2.0) + (-1.0)) - (_3833 * _3814))) + (_3830 * _3814);
                                _3837 = (_3855 * (_512 - (_3833 * _3784))) + (_3830 * _3784);
                            }
                            else
                            {
                                _3835 = _3814;
                                _3837 = _3784;
                            }
                            D _3842 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3835 * 2.0) + 2.0));
                            _3867 = spvNMin(_3842 * (_3835 + 1.0), 1.0);
                            _3868 = spvNClamp(_3842 * (_3837 + _512), 0.0, 1.0);
                            break;
                        }
                        D _3869 = spvNMax(9.9999997473787516355514526367188e-06, _3867);
                        D _3878 = sqrt(spvNMax(0.0, 1.0 - ((1.0 - (_512 * _512)) * 0.444444477558135986328125)));
                        D _3882 = (_518 * 0.666666686534881591796875) - (_3878 * _398);
                        D _3883 = (_519 * 0.666666686534881591796875) - (_3878 * _399);
                        D _3884 = (_520 * 0.666666686534881591796875) - (_3878 * _400);
                        D _3888 = inversesqrt(dot(vec3(_3882, _3883, _3884), vec3(_3882, _3883, _3884)));
                        D _3895 = dot(vec3((-0.0) - (_3888 * _3882), (-0.0) - (_3888 * _3883), (-0.0) - (_3888 * _3884)), vec3(_2025, _2026, _2027));
                        D _3898 = _3809 * _3809;
                        D _3912 = ((_3868 * _3868) * (_3898 + (-1.0))) + 1.0;
                        D _3918 = (_3807 * 2.0) * _538;
                        D _3923 = 1.0 - _3869;
                        D _3924 = _3923 * _3923;
                        D _3926 = (_3924 * _3924) * _3923;
                        D _3930 = spvNMin(dot(vec3(_496, _497, _498), vec3(16.666667938232421875)), 1.0);
                        D _3943 = spvNMax(0.039999999105930328369140625, _616);
                        D _3956 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_3943 * _3807) + 0.02669160068035125732421875) / (_3807 + 0.4664950072765350341796875)) * exp2(((1.0 / _3943) * _3807) * log2(_3943)), 0.0, 1.0));
                        D _3957 = 1.0 - _3807;
                        D _3958 = _3957 * _3957;
                        D _3970 = ((_3958 * _3958) * _3957) * exp2(log2((exp2((_3943 * 4.7702999114990234375) * log2(_3807)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _3943);
                        D _3973 = (1.0 / _3956) * (1.0 - _3956);
                        D _3977 = (_3973 * _496) + 1.0;
                        D _3978 = (_3973 * _497) + 1.0;
                        D _3979 = (_3973 * _498) + 1.0;
                        D _3980 = _3956 - _3970;
                        D _3994 = spvNClamp(1.0 - dot(vec3(_3977 * ((_3980 * _496) + _3970), _3978 * ((_3980 * _497) + _3970), _3979 * ((_3980 * _498) + _3970)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                        D _3998 = ((((_3898 * 0.3183098733425140380859375) * _3807) * (1.0 / (_3912 * _3912))) * (_3817 ? ((1.0 / ((((_3813 * 0.25) * (_3813 + (_3809 * 3.0))) * (1.0 / _3869)) + _3898)) * _3898) : 1.0)) * (0.5 / ((_3809 * ((_538 + _3807) - _3918)) + _3918));
                        D _3999 = _3807 * 0.3183098733425140380859375;
                        D _4002 = ((_3895 * _3895) + 1.0) * 0.05968309938907623291015625;
                        D _4003 = spvNMin(1.0, _424);
                        D _4005 = (_424 + 1.0) - _4003;
                        D _4006 = _4005 * _4005;
                        D _4009 = 1.0 - ((_4006 * _4006) * _4005);
                        D _4010 = _4009 * _4009;
                        D _4015 = ((_4010 * _4010) * (_4009 * (_424 - _4003))) + _4003;
                        D _4018 = sqrt(spvNMax(0.0, 1.0 - _4015));
                        D _4022 = 1.0 - spvNClamp((_616 * 3.5) + (-0.5), 0.0, 1.0);
                        D _4023 = _4022 * _4022;
                        D _4033 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_647 * _4018) * spvNClamp(1.0 - ((_4023 * _4023) * _4022), 0.0, 1.0))) * _3807, 0.0, 1.0);
                        D _4038 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _4018)) * _3807, 0.0, 1.0);
                        D _4040 = spvNMin(_3780, _4033 * _4033);
                        D _4041 = spvNMin(_3780, _4038 * _4038);
                        D _4042 = spvNMin(_3780, _4015);
                        D _4046 = (_2656 * _1137) * _3199;
                        D _4047 = (_2656 * _1138) * _3201;
                        D _4048 = (_2656 * _1139) * _3203;
                        D _4049 = _3783 * _4046;
                        D _4053 = _3783 * _4047;
                        D _4057 = _3783 * _4048;
                        _3655 = ((((_4046 * _448) * _3783) * _3999) * _3994) * _4041;
                        _3657 = ((((_4047 * _449) * _3783) * _3999) * _3994) * _4041;
                        _3659 = ((((_4048 * _450) * _3783) * _3999) * _3994) * _4041;
                        _3661 = (((_4049 * spvNClamp(((_3930 - _496) * _3926) + _496, 0.0, 1.0)) * _3998) * _3977) * _4040;
                        _3663 = (((_4053 * _3998) * spvNClamp(((_3930 - _497) * _3926) + _497, 0.0, 1.0)) * _3978) * _4040;
                        _3665 = (((_4057 * _3998) * spvNClamp(((_3930 - _498) * _3926) + _498, 0.0, 1.0)) * _3979) * _4040;
                        _3667 = (_4049 * _4002) * _4042;
                        _3669 = (_4053 * _4002) * _4042;
                        _3671 = (_4057 * _4002) * _4042;
                        break;
                    }
                    else
                    {
                        _3655 = 0.0;
                        _3657 = 0.0;
                        _3659 = 0.0;
                        _3661 = 0.0;
                        _3663 = 0.0;
                        _3665 = 0.0;
                        _3667 = 0.0;
                        _3669 = 0.0;
                        _3671 = 0.0;
                        break;
                    }
                }
                frontier_phi_47_pred = _1123;
                frontier_phi_47_pred_1 = _3655 + _1113;
                frontier_phi_47_pred_2 = _3657 + _1114;
                frontier_phi_47_pred_3 = _3659 + _1115;
                frontier_phi_47_pred_4 = _3661 + _1116;
                frontier_phi_47_pred_5 = _3663 + _1117;
                frontier_phi_47_pred_6 = _3665 + _1118;
                frontier_phi_47_pred_7 = _3667 + _1119;
                frontier_phi_47_pred_8 = _3669 + _1120;
                frontier_phi_47_pred_9 = _3671 + _1121;
                frontier_phi_47_pred_10 = _1122;
                frontier_phi_47_pred_11 = _1124;
                frontier_phi_47_pred_12 = _1125;
                frontier_phi_47_pred_13 = _1126;
                frontier_phi_47_pred_14 = _1127;
            }
            else
            {
                D _1296 = _1132 - _225;
                D _1297 = _1133 - _226;
                D _1298 = _1134 - _227;
                D _1299 = dot(vec3(_1296, _1297, _1298), vec3(_1296, _1297, _1298));
                D _1303 = (_1135 * _1135) * _1299;
                D _1304 = _1303 * _1303;
                D _1305 = _1304 * _1304;
                D _1308 = spvNClamp(1.0 - (_1305 * _1305), 0.0, 1.0);
                D _1309 = _1308 * _1308;
                D _1310 = _1309 * _1309;
                D _1311 = _1310 * _1310;
                D _1616;
                D _1618;
                D _1620;
                D _1622;
                D _1624;
                D _1626;
                if (_1311 > 0.0)
                {
                    D _1608 = dot(vec3(_233, _234, _235), vec3(_398, _399, _400)) * 2.0;
                    D _1612 = _233 - (_1608 * _398);
                    D _1613 = _234 - (_1608 * _399);
                    D _1614 = _235 - (_1608 * _400);
                    D _3266;
                    D _3267;
                    D _3268;
                    D _3269;
                    D _3270;
                    D _3271;
                    D _3272;
                    D _3273;
                    D _3274;
                    D _3275;
                    D _3276;
                    if (_1155 == 0.0)
                    {
                        D _2661;
                        D _2662;
                        D _2663;
                        if (_1299 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2657 = inversesqrt(_1299);
                            _2661 = _2657 * _1296;
                            _2662 = _2657 * _1297;
                            _2663 = _2657 * _1298;
                        }
                        else
                        {
                            _2661 = 0.0;
                            _2662 = 0.0;
                            _2663 = 0.0;
                        }
                        D _2666 = 1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1299));
                        _3266 = _2666;
                        _3267 = (_1154 * _1154) * _2666;
                        _3268 = _2661;
                        _3269 = _2662;
                        _3270 = _2663;
                        _3271 = _2661;
                        _3272 = _2662;
                        _3273 = _2663;
                        _3274 = _2661;
                        _3275 = _2662;
                        _3276 = _2663;
                    }
                    else
                    {
                        D _2039 = _1155 * 0.5;
                        D _2040 = _2039 * _1141;
                        D _2041 = _2039 * _1142;
                        D _2042 = _2039 * _1143;
                        D _2043 = _1296 - _2040;
                        D _2044 = _1297 - _2041;
                        D _2045 = _1298 - _2042;
                        D _2046 = _2040 + _1296;
                        D _2047 = _2041 + _1297;
                        D _2048 = _2042 + _1298;
                        D _2056 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2043, _2044, _2045), vec3(_2043, _2044, _2045))));
                        D _2058 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2046, _2047, _2048), vec3(_2046, _2047, _2048))));
                        D _2059 = _2058 * _2056;
                        D _2075 = (1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(_2059, ((dot(vec3(_2043, _2044, _2045), vec3(_2046, _2047, _2048)) * 0.5) * _2059) + 0.5))) * _2059;
                        D _2077 = (_1141 * 2.0) * _2039;
                        D _2079 = (_1142 * 2.0) * _2039;
                        D _2081 = (_1143 * 2.0) * _2039;
                        D _2082 = dot(vec3(_2077, _2079, _2081), vec3(_2077, _2079, _2081));
                        D _2699;
                        D _2700;
                        D _2701;
                        if (_2082 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2669 = dot(vec3(_1612, _1613, _1614), vec3(_2077, _2079, _2081));
                            D _2685 = spvNClamp((1.0 / (_2082 - (_2669 * _2669))) * dot(vec3(_2043, _2044, _2045), vec3((_2669 * _1612) - _2077, (_2669 * _1613) - _2079, (_2669 * _1614) - _2081)), 0.0, 1.0);
                            D _2689 = (_2685 * _2077) + _2043;
                            D _2690 = (_2685 * _2079) + _2044;
                            D _2691 = (_2685 * _2081) + _2045;
                            D _2695 = inversesqrt(dot(vec3(_2689, _2690, _2691), vec3(_2689, _2690, _2691)));
                            _2699 = _2689 * _2695;
                            _2700 = _2690 * _2695;
                            _2701 = _2691 * _2695;
                        }
                        else
                        {
                            _2699 = _2043;
                            _2700 = _2044;
                            _2701 = _2045;
                        }
                        _3266 = _2075;
                        _3267 = (_1154 * _1154) * _2075;
                        _3268 = _2056 * _2043;
                        _3269 = _2056 * _2044;
                        _3270 = _2056 * _2045;
                        _3271 = _2058 * _2046;
                        _3272 = _2058 * _2047;
                        _3273 = _2058 * _2048;
                        _3274 = _2699;
                        _3275 = _2700;
                        _3276 = _2701;
                    }
                    D _3286 = _3267 + 1.0;
                    D _3291 = _3274 - _233;
                    D _3292 = _3275 - _234;
                    D _3293 = _3276 - _235;
                    D _3297 = inversesqrt(dot(vec3(_3291, _3292, _3293), vec3(_3291, _3292, _3293)));
                    D _3298 = _3297 * _3291;
                    D _3299 = _3297 * _3292;
                    D _3300 = _3297 * _3293;
                    D _3307 = spvNClamp(dot(vec3(_398, _399, _400), vec3(_3298, _3299, _3300)), 0.0, 1.0);
                    D _3308 = _616 * _616;
                    D _3314 = spvNClamp(((1.0 - _3308) * _1154) * sqrt(_3266), 0.0, 1.0);
                    D _3328 = exp2(log2(spvNClamp((((_3314 * 0.25) * (_3314 + (_3308 * 3.0))) * (1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_236, _238, _239), vec3(_3298, _3299, _3300))))) + (_3308 * _3308), 0.0, 1.0)) * 0.25);
                    D _3332 = spvNClamp(dot(vec3(_3268, _3269, _3270), vec3(_3271, _3272, _3273)), 0.0, 1.0);
                    D _3334 = _3328 * _3328;
                    D _3335 = _3334 * _3334;
                    D _3687;
                    if (_3332 < 1.0)
                    {
                        D _3678 = sqrt(spvNClamp((1.0 / (_3332 + 1.0)) * (1.0 - _3332), 0.0, 1.0));
                        _3687 = (1.0 / spvNClamp(((_3678 * 0.25) * (_3678 + (_3334 * 3.0))) + _3335, 0.0, 1.0)) * _3335;
                    }
                    else
                    {
                        _3687 = 1.0;
                    }
                    D _3691 = ((_3307 * _3307) * (_3335 + (-1.0))) + 1.0;
                    D _3694 = spvNMax(0.0, (((dot(vec3(_398, _399, _400), vec3(_3271, _3272, _3273)) + dot(vec3(_398, _399, _400), vec3(_3268, _3269, _3270))) * 0.5) + _3267) * (1.0 / (_3286 * _3286))) * 0.3183098733425140380859375;
                    D _3697 = ((_3694 * _3335) * _3687) * (1.0 / (_3691 * _3691));
                    D _3699 = (_1311 * _1137) * _3266;
                    D _3701 = (_1311 * _1138) * _3266;
                    D _3703 = (_1311 * _1139) * _3266;
                    _1616 = _3697 * _3699;
                    _1618 = _3697 * _3701;
                    _1620 = _3697 * _3703;
                    _1622 = _3694 * _3699;
                    _1624 = _3694 * _3701;
                    _1626 = _3694 * _3703;
                }
                else
                {
                    _1616 = 0.0;
                    _1618 = 0.0;
                    _1620 = 0.0;
                    _1622 = 0.0;
                    _1624 = 0.0;
                    _1626 = 0.0;
                }
                frontier_phi_47_pred = _1618 + _1123;
                frontier_phi_47_pred_1 = _1113;
                frontier_phi_47_pred_2 = _1114;
                frontier_phi_47_pred_3 = _1115;
                frontier_phi_47_pred_4 = _1116;
                frontier_phi_47_pred_5 = _1117;
                frontier_phi_47_pred_6 = _1118;
                frontier_phi_47_pred_7 = _1119;
                frontier_phi_47_pred_8 = _1120;
                frontier_phi_47_pred_9 = _1121;
                frontier_phi_47_pred_10 = _1616 + _1122;
                frontier_phi_47_pred_11 = _1620 + _1124;
                frontier_phi_47_pred_12 = _1622 + _1125;
                frontier_phi_47_pred_13 = _1624 + _1126;
                frontier_phi_47_pred_14 = _1626 + _1127;
            }
            _802 = frontier_phi_47_pred;
            _782 = frontier_phi_47_pred_1;
            _784 = frontier_phi_47_pred_2;
            _786 = frontier_phi_47_pred_3;
            _788 = frontier_phi_47_pred_4;
            _790 = frontier_phi_47_pred_5;
            _792 = frontier_phi_47_pred_6;
            _794 = frontier_phi_47_pred_7;
            _796 = frontier_phi_47_pred_8;
            _798 = frontier_phi_47_pred_9;
            _800 = frontier_phi_47_pred_10;
            _804 = frontier_phi_47_pred_11;
            _806 = frontier_phi_47_pred_12;
            _808 = frontier_phi_47_pred_13;
            _810 = frontier_phi_47_pred_14;
            uint _1129 = _1128 + 1u;
            if (_1129 == _774)
            {
                break;
            }
            else
            {
                _1113 = _782;
                _1114 = _784;
                _1115 = _786;
                _1116 = _788;
                _1117 = _790;
                _1118 = _792;
                _1119 = _794;
                _1120 = _796;
                _1121 = _798;
                _1122 = _800;
                _1123 = _802;
                _1124 = _804;
                _1125 = _806;
                _1126 = _808;
                _1127 = _810;
                _1128 = _1129;
                continue;
            }
        }
        _781 = _782;
        _783 = _784;
        _785 = _786;
        _787 = _788;
        _789 = _790;
        _791 = _792;
        _793 = _794;
        _795 = _796;
        _797 = _798;
        _799 = _800;
        _801 = _802;
        _803 = _804;
        _805 = _806;
        _807 = _808;
        _809 = _810;
    }
    vec4 _851 = textureLod(sampler3D(TranslucentBasePass_TranslucencyLightingVolumeEnvironmentA, View_SharedBilinearClampedSampler), vec3((_225 - View._m0[180u].x) * View._m0[182u].x, (_226 - View._m0[180u].y) * View._m0[182u].y, (_227 - View._m0[180u].z) * View._m0[182u].z), 0.0);
    D _875;
    D _876;
    D _877;
    if (_345 < 1.0)
    {
        _875 = _322.x / ((_367 / _344) + 1.0);
        _876 = _322.y / ((_368 / _344) + 1.0);
        _877 = _322.z / ((_369 / _344) + 1.0);
    }
    else
    {
        _875 = 0.0;
        _876 = 0.0;
        _877 = 0.0;
    }
    D _894 = spvNClamp(_598, 0.0, 1.0);
    D _907 = _446 * _446;
    D _908 = _907 * _446;
    D _915 = ((_398 - _535) * _908) + _535;
    D _916 = ((_399 - _536) * _908) + _536;
    D _917 = ((_400 - _537) * _908) + _537;
    D _921 = inversesqrt(dot(vec3(_915, _916, _917), vec3(_915, _916, _917)));
    D _930 = 10.0 / spvNMax(9.9999997473787516355514526367188e-06, _907);
    D _959 = fma(_224, View._m0[2u].x, fma(_223, View._m0[1u].x, View._m0[0u].x * _222)) + View._m0[3u].x;
    D _963 = fma(_224, View._m0[2u].y, fma(_223, View._m0[1u].y, View._m0[0u].y * _222)) + View._m0[3u].y;
    D _967 = fma(_224, View._m0[2u].z, fma(_223, View._m0[1u].z, View._m0[0u].z * _222)) + View._m0[3u].z;
    D _971 = fma(_224, View._m0[2u].w, fma(_223, View._m0[1u].w, View._m0[0u].w * _222)) + View._m0[3u].w;
    D _978 = ((_915 * _102) * _921) + _222;
    D _979 = ((_916 * _102) * _921) + _223;
    D _980 = ((_917 * _102) * _921) + _224;
    D _1013 = 1.0 / _971;
    D _1014 = _1013 * _959;
    D _1015 = _1013 * _963;
    D _1019 = (_1013 * _967) + (0.0500000007450580596923828125 / _971);
    D _1020 = 1.0 / (fma(_980, View._m0[2u].w, fma(_979, View._m0[1u].w, View._m0[0u].w * _978)) + View._m0[3u].w);
    D _1031 = 1.0 / ((View._m0[36u].w * _930) + _971);
    D _1034 = (_1020 * (fma(_980, View._m0[2u].x, fma(_979, View._m0[1u].x, View._m0[0u].x * _978)) + View._m0[3u].x)) - _1014;
    D _1035 = (_1020 * (fma(_980, View._m0[2u].y, fma(_979, View._m0[1u].y, View._m0[0u].y * _978)) + View._m0[3u].y)) - _1015;
    D _1037 = (_1031 * ((View._m0[36u].x * _930) + _959)) - _1014;
    D _1038 = (_1031 * ((View._m0[36u].y * _930) + _963)) - _1015;
    D _1043 = sqrt((_1034 * _1034) + (_1035 * _1035)) * 0.5;
    D _1062 = spvNMin(1.0 - (spvNMax(0.0, abs((_1043 * _1014) + _1034) - _1043) / abs(_1034)), 1.0 - (spvNMax(0.0, abs((_1043 * _1015) + _1035) - _1043) / abs(_1035))) / _1043;
    D _1063 = _1062 * _1034;
    D _1064 = _1062 * _1035;
    D _1065 = _1062 * ((_1020 * (fma(_980, View._m0[2u].z, fma(_979, View._m0[1u].z, View._m0[0u].z * _978)) + View._m0[3u].z)) - _1019);
    uvec2 _1071 = uvec2(textureSize(TranslucentBasePass_HZBTexture, int(0u)));
    D _1073 = D(int(_1071.x));
    D _1075 = D(int(_1071.y));
    uint _1096 = max(1u, min(uint(ceil((spvNClamp((1.0 / spvNMax(9.9999997473787516355514526367188e-05, sqrt((_1063 * _1063) + (_1064 * _1064)))) * sqrt((_1037 * _1037) + (_1038 * _1038)), 0.0, 1.0) * 8.0) + _260)), 8u));
    D _1101 = ((_1014 * 0.5) + 0.5) * TranslucentBasePass_2._m0[198u].x;
    D _1102 = (0.5 - (_1015 * 0.5)) * TranslucentBasePass_2._m0[198u].y;
    D _1105 = (TranslucentBasePass_2._m0[198u].x * 0.0625) * _1063;
    D _1108 = (TranslucentBasePass_2._m0[198u].y * (-0.0625)) * _1064;
    D _1109 = _1065 * 0.125;
    D _1111 = spvNMax(abs(_1065), _1019 - ((1.0 / (fma(_102, View._m0[38u].w, 0.0) + _971)) * (fma(_102, View._m0[38u].z, 0.0) + _967))) * 0.125;
    D _1279;
    D _1281;
    D _1283;
    D _1285;
    if (_1096 == 0u)
    {
        _1279 = 0.0;
        _1281 = 0.0;
        _1283 = 0.0;
        _1285 = 0.0;
    }
    else
    {
        D frontier_phi_60;
        D frontier_phi_60_1;
        D frontier_phi_60_2;
        D frontier_phi_60_3;
        D _1529 = 0.0;
        uint _1531 = 0u;
        D _1530;
        D _1533;
        bool _1556;
        for (;;)
        {
            _1533 = D(_1531);
            D _1534 = _1533 + _260;
            vec4 _1548 = texelFetch(TranslucentBasePass_HZBTexture, ivec2_(uvec2(uint(int(floor(((_1534 * _1105) + _1101) * _1073))), uint(int(floor(((_1534 * _1108) + _1102) * _1075))))), int(0u));
            D _1550 = _1548.x;
            _1530 = ((_1534 * _1109) + _1019) - _1550;
            _1556 = (abs(((-0.0) - _1111) - _1530) < _1111) && (_1550 != 0.0);
            if (_1556)
            {
                D _1965 = (_1531 == 0u) ? (_1530 - _1109) : _1529;
                D _1972 = abs(((_260 + (-1.0)) + _1533) + spvNClamp(_1965 / (_1965 - _1530), 0.0, 1.0));
                D _1977 = spvNMin(_1972 * 0.125, 1.0);
                frontier_phi_60 = 1.0 - (_1977 * _1977);
                frontier_phi_60_1 = (_1972 * _1109) + _1019;
                frontier_phi_60_2 = (_1972 * _1108) + _1102;
                frontier_phi_60_3 = (_1972 * _1105) + _1101;
                break;
            }
            else
            {
                uint _1532 = _1531 + 1u;
                if (_1532 < _1096)
                {
                    _1529 = _1530;
                    _1531 = _1532;
                    continue;
                }
                else
                {
                    frontier_phi_60 = 0.0;
                    frontier_phi_60_1 = 0.0;
                    frontier_phi_60_2 = 0.0;
                    frontier_phi_60_3 = 0.0;
                    break;
                }
            }
        }
        _1279 = frontier_phi_60_3;
        _1281 = frontier_phi_60_2;
        _1283 = frontier_phi_60_1;
        _1285 = frontier_phi_60;
    }
    D _1293 = (spvNClamp(_1279 * TranslucentBasePass_2._m0[198u].z, 0.0, 1.0) * 2.0) + (-1.0);
    D _1294 = 1.0 - (spvNClamp(_1281 * TranslucentBasePass_2._m0[198u].w, 0.0, 1.0) * 2.0);
    D _1434;
    D _1436;
    D _1438;
    D _1440;
    if (_1285 > 0.0)
    {
        D _1435;
        D _1437;
        D _1439;
        D _2181;
        D _1427;
        bool _1433;
        for (;;)
        {
            D _1386 = ((View._m0[73u].x * _1283) + View._m0[73u].y) + (1.0 / ((View._m0[73u].z * _1283) - View._m0[73u].w));
            D _1410 = _1386 * _1293;
            D _1411 = _1386 * _1294;
            D _1422 = (_222 - View._m0[63u].x) - fma(_1386, View._m0[62u].x, fma(_1411, View._m0[61u].x, _1410 * View._m0[60u].x));
            D _1424 = (_223 - View._m0[63u].y) - fma(_1386, View._m0[62u].y, fma(_1411, View._m0[61u].y, _1410 * View._m0[60u].y));
            D _1426 = (_224 - View._m0[63u].z) - fma(_1386, View._m0[62u].z, fma(_1411, View._m0[61u].z, _1410 * View._m0[60u].z));
            _1427 = dot(vec3(_1422, _1424, _1426), vec3(_1422, _1424, _1426));
            _1433 = View._m0[175u].w != 0.0;
            if (_1433)
            {
                if (floatBitsToUint(View._m0[175u]).y == 0u)
                {
                    _1435 = 0.0;
                    _1437 = 0.0;
                    _1439 = 0.0;
                    _2181 = 0.0;
                    break;
                }
            }
            D _1823 = fma(_1283, View._m0[140u].w, fma(_1294, View._m0[139u].w, View._m0[138u].w * _1293)) + View._m0[141u].w;
            D _1824 = (fma(_1283, View._m0[140u].x, fma(_1294, View._m0[139u].x, View._m0[138u].x * _1293)) + View._m0[141u].x) / _1823;
            D _1825 = (fma(_1283, View._m0[140u].y, fma(_1294, View._m0[139u].y, View._m0[138u].y * _1293)) + View._m0[141u].y) / _1823;
            D _1842 = spvNClamp((abs((spvNMin(spvNMax(_1824, -1.0), 1.0) - _1293) * 0.5) * 5.0) + (-4.0), 0.0, 1.0);
            D _1843 = spvNClamp((abs((spvNMin(spvNMax(_1825, -1.0), 1.0) - _1294) * 0.5) * 5.0) + (-4.0), 0.0, 1.0);
            uvec2 _1896 = uvec2(textureSize(TranslucentBasePass_PrevSceneColor, int(0u)));
            vec4 _1917 = texelFetch(TranslucentBasePass_PrevSceneColor, ivec2_(uvec2(uint(min(int(uint(max(int(uint(int(D(int(_1896.x)) * ((TranslucentBasePass_2._m0[199u].x * spvNMin(spvNMax(_1824 - ((D(int(uint(_1824 > 0.0) - uint(_1824 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1824) + (-1.0))), -1.0), 1.0)) + TranslucentBasePass_2._m0[199u].z)))), int(uint(int(TranslucentBasePass_2._m0[200u].x)))))), int(uint(int(TranslucentBasePass_2._m0[200u].x + TranslucentBasePass_2._m0[200u].z)) + 4294967295u))), uint(min(int(uint(max(int(uint(int(D(int(_1896.y)) * ((TranslucentBasePass_2._m0[199u].y * spvNMin(spvNMax(_1825 - ((D(int(uint(_1825 > 0.0) - uint(_1825 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1825) + (-1.0))), -1.0), 1.0)) + TranslucentBasePass_2._m0[199u].w)))), int(uint(int(TranslucentBasePass_2._m0[200u].y)))))), int(uint(int(TranslucentBasePass_2._m0[200u].y + TranslucentBasePass_2._m0[200u].w)) + 4294967295u))))), int(0u));
            _1435 = View._m0[165u].x * spvNMin(_1917.x, 65504.0);
            _1437 = View._m0[165u].x * spvNMin(_1917.y, 65504.0);
            _1439 = View._m0[165u].x * spvNMin(_1917.z, 65504.0);
            _2181 = spvNMax(0.0, 1.0 - dot(vec2(_1842, _1843), vec2(_1842, _1843)));
            break;
        }
        _1434 = _1435;
        _1436 = _1437;
        _1438 = _1439;
        _1440 = (_2181 * _1285) * spvNClamp(1.0 / spvNMax(9.9999997473787516355514526367188e-06, (_907 * _907) * _1427), 0.0, 1.0);
    }
    else
    {
        _1434 = 0.0;
        _1436 = 0.0;
        _1438 = 0.0;
        _1440 = 0.0;
    }
    D _1474 = fma(_227, View._m0[14u].w, fma(_226, View._m0[13u].w, _225 * View._m0[12u].w)) + View._m0[15u].w;
    D _1479 = (((fma(_227, View._m0[14u].x, fma(_226, View._m0[13u].x, _225 * View._m0[12u].x)) + View._m0[15u].x) / _1474) * 0.5) + 0.5;
    D _1480 = 0.5 - (((fma(_227, View._m0[14u].y, fma(_226, View._m0[13u].y, _225 * View._m0[12u].y)) + View._m0[15u].y) / _1474) * 0.5);
    D _1509 = sqrt(((_223 * _223) + (_222 * _222)) + (_224 * _224));
    D _1527 = spvNMax(0.0, ((1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_222, _223, _224), vec3(View._m0[68u].xyz())))) * _1509) * View._m0[280u].w);
    D _1933;
    D _1935;
    D _1937;
    D _1939;
    D _1941;
    D _1943;
    if (_1509 < _1527)
    {
        _1933 = 0.0;
        _1935 = 0.0;
        _1937 = 0.0;
        _1939 = 1.0;
        _1941 = 1.0;
        _1943 = 1.0;
    }
    else
    {
        D _1951 = (1.0 / _1509) * _1527;
        uvec4 _1958 = floatBitsToUint(View._m0[220u]);
        uint _1959 = _1958.y;
        uint _1961 = (_1959 != 1u) ? 4294967295u : 0u;
        uint _2297;
        if (_1959 > 1u)
        {
            D _127[4];
            _127[0u] = 0.0;
            _127[1u] = 0.0;
            _127[2u] = 0.0;
            _127[3u] = 0.0;
            uint _3143 = 0u;
            bool _3149;
            for (;;)
            {
                _3149 = _3143 < floatBitsToUint(View._m0[220u]).y;
                if (_3149)
                {
                    uint _3570 = _3143 + 237u;
                    D _3582 = View._m0[_3570].x - View._m0[75u].x;
                    D _3583 = View._m0[_3570].y - View._m0[75u].y;
                    D _3584 = View._m0[_3570].z - View._m0[75u].z;
                    D _3585 = dot(vec3(_3582, _3583, _3584), vec3(_233, _234, _235));
                    D _3592 = dot(vec3(_3582, _3583, _3584), vec3(_3582, _3583, _3584)) - (View._m0[_3570].w * View._m0[_3570].w);
                    D _3594 = (_3585 * _3585) - _3592;
                    D _3712;
                    if ((_3592 < 0.0) && (!(_3594 < 0.0)))
                    {
                        D _3706 = sqrt(_3594);
                        _3712 = spvNMin(abs(_3706 + _3585), abs(_3585 - _3706));
                    }
                    else
                    {
                        _3712 = 0.0;
                    }
                    _127[_3143] = _3712;
                }
                uint _3144 = _3143 + 1u;
                if (_3144 == 4u)
                {
                    break;
                }
                else
                {
                    _3143 = _3144;
                    continue;
                }
            }
            D _3722 = (_260 * 0.99989998340606689453125) * dot(vec4(_127[0u], _127[1u], _127[2u], _127[3u]), vec4(1.0));
            uint frontier_phi_59_97_ladder;
            if (_127[0u] > _3722)
            {
                frontier_phi_59_97_ladder = 0u;
            }
            else
            {
                D _3790 = _127[1u] + _127[0u];
                uint frontier_phi_59_97_ladder_103_ladder;
                if (_3790 > _3722)
                {
                    frontier_phi_59_97_ladder_103_ladder = 1u;
                }
                else
                {
                    D _3820 = _3790 + _127[2u];
                    uint frontier_phi_59_97_ladder_103_ladder_109_ladder;
                    if (_3820 > _3722)
                    {
                        frontier_phi_59_97_ladder_103_ladder_109_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder;
                        if ((_3820 + _127[3u]) > _3722)
                        {
                            frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder = _1961;
                        }
                        frontier_phi_59_97_ladder_103_ladder_109_ladder = frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder;
                    }
                    frontier_phi_59_97_ladder_103_ladder = frontier_phi_59_97_ladder_103_ladder_109_ladder;
                }
                frontier_phi_59_97_ladder = frontier_phi_59_97_ladder_103_ladder;
            }
            _2297 = frontier_phi_59_97_ladder;
        }
        else
        {
            _2297 = _1961;
        }
        D frontier_phi_38_59_ladder;
        D frontier_phi_38_59_ladder_1;
        D frontier_phi_38_59_ladder_2;
        D frontier_phi_38_59_ladder_3;
        D frontier_phi_38_59_ladder_4;
        D frontier_phi_38_59_ladder_5;
        if (_2297 == 4294967295u)
        {
            frontier_phi_38_59_ladder = 1.0;
            frontier_phi_38_59_ladder_1 = 1.0;
            frontier_phi_38_59_ladder_2 = 1.0;
            frontier_phi_38_59_ladder_3 = 0.0;
            frontier_phi_38_59_ladder_4 = 0.0;
            frontier_phi_38_59_ladder_5 = 0.0;
        }
        else
        {
            uint _3150 = _2297 + 221u;
            D _3158 = spvNMin(View._m0[_3150].w, 0.9900000095367431640625);
            uint _3159 = _2297 + 225u;
            uint _3166 = _2297 + 229u;
            uint _3173 = _2297 + 233u;
            uint _3178 = _2297 + 241u;
            D _3625;
            D _3626;
            D _3627;
            if (TranslucentBasePass_2._m0[146u].x > 0.0)
            {
                vec4 _3617 = textureLod(sampler2D(TranslucentBasePass_Shared_Fog_FarIntegratedScatteringTexture, View_SharedBilinearClampedSampler), vec2(spvNMin(spvNMax(View._m0[278u].x * _1479, View._m0[279u].x), View._m0[280u].x), spvNMin(spvNMax(View._m0[278u].y * _1480, View._m0[279u].y), View._m0[280u].y)), 0.0);
                _3625 = View._m0[164u].z * _3617.x;
                _3626 = View._m0[164u].z * _3617.y;
                _3627 = View._m0[164u].z * _3617.z;
            }
            else
            {
                _3625 = 0.0;
                _3626 = 0.0;
                _3627 = 0.0;
            }
            D _3631 = dot(vec3((-0.0) - View._m0[218u].x, (-0.0) - View._m0[218u].y, (-0.0) - View._m0[218u].z), vec3(_236, _238, _239));
            D _3644 = (((_3631 * _3631) + 1.0) * 0.0397887341678142547607421875) * exp2(log2(spvNMax(0.0, _3631 + 1.25)) * (-1.5));
            D _3724;
            if (View._m0[_3159].x == 0.0)
            {
                _3724 = 0.0;
            }
            else
            {
                D _3772 = (((_1951 * _224) - View._m0[_3159].z) + View._m0[75u].z) * View._m0[_3159].y;
                D _3773 = ((1.0 - _1951) * _224) * View._m0[_3159].y;
                D _3778 = exp2((-0.0) - _3772);
                D frontier_phi_98_99_ladder;
                if (abs(_3773) > 0.00999999977648258209228515625)
                {
                    frontier_phi_98_99_ladder = ((_3778 - exp2(((-0.0) - _3773) - _3772)) * View._m0[_3159].x) * (1.0 / _3773);
                }
                else
                {
                    frontier_phi_98_99_ladder = (View._m0[_3159].x * 0.693147182464599609375) * _3778;
                }
                _3724 = frontier_phi_98_99_ladder;
            }
            D _3728 = _3724 * (1.0 - _3158);
            D _3732 = (1.0 - View._m0[_3166].x) * View._m0[_3173].x;
            D _3733 = (1.0 - View._m0[_3166].y) * View._m0[_3173].x;
            D _3734 = (1.0 - View._m0[_3166].z) * View._m0[_3173].x;
            D _3735 = (-0.0) - (_1509 - _1527);
            D _3763 = 1.0 - spvNClamp(exp2(_3728 * _3735), 0.0, 1.0);
            frontier_phi_38_59_ladder = spvNClamp(exp2((_3728 + _3734) * _3735), 0.0, 1.0);
            frontier_phi_38_59_ladder_1 = spvNClamp(exp2((_3728 + _3733) * _3735), 0.0, 1.0);
            frontier_phi_38_59_ladder_2 = spvNClamp(exp2((_3728 + _3732) * _3735), 0.0, 1.0);
            frontier_phi_38_59_ladder_3 = (((_3158 * View._m0[_3150].z) * (((View._m0[219u].z * View._m0[_3178].x) * _3644) + _3627)) * spvNClamp(exp2(_3734 * _3735), 0.0, 1.0)) * _3763;
            frontier_phi_38_59_ladder_4 = (((_3158 * View._m0[_3150].y) * (((View._m0[219u].y * View._m0[_3178].x) * _3644) + _3626)) * spvNClamp(exp2(_3733 * _3735), 0.0, 1.0)) * _3763;
            frontier_phi_38_59_ladder_5 = (((_3158 * View._m0[_3150].x) * (((View._m0[219u].x * View._m0[_3178].x) * _3644) + _3625)) * spvNClamp(exp2(_3732 * _3735), 0.0, 1.0)) * _3763;
        }
        _1933 = frontier_phi_38_59_ladder_5;
        _1935 = frontier_phi_38_59_ladder_4;
        _1937 = frontier_phi_38_59_ladder_3;
        _1939 = frontier_phi_38_59_ladder_2;
        _1941 = frontier_phi_38_59_ladder_1;
        _1943 = frontier_phi_38_59_ladder;
    }
    D _2229;
    D _2230;
    D _2231;
    D _2232;
    D _2233;
    D _2234;
    if (TranslucentBasePass_2._m0[148u].x > 0.0)
    {
        D _2209 = spvNMin(spvNMax(View._m0[278u].x * _1479, View._m0[279u].x), View._m0[280u].x);
        D _2210 = spvNMin(spvNMax(View._m0[278u].y * _1480, View._m0[279u].y), View._m0[280u].y);
        D _2211 = spvNMin(spvNMax((View._m0[275u].z * spvNMax(0.0, spvNMin(View._m0[276u].z * log2((View._m0[276u].x * _1474) + View._m0[276u].y), View._m0[274u].z + (-1.0)) + 0.5)) * View._m0[278u].z, View._m0[279u].z), View._m0[280u].z);
        vec4 _2214 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeATexture, View_SharedBilinearClampedSampler), vec3(_2209, _2210, _2211), 0.0);
        vec4 _2221 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeBTexture, View_SharedBilinearClampedSampler), vec3(_2209, _2210, _2211), 0.0);
        _2229 = View._m0[164u].z * _2214.x;
        _2230 = View._m0[164u].z * _2214.y;
        _2231 = View._m0[164u].z * _2214.z;
        _2232 = _2221.x;
        _2233 = _2221.y;
        _2234 = _2221.z;
    }
    else
    {
        _2229 = 0.0;
        _2230 = 0.0;
        _2231 = 0.0;
        _2232 = 1.0;
        _2233 = 1.0;
        _2234 = 1.0;
    }
    D _2241 = (1.0 - _603) + (_603 * _422);
    D _2242 = (1.0 - _606) + (_606 * _422);
    D _2243 = (1.0 - _609) + (_609 * _422);
    SV_Target.x = View._m0[164u].y * ((((_2232 * _1933) + _2229) * _2241) + ((_1939 * (((((((((_448 * _424) * _674) * spvNMax(1.0, ((_503 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_503 * 4.79510021209716796875)) + (((_503 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _424)) * _424))) * _805) + _781) * _425) + _787) + ((((_875 * _571) * spvNClamp(1.0 - (_587 * _577), 0.0, 1.0)) * ((View._m0[164u].z * _851.x) + _793)) * _894)) + ((_688 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1434)) + 29.8973522186279296875) * _1440) + (-29.8973522186279296875)) + _799)) * spvNClamp(_666, 0.0, 1.0)))) * _2232));
    SV_Target.y = ((((_2233 * _1935) + _2230) * _2242) + ((_1941 * (((((((((_449 * _424) * _674) * spvNMax(1.0, ((_504 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_504 * 4.79510021209716796875)) + (((_504 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _424)) * _424))) * _807) + _783) * _425) + _789) + ((((_876 * _571) * spvNClamp(1.0 - (_588 * _577), 0.0, 1.0)) * ((View._m0[164u].z * _851.y) + _795)) * _894)) + ((_688 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1436)) + 29.8973522186279296875) * _1440) + (-29.8973522186279296875)) + _801)) * spvNClamp(_667, 0.0, 1.0)))) * _2233)) * View._m0[164u].y;
    SV_Target.z = ((((_2234 * _1937) + _2231) * _2243) + ((_1943 * (((((((((_450 * _424) * _674) * spvNMax(1.0, ((_505 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_505 * 4.79510021209716796875)) + (((_505 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _424)) * _424))) * _809) + _785) * _425) + _791) + ((((_877 * _571) * ((View._m0[164u].z * _851.z) + _797)) * spvNClamp(1.0 - (_589 * _577), 0.0, 1.0)) * _894)) + ((_688 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1438)) + 29.8973522186279296875) * _1440) + (-29.8973522186279296875)) + _803)) * spvNClamp(_668, 0.0, 1.0)))) * _2234)) * View._m0[164u].y;
    SV_Target.w = dot(vec3(_2241, _2242, _2243), vec3(0.2125999927520751953125, 0.715200006961822509765625, 0.072200000286102294921875));
    SV_Target_1.x = _2241;
    SV_Target_1.y = _2242;
    SV_Target_1.z = _2243;
    SV_Target_1.w = 0.0;
    discard_exit(); if (g_discarded) return;
}



void set_inputs(Inputs& in) {
    in.get("TEXCOORD_10", TEXCOORD_10);
    in.get("TEXCOORD_11", TEXCOORD_11);
    in.get("TEXCOORD", TEXCOORD);
    in.get("CONSTANT_CONTEXT", CONSTANT_CONTEXT);
}
void get_outputs(Outputs& o) {
    o.put("SV_Target", SV_Target);
    o.put("SV_Target_1", SV_Target_1);
}
} // namespace S_lass_Thin_Environment