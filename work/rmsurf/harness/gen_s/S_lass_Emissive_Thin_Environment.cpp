namespace S_lass_Emissive_Thin_Environment {
using namespace cpuglsl;
static D _4363;
static D _4359;
static D _4360;
static D _4361;
static UBO& View = ubo("View");
static UBO& Primitive = ubo("Primitive");
static UBOF& TranslucentBasePass = uboF("b0_2");
static UBO& TranslucentBasePass_2 = ubo("b0_2");
static UBO& Material = ubo("junk:b0_3");
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
static Tex2D Material_Texture2D_6{texid("junk:T_Emissive")};
static Tex2D Material_Texture2D_7{texid("junk:T_Opacity")};
static Tex2D Material_Texture2D_18{texid("junk:T_Muddiness")};
static Tex2D Material_Texture2D_19{texid("junk:T_Transparency")};
static Tex2D Material_Texture2D_20{texid("junk:T_TransparencyCoefficient")};
static Tex2D Material_Texture2D_21{texid("junk:T_Transmittance")};
static Tex2D Material_Texture2D_22{texid("junk:T_TransmittanceCoefficient")};
static Tex2D Material_Texture2D_24{texid("junk:T_Thinness")};
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










void discard_cond(bool _4349)
{
    if (_4349)
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
    D _108 = 1.0 / gl_FragCoord.w;
    D _227 = fma(gl_FragCoord.z, View._m0[54u].w, fma(gl_FragCoord.y, View._m0[53u].w, View._m0[52u].w * gl_FragCoord.x)) + View._m0[55u].w;
    D _228 = (fma(gl_FragCoord.z, View._m0[54u].x, fma(gl_FragCoord.y, View._m0[53u].x, View._m0[52u].x * gl_FragCoord.x)) + View._m0[55u].x) / _227;
    D _229 = (fma(gl_FragCoord.z, View._m0[54u].y, fma(gl_FragCoord.y, View._m0[53u].y, View._m0[52u].y * gl_FragCoord.x)) + View._m0[55u].y) / _227;
    D _230 = (fma(gl_FragCoord.z, View._m0[54u].z, fma(gl_FragCoord.y, View._m0[53u].z, View._m0[52u].z * gl_FragCoord.x)) + View._m0[55u].z) / _227;
    D _231 = _228 - View._m0[78u].x;
    D _232 = _229 - View._m0[78u].y;
    D _233 = _230 - View._m0[78u].z;
    D _238 = inversesqrt(dot(vec3(_228, _229, _230), vec3(_228, _229, _230)));
    D _239 = _238 * _228;
    D _240 = _238 * _229;
    D _241 = _238 * _230;
    D _242 = (-0.0) - _239;
    D _244 = (-0.0) - _240;
    D _245 = (-0.0) - _241;
    vec4 _263 = texelFetch(View_SpatiotemporalBlueNoiseVolumeTexture, ivec3_(uvec3(uint(int(gl_FragCoord.x)) & 127u, uint(int(gl_FragCoord.y)) & 127u, ((floatBitsToUint(View._m0[175u]).x & 7u) + uint(roundEven(CONSTANT_CONTEXT))) & 63u)), int(0u));
    D _266 = _263.x;
    D _267 = _263.y;
    vec4 _281 = texture(sampler2D(Material_Texture2D_0, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _289 = texture(sampler2D(Material_Texture2D_1, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _294 = texture(sampler2D(Material_Texture2D_2, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _301 = (_294.x * 2.0) + (-1.0);
    D _303 = (_294.y * 2.0) + (-1.0);
    D _309 = sqrt(spvNMax(0.0, 1.0 - dot(vec2(_301, _303), vec2(_301, _303))));
    D _313 = inversesqrt(dot(vec3(_301, _303, _309), vec3(_301, _303, _309)));
    D _314 = _313 * _301;
    D _315 = _313 * _303;
    D _316 = _313 * _309;
    vec4 _319 = texture(sampler2D(Material_Texture2D_3, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _324 = texture(sampler2D(Material_Texture2D_4, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _329 = texture(sampler2D(Material_Texture2D_6, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _336 = texture(sampler2D(Material_Texture2D_7, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _342 = vec4(g_R.Muddiness.x, g_R.Muddiness.y, g_R.Muddiness.z, 0.0);
    vec4 _349 = texture(sampler2D(Material_Texture2D_19, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _354 = texture(sampler2D(Material_Texture2D_20, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _364 = g_R.TransparencyLog2;
    D _365 = exp2(_364);
    vec4 _368 = texture(sampler2D(Material_Texture2D_21, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _375 = texture(sampler2D(Material_Texture2D_22, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _380 = 1.0 / spvNMax(9.9999999747524270787835121154785e-07, _375.x * 100.0);
    D _387 = g_R.TransmittanceLog2.x;
    D _388 = g_R.TransmittanceLog2.y;
    D _389 = g_R.TransmittanceLog2.z;
    vec4 _395 = vec4(g_R.Thickness);
    D _405;
    if (Material._m0[3u].w > 0.0)
    {
        _405 = View._m0[164u].z;
    }
    else
    {
        _405 = 1.0;
    }
    D _412 = inversesqrt(dot(vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z), vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z)));
    D _413 = _412 * g_R.Normal.x;
    D _414 = _412 * g_R.Normal.y;
    D _415 = _412 * g_R.Normal.z;
    D _418 = fma(_415, TEXCOORD_11.x, fma(_414, ((TEXCOORD_10.z * TEXCOORD_11.y) - (TEXCOORD_10.y * TEXCOORD_11.z)) * TEXCOORD_11.w, _413 * TEXCOORD_10.x));
    D _421 = fma(_415, TEXCOORD_11.y, fma(_414, ((TEXCOORD_10.x * TEXCOORD_11.z) - (TEXCOORD_10.z * TEXCOORD_11.x)) * TEXCOORD_11.w, _413 * TEXCOORD_10.y));
    D _424 = fma(_415, TEXCOORD_11.z, fma(_414, ((TEXCOORD_10.y * TEXCOORD_11.x) - (TEXCOORD_10.x * TEXCOORD_11.y)) * TEXCOORD_11.w, _413 * TEXCOORD_10.z));
    D _428 = inversesqrt(dot(vec3(_418, _421, _424), vec3(_418, _421, _424)));
    D _429 = _428 * _418;
    D _430 = _428 * _421;
    D _431 = _428 * _424;
    bool _444;
    if (Primitive._m0[27u].w > ((_263.w * 0.99609375) + 0.001953125))
    {
        _444 = ((_266 * 0.99609375) + 0.001953125) < 1.0;
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
    D _459 = spvNClamp(g_R.Opacity, 0.0, 1.0);
    D _461 = dFdxFine(_429);
    D _462 = dFdxFine(_430);
    D _463 = dFdxFine(_431);
    D _467 = dFdyFine(_429);
    D _468 = dFdyFine(_430);
    D _469 = dFdyFine(_431);
    D _480 = sqrt(spvNClamp(spvNMin((dot(vec3(_467, _468, _469), vec3(_467, _468, _469)) + dot(vec3(_461, _462, _463), vec3(_461, _462, _463))) * 0.15915493667125701904296875, 0.180000007152557373046875) + (_454 * _454), 0.0, 1.0));
    D _481 = 1.0 - _453;
    D _482 = _481 * _450;
    D _483 = _481 * _451;
    D _484 = _481 * _452;
    D _489 = _453 * (_450 + (-0.0400000028312206268310546875));
    D _490 = _453 * (_451 + (-0.0400000028312206268310546875));
    D _491 = _453 * (_452 + (-0.0400000028312206268310546875));
    D _492 = _489 + 0.0400000028312206268310546875;
    D _494 = _490 + 0.0400000028312206268310546875;
    D _495 = _491 + 0.0400000028312206268310546875;
    D _502 = spvNClamp(D(View._m0[220u].x > 1.0), 0.0, 1.0);
    D _530 = ((exp2(log2(spvNMax(0.0, _489 + 0.020000003278255462646484375) * 1.020408153533935546875) * 1.39999997615814208984375) - _492) * _502) + _492;
    D _531 = ((exp2(log2(spvNMax(0.0, _490 + 0.020000003278255462646484375) * 1.020408153533935546875) * 1.39999997615814208984375) - _494) * _502) + _494;
    D _532 = ((exp2(log2(spvNMax(0.0, _491 + 0.020000003278255462646484375) * 1.020408153533935546875) * 1.39999997615814208984375) - _495) * _502) + _495;
    D _537 = (_530 * 0.449999988079071044921875) + _482;
    D _538 = (_531 * 0.449999988079071044921875) + _483;
    D _539 = (_532 * 0.449999988079071044921875) + _484;
    D _546 = dot(vec3(_429, _430, _431), vec3(_242, _244, _245));
    D _552 = (_546 * _429) + _239;
    D _553 = (_546 * _430) + _240;
    D _554 = (_546 * _431) + _241;
    D _558 = abs(_546);
    D _562 = (_552 * 2.0) + (_558 * _429);
    D _563 = (_553 * 2.0) + (_558 * _430);
    D _564 = (_554 * 2.0) + (_558 * _431);
    D _568 = inversesqrt(dot(vec3(_562, _563, _564), vec3(_562, _563, _564)));
    D _569 = _562 * _568;
    D _570 = _563 * _568;
    D _571 = _564 * _568;
    D _572 = spvNMax(9.9999997473787516355514526367188e-06, _558);
    D _584 = 1.0 - _480;
    D _585 = 0.0425000004470348358154296875 - (_480 * 0.0274999998509883880615234375);
    D _587 = 1.03999996185302734375 - (_480 * 0.572000026702880859375);
    D _589 = (_480 * 0.02199999988079071044921875) + (-0.039999999105930328369140625);
    D _594 = _584 * _584;
    D _598 = ((spvNMin(_594, exp2(_572 * (-9.27999973297119140625))) * _584) + _585) * 1.03999996185302734375;
    D _604 = 1.0 - spvNClamp((_589 + _598) + ((_587 - _598) * 0.0400000028312206268310546875), 0.0, 1.0);
    D _605 = _604 * _604;
    D _606 = spvNMax(0.001000000047497451305389404296875, (1.0 / spvNMax(0.0333333350718021392822265625, _572)) * _395.x);
    D _609 = log2(spvNMax(0.0, _365));
    D _611 = exp2(_609 * _606);
    D _615 = log2(spvNMax(0.0, exp2(_387)));
    D _616 = log2(spvNMax(0.0, exp2(_388)));
    D _617 = log2(spvNMax(0.0, exp2(_389)));
    D _621 = exp2(_615 * _606);
    D _622 = exp2(_616 * _606);
    D _623 = exp2(_617 * _606);
    D _625 = exp2(_609 * 0.001000000047497451305389404296875);
    D _632 = 1.0 - _459;
    D _634 = (_605 * _632) * _611;
    D _637 = ((_634 * _621) * _625) * exp2(_615 * 0.001000000047497451305389404296875);
    D _640 = ((_634 * _622) * _625) * exp2(_616 * 0.001000000047497451305389404296875);
    D _643 = ((_634 * _623) * _625) * exp2(_617 * 0.001000000047497451305389404296875);
    D _650 = spvNMax(0.039999999105930328369140625, _480);
    D _666 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_650 * _572) + 0.02669160068035125732421875) / (_572 + 0.4664950072765350341796875)) * exp2(((1.0 / _650) * _572) * log2(_650)), 0.0, 1.0));
    D _667 = 1.0 - _572;
    D _668 = _667 * _667;
    D _681 = _668 * _668;
    D _683 = (_681 * _667) * exp2(log2((exp2((_650 * 4.7702999114990234375) * log2(_572)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _650);
    D _686 = (1.0 / _666) * (1.0 - _666);
    D _693 = _666 - _683;
    D _700 = ((_686 * _530) + 1.0) * ((_693 * _530) + _683);
    D _701 = ((_686 * _531) + 1.0) * ((_693 * _531) + _683);
    D _702 = ((_686 * _532) + 1.0) * ((_693 * _532) + _683);
    D _708 = spvNClamp(1.0 - dot(vec3(_700, _701, _702), vec3(0.3333333432674407958984375)), 0.0, 1.0);
    D _722 = spvNClamp((_455 + (-1.0)) + exp2(log2(_572 + _455) * exp2((-1.0) - (_480 * 16.0))), 0.0, 1.0);
    D _782;
    D _784;
    D _786;
    D _788;
    D _790;
    D _792;
    D _794;
    D _796;
    D _798;
    if (floatBitsToUint(TranslucentBasePass_2._m0[0u]).z == 0u)
    {
        _782 = 0.0;
        _784 = 0.0;
        _786 = 0.0;
        _788 = 0.0;
        _790 = 0.0;
        _792 = 0.0;
        _794 = 0.0;
        _796 = 0.0;
        _798 = 0.0;
    }
    else
    {
        D _1230;
        uint _813;
        bool _814;
        for (;;)
        {
            _813 = floatBitsToUint(TranslucentBasePass_2._m0[7u]).z;
            _814 = _813 == 0u;
            if (!_814)
            {
                uint _1395;
                uint _1298 = 0u;
                for (;;)
                {
                    if (_108 < TranslucentBasePass._m0[_1298 + 32u])
                    {
                        _1395 = _1298;
                        break;
                    }
                    else
                    {
                        uint _1299 = _1298 + 1u;
                        if (_1299 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                        {
                            _1298 = _1299;
                            continue;
                        }
                        else
                        {
                            _1395 = _813;
                            break;
                        }
                    }
                }
                if (_1395 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                {
                    uint _1746 = _1395 << 2u;
                    uint _1747 = _1746 + 9u;
                    uint _1754 = _1746 + 10u;
                    uint _1761 = _1746 + 11u;
                    uint _1768 = _1746 + 12u;
                    uint _1775 = _1395 + 25u;
                    D _1801 = fma(_233, TranslucentBasePass_2._m0[_1761].z, fma(_232, TranslucentBasePass_2._m0[_1754].z, TranslucentBasePass_2._m0[_1747].z * _231)) + TranslucentBasePass_2._m0[_1768].z;
                    D _1805 = fma(_233, TranslucentBasePass_2._m0[_1761].w, fma(_232, TranslucentBasePass_2._m0[_1754].w, TranslucentBasePass_2._m0[_1747].w * _231)) + TranslucentBasePass_2._m0[_1768].w;
                    D _1806 = (fma(_233, TranslucentBasePass_2._m0[_1761].x, fma(_232, TranslucentBasePass_2._m0[_1754].x, TranslucentBasePass_2._m0[_1747].x * _231)) + TranslucentBasePass_2._m0[_1768].x) / _1805;
                    D _1807 = (fma(_233, TranslucentBasePass_2._m0[_1761].y, fma(_232, TranslucentBasePass_2._m0[_1754].y, TranslucentBasePass_2._m0[_1747].y * _231)) + TranslucentBasePass_2._m0[_1768].y) / _1805;
                    bool _1814 = (_1807 <= TranslucentBasePass_2._m0[_1775].w) && ((_1806 <= TranslucentBasePass_2._m0[_1775].z) && ((_1806 >= TranslucentBasePass_2._m0[_1775].x) && (_1807 >= TranslucentBasePass_2._m0[_1775].y)));
                    D _1231;
                    if (_1814)
                    {
                        D _2171 = dFdyFine(_1806);
                        D _2172 = dFdyFine(_1807);
                        D _2173 = dFdyFine(_1801);
                        D _2174 = dFdxFine(_1806);
                        D _2175 = dFdxFine(_1807);
                        D _2176 = dFdxFine(_1801);
                        D _2179 = (_2175 * _2173) - (_2176 * _2172);
                        D _2182 = (_2176 * _2171) - (_2174 * _2173);
                        D _2185 = (_2174 * _2172) - (_2175 * _2171);
                        D _2195 = 1.0 / spvNMax(abs(_2185), sqrt(((_2182 * _2182) + (_2185 * _2185)) + (_2179 * _2179)) * 0.100000001490116119384765625);
                        D _2201 = D(int(uint(_2185 > 0.0) - uint(_2185 < 0.0)));
                        D _2202 = _2179 * TranslucentBasePass_2._m0[29u].z;
                        D _2204 = (_2202 * _2195) * _2201;
                        D _2205 = _2182 * TranslucentBasePass_2._m0[29u].w;
                        D _2207 = (_2205 * _2195) * _2201;
                        D _2829;
                        D _2831;
                        if (dot(vec2(_2179, _2182), vec2(_2179, _2182)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2829 = 0.0;
                            _2831 = 0.0;
                        }
                        else
                        {
                            D _3199 = (-0.0) - _2179;
                            D _3200 = (-0.0) - _2182;
                            D _3204 = inversesqrt(dot(vec2(_3199, _3200), vec2(_3199, _3200)));
                            _2829 = _3204 * _3199;
                            _2831 = _3204 * _3200;
                        }
                        D _2833 = _267 + (-0.5);
                        D _2838 = _266 + 0.5;
                        D _2841 = ((_2831 * _2833) + (_1806 * TranslucentBasePass_2._m0[29u].x)) + (_2829 * _2838);
                        D _2844 = ((_2829 * _2833) + (_1807 * TranslucentBasePass_2._m0[29u].y)) + (_2831 * _2838);
                        D _2845 = _2841 + (-0.5);
                        D _2846 = _2844 + (-0.5);
                        D _2847 = trunc(_2845);
                        D _2848 = trunc(_2846);
                        D _2849 = _2845 - _2847;
                        D _2850 = _2846 - _2848;
                        D _2851 = _2847 * TranslucentBasePass_2._m0[29u].z;
                        D _2852 = _2848 * TranslucentBasePass_2._m0[29u].w;
                        D _2855 = (_2847 + (-0.5)) - _2841;
                        D _2856 = (_2848 + (-0.5)) - _2844;
                        D _2857 = dot(vec2(_2855, _2856), vec2(_2204, _2207));
                        D _2860 = _2857 + _2207;
                        D _2863 = _2201 * (_2195 * (_2205 + _2202));
                        D _2864 = _2863 + _2857;
                        D _2865 = _2857 + _2204;
                        vec4 _2871 = textureGather((sampler2D(ShadowMaps[_1395 + 0u], View_SharedPointClampedSampler)), vec2(_2851, _2852));
                        D _2872 = _2871.x;
                        D _2873 = _2871.y;
                        D _2874 = _2871.z;
                        D _2875 = _2871.w;
                        D _2912 = 1.525902189314365386962890625e-05 - _1801;
                        D _2943 = (_2847 + 1.5) - _2841;
                        D _2944 = dot(vec2(_2943, _2856), vec2(_2204, _2207));
                        D _2947 = _2944 + _2207;
                        D _2948 = _2863 + _2944;
                        D _2949 = _2944 + _2204;
                        vec4 _2951 = textureGatherOffset((sampler2D(ShadowMaps[_1395 + 0u], View_SharedPointClampedSampler)), vec2(_2851, _2852), ivec2(2, 0));
                        D _2952 = _2951.x;
                        D _2953 = _2951.y;
                        D _2954 = _2951.z;
                        D _2955 = _2951.w;
                        D _3021 = (_2848 + 1.5) - _2844;
                        D _3022 = dot(vec2(_2855, _3021), vec2(_2204, _2207));
                        D _3025 = _3022 + _2207;
                        D _3026 = _2863 + _3022;
                        D _3027 = _3022 + _2204;
                        vec4 _3029 = textureGatherOffset((sampler2D(ShadowMaps[_1395 + 0u], View_SharedPointClampedSampler)), vec2(_2851, _2852), ivec2(0, 2));
                        D _3030 = _3029.x;
                        D _3031 = _3029.y;
                        D _3032 = _3029.z;
                        D _3033 = _3029.w;
                        D _3098 = dot(vec2(_2943, _3021), vec2(_2204, _2207));
                        D _3101 = _3098 + _2207;
                        D _3102 = _2863 + _3098;
                        D _3103 = _3098 + _2204;
                        vec4 _3105 = textureGatherOffset((sampler2D(ShadowMaps[_1395 + 0u], View_SharedPointClampedSampler)), vec2(_2851, _2852), ivec2(2));
                        D _3106 = _3105.x;
                        D _3107 = _3105.y;
                        D _3108 = _3105.z;
                        D _3109 = _3105.w;
                        D _3174 = 1.0 - _2849;
                        vec4 _3197 = vec4((((((_2875 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2912 + _2875) + (spvNMin(abs(_2857), 0.0) * D(int(uint(_2857 > 0.0) - uint(_2857 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3174) + ((_2874 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2912 + _2874) + (spvNMin(abs(_2865), 0.0) * D(int(uint(_2865 > 0.0) - uint(_2865 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2955 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2912 + _2955) + (spvNMin(abs(_2944), 0.0) * D(int(uint(_2944 > 0.0) - uint(_2944 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2954 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2912 + _2954) + (spvNMin(abs(_2949), 0.0) * D(int(uint(_2949 > 0.0) - uint(_2949 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2849), (((((_2872 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2912 + _2872) + (spvNMin(abs(_2860), 0.0) * D(int(uint(_2860 > 0.0) - uint(_2860 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3174) + ((_2873 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2912 + _2873) + (spvNMin(abs(_2864), 0.0) * D(int(uint(_2864 > 0.0) - uint(_2864 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2952 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2912 + _2952) + (spvNMin(abs(_2947), 0.0) * D(int(uint(_2947 > 0.0) - uint(_2947 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2953 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2912 + _2953) + (spvNMin(abs(_2948), 0.0) * D(int(uint(_2948 > 0.0) - uint(_2948 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2849), (((((_3033 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2912 + _3033) + (spvNMin(abs(_3022), 0.0) * D(int(uint(_3022 > 0.0) - uint(_3022 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3174) + ((_3032 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2912 + _3032) + (spvNMin(abs(_3027), 0.0) * D(int(uint(_3027 > 0.0) - uint(_3027 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3109 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2912 + _3109) + (spvNMin(abs(_3098), 0.0) * D(int(uint(_3098 > 0.0) - uint(_3098 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3108 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2912 + _3108) + (spvNMin(abs(_3103), 0.0) * D(int(uint(_3103 > 0.0) - uint(_3103 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2849), (((((_3030 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2912 + _3030) + (spvNMin(abs(_3025), 0.0) * D(int(uint(_3025 > 0.0) - uint(_3025 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3174) + ((_3031 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2912 + _3031) + (spvNMin(abs(_3026), 0.0) * D(int(uint(_3026 > 0.0) - uint(_3026 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3106 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2912 + _3106) + (spvNMin(abs(_3101), 0.0) * D(int(uint(_3101 > 0.0) - uint(_3101 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3107 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2912 + _3107) + (spvNMin(abs(_3102), 0.0) * D(int(uint(_3102 > 0.0) - uint(_3102 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2849));
                        _1231 = dot(_3197, vec4(1.0 - _2850, 1.0, 1.0, _2850)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        _1231 = 1.0;
                    }
                    if (_1814)
                    {
                        _1230 = _1231;
                        break;
                    }
                }
            }
            if (floatBitsToUint(TranslucentBasePass_2._m0[30u]).y == 0u)
            {
                _1230 = 1.0;
                break;
            }
            D _1271 = fma(_233, TranslucentBasePass_2._m0[35u].z, fma(_232, TranslucentBasePass_2._m0[34u].z, TranslucentBasePass_2._m0[33u].z * _231)) + TranslucentBasePass_2._m0[36u].z;
            D _1275 = fma(_233, TranslucentBasePass_2._m0[35u].w, fma(_232, TranslucentBasePass_2._m0[34u].w, TranslucentBasePass_2._m0[33u].w * _231)) + TranslucentBasePass_2._m0[36u].w;
            D _1276 = (fma(_233, TranslucentBasePass_2._m0[35u].x, fma(_232, TranslucentBasePass_2._m0[34u].x, TranslucentBasePass_2._m0[33u].x * _231)) + TranslucentBasePass_2._m0[36u].x) / _1275;
            D _1277 = (fma(_233, TranslucentBasePass_2._m0[35u].y, fma(_232, TranslucentBasePass_2._m0[34u].y, TranslucentBasePass_2._m0[33u].y * _231)) + TranslucentBasePass_2._m0[36u].y) / _1275;
            uvec4 _1281 = floatBitsToUint(TranslucentBasePass_2._m0[32u]);
            uint _1282 = _1281.x;
            uint _1283 = _1281.y;
            uint _1284 = _1281.z;
            uint _1289 = uint(int(floor(_1276)));
            uint _1290 = uint(int((-0.0) - floor(_1277)));
            if (!((int(_1290) < int(_1281.w)) && ((int(_1289) < int(_1284)) && ((int(_1289) >= int(_1282)) && (int(_1290) >= int(_1283))))))
            {
                _1230 = 1.0;
                break;
            }
            D _1358 = dFdyFine(_1276);
            D _1359 = dFdyFine(_1277);
            D _1360 = dFdyFine(_1271);
            D _1361 = dFdxFine(_1276);
            D _1362 = dFdxFine(_1277);
            D _1363 = dFdxFine(_1271);
            D _1366 = (_1362 * _1360) - (_1363 * _1359);
            D _1369 = (_1363 * _1358) - (_1361 * _1360);
            D _1372 = (_1361 * _1359) - (_1362 * _1358);
            D _1383 = 1.0 / spvNMax(abs(_1372), sqrt(((_1369 * _1369) + (_1372 * _1372)) + (_1366 * _1366)) * 0.100000001490116119384765625);
            D _1389 = D(int(uint(_1372 > 0.0) - uint(_1372 < 0.0)));
            D _1673;
            D _1675;
            if (dot(vec2(_1366, _1369), vec2(_1366, _1369)) < 1.0000000195414813782625560981111e-24)
            {
                _1673 = 0.0;
                _1675 = 0.0;
            }
            else
            {
                D _1739 = (-0.0) - _1366;
                D _1740 = (-0.0) - _1369;
                D _1744 = inversesqrt(dot(vec2(_1739, _1740), vec2(_1739, _1740)));
                _1673 = _1744 * _1739;
                _1675 = _1744 * _1740;
            }
            D _1681 = _267 + (-0.5);
            D _1689 = (((_1675 * _1681) + (_1673 * _266)) * 2.0) + (_1673 * 0.5);
            D _1690 = (((_1675 * _266) + (_1673 * _1681)) * 2.0) + (_1675 * 0.5);
            D _1696 = _1689 + (fract(_1276) * 256.0);
            D _1697 = _1690 + (fract(_1277) * 256.0);
            D _1710 = dot(vec2((floor(_1696) + 0.5) - _1696, (floor(_1697) + 0.5) - _1697), vec2(((_1366 * 256.0) * _1383) * _1389, ((_1369 * 256.0) * _1383) * _1389));
            D _1716 = (_1689 * 0.00390625) + _1276;
            D _1717 = (_1690 * 0.00390625) + _1277;
            uint _1729 = ((uint(int((-0.0) - floor(_1717))) - _1283) * (_1284 - _1282)) + (uint(int(floor(_1716))) - _1282);
            D _2143;
            D _2146;
            if ((texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowLoadedTileData, int(_1729 >> 5u)).x & (1u << (_1729 & 31u))) == 0u)
            {
                _2143 = 3.0000000054977557577780399428115e+38;
                _2146 = 0.0;
            }
            else
            {
                uvec4 _2168 = uvec4(texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileIndices, int(_1729)));
                uint _2169 = _2168.x;
                D frontier_phi_53_54_ladder;
                D frontier_phi_53_54_ladder_1;
                if (int(_2169) > int(4294967295u))
                {
                    uint _2815 = (uint(floor(fract(_1716) * 256.0)) + (_2169 << 16u)) + (uint(floor(fract(_1717) * 256.0)) << 8u);
                    uvec4 _2818 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileData, int(_2815 >> 1u));
                    uint _2819 = _2818.x;
                    D _2827 = D((((_2815 & 1u) == 0u) ? _2819 : (_2819 >> 16u)) & 65535u) * 1.525902189314365386962890625e-05;
                    D frontier_phi_53_54_ladder_75_ladder;
                    D frontier_phi_53_54_ladder_75_ladder_1;
                    if (_2827 != 1.0)
                    {
                        vec4 _3628 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthRanges, int(_2169));
                        D _3630 = _3628.y;
                        frontier_phi_53_54_ladder_75_ladder = 1.0 / _3630;
                        frontier_phi_53_54_ladder_75_ladder_1 = (_3630 * _2827) + _3628.x;
                    }
                    else
                    {
                        frontier_phi_53_54_ladder_75_ladder = 0.0;
                        frontier_phi_53_54_ladder_75_ladder_1 = 3.0000000054977557577780399428115e+38;
                    }
                    frontier_phi_53_54_ladder = frontier_phi_53_54_ladder_75_ladder;
                    frontier_phi_53_54_ladder_1 = frontier_phi_53_54_ladder_75_ladder_1;
                }
                else
                {
                    frontier_phi_53_54_ladder = 0.0;
                    frontier_phi_53_54_ladder_1 = 3.0000000054977557577780399428115e+38;
                }
                _2143 = frontier_phi_53_54_ladder_1;
                _2146 = frontier_phi_53_54_ladder;
            }
            _1230 = spvNClamp(((((1.525902189314365386962890625e-05 - _1271) + _2143) + (spvNMin(abs(_1710), _2146 * 10.0) * D(int(uint(_1710 > 0.0) - uint(_1710 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0);
            break;
        }
        D _1345;
        if ((floatBitsToUint(Primitive._m0[27u]).z & 2u) == 0u)
        {
            _1345 = 1.0;
        }
        else
        {
            _1345 = View._m0[188u].y;
        }
        uvec4 _1349 = floatBitsToUint(View._m0[220u]);
        uint _1350 = _1349.y;
        uint _1353 = (_1350 != 1u) ? 4294967295u : 0u;
        uint _1671;
        if (_1350 > 1u)
        {
            D _132[4];
            _132[0u] = 0.0;
            _132[1u] = 0.0;
            _132[2u] = 0.0;
            _132[3u] = 0.0;
            uint _2128 = 0u;
            bool _2134;
            for (;;)
            {
                _2134 = _2128 < floatBitsToUint(View._m0[220u]).y;
                if (_2134)
                {
                    uint _2766 = _2128 + 237u;
                    D _2780 = View._m0[_2766].x - View._m0[75u].x;
                    D _2781 = View._m0[_2766].y - View._m0[75u].y;
                    D _2782 = View._m0[_2766].z - View._m0[75u].z;
                    D _2783 = dot(vec3(_2780, _2781, _2782), vec3(_239, _240, _241));
                    D _2790 = dot(vec3(_2780, _2781, _2782), vec3(_2780, _2781, _2782)) - (View._m0[_2766].w * View._m0[_2766].w);
                    D _2792 = (_2783 * _2783) - _2790;
                    D _3404;
                    if ((_2790 < 0.0) && (!(_2792 < 0.0)))
                    {
                        D _3398 = sqrt(_2792);
                        _3404 = spvNMin(abs(_3398 + _2783), abs(_2783 - _3398));
                    }
                    else
                    {
                        _3404 = 0.0;
                    }
                    _132[_2128] = _3404;
                }
                uint _2129 = _2128 + 1u;
                if (_2129 == 4u)
                {
                    break;
                }
                else
                {
                    _2128 = _2129;
                    continue;
                }
            }
            D _3415 = (_266 * 0.99989998340606689453125) * dot(vec4(_132[0u], _132[1u], _132[2u], _132[3u]), vec4(1.0));
            uint frontier_phi_34_85_ladder;
            if (_132[0u] > _3415)
            {
                frontier_phi_34_85_ladder = 0u;
            }
            else
            {
                D _3766 = _132[1u] + _132[0u];
                uint frontier_phi_34_85_ladder_96_ladder;
                if (_3766 > _3415)
                {
                    frontier_phi_34_85_ladder_96_ladder = 1u;
                }
                else
                {
                    D _3850 = _3766 + _132[2u];
                    uint frontier_phi_34_85_ladder_96_ladder_104_ladder;
                    if (_3850 > _3415)
                    {
                        frontier_phi_34_85_ladder_96_ladder_104_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_34_85_ladder_96_ladder_104_ladder_110_ladder;
                        if ((_3850 + _132[3u]) > _3415)
                        {
                            frontier_phi_34_85_ladder_96_ladder_104_ladder_110_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_34_85_ladder_96_ladder_104_ladder_110_ladder = _1353;
                        }
                        frontier_phi_34_85_ladder_96_ladder_104_ladder = frontier_phi_34_85_ladder_96_ladder_104_ladder_110_ladder;
                    }
                    frontier_phi_34_85_ladder_96_ladder = frontier_phi_34_85_ladder_96_ladder_104_ladder;
                }
                frontier_phi_34_85_ladder = frontier_phi_34_85_ladder_96_ladder;
            }
            _1671 = frontier_phi_34_85_ladder;
        }
        else
        {
            _1671 = _1353;
        }
        D _2135;
        if (_1671 == 4294967295u)
        {
            _2135 = _1345;
        }
        else
        {
            _2135 = View._m0[_1671 + 241u].x * _1345;
        }
        D frontier_phi_5_51_ladder;
        D frontier_phi_5_51_ladder_1;
        D frontier_phi_5_51_ladder_2;
        D frontier_phi_5_51_ladder_3;
        D frontier_phi_5_51_ladder_4;
        D frontier_phi_5_51_ladder_5;
        D frontier_phi_5_51_ladder_6;
        D frontier_phi_5_51_ladder_7;
        D frontier_phi_5_51_ladder_8;
        if (_2135 > 0.0)
        {
            D _2799 = spvNClamp((TranslucentBasePass_2._m0[7u].x * _108) + TranslucentBasePass_2._m0[7u].y, 0.0, 1.0);
            D _2803 = ((_2799 * _2799) * (1.0 - _1230)) + _1230;
            D frontier_phi_5_51_ladder_74_ladder;
            D frontier_phi_5_51_ladder_74_ladder_1;
            D frontier_phi_5_51_ladder_74_ladder_2;
            D frontier_phi_5_51_ladder_74_ladder_3;
            D frontier_phi_5_51_ladder_74_ladder_4;
            D frontier_phi_5_51_ladder_74_ladder_5;
            D frontier_phi_5_51_ladder_74_ladder_6;
            D frontier_phi_5_51_ladder_74_ladder_7;
            D frontier_phi_5_51_ladder_74_ladder_8;
            if (_2803 > 0.0)
            {
                D _3417 = dot(vec3(_429, _430, _431), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3420 = spvNMax(0.0, _3417);
                D _3421 = dot(vec3(_242, _244, _245), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3427 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3421 * 2.0) + 2.0));
                D _3430 = spvNClamp(_3427 * (_546 + _3417), 0.0, 1.0);
                D _3445 = sqrt(spvNMax(0.0, 1.0 - ((1.0 - (_546 * _546)) * 0.444444477558135986328125)));
                D _3449 = (_552 * 0.666666686534881591796875) - (_3445 * _429);
                D _3450 = (_553 * 0.666666686534881591796875) - (_3445 * _430);
                D _3451 = (_554 * 0.666666686534881591796875) - (_3445 * _431);
                D _3455 = inversesqrt(dot(vec3(_3449, _3450, _3451), vec3(_3449, _3450, _3451)));
                D _3462 = dot(vec3((-0.0) - (_3455 * _3449), (-0.0) - (_3455 * _3450), (-0.0) - (_3455 * _3451)), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3465 = _650 * _650;
                D _3466 = _3465 * _3465;
                D _3470 = ((_3430 * _3430) * (_3466 + (-1.0))) + 1.0;
                D _3476 = (_3420 * 2.0) * _572;
                D _3481 = 1.0 - spvNMax(9.9999997473787516355514526367188e-06, spvNMin(_3427 * (_3421 + 1.0), 1.0));
                D _3482 = _3481 * _3481;
                D _3484 = (_3482 * _3482) * _3481;
                D _3489 = spvNMin(dot(vec3(_530, _531, _532), vec3(16.666667938232421875)), 1.0);
                D _3502 = spvNMax(0.039999999105930328369140625, _650);
                D _3515 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_3502 * _3420) + 0.02669160068035125732421875) / (_3420 + 0.4664950072765350341796875)) * exp2(((1.0 / _3502) * _3420) * log2(_3502)), 0.0, 1.0));
                D _3516 = 1.0 - _3420;
                D _3517 = _3516 * _3516;
                D _3529 = ((_3517 * _3517) * _3516) * exp2(log2((exp2((_3502 * 4.7702999114990234375) * log2(_3420)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _3502);
                D _3532 = (1.0 / _3515) * (1.0 - _3515);
                D _3536 = (_3532 * _530) + 1.0;
                D _3537 = (_3532 * _531) + 1.0;
                D _3538 = (_3532 * _532) + 1.0;
                D _3539 = _3515 - _3529;
                D _3553 = spvNClamp(1.0 - dot(vec3(_3536 * ((_3539 * _530) + _3529), _3537 * ((_3539 * _531) + _3529), _3538 * ((_3539 * _532) + _3529)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                D _3556 = (((_3466 * 0.3183098733425140380859375) * _3420) * (1.0 / (_3470 * _3470))) * (0.5 / ((_3465 * ((_572 + _3420) - _3476)) + _3476));
                D _3557 = _3420 * 0.3183098733425140380859375;
                D _3560 = ((_3462 * _3462) + 1.0) * 0.05968309938907623291015625;
                D _3562 = spvNMin(1.0, _455);
                D _3564 = (_455 + 1.0) - _3562;
                D _3565 = _3564 * _3564;
                D _3568 = 1.0 - ((_3565 * _3565) * _3564);
                D _3569 = _3568 * _3568;
                D _3574 = ((_3569 * _3569) * (_3568 * (_455 - _3562))) + _3562;
                D _3577 = sqrt(spvNMax(0.0, 1.0 - _3574));
                D _3582 = 1.0 - spvNClamp((_650 * 3.5) + (-0.5), 0.0, 1.0);
                D _3583 = _3582 * _3582;
                D _3593 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_681 * _3577) * spvNClamp(1.0 - ((_3583 * _3583) * _3582), 0.0, 1.0))) * _3420, 0.0, 1.0);
                D _3598 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _3577)) * _3420, 0.0, 1.0);
                D _3600 = spvNMin(_2803, _3593 * _3593);
                D _3601 = spvNMin(_2803, _3598 * _3598);
                D _3602 = spvNMin(_2803, _3574);
                D _3603 = _2135 * TranslucentBasePass_2._m0[4u].x;
                D _3604 = _2135 * TranslucentBasePass_2._m0[4u].y;
                D _3605 = _2135 * TranslucentBasePass_2._m0[4u].z;
                frontier_phi_5_51_ladder_74_ladder = (_3560 * _3605) * _3602;
                frontier_phi_5_51_ladder_74_ladder_1 = (((_3603 * _482) * _3557) * _3553) * _3601;
                frontier_phi_5_51_ladder_74_ladder_2 = (((_3604 * _483) * _3557) * _3553) * _3601;
                frontier_phi_5_51_ladder_74_ladder_3 = (((_3605 * _484) * _3557) * _3553) * _3601;
                frontier_phi_5_51_ladder_74_ladder_4 = (((_3556 * _3603) * spvNClamp(((_3489 - _530) * _3484) + _530, 0.0, 1.0)) * _3536) * _3600;
                frontier_phi_5_51_ladder_74_ladder_5 = (((_3556 * _3604) * spvNClamp(((_3489 - _531) * _3484) + _531, 0.0, 1.0)) * _3537) * _3600;
                frontier_phi_5_51_ladder_74_ladder_6 = (((_3556 * _3605) * spvNClamp(((_3489 - _532) * _3484) + _532, 0.0, 1.0)) * _3538) * _3600;
                frontier_phi_5_51_ladder_74_ladder_7 = (_3560 * _3603) * _3602;
                frontier_phi_5_51_ladder_74_ladder_8 = (_3560 * _3604) * _3602;
            }
            else
            {
                frontier_phi_5_51_ladder_74_ladder = 0.0;
                frontier_phi_5_51_ladder_74_ladder_1 = 0.0;
                frontier_phi_5_51_ladder_74_ladder_2 = 0.0;
                frontier_phi_5_51_ladder_74_ladder_3 = 0.0;
                frontier_phi_5_51_ladder_74_ladder_4 = 0.0;
                frontier_phi_5_51_ladder_74_ladder_5 = 0.0;
                frontier_phi_5_51_ladder_74_ladder_6 = 0.0;
                frontier_phi_5_51_ladder_74_ladder_7 = 0.0;
                frontier_phi_5_51_ladder_74_ladder_8 = 0.0;
            }
            frontier_phi_5_51_ladder = frontier_phi_5_51_ladder_74_ladder;
            frontier_phi_5_51_ladder_1 = frontier_phi_5_51_ladder_74_ladder_1;
            frontier_phi_5_51_ladder_2 = frontier_phi_5_51_ladder_74_ladder_2;
            frontier_phi_5_51_ladder_3 = frontier_phi_5_51_ladder_74_ladder_3;
            frontier_phi_5_51_ladder_4 = frontier_phi_5_51_ladder_74_ladder_4;
            frontier_phi_5_51_ladder_5 = frontier_phi_5_51_ladder_74_ladder_5;
            frontier_phi_5_51_ladder_6 = frontier_phi_5_51_ladder_74_ladder_6;
            frontier_phi_5_51_ladder_7 = frontier_phi_5_51_ladder_74_ladder_7;
            frontier_phi_5_51_ladder_8 = frontier_phi_5_51_ladder_74_ladder_8;
        }
        else
        {
            frontier_phi_5_51_ladder = 0.0;
            frontier_phi_5_51_ladder_1 = 0.0;
            frontier_phi_5_51_ladder_2 = 0.0;
            frontier_phi_5_51_ladder_3 = 0.0;
            frontier_phi_5_51_ladder_4 = 0.0;
            frontier_phi_5_51_ladder_5 = 0.0;
            frontier_phi_5_51_ladder_6 = 0.0;
            frontier_phi_5_51_ladder_7 = 0.0;
            frontier_phi_5_51_ladder_8 = 0.0;
        }
        _782 = frontier_phi_5_51_ladder_1;
        _784 = frontier_phi_5_51_ladder_2;
        _786 = frontier_phi_5_51_ladder_3;
        _788 = frontier_phi_5_51_ladder_4;
        _790 = frontier_phi_5_51_ladder_5;
        _792 = frontier_phi_5_51_ladder_6;
        _794 = frontier_phi_5_51_ladder_7;
        _796 = frontier_phi_5_51_ladder_8;
        _798 = frontier_phi_5_51_ladder;
    }
    uvec4 _802 = floatBitsToUint(TranslucentBasePass_2._m0[0u]);
    uint _803 = _802.x;
    uint _808 = min(min(texelFetch(TranslucentBasePass_Shared_Forward_NumCulledLightsGrid, int(0u)).x, _803), _803);
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
    D _843;
    if (_808 == 0u)
    {
        _815 = _782;
        _817 = _784;
        _819 = _786;
        _821 = _788;
        _823 = _790;
        _825 = _792;
        _827 = _794;
        _829 = _796;
        _831 = _798;
        _833 = 0.0;
        _835 = 0.0;
        _837 = 0.0;
        _839 = 0.0;
        _841 = 0.0;
        _843 = 0.0;
    }
    else
    {
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
        D _842;
        D _844;
        D _1146 = _782;
        D _1147 = _784;
        D _1148 = _786;
        D _1149 = _788;
        D _1150 = _790;
        D _1151 = _792;
        D _1152 = _794;
        D _1153 = _796;
        D _1154 = _798;
        D _1155 = 0.0;
        D _1156 = 0.0;
        D _1157 = 0.0;
        D _1158 = 0.0;
        D _1159 = 0.0;
        D _1160 = 0.0;
        uint _1161 = 0u;
        D _1165;
        D _1166;
        D _1167;
        D _1168;
        D _1170;
        D _1171;
        D _1172;
        D _1174;
        D _1175;
        D _1176;
        uint _1178;
        D _1180;
        D _1181;
        D _1183;
        D _1184;
        D _1185;
        D _1187;
        D _1188;
        uint _1190;
        D _1192;
        D _1193;
        D _1194;
        D _1195;
        uint _1198;
        D _1200;
        D _1201;
        D _1202;
        D _1203;
        D _1206;
        D _1207;
        D _1208;
        D _1209;
        D _1212;
        D _1213;
        D _1214;
        D _1215;
        D _1218;
        D _1219;
        D _1220;
        D _1221;
        bool _1224;
        bool _1225;
        bool _1229;
        for (;;)
        {
            vec4 _1164 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(0u));
            _1165 = _1164.x;
            _1166 = _1164.y;
            _1167 = _1164.z;
            _1168 = _1164.w;
            vec4 _1169 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(1u));
            _1170 = _1169.x;
            _1171 = _1169.y;
            _1172 = _1169.z;
            vec4 _1173 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(2u));
            _1174 = _1173.x;
            _1175 = _1173.y;
            _1176 = _1173.z;
            _1178 = floatBitsToUint(_1173.w);
            vec4 _1179 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(3u));
            _1180 = _1179.x;
            _1181 = _1179.y;
            vec4 _1182 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(4u));
            _1183 = _1182.x;
            _1184 = _1182.y;
            _1185 = _1182.z;
            vec4 _1186 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(5u));
            _1187 = _1186.x;
            _1188 = _1186.y;
            _1190 = floatBitsToUint(_1186.z);
            vec4 _1191 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(6u));
            _1192 = _1191.x;
            _1193 = _1191.y;
            _1194 = _1191.z;
            _1195 = _1191.w;
            _1198 = floatBitsToUint(texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(7u)).x);
            vec4 _1199 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(8u));
            _1200 = _1199.x;
            _1201 = _1199.y;
            _1202 = _1199.z;
            _1203 = _1199.w;
            vec4 _1205 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(9u));
            _1206 = _1205.x;
            _1207 = _1205.y;
            _1208 = _1205.z;
            _1209 = _1205.w;
            vec4 _1211 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(10u));
            _1212 = _1211.x;
            _1213 = _1211.y;
            _1214 = _1211.z;
            _1215 = _1211.w;
            vec4 _1217 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(11u));
            _1218 = _1217.x;
            _1219 = _1217.y;
            _1220 = _1217.z;
            _1221 = _1217.w;
            _1224 = (_1178 & 131072u) != 0u;
            _1225 = _1180 > (-2.0);
            _1229 = (_1178 & 16384u) == 0u;
            D frontier_phi_49_pred;
            D frontier_phi_49_pred_1;
            D frontier_phi_49_pred_2;
            D frontier_phi_49_pred_3;
            D frontier_phi_49_pred_4;
            D frontier_phi_49_pred_5;
            D frontier_phi_49_pred_6;
            D frontier_phi_49_pred_7;
            D frontier_phi_49_pred_8;
            D frontier_phi_49_pred_9;
            D frontier_phi_49_pred_10;
            D frontier_phi_49_pred_11;
            D frontier_phi_49_pred_12;
            D frontier_phi_49_pred_13;
            D frontier_phi_49_pred_14;
            if (_1229)
            {
                D _1624;
                if (_1224)
                {
                    uint _1589 = _1198 + 0u;
                    uvec2 _1592 = uvec2(textureSize(ShadowMaps[(_1589)], int(0u)));
                    D _1594 = D(int(_1592.x));
                    D _1596 = D(int(_1592.y));
                    D _1597 = 1.0 / _1594;
                    D _1598 = 1.0 / _1596;
                    D _1610 = fma(_233, _1214, fma(_232, _1208, _1202 * _231)) + _1220;
                    D _1614 = fma(_233, _1215, fma(_232, _1209, _1203 * _231)) + _1221;
                    D _1615 = (fma(_233, _1212, fma(_232, _1206, _1200 * _231)) + _1218) / _1614;
                    D _1616 = (fma(_233, _1213, fma(_232, _1207, _1201 * _231)) + _1219) / _1614;
                    D frontier_phi_30_29_ladder;
                    if ((_1616 <= _1195) && ((_1615 <= _1194) && ((_1615 >= _1192) && (_1616 >= _1193))))
                    {
                        D _2012 = dFdyFine(_1615);
                        D _2013 = dFdyFine(_1616);
                        D _2014 = dFdyFine(_1610);
                        D _2015 = dFdxFine(_1615);
                        D _2016 = dFdxFine(_1616);
                        D _2017 = dFdxFine(_1610);
                        D _2020 = (_2016 * _2014) - (_2017 * _2013);
                        D _2023 = (_2017 * _2012) - (_2015 * _2014);
                        D _2026 = (_2015 * _2013) - (_2016 * _2012);
                        D _2036 = 1.0 / spvNMax(abs(_2026), sqrt(((_2023 * _2023) + (_2026 * _2026)) + (_2020 * _2020)) * 0.100000001490116119384765625);
                        D _2042 = D(int(uint(_2026 > 0.0) - uint(_2026 < 0.0)));
                        D _2043 = _2020 * _1597;
                        D _2045 = (_2043 * _2036) * _2042;
                        D _2046 = _2023 * _1598;
                        D _2048 = (_2046 * _2036) * _2042;
                        D _2361;
                        D _2363;
                        if (dot(vec2(_2020, _2023), vec2(_2020, _2023)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2361 = 0.0;
                            _2363 = 0.0;
                        }
                        else
                        {
                            D _2704 = (-0.0) - _2020;
                            D _2705 = (-0.0) - _2023;
                            D _2709 = inversesqrt(dot(vec2(_2704, _2705), vec2(_2704, _2705)));
                            _2361 = _2709 * _2704;
                            _2363 = _2709 * _2705;
                        }
                        D _2365 = _267 + (-0.5);
                        D _2370 = _266 + 0.5;
                        D _2373 = ((_2363 * _2365) + (_1615 * _1594)) + (_2361 * _2370);
                        D _2376 = ((_2361 * _2365) + (_1616 * _1596)) + (_2363 * _2370);
                        D _2377 = _2373 + (-0.5);
                        D _2378 = _2376 + (-0.5);
                        D _2379 = trunc(_2377);
                        D _2380 = trunc(_2378);
                        D _2381 = _2377 - _2379;
                        D _2382 = _2378 - _2380;
                        D _2383 = _2379 * _1597;
                        D _2384 = _2380 * _1598;
                        D _2387 = (_2379 + (-0.5)) - _2373;
                        D _2388 = (_2380 + (-0.5)) - _2376;
                        D _2389 = dot(vec2(_2387, _2388), vec2(_2045, _2048));
                        D _2392 = _2389 + _2048;
                        D _2395 = _2042 * (_2036 * (_2046 + _2043));
                        D _2396 = _2395 + _2389;
                        D _2397 = _2389 + _2045;
                        vec4 _2401 = textureGather((sampler2D(ShadowMaps[_1589], View_SharedPointClampedSampler)), vec2(_2383, _2384));
                        D _2442 = 1.525902189314365386962890625e-05 - _1610;
                        D _2465 = (_2379 + 1.5) - _2373;
                        D _2466 = dot(vec2(_2465, _2388), vec2(_2045, _2048));
                        D _2469 = _2466 + _2048;
                        D _2470 = _2395 + _2466;
                        D _2471 = _2466 + _2045;
                        vec4 _2475 = textureGatherOffset((sampler2D(ShadowMaps[_1589], View_SharedPointClampedSampler)), vec2(_2383, _2384), ivec2(2, 0));
                        D _2539 = (_2380 + 1.5) - _2376;
                        D _2540 = dot(vec2(_2387, _2539), vec2(_2045, _2048));
                        D _2543 = _2540 + _2048;
                        D _2544 = _2395 + _2540;
                        D _2545 = _2540 + _2045;
                        vec4 _2547 = textureGatherOffset((sampler2D(ShadowMaps[_1589], View_SharedPointClampedSampler)), vec2(_2383, _2384), ivec2(0, 2));
                        D _2609 = dot(vec2(_2465, _2539), vec2(_2045, _2048));
                        D _2612 = _2609 + _2048;
                        D _2613 = _2395 + _2609;
                        D _2614 = _2609 + _2045;
                        vec4 _2616 = textureGatherOffset((sampler2D(ShadowMaps[_1589], View_SharedPointClampedSampler)), vec2(_2383, _2384), ivec2(2));
                        D _2678 = 1.0 - _2381;
                        vec4 _2701 = vec4((((spvNClamp((((_2442 + _2401.w) + (spvNMin(abs(_2389), 0.0) * D(int(uint(_2389 > 0.0) - uint(_2389 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2678) + spvNClamp((((_2442 + _2401.z) + (spvNMin(abs(_2397), 0.0) * D(int(uint(_2397 > 0.0) - uint(_2397 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2442 + _2475.w) + (spvNMin(abs(_2466), 0.0) * D(int(uint(_2466 > 0.0) - uint(_2466 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2442 + _2475.z) + (spvNMin(abs(_2471), 0.0) * D(int(uint(_2471 > 0.0) - uint(_2471 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2381), (((spvNClamp((((_2442 + _2401.x) + (spvNMin(abs(_2392), 0.0) * D(int(uint(_2392 > 0.0) - uint(_2392 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2678) + spvNClamp((((_2442 + _2401.y) + (spvNMin(abs(_2396), 0.0) * D(int(uint(_2396 > 0.0) - uint(_2396 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2442 + _2475.x) + (spvNMin(abs(_2469), 0.0) * D(int(uint(_2469 > 0.0) - uint(_2469 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2442 + _2475.y) + (spvNMin(abs(_2470), 0.0) * D(int(uint(_2470 > 0.0) - uint(_2470 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2381), (((spvNClamp((((_2442 + _2547.w) + (spvNMin(abs(_2540), 0.0) * D(int(uint(_2540 > 0.0) - uint(_2540 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2678) + spvNClamp((((_2442 + _2547.z) + (spvNMin(abs(_2545), 0.0) * D(int(uint(_2545 > 0.0) - uint(_2545 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2442 + _2616.w) + (spvNMin(abs(_2609), 0.0) * D(int(uint(_2609 > 0.0) - uint(_2609 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2442 + _2616.z) + (spvNMin(abs(_2614), 0.0) * D(int(uint(_2614 > 0.0) - uint(_2614 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2381), (((spvNClamp((((_2442 + _2547.x) + (spvNMin(abs(_2543), 0.0) * D(int(uint(_2543 > 0.0) - uint(_2543 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2678) + spvNClamp((((_2442 + _2547.y) + (spvNMin(abs(_2544), 0.0) * D(int(uint(_2544 > 0.0) - uint(_2544 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2442 + _2616.x) + (spvNMin(abs(_2612), 0.0) * D(int(uint(_2612 > 0.0) - uint(_2612 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2442 + _2616.y) + (spvNMin(abs(_2613), 0.0) * D(int(uint(_2613 > 0.0) - uint(_2613 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2381));
                        frontier_phi_30_29_ladder = dot(_2701, vec4(1.0 - _2382, 1.0, 1.0, _2382)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        frontier_phi_30_29_ladder = 1.0;
                    }
                    _1624 = frontier_phi_30_29_ladder;
                }
                else
                {
                    _1624 = 1.0;
                }
                D _1630 = _1165 - _231;
                D _1631 = _1166 - _232;
                D _1632 = _1167 - _233;
                D _1633 = dot(vec3(_1630, _1631, _1632), vec3(_1630, _1631, _1632));
                D _2057;
                D _2058;
                D _2059;
                if (_1633 > 9.9999997473787516355514526367188e-05)
                {
                    D _2053 = inversesqrt(_1633);
                    _2057 = _2053 * _1630;
                    _2058 = _2053 * _1631;
                    _2059 = _2053 * _1632;
                }
                else
                {
                    _2057 = 0.0;
                    _2058 = 0.0;
                    _2059 = 0.0;
                }
                D _2060 = _1187 * _1187;
                D _2064 = (_1168 * _1168) * _1633;
                D _2067 = spvNClamp(1.0 - (_2064 * _2064), 0.0, 1.0);
                D _2717;
                if (_1225)
                {
                    D _2715 = spvNClamp((dot(vec3(_2057, _2058, _2059), vec3(_1174, _1175, _1176)) - _1180) * _1181, 0.0, 1.0);
                    _2717 = _2715 * _2715;
                }
                else
                {
                    _2717 = 1.0;
                }
                D _2718 = ((_2067 * _2067) * D(_1633 >= _2060)) * _2717;
                D _3261;
                D _3263;
                D _3265;
                if ((_1178 & 262144u) == 0u)
                {
                    _3261 = 1.0;
                    _3263 = 1.0;
                    _3265 = 1.0;
                }
                else
                {
                    D _3268 = (-0.0) - _1175;
                    D _3269 = (-0.0) - _1176;
                    D _3270 = (-0.0) - _1174;
                    D _3280 = (-0.0) - _2057;
                    D _3281 = (-0.0) - _2058;
                    D _3282 = (-0.0) - _2059;
                    D _3285 = fma(_3269, _3282, fma(_3268, _3281, _2057 * _1174));
                    D _3288 = fma(_1185, _3282, fma(_1184, _3281, _1183 * _3280));
                    D _3296 = atan(((-0.0) - _3288) / ((-0.0) - _3285));
                    bool _3301 = _3285 > (-0.0);
                    bool _3302 = _3285 == (-0.0);
                    bool _3303 = _3288 <= (-0.0);
                    bool _3304 = _3288 > (-0.0);
                    vec4 _3326 = texture((sampler2D(ForwardLightProfileTextures[_1190 + 0u], View_SharedBilinearWrappedSampler)), vec2(fract((_3302 && _3303) ? 1.25 : ((_3302 && _3304) ? 0.75 : ((((_3301 && _3304) ? (_3296 + (-3.1415927410125732421875)) : ((_3301 && _3303) ? (_3296 + 3.1415927410125732421875) : _3296)) * 0.15915493667125701904296875) + 1.0))), (asin((-0.0) - fma((_1184 * _3270) - (_1183 * _3268), _3282, fma((_1183 * _3269) - (_1185 * _3270), _3281, ((_1185 * _3268) - (_1184 * _3269)) * _3280))) * 0.3183098733425140380859375) + 0.5));
                    _3261 = _3326.x;
                    _3263 = _3326.y;
                    _3265 = _3326.z;
                }
                D _3717;
                D _3719;
                D _3721;
                D _3723;
                D _3725;
                D _3727;
                D _3729;
                D _3731;
                D _3733;
                for (;;)
                {
                    if (_2718 > 0.0)
                    {
                        D _3842;
                        if (_1224)
                        {
                            if (!(_1624 > 0.0))
                            {
                                _3717 = 0.0;
                                _3719 = 0.0;
                                _3721 = 0.0;
                                _3723 = 0.0;
                                _3725 = 0.0;
                                _3727 = 0.0;
                                _3729 = 0.0;
                                _3731 = 0.0;
                                _3733 = 0.0;
                                break;
                            }
                            _3842 = _1624;
                        }
                        else
                        {
                            _3842 = 1.0;
                        }
                        D _3844 = spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1633));
                        D _3845 = 1.0 / _3844;
                        D _3846 = dot(vec3(_429, _430, _431), vec3(_2057, _2058, _2059));
                        D _3867;
                        if (_1187 > 0.0)
                        {
                            D _3864 = sqrt(spvNClamp(_2060 * _3845, 0.0, 1.0));
                            D frontier_phi_109_108_ladder;
                            if (_3864 > spvNMax(9.9999997473787516355514526367188e-06, _3846))
                            {
                                D _3886 = spvNMax((-0.0) - _3864, _3846) + _3864;
                                frontier_phi_109_108_ladder = (_3886 * _3886) * (0.25 / _3864);
                            }
                            else
                            {
                                frontier_phi_109_108_ladder = _3846;
                            }
                            _3867 = frontier_phi_109_108_ladder;
                        }
                        else
                        {
                            _3867 = _3846;
                        }
                        D _3929;
                        D _3930;
                        D _3869;
                        D _3871;
                        D _3875;
                        D _3876;
                        bool _3879;
                        for (;;)
                        {
                            _3869 = spvNMax(0.0, _3867);
                            _3871 = _650 * _650;
                            _3875 = spvNClamp(((1.0 - _3871) * _1187) * inversesqrt(_3844), 0.0, 1.0);
                            _3876 = dot(vec3(_242, _244, _245), vec3(_2057, _2058, _2059));
                            _3879 = _3875 > 0.0;
                            D _3897;
                            D _3899;
                            if (_3879)
                            {
                                D _3892 = sqrt(spvNMax(0.0, 1.0 - (_3875 * _3875)));
                                D _3895 = ((_3846 * 2.0) * _546) - _3876;
                                if (!(!(_3895 >= _3892)))
                                {
                                    _3929 = _558;
                                    _3930 = 1.0;
                                    break;
                                }
                                D _3917 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, 1.0 - (_3895 * _3895))) * _3875;
                                _3897 = (_3917 * ((((_546 * _546) * 2.0) + (-1.0)) - (_3895 * _3876))) + (_3892 * _3876);
                                _3899 = (_3917 * (_546 - (_3895 * _3846))) + (_3892 * _3846);
                            }
                            else
                            {
                                _3897 = _3876;
                                _3899 = _3846;
                            }
                            D _3904 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3897 * 2.0) + 2.0));
                            _3929 = spvNMin(_3904 * (_3897 + 1.0), 1.0);
                            _3930 = spvNClamp(_3904 * (_3899 + _546), 0.0, 1.0);
                            break;
                        }
                        D _3931 = spvNMax(9.9999997473787516355514526367188e-06, _3929);
                        D _3940 = sqrt(spvNMax(0.0, 1.0 - ((1.0 - (_546 * _546)) * 0.444444477558135986328125)));
                        D _3944 = (_552 * 0.666666686534881591796875) - (_3940 * _429);
                        D _3945 = (_553 * 0.666666686534881591796875) - (_3940 * _430);
                        D _3946 = (_554 * 0.666666686534881591796875) - (_3940 * _431);
                        D _3950 = inversesqrt(dot(vec3(_3944, _3945, _3946), vec3(_3944, _3945, _3946)));
                        D _3957 = dot(vec3((-0.0) - (_3950 * _3944), (-0.0) - (_3950 * _3945), (-0.0) - (_3950 * _3946)), vec3(_2057, _2058, _2059));
                        D _3960 = _3871 * _3871;
                        D _3974 = ((_3930 * _3930) * (_3960 + (-1.0))) + 1.0;
                        D _3980 = (_3869 * 2.0) * _572;
                        D _3985 = 1.0 - _3931;
                        D _3986 = _3985 * _3985;
                        D _3988 = (_3986 * _3986) * _3985;
                        D _3992 = spvNMin(dot(vec3(_530, _531, _532), vec3(16.666667938232421875)), 1.0);
                        D _4005 = spvNMax(0.039999999105930328369140625, _650);
                        D _4018 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_4005 * _3869) + 0.02669160068035125732421875) / (_3869 + 0.4664950072765350341796875)) * exp2(((1.0 / _4005) * _3869) * log2(_4005)), 0.0, 1.0));
                        D _4019 = 1.0 - _3869;
                        D _4020 = _4019 * _4019;
                        D _4032 = ((_4020 * _4020) * _4019) * exp2(log2((exp2((_4005 * 4.7702999114990234375) * log2(_3869)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _4005);
                        D _4035 = (1.0 / _4018) * (1.0 - _4018);
                        D _4039 = (_4035 * _530) + 1.0;
                        D _4040 = (_4035 * _531) + 1.0;
                        D _4041 = (_4035 * _532) + 1.0;
                        D _4042 = _4018 - _4032;
                        D _4056 = spvNClamp(1.0 - dot(vec3(_4039 * ((_4042 * _530) + _4032), _4040 * ((_4042 * _531) + _4032), _4041 * ((_4042 * _532) + _4032)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                        D _4060 = ((((_3960 * 0.3183098733425140380859375) * _3869) * (1.0 / (_3974 * _3974))) * (_3879 ? ((1.0 / ((((_3875 * 0.25) * (_3875 + (_3871 * 3.0))) * (1.0 / _3931)) + _3960)) * _3960) : 1.0)) * (0.5 / ((_3871 * ((_572 + _3869) - _3980)) + _3980));
                        D _4061 = _3869 * 0.3183098733425140380859375;
                        D _4064 = ((_3957 * _3957) + 1.0) * 0.05968309938907623291015625;
                        D _4065 = spvNMin(1.0, _455);
                        D _4067 = (_455 + 1.0) - _4065;
                        D _4068 = _4067 * _4067;
                        D _4071 = 1.0 - ((_4068 * _4068) * _4067);
                        D _4072 = _4071 * _4071;
                        D _4077 = ((_4072 * _4072) * (_4071 * (_455 - _4065))) + _4065;
                        D _4080 = sqrt(spvNMax(0.0, 1.0 - _4077));
                        D _4084 = 1.0 - spvNClamp((_650 * 3.5) + (-0.5), 0.0, 1.0);
                        D _4085 = _4084 * _4084;
                        D _4095 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_681 * _4080) * spvNClamp(1.0 - ((_4085 * _4085) * _4084), 0.0, 1.0))) * _3869, 0.0, 1.0);
                        D _4100 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _4080)) * _3869, 0.0, 1.0);
                        D _4102 = spvNMin(_3842, _4095 * _4095);
                        D _4103 = spvNMin(_3842, _4100 * _4100);
                        D _4104 = spvNMin(_3842, _4077);
                        D _4108 = (_2718 * _1170) * _3261;
                        D _4109 = (_2718 * _1171) * _3263;
                        D _4110 = (_2718 * _1172) * _3265;
                        D _4111 = _3845 * _4108;
                        D _4115 = _3845 * _4109;
                        D _4119 = _3845 * _4110;
                        _3717 = ((((_4108 * _482) * _3845) * _4061) * _4056) * _4103;
                        _3719 = ((((_4109 * _483) * _3845) * _4061) * _4056) * _4103;
                        _3721 = ((((_4110 * _484) * _3845) * _4061) * _4056) * _4103;
                        _3723 = (((_4111 * spvNClamp(((_3992 - _530) * _3988) + _530, 0.0, 1.0)) * _4060) * _4039) * _4102;
                        _3725 = (((_4115 * _4060) * spvNClamp(((_3992 - _531) * _3988) + _531, 0.0, 1.0)) * _4040) * _4102;
                        _3727 = (((_4119 * _4060) * spvNClamp(((_3992 - _532) * _3988) + _532, 0.0, 1.0)) * _4041) * _4102;
                        _3729 = (_4111 * _4064) * _4104;
                        _3731 = (_4115 * _4064) * _4104;
                        _3733 = (_4119 * _4064) * _4104;
                        break;
                    }
                    else
                    {
                        _3717 = 0.0;
                        _3719 = 0.0;
                        _3721 = 0.0;
                        _3723 = 0.0;
                        _3725 = 0.0;
                        _3727 = 0.0;
                        _3729 = 0.0;
                        _3731 = 0.0;
                        _3733 = 0.0;
                        break;
                    }
                }
                frontier_phi_49_pred = _1156;
                frontier_phi_49_pred_1 = _3717 + _1146;
                frontier_phi_49_pred_2 = _3719 + _1147;
                frontier_phi_49_pred_3 = _3721 + _1148;
                frontier_phi_49_pred_4 = _3723 + _1149;
                frontier_phi_49_pred_5 = _3725 + _1150;
                frontier_phi_49_pred_6 = _3727 + _1151;
                frontier_phi_49_pred_7 = _3729 + _1152;
                frontier_phi_49_pred_8 = _3731 + _1153;
                frontier_phi_49_pred_9 = _3733 + _1154;
                frontier_phi_49_pred_10 = _1155;
                frontier_phi_49_pred_11 = _1157;
                frontier_phi_49_pred_12 = _1158;
                frontier_phi_49_pred_13 = _1159;
                frontier_phi_49_pred_14 = _1160;
            }
            else
            {
                D _1328 = _1165 - _231;
                D _1329 = _1166 - _232;
                D _1330 = _1167 - _233;
                D _1331 = dot(vec3(_1328, _1329, _1330), vec3(_1328, _1329, _1330));
                D _1335 = (_1168 * _1168) * _1331;
                D _1336 = _1335 * _1335;
                D _1337 = _1336 * _1336;
                D _1340 = spvNClamp(1.0 - (_1337 * _1337), 0.0, 1.0);
                D _1341 = _1340 * _1340;
                D _1342 = _1341 * _1341;
                D _1343 = _1342 * _1342;
                D _1648;
                D _1650;
                D _1652;
                D _1654;
                D _1656;
                D _1658;
                if (_1343 > 0.0)
                {
                    D _1640 = dot(vec3(_239, _240, _241), vec3(_429, _430, _431)) * 2.0;
                    D _1644 = _239 - (_1640 * _429);
                    D _1645 = _240 - (_1640 * _430);
                    D _1646 = _241 - (_1640 * _431);
                    D _3328;
                    D _3329;
                    D _3330;
                    D _3331;
                    D _3332;
                    D _3333;
                    D _3334;
                    D _3335;
                    D _3336;
                    D _3337;
                    D _3338;
                    if (_1188 == 0.0)
                    {
                        D _2723;
                        D _2724;
                        D _2725;
                        if (_1331 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2719 = inversesqrt(_1331);
                            _2723 = _2719 * _1328;
                            _2724 = _2719 * _1329;
                            _2725 = _2719 * _1330;
                        }
                        else
                        {
                            _2723 = 0.0;
                            _2724 = 0.0;
                            _2725 = 0.0;
                        }
                        D _2728 = 1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1331));
                        _3328 = _2728;
                        _3329 = (_1187 * _1187) * _2728;
                        _3330 = _2723;
                        _3331 = _2724;
                        _3332 = _2725;
                        _3333 = _2723;
                        _3334 = _2724;
                        _3335 = _2725;
                        _3336 = _2723;
                        _3337 = _2724;
                        _3338 = _2725;
                    }
                    else
                    {
                        D _2071 = _1188 * 0.5;
                        D _2072 = _2071 * _1174;
                        D _2073 = _2071 * _1175;
                        D _2074 = _2071 * _1176;
                        D _2075 = _1328 - _2072;
                        D _2076 = _1329 - _2073;
                        D _2077 = _1330 - _2074;
                        D _2078 = _2072 + _1328;
                        D _2079 = _2073 + _1329;
                        D _2080 = _2074 + _1330;
                        D _2088 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2075, _2076, _2077), vec3(_2075, _2076, _2077))));
                        D _2090 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2078, _2079, _2080), vec3(_2078, _2079, _2080))));
                        D _2091 = _2090 * _2088;
                        D _2107 = (1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(_2091, ((dot(vec3(_2075, _2076, _2077), vec3(_2078, _2079, _2080)) * 0.5) * _2091) + 0.5))) * _2091;
                        D _2109 = (_1174 * 2.0) * _2071;
                        D _2111 = (_1175 * 2.0) * _2071;
                        D _2113 = (_1176 * 2.0) * _2071;
                        D _2114 = dot(vec3(_2109, _2111, _2113), vec3(_2109, _2111, _2113));
                        D _2761;
                        D _2762;
                        D _2763;
                        if (_2114 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2731 = dot(vec3(_1644, _1645, _1646), vec3(_2109, _2111, _2113));
                            D _2747 = spvNClamp((1.0 / (_2114 - (_2731 * _2731))) * dot(vec3(_2075, _2076, _2077), vec3((_2731 * _1644) - _2109, (_2731 * _1645) - _2111, (_2731 * _1646) - _2113)), 0.0, 1.0);
                            D _2751 = (_2747 * _2109) + _2075;
                            D _2752 = (_2747 * _2111) + _2076;
                            D _2753 = (_2747 * _2113) + _2077;
                            D _2757 = inversesqrt(dot(vec3(_2751, _2752, _2753), vec3(_2751, _2752, _2753)));
                            _2761 = _2751 * _2757;
                            _2762 = _2752 * _2757;
                            _2763 = _2753 * _2757;
                        }
                        else
                        {
                            _2761 = _2075;
                            _2762 = _2076;
                            _2763 = _2077;
                        }
                        _3328 = _2107;
                        _3329 = (_1187 * _1187) * _2107;
                        _3330 = _2088 * _2075;
                        _3331 = _2088 * _2076;
                        _3332 = _2088 * _2077;
                        _3333 = _2090 * _2078;
                        _3334 = _2090 * _2079;
                        _3335 = _2090 * _2080;
                        _3336 = _2761;
                        _3337 = _2762;
                        _3338 = _2763;
                    }
                    D _3348 = _3329 + 1.0;
                    D _3353 = _3336 - _239;
                    D _3354 = _3337 - _240;
                    D _3355 = _3338 - _241;
                    D _3359 = inversesqrt(dot(vec3(_3353, _3354, _3355), vec3(_3353, _3354, _3355)));
                    D _3360 = _3359 * _3353;
                    D _3361 = _3359 * _3354;
                    D _3362 = _3359 * _3355;
                    D _3369 = spvNClamp(dot(vec3(_429, _430, _431), vec3(_3360, _3361, _3362)), 0.0, 1.0);
                    D _3370 = _650 * _650;
                    D _3376 = spvNClamp(((1.0 - _3370) * _1187) * sqrt(_3328), 0.0, 1.0);
                    D _3390 = exp2(log2(spvNClamp((((_3376 * 0.25) * (_3376 + (_3370 * 3.0))) * (1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_242, _244, _245), vec3(_3360, _3361, _3362))))) + (_3370 * _3370), 0.0, 1.0)) * 0.25);
                    D _3394 = spvNClamp(dot(vec3(_3330, _3331, _3332), vec3(_3333, _3334, _3335)), 0.0, 1.0);
                    D _3396 = _3390 * _3390;
                    D _3397 = _3396 * _3396;
                    D _3749;
                    if (_3394 < 1.0)
                    {
                        D _3740 = sqrt(spvNClamp((1.0 / (_3394 + 1.0)) * (1.0 - _3394), 0.0, 1.0));
                        _3749 = (1.0 / spvNClamp(((_3740 * 0.25) * (_3740 + (_3396 * 3.0))) + _3397, 0.0, 1.0)) * _3397;
                    }
                    else
                    {
                        _3749 = 1.0;
                    }
                    D _3753 = ((_3369 * _3369) * (_3397 + (-1.0))) + 1.0;
                    D _3756 = spvNMax(0.0, (((dot(vec3(_429, _430, _431), vec3(_3333, _3334, _3335)) + dot(vec3(_429, _430, _431), vec3(_3330, _3331, _3332))) * 0.5) + _3329) * (1.0 / (_3348 * _3348))) * 0.3183098733425140380859375;
                    D _3759 = ((_3756 * _3397) * _3749) * (1.0 / (_3753 * _3753));
                    D _3761 = (_1343 * _1170) * _3328;
                    D _3763 = (_1343 * _1171) * _3328;
                    D _3765 = (_1343 * _1172) * _3328;
                    _1648 = _3759 * _3761;
                    _1650 = _3759 * _3763;
                    _1652 = _3759 * _3765;
                    _1654 = _3756 * _3761;
                    _1656 = _3756 * _3763;
                    _1658 = _3756 * _3765;
                }
                else
                {
                    _1648 = 0.0;
                    _1650 = 0.0;
                    _1652 = 0.0;
                    _1654 = 0.0;
                    _1656 = 0.0;
                    _1658 = 0.0;
                }
                frontier_phi_49_pred = _1650 + _1156;
                frontier_phi_49_pred_1 = _1146;
                frontier_phi_49_pred_2 = _1147;
                frontier_phi_49_pred_3 = _1148;
                frontier_phi_49_pred_4 = _1149;
                frontier_phi_49_pred_5 = _1150;
                frontier_phi_49_pred_6 = _1151;
                frontier_phi_49_pred_7 = _1152;
                frontier_phi_49_pred_8 = _1153;
                frontier_phi_49_pred_9 = _1154;
                frontier_phi_49_pred_10 = _1648 + _1155;
                frontier_phi_49_pred_11 = _1652 + _1157;
                frontier_phi_49_pred_12 = _1654 + _1158;
                frontier_phi_49_pred_13 = _1656 + _1159;
                frontier_phi_49_pred_14 = _1658 + _1160;
            }
            _836 = frontier_phi_49_pred;
            _816 = frontier_phi_49_pred_1;
            _818 = frontier_phi_49_pred_2;
            _820 = frontier_phi_49_pred_3;
            _822 = frontier_phi_49_pred_4;
            _824 = frontier_phi_49_pred_5;
            _826 = frontier_phi_49_pred_6;
            _828 = frontier_phi_49_pred_7;
            _830 = frontier_phi_49_pred_8;
            _832 = frontier_phi_49_pred_9;
            _834 = frontier_phi_49_pred_10;
            _838 = frontier_phi_49_pred_11;
            _840 = frontier_phi_49_pred_12;
            _842 = frontier_phi_49_pred_13;
            _844 = frontier_phi_49_pred_14;
            uint _1162 = _1161 + 1u;
            if (_1162 == _808)
            {
                break;
            }
            else
            {
                _1146 = _816;
                _1147 = _818;
                _1148 = _820;
                _1149 = _822;
                _1150 = _824;
                _1151 = _826;
                _1152 = _828;
                _1153 = _830;
                _1154 = _832;
                _1155 = _834;
                _1156 = _836;
                _1157 = _838;
                _1158 = _840;
                _1159 = _842;
                _1160 = _844;
                _1161 = _1162;
                continue;
            }
        }
        _815 = _816;
        _817 = _818;
        _819 = _820;
        _821 = _822;
        _823 = _824;
        _825 = _826;
        _827 = _828;
        _829 = _830;
        _831 = _832;
        _833 = _834;
        _835 = _836;
        _837 = _838;
        _839 = _840;
        _841 = _842;
        _843 = _844;
    }
    vec4 _885 = textureLod(sampler3D(TranslucentBasePass_TranslucencyLightingVolumeEnvironmentA, View_SharedBilinearClampedSampler), vec3((_231 - View._m0[180u].x) * View._m0[182u].x, (_232 - View._m0[180u].y) * View._m0[182u].y, (_233 - View._m0[180u].z) * View._m0[182u].z), 0.0);
    D _909;
    D _910;
    D _911;
    if (_365 < 1.0)
    {
        _909 = _342.x / ((_387 / _364) + 1.0);
        _910 = _342.y / ((_388 / _364) + 1.0);
        _911 = _342.z / ((_389 / _364) + 1.0);
    }
    else
    {
        _909 = 0.0;
        _910 = 0.0;
        _911 = 0.0;
    }
    D _927 = spvNClamp(_632, 0.0, 1.0);
    D _940 = _480 * _480;
    D _941 = _940 * _480;
    D _948 = ((_429 - _569) * _941) + _569;
    D _949 = ((_430 - _570) * _941) + _570;
    D _950 = ((_431 - _571) * _941) + _571;
    D _954 = inversesqrt(dot(vec3(_948, _949, _950), vec3(_948, _949, _950)));
    D _963 = 10.0 / spvNMax(9.9999997473787516355514526367188e-06, _940);
    D _992 = fma(_230, View._m0[2u].x, fma(_229, View._m0[1u].x, View._m0[0u].x * _228)) + View._m0[3u].x;
    D _996 = fma(_230, View._m0[2u].y, fma(_229, View._m0[1u].y, View._m0[0u].y * _228)) + View._m0[3u].y;
    D _1000 = fma(_230, View._m0[2u].z, fma(_229, View._m0[1u].z, View._m0[0u].z * _228)) + View._m0[3u].z;
    D _1004 = fma(_230, View._m0[2u].w, fma(_229, View._m0[1u].w, View._m0[0u].w * _228)) + View._m0[3u].w;
    D _1011 = ((_948 * _108) * _954) + _228;
    D _1012 = ((_949 * _108) * _954) + _229;
    D _1013 = ((_950 * _108) * _954) + _230;
    D _1046 = 1.0 / _1004;
    D _1047 = _1046 * _992;
    D _1048 = _1046 * _996;
    D _1052 = (_1046 * _1000) + (0.0500000007450580596923828125 / _1004);
    D _1053 = 1.0 / (fma(_1013, View._m0[2u].w, fma(_1012, View._m0[1u].w, View._m0[0u].w * _1011)) + View._m0[3u].w);
    D _1064 = 1.0 / ((View._m0[36u].w * _963) + _1004);
    D _1067 = (_1053 * (fma(_1013, View._m0[2u].x, fma(_1012, View._m0[1u].x, View._m0[0u].x * _1011)) + View._m0[3u].x)) - _1047;
    D _1068 = (_1053 * (fma(_1013, View._m0[2u].y, fma(_1012, View._m0[1u].y, View._m0[0u].y * _1011)) + View._m0[3u].y)) - _1048;
    D _1070 = (_1064 * ((View._m0[36u].x * _963) + _992)) - _1047;
    D _1071 = (_1064 * ((View._m0[36u].y * _963) + _996)) - _1048;
    D _1076 = sqrt((_1067 * _1067) + (_1068 * _1068)) * 0.5;
    D _1095 = spvNMin(1.0 - (spvNMax(0.0, abs((_1076 * _1047) + _1067) - _1076) / abs(_1067)), 1.0 - (spvNMax(0.0, abs((_1076 * _1048) + _1068) - _1076) / abs(_1068))) / _1076;
    D _1096 = _1095 * _1067;
    D _1097 = _1095 * _1068;
    D _1098 = _1095 * ((_1053 * (fma(_1013, View._m0[2u].z, fma(_1012, View._m0[1u].z, View._m0[0u].z * _1011)) + View._m0[3u].z)) - _1052);
    uvec2 _1104 = uvec2(textureSize(TranslucentBasePass_HZBTexture, int(0u)));
    D _1106 = D(int(_1104.x));
    D _1108 = D(int(_1104.y));
    uint _1129 = max(1u, min(uint(ceil((spvNClamp((1.0 / spvNMax(9.9999997473787516355514526367188e-05, sqrt((_1096 * _1096) + (_1097 * _1097)))) * sqrt((_1070 * _1070) + (_1071 * _1071)), 0.0, 1.0) * 8.0) + _266)), 8u));
    D _1134 = ((_1047 * 0.5) + 0.5) * TranslucentBasePass_2._m0[198u].x;
    D _1135 = (0.5 - (_1048 * 0.5)) * TranslucentBasePass_2._m0[198u].y;
    D _1138 = (TranslucentBasePass_2._m0[198u].x * 0.0625) * _1096;
    D _1141 = (TranslucentBasePass_2._m0[198u].y * (-0.0625)) * _1097;
    D _1142 = _1098 * 0.125;
    D _1144 = spvNMax(abs(_1098), _1052 - ((1.0 / (fma(_108, View._m0[38u].w, 0.0) + _1004)) * (fma(_108, View._m0[38u].z, 0.0) + _1000))) * 0.125;
    D _1311;
    D _1313;
    D _1315;
    D _1317;
    if (_1129 == 0u)
    {
        _1311 = 0.0;
        _1313 = 0.0;
        _1315 = 0.0;
        _1317 = 0.0;
    }
    else
    {
        D frontier_phi_62;
        D frontier_phi_62_1;
        D frontier_phi_62_2;
        D frontier_phi_62_3;
        D _1561 = 0.0;
        uint _1563 = 0u;
        D _1562;
        D _1565;
        bool _1588;
        for (;;)
        {
            _1565 = D(_1563);
            D _1566 = _1565 + _266;
            vec4 _1580 = texelFetch(TranslucentBasePass_HZBTexture, ivec2_(uvec2(uint(int(floor(((_1566 * _1138) + _1134) * _1106))), uint(int(floor(((_1566 * _1141) + _1135) * _1108))))), int(0u));
            D _1582 = _1580.x;
            _1562 = ((_1566 * _1142) + _1052) - _1582;
            _1588 = (abs(((-0.0) - _1144) - _1562) < _1144) && (_1582 != 0.0);
            if (_1588)
            {
                D _1997 = (_1563 == 0u) ? (_1562 - _1142) : _1561;
                D _2004 = abs(((_266 + (-1.0)) + _1565) + spvNClamp(_1997 / (_1997 - _1562), 0.0, 1.0));
                D _2009 = spvNMin(_2004 * 0.125, 1.0);
                frontier_phi_62 = 1.0 - (_2009 * _2009);
                frontier_phi_62_1 = (_2004 * _1142) + _1052;
                frontier_phi_62_2 = (_2004 * _1141) + _1135;
                frontier_phi_62_3 = (_2004 * _1138) + _1134;
                break;
            }
            else
            {
                uint _1564 = _1563 + 1u;
                if (_1564 < _1129)
                {
                    _1561 = _1562;
                    _1563 = _1564;
                    continue;
                }
                else
                {
                    frontier_phi_62 = 0.0;
                    frontier_phi_62_1 = 0.0;
                    frontier_phi_62_2 = 0.0;
                    frontier_phi_62_3 = 0.0;
                    break;
                }
            }
        }
        _1311 = frontier_phi_62_3;
        _1313 = frontier_phi_62_2;
        _1315 = frontier_phi_62_1;
        _1317 = frontier_phi_62;
    }
    D _1325 = (spvNClamp(_1311 * TranslucentBasePass_2._m0[198u].z, 0.0, 1.0) * 2.0) + (-1.0);
    D _1326 = 1.0 - (spvNClamp(_1313 * TranslucentBasePass_2._m0[198u].w, 0.0, 1.0) * 2.0);
    D _1466;
    D _1468;
    D _1470;
    D _1472;
    if (_1317 > 0.0)
    {
        D _1467;
        D _1469;
        D _1471;
        D _2213;
        D _1459;
        bool _1465;
        for (;;)
        {
            D _1418 = ((View._m0[73u].x * _1315) + View._m0[73u].y) + (1.0 / ((View._m0[73u].z * _1315) - View._m0[73u].w));
            D _1442 = _1418 * _1325;
            D _1443 = _1418 * _1326;
            D _1454 = (_228 - View._m0[63u].x) - fma(_1418, View._m0[62u].x, fma(_1443, View._m0[61u].x, _1442 * View._m0[60u].x));
            D _1456 = (_229 - View._m0[63u].y) - fma(_1418, View._m0[62u].y, fma(_1443, View._m0[61u].y, _1442 * View._m0[60u].y));
            D _1458 = (_230 - View._m0[63u].z) - fma(_1418, View._m0[62u].z, fma(_1443, View._m0[61u].z, _1442 * View._m0[60u].z));
            _1459 = dot(vec3(_1454, _1456, _1458), vec3(_1454, _1456, _1458));
            _1465 = View._m0[175u].w != 0.0;
            if (_1465)
            {
                if (floatBitsToUint(View._m0[175u]).y == 0u)
                {
                    _1467 = 0.0;
                    _1469 = 0.0;
                    _1471 = 0.0;
                    _2213 = 0.0;
                    break;
                }
            }
            D _1855 = fma(_1315, View._m0[140u].w, fma(_1326, View._m0[139u].w, View._m0[138u].w * _1325)) + View._m0[141u].w;
            D _1856 = (fma(_1315, View._m0[140u].x, fma(_1326, View._m0[139u].x, View._m0[138u].x * _1325)) + View._m0[141u].x) / _1855;
            D _1857 = (fma(_1315, View._m0[140u].y, fma(_1326, View._m0[139u].y, View._m0[138u].y * _1325)) + View._m0[141u].y) / _1855;
            D _1874 = spvNClamp((abs((spvNMin(spvNMax(_1856, -1.0), 1.0) - _1325) * 0.5) * 5.0) + (-4.0), 0.0, 1.0);
            D _1875 = spvNClamp((abs((spvNMin(spvNMax(_1857, -1.0), 1.0) - _1326) * 0.5) * 5.0) + (-4.0), 0.0, 1.0);
            uvec2 _1928 = uvec2(textureSize(TranslucentBasePass_PrevSceneColor, int(0u)));
            vec4 _1949 = texelFetch(TranslucentBasePass_PrevSceneColor, ivec2_(uvec2(uint(min(int(uint(max(int(uint(int(D(int(_1928.x)) * ((TranslucentBasePass_2._m0[199u].x * spvNMin(spvNMax(_1856 - ((D(int(uint(_1856 > 0.0) - uint(_1856 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1856) + (-1.0))), -1.0), 1.0)) + TranslucentBasePass_2._m0[199u].z)))), int(uint(int(TranslucentBasePass_2._m0[200u].x)))))), int(uint(int(TranslucentBasePass_2._m0[200u].x + TranslucentBasePass_2._m0[200u].z)) + 4294967295u))), uint(min(int(uint(max(int(uint(int(D(int(_1928.y)) * ((TranslucentBasePass_2._m0[199u].y * spvNMin(spvNMax(_1857 - ((D(int(uint(_1857 > 0.0) - uint(_1857 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1857) + (-1.0))), -1.0), 1.0)) + TranslucentBasePass_2._m0[199u].w)))), int(uint(int(TranslucentBasePass_2._m0[200u].y)))))), int(uint(int(TranslucentBasePass_2._m0[200u].y + TranslucentBasePass_2._m0[200u].w)) + 4294967295u))))), int(0u));
            _1467 = View._m0[165u].x * spvNMin(_1949.x, 65504.0);
            _1469 = View._m0[165u].x * spvNMin(_1949.y, 65504.0);
            _1471 = View._m0[165u].x * spvNMin(_1949.z, 65504.0);
            _2213 = spvNMax(0.0, 1.0 - dot(vec2(_1874, _1875), vec2(_1874, _1875)));
            break;
        }
        _1466 = _1467;
        _1468 = _1469;
        _1470 = _1471;
        _1472 = (_2213 * _1317) * spvNClamp(1.0 / spvNMax(9.9999997473787516355514526367188e-06, (_940 * _940) * _1459), 0.0, 1.0);
    }
    else
    {
        _1466 = 0.0;
        _1468 = 0.0;
        _1470 = 0.0;
        _1472 = 0.0;
    }
    D _1506 = fma(_233, View._m0[14u].w, fma(_232, View._m0[13u].w, _231 * View._m0[12u].w)) + View._m0[15u].w;
    D _1511 = (((fma(_233, View._m0[14u].x, fma(_232, View._m0[13u].x, _231 * View._m0[12u].x)) + View._m0[15u].x) / _1506) * 0.5) + 0.5;
    D _1512 = 0.5 - (((fma(_233, View._m0[14u].y, fma(_232, View._m0[13u].y, _231 * View._m0[12u].y)) + View._m0[15u].y) / _1506) * 0.5);
    D _1541 = sqrt(((_229 * _229) + (_228 * _228)) + (_230 * _230));
    D _1559 = spvNMax(0.0, ((1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_228, _229, _230), vec3(View._m0[68u].xyz())))) * _1541) * View._m0[280u].w);
    D _1965;
    D _1967;
    D _1969;
    D _1971;
    D _1973;
    D _1975;
    if (_1541 < _1559)
    {
        _1965 = 0.0;
        _1967 = 0.0;
        _1969 = 0.0;
        _1971 = 1.0;
        _1973 = 1.0;
        _1975 = 1.0;
    }
    else
    {
        D _1983 = (1.0 / _1541) * _1559;
        uvec4 _1990 = floatBitsToUint(View._m0[220u]);
        uint _1991 = _1990.y;
        uint _1993 = (_1991 != 1u) ? 4294967295u : 0u;
        uint _2359;
        if (_1991 > 1u)
        {
            D _133[4];
            _133[0u] = 0.0;
            _133[1u] = 0.0;
            _133[2u] = 0.0;
            _133[3u] = 0.0;
            uint _3205 = 0u;
            bool _3211;
            for (;;)
            {
                _3211 = _3205 < floatBitsToUint(View._m0[220u]).y;
                if (_3211)
                {
                    uint _3632 = _3205 + 237u;
                    D _3644 = View._m0[_3632].x - View._m0[75u].x;
                    D _3645 = View._m0[_3632].y - View._m0[75u].y;
                    D _3646 = View._m0[_3632].z - View._m0[75u].z;
                    D _3647 = dot(vec3(_3644, _3645, _3646), vec3(_239, _240, _241));
                    D _3654 = dot(vec3(_3644, _3645, _3646), vec3(_3644, _3645, _3646)) - (View._m0[_3632].w * View._m0[_3632].w);
                    D _3656 = (_3647 * _3647) - _3654;
                    D _3774;
                    if ((_3654 < 0.0) && (!(_3656 < 0.0)))
                    {
                        D _3768 = sqrt(_3656);
                        _3774 = spvNMin(abs(_3768 + _3647), abs(_3647 - _3768));
                    }
                    else
                    {
                        _3774 = 0.0;
                    }
                    _133[_3205] = _3774;
                }
                uint _3206 = _3205 + 1u;
                if (_3206 == 4u)
                {
                    break;
                }
                else
                {
                    _3205 = _3206;
                    continue;
                }
            }
            D _3784 = (_266 * 0.99989998340606689453125) * dot(vec4(_133[0u], _133[1u], _133[2u], _133[3u]), vec4(1.0));
            uint frontier_phi_61_99_ladder;
            if (_133[0u] > _3784)
            {
                frontier_phi_61_99_ladder = 0u;
            }
            else
            {
                D _3852 = _133[1u] + _133[0u];
                uint frontier_phi_61_99_ladder_105_ladder;
                if (_3852 > _3784)
                {
                    frontier_phi_61_99_ladder_105_ladder = 1u;
                }
                else
                {
                    D _3882 = _3852 + _133[2u];
                    uint frontier_phi_61_99_ladder_105_ladder_111_ladder;
                    if (_3882 > _3784)
                    {
                        frontier_phi_61_99_ladder_105_ladder_111_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_61_99_ladder_105_ladder_111_ladder_116_ladder;
                        if ((_3882 + _133[3u]) > _3784)
                        {
                            frontier_phi_61_99_ladder_105_ladder_111_ladder_116_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_61_99_ladder_105_ladder_111_ladder_116_ladder = _1993;
                        }
                        frontier_phi_61_99_ladder_105_ladder_111_ladder = frontier_phi_61_99_ladder_105_ladder_111_ladder_116_ladder;
                    }
                    frontier_phi_61_99_ladder_105_ladder = frontier_phi_61_99_ladder_105_ladder_111_ladder;
                }
                frontier_phi_61_99_ladder = frontier_phi_61_99_ladder_105_ladder;
            }
            _2359 = frontier_phi_61_99_ladder;
        }
        else
        {
            _2359 = _1993;
        }
        D frontier_phi_40_61_ladder;
        D frontier_phi_40_61_ladder_1;
        D frontier_phi_40_61_ladder_2;
        D frontier_phi_40_61_ladder_3;
        D frontier_phi_40_61_ladder_4;
        D frontier_phi_40_61_ladder_5;
        if (_2359 == 4294967295u)
        {
            frontier_phi_40_61_ladder = 1.0;
            frontier_phi_40_61_ladder_1 = 1.0;
            frontier_phi_40_61_ladder_2 = 1.0;
            frontier_phi_40_61_ladder_3 = 0.0;
            frontier_phi_40_61_ladder_4 = 0.0;
            frontier_phi_40_61_ladder_5 = 0.0;
        }
        else
        {
            uint _3212 = _2359 + 221u;
            D _3220 = spvNMin(View._m0[_3212].w, 0.9900000095367431640625);
            uint _3221 = _2359 + 225u;
            uint _3228 = _2359 + 229u;
            uint _3235 = _2359 + 233u;
            uint _3240 = _2359 + 241u;
            D _3687;
            D _3688;
            D _3689;
            if (TranslucentBasePass_2._m0[146u].x > 0.0)
            {
                vec4 _3679 = textureLod(sampler2D(TranslucentBasePass_Shared_Fog_FarIntegratedScatteringTexture, View_SharedBilinearClampedSampler), vec2(spvNMin(spvNMax(View._m0[278u].x * _1511, View._m0[279u].x), View._m0[280u].x), spvNMin(spvNMax(View._m0[278u].y * _1512, View._m0[279u].y), View._m0[280u].y)), 0.0);
                _3687 = View._m0[164u].z * _3679.x;
                _3688 = View._m0[164u].z * _3679.y;
                _3689 = View._m0[164u].z * _3679.z;
            }
            else
            {
                _3687 = 0.0;
                _3688 = 0.0;
                _3689 = 0.0;
            }
            D _3693 = dot(vec3((-0.0) - View._m0[218u].x, (-0.0) - View._m0[218u].y, (-0.0) - View._m0[218u].z), vec3(_242, _244, _245));
            D _3706 = (((_3693 * _3693) + 1.0) * 0.0397887341678142547607421875) * exp2(log2(spvNMax(0.0, _3693 + 1.25)) * (-1.5));
            D _3786;
            if (View._m0[_3221].x == 0.0)
            {
                _3786 = 0.0;
            }
            else
            {
                D _3834 = (((_1983 * _230) - View._m0[_3221].z) + View._m0[75u].z) * View._m0[_3221].y;
                D _3835 = ((1.0 - _1983) * _230) * View._m0[_3221].y;
                D _3840 = exp2((-0.0) - _3834);
                D frontier_phi_100_101_ladder;
                if (abs(_3835) > 0.00999999977648258209228515625)
                {
                    frontier_phi_100_101_ladder = ((_3840 - exp2(((-0.0) - _3835) - _3834)) * View._m0[_3221].x) * (1.0 / _3835);
                }
                else
                {
                    frontier_phi_100_101_ladder = (View._m0[_3221].x * 0.693147182464599609375) * _3840;
                }
                _3786 = frontier_phi_100_101_ladder;
            }
            D _3790 = _3786 * (1.0 - _3220);
            D _3794 = (1.0 - View._m0[_3228].x) * View._m0[_3235].x;
            D _3795 = (1.0 - View._m0[_3228].y) * View._m0[_3235].x;
            D _3796 = (1.0 - View._m0[_3228].z) * View._m0[_3235].x;
            D _3797 = (-0.0) - (_1541 - _1559);
            D _3825 = 1.0 - spvNClamp(exp2(_3790 * _3797), 0.0, 1.0);
            frontier_phi_40_61_ladder = spvNClamp(exp2((_3790 + _3796) * _3797), 0.0, 1.0);
            frontier_phi_40_61_ladder_1 = spvNClamp(exp2((_3790 + _3795) * _3797), 0.0, 1.0);
            frontier_phi_40_61_ladder_2 = spvNClamp(exp2((_3790 + _3794) * _3797), 0.0, 1.0);
            frontier_phi_40_61_ladder_3 = (((_3220 * View._m0[_3212].z) * (((View._m0[219u].z * View._m0[_3240].x) * _3706) + _3689)) * spvNClamp(exp2(_3796 * _3797), 0.0, 1.0)) * _3825;
            frontier_phi_40_61_ladder_4 = (((_3220 * View._m0[_3212].y) * (((View._m0[219u].y * View._m0[_3240].x) * _3706) + _3688)) * spvNClamp(exp2(_3795 * _3797), 0.0, 1.0)) * _3825;
            frontier_phi_40_61_ladder_5 = (((_3220 * View._m0[_3212].x) * (((View._m0[219u].x * View._m0[_3240].x) * _3706) + _3687)) * spvNClamp(exp2(_3794 * _3797), 0.0, 1.0)) * _3825;
        }
        _1965 = frontier_phi_40_61_ladder_5;
        _1967 = frontier_phi_40_61_ladder_4;
        _1969 = frontier_phi_40_61_ladder_3;
        _1971 = frontier_phi_40_61_ladder_2;
        _1973 = frontier_phi_40_61_ladder_1;
        _1975 = frontier_phi_40_61_ladder;
    }
    D _2261;
    D _2262;
    D _2263;
    D _2264;
    D _2265;
    D _2266;
    if (TranslucentBasePass_2._m0[148u].x > 0.0)
    {
        D _2241 = spvNMin(spvNMax(View._m0[278u].x * _1511, View._m0[279u].x), View._m0[280u].x);
        D _2242 = spvNMin(spvNMax(View._m0[278u].y * _1512, View._m0[279u].y), View._m0[280u].y);
        D _2243 = spvNMin(spvNMax((View._m0[275u].z * spvNMax(0.0, spvNMin(View._m0[276u].z * log2((View._m0[276u].x * _1506) + View._m0[276u].y), View._m0[274u].z + (-1.0)) + 0.5)) * View._m0[278u].z, View._m0[279u].z), View._m0[280u].z);
        vec4 _2246 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeATexture, View_SharedBilinearClampedSampler), vec3(_2241, _2242, _2243), 0.0);
        vec4 _2253 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeBTexture, View_SharedBilinearClampedSampler), vec3(_2241, _2242, _2243), 0.0);
        _2261 = View._m0[164u].z * _2246.x;
        _2262 = View._m0[164u].z * _2246.y;
        _2263 = View._m0[164u].z * _2246.z;
        _2264 = _2253.x;
        _2265 = _2253.y;
        _2266 = _2253.z;
    }
    else
    {
        _2261 = 0.0;
        _2262 = 0.0;
        _2263 = 0.0;
        _2264 = 1.0;
        _2265 = 1.0;
        _2266 = 1.0;
    }
    D _2273 = spvNClamp(_546, 0.0, 1.0);
    D _2282 = ((spvNMin(_594, exp2(_2273 * (-9.27999973297119140625))) * _584) + _585) * 1.03999996185302734375;
    D _2288 = 1.0 - spvNClamp((_589 + _2282) + ((_587 - _2282) * 0.0400000028312206268310546875), 0.0, 1.0);
    D _2294 = (_2288 * _2288) * exp2(spvNMax(0.001000000047497451305389404296875, 0.300000011920928955078125 / spvNMax(0.0333333350718021392822265625, _2273)) * (-0.0291463173925876617431640625));
    D _2296 = _2294 - (_2294 * _453);
    D _2300 = (1.0 - _637) + (_637 * _453);
    D _2301 = (1.0 - _640) + (_640 * _453);
    D _2302 = (1.0 - _643) + (_643 * _453);
    D _2324 = _1971 * ((((((((((_482 * _455) * _708) * spvNMax(1.0, ((_537 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_537 * 4.79510021209716796875)) + (((_537 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _455)) * _455))) * _839) + _815) * _459) + _821) + ((((_909 * _605) * spvNClamp(1.0 - (_621 * _611), 0.0, 1.0)) * ((View._m0[164u].z * _885.x) + _827)) * _927)) + (_2296 * spvNMax(0.0, g_R.Emissive.x))) + ((_722 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1466)) + 29.8973522186279296875) * _1472) + (-29.8973522186279296875)) + _833)) * spvNClamp(_700, 0.0, 1.0)));
    D _2326 = _1973 * ((((((((((_483 * _455) * _708) * spvNMax(1.0, ((_538 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_538 * 4.79510021209716796875)) + (((_538 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _455)) * _455))) * _841) + _817) * _459) + _823) + ((((_910 * _605) * spvNClamp(1.0 - (_622 * _611), 0.0, 1.0)) * ((View._m0[164u].z * _885.y) + _829)) * _927)) + (_2296 * spvNMax(0.0, g_R.Emissive.y))) + ((_722 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1468)) + 29.8973522186279296875) * _1472) + (-29.8973522186279296875)) + _835)) * spvNClamp(_701, 0.0, 1.0)));
    D _2328 = _1975 * ((((((((((_484 * _455) * _708) * spvNMax(1.0, ((_539 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_539 * 4.79510021209716796875)) + (((_539 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _455)) * _455))) * _843) + _819) * _459) + _825) + ((((_911 * _605) * ((View._m0[164u].z * _885.z) + _831)) * spvNClamp(1.0 - (_623 * _611), 0.0, 1.0)) * _927)) + (_2296 * spvNMax(0.0, g_R.Emissive.z))) + ((_722 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1470)) + 29.8973522186279296875) * _1472) + (-29.8973522186279296875)) + _837)) * spvNClamp(_702, 0.0, 1.0)));
    SV_Target.x = View._m0[164u].y * ((((_2264 * _1965) + _2261) * _2300) + (_2324 * _2264));
    SV_Target.y = View._m0[164u].y * ((((_2265 * _1967) + _2262) * _2301) + (_2326 * _2265));
    SV_Target.z = View._m0[164u].y * ((((_2266 * _1969) + _2263) * _2302) + (_2328 * _2266));
    SV_Target.w = dot(vec3(_2300, _2301, _2302), vec3(0.2125999927520751953125, 0.715200006961822509765625, 0.072200000286102294921875));
    SV_Target_1.x = _2300;
    SV_Target_1.y = _2301;
    SV_Target_1.z = _2302;
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
} // namespace S_lass_Emissive_Thin_Environment