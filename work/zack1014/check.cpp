#include "/work/skelcompat33/src/SkelCompatCore.hpp"
#include <cstdio>
#include <fstream>
#include <sstream>
using namespace SkelCompat;
static std::string ReadAll(const char* p) { std::ifstream f(p, std::ios::binary); std::stringstream s; s << f.rdbuf(); return s.str(); }
int main(int argc, char** argv)
{
    Config cfg;
    for (int i = 1; i < argc; ++i)
    {
        std::string text = ReadAll(argv[i]);
        if (!AppendConfig(text, Widen(argv[i]), cfg)) { std::printf("PARSE FAILED %s\n", argv[i]); return 1; }
    }
    const auto installed = [](const std::wstring& n) {
        for (const wchar_t* p : {L"FullyPlayableSephirothDataAssets_P", L"OGSephiroth_P", L"SEPV2_P", L"Weapons Plus Ultra_P"})
            if (NameEquals(n, p)) return true;
        return false; };
    FinishConfig(cfg, installed);
    for (const auto& m : cfg.Messages) std::printf("MSG %s\n", Narrow(m).c_str());
    for (const auto& p : cfg.Pairs)
    {
        std::printf("PAIR use=%d receiving=%s hub=%s proportions=%d\n", (int)p.Use, Narrow(p.Receiving).c_str(), Narrow(p.FamilyHub).c_str(), (int)p.KeepProportions);
        for (const auto& a : p.Animation) std::printf("    anim %s\n", Narrow(a).c_str());
    }
    for (const auto& s : cfg.ProportionSkeletons()) std::printf("PROPORTIONS ON %s\n", Narrow(s).c_str());
    return 0;
}
