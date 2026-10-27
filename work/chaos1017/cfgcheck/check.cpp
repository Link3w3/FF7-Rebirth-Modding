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
    std::vector<std::wstring> installed;
    for (int k = 2; k < argc; ++k) installed.push_back(Widen(argv[k]));
    FinishConfig(cfg, [&](std::wstring_view pak) {
        if (installed.empty()) return true;
        return std::any_of(installed.begin(), installed.end(), [&](const std::wstring& p) { return NameEquals(p, pak); });
    });
    for (auto& m : cfg.Messages) std::printf("MSG %s\n", Narrow(m).c_str());
    for (auto& p : cfg.Pairs)
    {
        std::printf("PAIR %s use=%d recv=%s anims=%zu\n", Narrow(p.Hub).c_str(), (int)p.Use, Narrow(p.Receiving).c_str(), p.Animation.size());
        for (auto& a : p.Animation) std::printf("   member %s\n", Narrow(a).c_str());
    }
    for (auto& row : cfg.AnimSets)
    {
        std::string chars; for (auto& c : row.Characters) chars += Narrow(c).substr(Narrow(c).rfind('.') + 1) + " ";
        if (chars.find("PC0000_00_Cloud_Standard") == std::string::npos) continue;
        std::printf("ROW %s\n  origin=%s moves=%zu packassets=%zu shooter=%d forms=%zu\n", chars.c_str(), Narrow(row.Origin).c_str(), row.Moves.size(),
                    row.PackAssets.size(), row.Shooting.On, row.Forms.List.size());
        for (auto& f : row.Forms.List)
        {
            std::printf("   form %s pack=%s model=%s anim=%s shooter=%d armor=%d seconds=%.0f fly=%d effects=%zu sounds=%zu\n", Narrow(f.Name).c_str(),
                        Narrow(f.Pack).c_str(), Narrow(f.Model).c_str(), Narrow(f.AnimClass).c_str(), f.Shooting, f.SuperArmor, f.Seconds, f.Fly.On, f.Effects.size(), f.Sounds.size());
            if (f.ShooterSet)
            {
                const auto& s = *f.ShooterSet;
                std::printf("      shooter: on=%d folder=%s prefix=%s fly_stance=%s gun_mesh=%s distance=%.0f aim_distance=%.0f pivot=%.0f stand='%s' walking='%s' strafe=%d\n",
                            s.On, Narrow(s.Folder).c_str(), Narrow(s.Prefix).c_str(), Narrow(s.FlyStance).c_str(), Narrow(s.GunMesh).c_str(), s.Distance, s.AimDistance,
                            s.Pivot, Narrow(s.Stand).c_str(), Narrow(s.Walking).c_str(), s.Strafe);
                for (auto& w : s.Weapons)
                    std::printf("      gun %s set=%s fly_set=%s row=%s clip=%d interval=%.2f reload=%.2f range=%.0f upgrades=%zu sounds=%zu muzzle=%s\n   shot %s\n   fly shot %s\n   fly reload %s\n   fly stance %s\n",
                                Narrow(w.Name).c_str(), Narrow(w.Set).c_str(), Narrow(w.FlySet).c_str(), Narrow(w.DamageSource).c_str(), w.Clip, w.Interval, w.Reload, w.Range,
                                w.Upgrades.size(), w.Sounds.size(), Narrow(w.Muzzle.Path).c_str(), Narrow(s.Clip(w, s.Shot)).c_str(), Narrow(s.FlyClip(w, s.Shot)).c_str(),
                                Narrow(s.FlyClip(w, s.Reloading)).c_str(), Narrow(s.Plain(s.FlyStance)).c_str());
            }
        }
        for (auto& p : row.PackAssets) std::printf("   pack asset %s\n", Narrow(p).c_str());
    }
    return 0;
}
