





























struct RMS_Lib
{
    
    float3 NormalXY(float4 t)
    {
        D x = t.x * 2.0 - 1.0;
        D y = t.y * 2.0 - 1.0;
        D z = sqrt(max(0.0, 1.0 - dot(float2(x, y), float2(x, y))));
        return normalize(float3(x, y, z));
    }

    
    float3 WorldNormal(float3 n, float3x3 TangentToWorld, D TwoSidedSign)
    {
        float3 m = normalize(n);
        float3 w = normalize(mul(m, TangentToWorld));
        return w * TwoSidedSign;
    }

    
    D FilterRoughness(D Roughness, float3 N)
    {
        float3 dx = ddx_fine(N);
        float3 dy = ddy_fine(N);
        D r = saturate(Roughness);
        return sqrt(saturate(min((dot(dy, dy) + dot(dx, dx)) * 0.15915493667125701904296875, 0.180000007152557373046875) + r * r));
    }

    
    
    D EmissiveTransmission(float3 N, float3 V, D Roughness, D Metallic)
    {
        D NoV = saturate(dot(N, V));
        D a = 1.0 - Roughness;
        D a004 = (min(a * a, exp2(NoV * -9.27999973297119140625)) * a + (0.0425000004470348358154296875 - Roughness * 0.0274999998509883880615234375)) * 1.03999996185302734375;
        D t = 1.0 - saturate(((Roughness * 0.02199999988079071044921875 + -0.039999999105930328369140625) + a004) + ((1.03999996185302734375 - Roughness * 0.572000026702880859375) - a004) * 0.0400000028312206268310546875);
        D k = (t * t) * exp2(max(0.001000000047497451305389404296875, 0.300000011920928955078125 / max(0.0333333350718021392822265625, NoV)) * -0.0291463173925876617431640625);
        return k - k * saturate(Metallic);
    }

    
    D CombineOcclusion(D o, D w)
    {
        D p = o * w;
        D m = min(o, w);
        D a = (1.0 - m) + p;
        D a2 = a * a;
        D c = 1.0 - (a2 * a2) * a;
        D c2 = c * c;
        return (c2 * c2) * (c * (p - m)) + m;
    }

    
    float2 SafeDirection(float2 v)
    {
        D r = rsqrt(dot(v, v));
        return isnan(r) ? float2(0.0, 0.0) : float2(r * v.x, r * v.y);
    }

    
    
    float3 RotateToUV(float3 d, float2 uvThis, float2 uvOther)
    {
        float2 g0 = SafeDirection(ddy_fine(uvThis) + ddx_fine(uvThis));
        float2 g1 = SafeDirection(ddy_fine(uvOther) + ddx_fine(uvOther));
        D c = dot(g1, g0);
        D s = g1.x * g0.y - g1.y * g0.x;
        return float3(dot(float2(d.x, d.y), float2(c, -s)), dot(float2(d.x, d.y), float2(s, c)), d.z);
    }

    
    float3 Reoriented(float3 b, float3 d)
    {
        float3 t = float3(b.x, b.y, b.z + 1.0);
        float3 u = float3(-d.x, -d.y, d.z);
        D k = dot(t, u);
        return normalize(t * k - u * t.z);
    }

    
    float3 ArcBlend(float3 a, float3 b, D tIn)
    {
        D t = saturate(tIn);
        D c = dot(a, b);
        D sg = (c >= 0.0) ? 1.0 : -1.0;
        D th = acos(saturate(abs(c)));
        float3 r = ((b * sg) * sin(th * t)) + (a * sin(th * (1.0 - t)));
        if (dot(r, r) < 9.9999999747524270787835121154785e-07)
        {
            r = lerp(a, b, t);
        }
        if (dot(r, r) < 9.9999999747524270787835121154785e-07)
        {
            r = (t < 0.5) ? a : b;
        }
        return normalize(r);
    }

    
    D Half8x2(D lo, D hi)
    {
        return f16tof32((uint(round(hi * 255.0)) << 8) | uint(round(lo * 255.0)));
    }

    
    D RainEase(D e)
    {
        if (e < 0.5)
        {
            D e2 = e * e;
            return (e2 * e2) * 8.0;
        }
        D f = 1.0 - e;
        D f2 = f * f;
        return 1.0 - (f2 * f2) * 8.0;
    }

    
    float2 ExtraCoordinate(float2 uv, D usePixel, float4 pix, D useNormalized, float4 nrm, uint w, uint h)
    {
        float2 r = uv;
        if (usePixel > 0.5 && dot(pix, float4(1.0, 1.0, 1.0, 1.0)) > 0.0)
        {
            r = float2(min(max((pix.z - pix.x) * uv.x + pix.x, pix.x + 0.5), pix.z + -0.5) * (1.0 / D(w)),
                       min(max((pix.w - pix.y) * uv.y + pix.y, pix.y + 0.5), pix.w + -0.5) * (1.0 / D(h)));
        }
        if (useNormalized > 0.5 && dot(nrm, float4(1.0, 1.0, 1.0, 1.0)) > 0.0)
        {
            r = float2((nrm.z - nrm.x) * uv.x + nrm.x, (nrm.w - nrm.y) * uv.y + nrm.y);
        }
        return r;
    }

    
    D LinearToSrgb1(D c)
    {
        return (c < 0.003130800090730190277099609375) ? c * 12.9200000762939453125 : pow(c, 0.4166666567325592041015625) * 1.05499994754791259765625 + -0.054999999701976776123046875;
    }
    D SrgbToLinear1(D c)
    {
        return (c < 0.040449999272823333740234375) ? c * 0.077399380505084991455078125 : pow((c + 0.054999999701976776123046875) * 0.947867333889007568359375, 2.400000095367431640625);
    }
    float3 LinearToSrgb(float3 c)
    {
        return float3(LinearToSrgb1(c.x), LinearToSrgb1(c.y), LinearToSrgb1(c.z));
    }
    float3 SrgbToLinear(float3 c)
    {
        return float3(SrgbToLinear1(c.x), SrgbToLinear1(c.y), SrgbToLinear1(c.z));
    }
    
