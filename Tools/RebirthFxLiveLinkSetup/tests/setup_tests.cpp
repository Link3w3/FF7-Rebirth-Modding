// Linux tests of SetupCore.hpp (the parts of Setup.exe that don't need Windows).
//   setup_tests selftest
//   setup_tests unpack <Setup.exe> <out dir>    (writes <out>/<component>/<path> and prints the index)
#include "../src/SetupCore.hpp"

#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>
#include <sys/stat.h>

using namespace SetupCore;

static int failures = 0;
#define CHECK(x)                                                                 \
    do                                                                           \
    {                                                                            \
        if (!(x))                                                                \
        {                                                                        \
            std::cerr << "FAILED " << __FILE__ << ":" << __LINE__ << ": " #x "\n"; \
            ++failures;                                                          \
        }                                                                        \
    } while (0)

static void SelfTest()
{
    const char* digits = "123456789";
    CHECK(Crc32(reinterpret_cast<const uint8_t*>(digits), 9) == 0xCBF43926u);
    CHECK(Crc32(nullptr, 0) == 0);

    CHECK(LuaVersion("-- x\nlocal MOD = \"RebirthLiveLink\"\nlocal VERSION = \"1.5\"\n") == "1.5");
    CHECK(LuaVersion("local VERSION = \"1.10\"") == "1.10");
    CHECK(LuaVersion("x = 1 local VERSION = \"9\"\n").empty());
    CHECK(LuaVersion("local VERSION = VERSIONS[1]\n").empty());
    CHECK(VersionAtLeast("3.7.9", 3, 7, 9));
    CHECK(VersionAtLeast("3.7.10", 3, 7, 9));
    CHECK(VersionAtLeast("3.8.0", 3, 7, 9));
    CHECK(VersionAtLeast("4", 3, 7, 9));
    CHECK(!VersionAtLeast("3.7.5", 3, 7, 9));
    CHECK(!VersionAtLeast("3.6.14", 3, 7, 9));
    CHECK(!VersionAtLeast("", 3, 7, 9));
    CHECK(!VersionAtLeast("3.x", 3, 7, 9));
    CHECK(SafeRelativePath("dlls/main.dll"));
    CHECK(SafeRelativePath("Source/RebirthSkelCompatEditor/Private/EndMoveMaker.cpp"));
    CHECK(!SafeRelativePath("../x"));
    CHECK(!SafeRelativePath("a/../x"));
    CHECK(!SafeRelativePath("/abs"));
    CHECK(!SafeRelativePath("C:/abs"));
    CHECK(!SafeRelativePath("a\\b"));
    CHECK(!SafeRelativePath("a//b"));
    CHECK(!SafeRelativePath("a/./b"));
    CHECK(!SafeRelativePath("a/b."));
    CHECK(!SafeRelativePath(""));
    CHECK(!SafeRelativePath("Source/aux.h"));
    CHECK(!SafeRelativePath("con"));
    CHECK(!SafeRelativePath("a/NUL.txt"));
    CHECK(!SafeRelativePath("lpt1.cpp"));
    CHECK(!SafeRelativePath("COM9"));
    CHECK(SafeRelativePath("console.cpp"));
    CHECK(SafeRelativePath("com10.txt"));
    CHECK(SafeRelativePath("auxiliary/aux_tools.h"));

    FileEntry f;
    f.Flags = "keep,other";
    CHECK(f.Has("keep"));
    CHECK(f.Has("other"));
    CHECK(!f.Has("kee"));
    f.Flags = "";
    CHECK(!f.Has("keep"));

    // libraryfolders.vdf, current format
    const std::string vdf = "\"libraryfolders\"\n{\n\t\"0\"\n\t{\n\t\t\"path\"\t\t\"C:\\\\Program Files (x86)\\\\Steam\"\n"
                            "\t\t\"label\"\t\t\"\"\n\t\t\"apps\"\n\t\t{\n\t\t\t\"2909400\"\t\t\"151000000000\"\n\t\t}\n\t}\n"
                            "\t\"1\"\n\t{\n\t\t\"path\"\t\t\"E:\\\\SteamLibrary\"\n\t}\n}\n";
    auto libs = SteamLibraries(vdf);
    CHECK(libs.size() == 2);
    CHECK(libs.size() == 2 && libs[0] == "C:\\Program Files (x86)\\Steam" && libs[1] == "E:\\SteamLibrary");
    // old format
    const std::string old = "\"LibraryFolders\"\n{\n\t\"TimeNextStatsReport\"\t\t\"1234\"\n\t\"ContentStatsID\"\t\t\"-5\"\n"
                            "\t\"1\"\t\t\"D:\\\\Games\\\\Steam\"\n}\n";
    libs = SteamLibraries(old);
    CHECK(libs.size() == 1 && libs[0] == "D:\\Games\\Steam");
    const std::string acf = "\"AppState\"\n{\n\t\"appid\"\t\t\"2909400\"\n\t\"installdir\"\t\t\"FINAL FANTASY VII REBIRTH\"\n}\n";
    CHECK(VdfValue(acf, "installdir") == "FINAL FANTASY VII REBIRTH");
    CHECK(VdfValue(acf, "InstallDir") == "FINAL FANTASY VII REBIRTH");

    // Epic manifest
    const std::string item = "{\n\t\"FormatVersion\": 0,\n\t\"DisplayName\": \"FINAL FANTASY VII REBIRTH\",\n"
                             "\t\"InstallLocation\": \"D:\\\\Epic Games\\\\FFVIIRebirth\",\n\t\"x\": \"a\\/b\\u0041\"\n}";
    CHECK(JsonString(item, "InstallLocation") == "D:\\Epic Games\\FFVIIRebirth");
    CHECK(JsonString(item, "x") == "a/bA");
    CHECK(JsonString(item, "Missing").empty());
    const std::string modules = "{\n  \"BuildId\": \"17c11882-043f-4330-9e21-2efa519533c5\",\n  \"Modules\": {}\n}";
    CHECK(JsonString(modules, "BuildId") == "17c11882-043f-4330-9e21-2efa519533c5");
    const std::string uproject = "{\n\t\"FileVersion\": 3,\n\t\"EngineAssociation\": \"{B27A4B37-4B47-29AB-F685-658A01DA370E}\",\n}";
    CHECK(JsonString(uproject, "EngineAssociation") == "{B27A4B37-4B47-29AB-F685-658A01DA370E}");
    CHECK(JsonString("{\"EngineAssociation\":\"\"}", "EngineAssociation").empty());
    CHECK(JsonStrings("{\"EngineAssociation\":\"\"}", "EngineAssociation").size() == 1);

    // EditorSettings.ini
    const std::string ini = "[/Script/UnrealEd.EditorSettings]\r\nRecentlyOpenedProjectFiles=C:/FF7R2UProj/End.uproject\r\n"
                            "RecentlyOpenedProjectFiles=D:/Other/Thing.uproject\r\nRecentlyOpenedProjectFiles=notaproject\r\n"
                            "RecentlyOpenedProjectFiles=(ProjectName=\"E:/P/End.uproject\",LastOpenTime=2026.10.14-10.00.00)\r\n";
    auto recent = RecentProjects(ini);
    CHECK(recent.size() == 3);
    CHECK(recent.size() == 3 && recent[0] == "C:/FF7R2UProj/End.uproject" && recent[2] == "E:/P/End.uproject");

    // a needle split across blocks
    StreamSearch search("c0a8d4c");
    const std::string a = "xxxxxxxxc0a8", b = "d4cyyyy";
    CHECK(!search.Feed(reinterpret_cast<const uint8_t*>(a.data()), a.size()));
    CHECK(search.Feed(reinterpret_cast<const uint8_t*>(b.data()), b.size()));
    StreamSearch none("c0a8d4c");
    CHECK(!none.Feed(reinterpret_cast<const uint8_t*>(a.data()), a.size()));
    CHECK(!none.Feed(reinterpret_cast<const uint8_t*>("d4"), 2));
    CHECK(!none.Matched());

    // version literals of a DLL
    {
        std::string dll = std::string("MZ\0\0", 4);
        auto wide = [&](const char* s) {
            dll += std::string("\0\0", 2);
            for (const char* c = s; *c; ++c) { dll += *c, dll += '\0'; }
            dll += std::string("\0\0", 2);
        };
        wide("3.4.1");
        wide("hello 1.2.3");
        wide("10.20.30");
        wide("1.2");
        wide("3.4.1");
        auto versions = DllVersions(reinterpret_cast<const uint8_t*>(dll.data()), dll.size());
        CHECK(versions.size() == 2);
        CHECK(versions.size() == 2 && versions[0] == "3.4.1" && versions[1] == "10.20.30");
    }

    // index parsing errors
    Index index;
    std::string why;
    CHECK(!ParseIndex("nope\n", 10, index, why));
    CHECK(!ParseIndex("RFLL1\nversion\t1\n", 10, index, why)); // no end
    CHECK(!ParseIndex("RFLL1\nfile\tgame\t-\t0\t5\t5\t00000000\tstore\t../x\nend\n", 10, index, why));
    CHECK(!ParseIndex("RFLL1\nfile\tgame\t-\t8\t5\t5\t00000000\tstore\tx\nend\n", 10, index, why)); // past the payload
    CHECK(!ParseIndex("RFLL1\nfile\tgame\t-\t0\t4\t5\t00000000\tstore\tx\nend\n", 10, index, why)); // stored size mismatch
    CHECK(!ParseIndex("RFLL1\nfile\tother\t-\t0\t5\t5\t00000000\tstore\tx\nend\n", 10, index, why));
    CHECK(!ParseIndex("RFLL1\nfile\tgame\t-\t0\t5\t5\t00000000\tstore\tx\nfile\tgame\t-\t0\t5\t5\t00000000\tstore\tx\nend\n", 10, index, why));
    CHECK(ParseIndex("RFLL1\nversion\t3.4.0\nfile\tgame\tkeep\t0\t5\t5\t0000000a\tstore\tx y/z.txt\nend\n", 10, index, why));
    CHECK(index.Value("version") == "3.4.0" && index.Files.size() == 1 && index.Files[0].Has("keep") && index.Files[0].Crc == 10 &&
          index.Files[0].Path == "x y/z.txt");

    // Unpack: stored + damaged data
    const std::string hello = "hello";
    FileEntry stored;
    stored.Path = "h";
    stored.Size = 5;
    stored.Packed = 5;
    stored.Crc = Crc32(reinterpret_cast<const uint8_t*>(hello.data()), 5);
    std::vector<uint8_t> out;
    CHECK(Unpack(stored, reinterpret_cast<const uint8_t*>(hello.data()), 5, out, why) && std::string(out.begin(), out.end()) == hello);
    stored.Crc ^= 1;
    CHECK(!Unpack(stored, reinterpret_cast<const uint8_t*>(hello.data()), 5, out, why));
    FileEntry deflated = stored;
    deflated.Deflated = true;
    const uint8_t garbage[] = {0xFF, 0xFF, 0xFF};
    CHECK(!Unpack(deflated, garbage, sizeof(garbage), out, why));
}

