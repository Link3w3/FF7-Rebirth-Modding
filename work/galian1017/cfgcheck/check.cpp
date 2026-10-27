#include "/work/skelcompat36/src/SkelCompatCore.hpp"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <filesystem>
#include <algorithm>
using namespace SkelCompat;
int main(int argc, char** argv)
{
    Config cfg;
    std::vector<std::string> files;
    for (auto& e : std::filesystem::directory_iterator(argv[1]))
        if (e.path().extension() == ".json") files.push_back(e.path().string());
    std::sort(files.begin(), files.end());
    for (auto& f : files)
    {
        std::ifstream in(f, std::ios::binary); std::stringstream ss; ss << in.rdbuf();
        AppendConfig(ss.str(), Widen(std::filesystem::path(f).filename().string()), cfg);
    }
    // argv[2..]: the paks installed (none given: every pak counts as installed)
    std::vector<std::wstring> installed;
    for (int k = 2; k < argc; ++k) installed.push_back(Widen(argv[k]));
    FinishConfig(cfg, [&](std::wstring_view pak) {
        if (installed.empty()) return true;
        return std::any_of(installed.begin(), installed.end(), [&](const std::wstring& p) { return NameEquals(p, pak); });
    });
    for (auto& m : cfg.Messages) std::printf("MSG %s\n", Narrow(m).c_str());
    for (auto& row : cfg.AnimSets)
    {
        std::string chars; for (auto& c : row.Characters) chars += Narrow(c).substr(Narrow(c).rfind('.') + 1) + " ";
        std::printf("ROW %s\n  origin=%s override=%d moves=%zu battle=%zu skeleton=%s player=%s packassets=%zu preload=%zu shooter=%d forms=%zu\n", chars.c_str(),
                    Narrow(row.Origin).c_str(), row.Override, row.Moves.size(), row.Battle.size(), Narrow(row.Skeleton).c_str(), Narrow(row.Player).c_str(),
                    row.PackAssets.size(), row.Preload.size(), row.Shooting.On, row.Forms.List.size());
        for (auto& b : row.Battle) std::printf("   battle source %s as %s\n", Narrow(b.Path).c_str(), Narrow(b.As).c_str());
        for (auto& a : row.Abilities)
        {
            std::printf("   abilities %s: %zu commands, %zu limits, %zu weapon\n", Narrow(a.Pack).c_str(), a.Commands.size(), a.Limits.size(), a.Weapons.size());
        }
        for (auto& f : row.Forms.List)
        {
            std::printf("   form %s pack=%s model=%s anim=%s scale=%.2f shooter=%d armor=%d seconds=%.0f sets=%zu entrance=%d shots=%zu\n", Narrow(f.Name).c_str(),
                        Narrow(f.Pack).c_str(), Narrow(f.Model).c_str(), Narrow(f.AnimClass).c_str(), f.Scale, f.Shooting, f.SuperArmor, f.Seconds, f.Sets.size(),
                        f.Entrance.On, f.Entrance.Shots.size());
            for (auto& s : f.Sets) std::printf("      set %s -> %s\n", Narrow(s.first).c_str(), Narrow(s.second).c_str());
            for (auto& m : f.Meshes) std::printf("      part %s socket=%s follow=%d\n", Narrow(m.Mesh).c_str(), Narrow(m.Socket).c_str(), m.FollowPose);
        }
        size_t galian = std::count_if(row.Moves.begin(), row.Moves.end(), [](const AnimMove& m) { return Narrow(m.Set) == "Battle07" || Narrow(m.Set) == "Battle08"; });
        size_t chains = std::count_if(row.Moves.begin(), row.Moves.end(), [](const AnimMove& m) { return !m.Chain.empty(); });
        std::printf("   %zu moves of Battle07/08, %zu chains\n", galian, chains);
    }
    return 0;
}
