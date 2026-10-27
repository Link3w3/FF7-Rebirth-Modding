namespace S_lass_Thin_Coverage_Wide_Character {
using namespace cpuglsl;
static D _4330;
static D _4326;
static D _4327;
static D _4328;
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
static Tex2D Material_Texture2D_5{texid("junk:T_Coverage")};
static Tex2D Material_Texture2D_8{texid("junk:T_Opacity")};
static Tex2D Material_Texture2D_15{texid("junk:T_WideOcclusion")};
static Tex2D Material_Texture2D_19{texid("junk:T_Muddiness")};
static Tex2D Material_Texture2D_20{texid("junk:T_Transparency")};
static Tex2D Material_Texture2D_21{texid("junk:T_TransparencyCoefficient")};
static Tex2D Material_Texture2D_22{texid("junk:T_Transmittance")};
static Tex2D Material_Texture2D_23{texid("junk:T_TransmittanceCoefficient")};
static Tex2D Material_Texture2D_25{texid("junk:T_Thinness")};
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









void discard_cond(bool _4316)
{
    if (_4316)
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
    D _104 = 1.0 / gl_FragCoord.w;
    D _228 = fma(gl_FragCoord.z, View._m0[54u].w, fma(gl_FragCoord.y, View._m0[53u].w, View._m0[52u].w * gl_FragCoord.x)) + View._m0[55u].w;
    D _229 = (fma(gl_FragCoord.z, View._m0[54u].x, fma(gl_FragCoord.y, View._m0[53u].x, View._m0[52u].x * gl_FragCoord.x)) + View._m0[55u].x) / _228;
    D _230 = (fma(gl_FragCoord.z, View._m0[54u].y, fma(gl_FragCoord.y, View._m0[53u].y, View._m0[52u].y * gl_FragCoord.x)) + View._m0[55u].y) / _228;
    D _231 = (fma(gl_FragCoord.z, View._m0[54u].z, fma(gl_FragCoord.y, View._m0[53u].z, View._m0[52u].z * gl_FragCoord.x)) + View._m0[55u].z) / _228;
    D _232 = _229 - View._m0[78u].x;
    D _233 = _230 - View._m0[78u].y;
    D _234 = _231 - View._m0[78u].z;
    D _239 = inversesqrt(dot(vec3(_229, _230, _231), vec3(_229, _230, _231)));
    D _240 = _239 * _229;
    D _241 = _239 * _230;
    D _242 = _239 * _231;
    D _243 = (-0.0) - _240;
    D _245 = (-0.0) - _241;
    D _246 = (-0.0) - _242;
    vec4 _264 = texelFetch(View_SpatiotemporalBlueNoiseVolumeTexture, ivec3_(uvec3(uint(int(gl_FragCoord.x)) & 127u, uint(int(gl_FragCoord.y)) & 127u, ((floatBitsToUint(View._m0[175u]).x & 7u) + uint(roundEven(CONSTANT_CONTEXT))) & 63u)), int(0u));
    D _267 = _264.x;
    D _268 = _264.y;
    vec4 _274 = texture(sampler2D(Material_Texture2D_0, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _282 = texture(sampler2D(Material_Texture2D_1, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _287 = texture(sampler2D(Material_Texture2D_2, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _294 = (_287.x * 2.0) + (-1.0);
    D _296 = (_287.y * 2.0) + (-1.0);
    D _303 = sqrt(spvNMax(0.0, 1.0 - dot(vec2(_294, _296), vec2(_294, _296))));
    D _307 = inversesqrt(dot(vec3(_294, _296, _303), vec3(_294, _296, _303)));
    D _308 = _307 * _294;
    D _309 = _307 * _296;
    D _310 = _307 * _303;
    vec4 _313 = texture(sampler2D(Material_Texture2D_3, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _318 = texture(sampler2D(Material_Texture2D_4, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _320 = _318.x;
    vec4 _323 = texture(sampler2D(Material_Texture2D_5, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].w);
    vec4 _327 = texture(sampler2D(Material_Texture2D_15, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.z, TEXCOORD.w), View._m0[155u].y);
    D _329 = _327.x;
    D _330 = _329 * _320;
    D _331 = spvNMin(_320, _329);
    D _333 = (1.0 - _331) + _330;
    D _334 = _333 * _333;
    D _337 = 1.0 - ((_334 * _334) * _333);
    D _338 = _337 * _337;
    vec4 _346 = texture(sampler2D(Material_Texture2D_8, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _352 = vec4(g_R.Muddiness.x, g_R.Muddiness.y, g_R.Muddiness.z, 0.0);
    vec4 _359 = texture(sampler2D(Material_Texture2D_20, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _364 = texture(sampler2D(Material_Texture2D_21, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _374 = g_R.TransparencyLog2;
    D _375 = exp2(_374);
    vec4 _378 = texture(sampler2D(Material_Texture2D_22, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _385 = texture(sampler2D(Material_Texture2D_23, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _390 = 1.0 / spvNMax(9.9999999747524270787835121154785e-07, _385.x * 100.0);
    D _397 = g_R.TransmittanceLog2.x;
    D _398 = g_R.TransmittanceLog2.y;
    D _399 = g_R.TransmittanceLog2.z;
    vec4 _405 = vec4(g_R.Thickness);
    D _411 = inversesqrt(dot(vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z), vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z)));
    D _412 = _411 * g_R.Normal.x;
    D _413 = _411 * g_R.Normal.y;
    D _414 = _411 * g_R.Normal.z;
    D _417 = fma(_414, TEXCOORD_11.x, fma(_413, ((TEXCOORD_10.z * TEXCOORD_11.y) - (TEXCOORD_10.y * TEXCOORD_11.z)) * TEXCOORD_11.w, _412 * TEXCOORD_10.x));
    D _420 = fma(_414, TEXCOORD_11.y, fma(_413, ((TEXCOORD_10.x * TEXCOORD_11.z) - (TEXCOORD_10.z * TEXCOORD_11.x)) * TEXCOORD_11.w, _412 * TEXCOORD_10.y));
    D _423 = fma(_414, TEXCOORD_11.z, fma(_413, ((TEXCOORD_10.y * TEXCOORD_11.x) - (TEXCOORD_10.x * TEXCOORD_11.y)) * TEXCOORD_11.w, _412 * TEXCOORD_10.z));
    D _427 = inversesqrt(dot(vec3(_417, _420, _423), vec3(_417, _420, _423)));
    D _428 = _427 * _417;
    D _429 = _427 * _420;
    D _430 = _427 * _423;
    bool _444;
    if (Primitive._m0[27u].w > ((_264.w * 0.99609375) + 0.001953125))
    {
        _444 = _323.x > ((_267 * 0.99609375) + 0.001953125);
    }
    else
    {
        _444 = false;
    }
    (void)((_444 ? 1.0 : (-1.0)) < 0.0);
    D _450 = spvNClamp(g_R.BaseColor.x, 0.0, 1.0);
    D _451 = spvNClamp(g_R.BaseColor.y, 0.0, 1.0);
    D _452 = spvNClamp(g_R.BaseColor.z, 0.0, 1.0);
    D _453 = spvNClamp(g_R.Metallic, 0.0, 1.0);
    D _454 = spvNClamp(g_R.Roughness, 0.0, 1.0);
    D _455 = spvNClamp(g_R.AO, 0.0, 1.0);
    D _456 = spvNClamp(g_R.Opacity, 0.0, 1.0);
    D _458 = dFdxFine(_428);
    D _459 = dFdxFine(_429);
    D _460 = dFdxFine(_430);
    D _464 = dFdyFine(_428);
    D _465 = dFdyFine(_429);
    D _466 = dFdyFine(_430);
    D _477 = sqrt(spvNClamp(spvNMin((dot(vec3(_464, _465, _466), vec3(_464, _465, _466)) + dot(vec3(_458, _459, _460), vec3(_458, _459, _460))) * 0.15915493667125701904296875, 0.180000007152557373046875) + (_454 * _454), 0.0, 1.0));
    D _478 = 1.0 - _453;
    D _479 = _478 * _450;
    D _480 = _478 * _451;
    D _481 = _478 * _452;
    D _486 = _453 * (_450 + (-0.0400000028312206268310546875));
    D _487 = _453 * (_451 + (-0.0400000028312206268310546875));
    D _488 = _453 * (_452 + (-0.0400000028312206268310546875));
    D _489 = _486 + 0.0400000028312206268310546875;
    D _491 = _487 + 0.0400000028312206268310546875;
    D _492 = _488 + 0.0400000028312206268310546875;
    D _499 = spvNClamp(D(View._m0[220u].x > 1.0), 0.0, 1.0);
    D _527 = ((exp2(log2(spvNMax(0.0, _486 + 0.020000003278255462646484375) * 1.020408153533935546875) * 1.39999997615814208984375) - _489) * _499) + _489;
    D _528 = ((exp2(log2(spvNMax(0.0, _487 + 0.020000003278255462646484375) * 1.020408153533935546875) * 1.39999997615814208984375) - _491) * _499) + _491;
    D _529 = ((exp2(log2(spvNMax(0.0, _488 + 0.020000003278255462646484375) * 1.020408153533935546875) * 1.39999997615814208984375) - _492) * _499) + _492;
    D _534 = (_527 * 0.449999988079071044921875) + _479;
    D _535 = (_528 * 0.449999988079071044921875) + _480;
    D _536 = (_529 * 0.449999988079071044921875) + _481;
    D _543 = dot(vec3(_428, _429, _430), vec3(_243, _245, _246));
    D _549 = (_543 * _428) + _240;
    D _550 = (_543 * _429) + _241;
    D _551 = (_543 * _430) + _242;
    D _555 = abs(_543);
    D _559 = (_549 * 2.0) + (_555 * _428);
    D _560 = (_550 * 2.0) + (_555 * _429);
    D _561 = (_551 * 2.0) + (_555 * _430);
    D _565 = inversesqrt(dot(vec3(_559, _560, _561), vec3(_559, _560, _561)));
    D _566 = _559 * _565;
    D _567 = _560 * _565;
    D _568 = _561 * _565;
    D _569 = spvNMax(9.9999997473787516355514526367188e-06, _555);
    D _581 = 1.0 - _477;
    D _595 = ((spvNMin(_581 * _581, exp2(_569 * (-9.27999973297119140625))) * _581) + (0.0425000004470348358154296875 - (_477 * 0.0274999998509883880615234375))) * 1.03999996185302734375;
    D _601 = 1.0 - spvNClamp((((_477 * 0.02199999988079071044921875) + (-0.039999999105930328369140625)) + _595) + (((1.03999996185302734375 - (_477 * 0.572000026702880859375)) - _595) * 0.0400000028312206268310546875), 0.0, 1.0);
    D _602 = _601 * _601;
    D _603 = spvNMax(0.001000000047497451305389404296875, (1.0 / spvNMax(0.0333333350718021392822265625, _569)) * _405.x);
    D _606 = log2(spvNMax(0.0, _375));
    D _608 = exp2(_606 * _603);
    D _612 = log2(spvNMax(0.0, exp2(_397)));
    D _613 = log2(spvNMax(0.0, exp2(_398)));
    D _614 = log2(spvNMax(0.0, exp2(_399)));
    D _618 = exp2(_612 * _603);
    D _619 = exp2(_613 * _603);
    D _620 = exp2(_614 * _603);
    D _622 = exp2(_606 * 0.001000000047497451305389404296875);
    D _629 = 1.0 - _456;
    D _631 = (_602 * _629) * _608;
    D _634 = ((_631 * _618) * _622) * exp2(_612 * 0.001000000047497451305389404296875);
    D _637 = ((_631 * _619) * _622) * exp2(_613 * 0.001000000047497451305389404296875);
    D _640 = ((_631 * _620) * _622) * exp2(_614 * 0.001000000047497451305389404296875);
    D _647 = spvNMax(0.039999999105930328369140625, _477);
    D _663 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_647 * _569) + 0.02669160068035125732421875) / (_569 + 0.4664950072765350341796875)) * exp2(((1.0 / _647) * _569) * log2(_647)), 0.0, 1.0));
    D _664 = 1.0 - _569;
    D _665 = _664 * _664;
    D _678 = _665 * _665;
    D _680 = (_678 * _664) * exp2(log2((exp2((_647 * 4.7702999114990234375) * log2(_569)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _647);
    D _683 = (1.0 / _663) * (1.0 - _663);
    D _690 = _663 - _680;
    D _697 = ((_683 * _527) + 1.0) * ((_690 * _527) + _680);
    D _698 = ((_683 * _528) + 1.0) * ((_690 * _528) + _680);
    D _699 = ((_683 * _529) + 1.0) * ((_690 * _529) + _680);
    D _705 = spvNClamp(1.0 - dot(vec3(_697, _698, _699), vec3(0.3333333432674407958984375)), 0.0, 1.0);
    D _719 = spvNClamp((_455 + (-1.0)) + exp2(log2(_569 + _455) * exp2((-1.0) - (_477 * 16.0))), 0.0, 1.0);
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
                    if (_104 < TranslucentBasePass._m0[_1297 + 32u])
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
                    uint _1745 = _1394 << 2u;
                    uint _1746 = _1745 + 9u;
                    uint _1753 = _1745 + 10u;
                    uint _1760 = _1745 + 11u;
                    uint _1767 = _1745 + 12u;
                    uint _1774 = _1394 + 25u;
                    D _1800 = fma(_234, TranslucentBasePass_2._m0[_1760].z, fma(_233, TranslucentBasePass_2._m0[_1753].z, TranslucentBasePass_2._m0[_1746].z * _232)) + TranslucentBasePass_2._m0[_1767].z;
                    D _1804 = fma(_234, TranslucentBasePass_2._m0[_1760].w, fma(_233, TranslucentBasePass_2._m0[_1753].w, TranslucentBasePass_2._m0[_1746].w * _232)) + TranslucentBasePass_2._m0[_1767].w;
                    D _1805 = (fma(_234, TranslucentBasePass_2._m0[_1760].x, fma(_233, TranslucentBasePass_2._m0[_1753].x, TranslucentBasePass_2._m0[_1746].x * _232)) + TranslucentBasePass_2._m0[_1767].x) / _1804;
                    D _1806 = (fma(_234, TranslucentBasePass_2._m0[_1760].y, fma(_233, TranslucentBasePass_2._m0[_1753].y, TranslucentBasePass_2._m0[_1746].y * _232)) + TranslucentBasePass_2._m0[_1767].y) / _1804;
                    bool _1813 = (_1806 <= TranslucentBasePass_2._m0[_1774].w) && ((_1805 <= TranslucentBasePass_2._m0[_1774].z) && ((_1805 >= TranslucentBasePass_2._m0[_1774].x) && (_1806 >= TranslucentBasePass_2._m0[_1774].y)));
                    D _1230;
                    if (_1813)
                    {
                        D _2170 = dFdyFine(_1805);
                        D _2171 = dFdyFine(_1806);
                        D _2172 = dFdyFine(_1800);
                        D _2173 = dFdxFine(_1805);
                        D _2174 = dFdxFine(_1806);
                        D _2175 = dFdxFine(_1800);
                        D _2178 = (_2174 * _2172) - (_2175 * _2171);
                        D _2181 = (_2175 * _2170) - (_2173 * _2172);
                        D _2184 = (_2173 * _2171) - (_2174 * _2170);
                        D _2194 = 1.0 / spvNMax(abs(_2184), sqrt(((_2181 * _2181) + (_2184 * _2184)) + (_2178 * _2178)) * 0.100000001490116119384765625);
                        D _2200 = D(int(uint(_2184 > 0.0) - uint(_2184 < 0.0)));
                        D _2201 = _2178 * TranslucentBasePass_2._m0[29u].z;
                        D _2203 = (_2201 * _2194) * _2200;
                        D _2204 = _2181 * TranslucentBasePass_2._m0[29u].w;
                        D _2206 = (_2204 * _2194) * _2200;
                        D _2798;
                        D _2800;
                        if (dot(vec2(_2178, _2181), vec2(_2178, _2181)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2798 = 0.0;
                            _2800 = 0.0;
                        }
                        else
                        {
                            D _3168 = (-0.0) - _2178;
                            D _3169 = (-0.0) - _2181;
                            D _3173 = inversesqrt(dot(vec2(_3168, _3169), vec2(_3168, _3169)));
                            _2798 = _3173 * _3168;
                            _2800 = _3173 * _3169;
                        }
                        D _2802 = _268 + (-0.5);
                        D _2807 = _267 + 0.5;
                        D _2810 = ((_2800 * _2802) + (_1805 * TranslucentBasePass_2._m0[29u].x)) + (_2798 * _2807);
                        D _2813 = ((_2798 * _2802) + (_1806 * TranslucentBasePass_2._m0[29u].y)) + (_2800 * _2807);
                        D _2814 = _2810 + (-0.5);
                        D _2815 = _2813 + (-0.5);
                        D _2816 = trunc(_2814);
                        D _2817 = trunc(_2815);
                        D _2818 = _2814 - _2816;
                        D _2819 = _2815 - _2817;
                        D _2820 = _2816 * TranslucentBasePass_2._m0[29u].z;
                        D _2821 = _2817 * TranslucentBasePass_2._m0[29u].w;
                        D _2824 = (_2816 + (-0.5)) - _2810;
                        D _2825 = (_2817 + (-0.5)) - _2813;
                        D _2826 = dot(vec2(_2824, _2825), vec2(_2203, _2206));
                        D _2829 = _2826 + _2206;
                        D _2832 = _2200 * (_2194 * (_2204 + _2201));
                        D _2833 = _2832 + _2826;
                        D _2834 = _2826 + _2203;
                        vec4 _2840 = textureGather((sampler2D(ShadowMaps[_1394 + 0u], View_SharedPointClampedSampler)), vec2(_2820, _2821));
                        D _2841 = _2840.x;
                        D _2842 = _2840.y;
                        D _2843 = _2840.z;
                        D _2844 = _2840.w;
                        D _2881 = 1.525902189314365386962890625e-05 - _1800;
                        D _2912 = (_2816 + 1.5) - _2810;
                        D _2913 = dot(vec2(_2912, _2825), vec2(_2203, _2206));
                        D _2916 = _2913 + _2206;
                        D _2917 = _2832 + _2913;
                        D _2918 = _2913 + _2203;
                        vec4 _2920 = textureGatherOffset((sampler2D(ShadowMaps[_1394 + 0u], View_SharedPointClampedSampler)), vec2(_2820, _2821), ivec2(2, 0));
                        D _2921 = _2920.x;
                        D _2922 = _2920.y;
                        D _2923 = _2920.z;
                        D _2924 = _2920.w;
                        D _2990 = (_2817 + 1.5) - _2813;
                        D _2991 = dot(vec2(_2824, _2990), vec2(_2203, _2206));
                        D _2994 = _2991 + _2206;
                        D _2995 = _2832 + _2991;
                        D _2996 = _2991 + _2203;
                        vec4 _2998 = textureGatherOffset((sampler2D(ShadowMaps[_1394 + 0u], View_SharedPointClampedSampler)), vec2(_2820, _2821), ivec2(0, 2));
                        D _2999 = _2998.x;
                        D _3000 = _2998.y;
                        D _3001 = _2998.z;
                        D _3002 = _2998.w;
                        D _3067 = dot(vec2(_2912, _2990), vec2(_2203, _2206));
                        D _3070 = _3067 + _2206;
                        D _3071 = _2832 + _3067;
                        D _3072 = _3067 + _2203;
                        vec4 _3074 = textureGatherOffset((sampler2D(ShadowMaps[_1394 + 0u], View_SharedPointClampedSampler)), vec2(_2820, _2821), ivec2(2));
                        D _3075 = _3074.x;
                        D _3076 = _3074.y;
                        D _3077 = _3074.z;
                        D _3078 = _3074.w;
                        D _3143 = 1.0 - _2818;
                        vec4 _3166 = vec4((((((_2844 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2881 + _2844) + (spvNMin(abs(_2826), 0.0) * D(int(uint(_2826 > 0.0) - uint(_2826 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3143) + ((_2843 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2881 + _2843) + (spvNMin(abs(_2834), 0.0) * D(int(uint(_2834 > 0.0) - uint(_2834 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2924 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2881 + _2924) + (spvNMin(abs(_2913), 0.0) * D(int(uint(_2913 > 0.0) - uint(_2913 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2923 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2881 + _2923) + (spvNMin(abs(_2918), 0.0) * D(int(uint(_2918 > 0.0) - uint(_2918 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2818), (((((_2841 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2881 + _2841) + (spvNMin(abs(_2829), 0.0) * D(int(uint(_2829 > 0.0) - uint(_2829 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3143) + ((_2842 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2881 + _2842) + (spvNMin(abs(_2833), 0.0) * D(int(uint(_2833 > 0.0) - uint(_2833 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2921 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2881 + _2921) + (spvNMin(abs(_2916), 0.0) * D(int(uint(_2916 > 0.0) - uint(_2916 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2922 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2881 + _2922) + (spvNMin(abs(_2917), 0.0) * D(int(uint(_2917 > 0.0) - uint(_2917 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2818), (((((_3002 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2881 + _3002) + (spvNMin(abs(_2991), 0.0) * D(int(uint(_2991 > 0.0) - uint(_2991 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3143) + ((_3001 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2881 + _3001) + (spvNMin(abs(_2996), 0.0) * D(int(uint(_2996 > 0.0) - uint(_2996 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3078 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2881 + _3078) + (spvNMin(abs(_3067), 0.0) * D(int(uint(_3067 > 0.0) - uint(_3067 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3077 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2881 + _3077) + (spvNMin(abs(_3072), 0.0) * D(int(uint(_3072 > 0.0) - uint(_3072 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2818), (((((_2999 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2881 + _2999) + (spvNMin(abs(_2994), 0.0) * D(int(uint(_2994 > 0.0) - uint(_2994 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3143) + ((_3000 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2881 + _3000) + (spvNMin(abs(_2995), 0.0) * D(int(uint(_2995 > 0.0) - uint(_2995 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3075 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2881 + _3075) + (spvNMin(abs(_3070), 0.0) * D(int(uint(_3070 > 0.0) - uint(_3070 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3076 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2881 + _3076) + (spvNMin(abs(_3071), 0.0) * D(int(uint(_3071 > 0.0) - uint(_3071 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2818));
                        _1230 = dot(_3166, vec4(1.0 - _2819, 1.0, 1.0, _2819)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        _1230 = 1.0;
                    }
                    if (_1813)
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
            D _1270 = fma(_234, TranslucentBasePass_2._m0[35u].z, fma(_233, TranslucentBasePass_2._m0[34u].z, TranslucentBasePass_2._m0[33u].z * _232)) + TranslucentBasePass_2._m0[36u].z;
            D _1274 = fma(_234, TranslucentBasePass_2._m0[35u].w, fma(_233, TranslucentBasePass_2._m0[34u].w, TranslucentBasePass_2._m0[33u].w * _232)) + TranslucentBasePass_2._m0[36u].w;
            D _1275 = (fma(_234, TranslucentBasePass_2._m0[35u].x, fma(_233, TranslucentBasePass_2._m0[34u].x, TranslucentBasePass_2._m0[33u].x * _232)) + TranslucentBasePass_2._m0[36u].x) / _1274;
            D _1276 = (fma(_234, TranslucentBasePass_2._m0[35u].y, fma(_233, TranslucentBasePass_2._m0[34u].y, TranslucentBasePass_2._m0[33u].y * _232)) + TranslucentBasePass_2._m0[36u].y) / _1274;
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
            D _1672;
            D _1674;
            if (dot(vec2(_1365, _1368), vec2(_1365, _1368)) < 1.0000000195414813782625560981111e-24)
            {
                _1672 = 0.0;
                _1674 = 0.0;
            }
            else
            {
                D _1738 = (-0.0) - _1365;
                D _1739 = (-0.0) - _1368;
                D _1743 = inversesqrt(dot(vec2(_1738, _1739), vec2(_1738, _1739)));
                _1672 = _1743 * _1738;
                _1674 = _1743 * _1739;
            }
            D _1680 = _268 + (-0.5);
            D _1688 = (((_1674 * _1680) + (_1672 * _267)) * 2.0) + (_1672 * 0.5);
            D _1689 = (((_1674 * _267) + (_1672 * _1680)) * 2.0) + (_1674 * 0.5);
            D _1695 = _1688 + (fract(_1275) * 256.0);
            D _1696 = _1689 + (fract(_1276) * 256.0);
            D _1709 = dot(vec2((floor(_1695) + 0.5) - _1695, (floor(_1696) + 0.5) - _1696), vec2(((_1365 * 256.0) * _1382) * _1388, ((_1368 * 256.0) * _1382) * _1388));
            D _1715 = (_1688 * 0.00390625) + _1275;
            D _1716 = (_1689 * 0.00390625) + _1276;
            uint _1728 = ((uint(int((-0.0) - floor(_1716))) - _1282) * (_1283 - _1281)) + (uint(int(floor(_1715))) - _1281);
            D _2142;
            D _2145;
            if ((texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowLoadedTileData, int(_1728 >> 5u)).x & (1u << (_1728 & 31u))) == 0u)
            {
                _2142 = 3.0000000054977557577780399428115e+38;
                _2145 = 0.0;
            }
            else
            {
                uvec4 _2167 = uvec4(texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileIndices, int(_1728)));
                uint _2168 = _2167.x;
                D frontier_phi_51_52_ladder;
                D frontier_phi_51_52_ladder_1;
                if (int(_2168) > int(4294967295u))
                {
                    uint _2784 = (uint(floor(fract(_1715) * 256.0)) + (_2168 << 16u)) + (uint(floor(fract(_1716) * 256.0)) << 8u);
                    uvec4 _2787 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileData, int(_2784 >> 1u));
                    uint _2788 = _2787.x;
                    D _2796 = D((((_2784 & 1u) == 0u) ? _2788 : (_2788 >> 16u)) & 65535u) * 1.525902189314365386962890625e-05;
                    D frontier_phi_51_52_ladder_73_ladder;
                    D frontier_phi_51_52_ladder_73_ladder_1;
                    if (_2796 != 1.0)
                    {
                        vec4 _3597 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthRanges, int(_2168));
                        D _3599 = _3597.y;
                        frontier_phi_51_52_ladder_73_ladder = 1.0 / _3599;
                        frontier_phi_51_52_ladder_73_ladder_1 = (_3599 * _2796) + _3597.x;
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
                _2142 = frontier_phi_51_52_ladder_1;
                _2145 = frontier_phi_51_52_ladder;
            }
            _1229 = spvNClamp(((((1.525902189314365386962890625e-05 - _1270) + _2142) + (spvNMin(abs(_1709), _2145 * 10.0) * D(int(uint(_1709 > 0.0) - uint(_1709 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0);
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
        uint _1670;
        if (_1349 > 1u)
        {
            D _132[4];
            _132[0u] = 0.0;
            _132[1u] = 0.0;
            _132[2u] = 0.0;
            _132[3u] = 0.0;
            uint _2127 = 0u;
            bool _2133;
            for (;;)
            {
                _2133 = _2127 < floatBitsToUint(View._m0[220u]).y;
                if (_2133)
                {
                    uint _2735 = _2127 + 237u;
                    D _2749 = View._m0[_2735].x - View._m0[75u].x;
                    D _2750 = View._m0[_2735].y - View._m0[75u].y;
                    D _2751 = View._m0[_2735].z - View._m0[75u].z;
                    D _2752 = dot(vec3(_2749, _2750, _2751), vec3(_240, _241, _242));
                    D _2759 = dot(vec3(_2749, _2750, _2751), vec3(_2749, _2750, _2751)) - (View._m0[_2735].w * View._m0[_2735].w);
                    D _2761 = (_2752 * _2752) - _2759;
                    D _3373;
                    if ((_2759 < 0.0) && (!(_2761 < 0.0)))
                    {
                        D _3367 = sqrt(_2761);
                        _3373 = spvNMin(abs(_3367 + _2752), abs(_2752 - _3367));
                    }
                    else
                    {
                        _3373 = 0.0;
                    }
                    _132[_2127] = _3373;
                }
                uint _2128 = _2127 + 1u;
                if (_2128 == 4u)
                {
                    break;
                }
                else
                {
                    _2127 = _2128;
                    continue;
                }
            }
            D _3384 = (_267 * 0.99989998340606689453125) * dot(vec4(_132[0u], _132[1u], _132[2u], _132[3u]), vec4(1.0));
            uint frontier_phi_32_83_ladder;
            if (_132[0u] > _3384)
            {
                frontier_phi_32_83_ladder = 0u;
            }
            else
            {
                D _3735 = _132[1u] + _132[0u];
                uint frontier_phi_32_83_ladder_94_ladder;
                if (_3735 > _3384)
                {
                    frontier_phi_32_83_ladder_94_ladder = 1u;
                }
                else
                {
                    D _3819 = _3735 + _132[2u];
                    uint frontier_phi_32_83_ladder_94_ladder_102_ladder;
                    if (_3819 > _3384)
                    {
                        frontier_phi_32_83_ladder_94_ladder_102_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder;
                        if ((_3819 + _132[3u]) > _3384)
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
            _1670 = frontier_phi_32_83_ladder;
        }
        else
        {
            _1670 = _1352;
        }
        D _2134;
        if (_1670 == 4294967295u)
        {
            _2134 = _1344;
        }
        else
        {
            _2134 = View._m0[_1670 + 241u].x * _1344;
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
        if (_2134 > 0.0)
        {
            D _2768 = spvNClamp((TranslucentBasePass_2._m0[7u].x * _104) + TranslucentBasePass_2._m0[7u].y, 0.0, 1.0);
            D _2772 = ((_2768 * _2768) * (1.0 - _1229)) + _1229;
            D frontier_phi_3_49_ladder_72_ladder;
            D frontier_phi_3_49_ladder_72_ladder_1;
            D frontier_phi_3_49_ladder_72_ladder_2;
            D frontier_phi_3_49_ladder_72_ladder_3;
            D frontier_phi_3_49_ladder_72_ladder_4;
            D frontier_phi_3_49_ladder_72_ladder_5;
            D frontier_phi_3_49_ladder_72_ladder_6;
            D frontier_phi_3_49_ladder_72_ladder_7;
            D frontier_phi_3_49_ladder_72_ladder_8;
            if (_2772 > 0.0)
            {
                D _3386 = dot(vec3(_428, _429, _430), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3389 = spvNMax(0.0, _3386);
                D _3390 = dot(vec3(_243, _245, _246), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3396 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3390 * 2.0) + 2.0));
                D _3399 = spvNClamp(_3396 * (_543 + _3386), 0.0, 1.0);
                D _3414 = sqrt(spvNMax(0.0, 1.0 - ((1.0 - (_543 * _543)) * 0.444444477558135986328125)));
                D _3418 = (_549 * 0.666666686534881591796875) - (_3414 * _428);
                D _3419 = (_550 * 0.666666686534881591796875) - (_3414 * _429);
                D _3420 = (_551 * 0.666666686534881591796875) - (_3414 * _430);
                D _3424 = inversesqrt(dot(vec3(_3418, _3419, _3420), vec3(_3418, _3419, _3420)));
                D _3431 = dot(vec3((-0.0) - (_3424 * _3418), (-0.0) - (_3424 * _3419), (-0.0) - (_3424 * _3420)), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3434 = _647 * _647;
                D _3435 = _3434 * _3434;
                D _3439 = ((_3399 * _3399) * (_3435 + (-1.0))) + 1.0;
                D _3445 = (_3389 * 2.0) * _569;
                D _3450 = 1.0 - spvNMax(9.9999997473787516355514526367188e-06, spvNMin(_3396 * (_3390 + 1.0), 1.0));
                D _3451 = _3450 * _3450;
                D _3453 = (_3451 * _3451) * _3450;
                D _3458 = spvNMin(dot(vec3(_527, _528, _529), vec3(16.666667938232421875)), 1.0);
                D _3471 = spvNMax(0.039999999105930328369140625, _647);
                D _3484 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_3471 * _3389) + 0.02669160068035125732421875) / (_3389 + 0.4664950072765350341796875)) * exp2(((1.0 / _3471) * _3389) * log2(_3471)), 0.0, 1.0));
                D _3485 = 1.0 - _3389;
                D _3486 = _3485 * _3485;
                D _3498 = ((_3486 * _3486) * _3485) * exp2(log2((exp2((_3471 * 4.7702999114990234375) * log2(_3389)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _3471);
                D _3501 = (1.0 / _3484) * (1.0 - _3484);
                D _3505 = (_3501 * _527) + 1.0;
                D _3506 = (_3501 * _528) + 1.0;
                D _3507 = (_3501 * _529) + 1.0;
                D _3508 = _3484 - _3498;
                D _3522 = spvNClamp(1.0 - dot(vec3(_3505 * ((_3508 * _527) + _3498), _3506 * ((_3508 * _528) + _3498), _3507 * ((_3508 * _529) + _3498)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                D _3525 = (((_3435 * 0.3183098733425140380859375) * _3389) * (1.0 / (_3439 * _3439))) * (0.5 / ((_3434 * ((_569 + _3389) - _3445)) + _3445));
                D _3526 = _3389 * 0.3183098733425140380859375;
                D _3529 = ((_3431 * _3431) + 1.0) * 0.05968309938907623291015625;
                D _3531 = spvNMin(1.0, _455);
                D _3533 = (_455 + 1.0) - _3531;
                D _3534 = _3533 * _3533;
                D _3537 = 1.0 - ((_3534 * _3534) * _3533);
                D _3538 = _3537 * _3537;
                D _3543 = ((_3538 * _3538) * (_3537 * (_455 - _3531))) + _3531;
                D _3546 = sqrt(spvNMax(0.0, 1.0 - _3543));
                D _3551 = 1.0 - spvNClamp((_647 * 3.5) + (-0.5), 0.0, 1.0);
                D _3552 = _3551 * _3551;
                D _3562 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_678 * _3546) * spvNClamp(1.0 - ((_3552 * _3552) * _3551), 0.0, 1.0))) * _3389, 0.0, 1.0);
                D _3567 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _3546)) * _3389, 0.0, 1.0);
                D _3569 = spvNMin(_2772, _3562 * _3562);
                D _3570 = spvNMin(_2772, _3567 * _3567);
                D _3571 = spvNMin(_2772, _3543);
                D _3572 = _2134 * TranslucentBasePass_2._m0[4u].x;
                D _3573 = _2134 * TranslucentBasePass_2._m0[4u].y;
                D _3574 = _2134 * TranslucentBasePass_2._m0[4u].z;
                frontier_phi_3_49_ladder_72_ladder = (_3529 * _3574) * _3571;
                frontier_phi_3_49_ladder_72_ladder_1 = (((_3572 * _479) * _3526) * _3522) * _3570;
                frontier_phi_3_49_ladder_72_ladder_2 = (((_3573 * _480) * _3526) * _3522) * _3570;
                frontier_phi_3_49_ladder_72_ladder_3 = (((_3574 * _481) * _3526) * _3522) * _3570;
                frontier_phi_3_49_ladder_72_ladder_4 = (((_3525 * _3572) * spvNClamp(((_3458 - _527) * _3453) + _527, 0.0, 1.0)) * _3505) * _3569;
                frontier_phi_3_49_ladder_72_ladder_5 = (((_3525 * _3573) * spvNClamp(((_3458 - _528) * _3453) + _528, 0.0, 1.0)) * _3506) * _3569;
                frontier_phi_3_49_ladder_72_ladder_6 = (((_3525 * _3574) * spvNClamp(((_3458 - _529) * _3453) + _529, 0.0, 1.0)) * _3507) * _3569;
                frontier_phi_3_49_ladder_72_ladder_7 = (_3529 * _3572) * _3571;
                frontier_phi_3_49_ladder_72_ladder_8 = (_3529 * _3573) * _3571;
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
                D _1623;
                if (_1223)
                {
                    uint _1588 = _1197 + 0u;
                    uvec2 _1591 = uvec2(textureSize(ShadowMaps[(_1588)], int(0u)));
                    D _1593 = D(int(_1591.x));
                    D _1595 = D(int(_1591.y));
                    D _1596 = 1.0 / _1593;
                    D _1597 = 1.0 / _1595;
                    D _1609 = fma(_234, _1213, fma(_233, _1207, _1201 * _232)) + _1219;
                    D _1613 = fma(_234, _1214, fma(_233, _1208, _1202 * _232)) + _1220;
                    D _1614 = (fma(_234, _1211, fma(_233, _1205, _1199 * _232)) + _1217) / _1613;
                    D _1615 = (fma(_234, _1212, fma(_233, _1206, _1200 * _232)) + _1218) / _1613;
                    D frontier_phi_28_27_ladder;
                    if ((_1615 <= _1194) && ((_1614 <= _1193) && ((_1614 >= _1191) && (_1615 >= _1192))))
                    {
                        D _2011 = dFdyFine(_1614);
                        D _2012 = dFdyFine(_1615);
                        D _2013 = dFdyFine(_1609);
                        D _2014 = dFdxFine(_1614);
                        D _2015 = dFdxFine(_1615);
                        D _2016 = dFdxFine(_1609);
                        D _2019 = (_2015 * _2013) - (_2016 * _2012);
                        D _2022 = (_2016 * _2011) - (_2014 * _2013);
                        D _2025 = (_2014 * _2012) - (_2015 * _2011);
                        D _2035 = 1.0 / spvNMax(abs(_2025), sqrt(((_2022 * _2022) + (_2025 * _2025)) + (_2019 * _2019)) * 0.100000001490116119384765625);
                        D _2041 = D(int(uint(_2025 > 0.0) - uint(_2025 < 0.0)));
                        D _2042 = _2019 * _1596;
                        D _2044 = (_2042 * _2035) * _2041;
                        D _2045 = _2022 * _1597;
                        D _2047 = (_2045 * _2035) * _2041;
                        D _2330;
                        D _2332;
                        if (dot(vec2(_2019, _2022), vec2(_2019, _2022)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2330 = 0.0;
                            _2332 = 0.0;
                        }
                        else
                        {
                            D _2673 = (-0.0) - _2019;
                            D _2674 = (-0.0) - _2022;
                            D _2678 = inversesqrt(dot(vec2(_2673, _2674), vec2(_2673, _2674)));
                            _2330 = _2678 * _2673;
                            _2332 = _2678 * _2674;
                        }
                        D _2334 = _268 + (-0.5);
                        D _2339 = _267 + 0.5;
                        D _2342 = ((_2332 * _2334) + (_1614 * _1593)) + (_2330 * _2339);
                        D _2345 = ((_2330 * _2334) + (_1615 * _1595)) + (_2332 * _2339);
                        D _2346 = _2342 + (-0.5);
                        D _2347 = _2345 + (-0.5);
                        D _2348 = trunc(_2346);
                        D _2349 = trunc(_2347);
                        D _2350 = _2346 - _2348;
                        D _2351 = _2347 - _2349;
                        D _2352 = _2348 * _1596;
                        D _2353 = _2349 * _1597;
                        D _2356 = (_2348 + (-0.5)) - _2342;
                        D _2357 = (_2349 + (-0.5)) - _2345;
                        D _2358 = dot(vec2(_2356, _2357), vec2(_2044, _2047));
                        D _2361 = _2358 + _2047;
                        D _2364 = _2041 * (_2035 * (_2045 + _2042));
                        D _2365 = _2364 + _2358;
                        D _2366 = _2358 + _2044;
                        vec4 _2370 = textureGather((sampler2D(ShadowMaps[_1588], View_SharedPointClampedSampler)), vec2(_2352, _2353));
                        D _2411 = 1.525902189314365386962890625e-05 - _1609;
                        D _2434 = (_2348 + 1.5) - _2342;
                        D _2435 = dot(vec2(_2434, _2357), vec2(_2044, _2047));
                        D _2438 = _2435 + _2047;
                        D _2439 = _2364 + _2435;
                        D _2440 = _2435 + _2044;
                        vec4 _2444 = textureGatherOffset((sampler2D(ShadowMaps[_1588], View_SharedPointClampedSampler)), vec2(_2352, _2353), ivec2(2, 0));
                        D _2508 = (_2349 + 1.5) - _2345;
                        D _2509 = dot(vec2(_2356, _2508), vec2(_2044, _2047));
                        D _2512 = _2509 + _2047;
                        D _2513 = _2364 + _2509;
                        D _2514 = _2509 + _2044;
                        vec4 _2516 = textureGatherOffset((sampler2D(ShadowMaps[_1588], View_SharedPointClampedSampler)), vec2(_2352, _2353), ivec2(0, 2));
                        D _2578 = dot(vec2(_2434, _2508), vec2(_2044, _2047));
                        D _2581 = _2578 + _2047;
                        D _2582 = _2364 + _2578;
                        D _2583 = _2578 + _2044;
                        vec4 _2585 = textureGatherOffset((sampler2D(ShadowMaps[_1588], View_SharedPointClampedSampler)), vec2(_2352, _2353), ivec2(2));
                        D _2647 = 1.0 - _2350;
                        vec4 _2670 = vec4((((spvNClamp((((_2411 + _2370.w) + (spvNMin(abs(_2358), 0.0) * D(int(uint(_2358 > 0.0) - uint(_2358 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2647) + spvNClamp((((_2411 + _2370.z) + (spvNMin(abs(_2366), 0.0) * D(int(uint(_2366 > 0.0) - uint(_2366 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2411 + _2444.w) + (spvNMin(abs(_2435), 0.0) * D(int(uint(_2435 > 0.0) - uint(_2435 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2411 + _2444.z) + (spvNMin(abs(_2440), 0.0) * D(int(uint(_2440 > 0.0) - uint(_2440 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2350), (((spvNClamp((((_2411 + _2370.x) + (spvNMin(abs(_2361), 0.0) * D(int(uint(_2361 > 0.0) - uint(_2361 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2647) + spvNClamp((((_2411 + _2370.y) + (spvNMin(abs(_2365), 0.0) * D(int(uint(_2365 > 0.0) - uint(_2365 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2411 + _2444.x) + (spvNMin(abs(_2438), 0.0) * D(int(uint(_2438 > 0.0) - uint(_2438 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2411 + _2444.y) + (spvNMin(abs(_2439), 0.0) * D(int(uint(_2439 > 0.0) - uint(_2439 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2350), (((spvNClamp((((_2411 + _2516.w) + (spvNMin(abs(_2509), 0.0) * D(int(uint(_2509 > 0.0) - uint(_2509 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2647) + spvNClamp((((_2411 + _2516.z) + (spvNMin(abs(_2514), 0.0) * D(int(uint(_2514 > 0.0) - uint(_2514 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2411 + _2585.w) + (spvNMin(abs(_2578), 0.0) * D(int(uint(_2578 > 0.0) - uint(_2578 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2411 + _2585.z) + (spvNMin(abs(_2583), 0.0) * D(int(uint(_2583 > 0.0) - uint(_2583 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2350), (((spvNClamp((((_2411 + _2516.x) + (spvNMin(abs(_2512), 0.0) * D(int(uint(_2512 > 0.0) - uint(_2512 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2647) + spvNClamp((((_2411 + _2516.y) + (spvNMin(abs(_2513), 0.0) * D(int(uint(_2513 > 0.0) - uint(_2513 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2411 + _2585.x) + (spvNMin(abs(_2581), 0.0) * D(int(uint(_2581 > 0.0) - uint(_2581 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2411 + _2585.y) + (spvNMin(abs(_2582), 0.0) * D(int(uint(_2582 > 0.0) - uint(_2582 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2350));
                        frontier_phi_28_27_ladder = dot(_2670, vec4(1.0 - _2351, 1.0, 1.0, _2351)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        frontier_phi_28_27_ladder = 1.0;
                    }
                    _1623 = frontier_phi_28_27_ladder;
                }
                else
                {
                    _1623 = 1.0;
                }
                D _1629 = _1163 - _232;
                D _1630 = _1164 - _233;
                D _1631 = _1165 - _234;
                D _1632 = dot(vec3(_1629, _1630, _1631), vec3(_1629, _1630, _1631));
                D _2056;
                D _2057;
                D _2058;
                if (_1632 > 9.9999997473787516355514526367188e-05)
                {
                    D _2052 = inversesqrt(_1632);
                    _2056 = _2052 * _1629;
                    _2057 = _2052 * _1630;
                    _2058 = _2052 * _1631;
                }
                else
                {
                    _2056 = 0.0;
                    _2057 = 0.0;
                    _2058 = 0.0;
                }
                D _2059 = _1185 * _1185;
                D _2063 = (_1166 * _1166) * _1632;
                D _2066 = spvNClamp(1.0 - (_2063 * _2063), 0.0, 1.0);
                D _2686;
                if (_1224)
                {
                    D _2684 = spvNClamp((dot(vec3(_2056, _2057, _2058), vec3(_1172, _1173, _1174)) - _1178) * _1179, 0.0, 1.0);
                    _2686 = _2684 * _2684;
                }
                else
                {
                    _2686 = 1.0;
                }
                D _2687 = ((_2066 * _2066) * D(_1632 >= _2059)) * _2686;
                D _3230;
                D _3232;
                D _3234;
                if ((_1176 & 262144u) == 0u)
                {
                    _3230 = 1.0;
                    _3232 = 1.0;
                    _3234 = 1.0;
                }
                else
                {
                    D _3237 = (-0.0) - _1173;
                    D _3238 = (-0.0) - _1174;
                    D _3239 = (-0.0) - _1172;
                    D _3249 = (-0.0) - _2056;
                    D _3250 = (-0.0) - _2057;
                    D _3251 = (-0.0) - _2058;
                    D _3254 = fma(_3238, _3251, fma(_3237, _3250, _2056 * _1172));
                    D _3257 = fma(_1183, _3251, fma(_1182, _3250, _1181 * _3249));
                    D _3265 = atan(((-0.0) - _3257) / ((-0.0) - _3254));
                    bool _3270 = _3254 > (-0.0);
                    bool _3271 = _3254 == (-0.0);
                    bool _3272 = _3257 <= (-0.0);
                    bool _3273 = _3257 > (-0.0);
                    vec4 _3295 = texture((sampler2D(ForwardLightProfileTextures[_1188 + 0u], View_SharedBilinearWrappedSampler)), vec2(fract((_3271 && _3272) ? 1.25 : ((_3271 && _3273) ? 0.75 : ((((_3270 && _3273) ? (_3265 + (-3.1415927410125732421875)) : ((_3270 && _3272) ? (_3265 + 3.1415927410125732421875) : _3265)) * 0.15915493667125701904296875) + 1.0))), (asin((-0.0) - fma((_1182 * _3239) - (_1181 * _3237), _3251, fma((_1181 * _3238) - (_1183 * _3239), _3250, ((_1183 * _3237) - (_1182 * _3238)) * _3249))) * 0.3183098733425140380859375) + 0.5));
                    _3230 = _3295.x;
                    _3232 = _3295.y;
                    _3234 = _3295.z;
                }
                D _3686;
                D _3688;
                D _3690;
                D _3692;
                D _3694;
                D _3696;
                D _3698;
                D _3700;
                D _3702;
                for (;;)
                {
                    if (_2687 > 0.0)
                    {
                        D _3811;
                        if (_1223)
                        {
                            if (!(_1623 > 0.0))
                            {
                                _3686 = 0.0;
                                _3688 = 0.0;
                                _3690 = 0.0;
                                _3692 = 0.0;
                                _3694 = 0.0;
                                _3696 = 0.0;
                                _3698 = 0.0;
                                _3700 = 0.0;
                                _3702 = 0.0;
                                break;
                            }
                            _3811 = _1623;
                        }
                        else
                        {
                            _3811 = 1.0;
                        }
                        D _3813 = spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1632));
                        D _3814 = 1.0 / _3813;
                        D _3815 = dot(vec3(_428, _429, _430), vec3(_2056, _2057, _2058));
                        D _3836;
                        if (_1185 > 0.0)
                        {
                            D _3833 = sqrt(spvNClamp(_2059 * _3814, 0.0, 1.0));
                            D frontier_phi_107_106_ladder;
                            if (_3833 > spvNMax(9.9999997473787516355514526367188e-06, _3815))
                            {
                                D _3855 = spvNMax((-0.0) - _3833, _3815) + _3833;
                                frontier_phi_107_106_ladder = (_3855 * _3855) * (0.25 / _3833);
                            }
                            else
                            {
                                frontier_phi_107_106_ladder = _3815;
                            }
                            _3836 = frontier_phi_107_106_ladder;
                        }
                        else
                        {
                            _3836 = _3815;
                        }
                        D _3898;
                        D _3899;
                        D _3838;
                        D _3840;
                        D _3844;
                        D _3845;
                        bool _3848;
                        for (;;)
                        {
                            _3838 = spvNMax(0.0, _3836);
                            _3840 = _647 * _647;
                            _3844 = spvNClamp(((1.0 - _3840) * _1185) * inversesqrt(_3813), 0.0, 1.0);
                            _3845 = dot(vec3(_243, _245, _246), vec3(_2056, _2057, _2058));
                            _3848 = _3844 > 0.0;
                            D _3866;
                            D _3868;
                            if (_3848)
                            {
                                D _3861 = sqrt(spvNMax(0.0, 1.0 - (_3844 * _3844)));
                                D _3864 = ((_3815 * 2.0) * _543) - _3845;
                                if (!(!(_3864 >= _3861)))
                                {
                                    _3898 = _555;
                                    _3899 = 1.0;
                                    break;
                                }
                                D _3886 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, 1.0 - (_3864 * _3864))) * _3844;
                                _3866 = (_3886 * ((((_543 * _543) * 2.0) + (-1.0)) - (_3864 * _3845))) + (_3861 * _3845);
                                _3868 = (_3886 * (_543 - (_3864 * _3815))) + (_3861 * _3815);
                            }
                            else
                            {
                                _3866 = _3845;
                                _3868 = _3815;
                            }
                            D _3873 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3866 * 2.0) + 2.0));
                            _3898 = spvNMin(_3873 * (_3866 + 1.0), 1.0);
                            _3899 = spvNClamp(_3873 * (_3868 + _543), 0.0, 1.0);
                            break;
                        }
                        D _3900 = spvNMax(9.9999997473787516355514526367188e-06, _3898);
                        D _3909 = sqrt(spvNMax(0.0, 1.0 - ((1.0 - (_543 * _543)) * 0.444444477558135986328125)));
                        D _3913 = (_549 * 0.666666686534881591796875) - (_3909 * _428);
                        D _3914 = (_550 * 0.666666686534881591796875) - (_3909 * _429);
                        D _3915 = (_551 * 0.666666686534881591796875) - (_3909 * _430);
                        D _3919 = inversesqrt(dot(vec3(_3913, _3914, _3915), vec3(_3913, _3914, _3915)));
                        D _3926 = dot(vec3((-0.0) - (_3919 * _3913), (-0.0) - (_3919 * _3914), (-0.0) - (_3919 * _3915)), vec3(_2056, _2057, _2058));
                        D _3929 = _3840 * _3840;
                        D _3943 = ((_3899 * _3899) * (_3929 + (-1.0))) + 1.0;
                        D _3949 = (_3838 * 2.0) * _569;
                        D _3954 = 1.0 - _3900;
                        D _3955 = _3954 * _3954;
                        D _3957 = (_3955 * _3955) * _3954;
                        D _3961 = spvNMin(dot(vec3(_527, _528, _529), vec3(16.666667938232421875)), 1.0);
                        D _3974 = spvNMax(0.039999999105930328369140625, _647);
                        D _3987 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_3974 * _3838) + 0.02669160068035125732421875) / (_3838 + 0.4664950072765350341796875)) * exp2(((1.0 / _3974) * _3838) * log2(_3974)), 0.0, 1.0));
                        D _3988 = 1.0 - _3838;
                        D _3989 = _3988 * _3988;
                        D _4001 = ((_3989 * _3989) * _3988) * exp2(log2((exp2((_3974 * 4.7702999114990234375) * log2(_3838)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _3974);
                        D _4004 = (1.0 / _3987) * (1.0 - _3987);
                        D _4008 = (_4004 * _527) + 1.0;
                        D _4009 = (_4004 * _528) + 1.0;
                        D _4010 = (_4004 * _529) + 1.0;
                        D _4011 = _3987 - _4001;
                        D _4025 = spvNClamp(1.0 - dot(vec3(_4008 * ((_4011 * _527) + _4001), _4009 * ((_4011 * _528) + _4001), _4010 * ((_4011 * _529) + _4001)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                        D _4029 = ((((_3929 * 0.3183098733425140380859375) * _3838) * (1.0 / (_3943 * _3943))) * (_3848 ? ((1.0 / ((((_3844 * 0.25) * (_3844 + (_3840 * 3.0))) * (1.0 / _3900)) + _3929)) * _3929) : 1.0)) * (0.5 / ((_3840 * ((_569 + _3838) - _3949)) + _3949));
                        D _4030 = _3838 * 0.3183098733425140380859375;
                        D _4033 = ((_3926 * _3926) + 1.0) * 0.05968309938907623291015625;
                        D _4034 = spvNMin(1.0, _455);
                        D _4036 = (_455 + 1.0) - _4034;
                        D _4037 = _4036 * _4036;
                        D _4040 = 1.0 - ((_4037 * _4037) * _4036);
                        D _4041 = _4040 * _4040;
                        D _4046 = ((_4041 * _4041) * (_4040 * (_455 - _4034))) + _4034;
                        D _4049 = sqrt(spvNMax(0.0, 1.0 - _4046));
                        D _4053 = 1.0 - spvNClamp((_647 * 3.5) + (-0.5), 0.0, 1.0);
                        D _4054 = _4053 * _4053;
                        D _4064 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_678 * _4049) * spvNClamp(1.0 - ((_4054 * _4054) * _4053), 0.0, 1.0))) * _3838, 0.0, 1.0);
                        D _4069 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _4049)) * _3838, 0.0, 1.0);
                        D _4071 = spvNMin(_3811, _4064 * _4064);
                        D _4072 = spvNMin(_3811, _4069 * _4069);
                        D _4073 = spvNMin(_3811, _4046);
                        D _4077 = (_2687 * _1168) * _3230;
                        D _4078 = (_2687 * _1169) * _3232;
                        D _4079 = (_2687 * _1170) * _3234;
                        D _4080 = _3814 * _4077;
                        D _4084 = _3814 * _4078;
                        D _4088 = _3814 * _4079;
                        _3686 = ((((_4077 * _479) * _3814) * _4030) * _4025) * _4072;
                        _3688 = ((((_4078 * _480) * _3814) * _4030) * _4025) * _4072;
                        _3690 = ((((_4079 * _481) * _3814) * _4030) * _4025) * _4072;
                        _3692 = (((_4080 * spvNClamp(((_3961 - _527) * _3957) + _527, 0.0, 1.0)) * _4029) * _4008) * _4071;
                        _3694 = (((_4084 * _4029) * spvNClamp(((_3961 - _528) * _3957) + _528, 0.0, 1.0)) * _4009) * _4071;
                        _3696 = (((_4088 * _4029) * spvNClamp(((_3961 - _529) * _3957) + _529, 0.0, 1.0)) * _4010) * _4071;
                        _3698 = (_4080 * _4033) * _4073;
                        _3700 = (_4084 * _4033) * _4073;
                        _3702 = (_4088 * _4033) * _4073;
                        break;
                    }
                    else
                    {
                        _3686 = 0.0;
                        _3688 = 0.0;
                        _3690 = 0.0;
                        _3692 = 0.0;
                        _3694 = 0.0;
                        _3696 = 0.0;
                        _3698 = 0.0;
                        _3700 = 0.0;
                        _3702 = 0.0;
                        break;
                    }
                }
                frontier_phi_47_pred = _1154;
                frontier_phi_47_pred_1 = _3686 + _1144;
                frontier_phi_47_pred_2 = _3688 + _1145;
                frontier_phi_47_pred_3 = _3690 + _1146;
                frontier_phi_47_pred_4 = _3692 + _1147;
                frontier_phi_47_pred_5 = _3694 + _1148;
                frontier_phi_47_pred_6 = _3696 + _1149;
                frontier_phi_47_pred_7 = _3698 + _1150;
                frontier_phi_47_pred_8 = _3700 + _1151;
                frontier_phi_47_pred_9 = _3702 + _1152;
                frontier_phi_47_pred_10 = _1153;
                frontier_phi_47_pred_11 = _1155;
                frontier_phi_47_pred_12 = _1156;
                frontier_phi_47_pred_13 = _1157;
                frontier_phi_47_pred_14 = _1158;
            }
            else
            {
                D _1327 = _1163 - _232;
                D _1328 = _1164 - _233;
                D _1329 = _1165 - _234;
                D _1330 = dot(vec3(_1327, _1328, _1329), vec3(_1327, _1328, _1329));
                D _1334 = (_1166 * _1166) * _1330;
                D _1335 = _1334 * _1334;
                D _1336 = _1335 * _1335;
                D _1339 = spvNClamp(1.0 - (_1336 * _1336), 0.0, 1.0);
                D _1340 = _1339 * _1339;
                D _1341 = _1340 * _1340;
                D _1342 = _1341 * _1341;
                D _1647;
                D _1649;
                D _1651;
                D _1653;
                D _1655;
                D _1657;
                if (_1342 > 0.0)
                {
                    D _1639 = dot(vec3(_240, _241, _242), vec3(_428, _429, _430)) * 2.0;
                    D _1643 = _240 - (_1639 * _428);
                    D _1644 = _241 - (_1639 * _429);
                    D _1645 = _242 - (_1639 * _430);
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
                    D _3307;
                    if (_1186 == 0.0)
                    {
                        D _2692;
                        D _2693;
                        D _2694;
                        if (_1330 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2688 = inversesqrt(_1330);
                            _2692 = _2688 * _1327;
                            _2693 = _2688 * _1328;
                            _2694 = _2688 * _1329;
                        }
                        else
                        {
                            _2692 = 0.0;
                            _2693 = 0.0;
                            _2694 = 0.0;
                        }
                        D _2697 = 1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1330));
                        _3297 = _2697;
                        _3298 = (_1185 * _1185) * _2697;
                        _3299 = _2692;
                        _3300 = _2693;
                        _3301 = _2694;
                        _3302 = _2692;
                        _3303 = _2693;
                        _3304 = _2694;
                        _3305 = _2692;
                        _3306 = _2693;
                        _3307 = _2694;
                    }
                    else
                    {
                        D _2070 = _1186 * 0.5;
                        D _2071 = _2070 * _1172;
                        D _2072 = _2070 * _1173;
                        D _2073 = _2070 * _1174;
                        D _2074 = _1327 - _2071;
                        D _2075 = _1328 - _2072;
                        D _2076 = _1329 - _2073;
                        D _2077 = _2071 + _1327;
                        D _2078 = _2072 + _1328;
                        D _2079 = _2073 + _1329;
                        D _2087 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2074, _2075, _2076), vec3(_2074, _2075, _2076))));
                        D _2089 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2077, _2078, _2079), vec3(_2077, _2078, _2079))));
                        D _2090 = _2089 * _2087;
                        D _2106 = (1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(_2090, ((dot(vec3(_2074, _2075, _2076), vec3(_2077, _2078, _2079)) * 0.5) * _2090) + 0.5))) * _2090;
                        D _2108 = (_1172 * 2.0) * _2070;
                        D _2110 = (_1173 * 2.0) * _2070;
                        D _2112 = (_1174 * 2.0) * _2070;
                        D _2113 = dot(vec3(_2108, _2110, _2112), vec3(_2108, _2110, _2112));
                        D _2730;
                        D _2731;
                        D _2732;
                        if (_2113 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2700 = dot(vec3(_1643, _1644, _1645), vec3(_2108, _2110, _2112));
                            D _2716 = spvNClamp((1.0 / (_2113 - (_2700 * _2700))) * dot(vec3(_2074, _2075, _2076), vec3((_2700 * _1643) - _2108, (_2700 * _1644) - _2110, (_2700 * _1645) - _2112)), 0.0, 1.0);
                            D _2720 = (_2716 * _2108) + _2074;
                            D _2721 = (_2716 * _2110) + _2075;
                            D _2722 = (_2716 * _2112) + _2076;
                            D _2726 = inversesqrt(dot(vec3(_2720, _2721, _2722), vec3(_2720, _2721, _2722)));
                            _2730 = _2720 * _2726;
                            _2731 = _2721 * _2726;
                            _2732 = _2722 * _2726;
                        }
                        else
                        {
                            _2730 = _2074;
                            _2731 = _2075;
                            _2732 = _2076;
                        }
                        _3297 = _2106;
                        _3298 = (_1185 * _1185) * _2106;
                        _3299 = _2087 * _2074;
                        _3300 = _2087 * _2075;
                        _3301 = _2087 * _2076;
                        _3302 = _2089 * _2077;
                        _3303 = _2089 * _2078;
                        _3304 = _2089 * _2079;
                        _3305 = _2730;
                        _3306 = _2731;
                        _3307 = _2732;
                    }
                    D _3317 = _3298 + 1.0;
                    D _3322 = _3305 - _240;
                    D _3323 = _3306 - _241;
                    D _3324 = _3307 - _242;
                    D _3328 = inversesqrt(dot(vec3(_3322, _3323, _3324), vec3(_3322, _3323, _3324)));
                    D _3329 = _3328 * _3322;
                    D _3330 = _3328 * _3323;
                    D _3331 = _3328 * _3324;
                    D _3338 = spvNClamp(dot(vec3(_428, _429, _430), vec3(_3329, _3330, _3331)), 0.0, 1.0);
                    D _3339 = _647 * _647;
                    D _3345 = spvNClamp(((1.0 - _3339) * _1185) * sqrt(_3297), 0.0, 1.0);
                    D _3359 = exp2(log2(spvNClamp((((_3345 * 0.25) * (_3345 + (_3339 * 3.0))) * (1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_243, _245, _246), vec3(_3329, _3330, _3331))))) + (_3339 * _3339), 0.0, 1.0)) * 0.25);
                    D _3363 = spvNClamp(dot(vec3(_3299, _3300, _3301), vec3(_3302, _3303, _3304)), 0.0, 1.0);
                    D _3365 = _3359 * _3359;
                    D _3366 = _3365 * _3365;
                    D _3718;
                    if (_3363 < 1.0)
                    {
                        D _3709 = sqrt(spvNClamp((1.0 / (_3363 + 1.0)) * (1.0 - _3363), 0.0, 1.0));
                        _3718 = (1.0 / spvNClamp(((_3709 * 0.25) * (_3709 + (_3365 * 3.0))) + _3366, 0.0, 1.0)) * _3366;
                    }
                    else
                    {
                        _3718 = 1.0;
                    }
                    D _3722 = ((_3338 * _3338) * (_3366 + (-1.0))) + 1.0;
                    D _3725 = spvNMax(0.0, (((dot(vec3(_428, _429, _430), vec3(_3302, _3303, _3304)) + dot(vec3(_428, _429, _430), vec3(_3299, _3300, _3301))) * 0.5) + _3298) * (1.0 / (_3317 * _3317))) * 0.3183098733425140380859375;
                    D _3728 = ((_3725 * _3366) * _3718) * (1.0 / (_3722 * _3722));
                    D _3730 = (_1342 * _1168) * _3297;
                    D _3732 = (_1342 * _1169) * _3297;
                    D _3734 = (_1342 * _1170) * _3297;
                    _1647 = _3728 * _3730;
                    _1649 = _3728 * _3732;
                    _1651 = _3728 * _3734;
                    _1653 = _3725 * _3730;
                    _1655 = _3725 * _3732;
                    _1657 = _3725 * _3734;
                }
                else
                {
                    _1647 = 0.0;
                    _1649 = 0.0;
                    _1651 = 0.0;
                    _1653 = 0.0;
                    _1655 = 0.0;
                    _1657 = 0.0;
                }
                frontier_phi_47_pred = _1649 + _1154;
                frontier_phi_47_pred_1 = _1144;
                frontier_phi_47_pred_2 = _1145;
                frontier_phi_47_pred_3 = _1146;
                frontier_phi_47_pred_4 = _1147;
                frontier_phi_47_pred_5 = _1148;
                frontier_phi_47_pred_6 = _1149;
                frontier_phi_47_pred_7 = _1150;
                frontier_phi_47_pred_8 = _1151;
                frontier_phi_47_pred_9 = _1152;
                frontier_phi_47_pred_10 = _1647 + _1153;
                frontier_phi_47_pred_11 = _1651 + _1155;
                frontier_phi_47_pred_12 = _1653 + _1156;
                frontier_phi_47_pred_13 = _1655 + _1157;
                frontier_phi_47_pred_14 = _1657 + _1158;
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
    vec4 _882 = textureLod(sampler3D(TranslucentBasePass_TranslucencyLightingVolumeEnvironmentA, View_SharedBilinearClampedSampler), vec3((_232 - View._m0[180u].x) * View._m0[182u].x, (_233 - View._m0[180u].y) * View._m0[182u].y, (_234 - View._m0[180u].z) * View._m0[182u].z), 0.0);
    D _906;
    D _907;
    D _908;
    if (_375 < 1.0)
    {
        _906 = _352.x / ((_397 / _374) + 1.0);
        _907 = _352.y / ((_398 / _374) + 1.0);
        _908 = _352.z / ((_399 / _374) + 1.0);
    }
    else
    {
        _906 = 0.0;
        _907 = 0.0;
        _908 = 0.0;
    }
    D _925 = spvNClamp(_629, 0.0, 1.0);
    D _938 = _477 * _477;
    D _939 = _938 * _477;
    D _946 = ((_428 - _566) * _939) + _566;
    D _947 = ((_429 - _567) * _939) + _567;
    D _948 = ((_430 - _568) * _939) + _568;
    D _952 = inversesqrt(dot(vec3(_946, _947, _948), vec3(_946, _947, _948)));
    D _961 = 10.0 / spvNMax(9.9999997473787516355514526367188e-06, _938);
    D _990 = fma(_231, View._m0[2u].x, fma(_230, View._m0[1u].x, View._m0[0u].x * _229)) + View._m0[3u].x;
    D _994 = fma(_231, View._m0[2u].y, fma(_230, View._m0[1u].y, View._m0[0u].y * _229)) + View._m0[3u].y;
    D _998 = fma(_231, View._m0[2u].z, fma(_230, View._m0[1u].z, View._m0[0u].z * _229)) + View._m0[3u].z;
    D _1002 = fma(_231, View._m0[2u].w, fma(_230, View._m0[1u].w, View._m0[0u].w * _229)) + View._m0[3u].w;
    D _1009 = ((_946 * _104) * _952) + _229;
    D _1010 = ((_947 * _104) * _952) + _230;
    D _1011 = ((_948 * _104) * _952) + _231;
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
    uint _1127 = max(1u, min(uint(ceil((spvNClamp((1.0 / spvNMax(9.9999997473787516355514526367188e-05, sqrt((_1094 * _1094) + (_1095 * _1095)))) * sqrt((_1068 * _1068) + (_1069 * _1069)), 0.0, 1.0) * 8.0) + _267)), 8u));
    D _1132 = ((_1045 * 0.5) + 0.5) * TranslucentBasePass_2._m0[198u].x;
    D _1133 = (0.5 - (_1046 * 0.5)) * TranslucentBasePass_2._m0[198u].y;
    D _1136 = (TranslucentBasePass_2._m0[198u].x * 0.0625) * _1094;
    D _1139 = (TranslucentBasePass_2._m0[198u].y * (-0.0625)) * _1095;
    D _1140 = _1096 * 0.125;
    D _1142 = spvNMax(abs(_1096), _1050 - ((1.0 / (fma(_104, View._m0[38u].w, 0.0) + _1002)) * (fma(_104, View._m0[38u].z, 0.0) + _998))) * 0.125;
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
        D _1560 = 0.0;
        uint _1562 = 0u;
        D _1561;
        D _1564;
        bool _1587;
        for (;;)
        {
            _1564 = D(_1562);
            D _1565 = _1564 + _267;
            vec4 _1579 = texelFetch(TranslucentBasePass_HZBTexture, ivec2_(uvec2(uint(int(floor(((_1565 * _1136) + _1132) * _1104))), uint(int(floor(((_1565 * _1139) + _1133) * _1106))))), int(0u));
            D _1581 = _1579.x;
            _1561 = ((_1565 * _1140) + _1050) - _1581;
            _1587 = (abs(((-0.0) - _1142) - _1561) < _1142) && (_1581 != 0.0);
            if (_1587)
            {
                D _1996 = (_1562 == 0u) ? (_1561 - _1140) : _1560;
                D _2003 = abs(((_267 + (-1.0)) + _1564) + spvNClamp(_1996 / (_1996 - _1561), 0.0, 1.0));
                D _2008 = spvNMin(_2003 * 0.125, 1.0);
                frontier_phi_60 = 1.0 - (_2008 * _2008);
                frontier_phi_60_1 = (_2003 * _1140) + _1050;
                frontier_phi_60_2 = (_2003 * _1139) + _1133;
                frontier_phi_60_3 = (_2003 * _1136) + _1132;
                break;
            }
            else
            {
                uint _1563 = _1562 + 1u;
                if (_1563 < _1127)
                {
                    _1560 = _1561;
                    _1562 = _1563;
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
    D _1465;
    D _1467;
    D _1469;
    D _1471;
    if (_1316 > 0.0)
    {
        D _1466;
        D _1468;
        D _1470;
        D _2212;
        D _1458;
        bool _1464;
        for (;;)
        {
            D _1417 = ((View._m0[73u].x * _1314) + View._m0[73u].y) + (1.0 / ((View._m0[73u].z * _1314) - View._m0[73u].w));
            D _1441 = _1417 * _1324;
            D _1442 = _1417 * _1325;
            D _1453 = (_229 - View._m0[63u].x) - fma(_1417, View._m0[62u].x, fma(_1442, View._m0[61u].x, _1441 * View._m0[60u].x));
            D _1455 = (_230 - View._m0[63u].y) - fma(_1417, View._m0[62u].y, fma(_1442, View._m0[61u].y, _1441 * View._m0[60u].y));
            D _1457 = (_231 - View._m0[63u].z) - fma(_1417, View._m0[62u].z, fma(_1442, View._m0[61u].z, _1441 * View._m0[60u].z));
            _1458 = dot(vec3(_1453, _1455, _1457), vec3(_1453, _1455, _1457));
            _1464 = View._m0[175u].w != 0.0;
            if (_1464)
            {
                if (floatBitsToUint(View._m0[175u]).y == 0u)
                {
                    _1466 = 0.0;
                    _1468 = 0.0;
                    _1470 = 0.0;
                    _2212 = 0.0;
                    break;
                }
            }
            D _1854 = fma(_1314, View._m0[140u].w, fma(_1325, View._m0[139u].w, View._m0[138u].w * _1324)) + View._m0[141u].w;
            D _1855 = (fma(_1314, View._m0[140u].x, fma(_1325, View._m0[139u].x, View._m0[138u].x * _1324)) + View._m0[141u].x) / _1854;
            D _1856 = (fma(_1314, View._m0[140u].y, fma(_1325, View._m0[139u].y, View._m0[138u].y * _1324)) + View._m0[141u].y) / _1854;
            D _1873 = spvNClamp((abs((spvNMin(spvNMax(_1855, -1.0), 1.0) - _1324) * 0.5) * 5.0) + (-4.0), 0.0, 1.0);
            D _1874 = spvNClamp((abs((spvNMin(spvNMax(_1856, -1.0), 1.0) - _1325) * 0.5) * 5.0) + (-4.0), 0.0, 1.0);
            uvec2 _1927 = uvec2(textureSize(TranslucentBasePass_PrevSceneColor, int(0u)));
            vec4 _1948 = texelFetch(TranslucentBasePass_PrevSceneColor, ivec2_(uvec2(uint(min(int(uint(max(int(uint(int(D(int(_1927.x)) * ((TranslucentBasePass_2._m0[199u].x * spvNMin(spvNMax(_1855 - ((D(int(uint(_1855 > 0.0) - uint(_1855 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1855) + (-1.0))), -1.0), 1.0)) + TranslucentBasePass_2._m0[199u].z)))), int(uint(int(TranslucentBasePass_2._m0[200u].x)))))), int(uint(int(TranslucentBasePass_2._m0[200u].x + TranslucentBasePass_2._m0[200u].z)) + 4294967295u))), uint(min(int(uint(max(int(uint(int(D(int(_1927.y)) * ((TranslucentBasePass_2._m0[199u].y * spvNMin(spvNMax(_1856 - ((D(int(uint(_1856 > 0.0) - uint(_1856 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1856) + (-1.0))), -1.0), 1.0)) + TranslucentBasePass_2._m0[199u].w)))), int(uint(int(TranslucentBasePass_2._m0[200u].y)))))), int(uint(int(TranslucentBasePass_2._m0[200u].y + TranslucentBasePass_2._m0[200u].w)) + 4294967295u))))), int(0u));
            _1466 = View._m0[165u].x * spvNMin(_1948.x, 65504.0);
            _1468 = View._m0[165u].x * spvNMin(_1948.y, 65504.0);
            _1470 = View._m0[165u].x * spvNMin(_1948.z, 65504.0);
            _2212 = spvNMax(0.0, 1.0 - dot(vec2(_1873, _1874), vec2(_1873, _1874)));
            break;
        }
        _1465 = _1466;
        _1467 = _1468;
        _1469 = _1470;
        _1471 = (_2212 * _1316) * spvNClamp(1.0 / spvNMax(9.9999997473787516355514526367188e-06, (_938 * _938) * _1458), 0.0, 1.0);
    }
    else
    {
        _1465 = 0.0;
        _1467 = 0.0;
        _1469 = 0.0;
        _1471 = 0.0;
    }
    D _1505 = fma(_234, View._m0[14u].w, fma(_233, View._m0[13u].w, _232 * View._m0[12u].w)) + View._m0[15u].w;
    D _1510 = (((fma(_234, View._m0[14u].x, fma(_233, View._m0[13u].x, _232 * View._m0[12u].x)) + View._m0[15u].x) / _1505) * 0.5) + 0.5;
    D _1511 = 0.5 - (((fma(_234, View._m0[14u].y, fma(_233, View._m0[13u].y, _232 * View._m0[12u].y)) + View._m0[15u].y) / _1505) * 0.5);
    D _1540 = sqrt(((_230 * _230) + (_229 * _229)) + (_231 * _231));
    D _1558 = spvNMax(0.0, ((1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_229, _230, _231), vec3(View._m0[68u].xyz())))) * _1540) * View._m0[280u].w);
    D _1964;
    D _1966;
    D _1968;
    D _1970;
    D _1972;
    D _1974;
    if (_1540 < _1558)
    {
        _1964 = 0.0;
        _1966 = 0.0;
        _1968 = 0.0;
        _1970 = 1.0;
        _1972 = 1.0;
        _1974 = 1.0;
    }
    else
    {
        D _1982 = (1.0 / _1540) * _1558;
        uvec4 _1989 = floatBitsToUint(View._m0[220u]);
        uint _1990 = _1989.y;
        uint _1992 = (_1990 != 1u) ? 4294967295u : 0u;
        uint _2328;
        if (_1990 > 1u)
        {
            D _133[4];
            _133[0u] = 0.0;
            _133[1u] = 0.0;
            _133[2u] = 0.0;
            _133[3u] = 0.0;
            uint _3174 = 0u;
            bool _3180;
            for (;;)
            {
                _3180 = _3174 < floatBitsToUint(View._m0[220u]).y;
                if (_3180)
                {
                    uint _3601 = _3174 + 237u;
                    D _3613 = View._m0[_3601].x - View._m0[75u].x;
                    D _3614 = View._m0[_3601].y - View._m0[75u].y;
                    D _3615 = View._m0[_3601].z - View._m0[75u].z;
                    D _3616 = dot(vec3(_3613, _3614, _3615), vec3(_240, _241, _242));
                    D _3623 = dot(vec3(_3613, _3614, _3615), vec3(_3613, _3614, _3615)) - (View._m0[_3601].w * View._m0[_3601].w);
                    D _3625 = (_3616 * _3616) - _3623;
                    D _3743;
                    if ((_3623 < 0.0) && (!(_3625 < 0.0)))
                    {
                        D _3737 = sqrt(_3625);
                        _3743 = spvNMin(abs(_3737 + _3616), abs(_3616 - _3737));
                    }
                    else
                    {
                        _3743 = 0.0;
                    }
                    _133[_3174] = _3743;
                }
                uint _3175 = _3174 + 1u;
                if (_3175 == 4u)
                {
                    break;
                }
                else
                {
                    _3174 = _3175;
                    continue;
                }
            }
            D _3753 = (_267 * 0.99989998340606689453125) * dot(vec4(_133[0u], _133[1u], _133[2u], _133[3u]), vec4(1.0));
            uint frontier_phi_59_97_ladder;
            if (_133[0u] > _3753)
            {
                frontier_phi_59_97_ladder = 0u;
            }
            else
            {
                D _3821 = _133[1u] + _133[0u];
                uint frontier_phi_59_97_ladder_103_ladder;
                if (_3821 > _3753)
                {
                    frontier_phi_59_97_ladder_103_ladder = 1u;
                }
                else
                {
                    D _3851 = _3821 + _133[2u];
                    uint frontier_phi_59_97_ladder_103_ladder_109_ladder;
                    if (_3851 > _3753)
                    {
                        frontier_phi_59_97_ladder_103_ladder_109_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder;
                        if ((_3851 + _133[3u]) > _3753)
                        {
                            frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder = _1992;
                        }
                        frontier_phi_59_97_ladder_103_ladder_109_ladder = frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder;
                    }
                    frontier_phi_59_97_ladder_103_ladder = frontier_phi_59_97_ladder_103_ladder_109_ladder;
                }
                frontier_phi_59_97_ladder = frontier_phi_59_97_ladder_103_ladder;
            }
            _2328 = frontier_phi_59_97_ladder;
        }
        else
        {
            _2328 = _1992;
        }
        D frontier_phi_38_59_ladder;
        D frontier_phi_38_59_ladder_1;
        D frontier_phi_38_59_ladder_2;
        D frontier_phi_38_59_ladder_3;
        D frontier_phi_38_59_ladder_4;
        D frontier_phi_38_59_ladder_5;
        if (_2328 == 4294967295u)
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
            uint _3181 = _2328 + 221u;
            D _3189 = spvNMin(View._m0[_3181].w, 0.9900000095367431640625);
            uint _3190 = _2328 + 225u;
            uint _3197 = _2328 + 229u;
            uint _3204 = _2328 + 233u;
            uint _3209 = _2328 + 241u;
            D _3656;
            D _3657;
            D _3658;
            if (TranslucentBasePass_2._m0[146u].x > 0.0)
            {
                vec4 _3648 = textureLod(sampler2D(TranslucentBasePass_Shared_Fog_FarIntegratedScatteringTexture, View_SharedBilinearClampedSampler), vec2(spvNMin(spvNMax(View._m0[278u].x * _1510, View._m0[279u].x), View._m0[280u].x), spvNMin(spvNMax(View._m0[278u].y * _1511, View._m0[279u].y), View._m0[280u].y)), 0.0);
                _3656 = View._m0[164u].z * _3648.x;
                _3657 = View._m0[164u].z * _3648.y;
                _3658 = View._m0[164u].z * _3648.z;
            }
            else
            {
                _3656 = 0.0;
                _3657 = 0.0;
                _3658 = 0.0;
            }
            D _3662 = dot(vec3((-0.0) - View._m0[218u].x, (-0.0) - View._m0[218u].y, (-0.0) - View._m0[218u].z), vec3(_243, _245, _246));
            D _3675 = (((_3662 * _3662) + 1.0) * 0.0397887341678142547607421875) * exp2(log2(spvNMax(0.0, _3662 + 1.25)) * (-1.5));
            D _3755;
            if (View._m0[_3190].x == 0.0)
            {
                _3755 = 0.0;
            }
            else
            {
                D _3803 = (((_1982 * _231) - View._m0[_3190].z) + View._m0[75u].z) * View._m0[_3190].y;
                D _3804 = ((1.0 - _1982) * _231) * View._m0[_3190].y;
                D _3809 = exp2((-0.0) - _3803);
                D frontier_phi_98_99_ladder;
                if (abs(_3804) > 0.00999999977648258209228515625)
                {
                    frontier_phi_98_99_ladder = ((_3809 - exp2(((-0.0) - _3804) - _3803)) * View._m0[_3190].x) * (1.0 / _3804);
                }
                else
                {
                    frontier_phi_98_99_ladder = (View._m0[_3190].x * 0.693147182464599609375) * _3809;
                }
                _3755 = frontier_phi_98_99_ladder;
            }
            D _3759 = _3755 * (1.0 - _3189);
            D _3763 = (1.0 - View._m0[_3197].x) * View._m0[_3204].x;
            D _3764 = (1.0 - View._m0[_3197].y) * View._m0[_3204].x;
            D _3765 = (1.0 - View._m0[_3197].z) * View._m0[_3204].x;
            D _3766 = (-0.0) - (_1540 - _1558);
            D _3794 = 1.0 - spvNClamp(exp2(_3759 * _3766), 0.0, 1.0);
            frontier_phi_38_59_ladder = spvNClamp(exp2((_3759 + _3765) * _3766), 0.0, 1.0);
            frontier_phi_38_59_ladder_1 = spvNClamp(exp2((_3759 + _3764) * _3766), 0.0, 1.0);
            frontier_phi_38_59_ladder_2 = spvNClamp(exp2((_3759 + _3763) * _3766), 0.0, 1.0);
            frontier_phi_38_59_ladder_3 = (((_3189 * View._m0[_3181].z) * (((View._m0[219u].z * View._m0[_3209].x) * _3675) + _3658)) * spvNClamp(exp2(_3765 * _3766), 0.0, 1.0)) * _3794;
            frontier_phi_38_59_ladder_4 = (((_3189 * View._m0[_3181].y) * (((View._m0[219u].y * View._m0[_3209].x) * _3675) + _3657)) * spvNClamp(exp2(_3764 * _3766), 0.0, 1.0)) * _3794;
            frontier_phi_38_59_ladder_5 = (((_3189 * View._m0[_3181].x) * (((View._m0[219u].x * View._m0[_3209].x) * _3675) + _3656)) * spvNClamp(exp2(_3763 * _3766), 0.0, 1.0)) * _3794;
        }
        _1964 = frontier_phi_38_59_ladder_5;
        _1966 = frontier_phi_38_59_ladder_4;
        _1968 = frontier_phi_38_59_ladder_3;
        _1970 = frontier_phi_38_59_ladder_2;
        _1972 = frontier_phi_38_59_ladder_1;
        _1974 = frontier_phi_38_59_ladder;
    }
    D _2260;
    D _2261;
    D _2262;
    D _2263;
    D _2264;
    D _2265;
    if (TranslucentBasePass_2._m0[148u].x > 0.0)
    {
        D _2240 = spvNMin(spvNMax(View._m0[278u].x * _1510, View._m0[279u].x), View._m0[280u].x);
        D _2241 = spvNMin(spvNMax(View._m0[278u].y * _1511, View._m0[279u].y), View._m0[280u].y);
        D _2242 = spvNMin(spvNMax((View._m0[275u].z * spvNMax(0.0, spvNMin(View._m0[276u].z * log2((View._m0[276u].x * _1505) + View._m0[276u].y), View._m0[274u].z + (-1.0)) + 0.5)) * View._m0[278u].z, View._m0[279u].z), View._m0[280u].z);
        vec4 _2245 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeATexture, View_SharedBilinearClampedSampler), vec3(_2240, _2241, _2242), 0.0);
        vec4 _2252 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeBTexture, View_SharedBilinearClampedSampler), vec3(_2240, _2241, _2242), 0.0);
        _2260 = View._m0[164u].z * _2245.x;
        _2261 = View._m0[164u].z * _2245.y;
        _2262 = View._m0[164u].z * _2245.z;
        _2263 = _2252.x;
        _2264 = _2252.y;
        _2265 = _2252.z;
    }
    else
    {
        _2260 = 0.0;
        _2261 = 0.0;
        _2262 = 0.0;
        _2263 = 1.0;
        _2264 = 1.0;
        _2265 = 1.0;
    }
    D _2272 = (1.0 - _634) + (_634 * _453);
    D _2273 = (1.0 - _637) + (_637 * _453);
    D _2274 = (1.0 - _640) + (_640 * _453);
    SV_Target.x = View._m0[164u].y * ((((_2263 * _1964) + _2260) * _2272) + ((_1970 * (((((((((_479 * _455) * _705) * spvNMax(1.0, ((_534 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_534 * 4.79510021209716796875)) + (((_534 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _455)) * _455))) * _836) + _812) * _456) + _818) + ((((_906 * _602) * spvNClamp(1.0 - (_618 * _608), 0.0, 1.0)) * ((View._m0[164u].z * _882.x) + _824)) * _925)) + ((_719 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1465)) + 29.8973522186279296875) * _1471) + (-29.8973522186279296875)) + _830)) * spvNClamp(_697, 0.0, 1.0)))) * _2263));
    SV_Target.y = ((((_2264 * _1966) + _2261) * _2273) + ((_1972 * (((((((((_480 * _455) * _705) * spvNMax(1.0, ((_535 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_535 * 4.79510021209716796875)) + (((_535 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _455)) * _455))) * _838) + _814) * _456) + _820) + ((((_907 * _602) * spvNClamp(1.0 - (_619 * _608), 0.0, 1.0)) * ((View._m0[164u].z * _882.y) + _826)) * _925)) + ((_719 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1467)) + 29.8973522186279296875) * _1471) + (-29.8973522186279296875)) + _832)) * spvNClamp(_698, 0.0, 1.0)))) * _2264)) * View._m0[164u].y;
    SV_Target.z = ((((_2265 * _1968) + _2262) * _2274) + ((_1974 * (((((((((_481 * _455) * _705) * spvNMax(1.0, ((_536 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_536 * 4.79510021209716796875)) + (((_536 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _455)) * _455))) * _840) + _816) * _456) + _822) + ((((_908 * _602) * ((View._m0[164u].z * _882.z) + _828)) * spvNClamp(1.0 - (_620 * _608), 0.0, 1.0)) * _925)) + ((_719 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1469)) + 29.8973522186279296875) * _1471) + (-29.8973522186279296875)) + _834)) * spvNClamp(_699, 0.0, 1.0)))) * _2265)) * View._m0[164u].y;
    SV_Target.w = dot(vec3(_2272, _2273, _2274), vec3(0.2125999927520751953125, 0.715200006961822509765625, 0.072200000286102294921875));
    SV_Target_1.x = _2272;
    SV_Target_1.y = _2273;
    SV_Target_1.z = _2274;
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
} // namespace S_lass_Thin_Coverage_Wide_Character