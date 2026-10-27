#line 245 "RMS_Surface.ush"

RMS_Lib L;
RMS_Env Env;


float3 BaseColor = float3(0.0, 0.0, 0.0);
RMS_Metallic = 0.0;
RMS_Specular = 0.0;
RMS_Roughness = 0.5;
RMS_AO = 1.0;
RMS_Normal = float3(0.0, 0.0, 1.0);
RMS_Emissive = float3(0.0, 0.0, 0.0);
RMS_OpacityMask = 1.0;
RMS_Opacity = 1.0;
RMS_ShadingModel = 1.0;
RMS_ModelParam = 0.66666662693023681640625;
RMS_Reflectance = 0.0400000028312206268310546875;
RMS_Custom = float4(0.0, 0.0, 0.0, 0.0);
RMS_WetLayer = float2(0.0, 0.0);
RMS_ColoredOpacity = float3(0.0, 0.0, 0.0);
RMS_Muddiness = float3(0.0, 0.0, 0.0);
RMS_TransparencyLog2 = 0.0;
RMS_TransmittanceLog2 = float3(0.0, 0.0, 0.0);
RMS_Thickness = 1.0;
RMS_PhaseG = 0.0;
RMS_MediumPath = 0.0;
RMS_Foam = 0.0;
bool HasWetNormal = false;
float3 WetNormal = float3(0.0, 0.0, 1.0);






bool Flowing = S_Flow > 0.5;
float2 FlowA0 = UV0;
float2 FlowB0 = UV0;
float2 FlowA2 = UV2;
float2 FlowB2 = UV2;
D FlowW0 = 0.0;
D FlowW2 = 0.0;
if (Flowing)
{
    float2 dir = (S_FlowDirection > 0.5) ? UV3 : float2(0.0, 0.0);
    D ph = 0.0;
    if (S_WideFlowPhase > 0.5)
    {
        ph = Texture2DSample(T_WideFlowPhase, T_WideFlowPhaseSampler, UV1).x;
    }
    D dv = 1.0;
    if (S_WideFlowDirectivity > 0.5)
    {
        dv = Texture2DSample(T_WideFlowDirectivity, T_WideFlowDirectivitySampler, UV1).x;
    }
    D tm = (S_AnimateTime > 0.5) ? V_AnimateTimeContext.z : 0.0;
    L.FlowUV(UV0, dir, ph, dv, tm, V_GenericVector0Context, FlowA0, FlowB0, FlowW0);
    L.FlowUV(UV2, dir, ph, dv, tm, V_GenericVector1Context, FlowA2, FlowB2, FlowW2);
}


if (S_Color > 0.5)
{
    BaseColor = Texture2DSample(T_Color, T_ColorSampler, UV0).xyz();
}
if (S_Metallic > 0.5)
{
    RMS_Metallic = Texture2DSample(T_Metallic, T_MetallicSampler, UV0).x;
}
if (S_Normal > 0.5)
{
    if (Flowing && S_FlowNormal > 0.5)
    {
        float3 a = L.NormalXY(Texture2DSample(T_Normal, T_NormalSampler, FlowA0));
        float3 b = L.NormalXY(Texture2DSample(T_Normal, T_NormalSampler, FlowB0));
        RMS_Normal = normalize(lerp(a, b, FlowW0));
    }
    else
    {
        RMS_Normal = L.NormalXY(Texture2DSample(T_Normal, T_NormalSampler, UV0));
    }
}

if (S_PositiveTransitionNormal > 0.5)
{
    float3 w = L.NormalXY(Texture2DSample(T_PositiveTransitionNormal, T_PositiveTransitionNormalSampler, UV0));
    RMS_Normal = L.ArcBlend(RMS_Normal, w, saturate(RMS_VertexExpression.x));
}
if (S_Roughness > 0.5)
{
    if (Flowing && S_FlowRoughness > 0.5)
    {
        
        D a = Texture2DSample(T_Roughness, T_RoughnessSampler, FlowA0).x;
        D b = Texture2DSample(T_Roughness, T_RoughnessSampler, FlowB0).x;
        D a2 = a * a;
        RMS_Roughness = sqrt(saturate((b * b - a2) * FlowW0 + a2));
    }
    else
    {
        RMS_Roughness = Texture2DSample(T_Roughness, T_RoughnessSampler, UV0).x;
    }
}
if (S_Occlusion > 0.5)
{
    RMS_AO = Texture2DSample(T_Occlusion, T_OcclusionSampler, UV0).x;
}
if (S_Opacity > 0.5)
{
    RMS_Opacity = Texture2DSample(T_Opacity, T_OpacitySampler, UV0).x;
}

D Foam = 0.0;
if (S_Foam > 0.5)
{
    if (Flowing && S_FlowFoam > 0.5)
    {
        D a = Texture2DSample(T_Foam, T_FoamSampler, FlowA0).x;
        D b = Texture2DSample(T_Foam, T_FoamSampler, FlowB0).x;
        Foam = saturate((b - a) * FlowW0 + a);
    }
    else
    {
        Foam = saturate(Texture2DSample(T_Foam, T_FoamSampler, UV0).x);
    }
}







if (S_Muddiness > 0.5)
{
    RMS_Muddiness = Texture2DSample(T_Muddiness, T_MuddinessSampler, UV0).xyz();
}
if (S_Transparency > 0.5)
{
    D c = 1.0;
    if (S_TransparencyCoefficient > 0.5)
    {
        c = Texture2DSample(T_TransparencyCoefficient, T_TransparencyCoefficientSampler, UV0).x;
    }
    RMS_TransparencyLog2 = log2(saturate(Texture2DSample(T_Transparency, T_TransparencySampler, UV0).x)) * (1.0 / max(9.9999999747524270787835121154785e-07, c * 100.0));
}
if (S_Transmittance > 0.5)
{
    D c = 1.0;
    if (S_TransmittanceCoefficient > 0.5)
    {
        c = Texture2DSample(T_TransmittanceCoefficient, T_TransmittanceCoefficientSampler, UV0).x;
    }
    D k = 1.0 / max(9.9999999747524270787835121154785e-07, c * 100.0);
    float3 t = saturate(Texture2DSample(T_Transmittance, T_TransmittanceSampler, UV0).xyz());
    RMS_TransmittanceLog2 = float3(log2(t.x) * k, log2(t.y) * k, log2(t.z) * k);
}
if (S_Thinness > 0.5)
{
    RMS_Thickness = Texture2DSample(T_Thinness, T_ThinnessSampler, UV0).x;
}
if (S_Thickness > 0.5)
{
    RMS_Thickness = Texture2DSample(T_Thickness, T_ThicknessSampler, UV1).x;
}






