// Runtime for shaders translated from D3D11 (SM5) assembly by dxbc2cpp.py, for the material checker.
// A register lane keeps its exact 32 bits (integer instructions read and write those) and its float value with its
// screen-space derivatives (glsl_cpu.hpp's D: float instructions, deriv_rtx/rty, the made-up textures).
#pragma once
#include "glsl_cpu.hpp"
#include <array>
#include <vector>
#include <cstring>

struct Lane
{
    D f;
    uint32_t b = 0;
};

inline uint32_t bitsOf(float x) { uint32_t u; std::memcpy(&u, &x, 4); return u; }
inline float floatOf(uint32_t u) { float x; std::memcpy(&x, &u, 4); return x; }
// a float result: the value rounded to float (D already is), its bits from that float
inline Lane LF(D x)
{
    Lane l;
    const float v = (float)x.v;
    l.b = bitsOf(v);
    l.f = std::isnan(v) ? D(x.v, 0, 0) : D((double)v, x.dx, x.dy);
    return l;
}
// an integer result: the bits; its float view without derivatives
inline Lane LU(uint32_t u)
{
    Lane l;
    l.b = u;
    l.f = D((double)floatOf(u), 0, 0);
    return l;
}
inline Lane LI(int32_t i) { return LU((uint32_t)i); }
// a literal from the shader (its exact bits)
inline Lane LB(uint32_t u) { return LU(u); }
inline D FB(uint32_t u) { return D((double)floatOf(u), 0, 0); }

