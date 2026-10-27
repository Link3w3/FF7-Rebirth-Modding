namespace S_lass_Emissive_Thin_Wide_Character {
using namespace cpuglsl;
static D _4387;
static D _4383;
static D _4384;
static D _4385;
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










void discard_cond(bool _4373)
{
    if (_4373)
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
    D _109 = 1.0 / gl_FragCoord.w;
    D _232 = fma(gl_FragCoord.z, View._m0[54u].w, fma(gl_FragCoord.y, View._m0[53u].w, View._m0[52u].w * gl_FragCoord.x)) + View._m0[55u].w;
    D _233 = (fma(gl_FragCoord.z, View._m0[54u].x, fma(gl_FragCoord.y, View._m0[53u].x, View._m0[52u].x * gl_FragCoord.x)) + View._m0[55u].x) / _232;
    D _234 = (fma(gl_FragCoord.z, View._m0[54u].y, fma(gl_FragCoord.y, View._m0[53u].y, View._m0[52u].y * gl_FragCoord.x)) + View._m0[55u].y) / _232;
    D _235 = (fma(gl_FragCoord.z, View._m0[54u].z, fma(gl_FragCoord.y, View._m0[53u].z, View._m0[52u].z * gl_FragCoord.x)) + View._m0[55u].z) / _232;
    D _236 = _233 - View._m0[78u].x;
    D _237 = _234 - View._m0[78u].y;
    D _238 = _235 - View._m0[78u].z;
    D _243 = inversesqrt(dot(vec3(_233, _234, _235), vec3(_233, _234, _235)));
    D _244 = _243 * _233;
    D _245 = _243 * _234;
    D _246 = _243 * _235;
    D _247 = (-0.0) - _244;
    D _249 = (-0.0) - _245;
    D _250 = (-0.0) - _246;
    vec4 _268 = texelFetch(View_SpatiotemporalBlueNoiseVolumeTexture, ivec3_(uvec3(uint(int(gl_FragCoord.x)) & 127u, uint(int(gl_FragCoord.y)) & 127u, ((floatBitsToUint(View._m0[175u]).x & 7u) + uint(roundEven(CONSTANT_CONTEXT))) & 63u)), int(0u));
    D _271 = _268.x;
    D _272 = _268.y;
    vec4 _286 = texture(sampler2D(Material_Texture2D_0, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _294 = texture(sampler2D(Material_Texture2D_1, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _299 = texture(sampler2D(Material_Texture2D_2, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _306 = (_299.x * 2.0) + (-1.0);
    D _308 = (_299.y * 2.0) + (-1.0);
    D _314 = sqrt(spvNMax(0.0, 1.0 - dot(vec2(_306, _308), vec2(_306, _308))));
    D _318 = inversesqrt(dot(vec3(_306, _308, _314), vec3(_306, _308, _314)));
    D _319 = _318 * _306;
    D _320 = _318 * _308;
    D _321 = _318 * _314;
    vec4 _324 = texture(sampler2D(Material_Texture2D_3, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _329 = texture(sampler2D(Material_Texture2D_4, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _331 = _329.x;
    vec4 _334 = texture(sampler2D(Material_Texture2D_6, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _341 = texture(sampler2D(Material_Texture2D_15, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.z, TEXCOORD.w), View._m0[155u].y);
    D _343 = _341.x;
    D _344 = _343 * _331;
    D _345 = spvNMin(_331, _343);
    D _347 = (1.0 - _345) + _344;
    D _348 = _347 * _347;
    D _351 = 1.0 - ((_348 * _348) * _347);
    D _352 = _351 * _351;
    vec4 _360 = texture(sampler2D(Material_Texture2D_7, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _366 = vec4(g_R.Muddiness.x, g_R.Muddiness.y, g_R.Muddiness.z, 0.0);
    vec4 _373 = texture(sampler2D(Material_Texture2D_20, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _378 = texture(sampler2D(Material_Texture2D_21, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _388 = g_R.TransparencyLog2;
    D _389 = exp2(_388);
    vec4 _392 = texture(sampler2D(Material_Texture2D_22, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _399 = texture(sampler2D(Material_Texture2D_23, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _404 = 1.0 / spvNMax(9.9999999747524270787835121154785e-07, _399.x * 100.0);
    D _411 = g_R.TransmittanceLog2.x;
    D _412 = g_R.TransmittanceLog2.y;
    D _413 = g_R.TransmittanceLog2.z;
    vec4 _419 = vec4(g_R.Thickness);
    D _429;
    if (Material._m0[3u].w > 0.0)
    {
        _429 = View._m0[164u].z;
    }
    else
    {
        _429 = 1.0;
    }
    D _436 = inversesqrt(dot(vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z), vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z)));
    D _437 = _436 * g_R.Normal.x;
    D _438 = _436 * g_R.Normal.y;
    D _439 = _436 * g_R.Normal.z;
    D _442 = fma(_439, TEXCOORD_11.x, fma(_438, ((TEXCOORD_10.z * TEXCOORD_11.y) - (TEXCOORD_10.y * TEXCOORD_11.z)) * TEXCOORD_11.w, _437 * TEXCOORD_10.x));
    D _445 = fma(_439, TEXCOORD_11.y, fma(_438, ((TEXCOORD_10.x * TEXCOORD_11.z) - (TEXCOORD_10.z * TEXCOORD_11.x)) * TEXCOORD_11.w, _437 * TEXCOORD_10.y));
    D _448 = fma(_439, TEXCOORD_11.z, fma(_438, ((TEXCOORD_10.y * TEXCOORD_11.x) - (TEXCOORD_10.x * TEXCOORD_11.y)) * TEXCOORD_11.w, _437 * TEXCOORD_10.z));
    D _452 = inversesqrt(dot(vec3(_442, _445, _448), vec3(_442, _445, _448)));
    D _453 = _452 * _442;
    D _454 = _452 * _445;
    D _455 = _452 * _448;
    bool _468;
    if (Primitive._m0[27u].w > ((_268.w * 0.99609375) + 0.001953125))
    {
        _468 = ((_271 * 0.99609375) + 0.001953125) < 1.0;
    }
    else
    {
        _468 = false;
    }
    (void)((_468 ? 1.0 : (-1.0)) < 0.0);
    D _474 = spvNClamp(g_R.BaseColor.x, 0.0, 1.0);
    D _475 = spvNClamp(g_R.BaseColor.y, 0.0, 1.0);
    D _476 = spvNClamp(g_R.BaseColor.z, 0.0, 1.0);
    D _477 = spvNClamp(g_R.Metallic, 0.0, 1.0);
    D _478 = spvNClamp(g_R.Roughness, 0.0, 1.0);
    D _479 = spvNClamp(g_R.AO, 0.0, 1.0);
    D _483 = spvNClamp(g_R.Opacity, 0.0, 1.0);
    D _485 = dFdxFine(_453);
    D _486 = dFdxFine(_454);
    D _487 = dFdxFine(_455);
    D _491 = dFdyFine(_453);
    D _492 = dFdyFine(_454);
    D _493 = dFdyFine(_455);
    D _504 = sqrt(spvNClamp(spvNMin((dot(vec3(_491, _492, _493), vec3(_491, _492, _493)) + dot(vec3(_485, _486, _487), vec3(_485, _486, _487))) * 0.15915493667125701904296875, 0.180000007152557373046875) + (_478 * _478), 0.0, 1.0));
    D _505 = 1.0 - _477;
    D _506 = _505 * _474;
    D _507 = _505 * _475;
    D _508 = _505 * _476;
    D _513 = _477 * (_474 + (-0.0400000028312206268310546875));
    D _514 = _477 * (_475 + (-0.0400000028312206268310546875));
    D _515 = _477 * (_476 + (-0.0400000028312206268310546875));
    D _516 = _513 + 0.0400000028312206268310546875;
    D _518 = _514 + 0.0400000028312206268310546875;
    D _519 = _515 + 0.0400000028312206268310546875;
    D _526 = spvNClamp(D(View._m0[220u].x > 1.0), 0.0, 1.0);
    D _554 = ((exp2(log2(spvNMax(0.0, _513 + 0.020000003278255462646484375) * 1.020408153533935546875) * 1.39999997615814208984375) - _516) * _526) + _516;
    D _555 = ((exp2(log2(spvNMax(0.0, _514 + 0.020000003278255462646484375) * 1.020408153533935546875) * 1.39999997615814208984375) - _518) * _526) + _518;
    D _556 = ((exp2(log2(spvNMax(0.0, _515 + 0.020000003278255462646484375) * 1.020408153533935546875) * 1.39999997615814208984375) - _519) * _526) + _519;
    D _561 = (_554 * 0.449999988079071044921875) + _506;
    D _562 = (_555 * 0.449999988079071044921875) + _507;
    D _563 = (_556 * 0.449999988079071044921875) + _508;
    D _570 = dot(vec3(_453, _454, _455), vec3(_247, _249, _250));
    D _576 = (_570 * _453) + _244;
    D _577 = (_570 * _454) + _245;
    D _578 = (_570 * _455) + _246;
    D _582 = abs(_570);
    D _586 = (_576 * 2.0) + (_582 * _453);
    D _587 = (_577 * 2.0) + (_582 * _454);
    D _588 = (_578 * 2.0) + (_582 * _455);
    D _592 = inversesqrt(dot(vec3(_586, _587, _588), vec3(_586, _587, _588)));
    D _593 = _586 * _592;
    D _594 = _587 * _592;
    D _595 = _588 * _592;
    D _596 = spvNMax(9.9999997473787516355514526367188e-06, _582);
    D _608 = 1.0 - _504;
    D _609 = 0.0425000004470348358154296875 - (_504 * 0.0274999998509883880615234375);
    D _611 = 1.03999996185302734375 - (_504 * 0.572000026702880859375);
    D _613 = (_504 * 0.02199999988079071044921875) + (-0.039999999105930328369140625);
    D _618 = _608 * _608;
    D _622 = ((spvNMin(_618, exp2(_596 * (-9.27999973297119140625))) * _608) + _609) * 1.03999996185302734375;
    D _628 = 1.0 - spvNClamp((_613 + _622) + ((_611 - _622) * 0.0400000028312206268310546875), 0.0, 1.0);
    D _629 = _628 * _628;
    D _630 = spvNMax(0.001000000047497451305389404296875, (1.0 / spvNMax(0.0333333350718021392822265625, _596)) * _419.x);
    D _633 = log2(spvNMax(0.0, _389));
    D _635 = exp2(_633 * _630);
    D _639 = log2(spvNMax(0.0, exp2(_411)));
    D _640 = log2(spvNMax(0.0, exp2(_412)));
    D _641 = log2(spvNMax(0.0, exp2(_413)));
    D _645 = exp2(_639 * _630);
    D _646 = exp2(_640 * _630);
    D _647 = exp2(_641 * _630);
    D _649 = exp2(_633 * 0.001000000047497451305389404296875);
    D _656 = 1.0 - _483;
    D _658 = (_629 * _656) * _635;
    D _661 = ((_658 * _645) * _649) * exp2(_639 * 0.001000000047497451305389404296875);
    D _664 = ((_658 * _646) * _649) * exp2(_640 * 0.001000000047497451305389404296875);
    D _667 = ((_658 * _647) * _649) * exp2(_641 * 0.001000000047497451305389404296875);
    D _674 = spvNMax(0.039999999105930328369140625, _504);
    D _690 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_674 * _596) + 0.02669160068035125732421875) / (_596 + 0.4664950072765350341796875)) * exp2(((1.0 / _674) * _596) * log2(_674)), 0.0, 1.0));
    D _691 = 1.0 - _596;
    D _692 = _691 * _691;
    D _705 = _692 * _692;
    D _707 = (_705 * _691) * exp2(log2((exp2((_674 * 4.7702999114990234375) * log2(_596)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _674);
    D _710 = (1.0 / _690) * (1.0 - _690);
    D _717 = _690 - _707;
    D _724 = ((_710 * _554) + 1.0) * ((_717 * _554) + _707);
    D _725 = ((_710 * _555) + 1.0) * ((_717 * _555) + _707);
    D _726 = ((_710 * _556) + 1.0) * ((_717 * _556) + _707);
    D _732 = spvNClamp(1.0 - dot(vec3(_724, _725, _726), vec3(0.3333333432674407958984375)), 0.0, 1.0);
    D _746 = spvNClamp((_479 + (-1.0)) + exp2(log2(_596 + _479) * exp2((-1.0) - (_504 * 16.0))), 0.0, 1.0);
    D _806;
    D _808;
    D _810;
    D _812;
    D _814;
    D _816;
    D _818;
    D _820;
    D _822;
    if (floatBitsToUint(TranslucentBasePass_2._m0[0u]).z == 0u)
    {
        _806 = 0.0;
        _808 = 0.0;
        _810 = 0.0;
        _812 = 0.0;
        _814 = 0.0;
        _816 = 0.0;
        _818 = 0.0;
        _820 = 0.0;
        _822 = 0.0;
    }
    else
    {
        D _1254;
        uint _837;
        bool _838;
        for (;;)
        {
            _837 = floatBitsToUint(TranslucentBasePass_2._m0[7u]).z;
            _838 = _837 == 0u;
            if (!_838)
            {
                uint _1419;
                uint _1322 = 0u;
                for (;;)
                {
                    if (_109 < TranslucentBasePass._m0[_1322 + 32u])
                    {
                        _1419 = _1322;
                        break;
                    }
                    else
                    {
                        uint _1323 = _1322 + 1u;
                        if (_1323 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                        {
                            _1322 = _1323;
                            continue;
                        }
                        else
                        {
                            _1419 = _837;
                            break;
                        }
                    }
                }
                if (_1419 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                {
                    uint _1770 = _1419 << 2u;
                    uint _1771 = _1770 + 9u;
                    uint _1778 = _1770 + 10u;
                    uint _1785 = _1770 + 11u;
                    uint _1792 = _1770 + 12u;
                    uint _1799 = _1419 + 25u;
                    D _1825 = fma(_238, TranslucentBasePass_2._m0[_1785].z, fma(_237, TranslucentBasePass_2._m0[_1778].z, TranslucentBasePass_2._m0[_1771].z * _236)) + TranslucentBasePass_2._m0[_1792].z;
                    D _1829 = fma(_238, TranslucentBasePass_2._m0[_1785].w, fma(_237, TranslucentBasePass_2._m0[_1778].w, TranslucentBasePass_2._m0[_1771].w * _236)) + TranslucentBasePass_2._m0[_1792].w;
                    D _1830 = (fma(_238, TranslucentBasePass_2._m0[_1785].x, fma(_237, TranslucentBasePass_2._m0[_1778].x, TranslucentBasePass_2._m0[_1771].x * _236)) + TranslucentBasePass_2._m0[_1792].x) / _1829;
                    D _1831 = (fma(_238, TranslucentBasePass_2._m0[_1785].y, fma(_237, TranslucentBasePass_2._m0[_1778].y, TranslucentBasePass_2._m0[_1771].y * _236)) + TranslucentBasePass_2._m0[_1792].y) / _1829;
                    bool _1838 = (_1831 <= TranslucentBasePass_2._m0[_1799].w) && ((_1830 <= TranslucentBasePass_2._m0[_1799].z) && ((_1830 >= TranslucentBasePass_2._m0[_1799].x) && (_1831 >= TranslucentBasePass_2._m0[_1799].y)));
                    D _1255;
                    if (_1838)
                    {
                        D _2195 = dFdyFine(_1830);
                        D _2196 = dFdyFine(_1831);
                        D _2197 = dFdyFine(_1825);
                        D _2198 = dFdxFine(_1830);
                        D _2199 = dFdxFine(_1831);
                        D _2200 = dFdxFine(_1825);
                        D _2203 = (_2199 * _2197) - (_2200 * _2196);
                        D _2206 = (_2200 * _2195) - (_2198 * _2197);
                        D _2209 = (_2198 * _2196) - (_2199 * _2195);
                        D _2219 = 1.0 / spvNMax(abs(_2209), sqrt(((_2206 * _2206) + (_2209 * _2209)) + (_2203 * _2203)) * 0.100000001490116119384765625);
                        D _2225 = D(int(uint(_2209 > 0.0) - uint(_2209 < 0.0)));
                        D _2226 = _2203 * TranslucentBasePass_2._m0[29u].z;
                        D _2228 = (_2226 * _2219) * _2225;
                        D _2229 = _2206 * TranslucentBasePass_2._m0[29u].w;
                        D _2231 = (_2229 * _2219) * _2225;
                        D _2853;
                        D _2855;
                        if (dot(vec2(_2203, _2206), vec2(_2203, _2206)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2853 = 0.0;
                            _2855 = 0.0;
                        }
                        else
                        {
                            D _3223 = (-0.0) - _2203;
                            D _3224 = (-0.0) - _2206;
                            D _3228 = inversesqrt(dot(vec2(_3223, _3224), vec2(_3223, _3224)));
                            _2853 = _3228 * _3223;
                            _2855 = _3228 * _3224;
                        }
                        D _2857 = _272 + (-0.5);
                        D _2862 = _271 + 0.5;
                        D _2865 = ((_2855 * _2857) + (_1830 * TranslucentBasePass_2._m0[29u].x)) + (_2853 * _2862);
                        D _2868 = ((_2853 * _2857) + (_1831 * TranslucentBasePass_2._m0[29u].y)) + (_2855 * _2862);
                        D _2869 = _2865 + (-0.5);
                        D _2870 = _2868 + (-0.5);
                        D _2871 = trunc(_2869);
                        D _2872 = trunc(_2870);
                        D _2873 = _2869 - _2871;
                        D _2874 = _2870 - _2872;
                        D _2875 = _2871 * TranslucentBasePass_2._m0[29u].z;
                        D _2876 = _2872 * TranslucentBasePass_2._m0[29u].w;
                        D _2879 = (_2871 + (-0.5)) - _2865;
                        D _2880 = (_2872 + (-0.5)) - _2868;
                        D _2881 = dot(vec2(_2879, _2880), vec2(_2228, _2231));
                        D _2884 = _2881 + _2231;
                        D _2887 = _2225 * (_2219 * (_2229 + _2226));
                        D _2888 = _2887 + _2881;
                        D _2889 = _2881 + _2228;
                        vec4 _2895 = textureGather((sampler2D(ShadowMaps[_1419 + 0u], View_SharedPointClampedSampler)), vec2(_2875, _2876));
                        D _2896 = _2895.x;
                        D _2897 = _2895.y;
                        D _2898 = _2895.z;
                        D _2899 = _2895.w;
                        D _2936 = 1.525902189314365386962890625e-05 - _1825;
                        D _2967 = (_2871 + 1.5) - _2865;
                        D _2968 = dot(vec2(_2967, _2880), vec2(_2228, _2231));
                        D _2971 = _2968 + _2231;
                        D _2972 = _2887 + _2968;
                        D _2973 = _2968 + _2228;
                        vec4 _2975 = textureGatherOffset((sampler2D(ShadowMaps[_1419 + 0u], View_SharedPointClampedSampler)), vec2(_2875, _2876), ivec2(2, 0));
                        D _2976 = _2975.x;
                        D _2977 = _2975.y;
                        D _2978 = _2975.z;
                        D _2979 = _2975.w;
                        D _3045 = (_2872 + 1.5) - _2868;
                        D _3046 = dot(vec2(_2879, _3045), vec2(_2228, _2231));
                        D _3049 = _3046 + _2231;
                        D _3050 = _2887 + _3046;
                        D _3051 = _3046 + _2228;
                        vec4 _3053 = textureGatherOffset((sampler2D(ShadowMaps[_1419 + 0u], View_SharedPointClampedSampler)), vec2(_2875, _2876), ivec2(0, 2));
                        D _3054 = _3053.x;
                        D _3055 = _3053.y;
                        D _3056 = _3053.z;
                        D _3057 = _3053.w;
                        D _3122 = dot(vec2(_2967, _3045), vec2(_2228, _2231));
                        D _3125 = _3122 + _2231;
                        D _3126 = _2887 + _3122;
                        D _3127 = _3122 + _2228;
                        vec4 _3129 = textureGatherOffset((sampler2D(ShadowMaps[_1419 + 0u], View_SharedPointClampedSampler)), vec2(_2875, _2876), ivec2(2));
                        D _3130 = _3129.x;
                        D _3131 = _3129.y;
                        D _3132 = _3129.z;
                        D _3133 = _3129.w;
                        D _3198 = 1.0 - _2873;
                        vec4 _3221 = vec4((((((_2899 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2936 + _2899) + (spvNMin(abs(_2881), 0.0) * D(int(uint(_2881 > 0.0) - uint(_2881 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3198) + ((_2898 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2936 + _2898) + (spvNMin(abs(_2889), 0.0) * D(int(uint(_2889 > 0.0) - uint(_2889 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2979 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2936 + _2979) + (spvNMin(abs(_2968), 0.0) * D(int(uint(_2968 > 0.0) - uint(_2968 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2978 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2936 + _2978) + (spvNMin(abs(_2973), 0.0) * D(int(uint(_2973 > 0.0) - uint(_2973 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2873), (((((_2896 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2936 + _2896) + (spvNMin(abs(_2884), 0.0) * D(int(uint(_2884 > 0.0) - uint(_2884 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3198) + ((_2897 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2936 + _2897) + (spvNMin(abs(_2888), 0.0) * D(int(uint(_2888 > 0.0) - uint(_2888 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2976 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2936 + _2976) + (spvNMin(abs(_2971), 0.0) * D(int(uint(_2971 > 0.0) - uint(_2971 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2977 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2936 + _2977) + (spvNMin(abs(_2972), 0.0) * D(int(uint(_2972 > 0.0) - uint(_2972 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2873), (((((_3057 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2936 + _3057) + (spvNMin(abs(_3046), 0.0) * D(int(uint(_3046 > 0.0) - uint(_3046 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3198) + ((_3056 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2936 + _3056) + (spvNMin(abs(_3051), 0.0) * D(int(uint(_3051 > 0.0) - uint(_3051 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3133 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2936 + _3133) + (spvNMin(abs(_3122), 0.0) * D(int(uint(_3122 > 0.0) - uint(_3122 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3132 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2936 + _3132) + (spvNMin(abs(_3127), 0.0) * D(int(uint(_3127 > 0.0) - uint(_3127 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2873), (((((_3054 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2936 + _3054) + (spvNMin(abs(_3049), 0.0) * D(int(uint(_3049 > 0.0) - uint(_3049 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3198) + ((_3055 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2936 + _3055) + (spvNMin(abs(_3050), 0.0) * D(int(uint(_3050 > 0.0) - uint(_3050 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3130 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2936 + _3130) + (spvNMin(abs(_3125), 0.0) * D(int(uint(_3125 > 0.0) - uint(_3125 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3131 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2936 + _3131) + (spvNMin(abs(_3126), 0.0) * D(int(uint(_3126 > 0.0) - uint(_3126 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2873));
                        _1255 = dot(_3221, vec4(1.0 - _2874, 1.0, 1.0, _2874)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        _1255 = 1.0;
                    }
                    if (_1838)
                    {
                        _1254 = _1255;
                        break;
                    }
                }
            }
            if (floatBitsToUint(TranslucentBasePass_2._m0[30u]).y == 0u)
            {
                _1254 = 1.0;
                break;
            }
            D _1295 = fma(_238, TranslucentBasePass_2._m0[35u].z, fma(_237, TranslucentBasePass_2._m0[34u].z, TranslucentBasePass_2._m0[33u].z * _236)) + TranslucentBasePass_2._m0[36u].z;
            D _1299 = fma(_238, TranslucentBasePass_2._m0[35u].w, fma(_237, TranslucentBasePass_2._m0[34u].w, TranslucentBasePass_2._m0[33u].w * _236)) + TranslucentBasePass_2._m0[36u].w;
            D _1300 = (fma(_238, TranslucentBasePass_2._m0[35u].x, fma(_237, TranslucentBasePass_2._m0[34u].x, TranslucentBasePass_2._m0[33u].x * _236)) + TranslucentBasePass_2._m0[36u].x) / _1299;
            D _1301 = (fma(_238, TranslucentBasePass_2._m0[35u].y, fma(_237, TranslucentBasePass_2._m0[34u].y, TranslucentBasePass_2._m0[33u].y * _236)) + TranslucentBasePass_2._m0[36u].y) / _1299;
            uvec4 _1305 = floatBitsToUint(TranslucentBasePass_2._m0[32u]);
            uint _1306 = _1305.x;
            uint _1307 = _1305.y;
            uint _1308 = _1305.z;
            uint _1313 = uint(int(floor(_1300)));
            uint _1314 = uint(int((-0.0) - floor(_1301)));
            if (!((int(_1314) < int(_1305.w)) && ((int(_1313) < int(_1308)) && ((int(_1313) >= int(_1306)) && (int(_1314) >= int(_1307))))))
            {
                _1254 = 1.0;
                break;
            }
            D _1382 = dFdyFine(_1300);
            D _1383 = dFdyFine(_1301);
            D _1384 = dFdyFine(_1295);
            D _1385 = dFdxFine(_1300);
            D _1386 = dFdxFine(_1301);
            D _1387 = dFdxFine(_1295);
            D _1390 = (_1386 * _1384) - (_1387 * _1383);
            D _1393 = (_1387 * _1382) - (_1385 * _1384);
            D _1396 = (_1385 * _1383) - (_1386 * _1382);
            D _1407 = 1.0 / spvNMax(abs(_1396), sqrt(((_1393 * _1393) + (_1396 * _1396)) + (_1390 * _1390)) * 0.100000001490116119384765625);
            D _1413 = D(int(uint(_1396 > 0.0) - uint(_1396 < 0.0)));
            D _1697;
            D _1699;
            if (dot(vec2(_1390, _1393), vec2(_1390, _1393)) < 1.0000000195414813782625560981111e-24)
            {
                _1697 = 0.0;
                _1699 = 0.0;
            }
            else
            {
                D _1763 = (-0.0) - _1390;
                D _1764 = (-0.0) - _1393;
                D _1768 = inversesqrt(dot(vec2(_1763, _1764), vec2(_1763, _1764)));
                _1697 = _1768 * _1763;
                _1699 = _1768 * _1764;
            }
            D _1705 = _272 + (-0.5);
            D _1713 = (((_1699 * _1705) + (_1697 * _271)) * 2.0) + (_1697 * 0.5);
            D _1714 = (((_1699 * _271) + (_1697 * _1705)) * 2.0) + (_1699 * 0.5);
            D _1720 = _1713 + (fract(_1300) * 256.0);
            D _1721 = _1714 + (fract(_1301) * 256.0);
            D _1734 = dot(vec2((floor(_1720) + 0.5) - _1720, (floor(_1721) + 0.5) - _1721), vec2(((_1390 * 256.0) * _1407) * _1413, ((_1393 * 256.0) * _1407) * _1413));
            D _1740 = (_1713 * 0.00390625) + _1300;
            D _1741 = (_1714 * 0.00390625) + _1301;
            uint _1753 = ((uint(int((-0.0) - floor(_1741))) - _1307) * (_1308 - _1306)) + (uint(int(floor(_1740))) - _1306);
            D _2167;
            D _2170;
            if ((texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowLoadedTileData, int(_1753 >> 5u)).x & (1u << (_1753 & 31u))) == 0u)
            {
                _2167 = 3.0000000054977557577780399428115e+38;
                _2170 = 0.0;
            }
            else
            {
                uvec4 _2192 = uvec4(texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileIndices, int(_1753)));
                uint _2193 = _2192.x;
                D frontier_phi_53_54_ladder;
                D frontier_phi_53_54_ladder_1;
                if (int(_2193) > int(4294967295u))
                {
                    uint _2839 = (uint(floor(fract(_1740) * 256.0)) + (_2193 << 16u)) + (uint(floor(fract(_1741) * 256.0)) << 8u);
                    uvec4 _2842 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileData, int(_2839 >> 1u));
                    uint _2843 = _2842.x;
                    D _2851 = D((((_2839 & 1u) == 0u) ? _2843 : (_2843 >> 16u)) & 65535u) * 1.525902189314365386962890625e-05;
                    D frontier_phi_53_54_ladder_75_ladder;
                    D frontier_phi_53_54_ladder_75_ladder_1;
                    if (_2851 != 1.0)
                    {
                        vec4 _3652 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthRanges, int(_2193));
                        D _3654 = _3652.y;
                        frontier_phi_53_54_ladder_75_ladder = 1.0 / _3654;
                        frontier_phi_53_54_ladder_75_ladder_1 = (_3654 * _2851) + _3652.x;
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
                _2167 = frontier_phi_53_54_ladder_1;
                _2170 = frontier_phi_53_54_ladder;
            }
            _1254 = spvNClamp(((((1.525902189314365386962890625e-05 - _1295) + _2167) + (spvNMin(abs(_1734), _2170 * 10.0) * D(int(uint(_1734 > 0.0) - uint(_1734 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0);
            break;
        }
        D _1369;
        if ((floatBitsToUint(Primitive._m0[27u]).z & 2u) == 0u)
        {
            _1369 = 1.0;
        }
        else
        {
            _1369 = View._m0[188u].y;
        }
        uvec4 _1373 = floatBitsToUint(View._m0[220u]);
        uint _1374 = _1373.y;
        uint _1377 = (_1374 != 1u) ? 4294967295u : 0u;
        uint _1695;
        if (_1374 > 1u)
        {
            D _137[4];
            _137[0u] = 0.0;
            _137[1u] = 0.0;
            _137[2u] = 0.0;
            _137[3u] = 0.0;
            uint _2152 = 0u;
            bool _2158;
            for (;;)
            {
                _2158 = _2152 < floatBitsToUint(View._m0[220u]).y;
                if (_2158)
                {
                    uint _2790 = _2152 + 237u;
                    D _2804 = View._m0[_2790].x - View._m0[75u].x;
                    D _2805 = View._m0[_2790].y - View._m0[75u].y;
                    D _2806 = View._m0[_2790].z - View._m0[75u].z;
                    D _2807 = dot(vec3(_2804, _2805, _2806), vec3(_244, _245, _246));
                    D _2814 = dot(vec3(_2804, _2805, _2806), vec3(_2804, _2805, _2806)) - (View._m0[_2790].w * View._m0[_2790].w);
                    D _2816 = (_2807 * _2807) - _2814;
                    D _3428;
                    if ((_2814 < 0.0) && (!(_2816 < 0.0)))
                    {
                        D _3422 = sqrt(_2816);
                        _3428 = spvNMin(abs(_3422 + _2807), abs(_2807 - _3422));
                    }
                    else
                    {
                        _3428 = 0.0;
                    }
                    _137[_2152] = _3428;
                }
                uint _2153 = _2152 + 1u;
                if (_2153 == 4u)
                {
                    break;
                }
                else
                {
                    _2152 = _2153;
                    continue;
                }
            }
            D _3439 = (_271 * 0.99989998340606689453125) * dot(vec4(_137[0u], _137[1u], _137[2u], _137[3u]), vec4(1.0));
            uint frontier_phi_34_85_ladder;
            if (_137[0u] > _3439)
            {
                frontier_phi_34_85_ladder = 0u;
            }
            else
            {
                D _3790 = _137[1u] + _137[0u];
                uint frontier_phi_34_85_ladder_96_ladder;
                if (_3790 > _3439)
                {
                    frontier_phi_34_85_ladder_96_ladder = 1u;
                }
                else
                {
                    D _3874 = _3790 + _137[2u];
                    uint frontier_phi_34_85_ladder_96_ladder_104_ladder;
                    if (_3874 > _3439)
                    {
                        frontier_phi_34_85_ladder_96_ladder_104_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_34_85_ladder_96_ladder_104_ladder_110_ladder;
                        if ((_3874 + _137[3u]) > _3439)
                        {
                            frontier_phi_34_85_ladder_96_ladder_104_ladder_110_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_34_85_ladder_96_ladder_104_ladder_110_ladder = _1377;
                        }
                        frontier_phi_34_85_ladder_96_ladder_104_ladder = frontier_phi_34_85_ladder_96_ladder_104_ladder_110_ladder;
                    }
                    frontier_phi_34_85_ladder_96_ladder = frontier_phi_34_85_ladder_96_ladder_104_ladder;
                }
                frontier_phi_34_85_ladder = frontier_phi_34_85_ladder_96_ladder;
            }
            _1695 = frontier_phi_34_85_ladder;
        }
        else
        {
            _1695 = _1377;
        }
        D _2159;
        if (_1695 == 4294967295u)
        {
            _2159 = _1369;
        }
        else
        {
            _2159 = View._m0[_1695 + 241u].x * _1369;
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
        if (_2159 > 0.0)
        {
            D _2823 = spvNClamp((TranslucentBasePass_2._m0[7u].x * _109) + TranslucentBasePass_2._m0[7u].y, 0.0, 1.0);
            D _2827 = ((_2823 * _2823) * (1.0 - _1254)) + _1254;
            D frontier_phi_5_51_ladder_74_ladder;
            D frontier_phi_5_51_ladder_74_ladder_1;
            D frontier_phi_5_51_ladder_74_ladder_2;
            D frontier_phi_5_51_ladder_74_ladder_3;
            D frontier_phi_5_51_ladder_74_ladder_4;
            D frontier_phi_5_51_ladder_74_ladder_5;
            D frontier_phi_5_51_ladder_74_ladder_6;
            D frontier_phi_5_51_ladder_74_ladder_7;
            D frontier_phi_5_51_ladder_74_ladder_8;
            if (_2827 > 0.0)
            {
                D _3441 = dot(vec3(_453, _454, _455), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3444 = spvNMax(0.0, _3441);
                D _3445 = dot(vec3(_247, _249, _250), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3451 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3445 * 2.0) + 2.0));
                D _3454 = spvNClamp(_3451 * (_570 + _3441), 0.0, 1.0);
                D _3469 = sqrt(spvNMax(0.0, 1.0 - ((1.0 - (_570 * _570)) * 0.444444477558135986328125)));
                D _3473 = (_576 * 0.666666686534881591796875) - (_3469 * _453);
                D _3474 = (_577 * 0.666666686534881591796875) - (_3469 * _454);
                D _3475 = (_578 * 0.666666686534881591796875) - (_3469 * _455);
                D _3479 = inversesqrt(dot(vec3(_3473, _3474, _3475), vec3(_3473, _3474, _3475)));
                D _3486 = dot(vec3((-0.0) - (_3479 * _3473), (-0.0) - (_3479 * _3474), (-0.0) - (_3479 * _3475)), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3489 = _674 * _674;
                D _3490 = _3489 * _3489;
                D _3494 = ((_3454 * _3454) * (_3490 + (-1.0))) + 1.0;
                D _3500 = (_3444 * 2.0) * _596;
                D _3505 = 1.0 - spvNMax(9.9999997473787516355514526367188e-06, spvNMin(_3451 * (_3445 + 1.0), 1.0));
                D _3506 = _3505 * _3505;
                D _3508 = (_3506 * _3506) * _3505;
                D _3513 = spvNMin(dot(vec3(_554, _555, _556), vec3(16.666667938232421875)), 1.0);
                D _3526 = spvNMax(0.039999999105930328369140625, _674);
                D _3539 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_3526 * _3444) + 0.02669160068035125732421875) / (_3444 + 0.4664950072765350341796875)) * exp2(((1.0 / _3526) * _3444) * log2(_3526)), 0.0, 1.0));
                D _3540 = 1.0 - _3444;
                D _3541 = _3540 * _3540;
                D _3553 = ((_3541 * _3541) * _3540) * exp2(log2((exp2((_3526 * 4.7702999114990234375) * log2(_3444)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _3526);
                D _3556 = (1.0 / _3539) * (1.0 - _3539);
                D _3560 = (_3556 * _554) + 1.0;
                D _3561 = (_3556 * _555) + 1.0;
                D _3562 = (_3556 * _556) + 1.0;
                D _3563 = _3539 - _3553;
                D _3577 = spvNClamp(1.0 - dot(vec3(_3560 * ((_3563 * _554) + _3553), _3561 * ((_3563 * _555) + _3553), _3562 * ((_3563 * _556) + _3553)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                D _3580 = (((_3490 * 0.3183098733425140380859375) * _3444) * (1.0 / (_3494 * _3494))) * (0.5 / ((_3489 * ((_596 + _3444) - _3500)) + _3500));
                D _3581 = _3444 * 0.3183098733425140380859375;
                D _3584 = ((_3486 * _3486) + 1.0) * 0.05968309938907623291015625;
                D _3586 = spvNMin(1.0, _479);
                D _3588 = (_479 + 1.0) - _3586;
                D _3589 = _3588 * _3588;
                D _3592 = 1.0 - ((_3589 * _3589) * _3588);
                D _3593 = _3592 * _3592;
                D _3598 = ((_3593 * _3593) * (_3592 * (_479 - _3586))) + _3586;
                D _3601 = sqrt(spvNMax(0.0, 1.0 - _3598));
                D _3606 = 1.0 - spvNClamp((_674 * 3.5) + (-0.5), 0.0, 1.0);
                D _3607 = _3606 * _3606;
                D _3617 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_705 * _3601) * spvNClamp(1.0 - ((_3607 * _3607) * _3606), 0.0, 1.0))) * _3444, 0.0, 1.0);
                D _3622 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _3601)) * _3444, 0.0, 1.0);
                D _3624 = spvNMin(_2827, _3617 * _3617);
                D _3625 = spvNMin(_2827, _3622 * _3622);
                D _3626 = spvNMin(_2827, _3598);
                D _3627 = _2159 * TranslucentBasePass_2._m0[4u].x;
                D _3628 = _2159 * TranslucentBasePass_2._m0[4u].y;
                D _3629 = _2159 * TranslucentBasePass_2._m0[4u].z;
                frontier_phi_5_51_ladder_74_ladder = (_3584 * _3629) * _3626;
                frontier_phi_5_51_ladder_74_ladder_1 = (((_3627 * _506) * _3581) * _3577) * _3625;
                frontier_phi_5_51_ladder_74_ladder_2 = (((_3628 * _507) * _3581) * _3577) * _3625;
                frontier_phi_5_51_ladder_74_ladder_3 = (((_3629 * _508) * _3581) * _3577) * _3625;
                frontier_phi_5_51_ladder_74_ladder_4 = (((_3580 * _3627) * spvNClamp(((_3513 - _554) * _3508) + _554, 0.0, 1.0)) * _3560) * _3624;
                frontier_phi_5_51_ladder_74_ladder_5 = (((_3580 * _3628) * spvNClamp(((_3513 - _555) * _3508) + _555, 0.0, 1.0)) * _3561) * _3624;
                frontier_phi_5_51_ladder_74_ladder_6 = (((_3580 * _3629) * spvNClamp(((_3513 - _556) * _3508) + _556, 0.0, 1.0)) * _3562) * _3624;
                frontier_phi_5_51_ladder_74_ladder_7 = (_3584 * _3627) * _3626;
                frontier_phi_5_51_ladder_74_ladder_8 = (_3584 * _3628) * _3626;
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
        _806 = frontier_phi_5_51_ladder_1;
        _808 = frontier_phi_5_51_ladder_2;
        _810 = frontier_phi_5_51_ladder_3;
        _812 = frontier_phi_5_51_ladder_4;
        _814 = frontier_phi_5_51_ladder_5;
        _816 = frontier_phi_5_51_ladder_6;
        _818 = frontier_phi_5_51_ladder_7;
        _820 = frontier_phi_5_51_ladder_8;
        _822 = frontier_phi_5_51_ladder;
    }
    uvec4 _826 = floatBitsToUint(TranslucentBasePass_2._m0[0u]);
    uint _827 = _826.x;
    uint _832 = min(min(texelFetch(TranslucentBasePass_Shared_Forward_NumCulledLightsGrid, int(0u)).x, _827), _827);
    D _839;
    D _841;
    D _843;
    D _845;
    D _847;
    D _849;
    D _851;
    D _853;
    D _855;
    D _857;
    D _859;
    D _861;
    D _863;
    D _865;
    D _867;
    if (_832 == 0u)
    {
        _839 = _806;
        _841 = _808;
        _843 = _810;
        _845 = _812;
        _847 = _814;
        _849 = _816;
        _851 = _818;
        _853 = _820;
        _855 = _822;
        _857 = 0.0;
        _859 = 0.0;
        _861 = 0.0;
        _863 = 0.0;
        _865 = 0.0;
        _867 = 0.0;
    }
    else
    {
        D _840;
        D _842;
        D _844;
        D _846;
        D _848;
        D _850;
        D _852;
        D _854;
        D _856;
        D _858;
        D _860;
        D _862;
        D _864;
        D _866;
        D _868;
        D _1170 = _806;
        D _1171 = _808;
        D _1172 = _810;
        D _1173 = _812;
        D _1174 = _814;
        D _1175 = _816;
        D _1176 = _818;
        D _1177 = _820;
        D _1178 = _822;
        D _1179 = 0.0;
        D _1180 = 0.0;
        D _1181 = 0.0;
        D _1182 = 0.0;
        D _1183 = 0.0;
        D _1184 = 0.0;
        uint _1185 = 0u;
        D _1189;
        D _1190;
        D _1191;
        D _1192;
        D _1194;
        D _1195;
        D _1196;
        D _1198;
        D _1199;
        D _1200;
        uint _1202;
        D _1204;
        D _1205;
        D _1207;
        D _1208;
        D _1209;
        D _1211;
        D _1212;
        uint _1214;
        D _1216;
        D _1217;
        D _1218;
        D _1219;
        uint _1222;
        D _1224;
        D _1225;
        D _1226;
        D _1227;
        D _1230;
        D _1231;
        D _1232;
        D _1233;
        D _1236;
        D _1237;
        D _1238;
        D _1239;
        D _1242;
        D _1243;
        D _1244;
        D _1245;
        bool _1248;
        bool _1249;
        bool _1253;
        for (;;)
        {
            vec4 _1188 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(0u));
            _1189 = _1188.x;
            _1190 = _1188.y;
            _1191 = _1188.z;
            _1192 = _1188.w;
            vec4 _1193 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(1u));
            _1194 = _1193.x;
            _1195 = _1193.y;
            _1196 = _1193.z;
            vec4 _1197 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(2u));
            _1198 = _1197.x;
            _1199 = _1197.y;
            _1200 = _1197.z;
            _1202 = floatBitsToUint(_1197.w);
            vec4 _1203 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(3u));
            _1204 = _1203.x;
            _1205 = _1203.y;
            vec4 _1206 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(4u));
            _1207 = _1206.x;
            _1208 = _1206.y;
            _1209 = _1206.z;
            vec4 _1210 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(5u));
            _1211 = _1210.x;
            _1212 = _1210.y;
            _1214 = floatBitsToUint(_1210.z);
            vec4 _1215 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(6u));
            _1216 = _1215.x;
            _1217 = _1215.y;
            _1218 = _1215.z;
            _1219 = _1215.w;
            _1222 = floatBitsToUint(texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(7u)).x);
            vec4 _1223 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(8u));
            _1224 = _1223.x;
            _1225 = _1223.y;
            _1226 = _1223.z;
            _1227 = _1223.w;
            vec4 _1229 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(9u));
            _1230 = _1229.x;
            _1231 = _1229.y;
            _1232 = _1229.z;
            _1233 = _1229.w;
            vec4 _1235 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(10u));
            _1236 = _1235.x;
            _1237 = _1235.y;
            _1238 = _1235.z;
            _1239 = _1235.w;
            vec4 _1241 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(11u));
            _1242 = _1241.x;
            _1243 = _1241.y;
            _1244 = _1241.z;
            _1245 = _1241.w;
            _1248 = (_1202 & 131072u) != 0u;
            _1249 = _1204 > (-2.0);
            _1253 = (_1202 & 16384u) == 0u;
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
            if (_1253)
            {
                D _1648;
                if (_1248)
                {
                    uint _1613 = _1222 + 0u;
                    uvec2 _1616 = uvec2(textureSize(ShadowMaps[(_1613)], int(0u)));
                    D _1618 = D(int(_1616.x));
                    D _1620 = D(int(_1616.y));
                    D _1621 = 1.0 / _1618;
                    D _1622 = 1.0 / _1620;
                    D _1634 = fma(_238, _1238, fma(_237, _1232, _1226 * _236)) + _1244;
                    D _1638 = fma(_238, _1239, fma(_237, _1233, _1227 * _236)) + _1245;
                    D _1639 = (fma(_238, _1236, fma(_237, _1230, _1224 * _236)) + _1242) / _1638;
                    D _1640 = (fma(_238, _1237, fma(_237, _1231, _1225 * _236)) + _1243) / _1638;
                    D frontier_phi_30_29_ladder;
                    if ((_1640 <= _1219) && ((_1639 <= _1218) && ((_1639 >= _1216) && (_1640 >= _1217))))
                    {
                        D _2036 = dFdyFine(_1639);
                        D _2037 = dFdyFine(_1640);
                        D _2038 = dFdyFine(_1634);
                        D _2039 = dFdxFine(_1639);
                        D _2040 = dFdxFine(_1640);
                        D _2041 = dFdxFine(_1634);
                        D _2044 = (_2040 * _2038) - (_2041 * _2037);
                        D _2047 = (_2041 * _2036) - (_2039 * _2038);
                        D _2050 = (_2039 * _2037) - (_2040 * _2036);
                        D _2060 = 1.0 / spvNMax(abs(_2050), sqrt(((_2047 * _2047) + (_2050 * _2050)) + (_2044 * _2044)) * 0.100000001490116119384765625);
                        D _2066 = D(int(uint(_2050 > 0.0) - uint(_2050 < 0.0)));
                        D _2067 = _2044 * _1621;
                        D _2069 = (_2067 * _2060) * _2066;
                        D _2070 = _2047 * _1622;
                        D _2072 = (_2070 * _2060) * _2066;
                        D _2385;
                        D _2387;
                        if (dot(vec2(_2044, _2047), vec2(_2044, _2047)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2385 = 0.0;
                            _2387 = 0.0;
                        }
                        else
                        {
                            D _2728 = (-0.0) - _2044;
                            D _2729 = (-0.0) - _2047;
                            D _2733 = inversesqrt(dot(vec2(_2728, _2729), vec2(_2728, _2729)));
                            _2385 = _2733 * _2728;
                            _2387 = _2733 * _2729;
                        }
                        D _2389 = _272 + (-0.5);
                        D _2394 = _271 + 0.5;
                        D _2397 = ((_2387 * _2389) + (_1639 * _1618)) + (_2385 * _2394);
                        D _2400 = ((_2385 * _2389) + (_1640 * _1620)) + (_2387 * _2394);
                        D _2401 = _2397 + (-0.5);
                        D _2402 = _2400 + (-0.5);
                        D _2403 = trunc(_2401);
                        D _2404 = trunc(_2402);
                        D _2405 = _2401 - _2403;
                        D _2406 = _2402 - _2404;
                        D _2407 = _2403 * _1621;
                        D _2408 = _2404 * _1622;
                        D _2411 = (_2403 + (-0.5)) - _2397;
                        D _2412 = (_2404 + (-0.5)) - _2400;
                        D _2413 = dot(vec2(_2411, _2412), vec2(_2069, _2072));
                        D _2416 = _2413 + _2072;
                        D _2419 = _2066 * (_2060 * (_2070 + _2067));
                        D _2420 = _2419 + _2413;
                        D _2421 = _2413 + _2069;
                        vec4 _2425 = textureGather((sampler2D(ShadowMaps[_1613], View_SharedPointClampedSampler)), vec2(_2407, _2408));
                        D _2466 = 1.525902189314365386962890625e-05 - _1634;
                        D _2489 = (_2403 + 1.5) - _2397;
                        D _2490 = dot(vec2(_2489, _2412), vec2(_2069, _2072));
                        D _2493 = _2490 + _2072;
                        D _2494 = _2419 + _2490;
                        D _2495 = _2490 + _2069;
                        vec4 _2499 = textureGatherOffset((sampler2D(ShadowMaps[_1613], View_SharedPointClampedSampler)), vec2(_2407, _2408), ivec2(2, 0));
                        D _2563 = (_2404 + 1.5) - _2400;
                        D _2564 = dot(vec2(_2411, _2563), vec2(_2069, _2072));
                        D _2567 = _2564 + _2072;
                        D _2568 = _2419 + _2564;
                        D _2569 = _2564 + _2069;
                        vec4 _2571 = textureGatherOffset((sampler2D(ShadowMaps[_1613], View_SharedPointClampedSampler)), vec2(_2407, _2408), ivec2(0, 2));
                        D _2633 = dot(vec2(_2489, _2563), vec2(_2069, _2072));
                        D _2636 = _2633 + _2072;
                        D _2637 = _2419 + _2633;
                        D _2638 = _2633 + _2069;
                        vec4 _2640 = textureGatherOffset((sampler2D(ShadowMaps[_1613], View_SharedPointClampedSampler)), vec2(_2407, _2408), ivec2(2));
                        D _2702 = 1.0 - _2405;
                        vec4 _2725 = vec4((((spvNClamp((((_2466 + _2425.w) + (spvNMin(abs(_2413), 0.0) * D(int(uint(_2413 > 0.0) - uint(_2413 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2702) + spvNClamp((((_2466 + _2425.z) + (spvNMin(abs(_2421), 0.0) * D(int(uint(_2421 > 0.0) - uint(_2421 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2466 + _2499.w) + (spvNMin(abs(_2490), 0.0) * D(int(uint(_2490 > 0.0) - uint(_2490 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2466 + _2499.z) + (spvNMin(abs(_2495), 0.0) * D(int(uint(_2495 > 0.0) - uint(_2495 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2405), (((spvNClamp((((_2466 + _2425.x) + (spvNMin(abs(_2416), 0.0) * D(int(uint(_2416 > 0.0) - uint(_2416 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2702) + spvNClamp((((_2466 + _2425.y) + (spvNMin(abs(_2420), 0.0) * D(int(uint(_2420 > 0.0) - uint(_2420 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2466 + _2499.x) + (spvNMin(abs(_2493), 0.0) * D(int(uint(_2493 > 0.0) - uint(_2493 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2466 + _2499.y) + (spvNMin(abs(_2494), 0.0) * D(int(uint(_2494 > 0.0) - uint(_2494 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2405), (((spvNClamp((((_2466 + _2571.w) + (spvNMin(abs(_2564), 0.0) * D(int(uint(_2564 > 0.0) - uint(_2564 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2702) + spvNClamp((((_2466 + _2571.z) + (spvNMin(abs(_2569), 0.0) * D(int(uint(_2569 > 0.0) - uint(_2569 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2466 + _2640.w) + (spvNMin(abs(_2633), 0.0) * D(int(uint(_2633 > 0.0) - uint(_2633 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2466 + _2640.z) + (spvNMin(abs(_2638), 0.0) * D(int(uint(_2638 > 0.0) - uint(_2638 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2405), (((spvNClamp((((_2466 + _2571.x) + (spvNMin(abs(_2567), 0.0) * D(int(uint(_2567 > 0.0) - uint(_2567 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2702) + spvNClamp((((_2466 + _2571.y) + (spvNMin(abs(_2568), 0.0) * D(int(uint(_2568 > 0.0) - uint(_2568 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2466 + _2640.x) + (spvNMin(abs(_2636), 0.0) * D(int(uint(_2636 > 0.0) - uint(_2636 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2466 + _2640.y) + (spvNMin(abs(_2637), 0.0) * D(int(uint(_2637 > 0.0) - uint(_2637 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2405));
                        frontier_phi_30_29_ladder = dot(_2725, vec4(1.0 - _2406, 1.0, 1.0, _2406)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        frontier_phi_30_29_ladder = 1.0;
                    }
                    _1648 = frontier_phi_30_29_ladder;
                }
                else
                {
                    _1648 = 1.0;
                }
                D _1654 = _1189 - _236;
                D _1655 = _1190 - _237;
                D _1656 = _1191 - _238;
                D _1657 = dot(vec3(_1654, _1655, _1656), vec3(_1654, _1655, _1656));
                D _2081;
                D _2082;
                D _2083;
                if (_1657 > 9.9999997473787516355514526367188e-05)
                {
                    D _2077 = inversesqrt(_1657);
                    _2081 = _2077 * _1654;
                    _2082 = _2077 * _1655;
                    _2083 = _2077 * _1656;
                }
                else
                {
                    _2081 = 0.0;
                    _2082 = 0.0;
                    _2083 = 0.0;
                }
                D _2084 = _1211 * _1211;
                D _2088 = (_1192 * _1192) * _1657;
                D _2091 = spvNClamp(1.0 - (_2088 * _2088), 0.0, 1.0);
                D _2741;
                if (_1249)
                {
                    D _2739 = spvNClamp((dot(vec3(_2081, _2082, _2083), vec3(_1198, _1199, _1200)) - _1204) * _1205, 0.0, 1.0);
                    _2741 = _2739 * _2739;
                }
                else
                {
                    _2741 = 1.0;
                }
                D _2742 = ((_2091 * _2091) * D(_1657 >= _2084)) * _2741;
                D _3285;
                D _3287;
                D _3289;
                if ((_1202 & 262144u) == 0u)
                {
                    _3285 = 1.0;
                    _3287 = 1.0;
                    _3289 = 1.0;
                }
                else
                {
                    D _3292 = (-0.0) - _1199;
                    D _3293 = (-0.0) - _1200;
                    D _3294 = (-0.0) - _1198;
                    D _3304 = (-0.0) - _2081;
                    D _3305 = (-0.0) - _2082;
                    D _3306 = (-0.0) - _2083;
                    D _3309 = fma(_3293, _3306, fma(_3292, _3305, _2081 * _1198));
                    D _3312 = fma(_1209, _3306, fma(_1208, _3305, _1207 * _3304));
                    D _3320 = atan(((-0.0) - _3312) / ((-0.0) - _3309));
                    bool _3325 = _3309 > (-0.0);
                    bool _3326 = _3309 == (-0.0);
                    bool _3327 = _3312 <= (-0.0);
                    bool _3328 = _3312 > (-0.0);
                    vec4 _3350 = texture((sampler2D(ForwardLightProfileTextures[_1214 + 0u], View_SharedBilinearWrappedSampler)), vec2(fract((_3326 && _3327) ? 1.25 : ((_3326 && _3328) ? 0.75 : ((((_3325 && _3328) ? (_3320 + (-3.1415927410125732421875)) : ((_3325 && _3327) ? (_3320 + 3.1415927410125732421875) : _3320)) * 0.15915493667125701904296875) + 1.0))), (asin((-0.0) - fma((_1208 * _3294) - (_1207 * _3292), _3306, fma((_1207 * _3293) - (_1209 * _3294), _3305, ((_1209 * _3292) - (_1208 * _3293)) * _3304))) * 0.3183098733425140380859375) + 0.5));
                    _3285 = _3350.x;
                    _3287 = _3350.y;
                    _3289 = _3350.z;
                }
                D _3741;
                D _3743;
                D _3745;
                D _3747;
                D _3749;
                D _3751;
                D _3753;
                D _3755;
                D _3757;
                for (;;)
                {
                    if (_2742 > 0.0)
                    {
                        D _3866;
                        if (_1248)
                        {
                            if (!(_1648 > 0.0))
                            {
                                _3741 = 0.0;
                                _3743 = 0.0;
                                _3745 = 0.0;
                                _3747 = 0.0;
                                _3749 = 0.0;
                                _3751 = 0.0;
                                _3753 = 0.0;
                                _3755 = 0.0;
                                _3757 = 0.0;
                                break;
                            }
                            _3866 = _1648;
                        }
                        else
                        {
                            _3866 = 1.0;
                        }
                        D _3868 = spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1657));
                        D _3869 = 1.0 / _3868;
                        D _3870 = dot(vec3(_453, _454, _455), vec3(_2081, _2082, _2083));
                        D _3891;
                        if (_1211 > 0.0)
                        {
                            D _3888 = sqrt(spvNClamp(_2084 * _3869, 0.0, 1.0));
                            D frontier_phi_109_108_ladder;
                            if (_3888 > spvNMax(9.9999997473787516355514526367188e-06, _3870))
                            {
                                D _3910 = spvNMax((-0.0) - _3888, _3870) + _3888;
                                frontier_phi_109_108_ladder = (_3910 * _3910) * (0.25 / _3888);
                            }
                            else
                            {
                                frontier_phi_109_108_ladder = _3870;
                            }
                            _3891 = frontier_phi_109_108_ladder;
                        }
                        else
                        {
                            _3891 = _3870;
                        }
                        D _3953;
                        D _3954;
                        D _3893;
                        D _3895;
                        D _3899;
                        D _3900;
                        bool _3903;
                        for (;;)
                        {
                            _3893 = spvNMax(0.0, _3891);
                            _3895 = _674 * _674;
                            _3899 = spvNClamp(((1.0 - _3895) * _1211) * inversesqrt(_3868), 0.0, 1.0);
                            _3900 = dot(vec3(_247, _249, _250), vec3(_2081, _2082, _2083));
                            _3903 = _3899 > 0.0;
                            D _3921;
                            D _3923;
                            if (_3903)
                            {
                                D _3916 = sqrt(spvNMax(0.0, 1.0 - (_3899 * _3899)));
                                D _3919 = ((_3870 * 2.0) * _570) - _3900;
                                if (!(!(_3919 >= _3916)))
                                {
                                    _3953 = _582;
                                    _3954 = 1.0;
                                    break;
                                }
                                D _3941 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, 1.0 - (_3919 * _3919))) * _3899;
                                _3921 = (_3941 * ((((_570 * _570) * 2.0) + (-1.0)) - (_3919 * _3900))) + (_3916 * _3900);
                                _3923 = (_3941 * (_570 - (_3919 * _3870))) + (_3916 * _3870);
                            }
                            else
                            {
                                _3921 = _3900;
                                _3923 = _3870;
                            }
                            D _3928 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3921 * 2.0) + 2.0));
                            _3953 = spvNMin(_3928 * (_3921 + 1.0), 1.0);
                            _3954 = spvNClamp(_3928 * (_3923 + _570), 0.0, 1.0);
                            break;
                        }
                        D _3955 = spvNMax(9.9999997473787516355514526367188e-06, _3953);
                        D _3964 = sqrt(spvNMax(0.0, 1.0 - ((1.0 - (_570 * _570)) * 0.444444477558135986328125)));
                        D _3968 = (_576 * 0.666666686534881591796875) - (_3964 * _453);
                        D _3969 = (_577 * 0.666666686534881591796875) - (_3964 * _454);
                        D _3970 = (_578 * 0.666666686534881591796875) - (_3964 * _455);
                        D _3974 = inversesqrt(dot(vec3(_3968, _3969, _3970), vec3(_3968, _3969, _3970)));
                        D _3981 = dot(vec3((-0.0) - (_3974 * _3968), (-0.0) - (_3974 * _3969), (-0.0) - (_3974 * _3970)), vec3(_2081, _2082, _2083));
                        D _3984 = _3895 * _3895;
                        D _3998 = ((_3954 * _3954) * (_3984 + (-1.0))) + 1.0;
                        D _4004 = (_3893 * 2.0) * _596;
                        D _4009 = 1.0 - _3955;
                        D _4010 = _4009 * _4009;
                        D _4012 = (_4010 * _4010) * _4009;
                        D _4016 = spvNMin(dot(vec3(_554, _555, _556), vec3(16.666667938232421875)), 1.0);
                        D _4029 = spvNMax(0.039999999105930328369140625, _674);
                        D _4042 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_4029 * _3893) + 0.02669160068035125732421875) / (_3893 + 0.4664950072765350341796875)) * exp2(((1.0 / _4029) * _3893) * log2(_4029)), 0.0, 1.0));
                        D _4043 = 1.0 - _3893;
                        D _4044 = _4043 * _4043;
                        D _4056 = ((_4044 * _4044) * _4043) * exp2(log2((exp2((_4029 * 4.7702999114990234375) * log2(_3893)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _4029);
                        D _4059 = (1.0 / _4042) * (1.0 - _4042);
                        D _4063 = (_4059 * _554) + 1.0;
                        D _4064 = (_4059 * _555) + 1.0;
                        D _4065 = (_4059 * _556) + 1.0;
                        D _4066 = _4042 - _4056;
                        D _4080 = spvNClamp(1.0 - dot(vec3(_4063 * ((_4066 * _554) + _4056), _4064 * ((_4066 * _555) + _4056), _4065 * ((_4066 * _556) + _4056)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                        D _4084 = ((((_3984 * 0.3183098733425140380859375) * _3893) * (1.0 / (_3998 * _3998))) * (_3903 ? ((1.0 / ((((_3899 * 0.25) * (_3899 + (_3895 * 3.0))) * (1.0 / _3955)) + _3984)) * _3984) : 1.0)) * (0.5 / ((_3895 * ((_596 + _3893) - _4004)) + _4004));
                        D _4085 = _3893 * 0.3183098733425140380859375;
                        D _4088 = ((_3981 * _3981) + 1.0) * 0.05968309938907623291015625;
                        D _4089 = spvNMin(1.0, _479);
                        D _4091 = (_479 + 1.0) - _4089;
                        D _4092 = _4091 * _4091;
                        D _4095 = 1.0 - ((_4092 * _4092) * _4091);
                        D _4096 = _4095 * _4095;
                        D _4101 = ((_4096 * _4096) * (_4095 * (_479 - _4089))) + _4089;
                        D _4104 = sqrt(spvNMax(0.0, 1.0 - _4101));
                        D _4108 = 1.0 - spvNClamp((_674 * 3.5) + (-0.5), 0.0, 1.0);
                        D _4109 = _4108 * _4108;
                        D _4119 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_705 * _4104) * spvNClamp(1.0 - ((_4109 * _4109) * _4108), 0.0, 1.0))) * _3893, 0.0, 1.0);
                        D _4124 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _4104)) * _3893, 0.0, 1.0);
                        D _4126 = spvNMin(_3866, _4119 * _4119);
                        D _4127 = spvNMin(_3866, _4124 * _4124);
                        D _4128 = spvNMin(_3866, _4101);
                        D _4132 = (_2742 * _1194) * _3285;
                        D _4133 = (_2742 * _1195) * _3287;
                        D _4134 = (_2742 * _1196) * _3289;
                        D _4135 = _3869 * _4132;
                        D _4139 = _3869 * _4133;
                        D _4143 = _3869 * _4134;
                        _3741 = ((((_4132 * _506) * _3869) * _4085) * _4080) * _4127;
                        _3743 = ((((_4133 * _507) * _3869) * _4085) * _4080) * _4127;
                        _3745 = ((((_4134 * _508) * _3869) * _4085) * _4080) * _4127;
                        _3747 = (((_4135 * spvNClamp(((_4016 - _554) * _4012) + _554, 0.0, 1.0)) * _4084) * _4063) * _4126;
                        _3749 = (((_4139 * _4084) * spvNClamp(((_4016 - _555) * _4012) + _555, 0.0, 1.0)) * _4064) * _4126;
                        _3751 = (((_4143 * _4084) * spvNClamp(((_4016 - _556) * _4012) + _556, 0.0, 1.0)) * _4065) * _4126;
                        _3753 = (_4135 * _4088) * _4128;
                        _3755 = (_4139 * _4088) * _4128;
                        _3757 = (_4143 * _4088) * _4128;
                        break;
                    }
                    else
                    {
                        _3741 = 0.0;
                        _3743 = 0.0;
                        _3745 = 0.0;
                        _3747 = 0.0;
                        _3749 = 0.0;
                        _3751 = 0.0;
                        _3753 = 0.0;
                        _3755 = 0.0;
                        _3757 = 0.0;
                        break;
                    }
                }
                frontier_phi_49_pred = _1180;
                frontier_phi_49_pred_1 = _3741 + _1170;
                frontier_phi_49_pred_2 = _3743 + _1171;
                frontier_phi_49_pred_3 = _3745 + _1172;
                frontier_phi_49_pred_4 = _3747 + _1173;
                frontier_phi_49_pred_5 = _3749 + _1174;
                frontier_phi_49_pred_6 = _3751 + _1175;
                frontier_phi_49_pred_7 = _3753 + _1176;
                frontier_phi_49_pred_8 = _3755 + _1177;
                frontier_phi_49_pred_9 = _3757 + _1178;
                frontier_phi_49_pred_10 = _1179;
                frontier_phi_49_pred_11 = _1181;
                frontier_phi_49_pred_12 = _1182;
                frontier_phi_49_pred_13 = _1183;
                frontier_phi_49_pred_14 = _1184;
            }
            else
            {
                D _1352 = _1189 - _236;
                D _1353 = _1190 - _237;
                D _1354 = _1191 - _238;
                D _1355 = dot(vec3(_1352, _1353, _1354), vec3(_1352, _1353, _1354));
                D _1359 = (_1192 * _1192) * _1355;
                D _1360 = _1359 * _1359;
                D _1361 = _1360 * _1360;
                D _1364 = spvNClamp(1.0 - (_1361 * _1361), 0.0, 1.0);
                D _1365 = _1364 * _1364;
                D _1366 = _1365 * _1365;
                D _1367 = _1366 * _1366;
                D _1672;
                D _1674;
                D _1676;
                D _1678;
                D _1680;
                D _1682;
                if (_1367 > 0.0)
                {
                    D _1664 = dot(vec3(_244, _245, _246), vec3(_453, _454, _455)) * 2.0;
                    D _1668 = _244 - (_1664 * _453);
                    D _1669 = _245 - (_1664 * _454);
                    D _1670 = _246 - (_1664 * _455);
                    D _3352;
                    D _3353;
                    D _3354;
                    D _3355;
                    D _3356;
                    D _3357;
                    D _3358;
                    D _3359;
                    D _3360;
                    D _3361;
                    D _3362;
                    if (_1212 == 0.0)
                    {
                        D _2747;
                        D _2748;
                        D _2749;
                        if (_1355 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2743 = inversesqrt(_1355);
                            _2747 = _2743 * _1352;
                            _2748 = _2743 * _1353;
                            _2749 = _2743 * _1354;
                        }
                        else
                        {
                            _2747 = 0.0;
                            _2748 = 0.0;
                            _2749 = 0.0;
                        }
                        D _2752 = 1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1355));
                        _3352 = _2752;
                        _3353 = (_1211 * _1211) * _2752;
                        _3354 = _2747;
                        _3355 = _2748;
                        _3356 = _2749;
                        _3357 = _2747;
                        _3358 = _2748;
                        _3359 = _2749;
                        _3360 = _2747;
                        _3361 = _2748;
                        _3362 = _2749;
                    }
                    else
                    {
                        D _2095 = _1212 * 0.5;
                        D _2096 = _2095 * _1198;
                        D _2097 = _2095 * _1199;
                        D _2098 = _2095 * _1200;
                        D _2099 = _1352 - _2096;
                        D _2100 = _1353 - _2097;
                        D _2101 = _1354 - _2098;
                        D _2102 = _2096 + _1352;
                        D _2103 = _2097 + _1353;
                        D _2104 = _2098 + _1354;
                        D _2112 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2099, _2100, _2101), vec3(_2099, _2100, _2101))));
                        D _2114 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2102, _2103, _2104), vec3(_2102, _2103, _2104))));
                        D _2115 = _2114 * _2112;
                        D _2131 = (1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(_2115, ((dot(vec3(_2099, _2100, _2101), vec3(_2102, _2103, _2104)) * 0.5) * _2115) + 0.5))) * _2115;
                        D _2133 = (_1198 * 2.0) * _2095;
                        D _2135 = (_1199 * 2.0) * _2095;
                        D _2137 = (_1200 * 2.0) * _2095;
                        D _2138 = dot(vec3(_2133, _2135, _2137), vec3(_2133, _2135, _2137));
                        D _2785;
                        D _2786;
                        D _2787;
                        if (_2138 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2755 = dot(vec3(_1668, _1669, _1670), vec3(_2133, _2135, _2137));
                            D _2771 = spvNClamp((1.0 / (_2138 - (_2755 * _2755))) * dot(vec3(_2099, _2100, _2101), vec3((_2755 * _1668) - _2133, (_2755 * _1669) - _2135, (_2755 * _1670) - _2137)), 0.0, 1.0);
                            D _2775 = (_2771 * _2133) + _2099;
                            D _2776 = (_2771 * _2135) + _2100;
                            D _2777 = (_2771 * _2137) + _2101;
                            D _2781 = inversesqrt(dot(vec3(_2775, _2776, _2777), vec3(_2775, _2776, _2777)));
                            _2785 = _2775 * _2781;
                            _2786 = _2776 * _2781;
                            _2787 = _2777 * _2781;
                        }
                        else
                        {
                            _2785 = _2099;
                            _2786 = _2100;
                            _2787 = _2101;
                        }
                        _3352 = _2131;
                        _3353 = (_1211 * _1211) * _2131;
                        _3354 = _2112 * _2099;
                        _3355 = _2112 * _2100;
                        _3356 = _2112 * _2101;
                        _3357 = _2114 * _2102;
                        _3358 = _2114 * _2103;
                        _3359 = _2114 * _2104;
                        _3360 = _2785;
                        _3361 = _2786;
                        _3362 = _2787;
                    }
                    D _3372 = _3353 + 1.0;
                    D _3377 = _3360 - _244;
                    D _3378 = _3361 - _245;
                    D _3379 = _3362 - _246;
                    D _3383 = inversesqrt(dot(vec3(_3377, _3378, _3379), vec3(_3377, _3378, _3379)));
                    D _3384 = _3383 * _3377;
                    D _3385 = _3383 * _3378;
                    D _3386 = _3383 * _3379;
                    D _3393 = spvNClamp(dot(vec3(_453, _454, _455), vec3(_3384, _3385, _3386)), 0.0, 1.0);
                    D _3394 = _674 * _674;
                    D _3400 = spvNClamp(((1.0 - _3394) * _1211) * sqrt(_3352), 0.0, 1.0);
                    D _3414 = exp2(log2(spvNClamp((((_3400 * 0.25) * (_3400 + (_3394 * 3.0))) * (1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_247, _249, _250), vec3(_3384, _3385, _3386))))) + (_3394 * _3394), 0.0, 1.0)) * 0.25);
                    D _3418 = spvNClamp(dot(vec3(_3354, _3355, _3356), vec3(_3357, _3358, _3359)), 0.0, 1.0);
                    D _3420 = _3414 * _3414;
                    D _3421 = _3420 * _3420;
                    D _3773;
                    if (_3418 < 1.0)
                    {
                        D _3764 = sqrt(spvNClamp((1.0 / (_3418 + 1.0)) * (1.0 - _3418), 0.0, 1.0));
                        _3773 = (1.0 / spvNClamp(((_3764 * 0.25) * (_3764 + (_3420 * 3.0))) + _3421, 0.0, 1.0)) * _3421;
                    }
                    else
                    {
                        _3773 = 1.0;
                    }
                    D _3777 = ((_3393 * _3393) * (_3421 + (-1.0))) + 1.0;
                    D _3780 = spvNMax(0.0, (((dot(vec3(_453, _454, _455), vec3(_3357, _3358, _3359)) + dot(vec3(_453, _454, _455), vec3(_3354, _3355, _3356))) * 0.5) + _3353) * (1.0 / (_3372 * _3372))) * 0.3183098733425140380859375;
                    D _3783 = ((_3780 * _3421) * _3773) * (1.0 / (_3777 * _3777));
                    D _3785 = (_1367 * _1194) * _3352;
                    D _3787 = (_1367 * _1195) * _3352;
                    D _3789 = (_1367 * _1196) * _3352;
                    _1672 = _3783 * _3785;
                    _1674 = _3783 * _3787;
                    _1676 = _3783 * _3789;
                    _1678 = _3780 * _3785;
                    _1680 = _3780 * _3787;
                    _1682 = _3780 * _3789;
                }
                else
                {
                    _1672 = 0.0;
                    _1674 = 0.0;
                    _1676 = 0.0;
                    _1678 = 0.0;
                    _1680 = 0.0;
                    _1682 = 0.0;
                }
                frontier_phi_49_pred = _1674 + _1180;
                frontier_phi_49_pred_1 = _1170;
                frontier_phi_49_pred_2 = _1171;
                frontier_phi_49_pred_3 = _1172;
                frontier_phi_49_pred_4 = _1173;
                frontier_phi_49_pred_5 = _1174;
                frontier_phi_49_pred_6 = _1175;
                frontier_phi_49_pred_7 = _1176;
                frontier_phi_49_pred_8 = _1177;
                frontier_phi_49_pred_9 = _1178;
                frontier_phi_49_pred_10 = _1672 + _1179;
                frontier_phi_49_pred_11 = _1676 + _1181;
                frontier_phi_49_pred_12 = _1678 + _1182;
                frontier_phi_49_pred_13 = _1680 + _1183;
                frontier_phi_49_pred_14 = _1682 + _1184;
            }
            _860 = frontier_phi_49_pred;
            _840 = frontier_phi_49_pred_1;
            _842 = frontier_phi_49_pred_2;
            _844 = frontier_phi_49_pred_3;
            _846 = frontier_phi_49_pred_4;
            _848 = frontier_phi_49_pred_5;
            _850 = frontier_phi_49_pred_6;
            _852 = frontier_phi_49_pred_7;
            _854 = frontier_phi_49_pred_8;
            _856 = frontier_phi_49_pred_9;
            _858 = frontier_phi_49_pred_10;
            _862 = frontier_phi_49_pred_11;
            _864 = frontier_phi_49_pred_12;
            _866 = frontier_phi_49_pred_13;
            _868 = frontier_phi_49_pred_14;
            uint _1186 = _1185 + 1u;
            if (_1186 == _832)
            {
                break;
            }
            else
            {
                _1170 = _840;
                _1171 = _842;
                _1172 = _844;
                _1173 = _846;
                _1174 = _848;
                _1175 = _850;
                _1176 = _852;
                _1177 = _854;
                _1178 = _856;
                _1179 = _858;
                _1180 = _860;
                _1181 = _862;
                _1182 = _864;
                _1183 = _866;
                _1184 = _868;
                _1185 = _1186;
                continue;
            }
        }
        _839 = _840;
        _841 = _842;
        _843 = _844;
        _845 = _846;
        _847 = _848;
        _849 = _850;
        _851 = _852;
        _853 = _854;
        _855 = _856;
        _857 = _858;
        _859 = _860;
        _861 = _862;
        _863 = _864;
        _865 = _866;
        _867 = _868;
    }
    vec4 _909 = textureLod(sampler3D(TranslucentBasePass_TranslucencyLightingVolumeEnvironmentA, View_SharedBilinearClampedSampler), vec3((_236 - View._m0[180u].x) * View._m0[182u].x, (_237 - View._m0[180u].y) * View._m0[182u].y, (_238 - View._m0[180u].z) * View._m0[182u].z), 0.0);
    D _933;
    D _934;
    D _935;
    if (_389 < 1.0)
    {
        _933 = _366.x / ((_411 / _388) + 1.0);
        _934 = _366.y / ((_412 / _388) + 1.0);
        _935 = _366.z / ((_413 / _388) + 1.0);
    }
    else
    {
        _933 = 0.0;
        _934 = 0.0;
        _935 = 0.0;
    }
    D _951 = spvNClamp(_656, 0.0, 1.0);
    D _964 = _504 * _504;
    D _965 = _964 * _504;
    D _972 = ((_453 - _593) * _965) + _593;
    D _973 = ((_454 - _594) * _965) + _594;
    D _974 = ((_455 - _595) * _965) + _595;
    D _978 = inversesqrt(dot(vec3(_972, _973, _974), vec3(_972, _973, _974)));
    D _987 = 10.0 / spvNMax(9.9999997473787516355514526367188e-06, _964);
    D _1016 = fma(_235, View._m0[2u].x, fma(_234, View._m0[1u].x, View._m0[0u].x * _233)) + View._m0[3u].x;
    D _1020 = fma(_235, View._m0[2u].y, fma(_234, View._m0[1u].y, View._m0[0u].y * _233)) + View._m0[3u].y;
    D _1024 = fma(_235, View._m0[2u].z, fma(_234, View._m0[1u].z, View._m0[0u].z * _233)) + View._m0[3u].z;
    D _1028 = fma(_235, View._m0[2u].w, fma(_234, View._m0[1u].w, View._m0[0u].w * _233)) + View._m0[3u].w;
    D _1035 = ((_972 * _109) * _978) + _233;
    D _1036 = ((_973 * _109) * _978) + _234;
    D _1037 = ((_974 * _109) * _978) + _235;
    D _1070 = 1.0 / _1028;
    D _1071 = _1070 * _1016;
    D _1072 = _1070 * _1020;
    D _1076 = (_1070 * _1024) + (0.0500000007450580596923828125 / _1028);
    D _1077 = 1.0 / (fma(_1037, View._m0[2u].w, fma(_1036, View._m0[1u].w, View._m0[0u].w * _1035)) + View._m0[3u].w);
    D _1088 = 1.0 / ((View._m0[36u].w * _987) + _1028);
    D _1091 = (_1077 * (fma(_1037, View._m0[2u].x, fma(_1036, View._m0[1u].x, View._m0[0u].x * _1035)) + View._m0[3u].x)) - _1071;
    D _1092 = (_1077 * (fma(_1037, View._m0[2u].y, fma(_1036, View._m0[1u].y, View._m0[0u].y * _1035)) + View._m0[3u].y)) - _1072;
    D _1094 = (_1088 * ((View._m0[36u].x * _987) + _1016)) - _1071;
    D _1095 = (_1088 * ((View._m0[36u].y * _987) + _1020)) - _1072;
    D _1100 = sqrt((_1091 * _1091) + (_1092 * _1092)) * 0.5;
    D _1119 = spvNMin(1.0 - (spvNMax(0.0, abs((_1100 * _1071) + _1091) - _1100) / abs(_1091)), 1.0 - (spvNMax(0.0, abs((_1100 * _1072) + _1092) - _1100) / abs(_1092))) / _1100;
    D _1120 = _1119 * _1091;
    D _1121 = _1119 * _1092;
    D _1122 = _1119 * ((_1077 * (fma(_1037, View._m0[2u].z, fma(_1036, View._m0[1u].z, View._m0[0u].z * _1035)) + View._m0[3u].z)) - _1076);
    uvec2 _1128 = uvec2(textureSize(TranslucentBasePass_HZBTexture, int(0u)));
    D _1130 = D(int(_1128.x));
    D _1132 = D(int(_1128.y));
    uint _1153 = max(1u, min(uint(ceil((spvNClamp((1.0 / spvNMax(9.9999997473787516355514526367188e-05, sqrt((_1120 * _1120) + (_1121 * _1121)))) * sqrt((_1094 * _1094) + (_1095 * _1095)), 0.0, 1.0) * 8.0) + _271)), 8u));
    D _1158 = ((_1071 * 0.5) + 0.5) * TranslucentBasePass_2._m0[198u].x;
    D _1159 = (0.5 - (_1072 * 0.5)) * TranslucentBasePass_2._m0[198u].y;
    D _1162 = (TranslucentBasePass_2._m0[198u].x * 0.0625) * _1120;
    D _1165 = (TranslucentBasePass_2._m0[198u].y * (-0.0625)) * _1121;
    D _1166 = _1122 * 0.125;
    D _1168 = spvNMax(abs(_1122), _1076 - ((1.0 / (fma(_109, View._m0[38u].w, 0.0) + _1028)) * (fma(_109, View._m0[38u].z, 0.0) + _1024))) * 0.125;
    D _1335;
    D _1337;
    D _1339;
    D _1341;
    if (_1153 == 0u)
    {
        _1335 = 0.0;
        _1337 = 0.0;
        _1339 = 0.0;
        _1341 = 0.0;
    }
    else
    {
        D frontier_phi_62;
        D frontier_phi_62_1;
        D frontier_phi_62_2;
        D frontier_phi_62_3;
        D _1585 = 0.0;
        uint _1587 = 0u;
        D _1586;
        D _1589;
        bool _1612;
        for (;;)
        {
            _1589 = D(_1587);
            D _1590 = _1589 + _271;
            vec4 _1604 = texelFetch(TranslucentBasePass_HZBTexture, ivec2_(uvec2(uint(int(floor(((_1590 * _1162) + _1158) * _1130))), uint(int(floor(((_1590 * _1165) + _1159) * _1132))))), int(0u));
            D _1606 = _1604.x;
            _1586 = ((_1590 * _1166) + _1076) - _1606;
            _1612 = (abs(((-0.0) - _1168) - _1586) < _1168) && (_1606 != 0.0);
            if (_1612)
            {
                D _2021 = (_1587 == 0u) ? (_1586 - _1166) : _1585;
                D _2028 = abs(((_271 + (-1.0)) + _1589) + spvNClamp(_2021 / (_2021 - _1586), 0.0, 1.0));
                D _2033 = spvNMin(_2028 * 0.125, 1.0);
                frontier_phi_62 = 1.0 - (_2033 * _2033);
                frontier_phi_62_1 = (_2028 * _1166) + _1076;
                frontier_phi_62_2 = (_2028 * _1165) + _1159;
                frontier_phi_62_3 = (_2028 * _1162) + _1158;
                break;
            }
            else
            {
                uint _1588 = _1587 + 1u;
                if (_1588 < _1153)
                {
                    _1585 = _1586;
                    _1587 = _1588;
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
        _1335 = frontier_phi_62_3;
        _1337 = frontier_phi_62_2;
        _1339 = frontier_phi_62_1;
        _1341 = frontier_phi_62;
    }
    D _1349 = (spvNClamp(_1335 * TranslucentBasePass_2._m0[198u].z, 0.0, 1.0) * 2.0) + (-1.0);
    D _1350 = 1.0 - (spvNClamp(_1337 * TranslucentBasePass_2._m0[198u].w, 0.0, 1.0) * 2.0);
    D _1490;
    D _1492;
    D _1494;
    D _1496;
    if (_1341 > 0.0)
    {
        D _1491;
        D _1493;
        D _1495;
        D _2237;
        D _1483;
        bool _1489;
        for (;;)
        {
            D _1442 = ((View._m0[73u].x * _1339) + View._m0[73u].y) + (1.0 / ((View._m0[73u].z * _1339) - View._m0[73u].w));
            D _1466 = _1442 * _1349;
            D _1467 = _1442 * _1350;
            D _1478 = (_233 - View._m0[63u].x) - fma(_1442, View._m0[62u].x, fma(_1467, View._m0[61u].x, _1466 * View._m0[60u].x));
            D _1480 = (_234 - View._m0[63u].y) - fma(_1442, View._m0[62u].y, fma(_1467, View._m0[61u].y, _1466 * View._m0[60u].y));
            D _1482 = (_235 - View._m0[63u].z) - fma(_1442, View._m0[62u].z, fma(_1467, View._m0[61u].z, _1466 * View._m0[60u].z));
            _1483 = dot(vec3(_1478, _1480, _1482), vec3(_1478, _1480, _1482));
            _1489 = View._m0[175u].w != 0.0;
            if (_1489)
            {
                if (floatBitsToUint(View._m0[175u]).y == 0u)
                {
                    _1491 = 0.0;
                    _1493 = 0.0;
                    _1495 = 0.0;
                    _2237 = 0.0;
                    break;
                }
            }
            D _1879 = fma(_1339, View._m0[140u].w, fma(_1350, View._m0[139u].w, View._m0[138u].w * _1349)) + View._m0[141u].w;
            D _1880 = (fma(_1339, View._m0[140u].x, fma(_1350, View._m0[139u].x, View._m0[138u].x * _1349)) + View._m0[141u].x) / _1879;
            D _1881 = (fma(_1339, View._m0[140u].y, fma(_1350, View._m0[139u].y, View._m0[138u].y * _1349)) + View._m0[141u].y) / _1879;
            D _1898 = spvNClamp((abs((spvNMin(spvNMax(_1880, -1.0), 1.0) - _1349) * 0.5) * 5.0) + (-4.0), 0.0, 1.0);
            D _1899 = spvNClamp((abs((spvNMin(spvNMax(_1881, -1.0), 1.0) - _1350) * 0.5) * 5.0) + (-4.0), 0.0, 1.0);
            uvec2 _1952 = uvec2(textureSize(TranslucentBasePass_PrevSceneColor, int(0u)));
            vec4 _1973 = texelFetch(TranslucentBasePass_PrevSceneColor, ivec2_(uvec2(uint(min(int(uint(max(int(uint(int(D(int(_1952.x)) * ((TranslucentBasePass_2._m0[199u].x * spvNMin(spvNMax(_1880 - ((D(int(uint(_1880 > 0.0) - uint(_1880 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1880) + (-1.0))), -1.0), 1.0)) + TranslucentBasePass_2._m0[199u].z)))), int(uint(int(TranslucentBasePass_2._m0[200u].x)))))), int(uint(int(TranslucentBasePass_2._m0[200u].x + TranslucentBasePass_2._m0[200u].z)) + 4294967295u))), uint(min(int(uint(max(int(uint(int(D(int(_1952.y)) * ((TranslucentBasePass_2._m0[199u].y * spvNMin(spvNMax(_1881 - ((D(int(uint(_1881 > 0.0) - uint(_1881 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1881) + (-1.0))), -1.0), 1.0)) + TranslucentBasePass_2._m0[199u].w)))), int(uint(int(TranslucentBasePass_2._m0[200u].y)))))), int(uint(int(TranslucentBasePass_2._m0[200u].y + TranslucentBasePass_2._m0[200u].w)) + 4294967295u))))), int(0u));
            _1491 = View._m0[165u].x * spvNMin(_1973.x, 65504.0);
            _1493 = View._m0[165u].x * spvNMin(_1973.y, 65504.0);
            _1495 = View._m0[165u].x * spvNMin(_1973.z, 65504.0);
            _2237 = spvNMax(0.0, 1.0 - dot(vec2(_1898, _1899), vec2(_1898, _1899)));
            break;
        }
        _1490 = _1491;
        _1492 = _1493;
        _1494 = _1495;
        _1496 = (_2237 * _1341) * spvNClamp(1.0 / spvNMax(9.9999997473787516355514526367188e-06, (_964 * _964) * _1483), 0.0, 1.0);
    }
    else
    {
        _1490 = 0.0;
        _1492 = 0.0;
        _1494 = 0.0;
        _1496 = 0.0;
    }
    D _1530 = fma(_238, View._m0[14u].w, fma(_237, View._m0[13u].w, _236 * View._m0[12u].w)) + View._m0[15u].w;
    D _1535 = (((fma(_238, View._m0[14u].x, fma(_237, View._m0[13u].x, _236 * View._m0[12u].x)) + View._m0[15u].x) / _1530) * 0.5) + 0.5;
    D _1536 = 0.5 - (((fma(_238, View._m0[14u].y, fma(_237, View._m0[13u].y, _236 * View._m0[12u].y)) + View._m0[15u].y) / _1530) * 0.5);
    D _1565 = sqrt(((_234 * _234) + (_233 * _233)) + (_235 * _235));
    D _1583 = spvNMax(0.0, ((1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_233, _234, _235), vec3(View._m0[68u].xyz())))) * _1565) * View._m0[280u].w);
    D _1989;
    D _1991;
    D _1993;
    D _1995;
    D _1997;
    D _1999;
    if (_1565 < _1583)
    {
        _1989 = 0.0;
        _1991 = 0.0;
        _1993 = 0.0;
        _1995 = 1.0;
        _1997 = 1.0;
        _1999 = 1.0;
    }
    else
    {
        D _2007 = (1.0 / _1565) * _1583;
        uvec4 _2014 = floatBitsToUint(View._m0[220u]);
        uint _2015 = _2014.y;
        uint _2017 = (_2015 != 1u) ? 4294967295u : 0u;
        uint _2383;
        if (_2015 > 1u)
        {
            D _138[4];
            _138[0u] = 0.0;
            _138[1u] = 0.0;
            _138[2u] = 0.0;
            _138[3u] = 0.0;
            uint _3229 = 0u;
            bool _3235;
            for (;;)
            {
                _3235 = _3229 < floatBitsToUint(View._m0[220u]).y;
                if (_3235)
                {
                    uint _3656 = _3229 + 237u;
                    D _3668 = View._m0[_3656].x - View._m0[75u].x;
                    D _3669 = View._m0[_3656].y - View._m0[75u].y;
                    D _3670 = View._m0[_3656].z - View._m0[75u].z;
                    D _3671 = dot(vec3(_3668, _3669, _3670), vec3(_244, _245, _246));
                    D _3678 = dot(vec3(_3668, _3669, _3670), vec3(_3668, _3669, _3670)) - (View._m0[_3656].w * View._m0[_3656].w);
                    D _3680 = (_3671 * _3671) - _3678;
                    D _3798;
                    if ((_3678 < 0.0) && (!(_3680 < 0.0)))
                    {
                        D _3792 = sqrt(_3680);
                        _3798 = spvNMin(abs(_3792 + _3671), abs(_3671 - _3792));
                    }
                    else
                    {
                        _3798 = 0.0;
                    }
                    _138[_3229] = _3798;
                }
                uint _3230 = _3229 + 1u;
                if (_3230 == 4u)
                {
                    break;
                }
                else
                {
                    _3229 = _3230;
                    continue;
                }
            }
            D _3808 = (_271 * 0.99989998340606689453125) * dot(vec4(_138[0u], _138[1u], _138[2u], _138[3u]), vec4(1.0));
            uint frontier_phi_61_99_ladder;
            if (_138[0u] > _3808)
            {
                frontier_phi_61_99_ladder = 0u;
            }
            else
            {
                D _3876 = _138[1u] + _138[0u];
                uint frontier_phi_61_99_ladder_105_ladder;
                if (_3876 > _3808)
                {
                    frontier_phi_61_99_ladder_105_ladder = 1u;
                }
                else
                {
                    D _3906 = _3876 + _138[2u];
                    uint frontier_phi_61_99_ladder_105_ladder_111_ladder;
                    if (_3906 > _3808)
                    {
                        frontier_phi_61_99_ladder_105_ladder_111_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_61_99_ladder_105_ladder_111_ladder_116_ladder;
                        if ((_3906 + _138[3u]) > _3808)
                        {
                            frontier_phi_61_99_ladder_105_ladder_111_ladder_116_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_61_99_ladder_105_ladder_111_ladder_116_ladder = _2017;
                        }
                        frontier_phi_61_99_ladder_105_ladder_111_ladder = frontier_phi_61_99_ladder_105_ladder_111_ladder_116_ladder;
                    }
                    frontier_phi_61_99_ladder_105_ladder = frontier_phi_61_99_ladder_105_ladder_111_ladder;
                }
                frontier_phi_61_99_ladder = frontier_phi_61_99_ladder_105_ladder;
            }
            _2383 = frontier_phi_61_99_ladder;
        }
        else
        {
            _2383 = _2017;
        }
        D frontier_phi_40_61_ladder;
        D frontier_phi_40_61_ladder_1;
        D frontier_phi_40_61_ladder_2;
        D frontier_phi_40_61_ladder_3;
        D frontier_phi_40_61_ladder_4;
        D frontier_phi_40_61_ladder_5;
        if (_2383 == 4294967295u)
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
            uint _3236 = _2383 + 221u;
            D _3244 = spvNMin(View._m0[_3236].w, 0.9900000095367431640625);
            uint _3245 = _2383 + 225u;
            uint _3252 = _2383 + 229u;
            uint _3259 = _2383 + 233u;
            uint _3264 = _2383 + 241u;
            D _3711;
            D _3712;
            D _3713;
            if (TranslucentBasePass_2._m0[146u].x > 0.0)
            {
                vec4 _3703 = textureLod(sampler2D(TranslucentBasePass_Shared_Fog_FarIntegratedScatteringTexture, View_SharedBilinearClampedSampler), vec2(spvNMin(spvNMax(View._m0[278u].x * _1535, View._m0[279u].x), View._m0[280u].x), spvNMin(spvNMax(View._m0[278u].y * _1536, View._m0[279u].y), View._m0[280u].y)), 0.0);
                _3711 = View._m0[164u].z * _3703.x;
                _3712 = View._m0[164u].z * _3703.y;
                _3713 = View._m0[164u].z * _3703.z;
            }
            else
            {
                _3711 = 0.0;
                _3712 = 0.0;
                _3713 = 0.0;
            }
            D _3717 = dot(vec3((-0.0) - View._m0[218u].x, (-0.0) - View._m0[218u].y, (-0.0) - View._m0[218u].z), vec3(_247, _249, _250));
            D _3730 = (((_3717 * _3717) + 1.0) * 0.0397887341678142547607421875) * exp2(log2(spvNMax(0.0, _3717 + 1.25)) * (-1.5));
            D _3810;
            if (View._m0[_3245].x == 0.0)
            {
                _3810 = 0.0;
            }
            else
            {
                D _3858 = (((_2007 * _235) - View._m0[_3245].z) + View._m0[75u].z) * View._m0[_3245].y;
                D _3859 = ((1.0 - _2007) * _235) * View._m0[_3245].y;
                D _3864 = exp2((-0.0) - _3858);
                D frontier_phi_100_101_ladder;
                if (abs(_3859) > 0.00999999977648258209228515625)
                {
                    frontier_phi_100_101_ladder = ((_3864 - exp2(((-0.0) - _3859) - _3858)) * View._m0[_3245].x) * (1.0 / _3859);
                }
                else
                {
                    frontier_phi_100_101_ladder = (View._m0[_3245].x * 0.693147182464599609375) * _3864;
                }
                _3810 = frontier_phi_100_101_ladder;
            }
            D _3814 = _3810 * (1.0 - _3244);
            D _3818 = (1.0 - View._m0[_3252].x) * View._m0[_3259].x;
            D _3819 = (1.0 - View._m0[_3252].y) * View._m0[_3259].x;
            D _3820 = (1.0 - View._m0[_3252].z) * View._m0[_3259].x;
            D _3821 = (-0.0) - (_1565 - _1583);
            D _3849 = 1.0 - spvNClamp(exp2(_3814 * _3821), 0.0, 1.0);
            frontier_phi_40_61_ladder = spvNClamp(exp2((_3814 + _3820) * _3821), 0.0, 1.0);
            frontier_phi_40_61_ladder_1 = spvNClamp(exp2((_3814 + _3819) * _3821), 0.0, 1.0);
            frontier_phi_40_61_ladder_2 = spvNClamp(exp2((_3814 + _3818) * _3821), 0.0, 1.0);
            frontier_phi_40_61_ladder_3 = (((_3244 * View._m0[_3236].z) * (((View._m0[219u].z * View._m0[_3264].x) * _3730) + _3713)) * spvNClamp(exp2(_3820 * _3821), 0.0, 1.0)) * _3849;
            frontier_phi_40_61_ladder_4 = (((_3244 * View._m0[_3236].y) * (((View._m0[219u].y * View._m0[_3264].x) * _3730) + _3712)) * spvNClamp(exp2(_3819 * _3821), 0.0, 1.0)) * _3849;
            frontier_phi_40_61_ladder_5 = (((_3244 * View._m0[_3236].x) * (((View._m0[219u].x * View._m0[_3264].x) * _3730) + _3711)) * spvNClamp(exp2(_3818 * _3821), 0.0, 1.0)) * _3849;
        }
        _1989 = frontier_phi_40_61_ladder_5;
        _1991 = frontier_phi_40_61_ladder_4;
        _1993 = frontier_phi_40_61_ladder_3;
        _1995 = frontier_phi_40_61_ladder_2;
        _1997 = frontier_phi_40_61_ladder_1;
        _1999 = frontier_phi_40_61_ladder;
    }
    D _2285;
    D _2286;
    D _2287;
    D _2288;
    D _2289;
    D _2290;
    if (TranslucentBasePass_2._m0[148u].x > 0.0)
    {
        D _2265 = spvNMin(spvNMax(View._m0[278u].x * _1535, View._m0[279u].x), View._m0[280u].x);
        D _2266 = spvNMin(spvNMax(View._m0[278u].y * _1536, View._m0[279u].y), View._m0[280u].y);
        D _2267 = spvNMin(spvNMax((View._m0[275u].z * spvNMax(0.0, spvNMin(View._m0[276u].z * log2((View._m0[276u].x * _1530) + View._m0[276u].y), View._m0[274u].z + (-1.0)) + 0.5)) * View._m0[278u].z, View._m0[279u].z), View._m0[280u].z);
        vec4 _2270 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeATexture, View_SharedBilinearClampedSampler), vec3(_2265, _2266, _2267), 0.0);
        vec4 _2277 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeBTexture, View_SharedBilinearClampedSampler), vec3(_2265, _2266, _2267), 0.0);
        _2285 = View._m0[164u].z * _2270.x;
        _2286 = View._m0[164u].z * _2270.y;
        _2287 = View._m0[164u].z * _2270.z;
        _2288 = _2277.x;
        _2289 = _2277.y;
        _2290 = _2277.z;
    }
    else
    {
        _2285 = 0.0;
        _2286 = 0.0;
        _2287 = 0.0;
        _2288 = 1.0;
        _2289 = 1.0;
        _2290 = 1.0;
    }
    D _2297 = spvNClamp(_570, 0.0, 1.0);
    D _2306 = ((spvNMin(_618, exp2(_2297 * (-9.27999973297119140625))) * _608) + _609) * 1.03999996185302734375;
    D _2312 = 1.0 - spvNClamp((_613 + _2306) + ((_611 - _2306) * 0.0400000028312206268310546875), 0.0, 1.0);
    D _2318 = (_2312 * _2312) * exp2(spvNMax(0.001000000047497451305389404296875, 0.300000011920928955078125 / spvNMax(0.0333333350718021392822265625, _2297)) * (-0.0291463173925876617431640625));
    D _2320 = _2318 - (_2318 * _477);
    D _2324 = (1.0 - _661) + (_661 * _477);
    D _2325 = (1.0 - _664) + (_664 * _477);
    D _2326 = (1.0 - _667) + (_667 * _477);
    D _2348 = _1995 * ((((((((((_506 * _479) * _732) * spvNMax(1.0, ((_561 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_561 * 4.79510021209716796875)) + (((_561 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _479)) * _479))) * _863) + _839) * _483) + _845) + ((((_933 * _629) * spvNClamp(1.0 - (_645 * _635), 0.0, 1.0)) * ((View._m0[164u].z * _909.x) + _851)) * _951)) + (_2320 * spvNMax(0.0, g_R.Emissive.x))) + ((_746 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1490)) + 29.8973522186279296875) * _1496) + (-29.8973522186279296875)) + _857)) * spvNClamp(_724, 0.0, 1.0)));
    D _2350 = _1997 * ((((((((((_507 * _479) * _732) * spvNMax(1.0, ((_562 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_562 * 4.79510021209716796875)) + (((_562 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _479)) * _479))) * _865) + _841) * _483) + _847) + ((((_934 * _629) * spvNClamp(1.0 - (_646 * _635), 0.0, 1.0)) * ((View._m0[164u].z * _909.y) + _853)) * _951)) + (_2320 * spvNMax(0.0, g_R.Emissive.y))) + ((_746 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1492)) + 29.8973522186279296875) * _1496) + (-29.8973522186279296875)) + _859)) * spvNClamp(_725, 0.0, 1.0)));
    D _2352 = _1999 * ((((((((((_508 * _479) * _732) * spvNMax(1.0, ((_563 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_563 * 4.79510021209716796875)) + (((_563 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _479)) * _479))) * _867) + _843) * _483) + _849) + ((((_935 * _629) * ((View._m0[164u].z * _909.z) + _855)) * spvNClamp(1.0 - (_647 * _635), 0.0, 1.0)) * _951)) + (_2320 * spvNMax(0.0, g_R.Emissive.z))) + ((_746 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1494)) + 29.8973522186279296875) * _1496) + (-29.8973522186279296875)) + _861)) * spvNClamp(_726, 0.0, 1.0)));
    SV_Target.x = View._m0[164u].y * ((((_2288 * _1989) + _2285) * _2324) + (_2348 * _2288));
    SV_Target.y = View._m0[164u].y * ((((_2289 * _1991) + _2286) * _2325) + (_2350 * _2289));
    SV_Target.z = View._m0[164u].y * ((((_2290 * _1993) + _2287) * _2326) + (_2352 * _2290));
    SV_Target.w = dot(vec3(_2324, _2325, _2326), vec3(0.2125999927520751953125, 0.715200006961822509765625, 0.072200000286102294921875));
    SV_Target_1.x = _2324;
    SV_Target_1.y = _2325;
    SV_Target_1.z = _2326;
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
} // namespace S_lass_Emissive_Thin_Wide_Character