float3 EyeGlow = float3(0.0, 0.0, 0.0);
bool EyeInner = false;
D EyeAO = 1.0;
float3 EyeInnerNormal = float3(0.0, 0.0, 1.0);
D EyeScl = 0.0;
D EyeCv = 0.0;
float3 EyeG = float3(0.0, 0.0, 1.0);
float2 EyePi = float2(0.0, 0.0);
D EyeR2 = 0.0;
if (S_Eye > 0.5 || S_HologramEye > 0.5)
{
    float3x3 T2W = Parameters.TangentToWorld;
    float3 V = Parameters.CameraVector;
    D w = 1.0;
    {
        
        float3 c = cross(T2W[2], T2W[0]);
        w = (dot(c, T2W[1]) < 0.0) ? -1.0 : 1.0;
    }
    float3 gz = float3(0.0, 0.0, 1.0);
    if (S_GazeNormal > 0.5)
    {
        gz = L.NormalXY(Texture2DSample(T_GazeNormal, T_GazeNormalSampler, UV0));
    }
    float3 G = mul(gz, T2W);
    float3 F1 = normalize(cross(G, T2W[0])) * w;
    float3 F2 = normalize(cross(F1, G)) * w;
    float2 p = float2(UV0.x * 4.0 + -2.0, UV0.y * 4.0 + -2.0);
    D r = sqrt(p.y * p.y + p.x * p.x);
    D sc = saturate((r + -0.89999997615814208984375) * 4.99999904632568359375);
    D scl = (sc * sc) * (3.0 - sc * 2.0);
    D pp = dot(p, p);
    float2 d = p * rsqrt(pp);
    float3 nc = normalize(float3((r * 0.911536872386932373046875) * d.x, (r * -0.911536872386932373046875) * -d.y, d.x * d.x - d.y * -d.y));
    float3 Nc = mul(nc, float3x3(F2, F1, G));
    D cv = dot(Nc, V);
    D k2 = sqrt(max(0.0, 1.0 - (1.0 - cv * cv) * 0.4504301249980926513671875));
    float3 Rf = normalize((Nc * cv - V) * 0.6711409091949462890625 - Nc * k2);
    D gR = dot(G, Rf);
    D depth = max(0.0, 0.37349998950958251953125 - pp * 0.27950000762939453125) * 0.4076640605926513671875;
    float2 uvI = float2(UV0.x - (dot(F2, Rf) / gR) * depth, UV0.y - (dot(F1, Rf) / gR) * depth);
    float2 p2 = float2(uvI.x * 4.0 + -2.0, uvI.y * 4.0 + -2.0);
    D r2 = sqrt(p2.y * p2.y + p2.x * p2.x);
    D rc = saturate(saturate(r2));
    D q2 = rsqrt(dot(p2, p2));
    float2 pi = float2((rc * p2.x) * q2, (p2.y * rc) * q2);
    EyeScl = scl;
    EyeCv = cv;
    EyeG = G;
    EyePi = pi;
    EyeR2 = r2;
    if (S_Eye > 0.5)
    {
    float2 irisUV = (S_EyeMigration > 0.5) ? float2(pi.x * 0.5 + 0.5, pi.y * 0.5 + 0.5) : float2(pi.x * 0.25 + 0.5, pi.y * 0.25 + 0.5);
    float2 irisUVn = float2(pi.x * 0.5 + 0.5, pi.y * 0.5 + 0.5);
    float3 iris = float3(0.0, 0.0, 0.0);
    if (S_IrisColor > 0.5)
    {
        iris = Texture2DSample(T_IrisColor, T_IrisColorSampler, irisUV).xyz();
    }
    float3 nI = float3(0.0, 0.0, 1.0);
    if (S_IrisNormal > 0.5)
    {
        nI = L.NormalXY(Texture2DSample(T_IrisNormal, T_IrisNormalSampler, irisUVn));
    }
    D io = 1.0;
    if (S_IrisOcclusion > 0.5)
    {
        io = Texture2DSample(T_IrisOcclusion, T_IrisOcclusionSampler, irisUVn).x;
    }
    if (S_IrisEmissive > 0.5)
    {
        float3 g = Texture2DSample(T_IrisEmissive, T_IrisEmissiveSampler, irisUVn).xyz();
        EyeGlow = g - g * scl;
    }
    float3 rad = normalize(F1 * p2.y + F2 * p2.x);
    float3 NIw = mul(nI, float3x3(F2, F1, G));
    float3 perp = normalize(cross(G, rad));
    D c0 = (sign(RMS_Noise.x * 2.0 + -1.0) * 0.14285714924335479736328125) * (1.0 - sqrt(1.0 - abs(RMS_Noise.x * 2.0 + -1.0))) + dot(NIw, rad);
    D c1 = (sign(RMS_Noise.y * 2.0 + -1.0) * 0.14285714924335479736328125) * (1.0 - sqrt(1.0 - abs(RMS_Noise.y * 2.0 + -1.0))) + dot(NIw, perp);
    
    float3 Nm = mul(RMS_Normal, T2W);
    RMS_Normal = mul(T2W, normalize(lerp(Nc, Nm, scl)));
    float3 Ns = G;
    if (S_ScleraNormal > 0.5)
    {
        Ns = mul(L.NormalXY(Texture2DSample(T_ScrelaNormal, T_ScrelaNormalSampler, UV0)), T2W);
    }
    EyeInner = true;
    EyeInnerNormal = mul(T2W, normalize(lerp(G, Ns, scl)));
    BaseColor = lerp(iris, BaseColor, scl);
    RMS_ShadingModel = 9.0;
    RMS_ModelParam = 0.645419657230377197265625;
    RMS_Metallic = scl;
    RMS_Specular = io;
    RMS_Roughness = 0.07999999821186065673828125;
    EyeAO = r2 * 0.5;
    uint qy = uint(clamp(int(abs(c1 * 7.0) + 0.5), 0, 7));
    uint qx = uint(clamp(int(abs(c0 * 7.0) + 0.5), 0, 7));
    uint sy = uint(c1 > 0.0) - uint(c1 < 0.0);
    uint sx = uint(c0 > 0.0) - uint(c0 < 0.0);
    RMS_Custom = float4(saturate(rad * 0.5 + 0.5), D((((qy << 4) * sy) + 128u) | ((qx * sx) + 8u)) * 0.0039215688593685626983642578125);
    }
}



