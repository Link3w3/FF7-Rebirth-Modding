// (3.20.0) Offline run of a Kawaii Dynamic Motions entry whose nodes play the motions of animation sets ("pose_animset"),
// as the game mod plays them (KawaiiRt::Motions): the character plays a schedule of clips (samples.json, as anim_run's:
// each clip's local transforms a frame; its root moves the component), each for some seconds; every tenth of a second
// each node picks its motion for the clip playing (its name: what the character plays; in battle for a B_ clip), how fast
// the component moves, and the sets; a new pick is decoded from the game's animation package (AclDecode.hpp; the track
// table found in the package as the Python tools find it) and played, cross-faded (Node::PlayMotion).
//   anim_run_sets rig.json compat.json samples.json sets.json schedule out.bin [fps = 60]
//     sets.json: {"skeleton": {"names": [...], "ref_q": [[x, y, z, w], ...]}, "sets": {"<set path>": {"<motion>": "<package file>"}}}
//     schedule:  clip:seconds,clip:seconds,... (one after the other; a clip of samples.json, looped while it plays)
#include "../src/AclDecode.hpp"
#include "../src/SkelCompatCore.hpp"
#include "../src/KawaiiSolver.hpp"

#include <cmath>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <map>
#include <sstream>

using namespace Kawaii;

static std::string ReadAll(const std::string& path)
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

// the compressed tracks' bones in a cooked AnimSequence package: an int32 count n, then n distinct bone indices, the first 0
static std::vector<int32_t> TrackMap(const std::vector<uint8_t>& data, uint32_t n, size_t bones)
{
    for (size_t p = 0; p + 4 + 4 * static_cast<size_t>(n) <= data.size(); ++p)
    {
        int32_t count = 0;
        std::memcpy(&count, data.data() + p, 4);
        if (count != static_cast<int32_t>(n)) { continue; }
        std::vector<int32_t> v(n);
        std::memcpy(v.data(), data.data() + p + 4, 4 * static_cast<size_t>(n));
        if (v[0] != 0) { continue; }
        std::vector<uint8_t> seen(bones, 0);
        bool ok = true;
        for (int32_t b : v)
        {
            if (b < 0 || static_cast<size_t>(b) >= bones || seen[static_cast<size_t>(b)]) { ok = false; break; }
            seen[static_cast<size_t>(b)] = 1;
        }
        if (ok) { return v; }
    }
    return {};
}

struct SetsData
{
    std::vector<std::wstring> Names;
    std::vector<std::array<float, 4>> Ref;
    std::vector<std::pair<std::wstring, std::vector<std::pair<std::wstring, std::string>>>> Sets;   // path -> (motion, file)
};

static std::shared_ptr<const Node::Motion> DecodeFile(const std::string& file, const std::wstring& name, const SetsData& sd, const std::vector<uint8_t>& wantBone,
                                                      const SkelCompat::KawaiiPoseAnimSet& cfg, std::string& why)
{
    const std::string text = ReadAll(file);
    std::vector<uint8_t> data(text.begin(), text.end());
    const size_t at = Acl::FindClip(data.data(), data.size());
    if (at == static_cast<size_t>(-1)) { why = "no ACL clip"; return nullptr; }
    uint32_t tracks = 0;
    std::memcpy(&tracks, data.data() + at + 16, 2);
    tracks &= 0xFFFF;
    const std::vector<int32_t> map = TrackMap(data, tracks, sd.Names.size());
    if (map.empty()) { why = "no track map"; return nullptr; }
    std::vector<uint8_t> want(map.size(), 0);
    for (size_t t = 0; t < map.size(); ++t) { want[t] = wantBone[static_cast<size_t>(map[t])]; }
    Acl::Clip clip;
    if (!Acl::Decode(data.data() + at, data.size() - at, want, clip, why)) { return nullptr; }
    std::vector<SkelCompat::KawaiiKeyTrack> list;
    std::vector<std::array<float, 4>> bases;
    for (size_t t = 0; t < clip.Rotations.size(); ++t)
    {
        if (clip.Rotations[t].empty()) { continue; }
        SkelCompat::KawaiiKeyTrack k;
        k.Bone = sd.Names[static_cast<size_t>(map[t])];
        k.Keys = std::move(clip.Rotations[t]);
        list.push_back(std::move(k));
        bases.push_back(sd.Ref[static_cast<size_t>(map[t])]);
    }
    auto m = MakeMotion(std::move(list), cfg.FromReference ? &bases : nullptr, clip.SampleRate, cfg.Loop, name);
    if (!m) { why = "no track of the nodes' bones"; }
    return m;
}

