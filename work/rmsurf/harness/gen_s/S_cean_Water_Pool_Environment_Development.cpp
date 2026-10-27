namespace S_cean_Water_Pool_Environment_Development {
using namespace cpuglsl;
static D _4274;
static D _4270;
static D _4271;
static D _4272;
static UBO& View = ubo("View");
static UBO& Primitive = ubo("Primitive");
static UBOF& TranslucentBasePass = uboF("b0_2");
static UBO& TranslucentBasePass_2 = ubo("b0_2");
static UBO& Material = ubo("junk:b0_3");
static Tex3D View_SpatiotemporalBlueNoiseVolumeTexture{texid("View_SpatiotemporalBlueNoiseVolumeTexture")};
static Tex3D View_PerlinNoiseVolumeTexture{texid("View_PerlinNoiseVolumeTexture")};
static TexBufI TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileIndices{texid("TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileIndices")};
static TexBufF TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthRanges{texid("TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthRanges")};
static TexBufU TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowLoadedTileData{texid("TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowLoadedTileData")};
static TexBufU TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileData{texid("TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileData")};
static TexBufF TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer{texid("TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer")};
static TexBufU TranslucentBasePass_Shared_Forward_NumCulledLightsGrid{texid("TranslucentBasePass_Shared_Forward_NumCulledLightsGrid")};
static Tex2D TranslucentBasePass_SceneTextures_SceneDepthTexture{texid("TranslucentBasePass_SceneTextures_SceneDepthTexture")};
static Tex2D TranslucentBasePass_HZBTexture{texid("TranslucentBasePass_HZBTexture")};
static Tex2D TranslucentBasePass_SceneColorCopyTexture{texid("TranslucentBasePass_SceneColorCopyTexture")};
static Tex2D Material_Texture2D_13{texid("junk:T_Muddiness")};
static Tex2D Material_Texture2D_14{texid("junk:T_Transparency")};
static Tex2D Material_Texture2D_15{texid("junk:T_TransparencyCoefficient")};
static Tex2D Material_Texture2D_16{texid("junk:T_Transmittance")};
static Tex2D Material_Texture2D_17{texid("junk:T_TransmittanceCoefficient")};
static Tex2D Material_Texture2D_19{texid("junk:T_OceanGeometry")};
static Tex2D ForwardLightProfileTextures[64];
static Tex2D ShadowMaps[64];
static Samp View_SharedPointClampedSampler{texid("View_SharedPointClampedSampler")};
static Samp View_SharedBilinearWrappedSampler{texid("View_SharedBilinearWrappedSampler")};
static Samp View_SharedBilinearClampedSampler{texid("View_SharedBilinearClampedSampler")};
static Samp View_SharedTrilinearWrappedSampler{texid("View_SharedTrilinearWrappedSampler")};
static Samp View_SharedAnisotropic4XClampedSampler{texid("View_SharedAnisotropic4XClampedSampler")};
static vec4 TEXCOORD_10;
static vec4 TEXCOORD_11;
static vec4 TEXCOORD;
static vec4 VERTEX_EXPRESSION;
static D CONSTANT_CONTEXT;
static vec4 ENVIRONMENT_AMBIENT_DICE_;
static vec4 ENVIRONMENT_AMBIENT_DICE_1;
static vec4 ENVIRONMENT_AMBIENT_DICE_2;
static vec4 SV_Target;
static vec4 SV_Target_1;
static bool discard_state;










void discard_cond(bool _4260)
{
    if (_4260)
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
    D _172 = ((TEXCOORD_10.x * TEXCOORD_11.z) - (TEXCOORD_10.z * TEXCOORD_11.x)) * TEXCOORD_11.w;
    D _219 = fma(gl_FragCoord.z, View._m0[54u].w, fma(gl_FragCoord.y, View._m0[53u].w, View._m0[52u].w * gl_FragCoord.x)) + View._m0[55u].w;
    D _220 = (fma(gl_FragCoord.z, View._m0[54u].x, fma(gl_FragCoord.y, View._m0[53u].x, View._m0[52u].x * gl_FragCoord.x)) + View._m0[55u].x) / _219;
    D _221 = (fma(gl_FragCoord.z, View._m0[54u].y, fma(gl_FragCoord.y, View._m0[53u].y, View._m0[52u].y * gl_FragCoord.x)) + View._m0[55u].y) / _219;
    D _222 = (fma(gl_FragCoord.z, View._m0[54u].z, fma(gl_FragCoord.y, View._m0[53u].z, View._m0[52u].z * gl_FragCoord.x)) + View._m0[55u].z) / _219;
    D _223 = _220 - View._m0[78u].x;
    D _224 = _221 - View._m0[78u].y;
    D _225 = _222 - View._m0[78u].z;
    D _230 = inversesqrt(dot(vec3(_220, _221, _222), vec3(_220, _221, _222)));
    D _231 = _230 * _221;
    D _232 = _230 * _222;
    D _233 = (-0.0) - _231;
    vec4 _252 = texelFetch(View_SpatiotemporalBlueNoiseVolumeTexture, ivec3_(uvec3(uint(int(gl_FragCoord.x)) & 127u, uint(int(gl_FragCoord.y)) & 127u, ((floatBitsToUint(View._m0[175u]).x & 7u) + uint(roundEven(CONSTANT_CONTEXT))) & 63u)), int(0u));
    D _255 = _252.y;
    vec4 _264 = vec4(g_R.Muddiness.x, g_R.Muddiness.y, g_R.Muddiness.z, 0.0);
    vec4 _270 = texture(sampler2D(Material_Texture2D_14, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _275 = texture(sampler2D(Material_Texture2D_15, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _286 = g_R.TransparencyLog2;
    vec4 _289 = texture(sampler2D(Material_Texture2D_16, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _295 = texture(sampler2D(Material_Texture2D_17, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _300 = 1.0 / spvNMax(9.9999999747524270787835121154785e-07, _295.x * 100.0);
    D _305 = g_R.TransmittanceLog2.y;
    D _306 = g_R.TransmittanceLog2.z;
    vec4 _311 = textureLod(sampler2D(Material_Texture2D_19, View_SharedBilinearClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), 0.0);
    D _313 = _311.y;
    D _316 = _223 - VERTEX_EXPRESSION.x;
    D _327;
    D _330;
    D _332;
    D _334;
    D _336;
    D _338;
    D _340;
    uint _342;
    _327 = 0.5;
    _330 = 1.0;
    _332 = (_220 - VERTEX_EXPRESSION.x) * 0.0024999999441206455230712890625;
    _334 = (_221 - VERTEX_EXPRESSION.y) * 0.0024999999441206455230712890625;
    _336 = View._m0[78u].x * (-0.0024999999441206455230712890625);
    _338 = View._m0[78u].y * (-0.0024999999441206455230712890625);
    _340 = 0.0;
    _342 = 0u;
    D _341;
    for (;;)
    {
        D _350 = _336 * _330;
        D _351 = _338 * _330;
        D _352 = _332 * _330;
        D _353 = _334 * _330;
        D _367 = fract(fract(_350 * 0.00999999977648258209228515625) + fract(_352 * 0.00999999977648258209228515625)) * 256.0;
        D _369 = fract(fract(_351 * 0.00999999977648258209228515625) + fract(_353 * 0.00999999977648258209228515625)) * 256.0;
        uint _372 = uint(int(floor(_367)));
        uint _373 = uint(int(floor(_369)));
        D _377 = D(int(_372 & 255u));
        D _378 = D(int(_373 & 255u));
        D _387 = fract(sin(dot(vec2(_377, _378), vec2(127.09999847412109375, 311.70001220703125))) * 43758.546875);
        D _390 = D(int((_372 + 1u) & 255u));
        D _399 = D(int((_373 + 1u) & 255u));
        D _405 = fract(sin(dot(vec2(_377, _399), vec2(127.09999847412109375, 311.70001220703125))) * 43758.546875);
        D _414 = spvNClamp(fract(_367), 0.0, 1.0);
        D _420 = (_414 * _414) * (3.0 - (_414 * 2.0));
        D _421 = spvNClamp(fract(_369), 0.0, 1.0);
        D _431 = (_420 * (fract(sin(dot(vec2(_390, _378), vec2(127.09999847412109375, 311.70001220703125))) * 43758.546875) - _387)) + _387;
        D _435 = ((((_421 * _421) * (3.0 - (_421 * 2.0))) * (((_420 * (fract(sin(dot(vec2(_390, _399), vec2(127.09999847412109375, 311.70001220703125))) * 43758.546875) - _405)) + _405) - _431)) + _431) * 0.5;
        D _442 = fract((Material._m0[15u].z * 7.957746982574462890625) * sqrt(_330 * 0.00153938052244484424591064453125));
        D _449 = fract(((fract(_350) + fract(_352)) + _442) + _435) * 6.283185482025146484375;
        D _451 = fract(((fract(_351) + fract(_353)) + _442) + _435) * 6.283185482025146484375;
        D _458 = 1.0 - abs(sin(_449));
        D _459 = 1.0 - abs(sin(_451));
        _341 = ((1.0 - sqrt((((abs(cos(_451)) - _459) * _459) + _459) * (((abs(cos(_449)) - _458) * _458) + _458))) * _327) + _340;
        D _475 = _332 * (-0.809017121791839599609375);
        D _478 = _336 * (-0.809017121791839599609375);
        uint _343 = _342 + 1u;
        if (_343 == 6u)
        {
            break;
        }
        else
        {
            _327 *= 0.5;
            _330 *= 2.0;
            _332 = fma(_334, 0.809017121791839599609375, _332 * (-0.587785065174102783203125));
            _334 = fma(_334, -0.587785065174102783203125, _475);
            _336 = fma(_338, 0.809017121791839599609375, _336 * (-0.587785065174102783203125));
            _338 = fma(_338, -0.587785065174102783203125, _478);
            _340 = _341;
            _342 = _343;
        }
    }
    D _501 = ((TEXCOORD_10.z * TEXCOORD_11.y) - (TEXCOORD_10.y * TEXCOORD_11.z)) * TEXCOORD_11.w;
    D _502 = ((TEXCOORD_10.y * TEXCOORD_11.x) - (TEXCOORD_10.x * TEXCOORD_11.y)) * TEXCOORD_11.w;
    D _503 = _230 * _220;
    D _504 = (-0.0) - _503;
    D _505 = (-0.0) - _232;
    D _506 = _252.x;
    D _510 = exp2(_286);
    D _514 = g_R.TransmittanceLog2.x;
    D _517 = _311.x;
    D _519 = _224 - VERTEX_EXPRESSION.y;
    D _546 = _225 - (_311.z * 100.0);
    D _563 = (spvNClamp(1.0 - (_546 * 0.0033333334140479564666748046875), 0.0, 1.0) * spvNClamp(1.0 - (_546 * 0.0024999999441206455230712890625), 0.0, 1.0)) * spvNClamp(1.0 - (sqrt((_517 * _517) + (_313 * _313)) * 0.00166666670702397823333740234375), 0.0, 1.0);
    D _564 = _563 * _563;
    D _568 = spvNClamp((VERTEX_EXPRESSION.z - VERTEX_EXPRESSION.w) * 0.0333333350718021392822265625, 0.0, 1.0);
    D _573 = spvNClamp(abs(VERTEX_EXPRESSION.w) * 0.01666666753590106964111328125, 0.0, 1.0);
    D _584 = (spvNClamp(_341 * 0.100000001490116119384765625, 0.0, 1.0) * 0.050000011920928955078125) + 0.949999988079071044921875;
    D _586 = _584 * _584;
    D _587 = _586 * _586;
    D _590 = spvNClamp((_587 * _587) * ((sqrt(texture(sampler3D(View_PerlinNoiseVolumeTexture, View_SharedTrilinearWrappedSampler), vec3(Material._m0[15u].z * 0.125, _316 * 0.001953125, _519 * 0.001953125)).x * texture(sampler3D(View_PerlinNoiseVolumeTexture, View_SharedTrilinearWrappedSampler), vec3(_316 * 0.00390625, _519 * 0.00390625, Material._m0[15u].z * 0.0625)).x) * 0.5) + 0.5), 0.0, 1.0);
    D _602 = spvNClamp((sqrt(spvNClamp(((_564 + (-1.0)) + _590) * _590, 0.0, 1.0)) * (((_568 * _568) * (1.0 - _573)) + _573)) * D((_590 + _564) > 1.0), 0.0, 1.0);
    D _606 = (_602 * _602) * (3.0 - (_602 * 2.0));
    D _607 = _606 * _606;
    D _609 = spvNClamp(g_R.Opacity, 0.0, 1.0);
    D _619 = ((sqrt(_564) * ((_590 * 4.0) - _341)) + _341) + (_606 * 6.0);
    D _620 = dFdyFine(_220);
    D _621 = dFdyFine(_221);
    D _622 = dFdyFine(_222);
    D _623 = dFdxFine(_220);
    D _624 = dFdxFine(_221);
    D _625 = dFdxFine(_222);
    D _628 = (_624 * _622) - (_625 * _621);
    D _631 = (_625 * _620) - (_623 * _622);
    D _634 = (_623 * _621) - (_624 * _620);
    D _638 = inversesqrt(dot(vec3(_628, _631, _634), vec3(_628, _631, _634)));
    D _639 = _628 * _638;
    D _640 = _631 * _638;
    D _641 = _638 * _634;
    D _645 = (_639 * _619) + _220;
    D _646 = (_640 * _619) + _221;
    D _647 = (_641 * _619) + _222;
    D _648 = dFdyFine(_645);
    D _649 = dFdyFine(_646);
    D _650 = dFdyFine(_647);
    D _651 = dFdxFine(_645);
    D _652 = dFdxFine(_646);
    D _653 = dFdxFine(_647);
    D _656 = (_652 * _650) - (_653 * _649);
    D _659 = (_653 * _648) - (_651 * _650);
    D _662 = (_651 * _649) - (_652 * _648);
    D _666 = inversesqrt(dot(vec3(_656, _659, _662), vec3(_656, _659, _662)));
    D _671 = (TEXCOORD_11.x - _639) + (_656 * _666);
    D _673 = (TEXCOORD_11.y - _640) + (_659 * _666);
    D _675 = (TEXCOORD_11.z - _641) + (_666 * _662);
    D _679 = inversesqrt(dot(vec3(_671, _673, _675), vec3(_671, _673, _675)));
    D _680 = _671 * _679;
    D _681 = _673 * _679;
    D _682 = _675 * _679;
    D _692 = _103 * 9.9999997473787516355514526367188e-06;
    D _696 = 1.0 / ((_692 * _692) + 1.0);
    D _703 = (_696 * (fma(TEXCOORD_10.z, _682, fma(TEXCOORD_10.y, _681, _680 * TEXCOORD_10.x)) - TEXCOORD_10.z)) + TEXCOORD_10.z;
    D _704 = (_696 * (fma(_502, _682, fma(_172, _681, _680 * _501)) - _502)) + _502;
    D _705 = (_696 * (fma(TEXCOORD_11.z, _682, fma(TEXCOORD_11.y, _681, _680 * TEXCOORD_11.x)) - TEXCOORD_11.z)) + TEXCOORD_11.z;
    D _709 = inversesqrt(dot(vec3(_703, _704, _705), vec3(_703, _704, _705)));
    D _710 = _703 * _709;
    D _711 = _704 * _709;
    D _712 = _705 * _709;
    D _717 = inversesqrt(dot(vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z), vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z)));
    D _718 = _717 * g_R.Normal.x;
    D _719 = _717 * g_R.Normal.y;
    D _720 = _717 * g_R.Normal.z;
    D _723 = fma(_720, TEXCOORD_11.x, fma(_719, _501, _718 * TEXCOORD_10.x));
    D _726 = fma(_720, TEXCOORD_11.y, fma(_719, _172, _718 * TEXCOORD_10.y));
    D _729 = fma(_720, TEXCOORD_11.z, fma(_719, _502, _718 * TEXCOORD_10.z));
    D _733 = inversesqrt(dot(vec3(_723, _726, _729), vec3(_723, _726, _729)));
    D _734 = _733 * _723;
    D _735 = _733 * _726;
    D _736 = _733 * _729;
    bool _748;
    if (Primitive._m0[27u].w > ((_252.w * 0.99609375) + 0.001953125))
    {
        _748 = ((_506 * 0.99609375) + 0.001953125) < 1.0;
    }
    else
    {
        _748 = false;
    }
    (void)((_748 ? 1.0 : (-1.0)) < 0.0);
    D _754 = spvNClamp(g_R.Roughness, 0.0, 1.0);
    D _756 = dFdxFine(_734);
    D _757 = dFdxFine(_735);
    D _758 = dFdxFine(_736);
    D _762 = dFdyFine(_734);
    D _763 = dFdyFine(_735);
    D _764 = dFdyFine(_736);
    D _775 = sqrt(spvNClamp(spvNMin((dot(vec3(_762, _763, _764), vec3(_762, _763, _764)) + dot(vec3(_756, _757, _758), vec3(_756, _757, _758))) * 0.15915493667125701904296875, 0.180000007152557373046875) + (_754 * _754), 0.0, 1.0));
    D _782 = spvNClamp(D(View._m0[220u].x > 1.0), 0.0, 1.0);
    D _785 = 0.0203731842339038848876953125 - (_782 * 0.02035685442388057708740234375);
    D _793 = dot(vec3(_734, _735, _736), vec3(_504, _233, _505));
    D _799 = (_793 * _734) + _503;
    D _800 = (_793 * _735) + _231;
    D _801 = (_793 * _736) + _232;
    D _805 = abs(_793);
    D _809 = (_799 * 2.0) + (_805 * _734);
    D _810 = (_800 * 2.0) + (_805 * _735);
    D _811 = (_801 * 2.0) + (_805 * _736);
    D _815 = inversesqrt(dot(vec3(_809, _810, _811), vec3(_809, _810, _811)));
    D _816 = _809 * _815;
    D _817 = _810 * _815;
    D _818 = _811 * _815;
    D _819 = _793 * _793;
    D _820 = 1.0 - _819;
    D _829 = sqrt(spvNMax(0.0, 1.0 - (_820 * 0.562781393527984619140625)));
    D _833 = (_799 * 0.750187575817108154296875) - (_829 * _734);
    D _834 = (_800 * 0.750187575817108154296875) - (_829 * _735);
    D _835 = (_801 * 0.750187575817108154296875) - (_829 * _736);
    D _839 = inversesqrt(dot(vec3(_833, _834, _835), vec3(_833, _834, _835)));
    D _840 = _833 * _839;
    D _841 = _834 * _839;
    D _842 = _835 * _839;
    D _846 = _775 * _775;
    D _847 = _846 * _775;
    D _854 = ((((-0.0) - _734) - _840) * _847) + _840;
    D _855 = ((((-0.0) - _735) - _841) * _847) + _841;
    D _856 = ((((-0.0) - _736) - _842) * _847) + _842;
    D _860 = inversesqrt(dot(vec3(_854, _855, _856), vec3(_854, _855, _856)));
    D _861 = _854 * _860;
    D _862 = _855 * _860;
    D _863 = _856 * _860;
    D _864 = spvNMax(9.9999997473787516355514526367188e-06, _805);
    D _870 = View._m0[161u].z * gl_FragCoord.x;
    D _871 = View._m0[161u].w * gl_FragCoord.y;
    D _881 = (1.0 / ((-0.0) - View._m0[73u].w)) + View._m0[73u].y;
    D _883 = spvNMax(0.0, _881 - _103);
    D _886 = D(uint(gl_FragCoord.x)) + 0.5;
    D _887 = D(uint(gl_FragCoord.y)) + 0.5;
    D _910 = ((View._m0[55u].z + fma(_887, View._m0[53u].z, View._m0[52u].z * _886)) / (fma(_887, View._m0[53u].w, View._m0[52u].w * _886) + View._m0[55u].w)) - View._m0[78u].z;
    D _916 = spvNClamp((1.0 / (_883 + 49.0)) * _883, 0.0, 1.0) * 50.0;
    D _920 = fma(_842, View._m0[22u].x, fma(_841, View._m0[21u].x, _840 * View._m0[20u].x));
    D _923 = fma(_842, View._m0[22u].y, fma(_841, View._m0[21u].y, _840 * View._m0[20u].y));
    D _926 = fma(_842, View._m0[22u].z, fma(_841, View._m0[21u].z, _840 * View._m0[20u].z));
    D _930 = inversesqrt(dot(vec3(_920, _923, _926), vec3(_920, _923, _926)));
    D _931 = spvNMax(10.0, _103);
    D _953 = (((_920 * _916) * _930) * (1.0 / (View._m0[44u].x * _931))) * View._m0[74u].x;
    D _957 = (((_923 * _916) * _930) * (1.0 / (View._m0[45u].y * _931))) * View._m0[74u].y;
    D _974 = ((View._m0[161u].x * _870) - View._m0[158u].x) * View._m0[159u].z;
    D _975 = ((View._m0[161u].y * _871) - View._m0[158u].y) * View._m0[159u].w;
    D _978 = spvNMin(View._m0[159u].z, View._m0[159u].w);
    D _979 = _978 * View._m0[159u].y;
    D _980 = _978 * View._m0[159u].x;
    D _986 = (12.5 / _979) * abs(_953);
    D _987 = (12.5 / _980) * abs(_957);
    D _1008 = (((D(int(uint(_953 > 0.0) - uint(_953 < 0.0))) * 0.07999999821186065673828125) * _979) * _986) * (1.0 / (_986 + 1.0));
    D _1012 = (((D(int(uint(_957 > 0.0) - uint(_957 < 0.0))) * 0.07999999821186065673828125) * _980) * _987) * (1.0 / (_987 + 1.0));
    D _1021 = spvNClamp(abs((_974 * 2.0) + (-1.0)), 0.0, 1.0);
    D _1022 = spvNClamp(abs((_975 * 2.0) + (-1.0)), 0.0, 1.0);
    D _1023 = _1021 * _1021;
    D _1024 = _1022 * _1022;
    D _1032 = (View._m0[158u].x + (-1.0)) + View._m0[159u].x;
    D _1034 = (View._m0[158u].y + (-1.0)) + View._m0[159u].y;
    D _1047 = D(int(uint(int(spvNMin(spvNMax((View._m0[159u].x * ((_1008 + _974) - ((_1023 * _1023) * _1008))) + View._m0[158u].x, View._m0[158u].x), _1032))))) + 0.5;
    D _1048 = D(int(uint(int(spvNMin(spvNMax((View._m0[159u].y * ((_1012 + _975) - ((_1024 * _1024) * _1012))) + View._m0[158u].y, View._m0[158u].y), _1034))))) + 0.5;
    D _1061 = D(uint(spvNMin(spvNMax(View._m0[161u].x * (_1047 * View._m0[161u].z), View._m0[158u].x), _1032))) + 0.5;
    D _1062 = D(uint(spvNMin(spvNMax(View._m0[161u].y * (_1048 * View._m0[161u].w), View._m0[158u].y), _1034))) + 0.5;
    D _1074;
    if (_881 > _103)
    {
        _1074 = spvNClamp(_883 * 0.0199999995529651641845703125, 0.0, 1.0);
    }
    else
    {
        _1074 = 0.0;
    }
    D _1086 = spvNMin(_883, 6550400.0);
    D _1098 = 1.0 - _775;
    D _1112 = ((spvNMin(_1098 * _1098, exp2(_864 * (-9.27999973297119140625))) * _1098) + (0.0425000004470348358154296875 - (_775 * 0.0274999998509883880615234375))) * 1.03999996185302734375;
    D _1118 = 1.0 - spvNClamp((((_775 * 0.02199999988079071044921875) + (-0.039999999105930328369140625)) + _1112) + (((1.03999996185302734375 - (_775 * 0.572000026702880859375)) - _1112) * 0.0203731842339038848876953125), 0.0, 1.0);
    D _1121 = spvNClamp(_1086 * 0.0199999995529651641845703125, 0.0, 1.0) * g_R.Foam;
    D _1122 = spvNMax(0.001000000047497451305389404296875, _1086);
    D _1125 = log2(spvNMax(0.0, _510));
    D _1127 = exp2(_1125 * _1122);
    D _1131 = log2(spvNMax(0.0, exp2(_514)));
    D _1132 = log2(spvNMax(0.0, exp2(_305)));
    D _1133 = log2(spvNMax(0.0, exp2(_306)));
    D _1137 = exp2(_1131 * _1122);
    D _1138 = exp2(_1132 * _1122);
    D _1139 = exp2(_1133 * _1122);
    D _1140 = spvNMax(0.001000000047497451305389404296875, spvNMin(spvNMax(0.0, (_225 - _910) - (_1074 * ((((View._m0[55u].z + fma(_1062, View._m0[53u].z, View._m0[52u].z * _1061)) / (fma(_1062, View._m0[53u].w, View._m0[52u].w * _1061) + View._m0[55u].w)) - _910) - View._m0[78u].z))), 6550400.0));
    D _1142 = exp2(_1125 * _1140);
    D _1149 = 1.0 - _609;
    D _1153 = spvNMax(0.039999999105930328369140625, _775);
    D _1169 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_1153 * _864) + 0.02669160068035125732421875) / (_864 + 0.4664950072765350341796875)) * exp2(((1.0 / _1153) * _864) * log2(_1153)), 0.0, 1.0));
    D _1170 = 1.0 - _864;
    D _1171 = _1170 * _1170;
    D _1186 = ((_1171 * _1171) * _1170) * exp2(log2((exp2((_1153 * 4.7702999114990234375) * log2(_864)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _1153);
    D _1195 = ((((1.0 / _1169) * (1.0 - _1169)) * _785) + 1.0) * (((_1169 - _1186) * _785) + _1186);
    D _1202 = spvNClamp(_1195, 0.0, 1.0);
    D _1213 = spvNClamp(exp2(log2(_864 + 1.0) * exp2((-1.0) - (_775 * 16.0))), 0.0, 1.0);
    D _1239;
    D _1241;
    D _1243;
    D _1245;
    D _1247;
    D _1249;
    D _1251;
    D _1253;
    D _1255;
    D _1257;
    D _1259;
    D _1261;
    if (floatBitsToUint(TranslucentBasePass_2._m0[0u]).z == 0u)
    {
        _1239 = 0.0;
        _1241 = 0.0;
        _1243 = 0.0;
        _1245 = 0.0;
        _1247 = 0.0;
        _1249 = 0.0;
        _1251 = 0.0;
        _1253 = 0.0;
        _1255 = 0.0;
        _1257 = 0.0;
        _1259 = 0.0;
        _1261 = 0.0;
    }
    else
    {
        D _1736;
        uint _1276;
        bool _1277;
        for (;;)
        {
            _1276 = floatBitsToUint(TranslucentBasePass_2._m0[7u]).z;
            _1277 = _1276 == 0u;
            if (!_1277)
            {
                uint _1900;
                uint _1804 = 0u;
                for (;;)
                {
                    if (_103 < TranslucentBasePass._m0[_1804 + 32u])
                    {
                        _1900 = _1804;
                        break;
                    }
                    else
                    {
                        uint _1805 = _1804 + 1u;
                        if (_1805 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                        {
                            _1804 = _1805;
                            continue;
                        }
                        else
                        {
                            _1900 = _1276;
                            break;
                        }
                    }
                }
                if (_1900 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                {
                    uint _2321 = _1900 << 2u;
                    uint _2322 = _2321 + 9u;
                    uint _2329 = _2321 + 10u;
                    uint _2336 = _2321 + 11u;
                    uint _2343 = _2321 + 12u;
                    uint _2351 = _1900 + 25u;
                    D _2377 = fma(_225, TranslucentBasePass_2._m0[_2336].z, fma(_224, TranslucentBasePass_2._m0[_2329].z, TranslucentBasePass_2._m0[_2322].z * _223)) + TranslucentBasePass_2._m0[_2343].z;
                    D _2381 = fma(_225, TranslucentBasePass_2._m0[_2336].w, fma(_224, TranslucentBasePass_2._m0[_2329].w, TranslucentBasePass_2._m0[_2322].w * _223)) + TranslucentBasePass_2._m0[_2343].w;
                    D _2382 = (fma(_225, TranslucentBasePass_2._m0[_2336].x, fma(_224, TranslucentBasePass_2._m0[_2329].x, TranslucentBasePass_2._m0[_2322].x * _223)) + TranslucentBasePass_2._m0[_2343].x) / _2381;
                    D _2383 = (fma(_225, TranslucentBasePass_2._m0[_2336].y, fma(_224, TranslucentBasePass_2._m0[_2329].y, TranslucentBasePass_2._m0[_2322].y * _223)) + TranslucentBasePass_2._m0[_2343].y) / _2381;
                    bool _2390 = (_2383 <= TranslucentBasePass_2._m0[_2351].w) && ((_2382 <= TranslucentBasePass_2._m0[_2351].z) && ((_2382 >= TranslucentBasePass_2._m0[_2351].x) && (_2383 >= TranslucentBasePass_2._m0[_2351].y)));
                    D _1737;
                    if (_2390)
                    {
                        D _2569 = dFdyFine(_2382);
                        D _2570 = dFdyFine(_2383);
                        D _2571 = dFdyFine(_2377);
                        D _2572 = dFdxFine(_2382);
                        D _2573 = dFdxFine(_2383);
                        D _2574 = dFdxFine(_2377);
                        D _2577 = (_2573 * _2571) - (_2574 * _2570);
                        D _2580 = (_2574 * _2569) - (_2572 * _2571);
                        D _2583 = (_2572 * _2570) - (_2573 * _2569);
                        D _2593 = 1.0 / spvNMax(abs(_2583), sqrt(((_2580 * _2580) + (_2583 * _2583)) + (_2577 * _2577)) * 0.100000001490116119384765625);
                        D _2599 = D(int(uint(_2583 > 0.0) - uint(_2583 < 0.0)));
                        D _2600 = _2577 * TranslucentBasePass_2._m0[29u].z;
                        D _2602 = (_2600 * _2593) * _2599;
                        D _2603 = _2580 * TranslucentBasePass_2._m0[29u].w;
                        D _2605 = (_2603 * _2593) * _2599;
                        D _3079;
                        D _3081;
                        if (dot(vec2(_2577, _2580), vec2(_2577, _2580)) < 1.0000000195414813782625560981111e-24)
                        {
                            _3079 = 0.0;
                            _3081 = 0.0;
                        }
                        else
                        {
                            D _3449 = (-0.0) - _2577;
                            D _3450 = (-0.0) - _2580;
                            D _3454 = inversesqrt(dot(vec2(_3449, _3450), vec2(_3449, _3450)));
                            _3079 = _3454 * _3449;
                            _3081 = _3454 * _3450;
                        }
                        D _3083 = _255 + (-0.5);
                        D _3088 = _506 + 0.5;
                        D _3091 = ((_3081 * _3083) + (_2382 * TranslucentBasePass_2._m0[29u].x)) + (_3079 * _3088);
                        D _3094 = ((_3079 * _3083) + (_2383 * TranslucentBasePass_2._m0[29u].y)) + (_3081 * _3088);
                        D _3095 = _3091 + (-0.5);
                        D _3096 = _3094 + (-0.5);
                        D _3097 = trunc(_3095);
                        D _3098 = trunc(_3096);
                        D _3099 = _3095 - _3097;
                        D _3100 = _3096 - _3098;
                        D _3101 = _3097 * TranslucentBasePass_2._m0[29u].z;
                        D _3102 = _3098 * TranslucentBasePass_2._m0[29u].w;
                        D _3105 = (_3097 + (-0.5)) - _3091;
                        D _3106 = (_3098 + (-0.5)) - _3094;
                        D _3107 = dot(vec2(_3105, _3106), vec2(_2602, _2605));
                        D _3110 = _3107 + _2605;
                        D _3113 = _2599 * (_2593 * (_2603 + _2600));
                        D _3114 = _3113 + _3107;
                        D _3115 = _3107 + _2602;
                        vec4 _3121 = textureGather((sampler2D(ShadowMaps[_1900 + 0u], View_SharedPointClampedSampler)), vec2(_3101, _3102));
                        D _3122 = _3121.x;
                        D _3123 = _3121.y;
                        D _3124 = _3121.z;
                        D _3125 = _3121.w;
                        D _3162 = 1.525902189314365386962890625e-05 - _2377;
                        D _3193 = (_3097 + 1.5) - _3091;
                        D _3194 = dot(vec2(_3193, _3106), vec2(_2602, _2605));
                        D _3197 = _3194 + _2605;
                        D _3198 = _3113 + _3194;
                        D _3199 = _3194 + _2602;
                        vec4 _3201 = textureGatherOffset((sampler2D(ShadowMaps[_1900 + 0u], View_SharedPointClampedSampler)), vec2(_3101, _3102), ivec2(2, 0));
                        D _3202 = _3201.x;
                        D _3203 = _3201.y;
                        D _3204 = _3201.z;
                        D _3205 = _3201.w;
                        D _3271 = (_3098 + 1.5) - _3094;
                        D _3272 = dot(vec2(_3105, _3271), vec2(_2602, _2605));
                        D _3275 = _3272 + _2605;
                        D _3276 = _3113 + _3272;
                        D _3277 = _3272 + _2602;
                        vec4 _3279 = textureGatherOffset((sampler2D(ShadowMaps[_1900 + 0u], View_SharedPointClampedSampler)), vec2(_3101, _3102), ivec2(0, 2));
                        D _3280 = _3279.x;
                        D _3281 = _3279.y;
                        D _3282 = _3279.z;
                        D _3283 = _3279.w;
                        D _3348 = dot(vec2(_3193, _3271), vec2(_2602, _2605));
                        D _3351 = _3348 + _2605;
                        D _3352 = _3113 + _3348;
                        D _3353 = _3348 + _2602;
                        vec4 _3355 = textureGatherOffset((sampler2D(ShadowMaps[_1900 + 0u], View_SharedPointClampedSampler)), vec2(_3101, _3102), ivec2(2));
                        D _3356 = _3355.x;
                        D _3357 = _3355.y;
                        D _3358 = _3355.z;
                        D _3359 = _3355.w;
                        D _3424 = 1.0 - _3099;
                        vec4 _3447 = vec4((((((_3125 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3162 + _3125) + (spvNMin(abs(_3107), 0.0) * D(int(uint(_3107 > 0.0) - uint(_3107 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3424) + ((_3124 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3162 + _3124) + (spvNMin(abs(_3115), 0.0) * D(int(uint(_3115 > 0.0) - uint(_3115 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3205 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3162 + _3205) + (spvNMin(abs(_3194), 0.0) * D(int(uint(_3194 > 0.0) - uint(_3194 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3204 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3162 + _3204) + (spvNMin(abs(_3199), 0.0) * D(int(uint(_3199 > 0.0) - uint(_3199 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3099), (((((_3122 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3162 + _3122) + (spvNMin(abs(_3110), 0.0) * D(int(uint(_3110 > 0.0) - uint(_3110 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3424) + ((_3123 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3162 + _3123) + (spvNMin(abs(_3114), 0.0) * D(int(uint(_3114 > 0.0) - uint(_3114 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3202 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3162 + _3202) + (spvNMin(abs(_3197), 0.0) * D(int(uint(_3197 > 0.0) - uint(_3197 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3203 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3162 + _3203) + (spvNMin(abs(_3198), 0.0) * D(int(uint(_3198 > 0.0) - uint(_3198 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3099), (((((_3283 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3162 + _3283) + (spvNMin(abs(_3272), 0.0) * D(int(uint(_3272 > 0.0) - uint(_3272 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3424) + ((_3282 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3162 + _3282) + (spvNMin(abs(_3277), 0.0) * D(int(uint(_3277 > 0.0) - uint(_3277 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3359 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3162 + _3359) + (spvNMin(abs(_3348), 0.0) * D(int(uint(_3348 > 0.0) - uint(_3348 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3358 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3162 + _3358) + (spvNMin(abs(_3353), 0.0) * D(int(uint(_3353 > 0.0) - uint(_3353 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3099), (((((_3280 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3162 + _3280) + (spvNMin(abs(_3275), 0.0) * D(int(uint(_3275 > 0.0) - uint(_3275 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3424) + ((_3281 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3162 + _3281) + (spvNMin(abs(_3276), 0.0) * D(int(uint(_3276 > 0.0) - uint(_3276 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3356 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3162 + _3356) + (spvNMin(abs(_3351), 0.0) * D(int(uint(_3351 > 0.0) - uint(_3351 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3357 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3162 + _3357) + (spvNMin(abs(_3352), 0.0) * D(int(uint(_3352 > 0.0) - uint(_3352 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3099));
                        _1737 = dot(_3447, vec4(1.0 - _3100, 1.0, 1.0, _3100)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        _1737 = 1.0;
                    }
                    if (_2390)
                    {
                        _1736 = _1737;
                        break;
                    }
                }
            }
            if (floatBitsToUint(TranslucentBasePass_2._m0[30u]).y == 0u)
            {
                _1736 = 1.0;
                break;
            }
            D _1777 = fma(_225, TranslucentBasePass_2._m0[35u].z, fma(_224, TranslucentBasePass_2._m0[34u].z, TranslucentBasePass_2._m0[33u].z * _223)) + TranslucentBasePass_2._m0[36u].z;
            D _1781 = fma(_225, TranslucentBasePass_2._m0[35u].w, fma(_224, TranslucentBasePass_2._m0[34u].w, TranslucentBasePass_2._m0[33u].w * _223)) + TranslucentBasePass_2._m0[36u].w;
            D _1782 = (fma(_225, TranslucentBasePass_2._m0[35u].x, fma(_224, TranslucentBasePass_2._m0[34u].x, TranslucentBasePass_2._m0[33u].x * _223)) + TranslucentBasePass_2._m0[36u].x) / _1781;
            D _1783 = (fma(_225, TranslucentBasePass_2._m0[35u].y, fma(_224, TranslucentBasePass_2._m0[34u].y, TranslucentBasePass_2._m0[33u].y * _223)) + TranslucentBasePass_2._m0[36u].y) / _1781;
            uvec4 _1787 = floatBitsToUint(TranslucentBasePass_2._m0[32u]);
            uint _1788 = _1787.x;
            uint _1789 = _1787.y;
            uint _1790 = _1787.z;
            uint _1795 = uint(int(floor(_1782)));
            uint _1796 = uint(int((-0.0) - floor(_1783)));
            if (!((int(_1796) < int(_1787.w)) && ((int(_1795) < int(_1790)) && ((int(_1795) >= int(_1788)) && (int(_1796) >= int(_1789))))))
            {
                _1736 = 1.0;
                break;
            }
            D _1864 = dFdyFine(_1782);
            D _1865 = dFdyFine(_1783);
            D _1866 = dFdyFine(_1777);
            D _1867 = dFdxFine(_1782);
            D _1868 = dFdxFine(_1783);
            D _1869 = dFdxFine(_1777);
            D _1872 = (_1868 * _1866) - (_1869 * _1865);
            D _1875 = (_1869 * _1864) - (_1867 * _1866);
            D _1878 = (_1867 * _1865) - (_1868 * _1864);
            D _1888 = 1.0 / spvNMax(abs(_1878), sqrt(((_1875 * _1875) + (_1878 * _1878)) + (_1872 * _1872)) * 0.100000001490116119384765625);
            D _1894 = D(int(uint(_1878 > 0.0) - uint(_1878 < 0.0)));
            D _2250;
            D _2252;
            if (dot(vec2(_1872, _1875), vec2(_1872, _1875)) < 1.0000000195414813782625560981111e-24)
            {
                _2250 = 0.0;
                _2252 = 0.0;
            }
            else
            {
                D _2314 = (-0.0) - _1872;
                D _2315 = (-0.0) - _1875;
                D _2319 = inversesqrt(dot(vec2(_2314, _2315), vec2(_2314, _2315)));
                _2250 = _2319 * _2314;
                _2252 = _2319 * _2315;
            }
            D _2258 = _255 + (-0.5);
            D _2266 = (((_2252 * _2258) + (_2250 * _506)) * 2.0) + (_2250 * 0.5);
            D _2267 = (((_2252 * _506) + (_2250 * _2258)) * 2.0) + (_2252 * 0.5);
            D _2272 = _2266 + (fract(_1782) * 256.0);
            D _2273 = _2267 + (fract(_1783) * 256.0);
            D _2286 = dot(vec2((floor(_2272) + 0.5) - _2272, (floor(_2273) + 0.5) - _2273), vec2(((_1872 * 256.0) * _1888) * _1894, ((_1875 * 256.0) * _1888) * _1894));
            D _2291 = (_2266 * 0.00390625) + _1782;
            D _2292 = (_2267 * 0.00390625) + _1783;
            uint _2304 = ((uint(int((-0.0) - floor(_2292))) - _1789) * (_1790 - _1788)) + (uint(int(floor(_2291))) - _1788);
            D _2542;
            D _2545;
            if ((texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowLoadedTileData, int(_2304 >> 5u)).x & (1u << (_2304 & 31u))) == 0u)
            {
                _2542 = 3.0000000054977557577780399428115e+38;
                _2545 = 0.0;
            }
            else
            {
                uvec4 _2566 = uvec4(texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileIndices, int(_2304)));
                uint _2567 = _2566.x;
                D frontier_phi_51_52_ladder;
                D frontier_phi_51_52_ladder_1;
                if (int(_2567) > int(4294967295u))
                {
                    uint _3065 = (uint(floor(fract(_2291) * 256.0)) + (_2567 << 16u)) + (uint(floor(fract(_2292) * 256.0)) << 8u);
                    uvec4 _3068 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileData, int(_3065 >> 1u));
                    uint _3069 = _3068.x;
                    D _3077 = D((((_3065 & 1u) == 0u) ? _3069 : (_3069 >> 16u)) & 65535u) * 1.525902189314365386962890625e-05;
                    D frontier_phi_51_52_ladder_68_ladder;
                    D frontier_phi_51_52_ladder_68_ladder_1;
                    if (_3077 != 1.0)
                    {
                        vec4 _3783 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthRanges, int(_2567));
                        D _3785 = _3783.y;
                        D _2546 = (1.0 / _3785) * 10.0;
                        frontier_phi_51_52_ladder_68_ladder = _2546;
                        frontier_phi_51_52_ladder_68_ladder_1 = (_3785 * _3077) + _3783.x;
                    }
                    else
                    {
                        frontier_phi_51_52_ladder_68_ladder = 0.0;
                        frontier_phi_51_52_ladder_68_ladder_1 = 3.0000000054977557577780399428115e+38;
                    }
                    frontier_phi_51_52_ladder = frontier_phi_51_52_ladder_68_ladder;
                    frontier_phi_51_52_ladder_1 = frontier_phi_51_52_ladder_68_ladder_1;
                }
                else
                {
                    frontier_phi_51_52_ladder = 0.0;
                    frontier_phi_51_52_ladder_1 = 3.0000000054977557577780399428115e+38;
                }
                _2542 = frontier_phi_51_52_ladder_1;
                _2545 = frontier_phi_51_52_ladder;
            }
            _1736 = spvNClamp(((((1.525902189314365386962890625e-05 - _1777) + _2542) + (spvNMin(abs(_2286), _2545) * D(int(uint(_2286 > 0.0) - uint(_2286 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0);
            break;
        }
        D _1851;
        if ((floatBitsToUint(Primitive._m0[27u]).z & 2u) == 0u)
        {
            _1851 = 1.0;
        }
        else
        {
            _1851 = View._m0[188u].y;
        }
        uvec4 _1855 = floatBitsToUint(View._m0[220u]);
        uint _1856 = _1855.y;
        uint _1859 = (_1856 != 1u) ? 4294967295u : 0u;
        uint _2248;
        if (_1856 > 1u)
        {
            D _141[4];
            _141[0u] = 0.0;
            _141[1u] = 0.0;
            _141[2u] = 0.0;
            _141[3u] = 0.0;
            uint _2527 = 0u;
            bool _2533;
            for (;;)
            {
                _2533 = _2527 < floatBitsToUint(View._m0[220u]).y;
                if (_2533)
                {
                    uint _3016 = _2527 + 237u;
                    D _3030 = View._m0[_3016].x - View._m0[75u].x;
                    D _3031 = View._m0[_3016].y - View._m0[75u].y;
                    D _3032 = View._m0[_3016].z - View._m0[75u].z;
                    D _3033 = dot(vec3(_3030, _3031, _3032), vec3(_503, _231, _232));
                    D _3040 = dot(vec3(_3030, _3031, _3032), vec3(_3030, _3031, _3032)) - (View._m0[_3016].w * View._m0[_3016].w);
                    D _3042 = (_3033 * _3033) - _3040;
                    D _3597;
                    if ((_3040 < 0.0) && (!(_3042 < 0.0)))
                    {
                        D _3591 = sqrt(_3042);
                        _3597 = spvNMin(abs(_3591 + _3033), abs(_3033 - _3591));
                    }
                    else
                    {
                        _3597 = 0.0;
                    }
                    _141[_2527] = _3597;
                }
                uint _2528 = _2527 + 1u;
                if (_2528 == 4u)
                {
                    break;
                }
                else
                {
                    _2527 = _2528;
                    continue;
                }
            }
            D _3608 = (_506 * 0.99989998340606689453125) * dot(vec4(_141[0u], _141[1u], _141[2u], _141[3u]), vec4(1.0));
            uint frontier_phi_36_76_ladder;
            if (_141[0u] > _3608)
            {
                frontier_phi_36_76_ladder = 0u;
            }
            else
            {
                D _3843 = _141[1u] + _141[0u];
                uint frontier_phi_36_76_ladder_83_ladder;
                if (_3843 > _3608)
                {
                    frontier_phi_36_76_ladder_83_ladder = 1u;
                }
                else
                {
                    D _3854 = _3843 + _141[2u];
                    uint frontier_phi_36_76_ladder_83_ladder_86_ladder;
                    if (_3854 > _3608)
                    {
                        frontier_phi_36_76_ladder_83_ladder_86_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_36_76_ladder_83_ladder_86_ladder_89_ladder;
                        if ((_3854 + _141[3u]) > _3608)
                        {
                            frontier_phi_36_76_ladder_83_ladder_86_ladder_89_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_36_76_ladder_83_ladder_86_ladder_89_ladder = _1859;
                        }
                        frontier_phi_36_76_ladder_83_ladder_86_ladder = frontier_phi_36_76_ladder_83_ladder_86_ladder_89_ladder;
                    }
                    frontier_phi_36_76_ladder_83_ladder = frontier_phi_36_76_ladder_83_ladder_86_ladder;
                }
                frontier_phi_36_76_ladder = frontier_phi_36_76_ladder_83_ladder;
            }
            _2248 = frontier_phi_36_76_ladder;
        }
        else
        {
            _2248 = _1859;
        }
        D _2534;
        if (_2248 == 4294967295u)
        {
            _2534 = _1851;
        }
        else
        {
            _2534 = View._m0[_2248 + 241u].x * _1851;
        }
        D frontier_phi_7_49_ladder;
        D frontier_phi_7_49_ladder_1;
        D frontier_phi_7_49_ladder_2;
        D frontier_phi_7_49_ladder_3;
        D frontier_phi_7_49_ladder_4;
        D frontier_phi_7_49_ladder_5;
        D frontier_phi_7_49_ladder_6;
        D frontier_phi_7_49_ladder_7;
        D frontier_phi_7_49_ladder_8;
        D frontier_phi_7_49_ladder_9;
        D frontier_phi_7_49_ladder_10;
        D frontier_phi_7_49_ladder_11;
        if (_2534 > 0.0)
        {
            D _3049 = spvNClamp((TranslucentBasePass_2._m0[7u].x * _103) + TranslucentBasePass_2._m0[7u].y, 0.0, 1.0);
            D _3053 = ((_3049 * _3049) * (1.0 - _1736)) + _1736;
            D frontier_phi_7_49_ladder_67_ladder;
            D frontier_phi_7_49_ladder_67_ladder_1;
            D frontier_phi_7_49_ladder_67_ladder_2;
            D frontier_phi_7_49_ladder_67_ladder_3;
            D frontier_phi_7_49_ladder_67_ladder_4;
            D frontier_phi_7_49_ladder_67_ladder_5;
            D frontier_phi_7_49_ladder_67_ladder_6;
            D frontier_phi_7_49_ladder_67_ladder_7;
            D frontier_phi_7_49_ladder_67_ladder_8;
            D frontier_phi_7_49_ladder_67_ladder_9;
            D frontier_phi_7_49_ladder_67_ladder_10;
            D frontier_phi_7_49_ladder_67_ladder_11;
            if (_3053 > 0.0)
            {
                D _3610 = dot(vec3(_734, _735, _736), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3613 = spvNMax(0.0, _3610);
                D _3614 = dot(vec3(_504, _233, _505), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3620 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3614 * 2.0) + 2.0));
                D _3623 = spvNClamp(_3620 * (_793 + _3610), 0.0, 1.0);
                D _3636 = sqrt(spvNMax(0.0, 1.0 - (_820 * 0.444444477558135986328125)));
                D _3640 = (_799 * 0.666666686534881591796875) - (_3636 * _734);
                D _3641 = (_800 * 0.666666686534881591796875) - (_3636 * _735);
                D _3642 = (_801 * 0.666666686534881591796875) - (_3636 * _736);
                D _3646 = inversesqrt(dot(vec3(_3640, _3641, _3642), vec3(_3640, _3641, _3642)));
                D _3653 = dot(vec3((-0.0) - (_3646 * _3640), (-0.0) - (_3646 * _3641), (-0.0) - (_3646 * _3642)), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3656 = _1153 * _1153;
                D _3657 = _3656 * _3656;
                D _3661 = ((_3623 * _3623) * (_3657 + (-1.0))) + 1.0;
                D _3667 = (_3613 * 2.0) * _864;
                D _3672 = 1.0 - spvNMax(9.9999997473787516355514526367188e-06, spvNMin(_3620 * (_3614 + 1.0), 1.0));
                D _3673 = _3672 * _3672;
                D _3684 = spvNClamp(((spvNMin(dot(vec3(_785), vec3(16.666667938232421875)), 1.0) - _785) * ((_3673 * _3673) * _3672)) + _785, 0.0, 1.0);
                D _3685 = spvNMax(0.039999999105930328369140625, _1153);
                D _3698 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_3685 * _3613) + 0.02669160068035125732421875) / (_3613 + 0.4664950072765350341796875)) * exp2(((1.0 / _3685) * _3613) * log2(_3685)), 0.0, 1.0));
                D _3699 = 1.0 - _3613;
                D _3700 = _3699 * _3699;
                D _3712 = ((_3700 * _3700) * _3699) * exp2(log2((exp2((_3685 * 4.7702999114990234375) * log2(_3613)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _3685);
                D _3717 = (((1.0 / _3698) * (1.0 - _3698)) * _785) + 1.0;
                D _3726 = spvNClamp(1.0 - dot(vec3(_3717 * (((_3698 - _3712) * _785) + _3712)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                D _3729 = (((_3657 * 0.3183098733425140380859375) * _3613) * (1.0 / (_3661 * _3661))) * (0.5 / ((_3656 * ((_864 + _3613) - _3667)) + _3667));
                D _3743 = (((_3653 * _3653) + 1.0) * 0.0323704965412616729736328125) * exp2(log2(spvNMax(0.0, (_3653 * 1.2000000476837158203125) + 1.36000001430511474609375)) * (-1.5));
                D _3746 = ((_3614 * _3614) + 1.0) * 0.05968309938907623291015625;
                D _3750 = spvNClamp(_3613 * 999.99993896484375, 0.0, 1.0);
                D _3752 = spvNMin(_3053, _3750 * _3750);
                D _3753 = spvNMin(_3053, 1.0);
                D _3754 = _2534 * TranslucentBasePass_2._m0[4u].x;
                D _3755 = _2534 * TranslucentBasePass_2._m0[4u].y;
                D _3756 = _2534 * TranslucentBasePass_2._m0[4u].z;
                frontier_phi_7_49_ladder_67_ladder = (((_3756 * 0.2578310072422027587890625) * _3613) * _3726) * _3752;
                frontier_phi_7_49_ladder_67_ladder_1 = (((_3754 * 0.2578310072422027587890625) * _3613) * _3726) * _3752;
                frontier_phi_7_49_ladder_67_ladder_2 = (((_3755 * 0.2578310072422027587890625) * _3613) * _3726) * _3752;
                frontier_phi_7_49_ladder_67_ladder_3 = (((_3729 * _3754) * _3684) * _3717) * _3752;
                frontier_phi_7_49_ladder_67_ladder_4 = (((_3729 * _3755) * _3684) * _3717) * _3752;
                frontier_phi_7_49_ladder_67_ladder_5 = (((_3729 * _3756) * _3684) * _3717) * _3752;
                frontier_phi_7_49_ladder_67_ladder_6 = (_3743 * _3754) * _3753;
                frontier_phi_7_49_ladder_67_ladder_7 = (_3743 * _3755) * _3753;
                frontier_phi_7_49_ladder_67_ladder_8 = (_3743 * _3756) * _3753;
                frontier_phi_7_49_ladder_67_ladder_9 = (_3746 * _3754) * _3753;
                frontier_phi_7_49_ladder_67_ladder_10 = (_3746 * _3755) * _3753;
                frontier_phi_7_49_ladder_67_ladder_11 = (_3746 * _3756) * _3753;
            }
            else
            {
                frontier_phi_7_49_ladder_67_ladder = 0.0;
                frontier_phi_7_49_ladder_67_ladder_1 = 0.0;
                frontier_phi_7_49_ladder_67_ladder_2 = 0.0;
                frontier_phi_7_49_ladder_67_ladder_3 = 0.0;
                frontier_phi_7_49_ladder_67_ladder_4 = 0.0;
                frontier_phi_7_49_ladder_67_ladder_5 = 0.0;
                frontier_phi_7_49_ladder_67_ladder_6 = 0.0;
                frontier_phi_7_49_ladder_67_ladder_7 = 0.0;
                frontier_phi_7_49_ladder_67_ladder_8 = 0.0;
                frontier_phi_7_49_ladder_67_ladder_9 = 0.0;
                frontier_phi_7_49_ladder_67_ladder_10 = 0.0;
                frontier_phi_7_49_ladder_67_ladder_11 = 0.0;
            }
            frontier_phi_7_49_ladder = frontier_phi_7_49_ladder_67_ladder;
            frontier_phi_7_49_ladder_1 = frontier_phi_7_49_ladder_67_ladder_1;
            frontier_phi_7_49_ladder_2 = frontier_phi_7_49_ladder_67_ladder_2;
            frontier_phi_7_49_ladder_3 = frontier_phi_7_49_ladder_67_ladder_3;
            frontier_phi_7_49_ladder_4 = frontier_phi_7_49_ladder_67_ladder_4;
            frontier_phi_7_49_ladder_5 = frontier_phi_7_49_ladder_67_ladder_5;
            frontier_phi_7_49_ladder_6 = frontier_phi_7_49_ladder_67_ladder_6;
            frontier_phi_7_49_ladder_7 = frontier_phi_7_49_ladder_67_ladder_7;
            frontier_phi_7_49_ladder_8 = frontier_phi_7_49_ladder_67_ladder_8;
            frontier_phi_7_49_ladder_9 = frontier_phi_7_49_ladder_67_ladder_9;
            frontier_phi_7_49_ladder_10 = frontier_phi_7_49_ladder_67_ladder_10;
            frontier_phi_7_49_ladder_11 = frontier_phi_7_49_ladder_67_ladder_11;
        }
        else
        {
            frontier_phi_7_49_ladder = 0.0;
            frontier_phi_7_49_ladder_1 = 0.0;
            frontier_phi_7_49_ladder_2 = 0.0;
            frontier_phi_7_49_ladder_3 = 0.0;
            frontier_phi_7_49_ladder_4 = 0.0;
            frontier_phi_7_49_ladder_5 = 0.0;
            frontier_phi_7_49_ladder_6 = 0.0;
            frontier_phi_7_49_ladder_7 = 0.0;
            frontier_phi_7_49_ladder_8 = 0.0;
            frontier_phi_7_49_ladder_9 = 0.0;
            frontier_phi_7_49_ladder_10 = 0.0;
            frontier_phi_7_49_ladder_11 = 0.0;
        }
        _1239 = frontier_phi_7_49_ladder_1;
        _1241 = frontier_phi_7_49_ladder_2;
        _1243 = frontier_phi_7_49_ladder;
        _1245 = frontier_phi_7_49_ladder_3;
        _1247 = frontier_phi_7_49_ladder_4;
        _1249 = frontier_phi_7_49_ladder_5;
        _1251 = frontier_phi_7_49_ladder_6;
        _1253 = frontier_phi_7_49_ladder_7;
        _1255 = frontier_phi_7_49_ladder_8;
        _1257 = frontier_phi_7_49_ladder_9;
        _1259 = frontier_phi_7_49_ladder_10;
        _1261 = frontier_phi_7_49_ladder_11;
    }
    uvec4 _1265 = floatBitsToUint(TranslucentBasePass_2._m0[0u]);
    uint _1266 = _1265.x;
    uint _1271 = min(min(texelFetch(TranslucentBasePass_Shared_Forward_NumCulledLightsGrid, int(0u)).x, _1266), _1266);
    D _1278;
    D _1280;
    D _1282;
    D _1284;
    D _1286;
    D _1288;
    D _1290;
    D _1292;
    D _1294;
    D _1296;
    D _1298;
    D _1300;
    D _1302;
    D _1304;
    D _1306;
    D _1308;
    D _1310;
    D _1312;
    if (_1271 == 0u)
    {
        _1278 = _1239;
        _1280 = _1241;
        _1282 = _1243;
        _1284 = _1245;
        _1286 = _1247;
        _1288 = _1249;
        _1290 = _1251;
        _1292 = _1253;
        _1294 = _1255;
        _1296 = _1257;
        _1298 = _1259;
        _1300 = _1261;
        _1302 = 0.0;
        _1304 = 0.0;
        _1306 = 0.0;
        _1308 = 0.0;
        _1310 = 0.0;
        _1312 = 0.0;
    }
    else
    {
        D _1279;
        D _1281;
        D _1283;
        D _1285;
        D _1287;
        D _1289;
        D _1291;
        D _1293;
        D _1295;
        D _1297;
        D _1299;
        D _1301;
        D _1303;
        D _1305;
        D _1307;
        D _1309;
        D _1311;
        D _1313;
        D _1649 = _1239;
        D _1650 = _1241;
        D _1651 = _1243;
        D _1652 = _1245;
        D _1653 = _1247;
        D _1654 = _1249;
        D _1655 = _1251;
        D _1656 = _1253;
        D _1657 = _1255;
        D _1658 = _1257;
        D _1659 = _1259;
        D _1660 = _1261;
        D _1661 = 0.0;
        D _1662 = 0.0;
        D _1663 = 0.0;
        D _1664 = 0.0;
        D _1665 = 0.0;
        D _1666 = 0.0;
        uint _1667 = 0u;
        D _1671;
        D _1672;
        D _1673;
        D _1674;
        D _1676;
        D _1677;
        D _1678;
        D _1680;
        D _1681;
        D _1682;
        uint _1684;
        D _1686;
        D _1687;
        D _1689;
        D _1690;
        D _1691;
        D _1693;
        D _1694;
        uint _1696;
        D _1698;
        D _1699;
        D _1700;
        D _1701;
        uint _1704;
        D _1706;
        D _1707;
        D _1708;
        D _1709;
        D _1712;
        D _1713;
        D _1714;
        D _1715;
        D _1718;
        D _1719;
        D _1720;
        D _1721;
        D _1724;
        D _1725;
        D _1726;
        D _1727;
        bool _1730;
        bool _1731;
        bool _1735;
        for (;;)
        {
            vec4 _1670 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(0u));
            _1671 = _1670.x;
            _1672 = _1670.y;
            _1673 = _1670.z;
            _1674 = _1670.w;
            vec4 _1675 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(1u));
            _1676 = _1675.x;
            _1677 = _1675.y;
            _1678 = _1675.z;
            vec4 _1679 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(2u));
            _1680 = _1679.x;
            _1681 = _1679.y;
            _1682 = _1679.z;
            _1684 = floatBitsToUint(_1679.w);
            vec4 _1685 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(3u));
            _1686 = _1685.x;
            _1687 = _1685.y;
            vec4 _1688 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(4u));
            _1689 = _1688.x;
            _1690 = _1688.y;
            _1691 = _1688.z;
            vec4 _1692 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(5u));
            _1693 = _1692.x;
            _1694 = _1692.y;
            _1696 = floatBitsToUint(_1692.z);
            vec4 _1697 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(6u));
            _1698 = _1697.x;
            _1699 = _1697.y;
            _1700 = _1697.z;
            _1701 = _1697.w;
            _1704 = floatBitsToUint(texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(7u)).x);
            vec4 _1705 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(8u));
            _1706 = _1705.x;
            _1707 = _1705.y;
            _1708 = _1705.z;
            _1709 = _1705.w;
            vec4 _1711 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(9u));
            _1712 = _1711.x;
            _1713 = _1711.y;
            _1714 = _1711.z;
            _1715 = _1711.w;
            vec4 _1717 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(10u));
            _1718 = _1717.x;
            _1719 = _1717.y;
            _1720 = _1717.z;
            _1721 = _1717.w;
            vec4 _1723 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(11u));
            _1724 = _1723.x;
            _1725 = _1723.y;
            _1726 = _1723.z;
            _1727 = _1723.w;
            _1730 = (_1684 & 131072u) != 0u;
            _1731 = _1686 > (-2.0);
            _1735 = (_1684 & 16384u) == 0u;
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
            D frontier_phi_47_pred_15;
            D frontier_phi_47_pred_16;
            D frontier_phi_47_pred_17;
            if (_1735)
            {
                D _2201;
                if (_1730)
                {
                    uint _2166 = _1704 + 0u;
                    uvec2 _2169 = uvec2(textureSize(ShadowMaps[(_2166)], int(0u)));
                    D _2171 = D(int(_2169.x));
                    D _2173 = D(int(_2169.y));
                    D _2174 = 1.0 / _2171;
                    D _2175 = 1.0 / _2173;
                    D _2187 = fma(_225, _1720, fma(_224, _1714, _1708 * _223)) + _1726;
                    D _2191 = fma(_225, _1721, fma(_224, _1715, _1709 * _223)) + _1727;
                    D _2192 = (fma(_225, _1718, fma(_224, _1712, _1706 * _223)) + _1724) / _2191;
                    D _2193 = (fma(_225, _1719, fma(_224, _1713, _1707 * _223)) + _1725) / _2191;
                    D frontier_phi_32_31_ladder;
                    if ((_2193 <= _1701) && ((_2192 <= _1700) && ((_2192 >= _1698) && (_2193 >= _1699))))
                    {
                        D _2408 = dFdyFine(_2192);
                        D _2409 = dFdyFine(_2193);
                        D _2410 = dFdyFine(_2187);
                        D _2411 = dFdxFine(_2192);
                        D _2412 = dFdxFine(_2193);
                        D _2413 = dFdxFine(_2187);
                        D _2416 = (_2412 * _2410) - (_2413 * _2409);
                        D _2419 = (_2413 * _2408) - (_2411 * _2410);
                        D _2422 = (_2411 * _2409) - (_2412 * _2408);
                        D _2432 = 1.0 / spvNMax(abs(_2422), sqrt(((_2419 * _2419) + (_2422 * _2422)) + (_2416 * _2416)) * 0.100000001490116119384765625);
                        D _2438 = D(int(uint(_2422 > 0.0) - uint(_2422 < 0.0)));
                        D _2439 = _2416 * _2174;
                        D _2441 = (_2439 * _2432) * _2438;
                        D _2442 = _2419 * _2175;
                        D _2444 = (_2442 * _2432) * _2438;
                        D _2611;
                        D _2613;
                        if (dot(vec2(_2416, _2419), vec2(_2416, _2419)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2611 = 0.0;
                            _2613 = 0.0;
                        }
                        else
                        {
                            D _2954 = (-0.0) - _2416;
                            D _2955 = (-0.0) - _2419;
                            D _2959 = inversesqrt(dot(vec2(_2954, _2955), vec2(_2954, _2955)));
                            _2611 = _2959 * _2954;
                            _2613 = _2959 * _2955;
                        }
                        D _2615 = _255 + (-0.5);
                        D _2620 = _506 + 0.5;
                        D _2623 = ((_2613 * _2615) + (_2192 * _2171)) + (_2611 * _2620);
                        D _2626 = ((_2611 * _2615) + (_2193 * _2173)) + (_2613 * _2620);
                        D _2627 = _2623 + (-0.5);
                        D _2628 = _2626 + (-0.5);
                        D _2629 = trunc(_2627);
                        D _2630 = trunc(_2628);
                        D _2631 = _2627 - _2629;
                        D _2632 = _2628 - _2630;
                        D _2633 = _2629 * _2174;
                        D _2634 = _2630 * _2175;
                        D _2637 = (_2629 + (-0.5)) - _2623;
                        D _2638 = (_2630 + (-0.5)) - _2626;
                        D _2639 = dot(vec2(_2637, _2638), vec2(_2441, _2444));
                        D _2642 = _2639 + _2444;
                        D _2645 = _2438 * (_2432 * (_2442 + _2439));
                        D _2646 = _2645 + _2639;
                        D _2647 = _2639 + _2441;
                        vec4 _2651 = textureGather((sampler2D(ShadowMaps[_2166], View_SharedPointClampedSampler)), vec2(_2633, _2634));
                        D _2692 = 1.525902189314365386962890625e-05 - _2187;
                        D _2715 = (_2629 + 1.5) - _2623;
                        D _2716 = dot(vec2(_2715, _2638), vec2(_2441, _2444));
                        D _2719 = _2716 + _2444;
                        D _2720 = _2645 + _2716;
                        D _2721 = _2716 + _2441;
                        vec4 _2725 = textureGatherOffset((sampler2D(ShadowMaps[_2166], View_SharedPointClampedSampler)), vec2(_2633, _2634), ivec2(2, 0));
                        D _2789 = (_2630 + 1.5) - _2626;
                        D _2790 = dot(vec2(_2637, _2789), vec2(_2441, _2444));
                        D _2793 = _2790 + _2444;
                        D _2794 = _2645 + _2790;
                        D _2795 = _2790 + _2441;
                        vec4 _2797 = textureGatherOffset((sampler2D(ShadowMaps[_2166], View_SharedPointClampedSampler)), vec2(_2633, _2634), ivec2(0, 2));
                        D _2859 = dot(vec2(_2715, _2789), vec2(_2441, _2444));
                        D _2862 = _2859 + _2444;
                        D _2863 = _2645 + _2859;
                        D _2864 = _2859 + _2441;
                        vec4 _2866 = textureGatherOffset((sampler2D(ShadowMaps[_2166], View_SharedPointClampedSampler)), vec2(_2633, _2634), ivec2(2));
                        D _2928 = 1.0 - _2631;
                        vec4 _2951 = vec4((((spvNClamp((((_2692 + _2651.w) + (spvNMin(abs(_2639), 0.0) * D(int(uint(_2639 > 0.0) - uint(_2639 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2928) + spvNClamp((((_2692 + _2651.z) + (spvNMin(abs(_2647), 0.0) * D(int(uint(_2647 > 0.0) - uint(_2647 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2692 + _2725.w) + (spvNMin(abs(_2716), 0.0) * D(int(uint(_2716 > 0.0) - uint(_2716 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2692 + _2725.z) + (spvNMin(abs(_2721), 0.0) * D(int(uint(_2721 > 0.0) - uint(_2721 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2631), (((spvNClamp((((_2692 + _2651.x) + (spvNMin(abs(_2642), 0.0) * D(int(uint(_2642 > 0.0) - uint(_2642 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2928) + spvNClamp((((_2692 + _2651.y) + (spvNMin(abs(_2646), 0.0) * D(int(uint(_2646 > 0.0) - uint(_2646 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2692 + _2725.x) + (spvNMin(abs(_2719), 0.0) * D(int(uint(_2719 > 0.0) - uint(_2719 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2692 + _2725.y) + (spvNMin(abs(_2720), 0.0) * D(int(uint(_2720 > 0.0) - uint(_2720 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2631), (((spvNClamp((((_2692 + _2797.w) + (spvNMin(abs(_2790), 0.0) * D(int(uint(_2790 > 0.0) - uint(_2790 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2928) + spvNClamp((((_2692 + _2797.z) + (spvNMin(abs(_2795), 0.0) * D(int(uint(_2795 > 0.0) - uint(_2795 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2692 + _2866.w) + (spvNMin(abs(_2859), 0.0) * D(int(uint(_2859 > 0.0) - uint(_2859 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2692 + _2866.z) + (spvNMin(abs(_2864), 0.0) * D(int(uint(_2864 > 0.0) - uint(_2864 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2631), (((spvNClamp((((_2692 + _2797.x) + (spvNMin(abs(_2793), 0.0) * D(int(uint(_2793 > 0.0) - uint(_2793 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2928) + spvNClamp((((_2692 + _2797.y) + (spvNMin(abs(_2794), 0.0) * D(int(uint(_2794 > 0.0) - uint(_2794 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2692 + _2866.x) + (spvNMin(abs(_2862), 0.0) * D(int(uint(_2862 > 0.0) - uint(_2862 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2692 + _2866.y) + (spvNMin(abs(_2863), 0.0) * D(int(uint(_2863 > 0.0) - uint(_2863 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2631));
                        frontier_phi_32_31_ladder = dot(_2951, vec4(1.0 - _2632, 1.0, 1.0, _2632)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        frontier_phi_32_31_ladder = 1.0;
                    }
                    _2201 = frontier_phi_32_31_ladder;
                }
                else
                {
                    _2201 = 1.0;
                }
                D _2207 = _1671 - _223;
                D _2208 = _1672 - _224;
                D _2209 = _1673 - _225;
                D _2210 = dot(vec3(_2207, _2208, _2209), vec3(_2207, _2208, _2209));
                D _2453;
                D _2454;
                D _2455;
                if (_2210 > 9.9999997473787516355514526367188e-05)
                {
                    D _2449 = inversesqrt(_2210);
                    _2453 = _2449 * _2207;
                    _2454 = _2449 * _2208;
                    _2455 = _2449 * _2209;
                }
                else
                {
                    _2453 = 0.0;
                    _2454 = 0.0;
                    _2455 = 0.0;
                }
                D _2456 = _1693 * _1693;
                D _2460 = (_1674 * _1674) * _2210;
                D _2463 = spvNClamp(1.0 - (_2460 * _2460), 0.0, 1.0);
                D _2967;
                if (_1731)
                {
                    D _2965 = spvNClamp((dot(vec3(_2453, _2454, _2455), vec3(_1680, _1681, _1682)) - _1686) * _1687, 0.0, 1.0);
                    _2967 = _2965 * _2965;
                }
                else
                {
                    _2967 = 1.0;
                }
                D _2968 = ((_2463 * _2463) * D(_2210 >= _2456)) * _2967;
                D _3455;
                D _3457;
                D _3459;
                if ((_1684 & 262144u) == 0u)
                {
                    _3455 = 1.0;
                    _3457 = 1.0;
                    _3459 = 1.0;
                }
                else
                {
                    D _3462 = (-0.0) - _1681;
                    D _3463 = (-0.0) - _1682;
                    D _3464 = (-0.0) - _1680;
                    D _3474 = (-0.0) - _2453;
                    D _3475 = (-0.0) - _2454;
                    D _3476 = (-0.0) - _2455;
                    D _3479 = fma(_3463, _3476, fma(_3462, _3475, _2453 * _1680));
                    D _3482 = fma(_1691, _3476, fma(_1690, _3475, _1689 * _3474));
                    D _3490 = atan(((-0.0) - _3482) / ((-0.0) - _3479));
                    bool _3495 = _3479 > (-0.0);
                    bool _3496 = _3479 == (-0.0);
                    bool _3497 = _3482 <= (-0.0);
                    bool _3498 = _3482 > (-0.0);
                    vec4 _3520 = texture((sampler2D(ForwardLightProfileTextures[_1696 + 0u], View_SharedBilinearWrappedSampler)), vec2(fract((_3496 && _3497) ? 1.25 : ((_3496 && _3498) ? 0.75 : ((((_3495 && _3498) ? (_3490 + (-3.1415927410125732421875)) : ((_3495 && _3497) ? (_3490 + 3.1415927410125732421875) : _3490)) * 0.15915493667125701904296875) + 1.0))), (asin((-0.0) - fma((_1690 * _3464) - (_1689 * _3462), _3476, fma((_1689 * _3463) - (_1691 * _3464), _3475, ((_1691 * _3462) - (_1690 * _3463)) * _3474))) * 0.3183098733425140380859375) + 0.5));
                    _3455 = _3520.x;
                    _3457 = _3520.y;
                    _3459 = _3520.z;
                }
                D _3788;
                D _3790;
                D _3792;
                D _3794;
                D _3796;
                D _3798;
                D _3800;
                D _3802;
                D _3804;
                D _3806;
                D _3808;
                D _3810;
                for (;;)
                {
                    if (_2968 > 0.0)
                    {
                        D _3846;
                        if (_1730)
                        {
                            if (!(_2201 > 0.0))
                            {
                                _3788 = 0.0;
                                _3790 = 0.0;
                                _3792 = 0.0;
                                _3794 = 0.0;
                                _3796 = 0.0;
                                _3798 = 0.0;
                                _3800 = 0.0;
                                _3802 = 0.0;
                                _3804 = 0.0;
                                _3806 = 0.0;
                                _3808 = 0.0;
                                _3810 = 0.0;
                                break;
                            }
                            _3846 = _2201;
                        }
                        else
                        {
                            _3846 = 1.0;
                        }
                        D _3848 = spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _2210));
                        D _3849 = 1.0 / _3848;
                        D _3850 = dot(vec3(_734, _735, _736), vec3(_2453, _2454, _2455));
                        D _3861;
                        if (_1693 > 0.0)
                        {
                            D _3858 = sqrt(spvNClamp(_2456 * _3849, 0.0, 1.0));
                            D frontier_phi_88_87_ladder;
                            if (_3858 > spvNMax(9.9999997473787516355514526367188e-06, _3850))
                            {
                                D _3878 = spvNMax((-0.0) - _3858, _3850) + _3858;
                                frontier_phi_88_87_ladder = (_3878 * _3878) * (0.25 / _3858);
                            }
                            else
                            {
                                frontier_phi_88_87_ladder = _3850;
                            }
                            _3861 = frontier_phi_88_87_ladder;
                        }
                        else
                        {
                            _3861 = _3850;
                        }
                        D _3918;
                        D _3919;
                        D _3920;
                        D _3863;
                        D _3865;
                        D _3869;
                        D _3870;
                        bool _3873;
                        for (;;)
                        {
                            _3863 = spvNMax(0.0, _3861);
                            _3865 = _1153 * _1153;
                            _3869 = spvNClamp(((1.0 - _3865) * _1693) * inversesqrt(_3848), 0.0, 1.0);
                            _3870 = dot(vec3(_504, _233, _505), vec3(_2453, _2454, _2455));
                            _3873 = _3869 > 0.0;
                            D _3889;
                            D _3891;
                            if (_3873)
                            {
                                D _3884 = sqrt(spvNMax(0.0, 1.0 - (_3869 * _3869)));
                                D _3887 = ((_3850 * 2.0) * _793) - _3870;
                                if (!(!(_3887 >= _3884)))
                                {
                                    _3918 = _805;
                                    _3919 = 1.0;
                                    _3920 = _3870;
                                    break;
                                }
                                D _3907 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, 1.0 - (_3887 * _3887))) * _3869;
                                _3889 = (_3907 * (((_819 * 2.0) + (-1.0)) - (_3887 * _3870))) + (_3884 * _3870);
                                _3891 = (_3907 * (_793 - (_3887 * _3850))) + (_3884 * _3850);
                            }
                            else
                            {
                                _3889 = _3870;
                                _3891 = _3850;
                            }
                            D _3896 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3889 * 2.0) + 2.0));
                            _3918 = spvNMin(_3896 * (_3889 + 1.0), 1.0);
                            _3919 = spvNClamp(_3896 * (_3891 + _793), 0.0, 1.0);
                            _3920 = _3889;
                            break;
                        }
                        D _3921 = spvNMax(9.9999997473787516355514526367188e-06, _3918);
                        D _3928 = sqrt(spvNMax(0.0, 1.0 - (_820 * 0.444444477558135986328125)));
                        D _3932 = (_799 * 0.666666686534881591796875) - (_3928 * _734);
                        D _3933 = (_800 * 0.666666686534881591796875) - (_3928 * _735);
                        D _3934 = (_801 * 0.666666686534881591796875) - (_3928 * _736);
                        D _3938 = inversesqrt(dot(vec3(_3932, _3933, _3934), vec3(_3932, _3933, _3934)));
                        D _3945 = dot(vec3((-0.0) - (_3938 * _3932), (-0.0) - (_3938 * _3933), (-0.0) - (_3938 * _3934)), vec3(_2453, _2454, _2455));
                        D _3948 = _3865 * _3865;
                        D _3962 = ((_3919 * _3919) * (_3948 + (-1.0))) + 1.0;
                        D _3968 = (_3863 * 2.0) * _864;
                        D _3973 = 1.0 - _3921;
                        D _3974 = _3973 * _3973;
                        D _3984 = spvNClamp(((spvNMin(dot(vec3(_785), vec3(16.666667938232421875)), 1.0) - _785) * ((_3974 * _3974) * _3973)) + _785, 0.0, 1.0);
                        D _3985 = spvNMax(0.039999999105930328369140625, _1153);
                        D _3998 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_3985 * _3863) + 0.02669160068035125732421875) / (_3863 + 0.4664950072765350341796875)) * exp2(((1.0 / _3985) * _3863) * log2(_3985)), 0.0, 1.0));
                        D _3999 = 1.0 - _3863;
                        D _4000 = _3999 * _3999;
                        D _4012 = ((_4000 * _4000) * _3999) * exp2(log2((exp2((_3985 * 4.7702999114990234375) * log2(_3863)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _3985);
                        D _4017 = (((1.0 / _3998) * (1.0 - _3998)) * _785) + 1.0;
                        D _4026 = spvNClamp(1.0 - dot(vec3(_4017 * (((_3998 - _4012) * _785) + _4012)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                        D _4030 = ((((_3948 * 0.3183098733425140380859375) * _3863) * (1.0 / (_3962 * _3962))) * (_3873 ? ((1.0 / ((((_3869 * 0.25) * (_3869 + (_3865 * 3.0))) * (1.0 / _3921)) + _3948)) * _3948) : 1.0)) * (0.5 / ((_3865 * ((_864 + _3863) - _3968)) + _3968));
                        D _4040 = (((_3945 * _3945) + 1.0) * 0.0323704965412616729736328125) * exp2(log2(spvNMax(0.0, (_3945 * 1.2000000476837158203125) + 1.36000001430511474609375)) * (-1.5));
                        D _4043 = ((_3920 * _3920) + 1.0) * 0.05968309938907623291015625;
                        D _4045 = spvNClamp(_3863 * 999.99993896484375, 0.0, 1.0);
                        D _4047 = spvNMin(_3846, _4045 * _4045);
                        D _4048 = spvNMin(_3846, 1.0);
                        D _4052 = (_2968 * _1676) * _3455;
                        D _4053 = (_2968 * _1677) * _3457;
                        D _4054 = (_2968 * _1678) * _3459;
                        D _4055 = _3849 * _4052;
                        D _4059 = _3849 * _4053;
                        D _4063 = _3849 * _4054;
                        _3788 = ((((_4052 * 0.2578310072422027587890625) * _3849) * _3863) * _4026) * _4047;
                        _3790 = ((((_4053 * 0.2578310072422027587890625) * _3849) * _3863) * _4026) * _4047;
                        _3792 = ((((_4054 * 0.2578310072422027587890625) * _3849) * _3863) * _4026) * _4047;
                        _3794 = (((_4055 * _3984) * _4030) * _4017) * _4047;
                        _3796 = (((_4059 * _4030) * _3984) * _4017) * _4047;
                        _3798 = (((_4063 * _4030) * _3984) * _4017) * _4047;
                        _3800 = (_4055 * _4040) * _4048;
                        _3802 = (_4059 * _4040) * _4048;
                        _3804 = (_4063 * _4040) * _4048;
                        _3806 = (_4055 * _4043) * _4048;
                        _3808 = (_4059 * _4043) * _4048;
                        _3810 = (_4063 * _4043) * _4048;
                        break;
                    }
                    else
                    {
                        _3788 = 0.0;
                        _3790 = 0.0;
                        _3792 = 0.0;
                        _3794 = 0.0;
                        _3796 = 0.0;
                        _3798 = 0.0;
                        _3800 = 0.0;
                        _3802 = 0.0;
                        _3804 = 0.0;
                        _3806 = 0.0;
                        _3808 = 0.0;
                        _3810 = 0.0;
                        break;
                    }
                }
                frontier_phi_47_pred = _3806 + _1658;
                frontier_phi_47_pred_1 = _3788 + _1649;
                frontier_phi_47_pred_2 = _3790 + _1650;
                frontier_phi_47_pred_3 = _3792 + _1651;
                frontier_phi_47_pred_4 = _3794 + _1652;
                frontier_phi_47_pred_5 = _3796 + _1653;
                frontier_phi_47_pred_6 = _3798 + _1654;
                frontier_phi_47_pred_7 = _3800 + _1655;
                frontier_phi_47_pred_8 = _3802 + _1656;
                frontier_phi_47_pred_9 = _3804 + _1657;
                frontier_phi_47_pred_10 = _3808 + _1659;
                frontier_phi_47_pred_11 = _1666;
                frontier_phi_47_pred_12 = _1665;
                frontier_phi_47_pred_13 = _1664;
                frontier_phi_47_pred_14 = _1663;
                frontier_phi_47_pred_15 = _1662;
                frontier_phi_47_pred_16 = _1661;
                frontier_phi_47_pred_17 = _3810 + _1660;
            }
            else
            {
                D _1834 = _1671 - _223;
                D _1835 = _1672 - _224;
                D _1836 = _1673 - _225;
                D _1837 = dot(vec3(_1834, _1835, _1836), vec3(_1834, _1835, _1836));
                D _1841 = (_1674 * _1674) * _1837;
                D _1842 = _1841 * _1841;
                D _1843 = _1842 * _1842;
                D _1846 = spvNClamp(1.0 - (_1843 * _1843), 0.0, 1.0);
                D _1847 = _1846 * _1846;
                D _1848 = _1847 * _1847;
                D _1849 = _1848 * _1848;
                D _2225;
                D _2227;
                D _2229;
                D _2231;
                D _2233;
                D _2235;
                if (_1849 > 0.0)
                {
                    D _2217 = dot(vec3(_503, _231, _232), vec3(_734, _735, _736)) * 2.0;
                    D _2221 = _503 - (_2217 * _734);
                    D _2222 = _231 - (_2217 * _735);
                    D _2223 = _232 - (_2217 * _736);
                    D _3522;
                    D _3523;
                    D _3524;
                    D _3525;
                    D _3526;
                    D _3527;
                    D _3528;
                    D _3529;
                    D _3530;
                    D _3531;
                    D _3532;
                    if (_1694 == 0.0)
                    {
                        D _2973;
                        D _2974;
                        D _2975;
                        if (_1837 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2969 = inversesqrt(_1837);
                            _2973 = _2969 * _1834;
                            _2974 = _2969 * _1835;
                            _2975 = _2969 * _1836;
                        }
                        else
                        {
                            _2973 = 0.0;
                            _2974 = 0.0;
                            _2975 = 0.0;
                        }
                        D _2978 = 1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1837));
                        _3522 = _2978;
                        _3523 = (_1693 * _1693) * _2978;
                        _3524 = _2973;
                        _3525 = _2974;
                        _3526 = _2975;
                        _3527 = _2973;
                        _3528 = _2974;
                        _3529 = _2975;
                        _3530 = _2973;
                        _3531 = _2974;
                        _3532 = _2975;
                    }
                    else
                    {
                        D _2467 = _1694 * 0.5;
                        D _2468 = _2467 * _1680;
                        D _2469 = _2467 * _1681;
                        D _2470 = _2467 * _1682;
                        D _2471 = _1834 - _2468;
                        D _2472 = _1835 - _2469;
                        D _2473 = _1836 - _2470;
                        D _2474 = _2468 + _1834;
                        D _2475 = _2469 + _1835;
                        D _2476 = _2470 + _1836;
                        D _2484 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2471, _2472, _2473), vec3(_2471, _2472, _2473))));
                        D _2486 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2474, _2475, _2476), vec3(_2474, _2475, _2476))));
                        D _2487 = _2486 * _2484;
                        D _2503 = (1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(_2487, ((dot(vec3(_2471, _2472, _2473), vec3(_2474, _2475, _2476)) * 0.5) * _2487) + 0.5))) * _2487;
                        D _2505 = (_1680 * 2.0) * _2467;
                        D _2507 = (_1681 * 2.0) * _2467;
                        D _2509 = (_1682 * 2.0) * _2467;
                        D _2510 = dot(vec3(_2505, _2507, _2509), vec3(_2505, _2507, _2509));
                        D _3011;
                        D _3012;
                        D _3013;
                        if (_2510 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2981 = dot(vec3(_2221, _2222, _2223), vec3(_2505, _2507, _2509));
                            D _2997 = spvNClamp((1.0 / (_2510 - (_2981 * _2981))) * dot(vec3(_2471, _2472, _2473), vec3((_2981 * _2221) - _2505, (_2981 * _2222) - _2507, (_2981 * _2223) - _2509)), 0.0, 1.0);
                            D _3001 = (_2997 * _2505) + _2471;
                            D _3002 = (_2997 * _2507) + _2472;
                            D _3003 = (_2997 * _2509) + _2473;
                            D _3007 = inversesqrt(dot(vec3(_3001, _3002, _3003), vec3(_3001, _3002, _3003)));
                            _3011 = _3001 * _3007;
                            _3012 = _3002 * _3007;
                            _3013 = _3003 * _3007;
                        }
                        else
                        {
                            _3011 = _2471;
                            _3012 = _2472;
                            _3013 = _2473;
                        }
                        _3522 = _2503;
                        _3523 = (_1693 * _1693) * _2503;
                        _3524 = _2484 * _2471;
                        _3525 = _2484 * _2472;
                        _3526 = _2484 * _2473;
                        _3527 = _2486 * _2474;
                        _3528 = _2486 * _2475;
                        _3529 = _2486 * _2476;
                        _3530 = _3011;
                        _3531 = _3012;
                        _3532 = _3013;
                    }
                    D _3542 = _3523 + 1.0;
                    D _3547 = _3530 - _503;
                    D _3548 = _3531 - _231;
                    D _3549 = _3532 - _232;
                    D _3553 = inversesqrt(dot(vec3(_3547, _3548, _3549), vec3(_3547, _3548, _3549)));
                    D _3554 = _3553 * _3547;
                    D _3555 = _3553 * _3548;
                    D _3556 = _3553 * _3549;
                    D _3563 = spvNClamp(dot(vec3(_734, _735, _736), vec3(_3554, _3555, _3556)), 0.0, 1.0);
                    D _3564 = _1153 * _1153;
                    D _3570 = spvNClamp(((1.0 - _3564) * _1693) * sqrt(_3522), 0.0, 1.0);
                    D _3583 = exp2(log2(spvNClamp((((_3570 * 0.25) * (_3570 + (_3564 * 3.0))) * (1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_504, _233, _505), vec3(_3554, _3555, _3556))))) + (_3564 * _3564), 0.0, 1.0)) * 0.25);
                    D _3587 = spvNClamp(dot(vec3(_3524, _3525, _3526), vec3(_3527, _3528, _3529)), 0.0, 1.0);
                    D _3589 = _3583 * _3583;
                    D _3590 = _3589 * _3589;
                    D _3826;
                    if (_3587 < 1.0)
                    {
                        D _3817 = sqrt(spvNClamp((1.0 / (_3587 + 1.0)) * (1.0 - _3587), 0.0, 1.0));
                        _3826 = (1.0 / spvNClamp(((_3817 * 0.25) * (_3817 + (_3589 * 3.0))) + _3590, 0.0, 1.0)) * _3590;
                    }
                    else
                    {
                        _3826 = 1.0;
                    }
                    D _3830 = ((_3563 * _3563) * (_3590 + (-1.0))) + 1.0;
                    D _3833 = spvNMax(0.0, (((dot(vec3(_734, _735, _736), vec3(_3527, _3528, _3529)) + dot(vec3(_734, _735, _736), vec3(_3524, _3525, _3526))) * 0.5) + _3523) * (1.0 / (_3542 * _3542))) * 0.3183098733425140380859375;
                    D _3836 = ((_3833 * _3590) * _3826) * (1.0 / (_3830 * _3830));
                    D _3838 = (_1849 * _1676) * _3522;
                    D _3840 = (_1849 * _1677) * _3522;
                    D _3842 = (_1849 * _1678) * _3522;
                    _2225 = _3836 * _3838;
                    _2227 = _3836 * _3840;
                    _2229 = _3836 * _3842;
                    _2231 = _3833 * _3838;
                    _2233 = _3833 * _3840;
                    _2235 = _3833 * _3842;
                }
                else
                {
                    _2225 = 0.0;
                    _2227 = 0.0;
                    _2229 = 0.0;
                    _2231 = 0.0;
                    _2233 = 0.0;
                    _2235 = 0.0;
                }
                frontier_phi_47_pred = _1658;
                frontier_phi_47_pred_1 = _1649;
                frontier_phi_47_pred_2 = _1650;
                frontier_phi_47_pred_3 = _1651;
                frontier_phi_47_pred_4 = _1652;
                frontier_phi_47_pred_5 = _1653;
                frontier_phi_47_pred_6 = _1654;
                frontier_phi_47_pred_7 = _1655;
                frontier_phi_47_pred_8 = _1656;
                frontier_phi_47_pred_9 = _1657;
                frontier_phi_47_pred_10 = _1659;
                frontier_phi_47_pred_11 = _2235 + _1666;
                frontier_phi_47_pred_12 = _2233 + _1665;
                frontier_phi_47_pred_13 = _2231 + _1664;
                frontier_phi_47_pred_14 = _2229 + _1663;
                frontier_phi_47_pred_15 = _2227 + _1662;
                frontier_phi_47_pred_16 = _2225 + _1661;
                frontier_phi_47_pred_17 = _1660;
            }
            _1297 = frontier_phi_47_pred;
            _1279 = frontier_phi_47_pred_1;
            _1281 = frontier_phi_47_pred_2;
            _1283 = frontier_phi_47_pred_3;
            _1285 = frontier_phi_47_pred_4;
            _1287 = frontier_phi_47_pred_5;
            _1289 = frontier_phi_47_pred_6;
            _1291 = frontier_phi_47_pred_7;
            _1293 = frontier_phi_47_pred_8;
            _1295 = frontier_phi_47_pred_9;
            _1299 = frontier_phi_47_pred_10;
            _1313 = frontier_phi_47_pred_11;
            _1311 = frontier_phi_47_pred_12;
            _1309 = frontier_phi_47_pred_13;
            _1307 = frontier_phi_47_pred_14;
            _1305 = frontier_phi_47_pred_15;
            _1303 = frontier_phi_47_pred_16;
            _1301 = frontier_phi_47_pred_17;
            uint _1668 = _1667 + 1u;
            if (_1668 == _1271)
            {
                break;
            }
            else
            {
                _1649 = _1279;
                _1650 = _1281;
                _1651 = _1283;
                _1652 = _1285;
                _1653 = _1287;
                _1654 = _1289;
                _1655 = _1291;
                _1656 = _1293;
                _1657 = _1295;
                _1658 = _1297;
                _1659 = _1299;
                _1660 = _1301;
                _1661 = _1303;
                _1662 = _1305;
                _1663 = _1307;
                _1664 = _1309;
                _1665 = _1311;
                _1666 = _1313;
                _1667 = _1668;
                continue;
            }
        }
        _1278 = _1279;
        _1280 = _1281;
        _1282 = _1283;
        _1284 = _1285;
        _1286 = _1287;
        _1288 = _1289;
        _1290 = _1291;
        _1292 = _1293;
        _1294 = _1295;
        _1296 = _1297;
        _1298 = _1299;
        _1300 = _1301;
        _1302 = _1303;
        _1304 = _1305;
        _1306 = _1307;
        _1308 = _1309;
        _1310 = _1311;
        _1312 = _1313;
    }
    D _1315 = (_1127 * _1118) * (1.0 - ((_1121 * _1149) + _609));
    D _1325 = (spvNClamp(1.0 - dot(vec3(_1195), vec3(0.3333333432674407958984375)), 0.0, 1.0) * 0.810000002384185791015625) * spvNMax(1.0, 1.0000092983245849609375 - (_782 * 4.57651913166046142578125e-06));
    D _1354;
    D _1355;
    D _1356;
    if (_510 < 1.0)
    {
        _1354 = _264.x / ((_514 / _286) + 1.0);
        _1355 = _264.y / ((_305 / _286) + 1.0);
        _1356 = _264.z / ((_306 / _286) + 1.0);
    }
    else
    {
        _1354 = 0.0;
        _1355 = 0.0;
        _1356 = 0.0;
    }
    D _1361 = View._m0[164u].z * ENVIRONMENT_AMBIENT_DICE_.x;
    D _1362 = View._m0[164u].z * ENVIRONMENT_AMBIENT_DICE_.y;
    D _1363 = View._m0[164u].z * ENVIRONMENT_AMBIENT_DICE_.z;
    D _1364 = spvNClamp(_861, 0.0, 1.0);
    D _1365 = spvNClamp(_862, 0.0, 1.0);
    D _1366 = spvNClamp(_863, 0.0, 1.0);
    D _1376 = spvNClamp((-0.0) - _861, 0.0, 1.0);
    D _1377 = spvNClamp((-0.0) - _862, 0.0, 1.0);
    D _1378 = spvNClamp((-0.0) - _863, 0.0, 1.0);
    D _1385 = dot(vec3(ENVIRONMENT_AMBIENT_DICE_2.x, ENVIRONMENT_AMBIENT_DICE_2.y, ENVIRONMENT_AMBIENT_DICE_2.z), vec3(_1376 * _1376, _1377 * _1377, _1378 * _1378)) + dot(vec3(ENVIRONMENT_AMBIENT_DICE_1.x, ENVIRONMENT_AMBIENT_DICE_1.y, ENVIRONMENT_AMBIENT_DICE_1.z), vec3(_1364 * _1364, _1365 * _1365, _1366 * _1366));
    D _1386 = dot(vec3(ENVIRONMENT_AMBIENT_DICE_.x, ENVIRONMENT_AMBIENT_DICE_.y, ENVIRONMENT_AMBIENT_DICE_.z), vec3(0.2125999927520751953125, 0.715200006961822509765625, 0.072200000286102294921875));
    D _1394 = (_1386 > 0.0) ? (1.0 / _1386) : 0.0;
    D _1425 = ((_1354 * _1118) * spvNClamp(1.0 - (_1137 * _1127), 0.0, 1.0)) * ((_1361 + _1290) + ((((_1361 * _1385) * _1394) - _1361) * 0.6480000019073486328125));
    D _1428 = ((_1355 * _1118) * spvNClamp(1.0 - (_1138 * _1127), 0.0, 1.0)) * ((_1362 + _1292) + ((((_1362 * _1385) * _1394) - _1362) * 0.6480000019073486328125));
    D _1431 = ((_1356 * _1118) * spvNClamp(1.0 - (_1139 * _1127), 0.0, 1.0)) * ((_1363 + _1294) + ((((_1363 * _1385) * _1394) - _1363) * 0.6480000019073486328125));
    D _1445 = spvNClamp(_1149, 0.0, 1.0);
    D _1455 = ((_734 - _816) * _847) + _816;
    D _1456 = ((_735 - _817) * _847) + _817;
    D _1457 = ((_736 - _818) * _847) + _818;
    D _1461 = inversesqrt(dot(vec3(_1455, _1456, _1457), vec3(_1455, _1456, _1457)));
    D _1470 = 10.0 / spvNMax(9.9999997473787516355514526367188e-06, _846);
    D _1498 = fma(_222, View._m0[2u].x, fma(_221, View._m0[1u].x, View._m0[0u].x * _220)) + View._m0[3u].x;
    D _1502 = fma(_222, View._m0[2u].y, fma(_221, View._m0[1u].y, View._m0[0u].y * _220)) + View._m0[3u].y;
    D _1506 = fma(_222, View._m0[2u].z, fma(_221, View._m0[1u].z, View._m0[0u].z * _220)) + View._m0[3u].z;
    D _1510 = fma(_222, View._m0[2u].w, fma(_221, View._m0[1u].w, View._m0[0u].w * _220)) + View._m0[3u].w;
    D _1517 = ((_1455 * _103) * _1461) + _220;
    D _1518 = ((_1456 * _103) * _1461) + _221;
    D _1519 = ((_1457 * _103) * _1461) + _222;
    D _1552 = 1.0 / _1510;
    D _1553 = _1552 * _1498;
    D _1554 = _1552 * _1502;
    D _1558 = (_1552 * _1506) + (0.0500000007450580596923828125 / _1510);
    D _1559 = 1.0 / (fma(_1519, View._m0[2u].w, fma(_1518, View._m0[1u].w, View._m0[0u].w * _1517)) + View._m0[3u].w);
    D _1570 = 1.0 / ((View._m0[36u].w * _1470) + _1510);
    D _1573 = (_1559 * (fma(_1519, View._m0[2u].x, fma(_1518, View._m0[1u].x, View._m0[0u].x * _1517)) + View._m0[3u].x)) - _1553;
    D _1574 = (_1559 * (fma(_1519, View._m0[2u].y, fma(_1518, View._m0[1u].y, View._m0[0u].y * _1517)) + View._m0[3u].y)) - _1554;
    D _1576 = (_1570 * ((View._m0[36u].x * _1470) + _1498)) - _1553;
    D _1577 = (_1570 * ((View._m0[36u].y * _1470) + _1502)) - _1554;
    D _1582 = sqrt((_1573 * _1573) + (_1574 * _1574)) * 0.5;
    D _1600 = spvNMin(1.0 - (spvNMax(0.0, abs((_1582 * _1553) + _1573) - _1582) / abs(_1573)), 1.0 - (spvNMax(0.0, abs((_1582 * _1554) + _1574) - _1582) / abs(_1574))) / _1582;
    D _1601 = _1600 * _1573;
    D _1602 = _1600 * _1574;
    D _1603 = _1600 * ((_1559 * (fma(_1519, View._m0[2u].z, fma(_1518, View._m0[1u].z, View._m0[0u].z * _1517)) + View._m0[3u].z)) - _1558);
    uvec2 _1609 = uvec2(textureSize(TranslucentBasePass_HZBTexture, int(0u)));
    D _1611 = D(int(_1609.x));
    D _1613 = D(int(_1609.y));
    uint _1634 = max(1u, min(uint(ceil((spvNClamp((1.0 / spvNMax(9.9999997473787516355514526367188e-05, sqrt((_1601 * _1601) + (_1602 * _1602)))) * sqrt((_1576 * _1576) + (_1577 * _1577)), 0.0, 1.0) * 8.0) + _506)), 8u));
    D _1639 = ((_1553 * 0.5) + 0.5) * TranslucentBasePass_2._m0[198u].x;
    D _1640 = (0.5 - (_1554 * 0.5)) * TranslucentBasePass_2._m0[198u].y;
    D _1642 = (TranslucentBasePass_2._m0[198u].x * 0.0625) * _1601;
    D _1645 = (TranslucentBasePass_2._m0[198u].y * (-0.0625)) * _1602;
    D _1646 = _1603 * 0.125;
    D _1647 = spvNMax(abs(_1603), _1558 - ((1.0 / (fma(_103, View._m0[38u].w, 0.0) + _1510)) * (fma(_103, View._m0[38u].z, 0.0) + _1506))) * 0.125;
    D _1817;
    D _1819;
    D _1821;
    D _1823;
    if (_1634 == 0u)
    {
        _1817 = 0.0;
        _1819 = 0.0;
        _1821 = 0.0;
        _1823 = 0.0;
    }
    else
    {
        D frontier_phi_55;
        D frontier_phi_55_1;
        D frontier_phi_55_2;
        D frontier_phi_55_3;
        D _2138 = 0.0;
        uint _2140 = 0u;
        D _2139;
        D _2142;
        bool _2165;
        for (;;)
        {
            _2142 = D(_2140);
            D _2143 = _2142 + _506;
            vec4 _2157 = texelFetch(TranslucentBasePass_HZBTexture, ivec2_(uvec2(uint(int(floor(((_2143 * _1642) + _1639) * _1611))), uint(int(floor(((_2143 * _1645) + _1640) * _1613))))), int(0u));
            D _2159 = _2157.x;
            _2139 = ((_2143 * _1646) + _1558) - _2159;
            _2165 = (abs(((-0.0) - _1647) - _2139) < _1647) && (_2159 != 0.0);
            if (_2165)
            {
                D _2393 = (_2140 == 0u) ? (_2139 - _1646) : _2138;
                D _2400 = abs(((_506 + (-1.0)) + _2142) + spvNClamp(_2393 / (_2393 - _2139), 0.0, 1.0));
                D _2405 = spvNMin(_2400 * 0.125, 1.0);
                frontier_phi_55 = 1.0 - (_2405 * _2405);
                frontier_phi_55_1 = (_2400 * _1646) + _1558;
                frontier_phi_55_2 = (_2400 * _1645) + _1640;
                frontier_phi_55_3 = (_2400 * _1642) + _1639;
                break;
            }
            else
            {
                uint _2141 = _2140 + 1u;
                if (_2141 < _1634)
                {
                    _2138 = _2139;
                    _2140 = _2141;
                    continue;
                }
                else
                {
                    frontier_phi_55 = 0.0;
                    frontier_phi_55_1 = 0.0;
                    frontier_phi_55_2 = 0.0;
                    frontier_phi_55_3 = 0.0;
                    break;
                }
            }
        }
        _1817 = frontier_phi_55_3;
        _1819 = frontier_phi_55_2;
        _1821 = frontier_phi_55_1;
        _1823 = frontier_phi_55;
    }
    D _1831 = (spvNClamp(_1817 * TranslucentBasePass_2._m0[198u].z, 0.0, 1.0) * 2.0) + (-1.0);
    D _1832 = 1.0 - (spvNClamp(_1819 * TranslucentBasePass_2._m0[198u].w, 0.0, 1.0) * 2.0);
    D _2059;
    D _2060;
    D _2061;
    D _2062;
    if (_1823 > 0.0)
    {
        D _1922 = ((View._m0[73u].x * _1821) + View._m0[73u].y) + (1.0 / ((View._m0[73u].z * _1821) - View._m0[73u].w));
        D _1946 = _1922 * _1831;
        D _1947 = _1922 * _1832;
        D _1958 = (_220 - View._m0[63u].x) - fma(_1922, View._m0[62u].x, fma(_1947, View._m0[61u].x, _1946 * View._m0[60u].x));
        D _1960 = (_221 - View._m0[63u].y) - fma(_1922, View._m0[62u].y, fma(_1947, View._m0[61u].y, _1946 * View._m0[60u].y));
        D _1962 = (_222 - View._m0[63u].z) - fma(_1922, View._m0[62u].z, fma(_1947, View._m0[61u].z, _1946 * View._m0[60u].z));
        uvec2 _2013 = uvec2(textureSize(TranslucentBasePass_SceneColorCopyTexture, int(0u)));
        uint _2032 = uint(min(int(uint(max(int(uint(int(D(int(_2013.x)) * ((View._m0[74u].x * spvNMin(spvNMax(_1831 - ((D(int(uint(_1831 > 0.0) - uint(_1831 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1831) + (-1.0))), -1.0), 1.0)) + View._m0[74u].w)))), int(uint(int(View._m0[158u].x)))))), int(uint(int(View._m0[159u].x + View._m0[158u].x)) + 4294967295u)));
        uint _2033 = uint(min(int(uint(max(int(uint(int(D(int(_2013.y)) * ((View._m0[74u].y * spvNMin(spvNMax(_1832 - ((D(int(uint(_1832 > 0.0) - uint(_1832 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1832) + (-1.0))), -1.0), 1.0)) + View._m0[74u].z)))), int(uint(int(View._m0[158u].y)))))), int(uint(int(View._m0[159u].y + View._m0[158u].y)) + 4294967295u)));
        vec4 _2038 = texelFetch(TranslucentBasePass_SceneColorCopyTexture, ivec2_(uvec2(_2032, _2033)), int(0u));
        _2059 = View._m0[164u].z * spvNMin(_2038.x, 65504.0);
        _2060 = View._m0[164u].z * spvNMin(_2038.y, 65504.0);
        _2061 = View._m0[164u].z * spvNMin(_2038.z, 65504.0);
        _2062 = (D(texelFetch(TranslucentBasePass_SceneTextures_SceneDepthTexture, ivec2_(uvec2(_2032, _2033)), int(0u)).x != 0.0) * _1823) * spvNClamp(1.0 / spvNMax(9.9999997473787516355514526367188e-06, (_846 * _846) * dot(vec3(_1958, _1960, _1962), vec3(_1958, _1960, _1962))), 0.0, 1.0);
    }
    else
    {
        _2059 = 0.0;
        _2060 = 0.0;
        _2061 = 0.0;
        _2062 = 0.0;
    }
    vec4 _2087 = textureLod(sampler2D(TranslucentBasePass_SceneColorCopyTexture, View_SharedBilinearClampedSampler), vec2((_1074 * (View._m0[161u].z * (_1047 - gl_FragCoord.x))) + _870, (_1074 * (View._m0[161u].w * (_1048 - gl_FragCoord.y))) + _871), 0.0);
    SV_Target.x = View._m0[164u].y * (((((((_1325 * _1308) + _1278) * _609) + _1284) + ((((((_1361 + _1296) * 0.979626834392547607421875) - _1425) * _1121) + _1425) * _1445)) + (((View._m0[164u].z * _2087.x) * spvNClamp(((_1315 * _1137) * _1142) * exp2(_1131 * _1140), 0.0, 1.0)) * _1445)) + ((_1213 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _2059)) + 29.8973522186279296875) * _2062) + (-29.8973522186279296875)) + _1302)) * _1202));
    SV_Target.y = View._m0[164u].y * (((((((_1325 * _1310) + _1280) * _609) + _1286) + ((((((_1362 + _1298) * 0.979626834392547607421875) - _1428) * _1121) + _1428) * _1445)) + (((View._m0[164u].z * _2087.y) * spvNClamp(((_1315 * _1138) * _1142) * exp2(_1132 * _1140), 0.0, 1.0)) * _1445)) + ((_1213 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _2060)) + 29.8973522186279296875) * _2062) + (-29.8973522186279296875)) + _1304)) * _1202));
    SV_Target.z = View._m0[164u].y * (((((((_1325 * _1312) + _1282) * _609) + _1288) + ((((((_1363 + _1300) * 0.979626834392547607421875) - _1431) * _1121) + _1431) * _1445)) + (((View._m0[164u].z * _2087.z) * spvNClamp(((_1315 * _1139) * _1142) * exp2(_1133 * _1140), 0.0, 1.0)) * _1445)) + ((_1213 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _2061)) + 29.8973522186279296875) * _2062) + (-29.8973522186279296875)) + _1306)) * _1202));
    SV_Target.w = 1.0;
    SV_Target_1.x = 1.0;
    SV_Target_1.y = 1.0;
    SV_Target_1.z = 1.0;
    SV_Target_1.w = 0.0;
    discard_exit(); if (g_discarded) return;
}



void set_inputs(Inputs& in) {
    in.get("TEXCOORD_10", TEXCOORD_10);
    in.get("TEXCOORD_11", TEXCOORD_11);
    in.get("TEXCOORD", TEXCOORD);
    in.get("VERTEX_EXPRESSION", VERTEX_EXPRESSION);
    in.get("CONSTANT_CONTEXT", CONSTANT_CONTEXT);
    in.get("ENVIRONMENT_AMBIENT_DICE_", ENVIRONMENT_AMBIENT_DICE_);
    in.get("ENVIRONMENT_AMBIENT_DICE_1", ENVIRONMENT_AMBIENT_DICE_1);
    in.get("ENVIRONMENT_AMBIENT_DICE_2", ENVIRONMENT_AMBIENT_DICE_2);
}
void get_outputs(Outputs& o) {
    o.put("SV_Target", SV_Target);
    o.put("SV_Target_1", SV_Target_1);
}
} // namespace S_cean_Water_Pool_Environment_Development