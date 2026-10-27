// skins_tool: Create a Character System skins from a shell, with the editor's own code (SkinCore.hpp).
//   skins_tool check <skin folder>                 reads its skin.json the way the editor and the game mod read it, checks
//                                                  every file it names is there, prints it written back (WriteSkinJson)
//   skins_tool container <skins dir> <mods dir>    remakes <mods dir>/CreateACharacterSkins_P.utoc/.ucas/.pak from every
//                                                  skins/<Folder>/skin.json, as the editor's Install Skins does
//                                                  (RemakeSkinsContainer): the three written in place once all three
//                                                  can be opened for writing
#include "SkinCore.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>

namespace fs = std::filesystem;

static bool LoadBytes(const fs::path& p, CacsSound::Bytes& out)
{
    std::ifstream f(p, std::ios::binary);
    if (!f) { return false; }
    out.assign(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
    return true;
}

static bool LoadText(const fs::path& p, std::string& out)
{
    std::ifstream f(p, std::ios::binary);
    if (!f) { return false; }
    out.assign(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
    return true;
}

static bool ReadSkinFolder(const fs::path& folder, const std::string& name, CacsSkin::SkinFolder& out, std::string& problem)
{
    out = CacsSkin::SkinFolder{};
    out.Folder = name;
    std::string text, error;
    if (!LoadText(folder / "skin.json", text)) { problem = "its skin.json does not read"; return false; }
    if (!CacsSkin::ReadSkinJson(text, out.Info, error)) { problem = error; return false; }
    if (!out.Info.Enabled) { return true; }
    for (CacsSkin::SkinPackage& p : out.Info.Packages)
    {
        if (!LoadBytes(folder / p.File, p.Data) || p.Data.empty()) { problem = p.File + " is missing"; return false; }
        if (p.Data.size() != (p.Size & CacsSkin::SizeMask)) { problem = p.File + " is not the size skin.json gives"; return false; }
        for (CacsSkin::SkinBulk& b : p.Bulk)
        {
            if (!LoadBytes(folder / b.File, b.Data)) { problem = b.File + " is missing"; return false; }
        }
    }
    return true;
}

int main(int argc, char** argv)
{
    if (argc >= 3 && std::string(argv[1]) == "check")
    {
        CacsSkin::SkinFolder skin;
        std::string problem;
        const fs::path folder(argv[2]);
        if (!ReadSkinFolder(folder, folder.filename().string(), skin, problem))
        {
            std::cerr << "NOT OK: " << problem << "\n";
            return 1;
        }
        std::string text;
        LoadText(folder / "skin.json", text);
        const std::string back = CacsSkin::WriteSkinJson(skin.Info);
        std::cout << back;
        std::cerr << "OK: " << skin.Info.Packages.size() << " package(s); written back "
                  << (back == text ? "the same, byte for byte" : "DIFFERENTLY") << "\n";
        return back == text ? 0 : 2;
    }
    if (argc >= 4 && std::string(argv[1]) == "container")
    {
        const fs::path root(argv[2]), mods(argv[3]);
        std::vector<CacsSkin::SkinFolder> skins;
        for (const auto& e : fs::directory_iterator(root))
        {
            if (!e.is_directory() || !fs::exists(e.path() / "skin.json")) { continue; }
            CacsSkin::SkinFolder skin;
            std::string problem;
            const std::string name = e.path().filename().string();
            if (!ReadSkinFolder(e.path(), name, skin, problem))
            {
                std::cout << "    skins/" << name << ": left out of the skins container: " << problem << "\n";
                continue;
            }
            skins.push_back(std::move(skin));
        }
        const CacsSkin::CacheResult cache = CacsSkin::BuildCache(std::move(skins));
        if (!cache.Ok) { std::cout << "The skins container was NOT made: " << cache.Error << "\n"; return 1; }
        const fs::path base = mods / CacsSkin::CacheName;
        const fs::path paths[3] = {base.string() + ".utoc", base.string() + ".ucas", base.string() + ".pak"};
        const CacsSound::Bytes* data[3] = {&cache.Utoc, &cache.Ucas, &cache.Pak};
        for (const fs::path& p : paths)
        {
            if (fs::exists(p))
            {
                std::fstream probe(p, std::ios::binary | std::ios::in | std::ios::out);
                if (!probe) { std::cout << p << " is in use (close the game); the skins container was NOT changed\n"; return 1; }
            }
        }
        for (int i = 0; i < 3; ++i)
        {
            std::ofstream f(paths[i], std::ios::binary | std::ios::trunc);
            f.write(reinterpret_cast<const char*>(data[i]->data()), static_cast<std::streamsize>(data[i]->size()));
            if (!f) { std::cout << "cannot write " << paths[i] << "\n"; return 1; }
        }
        std::cout << "Skins container: " << CacsSkin::CacheName << ".utoc/.ucas/.pak in " << mods << ", " << cache.Packages
                  << " package(s) of every installed skin (" << cache.Ucas.size() / (1024.0 * 1024.0) << " MB)\n";
        for (const std::string& line : cache.Report) { std::cout << "      " << line << "\n"; }
        return 0;
    }
    std::cerr << "usage: skins_tool check <skin folder> | container <skins dir> <mods dir>\n";
    return 2;
}