static bool ReadFile(const std::string& path, std::string& out)
{
    std::ifstream in(path, std::ios::binary);
    if (!in) { return false; }
    std::ostringstream s;
    s << in.rdbuf();
    out = s.str();
    return true;
}

static void MakeDirs(const std::string& path)
{
    for (size_t at = 1; at < path.size(); ++at)
    {
        if (path[at] == '/') { mkdir(path.substr(0, at).c_str(), 0755); }
    }
}

static int Unpack(const std::string& exe, const std::string& outDir)
{
    std::string data;
    if (!ReadFile(exe, data) || data.size() < sizeof(Footer))
    {
        std::cerr << "can't read " << exe << "\n";
        return 2;
    }
    Footer footer{};
    std::memcpy(&footer, data.data() + data.size() - sizeof(Footer), sizeof(Footer));
    if (std::memcmp(footer.Magic, FooterMagic, 8) != 0 || footer.Version != 1 || footer.IndexOffset + footer.IndexSize + sizeof(Footer) != data.size() ||
        footer.PayloadOffset > footer.IndexOffset)
    {
        std::cerr << "bad footer\n";
        return 3;
    }
    const std::string text = data.substr(footer.IndexOffset, footer.IndexSize);
    if (Crc32(reinterpret_cast<const uint8_t*>(text.data()), text.size()) != footer.IndexCrc)
    {
        std::cerr << "index CRC mismatch\n";
        return 4;
    }
    Index index;
    std::string why;
    if (!ParseIndex(text, footer.IndexOffset - footer.PayloadOffset, index, why))
    {
        std::cerr << "index: " << why << "\n";
        return 5;
    }
    for (const auto& [k, v] : index.Values) { std::cout << k << " = " << v << "\n"; }
    for (const auto& f : index.Files)
    {
        std::vector<uint8_t> bytes;
        const auto* packed = reinterpret_cast<const uint8_t*>(data.data() + footer.PayloadOffset + f.Offset);
        if (!SetupCore::Unpack(f, packed, static_cast<size_t>(f.Packed), bytes, why))
        {
            std::cerr << why << "\n";
            return 6;
        }
        const std::string path = outDir + "/" + f.Component + "/" + f.Path;
        MakeDirs(path);
        std::ofstream o(path, std::ios::binary);
        o.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
        std::cout << f.Component << " " << (f.Deflated ? "deflate" : "store") << " " << f.Size << " " << f.Path << (f.Has("keep") ? " (keep)" : "") << "\n";
    }
    return 0;
}

int main(int argc, char** argv)
{
    if (argc >= 2 && std::string(argv[1]) == "selftest")
    {
        SelfTest();
        if (failures)
        {
            std::cerr << failures << " check(s) failed\n";
            return 1;
        }
        std::cout << "all setup core tests passed\n";
        return 0;
    }
    if (argc == 4 && std::string(argv[1]) == "unpack") { return Unpack(argv[2], argv[3]); }
    std::cerr << "usage: setup_tests selftest | unpack <Setup.exe> <out dir>\n";
    return 2;
}