if (S_Gradient > 0.5)
{
    D phase = 0.0;
    if (S_GradientPhase > 0.5)
    {
        phase = saturate(Texture2DSample(T_GradientPhase, T_GradientPhaseSampler, UV0).x) * 0.99609375;
    }
    if (S_AnimateTime > 0.5)
    {
        phase = phase + V_AnimateTimeContext.x;
    }
    D tri = saturate(abs(frac(phase) * 2.0 + -1.0));
    D g = (tri * tri) * (3.0 - tri * 2.0);
    if (S_GradientNormal > 0.5)
    {
        RMS_Normal = normalize(lerp(RMS_Normal, L.NormalXY(Texture2DSample(T_GradientNormal, T_GradientNormalSampler, UV0)), g));
    }
    if (S_GradientRoughness > 0.5)
    {
        D rg = Texture2DSample(T_GradientRoughness, T_GradientRoughnessSampler, UV0).x;
        RMS_Roughness = sqrt(saturate(lerp(RMS_Roughness * RMS_Roughness, rg * rg, g)));
    }
    if (S_GradientOcclusion > 0.5)
    {
        RMS_AO = saturate(lerp(RMS_AO, Texture2DSample(T_GradientOcclusion, T_GradientOcclusionSampler, UV0).x, g));
    }
}

D Coverage = 1.0;
if (S_Coverage > 0.5)
{
    Coverage = Texture2DSample(T_Coverage, T_CoverageSampler, UV0).x;
}


if (S_WideOcclusion > 0.5)
{
    RMS_AO = L.CombineOcclusion(RMS_AO, Texture2DSample(T_WideOcclusion, T_WideOcclusionSampler, UV1).x);
}



D DetailMask = 1.0;
bool DetailFade = S_Detail > 0.5;
if (DetailFade)
{
    DetailMask = Texture2DSample(T_Detail, T_DetailSampler, UV0).x;
}
if (S_DetailColor > 0.5)
{
    float3 dc = saturate(Texture2DSample(T_DetailColor, T_DetailColorSampler, UV2).xyz() * BaseColor);
    BaseColor = DetailFade ? lerp(BaseColor, dc, DetailMask) : dc;
}
if (S_DetailNormal > 0.5)
{
    float3 d = float3(0.0, 0.0, 1.0);
    if (Flowing && S_FlowDetailNormal > 0.5)
    {
        
        float3 a = L.RotateToUV(L.NormalXY(Texture2DSample(T_DetailNormal, T_DetailNormalSampler, FlowA2)), UV0, FlowA2);
        float3 b = L.RotateToUV(L.NormalXY(Texture2DSample(T_DetailNormal, T_DetailNormalSampler, FlowB2)), UV0, FlowB2);
        d = normalize(lerp(a, b, FlowW2));
    }
    else
    {
        d = L.RotateToUV(L.NormalXY(Texture2DSample(T_DetailNormal, T_DetailNormalSampler, UV2)), UV0, UV2);
    }
    RMS_Normal = L.ArcBlend(RMS_Normal, L.Reoriented(RMS_Normal, d), DetailMask);
}
if (S_DetailRoughness > 0.5)
{
    D rd = 0.0;
    if (Flowing && S_FlowDetailRoughness > 0.5)
    {
        D a = Texture2DSample(T_DetailRoughness, T_DetailRoughnessSampler, FlowA2).x;
        D b = Texture2DSample(T_DetailRoughness, T_DetailRoughnessSampler, FlowB2).x;
        D a2 = a * a;
        rd = sqrt(saturate((b * b - a2) * FlowW2 + a2));
    }
    else
    {
        rd = Texture2DSample(T_DetailRoughness, T_DetailRoughnessSampler, UV2).x;
    }
    D r = sqrt(saturate(rd * rd + RMS_Roughness * RMS_Roughness));
    RMS_Roughness = DetailFade ? lerp(RMS_Roughness, r, DetailMask) : r;
}
if (S_DetailFoam > 0.5)
{
    
    D df = 0.0;
    if (Flowing && S_FlowDetailFoam > 0.5)
    {
        D a = Texture2DSample(T_DetailFoam, T_DetailFoamSampler, FlowA2).x;
        D b = Texture2DSample(T_DetailFoam, T_DetailFoamSampler, FlowB2).x;
        df = saturate((b - a) * FlowW2 + a);
    }
    else
    {
        df = saturate(Texture2DSample(T_DetailFoam, T_DetailFoamSampler, UV2).x);
    }
    D inv = 1.0 - Foam;
    Foam = (inv - (1.0 - df) * inv) * DetailMask + Foam;
}

if (S_WideFoamThreshold > 0.5)
{
    Foam = Foam * Texture2DSample(T_WideFoamThreshold, T_WideFoamThresholdSampler, UV1).x;
}
RMS_Foam = saturate(Foam);








