// SkelCompatCore.hpp
// Portable logic for the RebirthSkelCompat UE4SS mod: JSON config parsing, object-path
// normalisation and a faithful copy of UE 4.26's USkeleton::IsCompatibleMesh test.
// No Unreal or Windows dependencies, so it is unit-tested off-target.
#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

namespace SkelCompat
{
// ---------------------------------------------------------------------------------------
// UTF-8 <-> wide strings (wchar_t is UTF-16 on Windows, UTF-32 elsewhere)
// ---------------------------------------------------------------------------------------
inline void AppendCodePoint(std::wstring& out, uint32_t cp)
{
    if constexpr (sizeof(wchar_t) == 2)
    {
        if (cp >= 0x10000)
        {
            cp -= 0x10000;
            out.push_back(static_cast<wchar_t>(0xD800 + (cp >> 10)));
            out.push_back(static_cast<wchar_t>(0xDC00 + (cp & 0x3FF)));
            return;
        }
    }
    out.push_back(static_cast<wchar_t>(cp));
}

inline std::wstring Widen(std::string_view s)
{
    std::wstring out;
    out.reserve(s.size());
    for (size_t i = 0; i < s.size();)
    {
        const unsigned char c = static_cast<unsigned char>(s[i]);
        uint32_t cp = 0xFFFD;
        size_t len = 1;
        if (c < 0x80) { cp = c; }
        else if ((c >> 5) == 0x6 && i + 1 < s.size()) { cp = ((c & 0x1F) << 6) | (s[i + 1] & 0x3F); len = 2; }
        else if ((c >> 4) == 0xE && i + 2 < s.size()) { cp = ((c & 0x0F) << 12) | ((s[i + 1] & 0x3F) << 6) | (s[i + 2] & 0x3F); len = 3; }
        else if ((c >> 3) == 0x1E && i + 3 < s.size())
        {
            cp = ((c & 0x07) << 18) | ((s[i + 1] & 0x3F) << 12) | ((s[i + 2] & 0x3F) << 6) | (s[i + 3] & 0x3F);
            len = 4;
        }
        AppendCodePoint(out, cp);
        i += len;
    }
    return out;
}

inline std::string Narrow(std::wstring_view w)
{
    std::string out;
    out.reserve(w.size());
    for (size_t i = 0; i < w.size(); ++i)
    {
        uint32_t cp = static_cast<uint32_t>(w[i]);
        if constexpr (sizeof(wchar_t) == 2)
        {
            if (cp >= 0xD800 && cp <= 0xDBFF && i + 1 < w.size())
            {
                const uint32_t lo = static_cast<uint32_t>(w[i + 1]);
                if (lo >= 0xDC00 && lo <= 0xDFFF) { cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00); ++i; }
            }
        }
        if (cp < 0x80) { out.push_back(static_cast<char>(cp)); }
        else if (cp < 0x800) { out.push_back(static_cast<char>(0xC0 | (cp >> 6))); out.push_back(static_cast<char>(0x80 | (cp & 0x3F))); }
        else if (cp < 0x10000)
        {
            out.push_back(static_cast<char>(0xE0 | (cp >> 12)));
            out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
            out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
        }
        else
        {
            out.push_back(static_cast<char>(0xF0 | (cp >> 18)));
            out.push_back(static_cast<char>(0x80 | ((cp >> 12) & 0x3F)));
            out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
            out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
        }
    }
    return out;
}

// FName comparisons in Unreal ignore ASCII case.
inline wchar_t FoldAscii(wchar_t c) { return (c >= L'A' && c <= L'Z') ? static_cast<wchar_t>(c - L'A' + L'a') : c; }

inline bool NameEquals(std::wstring_view a, std::wstring_view b)
{
    if (a.size() != b.size()) { return false; }
    for (size_t i = 0; i < a.size(); ++i)
    {
        if (FoldAscii(a[i]) != FoldAscii(b[i])) { return false; }
    }
    return true;
}

inline std::wstring FoldedKey(std::wstring_view s)
{
    std::wstring out(s);
    for (auto& c : out) { c = FoldAscii(c); }
    return out;
}

// ---------------------------------------------------------------------------------------
// Minimal JSON (RFC 8259 subset: everything except duplicate-key policy; depth-limited)
// ---------------------------------------------------------------------------------------
struct Json
{
    enum class Type { Null, Bool, Number, String, Array, Object };
    Type type = Type::Null;
    bool boolean = false;
    double number = 0.0;
    std::string string;
    std::vector<Json> array;
    std::vector<std::pair<std::string, Json>> object;

    const Json* Find(std::string_view key) const
    {
        if (type != Type::Object) { return nullptr; }
        for (const auto& [k, v] : object)
        {
            if (k == key) { return &v; }
        }
        return nullptr;
    }
};

class JsonParser
{
public:
    explicit JsonParser(std::string_view text) : Text(text) {}

    bool Parse(Json& out, std::string& error)
    {
        if (Text.size() >= 3 && static_cast<unsigned char>(Text[0]) == 0xEF &&
            static_cast<unsigned char>(Text[1]) == 0xBB && static_cast<unsigned char>(Text[2]) == 0xBF)
        {
            Pos = 3; // UTF-8 BOM
        }
        SkipSpace();
        if (!Value(out, 0)) { error = Error.empty() ? "invalid JSON" : Error; error += " at byte " + std::to_string(Pos); return false; }
        SkipSpace();
        if (Pos != Text.size()) { error = "unexpected trailing characters at byte " + std::to_string(Pos); return false; }
        return true;
    }

private:
    std::string_view Text;
    size_t Pos = 0;
    std::string Error;

    void SkipSpace()
    {
        while (Pos < Text.size() && (Text[Pos] == ' ' || Text[Pos] == '\t' || Text[Pos] == '\n' || Text[Pos] == '\r')) { ++Pos; }
    }

    bool Fail(const char* message) { if (Error.empty()) { Error = message; } return false; }

    bool Literal(std::string_view word)
    {
        if (Text.substr(Pos, word.size()) != word) { return Fail("unknown literal"); }
        Pos += word.size();
        return true;
    }

    static int Hex(char c)
    {
        if (c >= '0' && c <= '9') { return c - '0'; }
        if (c >= 'a' && c <= 'f') { return c - 'a' + 10; }
        if (c >= 'A' && c <= 'F') { return c - 'A' + 10; }
        return -1;
    }

    bool Hex4(uint32_t& out)
    {
        if (Pos + 4 > Text.size()) { return Fail("truncated \\u escape"); }
        out = 0;
        for (int i = 0; i < 4; ++i)
        {
            const int h = Hex(Text[Pos + i]);
            if (h < 0) { return Fail("bad \\u escape"); }
            out = (out << 4) | static_cast<uint32_t>(h);
        }
        Pos += 4;
        return true;
    }

    static void AppendUtf8(std::string& s, uint32_t cp)
    {
        std::wstring w;
        AppendCodePoint(w, cp);
        s += Narrow(w);
    }

    bool StringValue(std::string& out)
    {
        ++Pos; // opening quote
        while (Pos < Text.size())
        {
            const char c = Text[Pos++];
            if (c == '"') { return true; }
            if (static_cast<unsigned char>(c) < 0x20) { return Fail("control character in string"); }
            if (c != '\\') { out.push_back(c); continue; }
            if (Pos >= Text.size()) { break; }
            const char e = Text[Pos++];
            switch (e)
            {
            case '"': out.push_back('"'); break;
            case '\\': out.push_back('\\'); break;
            case '/': out.push_back('/'); break;
            case 'b': out.push_back('\b'); break;
            case 'f': out.push_back('\f'); break;
            case 'n': out.push_back('\n'); break;
            case 'r': out.push_back('\r'); break;
            case 't': out.push_back('\t'); break;
            case 'u':
            {
                uint32_t cp = 0;
                if (!Hex4(cp)) { return false; }
                if (cp >= 0xD800 && cp <= 0xDBFF)
                {
                    uint32_t lo = 0;
                    if (Text.substr(Pos, 2) != "\\u") { return Fail("unpaired surrogate"); }
                    Pos += 2;
                    if (!Hex4(lo) || lo < 0xDC00 || lo > 0xDFFF) { return Fail("bad surrogate pair"); }
                    cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
                }
                AppendUtf8(out, cp);
                break;
            }
            default: return Fail("bad escape");
            }
        }
        return Fail("unterminated string");
    }

