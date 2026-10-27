// (skirt) Offline run of Young Sephiroth's KawaiiPhysics entry with his legs moving: his reference pose (rig.json,
// component space) with the thighs swinging as in a run (and the knees bending), the body bobbing and the character
// running forward and turning; writes every frame's component-space transforms of all bones (the nodes' result in) for
// the coat-against-legs check (ys_skirt_check.py: skins the coat's vertices with them and measures how far they go into
// the legs).
//   preset_run rig.json kawaii.json fps out.bin [swing degrees = 55] [seconds = 6] [speed cm/s = 450] [turn deg/s = 20] [stop at s = 0: never]
//              [bob cm = 2.5] [lean degrees = 0] [arm swing degrees = 0] [chest twist degrees = 0] [stance degrees = 0]
// (2026-10-25: the upper body leaning forward as the run starts, the arms swinging against the legs with the elbows
// bending, and the chest twisting with the stride: a battle run, for the hair-against-body check, hair_check.py)
#include "/work/cacs3144/src/SkelCompatCore.hpp"
#include "/work/cacs3144/src/KawaiiSolver.hpp"
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

int main(int argc, char** argv)
{
    if (argc < 5) { std::printf("preset_run rig.json kawaii.json fps out.bin [swing] [seconds] [speed] [turn] [stop]\n"); return 2; }
    SkelCompat::Json rig;
    std::string error;
    if (!SkelCompat::ParseJson(ReadAll(argv[1]), rig, error)) { std::printf("rig: %s\n", error.c_str()); return 1; }
    SkelCompat::Config cfg;
    if (!SkelCompat::AppendConfig(ReadAll(argv[2]), L"YoungSephirothKawaii.json", cfg)) { std::printf("config not read\n"); return 1; }
    SkelCompat::FinishConfig(cfg, [](const std::wstring&) { return true; });
    for (const auto& m : cfg.Messages) { std::printf("message: %s\n", SkelCompat::Narrow(m).c_str()); }
    if (cfg.Kawaii.size() != 1) { std::printf("%zu entries\n", cfg.Kawaii.size()); return 1; }
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
    }
    const float fps = static_cast<float>(std::atof(argv[3]));
    const float swing = argc > 5 ? static_cast<float>(std::atof(argv[5])) : 55.0f;
    const float seconds = argc > 6 ? static_cast<float>(std::atof(argv[6])) : 6.0f;
    const float speed = argc > 7 ? static_cast<float>(std::atof(argv[7])) : 450.0f;
    const float turnRate = argc > 8 ? static_cast<float>(std::atof(argv[8])) : 20.0f;
    const float stopAt = argc > 9 ? static_cast<float>(std::atof(argv[9])) : 0.0f;
    const float bobAmp = argc > 10 ? static_cast<float>(std::atof(argv[10])) : 2.5f;
    const float leanDeg = argc > 11 ? static_cast<float>(std::atof(argv[11])) : 0.0f;
    const float armDeg = argc > 12 ? static_cast<float>(std::atof(argv[12])) : 0.0f;
    const float twistDeg = argc > 13 ? static_cast<float>(std::atof(argv[13])) : 0.0f;
    const float stanceDeg = argc > 14 ? static_cast<float>(std::atof(argv[14])) : 0.0f;   // each thigh turned out sideways (a wide stance)
    const float dt = 1.0f / fps;
    const int hip = skel.Find(L"C_Hip_a");
    const int legs[2] = {skel.Find(L"L_UpperLeg_a"), skel.Find(L"R_UpperLeg_a")};
    const int knees[2] = {skel.Find(L"L_Foreleg_a"), skel.Find(L"R_Foreleg_a")};
    if (hip < 0 || legs[0] < 0 || legs[1] < 0 || knees[0] < 0 || knees[1] < 0) { std::printf("leg bones missing\n"); return 1; }
    const int spine = skel.Find(L"C_Spine_a");
    const int arms[2] = {skel.Find(L"L_UpperArm_a"), skel.Find(L"R_UpperArm_a")};
    const int elbows[2] = {skel.Find(L"L_Forearm_a"), skel.Find(L"R_Forearm_a")};
    if ((leanDeg != 0.0f || twistDeg != 0.0f) && spine < 0) { std::printf("C_Spine_a missing\n"); return 1; }
    if (armDeg != 0.0f && (arms[0] < 0 || arms[1] < 0 || elbows[0] < 0 || elbows[1] < 0)) { std::printf("arm bones missing\n"); return 1; }
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
    float yaw = 0.0f;
    const float pi = 3.14159265f;
    for (int f = 0; f < frames; ++f)
    {
        const float t = static_cast<float>(f) * dt;
        // the first second standing, then running (the swing growing in over half a second), turning a little
        float run = Clamp((t - 1.0f) / 0.5f, 0.0f, 1.0f);
        if (stopAt > 0.0f && t >= stopAt) { run = Clamp(1.0f - (t - stopAt) / 0.3f, 0.0f, 1.0f); }
        yaw += turnRate * dt * run;
        const Q4 r = FromRotator(0.0f, yaw, 0.0f);
        component.T = component.T + Rotate(r, V3{speed * run * dt, 0, 0});
        component.R = r;
        pose = ref;
        const float phase = t * 2.0f * pi * 1.4f;   // 1.4 strides a second
        if (stanceDeg != 0.0f)
        {
            // (a wide stance) each thigh turned out about the forward axis at its hip joint: the left (-Y) one toward -Y
            for (int s = 0; s < 2; ++s)
            {
                RotateSubtree(skel, pose, legs[s], pose[static_cast<size_t>(legs[s])].T, FromRotator(0.0f, 0.0f, s ? -stanceDeg : stanceDeg));
            }
        }
        for (int s = 0; s < 2; ++s)
        {
            const float a = swing * run * std::sin(phase + (s ? pi : 0.0f));   // + forward
            // the thigh about the side axis (Y) at the hip joint: forward is +X, so a forward swing turns -Z toward +X
            const V3 pivot = pose[static_cast<size_t>(legs[s])].T;
            RotateSubtree(skel, pose, legs[s], pivot, FromRotator(a, 0.0f, 0.0f));
            // the knee bends back as the thigh comes forward (0 - 70 degrees)
            const float bend = 70.0f * (swing / 55.0f) * run * std::max(0.0f, std::sin(phase + (s ? pi : 0.0f) + 0.6f));   // (none when standing)
            RotateSubtree(skel, pose, knees[s], pose[static_cast<size_t>(knees[s])].T, FromRotator(-bend, 0.0f, 0.0f));
        }
        // (battle run) the arms swing against the legs (the left arm with the right leg), the elbows bending as an arm comes
        // forward; then the upper body (C_Spine_a and all above it) twists with the stride and leans forward
        if (armDeg != 0.0f)
        {
            for (int s = 0; s < 2; ++s)
            {
                const float a = armDeg * run * std::sin(phase + (s ? 0.0f : pi));   // + forward (against the same side's leg)
                RotateSubtree(skel, pose, arms[s], pose[static_cast<size_t>(arms[s])].T, FromRotator(a, 0.0f, 0.0f));
                const float bend = (25.0f + 35.0f * std::max(0.0f, std::sin(phase + (s ? 0.0f : pi)))) * run;
                RotateSubtree(skel, pose, elbows[s], pose[static_cast<size_t>(elbows[s])].T, FromRotator(bend, 0.0f, 0.0f));
            }
        }
        if (twistDeg != 0.0f)
        {
            const float tw = twistDeg * run * std::sin(phase);
            RotateSubtree(skel, pose, spine, pose[static_cast<size_t>(spine)].T, FromRotator(0.0f, tw, 0.0f));
        }
        if (leanDeg != 0.0f)
        {
            // forward: the spine's +Z toward +X (a negative pitch)
            RotateSubtree(skel, pose, spine, pose[static_cast<size_t>(spine)].T, FromRotator(-leanDeg * run, 0.0f, 0.0f));
        }
        // the body bobs (2.5 cm, twice a stride)
        const float bob = bobAmp * run * std::sin(phase * 2.0f);
        for (auto& x : pose) { x.T.Z += bob; }
        chain.Evaluate(skel, pose, changed, component, dt, nullptr);
        for (int i = 0; i < n; ++i)
        {
            const Xf& x = pose[static_cast<size_t>(i)];
            const float v[7] = {x.R.X, x.R.Y, x.R.Z, x.R.W, x.T.X, x.T.Y, x.T.Z};
            std::fwrite(v, 4, 7, out);
        }
    }
    std::fclose(out);
    std::printf("wrote %d frames of %d bones (swing %.0f, %.0f fps)\n", frames, n, swing, fps);
    return 0;
}