if (S_Ocean > 0.5)
{
    float3 P = Parameters.WorldPosition_CamRelative;
    D t = V_AnimateTimeContext.z;
    float2 pp = float2((P.x - RMS_VertexExpression.x) * 0.0024999999441206455230712890625, (P.y - RMS_VertexExpression.y) * 0.0024999999441206455230712890625);
    float2 pq = float2(View.PreViewTranslation.x * -0.0024999999441206455230712890625, View.PreViewTranslation.y * -0.0024999999441206455230712890625);
    D amp = 0.5;
    D freq = 1.0;
    D wave = 0.0;
    for (int i = 0; i < 6; ++i)
    {
        float2 a = float2(pq.x * freq, pq.y * freq);
        float2 b = float2(pp.x * freq, pp.y * freq);
        D gx = frac(frac(a.x * 0.00999999977648258209228515625) + frac(b.x * 0.00999999977648258209228515625)) * 256.0;
        D gy = frac(frac(a.y * 0.00999999977648258209228515625) + frac(b.y * 0.00999999977648258209228515625)) * 256.0;
        uint cx = uint(int(floor(gx)));
        uint cy = uint(int(floor(gy)));
        D fx = D(int(cx & 255u));
        D fy = D(int(cy & 255u));
        D fx1 = D(int((cx + 1u) & 255u));
        D fy1 = D(int((cy + 1u) & 255u));
        D h00 = frac(sin(dot(float2(fx, fy), float2(127.09999847412109375, 311.70001220703125))) * 43758.546875);
        D h01 = frac(sin(dot(float2(fx, fy1), float2(127.09999847412109375, 311.70001220703125))) * 43758.546875);
        D h10 = frac(sin(dot(float2(fx1, fy), float2(127.09999847412109375, 311.70001220703125))) * 43758.546875);
        D h11 = frac(sin(dot(float2(fx1, fy1), float2(127.09999847412109375, 311.70001220703125))) * 43758.546875);
        D sx = saturate(frac(gx));
        D wx = (sx * sx) * (3.0 - sx * 2.0);
        D sy = saturate(frac(gy));
        D wy = (sy * sy) * (3.0 - sy * 2.0);
        D n0 = wx * (h10 - h00) + h00;
        D n1 = wx * (h11 - h01) + h01;
        D nz = (wy * (n1 - n0) + n0) * 0.5;
        D ph = frac((t * 7.957746982574462890625) * sqrt(freq * 0.00153938052244484424591064453125));
        D ax = frac(((frac(a.x) + frac(b.x)) + ph) + nz) * 6.283185482025146484375;
        D ay = frac(((frac(a.y) + frac(b.y)) + ph) + nz) * 6.283185482025146484375;
        D kx = 1.0 - abs(sin(ax));
        D ky = 1.0 - abs(sin(ay));
        wave = (1.0 - sqrt(((abs(cos(ay)) - ky) * ky + ky) * ((abs(cos(ax)) - kx) * kx + kx))) * amp + wave;
        amp = amp * 0.5;
        freq = freq * 2.0;
        pp = float2(pp.y * 0.809017121791839599609375 + pp.x * -0.587785065174102783203125, pp.y * -0.587785065174102783203125 + pp.x * -0.809017121791839599609375);
        pq = float2(pq.y * 0.809017121791839599609375 + pq.x * -0.587785065174102783203125, pq.y * -0.587785065174102783203125 + pq.x * -0.809017121791839599609375);
    }
    float3 W = float3(P.x - View.PreViewTranslation.x, P.y - View.PreViewTranslation.y, P.z - View.PreViewTranslation.z);
    float4 g = float4(0.0, 0.0, 0.0, 0.0);
    if (S_OceanGeometry > 0.5)
    {
        g = Texture2DSampleLevel(T_OceanGeometry, T_OceanGeometrySampler, UV0, 0.0);
    }
    D rx = W.x - RMS_VertexExpression.x;
    D ry = W.y - RMS_VertexExpression.y;
    D above = W.z - g.z * 100.0;
    D shore = (saturate(1.0 - above * 0.0033333334140479564666748046875) * saturate(1.0 - above * 0.0024999999441206455230712890625)) * saturate(1.0 - sqrt(g.x * g.x + g.y * g.y) * 0.00166666670702397823333740234375);
    D s2 = shore * shore;
    D d1 = saturate((RMS_VertexExpression.z - RMS_VertexExpression.w) * 0.0333333350718021392822265625);
    D d2 = saturate(abs(RMS_VertexExpression.w) * 0.01666666753590106964111328125);
    D c = saturate(wave * 0.100000001490116119384765625) * 0.050000011920928955078125 + 0.949999988079071044921875;
    D c2 = c * c;
    D c4 = c2 * c2;
    D na = Texture3DSample(View.PerlinNoise3DTexture, View.PerlinNoise3DTextureSampler, float3(t * 0.125, rx * 0.001953125, ry * 0.001953125)).x;
    D nb = Texture3DSample(View.PerlinNoise3DTexture, View.PerlinNoise3DTextureSampler, float3(rx * 0.00390625, ry * 0.00390625, t * 0.0625)).x;
    D crest = saturate((c4 * c4) * (sqrt(na * nb) * 0.5 + 0.5));
    D br = saturate((sqrt(saturate(((s2 + -1.0) + crest) * crest)) * ((d1 * d1) * (1.0 - d2) + d2)) * (((crest + s2) > 1.0) ? 1.0 : 0.0));
    D foam = (br * br) * (3.0 - br * 2.0);
    D f2 = foam * foam;
    D op = saturate(f2 * f2);
    D lift = (sqrt(s2) * (crest * 4.0 - wave) + wave) + foam * 6.0;
    float3 ng = normalize(cross(ddx_fine(P), ddy_fine(P)));
    float3 Pd = ng * lift + P;
    float3 nd = normalize(cross(ddx_fine(Pd), ddy_fine(Pd)));
    float3x3 T2W = Parameters.TangentToWorld;
    float3 wn = normalize((T2W[2] - ng) + nd);
    D fd = Parameters.SvPosition.w * 9.9999997473787516355514526367188e-06;
    D fade = 1.0 / (fd * fd + 1.0);
    
    RMS_Normal = normalize(float3(lerp(T2W[0].z, dot(T2W[0], wn), fade), lerp(T2W[1].z, dot(T2W[1], wn), fade), lerp(T2W[2].z, dot(T2W[2], wn), fade)));
    BaseColor = float3(0.810000002384185791015625, 0.810000002384185791015625, 0.810000002384185791015625);
    RMS_Metallic = 0.0;
    RMS_AO = 1.0;
    RMS_Opacity = op;
    RMS_Roughness = sqrt(op);
    RMS_Foam = saturate(foam);
}
if (S_DetailOcclusion > 0.5)
{
    D od = L.CombineOcclusion(RMS_AO, Texture2DSample(T_DetailOcclusion, T_DetailOcclusionSampler, UV2).x);
    RMS_AO = DetailFade ? lerp(RMS_AO, od, DetailMask) : od;
}
if (S_DetailCoverage > 0.5)
{
    D dc = saturate(Texture2DSample(T_DetailCoverage, T_DetailCoverageSampler, UV2).x * Coverage);
    Coverage = DetailFade ? lerp(Coverage, dc, DetailMask) : dc;
}