    bool NumberValue(double& out)
    {
        const size_t start = Pos;
        if (Pos < Text.size() && Text[Pos] == '-') { ++Pos; }
        bool digits = false;
        while (Pos < Text.size() && Text[Pos] >= '0' && Text[Pos] <= '9') { ++Pos; digits = true; }
        if (Pos < Text.size() && Text[Pos] == '.')
        {
            ++Pos;
            while (Pos < Text.size() && Text[Pos] >= '0' && Text[Pos] <= '9') { ++Pos; digits = true; }
        }
        if (Pos < Text.size() && (Text[Pos] == 'e' || Text[Pos] == 'E'))
        {
            ++Pos;
            if (Pos < Text.size() && (Text[Pos] == '+' || Text[Pos] == '-')) { ++Pos; }
            while (Pos < Text.size() && Text[Pos] >= '0' && Text[Pos] <= '9') { ++Pos; }
        }
        if (!digits) { return Fail("bad number"); }
        const std::string copy(Text.substr(start, Pos - start));
        char* end = nullptr;
        out = std::strtod(copy.c_str(), &end);
        if (!end || *end != '\0' || !std::isfinite(out)) { return Fail("bad number"); }
        return true;
    }

    bool Value(Json& out, int depth)
    {
        if (depth > 64) { return Fail("nesting too deep"); }
        SkipSpace();
        if (Pos >= Text.size()) { return Fail("unexpected end of input"); }
        const char c = Text[Pos];
        if (c == '{')
        {
            out.type = Json::Type::Object;
            ++Pos;
            SkipSpace();
            if (Pos < Text.size() && Text[Pos] == '}') { ++Pos; return true; }
            while (true)
            {
                SkipSpace();
                if (Pos >= Text.size() || Text[Pos] != '"') { return Fail("expected object key"); }
                std::string key;
                if (!StringValue(key)) { return false; }
                SkipSpace();
                if (Pos >= Text.size() || Text[Pos] != ':') { return Fail("expected ':'"); }
                ++Pos;
                Json value;
                if (!Value(value, depth + 1)) { return false; }
                out.object.emplace_back(std::move(key), std::move(value));
                SkipSpace();
                if (Pos < Text.size() && Text[Pos] == ',') { ++Pos; continue; }
                if (Pos < Text.size() && Text[Pos] == '}') { ++Pos; return true; }
                return Fail("expected ',' or '}'");
            }
        }
        if (c == '[')
        {
            out.type = Json::Type::Array;
            ++Pos;
            SkipSpace();
            if (Pos < Text.size() && Text[Pos] == ']') { ++Pos; return true; }
            while (true)
            {
                Json value;
                if (!Value(value, depth + 1)) { return false; }
                out.array.push_back(std::move(value));
                SkipSpace();
                if (Pos < Text.size() && Text[Pos] == ',') { ++Pos; continue; }
                if (Pos < Text.size() && Text[Pos] == ']') { ++Pos; return true; }
                return Fail("expected ',' or ']'");
            }
        }
        if (c == '"') { out.type = Json::Type::String; return StringValue(out.string); }
        if (c == 't') { out.type = Json::Type::Bool; out.boolean = true; return Literal("true"); }
        if (c == 'f') { out.type = Json::Type::Bool; out.boolean = false; return Literal("false"); }
        if (c == 'n') { out.type = Json::Type::Null; return Literal("null"); }
        if (c == '-' || (c >= '0' && c <= '9')) { out.type = Json::Type::Number; return NumberValue(out.number); }
        return Fail("unexpected character");
    }
};

inline bool ParseJson(std::string_view text, Json& out, std::string& error)
{
    out = Json{};
    return JsonParser(text).Parse(out, error);
}

// ---------------------------------------------------------------------------------------
// Object paths
// ---------------------------------------------------------------------------------------
inline std::wstring Trim(std::wstring_view s)
{
    size_t b = 0, e = s.size();
    while (b < e && (s[b] == L' ' || s[b] == L'\t' || s[b] == L'\r' || s[b] == L'\n')) { ++b; }
    while (e > b && (s[e - 1] == L' ' || s[e - 1] == L'\t' || s[e - 1] == L'\r' || s[e - 1] == L'\n')) { --e; }
    return std::wstring(s.substr(b, e - b));
}

// Accepts "/Game/A/B", "/Game/A/B.B", "Skeleton'/Game/A/B.B'", "Skeleton /Game/A/B.B" and
// backslashes; returns "/Game/A/B.B" (empty if the input is not a mount-rooted path).
inline std::wstring NormalizeObjectPath(std::wstring_view input)
{
    std::wstring s = Trim(input);
    const size_t quote = s.find(L'\'');
    if (quote != std::wstring::npos && !s.empty() && s.back() == L'\'' && s.size() > quote + 1)
    {
        s = s.substr(quote + 1, s.size() - quote - 2); // Class'/Path' export text
    }
    const size_t space = s.find(L' ');
    if (space != std::wstring::npos && space + 1 < s.size() && s[space + 1] == L'/')
    {
        s = s.substr(space + 1); // "Class /Path" full-name form
    }
    std::replace(s.begin(), s.end(), L'\\', L'/');
    s = Trim(s);
    if (s.size() < 2 || s[0] != L'/') { return {}; }
    while (s.size() > 1 && s.back() == L'/') { s.pop_back(); }
    const size_t slash = s.find_last_of(L'/');
    std::wstring leaf = s.substr(slash + 1);
    if (leaf.empty()) { return {}; }
    if (leaf.find(L'.') == std::wstring::npos)
    {
        s += L'.';
        s += leaf;
    }
    return s;
}

inline bool PathEquals(std::wstring_view a, std::wstring_view b) { return NameEquals(a, b); }

// ---------------------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------------------
// How a pair makes the receiving skeleton play the other skeleton's animations.
//  Animations (KH3 mode, default): animations authored on an animation skeleton are rewritten at load onto the
//    receiving skeleton (bones matched by name). Characters keep their own skeleton, AnimBlueprint and physics.
//  Mesh: meshes on the receiving skeleton are rebound to the animation skeleton and run its AnimBlueprints.
//  Family: every listed skeleton plays the animations of every other one, both ways. Only parsed entries use it:
//    FinishConfig turns each family into one Animations pair (the hub adopts the animations of every other member)
//    and one Mesh pair per member (its meshes are rebound to the hub), so at run time only the first two exist.
enum class Method
{
    Animations,
    Mesh,
    Family
};

struct Pair
{
    std::wstring Receiving;               // skeleton whose meshes receive animations (family entry: its first skeleton)
    std::vector<std::wstring> Animation;  // skeletons the animations are authored on, in order of preference (family entry: the others)
    std::vector<std::wstring> Meshes;     // mesh method: only these meshes (empty = every mesh on Receiving)
    std::vector<std::wstring> AdoptPaths; // animations method: only assets under these paths (empty = all)
    std::vector<std::wstring> RequiresPaks; // only active while every one of these paks / mods is installed
    Method Use = Method::Animations;
    bool RepairLiveComponents = true;     // re-initialise components whose AnimBP was refused before the rebind
    bool FixHierarchy = true;             // rename mesh bones placed differently on the animation skeleton
    bool CarrySockets = true;             // a mesh rebound while it loads keeps the sockets of its own skeleton
    std::vector<std::wstring> KeepCompatible; // mesh: AnimBlueprints made for these skeletons must still accept the rebound
                                          // meshes (a family member's own skeleton; the skeleton an outfit was made for
                                          // before it followed that skeleton's animations elsewhere)
    std::wstring Hub;                     // family entry: the skeleton the family gathers on ("hub"; empty = its first skeleton)
    std::wstring FamilyHub;               // set by FinishConfig on the pairs it made for a family: that family's hub
    std::wstring Origin;                  // file the entry came from
};

