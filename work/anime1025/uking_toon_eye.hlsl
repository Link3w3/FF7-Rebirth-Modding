// UKing Toon Eye: a Rebirth eye drawn with M_UKing_Mat_Toon's light. The eye's textures go in as Rebirth's eye
// materials have them: Color (the sclera), IrisColor, GazeNormal, IrisEmissive (the iris's own glow: Sephiroth's mako).
// Rebirth's eye mapping (RMI_Surface_Eye_*): UV0 covers the eyeball; the iris is the disc of radius 0.25 around
// (0.5, 0.5), seen through the cornea: the view ray bends at the cornea (RefractionIndex) and the iris is read where it
// lands, deepest at the centre. GazeNormal gives the eye's axis.
// The light is M_UKing_Mat_Toon's (ukToonLight, BotW's toon step) from MPC_UKing: the albedo remap, a hard N.L step at
// ToonParams.x with sharpness ToonParams.y, ambient + sun. EyeShadowLift keeps some sun on the eye in the toon shadow;
// the top of the eyeball, under the lid, is shaded; two anime catchlights sit in the cornea.
float3 T = normalize(Parameters.TangentToWorld[0]);
float3 B = normalize(Parameters.TangentToWorld[1]);
float3 N = normalize(Parameters.TangentToWorld[2]);
float  s = dot(cross(N, T), B) < 0.0 ? -1.0 : 1.0;
float3 V = Parameters.CameraVector;

// the eye's axis and its basis, as Rebirth builds them
float2 gxy = Texture2DSample(Gaze, GazeSampler, UV).xy * 2.0 - 1.0;
float3 g = normalize(float3(gxy, sqrt(saturate(1.0 - dot(gxy, gxy)))));
float3 G = g.x * T + g.y * B + g.z * N;
float3 Bg = normalize(cross(G, T)) * s;
float3 Tg = normalize(cross(Bg, G)) * s;

// iris space: |p| = 1 at the iris edge; the sclera takes over from 0.9 to 1.1
float2 p = UV * 4.0 - 2.0;
float  r2 = dot(p, p);
float  r = sqrt(r2);
float  t0 = saturate((r - 0.9) * 5.0);
float  scleraW = t0 * t0 * (3.0 - 2.0 * t0);

// the cornea's bulge, the ray through it, and where it meets the iris
float3 nc = normalize(float3(0.9115 * p, 1.0));
float3 nw = nc.x * Tg + nc.y * Bg + nc.z * G;
float  cosI = dot(nw, V);
float  eta = 1.0 / max(RefractionIndex, 1.0);
float  k = 1.0 - eta * eta * (1.0 - cosI * cosI);
float3 tr = normalize(eta * (cosI * nw - V) - sqrt(max(k, 0.0)) * nw);
float  depth = max(0.3735 - r2 * 0.2795, 0.0) * 0.4077 * IrisDepth;
float  tz = dot(tr, G);
tz = abs(tz) > 0.0001 ? tz : -0.0001;
float2 uvi = UV - float2(dot(tr, Tg), dot(tr, Bg)) / tz * depth;
float2 q = uvi * 4.0 - 2.0;
float  qr = length(q);
float2 irisUV = 0.5 + 0.5 * saturate(qr) * q / max(qr, 0.0001);

float3 sclera = Texture2DSample(Sclera, ScleraSampler, UV).rgb;
float3 iris = Texture2DSample(Iris, IrisSampler, irisUV).rgb;
iris *= 1.0 - IrisRimDarken * smoothstep(0.8, 1.0, qr);
float3 col = lerp(iris, sclera, scleraW);

// the top of the eyeball, under the lid, a shade darker
float  up = dot(N, float3(0.0, 0.0, 1.0));
float  lid = smoothstep(LidShadow - LidSoftness, LidShadow + LidSoftness, up);
col *= 1.0 - LidShadowStrength * lid;

// M_UKing_Mat_Toon's light (ukToonLight, behave 0): SunDirection is the way the light travels
float3 a = saturate(col * 1.0732098 - float3(0.000528556, 0.000528556, 0.000528556)) * 0.9317843
           + float3(0.0004925, 0.0004925, 0.0004925);
float  ndl = -dot(SunDirection, N);
float  stepv = saturate((saturate(ndl) - ToonParams.x) * ToonParams.y);
stepv = lerp(saturate(EyeShadowLift), 1.0, stepv);
float3 lit = a * (AmbientColor + SunColor * stepv);

// the iris's own glow (Rebirth's emissive eyes): the IrisEmissive texture through the cornea, as the iris
float3 glow = Texture2DSample(IrisGlow, IrisGlowSampler, irisUV).rgb * GlowColor * GlowIntensity * (1.0 - scleraW);

// two catchlights in the cornea: up and to the side of the camera, and a small one opposite
float3 upS = float3(0.0, 0.0, 1.0) - V * V.z;
upS = dot(upS, upS) > 0.000001 ? normalize(upS) : float3(1.0, 0.0, 0.0);
float3 rightS = cross(upS, V);
float3 R = reflect(-V, nw);
float  h1 = smoothstep(1.0 - HighlightSize, 1.0 - HighlightSize * 0.5, dot(R, normalize(V + HighlightX * rightS + HighlightY * upS)));
float  h2 = smoothstep(1.0 - HighlightSize * 0.3, 1.0 - HighlightSize * 0.15, dot(R, normalize(V - 0.7 * HighlightX * rightS - 0.7 * HighlightY * upS)));
float3 shine = (h1 + 0.6 * h2) * HighlightIntensity * (1.0 - scleraW) * (AmbientColor + SunColor);

return lit + glow + shine;
