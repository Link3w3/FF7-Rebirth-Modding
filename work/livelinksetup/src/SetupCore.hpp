// Rebirth FX Live Link Setup: the parts that don't need Windows (payload index,
// CRC-32, inflate, and the small text formats Setup reads: Steam's libraryfolders.vdf,
// Epic's .item manifests, .uproject / .modules JSON values and UE's EditorSettings.ini).
// Built into Setup.exe and into the Linux tests (tests/setup_tests.cpp).
#pragma once

#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

extern "C" {
#include "../third_party/puff/puff.h"
}

namespace SetupCore
{

// ---- CRC-32 (zlib's polynomial; the packer uses zlib.crc32) ----
inline uint32_t Crc32(const uint8_t* data, size_t size, uint32_t crc = 0)
{
    static uint32_t table[256];
    static bool ready = false;
    if (!ready)
    {
        for (uint32_t n = 0; n < 256; ++n)
        {
            uint32_t c = n;
            for (int k = 0; k < 8; ++k) { c = (c & 1) ? 0xEDB88320u ^ (c >> 1) : c >> 1; }
            table[n] = c;
        }
        ready = true;
    }
    crc = ~crc;
    for (size_t i = 0; i < size; ++i) { crc = table[(crc ^ data[i]) & 0xFF] ^ (crc >> 8); }
    return ~crc;
}

// ---- Payload ----
// Setup.exe = stub + file data + index (UTF-8 text) + Footer. The packer is tools/make_setup.py.
constexpr char FooterMagic[8] = {'R', 'F', 'L', 'L', 'P', 'A', 'Y', '1'};

#pragma pack(push, 1)
struct Footer
{
    char Magic[8];
    uint64_t PayloadOffset; // where the file data starts (the stub's size)
    uint64_t IndexOffset;   // absolute
    uint64_t IndexSize;
    uint32_t IndexCrc;
    uint32_t Version;       // 1
};
#pragma pack(pop)
static_assert(sizeof(Footer) == 40, "footer layout");

struct FileEntry
{
    std::string Component; // "game" (the UE4SS mod folder) or "plugin" (the editor plugin folder)
    std::string Flags;     // comma list: "keep" = never replace an existing file
    uint64_t Offset = 0;   // relative to PayloadOffset
    uint64_t Packed = 0;
    uint64_t Size = 0;
    uint32_t Crc = 0;
    bool Deflated = false;
    std::string Path;      // relative, '/' separated

    bool Has(const char* flag) const
    {
        const size_t n = std::strlen(flag);
        size_t at = 0;
        while (at <= Flags.size())
        {
            size_t end = Flags.find(',', at);
            if (end == std::string::npos) { end = Flags.size(); }
            if (end - at == n && Flags.compare(at, n, flag) == 0) { return true; }
            at = end + 1;
        }
        return false;
    }
};

struct Index
{
    std::vector<std::pair<std::string, std::string>> Values; // product, version, ...
    std::vector<FileEntry> Files;