// "SephirothOverCloud_P.pak", "~mods\Seph\SephirothOverCloud_P.utoc" -> "SephirothOverCloud_P". The name a pair's
// requires_paks entry and an installed pak (or mod folder) are compared by, case-insensitively. Empty when unusable.
inline std::wstring PakStem(std::wstring_view input)
{
    std::wstring s(input);
    for (auto& c : s) { if (c == L'\\') { c = L'/'; } }
    while (!s.empty() && (s.back() == L' ' || s.back() == L'\t' || s.back() == L'/')) { s.pop_back(); }
    const size_t slash = s.find_last_of(L'/');
    if (slash != std::wstring::npos) { s.erase(0, slash + 1); }
    size_t start = 0;
    while (start < s.size() && (s[start] == L' ' || s[start] == L'\t')) { ++start; }
    s.erase(0, start);
    const size_t dot = s.find_last_of(L'.');
    if (dot != std::wstring::npos)
    {
        const std::wstring extension = FoldedKey(std::wstring_view(s).substr(dot));
        if (extension == L".pak" || extension == L".utoc" || extension == L".ucas" || extension == L".sig") { s.erase(dot); }
    }
    return s;
}

// "/Game/Motion/Player/PC0000_Cloud/Neutral20.Neutral20", "\Game\...\Neutral20\" -> "/Game/Motion/Player/PC0000_Cloud/Neutral20".
// A prefix names a package or a folder; an object name after the last '.' is dropped. Empty when unusable.
inline std::wstring NormalizePathPrefix(std::wstring_view input)
{
    std::wstring s(input);
    for (auto& c : s) { if (c == L'\\') { c = L'/'; } }
    while (!s.empty() && (s.back() == L' ' || s.back() == L'\t' || s.back() == L'/')) { s.pop_back(); }
    size_t start = 0;
    while (start < s.size() && (s[start] == L' ' || s[start] == L'\t')) { ++start; }
    s.erase(0, start);
    if (s.size() < 2 || s[0] != L'/') { return {}; }
    const size_t slash = s.find_last_of(L'/');
    const size_t dot = s.find(L'.', slash);
    if (dot != std::wstring::npos) { s.erase(dot); }
    return s.size() < 2 ? std::wstring{} : s;
}

// True when an object path lies under one of the prefixes (the package itself, its objects, or anything in the
// folder of that name). An empty list accepts everything.
inline bool PathUnder(const std::vector<std::wstring>& prefixes, std::wstring_view path)
{
    if (prefixes.empty()) { return true; }
    for (const auto& prefix : prefixes)
    {
        if (prefix.empty() || path.size() < prefix.size() || !NameEquals(path.substr(0, prefix.size()), prefix)) { continue; }
        if (path.size() == prefix.size()) { return true; }
        const wchar_t next = path[prefix.size()];
        if (next == L'/' || next == L'.' || next == L':') { return true; }
    }
    return false;
}

struct Config
{
    std::vector<Pair> Pairs;
    std::vector<std::wstring> Messages;

    // First pair whose receiving skeleton matches (case-insensitive object path).
    const Pair* FindForSkeleton(std::wstring_view skeletonPath) const
    {
        for (const auto& p : Pairs)
        {
            if (PathEquals(p.Receiving, skeletonPath)) { return &p; }
        }
        return nullptr;
    }

    bool IsAnimationSkeleton(std::wstring_view path) const
    {
        for (const auto& p : Pairs)
        {
            for (const auto& a : p.Animation)
            {
                if (PathEquals(a, path)) { return true; }
            }
        }
        return false;
    }
};

inline bool MeshAllowed(const Pair& pair, std::wstring_view meshPath)
{
    if (pair.Meshes.empty()) { return true; }
    for (const auto& m : pair.Meshes)
    {
        if (PathEquals(m, meshPath)) { return true; }
    }
    return false;
}

namespace Detail
{
inline void Note(Config& cfg, std::wstring_view origin, const std::wstring& message)
{
    std::wstring line(origin);
    line += L": ";
    line += message;
    cfg.Messages.push_back(std::move(line));
}

inline bool Lists(const std::vector<std::wstring>& list, std::wstring_view path)
{
    return std::any_of(list.begin(), list.end(), [&](const std::wstring& p) { return PathEquals(p, path); });
}

inline void AddUnique(std::vector<std::wstring>& list, const std::wstring& path)
{
    if (!path.empty() && !Lists(list, path)) { list.push_back(path); }
}

inline bool StringList(const Json* value, std::vector<std::wstring>& out, std::wstring& bad)
{
    if (!value) { return true; }
    auto add = [&](const Json& item) -> bool {
        if (item.type != Json::Type::String) { bad = L"expected a string"; return false; }
        const std::wstring path = NormalizeObjectPath(Widen(item.string));
        if (path.empty()) { bad = L"not an object path: " + Widen(item.string); return false; }
        AddUnique(out, path);
        return true;
    };
    if (value->type == Json::Type::String) { return add(*value); }
    if (value->type != Json::Type::Array) { bad = L"expected a string or an array of strings"; return false; }
    for (const auto& item : value->array)
    {
        if (!add(item)) { return false; }
    }
    return true;
}

inline std::wstring Joined(const std::vector<std::wstring>& items, const wchar_t* separator = L", ")
{
    std::wstring out;
    for (const auto& item : items) { out += (out.empty() ? L"" : separator) + item; }
    return out;
}
} // namespace Detail

