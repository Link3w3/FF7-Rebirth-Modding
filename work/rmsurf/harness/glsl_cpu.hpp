// A CPU runtime for the decompiled game shaders (dxil-spirv's GLSL) and the rebuilt RM_Surface: every float carries its
// screen-space derivatives (d/dx, d/dy) so dFdx / dFdy are exact, and textures are smooth made-up functions of their
// coordinates (the same for the game's shader and the rebuild), so the two can be compared output for output.
#pragma once
#include <cmath>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <algorithm>
#include <string>
#include <functional>

typedef uint32_t uint;

struct D
{
    double v = 0.0, dx = 0.0, dy = 0.0;
    D() = default;
    D(double a) : v((double)(float)a) {}      // a constant is a float on the GPU
    D(float a) : v(a) {}
    D(int a) : v(a) {}
    D(uint a) : v(a) {}
    D(long a) : v((double)a) {}
    D(unsigned long a) : v((double)a) {}
    D(long long a) : v((double)a) {}
    D(unsigned long long a) : v((double)a) {}
    D(bool a) : v(a ? 1.0 : 0.0) {}
    D(double a, double b, double c) : v((double)(float)a), dx(b), dy(c) {}
    explicit operator int() const { return std::isfinite(v) ? (int)(long long)std::trunc(v) : 0; }
    explicit operator uint() const { return std::isfinite(v) ? (uint)(long long)std::trunc(v) : 0u; }
    explicit operator bool() const { return v != 0.0; }
};

// the shaders' float precision: every value rounded to float, as the GPU computes
inline double F(double x) { return (double)(float)x; }
inline D mk(double v, double dx, double dy) { return D(F(v), dx, dy); }

inline D operator+(D a, D b) { return mk(a.v + b.v, a.dx + b.dx, a.dy + b.dy); }
inline D operator-(D a, D b) { return mk(a.v - b.v, a.dx - b.dx, a.dy - b.dy); }
inline D operator-(D a) { return D(-a.v, -a.dx, -a.dy); }
inline D operator*(D a, D b) { return mk(a.v * b.v, a.dx * b.v + a.v * b.dx, a.dy * b.v + a.v * b.dy); }
inline D operator/(D a, D b)
{
    const double q = a.v / b.v;
    return mk(q, (a.dx - q * b.dx) / b.v, (a.dy - q * b.dy) / b.v);
}
inline D& operator+=(D& a, D b) { return a = a + b; }
inline D& operator-=(D& a, D b) { return a = a - b; }
inline D& operator*=(D& a, D b) { return a = a * b; }
inline D& operator/=(D& a, D b) { return a = a / b; }
inline bool operator<(D a, D b) { return a.v < b.v; }
inline bool operator>(D a, D b) { return a.v > b.v; }
inline bool operator<=(D a, D b) { return a.v <= b.v; }
inline bool operator>=(D a, D b) { return a.v >= b.v; }
inline bool operator==(D a, D b) { return a.v == b.v; }
inline bool operator!=(D a, D b) { return a.v != b.v; }

