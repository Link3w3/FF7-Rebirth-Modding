#include "SkelCompatCore.hpp"
#include <cstdio>
#include <fstream>
#include <sstream>
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
    std::printf("pairs: %zu\n", cfg.Pairs.size());
    for (const auto& p : cfg.Pairs)
    {
        std::printf("  method=%d receiving=%s hub=%s anims=%zu paks=%zu\n", (int)p.Use, N(p.Receiving).c_str(), N(p.Hub).c_str(), p.Animation.size(), p.RequiresPaks.size());
        for (const auto& a : p.Animation) std::printf("     anim %s\n", N(a).c_str());
        for (const auto& r : p.RequiresPaks) std::printf("     needs %s\n", N(r).c_str());
    }
    return 0;
}