    D Overlay1(D b, D t)
    {
        return saturate((b < 0.5) ? (b * 2.0) * t : 1.0 - ((1.0 - b) * 2.0) * (1.0 - t));
    }
    
    float3 SegmentTint(float3 baseSrgb, float3 tint)
    {
        float3 t = LinearToSrgb(saturate(tint));
        return SrgbToLinear(float3(Overlay1(baseSrgb.x, t.x), Overlay1(baseSrgb.y, t.y), Overlay1(baseSrgb.z, t.z)));
    }

    
    D EncodeReflectance(D f0)
    {
        D a = max(0.0, min(saturate(f0), 0.1599999964237213134765625));
        return saturate((a < 0.039999999105930328369140625) ? a * 16.6666660308837890625 : a * 2.77777767181396484375 + 0.5555555820465087890625);
    }

    
    D FarFade(D sceneDepth, float4 invDeviceZToWorldZ)
    {
        D f = saturate(saturate(((invDeviceZToWorldZ.y - sceneDepth) + 1.0 / -invDeviceZToWorldZ.w) * 0.0199999995529651641845703125));
        D s = (f * f) * (3.0 - f * 2.0);
        D s2 = s * s;
        D s4 = s2 * s2;
        return s4 * s4;
    }

    
    
    float3 FlowLayer(Texture2D Tex, SamplerState TexSampler, float2 uv, float2 dir, D phase, D directivity, D time, float4 gv)
    {
        D len = directivity * gv.y;
        D t = frac(phase + time * gv.x);
        float2 off = float2(len * dir.x, len * dir.y);
        float2 o = float2(t * off.x, t * off.y);
        float3 a = Texture2DSample(Tex, TexSampler, float2(uv.x - o.x, uv.y - o.y)).xyz();
        float3 b = Texture2DSample(Tex, TexSampler, float2((off.x + uv.x) - o.x, (off.y + uv.y) - o.y)).xyz();
        D c = saturate(t);
        D w = (c * c) * (3.0 - c * 2.0);
        return lerp(a, b, w);
    }

    
    
    void FlowUV(float2 uv, float2 dir, D phase, D directivity, D time, float4 gv, float2& a, float2& b, D& w)
    {
        D len = directivity * gv.y;
        D t = frac(phase + time * gv.x);
        float2 off = float2(len * dir.x, len * dir.y);
        float2 o = float2(t * off.x, t * off.y);
        a = float2(uv.x - o.x, uv.y - o.y);
        b = float2((off.x + uv.x) - o.x, (off.y + uv.y) - o.y);
        D c = saturate(t);
        w = (c * c) * (3.0 - c * 2.0);
    }

    
    D Dithered(D Coverage, D Noise)
    {
        return (Coverage > Noise * 0.99609375 + 0.001953125) ? 1.0 : -1.0;
    }
};
