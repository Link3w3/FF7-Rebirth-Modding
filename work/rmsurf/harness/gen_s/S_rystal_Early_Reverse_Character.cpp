namespace S_rystal_Early_Reverse_Character {
using namespace cpuglsl;
static D _3390;
static D _3392;
static D _3386;
static D _3387;
static D _3388;
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
static Tex2D Material_Texture2D_2{texid("junk:T_Normal")};
static Tex2D Material_Texture2D_3{texid("junk:T_Roughness")};
static Tex2D Material_Texture2D_6{texid("junk:T_Opacity")};
static Tex2D ForwardLightProfileTextures[64];
static Tex2D ShadowMaps[64];
static Samp View_SharedPointClampedSampler{texid("View_SharedPointClampedSampler")};
static Samp View_SharedBilinearWrappedSampler{texid("View_SharedBilinearWrappedSampler")};
static Samp View_SharedBilinearClampedSampler{texid("View_SharedBilinearClampedSampler")};
static Samp View_SharedAnisotropic4XWrappedSampler{texid("View_SharedAnisotropic4XWrappedSampler")};
static vec4 TEXCOORD_10;
static vec4 TEXCOORD_11;
static vec4 TEXCOORD;
static D CONSTANT_CONTEXT;
static vec4 SV_Target;
static vec4 SV_Target_1;
static bool discard_state;









void discard_cond(bool _3376)
{
    if (_3376)
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
    D _89 = 1.0 / gl_FragCoord.w;
    D _208 = fma(gl_FragCoord.z, View._m0[54u].w, fma(gl_FragCoord.y, View._m0[53u].w, View._m0[52u].w * gl_FragCoord.x)) + View._m0[55u].w;
    D _209 = (fma(gl_FragCoord.z, View._m0[54u].x, fma(gl_FragCoord.y, View._m0[53u].x, View._m0[52u].x * gl_FragCoord.x)) + View._m0[55u].x) / _208;
    D _210 = (fma(gl_FragCoord.z, View._m0[54u].y, fma(gl_FragCoord.y, View._m0[53u].y, View._m0[52u].y * gl_FragCoord.x)) + View._m0[55u].y) / _208;
    D _211 = (fma(gl_FragCoord.z, View._m0[54u].z, fma(gl_FragCoord.y, View._m0[53u].z, View._m0[52u].z * gl_FragCoord.x)) + View._m0[55u].z) / _208;
    D _212 = _209 - View._m0[78u].x;
    D _213 = _210 - View._m0[78u].y;
    D _214 = _211 - View._m0[78u].z;
    D _219 = inversesqrt(dot(vec3(_209, _210, _211), vec3(_209, _210, _211)));
    D _220 = _219 * _209;
    D _221 = _219 * _210;
    D _222 = _219 * _211;
    D _223 = (-0.0) - _220;
    D _225 = (-0.0) - _221;
    D _226 = (-0.0) - _222;
    vec4 _244 = texelFetch(View_SpatiotemporalBlueNoiseVolumeTexture, ivec3_(uvec3(uint(int(gl_FragCoord.x)) & 127u, uint(int(gl_FragCoord.y)) & 127u, ((floatBitsToUint(View._m0[175u]).x & 7u) + uint(roundEven(CONSTANT_CONTEXT))) & 63u)), int(0u));
    D _247 = _244.x;
    D _248 = _244.y;
    vec4 _254 = texture(sampler2D(Material_Texture2D_2, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _262 = (_254.x * 2.0) + (-1.0);
    D _264 = (_254.y * 2.0) + (-1.0);
    D _271 = sqrt(spvNMax(0.0, 1.0 - dot(vec2(_262, _264), vec2(_262, _264))));
    D _275 = inversesqrt(dot(vec3(_262, _264, _271), vec3(_262, _264, _271)));
    D _276 = _275 * _262;
    D _277 = _275 * _264;
    D _278 = _275 * _271;
    vec4 _281 = texture(sampler2D(Material_Texture2D_3, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    vec4 _286 = texture(sampler2D(Material_Texture2D_6, View_SharedAnisotropic4XWrappedSampler), vec2(TEXCOORD.x, TEXCOORD.y), View._m0[155u].y);
    D _292 = inversesqrt(dot(vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z), vec3(g_R.Normal.x, g_R.Normal.y, g_R.Normal.z)));
    D _293 = _292 * g_R.Normal.x;
    D _294 = _292 * g_R.Normal.y;
    D _295 = _292 * g_R.Normal.z;
    D _298 = fma(_295, TEXCOORD_11.x, fma(_294, ((TEXCOORD_10.z * TEXCOORD_11.y) - (TEXCOORD_10.y * TEXCOORD_11.z)) * TEXCOORD_11.w, _293 * TEXCOORD_10.x));
    D _301 = fma(_295, TEXCOORD_11.y, fma(_294, ((TEXCOORD_10.x * TEXCOORD_11.z) - (TEXCOORD_10.z * TEXCOORD_11.x)) * TEXCOORD_11.w, _293 * TEXCOORD_10.y));
    D _304 = fma(_295, TEXCOORD_11.z, fma(_294, ((TEXCOORD_10.y * TEXCOORD_11.x) - (TEXCOORD_10.x * TEXCOORD_11.y)) * TEXCOORD_11.w, _293 * TEXCOORD_10.z));
    D _308 = inversesqrt(dot(vec3(_298, _301, _304), vec3(_298, _301, _304)));
    D _309 = _308 * _298;
    D _310 = _308 * _301;
    D _311 = _308 * _304;
    bool _324;
    if (Primitive._m0[27u].w > ((_244.w * 0.99609375) + 0.001953125))
    {
        _324 = ((_247 * 0.99609375) + 0.001953125) < 1.0;
    }
    else
    {
        _324 = false;
    }
    (void)((_324 ? 1.0 : (-1.0)) < 0.0);
    D _330 = spvNClamp(g_R.Roughness, 0.0, 1.0);
    D _333 = dFdxFine(_309);
    D _334 = dFdxFine(_310);
    D _335 = dFdxFine(_311);
    D _339 = dFdyFine(_309);
    D _340 = dFdyFine(_310);
    D _341 = dFdyFine(_311);
    D _352 = sqrt(spvNClamp(spvNMin((dot(vec3(_339, _340, _341), vec3(_339, _340, _341)) + dot(vec3(_333, _334, _335), vec3(_333, _334, _335))) * 0.15915493667125701904296875, 0.180000007152557373046875) + (_330 * _330), 0.0, 1.0));
    D _362 = 0.159951984882354736328125 - (spvNClamp(D(View._m0[220u].x > 1.0), 0.0, 1.0) * 0.0943896770477294921875);
    D _370 = dot(vec3(_309, _310, _311), vec3(_223, _225, _226));
    D _373 = abs(_370);
    D _374 = spvNMax(9.9999997473787516355514526367188e-06, _373);
    D _382 = 1.0 - _352;
    D _396 = ((spvNMin(_382 * _382, exp2(_374 * (-9.27999973297119140625))) * _382) + (0.0425000004470348358154296875 - (_352 * 0.0274999998509883880615234375))) * 1.03999996185302734375;
    D _403 = 1.0 - spvNClamp(g_R.Opacity, 0.0, 1.0);
    D _405 = spvNMax(0.039999999105930328369140625, _352);
    D _421 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_405 * _374) + 0.02669160068035125732421875) / (_374 + 0.4664950072765350341796875)) * exp2(((1.0 / _405) * _374) * log2(_405)), 0.0, 1.0));
    D _423 = 1.0 - _374;
    D _424 = _423 * _423;
    D _439 = ((_424 * _424) * _423) * exp2(log2((exp2((_405 * 4.7702999114990234375) * log2(_374)) * 2.366509914398193359375) + 0.03873319923877716064453125) * _405);
    D _470;
    D _472;
    D _474;
    if (floatBitsToUint(TranslucentBasePass_2._m0[0u]).z == 0u)
    {
        _470 = 0.0;
        _472 = 0.0;
        _474 = 0.0;
    }
    else
    {
        D _694;
        uint _489;
        bool _490;
        for (;;)
        {
            _489 = floatBitsToUint(TranslucentBasePass_2._m0[7u]).z;
            _490 = _489 == 0u;
            if (!_490)
            {
                uint _945;
                uint _763 = 0u;
                for (;;)
                {
                    if (_89 < TranslucentBasePass._m0[_763 + 32u])
                    {
                        _945 = _763;
                        break;
                    }
                    else
                    {
                        uint _764 = _763 + 1u;
                        if (_764 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                        {
                            _763 = _764;
                            continue;
                        }
                        else
                        {
                            _945 = _489;
                            break;
                        }
                    }
                }
                if (_945 < floatBitsToUint(TranslucentBasePass_2._m0[7u]).z)
                {
                    uint _1162 = _945 << 2u;
                    uint _1163 = _1162 + 9u;
                    uint _1170 = _1162 + 10u;
                    uint _1177 = _1162 + 11u;
                    uint _1184 = _1162 + 12u;
                    uint _1191 = _945 + 25u;
                    D _1217 = fma(_214, TranslucentBasePass_2._m0[_1177].z, fma(_213, TranslucentBasePass_2._m0[_1170].z, TranslucentBasePass_2._m0[_1163].z * _212)) + TranslucentBasePass_2._m0[_1184].z;
                    D _1221 = fma(_214, TranslucentBasePass_2._m0[_1177].w, fma(_213, TranslucentBasePass_2._m0[_1170].w, TranslucentBasePass_2._m0[_1163].w * _212)) + TranslucentBasePass_2._m0[_1184].w;
                    D _1222 = (fma(_214, TranslucentBasePass_2._m0[_1177].x, fma(_213, TranslucentBasePass_2._m0[_1170].x, TranslucentBasePass_2._m0[_1163].x * _212)) + TranslucentBasePass_2._m0[_1184].x) / _1221;
                    D _1223 = (fma(_214, TranslucentBasePass_2._m0[_1177].y, fma(_213, TranslucentBasePass_2._m0[_1170].y, TranslucentBasePass_2._m0[_1163].y * _212)) + TranslucentBasePass_2._m0[_1184].y) / _1221;
                    bool _1230 = (_1223 <= TranslucentBasePass_2._m0[_1191].w) && ((_1222 <= TranslucentBasePass_2._m0[_1191].z) && ((_1222 >= TranslucentBasePass_2._m0[_1191].x) && (_1223 >= TranslucentBasePass_2._m0[_1191].y)));
                    D _695;
                    if (_1230)
                    {
                        D _1476 = dFdyFine(_1222);
                        D _1477 = dFdyFine(_1223);
                        D _1478 = dFdyFine(_1217);
                        D _1479 = dFdxFine(_1222);
                        D _1480 = dFdxFine(_1223);
                        D _1481 = dFdxFine(_1217);
                        D _1484 = (_1480 * _1478) - (_1481 * _1477);
                        D _1487 = (_1481 * _1476) - (_1479 * _1478);
                        D _1490 = (_1479 * _1477) - (_1480 * _1476);
                        D _1500 = 1.0 / spvNMax(abs(_1490), sqrt(((_1487 * _1487) + (_1490 * _1490)) + (_1484 * _1484)) * 0.100000001490116119384765625);
                        D _1506 = D(int(uint(_1490 > 0.0) - uint(_1490 < 0.0)));
                        D _1507 = _1484 * TranslucentBasePass_2._m0[29u].z;
                        D _1509 = (_1507 * _1500) * _1506;
                        D _1510 = _1487 * TranslucentBasePass_2._m0[29u].w;
                        D _1512 = (_1510 * _1500) * _1506;
                        D _2058;
                        D _2060;
                        if (dot(vec2(_1484, _1487), vec2(_1484, _1487)) < 1.0000000195414813782625560981111e-24)
                        {
                            _2058 = 0.0;
                            _2060 = 0.0;
                        }
                        else
                        {
                            D _2427 = (-0.0) - _1484;
                            D _2428 = (-0.0) - _1487;
                            D _2432 = inversesqrt(dot(vec2(_2427, _2428), vec2(_2427, _2428)));
                            _2058 = _2432 * _2427;
                            _2060 = _2432 * _2428;
                        }
                        D _2062 = _248 + (-0.5);
                        D _2067 = _247 + 0.5;
                        D _2070 = ((_2060 * _2062) + (_1222 * TranslucentBasePass_2._m0[29u].x)) + (_2058 * _2067);
                        D _2073 = ((_2058 * _2062) + (_1223 * TranslucentBasePass_2._m0[29u].y)) + (_2060 * _2067);
                        D _2074 = _2070 + (-0.5);
                        D _2075 = _2073 + (-0.5);
                        D _2076 = trunc(_2074);
                        D _2077 = trunc(_2075);
                        D _2078 = _2074 - _2076;
                        D _2079 = _2075 - _2077;
                        D _2080 = _2076 * TranslucentBasePass_2._m0[29u].z;
                        D _2081 = _2077 * TranslucentBasePass_2._m0[29u].w;
                        D _2084 = (_2076 + (-0.5)) - _2070;
                        D _2085 = (_2077 + (-0.5)) - _2073;
                        D _2086 = dot(vec2(_2084, _2085), vec2(_1509, _1512));
                        D _2089 = _2086 + _1512;
                        D _2092 = _1506 * (_1500 * (_1510 + _1507));
                        D _2093 = _2092 + _2086;
                        D _2094 = _2086 + _1509;
                        vec4 _2100 = textureGather((sampler2D(ShadowMaps[_945 + 0u], View_SharedPointClampedSampler)), vec2(_2080, _2081));
                        D _2101 = _2100.x;
                        D _2102 = _2100.y;
                        D _2103 = _2100.z;
                        D _2104 = _2100.w;
                        D _2141 = 1.525902189314365386962890625e-05 - _1217;
                        D _2171 = (_2076 + 1.5) - _2070;
                        D _2172 = dot(vec2(_2171, _2085), vec2(_1509, _1512));
                        D _2175 = _2172 + _1512;
                        D _2176 = _2092 + _2172;
                        D _2177 = _2172 + _1509;
                        vec4 _2179 = textureGatherOffset((sampler2D(ShadowMaps[_945 + 0u], View_SharedPointClampedSampler)), vec2(_2080, _2081), ivec2(2, 0));
                        D _2180 = _2179.x;
                        D _2181 = _2179.y;
                        D _2182 = _2179.z;
                        D _2183 = _2179.w;
                        D _2249 = (_2077 + 1.5) - _2073;
                        D _2250 = dot(vec2(_2084, _2249), vec2(_1509, _1512));
                        D _2253 = _2250 + _1512;
                        D _2254 = _2092 + _2250;
                        D _2255 = _2250 + _1509;
                        vec4 _2257 = textureGatherOffset((sampler2D(ShadowMaps[_945 + 0u], View_SharedPointClampedSampler)), vec2(_2080, _2081), ivec2(0, 2));
                        D _2258 = _2257.x;
                        D _2259 = _2257.y;
                        D _2260 = _2257.z;
                        D _2261 = _2257.w;
                        D _2326 = dot(vec2(_2171, _2249), vec2(_1509, _1512));
                        D _2329 = _2326 + _1512;
                        D _2330 = _2092 + _2326;
                        D _2331 = _2326 + _1509;
                        vec4 _2333 = textureGatherOffset((sampler2D(ShadowMaps[_945 + 0u], View_SharedPointClampedSampler)), vec2(_2080, _2081), ivec2(2));
                        D _2334 = _2333.x;
                        D _2335 = _2333.y;
                        D _2336 = _2333.z;
                        D _2337 = _2333.w;
                        D _2402 = 1.0 - _2078;
                        vec4 _2425 = vec4((((((_2104 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2141 + _2104) + (spvNMin(abs(_2086), 0.0) * D(int(uint(_2086 > 0.0) - uint(_2086 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2402) + ((_2103 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2141 + _2103) + (spvNMin(abs(_2094), 0.0) * D(int(uint(_2094 > 0.0) - uint(_2094 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2183 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2141 + _2183) + (spvNMin(abs(_2172), 0.0) * D(int(uint(_2172 > 0.0) - uint(_2172 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2182 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2141 + _2182) + (spvNMin(abs(_2177), 0.0) * D(int(uint(_2177 > 0.0) - uint(_2177 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2078), (((((_2101 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2141 + _2101) + (spvNMin(abs(_2089), 0.0) * D(int(uint(_2089 > 0.0) - uint(_2089 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2402) + ((_2102 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2141 + _2102) + (spvNMin(abs(_2093), 0.0) * D(int(uint(_2093 > 0.0) - uint(_2093 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2180 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2141 + _2180) + (spvNMin(abs(_2175), 0.0) * D(int(uint(_2175 > 0.0) - uint(_2175 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2181 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2141 + _2181) + (spvNMin(abs(_2176), 0.0) * D(int(uint(_2176 > 0.0) - uint(_2176 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2078), (((((_2261 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2141 + _2261) + (spvNMin(abs(_2250), 0.0) * D(int(uint(_2250 > 0.0) - uint(_2250 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2402) + ((_2260 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2141 + _2260) + (spvNMin(abs(_2255), 0.0) * D(int(uint(_2255 > 0.0) - uint(_2255 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2337 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2141 + _2337) + (spvNMin(abs(_2326), 0.0) * D(int(uint(_2326 > 0.0) - uint(_2326 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2336 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2141 + _2336) + (spvNMin(abs(_2331), 0.0) * D(int(uint(_2331 > 0.0) - uint(_2331 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2078), (((((_2258 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2141 + _2258) + (spvNMin(abs(_2253), 0.0) * D(int(uint(_2253 > 0.0) - uint(_2253 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2402) + ((_2259 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2141 + _2259) + (spvNMin(abs(_2254), 0.0) * D(int(uint(_2254 > 0.0) - uint(_2254 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + ((_2334 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2141 + _2334) + (spvNMin(abs(_2329), 0.0) * D(int(uint(_2329 > 0.0) - uint(_2329 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0))) + (((_2335 > 0.9900000095367431640625) ? 1.0 : spvNClamp((((_2141 + _2335) + (spvNMin(abs(_2330), 0.0) * D(int(uint(_2330 > 0.0) - uint(_2330 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) * _2078));
                        _695 = dot(_2425, vec4(1.0 - _2079, 1.0, 1.0, _2079)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        _695 = 1.0;
                    }
                    if (_1230)
                    {
                        _694 = _695;
                        break;
                    }
                }
            }
            if (floatBitsToUint(TranslucentBasePass_2._m0[30u]).y == 0u)
            {
                _694 = 1.0;
                break;
            }
            D _736 = fma(_214, TranslucentBasePass_2._m0[35u].z, fma(_213, TranslucentBasePass_2._m0[34u].z, TranslucentBasePass_2._m0[33u].z * _212)) + TranslucentBasePass_2._m0[36u].z;
            D _740 = fma(_214, TranslucentBasePass_2._m0[35u].w, fma(_213, TranslucentBasePass_2._m0[34u].w, TranslucentBasePass_2._m0[33u].w * _212)) + TranslucentBasePass_2._m0[36u].w;
            D _741 = (fma(_214, TranslucentBasePass_2._m0[35u].x, fma(_213, TranslucentBasePass_2._m0[34u].x, TranslucentBasePass_2._m0[33u].x * _212)) + TranslucentBasePass_2._m0[36u].x) / _740;
            D _742 = (fma(_214, TranslucentBasePass_2._m0[35u].y, fma(_213, TranslucentBasePass_2._m0[34u].y, TranslucentBasePass_2._m0[33u].y * _212)) + TranslucentBasePass_2._m0[36u].y) / _740;
            uvec4 _746 = floatBitsToUint(TranslucentBasePass_2._m0[32u]);
            uint _747 = _746.x;
            uint _748 = _746.y;
            uint _749 = _746.z;
            uint _754 = uint(int(floor(_741)));
            uint _755 = uint(int((-0.0) - floor(_742)));
            if (!((int(_755) < int(_746.w)) && ((int(_754) < int(_749)) && ((int(_754) >= int(_747)) && (int(_755) >= int(_748))))))
            {
                _694 = 1.0;
                break;
            }
            D _908 = dFdyFine(_741);
            D _909 = dFdyFine(_742);
            D _910 = dFdyFine(_736);
            D _911 = dFdxFine(_741);
            D _912 = dFdxFine(_742);
            D _913 = dFdxFine(_736);
            D _916 = (_912 * _910) - (_913 * _909);
            D _919 = (_913 * _908) - (_911 * _910);
            D _922 = (_911 * _909) - (_912 * _908);
            D _933 = 1.0 / spvNMax(abs(_922), sqrt(((_919 * _919) + (_922 * _922)) + (_916 * _916)) * 0.100000001490116119384765625);
            D _939 = D(int(uint(_922 > 0.0) - uint(_922 < 0.0)));
            D _1089;
            D _1091;
            if (dot(vec2(_916, _919), vec2(_916, _919)) < 1.0000000195414813782625560981111e-24)
            {
                _1089 = 0.0;
                _1091 = 0.0;
            }
            else
            {
                D _1155 = (-0.0) - _916;
                D _1156 = (-0.0) - _919;
                D _1160 = inversesqrt(dot(vec2(_1155, _1156), vec2(_1155, _1156)));
                _1089 = _1160 * _1155;
                _1091 = _1160 * _1156;
            }
            D _1097 = _248 + (-0.5);
            D _1105 = (((_1091 * _1097) + (_1089 * _247)) * 2.0) + (_1089 * 0.5);
            D _1106 = (((_1091 * _247) + (_1089 * _1097)) * 2.0) + (_1091 * 0.5);
            D _1112 = _1105 + (fract(_741) * 256.0);
            D _1113 = _1106 + (fract(_742) * 256.0);
            D _1126 = dot(vec2((floor(_1112) + 0.5) - _1112, (floor(_1113) + 0.5) - _1113), vec2(((_916 * 256.0) * _933) * _939, ((_919 * 256.0) * _933) * _939));
            D _1132 = (_1105 * 0.00390625) + _741;
            D _1133 = (_1106 * 0.00390625) + _742;
            uint _1145 = ((uint(int((-0.0) - floor(_1133))) - _748) * (_749 - _747)) + (uint(int(floor(_1132))) - _747);
            D _1447;
            D _1450;
            if ((texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowLoadedTileData, int(_1145 >> 5u)).x & (1u << (_1145 & 31u))) == 0u)
            {
                _1447 = 3.0000000054977557577780399428115e+38;
                _1450 = 0.0;
            }
            else
            {
                uvec4 _1473 = uvec4(texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileIndices, int(_1145)));
                uint _1474 = _1473.x;
                D frontier_phi_50_51_ladder;
                D frontier_phi_50_51_ladder_1;
                if (int(_1474) > int(4294967295u))
                {
                    uint _2044 = (uint(floor(fract(_1132) * 256.0)) + (_1474 << 16u)) + (uint(floor(fract(_1133) * 256.0)) << 8u);
                    uvec4 _2047 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthTileData, int(_2044 >> 1u));
                    uint _2048 = _2047.x;
                    D _2056 = D((((_2044 & 1u) == 0u) ? _2048 : (_2048 >> 16u)) & 65535u) * 1.525902189314365386962890625e-05;
                    D frontier_phi_50_51_ladder_71_ladder;
                    D frontier_phi_50_51_ladder_71_ladder_1;
                    if (_2056 != 1.0)
                    {
                        vec4 _2811 = texelFetch(TranslucentBasePass_Shared_Forward_DirectionalLightStaticShadowDepthRanges, int(_1474));
                        D _2813 = _2811.y;
                        frontier_phi_50_51_ladder_71_ladder = 1.0 / _2813;
                        frontier_phi_50_51_ladder_71_ladder_1 = (_2813 * _2056) + _2811.x;
                    }
                    else
                    {
                        frontier_phi_50_51_ladder_71_ladder = 0.0;
                        frontier_phi_50_51_ladder_71_ladder_1 = 3.0000000054977557577780399428115e+38;
                    }
                    frontier_phi_50_51_ladder = frontier_phi_50_51_ladder_71_ladder;
                    frontier_phi_50_51_ladder_1 = frontier_phi_50_51_ladder_71_ladder_1;
                }
                else
                {
                    frontier_phi_50_51_ladder = 0.0;
                    frontier_phi_50_51_ladder_1 = 3.0000000054977557577780399428115e+38;
                }
                _1447 = frontier_phi_50_51_ladder_1;
                _1450 = frontier_phi_50_51_ladder;
            }
            _694 = spvNClamp(((((1.525902189314365386962890625e-05 - _736) + _1447) + (spvNMin(abs(_1126), _1450 * 10.0) * D(int(uint(_1126 > 0.0) - uint(_1126 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0);
            break;
        }
        D _896;
        if ((floatBitsToUint(Primitive._m0[27u]).z & 2u) == 0u)
        {
            _896 = 1.0;
        }
        else
        {
            _896 = View._m0[188u].y;
        }
        uvec4 _900 = floatBitsToUint(View._m0[220u]);
        uint _901 = _900.y;
        uint _903 = (_901 != 1u) ? 4294967295u : 0u;
        uint _1087;
        if (_901 > 1u)
        {
            D _113[4];
            _113[0u] = 0.0;
            _113[1u] = 0.0;
            _113[2u] = 0.0;
            _113[3u] = 0.0;
            uint _1433 = 0u;
            bool _1439;
            for (;;)
            {
                _1439 = _1433 < floatBitsToUint(View._m0[220u]).y;
                if (_1439)
                {
                    uint _1997 = _1433 + 237u;
                    D _2009 = View._m0[_1997].x - View._m0[75u].x;
                    D _2010 = View._m0[_1997].y - View._m0[75u].y;
                    D _2011 = View._m0[_1997].z - View._m0[75u].z;
                    D _2012 = dot(vec3(_2009, _2010, _2011), vec3(_220, _221, _222));
                    D _2019 = dot(vec3(_2009, _2010, _2011), vec3(_2009, _2010, _2011)) - (View._m0[_1997].w * View._m0[_1997].w);
                    D _2021 = (_2012 * _2012) - _2019;
                    D _2585;
                    if ((_2019 < 0.0) && (!(_2021 < 0.0)))
                    {
                        D _2579 = sqrt(_2021);
                        _2585 = spvNMin(abs(_2579 + _2012), abs(_2012 - _2579));
                    }
                    else
                    {
                        _2585 = 0.0;
                    }
                    _113[_1433] = _2585;
                }
                uint _1434 = _1433 + 1u;
                if (_1434 == 4u)
                {
                    break;
                }
                else
                {
                    _1433 = _1434;
                    continue;
                }
            }
            D _2595 = (_247 * 0.99989998340606689453125) * dot(vec4(_113[0u], _113[1u], _113[2u], _113[3u]), vec4(1.0));
            uint frontier_phi_33_82_ladder;
            if (_113[0u] > _2595)
            {
                frontier_phi_33_82_ladder = 0u;
            }
            else
            {
                D _2854 = _113[1u] + _113[0u];
                uint frontier_phi_33_82_ladder_90_ladder;
                if (_2854 > _2595)
                {
                    frontier_phi_33_82_ladder_90_ladder = 1u;
                }
                else
                {
                    D _2867 = _2854 + _113[2u];
                    uint frontier_phi_33_82_ladder_90_ladder_94_ladder;
                    if (_2867 > _2595)
                    {
                        frontier_phi_33_82_ladder_90_ladder_94_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_33_82_ladder_90_ladder_94_ladder_98_ladder;
                        if ((_2867 + _113[3u]) > _2595)
                        {
                            frontier_phi_33_82_ladder_90_ladder_94_ladder_98_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_33_82_ladder_90_ladder_94_ladder_98_ladder = _903;
                        }
                        frontier_phi_33_82_ladder_90_ladder_94_ladder = frontier_phi_33_82_ladder_90_ladder_94_ladder_98_ladder;
                    }
                    frontier_phi_33_82_ladder_90_ladder = frontier_phi_33_82_ladder_90_ladder_94_ladder;
                }
                frontier_phi_33_82_ladder = frontier_phi_33_82_ladder_90_ladder;
            }
            _1087 = frontier_phi_33_82_ladder;
        }
        else
        {
            _1087 = _903;
        }
        D _1440;
        if (_1087 == 4294967295u)
        {
            _1440 = _896;
        }
        else
        {
            _1440 = View._m0[_1087 + 241u].x * _896;
        }
        D frontier_phi_3_48_ladder;
        D frontier_phi_3_48_ladder_1;
        D frontier_phi_3_48_ladder_2;
        if (_1440 > 0.0)
        {
            D _2028 = spvNClamp((TranslucentBasePass_2._m0[7u].x * _89) + TranslucentBasePass_2._m0[7u].y, 0.0, 1.0);
            D _2032 = ((_2028 * _2028) * (1.0 - _694)) + _694;
            D frontier_phi_3_48_ladder_70_ladder;
            D frontier_phi_3_48_ladder_70_ladder_1;
            D frontier_phi_3_48_ladder_70_ladder_2;
            if (_2032 > 0.0)
            {
                D _2597 = dot(vec3(_309, _310, _311), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _2600 = spvNMax(0.0, _2597);
                D _2601 = dot(vec3(_223, _225, _226), vec3(TranslucentBasePass_2._m0[5u].xyz()));
                D _2607 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_2601 * 2.0) + 2.0));
                D _2610 = spvNClamp(_2607 * (_370 + _2597), 0.0, 1.0);
                D _2615 = _405 * _405;
                D _2616 = _2615 * _2615;
                D _2617 = _2616 + (-1.0);
                D _2620 = ((_2610 * _2610) * _2617) + 1.0;
                D _2621 = _2616 * 0.3183098733425140380859375;
                D _2626 = (_2600 * 2.0) * _374;
                D _2631 = 1.0 - spvNMax(9.9999997473787516355514526367188e-06, spvNMin(_2607 * (_2601 + 1.0), 1.0));
                D _2632 = _2631 * _2631;
                D _2644 = spvNMax(0.039999999105930328369140625, _405);
                D _2657 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_2644 * _2600) + 0.02669160068035125732421875) / (_2600 + 0.4664950072765350341796875)) * exp2(((1.0 / _2644) * _2600) * log2(_2644)), 0.0, 1.0));
                D _2668 = spvNClamp(_2600 * 999.99993896484375, 0.0, 1.0);
                D _2675 = dot(vec3(_362), vec3(0.3333333432674407958984375));
                D _2684 = 1.0 / ((2.0 / spvNMax(9.9999997473787516355514526367188e-05, 1.0 - sqrt(_2675))) + (-1.0));
                D _2685 = (-0.0) - _309;
                D _2686 = (-0.0) - _310;
                D _2687 = (-0.0) - _311;
                D _2688 = _370 * 2.0;
                D _2692 = _223 - (_2688 * _309);
                D _2693 = _225 - (_2688 * _310);
                D _2694 = _226 - (_2688 * _311);
                D _2698 = inversesqrt(dot(vec3(_2692, _2693, _2694), vec3(_2692, _2693, _2694)));
                D _2699 = _2692 * _2698;
                D _2700 = _2693 * _2698;
                D _2701 = _2694 * _2698;
                D _2705 = (_2699 * _2684) + TranslucentBasePass_2._m0[5u].x;
                D _2706 = (_2700 * _2684) + TranslucentBasePass_2._m0[5u].y;
                D _2707 = (_2701 * _2684) + TranslucentBasePass_2._m0[5u].z;
                D _2711 = inversesqrt(dot(vec3(_2705, _2706, _2707), vec3(_2705, _2706, _2707)));
                D _2712 = _2705 * _2711;
                D _2713 = _2706 * _2711;
                D _2714 = _2707 * _2711;
                D _2715 = dot(vec3(_2712, _2713, _2714), vec3(_2699, _2700, _2701));
                D _2727 = (((_2712 * _2715) - _2699) * 2.0) + _2699;
                D _2728 = (((_2713 * _2715) - _2700) * 2.0) + _2700;
                D _2729 = (((_2714 * _2715) - _2701) * 2.0) + _2701;
                D _2733 = inversesqrt(dot(vec3(_2727, _2728, _2729), vec3(_2727, _2728, _2729)));
                D _2734 = _2727 * _2733;
                D _2735 = _2728 * _2733;
                D _2736 = _2729 * _2733;
                D _2740 = spvNMax(0.0, dot(vec3(_2685, _2686, _2687), vec3(TranslucentBasePass_2._m0[5u].xyz())));
                D _2744 = dot(vec3(_2685, _2686, _2687), vec3(_2699, _2700, _2701));
                D _2747 = dot(vec3(_2699, _2700, _2701), vec3(_2734, _2735, _2736));
                D _2753 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_2747 * 2.0) + 2.0));
                D _2756 = spvNClamp(_2753 * (_2744 + dot(vec3(_2685, _2686, _2687), vec3(_2734, _2735, _2736))), 0.0, 1.0);
                D _2762 = spvNMax(9.9999997473787516355514526367188e-06, abs(_2744));
                D _2765 = ((_2756 * _2756) * _2617) + 1.0;
                D _2770 = (_2740 * 2.0) * _2762;
                D _2775 = 1.0 - spvNMax(9.9999997473787516355514526367188e-06, spvNMin(_2753 * (_2747 + 1.0), 1.0));
                D _2776 = _2775 * _2775;
                D _2790 = dot(vec3(TranslucentBasePass_2._m0[5u].xyz()), vec3(_2712, _2713, _2714));
                D _2794 = dot(vec3(_2699, _2700, _2701), vec3(_2712, _2713, _2714));
                D _2800 = (_2794 * _2684) + _2790;
                D _2806 = (((spvNClamp(_2794, 0.0, 1.0) * spvNClamp(_2790, 0.0, 1.0)) * (1.0 / spvNMax(9.9999997473787516355514526367188e-06, _2800 * _2800))) * ((((_2621 * _2740) * (1.0 / (_2765 * _2765))) * (0.5 / ((_2615 * ((_2762 + _2740) - _2770)) + _2770))) * ((1.0 - _2675) - (((_2776 * _2776) * _2775) * (spvNMin(_2675 * 50.0, 1.0) - _2675))))) + (((((((_2621 * _2600) * (1.0 / (_2620 * _2620))) * (0.5 / ((_2615 * ((_374 + _2600) - _2626)) + _2626))) * 0.840048015117645263671875) * spvNClamp(((spvNMin(dot(vec3(_362), vec3(16.666667938232421875)), 1.0) - _362) * ((_2632 * _2632) * _2631)) + _362, 0.0, 1.0)) * spvNMin(_2032, _2668 * _2668)) * ((((1.0 - _2657) * (1.0 / _2657)) * _362) + 1.0));
                frontier_phi_3_48_ladder_70_ladder = (_1440 * TranslucentBasePass_2._m0[4u].z) * _2806;
                frontier_phi_3_48_ladder_70_ladder_1 = (_1440 * TranslucentBasePass_2._m0[4u].y) * _2806;
                frontier_phi_3_48_ladder_70_ladder_2 = (_1440 * TranslucentBasePass_2._m0[4u].x) * _2806;
            }
            else
            {
                frontier_phi_3_48_ladder_70_ladder = 0.0;
                frontier_phi_3_48_ladder_70_ladder_1 = 0.0;
                frontier_phi_3_48_ladder_70_ladder_2 = 0.0;
            }
            frontier_phi_3_48_ladder = frontier_phi_3_48_ladder_70_ladder;
            frontier_phi_3_48_ladder_1 = frontier_phi_3_48_ladder_70_ladder_1;
            frontier_phi_3_48_ladder_2 = frontier_phi_3_48_ladder_70_ladder_2;
        }
        else
        {
            frontier_phi_3_48_ladder = 0.0;
            frontier_phi_3_48_ladder_1 = 0.0;
            frontier_phi_3_48_ladder_2 = 0.0;
        }
        _470 = frontier_phi_3_48_ladder_2;
        _472 = frontier_phi_3_48_ladder_1;
        _474 = frontier_phi_3_48_ladder;
    }
    uvec4 _478 = floatBitsToUint(TranslucentBasePass_2._m0[0u]);
    uint _479 = _478.x;
    uint _484 = min(min(texelFetch(TranslucentBasePass_Shared_Forward_NumCulledLightsGrid, int(0u)).x, _479), _479);
    D _491;
    D _493;
    D _495;
    D _497;
    D _499;
    D _501;
    if (_484 == 0u)
    {
        _491 = _470;
        _493 = _472;
        _495 = _474;
        _497 = 0.0;
        _499 = 0.0;
        _501 = 0.0;
    }
    else
    {
        D _492;
        D _494;
        D _496;
        D _498;
        D _500;
        D _502;
        D _617 = _470;
        D _618 = _472;
        D _619 = _474;
        D _620 = 0.0;
        D _621 = 0.0;
        D _622 = 0.0;
        uint _623 = 0u;
        D _627;
        D _628;
        D _629;
        D _630;
        D _632;
        D _633;
        D _634;
        D _636;
        D _637;
        D _638;
        uint _640;
        D _642;
        D _643;
        D _645;
        D _646;
        D _647;
        D _649;
        D _650;
        uint _652;
        D _655;
        D _656;
        D _657;
        D _658;
        uint _661;
        D _664;
        D _665;
        D _666;
        D _667;
        D _670;
        D _671;
        D _672;
        D _673;
        D _676;
        D _677;
        D _678;
        D _679;
        D _682;
        D _683;
        D _684;
        D _685;
        bool _688;
        bool _689;
        bool _693;
        for (;;)
        {
            vec4 _626 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(0u));
            _627 = _626.x;
            _628 = _626.y;
            _629 = _626.z;
            _630 = _626.w;
            vec4 _631 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(1u));
            _632 = _631.x;
            _633 = _631.y;
            _634 = _631.z;
            vec4 _635 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(2u));
            _636 = _635.x;
            _637 = _635.y;
            _638 = _635.z;
            _640 = floatBitsToUint(_635.w);
            vec4 _641 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(3u));
            _642 = _641.x;
            _643 = _641.y;
            vec4 _644 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(4u));
            _645 = _644.x;
            _646 = _644.y;
            _647 = _644.z;
            vec4 _648 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(5u));
            _649 = _648.x;
            _650 = _648.y;
            _652 = floatBitsToUint(_648.z);
            vec4 _654 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(6u));
            _655 = _654.x;
            _656 = _654.y;
            _657 = _654.z;
            _658 = _654.w;
            _661 = floatBitsToUint(texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(7u)).x);
            vec4 _663 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(8u));
            _664 = _663.x;
            _665 = _663.y;
            _666 = _663.z;
            _667 = _663.w;
            vec4 _669 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(9u));
            _670 = _669.x;
            _671 = _669.y;
            _672 = _669.z;
            _673 = _669.w;
            vec4 _675 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(10u));
            _676 = _675.x;
            _677 = _675.y;
            _678 = _675.z;
            _679 = _675.w;
            vec4 _681 = texelFetch(TranslucentBasePass_Shared_Forward_ForwardLocalLightBuffer, int(11u));
            _682 = _681.x;
            _683 = _681.y;
            _684 = _681.z;
            _685 = _681.w;
            _688 = (_640 & 131072u) != 0u;
            _689 = _642 > (-2.0);
            _693 = (_640 & 16384u) == 0u;
            D frontier_phi_46_pred;
            D frontier_phi_46_pred_1;
            D frontier_phi_46_pred_2;
            D frontier_phi_46_pred_3;
            D frontier_phi_46_pred_4;
            D frontier_phi_46_pred_5;
            if (_693)
            {
                D _1050;
                if (_688)
                {
                    uint _1014 = _661 + 0u;
                    uvec2 _1018 = uvec2(textureSize(ShadowMaps[(_1014)], int(0u)));
                    D _1020 = D(int(_1018.x));
                    D _1022 = D(int(_1018.y));
                    D _1023 = 1.0 / _1020;
                    D _1024 = 1.0 / _1022;
                    D _1036 = fma(_214, _678, fma(_213, _672, _666 * _212)) + _684;
                    D _1040 = fma(_214, _679, fma(_213, _673, _667 * _212)) + _685;
                    D _1041 = (fma(_214, _676, fma(_213, _670, _664 * _212)) + _682) / _1040;
                    D _1042 = (fma(_214, _677, fma(_213, _671, _665 * _212)) + _683) / _1040;
                    D frontier_phi_29_28_ladder;
                    if ((_1042 <= _658) && ((_1041 <= _657) && ((_1041 >= _655) && (_1042 >= _656))))
                    {
                        D _1323 = dFdyFine(_1041);
                        D _1324 = dFdyFine(_1042);
                        D _1325 = dFdyFine(_1036);
                        D _1326 = dFdxFine(_1041);
                        D _1327 = dFdxFine(_1042);
                        D _1328 = dFdxFine(_1036);
                        D _1331 = (_1327 * _1325) - (_1328 * _1324);
                        D _1334 = (_1328 * _1323) - (_1326 * _1325);
                        D _1337 = (_1326 * _1324) - (_1327 * _1323);
                        D _1347 = 1.0 / spvNMax(abs(_1337), sqrt(((_1334 * _1334) + (_1337 * _1337)) + (_1331 * _1331)) * 0.100000001490116119384765625);
                        D _1353 = D(int(uint(_1337 > 0.0) - uint(_1337 < 0.0)));
                        D _1354 = _1331 * _1023;
                        D _1356 = (_1354 * _1347) * _1353;
                        D _1357 = _1334 * _1024;
                        D _1359 = (_1357 * _1347) * _1353;
                        D _1592;
                        D _1594;
                        if (dot(vec2(_1331, _1334), vec2(_1331, _1334)) < 1.0000000195414813782625560981111e-24)
                        {
                            _1592 = 0.0;
                            _1594 = 0.0;
                        }
                        else
                        {
                            D _1935 = (-0.0) - _1331;
                            D _1936 = (-0.0) - _1334;
                            D _1940 = inversesqrt(dot(vec2(_1935, _1936), vec2(_1935, _1936)));
                            _1592 = _1940 * _1935;
                            _1594 = _1940 * _1936;
                        }
                        D _1596 = _248 + (-0.5);
                        D _1601 = _247 + 0.5;
                        D _1604 = ((_1594 * _1596) + (_1041 * _1020)) + (_1592 * _1601);
                        D _1607 = ((_1592 * _1596) + (_1042 * _1022)) + (_1594 * _1601);
                        D _1608 = _1604 + (-0.5);
                        D _1609 = _1607 + (-0.5);
                        D _1610 = trunc(_1608);
                        D _1611 = trunc(_1609);
                        D _1612 = _1608 - _1610;
                        D _1613 = _1609 - _1611;
                        D _1614 = _1610 * _1023;
                        D _1615 = _1611 * _1024;
                        D _1618 = (_1610 + (-0.5)) - _1604;
                        D _1619 = (_1611 + (-0.5)) - _1607;
                        D _1620 = dot(vec2(_1618, _1619), vec2(_1356, _1359));
                        D _1623 = _1620 + _1359;
                        D _1626 = _1353 * (_1347 * (_1357 + _1354));
                        D _1627 = _1626 + _1620;
                        D _1628 = _1620 + _1356;
                        vec4 _1632 = textureGather((sampler2D(ShadowMaps[_1014], View_SharedPointClampedSampler)), vec2(_1614, _1615));
                        D _1673 = 1.525902189314365386962890625e-05 - _1036;
                        D _1696 = (_1610 + 1.5) - _1604;
                        D _1697 = dot(vec2(_1696, _1619), vec2(_1356, _1359));
                        D _1700 = _1697 + _1359;
                        D _1701 = _1626 + _1697;
                        D _1702 = _1697 + _1356;
                        vec4 _1706 = textureGatherOffset((sampler2D(ShadowMaps[_1014], View_SharedPointClampedSampler)), vec2(_1614, _1615), ivec2(2, 0));
                        D _1770 = (_1611 + 1.5) - _1607;
                        D _1771 = dot(vec2(_1618, _1770), vec2(_1356, _1359));
                        D _1774 = _1771 + _1359;
                        D _1775 = _1626 + _1771;
                        D _1776 = _1771 + _1356;
                        vec4 _1778 = textureGatherOffset((sampler2D(ShadowMaps[_1014], View_SharedPointClampedSampler)), vec2(_1614, _1615), ivec2(0, 2));
                        D _1840 = dot(vec2(_1696, _1770), vec2(_1356, _1359));
                        D _1843 = _1840 + _1359;
                        D _1844 = _1626 + _1840;
                        D _1845 = _1840 + _1356;
                        vec4 _1847 = textureGatherOffset((sampler2D(ShadowMaps[_1014], View_SharedPointClampedSampler)), vec2(_1614, _1615), ivec2(2));
                        D _1909 = 1.0 - _1612;
                        vec4 _1932 = vec4((((spvNClamp((((_1673 + _1632.w) + (spvNMin(abs(_1620), 0.0) * D(int(uint(_1620 > 0.0) - uint(_1620 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _1909) + spvNClamp((((_1673 + _1632.z) + (spvNMin(abs(_1628), 0.0) * D(int(uint(_1628 > 0.0) - uint(_1628 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_1673 + _1706.w) + (spvNMin(abs(_1697), 0.0) * D(int(uint(_1697 > 0.0) - uint(_1697 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_1673 + _1706.z) + (spvNMin(abs(_1702), 0.0) * D(int(uint(_1702 > 0.0) - uint(_1702 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _1612), (((spvNClamp((((_1673 + _1632.x) + (spvNMin(abs(_1623), 0.0) * D(int(uint(_1623 > 0.0) - uint(_1623 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _1909) + spvNClamp((((_1673 + _1632.y) + (spvNMin(abs(_1627), 0.0) * D(int(uint(_1627 > 0.0) - uint(_1627 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_1673 + _1706.x) + (spvNMin(abs(_1700), 0.0) * D(int(uint(_1700 > 0.0) - uint(_1700 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_1673 + _1706.y) + (spvNMin(abs(_1701), 0.0) * D(int(uint(_1701 > 0.0) - uint(_1701 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _1612), (((spvNClamp((((_1673 + _1778.w) + (spvNMin(abs(_1771), 0.0) * D(int(uint(_1771 > 0.0) - uint(_1771 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _1909) + spvNClamp((((_1673 + _1778.z) + (spvNMin(abs(_1776), 0.0) * D(int(uint(_1776 > 0.0) - uint(_1776 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_1673 + _1847.w) + (spvNMin(abs(_1840), 0.0) * D(int(uint(_1840 > 0.0) - uint(_1840 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_1673 + _1847.z) + (spvNMin(abs(_1845), 0.0) * D(int(uint(_1845 > 0.0) - uint(_1845 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _1612), (((spvNClamp((((_1673 + _1778.x) + (spvNMin(abs(_1774), 0.0) * D(int(uint(_1774 > 0.0) - uint(_1774 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _1909) + spvNClamp((((_1673 + _1778.y) + (spvNMin(abs(_1775), 0.0) * D(int(uint(_1775 > 0.0) - uint(_1775 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + spvNClamp((((_1673 + _1847.x) + (spvNMin(abs(_1843), 0.0) * D(int(uint(_1843 > 0.0) - uint(_1843 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0)) + (spvNClamp((((_1673 + _1847.y) + (spvNMin(abs(_1844), 0.0) * D(int(uint(_1844 > 0.0) - uint(_1844 < 0.0))))) * 65535.0) + 1.0, 0.0, 1.0) * _1612));
                        frontier_phi_29_28_ladder = dot(_1932, vec4(1.0 - _1613, 1.0, 1.0, _1613)) * 0.111111111938953399658203125;
                    }
                    else
                    {
                        frontier_phi_29_28_ladder = 1.0;
                    }
                    _1050 = frontier_phi_29_28_ladder;
                }
                else
                {
                    _1050 = 1.0;
                }
                D _1056 = _627 - _212;
                D _1057 = _628 - _213;
                D _1058 = _629 - _214;
                D _1059 = dot(vec3(_1056, _1057, _1058), vec3(_1056, _1057, _1058));
                D _1368;
                D _1369;
                D _1370;
                if (_1059 > 9.9999997473787516355514526367188e-05)
                {
                    D _1364 = inversesqrt(_1059);
                    _1368 = _1364 * _1056;
                    _1369 = _1364 * _1057;
                    _1370 = _1364 * _1058;
                }
                else
                {
                    _1368 = 0.0;
                    _1369 = 0.0;
                    _1370 = 0.0;
                }
                D _1371 = _649 * _649;
                D _1375 = (_630 * _630) * _1059;
                D _1378 = spvNClamp(1.0 - (_1375 * _1375), 0.0, 1.0);
                D _1948;
                if (_689)
                {
                    D _1946 = spvNClamp((dot(vec3(_1368, _1369, _1370), vec3(_636, _637, _638)) - _642) * _643, 0.0, 1.0);
                    _1948 = _1946 * _1946;
                }
                else
                {
                    _1948 = 1.0;
                }
                D _1949 = ((_1378 * _1378) * D(_1059 >= _1371)) * _1948;
                D _2443;
                D _2445;
                D _2447;
                if ((_640 & 262144u) == 0u)
                {
                    _2443 = 1.0;
                    _2445 = 1.0;
                    _2447 = 1.0;
                }
                else
                {
                    D _2450 = (-0.0) - _637;
                    D _2451 = (-0.0) - _638;
                    D _2452 = (-0.0) - _636;
                    D _2462 = (-0.0) - _1368;
                    D _2463 = (-0.0) - _1369;
                    D _2464 = (-0.0) - _1370;
                    D _2467 = fma(_2451, _2464, fma(_2450, _2463, _1368 * _636));
                    D _2470 = fma(_647, _2464, fma(_646, _2463, _645 * _2462));
                    D _2478 = atan(((-0.0) - _2470) / ((-0.0) - _2467));
                    bool _2483 = _2467 > (-0.0);
                    bool _2484 = _2467 == (-0.0);
                    bool _2485 = _2470 <= (-0.0);
                    bool _2486 = _2470 > (-0.0);
                    vec4 _2507 = texture((sampler2D(ForwardLightProfileTextures[_652 + 0u], View_SharedBilinearWrappedSampler)), vec2(fract((_2484 && _2485) ? 1.25 : ((_2484 && _2486) ? 0.75 : ((((_2483 && _2486) ? (_2478 + (-3.1415927410125732421875)) : ((_2483 && _2485) ? (_2478 + 3.1415927410125732421875) : _2478)) * 0.15915493667125701904296875) + 1.0))), (asin((-0.0) - fma((_646 * _2452) - (_645 * _2450), _2464, fma((_645 * _2451) - (_647 * _2452), _2463, ((_647 * _2450) - (_646 * _2451)) * _2462))) * 0.3183098733425140380859375) + 0.5));
                    _2443 = _2507.x;
                    _2445 = _2507.y;
                    _2447 = _2507.z;
                }
                D _2817;
                D _2819;
                D _2821;
                for (;;)
                {
                    if (_1949 > 0.0)
                    {
                        D _2859;
                        if (_688)
                        {
                            if (!(_1050 > 0.0))
                            {
                                _2817 = 0.0;
                                _2819 = 0.0;
                                _2821 = 0.0;
                                break;
                            }
                            _2859 = _1050;
                        }
                        else
                        {
                            _2859 = 1.0;
                        }
                        D _2861 = spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _1059));
                        D _2862 = 1.0 / _2861;
                        D _2863 = dot(vec3(_309, _310, _311), vec3(_1368, _1369, _1370));
                        bool _2866 = _649 > 0.0;
                        D _2874;
                        if (_2866)
                        {
                            D _2871 = sqrt(spvNClamp(_1371 * _2862, 0.0, 1.0));
                            D frontier_phi_97_96_ladder;
                            if (_2871 > spvNMax(9.9999997473787516355514526367188e-06, _2863))
                            {
                                D _2891 = spvNMax((-0.0) - _2871, _2863) + _2871;
                                frontier_phi_97_96_ladder = (_2891 * _2891) * (0.25 / _2871);
                            }
                            else
                            {
                                frontier_phi_97_96_ladder = _2863;
                            }
                            _2874 = frontier_phi_97_96_ladder;
                        }
                        else
                        {
                            _2874 = _2863;
                        }
                        D _2932;
                        D _2933;
                        D _2876;
                        D _2878;
                        D _2882;
                        D _2883;
                        bool _2886;
                        for (;;)
                        {
                            _2876 = spvNMax(0.0, _2874);
                            _2878 = _405 * _405;
                            _2882 = spvNClamp(((1.0 - _2878) * _649) * inversesqrt(_2861), 0.0, 1.0);
                            _2883 = dot(vec3(_223, _225, _226), vec3(_1368, _1369, _1370));
                            _2886 = _2882 > 0.0;
                            D _2902;
                            D _2904;
                            if (_2886)
                            {
                                D _2897 = sqrt(spvNMax(0.0, 1.0 - (_2882 * _2882)));
                                D _2900 = ((_2863 * 2.0) * _370) - _2883;
                                if (!(!(_2900 >= _2897)))
                                {
                                    _2932 = _373;
                                    _2933 = 1.0;
                                    break;
                                }
                                D _2920 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, 1.0 - (_2900 * _2900))) * _2882;
                                _2902 = (_2920 * ((((_370 * _370) * 2.0) + (-1.0)) - (_2900 * _2883))) + (_2897 * _2883);
                                _2904 = (_2920 * (_370 - (_2900 * _2863))) + (_2897 * _2863);
                            }
                            else
                            {
                                _2902 = _2883;
                                _2904 = _2863;
                            }
                            D _2909 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_2902 * 2.0) + 2.0));
                            _2932 = spvNMin(_2909 * (_2902 + 1.0), 1.0);
                            _2933 = spvNClamp(_2909 * (_2904 + _370), 0.0, 1.0);
                            break;
                        }
                        D _2934 = spvNMax(9.9999997473787516355514526367188e-06, _2932);
                        D _2935 = _2878 * _2878;
                        D _2939 = (_2882 * 0.25) * (_2882 + (_2878 * 3.0));
                        D _2946 = _2935 + (-1.0);
                        D _2949 = ((_2933 * _2933) * _2946) + 1.0;
                        D _2950 = _2935 * 0.3183098733425140380859375;
                        D _2955 = (_2876 * 2.0) * _374;
                        D _2960 = 1.0 - _2934;
                        D _2961 = _2960 * _2960;
                        D _2971 = spvNClamp(((spvNMin(dot(vec3(_362), vec3(16.666667938232421875)), 1.0) - _362) * ((_2961 * _2961) * _2960)) + _362, 0.0, 1.0);
                        D _2972 = spvNMax(0.039999999105930328369140625, _405);
                        D _2985 = spvNMax(9.9999999747524270787835121154785e-07, 1.0 - spvNClamp((((_2972 * _2876) + 0.02669160068035125732421875) / (_2876 + 0.4664950072765350341796875)) * exp2(((1.0 / _2972) * _2876) * log2(_2972)), 0.0, 1.0));
                        D _2990 = (((1.0 - _2985) * (1.0 / _2985)) * _362) + 1.0;
                        D _2994 = (((_2950 * _2876) * (1.0 / (_2949 * _2949))) * (_2886 ? ((1.0 / ((_2939 * (1.0 / _2934)) + _2935)) * _2935) : 1.0)) * (0.5 / ((_2878 * ((_374 + _2876) - _2955)) + _2955));
                        D _2996 = spvNClamp(_2876 * 999.99993896484375, 0.0, 1.0);
                        D _2998 = spvNMin(_2859, _2996 * _2996);
                        D _2999 = _2862 * 0.840048015117645263671875;
                        D _3008 = dot(vec3(_362), vec3(0.3333333432674407958984375));
                        D _3016 = 1.0 / ((2.0 / spvNMax(9.9999997473787516355514526367188e-05, 1.0 - sqrt(_3008))) + (-1.0));
                        D _3017 = (-0.0) - _309;
                        D _3018 = (-0.0) - _310;
                        D _3019 = (-0.0) - _311;
                        D _3020 = _370 * 2.0;
                        D _3024 = _223 - (_3020 * _309);
                        D _3025 = _225 - (_3020 * _310);
                        D _3026 = _226 - (_3020 * _311);
                        D _3030 = inversesqrt(dot(vec3(_3024, _3025, _3026), vec3(_3024, _3025, _3026)));
                        D _3031 = _3024 * _3030;
                        D _3032 = _3025 * _3030;
                        D _3033 = _3026 * _3030;
                        D _3037 = (_3031 * _3016) + _1368;
                        D _3038 = (_3032 * _3016) + _1369;
                        D _3039 = (_3033 * _3016) + _1370;
                        D _3043 = inversesqrt(dot(vec3(_3037, _3038, _3039), vec3(_3037, _3038, _3039)));
                        D _3044 = _3037 * _3043;
                        D _3045 = _3038 * _3043;
                        D _3046 = _3039 * _3043;
                        D _3047 = dot(vec3(_3044, _3045, _3046), vec3(_3031, _3032, _3033));
                        D _3059 = (((_3044 * _3047) - _3031) * 2.0) + _3031;
                        D _3060 = (((_3045 * _3047) - _3032) * 2.0) + _3032;
                        D _3061 = (((_3046 * _3047) - _3033) * 2.0) + _3033;
                        D _3065 = inversesqrt(dot(vec3(_3059, _3060, _3061), vec3(_3059, _3060, _3061)));
                        D _3066 = _3059 * _3065;
                        D _3067 = _3060 * _3065;
                        D _3068 = _3061 * _3065;
                        D _3069 = dot(vec3(_3017, _3018, _3019), vec3(_1368, _1369, _1370));
                        D _3077;
                        if (_2866)
                        {
                            D _3074 = sqrt(spvNClamp(_1371 * _2862, 0.0, 1.0));
                            D frontier_phi_106_105_ladder;
                            if (_3074 > spvNMax(9.9999997473787516355514526367188e-06, _3069))
                            {
                                D _3091 = spvNMax((-0.0) - _3074, _3069) + _3074;
                                frontier_phi_106_105_ladder = (_3091 * _3091) * (0.25 / _3074);
                            }
                            else
                            {
                                frontier_phi_106_105_ladder = _3069;
                            }
                            _3077 = frontier_phi_106_105_ladder;
                        }
                        else
                        {
                            _3077 = _3069;
                        }
                        D _3134;
                        D _3135;
                        D _3136;
                        D _3079;
                        D _3080;
                        D _3083;
                        D _3086;
                        for (;;)
                        {
                            _3079 = spvNMax(0.0, _3077);
                            _3080 = dot(vec3(_3017, _3018, _3019), vec3(_3066, _3067, _3068));
                            _3083 = dot(vec3(_3017, _3018, _3019), vec3(_3031, _3032, _3033));
                            _3086 = dot(vec3(_3031, _3032, _3033), vec3(_3066, _3067, _3068));
                            D _3102;
                            D _3104;
                            if (_2886)
                            {
                                D _3097 = sqrt(spvNMax(0.0, 1.0 - (_2882 * _2882)));
                                D _3100 = ((_3080 * 2.0) * _3083) - _3086;
                                if (!(!(_3100 >= _3097)))
                                {
                                    D _3133 = abs(_3083);
                                    _3134 = _3133;
                                    _3135 = _3133;
                                    _3136 = 1.0;
                                    break;
                                }
                                D _3121 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, 1.0 - (_3100 * _3100))) * _2882;
                                _3102 = (_3121 * ((((_3083 * _3083) * 2.0) + (-1.0)) - (_3100 * _3086))) + (_3097 * _3086);
                                _3104 = (_3121 * (_3083 - (_3100 * _3080))) + (_3097 * _3080);
                            }
                            else
                            {
                                _3102 = _3086;
                                _3104 = _3080;
                            }
                            D _3109 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, (_3102 * 2.0) + 2.0));
                            _3134 = abs(_3083);
                            _3135 = spvNMin(_3109 * (_3102 + 1.0), 1.0);
                            _3136 = spvNClamp(_3109 * (_3104 + _3083), 0.0, 1.0);
                            break;
                        }
                        D _3137 = spvNMax(9.9999997473787516355514526367188e-06, _3135);
                        D _3138 = spvNMax(9.9999997473787516355514526367188e-06, _3134);
                        D _3147 = ((_3136 * _3136) * _2946) + 1.0;
                        D _3152 = (_3079 * 2.0) * _3138;
                        D _3157 = 1.0 - _3137;
                        D _3158 = _3157 * _3157;
                        D _3173 = dot(vec3(_1368, _1369, _1370), vec3(_3044, _3045, _3046));
                        D _3177 = dot(vec3(_3031, _3032, _3033), vec3(_3044, _3045, _3046));
                        D _3183 = (_3177 * _3016) + _3173;
                        D _3188 = ((((((_2950 * _3079) * (1.0 / (_3147 * _3147))) * (_2886 ? ((1.0 / ((_2939 * (1.0 / _3137)) + _2935)) * _2935) : 1.0)) * (0.5 / ((_2878 * ((_3138 + _3079) - _3152)) + _3152))) * ((1.0 - _3008) - (((_3158 * _3158) * _3157) * (spvNMin(_3008 * 50.0, 1.0) - _3008)))) * _2862) * ((spvNClamp(_3177, 0.0, 1.0) * spvNClamp(_3173, 0.0, 1.0)) * (1.0 / spvNMax(9.9999997473787516355514526367188e-06, _3183 * _3183)));
                        D _3190 = _3188 + ((((_2999 * _2994) * _2971) * _2998) * _2990);
                        _2817 = ((_1949 * _632) * _2443) * (_3188 + ((((_2999 * _2971) * _2994) * _2998) * _2990));
                        _2819 = ((_1949 * _633) * _2445) * _3190;
                        _2821 = ((_1949 * _634) * _2447) * _3190;
                        break;
                    }
                    else
                    {
                        _2817 = 0.0;
                        _2819 = 0.0;
                        _2821 = 0.0;
                        break;
                    }
                }
                frontier_phi_46_pred = _2819 + _618;
                frontier_phi_46_pred_1 = _2817 + _617;
                frontier_phi_46_pred_2 = _2821 + _619;
                frontier_phi_46_pred_3 = _621;
                frontier_phi_46_pred_4 = _622;
                frontier_phi_46_pred_5 = _620;
            }
            else
            {
                D _879 = _627 - _212;
                D _880 = _628 - _213;
                D _881 = _629 - _214;
                D _882 = dot(vec3(_879, _880, _881), vec3(_879, _880, _881));
                D _886 = (_630 * _630) * _882;
                D _887 = _886 * _886;
                D _888 = _887 * _887;
                D _891 = spvNClamp(1.0 - (_888 * _888), 0.0, 1.0);
                D _892 = _891 * _891;
                D _893 = _892 * _892;
                D _894 = _893 * _893;
                D _1074;
                D _1076;
                D _1078;
                if (_894 > 0.0)
                {
                    D _1066 = dot(vec3(_220, _221, _222), vec3(_309, _310, _311)) * 2.0;
                    D _1070 = _220 - (_1066 * _309);
                    D _1071 = _221 - (_1066 * _310);
                    D _1072 = _222 - (_1066 * _311);
                    D _2509;
                    D _2510;
                    D _2511;
                    D _2512;
                    D _2513;
                    D _2514;
                    D _2515;
                    D _2516;
                    D _2517;
                    D _2518;
                    D _2519;
                    if (_650 == 0.0)
                    {
                        D _1954;
                        D _1955;
                        D _1956;
                        if (_882 > 9.9999997473787516355514526367188e-05)
                        {
                            D _1950 = inversesqrt(_882);
                            _1954 = _1950 * _879;
                            _1955 = _1950 * _880;
                            _1956 = _1950 * _881;
                        }
                        else
                        {
                            _1954 = 0.0;
                            _1955 = 0.0;
                            _1956 = 0.0;
                        }
                        D _1959 = 1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(1.0, _882));
                        _2509 = _1959;
                        _2510 = (_649 * _649) * _1959;
                        _2511 = _1954;
                        _2512 = _1955;
                        _2513 = _1956;
                        _2514 = _1954;
                        _2515 = _1955;
                        _2516 = _1956;
                        _2517 = _1954;
                        _2518 = _1955;
                        _2519 = _1956;
                    }
                    else
                    {
                        D _1382 = _650 * 0.5;
                        D _1383 = _1382 * _636;
                        D _1384 = _1382 * _637;
                        D _1385 = _1382 * _638;
                        D _1386 = _879 - _1383;
                        D _1387 = _880 - _1384;
                        D _1388 = _881 - _1385;
                        D _1389 = _1383 + _879;
                        D _1390 = _1384 + _880;
                        D _1391 = _1385 + _881;
                        D _1399 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_1386, _1387, _1388), vec3(_1386, _1387, _1388))));
                        D _1401 = inversesqrt(spvNMax(9.9999997473787516355514526367188e-06, dot(vec3(_1389, _1390, _1391), vec3(_1389, _1390, _1391))));
                        D _1402 = _1401 * _1399;
                        D _1418 = (1.0 / spvNMax(9.9999997473787516355514526367188e-05, spvNMax(_1402, ((dot(vec3(_1386, _1387, _1388), vec3(_1389, _1390, _1391)) * 0.5) * _1402) + 0.5))) * _1402;
                        D _1420 = (_636 * 2.0) * _1382;
                        D _1422 = (_637 * 2.0) * _1382;
                        D _1424 = (_638 * 2.0) * _1382;
                        D _1425 = dot(vec3(_1420, _1422, _1424), vec3(_1420, _1422, _1424));
                        D _1992;
                        D _1993;
                        D _1994;
                        if (_1425 > 9.9999997473787516355514526367188e-05)
                        {
                            D _1962 = dot(vec3(_1070, _1071, _1072), vec3(_1420, _1422, _1424));
                            D _1978 = spvNClamp((1.0 / (_1425 - (_1962 * _1962))) * dot(vec3(_1386, _1387, _1388), vec3((_1962 * _1070) - _1420, (_1962 * _1071) - _1422, (_1962 * _1072) - _1424)), 0.0, 1.0);
                            D _1982 = (_1978 * _1420) + _1386;
                            D _1983 = (_1978 * _1422) + _1387;
                            D _1984 = (_1978 * _1424) + _1388;
                            D _1988 = inversesqrt(dot(vec3(_1982, _1983, _1984), vec3(_1982, _1983, _1984)));
                            _1992 = _1982 * _1988;
                            _1993 = _1983 * _1988;
                            _1994 = _1984 * _1988;
                        }
                        else
                        {
                            _1992 = _1386;
                            _1993 = _1387;
                            _1994 = _1388;
                        }
                        _2509 = _1418;
                        _2510 = (_649 * _649) * _1418;
                        _2511 = _1399 * _1386;
                        _2512 = _1399 * _1387;
                        _2513 = _1399 * _1388;
                        _2514 = _1401 * _1389;
                        _2515 = _1401 * _1390;
                        _2516 = _1401 * _1391;
                        _2517 = _1992;
                        _2518 = _1993;
                        _2519 = _1994;
                    }
                    D _2529 = _2510 + 1.0;
                    D _2534 = _2517 - _220;
                    D _2535 = _2518 - _221;
                    D _2536 = _2519 - _222;
                    D _2540 = inversesqrt(dot(vec3(_2534, _2535, _2536), vec3(_2534, _2535, _2536)));
                    D _2541 = _2540 * _2534;
                    D _2542 = _2540 * _2535;
                    D _2543 = _2540 * _2536;
                    D _2550 = spvNClamp(dot(vec3(_309, _310, _311), vec3(_2541, _2542, _2543)), 0.0, 1.0);
                    D _2551 = _405 * _405;
                    D _2557 = spvNClamp(((1.0 - _2551) * _649) * sqrt(_2509), 0.0, 1.0);
                    D _2571 = exp2(log2(spvNClamp((((_2557 * 0.25) * (_2557 + (_2551 * 3.0))) * (1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_223, _225, _226), vec3(_2541, _2542, _2543))))) + (_2551 * _2551), 0.0, 1.0)) * 0.25);
                    D _2575 = spvNClamp(dot(vec3(_2511, _2512, _2513), vec3(_2514, _2515, _2516)), 0.0, 1.0);
                    D _2577 = _2571 * _2571;
                    D _2578 = _2577 * _2577;
                    D _2837;
                    if (_2575 < 1.0)
                    {
                        D _2828 = sqrt(spvNClamp((1.0 / (_2575 + 1.0)) * (1.0 - _2575), 0.0, 1.0));
                        _2837 = (1.0 / spvNClamp(((_2828 * 0.25) * (_2828 + (_2577 * 3.0))) + _2578, 0.0, 1.0)) * _2578;
                    }
                    else
                    {
                        _2837 = 1.0;
                    }
                    D _2841 = ((_2550 * _2550) * (_2578 + (-1.0))) + 1.0;
                    D _2847 = (((spvNMax(0.0, (((dot(vec3(_309, _310, _311), vec3(_2514, _2515, _2516)) + dot(vec3(_309, _310, _311), vec3(_2511, _2512, _2513))) * 0.5) + _2510) * (1.0 / (_2529 * _2529))) * 0.3183098733425140380859375) * _2578) * _2837) * (1.0 / (_2841 * _2841));
                    _1074 = _2847 * ((_894 * _632) * _2509);
                    _1076 = _2847 * ((_894 * _633) * _2509);
                    _1078 = _2847 * ((_894 * _634) * _2509);
                }
                else
                {
                    _1074 = 0.0;
                    _1076 = 0.0;
                    _1078 = 0.0;
                }
                frontier_phi_46_pred = _618;
                frontier_phi_46_pred_1 = _617;
                frontier_phi_46_pred_2 = _619;
                frontier_phi_46_pred_3 = _1076 + _621;
                frontier_phi_46_pred_4 = _1078 + _622;
                frontier_phi_46_pred_5 = _1074 + _620;
            }
            _494 = frontier_phi_46_pred;
            _492 = frontier_phi_46_pred_1;
            _496 = frontier_phi_46_pred_2;
            _500 = frontier_phi_46_pred_3;
            _502 = frontier_phi_46_pred_4;
            _498 = frontier_phi_46_pred_5;
            uint _624 = _623 + 1u;
            if (_624 == _484)
            {
                break;
            }
            else
            {
                _617 = _492;
                _618 = _494;
                _619 = _496;
                _620 = _498;
                _621 = _500;
                _622 = _502;
                _623 = _624;
                continue;
            }
        }
        _491 = _492;
        _493 = _494;
        _495 = _496;
        _497 = _498;
        _499 = _500;
        _501 = _502;
    }
    D _503 = spvNClamp(_403, 0.0, 1.0);
    D _507 = spvNClamp(((((1.0 / _421) * (1.0 - _421)) * _362) + 1.0) * (((_421 - _439) * _362) + _439), 0.0, 1.0) * 0.840048015117645263671875;
    D _523 = fma(_214, View._m0[14u].w, fma(_213, View._m0[13u].w, _212 * View._m0[12u].w)) + View._m0[15u].w;
    D _529 = (((fma(_214, View._m0[14u].x, fma(_213, View._m0[13u].x, _212 * View._m0[12u].x)) + View._m0[15u].x) / _523) * 0.5) + 0.5;
    D _530 = 0.5 - (((fma(_214, View._m0[14u].y, fma(_213, View._m0[13u].y, _212 * View._m0[12u].y)) + View._m0[15u].y) / _523) * 0.5);
    D _559 = sqrt(((_210 * _210) + (_209 * _209)) + (_211 * _211));
    D _578 = spvNMax(0.0, ((1.0 / spvNMax(9.9999997473787516355514526367188e-05, dot(vec3(_209, _210, _211), vec3(View._m0[68u].xyz())))) * _559) * View._m0[280u].w);
    D _586;
    D _588;
    D _590;
    D _592;
    D _594;
    D _596;
    if (_559 < _578)
    {
        _586 = 0.0;
        _588 = 0.0;
        _590 = 0.0;
        _592 = 1.0;
        _594 = 1.0;
        _596 = 1.0;
    }
    else
    {
        D _604 = (1.0 / _559) * _578;
        uvec4 _611 = floatBitsToUint(View._m0[220u]);
        uint _612 = _611.y;
        uint _615 = (_612 != 1u) ? 4294967295u : 0u;
        uint _877;
        if (_612 > 1u)
        {
            D _114[4];
            _114[0u] = 0.0;
            _114[1u] = 0.0;
            _114[2u] = 0.0;
            _114[3u] = 0.0;
            uint _956 = 0u;
            bool _962;
            for (;;)
            {
                _962 = _956 < floatBitsToUint(View._m0[220u]).y;
                if (_962)
                {
                    uint _1231 = _956 + 237u;
                    D _1245 = View._m0[_1231].x - View._m0[75u].x;
                    D _1246 = View._m0[_1231].y - View._m0[75u].y;
                    D _1247 = View._m0[_1231].z - View._m0[75u].z;
                    D _1248 = dot(vec3(_1245, _1246, _1247), vec3(_220, _221, _222));
                    D _1255 = dot(vec3(_1245, _1246, _1247), vec3(_1245, _1246, _1247)) - (View._m0[_1231].w * View._m0[_1231].w);
                    D _1257 = (_1248 * _1248) - _1255;
                    D _1524;
                    if ((_1255 < 0.0) && (!(_1257 < 0.0)))
                    {
                        D _1518 = sqrt(_1257);
                        _1524 = spvNMin(abs(_1518 + _1248), abs(_1248 - _1518));
                    }
                    else
                    {
                        _1524 = 0.0;
                    }
                    _114[_956] = _1524;
                }
                uint _957 = _956 + 1u;
                if (_957 == 4u)
                {
                    break;
                }
                else
                {
                    _956 = _957;
                    continue;
                }
            }
            D _1535 = (_247 * 0.99989998340606689453125) * dot(vec4(_114[0u], _114[1u], _114[2u], _114[3u]), vec4(1.0));
            uint frontier_phi_18_56_ladder;
            if (_114[0u] > _1535)
            {
                frontier_phi_18_56_ladder = 0u;
            }
            else
            {
                D _2433 = _114[1u] + _114[0u];
                uint frontier_phi_18_56_ladder_74_ladder;
                if (_2433 > _1535)
                {
                    frontier_phi_18_56_ladder_74_ladder = 1u;
                }
                else
                {
                    D _2815 = _2433 + _114[2u];
                    uint frontier_phi_18_56_ladder_74_ladder_85_ladder;
                    if (_2815 > _1535)
                    {
                        frontier_phi_18_56_ladder_74_ladder_85_ladder = 2u;
                    }
                    else
                    {
                        uint frontier_phi_18_56_ladder_74_ladder_85_ladder_91_ladder;
                        if ((_2815 + _114[3u]) > _1535)
                        {
                            frontier_phi_18_56_ladder_74_ladder_85_ladder_91_ladder = 3u;
                        }
                        else
                        {
                            frontier_phi_18_56_ladder_74_ladder_85_ladder_91_ladder = _615;
                        }
                        frontier_phi_18_56_ladder_74_ladder_85_ladder = frontier_phi_18_56_ladder_74_ladder_85_ladder_91_ladder;
                    }
                    frontier_phi_18_56_ladder_74_ladder = frontier_phi_18_56_ladder_74_ladder_85_ladder;
                }
                frontier_phi_18_56_ladder = frontier_phi_18_56_ladder_74_ladder;
            }
            _877 = frontier_phi_18_56_ladder;
        }
        else
        {
            _877 = _615;
        }
        D frontier_phi_9_18_ladder;
        D frontier_phi_9_18_ladder_1;
        D frontier_phi_9_18_ladder_2;
        D frontier_phi_9_18_ladder_3;
        D frontier_phi_9_18_ladder_4;
        D frontier_phi_9_18_ladder_5;
        if (_877 == 4294967295u)
        {
            frontier_phi_9_18_ladder = 1.0;
            frontier_phi_9_18_ladder_1 = 1.0;
            frontier_phi_9_18_ladder_2 = 1.0;
            frontier_phi_9_18_ladder_3 = 0.0;
            frontier_phi_9_18_ladder_4 = 0.0;
            frontier_phi_9_18_ladder_5 = 0.0;
        }
        else
        {
            uint _963 = _877 + 221u;
            D _971 = spvNMin(View._m0[_963].w, 0.9900000095367431640625);
            uint _973 = _877 + 225u;
            uint _980 = _877 + 229u;
            uint _987 = _877 + 233u;
            uint _992 = _877 + 241u;
            D _1292;
            D _1293;
            D _1294;
            if (TranslucentBasePass_2._m0[146u].x > 0.0)
            {
                vec4 _1281 = textureLod(sampler2D(TranslucentBasePass_Shared_Fog_FarIntegratedScatteringTexture, View_SharedBilinearClampedSampler), vec2(spvNMin(spvNMax(View._m0[278u].x * _529, View._m0[279u].x), View._m0[280u].x), spvNMin(spvNMax(View._m0[278u].y * _530, View._m0[279u].y), View._m0[280u].y)), 0.0);
                _1292 = View._m0[164u].z * _1281.x;
                _1293 = View._m0[164u].z * _1281.y;
                _1294 = View._m0[164u].z * _1281.z;
            }
            else
            {
                _1292 = 0.0;
                _1293 = 0.0;
                _1294 = 0.0;
            }
            D _1298 = dot(vec3((-0.0) - View._m0[218u].x, (-0.0) - View._m0[218u].y, (-0.0) - View._m0[218u].z), vec3(_223, _225, _226));
            D _1312 = (((_1298 * _1298) + 1.0) * 0.0397887341678142547607421875) * exp2(log2(spvNMax(0.0, _1298 + 1.25)) * (-1.5));
            D _1537;
            if (View._m0[_973].x == 0.0)
            {
                _1537 = 0.0;
            }
            else
            {
                D _1585 = (((_604 * _211) - View._m0[_973].z) + View._m0[75u].z) * View._m0[_973].y;
                D _1586 = ((1.0 - _604) * _211) * View._m0[_973].y;
                D _1591 = exp2((-0.0) - _1585);
                D frontier_phi_57_58_ladder;
                if (abs(_1586) > 0.00999999977648258209228515625)
                {
                    frontier_phi_57_58_ladder = ((_1591 - exp2(((-0.0) - _1586) - _1585)) * View._m0[_973].x) * (1.0 / _1586);
                }
                else
                {
                    frontier_phi_57_58_ladder = (View._m0[_973].x * 0.693147182464599609375) * _1591;
                }
                _1537 = frontier_phi_57_58_ladder;
            }
            D _1541 = _1537 * (1.0 - _971);
            D _1545 = (1.0 - View._m0[_980].x) * View._m0[_987].x;
            D _1546 = (1.0 - View._m0[_980].y) * View._m0[_987].x;
            D _1547 = (1.0 - View._m0[_980].z) * View._m0[_987].x;
            D _1548 = (-0.0) - (_559 - _578);
            D _1576 = 1.0 - spvNClamp(exp2(_1541 * _1548), 0.0, 1.0);
            frontier_phi_9_18_ladder = spvNClamp(exp2((_1541 + _1547) * _1548), 0.0, 1.0);
            frontier_phi_9_18_ladder_1 = spvNClamp(exp2((_1541 + _1546) * _1548), 0.0, 1.0);
            frontier_phi_9_18_ladder_2 = spvNClamp(exp2((_1541 + _1545) * _1548), 0.0, 1.0);
            frontier_phi_9_18_ladder_3 = (((_971 * View._m0[_963].z) * (((View._m0[219u].z * View._m0[_992].x) * _1312) + _1294)) * spvNClamp(exp2(_1547 * _1548), 0.0, 1.0)) * _1576;
            frontier_phi_9_18_ladder_4 = (((_971 * View._m0[_963].y) * (((View._m0[219u].y * View._m0[_992].x) * _1312) + _1293)) * spvNClamp(exp2(_1546 * _1548), 0.0, 1.0)) * _1576;
            frontier_phi_9_18_ladder_5 = (((_971 * View._m0[_963].x) * (((View._m0[219u].x * View._m0[_992].x) * _1312) + _1292)) * spvNClamp(exp2(_1545 * _1548), 0.0, 1.0)) * _1576;
        }
        _586 = frontier_phi_9_18_ladder_5;
        _588 = frontier_phi_9_18_ladder_4;
        _590 = frontier_phi_9_18_ladder_3;
        _592 = frontier_phi_9_18_ladder_2;
        _594 = frontier_phi_9_18_ladder_1;
        _596 = frontier_phi_9_18_ladder;
    }
    D _823;
    D _824;
    D _825;
    D _826;
    D _827;
    D _828;
    if (TranslucentBasePass_2._m0[148u].x > 0.0)
    {
        D _797 = spvNMin(spvNMax(View._m0[278u].x * _529, View._m0[279u].x), View._m0[280u].x);
        D _798 = spvNMin(spvNMax(View._m0[278u].y * _530, View._m0[279u].y), View._m0[280u].y);
        D _799 = spvNMin(spvNMax((View._m0[275u].z * spvNMax(0.0, spvNMin(View._m0[276u].z * log2((View._m0[276u].x * _523) + View._m0[276u].y), View._m0[274u].z + (-1.0)) + 0.5)) * View._m0[278u].z, View._m0[279u].z), View._m0[280u].z);
        vec4 _804 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeATexture, View_SharedBilinearClampedSampler), vec3(_797, _798, _799), 0.0);
        vec4 _811 = textureLod(sampler3D(TranslucentBasePass_Shared_Fog_IntegratedScatteringVolumeBTexture, View_SharedBilinearClampedSampler), vec3(_797, _798, _799), 0.0);
        _823 = View._m0[164u].z * _804.x;
        _824 = View._m0[164u].z * _804.y;
        _825 = View._m0[164u].z * _804.z;
        _826 = _811.x;
        _827 = _811.y;
        _828 = _811.z;
    }
    else
    {
        _823 = 0.0;
        _824 = 0.0;
        _825 = 0.0;
        _826 = 1.0;
        _827 = 1.0;
        _828 = 1.0;
    }
    D _835 = 1.0 - ((1.0 - spvNClamp((((_352 * 0.02199999988079071044921875) + (-0.039999999105930328369140625)) + _396) + (((1.03999996185302734375 - (_352 * 0.572000026702880859375)) - _396) * 0.159951984882354736328125), 0.0, 1.0)) * _403);
    SV_Target.x = View._m0[164u].y * ((((_826 * _586) + _823) * _835) + ((_592 * ((_503 * _491) + (_507 * _497))) * _826));
    SV_Target.y = ((((_827 * _588) + _824) * _835) + ((_594 * ((_503 * _493) + (_507 * _499))) * _827)) * View._m0[164u].y;
    SV_Target.z = ((((_828 * _590) + _825) * _835) + ((_596 * ((_503 * _495) + (_507 * _501))) * _828)) * View._m0[164u].y;
    SV_Target.w = dot(vec3(_835), vec3(0.2125999927520751953125, 0.715200006961822509765625, 0.072200000286102294921875));
    SV_Target_1.x = _835;
    SV_Target_1.y = _835;
    SV_Target_1.z = _835;
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
} // namespace S_rystal_Early_Reverse_Character