if (S_LayeredColor > 0.5)
{
    float3 lc = L.LinearToSrgb(Texture2DSample(T_LayeredColor, T_LayeredColorSampler, UV0).xyz());
    float3 cs = L.LinearToSrgb(BaseColor);
    BaseColor = L.SrgbToLinear(float3(L.Overlay1(lc.x, cs.x), L.Overlay1(lc.y, cs.y), L.Overlay1(lc.z, cs.z)));
}



if (S_CylindricalNormal > 0.5)
{
    float3 n = RMS_Normal;
    float3 a = normalize(float3(n.z, 0.0, -n.x));
    float3 t = normalize(cross(a, n));
    float3 v = mul(Parameters.TangentToWorld, Parameters.CameraVector);
    D d = dot(v, t);
    if (abs(d) < 0.0500000007450580596923828125)
    {
        d = sign((RMS_Noise.x * 2.0 + -1.0) + d * 20.0) * 0.0500000007450580596923828125;
    }
    RMS_Normal = normalize(v - t * d);
}



if (S_Wetness > 0.5)
{
    D wet = 0.0;
    if (S_WetnessTrickle > 0.5)
    {
        
        
        uint ww;
        uint wh;
        T_Wetness.GetDimensions(ww, wh);
        D aspect = D(ww) / D(wh);
        uint frames = max(1u, uint(max(1.0, round(D(wh) / D(ww)))));
        D t = V_AnimateTimeContext.z + 0.5;
        D ft = trunc(t);
        uint f = uint(int(ft)) + frames;
        D a = Texture2DSample(T_Wetness, T_WetnessSampler, float2(UV0.x, (D((f + 4294967295u) % frames) + UV0.y) * aspect)).x;
        D b = Texture2DSample(T_Wetness, T_WetnessSampler, float2(UV0.x, (D(f % frames) + UV0.y) * aspect)).x;
        D fr = saturate(t - ft);
        wet = lerp(a, b, (fr * fr) * (3.0 - fr * 2.0));
    }
    else
    {
        wet = Texture2DSample(T_Wetness, T_WetnessSampler, UV0).x;
    }
    D rain = L.RainEase(saturate(saturate(RMS_EBuffer.z)));
    D flag = (RMS_EBuffer.w > 0.0) ? 1.0 : 0.0;
    float3 vn = Parameters.TangentToWorld[2];
    D up = saturate(vn.z);
    D up2 = up * up;
    D up4 = up2 * up2;
    D side = sqrt(max(0.0, 1.0 - vn.z * vn.z));
    D side2 = side * side;
    D puddle = L.Half8x2(RMS_EBuffer.x, RMS_EBuffer.y);
    D disp = 0.0;
    if (S_WetnessTrickle > 0.5)
    {
        
        disp = ((((puddle * 0.20000000298023223876953125) * saturate(up4 * up4)) + 0.20000000298023223876953125) + ((saturate(rain) * 0.4000000059604644775390625) * saturate((side2 * side2) * side))) * wet;
    }
    else
    {
        disp = (wet * 0.20000000298023223876953125) * (((saturate(rain) * 2.0) * saturate((side2 * side2) * side)) + saturate(up4 * up4) * puddle);
    }
    float3 P = Parameters.WorldPosition_CamRelative;
    float3 ng = normalize(cross(ddx_fine(P), ddy_fine(P)));
    float3 Pd = ng * disp + P;
    float3 nd = normalize(cross(ddx_fine(Pd), ddy_fine(Pd)));
    float3 wn = normalize((vn - ng) + nd);
    WetNormal = normalize(lerp(RMS_Normal, mul(Parameters.TangentToWorld, wn), pow(saturate(wet), 0.25)));
    HasWetNormal = true;
    D w16 = saturate(wet * 16.0);
    RMS_WetLayer = float2((1.0 - w16) * flag + w16, w16 * (1.0 - flag));
}






float3 MateriaGlow = float3(0.0, 0.0, 0.0);
bool HasMateria = false;
if (S_Materia > 0.5)
{
    BaseColor = float3(0.0, 0.0, 0.0);
    RMS_Metallic = 0.0;
    RMS_Roughness = 0.0;
    D phase = 0.0;
    float4 mc = float4(1.0, 1.0, 1.0, 1.0);
    if (S_MateriaIndexed > 0.5)
    {
        uint idx = uint(int(min(max(0.0, floor(UV2.x)), 7.0)));
        float4 gv = (idx < 4u) ? V_GenericVector0Context : V_GenericVector1Context;
        uint kind = uint(int(gv[idx & 3u]));
        mc = T_MateriaContext.Load(int3(int(kind), 0, 0));
        phase = D(int(idx)) * 0.125;
        Coverage = mc.w;
    }
    D a = frac(phase + V_AnimateTimeContext.x) * 6.283185482025146484375;
    D s = sin(a);
    D c = cos(a);
    float3 ve = float3(RMS_VertexExpression.x, RMS_VertexExpression.y, RMS_VertexExpression.z);
    float3 q0 = ve * 0.5 + 0.5;
    
    float3x3 R = float3x3(float3(c * c, -s * c + (s * s) * c, -s * -s + (s * c) * c),
                          float3(s * c, c * c + (s * s) * s, c * -s + (s * c) * s),
                          float3(-s, c * s, c * c));
    D n1 = Texture3DSample(View.PerlinNoise3DTexture, View.PerlinNoise3DTextureSampler, mul(R, q0) * 0.5).x;
    float3 dir = -Parameters.CameraVector;
    float3 qa = (dir * n1 + ve) * 0.25 + 0.25;
    float3 qb = ((dir * 1.2000000476837158203125) * n1 + ve) * 0.5 + 0.5;
    float3 qc = ((dir * 0.800000011920928955078125) * n1 + ve) * 0.125 + 0.125;
    D na = Texture3DSample(View.PerlinNoise3DTexture, View.PerlinNoise3DTextureSampler, float3(s * qa.z + qa.x * c, qa.y, c * qa.z + qa.x * -s)).x;
    D nb = Texture3DSample(View.PerlinNoise3DTexture, View.PerlinNoise3DTextureSampler, float3(qb.x, -s * qb.z + c * qb.y, c * qb.z + s * qb.y)).x;
    D nc = Texture3DSample(View.PerlinNoise3DTexture, View.PerlinNoise3DTextureSampler, float3(-s * qc.y + qc.x * c, c * qc.y + qc.x * s, qc.z)).x;
    D g = (na * nb) * nc;
    D facing = saturate(dot(mul(RMS_Normal, Parameters.TangentToWorld), Parameters.CameraVector)) * (g * g);
    D glow = (facing * facing) * 4096.0;
    MateriaGlow = (S_MateriaIndexed > 0.5) ? float3(mc.x * glow, mc.y * glow, mc.z * glow) : float3(glow, glow, glow);
    HasMateria = true;
}