// unary functions with their derivative
template <class FN, class DFN>
inline D un(D a, FN f, DFN df)
{
    const double d = df(a.v);
    return mk(f(a.v), a.dx * d, a.dy * d);
}
inline D sqrt(D a) { return un(a, [](double x) { return std::sqrt(x); }, [](double x) { return x > 0 ? 0.5 / std::sqrt(x) : 0.0; }); }
inline D inversesqrt(D a) { return un(a, [](double x) { return 1.0 / std::sqrt(x); }, [](double x) { return x > 0 ? -0.5 * std::pow(x, -1.5) : 0.0; }); }
inline D exp2(D a) { return un(a, [](double x) { return std::exp2(x); }, [](double x) { return std::exp2(x) * std::log(2.0); }); }
inline D log2(D a) { return un(a, [](double x) { return std::log2(x); }, [](double x) { return x > 0 ? 1.0 / (x * std::log(2.0)) : 0.0; }); }
inline D abs(D a) { return a.v < 0 ? -a : a; }
inline D floor(D a) { return D(std::floor(a.v), 0, 0); }
inline D ceil(D a) { return D(std::ceil(a.v), 0, 0); }
inline D trunc(D a) { return D(std::trunc(a.v), 0, 0); }
inline D fract(D a) { return mk(a.v - std::floor(a.v), a.dx, a.dy); }
inline D roundEven(D a) { return D(std::nearbyint(a.v), 0, 0); }
inline D sin(D a) { return un(a, [](double x) { return std::sin(x); }, [](double x) { return std::cos(x); }); }
inline D cos(D a) { return un(a, [](double x) { return std::cos(x); }, [](double x) { return -std::sin(x); }); }
inline D acos(D a) { return un(a, [](double x) { return std::acos(std::clamp(x, -1.0, 1.0)); }, [](double x) { return std::fabs(x) < 1 ? -1.0 / std::sqrt(1 - x * x) : 0.0; }); }
inline D asin(D a) { return un(a, [](double x) { return std::asin(std::clamp(x, -1.0, 1.0)); }, [](double x) { return std::fabs(x) < 1 ? 1.0 / std::sqrt(1 - x * x) : 0.0; }); }
inline D atan(D a) { return un(a, [](double x) { return std::atan(x); }, [](double x) { return 1.0 / (1 + x * x); }); }
inline D atan(D y, D x)
{
    const double r = x.v * x.v + y.v * y.v;
    const double gx = r > 0 ? -y.v / r : 0, gy = r > 0 ? x.v / r : 0;
    return mk(std::atan2(y.v, x.v), gx * x.dx + gy * y.dx, gx * x.dy + gy * y.dy);
}
inline D pow(D a, D b) { return exp2(b * log2(a)); }
inline D min(D a, D b) { return a.v <= b.v ? a : b; }
inline D max(D a, D b) { return a.v >= b.v ? a : b; }
inline D clamp(D a, D lo, D hi) { return min(max(a, lo), hi); }
inline D fma(D a, D b, D c) { return a * b + c; }
inline D mix(D a, D b, D t) { return a + (b - a) * t; }
inline bool isnan(D a) { return std::isnan(a.v); }
inline bool isinf(D a) { return std::isinf(a.v); }
// GLSL.std.450 NMin / NMax / NClamp: a NaN operand gives the other
inline D spvNMin(D a, D b) { return std::isnan(a.v) ? b : std::isnan(b.v) ? a : min(a, b); }
inline D spvNMax(D a, D b) { return std::isnan(a.v) ? b : std::isnan(b.v) ? a : max(a, b); }
inline D spvNClamp(D a, D lo, D hi) { return spvNMin(spvNMax(a, lo), hi); }
inline D dFdxFine(D a) { return D(a.dx, 0, 0); }
inline D dFdyFine(D a) { return D(a.dy, 0, 0); }
inline D dFdx(D a) { return dFdxFine(a); }
inline D dFdy(D a) { return dFdyFine(a); }
inline D dFdxCoarse(D a) { return dFdxFine(a); }
inline D dFdyCoarse(D a) { return dFdyFine(a); }
inline D fwidth(D a) { return D(std::fabs(a.dx) + std::fabs(a.dy), 0, 0); }

inline uint floatBitsToUint(D a)
{
    const float f = (float)a.v;
    uint u;
    std::memcpy(&u, &f, 4);
    return u;
}
inline int floatBitsToInt(D a) { return (int)floatBitsToUint(a); }
inline D uintBitsToFloat(uint u)
{
    float f;
    std::memcpy(&f, &u, 4);
    return D((double)f);
}
inline D intBitsToFloat(int i) { return uintBitsToFloat((uint)i); }

