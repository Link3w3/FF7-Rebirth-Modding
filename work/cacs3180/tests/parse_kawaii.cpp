// (3.17.0) A compat file read as the game mod reads it: its messages, and per "kawaii" entry its nodes, shapes and sync
// bones.   parse_kawaii file.json [...]
#include "../src/SkelCompatCore.hpp"
#include <cstdio>
#include <fstream>
#include <sstream>
int main(int argc, char** argv)
{
    int bad = 0;
    for (int a = 1; a < argc; ++a)
    {
        std::ifstream f(argv[a], std::ios::binary);
        std::stringstream s;
        s << f.rdbuf();
        SkelCompat::Config cfg;
        const bool ok = SkelCompat::AppendConfig(s.str(), SkelCompat::Widen(argv[a]), cfg);
        SkelCompat::FinishConfig(cfg, [](const std::wstring&) { return true; });
        std::printf("%s: %s, %zu message(s)\n", argv[a], ok ? "read" : "NOT READ", cfg.Messages.size());
        for (const auto& m : cfg.Messages) { std::printf("  message: %s\n", SkelCompat::Narrow(m).c_str()); }
        bad += ok ? 0 : 1;
        bad += static_cast<int>(cfg.Messages.size());
        for (const auto& set : cfg.Kawaii)
        {
            size_t syncs = 0, targets = 0, shapes = 0;
            for (const auto& n : set.Nodes)
            {
                syncs += n.SyncBones.size();
                for (const auto& sb : n.SyncBones) { targets += sb.Targets.size(); }
                shapes += n.Spheres.size() + n.Capsules.size() + n.TaperedCapsules.size() + n.Boxes.size() + n.Planes.size();
            }
            std::printf("  entry %s: %zu nodes, %zu shapes, %zu sync bones (%zu targets)\n", SkelCompat::Narrow(set.Models.front()).c_str(), set.Nodes.size(), shapes,
                        syncs, targets);
        }
    }
    return bad ? 1 : 0;
}
