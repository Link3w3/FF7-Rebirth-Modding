// AnimeShaderEye (KadeMats): Rebirth's eye mapping (RMI_Surface_Eye_Migration) shaded with AnimeShader's toon tones.
// UV0 covers the eyeball; the iris is the disc of radius 0.25 around (0.5, 0.5), seen through the cornea: the view ray
// bends at the cornea (RefractionIndex) and the iris is read where it lands, deepest at the centre, as Rebirth's eye
// shader does. Its GazeNormal map gives the eye's axis. Use with Rebirth's eye textures: Color (sclera), IrisColor,
// GazeNormal.
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

// AnimeShader's toon tones: the top of the eye, under the lid, in its shadow tone (tinted), the rest in its mid tone;
// as in AnimeShader the colour is multiplied by its toned self
float  up = dot(normalize(Parameters.WorldNormal), float3(0.0, 0.0, 1.0));
float  lid = smoothstep(LidShadow - LidSoftness, LidShadow + LidSoftness, up);
float3 band = lerp(MidIntensity.xxx, ShadowIntensity * ShadowTint, lid);
float3 toon = col * saturate(col * band);

// two highlights in the cornea: a light up and to the side of the camera, and a small one opposite
float3 upS = float3(0.0, 0.0, 1.0) - V * V.z;
upS = dot(upS, upS) > 0.000001 ? normalize(upS) : float3(1.0, 0.0, 0.0);
float3 rightS = cross(upS, V);
float3 R = reflect(-V, nw);
float  h1 = smoothstep(1.0 - HighlightSize, 1.0 - HighlightSize * 0.5, dot(R, normalize(V + HighlightX * rightS + HighlightY * upS)));
float  h2 = smoothstep(1.0 - HighlightSize * 0.3, 1.0 - HighlightSize * 0.15, dot(R, normalize(V - 0.7 * HighlightX * rightS - 0.7 * HighlightY * upS)));
return toon + (h1 + 0.6 * h2) * HighlightIntensity * (1.0 - scleraW);
