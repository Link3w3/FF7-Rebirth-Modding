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
        if (!AppendConfig(ss.str(), Widen(std::filesystem::path(f).filename().string()), cfg)) std::printf("FILE NOT READ %s\n", f.c_str());
    }
    FinishConfig(cfg, [](std::wstring_view) { return true; });
    for (auto& m : cfg.Messages) std::printf("MSG %s\n", Narrow(m).c_str());
    for (auto& row : cfg.AnimSets)
    {
        std::string chars; for (auto& c : row.Characters) chars += Narrow(c).substr(Narrow(c).rfind('.') + 1) + " ";
        if (chars.find("PC0010_") == std::string::npos) continue;
        std::printf("ROW %s origin=%s override=%d moves=%zu battle=%zu field=%zu player=%s abilities=%zu cutsocket=%s packassets=%zu\n", chars.c_str(),
                    Narrow(row.Origin).c_str(), row.Override, row.Moves.size(), row.Battle.size(), row.Field.size(), Narrow(row.Player).c_str(),
                    row.Abilities.size(), Narrow(row.CutsceneWeaponSocket).c_str(), row.PackAssets.size());
        for (auto& b : row.Battle) std::printf("   battle source %s\n", Narrow(b.Path).c_str());
        for (auto& b : row.Field) std::printf("   field source %s\n", Narrow(b.Path).c_str());
        for (auto& a : row.Abilities) { std::printf("   abilities pack %s weapons %zu\n", Narrow(a.Pack).c_str(), a.Weapons.size());
            for (auto& w : a.Weapons) std::printf("      %s -> %s\n", Narrow(w.first).c_str(), Narrow(w.second).c_str()); }
        for (auto& p : row.PackAssets) std::printf("   pack %s\n", Narrow(p).c_str());
    }
    return 0;
}
