// Offline check of Young Sephiroth's KawaiiPhysics entry: his reference pose (rig.json, component space) under the
// entry's nodes while the character runs, turns, jumps and stops; the chains stay finite, keep their lengths and stay
// out of the collision shapes.
#include "../src/SkelCompatCore.hpp"
#include "../src/KawaiiSolver.hpp"
#include <cstdio>
#include <fstream>
#include <sstream>
using namespace Kawaii;

static std::string ReadAll(const char* path)
{
    std::ifstream f(path, std::ios::binary);
    std::stringstream s;
    s << f.rdbuf();
    return s.str();
}

int main(int argc, char** argv)
{
    if (argc < 3) { std::printf("ys_sim rig.json YoungSephirothKawaii.json\n"); return 2; }
    SkelCompat::Json rig;
    std::string error;
    if (!SkelCompat::ParseJson(ReadAll(argv[1]), rig, error)) { std::printf("rig: %s\n", error.c_str()); return 1; }
    SkelCompat::Config cfg;
    if (!SkelCompat::AppendConfig(ReadAll(argv[2]), L"YoungSephirothKawaii.json", cfg)) { std::printf("config not read\n"); return 1; }
    SkelCompat::FinishConfig(cfg, [](const std::wstring&) { return true; });
    for (const auto& m : cfg.Messages) { std::printf("message: %s\n", SkelCompat::Narrow(m).c_str()); }
    if (cfg.Kawaii.size() != 1) { std::printf("%zu entries\n", cfg.Kawaii.size()); return 1; }
    const SkelCompat::KawaiiSet& set = cfg.Kawaii[0];
    std::printf("entry: %zu node(s), disable_bonamik %d (%zu named)\n", set.Nodes.size(), set.DisableBonamik ? 1 : 0, set.DisableBonamikAssets.size());

    Skeleton skel;
    std::vector<Xf> ref;
    const SkelCompat::Json* list = rig.Find("bones");
    for (const auto& b : list->array)
    {
        skel.Names.push_back(SkelCompat::Widen(b.Find("name")->string));
        const SkelCompat::Json* parent = b.Find("parent");
        int p = -1;
        if (parent && parent->type == SkelCompat::Json::Type::String) { p = skel.Find(SkelCompat::Widen(parent->string)); }
        skel.Parents.push_back(p);
        Xf x;
        const auto& q = b.Find("q")->array;
        const auto& t = b.Find("t")->array;
        x.R = {static_cast<float>(q[0].number), static_cast<float>(q[1].number), static_cast<float>(q[2].number), static_cast<float>(q[3].number)};
        x.T = {static_cast<float>(t[0].number), static_cast<float>(t[1].number), static_cast<float>(t[2].number)};
        ref.push_back(x);
    }
    for (size_t i = 0; i < ref.size(); ++i)
    {
        const int p = skel.Parents[i];
        skel.RefLength.push_back(p >= 0 ? Size(ref[i].T - ref[static_cast<size_t>(p)].T) : 0.0f);
    }
    std::printf("%d bones\n", skel.Count());

    Chain chain(set.Nodes);
    std::vector<uint8_t> changed;
    std::vector<Xf> pose;
    Xf component;
    float yaw = 0.0f, z = 0.0f, vz = 0.0f, maxStretch = 0.0f, maxOff = 0.0f;
    int bad = 0;
    const float dt = 1.0f / 60.0f;
    for (int f = 0; f < 60 * 12; ++f)
    {
        const float t = static_cast<float>(f) * dt;
        // 0-3 s: run forward 6 m/s turning; 3-5 s: spin fast in place; 5-7 s: jumps; 7-12 s: stand still
        float speed = 0.0f, turn = 0.0f;
        if (t < 3.0f) { speed = 600.0f; turn = 60.0f; }
        else if (t < 5.0f) { turn = 720.0f; }
        else if (t < 7.0f)
        {
            if (z <= 0.0f && vz <= 0.0f) { vz = 500.0f; }
        }
        yaw += turn * dt;
        vz -= 980.0f * dt;
        z = std::max(0.0f, z + vz * dt);
        if (z == 0.0f && vz < 0.0f) { vz = 0.0f; }
        const Q4 r = FromRotator(0.0f, yaw, 0.0f);
        component.T = component.T + Rotate(r, V3{speed * dt, 0, 0});
        component.T.Z = z;
        component.R = r;
        pose = ref;
        const int ran = chain.Evaluate(skel, pose, changed, component, dt, nullptr);
        if (f == 0)
        {
            std::printf("nodes run: %d\n", ran);
            for (size_t k = 0; k < chain.Nodes.size(); ++k)
            {
                std::printf("  %s: %zu bones simulated, %zu constraints%s%s\n", SkelCompat::Narrow(set.Nodes[k].Name).c_str(), chain.Nodes[k].SimulatedBones(),
                            chain.Nodes[k].MergedConstraints(), chain.Nodes[k].Problem.empty() ? "" : ", problem: ",
                            SkelCompat::Narrow(chain.Nodes[k].Problem).c_str());
            }
        }
        for (int b = 1; b < skel.Count(); ++b)
        {
            const Xf& x = pose[static_cast<size_t>(b)];
            if (!std::isfinite(x.T.X + x.T.Y + x.T.Z + x.R.X + x.R.Y + x.R.Z + x.R.W)) { ++bad; continue; }
            if (!changed[static_cast<size_t>(b)]) { continue; }
            const int p = skel.Parents[static_cast<size_t>(b)];
            const float got = Size(x.T - pose[static_cast<size_t>(p)].T);
            maxStretch = std::max(maxStretch, std::fabs(got - skel.RefLength[static_cast<size_t>(b)]));
            maxOff = std::max(maxOff, Size(x.T - ref[static_cast<size_t>(b)].T));
        }
        if (f % 60 == 59)
        {
            const int tip = skel.Find(L"C_CoatA_d_Phy"), hair = skel.Find(L"C_HairF_c_Phy");
            const int wingA = skel.Find(L"R_FeatherA_e_Phy"), wingK = skel.Find(L"R_FeatherK_d_Phy");
            std::printf("t=%4.1fs coat hem %.1f cm from its pose, front hair tip %.1f; worst stretch %.3f cm", t + dt,
                        Size(pose[static_cast<size_t>(tip)].T - ref[static_cast<size_t>(tip)].T), Size(pose[static_cast<size_t>(hair)].T - ref[static_cast<size_t>(hair)].T),
                        maxStretch);
            if (wingA >= 0 && wingK >= 0)
            {
                std::printf("; wing tips A %.1f, K %.1f", Size(pose[static_cast<size_t>(wingA)].T - ref[static_cast<size_t>(wingA)].T),
                            Size(pose[static_cast<size_t>(wingK)].T - ref[static_cast<size_t>(wingK)].T));
            }
            std::printf("\n");
        }
    }
    const int tip = skel.Find(L"C_CoatA_d_Phy");
    std::printf("non-finite bone values: %d; the most a bone left its pose: %.1f cm; at rest the coat hem is %.2f cm from its pose\n", bad, maxOff,
                Size(pose[static_cast<size_t>(tip)].T - ref[static_cast<size_t>(tip)].T));
    const int wingA = skel.Find(L"R_FeatherA_e_Phy");
    if (wingA >= 0) { std::printf("at rest the wing's longest feather tip is %.2f cm from its pose\n", Size(pose[static_cast<size_t>(wingA)].T - ref[static_cast<size_t>(wingA)].T)); }
    return bad ? 1 : 0;
}
