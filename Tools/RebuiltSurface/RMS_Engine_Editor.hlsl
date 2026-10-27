// RM_Surface rebuilt: what the game's base pass does with the material's values, for the editor's pins and the Rebirth
// preview bridges (the same arithmetic as the checked base pass): the world normal, the roughness widened by the normal's
// screen-space curvature, emissive light through the dielectric specular layer (the Standard model), the reflectance as
// the engine's Specular (F0 = 0.08 x Specular), and the eye's inner normal and radial direction in world space.
#if PIXELSHADER
float3x3 T2W = Parameters.TangentToWorld;
float3 m = normalize(RMS_N);
float3 raw = mul(m, T2W);
float3 Nw = raw * rsqrt(dot(raw, raw));
float3 dx = ddx_fine(Nw);
float3 dy = ddy_fine(Nw);
float r = saturate(RMS_R);
FilteredRoughness = sqrt(saturate(min((dot(dy, dy) + dot(dx, dx)) * 0.15915493667125701904296875, 0.180000007152557373046875) + r * r));
float3 e = max(RMS_E, float3(0.0, 0.0, 0.0));
if (abs(RMS_SM - 1.0) < 0.5)
{
    float NoV = saturate(dot(Nw, Parameters.CameraVector));
    float a = 1.0 - FilteredRoughness;
    float a004 = (min(a * a, exp2(NoV * -9.27999973297119140625)) * a + (0.0425000004470348358154296875 - FilteredRoughness * 0.0274999998509883880615234375)) * 1.03999996185302734375;
    float t = 1.0 - saturate(((FilteredRoughness * 0.02199999988079071044921875 + -0.039999999105930328369140625) + a004) + ((1.03999996185302734375 - FilteredRoughness * 0.572000026702880859375) - a004) * 0.0400000028312206268310546875);
    float k = (t * t) * exp2(max(0.001000000047497451305389404296875, 0.300000011920928955078125 / max(0.0333333350718021392822265625, NoV)) * -0.0291463173925876617431640625);
    e = e * (k - k * saturate(RMS_M));
}
EmissiveOut = e;
SpecularOut = saturate(RMS_F0 / 0.08);
AOOut = (abs(RMS_SM - 9.0) < 0.5) ? 1.0 : RMS_AO;
float3 wm = normalize(RMS_W);
float3 wr = mul(wm, T2W);
InnerNormalWS = wr * rsqrt(dot(wr, wr));
RadialDirectionWS = RMS_C.xyz * 2.0 - 1.0;
return Nw;
#else
FilteredRoughness = saturate(RMS_R);
EmissiveOut = RMS_E;
SpecularOut = 0.5;
AOOut = RMS_AO;
InnerNormalWS = float3(0.0, 0.0, 1.0);
RadialDirectionWS = float3(0.0, 0.0, 1.0);
return float3(0.0, 0.0, 1.0);
#endif
