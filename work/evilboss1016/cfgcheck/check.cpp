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
    FinishConfig(cfg, [](std::wstring_view) { return true; });
    for (auto& m : cfg.Messages) std::printf("MSG %s\n", Narrow(m).c_str());
    for (auto& row : cfg.AnimSets)
    {
        std::string chars; for (auto& c : row.Characters) chars += Narrow(c) + " ";
        if (chars.find("PC0010_10") == std::string::npos && chars.find("PC0010_20") == std::string::npos) continue;
        std::printf("ROW %s origin=%s override=%d moves=%zu battle=%zu skeleton=%s sockets=%zu packassets=%zu\n", chars.c_str(), Narrow(row.Origin).c_str(),
                    row.Override, row.Moves.size(), row.Battle.size(), Narrow(row.Skeleton).c_str(), row.Sockets.size(), row.PackAssets.size());
        for (auto& s : row.Sockets) std::printf("   socket %s -> %s\n", Narrow(s.first).c_str(), Narrow(s.second).c_str());
        for (auto& p : row.PackAssets) std::printf("   pack %s\n", Narrow(p).c_str());
        int n = 0;
        for (auto& m : row.Moves) { if (n++ < 4) std::printf("   move %s/%s -> %s\n", Narrow(m.Set).c_str(), Narrow(m.Key).c_str(), Narrow(m.Animation).c_str()); }
        size_t built = std::count_if(row.Moves.begin(), row.Moves.end(), [](const AnimMove& m){ return Narrow(m.Animation).find("EvilCloudBoss") != std::string::npos; });
        std::printf("   %zu moves from EvilCloudBoss\n", built);
        for (auto& b : row.Battle) std::printf("   battle source %s\n", Narrow(b.Path).c_str());
    }
    return 0;
}
