// (3.17.0) Offline run of a KawaiiPhysics entry with kicks: a model's reference pose (rig.json, component space), standing
// for 1.5 s, then kicking: a leg at a time chambers (the thigh up, the knee bent), snaps out, comes back and goes down,
// fast, as in a battle combo; "round" kicks swing the thigh out to the side as well. Writes every frame's component-space
// transforms of all bones (the nodes' result in) in ys_skirt's format (int bones, int frames, 7 floats a bone a frame)
// for ys_skirt_check.py / clip_check.py.
//   kick_run rig.json entry.json fps out.bin [seconds = 6] [kick seconds = 0.46] [front | round | both = both]
//            [lift degrees = 95]
#include "../src/SkelCompatCore.hpp"
#include "../src/KawaiiSolver.hpp"
#include <cstdio>
#include <cstring>
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

// rotate bone `root`'s subtree (component space) about `pivot` by `q`
static void RotateSubtree(const Skeleton& skel, std::vector<Xf>& pose, int root, V3 pivot, Q4 q)
{
    const int n = skel.Count();
    std::vector<uint8_t> in(static_cast<size_t>(n), 0);
    for (int i = 0; i < n; ++i)
    {
        if (i == root) { in[static_cast<size_t>(i)] = 1; }
        else
        {
            const int p = skel.Parents[static_cast<size_t>(i)];
            if (p >= 0 && in[static_cast<size_t>(p)]) { in[static_cast<size_t>(i)] = 1; }
        }
        if (!in[static_cast<size_t>(i)]) { continue; }
        Xf& x = pose[static_cast<size_t>(i)];
        x.T = Rotate(q, x.T - pivot) + pivot;
        x.R = Normalized(q * x.R);
    }
}

static float Smooth(float a, float b, float t)
{
    t = Clamp(t, 0.0f, 1.0f);
    t = t * t * (3.0f - 2.0f * t);
    return a + (b - a) * t;
}

int main(int argc, char** argv)
{
    if (argc < 5) { std::printf("kick_run rig.json entry.json fps out.bin [seconds] [kick seconds] [front|round|both] [lift]\n"); return 2; }
    SkelCompat::Json rig;
    std::string error;
    if (!SkelCompat::ParseJson(ReadAll(argv[1]), rig, error)) { std::printf("rig: %s\n", error.c_str()); return 1; }
    SkelCompat::Config cfg;
    if (!SkelCompat::AppendConfig(ReadAll(argv[2]), L"entry.json", cfg)) { std::printf("config not read\n"); return 1; }
    SkelCompat::FinishConfig(cfg, [](const std::wstring&) { return true; });
    for (const auto& m : cfg.Messages) { std::printf("message: %s\n", SkelCompat::Narrow(m).c_str()); }
    if (cfg.Kawaii.empty()) { std::printf("no entry\n"); return 1; }
    const SkelCompat::KawaiiSet& set = cfg.Kawaii[0];
    Skeleton skel;
    std::vector<Xf> ref;
    for (const auto& b : rig.Find("bones")->array)
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
        skel.RefLocation.push_back(ref[i].T);
    }
    const float fps = static_cast<float>(std::atof(argv[3]));
    const float seconds = argc > 5 ? static_cast<float>(std::atof(argv[5])) : 6.0f;
    const float kickSeconds = argc > 6 ? static_cast<float>(std::atof(argv[6])) : 0.46f;
    const char* kind = argc > 7 ? argv[7] : "both";
    const float lift = argc > 8 ? static_cast<float>(std::atof(argv[8])) : 95.0f;
    const float dt = 1.0f / fps;
    const int legs[2] = {skel.Find(L"L_UpperLeg_a"), skel.Find(L"R_UpperLeg_a")};
    const int knees[2] = {skel.Find(L"L_Foreleg_a"), skel.Find(L"R_Foreleg_a")};
    if (legs[0] < 0 || legs[1] < 0 || knees[0] < 0 || knees[1] < 0) { std::printf("leg bones missing\n"); return 1; }
    std::FILE* out = std::fopen(argv[4], "wb");
    if (!out) { std::printf("cannot write %s\n", argv[4]); return 1; }
    const int n = skel.Count();
    const int frames = static_cast<int>(fps * seconds);
    std::fwrite(&n, 4, 1, out);
    std::fwrite(&frames, 4, 1, out);
    Chain chain(set.Nodes);
    std::vector<uint8_t> changed;
    std::vector<Xf> pose;
    Xf component;
    const float period = kickSeconds + 0.34f;   // (a kick, then the leg down a moment)
    for (int f = 0; f < frames; ++f)
    {
        const float t = static_cast<float>(f) * dt;
        pose = ref;
        if (t >= 1.5f)
        {
            const int k = static_cast<int>((t - 1.5f) / period);
            const float u = (t - 1.5f) - static_cast<float>(k) * period;   // time into this kick
            const int s = k % 2;                                            // left, right, left, ...
            const bool round = std::strcmp(kind, "round") == 0 || (std::strcmp(kind, "both") == 0 && (k / 2) % 2 == 1);
            // its phases as parts of the kick's time: chamber 22%, snap out 13%, back 22%, down 43%
            const float ks = kickSeconds;
            const float c1 = 0.22f * ks, c2 = c1 + 0.13f * ks, c3 = c2 + 0.22f * ks;
            float thigh = 0.0f, bend = 0.0f;
            if (u < c1)
            {
                thigh = Smooth(0.0f, lift, u / c1);
                bend = Smooth(0.0f, 110.0f, u / c1);
            }
            else if (u < c2)
            {
                thigh = Smooth(lift, lift + 5.0f, (u - c1) / (c2 - c1));
                bend = Smooth(110.0f, 5.0f, (u - c1) / (c2 - c1));
            }
            else if (u < c3)
            {
                thigh = lift + 5.0f;
                bend = Smooth(5.0f, 100.0f, (u - c2) / (c3 - c2));
            }
            else if (u < ks)
            {
                thigh = Smooth(lift + 5.0f, 0.0f, (u - c3) / (ks - c3));
                bend = Smooth(100.0f, 0.0f, (u - c3) / (ks - c3));
            }
            const V3 pivot = pose[static_cast<size_t>(legs[s])].T;
            if (round)
            {
                // out to its side as well (the left leg to +Y... the model's left is -Y: out is away from the middle)
                const float side = s == 0 ? 1.0f : -1.0f;
                RotateSubtree(skel, pose, legs[s], pivot, FromRotator(thigh * 0.6f, 0.0f, side * thigh * 0.7f));
            }
            else { RotateSubtree(skel, pose, legs[s], pivot, FromRotator(thigh, 0.0f, 0.0f)); }
            RotateSubtree(skel, pose, knees[s], pose[static_cast<size_t>(knees[s])].T, FromRotator(-bend, 0.0f, 0.0f));
        }
        chain.Evaluate(skel, pose, changed, component, dt, nullptr);
        for (int i = 0; i < n; ++i)
        {
            const Xf& x = pose[static_cast<size_t>(i)];
            const float v[7] = {x.R.X, x.R.Y, x.R.Z, x.R.W, x.T.X, x.T.Y, x.T.Z};
            std::fwrite(v, 4, 7, out);
        }
    }
    std::fclose(out);
    std::printf("wrote %d frames of %d bones (%s kicks of %.2f s, lift %.0f, %.0f fps)\n", frames, n, kind, kickSeconds, lift, fps);
    return 0;
}
