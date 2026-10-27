#include "/work/cacs3120/src/SkelCompatCore.hpp"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <filesystem>
#include <algorithm>
#include <map>
using namespace SkelCompat;
int main(int argc, char** argv)
{
    for (int a = 1; a < argc; ++a)
    {
        Config cfg;
        std::ifstream in(argv[a], std::ios::binary); std::stringstream ss; ss << in.rdbuf();
        AppendConfig(ss.str(), Widen(std::filesystem::path(argv[a]).filename().string()), cfg);
        FinishConfig(cfg, [](std::wstring_view) { return true; });
        std::printf("== %s: %zu rows, %zu messages\n", argv[a], cfg.AnimSets.size(), cfg.Messages.size());
        for (auto& m : cfg.Messages) std::printf("MSG %s\n", Narrow(m).c_str());
        for (auto& row : cfg.AnimSets)
        {
            std::map<std::string, int> per;
            for (auto& m : row.Moves) per[Narrow(m.Set)]++;
            std::printf("ROW %zu chars, %zu moves, %zu battle sources, forms %zu\n", row.Characters.size(), row.Moves.size(), row.Battle.size(), row.Forms.List.size());
            for (auto& [k, v] : per) std::printf("   set %s: %d moves\n", k.c_str(), v);
            for (auto& f : row.Forms.List) std::printf("   form %s pack=%s\n", Narrow(f.Name).c_str(), Narrow(f.Pack).c_str());
            for (auto& m : row.Moves)
                if (Narrow(m.Set) == "Battle07" && (Narrow(m.Key) == "B_AtkLimit02_0" || Narrow(m.Key) == "B_AtkStab01" || Narrow(m.Key) == "B_NAttack01_0"))
                {
                    std::printf("   move %s/%s -> %s (chain %zu, clips %zu)\n", Narrow(m.Set).c_str(), Narrow(m.Key).c_str(), Narrow(m.Animation).c_str(), m.Chain.size(), m.Clips.size());
                }
        }
    }
    return 0;
}