    std::string Value(const char* key) const
    {
        for (const auto& [k, v] : Values)
        {
            if (k == key) { return v; }
        }
        return {};
    }
    size_t Count(const char* component) const
    {
        size_t n = 0;
        for (const auto& f : Files) { n += f.Component == component ? 1 : 0; }
        return n;
    }
};

inline std::vector<std::string> SplitTabs(const std::string& line)
{
    std::vector<std::string> parts;
    size_t at = 0;
    while (true)
    {
        const size_t tab = line.find('\t', at);
        parts.push_back(line.substr(at, tab == std::string::npos ? std::string::npos : tab - at));
        if (tab == std::string::npos) { break; }
        at = tab + 1;
    }
    return parts;
}

inline bool ParseUnsigned(const std::string& text, uint64_t& out, int base = 10)
{
    if (text.empty() || text.size() > 20) { return false; }
    uint64_t value = 0;
    for (char c : text)
    {
        int digit;
        if (c >= '0' && c <= '9') { digit = c - '0'; }
        else if (base == 16 && c >= 'a' && c <= 'f') { digit = c - 'a' + 10; }
        else if (base == 16 && c >= 'A' && c <= 'F') { digit = c - 'A' + 10; }
        else { return false; }
        if (value > (UINT64_MAX - static_cast<uint64_t>(digit)) / static_cast<uint64_t>(base)) { return false; }
        value = value * static_cast<uint64_t>(base) + static_cast<uint64_t>(digit);
    }
    out = value;
    return true;
}

// A payload path is relative, '/' separated, with no empty, "." or ".." parts and none of :*?"<>|\ .
inline bool SafeRelativePath(const std::string& path)
{
    if (path.empty() || path.size() > 200 || path.front() == '/' || path.back() == '/') { return false; }
    size_t at = 0;
    while (at <= path.size())
    {
        size_t end = path.find('/', at);
        if (end == std::string::npos) { end = path.size(); }
        const std::string part = path.substr(at, end - at);
        if (part.empty() || part == "." || part == ".." || part.back() == '.' || part.back() == ' ') { return false; }
        for (unsigned char c : part)
        {
            if (c < 32 || std::strchr(":*?\"<>|\\", c)) { return false; }
        }
        // Windows device names (con, aux.h, nul.txt, com1, lpt9.cpp, ...) open the device instead of a file.
        std::string stem = part.substr(0, part.find('.'));
        while (!stem.empty() && stem.back() == ' ') { stem.pop_back(); }
        for (char& c : stem) { c = (c >= 'A' && c <= 'Z') ? static_cast<char>(c - 'A' + 'a') : c; }
        if (stem == "con" || stem == "prn" || stem == "aux" || stem == "nul" || stem == "conin$" || stem == "conout$" ||
            (stem.size() == 4 && (stem.compare(0, 3, "com") == 0 || stem.compare(0, 3, "lpt") == 0) && stem[3] >= '0' && stem[3] <= '9'))
        {
            return false;
        }
        at = end + 1;
    }
    return true;
}

// Parses the index text. `payloadSize` bounds the file data; `why` says what is wrong.
inline bool ParseIndex(const std::string& text, uint64_t payloadSize, Index& out, std::string& why)
{
    out = Index{};
    size_t at = 0;
    int lineNumber = 0;
    bool header = false, end = false;
    while (at < text.size() && !end)
    {
        size_t eol = text.find('\n', at);
        if (eol == std::string::npos) { eol = text.size(); }
        std::string line = text.substr(at, eol - at);
        at = eol + 1;
        ++lineNumber;
        if (!line.empty() && line.back() == '\r') { line.pop_back(); }
        if (line.empty()) { continue; }
        if (!header)
        {
            if (line != "RFLL1")
            {
                why = "not a Rebirth FX Live Link payload";
                return false;
            }
            header = true;
            continue;
        }
        const auto parts = SplitTabs(line);
        if (parts[0] == "end")
        {
            end = true;
            continue;
        }
        if (parts[0] == "file")
        {
            if (parts.size() != 9)
            {
                why = "index line " + std::to_string(lineNumber) + " has " + std::to_string(parts.size()) + " fields";
                return false;
            }
            FileEntry f;
            uint64_t crc = 0;
            f.Component = parts[1];
            f.Flags = parts[2] == "-" ? std::string{} : parts[2];
            if (!ParseUnsigned(parts[3], f.Offset) || !ParseUnsigned(parts[4], f.Packed) || !ParseUnsigned(parts[5], f.Size) ||
                !ParseUnsigned(parts[6], crc, 16) || crc > 0xFFFFFFFFull || (parts[7] != "deflate" && parts[7] != "store"))
            {
                why = "index line " + std::to_string(lineNumber) + " is malformed";
                return false;
            }
            f.Crc = static_cast<uint32_t>(crc);
            f.Deflated = parts[7] == "deflate";
            f.Path = parts[8];
            if (f.Component != "game" && f.Component != "plugin")
            {
                why = "unknown component \"" + f.Component + "\"";
                return false;
            }
            if (!SafeRelativePath(f.Path))
            {
                why = "unsafe path \"" + f.Path + "\"";
                return false;
            }
            if (f.Offset > payloadSize || f.Packed > payloadSize - f.Offset || (!f.Deflated && f.Packed != f.Size) || f.Size > (1ull << 31))
            {
                why = f.Path + " lies outside the payload";
                return false;
            }
            for (const auto& other : out.Files)
            {
                if (other.Component == f.Component && other.Path == f.Path)
                {
                    why = f.Path + " is listed twice";
                    return false;
                }
            }
            out.Files.push_back(std::move(f));
            continue;
        }
        if (parts.size() != 2)
        {
            why = "index line " + std::to_string(lineNumber) + " is malformed";
            return false;
        }
        out.Values.emplace_back(parts[0], parts[1]);
    }
    if (!header || !end)
    {
        why = "the payload index is cut short";
        return false;
    }
    if (out.Files.empty())
    {
        why = "the payload has no files";
        return false;
    }
    return true;
}

// Unpacks one file from its packed bytes and checks its size and CRC.
inline bool Unpack(const FileEntry& f, const uint8_t* packed, size_t packedSize, std::vector<uint8_t>& out, std::string& why)
{
    out.assign(static_cast<size_t>(f.Size), 0);
    if (f.Deflated)
    {
        unsigned long destLength = static_cast<unsigned long>(f.Size);
        unsigned long sourceLength = static_cast<unsigned long>(packedSize);
        // puff reads `dest` only when non-null; a zero-size file still needs a valid pointer.
        static unsigned char empty[1];
        const int status = puff(out.empty() ? empty : out.data(), &destLength, packed, &sourceLength);
        if (status != 0 || destLength != f.Size)
        {
            why = "the packed data of " + f.Path + " is damaged (inflate " + std::to_string(status) + ")";
            return false;
        }
    }
    else
    {
        if (packedSize != f.Size)
        {
            why = "the stored data of " + f.Path + " has the wrong size";
            return false;
        }
        if (packedSize) { std::memcpy(out.data(), packed, packedSize); }
    }
    if (Crc32(out.data(), out.size()) != f.Crc)
    {
        why = "the data of " + f.Path + " fails its CRC check";
        return false;
    }
    return true;
}

// ---- Small text formats ----
inline char Lower(char c) { return (c >= 'A' && c <= 'Z') ? static_cast<char>(c - 'A' + 'a') : c; }

inline bool EqualsNoCase(const std::string& a, const char* b)
{
    const size_t n = std::strlen(b);
    if (a.size() != n) { return false; }
    for (size_t i = 0; i < n; ++i)
    {
        if (Lower(a[i]) != Lower(b[i])) { return false; }
    }
    return true;
}

// The quoted strings of a Valve KeyValues text (libraryfolders.vdf, appmanifest .acf), in order.
inline std::vector<std::string> VdfStrings(const std::string& text)
{
    std::vector<std::string> out;
    size_t at = 0;
    while (at < text.size())
    {
        if (text[at] == '/' && at + 1 < text.size() && text[at + 1] == '/')
        {
            const size_t eol = text.find('\n', at);
            at = eol == std::string::npos ? text.size() : eol + 1;
            continue;
        }
        if (text[at] != '"')
        {
            ++at;
            continue;
        }
        std::string value;
        ++at;
        while (at < text.size() && text[at] != '"')
        {
            if (text[at] == '\\' && at + 1 < text.size())
            {
                const char next = text[at + 1];
                value += next == 'n' ? '\n' : next == 't' ? '\t' : next;
                at += 2;
                continue;
            }
            value += text[at++];
        }
        ++at; // closing quote
        out.push_back(std::move(value));
    }
    return out;
}

// Library folders listed in steamapps/libraryfolders.vdf (both the "path" form and the old "1" "D:\\Lib" form).
inline std::vector<std::string> SteamLibraries(const std::string& vdf)
{
    std::vector<std::string> out;
    const auto strings = VdfStrings(vdf);
    for (size_t i = 0; i + 1 < strings.size(); ++i)
    {
        const std::string& key = strings[i];
        const std::string& value = strings[i + 1];
        bool numeric = !key.empty();
        for (char c : key) { numeric = numeric && c >= '0' && c <= '9'; }
        const bool looksLikePath = value.size() > 2 && value[1] == ':';
        if ((EqualsNoCase(key, "path") || (numeric && looksLikePath)) && looksLikePath)
        {
            bool seen = false;
            for (const auto& o : out) { seen = seen || o == value; }
            if (!seen) { out.push_back(value); }
            ++i;
        }
    }
    return out;
}

// The value of "key" in an appmanifest .acf ("installdir"), or empty.
inline std::string VdfValue(const std::string& vdf, const char* key)
{
    const auto strings = VdfStrings(vdf);
    for (size_t i = 0; i + 1 < strings.size(); ++i)
    {
        if (EqualsNoCase(strings[i], key)) { return strings[i + 1]; }
    }
    return {};
}

// Every string value of "key" in a JSON text (Epic .item "InstallLocation", .uproject "EngineAssociation",
// .modules "BuildId"). Not a full JSON parser: it finds "key" followed by ':' and a string.
inline std::vector<std::string> JsonStrings(const std::string& text, const char* key)
{
    std::vector<std::string> out;
    const std::string quoted = std::string("\"") + key + "\"";
    size_t at = 0;
    while ((at = text.find(quoted, at)) != std::string::npos)
    {
        size_t p = at + quoted.size();
        at = p;
        while (p < text.size() && (text[p] == ' ' || text[p] == '\t' || text[p] == '\r' || text[p] == '\n')) { ++p; }
        if (p >= text.size() || text[p] != ':') { continue; }
        ++p;
        while (p < text.size() && (text[p] == ' ' || text[p] == '\t' || text[p] == '\r' || text[p] == '\n')) { ++p; }
        if (p >= text.size() || text[p] != '"') { continue; }
        ++p;
        std::string value;
        bool closed = false;
        while (p < text.size())
        {
            const char c = text[p];
            if (c == '"')
            {
                closed = true;
                ++p;
                break;
            }
            if (c == '\\' && p + 1 < text.size())
            {
                const char next = text[p + 1];
                if (next == 'u' && p + 5 < text.size())
                {
                    uint64_t code = 0;
                    if (ParseUnsigned(text.substr(p + 2, 4), code, 16) && code < 0x80) { value += static_cast<char>(code); }
                    p += 6;
                    continue;
                }
                value += next == 'n' ? '\n' : next == 't' ? '\t' : next == 'r' ? '\r' : next == 'b' ? '\b' : next == 'f' ? '\f' : next;
                p += 2;
                continue;
            }
            value += c;
            ++p;
        }
        if (closed) { out.push_back(std::move(value)); }
        at = p;
    }
    return out;
}

inline std::string JsonString(const std::string& text, const char* key)
{
    auto all = JsonStrings(text, key);
    return all.empty() ? std::string{} : all.front();
}

// UE's EditorSettings.ini: RecentlyOpenedProjectFiles=<path> lines, most recent first as written.
inline std::vector<std::string> RecentProjects(const std::string& ini)
{
    std::vector<std::string> out;
    size_t at = 0;
    while (at < ini.size())
    {
        size_t eol = ini.find('\n', at);
        if (eol == std::string::npos) { eol = ini.size(); }
        std::string line = ini.substr(at, eol - at);
        at = eol + 1;
        if (!line.empty() && line.back() == '\r') { line.pop_back(); }
        static const char key[] = "RecentlyOpenedProjectFiles=";
        if (line.compare(0, sizeof(key) - 1, key) != 0) { continue; }
        std::string value = line.substr(sizeof(key) - 1);
        // Newer engines write a struct: (ProjectName="C:/x/End.uproject",LastOpenTime=...)
        const size_t name = value.find("ProjectName=\"");
        if (name != std::string::npos)
        {
            const size_t start = name + 13;
            const size_t close = value.find('"', start);
            value = close == std::string::npos ? std::string{} : value.substr(start, close - start);
        }
        if (value.size() > 9 && EqualsNoCase(value.substr(value.size() - 9), ".uproject")) { out.push_back(value); }
    }
    return out;
}

// The standalone wide-string literals of a DLL that look like a version ("3.4.1"): the mod's ModVersionText.
// The version of a RebirthLiveLink main.lua: its line  local VERSION = "1.5"  ("" when there is none).
inline std::string LuaVersion(const std::string& text)
{
    const std::string key = "local VERSION";
    for (size_t at = text.find(key); at != std::string::npos; at = text.find(key, at + 1))
    {
        if (at > 0 && text[at - 1] != '\n') { continue; }
        size_t q = text.find('"', at);
        const size_t eol = text.find('\n', at);
        if (q == std::string::npos || (eol != std::string::npos && q > eol)) { continue; }
        const size_t end = text.find('"', q + 1);
        if (end == std::string::npos || (eol != std::string::npos && end > eol) || end - q - 1 > 16) { continue; }
        const std::string v = text.substr(q + 1, end - q - 1);
        bool ok = !v.empty();
        for (char c : v) { ok = ok && ((c >= '0' && c <= '9') || c == '.'); }
        if (ok) { return v; }
    }
    return {};
}

// True when "a.b.c" (missing parts are 0) is at least major.minor.patch.
inline bool VersionAtLeast(const std::string& version, int major, int minor, int patch)
{
    int parts[3] = {0, 0, 0};
    int index = 0;
    bool any = false;
    for (char c : version)
    {
        if (c == '.') { if (++index > 2) { break; } continue; }
        if (c < '0' || c > '9') { return false; }
        parts[index] = parts[index] * 10 + (c - '0');
        any = true;
    }
    if (!any) { return false; }
    const int want[3] = {major, minor, patch};
    for (int i = 0; i < 3; ++i)
    {
        if (parts[i] != want[i]) { return parts[i] > want[i]; }
    }
    return true;
}

inline std::vector<std::string> DllVersions(const uint8_t* data, size_t size)
{
    std::vector<std::string> out;
    for (size_t at = 2; at + 12 <= size; at += 2)
    {
        if (data[at - 2] != 0 || data[at - 1] != 0 || data[at] < '0' || data[at] > '9' || data[at + 1] != 0) { continue; }
        std::string text;
        size_t p = at;
        int dots = 0;
        bool ok = true;
        while (p + 1 < size && data[p + 1] == 0 && data[p] != 0 && text.size() < 16)
        {
            const char c = static_cast<char>(data[p]);
            if (c == '.') { ++dots; }
            else if (c < '0' || c > '9') { ok = false; break; }
            text += c;
            p += 2;
        }
        if (!ok || dots != 2 || p + 1 >= size || data[p] != 0 || data[p + 1] != 0 || text.back() == '.' || text.find("..") != std::string::npos) { continue; }
        bool seen = false;
        for (const auto& o : out) { seen = seen || o == text; }
        if (!seen) { out.push_back(text); }
        at = p;
    }
    return out;
}

// Finds `needle` in a stream read in blocks: feed it the blocks in order.
class StreamSearch
{
public:
    explicit StreamSearch(std::string needle) : Needle(std::move(needle)) {}
    bool Feed(const uint8_t* data, size_t size)
    {
        if (Found || Needle.empty()) { return Found = true; }
        Window.append(reinterpret_cast<const char*>(data), size);
        if (Window.find(Needle) != std::string::npos) { return Found = true; }
        if (Window.size() > Needle.size()) { Window.erase(0, Window.size() - (Needle.size() - 1)); }
        return false;
    }
    bool Matched() const { return Found; }

private:
    std::string Needle;
    std::string Window;
    bool Found = false;
};

} // namespace SetupCore
