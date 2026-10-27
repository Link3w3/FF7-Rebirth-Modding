#include "/work/skelcompat36/src/SkelCompatCore.hpp"
#include <cstdio>
#include <fstream>
#include <sstream>
using namespace SkelCompat;
int main(int argc, char** argv)
{
    std::ifstream f(argv[1], std::ios::binary);
    std::stringstream ss; ss << f.rdbuf();
    Config cfg;
    bool ok = AppendConfig(ss.str(), L"test.json", cfg);
    FinishConfig(cfg, [](std::wstring_view) { return true; });
    std::printf("append ok %d, rows %zu, pairs %zu, messages %zu\n", ok, cfg.AnimSets.size(), cfg.Pairs.size(), cfg.Messages.size());
    for (auto& m : cfg.Messages) std::printf("  MSG %s\n", Narrow(m).c_str());
    if (!cfg.AnimSets.empty())
    {
        const auto& r = cfg.AnimSets.front();
        std::printf("row 0: characters %zu, moves %zu\n", r.Characters.size(), r.Moves.size());
        for (auto& mv : r.Moves) std::printf("   %s/%s -> %s\n", Narrow(mv.Set).c_str(), Narrow(mv.Key).c_str(), Narrow(mv.Animation).c_str());
        size_t withMoves = 0; for (auto& row : cfg.AnimSets) withMoves += !row.Moves.empty();
        std::printf("rows with moves: %zu of %zu\n", withMoves, cfg.AnimSets.size());
    }
    return 0;
}
