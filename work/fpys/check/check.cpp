#include "/work/skelcompat36/src/SkelCompatCore.hpp"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <filesystem>
#include <algorithm>
#include <set>
using namespace SkelCompat;
// check <installed paks, comma separated> <json files...>
int main(int argc, char** argv)
{
    std::set<std::string> paks;
    { std::stringstream ss(argv[1]); std::string p; while (std::getline(ss, p, ',')) paks.insert(p); }
    Config cfg;
    for (int i = 2; i < argc; ++i)
    {
        std::ifstream in(argv[i], std::ios::binary); std::stringstream ss; ss << in.rdbuf();
        if (!AppendConfig(ss.str(), Widen(std::filesystem::path(argv[i]).filename().string()), cfg)) std::printf("FILE NOT READ %s\n", argv[i]);
    }
    FinishConfig(cfg, [&](std::wstring_view name) { return paks.count(Narrow(std::wstring(name))) > 0; });
    for (auto& m : cfg.Messages) std::printf("MSG %s\n", Narrow(m).c_str());
    for (auto& p : cfg.Pairs)
    {
        std::string anims; for (auto& a : p.Animation) anims += Narrow(a).substr(Narrow(a).rfind('.') + 1) + " ";
        std::printf("PAIR use=%d receiving=%s anims=[%s] hub=%s proportions=%d carry_sockets=%d origin=%s\n", (int)p.Use,
                    Narrow(p.Receiving).substr(Narrow(p.Receiving).rfind('.') + 1).c_str(), anims.c_str(),
                    p.FamilyHub.empty() ? "-" : Narrow(p.FamilyHub).substr(Narrow(p.FamilyHub).rfind('.') + 1).c_str(), p.KeepProportions, p.CarrySockets, Narrow(p.Origin).c_str());
    }
    for (auto& s : cfg.ProportionSkeletons()) { std::printf("PROPORTIONS %s\n", Narrow(s).c_str()); for (const auto& b : cfg.ProportionBonesOf(s)) std::printf("   proportion_bones %s\n", Narrow(b).c_str()); }
    for (auto& row : cfg.AnimSets)
    {
        std::string chars; for (auto& c : row.Characters) chars += Narrow(c).substr(Narrow(c).rfind('.') + 1) + " ";
        std::printf("ROW %s origin=%s moves=%zu battle=%zu field=%zu player=%s abilities=%zu forms=%zu\n", chars.c_str(),
                    Narrow(row.Origin).c_str(), row.Moves.size(), row.Battle.size(), row.Field.size(), Narrow(row.Player).c_str(),
                    row.Abilities.size(), row.Forms.List.size());
        for (auto& a : row.Abilities)
        {
            std::string cmds; for (auto& c : a.Commands) cmds += Narrow(c) + " ";
            std::printf("   abilities %s: commands [%s] weapons %zu\n", Narrow(a.Pack).c_str(), cmds.c_str(), a.Weapons.size());
        }
        for (auto& m : row.Moves) if (NameEquals(m.Set, L"Battle00")) std::printf("   move %s/%s -> %s\n", Narrow(m.Set).c_str(), Narrow(m.Key).c_str(), Narrow(m.Animation).c_str());
        for (auto& f : row.Forms.List) std::printf("   form %s pack=%s model=%s\n", Narrow(f.Name).c_str(), Narrow(f.Pack).c_str(), Narrow(f.Model).c_str());
    }
    return 0;
}