float3 HologramGlow = float3(0.0, 0.0, 0.0);
bool HasHologram = false;
D HoloG = 0.0;
if (S_Hologram > 0.5 || S_Phantom > 0.5)
{
    float3 Nw = mul(RMS_Normal, Parameters.TangentToWorld);
    D NoV = saturate(dot(Nw, Parameters.CameraVector));
    D a = 1.0 - NoV;
    D a2 = a * a;
    D b2 = NoV * NoV;
    float3 ve = float3(RMS_VertexExpression.x, RMS_VertexExpression.y, RMS_VertexExpression.z);
    D sparkle = Env.BlueNoise3D(int3(int(round(frac(ve.x * 0.5) * 64.0)) & 63, int(round(frac(ve.y * 0.5) * 64.0)) & 63, int(round(frac(ve.z * 0.5) * 64.0)) & 255)).x;
    D rim = (a2 * a2) * a + (b2 * b2) * NoV;
    D rough = RMS_Roughness;
    if (S_HologramEye > 0.5)
    {
        
        D cvs = saturate(EyeCv);
        D gv = saturate(dot(EyeG, Parameters.CameraVector));
        D pupil = saturate((sqrt(EyePi.x * EyePi.x + EyePi.y * EyePi.y) + -0.2899999916553497314453125) * 49.999973297119140625);
        D ir = saturate((EyeR2 + -1.0) * -1.4285714626312255859375);
        D irs = (ir * ir) * (3.0 - ir * 2.0);
        D irs2 = irs * irs;
        D io = 1.0;
        if (S_IrisOcclusion > 0.5)
        {
            io = Texture2DSample(T_IrisOcclusion, T_IrisOcclusionSampler, float2(EyePi.x * 0.5 + 0.5, EyePi.y * 0.5 + 0.5)).x;
        }
        D m = (((pupil * pupil) * io) * (3.0 - pupil * 2.0)) * ((irs2 * irs2 - irs) * 0.5 + irs);
        D ga = 1.0 - gv;
        D ga2 = ga * ga;
        D gv2 = gv * gv;
        D g5 = ((ga2 * ga2) * ga + (gv2 * gv2) * gv) * saturate((pow(m + gv, 7.62939453125e-06) + -1.0) + m);
        D ca = 1.0 - cvs;
        D ca2 = ca * ca;
        D ca4 = ca2 * ca2;
        D cvs2 = cvs * cvs;
        D c5 = ca4 * ca + (cvs2 * cvs2) * cvs;
        D eyeRim = lerp(g5, c5, ca4 * (ca * 0.961274802684783935546875) + 0.03872518241405487060546875);
        rim = lerp(eyeRim, rim, EyeScl);
        rough = 0.07999999821186065673828125;
    }
    D so = saturate((RMS_AO + -1.0) + pow(RMS_AO + NoV, exp2(-1.0 - rough * 16.0)));
    HoloG = ((rim * (Nw.z * 0.5 + 0.5)) * sparkle) * so;
    if (S_Hologram > 0.5)
    {
        HologramGlow = float3(HoloG, HoloG, HoloG);
        HasHologram = true;
        RMS_Opacity = L.FarFade(Parameters.SvPosition.w, View.InvDeviceZToWorldZTransform);
    }
}




float3 PhantomGlow = float3(0.0, 0.0, 0.0);
bool HasPhantom = false;
if (S_Phantom > 0.5)
{
    D g = saturate(HoloG);
    float3 t0 = float3(1.0, 1.0, 1.0);
    float3 t1 = float3(1.0, 1.0, 1.0);
    if (S_ToneGradient > 0.5)
    {
        t0 = T_ToneGradient.Load(int3(0, 0, 0)).xyz();
        t1 = T_ToneGradient.Load(int3(1, 0, 0)).xyz();
    }
    PhantomGlow = lerp(t0, t1, g);
    HasPhantom = true;
    D dist = (V_GenericVector0Context.x > 0.0) ? V_GenericVector0Context.x * 50.0 : 50.0;
    D f = saturate(saturate((1.0 / max(1.0, dist)) * ((View.InvDeviceZToWorldZTransform.y - Parameters.SvPosition.w) + 1.0 / -View.InvDeviceZToWorldZTransform.w)));
    D fade = (f * f) * (3.0 - f * 2.0);
    D f2 = fade * fade;
    D f4 = f2 * f2;
    RMS_Opacity = f4 * f4;
    RMS_ColoredOpacity = float3(fade, fade, fade);
}




