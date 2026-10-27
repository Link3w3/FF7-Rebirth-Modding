// Parses compat files with the game mod's own core (SkelCompatCore.hpp) and prints its notes, forms and moves per set.
#include "SkelCompatCore.hpp"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <map>
using namespace SkelCompat;
static std::string N(const std::wstring& w) { return std::string(w.begin(), w.end()); }
int main(int argc, char** argv)
{
    Config cfg;
    for (int i = 1; i < argc; ++i)
    {
        std::ifstream f(argv[i], std::ios::binary);
        std::stringstream s; s << f.rdbuf();
        std::string a(argv[i]);
        AppendConfig(s.str(), std::wstring(a.begin(), a.end()), cfg);
    }
    FinishConfig(cfg, [](const std::wstring&) { return true; });
    std::printf("messages: %zu\n", cfg.Messages.size());
    for (const auto& m : cfg.Messages) std::printf("  %s\n", N(m).c_str());
    for (const auto& row : cfg.AnimSets)
    {
        std::map<std::wstring, int> sets;
        for (const auto& m : row.Moves) sets[m.Set]++;
        std::printf("row: %zu moves;", row.Moves.size());
        for (auto& [k, v] : sets) std::printf(" %s=%d", N(k).c_str(), v);
        std::printf("\n  forms:");
        for (const auto& f : row.Forms.List)
            std::printf(" [%s pack=%s model=%s abp=%s scale=%.2f hide=%d armor=%d s=%.0f cd=%.0f fx=%zu snd=%zu]", N(f.Name).c_str(), N(f.Pack).c_str(),
                        N(f.Model.substr(f.Model.rfind(L'/') == std::wstring::npos ? 0 : f.Model.rfind(L'/') + 1)).c_str(),
                        N(f.AnimClass.substr(f.AnimClass.rfind(L'/') == std::wstring::npos ? 0 : f.AnimClass.rfind(L'/') + 1)).c_str(),
                        f.Scale, f.HideWeapon, f.SuperArmor, f.Seconds, f.Cooldown, f.Effects.size(), f.Sounds.size());
        std::printf("\n");
    }
    return 0;
}
