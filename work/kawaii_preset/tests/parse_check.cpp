// Reads a compat file with the game mod's own parser: its messages, its "kawaii" entries and their nodes.
#include "/work/cacs3144/src/SkelCompatCore.hpp"
#include <cstdio>
#include <fstream>
#include <sstream>
int main(int argc, char** argv)
{
    std::ifstream f(argv[1], std::ios::binary);
    std::stringstream s;
    s << f.rdbuf();
    SkelCompat::Config cfg;
    if (!SkelCompat::AppendConfig(s.str(), L"SephirothKawaii.json", cfg)) { std::printf("NOT READ\n"); return 1; }
    SkelCompat::FinishConfig(cfg, [](const std::wstring&) { return true; });
    for (const auto& m : cfg.Messages) { std::printf("message: %s\n", SkelCompat::Narrow(m).c_str()); }
    for (const auto& k : cfg.Kawaii)
    {
        size_t ex = 0, sub = 0, shapes = 0;
        for (const auto& n : k.Nodes) { ex += n.ExcludeBones.size(); sub += n.BoneSubdivisionCount > 0; shapes += n.Spheres.size() + n.Capsules.size() + n.TaperedCapsules.size(); }
        std::printf("entry: %s | %zu node(s), %zu model(s), paks %zu, disable_bonamik %d (%zu named), %zu exclusions, %zu subdivided, %zu shapes\n",
                    SkelCompat::Narrow(k.Models.empty() ? L"" : k.Models[0]).c_str(), k.Nodes.size(), k.Models.size(), k.RequiresPaks.size(),
                    k.DisableBonamik ? 1 : 0, k.DisableBonamikAssets.size(), ex, sub, shapes); std::printf("   disable_kinedriver %d (%zu named)\n", k.DisableKineDriver ? 1 : 0, k.DisableKineDriverAssets.size());
    }
    return 0;
}
