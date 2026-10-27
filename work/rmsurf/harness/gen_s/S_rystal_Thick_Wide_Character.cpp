namespace S_rystal_Thick_Wide_Character {
using namespace cpuglsl;
static D _4329;
static D _4325;
static D _4326;
static D _4327;
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
static Tex2D Material_Texture2D_14{texid("junk:T_WideOcclusion")};
static Tex2D Material_Texture2D_18{texid("junk:T_Muddiness")};
static Tex2D Material_Texture2D_19{texid("junk:T_Transparency")};
static Tex2D Material_Texture2D_20{texid("junk:T_TransparencyCoefficient")};
static Tex2D Material_Texture2D_21{texid("junk:T_Transmittance")};
static Tex2D Material_Texture2D_22{texid("junk:T_TransmittanceCoefficient")};
static Tex2D Material_Texture2D_23{texid("junk:T_Thickness")};
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









void discard_cond(bool _4315)
{
    if (_4315)
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
    D _103 = 1.0 / gl_FragCoord.w;
    D _226 = fma(gl_FragCoord.z, View._m0[54u].w, fma(gl_FragCoord.y, View._m0[53u].w, View._m0[52u].w * gl_FragCoord.x)) + View._m0[55u].w;
    D _227 = (fma(gl_FragCoord.z, View._m0[54u].x, fma(gl_FragCoord.y, View._m0[53u].x, View._m0[52u].x * gl_FragCoord.x)) + View._m0[55u].x) / _226;
    D _228 = (fma(gl_FragCoord.z, View._m0[54u].y, fma(gl_FragCoord.y, View._m0[53u].y, View._m0[52u].y * gl_FragCoord.x)) + View._m0[55u].y) / _226;
    D _229 = (fma(gl_FragCoord.z, View._m0[54u].z, fma(gl_FragCoord.y, View._m0[53u].z, View._m0[52u].z * gl_FragCoord.x)) + View._m0[55u].z) / _226;
    D _230 = _227 - View._m0[78u].x;
    D _231 = _228 - View._m0[78u].y;
    D _232 = _229 - View._m0[78u].z;
    D _237 = inversesqrt(dot(vec3(_227, _228, _229), vec3(_227, _228, _229)));
    D _238 = _237 * _227;
    D _239 = _237 * _228;
    D _240 = _237 * _229;
    D _241 = (-0.0) - _238;
    D _243 = (-0.0) - _239;
    D _244 = (-0.0) - _240;
    vec4 _262 = texelFetch(View_SpatiotemporalBlueNoiseVolumeTexture, ivec3_(uvec3(uint(int(gl_FragCoord.x)) & 127u, uint(int(gl_FragCoord.y)) & 127u, ((floatBitsToUint(View._m0[175u]).x & 7u) + uint(roundEven(CONSTANT_CONTEXT))) & 63u)), int(0u));
    D _265 = _262.x;
    D _266 = _262.y;
    vec4 _272 = texture(sampler2D(Material_Texture2D_0, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _280 = texture(sampler2D(Material_Texture2D_1, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _285 = texture(sampler2D(Material_Texture2D_2, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _292 = (_285.x * 2.0) + (-1.0);
    D _294 = (_285.y * 2.0) + (-1.0);
    D _301 = sqrt(spvNMax(0.0, 1.0 - dot(vec2(_292, _294), vec2(_292, _294))));
    D _305 = inversesqrt(dot(vec3(_292, _294, _301), vec3(_292, _294, _301)));
    D _306 = _305 * _292;
    D _307 = _305 * _294;
    D _308 = _305 * _301;
    vec4 _311 = texture(sampler2D(Material_Texture2D_3, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _316 = texture(sampler2D(Material_Texture2D_4, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _318 = _316.x;
    vec4 _321 = texture(sampler2D(Material_Texture2D_14, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.z, TEXCOORD.w), View._m0[155u].y);
    D _323 = _321.x;
    D _324 = _323 * _318;
    D _325 = spvNMin(_318, _323);
    D _327 = (1.0 - _325) + _324;
    D _328 = _327 * _327;
    D _331 = 1.0 - ((_328 * _328) * _327);
    D _332 = _331 * _331;
    vec4 _340 = texture(sampler2D(Material_Texture2D_7, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _346 = vec4(g_R.Muddiness.x, g_R.Muddiness.y, g_R.Muddiness.z, 0.0);
    vec4 _353 = texture(sampler2D(Material_Texture2D_19, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _358 = texture(sampler2D(Material_Texture2D_20, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _368 = g_R.TransparencyLog2;
    D _369 = exp2(_368);
    vec4 _372 = texture(sampler2D(Material_Texture2D_21, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _379 = texture(sampler2D(Material_Texture2D_22, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _384 = 1.0 / spvNMax(9.9999999747524270787835121154785e-07, _379.x * 100.0);
    D _391 = g_R.TransmittanceLog2.x;
    D _392 = g_R.TransmittanceLog2.y;
    D _393 = g_R.TransmittanceLog2.z;
    vec4 _399 = vec4(g_R.Thickness);
    D _406 = inversesqrt(dot(vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z), vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z)));
    D _407 = _406 * g_R.Normal.x;
    D _408 = _406 * g_R.Normal.y;
    D _409 = _406 * g_R.Normal.z;
    D _412 = fma(_409, TEXCOORD_11.x, fma(_408, ((TEXCOORD_10.z * TEXCOORD_11.y) - (TEXCOORD_10.y * TEXCOORD_11.z)) * TEXCOORD_11.w, _407 * TEXCOORD_10.x));
    D _415 = fma(_409, TEXCOORD_11.y, fma(_408, ((TEXCOORD_10.x * TEXCOORD_11.z) - (TEXCOORD_10.z * TEXCOORD_11.x)) * TEXCOORD_11.w, _407 * TEXCOORD_10.y));
    D _418 = fma(_409, TEXCOORD_11.z, fma(_408, ((TEXCOORD_10.y * TEXCOORD_11.x) - (TEXCOORD_10.x * TEXCOORD_11.y)) * TEXCOORD_11.w, _407 * TEXCOORD_10.z));
    D _422 = inversesqrt(dot(vec3(_412, _415, _418), vec3(_412, _415, _418)));
    D _423 = _422 * _412;
    D _424 = _422 * _415;
    D _425 = _422 * _418;
    bool _438;
    if (Primitive._m0[27u].w > ((_262.w * 0.99609375) + 0.001953125))
    {
        _438 = ((_265 * 0.99609375) + 0.001953125) < 1.0;
    }
    else
    {
        _438 = false;
    }
    (void)((_438 ? 1.0 : (-1.0)) < 0.0);
    D _444 = spvNClamp(g_R.BaseColor.x, 0.0, 1.0);
    D _445 = spvNClamp(g_R.BaseColor.y, 0.0, 1.0);
    D _446 = spvNClamp(g_R.BaseColor.z, 0.0, 1.0);
    D _447 = spvNClamp(g_R.Metallic, 0.0, 1.0);
    D _448 = spvNClamp(g_R.Roughness, 0.0, 1.0);
    D _449 = spvNClamp(g_R.AO, 0.0, 1.0);
    D _450 = spvNClamp(g_R.Opacity, 0.0, 1.0);
    D _452 = dFdxFine(_423);
    D _453 = dFdxFine(_424);
    D _454 = dFdxFine(_425);
    D _458 = dFdyFine(_423);
    D _459 = dFdyFine(_424);
    D _460 = dFdyFine(_425);
    D _471 = sqrt(spvNClamp(spvNMin((dot(vec3(_458, _459, _460), vec3(_458, _459, _460)) + dot(vec3(_452, _453, _454), vec3(_452, _453, _454))) * 0.15915493667125701904296875, 0.180000007152557373046875) + (_448 * _448), 0.0, 1.0));
    D _472 = 1.0 - _447;
    D _473 = _472 * _444;
    D _474 = _472 * _445;
    D _475 = _472 * _446;
    D _480 = _447 * (_444 + (-0.159951984882354736328125));
    D _481 = _447 * (_445 + (-0.159951984882354736328125));
    D _482 = _447 * (_446 + (-0.159951984882354736328125));
    D _483 = _480 + 0.159951984882354736328125;
    D _485 = _481 + 0.159951984882354736328125;
    D _486 = _482 + 0.159951984882354736328125;
    D _493 = spvNClamp(D(View._m0[220u].x > 1.0), 0.0, 1.0);
    D _521 = ((exp2(log2(spvNMax(0.0, _480 + 0.13995198905467987060546875) * 1.020408153533935546875) * 1.39999997615814208984375) - _483) * _493) + _483;
    D _522 = ((exp2(log2(spvNMax(0.0, _481 + 0.13995198905467987060546875) * 1.020408153533935546875) * 1.39999997615814208984375) - _485) * _493) + _485;
    D _523 = ((exp2(log2(spvNMax(0.0, _482 + 0.13995198905467987060546875) * 1.020408153533935546875) * 1.39999997615814208984375) - _486) * _493) + _486;
    D _528 = (_521 * 0.449999988079071044921875) + _473;
    D _529 = (_522 * 0.449999988079071044921875) + _474;
    D _530 = (_523 * 0.449999988079071044921875) + _475;
    D _537 = dot(vec3(_423, _424, _425), vec3(_241, _243, _244));
    D _543 = (_537 * _423) + _238;
    D _544 = (_537 * _424) + _239;
    D _545 = (_537 * _425) + _240;
    D _549 = abs(_537);
    D _553 = (_543 * 2.0) + (_549 * _423);
    D _554 = (_544 * 2.0) + (_549 * _424);
    D _555 = (_545 * 2.0) + (_549 * _425);
    D _559 = inversesqrt(dot(vec3(_553, _554, _555), vec3(_553, _554, _555)));
    D _560 = _553 * _559;
    D _561 = _554 * _559;
    D _562 = _555 * _559;
    D _563 = spvNMax(9.9999997473787516355514526367188e-06, _549);
    D _582 = 1.0 - _471;
    D _596 = ((spvNMin(_582 * _582, exp2(_563 * (-9.27999973297119140625))) * _582) + (0.0425000004470348358154296875 - (_471 * 0.0274999998509883880615234375))) * 1.03999996185302734375;
    D _602 = 1.0 - spvNClamp((((_471 * 0.02199999988079071044921875) + (-0.039999999105930328369140625)) + _596) + (((1.03999996185302734375 - (_471 * 0.572000026702880859375)) - _596) * 0.159951984882354736328125), 0.0, 1.0);
    D _603 = spvNMax(0.001000000047497451305389404296875, spvNMin(spvNMax(0.0, (View._m0[73u].y - _103) + (1.0 / ((-0.0) - View._m0[73u].w))), _399.x * 100.0));
    D _606 = log2(spvNMax(0.0, _369));
    D _608 = exp2(_606 * _603);
    D _612 = log2(spvNMax(0.0, exp2(_391)));
    D _613 = log2(spvNMax(0.0, exp2(_392)));
    D _614 = log2(spvNMax(0.0, exp2(_393)));
    D _618 = exp2(_612 * _603);
    D _619 = exp2(_613 * _603);
    D _620 = exp2(_614 * _603);
    D _622 = exp2(_606 * 0.001000000047497451305389404296875);
    D _629 = 1.0 - _450;
    D _631 = (_602 * _629) * _608;
    D _634 = ((_631 * _618) * _622) * exp2(_612 * 0.001000000047497451305389404296875);
    D _637 = ((_631 * _619) * _622) * exp2(_613 * 0.001000000047497451305389404296875);
    D _640 = ((_631 * _620) * _622) * exp2(_614 * 0.001000000047497451305389404296875);
    D _647 = spvNMax(0.039999999105930328369140625, _471);
    D _663 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_647 * _563) + 0.02669160068035125732421875) / (_563 + 0.4664950072765350341796875)) * exp2(((1.0 / _647) * _563) * log2(_647)), 0.0, 1.0));
    D _664 = 1.0 - _563;
    D _665 = _664 * _664;
    D _678 = _665 * _665;
    D _680 = (_678 * _664) * exp2(log2((exp2((_647 * 4.7702999114990234375) * log2(_563)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _647);
    D _683 = (1.0 / _663) * (1.0 - _663);
    D _690 = _663 - _680;
    D _697 = ((_683 * _521) + 1.0) * ((_690 * _521) + _680);
    D _698 = ((_683 * _522) + 1.0) * ((_690 * _522) + _680);
    D _699 = ((_683 * _523) + 1.0) * ((_690 * _523) + _680);
    D _705 = spvNClamp(1.0 - dot(vec3(_697, _698, _699), vec3(0.3333333432674407958984375)), 0.0, 1.0);
    D _719 = spvNClamp((_449 + (-1.0)) + exp2(log2(_563 + _449) * exp2((-1.0) - (_471 * 16.0))), 0.0, 1.0);
    D _779;
    D _781;
    D _783;
    D _785;
    D _787;
    D _789;
    D _791;
    D _793;
    D _795;
    if (floatBitsToUint(TranslucentBasePass_2._m0[0u]).z == 0u)
    {
        _779 = 0.0;
        _781 = 0.0;
        _783 = 0.0;
        _785 = 0.0;
        _787 = 0.0;
        _789 = 0.0;
        _791 = 0.0;
        _793 = 0.0;
        _795 = 0.0;
    }
    else
    {
        D _1229;
        uint _810;
        bool _811;
        for (;;)
        {
            _810 = floatBitsToUint(TranslucentBasePass_2._m0[7u]).z;
            _811 = _810 == 0u;
            if (!_811)
            {
                uint _1394;
                uint _1297 = 0u;
                for (;;)
                {
                    if (_103 < TranslucentBasePass._m0[_1297 + 32u])
                    {
                        _1394 = _1297;
                        break;
                    }
                    else
                    {
                        uint _1298 = _1297 + 1u;
                        if (_1298 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                        {
                            _1297 = _1298;
                            continue;
                        }
                        else
                        {
                            _1394 = _810;
                            break;
                        }
                    }
                }
                if (_1394 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                {
                    uint _1744 = _1394 << 2u;
                    uint _1745 = _1744 + 9u;
                    uint _1752 = _1744 + 10u;
                    uint _1759 = _1744 + 11u;
                    uint _1766 = _1744 + 12u;
                    uint _1773 = _1394 + 25u;
                    D _1799 = fma(_232, TranslucentBasePass_2._m0[_1759].z, fma(_231, TranslucentBasePass_2._m0[_1752].z, TranslucentBasePass_2._m0[_1745].z * _230)) + TranslucentBasePass_2._m0[_1766].z;
                    D _1803 = fma(_232, TranslucentBasePass_2._m0[_1759].w, fma(_231, TranslucentBasePass_2._m0[_1752].w, TranslucentBasePass_2._m0[_1745].w * _230)) + TranslucentBasePass_2._m0[_1766].w;
                    D _1804 = (fma(_232, TranslucentBasePass_2._m0[_1759].x, fma(_231, TranslucentBasePass_2._m0[_1752].x, TranslucentBasePass_2._m0[_1745].x * _230)) + TranslucentBasePass_2._m0[_1766].x) / _1803;
                    D _1805 = (fma(_232, TranslucentBasePass_2._m0[_1759].y, fma(_231, TranslucentBasePass_2._m0[_1752].y, TranslucentBasePass_2._m0[_1745].y * _230)) + TranslucentBasePass_2._m0[_1766].y) / _1803;
                    bool _1812 = (_1805 <= TranslucentBasePass_2._m0[_1773].w) && ((_1804 <= TranslucentBasePass_2._m0[_1773].z) && ((_1804 >= TranslucentBasePass_2._m0[_1773].x) && (_1805 >= TranslucentBasePass_2._m0[_1773].y)));
                    D _1230;
                    if (_1812)
                    {
                        D _2169 = dFdyFine(_1804);
                        D _2170 = dFdyFine(_1805);
                        D _2171 = dFdyFine(_1799);
                        D _2172 = dFdxFine(_1804);
                        D _2173 = dFdxFine(_1805);
                        D _2174 = dFdxFine(_1799);
                        D _2177 = (_2173 * _2171) - (_2174 * _2170);
                        D _2180 = (_2174 * _2169) - (_2172 * _2171);
                        D _2183 = (_2172 * _2170) - (_2173 * _2169);
                        D _2193 = 1.0 / spvNMax(abs(_2183), sqrt(((_2180 * _2180) + (_2183 * _2183)) + (_2177 * _2177)) * 0.100000001490116119384765625);
                        D _2199 = D(int(uint(_2183 > 0.0) - uint(_2183 < 0.0)));
                        D _2200 = _2177 * TranslucentBasePass_2._m0[29u].z;
                        D _2202 = (_2200 * _2193) * _2199;
                        D _2203 = _2180 * TranslucentBasePass_2._m0[29u].w;
                        D _2205 = (_2203 * _2193) * _2199;
                        D _2797;
                        D _2799;
                        if (dot(vec2(_2177, _2180), vec2(_2177, _2180)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2797 = 0.0;
                            _2799 = 0.0;
                        }
                        else
                        {
                            D _3167 = (-0.0) - _2177;
                            D _3168 = (-0.0) - _2180;
                            D _3172 = inversesqrt(dot(vec2(_3167, _3168), vec2(_3167, _3168)));
                            _2797 = _3172 * _3167;
                            _2799 = _3172 * _3168;
                        }
                        D _2801 = _266 + (-0.5);
                        D _2806 = _265 + 0.5;
                        D _2809 = ((_2799 * _2801) + (_1804 * TranslucentBasePass_2._m0[29u].x)) + (_2797 * _2806);
                        D _2812 = ((_2797 * _2801) + (_1805 * TranslucentBasePass_2._m0[29u].y)) + (_2799 * _2806);
                        D _2813 = _2809 + (-0.5);
                        D _2814 = _2812 + (-0.5);
                        D _2815 = trunc(_2813);
                        D _2816 = trunc(_2814);
                        D _2817 = _2813 - _2815;
                        D _2818 = _2814 - _2816;
                        D _2819 = _2815 * TranslucentBasePass_2._m0[29u].z;
                        D _2820 = _2816 * TranslucentBasePass_2._m0[29u].w;
                        D _2823 = (_2815 + (-0.5)) - _2809;
                        D _2824 = (_2816 + (-0.5)) - _2812;
                        D _2825 = dot(vec2(_2823, _2824), vec2(_2202, _2205));
                        D _2828 = _2825 + _2205;
                        D _2831 = _2199 * (_2193 * (_2203 + _2200));
                        D _2832 = _2831 + _2825;
                        D _2833 = _2825 + _2202;
                        vec4 _2839 = textureGather((sampler2D(ShadowMaps[_1394 + 0u], View_SharedPointClampedSampler)), vec2(_2819, _2820));
                        D _2840 = _2839.x;
                        D _2841 = _2839.y;
                        D _2842 = _2839.z;
                        D _2843 = _2839.w;
                        D _2880 = 1.525902189314365386962890625e-05 - _1799;
                        D _2911 = (_2815 + 1.5) - _2809;
                        D _2912 = dot(vec2(_2911, _2824), vec2(_2202, _2205));
                        D _2915 = _2912 + _2205;
                        D _2916 = _2831 + _2912;
                        D _2917 = _2912 + _2202;
                        vec4 _2919 = textureGatherOffset((sampler2D(ShadowMaps[_1394 + 0u], View_SharedPointClampedSampler)), vec2(_2819, _2820), ivec2(2, 0));
                        D _2920 = _2919.x;
                        D _2921 = _2919.y;
                        D _2922 = _2919.z;
                        D _2923 = _2919.w;
                        D _2989 = (_2816 + 1.5) - _2812;
                        D _2990 = dot(vec2(_2823, _2989), vec2(_2202, _2205));
                        D _2993 = _2990 + _2205;
                        D _2994 = _2831 + _2990;
                        D _2995 = _2990 + _2202;
                        vec4 _2997 = textureGatherOffset((sampler2D(ShadowMaps[_1394 + 0u], View_SharedPointClampedSampler)), vec2(_2819, _2820), ivec2(0, 2));
                        D _2998 = _2997.x;
                        D _2999 = _2997.y;
                        D _3000 = _2997.z;
                        D _3001 = _2997.w;
                        D _3066 = dot(vec2(_2911, _2989), vec2(_2202, _2205));
                        D _3069 = _3066 + _2205;
                        D _3070 = _2831 + _3066;
                        D _3071 = _3066 + _2202;
                        vec4 _3073 = textureGatherOffset((sampler2D(ShadowMaps[_1394 + 0u], View_SharedPointClampedSampler)), vec2(_2819, _2820), ivec2(2));
                        D _3074 = _3073.x;
                        D _3075 = _3073.y;
                        D _3076 = _3073.z;
                        D _3077 = _3073.w;
                        D _3142 = 1.0 - _2817;
                        vec4 _3165 = vec4((((((_2843 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2880 + _2843) + (spvNMin(abs(_2825), 0.0) * D(int(uint(_2825 > 0.0) - uint(_2825 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3142) + ((_2842 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2880 + _2842) + (spvNMin(abs(_2833), 0.0) * D(int(uint(_2833 > 0.0) - uint(_2833 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2923 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2880 + _2923) + (spvNMin(abs(_2912), 0.0) * D(int(uint(_2912 > 0.0) - uint(_2912 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2922 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2880 + _2922) + (spvNMin(abs(_2917), 0.0) * D(int(uint(_2917 > 0.0) - uint(_2917 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2817), (((((_2840 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2880 + _2840) + (spvNMin(abs(_2828), 0.0) * D(int(uint(_2828 > 0.0) - uint(_2828 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3142) + ((_2841 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2880 + _2841) + (spvNMin(abs(_2832), 0.0) * D(int(uint(_2832 > 0.0) - uint(_2832 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2920 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2880 + _2920) + (spvNMin(abs(_2915), 0.0) * D(int(uint(_2915 > 0.0) - uint(_2915 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2921 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2880 + _2921) + (spvNMin(abs(_2916), 0.0) * D(int(uint(_2916 > 0.0) - uint(_2916 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2817), (((((_3001 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2880 + _3001) + (spvNMin(abs(_2990), 0.0) * D(int(uint(_2990 > 0.0) - uint(_2990 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3142) + ((_3000 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2880 + _3000) + (spvNMin(abs(_2995), 0.0) * D(int(uint(_2995 > 0.0) - uint(_2995 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3077 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2880 + _3077) + (spvNMin(abs(_3066), 0.0) * D(int(uint(_3066 > 0.0) - uint(_3066 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3076 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2880 + _3076) + (spvNMin(abs(_3071), 0.0) * D(int(uint(_3071 > 0.0) - uint(_3071 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2817), (((((_2998 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2880 + _2998) + (spvNMin(abs(_2993), 0.0) * D(int(uint(_2993 > 0.0) - uint(_2993 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3142) + ((_2999 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2880 + _2999) + (spvNMin(abs(_2994), 0.0) * D(int(uint(_2994 > 0.0) - uint(_2994 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3074 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2880 + _3074) + (spvNMin(abs(_3069), 0.0) * D(int(uint(_3069 > 0.0) - uint(_3069 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3075 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2880 + _3075) + (spvNMin(abs(_3070), 0.0) * D(int(uint(_3070 > 0.0) - uint(_3070 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2817));
                        _1230 = dot(_3165, vec4(1.0 - _2818, 1.0, 1.0, _2818)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        _1230 = 1.0;
                    }
                    if (_1812)
                    {
                        _1229 = _1230;
                        break;
                    }
                }
            }
            if (floatBitsToUint(TranslucentBasePass_2._m0[30u]).y == 0u)
            {
                _1229 = 1.0;
                break;
            }
            D _1270 = fma(_232, TranslucentBasePass_2._m0[35u].z, fma(_231, TranslucentBasePass_2._m0[34u].z, TranslucentBasePass_2._m0[33u].z * _230)) + TranslucentBasePass_2._m0[36u].z;
            D _1274 = fma(_232, TranslucentBasePass_2._m0[35u].w, fma(_231, TranslucentBasePass_2._m0[34u].w, TranslucentBasePass_2._m0[33u].w * _230)) + TranslucentBasePass_2._m0[36u].w;
            D _1275 = (fma(_232, TranslucentBasePass_2._m0[35u].x, fma(_231, TranslucentBasePass_2._m0[34u].x, TranslucentBasePass_2._m0[33u].x * _230)) + TranslucentBasePass_2._m0[36u].x) / _1274;
            D _1276 = (fma(_232, TranslucentBasePass_2._m0[35u].y, fma(_231, TranslucentBasePass_2._m0[34u].y, TranslucentBasePass_2._m0[33u].y * _230)) + TranslucentBasePass_2._m0[36u].y) / _1274;
            uvec4 _1280 = floatBitsToUint(TranslucentBasePass_2._m0[32u]);
            uint _1281 = _1280.x;
            uint _1282 = _1280.y;
            uint _1283 = _1280.z;
            uint _1288 = uint(int(floor(_1275)));
            uint _1289 = uint(int((-0.0) - floor(_1276)));
            if (!((int(_1289) < int(_1280.w)) && ((int(_1288) < int(_1283)) && ((int(_1288) >= int(_1281)) && (int(_1289) >= int(_1282))))))
            {
                _1229 = 1.0;
                break;
            }
            D _1357 = dFdyFine(_1275);
            D _1358 = dFdyFine(_1276);
            D _1359 = dFdyFine(_1270);
            D _1360 = dFdxFine(_1275);
            D _1361 = dFdxFine(_1276);
            D _1362 = dFdxFine(_1270);
            D _1365 = (_1361 * _1359) - (_1362 * _1358);
            D _1368 = (_1362 * _1357) - (_1360 * _1359);
            D _1371 = (_1360 * _1358) - (_1361 * _1357);
            D _1382 = 1.0 / spvNMax(abs(_1371), sqrt(((_1368 * _1368) + (_1371 * _1371)) + (_1365 * _1365)) * 0.100000001490116119384765625);
            D _1388 = D(int(uint(_1371 > 0.0) - uint(_1371 < 0.0)));
            D _1671;
            D _1673;
            if (dot(vec2(_1365, _1368), vec2(_1365, _1368)) < 1.0000000195414813782625560981111e-24)
            {
                _1671 = 0.0;
                _1673 = 0.0;
            }
            else
            {
                D _1737 = (-0.0) - _1365;
                D _1738 = (-0.0) - _1368;
                D _1742 = inversesqrt(dot(vec2(_1737, _1738), vec2(_1737, _1738)));
                _1671 = _1742 * _1737;
                _1673 = _1742 * _1738;
            }
            D _1679 = _266 + (-0.5);
            D _1687 = (((_1673 * _1679) + (_1671 * _265)) * 2.0) + (_1671 * 0.5);
            D _1688 = (((_1673 * _265) + (_1671 * _1679)) * 2.0) + (_1673 * 0.5);
            D _1694 = _1687 + (fract(_1275) * 256.0);
            D _1695 = _1688 + (fract(_1276) * 256.0);
            D _1708 = dot(vec2((floor(_1694) + 0.5) - _1694, (floor(_1695) + 0.5) - _1695), vec2(((_1365 * 256.0) * _1382) * _1388, ((_1368 * 256.0) * _1382) * _1388));
            D _1714 = (_1687 * 0.00390625) + _1275;
            D _1715 = (_1688 * 0.00390625) + _1276;
            uint _1727 = ((uint(int((-0.0) - floor(_1715))) - _1282) * (_1283 - _1281)) + (uint(int(floor(_1714))) - _1281);
            D _2141;
            D _2144;
            if ((texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowLoadedTileData, int(_1727 >> 5u)).x & (1u << (_1727 & 31u))) == 0u)
            {
                _2141 = 3.0000000054977557577780399428115e+38;
                _2144 = 0.0;
            }
            else
            {
                uvec4 _2166 = uvec4(texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileIndices, int(_1727)));
                uint _2167 = _2166.x;
                D frontier_phi_51_52_ladder;
                D frontier_phi_51_52_ladder_1;
                if (int(_2167) > int(4294967295u))
                {
                    uint _2783 = (uint(floor(fract(_1714) * 256.0)) + (_2167 << 16u)) + (uint(floor(fract(_1715) * 256.0)) << 8u);
                    uvec4 _2786 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileData, int(_2783 >> 1u));
                    uint _2787 = _2786.x;
                    D _2795 = D((((_2783 & 1u) == 0u) ? _2787 : (_2787 >> 16u)) & 65535u) * 1.525902189314365386962890625e-05;
                    D frontier_phi_51_52_ladder_73_ladder;
                    D frontier_phi_51_52_ladder_73_ladder_1;
                    if (_2795 != 1.0)
                    {
                        vec4 _3596 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthRanges, int(_2167));
                        D _3598 = _3596.y;
                        frontier_phi_51_52_ladder_73_ladder = 1.0 / _3598;
                        frontier_phi_51_52_ladder_73_ladder_1 = (_3598 * _2795) + _3596.x;
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
                _2141 = frontier_phi_51_52_ladder_1;
                _2144 = frontier_phi_51_52_ladder;
            }
            _1229 = spvNClamp(((((1.525902189314365386962890625e-05 - _1270) + _2141) + (spvNMin(abs(_1708), _2144 * 10.0) * D(int(uint(_1708 > 0.0) - uint(_1708 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0);
            break;
        }
        D _1344;
        if ((floatBitsToUint(Primitive._m0[27u]).z & 2u) == 0u)
        {
            _1344 = 1.0;
        }
        else
        {
            _1344 = View._m0[188u].y;
        }
        uvec4 _1348 = floatBitsToUint(View._m0[220u]);
        uint _1349 = _1348.y;
        uint _1352 = (_1349 != 1u) ? 4294967295u : 0u;
        uint _1669;
        if (_1349 > 1u)
        {
            D _131[4];
            _131[0u] = 0.0;
            _131[1u] = 0.0;
            _131[2u] = 0.0;
            _131[3u] = 0.0;
            uint _2126 = 0u;
            bool _2132;
            for (;;)
            {
                _2132 = _2126 < floatBitsToUint(View._m0[220u]).y;
                if (_2132)
                {
                    uint _2734 = _2126 + 237u;
                    D _2748 = View._m0[_2734].x - View._m0[75u].x;
                    D _2749 = View._m0[_2734].y - View._m0[75u].y;
                    D _2750 = View._m0[_2734].z - View._m0[75u].z;
                    D _2751 = dot(vec3(_2748, _2749, _2750), vec3(_238, _239, _240));
                    D _2758 = dot(vec3(_2748, _2749, _2750), vec3(_2748, _2749, _2750)) - (View._m0[_2734].w * View._m0[_2734].w);
                    D _2760 = (_2751 * _2751) - _2758;
                    D _3372;
                    if ((_2758 < 0.0) && (!(_2760 < 0.0)))
                    {
                        D _3366 = sqrt(_2760);
                        _3372 = spvNMin(abs(_3366 + _2751), abs(_2751 - _3366));
                    }
                    else
                    {
                        _3372 = 0.0;
                    }
                    _131[_2126] = _3372;
                }
                uint _2127 = _2126 + 1u;
                if (_2127 == 4u)
                {
                    break;
                }
                else
                {
                    _2126 = _2127;
                    continue;
                }
            }
            D _3383 = (_265 * 0.99989998340606689453125) * dot(vec4(_131[0u], _131[1u], _131[2u], _131[3u]), vec4(1.0));
            uint frontier_phi_32_83_ladder;
            if (_131[0u] > _3383)
            {
                frontier_phi_32_83_ladder = 0u;
            }
            else
            {
                D _3734 = _131[1u] + _131[0u];
                uint frontier_phi_32_83_ladder_94_ladder;
                if (_3734 > _3383)
                {
                    frontier_phi_32_83_ladder_94_ladder = 1u;
                }
                else
                {
                    D _3818 = _3734 + _131[2u];
                    uint frontier_phi_32_83_ladder_94_ladder_102_ladder;
                    if (_3818 > _3383)
                    {
                        frontier_phi_32_83_ladder_94_ladder_102_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder;
                        if ((_3818 + _131[3u]) > _3383)
                        {
                            frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder = _1352;
                        }
                        frontier_phi_32_83_ladder_94_ladder_102_ladder = frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder;
                    }
                    frontier_phi_32_83_ladder_94_ladder = frontier_phi_32_83_ladder_94_ladder_102_ladder;
                }
                frontier_phi_32_83_ladder = frontier_phi_32_83_ladder_94_ladder;
            }
            _1669 = frontier_phi_32_83_ladder;
        }
        else
        {
            _1669 = _1352;
        }
        D _2133;
        if (_1669 == 4294967295u)
        {
            _2133 = _1344;
        }
        else
        {
            _2133 = View._m0[_1669 + 241u].x * _1344;
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
        if (_2133 > 0.0)
        {
            D _2767 = spvNClamp((TranslucentBasePass_2._m0[7u].x * _103) + TranslucentBasePass_2._m0[7u].y, 0.0, 1.0);
            D _2771 = ((_2767 * _2767) * (1.0 - _1229)) + _1229;
            D frontier_phi_3_49_ladder_72_ladder;
            D frontier_phi_3_49_ladder_72_ladder_1;
            D frontier_phi_3_49_ladder_72_ladder_2;
            D frontier_phi_3_49_ladder_72_ladder_3;
            D frontier_phi_3_49_ladder_72_ladder_4;
            D frontier_phi_3_49_ladder_72_ladder_5;
            D frontier_phi_3_49_ladder_72_ladder_6;
            D frontier_phi_3_49_ladder_72_ladder_7;
            D frontier_phi_3_49_ladder_72_ladder_8;
            if (_2771 > 0.0)
            {
                D _3385 = dot(vec3(_423, _424, _425), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3388 = spvNMax(0.0, _3385);
                D _3389 = dot(vec3(_241, _243, _244), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3395 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3389 * 2.0) + 2.0));
                D _3398 = spvNClamp(_3395 * (_537 + _3385), 0.0, 1.0);
                D _3413 = sqrt(spvNMax(0.0, 1.0 - ((1.0 - (_537 * _537)) * 0.444444477558135986328125)));
                D _3417 = (_543 * 0.666666686534881591796875) - (_3413 * _423);
                D _3418 = (_544 * 0.666666686534881591796875) - (_3413 * _424);
                D _3419 = (_545 * 0.666666686534881591796875) - (_3413 * _425);
                D _3423 = inversesqrt(dot(vec3(_3417, _3418, _3419), vec3(_3417, _3418, _3419)));
                D _3430 = dot(vec3((-0.0) - (_3423 * _3417), (-0.0) - (_3423 * _3418), (-0.0) - (_3423 * _3419)), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3433 = _647 * _647;
                D _3434 = _3433 * _3433;
                D _3438 = ((_3398 * _3398) * (_3434 + (-1.0))) + 1.0;
                D _3444 = (_3388 * 2.0) * _563;
                D _3449 = 1.0 - spvNMax(9.9999997473787516355514526367188e-06, spvNMin(_3395 * (_3389 + 1.0), 1.0));
                D _3450 = _3449 * _3449;
                D _3452 = (_3450 * _3450) * _3449;
                D _3457 = spvNMin(dot(vec3(_521, _522, _523), vec3(16.666667938232421875)), 1.0);
                D _3470 = spvNMax(0.039999999105930328369140625, _647);
                D _3483 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_3470 * _3388) + 0.02669160068035125732421875) / (_3388 + 0.4664950072765350341796875)) * exp2(((1.0 / _3470) * _3388) * log2(_3470)), 0.0, 1.0));
                D _3484 = 1.0 - _3388;
                D _3485 = _3484 * _3484;
                D _3497 = ((_3485 * _3485) * _3484) * exp2(log2((exp2((_3470 * 4.7702999114990234375) * log2(_3388)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _3470);
                D _3500 = (1.0 / _3483) * (1.0 - _3483);
                D _3504 = (_3500 * _521) + 1.0;
                D _3505 = (_3500 * _522) + 1.0;
                D _3506 = (_3500 * _523) + 1.0;
                D _3507 = _3483 - _3497;
                D _3521 = spvNClamp(1.0 - dot(vec3(_3504 * ((_3507 * _521) + _3497), _3505 * ((_3507 * _522) + _3497), _3506 * ((_3507 * _523) + _3497)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                D _3524 = (((_3434 * 0.3183098733425140380859375) * _3388) * (1.0 / (_3438 * _3438))) * (0.5 / ((_3433 * ((_563 + _3388) - _3444)) + _3444));
                D _3525 = _3388 * 0.3183098733425140380859375;
                D _3528 = ((_3430 * _3430) + 1.0) * 0.05968309938907623291015625;
                D _3530 = spvNMin(1.0, _449);
                D _3532 = (_449 + 1.0) - _3530;
                D _3533 = _3532 * _3532;
                D _3536 = 1.0 - ((_3533 * _3533) * _3532);
                D _3537 = _3536 * _3536;
                D _3542 = ((_3537 * _3537) * (_3536 * (_449 - _3530))) + _3530;
                D _3545 = sqrt(spvNMax(0.0, 1.0 - _3542));
                D _3550 = 1.0 - spvNClamp((_647 * 3.5) + (-0.5), 0.0, 1.0);
                D _3551 = _3550 * _3550;
                D _3561 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_678 * _3545) * spvNClamp(1.0 - ((_3551 * _3551) * _3550), 0.0, 1.0))) * _3388, 0.0, 1.0);
                D _3566 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _3545)) * _3388, 0.0, 1.0);
                D _3568 = spvNMin(_2771, _3561 * _3561);
                D _3569 = spvNMin(_2771, _3566 * _3566);
                D _3570 = spvNMin(_2771, _3542);
                D _3571 = _2133 * TranslucentBasePass_2._m0[4u].x;
                D _3572 = _2133 * TranslucentBasePass_2._m0[4u].y;
                D _3573 = _2133 * TranslucentBasePass_2._m0[4u].z;
                frontier_phi_3_49_ladder_72_ladder = (_3528 * _3573) * _3570;
                frontier_phi_3_49_ladder_72_ladder_1 = (((_3571 * _473) * _3525) * _3521) * _3569;
                frontier_phi_3_49_ladder_72_ladder_2 = (((_3572 * _474) * _3525) * _3521) * _3569;
                frontier_phi_3_49_ladder_72_ladder_3 = (((_3573 * _475) * _3525) * _3521) * _3569;
                frontier_phi_3_49_ladder_72_ladder_4 = (((_3524 * _3571) * spvNClamp(((_3457 - _521) * _3452) + _521, 0.0, 1.0)) * _3504) * _3568;
                frontier_phi_3_49_ladder_72_ladder_5 = (((_3524 * _3572) * spvNClamp(((_3457 - _522) * _3452) + _522, 0.0, 1.0)) * _3505) * _3568;
                frontier_phi_3_49_ladder_72_ladder_6 = (((_3524 * _3573) * spvNClamp(((_3457 - _523) * _3452) + _523, 0.0, 1.0)) * _3506) * _3568;
                frontier_phi_3_49_ladder_72_ladder_7 = (_3528 * _3571) * _3570;
                frontier_phi_3_49_ladder_72_ladder_8 = (_3528 * _3572) * _3570;
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
        _779 = frontier_phi_3_49_ladder_1;
        _781 = frontier_phi_3_49_ladder_2;
        _783 = frontier_phi_3_49_ladder_3;
        _785 = frontier_phi_3_49_ladder_4;
        _787 = frontier_phi_3_49_ladder_5;
        _789 = frontier_phi_3_49_ladder_6;
        _791 = frontier_phi_3_49_ladder_7;
        _793 = frontier_phi_3_49_ladder_8;
        _795 = frontier_phi_3_49_ladder;
    }
    uvec4 _799 = floatBitsToUint(TranslucentBasePass_2._m0[0u]);
    uint _800 = _799.x;
    uint _805 = min(min(texelFetch(TranslucentBasePass_Shared_Forward_NumCulledLightsGrid, int(0u)).x, _800), _800);
    D _812;
    D _814;
    D _816;
    D _818;
    D _820;
    D _822;
    D _824;
    D _826;
    D _828;
    D _830;
    D _832;
    D _834;
    D _836;
    D _838;
    D _840;
    if (_805 == 0u)
    {
        _812 = _779;
        _814 = _781;
        _816 = _783;
        _818 = _785;
        _820 = _787;
        _822 = _789;
        _824 = _791;
        _826 = _793;
        _828 = _795;
        _830 = 0.0;
        _832 = 0.0;
        _834 = 0.0;
        _836 = 0.0;
        _838 = 0.0;
        _840 = 0.0;
    }
    else
    {
        D _813;
        D _815;
        D _817;
        D _819;
        D _821;
        D _823;
        D _825;
        D _827;
        D _829;
        D _831;
        D _833;
        D _835;
        D _837;
        D _839;
        D _841;
        D _1144 = _779;
        D _1145 = _781;
        D _1146 = _783;
        D _1147 = _785;
        D _1148 = _787;
        D _1149 = _789;
        D _1150 = _791;
        D _1151 = _793;
        D _1152 = _795;
        D _1153 = 0.0;
        D _1154 = 0.0;
        D _1155 = 0.0;
        D _1156 = 0.0;
        D _1157 = 0.0;
        D _1158 = 0.0;
        uint _1159 = 0u;
        D _1163;
        D _1164;
        D _1165;
        D _1166;
        D _1168;
        D _1169;
        D _1170;
        D _1172;
        D _1173;
        D _1174;
        uint _1176;
        D _1178;
        D _1179;
        D _1181;
        D _1182;
        D _1183;
        D _1185;
        D _1186;
        uint _1188;
        D _1191;
        D _1192;
        D _1193;
        D _1194;
        uint _1197;
        D _1199;
        D _1200;
        D _1201;
        D _1202;
        D _1205;
        D _1206;
        D _1207;
        D _1208;
        D _1211;
        D _1212;
        D _1213;
        D _1214;
        D _1217;
        D _1218;
        D _1219;
        D _1220;
        bool _1223;
        bool _1224;
        bool _1228;
        for (;;)
        {
            vec4 _1162 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(0u));
            _1163 = _1162.x;
            _1164 = _1162.y;
            _1165 = _1162.z;
            _1166 = _1162.w;
            vec4 _1167 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(1u));
            _1168 = _1167.x;
            _1169 = _1167.y;
            _1170 = _1167.z;
            vec4 _1171 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(2u));
            _1172 = _1171.x;
            _1173 = _1171.y;
            _1174 = _1171.z;
            _1176 = floatBitsToUint(_1171.w);
            vec4 _1177 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(3u));
            _1178 = _1177.x;
            _1179 = _1177.y;
            vec4 _1180 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(4u));
            _1181 = _1180.x;
            _1182 = _1180.y;
            _1183 = _1180.z;
            vec4 _1184 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(5u));
            _1185 = _1184.x;
            _1186 = _1184.y;
            _1188 = floatBitsToUint(_1184.z);
            vec4 _1190 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(6u));
            _1191 = _1190.x;
            _1192 = _1190.y;
            _1193 = _1190.z;
            _1194 = _1190.w;
            _1197 = floatBitsToUint(texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(7u)).x);
            vec4 _1198 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(8u));
            _1199 = _1198.x;
            _1200 = _1198.y;
            _1201 = _1198.z;
            _1202 = _1198.w;
            vec4 _1204 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(9u));
            _1205 = _1204.x;
            _1206 = _1204.y;
            _1207 = _1204.z;
            _1208 = _1204.w;
            vec4 _1210 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(10u));
            _1211 = _1210.x;
            _1212 = _1210.y;
            _1213 = _1210.z;
            _1214 = _1210.w;
            vec4 _1216 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(11u));
            _1217 = _1216.x;
            _1218 = _1216.y;
            _1219 = _1216.z;
            _1220 = _1216.w;
            _1223 = (_1176 & 131072u) != 0u;
            _1224 = _1178 > (-2.0);
            _1228 = (_1176 & 16384u) == 0u;
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
            if (_1228)
            {
                D _1622;
                if (_1223)
                {
                    uint _1587 = _1197 + 0u;
                    uvec2 _1590 = uvec2(textureSize(ShadowMaps[(_1587)], int(0u)));
                    D _1592 = D(int(_1590.x));
                    D _1594 = D(int(_1590.y));
                    D _1595 = 1.0 / _1592;
                    D _1596 = 1.0 / _1594;
                    D _1608 = fma(_232, _1213, fma(_231, _1207, _1201 * _230)) + _1219;
                    D _1612 = fma(_232, _1214, fma(_231, _1208, _1202 * _230)) + _1220;
                    D _1613 = (fma(_232, _1211, fma(_231, _1205, _1199 * _230)) + _1217) / _1612;
                    D _1614 = (fma(_232, _1212, fma(_231, _1206, _1200 * _230)) + _1218) / _1612;
                    D frontier_phi_28_27_ladder;
                    if ((_1614 <= _1194) && ((_1613 <= _1193) && ((_1613 >= _1191) && (_1614 >= _1192))))
                    {
                        D _2010 = dFdyFine(_1613);
                        D _2011 = dFdyFine(_1614);
                        D _2012 = dFdyFine(_1608);
                        D _2013 = dFdxFine(_1613);
                        D _2014 = dFdxFine(_1614);
                        D _2015 = dFdxFine(_1608);
                        D _2018 = (_2014 * _2012) - (_2015 * _2011);
                        D _2021 = (_2015 * _2010) - (_2013 * _2012);
                        D _2024 = (_2013 * _2011) - (_2014 * _2010);
                        D _2034 = 1.0 / spvNMax(abs(_2024), sqrt(((_2021 * _2021) + (_2024 * _2024)) + (_2018 * _2018)) * 0.100000001490116119384765625);
                        D _2040 = D(int(uint(_2024 > 0.0) - uint(_2024 < 0.0)));
                        D _2041 = _2018 * _1595;
                        D _2043 = (_2041 * _2034) * _2040;
                        D _2044 = _2021 * _1596;
                        D _2046 = (_2044 * _2034) * _2040;
                        D _2329;
                        D _2331;
                        if (dot(vec2(_2018, _2021), vec2(_2018, _2021)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2329 = 0.0;
                            _2331 = 0.0;
                        }
                        else
                        {
                            D _2672 = (-0.0) - _2018;
                            D _2673 = (-0.0) - _2021;
                            D _2677 = inversesqrt(dot(vec2(_2672, _2673), vec2(_2672, _2673)));
                            _2329 = _2677 * _2672;
                            _2331 = _2677 * _2673;
                        }
                        D _2333 = _266 + (-0.5);
                        D _2338 = _265 + 0.5;
                        D _2341 = ((_2331 * _2333) + (_1613 * _1592)) + (_2329 * _2338);
                        D _2344 = ((_2329 * _2333) + (_1614 * _1594)) + (_2331 * _2338);
                        D _2345 = _2341 + (-0.5);
                        D _2346 = _2344 + (-0.5);
                        D _2347 = trunc(_2345);
                        D _2348 = trunc(_2346);
                        D _2349 = _2345 - _2347;
                        D _2350 = _2346 - _2348;
                        D _2351 = _2347 * _1595;
                        D _2352 = _2348 * _1596;
                        D _2355 = (_2347 + (-0.5)) - _2341;
                        D _2356 = (_2348 + (-0.5)) - _2344;
                        D _2357 = dot(vec2(_2355, _2356), vec2(_2043, _2046));
                        D _2360 = _2357 + _2046;
                        D _2363 = _2040 * (_2034 * (_2044 + _2041));
                        D _2364 = _2363 + _2357;
                        D _2365 = _2357 + _2043;
                        vec4 _2369 = textureGather((sampler2D(ShadowMaps[_1587], View_SharedPointClampedSampler)), vec2(_2351, _2352));
                        D _2410 = 1.525902189314365386962890625e-05 - _1608;
                        D _2433 = (_2347 + 1.5) - _2341;
                        D _2434 = dot(vec2(_2433, _2356), vec2(_2043, _2046));
                        D _2437 = _2434 + _2046;
                        D _2438 = _2363 + _2434;
                        D _2439 = _2434 + _2043;
                        vec4 _2443 = textureGatherOffset((sampler2D(ShadowMaps[_1587], View_SharedPointClampedSampler)), vec2(_2351, _2352), ivec2(2, 0));
                        D _2507 = (_2348 + 1.5) - _2344;
                        D _2508 = dot(vec2(_2355, _2507), vec2(_2043, _2046));
                        D _2511 = _2508 + _2046;
                        D _2512 = _2363 + _2508;
                        D _2513 = _2508 + _2043;
                        vec4 _2515 = textureGatherOffset((sampler2D(ShadowMaps[_1587], View_SharedPointClampedSampler)), vec2(_2351, _2352), ivec2(0, 2));
                        D _2577 = dot(vec2(_2433, _2507), vec2(_2043, _2046));
                        D _2580 = _2577 + _2046;
                        D _2581 = _2363 + _2577;
                        D _2582 = _2577 + _2043;
                        vec4 _2584 = textureGatherOffset((sampler2D(ShadowMaps[_1587], View_SharedPointClampedSampler)), vec2(_2351, _2352), ivec2(2));
                        D _2646 = 1.0 - _2349;
                        vec4 _2669 = vec4((((spvNClamp((((_2410 + _2369.w) + (spvNMin(abs(_2357), 0.0) * D(int(uint(_2357 > 0.0) - uint(_2357 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2646) + spvNClamp((((_2410 + _2369.z) + (spvNMin(abs(_2365), 0.0) * D(int(uint(_2365 > 0.0) - uint(_2365 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2410 + _2443.w) + (spvNMin(abs(_2434), 0.0) * D(int(uint(_2434 > 0.0) - uint(_2434 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2410 + _2443.z) + (spvNMin(abs(_2439), 0.0) * D(int(uint(_2439 > 0.0) - uint(_2439 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2349), (((spvNClamp((((_2410 + _2369.x) + (spvNMin(abs(_2360), 0.0) * D(int(uint(_2360 > 0.0) - uint(_2360 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2646) + spvNClamp((((_2410 + _2369.y) + (spvNMin(abs(_2364), 0.0) * D(int(uint(_2364 > 0.0) - uint(_2364 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2410 + _2443.x) + (spvNMin(abs(_2437), 0.0) * D(int(uint(_2437 > 0.0) - uint(_2437 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2410 + _2443.y) + (spvNMin(abs(_2438), 0.0) * D(int(uint(_2438 > 0.0) - uint(_2438 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2349), (((spvNClamp((((_2410 + _2515.w) + (spvNMin(abs(_2508), 0.0) * D(int(uint(_2508 > 0.0) - uint(_2508 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2646) + spvNClamp((((_2410 + _2515.z) + (spvNMin(abs(_2513), 0.0) * D(int(uint(_2513 > 0.0) - uint(_2513 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2410 + _2584.w) + (spvNMin(abs(_2577), 0.0) * D(int(uint(_2577 > 0.0) - uint(_2577 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2410 + _2584.z) + (spvNMin(abs(_2582), 0.0) * D(int(uint(_2582 > 0.0) - uint(_2582 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2349), (((spvNClamp((((_2410 + _2515.x) + (spvNMin(abs(_2511), 0.0) * D(int(uint(_2511 > 0.0) - uint(_2511 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2646) + spvNClamp((((_2410 + _2515.y) + (spvNMin(abs(_2512), 0.0) * D(int(uint(_2512 > 0.0) - uint(_2512 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2410 + _2584.x) + (spvNMin(abs(_2580), 0.0) * D(int(uint(_2580 > 0.0) - uint(_2580 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2410 + _2584.y) + (spvNMin(abs(_2581), 0.0) * D(int(uint(_2581 > 0.0) - uint(_2581 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2349));
                        frontier_phi_28_27_ladder = dot(_2669, vec4(1.0 - _2350, 1.0, 1.0, _2350)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        frontier_phi_28_27_ladder = 1.0;
                    }
                    _1622 = frontier_phi_28_27_ladder;
                }
                else
                {
                    _1622 = 1.0;
                }
                D _1628 = _1163 - _230;
                D _1629 = _1164 - _231;
                D _1630 = _1165 - _232;
                D _1631 = dot(vec3(_1628, _1629, _1630), vec3(_1628, _1629, _1630));
                D _2055;
                D _2056;
                D _2057;
                if (_1631 > 9.9999997473787516355514526367188e-05)
                {
                    D _2051 = inversesqrt(_1631);
                    _2055 = _2051 * _1628;
                    _2056 = _2051 * _1629;
                    _2057 = _2051 * _1630;
                }
                else
                {
                    _2055 = 0.0;
                    _2056 = 0.0;
                    _2057 = 0.0;
                }
                D _2058 = _1185 * _1185;
                D _2062 = (_1166 * _1166) * _1631;
                D _2065 = spvNClamp(1.0 - (_2062 * _2062), 0.0, 1.0);
                D _2685;
                if (_1224)
                {
                    D _2683 = spvNClamp((dot(vec3(_2055, _2056, _2057), vec3(_1172, _1173, _1174)) - _1178) * _1179, 0.0, 1.0);
                    _2685 = _2683 * _2683;
                }
                else
                {
                    _2685 = 1.0;
                }
                D _2686 = ((_2065 * _2065) * D(_1631 >= _2058)) * _2685;
                D _3229;
                D _3231;
                D _3233;
                if ((_1176 & 262144u) == 0u)
                {
                    _3229 = 1.0;
                    _3231 = 1.0;
                    _3233 = 1.0;
                }
                else
                {
                    D _3236 = (-0.0) - _1173;
                    D _3237 = (-0.0) - _1174;
                    D _3238 = (-0.0) - _1172;
                    D _3248 = (-0.0) - _2055;
                    D _3249 = (-0.0) - _2056;
                    D _3250 = (-0.0) - _2057;
                    D _3253 = fma(_3237, _3250, fma(_3236, _3249, _2055 * _1172));
                    D _3256 = fma(_1183, _3250, fma(_1182, _3249, _1181 * _3248));
                    D _3264 = atan(((-0.0) - _3256) / ((-0.0) - _3253));
                    bool _3269 = _3253 > (-0.0);
                    bool _3270 = _3253 == (-0.0);
                    bool _3271 = _3256 <= (-0.0);
                    bool _3272 = _3256 > (-0.0);
                    vec4 _3294 = texture((sampler2D(ForwardLightProfileTextures[_1188 + 0u], View_SharedBilinearWrappedSampler)), vec2(fract((_3270 && _3271) ? 1.25 : ((_3270 && _3272) ? 0.75 : ((((_3269 && _3272) ? (_3264 + (-3.1415927410125732421875)) : ((_3269 && _3271) ? (_3264 + 3.1415927410125732421875) : _3264)) * 0.15915493667125701904296875) + 1.0))), (asin((-0.0) - fma((_1182 * _3238) - (_1181 * _3236), _3250, fma((_1181 * _3237) - (_1183 * _3238), _3249, ((_1183 * _3236) - (_1182 * _3237)) * _3248))) * 0.3183098733425140380859375) + 0.5));
                    _3229 = _3294.x;
                    _3231 = _3294.y;
                    _3233 = _3294.z;
                }
                D _3685;
                D _3687;
                D _3689;
                D _3691;
                D _3693;
                D _3695;
                D _3697;
                D _3699;
                D _3701;
                for (;;)
                {
                    if (_2686 > 0.0)
                    {
                        D _3810;
                        if (_1223)
                        {
                            if (!(_1622 > 0.0))
                            {
                                _3685 = 0.0;
                                _3687 = 0.0;
                                _3689 = 0.0;
                                _3691 = 0.0;
                                _3693 = 0.0;
                                _3695 = 0.0;
                                _3697 = 0.0;
                                _3699 = 0.0;
                                _3701 = 0.0;
                                break;
                            }
                            _3810 = _1622;
                        }
                        else
                        {
                            _3810 = 1.0;
                        }
                        D _3812 = spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1631));
                        D _3813 = 1.0 / _3812;
                        D _3814 = dot(vec3(_423, _424, _425), vec3(_2055, _2056, _2057));
                        D _3835;
                        if (_1185 > 0.0)
                        {
                            D _3832 = sqrt(spvNClamp(_2058 * _3813, 0.0, 1.0));
                            D frontier_phi_107_106_ladder;
                            if (_3832 > spvNMax(9.9999997473787516355514526367188e-06, _3814))
                            {
                                D _3854 = spvNMax((-0.0) - _3832, _3814) + _3832;
                                frontier_phi_107_106_ladder = (_3854 * _3854) * (0.25 / _3832);
                            }
                            else
                            {
                                frontier_phi_107_106_ladder = _3814;
                            }
                            _3835 = frontier_phi_107_106_ladder;
                        }
                        else
                        {
                            _3835 = _3814;
                        }
                        D _3897;
                        D _3898;
                        D _3837;
                        D _3839;
                        D _3843;
                        D _3844;
                        bool _3847;
                        for (;;)
                        {
                            _3837 = spvNMax(0.0, _3835);
                            _3839 = _647 * _647;
                            _3843 = spvNClamp(((1.0 - _3839) * _1185) * inversesqrt(_3812), 0.0, 1.0);
                            _3844 = dot(vec3(_241, _243, _244), vec3(_2055, _2056, _2057));
                            _3847 = _3843 > 0.0;
                            D _3865;
                            D _3867;
                            if (_3847)
                            {
                                D _3860 = sqrt(spvNMax(0.0, 1.0 - (_3843 * _3843)));
                                D _3863 = ((_3814 * 2.0) * _537) - _3844;
                                if (!(!(_3863 >= _3860)))
                                {
                                    _3897 = _549;
                                    _3898 = 1.0;
                                    break;
                                }
                                D _3885 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, 1.0 - (_3863 * _3863))) * _3843;
                                _3865 = (_3885 * ((((_537 * _537) * 2.0) + (-1.0)) - (_3863 * _3844))) + (_3860 * _3844);
                                _3867 = (_3885 * (_537 - (_3863 * _3814))) + (_3860 * _3814);
                            }
                            else
                            {
                                _3865 = _3844;
                                _3867 = _3814;
                            }
                            D _3872 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3865 * 2.0) + 2.0));
                            _3897 = spvNMin(_3872 * (_3865 + 1.0), 1.0);
                            _3898 = spvNClamp(_3872 * (_3867 + _537), 0.0, 1.0);
                            break;
                        }
                        D _3899 = spvNMax(9.9999997473787516355514526367188e-06, _3897);
                        D _3908 = sqrt(spvNMax(0.0, 1.0 - ((1.0 - (_537 * _537)) * 0.444444477558135986328125)));
                        D _3912 = (_543 * 0.666666686534881591796875) - (_3908 * _423);
                        D _3913 = (_544 * 0.666666686534881591796875) - (_3908 * _424);
                        D _3914 = (_545 * 0.666666686534881591796875) - (_3908 * _425);
                        D _3918 = inversesqrt(dot(vec3(_3912, _3913, _3914), vec3(_3912, _3913, _3914)));
                        D _3925 = dot(vec3((-0.0) - (_3918 * _3912), (-0.0) - (_3918 * _3913), (-0.0) - (_3918 * _3914)), vec3(_2055, _2056, _2057));
                        D _3928 = _3839 * _3839;
                        D _3942 = ((_3898 * _3898) * (_3928 + (-1.0))) + 1.0;
                        D _3948 = (_3837 * 2.0) * _563;
                        D _3953 = 1.0 - _3899;
                        D _3954 = _3953 * _3953;
                        D _3956 = (_3954 * _3954) * _3953;
                        D _3960 = spvNMin(dot(vec3(_521, _522, _523), vec3(16.666667938232421875)), 1.0);
                        D _3973 = spvNMax(0.039999999105930328369140625, _647);
                        D _3986 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_3973 * _3837) + 0.02669160068035125732421875) / (_3837 + 0.4664950072765350341796875)) * exp2(((1.0 / _3973) * _3837) * log2(_3973)), 0.0, 1.0));
                        D _3987 = 1.0 - _3837;
                        D _3988 = _3987 * _3987;
                        D _4000 = ((_3988 * _3988) * _3987) * exp2(log2((exp2((_3973 * 4.7702999114990234375) * log2(_3837)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _3973);
                        D _4003 = (1.0 / _3986) * (1.0 - _3986);
                        D _4007 = (_4003 * _521) + 1.0;
                        D _4008 = (_4003 * _522) + 1.0;
                        D _4009 = (_4003 * _523) + 1.0;
                        D _4010 = _3986 - _4000;
                        D _4024 = spvNClamp(1.0 - dot(vec3(_4007 * ((_4010 * _521) + _4000), _4008 * ((_4010 * _522) + _4000), _4009 * ((_4010 * _523) + _4000)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                        D _4028 = ((((_3928 * 0.3183098733425140380859375) * _3837) * (1.0 / (_3942 * _3942))) * (_3847 ? ((1.0 / ((((_3843 * 0.25) * (_3843 + (_3839 * 3.0))) * (1.0 / _3899)) + _3928)) * _3928) : 1.0)) * (0.5 / ((_3839 * ((_563 + _3837) - _3948)) + _3948));
                        D _4029 = _3837 * 0.3183098733425140380859375;
                        D _4032 = ((_3925 * _3925) + 1.0) * 0.05968309938907623291015625;
                        D _4033 = spvNMin(1.0, _449);
                        D _4035 = (_449 + 1.0) - _4033;
                        D _4036 = _4035 * _4035;
                        D _4039 = 1.0 - ((_4036 * _4036) * _4035);
                        D _4040 = _4039 * _4039;
                        D _4045 = ((_4040 * _4040) * (_4039 * (_449 - _4033))) + _4033;
                        D _4048 = sqrt(spvNMax(0.0, 1.0 - _4045));
                        D _4052 = 1.0 - spvNClamp((_647 * 3.5) + (-0.5), 0.0, 1.0);
                        D _4053 = _4052 * _4052;
                        D _4063 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_678 * _4048) * spvNClamp(1.0 - ((_4053 * _4053) * _4052), 0.0, 1.0))) * _3837, 0.0, 1.0);
                        D _4068 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _4048)) * _3837, 0.0, 1.0);
                        D _4070 = spvNMin(_3810, _4063 * _4063);
                        D _4071 = spvNMin(_3810, _4068 * _4068);
                        D _4072 = spvNMin(_3810, _4045);
                        D _4076 = (_2686 * _1168) * _3229;
                        D _4077 = (_2686 * _1169) * _3231;
                        D _4078 = (_2686 * _1170) * _3233;
                        D _4079 = _3813 * _4076;
                        D _4083 = _3813 * _4077;
                        D _4087 = _3813 * _4078;
                        _3685 = ((((_4076 * _473) * _3813) * _4029) * _4024) * _4071;
                        _3687 = ((((_4077 * _474) * _3813) * _4029) * _4024) * _4071;
                        _3689 = ((((_4078 * _475) * _3813) * _4029) * _4024) * _4071;
                        _3691 = (((_4079 * spvNClamp(((_3960 - _521) * _3956) + _521, 0.0, 1.0)) * _4028) * _4007) * _4070;
                        _3693 = (((_4083 * _4028) * spvNClamp(((_3960 - _522) * _3956) + _522, 0.0, 1.0)) * _4008) * _4070;
                        _3695 = (((_4087 * _4028) * spvNClamp(((_3960 - _523) * _3956) + _523, 0.0, 1.0)) * _4009) * _4070;
                        _3697 = (_4079 * _4032) * _4072;
                        _3699 = (_4083 * _4032) * _4072;
                        _3701 = (_4087 * _4032) * _4072;
                        break;
                    }
                    else
                    {
                        _3685 = 0.0;
                        _3687 = 0.0;
                        _3689 = 0.0;
                        _3691 = 0.0;
                        _3693 = 0.0;
                        _3695 = 0.0;
                        _3697 = 0.0;
                        _3699 = 0.0;
                        _3701 = 0.0;
                        break;
                    }
                }
                frontier_phi_47_pred = _1154;
                frontier_phi_47_pred_1 = _3685 + _1144;
                frontier_phi_47_pred_2 = _3687 + _1145;
                frontier_phi_47_pred_3 = _3689 + _1146;
                frontier_phi_47_pred_4 = _3691 + _1147;
                frontier_phi_47_pred_5 = _3693 + _1148;
                frontier_phi_47_pred_6 = _3695 + _1149;
                frontier_phi_47_pred_7 = _3697 + _1150;
                frontier_phi_47_pred_8 = _3699 + _1151;
                frontier_phi_47_pred_9 = _3701 + _1152;
                frontier_phi_47_pred_10 = _1153;
                frontier_phi_47_pred_11 = _1155;
                frontier_phi_47_pred_12 = _1156;
                frontier_phi_47_pred_13 = _1157;
                frontier_phi_47_pred_14 = _1158;
            }
            else
            {
                D _1327 = _1163 - _230;
                D _1328 = _1164 - _231;
                D _1329 = _1165 - _232;
                D _1330 = dot(vec3(_1327, _1328, _1329), vec3(_1327, _1328, _1329));
                D _1334 = (_1166 * _1166) * _1330;
                D _1335 = _1334 * _1334;
                D _1336 = _1335 * _1335;
                D _1339 = spvNClamp(1.0 - (_1336 * _1336), 0.0, 1.0);
                D _1340 = _1339 * _1339;
                D _1341 = _1340 * _1340;
                D _1342 = _1341 * _1341;
                D _1646;
                D _1648;
                D _1650;
                D _1652;
                D _1654;
                D _1656;
                if (_1342 > 0.0)
                {
                    D _1638 = dot(vec3(_238, _239, _240), vec3(_423, _424, _425)) * 2.0;
                    D _1642 = _238 - (_1638 * _423);
                    D _1643 = _239 - (_1638 * _424);
                    D _1644 = _240 - (_1638 * _425);
                    D _3296;
                    D _3297;
                    D _3298;
                    D _3299;
                    D _3300;
                    D _3301;
                    D _3302;
                    D _3303;
                    D _3304;
                    D _3305;
                    D _3306;
                    if (_1186 == 0.0)
                    {
                        D _2691;
                        D _2692;
                        D _2693;
                        if (_1330 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2687 = inversesqrt(_1330);
                            _2691 = _2687 * _1327;
                            _2692 = _2687 * _1328;
                            _2693 = _2687 * _1329;
                        }
                        else
                        {
                            _2691 = 0.0;
                            _2692 = 0.0;
                            _2693 = 0.0;
                        }
                        D _2696 = 1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1330));
                        _3296 = _2696;
                        _3297 = (_1185 * _1185) * _2696;
                        _3298 = _2691;
                        _3299 = _2692;
                        _3300 = _2693;
                        _3301 = _2691;
                        _3302 = _2692;
                        _3303 = _2693;
                        _3304 = _2691;
                        _3305 = _2692;
                        _3306 = _2693;
                    }
                    else
                    {
                        D _2069 = _1186 * 0.5;
                        D _2070 = _2069 * _1172;
                        D _2071 = _2069 * _1173;
                        D _2072 = _2069 * _1174;
                        D _2073 = _1327 - _2070;
                        D _2074 = _1328 - _2071;
                        D _2075 = _1329 - _2072;
                        D _2076 = _2070 + _1327;
                        D _2077 = _2071 + _1328;
                        D _2078 = _2072 + _1329;
                        D _2086 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2073, _2074, _2075), vec3(_2073, _2074, _2075))));
                        D _2088 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2076, _2077, _2078), vec3(_2076, _2077, _2078))));
                        D _2089 = _2088 * _2086;
                        D _2105 = (1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(_2089, ((dot(vec3(_2073, _2074, _2075), vec3(_2076, _2077, _2078)) * 0.5) * _2089) + 0.5))) * _2089;
                        D _2107 = (_1172 * 2.0) * _2069;
                        D _2109 = (_1173 * 2.0) * _2069;
                        D _2111 = (_1174 * 2.0) * _2069;
                        D _2112 = dot(vec3(_2107, _2109, _2111), vec3(_2107, _2109, _2111));
                        D _2729;
                        D _2730;
                        D _2731;
                        if (_2112 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2699 = dot(vec3(_1642, _1643, _1644), vec3(_2107, _2109, _2111));
                            D _2715 = spvNClamp((1.0 / (_2112 - (_2699 * _2699))) * dot(vec3(_2073, _2074, _2075), vec3((_2699 * _1642) - _2107, (_2699 * _1643) - _2109, (_2699 * _1644) - _2111)), 0.0, 1.0);
                            D _2719 = (_2715 * _2107) + _2073;
                            D _2720 = (_2715 * _2109) + _2074;
                            D _2721 = (_2715 * _2111) + _2075;
                            D _2725 = inversesqrt(dot(vec3(_2719, _2720, _2721), vec3(_2719, _2720, _2721)));
                            _2729 = _2719 * _2725;
                            _2730 = _2720 * _2725;
                            _2731 = _2721 * _2725;
                        }
                        else
                        {
                            _2729 = _2073;
                            _2730 = _2074;
                            _2731 = _2075;
                        }
                        _3296 = _2105;
                        _3297 = (_1185 * _1185) * _2105;
                        _3298 = _2086 * _2073;
                        _3299 = _2086 * _2074;
                        _3300 = _2086 * _2075;
                        _3301 = _2088 * _2076;
                        _3302 = _2088 * _2077;
                        _3303 = _2088 * _2078;
                        _3304 = _2729;
                        _3305 = _2730;
                        _3306 = _2731;
                    }
                    D _3316 = _3297 + 1.0;
                    D _3321 = _3304 - _238;
                    D _3322 = _3305 - _239;
                    D _3323 = _3306 - _240;
                    D _3327 = inversesqrt(dot(vec3(_3321, _3322, _3323), vec3(_3321, _3322, _3323)));
                    D _3328 = _3327 * _3321;
                    D _3329 = _3327 * _3322;
                    D _3330 = _3327 * _3323;
                    D _3337 = spvNClamp(dot(vec3(_423, _424, _425), vec3(_3328, _3329, _3330)), 0.0, 1.0);
                    D _3338 = _647 * _647;
                    D _3344 = spvNClamp(((1.0 - _3338) * _1185) * sqrt(_3296), 0.0, 1.0);
                    D _3358 = exp2(log2(spvNClamp((((_3344 * 0.25) * (_3344 + (_3338 * 3.0))) * (1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_241, _243, _244), vec3(_3328, _3329, _3330))))) + (_3338 * _3338), 0.0, 1.0)) * 0.25);
                    D _3362 = spvNClamp(dot(vec3(_3298, _3299, _3300), vec3(_3301, _3302, _3303)), 0.0, 1.0);
                    D _3364 = _3358 * _3358;
                    D _3365 = _3364 * _3364;
                    D _3717;
                    if (_3362 < 1.0)
                    {
                        D _3708 = sqrt(spvNClamp((1.0 / (_3362 + 1.0)) * (1.0 - _3362), 0.0, 1.0));
                        _3717 = (1.0 / spvNClamp(((_3708 * 0.25) * (_3708 + (_3364 * 3.0))) + _3365, 0.0, 1.0)) * _3365;
                    }
                    else
                    {
                        _3717 = 1.0;
                    }
                    D _3721 = ((_3337 * _3337) * (_3365 + (-1.0))) + 1.0;
                    D _3724 = spvNMax(0.0, (((dot(vec3(_423, _424, _425), vec3(_3301, _3302, _3303)) + dot(vec3(_423, _424, _425), vec3(_3298, _3299, _3300))) * 0.5) + _3297) * (1.0 / (_3316 * _3316))) * 0.3183098733425140380859375;
                    D _3727 = ((_3724 * _3365) * _3717) * (1.0 / (_3721 * _3721));
                    D _3729 = (_1342 * _1168) * _3296;
                    D _3731 = (_1342 * _1169) * _3296;
                    D _3733 = (_1342 * _1170) * _3296;
                    _1646 = _3727 * _3729;
                    _1648 = _3727 * _3731;
                    _1650 = _3727 * _3733;
                    _1652 = _3724 * _3729;
                    _1654 = _3724 * _3731;
                    _1656 = _3724 * _3733;
                }
                else
                {
                    _1646 = 0.0;
                    _1648 = 0.0;
                    _1650 = 0.0;
                    _1652 = 0.0;
                    _1654 = 0.0;
                    _1656 = 0.0;
                }
                frontier_phi_47_pred = _1648 + _1154;
                frontier_phi_47_pred_1 = _1144;
                frontier_phi_47_pred_2 = _1145;
                frontier_phi_47_pred_3 = _1146;
                frontier_phi_47_pred_4 = _1147;
                frontier_phi_47_pred_5 = _1148;
                frontier_phi_47_pred_6 = _1149;
                frontier_phi_47_pred_7 = _1150;
                frontier_phi_47_pred_8 = _1151;
                frontier_phi_47_pred_9 = _1152;
                frontier_phi_47_pred_10 = _1646 + _1153;
                frontier_phi_47_pred_11 = _1650 + _1155;
                frontier_phi_47_pred_12 = _1652 + _1156;
                frontier_phi_47_pred_13 = _1654 + _1157;
                frontier_phi_47_pred_14 = _1656 + _1158;
            }
            _833 = frontier_phi_47_pred;
            _813 = frontier_phi_47_pred_1;
            _815 = frontier_phi_47_pred_2;
            _817 = frontier_phi_47_pred_3;
            _819 = frontier_phi_47_pred_4;
            _821 = frontier_phi_47_pred_5;
            _823 = frontier_phi_47_pred_6;
            _825 = frontier_phi_47_pred_7;
            _827 = frontier_phi_47_pred_8;
            _829 = frontier_phi_47_pred_9;
            _831 = frontier_phi_47_pred_10;
            _835 = frontier_phi_47_pred_11;
            _837 = frontier_phi_47_pred_12;
            _839 = frontier_phi_47_pred_13;
            _841 = frontier_phi_47_pred_14;
            uint _1160 = _1159 + 1u;
            if (_1160 == _805)
            {
                break;
            }
            else
            {
                _1144 = _813;
                _1145 = _815;
                _1146 = _817;
                _1147 = _819;
                _1148 = _821;
                _1149 = _823;
                _1150 = _825;
                _1151 = _827;
                _1152 = _829;
                _1153 = _831;
                _1154 = _833;
                _1155 = _835;
                _1156 = _837;
                _1157 = _839;
                _1158 = _841;
                _1159 = _1160;
                continue;
            }
        }
        _812 = _813;
        _814 = _815;
        _816 = _817;
        _818 = _819;
        _820 = _821;
        _822 = _823;
        _824 = _825;
        _826 = _827;
        _828 = _829;
        _830 = _831;
        _832 = _833;
        _834 = _835;
        _836 = _837;
        _838 = _839;
        _840 = _841;
    }
    vec4 _882 = textureLod(sampler3D(TranslucentBasePass_TranslucencyLightingVolumeEnvironmentA, View_SharedBilinearClampedSampler), vec3((_230 - View._m0[180u].x) * View._m0[182u].x, (_231 - View._m0[180u].y) * View._m0[182u].y, (_232 - View._m0[180u].z) * View._m0[182u].z), 0.0);
    D _906;
    D _907;
    D _908;
    if (_369 < 1.0)
    {
        _906 = _346.x / ((_391 / _368) + 1.0);
        _907 = _346.y / ((_392 / _368) + 1.0);
        _908 = _346.z / ((_393 / _368) + 1.0);
    }
    else
    {
        _906 = 0.0;
        _907 = 0.0;
        _908 = 0.0;
    }
    D _925 = spvNClamp(_629, 0.0, 1.0);
    D _938 = _471 * _471;
    D _939 = _938 * _471;
    D _946 = ((_423 - _560) * _939) + _560;
    D _947 = ((_424 - _561) * _939) + _561;
    D _948 = ((_425 - _562) * _939) + _562;
    D _952 = inversesqrt(dot(vec3(_946, _947, _948), vec3(_946, _947, _948)));
    D _961 = 10.0 / spvNMax(9.9999997473787516355514526367188e-06, _938);
    D _990 = fma(_229, View._m0[2u].x, fma(_228, View._m0[1u].x, View._m0[0u].x * _227)) + View._m0[3u].x;
    D _994 = fma(_229, View._m0[2u].y, fma(_228, View._m0[1u].y, View._m0[0u].y * _227)) + View._m0[3u].y;
    D _998 = fma(_229, View._m0[2u].z, fma(_228, View._m0[1u].z, View._m0[0u].z * _227)) + View._m0[3u].z;
    D _1002 = fma(_229, View._m0[2u].w, fma(_228, View._m0[1u].w, View._m0[0u].w * _227)) + View._m0[3u].w;
    D _1009 = ((_946 * _103) * _952) + _227;
    D _1010 = ((_947 * _103) * _952) + _228;
    D _1011 = ((_948 * _103) * _952) + _229;
    D _1044 = 1.0 / _1002;
    D _1045 = _1044 * _990;
    D _1046 = _1044 * _994;
    D _1050 = (_1044 * _998) + (0.0500000007450580596923828125 / _1002);
    D _1051 = 1.0 / (fma(_1011, View._m0[2u].w, fma(_1010, View._m0[1u].w, View._m0[0u].w * _1009)) + View._m0[3u].w);
    D _1062 = 1.0 / ((View._m0[36u].w * _961) + _1002);
    D _1065 = (_1051 * (fma(_1011, View._m0[2u].x, fma(_1010, View._m0[1u].x, View._m0[0u].x * _1009)) + View._m0[3u].x)) - _1045;
    D _1066 = (_1051 * (fma(_1011, View._m0[2u].y, fma(_1010, View._m0[1u].y, View._m0[0u].y * _1009)) + View._m0[3u].y)) - _1046;
    D _1068 = (_1062 * ((View._m0[36u].x * _961) + _990)) - _1045;
    D _1069 = (_1062 * ((View._m0[36u].y * _961) + _994)) - _1046;
    D _1074 = sqrt((_1065 * _1065) + (_1066 * _1066)) * 0.5;
    D _1093 = spvNMin(1.0 - (spvNMax(0.0, abs((_1074 * _1045) + _1065) - _1074) / abs(_1065)), 1.0 - (spvNMax(0.0, abs((_1074 * _1046) + _1066) - _1074) / abs(_1066))) / _1074;
    D _1094 = _1093 * _1065;
    D _1095 = _1093 * _1066;
    D _1096 = _1093 * ((_1051 * (fma(_1011, View._m0[2u].z, fma(_1010, View._m0[1u].z, View._m0[0u].z * _1009)) + View._m0[3u].z)) - _1050);
    uvec2 _1102 = uvec2(textureSize(TranslucentBasePass_HZBTexture, int(0u)));
    D _1104 = D(int(_1102.x));
    D _1106 = D(int(_1102.y));
    uint _1127 = max(1u, min(uint(ceil((spvNClamp((1.0 / spvNMax(9.9999997473787516355514526367188e-05, sqrt((_1094 * _1094) + (_1095 * _1095)))) * sqrt((_1068 * _1068) + (_1069 * _1069)), 0.0, 1.0) * 8.0) + _265)), 8u));
    D _1132 = ((_1045 * 0.5) + 0.5) * TranslucentBasePass_2._m0[198u].x;
    D _1133 = (0.5 - (_1046 * 0.5)) * TranslucentBasePass_2._m0[198u].y;
    D _1136 = (TranslucentBasePass_2._m0[198u].x * 0.0625) * _1094;
    D _1139 = (TranslucentBasePass_2._m0[198u].y * (-0.0625)) * _1095;
    D _1140 = _1096 * 0.125;
    D _1142 = spvNMax(abs(_1096), _1050 - ((1.0 / (fma(_103, View._m0[38u].w, 0.0) + _1002)) * (fma(_103, View._m0[38u].z, 0.0) + _998))) * 0.125;
    D _1310;
    D _1312;
    D _1314;
    D _1316;
    if (_1127 == 0u)
    {
        _1310 = 0.0;
        _1312 = 0.0;
        _1314 = 0.0;
        _1316 = 0.0;
    }
    else
    {
        D frontier_phi_60;
        D frontier_phi_60_1;
        D frontier_phi_60_2;
        D frontier_phi_60_3;
        D _1559 = 0.0;
        uint _1561 = 0u;
        D _1560;
        D _1563;
        bool _1586;
        for (;;)
        {
            _1563 = D(_1561);
            D _1564 = _1563 + _265;
            vec4 _1578 = texelFetch(TranslucentBasePass_HZBTexture, ivec2_(uvec2(uint(int(floor(((_1564 * _1136) + _1132) * _1104))), uint(int(floor(((_1564 * _1139) + _1133) * _1106))))), int(0u));
            D _1580 = _1578.x;
            _1560 = ((_1564 * _1140) + _1050) - _1580;
            _1586 = (abs(((-0.0) - _1142) - _1560) < _1142) && (_1580 != 0.0);
            if (_1586)
            {
                D _1995 = (_1561 == 0u) ? (_1560 - _1140) : _1559;
                D _2002 = abs(((_265 + (-1.0)) + _1563) + spvNClamp(_1995 / (_1995 - _1560), 0.0, 1.0));
                D _2007 = spvNMin(_2002 * 0.125, 1.0);
                frontier_phi_60 = 1.0 - (_2007 * _2007);
                frontier_phi_60_1 = (_2002 * _1140) + _1050;
                frontier_phi_60_2 = (_2002 * _1139) + _1133;
                frontier_phi_60_3 = (_2002 * _1136) + _1132;
                break;
            }
            else
            {
                uint _1562 = _1561 + 1u;
                if (_1562 < _1127)
                {
                    _1559 = _1560;
                    _1561 = _1562;
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
        _1310 = frontier_phi_60_3;
        _1312 = frontier_phi_60_2;
        _1314 = frontier_phi_60_1;
        _1316 = frontier_phi_60;
    }
    D _1324 = (spvNClamp(_1310 * TranslucentBasePass_2._m0[198u].z, 0.0, 1.0) * 2.0) + (-1.0);
    D _1325 = 1.0 - (spvNClamp(_1312 * TranslucentBasePass_2._m0[198u].w, 0.0, 1.0) * 2.0);
    D _1464;
    D _1466;
    D _1468;
    D _1470;
    if (_1316 > 0.0)
    {
        D _1465;
        D _1467;
        D _1469;
        D _2211;
        D _1457;
        bool _1463;
        for (;;)
        {
            D _1416 = ((View._m0[73u].x * _1314) + View._m0[73u].y) + (1.0 / ((View._m0[73u].z * _1314) - View._m0[73u].w));
            D _1440 = _1416 * _1324;
            D _1441 = _1416 * _1325;
            D _1452 = (_227 - View._m0[63u].x) - fma(_1416, View._m0[62u].x, fma(_1441, View._m0[61u].x, _1440 * View._m0[60u].x));
            D _1454 = (_228 - View._m0[63u].y) - fma(_1416, View._m0[62u].y, fma(_1441, View._m0[61u].y, _1440 * View._m0[60u].y));
            D _1456 = (_229 - View._m0[63u].z) - fma(_1416, View._m0[62u].z, fma(_1441, View._m0[61u].z, _1440 * View._m0[60u].z));
            _1457 = dot(vec3(_1452, _1454, _1456), vec3(_1452, _1454, _1456));
            _1463 = View._m0[175u].w != 0.0;
            if (_1463)
            {
                if (floatBitsToUint(View._m0[175u]).y == 0u)
                {
                    _1465 = 0.0;
                    _1467 = 0.0;
                    _1469 = 0.0;
                    _2211 = 0.0;
                    break;
                }
            }
            D _1853 = fma(_1314, View._m0[140u].w, fma(_1325, View._m0[139u].w, View._m0[138u].w * _1324)) + View._m0[141u].w;
            D _1854 = (fma(_1314, View._m0[140u].x, fma(_1325, View._m0[139u].x, View._m0[138u].x * _1324)) + View._m0[141u].x) / _1853;
            D _1855 = (fma(_1314, View._m0[140u].y, fma(_1325, View._m0[139u].y, View._m0[138u].y * _1324)) + View._m0[141u].y) / _1853;
            D _1872 = spvNClamp((abs((spvNMin(spvNMax(_1854, -1.0), 1.0) - _1324) * 0.5) * 5.0) + (-4.0), 0.0, 1.0);
            D _1873 = spvNClamp((abs((spvNMin(spvNMax(_1855, -1.0), 1.0) - _1325) * 0.5) * 5.0) + (-4.0), 0.0, 1.0);
            uvec2 _1926 = uvec2(textureSize(TranslucentBasePass_PrevSceneColor, int(0u)));
            vec4 _1947 = texelFetch(TranslucentBasePass_PrevSceneColor, ivec2_(uvec2(uint(min(int(uint(max(int(uint(int(D(int(_1926.x)) * ((TranslucentBasePass_2._m0[199u].x * spvNMin(spvNMax(_1854 - ((D(int(uint(_1854 > 0.0) - uint(_1854 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1854) + (-1.0))), -1.0), 1.0)) + TranslucentBasePass_2._m0[199u].z)))), int(uint(int(TranslucentBasePass_2._m0[200u].x)))))), int(uint(int(TranslucentBasePass_2._m0[200u].x + TranslucentBasePass_2._m0[200u].z)) + 4294967295u))), uint(min(int(uint(max(int(uint(int(D(int(_1926.y)) * ((TranslucentBasePass_2._m0[199u].y * spvNMin(spvNMax(_1855 - ((D(int(uint(_1855 > 0.0) - uint(_1855 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1855) + (-1.0))), -1.0), 1.0)) + TranslucentBasePass_2._m0[199u].w)))), int(uint(int(TranslucentBasePass_2._m0[200u].y)))))), int(uint(int(TranslucentBasePass_2._m0[200u].y + TranslucentBasePass_2._m0[200u].w)) + 4294967295u))))), int(0u));
            _1465 = View._m0[165u].x * spvNMin(_1947.x, 65504.0);
            _1467 = View._m0[165u].x * spvNMin(_1947.y, 65504.0);
            _1469 = View._m0[165u].x * spvNMin(_1947.z, 65504.0);
            _2211 = spvNMax(0.0, 1.0 - dot(vec2(_1872, _1873), vec2(_1872, _1873)));
            break;
        }
        _1464 = _1465;
        _1466 = _1467;
        _1468 = _1469;
        _1470 = (_2211 * _1316) * spvNClamp(1.0 / spvNMax(9.9999997473787516355514526367188e-06, (_938 * _938) * _1457), 0.0, 1.0);
    }
    else
    {
        _1464 = 0.0;
        _1466 = 0.0;
        _1468 = 0.0;
        _1470 = 0.0;
    }
    D _1504 = fma(_232, View._m0[14u].w, fma(_231, View._m0[13u].w, _230 * View._m0[12u].w)) + View._m0[15u].w;
    D _1509 = (((fma(_232, View._m0[14u].x, fma(_231, View._m0[13u].x, _230 * View._m0[12u].x)) + View._m0[15u].x) / _1504) * 0.5) + 0.5;
    D _1510 = 0.5 - (((fma(_232, View._m0[14u].y, fma(_231, View._m0[13u].y, _230 * View._m0[12u].y)) + View._m0[15u].y) / _1504) * 0.5);
    D _1539 = sqrt(((_228 * _228) + (_227 * _227)) + (_229 * _229));
    D _1557 = spvNMax(0.0, ((1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_227, _228, _229), vec3(View._m0[68u].xyz())))) * _1539) * View._m0[280u].w);
    D _1963;
    D _1965;
    D _1967;
    D _1969;
    D _1971;
    D _1973;
    if (_1539 < _1557)
    {
        _1963 = 0.0;
        _1965 = 0.0;
        _1967 = 0.0;
        _1969 = 1.0;
        _1971 = 1.0;
        _1973 = 1.0;
    }
    else
    {
        D _1981 = (1.0 / _1539) * _1557;
        uvec4 _1988 = floatBitsToUint(View._m0[220u]);
        uint _1989 = _1988.y;
        uint _1991 = (_1989 != 1u) ? 4294967295u : 0u;
        uint _2327;
        if (_1989 > 1u)
        {
            D _132[4];
            _132[0u] = 0.0;
            _132[1u] = 0.0;
            _132[2u] = 0.0;
            _132[3u] = 0.0;
            uint _3173 = 0u;
            bool _3179;
            for (;;)
            {
                _3179 = _3173 < floatBitsToUint(View._m0[220u]).y;
                if (_3179)
                {
                    uint _3600 = _3173 + 237u;
                    D _3612 = View._m0[_3600].x - View._m0[75u].x;
                    D _3613 = View._m0[_3600].y - View._m0[75u].y;
                    D _3614 = View._m0[_3600].z - View._m0[75u].z;
                    D _3615 = dot(vec3(_3612, _3613, _3614), vec3(_238, _239, _240));
                    D _3622 = dot(vec3(_3612, _3613, _3614), vec3(_3612, _3613, _3614)) - (View._m0[_3600].w * View._m0[_3600].w);
                    D _3624 = (_3615 * _3615) - _3622;
                    D _3742;
                    if ((_3622 < 0.0) && (!(_3624 < 0.0)))
                    {
                        D _3736 = sqrt(_3624);
                        _3742 = spvNMin(abs(_3736 + _3615), abs(_3615 - _3736));
                    }
                    else
                    {
                        _3742 = 0.0;
                    }
                    _132[_3173] = _3742;
                }
                uint _3174 = _3173 + 1u;
                if (_3174 == 4u)
                {
                    break;
                }
                else
                {
                    _3173 = _3174;
                    continue;
                }
            }
            D _3752 = (_265 * 0.99989998340606689453125) * dot(vec4(_132[0u], _132[1u], _132[2u], _132[3u]), vec4(1.0));
            uint frontier_phi_59_97_ladder;
            if (_132[0u] > _3752)
            {
                frontier_phi_59_97_ladder = 0u;
            }
            else
            {
                D _3820 = _132[1u] + _132[0u];
                uint frontier_phi_59_97_ladder_103_ladder;
                if (_3820 > _3752)
                {
                    frontier_phi_59_97_ladder_103_ladder = 1u;
                }
                else
                {
                    D _3850 = _3820 + _132[2u];
                    uint frontier_phi_59_97_ladder_103_ladder_109_ladder;
                    if (_3850 > _3752)
                    {
                        frontier_phi_59_97_ladder_103_ladder_109_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder;
                        if ((_3850 + _132[3u]) > _3752)
                        {
                            frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder = _1991;
                        }
                        frontier_phi_59_97_ladder_103_ladder_109_ladder = frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder;
                    }
                    frontier_phi_59_97_ladder_103_ladder = frontier_phi_59_97_ladder_103_ladder_109_ladder;
                }
                frontier_phi_59_97_ladder = frontier_phi_59_97_ladder_103_ladder;
            }
            _2327 = frontier_phi_59_97_ladder;
        }
        else
        {
            _2327 = _1991;
        }
        D frontier_phi_38_59_ladder;
        D frontier_phi_38_59_ladder_1;
        D frontier_phi_38_59_ladder_2;
        D frontier_phi_38_59_ladder_3;
        D frontier_phi_38_59_ladder_4;
        D frontier_phi_38_59_ladder_5;
        if (_2327 == 4294967295u)
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
            uint _3180 = _2327 + 221u;
            D _3188 = spvNMin(View._m0[_3180].w, 0.9900000095367431640625);
            uint _3189 = _2327 + 225u;
            uint _3196 = _2327 + 229u;
            uint _3203 = _2327 + 233u;
            uint _3208 = _2327 + 241u;
            D _3655;
            D _3656;
            D _3657;
            if (TranslucentBasePass_2._m0[146u].x > 0.0)
            {
                vec4 _3647 = textureLod(sampler2D(TranslucentBasePass_Shared_Fog_FarIntegratedScatteringTexture, View_SharedBilinearClampedSampler), vec2(spvNMin(spvNMax(View._m0[278u].x * _1509, View._m0[279u].x), View._m0[280u].x), spvNMin(spvNMax(View._m0[278u].y * _1510, View._m0[279u].y), View._m0[280u].y)), 0.0);
                _3655 = View._m0[164u].z * _3647.x;
                _3656 = View._m0[164u].z * _3647.y;
                _3657 = View._m0[164u].z * _3647.z;
            }
            else
            {
                _3655 = 0.0;
                _3656 = 0.0;
                _3657 = 0.0;
            }
            D _3661 = dot(vec3((-0.0) - View._m0[218u].x, (-0.0) - View._m0[218u].y, (-0.0) - View._m0[218u].z), vec3(_241, _243, _244));
            D _3674 = (((_3661 * _3661) + 1.0) * 0.0397887341678142547607421875) * exp2(log2(spvNMax(0.0, _3661 + 1.25)) * (-1.5));
            D _3754;
            if (View._m0[_3189].x == 0.0)
            {
                _3754 = 0.0;
            }
            else
            {
                D _3802 = (((_1981 * _229) - View._m0[_3189].z) + View._m0[75u].z) * View._m0[_3189].y;
                D _3803 = ((1.0 - _1981) * _229) * View._m0[_3189].y;
                D _3808 = exp2((-0.0) - _3802);
                D frontier_phi_98_99_ladder;
                if (abs(_3803) > 0.00999999977648258209228515625)
                {
                    frontier_phi_98_99_ladder = ((_3808 - exp2(((-0.0) - _3803) - _3802)) * View._m0[_3189].x) * (1.0 / _3803);
                }
                else
                {
                    frontier_phi_98_99_ladder = (View._m0[_3189].x * 0.693147182464599609375) * _3808;
                }
                _3754 = frontier_phi_98_99_ladder;
            }
            D _3758 = _3754 * (1.0 - _3188);
            D _3762 = (1.0 - View._m0[_3196].x) * View._m0[_3203].x;
            D _3763 = (1.0 - View._m0[_3196].y) * View._m0[_3203].x;
            D _3764 = (1.0 - View._m0[_3196].z) * View._m0[_3203].x;
            D _3765 = (-0.0) - (_1539 - _1557);
            D _3793 = 1.0 - spvNClamp(exp2(_3758 * _3765), 0.0, 1.0);
            frontier_phi_38_59_ladder = spvNClamp(exp2((_3758 + _3764) * _3765), 0.0, 1.0);
            frontier_phi_38_59_ladder_1 = spvNClamp(exp2((_3758 + _3763) * _3765), 0.0, 1.0);
            frontier_phi_38_59_ladder_2 = spvNClamp(exp2((_3758 + _3762) * _3765), 0.0, 1.0);
            frontier_phi_38_59_ladder_3 = (((_3188 * View._m0[_3180].z) * (((View._m0[219u].z * View._m0[_3208].x) * _3674) + _3657)) * spvNClamp(exp2(_3764 * _3765), 0.0, 1.0)) * _3793;
            frontier_phi_38_59_ladder_4 = (((_3188 * View._m0[_3180].y) * (((View._m0[219u].y * View._m0[_3208].x) * _3674) + _3656)) * spvNClamp(exp2(_3763 * _3765), 0.0, 1.0)) * _3793;
            frontier_phi_38_59_ladder_5 = (((_3188 * View._m0[_3180].x) * (((View._m0[219u].x * View._m0[_3208].x) * _3674) + _3655)) * spvNClamp(exp2(_3762 * _3765), 0.0, 1.0)) * _3793;
        }
        _1963 = frontier_phi_38_59_ladder_5;
        _1965 = frontier_phi_38_59_ladder_4;
        _1967 = frontier_phi_38_59_ladder_3;
        _1969 = frontier_phi_38_59_ladder_2;
        _1971 = frontier_phi_38_59_ladder_1;
        _1973 = frontier_phi_38_59_ladder;
    }
    D _2259;
    D _2260;
    D _2261;
    D _2262;
    D _2263;
    D _2264;
    if (TranslucentBasePass_2._m0[148u].x > 0.0)
    {
        D _2239 = spvNMin(spvNMax(View._m0[278u].x * _1509, View._m0[279u].x), View._m0[280u].x);
        D _2240 = spvNMin(spvNMax(View._m0[278u].y * _1510, View._m0[279u].y), View._m0[280u].y);
        D _2241 = spvNMin(spvNMax((View._m0[275u].z * spvNMax(0.0, spvNMin(View._m0[276u].z * log2((View._m0[276u].x * _1504) + View._m0[276u].y), View._m0[274u].z + (-1.0)) + 0.5)) * View._m0[278u].z, View._m0[279u].z), View._m0[280u].z);
        vec4 _2244 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeATexture, View_SharedBilinearClampedSampler), vec3(_2239, _2240, _2241), 0.0);
        vec4 _2251 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeBTexture, View_SharedBilinearClampedSampler), vec3(_2239, _2240, _2241), 0.0);
        _2259 = View._m0[164u].z * _2244.x;
        _2260 = View._m0[164u].z * _2244.y;
        _2261 = View._m0[164u].z * _2244.z;
        _2262 = _2251.x;
        _2263 = _2251.y;
        _2264 = _2251.z;
    }
    else
    {
        _2259 = 0.0;
        _2260 = 0.0;
        _2261 = 0.0;
        _2262 = 1.0;
        _2263 = 1.0;
        _2264 = 1.0;
    }
    D _2271 = (1.0 - _634) + (_634 * _447);
    D _2272 = (1.0 - _637) + (_637 * _447);
    D _2273 = (1.0 - _640) + (_640 * _447);
    SV_Target.x = View._m0[164u].y * ((((_2262 * _1963) + _2259) * _2271) + ((_1969 * (((((((((_473 * _449) * _705) * spvNMax(1.0, ((_528 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_528 * 4.79510021209716796875)) + (((_528 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _449)) * _449))) * _836) + _812) * _450) + _818) + ((((_906 * _602) * spvNClamp(1.0 - (_618 * _608), 0.0, 1.0)) * ((View._m0[164u].z * _882.x) + _824)) * _925)) + ((_719 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1464)) + 29.8973522186279296875) * _1470) + (-29.8973522186279296875)) + _830)) * spvNClamp(_697, 0.0, 1.0)))) * _2262));
    SV_Target.y = ((((_2263 * _1965) + _2260) * _2272) + ((_1971 * (((((((((_474 * _449) * _705) * spvNMax(1.0, ((_529 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_529 * 4.79510021209716796875)) + (((_529 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _449)) * _449))) * _838) + _814) * _450) + _820) + ((((_907 * _602) * spvNClamp(1.0 - (_619 * _608), 0.0, 1.0)) * ((View._m0[164u].z * _882.y) + _826)) * _925)) + ((_719 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1466)) + 29.8973522186279296875) * _1470) + (-29.8973522186279296875)) + _832)) * spvNClamp(_698, 0.0, 1.0)))) * _2263)) * View._m0[164u].y;
    SV_Target.z = ((((_2264 * _1967) + _2261) * _2273) + ((_1973 * (((((((((_475 * _449) * _705) * spvNMax(1.0, ((_530 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_530 * 4.79510021209716796875)) + (((_530 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _449)) * _449))) * _840) + _816) * _450) + _822) + ((((_908 * _602) * ((View._m0[164u].z * _882.z) + _828)) * spvNClamp(1.0 - (_620 * _608), 0.0, 1.0)) * _925)) + ((_719 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1468)) + 29.8973522186279296875) * _1470) + (-29.8973522186279296875)) + _834)) * spvNClamp(_699, 0.0, 1.0)))) * _2264)) * View._m0[164u].y;
    SV_Target.w = dot(vec3(_2271, _2272, _2273), vec3(0.2125999927520751953125, 0.715200006961822509765625, 0.072200000286102294921875));
    SV_Target_1.x = _2271;
    SV_Target_1.y = _2272;
    SV_Target_1.z = _2273;
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
} // namespace S_rystal_Thick_Wide_Character