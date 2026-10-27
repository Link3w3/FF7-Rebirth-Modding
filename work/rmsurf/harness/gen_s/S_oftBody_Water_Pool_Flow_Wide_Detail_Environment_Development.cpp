namespace S_oftBody_Water_Pool_Flow_Wide_Detail_Environment_Development {
using namespace cpuglsl;
static D _4612;
static D _4608;
static D _4609;
static D _4610;
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
static Tex2D TranslucentBasePass_SceneTextures_SceneDepthTexture{texid("TranslucentBasePass_SceneTextures_SceneDepthTexture")};
static Tex2D TranslucentBasePass_HZBTexture{texid("TranslucentBasePass_HZBTexture")};
static Tex3D TranslucentBasePass_TranslucencyLightingVolumeEnvironmentA{texid("TranslucentBasePass_TranslucencyLightingVolumeEnvironmentA")};
static Tex3D TranslucentBasePass_TranslucencyLightingVolumeEnvironmentB{texid("TranslucentBasePass_TranslucencyLightingVolumeEnvironmentB")};
static Tex3D TranslucentBasePass_TranslucencyLightingVolumeEnvironmentC{texid("TranslucentBasePass_TranslucencyLightingVolumeEnvironmentC")};
static Tex2D TranslucentBasePass_SceneColorCopyTexture{texid("TranslucentBasePass_SceneColorCopyTexture")};
static Tex2D Material_Texture2D_0{texid("junk:T_Color")};
static Tex2D Material_Texture2D_1{texid("junk:T_Metallic")};
static Tex2D Material_Texture2D_2{texid("junk:T_Normal")};
static Tex2D Material_Texture2D_3{texid("junk:T_Roughness")};
static Tex2D Material_Texture2D_4{texid("junk:T_Occlusion")};
static Tex2D Material_Texture2D_7{texid("junk:T_Detail")};
static Tex2D Material_Texture2D_8{texid("junk:T_Opacity")};
static Tex2D Material_Texture2D_15{texid("junk:T_Foam")};
static Tex2D Material_Texture2D_16{texid("junk:T_WideFlowPhase")};
static Tex2D Material_Texture2D_17{texid("junk:T_WideFlowDirectivity")};
static Tex2D Material_Texture2D_18{texid("junk:T_WideFoamThreshold")};
static Tex2D Material_Texture2D_20{texid("junk:T_DetailNormal")};
static Tex2D Material_Texture2D_21{texid("junk:T_DetailRoughness")};
static Tex2D Material_Texture2D_23{texid("junk:T_DetailFoam")};
static Tex2D Material_Texture2D_25{texid("junk:T_Muddiness")};
static Tex2D Material_Texture2D_26{texid("junk:T_Transparency")};
static Tex2D Material_Texture2D_27{texid("junk:T_TransparencyCoefficient")};
static Tex2D Material_Texture2D_28{texid("junk:T_Transmittance")};
static Tex2D Material_Texture2D_29{texid("junk:T_TransmittanceCoefficient")};
static Tex2D Material_Texture2D_30{texid("junk:T_Thickness")};
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
static vec4 TEXCOORD_1;
static D CONSTANT_CONTEXT;
static vec4 SV_Target;
static vec4 SV_Target_1;
static bool discard_state;










void discard_cond(bool _4598)
{
    if (_4598)
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
    D _116 = 1.0 / gl_FragCoord.w;
    D _240 = fma(gl_FragCoord.z, View._m0[54u].w, fma(gl_FragCoord.y, View._m0[53u].w, View._m0[52u].w * gl_FragCoord.x)) + View._m0[55u].w;
    D _241 = (fma(gl_FragCoord.z, View._m0[54u].x, fma(gl_FragCoord.y, View._m0[53u].x, View._m0[52u].x * gl_FragCoord.x)) + View._m0[55u].x) / _240;
    D _242 = (fma(gl_FragCoord.z, View._m0[54u].y, fma(gl_FragCoord.y, View._m0[53u].y, View._m0[52u].y * gl_FragCoord.x)) + View._m0[55u].y) / _240;
    D _243 = (fma(gl_FragCoord.z, View._m0[54u].z, fma(gl_FragCoord.y, View._m0[53u].z, View._m0[52u].z * gl_FragCoord.x)) + View._m0[55u].z) / _240;
    D _244 = _241 - View._m0[78u].x;
    D _245 = _242 - View._m0[78u].y;
    D _246 = _243 - View._m0[78u].z;
    D _251 = inversesqrt(dot(vec3(_241, _242, _243), vec3(_241, _242, _243)));
    D _252 = _251 * _241;
    D _253 = _251 * _242;
    D _254 = _251 * _243;
    D _255 = (-0.0) - _252;
    D _257 = (-0.0) - _253;
    D _258 = (-0.0) - _254;
    vec4 _276 = texelFetch(View_SpatiotemporalBlueNoiseVolumeTexture, ivec3_(uvec3(uint(int(gl_FragCoord.x)) & 127u, uint(int(gl_FragCoord.y)) & 127u, ((floatBitsToUint(View._m0[175u]).x & 7u) + uint(roundEven(CONSTANT_CONTEXT))) & 63u)), int(0u));
    D _279 = _276.x;
    D _280 = _276.y;
    vec4 _298 = texture(sampler2D(Material_Texture2D_16, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.z, TEXCOORD.w), View._m0[155u].y);
    D _301 = _298.x;
    vec4 _304 = texture(sampler2D(Material_Texture2D_17, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.z, TEXCOORD.w), View._m0[155u].y);
    D _306 = _304.x;
    vec4 _309 = texture(sampler2D(Material_Texture2D_0, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _316 = texture(sampler2D(Material_Texture2D_1, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _319 = _306 * Material._m0[20u].y;
    D _322 = fract(_301 + (Material._m0[19u].z * Material._m0[20u].x));
    D _323 = _319 * TEXCOORD_1.z;
    D _324 = _319 * TEXCOORD_1.w;
    D _325 = _322 * _323;
    D _326 = _322 * _324;
    D _327 = TEXCOORD.x - _325;
    D _328 = TEXCOORD.y - _326;
    D _330 = (_323 + TEXCOORD.x) - _325;
    D _332 = (_324 + TEXCOORD.y) - _326;
    D _334 = spvNClamp(_322, 0.0, 1.0);
    D _340 = (_334 * _334) * (3.0 - (_334 * 2.0));
    D _341 = _306 * Material._m0[21u].y;
    D _344 = fract(_301 + (Material._m0[19u].z * Material._m0[21u].x));
    D _345 = _341 * TEXCOORD_1.z;
    D _346 = _341 * TEXCOORD_1.w;
    D _347 = _344 * _345;
    D _348 = _344 * _346;
    D _349 = TEXCOORD_1.x - _347;
    D _350 = TEXCOORD_1.y - _348;
    D _352 = (_345 + TEXCOORD_1.x) - _347;
    D _354 = (_346 + TEXCOORD_1.y) - _348;
    D _355 = spvNClamp(_344, 0.0, 1.0);
    D _359 = (_355 * _355) * (3.0 - (_355 * 2.0));
    vec4 _363 = texture(sampler2D(Material_Texture2D_2, View_SharedAnisotropic4XWrappedSampler), vec2(_327, _328), View._m0[155u].y);
    vec4 _367 = texture(sampler2D(Material_Texture2D_2, View_SharedAnisotropic4XWrappedSampler), vec2(_330, _332), View._m0[155u].y);
    D _373 = (_363.x * 2.0) + (-1.0);
    D _375 = (_363.y * 2.0) + (-1.0);
    D _381 = sqrt(spvNMax(0.0, 1.0 - dot(vec2(_373, _375), vec2(_373, _375))));
    D _385 = inversesqrt(dot(vec3(_373, _375, _381), vec3(_373, _375, _381)));
    D _386 = _385 * _373;
    D _387 = _385 * _375;
    D _388 = _385 * _381;
    D _391 = (_367.x * 2.0) + (-1.0);
    D _392 = (_367.y * 2.0) + (-1.0);
    D _398 = sqrt(spvNMax(0.0, 1.0 - dot(vec2(_391, _392), vec2(_391, _392))));
    D _402 = inversesqrt(dot(vec3(_391, _392, _398), vec3(_391, _392, _398)));
    D _412 = (((_402 * _391) - _386) * _340) + _386;
    D _413 = (((_402 * _392) - _387) * _340) + _387;
    D _414 = (((_402 * _398) - _388) * _340) + _388;
    D _418 = inversesqrt(dot(vec3(_412, _413, _414), vec3(_412, _413, _414)));
    D _419 = _412 * _418;
    D _420 = _413 * _418;
    D _421 = _414 * _418;
    vec4 _424 = texture(sampler2D(Material_Texture2D_3, View_SharedAnisotropic4XWrappedSampler), vec2(_327, _328), View._m0[155u].y);
    D _426 = _424.x;
    vec4 _427 = texture(sampler2D(Material_Texture2D_3, View_SharedAnisotropic4XWrappedSampler), vec2(_330, _332), View._m0[155u].y);
    D _429 = _427.x;
    D _431 = _426 * _426;
    D _436 = sqrt(spvNClamp((((_429 * _429) - _431) * _340) + _431, 0.0, 1.0));
    vec4 _439 = texture(sampler2D(Material_Texture2D_4, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _444 = texture(sampler2D(Material_Texture2D_15, View_SharedAnisotropic4XWrappedSampler), vec2(_327, _328), View._m0[155u].y);
    D _446 = _444.x;
    vec4 _447 = texture(sampler2D(Material_Texture2D_15, View_SharedAnisotropic4XWrappedSampler), vec2(_330, _332), View._m0[155u].y);
    D _453 = spvNClamp(((_447.x - _446) * _340) + _446, 0.0, 1.0);
    vec4 _456 = texture(sampler2D(Material_Texture2D_7, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _458 = _456.x;
    vec4 _461 = texture(sampler2D(Material_Texture2D_18, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.z, TEXCOORD.w), View._m0[155u].y);
    vec4 _466 = texture(sampler2D(Material_Texture2D_20, View_SharedAnisotropic4XWrappedSampler), vec2(_349, _350), View._m0[155u].y);
    vec4 _470 = texture(sampler2D(Material_Texture2D_20, View_SharedAnisotropic4XWrappedSampler), vec2(_352, _354), View._m0[155u].y);
    D _476 = (_466.x * 2.0) + (-1.0);
    D _477 = (_466.y * 2.0) + (-1.0);
    D _483 = sqrt(spvNMax(0.0, 1.0 - dot(vec2(_476, _477), vec2(_476, _477))));
    D _487 = inversesqrt(dot(vec3(_476, _477, _483), vec3(_476, _477, _483)));
    D _488 = _487 * _476;
    D _489 = _487 * _477;
    D _490 = _487 * _483;
    D _493 = (_470.x * 2.0) + (-1.0);
    D _494 = (_470.y * 2.0) + (-1.0);
    D _500 = sqrt(spvNMax(0.0, 1.0 - dot(vec2(_493, _494), vec2(_493, _494))));
    D _504 = inversesqrt(dot(vec3(_493, _494, _500), vec3(_493, _494, _500)));
    D _505 = _504 * _493;
    D _506 = _504 * _494;
    D _512 = dFdyFine(TEXCOORD.x) + dFdxFine(TEXCOORD.x);
    D _513 = dFdyFine(TEXCOORD.y) + dFdxFine(TEXCOORD.y);
    D _517 = inversesqrt(dot(vec2(_512, _513), vec2(_512, _513)));
    bool _518 = isnan(_517);
    D _521 = _518 ? 0.0 : (_517 * _512);
    D _522 = _518 ? 0.0 : (_517 * _513);
    D _527 = dFdyFine(_349) + dFdxFine(_349);
    D _528 = dFdyFine(_350) + dFdxFine(_350);
    D _532 = inversesqrt(dot(vec2(_527, _528), vec2(_527, _528)));
    bool _533 = isnan(_532);
    D _536 = _533 ? 0.0 : (_532 * _527);
    D _537 = _533 ? 0.0 : (_532 * _528);
    D _538 = dot(vec2(_536, _537), vec2(_521, _522));
    D _543 = (_536 * _522) - (_537 * _521);
    D _545 = dot(vec2(_488, _489), vec2(_538, (-0.0) - _543));
    D _548 = dot(vec2(_488, _489), vec2(_543, _538));
    D _555 = dFdyFine(_352) + dFdxFine(_352);
    D _556 = dFdyFine(_354) + dFdxFine(_354);
    D _560 = inversesqrt(dot(vec2(_555, _556), vec2(_555, _556)));
    bool _561 = isnan(_560);
    D _564 = _561 ? 0.0 : (_560 * _555);
    D _565 = _561 ? 0.0 : (_560 * _556);
    D _566 = dot(vec2(_564, _565), vec2(_521, _522));
    D _571 = (_564 * _522) - (_565 * _521);
    D _585 = ((dot(vec2(_505, _506), vec2(_566, (-0.0) - _571)) - _545) * _359) + _545;
    D _586 = ((dot(vec2(_505, _506), vec2(_571, _566)) - _548) * _359) + _548;
    D _587 = (((_504 * _500) - _490) * _359) + _490;
    D _591 = inversesqrt(dot(vec3(_585, _586, _587), vec3(_585, _586, _587)));
    D _592 = _591 * _587;
    D _593 = _421 + 1.0;
    D _595 = (-0.0) - (_591 * _585);
    D _597 = (-0.0) - (_591 * _586);
    D _598 = dot(vec3(_419, _420, _593), vec3(_595, _597, _592));
    D _605 = (_598 * _419) - (_593 * _595);
    D _606 = (_598 * _420) - (_593 * _597);
    D _608 = (_598 - _592) * _593;
    D _612 = inversesqrt(dot(vec3(_605, _606, _608), vec3(_605, _606, _608)));
    D _613 = _605 * _612;
    D _614 = _606 * _612;
    D _615 = _608 * _612;
    D _616 = spvNClamp(_458, 0.0, 1.0);
    D _617 = dot(vec3(_419, _420, _421), vec3(_613, _614, _615));
    D _621 = (_617 >= 0.0) ? 1.0 : (-1.0);
    D _624 = acos(spvNClamp(abs(_617), 0.0, 1.0));
    D _627 = sin(_624 * (1.0 - _616));
    D _632 = sin(_624 * _616);
    D _639 = ((_621 * _613) * _632) + (_627 * _419);
    D _640 = ((_621 * _614) * _632) + (_627 * _420);
    D _641 = ((_621 * _615) * _632) + (_627 * _421);
    D _656;
    D _657;
    D _658;
    if (dot(vec3(_639, _640, _641), vec3(_639, _640, _641)) < 9.9999999747524270787835121154785e-07)
    {
        _656 = ((_613 - _419) * _616) + _419;
        _657 = ((_614 - _420) * _616) + _420;
        _658 = ((_615 - _421) * _616) + _421;
    }
    else
    {
        _656 = _639;
        _657 = _640;
        _658 = _641;
    }
    bool _662 = dot(vec3(_656, _657, _658), vec3(_656, _657, _658)) < 9.9999999747524270787835121154785e-07;
    bool _663 = _616 < 0.5;
    D _668 = _662 ? (_663 ? _419 : _613) : _656;
    D _669 = _662 ? (_663 ? _420 : _614) : _657;
    D _670 = _662 ? (_663 ? _421 : _615) : _658;
    D _674 = inversesqrt(dot(vec3(_668, _669, _670), vec3(_668, _669, _670)));
    D _675 = _668 * _674;
    D _676 = _669 * _674;
    D _677 = _670 * _674;
    vec4 _680 = texture(sampler2D(Material_Texture2D_21, View_SharedAnisotropic4XWrappedSampler), vec2(_349, _350), View._m0[155u].y);
    D _682 = _680.x;
    vec4 _683 = texture(sampler2D(Material_Texture2D_21, View_SharedAnisotropic4XWrappedSampler), vec2(_352, _354), View._m0[155u].y);
    D _685 = _683.x;
    D _687 = _682 * _682;
    D _692 = sqrt(spvNClamp((((_685 * _685) - _687) * _359) + _687, 0.0, 1.0));
    vec4 _703 = texture(sampler2D(Material_Texture2D_23, View_SharedAnisotropic4XWrappedSampler), vec2(_349, _350), View._m0[155u].y);
    D _705 = _703.x;
    vec4 _706 = texture(sampler2D(Material_Texture2D_23, View_SharedAnisotropic4XWrappedSampler), vec2(_352, _354), View._m0[155u].y);
    D _713 = 1.0 - _453;
    vec4 _721 = texture(sampler2D(Material_Texture2D_8, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _727 = vec4(g_R.Muddiness.x, g_R.Muddiness.y, g_R.Muddiness.z, 0.0);
    vec4 _734 = texture(sampler2D(Material_Texture2D_26, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _739 = texture(sampler2D(Material_Texture2D_27, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _748 = g_R.TransparencyLog2;
    D _749 = exp2(_748);
    vec4 _752 = texture(sampler2D(Material_Texture2D_28, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _759 = texture(sampler2D(Material_Texture2D_29, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _764 = 1.0 / spvNMax(9.9999999747524270787835121154785e-07, _759.x * 100.0);
    D _771 = g_R.TransmittanceLog2.x;
    D _772 = g_R.TransmittanceLog2.y;
    D _773 = g_R.TransmittanceLog2.z;
    vec4 _779 = vec4(g_R.Thickness);
    D _782 = _779.x * 100.0;
    D _788 = inversesqrt(dot(vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z), vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z)));
    D _789 = _788 * g_R.Normal.x;
    D _790 = _788 * g_R.Normal.y;
    D _791 = _788 * g_R.Normal.z;
    D _794 = fma(_791, TEXCOORD_11.x, fma(_790, ((TEXCOORD_10.z * TEXCOORD_11.y) - (TEXCOORD_10.y * TEXCOORD_11.z)) * TEXCOORD_11.w, _789 * TEXCOORD_10.x));
    D _797 = fma(_791, TEXCOORD_11.y, fma(_790, ((TEXCOORD_10.x * TEXCOORD_11.z) - (TEXCOORD_10.z * TEXCOORD_11.x)) * TEXCOORD_11.w, _789 * TEXCOORD_10.y));
    D _800 = fma(_791, TEXCOORD_11.z, fma(_790, ((TEXCOORD_10.y * TEXCOORD_11.x) - (TEXCOORD_10.x * TEXCOORD_11.y)) * TEXCOORD_11.w, _789 * TEXCOORD_10.z));
    D _804 = inversesqrt(dot(vec3(_794, _797, _800), vec3(_794, _797, _800)));
    D _805 = _804 * _794;
    D _806 = _804 * _797;
    D _807 = _804 * _800;
    bool _820;
    if (Primitive._m0[27u].w > ((_276.w * 0.99609375) + 0.001953125))
    {
        _820 = ((_279 * 0.99609375) + 0.001953125) < 1.0;
    }
    else
    {
        _820 = false;
    }
    (void)((_820 ? 1.0 : (-1.0)) < 0.0);
    D _826 = spvNClamp(g_R.BaseColor.x, 0.0, 1.0);
    D _827 = spvNClamp(g_R.BaseColor.y, 0.0, 1.0);
    D _828 = spvNClamp(g_R.BaseColor.z, 0.0, 1.0);
    D _829 = spvNClamp(g_R.Metallic, 0.0, 1.0);
    D _830 = spvNClamp(g_R.Roughness, 0.0, 1.0);
    D _831 = spvNClamp(g_R.AO, 0.0, 1.0);
    D _832 = spvNClamp(g_R.Opacity, 0.0, 1.0);
    D _834 = dFdxFine(_805);
    D _835 = dFdxFine(_806);
    D _836 = dFdxFine(_807);
    D _840 = dFdyFine(_805);
    D _841 = dFdyFine(_806);
    D _842 = dFdyFine(_807);
    D _853 = sqrt(spvNClamp(spvNMin((dot(vec3(_840, _841, _842), vec3(_840, _841, _842)) + dot(vec3(_834, _835, _836), vec3(_834, _835, _836))) * 0.15915493667125701904296875, 0.180000007152557373046875) + (_830 * _830), 0.0, 1.0));
    D _854 = 1.0 - _829;
    D _855 = _854 * _826;
    D _856 = _854 * _827;
    D _857 = _854 * _828;
    D _862 = _829 * (_826 + (-0.0203731842339038848876953125));
    D _863 = _829 * (_827 + (-0.0203731842339038848876953125));
    D _864 = _829 * (_828 + (-0.0203731842339038848876953125));
    D _865 = _862 + 0.0203731842339038848876953125;
    D _867 = _863 + 0.0203731842339038848876953125;
    D _868 = _864 + 0.0203731842339038848876953125;
    D _875 = spvNClamp(D(View._m0[220u].x > 1.0), 0.0, 1.0);
    D _903 = ((exp2(log2(spvNMax(0.0, _862 + 0.000373184680938720703125) * 1.020408153533935546875) * 1.39999997615814208984375) - _865) * _875) + _865;
    D _904 = ((exp2(log2(spvNMax(0.0, _863 + 0.000373184680938720703125) * 1.020408153533935546875) * 1.39999997615814208984375) - _867) * _875) + _867;
    D _905 = ((exp2(log2(spvNMax(0.0, _864 + 0.000373184680938720703125) * 1.020408153533935546875) * 1.39999997615814208984375) - _868) * _875) + _868;
    D _910 = (_903 * 0.449999988079071044921875) + _855;
    D _911 = (_904 * 0.449999988079071044921875) + _856;
    D _912 = (_905 * 0.449999988079071044921875) + _857;
    D _919 = dot(vec3(_805, _806, _807), vec3(_255, _257, _258));
    D _925 = (_919 * _805) + _252;
    D _926 = (_919 * _806) + _253;
    D _927 = (_919 * _807) + _254;
    D _931 = abs(_919);
    D _935 = (_925 * 2.0) + (_931 * _805);
    D _936 = (_926 * 2.0) + (_931 * _806);
    D _937 = (_927 * 2.0) + (_931 * _807);
    D _941 = inversesqrt(dot(vec3(_935, _936, _937), vec3(_935, _936, _937)));
    D _942 = _935 * _941;
    D _943 = _936 * _941;
    D _944 = _937 * _941;
    D _945 = _919 * _919;
    D _946 = 1.0 - _945;
    D _955 = sqrt(spvNMax(0.0, 1.0 - (_946 * 0.562781393527984619140625)));
    D _959 = (_925 * 0.750187575817108154296875) - (_955 * _805);
    D _960 = (_926 * 0.750187575817108154296875) - (_955 * _806);
    D _961 = (_927 * 0.750187575817108154296875) - (_955 * _807);
    D _965 = inversesqrt(dot(vec3(_959, _960, _961), vec3(_959, _960, _961)));
    D _966 = _959 * _965;
    D _967 = _960 * _965;
    D _968 = _961 * _965;
    D _972 = _853 * _853;
    D _973 = _972 * _853;
    D _980 = ((((-0.0) - _805) - _966) * _973) + _966;
    D _981 = ((((-0.0) - _806) - _967) * _973) + _967;
    D _982 = ((((-0.0) - _807) - _968) * _973) + _968;
    D _986 = inversesqrt(dot(vec3(_980, _981, _982), vec3(_980, _981, _982)));
    D _987 = _980 * _986;
    D _988 = _981 * _986;
    D _989 = _982 * _986;
    D _990 = spvNMax(9.9999997473787516355514526367188e-06, _931);
    D _997 = View._m0[161u].z * gl_FragCoord.x;
    D _998 = View._m0[161u].w * gl_FragCoord.y;
    D _1008 = (1.0 / ((-0.0) - View._m0[73u].w)) + View._m0[73u].y;
    D _1010 = spvNMax(0.0, _1008 - _116);
    D _1013 = D(uint(gl_FragCoord.x)) + 0.5;
    D _1014 = D(uint(gl_FragCoord.y)) + 0.5;
    D _1037 = ((View._m0[55u].z + fma(_1014, View._m0[53u].z, View._m0[52u].z * _1013)) / (fma(_1014, View._m0[53u].w, View._m0[52u].w * _1013) + View._m0[55u].w)) - View._m0[78u].z;
    D _1043 = spvNClamp((1.0 / (_1010 + 49.0)) * _1010, 0.0, 1.0) * 50.0;
    D _1047 = fma(_968, View._m0[22u].x, fma(_967, View._m0[21u].x, _966 * View._m0[20u].x));
    D _1050 = fma(_968, View._m0[22u].y, fma(_967, View._m0[21u].y, _966 * View._m0[20u].y));
    D _1053 = fma(_968, View._m0[22u].z, fma(_967, View._m0[21u].z, _966 * View._m0[20u].z));
    D _1057 = inversesqrt(dot(vec3(_1047, _1050, _1053), vec3(_1047, _1050, _1053)));
    D _1058 = spvNMax(10.0, _116);
    D _1080 = (((_1047 * _1043) * _1057) * (1.0 / (View._m0[44u].x * _1058))) * View._m0[74u].x;
    D _1084 = (((_1050 * _1043) * _1057) * (1.0 / (View._m0[45u].y * _1058))) * View._m0[74u].y;
    D _1101 = ((View._m0[161u].x * _997) - View._m0[158u].x) * View._m0[159u].z;
    D _1102 = ((View._m0[161u].y * _998) - View._m0[158u].y) * View._m0[159u].w;
    D _1105 = spvNMin(View._m0[159u].z, View._m0[159u].w);
    D _1106 = _1105 * View._m0[159u].y;
    D _1107 = _1105 * View._m0[159u].x;
    D _1113 = (12.5 / _1106) * abs(_1080);
    D _1114 = (12.5 / _1107) * abs(_1084);
    D _1135 = (((D(int(uint(_1080 > 0.0) - uint(_1080 < 0.0))) * 0.07999999821186065673828125) * _1106) * _1113) * (1.0 / (_1113 + 1.0));
    D _1139 = (((D(int(uint(_1084 > 0.0) - uint(_1084 < 0.0))) * 0.07999999821186065673828125) * _1107) * _1114) * (1.0 / (_1114 + 1.0));
    D _1148 = spvNClamp(abs((_1101 * 2.0) + (-1.0)), 0.0, 1.0);
    D _1149 = spvNClamp(abs((_1102 * 2.0) + (-1.0)), 0.0, 1.0);
    D _1150 = _1148 * _1148;
    D _1151 = _1149 * _1149;
    D _1159 = (View._m0[158u].x + (-1.0)) + View._m0[159u].x;
    D _1161 = (View._m0[158u].y + (-1.0)) + View._m0[159u].y;
    D _1174 = D(int(uint(int(spvNMin(spvNMax((View._m0[159u].x * ((_1135 + _1101) - ((_1150 * _1150) * _1135))) + View._m0[158u].x, View._m0[158u].x), _1159))))) + 0.5;
    D _1175 = D(int(uint(int(spvNMin(spvNMax((View._m0[159u].y * ((_1139 + _1102) - ((_1151 * _1151) * _1139))) + View._m0[158u].y, View._m0[158u].y), _1161))))) + 0.5;
    D _1188 = D(uint(spvNMin(spvNMax(View._m0[161u].x * (_1174 * View._m0[161u].z), View._m0[158u].x), _1159))) + 0.5;
    D _1189 = D(uint(spvNMin(spvNMax(View._m0[161u].y * (_1175 * View._m0[161u].w), View._m0[158u].y), _1161))) + 0.5;
    D _1201;
    if (_1008 > _116)
    {
        _1201 = spvNClamp(_1010 * 0.0199999995529651641845703125, 0.0, 1.0);
    }
    else
    {
        _1201 = 0.0;
    }
    D _1213 = spvNMin(_1010, _782);
    D _1224 = 1.0 - _853;
    D _1238 = ((spvNMin(_1224 * _1224, exp2(_990 * (-9.27999973297119140625))) * _1224) + (0.0425000004470348358154296875 - (_853 * 0.0274999998509883880615234375))) * 1.03999996185302734375;
    D _1244 = 1.0 - spvNClamp((((_853 * 0.02199999988079071044921875) + (-0.039999999105930328369140625)) + _1238) + (((1.03999996185302734375 - (_853 * 0.572000026702880859375)) - _1238) * 0.0203731842339038848876953125), 0.0, 1.0);
    D _1247 = spvNClamp(_1213 * 0.0199999995529651641845703125, 0.0, 1.0) * g_R.Foam;
    D _1248 = spvNMax(0.001000000047497451305389404296875, _1213);
    D _1251 = log2(spvNMax(0.0, _749));
    D _1253 = exp2(_1251 * _1248);
    D _1257 = log2(spvNMax(0.0, exp2(_771)));
    D _1258 = log2(spvNMax(0.0, exp2(_772)));
    D _1259 = log2(spvNMax(0.0, exp2(_773)));
    D _1263 = exp2(_1257 * _1248);
    D _1264 = exp2(_1258 * _1248);
    D _1265 = exp2(_1259 * _1248);
    D _1266 = spvNMax(0.001000000047497451305389404296875, spvNMin(spvNMax(0.0, (_246 - _1037) - (_1201 * ((((View._m0[55u].z + fma(_1189, View._m0[53u].z, View._m0[52u].z * _1188)) / (fma(_1189, View._m0[53u].w, View._m0[52u].w * _1188) + View._m0[55u].w)) - _1037) - View._m0[78u].z))), _782));
    D _1268 = exp2(_1251 * _1266);
    D _1275 = 1.0 - _832;
    D _1280 = (_1253 * _1244) * (1.0 - ((_1247 * _1275) + _832));
    D _1283 = ((_1280 * _1263) * _1268) * exp2(_1257 * _1266);
    D _1286 = ((_1280 * _1264) * _1268) * exp2(_1258 * _1266);
    D _1289 = ((_1280 * _1265) * _1268) * exp2(_1259 * _1266);
    D _1293 = spvNMax(0.039999999105930328369140625, _853);
    D _1309 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_1293 * _990) + 0.02669160068035125732421875) / (_990 + 0.4664950072765350341796875)) * exp2(((1.0 / _1293) * _990) * log2(_1293)), 0.0, 1.0));
    D _1310 = 1.0 - _990;
    D _1311 = _1310 * _1310;
    D _1324 = _1311 * _1311;
    D _1326 = (_1324 * _1310) * exp2(log2((exp2((_1293 * 4.7702999114990234375) * log2(_990)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _1293);
    D _1329 = (1.0 / _1309) * (1.0 - _1309);
    D _1336 = _1309 - _1326;
    D _1343 = ((_1329 * _903) + 1.0) * ((_1336 * _903) + _1326);
    D _1344 = ((_1329 * _904) + 1.0) * ((_1336 * _904) + _1326);
    D _1345 = ((_1329 * _905) + 1.0) * ((_1336 * _905) + _1326);
    D _1351 = spvNClamp(1.0 - dot(vec3(_1343, _1344, _1345), vec3(0.3333333432674407958984375)), 0.0, 1.0);
    D _1365 = spvNClamp((_831 + (-1.0)) + exp2(log2(_990 + _831) * exp2((-1.0) - (_853 * 16.0))), 0.0, 1.0);
    D _1425;
    D _1427;
    D _1429;
    D _1431;
    D _1433;
    D _1435;
    D _1437;
    D _1439;
    D _1441;
    D _1443;
    D _1445;
    D _1447;
    if (floatBitsToUint(TranslucentBasePass_2._m0[0u]).z == 0u)
    {
        _1425 = 0.0;
        _1427 = 0.0;
        _1429 = 0.0;
        _1431 = 0.0;
        _1433 = 0.0;
        _1435 = 0.0;
        _1437 = 0.0;
        _1439 = 0.0;
        _1441 = 0.0;
        _1443 = 0.0;
        _1445 = 0.0;
        _1447 = 0.0;
    }
    else
    {
        D _1963;
        uint _1462;
        bool _1463;
        for (;;)
        {
            _1462 = floatBitsToUint(TranslucentBasePass_2._m0[7u]).z;
            _1463 = _1462 == 0u;
            if (!_1463)
            {
                uint _2128;
                uint _2031 = 0u;
                for (;;)
                {
                    if (_116 < TranslucentBasePass._m0[_2031 + 32u])
                    {
                        _2128 = _2031;
                        break;
                    }
                    else
                    {
                        uint _2032 = _2031 + 1u;
                        if (_2032 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                        {
                            _2031 = _2032;
                            continue;
                        }
                        else
                        {
                            _2128 = _1462;
                            break;
                        }
                    }
                }
                if (_2128 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                {
                    uint _2552 = _2128 << 2u;
                    uint _2553 = _2552 + 9u;
                    uint _2560 = _2552 + 10u;
                    uint _2567 = _2552 + 11u;
                    uint _2574 = _2552 + 12u;
                    uint _2582 = _2128 + 25u;
                    D _2608 = fma(_246, TranslucentBasePass_2._m0[_2567].z, fma(_245, TranslucentBasePass_2._m0[_2560].z, TranslucentBasePass_2._m0[_2553].z * _244)) + TranslucentBasePass_2._m0[_2574].z;
                    D _2612 = fma(_246, TranslucentBasePass_2._m0[_2567].w, fma(_245, TranslucentBasePass_2._m0[_2560].w, TranslucentBasePass_2._m0[_2553].w * _244)) + TranslucentBasePass_2._m0[_2574].w;
                    D _2613 = (fma(_246, TranslucentBasePass_2._m0[_2567].x, fma(_245, TranslucentBasePass_2._m0[_2560].x, TranslucentBasePass_2._m0[_2553].x * _244)) + TranslucentBasePass_2._m0[_2574].x) / _2612;
                    D _2614 = (fma(_246, TranslucentBasePass_2._m0[_2567].y, fma(_245, TranslucentBasePass_2._m0[_2560].y, TranslucentBasePass_2._m0[_2553].y * _244)) + TranslucentBasePass_2._m0[_2574].y) / _2612;
                    bool _2621 = (_2614 <= TranslucentBasePass_2._m0[_2582].w) && ((_2613 <= TranslucentBasePass_2._m0[_2582].z) && ((_2613 >= TranslucentBasePass_2._m0[_2582].x) && (_2614 >= TranslucentBasePass_2._m0[_2582].y)));
                    D _1964;
                    if (_2621)
                    {
                        D _2800 = dFdyFine(_2613);
                        D _2801 = dFdyFine(_2614);
                        D _2802 = dFdyFine(_2608);
                        D _2803 = dFdxFine(_2613);
                        D _2804 = dFdxFine(_2614);
                        D _2805 = dFdxFine(_2608);
                        D _2808 = (_2804 * _2802) - (_2805 * _2801);
                        D _2811 = (_2805 * _2800) - (_2803 * _2802);
                        D _2814 = (_2803 * _2801) - (_2804 * _2800);
                        D _2824 = 1.0 / spvNMax(abs(_2814), sqrt(((_2811 * _2811) + (_2814 * _2814)) + (_2808 * _2808)) * 0.100000001490116119384765625);
                        D _2830 = D(int(uint(_2814 > 0.0) - uint(_2814 < 0.0)));
                        D _2831 = _2808 * TranslucentBasePass_2._m0[29u].z;
                        D _2833 = (_2831 * _2824) * _2830;
                        D _2834 = _2811 * TranslucentBasePass_2._m0[29u].w;
                        D _2836 = (_2834 * _2824) * _2830;
                        D _3310;
                        D _3312;
                        if (dot(vec2(_2808, _2811), vec2(_2808, _2811)) < 1.0000000195414813782625560981111e-24)
                        {
                            _3310 = 0.0;
                            _3312 = 0.0;
                        }
                        else
                        {
                            D _3680 = (-0.0) - _2808;
                            D _3681 = (-0.0) - _2811;
                            D _3685 = inversesqrt(dot(vec2(_3680, _3681), vec2(_3680, _3681)));
                            _3310 = _3685 * _3680;
                            _3312 = _3685 * _3681;
                        }
                        D _3314 = _280 + (-0.5);
                        D _3319 = _279 + 0.5;
                        D _3322 = ((_3312 * _3314) + (_2613 * TranslucentBasePass_2._m0[29u].x)) + (_3310 * _3319);
                        D _3325 = ((_3310 * _3314) + (_2614 * TranslucentBasePass_2._m0[29u].y)) + (_3312 * _3319);
                        D _3326 = _3322 + (-0.5);
                        D _3327 = _3325 + (-0.5);
                        D _3328 = trunc(_3326);
                        D _3329 = trunc(_3327);
                        D _3330 = _3326 - _3328;
                        D _3331 = _3327 - _3329;
                        D _3332 = _3328 * TranslucentBasePass_2._m0[29u].z;
                        D _3333 = _3329 * TranslucentBasePass_2._m0[29u].w;
                        D _3336 = (_3328 + (-0.5)) - _3322;
                        D _3337 = (_3329 + (-0.5)) - _3325;
                        D _3338 = dot(vec2(_3336, _3337), vec2(_2833, _2836));
                        D _3341 = _3338 + _2836;
                        D _3344 = _2830 * (_2824 * (_2834 + _2831));
                        D _3345 = _3344 + _3338;
                        D _3346 = _3338 + _2833;
                        vec4 _3352 = textureGather((sampler2D(ShadowMaps[_2128 + 0u], View_SharedPointClampedSampler)), vec2(_3332, _3333));
                        D _3353 = _3352.x;
                        D _3354 = _3352.y;
                        D _3355 = _3352.z;
                        D _3356 = _3352.w;
                        D _3393 = 1.525902189314365386962890625e-05 - _2608;
                        D _3424 = (_3328 + 1.5) - _3322;
                        D _3425 = dot(vec2(_3424, _3337), vec2(_2833, _2836));
                        D _3428 = _3425 + _2836;
                        D _3429 = _3344 + _3425;
                        D _3430 = _3425 + _2833;
                        vec4 _3432 = textureGatherOffset((sampler2D(ShadowMaps[_2128 + 0u], View_SharedPointClampedSampler)), vec2(_3332, _3333), ivec2(2, 0));
                        D _3433 = _3432.x;
                        D _3434 = _3432.y;
                        D _3435 = _3432.z;
                        D _3436 = _3432.w;
                        D _3502 = (_3329 + 1.5) - _3325;
                        D _3503 = dot(vec2(_3336, _3502), vec2(_2833, _2836));
                        D _3506 = _3503 + _2836;
                        D _3507 = _3344 + _3503;
                        D _3508 = _3503 + _2833;
                        vec4 _3510 = textureGatherOffset((sampler2D(ShadowMaps[_2128 + 0u], View_SharedPointClampedSampler)), vec2(_3332, _3333), ivec2(0, 2));
                        D _3511 = _3510.x;
                        D _3512 = _3510.y;
                        D _3513 = _3510.z;
                        D _3514 = _3510.w;
                        D _3579 = dot(vec2(_3424, _3502), vec2(_2833, _2836));
                        D _3582 = _3579 + _2836;
                        D _3583 = _3344 + _3579;
                        D _3584 = _3579 + _2833;
                        vec4 _3586 = textureGatherOffset((sampler2D(ShadowMaps[_2128 + 0u], View_SharedPointClampedSampler)), vec2(_3332, _3333), ivec2(2));
                        D _3587 = _3586.x;
                        D _3588 = _3586.y;
                        D _3589 = _3586.z;
                        D _3590 = _3586.w;
                        D _3655 = 1.0 - _3330;
                        vec4 _3678 = vec4((((((_3356 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3393 + _3356) + (spvNMin(abs(_3338), 0.0) * D(int(uint(_3338 > 0.0) - uint(_3338 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3655) + ((_3355 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3393 + _3355) + (spvNMin(abs(_3346), 0.0) * D(int(uint(_3346 > 0.0) - uint(_3346 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3436 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3393 + _3436) + (spvNMin(abs(_3425), 0.0) * D(int(uint(_3425 > 0.0) - uint(_3425 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3435 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3393 + _3435) + (spvNMin(abs(_3430), 0.0) * D(int(uint(_3430 > 0.0) - uint(_3430 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3330), (((((_3353 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3393 + _3353) + (spvNMin(abs(_3341), 0.0) * D(int(uint(_3341 > 0.0) - uint(_3341 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3655) + ((_3354 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3393 + _3354) + (spvNMin(abs(_3345), 0.0) * D(int(uint(_3345 > 0.0) - uint(_3345 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3433 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3393 + _3433) + (spvNMin(abs(_3428), 0.0) * D(int(uint(_3428 > 0.0) - uint(_3428 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3434 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3393 + _3434) + (spvNMin(abs(_3429), 0.0) * D(int(uint(_3429 > 0.0) - uint(_3429 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3330), (((((_3514 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3393 + _3514) + (spvNMin(abs(_3503), 0.0) * D(int(uint(_3503 > 0.0) - uint(_3503 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3655) + ((_3513 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3393 + _3513) + (spvNMin(abs(_3508), 0.0) * D(int(uint(_3508 > 0.0) - uint(_3508 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3590 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3393 + _3590) + (spvNMin(abs(_3579), 0.0) * D(int(uint(_3579 > 0.0) - uint(_3579 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3589 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3393 + _3589) + (spvNMin(abs(_3584), 0.0) * D(int(uint(_3584 > 0.0) - uint(_3584 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3330), (((((_3511 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3393 + _3511) + (spvNMin(abs(_3506), 0.0) * D(int(uint(_3506 > 0.0) - uint(_3506 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3655) + ((_3512 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3393 + _3512) + (spvNMin(abs(_3507), 0.0) * D(int(uint(_3507 > 0.0) - uint(_3507 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3587 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3393 + _3587) + (spvNMin(abs(_3582), 0.0) * D(int(uint(_3582 > 0.0) - uint(_3582 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3588 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3393 + _3588) + (spvNMin(abs(_3583), 0.0) * D(int(uint(_3583 > 0.0) - uint(_3583 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3330));
                        _1964 = dot(_3678, vec4(1.0 - _3331, 1.0, 1.0, _3331)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        _1964 = 1.0;
                    }
                    if (_2621)
                    {
                        _1963 = _1964;
                        break;
                    }
                }
            }
            if (floatBitsToUint(TranslucentBasePass_2._m0[30u]).y == 0u)
            {
                _1963 = 1.0;
                break;
            }
            D _2004 = fma(_246, TranslucentBasePass_2._m0[35u].z, fma(_245, TranslucentBasePass_2._m0[34u].z, TranslucentBasePass_2._m0[33u].z * _244)) + TranslucentBasePass_2._m0[36u].z;
            D _2008 = fma(_246, TranslucentBasePass_2._m0[35u].w, fma(_245, TranslucentBasePass_2._m0[34u].w, TranslucentBasePass_2._m0[33u].w * _244)) + TranslucentBasePass_2._m0[36u].w;
            D _2009 = (fma(_246, TranslucentBasePass_2._m0[35u].x, fma(_245, TranslucentBasePass_2._m0[34u].x, TranslucentBasePass_2._m0[33u].x * _244)) + TranslucentBasePass_2._m0[36u].x) / _2008;
            D _2010 = (fma(_246, TranslucentBasePass_2._m0[35u].y, fma(_245, TranslucentBasePass_2._m0[34u].y, TranslucentBasePass_2._m0[33u].y * _244)) + TranslucentBasePass_2._m0[36u].y) / _2008;
            uvec4 _2014 = floatBitsToUint(TranslucentBasePass_2._m0[32u]);
            uint _2015 = _2014.x;
            uint _2016 = _2014.y;
            uint _2017 = _2014.z;
            uint _2022 = uint(int(floor(_2009)));
            uint _2023 = uint(int((-0.0) - floor(_2010)));
            if (!((int(_2023) < int(_2014.w)) && ((int(_2022) < int(_2017)) && ((int(_2022) >= int(_2015)) && (int(_2023) >= int(_2016))))))
            {
                _1963 = 1.0;
                break;
            }
            D _2091 = dFdyFine(_2009);
            D _2092 = dFdyFine(_2010);
            D _2093 = dFdyFine(_2004);
            D _2094 = dFdxFine(_2009);
            D _2095 = dFdxFine(_2010);
            D _2096 = dFdxFine(_2004);
            D _2099 = (_2095 * _2093) - (_2096 * _2092);
            D _2102 = (_2096 * _2091) - (_2094 * _2093);
            D _2105 = (_2094 * _2092) - (_2095 * _2091);
            D _2116 = 1.0 / spvNMax(abs(_2105), sqrt(((_2102 * _2102) + (_2105 * _2105)) + (_2099 * _2099)) * 0.100000001490116119384765625);
            D _2122 = D(int(uint(_2105 > 0.0) - uint(_2105 < 0.0)));
            D _2480;
            D _2482;
            if (dot(vec2(_2099, _2102), vec2(_2099, _2102)) < 1.0000000195414813782625560981111e-24)
            {
                _2480 = 0.0;
                _2482 = 0.0;
            }
            else
            {
                D _2545 = (-0.0) - _2099;
                D _2546 = (-0.0) - _2102;
                D _2550 = inversesqrt(dot(vec2(_2545, _2546), vec2(_2545, _2546)));
                _2480 = _2550 * _2545;
                _2482 = _2550 * _2546;
            }
            D _2488 = _280 + (-0.5);
            D _2496 = (((_2482 * _2488) + (_2480 * _279)) * 2.0) + (_2480 * 0.5);
            D _2497 = (((_2482 * _279) + (_2480 * _2488)) * 2.0) + (_2482 * 0.5);
            D _2503 = _2496 + (fract(_2009) * 256.0);
            D _2504 = _2497 + (fract(_2010) * 256.0);
            D _2517 = dot(vec2((floor(_2503) + 0.5) - _2503, (floor(_2504) + 0.5) - _2504), vec2(((_2099 * 256.0) * _2116) * _2122, ((_2102 * 256.0) * _2116) * _2122));
            D _2523 = (_2496 * 0.00390625) + _2009;
            D _2524 = (_2497 * 0.00390625) + _2010;
            uint _2536 = ((uint(int((-0.0) - floor(_2524))) - _2016) * (_2017 - _2015)) + (uint(int(floor(_2523))) - _2015);
            D _2773;
            D _2776;
            if ((texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowLoadedTileData, int(_2536 >> 5u)).x & (1u << (_2536 & 31u))) == 0u)
            {
                _2773 = 3.0000000054977557577780399428115e+38;
                _2776 = 0.0;
            }
            else
            {
                uvec4 _2797 = uvec4(texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileIndices, int(_2536)));
                uint _2798 = _2797.x;
                D frontier_phi_51_52_ladder;
                D frontier_phi_51_52_ladder_1;
                if (int(_2798) > int(4294967295u))
                {
                    uint _3296 = (uint(floor(fract(_2523) * 256.0)) + (_2798 << 16u)) + (uint(floor(fract(_2524) * 256.0)) << 8u);
                    uvec4 _3299 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileData, int(_3296 >> 1u));
                    uint _3300 = _3299.x;
                    D _3308 = D((((_3296 & 1u) == 0u) ? _3300 : (_3300 >> 16u)) & 65535u) * 1.525902189314365386962890625e-05;
                    D frontier_phi_51_52_ladder_68_ladder;
                    D frontier_phi_51_52_ladder_68_ladder_1;
                    if (_3308 != 1.0)
                    {
                        vec4 _4067 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthRanges, int(_2798));
                        D _4069 = _4067.y;
                        D _2777 = (1.0 / _4069) * 10.0;
                        frontier_phi_51_52_ladder_68_ladder = _2777;
                        frontier_phi_51_52_ladder_68_ladder_1 = (_4069 * _3308) + _4067.x;
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
                _2773 = frontier_phi_51_52_ladder_1;
                _2776 = frontier_phi_51_52_ladder;
            }
            _1963 = spvNClamp(((((1.525902189314365386962890625e-05 - _2004) + _2773) + (spvNMin(abs(_2517), _2776) * D(int(uint(_2517 > 0.0) - uint(_2517 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0);
            break;
        }
        D _2078;
        if ((floatBitsToUint(Primitive._m0[27u]).z & 2u) == 0u)
        {
            _2078 = 1.0;
        }
        else
        {
            _2078 = View._m0[188u].y;
        }
        uvec4 _2082 = floatBitsToUint(View._m0[220u]);
        uint _2083 = _2082.y;
        uint _2086 = (_2083 != 1u) ? 4294967295u : 0u;
        uint _2478;
        if (_2083 > 1u)
        {
            D _152[4];
            _152[0u] = 0.0;
            _152[1u] = 0.0;
            _152[2u] = 0.0;
            _152[3u] = 0.0;
            uint _2758 = 0u;
            bool _2764;
            for (;;)
            {
                _2764 = _2758 < floatBitsToUint(View._m0[220u]).y;
                if (_2764)
                {
                    uint _3247 = _2758 + 237u;
                    D _3261 = View._m0[_3247].x - View._m0[75u].x;
                    D _3262 = View._m0[_3247].y - View._m0[75u].y;
                    D _3263 = View._m0[_3247].z - View._m0[75u].z;
                    D _3264 = dot(vec3(_3261, _3262, _3263), vec3(_252, _253, _254));
                    D _3271 = dot(vec3(_3261, _3262, _3263), vec3(_3261, _3262, _3263)) - (View._m0[_3247].w * View._m0[_3247].w);
                    D _3273 = (_3264 * _3264) - _3271;
                    D _3828;
                    if ((_3271 < 0.0) && (!(_3273 < 0.0)))
                    {
                        D _3822 = sqrt(_3273);
                        _3828 = spvNMin(abs(_3822 + _3264), abs(_3264 - _3822));
                    }
                    else
                    {
                        _3828 = 0.0;
                    }
                    _152[_2758] = _3828;
                }
                uint _2759 = _2758 + 1u;
                if (_2759 == 4u)
                {
                    break;
                }
                else
                {
                    _2758 = _2759;
                    continue;
                }
            }
            D _3839 = (_279 * 0.99989998340606689453125) * dot(vec4(_152[0u], _152[1u], _152[2u], _152[3u]), vec4(1.0));
            uint frontier_phi_36_76_ladder;
            if (_152[0u] > _3839)
            {
                frontier_phi_36_76_ladder = 0u;
            }
            else
            {
                D _4127 = _152[1u] + _152[0u];
                uint frontier_phi_36_76_ladder_83_ladder;
                if (_4127 > _3839)
                {
                    frontier_phi_36_76_ladder_83_ladder = 1u;
                }
                else
                {
                    D _4138 = _4127 + _152[2u];
                    uint frontier_phi_36_76_ladder_83_ladder_86_ladder;
                    if (_4138 > _3839)
                    {
                        frontier_phi_36_76_ladder_83_ladder_86_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_36_76_ladder_83_ladder_86_ladder_89_ladder;
                        if ((_4138 + _152[3u]) > _3839)
                        {
                            frontier_phi_36_76_ladder_83_ladder_86_ladder_89_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_36_76_ladder_83_ladder_86_ladder_89_ladder = _2086;
                        }
                        frontier_phi_36_76_ladder_83_ladder_86_ladder = frontier_phi_36_76_ladder_83_ladder_86_ladder_89_ladder;
                    }
                    frontier_phi_36_76_ladder_83_ladder = frontier_phi_36_76_ladder_83_ladder_86_ladder;
                }
                frontier_phi_36_76_ladder = frontier_phi_36_76_ladder_83_ladder;
            }
            _2478 = frontier_phi_36_76_ladder;
        }
        else
        {
            _2478 = _2086;
        }
        D _2765;
        if (_2478 == 4294967295u)
        {
            _2765 = _2078;
        }
        else
        {
            _2765 = View._m0[_2478 + 241u].x * _2078;
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
        if (_2765 > 0.0)
        {
            D _3280 = spvNClamp((TranslucentBasePass_2._m0[7u].x * _116) + TranslucentBasePass_2._m0[7u].y, 0.0, 1.0);
            D _3284 = ((_3280 * _3280) * (1.0 - _1963)) + _1963;
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
            if (_3284 > 0.0)
            {
                D _3841 = dot(vec3(_805, _806, _807), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3844 = spvNMax(0.0, _3841);
                D _3845 = dot(vec3(_255, _257, _258), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3851 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3845 * 2.0) + 2.0));
                D _3854 = spvNClamp(_3851 * (_919 + _3841), 0.0, 1.0);
                D _3867 = sqrt(spvNMax(0.0, 1.0 - (_946 * 0.444444477558135986328125)));
                D _3871 = (_925 * 0.666666686534881591796875) - (_3867 * _805);
                D _3872 = (_926 * 0.666666686534881591796875) - (_3867 * _806);
                D _3873 = (_927 * 0.666666686534881591796875) - (_3867 * _807);
                D _3877 = inversesqrt(dot(vec3(_3871, _3872, _3873), vec3(_3871, _3872, _3873)));
                D _3884 = dot(vec3((-0.0) - (_3877 * _3871), (-0.0) - (_3877 * _3872), (-0.0) - (_3877 * _3873)), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3887 = _1293 * _1293;
                D _3888 = _3887 * _3887;
                D _3892 = ((_3854 * _3854) * (_3888 + (-1.0))) + 1.0;
                D _3898 = (_3844 * 2.0) * _990;
                D _3903 = 1.0 - spvNMax(9.9999997473787516355514526367188e-06, spvNMin(_3851 * (_3845 + 1.0), 1.0));
                D _3904 = _3903 * _3903;
                D _3906 = (_3904 * _3904) * _3903;
                D _3911 = spvNMin(dot(vec3(_903, _904, _905), vec3(16.666667938232421875)), 1.0);
                D _3924 = spvNMax(0.039999999105930328369140625, _1293);
                D _3937 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_3924 * _3844) + 0.02669160068035125732421875) / (_3844 + 0.4664950072765350341796875)) * exp2(((1.0 / _3924) * _3844) * log2(_3924)), 0.0, 1.0));
                D _3938 = 1.0 - _3844;
                D _3939 = _3938 * _3938;
                D _3951 = ((_3939 * _3939) * _3938) * exp2(log2((exp2((_3924 * 4.7702999114990234375) * log2(_3844)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _3924);
                D _3954 = (1.0 / _3937) * (1.0 - _3937);
                D _3958 = (_3954 * _903) + 1.0;
                D _3959 = (_3954 * _904) + 1.0;
                D _3960 = (_3954 * _905) + 1.0;
                D _3961 = _3937 - _3951;
                D _3975 = spvNClamp(1.0 - dot(vec3(_3958 * ((_3961 * _903) + _3951), _3959 * ((_3961 * _904) + _3951), _3960 * ((_3961 * _905) + _3951)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                D _3978 = (((_3888 * 0.3183098733425140380859375) * _3844) * (1.0 / (_3892 * _3892))) * (0.5 / ((_3887 * ((_990 + _3844) - _3898)) + _3898));
                D _3979 = _3844 * 0.3183098733425140380859375;
                D _3993 = (((_3884 * _3884) + 1.0) * 0.0323704965412616729736328125) * exp2(log2(spvNMax(0.0, (_3884 * 1.2000000476837158203125) + 1.36000001430511474609375)) * (-1.5));
                D _3996 = ((_3845 * _3845) + 1.0) * 0.05968309938907623291015625;
                D _3998 = spvNMin(1.0, _831);
                D _4000 = (_831 + 1.0) - _3998;
                D _4001 = _4000 * _4000;
                D _4004 = 1.0 - ((_4001 * _4001) * _4000);
                D _4005 = _4004 * _4004;
                D _4010 = ((_4005 * _4005) * (_4004 * (_831 - _3998))) + _3998;
                D _4013 = sqrt(spvNMax(0.0, 1.0 - _4010));
                D _4018 = 1.0 - spvNClamp((_1293 * 3.5) + (-0.5), 0.0, 1.0);
                D _4019 = _4018 * _4018;
                D _4029 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_1324 * _4013) * spvNClamp(1.0 - ((_4019 * _4019) * _4018), 0.0, 1.0))) * _3844, 0.0, 1.0);
                D _4034 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _4013)) * _3844, 0.0, 1.0);
                D _4036 = spvNMin(_3284, _4029 * _4029);
                D _4037 = spvNMin(_3284, _4034 * _4034);
                D _4038 = spvNMin(_3284, _4010);
                D _4039 = _2765 * TranslucentBasePass_2._m0[4u].x;
                D _4040 = _2765 * TranslucentBasePass_2._m0[4u].y;
                D _4041 = _2765 * TranslucentBasePass_2._m0[4u].z;
                frontier_phi_7_49_ladder_67_ladder = (((_4041 * _857) * _3979) * _3975) * _4037;
                frontier_phi_7_49_ladder_67_ladder_1 = (_3996 * _4039) * _4038;
                frontier_phi_7_49_ladder_67_ladder_2 = (_3996 * _4040) * _4038;
                frontier_phi_7_49_ladder_67_ladder_3 = (_3996 * _4041) * _4038;
                frontier_phi_7_49_ladder_67_ladder_4 = (_3993 * _4039) * _4038;
                frontier_phi_7_49_ladder_67_ladder_5 = (_3993 * _4040) * _4038;
                frontier_phi_7_49_ladder_67_ladder_6 = (_3993 * _4041) * _4038;
                frontier_phi_7_49_ladder_67_ladder_7 = (((_3978 * _4039) * spvNClamp(((_3911 - _903) * _3906) + _903, 0.0, 1.0)) * _3958) * _4036;
                frontier_phi_7_49_ladder_67_ladder_8 = (((_3978 * _4040) * spvNClamp(((_3911 - _904) * _3906) + _904, 0.0, 1.0)) * _3959) * _4036;
                frontier_phi_7_49_ladder_67_ladder_9 = (((_3978 * _4041) * spvNClamp(((_3911 - _905) * _3906) + _905, 0.0, 1.0)) * _3960) * _4036;
                frontier_phi_7_49_ladder_67_ladder_10 = (((_4039 * _855) * _3979) * _3975) * _4037;
                frontier_phi_7_49_ladder_67_ladder_11 = (((_4040 * _856) * _3979) * _3975) * _4037;
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
        _1425 = frontier_phi_7_49_ladder_1;
        _1427 = frontier_phi_7_49_ladder_2;
        _1429 = frontier_phi_7_49_ladder_3;
        _1431 = frontier_phi_7_49_ladder_4;
        _1433 = frontier_phi_7_49_ladder_5;
        _1435 = frontier_phi_7_49_ladder_6;
        _1437 = frontier_phi_7_49_ladder_7;
        _1439 = frontier_phi_7_49_ladder_8;
        _1441 = frontier_phi_7_49_ladder_9;
        _1443 = frontier_phi_7_49_ladder_10;
        _1445 = frontier_phi_7_49_ladder_11;
        _1447 = frontier_phi_7_49_ladder;
    }
    uvec4 _1451 = floatBitsToUint(TranslucentBasePass_2._m0[0u]);
    uint _1452 = _1451.x;
    uint _1457 = min(min(texelFetch(TranslucentBasePass_Shared_Forward_NumCulledLightsGrid, int(0u)).x, _1452), _1452);
    D _1464;
    D _1466;
    D _1468;
    D _1470;
    D _1472;
    D _1474;
    D _1476;
    D _1478;
    D _1480;
    D _1482;
    D _1484;
    D _1486;
    D _1488;
    D _1490;
    D _1492;
    D _1494;
    D _1496;
    D _1498;
    if (_1457 == 0u)
    {
        _1464 = _1425;
        _1466 = _1427;
        _1468 = _1429;
        _1470 = _1431;
        _1472 = _1433;
        _1474 = _1435;
        _1476 = _1437;
        _1478 = _1439;
        _1480 = _1441;
        _1482 = _1443;
        _1484 = _1445;
        _1486 = _1447;
        _1488 = 0.0;
        _1490 = 0.0;
        _1492 = 0.0;
        _1494 = 0.0;
        _1496 = 0.0;
        _1498 = 0.0;
    }
    else
    {
        D _1465;
        D _1467;
        D _1469;
        D _1471;
        D _1473;
        D _1475;
        D _1477;
        D _1479;
        D _1481;
        D _1483;
        D _1485;
        D _1487;
        D _1489;
        D _1491;
        D _1493;
        D _1495;
        D _1497;
        D _1499;
        D _1875 = _1425;
        D _1876 = _1427;
        D _1877 = _1429;
        D _1878 = _1431;
        D _1879 = _1433;
        D _1880 = _1435;
        D _1881 = _1437;
        D _1882 = _1439;
        D _1883 = _1441;
        D _1884 = _1443;
        D _1885 = _1445;
        D _1886 = _1447;
        D _1887 = 0.0;
        D _1888 = 0.0;
        D _1889 = 0.0;
        D _1890 = 0.0;
        D _1891 = 0.0;
        D _1892 = 0.0;
        uint _1893 = 0u;
        D _1897;
        D _1898;
        D _1899;
        D _1900;
        D _1902;
        D _1903;
        D _1904;
        D _1906;
        D _1907;
        D _1908;
        uint _1910;
        D _1912;
        D _1913;
        D _1915;
        D _1916;
        D _1917;
        D _1919;
        D _1920;
        uint _1922;
        D _1925;
        D _1926;
        D _1927;
        D _1928;
        uint _1931;
        D _1933;
        D _1934;
        D _1935;
        D _1936;
        D _1939;
        D _1940;
        D _1941;
        D _1942;
        D _1945;
        D _1946;
        D _1947;
        D _1948;
        D _1951;
        D _1952;
        D _1953;
        D _1954;
        bool _1957;
        bool _1958;
        bool _1962;
        for (;;)
        {
            vec4 _1896 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(0u));
            _1897 = _1896.x;
            _1898 = _1896.y;
            _1899 = _1896.z;
            _1900 = _1896.w;
            vec4 _1901 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(1u));
            _1902 = _1901.x;
            _1903 = _1901.y;
            _1904 = _1901.z;
            vec4 _1905 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(2u));
            _1906 = _1905.x;
            _1907 = _1905.y;
            _1908 = _1905.z;
            _1910 = floatBitsToUint(_1905.w);
            vec4 _1911 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(3u));
            _1912 = _1911.x;
            _1913 = _1911.y;
            vec4 _1914 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(4u));
            _1915 = _1914.x;
            _1916 = _1914.y;
            _1917 = _1914.z;
            vec4 _1918 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(5u));
            _1919 = _1918.x;
            _1920 = _1918.y;
            _1922 = floatBitsToUint(_1918.z);
            vec4 _1924 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(6u));
            _1925 = _1924.x;
            _1926 = _1924.y;
            _1927 = _1924.z;
            _1928 = _1924.w;
            _1931 = floatBitsToUint(texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(7u)).x);
            vec4 _1932 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(8u));
            _1933 = _1932.x;
            _1934 = _1932.y;
            _1935 = _1932.z;
            _1936 = _1932.w;
            vec4 _1938 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(9u));
            _1939 = _1938.x;
            _1940 = _1938.y;
            _1941 = _1938.z;
            _1942 = _1938.w;
            vec4 _1944 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(10u));
            _1945 = _1944.x;
            _1946 = _1944.y;
            _1947 = _1944.z;
            _1948 = _1944.w;
            vec4 _1950 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(11u));
            _1951 = _1950.x;
            _1952 = _1950.y;
            _1953 = _1950.z;
            _1954 = _1950.w;
            _1957 = (_1910 & 131072u) != 0u;
            _1958 = _1912 > (-2.0);
            _1962 = (_1910 & 16384u) == 0u;
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
            if (_1962)
            {
                D _2431;
                if (_1957)
                {
                    uint _2396 = _1931 + 0u;
                    uvec2 _2399 = uvec2(textureSize(ShadowMaps[(_2396)], int(0u)));
                    D _2401 = D(int(_2399.x));
                    D _2403 = D(int(_2399.y));
                    D _2404 = 1.0 / _2401;
                    D _2405 = 1.0 / _2403;
                    D _2417 = fma(_246, _1947, fma(_245, _1941, _1935 * _244)) + _1953;
                    D _2421 = fma(_246, _1948, fma(_245, _1942, _1936 * _244)) + _1954;
                    D _2422 = (fma(_246, _1945, fma(_245, _1939, _1933 * _244)) + _1951) / _2421;
                    D _2423 = (fma(_246, _1946, fma(_245, _1940, _1934 * _244)) + _1952) / _2421;
                    D frontier_phi_32_31_ladder;
                    if ((_2423 <= _1928) && ((_2422 <= _1927) && ((_2422 >= _1925) && (_2423 >= _1926))))
                    {
                        D _2639 = dFdyFine(_2422);
                        D _2640 = dFdyFine(_2423);
                        D _2641 = dFdyFine(_2417);
                        D _2642 = dFdxFine(_2422);
                        D _2643 = dFdxFine(_2423);
                        D _2644 = dFdxFine(_2417);
                        D _2647 = (_2643 * _2641) - (_2644 * _2640);
                        D _2650 = (_2644 * _2639) - (_2642 * _2641);
                        D _2653 = (_2642 * _2640) - (_2643 * _2639);
                        D _2663 = 1.0 / spvNMax(abs(_2653), sqrt(((_2650 * _2650) + (_2653 * _2653)) + (_2647 * _2647)) * 0.100000001490116119384765625);
                        D _2669 = D(int(uint(_2653 > 0.0) - uint(_2653 < 0.0)));
                        D _2670 = _2647 * _2404;
                        D _2672 = (_2670 * _2663) * _2669;
                        D _2673 = _2650 * _2405;
                        D _2675 = (_2673 * _2663) * _2669;
                        D _2842;
                        D _2844;
                        if (dot(vec2(_2647, _2650), vec2(_2647, _2650)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2842 = 0.0;
                            _2844 = 0.0;
                        }
                        else
                        {
                            D _3185 = (-0.0) - _2647;
                            D _3186 = (-0.0) - _2650;
                            D _3190 = inversesqrt(dot(vec2(_3185, _3186), vec2(_3185, _3186)));
                            _2842 = _3190 * _3185;
                            _2844 = _3190 * _3186;
                        }
                        D _2846 = _280 + (-0.5);
                        D _2851 = _279 + 0.5;
                        D _2854 = ((_2844 * _2846) + (_2422 * _2401)) + (_2842 * _2851);
                        D _2857 = ((_2842 * _2846) + (_2423 * _2403)) + (_2844 * _2851);
                        D _2858 = _2854 + (-0.5);
                        D _2859 = _2857 + (-0.5);
                        D _2860 = trunc(_2858);
                        D _2861 = trunc(_2859);
                        D _2862 = _2858 - _2860;
                        D _2863 = _2859 - _2861;
                        D _2864 = _2860 * _2404;
                        D _2865 = _2861 * _2405;
                        D _2868 = (_2860 + (-0.5)) - _2854;
                        D _2869 = (_2861 + (-0.5)) - _2857;
                        D _2870 = dot(vec2(_2868, _2869), vec2(_2672, _2675));
                        D _2873 = _2870 + _2675;
                        D _2876 = _2669 * (_2663 * (_2673 + _2670));
                        D _2877 = _2876 + _2870;
                        D _2878 = _2870 + _2672;
                        vec4 _2882 = textureGather((sampler2D(ShadowMaps[_2396], View_SharedPointClampedSampler)), vec2(_2864, _2865));
                        D _2923 = 1.525902189314365386962890625e-05 - _2417;
                        D _2946 = (_2860 + 1.5) - _2854;
                        D _2947 = dot(vec2(_2946, _2869), vec2(_2672, _2675));
                        D _2950 = _2947 + _2675;
                        D _2951 = _2876 + _2947;
                        D _2952 = _2947 + _2672;
                        vec4 _2956 = textureGatherOffset((sampler2D(ShadowMaps[_2396], View_SharedPointClampedSampler)), vec2(_2864, _2865), ivec2(2, 0));
                        D _3020 = (_2861 + 1.5) - _2857;
                        D _3021 = dot(vec2(_2868, _3020), vec2(_2672, _2675));
                        D _3024 = _3021 + _2675;
                        D _3025 = _2876 + _3021;
                        D _3026 = _3021 + _2672;
                        vec4 _3028 = textureGatherOffset((sampler2D(ShadowMaps[_2396], View_SharedPointClampedSampler)), vec2(_2864, _2865), ivec2(0, 2));
                        D _3090 = dot(vec2(_2946, _3020), vec2(_2672, _2675));
                        D _3093 = _3090 + _2675;
                        D _3094 = _2876 + _3090;
                        D _3095 = _3090 + _2672;
                        vec4 _3097 = textureGatherOffset((sampler2D(ShadowMaps[_2396], View_SharedPointClampedSampler)), vec2(_2864, _2865), ivec2(2));
                        D _3159 = 1.0 - _2862;
                        vec4 _3182 = vec4((((spvNClamp((((_2923 + _2882.w) + (spvNMin(abs(_2870), 0.0) * D(int(uint(_2870 > 0.0) - uint(_2870 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _3159) + spvNClamp((((_2923 + _2882.z) + (spvNMin(abs(_2878), 0.0) * D(int(uint(_2878 > 0.0) - uint(_2878 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2923 + _2956.w) + (spvNMin(abs(_2947), 0.0) * D(int(uint(_2947 > 0.0) - uint(_2947 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2923 + _2956.z) + (spvNMin(abs(_2952), 0.0) * D(int(uint(_2952 > 0.0) - uint(_2952 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2862), (((spvNClamp((((_2923 + _2882.x) + (spvNMin(abs(_2873), 0.0) * D(int(uint(_2873 > 0.0) - uint(_2873 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _3159) + spvNClamp((((_2923 + _2882.y) + (spvNMin(abs(_2877), 0.0) * D(int(uint(_2877 > 0.0) - uint(_2877 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2923 + _2956.x) + (spvNMin(abs(_2950), 0.0) * D(int(uint(_2950 > 0.0) - uint(_2950 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2923 + _2956.y) + (spvNMin(abs(_2951), 0.0) * D(int(uint(_2951 > 0.0) - uint(_2951 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2862), (((spvNClamp((((_2923 + _3028.w) + (spvNMin(abs(_3021), 0.0) * D(int(uint(_3021 > 0.0) - uint(_3021 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _3159) + spvNClamp((((_2923 + _3028.z) + (spvNMin(abs(_3026), 0.0) * D(int(uint(_3026 > 0.0) - uint(_3026 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2923 + _3097.w) + (spvNMin(abs(_3090), 0.0) * D(int(uint(_3090 > 0.0) - uint(_3090 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2923 + _3097.z) + (spvNMin(abs(_3095), 0.0) * D(int(uint(_3095 > 0.0) - uint(_3095 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2862), (((spvNClamp((((_2923 + _3028.x) + (spvNMin(abs(_3024), 0.0) * D(int(uint(_3024 > 0.0) - uint(_3024 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _3159) + spvNClamp((((_2923 + _3028.y) + (spvNMin(abs(_3025), 0.0) * D(int(uint(_3025 > 0.0) - uint(_3025 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2923 + _3097.x) + (spvNMin(abs(_3093), 0.0) * D(int(uint(_3093 > 0.0) - uint(_3093 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2923 + _3097.y) + (spvNMin(abs(_3094), 0.0) * D(int(uint(_3094 > 0.0) - uint(_3094 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2862));
                        frontier_phi_32_31_ladder = dot(_3182, vec4(1.0 - _2863, 1.0, 1.0, _2863)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        frontier_phi_32_31_ladder = 1.0;
                    }
                    _2431 = frontier_phi_32_31_ladder;
                }
                else
                {
                    _2431 = 1.0;
                }
                D _2437 = _1897 - _244;
                D _2438 = _1898 - _245;
                D _2439 = _1899 - _246;
                D _2440 = dot(vec3(_2437, _2438, _2439), vec3(_2437, _2438, _2439));
                D _2684;
                D _2685;
                D _2686;
                if (_2440 > 9.9999997473787516355514526367188e-05)
                {
                    D _2680 = inversesqrt(_2440);
                    _2684 = _2680 * _2437;
                    _2685 = _2680 * _2438;
                    _2686 = _2680 * _2439;
                }
                else
                {
                    _2684 = 0.0;
                    _2685 = 0.0;
                    _2686 = 0.0;
                }
                D _2687 = _1919 * _1919;
                D _2691 = (_1900 * _1900) * _2440;
                D _2694 = spvNClamp(1.0 - (_2691 * _2691), 0.0, 1.0);
                D _3198;
                if (_1958)
                {
                    D _3196 = spvNClamp((dot(vec3(_2684, _2685, _2686), vec3(_1906, _1907, _1908)) - _1912) * _1913, 0.0, 1.0);
                    _3198 = _3196 * _3196;
                }
                else
                {
                    _3198 = 1.0;
                }
                D _3199 = ((_2694 * _2694) * D(_2440 >= _2687)) * _3198;
                D _3686;
                D _3688;
                D _3690;
                if ((_1910 & 262144u) == 0u)
                {
                    _3686 = 1.0;
                    _3688 = 1.0;
                    _3690 = 1.0;
                }
                else
                {
                    D _3693 = (-0.0) - _1907;
                    D _3694 = (-0.0) - _1908;
                    D _3695 = (-0.0) - _1906;
                    D _3705 = (-0.0) - _2684;
                    D _3706 = (-0.0) - _2685;
                    D _3707 = (-0.0) - _2686;
                    D _3710 = fma(_3694, _3707, fma(_3693, _3706, _2684 * _1906));
                    D _3713 = fma(_1917, _3707, fma(_1916, _3706, _1915 * _3705));
                    D _3721 = atan(((-0.0) - _3713) / ((-0.0) - _3710));
                    bool _3726 = _3710 > (-0.0);
                    bool _3727 = _3710 == (-0.0);
                    bool _3728 = _3713 <= (-0.0);
                    bool _3729 = _3713 > (-0.0);
                    vec4 _3751 = texture((sampler2D(ForwardLightProfileTextures[_1922 + 0u], View_SharedBilinearWrappedSampler)), vec2(fract((_3727 && _3728) ? 1.25 : ((_3727 && _3729) ? 0.75 : ((((_3726 && _3729) ? (_3721 + (-3.1415927410125732421875)) : ((_3726 && _3728) ? (_3721 + 3.1415927410125732421875) : _3721)) * 0.15915493667125701904296875) + 1.0))), (asin((-0.0) - fma((_1916 * _3695) - (_1915 * _3693), _3707, fma((_1915 * _3694) - (_1917 * _3695), _3706, ((_1917 * _3693) - (_1916 * _3694)) * _3705))) * 0.3183098733425140380859375) + 0.5));
                    _3686 = _3751.x;
                    _3688 = _3751.y;
                    _3690 = _3751.z;
                }
                D _4072;
                D _4074;
                D _4076;
                D _4078;
                D _4080;
                D _4082;
                D _4084;
                D _4086;
                D _4088;
                D _4090;
                D _4092;
                D _4094;
                for (;;)
                {
                    if (_3199 > 0.0)
                    {
                        D _4130;
                        if (_1957)
                        {
                            if (!(_2431 > 0.0))
                            {
                                _4072 = 0.0;
                                _4074 = 0.0;
                                _4076 = 0.0;
                                _4078 = 0.0;
                                _4080 = 0.0;
                                _4082 = 0.0;
                                _4084 = 0.0;
                                _4086 = 0.0;
                                _4088 = 0.0;
                                _4090 = 0.0;
                                _4092 = 0.0;
                                _4094 = 0.0;
                                break;
                            }
                            _4130 = _2431;
                        }
                        else
                        {
                            _4130 = 1.0;
                        }
                        D _4132 = spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _2440));
                        D _4133 = 1.0 / _4132;
                        D _4134 = dot(vec3(_805, _806, _807), vec3(_2684, _2685, _2686));
                        D _4145;
                        if (_1919 > 0.0)
                        {
                            D _4142 = sqrt(spvNClamp(_2687 * _4133, 0.0, 1.0));
                            D frontier_phi_88_87_ladder;
                            if (_4142 > spvNMax(9.9999997473787516355514526367188e-06, _4134))
                            {
                                D _4162 = spvNMax((-0.0) - _4142, _4134) + _4142;
                                frontier_phi_88_87_ladder = (_4162 * _4162) * (0.25 / _4142);
                            }
                            else
                            {
                                frontier_phi_88_87_ladder = _4134;
                            }
                            _4145 = frontier_phi_88_87_ladder;
                        }
                        else
                        {
                            _4145 = _4134;
                        }
                        D _4202;
                        D _4203;
                        D _4204;
                        D _4147;
                        D _4149;
                        D _4153;
                        D _4154;
                        bool _4157;
                        for (;;)
                        {
                            _4147 = spvNMax(0.0, _4145);
                            _4149 = _1293 * _1293;
                            _4153 = spvNClamp(((1.0 - _4149) * _1919) * inversesqrt(_4132), 0.0, 1.0);
                            _4154 = dot(vec3(_255, _257, _258), vec3(_2684, _2685, _2686));
                            _4157 = _4153 > 0.0;
                            D _4173;
                            D _4175;
                            if (_4157)
                            {
                                D _4168 = sqrt(spvNMax(0.0, 1.0 - (_4153 * _4153)));
                                D _4171 = ((_4134 * 2.0) * _919) - _4154;
                                if (!(!(_4171 >= _4168)))
                                {
                                    _4202 = _931;
                                    _4203 = 1.0;
                                    _4204 = _4154;
                                    break;
                                }
                                D _4191 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, 1.0 - (_4171 * _4171))) * _4153;
                                _4173 = (_4191 * (((_945 * 2.0) + (-1.0)) - (_4171 * _4154))) + (_4168 * _4154);
                                _4175 = (_4191 * (_919 - (_4171 * _4134))) + (_4168 * _4134);
                            }
                            else
                            {
                                _4173 = _4154;
                                _4175 = _4134;
                            }
                            D _4180 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_4173 * 2.0) + 2.0));
                            _4202 = spvNMin(_4180 * (_4173 + 1.0), 1.0);
                            _4203 = spvNClamp(_4180 * (_4175 + _919), 0.0, 1.0);
                            _4204 = _4173;
                            break;
                        }
                        D _4205 = spvNMax(9.9999997473787516355514526367188e-06, _4202);
                        D _4212 = sqrt(spvNMax(0.0, 1.0 - (_946 * 0.444444477558135986328125)));
                        D _4216 = (_925 * 0.666666686534881591796875) - (_4212 * _805);
                        D _4217 = (_926 * 0.666666686534881591796875) - (_4212 * _806);
                        D _4218 = (_927 * 0.666666686534881591796875) - (_4212 * _807);
                        D _4222 = inversesqrt(dot(vec3(_4216, _4217, _4218), vec3(_4216, _4217, _4218)));
                        D _4229 = dot(vec3((-0.0) - (_4222 * _4216), (-0.0) - (_4222 * _4217), (-0.0) - (_4222 * _4218)), vec3(_2684, _2685, _2686));
                        D _4232 = _4149 * _4149;
                        D _4246 = ((_4203 * _4203) * (_4232 + (-1.0))) + 1.0;
                        D _4252 = (_4147 * 2.0) * _990;
                        D _4257 = 1.0 - _4205;
                        D _4258 = _4257 * _4257;
                        D _4260 = (_4258 * _4258) * _4257;
                        D _4264 = spvNMin(dot(vec3(_903, _904, _905), vec3(16.666667938232421875)), 1.0);
                        D _4277 = spvNMax(0.039999999105930328369140625, _1293);
                        D _4290 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_4277 * _4147) + 0.02669160068035125732421875) / (_4147 + 0.4664950072765350341796875)) * exp2(((1.0 / _4277) * _4147) * log2(_4277)), 0.0, 1.0));
                        D _4291 = 1.0 - _4147;
                        D _4292 = _4291 * _4291;
                        D _4304 = ((_4292 * _4292) * _4291) * exp2(log2((exp2((_4277 * 4.7702999114990234375) * log2(_4147)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _4277);
                        D _4307 = (1.0 / _4290) * (1.0 - _4290);
                        D _4311 = (_4307 * _903) + 1.0;
                        D _4312 = (_4307 * _904) + 1.0;
                        D _4313 = (_4307 * _905) + 1.0;
                        D _4314 = _4290 - _4304;
                        D _4328 = spvNClamp(1.0 - dot(vec3(_4311 * ((_4314 * _903) + _4304), _4312 * ((_4314 * _904) + _4304), _4313 * ((_4314 * _905) + _4304)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                        D _4332 = ((((_4232 * 0.3183098733425140380859375) * _4147) * (1.0 / (_4246 * _4246))) * (_4157 ? ((1.0 / ((((_4153 * 0.25) * (_4153 + (_4149 * 3.0))) * (1.0 / _4205)) + _4232)) * _4232) : 1.0)) * (0.5 / ((_4149 * ((_990 + _4147) - _4252)) + _4252));
                        D _4333 = _4147 * 0.3183098733425140380859375;
                        D _4343 = (((_4229 * _4229) + 1.0) * 0.0323704965412616729736328125) * exp2(log2(spvNMax(0.0, (_4229 * 1.2000000476837158203125) + 1.36000001430511474609375)) * (-1.5));
                        D _4346 = ((_4204 * _4204) + 1.0) * 0.05968309938907623291015625;
                        D _4347 = spvNMin(1.0, _831);
                        D _4349 = (_831 + 1.0) - _4347;
                        D _4350 = _4349 * _4349;
                        D _4353 = 1.0 - ((_4350 * _4350) * _4349);
                        D _4354 = _4353 * _4353;
                        D _4359 = ((_4354 * _4354) * (_4353 * (_831 - _4347))) + _4347;
                        D _4362 = sqrt(spvNMax(0.0, 1.0 - _4359));
                        D _4366 = 1.0 - spvNClamp((_1293 * 3.5) + (-0.5), 0.0, 1.0);
                        D _4367 = _4366 * _4366;
                        D _4377 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_1324 * _4362) * spvNClamp(1.0 - ((_4367 * _4367) * _4366), 0.0, 1.0))) * _4147, 0.0, 1.0);
                        D _4382 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _4362)) * _4147, 0.0, 1.0);
                        D _4384 = spvNMin(_4130, _4377 * _4377);
                        D _4385 = spvNMin(_4130, _4382 * _4382);
                        D _4386 = spvNMin(_4130, _4359);
                        D _4390 = (_3199 * _1902) * _3686;
                        D _4391 = (_3199 * _1903) * _3688;
                        D _4392 = (_3199 * _1904) * _3690;
                        D _4393 = _4133 * _4390;
                        D _4397 = _4133 * _4391;
                        D _4401 = _4133 * _4392;
                        _4072 = (_4393 * _4346) * _4386;
                        _4074 = (_4397 * _4346) * _4386;
                        _4076 = (_4401 * _4346) * _4386;
                        _4078 = (_4393 * _4343) * _4386;
                        _4080 = (_4397 * _4343) * _4386;
                        _4082 = (_4401 * _4343) * _4386;
                        _4084 = (((_4393 * spvNClamp(((_4264 - _903) * _4260) + _903, 0.0, 1.0)) * _4332) * _4311) * _4384;
                        _4086 = (((_4397 * _4332) * spvNClamp(((_4264 - _904) * _4260) + _904, 0.0, 1.0)) * _4312) * _4384;
                        _4088 = (((_4401 * _4332) * spvNClamp(((_4264 - _905) * _4260) + _905, 0.0, 1.0)) * _4313) * _4384;
                        _4090 = ((((_4390 * _855) * _4133) * _4333) * _4328) * _4385;
                        _4092 = ((((_4391 * _856) * _4133) * _4333) * _4328) * _4385;
                        _4094 = ((((_4392 * _857) * _4133) * _4333) * _4328) * _4385;
                        break;
                    }
                    else
                    {
                        _4072 = 0.0;
                        _4074 = 0.0;
                        _4076 = 0.0;
                        _4078 = 0.0;
                        _4080 = 0.0;
                        _4082 = 0.0;
                        _4084 = 0.0;
                        _4086 = 0.0;
                        _4088 = 0.0;
                        _4090 = 0.0;
                        _4092 = 0.0;
                        _4094 = 0.0;
                        break;
                    }
                }
                frontier_phi_47_pred = _4086 + _1882;
                frontier_phi_47_pred_1 = _4072 + _1875;
                frontier_phi_47_pred_2 = _4074 + _1876;
                frontier_phi_47_pred_3 = _4076 + _1877;
                frontier_phi_47_pred_4 = _4078 + _1878;
                frontier_phi_47_pred_5 = _4080 + _1879;
                frontier_phi_47_pred_6 = _4082 + _1880;
                frontier_phi_47_pred_7 = _4084 + _1881;
                frontier_phi_47_pred_8 = _4088 + _1883;
                frontier_phi_47_pred_9 = _4092 + _1885;
                frontier_phi_47_pred_10 = _4090 + _1884;
                frontier_phi_47_pred_11 = _1892;
                frontier_phi_47_pred_12 = _1891;
                frontier_phi_47_pred_13 = _1890;
                frontier_phi_47_pred_14 = _1889;
                frontier_phi_47_pred_15 = _1888;
                frontier_phi_47_pred_16 = _1887;
                frontier_phi_47_pred_17 = _4094 + _1886;
            }
            else
            {
                D _2061 = _1897 - _244;
                D _2062 = _1898 - _245;
                D _2063 = _1899 - _246;
                D _2064 = dot(vec3(_2061, _2062, _2063), vec3(_2061, _2062, _2063));
                D _2068 = (_1900 * _1900) * _2064;
                D _2069 = _2068 * _2068;
                D _2070 = _2069 * _2069;
                D _2073 = spvNClamp(1.0 - (_2070 * _2070), 0.0, 1.0);
                D _2074 = _2073 * _2073;
                D _2075 = _2074 * _2074;
                D _2076 = _2075 * _2075;
                D _2455;
                D _2457;
                D _2459;
                D _2461;
                D _2463;
                D _2465;
                if (_2076 > 0.0)
                {
                    D _2447 = dot(vec3(_252, _253, _254), vec3(_805, _806, _807)) * 2.0;
                    D _2451 = _252 - (_2447 * _805);
                    D _2452 = _253 - (_2447 * _806);
                    D _2453 = _254 - (_2447 * _807);
                    D _3753;
                    D _3754;
                    D _3755;
                    D _3756;
                    D _3757;
                    D _3758;
                    D _3759;
                    D _3760;
                    D _3761;
                    D _3762;
                    D _3763;
                    if (_1920 == 0.0)
                    {
                        D _3204;
                        D _3205;
                        D _3206;
                        if (_2064 > 9.9999997473787516355514526367188e-05)
                        {
                            D _3200 = inversesqrt(_2064);
                            _3204 = _3200 * _2061;
                            _3205 = _3200 * _2062;
                            _3206 = _3200 * _2063;
                        }
                        else
                        {
                            _3204 = 0.0;
                            _3205 = 0.0;
                            _3206 = 0.0;
                        }
                        D _3209 = 1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _2064));
                        _3753 = _3209;
                        _3754 = (_1919 * _1919) * _3209;
                        _3755 = _3204;
                        _3756 = _3205;
                        _3757 = _3206;
                        _3758 = _3204;
                        _3759 = _3205;
                        _3760 = _3206;
                        _3761 = _3204;
                        _3762 = _3205;
                        _3763 = _3206;
                    }
                    else
                    {
                        D _2698 = _1920 * 0.5;
                        D _2699 = _2698 * _1906;
                        D _2700 = _2698 * _1907;
                        D _2701 = _2698 * _1908;
                        D _2702 = _2061 - _2699;
                        D _2703 = _2062 - _2700;
                        D _2704 = _2063 - _2701;
                        D _2705 = _2699 + _2061;
                        D _2706 = _2700 + _2062;
                        D _2707 = _2701 + _2063;
                        D _2715 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2702, _2703, _2704), vec3(_2702, _2703, _2704))));
                        D _2717 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2705, _2706, _2707), vec3(_2705, _2706, _2707))));
                        D _2718 = _2717 * _2715;
                        D _2734 = (1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(_2718, ((dot(vec3(_2702, _2703, _2704), vec3(_2705, _2706, _2707)) * 0.5) * _2718) + 0.5))) * _2718;
                        D _2736 = (_1906 * 2.0) * _2698;
                        D _2738 = (_1907 * 2.0) * _2698;
                        D _2740 = (_1908 * 2.0) * _2698;
                        D _2741 = dot(vec3(_2736, _2738, _2740), vec3(_2736, _2738, _2740));
                        D _3242;
                        D _3243;
                        D _3244;
                        if (_2741 > 9.9999997473787516355514526367188e-05)
                        {
                            D _3212 = dot(vec3(_2451, _2452, _2453), vec3(_2736, _2738, _2740));
                            D _3228 = spvNClamp((1.0 / (_2741 - (_3212 * _3212))) * dot(vec3(_2702, _2703, _2704), vec3((_3212 * _2451) - _2736, (_3212 * _2452) - _2738, (_3212 * _2453) - _2740)), 0.0, 1.0);
                            D _3232 = (_3228 * _2736) + _2702;
                            D _3233 = (_3228 * _2738) + _2703;
                            D _3234 = (_3228 * _2740) + _2704;
                            D _3238 = inversesqrt(dot(vec3(_3232, _3233, _3234), vec3(_3232, _3233, _3234)));
                            _3242 = _3232 * _3238;
                            _3243 = _3233 * _3238;
                            _3244 = _3234 * _3238;
                        }
                        else
                        {
                            _3242 = _2702;
                            _3243 = _2703;
                            _3244 = _2704;
                        }
                        _3753 = _2734;
                        _3754 = (_1919 * _1919) * _2734;
                        _3755 = _2715 * _2702;
                        _3756 = _2715 * _2703;
                        _3757 = _2715 * _2704;
                        _3758 = _2717 * _2705;
                        _3759 = _2717 * _2706;
                        _3760 = _2717 * _2707;
                        _3761 = _3242;
                        _3762 = _3243;
                        _3763 = _3244;
                    }
                    D _3773 = _3754 + 1.0;
                    D _3778 = _3761 - _252;
                    D _3779 = _3762 - _253;
                    D _3780 = _3763 - _254;
                    D _3784 = inversesqrt(dot(vec3(_3778, _3779, _3780), vec3(_3778, _3779, _3780)));
                    D _3785 = _3784 * _3778;
                    D _3786 = _3784 * _3779;
                    D _3787 = _3784 * _3780;
                    D _3794 = spvNClamp(dot(vec3(_805, _806, _807), vec3(_3785, _3786, _3787)), 0.0, 1.0);
                    D _3795 = _1293 * _1293;
                    D _3801 = spvNClamp(((1.0 - _3795) * _1919) * sqrt(_3753), 0.0, 1.0);
                    D _3814 = exp2(log2(spvNClamp((((_3801 * 0.25) * (_3801 + (_3795 * 3.0))) * (1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_255, _257, _258), vec3(_3785, _3786, _3787))))) + (_3795 * _3795), 0.0, 1.0)) * 0.25);
                    D _3818 = spvNClamp(dot(vec3(_3755, _3756, _3757), vec3(_3758, _3759, _3760)), 0.0, 1.0);
                    D _3820 = _3814 * _3814;
                    D _3821 = _3820 * _3820;
                    D _4110;
                    if (_3818 < 1.0)
                    {
                        D _4101 = sqrt(spvNClamp((1.0 / (_3818 + 1.0)) * (1.0 - _3818), 0.0, 1.0));
                        _4110 = (1.0 / spvNClamp(((_4101 * 0.25) * (_4101 + (_3820 * 3.0))) + _3821, 0.0, 1.0)) * _3821;
                    }
                    else
                    {
                        _4110 = 1.0;
                    }
                    D _4114 = ((_3794 * _3794) * (_3821 + (-1.0))) + 1.0;
                    D _4117 = spvNMax(0.0, (((dot(vec3(_805, _806, _807), vec3(_3758, _3759, _3760)) + dot(vec3(_805, _806, _807), vec3(_3755, _3756, _3757))) * 0.5) + _3754) * (1.0 / (_3773 * _3773))) * 0.3183098733425140380859375;
                    D _4120 = ((_4117 * _3821) * _4110) * (1.0 / (_4114 * _4114));
                    D _4122 = (_2076 * _1902) * _3753;
                    D _4124 = (_2076 * _1903) * _3753;
                    D _4126 = (_2076 * _1904) * _3753;
                    _2455 = _4120 * _4122;
                    _2457 = _4120 * _4124;
                    _2459 = _4120 * _4126;
                    _2461 = _4117 * _4122;
                    _2463 = _4117 * _4124;
                    _2465 = _4117 * _4126;
                }
                else
                {
                    _2455 = 0.0;
                    _2457 = 0.0;
                    _2459 = 0.0;
                    _2461 = 0.0;
                    _2463 = 0.0;
                    _2465 = 0.0;
                }
                frontier_phi_47_pred = _1882;
                frontier_phi_47_pred_1 = _1875;
                frontier_phi_47_pred_2 = _1876;
                frontier_phi_47_pred_3 = _1877;
                frontier_phi_47_pred_4 = _1878;
                frontier_phi_47_pred_5 = _1879;
                frontier_phi_47_pred_6 = _1880;
                frontier_phi_47_pred_7 = _1881;
                frontier_phi_47_pred_8 = _1883;
                frontier_phi_47_pred_9 = _1885;
                frontier_phi_47_pred_10 = _1884;
                frontier_phi_47_pred_11 = _2465 + _1892;
                frontier_phi_47_pred_12 = _2463 + _1891;
                frontier_phi_47_pred_13 = _2461 + _1890;
                frontier_phi_47_pred_14 = _2459 + _1889;
                frontier_phi_47_pred_15 = _2457 + _1888;
                frontier_phi_47_pred_16 = _2455 + _1887;
                frontier_phi_47_pred_17 = _1886;
            }
            _1479 = frontier_phi_47_pred;
            _1465 = frontier_phi_47_pred_1;
            _1467 = frontier_phi_47_pred_2;
            _1469 = frontier_phi_47_pred_3;
            _1471 = frontier_phi_47_pred_4;
            _1473 = frontier_phi_47_pred_5;
            _1475 = frontier_phi_47_pred_6;
            _1477 = frontier_phi_47_pred_7;
            _1481 = frontier_phi_47_pred_8;
            _1485 = frontier_phi_47_pred_9;
            _1483 = frontier_phi_47_pred_10;
            _1499 = frontier_phi_47_pred_11;
            _1497 = frontier_phi_47_pred_12;
            _1495 = frontier_phi_47_pred_13;
            _1493 = frontier_phi_47_pred_14;
            _1491 = frontier_phi_47_pred_15;
            _1489 = frontier_phi_47_pred_16;
            _1487 = frontier_phi_47_pred_17;
            uint _1894 = _1893 + 1u;
            if (_1894 == _1457)
            {
                break;
            }
            else
            {
                _1875 = _1465;
                _1876 = _1467;
                _1877 = _1469;
                _1878 = _1471;
                _1879 = _1473;
                _1880 = _1475;
                _1881 = _1477;
                _1882 = _1479;
                _1883 = _1481;
                _1884 = _1483;
                _1885 = _1485;
                _1886 = _1487;
                _1887 = _1489;
                _1888 = _1491;
                _1889 = _1493;
                _1890 = _1495;
                _1891 = _1497;
                _1892 = _1499;
                _1893 = _1894;
                continue;
            }
        }
        _1464 = _1465;
        _1466 = _1467;
        _1468 = _1469;
        _1470 = _1471;
        _1472 = _1473;
        _1474 = _1475;
        _1476 = _1477;
        _1478 = _1479;
        _1480 = _1481;
        _1482 = _1483;
        _1484 = _1485;
        _1486 = _1487;
        _1488 = _1489;
        _1490 = _1491;
        _1492 = _1493;
        _1494 = _1495;
        _1496 = _1497;
        _1498 = _1499;
    }
    D _1533 = (_244 - View._m0[180u].x) * View._m0[182u].x;
    D _1534 = (_245 - View._m0[180u].y) * View._m0[182u].y;
    D _1535 = (_246 - View._m0[180u].z) * View._m0[182u].z;
    vec4 _1540 = textureLod(sampler3D(TranslucentBasePass_TranslucencyLightingVolumeEnvironmentA, View_SharedBilinearClampedSampler), vec3(_1533, _1534, _1535), 0.0);
    D _1542 = _1540.x;
    D _1578;
    D _1579;
    D _1580;
    if (_749 < 1.0)
    {
        _1578 = _727.x / ((_771 / _748) + 1.0);
        _1579 = _727.y / ((_772 / _748) + 1.0);
        _1580 = _727.z / ((_773 / _748) + 1.0);
    }
    else
    {
        _1578 = 0.0;
        _1579 = 0.0;
        _1580 = 0.0;
    }
    D _1585 = View._m0[164u].z * _1542;
    D _1586 = View._m0[164u].z * _1540.y;
    D _1587 = View._m0[164u].z * _1540.z;
    D _1588 = spvNClamp(_987, 0.0, 1.0);
    D _1589 = spvNClamp(_988, 0.0, 1.0);
    D _1590 = spvNClamp(_989, 0.0, 1.0);
    D _1600 = spvNClamp((-0.0) - _987, 0.0, 1.0);
    D _1601 = spvNClamp((-0.0) - _988, 0.0, 1.0);
    D _1602 = spvNClamp((-0.0) - _989, 0.0, 1.0);
    D _1609 = dot(vec3(textureLod(sampler3D(TranslucentBasePass_TranslucencyLightingVolumeEnvironmentC, View_SharedBilinearClampedSampler), vec3(_1533, _1534, _1535), 0.0).xyz()), vec3(_1600 * _1600, _1601 * _1601, _1602 * _1602)) + dot(vec3(textureLod(sampler3D(TranslucentBasePass_TranslucencyLightingVolumeEnvironmentB, View_SharedBilinearClampedSampler), vec3(_1533, _1534, _1535), 0.0).xyz()), vec3(_1588 * _1588, _1589 * _1589, _1590 * _1590));
    D _1610 = dot(vec3(_1542, _1540.yz()), vec3(0.2125999927520751953125, 0.715200006961822509765625, 0.072200000286102294921875));
    D _1618 = (_1610 > 0.0) ? (1.0 / _1610) : 0.0;
    D _1649 = ((_1578 * _1244) * spvNClamp(1.0 - (_1263 * _1253), 0.0, 1.0)) * ((_1585 + _1470) + ((((_1585 * _1609) * _1618) - _1585) * 0.6480000019073486328125));
    D _1652 = ((_1579 * _1244) * spvNClamp(1.0 - (_1264 * _1253), 0.0, 1.0)) * ((_1586 + _1472) + ((((_1586 * _1609) * _1618) - _1586) * 0.6480000019073486328125));
    D _1655 = ((_1580 * _1244) * spvNClamp(1.0 - (_1265 * _1253), 0.0, 1.0)) * ((_1587 + _1474) + ((((_1587 * _1609) * _1618) - _1587) * 0.6480000019073486328125));
    D _1669 = spvNClamp(_1275, 0.0, 1.0);
    D _1679 = ((_805 - _942) * _973) + _942;
    D _1680 = ((_806 - _943) * _973) + _943;
    D _1681 = ((_807 - _944) * _973) + _944;
    D _1685 = inversesqrt(dot(vec3(_1679, _1680, _1681), vec3(_1679, _1680, _1681)));
    D _1694 = 10.0 / spvNMax(9.9999997473787516355514526367188e-06, _972);
    D _1722 = fma(_243, View._m0[2u].x, fma(_242, View._m0[1u].x, View._m0[0u].x * _241)) + View._m0[3u].x;
    D _1726 = fma(_243, View._m0[2u].y, fma(_242, View._m0[1u].y, View._m0[0u].y * _241)) + View._m0[3u].y;
    D _1730 = fma(_243, View._m0[2u].z, fma(_242, View._m0[1u].z, View._m0[0u].z * _241)) + View._m0[3u].z;
    D _1734 = fma(_243, View._m0[2u].w, fma(_242, View._m0[1u].w, View._m0[0u].w * _241)) + View._m0[3u].w;
    D _1741 = ((_1679 * _116) * _1685) + _241;
    D _1742 = ((_1680 * _116) * _1685) + _242;
    D _1743 = ((_1681 * _116) * _1685) + _243;
    D _1776 = 1.0 / _1734;
    D _1777 = _1776 * _1722;
    D _1778 = _1776 * _1726;
    D _1782 = (_1776 * _1730) + (0.0500000007450580596923828125 / _1734);
    D _1783 = 1.0 / (fma(_1743, View._m0[2u].w, fma(_1742, View._m0[1u].w, View._m0[0u].w * _1741)) + View._m0[3u].w);
    D _1794 = 1.0 / ((View._m0[36u].w * _1694) + _1734);
    D _1797 = (_1783 * (fma(_1743, View._m0[2u].x, fma(_1742, View._m0[1u].x, View._m0[0u].x * _1741)) + View._m0[3u].x)) - _1777;
    D _1798 = (_1783 * (fma(_1743, View._m0[2u].y, fma(_1742, View._m0[1u].y, View._m0[0u].y * _1741)) + View._m0[3u].y)) - _1778;
    D _1800 = (_1794 * ((View._m0[36u].x * _1694) + _1722)) - _1777;
    D _1801 = (_1794 * ((View._m0[36u].y * _1694) + _1726)) - _1778;
    D _1806 = sqrt((_1797 * _1797) + (_1798 * _1798)) * 0.5;
    D _1824 = spvNMin(1.0 - (spvNMax(0.0, abs((_1806 * _1777) + _1797) - _1806) / abs(_1797)), 1.0 - (spvNMax(0.0, abs((_1806 * _1778) + _1798) - _1806) / abs(_1798))) / _1806;
    D _1825 = _1824 * _1797;
    D _1826 = _1824 * _1798;
    D _1827 = _1824 * ((_1783 * (fma(_1743, View._m0[2u].z, fma(_1742, View._m0[1u].z, View._m0[0u].z * _1741)) + View._m0[3u].z)) - _1782);
    uvec2 _1833 = uvec2(textureSize(TranslucentBasePass_HZBTexture, int(0u)));
    D _1835 = D(int(_1833.x));
    D _1837 = D(int(_1833.y));
    uint _1858 = max(1u, min(uint(ceil((spvNClamp((1.0 / spvNMax(9.9999997473787516355514526367188e-05, sqrt((_1825 * _1825) + (_1826 * _1826)))) * sqrt((_1800 * _1800) + (_1801 * _1801)), 0.0, 1.0) * 8.0) + _279)), 8u));
    D _1863 = ((_1777 * 0.5) + 0.5) * TranslucentBasePass_2._m0[198u].x;
    D _1864 = (0.5 - (_1778 * 0.5)) * TranslucentBasePass_2._m0[198u].y;
    D _1867 = (TranslucentBasePass_2._m0[198u].x * 0.0625) * _1825;
    D _1870 = (TranslucentBasePass_2._m0[198u].y * (-0.0625)) * _1826;
    D _1871 = _1827 * 0.125;
    D _1873 = spvNMax(abs(_1827), _1782 - ((1.0 / (fma(_116, View._m0[38u].w, 0.0) + _1734)) * (fma(_116, View._m0[38u].z, 0.0) + _1730))) * 0.125;
    D _2044;
    D _2046;
    D _2048;
    D _2050;
    if (_1858 == 0u)
    {
        _2044 = 0.0;
        _2046 = 0.0;
        _2048 = 0.0;
        _2050 = 0.0;
    }
    else
    {
        D frontier_phi_55;
        D frontier_phi_55_1;
        D frontier_phi_55_2;
        D frontier_phi_55_3;
        D _2368 = 0.0;
        uint _2370 = 0u;
        D _2369;
        D _2372;
        bool _2395;
        for (;;)
        {
            _2372 = D(_2370);
            D _2373 = _2372 + _279;
            vec4 _2387 = texelFetch(TranslucentBasePass_HZBTexture, ivec2_(uvec2(uint(int(floor(((_2373 * _1867) + _1863) * _1835))), uint(int(floor(((_2373 * _1870) + _1864) * _1837))))), int(0u));
            D _2389 = _2387.x;
            _2369 = ((_2373 * _1871) + _1782) - _2389;
            _2395 = (abs(((-0.0) - _1873) - _2369) < _1873) && (_2389 != 0.0);
            if (_2395)
            {
                D _2624 = (_2370 == 0u) ? (_2369 - _1871) : _2368;
                D _2631 = abs(((_279 + (-1.0)) + _2372) + spvNClamp(_2624 / (_2624 - _2369), 0.0, 1.0));
                D _2636 = spvNMin(_2631 * 0.125, 1.0);
                frontier_phi_55 = 1.0 - (_2636 * _2636);
                frontier_phi_55_1 = (_2631 * _1871) + _1782;
                frontier_phi_55_2 = (_2631 * _1870) + _1864;
                frontier_phi_55_3 = (_2631 * _1867) + _1863;
                break;
            }
            else
            {
                uint _2371 = _2370 + 1u;
                if (_2371 < _1858)
                {
                    _2368 = _2369;
                    _2370 = _2371;
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
        _2044 = frontier_phi_55_3;
        _2046 = frontier_phi_55_2;
        _2048 = frontier_phi_55_1;
        _2050 = frontier_phi_55;
    }
    D _2058 = (spvNClamp(_2044 * TranslucentBasePass_2._m0[198u].z, 0.0, 1.0) * 2.0) + (-1.0);
    D _2059 = 1.0 - (spvNClamp(_2046 * TranslucentBasePass_2._m0[198u].w, 0.0, 1.0) * 2.0);
    D _2287;
    D _2288;
    D _2289;
    D _2290;
    if (_2050 > 0.0)
    {
        D _2150 = ((View._m0[73u].x * _2048) + View._m0[73u].y) + (1.0 / ((View._m0[73u].z * _2048) - View._m0[73u].w));
        D _2174 = _2150 * _2058;
        D _2175 = _2150 * _2059;
        D _2186 = (_241 - View._m0[63u].x) - fma(_2150, View._m0[62u].x, fma(_2175, View._m0[61u].x, _2174 * View._m0[60u].x));
        D _2188 = (_242 - View._m0[63u].y) - fma(_2150, View._m0[62u].y, fma(_2175, View._m0[61u].y, _2174 * View._m0[60u].y));
        D _2190 = (_243 - View._m0[63u].z) - fma(_2150, View._m0[62u].z, fma(_2175, View._m0[61u].z, _2174 * View._m0[60u].z));
        uvec2 _2241 = uvec2(textureSize(TranslucentBasePass_SceneColorCopyTexture, int(0u)));
        uint _2260 = uint(min(int(uint(max(int(uint(int(D(int(_2241.x)) * ((View._m0[74u].x * spvNMin(spvNMax(_2058 - ((D(int(uint(_2058 > 0.0) - uint(_2058 < 0.0))) * 2.0) * spvNMax(0.0, abs(_2058) + (-1.0))), -1.0), 1.0)) + View._m0[74u].w)))), int(uint(int(View._m0[158u].x)))))), int(uint(int(View._m0[159u].x + View._m0[158u].x)) + 4294967295u)));
        uint _2261 = uint(min(int(uint(max(int(uint(int(D(int(_2241.y)) * ((View._m0[74u].y * spvNMin(spvNMax(_2059 - ((D(int(uint(_2059 > 0.0) - uint(_2059 < 0.0))) * 2.0) * spvNMax(0.0, abs(_2059) + (-1.0))), -1.0), 1.0)) + View._m0[74u].z)))), int(uint(int(View._m0[158u].y)))))), int(uint(int(View._m0[159u].y + View._m0[158u].y)) + 4294967295u)));
        vec4 _2266 = texelFetch(TranslucentBasePass_SceneColorCopyTexture, ivec2_(uvec2(_2260, _2261)), int(0u));
        _2287 = View._m0[164u].z * spvNMin(_2266.x, 65504.0);
        _2288 = View._m0[164u].z * spvNMin(_2266.y, 65504.0);
        _2289 = View._m0[164u].z * spvNMin(_2266.z, 65504.0);
        _2290 = (D(texelFetch(TranslucentBasePass_SceneTextures_SceneDepthTexture, ivec2_(uvec2(_2260, _2261)), int(0u)).x != 0.0) * _2050) * spvNClamp(1.0 / spvNMax(9.9999997473787516355514526367188e-06, (_972 * _972) * dot(vec3(_2186, _2188, _2190), vec3(_2186, _2188, _2190))), 0.0, 1.0);
    }
    else
    {
        _2287 = 0.0;
        _2288 = 0.0;
        _2289 = 0.0;
        _2290 = 0.0;
    }
    vec4 _2314 = textureLod(sampler2D(TranslucentBasePass_SceneColorCopyTexture, View_SharedBilinearClampedSampler), vec2((_1201 * (View._m0[161u].z * (_1174 - gl_FragCoord.x))) + _997, (_1201 * (View._m0[161u].w * (_1175 - gl_FragCoord.y))) + _998), 0.0);
    SV_Target.x = View._m0[164u].y * ((((((((((_855 * _831) * _1351) * spvNMax(1.0, ((_910 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_910 * 4.79510021209716796875)) + (((_910 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _831)) * _831))) * _1494) + _1482) * _832) + _1476) + ((((((_1585 + _1464) * 0.979626834392547607421875) - _1649) * _1247) + _1649) * _1669)) + (((View._m0[164u].z * _2314.x) * spvNClamp(_1283 - (_1283 * _829), 0.0, 1.0)) * _1669)) + ((_1365 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _2287)) + 29.8973522186279296875) * _2290) + (-29.8973522186279296875)) + _1488)) * spvNClamp(_1343, 0.0, 1.0)));
    SV_Target.y = View._m0[164u].y * ((((((((((_856 * _831) * _1351) * spvNMax(1.0, ((_911 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_911 * 4.79510021209716796875)) + (((_911 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _831)) * _831))) * _1496) + _1484) * _832) + _1478) + ((((((_1586 + _1466) * 0.979626834392547607421875) - _1652) * _1247) + _1652) * _1669)) + (((View._m0[164u].z * _2314.y) * spvNClamp(_1286 - (_1286 * _829), 0.0, 1.0)) * _1669)) + ((_1365 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _2288)) + 29.8973522186279296875) * _2290) + (-29.8973522186279296875)) + _1490)) * spvNClamp(_1344, 0.0, 1.0)));
    SV_Target.z = View._m0[164u].y * ((((((((((_857 * _831) * _1351) * spvNMax(1.0, ((_912 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_912 * 4.79510021209716796875)) + (((_912 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _831)) * _831))) * _1498) + _1486) * _832) + _1480) + ((((((_1587 + _1468) * 0.979626834392547607421875) - _1655) * _1247) + _1655) * _1669)) + (((View._m0[164u].z * _2314.z) * spvNClamp(_1289 - (_1289 * _829), 0.0, 1.0)) * _1669)) + ((_1365 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _2289)) + 29.8973522186279296875) * _2290) + (-29.8973522186279296875)) + _1492)) * spvNClamp(_1345, 0.0, 1.0)));
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
    in.get("TEXCOORD_1", TEXCOORD_1);
    in.get("CONSTANT_CONTEXT", CONSTANT_CONTEXT);
}
void get_outputs(Outputs& o) {
    o.put("SV_Target", SV_Target);
    o.put("SV_Target_1", SV_Target_1);
}
} // namespace S_oftBody_Water_Pool_Flow_Wide_Detail_Environment_Development