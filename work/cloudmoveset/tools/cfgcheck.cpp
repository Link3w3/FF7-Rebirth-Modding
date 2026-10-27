// Off-target check of compat files and skins with the mod's own parser (SkelCompatCore.hpp, g++ -std=c++20):
//   cfgcheck <compat .json>... -- <skin folder name> <skin.json> ...
// Prints the parser's messages, each animation-set row's sets, moves, movesets and forms, and each skin's weapon socket.
#include "/work/cacs3151/src/SkelCompatCore.hpp"

#include <cstdio>
#include <fstream>
#include <map>
#include <sstream>

using namespace SkelCompat;

static std::string ReadAll(const char* path)
{
    std::ifstream f(path, std::ios::binary);
    std::stringstream s;
    s << f.rdbuf();
    return s.str();
}

static std::string N(const std::wstring& w)
{
    std::string s;
    for (wchar_t c : w) { s += c < 128 ? static_cast<char>(c) : '?'; }
    return s;
}

int main(int argc, char** argv)
{
    Config cfg;
    int i = 1;
    for (; i < argc && std::string(argv[i]) != "--"; ++i)
    {
        const std::string text = ReadAll(argv[i]);
        std::wstring origin;
        for (const char* p = argv[i]; *p; ++p) { origin += static_cast<wchar_t>(*p); }
        const bool ok = AppendConfig(text, origin, cfg);
        std::printf("%s: %s (%zu bytes)\n", argv[i], ok ? "read" : "NOT READ", text.size());
    }
    for (++i; i + 1 < argc; i += 2)
    {
        std::wstring folder;
        for (const char* p = argv[i]; *p; ++p) { folder += static_cast<wchar_t>(*p); }
        const bool ok = AppendSkin(ReadAll(argv[i + 1]), folder, cfg);
        std::printf("skin %s: %s\n", argv[i], ok ? "read" : "NOT READ");
    }
    FinishConfig(cfg, [](const std::wstring&) { return true; });
    AttachSkins(cfg, true);
    std::printf("messages: %zu\n", cfg.Messages.size());
    for (const auto& m : cfg.Messages) { std::printf("  MSG %s\n", N(m).c_str()); }
    size_t r = 0;
    for (const auto& row : cfg.AnimSets)
    {
        std::map<std::wstring, int> sets;
        for (const auto& m : row.Moves) { ++sets[m.Set]; }
        std::printf("row %zu %s (%s): %zu moves", r++, row.Characters.empty() ? "-" : N(row.Characters[0]).c_str(), N(row.Origin).c_str(), row.Moves.size());
        for (const auto& [s, n] : sets) { std::printf(" %s:%d", N(s).c_str(), n); }
        std::printf("\n   battle sources as Battle11:");
        for (const auto& b : row.Battle)
        {
            if (b.As == L"Battle11") { std::printf(" %s", N(b.Path).c_str()); }
        }
        std::printf("\n   forms:");
        for (const auto& f : row.Forms.List) { std::printf(" %s[%s]", N(f.Name).c_str(), N(f.Pack).c_str()); }
        std::printf("\n   movesets:");
        for (const auto& f : row.Forms.Movesets) { std::printf(" %s[%s] socket %s", N(f.Name).c_str(), N(f.Pack).c_str(), N(f.WeaponSocket).c_str()); }
        std::printf("\n");
    }
    for (const auto& skin : cfg.Skins)
    {
        std::printf("skin %s: weapon %s, weapon_field_socket '%s'\n", N(skin.Folder).c_str(), N(skin.Weapon).c_str(), N(skin.WeaponFieldSocket).c_str());
    }
    return 0;
}
