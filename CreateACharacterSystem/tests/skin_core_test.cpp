// Tests of SkinCore.hpp (Create a Character System skins, editor 1.15) against the Python prototype's output.
//
//   g++ -std=c++17 -O2 -I<plugin Private folder> skin_core_test.cpp -o skin_core_test
//   ./skin_core_test <engine-made .utoc> <its skin folder (prototype)> <the prototype's cache folder>
//
// 1. SkinCore reads the container the engine's IoStore commandlet made into the same package bytes and store entries
//    as the prototype's skin folder (skin.json and its Content/ files).
// 2. SkinCore's skins container for the skin folder's parent is byte for byte the prototype's
//    (skinpack.py cache <skins folder> <out>).
// 3. Its own pieces: skin.json written and read back, JSON escapes, the reader on its own container, duplicates and
//    skins that are off, a compressed container refused.
#include "SkinCore.hpp"

#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>

namespace fs = std::filesystem;
using CacsSound::Bytes;

static int Failures = 0;
static int Checks = 0;

#define CHECK(cond, what)                                                                                    \
    do                                                                                                       \
    {                                                                                                        \
        ++Checks;                                                                                            \
        if (!(cond)) { ++Failures; std::cout << "FAIL " << __LINE__ << ": " << what << "\n"; }               \
    } while (0)

