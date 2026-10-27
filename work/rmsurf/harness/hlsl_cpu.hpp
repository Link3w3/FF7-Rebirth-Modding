// The checker's side of the rebuilt RM_Surface: just enough of HLSL (UE flavour) over glsl_cpu.hpp's derivative-carrying
// floats that the rebuild's .ush compiles as C++ after hlsl2cpp.py (swizzle reads become calls, out/inout become refs).
#pragma once
#include "glsl_cpu.hpp"
#include "harness.hpp"

namespace hlslcpu
{
using cpuglsl::texid;
typedef D float1;
typedef vec2 float2;
typedef vec3 float3;
typedef vec4 float4;
typedef D half;
typedef vec2 half2;
typedef vec3 half3;
typedef vec4 half4;
typedef ivec2 int2;
typedef ivec3 int3;
typedef ivec4 int4;
typedef uvec2 uint2;
typedef uvec3 uint3;
typedef uvec4 uint4;
typedef D MaterialFloat;
typedef vec2 MaterialFloat2;
typedef vec3 MaterialFloat3;
typedef vec4 MaterialFloat4;
}

// ---- vector arithmetic (every mix of vector / scalar) ----
#define RMS_VEC_OPS(V, N)                                                                                          \
    inline V vmap(const V& a, D (*f)(D)) { V r; for (int i = 0; i < N; ++i) r[i] = f(a[i]); return r; }        \
    inline D dot_(const V& a, const V& b) { D s = a[0] * b[0]; for (int i = 1; i < N; ++i) s = s + a[i] * b[i]; return s; } \
    inline V min(const V& a, const V& b) { V r; for (int i = 0; i < N; ++i) r[i] = min(a[i], b[i]); return r; }   \
    inline V max(const V& a, const V& b) { V r; for (int i = 0; i < N; ++i) r[i] = max(a[i], b[i]); return r; }   \
    inline V min(const V& a, D b) { V r; for (int i = 0; i < N; ++i) r[i] = min(a[i], b); return r; }             \
    inline V max(const V& a, D b) { V r; for (int i = 0; i < N; ++i) r[i] = max(a[i], b); return r; }             \
    inline V clamp(const V& a, const V& lo, const V& hi) { V r; for (int i = 0; i < N; ++i) r[i] = clamp(a[i], lo[i], hi[i]); return r; } \
    inline V clamp(const V& a, D lo, D hi) { V r; for (int i = 0; i < N; ++i) r[i] = clamp(a[i], lo, hi); return r; } \
    inline V lerp(const V& a, const V& b, const V& t) { V r; for (int i = 0; i < N; ++i) r[i] = a[i] + (b[i] - a[i]) * t[i]; return r; } \
    inline V lerp(const V& a, const V& b, D t) { V r; for (int i = 0; i < N; ++i) r[i] = a[i] + (b[i] - a[i]) * t; return r; } \
    inline V pow(const V& a, const V& b) { V r; for (int i = 0; i < N; ++i) r[i] = pow(a[i], b[i]); return r; }   \
    inline V pow(const V& a, D b) { V r; for (int i = 0; i < N; ++i) r[i] = pow(a[i], b); return r; }             \
    inline V step(const V& e, const V& x) { V r; for (int i = 0; i < N; ++i) r[i] = D(x[i].v >= e[i].v ? 1.0 : 0.0); return r; }

RMS_VEC_OPS(vec2, 2)
RMS_VEC_OPS(vec3, 3)
RMS_VEC_OPS(vec4, 4)

inline D lerp(D a, D b, D t) { return a + (b - a) * t; }
inline D saturate(D a) { return clamp(a, D(0.0), D(1.0)); }
inline D frac(D a) { return fract(a); }
inline D rsqrt(D a) { return inversesqrt(a); }
inline D rcp(D a) { return D(1.0) / a; }
inline D sign(D a) { return D(a.v > 0 ? 1.0 : a.v < 0 ? -1.0 : 0.0); }
inline D step(D e, D x) { return D(x.v >= e.v ? 1.0 : 0.0); }
inline D smoothstep(D a, D b, D x) { const D t = saturate((x - a) / (b - a)); return t * t * (D(3.0) - D(2.0) * t); }
inline D exp(D a) { return exp2(a * D(1.4426950408889634)); }
inline D log(D a) { return log2(a) * D(0.6931471805599453); }
inline D tan(D a) { return sin(a) / cos(a); }
inline D atan2(D y, D x) { return atan(y, x); }
inline D round(D a) { return roundEven(a); }
inline D fmod(D a, D b) { return a - b * trunc(a / b); }
inline D ddx(D a) { return dFdxFine(a); }
inline D ddy(D a) { return dFdyFine(a); }
inline D ddx_fine(D a) { return dFdxFine(a); }
inline D ddy_fine(D a) { return dFdyFine(a); }
inline D length(D a) { return abs(a); }
inline D asfloat(uint u) { return uintBitsToFloat(u); }
inline uint asuint(D a) { return floatBitsToUint(a); }
inline D dot(D a, D b) { return a * b; }
inline D f16tof32(uint u) { return unpackHalf2x16(u).x; }