float3 GhostGlow = float3(0.0, 0.0, 0.0);
bool HasGhost = false;
if (S_Ghost > 0.5)
{
    float3 Nw = mul(RMS_Normal, Parameters.TangentToWorld);
    D NoV = saturate(dot(Nw, Parameters.CameraVector));
    float3 q = float3(RMS_VertexExpression.x, RMS_VertexExpression.y, RMS_VertexExpression.z) * 0.00999999977648258209228515625;
    D t = V_AnimateTimeContext.x;
    D f4 = frac(t * 4.0);
    D f2 = frac(t * 2.0);
    D f1 = frac(t);
    float3 cx = float3(RMS_LocalToWorld0.x, RMS_LocalToWorld1.x, RMS_LocalToWorld2.x);
    float3 cy = float3(RMS_LocalToWorld0.y, RMS_LocalToWorld1.y, RMS_LocalToWorld2.y);
    float3 cz = float3(RMS_LocalToWorld0.z, RMS_LocalToWorld1.z, RMS_LocalToWorld2.z);
    D pa = Texture3DSample(View.PerlinNoise3DTexture, View.PerlinNoise3DTextureSampler, q - cz * f4).x;
    D pb = Texture3DSample(View.PerlinNoise3DTexture, View.PerlinNoise3DTextureSampler, (cz + q) - cz * f4).x;
    float3 qy = q + 0.3300000131130218505859375;
    D pc = Texture3DSample(View.PerlinNoise3DTexture, View.PerlinNoise3DTextureSampler, (qy - cy * f2) * 0.5).x;
    D pd = Texture3DSample(View.PerlinNoise3DTexture, View.PerlinNoise3DTextureSampler, ((qy + cy) - cy * f2) * 0.5).x;
    float3 qx = q + 0.660000026226043701171875;
    D pe = Texture3DSample(View.PerlinNoise3DTexture, View.PerlinNoise3DTextureSampler, (qx - cx * f1) * 0.25).x;
    D pf = Texture3DSample(View.PerlinNoise3DTexture, View.PerlinNoise3DTextureSampler, ((qx + cx) - cx * f1) * 0.25).x;
    D turb = saturate(exp2(log2((lerp(pc, pd, f2) * lerp(pa, pb, f4)) * lerp(pe, pf, f1)) * 0.3333333432674407958984375));
    float3 tone = float3(1.0, 1.0, 1.0);
    if (S_ToneGradient > 0.5)
    {
        uint tw;
        uint th;
        T_ToneGradient.GetDimensions(tw, th);
        D w = D(tw);
        tone = Texture2DSampleLevel(T_ToneGradient, T_ToneGradientSampler, float2(((w + -1.0) * turb + 0.5) * (1.0 / w), 0.5 / D(th)), 0.0).xyz();
    }
    D n2 = NoV * NoV;
    D n5 = (n2 * n2) * NoV;
    GhostGlow = tone * (RMS_AO * n5);
    HasGhost = true;
    RMS_Opacity = L.FarFade(Parameters.SvPosition.w, View.InvDeviceZToWorldZTransform);
}



RMS_OpacityMask = (RMS_DynamicCoverage > RMS_Noise.w * 0.99609375 + 0.001953125) ? L.Dithered(Coverage, RMS_Noise.x) : -1.0;



if (S_Segmented > 0.5)
{
    float3 c = BaseColor;
    float3 cs = L.LinearToSrgb(c);
    if (S_SegmentLayer0 > 0.5)
    {
        D w = saturate(V_GenericVector0Context.w) * Texture2DSample(T_SegmentLayer0, T_SegmentLayer0Sampler, UV0).x;
        c = lerp(c, L.SegmentTint(cs, V_GenericVector0Context.xyz()), w);
    }
    if (S_SegmentLayer1 > 0.5)
    {
        D w = saturate(V_GenericVector1Context.w) * Texture2DSample(T_SegmentLayer1, T_SegmentLayer1Sampler, UV0).x;
        c = lerp(c, L.SegmentTint(cs, V_GenericVector1Context.xyz()), w);
    }
    float3 dielectric = min(max(c, float3(0.00604883022606372833251953125, 0.00604883022606372833251953125, 0.00604883022606372833251953125)), float3(1.0, 1.0, 1.0));
    float3 metal = min(max(c, float3(0.2581828534603118896484375, 0.2581828534603118896484375, 0.2581828534603118896484375)), float3(1.0, 1.0, 1.0));
    BaseColor = lerp(dielectric, metal, RMS_Metallic);
}



if (S_ExtraColor > 0.5)
{
    uint ew;
    uint eh;
    T_ExtraColor.GetDimensions(ew, eh);
    float2 uv = L.ExtraCoordinate(UV2, S_ExtraPixelCoordinate, V_ExtraPixelCoordinateContext, S_ExtraNormalizedCoordinate, V_ExtraNormalizedCoordinateContext, ew, eh);
    float4 x = Texture2DSampleLevel(T_ExtraColor, T_ExtraColorSampler, uv, 0.0);
    BaseColor = BaseColor * x.w + x.xyz();
}


if (S_Emissive > 0.5 || HasMateria || HasHologram || HasGhost || HasPhantom)
{
    float3 e = float3(0.0, 0.0, 0.0);
    if (HasMateria)
    {
        e = MateriaGlow;
    }
    else if (HasPhantom)
    {
        e = PhantomGlow;
    }
    else if (HasHologram)
    {
        e = HologramGlow;
    }
    else if (HasGhost)
    {
        e = GhostGlow;
    }
    else if (S_ViewCoordinate > 0.5)
    {
        
        float2 sv = float2((Parameters.SvPosition.x - View.ViewRectMin.x) * View.ViewSizeAndInvSize.z + -0.5, (Parameters.SvPosition.y - View.ViewRectMin.y) * View.ViewSizeAndInvSize.w + -0.5);
        float2 fit = float2(min((View.ViewSizeAndInvSize.x * 0.5625) * View.ViewSizeAndInvSize.w, 1.0), min((View.ViewSizeAndInvSize.y * 1.77777779102325439453125) * View.ViewSizeAndInvSize.z, 1.0));
        e = Texture2DSampleLevel(T_Emissive, T_EmissiveSampler, float2(sv.x * fit.x + 0.5, fit.y * sv.y + 0.5), 0.0).xyz();
    }
    else
    {
        e = Texture2DSample(T_Emissive, T_EmissiveSampler, UV0).xyz() + EyeGlow;
    }
    D k = 1.0;
    if (S_ExternalEmissive > 0.5)
    {
        k = (V_ExternalEmissiveContext.w > 0.0) ? View.OneOverPreExposure : 1.0;
        e = e * V_ExternalEmissiveContext.xyz();
    }
    
    
    
    if (S_BrokenFlow > 0.5)
    {
        float2 dir = float2(0.0, 0.0);
        if (S_WideFlowDirection > 0.5)
        {
            float3 fd = L.NormalXY(Texture2DSample(T_WideFlowDirection, T_WideFlowDirectionSampler, UV1));
            dir = float2(fd.x, fd.y);
        }
        D ph = 0.0;
        if (S_WideFlowPhase > 0.5)
        {
            ph = Texture2DSample(T_WideFlowPhase, T_WideFlowPhaseSampler, UV1).x;
        }
        D dv = 1.0;
        if (S_WideFlowDirectivity > 0.5)
        {
            dv = Texture2DSample(T_WideFlowDirectivity, T_WideFlowDirectivitySampler, UV1).x;
        }
        D tm = (S_AnimateTime > 0.5) ? V_AnimateTimeContext.z : 0.0;
        if (S_BrokenFlowEmissive0 > 0.5)
        {
            e = e * L.FlowLayer(T_BrokenFlowEmissive0, T_BrokenFlowEmissive0Sampler, UV2, dir, ph, dv, tm, V_GenericVector0Context);
        }
        if (S_BrokenFlowEmissive1 > 0.5)
        {
            e = e * L.FlowLayer(T_BrokenFlowEmissive1, T_BrokenFlowEmissive1Sampler, UV2, dir, ph, dv, tm, V_GenericVector1Context);
        }
    }
    if (S_ExtraEmissive > 0.5)
    {
        uint ew;
        uint eh;
        T_ExtraEmissive.GetDimensions(ew, eh);
        float2 uv = L.ExtraCoordinate(UV2, S_ExtraPixelCoordinate, V_ExtraPixelCoordinateContext, S_ExtraNormalizedCoordinate, V_ExtraNormalizedCoordinateContext, ew, eh);
        e = e * Texture2DSampleLevel(T_ExtraEmissive, T_ExtraEmissiveSampler, uv, 0.0).xyz();
    }
    RMS_Emissive = e * k;
}