// ---- vectors ----
#include "swizzles.inc"
struct vec3;
struct vec4;
struct vec2
{
    D x, y;
    vec2() = default;
    explicit vec2(D a) : x(a), y(a) {}
    vec2(D a, D b) : x(a), y(b) {}
    D& operator[](int i) { return i == 0 ? x : y; }
    D operator[](int i) const { return i == 0 ? x : y; }
    VEC2_SWIZZLE_DECLS
};
struct vec3
{
    D x, y, z;
    vec3() = default;
    explicit vec3(D a) : x(a), y(a), z(a) {}
    vec3(D a, D b, D c) : x(a), y(b), z(c) {}
    vec3(vec2 a, D c) : x(a.x), y(a.y), z(c) {}
    vec3(D a, vec2 b) : x(a), y(b.x), z(b.y) {}
    D& operator[](int i) { return i == 0 ? x : i == 1 ? y : z; }
    D operator[](int i) const { return i == 0 ? x : i == 1 ? y : z; }
    VEC3_SWIZZLE_DECLS
};
struct vec4
{
    D x, y, z, w;
    vec4() = default;
    explicit vec4(D a) : x(a), y(a), z(a), w(a) {}
    vec4(D a, D b, D c, D d) : x(a), y(b), z(c), w(d) {}
    vec4(vec3 a, D d) : x(a.x), y(a.y), z(a.z), w(d) {}
    vec4(vec2 a, vec2 b) : x(a.x), y(a.y), z(b.x), w(b.y) {}
    D& operator[](int i) { return i == 0 ? x : i == 1 ? y : i == 2 ? z : w; }
    D operator[](int i) const { return i == 0 ? x : i == 1 ? y : i == 2 ? z : w; }
    VEC4_SWIZZLE_DECLS
};
#include "swizzles_defs.inc"
inline D dot(vec2 a, vec2 b) { return a.x * b.x + a.y * b.y; }
inline D dot(vec3 a, vec3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
inline D dot(vec4 a, vec4 b) { return a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w; }
inline vec3 cross(vec3 a, vec3 b) { return vec3(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x); }
// (every other vector operator: hlsl_cpu.hpp's RMS_VEC_OPS, included below for both kinds of code)
#define RMS_GLSL_VEC_OPS(V, N) \
    inline V operator+(const V& a, const V& b) { V r; for (int i = 0; i < N; ++i) r[i] = a[i] + b[i]; return r; } \
    inline V operator-(const V& a, const V& b) { V r; for (int i = 0; i < N; ++i) r[i] = a[i] - b[i]; return r; } \
    inline V operator*(const V& a, const V& b) { V r; for (int i = 0; i < N; ++i) r[i] = a[i] * b[i]; return r; } \
    inline V operator/(const V& a, const V& b) { V r; for (int i = 0; i < N; ++i) r[i] = a[i] / b[i]; return r; } \
    inline V operator+(const V& a, D b) { V r; for (int i = 0; i < N; ++i) r[i] = a[i] + b; return r; } \
    inline V operator-(const V& a, D b) { V r; for (int i = 0; i < N; ++i) r[i] = a[i] - b; return r; } \
    inline V operator*(const V& a, D b) { V r; for (int i = 0; i < N; ++i) r[i] = a[i] * b; return r; } \
    inline V operator/(const V& a, D b) { V r; for (int i = 0; i < N; ++i) r[i] = a[i] / b; return r; } \
    inline V operator+(D b, const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = b + a[i]; return r; } \
    inline V operator-(D b, const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = b - a[i]; return r; } \
    inline V operator*(D b, const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = b * a[i]; return r; } \
    inline V operator/(D b, const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = b / a[i]; return r; } \
    inline V operator-(const V& a) { V r; for (int i = 0; i < N; ++i) r[i] = -a[i]; return r; } \
    inline V& operator+=(V& a, const V& b) { return a = a + b; } \
    inline V& operator-=(V& a, const V& b) { return a = a - b; } \
    inline V& operator*=(V& a, const V& b) { return a = a * b; } \
    inline V& operator/=(V& a, const V& b) { return a = a / b; } \
    inline V& operator*=(V& a, D b) { return a = a * b; } \
    inline V& operator/=(V& a, D b) { return a = a / b; } \
    inline V& operator+=(V& a, D b) { return a = a + b; } \
    inline V& operator-=(V& a, D b) { return a = a - b; }
RMS_GLSL_VEC_OPS(vec2, 2)
RMS_GLSL_VEC_OPS(vec3, 3)
RMS_GLSL_VEC_OPS(vec4, 4)
inline vec3 normalize(vec3 a) { return a * inversesqrt(dot(a, a)); }

template <class T>
struct ivec_base;
struct ivec2
{
    int x = 0, y = 0;
    ivec2() = default;
    ivec2(int a, int b) : x(a), y(b) {}
    explicit ivec2(int a) : x(a), y(a) {}
};
struct ivec3
{
    int x = 0, y = 0, z = 0;
    ivec3() = default;
    ivec3(int a, int b, int c) : x(a), y(b), z(c) {}
};
struct ivec4
{
    int x = 0, y = 0, z = 0, w = 0;
    ivec4() = default;
    ivec4(int a, int b, int c, int d) : x(a), y(b), z(c), w(d) {}
};
struct uvec2
{
    uint x = 0, y = 0;
    uvec2() = default;
    uvec2(uint a, uint b) : x(a), y(b) {}
    explicit uvec2(uint a) : x(a), y(a) {}
    explicit uvec2(ivec2 a) : x((uint)a.x), y((uint)a.y) {}
};
struct uvec3
{
    uint x = 0, y = 0, z = 0;
    uvec3() = default;
    uvec3(uint a, uint b, uint c) : x(a), y(b), z(c) {}
    explicit uvec3(ivec3 a) : x((uint)a.x), y((uint)a.y), z((uint)a.z) {}
};
struct uvec4
{
    uint x = 0, y = 0, z = 0, w = 0;
    uvec4() = default;
    uvec4(uint a, uint b, uint c, uint d) : x(a), y(b), z(c), w(d) {}
    explicit uvec4(ivec4 a) : x((uint)a.x), y((uint)a.y), z((uint)a.z), w((uint)a.w) {}
    uvec3 xyz() const { return uvec3(x, y, z); }
};
inline ivec2 ivec2_(uvec2 a) { return ivec2((int)a.x, (int)a.y); }
inline ivec3 ivec3_(uvec3 a) { return ivec3((int)a.x, (int)a.y, (int)a.z); }
inline uvec4 floatBitsToUint(vec4 a) { return uvec4(floatBitsToUint(a.x), floatBitsToUint(a.y), floatBitsToUint(a.z), floatBitsToUint(a.w)); }
inline uvec3 floatBitsToUint(vec3 a) { return uvec3(floatBitsToUint(a.x), floatBitsToUint(a.y), floatBitsToUint(a.z)); }

// ---- resources ----
struct Tex2D { uint64_t id = 0; };
struct Tex3D { uint64_t id = 0; };
struct TexBuf { uint64_t id = 0; };
struct Samp { uint64_t id = 0; };
struct Sampler2D { Tex2D t; Samp s; };
struct Sampler3D { Tex3D t; Samp s; };
inline Sampler2D sampler2D(Tex2D t, Samp s) { return Sampler2D{t, s}; }
inline Sampler3D sampler3D(Tex3D t, Samp s) { return Sampler3D{t, s}; }

// The made-up textures: per texture id, four smooth channels in [0.05, 0.95] (each a sum of two waves of the coordinates).
inline std::function<uint64_t(uint64_t)> TextureAlias;   // the harness: two names of the same texture -> one id
inline uint64_t mixid(uint64_t h)
{
    h ^= h >> 33; h *= 0xff51afd7ed558ccdULL; h ^= h >> 33; h *= 0xc4ceb9fe1a85ec53ULL; h ^= h >> 33;
    return h;
}
inline double hashf(uint64_t h, int k) { return (double)(mixid(h * 31 + k) % 100000) / 100000.0; }
// textures that are one colour everywhere (the material's default textures, bound where a texture parameter is off)
#include <unordered_map>
inline std::unordered_map<uint64_t, vec4>& ConstantTextures() { static std::unordered_map<uint64_t, vec4> m; return m; }
inline vec4 texture(Sampler2D s, vec2 uv)
{
    const uint64_t id = TextureAlias ? TextureAlias(s.t.id) : s.t.id;
    {
        auto it = ConstantTextures().find(id);
        if (it != ConstantTextures().end()) return it->second;
    }
    D out[4];
    for (int k = 0; k < 4; ++k)
    {
        const double a = 1.0 + 6.0 * hashf(id, k), b = 1.0 + 6.0 * hashf(id, k + 4), c = 6.283 * hashf(id, k + 8);
        const double a2 = 1.0 + 9.0 * hashf(id, k + 12), b2 = 1.0 + 9.0 * hashf(id, k + 16), c2 = 6.283 * hashf(id, k + 20);
        const D ph = uv.x * D(a) + uv.y * D(b) + D(c);
        const D ph2 = uv.x * D(a2) - uv.y * D(b2) + D(c2);
        out[k] = D(0.5) + D(0.3) * sin(ph) + D(0.15) * sin(ph2);
    }
    return vec4(out[0], out[1], out[2], out[3]);
}
inline vec4 texture(Sampler2D s, vec2 uv, D) { return texture(s, uv); }
inline vec4 textureLod(Sampler2D s, vec2 uv, D) { return texture(s, uv); }
inline vec4 textureGrad(Sampler2D s, vec2 uv, vec2, vec2) { return texture(s, uv); }
inline vec4 texture(Sampler3D s, vec3 p) { return texture(Sampler2D{Tex2D{s.t.id}, s.s}, vec2(p.x + p.z * 0.37, p.y - p.z * 0.21)); }
inline vec4 texture(Sampler3D s, vec3 p, D) { return texture(s, p); }
inline vec4 textureLod(Sampler3D s, vec3 p, D) { return texture(s, p); }
// fetches: per integer texel, made-up values (no derivatives)
inline vec4 texelFetch(Tex3D t, ivec3 p, int)
{
    const uint64_t h = mixid(t.id * 1000003ULL + (uint64_t)(p.x & 1023) * 1048576ULL + (uint64_t)(p.y & 1023) * 1024ULL + (uint64_t)(p.z & 1023));
    return vec4(D(hashf(h, 0)), D(hashf(h, 1)), D(hashf(h, 2)), D(hashf(h, 3)));
}
inline vec4 texelFetch(Tex2D t, ivec2 p, int)
{
    const uint64_t h = mixid(t.id * 1000003ULL + (uint64_t)(p.x & 4095) * 4096ULL + (uint64_t)(p.y & 4095));
    return vec4(D(hashf(h, 0)), D(hashf(h, 1)), D(hashf(h, 2)), D(hashf(h, 3)));
}

struct UBO
{
    vec4 _m0[1024];
};


// ---- more of GLSL ----
inline double halfToDouble(uint16_t h)
{
    const int s = (h >> 15) & 1, e = (h >> 10) & 31, m = h & 1023;
    double v;
    if (e == 0) { v = std::ldexp((double)m, -24); }
    else if (e == 31) { v = m ? NAN : INFINITY; }
    else { v = std::ldexp((double)(m | 1024), e - 25); }
    return s ? -v : v;
}
inline vec2 unpackHalf2x16(uint u) { return vec2(D(halfToDouble((uint16_t)(u & 0xffff))), D(halfToDouble((uint16_t)(u >> 16)))); }
inline ivec2 textureSize(Tex2D t, int lod)
{
    const int s = 256 << (int)(t.id % 4);
    return ivec2(std::max(1, s >> lod), std::max(1, s >> lod));
}
inline ivec3 textureSize(Tex3D t, int lod) { const int s = 64 >> lod; return ivec3(s, s, s); }
struct TexBufF { uint64_t id = 0; };
struct TexBufU { uint64_t id = 0; };
struct TexBufI { uint64_t id = 0; };
inline vec4 texelFetch(TexBufF b, int i) { const uint64_t h = mixid(b.id * 7919ULL + (uint64_t)i); return vec4(D(hashf(h, 0)), D(hashf(h, 1)), D(hashf(h, 2)), D(hashf(h, 3))); }
inline uvec4 texelFetch(TexBufU b, int i) { const uint64_t h = mixid(b.id * 7919ULL + (uint64_t)i); return uvec4((uint)(h & 3), (uint)((h >> 8) & 3), (uint)((h >> 16) & 3), (uint)((h >> 24) & 3)); }
inline ivec4 texelFetch(TexBufI b, int i) { const uint64_t h = mixid(b.id * 7919ULL + (uint64_t)i); return ivec4((int)(h & 3), (int)((h >> 8) & 3), (int)((h >> 16) & 3), (int)((h >> 24) & 3)); }
inline uint min(uint a, uint b) { return a < b ? a : b; }
inline uint max(uint a, uint b) { return a > b ? a : b; }
inline int min(int a, int b) { return a < b ? a : b; }
inline int max(int a, int b) { return a > b ? a : b; }
inline uint clamp(uint a, uint lo, uint hi) { return min(max(a, lo), hi); }
inline int clamp(int a, int lo, int hi) { return min(max(a, lo), hi); }
inline vec4 textureGather(Sampler2D s, vec2 uv) { const vec4 a = texture(s, uv); return vec4(a.x, a.y, a.z, a.w); }
inline vec4 textureGather(Sampler2D s, vec2 uv, int) { return textureGather(s, uv); }
inline vec4 textureGatherOffset(Sampler2D s, vec2 uv, ivec2 o) { return textureGather(s, vec2(uv.x + D(o.x * 0.001), uv.y + D(o.y * 0.001))); }
inline vec4 textureGatherOffset(Sampler2D s, vec2 uv, ivec2 o, int) { return textureGatherOffset(s, uv, o); }
