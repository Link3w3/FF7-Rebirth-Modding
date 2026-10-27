// The checker's side of a transpiled shader: uniform buffers by name, texture identities, inputs and outputs by name.
#pragma once
#include "glsl_cpu.hpp"
#include <map>
#include <string>
#include <vector>

namespace cpuglsl
{
inline std::map<std::string, UBO>& Buffers()
{
    static std::map<std::string, UBO> b;
    return b;
}
inline UBO& ubo(const char* name) { return Buffers()[name]; }
struct UBOF { D _m0[4096]; };
struct UBOU { uint _m0[4096]; };
struct UBOI { int _m0[4096]; };
struct UBOUV { uvec4 _m0[1024]; };
// the scalar-layout views of a buffer: the same bytes as its vec4 view (refresh_views() copies the vec4 one into them)
inline std::map<std::string, UBOF>& ViewsF() { static std::map<std::string, UBOF> m; return m; }
inline std::map<std::string, UBOU>& ViewsU() { static std::map<std::string, UBOU> m; return m; }
inline std::map<std::string, UBOI>& ViewsI() { static std::map<std::string, UBOI> m; return m; }
inline std::map<std::string, UBOUV>& ViewsUV() { static std::map<std::string, UBOUV> m; return m; }
inline UBOF& uboF(const char* name) { return ViewsF()[name]; }
inline UBOU& uboU(const char* name) { return ViewsU()[name]; }
inline UBOI& uboI(const char* name) { return ViewsI()[name]; }
inline UBOUV& uboUV(const char* name) { return ViewsUV()[name]; }
inline void refresh_views()
{
    for (auto& [n, f] : ViewsF()) { UBO& b = ubo(n.c_str()); for (int i = 0; i < 1024; ++i) { f._m0[4*i] = b._m0[i].x; f._m0[4*i+1] = b._m0[i].y; f._m0[4*i+2] = b._m0[i].z; f._m0[4*i+3] = b._m0[i].w; } }
    for (auto& [n, f] : ViewsU()) { UBO& b = ubo(n.c_str()); for (int i = 0; i < 1024; ++i) { f._m0[4*i] = floatBitsToUint(b._m0[i].x); f._m0[4*i+1] = floatBitsToUint(b._m0[i].y); f._m0[4*i+2] = floatBitsToUint(b._m0[i].z); f._m0[4*i+3] = floatBitsToUint(b._m0[i].w); } }
    for (auto& [n, f] : ViewsI()) { UBO& b = ubo(n.c_str()); for (int i = 0; i < 1024; ++i) { f._m0[4*i] = (int)floatBitsToUint(b._m0[i].x); f._m0[4*i+1] = (int)floatBitsToUint(b._m0[i].y); f._m0[4*i+2] = (int)floatBitsToUint(b._m0[i].z); f._m0[4*i+3] = (int)floatBitsToUint(b._m0[i].w); } }
    for (auto& [n, f] : ViewsUV()) { UBO& b = ubo(n.c_str()); for (int i = 0; i < 1024; ++i) f._m0[i] = floatBitsToUint(b._m0[i]); }
}
inline uint64_t texid(const char* name)
{
    uint64_t h = 1469598103934665603ULL;
    for (const char* p = name; *p; ++p) { h = (h ^ (uint8_t)*p) * 1099511628211ULL; }
    return h;
}
inline bool g_discarded = false;
inline vec4 gl_FragCoord;
inline bool gl_FrontFacing = true;
inline int SRem(int a, int b) { return b ? a % b : 0; }
inline uint SRem(uint a, uint b) { return b ? a % b : 0; }

struct Inputs
{
    std::map<std::string, vec4> v;
    void get(const char* name, vec4& out) { out = v[name]; }
    void get(const char* name, vec3& out) { const vec4 a = v[name]; out = vec3(a.x, a.y, a.z); }
    void get(const char* name, vec2& out) { const vec4 a = v[name]; out = vec2(a.x, a.y); }
    void get(const char* name, D& out) { out = v[name].x; }
};
struct Outputs
{
    std::map<std::string, vec4> v;
    void put(const char* name, const vec4& a) { v[name] = a; }
    void put(const char* name, const vec3& a) { v[name] = vec4(a.x, a.y, a.z, D(0.0)); }
    void put(const char* name, const vec2& a) { v[name] = vec4(a.x, a.y, D(0.0), D(0.0)); }
    void put(const char* name, const D& a) { v[name] = vec4(a, D(0.0), D(0.0), D(0.0)); }
};
// the rebuild's material values as the spliced copies of the lit translucent game shaders read them (splice.py)
struct SpliceAttrs
{
    vec3 BaseColor, Normal, Emissive, Muddiness, TransmittanceLog2;
    D Metallic, Roughness, AO, Opacity, TransparencyLog2, Thickness, Foam;
};
inline SpliceAttrs g_R;
} // namespace cpuglsl

