// (jitter) Offline check of Young Sephiroth's KawaiiPhysics entry: his reference pose (rig.json, component space) under the
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
    if (argc < 4) { std::printf("ys_jitter rig.json YoungSephirothKawaii.json fps\n"); return 2; }
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


    const float fps = static_cast<float>(std::atof(argv[3]));
    const float dt = 1.0f / fps;
    // the head and everything under it bob as a run animation would (component space): 4 cm up and down, 2.5 times a second
    std::vector<uint8_t> underHead(ref.size(), 0);
    const int head = skel.Find(L"C_Head_a");
    for (size_t i = 0; i < ref.size(); ++i)
    {
        for (int a = static_cast<int>(i); a >= 0; a = skel.Parents[static_cast<size_t>(a)])
        {
            if (a == head) { underHead[i] = 1; break; }
        }
    }
    const char* names[] = {"C_HairF_c_Phy", "C_CoatA_d_Phy", "L_CollarA_b_Phy", "R_FeatherA_e_Phy", "R_FeatherK_d_Phy"};
    struct Track { int bone; Xf prev1, prev2; bool have1 = false, have2 = false; float maxJerk = 0, sumJerk = 0; int n = 0; };
    std::vector<Track> tracks;
    for (const char* n : names) { Track t; t.bone = skel.Find(SkelCompat::Widen(n)); tracks.push_back(t); }
    Chain chain(set.Nodes);
    std::vector<uint8_t> changed;
    std::vector<Xf> pose;
    Xf component;
    float yaw = 0.0f;
    const int frames = static_cast<int>(fps * 6.0f);
    for (int f = 0; f < frames; ++f)
    {
        const float t = static_cast<float>(f) * dt;
        yaw += 30.0f * dt;
        const Q4 r = FromRotator(0.0f, yaw, 0.0f);
        component.T = component.T + Rotate(r, V3{400.0f * dt, 0, 0});
        component.R = r;
        pose = ref;
        const float bob = 4.0f * std::sin(t * 2.0f * 3.14159265f * 2.5f);
        for (size_t i = 0; i < pose.size(); ++i) { if (underHead[i]) { pose[i].T.Z += bob; } }
        chain.Evaluate(skel, pose, changed, component, dt, nullptr);
        for (auto& tr : tracks)
        {
            if (tr.bone < 0) { continue; }
            // its place against its pose (what the eye sees move on the body): the jerk is the change of that change
            Xf x;
            x.T = pose[static_cast<size_t>(tr.bone)].T - (ref[static_cast<size_t>(tr.bone)].T + V3{0, 0, underHead[static_cast<size_t>(tr.bone)] ? bob : 0.0f});
            if (tr.have2 && t > 1.0f)
            {
                const V3 jerk = x.T - tr.prev1.T * 2.0f + tr.prev2.T;
                const float j = Size(jerk);
                tr.maxJerk = std::max(tr.maxJerk, j);
                tr.sumJerk += j;
                ++tr.n;
            }
            tr.prev2 = tr.prev1; tr.have2 = tr.have1;
            tr.prev1 = x; tr.have1 = true;
        }
    }
    std::printf("%5.0f fps:", fps);
    for (size_t k = 0; k < tracks.size(); ++k)
    {
        const auto& tr = tracks[k];
        std::printf("  %s %.2f/%.2f", names[k], tr.n ? tr.sumJerk / tr.n : 0.0f, tr.maxJerk);
    }
    std::printf("  (mean/max cm per frame^2 of its offset from its pose)\n");
    return 0;
}
