// Offline run of a KawaiiPhysics entry on a game animation: a clip sampled in the editor (anims/*_samples.json: each
// frame's local transforms of the bones it lists, at 60 fps, from AnimationLibrary.GetBonePoseForTime), looped, on a
// model's reference pose (rig.json, component space; the bones the clip does not list keep their reference local
// transforms). The clip's root (Trans) moves the component (its root motion, as the game's character movement takes it);
// the hips keep the clip's own translation (bob, sway). The first second the model stands in the clip's first pose
// (still), then the clip plays. Writes every frame's component-space transforms of all bones after the nodes (the
// format of preset_run: int bones, int frames, then 7 floats a bone a frame) for clip_check.py / coat_flare.py.
//   anim_run rig.json entry.json samples.json clip out.bin [seconds = 7] [fps = 60] [speed scale = 1]
#include "/work/cacs3183/src/SkelCompatCore.hpp"
#include "/work/cacs3183/src/KawaiiSolver.hpp"
#include <cmath>
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

static Q4 Nlerp(Q4 a, Q4 b, float t)
{
    const float d = a.X * b.X + a.Y * b.Y + a.Z * b.Z + a.W * b.W;
    if (d < 0.0f) { b = Q4{-b.X, -b.Y, -b.Z, -b.W}; }
    return Normalized(Q4{a.X + (b.X - a.X) * t, a.Y + (b.Y - a.Y) * t, a.Z + (b.Z - a.Z) * t, a.W + (b.W - a.W) * t});
}

