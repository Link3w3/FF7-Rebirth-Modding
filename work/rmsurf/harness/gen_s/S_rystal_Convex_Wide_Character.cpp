namespace S_rystal_Convex_Wide_Character {
using namespace cpuglsl;
static D _4321;
static D _4317;
static D _4318;
static D _4319;
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









void discard_cond(bool _4307)
{
    if (_4307)
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
    D _225 = fma(gl_FragCoord.z, View._m0[54u].w, fma(gl_FragCoord.y, View._m0[53u].w, View._m0[52u].w * gl_FragCoord.x)) + View._m0[55u].w;
    D _226 = (fma(gl_FragCoord.z, View._m0[54u].x, fma(gl_FragCoord.y, View._m0[53u].x, View._m0[52u].x * gl_FragCoord.x)) + View._m0[55u].x) / _225;
    D _227 = (fma(gl_FragCoord.z, View._m0[54u].y, fma(gl_FragCoord.y, View._m0[53u].y, View._m0[52u].y * gl_FragCoord.x)) + View._m0[55u].y) / _225;
    D _228 = (fma(gl_FragCoord.z, View._m0[54u].z, fma(gl_FragCoord.y, View._m0[53u].z, View._m0[52u].z * gl_FragCoord.x)) + View._m0[55u].z) / _225;
    D _229 = _226 - View._m0[78u].x;
    D _230 = _227 - View._m0[78u].y;
    D _231 = _228 - View._m0[78u].z;
    D _236 = inversesqrt(dot(vec3(_226, _227, _228), vec3(_226, _227, _228)));
    D _237 = _236 * _226;
    D _238 = _236 * _227;
    D _239 = _236 * _228;
    D _240 = (-0.0) - _237;
    D _242 = (-0.0) - _238;
    D _243 = (-0.0) - _239;
    vec4 _261 = texelFetch(View_SpatiotemporalBlueNoiseVolumeTexture, ivec3_(uvec3(uint(int(gl_FragCoord.x)) & 127u, uint(int(gl_FragCoord.y)) & 127u, ((floatBitsToUint(View._m0[175u]).x & 7u) + uint(roundEven(CONSTANT_CONTEXT))) & 63u)), int(0u));
    D _264 = _261.x;
    D _265 = _261.y;
    vec4 _271 = texture(sampler2D(Material_Texture2D_0, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _279 = texture(sampler2D(Material_Texture2D_1, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _284 = texture(sampler2D(Material_Texture2D_2, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _291 = (_284.x * 2.0) + (-1.0);
    D _293 = (_284.y * 2.0) + (-1.0);
    D _300 = sqrt(spvNMax(0.0, 1.0 - dot(vec2(_291, _293), vec2(_291, _293))));
    D _304 = inversesqrt(dot(vec3(_291, _293, _300), vec3(_291, _293, _300)));
    D _305 = _304 * _291;
    D _306 = _304 * _293;
    D _307 = _304 * _300;
    vec4 _310 = texture(sampler2D(Material_Texture2D_3, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _315 = texture(sampler2D(Material_Texture2D_4, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _317 = _315.x;
    vec4 _320 = texture(sampler2D(Material_Texture2D_14, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.z, TEXCOORD.w), View._m0[155u].y);
    D _322 = _320.x;
    D _323 = _322 * _317;
    D _324 = spvNMin(_317, _322);
    D _326 = (1.0 - _324) + _323;
    D _327 = _326 * _326;
    D _330 = 1.0 - ((_327 * _327) * _326);
    D _331 = _330 * _330;
    vec4 _339 = texture(sampler2D(Material_Texture2D_7, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _345 = vec4(g_R.Muddiness.x, g_R.Muddiness.y, g_R.Muddiness.z, 0.0);
    vec4 _352 = texture(sampler2D(Material_Texture2D_19, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _357 = texture(sampler2D(Material_Texture2D_20, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _367 = g_R.TransparencyLog2;
    D _368 = exp2(_367);
    vec4 _371 = texture(sampler2D(Material_Texture2D_21, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _378 = texture(sampler2D(Material_Texture2D_22, View_SharedAnisotropic4XClampedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _383 = 1.0 / spvNMax(9.9999999747524270787835121154785e-07, _378.x * 100.0);
    D _390 = g_R.TransmittanceLog2.x;
    D _391 = g_R.TransmittanceLog2.y;
    D _392 = g_R.TransmittanceLog2.z;
    D _399 = inversesqrt(dot(vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z), vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z)));
    D _400 = _399 * g_R.Normal.x;
    D _401 = _399 * g_R.Normal.y;
    D _402 = _399 * g_R.Normal.z;
    D _405 = fma(_402, TEXCOORD_11.x, fma(_401, ((TEXCOORD_10.z * TEXCOORD_11.y) - (TEXCOORD_10.y * TEXCOORD_11.z)) * TEXCOORD_11.w, _400 * TEXCOORD_10.x));
    D _408 = fma(_402, TEXCOORD_11.y, fma(_401, ((TEXCOORD_10.x * TEXCOORD_11.z) - (TEXCOORD_10.z * TEXCOORD_11.x)) * TEXCOORD_11.w, _400 * TEXCOORD_10.y));
    D _411 = fma(_402, TEXCOORD_11.z, fma(_401, ((TEXCOORD_10.y * TEXCOORD_11.x) - (TEXCOORD_10.x * TEXCOORD_11.y)) * TEXCOORD_11.w, _400 * TEXCOORD_10.z));
    D _415 = inversesqrt(dot(vec3(_405, _408, _411), vec3(_405, _408, _411)));
    D _416 = _415 * _405;
    D _417 = _415 * _408;
    D _418 = _415 * _411;
    bool _431;
    if (Primitive._m0[27u].w > ((_261.w * 0.99609375) + 0.001953125))
    {
        _431 = ((_264 * 0.99609375) + 0.001953125) < 1.0;
    }
    else
    {
        _431 = false;
    }
    (void)((_431 ? 1.0 : (-1.0)) < 0.0);
    D _437 = spvNClamp(g_R.BaseColor.x, 0.0, 1.0);
    D _438 = spvNClamp(g_R.BaseColor.y, 0.0, 1.0);
    D _439 = spvNClamp(g_R.BaseColor.z, 0.0, 1.0);
    D _440 = spvNClamp(g_R.Metallic, 0.0, 1.0);
    D _441 = spvNClamp(g_R.Roughness, 0.0, 1.0);
    D _442 = spvNClamp(g_R.AO, 0.0, 1.0);
    D _443 = spvNClamp(g_R.Opacity, 0.0, 1.0);
    D _445 = dFdxFine(_416);
    D _446 = dFdxFine(_417);
    D _447 = dFdxFine(_418);
    D _451 = dFdyFine(_416);
    D _452 = dFdyFine(_417);
    D _453 = dFdyFine(_418);
    D _464 = sqrt(spvNClamp(spvNMin((dot(vec3(_451, _452, _453), vec3(_451, _452, _453)) + dot(vec3(_445, _446, _447), vec3(_445, _446, _447))) * 0.15915493667125701904296875, 0.180000007152557373046875) + (_441 * _441), 0.0, 1.0));
    D _465 = 1.0 - _440;
    D _466 = _465 * _437;
    D _467 = _465 * _438;
    D _468 = _465 * _439;
    D _473 = _440 * (_437 + (-0.159951984882354736328125));
    D _474 = _440 * (_438 + (-0.159951984882354736328125));
    D _475 = _440 * (_439 + (-0.159951984882354736328125));
    D _476 = _473 + 0.159951984882354736328125;
    D _478 = _474 + 0.159951984882354736328125;
    D _479 = _475 + 0.159951984882354736328125;
    D _486 = spvNClamp(D(View._m0[220u].x > 1.0), 0.0, 1.0);
    D _514 = ((exp2(log2(spvNMax(0.0, _473 + 0.13995198905467987060546875) * 1.020408153533935546875) * 1.39999997615814208984375) - _476) * _486) + _476;
    D _515 = ((exp2(log2(spvNMax(0.0, _474 + 0.13995198905467987060546875) * 1.020408153533935546875) * 1.39999997615814208984375) - _478) * _486) + _478;
    D _516 = ((exp2(log2(spvNMax(0.0, _475 + 0.13995198905467987060546875) * 1.020408153533935546875) * 1.39999997615814208984375) - _479) * _486) + _479;
    D _521 = (_514 * 0.449999988079071044921875) + _466;
    D _522 = (_515 * 0.449999988079071044921875) + _467;
    D _523 = (_516 * 0.449999988079071044921875) + _468;
    D _530 = dot(vec3(_416, _417, _418), vec3(_240, _242, _243));
    D _536 = (_530 * _416) + _237;
    D _537 = (_530 * _417) + _238;
    D _538 = (_530 * _418) + _239;
    D _542 = abs(_530);
    D _546 = (_536 * 2.0) + (_542 * _416);
    D _547 = (_537 * 2.0) + (_542 * _417);
    D _548 = (_538 * 2.0) + (_542 * _418);
    D _552 = inversesqrt(dot(vec3(_546, _547, _548), vec3(_546, _547, _548)));
    D _553 = _546 * _552;
    D _554 = _547 * _552;
    D _555 = _548 * _552;
    D _556 = spvNMax(9.9999997473787516355514526367188e-06, _542);
    D _574 = 1.0 - _464;
    D _588 = ((spvNMin(_574 * _574, exp2(_556 * (-9.27999973297119140625))) * _574) + (0.0425000004470348358154296875 - (_464 * 0.0274999998509883880615234375))) * 1.03999996185302734375;
    D _594 = 1.0 - spvNClamp((((_464 * 0.02199999988079071044921875) + (-0.039999999105930328369140625)) + _588) + (((1.03999996185302734375 - (_464 * 0.572000026702880859375)) - _588) * 0.159951984882354736328125), 0.0, 1.0);
    D _595 = spvNMax(0.001000000047497451305389404296875, spvNMax(0.0, (View._m0[73u].y - _102) + (1.0 / ((-0.0) - View._m0[73u].w))));
    D _598 = log2(spvNMax(0.0, _368));
    D _600 = exp2(_598 * _595);
    D _604 = log2(spvNMax(0.0, exp2(_390)));
    D _605 = log2(spvNMax(0.0, exp2(_391)));
    D _606 = log2(spvNMax(0.0, exp2(_392)));
    D _610 = exp2(_604 * _595);
    D _611 = exp2(_605 * _595);
    D _612 = exp2(_606 * _595);
    D _614 = exp2(_598 * 0.001000000047497451305389404296875);
    D _621 = 1.0 - _443;
    D _623 = (_594 * _621) * _600;
    D _626 = ((_623 * _610) * _614) * exp2(_604 * 0.001000000047497451305389404296875);
    D _629 = ((_623 * _611) * _614) * exp2(_605 * 0.001000000047497451305389404296875);
    D _632 = ((_623 * _612) * _614) * exp2(_606 * 0.001000000047497451305389404296875);
    D _639 = spvNMax(0.039999999105930328369140625, _464);
    D _655 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_639 * _556) + 0.02669160068035125732421875) / (_556 + 0.4664950072765350341796875)) * exp2(((1.0 / _639) * _556) * log2(_639)), 0.0, 1.0));
    D _656 = 1.0 - _556;
    D _657 = _656 * _656;
    D _670 = _657 * _657;
    D _672 = (_670 * _656) * exp2(log2((exp2((_639 * 4.7702999114990234375) * log2(_556)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _639);
    D _675 = (1.0 / _655) * (1.0 - _655);
    D _682 = _655 - _672;
    D _689 = ((_675 * _514) + 1.0) * ((_682 * _514) + _672);
    D _690 = ((_675 * _515) + 1.0) * ((_682 * _515) + _672);
    D _691 = ((_675 * _516) + 1.0) * ((_682 * _516) + _672);
    D _697 = spvNClamp(1.0 - dot(vec3(_689, _690, _691), vec3(0.3333333432674407958984375)), 0.0, 1.0);
    D _711 = spvNClamp((_442 + (-1.0)) + exp2(log2(_556 + _442) * exp2((-1.0) - (_464 * 16.0))), 0.0, 1.0);
    D _771;
    D _773;
    D _775;
    D _777;
    D _779;
    D _781;
    D _783;
    D _785;
    D _787;
    if (floatBitsToUint(TranslucentBasePass_2._m0[0u]).z == 0u)
    {
        _771 = 0.0;
        _773 = 0.0;
        _775 = 0.0;
        _777 = 0.0;
        _779 = 0.0;
        _781 = 0.0;
        _783 = 0.0;
        _785 = 0.0;
        _787 = 0.0;
    }
    else
    {
        D _1221;
        uint _802;
        bool _803;
        for (;;)
        {
            _802 = floatBitsToUint(TranslucentBasePass_2._m0[7u]).z;
            _803 = _802 == 0u;
            if (!_803)
            {
                uint _1386;
                uint _1289 = 0u;
                for (;;)
                {
                    if (_102 < TranslucentBasePass._m0[_1289 + 32u])
                    {
                        _1386 = _1289;
                        break;
                    }
                    else
                    {
                        uint _1290 = _1289 + 1u;
                        if (_1290 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                        {
                            _1289 = _1290;
                            continue;
                        }
                        else
                        {
                            _1386 = _802;
                            break;
                        }
                    }
                }
                if (_1386 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                {
                    uint _1736 = _1386 << 2u;
                    uint _1737 = _1736 + 9u;
                    uint _1744 = _1736 + 10u;
                    uint _1751 = _1736 + 11u;
                    uint _1758 = _1736 + 12u;
                    uint _1765 = _1386 + 25u;
                    D _1791 = fma(_231, TranslucentBasePass_2._m0[_1751].z, fma(_230, TranslucentBasePass_2._m0[_1744].z, TranslucentBasePass_2._m0[_1737].z * _229)) + TranslucentBasePass_2._m0[_1758].z;
                    D _1795 = fma(_231, TranslucentBasePass_2._m0[_1751].w, fma(_230, TranslucentBasePass_2._m0[_1744].w, TranslucentBasePass_2._m0[_1737].w * _229)) + TranslucentBasePass_2._m0[_1758].w;
                    D _1796 = (fma(_231, TranslucentBasePass_2._m0[_1751].x, fma(_230, TranslucentBasePass_2._m0[_1744].x, TranslucentBasePass_2._m0[_1737].x * _229)) + TranslucentBasePass_2._m0[_1758].x) / _1795;
                    D _1797 = (fma(_231, TranslucentBasePass_2._m0[_1751].y, fma(_230, TranslucentBasePass_2._m0[_1744].y, TranslucentBasePass_2._m0[_1737].y * _229)) + TranslucentBasePass_2._m0[_1758].y) / _1795;
                    bool _1804 = (_1797 <= TranslucentBasePass_2._m0[_1765].w) && ((_1796 <= TranslucentBasePass_2._m0[_1765].z) && ((_1796 >= TranslucentBasePass_2._m0[_1765].x) && (_1797 >= TranslucentBasePass_2._m0[_1765].y)));
                    D _1222;
                    if (_1804)
                    {
                        D _2161 = dFdyFine(_1796);
                        D _2162 = dFdyFine(_1797);
                        D _2163 = dFdyFine(_1791);
                        D _2164 = dFdxFine(_1796);
                        D _2165 = dFdxFine(_1797);
                        D _2166 = dFdxFine(_1791);
                        D _2169 = (_2165 * _2163) - (_2166 * _2162);
                        D _2172 = (_2166 * _2161) - (_2164 * _2163);
                        D _2175 = (_2164 * _2162) - (_2165 * _2161);
                        D _2185 = 1.0 / spvNMax(abs(_2175), sqrt(((_2172 * _2172) + (_2175 * _2175)) + (_2169 * _2169)) * 0.100000001490116119384765625);
                        D _2191 = D(int(uint(_2175 > 0.0) - uint(_2175 < 0.0)));
                        D _2192 = _2169 * TranslucentBasePass_2._m0[29u].z;
                        D _2194 = (_2192 * _2185) * _2191;
                        D _2195 = _2172 * TranslucentBasePass_2._m0[29u].w;
                        D _2197 = (_2195 * _2185) * _2191;
                        D _2789;
                        D _2791;
                        if (dot(vec2(_2169, _2172), vec2(_2169, _2172)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2789 = 0.0;
                            _2791 = 0.0;
                        }
                        else
                        {
                            D _3159 = (-0.0) - _2169;
                            D _3160 = (-0.0) - _2172;
                            D _3164 = inversesqrt(dot(vec2(_3159, _3160), vec2(_3159, _3160)));
                            _2789 = _3164 * _3159;
                            _2791 = _3164 * _3160;
                        }
                        D _2793 = _265 + (-0.5);
                        D _2798 = _264 + 0.5;
                        D _2801 = ((_2791 * _2793) + (_1796 * TranslucentBasePass_2._m0[29u].x)) + (_2789 * _2798);
                        D _2804 = ((_2789 * _2793) + (_1797 * TranslucentBasePass_2._m0[29u].y)) + (_2791 * _2798);
                        D _2805 = _2801 + (-0.5);
                        D _2806 = _2804 + (-0.5);
                        D _2807 = trunc(_2805);
                        D _2808 = trunc(_2806);
                        D _2809 = _2805 - _2807;
                        D _2810 = _2806 - _2808;
                        D _2811 = _2807 * TranslucentBasePass_2._m0[29u].z;
                        D _2812 = _2808 * TranslucentBasePass_2._m0[29u].w;
                        D _2815 = (_2807 + (-0.5)) - _2801;
                        D _2816 = (_2808 + (-0.5)) - _2804;
                        D _2817 = dot(vec2(_2815, _2816), vec2(_2194, _2197));
                        D _2820 = _2817 + _2197;
                        D _2823 = _2191 * (_2185 * (_2195 + _2192));
                        D _2824 = _2823 + _2817;
                        D _2825 = _2817 + _2194;
                        vec4 _2831 = textureGather((sampler2D(ShadowMaps[_1386 + 0u], View_SharedPointClampedSampler)), vec2(_2811, _2812));
                        D _2832 = _2831.x;
                        D _2833 = _2831.y;
                        D _2834 = _2831.z;
                        D _2835 = _2831.w;
                        D _2872 = 1.525902189314365386962890625e-05 - _1791;
                        D _2903 = (_2807 + 1.5) - _2801;
                        D _2904 = dot(vec2(_2903, _2816), vec2(_2194, _2197));
                        D _2907 = _2904 + _2197;
                        D _2908 = _2823 + _2904;
                        D _2909 = _2904 + _2194;
                        vec4 _2911 = textureGatherOffset((sampler2D(ShadowMaps[_1386 + 0u], View_SharedPointClampedSampler)), vec2(_2811, _2812), ivec2(2, 0));
                        D _2912 = _2911.x;
                        D _2913 = _2911.y;
                        D _2914 = _2911.z;
                        D _2915 = _2911.w;
                        D _2981 = (_2808 + 1.5) - _2804;
                        D _2982 = dot(vec2(_2815, _2981), vec2(_2194, _2197));
                        D _2985 = _2982 + _2197;
                        D _2986 = _2823 + _2982;
                        D _2987 = _2982 + _2194;
                        vec4 _2989 = textureGatherOffset((sampler2D(ShadowMaps[_1386 + 0u], View_SharedPointClampedSampler)), vec2(_2811, _2812), ivec2(0, 2));
                        D _2990 = _2989.x;
                        D _2991 = _2989.y;
                        D _2992 = _2989.z;
                        D _2993 = _2989.w;
                        D _3058 = dot(vec2(_2903, _2981), vec2(_2194, _2197));
                        D _3061 = _3058 + _2197;
                        D _3062 = _2823 + _3058;
                        D _3063 = _3058 + _2194;
                        vec4 _3065 = textureGatherOffset((sampler2D(ShadowMaps[_1386 + 0u], View_SharedPointClampedSampler)), vec2(_2811, _2812), ivec2(2));
                        D _3066 = _3065.x;
                        D _3067 = _3065.y;
                        D _3068 = _3065.z;
                        D _3069 = _3065.w;
                        D _3134 = 1.0 - _2809;
                        vec4 _3157 = vec4((((((_2835 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2872 + _2835) + (spvNMin(abs(_2817), 0.0) * D(int(uint(_2817 > 0.0) - uint(_2817 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3134) + ((_2834 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2872 + _2834) + (spvNMin(abs(_2825), 0.0) * D(int(uint(_2825 > 0.0) - uint(_2825 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2915 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2872 + _2915) + (spvNMin(abs(_2904), 0.0) * D(int(uint(_2904 > 0.0) - uint(_2904 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2914 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2872 + _2914) + (spvNMin(abs(_2909), 0.0) * D(int(uint(_2909 > 0.0) - uint(_2909 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2809), (((((_2832 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2872 + _2832) + (spvNMin(abs(_2820), 0.0) * D(int(uint(_2820 > 0.0) - uint(_2820 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3134) + ((_2833 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2872 + _2833) + (spvNMin(abs(_2824), 0.0) * D(int(uint(_2824 > 0.0) - uint(_2824 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2912 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2872 + _2912) + (spvNMin(abs(_2907), 0.0) * D(int(uint(_2907 > 0.0) - uint(_2907 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2913 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2872 + _2913) + (spvNMin(abs(_2908), 0.0) * D(int(uint(_2908 > 0.0) - uint(_2908 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2809), (((((_2993 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2872 + _2993) + (spvNMin(abs(_2982), 0.0) * D(int(uint(_2982 > 0.0) - uint(_2982 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3134) + ((_2992 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2872 + _2992) + (spvNMin(abs(_2987), 0.0) * D(int(uint(_2987 > 0.0) - uint(_2987 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3069 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2872 + _3069) + (spvNMin(abs(_3058), 0.0) * D(int(uint(_3058 > 0.0) - uint(_3058 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3068 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2872 + _3068) + (spvNMin(abs(_3063), 0.0) * D(int(uint(_3063 > 0.0) - uint(_3063 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2809), (((((_2990 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2872 + _2990) + (spvNMin(abs(_2985), 0.0) * D(int(uint(_2985 > 0.0) - uint(_2985 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _3134) + ((_2991 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2872 + _2991) + (spvNMin(abs(_2986), 0.0) * D(int(uint(_2986 > 0.0) - uint(_2986 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_3066 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2872 + _3066) + (spvNMin(abs(_3061), 0.0) * D(int(uint(_3061 > 0.0) - uint(_3061 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_3067 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2872 + _3067) + (spvNMin(abs(_3062), 0.0) * D(int(uint(_3062 > 0.0) - uint(_3062 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2809));
                        _1222 = dot(_3157, vec4(1.0 - _2810, 1.0, 1.0, _2810)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        _1222 = 1.0;
                    }
                    if (_1804)
                    {
                        _1221 = _1222;
                        break;
                    }
                }
            }
            if (floatBitsToUint(TranslucentBasePass_2._m0[30u]).y == 0u)
            {
                _1221 = 1.0;
                break;
            }
            D _1262 = fma(_231, TranslucentBasePass_2._m0[35u].z, fma(_230, TranslucentBasePass_2._m0[34u].z, TranslucentBasePass_2._m0[33u].z * _229)) + TranslucentBasePass_2._m0[36u].z;
            D _1266 = fma(_231, TranslucentBasePass_2._m0[35u].w, fma(_230, TranslucentBasePass_2._m0[34u].w, TranslucentBasePass_2._m0[33u].w * _229)) + TranslucentBasePass_2._m0[36u].w;
            D _1267 = (fma(_231, TranslucentBasePass_2._m0[35u].x, fma(_230, TranslucentBasePass_2._m0[34u].x, TranslucentBasePass_2._m0[33u].x * _229)) + TranslucentBasePass_2._m0[36u].x) / _1266;
            D _1268 = (fma(_231, TranslucentBasePass_2._m0[35u].y, fma(_230, TranslucentBasePass_2._m0[34u].y, TranslucentBasePass_2._m0[33u].y * _229)) + TranslucentBasePass_2._m0[36u].y) / _1266;
            uvec4 _1272 = floatBitsToUint(TranslucentBasePass_2._m0[32u]);
            uint _1273 = _1272.x;
            uint _1274 = _1272.y;
            uint _1275 = _1272.z;
            uint _1280 = uint(int(floor(_1267)));
            uint _1281 = uint(int((-0.0) - floor(_1268)));
            if (!((int(_1281) < int(_1272.w)) && ((int(_1280) < int(_1275)) && ((int(_1280) >= int(_1273)) && (int(_1281) >= int(_1274))))))
            {
                _1221 = 1.0;
                break;
            }
            D _1349 = dFdyFine(_1267);
            D _1350 = dFdyFine(_1268);
            D _1351 = dFdyFine(_1262);
            D _1352 = dFdxFine(_1267);
            D _1353 = dFdxFine(_1268);
            D _1354 = dFdxFine(_1262);
            D _1357 = (_1353 * _1351) - (_1354 * _1350);
            D _1360 = (_1354 * _1349) - (_1352 * _1351);
            D _1363 = (_1352 * _1350) - (_1353 * _1349);
            D _1374 = 1.0 / spvNMax(abs(_1363), sqrt(((_1360 * _1360) + (_1363 * _1363)) + (_1357 * _1357)) * 0.100000001490116119384765625);
            D _1380 = D(int(uint(_1363 > 0.0) - uint(_1363 < 0.0)));
            D _1663;
            D _1665;
            if (dot(vec2(_1357, _1360), vec2(_1357, _1360)) < 1.0000000195414813782625560981111e-24)
            {
                _1663 = 0.0;
                _1665 = 0.0;
            }
            else
            {
                D _1729 = (-0.0) - _1357;
                D _1730 = (-0.0) - _1360;
                D _1734 = inversesqrt(dot(vec2(_1729, _1730), vec2(_1729, _1730)));
                _1663 = _1734 * _1729;
                _1665 = _1734 * _1730;
            }
            D _1671 = _265 + (-0.5);
            D _1679 = (((_1665 * _1671) + (_1663 * _264)) * 2.0) + (_1663 * 0.5);
            D _1680 = (((_1665 * _264) + (_1663 * _1671)) * 2.0) + (_1665 * 0.5);
            D _1686 = _1679 + (fract(_1267) * 256.0);
            D _1687 = _1680 + (fract(_1268) * 256.0);
            D _1700 = dot(vec2((floor(_1686) + 0.5) - _1686, (floor(_1687) + 0.5) - _1687), vec2(((_1357 * 256.0) * _1374) * _1380, ((_1360 * 256.0) * _1374) * _1380));
            D _1706 = (_1679 * 0.00390625) + _1267;
            D _1707 = (_1680 * 0.00390625) + _1268;
            uint _1719 = ((uint(int((-0.0) - floor(_1707))) - _1274) * (_1275 - _1273)) + (uint(int(floor(_1706))) - _1273);
            D _2133;
            D _2136;
            if ((texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowLoadedTileData, int(_1719 >> 5u)).x & (1u << (_1719 & 31u))) == 0u)
            {
                _2133 = 3.0000000054977557577780399428115e+38;
                _2136 = 0.0;
            }
            else
            {
                uvec4 _2158 = uvec4(texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileIndices, int(_1719)));
                uint _2159 = _2158.x;
                D frontier_phi_51_52_ladder;
                D frontier_phi_51_52_ladder_1;
                if (int(_2159) > int(4294967295u))
                {
                    uint _2775 = (uint(floor(fract(_1706) * 256.0)) + (_2159 << 16u)) + (uint(floor(fract(_1707) * 256.0)) << 8u);
                    uvec4 _2778 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileData, int(_2775 >> 1u));
                    uint _2779 = _2778.x;
                    D _2787 = D((((_2775 & 1u) == 0u) ? _2779 : (_2779 >> 16u)) & 65535u) * 1.525902189314365386962890625e-05;
                    D frontier_phi_51_52_ladder_73_ladder;
                    D frontier_phi_51_52_ladder_73_ladder_1;
                    if (_2787 != 1.0)
                    {
                        vec4 _3588 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthRanges, int(_2159));
                        D _3590 = _3588.y;
                        frontier_phi_51_52_ladder_73_ladder = 1.0 / _3590;
                        frontier_phi_51_52_ladder_73_ladder_1 = (_3590 * _2787) + _3588.x;
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
                _2133 = frontier_phi_51_52_ladder_1;
                _2136 = frontier_phi_51_52_ladder;
            }
            _1221 = spvNClamp(((((1.525902189314365386962890625e-05 - _1262) + _2133) + (spvNMin(abs(_1700), _2136 * 10.0) * D(int(uint(_1700 > 0.0) - uint(_1700 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0);
            break;
        }
        D _1336;
        if ((floatBitsToUint(Primitive._m0[27u]).z & 2u) == 0u)
        {
            _1336 = 1.0;
        }
        else
        {
            _1336 = View._m0[188u].y;
        }
        uvec4 _1340 = floatBitsToUint(View._m0[220u]);
        uint _1341 = _1340.y;
        uint _1344 = (_1341 != 1u) ? 4294967295u : 0u;
        uint _1661;
        if (_1341 > 1u)
        {
            D _130[4];
            _130[0u] = 0.0;
            _130[1u] = 0.0;
            _130[2u] = 0.0;
            _130[3u] = 0.0;
            uint _2118 = 0u;
            bool _2124;
            for (;;)
            {
                _2124 = _2118 < floatBitsToUint(View._m0[220u]).y;
                if (_2124)
                {
                    uint _2726 = _2118 + 237u;
                    D _2740 = View._m0[_2726].x - View._m0[75u].x;
                    D _2741 = View._m0[_2726].y - View._m0[75u].y;
                    D _2742 = View._m0[_2726].z - View._m0[75u].z;
                    D _2743 = dot(vec3(_2740, _2741, _2742), vec3(_237, _238, _239));
                    D _2750 = dot(vec3(_2740, _2741, _2742), vec3(_2740, _2741, _2742)) - (View._m0[_2726].w * View._m0[_2726].w);
                    D _2752 = (_2743 * _2743) - _2750;
                    D _3364;
                    if ((_2750 < 0.0) && (!(_2752 < 0.0)))
                    {
                        D _3358 = sqrt(_2752);
                        _3364 = spvNMin(abs(_3358 + _2743), abs(_2743 - _3358));
                    }
                    else
                    {
                        _3364 = 0.0;
                    }
                    _130[_2118] = _3364;
                }
                uint _2119 = _2118 + 1u;
                if (_2119 == 4u)
                {
                    break;
                }
                else
                {
                    _2118 = _2119;
                    continue;
                }
            }
            D _3375 = (_264 * 0.99989998340606689453125) * dot(vec4(_130[0u], _130[1u], _130[2u], _130[3u]), vec4(1.0));
            uint frontier_phi_32_83_ladder;
            if (_130[0u] > _3375)
            {
                frontier_phi_32_83_ladder = 0u;
            }
            else
            {
                D _3726 = _130[1u] + _130[0u];
                uint frontier_phi_32_83_ladder_94_ladder;
                if (_3726 > _3375)
                {
                    frontier_phi_32_83_ladder_94_ladder = 1u;
                }
                else
                {
                    D _3810 = _3726 + _130[2u];
                    uint frontier_phi_32_83_ladder_94_ladder_102_ladder;
                    if (_3810 > _3375)
                    {
                        frontier_phi_32_83_ladder_94_ladder_102_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder;
                        if ((_3810 + _130[3u]) > _3375)
                        {
                            frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder = _1344;
                        }
                        frontier_phi_32_83_ladder_94_ladder_102_ladder = frontier_phi_32_83_ladder_94_ladder_102_ladder_108_ladder;
                    }
                    frontier_phi_32_83_ladder_94_ladder = frontier_phi_32_83_ladder_94_ladder_102_ladder;
                }
                frontier_phi_32_83_ladder = frontier_phi_32_83_ladder_94_ladder;
            }
            _1661 = frontier_phi_32_83_ladder;
        }
        else
        {
            _1661 = _1344;
        }
        D _2125;
        if (_1661 == 4294967295u)
        {
            _2125 = _1336;
        }
        else
        {
            _2125 = View._m0[_1661 + 241u].x * _1336;
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
        if (_2125 > 0.0)
        {
            D _2759 = spvNClamp((TranslucentBasePass_2._m0[7u].x * _102) + TranslucentBasePass_2._m0[7u].y, 0.0, 1.0);
            D _2763 = ((_2759 * _2759) * (1.0 - _1221)) + _1221;
            D frontier_phi_3_49_ladder_72_ladder;
            D frontier_phi_3_49_ladder_72_ladder_1;
            D frontier_phi_3_49_ladder_72_ladder_2;
            D frontier_phi_3_49_ladder_72_ladder_3;
            D frontier_phi_3_49_ladder_72_ladder_4;
            D frontier_phi_3_49_ladder_72_ladder_5;
            D frontier_phi_3_49_ladder_72_ladder_6;
            D frontier_phi_3_49_ladder_72_ladder_7;
            D frontier_phi_3_49_ladder_72_ladder_8;
            if (_2763 > 0.0)
            {
                D _3377 = dot(vec3(_416, _417, _418), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3380 = spvNMax(0.0, _3377);
                D _3381 = dot(vec3(_240, _242, _243), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3387 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3381 * 2.0) + 2.0));
                D _3390 = spvNClamp(_3387 * (_530 + _3377), 0.0, 1.0);
                D _3405 = sqrt(spvNMax(0.0, 1.0 - ((1.0 - (_530 * _530)) * 0.444444477558135986328125)));
                D _3409 = (_536 * 0.666666686534881591796875) - (_3405 * _416);
                D _3410 = (_537 * 0.666666686534881591796875) - (_3405 * _417);
                D _3411 = (_538 * 0.666666686534881591796875) - (_3405 * _418);
                D _3415 = inversesqrt(dot(vec3(_3409, _3410, _3411), vec3(_3409, _3410, _3411)));
                D _3422 = dot(vec3((-0.0) - (_3415 * _3409), (-0.0) - (_3415 * _3410), (-0.0) - (_3415 * _3411)), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _3425 = _639 * _639;
                D _3426 = _3425 * _3425;
                D _3430 = ((_3390 * _3390) * (_3426 + (-1.0))) + 1.0;
                D _3436 = (_3380 * 2.0) * _556;
                D _3441 = 1.0 - spvNMax(9.9999997473787516355514526367188e-06, spvNMin(_3387 * (_3381 + 1.0), 1.0));
                D _3442 = _3441 * _3441;
                D _3444 = (_3442 * _3442) * _3441;
                D _3449 = spvNMin(dot(vec3(_514, _515, _516), vec3(16.666667938232421875)), 1.0);
                D _3462 = spvNMax(0.039999999105930328369140625, _639);
                D _3475 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_3462 * _3380) + 0.02669160068035125732421875) / (_3380 + 0.4664950072765350341796875)) * exp2(((1.0 / _3462) * _3380) * log2(_3462)), 0.0, 1.0));
                D _3476 = 1.0 - _3380;
                D _3477 = _3476 * _3476;
                D _3489 = ((_3477 * _3477) * _3476) * exp2(log2((exp2((_3462 * 4.7702999114990234375) * log2(_3380)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _3462);
                D _3492 = (1.0 / _3475) * (1.0 - _3475);
                D _3496 = (_3492 * _514) + 1.0;
                D _3497 = (_3492 * _515) + 1.0;
                D _3498 = (_3492 * _516) + 1.0;
                D _3499 = _3475 - _3489;
                D _3513 = spvNClamp(1.0 - dot(vec3(_3496 * ((_3499 * _514) + _3489), _3497 * ((_3499 * _515) + _3489), _3498 * ((_3499 * _516) + _3489)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                D _3516 = (((_3426 * 0.3183098733425140380859375) * _3380) * (1.0 / (_3430 * _3430))) * (0.5 / ((_3425 * ((_556 + _3380) - _3436)) + _3436));
                D _3517 = _3380 * 0.3183098733425140380859375;
                D _3520 = ((_3422 * _3422) + 1.0) * 0.05968309938907623291015625;
                D _3522 = spvNMin(1.0, _442);
                D _3524 = (_442 + 1.0) - _3522;
                D _3525 = _3524 * _3524;
                D _3528 = 1.0 - ((_3525 * _3525) * _3524);
                D _3529 = _3528 * _3528;
                D _3534 = ((_3529 * _3529) * (_3528 * (_442 - _3522))) + _3522;
                D _3537 = sqrt(spvNMax(0.0, 1.0 - _3534));
                D _3542 = 1.0 - spvNClamp((_639 * 3.5) + (-0.5), 0.0, 1.0);
                D _3543 = _3542 * _3542;
                D _3553 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_670 * _3537) * spvNClamp(1.0 - ((_3543 * _3543) * _3542), 0.0, 1.0))) * _3380, 0.0, 1.0);
                D _3558 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _3537)) * _3380, 0.0, 1.0);
                D _3560 = spvNMin(_2763, _3553 * _3553);
                D _3561 = spvNMin(_2763, _3558 * _3558);
                D _3562 = spvNMin(_2763, _3534);
                D _3563 = _2125 * TranslucentBasePass_2._m0[4u].x;
                D _3564 = _2125 * TranslucentBasePass_2._m0[4u].y;
                D _3565 = _2125 * TranslucentBasePass_2._m0[4u].z;
                frontier_phi_3_49_ladder_72_ladder = (_3520 * _3565) * _3562;
                frontier_phi_3_49_ladder_72_ladder_1 = (((_3563 * _466) * _3517) * _3513) * _3561;
                frontier_phi_3_49_ladder_72_ladder_2 = (((_3564 * _467) * _3517) * _3513) * _3561;
                frontier_phi_3_49_ladder_72_ladder_3 = (((_3565 * _468) * _3517) * _3513) * _3561;
                frontier_phi_3_49_ladder_72_ladder_4 = (((_3516 * _3563) * spvNClamp(((_3449 - _514) * _3444) + _514, 0.0, 1.0)) * _3496) * _3560;
                frontier_phi_3_49_ladder_72_ladder_5 = (((_3516 * _3564) * spvNClamp(((_3449 - _515) * _3444) + _515, 0.0, 1.0)) * _3497) * _3560;
                frontier_phi_3_49_ladder_72_ladder_6 = (((_3516 * _3565) * spvNClamp(((_3449 - _516) * _3444) + _516, 0.0, 1.0)) * _3498) * _3560;
                frontier_phi_3_49_ladder_72_ladder_7 = (_3520 * _3563) * _3562;
                frontier_phi_3_49_ladder_72_ladder_8 = (_3520 * _3564) * _3562;
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
        _771 = frontier_phi_3_49_ladder_1;
        _773 = frontier_phi_3_49_ladder_2;
        _775 = frontier_phi_3_49_ladder_3;
        _777 = frontier_phi_3_49_ladder_4;
        _779 = frontier_phi_3_49_ladder_5;
        _781 = frontier_phi_3_49_ladder_6;
        _783 = frontier_phi_3_49_ladder_7;
        _785 = frontier_phi_3_49_ladder_8;
        _787 = frontier_phi_3_49_ladder;
    }
    uvec4 _791 = floatBitsToUint(TranslucentBasePass_2._m0[0u]);
    uint _792 = _791.x;
    uint _797 = min(min(texelFetch(TranslucentBasePass_Shared_Forward_NumCulledLightsGrid, int(0u)).x, _792), _792);
    D _804;
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
    if (_797 == 0u)
    {
        _804 = _771;
        _806 = _773;
        _808 = _775;
        _810 = _777;
        _812 = _779;
        _814 = _781;
        _816 = _783;
        _818 = _785;
        _820 = _787;
        _822 = 0.0;
        _824 = 0.0;
        _826 = 0.0;
        _828 = 0.0;
        _830 = 0.0;
        _832 = 0.0;
    }
    else
    {
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
        D _1136 = _771;
        D _1137 = _773;
        D _1138 = _775;
        D _1139 = _777;
        D _1140 = _779;
        D _1141 = _781;
        D _1142 = _783;
        D _1143 = _785;
        D _1144 = _787;
        D _1145 = 0.0;
        D _1146 = 0.0;
        D _1147 = 0.0;
        D _1148 = 0.0;
        D _1149 = 0.0;
        D _1150 = 0.0;
        uint _1151 = 0u;
        D _1155;
        D _1156;
        D _1157;
        D _1158;
        D _1160;
        D _1161;
        D _1162;
        D _1164;
        D _1165;
        D _1166;
        uint _1168;
        D _1170;
        D _1171;
        D _1173;
        D _1174;
        D _1175;
        D _1177;
        D _1178;
        uint _1180;
        D _1183;
        D _1184;
        D _1185;
        D _1186;
        uint _1189;
        D _1191;
        D _1192;
        D _1193;
        D _1194;
        D _1197;
        D _1198;
        D _1199;
        D _1200;
        D _1203;
        D _1204;
        D _1205;
        D _1206;
        D _1209;
        D _1210;
        D _1211;
        D _1212;
        bool _1215;
        bool _1216;
        bool _1220;
        for (;;)
        {
            vec4 _1154 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(0u));
            _1155 = _1154.x;
            _1156 = _1154.y;
            _1157 = _1154.z;
            _1158 = _1154.w;
            vec4 _1159 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(1u));
            _1160 = _1159.x;
            _1161 = _1159.y;
            _1162 = _1159.z;
            vec4 _1163 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(2u));
            _1164 = _1163.x;
            _1165 = _1163.y;
            _1166 = _1163.z;
            _1168 = floatBitsToUint(_1163.w);
            vec4 _1169 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(3u));
            _1170 = _1169.x;
            _1171 = _1169.y;
            vec4 _1172 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(4u));
            _1173 = _1172.x;
            _1174 = _1172.y;
            _1175 = _1172.z;
            vec4 _1176 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(5u));
            _1177 = _1176.x;
            _1178 = _1176.y;
            _1180 = floatBitsToUint(_1176.z);
            vec4 _1182 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(6u));
            _1183 = _1182.x;
            _1184 = _1182.y;
            _1185 = _1182.z;
            _1186 = _1182.w;
            _1189 = floatBitsToUint(texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(7u)).x);
            vec4 _1190 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(8u));
            _1191 = _1190.x;
            _1192 = _1190.y;
            _1193 = _1190.z;
            _1194 = _1190.w;
            vec4 _1196 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(9u));
            _1197 = _1196.x;
            _1198 = _1196.y;
            _1199 = _1196.z;
            _1200 = _1196.w;
            vec4 _1202 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(10u));
            _1203 = _1202.x;
            _1204 = _1202.y;
            _1205 = _1202.z;
            _1206 = _1202.w;
            vec4 _1208 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(11u));
            _1209 = _1208.x;
            _1210 = _1208.y;
            _1211 = _1208.z;
            _1212 = _1208.w;
            _1215 = (_1168 & 131072u) != 0u;
            _1216 = _1170 > (-2.0);
            _1220 = (_1168 & 16384u) == 0u;
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
            if (_1220)
            {
                D _1614;
                if (_1215)
                {
                    uint _1579 = _1189 + 0u;
                    uvec2 _1582 = uvec2(textureSize(ShadowMaps[(_1579)], int(0u)));
                    D _1584 = D(int(_1582.x));
                    D _1586 = D(int(_1582.y));
                    D _1587 = 1.0 / _1584;
                    D _1588 = 1.0 / _1586;
                    D _1600 = fma(_231, _1205, fma(_230, _1199, _1193 * _229)) + _1211;
                    D _1604 = fma(_231, _1206, fma(_230, _1200, _1194 * _229)) + _1212;
                    D _1605 = (fma(_231, _1203, fma(_230, _1197, _1191 * _229)) + _1209) / _1604;
                    D _1606 = (fma(_231, _1204, fma(_230, _1198, _1192 * _229)) + _1210) / _1604;
                    D frontier_phi_28_27_ladder;
                    if ((_1606 <= _1186) && ((_1605 <= _1185) && ((_1605 >= _1183) && (_1606 >= _1184))))
                    {
                        D _2002 = dFdyFine(_1605);
                        D _2003 = dFdyFine(_1606);
                        D _2004 = dFdyFine(_1600);
                        D _2005 = dFdxFine(_1605);
                        D _2006 = dFdxFine(_1606);
                        D _2007 = dFdxFine(_1600);
                        D _2010 = (_2006 * _2004) - (_2007 * _2003);
                        D _2013 = (_2007 * _2002) - (_2005 * _2004);
                        D _2016 = (_2005 * _2003) - (_2006 * _2002);
                        D _2026 = 1.0 / spvNMax(abs(_2016), sqrt(((_2013 * _2013) + (_2016 * _2016)) + (_2010 * _2010)) * 0.100000001490116119384765625);
                        D _2032 = D(int(uint(_2016 > 0.0) - uint(_2016 < 0.0)));
                        D _2033 = _2010 * _1587;
                        D _2035 = (_2033 * _2026) * _2032;
                        D _2036 = _2013 * _1588;
                        D _2038 = (_2036 * _2026) * _2032;
                        D _2321;
                        D _2323;
                        if (dot(vec2(_2010, _2013), vec2(_2010, _2013)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2321 = 0.0;
                            _2323 = 0.0;
                        }
                        else
                        {
                            D _2664 = (-0.0) - _2010;
                            D _2665 = (-0.0) - _2013;
                            D _2669 = inversesqrt(dot(vec2(_2664, _2665), vec2(_2664, _2665)));
                            _2321 = _2669 * _2664;
                            _2323 = _2669 * _2665;
                        }
                        D _2325 = _265 + (-0.5);
                        D _2330 = _264 + 0.5;
                        D _2333 = ((_2323 * _2325) + (_1605 * _1584)) + (_2321 * _2330);
                        D _2336 = ((_2321 * _2325) + (_1606 * _1586)) + (_2323 * _2330);
                        D _2337 = _2333 + (-0.5);
                        D _2338 = _2336 + (-0.5);
                        D _2339 = trunc(_2337);
                        D _2340 = trunc(_2338);
                        D _2341 = _2337 - _2339;
                        D _2342 = _2338 - _2340;
                        D _2343 = _2339 * _1587;
                        D _2344 = _2340 * _1588;
                        D _2347 = (_2339 + (-0.5)) - _2333;
                        D _2348 = (_2340 + (-0.5)) - _2336;
                        D _2349 = dot(vec2(_2347, _2348), vec2(_2035, _2038));
                        D _2352 = _2349 + _2038;
                        D _2355 = _2032 * (_2026 * (_2036 + _2033));
                        D _2356 = _2355 + _2349;
                        D _2357 = _2349 + _2035;
                        vec4 _2361 = textureGather((sampler2D(ShadowMaps[_1579], View_SharedPointClampedSampler)), vec2(_2343, _2344));
                        D _2402 = 1.525902189314365386962890625e-05 - _1600;
                        D _2425 = (_2339 + 1.5) - _2333;
                        D _2426 = dot(vec2(_2425, _2348), vec2(_2035, _2038));
                        D _2429 = _2426 + _2038;
                        D _2430 = _2355 + _2426;
                        D _2431 = _2426 + _2035;
                        vec4 _2435 = textureGatherOffset((sampler2D(ShadowMaps[_1579], View_SharedPointClampedSampler)), vec2(_2343, _2344), ivec2(2, 0));
                        D _2499 = (_2340 + 1.5) - _2336;
                        D _2500 = dot(vec2(_2347, _2499), vec2(_2035, _2038));
                        D _2503 = _2500 + _2038;
                        D _2504 = _2355 + _2500;
                        D _2505 = _2500 + _2035;
                        vec4 _2507 = textureGatherOffset((sampler2D(ShadowMaps[_1579], View_SharedPointClampedSampler)), vec2(_2343, _2344), ivec2(0, 2));
                        D _2569 = dot(vec2(_2425, _2499), vec2(_2035, _2038));
                        D _2572 = _2569 + _2038;
                        D _2573 = _2355 + _2569;
                        D _2574 = _2569 + _2035;
                        vec4 _2576 = textureGatherOffset((sampler2D(ShadowMaps[_1579], View_SharedPointClampedSampler)), vec2(_2343, _2344), ivec2(2));
                        D _2638 = 1.0 - _2341;
                        vec4 _2661 = vec4((((spvNClamp((((_2402 + _2361.w) + (spvNMin(abs(_2349), 0.0) * D(int(uint(_2349 > 0.0) - uint(_2349 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2638) + spvNClamp((((_2402 + _2361.z) + (spvNMin(abs(_2357), 0.0) * D(int(uint(_2357 > 0.0) - uint(_2357 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2402 + _2435.w) + (spvNMin(abs(_2426), 0.0) * D(int(uint(_2426 > 0.0) - uint(_2426 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2402 + _2435.z) + (spvNMin(abs(_2431), 0.0) * D(int(uint(_2431 > 0.0) - uint(_2431 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2341), (((spvNClamp((((_2402 + _2361.x) + (spvNMin(abs(_2352), 0.0) * D(int(uint(_2352 > 0.0) - uint(_2352 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2638) + spvNClamp((((_2402 + _2361.y) + (spvNMin(abs(_2356), 0.0) * D(int(uint(_2356 > 0.0) - uint(_2356 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2402 + _2435.x) + (spvNMin(abs(_2429), 0.0) * D(int(uint(_2429 > 0.0) - uint(_2429 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2402 + _2435.y) + (spvNMin(abs(_2430), 0.0) * D(int(uint(_2430 > 0.0) - uint(_2430 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2341), (((spvNClamp((((_2402 + _2507.w) + (spvNMin(abs(_2500), 0.0) * D(int(uint(_2500 > 0.0) - uint(_2500 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2638) + spvNClamp((((_2402 + _2507.z) + (spvNMin(abs(_2505), 0.0) * D(int(uint(_2505 > 0.0) - uint(_2505 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2402 + _2576.w) + (spvNMin(abs(_2569), 0.0) * D(int(uint(_2569 > 0.0) - uint(_2569 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2402 + _2576.z) + (spvNMin(abs(_2574), 0.0) * D(int(uint(_2574 > 0.0) - uint(_2574 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2341), (((spvNClamp((((_2402 + _2507.x) + (spvNMin(abs(_2503), 0.0) * D(int(uint(_2503 > 0.0) - uint(_2503 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2638) + spvNClamp((((_2402 + _2507.y) + (spvNMin(abs(_2504), 0.0) * D(int(uint(_2504 > 0.0) - uint(_2504 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_2402 + _2576.x) + (spvNMin(abs(_2572), 0.0) * D(int(uint(_2572 > 0.0) - uint(_2572 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_2402 + _2576.y) + (spvNMin(abs(_2573), 0.0) * D(int(uint(_2573 > 0.0) - uint(_2573 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _2341));
                        frontier_phi_28_27_ladder = dot(_2661, vec4(1.0 - _2342, 1.0, 1.0, _2342)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        frontier_phi_28_27_ladder = 1.0;
                    }
                    _1614 = frontier_phi_28_27_ladder;
                }
                else
                {
                    _1614 = 1.0;
                }
                D _1620 = _1155 - _229;
                D _1621 = _1156 - _230;
                D _1622 = _1157 - _231;
                D _1623 = dot(vec3(_1620, _1621, _1622), vec3(_1620, _1621, _1622));
                D _2047;
                D _2048;
                D _2049;
                if (_1623 > 9.9999997473787516355514526367188e-05)
                {
                    D _2043 = inversesqrt(_1623);
                    _2047 = _2043 * _1620;
                    _2048 = _2043 * _1621;
                    _2049 = _2043 * _1622;
                }
                else
                {
                    _2047 = 0.0;
                    _2048 = 0.0;
                    _2049 = 0.0;
                }
                D _2050 = _1177 * _1177;
                D _2054 = (_1158 * _1158) * _1623;
                D _2057 = spvNClamp(1.0 - (_2054 * _2054), 0.0, 1.0);
                D _2677;
                if (_1216)
                {
                    D _2675 = spvNClamp((dot(vec3(_2047, _2048, _2049), vec3(_1164, _1165, _1166)) - _1170) * _1171, 0.0, 1.0);
                    _2677 = _2675 * _2675;
                }
                else
                {
                    _2677 = 1.0;
                }
                D _2678 = ((_2057 * _2057) * D(_1623 >= _2050)) * _2677;
                D _3221;
                D _3223;
                D _3225;
                if ((_1168 & 262144u) == 0u)
                {
                    _3221 = 1.0;
                    _3223 = 1.0;
                    _3225 = 1.0;
                }
                else
                {
                    D _3228 = (-0.0) - _1165;
                    D _3229 = (-0.0) - _1166;
                    D _3230 = (-0.0) - _1164;
                    D _3240 = (-0.0) - _2047;
                    D _3241 = (-0.0) - _2048;
                    D _3242 = (-0.0) - _2049;
                    D _3245 = fma(_3229, _3242, fma(_3228, _3241, _2047 * _1164));
                    D _3248 = fma(_1175, _3242, fma(_1174, _3241, _1173 * _3240));
                    D _3256 = atan(((-0.0) - _3248) / ((-0.0) - _3245));
                    bool _3261 = _3245 > (-0.0);
                    bool _3262 = _3245 == (-0.0);
                    bool _3263 = _3248 <= (-0.0);
                    bool _3264 = _3248 > (-0.0);
                    vec4 _3286 = texture((sampler2D(ForwardLightProfileTextures[_1180 + 0u], View_SharedBilinearWrappedSampler)), vec2(fract((_3262 && _3263) ? 1.25 : ((_3262 && _3264) ? 0.75 : ((((_3261 && _3264) ? (_3256 + (-3.1415927410125732421875)) : ((_3261 && _3263) ? (_3256 + 3.1415927410125732421875) : _3256)) * 0.15915493667125701904296875) + 1.0))), (asin((-0.0) - fma((_1174 * _3230) - (_1173 * _3228), _3242, fma((_1173 * _3229) - (_1175 * _3230), _3241, ((_1175 * _3228) - (_1174 * _3229)) * _3240))) * 0.3183098733425140380859375) + 0.5));
                    _3221 = _3286.x;
                    _3223 = _3286.y;
                    _3225 = _3286.z;
                }
                D _3677;
                D _3679;
                D _3681;
                D _3683;
                D _3685;
                D _3687;
                D _3689;
                D _3691;
                D _3693;
                for (;;)
                {
                    if (_2678 > 0.0)
                    {
                        D _3802;
                        if (_1215)
                        {
                            if (!(_1614 > 0.0))
                            {
                                _3677 = 0.0;
                                _3679 = 0.0;
                                _3681 = 0.0;
                                _3683 = 0.0;
                                _3685 = 0.0;
                                _3687 = 0.0;
                                _3689 = 0.0;
                                _3691 = 0.0;
                                _3693 = 0.0;
                                break;
                            }
                            _3802 = _1614;
                        }
                        else
                        {
                            _3802 = 1.0;
                        }
                        D _3804 = spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1623));
                        D _3805 = 1.0 / _3804;
                        D _3806 = dot(vec3(_416, _417, _418), vec3(_2047, _2048, _2049));
                        D _3827;
                        if (_1177 > 0.0)
                        {
                            D _3824 = sqrt(spvNClamp(_2050 * _3805, 0.0, 1.0));
                            D frontier_phi_107_106_ladder;
                            if (_3824 > spvNMax(9.9999997473787516355514526367188e-06, _3806))
                            {
                                D _3846 = spvNMax((-0.0) - _3824, _3806) + _3824;
                                frontier_phi_107_106_ladder = (_3846 * _3846) * (0.25 / _3824);
                            }
                            else
                            {
                                frontier_phi_107_106_ladder = _3806;
                            }
                            _3827 = frontier_phi_107_106_ladder;
                        }
                        else
                        {
                            _3827 = _3806;
                        }
                        D _3889;
                        D _3890;
                        D _3829;
                        D _3831;
                        D _3835;
                        D _3836;
                        bool _3839;
                        for (;;)
                        {
                            _3829 = spvNMax(0.0, _3827);
                            _3831 = _639 * _639;
                            _3835 = spvNClamp(((1.0 - _3831) * _1177) * inversesqrt(_3804), 0.0, 1.0);
                            _3836 = dot(vec3(_240, _242, _243), vec3(_2047, _2048, _2049));
                            _3839 = _3835 > 0.0;
                            D _3857;
                            D _3859;
                            if (_3839)
                            {
                                D _3852 = sqrt(spvNMax(0.0, 1.0 - (_3835 * _3835)));
                                D _3855 = ((_3806 * 2.0) * _530) - _3836;
                                if (!(!(_3855 >= _3852)))
                                {
                                    _3889 = _542;
                                    _3890 = 1.0;
                                    break;
                                }
                                D _3877 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, 1.0 - (_3855 * _3855))) * _3835;
                                _3857 = (_3877 * ((((_530 * _530) * 2.0) + (-1.0)) - (_3855 * _3836))) + (_3852 * _3836);
                                _3859 = (_3877 * (_530 - (_3855 * _3806))) + (_3852 * _3806);
                            }
                            else
                            {
                                _3857 = _3836;
                                _3859 = _3806;
                            }
                            D _3864 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3857 * 2.0) + 2.0));
                            _3889 = spvNMin(_3864 * (_3857 + 1.0), 1.0);
                            _3890 = spvNClamp(_3864 * (_3859 + _530), 0.0, 1.0);
                            break;
                        }
                        D _3891 = spvNMax(9.9999997473787516355514526367188e-06, _3889);
                        D _3900 = sqrt(spvNMax(0.0, 1.0 - ((1.0 - (_530 * _530)) * 0.444444477558135986328125)));
                        D _3904 = (_536 * 0.666666686534881591796875) - (_3900 * _416);
                        D _3905 = (_537 * 0.666666686534881591796875) - (_3900 * _417);
                        D _3906 = (_538 * 0.666666686534881591796875) - (_3900 * _418);
                        D _3910 = inversesqrt(dot(vec3(_3904, _3905, _3906), vec3(_3904, _3905, _3906)));
                        D _3917 = dot(vec3((-0.0) - (_3910 * _3904), (-0.0) - (_3910 * _3905), (-0.0) - (_3910 * _3906)), vec3(_2047, _2048, _2049));
                        D _3920 = _3831 * _3831;
                        D _3934 = ((_3890 * _3890) * (_3920 + (-1.0))) + 1.0;
                        D _3940 = (_3829 * 2.0) * _556;
                        D _3945 = 1.0 - _3891;
                        D _3946 = _3945 * _3945;
                        D _3948 = (_3946 * _3946) * _3945;
                        D _3952 = spvNMin(dot(vec3(_514, _515, _516), vec3(16.666667938232421875)), 1.0);
                        D _3965 = spvNMax(0.039999999105930328369140625, _639);
                        D _3978 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_3965 * _3829) + 0.02669160068035125732421875) / (_3829 + 0.4664950072765350341796875)) * exp2(((1.0 / _3965) * _3829) * log2(_3965)), 0.0, 1.0));
                        D _3979 = 1.0 - _3829;
                        D _3980 = _3979 * _3979;
                        D _3992 = ((_3980 * _3980) * _3979) * exp2(log2((exp2((_3965 * 4.7702999114990234375) * log2(_3829)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _3965);
                        D _3995 = (1.0 / _3978) * (1.0 - _3978);
                        D _3999 = (_3995 * _514) + 1.0;
                        D _4000 = (_3995 * _515) + 1.0;
                        D _4001 = (_3995 * _516) + 1.0;
                        D _4002 = _3978 - _3992;
                        D _4016 = spvNClamp(1.0 - dot(vec3(_3999 * ((_4002 * _514) + _3992), _4000 * ((_4002 * _515) + _3992), _4001 * ((_4002 * _516) + _3992)), vec3(0.3333333432674407958984375)), 0.0, 1.0);
                        D _4020 = ((((_3920 * 0.3183098733425140380859375) * _3829) * (1.0 / (_3934 * _3934))) * (_3839 ? ((1.0 / ((((_3835 * 0.25) * (_3835 + (_3831 * 3.0))) * (1.0 / _3891)) + _3920)) * _3920) : 1.0)) * (0.5 / ((_3831 * ((_556 + _3829) - _3940)) + _3940));
                        D _4021 = _3829 * 0.3183098733425140380859375;
                        D _4024 = ((_3917 * _3917) + 1.0) * 0.05968309938907623291015625;
                        D _4025 = spvNMin(1.0, _442);
                        D _4027 = (_442 + 1.0) - _4025;
                        D _4028 = _4027 * _4027;
                        D _4031 = 1.0 - ((_4028 * _4028) * _4027);
                        D _4032 = _4031 * _4031;
                        D _4037 = ((_4032 * _4032) * (_4031 * (_442 - _4025))) + _4025;
                        D _4040 = sqrt(spvNMax(0.0, 1.0 - _4037));
                        D _4044 = 1.0 - spvNClamp((_639 * 3.5) + (-0.5), 0.0, 1.0);
                        D _4045 = _4044 * _4044;
                        D _4055 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, (_670 * _4040) * spvNClamp(1.0 - ((_4045 * _4045) * _4044), 0.0, 1.0))) * _3829, 0.0, 1.0);
                        D _4060 = spvNClamp((1.0 / spvNMax(0.001000000047497451305389404296875, _4040)) * _3829, 0.0, 1.0);
                        D _4062 = spvNMin(_3802, _4055 * _4055);
                        D _4063 = spvNMin(_3802, _4060 * _4060);
                        D _4064 = spvNMin(_3802, _4037);
                        D _4068 = (_2678 * _1160) * _3221;
                        D _4069 = (_2678 * _1161) * _3223;
                        D _4070 = (_2678 * _1162) * _3225;
                        D _4071 = _3805 * _4068;
                        D _4075 = _3805 * _4069;
                        D _4079 = _3805 * _4070;
                        _3677 = ((((_4068 * _466) * _3805) * _4021) * _4016) * _4063;
                        _3679 = ((((_4069 * _467) * _3805) * _4021) * _4016) * _4063;
                        _3681 = ((((_4070 * _468) * _3805) * _4021) * _4016) * _4063;
                        _3683 = (((_4071 * spvNClamp(((_3952 - _514) * _3948) + _514, 0.0, 1.0)) * _4020) * _3999) * _4062;
                        _3685 = (((_4075 * _4020) * spvNClamp(((_3952 - _515) * _3948) + _515, 0.0, 1.0)) * _4000) * _4062;
                        _3687 = (((_4079 * _4020) * spvNClamp(((_3952 - _516) * _3948) + _516, 0.0, 1.0)) * _4001) * _4062;
                        _3689 = (_4071 * _4024) * _4064;
                        _3691 = (_4075 * _4024) * _4064;
                        _3693 = (_4079 * _4024) * _4064;
                        break;
                    }
                    else
                    {
                        _3677 = 0.0;
                        _3679 = 0.0;
                        _3681 = 0.0;
                        _3683 = 0.0;
                        _3685 = 0.0;
                        _3687 = 0.0;
                        _3689 = 0.0;
                        _3691 = 0.0;
                        _3693 = 0.0;
                        break;
                    }
                }
                frontier_phi_47_pred = _1146;
                frontier_phi_47_pred_1 = _3677 + _1136;
                frontier_phi_47_pred_2 = _3679 + _1137;
                frontier_phi_47_pred_3 = _3681 + _1138;
                frontier_phi_47_pred_4 = _3683 + _1139;
                frontier_phi_47_pred_5 = _3685 + _1140;
                frontier_phi_47_pred_6 = _3687 + _1141;
                frontier_phi_47_pred_7 = _3689 + _1142;
                frontier_phi_47_pred_8 = _3691 + _1143;
                frontier_phi_47_pred_9 = _3693 + _1144;
                frontier_phi_47_pred_10 = _1145;
                frontier_phi_47_pred_11 = _1147;
                frontier_phi_47_pred_12 = _1148;
                frontier_phi_47_pred_13 = _1149;
                frontier_phi_47_pred_14 = _1150;
            }
            else
            {
                D _1319 = _1155 - _229;
                D _1320 = _1156 - _230;
                D _1321 = _1157 - _231;
                D _1322 = dot(vec3(_1319, _1320, _1321), vec3(_1319, _1320, _1321));
                D _1326 = (_1158 * _1158) * _1322;
                D _1327 = _1326 * _1326;
                D _1328 = _1327 * _1327;
                D _1331 = spvNClamp(1.0 - (_1328 * _1328), 0.0, 1.0);
                D _1332 = _1331 * _1331;
                D _1333 = _1332 * _1332;
                D _1334 = _1333 * _1333;
                D _1638;
                D _1640;
                D _1642;
                D _1644;
                D _1646;
                D _1648;
                if (_1334 > 0.0)
                {
                    D _1630 = dot(vec3(_237, _238, _239), vec3(_416, _417, _418)) * 2.0;
                    D _1634 = _237 - (_1630 * _416);
                    D _1635 = _238 - (_1630 * _417);
                    D _1636 = _239 - (_1630 * _418);
                    D _3288;
                    D _3289;
                    D _3290;
                    D _3291;
                    D _3292;
                    D _3293;
                    D _3294;
                    D _3295;
                    D _3296;
                    D _3297;
                    D _3298;
                    if (_1178 == 0.0)
                    {
                        D _2683;
                        D _2684;
                        D _2685;
                        if (_1322 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2679 = inversesqrt(_1322);
                            _2683 = _2679 * _1319;
                            _2684 = _2679 * _1320;
                            _2685 = _2679 * _1321;
                        }
                        else
                        {
                            _2683 = 0.0;
                            _2684 = 0.0;
                            _2685 = 0.0;
                        }
                        D _2688 = 1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1322));
                        _3288 = _2688;
                        _3289 = (_1177 * _1177) * _2688;
                        _3290 = _2683;
                        _3291 = _2684;
                        _3292 = _2685;
                        _3293 = _2683;
                        _3294 = _2684;
                        _3295 = _2685;
                        _3296 = _2683;
                        _3297 = _2684;
                        _3298 = _2685;
                    }
                    else
                    {
                        D _2061 = _1178 * 0.5;
                        D _2062 = _2061 * _1164;
                        D _2063 = _2061 * _1165;
                        D _2064 = _2061 * _1166;
                        D _2065 = _1319 - _2062;
                        D _2066 = _1320 - _2063;
                        D _2067 = _1321 - _2064;
                        D _2068 = _2062 + _1319;
                        D _2069 = _2063 + _1320;
                        D _2070 = _2064 + _1321;
                        D _2078 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2065, _2066, _2067), vec3(_2065, _2066, _2067))));
                        D _2080 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_2068, _2069, _2070), vec3(_2068, _2069, _2070))));
                        D _2081 = _2080 * _2078;
                        D _2097 = (1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(_2081, ((dot(vec3(_2065, _2066, _2067), vec3(_2068, _2069, _2070)) * 0.5) * _2081) + 0.5))) * _2081;
                        D _2099 = (_1164 * 2.0) * _2061;
                        D _2101 = (_1165 * 2.0) * _2061;
                        D _2103 = (_1166 * 2.0) * _2061;
                        D _2104 = dot(vec3(_2099, _2101, _2103), vec3(_2099, _2101, _2103));
                        D _2721;
                        D _2722;
                        D _2723;
                        if (_2104 > 9.9999997473787516355514526367188e-05)
                        {
                            D _2691 = dot(vec3(_1634, _1635, _1636), vec3(_2099, _2101, _2103));
                            D _2707 = spvNClamp((1.0 / (_2104 - (_2691 * _2691))) * dot(vec3(_2065, _2066, _2067), vec3((_2691 * _1634) - _2099, (_2691 * _1635) - _2101, (_2691 * _1636) - _2103)), 0.0, 1.0);
                            D _2711 = (_2707 * _2099) + _2065;
                            D _2712 = (_2707 * _2101) + _2066;
                            D _2713 = (_2707 * _2103) + _2067;
                            D _2717 = inversesqrt(dot(vec3(_2711, _2712, _2713), vec3(_2711, _2712, _2713)));
                            _2721 = _2711 * _2717;
                            _2722 = _2712 * _2717;
                            _2723 = _2713 * _2717;
                        }
                        else
                        {
                            _2721 = _2065;
                            _2722 = _2066;
                            _2723 = _2067;
                        }
                        _3288 = _2097;
                        _3289 = (_1177 * _1177) * _2097;
                        _3290 = _2078 * _2065;
                        _3291 = _2078 * _2066;
                        _3292 = _2078 * _2067;
                        _3293 = _2080 * _2068;
                        _3294 = _2080 * _2069;
                        _3295 = _2080 * _2070;
                        _3296 = _2721;
                        _3297 = _2722;
                        _3298 = _2723;
                    }
                    D _3308 = _3289 + 1.0;
                    D _3313 = _3296 - _237;
                    D _3314 = _3297 - _238;
                    D _3315 = _3298 - _239;
                    D _3319 = inversesqrt(dot(vec3(_3313, _3314, _3315), vec3(_3313, _3314, _3315)));
                    D _3320 = _3319 * _3313;
                    D _3321 = _3319 * _3314;
                    D _3322 = _3319 * _3315;
                    D _3329 = spvNClamp(dot(vec3(_416, _417, _418), vec3(_3320, _3321, _3322)), 0.0, 1.0);
                    D _3330 = _639 * _639;
                    D _3336 = spvNClamp(((1.0 - _3330) * _1177) * sqrt(_3288), 0.0, 1.0);
                    D _3350 = exp2(log2(spvNClamp((((_3336 * 0.25) * (_3336 + (_3330 * 3.0))) * (1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_240, _242, _243), vec3(_3320, _3321, _3322))))) + (_3330 * _3330), 0.0, 1.0)) * 0.25);
                    D _3354 = spvNClamp(dot(vec3(_3290, _3291, _3292), vec3(_3293, _3294, _3295)), 0.0, 1.0);
                    D _3356 = _3350 * _3350;
                    D _3357 = _3356 * _3356;
                    D _3709;
                    if (_3354 < 1.0)
                    {
                        D _3700 = sqrt(spvNClamp((1.0 / (_3354 + 1.0)) * (1.0 - _3354), 0.0, 1.0));
                        _3709 = (1.0 / spvNClamp(((_3700 * 0.25) * (_3700 + (_3356 * 3.0))) + _3357, 0.0, 1.0)) * _3357;
                    }
                    else
                    {
                        _3709 = 1.0;
                    }
                    D _3713 = ((_3329 * _3329) * (_3357 + (-1.0))) + 1.0;
                    D _3716 = spvNMax(0.0, (((dot(vec3(_416, _417, _418), vec3(_3293, _3294, _3295)) + dot(vec3(_416, _417, _418), vec3(_3290, _3291, _3292))) * 0.5) + _3289) * (1.0 / (_3308 * _3308))) * 0.3183098733425140380859375;
                    D _3719 = ((_3716 * _3357) * _3709) * (1.0 / (_3713 * _3713));
                    D _3721 = (_1334 * _1160) * _3288;
                    D _3723 = (_1334 * _1161) * _3288;
                    D _3725 = (_1334 * _1162) * _3288;
                    _1638 = _3719 * _3721;
                    _1640 = _3719 * _3723;
                    _1642 = _3719 * _3725;
                    _1644 = _3716 * _3721;
                    _1646 = _3716 * _3723;
                    _1648 = _3716 * _3725;
                }
                else
                {
                    _1638 = 0.0;
                    _1640 = 0.0;
                    _1642 = 0.0;
                    _1644 = 0.0;
                    _1646 = 0.0;
                    _1648 = 0.0;
                }
                frontier_phi_47_pred = _1640 + _1146;
                frontier_phi_47_pred_1 = _1136;
                frontier_phi_47_pred_2 = _1137;
                frontier_phi_47_pred_3 = _1138;
                frontier_phi_47_pred_4 = _1139;
                frontier_phi_47_pred_5 = _1140;
                frontier_phi_47_pred_6 = _1141;
                frontier_phi_47_pred_7 = _1142;
                frontier_phi_47_pred_8 = _1143;
                frontier_phi_47_pred_9 = _1144;
                frontier_phi_47_pred_10 = _1638 + _1145;
                frontier_phi_47_pred_11 = _1642 + _1147;
                frontier_phi_47_pred_12 = _1644 + _1148;
                frontier_phi_47_pred_13 = _1646 + _1149;
                frontier_phi_47_pred_14 = _1648 + _1150;
            }
            _825 = frontier_phi_47_pred;
            _805 = frontier_phi_47_pred_1;
            _807 = frontier_phi_47_pred_2;
            _809 = frontier_phi_47_pred_3;
            _811 = frontier_phi_47_pred_4;
            _813 = frontier_phi_47_pred_5;
            _815 = frontier_phi_47_pred_6;
            _817 = frontier_phi_47_pred_7;
            _819 = frontier_phi_47_pred_8;
            _821 = frontier_phi_47_pred_9;
            _823 = frontier_phi_47_pred_10;
            _827 = frontier_phi_47_pred_11;
            _829 = frontier_phi_47_pred_12;
            _831 = frontier_phi_47_pred_13;
            _833 = frontier_phi_47_pred_14;
            uint _1152 = _1151 + 1u;
            if (_1152 == _797)
            {
                break;
            }
            else
            {
                _1136 = _805;
                _1137 = _807;
                _1138 = _809;
                _1139 = _811;
                _1140 = _813;
                _1141 = _815;
                _1142 = _817;
                _1143 = _819;
                _1144 = _821;
                _1145 = _823;
                _1146 = _825;
                _1147 = _827;
                _1148 = _829;
                _1149 = _831;
                _1150 = _833;
                _1151 = _1152;
                continue;
            }
        }
        _804 = _805;
        _806 = _807;
        _808 = _809;
        _810 = _811;
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
    }
    vec4 _874 = textureLod(sampler3D(TranslucentBasePass_TranslucencyLightingVolumeEnvironmentA, View_SharedBilinearClampedSampler), vec3((_229 - View._m0[180u].x) * View._m0[182u].x, (_230 - View._m0[180u].y) * View._m0[182u].y, (_231 - View._m0[180u].z) * View._m0[182u].z), 0.0);
    D _898;
    D _899;
    D _900;
    if (_368 < 1.0)
    {
        _898 = _345.x / ((_390 / _367) + 1.0);
        _899 = _345.y / ((_391 / _367) + 1.0);
        _900 = _345.z / ((_392 / _367) + 1.0);
    }
    else
    {
        _898 = 0.0;
        _899 = 0.0;
        _900 = 0.0;
    }
    D _917 = spvNClamp(_621, 0.0, 1.0);
    D _930 = _464 * _464;
    D _931 = _930 * _464;
    D _938 = ((_416 - _553) * _931) + _553;
    D _939 = ((_417 - _554) * _931) + _554;
    D _940 = ((_418 - _555) * _931) + _555;
    D _944 = inversesqrt(dot(vec3(_938, _939, _940), vec3(_938, _939, _940)));
    D _953 = 10.0 / spvNMax(9.9999997473787516355514526367188e-06, _930);
    D _982 = fma(_228, View._m0[2u].x, fma(_227, View._m0[1u].x, View._m0[0u].x * _226)) + View._m0[3u].x;
    D _986 = fma(_228, View._m0[2u].y, fma(_227, View._m0[1u].y, View._m0[0u].y * _226)) + View._m0[3u].y;
    D _990 = fma(_228, View._m0[2u].z, fma(_227, View._m0[1u].z, View._m0[0u].z * _226)) + View._m0[3u].z;
    D _994 = fma(_228, View._m0[2u].w, fma(_227, View._m0[1u].w, View._m0[0u].w * _226)) + View._m0[3u].w;
    D _1001 = ((_938 * _102) * _944) + _226;
    D _1002 = ((_939 * _102) * _944) + _227;
    D _1003 = ((_940 * _102) * _944) + _228;
    D _1036 = 1.0 / _994;
    D _1037 = _1036 * _982;
    D _1038 = _1036 * _986;
    D _1042 = (_1036 * _990) + (0.0500000007450580596923828125 / _994);
    D _1043 = 1.0 / (fma(_1003, View._m0[2u].w, fma(_1002, View._m0[1u].w, View._m0[0u].w * _1001)) + View._m0[3u].w);
    D _1054 = 1.0 / ((View._m0[36u].w * _953) + _994);
    D _1057 = (_1043 * (fma(_1003, View._m0[2u].x, fma(_1002, View._m0[1u].x, View._m0[0u].x * _1001)) + View._m0[3u].x)) - _1037;
    D _1058 = (_1043 * (fma(_1003, View._m0[2u].y, fma(_1002, View._m0[1u].y, View._m0[0u].y * _1001)) + View._m0[3u].y)) - _1038;
    D _1060 = (_1054 * ((View._m0[36u].x * _953) + _982)) - _1037;
    D _1061 = (_1054 * ((View._m0[36u].y * _953) + _986)) - _1038;
    D _1066 = sqrt((_1057 * _1057) + (_1058 * _1058)) * 0.5;
    D _1085 = spvNMin(1.0 - (spvNMax(0.0, abs((_1066 * _1037) + _1057) - _1066) / abs(_1057)), 1.0 - (spvNMax(0.0, abs((_1066 * _1038) + _1058) - _1066) / abs(_1058))) / _1066;
    D _1086 = _1085 * _1057;
    D _1087 = _1085 * _1058;
    D _1088 = _1085 * ((_1043 * (fma(_1003, View._m0[2u].z, fma(_1002, View._m0[1u].z, View._m0[0u].z * _1001)) + View._m0[3u].z)) - _1042);
    uvec2 _1094 = uvec2(textureSize(TranslucentBasePass_HZBTexture, int(0u)));
    D _1096 = D(int(_1094.x));
    D _1098 = D(int(_1094.y));
    uint _1119 = max(1u, min(uint(ceil((spvNClamp((1.0 / spvNMax(9.9999997473787516355514526367188e-05, sqrt((_1086 * _1086) + (_1087 * _1087)))) * sqrt((_1060 * _1060) + (_1061 * _1061)), 0.0, 1.0) * 8.0) + _264)), 8u));
    D _1124 = ((_1037 * 0.5) + 0.5) * TranslucentBasePass_2._m0[198u].x;
    D _1125 = (0.5 - (_1038 * 0.5)) * TranslucentBasePass_2._m0[198u].y;
    D _1128 = (TranslucentBasePass_2._m0[198u].x * 0.0625) * _1086;
    D _1131 = (TranslucentBasePass_2._m0[198u].y * (-0.0625)) * _1087;
    D _1132 = _1088 * 0.125;
    D _1134 = spvNMax(abs(_1088), _1042 - ((1.0 / (fma(_102, View._m0[38u].w, 0.0) + _994)) * (fma(_102, View._m0[38u].z, 0.0) + _990))) * 0.125;
    D _1302;
    D _1304;
    D _1306;
    D _1308;
    if (_1119 == 0u)
    {
        _1302 = 0.0;
        _1304 = 0.0;
        _1306 = 0.0;
        _1308 = 0.0;
    }
    else
    {
        D frontier_phi_60;
        D frontier_phi_60_1;
        D frontier_phi_60_2;
        D frontier_phi_60_3;
        D _1551 = 0.0;
        uint _1553 = 0u;
        D _1552;
        D _1555;
        bool _1578;
        for (;;)
        {
            _1555 = D(_1553);
            D _1556 = _1555 + _264;
            vec4 _1570 = texelFetch(TranslucentBasePass_HZBTexture, ivec2_(uvec2(uint(int(floor(((_1556 * _1128) + _1124) * _1096))), uint(int(floor(((_1556 * _1131) + _1125) * _1098))))), int(0u));
            D _1572 = _1570.x;
            _1552 = ((_1556 * _1132) + _1042) - _1572;
            _1578 = (abs(((-0.0) - _1134) - _1552) < _1134) && (_1572 != 0.0);
            if (_1578)
            {
                D _1987 = (_1553 == 0u) ? (_1552 - _1132) : _1551;
                D _1994 = abs(((_264 + (-1.0)) + _1555) + spvNClamp(_1987 / (_1987 - _1552), 0.0, 1.0));
                D _1999 = spvNMin(_1994 * 0.125, 1.0);
                frontier_phi_60 = 1.0 - (_1999 * _1999);
                frontier_phi_60_1 = (_1994 * _1132) + _1042;
                frontier_phi_60_2 = (_1994 * _1131) + _1125;
                frontier_phi_60_3 = (_1994 * _1128) + _1124;
                break;
            }
            else
            {
                uint _1554 = _1553 + 1u;
                if (_1554 < _1119)
                {
                    _1551 = _1552;
                    _1553 = _1554;
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
        _1302 = frontier_phi_60_3;
        _1304 = frontier_phi_60_2;
        _1306 = frontier_phi_60_1;
        _1308 = frontier_phi_60;
    }
    D _1316 = (spvNClamp(_1302 * TranslucentBasePass_2._m0[198u].z, 0.0, 1.0) * 2.0) + (-1.0);
    D _1317 = 1.0 - (spvNClamp(_1304 * TranslucentBasePass_2._m0[198u].w, 0.0, 1.0) * 2.0);
    D _1456;
    D _1458;
    D _1460;
    D _1462;
    if (_1308 > 0.0)
    {
        D _1457;
        D _1459;
        D _1461;
        D _2203;
        D _1449;
        bool _1455;
        for (;;)
        {
            D _1408 = ((View._m0[73u].x * _1306) + View._m0[73u].y) + (1.0 / ((View._m0[73u].z * _1306) - View._m0[73u].w));
            D _1432 = _1408 * _1316;
            D _1433 = _1408 * _1317;
            D _1444 = (_226 - View._m0[63u].x) - fma(_1408, View._m0[62u].x, fma(_1433, View._m0[61u].x, _1432 * View._m0[60u].x));
            D _1446 = (_227 - View._m0[63u].y) - fma(_1408, View._m0[62u].y, fma(_1433, View._m0[61u].y, _1432 * View._m0[60u].y));
            D _1448 = (_228 - View._m0[63u].z) - fma(_1408, View._m0[62u].z, fma(_1433, View._m0[61u].z, _1432 * View._m0[60u].z));
            _1449 = dot(vec3(_1444, _1446, _1448), vec3(_1444, _1446, _1448));
            _1455 = View._m0[175u].w != 0.0;
            if (_1455)
            {
                if (floatBitsToUint(View._m0[175u]).y == 0u)
                {
                    _1457 = 0.0;
                    _1459 = 0.0;
                    _1461 = 0.0;
                    _2203 = 0.0;
                    break;
                }
            }
            D _1845 = fma(_1306, View._m0[140u].w, fma(_1317, View._m0[139u].w, View._m0[138u].w * _1316)) + View._m0[141u].w;
            D _1846 = (fma(_1306, View._m0[140u].x, fma(_1317, View._m0[139u].x, View._m0[138u].x * _1316)) + View._m0[141u].x) / _1845;
            D _1847 = (fma(_1306, View._m0[140u].y, fma(_1317, View._m0[139u].y, View._m0[138u].y * _1316)) + View._m0[141u].y) / _1845;
            D _1864 = spvNClamp((abs((spvNMin(spvNMax(_1846, -1.0), 1.0) - _1316) * 0.5) * 5.0) + (-4.0), 0.0, 1.0);
            D _1865 = spvNClamp((abs((spvNMin(spvNMax(_1847, -1.0), 1.0) - _1317) * 0.5) * 5.0) + (-4.0), 0.0, 1.0);
            uvec2 _1918 = uvec2(textureSize(TranslucentBasePass_PrevSceneColor, int(0u)));
            vec4 _1939 = texelFetch(TranslucentBasePass_PrevSceneColor, ivec2_(uvec2(uint(min(int(uint(max(int(uint(int(D(int(_1918.x)) * ((TranslucentBasePass_2._m0[199u].x * spvNMin(spvNMax(_1846 - ((D(int(uint(_1846 > 0.0) - uint(_1846 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1846) + (-1.0))), -1.0), 1.0)) + TranslucentBasePass_2._m0[199u].z)))), int(uint(int(TranslucentBasePass_2._m0[200u].x)))))), int(uint(int(TranslucentBasePass_2._m0[200u].x + TranslucentBasePass_2._m0[200u].z)) + 4294967295u))), uint(min(int(uint(max(int(uint(int(D(int(_1918.y)) * ((TranslucentBasePass_2._m0[199u].y * spvNMin(spvNMax(_1847 - ((D(int(uint(_1847 > 0.0) - uint(_1847 < 0.0))) * 2.0) * spvNMax(0.0, abs(_1847) + (-1.0))), -1.0), 1.0)) + TranslucentBasePass_2._m0[199u].w)))), int(uint(int(TranslucentBasePass_2._m0[200u].y)))))), int(uint(int(TranslucentBasePass_2._m0[200u].y + TranslucentBasePass_2._m0[200u].w)) + 4294967295u))))), int(0u));
            _1457 = View._m0[165u].x * spvNMin(_1939.x, 65504.0);
            _1459 = View._m0[165u].x * spvNMin(_1939.y, 65504.0);
            _1461 = View._m0[165u].x * spvNMin(_1939.z, 65504.0);
            _2203 = spvNMax(0.0, 1.0 - dot(vec2(_1864, _1865), vec2(_1864, _1865)));
            break;
        }
        _1456 = _1457;
        _1458 = _1459;
        _1460 = _1461;
        _1462 = (_2203 * _1308) * spvNClamp(1.0 / spvNMax(9.9999997473787516355514526367188e-06, (_930 * _930) * _1449), 0.0, 1.0);
    }
    else
    {
        _1456 = 0.0;
        _1458 = 0.0;
        _1460 = 0.0;
        _1462 = 0.0;
    }
    D _1496 = fma(_231, View._m0[14u].w, fma(_230, View._m0[13u].w, _229 * View._m0[12u].w)) + View._m0[15u].w;
    D _1501 = (((fma(_231, View._m0[14u].x, fma(_230, View._m0[13u].x, _229 * View._m0[12u].x)) + View._m0[15u].x) / _1496) * 0.5) + 0.5;
    D _1502 = 0.5 - (((fma(_231, View._m0[14u].y, fma(_230, View._m0[13u].y, _229 * View._m0[12u].y)) + View._m0[15u].y) / _1496) * 0.5);
    D _1531 = sqrt(((_227 * _227) + (_226 * _226)) + (_228 * _228));
    D _1549 = spvNMax(0.0, ((1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_226, _227, _228), vec3(View._m0[68u].xyz())))) * _1531) * View._m0[280u].w);
    D _1955;
    D _1957;
    D _1959;
    D _1961;
    D _1963;
    D _1965;
    if (_1531 < _1549)
    {
        _1955 = 0.0;
        _1957 = 0.0;
        _1959 = 0.0;
        _1961 = 1.0;
        _1963 = 1.0;
        _1965 = 1.0;
    }
    else
    {
        D _1973 = (1.0 / _1531) * _1549;
        uvec4 _1980 = floatBitsToUint(View._m0[220u]);
        uint _1981 = _1980.y;
        uint _1983 = (_1981 != 1u) ? 4294967295u : 0u;
        uint _2319;
        if (_1981 > 1u)
        {
            D _131[4];
            _131[0u] = 0.0;
            _131[1u] = 0.0;
            _131[2u] = 0.0;
            _131[3u] = 0.0;
            uint _3165 = 0u;
            bool _3171;
            for (;;)
            {
                _3171 = _3165 < floatBitsToUint(View._m0[220u]).y;
                if (_3171)
                {
                    uint _3592 = _3165 + 237u;
                    D _3604 = View._m0[_3592].x - View._m0[75u].x;
                    D _3605 = View._m0[_3592].y - View._m0[75u].y;
                    D _3606 = View._m0[_3592].z - View._m0[75u].z;
                    D _3607 = dot(vec3(_3604, _3605, _3606), vec3(_237, _238, _239));
                    D _3614 = dot(vec3(_3604, _3605, _3606), vec3(_3604, _3605, _3606)) - (View._m0[_3592].w * View._m0[_3592].w);
                    D _3616 = (_3607 * _3607) - _3614;
                    D _3734;
                    if ((_3614 < 0.0) && (!(_3616 < 0.0)))
                    {
                        D _3728 = sqrt(_3616);
                        _3734 = spvNMin(abs(_3728 + _3607), abs(_3607 - _3728));
                    }
                    else
                    {
                        _3734 = 0.0;
                    }
                    _131[_3165] = _3734;
                }
                uint _3166 = _3165 + 1u;
                if (_3166 == 4u)
                {
                    break;
                }
                else
                {
                    _3165 = _3166;
                    continue;
                }
            }
            D _3744 = (_264 * 0.99989998340606689453125) * dot(vec4(_131[0u], _131[1u], _131[2u], _131[3u]), vec4(1.0));
            uint frontier_phi_59_97_ladder;
            if (_131[0u] > _3744)
            {
                frontier_phi_59_97_ladder = 0u;
            }
            else
            {
                D _3812 = _131[1u] + _131[0u];
                uint frontier_phi_59_97_ladder_103_ladder;
                if (_3812 > _3744)
                {
                    frontier_phi_59_97_ladder_103_ladder = 1u;
                }
                else
                {
                    D _3842 = _3812 + _131[2u];
                    uint frontier_phi_59_97_ladder_103_ladder_109_ladder;
                    if (_3842 > _3744)
                    {
                        frontier_phi_59_97_ladder_103_ladder_109_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder;
                        if ((_3842 + _131[3u]) > _3744)
                        {
                            frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder = _1983;
                        }
                        frontier_phi_59_97_ladder_103_ladder_109_ladder = frontier_phi_59_97_ladder_103_ladder_109_ladder_114_ladder;
                    }
                    frontier_phi_59_97_ladder_103_ladder = frontier_phi_59_97_ladder_103_ladder_109_ladder;
                }
                frontier_phi_59_97_ladder = frontier_phi_59_97_ladder_103_ladder;
            }
            _2319 = frontier_phi_59_97_ladder;
        }
        else
        {
            _2319 = _1983;
        }
        D frontier_phi_38_59_ladder;
        D frontier_phi_38_59_ladder_1;
        D frontier_phi_38_59_ladder_2;
        D frontier_phi_38_59_ladder_3;
        D frontier_phi_38_59_ladder_4;
        D frontier_phi_38_59_ladder_5;
        if (_2319 == 4294967295u)
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
            uint _3172 = _2319 + 221u;
            D _3180 = spvNMin(View._m0[_3172].w, 0.9900000095367431640625);
            uint _3181 = _2319 + 225u;
            uint _3188 = _2319 + 229u;
            uint _3195 = _2319 + 233u;
            uint _3200 = _2319 + 241u;
            D _3647;
            D _3648;
            D _3649;
            if (TranslucentBasePass_2._m0[146u].x > 0.0)
            {
                vec4 _3639 = textureLod(sampler2D(TranslucentBasePass_Shared_Fog_FarIntegratedScatteringTexture, View_SharedBilinearClampedSampler), vec2(spvNMin(spvNMax(View._m0[278u].x * _1501, View._m0[279u].x), View._m0[280u].x), spvNMin(spvNMax(View._m0[278u].y * _1502, View._m0[279u].y), View._m0[280u].y)), 0.0);
                _3647 = View._m0[164u].z * _3639.x;
                _3648 = View._m0[164u].z * _3639.y;
                _3649 = View._m0[164u].z * _3639.z;
            }
            else
            {
                _3647 = 0.0;
                _3648 = 0.0;
                _3649 = 0.0;
            }
            D _3653 = dot(vec3((-0.0) - View._m0[218u].x, (-0.0) - View._m0[218u].y, (-0.0) - View._m0[218u].z), vec3(_240, _242, _243));
            D _3666 = (((_3653 * _3653) + 1.0) * 0.0397887341678142547607421875) * exp2(log2(spvNMax(0.0, _3653 + 1.25)) * (-1.5));
            D _3746;
            if (View._m0[_3181].x == 0.0)
            {
                _3746 = 0.0;
            }
            else
            {
                D _3794 = (((_1973 * _228) - View._m0[_3181].z) + View._m0[75u].z) * View._m0[_3181].y;
                D _3795 = ((1.0 - _1973) * _228) * View._m0[_3181].y;
                D _3800 = exp2((-0.0) - _3794);
                D frontier_phi_98_99_ladder;
                if (abs(_3795) > 0.00999999977648258209228515625)
                {
                    frontier_phi_98_99_ladder = ((_3800 - exp2(((-0.0) - _3795) - _3794)) * View._m0[_3181].x) * (1.0 / _3795);
                }
                else
                {
                    frontier_phi_98_99_ladder = (View._m0[_3181].x * 0.693147182464599609375) * _3800;
                }
                _3746 = frontier_phi_98_99_ladder;
            }
            D _3750 = _3746 * (1.0 - _3180);
            D _3754 = (1.0 - View._m0[_3188].x) * View._m0[_3195].x;
            D _3755 = (1.0 - View._m0[_3188].y) * View._m0[_3195].x;
            D _3756 = (1.0 - View._m0[_3188].z) * View._m0[_3195].x;
            D _3757 = (-0.0) - (_1531 - _1549);
            D _3785 = 1.0 - spvNClamp(exp2(_3750 * _3757), 0.0, 1.0);
            frontier_phi_38_59_ladder = spvNClamp(exp2((_3750 + _3756) * _3757), 0.0, 1.0);
            frontier_phi_38_59_ladder_1 = spvNClamp(exp2((_3750 + _3755) * _3757), 0.0, 1.0);
            frontier_phi_38_59_ladder_2 = spvNClamp(exp2((_3750 + _3754) * _3757), 0.0, 1.0);
            frontier_phi_38_59_ladder_3 = (((_3180 * View._m0[_3172].z) * (((View._m0[219u].z * View._m0[_3200].x) * _3666) + _3649)) * spvNClamp(exp2(_3756 * _3757), 0.0, 1.0)) * _3785;
            frontier_phi_38_59_ladder_4 = (((_3180 * View._m0[_3172].y) * (((View._m0[219u].y * View._m0[_3200].x) * _3666) + _3648)) * spvNClamp(exp2(_3755 * _3757), 0.0, 1.0)) * _3785;
            frontier_phi_38_59_ladder_5 = (((_3180 * View._m0[_3172].x) * (((View._m0[219u].x * View._m0[_3200].x) * _3666) + _3647)) * spvNClamp(exp2(_3754 * _3757), 0.0, 1.0)) * _3785;
        }
        _1955 = frontier_phi_38_59_ladder_5;
        _1957 = frontier_phi_38_59_ladder_4;
        _1959 = frontier_phi_38_59_ladder_3;
        _1961 = frontier_phi_38_59_ladder_2;
        _1963 = frontier_phi_38_59_ladder_1;
        _1965 = frontier_phi_38_59_ladder;
    }
    D _2251;
    D _2252;
    D _2253;
    D _2254;
    D _2255;
    D _2256;
    if (TranslucentBasePass_2._m0[148u].x > 0.0)
    {
        D _2231 = spvNMin(spvNMax(View._m0[278u].x * _1501, View._m0[279u].x), View._m0[280u].x);
        D _2232 = spvNMin(spvNMax(View._m0[278u].y * _1502, View._m0[279u].y), View._m0[280u].y);
        D _2233 = spvNMin(spvNMax((View._m0[275u].z * spvNMax(0.0, spvNMin(View._m0[276u].z * log2((View._m0[276u].x * _1496) + View._m0[276u].y), View._m0[274u].z + (-1.0)) + 0.5)) * View._m0[278u].z, View._m0[279u].z), View._m0[280u].z);
        vec4 _2236 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeATexture, View_SharedBilinearClampedSampler), vec3(_2231, _2232, _2233), 0.0);
        vec4 _2243 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeBTexture, View_SharedBilinearClampedSampler), vec3(_2231, _2232, _2233), 0.0);
        _2251 = View._m0[164u].z * _2236.x;
        _2252 = View._m0[164u].z * _2236.y;
        _2253 = View._m0[164u].z * _2236.z;
        _2254 = _2243.x;
        _2255 = _2243.y;
        _2256 = _2243.z;
    }
    else
    {
        _2251 = 0.0;
        _2252 = 0.0;
        _2253 = 0.0;
        _2254 = 1.0;
        _2255 = 1.0;
        _2256 = 1.0;
    }
    D _2263 = (1.0 - _626) + (_626 * _440);
    D _2264 = (1.0 - _629) + (_629 * _440);
    D _2265 = (1.0 - _632) + (_632 * _440);
    SV_Target.x = View._m0[164u].y * ((((_2254 * _1955) + _2251) * _2263) + ((_1961 * (((((((((_466 * _442) * _697) * spvNMax(1.0, ((_521 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_521 * 4.79510021209716796875)) + (((_521 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _442)) * _442))) * _828) + _804) * _443) + _810) + ((((_898 * _594) * spvNClamp(1.0 - (_610 * _600), 0.0, 1.0)) * ((View._m0[164u].z * _874.x) + _816)) * _917)) + ((_711 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1456)) + 29.8973522186279296875) * _1462) + (-29.8973522186279296875)) + _822)) * spvNClamp(_689, 0.0, 1.0)))) * _2254));
    SV_Target.y = ((((_2255 * _1957) + _2252) * _2264) + ((_1963 * (((((((((_467 * _442) * _697) * spvNMax(1.0, ((_522 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_522 * 4.79510021209716796875)) + (((_522 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _442)) * _442))) * _830) + _806) * _443) + _812) + ((((_899 * _594) * spvNClamp(1.0 - (_611 * _600), 0.0, 1.0)) * ((View._m0[164u].z * _874.y) + _818)) * _917)) + ((_711 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1458)) + 29.8973522186279296875) * _1462) + (-29.8973522186279296875)) + _824)) * spvNClamp(_690, 0.0, 1.0)))) * _2255)) * View._m0[164u].y;
    SV_Target.z = ((((_2256 * _1959) + _2253) * _2265) + ((_1965 * (((((((((_468 * _442) * _697) * spvNMax(1.0, ((_523 * 2.755199909210205078125) + 0.69029998779296875) + (((0.6417000293731689453125 - (_523 * 4.79510021209716796875)) + (((_523 * 2.040400028228759765625) + (-0.3323999941349029541015625)) * _442)) * _442))) * _832) + _808) * _443) + _814) + ((((_900 * _594) * ((View._m0[164u].z * _874.z) + _820)) * spvNClamp(1.0 - (_612 * _600), 0.0, 1.0)) * _917)) + ((_711 * (exp2(((log2(spvNMax(9.999999717180685365747194737196e-10, _1460)) + 29.8973522186279296875) * _1462) + (-29.8973522186279296875)) + _826)) * spvNClamp(_691, 0.0, 1.0)))) * _2256)) * View._m0[164u].y;
    SV_Target.w = dot(vec3(_2263, _2264, _2265), vec3(0.2125999927520751953125, 0.715200006961822509765625, 0.072200000286102294921875));
    SV_Target_1.x = _2263;
    SV_Target_1.y = _2264;
    SV_Target_1.z = _2265;
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
} // namespace S_rystal_Convex_Wide_Character