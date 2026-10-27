// UKing Toon Lite: what M_UKing_Mat_Toon draws with its default options (an instance setting only Coverage, _a0 and
// _n0, as Anime Sephiroth's do): _a0 at UV0 is the albedo; _n0 at UV0 the normal map (BotW's decode: xy * 2.007874 -
// 1.007874, z rebuilt) on the mesh's tangent basis; BotW's toon light (ukToonLight, behave 0) from MPC_UKing: the
// albedo remap, a hard N.L step at ToonParams.x with sharpness ToonParams.y, ambient + sun. The same picture without the
// interpreter of every BotW option that M_UKing_Mat_Toon runs for each pixel in every pass (seconds a frame in the game).
float3 albedo = Texture2DSample(A0, A0Sampler, UV).rgb;
float2 nxy = Texture2DSample(N0, N0Sampler, UV).xy * 2.007874 - 1.007874;
float3 n = float3(nxy, sqrt(1.0 - saturate(dot(nxy, nxy))));
float3 N = normalize(Parameters.TangentToWorld[0] * n.x + Parameters.TangentToWorld[1] * n.y + Parameters.TangentToWorld[2] * n.z);
float3 a = saturate(albedo * 1.0732098 - float3(0.000528556, 0.000528556, 0.000528556)) * 0.9317843
           + float3(0.0004925, 0.0004925, 0.0004925);
float  ndl = -dot(SunDirection, N);
float  stepv = saturate((saturate(ndl) - ToonParams.x) * ToonParams.y);
return a * (AmbientColor + SunColor * stepv);