// Parses one runtime manifest and appends its pairs. Bad entries are skipped with a message;
// returns false only when the file itself is unusable.
inline bool AppendConfig(std::string_view text, std::wstring_view origin, Config& cfg)
{
    Json root;
    std::string error;
    if (!ParseJson(text, root, error))
    {
        Detail::Note(cfg, origin, L"invalid JSON (" + Widen(error) + L"), file skipped");
        return false;
    }
    if (root.type != Json::Type::Object)
    {
        Detail::Note(cfg, origin, L"top level must be an object, file skipped");
        return false;
    }
    const Json* schema = root.Find("schema");
    if (!schema || schema->type != Json::Type::String || schema->string.rfind("RebirthSkelCompat/1", 0) != 0)
    {
        Detail::Note(cfg, origin, L"missing \"schema\": \"RebirthSkelCompat/1\", file skipped");
        return false;
    }
    // "pairs" and, for readability, "families" (entries of the second list default to "method": "family").
    const Json* pairs = root.Find("pairs");
    const Json* families = root.Find("families");
    if ((!pairs || pairs->type != Json::Type::Array) && (!families || families->type != Json::Type::Array))
    {
        Detail::Note(cfg, origin, L"missing \"pairs\" array, file skipped");
        return false;
    }
    std::vector<std::pair<const Json*, std::wstring>> entries;
    if (pairs && pairs->type == Json::Type::Array)
    {
        for (size_t k = 0; k < pairs->array.size(); ++k) { entries.emplace_back(&pairs->array[k], L"pairs[" + std::to_wstring(k) + L"]"); }
    }
    if (families && families->type == Json::Type::Array)
    {
        for (size_t k = 0; k < families->array.size(); ++k) { entries.emplace_back(&families->array[k], L"families[" + std::to_wstring(k) + L"]"); }
    }
    for (const auto& [entryJson, where] : entries)
    {
        const Json& entry = *entryJson;
        const bool familyList = where.rfind(L"families", 0) == 0;
        if (entry.type != Json::Type::Object) { Detail::Note(cfg, origin, where + L" is not an object, skipped"); continue; }
        if (const Json* enabled = entry.Find("enabled"); enabled && enabled->type == Json::Type::Bool && !enabled->boolean)
        {
            continue;
        }
        Pair pair;
        pair.Origin = std::wstring(origin);
        if (familyList) { pair.Use = Method::Family; }
        if (const Json* method = entry.Find("method"))
        {
            const std::wstring name = method->type == Json::Type::String ? FoldedKey(Widen(method->string)) : std::wstring{};
            if (name == L"animations" || name == L"animation" || name == L"adopt") { pair.Use = Method::Animations; }
            else if (name == L"mesh" || name == L"meshes" || name == L"rebind") { pair.Use = Method::Mesh; }
            else if (name == L"family" || name == L"group" || name == L"share" || name == L"shared" || name == L"both" || name == L"both_ways" ||
                     name == L"bidirectional")
            {
                pair.Use = Method::Family;
            }
            else
            {
                Detail::Note(cfg, origin, where + L" method must be \"animations\", \"mesh\" or \"family\"; using \"" +
                                              std::wstring(pair.Use == Method::Family ? L"family" : L"animations") + L"\"");
            }
        }
        std::wstring bad;
        std::vector<std::wstring> receivers;
        if (!Detail::StringList(entry.Find("receiving_skeleton"), receivers, bad) || !Detail::StringList(entry.Find("receiving_skeletons"), receivers, bad))
        {
            Detail::Note(cfg, origin, where + L" receiving skeleton: " + bad + L", skipped");
            continue;
        }
        std::vector<std::wstring> animation;
        if (!Detail::StringList(entry.Find("animation_skeletons"), animation, bad) || !Detail::StringList(entry.Find("animation_skeleton"), animation, bad) ||
            !Detail::StringList(entry.Find("skeletons"), animation, bad))
        {
            Detail::Note(cfg, origin, where + L" animation skeleton list: " + bad + L", skipped");
            continue;
        }
        if (const Json* hub = entry.Find("hub"))
        {
            pair.Hub = hub->type == Json::Type::String ? NormalizeObjectPath(Widen(hub->string)) : std::wstring{};
            if (pair.Hub.empty())
            {
                Detail::Note(cfg, origin, where + L" hub is not an object path, skipped");
                continue;
            }
            // Naming a hub asks for a family: the listed skeletons gather on it.
            if (pair.Use != Method::Family) { pair.Use = Method::Family; }
        }
        if (!Detail::StringList(entry.Find("receiving_meshes"), pair.Meshes, bad))
        {
            Detail::Note(cfg, origin, where + L" receiving_meshes: " + bad + L", skipped");
            continue;
        }
        if (const Json* repair = entry.Find("repair_live_components"); repair && repair->type == Json::Type::Bool)
        {
            pair.RepairLiveComponents = repair->boolean;
        }
        if (const Json* fix = entry.Find("fix_hierarchy"); fix && fix->type == Json::Type::Bool)
        {
            pair.FixHierarchy = fix->boolean;
        }
        if (const Json* sockets = entry.Find("carry_sockets"); sockets && sockets->type == Json::Type::Bool)
        {
            pair.CarrySockets = sockets->boolean;
        }
        if (const Json* adopt = entry.Find("adopt_paths"))
        {
            std::vector<const Json*> items;
            if (adopt->type == Json::Type::String) { items.push_back(adopt); }
            else if (adopt->type == Json::Type::Array) { for (const auto& item : adopt->array) { items.push_back(&item); } }
            bool usable = adopt->type == Json::Type::String || adopt->type == Json::Type::Array;
            for (const Json* item : items)
            {
                const std::wstring prefix = item->type == Json::Type::String ? NormalizePathPrefix(Widen(item->string)) : std::wstring{};
                if (prefix.empty()) { usable = false; continue; }
                if (std::none_of(pair.AdoptPaths.begin(), pair.AdoptPaths.end(), [&](const std::wstring& p) { return PathEquals(p, prefix); }))
                {
                    pair.AdoptPaths.push_back(prefix);
                }
            }
            if (!usable) { Detail::Note(cfg, origin, where + L" adopt_paths: entries must be paths like /Game/Folder/Asset; bad entries ignored"); }
        }
        for (const char* key : {"requires_paks", "requires_pak"})
        {
            const Json* wanted = entry.Find(key);
            if (!wanted) { continue; }
            std::vector<const Json*> items;
            if (wanted->type == Json::Type::String) { items.push_back(wanted); }
            else if (wanted->type == Json::Type::Array) { for (const auto& item : wanted->array) { items.push_back(&item); } }
            bool usable = wanted->type == Json::Type::String || wanted->type == Json::Type::Array;
            for (const Json* item : items)
            {
                const std::wstring name = item->type == Json::Type::String ? PakStem(Widen(item->string)) : std::wstring{};
                if (name.empty()) { usable = false; continue; }
                if (std::none_of(pair.RequiresPaks.begin(), pair.RequiresPaks.end(), [&](const std::wstring& n) { return NameEquals(n, name); }))
                {
                    pair.RequiresPaks.push_back(name);
                }
            }
            if (!usable) { Detail::Note(cfg, origin, where + L" requires_paks: entries must be pak or mod names like \"SephirothOverCloud_P\"; bad entries ignored"); }
        }

        if (pair.Use == Method::Family)
        {
            // Every skeleton named anywhere in the entry is a member; the hub is "hub", else the first one listed.
            std::vector<std::wstring> members = receivers;
            for (const auto& a : animation) { Detail::AddUnique(members, a); }
            std::vector<std::wstring> all = members;
            Detail::AddUnique(all, pair.Hub);
            if (all.size() < 2)
            {
                Detail::Note(cfg, origin, where + L" family needs at least two skeletons, skipped");
                continue;
            }
            if (!pair.AdoptPaths.empty() || !pair.Meshes.empty())
            {
                Detail::Note(cfg, origin, where + L" adopt_paths and receiving_meshes are not used by a family (it shares every animation and rebinds every mesh)");
                pair.AdoptPaths.clear();
                pair.Meshes.clear();
            }
            pair.Receiving = members.empty() ? pair.Hub : members.front();
            pair.Animation.assign(members.begin() + (members.empty() ? 0 : 1), members.end());
            cfg.Pairs.push_back(std::move(pair)); // families are joined later (FinishConfig), never merged here
            continue;
        }

        if (receivers.empty())
        {
            Detail::Note(cfg, origin, where + L" has no \"receiving_skeleton\", skipped");
            continue;
        }
        // One pair per receiving skeleton ("receiving_skeletons" lists several that get the same animations).
        for (const auto& receiving : receivers)
        {
            Pair one = pair;
            one.Receiving = receiving;
            one.Animation.clear();
            for (const auto& a : animation)
            {
                if (!PathEquals(a, receiving)) { one.Animation.push_back(a); }
            }
            const std::wstring label = receivers.size() > 1 ? where + L" (" + receiving + L")" : where;
            if (one.Animation.empty())
            {
                Detail::Note(cfg, origin, label + L" lists no animation skeleton other than itself, skipped");
                continue;
            }
            bool merged = false;
            for (auto& existing : cfg.Pairs)
            {
                if (existing.Use == Method::Family || !PathEquals(existing.Receiving, one.Receiving)) { continue; }
                // Same receiving skeleton from several files: keep one entry, union the lists.
                for (const auto& a : one.Animation) { Detail::AddUnique(existing.Animation, a); }
                if (existing.Meshes.empty() || one.Meshes.empty()) { existing.Meshes.clear(); }
                else
                {
                    for (const auto& m : one.Meshes) { Detail::AddUnique(existing.Meshes, m); }
                }
                existing.RepairLiveComponents = existing.RepairLiveComponents && one.RepairLiveComponents;
                existing.FixHierarchy = existing.FixHierarchy && one.FixHierarchy;
                existing.CarrySockets = existing.CarrySockets && one.CarrySockets;
                if (existing.Use != one.Use)
                {
                    Detail::Note(cfg, origin, label + L" asks for a different method than an earlier entry for the same skeleton; the earlier one is kept");
                }
                // Adopt paths: union; an entry without a list (= everything) widens the merged entry to everything.
                if (existing.AdoptPaths.empty() || one.AdoptPaths.empty()) { existing.AdoptPaths.clear(); }
                else
                {
                    for (const auto& p : one.AdoptPaths) { Detail::AddUnique(existing.AdoptPaths, p); }
                }
                // Required paks: union (the merged pair is on only while all of them are installed).
                for (const auto& name : one.RequiresPaks)
                {
                    if (std::none_of(existing.RequiresPaks.begin(), existing.RequiresPaks.end(), [&](const std::wstring& n) { return NameEquals(n, name); }))
                    {
                        existing.RequiresPaks.push_back(name);
                    }
                }
                Detail::Note(cfg, origin, label + L" merged with an earlier entry for the same receiving skeleton");
                merged = true;
                break;
            }
            if (!merged) { cfg.Pairs.push_back(std::move(one)); }
        }
    }
    return true; // rules between pairs are applied once every file is read (FinishConfig)
}

