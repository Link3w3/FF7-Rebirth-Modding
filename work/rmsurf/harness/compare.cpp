// The checker: every chosen game permutation against the rebuilt RM_Surface, on the same random pixels.
//   compare [-n cases] [-seed s] [-v] [name filters...]
// For each case: random View / Primitive / material parameters and interpolants; the game's shader runs; the rebuild
// runs (rms::evaluate) and the game's base pass is applied to it (basepass::encode); the seven targets are compared.
#include "rb/basepass.hpp"
#include <random>
#include <vector>
#include <string>
#include <map>
#include <cstring>

struct GameShader
{
    const char* name;
    const char* ns;
    void (*run)();
    void (*set_inputs)(cpuglsl::Inputs&);
    void (*get_outputs)(cpuglsl::Outputs&);
    const char* material_ubo;
    std::vector<std::string> switches;
    void (*fill_material)(UBO&, const vec4*, const D*);
    const char* vf;
    const char* translucent_ubo;
    bool clip;   // the instance's blend mode applies the opacity mask (masked, translucent)
    void (*srun)();   // the lit translucent ones: the spliced copy (splice.py), the game's lighting on the rebuild's values
    void (*sset_inputs)(cpuglsl::Inputs&);
    void (*sget_outputs)(cpuglsl::Outputs&);
};
extern std::vector<GameShader> g_shaders;

using namespace cpuglsl;

static std::mt19937_64 rng;
static double U(double a, double b) { return a + (b - a) * std::uniform_real_distribution<double>(0, 1)(rng); }
static D RD(double a, double b, double s) { return D(F(U(a, b)), U(-s, s), U(-s, s)); }
static vec3 unit(double s)
{
    vec3 v;
    do { v = vec3(D(U(-1, 1)), D(U(-1, 1)), D(U(-1, 1))); } while (dot(v, v).v < 0.05 || dot(v, v).v > 1.0);
    const double r = 1.0 / std::sqrt(dot(v, v).v);
    return vec3(D(F(v.x.v * r), U(-s, s), U(-s, s)), D(F(v.y.v * r), U(-s, s), U(-s, s)), D(F(v.z.v * r), U(-s, s), U(-s, s)));
}

struct Stat
{
    int cases = 0, discard_mismatch = 0, discarded = 0;
    double maxerr[7][4] = {};
    int bad[7][4] = {};
    std::string first;
    bool spliced = false;
    int tested[12] = {};   // spliced: the cases in which each material value moved the result
    double lo[12], hi[12];
    Stat() { for (int k = 0; k < 12; ++k) { lo[k] = 1e30; hi[k] = -1e30; } }
};
static const char* tn_[7] = {"SV_Target", "SV_Target_1", "SV_Target_2", "SV_Target_3", "SV_Target_4", "SV_Target_5", "SV_Target_6"};

static const char* TNAME[7] = {"T0 emissive", "T1 normal", "T2 metal/spec/rough/model", "T3 color/ao", "T4 custom", "T5 normal8", "T6 velocity"};

