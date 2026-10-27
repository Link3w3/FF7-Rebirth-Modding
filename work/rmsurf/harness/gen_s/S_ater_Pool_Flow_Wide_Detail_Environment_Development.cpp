namespace S_ater_Pool_Flow_Wide_Detail_Environment_Development {
using namespace cpuglsl;
static D _4614;
static D _4610;
static D _4611;
static D _4612;
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










void discard_cond(bool _4600)
{
    if (_4600)
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
    vec4 _300 = texture(sampler2D(Material_Texture2D_16, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.z, TEXCOORD.w), View._m0[155u].y);
    D _303 = _300.x;
    vec4 _306 = texture(sampler2D(Material_Texture2D_17, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.z, TEXCOORD.w), View._m0[155u].y);
    D _308 = _306.x;
    vec4 _311 = texture(sampler2D(Material_Texture2D_0, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _318 = texture(sampler2D(Material_Texture2D_1, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _321 = _308 * Material._m0[16u].y;
    D _324 = fract(_303 + (Material._m0[15u].z * Material._m0[16u].x));
    D _325 = _321 * TEXCOORD_1.z;
    D _326 = _321 * TEXCOORD_1.w;
    D _327 = _324 * _325;
    D _328 = _324 * _326;
    D _329 = TEXCOORD.x - _327;
    D _330 = TEXCOORD.y - _328;
    D _332 = (_325 + TEXCOORD.x) - _327;
    D _334 = (_326 + TEXCOORD.y) - _328;
    D _336 = spvNClamp(_324, 0.0, 1.0);
    D _342 = (_336 * _336) * (3.0 - (_336 * 2.0));
    D _343 = _308 * Material._m0[17u].y;
    D _346 = fract(_303 + (Material._m0[15u].z * Material._m0[17u].x));
    D _347 = _343 * TEXCOORD_1.z;
    D _348 = _343 * TEXCOORD_1.w;
    D _349 = _346 * _347;
    D _350 = _346 * _348;
    D _351 = TEXCOORD_1.x - _349;
    D _352 = TEXCOORD_1.y - _350;
    D _354 = (_347 + TEXCOORD_1.x) - _349;
    D _356 = (_348 + TEXCOORD_1.y) - _350;
    D _357 = spvNClamp(_346, 0.0, 1.0);
    D _361 = (_357 * _357) * (3.0 - (_357 * 2.0));
    vec4 _365 = texture(sampler2D(Material_Texture2D_2, View_SharedAnisotropic4XWrappedSampler), vec2(_329, _330), View._m0[155u].y);
    vec4 _369 = texture(sampler2D(Material_Texture2D_2, View_SharedAnisotropic4XWrappedSampler), vec2(_332, _334), View._m0[155u].y);
    D _375 = (_365.x * 2.0) + (-1.0);
    D _377 = (_365.y * 2.0) + (-1.0);
    D _383 = sqrt(spvNMax(0.0, 1.0 - dot(vec2(_375, _377), vec2(_375, _377))));
    D _387 = inversesqrt(dot(vec3(_375, _377, _383), vec3(_375, _377, _383)));
    D _388 = _387 * _375;
    D _389 = _387 * _377;
    D _390 = _387 * _383;
    D _393 = (_369.x * 2.0) + (-1.0);
    D _394 = (_369.y * 2.0) + (-1.0);
    D _400 = sqrt(spvNMax(0.0, 1.0 - dot(vec2(_393, _394), vec2(_393, _394))));
    D _404 = inversesqrt(dot(vec3(_393, _394, _400), vec3(_393, _394, _400)));
    D _414 = (((_404 * _393) - _388) * _342) + _388;
    D _415 = (((_404 * _394) - _389) * _342) + _389;
    D _416 = (((_404 * _400) - _390) * _342) + _390;
    D _420 = inversesqrt(dot(vec3(_414, _415, _416), vec3(_414, _415, _416)));
    D _421 = _414 * _420;
    D _422 = _415 * _420;
    D _423 = _416 * _420;
    vec4 _426 = texture(sampler2D(Material_Texture2D_3, View_SharedAnisotropic4XWrappedSampler), vec2(_329, _330), View._m0[155u].y);
    D _428 = _426.x;
    vec4 _429 = texture(sampler2D(Material_Texture2D_3, View_SharedAnisotropic4XWrappedSampler), vec2(_332, _334), View._m0[155u].y);
    D _431 = _429.x;
    D _433 = _428 * _428;
    D _438 = sqrt(spvNClamp((((_431 * _431) - _433) * _342) + _433, 0.0, 1.0));
    vec4 _441 = texture(sampler2D(Material_Texture2D_4, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _446 = texture(sampler2D(Material_Texture2D_15, View_SharedAnisotropic4XWrappedSampler), vec2(_329, _330), View._m0[155u].y);
    D _448 = _446.x;
    vec4 _449 = texture(sampler2D(Material_Texture2D_15, View_SharedAnisotropic4XWrappedSampler), vec2(_332, _334), View._m0[155u].y);
    D _455 = spvNClamp(((_449.x - _448) * _342) + _448, 0.0, 1.0);
    vec4 _458 = texture(sampler2D(Material_Texture2D_7, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _460 = _458.x;
    vec4 _463 = texture(sampler2D(Material_Texture2D_18, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.z, TEXCOORD.w), View._m0[155u].y);
    vec4 _468 = texture(sampler2D(Material_Texture2D_20, View_SharedAnisotropic4XWrappedSampler), vec2(_351, _352), View._m0[155u].y);
    vec4 _472 = texture(sampler2D(Material_Texture2D_20, View_SharedAnisotropic4XWrappedSampler), vec2(_354, _356), View._m0[155u].y);
    D _478 = (_468.x * 2.0) + (-1.0);
    D _479 = (_468.y * 2.0) + (-1.0);
    D _485 = sqrt(spvNMax(0.0, 1.0 - dot(vec2(_478, _479), vec2(_478, _479))));
    D _489 = inversesqrt(dot(vec3(_478, _479, _485), vec3(_478, _479, _485)));
    D _490 = _489 * _478;
    D _491 = _489 * _479;
    D _492 = _489 * _485;
    D _495 = (_472.x * 2.0) + (-1.0);
    D _496 = (_472.y * 2.0) + (-1.0);
    D _502 = sqrt(spvNMax(0.0, 1.0 - dot(vec2(_495, _496), vec2(_495, _496))));
    D _506 = inversesqrt(dot(vec3(_495, _496, _502), vec3(_495, _496, _502)));
    D _507 = _506 * _495;
    D _508 = _506 * _496;
    D _514 = dFdyFine(TEXCOORD.x) + dFdxFine(TEXCOORD.x);
    D _515 = dFdyFine(TEXCOORD.y) + dFdxFine(TEXCOORD.y);
    D _519 = inversesqrt(dot(vec2(_514, _515), vec2(_514, _515)));
    bool _520 = isnan(_519);
    D _523 = _520 ? 0.0 : (_519 * _514);
    D _524 = _520 ? 0.0 : (_519 * _515);
    D _529 = dFdyFine(_351) + dFdxFine(_351);
    D _530 = dFdyFine(_352) + dFdxFine(_352);
    D _534 = inversesqrt(dot(vec2(_529, _530), vec2(_529, _530)));
    bool _535 = isnan(_534);
    D _538 = _535 ? 0.0 : (_534 * _529);
    D _539 = _535 ? 0.0 : (_534 * _530);
    D _540 = dot(vec2(_538, _539), vec2(_523, _524));
    D _545 = (_538 * _524) - (_539 * _523);
    D _547 = dot(vec2(_490, _491), vec2(_540, (-0.0) - _545));
    D _550 = dot(vec2(_490, _491), vec2(_545, _540));
    D _557 = dFdyFine(_354) + dFdxFine(_354);
    D _558 = dFdyFine(_356) + dFdxFine(_356);
    D _562 = inversesqrt(dot(vec2(_557, _558), vec2(_557, _558)));
    bool _563 = isnan(_562);
    D _566 = _563 ? 0.0 : (_562 * _557);
    D _567 = _563 ? 0.0 : (_562 * _558);
    D _568 = dot(vec2(_566, _567), vec2(_523, _524));
    D _573 = (_566 * _524) - (_567 * _523);
    D _587 = ((dot(vec2(_507, _508), vec2(_568, (-0.0) - _573)) - _547) * _361) + _547;
    D _588 = ((dot(vec2(_507, _508), vec2(_573, _568)) - _550) * _361) + _550;
    D _589 = (((_506 * _502) - _492) * _361) + _492;
    D _593 = inversesqrt(dot(vec3(_587, _588, _589), vec3(_587, _588, _589)));
    D _594 = _593 * _589;
    D _595 = _423 + 1.0;
    D _597 = (-0.0) - (_593 * _587);
    D _599 = (-0.0) - (_593 * _588);
    D _600 = dot(vec3(_421, _422, _595), vec3(_597, _599, _594));
    D _607 = (_600 * _421) - (_595 * _597);
    D _608 = (_600 * _422) - (_595 * _599);
    D _610 = (_600 - _594) * _595;
    D _614 = inversesqrt(dot(vec3(_607, _608, _610), vec3(_607, _608, _610)));
    D _615 = _607 * _614;
    D _616 = _608 * _614;
    D _617 = _610 * _614;
    D _618 = spvNClamp(_460, 0.0, 1.0);
    D _619 = dot(vec3(_421, _422, _423), vec3(_615, _616, _617));
    D _623 = (_619 >= 0.0) ? 1.0 : (-1.0);
    D _626 = acos(spvNClamp(abs(_619), 0.0, 1.0));
    D _629 = sin(_626 * (1.0 - _618));
    D _634 = sin(_626 * _618);
    D _641 = ((_623 * _615) * _634) + (_629 * _421);
    D _642 = ((_623 * _616) * _634) + (_629 * _422);
    D _643 = ((_623 * _617) * _634) + (_629 * _423);
    D _658;
    D _659;
    D _660;
    if (dot(vec3(_641, _642, _643), vec3(_641, _642, _643)) < 9.9999999747524270787835121154785e-07)
    {
        _658 = ((_615 - _421) * _618) + _421;
        _659 = ((_616 - _422) * _618) + _422;
        _660 = ((_617 - _423) * _618) + _423;
    }
    else
    {
        _658 = _641;
        _659 = _642;
        _660 = _643;
    }
    bool _664 = dot(vec3(_658, _659, _660), vec3(_658, _659, _660)) < 9.9999999747524270787835121154785e-07;
    bool _665 = _618 < 0.5;
    D _670 = _664 ? (_665 ? _421 : _615) : _658;
    D _671 = _664 ? (_665 ? _422 : _616) : _659;
    D _672 = _664 ? (_665 ? _423 : _617) : _660;
    D _676 = inversesqrt(dot(vec3(_670, _671, _672), vec3(_670, _671, _672)));
    D _677 = _670 * _676;
    D _678 = _671 * _676;
    D _679 = _672 * _676;
    vec4 _682 = texture(sampler2D(Material_Texture2D_21, View_SharedAnisotropic4XWrappedSampler), vec2(_351, _352), View._m0[155u].y);
    D _684 = _682.x;
    vec4 _685 = texture(sampler2D(Material_Texture2D_21, View_SharedAnisotropic4XWrappedSampler), vec2(_354, _356), View._m0[155u].y);
    D _687 = _685.x;
    D _689 = _684 * _684;
    D _694 = sqrt(spvNClamp((((_687 * _687) - _689) * _361) + _689, 0.0, 1.0));
    vec4 _705 = texture(sampler2D(Material_Texture2D_23, View_SharedAnisotropic4XWrappedSampler), vec2(_351, _352), View._m0[155u].y);
    D _707 = _705.x;
    vec4 _708 = texture(sampler2D(Material_Texture2D_23, View_SharedAnisotropic4XWrappedSampler), vec2(_354, _356), View._m0[155u].y);
    D _715 = 1.0 - _455;
    vec4 _723 = texture(sampler2D(Material_Texture2D_8, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _729 = vec4(g_R.Muddiness.x, g_R.Muddiness.y, g_R.Muddiness.z, 0.0);
    vec4 _736 = texture(sampler2D(Material_Texture2D_26, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _741 = texture(sampler2D(Material_Texture2D_27, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _750 = g_R.TransparencyLog2;
    D _751 = exp2(_750);
    vec4 _754 = texture(sampler2D(Material_Texture2D_28, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _761 = texture(sampler2D(Material_Texture2D_29, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _766 = 1.0 / spvNMax(9.9999999747524270787835121154785e-07, _761.x * 100.0);
    D _773 = g_R.TransmittanceLog2.x;
    D _774 = g_R.TransmittanceLog2.y;
    D _775 = g_R.TransmittanceLog2.z;
    vec4 _781 = vec4(g_R.Thickness);
    D _784 = _781.x * 100.0;
    D _790 = inversesqrt(dot(vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z), vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z)));
    D _791 = _790 * g_R.Normal.x;
    D _792 = _790 * g_R.Normal.y;
    D _793 = _790 * g_R.Normal.z;
    D _796 = fma(_793, TEXCOORD_11.x, fma(_792, ((TEXCOORD_10.z * TEXCOORD_11.y) - (TEXCOORD_10.y * TEXCOORD_11.z)) * TEXCOORD_11.w, _791 * TEXCOORD_10.x));
    D _799 = fma(_793, TEXCOORD_11.y, fma(_792, ((TEXCOORD_10.x * TEXCOORD_11.z) - (TEXCOORD_10.z * TEXCOORD_11.x)) * TEXCOORD_11.w, _791 * TEXCOORD_10.y));
    D _802 = fma(_793, TEXCOORD_11.z, fma(_792, ((TEXCOORD_10.y * TEXCOORD_11.x) - (TEXCOORD_10.x * TEXCOORD_11.y)) * TEXCOORD_11.w, _791 * TEXCOORD_10.z));
    D _806 = inversesqrt(dot(vec3(_796, _799, _802), vec3(_796, _799, _802)));
    D _807 = _806 * _796;
    D _808 = _806 * _799;
    D _809 = _806 * _802;
    bool _822;
    if (Primitive._m0[27u].w > ((_276.w * 0.99609375) + 0.001953125))
    {
        _822 = ((_279 * 0.99609375) + 0.001953125) < 1.0;
    }
    else
    {
        _822 = false;
    }
    (void)((_822 ? 1.0 : (-1.0)) < 0.0);
    D _828 = spvNClamp(g_R.BaseColor.x, 0.0, 1.0);
    D _829 = spvNClamp(g_R.BaseColor.y, 0.0, 1.0);
    D _830 = spvNClamp(g_R.BaseColor.z, 0.0, 1.0);
    D _831 = spvNClamp(g_R.Metallic, 0.0, 1.0);
    D _832 = spvNClamp(g_R.Roughness, 0.0, 1.0);
    D _833 = spvNClamp(g_R.AO, 0.0, 1.0);
    D _834 = spvNClamp(g_R.Opacity, 0.0, 1.0);
    D _836 = dFdxFine(_807);
    D _837 = dFdxFine(_808);
    D _838 = dFdxFine(_809);
    D _842 = dFdyFine(_807);
    D _843 = dFdyFine(_808);
    D _844 = dFdyFine(_809);
    D _855 = sqrt(spvNClamp(spvNMin((dot(vec3(_842, _843, _844), vec3(_842, _843, _844)) + dot(vec3(_836, _837, _838), vec3(_836, _837, _838))) * 0.15915493667125701904296875, 0.180000007152557373046875) + (_832 * _832), 0.0, 1.0));
    D _856 = 1.0 - _831;
    D _857 = _856 * _828;
    D _858 = _856 * _829;
    D _859 = _856 * _830;
    D _864 = _831 * (_828 + (-0.0203731842339038848876953125));
    D _865 = _831 * (_829 + (-0.0203731842339038848876953125));
    D _866 = _831 * (_830 + (-0.0203731842339038848876953125));
    D _867 = _864 + 0.0203731842339038848876953125;
    D _869 = _865 + 0.0203731842339038848876953125;
    D _870 = _866 + 0.0203731842339038848876953125;
    D _877 = spvNClamp(D(View._m0[220u].x > 1.0), 0.0, 1.0);
    D _905 = ((exp2(log2(spvNMax(0.0, _864 + 0.000373184680938720703125) * 1.020408153533935546875) * 1.39999997615814208984375) - _867) * _877) + _867;
    D _906 = ((exp2(log2(spvNMax(0.0, _865 + 0.000373184680938720703125) * 1.020408153533935546875) * 1.39999997615814208984375) - _869) * _877) + _869;
    D _907 = ((exp2(log2(spvNMax(0.0, _866 + 0.000373184680938720703125) * 1.020408153533935546875) * 1.39999997615814208984375) - _870) * _877) + _870;
    D _912 = (_905 * 0.449999988079071044921875) + _857;
    D _913 = (_906 * 0.449999988079071044921875) + _858;
    D _914 = (_907 * 0.449999988079071044921875) + _859;
    D _921 = dot(vec3(_807, _808, _809), vec3(_255, _257, _258));
    D _927 = (_921 * _807) + _252;
    D _928 = (_921 * _808) + _253;
    D _929 = (_921 * _809) + _254;
    D _933 = abs(_921);
    D _937 = (_927 * 2.0) + (_933 * _807);
    D _938 = (_928 * 2.0) + (_933 * _808);
    D _939 = (_929 * 2.0) + (_933 * _809);
    D _943 = inversesqrt(dot(vec3(_937, _938, _939), vec3(_937, _938, _939)));
    D _944 = _937 * _943;
    D _945 = _938 * _943;
    D _946 = _939 * _943;
    D _947 = _921 * _921;
    D _948 = 1.0 - _947;
    D _957 = sqrt(spvNMax(0.0, 1.0 - (_948 * 0.562781393527984619140625)));
    D _961 = (_927 * 0.750187575817108154296875) - (_957 * _807);
    D _962 = (_928 * 0.750187575817108154296875) - (_957 * _808);
    D _963 = (_929 * 0.750187575817108154296875) - (_957 * _809);
    D _967 = inversesqrt(dot(vec3(_961, _962, _963), vec3(_961, _962, _963)));
    D _968 = _961 * _967;
    D _969 = _962 * _967;
    D _970 = _963 * _967;
    D _974 = _855 * _855;
    D _975 = _974 * _855;
    D _982 = ((((-0.0) - _807) - _968) * _975) + _968;
    D _983 = ((((-0.0) - _808) - _969) * _975) + _969;
    D _984 = ((((-0.0) - _809) - _970) * _975) + _970;
    D _988 = inversesqrt(dot(vec3(_982, _983, _984), vec3(_982, _983, _984)));
    D _989 = _982 * _988;
    D _990 = _983 * _988;
    D _991 = _984 * _988;
    D _992 = spvNMax(9.9999997473787516355514526367188e-06, _933);
    D _999 = View._m0[161u].z * gl_FragCoord.x;
    D _1000 = View._m0[161u].w * gl_FragCoord.y;
    D _1010 = (1.0 / ((-0.0) - View._m0[73u].w)) + View._m0[73u].y;
    D _1012 = spvNMax(0.0, _1010 - _116);
    D _1015 = D(uint(gl_FragCoord.x)) + 0.5;
    D _1016 = D(uint(gl_FragCoord.y)) + 0.5;
    D _1039 = ((View._m0[55u].z + fma(_1016, View._m0[53u].z, View._m0[52u].z * _1015)) / (fma(_1016, View._m0[53u].w, View._m0[52u].w * _1015) + View._m0[55u].w)) - View._m0[78u].z;
    D _1045 = spvNClamp((1.0 / (_1012 + 49.0)) * _1012, 0.0, 1.0) * 50.0;
    D _1049 = fma(_970, View._m0[22u].x, fma(_969, View._m0[21u].x, _968 * View._m0[20u].x));
    D _1052 = fma(_970, View._m0[22u].y, fma(_969, View._m0[21u].y, _968 * View._m0[20u].y));
    D _1055 = fma(_970, View._m0[22u].z, fma(_969, View._m0[21u].z, _968 * View._m0[20u].z));
    D _1059 = inversesqrt(dot(vec3(_1049, _1052, _1055), vec3(_1049, _1052, _1055)));
    D _1060 = spvNMax(10.0, _116);
    D _1082 = (((_1049 * _1045) * _1059) * (1.0 / (View._m0[44u].x * _1060))) * View._m0[74u].x;
    D _1086 = (((_1052 * _1045) * _1059) * (1.0 / (View._m0[45u].y * _1060))) * View._m0[74u].y;
    D _1103 = ((View._m0[161u].x * _999) - View._m0[158u].x) * View._m0[159u].z;
    D _1104 = ((View._m0[161u].y * _1000) - View._m0[158u].y) * View._m0[159u].w;
    D _1107 = spvNMin(View._m0[159u].z, View._m0[159u].w);
    D _1108 = _1107 * View._m0[159u].y;
    D _1109 = _1107 * View._m0[159u].x;
    D _1115 = (12.5 / _1108) * abs(_1082);
    D _1116 = (12.5 / _1109) * abs(_1086);
    D _1137 = (((D(int(uint(_1082 > 0.0) - uint(_1082 < 0.0))) * 0.07999999821186065673828125) * _1108) * _1115) * (1.0 / (_1115 + 1.0));
    D _1141 = (((D(int(uint(_1086 > 0.0) - uint(_1086 < 0.0))) * 0.07999999821186065673828125) * _1109) * _1116) * (1.0 / (_1116 + 1.0));
    D _1150 = spvNClamp(abs((_1103 * 2.0) + (-1.0)), 0.0, 1.0);
    D _1151 = spvNClamp(abs((_1104 * 2.0) + (-1.0)), 0.0, 1.0);
    D _1152 = _1150 * _1150;
    D _1153 = _1151 * _1151;
    D _1161 = (View._m0[158u].x + (-1.0)) + View._m0[159u].x;
    D _1163 = (View._m0[158u].y + (-1.0)) + View._m0[159u].y;
    D _1176 = D(int(uint(int(spvNMin(spvNMax((View._m0[159u].x * ((_1137 + _1103) - ((_1152 * _1152) * _1137))) + View._m0[158u].x, View._m0[158u].x), _1161))))) + 0.5;
    D _1177 = D(int(uint(int(spvNMin(spvNMax((View._m0[159u].y * ((_1141 + _1104) - ((_1153 * _1153) * _1141))) + View._m0[158u].y, View._m0[158u].y), _1163))))) + 0.5;
    D _1190 = D(uint(spvNMin(spvNMax(View._m0[161u].x * (_1176 * View._m0[161u].z), View._m0[158u].x), _1161))) + 0.5;
    D _1191 = D(uint(spvNMin(spvNMax(View._m0[161u].y * (_1177 * View._m0[161u].w), View._m0[158u].y), _1163))) + 0.5;
    D _1203;
    if (_1010 > _116)
    {
        _1203 = spvNClamp(_1012 * 0.0199999995529651641845703125, 0.0, 1.0);
    }
    else
    {
        _1203 = 0.0;
    }
    D _1215 = spvNMin(_1012, _784);
    D _1226 = 1.0 - _855;
    D _1240 = ((spvNMin(_1226 * _1226, exp2(_992 * (-9.27999973297119140625))) * _1226) + (0.0425000004470348358154296875 - (_855 * 0.0274999998509883880615234375))) * 1.03999996185302734375;
    D _1246 = 1.0 - spvNClamp((((_855 * 0.02199999988079071044921875) + (-0.039999999105930328369140625)) + _1240) + (((1.03999996185302734375 - (_855 * 0.572000026702880859375)) - _1240) * 0.0203731842339038848876953125), 0.0, 1.0);
    D _1249 = spvNClamp(_1215 * 0.0199999995529651641845703125, 0.0, 1.0) * g_R.Foam;
    D _1250 = spvNMax(0.001000000047497451305389404296875, _1215);
    D _1253 = log2(spvNMax(0.0, _751));
    D _1255 = exp2(_1253 * _1250);
    D _1259 = log2(spvNMax(0.0, exp2(_773)));
    D _1260 = log2(spvNMax(0.0, exp2(_774)));
    D _1261 = log2(spvNMax(0.0, exp2(_775)));
    D _1265 = exp2(_1259 * _1250);
    D _1266 = exp2(_1260 * _1250);
    D _1267 = exp2(_1261 * _1250);
    D _1268 = spvNMax(0.001000000047497451305389404296875, spvNMin(spvNMax(0.0, (_246 - _1039) - (_1203 * ((((View._m0[55u].z + fma(_1191, View._m0[53u].z, View._m0[52u].z * _1190)) / (fma(_1191, View._m0[53u].w, View._m0[52u].w * _1190) + View._m0[55u].w)) - _1039) - View._m0[78u].z))), _784));
    D _1270 = exp2(_1253 * _1268);
    D _1277 = 1.0 - _834;
    D _1282 = (_1255 * _1246) * (1.0 - ((_1249 * _1277) + _834));
    D _1285 = ((_1282 * _1265) * _1270) * exp2(_1259 * _1268);
    D _1288 = ((_1282 * _1266) * _1270) * exp2(_1260 * _1268);
    D _1291 = ((_1282 * _1267) * _1270) * exp2(_1261 * _1268);
    D _1295 = spvNMax(0.039999999105930328369140625, _855);
    D _1311 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_1295 * _992) + 0.02669160068035125732421875) / (_992 + 0.4664950072765350341796875)) * exp2(((1.0 / _1295) * _992) * log2(_1295)), 0.0, 1.0));
    D _1312 = 1.0 - _992;
    D _1313 = _1312 * _1312;
    D _1326 = _1313 * _1313;
    D _1328 = (_1326 * _1312) * exp2(log2((exp2((_1295 * 4.7702999114990234375) * log2(_992)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _1295);
    D _1331 = (1.0 / _1311) * (1.0 - _1311);
    D _1338 = _1311 - _1328;
    D _1345 = ((_1331 * _905) + 1.0) * ((_1338 * _905) + _1328);
    D _1346 = ((_1331 * _906) + 1.0) * ((_1338 * _906) + _1328);
    D _1347 = ((_1331 * _907) + 1.0) * ((_1338 * _907) + _1328);
    D _1353 = spvNClamp(1.0 - dot(vec3(_1345, _1346, _1347), vec3(0.3333333432674407958984375)), 0.0, 1.0);
    D _1367 = spvNClamp((_833 + (-1.0)) + exp2(log2(_992 + _833) * exp2((-1.0) - (_855 * 16.0))), 0.0, 1.0);
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
    D _1449;
    if (floatBitsToUint(TranslucentBasePass_2._m0[0u]).z == 0u)
    {
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
        _1449 = 0.0;
    }
    else
    {
        D _1965;
        uint _1464;
        bool _1465;
        for (;;)
        {
            _1464 = floatBitsToUint(TranslucentBasePass_2._m0[7u]).z;
            _1465 = _1464 == 0u;
            if (!_1465)
            {
                uint _2130;
                uint _2033 = 0u;
                for (;;)
                {
                    if (_116 < TranslucentBasePass._m0[_2033 + 32u])
                    {
                        _2130 = _2033;
                        break;
                    }
                    else
                    {
                        uint _2034 = _2033 + 1u;
                        if (_2034 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                        {
                            _2033 = _2034;
                            continue;
                        }
                        else
                        {
                            _2130 = _1464;
                            break;
                        }
                    }
                }
                if (_2130 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                {
                    uint _2555 = _2130 << 2u;
                    uint _2556 = _2555 + 9u;
                    uint _2563 = _2555 + 10u;
                    uint _2570 = _2555 + 11u;
                    uint _2577 = _2555 + 12u;
                    uint _2585 = _2130 + 25u;
                    D _2611 = fma(_246, TranslucentBasePass_2._m0[_2570].z, fma(_245, TranslucentBasePass_2._m0[_2563].z, TranslucentBasePass_2._m0[_2556].z * _244)) + TranslucentBasePass_2._m0[_2577].z;
                    D _2615 = fma(_246, TranslucentBasePass_2._m0[_2570].w, fma(_245, TranslucentBasePass_2._m0[_2563].w, TranslucentBasePass_2._m0[_2556].w * _244)) + TranslucentBasePass_2._m0[_2577].w;
                    D _2616 = (fma(_246, TranslucentBasePass_2._m0[_2570].x, fma(_245, TranslucentBasePass_2._m0[_2563].x, TranslucentBasePass_2._m0[_2556].x * _244)) + TranslucentBasePass_2._m0[_2577].x) / _2615;
                    D _2617 = (fma(_246, TranslucentBasePass_2._m0[_2570].y, fma(_245, TranslucentBasePass_2._m0[_2563].y, TranslucentBasePass_2._m0[_2556].y * _244)) + TranslucentBasePass_2._m0[_2577].y) / _2615;
                    bool _2624 = (_2617 <= TranslucentBasePass_2._m0[_2585].w) && ((_2616 <= TranslucentBasePass_2._m0[_2585].z) && ((_2616 >= TranslucentBasePass_2._m0[_2585].x) && (_2617 >= TranslucentBasePass_2._m0[_2585].y)));
                    D _1966;
                    if (_2624)
                    {
                        D _2803 = dFdyFine(_2616);
                        D _2804 = dFdyFine(_2617);
                        D _2805 = dFdyFine(_2611);
                        D _2806 = dFdxFine(_2616);
                        D _2807 = dFdxFine(_2617);
                        D _2808 = dFdxFine(_2611);
                        D _2811 = (_2807 * _2805) - (_2808 * _2804);
                        D _2814 = (_2808 * _2803) - (_2806 * _2805);
                        D _2817 = (_2806 * _2804) - (_2807 * _2803);
                        D _2827 = 1.0 / spvNMax(abs(_2817), sqrt(((_2814 * _2814) + (_2817 * _2817)) + (_2811 * _2811)) * 0.100000001490116119384765625);
                        D _2833 = D(int(uint(_2817 > 0.0) - uint(_2817 < 0.0)));
                        D _2834 = _2811 * TranslucentBasePass_2._m0[29u].z;
                        D _2836 = (_2834 * _2827) * _2833;
                        D _2837 = _2814 * TranslucentBasePass_2._m0[29u].w;
                        D _2839 = (_2837 * _2827) * _2833;
                        D _3312;
                        D _3314;
                        if (dot(vec2(_2811, _2814), vec2(_2811, _2814)) < 1.0000000195414813782625560981111e-24)
                        {
                            _3312 = 0.0;
                            _3314 = 0.0;
                        }
                        else
                        {
                            D _3682 = (-0.0) - _2811;
                            D _3683 = (-0.0) - _2814;
                            D _3687 = inversesqrt(dot(vec2(_3682, _3683), vec2(_3682, _3683)));
                            _3312 = _3687 * _3682;
                            _3314 = _3687 * _3683;
                        }
                        D _3316 = _280 + (-0.5);
                        D _3321 = _279 + 0.5;
                        D _3324 = ((_3314 * _3316) + (_2616 * TranslucentBasePass_2._m0[29u].x)) + (_3312 * _3321);
                        D _3327 = ((_3312 * _3316) + (_2617 * TranslucentBasePass_2._m0[29u].y)) + (_3314 * _3321);
                        D _3328 = _3324 + (-0.5);
                        D _3329 = _3327 + (-0.5);
                        D _3330 = trunc(_3328);
                        D _3331 = trunc(_3329);
                        D _3332 = _3328 - _3330;
                        D _3333 = _3329 - _3331;
                        D _3334 = _3330 * TranslucentBasePass_2._m0[29u].z;
                        D _3335 = _3331 * TranslucentBasePass_2._m0[29u].w;
                        D _3338 = (_3330 + (-0.5)) - _3324;
                        D _3339 = (_3331 + (-0.5)) - _3327;
                        D _3340 = dot(vec2(_3338, _3339), vec2(_2836, _2839));
                        D _3343 = _3340 + _2839;
                        D _3346 = _2833 * (_2827 * (_2837 + _2834));
                        D _3347 = _3346 + _3340;
                        D _3348 = _3340 + _2836;
                        vec4 _3354 = textureGather((sampler2D(ShadowMaps[_2130 + 0u], View_SharedPointClampedSampler)), vec2(_3334, _3335));
                        D _3355 = _3354.x;
                        D _3356 = _3354.y;
                        D _3357 = _3354.z;
                        D _3358 = _3354.w;
                        D _3395 = 1.525902189314365386962890625e-05 - _2611;
                        D _3426 = (_3330 + 1.5) - _3324;
                        D _3427 = dot(vec2(_3426, _3339), vec2(_2836, _2839));
                        D _3430 = _3427 + _2839;
                        D _3431 = _3346 + _3427;
                        D _3432 = _3427 + _2836;
                        vec4 _3434 = textureGatherOffset((sampler2D(ShadowMaps[_2130 + 0u], View_SharedPointClampedSampler)), vec2(_3334, _3335), ivec2(2, 0));
                        D _3435 = _3434.x;
                        D _3436 = _3434.y;
                        D _3437 = _3434.z;
                        D _3438 = _3434.w;
                        D _3504 = (_3331 + 1.5) - _3327;
                        D _3505 = dot(vec2(_3338, _3504), vec2(_2836, _2839));
                        D _3508 = _3505 + _2839;
                        D _3509 = _3346 + _3505;
                        D _3510 = _3505 + _2836;
                        vec4 _3512 = textureGatherOffset((sampler2D(ShadowMaps[_2130 + 0u], View_SharedPointClampedSampler)), vec2(_3334, _3335), ivec2(0, 2));
                        D _3513 = _3512.x;
                        D _3514 = _3512.y;
                        D _3515 = _3512.z;
                        D _3516 = _3512.w;
                        D _3581 = dot(vec2(_3426, _3504), vec2(_2836, _2839));
                        D _3584 = _3581 + _2839;
                        D _3585 = _3346 + _3581;
                        D _3586 = _3581 + _2836;
                        vec4 _3588 = textureGatherOffset((sampler2D(ShadowMaps[_2130 + 0u], View_SharedPointClampedSampler)), vec2(_3334, _3335), ivec2(2));
                        D _3589 = _3588.x;
                        D _3590 = _3588.y;
                        D _3591 = _3588.z;
                        D _3592 = _3588.w;
                        D _3657 = 1.0 - _3332;
                        vec4 _3680 = vec4((((((_3358 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3395 + _3358) + (spvNMin(abs(_3340), 0.0) * D(int(uint(_3340 > 0.0) - uint(_3340 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3657) + ((_3357 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3395 + _3357) + (spvNMin(abs(_3348), 0.0) * D(int(uint(_3348 > 0.0) - uint(_3348 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3438 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3395 + _3438) + (spvNMin(abs(_3427), 0.0) * D(int(uint(_3427 > 0.0) - uint(_3427 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3437 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3395 + _3437) + (spvNMin(abs(_3432), 0.0) * D(int(uint(_3432 > 0.0) - uint(_3432 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3332), (((((_3355 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3395 + _3355) + (spvNMin(abs(_3343), 0.0) * D(int(uint(_3343 > 0.0) - uint(_3343 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3657) + ((_3356 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3395 + _3356) + (spvNMin(abs(_3347), 0.0) * D(int(uint(_3347 > 0.0) - uint(_3347 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3435 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3395 + _3435) + (spvNMin(abs(_3430), 0.0) * D(int(uint(_3430 > 0.0) - uint(_3430 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3436 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3395 + _3436) + (spvNMin(abs(_3431), 0.0) * D(int(uint(_3431 > 0.0) - uint(_3431 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3332), (((((_3516 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3395 + _3516) + (spvNMin(abs(_3505), 0.0) * D(int(uint(_3505 > 0.0) - uint(_3505 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3657) + ((_3515 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3395 + _3515) + (spvNMin(abs(_3510), 0.0) * D(int(uint(_3510 > 0.0) - uint(_3510 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3592 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3395 + _3592) + (spvNMin(abs(_3581), 0.0) * D(int(uint(_3581 > 0.0) - uint(_3581 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3591 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3395 + _3591) + (spvNMin(abs(_3586), 0.0) * D(int(uint(_3586 > 0.0) - uint(_3586 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3332), (((((_3513 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3395 + _3513) + (spvNMin(abs(_3508), 0.0) * D(int(uint(_3508 > 0.0) - uint(_3508 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3657) + ((_3514 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3395 + _3514) + (spvNMin(abs(_3509), 0.0) * D(int(uint(_3509 > 0.0) - uint(_3509 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3589 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3395 + _3589) + (spvNMin(abs(_3584), 0.0) * D(int(uint(_3584 > 0.0) - uint(_3584 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3590 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_3395 + _3590) + (spvNMin(abs(_3585), 0.0) * D(int(uint(_3585 > 0.0) - uint(_3585 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3332));
                        _1966 = dot(_3680, vec4(1.0 - _3333, 1.0, 1.0, _3333)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        _1966 = 1.0;
                    }
                    if (_2624)
                    {
                        _1965 = _1966;
                        break;
                    }
                }
            }
            if (floatBitsToUint(TranslucentBasePass_2._m0[30u]).y == 0u)
            {
                _1965 = 1.0;
                break;
            }
            D _2006 = fma(_246, TranslucentBasePass_2._m0[35u].z, fma(_245, TranslucentBasePass_2._m0[34u].z, TranslucentBasePass_2._m0[33u].z * _244)) + TranslucentBasePass_2._m0[36u].z;
            D _2010 = fma(_246, TranslucentBasePass_2._m0[35u].w, fma(_245, TranslucentBasePass_2._m0[34u].w, TranslucentBasePass_2._m0[33u].w * _244)) + TranslucentBasePass_2._m0[36u].w;
            D _2011 = (fma(_246, TranslucentBasePass_2._m0[35u].x, fma(_245, TranslucentBasePass_2._m0[34u].x, TranslucentBasePass_2._m0[33u].x * _244)) + TranslucentBasePass_2._m0[36u].x) / _2010;
            D _2012 = (fma(_246, TranslucentBasePass_2._m0[35u].y, fma(_245, TranslucentBasePass_2._m0[34u].y, TranslucentBasePass_2._m0[33u].y * _244)) + TranslucentBasePass_2._m0[36u].y) / _2010;
            uvec4 _2016 = floatBitsToUint(TranslucentBasePass_2._m0[32u]);
            uint _2017 = _2016.x;
            uint _2018 = _2016.y;
            uint _2019 = _2016.z;
            uint _2024 = uint(int(floor(_2011)));
            uint _2025 = uint(int((-0.0) - floor(_2012)));
            if (!((int(_2025) < int(_2016.w)) && ((int(_2024) < int(_2019)) && ((int(_2024) >= int(_2017)) && (int(_2025) >= int(_2018))))))
            {
                _1965 = 1.0;
                break;
            }
            D _2093 = dFdyFine(_2011);
            D _2094 = dFdyFine(_2012);
            D _2095 = dFdyFine(_2006);
            D _2096 = dFdxFine(_2011);
            D _2097 = dFdxFine(_2012);
            D _2098 = dFdxFine(_2006);
            D _2101 = (_2097 * _2095) - (_2098 * _2094);
            D _2104 = (_2098 * _2093) - (_2096 * _2095);
            D _2107 = (_2096 * _2094) - (_2097 * _2093);
            D _2118 = 1.0 / spvNMax(abs(_2107), sqrt(((_2104 * _2104) + (_2107 * _2107)) + (_2101 * _2101)) * 0.100000001490116119384765625);
            D _2124 = D(int(uint(_2107 > 0.0) - uint(_2107 < 0.0)));
            D _2482;
            D _2484;
            if (dot(vec2(_2101, _2104), vec2(_2101, _2104)) < 1.0000000195414813782625560981111e-24)
            {
                _2482 = 0.0;
                _2484 = 0.0;
            }
            else
            {
                D _2548 = (-0.0) - _2101;
                D _2549 = (-0.0) - _2104;
                D _2553 = inversesqrt(dot(vec2(_2548, _2549), vec2(_2548, _2549)));
                _2482 = _2553 * _2548;
                _2484 = _2553 * _2549;
            }
            D _2490 = _280 + (-0.5);
            D _2498 = (((_2484 * _2490) + (_2482 * _279)) * 2.0) + (_2482 * 0.5);
            D _2499 = (((_2484 * _279) + (_2482 * _2490)) * 2.0) + (_2484 * 0.5);
            D _2505 = _2498 + (fract(_2011) * 256.0);
            D _2506 = _2499 + (fract(_2012) * 256.0);
            D _2519 = dot(vec2((floor(_2505) + 0.5) - _2505, (floor(_2506) + 0.5) - _2506), vec2(((_2101 * 256.0) * _2118) * _2124, ((_2104 * 256.0) * _2118) * _2124));
            D _2525 = (_2498 * 0.00390625) + _2011;
            D _2526 = (_2499 * 0.00390625) + _2012;
            uint _2538 = ((uint(int((-0.0) - floor(_2526))) - _2018) * (_2019 - _2017)) + (uint(int(floor(_2525))) - _2017);
            D _2776;
            D _2779;
            if ((texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowLoadedTileData, int(_2538 >> 5u)).x & (1u << (_2538 & 31u))) == 0u)
            {
                _2776 = 3.0000000054977557577780399428115e+38;
                _2779 = 0.0;
            }
            else
            {
                uvec4 _2800 = uvec4(texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileIndices, int(_2538)));
                uint _2801 = _2800.x;
                D frontier_phi_51_52_ladder;
                D frontier_phi_51_52_ladder_1;
                if (int(_2801) > int(4294967295u))
                {
                    uint _3298 = (uint(floor(fract(_2525) * 256.0)) + (_2801 << 16u)) + (uint(floor(fract(_2526) * 256.0)) << 8u);
                    uvec4 _3301 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileData, int(_3298 >> 1u));
                    uint _3302 = _3301.x;
                    D _3310 = D((((_3298 & 1u) == 0u) ? _3302 : (_3302 >> 16u)) & 65535u) * 1.525902189314365386962890625e-05;
                    D frontier_phi_51_52_ladder_68_ladder;
                    D frontier_phi_51_52_ladder_68_ladder_1;
                    if (_3310 != 1.0)
                    {
                        vec4 _4069 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthRanges, int(_2801));
                        D _4071 = _4069.y;
                        D _2780 = (1.0 / _4071) * 10.0;
                        frontier_phi_51_52_ladder_68_ladder = _2780;
                        frontier_phi_51_52_ladder_68_ladder_1 = (_4071 * _3310) + _4069.x;
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
                _2776 = frontier_phi_51_52_ladder_1;
                _2779 = frontier_phi_51_52_ladder;
            }
            _1965 = spvNClamp(((((1.525902189314365386962890625e-05 - _2006) + _2776) + (spvNMin(abs(_2519), _2779) * D(int(uint(_2519 > 0.0) - uint(_2519 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0);
            break;
        }
        D _2080;
        if ((floatBitsToUint(Primitive._m0[27u]).z & 2u) == 0u)
        {
            _2080 = 1.0;
        }
        else
        {
            _2080 = View._m0[188u].y;
        }
        uvec4 _2084 = floatBitsToUint(View._m0[220u]);
        uint _2085 = _2084.y;
        uint _2088 = (_2085 != 1u) ? 4294967295u : 0u;
        uint _2480;
        if (_2085 > 1u)
        {
            D _152[4];
            _152[0u] = 0.0;
            _152[1u] = 0.0;
            _152[2u] = 0.0;
            _152[3u] = 0.0;
            uint _2761 = 0u;
            bool _2767;
            for (;;)
            {
                _2767 = _2761 < floatBitsToUint(View._m0[220u]).y;
                if (_2767)
                {
                    uint _3250 = _2761 + 237u;
                    D _3264 = View._m0[_3250].x - View._m0[75u].x;
                    D _3265 = View._m0[_3250].y - View._m0[75u].y;
                    D _3266 = View._m0[_3250].z - View._m0[75u].z;
                    D _3267 = dot(vec3(_3264, _3265, _3266), vec3(_252, _253, _254));
                    D _3274 = dot(vec3(_3264, _3265, _3266), vec3(_3264, _3265, _3266)) - (View._m0[_3250].w * View._m0[_3250].w);
                    D _3276 = (_3267 * _3267) - _3274;
                    D _3830;
                    if ((_3274 < 0.0) && (!(_3276 < 0.0)))
                    {
                        D _3824 = sqrt(_3276);
                        _3830 = spvNMin(abs(_3824 + _3267), abs(_3267 - _3824));
                    }
                    else
                    {
                        _3830 = 0.0;
                    }
                    _152[_2761] = _3830;
                }
                uint _2762 = _2761 + 1u;
                if (_2762 == 4u)
                {
                    break;
                }
                else
                {
                    _2761 = _2762;
                    continue;
                }
            }
            D _3841 = (_279 * 0.99989998340606689453125) * dot(vec4(_152[0u], _152[1u], _152[2u], _152[3u]), vec4(1.0));
            uint frontier_phi_36_76_ladder;
            if (_152[0u] > _3841)
            {
                frontier_phi_36_76_ladder = 0u;
            }
            else
            {
                D _4129 = _152[1u] + _152[0u];
                uint frontier_phi_36_76_ladder_83_ladder;
                if (_4129 > _3841)
                {
                    frontier_phi_36_76_ladder_83_ladder = 1u;
                }
                else
                {
                    D _4140 = _4129 + _152[2u];
                    uint frontier_phi_36_76_ladder_83_ladder_86_ladder;
                    if (_4140 > _3841)
                    {
                        frontier_phi_36_76_ladder_83_ladder_86_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_36_76_ladder_83_ladder_86_ladder_89_ladder;
                        if ((_4140 + _152[3u]) > _3841)
                        {
                            frontier_phi_36_76_ladder_83_ladder_86_ladder_89_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_36_76_ladder_83_ladder_86_ladder_89_ladder = _2088;
                        }
                        frontier_phi_36_76_ladder_83_ladder_86_ladder = frontier_phi_36_76_ladder_83_ladder_86_ladder_89_ladder;
                    }
                    frontier_phi_36_76_ladder_83_ladder = frontier_phi_36_76_ladder_83_ladder_86_ladder;
                }
                frontier_phi_36_76_ladder = frontier_phi_36_76_ladder_83_ladder;
            }
            _2480 = frontier_phi_36_76_ladder;
        }
        else
        {
            _2480 = _2088;
        }
        D _2768;
        if (_2480 == 4294967295u)
        {
            _2768 = _2080;
        }
        else
        {
            _2768 = View._m0[_2480 + 241u].x * _2080;
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
        if (_2768 > 0.0)
        {
            D _3283 = spvNClamp((TranslucentBasePass_2._m0[7u].x * _116) + TranslucentBasePass_2._m0[7u].y, 0.0, 1.0);
            D _3287 = ((_3283 * _3283) * (1.0 - _1965)) + _1965;
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
            if (_3287 > 0.0)
            {
                D _3843 = dot(vec3(_807, _808, _809), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3846 = spvNMax(0.0, _3843);
                D _3847 = dot(vec3(_255, _257, _258), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3853 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3847 * 2.0) + 2.0));
                D _3856 = spvNClamp(_3853 * (_921 + _3843), 0.0, 1.0);
                D _3869 = sqrt(spvNMax(0.0, 1.0 - (_948 * 0.444444477558135986328125)));
                D _3873 = (_927 * 0.666666686534881591796875) - (_3869 * _807);
                D _3874 = (_928 * 0.666666686534881591796875) - (_3869 * _808);
                D _3875 = (_929 * 0.666666686534881591796875) - (_3869 * _809);
                D _3879 = inversesqrt(dot(vec3(_3873, _3874, _3875), vec3(_3873, _3874, _3875)));
                D _3886 = dot(vec3((-0.0) - (_3879 * _3873), (-0.0) - (_3879 * _3874), (-0.0) - (_3879 * _3875)), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3889 = _1295 * _1295;
                D _3890 = _3889 * _3889;
                D _3894 = ((_3856 * _3856) * (_3890 + (-1.0))) + 1.0;
                D _3900 = (_3846 * 2.0) * _992;
                D _3905 = 1.0 - spvNMax(9.9999997473787516355514526367188e-06, spvNMin(_3853 * (_3847 + 1.0), 1.0));
                D _3906 = _3905 * _3905;
                D _3908 = (_3906 * _3906) * _3905;
                D _3913 = spvNMin(dot(vec3(_905, _906, _907), vec3(16.666667938232421875)), 1.0);
                D _3926 = spvNMax(0.039999999105930328369140625, _1295);
                D _3939 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_3926 * _3846) + 0.02669160068035125732421875) / (_3846 + 0.4664950072765350341796875)) * exp2(((1.0 / _3926) * _3846) * log2(_3926)), 0.0, 1.0));
                D _3940 = 1.0 - _3846;
                D _3941 = _3940 * _3940;
                D _3953 = ((_3941 * _3941) * _3940) * exp2(log2((exp2((_3926 * 4.7702999114990234375) * log2(_3846)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _3926);
                D _3956 = (1.0 / _3939) * (1.0 - _3939);
                D _3960 = (_3956 * _905) + 1.0;
                D _3961 = (_3956 * _906) + 1.0;
                D _3962 = (_3956 * _907) + 1.0;
                D _3963 = _3939 - _3953;
                D _3977 = spvNClamp(1.0 - dot(vec3(_3960 * ((_3963 * _905) + _3953), _3961 * ((_3963 * _906) + _3953), _3962 * ((_3963 * _907) + _3953)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                D _3980 = (((_3890 * 0.3183098733425140380859375) * _3846) * (1.0 / (_3894 * _3894))) * (0.5 / ((_3889 * ((_992 + _3846) - _3900)) + _3900));
                D _3981 = _3846 * 0.3183098733425140380859375;
                D _3995 = (((_3886 * _3886) + 1.0) * 0.0323704965412616729736328125) * exp2(log2(spvNMax(0.0, (_3886 * 1.2000000476837158203125) + 1.36000001430511474609375)) * (-1.5));
                D _3998 = ((_3847 * _3847) + 1.0) * 0.05968309938907623291015625;
                D _4000 = spvNMin(1.0, _833);
                D _4002 = (_833 + 1.0) - _4000;
                D _4003 = _4002 * _4002;
                D _4006 = 1.0 - ((_4003 * _4003) * _4002);
                D _4007 = _4006 * _4006;
                D _4012 = ((_4007 * _4007) * (_4006 * (_833 - _4000))) + _4000;
                D _4015 = sqrt(spvNMax(0.0, 1.0 - _4012));
                D _4020 = 1.0 - spvNClamp((_1295 * 3.5) + (-0.5), 0.0, 1.0);
                D _4021 = _4020 * _4020;
                D _4031 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_1326 * _4015) * spvNClamp(1.0 - ((_4021 * _4021) * _4020), 0.0, 1.0))) * _3846, 0.0, 1.0);
                D _4036 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _4015)) * _3846, 0.0, 1.0);
                D _4038 = spvNMin(_3287, _4031 * _4031);
                D _4039 = spvNMin(_3287, _4036 * _4036);
                D _4040 = spvNMin(_3287, _4012);
                D _4041 = _2768 * TranslucentBasePass_2._m0[4u].x;
                D _4042 = _2768 * TranslucentBasePass_2._m0[4u].y;
                D _4043 = _2768 * TranslucentBasePass_2._m0[4u].z;
                frontier_phi_7_49_ladder_67_ladder = (((_4043 * _859) * _3981) * _3977) * _4039;
                frontier_phi_7_49_ladder_67_ladder_1 = (_3998 * _4041) * _4040;
                frontier_phi_7_49_ladder_67_ladder_2 = (_3998 * _4042) * _4040;
                frontier_phi_7_49_ladder_67_ladder_3 = (_3998 * _4043) * _4040;
                frontier_phi_7_49_ladder_67_ladder_4 = (_3995 * _4041) * _4040;
                frontier_phi_7_49_ladder_67_ladder_5 = (_3995 * _4042) * _4040;
                frontier_phi_7_49_ladder_67_ladder_6 = (_3995 * _4043) * _4040;
                frontier_phi_7_49_ladder_67_ladder_7 = (((_3980 * _4041) * spvNClamp(((_3913 - _905) * _3908) + _905, 0.0, 1.0)) * _3960) * _4038;
                frontier_phi_7_49_ladder_67_ladder_8 = (((_3980 * _4042) * spvNClamp(((_3913 - _906) * _3908) + _906, 0.0, 1.0)) * _3961) * _4038;
                frontier_phi_7_49_ladder_67_ladder_9 = (((_3980 * _4043) * spvNClamp(((_3913 - _907) * _3908) + _907, 0.0, 1.0)) * _3962) * _4038;
                frontier_phi_7_49_ladder_67_ladder_10 = (((_4041 * _857) * _3981) * _3977) * _4039;
                frontier_phi_7_49_ladder_67_ladder_11 = (((_4042 * _858) * _3981) * _3977) * _4039;
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
        _1427 = frontier_phi_7_49_ladder_1;
        _1429 = frontier_phi_7_49_ladder_2;
        _1431 = frontier_phi_7_49_ladder_3;
        _1433 = frontier_phi_7_49_ladder_4;
        _1435 = frontier_phi_7_49_ladder_5;
        _1437 = frontier_phi_7_49_ladder_6;
        _1439 = frontier_phi_7_49_ladder_7;
        _1441 = frontier_phi_7_49_ladder_8;
        _1443 = frontier_phi_7_49_ladder_9;
        _1445 = frontier_phi_7_49_ladder_10;
        _1447 = frontier_phi_7_49_ladder_11;
        _1449 = frontier_phi_7_49_ladder;
    }
    uvec4 _1453 = floatBitsToUint(TranslucentBasePass_2._m0[0u]);
    uint _1454 = _1453.x;
    uint _1459 = min(min(texelFetch(TranslucentBasePass_Shared_Forward_NumCulledLightsGrid, int(0u)).x, _1454), _1454);
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
    D _1500;
    if (_1459 == 0u)
    {
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
        _1488 = _1449;
        _1490 = 0.0;
        _1492 = 0.0;
        _1494 = 0.0;
        _1496 = 0.0;
        _1498 = 0.0;
        _1500 = 0.0;
    }
    else
    {
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
        D _1501;
        D _1877 = _1427;
        D _1878 = _1429;
        D _1879 = _1431;
        D _1880 = _1433;
        D _1881 = _1435;
        D _1882 = _1437;
        D _1883 = _1439;
        D _1884 = _1441;
        D _1885 = _1443;
        D _1886 = _1445;
        D _1887 = _1447;
        D _1888 = _1449;
        D _1889 = 0.0;
        D _1890 = 0.0;
        D _1891 = 0.0;
        D _1892 = 0.0;
        D _1893 = 0.0;
        D _1894 = 0.0;
        uint _1895 = 0u;
        D _1899;
        D _1900;
        D _1901;
        D _1902;
        D _1904;
        D _1905;
        D _1906;
        D _1908;
        D _1909;
        D _1910;
        uint _1912;
        D _1914;
        D _1915;
        D _1917;
        D _1918;
        D _1919;
        D _1921;
        D _1922;
        uint _1924;
        D _1927;
        D _1928;
        D _1929;
        D _1930;
        uint _1933;
        D _1935;
        D _1936;
        D _1937;
        D _1938;
        D _1941;
        D _1942;
        D _1943;
        D _1944;
        D _1947;
        D _1948;
        D _1949;
        D _1950;
        D _1953;
        D _1954;
        D _1955;
        D _1956;
        bool _1959;
        bool _1960;
        bool _1964;
        for (;;)
        {
            vec4 _1898 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(0u));
            _1899 = _1898.x;
            _1900 = _1898.y;
            _1901 = _1898.z;
            _1902 = _1898.w;
            vec4 _1903 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(1u));
            _1904 = _1903.x;
            _1905 = _1903.y;
            _1906 = _1903.z;
            vec4 _1907 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(2u));
            _1908 = _1907.x;
            _1909 = _1907.y;
            _1910 = _1907.z;
            _1912 = floatBitsToUint(_1907.w);
            vec4 _1913 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(3u));
            _1914 = _1913.x;
            _1915 = _1913.y;
            vec4 _1916 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(4u));
            _1917 = _1916.x;
            _1918 = _1916.y;
            _1919 = _1916.z;
            vec4 _1920 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(5u));
            _1921 = _1920.x;
            _1922 = _1920.y;
            _1924 = floatBitsToUint(_1920.z);
            vec4 _1926 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(6u));
            _1927 = _1926.x;
            _1928 = _1926.y;
            _1929 = _1926.z;
            _1930 = _1926.w;
            _1933 = floatBitsToUint(texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(7u)).x);
            vec4 _1934 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(8u));
            _1935 = _1934.x;
            _1936 = _1934.y;
            _1937 = _1934.z;
            _1938 = _1934.w;
            vec4 _1940 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(9u));
            _1941 = _1940.x;
            _1942 = _1940.y;
            _1943 = _1940.z;
            _1944 = _1940.w;
            vec4 _1946 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(10u));
            _1947 = _1946.x;
            _1948 = _1946.y;
            _1949 = _1946.z;
            _1950 = _1946.w;
            vec4 _1952 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(11u));
            _1953 = _1952.x;
            _1954 = _1952.y;
            _1955 = _1952.z;
            _1956 = _1952.w;
            _1959 = (_1912 & 131072u) != 0u;
            _1960 = _1914 > (-2.0);
            _1964 = (_1912 & 16384u) == 0u;
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
            if (_1964)
            {
                D _2433;
                if (_1959)
                {
                    uint _2398 = _1933 + 0u;
                    uvec2 _2401 = uvec2(textureSize(ShadowMaps[(_2398)], int(0u)));
                    D _2403 = D(int(_2401.x));
                    D _2405 = D(int(_2401.y));
                    D _2406 = 1.0 / _2403;
                    D _2407 = 1.0 / _2405;
                    D _2419 = fma(_246, _1949, fma(_245, _1943, _1937 * _244)) + _1955;
                    D _2423 = fma(_246, _1950, fma(_245, _1944, _1938 * _244)) + _1956;
                    D _2424 = (fma(_246, _1947, fma(_245, _1941, _1935 * _244)) + _1953) / _2423;
                    D _2425 = (fma(_246, _1948, fma(_245, _1942, _1936 * _244)) + _1954) / _2423;
                    D frontier_phi_32_31_ladder;
                    if ((_2425 <= _1930) && ((_2424 <= _1929) && ((_2424 >= _1927) && (_2425 >= _1928))))
                    {
                        D _2642 = dFdyFine(_2424);
                        D _2643 = dFdyFine(_2425);
                        D _2644 = dFdyFine(_2419);
                        D _2645 = dFdxFine(_2424);
                        D _2646 = dFdxFine(_2425);
                        D _2647 = dFdxFine(_2419);
                        D _2650 = (_2646 * _2644) - (_2647 * _2643);
                        D _2653 = (_2647 * _2642) - (_2645 * _2644);
                        D _2656 = (_2645 * _2643) - (_2646 * _2642);
                        D _2666 = 1.0 / spvNMax(abs(_2656), sqrt(((_2653 * _2653) + (_2656 * _2656)) + (_2650 * _2650)) * 0.100000001490116119384765625);
                        D _2672 = D(int(uint(_2656 > 0.0) - uint(_2656 < 0.0)));
                        D _2673 = _2650 * _2406;
                        D _2675 = (_2673 * _2666) * _2672;
                        D _2676 = _2653 * _2407;
                        D _2678 = (_2676 * _2666) * _2672;
                        D _2845;
                        D _2847;
                        if (dot(vec2(_2650, _2653), vec2(_2650, _2653)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2845 = 0.0;
                            _2847 = 0.0;
                        }
                        else
                        {
                            D _3188 = (-0.0) - _2650;
                            D _3189 = (-0.0) - _2653;
                            D _3193 = inversesqrt(dot(vec2(_3188, _3189), vec2(_3188, _3189)));
                            _2845 = _3193 * _3188;
                            _2847 = _3193 * _3189;
                        }
                        D _2849 = _280 + (-0.5);
                        D _2854 = _279 + 0.5;
                        D _2857 = ((_2847 * _2849) + (_2424 * _2403)) + (_2845 * _2854);
                        D _2860 = ((_2845 * _2849) + (_2425 * _2405)) + (_2847 * _2854);
                        D _2861 = _2857 + (-0.5);
                        D _2862 = _2860 + (-0.5);
                        D _2863 = trunc(_2861);
                        D _2864 = trunc(_2862);
                        D _2865 = _2861 - _2863;
                        D _2866 = _2862 - _2864;
                        D _2867 = _2863 * _2406;
                        D _2868 = _2864 * _2407;
                        D _2871 = (_2863 + (-0.5)) - _2857;
                        D _2872 = (_2864 + (-0.5)) - _2860;
                        D _2873 = dot(vec2(_2871, _2872), vec2(_2675, _2678));
                        D _2876 = _2873 + _2678;
                        D _2879 = _2672 * (_2666 * (_2676 + _2673));
                        D _2880 = _2879 + _2873;
                        D _2881 = _2873 + _2675;
                        vec4 _2885 = textureGather((sampler2D(ShadowMaps[_2398], View_SharedPointClampedSampler)), vec2(_2867, _2868));
                        D _2926 = 1.525902189314365386962890625e-05 - _2419;
                        D _2949 = (_2863 + 1.5) - _2857;
                        D _2950 = dot(vec2(_2949, _2872), vec2(_2675, _2678));
                        D _2953 = _2950 + _2678;
                        D _2954 = _2879 + _2950;
                        D _2955 = _2950 + _2675;
                        vec4 _2959 = textureGatherOffset((sampler2D(ShadowMaps[_2398], View_SharedPointClampedSampler)), vec2(_2867, _2868), ivec2(2, 0));
                        D _3023 = (_2864 + 1.5) - _2860;
                        D _3024 = dot(vec2(_2871, _3023), vec2(_2675, _2678));
                        D _3027 = _3024 + _2678;
                        D _3028 = _2879 + _3024;
                        D _3029 = _3024 + _2675;
                        vec4 _3031 = textureGatherOffset((sampler2D(ShadowMaps[_2398], View_SharedPointClampedSampler)), vec2(_2867, _2868), ivec2(0, 2));
                        D _3093 = dot(vec2(_2949, _3023), vec2(_2675, _2678));
                        D _3096 = _3093 + _2678;
                        D _3097 = _2879 + _3093;
                        D _3098 = _3093 + _2675;
                        vec4 _3100 = textureGatherOffset((sampler2D(ShadowMaps[_2398], View_SharedPointClampedSampler)), vec2(_2867, _2868), ivec2(2));
                        D _3162 = 1.0 - _2865;
                        vec4 _3185 = vec4((((spvNClamp((((_2926 + _2885.w) + (spvNMin(abs(_2873), 0.0) * D(int(uint(_2873 > 0.0) - uint(_2873 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _3162) + spvNClamp((((_2926 + _2885.z) + (spvNMin(abs(_2881), 0.0) * D(int(uint(_2881 > 0.0) - uint(_2881 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2926 + _2959.w) + (spvNMin(abs(_2950), 0.0) * D(int(uint(_2950 > 0.0) - uint(_2950 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2926 + _2959.z) + (spvNMin(abs(_2955), 0.0) * D(int(uint(_2955 > 0.0) - uint(_2955 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2865), (((spvNClamp((((_2926 + _2885.x) + (spvNMin(abs(_2876), 0.0) * D(int(uint(_2876 > 0.0) - uint(_2876 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _3162) + spvNClamp((((_2926 + _2885.y) + (spvNMin(abs(_2880), 0.0) * D(int(uint(_2880 > 0.0) - uint(_2880 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2926 + _2959.x) + (spvNMin(abs(_2953), 0.0) * D(int(uint(_2953 > 0.0) - uint(_2953 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2926 + _2959.y) + (spvNMin(abs(_2954), 0.0) * D(int(uint(_2954 > 0.0) - uint(_2954 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2865), (((spvNClamp((((_2926 + _3031.w) + (spvNMin(abs(_3024), 0.0) * D(int(uint(_3024 > 0.0) - uint(_3024 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _3162) + spvNClamp((((_2926 + _3031.z) + (spvNMin(abs(_3029), 0.0) * D(int(uint(_3029 > 0.0) - uint(_3029 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2926 + _3100.w) + (spvNMin(abs(_3093), 0.0) * D(int(uint(_3093 > 0.0) - uint(_3093 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2926 + _3100.z) + (spvNMin(abs(_3098), 0.0) * D(int(uint(_3098 > 0.0) - uint(_3098 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2865), (((spvNClamp((((_2926 + _3031.x) + (spvNMin(abs(_3027), 0.0) * D(int(uint(_3027 > 0.0) - uint(_3027 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _3162) + spvNClamp((((_2926 + _3031.y) + (spvNMin(abs(_3028), 0.0) * D(int(uint(_3028 > 0.0) - uint(_3028 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2926 + _3100.x) + (spvNMin(abs(_3096), 0.0) * D(int(uint(_3096 > 0.0) - uint(_3096 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2926 + _3100.y) + (spvNMin(abs(_3097), 0.0) * D(int(uint(_3097 > 0.0) - uint(_3097 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2865));
                        frontier_phi_32_31_ladder = dot(_3185, vec4(1.0 - _2866, 1.0, 1.0, _2866)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        frontier_phi_32_31_ladder = 1.0;
                    }
                    _2433 = frontier_phi_32_31_ladder;
                }
                else
                {
                    _2433 = 1.0;
                }
                D _2439 = _1899 - _244;
                D _2440 = _1900 - _245;
                D _2441 = _1901 - _246;
                D _2442 = dot(vec3(_2439, _2440, _2441), vec3(_2439, _2440, _2441));
                D _2687;
                D _2688;
                D _2689;
                if (_2442 > 9.9999997473787516355514526367188e-05)
                {
                    D _2683 = inversesqrt(_2442);
                    _2687 = _2683 * _2439;
                    _2688 = _2683 * _2440;
                    _2689 = _2683 * _2441;
                }
                else
                {
                    _2687 = 0.0;
                    _2688 = 0.0;
                    _2689 = 0.0;
                }
                D _2690 = _1921 * _1921;
                D _2694 = (_1902 * _1902) * _2442;
                D _2697 = spvNClamp(1.0 - (_2694 * _2694), 0.0, 1.0);
                D _3201;
                if (_1960)
                {
                    D _3199 = spvNClamp((dot(vec3(_2687, _2688, _2689), vec3(_1908, _1909, _1910)) - _1914) * _1915, 0.0, 1.0);
                    _3201 = _3199 * _3199;
                }
                else
                {
                    _3201 = 1.0;
                }
                D _3202 = ((_2697 * _2697) * D(_2442 >= _2690)) * _3201;
                D _3688;
                D _3690;
                D _3692;
                if ((_1912 & 262144u) == 0u)
                {
                    _3688 = 1.0;
                    _3690 = 1.0;
                    _3692 = 1.0;
                }
                else
                {
                    D _3695 = (-0.0) - _1909;
                    D _3696 = (-0.0) - _1910;
                    D _3697 = (-0.0) - _1908;
                    D _3707 = (-0.0) - _2687;
                    D _3708 = (-0.0) - _2688;
                    D _3709 = (-0.0) - _2689;
                    D _3712 = fma(_3696, _3709, fma(_3695, _3708, _2687 * _1908));
                    D _3715 = fma(_1919, _3709, fma(_1918, _3708, _1917 * _3707));
                    D _3723 = atan(((-0.0) - _3715) / ((-0.0) - _3712));
                    bool _3728 = _3712 > (-0.0);
                    bool _3729 = _3712 == (-0.0);
                    bool _3730 = _3715 <= (-0.0);
                    bool _3731 = _3715 > (-0.0);
                    vec4 _3753 = texture((sampler2D(ForwardLightProfileTextures[_1924 + 0u], View_SharedBilinearWrappedSampler)), vec2(fract((_3729 && _3730) ? 1.25 : ((_3729 && _3731) ? 0.75 : ((((_3728 && _3731) ? (_3723 + (-3.1415927410125732421875)) : ((_3728 && _3730) ? (_3723 + 3.1415927410125732421875) : _3723)) * 0.15915493667125701904296875) + 1.0))), (asin((-0.0) - fma((_1918 * _3697) - (_1917 * _3695), _3709, fma((_1917 * _3696) - (_1919 * _3697), _3708, ((_1919 * _3695) - (_1918 * _3696)) * _3707))) * 0.3183098733425140380859375) + 0.5));
                    _3688 = _3753.x;
                    _3690 = _3753.y;
                    _3692 = _3753.z;
                }
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
                D _4096;
                for (;;)
                {
                    if (_3202 > 0.0)
                    {
                        D _4132;
                        if (_1959)
                        {
                            if (!(_2433 > 0.0))
                            {
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
                                _4096 = 0.0;
                                break;
                            }
                            _4132 = _2433;
                        }
                        else
                        {
                            _4132 = 1.0;
                        }
                        D _4134 = spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _2442));
                        D _4135 = 1.0 / _4134;
                        D _4136 = dot(vec3(_807, _808, _809), vec3(_2687, _2688, _2689));
                        D _4147;
                        if (_1921 > 0.0)
                        {
                            D _4144 = sqrt(spvNClamp(_2690 * _4135, 0.0, 1.0));
                            D frontier_phi_88_87_ladder;
                            if (_4144 > spvNMax(9.9999997473787516355514526367188e-06, _4136))
                            {
                                D _4164 = spvNMax((-0.0) - _4144, _4136) + _4144;
                                frontier_phi_88_87_ladder = (_4164 * _4164) * (0.25 / _4144);
                            }
                            else
                            {
                                frontier_phi_88_87_ladder = _4136;
                            }
                            _4147 = frontier_phi_88_87_ladder;
                        }
                        else
                        {
                            _4147 = _4136;
                        }
                        D _4204;
                        D _4205;
                        D _4206;
                        D _4149;
                        D _4151;
                        D _4155;
                        D _4156;
                        bool _4159;
                        for (;;)
                        {
                            _4149 = spvNMax(0.0, _4147);
                            _4151 = _1295 * _1295;
                            _4155 = spvNClamp(((1.0 - _4151) * _1921) * inversesqrt(_4134), 0.0, 1.0);
                            _4156 = dot(vec3(_255, _257, _258), vec3(_2687, _2688, _2689));
                            _4159 = _4155 > 0.0;
                            D _4175;
                            D _4177;
                            if (_4159)
                            {
                                D _4170 = sqrt(spvNMax(0.0, 1.0 - (_4155 * _4155)));
                                D _4173 = ((_4136 * 2.0) * _921) - _4156;
                                if (!(!(_4173 >= _4170)))
                                {
                                    _4204 = _933;
                                    _4205 = 1.0;
                                    _4206 = _4156;
                                    break;
                                }
                                D _4193 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, 1.0 - (_4173 * _4173))) * _4155;
                                _4175 = (_4193 * (((_947 * 2.0) + (-1.0)) - (_4173 * _4156))) + (_4170 * _4156);
                                _4177 = (_4193 * (_921 - (_4173 * _4136))) + (_4170 * _4136);
                            }
                            else
                            {
                                _4175 = _4156;
                                _4177 = _4136;
                            }
                            D _4182 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_4175 * 2.0) + 2.0));
                            _4204 = spvNMin(_4182 * (_4175 + 1.0), 1.0);
                            _4205 = spvNClamp(_4182 * (_4177 + _921), 0.0, 1.0);
                            _4206 = _4175;
                            break;
                        }
                        D _4207 = spvNMax(9.9999997473787516355514526367188e-06, _4204);
                        D _4214 = sqrt(spvNMax(0.0, 1.0 - (_948 * 0.444444477558135986328125)));
                        D _4218 = (_927 * 0.666666686534881591796875) - (_4214 * _807);
                        D _4219 = (_928 * 0.666666686534881591796875) - (_4214 * _808);
                        D _4220 = (_929 * 0.666666686534881591796875) - (_4214 * _809);
                        D _4224 = inversesqrt(dot(vec3(_4218, _4219, _4220), vec3(_4218, _4219, _4220)));
                        D _4231 = dot(vec3((-0.0) - (_4224 * _4218), (-0.0) - (_4224 * _4219), (-0.0) - (_4224 * _4220)), vec3(_2687, _2688, _2689));
                        D _4234 = _4151 * _4151;
                        D _4248 = ((_4205 * _4205) * (_4234 + (-1.0))) + 1.0;
                        D _4254 = (_4149 * 2.0) * _992;
                        D _4259 = 1.0 - _4207;
                        D _4260 = _4259 * _4259;
                        D _4262 = (_4260 * _4260) * _4259;
                        D _4266 = spvNMin(dot(vec3(_905, _906, _907), vec3(16.666667938232421875)), 1.0);
                        D _4279 = spvNMax(0.039999999105930328369140625, _1295);
                        D _4292 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_4279 * _4149) + 0.02669160068035125732421875) / (_4149 + 0.4664950072765350341796875)) * exp2(((1.0 / _4279) * _4149) * log2(_4279)), 0.0, 1.0));
                        D _4293 = 1.0 - _4149;
                        D _4294 = _4293 * _4293;
                        D _4306 = ((_4294 * _4294) * _4293) * exp2(log2((exp2((_4279 * 4.7702999114990234375) * log2(_4149)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _4279);
                        D _4309 = (1.0 / _4292) * (1.0 - _4292);
                        D _4313 = (_4309 * _905) + 1.0;
                        D _4314 = (_4309 * _906) + 1.0;
                        D _4315 = (_4309 * _907) + 1.0;
                        D _4316 = _4292 - _4306;
                        D _4330 = spvNClamp(1.0 - dot(vec3(_4313 * ((_4316 * _905) + _4306), _4314 * ((_4316 * _906) + _4306), _4315 * ((_4316 * _907) + _4306)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                        D _4334 = ((((_4234 * 0.3183098733425140380859375) * _4149) * (1.0 / (_4248 * _4248))) * (_4159 ? ((1.0 / ((((_4155 * 0.25) * (_4155 + (_4151 * 3.0))) * (1.0 / _4207)) + _4234)) * _4234) : 1.0)) * (0.5 / ((_4151 * ((_992 + _4149) - _4254)) + _4254));
                        D _4335 = _4149 * 0.3183098733425140380859375;
                        D _4345 = (((_4231 * _4231) + 1.0) * 0.0323704965412616729736328125) * exp2(log2(spvNMax(0.0, (_4231 * 1.2000000476837158203125) + 1.36000001430511474609375)) * (-1.5));
                        D _4348 = ((_4206 * _4206) + 1.0) * 0.05968309938907623291015625;
                        D _4349 = spvNMin(1.0, _833);
                        D _4351 = (_833 + 1.0) - _4349;
                        D _4352 = _4351 * _4351;
                        D _4355 = 1.0 - ((_4352 * _4352) * _4351);
                        D _4356 = _4355 * _4355;
                        D _4361 = ((_4356 * _4356) * (_4355 * (_833 - _4349))) + _4349;
                        D _4364 = sqrt(spvNMax(0.0, 1.0 - _4361));
                        D _4368 = 1.0 - spvNClamp((_1295 * 3.5) + (-0.5), 0.0, 1.0);
                        D _4369 = _4368 * _4368;
                        D _4379 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_1326 * _4364) * spvNClamp(1.0 - ((_4369 * _4369) * _4368), 0.0, 1.0))) * _4149, 0.0, 1.0);
                        D _4384 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _4364)) * _4149, 0.0, 1.0);
                        D _4386 = spvNMin(_4132, _4379 * _4379);
                        D _4387 = spvNMin(_4132, _4384 * _4384);
                        D _4388 = spvNMin(_4132, _4361);
                        D _4392 = (_3202 * _1904) * _3688;
                        D _4393 = (_3202 * _1905) * _3690;
                        D _4394 = (_3202 * _1906) * _3692;
                        D _4395 = _4135 * _4392;
                        D _4399 = _4135 * _4393;
                        D _4403 = _4135 * _4394;
                        _4074 = (_4395 * _4348) * _4388;
                        _4076 = (_4399 * _4348) * _4388;
                        _4078 = (_4403 * _4348) * _4388;
                        _4080 = (_4395 * _4345) * _4388;
                        _4082 = (_4399 * _4345) * _4388;
                        _4084 = (_4403 * _4345) * _4388;
                        _4086 = (((_4395 * spvNClamp(((_4266 - _905) * _4262) + _905, 0.0, 1.0)) * _4334) * _4313) * _4386;
                        _4088 = (((_4399 * _4334) * spvNClamp(((_4266 - _906) * _4262) + _906, 0.0, 1.0)) * _4314) * _4386;
                        _4090 = (((_4403 * _4334) * spvNClamp(((_4266 - _907) * _4262) + _907, 0.0, 1.0)) * _4315) * _4386;
                        _4092 = ((((_4392 * _857) * _4135) * _4335) * _4330) * _4387;
                        _4094 = ((((_4393 * _858) * _4135) * _4335) * _4330) * _4387;
                        _4096 = ((((_4394 * _859) * _4135) * _4335) * _4330) * _4387;
                        break;
                    }
                    else
                    {
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
                        _4096 = 0.0;
                        break;
                    }
                }
                frontier_phi_47_pred = _4088 + _1884;
                frontier_phi_47_pred_1 = _4074 + _1877;
                frontier_phi_47_pred_2 = _4076 + _1878;
                frontier_phi_47_pred_3 = _4078 + _1879;
                frontier_phi_47_pred_4 = _4080 + _1880;
                frontier_phi_47_pred_5 = _4082 + _1881;
                frontier_phi_47_pred_6 = _4084 + _1882;
                frontier_phi_47_pred_7 = _4086 + _1883;
                frontier_phi_47_pred_8 = _4090 + _1885;
                frontier_phi_47_pred_9 = _4094 + _1887;
                frontier_phi_47_pred_10 = _4092 + _1886;
                frontier_phi_47_pred_11 = _1894;
                frontier_phi_47_pred_12 = _1893;
                frontier_phi_47_pred_13 = _1892;
                frontier_phi_47_pred_14 = _1891;
                frontier_phi_47_pred_15 = _1890;
                frontier_phi_47_pred_16 = _1889;
                frontier_phi_47_pred_17 = _4096 + _1888;
            }
            else
            {
                D _2063 = _1899 - _244;
                D _2064 = _1900 - _245;
                D _2065 = _1901 - _246;
                D _2066 = dot(vec3(_2063, _2064, _2065), vec3(_2063, _2064, _2065));
                D _2070 = (_1902 * _1902) * _2066;
                D _2071 = _2070 * _2070;
                D _2072 = _2071 * _2071;
                D _2075 = spvNClamp(1.0 - (_2072 * _2072), 0.0, 1.0);
                D _2076 = _2075 * _2075;
                D _2077 = _2076 * _2076;
                D _2078 = _2077 * _2077;
                D _2457;
                D _2459;
                D _2461;
                D _2463;
                D _2465;
                D _2467;
                if (_2078 > 0.0)
                {
                    D _2449 = dot(vec3(_252, _253, _254), vec3(_807, _808, _809)) * 2.0;
                    D _2453 = _252 - (_2449 * _807);
                    D _2454 = _253 - (_2449 * _808);
                    D _2455 = _254 - (_2449 * _809);
                    D _3755;
                    D _3756;
                    D _3757;
                    D _3758;
                    D _3759;
                    D _3760;
                    D _3761;
                    D _3762;
                    D _3763;
                    D _3764;
                    D _3765;
                    if (_1922 == 0.0)
                    {
                        D _3207;
                        D _3208;
                        D _3209;
                        if (_2066 > 9.9999997473787516355514526367188e-05)
                        {
                            D _3203 = inversesqrt(_2066);
                            _3207 = _3203 * _2063;
                            _3208 = _3203 * _2064;
                            _3209 = _3203 * _2065;
                        }
                        else
                        {
                            _3207 = 0.0;
                            _3208 = 0.0;
                            _3209 = 0.0;
                        }
                        D _3212 = 1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _2066));
                        _3755 = _3212;
                        _3756 = (_1921 * _1921) * _3212;
                        _3757 = _3207;
                        _3758 = _3208;
                        _3759 = _3209;
                        _3760 = _3207;
                        _3761 = _3208;
                        _3762 = _3209;
                        _3763 = _3207;
                        _3764 = _3208;
                        _3765 = _3209;
                    }
                    else
                    {
                        D _2701 = _1922 * 0.5;
                        D _2702 = _2701 * _1908;
                        D _2703 = _2701 * _1909;
                        D _2704 = _2701 * _1910;
                        D _2705 = _2063 - _2702;
                        D _2706 = _2064 - _2703;
                        D _2707 = _2065 - _2704;
                        D _2708 = _2702 + _2063;
                        D _2709 = _2703 + _2064;
                        D _2710 = _2704 + _2065;
                        D _2718 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2705, _2706, _2707), vec3(_2705, _2706, _2707))));
                        D _2720 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2708, _2709, _2710), vec3(_2708, _2709, _2710))));
                        D _2721 = _2720 * _2718;
                        D _2737 = (1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(_2721, ((dot(vec3(_2705, _2706, _2707), vec3(_2708, _2709, _2710)) * 0.5) * _2721) + 0.5))) * _2721;
                        D _2739 = (_1908 * 2.0) * _2701;
                        D _2741 = (_1909 * 2.0) * _2701;
                        D _2743 = (_1910 * 2.0) * _2701;
                        D _2744 = dot(vec3(_2739, _2741, _2743), vec3(_2739, _2741, _2743));
                        D _3245;
                        D _3246;
                        D _3247;
                        if (_2744 > 9.9999997473787516355514526367188e-05)
                        {
                            D _3215 = dot(vec3(_2453, _2454, _2455), vec3(_2739, _2741, _2743));
                            D _3231 = spvNClamp((1.0 / (_2744 - (_3215 * _3215))) * dot(vec3(_2705, _2706, _2707), vec3((_3215 * _2453) - _2739, (_3215 * _2454) - _2741, (_3215 * _2455) - _2743)), 0.0, 1.0);
                            D _3235 = (_3231 * _2739) + _2705;
                            D _3236 = (_3231 * _2741) + _2706;
                            D _3237 = (_3231 * _2743) + _2707;
                            D _3241 = inversesqrt(dot(vec3(_3235, _3236, _3237), vec3(_3235, _3236, _3237)));
                            _3245 = _3235 * _3241;
                            _3246 = _3236 * _3241;
                            _3247 = _3237 * _3241;
                        }
                        else
                        {
                            _3245 = _2705;
                            _3246 = _2706;
                            _3247 = _2707;
                        }
                        _3755 = _2737;
                        _3756 = (_1921 * _1921) * _2737;
                        _3757 = _2718 * _2705;
                        _3758 = _2718 * _2706;
                        _3759 = _2718 * _2707;
                        _3760 = _2720 * _2708;
                        _3761 = _2720 * _2709;
                        _3762 = _2720 * _2710;
                        _3763 = _3245;
                        _3764 = _3246;
                        _3765 = _3247;
                    }
                    D _3775 = _3756 + 1.0;
                    D _3780 = _3763 - _252;
                    D _3781 = _3764 - _253;
                    D _3782 = _3765 - _254;
                    D _3786 = inversesqrt(dot(vec3(_3780, _3781, _3782), vec3(_3780, _3781, _3782)));
                    D _3787 = _3786 * _3780;
                    D _3788 = _3786 * _3781;
                    D _3789 = _3786 * _3782;
                    D _3796 = spvNClamp(dot(vec3(_807, _808, _809), vec3(_3787, _3788, _3789)), 0.0, 1.0);
                    D _3797 = _1295 * _1295;
                    D _3803 = spvNClamp(((1.0 - _3797) * _1921) * sqrt(_3755), 0.0, 1.0);
                    D _3816 = exp2(log2(spvNClamp((((_3803 * 0.25) * (_3803 + (_3797 * 3.0))) * (1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_255, _257, _258), vec3(_3787, _3788, _3789))))) + (_3797 * _3797), 0.0, 1.0)) * 0.25);
                    D _3820 = spvNClamp(dot(vec3(_3757, _3758, _3759), vec3(_3760, _3761, _3762)), 0.0, 1.0);
                    D _3822 = _3816 * _3816;
                    D _3823 = _3822 * _3822;
                    D _4112;
                    if (_3820 < 1.0)
                    {
                        D _4103 = sqrt(spvNClamp((1.0 / (_3820 + 1.0)) * (1.0 - _3820), 0.0, 1.0));
                        _4112 = (1.0 / spvNClamp(((_4103 * 0.25) * (_4103 + (_3822 * 3.0))) + _3823, 0.0, 1.0)) * _3823;
                    }
                    else
                    {
                        _4112 = 1.0;
                    }
                    D _4116 = ((_3796 * _3796) * (_3823 + (-1.0))) + 1.0;
                    D _4119 = spvNMax(0.0, (((dot(vec3(_807, _808, _809), vec3(_3760, _3761, _3762)) + dot(vec3(_807, _808, _809), vec3(_3757, _3758, _3759))) * 0.5) + _3756) * (1.0 / (_3775 * _3775))) * 0.3183098733425140380859375;
                    D _4122 = ((_4119 * _3823) * _4112) * (1.0 / (_4116 * _4116));
                    D _4124 = (_2078 * _1904) * _3755;
                    D _4126 = (_2078 * _1905) * _3755;
                    D _4128 = (_2078 * _1906) * _3755;
                    _2457 = _4122 * _4124;
                    _2459 = _4122 * _4126;
                    _2461 = _4122 * _4128;
                    _2463 = _4119 * _4124;
                    _2465 = _4119 * _4126;
                    _2467 = _4119 * _4128;
                }
                else
                {
                    _2457 = 0.0;
                    _2459 = 0.0;
                    _2461 = 0.0;
                    _2463 = 0.0;
                    _2465 = 0.0;
                    _2467 = 0.0;
                }
                frontier_phi_47_pred = _1884;
                frontier_phi_47_pred_1 = _1877;
                frontier_phi_47_pred_2 = _1878;
                frontier_phi_47_pred_3 = _1879;
                frontier_phi_47_pred_4 = _1880;
                frontier_phi_47_pred_5 = _1881;
                frontier_phi_47_pred_6 = _1882;
                frontier_phi_47_pred_7 = _1883;
                frontier_phi_47_pred_8 = _1885;
                frontier_phi_47_pred_9 = _1887;
                frontier_phi_47_pred_10 = _1886;
                frontier_phi_47_pred_11 = _2467 + _1894;
                frontier_phi_47_pred_12 = _2465 + _1893;
                frontier_phi_47_pred_13 = _2463 + _1892;
                frontier_phi_47_pred_14 = _2461 + _1891;
                frontier_phi_47_pred_15 = _2459 + _1890;
                frontier_phi_47_pred_16 = _2457 + _1889;
                frontier_phi_47_pred_17 = _1888;
            }
            _1481 = frontier_phi_47_pred;
            _1467 = frontier_phi_47_pred_1;
            _1469 = frontier_phi_47_pred_2;
            _1471 = frontier_phi_47_pred_3;
            _1473 = frontier_phi_47_pred_4;
            _1475 = frontier_phi_47_pred_5;
            _1477 = frontier_phi_47_pred_6;
            _1479 = frontier_phi_47_pred_7;
            _1483 = frontier_phi_47_pred_8;
            _1487 = frontier_phi_47_pred_9;
            _1485 = frontier_phi_47_pred_10;
            _1501 = frontier_phi_47_pred_11;
            _1499 = frontier_phi_47_pred_12;
            _1497 = frontier_phi_47_pred_13;
            _1495 = frontier_phi_47_pred_14;
            _1493 = frontier_phi_47_pred_15;
            _1491 = frontier_phi_47_pred_16;
            _1489 = frontier_phi_47_pred_17;
            uint _1896 = _1895 + 1u;
            if (_1896 == _1459)
            {
                break;
            }
            else
            {
                _1877 = _1467;
                _1878 = _1469;
                _1879 = _1471;
                _1880 = _1473;
                _1881 = _1475;
                _1882 = _1477;
                _1883 = _1479;
                _1884 = _1481;
                _1885 = _1483;
                _1886 = _1485;
                _1887 = _1487;
                _1888 = _1489;
                _1889 = _1491;
                _1890 = _1493;
                _1891 = _1495;
                _1892 = _1497;
                _1893 = _1499;
                _1894 = _1501;
                _1895 = _1896;
                continue;
            }
        }
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
        _1500 = _1501;
    }
    D _1535 = (_244 - View._m0[180u].x) * View._m0[182u].x;
    D _1536 = (_245 - View._m0[180u].y) * View._m0[182u].y;
    D _1537 = (_246 - View._m0[180u].z) * View._m0[182u].z;
    vec4 _1542 = textureLod(sampler3D(TranslucentBasePass_TranslucencyLightingVolumeEnvironmentA, View_SharedBilinearClampedSampler), vec3(_1535, _1536, _1537), 0.0);
    D _1544 = _1542.x;
    D _1580;
    D _1581;
    D _1582;
    if (_751 < 1.0)
    {
        _1580 = _729.x / ((_773 / _750) + 1.0);
        _1581 = _729.y / ((_774 / _750) + 1.0);
        _1582 = _729.z / ((_775 / _750) + 1.0);
    }
    else
    {
        _1580 = 0.0;
        _1581 = 0.0;
        _1582 = 0.0;
    }
    D _1587 = View._m0[164u].z * _1544;
    D _1588 = View._m0[164u].z * _1542.y;
    D _1589 = View._m0[164u].z * _1542.z;
    D _1590 = spvNClamp(_989, 0.0, 1.0);
    D _1591 = spvNClamp(_990, 0.0, 1.0);
    D _1592 = spvNClamp(_991, 0.0, 1.0);
    D _1602 = spvNClamp((-0.0) - _989, 0.0, 1.0);
    D _1603 = spvNClamp((-0.0) - _990, 0.0, 1.0);
    D _1604 = spvNClamp((-0.0) - _991, 0.0, 1.0);
    D _1611 = dot(vec3(textureLod(sampler3D(TranslucentBasePass_TranslucencyLightingVolumeEnvironmentC, View_SharedBilinearClampedSampler), vec3(_1535, _1536, _1537), 0.0).xyz()), vec3(_1602 * _1602, _1603 * _1603, _1604 * _1604)) + dot(vec3(textureLod(sampler3D(TranslucentBasePass_TranslucencyLightingVolumeEnvironmentB, View_SharedBilinearClampedSampler), vec3(_1535, _1536, _1537), 0.0).xyz()), vec3(_1590 * _1590, _1591 * _1591, _1592 * _1592));
    D _1612 = dot(vec3(_1544, _1542.yz()), vec3(0.2125999927520751953125, 0.715200006961822509765625, 0.072200000286102294921875));
    D _1620 = (_1612 > 0.0) ? (1.0 / _1612) : 0.0;
    D _1651 = ((_1580 * _1246) * spvNClamp(1.0 - (_1265 * _1255), 0.0, 1.0)) * ((_1587 + _1472) + ((((_1587 * _1611) * _1620) - _1587) * 0.6480000019073486328125));
    D _1654 = ((_1581 * _1246) * spvNClamp(1.0 - (_1266 * _1255), 0.0, 1.0)) * ((_1588 + _1474) + ((((_1588 * _1611) * _1620) - _1588) * 0.6480000019073486328125));
    D _1657 = ((_1582 * _1246) * spvNClamp(1.0 - (_1267 * _1255), 0.0, 1.0)) * ((_1589 + _1476) + ((((_1589 * _1611) * _1620) - _1589) * 0.6480000019073486328125));
    D _1671 = spvNClamp(_1277, 0.0, 1.0);
    D _1681 = ((_807 - _944) * _975) + _944;
    D _1682 = ((_808 - _945) * _975) + _945;
    D _1683 = ((_809 - _946) * _975) + _946;
    D _1687 = inversesqrt(dot(vec3(_1681, _1682, _1683), vec3(_1681, _1682, _1683)));
    D _1696 = 10.0 / spvNMax(9.9999997473787516355514526367188e-06, _974);
    D _1724 = fma(_243, View._m0[2u].x, fma(_242, View._m0[1u].x, View._m0[0u].x * _241)) + View._m0[3u].x;
    D _1728 = fma(_243, View._m0[2u].y, fma(_242, View._m0[1u].y, View._m0[0u].y * _241)) + View._m0[3u].y;
    D _1732 = fma(_243, View._m0[2u].z, fma(_242, View._m0[1u].z, View._m0[0u].z * _241)) + View._m0[3u].z;
    D _1736 = fma(_243, View._m0[2u].w, fma(_242, View._m0[1u].w, View._m0[0u].w * _241)) + View._m0[3u].w;
    D _1743 = ((_1681 * _116) * _1687) + _241;
    D _1744 = ((_1682 * _116) * _1687) + _242;
    D _1745 = ((_1683 * _116) * _1687) + _243;
    D _1778 = 1.0 / _1736;
    D _1779 = _1778 * _1724;
    D _1780 = _1778 * _1728;
    D _1784 = (_1778 * _1732) + (0.0500000007450580596923828125 / _1736);
    D _1785 = 1.0 / (fma(_1745, View._m0[2u].w, fma(_1744, View._m0[1u].w, View._m0[0u].w * _1743)) + View._m0[3u].w);
    D _1796 = 1.0 / ((View._m0[36u].w * _1696) + _1736);
    D _1799 = (_1785 * (fma(_1745, View._m0[2u].x, fma(_1744, View._m0[1u].x, View._m0[0u].x * _1743)) + View._m0[3u].x)) - _1779;
    D _1800 = (_1785 * (fma(_1745, View._m0[2u].y, fma(_1744, View._m0[1u].y, View._m0[0u].y * _1743)) + View._m0[3u].y)) - _1780;
    D _1802 = (_1796 * ((View._m0[36u].x * _1696) + _1724)) - _1779;
    D _1803 = (_1796 * ((View._m0[36u].y * _1696) + _1728)) - _1780;
    D _1808 = sqrt((_1799 * _1799) + (_1800 * _1800)) * 0.5;
    D _1826 = spvNMin(1.0 - (spvNMax(0.0, abs((_1808 * _1779) + _1799) - _1808) / abs(_1799)), 1.0 - (spvNMax(0.0, abs((_1808 * _1780) + _1800) - _1808) / abs(_1800))) / _1808;
    D _1827 = _1826 * _1799;
    D _1828 = _1826 * _1800;
    D _1829 = _1826 * ((_1785 * (fma(_1745, View._m0[2u].z, fma(_1744, View._m0[1u].z, View._m0[0u].z * _1743)) + View._m0[3u].z)) - _1784);
    uvec2 _1835 = uvec2(textureSize(TranslucentBasePass_HZBTexture, int(0u)));
    D _1837 = D(int(_1835.x));
    D _1839 = D(int(_1835.y));
    uint _1860 = max(1u, min(uint(ceil((spvNClamp((1.0 / spvNMax(9.9999997473787516355514526367188e-05, sqrt((_1827 * _1827) + (_1828 * _1828)))) * sqrt((_1802 * _1802) + (_1803 * _1803)), 0.0, 1.0) * 8.0) + _279)), 8u));
    D _1865 = ((_1779 * 0.5) + 0.5) * TranslucentBasePass_2._m0[198u].x;
    D _1866 = (0.5 - (_1780 * 0.5)) * TranslucentBasePass_2._m0[198u].y;
    D _1869 = (TranslucentBasePass_2._m0[198u].x * 0.0625) * _1827;
    D _1872 = (TranslucentBasePass_2._m0[198u].y * (-0.0625)) * _1828;
    D _1873 = _1829 * 0.125;
    D _1875 = spvNMax(abs(_1829), _1784 - ((1.0 / (fma(_116, View._m0[38u].w, 0.0) + _1736)) * (fma(_116, View._m0[38u].z, 0.0) + _1732))) * 0.125;
    D _2046;
    D _2048;
    D _2050;
    D _2052;
    if (_1860 == 0u)
    {
        _2046 = 0.0;
        _2048 = 0.0;
        _2050 = 0.0;
        _2052 = 0.0;
    }
    else
    {
        D frontier_phi_55;
        D frontier_phi_55_1;
        D frontier_phi_55_2;
        D frontier_phi_55_3;
        D _2370 = 0.0;
        uint _2372 = 0u;
        D _2371;
        D _2374;
        bool _2397;
        for (;;)
        {
            _2374 = D(_2372);
            D _2375 = _2374 + _279;
            vec4 _2389 = texelFetch(TranslucentBasePass_HZBTexture, ivec2_(uvec2(uint(int(floor(((_2375 * _1869) + _1865) * _1837))), uint(int(floor(((_2375 * _1872) + _1866) * _1839))))), int(0u));
            D _2391 = _2389.x;
            _2371 = ((_2375 * _1873) + _1784) - _2391;
            _2397 = (abs(((-0.0) - _1875) - _2371) < _1875) && (_2391 != 0.0);
            if (_2397)
            {
                D _2627 = (_2372 == 0u) ? (_2371 - _1873) : _2370;
                D _2634 = abs(((_279 + (-1.0)) + _2374) + spvNClamp(_2627 / (_2627 - _2371), 0.0, 1.0));
                D _2639 = spvNMin(_2634 * 0.125, 1.0);
                frontier_phi_55 = 1.0 - (_2639 * _2639);
                frontier_phi_55_1 = (_2634 * _1873) + _1784;
                frontier_phi_55_2 = (_2634 * _1872) + _1866;
                frontier_phi_55_3 = (_2634 * _1869) + _1865;
                break;
            }
            else
            {
                uint _2373 = _2372 + 1u;
                if (_2373 < _1860)
                {
                    _2370 = _2371;
                    _2372 = _2373;
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
        _2046 = frontier_phi_55_3;
        _2048 = frontier_phi_55_2;
        _2050 = frontier_phi_55_1;
        _2052 = frontier_phi_55;
    }
    D _2060 = (spvNClamp(_2046 * TranslucentBasePass_2._m0[198u].z, 0.0, 1.0) * 2.0) + (-1.0);
    D _2061 = 1.0 - (spvNClamp(_2048 * TranslucentBasePass_2._m0[198u].w, 0.0, 1.0) * 2.0);
    D _2289;
    D _2290;
    D _2291;
    D _2292;
    if (_2052 > 0.0)
    {
        D _2152 = ((View._m0[73u].x * _2050) + View._m0[73u].y) + (1.0 / ((View._m0[73u].z * _2050) - View._m0[73u].w));
        D _2176 = _2152 * _2060;
        D _2177 = _2152 * _2061;
        D _2188 = (_241 - View._m0[63u].x) - fma(_2152, View._m0[62u].x, fma(_2177, View._m0[61u].x, _2176 * View._m0[60u].x));
        D _2190 = (_242 - View._m0[63u].y) - fma(_2152, View._m0[62u].y, fma(_2177, View._m0[61u].y, _2176 * View._m0[60u].y));
        D _2192 = (_243 - View._m0[63u].z) - fma(_2152, View._m0[62u].z, fma(_2177, View._m0[61u].z, _2176 * View._m0[60u].z));
        uvec2 _2243 = uvec2(textureSize(TranslucentBasePass_SceneColorCopyTexture, int(0u)));
        uint _2262 = uint(min(int(uint(max(int(uint(int(D(int(_2243.x)) * ((View._m0[74u].x * spvNMin(spvNMax(_2060 - ((D(int(uint(_2060 > 0.0) - uint(_2060 < 0.0))) * 2.0) * spvNMax(0.0, abs(_2060) + (-1.0))), -1.0), 1.0)) + View._m0[74u].w)))), int(uint(int(View._m0[158u].x)))))), int(uint(int(View._m0[159u].x + View._m0[158u].x)) + 4294967295u)));
        uint _2263 = uint(min(int(uint(max(int(uint(int(D(int(_2243.y)) * ((View._m0[74u].y * spvNMin(spvNMax(_2061 - ((D(int(uint(_2061 > 0.0) - uint(_2061 < 0.0))) * 2.0) * spvNMax(0.0, abs(_2061) + (-1.0))), -1.0), 1.0)) + View._m0[74u].z)))), int(uint(int(View._m0[158u].y)))))), int(uint(int(View._m0[159u].y + View._m0[158u].y)) + 4294967295u)));
        vec4 _2268 = texelFetch(TranslucentBasePass_SceneColorCopyTexture, ivec2_(uvec2(_2262, _2263)), int(0u));
        _2289 = View._m0[164u].z * spvNMin(_2268.x, 65504.0);
        _2290 = View._m0[164u].z * spvNMin(_2268.y, 65504.0);
        _2291 = View._m0[164u].z * spvNMin(_2268.z, 65504.0);
        _2292 = (D(texelFetch(TranslucentBasePass_SceneTextures_SceneDepthTexture, ivec2_(uvec2(_2262, _2263)), int(0u)).x != 0.0) * _2052) * spvNClamp(1.0 / spvNMax(9.9999997473787516355514526367188e-06, (_974 * _974) * dot(vec3(_2188, _2190, _2192), vec3(_2188, _2190, _2192))), 0.0, 1.0);
    }
    else
    {
        _2289 = 0.0;
        _2290 = 0.0;
        _2291 = 0.0;
        _2292 = 0.0;
    }
    vec4 _2316 = textureLod(sampler2D(TranslucentBasePass_SceneColorCopyTexture, View_SharedBilinearClampedSampler), vec2((_1203 * (View._m0[161u].z * (_1176 - gl_FragCoord.x))) + _999, (_1203 * (View._m0[161u].w * (_1177 - gl_FragCoord.y))) + _1000), 0.0);
    SV_Target.x = View._m0[164u].y * ((((((((((_857 * _833) * _1353) * spvNMax(1.0, ((_912 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_912 * 4.79510021209716796875)) + (((_912 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _833)) * _833))) * _1496) + _1484) * _834) + _1478) + ((((((_1587 + _1466) * 0.979626834392547607421875) - _1651) * _1249) + _1651) * _1671)) + (((View._m0[164u].z * _2316.x) * spvNClamp(_1285 - (_1285 * _831), 0.0, 1.0)) * _1671)) + ((_1367 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _2289)) + 29.8973522186279296875) * _2292) + (-29.8973522186279296875)) + _1490)) * spvNClamp(_1345, 0.0, 1.0)));
    SV_Target.y = View._m0[164u].y * ((((((((((_858 * _833) * _1353) * spvNMax(1.0, ((_913 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_913 * 4.79510021209716796875)) + (((_913 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _833)) * _833))) * _1498) + _1486) * _834) + _1480) + ((((((_1588 + _1468) * 0.979626834392547607421875) - _1654) * _1249) + _1654) * _1671)) + (((View._m0[164u].z * _2316.y) * spvNClamp(_1288 - (_1288 * _831), 0.0, 1.0)) * _1671)) + ((_1367 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _2290)) + 29.8973522186279296875) * _2292) + (-29.8973522186279296875)) + _1492)) * spvNClamp(_1346, 0.0, 1.0)));
    SV_Target.z = View._m0[164u].y * ((((((((((_859 * _833) * _1353) * spvNMax(1.0, ((_914 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_914 * 4.79510021209716796875)) + (((_914 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _833)) * _833))) * _1500) + _1488) * _834) + _1482) + ((((((_1589 + _1470) * 0.979626834392547607421875) - _1657) * _1249) + _1657) * _1671)) + (((View._m0[164u].z * _2316.z) * spvNClamp(_1291 - (_1291 * _831), 0.0, 1.0)) * _1671)) + ((_1367 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _2291)) + 29.8973522186279296875) * _2292) + (-29.8973522186279296875)) + _1494)) * spvNClamp(_1347, 0.0, 1.0)));
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
} // namespace S_ater_Pool_Flow_Wide_Detail_Environment_Development