// D3D float semantics
inline D sat_(D a) { if (std::isnan(a.v) || a.v <= 0.0) return D(0.0, 0, 0); if (a.v >= 1.0) return D(1.0, 0, 0); return a; }
inline D abs_(D a) { return a.v < 0 || (a.v == 0 && std::signbit(a.v)) ? D(-a.v, -a.dx, -a.dy) : a; }
inline D neg_(D a) { return D(-a.v, -a.dx, -a.dy); }
inline D min_(D a, D b) { if (std::isnan(a.v)) return b; if (std::isnan(b.v)) return a; return a.v < b.v ? a : b; }
inline D max_(D a, D b) { if (std::isnan(a.v)) return b; if (std::isnan(b.v)) return a; return a.v >= b.v ? a : b; }
inline D add_(D a, D b) { return a + b; }
inline D mul_(D a, D b) { return a * b; }
inline D mad_(D a, D b, D c) { return a * b + c; }
inline D div_(D a, D b) { return a / b; }
inline D sqrt_(D a) { return sqrt(a); }
inline D rsq_(D a) { return inversesqrt(a); }
inline D rcp_(D a) { return D(1.0) / a; }
inline D exp_(D a) { return exp2(a); }
inline D log_(D a) { return log2(a); }
inline D frc_(D a) { return fract(a); }
inline D round_ne_(D a) { return D(std::nearbyint(a.v), 0, 0); }
inline D round_ni_(D a) { return D(std::floor(a.v), 0, 0); }
inline D round_pi_(D a) { return D(std::ceil(a.v), 0, 0); }
inline D round_z_(D a) { return D(std::trunc(a.v), 0, 0); }
inline D sin_(D a) { return sin(a); }
inline D cos_(D a) { return cos(a); }
inline D dx_(D a) { return D(a.dx, 0, 0); }
inline D dy_(D a) { return D(a.dy, 0, 0); }
inline uint32_t lt_(D a, D b) { return a.v < b.v ? 0xffffffffu : 0u; }
inline uint32_t ge_(D a, D b) { return a.v >= b.v ? 0xffffffffu : 0u; }
inline uint32_t eq_(D a, D b) { return a.v == b.v ? 0xffffffffu : 0u; }
inline uint32_t ne_(D a, D b) { return a.v != b.v ? 0xffffffffu : 0u; }   // NaN != NaN is true
// conversions as D3D defines them: NaN -> 0, saturating at the integer range
inline uint32_t ftoi_(D a)
{
    const double v = (double)(float)a.v;
    if (std::isnan(v)) return 0;
    if (v >= 2147483647.0) return 0x7fffffffu;
    if (v <= -2147483648.0) return 0x80000000u;
    return (uint32_t)(int32_t)std::trunc(v);
}
inline uint32_t ftou_(D a)
{
    const double v = (double)(float)a.v;
    if (std::isnan(v) || v <= 0.0) return 0;
    if (v >= 4294967295.0) return 0xffffffffu;
    return (uint32_t)std::trunc(v);
}
inline D itof_(uint32_t u) { return D((double)(float)(int32_t)u, 0, 0); }
inline D utof_(uint32_t u) { return D((double)(float)u, 0, 0); }
inline uint32_t f32tof16_(D a)
{
    const float f = (float)a.v;
    uint32_t x = bitsOf(f);
    const uint32_t s = (x >> 16) & 0x8000u;
    int e = (int)((x >> 23) & 0xff) - 127 + 15;
    uint32_t m = x & 0x7fffffu;
    if (((x >> 23) & 0xff) == 0xff) return s | 0x7c00u | (m ? 0x200u : 0u);
    if (e >= 31) return s | 0x7c00u;
    if (e <= 0)
    {
        if (e < -10) return s;
        m |= 0x800000u;
        const int sh = 14 - e;
        uint32_t h = m >> sh;
        const uint32_t rem = m & ((1u << sh) - 1), half = 1u << (sh - 1);
        if (rem > half || (rem == half && (h & 1))) ++h;
        return s | h;
    }
    uint32_t h = (uint32_t)(e << 10) | (m >> 13);
    const uint32_t rem = m & 0x1fffu;
    if (rem > 0x1000u || (rem == 0x1000u && (h & 1))) ++h;
    return s | h;
}
inline D f16tof32_(uint32_t u) { return D(halfToDouble((uint16_t)(u & 0xffff)), 0, 0); }
inline uint32_t ishl_(uint32_t a, uint32_t b) { return a << (b & 31); }
inline uint32_t ushr_(uint32_t a, uint32_t b) { return a >> (b & 31); }
inline uint32_t ishr_(uint32_t a, uint32_t b) { return (uint32_t)((int32_t)a >> (b & 31)); }
inline uint32_t imin_(uint32_t a, uint32_t b) { return (int32_t)a < (int32_t)b ? a : b; }
inline uint32_t imax_(uint32_t a, uint32_t b) { return (int32_t)a > (int32_t)b ? a : b; }
inline uint32_t umin_(uint32_t a, uint32_t b) { return a < b ? a : b; }
inline uint32_t umax_(uint32_t a, uint32_t b) { return a > b ? a : b; }
inline uint32_t ilt_(uint32_t a, uint32_t b) { return (int32_t)a < (int32_t)b ? 0xffffffffu : 0u; }
inline uint32_t ige_(uint32_t a, uint32_t b) { return (int32_t)a >= (int32_t)b ? 0xffffffffu : 0u; }
inline uint32_t ult_(uint32_t a, uint32_t b) { return a < b ? 0xffffffffu : 0u; }
inline uint32_t uge_(uint32_t a, uint32_t b) { return a >= b ? 0xffffffffu : 0u; }
inline uint32_t ieq_(uint32_t a, uint32_t b) { return a == b ? 0xffffffffu : 0u; }
inline uint32_t ine_(uint32_t a, uint32_t b) { return a != b ? 0xffffffffu : 0u; }
inline uint32_t udiv_q(uint32_t a, uint32_t b) { return b ? a / b : 0xffffffffu; }
inline uint32_t udiv_r(uint32_t a, uint32_t b) { return b ? a % b : 0xffffffffu; }
inline uint32_t bfi_(uint32_t w, uint32_t o, uint32_t ins, uint32_t base)
{
    w &= 31; o &= 31;
    const uint32_t mask = (w == 0 ? 0u : ((w == 32 ? 0xffffffffu : ((1u << w) - 1)) << o));
    return ((ins << o) & mask) | (base & ~mask);
}
inline uint32_t ubfe_(uint32_t w, uint32_t o, uint32_t v)
{
    w &= 31; o &= 31;
    if (w == 0) return 0;
    if (w + o < 32) return (v << (32 - w - o)) >> (32 - w);
    return v >> o;
}
inline uint32_t ibfe_(uint32_t w, uint32_t o, uint32_t v)
{
    w &= 31; o &= 31;
    if (w == 0) return 0;
    if (w + o < 32) return (uint32_t)(((int32_t)(v << (32 - w - o))) >> (32 - w));
    return (uint32_t)((int32_t)v >> o);
}
inline uint32_t countbits_(uint32_t v) { return (uint32_t)__builtin_popcount(v); }
inline uint32_t bfrev_(uint32_t v) { uint32_t r = 0; for (int i = 0; i < 32; ++i) if (v & (1u << i)) r |= 1u << (31 - i); return r; }
inline uint32_t firstbit_hi_(uint32_t v) { return v ? (uint32_t)__builtin_clz(v) : 0xffffffffu; }
inline uint32_t firstbit_lo_(uint32_t v) { return v ? (uint32_t)__builtin_ctz(v) : 0xffffffffu; }
inline uint32_t firstbit_shi_(uint32_t v) { if ((int32_t)v < 0) v = ~v; return v ? (uint32_t)__builtin_clz(v) : 0xffffffffu; }

