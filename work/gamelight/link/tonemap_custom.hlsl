// FINAL FANTASY VII REBIRTH's SDR tonemapping (from its FTonemapPS): the exposed scene colour and glare, natural
// vignetting, PQ encoding (1.0 = 100 nits), then the area colour LUT (BT.709 PQ -> ACES BT.2020 PQ 1000 nits, graded,
// e.g. the menu's 030-SLUM7_day_HDR) and the output LUT (ACES BT.2020 PQ -> sRGB), both 32^3 and looked up like the
// game (31/32 scale + half texel, trilinear). The LUTs are 1024 x 32 strips: blue picks the 32-texel tile.
float Scale = View.OneOverPreExposure * Exposure;
float3 C = (SceneColor.rgb + Bloom.rgb * BloomScale) * Scale;
float2 Ndc = UV * 2.0 - 1.0;
float2 Tn = Ndc * float2(1.0 / View.ViewToClip[0][0], 1.0 / View.ViewToClip[1][1]);
float Cos2 = 1.0 / (dot(Tn, Tn) + 1.0);
C *= 1.0 + (Cos2 * Cos2 - 1.0) * VignetteIntensity;
float3 X = pow(saturate(C * 0.01), 0.1593017578125);
float3 E = saturate(pow(max(0.0, (0.8359375 + 18.8515625 * X) / (1.0 + 18.6875 * X)), 78.84375));
float3 P = E * 0.96875 + 0.015625;
float B = P.z * 32.0 - 0.5;
float B0 = clamp(floor(B), 0.0, 31.0);
float B1 = min(B0 + 1.0, 31.0);
float FB = saturate(B - B0);
float3 G = lerp(LUTA.SampleLevel(LUTASampler, float2((P.x + B0) / 32.0, P.y), 0).rgb, LUTA.SampleLevel(LUTASampler, float2((P.x + B1) / 32.0, P.y), 0).rgb, FB);
P = G * 0.96875 + 0.015625;
B = P.z * 32.0 - 0.5;
B0 = clamp(floor(B), 0.0, 31.0);
B1 = min(B0 + 1.0, 31.0);
FB = saturate(B - B0);
return saturate(lerp(LUTB.SampleLevel(LUTBSampler, float2((P.x + B0) / 32.0, P.y), 0).rgb, LUTB.SampleLevel(LUTBSampler, float2((P.x + B1) / 32.0, P.y), 0).rgb, FB));
