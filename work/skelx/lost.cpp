#include "../skelcompat/src/SkelCompatCore.hpp"
#include <cstdio>
#include <fstream>
#include <map>
using namespace SkelCompat;
static BoneTable Load(const char* path) { BoneTable t; std::ifstream f(path); std::string n; int p; while (f >> n >> p) { t.Names.push_back(Widen(n)); t.Parents.push_back(p); } return t; }
static void Lost(const char* label, const BoneTable& from, const BoneTable& to)
{
    const auto map = BuildTrackRemap(from, to);
    std::map<std::wstring, int> kinds; std::wstring other;
    int n = 0;
    for (size_t i = 0; i < map.size(); ++i)
    {
        if (map[i] >= 0) continue;
        const std::wstring& b = from.Names[i];
        std::wstring k = b.find(L"_Phy") != std::wstring::npos ? L"Phy" : b.find(L"_Spo") != std::wstring::npos ? L"Spo" : b.find(L"_End") != std::wstring::npos ? L"End" : L"other";
        kinds[k]++;
        if (k == L"other" && n++ < 80) other += b + L" ";
    }
    std::printf("%s lost tracks by kind:", label); for (auto& [k, v] : kinds) std::printf(" %s=%d", Narrow(k).c_str(), v); std::printf("\n  other: %s\n", Narrow(other).c_str());
}
int main()
{
    const BoneTable cs = Load("PC0000_00_Skeleton.bones"), ss = Load("PC0010_00_Skeleton.bones"), vs = Load("PC0011_00_Skeleton.bones");
    Lost("Vincent->Cloud", vs, cs); Lost("Seph->Cloud", ss, cs); Lost("Cloud->Seph", cs, ss);
}