// Removes pairs whose requires_paks are not all installed. `isInstalled(name)` answers for one pak/mod name.
// Returns one message per removed pair.
template <class IsInstalled>
inline std::vector<std::wstring> DropPairsMissingPaks(Config& cfg, IsInstalled&& isInstalled)
{
    std::vector<std::wstring> notes;
    for (auto it = cfg.Pairs.begin(); it != cfg.Pairs.end();)
    {
        std::wstring missing;
        for (const auto& name : it->RequiresPaks)
        {
            if (!isInstalled(name)) { missing += (missing.empty() ? L"" : L", ") + name; }
        }
        if (missing.empty())
        {
            ++it;
            continue;
        }
        const std::wstring what = it->Use == Method::Family ? L"family entry with " + (it->Hub.empty() ? it->Receiving : it->Hub)
                                                            : L"pair for " + it->Receiving;
        notes.push_back(what + L" is off: it requires " + missing + L", which is not installed");
        it = cfg.Pairs.erase(it);
    }
    return notes;
}

// Where a mesh bound for `animationSkeleton` should go. When exactly one "animations" pair lists that skeleton and
// takes all of its animations (no adopt_paths), that skeleton's own AnimBlueprints cannot play them any more, so
// the mesh follows them to the pair's receiving skeleton: a Cloud outfit is worn by Sephiroth while Sephiroth plays
// Cloud's animations, and a family member's outfit goes to the family's hub. Otherwise the skeleton itself.
// `taker` (optional) receives the pair that has the animations.
inline std::wstring FollowAdoption(const Config& cfg, const std::wstring& animationSkeleton, const Pair** taker = nullptr)
{
    const Pair* only = nullptr;
    int listing = 0;
    for (const auto& p : cfg.Pairs)
    {
        if (p.Use == Method::Animations && Detail::Lists(p.Animation, animationSkeleton))
        {
            ++listing;
            only = &p;
        }
    }
    if (taker) { *taker = nullptr; }
    if (listing != 1 || !only->AdoptPaths.empty()) { return animationSkeleton; }
    if (taker) { *taker = only; }
    return only->Receiving;
}

namespace Detail
{
// Mesh chains are ambiguous: a mesh rebound onto a skeleton whose own meshes are rebound again. Such receivers are
// dropped. ("animations" chains never get here: FinishConfig turns them into families.)
inline void DropChains(Config& cfg)
{
    for (auto it = cfg.Pairs.begin(); it != cfg.Pairs.end();)
    {
        const Pair* chain = nullptr;
        for (const auto& other : cfg.Pairs)
        {
            if (&other == &*it || other.Use != it->Use) { continue; }
            if (Lists(other.Animation, it->Receiving))
            {
                chain = &other;
                break;
            }
        }
        if (!chain)
        {
            ++it;
            continue;
        }
        if (!chain->FamilyHub.empty() && PathEquals(chain->FamilyHub, it->Receiving))
        {
            Note(cfg, it->Origin, L"meshes on " + it->Receiving + L" stay on it: it is the hub of a family (" + chain->Origin +
                                      L"), whose members play their animations on it; entry ignored");
        }
        else
        {
            Note(cfg, it->Origin, L"receiving skeleton " + it->Receiving + L" is also an animation skeleton of another \"" +
                                      (it->Use == Method::Mesh ? L"mesh" : L"animations") +
                                      L"\" pair; entry ignored (list every animation skeleton on the final skeleton instead)");
        }
        it = cfg.Pairs.erase(it);
    }
}

// Union-find over skeleton paths (case-insensitive), nodes in order of first appearance.
struct SkeletonGraph
{
    std::vector<std::wstring> Paths;
    std::unordered_map<std::wstring, size_t> Index;
    std::vector<size_t> Parent;

    size_t Node(const std::wstring& path)
    {
        const std::wstring key = FoldedKey(path);
        const auto it = Index.find(key);
        if (it != Index.end()) { return it->second; }
        Index.emplace(key, Paths.size());
        Paths.push_back(path);
        Parent.push_back(Parent.size());
        return Paths.size() - 1;
    }

    bool Has(const std::wstring& path) const { return Index.count(FoldedKey(path)) > 0; }

    size_t Root(size_t n)
    {
        while (Parent[n] != n)
        {
            Parent[n] = Parent[Parent[n]];
            n = Parent[n];
        }
        return n;
    }