#define RMS_VEC_FUNCS(V, N)                                                                                \
    inline V saturate(const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = saturate(a[i]); return r; }   \
    inline V frac(const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = fract(a[i]); return r; }          \
    inline V fract(const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = fract(a[i]); return r; }         \
    inline V abs(const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = abs(a[i]); return r; }             \
    inline V sqrt(const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = sqrt(a[i]); return r; }           \
    inline V rsqrt(const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = inversesqrt(a[i]); return r; }   \
    inline V floor(const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = floor(a[i]); return r; }         \
    inline V ceil(const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = ceil(a[i]); return r; }           \
    inline V round(const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = roundEven(a[i]); return r; }    \
    inline V exp2(const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = exp2(a[i]); return r; }           \
    inline V log2(const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = log2(a[i]); return r; }           \
    inline V sin(const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = sin(a[i]); return r; }             \
    inline V cos(const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = cos(a[i]); return r; }             \
    inline V sign(const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = sign(a[i]); return r; }           \
    inline V ddx(const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = dFdxFine(a[i]); return r; }        \
    inline V ddy(const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = dFdyFine(a[i]); return r; }        \
    inline V ddx_fine(const V& a) { return ddx(a); }                                                       \
    inline V ddy_fine(const V& a) { return ddy(a); }                                                       \
    inline D length(const V& a) { return sqrt(dot_(a, a)); }                                               \
    inline V normalize(const V& a) { return a * inversesqrt(dot_(a, a)); }

RMS_VEC_FUNCS(vec2, 2)
RMS_VEC_FUNCS(vec4, 4)
// vec3: glsl_cpu.hpp already has dot / cross / normalize for vec3
inline vec3 saturate(const vec3& a) { return vec3(saturate(a.x), saturate(a.y), saturate(a.z)); }
inline vec3 frac(const vec3& a) { return vec3(fract(a.x), fract(a.y), fract(a.z)); }
inline vec3 fract(const vec3& a) { return frac(a); }
inline vec3 abs(const vec3& a) { return vec3(abs(a.x), abs(a.y), abs(a.z)); }
inline vec3 sqrt(const vec3& a) { return vec3(sqrt(a.x), sqrt(a.y), sqrt(a.z)); }
inline vec3 rsqrt(const vec3& a) { return vec3(inversesqrt(a.x), inversesqrt(a.y), inversesqrt(a.z)); }
inline vec3 floor(const vec3& a) { return vec3(floor(a.x), floor(a.y), floor(a.z)); }
inline vec3 ceil(const vec3& a) { return vec3(ceil(a.x), ceil(a.y), ceil(a.z)); }
inline vec3 round(const vec3& a) { return vec3(roundEven(a.x), roundEven(a.y), roundEven(a.z)); }
inline vec3 exp2(const vec3& a) { return vec3(exp2(a.x), exp2(a.y), exp2(a.z)); }
inline vec3 log2(const vec3& a) { return vec3(log2(a.x), log2(a.y), log2(a.z)); }
inline vec3 sin(const vec3& a) { return vec3(sin(a.x), sin(a.y), sin(a.z)); }
inline vec3 cos(const vec3& a) { return vec3(cos(a.x), cos(a.y), cos(a.z)); }
inline vec3 sign(const vec3& a) { return vec3(sign(a.x), sign(a.y), sign(a.z)); }
inline vec3 ddx(const vec3& a) { return vec3(dFdxFine(a.x), dFdxFine(a.y), dFdxFine(a.z)); }
inline vec3 ddy(const vec3& a) { return vec3(dFdyFine(a.x), dFdyFine(a.y), dFdyFine(a.z)); }
inline vec3 ddx_fine(const vec3& a) { return ddx(a); }
inline vec3 ddy_fine(const vec3& a) { return ddy(a); }
inline D length(const vec3& a) { return sqrt(dot(a, a)); }
inline D distance(const vec3& a, const vec3& b) { return length(a - b); }
inline vec3 reflect(const vec3& i, const vec3& n) { return i - n * (D(2.0) * dot(n, i)); }

// ---- matrices (rows, as UE's float3x3 TangentToWorld) ----
struct float3x3
{
    vec3 r[3];
    float3x3() = default;
    float3x3(vec3 a, vec3 b, vec3 c) { r[0] = a; r[1] = b; r[2] = c; }
    vec3& operator[](int i) { return r[i]; }
    const vec3& operator[](int i) const { return r[i]; }
};
inline vec3 mul(const vec3& v, const float3x3& m) { return m.r[0] * v.x + m.r[1] * v.y + m.r[2] * v.z; }
inline vec3 mul(const float3x3& m, const vec3& v) { return vec3(dot(m.r[0], v), dot(m.r[1], v), dot(m.r[2], v)); }

// ---- textures: UE's Texture2DSample family over the made-up textures ----
struct Texture2D
{
    Tex2D t;
    void GetDimensions(uint& w, uint& h) const { const ivec2 s = textureSize(t, 0); w = (uint)s.x; h = (uint)s.y; }
    vec4 Load(ivec3 p) const { return texelFetch(t, ivec2(p.x, p.y), p.z); }
};
struct SamplerState { Samp s; };
struct Texture3D { Tex3D t; vec4 Load(ivec4 p) const { return texelFetch(t, ivec3(p.x, p.y, p.z), p.w); } };
inline vec4 Texture3DSample(const Texture3D& t, const SamplerState& s, vec3 p) { return texture(sampler3D(t.t, s.s), p); }
inline vec4 Texture2DSample(const Texture2D& t, const SamplerState& s, vec2 uv) { return texture(sampler2D(t.t, s.s), uv); }
inline vec4 Texture2DSampleBias(const Texture2D& t, const SamplerState& s, vec2 uv, D) { return Texture2DSample(t, s, uv); }
inline vec4 Texture2DSampleLevel(const Texture2D& t, const SamplerState& s, vec2 uv, D) { return Texture2DSample(t, s, uv); }
inline vec4 Texture2DSampleGrad(const Texture2D& t, const SamplerState& s, vec2 uv, vec2, vec2) { return Texture2DSample(t, s, uv); }
inline Texture2D MakeTexture(const char* name) { return Texture2D{Tex2D{cpuglsl::texid(name)}}; }

// HLSL scalar casts on vectors and select()
inline vec3 select3(bool c, vec3 a, vec3 b) { return c ? a : b; }
