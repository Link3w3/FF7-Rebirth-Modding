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
    for (auto& e : std::filesystem::directory_iterator(argv[1])) if (e.path().extension() == ".json") files.push_back(e.path().string());
    std::sort(files.begin(), files.end());
    for (auto& f : files) { std::ifstream in(f, std::ios::binary); std::stringstream ss; ss << in.rdbuf(); AppendConfig(ss.str(), Widen(std::filesystem::path(f).filename().string()), cfg); }
    FinishConfig(cfg, [](std::wstring_view) { return true; });
    for (auto& row : cfg.AnimSets)
        for (auto& form : row.Forms.List)
            if (form.Camera.Set || !form.AbilityCameras.empty())
            {
                std::printf("%s %s camera set=%d %.0f back %.0f up fov %.0f blend %.1f\n", Narrow(row.Characters[0]).c_str(), Narrow(form.Name).c_str(), form.Camera.Set,
                            form.Camera.Distance, form.Camera.Height, form.Camera.Fov, form.Camera.Blend);
                for (auto& a : form.AbilityCameras)
                    std::printf("   while %s: %.0f back %.0f up blend %.1f (matches M_SMN_103_atk001_01: %d)\n", Narrow(a.Abilities[0]).c_str(), a.Camera.Distance,
                                a.Camera.Height, a.Camera.Blend, a.Matches(L"M_SMN_103_atk001_01"));
            }
    return 0;
}