int main(int argc, char** argv)
{
    if (argc < 6) { std::printf("anim_run rig.json entry.json samples.json clip out.bin [seconds] [fps] [speed scale]\n"); return 2; }
    SkelCompat::Json rig, samples;
    std::string error;
    if (!SkelCompat::ParseJson(ReadAll(argv[1]), rig, error)) { std::printf("rig: %s\n", error.c_str()); return 1; }
    SkelCompat::Config cfg;
    if (!SkelCompat::AppendConfig(ReadAll(argv[2]), L"entry.json", cfg)) { std::printf("config not read\n"); return 1; }
    SkelCompat::FinishConfig(cfg, [](const std::wstring&) { return true; });
    for (const auto& m : cfg.Messages) { std::printf("message: %s\n", SkelCompat::Narrow(m).c_str()); }
    if (cfg.Kawaii.size() != 1) { std::printf("%zu entries (one expected)\n", cfg.Kawaii.size()); return 1; }
    if (!SkelCompat::ParseJson(ReadAll(argv[3]), samples, error)) { std::printf("samples: %s\n", error.c_str()); return 1; }
    const SkelCompat::Json* clip = samples.Find(argv[4]);
    if (!clip) { std::printf("no clip %s\n", argv[4]); return 1; }
    const float seconds = argc > 6 ? static_cast<float>(std::atof(argv[6])) : 7.0f;
    const float fps = argc > 7 ? static_cast<float>(std::atof(argv[7])) : 60.0f;
    const float speedScale = argc > 8 ? static_cast<float>(std::atof(argv[8])) : 1.0f;

    Skeleton skel;
    std::vector<Xf> refLocal, refCs;
    for (const auto& b : rig.Find("bones")->array)
    {
        skel.Names.push_back(SkelCompat::Widen(b.Find("name")->string));
        const SkelCompat::Json* parent = b.Find("parent");
        int p = -1;
        if (parent && parent->type == SkelCompat::Json::Type::String) { p = skel.Find(SkelCompat::Widen(parent->string)); }
        skel.Parents.push_back(p);
        const auto& q = b.Find("q")->array;
        const auto& t = b.Find("t")->array;
        Xf l, c;
        c.R = {static_cast<float>(q[0].number), static_cast<float>(q[1].number), static_cast<float>(q[2].number), static_cast<float>(q[3].number)};
        c.T = {static_cast<float>(t[0].number), static_cast<float>(t[1].number), static_cast<float>(t[2].number)};
        if (b.Find("local_q") && b.Find("local_t"))
        {
            const auto& lq = b.Find("local_q")->array;
            const auto& lt = b.Find("local_t")->array;
            l.R = {static_cast<float>(lq[0].number), static_cast<float>(lq[1].number), static_cast<float>(lq[2].number), static_cast<float>(lq[3].number)};
            l.T = {static_cast<float>(lt[0].number), static_cast<float>(lt[1].number), static_cast<float>(lt[2].number)};
        }
        else if (p >= 0)
        {
            // (a rig in component space only: the local transform from the parent's)
            const Xf& P = refCs[static_cast<size_t>(p)];
            const Q4 inv{-P.R.X, -P.R.Y, -P.R.Z, P.R.W};
            l.R = Normalized(inv * c.R);
            l.T = Rotate(inv, c.T - P.T);
        }
        else { l = c; }
        refLocal.push_back(l);
        refCs.push_back(c);
    }
    const int n = skel.Count();
    for (int i = 0; i < n; ++i)
    {
        const int p = skel.Parents[static_cast<size_t>(i)];
        skel.RefLength.push_back(p >= 0 ? Size(refCs[static_cast<size_t>(i)].T - refCs[static_cast<size_t>(p)].T) : 0.0f);
        skel.RefLocation.push_back(refCs[static_cast<size_t>(i)].T);   // (3.17.0: the sync bones' start)
        skel.RefRotation.push_back(refCs[static_cast<size_t>(i)].R);   // (3.18.0: the mirrored shapes)
    }
    // the clip: its bones (by index in the rig) and frames
    std::vector<int> clipBone;
    for (const auto& b : clip->Find("bones")->array) { clipBone.push_back(skel.Find(SkelCompat::Widen(b.string))); }
    const auto& framesJ = clip->Find("poses")->array;
    const int clipFrames = static_cast<int>(framesJ.size());
    const float length = static_cast<float>(clip->Find("length")->number);
    std::vector<std::vector<Xf>> clipPose(static_cast<size_t>(clipFrames));
    for (int f = 0; f < clipFrames; ++f)
    {
        for (const auto& v : framesJ[static_cast<size_t>(f)].array)
        {
            Xf x;
            x.R = Normalized(Q4{static_cast<float>(v.array[0].number), static_cast<float>(v.array[1].number), static_cast<float>(v.array[2].number), static_cast<float>(v.array[3].number)});
            x.T = {static_cast<float>(v.array[4].number), static_cast<float>(v.array[5].number), static_cast<float>(v.array[6].number)};
            clipPose[static_cast<size_t>(f)].push_back(x);
        }
    }
    const int trans = skel.Find(L"Trans");
    const int hip = skel.Find(L"C_Hip_a");
    int transInClip = -1;
    for (size_t k = 0; k < clipBone.size(); ++k) { if (clipBone[k] == trans) { transInClip = static_cast<int>(k); } }
    // the root's travel over one loop (its last sample's place less its first's)
    V3 loopTravel{0, 0, 0};
    if (transInClip >= 0) { loopTravel = clipPose.back()[static_cast<size_t>(transInClip)].T - clipPose.front()[static_cast<size_t>(transInClip)].T; }

    std::FILE* out = std::fopen(argv[5], "wb");
    if (!out) { std::printf("cannot write %s\n", argv[5]); return 1; }
    const float dt = 1.0f / fps;
    const int frames = static_cast<int>(fps * seconds);
    std::fwrite(&n, 4, 1, out);
    std::fwrite(&frames, 4, 1, out);
    Chain chain(cfg.Kawaii[0].Nodes);
    std::vector<uint8_t> changed;
    std::vector<Xf> local(static_cast<size_t>(n)), pose(static_cast<size_t>(n));
    Xf component;
    for (int f = 0; f < frames; ++f)
    {
        const float t = static_cast<float>(f) * dt;
        const float playing = std::max(0.0f, t - 1.0f) * speedScale;   // (the first second still, in the clip's first pose)
        const float loops = std::floor(playing / length);
        const float at = (playing - loops * length) / length * static_cast<float>(clipFrames - 1);
        const int k0 = std::min(clipFrames - 1, static_cast<int>(at));
        const int k1 = std::min(clipFrames - 1, k0 + 1);
        const float w = at - static_cast<float>(k0);
        local = refLocal;
        V3 root{0, 0, 0};
        for (size_t k = 0; k < clipBone.size(); ++k)
        {
            const int b = clipBone[k];
            if (b < 0) { continue; }
            const Xf& a = clipPose[static_cast<size_t>(k0)][k];
            const Xf& c = clipPose[static_cast<size_t>(k1)][k];
            const V3 tt = a.T + (c.T - a.T) * w;
            if (b == trans)
            {
                root = tt - clipPose.front()[k].T + loopTravel * loops;   // (the root motion: the component carries it)
                continue;
            }
            local[static_cast<size_t>(b)].R = Nlerp(a.R, c.R, w);
            if (b == hip) { local[static_cast<size_t>(b)].T = tt; }
        }
        component.T = root;
        for (int i = 0; i < n; ++i)
        {
            const int p = skel.Parents[static_cast<size_t>(i)];
            const Xf& l = local[static_cast<size_t>(i)];
            if (p < 0) { pose[static_cast<size_t>(i)] = l; continue; }
            const Xf& P = pose[static_cast<size_t>(p)];
            Xf x;
            x.R = Normalized(P.R * l.R);
            x.T = Rotate(P.R, l.T) + P.T;
            pose[static_cast<size_t>(i)] = x;
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
    std::printf("wrote %d frames of %d bones (%s, %.3f s a loop, %.0f cm a loop, %.0f fps)\n", frames, n, argv[4], length, Size(loopTravel), fps);
    return 0;
}
