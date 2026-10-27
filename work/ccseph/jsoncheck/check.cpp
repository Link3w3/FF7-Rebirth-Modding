#include "/work/cacs3146/src/SkelCompatCore.hpp"
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
    std::printf("append ok %d, messages %zu, kawaii sets %zu\n", ok, cfg.Messages.size(), cfg.Kawaii.size());
    for (auto& m : cfg.Messages) std::printf("  MSG %s\n", Narrow(m).c_str());
    for (auto& k : cfg.Kawaii)
    {
        std::printf("set: %zu models (%s), %zu nodes\n", k.Models.size(), Narrow(k.Models.empty() ? std::wstring() : k.Models[0]).c_str(), k.Nodes.size());
        for (auto& n : k.Nodes) std::printf("   node root %s\n", Narrow(n.RootBone).c_str());
    }
    return 0;
}