    void Unite(size_t a, size_t b)
    {
        a = Root(a);
        b = Root(b);
        if (a != b) { Parent[(std::max)(a, b)] = (std::min)(a, b); } // parenthesised: safe from Windows min/max macros
    }
};

inline bool PrefixesOverlap(const std::vector<std::wstring>& a, const std::vector<std::wstring>& b)
{
    for (const auto& x : a)
    {
        for (const auto& y : b)
        {
            if (PathUnder({x}, y) || PathUnder({y}, x)) { return true; }
        }
    }
    return false;
}

// Families. An animation asset can only belong to one skeleton, so skeletons that must share animations gather on
// one "hub" skeleton: the hub adopts the animations of every other member, and the meshes of every other member are
// rebound to the hub. Then every member's character plays every member's animations (bones the hub lacks keep their
// own pose), with its own AnimBlueprint. A family is made from:
//  * "family" entries (or entries that name a "hub");
//  * "animations" pairs that could not all work by moving animations: a skeleton that both receives and hands on
//    animations (reverse pairs, chains), or two pairs that want the same animations of one skeleton (the earlier one
//    without adopt_paths, or both with overlapping adopt_paths);
//  * every "animations" pair connected to those through a shared skeleton.
// Other "animations" pairs keep working by moving animations (KH3 mode), as before.
// Hub: the one a family entry (or "hub") names; else the skeleton whose animations the most pairs want, then one that
// receives none, then the receiving skeleton of the first pair. "mesh" pairs for a member join its family.
inline void BuildFamilies(Config& cfg)
{
    const size_t count = cfg.Pairs.size();
    SkeletonGraph graph;
    std::vector<char> involved(count, 0), conflict(count, 0);
    for (size_t i = 0; i < count; ++i)
    {
        const Pair& p = cfg.Pairs[i];
        if (p.Use == Method::Mesh) { continue; }
        involved[i] = 1;
        conflict[i] = p.Use == Method::Family ? 1 : 0;
        const size_t r = graph.Node(p.Receiving);
        for (const auto& a : p.Animation) { graph.Unite(r, graph.Node(a)); }
        if (!p.Hub.empty()) { graph.Unite(r, graph.Node(p.Hub)); }
    }
    for (size_t i = 0; i < count; ++i)
    {
        if (!involved[i] || cfg.Pairs[i].Use != Method::Animations) { continue; }
        for (size_t j = 0; j < count; ++j)
        {
            if (j == i || !involved[j] || cfg.Pairs[j].Use != Method::Animations) { continue; }
            const Pair& p = cfg.Pairs[i];
            const Pair& q = cfg.Pairs[j];
            if (Lists(p.Animation, q.Receiving))
            {
                conflict[i] = conflict[j] = 1; // q hands animations on to p while it receives some itself
                continue;
            }
            if (j < i) { continue; } // p earlier, q later
            for (const auto& a : p.Animation)
            {
                if (!Lists(q.Animation, a)) { continue; }
                if (p.AdoptPaths.empty() || (!q.AdoptPaths.empty() && PrefixesOverlap(p.AdoptPaths, q.AdoptPaths)))
                {
                    conflict[i] = conflict[j] = 1; // both want the same animations
                }
            }
        }
    }
    std::vector<char> familyRoot(graph.Paths.size(), 0);
    bool any = false;
    for (size_t i = 0; i < count; ++i)
    {
        if (involved[i] && conflict[i])
        {
            familyRoot[graph.Root(graph.Node(cfg.Pairs[i].Receiving))] = 1;
            any = true;
        }
    }
    if (!any) { return; }

    struct Family
    {
        size_t Root = 0;
        std::wstring Hub;
        std::wstring HubWhy;
        std::vector<std::wstring> Members;
        std::vector<size_t> Entries;          // "animations" and "family" entries, in config order
        std::vector<size_t> MeshEntries;      // "mesh" pairs of members
        std::vector<std::wstring> Origins;
        std::vector<std::wstring> RequiresPaks;
        bool FixHierarchy = true;
        bool RepairLiveComponents = true;
        bool CarrySockets = true;
    };
    std::vector<Family> families;
    const auto familyOf = [&](size_t root) -> Family& {
        for (auto& f : families)
        {
            if (f.Root == root) { return f; }
        }
        families.emplace_back();
        families.back().Root = root;
        return families.back();
    };
    std::vector<char> consumed(count, 0);
    for (size_t i = 0; i < count; ++i)
    {
        if (!involved[i]) { continue; }
        const size_t root = graph.Root(graph.Node(cfg.Pairs[i].Receiving));
        if (!familyRoot[root]) { continue; }
        familyOf(root).Entries.push_back(i);
        consumed[i] = 1;
    }

    for (Family& f : families)
    {
        // The hub a family entry (or "hub") names; the first one wins.
        for (size_t i : f.Entries)
        {
            const Pair& p = cfg.Pairs[i];
            const std::wstring named = !p.Hub.empty() ? p.Hub : (p.Use == Method::Family ? p.Receiving : std::wstring{});
            if (named.empty()) { continue; }
            if (f.Hub.empty())
            {
                f.Hub = named;
                f.HubWhy = L"named in " + p.Origin;
            }
            else if (!PathEquals(f.Hub, named))
            {
                Note(cfg, p.Origin, L"asks for hub " + named + L", but this family already gathers on " + f.Hub + L" (" + f.HubWhy +
                                        L"); " + named + L" is a member");
            }
        }
        if (f.Hub.empty())
        {
            std::vector<std::wstring> skeletons;
            std::vector<int> gives, receives;
            const auto at = [&](const std::wstring& path) -> size_t {
                for (size_t k = 0; k < skeletons.size(); ++k)
                {
                    if (PathEquals(skeletons[k], path)) { return k; }
                }
                skeletons.push_back(path);
                gives.push_back(0);
                receives.push_back(0);
                return skeletons.size() - 1;
            };
            for (size_t i : f.Entries)
            {
                const Pair& p = cfg.Pairs[i];
                ++receives[at(p.Receiving)];
                for (const auto& a : p.Animation) { ++gives[at(a)]; }
            }
            const int most = *std::max_element(gives.begin(), gives.end());
            std::vector<size_t> best;
            for (size_t k = 0; k < skeletons.size(); ++k)
            {
                if (gives[k] == most) { best.push_back(k); }
            }
            f.HubWhy = L"its animations are wanted by the most pairs";
            if (best.size() > 1 && std::any_of(best.begin(), best.end(), [&](size_t k) { return receives[k] == 0; }))
            {
                best.erase(std::remove_if(best.begin(), best.end(), [&](size_t k) { return receives[k] != 0; }), best.end());
                f.HubWhy += L" and it receives none";
            }
            size_t chosen = best.front();
            if (best.size() > 1)
            {
                const std::wstring& first = cfg.Pairs[f.Entries.front()].Receiving;
                for (size_t k : best)
                {
                    if (PathEquals(skeletons[k], first))
                    {
                        chosen = k;
                        f.HubWhy += L"; receiving skeleton of the first pair";
                    }
                }
            }
            f.Hub = skeletons[chosen];
        }
        for (size_t i : f.Entries)
        {
            const Pair& p = cfg.Pairs[i];
            if (!PathEquals(p.Receiving, f.Hub)) { AddUnique(f.Members, p.Receiving); }
            for (const auto& a : p.Animation)
            {
                if (!PathEquals(a, f.Hub)) { AddUnique(f.Members, a); }
            }
            if (!p.Hub.empty() && !PathEquals(p.Hub, f.Hub)) { AddUnique(f.Members, p.Hub); }
            AddUnique(f.Origins, p.Origin);
            for (const auto& name : p.RequiresPaks)
            {
                if (std::none_of(f.RequiresPaks.begin(), f.RequiresPaks.end(), [&](const std::wstring& n) { return NameEquals(n, name); }))
                {
                    f.RequiresPaks.push_back(name);
                }
            }
            if (p.Use == Method::Family)
            {
                f.FixHierarchy = f.FixHierarchy && p.FixHierarchy;
                f.RepairLiveComponents = f.RepairLiveComponents && p.RepairLiveComponents;
                f.CarrySockets = f.CarrySockets && p.CarrySockets;
            }
            else if (!p.AdoptPaths.empty())
            {
                Note(cfg, p.Origin, L"adopt_paths of the pair for " + p.Receiving + L" are not used: it is part of the family of " + f.Hub +
                                        L", which shares every animation of its members");
            }
        }
    }

    // "mesh" pairs whose meshes belong to a member: they go to the hub with the rest of the family.
    for (size_t i = 0; i < count; ++i)
    {
        Pair& m = cfg.Pairs[i];
        if (m.Use != Method::Mesh || !graph.Has(m.Receiving)) { continue; }
        const size_t root = graph.Root(graph.Node(m.Receiving));
        if (!familyRoot[root]) { continue; }
        Family& f = familyOf(root);
        if (PathEquals(m.Receiving, f.Hub)) { continue; } // would pull the hub's own meshes away; DropChains settles it
        f.MeshEntries.push_back(i);
        consumed[i] = 1;
        f.FixHierarchy = f.FixHierarchy && m.FixHierarchy;
        f.RepairLiveComponents = f.RepairLiveComponents && m.RepairLiveComponents;
        f.CarrySockets = f.CarrySockets && m.CarrySockets;
        AddUnique(f.Origins, m.Origin);
        std::vector<std::wstring> elsewhere;
        for (const auto& a : m.Animation)
        {
            if (!PathEquals(a, f.Hub) && !Lists(f.Members, a)) { elsewhere.push_back(a); }
        }
        Note(cfg, m.Origin, L"meshes on " + m.Receiving + L" belong to the family of " + f.Hub + L", so they are rebound to " + f.Hub +
                                (elsewhere.empty() ? std::wstring{} : L" (not to " + Joined(elsewhere) + L")"));
    }

    std::vector<Pair> result;
    result.reserve(count + families.size() * 4);
    for (size_t i = 0; i < count; ++i)
    {
        if (!consumed[i])
        {
            result.push_back(std::move(cfg.Pairs[i]));
            continue;
        }
        for (Family& f : families)
        {
            if (f.Entries.empty() || f.Entries.front() != i) { continue; }
            const std::wstring origin = Joined(f.Origins);
            Pair hub;
            hub.Use = Method::Animations;
            hub.Receiving = f.Hub;
            hub.Animation = f.Members;
            hub.RequiresPaks = f.RequiresPaks;
            hub.FamilyHub = f.Hub;
            hub.Origin = origin;
            result.push_back(std::move(hub));
            for (const auto& member : f.Members)
            {
                Pair mesh;
                mesh.Use = Method::Mesh;
                mesh.Receiving = member;
                mesh.Animation = {f.Hub};
                mesh.KeepCompatible = {member}; // the member's own AnimBlueprints still run on its meshes
                mesh.RequiresPaks = f.RequiresPaks;
                mesh.FixHierarchy = f.FixHierarchy;
                mesh.RepairLiveComponents = f.RepairLiveComponents;
                mesh.CarrySockets = f.CarrySockets;
                mesh.FamilyHub = f.Hub;
                mesh.Origin = origin;
                result.push_back(std::move(mesh));
            }
            Note(cfg, origin, L"family of " + f.Hub + L" (hub: " + f.HubWhy + L"): " + Joined(f.Members) +
                                  L" and " + f.Hub + L" play each other's animations. The animations of the others are adopted onto " + f.Hub +
                                  L" and their meshes are rebound to it");
        }
    }
    cfg.Pairs = std::move(result);
}
} // namespace Detail