int main(int argc, char** argv)
{
    if (argc < 7) { std::printf("anim_run_sets rig.json compat.json samples.json sets.json schedule out.bin [fps]\n"); return 2; }
    SkelCompat::Json rig, samples, setsJ;
    std::string error;
    if (!SkelCompat::ParseJson(ReadAll(argv[1]), rig, error)) { std::printf("rig: %s\n", error.c_str()); return 1; }
    SkelCompat::Config cfg;
    if (!SkelCompat::AppendConfig(ReadAll(argv[2]), L"compat.json", cfg)) { std::printf("config not read\n"); return 1; }
    SkelCompat::FinishConfig(cfg, [](const std::wstring&) { return true; });
    for (const auto& m : cfg.Messages) { std::printf("message: %s\n", SkelCompat::Narrow(m).c_str()); }
    if (cfg.Kawaii.size() != 1) { std::printf("%zu entries (one expected)\n", cfg.Kawaii.size()); return 1; }
    if (!SkelCompat::ParseJson(ReadAll(argv[3]), samples, error)) { std::printf("samples: %s\n", error.c_str()); return 1; }
    if (!SkelCompat::ParseJson(ReadAll(argv[4]), setsJ, error)) { std::printf("sets: %s\n", error.c_str()); return 1; }
    const float fps = argc > 7 ? static_cast<float>(std::atof(argv[7])) : 60.0f;
    // the sets
    SetsData sd;
    for (const auto& n : setsJ.Find("skeleton")->Find("names")->array) { sd.Names.push_back(SkelCompat::Widen(n.string)); }
    for (const auto& q : setsJ.Find("skeleton")->Find("ref_q")->array)
    {
        sd.Ref.push_back({static_cast<float>(q.array[0].number), static_cast<float>(q.array[1].number), static_cast<float>(q.array[2].number),
                          static_cast<float>(q.array[3].number)});
    }
    for (const auto& [path, motions] : setsJ.Find("sets")->object)
    {
        std::vector<std::pair<std::wstring, std::string>> list;
        for (const auto& [m, file] : motions.object) { list.emplace_back(SkelCompat::Widen(m), file.string); }
        sd.Sets.emplace_back(SkelCompat::NormalizeObjectPath(SkelCompat::Widen(path)), std::move(list));
    }
    // the model
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
        const auto& lq = b.Find("local_q")->array;
        const auto& lt = b.Find("local_t")->array;
        Xf l, c;
        c.R = {static_cast<float>(q[0].number), static_cast<float>(q[1].number), static_cast<float>(q[2].number), static_cast<float>(q[3].number)};
        c.T = {static_cast<float>(t[0].number), static_cast<float>(t[1].number), static_cast<float>(t[2].number)};
        l.R = {static_cast<float>(lq[0].number), static_cast<float>(lq[1].number), static_cast<float>(lq[2].number), static_cast<float>(lq[3].number)};
        l.T = {static_cast<float>(lt[0].number), static_cast<float>(lt[1].number), static_cast<float>(lt[2].number)};
        refLocal.push_back(l);
        refCs.push_back(c);
    }
    const int n = skel.Count();
    for (int i = 0; i < n; ++i)
    {
        const int p = skel.Parents[static_cast<size_t>(i)];
        skel.RefLength.push_back(p >= 0 ? Size(refCs[static_cast<size_t>(i)].T - refCs[static_cast<size_t>(p)].T) : 0.0f);
        skel.RefLocation.push_back(refCs[static_cast<size_t>(i)].T);
        skel.RefRotation.push_back(refCs[static_cast<size_t>(i)].R);
    }
    // the nodes' bones (as KawaiiRt::Motions::Prepare marks them), on the sets' skeleton
    const auto& nodesCfg = cfg.Kawaii[0].Nodes;
    std::vector<uint8_t> mark(static_cast<size_t>(n), 0);
    for (const auto& node : nodesCfg)
    {
        if (!node.PoseAnimSet.Active()) { continue; }
        if (const int r = skel.Find(node.RootBone); r >= 0) { mark[static_cast<size_t>(r)] = 1; }
        for (const auto& extra : node.AdditionalRootBones)
        {
            if (const int r = skel.Find(extra.Bone); r >= 0) { mark[static_cast<size_t>(r)] = 1; }
        }
    }
    for (int i = 0; i < n; ++i)
    {
        const int p = skel.Parents[static_cast<size_t>(i)];
        if (p >= 0 && mark[static_cast<size_t>(p)]) { mark[static_cast<size_t>(i)] = 1; }
    }
    std::vector<uint8_t> wantBone(sd.Names.size(), 0);
    for (size_t b = 0; b < sd.Names.size(); ++b)
    {
        const int i = skel.Find(sd.Names[b]);
        wantBone[b] = i >= 0 && mark[static_cast<size_t>(i)] ? 1 : 0;
    }
    // the schedule
    struct Part
    {
        std::string Clip;
        float Seconds = 0;
        const SkelCompat::Json* J = nullptr;
    };
    std::vector<Part> parts;
    {
        std::stringstream ss(argv[5]);
        std::string item;
        while (std::getline(ss, item, ','))
        {
            const size_t colon = item.rfind(':');
            Part p;
            p.Clip = item.substr(0, colon);
            p.Seconds = static_cast<float>(std::atof(item.substr(colon + 1).c_str()));
            p.J = samples.Find(p.Clip);
            if (!p.J) { std::printf("no clip %s\n", p.Clip.c_str()); return 1; }
            parts.push_back(p);
        }
    }
    float total = 0;
    for (const auto& p : parts) { total += p.Seconds; }
    std::FILE* out = std::fopen(argv[6], "wb");
    if (!out) { return 1; }
    const float dt = 1.0f / fps;
    const int frames = static_cast<int>(fps * total);
    std::fwrite(&n, 4, 1, out);
    std::fwrite(&frames, 4, 1, out);
    Chain chain(nodesCfg);
    std::vector<uint8_t> changed;
    std::vector<Xf> local(static_cast<size_t>(n)), pose(static_cast<size_t>(n));
    Xf component;
    const int trans = skel.Find(L"Trans"), hip = skel.Find(L"C_Hip_a");
    V3 rootBase{0, 0, 0}, lastRoot{0, 0, 0}, lastPos{0, 0, 0};
    bool havePos = false;
    float speed = 0.0f;
    double nextLook = 0.0;
    std::vector<std::wstring> nodeMotion(nodesCfg.size());
    std::map<std::wstring, std::shared_ptr<const Node::Motion>> decoded;
    size_t partIndex = 0;
    float partStart = 0.0f;
    for (int f = 0; f < frames; ++f)
    {
        const float t = static_cast<float>(f) * dt;
        while (partIndex + 1 < parts.size() && t >= partStart + parts[partIndex].Seconds)
        {
            partStart += parts[partIndex].Seconds;
            ++partIndex;
            rootBase = component.T;   // (the next clip's root motion from where the last left the component)
        }
        const Part& part = parts[partIndex];
        const SkelCompat::Json& clip = *part.J;
        std::vector<int> clipBone;
        for (const auto& b : clip.Find("bones")->array) { clipBone.push_back(skel.Find(SkelCompat::Widen(b.string))); }
        const auto& framesJ = clip.Find("poses")->array;
        const int clipFrames = static_cast<int>(framesJ.size());
        const float length = static_cast<float>(clip.Find("length")->number);
        const float playing = t - partStart;
        const float loops = std::floor(playing / length);
        const float at = (playing - loops * length) / length * static_cast<float>(clipFrames - 1);
        const int k0 = std::min(clipFrames - 1, static_cast<int>(at));
        const int k1 = std::min(clipFrames - 1, k0 + 1);
        const float w = at - static_cast<float>(k0);
        local = refLocal;
        V3 root{0, 0, 0}, travel{0, 0, 0};
        int transK = -1;
        for (size_t k = 0; k < clipBone.size(); ++k) { if (clipBone[k] == trans) { transK = static_cast<int>(k); } }
        const auto key = [&](int fr, size_t k) {
            const auto& v = framesJ[static_cast<size_t>(fr)].array[k].array;
            Xf x;
            x.R = Normalized(Q4{static_cast<float>(v[0].number), static_cast<float>(v[1].number), static_cast<float>(v[2].number), static_cast<float>(v[3].number)});
            x.T = {static_cast<float>(v[4].number), static_cast<float>(v[5].number), static_cast<float>(v[6].number)};
            return x;
        };
        if (transK >= 0) { travel = key(clipFrames - 1, static_cast<size_t>(transK)).T - key(0, static_cast<size_t>(transK)).T; }
        for (size_t k = 0; k < clipBone.size(); ++k)
        {
            const int b = clipBone[k];
            if (b < 0) { continue; }
            const Xf a = key(k0, k), c = key(k1, k);
            const V3 tt = a.T + (c.T - a.T) * w;
            if (b == trans)
            {
                root = tt - key(0, k).T + travel * loops;
                continue;
            }
            local[static_cast<size_t>(b)].R = Nlerp(a.R, c.R, w);
            if (b == hip) { local[static_cast<size_t>(b)].T = tt; }
        }
        component.T = rootBase + root;
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
        // the motions (KawaiiRt::Motions::Before)
        {
            V3 d = component.T - lastPos;
            d.Z = 0.0f;
            const float v = havePos ? Size(d) / dt : 0.0f;
            if (v < 3000.0f) { speed += (v - speed) * std::min(1.0f, dt / 0.15f); }
            lastPos = component.T;
            havePos = true;
        }
        if (t >= nextLook)
        {
            nextLook = t + 0.1;
            const std::wstring playingName = SkelCompat::Widen(part.Clip);
            const bool battle = part.Clip.rfind("B_", 0) == 0;
            for (size_t k = 0; k < nodesCfg.size(); ++k)
            {
                const auto& a = nodesCfg[k].PoseAnimSet;
                if (!a.Active()) { continue; }
                const auto find = [&](const std::wstring& name) -> const std::string* {
                    for (const auto& path : a.Sets)
                    {
                        for (const auto& [setPath, list] : sd.Sets)
                        {
                            if (!SkelCompat::NameEquals(setPath, path)) { continue; }
                            for (const auto& [m, file] : list)
                            {
                                if (SkelCompat::NameEquals(m, name)) { return &file; }
                            }
                        }
                    }
                    return nullptr;
                };
                const bool moving = speed > a.MovingSpeed;
                const std::wstring pick = SkelCompat::KawaiiAnimSetMotion(a, playingName, battle, moving, [&](const std::wstring& m) { return find(m) != nullptr; });
                if (pick == nodeMotion[k]) { continue; }
                std::shared_ptr<const Node::Motion> motion;
                if (const std::string* file = pick.empty() ? nullptr : find(pick))
                {
                    const std::wstring cacheKey = pick + (a.FromReference ? L"|r" : L"|f");
                    auto it = decoded.find(cacheKey);
                    if (it == decoded.end())
                    {
                        std::string why;
                        auto m = DecodeFile(*file, pick, sd, wantBone, a, why);
                        std::printf("  decoded %s: %s\n", SkelCompat::Narrow(pick).c_str(),
                                    m ? (std::to_string(m->Tracks->size()) + " tracks, " + std::to_string(m->Tracks->front().Keys.size()) + " keys, " +
                                         (m->Loop ? "loop" : "holds")).c_str()
                                      : why.c_str());
                        it = decoded.emplace(cacheKey, m).first;
                    }
                    motion = it->second;
                }
                chain.Nodes[k].PlayMotion(motion, a.BlendSeconds);
                if (k == 0 || nodeMotion[k].empty() != pick.empty() || true)
                {
                    std::printf("%6.2f s  %-12s %-26s plays %s (character: %s%s%s)\n", t, SkelCompat::Narrow(nodesCfg[k].Name).c_str(), "",
                                pick.empty() ? "(none)" : SkelCompat::Narrow(pick).c_str(), part.Clip.c_str(), battle ? ", battle" : "", moving ? ", moving" : "");
                }
                nodeMotion[k] = pick;
            }
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
    std::printf("wrote %d frames of %d bones (%.1f s)\n", frames, n, total);
    return 0;
}
