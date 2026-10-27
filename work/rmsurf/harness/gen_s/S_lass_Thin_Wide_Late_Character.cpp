namespace S_lass_Thin_Wide_Late_Character {
using namespace cpuglsl;
static D _4323;
static D _4319;
static D _4320;
static D _4321;
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









void discard_cond(bool _4309)
{
    if (_4309)
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
    D _405 = inversesqrt(dot(vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z), vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z)));
    D _406 = _405 * g_R.Normal.x;
    D _407 = _405 * g_R.Normal.y;
    D _408 = _405 * g_R.Normal.z;
    D _411 = fma(_408, TEXCOORD_11.x, fma(_407, ((TEXCOORD_10.z * TEXCOORD_11.y) - (TEXCOORD_10.y * TEXCOORD_11.z)) * TEXCOORD_11.w, _406 * TEXCOORD_10.x));
    D _414 = fma(_408, TEXCOORD_11.y, fma(_407, ((TEXCOORD_10.x * TEXCOORD_11.z) - (TEXCOORD_10.z * TEXCOORD_11.x)) * TEXCOORD_11.w, _406 * TEXCOORD_10.y));
    D _417 = fma(_408, TEXCOORD_11.z, fma(_407, ((TEXCOORD_10.y * TEXCOORD_11.x) - (TEXCOORD_10.x * TEXCOORD_11.y)) * TEXCOORD_11.w, _406 * TEXCOORD_10.z));
    D _421 = inversesqrt(dot(vec3(_411, _414, _417), vec3(_411, _414, _417)));
    D _422 = _421 * _411;
    D _423 = _421 * _414;
    D _424 = _421 * _417;
    bool _437;
    if (Primitive._m0[27u].w > ((_262.w * 0.99609375) + 0.001953125))
    {
        _437 = ((_265 * 0.99609375) + 0.001953125) < 1.0;
    }
    else
    {
        _437 = false;
    }
    (void)((_437 ? 1.0 : (-1.0)) < 0.0);
    D _443 = spvNClamp(g_R.BaseColor.x, 0.0, 1.0);
    D _444 = spvNClamp(g_R.BaseColor.y, 0.0, 1.0);
    D _445 = spvNClamp(g_R.BaseColor.z, 0.0, 1.0);
    D _446 = spvNClamp(g_R.Metallic, 0.0, 1.0);
    D _447 = spvNClamp(g_R.Roughness, 0.0, 1.0);
    D _448 = spvNClamp(g_R.AO, 0.0, 1.0);
    D _449 = spvNClamp(g_R.Opacity, 0.0, 1.0);
    D _451 = dFdxFine(_422);
    D _452 = dFdxFine(_423);
    D _453 = dFdxFine(_424);
    D _457 = dFdyFine(_422);
    D _458 = dFdyFine(_423);
    D _459 = dFdyFine(_424);
    D _470 = sqrt(spvNClamp(spvNMin((dot(vec3(_457, _458, _459), vec3(_457, _458, _459)) + dot(vec3(_451, _452, _453), vec3(_451, _452, _453))) * 0.15915493667125701904296875, 0.180000007152557373046875) + (_447 * _447), 0.0, 1.0));
    D _471 = 1.0 - _446;
    D _472 = _471 * _443;
    D _473 = _471 * _444;
    D _474 = _471 * _445;
    D _479 = _446 * (_443 + (-0.0400000028312206268310546875));
    D _480 = _446 * (_444 + (-0.0400000028312206268310546875));
    D _481 = _446 * (_445 + (-0.0400000028312206268310546875));
    D _482 = _479 + 0.0400000028312206268310546875;
    D _484 = _480 + 0.0400000028312206268310546875;
    D _485 = _481 + 0.0400000028312206268310546875;
    D _492 = spvNClamp(D(View._m0[220u].x > 1.0), 0.0, 1.0);
    D _520 = ((exp2(log2(spvNMax(0.0, _479 + 0.020000003278255462646484375) * 1.020408153533935546875) * 1.39999997615814208984375) - _482) * _492) + _482;
    D _521 = ((exp2(log2(spvNMax(0.0, _480 + 0.020000003278255462646484375) * 1.020408153533935546875) * 1.39999997615814208984375) - _484) * _492) + _484;
    D _522 = ((exp2(log2(spvNMax(0.0, _481 + 0.020000003278255462646484375) * 1.020408153533935546875) * 1.39999997615814208984375) - _485) * _492) + _485;
    D _527 = (_520 * 0.449999988079071044921875) + _472;
    D _528 = (_521 * 0.449999988079071044921875) + _473;
    D _529 = (_522 * 0.449999988079071044921875) + _474;
    D _536 = dot(vec3(_422, _423, _424), vec3(_241, _243, _244));
    D _542 = (_536 * _422) + _238;
    D _543 = (_536 * _423) + _239;
    D _544 = (_536 * _424) + _240;
    D _548 = abs(_536);
    D _552 = (_542 * 2.0) + (_548 * _422);
    D _553 = (_543 * 2.0) + (_548 * _423);
    D _554 = (_544 * 2.0) + (_548 * _424);
    D _558 = inversesqrt(dot(vec3(_552, _553, _554), vec3(_552, _553, _554)));
    D _559 = _552 * _558;
    D _560 = _553 * _558;
    D _561 = _554 * _558;
    D _562 = spvNMax(9.9999997473787516355514526367188e-06, _548);
    D _574 = 1.0 - _470;
    D _588 = ((spvNMin(_574 * _574, exp2(_562 * (-9.27999973297119140625))) * _574) + (0.0425000004470348358154296875 - (_470 * 0.0274999998509883880615234375))) * 1.03999996185302734375;
    D _594 = 1.0 - spvNClamp((((_470 * 0.02199999988079071044921875) + (-0.039999999105930328369140625)) + _588) + (((1.03999996185302734375 - (_470 * 0.572000026702880859375)) - _588) * 0.0400000028312206268310546875), 0.0, 1.0);
    D _595 = _594 * _594;
    D _596 = spvNMax(0.001000000047497451305389404296875, (1.0 / spvNMax(0.0333333350718021392822265625, _562)) * _399.x);
    D _599 = log2(spvNMax(0.0, _369));
    D _601 = exp2(_599 * _596);
    D _605 = log2(spvNMax(0.0, exp2(_391)));
    D _606 = log2(spvNMax(0.0, exp2(_392)));
    D _607 = log2(spvNMax(0.0, exp2(_393)));
    D _611 = exp2(_605 * _596);
    D _612 = exp2(_606 * _596);
    D _613 = exp2(_607 * _596);
    D _615 = exp2(_599 * 0.001000000047497451305389404296875);
    D _622 = 1.0 - _449;
    D _624 = (_595 * _622) * _601;
    D _627 = ((_624 * _611) * _615) * exp2(_605 * 0.001000000047497451305389404296875);
    D _630 = ((_624 * _612) * _615) * exp2(_606 * 0.001000000047497451305389404296875);
    D _633 = ((_624 * _613) * _615) * exp2(_607 * 0.001000000047497451305389404296875);
    D _640 = spvNMax(0.039999999105930328369140625, _470);
    D _656 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_640 * _562) + 0.02669160068035125732421875) / (_562 + 0.4664950072765350341796875)) * exp2(((1.0 / _640) * _562) * log2(_640)), 0.0, 1.0));
    D _657 = 1.0 - _562;
    D _658 = _657 * _657;
    D _671 = _658 * _658;
    D _673 = (_671 * _657) * exp2(log2((exp2((_640 * 4.7702999114990234375) * log2(_562)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _640);
    D _676 = (1.0 / _656) * (1.0 - _656);
    D _683 = _656 - _673;
    D _690 = ((_676 * _520) + 1.0) * ((_683 * _520) + _673);
    D _691 = ((_676 * _521) + 1.0) * ((_683 * _521) + _673);
    D _692 = ((_676 * _522) + 1.0) * ((_683 * _522) + _673);
    D _698 = spvNClamp(1.0 - dot(vec3(_690, _691, _692), vec3(0.3333333432674407958984375)), 0.0, 1.0);
    D _712 = spvNClamp((_448 + (-1.0)) + exp2(log2(_562 + _448) * exp2((-1.0) - (_470 * 16.0))), 0.0, 1.0);
    D _772;
    D _774;
    D _776;
    D _778;
    D _780;
    D _782;
    D _784;
    D _786;
    D _788;
    if (floatBitsToUint(TranslucentBasePass_2._m0[0u]).z == 0u)
    {
        _772 = 0.0;
        _774 = 0.0;
        _776 = 0.0;
        _778 = 0.0;
        _780 = 0.0;
        _782 = 0.0;
        _784 = 0.0;
        _786 = 0.0;
        _788 = 0.0;
    }
    else
    {
        D _1222;
        uint _803;
        bool _804;
        for (;;)
        {
            _803 = floatBitsToUint(TranslucentBasePass_2._m0[7u]).z;
            _804 = _803 == 0u;
            if (!_804)
            {
                uint _1387;
                uint _1290 = 0u;
                for (;;)
                {
                    if (_103 < TranslucentBasePass._m0[_1290 + 32u])
                    {
                        _1387 = _1290;
                        break;
                    }
                    else
                    {
                        uint _1291 = _1290 + 1u;
                        if (_1291 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                        {
                            _1290 = _1291;
                            continue;
                        }
                        else
                        {
                            _1387 = _803;
                            break;
                        }
                    }
                }
                if (_1387 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                {
                    uint _1738 = _1387 << 2u;
                    uint _1739 = _1738 + 9u;
                    uint _1746 = _1738 + 10u;
                    uint _1753 = _1738 + 11u;
                    uint _1760 = _1738 + 12u;
                    uint _1767 = _1387 + 25u;
                    D _1793 = fma(_232, TranslucentBasePass_2._m0[_1753].z, fma(_231, TranslucentBasePass_2._m0[_1746].z, TranslucentBasePass_2._m0[_1739].z * _230)) + TranslucentBasePass_2._m0[_1760].z;
                    D _1797 = fma(_232, TranslucentBasePass_2._m0[_1753].w, fma(_231, TranslucentBasePass_2._m0[_1746].w, TranslucentBasePass_2._m0[_1739].w * _230)) + TranslucentBasePass_2._m0[_1760].w;
                    D _1798 = (fma(_232, TranslucentBasePass_2._m0[_1753].x, fma(_231, TranslucentBasePass_2._m0[_1746].x, TranslucentBasePass_2._m0[_1739].x * _230)) + TranslucentBasePass_2._m0[_1760].x) / _1797;
                    D _1799 = (fma(_232, TranslucentBasePass_2._m0[_1753].y, fma(_231, TranslucentBasePass_2._m0[_1746].y, TranslucentBasePass_2._m0[_1739].y * _230)) + TranslucentBasePass_2._m0[_1760].y) / _1797;
                    bool _1806 = (_1799 <= TranslucentBasePass_2._m0[_1767].w) && ((_1798 <= TranslucentBasePass_2._m0[_1767].z) && ((_1798 >= TranslucentBasePass_2._m0[_1767].x) && (_1799 >= TranslucentBasePass_2._m0[_1767].y)));
                    D _1223;
                    if (_1806)
                    {
                        D _2163 = dFdyFine(_1798);
                        D _2164 = dFdyFine(_1799);
                        D _2165 = dFdyFine(_1793);
                        D _2166 = dFdxFine(_1798);
                        D _2167 = dFdxFine(_1799);
                        D _2168 = dFdxFine(_1793);
                        D _2171 = (_2167 * _2165) - (_2168 * _2164);
                        D _2174 = (_2168 * _2163) - (_2166 * _2165);
                        D _2177 = (_2166 * _2164) - (_2167 * _2163);
                        D _2187 = 1.0 / spvNMax(abs(_2177), sqrt(((_2174 * _2174) + (_2177 * _2177)) + (_2171 * _2171)) * 0.100000001490116119384765625);
                        D _2193 = D(int(uint(_2177 > 0.0) - uint(_2177 < 0.0)));
                        D _2194 = _2171 * TranslucentBasePass_2._m0[29u].z;
                        D _2196 = (_2194 * _2187) * _2193;
                        D _2197 = _2174 * TranslucentBasePass_2._m0[29u].w;
                        D _2199 = (_2197 * _2187) * _2193;
                        D _2791;
                        D _2793;
                        if (dot(vec2(_2171, _2174), vec2(_2171, _2174)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2791 = 0.0;
                            _2793 = 0.0;
                        }
                        else
                        {
                            D _3161 = (-0.0) - _2171;
                            D _3162 = (-0.0) - _2174;
                            D _3166 = inversesqrt(dot(vec2(_3161, _3162), vec2(_3161, _3162)));
                            _2791 = _3166 * _3161;
                            _2793 = _3166 * _3162;
                        }
                        D _2795 = _266 + (-0.5);
                        D _2800 = _265 + 0.5;
                        D _2803 = ((_2793 * _2795) + (_1798 * TranslucentBasePass_2._m0[29u].x)) + (_2791 * _2800);
                        D _2806 = ((_2791 * _2795) + (_1799 * TranslucentBasePass_2._m0[29u].y)) + (_2793 * _2800);
                        D _2807 = _2803 + (-0.5);
                        D _2808 = _2806 + (-0.5);
                        D _2809 = trunc(_2807);
                        D _2810 = trunc(_2808);
                        D _2811 = _2807 - _2809;
                        D _2812 = _2808 - _2810;
                        D _2813 = _2809 * TranslucentBasePass_2._m0[29u].z;
                        D _2814 = _2810 * TranslucentBasePass_2._m0[29u].w;
                        D _2817 = (_2809 + (-0.5)) - _2803;
                        D _2818 = (_2810 + (-0.5)) - _2806;
                        D _2819 = dot(vec2(_2817, _2818), vec2(_2196, _2199));
                        D _2822 = _2819 + _2199;
                        D _2825 = _2193 * (_2187 * (_2197 + _2194));
                        D _2826 = _2825 + _2819;
                        D _2827 = _2819 + _2196;
                        vec4 _2833 = textureGather((sampler2D(ShadowMaps[_1387 + 0u], View_SharedPointClampedSampler)), vec2(_2813, _2814));
                        D _2834 = _2833.x;
                        D _2835 = _2833.y;
                        D _2836 = _2833.z;
                        D _2837 = _2833.w;
                        D _2874 = 1.525902189314365386962890625e-05 - _1793;
                        D _2905 = (_2809 + 1.5) - _2803;
                        D _2906 = dot(vec2(_2905, _2818), vec2(_2196, _2199));
                        D _2909 = _2906 + _2199;
                        D _2910 = _2825 + _2906;
                        D _2911 = _2906 + _2196;
                        vec4 _2913 = textureGatherOffset((sampler2D(ShadowMaps[_1387 + 0u], View_SharedPointClampedSampler)), vec2(_2813, _2814), ivec2(2, 0));
                        D _2914 = _2913.x;
                        D _2915 = _2913.y;
                        D _2916 = _2913.z;
                        D _2917 = _2913.w;
                        D _2983 = (_2810 + 1.5) - _2806;
                        D _2984 = dot(vec2(_2817, _2983), vec2(_2196, _2199));
                        D _2987 = _2984 + _2199;
                        D _2988 = _2825 + _2984;
                        D _2989 = _2984 + _2196;
                        vec4 _2991 = textureGatherOffset((sampler2D(ShadowMaps[_1387 + 0u], View_SharedPointClampedSampler)), vec2(_2813, _2814), ivec2(0, 2));
                        D _2992 = _2991.x;
                        D _2993 = _2991.y;
                        D _2994 = _2991.z;
                        D _2995 = _2991.w;
                        D _3060 = dot(vec2(_2905, _2983), vec2(_2196, _2199));
                        D _3063 = _3060 + _2199;
                        D _3064 = _2825 + _3060;
                        D _3065 = _3060 + _2196;
                        vec4 _3067 = textureGatherOffset((sampler2D(ShadowMaps[_1387 + 0u], View_SharedPointClampedSampler)), vec2(_2813, _2814), ivec2(2));
                        D _3068 = _3067.x;
                        D _3069 = _3067.y;
                        D _3070 = _3067.z;
                        D _3071 = _3067.w;
                        D _3136 = 1.0 - _2811;
                        vec4 _3159 = vec4((((((_2837 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2874 + _2837) + (spvNMin(abs(_2819), 0.0) * D(int(uint(_2819 > 0.0) - uint(_2819 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3136) + ((_2836 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2874 + _2836) + (spvNMin(abs(_2827), 0.0) * D(int(uint(_2827 > 0.0) - uint(_2827 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2917 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2874 + _2917) + (spvNMin(abs(_2906), 0.0) * D(int(uint(_2906 > 0.0) - uint(_2906 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2916 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2874 + _2916) + (spvNMin(abs(_2911), 0.0) * D(int(uint(_2911 > 0.0) - uint(_2911 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2811), (((((_2834 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2874 + _2834) + (spvNMin(abs(_2822), 0.0) * D(int(uint(_2822 > 0.0) - uint(_2822 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3136) + ((_2835 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2874 + _2835) + (spvNMin(abs(_2826), 0.0) * D(int(uint(_2826 > 0.0) - uint(_2826 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2914 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2874 + _2914) + (spvNMin(abs(_2909), 0.0) * D(int(uint(_2909 > 0.0) - uint(_2909 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2915 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2874 + _2915) + (spvNMin(abs(_2910), 0.0) * D(int(uint(_2910 > 0.0) - uint(_2910 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2811), (((((_2995 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2874 + _2995) + (spvNMin(abs(_2984), 0.0) * D(int(uint(_2984 > 0.0) - uint(_2984 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3136) + ((_2994 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2874 + _2994) + (spvNMin(abs(_2989), 0.0) * D(int(uint(_2989 > 0.0) - uint(_2989 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3071 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2874 + _3071) + (spvNMin(abs(_3060), 0.0) * D(int(uint(_3060 > 0.0) - uint(_3060 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3070 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2874 + _3070) + (spvNMin(abs(_3065), 0.0) * D(int(uint(_3065 > 0.0) - uint(_3065 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2811), (((((_2992 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2874 + _2992) + (spvNMin(abs(_2987), 0.0) * D(int(uint(_2987 > 0.0) - uint(_2987 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3136) + ((_2993 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2874 + _2993) + (spvNMin(abs(_2988), 0.0) * D(int(uint(_2988 > 0.0) - uint(_2988 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3068 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2874 + _3068) + (spvNMin(abs(_3063), 0.0) * D(int(uint(_3063 > 0.0) - uint(_3063 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3069 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2874 + _3069) + (spvNMin(abs(_3064), 0.0) * D(int(uint(_3064 > 0.0) - uint(_3064 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2811));
                        _1223 = dot(_3159, vec4(1.0 - _2812, 1.0, 1.0, _2812)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        _1223 = 1.0;
                    }
                    if (_1806)
                    {
                        _1222 = _1223;
                        break;
                    }
                }
            }
            if (floatBitsToUint(TranslucentBasePass_2._m0[30u]).y == 0u)
            {
                _1222 = 1.0;
                break;
            }
            D _1263 = fma(_232, TranslucentBasePass_2._m0[35u].z, fma(_231, TranslucentBasePass_2._m0[34u].z, TranslucentBasePass_2._m0[33u].z * _230)) + TranslucentBasePass_2._m0[36u].z;
            D _1267 = fma(_232, TranslucentBasePass_2._m0[35u].w, fma(_231, TranslucentBasePass_2._m0[34u].w, TranslucentBasePass_2._m0[33u].w * _230)) + TranslucentBasePass_2._m0[36u].w;
            D _1268 = (fma(_232, TranslucentBasePass_2._m0[35u].x, fma(_231, TranslucentBasePass_2._m0[34u].x, TranslucentBasePass_2._m0[33u].x * _230)) + TranslucentBasePass_2._m0[36u].x) / _1267;
            D _1269 = (fma(_232, TranslucentBasePass_2._m0[35u].y, fma(_231, TranslucentBasePass_2._m0[34u].y, TranslucentBasePass_2._m0[33u].y * _230)) + TranslucentBasePass_2._m0[36u].y) / _1267;
            uvec4 _1273 = floatBitsToUint(TranslucentBasePass_2._m0[32u]);
            uint _1274 = _1273.x;
            uint _1275 = _1273.y;
            uint _1276 = _1273.z;
            uint _1281 = uint(int(floor(_1268)));
            uint _1282 = uint(int((-0.0) - floor(_1269)));
            if (!((int(_1282) < int(_1273.w)) && ((int(_1281) < int(_1276)) && ((int(_1281) >= int(_1274)) && (int(_1282) >= int(_1275))))))
            {
                _1222 = 1.0;
                break;
            }
            D _1350 = dFdyFine(_1268);
            D _1351 = dFdyFine(_1269);
            D _1352 = dFdyFine(_1263);
            D _1353 = dFdxFine(_1268);
            D _1354 = dFdxFine(_1269);
            D _1355 = dFdxFine(_1263);
            D _1358 = (_1354 * _1352) - (_1355 * _1351);
            D _1361 = (_1355 * _1350) - (_1353 * _1352);
            D _1364 = (_1353 * _1351) - (_1354 * _1350);
            D _1375 = 1.0 / spvNMax(abs(_1364), sqrt(((_1361 * _1361) + (_1364 * _1364)) + (_1358 * _1358)) * 0.100000001490116119384765625);
            D _1381 = D(int(uint(_1364 > 0.0) - uint(_1364 < 0.0)));
            D _1665;
            D _1667;
            if (dot(vec2(_1358, _1361), vec2(_1358, _1361)) < 1.0000000195414813782625560981111e-24)
            {
                _1665 = 0.0;
                _1667 = 0.0;
            }
            else
            {
                D _1731 = (-0.0) - _1358;
                D _1732 = (-0.0) - _1361;
                D _1736 = inversesqrt(dot(vec2(_1731, _1732), vec2(_1731, _1732)));
                _1665 = _1736 * _1731;
                _1667 = _1736 * _1732;
            }
            D _1673 = _266 + (-0.5);
            D _1681 = (((_1667 * _1673) + (_1665 * _265)) * 2.0) + (_1665 * 0.5);
            D _1682 = (((_1667 * _265) + (_1665 * _1673)) * 2.0) + (_1667 * 0.5);
            D _1688 = _1681 + (fract(_1268) * 256.0);
            D _1689 = _1682 + (fract(_1269) * 256.0);
            D _1702 = dot(vec2((floor(_1688) + 0.5) - _1688, (floor(_1689) + 0.5) - _1689), vec2(((_1358 * 256.0) * _1375) * _1381, ((_1361 * 256.0) * _1375) * _1381));
            D _1708 = (_1681 * 0.00390625) + _1268;
            D _1709 = (_1682 * 0.00390625) + _1269;
            uint _1721 = ((uint(int((-0.0) - floor(_1709))) - _1275) * (_1276 - _1274)) + (uint(int(floor(_1708))) - _1274);
            D _2135;
            D _2138;
            if ((texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowLoadedTileData, int(_1721 >> 5u)).x & (1u << (_1721 & 31u))) == 0u)
            {
                _2135 = 3.0000000054977557577780399428115e+38;
                _2138 = 0.0;
            }
            else
            {
                uvec4 _2160 = uvec4(texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileIndices, int(_1721)));
                uint _2161 = _2160.x;
                D frontier_phi_51_52_ladder;
                D frontier_phi_51_52_ladder_1;
                if (int(_2161) > int(4294967295u))
                {
                    uint _2777 = (uint(floor(fract(_1708) * 256.0)) + (_2161 << 16u)) + (uint(floor(fract(_1709) * 256.0)) << 8u);
                    uvec4 _2780 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileData, int(_2777 >> 1u));
                    uint _2781 = _2780.x;
                    D _2789 = D((((_2777 & 1u) == 0u) ? _2781 : (_2781 >> 16u)) & 65535u) * 1.525902189314365386962890625e-05;
                    D frontier_phi_51_52_ladder_73_ladder;
                    D frontier_phi_51_52_ladder_73_ladder_1;
                    if (_2789 != 1.0)
                    {
                        vec4 _3590 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthRanges, int(_2161));
                        D _3592 = _3590.y;
                        frontier_phi_51_52_ladder_73_ladder = 1.0 / _3592;
                        frontier_phi_51_52_ladder_73_ladder_1 = (_3592 * _2789) + _3590.x;
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
                _2135 = frontier_phi_51_52_ladder_1;
                _2138 = frontier_phi_51_52_ladder;
            }
            _1222 = spvNClamp(((((1.525902189314365386962890625e-05 - _1263) + _2135) + (spvNMin(abs(_1702), _2138 * 10.0) * D(int(uint(_1702 > 0.0) - uint(_1702 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0);
            break;
        }
        D _1337;
        if ((floatBitsToUint(Primitive._m0[27u]).z & 2u) == 0u)
        {
            _1337 = 1.0;
        }
        else
        {
            _1337 = View._m0[188u].y;
        }
        uvec4 _1341 = floatBitsToUint(View._m0[220u]);
        uint _1342 = _1341.y;
        uint _1345 = (_1342 != 1u) ? 4294967295u : 0u;
        uint _1663;
        if (_1342 > 1u)
        {
            D _131[4];
            _131[0u] = 0.0;
            _131[1u] = 0.0;
            _131[2u] = 0.0;
            _131[3u] = 0.0;
            uint _2120 = 0u;
            bool _2126;
            for (;;)
            {
                _2126 = _2120 < floatBitsToUint(View._m0[220u]).y;
                if (_2126)
                {
                    uint _2728 = _2120 + 237u;
                    D _2742 = View._m0[_2728].x - View._m0[75u].x;
                    D _2743 = View._m0[_2728].y - View._m0[75u].y;
                    D _2744 = View._m0[_2728].z - View._m0[75u].z;
                    D _2745 = dot(vec3(_2742, _2743, _2744), vec3(_238, _239, _240));
                    D _2752 = dot(vec3(_2742, _2743, _2744), vec3(_2742, _2743, _2744)) - (View._m0[_2728].w * View._m0[_2728].w);
                    D _2754 = (_2745 * _2745) - _2752;
                    D _3366;
                    if ((_2752 < 0.0) && (!(_2754 < 0.0)))
                    {
                        D _3360 = sqrt(_2754);
                        _3366 = spvNMin(abs(_3360 + _2745), abs(_2745 - _3360));
                    }
                    else
                    {
                        _3366 = 0.0;
                    }
                    _131[_2120] = _3366;
                }
                uint _2121 = _2120 + 1u;
                if (_2121 == 4u)
                {
                    break;
                }
                else
                {
                    _2120 = _2121;
                    continue;
                }
            }
            D _3377 = (_265 * 0.99989998340606689453125) * dot(vec4(_131[0u], _131[1u], _131[2u], _131[3u]), vec4(1.0));
            uint frontier_phi_32_83_ladder;
            if (_131[0u] > _3377)
            {
                frontier_phi_32_83_ladder = 0u;
            }
            else
            {
                D _3728 = _131[1u] + _131[0u];
                uint frontier_phi_32_83_ladder_94_ladder;
                if (_3728 > _3377)
                {
                    frontier_phi_32_83_ladder_94_ladder = 1u;
                }
                else
                {
                    D _3812 = _3728 + _131[2u];
                    uint frontier_phi_32_83_ladder_94_ladder_102_ladder;
                    if (_3812 > _3377)
                    {
                        frontier_phi_32_83_ladder_94_ladder_102_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder;
                        if ((_3812 + _131[3u]) > _3377)
                        {
                            frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder = _1345;
                        }
                        frontier_phi_32_83_ladder_94_ladder_102_ladder = frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder;
                    }
                    frontier_phi_32_83_ladder_94_ladder = frontier_phi_32_83_ladder_94_ladder_102_ladder;
                }
                frontier_phi_32_83_ladder = frontier_phi_32_83_ladder_94_ladder;
            }
            _1663 = frontier_phi_32_83_ladder;
        }
        else
        {
            _1663 = _1345;
        }
        D _2127;
        if (_1663 == 4294967295u)
        {
            _2127 = _1337;
        }
        else
        {
            _2127 = View._m0[_1663 + 241u].x * _1337;
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
        if (_2127 > 0.0)
        {
            D _2761 = spvNClamp((TranslucentBasePass_2._m0[7u].x * _103) + TranslucentBasePass_2._m0[7u].y, 0.0, 1.0);
            D _2765 = ((_2761 * _2761) * (1.0 - _1222)) + _1222;
            D frontier_phi_3_49_ladder_72_ladder;
            D frontier_phi_3_49_ladder_72_ladder_1;
            D frontier_phi_3_49_ladder_72_ladder_2;
            D frontier_phi_3_49_ladder_72_ladder_3;
            D frontier_phi_3_49_ladder_72_ladder_4;
            D frontier_phi_3_49_ladder_72_ladder_5;
            D frontier_phi_3_49_ladder_72_ladder_6;
            D frontier_phi_3_49_ladder_72_ladder_7;
            D frontier_phi_3_49_ladder_72_ladder_8;
            if (_2765 > 0.0)
            {
                D _3379 = dot(vec3(_422, _423, _424), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3382 = spvNMax(0.0, _3379);
                D _3383 = dot(vec3(_241, _243, _244), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3389 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3383 * 2.0) + 2.0));
                D _3392 = spvNClamp(_3389 * (_536 + _3379), 0.0, 1.0);
                D _3407 = sqrt(spvNMax(0.0, 1.0 - ((1.0 - (_536 * _536)) * 0.444444477558135986328125)));
                D _3411 = (_542 * 0.666666686534881591796875) - (_3407 * _422);
                D _3412 = (_543 * 0.666666686534881591796875) - (_3407 * _423);
                D _3413 = (_544 * 0.666666686534881591796875) - (_3407 * _424);
                D _3417 = inversesqrt(dot(vec3(_3411, _3412, _3413), vec3(_3411, _3412, _3413)));
                D _3424 = dot(vec3((-0.0) - (_3417 * _3411), (-0.0) - (_3417 * _3412), (-0.0) - (_3417 * _3413)), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3427 = _640 * _640;
                D _3428 = _3427 * _3427;
                D _3432 = ((_3392 * _3392) * (_3428 + (-1.0))) + 1.0;
                D _3438 = (_3382 * 2.0) * _562;
                D _3443 = 1.0 - spvNMax(9.9999997473787516355514526367188e-06, spvNMin(_3389 * (_3383 + 1.0), 1.0));
                D _3444 = _3443 * _3443;
                D _3446 = (_3444 * _3444) * _3443;
                D _3451 = spvNMin(dot(vec3(_520, _521, _522), vec3(16.666667938232421875)), 1.0);
                D _3464 = spvNMax(0.039999999105930328369140625, _640);
                D _3477 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_3464 * _3382) + 0.02669160068035125732421875) / (_3382 + 0.4664950072765350341796875)) * exp2(((1.0 / _3464) * _3382) * log2(_3464)), 0.0, 1.0));
                D _3478 = 1.0 - _3382;
                D _3479 = _3478 * _3478;
                D _3491 = ((_3479 * _3479) * _3478) * exp2(log2((exp2((_3464 * 4.7702999114990234375) * log2(_3382)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _3464);
                D _3494 = (1.0 / _3477) * (1.0 - _3477);
                D _3498 = (_3494 * _520) + 1.0;
                D _3499 = (_3494 * _521) + 1.0;
                D _3500 = (_3494 * _522) + 1.0;
                D _3501 = _3477 - _3491;
                D _3515 = spvNClamp(1.0 - dot(vec3(_3498 * ((_3501 * _520) + _3491), _3499 * ((_3501 * _521) + _3491), _3500 * ((_3501 * _522) + _3491)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                D _3518 = (((_3428 * 0.3183098733425140380859375) * _3382) * (1.0 / (_3432 * _3432))) * (0.5 / ((_3427 * ((_562 + _3382) - _3438)) + _3438));
                D _3519 = _3382 * 0.3183098733425140380859375;
                D _3522 = ((_3424 * _3424) + 1.0) * 0.05968309938907623291015625;
                D _3524 = spvNMin(1.0, _448);
                D _3526 = (_448 + 1.0) - _3524;
                D _3527 = _3526 * _3526;
                D _3530 = 1.0 - ((_3527 * _3527) * _3526);
                D _3531 = _3530 * _3530;
                D _3536 = ((_3531 * _3531) * (_3530 * (_448 - _3524))) + _3524;
                D _3539 = sqrt(spvNMax(0.0, 1.0 - _3536));
                D _3544 = 1.0 - spvNClamp((_640 * 3.5) + (-0.5), 0.0, 1.0);
                D _3545 = _3544 * _3544;
                D _3555 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_671 * _3539) * spvNClamp(1.0 - ((_3545 * _3545) * _3544), 0.0, 1.0))) * _3382, 0.0, 1.0);
                D _3560 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _3539)) * _3382, 0.0, 1.0);
                D _3562 = spvNMin(_2765, _3555 * _3555);
                D _3563 = spvNMin(_2765, _3560 * _3560);
                D _3564 = spvNMin(_2765, _3536);
                D _3565 = _2127 * TranslucentBasePass_2._m0[4u].x;
                D _3566 = _2127 * TranslucentBasePass_2._m0[4u].y;
                D _3567 = _2127 * TranslucentBasePass_2._m0[4u].z;
                frontier_phi_3_49_ladder_72_ladder = (_3522 * _3567) * _3564;
                frontier_phi_3_49_ladder_72_ladder_1 = (((_3565 * _472) * _3519) * _3515) * _3563;
                frontier_phi_3_49_ladder_72_ladder_2 = (((_3566 * _473) * _3519) * _3515) * _3563;
                frontier_phi_3_49_ladder_72_ladder_3 = (((_3567 * _474) * _3519) * _3515) * _3563;
                frontier_phi_3_49_ladder_72_ladder_4 = (((_3518 * _3565) * spvNClamp(((_3451 - _520) * _3446) + _520, 0.0, 1.0)) * _3498) * _3562;
                frontier_phi_3_49_ladder_72_ladder_5 = (((_3518 * _3566) * spvNClamp(((_3451 - _521) * _3446) + _521, 0.0, 1.0)) * _3499) * _3562;
                frontier_phi_3_49_ladder_72_ladder_6 = (((_3518 * _3567) * spvNClamp(((_3451 - _522) * _3446) + _522, 0.0, 1.0)) * _3500) * _3562;
                frontier_phi_3_49_ladder_72_ladder_7 = (_3522 * _3565) * _3564;
                frontier_phi_3_49_ladder_72_ladder_8 = (_3522 * _3566) * _3564;
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
        _772 = frontier_phi_3_49_ladder_1;
        _774 = frontier_phi_3_49_ladder_2;
        _776 = frontier_phi_3_49_ladder_3;
        _778 = frontier_phi_3_49_ladder_4;
        _780 = frontier_phi_3_49_ladder_5;
        _782 = frontier_phi_3_49_ladder_6;
        _784 = frontier_phi_3_49_ladder_7;
        _786 = frontier_phi_3_49_ladder_8;
        _788 = frontier_phi_3_49_ladder;
    }
    uvec4 _792 = floatBitsToUint(TranslucentBasePass_2._m0[0u]);
    uint _793 = _792.x;
    uint _798 = min(min(texelFetch(TranslucentBasePass_Shared_Forward_NumCulledLightsGrid, int(0u)).x, _793), _793);
    D _805;
    D _807;
    D _809;
    D _811;
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
    if (_798 == 0u)
    {
        _805 = _772;
        _807 = _774;
        _809 = _776;
        _811 = _778;
        _813 = _780;
        _815 = _782;
        _817 = _784;
        _819 = _786;
        _821 = _788;
        _823 = 0.0;
        _825 = 0.0;
        _827 = 0.0;
        _829 = 0.0;
        _831 = 0.0;
        _833 = 0.0;
    }
    else
    {
        D _806;
        D _808;
        D _810;
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
        D _1137 = _772;
        D _1138 = _774;
        D _1139 = _776;
        D _1140 = _778;
        D _1141 = _780;
        D _1142 = _782;
        D _1143 = _784;
        D _1144 = _786;
        D _1145 = _788;
        D _1146 = 0.0;
        D _1147 = 0.0;
        D _1148 = 0.0;
        D _1149 = 0.0;
        D _1150 = 0.0;
        D _1151 = 0.0;
        uint _1152 = 0u;
        D _1156;
        D _1157;
        D _1158;
        D _1159;
        D _1161;
        D _1162;
        D _1163;
        D _1165;
        D _1166;
        D _1167;
        uint _1169;
        D _1171;
        D _1172;
        D _1174;
        D _1175;
        D _1176;
        D _1178;
        D _1179;
        uint _1181;
        D _1184;
        D _1185;
        D _1186;
        D _1187;
        uint _1190;
        D _1192;
        D _1193;
        D _1194;
        D _1195;
        D _1198;
        D _1199;
        D _1200;
        D _1201;
        D _1204;
        D _1205;
        D _1206;
        D _1207;
        D _1210;
        D _1211;
        D _1212;
        D _1213;
        bool _1216;
        bool _1217;
        bool _1221;
        for (;;)
        {
            vec4 _1155 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(0u));
            _1156 = _1155.x;
            _1157 = _1155.y;
            _1158 = _1155.z;
            _1159 = _1155.w;
            vec4 _1160 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(1u));
            _1161 = _1160.x;
            _1162 = _1160.y;
            _1163 = _1160.z;
            vec4 _1164 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(2u));
            _1165 = _1164.x;
            _1166 = _1164.y;
            _1167 = _1164.z;
            _1169 = floatBitsToUint(_1164.w);
            vec4 _1170 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(3u));
            _1171 = _1170.x;
            _1172 = _1170.y;
            vec4 _1173 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(4u));
            _1174 = _1173.x;
            _1175 = _1173.y;
            _1176 = _1173.z;
            vec4 _1177 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(5u));
            _1178 = _1177.x;
            _1179 = _1177.y;
            _1181 = floatBitsToUint(_1177.z);
            vec4 _1183 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(6u));
            _1184 = _1183.x;
            _1185 = _1183.y;
            _1186 = _1183.z;
            _1187 = _1183.w;
            _1190 = floatBitsToUint(texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(7u)).x);
            vec4 _1191 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(8u));
            _1192 = _1191.x;
            _1193 = _1191.y;
            _1194 = _1191.z;
            _1195 = _1191.w;
            vec4 _1197 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(9u));
            _1198 = _1197.x;
            _1199 = _1197.y;
            _1200 = _1197.z;
            _1201 = _1197.w;
            vec4 _1203 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(10u));
            _1204 = _1203.x;
            _1205 = _1203.y;
            _1206 = _1203.z;
            _1207 = _1203.w;
            vec4 _1209 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(11u));
            _1210 = _1209.x;
            _1211 = _1209.y;
            _1212 = _1209.z;
            _1213 = _1209.w;
            _1216 = (_1169 & 131072u) != 0u;
            _1217 = _1171 > (-2.0);
            _1221 = (_1169 & 16384u) == 0u;
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
            if (_1221)
            {
                D _1616;
                if (_1216)
                {
                    uint _1581 = _1190 + 0u;
                    uvec2 _1584 = uvec2(textureSize(ShadowMaps[(_1581)], int(0u)));
                    D _1586 = D(int(_1584.x));
                    D _1588 = D(int(_1584.y));
                    D _1589 = 1.0 / _1586;
                    D _1590 = 1.0 / _1588;
                    D _1602 = fma(_232, _1206, fma(_231, _1200, _1194 * _230)) + _1212;
                    D _1606 = fma(_232, _1207, fma(_231, _1201, _1195 * _230)) + _1213;
                    D _1607 = (fma(_232, _1204, fma(_231, _1198, _1192 * _230)) + _1210) / _1606;
                    D _1608 = (fma(_232, _1205, fma(_231, _1199, _1193 * _230)) + _1211) / _1606;
                    D frontier_phi_28_27_ladder;
                    if ((_1608 <= _1187) && ((_1607 <= _1186) && ((_1607 >= _1184) && (_1608 >= _1185))))
                    {
                        D _2004 = dFdyFine(_1607);
                        D _2005 = dFdyFine(_1608);
                        D _2006 = dFdyFine(_1602);
                        D _2007 = dFdxFine(_1607);
                        D _2008 = dFdxFine(_1608);
                        D _2009 = dFdxFine(_1602);
                        D _2012 = (_2008 * _2006) - (_2009 * _2005);
                        D _2015 = (_2009 * _2004) - (_2007 * _2006);
                        D _2018 = (_2007 * _2005) - (_2008 * _2004);
                        D _2028 = 1.0 / spvNMax(abs(_2018), sqrt(((_2015 * _2015) + (_2018 * _2018)) + (_2012 * _2012)) * 0.100000001490116119384765625);
                        D _2034 = D(int(uint(_2018 > 0.0) - uint(_2018 < 0.0)));
                        D _2035 = _2012 * _1589;
                        D _2037 = (_2035 * _2028) * _2034;
                        D _2038 = _2015 * _1590;
                        D _2040 = (_2038 * _2028) * _2034;
                        D _2323;
                        D _2325;
                        if (dot(vec2(_2012, _2015), vec2(_2012, _2015)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2323 = 0.0;
                            _2325 = 0.0;
                        }
                        else
                        {
                            D _2666 = (-0.0) - _2012;
                            D _2667 = (-0.0) - _2015;
                            D _2671 = inversesqrt(dot(vec2(_2666, _2667), vec2(_2666, _2667)));
                            _2323 = _2671 * _2666;
                            _2325 = _2671 * _2667;
                        }
                        D _2327 = _266 + (-0.5);
                        D _2332 = _265 + 0.5;
                        D _2335 = ((_2325 * _2327) + (_1607 * _1586)) + (_2323 * _2332);
                        D _2338 = ((_2323 * _2327) + (_1608 * _1588)) + (_2325 * _2332);
                        D _2339 = _2335 + (-0.5);
                        D _2340 = _2338 + (-0.5);
                        D _2341 = trunc(_2339);
                        D _2342 = trunc(_2340);
                        D _2343 = _2339 - _2341;
                        D _2344 = _2340 - _2342;
                        D _2345 = _2341 * _1589;
                        D _2346 = _2342 * _1590;
                        D _2349 = (_2341 + (-0.5)) - _2335;
                        D _2350 = (_2342 + (-0.5)) - _2338;
                        D _2351 = dot(vec2(_2349, _2350), vec2(_2037, _2040));
                        D _2354 = _2351 + _2040;
                        D _2357 = _2034 * (_2028 * (_2038 + _2035));
                        D _2358 = _2357 + _2351;
                        D _2359 = _2351 + _2037;
                        vec4 _2363 = textureGather((sampler2D(ShadowMaps[_1581], View_SharedPointClampedSampler)), vec2(_2345, _2346));
                        D _2404 = 1.525902189314365386962890625e-05 - _1602;
                        D _2427 = (_2341 + 1.5) - _2335;
                        D _2428 = dot(vec2(_2427, _2350), vec2(_2037, _2040));
                        D _2431 = _2428 + _2040;
                        D _2432 = _2357 + _2428;
                        D _2433 = _2428 + _2037;
                        vec4 _2437 = textureGatherOffset((sampler2D(ShadowMaps[_1581], View_SharedPointClampedSampler)), vec2(_2345, _2346), ivec2(2, 0));
                        D _2501 = (_2342 + 1.5) - _2338;
                        D _2502 = dot(vec2(_2349, _2501), vec2(_2037, _2040));
                        D _2505 = _2502 + _2040;
                        D _2506 = _2357 + _2502;
                        D _2507 = _2502 + _2037;
                        vec4 _2509 = textureGatherOffset((sampler2D(ShadowMaps[_1581], View_SharedPointClampedSampler)), vec2(_2345, _2346), ivec2(0, 2));
                        D _2571 = dot(vec2(_2427, _2501), vec2(_2037, _2040));
                        D _2574 = _2571 + _2040;
                        D _2575 = _2357 + _2571;
                        D _2576 = _2571 + _2037;
                        vec4 _2578 = textureGatherOffset((sampler2D(ShadowMaps[_1581], View_SharedPointClampedSampler)), vec2(_2345, _2346), ivec2(2));
                        D _2640 = 1.0 - _2343;
                        vec4 _2663 = vec4((((spvNClamp((((_2404 + _2363.w) + (spvNMin(abs(_2351), 0.0) * D(int(uint(_2351 > 0.0) - uint(_2351 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2640) + spvNClamp((((_2404 + _2363.z) + (spvNMin(abs(_2359), 0.0) * D(int(uint(_2359 > 0.0) - uint(_2359 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2404 + _2437.w) + (spvNMin(abs(_2428), 0.0) * D(int(uint(_2428 > 0.0) - uint(_2428 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2404 + _2437.z) + (spvNMin(abs(_2433), 0.0) * D(int(uint(_2433 > 0.0) - uint(_2433 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2343), (((spvNClamp((((_2404 + _2363.x) + (spvNMin(abs(_2354), 0.0) * D(int(uint(_2354 > 0.0) - uint(_2354 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2640) + spvNClamp((((_2404 + _2363.y) + (spvNMin(abs(_2358), 0.0) * D(int(uint(_2358 > 0.0) - uint(_2358 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2404 + _2437.x) + (spvNMin(abs(_2431), 0.0) * D(int(uint(_2431 > 0.0) - uint(_2431 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2404 + _2437.y) + (spvNMin(abs(_2432), 0.0) * D(int(uint(_2432 > 0.0) - uint(_2432 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2343), (((spvNClamp((((_2404 + _2509.w) + (spvNMin(abs(_2502), 0.0) * D(int(uint(_2502 > 0.0) - uint(_2502 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2640) + spvNClamp((((_2404 + _2509.z) + (spvNMin(abs(_2507), 0.0) * D(int(uint(_2507 > 0.0) - uint(_2507 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2404 + _2578.w) + (spvNMin(abs(_2571), 0.0) * D(int(uint(_2571 > 0.0) - uint(_2571 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2404 + _2578.z) + (spvNMin(abs(_2576), 0.0) * D(int(uint(_2576 > 0.0) - uint(_2576 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2343), (((spvNClamp((((_2404 + _2509.x) + (spvNMin(abs(_2505), 0.0) * D(int(uint(_2505 > 0.0) - uint(_2505 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2640) + spvNClamp((((_2404 + _2509.y) + (spvNMin(abs(_2506), 0.0) * D(int(uint(_2506 > 0.0) - uint(_2506 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2404 + _2578.x) + (spvNMin(abs(_2574), 0.0) * D(int(uint(_2574 > 0.0) - uint(_2574 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2404 + _2578.y) + (spvNMin(abs(_2575), 0.0) * D(int(uint(_2575 > 0.0) - uint(_2575 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2343));
                        frontier_phi_28_27_ladder = dot(_2663, vec4(1.0 - _2344, 1.0, 1.0, _2344)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        frontier_phi_28_27_ladder = 1.0;
                    }
                    _1616 = frontier_phi_28_27_ladder;
                }
                else
                {
                    _1616 = 1.0;
                }
                D _1622 = _1156 - _230;
                D _1623 = _1157 - _231;
                D _1624 = _1158 - _232;
                D _1625 = dot(vec3(_1622, _1623, _1624), vec3(_1622, _1623, _1624));
                D _2049;
                D _2050;
                D _2051;
                if (_1625 > 9.9999997473787516355514526367188e-05)
                {
                    D _2045 = inversesqrt(_1625);
                    _2049 = _2045 * _1622;
                    _2050 = _2045 * _1623;
                    _2051 = _2045 * _1624;
                }
                else
                {
                    _2049 = 0.0;
                    _2050 = 0.0;
                    _2051 = 0.0;
                }
                D _2052 = _1178 * _1178;
                D _2056 = (_1159 * _1159) * _1625;
                D _2059 = spvNClamp(1.0 - (_2056 * _2056), 0.0, 1.0);
                D _2679;
                if (_1217)
                {
                    D _2677 = spvNClamp((dot(vec3(_2049, _2050, _2051), vec3(_1165, _1166, _1167)) - _1171) * _1172, 0.0, 1.0);
                    _2679 = _2677 * _2677;
                }
                else
                {
                    _2679 = 1.0;
                }
                D _2680 = ((_2059 * _2059) * D(_1625 >= _2052)) * _2679;
                D _3223;
                D _3225;
                D _3227;
                if ((_1169 & 262144u) == 0u)
                {
                    _3223 = 1.0;
                    _3225 = 1.0;
                    _3227 = 1.0;
                }
                else
                {
                    D _3230 = (-0.0) - _1166;
                    D _3231 = (-0.0) - _1167;
                    D _3232 = (-0.0) - _1165;
                    D _3242 = (-0.0) - _2049;
                    D _3243 = (-0.0) - _2050;
                    D _3244 = (-0.0) - _2051;
                    D _3247 = fma(_3231, _3244, fma(_3230, _3243, _2049 * _1165));
                    D _3250 = fma(_1176, _3244, fma(_1175, _3243, _1174 * _3242));
                    D _3258 = atan(((-0.0) - _3250) / ((-0.0) - _3247));
                    bool _3263 = _3247 > (-0.0);
                    bool _3264 = _3247 == (-0.0);
                    bool _3265 = _3250 <= (-0.0);
                    bool _3266 = _3250 > (-0.0);
                    vec4 _3288 = texture((sampler2D(ForwardLightProfileTextures[_1181 + 0u], View_SharedBilinearWrappedSampler)), vec2(fract((_3264 && _3265) ? 1.25 : ((_3264 && _3266) ? 0.75 : ((((_3263 && _3266) ? (_3258 + (-3.1415927410125732421875)) : ((_3263 && _3265) ? (_3258 + 3.1415927410125732421875) : _3258)) * 0.15915493667125701904296875) + 1.0))), (asin((-0.0) - fma((_1175 * _3232) - (_1174 * _3230), _3244, fma((_1174 * _3231) - (_1176 * _3232), _3243, ((_1176 * _3230) - (_1175 * _3231)) * _3242))) * 0.3183098733425140380859375) + 0.5));
                    _3223 = _3288.x;
                    _3225 = _3288.y;
                    _3227 = _3288.z;
                }
                D _3679;
                D _3681;
                D _3683;
                D _3685;
                D _3687;
                D _3689;
                D _3691;
                D _3693;
                D _3695;
                for (;;)
                {
                    if (_2680 > 0.0)
                    {
                        D _3804;
                        if (_1216)
                        {
                            if (!(_1616 > 0.0))
                            {
                                _3679 = 0.0;
                                _3681 = 0.0;
                                _3683 = 0.0;
                                _3685 = 0.0;
                                _3687 = 0.0;
                                _3689 = 0.0;
                                _3691 = 0.0;
                                _3693 = 0.0;
                                _3695 = 0.0;
                                break;
                            }
                            _3804 = _1616;
                        }
                        else
                        {
                            _3804 = 1.0;
                        }
                        D _3806 = spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1625));
                        D _3807 = 1.0 / _3806;
                        D _3808 = dot(vec3(_422, _423, _424), vec3(_2049, _2050, _2051));
                        D _3829;
                        if (_1178 > 0.0)
                        {
                            D _3826 = sqrt(spvNClamp(_2052 * _3807, 0.0, 1.0));
                            D frontier_phi_107_106_ladder;
                            if (_3826 > spvNMax(9.9999997473787516355514526367188e-06, _3808))
                            {
                                D _3848 = spvNMax((-0.0) - _3826, _3808) + _3826;
                                frontier_phi_107_106_ladder = (_3848 * _3848) * (0.25 / _3826);
                            }
                            else
                            {
                                frontier_phi_107_106_ladder = _3808;
                            }
                            _3829 = frontier_phi_107_106_ladder;
                        }
                        else
                        {
                            _3829 = _3808;
                        }
                        D _3891;
                        D _3892;
                        D _3831;
                        D _3833;
                        D _3837;
                        D _3838;
                        bool _3841;
                        for (;;)
                        {
                            _3831 = spvNMax(0.0, _3829);
                            _3833 = _640 * _640;
                            _3837 = spvNClamp(((1.0 - _3833) * _1178) * inversesqrt(_3806), 0.0, 1.0);
                            _3838 = dot(vec3(_241, _243, _244), vec3(_2049, _2050, _2051));
                            _3841 = _3837 > 0.0;
                            D _3859;
                            D _3861;
                            if (_3841)
                            {
                                D _3854 = sqrt(spvNMax(0.0, 1.0 - (_3837 * _3837)));
                                D _3857 = ((_3808 * 2.0) * _536) - _3838;
                                if (!(!(_3857 >= _3854)))
                                {
                                    _3891 = _548;
                                    _3892 = 1.0;
                                    break;
                                }
                                D _3879 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, 1.0 - (_3857 * _3857))) * _3837;
                                _3859 = (_3879 * ((((_536 * _536) * 2.0) + (-1.0)) - (_3857 * _3838))) + (_3854 * _3838);
                                _3861 = (_3879 * (_536 - (_3857 * _3808))) + (_3854 * _3808);
                            }
                            else
                            {
                                _3859 = _3838;
                                _3861 = _3808;
                            }
                            D _3866 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3859 * 2.0) + 2.0));
                            _3891 = spvNMin(_3866 * (_3859 + 1.0), 1.0);
                            _3892 = spvNClamp(_3866 * (_3861 + _536), 0.0, 1.0);
                            break;
                        }
                        D _3893 = spvNMax(9.9999997473787516355514526367188e-06, _3891);
                        D _3902 = sqrt(spvNMax(0.0, 1.0 - ((1.0 - (_536 * _536)) * 0.444444477558135986328125)));
                        D _3906 = (_542 * 0.666666686534881591796875) - (_3902 * _422);
                        D _3907 = (_543 * 0.666666686534881591796875) - (_3902 * _423);
                        D _3908 = (_544 * 0.666666686534881591796875) - (_3902 * _424);
                        D _3912 = inversesqrt(dot(vec3(_3906, _3907, _3908), vec3(_3906, _3907, _3908)));
                        D _3919 = dot(vec3((-0.0) - (_3912 * _3906), (-0.0) - (_3912 * _3907), (-0.0) - (_3912 * _3908)), vec3(_2049, _2050, _2051));
                        D _3922 = _3833 * _3833;
                        D _3936 = ((_3892 * _3892) * (_3922 + (-1.0))) + 1.0;
                        D _3942 = (_3831 * 2.0) * _562;
                        D _3947 = 1.0 - _3893;
                        D _3948 = _3947 * _3947;
                        D _3950 = (_3948 * _3948) * _3947;
                        D _3954 = spvNMin(dot(vec3(_520, _521, _522), vec3(16.666667938232421875)), 1.0);
                        D _3967 = spvNMax(0.039999999105930328369140625, _640);
                        D _3980 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_3967 * _3831) + 0.02669160068035125732421875) / (_3831 + 0.4664950072765350341796875)) * exp2(((1.0 / _3967) * _3831) * log2(_3967)), 0.0, 1.0));
                        D _3981 = 1.0 - _3831;
                        D _3982 = _3981 * _3981;
                        D _3994 = ((_3982 * _3982) * _3981) * exp2(log2((exp2((_3967 * 4.7702999114990234375) * log2(_3831)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _3967);
                        D _3997 = (1.0 / _3980) * (1.0 - _3980);
                        D _4001 = (_3997 * _520) + 1.0;
                        D _4002 = (_3997 * _521) + 1.0;
                        D _4003 = (_3997 * _522) + 1.0;
                        D _4004 = _3980 - _3994;
                        D _4018 = spvNClamp(1.0 - dot(vec3(_4001 * ((_4004 * _520) + _3994), _4002 * ((_4004 * _521) + _3994), _4003 * ((_4004 * _522) + _3994)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                        D _4022 = ((((_3922 * 0.3183098733425140380859375) * _3831) * (1.0 / (_3936 * _3936))) * (_3841 ? ((1.0 / ((((_3837 * 0.25) * (_3837 + (_3833 * 3.0))) * (1.0 / _3893)) + _3922)) * _3922) : 1.0)) * (0.5 / ((_3833 * ((_562 + _3831) - _3942)) + _3942));
                        D _4023 = _3831 * 0.3183098733425140380859375;
                        D _4026 = ((_3919 * _3919) + 1.0) * 0.05968309938907623291015625;
                        D _4027 = spvNMin(1.0, _448);
                        D _4029 = (_448 + 1.0) - _4027;
                        D _4030 = _4029 * _4029;
                        D _4033 = 1.0 - ((_4030 * _4030) * _4029);
                        D _4034 = _4033 * _4033;
                        D _4039 = ((_4034 * _4034) * (_4033 * (_448 - _4027))) + _4027;
                        D _4042 = sqrt(spvNMax(0.0, 1.0 - _4039));
                        D _4046 = 1.0 - spvNClamp((_640 * 3.5) + (-0.5), 0.0, 1.0);
                        D _4047 = _4046 * _4046;
                        D _4057 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_671 * _4042) * spvNClamp(1.0 - ((_4047 * _4047) * _4046), 0.0, 1.0))) * _3831, 0.0, 1.0);
                        D _4062 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _4042)) * _3831, 0.0, 1.0);
                        D _4064 = spvNMin(_3804, _4057 * _4057);
                        D _4065 = spvNMin(_3804, _4062 * _4062);
                        D _4066 = spvNMin(_3804, _4039);
                        D _4070 = (_2680 * _1161) * _3223;
                        D _4071 = (_2680 * _1162) * _3225;
                        D _4072 = (_2680 * _1163) * _3227;
                        D _4073 = _3807 * _4070;
                        D _4077 = _3807 * _4071;
                        D _4081 = _3807 * _4072;
                        _3679 = ((((_4070 * _472) * _3807) * _4023) * _4018) * _4065;
                        _3681 = ((((_4071 * _473) * _3807) * _4023) * _4018) * _4065;
                        _3683 = ((((_4072 * _474) * _3807) * _4023) * _4018) * _4065;
                        _3685 = (((_4073 * spvNClamp(((_3954 - _520) * _3950) + _520, 0.0, 1.0)) * _4022) * _4001) * _4064;
                        _3687 = (((_4077 * _4022) * spvNClamp(((_3954 - _521) * _3950) + _521, 0.0, 1.0)) * _4002) * _4064;
                        _3689 = (((_4081 * _4022) * spvNClamp(((_3954 - _522) * _3950) + _522, 0.0, 1.0)) * _4003) * _4064;
                        _3691 = (_4073 * _4026) * _4066;
                        _3693 = (_4077 * _4026) * _4066;
                        _3695 = (_4081 * _4026) * _4066;
                        break;
                    }
                    else
                    {
                        _3679 = 0.0;
                        _3681 = 0.0;
                        _3683 = 0.0;
                        _3685 = 0.0;
                        _3687 = 0.0;
                        _3689 = 0.0;
                        _3691 = 0.0;
                        _3693 = 0.0;
                        _3695 = 0.0;
                        break;
                    }
                }
                frontier_phi_47_pred = _1147;
                frontier_phi_47_pred_1 = _3679 + _1137;
                frontier_phi_47_pred_2 = _3681 + _1138;
                frontier_phi_47_pred_3 = _3683 + _1139;
                frontier_phi_47_pred_4 = _3685 + _1140;
                frontier_phi_47_pred_5 = _3687 + _1141;
                frontier_phi_47_pred_6 = _3689 + _1142;
                frontier_phi_47_pred_7 = _3691 + _1143;
                frontier_phi_47_pred_8 = _3693 + _1144;
                frontier_phi_47_pred_9 = _3695 + _1145;
                frontier_phi_47_pred_10 = _1146;
                frontier_phi_47_pred_11 = _1148;
                frontier_phi_47_pred_12 = _1149;
                frontier_phi_47_pred_13 = _1150;
                frontier_phi_47_pred_14 = _1151;
            }
            else
            {
                D _1320 = _1156 - _230;
                D _1321 = _1157 - _231;
                D _1322 = _1158 - _232;
                D _1323 = dot(vec3(_1320, _1321, _1322), vec3(_1320, _1321, _1322));
                D _1327 = (_1159 * _1159) * _1323;
                D _1328 = _1327 * _1327;
                D _1329 = _1328 * _1328;
                D _1332 = spvNClamp(1.0 - (_1329 * _1329), 0.0, 1.0);
                D _1333 = _1332 * _1332;
                D _1334 = _1333 * _1333;
                D _1335 = _1334 * _1334;
                D _1640;
                D _1642;
                D _1644;
                D _1646;
                D _1648;
                D _1650;
                if (_1335 > 0.0)
                {
                    D _1632 = dot(vec3(_238, _239, _240), vec3(_422, _423, _424)) * 2.0;
                    D _1636 = _238 - (_1632 * _422);
                    D _1637 = _239 - (_1632 * _423);
                    D _1638 = _240 - (_1632 * _424);
                    D _3290;
                    D _3291;
                    D _3292;
                    D _3293;
                    D _3294;
                    D _3295;
                    D _3296;
                    D _3297;
                    D _3298;
                    D _3299;
                    D _3300;
                    if (_1179 == 0.0)
                    {
                        D _2685;
                        D _2686;
                        D _2687;
                        if (_1323 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2681 = inversesqrt(_1323);
                            _2685 = _2681 * _1320;
                            _2686 = _2681 * _1321;
                            _2687 = _2681 * _1322;
                        }
                        else
                        {
                            _2685 = 0.0;
                            _2686 = 0.0;
                            _2687 = 0.0;
                        }
                        D _2690 = 1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1323));
                        _3290 = _2690;
                        _3291 = (_1178 * _1178) * _2690;
                        _3292 = _2685;
                        _3293 = _2686;
                        _3294 = _2687;
                        _3295 = _2685;
                        _3296 = _2686;
                        _3297 = _2687;
                        _3298 = _2685;
                        _3299 = _2686;
                        _3300 = _2687;
                    }
                    else
                    {
                        D _2063 = _1179 * 0.5;
                        D _2064 = _2063 * _1165;
                        D _2065 = _2063 * _1166;
                        D _2066 = _2063 * _1167;
                        D _2067 = _1320 - _2064;
                        D _2068 = _1321 - _2065;
                        D _2069 = _1322 - _2066;
                        D _2070 = _2064 + _1320;
                        D _2071 = _2065 + _1321;
                        D _2072 = _2066 + _1322;
                        D _2080 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2067, _2068, _2069), vec3(_2067, _2068, _2069))));
                        D _2082 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2070, _2071, _2072), vec3(_2070, _2071, _2072))));
                        D _2083 = _2082 * _2080;
                        D _2099 = (1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(_2083, ((dot(vec3(_2067, _2068, _2069), vec3(_2070, _2071, _2072)) * 0.5) * _2083) + 0.5))) * _2083;
                        D _2101 = (_1165 * 2.0) * _2063;
                        D _2103 = (_1166 * 2.0) * _2063;
                        D _2105 = (_1167 * 2.0) * _2063;
                        D _2106 = dot(vec3(_2101, _2103, _2105), vec3(_2101, _2103, _2105));
                        D _2723;
                        D _2724;
                        D _2725;
                        if (_2106 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2693 = dot(vec3(_1636, _1637, _1638), vec3(_2101, _2103, _2105));
                            D _2709 = spvNClamp((1.0 / (_2106 - (_2693 * _2693))) * dot(vec3(_2067, _2068, _2069), vec3((_2693 * _1636) - _2101, (_2693 * _1637) - _2103, (_2693 * _1638) - _2105)), 0.0, 1.0);
                            D _2713 = (_2709 * _2101) + _2067;
                            D _2714 = (_2709 * _2103) + _2068;
                            D _2715 = (_2709 * _2105) + _2069;
                            D _2719 = inversesqrt(dot(vec3(_2713, _2714, _2715), vec3(_2713, _2714, _2715)));
                            _2723 = _2713 * _2719;
                            _2724 = _2714 * _2719;
                            _2725 = _2715 * _2719;
                        }
                        else
                        {
                            _2723 = _2067;
                            _2724 = _2068;
                            _2725 = _2069;
                        }
                        _3290 = _2099;
                        _3291 = (_1178 * _1178) * _2099;
                        _3292 = _2080 * _2067;
                        _3293 = _2080 * _2068;
                        _3294 = _2080 * _2069;
                        _3295 = _2082 * _2070;
                        _3296 = _2082 * _2071;
                        _3297 = _2082 * _2072;
                        _3298 = _2723;
                        _3299 = _2724;
                        _3300 = _2725;
                    }
                    D _3310 = _3291 + 1.0;
                    D _3315 = _3298 - _238;
                    D _3316 = _3299 - _239;
                    D _3317 = _3300 - _240;
                    D _3321 = inversesqrt(dot(vec3(_3315, _3316, _3317), vec3(_3315, _3316, _3317)));
                    D _3322 = _3321 * _3315;
                    D _3323 = _3321 * _3316;
                    D _3324 = _3321 * _3317;
                    D _3331 = spvNClamp(dot(vec3(_422, _423, _424), vec3(_3322, _3323, _3324)), 0.0, 1.0);
                    D _3332 = _640 * _640;
                    D _3338 = spvNClamp(((1.0 - _3332) * _1178) * sqrt(_3290), 0.0, 1.0);
                    D _3352 = exp2(log2(spvNClamp((((_3338 * 0.25) * (_3338 + (_3332 * 3.0))) * (1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_241, _243, _244), vec3(_3322, _3323, _3324))))) + (_3332 * _3332), 0.0, 1.0)) * 0.25);
                    D _3356 = spvNClamp(dot(vec3(_3292, _3293, _3294), vec3(_3295, _3296, _3297)), 0.0, 1.0);
                    D _3358 = _3352 * _3352;
                    D _3359 = _3358 * _3358;
                    D _3711;
                    if (_3356 < 1.0)
                    {
                        D _3702 = sqrt(spvNClamp((1.0 / (_3356 + 1.0)) * (1.0 - _3356), 0.0, 1.0));
                        _3711 = (1.0 / spvNClamp(((_3702 * 0.25) * (_3702 + (_3358 * 3.0))) + _3359, 0.0, 1.0)) * _3359;
                    }
                    else
                    {
                        _3711 = 1.0;
                    }
                    D _3715 = ((_3331 * _3331) * (_3359 + (-1.0))) + 1.0;
                    D _3718 = spvNMax(0.0, (((dot(vec3(_422, _423, _424), vec3(_3295, _3296, _3297)) + dot(vec3(_422, _423, _424), vec3(_3292, _3293, _3294))) * 0.5) + _3291) * (1.0 / (_3310 * _3310))) * 0.3183098733425140380859375;
                    D _3721 = ((_3718 * _3359) * _3711) * (1.0 / (_3715 * _3715));
                    D _3723 = (_1335 * _1161) * _3290;
                    D _3725 = (_1335 * _1162) * _3290;
                    D _3727 = (_1335 * _1163) * _3290;
                    _1640 = _3721 * _3723;
                    _1642 = _3721 * _3725;
                    _1644 = _3721 * _3727;
                    _1646 = _3718 * _3723;
                    _1648 = _3718 * _3725;
                    _1650 = _3718 * _3727;
                }
                else
                {
                    _1640 = 0.0;
                    _1642 = 0.0;
                    _1644 = 0.0;
                    _1646 = 0.0;
                    _1648 = 0.0;
                    _1650 = 0.0;
                }
                frontier_phi_47_pred = _1642 + _1147;
                frontier_phi_47_pred_1 = _1137;
                frontier_phi_47_pred_2 = _1138;
                frontier_phi_47_pred_3 = _1139;
                frontier_phi_47_pred_4 = _1140;
                frontier_phi_47_pred_5 = _1141;
                frontier_phi_47_pred_6 = _1142;
                frontier_phi_47_pred_7 = _1143;
                frontier_phi_47_pred_8 = _1144;
                frontier_phi_47_pred_9 = _1145;
                frontier_phi_47_pred_10 = _1640 + _1146;
                frontier_phi_47_pred_11 = _1644 + _1148;
                frontier_phi_47_pred_12 = _1646 + _1149;
                frontier_phi_47_pred_13 = _1648 + _1150;
                frontier_phi_47_pred_14 = _1650 + _1151;
            }
            _826 = frontier_phi_47_pred;
            _806 = frontier_phi_47_pred_1;
            _808 = frontier_phi_47_pred_2;
            _810 = frontier_phi_47_pred_3;
            _812 = frontier_phi_47_pred_4;
            _814 = frontier_phi_47_pred_5;
            _816 = frontier_phi_47_pred_6;
            _818 = frontier_phi_47_pred_7;
            _820 = frontier_phi_47_pred_8;
            _822 = frontier_phi_47_pred_9;
            _824 = frontier_phi_47_pred_10;
            _828 = frontier_phi_47_pred_11;
            _830 = frontier_phi_47_pred_12;
            _832 = frontier_phi_47_pred_13;
            _834 = frontier_phi_47_pred_14;
            uint _1153 = _1152 + 1u;
            if (_1153 == _798)
            {
                break;
            }
            else
            {
                _1137 = _806;
                _1138 = _808;
                _1139 = _810;
                _1140 = _812;
                _1141 = _814;
                _1142 = _816;
                _1143 = _818;
                _1144 = _820;
                _1145 = _822;
                _1146 = _824;
                _1147 = _826;
                _1148 = _828;
                _1149 = _830;
                _1150 = _832;
                _1151 = _834;
                _1152 = _1153;
                continue;
            }
        }
        _805 = _806;
        _807 = _808;
        _809 = _810;
        _811 = _812;
        _813 = _814;
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
    }
    vec4 _875 = textureLod(sampler3D(TranslucentBasePass_TranslucencyLightingVolumeEnvironmentA, View_SharedBilinearClampedSampler), vec3((_230 - View._m0[180u].x) * View._m0[182u].x, (_231 - View._m0[180u].y) * View._m0[182u].y, (_232 - View._m0[180u].z) * View._m0[182u].z), 0.0);
    D _899;
    D _900;
    D _901;
    if (_369 < 1.0)
    {
        _899 = _346.x / ((_391 / _368) + 1.0);
        _900 = _346.y / ((_392 / _368) + 1.0);
        _901 = _346.z / ((_393 / _368) + 1.0);
    }
    else
    {
        _899 = 0.0;
        _900 = 0.0;
        _901 = 0.0;
    }
    D _918 = spvNClamp(_622, 0.0, 1.0);
    D _931 = _470 * _470;
    D _932 = _931 * _470;
    D _939 = ((_422 - _559) * _932) + _559;
    D _940 = ((_423 - _560) * _932) + _560;
    D _941 = ((_424 - _561) * _932) + _561;
    D _945 = inversesqrt(dot(vec3(_939, _940, _941), vec3(_939, _940, _941)));
    D _954 = 10.0 / spvNMax(9.9999997473787516355514526367188e-06, _931);
    D _983 = fma(_229, View._m0[2u].x, fma(_228, View._m0[1u].x, View._m0[0u].x * _227)) + View._m0[3u].x;
    D _987 = fma(_229, View._m0[2u].y, fma(_228, View._m0[1u].y, View._m0[0u].y * _227)) + View._m0[3u].y;
    D _991 = fma(_229, View._m0[2u].z, fma(_228, View._m0[1u].z, View._m0[0u].z * _227)) + View._m0[3u].z;
    D _995 = fma(_229, View._m0[2u].w, fma(_228, View._m0[1u].w, View._m0[0u].w * _227)) + View._m0[3u].w;
    D _1002 = ((_939 * _103) * _945) + _227;
    D _1003 = ((_940 * _103) * _945) + _228;
    D _1004 = ((_941 * _103) * _945) + _229;
    D _1037 = 1.0 / _995;
    D _1038 = _1037 * _983;
    D _1039 = _1037 * _987;
    D _1043 = (_1037 * _991) + (0.0500000007450580596923828125 / _995);
    D _1044 = 1.0 / (fma(_1004, View._m0[2u].w, fma(_1003, View._m0[1u].w, View._m0[0u].w * _1002)) + View._m0[3u].w);
    D _1055 = 1.0 / ((View._m0[36u].w * _954) + _995);
    D _1058 = (_1044 * (fma(_1004, View._m0[2u].x, fma(_1003, View._m0[1u].x, View._m0[0u].x * _1002)) + View._m0[3u].x)) - _1038;
    D _1059 = (_1044 * (fma(_1004, View._m0[2u].y, fma(_1003, View._m0[1u].y, View._m0[0u].y * _1002)) + View._m0[3u].y)) - _1039;
    D _1061 = (_1055 * ((View._m0[36u].x * _954) + _983)) - _1038;
    D _1062 = (_1055 * ((View._m0[36u].y * _954) + _987)) - _1039;
    D _1067 = sqrt((_1058 * _1058) + (_1059 * _1059)) * 0.5;
    D _1086 = spvNMin(1.0 - (spvNMax(0.0, abs((_1067 * _1038) + _1058) - _1067) / abs(_1058)), 1.0 - (spvNMax(0.0, abs((_1067 * _1039) + _1059) - _1067) / abs(_1059))) / _1067;
    D _1087 = _1086 * _1058;
    D _1088 = _1086 * _1059;
    D _1089 = _1086 * ((_1044 * (fma(_1004, View._m0[2u].z, fma(_1003, View._m0[1u].z, View._m0[0u].z * _1002)) + View._m0[3u].z)) - _1043);
    uvec2 _1095 = uvec2(textureSize(TranslucentBasePass_HZBTexture, int(0u)));
    D _1097 = D(int(_1095.x));
    D _1099 = D(int(_1095.y));
    uint _1120 = max(1u, min(uint(ceil((spvNClamp((1.0 / spvNMax(9.9999997473787516355514526367188e-05, sqrt((_1087 * _1087) + (_1088 * _1088)))) * sqrt((_1061 * _1061) + (_1062 * _1062)), 0.0, 1.0) * 8.0) + _265)), 8u));
    D _1125 = ((_1038 * 0.5) + 0.5) * TranslucentBasePass_2._m0[198u].x;
    D _1126 = (0.5 - (_1039 * 0.5)) * TranslucentBasePass_2._m0[198u].y;
    D _1129 = (TranslucentBasePass_2._m0[198u].x * 0.0625) * _1087;
    D _1132 = (TranslucentBasePass_2._m0[198u].y * (-0.0625)) * _1088;
    D _1133 = _1089 * 0.125;
    D _1135 = spvNMax(abs(_1089), _1043 - ((1.0 / (fma(_103, View._m0[38u].w, 0.0) + _995)) * (fma(_103, View._m0[38u].z, 0.0) + _991))) * 0.125;
    D _1303;
    D _1305;
    D _1307;
    D _1309;
    if (_1120 == 0u)
    {
        _1303 = 0.0;
        _1305 = 0.0;
        _1307 = 0.0;
        _1309 = 0.0;
    }
    else
    {
        D frontier_phi_60;
        D frontier_phi_60_1;
        D frontier_phi_60_2;
        D frontier_phi_60_3;
        D _1553 = 0.0;
        uint _1555 = 0u;
        D _1554;
        D _1557;
        bool _1580;
        for (;;)
        {
            _1557 = D(_1555);
            D _1558 = _1557 + _265;
            vec4 _1572 = texelFetch(TranslucentBasePass_HZBTexture, ivec2_(uvec2(uint(int(floor(((_1558 * _1129) + _1125) * _1097))), uint(int(floor(((_1558 * _1132) + _1126) * _1099))))), int(0u));
            D _1574 = _1572.x;
            _1554 = ((_1558 * _1133) + _1043) - _1574;
            _1580 = (abs(((-0.0) - _1135) - _1554) < _1135) && (_1574 != 0.0);
            if (_1580)
            {
                D _1989 = (_1555 == 0u) ? (_1554 - _1133) : _1553;
                D _1996 = abs(((_265 + (-1.0)) + _1557) + spvNClamp(_1989 / (_1989 - _1554), 0.0, 1.0));
                D _2001 = spvNMin(_1996 * 0.125, 1.0);
                frontier_phi_60 = 1.0 - (_2001 * _2001);
                frontier_phi_60_1 = (_1996 * _1133) + _1043;
                frontier_phi_60_2 = (_1996 * _1132) + _1126;
                frontier_phi_60_3 = (_1996 * _1129) + _1125;
                break;
            }
            else
            {
                uint _1556 = _1555 + 1u;
                if (_1556 < _1120)
                {
                    _1553 = _1554;
                    _1555 = _1556;
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
        _1303 = frontier_phi_60_3;
        _1305 = frontier_phi_60_2;
        _1307 = frontier_phi_60_1;
        _1309 = frontier_phi_60;
    }
    D _1317 = (spvNClamp(_1303 * TranslucentBasePass_2._m0[198u].z, 0.0, 1.0) * 2.0) + (-1.0);
    D _1318 = 1.0 - (spvNClamp(_1305 * TranslucentBasePass_2._m0[198u].w, 0.0, 1.0) * 2.0);
    D _1458;
    D _1460;
    D _1462;
    D _1464;
    if (_1309 > 0.0)
    {
        D _1459;
        D _1461;
        D _1463;
        D _2205;
        D _1451;
        bool _1457;
        for (;;)
        {
            D _1410 = ((View._m0[73u].x * _1307) + View._m0[73u].y) + (1.0 / ((View._m0[73u].z * _1307) - View._m0[73u].w));
            D _1434 = _1410 * _1317;
            D _1435 = _1410 * _1318;
            D _1446 = (_227 - View._m0[63u].x) - fma(_1410, View._m0[62u].x, fma(_1435, View._m0[61u].x, _1434 * View._m0[60u].x));
            D _1448 = (_228 - View._m0[63u].y) - fma(_1410, View._m0[62u].y, fma(_1435, View._m0[61u].y, _1434 * View._m0[60u].y));
            D _1450 = (_229 - View._m0[63u].z) - fma(_1410, View._m0[62u].z, fma(_1435, View._m0[61u].z, _1434 * View._m0[60u].z));
            _1451 = dot(vec3(_1446, _1448, _1450), vec3(_1446, _1448, _1450));
            _1457 = View._m0[175u].w != 0.0;
            if (_1457)
            {
                if (floatBitsToUint(View._m0[175u]).y == 0u)
                {
                    _1459 = 0.0;
                    _1461 = 0.0;
                    _1463 = 0.0;
                    _2205 = 0.0;
                    break;
                }
            }
            D _1847 = fma(_1307, View._m0[140u].w, fma(_1318, View._m0[139u].w, View._m0[138u].w * _1317)) + View._m0[141u].w;
            D _1848 = (fma(_1307, View._m0[140u].x, fma(_1318, View._m0[139u].x, View._m0[138u].x * _1317)) + View._m0[141u].x) / _1847;
            D _1849 = (fma(_1307, View._m0[140u].y, fma(_1318, View._m0[139u].y, View._m0[138u].y * _1317)) + View._m0[141u].y) / _1847;
            D _1866 = spvNClamp((abs((spvNMin(spvNMax(_1848, -1.0), 1.0) - _1317) * 0.5) * 5.0) + (-4.0), 0.0, 1.0);
            D _1867 = spvNClamp((abs((spvNMin(spvNMax(_1849, -1.0), 1.0) - _1318) * 0.5) * 5.0) + (-4.0), 0.0, 1.0);
            uvec2 _1920 = uvec2(textureSize(TranslucentBasePass_PrevSceneColor, int(0u)));
            vec4 _1941 = texelFetch(TranslucentBasePass_PrevSceneColor, ivec2_(uvec2(uint(min(int(uint(max(int(uint(int(D(int(_1920.x)) * ((TranslucentBasePass_2._m0[199u].x * spvNMin(spvNMax(_1848 - ((D(int(uint(_1848 > 0.0) - uint(_1848 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1848) + (-1.0))), -1.0), 1.0)) + TranslucentBasePass_2._m0[199u].z)))), int(uint(int(TranslucentBasePass_2._m0[200u].x)))))), int(uint(int(TranslucentBasePass_2._m0[200u].x + TranslucentBasePass_2._m0[200u].z)) + 4294967295u))), uint(min(int(uint(max(int(uint(int(D(int(_1920.y)) * ((TranslucentBasePass_2._m0[199u].y * spvNMin(spvNMax(_1849 - ((D(int(uint(_1849 > 0.0) - uint(_1849 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1849) + (-1.0))), -1.0), 1.0)) + TranslucentBasePass_2._m0[199u].w)))), int(uint(int(TranslucentBasePass_2._m0[200u].y)))))), int(uint(int(TranslucentBasePass_2._m0[200u].y + TranslucentBasePass_2._m0[200u].w)) + 4294967295u))))), int(0u));
            _1459 = View._m0[165u].x * spvNMin(_1941.x, 65504.0);
            _1461 = View._m0[165u].x * spvNMin(_1941.y, 65504.0);
            _1463 = View._m0[165u].x * spvNMin(_1941.z, 65504.0);
            _2205 = spvNMax(0.0, 1.0 - dot(vec2(_1866, _1867), vec2(_1866, _1867)));
            break;
        }
        _1458 = _1459;
        _1460 = _1461;
        _1462 = _1463;
        _1464 = (_2205 * _1309) * spvNClamp(1.0 / spvNMax(9.9999997473787516355514526367188e-06, (_931 * _931) * _1451), 0.0, 1.0);
    }
    else
    {
        _1458 = 0.0;
        _1460 = 0.0;
        _1462 = 0.0;
        _1464 = 0.0;
    }
    D _1498 = fma(_232, View._m0[14u].w, fma(_231, View._m0[13u].w, _230 * View._m0[12u].w)) + View._m0[15u].w;
    D _1503 = (((fma(_232, View._m0[14u].x, fma(_231, View._m0[13u].x, _230 * View._m0[12u].x)) + View._m0[15u].x) / _1498) * 0.5) + 0.5;
    D _1504 = 0.5 - (((fma(_232, View._m0[14u].y, fma(_231, View._m0[13u].y, _230 * View._m0[12u].y)) + View._m0[15u].y) / _1498) * 0.5);
    D _1533 = sqrt(((_228 * _228) + (_227 * _227)) + (_229 * _229));
    D _1551 = spvNMax(0.0, ((1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_227, _228, _229), vec3(View._m0[68u].xyz())))) * _1533) * View._m0[280u].w);
    D _1957;
    D _1959;
    D _1961;
    D _1963;
    D _1965;
    D _1967;
    if (_1533 < _1551)
    {
        _1957 = 0.0;
        _1959 = 0.0;
        _1961 = 0.0;
        _1963 = 1.0;
        _1965 = 1.0;
        _1967 = 1.0;
    }
    else
    {
        D _1975 = (1.0 / _1533) * _1551;
        uvec4 _1982 = floatBitsToUint(View._m0[220u]);
        uint _1983 = _1982.y;
        uint _1985 = (_1983 != 1u) ? 4294967295u : 0u;
        uint _2321;
        if (_1983 > 1u)
        {
            D _132[4];
            _132[0u] = 0.0;
            _132[1u] = 0.0;
            _132[2u] = 0.0;
            _132[3u] = 0.0;
            uint _3167 = 0u;
            bool _3173;
            for (;;)
            {
                _3173 = _3167 < floatBitsToUint(View._m0[220u]).y;
                if (_3173)
                {
                    uint _3594 = _3167 + 237u;
                    D _3606 = View._m0[_3594].x - View._m0[75u].x;
                    D _3607 = View._m0[_3594].y - View._m0[75u].y;
                    D _3608 = View._m0[_3594].z - View._m0[75u].z;
                    D _3609 = dot(vec3(_3606, _3607, _3608), vec3(_238, _239, _240));
                    D _3616 = dot(vec3(_3606, _3607, _3608), vec3(_3606, _3607, _3608)) - (View._m0[_3594].w * View._m0[_3594].w);
                    D _3618 = (_3609 * _3609) - _3616;
                    D _3736;
                    if ((_3616 < 0.0) && (!(_3618 < 0.0)))
                    {
                        D _3730 = sqrt(_3618);
                        _3736 = spvNMin(abs(_3730 + _3609), abs(_3609 - _3730));
                    }
                    else
                    {
                        _3736 = 0.0;
                    }
                    _132[_3167] = _3736;
                }
                uint _3168 = _3167 + 1u;
                if (_3168 == 4u)
                {
                    break;
                }
                else
                {
                    _3167 = _3168;
                    continue;
                }
            }
            D _3746 = (_265 * 0.99989998340606689453125) * dot(vec4(_132[0u], _132[1u], _132[2u], _132[3u]), vec4(1.0));
            uint frontier_phi_59_97_ladder;
            if (_132[0u] > _3746)
            {
                frontier_phi_59_97_ladder = 0u;
            }
            else
            {
                D _3814 = _132[1u] + _132[0u];
                uint frontier_phi_59_97_ladder_103_ladder;
                if (_3814 > _3746)
                {
                    frontier_phi_59_97_ladder_103_ladder = 1u;
                }
                else
                {
                    D _3844 = _3814 + _132[2u];
                    uint frontier_phi_59_97_ladder_103_ladder_109_ladder;
                    if (_3844 > _3746)
                    {
                        frontier_phi_59_97_ladder_103_ladder_109_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder;
                        if ((_3844 + _132[3u]) > _3746)
                        {
                            frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder = _1985;
                        }
                        frontier_phi_59_97_ladder_103_ladder_109_ladder = frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder;
                    }
                    frontier_phi_59_97_ladder_103_ladder = frontier_phi_59_97_ladder_103_ladder_109_ladder;
                }
                frontier_phi_59_97_ladder = frontier_phi_59_97_ladder_103_ladder;
            }
            _2321 = frontier_phi_59_97_ladder;
        }
        else
        {
            _2321 = _1985;
        }
        D frontier_phi_38_59_ladder;
        D frontier_phi_38_59_ladder_1;
        D frontier_phi_38_59_ladder_2;
        D frontier_phi_38_59_ladder_3;
        D frontier_phi_38_59_ladder_4;
        D frontier_phi_38_59_ladder_5;
        if (_2321 == 4294967295u)
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
            uint _3174 = _2321 + 221u;
            D _3182 = spvNMin(View._m0[_3174].w, 0.9900000095367431640625);
            uint _3183 = _2321 + 225u;
            uint _3190 = _2321 + 229u;
            uint _3197 = _2321 + 233u;
            uint _3202 = _2321 + 241u;
            D _3649;
            D _3650;
            D _3651;
            if (TranslucentBasePass_2._m0[146u].x > 0.0)
            {
                vec4 _3641 = textureLod(sampler2D(TranslucentBasePass_Shared_Fog_FarIntegratedScatteringTexture, View_SharedBilinearClampedSampler), vec2(spvNMin(spvNMax(View._m0[278u].x * _1503, View._m0[279u].x), View._m0[280u].x), spvNMin(spvNMax(View._m0[278u].y * _1504, View._m0[279u].y), View._m0[280u].y)), 0.0);
                _3649 = View._m0[164u].z * _3641.x;
                _3650 = View._m0[164u].z * _3641.y;
                _3651 = View._m0[164u].z * _3641.z;
            }
            else
            {
                _3649 = 0.0;
                _3650 = 0.0;
                _3651 = 0.0;
            }
            D _3655 = dot(vec3((-0.0) - View._m0[218u].x, (-0.0) - View._m0[218u].y, (-0.0) - View._m0[218u].z), vec3(_241, _243, _244));
            D _3668 = (((_3655 * _3655) + 1.0) * 0.0397887341678142547607421875) * exp2(log2(spvNMax(0.0, _3655 + 1.25)) * (-1.5));
            D _3748;
            if (View._m0[_3183].x == 0.0)
            {
                _3748 = 0.0;
            }
            else
            {
                D _3796 = (((_1975 * _229) - View._m0[_3183].z) + View._m0[75u].z) * View._m0[_3183].y;
                D _3797 = ((1.0 - _1975) * _229) * View._m0[_3183].y;
                D _3802 = exp2((-0.0) - _3796);
                D frontier_phi_98_99_ladder;
                if (abs(_3797) > 0.00999999977648258209228515625)
                {
                    frontier_phi_98_99_ladder = ((_3802 - exp2(((-0.0) - _3797) - _3796)) * View._m0[_3183].x) * (1.0 / _3797);
                }
                else
                {
                    frontier_phi_98_99_ladder = (View._m0[_3183].x * 0.693147182464599609375) * _3802;
                }
                _3748 = frontier_phi_98_99_ladder;
            }
            D _3752 = _3748 * (1.0 - _3182);
            D _3756 = (1.0 - View._m0[_3190].x) * View._m0[_3197].x;
            D _3757 = (1.0 - View._m0[_3190].y) * View._m0[_3197].x;
            D _3758 = (1.0 - View._m0[_3190].z) * View._m0[_3197].x;
            D _3759 = (-0.0) - (_1533 - _1551);
            D _3787 = 1.0 - spvNClamp(exp2(_3752 * _3759), 0.0, 1.0);
            frontier_phi_38_59_ladder = spvNClamp(exp2((_3752 + _3758) * _3759), 0.0, 1.0);
            frontier_phi_38_59_ladder_1 = spvNClamp(exp2((_3752 + _3757) * _3759), 0.0, 1.0);
            frontier_phi_38_59_ladder_2 = spvNClamp(exp2((_3752 + _3756) * _3759), 0.0, 1.0);
            frontier_phi_38_59_ladder_3 = (((_3182 * View._m0[_3174].z) * (((View._m0[219u].z * View._m0[_3202].x) * _3668) + _3651)) * spvNClamp(exp2(_3758 * _3759), 0.0, 1.0)) * _3787;
            frontier_phi_38_59_ladder_4 = (((_3182 * View._m0[_3174].y) * (((View._m0[219u].y * View._m0[_3202].x) * _3668) + _3650)) * spvNClamp(exp2(_3757 * _3759), 0.0, 1.0)) * _3787;
            frontier_phi_38_59_ladder_5 = (((_3182 * View._m0[_3174].x) * (((View._m0[219u].x * View._m0[_3202].x) * _3668) + _3649)) * spvNClamp(exp2(_3756 * _3759), 0.0, 1.0)) * _3787;
        }
        _1957 = frontier_phi_38_59_ladder_5;
        _1959 = frontier_phi_38_59_ladder_4;
        _1961 = frontier_phi_38_59_ladder_3;
        _1963 = frontier_phi_38_59_ladder_2;
        _1965 = frontier_phi_38_59_ladder_1;
        _1967 = frontier_phi_38_59_ladder;
    }
    D _2253;
    D _2254;
    D _2255;
    D _2256;
    D _2257;
    D _2258;
    if (TranslucentBasePass_2._m0[148u].x > 0.0)
    {
        D _2233 = spvNMin(spvNMax(View._m0[278u].x * _1503, View._m0[279u].x), View._m0[280u].x);
        D _2234 = spvNMin(spvNMax(View._m0[278u].y * _1504, View._m0[279u].y), View._m0[280u].y);
        D _2235 = spvNMin(spvNMax((View._m0[275u].z * spvNMax(0.0, spvNMin(View._m0[276u].z * log2((View._m0[276u].x * _1498) + View._m0[276u].y), View._m0[274u].z + (-1.0)) + 0.5)) * View._m0[278u].z, View._m0[279u].z), View._m0[280u].z);
        vec4 _2238 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeATexture, View_SharedBilinearClampedSampler), vec3(_2233, _2234, _2235), 0.0);
        vec4 _2245 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeBTexture, View_SharedBilinearClampedSampler), vec3(_2233, _2234, _2235), 0.0);
        _2253 = View._m0[164u].z * _2238.x;
        _2254 = View._m0[164u].z * _2238.y;
        _2255 = View._m0[164u].z * _2238.z;
        _2256 = _2245.x;
        _2257 = _2245.y;
        _2258 = _2245.z;
    }
    else
    {
        _2253 = 0.0;
        _2254 = 0.0;
        _2255 = 0.0;
        _2256 = 1.0;
        _2257 = 1.0;
        _2258 = 1.0;
    }
    D _2265 = (1.0 - _627) + (_627 * _446);
    D _2266 = (1.0 - _630) + (_630 * _446);
    D _2267 = (1.0 - _633) + (_633 * _446);
    SV_Target.x = View._m0[164u].y * ((((_2256 * _1957) + _2253) * _2265) + ((_1963 * (((((((((_472 * _448) * _698) * spvNMax(1.0, ((_527 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_527 * 4.79510021209716796875)) + (((_527 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _448)) * _448))) * _829) + _805) * _449) + _811) + ((((_899 * _595) * spvNClamp(1.0 - (_611 * _601), 0.0, 1.0)) * ((View._m0[164u].z * _875.x) + _817)) * _918)) + ((_712 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1458)) + 29.8973522186279296875) * _1464) + (-29.8973522186279296875)) + _823)) * spvNClamp(_690, 0.0, 1.0)))) * _2256));
    SV_Target.y = ((((_2257 * _1959) + _2254) * _2266) + ((_1965 * (((((((((_473 * _448) * _698) * spvNMax(1.0, ((_528 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_528 * 4.79510021209716796875)) + (((_528 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _448)) * _448))) * _831) + _807) * _449) + _813) + ((((_900 * _595) * spvNClamp(1.0 - (_612 * _601), 0.0, 1.0)) * ((View._m0[164u].z * _875.y) + _819)) * _918)) + ((_712 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1460)) + 29.8973522186279296875) * _1464) + (-29.8973522186279296875)) + _825)) * spvNClamp(_691, 0.0, 1.0)))) * _2257)) * View._m0[164u].y;
    SV_Target.z = ((((_2258 * _1961) + _2255) * _2267) + ((_1967 * (((((((((_474 * _448) * _698) * spvNMax(1.0, ((_529 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_529 * 4.79510021209716796875)) + (((_529 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _448)) * _448))) * _833) + _809) * _449) + _815) + ((((_901 * _595) * ((View._m0[164u].z * _875.z) + _821)) * spvNClamp(1.0 - (_613 * _601), 0.0, 1.0)) * _918)) + ((_712 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1462)) + 29.8973522186279296875) * _1464) + (-29.8973522186279296875)) + _827)) * spvNClamp(_692, 0.0, 1.0)))) * _2258)) * View._m0[164u].y;
    SV_Target.w = dot(vec3(_2265, _2266, _2267), vec3(0.2125999927520751953125, 0.715200006961822509765625, 0.072200000286102294921875));
    SV_Target_1.x = _2265;
    SV_Target_1.y = _2266;
    SV_Target_1.z = _2267;
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
} // namespace S_lass_Thin_Wide_Late_Character