// Settles the pairs once every file is read, in this order (each step only sees the pairs the steps before kept):
//  1. pairs whose requires_paks are not all installed switch off (`isInstalled(name)` answers for one name);
//  2. families are formed (Detail::BuildFamilies): "family" entries, and "animations" pairs that would otherwise
//     fight over the same animations or chain. Each becomes one "animations" pair onto the hub plus a "mesh" pair per
//     member. Other "animations" pairs keep moving animations onto their receiving skeleton (KH3 mode);
//  3. "mesh" pairs follow adopted animations (FollowAdoption), then mesh chains are dropped.
// Every change is explained in cfg.Messages.
template <class IsInstalled>
inline void FinishConfig(Config& cfg, IsInstalled&& isInstalled)
{
    if (std::any_of(cfg.Pairs.begin(), cfg.Pairs.end(), [](const Pair& p) { return !p.RequiresPaks.empty(); }))
    {
        for (auto& note : DropPairsMissingPaks(cfg, isInstalled)) { cfg.Messages.push_back(std::move(note)); }
    }

    Detail::BuildFamilies(cfg);

    for (size_t i = 0; i < cfg.Pairs.size();)
    {
        if (cfg.Pairs[i].Use != Method::Mesh || !cfg.Pairs[i].FamilyHub.empty())
        {
            ++i;
            continue;
        }
        const std::wstring receiving = cfg.Pairs[i].Receiving;
        const std::wstring origin = cfg.Pairs[i].Origin;
        std::vector<std::wstring> targets;
        std::vector<std::wstring> notes;
        std::vector<std::wstring> keep = cfg.Pairs[i].KeepCompatible;
        for (const auto& a : cfg.Pairs[i].Animation)
        {
            const Pair* taker = nullptr;
            const std::wstring target = FollowAdoption(cfg, a, &taker);
            if (taker)
            {
                notes.push_back(L"meshes on " + receiving + L" follow the animations of " + a + L" to " + target + L", which takes all of them (" +
                                (taker->FamilyHub.empty() ? taker->Origin : L"family of " + taker->FamilyHub) + L")");
                Detail::AddUnique(keep, a); // the outfit is still shown by a's characters, with a's AnimBlueprints
            }
            if (PathEquals(target, receiving))
            {
                notes.push_back(L"meshes on " + receiving + L" already use " + target + L", so " + a + L" is left out of their pair");
                continue;
            }
            Detail::AddUnique(targets, target);
        }
        for (const auto& note : notes) { Detail::Note(cfg, origin, note); }
        if (targets.empty())
        {
            Detail::Note(cfg, origin, L"pair for " + receiving + L" is off: it has no animation skeleton left");
            cfg.Pairs.erase(cfg.Pairs.begin() + static_cast<std::ptrdiff_t>(i));
            continue;
        }
        cfg.Pairs[i].Animation = std::move(targets);
        cfg.Pairs[i].KeepCompatible = std::move(keep);
        ++i;
    }
    Detail::DropChains(cfg); // a mesh pair may now point at the receiving skeleton of another mesh pair
}

// ---------------------------------------------------------------------------------------
// Hierarchy test: exact port of UE 4.26 USkeleton::IsCompatibleMesh / DoesParentChainMatch.
// The game only spawns an AnimBlueprint on a mesh when this passes against the AnimBP's
// skeleton, so the mod reports the first failing bone before the game silently T-poses.
// ---------------------------------------------------------------------------------------
struct BoneTable
{
    std::vector<std::wstring> Names;   // final bone list (raw bones first, then virtual bones)
    std::vector<int32_t> Parents;      // parent index per bone, -1 for the root
    int32_t RawCount = -1;             // raw (non-virtual) bones; -1 means all of Names

    int32_t Raw() const { return RawCount < 0 ? static_cast<int32_t>(Names.size()) : RawCount; }

    // Case-insensitive like FName; the first bone with the name wins. Indexed on first use;
    // change names only through Rename() once Find has been called.
    int32_t Find(std::wstring_view name) const
    {
        if (IndexedCount != Names.size())
        {
            Index.clear();
            Index.reserve(Names.size());
            for (size_t i = Names.size(); i-- > 0;) { Index[FoldedKey(Names[i])] = static_cast<int32_t>(i); }
            IndexedCount = Names.size();
        }
        const auto it = Index.find(FoldedKey(name));
        return it == Index.end() ? -1 : it->second;
    }

    void Rename(int32_t index, std::wstring name)
    {
        Names[static_cast<size_t>(index)] = std::move(name);
        IndexedCount = static_cast<size_t>(-1);
    }

    bool Valid() const
    {
        if (Names.empty() || Names.size() != Parents.size() || Raw() > static_cast<int32_t>(Names.size())) { return false; }
        if (Parents[0] != -1) { return false; }
        for (size_t i = 1; i < Parents.size(); ++i)
        {
            if (Parents[i] < 0 || Parents[i] >= static_cast<int32_t>(i)) { return false; }
        }
        return true;
    }

private:
    mutable std::unordered_map<std::wstring, int32_t> Index;
    mutable size_t IndexedCount = static_cast<size_t>(-1);
};

struct MeshCheck
{
    bool Compatible = false;
    int32_t Matched = 0;      // mesh bones that exist on the skeleton
    int32_t MeshOnly = 0;     // mesh bones the skeleton lacks (left at their reference pose)
    int32_t SkeletonOnly = 0; // skeleton bones the mesh lacks (their tracks are ignored)
    std::wstring Problem;     // first reason the engine would refuse the AnimBlueprint
};

namespace Detail
{
inline bool DoesParentChainMatch(int32_t startSkeletonIndex, const BoneTable& skel, const BoneTable& mesh)
{
    if (startSkeletonIndex == 0) { return NameEquals(skel.Names[0], mesh.Names[0]); }
    int32_t s = startSkeletonIndex;
    int32_t m = mesh.Find(skel.Names[s]);
    if (m < 0) { return false; }
    while (true)
    {
        const int32_t ps = skel.Parents[s];
        const int32_t pm = mesh.Parents[m];
        if (ps < 0 || pm < 0) { return ps == pm; }
        if (!NameEquals(skel.Names[ps], mesh.Names[pm])) { return false; }
        s = ps;
        m = pm;
    }
}

inline std::wstring Chain(const BoneTable& t, int32_t index)
{
    std::wstring out;
    int guard = 0;
    while (index >= 0 && guard++ < 6)
    {
        if (!out.empty()) { out += L" <- "; }
        out += t.Names[index];
        index = t.Parents[index];
    }
    if (index >= 0) { out += L" <- ..."; }
    return out;
}
} // namespace Detail

inline MeshCheck CheckMeshAgainstSkeleton(const BoneTable& mesh, const BoneTable& skel)
{
    MeshCheck r;
    if (!mesh.Valid() || !skel.Valid()) { r.Problem = L"bone table unreadable"; return r; }
    for (int32_t i = 0; i < skel.Raw(); ++i)
    {
        if (mesh.Find(skel.Names[i]) < 0) { ++r.SkeletonOnly; }
    }
    for (int32_t mi = 0; mi < mesh.Raw(); ++mi)
    {
        int32_t si = skel.Find(mesh.Names[mi]);
        if (si >= 0)
        {
            ++r.Matched;
            if (r.Problem.empty() && !Detail::DoesParentChainMatch(si, skel, mesh))
            {
                if (si == 0)
                {
                    r.Problem = L"root bone is '" + mesh.Names[0] + L"' on the mesh but '" + skel.Names[0] + L"' on the skeleton";
                }
                else
                {
                    const int32_t mm = mesh.Find(skel.Names[si]);
                    r.Problem = L"bone '" + mesh.Names[mi] + L"' has a different parent chain: mesh " +
                                Detail::Chain(mesh, mm < 0 ? mi : mm) + L" vs skeleton " + Detail::Chain(skel, si);
                }
            }
            continue;
        }
        ++r.MeshOnly;
        int32_t current = mi;
        while (si < 0 && current >= 0)
        {
            const int32_t parent = mesh.Parents[current];
            if (parent >= 0) { si = skel.Find(mesh.Names[parent]); }
            if (parent == 0) { break; }
            current = parent;
        }
        if (r.Problem.empty())
        {
            if (mi == 0)
            {
                r.Problem = L"root bone is '" + mesh.Names[0] + L"' on the mesh but '" + skel.Names[0] + L"' on the skeleton";
            }
            else if (si < 0)
            {
                r.Problem = L"mesh-only bone '" + mesh.Names[mi] + L"' has no ancestor that exists on the skeleton";
            }
            else if (!Detail::DoesParentChainMatch(si, skel, mesh))
            {
                r.Problem = L"mesh-only bone '" + mesh.Names[mi] + L"' hangs under '" + skel.Names[si] +
                            L"', whose parent chain differs: mesh " + Detail::Chain(mesh, mesh.Find(skel.Names[si])) +
                            L" vs skeleton " + Detail::Chain(skel, si);
            }
        }
    }
    r.Compatible = r.Problem.empty() && r.Matched > 0;
    if (r.Problem.empty() && r.Matched == 0) { r.Problem = L"no bone names in common"; }
    return r;
}

