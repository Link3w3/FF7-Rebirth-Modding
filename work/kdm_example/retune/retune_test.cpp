// The editor's live edits of a node's motions (Kawaii::Node::Retune): a node with a key animation of 3 tracks runs, then
// is retuned to 1 track (other bones), then to none, then back; each time it evaluates on. Before 3.15.0's Retune fix
// the track numbers found for the first tracks stayed (reading past the new, shorter list).
#include "/work/cacs3150/src/SkelCompatCore.hpp"
#include "/work/cacs3150/src/KawaiiSolver.hpp"
#include <cmath>
#include <cstdio>
using namespace Kawaii;

int main()
{
    // a chain of 6 bones along +X under a root
    Skeleton skel;
    const int n = 7;
    std::vector<Xf> pose(n);
    for (int i = 0; i < n; ++i)
    {
        skel.Names.push_back(i == 0 ? L"Root" : L"Tail" + std::to_wstring(i));
        skel.Parents.push_back(i - 1);
        skel.RefLength.push_back(i == 0 ? 0.0f : 10.0f);
        pose[i].T = {10.0f * i, 0, 0};
    }
    SkelCompat::KawaiiNode cfg;
    cfg.RootBone = L"Tail1";
    cfg.DummyBoneLength = 5.0f;
    auto make = [](std::vector<std::wstring> bones) {
        auto t = std::make_shared<std::vector<SkelCompat::KawaiiKeyTrack>>();
        for (auto& b : bones)
        {
            SkelCompat::KawaiiKeyTrack k;
            k.Bone = b;
            for (int f = 0; f < 30; ++f)
            {
                const float a = 0.3f * std::sin(f / 30.0f * 6.2831853f) / 2.0f;
                k.Keys.push_back({0.0f, 0.0f, std::sin(a), std::cos(a)});
            }
            t->push_back(k);
        }
        return std::shared_ptr<const std::vector<SkelCompat::KawaiiKeyTrack>>(t);
    };
    cfg.PoseAnimation.Tracks = make({L"Tail2", L"Tail4", L"Tail6"});
    SkelCompat::KawaiiWave w;
    w.Degrees = 5; w.Seconds = 2; w.PhasePerBone = 20;
    cfg.PoseWaves.push_back(w);
    Node node(cfg);
    std::vector<uint8_t> changed;
    Xf component;
    double sum = 0;
    auto run = [&](int frames) {
        for (int f = 0; f < frames; ++f)
        {
            std::vector<Xf> p = pose;
            changed.assign(n, 0);
            if (!node.Evaluate(skel, p, changed, component, 1.0f / 60.0f, nullptr)) { std::printf("not run\n"); return false; }
            for (auto& x : p) { if (!std::isfinite(x.T.X + x.T.Y + x.T.Z)) { std::printf("NaN\n"); return false; } sum += x.T.Y; }
        }
        return true;
    };
    bool ok = run(60);
    SkelCompat::KawaiiNode c2 = cfg;
    c2.PoseAnimation.Tracks = make({L"Tail5"});
    node.Retune(c2);
    ok = ok && run(60);
    SkelCompat::KawaiiNode c3 = cfg;
    c3.PoseAnimation.Tracks = nullptr;
    c3.PoseWaves.clear();
    node.Retune(c3);
    ok = ok && run(60);
    node.Retune(cfg);
    ok = ok && run(60);
    std::printf("%s (sum of y %.3f)\n", ok ? "OK: every retune evaluated" : "FAILED", sum);
    return ok ? 0 : 1;
}