int main(int argc, char** argv)
{
    int ncases = 200;
    uint64_t seed = 1;
    bool verbose = false;
    std::vector<std::string> filters;
    for (int i = 1; i < argc; ++i)
    {
        if (!strcmp(argv[i], "-n")) ncases = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-seed")) seed = strtoull(argv[++i], 0, 10);
        else if (!strcmp(argv[i], "-v")) verbose = true;
        else filters.push_back(argv[i]);
    }
    // the master's default textures (its ReferencedTextures, in order): what a shader's unnamed texture slots hold
    {
        auto srgb = [](double c) { return c <= 0.04045 ? c / 12.92 : std::pow((c + 0.055) / 1.055, 2.4); };
        auto b = [](int v) { return v / 255.0; };
        const vec4 defaults[13] = {
            vec4(D(srgb(b(0x76))), D(srgb(b(0x76))), D(srgb(b(0x76))), D(1.0)),   // 767676FF_sRGB
            vec4(D(0.0), D(0.0), D(0.0), D(1.0)),                                  // 000000FF_BC4
            vec4(D(b(0x80)), D(0.0), D(0.0), D(1.0)),                              // 808080FF_BC4
            vec4(D(0.0), D(0.0), D(0.0), D(1.0)),                                  // 000000FF_HDR
            vec4(D(b(0x80)), D(b(0x80)), D(0.0), D(1.0)),                          // 8080FFFF_BC5
            vec4(D(1.0), D(0.0), D(0.0), D(1.0)),                                  // FFFFFFFF_BC4
            vec4(D(0.0), D(0.0), D(0.0), D(1.0)),                                  // 000000FF_sRGB
            vec4(D(0.5), D(0.5), D(b(0x7B)), D(1.0)),                              // XXXX7BFF_HDR (xy unknown)
            vec4(D(1.0), D(1.0), D(1.0), D(1.0)),                                  // FFFFFFFF_sRGB
            vec4(D(srgb(b(0x80))), D(srgb(b(0x80))), D(srgb(b(0x80))), D(1.0)),   // 808080FF_sRGB
            vec4(D(1.0), D(1.0), D(1.0), D(1.0)),                                  // FFFFFFFF_HDR
            vec4(D(0.5), D(0.5), D(0.5), D(1.0)),                                  // 000000FF_FFFFFFFF_HDR (a ramp: its middle)
            vec4(D(b(0x66)), D(0.0), D(0.0), D(1.0)),                              // 666666FF_BC4
        };
        for (int k = 0; k < 64; ++k)
            for (int n = 0; n < 13; ++n)
            {
                char nm[64];
                snprintf(nm, sizeof nm, "T_Unnamed%d_%d", k, n);
                ConstantTextures()[texid(nm)] = defaults[n];
            }
    }
    int total_ok = 0, total = 0;
    for (const GameShader& gs : g_shaders)
    {
        if (!filters.empty())
        {
            bool hit = false;
            for (auto& f : filters)
                if (f == gs.name || f == std::string(gs.name).substr(12)) hit = true;   // exact (with or without RMI_Surface_)
            if (!hit) continue;
        }
        Stat st;
        rng.seed(seed);
        for (int c = 0; c < ncases; ++c)
        {
            // ---- the uniform buffers
            for (auto& kv : Buffers()) for (int i = 0; i < 1024; ++i) kv.second._m0[i] = vec4(D(0.0));   // (the shaders hold references: never clear the map)
            UBO& View_ = ubo("View");
            UBO& Prim = ubo("Primitive");
            for (int i = 0; i < 1024; ++i)
            {
                View_._m0[i] = vec4(D(F(U(0, 1))), D(F(U(0, 1))), D(F(U(0, 1))), D(F(U(0, 1))));
                Prim._m0[i] = vec4(D(F(U(0, 1))), D(F(U(0, 1))), D(F(U(0, 1))), D(F(U(0, 1))));
            }
            // SvPosition -> translated world: a plausible projection inverse (w > 0 over the screen)
            {
                const int o = basepass::V_SVPositionToTranslatedWorld / 16;
                for (int r = 0; r < 4; ++r)
                    for (int k = 0; k < 4; ++k)
                        View_._m0[o + r][k] = D(F(U(-0.01, 0.01)));
                View_._m0[o + 0][0] = D(F(U(0.001, 0.003)));
                View_._m0[o + 1][1] = D(F(-U(0.001, 0.003)));
                View_._m0[o + 2][3] = D(F(U(-0.5, -0.1)));
                View_._m0[o + 3] = vec4(D(F(U(-2, 2))), D(F(U(-2, 2))), D(F(U(-2, 2))), D(F(U(0.6, 1.2))));
            }
            {
                const double pe = U(0.25, 4.0);
                const int a = basepass::V_PreExposure / 16, b = basepass::V_OneOverPreExposure / 16;
                View_._m0[a][(basepass::V_PreExposure % 16) / 4] = D(F(pe));
                View_._m0[b][(basepass::V_OneOverPreExposure % 16) / 4] = D(F(1.0 / pe));
                const int g = basepass::V_GameTime / 16;
                View_._m0[g][(basepass::V_GameTime % 16) / 4] = D(F(U(0, 1000)));
            }
            // the engine's translucency fog off (it isn't RM_Surface's): volumetric fog beyond the pixel, no scattering volumes
            View_._m0[4492 / 16].w = D(1.0e9);
            if (*gs.translucent_ubo)
            {
                UBO& T = ubo(gs.translucent_ubo);
                for (int k : {2336, 2368, 2960, 2992}) T._m0[k / 16].x = D(0.0);
                if (gs.srun)
                {
                    // the lit ones: a sun (unshadowed: no cascades), so the diffuse side of the lighting counts too
                    T._m0[0].z = uintBitsToFloat(1u);                       // HasDirectionalLight
                    T._m0[7].z = uintBitsToFloat(0u);                       // NumDirectionalLightCascades
                    T._m0[6].w = uintBitsToFloat(0xffffffffu);              // DirectionalLightLightContextBitField
                    T._m0[4] = vec4(D(F(U(0.5, 3))), D(F(U(0.5, 3))), D(F(U(0.5, 3))), D(0.0));   // DirectionalLightColor
                    const vec3 L = unit(0.0);
                    T._m0[5] = vec4(L.x, L.y, L.z, D(0.0));                 // DirectionalLightDirection
                    T._m0[7].x = D(0.0);                                    // DirectionalLightDistanceFadeMAD: no fade
                    T._m0[7].y = D(1.0);
                    View_._m0[3524 / 16].y = uintBitsToFloat(1u);           // View NumberOfFogContext: one context
                    View_._m0[3520 / 16].x = D(U(0, 1) < 0.25 ? F(1.333) : F(U(0, 1)));   // FogContextMediumIOR: sometimes under water
                    // the depth behind the surface (InvDeviceZToWorldZTransform): from ~100 to a few thousand units
                    View_._m0[1168 / 16].w = D(F(-U(0.0003, 0.01)));
                }
            }
            {
                const int o = basepass::P_DynamicCoverage / 16;
                Prim._m0[o][(basepass::P_DynamicCoverage % 16) / 4] = D(F(U(0, 1) < 0.25 ? 1.0 : U(0, 1)));
            }
            // ---- material parameters
            vec4 P[RMS_NUM_VECTORS];
            for (int k = 0; k < RMS_NUM_VECTORS; ++k)
                P[k] = vec4(D(F(U(-0.5, 2))), D(F(U(-0.5, 2))), D(F(U(-0.5, 2))), D(F(U(0, 1) < 0.5 ? 0.0 : U(-1, 1))));
            D S[2] = {D(F(U(0, 1))), D(F(U(0, 4)))};
            if (*gs.material_ubo)
                gs.fill_material(ubo(gs.material_ubo), P, S);
            for (auto& kv : Buffers())
                if (kv.first.rfind("junk:", 0) == 0)
                    for (int i = 0; i < 1024; ++i) kv.second._m0[i] = vec4(D(F(U(-1, 2))), D(F(U(-1, 2))), D(F(U(-1, 2))), D(F(U(-1, 2))));
            refresh_views();
            // ---- interpolants
            basepass::Interp I;
            // texture coordinates: mostly inside the 0..1 square, often near its middle (an eye's iris), sometimes far
            // out (tiling); UV2's whole part up to 8 (the materia's index)
            auto uvc = [&](double far) -> D {
                const double r = U(0, 1);
                if (r < 0.4) return RD(0, 1, 0.01);
                if (r < 0.75) return RD(0.5 - 0.3, 0.5 + 0.3, 0.003);
                return RD(-far, far, 0.01);
            };
            I.TEXCOORD = vec4(uvc(2), uvc(2), uvc(2), uvc(2));
            I.TEXCOORD_1 = vec4(U(0, 1) < 0.5 ? RD(0, 9, 0.01) : uvc(2), uvc(2), uvc(2), uvc(2));
            I.VERTEX_EXPRESSION = vec4(RD(-1, 1, 0.01), RD(-1, 1, 0.01), RD(-1, 1, 0.01), RD(-1, 1, 0.01));
            if (gs.srun)   // (the ocean's: its origin and two depths, in world units)
                I.VERTEX_EXPRESSION = vec4(RD(-300, 300, 0.01), RD(-300, 300, 0.01), RD(-20, 80, 0.01), RD(-60, 60, 0.01));
            const vec3 t0 = unit(0.02), t2 = unit(0.02);
            I.TEXCOORD_10 = vec4(t0, D(0.0));
            I.TEXCOORD_11 = vec4(t2, D(U(0, 1) < 0.5 ? -1.0 : 1.0));
            I.CONSTANT_CONTEXT = D((double)(int)U(0, 64));
            I.CURRENT_CLIP_SPACE_POSITION = vec4(RD(-1, 1, 0.001), RD(-1, 1, 0.001), RD(0, 1, 0.001), RD(0.5, 2, 0.001));
            I.PREVIOUS_CLIP_SPACE_POSITION = vec4(RD(-1, 1, 0.001), RD(-1, 1, 0.001), RD(0, 1, 0.001), RD(0.5, 2, 0.001));
            I.FragCoord = vec4(D(std::floor(U(0, 1920)) + 0.5, 1, 0), D(std::floor(U(0, 1080)) + 0.5, 0, 1), RD(0.01, 0.99, 0.0001), D(F(1.0 / U(1.0, gs.srun ? 30.0 : 3000.0))));   // (the lit ones: near, so the light crosses their medium)
            cpuglsl::gl_FragCoord = I.FragCoord;
            Inputs gin;
            gin.v["TEXCOORD"] = I.TEXCOORD;
            gin.v["TEXCOORD_1"] = I.TEXCOORD_1;
            gin.v["TEXCOORD_10"] = I.TEXCOORD_10;
            gin.v["TEXCOORD_11"] = I.TEXCOORD_11;
            gin.v["CONSTANT_CONTEXT"] = vec4(I.CONSTANT_CONTEXT);
            gin.v["CURRENT_CLIP_SPACE_POSITION"] = I.CURRENT_CLIP_SPACE_POSITION;
            gin.v["PREVIOUS_CLIP_SPACE_POSITION"] = I.PREVIOUS_CLIP_SPACE_POSITION;
            gin.v["VERTEX_EXPRESSION"] = I.VERTEX_EXPRESSION;
            // ---- the game
            g_discarded = false;
            gs.set_inputs(gin);
            gs.run();
            const bool gdisc = g_discarded;
            Outputs gout;
            gs.get_outputs(gout);
            // ---- the rebuild
            rms::In in;
            in.P = basepass::pixel_parameters(I, View_);
            basepass::load_view(View_);
            in.UV[0] = I.TEXCOORD.xy();
            in.UV[1] = I.TEXCOORD.zw();
            in.UV[2] = I.TEXCOORD_1.xy();
            in.UV[3] = I.TEXCOORD_1.zw();
            in.Noise = basepass::blue_noise(I, View_, texid("View_SpatiotemporalBlueNoiseVolumeTexture"));
            in.DynamicCoverage = basepass::ubo_f(Prim, basepass::P_DynamicCoverage);
            in.VertexExpression = I.VERTEX_EXPRESSION;
            for (int r = 0; r < 3; ++r) in.LocalToWorld[r] = basepass::ubo_f4(Prim, 16 * r);
            in.EBuffer = texelFetch(Tex2D{texid("OpaqueBasePass_EBufferTexture")}, ivec2_(uvec2(uint(I.FragCoord.x), uint(I.FragCoord.y))), 0);
#define SET_TEX(n) in.tex[rms::k_##n] = MakeTexture("T_" #n);
            RMS_TEXTURES(SET_TEX)
            for (int k = 0; k < RMS_NUM_VECTORS; ++k) in.vec[k] = P[k];
            for (int k = 0; k < rms::s_NumSwitches; ++k) in.sw[k] = D(0.0);
            for (auto& s : gs.switches)
                for (int k = 0; k < RMS_NUM_SWITCHES; ++k)
                    if (s == RMS_SWITCH_NAMES[k]) in.sw[k] = D(1.0);
            rms::Out o;
            rms::evaluate(in, o);
            const bool rdisc = gs.clip && o.OpacityMask.v < 0.0;
            ++st.cases;
            if (gdisc != rdisc)
            {
                ++st.discard_mismatch;
                if (st.first.empty()) st.first = "case " + std::to_string(c) + ": discard game " + std::to_string(gdisc) + " rebuild " + std::to_string(rdisc);
                continue;
            }
            if (gdisc) { ++st.discarded; continue; }
            const bool translucent = gout.v.find("SV_Target_2") == gout.v.end();
            basepass::GBuffer g = translucent ? basepass::encode_translucent(View_, o) : basepass::encode(I, View_, Prim, in.P, o, in.Noise);
            if (gs.srun)
            {
                // a lit translucent one: the game's own lighting (the spliced copy) on the rebuild's material values
                auto run_spliced = [&](const SpliceAttrs& a) -> Outputs {
                    g_R = a;
                    g_discarded = false;
                    gs.sset_inputs(gin);
                    gs.srun();
                    Outputs so;
                    gs.sget_outputs(so);
                    return so;
                };
                SpliceAttrs a;
                a.BaseColor = o.BaseColor; a.Normal = o.Normal; a.Emissive = o.Emissive; a.Muddiness = o.Muddiness;
                a.TransmittanceLog2 = o.TransmittanceLog2; a.Metallic = o.Metallic; a.Roughness = o.Roughness; a.AO = o.AO;
                a.Opacity = o.Opacity; a.TransparencyLog2 = o.TransparencyLog2; a.Thickness = o.Thickness; a.Foam = o.Foam;
                const Outputs so = run_spliced(a);
                for (int t = 0; t < 2; ++t)
                {
                    auto it = so.v.find(tn_[t]);
                    if (it != so.v.end()) g.t[t] = it->second;
                }
                // which material values this case tests: the copy's result moves when the value does
                auto moved = [&](const Outputs& x) {
                    for (int t = 0; t < 2; ++t)
                    {
                        auto i0 = so.v.find(tn_[t]), i1 = x.v.find(tn_[t]);
                        if (i0 == so.v.end() || i1 == x.v.end()) continue;
                        for (int k = 0; k < 4; ++k)
                        {
                            const double p = i0->second[k].v, q = i1->second[k].v;
                            if (std::isfinite(p) && std::isfinite(q) && std::fabs(p - q) > 1e-5 + 1e-5 * std::fabs(p)) return true;
                        }
                    }
                    return false;
                };
                const char* an[12] = {"BaseColor", "Normal", "Emissive", "Muddiness", "TransmittanceLog2", "Metallic", "Roughness", "AO", "Opacity", "TransparencyLog2", "Thickness", "Foam"};
                for (int k = 0; k < 12; ++k)
                {
                    SpliceAttrs b = a;
                    const D d(0.0625);
                    switch (k)
                    {
                    case 0: b.BaseColor = b.BaseColor * D(0.75) + vec3(d); break;
                    case 1: b.Normal = b.Normal + vec3(D(0.25), D(-0.125), D(0.0)); break;
                    case 2: b.Emissive = b.Emissive * D(1.5) + vec3(d); break;
                    case 3: b.Muddiness = b.Muddiness * D(0.75) + vec3(d); break;
                    case 4: b.TransmittanceLog2 = b.TransmittanceLog2 * D(1.5) - vec3(d); break;
                    case 5: b.Metallic = b.Metallic * D(0.75) + d; break;
                    case 6: b.Roughness = b.Roughness * D(0.75) + d; break;
                    case 7: b.AO = b.AO * D(0.75) + d; break;
                    case 8: b.Opacity = b.Opacity * D(0.75) + d; break;
                    case 9: b.TransparencyLog2 = b.TransparencyLog2 * D(1.5) - d; break;
                    case 10: b.Thickness = b.Thickness * D(0.75) + d; break;
                    case 11: b.Foam = b.Foam * D(0.75) + d; break;
                    }
                    if (moved(run_spliced(b))) ++st.tested[k];
                }
                st.spliced = true;
                const double val[12] = {a.BaseColor.x.v, a.Normal.x.v, a.Emissive.x.v, a.Muddiness.x.v, a.TransmittanceLog2.x.v, a.Metallic.v,
                                        a.Roughness.v, a.AO.v, a.Opacity.v, a.TransparencyLog2.v, a.Thickness.v, a.Foam.v};
                for (int k = 0; k < 12; ++k)
                    if (std::isfinite(val[k])) { st.lo[k] = std::min(st.lo[k], val[k]); st.hi[k] = std::max(st.hi[k], val[k]); }
            }
            const char* const* tn = tn_;
            for (int t = 0; t < 7; ++t)
            {
                auto it = gout.v.find(tn[t]);
                if (it == gout.v.end()) continue;
                for (int k = 0; k < 4; ++k)
                {
                    const double a = it->second[k].v, b = g.t[t][k].v;
                    const double e = std::fabs(a - b);
                    const double tol = 2e-6 + 2e-6 * std::fabs(a);
                    if (!(e <= tol) && !(std::isnan(a) && std::isnan(b)))
                    {
                        ++st.bad[t][k];
                        if (st.first.empty())
                        {
                            char buf[256];
                            snprintf(buf, sizeof buf, "case %d: %s.%c game %.9g rebuild %.9g", c, tn[t], "xyzw"[k], a, b);
                            st.first = buf;
                        }
                    }
                    if (std::isfinite(e)) st.maxerr[t][k] = std::max(st.maxerr[t][k], e);
                }
            }
        }
        int nbad = st.discard_mismatch;
        for (int t = 0; t < 7; ++t) for (int k = 0; k < 4; ++k) nbad += st.bad[t][k];
        ++total;
        if (nbad == 0) ++total_ok;
        printf("%-56s %s  (%d cases, %d discarded)\n", gs.name, nbad ? "DIFFERS" : "same", st.cases, st.discarded);
        if (st.spliced)
        {
            const char* an[12] = {"BaseColor", "Normal", "Emissive", "Muddiness", "TransmittanceLog2", "Metallic", "Roughness", "AO", "Opacity", "TransparencyLog2", "Thickness", "Foam"};
            printf("      (game lighting on the rebuild's values; each value moved the result in:");
            for (int k = 0; k < 12; ++k) printf(" %s %d", an[k], st.tested[k]);
            printf(")\n      (their ranges:");
            for (int k = 0; k < 12; ++k) if (st.tested[k]) printf(" %s %.3g..%.3g", an[k], st.lo[k], st.hi[k]);
            printf(")\n");
        }
        if (nbad && (verbose || true))
        {
            if (st.discard_mismatch) printf("      discard differs in %d cases\n", st.discard_mismatch);
            for (int t = 0; t < 7; ++t)
                for (int k = 0; k < 4; ++k)
                    if (st.bad[t][k]) printf("      %s .%c: %d cases, max error %.3g\n", TNAME[t], "xyzw"[k], st.bad[t][k], st.maxerr[t][k]);
            printf("      first: %s\n", st.first.c_str());
        }
    }
    printf("%d of %d permutations match\n", total_ok, total);
}