bool LayerB = false;
if (S_Layered > 0.5 && S_ShadingLayer > 0.5)
{
    LayerB = Texture2DSample(T_ShadingLayer, T_ShadingLayerSampler, UV0).x > RMS_Noise.x * 0.99609375 + 0.001953125;
}
bool FirstLayer = !(S_Layered > 0.5 && LayerB);

if (S_Unlit > 0.5)
{
    RMS_ShadingModel = 0.0;
}

if (S_Eye > 0.5)
{
    RMS_AO = EyeAO;
    RMS_Reflectance = 0.03872518241405487060546875;
}

if (S_Standard > 0.5 && FirstLayer)
{
    RMS_ShadingModel = 1.0;
    RMS_Reflectance = 0.0400000028312206268310546875;
    RMS_Custom.y = 0.4000000059604644775390625;
    if (S_Film > 0.5)
    {
        if (S_FilmThickness > 0.5)
        {
            RMS_Custom.x = Texture2DSample(T_FilmThickness, T_FilmThicknessSampler, UV0).x;
        }
        if (S_FilmStructure > 0.5)
        {
            RMS_Custom.y = Texture2DSample(T_FilmStructure, T_FilmStructureSampler, UV0).x;
        }
    }
    if (S_Isotropy > 0.5)
    {
        RMS_Custom.z = Texture2DSample(T_Isotropy, T_IsotropySampler, UV0).x;
    }
}

if (S_Skin > 0.5 && FirstLayer)
{
    RMS_ShadingModel = 3.0;
    RMS_Reflectance = 0.0465205647051334381103515625;
    RMS_ModelParam = 0.684779345989227294921875;
    RMS_Metallic = 0.0;
    RMS_Specular = 0.1500000059604644775390625;
    if (S_Pores > 0.5)
    {
        RMS_Custom.x = Texture2DSample(T_Pores, T_PoresSampler, UV0).x;
    }
}

if (S_Subsurface > 0.5)
{
    RMS_ShadingModel = 5.0;
    if (S_Distribution > 0.5)
    {
        RMS_Specular = Texture2DSample(T_Distribution, T_DistributionSampler, UV0).x;
    }
}

if (S_Blood > 0.5)
{
    D o2 = 1.0;
    if (S_OxygenSaturation > 0.5)
    {
        o2 = Texture2DSample(T_OxygenSaturation, T_OxygenSaturationSampler, UV0).x;
    }
    BaseColor = lerp(float3(0.0802, 0.00368, 0.00802), float3(0.913, 0.0, 0.00152), o2);
    RMS_Metallic = 0.0;
    RMS_Specular = 0.1500000059604644775390625;
    RMS_Reflectance = 0.0266276858747005462646484375;
    RMS_ModelParam = 0.4437947571277618408203125;
}

if (S_Hair > 0.5)
{
    RMS_ShadingModel = 7.0;
    RMS_Reflectance = 0.0465205647051334381103515625;
    RMS_ModelParam = 0.684779345989227294921875;
    RMS_Metallic = 0.0;
    RMS_Specular = 0.0;
    if (S_WideBentNormal > 0.5)
    {
        float4 b = Texture2DSample(T_WideBentNormal, T_WideBentNormalSampler, UV1);
        float3 bn = normalize(float3(b.x * 2.0 + -1.0, b.y * 2.0 + -1.0, b.z * 2.0 + -1.0));
        RMS_Custom = float4(saturate(mul(bn, Parameters.TangentToWorld) * 0.5 + 0.5), 0.0);
    }
}

if (S_Fabric > 0.5 && (S_Layered < 0.5 || LayerB))
{
    RMS_ShadingModel = 8.0;
    RMS_Reflectance = 0.067215375602245330810546875;
    RMS_ModelParam = 0.742264926433563232421875;
    RMS_Roughness = max(0.5, RMS_Roughness);
    RMS_Metallic = 0.0;
    RMS_Specular = 0.0;
    RMS_Custom = float4(0.0, 0.0, 0.0, 0.0);
    if (S_Diffusion > 0.5)
    {
        RMS_Custom.x = Texture2DSample(T_Diffusion, T_DiffusionSampler, UV0).x;
    }
}

if (S_Layered > 0.5)
{
    RMS_ModelParam = L.EncodeReflectance(RMS_Reflectance);
}






if (S_ReflectanceGlass > 0.5)
{
    RMS_Reflectance = 0.0400000028312206268310546875;
}
if (S_ReflectanceWater > 0.5)
{
    RMS_Reflectance = 0.0203731842339038848876953125;
}
if (S_ReflectanceCrystal > 0.5)
{
    RMS_Reflectance = 0.159951984882354736328125;
}
if (S_PhaseGWater > 0.5)
{
    RMS_PhaseG = -0.60000002384185791015625;
}
if (S_Thin > 0.5)
{
    RMS_MediumPath = 1.0;
}
if (S_Thick > 0.5)
{
    RMS_MediumPath = 2.0;
}
if (S_Convex > 0.5)
{
    RMS_MediumPath = 3.0;
}
if (S_Pool > 0.5)
{
    RMS_MediumPath = (S_Ocean > 0.5) ? 5.0 : 4.0;
}

RMS_WetNormal = HasWetNormal ? WetNormal : (EyeInner ? EyeInnerNormal : RMS_Normal);
return BaseColor;
