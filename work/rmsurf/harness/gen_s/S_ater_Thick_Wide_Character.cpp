namespace S_ater_Thick_Wide_Character {
using namespace cpuglsl;
static D _4443;
static D _4439;
static D _4440;
static D _4441;
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
static Tex3D TranslucentBasePass_TranslucencyLightingVolumeEnvironmentB{texid("TranslucentBasePass_TranslucencyLightingVolumeEnvironmentB")};
static Tex3D TranslucentBasePass_TranslucencyLightingVolumeEnvironmentC{texid("TranslucentBasePass_TranslucencyLightingVolumeEnvironmentC")};
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









void discard_cond(bool _4429)
{
    if (_4429)
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
    D _105 = 1.0 / gl_FragCoord.w;
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
    vec4 _323 = texture(sampler2D(Material_Texture2D_14, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.z, TEXCOORD.w), View._m0[155u].y);
    D _325 = _323.x;
    D _326 = _325 * _320;
    D _327 = spvNMin(_320, _325);
    D _329 = (1.0 - _327) + _326;
    D _330 = _329 * _329;
    D _333 = 1.0 - ((_330 * _330) * _329);
    D _334 = _333 * _333;
    vec4 _342 = texture(sampler2D(Material_Texture2D_7, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _348 = vec4(g_R.Muddiness.x, g_R.Muddiness.y, g_R.Muddiness.z, 0.0);
    vec4 _355 = texture(sampler2D(Material_Texture2D_19, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _360 = texture(sampler2D(Material_Texture2D_20, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _370 = g_R.TransparencyLog2;
    D _371 = exp2(_370);
    vec4 _374 = texture(sampler2D(Material_Texture2D_21, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _381 = texture(sampler2D(Material_Texture2D_22, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _386 = 1.0 / spvNMax(9.9999999747524270787835121154785e-07, _381.x * 100.0);
    D _393 = g_R.TransmittanceLog2.x;
    D _394 = g_R.TransmittanceLog2.y;
    D _395 = g_R.TransmittanceLog2.z;
    vec4 _401 = vec4(g_R.Thickness);
    D _408 = inversesqrt(dot(vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z), vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z)));
    D _409 = _408 * g_R.Normal.x;
    D _410 = _408 * g_R.Normal.y;
    D _411 = _408 * g_R.Normal.z;
    D _414 = fma(_411, TEXCOORD_11.x, fma(_410, ((TEXCOORD_10.z * TEXCOORD_11.y) - (TEXCOORD_10.y * TEXCOORD_11.z)) * TEXCOORD_11.w, _409 * TEXCOORD_10.x));
    D _417 = fma(_411, TEXCOORD_11.y, fma(_410, ((TEXCOORD_10.x * TEXCOORD_11.z) - (TEXCOORD_10.z * TEXCOORD_11.x)) * TEXCOORD_11.w, _409 * TEXCOORD_10.y));
    D _420 = fma(_411, TEXCOORD_11.z, fma(_410, ((TEXCOORD_10.y * TEXCOORD_11.x) - (TEXCOORD_10.x * TEXCOORD_11.y)) * TEXCOORD_11.w, _409 * TEXCOORD_10.z));
    D _424 = inversesqrt(dot(vec3(_414, _417, _420), vec3(_414, _417, _420)));
    D _425 = _424 * _414;
    D _426 = _424 * _417;
    D _427 = _424 * _420;
    bool _440;
    if (Primitive._m0[27u].w > ((_264.w * 0.99609375) + 0.001953125))
    {
        _440 = ((_267 * 0.99609375) + 0.001953125) < 1.0;
    }
    else
    {
        _440 = false;
    }
    (void)((_440 ? 1.0 : (-1.0)) < 0.0);
    D _446 = spvNClamp(g_R.BaseColor.x, 0.0, 1.0);
    D _447 = spvNClamp(g_R.BaseColor.y, 0.0, 1.0);
    D _448 = spvNClamp(g_R.BaseColor.z, 0.0, 1.0);
    D _449 = spvNClamp(g_R.Metallic, 0.0, 1.0);
    D _450 = spvNClamp(g_R.Roughness, 0.0, 1.0);
    D _451 = spvNClamp(g_R.AO, 0.0, 1.0);
    D _452 = spvNClamp(g_R.Opacity, 0.0, 1.0);
    D _454 = dFdxFine(_425);
    D _455 = dFdxFine(_426);
    D _456 = dFdxFine(_427);
    D _460 = dFdyFine(_425);
    D _461 = dFdyFine(_426);
    D _462 = dFdyFine(_427);
    D _473 = sqrt(spvNClamp(spvNMin((dot(vec3(_460, _461, _462), vec3(_460, _461, _462)) + dot(vec3(_454, _455, _456), vec3(_454, _455, _456))) * 0.15915493667125701904296875, 0.180000007152557373046875) + (_450 * _450), 0.0, 1.0));
    D _474 = 1.0 - _449;
    D _475 = _474 * _446;
    D _476 = _474 * _447;
    D _477 = _474 * _448;
    D _482 = _449 * (_446 + (-0.0203731842339038848876953125));
    D _483 = _449 * (_447 + (-0.0203731842339038848876953125));
    D _484 = _449 * (_448 + (-0.0203731842339038848876953125));
    D _485 = _482 + 0.0203731842339038848876953125;
    D _487 = _483 + 0.0203731842339038848876953125;
    D _488 = _484 + 0.0203731842339038848876953125;
    D _495 = spvNClamp(D(View._m0[220u].x > 1.0), 0.0, 1.0);
    D _523 = ((exp2(log2(spvNMax(0.0, _482 + 0.000373184680938720703125) * 1.020408153533935546875) * 1.39999997615814208984375) - _485) * _495) + _485;
    D _524 = ((exp2(log2(spvNMax(0.0, _483 + 0.000373184680938720703125) * 1.020408153533935546875) * 1.39999997615814208984375) - _487) * _495) + _487;
    D _525 = ((exp2(log2(spvNMax(0.0, _484 + 0.000373184680938720703125) * 1.020408153533935546875) * 1.39999997615814208984375) - _488) * _495) + _488;
    D _530 = (_523 * 0.449999988079071044921875) + _475;
    D _531 = (_524 * 0.449999988079071044921875) + _476;
    D _532 = (_525 * 0.449999988079071044921875) + _477;
    D _539 = dot(vec3(_425, _426, _427), vec3(_243, _245, _246));
    D _545 = (_539 * _425) + _240;
    D _546 = (_539 * _426) + _241;
    D _547 = (_539 * _427) + _242;
    D _551 = abs(_539);
    D _555 = (_545 * 2.0) + (_551 * _425);
    D _556 = (_546 * 2.0) + (_551 * _426);
    D _557 = (_547 * 2.0) + (_551 * _427);
    D _561 = inversesqrt(dot(vec3(_555, _556, _557), vec3(_555, _556, _557)));
    D _562 = _555 * _561;
    D _563 = _556 * _561;
    D _564 = _557 * _561;
    D _565 = _539 * _539;
    D _566 = 1.0 - _565;
    D _575 = sqrt(spvNMax(0.0, 1.0 - (_566 * 0.562781393527984619140625)));
    D _579 = (_545 * 0.750187575817108154296875) - (_575 * _425);
    D _580 = (_546 * 0.750187575817108154296875) - (_575 * _426);
    D _581 = (_547 * 0.750187575817108154296875) - (_575 * _427);
    D _585 = inversesqrt(dot(vec3(_579, _580, _581), vec3(_579, _580, _581)));
    D _586 = _579 * _585;
    D _587 = _580 * _585;
    D _588 = _581 * _585;
    D _592 = _473 * _473;
    D _593 = _592 * _473;
    D _600 = ((((-0.0) - _425) - _586) * _593) + _586;
    D _601 = ((((-0.0) - _426) - _587) * _593) + _587;
    D _602 = ((((-0.0) - _427) - _588) * _593) + _588;
    D _606 = inversesqrt(dot(vec3(_600, _601, _602), vec3(_600, _601, _602)));
    D _607 = _600 * _606;
    D _608 = _601 * _606;
    D _609 = _602 * _606;
    D _610 = spvNMax(9.9999997473787516355514526367188e-06, _551);
    D _629 = 1.0 - _473;
    D _643 = ((spvNMin(_629 * _629, exp2(_610 * (-9.27999973297119140625))) * _629) + (0.0425000004470348358154296875 - (_473 * 0.0274999998509883880615234375))) * 1.03999996185302734375;
    D _649 = 1.0 - spvNClamp((((_473 * 0.02199999988079071044921875) + (-0.039999999105930328369140625)) + _643) + (((1.03999996185302734375 - (_473 * 0.572000026702880859375)) - _643) * 0.0203731842339038848876953125), 0.0, 1.0);
    D _650 = spvNMax(0.001000000047497451305389404296875, spvNMin(spvNMax(0.0, (View._m0[73u].y - _105) + (1.0 / ((-0.0) - View._m0[73u].w))), _401.x * 100.0));
    D _653 = log2(spvNMax(0.0, _371));
    D _655 = exp2(_653 * _650);
    D _659 = log2(spvNMax(0.0, exp2(_393)));
    D _660 = log2(spvNMax(0.0, exp2(_394)));
    D _661 = log2(spvNMax(0.0, exp2(_395)));
    D _665 = exp2(_659 * _650);
    D _666 = exp2(_660 * _650);
    D _667 = exp2(_661 * _650);
    D _669 = exp2(_653 * 0.001000000047497451305389404296875);
    D _676 = 1.0 - _452;
    D _678 = (_649 * _676) * _655;
    D _681 = ((_678 * _665) * _669) * exp2(_659 * 0.001000000047497451305389404296875);
    D _684 = ((_678 * _666) * _669) * exp2(_660 * 0.001000000047497451305389404296875);
    D _687 = ((_678 * _667) * _669) * exp2(_661 * 0.001000000047497451305389404296875);
    D _694 = spvNMax(0.039999999105930328369140625, _473);
    D _710 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_694 * _610) + 0.02669160068035125732421875) / (_610 + 0.4664950072765350341796875)) * exp2(((1.0 / _694) * _610) * log2(_694)), 0.0, 1.0));
    D _711 = 1.0 - _610;
    D _712 = _711 * _711;
    D _725 = _712 * _712;
    D _727 = (_725 * _711) * exp2(log2((exp2((_694 * 4.7702999114990234375) * log2(_610)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _694);
    D _730 = (1.0 / _710) * (1.0 - _710);
    D _737 = _710 - _727;
    D _744 = ((_730 * _523) + 1.0) * ((_737 * _523) + _727);
    D _745 = ((_730 * _524) + 1.0) * ((_737 * _524) + _727);
    D _746 = ((_730 * _525) + 1.0) * ((_737 * _525) + _727);
    D _752 = spvNClamp(1.0 - dot(vec3(_744, _745, _746), vec3(0.3333333432674407958984375)), 0.0, 1.0);
    D _766 = spvNClamp((_451 + (-1.0)) + exp2(log2(_610 + _451) * exp2((-1.0) - (_473 * 16.0))), 0.0, 1.0);
    D _826;
    D _828;
    D _830;
    D _832;
    D _834;
    D _836;
    D _838;
    D _840;
    D _842;
    if (floatBitsToUint(TranslucentBasePass_2._m0[0u]).z == 0u)
    {
        _826 = 0.0;
        _828 = 0.0;
        _830 = 0.0;
        _832 = 0.0;
        _834 = 0.0;
        _836 = 0.0;
        _838 = 0.0;
        _840 = 0.0;
        _842 = 0.0;
    }
    else
    {
        D _1335;
        uint _857;
        bool _858;
        for (;;)
        {
            _857 = floatBitsToUint(TranslucentBasePass_2._m0[7u]).z;
            _858 = _857 == 0u;
            if (!_858)
            {
                uint _1500;
                uint _1403 = 0u;
                for (;;)
                {
                    if (_105 < TranslucentBasePass._m0[_1403 + 32u])
                    {
                        _1500 = _1403;
                        break;
                    }
                    else
                    {
                        uint _1404 = _1403 + 1u;
                        if (_1404 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                        {
                            _1403 = _1404;
                            continue;
                        }
                        else
                        {
                            _1500 = _857;
                            break;
                        }
                    }
                }
                if (_1500 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                {
                    uint _1850 = _1500 << 2u;
                    uint _1851 = _1850 + 9u;
                    uint _1858 = _1850 + 10u;
                    uint _1865 = _1850 + 11u;
                    uint _1872 = _1850 + 12u;
                    uint _1879 = _1500 + 25u;
                    D _1905 = fma(_234, TranslucentBasePass_2._m0[_1865].z, fma(_233, TranslucentBasePass_2._m0[_1858].z, TranslucentBasePass_2._m0[_1851].z * _232)) + TranslucentBasePass_2._m0[_1872].z;
                    D _1909 = fma(_234, TranslucentBasePass_2._m0[_1865].w, fma(_233, TranslucentBasePass_2._m0[_1858].w, TranslucentBasePass_2._m0[_1851].w * _232)) + TranslucentBasePass_2._m0[_1872].w;
                    D _1910 = (fma(_234, TranslucentBasePass_2._m0[_1865].x, fma(_233, TranslucentBasePass_2._m0[_1858].x, TranslucentBasePass_2._m0[_1851].x * _232)) + TranslucentBasePass_2._m0[_1872].x) / _1909;
                    D _1911 = (fma(_234, TranslucentBasePass_2._m0[_1865].y, fma(_233, TranslucentBasePass_2._m0[_1858].y, TranslucentBasePass_2._m0[_1851].y * _232)) + TranslucentBasePass_2._m0[_1872].y) / _1909;
                    bool _1918 = (_1911 <= TranslucentBasePass_2._m0[_1879].w) && ((_1910 <= TranslucentBasePass_2._m0[_1879].z) && ((_1910 >= TranslucentBasePass_2._m0[_1879].x) && (_1911 >= TranslucentBasePass_2._m0[_1879].y)));
                    D _1336;
                    if (_1918)
                    {
                        D _2275 = dFdyFine(_1910);
                        D _2276 = dFdyFine(_1911);
                        D _2277 = dFdyFine(_1905);
                        D _2278 = dFdxFine(_1910);
                        D _2279 = dFdxFine(_1911);
                        D _2280 = dFdxFine(_1905);
                        D _2283 = (_2279 * _2277) - (_2280 * _2276);
                        D _2286 = (_2280 * _2275) - (_2278 * _2277);
                        D _2289 = (_2278 * _2276) - (_2279 * _2275);
                        D _2299 = 1.0 / spvNMax(abs(_2289), sqrt(((_2286 * _2286) + (_2289 * _2289)) + (_2283 * _2283)) * 0.100000001490116119384765625);
                        D _2305 = D(int(uint(_2289 > 0.0) - uint(_2289 < 0.0)));
                        D _2306 = _2283 * TranslucentBasePass_2._m0[29u].z;
                        D _2308 = (_2306 * _2299) * _2305;
                        D _2309 = _2286 * TranslucentBasePass_2._m0[29u].w;
                        D _2311 = (_2309 * _2299) * _2305;
                        D _2900;
                        D _2902;
                        if (dot(vec2(_2283, _2286), vec2(_2283, _2286)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2900 = 0.0;
                            _2902 = 0.0;
                        }
                        else
                        {
                            D _3270 = (-0.0) - _2283;
                            D _3271 = (-0.0) - _2286;
                            D _3275 = inversesqrt(dot(vec2(_3270, _3271), vec2(_3270, _3271)));
                            _2900 = _3275 * _3270;
                            _2902 = _3275 * _3271;
                        }
                        D _2904 = _268 + (-0.5);
                        D _2909 = _267 + 0.5;
                        D _2912 = ((_2902 * _2904) + (_1910 * TranslucentBasePass_2._m0[29u].x)) + (_2900 * _2909);
                        D _2915 = ((_2900 * _2904) + (_1911 * TranslucentBasePass_2._m0[29u].y)) + (_2902 * _2909);
                        D _2916 = _2912 + (-0.5);
                        D _2917 = _2915 + (-0.5);
                        D _2918 = trunc(_2916);
                        D _2919 = trunc(_2917);
                        D _2920 = _2916 - _2918;
                        D _2921 = _2917 - _2919;
                        D _2922 = _2918 * TranslucentBasePass_2._m0[29u].z;
                        D _2923 = _2919 * TranslucentBasePass_2._m0[29u].w;
                        D _2926 = (_2918 + (-0.5)) - _2912;
                        D _2927 = (_2919 + (-0.5)) - _2915;
                        D _2928 = dot(vec2(_2926, _2927), vec2(_2308, _2311));
                        D _2931 = _2928 + _2311;
                        D _2934 = _2305 * (_2299 * (_2309 + _2306));
                        D _2935 = _2934 + _2928;
                        D _2936 = _2928 + _2308;
                        vec4 _2942 = textureGather((sampler2D(ShadowMaps[_1500 + 0u], View_SharedPointClampedSampler)), vec2(_2922, _2923));
                        D _2943 = _2942.x;
                        D _2944 = _2942.y;
                        D _2945 = _2942.z;
                        D _2946 = _2942.w;
                        D _2983 = 1.525902189314365386962890625e-05 - _1905;
                        D _3014 = (_2918 + 1.5) - _2912;
                        D _3015 = dot(vec2(_3014, _2927), vec2(_2308, _2311));
                        D _3018 = _3015 + _2311;
                        D _3019 = _2934 + _3015;
                        D _3020 = _3015 + _2308;
                        vec4 _3022 = textureGatherOffset((sampler2D(ShadowMaps[_1500 + 0u], View_SharedPointClampedSampler)), vec2(_2922, _2923), ivec2(2, 0));
                        D _3023 = _3022.x;
                        D _3024 = _3022.y;
                        D _3025 = _3022.z;
                        D _3026 = _3022.w;
                        D _3092 = (_2919 + 1.5) - _2915;
                        D _3093 = dot(vec2(_2926, _3092), vec2(_2308, _2311));
                        D _3096 = _3093 + _2311;
                        D _3097 = _2934 + _3093;
                        D _3098 = _3093 + _2308;
                        vec4 _3100 = textureGatherOffset((sampler2D(ShadowMaps[_1500 + 0u], View_SharedPointClampedSampler)), vec2(_2922, _2923), ivec2(0, 2));
                        D _3101 = _3100.x;
                        D _3102 = _3100.y;
                        D _3103 = _3100.z;
                        D _3104 = _3100.w;
                        D _3169 = dot(vec2(_3014, _3092), vec2(_2308, _2311));
                        D _3172 = _3169 + _2311;
                        D _3173 = _2934 + _3169;
                        D _3174 = _3169 + _2308;
                        vec4 _3176 = textureGatherOffset((sampler2D(ShadowMaps[_1500 + 0u], View_SharedPointClampedSampler)), vec2(_2922, _2923), ivec2(2));
                        D _3177 = _3176.x;
                        D _3178 = _3176.y;
                        D _3179 = _3176.z;
                        D _3180 = _3176.w;
                        D _3245 = 1.0 - _2920;
                        vec4 _3268 = vec4((((((_2946 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2983 + _2946) + (spvNMin(abs(_2928), 0.0) * D(int(uint(_2928 > 0.0) - uint(_2928 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3245) + ((_2945 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2983 + _2945) + (spvNMin(abs(_2936), 0.0) * D(int(uint(_2936 > 0.0) - uint(_2936 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3026 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2983 + _3026) + (spvNMin(abs(_3015), 0.0) * D(int(uint(_3015 > 0.0) - uint(_3015 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3025 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2983 + _3025) + (spvNMin(abs(_3020), 0.0) * D(int(uint(_3020 > 0.0) - uint(_3020 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2920), (((((_2943 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2983 + _2943) + (spvNMin(abs(_2931), 0.0) * D(int(uint(_2931 > 0.0) - uint(_2931 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3245) + ((_2944 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2983 + _2944) + (spvNMin(abs(_2935), 0.0) * D(int(uint(_2935 > 0.0) - uint(_2935 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3023 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2983 + _3023) + (spvNMin(abs(_3018), 0.0) * D(int(uint(_3018 > 0.0) - uint(_3018 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3024 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2983 + _3024) + (spvNMin(abs(_3019), 0.0) * D(int(uint(_3019 > 0.0) - uint(_3019 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2920), (((((_3104 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2983 + _3104) + (spvNMin(abs(_3093), 0.0) * D(int(uint(_3093 > 0.0) - uint(_3093 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3245) + ((_3103 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2983 + _3103) + (spvNMin(abs(_3098), 0.0) * D(int(uint(_3098 > 0.0) - uint(_3098 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3180 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2983 + _3180) + (spvNMin(abs(_3169), 0.0) * D(int(uint(_3169 > 0.0) - uint(_3169 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3179 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2983 + _3179) + (spvNMin(abs(_3174), 0.0) * D(int(uint(_3174 > 0.0) - uint(_3174 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2920), (((((_3101 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2983 + _3101) + (spvNMin(abs(_3096), 0.0) * D(int(uint(_3096 > 0.0) - uint(_3096 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3245) + ((_3102 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2983 + _3102) + (spvNMin(abs(_3097), 0.0) * D(int(uint(_3097 > 0.0) - uint(_3097 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3177 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2983 + _3177) + (spvNMin(abs(_3172), 0.0) * D(int(uint(_3172 > 0.0) - uint(_3172 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3178 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2983 + _3178) + (spvNMin(abs(_3173), 0.0) * D(int(uint(_3173 > 0.0) - uint(_3173 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2920));
                        _1336 = dot(_3268, vec4(1.0 - _2921, 1.0, 1.0, _2921)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        _1336 = 1.0;
                    }
                    if (_1918)
                    {
                        _1335 = _1336;
                        break;
                    }
                }
            }
            if (floatBitsToUint(TranslucentBasePass_2._m0[30u]).y == 0u)
            {
                _1335 = 1.0;
                break;
            }
            D _1376 = fma(_234, TranslucentBasePass_2._m0[35u].z, fma(_233, TranslucentBasePass_2._m0[34u].z, TranslucentBasePass_2._m0[33u].z * _232)) + TranslucentBasePass_2._m0[36u].z;
            D _1380 = fma(_234, TranslucentBasePass_2._m0[35u].w, fma(_233, TranslucentBasePass_2._m0[34u].w, TranslucentBasePass_2._m0[33u].w * _232)) + TranslucentBasePass_2._m0[36u].w;
            D _1381 = (fma(_234, TranslucentBasePass_2._m0[35u].x, fma(_233, TranslucentBasePass_2._m0[34u].x, TranslucentBasePass_2._m0[33u].x * _232)) + TranslucentBasePass_2._m0[36u].x) / _1380;
            D _1382 = (fma(_234, TranslucentBasePass_2._m0[35u].y, fma(_233, TranslucentBasePass_2._m0[34u].y, TranslucentBasePass_2._m0[33u].y * _232)) + TranslucentBasePass_2._m0[36u].y) / _1380;
            uvec4 _1386 = floatBitsToUint(TranslucentBasePass_2._m0[32u]);
            uint _1387 = _1386.x;
            uint _1388 = _1386.y;
            uint _1389 = _1386.z;
            uint _1394 = uint(int(floor(_1381)));
            uint _1395 = uint(int((-0.0) - floor(_1382)));
            if (!((int(_1395) < int(_1386.w)) && ((int(_1394) < int(_1389)) && ((int(_1394) >= int(_1387)) && (int(_1395) >= int(_1388))))))
            {
                _1335 = 1.0;
                break;
            }
            D _1463 = dFdyFine(_1381);
            D _1464 = dFdyFine(_1382);
            D _1465 = dFdyFine(_1376);
            D _1466 = dFdxFine(_1381);
            D _1467 = dFdxFine(_1382);
            D _1468 = dFdxFine(_1376);
            D _1471 = (_1467 * _1465) - (_1468 * _1464);
            D _1474 = (_1468 * _1463) - (_1466 * _1465);
            D _1477 = (_1466 * _1464) - (_1467 * _1463);
            D _1488 = 1.0 / spvNMax(abs(_1477), sqrt(((_1474 * _1474) + (_1477 * _1477)) + (_1471 * _1471)) * 0.100000001490116119384765625);
            D _1494 = D(int(uint(_1477 > 0.0) - uint(_1477 < 0.0)));
            D _1777;
            D _1779;
            if (dot(vec2(_1471, _1474), vec2(_1471, _1474)) < 1.0000000195414813782625560981111e-24)
            {
                _1777 = 0.0;
                _1779 = 0.0;
            }
            else
            {
                D _1843 = (-0.0) - _1471;
                D _1844 = (-0.0) - _1474;
                D _1848 = inversesqrt(dot(vec2(_1843, _1844), vec2(_1843, _1844)));
                _1777 = _1848 * _1843;
                _1779 = _1848 * _1844;
            }
            D _1785 = _268 + (-0.5);
            D _1793 = (((_1779 * _1785) + (_1777 * _267)) * 2.0) + (_1777 * 0.5);
            D _1794 = (((_1779 * _267) + (_1777 * _1785)) * 2.0) + (_1779 * 0.5);
            D _1800 = _1793 + (fract(_1381) * 256.0);
            D _1801 = _1794 + (fract(_1382) * 256.0);
            D _1814 = dot(vec2((floor(_1800) + 0.5) - _1800, (floor(_1801) + 0.5) - _1801), vec2(((_1471 * 256.0) * _1488) * _1494, ((_1474 * 256.0) * _1488) * _1494));
            D _1820 = (_1793 * 0.00390625) + _1381;
            D _1821 = (_1794 * 0.00390625) + _1382;
            uint _1833 = ((uint(int((-0.0) - floor(_1821))) - _1388) * (_1389 - _1387)) + (uint(int(floor(_1820))) - _1387);
            D _2247;
            D _2250;
            if ((texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowLoadedTileData, int(_1833 >> 5u)).x & (1u << (_1833 & 31u))) == 0u)
            {
                _2247 = 3.0000000054977557577780399428115e+38;
                _2250 = 0.0;
            }
            else
            {
                uvec4 _2272 = uvec4(texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileIndices, int(_1833)));
                uint _2273 = _2272.x;
                D frontier_phi_51_52_ladder;
                D frontier_phi_51_52_ladder_1;
                if (int(_2273) > int(4294967295u))
                {
                    uint _2886 = (uint(floor(fract(_1820) * 256.0)) + (_2273 << 16u)) + (uint(floor(fract(_1821) * 256.0)) << 8u);
                    uvec4 _2889 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileData, int(_2886 >> 1u));
                    uint _2890 = _2889.x;
                    D _2898 = D((((_2886 & 1u) == 0u) ? _2890 : (_2890 >> 16u)) & 65535u) * 1.525902189314365386962890625e-05;
                    D frontier_phi_51_52_ladder_73_ladder;
                    D frontier_phi_51_52_ladder_73_ladder_1;
                    if (_2898 != 1.0)
                    {
                        vec4 _3707 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthRanges, int(_2273));
                        D _3709 = _3707.y;
                        frontier_phi_51_52_ladder_73_ladder = 1.0 / _3709;
                        frontier_phi_51_52_ladder_73_ladder_1 = (_3709 * _2898) + _3707.x;
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
                _2247 = frontier_phi_51_52_ladder_1;
                _2250 = frontier_phi_51_52_ladder;
            }
            _1335 = spvNClamp(((((1.525902189314365386962890625e-05 - _1376) + _2247) + (spvNMin(abs(_1814), _2250 * 10.0) * D(int(uint(_1814 > 0.0) - uint(_1814 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0);
            break;
        }
        D _1450;
        if ((floatBitsToUint(Primitive._m0[27u]).z & 2u) == 0u)
        {
            _1450 = 1.0;
        }
        else
        {
            _1450 = View._m0[188u].y;
        }
        uvec4 _1454 = floatBitsToUint(View._m0[220u]);
        uint _1455 = _1454.y;
        uint _1458 = (_1455 != 1u) ? 4294967295u : 0u;
        uint _1775;
        if (_1455 > 1u)
        {
            D _133[4];
            _133[0u] = 0.0;
            _133[1u] = 0.0;
            _133[2u] = 0.0;
            _133[3u] = 0.0;
            uint _2232 = 0u;
            bool _2238;
            for (;;)
            {
                _2238 = _2232 < floatBitsToUint(View._m0[220u]).y;
                if (_2238)
                {
                    uint _2837 = _2232 + 237u;
                    D _2851 = View._m0[_2837].x - View._m0[75u].x;
                    D _2852 = View._m0[_2837].y - View._m0[75u].y;
                    D _2853 = View._m0[_2837].z - View._m0[75u].z;
                    D _2854 = dot(vec3(_2851, _2852, _2853), vec3(_240, _241, _242));
                    D _2861 = dot(vec3(_2851, _2852, _2853), vec3(_2851, _2852, _2853)) - (View._m0[_2837].w * View._m0[_2837].w);
                    D _2863 = (_2854 * _2854) - _2861;
                    D _3475;
                    if ((_2861 < 0.0) && (!(_2863 < 0.0)))
                    {
                        D _3469 = sqrt(_2863);
                        _3475 = spvNMin(abs(_3469 + _2854), abs(_2854 - _3469));
                    }
                    else
                    {
                        _3475 = 0.0;
                    }
                    _133[_2232] = _3475;
                }
                uint _2233 = _2232 + 1u;
                if (_2233 == 4u)
                {
                    break;
                }
                else
                {
                    _2232 = _2233;
                    continue;
                }
            }
            D _3486 = (_267 * 0.99989998340606689453125) * dot(vec4(_133[0u], _133[1u], _133[2u], _133[3u]), vec4(1.0));
            uint frontier_phi_32_83_ladder;
            if (_133[0u] > _3486)
            {
                frontier_phi_32_83_ladder = 0u;
            }
            else
            {
                D _3844 = _133[1u] + _133[0u];
                uint frontier_phi_32_83_ladder_94_ladder;
                if (_3844 > _3486)
                {
                    frontier_phi_32_83_ladder_94_ladder = 1u;
                }
                else
                {
                    D _3928 = _3844 + _133[2u];
                    uint frontier_phi_32_83_ladder_94_ladder_102_ladder;
                    if (_3928 > _3486)
                    {
                        frontier_phi_32_83_ladder_94_ladder_102_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder;
                        if ((_3928 + _133[3u]) > _3486)
                        {
                            frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder = _1458;
                        }
                        frontier_phi_32_83_ladder_94_ladder_102_ladder = frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder;
                    }
                    frontier_phi_32_83_ladder_94_ladder = frontier_phi_32_83_ladder_94_ladder_102_ladder;
                }
                frontier_phi_32_83_ladder = frontier_phi_32_83_ladder_94_ladder;
            }
            _1775 = frontier_phi_32_83_ladder;
        }
        else
        {
            _1775 = _1458;
        }
        D _2239;
        if (_1775 == 4294967295u)
        {
            _2239 = _1450;
        }
        else
        {
            _2239 = View._m0[_1775 + 241u].x * _1450;
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
        if (_2239 > 0.0)
        {
            D _2870 = spvNClamp((TranslucentBasePass_2._m0[7u].x * _105) + TranslucentBasePass_2._m0[7u].y, 0.0, 1.0);
            D _2874 = ((_2870 * _2870) * (1.0 - _1335)) + _1335;
            D frontier_phi_3_49_ladder_72_ladder;
            D frontier_phi_3_49_ladder_72_ladder_1;
            D frontier_phi_3_49_ladder_72_ladder_2;
            D frontier_phi_3_49_ladder_72_ladder_3;
            D frontier_phi_3_49_ladder_72_ladder_4;
            D frontier_phi_3_49_ladder_72_ladder_5;
            D frontier_phi_3_49_ladder_72_ladder_6;
            D frontier_phi_3_49_ladder_72_ladder_7;
            D frontier_phi_3_49_ladder_72_ladder_8;
            if (_2874 > 0.0)
            {
                D _3488 = dot(vec3(_425, _426, _427), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3491 = spvNMax(0.0, _3488);
                D _3492 = dot(vec3(_243, _245, _246), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3498 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3492 * 2.0) + 2.0));
                D _3501 = spvNClamp(_3498 * (_539 + _3488), 0.0, 1.0);
                D _3514 = sqrt(spvNMax(0.0, 1.0 - (_566 * 0.444444477558135986328125)));
                D _3518 = (_545 * 0.666666686534881591796875) - (_3514 * _425);
                D _3519 = (_546 * 0.666666686534881591796875) - (_3514 * _426);
                D _3520 = (_547 * 0.666666686534881591796875) - (_3514 * _427);
                D _3524 = inversesqrt(dot(vec3(_3518, _3519, _3520), vec3(_3518, _3519, _3520)));
                D _3531 = dot(vec3((-0.0) - (_3524 * _3518), (-0.0) - (_3524 * _3519), (-0.0) - (_3524 * _3520)), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3534 = _694 * _694;
                D _3535 = _3534 * _3534;
                D _3539 = ((_3501 * _3501) * (_3535 + (-1.0))) + 1.0;
                D _3545 = (_3491 * 2.0) * _610;
                D _3550 = 1.0 - spvNMax(9.9999997473787516355514526367188e-06, spvNMin(_3498 * (_3492 + 1.0), 1.0));
                D _3551 = _3550 * _3550;
                D _3553 = (_3551 * _3551) * _3550;
                D _3558 = spvNMin(dot(vec3(_523, _524, _525), vec3(16.666667938232421875)), 1.0);
                D _3571 = spvNMax(0.039999999105930328369140625, _694);
                D _3584 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_3571 * _3491) + 0.02669160068035125732421875) / (_3491 + 0.4664950072765350341796875)) * exp2(((1.0 / _3571) * _3491) * log2(_3571)), 0.0, 1.0));
                D _3585 = 1.0 - _3491;
                D _3586 = _3585 * _3585;
                D _3598 = ((_3586 * _3586) * _3585) * exp2(log2((exp2((_3571 * 4.7702999114990234375) * log2(_3491)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _3571);
                D _3601 = (1.0 / _3584) * (1.0 - _3584);
                D _3605 = (_3601 * _523) + 1.0;
                D _3606 = (_3601 * _524) + 1.0;
                D _3607 = (_3601 * _525) + 1.0;
                D _3608 = _3584 - _3598;
                D _3622 = spvNClamp(1.0 - dot(vec3(_3605 * ((_3608 * _523) + _3598), _3606 * ((_3608 * _524) + _3598), _3607 * ((_3608 * _525) + _3598)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                D _3625 = (((_3535 * 0.3183098733425140380859375) * _3491) * (1.0 / (_3539 * _3539))) * (0.5 / ((_3534 * ((_610 + _3491) - _3545)) + _3545));
                D _3626 = _3491 * 0.3183098733425140380859375;
                D _3640 = (((_3531 * _3531) + 1.0) * 0.0323704965412616729736328125) * exp2(log2(spvNMax(0.0, (_3531 * 1.2000000476837158203125) + 1.36000001430511474609375)) * (-1.5));
                D _3641 = spvNMin(1.0, _451);
                D _3643 = (_451 + 1.0) - _3641;
                D _3644 = _3643 * _3643;
                D _3647 = 1.0 - ((_3644 * _3644) * _3643);
                D _3648 = _3647 * _3647;
                D _3653 = ((_3648 * _3648) * (_3647 * (_451 - _3641))) + _3641;
                D _3656 = sqrt(spvNMax(0.0, 1.0 - _3653));
                D _3661 = 1.0 - spvNClamp((_694 * 3.5) + (-0.5), 0.0, 1.0);
                D _3662 = _3661 * _3661;
                D _3672 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_725 * _3656) * spvNClamp(1.0 - ((_3662 * _3662) * _3661), 0.0, 1.0))) * _3491, 0.0, 1.0);
                D _3677 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _3656)) * _3491, 0.0, 1.0);
                D _3679 = spvNMin(_2874, _3672 * _3672);
                D _3680 = spvNMin(_2874, _3677 * _3677);
                D _3681 = spvNMin(_2874, _3653);
                D _3682 = _2239 * TranslucentBasePass_2._m0[4u].x;
                D _3683 = _2239 * TranslucentBasePass_2._m0[4u].y;
                D _3684 = _2239 * TranslucentBasePass_2._m0[4u].z;
                frontier_phi_3_49_ladder_72_ladder = (_3640 * _3684) * _3681;
                frontier_phi_3_49_ladder_72_ladder_1 = (((_3682 * _475) * _3626) * _3622) * _3680;
                frontier_phi_3_49_ladder_72_ladder_2 = (((_3683 * _476) * _3626) * _3622) * _3680;
                frontier_phi_3_49_ladder_72_ladder_3 = (((_3684 * _477) * _3626) * _3622) * _3680;
                frontier_phi_3_49_ladder_72_ladder_4 = (((_3625 * _3682) * spvNClamp(((_3558 - _523) * _3553) + _523, 0.0, 1.0)) * _3605) * _3679;
                frontier_phi_3_49_ladder_72_ladder_5 = (((_3625 * _3683) * spvNClamp(((_3558 - _524) * _3553) + _524, 0.0, 1.0)) * _3606) * _3679;
                frontier_phi_3_49_ladder_72_ladder_6 = (((_3625 * _3684) * spvNClamp(((_3558 - _525) * _3553) + _525, 0.0, 1.0)) * _3607) * _3679;
                frontier_phi_3_49_ladder_72_ladder_7 = (_3640 * _3682) * _3681;
                frontier_phi_3_49_ladder_72_ladder_8 = (_3640 * _3683) * _3681;
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
        _826 = frontier_phi_3_49_ladder_1;
        _828 = frontier_phi_3_49_ladder_2;
        _830 = frontier_phi_3_49_ladder_3;
        _832 = frontier_phi_3_49_ladder_4;
        _834 = frontier_phi_3_49_ladder_5;
        _836 = frontier_phi_3_49_ladder_6;
        _838 = frontier_phi_3_49_ladder_7;
        _840 = frontier_phi_3_49_ladder_8;
        _842 = frontier_phi_3_49_ladder;
    }
    uvec4 _846 = floatBitsToUint(TranslucentBasePass_2._m0[0u]);
    uint _847 = _846.x;
    uint _852 = min(min(texelFetch(TranslucentBasePass_Shared_Forward_NumCulledLightsGrid, int(0u)).x, _847), _847);
    D _859;
    D _861;
    D _863;
    D _865;
    D _867;
    D _869;
    D _871;
    D _873;
    D _875;
    D _877;
    D _879;
    D _881;
    D _883;
    D _885;
    D _887;
    if (_852 == 0u)
    {
        _859 = _826;
        _861 = _828;
        _863 = _830;
        _865 = _832;
        _867 = _834;
        _869 = _836;
        _871 = _838;
        _873 = _840;
        _875 = _842;
        _877 = 0.0;
        _879 = 0.0;
        _881 = 0.0;
        _883 = 0.0;
        _885 = 0.0;
        _887 = 0.0;
    }
    else
    {
        D _860;
        D _862;
        D _864;
        D _866;
        D _868;
        D _870;
        D _872;
        D _874;
        D _876;
        D _878;
        D _880;
        D _882;
        D _884;
        D _886;
        D _888;
        D _1250 = _826;
        D _1251 = _828;
        D _1252 = _830;
        D _1253 = _832;
        D _1254 = _834;
        D _1255 = _836;
        D _1256 = _838;
        D _1257 = _840;
        D _1258 = _842;
        D _1259 = 0.0;
        D _1260 = 0.0;
        D _1261 = 0.0;
        D _1262 = 0.0;
        D _1263 = 0.0;
        D _1264 = 0.0;
        uint _1265 = 0u;
        D _1269;
        D _1270;
        D _1271;
        D _1272;
        D _1274;
        D _1275;
        D _1276;
        D _1278;
        D _1279;
        D _1280;
        uint _1282;
        D _1284;
        D _1285;
        D _1287;
        D _1288;
        D _1289;
        D _1291;
        D _1292;
        uint _1294;
        D _1297;
        D _1298;
        D _1299;
        D _1300;
        uint _1303;
        D _1305;
        D _1306;
        D _1307;
        D _1308;
        D _1311;
        D _1312;
        D _1313;
        D _1314;
        D _1317;
        D _1318;
        D _1319;
        D _1320;
        D _1323;
        D _1324;
        D _1325;
        D _1326;
        bool _1329;
        bool _1330;
        bool _1334;
        for (;;)
        {
            vec4 _1268 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(0u));
            _1269 = _1268.x;
            _1270 = _1268.y;
            _1271 = _1268.z;
            _1272 = _1268.w;
            vec4 _1273 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(1u));
            _1274 = _1273.x;
            _1275 = _1273.y;
            _1276 = _1273.z;
            vec4 _1277 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(2u));
            _1278 = _1277.x;
            _1279 = _1277.y;
            _1280 = _1277.z;
            _1282 = floatBitsToUint(_1277.w);
            vec4 _1283 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(3u));
            _1284 = _1283.x;
            _1285 = _1283.y;
            vec4 _1286 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(4u));
            _1287 = _1286.x;
            _1288 = _1286.y;
            _1289 = _1286.z;
            vec4 _1290 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(5u));
            _1291 = _1290.x;
            _1292 = _1290.y;
            _1294 = floatBitsToUint(_1290.z);
            vec4 _1296 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(6u));
            _1297 = _1296.x;
            _1298 = _1296.y;
            _1299 = _1296.z;
            _1300 = _1296.w;
            _1303 = floatBitsToUint(texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(7u)).x);
            vec4 _1304 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(8u));
            _1305 = _1304.x;
            _1306 = _1304.y;
            _1307 = _1304.z;
            _1308 = _1304.w;
            vec4 _1310 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(9u));
            _1311 = _1310.x;
            _1312 = _1310.y;
            _1313 = _1310.z;
            _1314 = _1310.w;
            vec4 _1316 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(10u));
            _1317 = _1316.x;
            _1318 = _1316.y;
            _1319 = _1316.z;
            _1320 = _1316.w;
            vec4 _1322 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(11u));
            _1323 = _1322.x;
            _1324 = _1322.y;
            _1325 = _1322.z;
            _1326 = _1322.w;
            _1329 = (_1282 & 131072u) != 0u;
            _1330 = _1284 > (-2.0);
            _1334 = (_1282 & 16384u) == 0u;
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
            if (_1334)
            {
                D _1728;
                if (_1329)
                {
                    uint _1693 = _1303 + 0u;
                    uvec2 _1696 = uvec2(textureSize(ShadowMaps[(_1693)], int(0u)));
                    D _1698 = D(int(_1696.x));
                    D _1700 = D(int(_1696.y));
                    D _1701 = 1.0 / _1698;
                    D _1702 = 1.0 / _1700;
                    D _1714 = fma(_234, _1319, fma(_233, _1313, _1307 * _232)) + _1325;
                    D _1718 = fma(_234, _1320, fma(_233, _1314, _1308 * _232)) + _1326;
                    D _1719 = (fma(_234, _1317, fma(_233, _1311, _1305 * _232)) + _1323) / _1718;
                    D _1720 = (fma(_234, _1318, fma(_233, _1312, _1306 * _232)) + _1324) / _1718;
                    D frontier_phi_28_27_ladder;
                    if ((_1720 <= _1300) && ((_1719 <= _1299) && ((_1719 >= _1297) && (_1720 >= _1298))))
                    {
                        D _2116 = dFdyFine(_1719);
                        D _2117 = dFdyFine(_1720);
                        D _2118 = dFdyFine(_1714);
                        D _2119 = dFdxFine(_1719);
                        D _2120 = dFdxFine(_1720);
                        D _2121 = dFdxFine(_1714);
                        D _2124 = (_2120 * _2118) - (_2121 * _2117);
                        D _2127 = (_2121 * _2116) - (_2119 * _2118);
                        D _2130 = (_2119 * _2117) - (_2120 * _2116);
                        D _2140 = 1.0 / spvNMax(abs(_2130), sqrt(((_2127 * _2127) + (_2130 * _2130)) + (_2124 * _2124)) * 0.100000001490116119384765625);
                        D _2146 = D(int(uint(_2130 > 0.0) - uint(_2130 < 0.0)));
                        D _2147 = _2124 * _1701;
                        D _2149 = (_2147 * _2140) * _2146;
                        D _2150 = _2127 * _1702;
                        D _2152 = (_2150 * _2140) * _2146;
                        D _2432;
                        D _2434;
                        if (dot(vec2(_2124, _2127), vec2(_2124, _2127)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2432 = 0.0;
                            _2434 = 0.0;
                        }
                        else
                        {
                            D _2775 = (-0.0) - _2124;
                            D _2776 = (-0.0) - _2127;
                            D _2780 = inversesqrt(dot(vec2(_2775, _2776), vec2(_2775, _2776)));
                            _2432 = _2780 * _2775;
                            _2434 = _2780 * _2776;
                        }
                        D _2436 = _268 + (-0.5);
                        D _2441 = _267 + 0.5;
                        D _2444 = ((_2434 * _2436) + (_1719 * _1698)) + (_2432 * _2441);
                        D _2447 = ((_2432 * _2436) + (_1720 * _1700)) + (_2434 * _2441);
                        D _2448 = _2444 + (-0.5);
                        D _2449 = _2447 + (-0.5);
                        D _2450 = trunc(_2448);
                        D _2451 = trunc(_2449);
                        D _2452 = _2448 - _2450;
                        D _2453 = _2449 - _2451;
                        D _2454 = _2450 * _1701;
                        D _2455 = _2451 * _1702;
                        D _2458 = (_2450 + (-0.5)) - _2444;
                        D _2459 = (_2451 + (-0.5)) - _2447;
                        D _2460 = dot(vec2(_2458, _2459), vec2(_2149, _2152));
                        D _2463 = _2460 + _2152;
                        D _2466 = _2146 * (_2140 * (_2150 + _2147));
                        D _2467 = _2466 + _2460;
                        D _2468 = _2460 + _2149;
                        vec4 _2472 = textureGather((sampler2D(ShadowMaps[_1693], View_SharedPointClampedSampler)), vec2(_2454, _2455));
                        D _2513 = 1.525902189314365386962890625e-05 - _1714;
                        D _2536 = (_2450 + 1.5) - _2444;
                        D _2537 = dot(vec2(_2536, _2459), vec2(_2149, _2152));
                        D _2540 = _2537 + _2152;
                        D _2541 = _2466 + _2537;
                        D _2542 = _2537 + _2149;
                        vec4 _2546 = textureGatherOffset((sampler2D(ShadowMaps[_1693], View_SharedPointClampedSampler)), vec2(_2454, _2455), ivec2(2, 0));
                        D _2610 = (_2451 + 1.5) - _2447;
                        D _2611 = dot(vec2(_2458, _2610), vec2(_2149, _2152));
                        D _2614 = _2611 + _2152;
                        D _2615 = _2466 + _2611;
                        D _2616 = _2611 + _2149;
                        vec4 _2618 = textureGatherOffset((sampler2D(ShadowMaps[_1693], View_SharedPointClampedSampler)), vec2(_2454, _2455), ivec2(0, 2));
                        D _2680 = dot(vec2(_2536, _2610), vec2(_2149, _2152));
                        D _2683 = _2680 + _2152;
                        D _2684 = _2466 + _2680;
                        D _2685 = _2680 + _2149;
                        vec4 _2687 = textureGatherOffset((sampler2D(ShadowMaps[_1693], View_SharedPointClampedSampler)), vec2(_2454, _2455), ivec2(2));
                        D _2749 = 1.0 - _2452;
                        vec4 _2772 = vec4((((spvNClamp((((_2513 + _2472.w) + (spvNMin(abs(_2460), 0.0) * D(int(uint(_2460 > 0.0) - uint(_2460 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2749) + spvNClamp((((_2513 + _2472.z) + (spvNMin(abs(_2468), 0.0) * D(int(uint(_2468 > 0.0) - uint(_2468 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2513 + _2546.w) + (spvNMin(abs(_2537), 0.0) * D(int(uint(_2537 > 0.0) - uint(_2537 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2513 + _2546.z) + (spvNMin(abs(_2542), 0.0) * D(int(uint(_2542 > 0.0) - uint(_2542 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2452), (((spvNClamp((((_2513 + _2472.x) + (spvNMin(abs(_2463), 0.0) * D(int(uint(_2463 > 0.0) - uint(_2463 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2749) + spvNClamp((((_2513 + _2472.y) + (spvNMin(abs(_2467), 0.0) * D(int(uint(_2467 > 0.0) - uint(_2467 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2513 + _2546.x) + (spvNMin(abs(_2540), 0.0) * D(int(uint(_2540 > 0.0) - uint(_2540 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2513 + _2546.y) + (spvNMin(abs(_2541), 0.0) * D(int(uint(_2541 > 0.0) - uint(_2541 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2452), (((spvNClamp((((_2513 + _2618.w) + (spvNMin(abs(_2611), 0.0) * D(int(uint(_2611 > 0.0) - uint(_2611 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2749) + spvNClamp((((_2513 + _2618.z) + (spvNMin(abs(_2616), 0.0) * D(int(uint(_2616 > 0.0) - uint(_2616 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2513 + _2687.w) + (spvNMin(abs(_2680), 0.0) * D(int(uint(_2680 > 0.0) - uint(_2680 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2513 + _2687.z) + (spvNMin(abs(_2685), 0.0) * D(int(uint(_2685 > 0.0) - uint(_2685 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2452), (((spvNClamp((((_2513 + _2618.x) + (spvNMin(abs(_2614), 0.0) * D(int(uint(_2614 > 0.0) - uint(_2614 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2749) + spvNClamp((((_2513 + _2618.y) + (spvNMin(abs(_2615), 0.0) * D(int(uint(_2615 > 0.0) - uint(_2615 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2513 + _2687.x) + (spvNMin(abs(_2683), 0.0) * D(int(uint(_2683 > 0.0) - uint(_2683 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2513 + _2687.y) + (spvNMin(abs(_2684), 0.0) * D(int(uint(_2684 > 0.0) - uint(_2684 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2452));
                        frontier_phi_28_27_ladder = dot(_2772, vec4(1.0 - _2453, 1.0, 1.0, _2453)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        frontier_phi_28_27_ladder = 1.0;
                    }
                    _1728 = frontier_phi_28_27_ladder;
                }
                else
                {
                    _1728 = 1.0;
                }
                D _1734 = _1269 - _232;
                D _1735 = _1270 - _233;
                D _1736 = _1271 - _234;
                D _1737 = dot(vec3(_1734, _1735, _1736), vec3(_1734, _1735, _1736));
                D _2161;
                D _2162;
                D _2163;
                if (_1737 > 9.9999997473787516355514526367188e-05)
                {
                    D _2157 = inversesqrt(_1737);
                    _2161 = _2157 * _1734;
                    _2162 = _2157 * _1735;
                    _2163 = _2157 * _1736;
                }
                else
                {
                    _2161 = 0.0;
                    _2162 = 0.0;
                    _2163 = 0.0;
                }
                D _2164 = _1291 * _1291;
                D _2168 = (_1272 * _1272) * _1737;
                D _2171 = spvNClamp(1.0 - (_2168 * _2168), 0.0, 1.0);
                D _2788;
                if (_1330)
                {
                    D _2786 = spvNClamp((dot(vec3(_2161, _2162, _2163), vec3(_1278, _1279, _1280)) - _1284) * _1285, 0.0, 1.0);
                    _2788 = _2786 * _2786;
                }
                else
                {
                    _2788 = 1.0;
                }
                D _2789 = ((_2171 * _2171) * D(_1737 >= _2164)) * _2788;
                D _3332;
                D _3334;
                D _3336;
                if ((_1282 & 262144u) == 0u)
                {
                    _3332 = 1.0;
                    _3334 = 1.0;
                    _3336 = 1.0;
                }
                else
                {
                    D _3339 = (-0.0) - _1279;
                    D _3340 = (-0.0) - _1280;
                    D _3341 = (-0.0) - _1278;
                    D _3351 = (-0.0) - _2161;
                    D _3352 = (-0.0) - _2162;
                    D _3353 = (-0.0) - _2163;
                    D _3356 = fma(_3340, _3353, fma(_3339, _3352, _2161 * _1278));
                    D _3359 = fma(_1289, _3353, fma(_1288, _3352, _1287 * _3351));
                    D _3367 = atan(((-0.0) - _3359) / ((-0.0) - _3356));
                    bool _3372 = _3356 > (-0.0);
                    bool _3373 = _3356 == (-0.0);
                    bool _3374 = _3359 <= (-0.0);
                    bool _3375 = _3359 > (-0.0);
                    vec4 _3397 = texture((sampler2D(ForwardLightProfileTextures[_1294 + 0u], View_SharedBilinearWrappedSampler)), vec2(fract((_3373 && _3374) ? 1.25 : ((_3373 && _3375) ? 0.75 : ((((_3372 && _3375) ? (_3367 + (-3.1415927410125732421875)) : ((_3372 && _3374) ? (_3367 + 3.1415927410125732421875) : _3367)) * 0.15915493667125701904296875) + 1.0))), (asin((-0.0) - fma((_1288 * _3341) - (_1287 * _3339), _3353, fma((_1287 * _3340) - (_1289 * _3341), _3352, ((_1289 * _3339) - (_1288 * _3340)) * _3351))) * 0.3183098733425140380859375) + 0.5));
                    _3332 = _3397.x;
                    _3334 = _3397.y;
                    _3336 = _3397.z;
                }
                D _3795;
                D _3797;
                D _3799;
                D _3801;
                D _3803;
                D _3805;
                D _3807;
                D _3809;
                D _3811;
                for (;;)
                {
                    if (_2789 > 0.0)
                    {
                        D _3920;
                        if (_1329)
                        {
                            if (!(_1728 > 0.0))
                            {
                                _3795 = 0.0;
                                _3797 = 0.0;
                                _3799 = 0.0;
                                _3801 = 0.0;
                                _3803 = 0.0;
                                _3805 = 0.0;
                                _3807 = 0.0;
                                _3809 = 0.0;
                                _3811 = 0.0;
                                break;
                            }
                            _3920 = _1728;
                        }
                        else
                        {
                            _3920 = 1.0;
                        }
                        D _3922 = spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1737));
                        D _3923 = 1.0 / _3922;
                        D _3924 = dot(vec3(_425, _426, _427), vec3(_2161, _2162, _2163));
                        D _3945;
                        if (_1291 > 0.0)
                        {
                            D _3942 = sqrt(spvNClamp(_2164 * _3923, 0.0, 1.0));
                            D frontier_phi_107_106_ladder;
                            if (_3942 > spvNMax(9.9999997473787516355514526367188e-06, _3924))
                            {
                                D _3964 = spvNMax((-0.0) - _3942, _3924) + _3942;
                                frontier_phi_107_106_ladder = (_3964 * _3964) * (0.25 / _3942);
                            }
                            else
                            {
                                frontier_phi_107_106_ladder = _3924;
                            }
                            _3945 = frontier_phi_107_106_ladder;
                        }
                        else
                        {
                            _3945 = _3924;
                        }
                        D _4006;
                        D _4007;
                        D _3947;
                        D _3949;
                        D _3953;
                        D _3954;
                        bool _3957;
                        for (;;)
                        {
                            _3947 = spvNMax(0.0, _3945);
                            _3949 = _694 * _694;
                            _3953 = spvNClamp(((1.0 - _3949) * _1291) * inversesqrt(_3922), 0.0, 1.0);
                            _3954 = dot(vec3(_243, _245, _246), vec3(_2161, _2162, _2163));
                            _3957 = _3953 > 0.0;
                            D _3975;
                            D _3977;
                            if (_3957)
                            {
                                D _3970 = sqrt(spvNMax(0.0, 1.0 - (_3953 * _3953)));
                                D _3973 = ((_3924 * 2.0) * _539) - _3954;
                                if (!(!(_3973 >= _3970)))
                                {
                                    _4006 = _551;
                                    _4007 = 1.0;
                                    break;
                                }
                                D _3995 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, 1.0 - (_3973 * _3973))) * _3953;
                                _3975 = (_3995 * (((_565 * 2.0) + (-1.0)) - (_3973 * _3954))) + (_3970 * _3954);
                                _3977 = (_3995 * (_539 - (_3973 * _3924))) + (_3970 * _3924);
                            }
                            else
                            {
                                _3975 = _3954;
                                _3977 = _3924;
                            }
                            D _3982 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3975 * 2.0) + 2.0));
                            _4006 = spvNMin(_3982 * (_3975 + 1.0), 1.0);
                            _4007 = spvNClamp(_3982 * (_3977 + _539), 0.0, 1.0);
                            break;
                        }
                        D _4008 = spvNMax(9.9999997473787516355514526367188e-06, _4006);
                        D _4015 = sqrt(spvNMax(0.0, 1.0 - (_566 * 0.444444477558135986328125)));
                        D _4019 = (_545 * 0.666666686534881591796875) - (_4015 * _425);
                        D _4020 = (_546 * 0.666666686534881591796875) - (_4015 * _426);
                        D _4021 = (_547 * 0.666666686534881591796875) - (_4015 * _427);
                        D _4025 = inversesqrt(dot(vec3(_4019, _4020, _4021), vec3(_4019, _4020, _4021)));
                        D _4032 = dot(vec3((-0.0) - (_4025 * _4019), (-0.0) - (_4025 * _4020), (-0.0) - (_4025 * _4021)), vec3(_2161, _2162, _2163));
                        D _4035 = _3949 * _3949;
                        D _4049 = ((_4007 * _4007) * (_4035 + (-1.0))) + 1.0;
                        D _4055 = (_3947 * 2.0) * _610;
                        D _4060 = 1.0 - _4008;
                        D _4061 = _4060 * _4060;
                        D _4063 = (_4061 * _4061) * _4060;
                        D _4067 = spvNMin(dot(vec3(_523, _524, _525), vec3(16.666667938232421875)), 1.0);
                        D _4080 = spvNMax(0.039999999105930328369140625, _694);
                        D _4093 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_4080 * _3947) + 0.02669160068035125732421875) / (_3947 + 0.4664950072765350341796875)) * exp2(((1.0 / _4080) * _3947) * log2(_4080)), 0.0, 1.0));
                        D _4094 = 1.0 - _3947;
                        D _4095 = _4094 * _4094;
                        D _4107 = ((_4095 * _4095) * _4094) * exp2(log2((exp2((_4080 * 4.7702999114990234375) * log2(_3947)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _4080);
                        D _4110 = (1.0 / _4093) * (1.0 - _4093);
                        D _4114 = (_4110 * _523) + 1.0;
                        D _4115 = (_4110 * _524) + 1.0;
                        D _4116 = (_4110 * _525) + 1.0;
                        D _4117 = _4093 - _4107;
                        D _4131 = spvNClamp(1.0 - dot(vec3(_4114 * ((_4117 * _523) + _4107), _4115 * ((_4117 * _524) + _4107), _4116 * ((_4117 * _525) + _4107)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                        D _4135 = ((((_4035 * 0.3183098733425140380859375) * _3947) * (1.0 / (_4049 * _4049))) * (_3957 ? ((1.0 / ((((_3953 * 0.25) * (_3953 + (_3949 * 3.0))) * (1.0 / _4008)) + _4035)) * _4035) : 1.0)) * (0.5 / ((_3949 * ((_610 + _3947) - _4055)) + _4055));
                        D _4136 = _3947 * 0.3183098733425140380859375;
                        D _4146 = (((_4032 * _4032) + 1.0) * 0.0323704965412616729736328125) * exp2(log2(spvNMax(0.0, (_4032 * 1.2000000476837158203125) + 1.36000001430511474609375)) * (-1.5));
                        D _4147 = spvNMin(1.0, _451);
                        D _4149 = (_451 + 1.0) - _4147;
                        D _4150 = _4149 * _4149;
                        D _4153 = 1.0 - ((_4150 * _4150) * _4149);
                        D _4154 = _4153 * _4153;
                        D _4159 = ((_4154 * _4154) * (_4153 * (_451 - _4147))) + _4147;
                        D _4162 = sqrt(spvNMax(0.0, 1.0 - _4159));
                        D _4166 = 1.0 - spvNClamp((_694 * 3.5) + (-0.5), 0.0, 1.0);
                        D _4167 = _4166 * _4166;
                        D _4177 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_725 * _4162) * spvNClamp(1.0 - ((_4167 * _4167) * _4166), 0.0, 1.0))) * _3947, 0.0, 1.0);
                        D _4182 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _4162)) * _3947, 0.0, 1.0);
                        D _4184 = spvNMin(_3920, _4177 * _4177);
                        D _4185 = spvNMin(_3920, _4182 * _4182);
                        D _4186 = spvNMin(_3920, _4159);
                        D _4190 = (_2789 * _1274) * _3332;
                        D _4191 = (_2789 * _1275) * _3334;
                        D _4192 = (_2789 * _1276) * _3336;
                        D _4193 = _3923 * _4190;
                        D _4197 = _3923 * _4191;
                        D _4201 = _3923 * _4192;
                        _3795 = ((((_4190 * _475) * _3923) * _4136) * _4131) * _4185;
                        _3797 = ((((_4191 * _476) * _3923) * _4136) * _4131) * _4185;
                        _3799 = ((((_4192 * _477) * _3923) * _4136) * _4131) * _4185;
                        _3801 = (((_4193 * spvNClamp(((_4067 - _523) * _4063) + _523, 0.0, 1.0)) * _4135) * _4114) * _4184;
                        _3803 = (((_4197 * _4135) * spvNClamp(((_4067 - _524) * _4063) + _524, 0.0, 1.0)) * _4115) * _4184;
                        _3805 = (((_4201 * _4135) * spvNClamp(((_4067 - _525) * _4063) + _525, 0.0, 1.0)) * _4116) * _4184;
                        _3807 = (_4193 * _4146) * _4186;
                        _3809 = (_4197 * _4146) * _4186;
                        _3811 = (_4201 * _4146) * _4186;
                        break;
                    }
                    else
                    {
                        _3795 = 0.0;
                        _3797 = 0.0;
                        _3799 = 0.0;
                        _3801 = 0.0;
                        _3803 = 0.0;
                        _3805 = 0.0;
                        _3807 = 0.0;
                        _3809 = 0.0;
                        _3811 = 0.0;
                        break;
                    }
                }
                frontier_phi_47_pred = _1260;
                frontier_phi_47_pred_1 = _3795 + _1250;
                frontier_phi_47_pred_2 = _3797 + _1251;
                frontier_phi_47_pred_3 = _3799 + _1252;
                frontier_phi_47_pred_4 = _3801 + _1253;
                frontier_phi_47_pred_5 = _3803 + _1254;
                frontier_phi_47_pred_6 = _3805 + _1255;
                frontier_phi_47_pred_7 = _3807 + _1256;
                frontier_phi_47_pred_8 = _3809 + _1257;
                frontier_phi_47_pred_9 = _3811 + _1258;
                frontier_phi_47_pred_10 = _1259;
                frontier_phi_47_pred_11 = _1261;
                frontier_phi_47_pred_12 = _1262;
                frontier_phi_47_pred_13 = _1263;
                frontier_phi_47_pred_14 = _1264;
            }
            else
            {
                D _1433 = _1269 - _232;
                D _1434 = _1270 - _233;
                D _1435 = _1271 - _234;
                D _1436 = dot(vec3(_1433, _1434, _1435), vec3(_1433, _1434, _1435));
                D _1440 = (_1272 * _1272) * _1436;
                D _1441 = _1440 * _1440;
                D _1442 = _1441 * _1441;
                D _1445 = spvNClamp(1.0 - (_1442 * _1442), 0.0, 1.0);
                D _1446 = _1445 * _1445;
                D _1447 = _1446 * _1446;
                D _1448 = _1447 * _1447;
                D _1752;
                D _1754;
                D _1756;
                D _1758;
                D _1760;
                D _1762;
                if (_1448 > 0.0)
                {
                    D _1744 = dot(vec3(_240, _241, _242), vec3(_425, _426, _427)) * 2.0;
                    D _1748 = _240 - (_1744 * _425);
                    D _1749 = _241 - (_1744 * _426);
                    D _1750 = _242 - (_1744 * _427);
                    D _3399;
                    D _3400;
                    D _3401;
                    D _3402;
                    D _3403;
                    D _3404;
                    D _3405;
                    D _3406;
                    D _3407;
                    D _3408;
                    D _3409;
                    if (_1292 == 0.0)
                    {
                        D _2794;
                        D _2795;
                        D _2796;
                        if (_1436 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2790 = inversesqrt(_1436);
                            _2794 = _2790 * _1433;
                            _2795 = _2790 * _1434;
                            _2796 = _2790 * _1435;
                        }
                        else
                        {
                            _2794 = 0.0;
                            _2795 = 0.0;
                            _2796 = 0.0;
                        }
                        D _2799 = 1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1436));
                        _3399 = _2799;
                        _3400 = (_1291 * _1291) * _2799;
                        _3401 = _2794;
                        _3402 = _2795;
                        _3403 = _2796;
                        _3404 = _2794;
                        _3405 = _2795;
                        _3406 = _2796;
                        _3407 = _2794;
                        _3408 = _2795;
                        _3409 = _2796;
                    }
                    else
                    {
                        D _2175 = _1292 * 0.5;
                        D _2176 = _2175 * _1278;
                        D _2177 = _2175 * _1279;
                        D _2178 = _2175 * _1280;
                        D _2179 = _1433 - _2176;
                        D _2180 = _1434 - _2177;
                        D _2181 = _1435 - _2178;
                        D _2182 = _2176 + _1433;
                        D _2183 = _2177 + _1434;
                        D _2184 = _2178 + _1435;
                        D _2192 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2179, _2180, _2181), vec3(_2179, _2180, _2181))));
                        D _2194 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2182, _2183, _2184), vec3(_2182, _2183, _2184))));
                        D _2195 = _2194 * _2192;
                        D _2211 = (1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(_2195, ((dot(vec3(_2179, _2180, _2181), vec3(_2182, _2183, _2184)) * 0.5) * _2195) + 0.5))) * _2195;
                        D _2213 = (_1278 * 2.0) * _2175;
                        D _2215 = (_1279 * 2.0) * _2175;
                        D _2217 = (_1280 * 2.0) * _2175;
                        D _2218 = dot(vec3(_2213, _2215, _2217), vec3(_2213, _2215, _2217));
                        D _2832;
                        D _2833;
                        D _2834;
                        if (_2218 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2802 = dot(vec3(_1748, _1749, _1750), vec3(_2213, _2215, _2217));
                            D _2818 = spvNClamp((1.0 / (_2218 - (_2802 * _2802))) * dot(vec3(_2179, _2180, _2181), vec3((_2802 * _1748) - _2213, (_2802 * _1749) - _2215, (_2802 * _1750) - _2217)), 0.0, 1.0);
                            D _2822 = (_2818 * _2213) + _2179;
                            D _2823 = (_2818 * _2215) + _2180;
                            D _2824 = (_2818 * _2217) + _2181;
                            D _2828 = inversesqrt(dot(vec3(_2822, _2823, _2824), vec3(_2822, _2823, _2824)));
                            _2832 = _2822 * _2828;
                            _2833 = _2823 * _2828;
                            _2834 = _2824 * _2828;
                        }
                        else
                        {
                            _2832 = _2179;
                            _2833 = _2180;
                            _2834 = _2181;
                        }
                        _3399 = _2211;
                        _3400 = (_1291 * _1291) * _2211;
                        _3401 = _2192 * _2179;
                        _3402 = _2192 * _2180;
                        _3403 = _2192 * _2181;
                        _3404 = _2194 * _2182;
                        _3405 = _2194 * _2183;
                        _3406 = _2194 * _2184;
                        _3407 = _2832;
                        _3408 = _2833;
                        _3409 = _2834;
                    }
                    D _3419 = _3400 + 1.0;
                    D _3424 = _3407 - _240;
                    D _3425 = _3408 - _241;
                    D _3426 = _3409 - _242;
                    D _3430 = inversesqrt(dot(vec3(_3424, _3425, _3426), vec3(_3424, _3425, _3426)));
                    D _3431 = _3430 * _3424;
                    D _3432 = _3430 * _3425;
                    D _3433 = _3430 * _3426;
                    D _3440 = spvNClamp(dot(vec3(_425, _426, _427), vec3(_3431, _3432, _3433)), 0.0, 1.0);
                    D _3441 = _694 * _694;
                    D _3447 = spvNClamp(((1.0 - _3441) * _1291) * sqrt(_3399), 0.0, 1.0);
                    D _3461 = exp2(log2(spvNClamp((((_3447 * 0.25) * (_3447 + (_3441 * 3.0))) * (1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_243, _245, _246), vec3(_3431, _3432, _3433))))) + (_3441 * _3441), 0.0, 1.0)) * 0.25);
                    D _3465 = spvNClamp(dot(vec3(_3401, _3402, _3403), vec3(_3404, _3405, _3406)), 0.0, 1.0);
                    D _3467 = _3461 * _3461;
                    D _3468 = _3467 * _3467;
                    D _3827;
                    if (_3465 < 1.0)
                    {
                        D _3818 = sqrt(spvNClamp((1.0 / (_3465 + 1.0)) * (1.0 - _3465), 0.0, 1.0));
                        _3827 = (1.0 / spvNClamp(((_3818 * 0.25) * (_3818 + (_3467 * 3.0))) + _3468, 0.0, 1.0)) * _3468;
                    }
                    else
                    {
                        _3827 = 1.0;
                    }
                    D _3831 = ((_3440 * _3440) * (_3468 + (-1.0))) + 1.0;
                    D _3834 = spvNMax(0.0, (((dot(vec3(_425, _426, _427), vec3(_3404, _3405, _3406)) + dot(vec3(_425, _426, _427), vec3(_3401, _3402, _3403))) * 0.5) + _3400) * (1.0 / (_3419 * _3419))) * 0.3183098733425140380859375;
                    D _3837 = ((_3834 * _3468) * _3827) * (1.0 / (_3831 * _3831));
                    D _3839 = (_1448 * _1274) * _3399;
                    D _3841 = (_1448 * _1275) * _3399;
                    D _3843 = (_1448 * _1276) * _3399;
                    _1752 = _3837 * _3839;
                    _1754 = _3837 * _3841;
                    _1756 = _3837 * _3843;
                    _1758 = _3834 * _3839;
                    _1760 = _3834 * _3841;
                    _1762 = _3834 * _3843;
                }
                else
                {
                    _1752 = 0.0;
                    _1754 = 0.0;
                    _1756 = 0.0;
                    _1758 = 0.0;
                    _1760 = 0.0;
                    _1762 = 0.0;
                }
                frontier_phi_47_pred = _1754 + _1260;
                frontier_phi_47_pred_1 = _1250;
                frontier_phi_47_pred_2 = _1251;
                frontier_phi_47_pred_3 = _1252;
                frontier_phi_47_pred_4 = _1253;
                frontier_phi_47_pred_5 = _1254;
                frontier_phi_47_pred_6 = _1255;
                frontier_phi_47_pred_7 = _1256;
                frontier_phi_47_pred_8 = _1257;
                frontier_phi_47_pred_9 = _1258;
                frontier_phi_47_pred_10 = _1752 + _1259;
                frontier_phi_47_pred_11 = _1756 + _1261;
                frontier_phi_47_pred_12 = _1758 + _1262;
                frontier_phi_47_pred_13 = _1760 + _1263;
                frontier_phi_47_pred_14 = _1762 + _1264;
            }
            _880 = frontier_phi_47_pred;
            _860 = frontier_phi_47_pred_1;
            _862 = frontier_phi_47_pred_2;
            _864 = frontier_phi_47_pred_3;
            _866 = frontier_phi_47_pred_4;
            _868 = frontier_phi_47_pred_5;
            _870 = frontier_phi_47_pred_6;
            _872 = frontier_phi_47_pred_7;
            _874 = frontier_phi_47_pred_8;
            _876 = frontier_phi_47_pred_9;
            _878 = frontier_phi_47_pred_10;
            _882 = frontier_phi_47_pred_11;
            _884 = frontier_phi_47_pred_12;
            _886 = frontier_phi_47_pred_13;
            _888 = frontier_phi_47_pred_14;
            uint _1266 = _1265 + 1u;
            if (_1266 == _852)
            {
                break;
            }
            else
            {
                _1250 = _860;
                _1251 = _862;
                _1252 = _864;
                _1253 = _866;
                _1254 = _868;
                _1255 = _870;
                _1256 = _872;
                _1257 = _874;
                _1258 = _876;
                _1259 = _878;
                _1260 = _880;
                _1261 = _882;
                _1262 = _884;
                _1263 = _886;
                _1264 = _888;
                _1265 = _1266;
                continue;
            }
        }
        _859 = _860;
        _861 = _862;
        _863 = _864;
        _865 = _866;
        _867 = _868;
        _869 = _870;
        _871 = _872;
        _873 = _874;
        _875 = _876;
        _877 = _878;
        _879 = _880;
        _881 = _882;
        _883 = _884;
        _885 = _886;
        _887 = _888;
    }
    D _922 = (_232 - View._m0[180u].x) * View._m0[182u].x;
    D _923 = (_233 - View._m0[180u].y) * View._m0[182u].y;
    D _924 = (_234 - View._m0[180u].z) * View._m0[182u].z;
    vec4 _929 = textureLod(sampler3D(TranslucentBasePass_TranslucencyLightingVolumeEnvironmentA, View_SharedBilinearClampedSampler), vec3(_922, _923, _924), 0.0);
    D _931 = _929.x;
    D _967;
    D _968;
    D _969;
    if (_371 < 1.0)
    {
        _967 = _348.x / ((_393 / _370) + 1.0);
        _968 = _348.y / ((_394 / _370) + 1.0);
        _969 = _348.z / ((_395 / _370) + 1.0);
    }
    else
    {
        _967 = 0.0;
        _968 = 0.0;
        _969 = 0.0;
    }
    D _974 = View._m0[164u].z * _931;
    D _975 = View._m0[164u].z * _929.y;
    D _976 = View._m0[164u].z * _929.z;
    D _977 = spvNClamp(_607, 0.0, 1.0);
    D _978 = spvNClamp(_608, 0.0, 1.0);
    D _979 = spvNClamp(_609, 0.0, 1.0);
    D _989 = spvNClamp((-0.0) - _607, 0.0, 1.0);
    D _990 = spvNClamp((-0.0) - _608, 0.0, 1.0);
    D _991 = spvNClamp((-0.0) - _609, 0.0, 1.0);
    D _998 = dot(vec3(textureLod(sampler3D(TranslucentBasePass_TranslucencyLightingVolumeEnvironmentC, View_SharedBilinearClampedSampler), vec3(_922, _923, _924), 0.0).xyz()), vec3(_989 * _989, _990 * _990, _991 * _991)) + dot(vec3(textureLod(sampler3D(TranslucentBasePass_TranslucencyLightingVolumeEnvironmentB, View_SharedBilinearClampedSampler), vec3(_922, _923, _924), 0.0).xyz()), vec3(_977 * _977, _978 * _978, _979 * _979));
    D _999 = dot(vec3(_931, _929.yz()), vec3(0.2125999927520751953125, 0.715200006961822509765625, 0.072200000286102294921875));
    D _1007 = (_999 > 0.0) ? (1.0 / _999) : 0.0;
    D _1033 = spvNClamp(_676, 0.0, 1.0);
    D _1052 = ((_425 - _562) * _593) + _562;
    D _1053 = ((_426 - _563) * _593) + _563;
    D _1054 = ((_427 - _564) * _593) + _564;
    D _1058 = inversesqrt(dot(vec3(_1052, _1053, _1054), vec3(_1052, _1053, _1054)));
    D _1067 = 10.0 / spvNMax(9.9999997473787516355514526367188e-06, _592);
    D _1096 = fma(_231, View._m0[2u].x, fma(_230, View._m0[1u].x, View._m0[0u].x * _229)) + View._m0[3u].x;
    D _1100 = fma(_231, View._m0[2u].y, fma(_230, View._m0[1u].y, View._m0[0u].y * _229)) + View._m0[3u].y;
    D _1104 = fma(_231, View._m0[2u].z, fma(_230, View._m0[1u].z, View._m0[0u].z * _229)) + View._m0[3u].z;
    D _1108 = fma(_231, View._m0[2u].w, fma(_230, View._m0[1u].w, View._m0[0u].w * _229)) + View._m0[3u].w;
    D _1115 = ((_1052 * _105) * _1058) + _229;
    D _1116 = ((_1053 * _105) * _1058) + _230;
    D _1117 = ((_1054 * _105) * _1058) + _231;
    D _1150 = 1.0 / _1108;
    D _1151 = _1150 * _1096;
    D _1152 = _1150 * _1100;
    D _1156 = (_1150 * _1104) + (0.0500000007450580596923828125 / _1108);
    D _1157 = 1.0 / (fma(_1117, View._m0[2u].w, fma(_1116, View._m0[1u].w, View._m0[0u].w * _1115)) + View._m0[3u].w);
    D _1168 = 1.0 / ((View._m0[36u].w * _1067) + _1108);
    D _1171 = (_1157 * (fma(_1117, View._m0[2u].x, fma(_1116, View._m0[1u].x, View._m0[0u].x * _1115)) + View._m0[3u].x)) - _1151;
    D _1172 = (_1157 * (fma(_1117, View._m0[2u].y, fma(_1116, View._m0[1u].y, View._m0[0u].y * _1115)) + View._m0[3u].y)) - _1152;
    D _1174 = (_1168 * ((View._m0[36u].x * _1067) + _1096)) - _1151;
    D _1175 = (_1168 * ((View._m0[36u].y * _1067) + _1100)) - _1152;
    D _1180 = sqrt((_1171 * _1171) + (_1172 * _1172)) * 0.5;
    D _1199 = spvNMin(1.0 - (spvNMax(0.0, abs((_1180 * _1151) + _1171) - _1180) / abs(_1171)), 1.0 - (spvNMax(0.0, abs((_1180 * _1152) + _1172) - _1180) / abs(_1172))) / _1180;
    D _1200 = _1199 * _1171;
    D _1201 = _1199 * _1172;
    D _1202 = _1199 * ((_1157 * (fma(_1117, View._m0[2u].z, fma(_1116, View._m0[1u].z, View._m0[0u].z * _1115)) + View._m0[3u].z)) - _1156);
    uvec2 _1208 = uvec2(textureSize(TranslucentBasePass_HZBTexture, int(0u)));
    D _1210 = D(int(_1208.x));
    D _1212 = D(int(_1208.y));
    uint _1233 = max(1u, min(uint(ceil((spvNClamp((1.0 / spvNMax(9.9999997473787516355514526367188e-05, sqrt((_1200 * _1200) + (_1201 * _1201)))) * sqrt((_1174 * _1174) + (_1175 * _1175)), 0.0, 1.0) * 8.0) + _267)), 8u));
    D _1238 = ((_1151 * 0.5) + 0.5) * TranslucentBasePass_2._m0[198u].x;
    D _1239 = (0.5 - (_1152 * 0.5)) * TranslucentBasePass_2._m0[198u].y;
    D _1242 = (TranslucentBasePass_2._m0[198u].x * 0.0625) * _1200;
    D _1245 = (TranslucentBasePass_2._m0[198u].y * (-0.0625)) * _1201;
    D _1246 = _1202 * 0.125;
    D _1248 = spvNMax(abs(_1202), _1156 - ((1.0 / (fma(_105, View._m0[38u].w, 0.0) + _1108)) * (fma(_105, View._m0[38u].z, 0.0) + _1104))) * 0.125;
    D _1416;
    D _1418;
    D _1420;
    D _1422;
    if (_1233 == 0u)
    {
        _1416 = 0.0;
        _1418 = 0.0;
        _1420 = 0.0;
        _1422 = 0.0;
    }
    else
    {
        D frontier_phi_60;
        D frontier_phi_60_1;
        D frontier_phi_60_2;
        D frontier_phi_60_3;
        D _1665 = 0.0;
        uint _1667 = 0u;
        D _1666;
        D _1669;
        bool _1692;
        for (;;)
        {
            _1669 = D(_1667);
            D _1670 = _1669 + _267;
            vec4 _1684 = texelFetch(TranslucentBasePass_HZBTexture, ivec2_(uvec2(uint(int(floor(((_1670 * _1242) + _1238) * _1210))), uint(int(floor(((_1670 * _1245) + _1239) * _1212))))), int(0u));
            D _1686 = _1684.x;
            _1666 = ((_1670 * _1246) + _1156) - _1686;
            _1692 = (abs(((-0.0) - _1248) - _1666) < _1248) && (_1686 != 0.0);
            if (_1692)
            {
                D _2101 = (_1667 == 0u) ? (_1666 - _1246) : _1665;
                D _2108 = abs(((_267 + (-1.0)) + _1669) + spvNClamp(_2101 / (_2101 - _1666), 0.0, 1.0));
                D _2113 = spvNMin(_2108 * 0.125, 1.0);
                frontier_phi_60 = 1.0 - (_2113 * _2113);
                frontier_phi_60_1 = (_2108 * _1246) + _1156;
                frontier_phi_60_2 = (_2108 * _1245) + _1239;
                frontier_phi_60_3 = (_2108 * _1242) + _1238;
                break;
            }
            else
            {
                uint _1668 = _1667 + 1u;
                if (_1668 < _1233)
                {
                    _1665 = _1666;
                    _1667 = _1668;
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
        _1416 = frontier_phi_60_3;
        _1418 = frontier_phi_60_2;
        _1420 = frontier_phi_60_1;
        _1422 = frontier_phi_60;
    }
    D _1430 = (spvNClamp(_1416 * TranslucentBasePass_2._m0[198u].z, 0.0, 1.0) * 2.0) + (-1.0);
    D _1431 = 1.0 - (spvNClamp(_1418 * TranslucentBasePass_2._m0[198u].w, 0.0, 1.0) * 2.0);
    D _1570;
    D _1572;
    D _1574;
    D _1576;
    if (_1422 > 0.0)
    {
        D _1571;
        D _1573;
        D _1575;
        D _2317;
        D _1563;
        bool _1569;
        for (;;)
        {
            D _1522 = ((View._m0[73u].x * _1420) + View._m0[73u].y) + (1.0 / ((View._m0[73u].z * _1420) - View._m0[73u].w));
            D _1546 = _1522 * _1430;
            D _1547 = _1522 * _1431;
            D _1558 = (_229 - View._m0[63u].x) - fma(_1522, View._m0[62u].x, fma(_1547, View._m0[61u].x, _1546 * View._m0[60u].x));
            D _1560 = (_230 - View._m0[63u].y) - fma(_1522, View._m0[62u].y, fma(_1547, View._m0[61u].y, _1546 * View._m0[60u].y));
            D _1562 = (_231 - View._m0[63u].z) - fma(_1522, View._m0[62u].z, fma(_1547, View._m0[61u].z, _1546 * View._m0[60u].z));
            _1563 = dot(vec3(_1558, _1560, _1562), vec3(_1558, _1560, _1562));
            _1569 = View._m0[175u].w != 0.0;
            if (_1569)
            {
                if (floatBitsToUint(View._m0[175u]).y == 0u)
                {
                    _1571 = 0.0;
                    _1573 = 0.0;
                    _1575 = 0.0;
                    _2317 = 0.0;
                    break;
                }
            }
            D _1959 = fma(_1420, View._m0[140u].w, fma(_1431, View._m0[139u].w, View._m0[138u].w * _1430)) + View._m0[141u].w;
            D _1960 = (fma(_1420, View._m0[140u].x, fma(_1431, View._m0[139u].x, View._m0[138u].x * _1430)) + View._m0[141u].x) / _1959;
            D _1961 = (fma(_1420, View._m0[140u].y, fma(_1431, View._m0[139u].y, View._m0[138u].y * _1430)) + View._m0[141u].y) / _1959;
            D _1978 = spvNClamp((abs((spvNMin(spvNMax(_1960, -1.0), 1.0) - _1430) * 0.5) * 5.0) + (-4.0), 0.0, 1.0);
            D _1979 = spvNClamp((abs((spvNMin(spvNMax(_1961, -1.0), 1.0) - _1431) * 0.5) * 5.0) + (-4.0), 0.0, 1.0);
            uvec2 _2032 = uvec2(textureSize(TranslucentBasePass_PrevSceneColor, int(0u)));
            vec4 _2053 = texelFetch(TranslucentBasePass_PrevSceneColor, ivec2_(uvec2(uint(min(int(uint(max(int(uint(int(D(int(_2032.x)) * ((TranslucentBasePass_2._m0[199u].x * spvNMin(spvNMax(_1960 - ((D(int(uint(_1960 > 0.0) - uint(_1960 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1960) + (-1.0))), -1.0), 1.0)) + TranslucentBasePass_2._m0[199u].z)))), int(uint(int(TranslucentBasePass_2._m0[200u].x)))))), int(uint(int(TranslucentBasePass_2._m0[200u].x + TranslucentBasePass_2._m0[200u].z)) + 4294967295u))), uint(min(int(uint(max(int(uint(int(D(int(_2032.y)) * ((TranslucentBasePass_2._m0[199u].y * spvNMin(spvNMax(_1961 - ((D(int(uint(_1961 > 0.0) - uint(_1961 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1961) + (-1.0))), -1.0), 1.0)) + TranslucentBasePass_2._m0[199u].w)))), int(uint(int(TranslucentBasePass_2._m0[200u].y)))))), int(uint(int(TranslucentBasePass_2._m0[200u].y + TranslucentBasePass_2._m0[200u].w)) + 4294967295u))))), int(0u));
            _1571 = View._m0[165u].x * spvNMin(_2053.x, 65504.0);
            _1573 = View._m0[165u].x * spvNMin(_2053.y, 65504.0);
            _1575 = View._m0[165u].x * spvNMin(_2053.z, 65504.0);
            _2317 = spvNMax(0.0, 1.0 - dot(vec2(_1978, _1979), vec2(_1978, _1979)));
            break;
        }
        _1570 = _1571;
        _1572 = _1573;
        _1574 = _1575;
        _1576 = (_2317 * _1422) * spvNClamp(1.0 / spvNMax(9.9999997473787516355514526367188e-06, (_592 * _592) * _1563), 0.0, 1.0);
    }
    else
    {
        _1570 = 0.0;
        _1572 = 0.0;
        _1574 = 0.0;
        _1576 = 0.0;
    }
    D _1610 = fma(_234, View._m0[14u].w, fma(_233, View._m0[13u].w, _232 * View._m0[12u].w)) + View._m0[15u].w;
    D _1615 = (((fma(_234, View._m0[14u].x, fma(_233, View._m0[13u].x, _232 * View._m0[12u].x)) + View._m0[15u].x) / _1610) * 0.5) + 0.5;
    D _1616 = 0.5 - (((fma(_234, View._m0[14u].y, fma(_233, View._m0[13u].y, _232 * View._m0[12u].y)) + View._m0[15u].y) / _1610) * 0.5);
    D _1645 = sqrt(((_230 * _230) + (_229 * _229)) + (_231 * _231));
    D _1663 = spvNMax(0.0, ((1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_229, _230, _231), vec3(View._m0[68u].xyz())))) * _1645) * View._m0[280u].w);
    D _2069;
    D _2071;
    D _2073;
    D _2075;
    D _2077;
    D _2079;
    if (_1645 < _1663)
    {
        _2069 = 0.0;
        _2071 = 0.0;
        _2073 = 0.0;
        _2075 = 1.0;
        _2077 = 1.0;
        _2079 = 1.0;
    }
    else
    {
        D _2087 = (1.0 / _1645) * _1663;
        uvec4 _2094 = floatBitsToUint(View._m0[220u]);
        uint _2095 = _2094.y;
        uint _2097 = (_2095 != 1u) ? 4294967295u : 0u;
        uint _2430;
        if (_2095 > 1u)
        {
            D _134[4];
            _134[0u] = 0.0;
            _134[1u] = 0.0;
            _134[2u] = 0.0;
            _134[3u] = 0.0;
            uint _3276 = 0u;
            bool _3282;
            for (;;)
            {
                _3282 = _3276 < floatBitsToUint(View._m0[220u]).y;
                if (_3282)
                {
                    uint _3711 = _3276 + 237u;
                    D _3723 = View._m0[_3711].x - View._m0[75u].x;
                    D _3724 = View._m0[_3711].y - View._m0[75u].y;
                    D _3725 = View._m0[_3711].z - View._m0[75u].z;
                    D _3726 = dot(vec3(_3723, _3724, _3725), vec3(_240, _241, _242));
                    D _3733 = dot(vec3(_3723, _3724, _3725), vec3(_3723, _3724, _3725)) - (View._m0[_3711].w * View._m0[_3711].w);
                    D _3735 = (_3726 * _3726) - _3733;
                    D _3852;
                    if ((_3733 < 0.0) && (!(_3735 < 0.0)))
                    {
                        D _3846 = sqrt(_3735);
                        _3852 = spvNMin(abs(_3846 + _3726), abs(_3726 - _3846));
                    }
                    else
                    {
                        _3852 = 0.0;
                    }
                    _134[_3276] = _3852;
                }
                uint _3277 = _3276 + 1u;
                if (_3277 == 4u)
                {
                    break;
                }
                else
                {
                    _3276 = _3277;
                    continue;
                }
            }
            D _3862 = (_267 * 0.99989998340606689453125) * dot(vec4(_134[0u], _134[1u], _134[2u], _134[3u]), vec4(1.0));
            uint frontier_phi_59_97_ladder;
            if (_134[0u] > _3862)
            {
                frontier_phi_59_97_ladder = 0u;
            }
            else
            {
                D _3930 = _134[1u] + _134[0u];
                uint frontier_phi_59_97_ladder_103_ladder;
                if (_3930 > _3862)
                {
                    frontier_phi_59_97_ladder_103_ladder = 1u;
                }
                else
                {
                    D _3960 = _3930 + _134[2u];
                    uint frontier_phi_59_97_ladder_103_ladder_109_ladder;
                    if (_3960 > _3862)
                    {
                        frontier_phi_59_97_ladder_103_ladder_109_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder;
                        if ((_3960 + _134[3u]) > _3862)
                        {
                            frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder = _2097;
                        }
                        frontier_phi_59_97_ladder_103_ladder_109_ladder = frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder;
                    }
                    frontier_phi_59_97_ladder_103_ladder = frontier_phi_59_97_ladder_103_ladder_109_ladder;
                }
                frontier_phi_59_97_ladder = frontier_phi_59_97_ladder_103_ladder;
            }
            _2430 = frontier_phi_59_97_ladder;
        }
        else
        {
            _2430 = _2097;
        }
        D frontier_phi_38_59_ladder;
        D frontier_phi_38_59_ladder_1;
        D frontier_phi_38_59_ladder_2;
        D frontier_phi_38_59_ladder_3;
        D frontier_phi_38_59_ladder_4;
        D frontier_phi_38_59_ladder_5;
        if (_2430 == 4294967295u)
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
            uint _3283 = _2430 + 221u;
            D _3291 = spvNMin(View._m0[_3283].w, 0.9900000095367431640625);
            uint _3292 = _2430 + 225u;
            uint _3299 = _2430 + 229u;
            uint _3306 = _2430 + 233u;
            uint _3311 = _2430 + 241u;
            D _3766;
            D _3767;
            D _3768;
            if (TranslucentBasePass_2._m0[146u].x > 0.0)
            {
                vec4 _3758 = textureLod(sampler2D(TranslucentBasePass_Shared_Fog_FarIntegratedScatteringTexture, View_SharedBilinearClampedSampler), vec2(spvNMin(spvNMax(View._m0[278u].x * _1615, View._m0[279u].x), View._m0[280u].x), spvNMin(spvNMax(View._m0[278u].y * _1616, View._m0[279u].y), View._m0[280u].y)), 0.0);
                _3766 = View._m0[164u].z * _3758.x;
                _3767 = View._m0[164u].z * _3758.y;
                _3768 = View._m0[164u].z * _3758.z;
            }
            else
            {
                _3766 = 0.0;
                _3767 = 0.0;
                _3768 = 0.0;
            }
            D _3772 = dot(vec3((-0.0) - View._m0[218u].x, (-0.0) - View._m0[218u].y, (-0.0) - View._m0[218u].z), vec3(_243, _245, _246));
            D _3784 = (((_3772 * _3772) + 1.0) * 0.0397887341678142547607421875) * exp2(log2(spvNMax(0.0, _3772 + 1.25)) * (-1.5));
            D _3864;
            if (View._m0[_3292].x == 0.0)
            {
                _3864 = 0.0;
            }
            else
            {
                D _3912 = (((_2087 * _231) - View._m0[_3292].z) + View._m0[75u].z) * View._m0[_3292].y;
                D _3913 = ((1.0 - _2087) * _231) * View._m0[_3292].y;
                D _3918 = exp2((-0.0) - _3912);
                D frontier_phi_98_99_ladder;
                if (abs(_3913) > 0.00999999977648258209228515625)
                {
                    frontier_phi_98_99_ladder = ((_3918 - exp2(((-0.0) - _3913) - _3912)) * View._m0[_3292].x) * (1.0 / _3913);
                }
                else
                {
                    frontier_phi_98_99_ladder = (View._m0[_3292].x * 0.693147182464599609375) * _3918;
                }
                _3864 = frontier_phi_98_99_ladder;
            }
            D _3868 = _3864 * (1.0 - _3291);
            D _3872 = (1.0 - View._m0[_3299].x) * View._m0[_3306].x;
            D _3873 = (1.0 - View._m0[_3299].y) * View._m0[_3306].x;
            D _3874 = (1.0 - View._m0[_3299].z) * View._m0[_3306].x;
            D _3875 = (-0.0) - (_1645 - _1663);
            D _3903 = 1.0 - spvNClamp(exp2(_3868 * _3875), 0.0, 1.0);
            frontier_phi_38_59_ladder = spvNClamp(exp2((_3868 + _3874) * _3875), 0.0, 1.0);
            frontier_phi_38_59_ladder_1 = spvNClamp(exp2((_3868 + _3873) * _3875), 0.0, 1.0);
            frontier_phi_38_59_ladder_2 = spvNClamp(exp2((_3868 + _3872) * _3875), 0.0, 1.0);
            frontier_phi_38_59_ladder_3 = (((_3291 * View._m0[_3283].z) * (((View._m0[219u].z * View._m0[_3311].x) * _3784) + _3768)) * spvNClamp(exp2(_3874 * _3875), 0.0, 1.0)) * _3903;
            frontier_phi_38_59_ladder_4 = (((_3291 * View._m0[_3283].y) * (((View._m0[219u].y * View._m0[_3311].x) * _3784) + _3767)) * spvNClamp(exp2(_3873 * _3875), 0.0, 1.0)) * _3903;
            frontier_phi_38_59_ladder_5 = (((_3291 * View._m0[_3283].x) * (((View._m0[219u].x * View._m0[_3311].x) * _3784) + _3766)) * spvNClamp(exp2(_3872 * _3875), 0.0, 1.0)) * _3903;
        }
        _2069 = frontier_phi_38_59_ladder_5;
        _2071 = frontier_phi_38_59_ladder_4;
        _2073 = frontier_phi_38_59_ladder_3;
        _2075 = frontier_phi_38_59_ladder_2;
        _2077 = frontier_phi_38_59_ladder_1;
        _2079 = frontier_phi_38_59_ladder;
    }
    D _2365;
    D _2366;
    D _2367;
    D _2368;
    D _2369;
    D _2370;
    if (TranslucentBasePass_2._m0[148u].x > 0.0)
    {
        D _2345 = spvNMin(spvNMax(View._m0[278u].x * _1615, View._m0[279u].x), View._m0[280u].x);
        D _2346 = spvNMin(spvNMax(View._m0[278u].y * _1616, View._m0[279u].y), View._m0[280u].y);
        D _2347 = spvNMin(spvNMax((View._m0[275u].z * spvNMax(0.0, spvNMin(View._m0[276u].z * log2((View._m0[276u].x * _1610) + View._m0[276u].y), View._m0[274u].z + (-1.0)) + 0.5)) * View._m0[278u].z, View._m0[279u].z), View._m0[280u].z);
        vec4 _2350 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeATexture, View_SharedBilinearClampedSampler), vec3(_2345, _2346, _2347), 0.0);
        vec4 _2357 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeBTexture, View_SharedBilinearClampedSampler), vec3(_2345, _2346, _2347), 0.0);
        _2365 = View._m0[164u].z * _2350.x;
        _2366 = View._m0[164u].z * _2350.y;
        _2367 = View._m0[164u].z * _2350.z;
        _2368 = _2357.x;
        _2369 = _2357.y;
        _2370 = _2357.z;
    }
    else
    {
        _2365 = 0.0;
        _2366 = 0.0;
        _2367 = 0.0;
        _2368 = 1.0;
        _2369 = 1.0;
        _2370 = 1.0;
    }
    D _2377 = (1.0 - _681) + (_681 * _449);
    D _2378 = (1.0 - _684) + (_684 * _449);
    D _2379 = (1.0 - _687) + (_687 * _449);
    SV_Target.x = View._m0[164u].y * ((((_2368 * _2069) + _2365) * _2377) + ((_2075 * (((((((((_475 * _451) * _752) * spvNMax(1.0, ((_530 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_530 * 4.79510021209716796875)) + (((_530 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _451)) * _451))) * _883) + _859) * _452) + _865) + ((((_967 * _649) * spvNClamp(1.0 - (_665 * _655), 0.0, 1.0)) * _1033) * ((_974 + _871) + ((((_974 * _998) * _1007) - _974) * 0.6480000019073486328125)))) + ((_766 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1570)) + 29.8973522186279296875) * _1576) + (-29.8973522186279296875)) + _877)) * spvNClamp(_744, 0.0, 1.0)))) * _2368));
    SV_Target.y = ((((_2369 * _2071) + _2366) * _2378) + ((_2077 * (((((((((_476 * _451) * _752) * spvNMax(1.0, ((_531 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_531 * 4.79510021209716796875)) + (((_531 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _451)) * _451))) * _885) + _861) * _452) + _867) + ((((_968 * _649) * spvNClamp(1.0 - (_666 * _655), 0.0, 1.0)) * _1033) * ((_975 + _873) + ((((_975 * _998) * _1007) - _975) * 0.6480000019073486328125)))) + ((_766 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1572)) + 29.8973522186279296875) * _1576) + (-29.8973522186279296875)) + _879)) * spvNClamp(_745, 0.0, 1.0)))) * _2369)) * View._m0[164u].y;
    SV_Target.z = ((((_2370 * _2073) + _2367) * _2379) + ((_2079 * (((((((((_477 * _451) * _752) * spvNMax(1.0, ((_532 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_532 * 4.79510021209716796875)) + (((_532 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _451)) * _451))) * _887) + _863) * _452) + _869) + ((((_969 * _649) * spvNClamp(1.0 - (_667 * _655), 0.0, 1.0)) * _1033) * ((_976 + _875) + ((((_976 * _998) * _1007) - _976) * 0.6480000019073486328125)))) + ((_766 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1574)) + 29.8973522186279296875) * _1576) + (-29.8973522186279296875)) + _881)) * spvNClamp(_746, 0.0, 1.0)))) * _2370)) * View._m0[164u].y;
    SV_Target.w = dot(vec3(_2377, _2378, _2379), vec3(0.2125999927520751953125, 0.715200006961822509765625, 0.072200000286102294921875));
    SV_Target_1.x = _2377;
    SV_Target_1.y = _2378;
    SV_Target_1.z = _2379;
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
} // namespace S_ater_Thick_Wide_Character