// ---------------------------------------------------------------------------------------
// Hierarchy fix. The engine refuses the AnimBlueprint when a bone the mesh shares with the
// animation skeleton hangs under a different parent chain (KH3-style rigs usually differ only in
// accessory chains: belts, hair, coat tails). Such a bone is taken out of the shared set by giving
// it a unique name on the mesh; it then keeps the mesh's own pose relative to its mesh parent, and
// the engine accepts the AnimBlueprint for everything else. Shared bones under a renamed bone are
// re-tested and follow when their chain no longer matches. Parents come before children in a
// reference skeleton, so one pass in index order decides every bone with its ancestors settled.
// ---------------------------------------------------------------------------------------
struct RenamePlan
{
    std::vector<int32_t> Bones; // raw mesh bone indices to rename, ascending
    bool Possible = true;       // false when the root bones differ (renaming cannot help) or a table is unreadable
};

constexpr uint32_t RenameDisplayBase = 900000; // renamed bones show as "<name>_9xxxxx" (FName number = this + index + 1)

inline RenamePlan PlanConflictRenames(const BoneTable& mesh, const BoneTable& skel)
{
    RenamePlan plan;
    if (!mesh.Valid() || !skel.Valid() || !NameEquals(mesh.Names[0], skel.Names[0]))
    {
        plan.Possible = false;
        return plan;
    }
    const int32_t count = mesh.Raw();
    // skeleton index of each mesh bone that stays shared and whose whole chain matches, else -1
    std::vector<int32_t> settled(static_cast<size_t>(count), -1);
    settled[0] = 0;
    for (int32_t i = 1; i < count; ++i)
    {
        const int32_t s = skel.Find(mesh.Names[static_cast<size_t>(i)]);
        if (s < 0) { continue; } // mesh-only already
        const int32_t skeletonParent = skel.Parents[static_cast<size_t>(s)];
        const int32_t meshParent = mesh.Parents[static_cast<size_t>(i)];
        // The engine walks both chains comparing parent names. With the mesh parent settled this is
        // exactly: the mesh parent is the very bone the skeleton names as parent.
        if (s != 0 && skeletonParent >= 0 && settled[static_cast<size_t>(meshParent)] == skeletonParent)
        {
            settled[static_cast<size_t>(i)] = s;
        }
        else
        {
            plan.Bones.push_back(i);
        }
    }
    return plan;
}

inline std::wstring RenamedBoneName(const std::wstring& name, int32_t index)
{
    return name + L"_" + std::to_wstring(RenameDisplayBase + static_cast<uint32_t>(index));
}

// ---------------------------------------------------------------------------------------
// Animation adoption (KH3 mode). An animation authored on skeleton `from` is rewritten onto skeleton `to`:
// each track moves to the `to` bone of the same name, but only where that bone's whole parent chain matches
// (a local transform is only meaningful relative to the same parent). Tracks of other bones are dropped, and
// `to` bones without a track keep their reference pose or physics. Bones come parents-first in a reference
// skeleton (virtual bones after the raw bones, parented to their source bone), so one pass settles each bone
// after its parent. Returns from-index -> to-index or -1; empty when the root bones differ.
// ---------------------------------------------------------------------------------------
inline std::vector<int32_t> BuildTrackRemap(const BoneTable& from, const BoneTable& to)
{
    std::vector<int32_t> map;
    if (!from.Valid() || !to.Valid() || !NameEquals(from.Names[0], to.Names[0])) { return map; }
    map.assign(from.Names.size(), -1);
    std::vector<int32_t> partner(to.Names.size(), -1); // from-index matched to each `to` bone, chain verified
    partner[0] = 0;
    map[0] = 0;
    for (size_t r = 1; r < to.Names.size(); ++r)
    {
        const int32_t a = from.Find(to.Names[r]);
        if (a <= 0 || map[static_cast<size_t>(a)] >= 0) { continue; } // missing, the root's name, or taken
        const int32_t toParent = to.Parents[r];
        const int32_t fromParent = from.Parents[static_cast<size_t>(a)];
        if (toParent >= 0 && fromParent >= 0 && partner[static_cast<size_t>(toParent)] == fromParent)
        {
            partner[r] = a;
            map[static_cast<size_t>(a)] = static_cast<int32_t>(r);
        }
    }
    return map;
}

// The mesh table as the engine sees it after the plan was applied.
inline BoneTable ApplyRenamePlan(const BoneTable& mesh, const RenamePlan& plan)
{
    BoneTable out;
    out.Names = mesh.Names;
    out.Parents = mesh.Parents;
    out.RawCount = mesh.RawCount;
    for (int32_t bone : plan.Bones) { out.Rename(bone, RenamedBoneName(mesh.Names[static_cast<size_t>(bone)], bone)); }
    return out;
}

// A family member's mesh is rebound to the hub but may also run its own character's AnimBlueprint, which the engine
// tests against the member's own skeleton. That skeleton has every bone of the mesh, so a bone left under a renamed
// one fails there (its parent chain no longer matches). Renaming whole subtrees passes both tests: the renamed bones
// are mesh-only for both skeletons. Raw bones only (virtual bones are never renamed).
inline RenamePlan CloseRenamePlan(const BoneTable& mesh, const RenamePlan& plan)
{
    RenamePlan closed = plan;
    if (!plan.Possible || plan.Bones.empty() || !mesh.Valid()) { return closed; }
    const int32_t count = mesh.Raw();
    std::vector<char> renamed(static_cast<size_t>(count), 0);
    for (int32_t bone : plan.Bones)
    {
        if (bone > 0 && bone < count) { renamed[static_cast<size_t>(bone)] = 1; }
    }
    closed.Bones.clear();
    for (int32_t i = 1; i < count; ++i) // parents come first
    {
        if (!renamed[static_cast<size_t>(i)] && renamed[static_cast<size_t>(mesh.Parents[static_cast<size_t>(i)])]) { renamed[static_cast<size_t>(i)] = 1; }
        if (renamed[static_cast<size_t>(i)]) { closed.Bones.push_back(i); }
    }
    return closed;
}

// Renames that make the engine accept `mesh` for AnimBlueprints of `target` and of every skeleton in `keep` (the mesh's
// own skeleton, the skeleton an outfit was made for): the union of the plans for each one, closed over subtrees. A bone
// that stays has no renamed ancestor, so wherever it is shared it is settled for that skeleton; renamed bones are
// mesh-only everywhere. A skeleton in `keep` whose root differs from the mesh's cannot be satisfied and is left out.
inline RenamePlan PlanConflictRenamesFor(const BoneTable& mesh, const BoneTable& target, const std::vector<const BoneTable*>& keep)
{
    RenamePlan plan = PlanConflictRenames(mesh, target);
    if (!plan.Possible || keep.empty()) { return plan; }
    std::vector<char> renamed(mesh.Names.size(), 0);
    for (int32_t bone : plan.Bones) { renamed[static_cast<size_t>(bone)] = 1; }
    for (const BoneTable* other : keep)
    {
        if (!other) { continue; }
        const RenamePlan extra = PlanConflictRenames(mesh, *other);
        if (!extra.Possible) { continue; }
        for (int32_t bone : extra.Bones) { renamed[static_cast<size_t>(bone)] = 1; }
    }
    RenamePlan merged;
    for (int32_t i = 1; i < mesh.Raw(); ++i)
    {
        if (renamed[static_cast<size_t>(i)]) { merged.Bones.push_back(i); }
    }
    return CloseRenamePlan(mesh, merged);
}
} // namespace SkelCompat