// What a translated shader reads and writes.
struct DXIO
{
    Lane v[40][4];                                // inputs (v#), by register
    Lane o[10][4];                                // outputs (o#)
    Lane oDepth;
    std::vector<std::array<uint32_t, 4>> cb[16];  // constant buffers: CB#[i] as raw bits
    uint64_t tex[128] = {};                       // t#: made-up texture identities
    uint64_t samp[16] = {};
    uint32_t coverage = 0xffffffffu;
    bool front = true;
    bool discarded = false;
    std::vector<std::array<uint32_t, 4>> icb;
    std::vector<std::array<uint32_t, 4>> buf[128];  // t#: a buffer's rows (the driver's), else made-up texels
};
inline D cbF(DXIO& io, int b, int i, int c)
{
    if (i < 0 || i >= (int)io.cb[b].size()) return D(0.0, 0, 0);
    return D((double)floatOf(io.cb[b][i][c]), 0, 0);
}
inline uint32_t cbU(DXIO& io, int b, int i, int c) { return (i < 0 || i >= (int)io.cb[b].size()) ? 0u : io.cb[b][i][c]; }
inline Lane cbL(DXIO& io, int b, int i, int c) { return LU(cbU(io, b, i, c)); }

// textures: the harness's made-up functions (same for the game's shader and the rebuild)
inline vec4 tex2d(DXIO& io, int t, int s, D u, D v) { return texture(Sampler2D{Tex2D{io.tex[t]}, Samp{io.samp[s]}}, vec2(u, v)); }
inline vec4 tex3d(DXIO& io, int t, int s, D u, D v, D w) { return texture(Sampler3D{Tex3D{io.tex[t]}, Samp{io.samp[s]}}, vec3(u, v, w)); }
inline vec4 texcube(DXIO& io, int t, int s, D x, D y, D z)
{
    // a smooth made-up function of the direction (its length doesn't matter, as a cube map's)
    const D l = inversesqrt(x * x + y * y + z * z);
    return texture(Sampler2D{Tex2D{io.tex[t] ^ 0x5bd1e995ULL}, Samp{io.samp[s]}}, vec2(x * l + z * l * D(0.5), y * l - z * l * D(0.25)));
}
inline vec4 tex2darr(DXIO& io, int t, int s, D u, D v, D a)
{
    return texture(Sampler2D{Tex2D{io.tex[t] + (uint64_t)std::llround(std::max(0.0, a.v)) * 0x9e3779b97f4a7c15ULL}, Samp{io.samp[s]}}, vec2(u, v));
}
// a cube array: the cube's function of the direction, one per array slice
inline vec4 texcubearr(DXIO& io, int t, int s, D x, D y, D z, D a)
{
    const D l = inversesqrt(x * x + y * y + z * z);
    const uint64_t id = (io.tex[t] ^ 0x5bd1e995ULL) + (uint64_t)std::llround(std::max(0.0, a.v)) * 0x9e3779b97f4a7c15ULL;
    return texture(Sampler2D{Tex2D{id}, Samp{io.samp[s]}}, vec2(x * l + z * l * D(0.5), y * l - z * l * D(0.25)));
}
inline vec4 fetch2d(DXIO& io, int t, uint32_t x, uint32_t y, uint32_t lod) { (void)lod; return texelFetch(Tex2D{io.tex[t]}, ivec2((int)x, (int)y), 0); }
inline vec4 fetch3d(DXIO& io, int t, uint32_t x, uint32_t y, uint32_t z, uint32_t lod) { (void)lod; return texelFetch(Tex3D{io.tex[t]}, ivec3((int)x, (int)y, (int)z), 0); }
inline vec4 fetchbuf(DXIO& io, int t, uint32_t i) { return texelFetch(TexBufF{io.tex[t]}, (int)i); }
inline std::array<uint32_t, 4> fetchbufU(DXIO& io, int t, uint32_t i)
{
    const auto& b = io.buf[t];
    if (!b.empty()) return b[i % b.size()];
    const vec4 x = texelFetch(TexBufF{io.tex[t]}, (int)i);
    return {bitsOf((float)x.x.v), bitsOf((float)x.y.v), bitsOf((float)x.z.v), bitsOf((float)x.w.v)};
}
inline void size2d(DXIO& io, int t, uint32_t lod, uint32_t& w, uint32_t& h, uint32_t& levels)
{
    const ivec2 s = textureSize(Tex2D{io.tex[t]}, (int)lod);
    w = (uint32_t)s.x; h = (uint32_t)s.y; levels = 9;
}
inline uint32_t iabs_(uint32_t a) { return (int32_t)a < 0 ? 0u - a : a; }
// sample_c / gather4_c: the comparison against the reference (1 where it passes)
inline vec4 cmp4_(vec4 r, D ref)
{
    auto c = [&](D a) { return D(ref.v <= a.v ? 1.0 : 0.0, 0, 0); };
    return vec4(c(r.x), c(r.y), c(r.z), c(r.w));
}