static bool Load(const fs::path& path, Bytes& out)
{
    std::ifstream f(path, std::ios::binary);
    if (!f) { return false; }
    out.assign(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
    return true;
}

static std::string LoadText(const fs::path& path)
{
    Bytes b;
    Load(path, b);
    return std::string(b.begin(), b.end());
}

// A skin folder read the way the editor's install step reads one (skin.json, then every file it lists).
static bool ReadSkinFolder(const fs::path& folder, CacsSkin::SkinFolder& out, std::string& error)
{
    out = CacsSkin::SkinFolder{};
    out.Folder = folder.filename().string();
    if (!CacsSkin::ReadSkinJson(LoadText(folder / "skin.json"), out.Info, error)) { return false; }
    for (CacsSkin::SkinPackage& p : out.Info.Packages)
    {
        if (!Load(folder / p.File, p.Data)) { error = "cannot read " + p.File; return false; }
        for (CacsSkin::SkinBulk& b : p.Bulk)
        {
            if (!Load(folder / b.File, b.Data)) { error = "cannot read " + b.File; return false; }
        }
    }
    return true;
}

static void TestEngineContainer(const fs::path& utoc, const fs::path& skinFolder)
{
    Bytes toc, cas;
    CHECK(Load(utoc, toc), "read " << utoc);
    fs::path ucas = utoc;
    ucas.replace_extension(".ucas");
    CHECK(Load(ucas, cas), "read " << ucas);
    CacsSkin::Toc t;
    std::string error;
    const bool tocOk = CacsSkin::ReadToc(toc.data(), toc.size(), t, error);
    CHECK(tocOk, "ReadToc: " << error);
    if (!tocOk) { return; }
    std::cout << "engine container: version " << int(t.Version) << ", " << t.Chunks.size() << " chunks, " << t.Blocks.size() << " blocks, mount " << t.Mount << "\n";
    std::vector<CacsSkin::SkinPackage> packages;
    const bool extracted = CacsSkin::ExtractPackages(t, cas.data(), cas.size(), packages, error);
    CHECK(extracted, "ExtractPackages: " << error);
    CacsSkin::SkinInfo skin;
    const bool readOk = CacsSkin::ReadSkinJson(LoadText(skinFolder / "skin.json"), skin, error);
    CHECK(readOk, "ReadSkinJson (prototype's skin.json): " << error);
    if (!extracted || !readOk) { return; }
    CHECK(packages.size() == skin.Packages.size(), "package count " << packages.size() << " vs skin.json " << skin.Packages.size());
    for (size_t i = 0; i < packages.size() && i < skin.Packages.size(); ++i)
    {
        const CacsSkin::SkinPackage& a = packages[i];
        const CacsSkin::SkinPackage& b = skin.Packages[i];
        CHECK(a.Package == b.Package, "package " << i << ": " << a.Package << " vs " << b.Package);
        CHECK(a.File == b.File, "file " << a.File << " vs " << b.File);
        CHECK(a.Size == b.Size, a.Package << " size " << a.Size << " vs " << b.Size);
        CHECK(a.ExportCount == b.ExportCount, a.Package << " export count");
        CHECK(a.BundleCount == b.BundleCount, a.Package << " bundle count");
        CHECK(a.LoadOrder == b.LoadOrder, a.Package << " load order " << a.LoadOrder << " vs " << b.LoadOrder);
        CHECK(a.Imports == b.Imports, a.Package << " imports");
        Bytes file;
        CHECK(Load(skinFolder / b.File, file), "read " << b.File);
        CHECK(a.Data == file, a.Package << ": the extracted package is not the prototype's file (" << a.Data.size() << " vs " << file.size() << " bytes)");
        CHECK(a.Bulk.size() == b.Bulk.size(), a.Package << " bulk count");
        for (size_t k = 0; k < a.Bulk.size() && k < b.Bulk.size(); ++k)
        {
            CHECK(a.Bulk[k].File == b.Bulk[k].File && a.Bulk[k].Type == b.Bulk[k].Type, a.Package << " bulk " << k);
            Bytes bulk;
            CHECK(Load(skinFolder / b.Bulk[k].File, bulk) && bulk == a.Bulk[k].Data, a.Package << " bulk data " << k);
        }
        std::cout << "  " << a.Package << ": " << a.Data.size() << " bytes, " << a.ExportCount << " export(s), " << a.Imports.size() << " import(s), "
                  << a.Bulk.size() << " bulk\n";
    }
    // the prototype's skin.json fields read back
    CHECK(skin.Name == "Remake Sephiroth", "name " << skin.Name);
    CHECK(skin.Voice == "own", "voice " << skin.Voice);
    CHECK(skin.Characters.size() == 9 && skin.Characters[0] == "PC0000_00_Cloud_Standard", "characters");
    CHECK(skin.Enabled, "enabled by default");
}

static void TestCache(const fs::path& skinsRoot, const fs::path& pythonCache)
{
    std::vector<CacsSkin::SkinFolder> skins;
    std::vector<fs::path> folders;
    for (const auto& entry : fs::directory_iterator(skinsRoot))
    {
        if (entry.is_directory() && fs::exists(entry.path() / "skin.json")) { folders.push_back(entry.path()); }
    }
    for (const fs::path& folder : folders)
    {
        CacsSkin::SkinFolder skin;
        std::string error;
        const bool ok = ReadSkinFolder(folder, skin, error);
        CHECK(ok, "read skin folder " << folder << ": " << error);
        if (ok) { skins.push_back(std::move(skin)); }
    }
    const CacsSkin::CacheResult cache = CacsSkin::BuildCache(std::move(skins));
    CHECK(cache.Ok, "BuildCache: " << cache.Error);
    for (const std::string& line : cache.Report) { std::cout << "  cache: " << line << "\n"; }
    const std::string base = std::string(CacsSkin::CacheName);
    Bytes utoc, ucas, pak;
    CHECK(Load(pythonCache / (base + ".utoc"), utoc), "read the prototype's .utoc");
    CHECK(Load(pythonCache / (base + ".ucas"), ucas), "read the prototype's .ucas");
    CHECK(Load(pythonCache / (base + ".pak"), pak), "read the prototype's .pak");
    CHECK(cache.Utoc == utoc, "the .utoc is not the prototype's (" << cache.Utoc.size() << " vs " << utoc.size() << " bytes)");
    CHECK(cache.Ucas == ucas, "the .ucas is not the prototype's (" << cache.Ucas.size() << " vs " << ucas.size() << " bytes)");
    CHECK(cache.Pak == pak, "the .pak is not the prototype's (" << cache.Pak.size() << " vs " << pak.size() << " bytes)");
    if (cache.Utoc != utoc)
    {
        for (size_t i = 0; i < std::min(cache.Utoc.size(), utoc.size()); ++i)
        {
            if (cache.Utoc[i] != utoc[i]) { std::cout << "  first .utoc difference at byte " << i << "\n"; break; }
        }
    }
    std::cout << "cache: " << cache.Packages << " package(s), .utoc " << cache.Utoc.size() << ", .ucas " << cache.Ucas.size() << ", .pak " << cache.Pak.size() << " bytes\n";

    // read back with SkinCore's own reader: the same packages come out
    CacsSkin::Toc t;
    std::string error;
    const bool tocOk = CacsSkin::ReadToc(cache.Utoc.data(), cache.Utoc.size(), t, error);
    CHECK(tocOk, "ReadToc (own cache): " << error);
    std::vector<CacsSkin::SkinPackage> back;
    if (tocOk)
    {
        CHECK(CacsSkin::ExtractPackages(t, cache.Ucas.data(), cache.Ucas.size(), back, error), "ExtractPackages (own cache): " << error);
        CHECK(back.size() == cache.Packages, "own cache: " << back.size() << " packages back");
    }
    for (const CacsSkin::SkinPackage& p : back)
    {
        Bytes file;
        bool found = false;
        for (const fs::path& folder : folders)
        {
            if (fs::exists(folder / p.File)) { found = Load(folder / p.File, file); break; }
        }
        CHECK(found && file == p.Data, "own cache: " << p.Package << " comes back as its file");
    }
}

static CacsSkin::SkinPackage FakePackage(const std::string& name, uint8_t fill, size_t size, bool bulk)
{
    CacsSkin::SkinPackage p;
    p.Package = name;
    p.File = "Content/" + name.substr(6) + ".uasset";
    p.Data.assign(size, fill);
    p.Size = size;
    p.ExportCount = 2;
    p.BundleCount = 1;
    p.LoadOrder = 3;
    p.Imports = {0x1122334455667788ULL, 0x0102030405060708ULL};
    if (bulk)
    {
        CacsSkin::SkinBulk b;
        b.File = "Content/" + name.substr(6) + ".ubulk";
        b.Type = CacsSkin::BulkData;
        b.Data.assign(70000, static_cast<uint8_t>(fill + 1));
        p.Bulk.push_back(b);
    }
    return p;
}

static void TestPieces()
{
    // skin.json: written and read back
    CacsSkin::SkinInfo s;
    s.Name = "Remake \"Sephiroth\" \xC3\xA9 \xE3\x83\xAA \xF0\x9F\x98\x80";   // a quote, e-acute, katakana RI, an emoji
    s.Author = "Kade";
    s.Description = "line one\nline two\tand a back\\slash";
    s.Characters = {"PC0000_00_Cloud_Standard", "PC0000_08_Cloud_SoldierNoHelmet"};
    s.Model = "/Game/A/B.B";
    s.Skeleton = "/Game/A/B_Skeleton.B_Skeleton";
    s.Family = "/Game/C/D.D";
    s.Proportions = true;
    s.ProportionBones = {"R_Feather*"};
    s.Voice = "own";
    s.Weapon = "/Game/BluePrint/W.W_C";
    s.AnimBlueprint = "";
    s.Enabled = false;
    s.Preview = "preview.png";
    CacsSkin::SkinPackage big = FakePackage("/Game/A/B", 7, 10, true);
    big.Size = (4ULL << 60) | 10;   // flags above bit 60 kept exactly
    s.Packages = {big, FakePackage("/Game/A/B_Skeleton", 9, 5, false)};
    s.Built = "2026-10-21T23:12:19Z";
    s.BuiltWith = "Create a Character System editor 1.15.0";
    const std::string text = CacsSkin::WriteSkinJson(s);
    CacsSkin::SkinInfo r;
    std::string error;
    CHECK(CacsSkin::ReadSkinJson(text, r, error), "ReadSkinJson(WriteSkinJson): " << error);
    CHECK(r.Name == s.Name && r.Author == s.Author && r.Description == s.Description, "texts come back (" << r.Name << ")");
    CHECK(r.Characters == s.Characters && r.ProportionBones == s.ProportionBones, "lists come back");
    CHECK(r.Model == s.Model && r.Skeleton == s.Skeleton && r.Family == s.Family && r.Voice == s.Voice && r.Weapon == s.Weapon, "paths come back");
    CHECK(r.Proportions && !r.Enabled && r.Preview == s.Preview && r.Built == s.Built && r.BuiltWith == s.BuiltWith, "flags come back");
    CHECK(r.Packages.size() == 2 && r.Packages[0].Size == big.Size && r.Packages[0].Imports == big.Imports && r.Packages[0].Bulk.size() == 1 &&
              r.Packages[0].Bulk[0].File == big.Bulk[0].File && r.Packages[1].LoadOrder == 3,
          "packages come back");
    CHECK(text.find("\\u00e9") != std::string::npos && text.find("\\ud83d\\ude00") != std::string::npos, "non-ASCII written as \\u escapes");
    CHECK(CacsSkin::FilesOf(r).size() == 4, "FilesOf lists the packages, their bulk and the preview");
    // JSON odds and ends
    CacsSkin::Json j;
    CHECK(CacsSkin::ParseJson("\xEF\xBB\xBF{\"a\": [1, 2.5e3, -4], \"b\": \"x\\u00e9\\ud83d\\ude00\", \"c\": null, \"d\": {}}", j, error), "BOM and nesting: " << error);
    CHECK(j.Find("b") && j.Find("b")->Text == "x\xC3\xA9\xF0\x9F\x98\x80", "\\u escapes to UTF-8");
    CHECK(!CacsSkin::ParseJson("{\"a\": 1,}", j, error), "a trailing comma is refused");
    CHECK(!CacsSkin::ReadSkinJson("{\"name\": \"x\"}", r, error), "a skin.json without schema is refused");
    CHECK(!CacsSkin::ReadSkinJson("{\"schema\": \"CreateACharacterSkin/1\", \"packages\": [{\"package\": \"/Game/A\", \"file\": \"Content/../x.uasset\", \"size\": 1, "
                                  "\"export_count\": 1, \"export_bundle_count\": 1}]}",
                                  r, error),
          "a file outside the skin folder is refused");
    CHECK(CacsSkin::SafeRelativePath("Content/A/B.uasset") && !CacsSkin::SafeRelativePath("C:/x") && !CacsSkin::SafeRelativePath("a//b"), "SafeRelativePath");

    // the cache: folder order, a skin that is off, a package two skins have
    std::vector<CacsSkin::SkinFolder> skins(3);
    skins[0].Folder = "Zeta";
    skins[0].Info.Packages = {FakePackage("/Game/Z/Shared", 1, 100, false)};
    skins[1].Folder = "Alpha";
    skins[1].Info.Packages = {FakePackage("/Game/A/Model", 2, 70000, true), FakePackage("/Game/Z/Shared", 3, 50, false)};
    skins[2].Folder = "Mid";
    skins[2].Info.Enabled = false;
    skins[2].Info.Packages = {FakePackage("/Game/M/Model", 4, 10, false)};
    CacsSkin::CacheResult cache = CacsSkin::BuildCache(skins);
    CHECK(cache.Ok, "BuildCache (pieces): " << cache.Error);
    CHECK(cache.Packages == 2, "two packages: Alpha's two (Shared from Alpha, the first by folder name), Mid off, Zeta's Shared left out");
    bool dupReported = false, offReported = false;
    for (const std::string& line : cache.Report)
    {
        if (line.find("Zeta: /Game/Z/Shared is in another skin too") == 0) { dupReported = true; }
        if (line == "Mid: off") { offReported = true; }
    }
    CHECK(dupReported && offReported, "the report says which package was left out and which skin is off");
    CacsSkin::Toc t;
    CHECK(CacsSkin::ReadToc(cache.Utoc.data(), cache.Utoc.size(), t, error), "ReadToc (pieces): " << error);
    std::vector<CacsSkin::SkinPackage> back;
    CHECK(CacsSkin::ExtractPackages(t, cache.Ucas.data(), cache.Ucas.size(), back, error), "ExtractPackages (pieces): " << error);
    CHECK(back.size() == 2 && back[0].Package == "/Game/A/Model" && back[0].Bulk.size() == 1 && back[0].Bulk[0].Data.size() == 70000 &&
              back[0].Bulk[0].Data[0] == 3 && back[1].Package == "/Game/Z/Shared" && back[1].Data.size() == 50 && back[1].Data[0] == 3,
          "the cache reads back: Alpha's model with its bulk data, Alpha's Shared");
    CHECK(back.size() == 2 && back[0].Imports == skins[1].Info.Packages[0].Imports && back[0].LoadOrder == 3 && back[0].ExportCount == 2, "store entries read back");
    // a compressed block is refused
    if (!t.Blocks.empty())
    {
        CacsSkin::Toc compressed = t;
        compressed.Blocks[0].Method = 1;
        compressed.Methods = {"Oodle"};
        back.clear();
        CHECK(!CacsSkin::ExtractPackages(compressed, cache.Ucas.data(), cache.Ucas.size(), back, error) && error.find("compressed") != std::string::npos,
              "a compressed container is refused (" << error << ")");
    }
    // a damaged TOC is refused, not read out of bounds
    Bytes cut(cache.Utoc.begin(), cache.Utoc.begin() + 150);
    CHECK(!CacsSkin::ReadToc(cut.data(), cut.size(), t, error), "a TOC cut short is refused");
}

int main(int argc, char** argv)
{
    TestPieces();
    if (argc >= 4)
    {
        TestEngineContainer(argv[1], argv[2]);
        TestCache(fs::path(argv[2]).parent_path(), argv[3]);
    }
    else { std::cout << "(no container given: only the pieces were tested)\n"; }
    std::cout << (Failures ? "FAILED: " : "OK: ") << Checks - Failures << " of " << Checks << " checks passed\n";
    return Failures ? 1 : 0;
}
