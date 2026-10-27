// SkelCompatCore.hpp
// Portable logic for the RebirthSkelCompat UE4SS mod: JSON config parsing, object-path
// normalisation and a faithful copy of UE 4.26's USkeleton::IsCompatibleMesh test.
// No Unreal or Windows dependencies, so it is unit-tested off-target.
#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cwctype>
#include <memory>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
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

// (3.12.1) A number of seconds at the start of the text ("1.5", as std::stof reads it, without its exceptions): false
// (out unchanged) when it does not start with one.
inline bool ParseSeconds(const std::wstring& text, float& out)
{
    if (text.empty()) { return false; }
    wchar_t* end = nullptr;
    const double value = std::wcstod(text.c_str(), &end);
    if (!end || end == text.c_str() || !(value > -3.0e38 && value < 3.0e38)) { return false; }
    out = static_cast<float>(value);
    return true;
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
    bool KeepProportions = false;         // animations: every character keeps its own bone lengths (3.2, "proportions")
    std::vector<std::wstring> ProportionBones; // (3.8.2) "proportion_bones": more bones that keep the mesh's own length with
                                          // "proportions" (patterns as "keep": "R_Feather*", "*_Phy"), e.g. a smaller wing
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

// ---------------------------------------------------------------------------------------
// Animation set rows (3.1)
// A character's CharaSpec pack (/Game/DataAsset/Game/CharaSpec/CharaSpec_<row>) lists the animation sets (UEndAnimSet:
// animation name -> animation) the game looks its animations up in, by set name ("Battle00", "Neutral00", ...). A row
// rebuilds those sets from sources in order: the first source that has an animation name wins, whatever the pack
// already had fills in last, and "moves" put a chosen animation under a chosen name. Sets named Battle* take the
// "battle" sources, every other set (Neutral*, Emotion*, Facial*, ...) the "field" sources. Which skeleton plays the
// animations is still up to the pairs and families; a row's "cutscene" entry adds the family for its character.
// ---------------------------------------------------------------------------------------
// 3.2: how a source takes part besides "same name wins" (see AutoMatch).
//  Off:     an ordinary source: every animation name it has, first source wins.
//  Basic:   ("auto": "basic") the basic attacks only: every attack and air attack name of the set (normal and mode
//           attacks, counters, air combos) is filled from this source: the same name, else another variant of the same
//           move, else an attack of the same kind with the closest length. Abilities, limits and everything else (walking,
//           damage, ...) come from the next sources.
//  Attacks: ("auto": true) like Basic, and the attack abilities and limits too.
//  All:     ("auto": "all") the whole animation set: every name it has, like an ordinary source, and the attack names it
//           lacks matched as for Attacks.
enum class AutoMatchMode : uint8_t
{
    Off = 0,
    Attacks = 1,
    All = 2,
    Basic = 3
};

struct SetSource
{
    std::wstring Path;  // folder ("/Game/Motion/Player/PC0000_Cloud") or set object path ("/Game/.../Battle00.Battle00")
    bool Folder = true;
    std::wstring As;    // set source: the set it fills (empty = the set of its own name)
    AutoMatchMode Auto = AutoMatchMode::Off;
    std::vector<std::wstring> Only; // 3.2 "only": auto matches only use animations whose name contains one of these words
};

struct AnimMove
{
    std::wstring Set;       // empty: every set of the row that has Key
    std::wstring Key;       // animation name the game asks for, e.g. "B_Atk01_0"
    std::wstring Animation; // object path of the animation played under that name (a chain: its first animation)
    std::vector<std::wstring> Chain; // 3.2: two or more animations played one after another as one (start, loop, end
                                     // pieces of a move); the mod builds an AnimComposite of them at run time
    // 3.12.0: the part of each Chain animation played, seconds (from, to; to < 0: to its end): "path@0-1.5" in the json.
    // A move of one clipped animation has a Chain of one.
    std::vector<std::pair<float, float>> Clips;
};

// Every animation a move plays.
inline std::vector<std::wstring> MoveAnimations(const AnimMove& move)
{
    return move.Chain.empty() ? std::vector<std::wstring>{move.Animation} : move.Chain;
}

// 3.3: the battle commands a character has while it plays one primary animation pack. The game switches a character's
// pack with EndBattleAPI SetPrimaryAnimPack (ResetPrimaryAnimPack goes back to its own); while a pack plays, the
// character's BattlePlayerParameter row ("player") lists these abilities instead of the table's.
struct PackAbilities
{
    std::wstring Pack;                   // "Battle02"; the "Battle00" entry also applies at map load and after a reset
    std::vector<std::wstring> Commands;  // ATB abilities in the command menu (BattleAbility rows), in menu order
    std::vector<std::wstring> Limits;    // limit breaks (BattleAbility rows): level 1, 2, ...
    bool HasCommands = false;            // "commands" given (an empty list empties the menu)
    bool HasLimits = false;              // "limits" given
    // 3.4 "weapon_abilities": the ability a weapon gives (its Equipment row's BurstAbilityID, e.g. Cloud's Buster Sword
    // gives PC0000_AtkBurst02) -> the BattleAbility row it gives while this pack plays. Whether the weapon's ability is
    // learned (or the weapon equipped) still decides whether it shows.
    std::vector<std::pair<std::wstring, std::wstring>> Weapons;
    bool HasWeapons = false;             // "weapon_abilities" given (an empty object: the weapons' own)
};

// The pack the game plays when no other is set (and after ResetPrimaryAnimPack).
inline const wchar_t* DefaultAbilityPack() { return L"Battle00"; }

// ---------------------------------------------------------------------------------------
// 3.6: forms. A character with forms changes form in battle through the forms menu: hold its button (Triangle by
// default) and a command window in the game's menu art lists them (up to 13, 7 at a time; the list scrolls); pick one
// with the left stick or the D-pad and let go. A form is an animation pack (a set of the character's CharaSpec pack: its
// moves, switched with EndBattleAPI SetPrimaryAnimPack) and what changes with it: parts of the model shown or hidden,
// another model, effects and sounds played as it switches, real flying. The first form is the character's normal one:
// it is back in it when the battle ends.
// ---------------------------------------------------------------------------------------
constexpr size_t MaxForms = 13;
constexpr size_t MaxMovesetSources = 8;   // (3.15.1) "movesets" of one row

// An effect played on the character: a Niagara system or a Cascade particle system attached to its mesh.
struct FormEffect
{
    std::wstring Path;
    std::wstring Socket;     // socket or bone of the mesh it is attached at (empty: the mesh's root)
    float Scale = 1.0f;
    float Seconds = 0.0f;    // it plays this long, then stops and fades (0: the forms' "effect_seconds")
};

// A sound played on the character: a cue of a sound bank (SQEX SEAD). A bank path with {language} in it is a voice bank:
// the one of the language the game loaded (US, JP, FR, DE) plays.
struct FormSound
{
    std::wstring Bank;
    std::wstring Cue;
    float Start = 0.0f;    // (3.7.1) seconds into the sound it starts at: a slice of a long one (a cutscene's sound track)
    float Length = 0.0f;   // (3.7.1) seconds it plays, then stops (0: to its end)
    float Volume = 1.0f;   // (3.7.1)
};

// (3.9.0) A character's voice: the voice bank the voice lines of its animations play from (EndAnimNotifyPlayVoice:
// each names a bank and a cue; the cue stays, the bank is this one). "voice": a bank path ({language} where the voice
// language goes: /Game/Sound/Voice/{language}/Character/Player/VO_PC0010_13_YoungSephiroth), "own" (the banks the
// animations name), or {"bank": path, "replaces": [paths]}: the banks it plays in place of (by default the voice banks
// of the character's CharaSpec pack, but for the voices its row and forms switch to). On a row: in every form and in the
// field; on a form: in that form.
struct Voice
{
    bool Set = false;                       // the row or form says something ("voice")
    bool Own = false;                       // "own": the animations' own banks
    std::wstring Bank;                      // the bank's object path, its voice-language folder JP (the source package)
    std::vector<std::wstring> Replaces;     // object paths (JP); empty: the CharaSpec pack's voice banks
};

// A voice bank's path as the game's animations name it: its object path, the language folder of a voice bank its
// source's (JP): "/Game/Sound/Voice/{language}/X/VO_A" and ".../US/X/VO_A.VO_A" -> "/Game/Sound/Voice/JP/X/VO_A.VO_A".
inline std::wstring VoiceSourcePath(std::wstring_view bank)
{
    std::wstring path = NormalizeObjectPath(bank);
    const std::wstring_view root = L"/Game/Sound/Voice/";
    if (path.size() > root.size() && NameEquals(std::wstring_view(path).substr(0, root.size()), root))
    {
        const size_t slash = path.find(L'/', root.size());
        if (slash != std::wstring::npos) { path = path.substr(0, root.size()) + L"JP" + path.substr(slash); }
    }
    return path;
}

// Real flying: the character's movement flies while it is in the form, hovering above where the form started.
struct FormFlight
{
    bool On = false;
    float Height = 250.0f;   // how high above the ground where it started it hovers (cm)
    float Speed = 600.0f;    // how fast "up" and "down" raise and lower it (cm/s)
    float Max = 3000.0f;     // highest it goes above where it started (cm)
    std::wstring Up = L"Gamepad_DPad_Up";
    std::wstring Down = L"Gamepad_DPad_Down";
};

// A model part added in a form: another skeletal mesh attached to the character's mesh, following its pose (a monster's
// wings, face and core).
struct FormMesh
{
    std::wstring Mesh;
    std::wstring Socket;              // where it is attached (empty: the mesh's root)
    bool FollowPose = true;           // it plays the character's mesh's pose (master pose); false: its own (none)
};

// Effects played while the character runs one of some abilities in a form, stopped when the ability ends (a monster's
// conjured sword in its sword attacks).
struct FormAbilityEffects
{
    std::vector<std::wstring> Abilities;  // BattleAbility rows ("PC0010_BZ_Octaslash"); one ending in * stands for every
                                          // row that starts with it ("PC0010_NAtk_*")
    std::vector<FormEffect> Effects;

    bool Matches(std::wstring_view ability) const
    {
        if (ability.empty()) { return false; }
        for (const auto& pattern : Abilities)
        {
            if (!pattern.empty() && pattern.back() == L'*')
            {
                const size_t n = pattern.size() - 1;
                if (ability.size() >= n && NameEquals(ability.substr(0, n), std::wstring_view(pattern).substr(0, n))) { return true; }
            }
            else if (NameEquals(pattern, ability)) { return true; }
        }
        return false;
    }
};

// 3.6.6: a form's entrance, as the character in charge switches to it (with its switch effects, not quietly): its
// animation played over everything else (a slot of its AnimBlueprint), the screen white and fading back, the character
// coming down from above where it stands, effects, and a camera of its own for the shot: low in front of it looking up,
// moving in until it is close on its face, then back to the game's camera. An ability (an attack, a command) ends it.
struct FormEntranceCamera
{
    bool On = true;
    std::wstring Face = L"C_Head_a";  // the bone (or socket) of the model it looks at and ends close to
    float Distance = 900.0f;          // how far in front of the character it starts (cm)
    float Side = 150.0f;              // how far to the character's right (cm; below 0: its left)
    float Height = 40.0f;             // how high above the ground under the character it starts (cm)
    float Fov = 70.0f;                // its field of view (degrees)
    float CloseAt = 0.65f;            // the part of the shot after which it moves in to the face (0 to 1)
    float Close = 180.0f;             // how far in front of the face it ends (cm)
    float CloseFov = 30.0f;           // its field of view at the end (degrees)
    float Hold = 0.6f;                // it stays on the face this long after the shot (s)
    float BlendBack = 1.0f;           // how long the blend back to the game's camera takes (s)
    float Bars = 2.39f;               // the picture's shape while it is on (2.39: cinema bars; 0: the screen's own)
};

// 3.6.7: an entrance made of shots, the way a cutscene is (one made from the game's own: its cameras, its character's
// animations, its effects and lines), played one after another. Each shot has its animation (played as it starts, from
// "animation_start" seconds in), its camera's keys relative to the character (from where its model stands, turned the way
// the character faces, sized with the model: the offsets are in the units of a character of "scale"; the camera cuts from
// shot to shot), and effects and sounds at times in it. The shots with "before_switch" at the start play on the form the
// character comes from (a line before a transformation); the switch to the form follows them, then the other shots.
struct EntranceKey
{
    float T = 0.0f;                           // seconds into the shot
    float X = 0.0f, Y = 0.0f, Z = 0.0f;       // cm: in front of, to the right of and above where the model stands
    float Pitch = 0.0f, Yaw = 0.0f, Roll = 0.0f; // degrees; yaw 0 looks the way the character faces
    float Fov = 70.0f;                        // degrees (horizontal)
};

struct EntranceEffect
{
    float At = 0.0f;                          // seconds into the shot
    FormEffect Effect;                        // with a socket: attached to the model there
    float Offset[3]{};                        // without one: placed here (cm, as the camera's keys), not attached
    float Yaw = 0.0f;                         // (placed) its turn from the way the character faces (degrees)
};

struct EntranceSound
{
    float At = 0.0f;                          // seconds into the shot
    FormSound Sound;
    float Start = 0.0f;                       // seconds into the sound it starts at (a part of a cutscene's sound track)
    bool StopAtEnd = false;                   // it stops when the shot ends
};

struct EntranceShot
{
    std::wstring Name;
    float Seconds = 1.0f;                     // how long it lasts
    bool BeforeSwitch = false;                // (at the start) on the form the character comes from
    std::wstring Animation;                   // played as it starts (empty: none)
    float AnimationStart = 0.0f;              // from this many seconds into it
    float Rate = 1.0f;
    float Scale = 1.0f;                       // the size of the character the offsets were made for (1: the model at its own size)
    float Flash = 0.0f;                       // the screen starts this colour as the shot starts and fades back in this long (s)
    float FlashColor[3] = {1.0f, 1.0f, 1.0f};
    std::vector<EntranceKey> Camera;          // its camera (none: the game's camera for this shot)
    std::vector<EntranceEffect> Effects;
    std::vector<EntranceSound> Sounds;
};

constexpr size_t MaxEntranceShots = 32;
constexpr size_t MaxShotKeys = 4000;
constexpr size_t MaxShotCues = 64;

struct FormEntrance
{
    bool On = false;
    std::vector<EntranceShot> Shots;  // 3.6.7: a cutscene (then Animation, Descend and the camera's shot below are not used;
                                      // the camera's hold, blend_back and bars are)
    std::wstring Animation;           // played as a slot animation (empty: none)
    std::wstring Slot = L"DefaultSlot";
    float Rate = 1.0f;
    float Seconds = 0.0f;             // how long the shot lasts (0: the animation's length at its rate, else 6 s)
    float Flash = 1.5f;               // the screen starts white and fades back in this long (0: no flash)
    float FlashColor[3] = {1.0f, 1.0f, 1.0f};
    float Descend = 0.0f;             // the character comes down from this high above where it is (cm; 0: it does not)
    float DescendSeconds = 0.0f;      // how long that takes (0: 70% of the shot)
    std::vector<FormEffect> Effects;  // played on the character as it starts (for the whole shot, unless an effect says)
    FormEntranceCamera Camera;
    bool HoldInput = true;            // the sticks do nothing while it plays (the buttons still do)
    bool Skip = true;                 // an ability the character starts ends it early
    bool Invincible = true;           // the character takes no damage while it plays (the way the Meteor cinematic does)

    // (3.6.7) the shots that play before the switch: the "before_switch" ones at the start
    size_t PreludeShots() const
    {
        size_t n = 0;
        while (n < Shots.size() && Shots[n].BeforeSwitch) { ++n; }
        return n;
    }
    float PreludeSeconds() const
    {
        float s = 0.0f;
        for (size_t k = 0; k < PreludeShots(); ++k) { s += Shots[k].Seconds; }
        return s;
    }
    float ShotsSeconds() const
    {
        float s = 0.0f;
        for (const auto& shot : Shots) { s += shot.Seconds; }
        return s;
    }
};

// 3.6.16: how a form moves the battle camera of the character in charge: back along its view, up, a wider view, blended.
struct FormCamera
{
    bool Set = false;
    float Distance = 0.0f;   // cm further back along the camera's view (negative: closer)
    float Height = 0.0f;     // cm higher
    float Fov = 0.0f;        // degrees wider
    float Blend = 0.6f;      // seconds it takes to get there (and back)
};

// 3.6.16: the camera while some abilities run in a form (a summon called: M_SMN_*).
struct FormAbilityCamera
{
    std::vector<std::wstring> Abilities;  // as FormAbilityEffects' (a name ending in * stands for every row that starts with it)
    FormCamera Camera;

    bool Matches(std::wstring_view ability) const
    {
        FormAbilityEffects probe;
        probe.Abilities = Abilities;
        return probe.Matches(ability);
    }
};

// ---------------------------------------------------------------------------------------
// 3.7: "shooter": the character fights as a third-person shooter, the way Vincent plays in Dirge of Cerberus. The camera
// is over its shoulder and turns with the right stick (or the mouse), a reticle is in the middle of the screen, and the
// character always faces where it aims. The fire button shoots a real bullet of the game's at what is under the reticle
// (a damage source: its damage, numbers and stagger), from a clip that empties and is reloaded (the ammo itself never runs
// out). The aim button brings the camera in (a narrower view, slower turning), the zoom button closer still. Its moves
// are the Dirge of Cerberus motions of the character (aim stance, walking and running every way while aiming, firing and
// reloading), played over the game's own pose (its hair and cloth physics and its face stay the game's), the upper body
// turned so the gun points at the reticle. While it is on, the game no longer sees the buttons the shooter uses (read from
// the controller itself: a DualSense or DualShock 4, or an XInput pad), and a DualSense's adaptive triggers pull like a
// gun's. The game's own moves stay on the other buttons (Square: the character's normal attack, here a melee combo).
// ---------------------------------------------------------------------------------------
namespace Shooter
{
// ---- pad buttons, as the mod reads them from the controller ----
enum class Button : uint8_t { None = 0, Square, Cross, Circle, Triangle, L1, R1, L2, R2, L3, R3, Create, Options, PS, Touchpad, Up, Down, Left, Right, Count };

inline constexpr uint32_t Bit(Button b) { return b == Button::None ? 0u : (1u << static_cast<uint32_t>(b)); }

struct ButtonInfo
{
    Button Id;
    const wchar_t* Key;     // the input key the game's input has for it ("" when it has none)
    const wchar_t* Label;
};

inline const std::vector<ButtonInfo>& Buttons()
{
    static const std::vector<ButtonInfo> list = {
        {Button::Square, L"Gamepad_FaceButton_Left", L"Square"},  {Button::Cross, L"Gamepad_FaceButton_Bottom", L"Cross"},
        {Button::Circle, L"Gamepad_FaceButton_Right", L"Circle"}, {Button::Triangle, L"Gamepad_FaceButton_Top", L"Triangle"},
        {Button::L1, L"Gamepad_LeftShoulder", L"L1"},             {Button::R1, L"Gamepad_RightShoulder", L"R1"},
        {Button::L2, L"Gamepad_LeftTrigger", L"L2"},              {Button::R2, L"Gamepad_RightTrigger", L"R2"},
        {Button::L3, L"Gamepad_LeftThumbstick", L"L3"},           {Button::R3, L"Gamepad_RightThumbstick", L"R3"},
        {Button::Create, L"Gamepad_Special_Left", L"Create"},     {Button::Options, L"Gamepad_Special_Right", L"Options"},
        {Button::PS, L"", L"PS"},                                 {Button::Touchpad, L"", L"Touchpad"},
        {Button::Up, L"Gamepad_DPad_Up", L"Up"},                  {Button::Down, L"Gamepad_DPad_Down", L"Down"},
        {Button::Left, L"Gamepad_DPad_Left", L"Left"},            {Button::Right, L"Gamepad_DPad_Right", L"Right"}};
    return list;
}

// "R2", "Square", "X" (the cross), "Gamepad_RightTrigger"...; None when it is none of them.
inline Button ButtonOf(std::wstring_view text)
{
    const std::wstring t = Trim(text);
    if (t.empty()) { return Button::None; }
    for (const auto& b : Buttons())
    {
        if (NameEquals(t, b.Label) || (*b.Key && NameEquals(t, b.Key))) { return b.Id; }
    }
    static const std::pair<const wchar_t*, Button> other[] = {
        {L"X", Button::Cross},       {L"A", Button::Cross},       {L"B", Button::Circle},    {L"Y", Button::Triangle},   {L"Share", Button::Create},
        {L"Select", Button::Create}, {L"Back", Button::Create},   {L"Start", Button::Options}, {L"Menu", Button::Options}, {L"LB", Button::L1},
        {L"RB", Button::R1},         {L"LT", Button::L2},         {L"RT", Button::R2},       {L"LS", Button::L3},        {L"RS", Button::R3},
        {L"DPad_Up", Button::Up},    {L"DPad_Down", Button::Down}, {L"DPad_Left", Button::Left}, {L"DPad_Right", Button::Right}};
    for (const auto& [name, id] : other)
    {
        if (NameEquals(t, name)) { return id; }
    }
    return Button::None;
}

inline const wchar_t* LabelOf(Button b)
{
    for (const auto& i : Buttons()) { if (i.Id == b) { return i.Label; } }
    return L"none";
}

inline const wchar_t* KeyNameOf(Button b)
{
    for (const auto& i : Buttons()) { if (i.Id == b) { return i.Key; } }
    return L"";
}

inline std::wstring LabelsOf(uint32_t mask)
{
    std::wstring text;
    for (const auto& i : Buttons())
    {
        if (mask & Bit(i.Id)) { text += (text.empty() ? L"" : L", ") + std::wstring(i.Label); }
    }
    return text.empty() ? std::wstring(L"none") : text;
}

// ---- a DualSense's adaptive trigger ----
enum class TriggerMode : uint8_t { Off, Feedback, Weapon, Vibration };

// Feedback: the trigger pushes back with Strength from zone Start (0 to 9) to its end. Weapon: a gun's trigger: resistance
// from Start (2 to 7) that gives way at End (Start+1 to 8). Vibration: it shakes with Strength (its amplitude) at
// Frequency (Hz) from Start on. Strengths go from 1 to 8.
struct TriggerEffect
{
    TriggerMode Mode = TriggerMode::Off;
    int Start = 0;
    int End = 0;
    int Strength = 0;
    int Frequency = 0;
    bool operator==(const TriggerEffect& o) const
    {
        return Mode == o.Mode && Start == o.Start && End == o.End && Strength == o.Strength && Frequency == o.Frequency;
    }
    bool operator!=(const TriggerEffect& o) const { return !(*this == o); }
};

inline TriggerEffect FeedbackTrigger(int start, int strength) { return {TriggerMode::Feedback, start, 0, strength, 0}; }
inline TriggerEffect WeaponTrigger(int start, int end, int strength) { return {TriggerMode::Weapon, start, end, strength, 0}; }
inline TriggerEffect VibrationTrigger(int start, int amplitude, int frequency) { return {TriggerMode::Vibration, start, 0, amplitude, frequency}; }

inline std::wstring TriggerText(const TriggerEffect& e)
{
    switch (e.Mode)
    {
    case TriggerMode::Feedback: return L"feedback from " + std::to_wstring(e.Start) + L", strength " + std::to_wstring(e.Strength);
    case TriggerMode::Weapon: return L"gun trigger " + std::to_wstring(e.Start) + L"-" + std::to_wstring(e.End) + L", strength " + std::to_wstring(e.Strength);
    case TriggerMode::Vibration:
        return L"vibration from " + std::to_wstring(e.Start) + L", strength " + std::to_wstring(e.Strength) + L", " + std::to_wstring(e.Frequency) + L" Hz";
    default: return L"off";
    }
}

// The 11 bytes of one trigger's effect in a DualSense output report (the controller's own effect format).
inline void EncodeTrigger(const TriggerEffect& e, uint8_t out[11])
{
    std::memset(out, 0, 11);
    out[0] = 0x05;   // off
    if (e.Mode == TriggerMode::Feedback)
    {
        const int start = std::clamp(e.Start, 0, 9), strength = std::clamp(e.Strength, 0, 8);
        if (strength == 0) { return; }
        uint32_t zones = 0, forces = 0;
        for (int i = start; i < 10; ++i)
        {
            zones |= 1u << i;
            forces |= static_cast<uint32_t>(strength - 1) << (3 * i);
        }
        out[0] = 0x21;
        out[1] = static_cast<uint8_t>(zones);
        out[2] = static_cast<uint8_t>(zones >> 8);
        out[3] = static_cast<uint8_t>(forces);
        out[4] = static_cast<uint8_t>(forces >> 8);
        out[5] = static_cast<uint8_t>(forces >> 16);
        out[6] = static_cast<uint8_t>(forces >> 24);
    }
    else if (e.Mode == TriggerMode::Weapon)
    {
        const int start = std::clamp(e.Start, 2, 7), end = std::clamp(e.End, start + 1, 8), strength = std::clamp(e.Strength, 0, 8);
        if (strength == 0) { return; }
        const uint32_t zones = (1u << start) | (1u << end);
        out[0] = 0x25;
        out[1] = static_cast<uint8_t>(zones);
        out[2] = static_cast<uint8_t>(zones >> 8);
        out[3] = static_cast<uint8_t>(strength - 1);
    }
    else if (e.Mode == TriggerMode::Vibration)
    {
        const int start = std::clamp(e.Start, 0, 9), amplitude = std::clamp(e.Strength, 0, 8), frequency = std::clamp(e.Frequency, 0, 255);
        if (amplitude == 0 || frequency == 0) { return; }
        uint32_t zones = 0, strengths = 0;
        for (int i = start; i < 10; ++i)
        {
            zones |= 1u << i;
            strengths |= static_cast<uint32_t>(amplitude - 1) << (3 * i);
        }
        out[0] = 0x26;
        out[1] = static_cast<uint8_t>(zones);
        out[2] = static_cast<uint8_t>(zones >> 8);
        out[3] = static_cast<uint8_t>(strengths);
        out[4] = static_cast<uint8_t>(strengths >> 8);
        out[5] = static_cast<uint8_t>(strengths >> 16);
        out[6] = static_cast<uint8_t>(strengths >> 24);
        out[9] = static_cast<uint8_t>(frequency);
    }
}

// CRC-32 (the zip one), and a Bluetooth report's: over a seed byte (0xA1 input, 0xA2 output) and the report but its last 4.
inline uint32_t Crc32(const uint8_t* data, size_t size, uint32_t crc = 0xFFFFFFFFu)
{
    for (size_t i = 0; i < size; ++i)
    {
        crc ^= data[i];
        for (int k = 0; k < 8; ++k) { crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u))); }
    }
    return crc;
}

inline uint32_t ReportCrc(uint8_t seed, const uint8_t* report, size_t size)
{
    uint32_t crc = Crc32(&seed, 1);
    crc = Crc32(report, size, crc);
    return ~crc;
}

inline void StoreCrc(uint8_t seed, uint8_t* report, size_t size)
{
    const uint32_t crc = ReportCrc(seed, report, size - 4);
    report[size - 4] = static_cast<uint8_t>(crc);
    report[size - 3] = static_cast<uint8_t>(crc >> 8);
    report[size - 2] = static_cast<uint8_t>(crc >> 16);
    report[size - 1] = static_cast<uint8_t>(crc >> 24);
}

// A DualSense output report that sets only the two triggers' effects (nothing else the controller does changes): USB
// (report 0x02) or Bluetooth (0x31, with its sequence number and checksum). `size` is the device's output report length
// (78 or more over Bluetooth, 48 or more over USB; the rest is zeros). Returns the bytes to write (0: too small).
inline size_t TriggerReport(bool bluetooth, uint8_t sequence, const uint8_t right[11], const uint8_t left[11], uint8_t* out, size_t size)
{
    if (size < (bluetooth ? 78u : 48u)) { return 0; }
    std::memset(out, 0, size);
    const size_t c = bluetooth ? 3 : 1;   // where the common part starts
    if (bluetooth)
    {
        out[0] = 0x31;
        out[1] = static_cast<uint8_t>((sequence & 0x0f) << 4);
        out[2] = 0x10;
    }
    else { out[0] = 0x02; }
    out[c] = 0x04 | 0x08;                 // valid_flag0: the right and the left trigger's effects
    std::memcpy(out + c + 10, right, 11);
    std::memcpy(out + c + 21, left, 11);
    if (bluetooth) { StoreCrc(0xA2, out, 78); }
    return size;
}

// The triggers' effects put into an output report the game sends to a DualSense (a copy of it): the game's lights and
// rumble stay, the triggers are the mod's. False: not a DualSense output report.
inline bool PatchTriggerReport(uint8_t* r, size_t n, const uint8_t right[11], const uint8_t left[11])
{
    size_t c = 0;
    bool bluetooth = false;
    if (n >= 48 && r[0] == 0x02) { c = 1; }
    else if (n >= 78 && r[0] == 0x31) { c = 3; bluetooth = true; }
    else { return false; }
    r[c] |= 0x04 | 0x08;
    std::memcpy(r + c + 10, right, 11);
    std::memcpy(r + c + 21, left, 11);
    if (bluetooth) { StoreCrc(0xA2, r, 78); }
    return true;
}

// ---- reading the pad (and taking buttons away from the game) ----
enum class PadKind : uint8_t { None, DualSenseUsb, DualSenseBt, DualShock4Usb, DualShock4Bt };

inline const wchar_t* PadKindText(PadKind k)
{
    switch (k)
    {
    case PadKind::DualSenseUsb: return L"DualSense (USB)";
    case PadKind::DualSenseBt: return L"DualSense (Bluetooth)";
    case PadKind::DualShock4Usb: return L"DualShock 4 (USB)";
    case PadKind::DualShock4Bt: return L"DualShock 4 (Bluetooth)";
    default: return L"none";
    }
}

struct PadRead
{
    float L2 = 0.0f, R2 = 0.0f;   // how far the triggers are pulled (0 to 1)
    float RX = 0.0f, RY = 0.0f;   // the right stick (-1 to 1, up and right positive), as the controller has it
    float LX = 0.0f, LY = 0.0f;   // (3.11.0) the left stick, the same way
    uint32_t Down = 0;            // Bit() of the buttons held
};

// A stick axis byte (128 the middle) moved toward the middle by `scale` (0 to 1).
inline uint8_t ScaledAxis(uint8_t v, float scale)
{
    const long moved = std::lround(128.0f + (static_cast<float>(v) - 128.0f) * std::clamp(scale, 0.0f, 1.0f));
    return static_cast<uint8_t>(std::clamp(moved, 0L, 255L));
}

inline uint32_t HatBits(int hat)
{
    switch (hat)
    {
    case 0: return Bit(Button::Up);
    case 1: return Bit(Button::Up) | Bit(Button::Right);
    case 2: return Bit(Button::Right);
    case 3: return Bit(Button::Down) | Bit(Button::Right);
    case 4: return Bit(Button::Down);
    case 5: return Bit(Button::Down) | Bit(Button::Left);
    case 6: return Bit(Button::Left);
    case 7: return Bit(Button::Up) | Bit(Button::Left);
    default: return 0;
    }
}

inline int HatOf(uint32_t down)
{
    const bool u = down & Bit(Button::Up), d = down & Bit(Button::Down), l = down & Bit(Button::Left), r = down & Bit(Button::Right);
    if (u && r) { return 1; }
    if (d && r) { return 3; }
    if (d && l) { return 5; }
    if (u && l) { return 7; }
    if (u) { return 0; }
    if (r) { return 2; }
    if (d) { return 4; }
    if (l) { return 6; }
    return 8;
}

// One input report of a DualSense or DualShock 4 (`kind`), as the game reads it: what it holds, and with `block`, those
// buttons taken out of it in place (their bits cleared, a blocked trigger's travel zeroed), with `rightStick` below 1 the
// right stick moved toward its middle that much (the slower aim), and (3.7.3) with `force` those buttons held for the
// game (a face or shoulder button's bit set, a trigger pulled all the way; after `block`, so a button in both is held);
// a Bluetooth report's checksum is made again when it changed. `out` is what the controller itself holds. False: not an
// input report this knows (it is left as it is).
inline bool ReadPadReport(uint8_t* r, size_t n, PadKind kind, uint32_t block, PadRead& out, float rightStick = 1.0f, uint32_t force = 0, bool centre = false)
{
    int b0 = -1, b1 = 0, b2 = 0, l2 = 0, r2 = 0, rx = 0, ry = 0;
    bool crc = false;
    if (kind == PadKind::DualSenseUsb && n >= 11 && r[0] == 0x01) { rx = 3; ry = 4; l2 = 5; r2 = 6; b0 = 8; b1 = 9; b2 = 10; }
    else if (kind == PadKind::DualSenseBt && n >= 78 && r[0] == 0x31) { rx = 4; ry = 5; l2 = 6; r2 = 7; b0 = 9; b1 = 10; b2 = 11; crc = true; }
    else if ((kind == PadKind::DualSenseBt || kind == PadKind::DualShock4Bt || kind == PadKind::DualShock4Usb) && n >= 10 && r[0] == 0x01)
    {
        rx = 3; ry = 4; b0 = 5; b1 = 6; b2 = 7; l2 = 8; r2 = 9;   // a DualShock 4's USB report, and the short Bluetooth report of both
    }
    else if (kind == PadKind::DualShock4Bt && n >= 78 && r[0] == 0x11) { rx = 5; ry = 6; b0 = 7; b1 = 8; b2 = 9; l2 = 10; r2 = 11; crc = true; }
    if (b0 < 0) { return false; }
    out.L2 = r[l2] / 255.0f;
    out.R2 = r[r2] / 255.0f;
    out.RX = std::clamp((static_cast<float>(r[rx]) - 128.0f) / 127.0f, -1.0f, 1.0f);
    out.RY = std::clamp((128.0f - static_cast<float>(r[ry])) / 127.0f, -1.0f, 1.0f);
    const int lx = rx - 2, ly = rx - 1;   // (3.11.0: the left stick, the two bytes before the right one in every report)
    out.LX = std::clamp((static_cast<float>(r[lx]) - 128.0f) / 127.0f, -1.0f, 1.0f);
    out.LY = std::clamp((128.0f - static_cast<float>(r[ly])) / 127.0f, -1.0f, 1.0f);
    uint32_t down = HatBits(r[b0] & 0x0f);
    static constexpr Button Face[4] = {Button::Square, Button::Cross, Button::Circle, Button::Triangle};
    static constexpr Button Shoulder[8] = {Button::L1, Button::R1, Button::L2, Button::R2, Button::Create, Button::Options, Button::L3, Button::R3};
    for (int k = 0; k < 4; ++k) { if (r[b0] & (0x10 << k)) { down |= Bit(Face[k]); } }
    for (int k = 0; k < 8; ++k) { if (r[b1] & (1 << k)) { down |= Bit(Shoulder[k]); } }
    if (r[b2] & 0x01) { down |= Bit(Button::PS); }
    if (r[b2] & 0x02) { down |= Bit(Button::Touchpad); }
    out.Down = down;
    bool changed = false;
    if (rightStick < 0.999f)
    {
        const uint8_t x = ScaledAxis(r[rx], rightStick), y = ScaledAxis(r[ry], rightStick);
        if (x != r[rx] || y != r[ry]) { r[rx] = x; r[ry] = y; changed = true; }
    }
    if (centre)   // (3.11.0) both sticks in the middle for the game
    {
        for (const int at : {lx, ly, rx, ry})
        {
            if (r[at] != 128) { r[at] = 128; changed = true; }
        }
    }
    const uint32_t pad = Bit(Button::Up) | Bit(Button::Down) | Bit(Button::Left) | Bit(Button::Right);
    if (block & pad & down)
    {
        r[b0] = static_cast<uint8_t>((r[b0] & 0xf0) | HatOf(down & ~block & pad));
        changed = true;
    }
    for (int k = 0; k < 4; ++k)
    {
        if ((block & Bit(Face[k])) && (r[b0] & (0x10 << k))) { r[b0] = static_cast<uint8_t>(r[b0] & ~(0x10 << k)); changed = true; }
    }
    for (int k = 0; k < 8; ++k)
    {
        if ((block & Bit(Shoulder[k])) && (r[b1] & (1 << k))) { r[b1] = static_cast<uint8_t>(r[b1] & ~(1 << k)); changed = true; }
    }
    if ((block & Bit(Button::PS)) && (r[b2] & 0x01)) { r[b2] = static_cast<uint8_t>(r[b2] & ~0x01); changed = true; }
    if ((block & Bit(Button::Touchpad)) && (r[b2] & 0x02)) { r[b2] = static_cast<uint8_t>(r[b2] & ~0x02); changed = true; }
    if ((block & Bit(Button::L2)) && r[l2]) { r[l2] = 0; changed = true; }
    if ((block & Bit(Button::R2)) && r[r2]) { r[r2] = 0; changed = true; }
    // (3.7.3) the buttons the game is to see held
    if (force)
    {
        for (int k = 0; k < 4; ++k)
        {
            if ((force & Bit(Face[k])) && !(r[b0] & (0x10 << k))) { r[b0] = static_cast<uint8_t>(r[b0] | (0x10 << k)); changed = true; }
        }
        for (int k = 0; k < 8; ++k)
        {
            if ((force & Bit(Shoulder[k])) && !(r[b1] & (1 << k))) { r[b1] = static_cast<uint8_t>(r[b1] | (1 << k)); changed = true; }
        }
        if ((force & Bit(Button::L2)) && r[l2] != 255) { r[l2] = 255; changed = true; }
        if ((force & Bit(Button::R2)) && r[r2] != 255) { r[r2] = 255; changed = true; }
    }
    if (changed && crc) { StoreCrc(0xA1, r, 78); }
    return true;
}

// An XInput pad's XINPUT_GAMEPAD (12 bytes: buttons, the two triggers, the sticks), read, with `block` taken out of it,
// its right stick moved toward the middle by `rightStick` and (3.7.3) `force` held for the game (after `block`).
inline void ReadXInputPad(uint8_t* gamepad, uint32_t block, PadRead& out, float rightStick = 1.0f, uint32_t force = 0, bool centre = false)
{
    uint16_t w = 0;
    std::memcpy(&w, gamepad, 2);
    static constexpr std::pair<uint16_t, Button> Map[] = {
        {0x0001, Button::Up},      {0x0002, Button::Down}, {0x0004, Button::Left}, {0x0008, Button::Right},  {0x0010, Button::Options},
        {0x0020, Button::Create},  {0x0040, Button::L3},   {0x0080, Button::R3},   {0x0100, Button::L1},     {0x0200, Button::R1},
        {0x1000, Button::Cross},   {0x2000, Button::Circle}, {0x4000, Button::Square}, {0x8000, Button::Triangle}};
    out.L2 = gamepad[2] / 255.0f;
    out.R2 = gamepad[3] / 255.0f;
    int16_t x = 0, y = 0;
    std::memcpy(&x, gamepad + 8, 2);
    std::memcpy(&y, gamepad + 10, 2);
    out.RX = std::clamp(x / 32767.0f, -1.0f, 1.0f);
    out.RY = std::clamp(y / 32767.0f, -1.0f, 1.0f);
    int16_t lx = 0, ly = 0;   // (3.11.0)
    std::memcpy(&lx, gamepad + 4, 2);
    std::memcpy(&ly, gamepad + 6, 2);
    out.LX = std::clamp(lx / 32767.0f, -1.0f, 1.0f);
    out.LY = std::clamp(ly / 32767.0f, -1.0f, 1.0f);
    out.Down = 0;
    for (const auto& [mask, id] : Map)
    {
        if (w & mask) { out.Down |= Bit(id); }
    }
    if (out.L2 > 0.12f) { out.Down |= Bit(Button::L2); }
    if (out.R2 > 0.12f) { out.Down |= Bit(Button::R2); }
    if (rightStick < 0.999f)
    {
        const float k = std::clamp(rightStick, 0.0f, 1.0f);
        const int16_t sx = static_cast<int16_t>(std::lround(x * k)), sy = static_cast<int16_t>(std::lround(y * k));
        std::memcpy(gamepad + 8, &sx, 2);
        std::memcpy(gamepad + 10, &sy, 2);
    }
    if (centre) { std::memset(gamepad + 4, 0, 8); }   // (3.11.0) both sticks in the middle for the game
    if (!block && !force) { return; }
    for (const auto& [mask, id] : Map)
    {
        if (block & Bit(id)) { w = static_cast<uint16_t>(w & ~mask); }
        if (force & Bit(id)) { w = static_cast<uint16_t>(w | mask); }   // (3.7.3)
    }
    std::memcpy(gamepad, &w, 2);
    if (block & Bit(Button::L2)) { gamepad[2] = 0; }
    if (block & Bit(Button::R2)) { gamepad[3] = 0; }
    if (force & Bit(Button::L2)) { gamepad[2] = 255; }
    if (force & Bit(Button::R2)) { gamepad[3] = 255; }
}

// ---- the shooter's locomotion: how much of each Dirge of Cerberus motion plays ----
struct Locomotion
{
    float Idle = 1.0f, Walk = 0.0f, Forward = 0.0f, Back = 0.0f, Left = 0.0f, Right = 0.0f;
    float Rate = 1.0f;   // how fast the walk and run motions play
};

// `speed` (cm/s, on the ground) and `angle` (degrees of the movement from where the character aims: 0 ahead, 90 to its
// right, 180 behind, -90 to its left); the walk is its slow forward motion, the runs every way.
inline Locomotion LocomotionFor(float speed, float angle, float walkSpeed, float runSpeed)
{
    Locomotion m;
    walkSpeed = std::max(walkSpeed, 1.0f);
    runSpeed = std::max(runSpeed, walkSpeed + 1.0f);
    if (!std::isfinite(speed) || !std::isfinite(angle)) { return m; }
    float a = std::fmod(angle, 360.0f);
    if (a > 180.0f) { a -= 360.0f; }
    if (a <= -180.0f) { a += 360.0f; }
    const float moving = std::clamp((speed - 25.0f) / std::max(1.0f, walkSpeed * 0.8f - 25.0f), 0.0f, 1.0f);
    float f = 0.0f, r = 0.0f, b = 0.0f, l = 0.0f;
    if (a >= 0.0f && a <= 90.0f) { f = 1.0f - a / 90.0f; r = a / 90.0f; }
    else if (a > 90.0f) { r = 1.0f - (a - 90.0f) / 90.0f; b = (a - 90.0f) / 90.0f; }
    else if (a >= -90.0f) { f = 1.0f + a / 90.0f; l = -a / 90.0f; }
    else { l = 1.0f - (-a - 90.0f) / 90.0f; b = (-a - 90.0f) / 90.0f; }
    // the walk: ahead (within 45 degrees) and slow
    const float ahead = std::clamp(1.0f - std::fabs(a) / 45.0f, 0.0f, 1.0f);
    const float slow = std::clamp((runSpeed * 0.7f - speed) / std::max(1.0f, runSpeed * 0.7f - walkSpeed), 0.0f, 1.0f);
    const float walk = ahead * slow;
    m.Idle = 1.0f - moving;
    m.Walk = moving * walk;
    const float run = moving * (1.0f - walk);
    m.Forward = run * f;
    m.Right = run * r;
    m.Back = run * b;
    m.Left = run * l;
    const float made = walk > 0.5f ? walkSpeed : runSpeed;
    m.Rate = speed < 25.0f ? 1.0f : std::clamp(speed / made, 0.5f, 1.6f);
    return m;
}

// ---- pose math (UE's conventions: FTransform A*B applies A, then B; quaternion a*b applies b, then a) ----
struct V3
{
    float X = 0.0f, Y = 0.0f, Z = 0.0f;
};
struct Q4
{
    float X = 0.0f, Y = 0.0f, Z = 0.0f, W = 1.0f;
};
struct Xf
{
    Q4 R;
    V3 T;
    V3 S{1.0f, 1.0f, 1.0f};
};

inline V3 operator+(V3 a, V3 b) { return {a.X + b.X, a.Y + b.Y, a.Z + b.Z}; }
inline V3 operator-(V3 a, V3 b) { return {a.X - b.X, a.Y - b.Y, a.Z - b.Z}; }
inline V3 operator*(V3 a, float s) { return {a.X * s, a.Y * s, a.Z * s}; }
inline float Dot(V3 a, V3 b) { return a.X * b.X + a.Y * b.Y + a.Z * b.Z; }
inline V3 Cross(V3 a, V3 b) { return {a.Y * b.Z - a.Z * b.Y, a.Z * b.X - a.X * b.Z, a.X * b.Y - a.Y * b.X}; }
inline float Length(V3 a) { return std::sqrt(Dot(a, a)); }
inline V3 Unit(V3 a)
{
    const float n = Length(a);
    return n > 1e-6f ? a * (1.0f / n) : V3{};
}
inline Q4 Mul(Q4 a, Q4 b)
{
    return {a.W * b.X + a.X * b.W + a.Y * b.Z - a.Z * b.Y, a.W * b.Y - a.X * b.Z + a.Y * b.W + a.Z * b.X,
            a.W * b.Z + a.X * b.Y - a.Y * b.X + a.Z * b.W, a.W * b.W - a.X * b.X - a.Y * b.Y - a.Z * b.Z};
}
inline Q4 Conj(Q4 q) { return {-q.X, -q.Y, -q.Z, q.W}; }
inline float QDot(Q4 a, Q4 b) { return a.X * b.X + a.Y * b.Y + a.Z * b.Z + a.W * b.W; }
inline Q4 QUnit(Q4 q)
{
    const float n = std::sqrt(QDot(q, q));
    if (!(n > 1e-8f) || !std::isfinite(n)) { return Q4{}; }
    return {q.X / n, q.Y / n, q.Z / n, q.W / n};
}
inline V3 Rotate(Q4 q, V3 v)
{
    const V3 u{q.X, q.Y, q.Z};
    const float s = q.W;
    return u * (2.0f * Dot(u, v)) + v * (s * s - Dot(u, u)) + Cross(u, v) * (2.0f * s);
}
inline Q4 AxisAngle(V3 axis, float radians)
{
    const V3 a = Unit(axis);
    const float h = radians * 0.5f, s = std::sin(h);
    return {a.X * s, a.Y * s, a.Z * s, std::cos(h)};
}
// The shortest rotation that turns unit vector a onto unit vector b.
inline Q4 FromTo(V3 a, V3 b)
{
    const float d = std::clamp(Dot(a, b), -1.0f, 1.0f);
    if (d > 0.999999f) { return Q4{}; }
    if (d < -0.999999f)
    {
        V3 axis = Cross(V3{1, 0, 0}, a);
        if (Length(axis) < 1e-3f) { axis = Cross(V3{0, 1, 0}, a); }
        return AxisAngle(axis, 3.14159265f);
    }
    const V3 c = Cross(a, b);
    return QUnit(Q4{c.X, c.Y, c.Z, 1.0f + d});
}
inline float AngleOf(Q4 q) { return 2.0f * std::acos(std::clamp(std::fabs(QUnit(q).W), 0.0f, 1.0f)); }
// The part t (0 to 1) of rotation q, about the same axis.
inline Q4 Part(Q4 q, float t)
{
    q = QUnit(q);
    if (q.W < 0.0f) { q = {-q.X, -q.Y, -q.Z, -q.W}; }
    const float angle = 2.0f * std::acos(std::clamp(q.W, -1.0f, 1.0f));
    if (angle < 1e-5f) { return Q4{}; }
    return AxisAngle(V3{q.X, q.Y, q.Z}, angle * t);
}
inline Q4 NLerp(Q4 a, Q4 b, float t)
{
    if (QDot(a, b) < 0.0f) { b = {-b.X, -b.Y, -b.Z, -b.W}; }
    return QUnit(Q4{a.X + (b.X - a.X) * t, a.Y + (b.Y - a.Y) * t, a.Z + (b.Z - a.Z) * t, a.W + (b.W - a.W) * t});
}
inline V3 Lerp(V3 a, V3 b, float t) { return a + (b - a) * t; }
inline V3 Times(V3 a, V3 b) { return {a.X * b.X, a.Y * b.Y, a.Z * b.Z}; }
inline V3 SafeInverse(V3 s)
{
    const auto inv = [](float v) { return std::fabs(v) > 1e-6f ? 1.0f / v : 0.0f; };
    return {inv(s.X), inv(s.Y), inv(s.Z)};
}
// A then B (FTransform's A * B).
inline Xf Compose(const Xf& a, const Xf& b)
{
    Xf o;
    o.R = QUnit(Mul(b.R, a.R));
    o.S = Times(a.S, b.S);
    o.T = Rotate(b.R, Times(b.S, a.T)) + b.T;
    return o;
}
inline Xf Inverse(const Xf& a)
{
    Xf o;
    o.R = Conj(QUnit(a.R));
    o.S = SafeInverse(a.S);
    o.T = Rotate(o.R, Times(o.S, a.T * -1.0f));
    return o;
}
// The transform of `child` under `parent`: Compose(Relative(child, parent), parent) == child.
inline Xf Relative(const Xf& child, const Xf& parent)
{
    const Q4 inv = Conj(QUnit(parent.R));
    const V3 invScale = SafeInverse(parent.S);
    Xf o;
    o.R = QUnit(Mul(inv, child.R));
    o.S = Times(child.S, invScale);
    o.T = Times(Rotate(inv, child.T - parent.T), invScale);
    return o;
}
inline Xf Blend(const Xf& a, const Xf& b, float t)
{
    Xf o;
    o.R = NLerp(a.R, b.R, t);
    o.T = Lerp(a.T, b.T, t);
    o.S = Lerp(a.S, b.S, t);
    return o;
}

// UE's rotator directions (degrees): ahead, to the right.
inline V3 ForwardOf(float yaw, float pitch)
{
    constexpr float Rad = 3.14159265f / 180.0f;
    const float cp = std::cos(pitch * Rad), sp = std::sin(pitch * Rad), cy = std::cos(yaw * Rad), sy = std::sin(yaw * Rad);
    return {cp * cy, cp * sy, sp};
}
inline V3 RightOf(float yaw)
{
    constexpr float Rad = 3.14159265f / 180.0f;
    return {-std::sin(yaw * Rad), std::cos(yaw * Rad), 0.0f};
}
// The camera over the shoulder: `back` behind the pivot along the view, `side` to its right, `up` above it.
inline V3 ShoulderCamera(V3 pivot, float yaw, float pitch, float back, float side, float up)
{
    return pivot - ForwardOf(yaw, pitch) * back + RightOf(yaw) * side + V3{0.0f, 0.0f, up};
}
// Yaw and pitch (degrees) of a direction.
inline void AnglesOf(V3 d, float& yaw, float& pitch)
{
    constexpr float Deg = 180.0f / 3.14159265f;
    yaw = std::atan2(d.Y, d.X) * Deg;
    pitch = std::atan2(d.Z, std::sqrt(d.X * d.X + d.Y * d.Y)) * Deg;
}

// The target a shot goes to: of `points` (their centres, with `radii`), the one nearest the line of sight from `eye`
// along unit `dir` within `assist` degrees (or within its own size), in front of the eye and within `range`; -1: none.
inline int PickTarget(V3 eye, V3 dir, const std::vector<V3>& points, const std::vector<float>& radii, float assist, float range)
{
    constexpr float Deg = 180.0f / 3.14159265f;
    int best = -1;
    float bestScore = 1e9f;
    for (size_t i = 0; i < points.size(); ++i)
    {
        const V3 d = points[i] - eye;
        const float distance = Length(d);
        if (!(distance > 1.0f) || distance > range) { continue; }
        const float along = Dot(d, dir);
        if (along <= 0.0f) { continue; }
        const float angle = std::acos(std::clamp(along / distance, -1.0f, 1.0f)) * Deg;
        const float size = i < radii.size() ? std::max(0.0f, radii[i]) : 0.0f;
        const float own = std::atan(size / distance) * Deg;
        const float allowed = std::max(assist, own);
        if (angle > allowed) { continue; }
        const float score = angle / std::max(allowed, 0.01f) + distance / std::max(range, 1.0f) * 0.25f;
        if (score < bestScore)
        {
            bestScore = score;
            best = static_cast<int>(i);
        }
    }
    return best;
}

// (3.7.6) An enemy's hit zones for a shot: its body, a capsule (the segment Bottom - Top with Radius around it) made from
// the enemy's whole bounds (a big target), and its crit spot, a ball at Crit (its head) CritRadius across (0: none).
struct HitZone
{
    V3 Bottom, Top;
    float Radius = 0.0f;
    V3 Crit;
    float CritRadius = 0.0f;
};

// Where a ray from `eye` along unit `dir` comes closest to the segment a - b: the distance between them there (`gap`) and
// how far along the ray that is (`along`; at the eye, 0, when the closest point would be behind it).
inline void RayToSegment(V3 eye, V3 dir, V3 a, V3 b, float& gap, float& along)
{
    const V3 u = b - a;
    const V3 w = a - eye;
    const float uu = Dot(u, u), ud = Dot(u, dir), uw = Dot(u, w), dw = Dot(dir, w);
    float s = 0.0f;
    const float denominator = uu - ud * ud;   // (|dir| = 1)
    if (uu > 1e-6f) { s = denominator > 1e-6f ? (dw * ud - uw) / denominator : -uw / uu; }
    s = std::clamp(s, 0.0f, 1.0f);
    float t = s * ud + dw;
    if (t < 0.0f)
    {
        t = 0.0f;
        s = uu > 1e-6f ? std::clamp(-uw / uu, 0.0f, 1.0f) : 0.0f;
    }
    gap = Length(eye + dir * t - (a + u * s));
    along = t;
}

// The result of a shot's pick: the zone it goes to (-1: none) and whether it goes through that zone's crit spot.
struct Picked
{
    int Index = -1;
    bool Crit = false;
};

// (3.7.6) The target a shot goes to: of `zones`, the nearest body the line of sight from `eye` along unit `dir` goes
// through, else the body whose edge it passes within `assist` degrees of (the nearest in angle), in front of the eye and
// within `range`; and whether the line goes through that one's crit spot.
inline Picked PickZone(V3 eye, V3 dir, const std::vector<HitZone>& zones, float assist, float range)
{
    constexpr float Deg = 180.0f / 3.14159265f;
    Picked best;
    float bestScore = 1e30f;
    for (size_t i = 0; i < zones.size(); ++i)
    {
        const HitZone& z = zones[i];
        float gap = 0.0f, along = 0.0f;
        RayToSegment(eye, dir, z.Bottom, z.Top, gap, along);
        if (!(along > 1.0f) || along > range) { continue; }
        const bool through = gap <= z.Radius;
        const float angle = std::atan2(std::max(0.0f, gap - z.Radius), along) * Deg;
        if (!through && angle > assist) { continue; }
        const float score = through ? along : 1e9f + angle * 1e5f + along;
        if (score >= bestScore) { continue; }
        bestScore = score;
        best.Index = static_cast<int>(i);
        best.Crit = false;
        if (z.CritRadius > 0.0f)
        {
            const float t = Dot(z.Crit - eye, dir);
            best.Crit = t > 0.0f && Length(z.Crit - (eye + dir * t)) <= z.CritRadius;
        }
    }
    return best;
}

// ---- the settings ----
// (3.7.4) an upgrade of a gun: a key item of the game's (a part bought at a shop) whose count, up to the upgrade's levels, is
// its level; read when the shooter comes on (each battle)
struct Upgrade
{
    std::wstring Item;                     // the item: an Item row's name (like "key_dirge_cerberus_power")
    int Id = 0;                            // its UniqueId (0: none), for a count function of the game's that takes ids
    std::wstring Row;                      // its tag in the bullet row's name: <damage_source>_<tag><level><tag><level>... (empty: none)
    int Levels = 0;                        // how many levels (0: as many as its lists have)
    std::vector<float> Interval, Reload, Range;   // the time between shots, the reload time and the reach: times these at levels 1, 2...
    std::vector<int> Clip;                 // rounds added at levels 1, 2...
    int MaxLevel() const
    {
        size_t n = static_cast<size_t>(std::max(0, Levels));
        for (const auto* list : {&Interval, &Reload, &Range}) { n = std::max(n, list->size()); }
        return static_cast<int>(std::min<size_t>(std::max(n, Clip.size()), 99));
    }
};

struct Weapon
{
    std::wstring Name = L"CERBERUS";
    std::wstring Set = L"m001_h";                          // its Dirge of Cerberus motions (p000_ + m001_h + _st_a + _remap)
    std::wstring DamageSource = L"EB2020_03_AtkShot_Renkei";   // a row of the game's damage table, made at the target
    std::wstring Ability = L"PC0000_NAtk_1";               // the ability the damage counts as (the character's normal attack)
    int Clip = 6;                                          // shots before it reloads (the ammo itself never runs out)
    float Interval = 0.22f;                                // seconds between shots
    bool Automatic = false;                                // holding the fire button keeps firing
    float Reload = 1.3f;                                   // seconds a reload takes
    float Spread = 0.4f;                                   // degrees a shot may stray
    float Recoil = 2.0f;                                   // degrees the aim kicks up with each shot
    float Range = 8000.0f;                                 // cm
    float FireAt = 0.6f;                                   // how far the fire trigger is pulled when it fires (0 to 1)
    float AimFov = 0.0f;                                   // (0: the shooter's) the view while aiming
    FormEffect Muzzle;                                     // at the gun's muzzle
    FormEffect Impact;                                     // where a shot that hits no one lands (empty: none)
    std::vector<FormSound> Sounds;                         // the gunshot: sounds played together (3.7.1: slices of Vincent's
                                                           // shot in the cutscene EV_FOREE_0630)
    FormSound ReloadSound;
    std::wstring Reticle = L"reticle_cross";               // its reticle: <ui folder>/<this>.png (Dirge of Cerberus' own sprites)
    TriggerEffect FireTrigger = WeaponTrigger(4, 6, 6);    // the fire trigger, ready
    TriggerEffect Kick = VibrationTrigger(3, 8, 35);       // ... for a moment after each shot
    float KickSeconds = 0.06f;
    std::vector<Upgrade> Upgrades;                         // (3.7.4) parts that make it stronger
    std::wstring FlySet;                                   // (3.7.7) its motions while the character flies ("m004_hf":
                                                           // p007_ + m004_hf + _st_f + _remap); empty: the ones on the ground
};

// (3.7.4) A gun with its upgrades at the levels owned (each clamped to its upgrade's levels; `owned` in the order of its
// Upgrades, -1 or missing: 0). Its DamageSource becomes <damage_source>_<tag><level>... for the upgrades with a row tag, when
// one of them is above level 0. `levels` gets the levels used.
inline Weapon Upgraded(const Weapon& base, const std::vector<int>& owned, std::vector<int>* levels = nullptr)
{
    Weapon w = base;
    std::wstring tags;
    bool tagged = false;
    std::vector<int> used;
    for (size_t k = 0; k < base.Upgrades.size(); ++k)
    {
        const Upgrade& u = base.Upgrades[k];
        const int level = std::clamp(k < owned.size() ? owned[k] : 0, 0, u.MaxLevel());
        used.push_back(level);
        if (!u.Row.empty())
        {
            tags += u.Row + std::to_wstring(level);
            tagged = tagged || level > 0;
        }
        if (level <= 0) { continue; }
        const auto at = [level](const auto& list) { return list[static_cast<size_t>(std::min(level, static_cast<int>(list.size())) - 1)]; };
        if (!u.Interval.empty()) { w.Interval = std::max(0.02f, w.Interval * at(u.Interval)); }
        if (!u.Reload.empty()) { w.Reload = std::max(0.0f, w.Reload * at(u.Reload)); }
        if (!u.Range.empty()) { w.Range = std::clamp(w.Range * at(u.Range), 100.0f, 1000000.0f); }
        if (!u.Clip.empty()) { w.Clip = std::clamp(w.Clip + at(u.Clip), 1, 999); }
    }
    if (tagged) { w.DamageSource = base.DamageSource + L"_" + tags; }
    if (levels) { *levels = std::move(used); }
    return w;
}

struct Settings
{
    bool On = false;
    bool InField = false;                     // also outside battle
    std::wstring Controls = L"triggers";      // "triggers": R2 fire, L2 aim, R1 reload, L1 switch; "dirge": R1 fire, L1 aim, R2 reload, L2 switch
    Button Fire = Button::R2, Aim = Button::L2, Reload = Button::R1, Switch = Button::L1, Zoom = Button::R3;
    uint32_t Block = Bit(Button::L1) | Bit(Button::R1) | Bit(Button::L2) | Bit(Button::R2) | Bit(Button::R3);
    bool Triggers = true;                     // a DualSense's adaptive triggers
    TriggerEffect AimTrigger = FeedbackTrigger(2, 2);
    float Assist = 2.5f;                      // degrees of aim assist
    // the camera
    float Distance = 250.0f, Side = 55.0f, Height = 20.0f;           // behind, right of and above the pivot (cm)
    float AimDistance = 130.0f, AimSide = 50.0f, AimHeight = 12.0f;  // while aiming
    float Pivot = 60.0f;                      // cm above the character's location (the middle of its capsule) the camera turns about
    float Fov = 0.0f, AimFov = 55.0f, ZoomFov = 25.0f;               // degrees (Fov 0: the game's)
    float CameraBlend = 0.2f;                 // s between the shoulder and the aim
    // abilities the shooter's camera stays on through (a normal attack, a dodge); while any other runs (a spell, a limit
    // break, a summon) the game's camera has the view
    std::vector<std::wstring> CameraAbilities = {L"*NAtk*", L"*Avoid*", L"*Dodge*", L"*Guard*"};
    float YawSpeed = 240.0f, PitchSpeed = 170.0f;                    // degrees a second at the stick's edge
    float AimScale = 0.55f, ZoomScale = 0.3f, Mouse = 1.0f;
    bool InvertY = false;
    float PitchMin = -70.0f, PitchMax = 75.0f;
    // the reticle
    float ReticleSize = 12.0f, ReticleGap = 5.0f, ReticleThickness = 2.0f;
    float ReticleColor[4] = {1.0f, 1.0f, 1.0f, 0.9f}, EnemyColor[4] = {1.0f, 0.25f, 0.2f, 1.0f}, HitColor[4] = {1.0f, 0.85f, 0.3f, 1.0f};
    float HitSeconds = 0.15f;
    // (3.7.6) the shot's targets: each enemy's body zone, its bounds times HitScale (1: its whole size), and its crit spot
    // (its head bone, else the top of its bounds), a shot through which is a critical hit: CritHits bullets
    float HitScale = 1.0f;
    bool Crit = true;
    int CritHits = 2;
    float CritScale = 1.0f;
    float CritColor[4] = {1.0f, 0.3f, 0.15f, 1.0f};
    bool Ammo = true;
    std::wstring Ui = L"dirge_ui";            // the HUD's pictures: PNG files in this folder of the mod (Dirge of Cerberus' sprites)
    float HudScale = 1.0f;                    // the reticle and the bullet counter's size
    float ReticleScale = 0.55f;               // the reticle's size on screen (of its picture's)
    // the motions
    bool Motions = true;                      // the Dirge of Cerberus motions over the game's pose
    std::wstring Folder = L"/Game/RebirthSkelCompat/Dirge/Vincent";   // (the motions made cookable: VincentDirgeMotions_P)
    std::wstring Slot = L"DefaultSlot";       // the slot its aim, shot and reload motions play in
    std::wstring Prefix = L"p000_", Suffix = L"_remap";
    std::wstring Idle = L"st_a", Walk = L"wk_a", Run = L"rn_a", Back = L"brn_a", Left = L"lrn_a", Right = L"rrn_a", Shot = L"st_f",
                 Reloading = L"st_rd", Switching = L"swtch";
    std::wstring Stand = L"st";               // (3.7.1) the stance standing still, not aiming (Idle: aiming)
    std::wstring Walking = L"wk", Running = L"rn";            // (3.7.1) walking and running, not aiming (Walk, Run...: aiming)
    std::wstring WalkReload = L"wk_rd", RunReload = L"rn_rd";  // (3.7.1) reloading on the move
    float WalkSpeed = 160.0f, RunSpeed = 500.0f;
    float PoseBlend = 0.15f;                  // s the shooter's pose takes to come and go
    bool TurnActor = true;                    // the character turns where it aims while it stands aiming or shooting
    // (3.7.3) aiming, the game sees its guard button held: the character guard-walks (the game's strafing walk, its
    // B_StrafingWalk01 / B_Walk[F|B|L|R]01 animations, played by the way it moves against the way it faces) while it turns
    // where it aims, and stands in its guard (B_Guard01). The row's "moves" can make those Dirge of Cerberus' aim-runs and
    // aim stance. Not while a face button is held (the guard button and a face button make a synergy skill).
    bool Strafe = true;
    Button StrafeButton = Button::R1;         // the game's guard button
    std::vector<std::wstring> GuardAbilities = {L"*Guard*"};   // abilities that are the guard: the shots go on through them
    std::wstring GunSocket = L"Attach_Weapon_Right01";   // (3.7.1) its gun is kept on this socket of its model while it is on (empty: where the game puts it)
    std::vector<std::wstring> Spine = {L"C_Spine_b", L"C_Spine_c", L"C_Spine_d"};
    std::vector<float> Share = {0.25f, 0.35f, 0.40f};
    float MaxAim = 80.0f;                     // degrees the upper body turns at most
    std::wstring UpperBody = L"C_Spine_b";    // fire and reload motions play from this bone up
    std::vector<std::wstring> Keep = {L"*_Phy*", L"*Kdi*", L"*_Spo*", L"*_End*"};   // bones the game's pose keeps (physics, helpers; a bone the hierarchy fix renamed too)
    std::vector<std::wstring> KeepUnder = {L"C_FaceBase_a"};                    // ... with everything under them (the face)
    std::vector<Weapon> Weapons;              // (none given: Cerberus, Hydra and Griffon)
    // (3.7.7) a form's shooter: another gun model in hand while it is on ("gun_mesh": a skeletal mesh on the gun's skeleton or
    // one of its family: Chaos's Death Penalty), and flying: the stance it holds in the air ("fly_stance", a motion's whole
    // name without the gun's set: "m004_cf_st_a"; each gun's shot and reload while it flies are its "fly_set"'s)
    std::wstring GunMesh;
    std::wstring FlyStance;

    std::wstring Clip(const Weapon& w, const std::wstring& motion) const
    {
        if (motion.empty()) { return {}; }
        const std::wstring name = Prefix + w.Set + L"_" + motion + Suffix;
        return Folder + L"/" + name + L"." + name;
    }
    // (3.7.7) a motion of a gun in the air (its fly set's; none: the one on the ground)
    std::wstring FlyClip(const Weapon& w, const std::wstring& motion) const
    {
        if (motion.empty()) { return {}; }
        if (w.FlySet.empty()) { return Clip(w, motion); }
        const std::wstring name = Prefix + w.FlySet + L"_" + motion + Suffix;
        return Folder + L"/" + name + L"." + name;
    }
    // (3.7.7) a motion by its whole name (no gun's set in it)
    std::wstring Plain(const std::wstring& motion) const
    {
        if (motion.empty()) { return {}; }
        const std::wstring name = Prefix + motion + Suffix;
        return Folder + L"/" + name + L"." + name;
    }
};

// The buttons of a controls preset.
inline bool ApplyPreset(Settings& s, std::wstring_view preset)
{
    if (NameEquals(preset, L"triggers") || NameEquals(preset, L"default"))
    {
        s.Fire = Button::R2; s.Aim = Button::L2; s.Reload = Button::R1; s.Switch = Button::L1; s.Zoom = Button::R3;
    }
    else if (NameEquals(preset, L"dirge") || NameEquals(preset, L"dirge of cerberus") || NameEquals(preset, L"doc"))
    {
        s.Fire = Button::R1; s.Aim = Button::L1; s.Reload = Button::R2; s.Switch = Button::L2; s.Zoom = Button::R3;
    }
    else { return false; }
    s.Controls = std::wstring(preset);
    s.Block = Bit(s.Fire) | Bit(s.Aim) | Bit(s.Reload) | Bit(s.Switch) | Bit(s.Zoom);
    return true;
}

// Vincent's own gunshot: the cutscene EV_FOREE_0630 (he fires through a scope; its muzzle flash is at frame 320) has it
// in two of its sound tracks, EV_FOREE_0630_01 (from frame 0: the shot 10.59 s in) and EV_FOREE_0630_0319f (from frame
// 319: the shot 0.035 s in). A gun plays a slice of each (`ring`, `burst`: how long each plays).
inline std::vector<FormSound> VincentShot(float ring, float burst)
{
    FormSound bang;
    bang.Bank = L"/Game/Sound/SE/Cut/8800-FOREE/EV_FOREE_0630/EV_FOREE_0630_01.EV_FOREE_0630_01";
    bang.Cue = L"EV_FOREE_0630_01";
    bang.Start = 10.59f;
    bang.Length = ring;
    bang.Volume = 0.8f;
    FormSound blast;
    blast.Bank = L"/Game/Sound/SE/Cut/8800-FOREE/EV_FOREE_0630/EV_FOREE_0630_0319f.EV_FOREE_0630_0319f";
    blast.Cue = L"EV_FOREE_0630_0319f";
    blast.Start = 0.035f;
    blast.Length = burst;
    blast.Volume = 0.6f;
    return {bang, blast};
}

// Dirge of Cerberus' three guns (the motions of each: handgun m001_h, machine gun m002_m, rifle m003_r), with a muzzle
// flash of the game's (a pistol's) and Vincent's gunshot. Each fires a bullet row that starts at the gun's VFX_Muzzle01
// (the Quicksilver's muzzle socket; the row's "CreateBasePos" 1: the weapon).
inline std::vector<Weapon> DefaultWeapons()
{
    FormEffect muzzle;
    muzzle.Path = L"/Game/Effect/Character/Weapon/WE1003_01_CorneoLackey_Pistol/Particle/FX_WE1003_01_Muzzle_01.FX_WE1003_01_Muzzle_01";
    muzzle.Socket = L"VFX_Muzzle01";
    muzzle.Seconds = 0.15f;
    Weapon cerberus;
    cerberus.Muzzle = muzzle;
    cerberus.Sounds = VincentShot(0.9f, 0.45f);
    Weapon hydra = cerberus;
    hydra.Name = L"HYDRA";
    hydra.Reticle = L"reticle_round";
    hydra.Set = L"m002_m";
    hydra.DamageSource = L"EB2020_00_AtkShot01_Bullet";   // (3.7.1: Barret's PC0001_NAtk_1_01 starts at VFX_Muzzle02, which the gun lacks)
    hydra.Sounds = VincentShot(0.32f, 0.12f);
    hydra.Clip = 30;
    hydra.Interval = 0.1f;
    hydra.Automatic = true;
    hydra.Reload = 1.8f;
    hydra.Spread = 1.2f;
    hydra.Recoil = 0.6f;
    hydra.FireAt = 0.4f;
    hydra.FireTrigger = FeedbackTrigger(3, 3);
    hydra.Kick = VibrationTrigger(3, 6, 60);
    hydra.KickSeconds = 0.08f;
    Weapon griffon = cerberus;
    griffon.Name = L"GRIFFON";
    griffon.Reticle = L"reticle_ornate";
    griffon.Set = L"m003_r";
    griffon.DamageSource = L"EB2020_03_AtkFollowShot_Renkei";
    griffon.Sounds = VincentShot(1.2f, 0.55f);
    griffon.Clip = 5;
    griffon.Interval = 0.9f;
    griffon.Reload = 2.0f;
    griffon.Spread = 0.1f;
    griffon.Recoil = 5.0f;
    griffon.FireAt = 0.7f;
    griffon.AimFov = 35.0f;
    griffon.FireTrigger = WeaponTrigger(5, 8, 8);
    griffon.Kick = VibrationTrigger(2, 8, 25);
    griffon.KickSeconds = 0.12f;
    return {cerberus, hydra, griffon};
}

// (3.7.1) The motion that goes with how the character moves: standing still, its stance (aiming: the aim stance);
// moving, its walk or run (aiming: by the way it moves against the way it faces, forward, back, left or right). `rate`:
// how fast it plays to keep up with the speed. Empty: none (the game's own).
inline std::wstring LocomotionFor(const Settings& s, bool aiming, float speed, float moveYaw, float faceYaw, float& rate)
{
    rate = 1.0f;
    if (!(speed >= 60.0f)) { return aiming ? s.Idle : s.Stand; }
    const bool run = speed >= 0.5f * (s.WalkSpeed + s.RunSpeed);
    rate = std::clamp(speed / std::max(1.0f, run ? s.RunSpeed : s.WalkSpeed), 0.6f, 1.5f);
    if (!aiming) { return run ? s.Running : s.Walking; }
    float d = std::fmod(moveYaw - faceYaw, 360.0f);
    if (d > 180.0f) { d -= 360.0f; }
    if (d < -180.0f) { d += 360.0f; }
    if (std::fabs(d) <= 50.0f) { return run ? s.Run : s.Walk; }
    if (std::fabs(d) >= 130.0f) { return s.Back; }
    return d > 0.0f ? s.Right : s.Left;   // (a yaw grows turning right)
}

// (3.7.1) The reload motion for how fast the character moves.
inline const std::wstring& ReloadFor(const Settings& s, float speed)
{
    if (!(speed >= 60.0f)) { return s.Reloading; }
    return speed >= 0.5f * (s.WalkSpeed + s.RunSpeed) ? s.RunReload : s.WalkReload;
}

// A bone name against Keep's patterns ("*_Phy": ends with, "C_Hair*": starts with, "*Kdi*": has, else the whole name).
inline bool BoneMatches(std::wstring_view bone, const std::vector<std::wstring>& patterns)
{
    const std::wstring b = FoldedKey(bone);
    for (const auto& raw : patterns)
    {
        const std::wstring p = FoldedKey(raw);
        if (p.empty()) { continue; }
        const bool head = p.front() == L'*', tail = p.size() > 1 && p.back() == L'*';
        const std::wstring core = p.substr(head ? 1 : 0, p.size() - (head ? 1 : 0) - (tail ? 1 : 0));
        if (core.empty()) { continue; }
        if (head && tail) { if (b.find(core) != std::wstring::npos) { return true; } }
        else if (head) { if (b.size() >= core.size() && b.compare(b.size() - core.size(), core.size(), core) == 0) { return true; } }
        else if (tail) { if (b.compare(0, core.size(), core) == 0) { return true; } }
        else if (b == core) { return true; }
    }
    return false;
}
} // namespace Shooter

// (3.12.2) One of the game's special state effects (its BattleSpecialStateEffect table: effects the game keeps on a
// character at the sockets the row names while the state is on; the boss Sephiroth's feelers on his sword and his wing
// are BossSephiroth_FeelerSword and BossSephiroth_FeelerWing), on the character while it is in a form in battle.
struct FormStateEffect
{
    std::wstring Name;    // the table's row
    std::wstring Needs;   // a socket or bone the character's model must have for it ("needs"; empty: none): the wing's bone
};

inline constexpr size_t MaxFormStateEffects = 8;
inline constexpr size_t MaxFormWatchedDamage = 16;

struct Form
{
    std::wstring Name;                // on the menu
    std::wstring Pack;                // its animation pack ("Battle02"); empty or Battle00: the character's own
    std::vector<std::wstring> Show;   // the parts ("parts": material slots) shown in this form; the others are hidden
    std::wstring Model;               // the skeletal mesh worn in this form (empty: the character's own)
    std::wstring AnimClass;           // the AnimBlueprint (class) the model runs in this form; needed for a model on another
                                      // skeleton (the model's own; empty: the character's)
    bool AsLook = false;              // (3.7.8) "as_look": the model goes on the game's way (its look change, as a model with an
                                      // AnimBlueprint of its own does) even with the character's own AnimBlueprint: the game sets
                                      // up its physics and bone tables for it (a model whose bones are not in the order of the
                                      // character's own needs that)
    float Scale = 0.0f;               // the model's size in this form (0: the character's own)
    std::vector<FormMesh> Meshes;     // model parts added in this form
    bool HideWeapon = false;          // the character's weapons are hidden in this form
    std::wstring Weapon;              // (3.8.2) "weapon": the weapon this form fights with, a weapon blueprint (its class:
                                      // "/Game/BluePrint/Character/Weapon/WE1021_00_SephirothIllusion_Masamune.WE1021_00_..._C"; the
                                      // asset's path gets _C): spawned and put in the character's weapon slot the game's way
                                      // (EndSceneAPI AttachWeapon) in place of its own, which comes back when it leaves the form
    std::vector<FormEffect> Effects;  // played on the character as it switches to this form
    std::vector<FormEffect> Keep;     // played for as long as it is in this form (an aura, a sword of light)
    std::vector<FormStateEffect> States;   // (3.12.2) "state_effects": the game's special state effects on it in battle
    std::vector<std::wstring> WatchDamage; // (3.12.2) "watch_damage": damage source rows the log counts as its abilities run
    std::vector<FormSound> Sounds;
    FormFlight Fly;
    std::wstring After;               // it switches to this form by itself when this ability ends (a limit break)
    std::vector<FormAbilityEffects> AbilityEffects; // effects while some abilities run in this form
    bool SuperArmor = false;          // hits do not make the character flinch or stagger in this form (its hit reactions are off)
    float Seconds = 0.0f;             // the form lasts this long (game time: pauses and the command menu's slow time stretch it),
                                      // then the character turns back by itself (0: for as long as you like)
    float Cooldown = 0.0f;            // once the character leaves the form (its time up or switched away), it can be chosen
                                      // again only this much later
    std::wstring RevertTo;            // the form it turns back into when its time is up or it is knocked out (empty: the normal one)
    int RevertIndex = 0;              // (RevertTo's place in the list, found once the list is read)
    FormEntrance Entrance;            // (3.6.6) played as the character switches to it
    FormCamera Camera;                // (3.6.16) the battle camera in this form
    std::vector<FormAbilityCamera> AbilityCameras; // (3.6.16) the camera while some abilities run in it
    int Shooting = -1;                // (3.7) "shooter": the character's shooter in this form (-1: the row's; 0 off, 1 on)
    // (3.7.7) "shooter": {...}: the form's own shooter, the character's with these settings over it (its motions, guns, gun
    // model, camera, flying); made once the rows for the character are joined (the shooter and the forms may come from
    // different rows)
    std::shared_ptr<Json> ShooterJson;
    std::shared_ptr<Shooter::Settings> ShooterSet;
    // (3.7.5) "sets": {"Battle00": "Battle07", "Battle01": "Battle08"}: while the character is in this form, the game's
    // lookups of a set of the name on the left (its default pack's, Punisher mode's, its face's) get the set of the name
    // on the right (one of the row's sets: a beast's own walks, guard and face)
    std::vector<std::pair<std::wstring, std::wstring>> Sets;
    Voice Speaks;                     // (3.9.0) "voice": the voice its lines play in, in this form (unset: the row's)
    std::wstring WeaponSocket;        // (3.16.1) a "movesets" entry's "weapon_socket": in battle the weapon in the character's
                                      // hands sits on this socket of its model while a form plays the moveset (CLOUD's:
                                      // "Attach_Weapon_Right01", Cloud's sword hand; Sephiroth's rules put it in his left)
    bool Limited() const { return Seconds > 0.0f; }
};

inline constexpr size_t MaxFormSets = 8;   // (3.7.5) "sets" of one form

struct FormSettings
{
    std::vector<Form> List;                            // [0]: the normal form
    std::wstring Button = L"Gamepad_FaceButton_Top";   // held to open the menu (an input key name)
    std::wstring Key;                                  // a keyboard key that opens it too ("T"; empty: none)
    float HoldSeconds = 0.35f;                         // held this long, the menu opens (a tap stays the game's)
    std::wstring Title = L"FORMS";                     // the menu's heading
    std::vector<std::wstring> Parts;                   // material slots the forms show or hide (each form's "show")
    float FadeSeconds = 0.0f;                          // parts fade in and out this long (0: at once)
    std::wstring FadeParameter = L"NativePrimitiveCoverage"; // the parts' materials' scalar that fades them (1: shown)
    std::vector<FormEffect> ShowEffects;               // played as parts come out
    std::vector<FormEffect> HideEffects;               // played as parts go
    float EffectSeconds = 2.5f;                        // how long switch effects play (an effect can set its own)
    bool HideOnOthers = true;                          // other copies of the character's model (cutscenes, menus) keep the parts hidden
    bool Timer = true;                                 // a timed form's time left is on screen in battle
    float TimerX = 0.97f, TimerY = 0.55f;              // where (fractions of the screen; right of the middle: its right edge there)
    // (3.15.1) "movesets": [{"name": "CLOUD", "pack": "Battle11"}]: movesets the MOVESET page offers besides the forms'
    // (another character's motions built for this one), each its pack's set; not forms (not on the forms menu, never worn):
    // only Name and Pack are used
    std::vector<Form> Movesets;
    bool HasList() const { return List.size() >= 2; }

    // The form playing pack `pack` (the first that names it; Battle00 or none: the normal form), or -1.
    int IndexOfPack(std::wstring_view pack) const
    {
        const bool own = pack.empty() || NameEquals(pack, DefaultAbilityPack());
        for (size_t k = 0; k < List.size(); ++k)
        {
            const std::wstring& p = List[k].Pack;
            if (own ? (p.empty() || NameEquals(p, DefaultAbilityPack())) : NameEquals(p, pack)) { return static_cast<int>(k); }
        }
        return own && !List.empty() ? 0 : -1;
    }
    // (3.7.7) Form `k` plays pack `pack` (Battle00 or none: the character's own): a switch to that pack leaves it in that form
    // (a form on the character's own pack, like the normal form, is not the normal form when the game goes back to its pack).
    bool Plays(int k, std::wstring_view pack) const
    {
        if (k < 0 || static_cast<size_t>(k) >= List.size()) { return false; }
        const std::wstring& p = List[static_cast<size_t>(k)].Pack;
        const bool own = pack.empty() || NameEquals(pack, DefaultAbilityPack());
        return own ? (p.empty() || NameEquals(p, DefaultAbilityPack())) : NameEquals(p, pack);
    }
};

// 3.8.1: a socket stand-in's scale with "hidden": true. 1/1000 puts what is attached there out of sight (a weapon at the
// chest bone shrinks to a speck inside the body) without the zero scale whose transform cannot be inverted.
inline constexpr float HiddenSocketScale = 0.001f;

// 3.8.1: a socket stand-in's own placement on its bone, over what it copies: "location" [x, y, z] (cm), "rotation"
// [pitch, yaw, roll] (degrees, as the editor shows a socket's), "scale" (a number or [x, y, z]; "hidden": true is
// HiddenSocketScale).
struct SocketPlacement
{
    bool HasLocation = false, HasRotation = false, HasScale = false;
    std::array<float, 3> Location{0.0f, 0.0f, 0.0f};
    std::array<float, 3> Rotation{0.0f, 0.0f, 0.0f};    // pitch, yaw, roll (FRotator order)
    std::array<float, 3> Scale{1.0f, 1.0f, 1.0f};
    bool Any() const { return HasLocation || HasRotation || HasScale; }
    bool Hidden() const { return HasScale && Scale[0] <= HiddenSocketScale && Scale[1] <= HiddenSocketScale && Scale[2] <= HiddenSocketScale; }
};

// 3.9.3 "ability_pages": the game takes 5 commands from a player row, so a pack's "commands" go on pages of 5; while the
// battle command menu is open (the game's time slowed) two buttons turn the page, KH3-style (L1 / R1 by default; the game
// does not see them then). true / false, or {"previous": "L1", "next": "R1", "refresh": "now", "x": 90, "y": -430}:
// "refresh" "now" has the game rebuild the member's lists at once (the open list shows the page), "close" only once the
// menu closes; "x" / "y" place the page's label (from the screen's bottom left).
struct AbilityPagesSettings
{
    bool On = true;
    bool Set = false;                               // given in the row
    Shooter::Button Previous = Shooter::Button::L1;
    Shooter::Button Next = Shooter::Button::R1;
    bool RefreshNow = true;
    float X = 90.0f, Y = -430.0f;
};

// The input key of a button for the game's input ("Gamepad_LeftShoulder"); empty when it has none.
inline std::wstring ButtonKey(Shooter::Button b)
{
    for (const auto& info : Shooter::Buttons())
    {
        if (info.Id == b) { return info.Key; }
    }
    return {};
}

inline std::wstring ButtonLabelOf(Shooter::Button b)
{
    for (const auto& info : Shooter::Buttons())
    {
        if (info.Id == b) { return info.Label; }
    }
    return L"?";
}

struct AnimSetRow
{
    std::vector<std::wstring> Characters;  // CharaSpec pack object paths (one per row after FinishConfig)
    std::vector<SetSource> Battle;         // sources of the Battle* sets, in order of preference
    std::vector<SetSource> Field;          // sources of every other set
    std::vector<std::wstring> Sets;        // set names to build besides the standard ones
    std::vector<AnimMove> Moves;
    std::wstring FieldActions;             // AnimationSetParentFolder the character's CharaSpec row should use (field actions)
    std::wstring CutsceneWeaponSocket;     // 3.6.16 "cutscene_weapon_socket": the socket of its mesh its weapons go to while it
                                           // plays a cutscene (its anim instance's bPlayingCutScene); empty: the game's
    std::wstring Skeleton;                 // the character's own skeleton ("skeleton"), whose meshes get Sockets
    std::wstring AnimBlueprintsFrom;       // 3.8 "anim_blueprints_from": the skeleton the slot's AnimBlueprints were made for (the
                                           // slot owner's); they run on meshes of Skeleton (nothing else moves)
    std::wstring LooksFrom;                // 3.9.1 "looks_from": a character blueprint's class whose looks (ChangeAppearanceSettings:
                                           // the Toad status's frog) the character gets when its own blueprint has none
    std::vector<std::pair<std::wstring, std::wstring>> Sockets; // 3.2: socket the game asks for -> socket or bone of this
                                                                // character that stands in for it (weapon in hand, ...)
    std::vector<std::pair<std::wstring, SocketPlacement>> SocketPlacements; // 3.8.1: a stand-in's own "location", "rotation",
                                                                             // "scale" ("hidden": shrunk out of sight, e.g. a weapon
                                                                             // put away by a character that carries none outside battle)
    bool KeepProportions = false;          // 3.2 "proportions": the pairs and families of Skeleton keep every body's proportions
    bool Override = false;                 // 3.2 "override": joined before the other rows of its character (its sources, moves,
                                           // field actions and sockets win), e.g. a test file over a mod's own row
    std::wstring Player;                   // 3.3 "player": the character's BattlePlayerParameter row ("pt_Cloud")
    std::vector<PackAbilities> Abilities;  // 3.3 "abilities": commands and limits per primary animation pack
    bool RefreshAbilities = true;          // 3.3 "refresh_abilities": after a switch the mod has the game recalculate the
                                           // party member's status, which rebuilds its ability lists; false: they show
                                           // when the game next does
    AbilityPagesSettings Pages;            // 3.9.3 "ability_pages": a pack's commands 5 at a time, L1 / R1 in the battle menu
    std::vector<std::wstring> PackAssets;  // 3.3.1 "pack_assets": objects added to the character's CharaSpec pack (another
                                           // character's effect pack, a sound bank): loaded at the first map load, each goes
                                           // into the pack entry that lists an object of its class
    std::vector<std::wstring> Preload;     // 3.3 "preload": objects loaded and kept at the first map load (a CharaSpec pack a
                                           // damage source spawns, ...)
    FormSettings Forms;                    // 3.6 "forms": the forms it changes into in battle (the forms menu)
    Voice Speaks;                          // 3.9.0 "voice": the voice its lines play in (every form's, and in the field)
    int Skin = -1;                         // 3.10.0: the skin its character wears (an index into Config::Skins; -1: its own model)
    Voice SkinSpeaks;                      // 3.10.0: that skin's "voice" (unset: the skin has none of its own)
    Voice ChosenSpeaks;                    // 3.11.1: the voice chosen for it on the Customization screen (VOICES; unset: none)
    std::wstring ChosenWeapon;             // 3.12.0: the weapon chosen for it on the Customization screen (WEAPONS): a weapon
                                           // blueprint class, "-" its own weapon (also under a skin that has one); empty:
                                           // none chosen (its skin's weapon, else its own)
    std::wstring ChosenCombo;              // 3.12.0: the combo chosen for it on the Customization screen (COMBO): the name of
                                           // the form whose Square chain (B_NAttack*) every form on its own AnimBlueprint
                                           // plays; empty: each form its own. (3.14.6: no longer used: FormCombos)
    std::vector<std::pair<std::wstring, std::wstring>> FormCombos;   // 3.14.6: the combos chosen on the COMBO page, a form
                                           // at a time: (a form's name, the form whose Square chain it plays); a form
                                           // not listed plays its own
    bool SkinOnly = false;                 // 3.10.0: a row made for a skin (its character has no row of its own: no sets are
                                           // built for it and it has no forms menu)
    Shooter::Settings Shooting;            // 3.7 "shooter": it fights as a third-person shooter (Dirge of Cerberus)
    std::vector<std::wstring> RequiresPaks;
    std::wstring Origin;

    // (3.9.0) The voice of form `form` (-1: outside battle): (3.11.1) the one chosen on the Customization screen (in every
    // form: the player's choice; 3.11.2: `chosen` false while the game has not loaded it), else the form's own "voice",
    // else (3.10.0) the voice of the skin the character wears, else the row's.
    const Voice& VoiceOf(int form, bool chosen = true) const
    {
        if (chosen && ChosenSpeaks.Set) { return ChosenSpeaks; }
        if (form >= 0 && static_cast<size_t>(form) < Forms.List.size() && Forms.List[static_cast<size_t>(form)].Speaks.Set)
        {
            return Forms.List[static_cast<size_t>(form)].Speaks;
        }
        if (SkinSpeaks.Set) { return SkinSpeaks; }
        return Speaks;
    }
    // (3.9.0) The banks its row and forms switch to (never replaced themselves).
    std::vector<std::wstring> VoiceTargets() const
    {
        std::vector<std::wstring> out;
        const auto add = [&](const Voice& v) {
            if (v.Set && !v.Own && std::none_of(out.begin(), out.end(), [&](const std::wstring& b) { return PathEquals(b, v.Bank); })) { out.push_back(v.Bank); }
        };
        add(Speaks);
        add(SkinSpeaks);   // (3.10.0)
        add(ChosenSpeaks);   // (3.11.1)
        for (const auto& f : Forms.List) { add(f.Speaks); }
        return out;
    }
    bool HasVoices() const
    {
        return Speaks.Set || SkinSpeaks.Set || ChosenSpeaks.Set || std::any_of(Forms.List.begin(), Forms.List.end(), [](const Form& f) { return f.Speaks.Set; });
    }

    // The abilities for a pack: its own entry, else the default pack's (Battle00), else none.
    const PackAbilities* AbilitiesFor(std::wstring_view pack) const
    {
        const PackAbilities* fallback = nullptr;
        for (const auto& entry : Abilities)
        {
            if (NameEquals(entry.Pack, pack)) { return &entry; }
            if (NameEquals(entry.Pack, DefaultAbilityPack())) { fallback = &entry; }
        }
        return fallback;
    }

    // The command list (`limits` false) or limit list a pack plays with: the pack's own, else the default pack's
    // (Battle00), else null (the table's own list). `from` names the pack the list came from.
    const std::vector<std::wstring>* ListFor(std::wstring_view pack, bool limits, std::wstring* from = nullptr) const
    {
        for (const std::wstring_view name : {pack, std::wstring_view(DefaultAbilityPack())})
        {
            for (const auto& entry : Abilities)
            {
                if (!NameEquals(entry.Pack, name) || !(limits ? entry.HasLimits : entry.HasCommands)) { continue; }
                if (from) { *from = entry.Pack; }
                return limits ? &entry.Limits : &entry.Commands;
            }
        }
        return nullptr;
    }

    // 3.4: the weapon abilities a pack plays with (weapon's ability -> ability): the pack's own, else the default
    // pack's (Battle00), else null (the weapons' own). `from` names the pack the list came from.
    const std::vector<std::pair<std::wstring, std::wstring>>* WeaponsFor(std::wstring_view pack, std::wstring* from = nullptr) const
    {
        for (const std::wstring_view name : {pack, std::wstring_view(DefaultAbilityPack())})
        {
            for (const auto& entry : Abilities)
            {
                if (!NameEquals(entry.Pack, name) || !entry.HasWeapons) { continue; }
                if (from) { *from = entry.Pack; }
                return &entry.Weapons;
            }
        }
        return nullptr;
    }
};

// A data object row or ability name: letters, digits, '_' and '-' only.
inline bool IsRowName(std::wstring_view name)
{
    if (name.empty() || name.size() > 200) { return false; }
    return std::all_of(name.begin(), name.end(), [](wchar_t c) {
        return (c >= L'a' && c <= L'z') || (c >= L'A' && c <= L'Z') || (c >= L'0' && c <= L'9') || c == L'_' || c == L'-';
    });
}

// ---------------------------------------------------------------------------------------
// 3.3: the game's data object tables (EndDataObject, e.g. /Game/DataObject/Resident/BattlePlayerParameter) are frozen
// memory images, used in place. The root holds three arrays and the row hash:
//   +0  elements {ptr, num, max}: TSetElement {FName key, int32 row, int32 next, int32 bucket} (20 bytes)
//   +16 allocation bits, +32 free list, +40 hash {ptr, size}
//   +56 struct definition {ptr, num, max}: {FName field, int32 type} (12 bytes), in row order
//   +72 rows {ptr, num, max}
// A frozen pointer is odd and relative to its own address (address + (value >> 1)); an even one is a plain pointer.
// Rows lay their fields out in definition order with natural alignment; a field whose name ends in "_Array" is an array
// {ptr, num, max} of its type.
// ---------------------------------------------------------------------------------------
namespace Frozen
{
inline uintptr_t Resolve(uintptr_t at, int64_t value)
{
    if (value == 0) { return 0; }
    if (value & 1) { return at + static_cast<uintptr_t>(value >> 1); }
    return static_cast<uintptr_t>(value);
}

// The frozen value that points `at` (where the pointer is stored) to `target`.
inline int64_t Encode(uintptr_t at, uintptr_t target) { return static_cast<int64_t>(target - at) * 2 + 1; }

// Element size and alignment of a field type: 1 bool, 2 uint8, 3 int8, 4 uint16, 5 int16, 6 uint32, 7 int32, 8 int64,
// 9 float, 10 string (TArray<TCHAR>), 11 FName.
inline bool TypeSize(int32_t code, int32_t& size, int32_t& align)
{
    switch (code)
    {
    case 1: case 2: case 3: size = 1; align = 1; return true;
    case 4: case 5: size = 2; align = 2; return true;
    case 6: case 7: case 9: size = 4; align = 4; return true;
    case 8: size = 8; align = 8; return true;
    case 10: size = 16; align = 8; return true;
    case 11: size = 8; align = 4; return true;
    default: return false;
    }
}

struct Field
{
    std::wstring Name;
    int32_t Type = 0;
    bool Array = false;
    int32_t Offset = 0;
};

inline bool EndsWithArray(std::wstring_view name)
{
    constexpr std::wstring_view suffix = L"_Array";
    return name.size() > suffix.size() && NameEquals(name.substr(name.size() - suffix.size()), suffix);
}

// Offsets of the fields (Name, Type filled in) and the row size; false for an unknown type.
inline bool Layout(std::vector<Field>& fields, int32_t& rowSize)
{
    int32_t offset = 0, rowAlign = 1;
    for (auto& field : fields)
    {
        int32_t size = 0, align = 0;
        if (!TypeSize(field.Type, size, align)) { return false; }
        field.Array = EndsWithArray(field.Name);
        if (field.Array) { size = 16; align = 8; }
        offset = (offset + align - 1) / align * align;
        field.Offset = offset;
        offset += size;
        rowAlign = std::max(rowAlign, align);
    }
    rowSize = (offset + rowAlign - 1) / rowAlign * rowAlign;
    return !fields.empty();
}

inline const Field* Find(const std::vector<Field>& fields, std::wstring_view name)
{
    for (const auto& field : fields)
    {
        if (NameEquals(field.Name, name)) { return &field; }
    }
    return nullptr;
}

// The game reads entry `index` of a row's FName array (at `offset` in the row) through a small getter of its own,
// one per index, listed in tables of function pointers:
//   mov rcx,[rcx+8]               the row the handle found
//   cmp dword [rcx+offset+8],index; jg Entry
//   mov rax,[rip+None]; mov [rdx],rax; jmp Done          past the count: None
//   Entry: add rcx,offset; mov rax,[rcx]; test al,1; je M; sar rax,1; add rax,rcx   (the frozen pointer)
//   M: mov rax,[rax+8*index]; mov [rdx],eax; shr rax,32; mov [rdx+4],eax; ...
// True when the `size` bytes at `code` are that getter; `noneDisp` gets where (from `code`) the rel32 of None is.
inline bool IsNameEntryGetter(const uint8_t* code, size_t size, int32_t offset, int32_t index, size_t* noneDisp = nullptr)
{
    if (!code || size < 64 || offset < 0 || offset > 0x7FFFFF00 || index < 0 || index > 15) { return false; }
    size_t at = 0;
    const auto bytes = [&](std::initializer_list<uint8_t> want) {
        for (const uint8_t b : want)
        {
            if (at >= size || code[at] != b) { return false; }
            ++at;
        }
        return true;
    };
    const auto dword = [&](int32_t want) {
        if (at + 4 > size) { return false; }
        int32_t value = 0;
        std::memcpy(&value, code + at, 4);
        at += 4;
        return value == want;
    };
    // A displacement or immediate is one byte below 0x80 (sign-extended), four from there.
    const auto small = [](int32_t value) { return value < 0x80; };
    // mov rcx,[rcx+8]
    if (!bytes({0x48, 0x8B, 0x49, 0x08})) { return false; }
    // cmp dword [rcx+offset+8], index: 83 79 disp8 imm8 / 83 B9 disp32 imm8
    const int32_t count = offset + 8;
    if (small(count) ? !bytes({0x83, 0x79, static_cast<uint8_t>(count)}) : !(bytes({0x83, 0xB9}) && dword(count))) { return false; }
    // jg Entry
    if (!bytes({static_cast<uint8_t>(index), 0x7F}) || at >= size) { return false; }
    const size_t entry = at + 1 + code[at];
    ++at;
    // mov rax,[rip+None]; mov [rdx],rax; jmp Done
    if (!bytes({0x48, 0x8B, 0x05})) { return false; }
    if (noneDisp) { *noneDisp = at; }
    at += 4;
    if (!bytes({0x48, 0x89, 0x02, 0xEB})) { return false; }
    at = entry;
    // add rcx,offset: 48 83 C1 imm8 / 48 81 C1 imm32
    if (small(offset) ? !bytes({0x48, 0x83, 0xC1, static_cast<uint8_t>(offset)}) : !(bytes({0x48, 0x81, 0xC1}) && dword(offset))) { return false; }
    // mov rax,[rcx]; test al,1; je M; sar rax,1; add rax,rcx
    if (!bytes({0x48, 0x8B, 0x01, 0xA8, 0x01, 0x74, 0x06, 0x48, 0xD1, 0xF8, 0x48, 0x03, 0xC1})) { return false; }
    // M: mov rax,[rax+8*index]: 48 8B 00 / 48 8B 40 disp8 / 48 8B 80 disp32
    const int32_t element = index * 8;
    if (element == 0) { if (!bytes({0x48, 0x8B, 0x00})) { return false; } }
    else if (small(element) ? !bytes({0x48, 0x8B, 0x40, static_cast<uint8_t>(element)}) : !(bytes({0x48, 0x8B, 0x80}) && dword(element))) { return false; }
    // mov [rdx],eax; shr rax,32; mov [rdx+4],eax
    return bytes({0x89, 0x02, 0x48, 0xC1, 0xE8, 0x20, 0x89, 0x42, 0x04});
}

// 3.4: the game lists a character's weapon abilities by looking up each of its weapons' Equipment rows and reading the
// row's BurstAbilityID (an FName in the frozen row):
//   lea rcx,[rip+Table]; call Lookup; mov r13,rax; test rax,rax; je Skip; mov rcx,[rax+field]
// The mod points such calls at a lookup of its own that hands out a stand-in row with another ability for a weapon.
struct WeaponRowCall
{
    size_t Call = 0;         // where the call (E8) is, from the start of the match
    int64_t Table = 0;       // what lea loads, from the start of the match
    int64_t Lookup = 0;      // what the call calls, from the start of the match
    int32_t Field = 0;       // the field read from the row
};
inline constexpr size_t WeaponRowCallSize = 7 + 5 + 3 + 3 + 6 + 7;
inline bool IsWeaponRowCall(const uint8_t* code, size_t size, WeaponRowCall* out = nullptr)
{
    if (!code || size < WeaponRowCallSize) { return false; }
    // lea rcx,[rip+rel32]
    if (code[0] != 0x48 || code[1] != 0x8D || code[2] != 0x0D) { return false; }
    // call rel32
    if (code[7] != 0xE8) { return false; }
    // mov r13,rax; test rax,rax; je rel32
    static constexpr uint8_t middle[] = {0x4C, 0x8B, 0xE8, 0x48, 0x85, 0xC0, 0x0F, 0x84};
    if (std::memcmp(code + 12, middle, sizeof(middle)) != 0) { return false; }
    // mov rcx,[rax+disp32]
    if (code[24] != 0x48 || code[25] != 0x8B || code[26] != 0x88) { return false; }
    int32_t table = 0, call = 0, field = 0;
    std::memcpy(&table, code + 3, 4);
    std::memcpy(&call, code + 8, 4);
    std::memcpy(&field, code + 27, 4);
    if (field <= 0 || field > 0x10000 || (field & 7) != 0) { return false; }
    if (out)
    {
        out->Call = 7;
        out->Table = 7 + static_cast<int64_t>(table);
        out->Lookup = 12 + static_cast<int64_t>(call);
        out->Field = field;
    }
    return true;
}
} // namespace Frozen

// Set names player characters use (CharaSpec AnimationSetList); a folder source is searched for these and Sets.
inline const std::vector<std::wstring>& StandardSetNames()
{
    static const std::vector<std::wstring> names{L"Battle00", L"Battle01",  L"Battle02",  L"Battle00_Comp", L"Battle01_Comp", L"Neutral00",
                                                 L"Neutral01", L"Neutral10", L"Neutral20", L"Emotion00",     L"Facial00",      L"Facial01"};
    return names;
}

inline bool StartsWithFolded(std::wstring_view text, std::wstring_view prefix)
{
    return text.size() >= prefix.size() && NameEquals(text.substr(0, prefix.size()), prefix);
}

// 3.3: the game builds a player's ability lists from the first 5 CommandAbilityID_Array entries and the first 3
// LimitAbilityID_Array entries of its BattlePlayerParameter row (then adds its weapons' and materia's abilities).
inline constexpr size_t MaxCommandAbilities = 5;
inline constexpr size_t MaxLimitAbilities = 3;

// The game's EPlayerType of a party member's BattlePlayerParameter row ("pt_Cloud" -> 0, "pt_AerithAge7" -> 11);
// -1 for any other row.
inline int PlayerTypeOf(std::wstring_view player)
{
    static constexpr std::pair<const wchar_t*, int> types[] = {{L"Cloud", 0},    {L"Barret", 1},    {L"Tifa", 2},     {L"Aerith", 3},
                                                               {L"RedXIII", 4},  {L"Yuffie", 5},    {L"CaitSith", 6}, {L"Zack", 7},
                                                               {L"Sephiroth", 8}, {L"Vincent", 9},  {L"Cid", 10},     {L"AerithAge7", 11}};
    if (!StartsWithFolded(player, L"pt_")) { return -1; }
    player.remove_prefix(3);
    for (const auto& [name, type] : types)
    {
        if (NameEquals(player, name)) { return type; }
    }
    return -1;
}

// Battle00, Battle01_Comp, ... take the "battle" sources.
inline bool IsBattleSetName(std::wstring_view name) { return StartsWithFolded(name, L"Battle"); }

// "Battle00", "Neutral20", "Facial01_Foo": a set name rather than a folder name.
inline bool LooksLikeSetName(std::wstring_view name)
{
    for (const wchar_t* prefix : {L"Battle", L"Neutral", L"Emotion", L"Facial", L"Reaction", L"Mount"})
    {
        const std::wstring_view p(prefix);
        if (StartsWithFolded(name, p) && name.size() > p.size() && name[p.size()] >= L'0' && name[p.size()] <= L'9') { return true; }
    }
    return false;
}

// Object name of an object path ("/Game/A/Battle00.Battle00" -> "Battle00").
inline std::wstring ObjectNameOfPath(std::wstring_view path)
{
    const size_t cut = path.find_last_of(L".:/");
    return std::wstring(cut == std::wstring_view::npos ? path : path.substr(cut + 1));
}

// "PC0000_00_Cloud_Standard", "CharaSpec_PC0000_00_Cloud_Standard" or the pack's path ->
// "/Game/DataAsset/Game/CharaSpec/CharaSpec_PC0000_00_Cloud_Standard.CharaSpec_PC0000_00_Cloud_Standard". Empty when unusable.
inline std::wstring CharacterPackPath(std::wstring_view input)
{
    const std::wstring s = Trim(input);
    if (s.empty()) { return {}; }
    if (s[0] == L'/' || s[0] == L'\\' || s.find(L'\'') != std::wstring::npos) { return NormalizeObjectPath(s); }
    if (s.find_first_of(L"/\\.: \t") != std::wstring::npos) { return {}; }
    const std::wstring name = StartsWithFolded(s, L"CharaSpec_") ? s : L"CharaSpec_" + s;
    return L"/Game/DataAsset/Game/CharaSpec/" + name + L"." + name;
}

// A source string: a folder ("/Game/Motion/Player/PC0000_Cloud") or one set ("/Game/.../Battle00.Battle00",
// "EndAnimSet'/Game/.../Battle00.Battle00'", or a package path whose name looks like a set name). False when unusable.
inline bool ParseSetSource(std::wstring_view input, SetSource& out)
{
    std::wstring s = Trim(input);
    for (auto& c : s) { if (c == L'\\') { c = L'/'; } }
    while (s.size() > 1 && s.back() == L'/') { s.pop_back(); }
    if (s.empty()) { return false; }
    const bool quoted = s.find(L'\'') != std::wstring::npos || (s[0] != L'/' && s.find(L" /") != std::wstring::npos);
    const size_t slash = s.find_last_of(L'/');
    const std::wstring leaf = slash == std::wstring::npos ? s : s.substr(slash + 1);
    if (quoted || leaf.find(L'.') != std::wstring::npos || LooksLikeSetName(leaf))
    {
        out.Path = NormalizeObjectPath(s);
        out.Folder = false;
        return !out.Path.empty();
    }
    out.Path = NormalizePathPrefix(s);
    out.Folder = true;
    return !out.Path.empty();
}

// The set a source fills.
inline std::wstring SetNameOf(const SetSource& source) { return source.As.empty() ? ObjectNameOfPath(source.Path) : source.As; }

// "Battle01" -> "Battle00", "Neutral20" -> "Neutral00": the first set of the same kind. Empty for names like
// "Battle00_Comp" or a name that already is that set.
inline std::wstring FirstSetOfKind(std::wstring_view setName)
{
    if (setName.find(L'_') != std::wstring_view::npos) { return {}; }
    size_t letters = 0;
    while (letters < setName.size() && !(setName[letters] >= L'0' && setName[letters] <= L'9')) { ++letters; }
    if (letters == 0 || letters == setName.size()) { return {}; }
    std::wstring first = std::wstring(setName.substr(0, letters)) + L"00";
    return NameEquals(first, setName) ? std::wstring{} : first;
}

// One source of one set: the object paths to try in order (the first one that exists is used), and how it takes part.
struct SetSourceRef
{
    std::vector<std::wstring> Paths;
    AutoMatchMode Auto = AutoMatchMode::Off;
    std::vector<std::wstring> Only;
};

// The sources a row reads set `setName` from, in order of preference. A folder source with "auto" whose character
// has no set of that name falls back to its first set of the same kind (Battle01 -> its Battle00).
inline std::vector<SetSourceRef> SetSourcesFor(const AnimSetRow& row, std::wstring_view setName)
{
    std::vector<SetSourceRef> out;
    const auto seen = [&](const std::wstring& path) {
        return std::any_of(out.begin(), out.end(), [&](const SetSourceRef& r) {
            return std::any_of(r.Paths.begin(), r.Paths.end(), [&](const std::wstring& p) { return PathEquals(p, path); });
        });
    };
    for (const SetSource& source : IsBattleSetName(setName) ? row.Battle : row.Field)
    {
        SetSourceRef ref;
        ref.Auto = source.Auto;
        ref.Only = source.Only;
        if (source.Folder)
        {
            ref.Paths.push_back(source.Path + L"/" + std::wstring(setName) + L"." + std::wstring(setName));
            if (source.Auto != AutoMatchMode::Off)
            {
                const std::wstring first = FirstSetOfKind(setName);
                if (!first.empty()) { ref.Paths.push_back(source.Path + L"/" + first + L"." + first); }
            }
        }
        else if (NameEquals(SetNameOf(source), setName))
        {
            ref.Paths.push_back(source.Path);
        }
        if (ref.Paths.empty() || seen(ref.Paths.front())) { continue; }
        out.push_back(std::move(ref));
    }
    return out;
}

// Every object path a row may read set `setName` from (fallbacks included), in order of preference.
inline std::vector<std::wstring> SetSourcePaths(const AnimSetRow& row, std::wstring_view setName)
{
    std::vector<std::wstring> out;
    for (const auto& ref : SetSourcesFor(row, setName))
    {
        for (const auto& path : ref.Paths)
        {
            if (std::none_of(out.begin(), out.end(), [&](const std::wstring& p) { return PathEquals(p, path); })) { out.push_back(path); }
        }
    }
    return out;
}

// ---------------------------------------------------------------------------------------
// Auto match (3.2). A source marked "auto" (another character's animations, e.g. Rufus for Vincent) also fills the
// names it lacks:
//  1. same name;
//  2. same move, another variant: the same body and number with the closest suffix ("B_Walk01_0_L0" -> "B_Walk01_0");
//  3. same kind (battle sets): attacks -> its attacks, air attacks -> its air attacks, attack abilities and limits ->
//     its attacks. Each name gets the unused move of that kind with the closest length, so pacing stays similar.
// Moves are whole: a move split into pieces ("B_AtkShot02_0" aim, "_1" fire, "_2" recover; some too short to stand
// alone) is offered as all its pieces played one after another. Additive animations never take part. Of the names
// asked for, a split move only offers its longest piece. Lengths come from the game; 0 means unknown.
// ---------------------------------------------------------------------------------------
struct MatchAnim
{
    std::wstring Name;     // animation name in the set (the key the game asks for)
    float Length = 0.0f;   // seconds; 0 = unknown
    bool Additive = false;
};

struct AutoMatchPick
{
    size_t Target = 0;     // index into the targets
    size_t Source = 0;     // index into the sources (a split move: its first piece)
    int Tier = 0;          // 2 variant, 3 kind
    std::vector<size_t> Chain; // a split move: every piece in play order (Source first); empty for one animation
};

namespace Detail
{
struct AnimName
{
    std::wstring Lead;                 // "B_", "N_", ... (folded)
    std::wstring Body;                 // "NAttack", "Walk", "AtkShotGun" (folded)
    std::wstring Num;                  // "01"
    std::vector<std::wstring> Rest;    // tokens after the number, folded: "_1_2" -> {"1", "2"}
    std::wstring Stem;                 // folded name without a trailing "_<digits>" token (phase)
    int Phase = -1;                    // that trailing number, -1 when none
};

inline bool AllDigits(std::wstring_view s)
{
    return !s.empty() && std::all_of(s.begin(), s.end(), [](wchar_t c) { return c >= L'0' && c <= L'9'; });
}

inline AnimName ParseAnimName(std::wstring_view input)
{
    AnimName out;
    std::wstring s = FoldedKey(input);
    // Character prefix "pc0000_00_" of some reaction animations.
    if (s.size() > 10 && std::iswalpha(s[0]) && std::iswalpha(s[1]) && AllDigits(std::wstring_view(s).substr(2, 4)) && s[6] == L'_' &&
        AllDigits(std::wstring_view(s).substr(7, 2)) && s[9] == L'_')
    {
        s.erase(0, 10);
    }
    size_t p = 0;
    if (s.size() > 2 && std::iswalpha(s[0]) && s[1] == L'_') { out.Lead = s.substr(0, 2); p = 2; }
    size_t bodyEnd = p;
    while (bodyEnd < s.size() && !(s[bodyEnd] >= L'0' && s[bodyEnd] <= L'9')) { ++bodyEnd; }
    out.Body = s.substr(p, bodyEnd - p);
    while (!out.Body.empty() && out.Body.back() == L'_') { out.Body.pop_back(); }
    size_t numEnd = bodyEnd;
    while (numEnd < s.size() && s[numEnd] >= L'0' && s[numEnd] <= L'9') { ++numEnd; }
    out.Num = s.substr(bodyEnd, numEnd - bodyEnd);
    std::wstring token;
    for (size_t i = numEnd; i <= s.size(); ++i)
    {
        if (i == s.size() || s[i] == L'_')
        {
            if (!token.empty()) { out.Rest.push_back(token); }
            token.clear();
        }
        else
        {
            token += s[i];
        }
    }
    out.Stem = s;
    const size_t cut = s.find_last_of(L'_');
    if (cut != std::wstring::npos && cut > p && AllDigits(std::wstring_view(s).substr(cut + 1)) && cut + 1 < s.size() &&
        s.size() - (cut + 1) <= 2 && cut >= numEnd)
    {
        out.Phase = std::stoi(s.substr(cut + 1));
        out.Stem = s.substr(0, cut);
    }
    return out;
}

inline bool HasAny(std::wstring_view text, std::initializer_list<const wchar_t*> words)
{
    for (const wchar_t* w : words)
    {
        if (text.find(w) != std::wstring_view::npos) { return true; }
    }
    return false;
}

// Kinds of the names the game asks for (battle sets): 1 attack, 2 air attack, 3 attack ability or limit, 4 air ability.
inline int TargetKind(const AnimName& n)
{
    if (n.Lead != L"b_") { return 0; }
    const std::wstring& b = n.Body;
    if (b.rfind(L"atkburstj", 0) == 0) { return 4; }
    if (b == L"nattackj" || b == L"sattackj" || b == L"aattack") { return 2; }
    if (b == L"nattack" || b == L"sattack" || b == L"ssattack" || b == L"wattack" || b == L"counterattack") { return 1; }
    if (b.rfind(L"atkburst", 0) == 0 || b.rfind(L"atklimit", 0) == 0) { return 3; }
    return 0;
}

// The words of an animation name, lower case: "B_AtkAerialTwinShot01" -> b, atk, aerial, twin, shot, 01;
// "B_WIdleL01_1" -> b, w, idle, l, 01, 1.
inline std::vector<std::wstring> Words(std::wstring_view name)
{
    std::vector<std::wstring> words;
    std::wstring word;
    const auto flush = [&] {
        if (!word.empty()) { words.push_back(FoldedKey(word)); }
        word.clear();
    };
    const auto upper = [](wchar_t c) { return c >= L'A' && c <= L'Z'; };
    const auto lower = [](wchar_t c) { return c >= L'a' && c <= L'z'; };
    const auto digit = [](wchar_t c) { return c >= L'0' && c <= L'9'; };
    for (size_t i = 0; i < name.size(); ++i)
    {
        const wchar_t c = name[i];
        if (c == L'_' || c == L' ' || c == L'-') { flush(); continue; }
        if (!word.empty())
        {
            const wchar_t p = word.back();
            const bool next = i + 1 < name.size() && lower(name[i + 1]);
            if ((lower(p) && upper(c)) || (digit(p) != digit(c)) || (upper(p) && upper(c) && next)) { flush(); }
        }
        word += c;
    }
    flush();
    return words;
}

inline bool HasWord(const std::vector<std::wstring>& words, std::initializer_list<const wchar_t*> wanted)
{
    for (const auto& w : words)
    {
        for (const wchar_t* x : wanted)
        {
            if (w == x) { return true; }
        }
    }
    return false;
}

// Kinds of another character's animations: 1 attack, 2 air attack, 0 anything else.
inline int SourceKind(const AnimName& n, std::wstring_view name)
{
    if (n.Lead != L"b_") { return 0; }
    const std::vector<std::wstring> words = Words(name);
    const std::wstring folded = FoldedKey(name);
    if (HasWord(words, {L"dmg", L"damage", L"guard", L"parry", L"step", L"turn", L"walk", L"run", L"idle", L"die", L"abnormal", L"accel", L"call",
                        L"test", L"win", L"avoid", L"reload", L"setup", L"add", L"down", L"recover", L"fall", L"land", L"wait"}) ||
        HasAny(folded, {L"reload", L"setup", L"damage"}))
    {
        return 0;
    }
    if (!HasAny(n.Body, {L"atk", L"attack", L"shot", L"counter", L"kick", L"punch", L"slash", L"strike", L"combi"})) { return 0; }
    return (HasAny(folded, {L"aerial"}) || HasWord(words, {L"air", L"jump", L"j"})) ? 2 : 1;
}

// Which members of phased moves take part: a stem whose pieces are all at least `minPiece` long is a set of separate
// animations (every piece takes part); otherwise only its longest piece does, if it reaches `minLeader`.
inline std::vector<uint8_t> CompleteAnimations(const std::vector<MatchAnim>& anims, const std::vector<AnimName>& names, float minPiece, float minLeader)
{
    std::vector<uint8_t> out(anims.size(), 0);
    std::unordered_map<std::wstring, std::vector<size_t>> stems;
    for (size_t i = 0; i < anims.size(); ++i)
    {
        if (anims[i].Additive || anims[i].Length <= 0.0f) { continue; }
        stems[names[i].Stem].push_back(i);
    }
    for (const auto& [stem, members] : stems)
    {
        const bool allLong = std::all_of(members.begin(), members.end(), [&](size_t i) { return anims[i].Length >= minPiece; });
        if (allLong)
        {
            for (size_t i : members) { out[i] = 1; }
            continue;
        }
        size_t best = members.front();
        for (size_t i : members)
        {
            if (anims[i].Length > anims[best].Length) { best = i; }
        }
        if (anims[best].Length >= minLeader) { out[best] = 1; }
    }
    return out;
}

// A whole move another character offers: one animation, or every piece of a split move in play order.
struct MoveCandidate
{
    std::vector<size_t> Pieces;
    float Length = 0.0f;
};

// The whole moves of a set: animations that stand alone (every piece of a stem at least `minPiece` long), and each
// split move (pieces numbered "_0", "_1", ... not all that long) as all its pieces, when they add up to `minMove`.
// Additive animations and unknown lengths take no part. In set order.
inline std::vector<MoveCandidate> WholeMoves(const std::vector<MatchAnim>& anims, const std::vector<AnimName>& names, float minPiece, float minMove)
{
    std::vector<MoveCandidate> out;
    std::unordered_map<std::wstring, std::vector<size_t>> stems;
    std::vector<std::wstring> order;
    for (size_t i = 0; i < anims.size(); ++i)
    {
        if (anims[i].Additive || anims[i].Length <= 0.0f) { continue; }
        auto& members = stems[names[i].Stem];
        if (members.empty()) { order.push_back(names[i].Stem); }
        members.push_back(i);
    }
    for (const auto& stem : order)
    {
        std::vector<size_t> members = stems[stem];
        if (std::all_of(members.begin(), members.end(), [&](size_t i) { return anims[i].Length >= minPiece; }))
        {
            for (size_t i : members) { out.push_back({{i}, anims[i].Length}); }
            continue;
        }
        const bool split = members.size() >= 2 && std::all_of(members.begin(), members.end(), [&](size_t i) { return names[i].Phase >= 0; });
        if (split)
        {
            std::stable_sort(members.begin(), members.end(), [&](size_t a, size_t b) { return names[a].Phase < names[b].Phase; });
            bool distinct = true;
            for (size_t k = 1; k < members.size(); ++k) { distinct = distinct && names[members[k]].Phase != names[members[k - 1]].Phase; }
            float length = 0.0f;
            for (size_t i : members) { length += anims[i].Length; }
            if (distinct && length >= minMove) { out.push_back({members, length}); }
            continue;
        }
        size_t best = members.front();
        for (size_t i : members)
        {
            if (anims[i].Length > anims[best].Length) { best = i; }
        }
        if (anims[best].Length >= minMove) { out.push_back({{best}, anims[best].Length}); }
    }
    return out;
}
} // namespace Detail

// `open[i]`: target i still needs an animation (targets that are not open only give phased moves their context).
// Whether an animation name contains one of the words (case-insensitive); an empty list takes every name.
inline bool NameHasAny(std::wstring_view name, const std::vector<std::wstring>& words)
{
    if (words.empty()) { return true; }
    const std::wstring folded = FoldedKey(name);
    return std::any_of(words.begin(), words.end(), [&](const std::wstring& w) { return !w.empty() && folded.find(FoldedKey(w)) != std::wstring::npos; });
}

// `only`: matched animations must have one of these words in their name ("Shot", "Gun"); empty takes every one.
inline std::vector<AutoMatchPick> AutoMatch(const std::vector<MatchAnim>& targets, const std::vector<uint8_t>& open, const std::vector<MatchAnim>& sources,
                                            const std::vector<std::wstring>& only = {})
{
    std::vector<AutoMatchPick> picks;
    std::vector<Detail::AnimName> tn, sn;
    tn.reserve(targets.size());
    sn.reserve(sources.size());
    for (const auto& t : targets) { tn.push_back(Detail::ParseAnimName(t.Name)); }
    for (const auto& s : sources) { sn.push_back(Detail::ParseAnimName(s.Name)); }
    std::vector<uint8_t> taken(targets.size(), 0);
    std::unordered_set<std::wstring> sourceNames;
    for (const auto& s : sources) { sourceNames.insert(FoldedKey(s.Name)); }

    // 2. Same move, another variant: same lead, body and number; the suffix closest by tokens.
    for (size_t t = 0; t < targets.size(); ++t)
    {
        if (t >= open.size() || !open[t] || sourceNames.count(FoldedKey(targets[t].Name)) > 0) { continue; }
        const auto& a = tn[t];
        if (a.Body.empty()) { continue; }
        int bestScore = -1000;
        size_t best = sources.size();
        for (size_t s = 0; s < sources.size(); ++s)
        {
            const auto& b = sn[s];
            if (b.Lead != a.Lead || b.Body != a.Body || b.Num != a.Num || sources[s].Additive != targets[t].Additive) { continue; }
            if (!NameHasAny(sources[s].Name, only)) { continue; }
            if (a.Phase >= 0 && b.Phase >= 0 && a.Phase != b.Phase) { continue; } // a start piece never stands in for an end
            int score = 0;
            const size_t common = (std::min)(a.Rest.size(), b.Rest.size());
            for (size_t k = 0; k < common; ++k) { score += a.Rest[k] == b.Rest[k] ? 2 : -2; }
            score -= static_cast<int>((std::max)(a.Rest.size(), b.Rest.size()) - common);
            if (score > bestScore) { bestScore = score; best = s; }
        }
        if (best < sources.size() && bestScore > -2)
        {
            picks.push_back({t, best, 2, {}});
            taken[t] = 1;
        }
    }

    // 3. Same kind, battle sets only: closest length among the unused moves of that kind. Basic attacks choose
    //    first (they are seen most), then abilities and limits; air attacks have their own pool.
    const std::vector<uint8_t> targetComplete = Detail::CompleteAnimations(targets, tn, 0.6f, 0.6f);
    const std::vector<Detail::MoveCandidate> moves = Detail::WholeMoves(sources, sn, 0.6f, 1.0f);
    std::vector<size_t> attackPool, airPool; // indices into moves
    for (size_t m = 0; m < moves.size(); ++m)
    {
        const size_t first = moves[m].Pieces.front();
        if (!NameHasAny(sources[first].Name, only)) { continue; }
        const int kind = Detail::SourceKind(sn[first], sources[first].Name);
        if (kind == 1) { attackPool.push_back(m); }
        else if (kind == 2) { airPool.push_back(m); }
    }
    std::vector<size_t> order(targets.size());
    std::vector<std::wstring> folded(targets.size());
    for (size_t i = 0; i < order.size(); ++i)
    {
        order[i] = i;
        folded[i] = FoldedKey(targets[i].Name);
    }
    std::sort(order.begin(), order.end(), [&](size_t x, size_t y) {
        const int kx = Detail::TargetKind(tn[x]), ky = Detail::TargetKind(tn[y]);
        if (kx != ky) { return kx < ky; }
        return folded[x] < folded[y];
    });
    std::vector<uint8_t> used(moves.size(), 0);
    for (size_t t : order)
    {
        if (t >= open.size() || !open[t] || taken[t] || !targetComplete[t] || sourceNames.count(FoldedKey(targets[t].Name)) > 0) { continue; }
        const int kind = Detail::TargetKind(tn[t]);
        if (kind == 0) { continue; }
        const bool air = kind == 2 || kind == 4;
        const std::vector<size_t>& pool = air ? airPool : attackPool;
        if (pool.empty()) { continue; }
        if (std::all_of(pool.begin(), pool.end(), [&](size_t m) { return used[m] != 0; }))
        {
            for (size_t m : pool) { used[m] = 0; } // every one was used once: start over
        }
        size_t best = moves.size();
        float bestGap = 0.0f;
        for (size_t m : pool)
        {
            if (used[m]) { continue; }
            const float gap = std::fabs(moves[m].Length - targets[t].Length);
            if (best == moves.size() || gap < bestGap) { best = m; bestGap = gap; }
        }
        if (best == moves.size()) { continue; }
        used[best] = 1;
        AutoMatchPick pick{t, moves[best].Pieces.front(), 3, {}};
        if (moves[best].Pieces.size() > 1) { pick.Chain = moves[best].Pieces; }
        picks.push_back(std::move(pick));
        taken[t] = 1;
    }
    return picks;
}

// An animation name the game asks for when the character attacks: attacks, air attacks, attack abilities, limits
// (`basic`: attacks and air attacks only).
inline bool IsAttackName(std::wstring_view name, bool basic = false)
{
    const int kind = Detail::TargetKind(Detail::ParseAnimName(name));
    return basic ? (kind == 1 || kind == 2) : kind != 0;
}

// One source set of a merge: its animations in map order (raw FName keys and what the auto match needs to know).
struct MergeSource
{
    AutoMatchMode Auto = AutoMatchMode::Off;
    std::vector<std::wstring> Only; // auto matches: only animations with one of these words in their name
    std::vector<uint64_t> Keys;
    std::vector<MatchAnim> Anims; // same order as Keys; Name is the text of the key
};

struct MergedEntry
{
    uint64_t Key = 0;    // the name the game asks for
    size_t Source = 0;   // source the animation comes from
    size_t Entry = 0;    // its index in that source (a split move: its first piece)
    int Tier = 0;        // 0 same name (ordinary source), 1 same name (auto source), 2 another variant, 3 same kind
    std::vector<size_t> Chain; // a split move of the source: every piece in play order (play them as one); else empty
};

// The animations of one set from its sources, in order of preference (see AutoMatchMode). The names the game asks for
// are the names of the ordinary sources (the character's own set, its fallbacks, the pack's set); an auto source only
// fills names no source before it has filled. Entries come in the order they were filled.
inline std::vector<MergedEntry> MergeSetSources(const std::vector<MergeSource>& sources)
{
    std::vector<MergedEntry> out;
    std::unordered_map<uint64_t, size_t> filled;
    // The names the game asks for, with the animation the first ordinary source has under each.
    std::vector<uint64_t> wantedKeys;
    std::vector<MatchAnim> wanted;
    std::unordered_map<uint64_t, size_t> wantedIndex;
    for (const auto& source : sources)
    {
        if (source.Auto != AutoMatchMode::Off) { continue; }
        for (size_t e = 0; e < source.Keys.size() && e < source.Anims.size(); ++e)
        {
            if (wantedIndex.emplace(source.Keys[e], wanted.size()).second)
            {
                wantedKeys.push_back(source.Keys[e]);
                wanted.push_back(source.Anims[e]);
            }
        }
    }
    // Per name: 1 basic attack (Basic and up), 2 ability or limit (Attacks and up), 0 anything else.
    std::vector<uint8_t> attack(wanted.size(), 0);
    for (size_t t = 0; t < wanted.size(); ++t) { attack[t] = IsAttackName(wanted[t].Name, true) ? 1 : IsAttackName(wanted[t].Name) ? 2 : 0; }
    const auto takes = [&](AutoMatchMode mode, size_t t) {
        return mode == AutoMatchMode::All || (attack[t] != 0 && (attack[t] == 1 || mode != AutoMatchMode::Basic));
    };
    const auto fill = [&](uint64_t key, size_t source, size_t entry, int tier, std::vector<size_t> chain = {}) {
        if (filled.emplace(key, out.size()).second) { out.push_back({key, source, entry, tier, std::move(chain)}); }
    };
    for (size_t s = 0; s < sources.size(); ++s)
    {
        const MergeSource& source = sources[s];
        const size_t count = (std::min)(source.Keys.size(), source.Anims.size());
        if (source.Auto == AutoMatchMode::Off)
        {
            for (size_t e = 0; e < count; ++e) { fill(source.Keys[e], s, e, 0); }
            continue;
        }
        // Same name first: every name (All) or the attack names the game asks for (Attacks). "only" limits every pick.
        for (size_t e = 0; e < count; ++e)
        {
            if (!NameHasAny(source.Anims[e].Name, source.Only)) { continue; }
            const auto it = wantedIndex.find(source.Keys[e]);
            const bool asked = it != wantedIndex.end();
            if (source.Auto == AutoMatchMode::All || (asked && takes(source.Auto, it->second))) { fill(source.Keys[e], s, e, asked ? 1 : 0); }
        }
        // Then the names still open: another variant of the same move, else an attack of the same kind.
        std::vector<uint8_t> open(wanted.size(), 0);
        bool any = false;
        for (size_t t = 0; t < wanted.size(); ++t)
        {
            open[t] = (filled.count(wantedKeys[t]) == 0 && takes(source.Auto, t)) ? 1 : 0;
            any = any || open[t];
        }
        if (!any) { continue; }
        const std::vector<MatchAnim> offered(source.Anims.begin(), source.Anims.begin() + static_cast<std::ptrdiff_t>(count));
        for (const AutoMatchPick& pick : AutoMatch(wanted, open, offered, source.Only)) { fill(wantedKeys[pick.Target], s, pick.Source, pick.Tier, pick.Chain); }
    }
    return out;
}

// ---------------------------------------------------------------------------------------
// Proportions (3.2). EBoneTranslationRetargetingMode per bone of a receiving skeleton so that every character keeps
// its own bone lengths while it plays animations made for another body: the body chain takes its translation from the
// character's own mesh (Skeleton), the pelvis is scaled by the ratio of the two bodies (AnimationScaled, against the
// pose of the character the animation was made for), and everything else (root, face, physics, weapons, driven
// bones) keeps the animation's own translation.
// ---------------------------------------------------------------------------------------
enum class RetargetMode : int8_t
{
    Keep = -1,
    Animation = 0,
    Skeleton = 1,
    AnimationScaled = 2
};

namespace Detail
{
inline bool IsBodyBone(std::wstring_view name)
{
    // Square Enix humanoid naming: C_/L_/R_ + part + _a.._d ("L_UpperArm_a", "C_Spine_c", "R_Index_b").
    const std::wstring folded = FoldedKey(name);
    if (folded.size() < 5 || (folded[0] != L'c' && folded[0] != L'l' && folded[0] != L'r') || folded[1] != L'_') { return false; }
    const size_t cut = folded.find_last_of(L'_');
    if (cut <= 2 || cut + 2 != folded.size() || folded[cut + 1] < L'a' || folded[cut + 1] > L'd') { return false; }
    const std::wstring part = folded.substr(2, cut - 2);
    static const wchar_t* parts[] = {L"spine", L"neck", L"head", L"shoulder", L"upperarm", L"forearm", L"hand", L"thumb", L"index",
                                     L"middle", L"ring", L"pinky", L"upperleg", L"foreleg", L"foot", L"toe"};
    for (const wchar_t* p : parts)
    {
        if (part == p) { return true; }
    }
    return false;
}

inline bool IsPelvisName(std::wstring_view name)
{
    const std::wstring folded = FoldedKey(name);
    return folded.find(L"hip") != std::wstring::npos || folded.find(L"pelvis") != std::wstring::npos;
}
} // namespace Detail

// Mode for every bone of a skeleton (names and parent indices of its reference skeleton). (3.8.2) Bones matching `extra`
// ("proportion_bones" patterns) keep their length too, like the body's.
inline std::vector<RetargetMode> ProportionModes(const std::vector<std::wstring>& names, const std::vector<int32_t>& parents,
                                                 const std::vector<std::wstring>& extra = {})
{
    std::vector<RetargetMode> modes(names.size(), RetargetMode::Keep);
    if (names.empty() || parents.size() != names.size()) { return modes; }
    // Pelvis: a child of the root named like a hip, else the root's child with the most descendants.
    std::vector<int32_t> descendants(names.size(), 0);
    for (size_t i = names.size(); i-- > 1;)
    {
        const int32_t p = parents[i];
        if (p >= 0 && static_cast<size_t>(p) < names.size()) { descendants[static_cast<size_t>(p)] += descendants[i] + 1; }
    }
    int32_t pelvis = -1;
    for (size_t i = 1; i < names.size(); ++i)
    {
        if (parents[i] != 0) { continue; }
        if (Detail::IsPelvisName(names[i])) { pelvis = static_cast<int32_t>(i); break; }
        if (pelvis < 0 || descendants[i] > descendants[static_cast<size_t>(pelvis)]) { pelvis = static_cast<int32_t>(i); }
    }
    for (size_t i = 1; i < names.size(); ++i)
    {
        if (static_cast<int32_t>(i) == pelvis) { modes[i] = RetargetMode::AnimationScaled; }
        else if (Detail::IsBodyBone(names[i]) || (!extra.empty() && Shooter::BoneMatches(names[i], extra))) { modes[i] = RetargetMode::Skeleton; }
    }
    return modes;
}

// The reference pose a receiving skeleton keeps for the animations of another skeleton (a USkeleton::AnimRetargetSources
// entry): the receiving skeleton's own pose (`receivingPose`, one `stride`-byte transform per bone) with every bone the
// animation skeleton carries over (`trackMap`: animation bone -> receiving bone, -1 none) replaced by that skeleton's.
// AnimationScaled bones then scale by (playing mesh / the body the animation was made for). Empty when the sizes do
// not fit.
inline std::vector<uint8_t> BuildRetargetPose(const std::vector<uint8_t>& receivingPose, const std::vector<uint8_t>& animationPose,
                                              const std::vector<int32_t>& trackMap, size_t stride)
{
    if (stride == 0 || receivingPose.empty() || receivingPose.size() % stride != 0 || animationPose.size() != trackMap.size() * stride) { return {}; }
    std::vector<uint8_t> out = receivingPose;
    const size_t bones = receivingPose.size() / stride;
    for (size_t a = 0; a < trackMap.size(); ++a)
    {
        const int32_t to = trackMap[a];
        if (to < 0 || static_cast<size_t>(to) >= bones) { continue; }
        std::memcpy(out.data() + static_cast<size_t>(to) * stride, animationPose.data() + a * stride, stride);
    }
    return out;
}

// Counts per mode, for the log: "312 animation, 54 skeleton, 1 scaled".
inline std::wstring DescribeModes(const std::vector<RetargetMode>& modes)
{
    size_t keep = 0, skeleton = 0, scaled = 0;
    for (const RetargetMode m : modes)
    {
        if (m == RetargetMode::Skeleton) { ++skeleton; }
        else if (m == RetargetMode::AnimationScaled) { ++scaled; }
        else { ++keep; }
    }
    return std::to_wstring(skeleton) + L" body bone(s) keep their length, " + std::to_wstring(scaled) + L" pelvis scaled, " + std::to_wstring(keep) +
           L" other bone(s) unchanged";
}

// Set names a row builds: the standard ones and Sets for folder sources, and the set each set source fills.
inline std::vector<std::wstring> RowSetNames(const AnimSetRow& row)
{
    std::vector<std::wstring> out;
    const auto add = [&](const std::wstring& name) {
        if (!name.empty() && std::none_of(out.begin(), out.end(), [&](const std::wstring& n) { return NameEquals(n, name); })) { out.push_back(name); }
    };
    const bool battleFolders = std::any_of(row.Battle.begin(), row.Battle.end(), [](const SetSource& s) { return s.Folder; });
    const bool fieldFolders = std::any_of(row.Field.begin(), row.Field.end(), [](const SetSource& s) { return s.Folder; });
    for (const auto& list : {std::cref(StandardSetNames()), std::cref(row.Sets)})
    {
        for (const auto& name : list.get())
        {
            if (IsBattleSetName(name) ? battleFolders : fieldFolders) { add(name); }
        }
    }
    for (const auto& source : row.Battle) { if (!source.Folder && IsBattleSetName(SetNameOf(source))) { add(SetNameOf(source)); } }
    for (const auto& source : row.Field) { if (!source.Folder && !IsBattleSetName(SetNameOf(source))) { add(SetNameOf(source)); } }
    for (const auto& move : row.Moves) { if (!move.Set.empty()) { add(move.Set); } }
    for (const auto& form : row.Forms.List) { if (!form.Pack.empty()) { add(form.Pack); } } // 3.6: every form's pack is in the pack
    for (const auto& moveset : row.Forms.Movesets) { add(moveset.Pack); }                   // (3.15.1) and every moveset's
    return out;
}

// 3.6: whether a set is the pack of one of the row's forms (other than its normal one): a form pack nothing else fills
// starts from the character's own Battle00 and Battle00_Comp.
inline bool IsFormPack(const AnimSetRow& row, std::wstring_view setName)
{
    const auto named = [&](const Form& f) { return NameEquals(f.Pack, setName); };
    return !NameEquals(setName, DefaultAbilityPack()) &&
           (std::any_of(row.Forms.List.begin(), row.Forms.List.end(), named) ||
            std::any_of(row.Forms.Movesets.begin(), row.Forms.Movesets.end(), named));   // (3.15.1: a moveset's pack, too)
}

// Moves that apply to set `setName`: those naming it, then those naming no set.
inline std::vector<const AnimMove*> MovesFor(const AnimSetRow& row, std::wstring_view setName)
{
    std::vector<const AnimMove*> out;
    for (const auto& move : row.Moves) { if (!move.Set.empty() && NameEquals(move.Set, setName)) { out.push_back(&move); } }
    for (const auto& move : row.Moves) { if (move.Set.empty()) { out.push_back(&move); } }
    return out;
}

// ---------------------------------------------------------------------------------------
// TMap/TSet memory layout (UE 4.26) for maps the mod builds: GetTypeHash(FName) and the hash bucket layout.
// ---------------------------------------------------------------------------------------
// GetTypeHash(FNameEntryId) of UE 4.23+: the entry handle (block, offset) spread over the hash bits.
inline uint32_t NameEntryHash(uint32_t comparisonIndex)
{
    const uint32_t block = comparisonIndex >> 16;     // FNameBlockOffsetBits = 16
    const uint32_t offset = comparisonIndex & 0xFFFF;
    return (block << 19) + block + (offset << 16) + offset + (offset >> 4); // 32 - FNameMaxBlockBits(13) = 19
}

// GetTypeHash(FName) = GetTypeHash(ComparisonIndex) + Number. `handleHash` false: the older plain-index form.
inline uint32_t NameHash(uint32_t comparisonIndex, uint32_t number, bool handleHash)
{
    return (handleHash ? NameEntryHash(comparisonIndex) : comparisonIndex) + number;
}

// TSetAllocator::GetNumberOfHashBuckets.
inline int32_t HashBuckets(int32_t elements)
{
    if (elements < 4) { return 1; }
    const uint32_t wanted = static_cast<uint32_t>(elements) / 2 + 8;
    uint32_t size = 1;
    while (size < wanted) { size <<= 1; }
    return static_cast<int32_t>(size);
}

// A set whose elements fill slots 0..n-1 in order, as TSet builds it by adding them one after another.
struct SetImage
{
    int32_t HashSize = 0;
    std::vector<int32_t> Heads;   // bucket -> first element, -1 when empty
    std::vector<int32_t> Next;    // element -> next element in its bucket (HashNextId)
    std::vector<int32_t> Bucket;  // element -> its bucket (HashIndex)
    int32_t MaxBits = 0;          // allocation flag capacity: 128 inline bits, else a multiple of 32
    std::vector<uint32_t> Words;  // allocation flags, MaxBits / 32 words
};

inline SetImage BuildSetImage(const std::vector<uint32_t>& hashes)
{
    SetImage image;
    const int32_t count = static_cast<int32_t>(hashes.size());
    image.HashSize = HashBuckets(count);
    image.Heads.assign(static_cast<size_t>(image.HashSize), -1);
    image.Next.assign(hashes.size(), -1);
    image.Bucket.assign(hashes.size(), 0);
    for (int32_t i = 0; i < count; ++i)
    {
        const int32_t bucket = static_cast<int32_t>(hashes[static_cast<size_t>(i)] & static_cast<uint32_t>(image.HashSize - 1));
        image.Bucket[static_cast<size_t>(i)] = bucket;
        image.Next[static_cast<size_t>(i)] = image.Heads[static_cast<size_t>(bucket)]; // newest first, like TSet::LinkElement
        image.Heads[static_cast<size_t>(bucket)] = i;
    }
    image.MaxBits = (std::max)(128, (count + 31) / 32 * 32); // parenthesised: safe from Windows min/max macros
    image.Words.assign(static_cast<size_t>(image.MaxBits / 32), 0u);
    for (int32_t i = 0; i < count; ++i) { image.Words[static_cast<size_t>(i / 32)] |= 1u << (i % 32); }
    return image;
}

// Key/value lists of one set's sources, in order of preference, as one list: the first source with a key wins.
template <class Value>
inline std::vector<std::pair<uint64_t, Value>> MergeFirstWins(const std::vector<std::vector<std::pair<uint64_t, Value>>>& sources)
{
    std::vector<std::pair<uint64_t, Value>> out;
    std::unordered_map<uint64_t, size_t> index;
    for (const auto& list : sources)
    {
        for (const auto& [key, value] : list)
        {
            if (index.emplace(key, out.size()).second) { out.emplace_back(key, value); }
        }
    }
    return out;
}

// Every allocated element is reachable exactly once from the bucket its hash names, and records that bucket.
inline bool SetChainsMatch(const std::vector<int32_t>& heads, const std::vector<int32_t>& next, const std::vector<int32_t>& bucket,
                           const std::vector<uint8_t>& allocated, const std::vector<uint32_t>& hashes)
{
    const size_t size = heads.size();
    if (size == 0 || (size & (size - 1)) != 0 || next.size() != allocated.size() || bucket.size() != allocated.size() || hashes.size() != allocated.size())
    {
        return false;
    }
    std::vector<uint8_t> seen(allocated.size(), 0);
    size_t visited = 0;
    for (size_t b = 0; b < size; ++b)
    {
        for (int32_t e = heads[b]; e != -1; e = next[static_cast<size_t>(e)])
        {
            if (e < 0 || static_cast<size_t>(e) >= allocated.size() || !allocated[static_cast<size_t>(e)] || seen[static_cast<size_t>(e)]) { return false; }
            if (static_cast<size_t>(bucket[static_cast<size_t>(e)]) != b || (hashes[static_cast<size_t>(e)] & (size - 1)) != b) { return false; }
            seen[static_cast<size_t>(e)] = 1;
            ++visited;
        }
    }
    return visited == static_cast<size_t>(std::count(allocated.begin(), allocated.end(), uint8_t{1}));
}

// TSet / TMap header of UE 4.26 shipping (0x50 bytes): the sparse array (elements; allocation flags with four inline
// words; free list), the bucket heads (one inline slot, or a heap block when there is more than one bucket) and the
// bucket count.
struct SetHeader
{
    void* Elements = nullptr;
    int32_t Num = 0;
    int32_t Max = 0;
    uint32_t InlineFlags[4]{};
    uint32_t* HeapFlags = nullptr;
    int32_t NumBits = 0;
    int32_t MaxBits = 0;
    int32_t FirstFree = -1;
    int32_t NumFree = 0;
    int32_t InlineHash = 0;
    int32_t Pad0 = 0;
    int32_t* HeapHash = nullptr;
    int32_t HashSize = 0;
    int32_t Pad1 = 0;
};
static_assert(sizeof(SetHeader) == 0x50 && sizeof(void*) == 8, "UE 4.26 x64 TSet layout");

// TMap<FName, UObject*> element as the mod handles it: the raw FName (comparison index, number) and the pointer.
// In memory: TSetElement { TPair<FName, UObject*>; HashNextId; HashIndex } = 24 bytes.
struct NameObjectPair
{
    uint64_t Key = 0;
    void* Value = nullptr;
};
constexpr size_t NameObjectStride = 24;
constexpr int32_t MaxMapElements = 1 << 16;

inline uint32_t KeyHash(uint64_t key, bool handleHash)
{
    return NameHash(static_cast<uint32_t>(key & 0xFFFFFFFFu), static_cast<uint32_t>(key >> 32), handleHash);
}

// Reads a TMap<FName, Object*> from a copy of its header; `read(destination, source, bytes)` copies the blocks it points
// at (false when unreadable). Checks the layout and the bucket chains against both forms of GetTypeHash(FName):
// `forms` gets bit 0 when the plain index form checks out, bit 1 for the entry-handle form (a valid map has at least
// one). Elements come in slot order. False, with `why`, when the memory is not such a map.
template <class Read>
inline bool ReadNameObjectMap(const SetHeader& header, Read&& read, std::vector<NameObjectPair>& out, int& forms, std::wstring& why)
{
    out.clear();
    forms = 0;
    const int32_t slots = header.Num;
    if (slots == 0 && header.NumFree == 0) { forms = 3; return true; }
    if (slots < 0 || slots > MaxMapElements || header.Max < slots || !header.Elements || header.NumBits != slots || header.MaxBits < header.NumBits ||
        header.NumFree < 0 || header.NumFree >= slots)
    {
        why = L"map layout not recognised";
        return false;
    }
    std::vector<uint8_t> bytes(static_cast<size_t>(slots) * NameObjectStride);
    if (!read(bytes.data(), header.Elements, bytes.size())) { why = L"map elements unreadable"; return false; }
    const size_t wordCount = (static_cast<size_t>(slots) + 31) / 32;
    std::vector<uint32_t> words(wordCount, 0);
    if (header.HeapFlags)
    {
        if (!read(words.data(), header.HeapFlags, wordCount * sizeof(uint32_t))) { why = L"map flags unreadable"; return false; }
    }
    else if (wordCount <= 4)
    {
        std::copy(header.InlineFlags, header.InlineFlags + wordCount, words.begin());
    }
    else
    {
        why = L"map flags not recognised";
        return false;
    }
    std::vector<uint8_t> allocated(static_cast<size_t>(slots), 0);
    int32_t live = 0;
    for (int32_t i = 0; i < slots; ++i)
    {
        allocated[static_cast<size_t>(i)] = static_cast<uint8_t>((words[static_cast<size_t>(i) / 32] >> (i % 32)) & 1u);
        live += allocated[static_cast<size_t>(i)];
    }
    if (live != slots - header.NumFree) { why = L"map flags do not match its size"; return false; }
    const int32_t size = header.HashSize;
    if (size <= 0 || (size & (size - 1)) != 0 || size > (1 << 20) || (!header.HeapHash && size != 1))
    {
        why = L"map buckets not recognised";
        return false;
    }
    std::vector<int32_t> heads(static_cast<size_t>(size), -1);
    if (header.HeapHash)
    {
        if (!read(heads.data(), header.HeapHash, heads.size() * sizeof(int32_t))) { why = L"map buckets unreadable"; return false; }
    }
    else
    {
        heads[0] = header.InlineHash;
    }
    std::vector<int32_t> next(static_cast<size_t>(slots), -1), bucket(static_cast<size_t>(slots), 0);
    std::vector<uint32_t> plain(static_cast<size_t>(slots), 0), handle(static_cast<size_t>(slots), 0);
    out.reserve(static_cast<size_t>(live));
    for (int32_t i = 0; i < slots; ++i)
    {
        if (!allocated[static_cast<size_t>(i)]) { continue; }
        const uint8_t* element = bytes.data() + static_cast<size_t>(i) * NameObjectStride;
        NameObjectPair pair;
        std::memcpy(&pair.Key, element, sizeof(pair.Key));
        std::memcpy(&pair.Value, element + 8, sizeof(pair.Value));
        std::memcpy(&next[static_cast<size_t>(i)], element + 16, sizeof(int32_t));
        std::memcpy(&bucket[static_cast<size_t>(i)], element + 20, sizeof(int32_t));
        plain[static_cast<size_t>(i)] = KeyHash(pair.Key, false);
        handle[static_cast<size_t>(i)] = KeyHash(pair.Key, true);
        out.push_back(pair);
    }
    forms = (SetChainsMatch(heads, next, bucket, allocated, plain) ? 1 : 0) | (SetChainsMatch(heads, next, bucket, allocated, handle) ? 2 : 0);
    if (forms == 0)
    {
        out.clear();
        why = L"map buckets match no form of the FName hash";
        return false;
    }
    return true;
}

// The header and blocks of a TMap<FName, Object*> holding `entries` in that order, laid out as TSet lays out elements
// added one by one: elements in slots 0..n-1, newest first in each bucket, inline flag words up to 128 elements, an
// inline bucket head for a single bucket. `alloc(bytes)` returns memory the engine may free later (FMemory); on
// failure the blocks are handed back to `release` and false is returned.
template <class Alloc, class Release>
inline bool BuildNameObjectMap(const std::vector<NameObjectPair>& entries, bool handleHash, Alloc&& alloc, Release&& release, SetHeader& out)
{
    if (entries.empty() || entries.size() > static_cast<size_t>(MaxMapElements)) { return false; }
    std::vector<uint32_t> hashes;
    hashes.reserve(entries.size());
    for (const auto& entry : entries) { hashes.push_back(KeyHash(entry.Key, handleHash)); }
    const SetImage image = BuildSetImage(hashes);
    const int32_t count = static_cast<int32_t>(entries.size());
    auto* elements = static_cast<uint8_t*>(alloc(entries.size() * NameObjectStride));
    auto* words = image.MaxBits > 128 ? static_cast<uint32_t*>(alloc(image.Words.size() * sizeof(uint32_t))) : nullptr;
    auto* heads = image.HashSize > 1 ? static_cast<int32_t*>(alloc(image.Heads.size() * sizeof(int32_t))) : nullptr;
    if (!elements || (image.MaxBits > 128 && !words) || (image.HashSize > 1 && !heads))
    {
        for (void* block : {static_cast<void*>(elements), static_cast<void*>(words), static_cast<void*>(heads)})
        {
            if (block) { release(block); }
        }
        return false;
    }
    for (int32_t i = 0; i < count; ++i)
    {
        uint8_t* element = elements + static_cast<size_t>(i) * NameObjectStride;
        std::memcpy(element, &entries[static_cast<size_t>(i)].Key, 8);
        std::memcpy(element + 8, &entries[static_cast<size_t>(i)].Value, 8);
        std::memcpy(element + 16, &image.Next[static_cast<size_t>(i)], 4);
        std::memcpy(element + 20, &image.Bucket[static_cast<size_t>(i)], 4);
    }
    out = SetHeader{};
    out.Elements = elements;
    out.Num = count;
    out.Max = count;
    if (words) { std::copy(image.Words.begin(), image.Words.end(), words); }
    else { std::copy(image.Words.begin(), image.Words.begin() + 4, out.InlineFlags); }
    out.HeapFlags = words;
    out.NumBits = count;
    out.MaxBits = image.MaxBits;
    out.FirstFree = -1;
    out.NumFree = 0;
    if (heads) { std::copy(image.Heads.begin(), image.Heads.end(), heads); }
    else { out.InlineHash = image.Heads[0]; }
    out.HeapHash = heads;
    out.HashSize = image.HashSize;
    return true;
}

// Like BuildNameObjectMap for a TMap<FName, V> whose value is `valueSize` bytes (a multiple of 8, at most 8-aligned):
// element = { FName key; V value; int32 HashNextId; int32 HashIndex }, stride 16 + valueSize. `values` holds the value
// bytes of every entry back to back.
template <class Alloc, class Release>
inline bool BuildNameKeyedMap(const std::vector<uint64_t>& keys, const std::vector<uint8_t>& values, size_t valueSize, bool handleHash,
                              Alloc&& alloc, Release&& release, SetHeader& out)
{
    if (keys.empty() || keys.size() > static_cast<size_t>(MaxMapElements) || valueSize == 0 || valueSize % 8 != 0 ||
        values.size() != keys.size() * valueSize)
    {
        return false;
    }
    const size_t stride = 16 + valueSize;
    std::vector<uint32_t> hashes;
    hashes.reserve(keys.size());
    for (const uint64_t key : keys) { hashes.push_back(KeyHash(key, handleHash)); }
    const SetImage image = BuildSetImage(hashes);
    const int32_t count = static_cast<int32_t>(keys.size());
    auto* elements = static_cast<uint8_t*>(alloc(keys.size() * stride));
    auto* words = image.MaxBits > 128 ? static_cast<uint32_t*>(alloc(image.Words.size() * sizeof(uint32_t))) : nullptr;
    auto* heads = image.HashSize > 1 ? static_cast<int32_t*>(alloc(image.Heads.size() * sizeof(int32_t))) : nullptr;
    if (!elements || (image.MaxBits > 128 && !words) || (image.HashSize > 1 && !heads))
    {
        for (void* block : {static_cast<void*>(elements), static_cast<void*>(words), static_cast<void*>(heads)})
        {
            if (block) { release(block); }
        }
        return false;
    }
    for (int32_t i = 0; i < count; ++i)
    {
        uint8_t* element = elements + static_cast<size_t>(i) * stride;
        std::memcpy(element, &keys[static_cast<size_t>(i)], 8);
        std::memcpy(element + 8, values.data() + static_cast<size_t>(i) * valueSize, valueSize);
        std::memcpy(element + 8 + valueSize, &image.Next[static_cast<size_t>(i)], 4);
        std::memcpy(element + 12 + valueSize, &image.Bucket[static_cast<size_t>(i)], 4);
    }
    out = SetHeader{};
    out.Elements = elements;
    out.Num = count;
    out.Max = count;
    if (words) { std::copy(image.Words.begin(), image.Words.end(), words); }
    else { std::copy(image.Words.begin(), image.Words.begin() + 4, out.InlineFlags); }
    out.HeapFlags = words;
    out.NumBits = count;
    out.MaxBits = image.MaxBits;
    out.FirstFree = -1;
    out.NumFree = 0;
    if (heads) { std::copy(image.Heads.begin(), image.Heads.end(), heads); }
    else { out.InlineHash = image.Heads[0]; }
    out.HeapHash = heads;
    out.HashSize = image.HashSize;
    return true;
}

// An empty TMap as a default-constructed or empty-loaded one looks (nothing allocated).
inline bool IsEmptyMapHeader(const SetHeader& h)
{
    return h.Elements == nullptr && h.Num == 0 && h.Max == 0 && h.HeapFlags == nullptr && h.NumBits == 0 && h.NumFree == 0 && h.HeapHash == nullptr &&
           (h.HashSize == 0 || (h.HashSize == 1 && h.InlineHash == -1)) && (h.MaxBits == 0 || h.MaxBits == 128) &&
           (h.FirstFree == -1 || h.FirstFree == 0);
}

// Reads a TMap<FName, V> (V: `valueSize` bytes, a multiple of 8) from a copy of its header, the counterpart of
// BuildNameKeyedMap: the keys and the value bytes of every allocated element in slot order. The bucket chains must
// check out with the GetTypeHash(FName) form given. An empty map reads as no entries. False, with `why`, otherwise.
template <class Read>
inline bool ReadNameKeyedMap(const SetHeader& header, size_t valueSize, bool handleHash, Read&& read, std::vector<uint64_t>& keys,
                             std::vector<uint8_t>& values, std::wstring& why)
{
    keys.clear();
    values.clear();
    if (IsEmptyMapHeader(header)) { return true; }
    const int32_t slots = header.Num;
    if (valueSize == 0 || valueSize % 8 != 0 || slots <= 0 || slots > MaxMapElements || header.Max < slots || !header.Elements ||
        header.NumBits != slots || header.MaxBits < header.NumBits || header.NumFree < 0 || header.NumFree >= slots)
    {
        why = L"map layout not recognised";
        return false;
    }
    const size_t stride = 16 + valueSize;
    std::vector<uint8_t> bytes(static_cast<size_t>(slots) * stride);
    if (!read(bytes.data(), header.Elements, bytes.size())) { why = L"map elements unreadable"; return false; }
    const size_t wordCount = (static_cast<size_t>(slots) + 31) / 32;
    std::vector<uint32_t> words(wordCount, 0);
    if (header.HeapFlags)
    {
        if (!read(words.data(), header.HeapFlags, wordCount * sizeof(uint32_t))) { why = L"map flags unreadable"; return false; }
    }
    else if (wordCount <= 4)
    {
        std::copy(header.InlineFlags, header.InlineFlags + wordCount, words.begin());
    }
    else
    {
        why = L"map flags not recognised";
        return false;
    }
    std::vector<uint8_t> allocated(static_cast<size_t>(slots), 0);
    int32_t live = 0;
    for (int32_t i = 0; i < slots; ++i)
    {
        allocated[static_cast<size_t>(i)] = static_cast<uint8_t>((words[static_cast<size_t>(i) / 32] >> (i % 32)) & 1u);
        live += allocated[static_cast<size_t>(i)];
    }
    if (live != slots - header.NumFree) { why = L"map flags do not match its size"; return false; }
    const int32_t size = header.HashSize;
    if (size <= 0 || (size & (size - 1)) != 0 || size > (1 << 20) || (!header.HeapHash && size != 1))
    {
        why = L"map buckets not recognised";
        return false;
    }
    std::vector<int32_t> heads(static_cast<size_t>(size), -1);
    if (header.HeapHash)
    {
        if (!read(heads.data(), header.HeapHash, heads.size() * sizeof(int32_t))) { why = L"map buckets unreadable"; return false; }
    }
    else
    {
        heads[0] = header.InlineHash;
    }
    std::vector<int32_t> next(static_cast<size_t>(slots), -1), bucket(static_cast<size_t>(slots), 0);
    std::vector<uint32_t> hashes(static_cast<size_t>(slots), 0);
    for (int32_t i = 0; i < slots; ++i)
    {
        if (!allocated[static_cast<size_t>(i)]) { continue; }
        const uint8_t* element = bytes.data() + static_cast<size_t>(i) * stride;
        uint64_t key = 0;
        std::memcpy(&key, element, sizeof(key));
        std::memcpy(&next[static_cast<size_t>(i)], element + 8 + valueSize, sizeof(int32_t));
        std::memcpy(&bucket[static_cast<size_t>(i)], element + 12 + valueSize, sizeof(int32_t));
        hashes[static_cast<size_t>(i)] = KeyHash(key, handleHash);
        keys.push_back(key);
        values.insert(values.end(), element + 8, element + 8 + valueSize);
    }
    if (!SetChainsMatch(heads, next, bucket, allocated, hashes))
    {
        keys.clear();
        values.clear();
        why = L"map buckets do not follow the FName hash";
        return false;
    }
    return true;
}

// TSet::FindId on a map the mod can read: the slot of `key`, or -1.
template <class Read>
inline int32_t FindInNameObjectMap(const SetHeader& header, Read&& read, uint64_t key, bool handleHash)
{
    if (header.HashSize <= 0 || header.Num <= 0) { return -1; }
    int32_t e = -1;
    const int32_t bucket = static_cast<int32_t>(KeyHash(key, handleHash) & static_cast<uint32_t>(header.HashSize - 1));
    if (header.HeapHash) { if (!read(&e, header.HeapHash + bucket, sizeof(e))) { return -1; } }
    else { e = header.InlineHash; }
    for (int32_t guard = 0; e != -1 && guard <= header.Num; ++guard)
    {
        if (e < 0 || e >= header.Num) { return -1; }
        uint8_t element[NameObjectStride];
        if (!read(element, static_cast<const uint8_t*>(header.Elements) + static_cast<size_t>(e) * NameObjectStride, sizeof(element))) { return -1; }
        uint64_t found = 0;
        std::memcpy(&found, element, 8);
        if (found == key) { return e; }
        std::memcpy(&e, element + 16, 4);
    }
    return -1;
}

// 3.10.0: a skin (skins\<folder>\skin.json, made by the editor's Build Skins): a model on its own skeleton, worn by the
// characters of some CharaSpec rows in every form that has no model of its own, with its voice and weapon.
struct Skin
{
    std::wstring Name;                       // "name" (on the menu; the folder's name when empty)
    std::wstring Folder;                     // its folder under skins\ (what selects it)
    std::vector<std::wstring> Characters;    // "characters": the CharaSpec pack object paths of the rows that wear it
    std::wstring Model;                      // "model": the skeletal mesh (object path)
    std::wstring Skeleton;                   // "skeleton": its skeleton (object path)
    std::wstring Family;                     // "family": the hub of the skeleton family its skeleton joins (empty: none)
    bool KeepProportions = false;            // "proportions"
    std::vector<std::wstring> ProportionBones; // "proportion_bones"
    Voice Speaks;                            // "voice": as a row's ("own": the animations' own banks); unset: the row's
    std::wstring Weapon;                     // "weapon": a weapon blueprint's class (empty: the character's own)
    std::wstring AnimClass;                  // "anim_blueprint": the AnimBlueprint's class (empty: the character's own, the
                                             // model going on the game's way as a form's "as_look")
    std::wstring WeaponFieldSocket;          // (3.15.1) "weapon_field_socket": outside battle its weapon sits on this socket of
                                             // the model (Cloud's Buster Sword on his back: Attach_Weapon01); in battle where
                                             // the game puts it (the hand)
    std::vector<FormMesh> Meshes;            // (3.11.2) "meshes": model parts worn with its model, as a form's (a wing of its
                                             // own: "mesh", "socket", "follow_pose", or just the mesh's path)
    std::wstring Pack;                       // (3.18.0) "pack": the moves it carries: the animation pack the character plays
                                             // while it wears the skin, in its normal form and each form with no pack of its own
                                             // (a pack its row builds: a form's, or a "battle" source "as" it; empty: the form's)
    std::vector<std::pair<std::wstring, std::wstring>> Sets;   // (3.18.0) "sets": {"Neutral00": "Neutral10"}: as a form's
                                             // "sets" while it is worn (its own field walk and run), in its normal form and each
                                             // form with no sets of its own
    std::vector<std::wstring> Packages;      // its packages ("packages"), for the report
    bool Enabled = true;                     // "enabled"
    bool Worn = true;                        // (3.11.1) "worn": false: a choice for its characters (the Customization screen's
                                             // SKINS page), not worn until chosen there
    std::wstring Origin;                     // skins\<folder>\skin.json
};

// ---- (3.14.0) "kawaii": KawaiiPhysics' node (pafuhana1213's, MIT: 1.21's simulation) run by the mod on a model's bones --
// right after the game animates them, whatever AnimBlueprint plays them (KawaiiSolver.hpp has the simulation). The names
// are the node's properties in snake_case.

// A KawaiiPhysics curve ("damping_curve" ...): its value by the bone's length from the root bone over the chain's longest
// (0 at the root, 1 at the farthest tip), [[time, value], ...] in time order; between keys a straight line, outside them the
// first or last value; none: 1 everywhere (the node's FRuntimeFloatCurve, sampled: the editor's export writes enough keys
// for its shape).
struct KawaiiCurve
{
    std::vector<std::pair<float, float>> Keys;

    bool Empty() const { return Keys.empty(); }
    float Eval(float time, float fallback = 1.0f) const
    {
        if (Keys.empty()) { return fallback; }
        if (time <= Keys.front().first) { return Keys.front().second; }
        if (time >= Keys.back().first) { return Keys.back().second; }
        for (size_t k = 1; k < Keys.size(); ++k)
        {
            if (time > Keys[k].first) { continue; }
            const auto& [t0, v0] = Keys[k - 1];
            const auto& [t1, v1] = Keys[k];
            const float span = t1 - t0;
            return span > 0.0f ? v0 + (v1 - v0) * ((time - t0) / span) : v1;
        }
        return Keys.back().second;
    }
};

enum class KawaiiAxis : uint8_t { XPositive, XNegative, YPositive, YNegative, ZPositive, ZNegative };   // "bone_forward_axis"
enum class KawaiiPlanar : uint8_t { None, X, Y, Z };                                                    // "planar_constraint"
enum class KawaiiSpace : uint8_t { Component, World, BaseBone };                                        // "simulation_space"
// "compliance" (XPBD bone constraints): KawaiiPhysics' EXPBDComplianceType, softest last.
enum class KawaiiCompliance : uint8_t { Concrete, Wood, Leather, Tendon, Rubber, Muscle, Fat };

// A collision shape on a bone (the node's spherical, capsule, tapered capsule, box and planar limits): `Bone` its driving
// bone (a planar limit may have none: then it is in the component's space, a floor), `Offset` (cm) and `Rotation` (pitch, yaw,
// roll in degrees) in that bone's space.
struct KawaiiLimit
{
    std::wstring Bone;
    float Offset[3]{0, 0, 0};
    float Rotation[3]{0, 0, 0};
    float Radius = 5.0f;          // spheres and capsules
    float Length = 10.0f;         // capsules and tapered capsules: along the shape's Z
    float Radius0 = 5.0f;         // tapered capsules: at its +Z end
    float Radius1 = 5.0f;         //                   at its -Z end
    float Extent[3]{5, 5, 5};     // boxes: half sizes
    bool Inner = false;           // spheres: keep the bones inside it ("limit_type": "inner") rather than out of it
};

// Two bones of the chains kept at their distance (XPBD), the node's bone constraints (a skirt's neighbouring strands).
struct KawaiiBoneConstraint
{
    std::wstring Bone1, Bone2;
    bool OverrideCompliance = false;
    KawaiiCompliance Compliance = KawaiiCompliance::Leather;
    bool ExcludeFromSubdivision = false;
};

// Another root bone of the node ("additional_root_bones"), with its own exclude list when it gives one.
struct KawaiiRoot
{
    std::wstring Bone;
    bool OverrideExcludeBones = false;
    std::vector<std::wstring> ExcludeBones;
};

// (3.15.0) A wave that turns a node's bones to and fro in their pose, the place the physics pulls each one back to (so
// the chain moves on its own, the physics on top of it): a tail's sway, a wing's slow beat. Each bone turns about
// `Axis` by Degrees * sin(360 * time / Seconds + Phase - PhasePerBone * its steps from its root - PhasePerRoot * its
// chain's number - its chain's root_phases entry), times DegreesCurve at its place along the chains.
struct KawaiiWave
{
    float Axis[3]{0, 0, 1};       // "axis": the model's (+X its front, +Y its right, +Z up) at each bone, as the animation has it
    bool LocalAxis = false;       // "local_axis": true: Axis in each bone's own space instead
    float Degrees = 0.0f;         // "degrees": the turn at the wave's crest
    float Seconds = 2.0f;         // "seconds": a whole wave
    float Phase = 0.0f;           // "phase" (degrees): where in its wave it starts
    float PhasePerBone = 0.0f;    // "phase_per_bone" (degrees): each bone a step further from its root this far behind (a wave down the chain)
    float PhasePerRoot = 0.0f;    // "phase_per_root" (degrees): each chain (root_bone, then additional_root_bones in order) this far behind the one before
    std::vector<float> RootPhases;   // "root_phases" (degrees): each chain this far behind, chain by chain (added to phase_per_root's)
    KawaiiCurve DegreesCurve;     // "degrees_curve": along the chains (0 the root, 1 the end), the part of Degrees each bone turns
};

// (3.15.0) A looping key animation of a node's bones in their pose: each track a bone's local rotation (its rotation
// under its parent, x y z w) frame by frame. Additive: the turn from its first frame is added to the pose (its first
// frame changes nothing); else its rotations take the place of the pose's. Weight 0 - 1.
struct KawaiiKeyTrack
{
    std::wstring Bone;
    std::vector<std::array<float, 4>> Keys;
};
struct KawaiiPoseAnimation
{
    float Fps = 30.0f;            // "fps": the tracks' frames a second
    float Speed = 1.0f;           // "speed": how fast it plays
    float Weight = 1.0f;          // "weight"
    bool Additive = true;         // "additive"
    std::shared_ptr<const std::vector<KawaiiKeyTrack>> Tracks;   // "tracks": {"bone": [[x, y, z, w], ...], ...} (one shared copy)
    bool Active() const { return Tracks && !Tracks->empty() && Weight > 0.0f; }
};

inline constexpr size_t MaxKawaiiWaves = 8;
inline constexpr size_t MaxKawaiiKeyTracks = 256;
inline constexpr size_t MaxKawaiiKeyFrames = 6000;

// (3.17.0) KawaiiPhysics' SyncBone: an animated bone (a knee) whose move from its reference pose goes onto the pose of
// bones of the node's chains (a coat's strips over that leg), so they follow it instead of the leg going through them.
// Each frame the bone's place in the component's space less its reference pose's place, times ScaleCurveByDeltaDistance
// at that move's length and GlobalScale, only along the axes Direction lets through, moves each target's pose (each
// bone kept at its length from its parent), times its ScaleCurve by its place below its target root (0 the target root,
// 1 the farthest bone below it) and, with distance attenuation, less the farther the bone is from the synced bone.
enum class KawaiiSyncDirection : uint8_t { Both, Positive, Negative, None };   // "apply_direction_x" / "_y" / "_z"
struct KawaiiSyncTarget
{
    std::wstring Bone;                 // "bone": a bone of the node's chains
    bool IncludeChildBones = true;     // "include_child_bones": the chain's bones below it too
    KawaiiCurve ScaleCurve;            // "scale_curve_by_bone_length_rate": [[place 0 - 1, scale], ...]
};
struct KawaiiSyncBone
{
    std::wstring Bone;                 // "bone": the bone followed (one the animation moves: not a bone of the node)
    std::vector<KawaiiSyncTarget> Targets;   // "target_roots": bone names or {"bone", "include_child_bones", "scale_curve_by_bone_length_rate"}
    float GlobalScale[3]{1, 1, 1};     // "global_scale": 0 - 1 per axis of the component (+X its front, +Y its right, +Z up)
    KawaiiCurve ScaleCurveByDeltaDistance;   // "scale_curve_by_delta_distance": [[cm, scale], ...] by the move's length
    KawaiiSyncDirection Direction[3]{KawaiiSyncDirection::Both, KawaiiSyncDirection::Both, KawaiiSyncDirection::Both};
    bool DistanceAttenuation = false;  // "enable_distance_attenuation"
    float AttenuationInnerRadius = 0.0f;   // "attenuation_inner_radius" (cm): nearer than this, the whole move
    float AttenuationOuterRadius = 0.0f;   // "attenuation_outer_radius" (cm): farther, the move less max_attenuation_rate of it
    float MaxAttenuationRate = 1.0f;   // "max_attenuation_rate" 0 - 1 (1: none of the move out there)
};
inline constexpr size_t MaxKawaiiSyncBones = 16;
inline constexpr size_t MaxKawaiiSyncTargets = 64;

// (3.18.0) KawaiiPhysics' external forces (its ExternalForces: Basic, Gravity, Curve, Wind and Procedural Wind; the
// End editor's node lists them as a type and its settings, UE 4.26 has no instanced structs). Each one moves the bones
// it applies to (its bone filters) every step, in the space it is given in, times its curve by the bone's place along
// its chain.
enum class KawaiiForceType : uint8_t { Basic, Gravity, Curve, Wind, ProceduralWind };   // "type"
enum class KawaiiForceSpace : uint8_t { Component, World, Bone };                       // "external_force_space"
enum class KawaiiCurveEvaluate : uint8_t { Single, Average, Max, Min };                 // "curve_evaluate_type"
enum class KawaiiWindSource : uint8_t { Local, Shared, Auto };                          // "wind_source"
// A vector curve (the Curve force's FRuntimeVectorCurve): [[time, x, y, z], ...] in time order, straight lines between
// keys, the first or last value outside them.
struct KawaiiVectorCurve
{
    std::vector<std::array<float, 4>> Keys;
    bool Empty() const { return Keys.empty(); }
    float LastTime() const { return Keys.empty() ? 0.0f : Keys.back()[0]; }
    std::array<float, 3> Eval(float time) const
    {
        if (Keys.empty()) { return {0.0f, 0.0f, 0.0f}; }
        if (time <= Keys.front()[0]) { return {Keys.front()[1], Keys.front()[2], Keys.front()[3]}; }
        if (time >= Keys.back()[0]) { return {Keys.back()[1], Keys.back()[2], Keys.back()[3]}; }
        for (size_t k = 1; k < Keys.size(); ++k)
        {
            if (time > Keys[k][0]) { continue; }
            const auto& a = Keys[k - 1];
            const auto& b = Keys[k];
            const float span = b[0] - a[0];
            const float t = span > 0.0f ? (time - a[0]) / span : 1.0f;
            return {a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, a[3] + (b[3] - a[3]) * t};
        }
        return {Keys.back()[1], Keys.back()[2], Keys.back()[3]};
    }
};
struct KawaiiExternalForce
{
    KawaiiForceType Type = KawaiiForceType::Basic;
    bool Enabled = true;                               // "enabled" (bIsEnabled)
    std::vector<std::wstring> ApplyBoneFilter;         // "apply_bone_filter": only these bones (none: every bone)
    std::vector<std::wstring> IgnoreBoneFilter;        // "ignore_bone_filter": never these
    KawaiiForceSpace Space = KawaiiForceSpace::World;  // "external_force_space": "world", "component" or "bone" (Basic, Curve, Procedural Wind)
    float RandomForceScaleRange[2]{1, 1};              // "random_force_scale_range": [min, max], a scale drawn each frame (not Procedural Wind)
    KawaiiCurve ForceRateByBoneLengthRate;             // "force_rate_by_bone_length_rate": [[place 0 - 1, rate], ...]
    // Basic
    float ForceDir[3]{0, 0, 0};                        // "force_dir": the force (cm/s on the bones' places)
    float Interval = 0.0f;                             // "interval" (s): > 0: only once each interval
    // Gravity (a pull, in the world's space, added to the bones' speed)
    bool UseCharacterGravityDirection = false;         // "use_character_gravity_direction" (UE 5.3's custom gravity: down here)
    bool UseCharacterGravityScale = false;             // "use_character_gravity_scale": times the character's gravity (980)
    bool UseOverrideGravityDirection = false;          // "use_override_gravity_direction"
    float OverrideGravityDirection[3]{0, 0, 0};        // "override_gravity_direction"
    // Curve
    KawaiiVectorCurve ForceCurve;                      // "force_curve": [[time, x, y, z], ...] the force over time (looping)
    KawaiiCurveEvaluate CurveEvaluateType = KawaiiCurveEvaluate::Single;   // "curve_evaluate_type": single, average, max, min
    int SubstepCount = 10;                             // "substep_count": the frame's time cut in this many for average/max/min
    float TimeScale = 1.0f;                            // "time_scale" (Curve, Procedural Wind)
    // Wind (the level's wind sources) and Procedural Wind
    float WindDirectionNoiseAngle = 0.0f;              // "wind_direction_noise_angle" (degrees)
    // Procedural Wind: (constant + sway + ripple) * strength cycle + random + gust, along WindDirection
    KawaiiWindSource WindSource = KawaiiWindSource::Local;   // "wind_source": "local", "shared", "auto" (the entry's "shared_winds")
    std::wstring SharedWindTag = L"KawaiiPhysics.Shared.Default";   // "shared_wind_tag"
    float WindDirection[3]{1, 0, 0};                   // "wind_direction" (normalized; zero: +X)
    float WindDirectionNoisePeriod = 1.0f;             // "wind_direction_noise_period" (s)
    float ConstantForce = 0.0f;                        // "constant_force"
    float SwayForce = 0.0f;                            // "sway_force"
    float SwayPeriod = 1.0f;                           // "sway_period" (s)
    float SwayPhaseOffset = 0.0f;                      // "sway_phase_offset" (degrees)
    float RippleForce = 0.0f;                          // "ripple_force": a wave down the chains
    float RipplePeriod = 1.0f;                         // "ripple_period" (s)
    float RipplePhaseOffset = 0.0f;                    // "ripple_phase_offset" (degrees)
    float RippleTipPhaseDelay = 180.0f;                // "ripple_tip_phase_delay" (degrees at the chains' ends)
    float StrengthCycleRange[2]{1, 1};                 // "strength_cycle_range": [min, max] a slow swell between them
    float StrengthCyclePeriod = 10.0f;                 // "strength_cycle_period" (s)
    float StrengthCyclePhaseOffset = 0.0f;             // "strength_cycle_phase_offset" (degrees)
    float RandomForce = 0.0f;                          // "random_force": seeded smooth noise
    float RandomForcePeriod = 0.5f;                    // "random_force_period" (s)
    int Seed = 0;                                      // "seed"
    std::wstring WindPreset;                           // "wind_preset": Breeze, Strong, Storm or one of the file's "kawaii_wind_presets"
    bool IsWind() const { return Type == KawaiiForceType::ProceduralWind; }
};
inline constexpr size_t MaxKawaiiExternalForces = 16;

// (3.18.0) A KawaiiPhysics node's settings multiplier (FKawaiiPhysicsSettingsMultiplier): each physics setting times
// its factor (1: unchanged).
struct KawaiiSettingsScale
{
    float Damping = 1.0f, Stiffness = 1.0f, WorldDampingLocation = 1.0f, WorldDampingRotation = 1.0f, Radius = 1.0f, LimitAngle = 1.0f;
    bool Identity() const
    {
        return Damping == 1.0f && Stiffness == 1.0f && WorldDampingLocation == 1.0f && WorldDampingRotation == 1.0f && Radius == 1.0f && LimitAngle == 1.0f;
    }
};

// (3.18.0) Mirrored collision shapes (the node's MirrorDataTableForLimits): each shape of the node (and of its sets) on a
// bone with a mirror bone is copied onto that bone, mirrored across the model's axis.
enum class KawaiiMirrorAxis : uint8_t { None, X, Y, Z };
struct KawaiiMirror
{
    KawaiiMirrorAxis Axis = KawaiiMirrorAxis::None;    // "axis": "x", "y" (left and right: the default) or "z"
    std::vector<std::pair<std::wstring, std::wstring>> Pairs;   // "pairs": [["L_Thigh", "R_Thigh"], ...] (both ways)
    std::vector<std::pair<std::wstring, std::wstring>> Prefixes;   // "prefixes": [["L_", "R_"], ...] (both ways)
    std::vector<std::pair<std::wstring, std::wstring>> Suffixes;   // "suffixes": [["_L", "_R"], ...] (both ways)
    bool SkipExisting = true;                          // "skip_mirrored_bone_with_existing_collision"
    bool Active() const { return Axis != KawaiiMirrorAxis::None; }
};

// (3.18.0) A node's ground and level collision (SimpleWorldCollision, world collision): what it collides with outside
// the model.
struct KawaiiWorldCollision
{
    bool AllowWorldCollision = false;                  // "allow_world_collision": a sphere sweep a bone a step (a budget a frame)
    bool IgnoreSelfComponent = true;                   // "ignore_self_component"
    int MaxSweepsPerFrame = 96;                        // "world_collision_max_sweeps_per_frame" (the game's budget; past it: none)
    bool UseSimpleWorldCollision = false;              // "use_simple_world_collision": the level's simple shapes near the character
    float GatherInterval = 0.2f;                       // "simple_world_collision_gather_interval" (s)
    bool OverrideGatherRadius = false;                 // "override_simple_world_collision_gather_radius"
    float GatherRadius = 200.0f;                       // "simple_world_collision_gather_radius" (cm)
    bool GroundCollision = true;                       // "simple_world_collision_ground_collision": the floor as a box
    bool GroundOnly = false;                           // "ground_collision": the floor alone (no level shapes gathered)
};

// One KawaiiPhysics node: the bones from `RootBone` (and each additional root) down, but `ExcludeBones` and theirs, swing
// with the character's motion.
struct KawaiiNode
{
    std::wstring Name;                       // for the log ("hair"; else the root bone)
    std::wstring RootBone;
    std::vector<std::wstring> ExcludeBones;
    std::vector<KawaiiRoot> AdditionalRootBones;
    float DummyBoneLength = 0.0f;            // > 0: a bone of that length added past each end bone (it turns the end bone)
    int BoneSubdivisionCount = 0;            // 0 - 10 points put between each two bones
    bool BoneSubdivisionCollisionOnly = true;    // they only collide (placed between their bones), else they simulate
    bool BoneSubdivisionDensifyByRadius = false; // more of them where bones are far apart for their radius
    int BoneConstraintSubdivisionCount = 0;      // 0 - 10 collision points along each bone constraint
    float BoneConstraintSubdivisionFeedbackScale = 1.0f;   // 0 - 2: how much their pushes move the two bones
    KawaiiAxis BoneForwardAxis = KawaiiAxis::XPositive;
    // physics settings (the node's PhysicsSettings)
    float Damping = 0.1f;                    // 0 - 1: how fast a bone's swing dies down
    float Stiffness = 0.05f;                 // 0 - 1: how hard a bone is pulled back to its animated place
    float WorldDampingLocation = 0.8f;       // 0 - 1: how little the bones lag behind the character's moves (1: none)
    float WorldDampingRotation = 0.8f;       // 0 - 1: as that, for its turns
    float Radius = 3.0f;                     // cm: each bone's size against the collision shapes
    float LimitAngle = 0.0f;                 // degrees from its animated direction a bone may swing (0: no limit)
    KawaiiCurve DampingCurve, StiffnessCurve, WorldDampingLocationCurve, WorldDampingRotationCurve, RadiusCurve, LimitAngleCurve;
    KawaiiSpace SimulationSpace = KawaiiSpace::Component;
    std::wstring SimulationBaseBone;         // its bone, for "base_bone"
    int TargetFramerate = 60;
    bool UseFixedSubstepping = true;         // fixed steps of 1/target_framerate (KawaiiPhysics' project setting, on)
    int MaxSubsteps = 4;                     // at most this many in a frame
    bool KeepCollisionSide = false;          // (3.17.0) a bone a shape moved past in a step put back out on the side it
                                             // was on (KawaiiPhysics pushes it out the nearest way: on through)
    bool InterpolateLimitsInSubsteps = true; // (3.17.0) each step's collision shapes between the last frame's places and
                                             // this frame's, as the bones' pose (KawaiiPhysics puts them at this frame's
                                             // places for every step: a fast leg jumped past the cloth)
    int WarmUpFrames = 0;
    bool NeedWarmUp = false;                 // warm up as it starts ("warm_up": warm_up_frames steps before the first frame)
    bool UseWarmUpWhenResetDynamics = true;  // and again after a reset (a teleport the game makes)
    float TeleportDistanceThreshold = 300.0f;   // cm: a move of the character's mesh longer than this in one frame is ignored
    float TeleportRotationThreshold = 10.0f;    // degrees: as that, for a turn (0: never)
    KawaiiPlanar PlanarConstraint = KawaiiPlanar::None;
    float SkelCompMoveScale[3]{1, 1, 1};     // how much of the mesh's move the bones feel, per axis of the mesh
    std::vector<KawaiiLimit> Spheres, Capsules, TaperedCapsules, Boxes, Planes;
    // bone constraints
    KawaiiCompliance BoneConstraintGlobalCompliance = KawaiiCompliance::Leather;
    int BoneConstraintIterationsBeforeCollision = 1;
    int BoneConstraintIterationsAfterCollision = 1;
    bool AutoAddChildDummyBoneConstraint = true;
    std::vector<KawaiiBoneConstraint> BoneConstraints;
    // forces
    float Gravity[3]{0, 0, 0};               // cm/s^2 (KawaiiPhysics' default: none)
    bool UseLegacyGravity = false;
    bool UseDefaultGravityZ = false;         // gravity's length times the world's gravity (980)
    bool UseWorldSpaceGravity = true;
    float SimpleExternalForce[3]{0, 0, 0};   // cm/s added to the bones' place every second
    bool UseWorldSpaceSimpleExternalForce = true;
    // (3.14.0) bones the model's Bonamik (BNM) moves are left out of the chains ("skip_bonamik_bones": false to keep them)
    bool SkipBonamikBones = true;
    // (3.15.0) the bones' pose animated before the physics runs: "pose_waves" and "pose_animation"
    std::vector<KawaiiWave> PoseWaves;
    KawaiiPoseAnimation PoseAnimation;
    bool Animated() const { return !PoseWaves.empty() || PoseAnimation.Active(); }
    // (3.17.0) "sync_bones": animated bones whose moves the chains' pose follows
    std::vector<KawaiiSyncBone> SyncBones;
    // (3.18.0) the node's wind, external forces, sets, shared and world collision and its blend
    bool EnableWind = false;                 // "enable_wind": the level's wind sources (WindDirectionalSource)
    float WindScale = 1.0f;                  // "wind_scale"
    float WindDirectionNoiseAngle = 0.0f;    // "wind_direction_noise_angle" (degrees)
    std::vector<KawaiiExternalForce> ExternalForces;   // "external_forces"
    float Alpha = 1.0f;                      // "alpha": the node's blend (0: the pose as it was, 1: the physics)
    std::wstring Tag;                        // "kawaii_physics_tag" ("Hair.Front"): what the triggers' filter tags match
    std::vector<std::wstring> LimitsSets;    // "limits_data_asset": names of the files' "kawaii_limits_sets"
    std::vector<std::wstring> BoneConstraintsSets;   // "bone_constraints_data_asset": names of "kawaii_bone_constraints_sets"
    bool PhysicsAssetForLimits = false;      // "physics_asset_for_limits": true: the model's physics asset's bodies as shapes
    std::wstring PhysicsAssetPath;           //   or a physics asset's path (loaded in the game)
    KawaiiMirror MirrorLimits;               // "mirror_data_table_for_limits"
    bool SharedCollisionSource = false;      // "shared_collision_source": its shapes go to the character's other meshes
    bool UseSharedCollision = false;         // "use_shared_collision": it collides with them
    std::wstring SharedCollisionGroupTag = L"KawaiiPhysics.Shared.Default";   // "shared_collision_group_tag"
    KawaiiWorldCollision World;              // ground, level shapes, sweeps
    // (filled by ResolveKawaiiSets and, in the game, from the model's physics asset: the shapes and bone constraints
    // the node runs with besides its own; the export writes the set names, not these)
    std::vector<KawaiiLimit> DataSpheres, DataCapsules, DataTaperedCapsules, DataBoxes, DataPlanes;
    std::vector<KawaiiBoneConstraint> DataBoneConstraints;
    std::vector<std::pair<std::wstring, std::wstring>> ConstraintPatterns;   // the sets' "regex_pattern_list" (bone1, bone2)
    bool SetsResolved = false;
};

// (3.18.0) An animation trigger: KawaiiPhysics' AnimNotifies (Add External Force (pulse and state), Set Alpha, Settings
// Multiplier (pulse and state), Trigger Gust) for the animations the character plays in the game: by the montage the
// mesh's anim instance plays and its time in it.
enum class KawaiiTriggerKind : uint8_t { AddExternalForce, SetAlpha, SettingsMultiplier, TriggerGust, WindPreset };
struct KawaiiTrigger
{
    KawaiiTriggerKind Kind = KawaiiTriggerKind::AddExternalForce;   // "type"
    std::vector<std::wstring> Montages;      // "montage": names (case-insensitive; "Name*" every name starting so)
    bool Pulse = false;                      // "at" given: once, as the montage's time passes it; else "start" - "end"
    float At = 0.0f, Start = 0.0f, End = -1.0f;   // seconds into the montage (End < 0: to its end)
    std::vector<std::wstring> FilterTags;    // "filter_tags": the nodes whose "kawaii_physics_tag" matches (none: all)
    bool FilterExactMatch = false;           // "filter_exact_match" (false: a node tagged "Hair.Front" matches "Hair")
    std::vector<KawaiiExternalForce> Forces; // add_external_force: "external_forces"
    bool AlphaFromCurve = false;             // set_alpha: "source": "curve" (the anim instance's curve) or "constant"
    std::wstring CurveName;                  // set_alpha / settings_multiplier: "curve_name"
    float ConstantAlpha = 1.0f;              // "constant_alpha"
    float DefaultAlpha = 1.0f;               // "default_alpha_if_no_curve" / "default_weight_if_no_curve"
    KawaiiSettingsScale Scale;               // settings_multiplier: "settings_scale": {"damping": ..., ...}
    bool WeightFromCurve = false;            // settings_multiplier state: "weight_source": "envelope" or "curve"
    float Duration = 1.0f;                   // settings_multiplier pulse: "duration" (s)
    float BlendInTime = 0.2f, BlendOutTime = 0.2f;   // "blend_in_time", "blend_out_time" (pulse default out: 0.5)
    float Strength = 0.0f, RiseTime = 0.0f, HoldTime = 0.0f, DecayTime = 0.0f;   // trigger_gust
    float GustDirection[3]{0, 0, 0};         // "gust_direction" (world; zero: the node's procedural winds' own)
    bool SharedPublisher = false;            // "gust_target": "shared_publisher": the entry's shared wind (all its consumers)
    std::wstring SharedWindTag = L"KawaiiPhysics.Shared.Default";
    std::wstring Preset;                     // wind_preset: the preset applied to the nodes' procedural winds
};
inline constexpr size_t MaxKawaiiTriggers = 128;

// (3.18.0) An entry's own wind source ("world_wind"), for the nodes' "enable_wind" and their "wind" forces where the level
// has no WindDirectionalSource of its own: a directional source as UE's (its direction in the world, its speed, its
// gusts, its strength the weight it has when it is mixed with the level's).
struct KawaiiWorldWind
{
    bool Enabled = false;
    bool OnlyWithoutLevelWind = true;        // "only_without_level_wind": false: mixed with the level's sources too
    float Direction[3]{1, 0, 0};             // "direction" (world, normalized; zero: +X)
    float Speed = 0.0f;                      // "speed" (cm/s, UE's WindDirectionalSourceComponent.Speed)
    float Strength = 1.0f;                   // "strength"
    float MinGustAmount = 0.0f, MaxGustAmount = 0.0f;   // "min_gust_amount", "max_gust_amount"
};

// (3.18.0) A shared wind (KawaiiPhysics' Shared Publisher): a procedural wind whose settings, time and gusts every
// procedural wind of the character's meshes with "wind_source" "shared" (or "auto") and its tag uses.
struct KawaiiSharedWind
{
    std::wstring Tag = L"KawaiiPhysics.Shared.Default";   // "shared_wind_tag"
    bool Enabled = true;
    KawaiiExternalForce Wind;                // its procedural wind settings
};

// A "kawaii" entry: its nodes, on every mesh showing one of its models (in battle and in the field, on any character).
struct KawaiiSet
{
    std::vector<std::wstring> Models;        // "models" / "model": object paths ("/Game/.../PC0010_13.PC0010_13"); one ending
                                             // in * stands for every model whose path starts with the rest
    std::vector<std::wstring> RequiresPaks;
    std::vector<KawaiiNode> Nodes;
    bool DisableBonamik = false;             // "disable_bonamik": the model's Bonamik (its BNMs, run by the character's
                                             // SQEX_KBD_Component) is off while it shows the model (KawaiiPhysics moves those
                                             // bones instead), on again when the model goes: true, every BNM of the model;
    std::vector<std::wstring> DisableBonamikAssets;   // or a list of its BNMs' names ("PC0010_13_BNM"): only those (the
                                             // others, a wing's, keep running; their bones are left out of the chains)
    bool DisableKineDriver = false;          // (3.14.5) "disable_kinedriver": the model's KineDriver (its KDIs: the
                                             // SQEX_KBD_Component's KineDriverDataList and PostKineDriverDataList, which
                                             // write hair, collar and wing bones and the joints' helper bones after the
                                             // nodes) taken off the model as it loads: true, every KDI of the model;
    std::vector<std::wstring> DisableKineDriverAssets;   // or a list of its KDIs' names ("PC0010_00_KDI_Extra1"): only those
    std::vector<KawaiiTrigger> Triggers;     // (3.18.0) "animation_triggers"
    std::vector<KawaiiSharedWind> SharedWinds;   // (3.18.0) "shared_winds"
    KawaiiWorldWind WorldWind;               // (3.18.0) "world_wind": a wind source of the entry's own (the level's
                                             // wind sources first: where the level has none, this one)
    std::wstring Origin;
};

// (3.18.0) The files' reusable sets (KawaiiPhysics' data assets, by name): "kawaii_limits_sets" (LimitsDataAsset: shapes),
// "kawaii_bone_constraints_sets" (BoneConstraintsDataAsset: bone constraints and regex patterns), "kawaii_presets"
// (PresetDataAsset: node settings) and "kawaii_wind_presets" (WindPresetDataAsset: procedural wind settings).
struct KawaiiLimitsSet
{
    std::wstring Name, Origin;
    std::vector<KawaiiLimit> Spheres, Capsules, TaperedCapsules, Boxes, Planes;
};
struct KawaiiConstraintsSet
{
    std::wstring Name, Origin;
    std::vector<KawaiiBoneConstraint> Constraints;
    std::vector<std::pair<std::wstring, std::wstring>> Patterns;   // "regex_pattern_list": [["bone1 regex", "bone2 regex"], ...]
};
struct KawaiiWindPreset
{
    std::wstring Name;
    float ConstantForce = 2.0f, SwayForce = 1.0f, SwayPeriod = 2.0f, RippleForce = 1.0f, RipplePeriod = 1.5f, RippleTipPhaseDelay = 90.0f;
    float StrengthCycleRange[2]{0.6f, 1.0f};
    float StrengthCyclePeriod = 20.0f, RandomForce = 0.5f, RandomForcePeriod = 0.8f, WindDirectionNoiseAngle = 5.0f;
};

inline constexpr size_t MaxKawaiiNodes = 64;   // (3.14.2: 16 before; a node a chain, each with its own settings)
inline constexpr size_t MaxKawaiiLimits = 64;
inline constexpr size_t MaxKawaiiCurveKeys = 64;
inline constexpr size_t MaxKawaiiBoneConstraints = 512;
inline constexpr size_t MaxKawaiiRoots = 32;

// ---------------------------------------------------------------------------------------
// 3.16.0 "characters": a character of its own that takes another's place in the party ("slot": "Cloud"), picked on the
// Customization screen's CHARACTER page (one at a time per place; the place's own is the default). While it has the
// place, the game's tables are as the character has them (the mod's copies of them, in the game's place):
//   * "charaspecs": {"the place's CharaSpec row": "the character's own row", ...}: the rows the game spawns, wherever
//     the tables of "names_in" name them (by default PlayerTable's PlayerCharaSpec_Array, EventCharaSpec_Array and
//     ChangeWeaponCharaSpec_Array, PlannerEventChara's CharaSpecName, BikeCharaSpec's RiderCharaSpecID_Array and
//     Equipment's CharaSpecID_Array: the party, events, rides and weapons);
//   * "rows": [{"table": "BattlePlayerParameter", "row": "pt_Cloud", "from": "pt_Cloud_CACS", "keep": [fields]}]: a
//     row with another row's content, but for the "keep" fields (an ability's UniqueId: the save keeps its progress
//     under it);
//   * "values": [{"table": "PlannerEvent", "rows": [...], "field": "VoicePack", "value": "VO_PC0000_00_Cloud"}]: a field
//     of rows set (a name, a text, a number, or a list of names).
// "player": its BattlePlayerParameter row (default: the "rows" entry of that table); a compat row's "abilities" for that
// player row stand down while the character has the place. "requires_paks": as a row's. A table is a table's name
// ("PlayerTable": /Game/DataObject/Resident/PlayerTable) or a data object's object path.
// ---------------------------------------------------------------------------------------
struct CharacterNamesIn
{
    std::wstring Table;
    std::vector<std::wstring> Fields;
};

struct CharacterRowCopy
{
    std::wstring Table, Row, From;
    std::vector<std::wstring> Keep;
};

struct CharacterValue
{
    enum class Kind
    {
        Text,     // a name or a text (the field's type decides)
        Number,
        List      // a list of names
    };
    std::wstring Table, Field;
    std::vector<std::wstring> Rows;
    Kind Is = Kind::Text;
    std::wstring Text;
    double Number = 0.0;
    std::vector<std::wstring> List;
};

struct Character
{
    std::wstring Name;                                          // shown ("CLOUD")
    std::wstring Slot;                                          // whose place it takes ("Cloud")
    std::wstring Player;                                        // its BattlePlayerParameter row ("pt_Cloud")
    std::wstring Note;                                          // a line about it (the screen's detail)
    std::vector<std::pair<std::wstring, std::wstring>> Specs;   // the place's CharaSpec row -> its own
    std::vector<CharacterNamesIn> NamesIn;
    bool DefaultNamesIn = false;                                // NamesIn is DefaultCharacterNamesIn (the file gave none)
    std::vector<CharacterRowCopy> Rows;
    std::vector<CharacterValue> Values;
    std::vector<std::wstring> RequiresPaks;
    std::wstring Origin;
};

// The game's tables that name the CharaSpec rows it spawns for a party member ("names_in" when a character gives none).
inline const std::vector<CharacterNamesIn>& DefaultCharacterNamesIn()
{
    static const std::vector<CharacterNamesIn> list{
        {L"PlayerTable", {L"PlayerCharaSpec_Array", L"EventCharaSpec_Array", L"ChangeWeaponCharaSpec_Array"}},
        {L"PlannerEventChara", {L"CharaSpecName"}},
        {L"BikeCharaSpec", {L"RiderCharaSpecID_Array"}},
        {L"Equipment", {L"CharaSpecID_Array"}}};
    return list;
}

// A "characters" table: "PlayerTable" -> /Game/DataObject/Resident/PlayerTable.PlayerTable; a path: its object path, one
// of the game's data objects (under /Game/DataObject/). Empty: neither.
inline std::wstring DataTablePath(std::wstring_view table)
{
    const std::wstring text = Trim(std::wstring(table));
    if (text.empty()) { return {}; }
    if (text.find(L'/') != std::wstring::npos)
    {
        std::wstring path = NormalizeObjectPath(text);
        return StartsWithFolded(path, L"/Game/DataObject/") ? path : std::wstring{};
    }
    if (!IsRowName(text)) { return {}; }
    return L"/Game/DataObject/Resident/" + text + L"." + text;
}

// (3.16.0) Whether a table a character changes may be left out when the game has not loaded it: one of the default
// "names_in" tables (the file gave none) but the party's (PlayerTable), and none of its "rows" or "values" (events,
// rides, weapons name the place's CharaSpec rows there; the party spawns from PlayerTable). Every other table it changes
// is needed: it plays with all of them or not at all.
inline bool CharacterTableOptional(const Character& c, std::wstring_view path)
{
    if (!c.DefaultNamesIn || PathEquals(path, DataTablePath(L"PlayerTable"))) { return false; }
    for (const auto& r : c.Rows)
    {
        if (PathEquals(r.Table, path)) { return false; }
    }
    for (const auto& v : c.Values)
    {
        if (PathEquals(v.Table, path)) { return false; }
    }
    return std::any_of(c.NamesIn.begin(), c.NamesIn.end(), [&](const CharacterNamesIn& n) { return PathEquals(n.Table, path); });
}

struct Config
{
    std::vector<Pair> Pairs;
    std::vector<AnimSetRow> AnimSets;  // one row per character after FinishConfig
    std::vector<Skin> Skins;           // 3.10.0: the skins (in folder order)
    std::vector<KawaiiSet> Kawaii;     // 3.14.0: "kawaii" entries (after FinishConfig: those whose paks are installed)
    std::vector<KawaiiLimitsSet> KawaiiLimitsSets;           // 3.18.0: the files' reusable sets (ResolveKawaiiSets puts
    std::vector<KawaiiConstraintsSet> KawaiiConstraintsSets; // them on the nodes naming them, in FinishConfig)
    std::vector<std::pair<std::wstring, Json>> KawaiiPresets;// 3.18.0: "kawaii_presets" (node settings by name; a node's
                                                             // "preset" starts from one: the files read before it)
    std::vector<KawaiiWindPreset> KawaiiWindPresets;         // 3.18.0: "kawaii_wind_presets"
    std::vector<Character> Characters; // 3.16.0: "characters" (after FinishConfig: those whose paks are installed)
    std::vector<std::wstring> Messages;
    // 3.6.7: "proportions" also in cutscenes (Rebirth's cutscene animations skip translation retargeting:
    // UAnimSequence::bIgnoreTranslationRetargeting; the mod clears it on the ones the proportions are for). A file's
    // top-level "cutscene_proportions": false turns that off (the cutscenes play as they did before).
    bool CutsceneProportions = true;

    // Row for a CharaSpec pack (object path, case-insensitive).
    const AnimSetRow* FindAnimSetRow(std::wstring_view packPath) const
    {
        for (const auto& row : AnimSets)
        {
            for (const auto& character : row.Characters)
            {
                if (PathEquals(character, packPath)) { return &row; }
            }
        }
        return nullptr;
    }

    // Socket stand-ins for meshes of a character's own skeleton (rows naming that "skeleton" and "sockets").
    std::vector<std::pair<std::wstring, std::wstring>> SocketAliasesFor(std::wstring_view skeletonPath) const
    {
        std::vector<std::pair<std::wstring, std::wstring>> out;
        for (const auto& row : AnimSets)
        {
            if (row.Skeleton.empty() || !PathEquals(row.Skeleton, skeletonPath)) { continue; }
            for (const auto& alias : row.Sockets)
            {
                if (std::none_of(out.begin(), out.end(), [&](const auto& a) { return NameEquals(a.first, alias.first); })) { out.push_back(alias); }
            }
        }
        return out;
    }

    // 3.8.1: the placement a row gives a socket stand-in (SocketAliasesFor) of a character's own skeleton, from the row that
    // made it; false: the stand-in keeps what it copies (the socket it names, or nothing on a bone).
    bool SocketPlacementFor(std::wstring_view skeletonPath, std::wstring_view socket, SocketPlacement& placement) const
    {
        for (const auto& row : AnimSets)
        {
            if (row.Skeleton.empty() || !PathEquals(row.Skeleton, skeletonPath)) { continue; }
            if (std::none_of(row.Sockets.begin(), row.Sockets.end(), [&](const auto& a) { return NameEquals(a.first, socket); })) { continue; }
            // (the first row with this stand-in made it: its placement, if it gave one)
            for (const auto& [name, value] : row.SocketPlacements)
            {
                if (NameEquals(name, socket))
                {
                    placement = value;
                    return true;
                }
            }
            return false;
        }
        return false;
    }

    // Skeletons whose bones get the proportion modes (ProportionModes): the receiving skeleton of every "animations"
    // pair (a family's hub) and the animation skeletons of every "mesh" pair outside a family, with "proportions" on.
    std::vector<std::wstring> ProportionSkeletons() const
    {
        std::vector<std::wstring> out;
        const auto add = [&](const std::wstring& path) {
            if (!path.empty() && std::none_of(out.begin(), out.end(), [&](const std::wstring& p) { return PathEquals(p, path); })) { out.push_back(path); }
        };
        for (const auto& p : Pairs)
        {
            if (!p.KeepProportions) { continue; }
            if (p.Use == Method::Animations) { add(p.Receiving); }
            else if (p.Use == Method::Mesh && p.FamilyHub.empty()) { for (const auto& a : p.Animation) { add(a); } }
        }
        return out;
    }

    // (3.8.2) "proportion_bones" patterns for one of ProportionSkeletons(): those of every pair that gives it the modes.
    std::vector<std::wstring> ProportionBonesOf(std::wstring_view skeletonPath) const
    {
        std::vector<std::wstring> out;
        const auto add = [&](const Pair& p) {
            for (const auto& b : p.ProportionBones)
            {
                if (std::none_of(out.begin(), out.end(), [&](const std::wstring& o) { return NameEquals(o, b); })) { out.push_back(b); }
            }
        };
        for (const auto& p : Pairs)
        {
            if (!p.KeepProportions || p.ProportionBones.empty()) { continue; }
            if (p.Use == Method::Animations && PathEquals(p.Receiving, skeletonPath)) { add(p); }
            else if (p.Use == Method::Mesh && p.FamilyHub.empty() &&
                     std::any_of(p.Animation.begin(), p.Animation.end(), [&](const std::wstring& a) { return PathEquals(a, skeletonPath); })) { add(p); }
        }
        return out;
    }

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

// (3.8.2) A name (case-insensitive) once.
inline void AddUniqueName(std::vector<std::wstring>& list, const std::wstring& name)
{
    if (std::none_of(list.begin(), list.end(), [&](const std::wstring& n) { return NameEquals(n, name); })) { list.push_back(name); }
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

// A string, or every item of an array (anything else: none, `ok` false).
inline std::vector<const Json*> Items(const Json* value, bool& ok)
{
    std::vector<const Json*> items;
    if (!value) { return items; }
    if (value->type == Json::Type::Array) { for (const auto& item : value->array) { items.push_back(&item); } }
    else if (value->type == Json::Type::String || value->type == Json::Type::Object) { items.push_back(value); }
    else { ok = false; }
    return items;
}

// "requires_paks" / "requires_pak": names added to `out`; false when an entry was unusable.
inline bool PakNames(const Json& entry, std::vector<std::wstring>& out)
{
    bool usable = true;
    for (const char* key : {"requires_paks", "requires_pak"})
    {
        for (const Json* item : Items(entry.Find(key), usable))
        {
            const std::wstring name = item->type == Json::Type::String ? PakStem(Widen(item->string)) : std::wstring{};
            if (name.empty()) { usable = false; continue; }
            if (std::none_of(out.begin(), out.end(), [&](const std::wstring& n) { return NameEquals(n, name); })) { out.push_back(name); }
        }
    }
    return usable;
}

inline bool SameSource(const SetSource& a, const SetSource& b) { return a.Folder == b.Folder && PathEquals(a.Path, b.Path) && NameEquals(a.As, b.As); }

// How much of a source an auto match takes: Off < Basic < Attacks < All.
inline int AutoWidth(AutoMatchMode mode)
{
    switch (mode)
    {
    case AutoMatchMode::Basic: return 1;
    case AutoMatchMode::Attacks: return 2;
    case AutoMatchMode::All: return 3;
    default: return 0;
    }
}

// Adds a source unless the list has it; a source listed again with a wider auto match widens the earlier entry.
inline void AddSource(std::vector<SetSource>& list, const SetSource& source)
{
    for (auto& existing : list)
    {
        if (!SameSource(existing, source)) { continue; }
        if (AutoWidth(source.Auto) > AutoWidth(existing.Auto)) { existing.Auto = source.Auto; }
        // Name filters: listed again without one takes every name; with one, either list's words count.
        if (existing.Only.empty() || source.Only.empty()) { existing.Only.clear(); }
        else
        {
            for (const auto& word : source.Only)
            {
                if (std::none_of(existing.Only.begin(), existing.Only.end(), [&](const std::wstring& w) { return NameEquals(w, word); })) { existing.Only.push_back(word); }
            }
        }
        return;
    }
    list.push_back(source);
}

inline std::wstring StringOf(const Json* value) { return value && value->type == Json::Type::String ? Trim(Widen(value->string)) : std::wstring{}; }

// "auto" / "match": true, "attacks" or "auto" -> Attacks; "basic" -> Basic; "all" (the whole set) -> All; false or "off" -> Off.
inline bool ParseAutoMatch(const Json& value, AutoMatchMode& out)
{
    if (value.type == Json::Type::Bool)
    {
        out = value.boolean ? AutoMatchMode::Attacks : AutoMatchMode::Off;
        return true;
    }
    if (value.type != Json::Type::String) { return false; }
    const std::wstring v = FoldedKey(Trim(Widen(value.string)));
    if (v == L"attacks" || v == L"attack" || v == L"auto" || v == L"true" || v == L"yes" || v == L"on")
    {
        out = AutoMatchMode::Attacks;
        return true;
    }
    if (v == L"all" || v == L"everything" || v == L"animset" || v == L"set" || v == L"whole")
    {
        out = AutoMatchMode::All;
        return true;
    }
    if (v == L"basic" || v == L"basic_attacks" || v == L"combo" || v == L"normal")
    {
        out = AutoMatchMode::Basic;
        return true;
    }
    if (v == L"off" || v == L"none" || v == L"false" || v == L"no" || v.empty())
    {
        out = AutoMatchMode::Off;
        return true;
    }
    return false;
}

// "proportions" / "keep_proportions" on a pair, family or row: true, false, or absent (`fallback`).
inline bool ProportionsOf(const Json& entry, bool fallback)
{
    bool out = fallback;
    for (const char* key : {"proportions", "keep_proportions"})
    {
        if (const Json* value = entry.Find(key); value && value->type == Json::Type::Bool) { out = value->boolean; }
    }
    return out;
}

// 3.3 "player" and "abilities" of a row:
//   "player": "pt_Cloud",
//   "abilities": [{"pack": "Battle00", "commands": ["PC0010_AtkBurst01"], "limits": ["PC0010_Limit001"]},
//                 {"pack": "Battle02", "commands": [...]}]
// or an object by pack: {"Battle02": {"commands": [...], "limits": [...]}, "Battle03": ["...commands..."]}.
inline void ParseAbilities(const Json& entry, std::wstring_view origin, const std::wstring& where, Config& cfg, AnimSetRow& row)
{
    for (const char* key : {"player", "player_parameter", "battle_player_parameter"})
    {
        if (!row.Player.empty()) { break; }
        if (const Json* value = entry.Find(key))
        {
            const std::wstring name = StringOf(value);
            if (IsRowName(name)) { row.Player = name; }
            else { Note(cfg, origin, where + L" " + Widen(key) + L" must be a BattlePlayerParameter row like \"pt_Cloud\"; ignored"); }
        }
    }
    {
        std::wstring bad;
        if (!StringList(entry.Find("pack_assets"), row.PackAssets, bad))
        {
            Note(cfg, origin, where + L" pack_assets: entries must be object paths like /Game/Effect/Character/Player/X/Build/X_Effect__Pack (" + bad +
                                  L"); ignored");
            row.PackAssets.clear();
        }
        bad.clear();
        if (!StringList(entry.Find("preload"), row.Preload, bad))
        {
            Note(cfg, origin, where + L" preload: entries must be object paths like /Game/DataAsset/Game/CharaSpec/CharaSpec_X (" + bad + L"); ignored");
            row.Preload.clear();
        }
    }
    if (const Json* refresh = entry.Find("refresh_abilities"))
    {
        if (refresh->type == Json::Type::Bool) { row.RefreshAbilities = refresh->boolean; }
        else { Note(cfg, origin, where + L" refresh_abilities must be true or false; ignored"); }
    }
    // 3.9.3 "ability_pages"
    if (const Json* pages = entry.Find("ability_pages"))
    {
        AbilityPagesSettings& p = row.Pages;
        p.Set = true;
        if (pages->type == Json::Type::Bool) { p.On = pages->boolean; }
        else if (pages->type == Json::Type::Object)
        {
            p.On = true;
            if (const Json* on = pages->Find("on"); on && on->type == Json::Type::Bool) { p.On = on->boolean; }
            const auto button = [&](std::initializer_list<const char*> keys, Shooter::Button& out) {
                for (const char* key : keys)
                {
                    const Json* value = pages->Find(key);
                    if (!value) { continue; }
                    const Shooter::Button b = Shooter::ButtonOf(StringOf(value));
                    if (b == Shooter::Button::None)
                    {
                        Note(cfg, origin, where + L" ability_pages " + Widen(key) + L" must be a button like \"L1\" or \"Gamepad_LeftShoulder\"; the default kept");
                    }
                    else { out = b; }
                    return;
                }
            };
            button({"previous", "prev", "back"}, p.Previous);
            button({"next", "forward"}, p.Next);
            if (p.Previous == p.Next)
            {
                Note(cfg, origin, where + L" ability_pages: previous and next are the same button; L1 / R1 used");
                p.Previous = Shooter::Button::L1;
                p.Next = Shooter::Button::R1;
            }
            if (const Json* refresh = pages->Find("refresh"))
            {
                const std::wstring v = StringOf(refresh);
                if (NameEquals(v, L"now") || NameEquals(v, L"open")) { p.RefreshNow = true; }
                else if (NameEquals(v, L"close") || NameEquals(v, L"closed") || NameEquals(v, L"later")) { p.RefreshNow = false; }
                else { Note(cfg, origin, where + L" ability_pages refresh must be \"now\" or \"close\"; \"now\" kept"); }
            }
            for (const auto& [key, out] : {std::pair<const char*, float*>{"x", &p.X}, std::pair<const char*, float*>{"y", &p.Y}})
            {
                const Json* value = pages->Find(key);
                if (value && value->type == Json::Type::Number && std::isfinite(value->number)) { *out = static_cast<float>(value->number); }
            }
        }
        else { Note(cfg, origin, where + L" ability_pages must be true, false or an object like {\"previous\": \"L1\", \"next\": \"R1\"}; ignored"); }
    }
    const Json* abilities = entry.Find("abilities");
    if (!abilities) { return; }
    bool ok = abilities->type == Json::Type::Array || abilities->type == Json::Type::Object;
    const auto names = [&](const Json* value, std::vector<std::wstring>& out, bool& given) {
        if (!value) { return; }
        given = true;
        bool listOk = true;
        for (const Json* item : Items(value, listOk))
        {
            const std::wstring name = StringOf(item);
            if (!IsRowName(name)) { listOk = false; continue; }
            if (std::any_of(out.begin(), out.end(), [&](const std::wstring& n) { return NameEquals(n, name); }))
            {
                Note(cfg, origin, where + L" abilities: " + name + L" is listed twice in one list; the first one is kept");
                continue;
            }
            out.push_back(name);
        }
        if (!listOk) { ok = false; }
    };
    // 3.4 "weapon_abilities": {"PC0000_AtkBurst02": "PC0010_T_Blizzaga", ...}, or [["PC0000_AtkBurst02", "PC0010_T_Blizzaga"], ...],
    // or [{"weapon": "PC0000_AtkBurst02", "ability": "PC0010_T_Blizzaga"}, ...].
    const auto weaponList = [&](const Json* value, PackAbilities& one) {
        if (!value) { return; }
        one.HasWeapons = true;
        bool listOk = true;
        const auto pair = [&](const std::wstring& weapon, const std::wstring& ability) {
            if (!IsRowName(weapon) || !IsRowName(ability))
            {
                listOk = false;
                return;
            }
            if (std::any_of(one.Weapons.begin(), one.Weapons.end(), [&](const auto& p) { return NameEquals(p.first, weapon); }))
            {
                Note(cfg, origin, where + L" abilities: pack " + one.Pack + L" weapon_abilities lists " + weapon + L" twice; the first one is kept");
                return;
            }
            one.Weapons.emplace_back(weapon, ability);
        };
        if (value->type == Json::Type::Object)
        {
            for (const auto& [weapon, ability] : value->object) { pair(Trim(Widen(weapon)), StringOf(&ability)); }
        }
        else if (value->type == Json::Type::Array)
        {
            for (const auto& item : value->array)
            {
                if (item.type == Json::Type::Array && item.array.size() == 2) { pair(StringOf(&item.array[0]), StringOf(&item.array[1])); }
                else if (item.type == Json::Type::Object)
                {
                    std::wstring weapon = StringOf(item.Find("weapon"));
                    if (weapon.empty()) { weapon = StringOf(item.Find("from")); }
                    std::wstring ability = StringOf(item.Find("ability"));
                    if (ability.empty()) { ability = StringOf(item.Find("to")); }
                    pair(weapon, ability);
                }
                else { listOk = false; }
            }
        }
        else { listOk = false; }
        if (!listOk)
        {
            Note(cfg, origin, where + L" abilities: pack " + one.Pack + L" weapon_abilities must map the ability a weapon gives to a BattleAbility row, "
                                  L"like {\"PC0000_AtkBurst02\": \"PC0010_T_Blizzaga\"}; bad entries ignored");
        }
    };
    const auto add = [&](std::wstring pack, const Json* value) {
        pack = Trim(pack);
        if (!value || pack.empty() || pack.find_first_of(L"/.: ") != std::wstring::npos) { ok = false; return; }
        PackAbilities one;
        one.Pack = pack;
        if (value->type == Json::Type::Array || value->type == Json::Type::String) { names(value, one.Commands, one.HasCommands); }
        else if (value->type == Json::Type::Object)
        {
            const Json* commands = value->Find("commands");
            if (!commands) { commands = value->Find("command"); }
            if (!commands) { commands = value->Find("atb"); }
            const Json* limits = value->Find("limits");
            if (!limits) { limits = value->Find("limit"); }
            if (!limits) { limits = value->Find("limit_breaks"); }
            const Json* weapons = value->Find("weapon_abilities");
            if (!weapons) { weapons = value->Find("weapons"); }
            names(commands, one.Commands, one.HasCommands);
            names(limits, one.Limits, one.HasLimits);
            weaponList(weapons, one);
        }
        else { ok = false; return; }
        if (!one.HasCommands && !one.HasLimits && !one.HasWeapons) { ok = false; return; }
        if (std::any_of(row.Abilities.begin(), row.Abilities.end(), [&](const PackAbilities& a) { return NameEquals(a.Pack, one.Pack); }))
        {
            Note(cfg, origin, where + L" abilities: pack " + one.Pack + L" is listed twice; the first one is kept");
            return;
        }
        for (const bool limits : {false, true})
        {
            const size_t count = (limits ? one.Limits : one.Commands).size();
            const size_t most = limits ? MaxLimitAbilities : MaxCommandAbilities;
            if (count > most && !limits && row.Pages.On)
            {
                Note(cfg, origin, where + L" abilities: pack " + one.Pack + L" lists " + std::to_wstring(count) + L" commands: the game shows " +
                                      std::to_wstring(most) + L" from a player row, so they go on " + std::to_wstring((count + most - 1) / most) +
                                      L" pages (" + ButtonLabelOf(row.Pages.Previous) + L" / " + ButtonLabelOf(row.Pages.Next) + L" in the battle menu)");
            }
            else if (count > most)
            {
                Note(cfg, origin, where + L" abilities: pack " + one.Pack + L" lists " + std::to_wstring(count) + (limits ? L" limits" : L" commands") +
                                      L"; the game takes the first " + std::to_wstring(most) + L" from a player row, the rest are left out");
            }
        }
        row.Abilities.push_back(std::move(one));
    };
    if (abilities->type == Json::Type::Array)
    {
        for (const auto& item : abilities->array)
        {
            if (item.type != Json::Type::Object) { ok = false; continue; }
            std::wstring pack = StringOf(item.Find("pack"));
            if (pack.empty()) { pack = StringOf(item.Find("set")); }
            if (pack.empty()) { pack = StringOf(item.Find("form")); }
            add(pack, &item);
        }
    }
    else if (abilities->type == Json::Type::Object)
    {
        for (const auto& [pack, value] : abilities->object) { add(Widen(pack), &value); }
    }
    if (!ok)
    {
        Note(cfg, origin, where + L" abilities: entries must look like {\"pack\": \"Battle02\", \"commands\": [\"PC0010_AtkBurst01\"], \"limits\": "
                              L"[\"PC0010_Limit001\"], \"weapon_abilities\": {\"PC0000_AtkBurst02\": \"PC0010_T_Blizzaga\"}} (BattleAbility rows); bad entries ignored");
    }
    if (!row.Abilities.empty() && row.Player.empty())
    {
        Note(cfg, origin, where + L" abilities need the character's \"player\" row (its BattlePlayerParameter row, like \"pt_Cloud\"); ignored");
        row.Abilities.clear();
    }
}

// A number (false when absent or not a number).
inline bool NumberOf(const Json* value, float& out)
{
    if (!value || value->type != Json::Type::Number || !std::isfinite(value->number)) { return false; }
    out = static_cast<float>(value->number);
    return true;
}

// A socket, bone, material slot or input key name: no spaces, quotes or path characters.
inline bool IsPlainName(std::wstring_view name)
{
    return !name.empty() && name.size() <= 128 && name.find_first_of(L"/.:'\" \\{}") == std::wstring_view::npos;
}

// 3.6 effects of a form: a path, or {"effect": path, "socket": "R_Hand_a", "scale": 1.0, "seconds": 2.5} (or an array).
inline bool ParseFormEffects(const Json* value, std::vector<FormEffect>& out)
{
    bool ok = true;
    for (const Json* item : Items(value, ok))
    {
        FormEffect effect;
        if (item->type == Json::Type::String) { effect.Path = NormalizeObjectPath(Widen(item->string)); }
        else
        {
            for (const char* k : {"effect", "path", "system", "particle"})
            {
                if (effect.Path.empty()) { effect.Path = NormalizeObjectPath(StringOf(item->Find(k))); }
            }
            effect.Socket = StringOf(item->Find("socket"));
            if (effect.Socket.empty()) { effect.Socket = StringOf(item->Find("bone")); }
            NumberOf(item->Find("scale"), effect.Scale);
            NumberOf(item->Find("seconds"), effect.Seconds);
        }
        if (effect.Path.empty() || (!effect.Socket.empty() && !IsPlainName(effect.Socket)) || !(effect.Scale > 0.0f) || effect.Seconds < 0.0f)
        {
            ok = false;
            continue;
        }
        out.push_back(std::move(effect));
    }
    return ok;
}

// 3.6 sounds of a form: {"bank": path, "cue": "SE_..."} or {"voice": "/Game/Sound/Voice/{language}/...", "cue": "Atk_..."}.
// Reads "voice" (a bank path, "own", or {"bank", "replaces"}). False: not one of those (`out` unchanged).
inline bool ParseVoice(const Json* value, Voice& out)
{
    if (!value) { return true; }
    Voice v;
    v.Set = true;
    if (value->type == Json::Type::String)
    {
        const std::wstring text = Trim(Widen(value->string));
        if (text.empty() || NameEquals(text, L"own") || NameEquals(text, L"none")) { v.Own = true; }
        else
        {
            v.Bank = VoiceSourcePath(text);
            if (v.Bank.empty()) { return false; }
        }
        out = std::move(v);
        return true;
    }
    if (value->type != Json::Type::Object) { return false; }
    const std::wstring bank = StringOf(value->Find("bank"));
    if (bank.empty() || NameEquals(bank, L"own")) { v.Own = true; }
    else
    {
        v.Bank = VoiceSourcePath(bank);
        if (v.Bank.empty()) { return false; }
    }
    bool ok = true;
    for (const Json* item : Items(value->Find("replaces"), ok))
    {
        const std::wstring path = VoiceSourcePath(StringOf(item));
        if (path.empty()) { ok = false; continue; }
        if (std::none_of(v.Replaces.begin(), v.Replaces.end(), [&](const std::wstring& r) { return PathEquals(r, path); })) { v.Replaces.push_back(path); }
    }
    if (!ok) { return false; }
    out = std::move(v);
    return true;
}

inline bool ParseFormSounds(const Json* value, std::vector<FormSound>& out)
{
    bool ok = true;
    for (const Json* item : Items(value, ok))
    {
        if (item->type != Json::Type::Object) { ok = false; continue; }
        FormSound sound;
        for (const char* k : {"bank", "voice"})
        {
            if (sound.Bank.empty()) { sound.Bank = StringOf(item->Find(k)); }
        }
        sound.Bank = NormalizeObjectPath(sound.Bank);
        for (const char* k : {"cue", "name", "sound"})
        {
            if (sound.Cue.empty()) { sound.Cue = StringOf(item->Find(k)); }
        }
        if (sound.Bank.empty() || !IsPlainName(sound.Cue)) { ok = false; continue; }
        // (3.7.1) a slice of it: "start" (seconds into it), "length" (seconds it plays), "volume"
        const auto number = [&](const char* key, float& field, float lo, float hi) {
            const Json* v = item->Find(key);
            if (!v) { return; }
            float n = 0.0f;
            if (!NumberOf(v, n) || !std::isfinite(n) || n < lo || n > hi) { ok = false; return; }
            field = n;
        };
        number("start", sound.Start, 0.0f, 3600.0f);
        for (const char* k : {"length", "seconds"}) { number(k, sound.Length, 0.0f, 600.0f); }
        number("volume", sound.Volume, 0.0f, 4.0f);
        out.push_back(std::move(sound));
    }
    return ok;
}

// 3.6.7 an entrance's "shots": [{"name": "C0160", "seconds": 9.4, "before_switch": false, "animation": path,
// "animation_start": 0, "rate": 1, "scale": 1, "flash": 0, "flash_color": [1, 1, 1],
// "camera": [[t, forward, right, up, pitch, yaw, roll, fov], ...],
// "effects": [{"effect": path, "at": 0.5, "seconds": 2, "socket": "C_Spine_c"} or {..., "offset": [forward, right, up], "yaw": 0}],
// "sounds": [{"bank": path (or "voice": a {language} path), "cue": "...", "at": 1.2, "start": 0, "stop_at_end": false}]}, ...].
// A bad shot is left out, a bad key, effect or sound of a shot too; `why` says what.
inline void ParseEntranceShots(const Json* value, std::vector<EntranceShot>& out, std::wstring& why)
{
    const auto bad = [&](const std::wstring& what) { why += (why.empty() ? L"" : L"; ") + what; };
    if (!value) { return; }
    if (value->type != Json::Type::Array)
    {
        bad(L"shots must be an array of shots like {\"seconds\": 4, \"camera\": [[0, 300, 0, 120, -10, 180, 0, 50]]}");
        return;
    }
    const auto number = [&](const Json* item, float& field, float lo, float hi, const std::wstring& what) {
        if (!item) { return true; }
        float n = 0.0f;
        if (!NumberOf(item, n) || n < lo || n > hi)
        {
            bad(what);
            return false;
        }
        field = n;
        return true;
    };
    const auto flag = [&](const Json* item, bool& field, const std::wstring& what) {
        if (!item) { return; }
        if (item->type == Json::Type::Bool) { field = item->boolean; }
        else { bad(what + L" must be true or false"); }
    };
    for (size_t k = 0; k < value->array.size(); ++k)
    {
        const Json& item = value->array[k];
        const std::wstring at = L"shots[" + std::to_wstring(k) + L"]";
        if (out.size() >= MaxEntranceShots)
        {
            bad(L"more than " + std::to_wstring(MaxEntranceShots) + L" shots: the rest are left out");
            break;
        }
        if (item.type != Json::Type::Object)
        {
            bad(at + L" is not an object; left out");
            continue;
        }
        EntranceShot shot;
        shot.Name = StringOf(item.Find("name"));
        if (shot.Name.size() > 64) { shot.Name.resize(64); }
        const std::wstring label = shot.Name.empty() ? at : at + L" (" + shot.Name + L")";
        float seconds = 0.0f;
        if (!NumberOf(item.Find("seconds"), seconds) || seconds < 0.05f || seconds > 120.0f)
        {
            bad(label + L" seconds must be a number from 0.05 to 120; left out");
            continue;
        }
        shot.Seconds = seconds;
        flag(item.Find("before_switch"), shot.BeforeSwitch, label + L" before_switch");
        const std::wstring animation = StringOf(item.Find("animation"));
        shot.Animation = NormalizeObjectPath(animation);
        if (!animation.empty() && shot.Animation.empty()) { bad(label + L" animation must be an animation's path (\"/Game/...\")"); }
        number(item.Find("animation_start"), shot.AnimationStart, 0.0f, 600.0f, label + L" animation_start must be a number from 0 to 600 (seconds)");
        number(item.Find("rate"), shot.Rate, 0.05f, 10.0f, label + L" rate must be a number from 0.05 to 10");
        number(item.Find("scale"), shot.Scale, 0.001f, 1000.0f, label + L" scale must be a number from 0.001 to 1000");
        number(item.Find("flash"), shot.Flash, 0.0f, 10.0f, label + L" flash must be a number from 0 to 10 (seconds)");
        if (const Json* color = item.Find("flash_color"))
        {
            float rgb[3]{};
            bool ok = color->type == Json::Type::Array && color->array.size() == 3;
            for (size_t c = 0; ok && c < 3; ++c) { ok = NumberOf(&color->array[c], rgb[c]) && rgb[c] >= 0.0f && rgb[c] <= 1.0f; }
            if (ok) { std::copy(rgb, rgb + 3, shot.FlashColor); }
            else { bad(label + L" flash_color must be [red, green, blue], each 0 to 1"); }
        }
        // its camera: keys in time order
        if (const Json* keys = item.Find("camera"))
        {
            if (keys->type != Json::Type::Array) { bad(label + L" camera must be an array of keys [t, forward, right, up, pitch, yaw, roll, fov]"); }
            else
            {
                size_t dropped = 0;
                for (const Json& key : keys->array)
                {
                    float v[8]{};
                    bool ok = key.type == Json::Type::Array && key.array.size() == 8 && shot.Camera.size() < MaxShotKeys;
                    for (size_t c = 0; ok && c < 8; ++c) { ok = NumberOf(&key.array[c], v[c]) && std::fabs(v[c]) <= 1.0e6f; }
                    ok = ok && v[0] >= 0.0f && v[0] <= shot.Seconds + 1.0f && v[7] >= 5.0f && v[7] <= 170.0f &&
                         (shot.Camera.empty() || v[0] >= shot.Camera.back().T);
                    if (!ok)
                    {
                        ++dropped;
                        continue;
                    }
                    shot.Camera.push_back(EntranceKey{v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7]});
                }
                if (dropped)
                {
                    bad(label + L" camera: " + std::to_wstring(dropped) + L" key(s) left out (each must be [t, forward, right, up, pitch, yaw, roll, fov], "
                                L"t from 0 to the shot's end and in order, fov 5 to 170)");
                }
            }
        }
        // its effects
        if (const Json* effects = item.Find("effects"))
        {
            bool ok = true;
            for (const Json* e : Items(effects, ok))
            {
                if (shot.Effects.size() >= MaxShotCues) { ok = false; break; }
                std::vector<FormEffect> one;
                if (e->type != Json::Type::Object || !ParseFormEffects(e, one) || one.size() != 1) { ok = false; continue; }
                EntranceEffect cue;
                cue.Effect = std::move(one.front());
                float when = 0.0f;
                if (const Json* t = e->Find("at"); t && (!NumberOf(t, when) || when < 0.0f || when > shot.Seconds)) { ok = false; continue; }
                cue.At = when;
                if (const Json* offset = e->Find("offset"))
                {
                    bool good = offset->type == Json::Type::Array && offset->array.size() == 3;
                    for (size_t c = 0; good && c < 3; ++c) { good = NumberOf(&offset->array[c], cue.Offset[c]) && std::fabs(cue.Offset[c]) <= 1.0e6f; }
                    if (!good || !cue.Effect.Socket.empty()) { ok = false; continue; }
                }
                if (const Json* yaw = e->Find("yaw"); yaw && (!NumberOf(yaw, cue.Yaw) || std::fabs(cue.Yaw) > 360.0f)) { ok = false; continue; }
                shot.Effects.push_back(std::move(cue));
            }
            if (!ok)
            {
                bad(label + L" effects: entries must look like {\"effect\": \"/Game/...\", \"at\": 0.5, \"seconds\": 2, \"socket\": \"C_Spine_c\"} or "
                            L"with \"offset\": [forward, right, up] instead of a socket, \"at\" within the shot (bad ones left out)");
            }
        }
        // its sounds
        if (const Json* sounds = item.Find("sounds"))
        {
            bool ok = true;
            for (const Json* s : Items(sounds, ok))
            {
                if (shot.Sounds.size() >= MaxShotCues) { ok = false; break; }
                std::vector<FormSound> one;
                if (s->type != Json::Type::Object || !ParseFormSounds(s, one) || one.size() != 1) { ok = false; continue; }
                EntranceSound cue;
                cue.Sound = std::move(one.front());
                float when = 0.0f, start = 0.0f;
                if (const Json* t = s->Find("at"); t && (!NumberOf(t, when) || when < 0.0f || when > shot.Seconds)) { ok = false; continue; }
                if (const Json* t = s->Find("start"); t && (!NumberOf(t, start) || start < 0.0f || start > 3600.0f)) { ok = false; continue; }
                cue.At = when;
                cue.Start = start;
                if (const Json* stop = s->Find("stop_at_end"))
                {
                    if (stop->type != Json::Type::Bool) { ok = false; continue; }
                    cue.StopAtEnd = stop->boolean;
                }
                shot.Sounds.push_back(std::move(cue));
            }
            if (!ok)
            {
                bad(label + L" sounds: entries must look like {\"bank\": \"/Game/...\", \"cue\": \"...\", \"at\": 1.2, \"start\": 0, \"stop_at_end\": false}, "
                            L"\"at\" within the shot (bad ones left out)");
            }
        }
        out.push_back(std::move(shot));
    }
}

// 3.6.6 a form's "entrance": true (the flash and the camera), false, or {"animation": path, "slot": "DefaultSlot",
// "rate": 1, "seconds": 0, "flash": 1.5, "flash_color": [1, 1, 1], "descend": 1200, "descend_seconds": 0,
// "effects": [...], "camera": {"face": "C_Head_a", "distance": 900, "side": 150, "height": 40, "fov": 70,
// "close_at": 0.65, "close": 180, "close_fov": 30, "hold": 0.6, "blend_back": 1, "bars": 2.39} (or false),
// "hold_input": true, "skip": true, "invincible": true}. What is wrong is said in `why`; those parts keep their defaults.
inline void ParseFormEntrance(const Json* value, FormEntrance& out, std::wstring& why)
{
    out = FormEntrance{};
    if (!value) { return; }
    const auto bad = [&](const std::wstring& what) { why += (why.empty() ? L"" : L"; ") + what; };
    if (value->type == Json::Type::Bool)
    {
        out.On = value->boolean;
        return;
    }
    if (value->type != Json::Type::Object)
    {
        bad(L"it must be true, false or an object like {\"animation\": \"/Game/...\", \"descend\": 1200}");
        return;
    }
    out.On = true;
    if (const Json* on = value->Find("enabled"); on && on->type == Json::Type::Bool) { out.On = on->boolean; }
    const std::wstring animation = StringOf(value->Find("animation"));
    out.Animation = NormalizeObjectPath(animation);
    if (!animation.empty() && out.Animation.empty()) { bad(L"animation must be an animation's path (\"/Game/...\")"); }
    if (const Json* slot = value->Find("slot"))
    {
        const std::wstring name = StringOf(slot);
        if (IsPlainName(name)) { out.Slot = name; }
        else { bad(L"slot must be a slot name of the AnimBlueprint like \"DefaultSlot\""); }
    }
    struct NumberKey
    {
        const char* Key;
        float* Field;
        float Min, Max;
        const wchar_t* Range;
    };
    const auto numbers = [&](const Json* object, std::initializer_list<NumberKey> keys, const wchar_t* prefix) {
        for (const NumberKey& n : keys)
        {
            const Json* item = object->Find(n.Key);
            if (!item) { continue; }
            float number = 0.0f;
            if (!NumberOf(item, number) || number < n.Min || number > n.Max)
            {
                bad(std::wstring(prefix) + Widen(n.Key) + L" must be a number from " + n.Range);
                continue;
            }
            *n.Field = number;
        }
    };
    numbers(value,
            {{"rate", &out.Rate, 0.05f, 10.0f, L"0.05 to 10"},
             {"seconds", &out.Seconds, 0.0f, 60.0f, L"0 to 60 (seconds)"},
             {"flash", &out.Flash, 0.0f, 10.0f, L"0 to 10 (seconds)"},
             {"descend", &out.Descend, 0.0f, 20000.0f, L"0 to 20000 (cm)"},
             {"descend_seconds", &out.DescendSeconds, 0.0f, 60.0f, L"0 to 60 (seconds)"}},
            L"");
    if (const Json* color = value->Find("flash_color"))
    {
        float rgb[3]{};
        bool ok = color->type == Json::Type::Array && color->array.size() == 3;
        for (size_t k = 0; ok && k < 3; ++k) { ok = NumberOf(&color->array[k], rgb[k]) && rgb[k] >= 0.0f && rgb[k] <= 1.0f; }
        if (ok) { std::copy(rgb, rgb + 3, out.FlashColor); }
        else { bad(L"flash_color must be [red, green, blue], each 0 to 1"); }
    }
    if (!ParseFormEffects(value->Find("effects"), out.Effects))
    {
        bad(L"effects: entries must look like {\"effect\": \"/Game/Path/To/Effect\", \"socket\": \"C_Spine_c\"} (bad ones left out)");
    }
    for (const auto& [key, field] : std::initializer_list<std::pair<const char*, bool*>>{
             {"hold_input", &out.HoldInput}, {"skip", &out.Skip}, {"invincible", &out.Invincible}})
    {
        if (const Json* item = value->Find(key))
        {
            if (item->type == Json::Type::Bool) { *field = item->boolean; }
            else { bad(Widen(key) + L" must be true or false"); }
        }
    }
    if (const Json* camera = value->Find("camera"))
    {
        FormEntranceCamera& c = out.Camera;
        if (camera->type == Json::Type::Bool) { c.On = camera->boolean; }
        else if (camera->type != Json::Type::Object) { bad(L"camera must be true, false or an object like {\"face\": \"C_Head_a\"}"); }
        else
        {
            if (const Json* on = camera->Find("enabled"); on && on->type == Json::Type::Bool) { c.On = on->boolean; }
            if (const Json* face = camera->Find("face"))
            {
                const std::wstring name = StringOf(face);
                if (IsPlainName(name)) { c.Face = name; }
                else { bad(L"camera face must be a bone or socket name of the model like \"C_Head_a\""); }
            }
            numbers(camera,
                    {{"distance", &c.Distance, 0.0f, 10000.0f, L"0 to 10000 (cm)"},
                     {"side", &c.Side, -5000.0f, 5000.0f, L"-5000 to 5000 (cm)"},
                     {"height", &c.Height, -1000.0f, 5000.0f, L"-1000 to 5000 (cm)"},
                     {"fov", &c.Fov, 5.0f, 170.0f, L"5 to 170 (degrees)"},
                     {"close_at", &c.CloseAt, 0.0f, 1.0f, L"0 to 1"},
                     {"close", &c.Close, 10.0f, 5000.0f, L"10 to 5000 (cm)"},
                     {"close_fov", &c.CloseFov, 5.0f, 170.0f, L"5 to 170 (degrees)"},
                     {"hold", &c.Hold, 0.0f, 10.0f, L"0 to 10 (seconds)"},
                     {"blend_back", &c.BlendBack, 0.0f, 10.0f, L"0 to 10 (seconds)"}},
                    L"camera ");
            if (const Json* bars = camera->Find("bars"))
            {
                float shape = 0.0f;
                if (bars->type == Json::Type::Bool) { c.Bars = bars->boolean ? 2.39f : 0.0f; }
                else if (NumberOf(bars, shape) && (shape == 0.0f || (shape >= 1.0f && shape <= 4.0f))) { c.Bars = shape; }
                else { bad(L"camera bars must be true, false or the picture's shape (width / height, 1 to 4; 0: the screen's)"); }
            }
        }
    }
    // (3.6.7) a cutscene's shots
    if (const Json* shots = value->Find("shots"))
    {
        ParseEntranceShots(shots, out.Shots, why);
        if (out.Shots.empty()) { bad(L"none of its shots is usable: it plays as an entrance without them"); }
    }
}

// 3.6 "forms" of a row: an array of forms, or an object with the menu's settings and the forms as "list".
// (3.6.16) A form's camera: the distance alone (a number) or {"distance": 300, "height": 100, "fov": 0, "blend": 0.6}.
inline bool ParseFormCamera(const Json* value, FormCamera& out)
{
    if (!value) { return true; }
    FormCamera camera;
    camera.Set = true;
    if (value->type == Json::Type::Number)
    {
        if (!NumberOf(value, camera.Distance)) { return false; }
    }
    else if (value->type == Json::Type::Object)
    {
        bool ok = true;
        const auto number = [&](const char* key, float& field, float low, float high) {
            const Json* item = value->Find(key);
            if (!item) { return; }
            float v = 0.0f;
            if (!NumberOf(item, v) || !(v >= low && v <= high)) { ok = false; return; }
            field = v;
        };
        number("distance", camera.Distance, -500.0f, 20000.0f);
        number("height", camera.Height, -2000.0f, 10000.0f);
        number("fov", camera.Fov, -60.0f, 60.0f);
        number("blend", camera.Blend, 0.0f, 10.0f);
        if (!ok) { return false; }
    }
    else { return false; }
    camera.Distance = std::clamp(camera.Distance, -500.0f, 20000.0f);
    out = camera;
    return true;
}

inline void ParseForms(const Json& entry, std::wstring_view origin, const std::wstring& where, Config& cfg, AnimSetRow& row)
{
    const Json* value = entry.Find("forms");
    if (!value) { return; }
    FormSettings& forms = row.Forms;
    const Json* list = value;
    const std::wstring at = where + L" forms";
    if (value->type == Json::Type::Object)
    {
        list = value->Find("list");
        if (!list) { list = value->Find("forms"); }
        for (const auto& [key, field] : std::initializer_list<std::pair<const char*, std::wstring*>>{
                 {"button", &forms.Button}, {"key", &forms.Key}, {"fade_parameter", &forms.FadeParameter}})
        {
            if (const Json* item = value->Find(key))
            {
                const std::wstring text = StringOf(item);
                if (IsPlainName(text) || (text.empty() && std::string_view(key) == "key")) { *field = text; }
                else { Note(cfg, origin, at + L" " + Widen(key) + L" must be a name like \"Gamepad_FaceButton_Top\"; ignored"); }
            }
        }
        if (const Json* item = value->Find("title"))
        {
            const std::wstring text = StringOf(item);
            if (!text.empty() && text.size() <= 40) { forms.Title = text; }
            else { Note(cfg, origin, at + L" title must be a short text; ignored"); }
        }
        for (const auto& [key, field] : std::initializer_list<std::pair<const char*, float*>>{
                 {"hold_seconds", &forms.HoldSeconds}, {"fade_seconds", &forms.FadeSeconds}, {"effect_seconds", &forms.EffectSeconds}})
        {
            float number = 0.0f;
            if (const Json* item = value->Find(key); item && (!NumberOf(item, number) || number < 0.0f || number > 60.0f))
            {
                Note(cfg, origin, at + L" " + Widen(key) + L" must be a number of seconds (0 to 60); ignored");
            }
            else if (item) { *field = number; }
        }
        if (forms.HoldSeconds < 0.1f) { forms.HoldSeconds = 0.1f; } // (a tap is the game's)
        bool partsOk = true;
        for (const Json* item : Items(value->Find("parts"), partsOk))
        {
            const std::wstring slot = StringOf(item);
            if (!IsPlainName(slot)) { partsOk = false; continue; }
            AddUnique(forms.Parts, slot);
        }
        if (!partsOk) { Note(cfg, origin, at + L" parts: entries must be material slot names of the character's model; bad entries ignored"); }
        if (!ParseFormEffects(value->Find("show_effects"), forms.ShowEffects) || !ParseFormEffects(value->Find("hide_effects"), forms.HideEffects))
        {
            Note(cfg, origin, at + L" show_effects / hide_effects: entries must look like {\"effect\": \"/Game/Path/To/Effect\", \"socket\": \"R_Hand_a\"}; "
                                 L"bad entries ignored");
        }
        if (const Json* item = value->Find("hide_on_others"); item && item->type == Json::Type::Bool) { forms.HideOnOthers = item->boolean; }
        // "timer_at": [x, y] (fractions of the screen) where a timed form's time left shows; false: not shown
        if (const Json* item = value->Find("timer_at"))
        {
            float x = 0.0f, y = 0.0f;
            if (item->type == Json::Type::Bool) { forms.Timer = item->boolean; }
            else if (item->type == Json::Type::Array && item->array.size() == 2 && NumberOf(&item->array[0], x) && NumberOf(&item->array[1], y) &&
                     x >= 0.0f && x <= 1.0f && y >= 0.0f && y <= 1.0f)
            {
                forms.TimerX = x;
                forms.TimerY = y;
            }
            else { Note(cfg, origin, at + L" timer_at must be [x, y] in fractions of the screen (0 to 1), or false; ignored"); }
        }
    }
    if (!list || list->type != Json::Type::Array)
    {
        Note(cfg, origin, at + L" needs a list of forms: \"forms\": [{\"name\": \"NORMAL\"}, {\"name\": \"WINGED\", \"pack\": \"Battle02\"}] "
                             L"(or an object with the menu's settings and the forms as \"list\"); ignored");
        forms = FormSettings{};
        return;
    }
    bool formsOk = true;
    for (const auto& item : list->array)
    {
        Form form;
        if (item.type == Json::Type::String)
        {
            form.Pack = Trim(Widen(item.string));
            form.Name = form.Pack;
        }
        else if (item.type == Json::Type::Object)
        {
            form.Name = StringOf(item.Find("name"));
            form.Pack = StringOf(item.Find("pack"));
            form.Model = NormalizeObjectPath(StringOf(item.Find("model")));
            if (!StringOf(item.Find("model")).empty() && form.Model.empty()) { formsOk = false; }
            // "anim_class": an AnimBlueprint (its class: "/Game/.../ABP.ABP_C"; the asset's path gets _C)
            if (std::wstring abp = NormalizeObjectPath(StringOf(item.Find("anim_class"))); !abp.empty())
            {
                if (abp.size() < 2 || abp.compare(abp.size() - 2, 2, L"_C") != 0) { abp += L"_C"; }
                form.AnimClass = abp;
            }
            else if (!StringOf(item.Find("anim_class")).empty()) { formsOk = false; }
            // (3.7.8) "as_look": true: the model goes on the game's way with the character's own AnimBlueprint
            if (const Json* look = item.Find("as_look"))
            {
                if (look->type == Json::Type::Bool) { form.AsLook = look->boolean; }
                else { formsOk = false; }
            }
            if (const Json* scale = item.Find("scale"))
            {
                if (!NumberOf(scale, form.Scale) || form.Scale < 0.01f || form.Scale > 50.0f) { formsOk = false; form.Scale = 0.0f; }
            }
            bool meshesOk = true;
            for (const Json* part : Items(item.Find("meshes"), meshesOk))
            {
                FormMesh mesh;
                if (part->type == Json::Type::String) { mesh.Mesh = NormalizeObjectPath(Widen(part->string)); }
                else
                {
                    mesh.Mesh = NormalizeObjectPath(StringOf(part->Find("mesh")));
                    mesh.Socket = StringOf(part->Find("socket"));
                    if (const Json* follow = part->Find("follow_pose"); follow && follow->type == Json::Type::Bool) { mesh.FollowPose = follow->boolean; }
                }
                if (mesh.Mesh.empty() || (!mesh.Socket.empty() && !IsPlainName(mesh.Socket))) { meshesOk = false; continue; }
                form.Meshes.push_back(std::move(mesh));
            }
            if (!meshesOk) { formsOk = false; }
            if (const Json* hide = item.Find("hide_weapon"); hide && hide->type == Json::Type::Bool) { form.HideWeapon = hide->boolean; }
            // (3.8.2) "weapon": a weapon blueprint the form fights with (a true weapon swap)
            if (std::wstring weapon = NormalizeObjectPath(StringOf(item.Find("weapon"))); !weapon.empty())
            {
                if (weapon.size() < 2 || weapon.compare(weapon.size() - 2, 2, L"_C") != 0) { weapon += L"_C"; }
                form.Weapon = weapon;
            }
            else if (!StringOf(item.Find("weapon")).empty()) { formsOk = false; }
            if (!ParseFormEffects(item.Find("keep_effects"), form.Keep)) { formsOk = false; }
            // (3.12.2) "state_effects": ["BossSephiroth_FeelerSword", {"state": "BossSephiroth_FeelerWing", "needs": "R_FeatherD_b_Phy"}]
            {
                bool statesOk = true;
                for (const Json* one : Items(item.Find("state_effects"), statesOk))
                {
                    FormStateEffect state;
                    if (one->type == Json::Type::String) { state.Name = Trim(Widen(one->string)); }
                    else if (one->type == Json::Type::Object)
                    {
                        state.Name = StringOf(one->Find("state"));
                        if (state.Name.empty()) { state.Name = StringOf(one->Find("name")); }
                        state.Needs = StringOf(one->Find("needs"));
                    }
                    const bool twice = std::any_of(form.States.begin(), form.States.end(), [&](const FormStateEffect& s) { return NameEquals(s.Name, state.Name); });
                    if (state.Name.empty() || !IsPlainName(state.Name) || (!state.Needs.empty() && !IsPlainName(state.Needs)) || twice ||
                        form.States.size() >= MaxFormStateEffects)
                    {
                        statesOk = false;
                        continue;
                    }
                    form.States.push_back(std::move(state));
                }
                if (!statesOk)
                {
                    Note(cfg, origin, at + L": " + (form.Name.empty() ? form.Pack : form.Name) +
                                         L" state_effects: each must be a special state effect's name (\"BossSephiroth_FeelerSword\") or {\"state\": name, \"needs\": a socket or bone}, each once, " +
                                         std::to_wstring(MaxFormStateEffects) + L" at most; bad entries ignored");
                }
                bool watchOk = true;
                for (const Json* one : Items(item.Find("watch_damage"), watchOk))
                {
                    const std::wstring row = StringOf(one);
                    if (row.empty() || !IsRowName(row) || form.WatchDamage.size() >= MaxFormWatchedDamage)
                    {
                        watchOk = false;
                        continue;
                    }
                    AddUniqueName(form.WatchDamage, row);
                }
                if (!watchOk)
                {
                    Note(cfg, origin, at + L": " + (form.Name.empty() ? form.Pack : form.Name) + L" watch_damage: each must be a damage source row's name, " +
                                         std::to_wstring(MaxFormWatchedDamage) + L" at most; bad entries ignored");
                }
            }
            form.After = StringOf(item.Find("after"));
            // "super_armor": true; "seconds" (or "time_limit"): how long it lasts; "cooldown": how long before it can be chosen
            // again; "revert_to": the form it turns back into (a name on the menu)
            if (const Json* armor = item.Find("super_armor"))
            {
                if (armor->type == Json::Type::Bool) { form.SuperArmor = armor->boolean; }
                else { formsOk = false; }
            }
            // (3.7) "shooter": false: the character does not fight as a shooter in this form (a beast); true: it does
            // (3.7.7) {...}: it does, with these settings over the character's (its own motions, guns, gun model, flying)
            if (const Json* shooting = item.Find("shooter"))
            {
                if (shooting->type == Json::Type::Bool) { form.Shooting = shooting->boolean ? 1 : 0; }
                else if (shooting->type == Json::Type::Object)
                {
                    form.Shooting = 1;
                    if (const Json* on = shooting->Find("on"); on && on->type == Json::Type::Bool && !on->boolean) { form.Shooting = 0; }
                    else { form.ShooterJson = std::make_shared<Json>(*shooting); }
                }
                else { formsOk = false; }
            }
            // (3.7.5) "sets": {"Battle00": "Battle07", ...}: set names the game looks up -> the set it gets in their place
            if (const Json* sets = item.Find("sets"))
            {
                if (sets->type != Json::Type::Object)
                {
                    Note(cfg, origin, at + L": " + (form.Name.empty() ? form.Pack : form.Name) +
                                         L" sets must be an object of set names: {\"Battle00\": \"Battle07\", \"Battle01\": \"Battle08\"}; ignored");
                }
                else
                {
                    bool setsOk = true;
                    for (const auto& [from, to] : sets->object)
                    {
                        const std::wstring f = Trim(Widen(from)), t = StringOf(&to);
                        const bool twice = std::any_of(form.Sets.begin(), form.Sets.end(), [&](const auto& p) { return NameEquals(p.first, f); });
                        if (!IsPlainName(f) || !IsPlainName(t) || NameEquals(f, t) || twice || form.Sets.size() >= MaxFormSets)
                        {
                            setsOk = false;
                            continue;
                        }
                        form.Sets.emplace_back(f, t);
                    }
                    if (!setsOk)
                    {
                        Note(cfg, origin, at + L": " + (form.Name.empty() ? form.Pack : form.Name) + L" sets: each entry must be a set name -> another set name " +
                                             L"(\"Battle01\": \"Battle08\"), each name once, " + std::to_wstring(MaxFormSets) + L" at most; bad entries ignored");
                    }
                }
            }
            // (3.9.0) "voice": the voice its lines play in, in this form
            if (!ParseVoice(item.Find("voice"), form.Speaks))
            {
                Note(cfg, origin, at + L": " + (form.Name.empty() ? form.Pack : form.Name) +
                                     L" voice must be a voice bank (\"/Game/Sound/Voice/{language}/Character/Player/VO_...\"), \"own\", or "
                                     L"{\"bank\": ..., \"replaces\": [...]}; ignored");
            }
            for (const auto& [keys, field] : std::initializer_list<std::pair<std::pair<const char*, const char*>, float*>>{
                     {{"seconds", "time_limit"}, &form.Seconds}, {{"cooldown", "cooldown_seconds"}, &form.Cooldown}})
            {
                const Json* number = item.Find(keys.first);
                if (!number) { number = item.Find(keys.second); }
                if (!number) { continue; }
                float seconds = 0.0f;
                if (!NumberOf(number, seconds) || !(seconds >= 0.0f && seconds <= 3600.0f))
                {
                    Note(cfg, origin, at + L": " + (form.Name.empty() ? form.Pack : form.Name) + L" " + Widen(keys.first) +
                                         L" must be a number of seconds (0 to 3600); ignored");
                    continue;
                }
                *field = seconds;
            }
            form.RevertTo = StringOf(item.Find("revert_to"));
            // "ability_effects": [{"ability": "PC0010_BZ_Octaslash" (or "abilities": [...]), "effects": [...]}] or
            // {"PC0010_BZ_Octaslash": [...effects]}
            if (const Json* list = item.Find("ability_effects"))
            {
                const auto add = [&](std::vector<std::wstring> names, const Json* effects) {
                    FormAbilityEffects entry;
                    for (auto& name : names)
                    {
                        name = Trim(name);
                        const std::wstring_view bare = !name.empty() && name.back() == L'*' ? std::wstring_view(name).substr(0, name.size() - 1) : std::wstring_view(name);
                        if (bare.empty() || !IsRowName(bare)) { formsOk = false; continue; }
                        AddUnique(entry.Abilities, name);
                    }
                    if (!ParseFormEffects(effects, entry.Effects)) { formsOk = false; }
                    if (!entry.Abilities.empty() && !entry.Effects.empty()) { form.AbilityEffects.push_back(std::move(entry)); }
                    else { formsOk = false; }
                };
                if (list->type == Json::Type::Object)
                {
                    for (const auto& [key, effects] : list->object) { add({Widen(key)}, &effects); }
                }
                else
                {
                    bool listOk = true;
                    for (const Json* one : Items(list, listOk))
                    {
                        if (one->type != Json::Type::Object) { listOk = false; continue; }
                        std::vector<std::wstring> names;
                        bool namesOk = true;
                        for (const char* key : {"ability", "abilities"})
                        {
                            for (const Json* name : Items(one->Find(key), namesOk)) { names.push_back(StringOf(name)); }
                        }
                        if (!namesOk) { formsOk = false; }
                        add(std::move(names), one->Find("effects"));
                    }
                    if (!listOk) { formsOk = false; }
                }
            }
            // (3.6.16) "camera": the battle camera in this form; "ability_cameras": [{"abilities": ["M_SMN_*"], "distance": 1500,
            // "height": 400}]: while one of those runs
            if (!ParseFormCamera(item.Find("camera"), form.Camera))
            {
                Note(cfg, origin, at + L": " + (form.Name.empty() ? form.Pack : form.Name) +
                                     L" camera must be a distance or {\"distance\": 300, \"height\": 100, \"fov\": 0, \"blend\": 0.6}; ignored");
                form.Camera = FormCamera{};
            }
            if (const Json* list = item.Find("ability_cameras"))
            {
                bool listOk = true;
                for (const Json* one : Items(list, listOk))
                {
                    if (one->type != Json::Type::Object) { listOk = false; continue; }
                    FormAbilityCamera entry;
                    bool namesOk = true;
                    for (const char* key : {"ability", "abilities"})
                    {
                        for (const Json* name : Items(one->Find(key), namesOk))
                        {
                            std::wstring text = Trim(StringOf(name));
                            const std::wstring_view bare = !text.empty() && text.back() == L'*' ? std::wstring_view(text).substr(0, text.size() - 1) : std::wstring_view(text);
                            if (bare.empty() || !IsRowName(bare)) { namesOk = false; continue; }
                            AddUnique(entry.Abilities, text);
                        }
                    }
                    Json camera = *one;   // (the entry is the camera too: its distance, height, fov, blend)
                    camera.object.erase(std::remove_if(camera.object.begin(), camera.object.end(),
                                                       [](const auto& kv) { return kv.first == "ability" || kv.first == "abilities"; }),
                                        camera.object.end());
                    if (!namesOk || entry.Abilities.empty() || !ParseFormCamera(&camera, entry.Camera)) { listOk = false; continue; }
                    form.AbilityCameras.push_back(std::move(entry));
                }
                if (!listOk)
                {
                    Note(cfg, origin, at + L": " + (form.Name.empty() ? form.Pack : form.Name) +
                                         L" ability_cameras entries must look like {\"abilities\": [\"M_SMN_*\"], \"distance\": 1500, \"height\": 400}; bad ones ignored");
                }
            }
            bool showOk = true;
            for (const Json* slot : Items(item.Find("show"), showOk))
            {
                const std::wstring name = StringOf(slot);
                if (!IsPlainName(name)) { showOk = false; continue; }
                AddUnique(form.Show, name);
            }
            if (!showOk || !ParseFormEffects(item.Find("effects"), form.Effects) || !ParseFormSounds(item.Find("sounds"), form.Sounds)) { formsOk = false; }
            if (const Json* fly = item.Find("fly"))
            {
                if (fly->type == Json::Type::Bool) { form.Fly.On = fly->boolean; }
                else if (fly->type == Json::Type::Object)
                {
                    form.Fly.On = true;
                    if (const Json* on = fly->Find("enabled"); on && on->type == Json::Type::Bool) { form.Fly.On = on->boolean; }
                    NumberOf(fly->Find("height"), form.Fly.Height);
                    NumberOf(fly->Find("speed"), form.Fly.Speed);
                    NumberOf(fly->Find("max"), form.Fly.Max);
                    const std::wstring up = StringOf(fly->Find("up")), down = StringOf(fly->Find("down"));
                    if (!up.empty()) { form.Fly.Up = up; }
                    if (!down.empty()) { form.Fly.Down = down; }
                }
                else { formsOk = false; }
                form.Fly.Height = std::clamp(form.Fly.Height, 0.0f, 5000.0f);
                form.Fly.Max = std::clamp(form.Fly.Max, form.Fly.Height, 20000.0f);
                form.Fly.Speed = std::clamp(form.Fly.Speed, 0.0f, 5000.0f);
                if (!IsPlainName(form.Fly.Up) || !IsPlainName(form.Fly.Down)) { formsOk = false; form.Fly.Up = L"Gamepad_DPad_Up"; form.Fly.Down = L"Gamepad_DPad_Down"; }
            }
            // (3.6.6) "entrance": played as the character switches to the form
            std::wstring entranceWhy;
            ParseFormEntrance(item.Find("entrance"), form.Entrance, entranceWhy);
            if (!entranceWhy.empty())
            {
                Note(cfg, origin, at + L": " + (form.Name.empty() ? form.Pack : form.Name) + L" entrance: " + entranceWhy + L" (those parts keep their defaults)");
            }
        }
        else
        {
            formsOk = false;
            continue;
        }
        if (!form.Pack.empty() && (!IsBattleSetName(form.Pack) || form.Pack.find_first_of(L"/.: ") != std::wstring::npos))
        {
            Note(cfg, origin, at + L": " + form.Pack + L" is not a battle animation pack name like \"Battle02\"; that form is left out");
            continue;
        }
        if (!form.After.empty() && !IsRowName(form.After)) { formsOk = false; form.After.clear(); }
        if (form.Name.empty()) { form.Name = form.Pack.empty() ? (forms.List.empty() ? std::wstring(L"NORMAL") : L"FORM " + std::to_wstring(forms.List.size() + 1)) : form.Pack; }
        if (form.Name.size() > 40) { form.Name.resize(40); }
        if (forms.List.size() == MaxForms)
        {
            Note(cfg, origin, at + L": " + form.Name + L" left out: the menu takes " + std::to_wstring(MaxForms) + L" forms (the normal one included)");
            continue;
        }
        forms.List.push_back(std::move(form));
    }
    if (!formsOk)
    {
        Note(cfg, origin, at + L": entries must look like {\"name\": \"WINGED\", \"pack\": \"Battle02\", \"show\": [\"Wing\"], \"effects\": [...], "
                             L"\"sounds\": [{\"bank\": \"/Game/...\", \"cue\": \"...\"}], \"fly\": true}; bad parts of them ignored");
    }
    if (!forms.List.empty() && !forms.List.front().Pack.empty() && !NameEquals(forms.List.front().Pack, DefaultAbilityPack()))
    {
        // (3.9.0) the normal form's own pack: the character starts each battle in it (and goes back to it when the battle
        // ends); a form without a pack plays the character's own (Battle00)
        Note(cfg, origin, at + L": the normal form " + forms.List.front().Name + L" plays " + forms.List.front().Pack +
                             L": the character starts each battle in it (Create a Character System 3.9.0); forms without a pack play its own Battle00");
    }
    for (const auto& form : forms.List)
    {
        for (const auto& slot : form.Show)
        {
            if (std::none_of(forms.Parts.begin(), forms.Parts.end(), [&](const std::wstring& p) { return NameEquals(p, slot); }))
            {
                forms.Parts.push_back(slot); // a part a form shows is one the forms show or hide
            }
        }
    }
    if (forms.List.size() < 2)
    {
        Note(cfg, origin, at + L": a character needs two forms or more (its normal one first) for the forms menu; ignored");
        forms = FormSettings{};
        return;
    }
    // time limits: the form it turns back into, by its name on the menu (the normal one when none is named)
    for (size_t k = 0; k < forms.List.size(); ++k)
    {
        Form& form = forms.List[k];
        form.RevertIndex = 0;
        if (k == 0 && form.Limited())
        {
            Note(cfg, origin, at + L": " + form.Name + L" is the normal form, which has no time limit (seconds ignored)");
            form.Seconds = 0.0f;
        }
        if (form.RevertTo.empty()) { continue; }
        const auto it = std::find_if(forms.List.begin(), forms.List.end(), [&](const Form& f) { return NameEquals(f.Name, form.RevertTo); });
        if (it == forms.List.end() || it - forms.List.begin() == static_cast<std::ptrdiff_t>(k))
        {
            Note(cfg, origin, at + L": " + form.Name + L" revert_to " + form.RevertTo + (it == forms.List.end() ? L" is not one of its forms" : L" is the form itself") +
                                 L"; it turns back into " + forms.List.front().Name);
            form.RevertTo.clear();
            continue;
        }
        form.RevertIndex = static_cast<int>(it - forms.List.begin());
    }
    // (3.15.1) "movesets": movesets for the MOVESET page that are not forms, each {"name", "pack"} (its pack's set: one the
    // row builds, e.g. a "battle" source "as" it with the moves that make the moveset)
    const Json* movesets = value->type == Json::Type::Object ? value->Find("movesets") : nullptr;
    if (!movesets) { return; }
    bool movesetsOk = movesets->type == Json::Type::Array;
    for (size_t k = 0; movesetsOk && k < movesets->array.size(); ++k)
    {
        const Json& item = movesets->array[k];
        Form moveset;
        if (item.type == Json::Type::Object)
        {
            moveset.Name = StringOf(item.Find("name"));
            moveset.Pack = StringOf(item.Find("pack"));
            // (3.16.1) "weapon_socket": the weapon in hand on that socket in battle while a form plays it
            if (const std::wstring socket = StringOf(item.Find("weapon_socket")); !socket.empty())
            {
                if (IsPlainName(socket)) { moveset.WeaponSocket = socket; }
                else { Note(cfg, origin, at + L" movesets: " + moveset.Name + L" \"weapon_socket\" must be a socket name like \"Attach_Weapon_Right01\"; left out"); }
            }
        }
        const auto same = [&](const Form& f) { return NameEquals(f.Name, moveset.Name); };
        const bool taken = std::any_of(forms.List.begin(), forms.List.end(), same) || std::any_of(forms.Movesets.begin(), forms.Movesets.end(), same);
        if (moveset.Name.empty() || moveset.Name.size() > 40 || taken || !IsPlainName(moveset.Pack) || !IsBattleSetName(moveset.Pack) ||
            NameEquals(moveset.Pack, DefaultAbilityPack()))
        {
            Note(cfg, origin, at + L" movesets: " + (moveset.Name.empty() ? L"entry " + std::to_wstring(k + 1) : moveset.Name) +
                                 L" left out: each needs a name of its own (not a form's) and a battle pack of its own like \"Battle11\"");
            continue;
        }
        if (forms.Movesets.size() == MaxMovesetSources)
        {
            Note(cfg, origin, at + L" movesets: " + moveset.Name + L" left out: " + std::to_wstring(MaxMovesetSources) + L" at most");
            continue;
        }
        forms.Movesets.push_back(std::move(moveset));
    }
    if (!movesetsOk)
    {
        Note(cfg, origin, at + L" movesets must be a list like [{\"name\": \"CLOUD\", \"pack\": \"Battle11\"}]; ignored");
    }
}

// One "animation_sets" entry. Its "cutscene" entry becomes a family pair.
// 3.7 a DualSense trigger effect: {"mode": "weapon", "start": 4, "end": 6, "strength": 6}, {"mode": "feedback", "start": 2,
// "strength": 2}, {"mode": "vibration", "start": 3, "strength": 6, "frequency": 40}, or "off" / false.
inline bool ParseTrigger(const Json* value, Shooter::TriggerEffect& out)
{
    using Shooter::TriggerMode;
    if (!value) { return true; }
    if ((value->type == Json::Type::Bool && !value->boolean) || (value->type == Json::Type::String && NameEquals(StringOf(value), L"off")))
    {
        out = Shooter::TriggerEffect{};
        return true;
    }
    if (value->type != Json::Type::Object) { return false; }
    const std::wstring mode = StringOf(value->Find("mode"));
    Shooter::TriggerEffect e;
    if (NameEquals(mode, L"feedback") || NameEquals(mode, L"resistance")) { e.Mode = TriggerMode::Feedback; }
    else if (NameEquals(mode, L"weapon") || NameEquals(mode, L"gun")) { e.Mode = TriggerMode::Weapon; }
    else if (NameEquals(mode, L"vibration") || NameEquals(mode, L"vibrate")) { e.Mode = TriggerMode::Vibration; }
    else if (mode.empty() || NameEquals(mode, L"off")) { e.Mode = TriggerMode::Off; }
    else { return false; }
    bool ok = true;
    const auto whole = [&](std::initializer_list<const char*> keys, int& field, int low, int high) {
        for (const char* key : keys)
        {
            const Json* item = value->Find(key);
            if (!item) { continue; }
            float v = 0.0f;
            if (!NumberOf(item, v) || v < static_cast<float>(low) || v > static_cast<float>(high)) { ok = false; return; }
            field = static_cast<int>(std::lround(v));
            return;
        }
    };
    whole({"start", "position"}, e.Start, 0, 9);
    whole({"end"}, e.End, 0, 9);
    whole({"strength", "amplitude"}, e.Strength, 0, 8);
    whole({"frequency", "hz"}, e.Frequency, 0, 255);
    if (e.Mode == TriggerMode::Weapon)
    {
        e.Start = std::clamp(e.Start, 2, 7);
        if (e.End <= e.Start) { e.End = std::min(e.Start + 2, 8); }
        e.End = std::min(e.End, 8);
    }
    if (!ok) { return false; }
    out = e;
    return true;
}

// 3.7 "shooter": true (Dirge of Cerberus' way, every setting its default), false, or an object of settings.
// `base` (3.7.7, a form's shooter): the settings start from it (the character's shooter) instead of the defaults, and a gun
// of the form's starts from the character's gun of its name.
inline void ParseShooter(const Json* value, std::wstring_view origin, const std::wstring& where, Config& cfg, Shooter::Settings& out,
                         const Shooter::Settings* base = nullptr)
{
    using Shooter::Button;
    if (!value) { return; }
    const std::wstring at = where + L" shooter";
    Shooter::Settings s;
    s.Weapons = Shooter::DefaultWeapons();
    if (base)
    {
        s = *base;
        if (s.Weapons.empty()) { s.Weapons = Shooter::DefaultWeapons(); }
    }
    if (value->type == Json::Type::Bool)
    {
        s.On = value->boolean;
        out = s;
        return;
    }
    if (value->type != Json::Type::Object)
    {
        Note(cfg, origin, at + L" must be true, false or an object of settings; ignored");
        return;
    }
    s.On = true;
    std::wstring bad;
    const auto said = [&](const std::wstring& what) { bad += (bad.empty() ? L"" : L"; ") + what; };
    const auto flag = [&](const Json* from, const char* key, bool& field) {
        if (const Json* item = from ? from->Find(key) : nullptr)
        {
            if (item->type == Json::Type::Bool) { field = item->boolean; }
            else { said(Widen(key) + L" must be true or false"); }
        }
    };
    const auto number = [&](const Json* from, const char* key, float& field, float low, float high) {
        const Json* item = from ? from->Find(key) : nullptr;
        if (!item) { return; }
        float v = 0.0f;
        if (!NumberOf(item, v) || v < low || v > high)
        {
            said(Widen(key) + L" must be a number from " + std::to_wstring(static_cast<int>(low)) + L" to " + std::to_wstring(static_cast<int>(high)));
            return;
        }
        field = v;
    };
    const auto text = [&](const Json* from, const char* key, std::wstring& field) {
        if (const Json* item = from ? from->Find(key) : nullptr)
        {
            const std::wstring t = Trim(StringOf(item));
            if (t.empty() || t.size() > 200) { said(Widen(key) + L" must be a text"); }
            else { field = t; }
        }
    };
    const auto color = [&](const Json* from, const char* key, float* field) {
        const Json* item = from ? from->Find(key) : nullptr;
        if (!item) { return; }
        float c[4] = {field[0], field[1], field[2], field[3]};
        bool fine = item->type == Json::Type::Array && (item->array.size() == 3 || item->array.size() == 4);
        for (size_t k = 0; fine && k < item->array.size(); ++k) { fine = NumberOf(&item->array[k], c[k]) && c[k] >= 0.0f && c[k] <= 1.0f; }
        if (!fine) { said(Widen(key) + L" must be [red, green, blue] or [red, green, blue, alpha], each 0 to 1"); return; }
        std::copy(c, c + 4, field);
    };
    flag(value, "on", s.On);
    flag(value, "in_field", s.InField);
    flag(value, "triggers", s.Triggers);
    // the buttons: a preset, then any of them by name
    if (const Json* item = value->Find("controls"))
    {
        const std::wstring preset = StringOf(item);
        if (!Shooter::ApplyPreset(s, preset)) { said(L"controls must be \"triggers\" or \"dirge\""); }
    }
    bool buttonsChanged = false;
    for (const auto& [key, field] : std::initializer_list<std::pair<const char*, Button*>>{
             {"fire", &s.Fire}, {"aim", &s.Aim}, {"reload", &s.Reload}, {"switch", &s.Switch}, {"zoom", &s.Zoom}})
    {
        const Json* item = value->Find(key);
        if (!item) { continue; }
        if (item->type == Json::Type::Bool && !item->boolean)
        {
            *field = Button::None;
            buttonsChanged = true;
            continue;
        }
        const Button b = Shooter::ButtonOf(StringOf(item));
        if (b == Button::None) { said(Widen(key) + L" must be a button: R2, L2, R1, L1, R3, L3, Square, Cross, Circle, Triangle, Up, Down, Left or Right"); }
        else
        {
            *field = b;
            buttonsChanged = true;
        }
    }
    if (buttonsChanged) { s.Block = Shooter::Bit(s.Fire) | Shooter::Bit(s.Aim) | Shooter::Bit(s.Reload) | Shooter::Bit(s.Switch) | Shooter::Bit(s.Zoom); }
    if (const Json* item = value->Find("block"))
    {
        uint32_t mask = 0;
        bool fine = true;
        for (const Json* entry : Items(item, fine))
        {
            const Button b = Shooter::ButtonOf(StringOf(entry));
            if (b == Button::None) { fine = false; continue; }
            mask |= Shooter::Bit(b);
        }
        if (!fine) { said(L"block must be a list of buttons like [\"L2\", \"R2\"]; bad entries ignored"); }
        s.Block = mask;
    }
    if (!ParseTrigger(value->Find("aim_trigger"), s.AimTrigger)) { said(L"aim_trigger must be a trigger effect like {\"mode\": \"feedback\", \"start\": 2, \"strength\": 2}"); }
    number(value, "assist", s.Assist, 0.0f, 30.0f);
    // (3.7.3) aiming: the game's guard-walk
    flag(value, "strafe", s.Strafe);
    if (const Json* item = value->Find("strafe_button"))
    {
        const Button b = Shooter::ButtonOf(StringOf(item));
        if (b == Button::None || b == Button::Up || b == Button::Down || b == Button::Left || b == Button::Right)
        {
            said(L"strafe_button must be the game's guard button: R1, L1, R2, L2, R3, L3, Square, Cross, Circle or Triangle");
        }
        else { s.StrafeButton = b; }
    }
    if (const Json* item = value->Find("guard_abilities"))
    {
        std::vector<std::wstring> names;
        bool fine = item->type == Json::Type::Array;
        for (size_t k = 0; fine && k < item->array.size(); ++k)
        {
            const std::wstring name = Trim(StringOf(&item->array[k]));
            fine = !name.empty() && IsPlainName(name);
            if (fine) { names.push_back(name); }
        }
        if (!fine) { said(L"guard_abilities must be a list of ability names (\"*Guard*\": every one with Guard in its name)"); }
        else { s.GuardAbilities = std::move(names); }
    }
    if (const Json* gun = value->Find("gun_socket"))   // (3.7.1; false or "": where the game puts it)
    {
        if ((gun->type == Json::Type::Bool && !gun->boolean) || Trim(StringOf(gun)).empty()) { s.GunSocket.clear(); }
        else if (!IsPlainName(Trim(StringOf(gun)))) { said(L"gun_socket must be a socket name (like \"Attach_Weapon_Right01\")"); }
        else { s.GunSocket = Trim(StringOf(gun)); }
    }
    // (3.7.7) another model on the gun while this shooter is on (false or "": the gun's own)
    if (const Json* mesh = value->Find("gun_mesh"))
    {
        if ((mesh->type == Json::Type::Bool && !mesh->boolean) || Trim(StringOf(mesh)).empty()) { s.GunMesh.clear(); }
        else
        {
            const std::wstring path = NormalizeObjectPath(StringOf(mesh));
            if (path.empty() || path.rfind(L"/Game/", 0) != 0) { said(L"gun_mesh must be a skeletal mesh's path (like \"/Game/Character/Weapon/WE0011_10/Model/WE0011_10\")"); }
            else { s.GunMesh = path; }
        }
    }
    // the camera
    const Json* camera = value->Find("camera");
    if (camera && camera->type != Json::Type::Object) { said(L"camera must be an object"); camera = nullptr; }
    for (const Json* from : {value, camera})
    {
        if (!from) { continue; }
        number(from, "distance", s.Distance, 0.0f, 3000.0f);
        number(from, "side", s.Side, -500.0f, 500.0f);
        number(from, "height", s.Height, -300.0f, 600.0f);
        number(from, "aim_distance", s.AimDistance, 0.0f, 3000.0f);
        number(from, "aim_side", s.AimSide, -500.0f, 500.0f);
        number(from, "aim_height", s.AimHeight, -300.0f, 600.0f);
        number(from, "pivot", s.Pivot, -100.0f, 400.0f);
        number(from, "fov", s.Fov, 0.0f, 150.0f);
        number(from, "aim_fov", s.AimFov, 5.0f, 150.0f);
        number(from, "zoom_fov", s.ZoomFov, 2.0f, 150.0f);
        number(from, "blend", s.CameraBlend, 0.0f, 5.0f);
        number(from, "yaw_speed", s.YawSpeed, 10.0f, 2000.0f);
        number(from, "pitch_speed", s.PitchSpeed, 10.0f, 2000.0f);
        number(from, "aim_scale", s.AimScale, 0.05f, 2.0f);
        number(from, "zoom_scale", s.ZoomScale, 0.05f, 2.0f);
        number(from, "mouse", s.Mouse, 0.0f, 20.0f);
        number(from, "pitch_min", s.PitchMin, -89.0f, 0.0f);
        number(from, "pitch_max", s.PitchMax, 0.0f, 89.0f);
        flag(from, "invert_y", s.InvertY);
        if (const Json* item = from->Find("camera_abilities"))
        {
            std::vector<std::wstring> names;
            bool fine = item->type == Json::Type::Array;
            for (size_t k = 0; fine && k < item->array.size(); ++k)
            {
                const std::wstring name = Trim(StringOf(&item->array[k]));
                fine = !name.empty() && IsPlainName(name);
                if (fine) { names.push_back(name); }
            }
            if (!fine) { said(L"camera_abilities must be a list of ability names (\"*NAtk*\": every one with NAtk in its name)"); }
            else { s.CameraAbilities = std::move(names); }
        }
    }
    // the reticle
    if (const Json* reticle = value->Find("reticle"))
    {
        if (reticle->type == Json::Type::Object)
        {
            number(reticle, "size", s.ReticleSize, 2.0f, 200.0f);
            number(reticle, "gap", s.ReticleGap, 0.0f, 200.0f);
            number(reticle, "thickness", s.ReticleThickness, 1.0f, 20.0f);
            color(reticle, "color", s.ReticleColor);
            color(reticle, "enemy_color", s.EnemyColor);
            color(reticle, "hit_color", s.HitColor);
            number(reticle, "hit_seconds", s.HitSeconds, 0.0f, 2.0f);
            flag(reticle, "ammo", s.Ammo);
            number(reticle, "scale", s.ReticleScale, 0.05f, 10.0f);
            number(reticle, "hud_scale", s.HudScale, 0.1f, 10.0f);
            text(reticle, "ui_folder", s.Ui);
        }
        else { said(L"reticle must be an object"); }
    }
    // (3.7.6) the targets: "hit_scale" (an enemy's body zone: its bounds times this), "crit": true / false or {"hits": 2,
    // "scale": 1, "color": [1, 0.3, 0.15]} (a shot through its head)
    number(value, "hit_scale", s.HitScale, 0.1f, 5.0f);
    if (const Json* crit = value->Find("crit"))
    {
        if (crit->type == Json::Type::Bool) { s.Crit = crit->boolean; }
        else if (crit->type == Json::Type::Object)
        {
            s.Crit = true;
            flag(crit, "on", s.Crit);
            float hits = static_cast<float>(s.CritHits);
            number(crit, "hits", hits, 1.0f, 4.0f);
            s.CritHits = static_cast<int>(hits);
            number(crit, "scale", s.CritScale, 0.1f, 5.0f);
            color(crit, "color", s.CritColor);
        }
        else { said(L"crit must be true, false or {\"hits\": 2, \"scale\": 1, \"color\": [1, 0.3, 0.15]}"); }
    }
    // the motions
    if (const Json* motions = value->Find("motions"))
    {
        if (motions->type == Json::Type::Bool) { s.Motions = motions->boolean; }
        else if (motions->type == Json::Type::Object)
        {
            flag(motions, "on", s.Motions);
            if (const Json* folder = motions->Find("folder"))
            {
                std::wstring f = Trim(StringOf(folder));
                while (!f.empty() && f.back() == L'/') { f.pop_back(); }
                if (f.rfind(L"/Game/", 0) != 0 || f.find_first_of(L". ") != std::wstring::npos) { said(L"motions folder must be a content folder like \"/Game/Motion/Player/PC0011_00_Vincent/Battle00\""); }
                else { s.Folder = f; }
            }
            if (const Json* prefix = motions->Find("prefix")) { s.Prefix = StringOf(prefix); }
            if (const Json* suffix = motions->Find("suffix")) { s.Suffix = StringOf(suffix); }
            text(motions, "idle", s.Idle);
            text(motions, "shot", s.Shot);
            text(motions, "reload", s.Reloading);
            text(motions, "switch", s.Switching);
            // (3.7.1) the stance and the walk and run of each kind; false or "": none (the game's own)
            for (const auto& [key, field] : std::initializer_list<std::pair<const char*, std::wstring*>>{
                     {"stand", &s.Stand}, {"walking", &s.Walking}, {"running", &s.Running}, {"walk", &s.Walk}, {"run", &s.Run}, {"back", &s.Back},
                     {"left", &s.Left}, {"right", &s.Right}, {"walk_reload", &s.WalkReload}, {"run_reload", &s.RunReload},
                     {"fly_stance", &s.FlyStance}})   // (3.7.7: the stance in the air, a motion's whole name: "m004_cf_st_a")
            {
                const Json* motion = motions->Find(key);
                if (!motion) { continue; }
                if ((motion->type == Json::Type::Bool && !motion->boolean) || Trim(StringOf(motion)).empty()) { field->clear(); }
                else { text(motions, key, *field); }
            }
            number(motions, "walk_speed", s.WalkSpeed, 10.0f, 2000.0f);
            number(motions, "run_speed", s.RunSpeed, 20.0f, 3000.0f);
            number(motions, "blend", s.PoseBlend, 0.0f, 3.0f);
            number(motions, "max_aim", s.MaxAim, 0.0f, 120.0f);
            flag(motions, "turn_actor", s.TurnActor);
            text(motions, "upper_body", s.UpperBody);
            text(motions, "slot", s.Slot);
            for (const auto& [key, list] : std::initializer_list<std::pair<const char*, std::vector<std::wstring>*>>{
                     {"spine", &s.Spine}, {"keep", &s.Keep}, {"keep_under", &s.KeepUnder}})
            {
                const Json* item = motions->Find(key);
                if (!item) { continue; }
                std::vector<std::wstring> names;
                bool fine = item->type == Json::Type::Array;
                for (size_t k = 0; fine && k < item->array.size(); ++k)
                {
                    const std::wstring name = Trim(StringOf(&item->array[k]));
                    fine = IsPlainName(name);
                    if (fine) { names.push_back(name); }
                }
                if (!fine) { said(Widen(key) + L" must be a list of bone names (\"*_Phy\": every bone ending with _Phy)"); continue; }
                *list = std::move(names);
            }
            if (const Json* share = motions->Find("share"))
            {
                std::vector<float> parts;
                bool fine = share->type == Json::Type::Array;
                for (size_t k = 0; fine && k < share->array.size(); ++k)
                {
                    float v = 0.0f;
                    fine = NumberOf(&share->array[k], v) && v >= 0.0f && v <= 1.0f;
                    parts.push_back(v);
                }
                if (!fine) { said(L"share must be a list of numbers from 0 to 1 (one for each spine bone)"); }
                else { s.Share = std::move(parts); }
            }
        }
        else { said(L"motions must be true, false or an object"); }
    }
    while (s.Share.size() < s.Spine.size()) { s.Share.push_back(s.Share.empty() ? 1.0f : s.Share.back()); }
    for (std::wstring* motion : {&s.Idle, &s.Stand, &s.Walking, &s.Running, &s.Walk, &s.Run, &s.Back, &s.Left, &s.Right, &s.Shot, &s.Reloading,
                                 &s.WalkReload, &s.RunReload, &s.Switching, &s.FlyStance})
    {
        if (!motion->empty() && !IsPlainName(*motion))
        {
            said(L"motion " + *motion + L" must be a motion's name (like \"rn_a\"); left out");
            motion->clear();
        }
    }
    if (!IsPlainName(s.Ui)) { said(L"ui_folder must be a folder name of the mod's (like \"dirge_ui\")"); s.Ui = L"dirge_ui"; }
    if (!IsPlainName(s.Slot)) { said(L"slot must be a slot name (like \"DefaultSlot\")"); s.Slot = L"DefaultSlot"; }
    // the guns
    if (const Json* weapons = value->Find("weapons"))
    {
        bool fine = true;
        std::vector<Shooter::Weapon> list;
        const std::vector<Shooter::Weapon> defaults = Shooter::DefaultWeapons();
        for (const Json* item : Items(weapons, fine))
        {
            if (item->type != Json::Type::Object) { fine = false; continue; }
            const std::wstring name = Trim(StringOf(item->Find("name")));
            Shooter::Weapon w = defaults.front();
            for (const auto& d : defaults) { if (NameEquals(d.Name, name)) { w = d; } }
            if (base)   // (3.7.7: a form's gun of the character's name is the character's gun with these settings over it)
            {
                for (const auto& d : base->Weapons) { if (NameEquals(d.Name, name)) { w = d; } }
            }
            if (!name.empty()) { w.Name = name; }
            text(item, "set", w.Set);
            // (3.7.7) its motions in the air: a set with its shot and reload (p007_ + m004_hf + _st_f + _remap); false: none
            if (const Json* fly = item->Find("fly_set"))
            {
                if ((fly->type == Json::Type::Bool && !fly->boolean) || Trim(StringOf(fly)).empty()) { w.FlySet.clear(); }
                else { text(item, "fly_set", w.FlySet); }
            }
            text(item, "damage_source", w.DamageSource);
            text(item, "reticle", w.Reticle);
            if (const Json* ability = item->Find("ability")) { w.Ability = Trim(StringOf(ability)); }
            float clip = static_cast<float>(w.Clip);
            number(item, "clip", clip, 1.0f, 999.0f);
            w.Clip = static_cast<int>(clip);
            number(item, "interval", w.Interval, 0.02f, 10.0f);
            flag(item, "automatic", w.Automatic);
            number(item, "reload", w.Reload, 0.0f, 10.0f);
            number(item, "spread", w.Spread, 0.0f, 30.0f);
            number(item, "recoil", w.Recoil, 0.0f, 30.0f);
            number(item, "range", w.Range, 100.0f, 100000.0f);
            number(item, "fire_at", w.FireAt, 0.05f, 1.0f);
            number(item, "aim_fov", w.AimFov, 0.0f, 150.0f);
            number(item, "kick_seconds", w.KickSeconds, 0.0f, 2.0f);
            for (const auto& [key, field] : std::initializer_list<std::pair<const char*, FormEffect*>>{{"muzzle", &w.Muzzle}, {"impact", &w.Impact}})
            {
                const Json* effect = item->Find(key);
                if (!effect) { continue; }
                if (effect->type == Json::Type::Null || (effect->type == Json::Type::Bool && !effect->boolean))
                {
                    *field = FormEffect{};
                    continue;
                }
                std::vector<FormEffect> one;
                if (!ParseFormEffects(effect, one) || one.size() != 1) { said(Widen(key) + L" must be an effect path or {\"effect\": path, \"socket\": ...}"); }
                else { *field = one.front(); }
            }
            // the gunshot: one sound or a list played together ({"bank": path, "cue": name, "start": s, "length": s, "volume": v})
            for (const char* key : {"sound", "sounds"})
            {
                const Json* sound = item->Find(key);
                if (!sound) { continue; }
                if (sound->type == Json::Type::Null || (sound->type == Json::Type::Bool && !sound->boolean))
                {
                    w.Sounds.clear();
                    continue;
                }
                std::vector<FormSound> list;
                if (!ParseFormSounds(sound, list) || list.empty() || list.size() > 8)
                {
                    said(Widen(key) + L" must be {\"bank\": path, \"cue\": name, \"start\": seconds, \"length\": seconds} or a list of up to 8 of them");
                }
                else { w.Sounds = std::move(list); }
            }
            if (const Json* sound = item->Find("reload_sound"))
            {
                std::vector<FormSound> one;
                if (sound->type == Json::Type::Null || (sound->type == Json::Type::Bool && !sound->boolean)) { w.ReloadSound = FormSound{}; }
                else if (!ParseFormSounds(sound, one) || one.size() != 1) { said(L"reload_sound must be {\"bank\": path, \"cue\": name}"); }
                else { w.ReloadSound = one.front(); }
            }
            if (!ParseTrigger(item->Find("fire_trigger"), w.FireTrigger)) { said(L"fire_trigger must be a trigger effect"); }
            if (!ParseTrigger(item->Find("kick"), w.Kick)) { said(L"kick must be a trigger effect"); }
            // (3.7.4) its upgrades: [{"item": "key_...", "id": 3860, "row": "P", "levels": 5}, {"item": ..., "interval": [0.92, ...]}, ...]
            if (const Json* ups = item->Find("upgrades"))
            {
                bool listed = true;
                std::vector<Shooter::Upgrade> made;
                for (const Json* one : Items(ups, listed))
                {
                    if (one->type != Json::Type::Object) { listed = false; continue; }
                    Shooter::Upgrade u;
                    u.Item = StringOf(one->Find("item"));
                    u.Row = StringOf(one->Find("row"));
                    bool fine = !u.Item.empty() && IsPlainName(u.Item) && (u.Row.empty() || (IsPlainName(u.Row) && u.Row.size() <= 16));
                    float v = 0.0f;
                    if (const Json* id = one->Find("id"))
                    {
                        if (NumberOf(id, v) && v >= 0.0f && v <= 9999999.0f && v == std::floor(v)) { u.Id = static_cast<int>(v); }
                        else { fine = false; }
                    }
                    if (const Json* levels = one->Find("levels"))
                    {
                        if (NumberOf(levels, v) && v >= 1.0f && v <= 99.0f && v == std::floor(v)) { u.Levels = static_cast<int>(v); }
                        else { fine = false; }
                    }
                    for (const auto& [key, list, low, high] : std::initializer_list<std::tuple<const char*, std::vector<float>*, float, float>>{
                             {"interval", &u.Interval, 0.05f, 20.0f}, {"reload", &u.Reload, 0.0f, 20.0f}, {"range", &u.Range, 0.05f, 100.0f}})
                    {
                        const Json* values = one->Find(key);
                        if (!values) { continue; }
                        if (values->type != Json::Type::Array || values->array.empty() || values->array.size() > 99) { fine = false; continue; }
                        for (const auto& x : values->array)
                        {
                            if (NumberOf(&x, v) && v >= low && v <= high) { list->push_back(v); }
                            else { fine = false; }
                        }
                    }
                    if (const Json* values = one->Find("clip"))
                    {
                        if (values->type != Json::Type::Array || values->array.empty() || values->array.size() > 99) { fine = false; }
                        else
                        {
                            for (const auto& x : values->array)
                            {
                                if (NumberOf(&x, v) && v >= -998.0f && v <= 998.0f && v == std::floor(v)) { u.Clip.push_back(static_cast<int>(v)); }
                                else { fine = false; }
                            }
                        }
                    }
                    if (!fine || u.MaxLevel() < 1)
                    {
                        said(L"weapon " + w.Name + L": upgrade " + (u.Item.empty() ? std::wstring(L"(no item)") : u.Item) +
                             L" must be {\"item\": an item's name, \"id\": its number, \"row\": a short tag, \"levels\": 1-99} with lists of numbers"
                             L" (\"interval\", \"reload\", \"range\": times these; \"clip\": rounds added) for levels 1, 2...; left out");
                        continue;
                    }
                    if (made.size() >= 8) { said(L"weapon " + w.Name + L": up to 8 upgrades; the rest left out"); break; }
                    made.push_back(std::move(u));
                }
                if (!listed) { said(L"weapon " + w.Name + L": upgrades must be a list of objects like {\"item\": \"key_...\", \"row\": \"P\", \"levels\": 5}"); }
                w.Upgrades = std::move(made);
            }
            if (!IsPlainName(w.Set) || w.DamageSource.empty() || !IsPlainName(w.DamageSource) || (!w.Ability.empty() && !IsPlainName(w.Ability)) ||
                !IsPlainName(w.Reticle) || (!w.FlySet.empty() && !IsPlainName(w.FlySet)))
            {
                said(L"weapon " + w.Name + L": set, fly_set, damage_source and ability must be names; left out");
                continue;
            }
            list.push_back(std::move(w));
        }
        if (!fine) { said(L"weapons must be a list of objects like {\"name\": \"CERBERUS\", \"clip\": 6}; bad entries ignored"); }
        if (!list.empty()) { s.Weapons = std::move(list); }
    }
    if (!bad.empty()) { Note(cfg, origin, at + L": " + bad); }
    out = s;
}

inline void ParseAnimSetRow(const Json& entry, std::wstring_view origin, const std::wstring& where, Config& cfg)
{
    if (entry.type != Json::Type::Object) { Note(cfg, origin, where + L" is not an object, skipped"); return; }
    if (const Json* enabled = entry.Find("enabled"); enabled && enabled->type == Json::Type::Bool && !enabled->boolean) { return; }
    AnimSetRow row;
    row.Origin = std::wstring(origin);
    bool ok = true;
    for (const char* key : {"character", "characters"})
    {
        for (const Json* item : Items(entry.Find(key), ok))
        {
            const std::wstring path = item->type == Json::Type::String ? CharacterPackPath(Widen(item->string)) : std::wstring{};
            if (path.empty()) { ok = false; continue; }
            AddUnique(row.Characters, path);
        }
    }
    if (!ok) { Note(cfg, origin, where + L" character: entries must be CharaSpec rows like \"PC0000_00_Cloud_Standard\"; bad entries ignored"); }
    if (row.Characters.empty())
    {
        Note(cfg, origin, where + L" names no \"character\" (a CharaSpec row such as \"PC0000_00_Cloud_Standard\"), skipped");
        return;
    }
    const auto sources = [&](const char* key, bool battle) {
        bool usable = true;
        for (const Json* item : Items(entry.Find(key), usable))
        {
            SetSource source;
            std::wstring from = StringOf(item);
            std::wstring as;
            AutoMatchMode automatic = AutoMatchMode::Off;
            if (item->type == Json::Type::Object)
            {
                for (const char* k : {"from", "set", "path", "use"}) { if (from.empty()) { from = StringOf(item->Find(k)); } }
                as = StringOf(item->Find("as"));
                bool onlyOk = true;
                for (const Json* word : Items(item->Find("only"), onlyOk))
                {
                    const std::wstring text = StringOf(word);
                    if (text.empty()) { onlyOk = false; continue; }
                    if (std::none_of(source.Only.begin(), source.Only.end(), [&](const std::wstring& w) { return NameEquals(w, text); })) { source.Only.push_back(text); }
                }
                if (!onlyOk) { Note(cfg, origin, where + L" " + Widen(key) + L": \"only\" must be a word or an array of words like [\"Shot\", \"Gun\"]; bad entries ignored"); }
                for (const char* k : {"auto", "match"})
                {
                    const Json* a = item->Find(k);
                    if (!a) { continue; }
                    if (!ParseAutoMatch(*a, automatic))
                    {
                        Note(cfg, origin, where + L" " + Widen(key) + L": \"" + Widen(k) + L"\" must be true, false, \"basic\", \"attacks\" or \"all\"; " +
                                              L"using \"attacks\" for " + from);
                        automatic = AutoMatchMode::Attacks;
                    }
                }
            }
            if (from.empty() || !ParseSetSource(from, source)) { usable = false; continue; }
            source.Auto = automatic;
            if (!source.Only.empty() && automatic == AutoMatchMode::Off)
            {
                Note(cfg, origin, where + L" " + Widen(key) + L": \"only\" picks what an \"auto\" source matches; " + from +
                                      L" has no \"auto\", so it is ignored");
                source.Only.clear();
            }
            if (!as.empty())
            {
                if (source.Folder || as.find_first_of(L"/.: ") != std::wstring::npos)
                {
                    Note(cfg, origin, where + L" " + Widen(key) + L": \"as\" names the set one set fills (like \"Battle00\"); ignored for " + source.Path);
                }
                else if (!NameEquals(as, ObjectNameOfPath(source.Path)))
                {
                    source.As = as;
                }
            }
            // A set goes where its name says: Battle* sets are battle sets, every other set a field set.
            const bool battleSet = source.Folder ? battle : IsBattleSetName(SetNameOf(source));
            if (battleSet != battle)
            {
                Note(cfg, origin, where + L" " + Widen(key) + L": " + source.Path + L" fills " + SetNameOf(source) + L", a " +
                                      (battleSet ? L"battle" : L"field") + L" set; used as a " + (battleSet ? L"battle" : L"field") + L" source");
            }
            auto& list = battleSet ? row.Battle : row.Field;
            AddSource(list, source);
        }
        if (!usable)
        {
            Note(cfg, origin, where + L" " + Widen(key) + L": entries must be folders like /Game/Motion/Player/PC0000_Cloud or sets like "
                                  L"/Game/Motion/Player/PC0000_Cloud/Battle00.Battle00; bad entries ignored");
        }
    };
    sources("battle", true);
    sources("field", false);
    bool setsOk = true;
    for (const Json* item : Items(entry.Find("sets"), setsOk))
    {
        const std::wstring name = StringOf(item);
        if (name.empty() || name.find_first_of(L"/.: ") != std::wstring::npos) { setsOk = false; continue; }
        if (std::none_of(row.Sets.begin(), row.Sets.end(), [&](const std::wstring& n) { return NameEquals(n, name); })) { row.Sets.push_back(name); }
    }
    if (!setsOk) { Note(cfg, origin, where + L" sets: entries must be set names like \"Battle01\"; bad entries ignored"); }
    {
        const Json* moves = entry.Find("moves");
        bool movesOk = !moves || moves->type == Json::Type::Object || moves->type == Json::Type::Array;
        const auto addMove = [&](std::wstring key, std::wstring set, const std::vector<std::wstring>& animations) {
            const size_t slash = key.find(L'/');
            if (set.empty() && slash != std::wstring::npos)
            {
                set = Trim(key.substr(0, slash));
                key = Trim(key.substr(slash + 1));
            }
            AnimMove move{set, key, {}, {}, {}};
            bool pathsOk = !animations.empty();
            bool clipped = false;
            for (const auto& animation : animations)
            {
                // (3.12.0) "path@from-to": only that part of it is played (seconds; either side may be left out)
                std::wstring text = animation;
                float from = 0.0f, to = -1.0f;
                if (const size_t at = text.rfind(L'@'); at != std::wstring::npos)
                {
                    const std::wstring clip = Trim(text.substr(at + 1));
                    text = text.substr(0, at);
                    const size_t dash = clip.find(L'-');
                    // (3.12.1: read without exceptions: the editor's copy of this file is built without them)
                    if (dash == std::wstring::npos) { pathsOk = false; }
                    else
                    {
                        const std::wstring a = Trim(clip.substr(0, dash)), b = Trim(clip.substr(dash + 1));
                        if (!a.empty() && !ParseSeconds(a, from)) { pathsOk = false; }
                        else if (!b.empty() && !ParseSeconds(b, to)) { pathsOk = false; }
                    }
                    if (!(from >= 0.0f && from < 3600.0f) || (to >= 0.0f && to <= from)) { pathsOk = false; }
                    clipped = clipped || from > 0.0f || to >= 0.0f;
                }
                const std::wstring path = NormalizeObjectPath(text);
                if (path.empty()) { pathsOk = false; }
                move.Chain.push_back(path);
                move.Clips.emplace_back(from, to);
            }
            if (pathsOk) { move.Animation = move.Chain.front(); }
            if (move.Chain.size() < 2 && !clipped)
            {
                move.Chain.clear();
                move.Clips.clear();
            }
            if (!clipped) { move.Clips.clear(); }
            if (!pathsOk || move.Key.empty() || move.Key.find_first_of(L"/.: ") != std::wstring::npos || move.Animation.empty() ||
                move.Set.find_first_of(L"/.: ") != std::wstring::npos)
            {
                movesOk = false;
                return;
            }
            const bool known = std::any_of(row.Moves.begin(), row.Moves.end(), [&](const AnimMove& m) {
                return NameEquals(m.Set, move.Set) && NameEquals(m.Key, move.Key);
            });
            if (known) { Note(cfg, origin, where + L" moves: " + (move.Set.empty() ? L"" : move.Set + L"/") + move.Key + L" is listed twice; the first one is kept"); }
            else { row.Moves.push_back(std::move(move)); }
        };
        // An animation path, or a list of them played one after another.
        const auto paths = [&](const Json* value, std::vector<std::wstring>& out) {
            out.clear();
            if (!value) { return; }
            if (value->type == Json::Type::String) { out.push_back(Widen(value->string)); return; }
            if (value->type != Json::Type::Array) { movesOk = false; return; }
            for (const auto& item : value->array)
            {
                if (item.type != Json::Type::String) { movesOk = false; out.clear(); return; }
                out.push_back(Widen(item.string));
            }
        };
        std::vector<std::wstring> animations;
        if (moves && moves->type == Json::Type::Object)
        {
            for (const auto& [key, value] : moves->object)
            {
                paths(&value, animations);
                if (animations.empty()) { movesOk = false; continue; }
                addMove(Trim(Widen(key)), {}, animations);
            }
        }
        else if (moves && moves->type == Json::Type::Array)
        {
            for (const auto& item : moves->array)
            {
                const Json* value = item.Find("animation");
                if (!value) { value = item.Find("use"); }
                if (!value) { value = item.Find("chain"); }
                paths(value, animations);
                if (animations.empty()) { movesOk = false; continue; }
                addMove(StringOf(item.Find("key")), StringOf(item.Find("set")), animations);
            }
        }
        if (!movesOk)
        {
            Note(cfg, origin, where + L" moves: entries must look like {\"set\": \"Battle00\", \"key\": \"B_Atk01_0\", \"animation\": \"/Game/Path/To/Animation\"} "
                                  L"(\"set\" optional; \"animation\" can be an array played one after another); bad entries ignored");
        }
        // "limit_breaks" (3.2): limit 1, 2, ... -> the animation (or chain) played as B_AtkLimit01_0, B_AtkLimit02_0, ...
        // An array lists them in order (null or "" skips one); an object names them by number or by animation name.
        // Moves of the same name win.
        const Json* limits = entry.Find("limit_breaks");
        if (!limits) { limits = entry.Find("limits"); }
        if (limits)
        {
            bool limitsOk = limits->type == Json::Type::Object || limits->type == Json::Type::Array;
            const auto addLimit = [&](std::wstring key, const Json* value) {
                if (!value || value->type == Json::Type::Null || (value->type == Json::Type::String && Trim(Widen(value->string)).empty())) { return; }
                if (!key.empty() && AllDigits(key) && key.size() <= 2)
                {
                    const int number = std::stoi(key);
                    if (number < 1 || number > 99) { limitsOk = false; return; }
                    key = std::wstring(L"B_AtkLimit") + (number < 10 ? L"0" : L"") + std::to_wstring(number) + L"_0";
                }
                if (!StartsWithFolded(key, L"B_AtkLimit")) { limitsOk = false; return; }
                if (std::any_of(row.Moves.begin(), row.Moves.end(), [&](const AnimMove& m) { return NameEquals(m.Key, key); }))
                {
                    Note(cfg, origin, where + L" limit_breaks: " + key + L" is also in \"moves\"; the move is kept");
                    return;
                }
                const bool before = movesOk; // paths and addMove report into movesOk
                movesOk = true;
                paths(value, animations);
                if (movesOk && !animations.empty()) { addMove(key, {}, animations); }
                if (!movesOk || animations.empty()) { limitsOk = false; }
                movesOk = before;
            };
            if (limits->type == Json::Type::Array)
            {
                for (size_t k = 0; k < limits->array.size(); ++k) { addLimit(std::to_wstring(k + 1), &limits->array[k]); }
            }
            else if (limits->type == Json::Type::Object)
            {
                for (const auto& [key, value] : limits->object) { addLimit(Trim(Widen(key)), &value); }
            }
            if (!limitsOk)
            {
                Note(cfg, origin, where + L" limit_breaks: entries must be animation paths (or arrays of them played one after another) in "
                                      L"limit order, null to skip one; bad entries ignored");
            }
        }
    }
    if (const Json* folder = entry.Find("field_actions"))
    {
        std::wstring name = StringOf(folder);
        while (!name.empty() && (name.back() == L'/' || name.back() == L'\\')) { name.pop_back(); }
        const size_t cut = name.find_last_of(L"/\\");
        if (cut != std::wstring::npos) { name.erase(0, cut + 1); } // "/Game/Motion/Player/PC0000_Cloud" -> "PC0000_Cloud"
        if (name.empty() || name.find_first_of(L".: ") != std::wstring::npos)
        {
            Note(cfg, origin, where + L" field_actions must be a motion folder name like \"PC0000_Cloud\"; ignored");
        }
        else
        {
            row.FieldActions = name;
        }
    }
    // 3.6.16 "cutscene_weapon_socket": a socket (or bone) of the character's mesh
    if (const Json* socket = entry.Find("cutscene_weapon_socket"))
    {
        const std::wstring name = Trim(StringOf(socket));
        if (name.empty() || name.find_first_of(L"/.: ") != std::wstring::npos)
        {
            Note(cfg, origin, where + L" cutscene_weapon_socket must be a socket name like \"Attach_Weapon_Left01\"; ignored");
        }
        else
        {
            row.CutsceneWeaponSocket = name;
        }
    }
    // 3.9.0 "voice": the voice its lines play in
    if (!ParseVoice(entry.Find("voice"), row.Speaks))
    {
        Note(cfg, origin, where + L" voice must be a voice bank (\"/Game/Sound/Voice/{language}/Character/Player/VO_...\"), \"own\", or "
                                 L"{\"bank\": ..., \"replaces\": [...]}; ignored");
    }
    if (!PakNames(entry, row.RequiresPaks))
    {
        Note(cfg, origin, where + L" requires_paks: entries must be pak or mod names like \"SephirothOverCloud_P\"; bad entries ignored");
    }
    // "skeleton": the character's own skeleton (its meshes get "sockets"; "cutscene" and "proportions" start from it).
    if (const Json* own = entry.Find("skeleton"))
    {
        row.Skeleton = NormalizeObjectPath(StringOf(own));
        if (row.Skeleton.empty()) { Note(cfg, origin, where + L" skeleton is not an object path; ignored"); }
    }
    // 3.8 "anim_blueprints_from": the skeleton the AnimBlueprints of the character's slot were made for (Cloud's, in Cloud's slot). They
    // run on meshes of "skeleton" instead: for a character whose animations are all on its own skeleton (retargeted ahead of time),
    // in another one's slot. Nothing else moves: no animation is adopted, no mesh is rebound.
    if (const Json* from = entry.Find("anim_blueprints_from"))
    {
        const std::wstring path = NormalizeObjectPath(StringOf(from));
        if (path.empty() || path.find(L'/') != 0)
        {
            Note(cfg, origin, where + L" anim_blueprints_from must be a skeleton path like /Game/Character/Player/PC0000_00_Cloud_Standard/Model/PC0000_00_Skeleton; ignored");
        }
        else if (row.Skeleton.empty())
        {
            Note(cfg, origin, where + L" anim_blueprints_from needs the row's \"skeleton\" (the skeleton they run on); ignored");
        }
        else if (PathEquals(path, row.Skeleton))
        {
            Note(cfg, origin, where + L" anim_blueprints_from is the row's own skeleton; nothing to do");
        }
        else
        {
            row.AnimBlueprintsFrom = path;
        }
    }
    // 3.9.1 "looks_from": a character blueprint (/Game/BluePrint/Character/Player/PC0000_00_Cloud_Standard: the slot's own
    // character's) whose looks the character gets when its own blueprint has none: the Toad status puts the game's frog on
    // it (a character in another's slot, on a blueprint the game never toads, otherwise keeps its model and plays the frog's
    // moves)
    if (const Json* looks = entry.Find("looks_from"))
    {
        std::wstring path = NormalizeObjectPath(StringOf(looks));
        if (path.empty() || path.rfind(L"/Game/", 0) != 0)
        {
            Note(cfg, origin, where + L" looks_from must be a character blueprint like /Game/BluePrint/Character/Player/PC0000_00_Cloud_Standard; ignored");
        }
        else
        {
            if (path.size() < 2 || path.compare(path.size() - 2, 2, L"_C") != 0) { path += L"_C"; }
            row.LooksFrom = path;
        }
    }
    // "sockets": [{"socket": "Attach_Weapon01", "use": "Attach_Weapon_Right01"}]: the socket the game asks for -> the socket
    // (or bone) of this character that stands in for it (an object {"Attach_Weapon01": "Attach_Weapon_Right01"} works too).
    if (const Json* sockets = entry.Find("sockets"))
    {
        bool socketsOk = sockets->type == Json::Type::Object || sockets->type == Json::Type::Array;
        const auto addSocket = [&](const std::wstring& name, const std::wstring& use, bool scaled) {
            if (name.empty() || use.empty() || name.find_first_of(L"/.:'\"") != std::wstring::npos || use.find_first_of(L"/.:'\"") != std::wstring::npos)
            {
                socketsOk = false;
                return false;
            }
            // (a socket standing in for itself is nothing to do, unless it gets a scale of its own)
            if (NameEquals(name, use) && !scaled) { return false; }
            if (std::any_of(row.Sockets.begin(), row.Sockets.end(), [&](const auto& s) { return NameEquals(s.first, name); }))
            {
                Note(cfg, origin, where + L" sockets: " + name + L" is listed twice; the first one is kept");
                return false;
            }
            row.Sockets.emplace_back(name, use);
            return true;
        };
        if (sockets->type == Json::Type::Object)
        {
            for (const auto& [key, value] : sockets->object) { addSocket(Trim(Widen(key)), StringOf(&value), false); }
        }
        else if (sockets->type == Json::Type::Array)
        {
            for (const auto& item : sockets->array)
            {
                std::wstring name = StringOf(item.Find("socket"));
                if (name.empty()) { name = StringOf(item.Find("name")); }
                std::wstring use = StringOf(item.Find("use"));
                if (use.empty()) { use = StringOf(item.Find("to")); }
                if (use.empty()) { use = StringOf(item.Find("bone")); }
                // 3.8.1: the stand-in's own placement on its bone: "location" [x, y, z], "rotation" [pitch, yaw, roll], "scale"
                // (a number or [x, y, z]: what the game attaches there is scaled with it); "hidden": true shrinks it out of
                // sight (HiddenSocketScale)
                SocketPlacement place;
                bool placeOk = true;
                const auto three = [&](const Json* value, std::array<float, 3>& out, float lo, float hi) {
                    if (!value || value->type != Json::Type::Array || value->array.size() != 3) { return false; }
                    for (size_t c = 0; c < 3; ++c)
                    {
                        if (!NumberOf(&value->array[c], out[c]) || !(out[c] >= lo && out[c] <= hi)) { return false; }
                    }
                    return true;
                };
                if (const Json* value = item.Find("location"))
                {
                    if (three(value, place.Location, -100000.0f, 100000.0f)) { place.HasLocation = true; }
                    else { placeOk = false; }
                }
                if (const Json* value = item.Find("rotation"))
                {
                    if (three(value, place.Rotation, -720.0f, 720.0f)) { place.HasRotation = true; }
                    else { placeOk = false; }
                }
                if (const Json* hidden = item.Find("hidden"))
                {
                    if (hidden->type != Json::Type::Bool) { placeOk = false; }
                    else if (hidden->boolean)
                    {
                        place.Scale = {HiddenSocketScale, HiddenSocketScale, HiddenSocketScale};
                        place.HasScale = true;
                    }
                }
                if (const Json* value = item.Find("scale"); value && !place.HasScale)
                {
                    float n = 0.0f;
                    bool ok = true;
                    if (NumberOf(value, n)) { place.Scale = {n, n, n}; }
                    else if (!three(value, place.Scale, -1.0e9f, 1.0e9f)) { ok = false; }
                    for (float& c : place.Scale)
                    {
                        if (!(c >= 0.0f && c <= 100.0f)) { ok = false; }
                        // (no zero: a scale of 0 gives what is attached there a transform that cannot be inverted)
                        c = std::max(c, HiddenSocketScale);
                    }
                    if (ok) { place.HasScale = true; }
                    else { placeOk = false; }
                }
                if (!placeOk)
                {
                    Note(cfg, origin, where + L" sockets: " + name + L": \"location\" and \"rotation\" take [x, y, z], \"scale\" a number or [x, y, z] "
                                      L"from 0 to 100, \"hidden\" true or false; the stand-in keeps what it copies where these are bad");
                }
                if (addSocket(name, use, place.Any()) && place.Any()) { row.SocketPlacements.emplace_back(name, place); }
            }
        }
        if (!socketsOk)
        {
            Note(cfg, origin, where + L" sockets: entries must look like {\"socket\": \"Attach_Weapon01\", \"use\": \"Attach_Weapon_Right01\"} (the socket "
                                  L"the game uses -> a socket or bone of this character); bad entries ignored");
        }
        if (!row.Sockets.empty() && row.Skeleton.empty())
        {
            Note(cfg, origin, where + L" sockets need the character's own \"skeleton\" (its meshes get the sockets); ignored");
            row.Sockets.clear();
        }
    }
    row.KeepProportions = ProportionsOf(entry, false);
    if (const Json* first = entry.Find("override"); first && first->type == Json::Type::Bool) { row.Override = first->boolean; }
    if (row.KeepProportions && row.Skeleton.empty())
    {
        Note(cfg, origin, where + L" proportions needs the character's own \"skeleton\"; ignored");
        row.KeepProportions = false;
    }
    // "cutscene": the skeleton whose cutscene animations the character's mesh plays (a family with that skeleton as hub).
    if (const Json* cutscene = entry.Find("cutscene"))
    {
        std::wstring skeleton = row.Skeleton;
        std::wstring hub = NormalizeObjectPath(StringOf(cutscene));
        if (cutscene->type == Json::Type::Object)
        {
            if (const std::wstring own = NormalizeObjectPath(StringOf(cutscene->Find("skeleton"))); !own.empty()) { skeleton = own; }
            hub = NormalizeObjectPath(StringOf(cutscene->Find("hub")));
            if (hub.empty()) { hub = NormalizeObjectPath(StringOf(cutscene->Find("plays"))); }
        }
        if (skeleton.empty() || hub.empty() || PathEquals(skeleton, hub))
        {
            Note(cfg, origin, where + L" cutscene needs the character's own \"skeleton\" and the \"hub\" skeleton whose cutscenes it plays "
                                  L"(two different skeleton paths); ignored");
        }
        else
        {
            Pair family;
            family.Use = Method::Family;
            family.Receiving = skeleton;
            family.Animation = {hub};
            family.Hub = hub;
            family.RequiresPaks = row.RequiresPaks;
            family.KeepProportions = row.KeepProportions;
            family.Origin = std::wstring(origin);
            cfg.Pairs.push_back(std::move(family));
        }
    }
    ParseAbilities(entry, origin, where, cfg, row);
    ParseForms(entry, origin, where, cfg, row);
    ParseShooter(entry.Find("shooter"), origin, where, cfg, row.Shooting);   // (3.7)
    if (row.Battle.empty() && row.Field.empty() && row.Moves.empty() && row.FieldActions.empty() && row.Sockets.empty() && !row.KeepProportions &&
        row.Abilities.empty() && row.Preload.empty() && row.PackAssets.empty() && !row.Forms.HasList() && row.CutsceneWeaponSocket.empty() &&
        !row.Shooting.On && row.AnimBlueprintsFrom.empty() && !row.Speaks.Set && row.LooksFrom.empty())
    {
        if (!entry.Find("cutscene"))
        {
            Note(cfg, origin, where + L" has no \"battle\", \"field\", \"moves\", \"sockets\", \"proportions\", \"abilities\", \"pack_assets\", \"preload\", "
                                  L"\"forms\", \"cutscene_weapon_socket\", \"shooter\" or \"voice\", skipped");
        }
        return;
    }
    cfg.AnimSets.push_back(std::move(row));
}

// ---- (3.14.0) "kawaii" ------------------------------------------------------------------------------------------------
// [x, y, z] (each within +-limit) into `out` when present; `ok` false when it is there and not that.
inline void KawaiiTriple(const Json* value, float (&out)[3], float limit, bool& ok)
{
    if (!value) { return; }
    float v[3]{};
    bool fine = value->type == Json::Type::Array && value->array.size() == 3;
    for (size_t k = 0; fine && k < 3; ++k) { fine = NumberOf(&value->array[k], v[k]) && std::fabs(v[k]) <= limit; }
    if (!fine)
    {
        ok = false;
        return;
    }
    for (size_t k = 0; k < 3; ++k) { out[k] = v[k]; }
}

// A number within [lo, hi] into `out` when present; `ok` false when it is there and not that.
inline void KawaiiNumber(const Json& entry, const char* key, float& out, float lo, float hi, bool& ok)
{
    const Json* value = entry.Find(key);
    if (!value) { return; }
    float v = 0.0f;
    if (!NumberOf(value, v) || v < lo || v > hi)
    {
        ok = false;
        return;
    }
    out = v;
}

inline void KawaiiInteger(const Json& entry, const char* key, int& out, int lo, int hi, bool& ok)
{
    const Json* value = entry.Find(key);
    if (!value) { return; }
    float v = 0.0f;
    if (!NumberOf(value, v) || v != std::floor(v) || v < static_cast<float>(lo) || v > static_cast<float>(hi))
    {
        ok = false;
        return;
    }
    out = static_cast<int>(v);
}

inline void KawaiiBool(const Json& entry, const char* key, bool& out, bool& ok)
{
    const Json* value = entry.Find(key);
    if (!value) { return; }
    if (value->type != Json::Type::Bool)
    {
        ok = false;
        return;
    }
    out = value->boolean;
}

// Bone names (a name, or a list of them) added to `out`; `ok` false when one is not a bone's name.
inline void KawaiiBones(const Json* value, std::vector<std::wstring>& out, bool& ok)
{
    for (const Json* bone : Items(value, ok))
    {
        const std::wstring name = StringOf(bone);
        if (!IsPlainName(name))
        {
            ok = false;
            continue;
        }
        AddUniqueName(out, name);
    }
}

// [[time, value], ...]: times rising (each within 0 - maxTime: 10, the chains' curves), values within +-1e4; at most
// MaxKawaiiCurveKeys.
inline bool KawaiiCurveOf(const Json* value, KawaiiCurve& out, float maxTime = 10.0f)
{
    out.Keys.clear();
    if (!value) { return true; }
    if (value->type != Json::Type::Array || value->array.size() > MaxKawaiiCurveKeys) { return false; }
    for (const auto& key : value->array)
    {
        float t = 0.0f, v = 0.0f;
        if (key.type != Json::Type::Array || key.array.size() != 2 || !NumberOf(&key.array[0], t) || !NumberOf(&key.array[1], v) || t < 0.0f || t > maxTime ||
            std::fabs(v) > 1.0e4f || (!out.Keys.empty() && t <= out.Keys.back().first))
        {
            out.Keys.clear();
            return false;
        }
        out.Keys.emplace_back(t, v);
    }
    return true;
}

inline bool KawaiiComplianceOf(const Json* value, KawaiiCompliance& out)
{
    const std::wstring name = FoldedKey(StringOf(value));
    static const std::pair<const wchar_t*, KawaiiCompliance> names[] = {
        {L"concrete", KawaiiCompliance::Concrete}, {L"wood", KawaiiCompliance::Wood},     {L"leather", KawaiiCompliance::Leather},
        {L"tendon", KawaiiCompliance::Tendon},     {L"rubber", KawaiiCompliance::Rubber}, {L"muscle", KawaiiCompliance::Muscle},
        {L"fat", KawaiiCompliance::Fat}};
    for (const auto& [n, c] : names)
    {
        if (name == n)
        {
            out = c;
            return true;
        }
    }
    return false;
}

// One collision shape of a node's "spheres", "capsules", "tapered_capsules", "boxes" or "planes" (kind 0 - 4).
inline bool KawaiiLimitOf(const Json& item, int kind, KawaiiLimit& out, std::wstring& why)
{
    if (item.type != Json::Type::Object)
    {
        why = L"each must be an object";
        return false;
    }
    bool ok = true;
    out.Bone = StringOf(item.Find("bone"));
    if (out.Bone.empty()) { out.Bone = StringOf(item.Find("driving_bone")); }
    if (!out.Bone.empty() && !IsPlainName(out.Bone))
    {
        why = L"\"bone\" must be a bone's name";
        return false;
    }
    if (out.Bone.empty() && kind != 4)
    {
        why = L"needs its \"bone\" (the bone it is on)";
        return false;
    }
    KawaiiTriple(item.Find("offset"), out.Offset, 1.0e5f, ok);
    KawaiiTriple(item.Find("offset_location"), out.Offset, 1.0e5f, ok);
    KawaiiTriple(item.Find("rotation"), out.Rotation, 1.0e4f, ok);
    KawaiiTriple(item.Find("offset_rotation"), out.Rotation, 1.0e4f, ok);
    switch (kind)
    {
    case 0:
    {
        KawaiiNumber(item, "radius", out.Radius, 0.0f, 1.0e5f, ok);
        const std::wstring type = FoldedKey(StringOf(item.Find("limit_type")));
        if (type == L"inner") { out.Inner = true; }
        else if (!type.empty() && type != L"outer") { ok = false; }
        break;
    }
    case 1:
        KawaiiNumber(item, "radius", out.Radius, 0.0f, 1.0e5f, ok);
        KawaiiNumber(item, "length", out.Length, 0.0f, 1.0e5f, ok);
        break;
    case 2:
        KawaiiNumber(item, "radius0", out.Radius0, 0.0f, 1.0e5f, ok);
        KawaiiNumber(item, "radius1", out.Radius1, 0.0f, 1.0e5f, ok);
        KawaiiNumber(item, "length", out.Length, 0.0f, 1.0e5f, ok);
        break;
    case 3:
        KawaiiTriple(item.Find("extent"), out.Extent, 1.0e5f, ok);
        if (out.Extent[0] < 0.0f || out.Extent[1] < 0.0f || out.Extent[2] < 0.0f) { ok = false; }
        break;
    default:
        break;
    }
    if (!ok)
    {
        why = L"\"offset\" and \"rotation\" must be [x, y, z] (rotation: pitch, yaw, roll in degrees), sizes 0 or more" +
              std::wstring(kind == 0 ? L", \"limit_type\" \"outer\" or \"inner\"" : kind == 3 ? L", \"extent\" [x, y, z] (half sizes)" : L"");
        return false;
    }
    return true;
}

// (3.15.0) A node's "pose_waves" and "pose_animation" (its bones' pose animated before the physics runs).
inline void ParseKawaiiPoseAnimation(const Json& item, std::wstring_view origin, const std::wstring& at, Config& cfg, KawaiiNode& node)
{
    if (const Json* waves = item.Find("pose_waves"))
    {
        bool fine = waves->type == Json::Type::Array;
        for (size_t k = 0; fine && k < waves->array.size(); ++k)
        {
            const Json& w = waves->array[k];
            KawaiiWave wave;
            bool ok = w.type == Json::Type::Object && node.PoseWaves.size() < MaxKawaiiWaves;
            if (ok)
            {
                KawaiiTriple(w.Find("axis"), wave.Axis, 1.0e3f, ok);
                KawaiiBool(w, "local_axis", wave.LocalAxis, ok);
                KawaiiNumber(w, "degrees", wave.Degrees, -180.0f, 180.0f, ok);
                KawaiiNumber(w, "seconds", wave.Seconds, 0.05f, 600.0f, ok);
                KawaiiNumber(w, "phase", wave.Phase, -1.0e5f, 1.0e5f, ok);
                KawaiiNumber(w, "phase_per_bone", wave.PhasePerBone, -1.0e4f, 1.0e4f, ok);
                KawaiiNumber(w, "phase_per_root", wave.PhasePerRoot, -1.0e4f, 1.0e4f, ok);
                ok = ok && KawaiiCurveOf(w.Find("degrees_curve"), wave.DegreesCurve);
                if (const Json* phases = ok ? w.Find("root_phases") : nullptr)
                {
                    ok = phases->type == Json::Type::Array && phases->array.size() <= MaxKawaiiRoots + 1;
                    for (size_t r = 0; ok && r < phases->array.size(); ++r)
                    {
                        float v = 0.0f;
                        ok = NumberOf(&phases->array[r], v) && std::fabs(v) <= 1.0e5f;
                        if (ok) { wave.RootPhases.push_back(v); }
                    }
                }
                ok = ok && (wave.Axis[0] != 0.0f || wave.Axis[1] != 0.0f || wave.Axis[2] != 0.0f);
            }
            if (!ok)
            {
                fine = false;
                continue;
            }
            node.PoseWaves.push_back(std::move(wave));
        }
        if (!fine)
        {
            Note(cfg, origin, at + L" pose_waves must be [{\"axis\": [x, y, z] (not all 0), \"degrees\" (-180 - 180), \"seconds\" (0.05 - 600), \"phase\", "
                                  L"\"phase_per_bone\", \"phase_per_root\" (degrees), \"root_phases\" ([degrees, ...] a chain each), \"degrees_curve\", \"local_axis\"}], " + std::to_wstring(MaxKawaiiWaves) +
                                  L" at most; bad ones ignored");
        }
    }
    const Json* anim = item.Find("pose_animation");
    if (!anim) { return; }
    bool ok = anim->type == Json::Type::Object;
    KawaiiPoseAnimation pa;
    if (ok)
    {
        KawaiiNumber(*anim, "fps", pa.Fps, 1.0f, 1000.0f, ok);
        KawaiiNumber(*anim, "speed", pa.Speed, -100.0f, 100.0f, ok);
        KawaiiNumber(*anim, "weight", pa.Weight, 0.0f, 1.0f, ok);
        KawaiiBool(*anim, "additive", pa.Additive, ok);
    }
    auto tracks = std::make_shared<std::vector<KawaiiKeyTrack>>();
    const Json* list = ok ? anim->Find("tracks") : nullptr;
    ok = ok && list && list->type == Json::Type::Object && !list->object.empty() && list->object.size() <= MaxKawaiiKeyTracks;
    size_t frames = 0;
    for (size_t t = 0; ok && t < list->object.size(); ++t)
    {
        const auto& [bone, keys] = list->object[t];
        KawaiiKeyTrack track;
        track.Bone = Widen(bone);
        ok = IsPlainName(track.Bone) && keys.type == Json::Type::Array && !keys.array.empty() && keys.array.size() <= MaxKawaiiKeyFrames &&
             (frames == 0 || keys.array.size() == frames || keys.array.size() == 1);
        for (size_t f = 0; ok && f < keys.array.size(); ++f)
        {
            const Json& key = keys.array[f];
            std::array<float, 4> q{};
            ok = key.type == Json::Type::Array && key.array.size() == 4;
            for (size_t c = 0; ok && c < 4; ++c) { ok = NumberOf(&key.array[c], q[c]) && std::fabs(q[c]) <= 2.0f; }
            const float len = ok ? std::sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3]) : 0.0f;
            ok = ok && len > 1.0e-4f;
            if (ok)
            {
                for (float& c : q) { c /= len; }
                track.Keys.push_back(q);
            }
        }
        if (ok && keys.array.size() > 1) { frames = keys.array.size(); }
        if (ok) { tracks->push_back(std::move(track)); }
    }
    if (!ok)
    {
        Note(cfg, origin, at + L" pose_animation must be {\"tracks\": {\"bone\": [[x, y, z, w], ...] (each bone's local rotation a frame; " +
                              std::to_wstring(MaxKawaiiKeyTracks) + L" bones and " + std::to_wstring(MaxKawaiiKeyFrames) +
                              L" frames at most, every track as long, or one frame), \"fps\" (1 - 1000), \"speed\", \"weight\" (0 - 1), \"additive\"}; ignored");
        return;
    }
    pa.Tracks = std::move(tracks);
    node.PoseAnimation = std::move(pa);
}

inline bool KawaiiSyncDirectionOf(const Json* value, KawaiiSyncDirection& out)
{
    if (!value) { return true; }
    const std::wstring name = FoldedKey(StringOf(value));
    if (name == L"both") { out = KawaiiSyncDirection::Both; }
    else if (name == L"positive" || name == L"+") { out = KawaiiSyncDirection::Positive; }
    else if (name == L"negative" || name == L"-") { out = KawaiiSyncDirection::Negative; }
    else if (name == L"none") { out = KawaiiSyncDirection::None; }
    else { return false; }
    return true;
}

// (3.17.0) A node's "sync_bones" (KawaiiPhysics' SyncBones).
inline void ParseKawaiiSyncBones(const Json& item, std::wstring_view origin, const std::wstring& at, Config& cfg, KawaiiNode& node)
{
    const Json* list = item.Find("sync_bones");
    if (!list) { return; }
    if (list->type != Json::Type::Array)
    {
        Note(cfg, origin, at + L" sync_bones must be an array; ignored");
        return;
    }
    for (size_t k = 0; k < list->array.size(); ++k)
    {
        const Json& s = list->array[k];
        const std::wstring here = at + L" sync_bones[" + std::to_wstring(k) + L"]";
        if (node.SyncBones.size() >= MaxKawaiiSyncBones)
        {
            Note(cfg, origin, at + L" sync_bones: " + std::to_wstring(MaxKawaiiSyncBones) + L" at most; the rest ignored");
            break;
        }
        KawaiiSyncBone sync;
        sync.Bone = s.type == Json::Type::Object ? StringOf(s.Find("bone")) : std::wstring{};
        if (!IsPlainName(sync.Bone))
        {
            Note(cfg, origin, here + L" needs its \"bone\" (the animated bone the chains follow); ignored");
            continue;
        }
        bool ok = true;
        const Json* targets = s.Find("target_roots");
        if (!targets) { targets = s.Find("targets"); }
        if (!targets || targets->type != Json::Type::Array || targets->array.empty())
        {
            Note(cfg, origin, here + L" needs \"target_roots\" (bones of the node's chains: names or {\"bone\", \"include_child_bones\", "
                                    L"\"scale_curve_by_bone_length_rate\"}); ignored");
            continue;
        }
        for (const Json& t : targets->array)
        {
            KawaiiSyncTarget target;
            if (t.type == Json::Type::String) { target.Bone = StringOf(&t); }
            else if (t.type == Json::Type::Object)
            {
                target.Bone = StringOf(t.Find("bone"));
                KawaiiBool(t, "include_child_bones", target.IncludeChildBones, ok);
                if (!KawaiiCurveOf(t.Find("scale_curve_by_bone_length_rate"), target.ScaleCurve)) { ok = false; }
            }
            if (!IsPlainName(target.Bone) || sync.Targets.size() >= MaxKawaiiSyncTargets)
            {
                ok = false;
                continue;
            }
            sync.Targets.push_back(std::move(target));
        }
        KawaiiTriple(s.Find("global_scale"), sync.GlobalScale, 1.0f, ok);
        for (float& g : sync.GlobalScale)
        {
            if (g < 0.0f)
            {
                g = 0.0f;
                ok = false;
            }
        }
        if (!KawaiiCurveOf(s.Find("scale_curve_by_delta_distance"), sync.ScaleCurveByDeltaDistance, 1.0e4f)) { ok = false; }
        const char* const axes[] = {"apply_direction_x", "apply_direction_y", "apply_direction_z"};
        for (int a = 0; a < 3; ++a)
        {
            if (!KawaiiSyncDirectionOf(s.Find(axes[a]), sync.Direction[a])) { ok = false; }
        }
        KawaiiBool(s, "enable_distance_attenuation", sync.DistanceAttenuation, ok);
        KawaiiNumber(s, "attenuation_inner_radius", sync.AttenuationInnerRadius, 0.0f, 1.0e5f, ok);
        KawaiiNumber(s, "attenuation_outer_radius", sync.AttenuationOuterRadius, 0.0f, 1.0e5f, ok);
        KawaiiNumber(s, "max_attenuation_rate", sync.MaxAttenuationRate, 0.0f, 1.0f, ok);
        if (!ok)
        {
            Note(cfg, origin, here + L": target_roots bone names (or {\"bone\", \"include_child_bones\", \"scale_curve_by_bone_length_rate\"}, " +
                                  std::to_wstring(MaxKawaiiSyncTargets) + L" at most), global_scale [x, y, z] (0 - 1), scale_curve_by_delta_distance [[cm, "
                                  L"scale], ...], apply_direction_x / _y / _z \"both\", \"positive\", \"negative\" or \"none\", attenuation radii (cm, 0 or "
                                  L"more), max_attenuation_rate (0 - 1); bad ones keep their defaults");
        }
        if (sync.Targets.empty()) { continue; }
        node.SyncBones.push_back(std::move(sync));
    }
}

// ---- (3.18.0) external forces, wind presets, sets, triggers ----
// [min, max] (each within lo - hi, min <= max) into `out` when present; `ok` false when it is there and not that.
inline void KawaiiInterval(const Json* value, float (&out)[2], float lo, float hi, bool& ok)
{
    if (!value) { return; }
    float v[2]{};
    bool fine = value->type == Json::Type::Array && value->array.size() == 2;
    for (size_t k = 0; fine && k < 2; ++k) { fine = NumberOf(&value->array[k], v[k]) && v[k] >= lo && v[k] <= hi; }
    if (!fine || v[0] > v[1])
    {
        ok = false;
        return;
    }
    out[0] = v[0];
    out[1] = v[1];
}

// A gameplay tag's name ("KawaiiPhysics.Shared.Default"): letters, digits, '_' and '-' between dots.
inline bool IsTagName(std::wstring_view tag)
{
    if (tag.empty() || tag.size() > 128 || tag.front() == L'.' || tag.back() == L'.') { return false; }
    for (size_t i = 0; i < tag.size(); ++i)
    {
        const wchar_t c = tag[i];
        if (c == L'.')
        {
            if (tag[i - 1] == L'.') { return false; }
            continue;
        }
        if (!((c >= L'a' && c <= L'z') || (c >= L'A' && c <= L'Z') || (c >= L'0' && c <= L'9') || c == L'_' || c == L'-')) { return false; }
    }
    return true;
}

// Gameplay tag matching (FGameplayTag::MatchesTag): "A.B" matches "A.B" and, not exact, "A".
inline bool KawaiiTagMatches(std::wstring_view tag, std::wstring_view filter, bool exact)
{
    if (tag.empty() || filter.empty()) { return false; }
    if (NameEquals(tag, filter)) { return true; }
    if (exact || tag.size() <= filter.size() || tag[filter.size()] != L'.') { return false; }
    return NameEquals(tag.substr(0, filter.size()), filter);
}
inline bool KawaiiTagFilterPasses(std::wstring_view tag, const std::vector<std::wstring>& filters, bool exact)
{
    if (filters.empty()) { return true; }
    return std::any_of(filters.begin(), filters.end(), [&](const std::wstring& f) { return KawaiiTagMatches(tag, f, exact); });
}

// The built-in wind presets (KawaiiPhysics' Wind Scope presets): Breeze, Strong, Storm.
inline const std::vector<KawaiiWindPreset>& KawaiiBuiltInWindPresets()
{
    static const std::vector<KawaiiWindPreset> presets = [] {
        std::vector<KawaiiWindPreset> list(3);
        const auto set = [](KawaiiWindPreset& p, const wchar_t* name, float c, float s, float sp, float r, float rp, float rd, float cmin, float cmax, float cp,
                            float rnd, float rndp, float noise) {
            p.Name = name;
            p.ConstantForce = c;
            p.SwayForce = s;
            p.SwayPeriod = sp;
            p.RippleForce = r;
            p.RipplePeriod = rp;
            p.RippleTipPhaseDelay = rd;
            p.StrengthCycleRange[0] = cmin;
            p.StrengthCycleRange[1] = cmax;
            p.StrengthCyclePeriod = cp;
            p.RandomForce = rnd;
            p.RandomForcePeriod = rndp;
            p.WindDirectionNoiseAngle = noise;
        };
        set(list[0], L"Breeze", 2.0f, 1.0f, 3.0f, 1.0f, 1.2f, 120.0f, 0.6f, 1.0f, 20.0f, 0.5f, 0.8f, 5.0f);
        set(list[1], L"Strong", 8.0f, 4.0f, 1.6f, 3.0f, 0.5f, 120.0f, 0.7f, 1.3f, 12.0f, 2.0f, 0.5f, 10.0f);
        set(list[2], L"Storm", 15.0f, 10.0f, 0.9f, 8.0f, 0.3f, 180.0f, 0.5f, 1.6f, 7.0f, 6.0f, 0.3f, 20.0f);
        return list;
    }();
    return presets;
}

// A wind preset by name ("Breeze", "KawaiiPhysics.WindPreset.Breeze", or one of the files'): the files' own first (when
// the files have any, only theirs, as KawaiiPhysics does with a preset data asset), else the built-in ones.
inline const KawaiiWindPreset* FindKawaiiWindPreset(const Config& cfg, std::wstring_view name)
{
    std::wstring_view shortName = name;
    if (const size_t dot = name.find_last_of(L'.'); dot != std::wstring_view::npos) { shortName = name.substr(dot + 1); }
    const auto& list = cfg.KawaiiWindPresets.empty() ? KawaiiBuiltInWindPresets() : cfg.KawaiiWindPresets;
    for (const auto& p : list)
    {
        if (NameEquals(p.Name, name) || NameEquals(p.Name, shortName)) { return &p; }
    }
    return nullptr;
}

// FKawaiiProceduralWindPreset::ToDynamicParams applied to a procedural wind (its 11 settings).
inline void ApplyKawaiiWindPreset(const KawaiiWindPreset& p, KawaiiExternalForce& f)
{
    f.ConstantForce = std::max(p.ConstantForce, 0.0f);
    f.SwayForce = std::max(p.SwayForce, 0.0f);
    f.SwayPeriod = std::max(p.SwayPeriod, 0.01f);
    f.RippleForce = std::max(p.RippleForce, 0.0f);
    f.RipplePeriod = std::max(p.RipplePeriod, 0.01f);
    f.RippleTipPhaseDelay = p.RippleTipPhaseDelay;
    f.StrengthCycleRange[0] = p.StrengthCycleRange[0];
    f.StrengthCycleRange[1] = p.StrengthCycleRange[1];
    f.StrengthCyclePeriod = std::max(p.StrengthCyclePeriod, 0.01f);
    f.RandomForce = std::max(p.RandomForce, 0.0f);
    f.RandomForcePeriod = std::max(p.RandomForcePeriod, 0.01f);
    f.WindDirectionNoiseAngle = std::max(p.WindDirectionNoiseAngle, 0.0f);
}

// [[time, x, y, z], ...]: times rising (0 - 1e4), values within +-1e6; at most MaxKawaiiCurveKeys.
inline bool KawaiiVectorCurveOf(const Json* value, KawaiiVectorCurve& out)
{
    out.Keys.clear();
    if (!value) { return true; }
    if (value->type != Json::Type::Array || value->array.size() > MaxKawaiiCurveKeys) { return false; }
    for (const auto& key : value->array)
    {
        std::array<float, 4> k{};
        bool fine = key.type == Json::Type::Array && key.array.size() == 4;
        for (size_t i = 0; fine && i < 4; ++i) { fine = NumberOf(&key.array[i], k[i]) && std::fabs(k[i]) <= 1.0e6f; }
        if (!fine || k[0] < 0.0f || k[0] > 1.0e4f || (!out.Keys.empty() && k[0] <= out.Keys.back()[0]))
        {
            out.Keys.clear();
            return false;
        }
        out.Keys.push_back(k);
    }
    return true;
}

// One external force ({"type": "basic" | "gravity" | "curve" | "wind" | "procedural_wind", ...}). False (why) when unusable.
inline bool ParseKawaiiExternalForce(const Json& item, const Config& cfg, KawaiiExternalForce& f, std::wstring& why)
{
    if (item.type != Json::Type::Object)
    {
        why = L"each must be an object";
        return false;
    }
    const std::wstring type = FoldedKey(StringOf(item.Find("type")));
    if (type == L"basic") { f.Type = KawaiiForceType::Basic; }
    else if (type == L"gravity") { f.Type = KawaiiForceType::Gravity; }
    else if (type == L"curve") { f.Type = KawaiiForceType::Curve; }
    else if (type == L"wind") { f.Type = KawaiiForceType::Wind; }
    else if (type == L"procedural_wind" || type == L"proceduralwind" || type == L"procedural wind") { f.Type = KawaiiForceType::ProceduralWind; }
    else
    {
        why = L"needs \"type\": \"basic\", \"gravity\", \"curve\", \"wind\" or \"procedural_wind\"";
        return false;
    }
    // (Gravity and Wind are in the world's space; KawaiiPhysics does not let them be set)
    if (f.Type == KawaiiForceType::Gravity || f.Type == KawaiiForceType::Wind) { f.Space = KawaiiForceSpace::World; }
    bool ok = true;
    KawaiiBool(item, "enabled", f.Enabled, ok);
    KawaiiBool(item, "is_enabled", f.Enabled, ok);
    bool names = true;
    KawaiiBones(item.Find("apply_bone_filter"), f.ApplyBoneFilter, names);
    KawaiiBones(item.Find("ignore_bone_filter"), f.IgnoreBoneFilter, names);
    if (!names) { ok = false; }
    if (const Json* space = item.Find("external_force_space"); space && f.Type != KawaiiForceType::Gravity && f.Type != KawaiiForceType::Wind)
    {
        const std::wstring name = FoldedKey(StringOf(space));
        if (name == L"world" || name == L"world_space") { f.Space = KawaiiForceSpace::World; }
        else if (name == L"component" || name == L"component_space") { f.Space = KawaiiForceSpace::Component; }
        else if (name == L"bone" || name == L"bone_space") { f.Space = KawaiiForceSpace::Bone; }
        else { ok = false; }
    }
    KawaiiInterval(item.Find("random_force_scale_range"), f.RandomForceScaleRange, -1.0e6f, 1.0e6f, ok);
    if (!KawaiiCurveOf(item.Find("force_rate_by_bone_length_rate"), f.ForceRateByBoneLengthRate)) { ok = false; }
    KawaiiTriple(item.Find("force_dir"), f.ForceDir, 1.0e7f, ok);
    KawaiiNumber(item, "interval", f.Interval, 0.0f, 1.0e5f, ok);
    KawaiiBool(item, "use_character_gravity_direction", f.UseCharacterGravityDirection, ok);
    KawaiiBool(item, "use_character_gravity_scale", f.UseCharacterGravityScale, ok);
    KawaiiBool(item, "use_override_gravity_direction", f.UseOverrideGravityDirection, ok);
    KawaiiTriple(item.Find("override_gravity_direction"), f.OverrideGravityDirection, 1.0e6f, ok);
    if (!KawaiiVectorCurveOf(item.Find("force_curve"), f.ForceCurve)) { ok = false; }
    if (const Json* how = item.Find("curve_evaluate_type"))
    {
        const std::wstring name = FoldedKey(StringOf(how));
        if (name == L"single") { f.CurveEvaluateType = KawaiiCurveEvaluate::Single; }
        else if (name == L"average") { f.CurveEvaluateType = KawaiiCurveEvaluate::Average; }
        else if (name == L"max") { f.CurveEvaluateType = KawaiiCurveEvaluate::Max; }
        else if (name == L"min") { f.CurveEvaluateType = KawaiiCurveEvaluate::Min; }
        else { ok = false; }
    }
    KawaiiInteger(item, "substep_count", f.SubstepCount, 1, 1000, ok);
    KawaiiNumber(item, "time_scale", f.TimeScale, 0.0f, 1.0e3f, ok);
    KawaiiNumber(item, "wind_direction_noise_angle", f.WindDirectionNoiseAngle, 0.0f, 180.0f, ok);
    if (const Json* source = item.Find("wind_source"))
    {
        const std::wstring name = FoldedKey(StringOf(source));
        if (name == L"local") { f.WindSource = KawaiiWindSource::Local; }
        else if (name == L"shared") { f.WindSource = KawaiiWindSource::Shared; }
        else if (name == L"auto") { f.WindSource = KawaiiWindSource::Auto; }
        else { ok = false; }
    }
    if (const Json* tag = item.Find("shared_wind_tag"))
    {
        const std::wstring text = StringOf(tag);
        if (IsTagName(text)) { f.SharedWindTag = text; }
        else { ok = false; }
    }
    // the preset first: the force's own settings over it
    if (const Json* preset = item.Find("wind_preset"))
    {
        f.WindPreset = StringOf(preset);
        if (const KawaiiWindPreset* p = FindKawaiiWindPreset(cfg, f.WindPreset)) { ApplyKawaiiWindPreset(*p, f); }
        else
        {
            why = L"wind_preset " + f.WindPreset + L" is not one (Breeze, Strong, Storm or the files' \"kawaii_wind_presets\")";
            return false;
        }
    }
    KawaiiTriple(item.Find("wind_direction"), f.WindDirection, 1.0e6f, ok);
    KawaiiNumber(item, "wind_direction_noise_period", f.WindDirectionNoisePeriod, 0.01f, 1.0e4f, ok);
    KawaiiNumber(item, "constant_force", f.ConstantForce, 0.0f, 1.0e6f, ok);
    KawaiiNumber(item, "sway_force", f.SwayForce, 0.0f, 1.0e6f, ok);
    KawaiiNumber(item, "sway_period", f.SwayPeriod, 0.01f, 1.0e4f, ok);
    KawaiiNumber(item, "sway_phase_offset", f.SwayPhaseOffset, -1.0e5f, 1.0e5f, ok);
    KawaiiNumber(item, "ripple_force", f.RippleForce, 0.0f, 1.0e6f, ok);
    KawaiiNumber(item, "ripple_period", f.RipplePeriod, 0.01f, 1.0e4f, ok);
    KawaiiNumber(item, "ripple_phase_offset", f.RipplePhaseOffset, -1.0e5f, 1.0e5f, ok);
    KawaiiNumber(item, "ripple_tip_phase_delay", f.RippleTipPhaseDelay, -1.0e5f, 1.0e5f, ok);
    KawaiiInterval(item.Find("strength_cycle_range"), f.StrengthCycleRange, 0.0f, 1.0e4f, ok);
    KawaiiNumber(item, "strength_cycle_period", f.StrengthCyclePeriod, 0.01f, 1.0e5f, ok);
    KawaiiNumber(item, "strength_cycle_phase_offset", f.StrengthCyclePhaseOffset, -1.0e5f, 1.0e5f, ok);
    KawaiiNumber(item, "random_force", f.RandomForce, 0.0f, 1.0e6f, ok);
    KawaiiNumber(item, "random_force_period", f.RandomForcePeriod, 0.01f, 1.0e4f, ok);
    KawaiiInteger(item, "seed", f.Seed, -2147483647, 2147483647, ok);
    if (!ok)
    {
        why = L"has a bad setting (bone filters: bone names; external_force_space world, component or bone; random_force_scale_range and "
              L"strength_cycle_range [min, max]; curves [[time, value], ...] (force_curve [[time, x, y, z], ...]); curve_evaluate_type single, "
              L"average, max or min; wind_source local, shared or auto; periods 0.01 or more; forces 0 or more); the bad ones keep their defaults";
        return true;   // (usable: the bad settings kept KawaiiPhysics' defaults)
    }
    return true;
}

// A list of external forces ("external_forces"). Notes for the bad ones.
inline void ParseKawaiiExternalForces(const Json* value, std::wstring_view origin, const std::wstring& at, Config& cfg, std::vector<KawaiiExternalForce>& out)
{
    if (!value) { return; }
    if (value->type != Json::Type::Array)
    {
        Note(cfg, origin, at + L" external_forces must be an array; ignored");
        return;
    }
    for (size_t k = 0; k < value->array.size(); ++k)
    {
        if (out.size() >= MaxKawaiiExternalForces)
        {
            Note(cfg, origin, at + L" external_forces: " + std::to_wstring(MaxKawaiiExternalForces) + L" at most; the rest ignored");
            break;
        }
        KawaiiExternalForce f;
        std::wstring why;
        const bool usable = ParseKawaiiExternalForce(value->array[k], cfg, f, why);
        if (!why.empty()) { Note(cfg, origin, at + L" external_forces[" + std::to_wstring(k) + L"] " + why + (usable ? L"" : L"; ignored")); }
        if (usable) { out.push_back(std::move(f)); }
    }
}

// A settings multiplier ({"damping": 0.5, "stiffness": ...}, each 0 or more).
inline void KawaiiSettingsScaleOf(const Json* value, KawaiiSettingsScale& out, bool& ok)
{
    if (!value) { return; }
    if (value->type != Json::Type::Object)
    {
        ok = false;
        return;
    }
    KawaiiNumber(*value, "damping", out.Damping, 0.0f, 1.0e3f, ok);
    KawaiiNumber(*value, "stiffness", out.Stiffness, 0.0f, 1.0e3f, ok);
    KawaiiNumber(*value, "world_damping_location", out.WorldDampingLocation, 0.0f, 1.0e3f, ok);
    KawaiiNumber(*value, "world_damping_rotation", out.WorldDampingRotation, 0.0f, 1.0e3f, ok);
    KawaiiNumber(*value, "radius", out.Radius, 0.0f, 1.0e3f, ok);
    KawaiiNumber(*value, "limit_angle", out.LimitAngle, 0.0f, 1.0e3f, ok);
}

// Pairs of names: [["a", "b"], ...]
inline bool KawaiiNamePairs(const Json* value, std::vector<std::pair<std::wstring, std::wstring>>& out, bool plain)
{
    if (!value) { return true; }
    if (value->type != Json::Type::Array) { return false; }
    bool fine = true;
    for (const auto& p : value->array)
    {
        if (p.type != Json::Type::Array || p.array.size() != 2)
        {
            fine = false;
            continue;
        }
        const std::wstring a = StringOf(&p.array[0]), b = StringOf(&p.array[1]);
        if (a.empty() || b.empty() || a.size() > 256 || b.size() > 256 || (plain && (!IsPlainName(a) || !IsPlainName(b))))
        {
            fine = false;
            continue;
        }
        out.emplace_back(a, b);
    }
    return fine;
}

// A node's (or a set's) collision shape lists: "spheres" ... "planes" (and their KawaiiPhysics names).
inline void ParseKawaiiLimitLists(const Json& item, std::wstring_view origin, const std::wstring& at, Config& cfg, std::vector<KawaiiLimit>& spheres,
                                  std::vector<KawaiiLimit>& capsules, std::vector<KawaiiLimit>& tapered, std::vector<KawaiiLimit>& boxes,
                                  std::vector<KawaiiLimit>& planes)
{
    const std::tuple<const char*, int, std::vector<KawaiiLimit>*> lists[] = {
        {"spheres", 0, &spheres},          {"spherical_limits", 0, &spheres},       {"capsules", 1, &capsules},
        {"capsule_limits", 1, &capsules},  {"tapered_capsules", 2, &tapered},       {"tapered_capsule_limits", 2, &tapered},
        {"boxes", 3, &boxes},              {"box_limits", 3, &boxes},               {"planes", 4, &planes},
        {"planar_limits", 4, &planes}};
    for (const auto& [key, kind, list] : lists)
    {
        const Json* value = item.Find(key);
        if (!value) { continue; }
        if (value->type != Json::Type::Array)
        {
            Note(cfg, origin, at + L" " + Widen(key) + L" must be an array; ignored");
            continue;
        }
        for (size_t k = 0; k < value->array.size(); ++k)
        {
            if (list->size() >= MaxKawaiiLimits)
            {
                Note(cfg, origin, at + L" " + Widen(key) + L": " + std::to_wstring(MaxKawaiiLimits) + L" at most; the rest ignored");
                break;
            }
            KawaiiLimit limit;
            std::wstring why;
            if (!KawaiiLimitOf(value->array[k], kind, limit, why))
            {
                Note(cfg, origin, at + L" " + Widen(key) + L"[" + std::to_wstring(k) + L"] " + why + L"; ignored");
                continue;
            }
            list->push_back(std::move(limit));
        }
    }
}

// Bone constraints ([{"bone1", "bone2", "compliance", "exclude_from_subdivision"}] or [[bone1, bone2]]).
inline void ParseKawaiiBoneConstraintList(const Json* constraints, std::wstring_view origin, const std::wstring& at, Config& cfg, std::vector<KawaiiBoneConstraint>& out)
{
    if (!constraints) { return; }
    bool fine = constraints->type == Json::Type::Array;
    for (size_t k = 0; fine && k < constraints->array.size(); ++k)
    {
        const Json& c = constraints->array[k];
        KawaiiBoneConstraint one;
        if (c.type == Json::Type::Array && c.array.size() == 2)
        {
            one.Bone1 = StringOf(&c.array[0]);
            one.Bone2 = StringOf(&c.array[1]);
        }
        else if (c.type == Json::Type::Object)
        {
            one.Bone1 = StringOf(c.Find("bone1"));
            one.Bone2 = StringOf(c.Find("bone2"));
            if (const Json* type = c.Find("compliance"))
            {
                one.OverrideCompliance = KawaiiComplianceOf(type, one.Compliance);
                if (!one.OverrideCompliance) { fine = false; }
            }
            KawaiiBool(c, "exclude_from_subdivision", one.ExcludeFromSubdivision, fine);
        }
        if (!IsPlainName(one.Bone1) || !IsPlainName(one.Bone2) || NameEquals(one.Bone1, one.Bone2) || out.size() >= MaxKawaiiBoneConstraints)
        {
            fine = false;
            continue;
        }
        out.push_back(std::move(one));
    }
    if (!fine)
    {
        Note(cfg, origin, at + L" bone_constraints must be [{\"bone1\", \"bone2\", \"compliance\", \"exclude_from_subdivision\"}] or [[bone1, bone2]] of two "
                              L"bones each, " + std::to_wstring(MaxKawaiiBoneConstraints) + L" at most; bad ones ignored");
    }
}

// A trigger of an entry's "animation_triggers".
inline bool ParseKawaiiTrigger(const Json& item, std::wstring_view origin, const std::wstring& at, Config& cfg, KawaiiTrigger& t, std::wstring& why)
{
    if (item.type != Json::Type::Object)
    {
        why = L"must be an object";
        return false;
    }
    const std::wstring type = FoldedKey(StringOf(item.Find("type")));
    if (type == L"add_external_force") { t.Kind = KawaiiTriggerKind::AddExternalForce; }
    else if (type == L"set_alpha") { t.Kind = KawaiiTriggerKind::SetAlpha; }
    else if (type == L"settings_multiplier") { t.Kind = KawaiiTriggerKind::SettingsMultiplier; }
    else if (type == L"trigger_gust") { t.Kind = KawaiiTriggerKind::TriggerGust; }
    else if (type == L"wind_preset") { t.Kind = KawaiiTriggerKind::WindPreset; }
    else
    {
        why = L"needs \"type\": \"add_external_force\", \"set_alpha\", \"settings_multiplier\", \"trigger_gust\" or \"wind_preset\"";
        return false;
    }
    bool ok = true;
    for (const Json* m : Items(item.Find("montage"), ok))
    {
        std::wstring name = StringOf(m);
        // (a path: its object's name)
        if (const size_t cut = name.find_last_of(L"./"); cut != std::wstring::npos && name.back() != L'*') { name = name.substr(cut + 1); }
        if (name.empty() || name.size() > 128) { ok = false; continue; }
        AddUniqueName(t.Montages, name);
    }
    for (const Json* m : Items(item.Find("montages"), ok))
    {
        const std::wstring name = StringOf(m);
        if (name.empty() || name.size() > 128) { ok = false; continue; }
        AddUniqueName(t.Montages, name);
    }
    if (t.Montages.empty())
    {
        why = L"needs \"montage\": the montage(s) it is for (names; \"Name*\" for every name starting so)";
        return false;
    }
    if (const Json* at2 = item.Find("at"))
    {
        t.Pulse = NumberOf(at2, t.At) && t.At >= 0.0f;
        if (!t.Pulse) { ok = false; }
    }
    KawaiiNumber(item, "start", t.Start, 0.0f, 1.0e5f, ok);
    KawaiiNumber(item, "end", t.End, -1.0f, 1.0e5f, ok);
    if (t.End >= 0.0f && t.End < t.Start) { ok = false; }
    // pulses: the kinds that are one (a gust, a preset) at "at" (or "start")
    if ((t.Kind == KawaiiTriggerKind::TriggerGust || t.Kind == KawaiiTriggerKind::WindPreset) && !t.Pulse)
    {
        t.Pulse = true;
        t.At = t.Start;
    }
    if (t.Kind == KawaiiTriggerKind::SetAlpha && t.Pulse)
    {
        why = L"set_alpha is a state (\"start\" - \"end\"), not a pulse (\"at\")";
        return false;
    }
    for (const Json* tag : Items(item.Find("filter_tags"), ok))
    {
        const std::wstring text = StringOf(tag);
        if (!IsTagName(text)) { ok = false; continue; }
        AddUniqueName(t.FilterTags, text);
    }
    KawaiiBool(item, "filter_exact_match", t.FilterExactMatch, ok);
    switch (t.Kind)
    {
    case KawaiiTriggerKind::AddExternalForce:
        ParseKawaiiExternalForces(item.Find("external_forces"), origin, at, cfg, t.Forces);
        ParseKawaiiExternalForces(item.Find("additional_external_forces"), origin, at, cfg, t.Forces);
        if (t.Forces.empty())
        {
            why = L"add_external_force needs \"external_forces\"";
            return false;
        }
        break;
    case KawaiiTriggerKind::SetAlpha:
    {
        const std::wstring source = FoldedKey(StringOf(item.Find("source")));
        if (source == L"curve") { t.AlphaFromCurve = true; }
        else if (source.empty() || source == L"constant") { t.AlphaFromCurve = false; }
        else { ok = false; }
        if (source.empty() && item.Find("curve_name")) { t.AlphaFromCurve = true; }
        KawaiiNumber(item, "constant_alpha", t.ConstantAlpha, 0.0f, 1.0f, ok);
        KawaiiNumber(item, "default_alpha_if_no_curve", t.DefaultAlpha, 0.0f, 1.0f, ok);
        break;
    }
    case KawaiiTriggerKind::SettingsMultiplier:
    {
        KawaiiSettingsScaleOf(item.Find("settings_scale"), t.Scale, ok);
        const std::wstring source = FoldedKey(StringOf(item.Find("weight_source")));
        if (source == L"curve") { t.WeightFromCurve = true; }
        else if (!source.empty() && source != L"envelope") { ok = false; }
        if (t.Pulse) { t.BlendOutTime = 0.5f; }   // (the pulse's default)
        KawaiiNumber(item, "duration", t.Duration, 0.0f, 1.0e4f, ok);
        KawaiiNumber(item, "blend_in_time", t.BlendInTime, 0.0f, 1.0e4f, ok);
        KawaiiNumber(item, "blend_out_time", t.BlendOutTime, 0.0f, 1.0e4f, ok);
        KawaiiNumber(item, "default_weight_if_no_curve", t.DefaultAlpha, 0.0f, 1.0f, ok);
        break;
    }
    case KawaiiTriggerKind::TriggerGust:
    {
        KawaiiNumber(item, "strength", t.Strength, -1.0e6f, 1.0e6f, ok);
        KawaiiNumber(item, "rise_time", t.RiseTime, 0.0f, 1.0e4f, ok);
        KawaiiNumber(item, "hold_time", t.HoldTime, 0.0f, 1.0e4f, ok);
        KawaiiNumber(item, "decay_time", t.DecayTime, 0.0f, 1.0e4f, ok);
        KawaiiTriple(item.Find("gust_direction"), t.GustDirection, 1.0e6f, ok);
        const std::wstring target = FoldedKey(StringOf(item.Find("gust_target")));
        if (target == L"shared_publisher") { t.SharedPublisher = true; }
        else if (!target.empty() && target != L"nodes") { ok = false; }
        break;
    }
    case KawaiiTriggerKind::WindPreset:
        t.Preset = StringOf(item.Find("preset"));
        if (!FindKawaiiWindPreset(cfg, t.Preset))
        {
            why = L"wind_preset needs \"preset\": Breeze, Strong, Storm or one of the files' \"kawaii_wind_presets\"";
            return false;
        }
        break;
    }
    if (t.Kind == KawaiiTriggerKind::SetAlpha || t.Kind == KawaiiTriggerKind::SettingsMultiplier) { t.CurveName = StringOf(item.Find("curve_name")); }
    if (const Json* tag = item.Find("shared_wind_tag"))
    {
        const std::wstring text = StringOf(tag);
        if (IsTagName(text)) { t.SharedWindTag = text; }
        else { ok = false; }
    }
    if (!ok) { why = L"has a bad setting (times 0 or more, end after start; filter_tags gameplay tags; alphas and weights 0 - 1); the bad ones keep their defaults"; }
    return true;
}

// (3.18.0) The files' sets: "kawaii_limits_sets", "kawaii_bone_constraints_sets", "kawaii_presets", "kawaii_wind_presets"
// ({"name": {...}, ...}). A later file's set of a name takes the place of an earlier one's.
inline void ParseKawaiiSets(const Json& root, std::wstring_view origin, Config& cfg)
{
    const auto objectOf = [&](const char* key) -> const Json* {
        const Json* v = root.Find(key);
        if (v && v->type != Json::Type::Object)
        {
            Note(cfg, origin, Widen(key) + L" must be an object ({\"name\": {...}}); ignored");
            return nullptr;
        }
        return v;
    };
    if (const Json* sets = objectOf("kawaii_wind_presets"))
    {
        for (const auto& [key, value] : sets->object)
        {
            KawaiiWindPreset p;
            p.Name = Widen(key);
            bool ok = value.type == Json::Type::Object && IsTagName(p.Name);
            if (ok)
            {
                KawaiiNumber(value, "constant_force", p.ConstantForce, 0.0f, 1.0e6f, ok);
                KawaiiNumber(value, "sway_force", p.SwayForce, 0.0f, 1.0e6f, ok);
                KawaiiNumber(value, "sway_period", p.SwayPeriod, 0.01f, 1.0e4f, ok);
                KawaiiNumber(value, "ripple_force", p.RippleForce, 0.0f, 1.0e6f, ok);
                KawaiiNumber(value, "ripple_period", p.RipplePeriod, 0.01f, 1.0e4f, ok);
                KawaiiNumber(value, "ripple_tip_phase_delay", p.RippleTipPhaseDelay, -1.0e5f, 1.0e5f, ok);
                KawaiiInterval(value.Find("strength_cycle_range"), p.StrengthCycleRange, 0.0f, 1.0e4f, ok);
                KawaiiNumber(value, "strength_cycle_period", p.StrengthCyclePeriod, 0.01f, 1.0e5f, ok);
                KawaiiNumber(value, "random_force", p.RandomForce, 0.0f, 1.0e6f, ok);
                KawaiiNumber(value, "random_force_period", p.RandomForcePeriod, 0.01f, 1.0e4f, ok);
                KawaiiNumber(value, "wind_direction_noise_angle", p.WindDirectionNoiseAngle, 0.0f, 180.0f, ok);
            }
            if (!ok)
            {
                Note(cfg, origin, L"kawaii_wind_presets " + p.Name + L": a name (letters, digits, dots) and procedural wind settings (forces 0 or more, periods 0.01 or more); bad ones keep the defaults");
                if (value.type != Json::Type::Object || !IsTagName(p.Name)) { continue; }
            }
            auto& list = cfg.KawaiiWindPresets;
            list.erase(std::remove_if(list.begin(), list.end(), [&](const KawaiiWindPreset& o) { return NameEquals(o.Name, p.Name); }), list.end());
            list.push_back(std::move(p));
        }
    }
    if (const Json* sets = objectOf("kawaii_presets"))
    {
        for (const auto& [key, value] : sets->object)
        {
            const std::wstring name = Widen(key);
            if (value.type != Json::Type::Object || !IsTagName(name))
            {
                Note(cfg, origin, L"kawaii_presets " + name + L" must be a node's settings ({...}) under a name; ignored");
                continue;
            }
            auto& list = cfg.KawaiiPresets;
            list.erase(std::remove_if(list.begin(), list.end(), [&](const auto& o) { return NameEquals(o.first, name); }), list.end());
            list.emplace_back(name, value);
        }
    }
    if (const Json* sets = objectOf("kawaii_limits_sets"))
    {
        for (const auto& [key, value] : sets->object)
        {
            KawaiiLimitsSet s;
            s.Name = Widen(key);
            s.Origin = std::wstring(origin);
            if (value.type != Json::Type::Object || !IsTagName(s.Name))
            {
                Note(cfg, origin, L"kawaii_limits_sets " + s.Name + L" must be shape lists ({\"spheres\": [...], ...}) under a name; ignored");
                continue;
            }
            ParseKawaiiLimitLists(value, origin, L"kawaii_limits_sets " + s.Name, cfg, s.Spheres, s.Capsules, s.TaperedCapsules, s.Boxes, s.Planes);
            auto& list = cfg.KawaiiLimitsSets;
            list.erase(std::remove_if(list.begin(), list.end(), [&](const KawaiiLimitsSet& o) { return NameEquals(o.Name, s.Name); }), list.end());
            list.push_back(std::move(s));
        }
    }
    if (const Json* sets = objectOf("kawaii_bone_constraints_sets"))
    {
        for (const auto& [key, value] : sets->object)
        {
            KawaiiConstraintsSet s;
            s.Name = Widen(key);
            s.Origin = std::wstring(origin);
            if (value.type != Json::Type::Object || !IsTagName(s.Name))
            {
                Note(cfg, origin, L"kawaii_bone_constraints_sets " + s.Name + L" must be {\"bone_constraints\": [...], \"regex_pattern_list\": [...]} under a name; ignored");
                continue;
            }
            ParseKawaiiBoneConstraintList(value.Find("bone_constraints"), origin, L"kawaii_bone_constraints_sets " + s.Name, cfg, s.Constraints);
            if (!KawaiiNamePairs(value.Find("regex_pattern_list"), s.Patterns, false))
            {
                Note(cfg, origin, L"kawaii_bone_constraints_sets " + s.Name + L" regex_pattern_list must be [[bone1 regex, bone2 regex], ...]; bad ones ignored");
            }
            auto& list = cfg.KawaiiConstraintsSets;
            list.erase(std::remove_if(list.begin(), list.end(), [&](const KawaiiConstraintsSet& o) { return NameEquals(o.Name, s.Name); }), list.end());
            list.push_back(std::move(s));
        }
    }
}

// (3.18.0) A node's JSON with its preset(s) under it: the preset's keys the node does not give (the bone assignment
// (root_bone, exclude_bones, additional_root_bones) only with "apply_bone_assignment": true, the tag only with
// "apply_tag": true: KawaiiPhysics' preset apply options). False: no preset named.
inline bool KawaiiWithPreset(const Json& item, const Config& cfg, Json& merged, std::wstring& missing)
{
    const Json* names = item.Find("preset");
    if (!names) { return false; }
    bool ok = true;
    std::vector<const Json*> presets;
    for (const Json* n : Items(names, ok))
    {
        const std::wstring name = StringOf(n);
        const auto it = std::find_if(cfg.KawaiiPresets.begin(), cfg.KawaiiPresets.end(), [&](const auto& p) { return NameEquals(p.first, name); });
        if (it == cfg.KawaiiPresets.end())
        {
            missing += (missing.empty() ? L"" : L", ") + name;
            continue;
        }
        presets.push_back(&it->second);
    }
    bool bones = false, tag = false;
    if (const Json* v = item.Find("apply_bone_assignment"); v && v->type == Json::Type::Bool) { bones = v->boolean; }
    if (const Json* v = item.Find("apply_tag"); v && v->type == Json::Type::Bool) { tag = v->boolean; }
    merged = item;
    merged.object.erase(std::remove_if(merged.object.begin(), merged.object.end(), [](const auto& kv) { return kv.first == "preset"; }), merged.object.end());
    // (later presets over earlier ones, the node's own over all)
    for (auto p = presets.rbegin(); p != presets.rend(); ++p)
    {
        for (const auto& [key, value] : (*p)->object)
        {
            if (key == "preset" || key == "name" || key == "enabled") { continue; }
            if (!bones && (key == "root_bone" || key == "exclude_bones" || key == "additional_root_bones")) { continue; }
            if (!tag && key == "kawaii_physics_tag") { continue; }
            if (merged.Find(key)) { continue; }
            merged.object.emplace_back(key, value);
        }
    }
    return true;
}

inline void ParseKawaiiNode(const Json& item, std::wstring_view origin, const std::wstring& where, Config& cfg, KawaiiNode& node, bool& usable);

// (3.18.0) A node's keys of 3.18.0 (wind, forces, alpha, tag, sets, shared and world collision).
inline void ParseKawaiiNode318(const Json& item, std::wstring_view origin, const std::wstring& at, Config& cfg, KawaiiNode& node)
{
    bool ok = true;
    KawaiiBool(item, "enable_wind", node.EnableWind, ok);
    KawaiiNumber(item, "wind_scale", node.WindScale, -1.0e4f, 1.0e4f, ok);
    KawaiiNumber(item, "wind_direction_noise_angle", node.WindDirectionNoiseAngle, 0.0f, 180.0f, ok);
    KawaiiNumber(item, "alpha", node.Alpha, 0.0f, 1.0f, ok);
    if (const Json* tag = item.Find("kawaii_physics_tag"))
    {
        const std::wstring text = StringOf(tag);
        if (IsTagName(text) || text.empty()) { node.Tag = text; }
        else { ok = false; }
    }
    if (!ok) { Note(cfg, origin, at + L" enable_wind (true or false), wind_scale, wind_direction_noise_angle (0 - 180), alpha (0 - 1), kawaii_physics_tag (a gameplay tag): bad ones keep their defaults"); }
    ParseKawaiiExternalForces(item.Find("external_forces"), origin, at, cfg, node.ExternalForces);
    // sets (by name; ResolveKawaiiSets puts them on)
    bool names = true;
    for (const Json* n : Items(item.Find("limits_data_asset"), names))
    {
        const std::wstring name = StringOf(n);
        if (IsTagName(name)) { AddUniqueName(node.LimitsSets, name); }
        else { names = false; }
    }
    for (const Json* n : Items(item.Find("bone_constraints_data_asset"), names))
    {
        const std::wstring name = StringOf(n);
        if (IsTagName(name)) { AddUniqueName(node.BoneConstraintsSets, name); }
        else { names = false; }
    }
    if (!names) { Note(cfg, origin, at + L" limits_data_asset and bone_constraints_data_asset must be set names (the files' \"kawaii_limits_sets\" / \"kawaii_bone_constraints_sets\"); bad ones ignored"); }
    if (const Json* pa = item.Find("physics_asset_for_limits"))
    {
        if (pa->type == Json::Type::Bool) { node.PhysicsAssetForLimits = pa->boolean; }
        else if (pa->type == Json::Type::String)
        {
            const std::wstring text = StringOf(pa);
            if (FoldedKey(text) == L"model" || FoldedKey(text) == L"own") { node.PhysicsAssetForLimits = true; }
            else
            {
                node.PhysicsAssetPath = NormalizeObjectPath(text);
                node.PhysicsAssetForLimits = !node.PhysicsAssetPath.empty();
                if (node.PhysicsAssetPath.empty()) { Note(cfg, origin, at + L" physics_asset_for_limits must be true (the model's own) or a physics asset's path; ignored"); }
            }
        }
        else { Note(cfg, origin, at + L" physics_asset_for_limits must be true (the model's own) or a physics asset's path; ignored"); }
    }
    if (const Json* mirror = item.Find("mirror_data_table_for_limits"))
    {
        bool fine = mirror->type == Json::Type::Object;
        if (fine)
        {
            node.MirrorLimits.Axis = KawaiiMirrorAxis::Y;
            const std::wstring axis = FoldedKey(StringOf(mirror->Find("axis")));
            if (axis == L"x") { node.MirrorLimits.Axis = KawaiiMirrorAxis::X; }
            else if (axis == L"z") { node.MirrorLimits.Axis = KawaiiMirrorAxis::Z; }
            else if (axis == L"none") { node.MirrorLimits.Axis = KawaiiMirrorAxis::None; }
            else if (!axis.empty() && axis != L"y") { fine = false; }
            fine = KawaiiNamePairs(mirror->Find("pairs"), node.MirrorLimits.Pairs, true) && fine;
            fine = KawaiiNamePairs(mirror->Find("prefixes"), node.MirrorLimits.Prefixes, false) && fine;
            fine = KawaiiNamePairs(mirror->Find("suffixes"), node.MirrorLimits.Suffixes, false) && fine;
            KawaiiBool(*mirror, "skip_mirrored_bone_with_existing_collision", node.MirrorLimits.SkipExisting, fine);
            if (node.MirrorLimits.Pairs.empty() && node.MirrorLimits.Prefixes.empty() && node.MirrorLimits.Suffixes.empty())
            {
                // (no table given: the game's own left / right names)
                node.MirrorLimits.Prefixes = {{L"L_", L"R_"}};
                node.MirrorLimits.Suffixes = {{L"_L", L"_R"}};
            }
        }
        if (!fine)
        {
            Note(cfg, origin, at + L" mirror_data_table_for_limits must be {\"axis\": \"x\" | \"y\" | \"z\", \"pairs\": [[left, right], ...], \"prefixes\": [[\"L_\", \"R_\"]], "
                                  L"\"suffixes\": [[\"_L\", \"_R\"]], \"skip_mirrored_bone_with_existing_collision\": true}; bad parts ignored");
        }
    }
    KawaiiBool(item, "skip_mirrored_bone_with_existing_collision", node.MirrorLimits.SkipExisting, ok);
    // shared collision
    bool shared = true;
    KawaiiBool(item, "shared_collision_source", node.SharedCollisionSource, shared);
    KawaiiBool(item, "use_shared_collision", node.UseSharedCollision, shared);
    if (const Json* tag = item.Find("shared_collision_group_tag"))
    {
        const std::wstring text = StringOf(tag);
        if (IsTagName(text)) { node.SharedCollisionGroupTag = text; }
        else { shared = false; }
    }
    if (!shared) { Note(cfg, origin, at + L" shared_collision_source / use_shared_collision (true or false), shared_collision_group_tag (a gameplay tag): bad ones ignored"); }
    // ground and level collision
    bool world = true;
    KawaiiWorldCollision& w = node.World;
    KawaiiBool(item, "allow_world_collision", w.AllowWorldCollision, world);
    KawaiiBool(item, "ignore_self_component", w.IgnoreSelfComponent, world);
    KawaiiInteger(item, "world_collision_max_sweeps_per_frame", w.MaxSweepsPerFrame, 0, 4096, world);
    KawaiiBool(item, "use_simple_world_collision", w.UseSimpleWorldCollision, world);
    KawaiiNumber(item, "simple_world_collision_gather_interval", w.GatherInterval, 0.0f, 60.0f, world);
    KawaiiBool(item, "override_simple_world_collision_gather_radius", w.OverrideGatherRadius, world);
    KawaiiNumber(item, "simple_world_collision_gather_radius", w.GatherRadius, 1.0f, 1.0e5f, world);
    KawaiiBool(item, "simple_world_collision_ground_collision", w.GroundCollision, world);
    KawaiiBool(item, "ground_collision", w.GroundOnly, world);
    if (!world)
    {
        Note(cfg, origin, at + L" allow_world_collision, ignore_self_component, use_simple_world_collision, simple_world_collision_ground_collision, ground_collision "
                              L"(true or false), world_collision_max_sweeps_per_frame (0 - 4096), simple_world_collision_gather_interval (s), "
                              L"simple_world_collision_gather_radius (cm): bad ones keep their defaults");
    }
}

inline void ParseKawaiiNode(const Json& item, std::wstring_view origin, const std::wstring& where, Config& cfg, KawaiiNode& node, bool& usable)
{
    usable = false;
    // (3.18.0) a preset under the node's own settings
    if (item.type == Json::Type::Object && item.Find("preset"))
    {
        Json merged;
        std::wstring missing;
        KawaiiWithPreset(item, cfg, merged, missing);
        if (!missing.empty()) { Note(cfg, origin, where + L" preset " + missing + L": no such preset in the files' \"kawaii_presets\" (read before this one); its own settings alone"); }
        ParseKawaiiNode(merged, origin, where, cfg, node, usable);
        return;
    }
    if (item.type != Json::Type::Object)
    {
        Note(cfg, origin, where + L" is not an object, skipped");
        return;
    }
    node.RootBone = StringOf(item.Find("root_bone"));
    if (!IsPlainName(node.RootBone))
    {
        Note(cfg, origin, where + L" needs its \"root_bone\" (a bone's name: the bones from it down swing), skipped");
        return;
    }
    node.Name = StringOf(item.Find("name"));
    if (node.Name.empty()) { node.Name = node.RootBone; }
    const std::wstring at = where + L" (" + node.Name + L")";
    bool namesOk = true;
    KawaiiBones(item.Find("exclude_bones"), node.ExcludeBones, namesOk);
    if (const Json* roots = item.Find("additional_root_bones"))
    {
        bool fine = roots->type == Json::Type::Array;
        for (size_t k = 0; fine && k < roots->array.size(); ++k)
        {
            const Json& r = roots->array[k];
            KawaiiRoot root;
            if (r.type == Json::Type::String) { root.Bone = StringOf(&r); }
            else if (r.type == Json::Type::Object)
            {
                root.Bone = StringOf(r.Find("root_bone"));
                if (root.Bone.empty()) { root.Bone = StringOf(r.Find("bone")); }
                if (const Json* own = r.Find("exclude_bones"))
                {
                    root.OverrideExcludeBones = true;
                    KawaiiBones(own, root.ExcludeBones, fine);
                }
            }
            if (!IsPlainName(root.Bone) || node.AdditionalRootBones.size() >= MaxKawaiiRoots)
            {
                fine = false;
                continue;
            }
            node.AdditionalRootBones.push_back(std::move(root));
        }
        if (!fine)
        {
            Note(cfg, origin, at + L" additional_root_bones must be bone names or {\"root_bone\", \"exclude_bones\"}, " + std::to_wstring(MaxKawaiiRoots) +
                                  L" at most; bad ones ignored");
        }
    }
    if (!namesOk) { Note(cfg, origin, at + L" exclude_bones must be bone names; bad ones ignored"); }
    // the physics settings (the node's PhysicsSettings), flat or as "physics_settings": {...}
    bool ok = true;
    const Json* physics = item.Find("physics_settings");
    const Json& settings = physics && physics->type == Json::Type::Object ? *physics : item;
    KawaiiNumber(settings, "damping", node.Damping, 0.0f, 1.0f, ok);
    KawaiiNumber(settings, "stiffness", node.Stiffness, 0.0f, 1.0f, ok);
    KawaiiNumber(settings, "world_damping_location", node.WorldDampingLocation, 0.0f, 1.0f, ok);
    KawaiiNumber(settings, "world_damping_rotation", node.WorldDampingRotation, 0.0f, 1.0f, ok);
    KawaiiNumber(settings, "radius", node.Radius, 0.0f, 1.0e4f, ok);
    KawaiiNumber(settings, "limit_angle", node.LimitAngle, 0.0f, 360.0f, ok);
    if (!ok)
    {
        Note(cfg, origin, at + L" physics settings: damping, stiffness, world_damping_location and world_damping_rotation must be 0 - 1, radius 0 or more, "
                              L"limit_angle 0 - 360; bad ones keep KawaiiPhysics' defaults");
    }
    const std::pair<const char*, KawaiiCurve*> curves[] = {{"damping_curve", &node.DampingCurve},
                                                            {"stiffness_curve", &node.StiffnessCurve},
                                                            {"world_damping_location_curve", &node.WorldDampingLocationCurve},
                                                            {"world_damping_rotation_curve", &node.WorldDampingRotationCurve},
                                                            {"radius_curve", &node.RadiusCurve},
                                                            {"limit_angle_curve", &node.LimitAngleCurve}};
    for (const auto& [key, curve] : curves)
    {
        if (!KawaiiCurveOf(item.Find(key), *curve))
        {
            Note(cfg, origin, at + L" " + Widen(key) + L" must be [[time, value], ...] with rising times from 0 to 1 (the bone's length from the root over the "
                                  L"longest), " + std::to_wstring(MaxKawaiiCurveKeys) + L" keys at most; ignored");
        }
    }
    bool more = true;
    KawaiiNumber(item, "dummy_bone_length", node.DummyBoneLength, 0.0f, 1.0e4f, more);
    KawaiiInteger(item, "bone_subdivision_count", node.BoneSubdivisionCount, 0, 10, more);
    KawaiiBool(item, "bone_subdivision_collision_only", node.BoneSubdivisionCollisionOnly, more);
    KawaiiBool(item, "bone_subdivision_densify_by_radius", node.BoneSubdivisionDensifyByRadius, more);
    KawaiiInteger(item, "bone_constraint_subdivision_count", node.BoneConstraintSubdivisionCount, 0, 10, more);
    KawaiiNumber(item, "bone_constraint_subdivision_feedback_scale", node.BoneConstraintSubdivisionFeedbackScale, 0.0f, 2.0f, more);
    KawaiiInteger(item, "target_framerate", node.TargetFramerate, 1, 1000, more);
    KawaiiBool(item, "use_fixed_substepping", node.UseFixedSubstepping, more);
    KawaiiInteger(item, "max_substeps", node.MaxSubsteps, 1, 64, more);
    KawaiiBool(item, "interpolate_limits_in_substeps", node.InterpolateLimitsInSubsteps, more);
    KawaiiBool(item, "keep_collision_side", node.KeepCollisionSide, more);
    KawaiiInteger(item, "warm_up_frames", node.WarmUpFrames, 0, 1000, more);
    KawaiiBool(item, "warm_up", node.NeedWarmUp, more);
    KawaiiBool(item, "need_warm_up", node.NeedWarmUp, more);
    KawaiiBool(item, "use_warm_up_when_reset_dynamics", node.UseWarmUpWhenResetDynamics, more);
    KawaiiNumber(item, "teleport_distance_threshold", node.TeleportDistanceThreshold, 0.0f, 1.0e7f, more);
    KawaiiNumber(item, "teleport_rotation_threshold", node.TeleportRotationThreshold, 0.0f, 360.0f, more);
    KawaiiTriple(item.Find("skel_comp_move_scale"), node.SkelCompMoveScale, 1.0e3f, more);
    KawaiiTriple(item.Find("gravity"), node.Gravity, 1.0e6f, more);
    KawaiiBool(item, "use_legacy_gravity", node.UseLegacyGravity, more);
    KawaiiBool(item, "use_default_gravity_z", node.UseDefaultGravityZ, more);
    KawaiiBool(item, "use_world_space_gravity", node.UseWorldSpaceGravity, more);
    KawaiiTriple(item.Find("simple_external_force"), node.SimpleExternalForce, 1.0e6f, more);
    KawaiiBool(item, "use_world_space_simple_external_force", node.UseWorldSpaceSimpleExternalForce, more);
    KawaiiBool(item, "skip_bonamik_bones", node.SkipBonamikBones, more);
    if (!more)
    {
        Note(cfg, origin, at + L" dummy_bone_length (0 or more), bone_subdivision_count and bone_constraint_subdivision_count (0 - 10), "
                              L"bone_constraint_subdivision_feedback_scale (0 - 2), target_framerate (1 - 1000), max_substeps (1 - 64), warm_up_frames (0 - 1000), "
                              L"teleport thresholds (cm, degrees), skel_comp_move_scale, gravity and simple_external_force ([x, y, z]) or a true / false switch: "
                              L"bad ones keep their defaults");
    }
    if (const Json* axis = item.Find("bone_forward_axis"))
    {
        const std::wstring name = FoldedKey(StringOf(axis));
        static const std::pair<const wchar_t*, KawaiiAxis> names[] = {
            {L"x+", KawaiiAxis::XPositive}, {L"x_positive", KawaiiAxis::XPositive}, {L"x", KawaiiAxis::XPositive}, {L"x-", KawaiiAxis::XNegative},
            {L"x_negative", KawaiiAxis::XNegative}, {L"y+", KawaiiAxis::YPositive}, {L"y_positive", KawaiiAxis::YPositive}, {L"y", KawaiiAxis::YPositive},
            {L"y-", KawaiiAxis::YNegative}, {L"y_negative", KawaiiAxis::YNegative}, {L"z+", KawaiiAxis::ZPositive}, {L"z_positive", KawaiiAxis::ZPositive},
            {L"z", KawaiiAxis::ZPositive}, {L"z-", KawaiiAxis::ZNegative}, {L"z_negative", KawaiiAxis::ZNegative}};
        bool found = false;
        for (const auto& [n, a] : names)
        {
            if (name == n)
            {
                node.BoneForwardAxis = a;
                found = true;
            }
        }
        if (!found) { Note(cfg, origin, at + L" bone_forward_axis must be \"X+\", \"X-\", \"Y+\", \"Y-\", \"Z+\" or \"Z-\"; using \"X+\""); }
    }
    if (const Json* planar = item.Find("planar_constraint"))
    {
        const std::wstring name = FoldedKey(StringOf(planar));
        if (name == L"none" || name.empty()) { node.PlanarConstraint = KawaiiPlanar::None; }
        else if (name == L"x") { node.PlanarConstraint = KawaiiPlanar::X; }
        else if (name == L"y") { node.PlanarConstraint = KawaiiPlanar::Y; }
        else if (name == L"z") { node.PlanarConstraint = KawaiiPlanar::Z; }
        else { Note(cfg, origin, at + L" planar_constraint must be \"none\", \"x\", \"y\" or \"z\"; using none"); }
    }
    if (const Json* space = item.Find("simulation_space"))
    {
        const std::wstring name = FoldedKey(StringOf(space));
        if (name == L"component" || name == L"component_space") { node.SimulationSpace = KawaiiSpace::Component; }
        else if (name == L"world" || name == L"world_space") { node.SimulationSpace = KawaiiSpace::World; }
        else if (name == L"base_bone" || name == L"base_bone_space") { node.SimulationSpace = KawaiiSpace::BaseBone; }
        else { Note(cfg, origin, at + L" simulation_space must be \"component\", \"world\" or \"base_bone\"; using component"); }
    }
    node.SimulationBaseBone = StringOf(item.Find("simulation_base_bone"));
    if (node.SimulationSpace == KawaiiSpace::BaseBone && !IsPlainName(node.SimulationBaseBone))
    {
        Note(cfg, origin, at + L" simulation_space \"base_bone\" needs \"simulation_base_bone\" (a bone's name); using component");
        node.SimulationSpace = KawaiiSpace::Component;
    }
    // collision shapes
    ParseKawaiiLimitLists(item, origin, at, cfg, node.Spheres, node.Capsules, node.TaperedCapsules, node.Boxes, node.Planes);
    // bone constraints (XPBD)
    if (const Json* compliance = item.Find("bone_constraint_global_compliance"); compliance && !KawaiiComplianceOf(compliance, node.BoneConstraintGlobalCompliance))
    {
        Note(cfg, origin, at + L" bone_constraint_global_compliance must be concrete, wood, leather, tendon, rubber, muscle or fat; using leather");
    }
    bool loops = true;
    KawaiiInteger(item, "bone_constraint_iteration_count_before_collision", node.BoneConstraintIterationsBeforeCollision, 0, 64, loops);
    KawaiiInteger(item, "bone_constraint_iteration_count_after_collision", node.BoneConstraintIterationsAfterCollision, 0, 64, loops);
    KawaiiBool(item, "auto_add_child_dummy_bone_constraint", node.AutoAddChildDummyBoneConstraint, loops);
    if (!loops)
    {
        Note(cfg, origin, at + L" bone_constraint_iteration_count_* must be 0 - 64, auto_add_child_dummy_bone_constraint true or false; bad ones ignored");
    }
    ParseKawaiiBoneConstraintList(item.Find("bone_constraints"), origin, at, cfg, node.BoneConstraints);
    ParseKawaiiPoseAnimation(item, origin, at, cfg, node);
    ParseKawaiiSyncBones(item, origin, at, cfg, node);
    ParseKawaiiNode318(item, origin, at, cfg, node);   // (3.18.0: what was "not run in the game yet" before runs now)
    usable = true;
}

// "kawaii": [{"models": [...], "requires_paks": [...], "nodes": [...]}, ...]
inline void ParseKawaii(const Json* value, std::wstring_view origin, Config& cfg)
{
    if (!value) { return; }
    if (value->type != Json::Type::Array)
    {
        Note(cfg, origin, L"\"kawaii\" must be an array; ignored");
        return;
    }
    for (size_t k = 0; k < value->array.size(); ++k)
    {
        const Json& entry = value->array[k];
        const std::wstring where = L"kawaii[" + std::to_wstring(k) + L"]";
        if (entry.type != Json::Type::Object)
        {
            Note(cfg, origin, where + L" is not an object, skipped");
            continue;
        }
        if (const Json* enabled = entry.Find("enabled"); enabled && enabled->type == Json::Type::Bool && !enabled->boolean) { continue; }
        KawaiiSet set;
        set.Origin = std::wstring(origin);
        bool modelsOk = true;
        for (const char* key : {"models", "model"})
        {
            for (const Json* item : Items(entry.Find(key), modelsOk))
            {
                std::wstring text = StringOf(item);
                const bool prefix = !text.empty() && text.back() == L'*';
                if (prefix) { text.pop_back(); }
                std::wstring path = prefix ? NormalizePathPrefix(text) : NormalizeObjectPath(text);
                if (path.empty())
                {
                    modelsOk = false;
                    continue;
                }
                if (prefix) { path += L'*'; }
                AddUnique(set.Models, path);
            }
        }
        if (!modelsOk) { Note(cfg, origin, where + L" models must be model paths (/Game/.../Model.Model; one ending in * for every model under it); bad ones ignored"); }
        if (set.Models.empty())
        {
            Note(cfg, origin, where + L" names no model (\"models\": the skeletal meshes it is for), skipped");
            continue;
        }
        if (!PakNames(entry, set.RequiresPaks)) { Note(cfg, origin, where + L" requires_paks: entries must be pak or mod names; bad entries ignored"); }
        bool switches = true;
        if (const Json* off = entry.Find("disable_bonamik"); off && off->type == Json::Type::Array)
        {
            for (const Json* item : Items(off, switches))
            {
                std::wstring text = StringOf(item);
                // (a BNM's name, or its object path: its name is what is compared)
                const size_t cut = text.find_last_of(L"./");
                if (cut != std::wstring::npos) { text = text.substr(cut + 1); }
                if (text.empty() || text.find_first_of(L" :\\") != std::wstring::npos)
                {
                    switches = false;
                    continue;
                }
                AddUniqueName(set.DisableBonamikAssets, text);
            }
            set.DisableBonamik = !set.DisableBonamikAssets.empty();
            if (!switches) { Note(cfg, origin, where + L" disable_bonamik: entries must be BNM names (\"PC0010_13_BNM\") or paths; bad ones ignored"); }
        }
        else
        {
            KawaiiBool(entry, "disable_bonamik", set.DisableBonamik, switches);
            if (!switches) { Note(cfg, origin, where + L" disable_bonamik must be true, false or a list of BNM names; ignored"); }
        }
        // (3.14.5) the KineDriver: true, false or KDI names (as "disable_bonamik")
        bool drivers = true;
        if (const Json* off = entry.Find("disable_kinedriver"); off && off->type == Json::Type::Array)
        {
            for (const Json* item : Items(off, drivers))
            {
                std::wstring text = StringOf(item);
                const size_t cut = text.find_last_of(L"./");
                if (cut != std::wstring::npos) { text = text.substr(cut + 1); }
                if (text.empty() || text.find_first_of(L" :\\") != std::wstring::npos)
                {
                    drivers = false;
                    continue;
                }
                AddUniqueName(set.DisableKineDriverAssets, text);
            }
            set.DisableKineDriver = !set.DisableKineDriverAssets.empty();
            if (!drivers) { Note(cfg, origin, where + L" disable_kinedriver: entries must be KDI names (\"PC0010_00_KDI\") or paths; bad ones ignored"); }
        }
        else
        {
            KawaiiBool(entry, "disable_kinedriver", set.DisableKineDriver, drivers);
            if (!drivers) { Note(cfg, origin, where + L" disable_kinedriver must be true, false or a list of KDI names; ignored"); }
        }
        // (3.18.0) the entry's animation triggers and shared winds
        if (const Json* triggers = entry.Find("animation_triggers"))
        {
            if (triggers->type != Json::Type::Array) { Note(cfg, origin, where + L" animation_triggers must be an array; ignored"); }
            else
            {
                for (size_t t = 0; t < triggers->array.size(); ++t)
                {
                    if (set.Triggers.size() >= MaxKawaiiTriggers)
                    {
                        Note(cfg, origin, where + L" animation_triggers: " + std::to_wstring(MaxKawaiiTriggers) + L" at most; the rest ignored");
                        break;
                    }
                    KawaiiTrigger trigger;
                    std::wstring why;
                    const std::wstring at = where + L".animation_triggers[" + std::to_wstring(t) + L"]";
                    const bool usable = ParseKawaiiTrigger(triggers->array[t], origin, at, cfg, trigger, why);
                    if (!why.empty()) { Note(cfg, origin, at + L" " + why + (usable ? L"" : L"; ignored")); }
                    if (usable) { set.Triggers.push_back(std::move(trigger)); }
                }
            }
        }
        if (const Json* winds = entry.Find("shared_winds"))
        {
            if (winds->type != Json::Type::Array) { Note(cfg, origin, where + L" shared_winds must be an array; ignored"); }
            else
            {
                for (size_t w = 0; w < winds->array.size() && set.SharedWinds.size() < 16; ++w)
                {
                    const Json& item = winds->array[w];
                    const std::wstring at = where + L".shared_winds[" + std::to_wstring(w) + L"]";
                    KawaiiSharedWind shared;
                    std::wstring why;
                    // (a procedural wind's settings: "type" not needed)
                    Json typed = item;
                    if (typed.type == Json::Type::Object && !typed.Find("type"))
                    {
                        Json type;
                        type.type = Json::Type::String;
                        type.string = "procedural_wind";
                        typed.object.emplace_back("type", type);
                    }
                    const bool usable = ParseKawaiiExternalForce(typed, cfg, shared.Wind, why) && shared.Wind.IsWind();
                    if (!why.empty() || !usable) { Note(cfg, origin, at + L" " + (why.empty() ? std::wstring(L"must be a procedural wind's settings") : why) + (usable ? L"" : L"; ignored")); }
                    if (!usable) { continue; }
                    shared.Tag = shared.Wind.SharedWindTag;
                    shared.Enabled = shared.Wind.Enabled;
                    set.SharedWinds.push_back(std::move(shared));
                }
            }
        }
        if (const Json* wind = entry.Find("world_wind"))   // (3.18.0)
        {
            KawaiiWorldWind& w = set.WorldWind;
            bool fine = wind->type == Json::Type::Object;
            if (fine)
            {
                w.Enabled = true;
                KawaiiBool(*wind, "enabled", w.Enabled, fine);
                KawaiiBool(*wind, "only_without_level_wind", w.OnlyWithoutLevelWind, fine);
                KawaiiTriple(wind->Find("direction"), w.Direction, 1.0e6f, fine);
                KawaiiNumber(*wind, "speed", w.Speed, 0.0f, 1.0e5f, fine);
                KawaiiNumber(*wind, "strength", w.Strength, 0.0f, 1.0e4f, fine);
                KawaiiNumber(*wind, "min_gust_amount", w.MinGustAmount, 0.0f, 1.0e4f, fine);
                KawaiiNumber(*wind, "max_gust_amount", w.MaxGustAmount, 0.0f, 1.0e4f, fine);
            }
            if (!fine)
            {
                Note(cfg, origin, where + L" world_wind must be {\"direction\": [x, y, z], \"speed\": cm/s, \"strength\", \"min_gust_amount\", \"max_gust_amount\", "
                                          L"\"only_without_level_wind\": true}; bad settings keep their defaults");
            }
        }
        const Json* nodes = entry.Find("nodes");
        if (!nodes || nodes->type != Json::Type::Array)
        {
            Note(cfg, origin, where + L" needs \"nodes\" (an array of KawaiiPhysics nodes), skipped");
            continue;
        }
        for (size_t n = 0; n < nodes->array.size(); ++n)
        {
            if (set.Nodes.size() >= MaxKawaiiNodes)
            {
                Note(cfg, origin, where + L": " + std::to_wstring(MaxKawaiiNodes) + L" nodes at most; the rest ignored");
                break;
            }
            KawaiiNode node;
            bool usable = false;
            ParseKawaiiNode(nodes->array[n], origin, where + L".nodes[" + std::to_wstring(n) + L"]", cfg, node, usable);
            if (usable) { set.Nodes.push_back(std::move(node)); }
        }
        if (set.Nodes.empty())
        {
            Note(cfg, origin, where + L" has no usable node, skipped");
            continue;
        }
        cfg.Kawaii.push_back(std::move(set));
    }
}

// (3.18.0) The sets a node names, put on it (its Data* lists: KawaiiPhysics' *LimitsData from a LimitsDataAsset, its
// BoneConstraintsData from a BoneConstraintsDataAsset). Once per node (a set named twice counts once).
inline void ResolveKawaiiNodeSets(Config& cfg, KawaiiNode& node, std::wstring_view origin)
{
    if (node.SetsResolved) { return; }
    node.SetsResolved = true;
    for (const auto& name : node.LimitsSets)
    {
        const auto it = std::find_if(cfg.KawaiiLimitsSets.begin(), cfg.KawaiiLimitsSets.end(), [&](const KawaiiLimitsSet& s) { return NameEquals(s.Name, name); });
        if (it == cfg.KawaiiLimitsSets.end())
        {
            Note(cfg, origin, L"kawaii node " + node.Name + L": limits_data_asset " + name + L" is in no file's \"kawaii_limits_sets\"; ignored");
            continue;
        }
        const auto append = [](std::vector<KawaiiLimit>& to, const std::vector<KawaiiLimit>& from) {
            for (const auto& l : from)
            {
                if (to.size() < MaxKawaiiLimits * 4) { to.push_back(l); }
            }
        };
        append(node.DataSpheres, it->Spheres);
        append(node.DataCapsules, it->Capsules);
        append(node.DataTaperedCapsules, it->TaperedCapsules);
        append(node.DataBoxes, it->Boxes);
        append(node.DataPlanes, it->Planes);
    }
    for (const auto& name : node.BoneConstraintsSets)
    {
        const auto it = std::find_if(cfg.KawaiiConstraintsSets.begin(), cfg.KawaiiConstraintsSets.end(), [&](const KawaiiConstraintsSet& s) { return NameEquals(s.Name, name); });
        if (it == cfg.KawaiiConstraintsSets.end())
        {
            Note(cfg, origin, L"kawaii node " + node.Name + L": bone_constraints_data_asset " + name + L" is in no file's \"kawaii_bone_constraints_sets\"; ignored");
            continue;
        }
        for (const auto& c : it->Constraints)
        {
            if (node.DataBoneConstraints.size() < MaxKawaiiBoneConstraints) { node.DataBoneConstraints.push_back(c); }
        }
        node.ConstraintPatterns.insert(node.ConstraintPatterns.end(), it->Patterns.begin(), it->Patterns.end());
    }
}

inline void ResolveKawaiiSets(Config& cfg)
{
    for (auto& set : cfg.Kawaii)
    {
        for (auto& node : set.Nodes) { ResolveKawaiiNodeSets(cfg, node, set.Origin); }
    }
}

// (3.16.0) Row names: a string or an array of strings, each a row name; false when one is not.
inline bool RowNames(const Json* value, std::vector<std::wstring>& out)
{
    bool ok = true;
    for (const Json* item : Items(value, ok))
    {
        const std::wstring name = StringOf(item);
        if (!IsRowName(name))
        {
            ok = false;
            continue;
        }
        AddUniqueName(out, name);
    }
    return ok;
}

// (3.16.0) "characters": [{"name", "slot", "player", "note", "charaspecs", "names_in", "rows", "values", "requires_paks"}]
inline void ParseCharacters(const Json* value, std::wstring_view origin, Config& cfg)
{
    if (!value) { return; }
    if (value->type != Json::Type::Array)
    {
        Note(cfg, origin, L"\"characters\" must be an array; ignored");
        return;
    }
    for (size_t k = 0; k < value->array.size(); ++k)
    {
        const Json& entry = value->array[k];
        const std::wstring where = L"characters[" + std::to_wstring(k) + L"]";
        if (entry.type != Json::Type::Object)
        {
            Note(cfg, origin, where + L" is not an object, skipped");
            continue;
        }
        if (const Json* enabled = entry.Find("enabled"); enabled && enabled->type == Json::Type::Bool && !enabled->boolean) { continue; }
        Character c;
        c.Origin = std::wstring(origin);
        c.Name = StringOf(entry.Find("name"));
        c.Slot = StringOf(entry.Find("slot"));
        c.Note = StringOf(entry.Find("note"));
        if (c.Name.empty() || c.Name.size() > 40 || c.Name == L"-")   // ("-" is a place's own in saved.json)
        {
            Note(cfg, origin, where + L" needs a \"name\" (what the CHARACTER page shows, 40 letters at most, not \"-\"), skipped");
            continue;
        }
        if (!IsRowName(c.Slot))
        {
            Note(cfg, origin, where + L" (" + c.Name + L") needs a \"slot\": the party member whose place it takes (\"Cloud\"), skipped");
            continue;
        }
        const std::wstring label = where + L" (" + c.Name + L")";
        // the place's CharaSpec rows -> its own
        const Json* specs = entry.Find("charaspecs");
        if (!specs || specs->type != Json::Type::Object || specs->object.empty())
        {
            Note(cfg, origin, label + L" needs \"charaspecs\": {\"the place's CharaSpec row\": \"its own row\", ...}, skipped");
            continue;
        }
        bool fine = true;
        for (const auto& [from, to] : specs->object)
        {
            const std::wstring f = Trim(Widen(from));
            const std::wstring t = to.type == Json::Type::String ? Trim(Widen(to.string)) : std::wstring{};
            if (!IsRowName(f) || !IsRowName(t) || NameEquals(f, t) ||
                std::any_of(c.Specs.begin(), c.Specs.end(), [&](const auto& p) { return NameEquals(p.first, f); }))
            {
                fine = false;
                continue;
            }
            c.Specs.emplace_back(f, t);
        }
        if (!fine) { Note(cfg, origin, label + L" charaspecs: each must be a CharaSpec row (once) and another row of its own; bad ones ignored"); }
        if (c.Specs.empty())
        {
            Note(cfg, origin, label + L" has no usable \"charaspecs\", skipped");
            continue;
        }
        // where the game names them
        if (const Json* in = entry.Find("names_in"))
        {
            bool ok = in->type == Json::Type::Array;
            for (size_t n = 0; ok && n < in->array.size(); ++n)
            {
                const Json& item = in->array[n];
                CharacterNamesIn names;
                names.Table = item.type == Json::Type::Object ? DataTablePath(StringOf(item.Find("table"))) : std::wstring{};
                const Json* fields = item.type == Json::Type::Object ? item.Find("fields") : nullptr;
                if (!fields) { fields = item.type == Json::Type::Object ? item.Find("field") : nullptr; }
                if (names.Table.empty() || !RowNames(fields, names.Fields) || names.Fields.empty())
                {
                    ok = false;
                    continue;
                }
                c.NamesIn.push_back(std::move(names));
            }
            if (!ok) { Note(cfg, origin, label + L" names_in: entries must be {\"table\": a table, \"fields\": [its fields]}; bad ones ignored"); }
        }
        else
        {
            for (const auto& names : DefaultCharacterNamesIn())
            {
                CharacterNamesIn copy = names;
                copy.Table = DataTablePath(names.Table);
                c.NamesIn.push_back(std::move(copy));
            }
            c.DefaultNamesIn = true;
        }
        // rows with another row's content
        {
            bool ok = true;
            for (const Json* item : Items(entry.Find("rows"), ok))
            {
                CharacterRowCopy row;
                if (item->type == Json::Type::Object)
                {
                    row.Table = DataTablePath(StringOf(item->Find("table")));
                    row.Row = StringOf(item->Find("row"));
                    row.From = StringOf(item->Find("from"));
                }
                if (row.Table.empty() || !IsRowName(row.Row) || !IsRowName(row.From) || NameEquals(row.Row, row.From) || !RowNames(item->Find("keep"), row.Keep))
                {
                    ok = false;
                    continue;
                }
                c.Rows.push_back(std::move(row));
            }
            if (!ok) { Note(cfg, origin, label + L" rows: entries must be {\"table\", \"row\", \"from\" (another row), \"keep\": [fields]}; bad ones ignored"); }
        }
        // fields set
        {
            bool ok = true;
            for (const Json* item : Items(entry.Find("values"), ok))
            {
                CharacterValue v;
                const Json* given = item->type == Json::Type::Object ? item->Find("value") : nullptr;
                if (item->type == Json::Type::Object)
                {
                    v.Table = DataTablePath(StringOf(item->Find("table")));
                    v.Field = StringOf(item->Find("field"));
                }
                bool usable = !v.Table.empty() && IsRowName(v.Field) && given && RowNames(item->Find("rows"), v.Rows) && !v.Rows.empty();
                if (usable)
                {
                    switch (given->type)
                    {
                    case Json::Type::String:
                        v.Is = CharacterValue::Kind::Text;
                        v.Text = Trim(Widen(given->string));
                        if (v.Text.size() > 1000) { usable = false; }   // (a name is 1023 letters at most)
                        break;
                    case Json::Type::Number:
                        v.Is = CharacterValue::Kind::Number;
                        v.Number = given->number;
                        break;
                    case Json::Type::Bool:
                        v.Is = CharacterValue::Kind::Number;
                        v.Number = given->boolean ? 1.0 : 0.0;
                        break;
                    case Json::Type::Array:
                        v.Is = CharacterValue::Kind::List;
                        for (const auto& name : given->array)
                        {
                            const std::wstring text = name.type == Json::Type::String ? Trim(Widen(name.string)) : std::wstring{};
                            if (!IsRowName(text)) { usable = false; }
                            v.List.push_back(text);
                        }
                        break;
                    default: usable = false; break;
                    }
                }
                if (!usable)
                {
                    ok = false;
                    continue;
                }
                c.Values.push_back(std::move(v));
            }
            if (!ok)
            {
                Note(cfg, origin, label + L" values: entries must be {\"table\", \"rows\": [rows], \"field\", \"value\": a name, a text, a number or a list of names}; bad ones ignored");
            }
        }
        // its BattlePlayerParameter row
        c.Player = StringOf(entry.Find("player"));
        if (c.Player.empty())
        {
            const std::wstring players = DataTablePath(L"BattlePlayerParameter");
            for (const auto& row : c.Rows)
            {
                if (PathEquals(row.Table, players))
                {
                    c.Player = row.Row;
                    break;
                }
            }
        }
        if (!c.Player.empty() && !IsRowName(c.Player))
        {
            Note(cfg, origin, label + L" player must be a BattlePlayerParameter row (\"pt_Cloud\"); ignored");
            c.Player.clear();
        }
        if (!PakNames(entry, c.RequiresPaks)) { Note(cfg, origin, label + L" requires_paks: entries must be pak or mod names; bad entries ignored"); }
        if (std::any_of(cfg.Characters.begin(), cfg.Characters.end(), [&](const Character& o) { return NameEquals(o.Slot, c.Slot) && NameEquals(o.Name, c.Name); }))
        {
            Note(cfg, origin, label + L": another character for " + c.Slot + L"'s place is called " + c.Name + L" already, skipped");
            continue;
        }
        cfg.Characters.push_back(std::move(c));
    }
}
} // namespace Detail

// (3.14.0) The "kawaii" entry for a model (its object path), the first one listing it: an exact path first, then the
// longest prefix ("...*"). Null: none.
inline const KawaiiSet* KawaiiFor(const Config& cfg, std::wstring_view modelPath)
{
    const KawaiiSet* best = nullptr;
    size_t bestLength = 0;
    for (const auto& set : cfg.Kawaii)
    {
        for (const auto& model : set.Models)
        {
            if (!model.empty() && model.back() == L'*')
            {
                const std::wstring_view prefix(model.data(), model.size() - 1);
                if (prefix.size() > bestLength && StartsWithFolded(modelPath, prefix))
                {
                    best = &set;
                    bestLength = prefix.size();
                }
            }
            else if (PathEquals(model, modelPath))
            {
                return &set;
            }
        }
    }
    return best;
}

// (3.14.0) A "kawaii" node as JSON text (an object: the keys AppendConfig reads, what differs from the defaults), the
// End editor's KawaiiPhysics node's export. `indent` starts each line after the first.
namespace Detail
{
inline std::wstring JsonText(std::wstring_view text)
{
    std::wstring out = L"\"";
    for (const wchar_t c : text)
    {
        switch (c)
        {
        case L'"': out += L"\\\""; break;
        case L'\\': out += L"\\\\"; break;
        case L'\n': out += L"\\n"; break;
        case L'\r': out += L"\\r"; break;
        case L'\t': out += L"\\t"; break;
        default:
            if (c < 0x20)
            {
                wchar_t buffer[8]{};
                swprintf(buffer, 8, L"\\u%04x", static_cast<unsigned>(c));
                out += buffer;
            }
            else { out += c; }
        }
    }
    return out + L"\"";
}

inline std::wstring JsonNumber(float value)
{
    if (!std::isfinite(value)) { return L"0"; }
    wchar_t buffer[48]{};
    swprintf(buffer, 48, L"%.6g", static_cast<double>(value));
    std::wstring text = buffer;
    return text == L"-0" ? std::wstring(L"0") : text;
}

inline std::wstring JsonTriple(const float (&v)[3])
{
    return L"[" + JsonNumber(v[0]) + L", " + JsonNumber(v[1]) + L", " + JsonNumber(v[2]) + L"]";
}

inline std::wstring JsonNames(const std::vector<std::wstring>& names)
{
    std::wstring out = L"[";
    for (size_t i = 0; i < names.size(); ++i) { out += (i ? L", " : L"") + JsonText(names[i]); }
    return out + L"]";
}

inline const wchar_t* ComplianceName(KawaiiCompliance c)
{
    switch (c)
    {
    case KawaiiCompliance::Concrete: return L"concrete";
    case KawaiiCompliance::Wood: return L"wood";
    case KawaiiCompliance::Leather: return L"leather";
    case KawaiiCompliance::Tendon: return L"tendon";
    case KawaiiCompliance::Rubber: return L"rubber";
    case KawaiiCompliance::Muscle: return L"muscle";
    case KawaiiCompliance::Fat: return L"fat";
    }
    return L"leather";
}
} // namespace Detail

// (3.18.0) An external force as JSON text (one line: the keys ParseKawaiiExternalForce reads, what differs from the defaults).
inline std::wstring KawaiiExternalForceJson(const KawaiiExternalForce& f)
{
    using namespace Detail;
    const KawaiiExternalForce d;
    static const wchar_t* const types[] = {L"basic", L"gravity", L"curve", L"wind", L"procedural_wind"};
    std::wstring out = L"{\"type\": " + JsonText(types[static_cast<int>(f.Type)]);
    const auto field = [&](const wchar_t* key, const std::wstring& value) { out += L", " + JsonText(key) + L": " + value; };
    const auto number = [&](const wchar_t* key, float value, float def) {
        if (value != def) { field(key, JsonNumber(value)); }
    };
    const auto curveText = [](const KawaiiCurve& c) {
        std::wstring keys = L"[";
        for (size_t k = 0; k < c.Keys.size(); ++k) { keys += (k ? L", [" : L"[") + JsonNumber(c.Keys[k].first) + L", " + JsonNumber(c.Keys[k].second) + L"]"; }
        return keys + L"]";
    };
    const auto pair = [](const float (&v)[2]) { return L"[" + JsonNumber(v[0]) + L", " + JsonNumber(v[1]) + L"]"; };
    if (!f.Enabled) { field(L"enabled", L"false"); }
    if (!f.ApplyBoneFilter.empty()) { field(L"apply_bone_filter", JsonNames(f.ApplyBoneFilter)); }
    if (!f.IgnoreBoneFilter.empty()) { field(L"ignore_bone_filter", JsonNames(f.IgnoreBoneFilter)); }
    if (f.Space != KawaiiForceSpace::World && f.Type != KawaiiForceType::Gravity && f.Type != KawaiiForceType::Wind)
    {
        field(L"external_force_space", f.Space == KawaiiForceSpace::Component ? L"\"component\"" : L"\"bone\"");
    }
    if (f.RandomForceScaleRange[0] != 1.0f || f.RandomForceScaleRange[1] != 1.0f) { field(L"random_force_scale_range", pair(f.RandomForceScaleRange)); }
    if (!f.ForceRateByBoneLengthRate.Empty()) { field(L"force_rate_by_bone_length_rate", curveText(f.ForceRateByBoneLengthRate)); }
    switch (f.Type)
    {
    case KawaiiForceType::Basic:
        field(L"force_dir", JsonTriple(f.ForceDir));
        number(L"interval", f.Interval, d.Interval);
        break;
    case KawaiiForceType::Gravity:
        if (f.UseCharacterGravityDirection) { field(L"use_character_gravity_direction", L"true"); }
        if (f.UseCharacterGravityScale) { field(L"use_character_gravity_scale", L"true"); }
        if (f.UseOverrideGravityDirection) { field(L"use_override_gravity_direction", L"true"); }
        if (f.UseOverrideGravityDirection || f.OverrideGravityDirection[0] != 0.0f || f.OverrideGravityDirection[1] != 0.0f || f.OverrideGravityDirection[2] != 0.0f)
        {
            field(L"override_gravity_direction", JsonTriple(f.OverrideGravityDirection));
        }
        break;
    case KawaiiForceType::Curve:
    {
        std::wstring keys = L"[";
        for (size_t k = 0; k < f.ForceCurve.Keys.size(); ++k)
        {
            const auto& q = f.ForceCurve.Keys[k];
            keys += (k ? L", [" : L"[") + JsonNumber(q[0]) + L", " + JsonNumber(q[1]) + L", " + JsonNumber(q[2]) + L", " + JsonNumber(q[3]) + L"]";
        }
        field(L"force_curve", keys + L"]");
        static const wchar_t* const how[] = {L"single", L"average", L"max", L"min"};
        if (f.CurveEvaluateType != d.CurveEvaluateType) { field(L"curve_evaluate_type", JsonText(how[static_cast<int>(f.CurveEvaluateType)])); }
        if (f.SubstepCount != d.SubstepCount) { field(L"substep_count", std::to_wstring(f.SubstepCount)); }
        number(L"time_scale", f.TimeScale, d.TimeScale);
        break;
    }
    case KawaiiForceType::Wind: number(L"wind_direction_noise_angle", f.WindDirectionNoiseAngle, d.WindDirectionNoiseAngle); break;
    case KawaiiForceType::ProceduralWind:
    {
        static const wchar_t* const sources[] = {L"local", L"shared", L"auto"};
        if (f.WindSource != d.WindSource) { field(L"wind_source", JsonText(sources[static_cast<int>(f.WindSource)])); }
        if (f.SharedWindTag != d.SharedWindTag) { field(L"shared_wind_tag", JsonText(f.SharedWindTag)); }
        if (f.WindDirection[0] != d.WindDirection[0] || f.WindDirection[1] != d.WindDirection[1] || f.WindDirection[2] != d.WindDirection[2])
        {
            field(L"wind_direction", JsonTriple(f.WindDirection));
        }
        number(L"wind_direction_noise_angle", f.WindDirectionNoiseAngle, d.WindDirectionNoiseAngle);
        number(L"wind_direction_noise_period", f.WindDirectionNoisePeriod, d.WindDirectionNoisePeriod);
        number(L"time_scale", f.TimeScale, d.TimeScale);
        number(L"constant_force", f.ConstantForce, d.ConstantForce);
        number(L"sway_force", f.SwayForce, d.SwayForce);
        number(L"sway_period", f.SwayPeriod, d.SwayPeriod);
        number(L"sway_phase_offset", f.SwayPhaseOffset, d.SwayPhaseOffset);
        number(L"ripple_force", f.RippleForce, d.RippleForce);
        number(L"ripple_period", f.RipplePeriod, d.RipplePeriod);
        number(L"ripple_phase_offset", f.RipplePhaseOffset, d.RipplePhaseOffset);
        number(L"ripple_tip_phase_delay", f.RippleTipPhaseDelay, d.RippleTipPhaseDelay);
        if (f.StrengthCycleRange[0] != 1.0f || f.StrengthCycleRange[1] != 1.0f) { field(L"strength_cycle_range", pair(f.StrengthCycleRange)); }
        number(L"strength_cycle_period", f.StrengthCyclePeriod, d.StrengthCyclePeriod);
        number(L"strength_cycle_phase_offset", f.StrengthCyclePhaseOffset, d.StrengthCyclePhaseOffset);
        number(L"random_force", f.RandomForce, d.RandomForce);
        number(L"random_force_period", f.RandomForcePeriod, d.RandomForcePeriod);
        if (f.Seed != d.Seed) { field(L"seed", std::to_wstring(f.Seed)); }
        break;
    }
    }
    return out + L"}";
}

// (3.18.0) An entry's animation trigger as JSON text (one line: the keys ParseKawaiiTrigger reads, what differs from the
// defaults; a pulse by its "at").
inline std::wstring KawaiiTriggerJson(const KawaiiTrigger& t)
{
    using namespace Detail;
    const KawaiiTrigger d;
    static const wchar_t* const kinds[] = {L"add_external_force", L"set_alpha", L"settings_multiplier", L"trigger_gust", L"wind_preset"};
    std::wstring out = L"{\"type\": " + JsonText(kinds[static_cast<int>(t.Kind)]);
    const auto field = [&](const wchar_t* key, const std::wstring& value) { out += L", " + JsonText(key) + L": " + value; };
    const auto number = [&](const wchar_t* key, float value, float def) {
        if (value != def) { field(key, JsonNumber(value)); }
    };
    field(L"montage", t.Montages.size() == 1 ? JsonText(t.Montages[0]) : JsonNames(t.Montages));
    if (t.Pulse) { field(L"at", JsonNumber(t.At)); }
    else
    {
        number(L"start", t.Start, d.Start);
        number(L"end", t.End, d.End);
    }
    if (!t.FilterTags.empty()) { field(L"filter_tags", JsonNames(t.FilterTags)); }
    if (t.FilterExactMatch) { field(L"filter_exact_match", L"true"); }
    switch (t.Kind)
    {
    case KawaiiTriggerKind::AddExternalForce:
    {
        std::wstring list = L"[";
        for (size_t i = 0; i < t.Forces.size(); ++i) { list += (i ? L", " : L"") + KawaiiExternalForceJson(t.Forces[i]); }
        field(L"external_forces", list + L"]");
        break;
    }
    case KawaiiTriggerKind::SetAlpha:
        if (t.AlphaFromCurve)
        {
            field(L"source", L"\"curve\"");
            if (!t.CurveName.empty()) { field(L"curve_name", JsonText(t.CurveName)); }
            number(L"default_alpha_if_no_curve", t.DefaultAlpha, d.DefaultAlpha);
        }
        else
        {
            field(L"source", L"\"constant\"");
            number(L"constant_alpha", t.ConstantAlpha, d.ConstantAlpha);
        }
        break;
    case KawaiiTriggerKind::SettingsMultiplier:
    {
        const KawaiiSettingsScale& s = t.Scale;
        std::wstring scale = L"{";
        const auto factor = [&](const wchar_t* key, float value) {
            if (value != 1.0f) { scale += (scale.size() > 1 ? L", " : L"") + JsonText(key) + L": " + JsonNumber(value); }
        };
        factor(L"damping", s.Damping);
        factor(L"stiffness", s.Stiffness);
        factor(L"world_damping_location", s.WorldDampingLocation);
        factor(L"world_damping_rotation", s.WorldDampingRotation);
        factor(L"radius", s.Radius);
        factor(L"limit_angle", s.LimitAngle);
        field(L"settings_scale", scale + L"}");
        if (t.WeightFromCurve)
        {
            field(L"weight_source", L"\"curve\"");
            if (!t.CurveName.empty()) { field(L"curve_name", JsonText(t.CurveName)); }
            number(L"default_weight_if_no_curve", t.DefaultAlpha, d.DefaultAlpha);
        }
        if (t.Pulse) { number(L"duration", t.Duration, d.Duration); }
        number(L"blend_in_time", t.BlendInTime, d.BlendInTime);
        number(L"blend_out_time", t.BlendOutTime, t.Pulse ? 0.5f : d.BlendOutTime);
        break;
    }
    case KawaiiTriggerKind::TriggerGust:
        field(L"strength", JsonNumber(t.Strength));
        number(L"rise_time", t.RiseTime, d.RiseTime);
        number(L"hold_time", t.HoldTime, d.HoldTime);
        number(L"decay_time", t.DecayTime, d.DecayTime);
        if (t.GustDirection[0] != 0.0f || t.GustDirection[1] != 0.0f || t.GustDirection[2] != 0.0f) { field(L"gust_direction", JsonTriple(t.GustDirection)); }
        if (t.SharedPublisher) { field(L"gust_target", L"\"shared_publisher\""); }
        break;
    case KawaiiTriggerKind::WindPreset: field(L"preset", JsonText(t.Preset)); break;
    }
    if (t.SharedWindTag != d.SharedWindTag) { field(L"shared_wind_tag", JsonText(t.SharedWindTag)); }
    return out + L"}";
}

// (3.18.0) An entry's shared wind as JSON text (its procedural wind's settings, its tag and switch).
inline std::wstring KawaiiSharedWindJson(const KawaiiSharedWind& w)
{
    KawaiiExternalForce f = w.Wind;
    f.Type = KawaiiForceType::ProceduralWind;
    f.SharedWindTag = w.Tag;
    f.Enabled = w.Enabled;
    return KawaiiExternalForceJson(f);
}

// (3.18.0) An entry's own wind source as JSON text (empty: none).
inline std::wstring KawaiiWorldWindJson(const KawaiiWorldWind& w)
{
    using namespace Detail;
    if (!w.Enabled) { return {}; }
    const KawaiiWorldWind d;
    std::wstring out = L"{\"direction\": " + JsonTriple(w.Direction) + L", \"speed\": " + JsonNumber(w.Speed);
    if (w.Strength != d.Strength) { out += L", \"strength\": " + JsonNumber(w.Strength); }
    if (w.MinGustAmount != d.MinGustAmount) { out += L", \"min_gust_amount\": " + JsonNumber(w.MinGustAmount); }
    if (w.MaxGustAmount != d.MaxGustAmount) { out += L", \"max_gust_amount\": " + JsonNumber(w.MaxGustAmount); }
    if (w.OnlyWithoutLevelWind != d.OnlyWithoutLevelWind) { out += L", \"only_without_level_wind\": false"; }
    return out + L"}";
}

inline std::wstring KawaiiNodeJson(const KawaiiNode& node, const std::wstring& indent = std::wstring{})
{
    using namespace Detail;
    const KawaiiNode d;   // (the defaults)
    const std::wstring in = indent + L"  ";
    std::vector<std::wstring> items;
    const auto add = [&](const wchar_t* key, const std::wstring& value) { items.push_back(in + JsonText(key) + L": " + value); };
    const auto number = [&](const wchar_t* key, float value, float def) {
        if (value != def) { add(key, JsonNumber(value)); }
    };
    const auto integer = [&](const wchar_t* key, int value, int def) {
        if (value != def) { add(key, std::to_wstring(value)); }
    };
    const auto boolean = [&](const wchar_t* key, bool value, bool def) {
        if (value != def) { add(key, value ? L"true" : L"false"); }
    };
    const auto triple = [&](const wchar_t* key, const float (&v)[3], const float (&def)[3]) {
        if (v[0] != def[0] || v[1] != def[1] || v[2] != def[2]) { add(key, JsonTriple(v)); }
    };
    if (!node.Name.empty() && node.Name != node.RootBone) { add(L"name", JsonText(node.Name)); }
    add(L"root_bone", JsonText(node.RootBone));
    if (!node.ExcludeBones.empty()) { add(L"exclude_bones", JsonNames(node.ExcludeBones)); }
    if (!node.AdditionalRootBones.empty())
    {
        std::wstring list = L"[";
        for (size_t i = 0; i < node.AdditionalRootBones.size(); ++i)
        {
            const KawaiiRoot& r = node.AdditionalRootBones[i];
            list += i ? L", " : L"";
            list += r.OverrideExcludeBones ? L"{\"root_bone\": " + JsonText(r.Bone) + L", \"exclude_bones\": " + JsonNames(r.ExcludeBones) + L"}" : JsonText(r.Bone);
        }
        add(L"additional_root_bones", list + L"]");
    }
    number(L"damping", node.Damping, d.Damping);
    number(L"stiffness", node.Stiffness, d.Stiffness);
    number(L"world_damping_location", node.WorldDampingLocation, d.WorldDampingLocation);
    number(L"world_damping_rotation", node.WorldDampingRotation, d.WorldDampingRotation);
    number(L"radius", node.Radius, d.Radius);
    number(L"limit_angle", node.LimitAngle, d.LimitAngle);
    const std::pair<const wchar_t*, const KawaiiCurve*> curves[] = {{L"damping_curve", &node.DampingCurve},
                                                                    {L"stiffness_curve", &node.StiffnessCurve},
                                                                    {L"world_damping_location_curve", &node.WorldDampingLocationCurve},
                                                                    {L"world_damping_rotation_curve", &node.WorldDampingRotationCurve},
                                                                    {L"radius_curve", &node.RadiusCurve},
                                                                    {L"limit_angle_curve", &node.LimitAngleCurve}};
    for (const auto& [key, curve] : curves)
    {
        if (curve->Keys.empty()) { continue; }
        std::wstring keys = L"[";
        for (size_t i = 0; i < curve->Keys.size(); ++i) { keys += (i ? L", [" : L"[") + JsonNumber(curve->Keys[i].first) + L", " + JsonNumber(curve->Keys[i].second) + L"]"; }
        add(key, keys + L"]");
    }
    number(L"dummy_bone_length", node.DummyBoneLength, d.DummyBoneLength);
    if (node.BoneForwardAxis != d.BoneForwardAxis)
    {
        static const wchar_t* const axes[] = {L"X+", L"X-", L"Y+", L"Y-", L"Z+", L"Z-"};
        add(L"bone_forward_axis", JsonText(axes[static_cast<int>(node.BoneForwardAxis)]));
    }
    integer(L"bone_subdivision_count", node.BoneSubdivisionCount, d.BoneSubdivisionCount);
    boolean(L"bone_subdivision_collision_only", node.BoneSubdivisionCollisionOnly, d.BoneSubdivisionCollisionOnly);
    boolean(L"bone_subdivision_densify_by_radius", node.BoneSubdivisionDensifyByRadius, d.BoneSubdivisionDensifyByRadius);
    if (node.PlanarConstraint != d.PlanarConstraint)
    {
        static const wchar_t* const planes[] = {L"none", L"x", L"y", L"z"};
        add(L"planar_constraint", JsonText(planes[static_cast<int>(node.PlanarConstraint)]));
    }
    if (node.SimulationSpace != d.SimulationSpace)
    {
        static const wchar_t* const spaces[] = {L"component", L"world", L"base_bone"};
        add(L"simulation_space", JsonText(spaces[static_cast<int>(node.SimulationSpace)]));
    }
    if (!node.SimulationBaseBone.empty()) { add(L"simulation_base_bone", JsonText(node.SimulationBaseBone)); }
    integer(L"target_framerate", node.TargetFramerate, d.TargetFramerate);
    boolean(L"use_fixed_substepping", node.UseFixedSubstepping, d.UseFixedSubstepping);
    integer(L"max_substeps", node.MaxSubsteps, d.MaxSubsteps);
    boolean(L"interpolate_limits_in_substeps", node.InterpolateLimitsInSubsteps, d.InterpolateLimitsInSubsteps);
    boolean(L"keep_collision_side", node.KeepCollisionSide, d.KeepCollisionSide);
    boolean(L"warm_up", node.NeedWarmUp, d.NeedWarmUp);
    integer(L"warm_up_frames", node.WarmUpFrames, d.WarmUpFrames);
    boolean(L"use_warm_up_when_reset_dynamics", node.UseWarmUpWhenResetDynamics, d.UseWarmUpWhenResetDynamics);
    number(L"teleport_distance_threshold", node.TeleportDistanceThreshold, d.TeleportDistanceThreshold);
    number(L"teleport_rotation_threshold", node.TeleportRotationThreshold, d.TeleportRotationThreshold);
    triple(L"skel_comp_move_scale", node.SkelCompMoveScale, d.SkelCompMoveScale);
    triple(L"gravity", node.Gravity, d.Gravity);
    boolean(L"use_legacy_gravity", node.UseLegacyGravity, d.UseLegacyGravity);
    boolean(L"use_default_gravity_z", node.UseDefaultGravityZ, d.UseDefaultGravityZ);
    boolean(L"use_world_space_gravity", node.UseWorldSpaceGravity, d.UseWorldSpaceGravity);
    triple(L"simple_external_force", node.SimpleExternalForce, d.SimpleExternalForce);
    boolean(L"use_world_space_simple_external_force", node.UseWorldSpaceSimpleExternalForce, d.UseWorldSpaceSimpleExternalForce);
    boolean(L"skip_bonamik_bones", node.SkipBonamikBones, d.SkipBonamikBones);
    // the shapes
    const std::tuple<const wchar_t*, int, const std::vector<KawaiiLimit>*> lists[] = {{L"spheres", 0, &node.Spheres},
                                                                                     {L"capsules", 1, &node.Capsules},
                                                                                     {L"tapered_capsules", 2, &node.TaperedCapsules},
                                                                                     {L"boxes", 3, &node.Boxes},
                                                                                     {L"planes", 4, &node.Planes}};
    const float zero[3]{0, 0, 0};
    for (const auto& [key, kind, list] : lists)
    {
        if (list->empty()) { continue; }
        std::wstring shapes = L"[";
        for (size_t i = 0; i < list->size(); ++i)
        {
            const KawaiiLimit& l = (*list)[i];
            std::wstring one = L"{";
            std::wstring sep;
            const auto field = [&](const wchar_t* name, const std::wstring& value) {
                one += sep + JsonText(name) + L": " + value;
                sep = L", ";
            };
            if (!l.Bone.empty()) { field(L"bone", JsonText(l.Bone)); }
            field(L"offset", JsonTriple(l.Offset));
            if (l.Rotation[0] != zero[0] || l.Rotation[1] != zero[1] || l.Rotation[2] != zero[2]) { field(L"rotation", JsonTriple(l.Rotation)); }
            switch (kind)
            {
            case 0:
                field(L"radius", JsonNumber(l.Radius));
                if (l.Inner) { field(L"limit_type", L"\"inner\""); }
                break;
            case 1:
                field(L"radius", JsonNumber(l.Radius));
                field(L"length", JsonNumber(l.Length));
                break;
            case 2:
                field(L"radius0", JsonNumber(l.Radius0));
                field(L"radius1", JsonNumber(l.Radius1));
                field(L"length", JsonNumber(l.Length));
                break;
            case 3: field(L"extent", JsonTriple(l.Extent)); break;
            default: break;
            }
            shapes += (i ? L",\n" + in + L"  " : L"\n" + in + L"  ") + one + L"}";
        }
        add(key, shapes + L"\n" + in + L"]");
    }
    // the bone constraints
    if (node.BoneConstraintGlobalCompliance != d.BoneConstraintGlobalCompliance) { add(L"bone_constraint_global_compliance", JsonText(ComplianceName(node.BoneConstraintGlobalCompliance))); }
    integer(L"bone_constraint_iteration_count_before_collision", node.BoneConstraintIterationsBeforeCollision, d.BoneConstraintIterationsBeforeCollision);
    integer(L"bone_constraint_iteration_count_after_collision", node.BoneConstraintIterationsAfterCollision, d.BoneConstraintIterationsAfterCollision);
    boolean(L"auto_add_child_dummy_bone_constraint", node.AutoAddChildDummyBoneConstraint, d.AutoAddChildDummyBoneConstraint);
    integer(L"bone_constraint_subdivision_count", node.BoneConstraintSubdivisionCount, d.BoneConstraintSubdivisionCount);
    number(L"bone_constraint_subdivision_feedback_scale", node.BoneConstraintSubdivisionFeedbackScale, d.BoneConstraintSubdivisionFeedbackScale);
    if (!node.BoneConstraints.empty())
    {
        std::wstring list = L"[";
        for (size_t i = 0; i < node.BoneConstraints.size(); ++i)
        {
            const KawaiiBoneConstraint& c = node.BoneConstraints[i];
            std::wstring one;
            if (!c.OverrideCompliance && !c.ExcludeFromSubdivision) { one = L"[" + JsonText(c.Bone1) + L", " + JsonText(c.Bone2) + L"]"; }
            else
            {
                one = L"{\"bone1\": " + JsonText(c.Bone1) + L", \"bone2\": " + JsonText(c.Bone2);
                if (c.OverrideCompliance) { one += L", \"compliance\": " + JsonText(ComplianceName(c.Compliance)); }
                if (c.ExcludeFromSubdivision) { one += L", \"exclude_from_subdivision\": true"; }
                one += L"}";
            }
            list += (i ? (i % 4 ? L", " : L",\n" + in + L"  ") : L"") + one;
        }
        add(L"bone_constraints", list + L"]");
    }
    // (3.17.0) the sync bones
    if (!node.SyncBones.empty())
    {
        const KawaiiSyncBone ds;
        const auto curveText = [](const KawaiiCurve& c) {
            std::wstring keys = L"[";
            for (size_t k = 0; k < c.Keys.size(); ++k) { keys += (k ? L", [" : L"[") + JsonNumber(c.Keys[k].first) + L", " + JsonNumber(c.Keys[k].second) + L"]"; }
            return keys + L"]";
        };
        static const wchar_t* const directions[] = {L"both", L"positive", L"negative", L"none"};
        static const wchar_t* const axisKeys[] = {L"apply_direction_x", L"apply_direction_y", L"apply_direction_z"};
        std::wstring list = L"[";
        for (size_t i = 0; i < node.SyncBones.size(); ++i)
        {
            const KawaiiSyncBone& s = node.SyncBones[i];
            std::wstring one = L"{\"bone\": " + JsonText(s.Bone) + L", \"target_roots\": [";
            for (size_t t = 0; t < s.Targets.size(); ++t)
            {
                const KawaiiSyncTarget& target = s.Targets[t];
                one += t ? L", " : L"";
                if (target.IncludeChildBones && target.ScaleCurve.Empty()) { one += JsonText(target.Bone); }
                else
                {
                    one += L"{\"bone\": " + JsonText(target.Bone);
                    if (!target.IncludeChildBones) { one += L", \"include_child_bones\": false"; }
                    if (!target.ScaleCurve.Empty()) { one += L", \"scale_curve_by_bone_length_rate\": " + curveText(target.ScaleCurve); }
                    one += L"}";
                }
            }
            one += L"]";
            if (s.GlobalScale[0] != ds.GlobalScale[0] || s.GlobalScale[1] != ds.GlobalScale[1] || s.GlobalScale[2] != ds.GlobalScale[2])
            {
                one += L", \"global_scale\": " + JsonTriple(s.GlobalScale);
            }
            if (!s.ScaleCurveByDeltaDistance.Empty()) { one += L", \"scale_curve_by_delta_distance\": " + curveText(s.ScaleCurveByDeltaDistance); }
            for (int a = 0; a < 3; ++a)
            {
                if (s.Direction[a] != KawaiiSyncDirection::Both) { one += L", " + JsonText(axisKeys[a]) + L": " + JsonText(directions[static_cast<int>(s.Direction[a])]); }
            }
            if (s.DistanceAttenuation) { one += L", \"enable_distance_attenuation\": true"; }
            if (s.AttenuationInnerRadius != ds.AttenuationInnerRadius) { one += L", \"attenuation_inner_radius\": " + JsonNumber(s.AttenuationInnerRadius); }
            if (s.AttenuationOuterRadius != ds.AttenuationOuterRadius) { one += L", \"attenuation_outer_radius\": " + JsonNumber(s.AttenuationOuterRadius); }
            if (s.MaxAttenuationRate != ds.MaxAttenuationRate) { one += L", \"max_attenuation_rate\": " + JsonNumber(s.MaxAttenuationRate); }
            list += (i ? L",\n" + in + L"  " : L"\n" + in + L"  ") + one + L"}";
        }
        add(L"sync_bones", list + L"\n" + in + L"]");
    }
    // (3.18.0) wind, external forces, blend, tag, sets, shared and world collision
    boolean(L"enable_wind", node.EnableWind, d.EnableWind);
    number(L"wind_scale", node.WindScale, d.WindScale);
    number(L"wind_direction_noise_angle", node.WindDirectionNoiseAngle, d.WindDirectionNoiseAngle);
    if (!node.ExternalForces.empty())
    {
        std::wstring list = L"[";
        for (size_t i = 0; i < node.ExternalForces.size(); ++i) { list += (i ? L",\n" + in + L"  " : L"\n" + in + L"  ") + KawaiiExternalForceJson(node.ExternalForces[i]); }
        add(L"external_forces", list + L"\n" + in + L"]");
    }
    number(L"alpha", node.Alpha, d.Alpha);
    if (!node.Tag.empty()) { add(L"kawaii_physics_tag", JsonText(node.Tag)); }
    if (!node.LimitsSets.empty()) { add(L"limits_data_asset", node.LimitsSets.size() == 1 ? JsonText(node.LimitsSets[0]) : JsonNames(node.LimitsSets)); }
    if (!node.BoneConstraintsSets.empty())
    {
        add(L"bone_constraints_data_asset", node.BoneConstraintsSets.size() == 1 ? JsonText(node.BoneConstraintsSets[0]) : JsonNames(node.BoneConstraintsSets));
    }
    if (node.PhysicsAssetForLimits) { add(L"physics_asset_for_limits", node.PhysicsAssetPath.empty() ? std::wstring(L"true") : JsonText(node.PhysicsAssetPath)); }
    if (node.MirrorLimits.Active())
    {
        const KawaiiMirror& m = node.MirrorLimits;
        static const wchar_t* const axes[] = {L"none", L"x", L"y", L"z"};
        const auto pairs = [](const std::vector<std::pair<std::wstring, std::wstring>>& list) {
            std::wstring text = L"[";
            for (size_t i = 0; i < list.size(); ++i) { text += (i ? L", [" : L"[") + JsonText(list[i].first) + L", " + JsonText(list[i].second) + L"]"; }
            return text + L"]";
        };
        std::wstring text = L"{\"axis\": " + JsonText(axes[static_cast<int>(m.Axis)]);
        if (!m.Pairs.empty()) { text += L", \"pairs\": " + pairs(m.Pairs); }
        if (!m.Prefixes.empty()) { text += L", \"prefixes\": " + pairs(m.Prefixes); }
        if (!m.Suffixes.empty()) { text += L", \"suffixes\": " + pairs(m.Suffixes); }
        if (!m.SkipExisting) { text += L", \"skip_mirrored_bone_with_existing_collision\": false"; }
        add(L"mirror_data_table_for_limits", text + L"}");
    }
    boolean(L"shared_collision_source", node.SharedCollisionSource, d.SharedCollisionSource);
    boolean(L"use_shared_collision", node.UseSharedCollision, d.UseSharedCollision);
    if (node.SharedCollisionGroupTag != d.SharedCollisionGroupTag) { add(L"shared_collision_group_tag", JsonText(node.SharedCollisionGroupTag)); }
    {
        const KawaiiWorldCollision& w = node.World;
        const KawaiiWorldCollision dw;
        boolean(L"allow_world_collision", w.AllowWorldCollision, dw.AllowWorldCollision);
        boolean(L"ignore_self_component", w.IgnoreSelfComponent, dw.IgnoreSelfComponent);
        integer(L"world_collision_max_sweeps_per_frame", w.MaxSweepsPerFrame, dw.MaxSweepsPerFrame);
        boolean(L"use_simple_world_collision", w.UseSimpleWorldCollision, dw.UseSimpleWorldCollision);
        number(L"simple_world_collision_gather_interval", w.GatherInterval, dw.GatherInterval);
        boolean(L"override_simple_world_collision_gather_radius", w.OverrideGatherRadius, dw.OverrideGatherRadius);
        number(L"simple_world_collision_gather_radius", w.GatherRadius, dw.GatherRadius);
        boolean(L"simple_world_collision_ground_collision", w.GroundCollision, dw.GroundCollision);
        boolean(L"ground_collision", w.GroundOnly, dw.GroundOnly);
    }
    // (3.15.0) the pose animation
    if (!node.PoseWaves.empty())
    {
        const KawaiiWave dw;
        std::wstring list = L"[";
        for (size_t i = 0; i < node.PoseWaves.size(); ++i)
        {
            const KawaiiWave& w = node.PoseWaves[i];
            std::wstring one = L"{\"axis\": " + JsonTriple(w.Axis) + L", \"degrees\": " + JsonNumber(w.Degrees) + L", \"seconds\": " + JsonNumber(w.Seconds);
            if (w.LocalAxis) { one += L", \"local_axis\": true"; }
            if (w.Phase != dw.Phase) { one += L", \"phase\": " + JsonNumber(w.Phase); }
            if (w.PhasePerBone != dw.PhasePerBone) { one += L", \"phase_per_bone\": " + JsonNumber(w.PhasePerBone); }
            if (w.PhasePerRoot != dw.PhasePerRoot) { one += L", \"phase_per_root\": " + JsonNumber(w.PhasePerRoot); }
            if (!w.RootPhases.empty())
            {
                std::wstring phases = L"[";
                for (size_t r = 0; r < w.RootPhases.size(); ++r) { phases += (r ? L", " : L"") + JsonNumber(w.RootPhases[r]); }
                one += L", \"root_phases\": " + phases + L"]";
            }
            if (!w.DegreesCurve.Keys.empty())
            {
                std::wstring keys = L"[";
                for (size_t k = 0; k < w.DegreesCurve.Keys.size(); ++k)
                {
                    keys += (k ? L", [" : L"[") + JsonNumber(w.DegreesCurve.Keys[k].first) + L", " + JsonNumber(w.DegreesCurve.Keys[k].second) + L"]";
                }
                one += L", \"degrees_curve\": " + keys + L"]";
            }
            list += (i ? L",\n" + in + L"  " : L"\n" + in + L"  ") + one + L"}";
        }
        add(L"pose_waves", list + L"\n" + in + L"]");
    }
    if (node.PoseAnimation.Tracks && !node.PoseAnimation.Tracks->empty())
    {
        const KawaiiPoseAnimation& a = node.PoseAnimation;
        std::wstring text = L"{\"fps\": " + JsonNumber(a.Fps) + L", \"speed\": " + JsonNumber(a.Speed) + L", \"weight\": " + JsonNumber(a.Weight) +
                            L", \"additive\": " + (a.Additive ? L"true" : L"false") + L", \"tracks\": {";
        for (size_t t = 0; t < a.Tracks->size(); ++t)
        {
            const KawaiiKeyTrack& track = (*a.Tracks)[t];
            text += (t ? L",\n" : L"\n") + in + L"  " + JsonText(track.Bone) + L": [";
            for (size_t f = 0; f < track.Keys.size(); ++f)
            {
                const auto& q = track.Keys[f];
                text += (f ? L", [" : L"[") + JsonNumber(q[0]) + L", " + JsonNumber(q[1]) + L", " + JsonNumber(q[2]) + L", " + JsonNumber(q[3]) + L"]";
            }
            text += L"]";
        }
        add(L"pose_animation", text + L"\n" + in + L"}}");
    }
    std::wstring out = L"{\n";
    for (size_t i = 0; i < items.size(); ++i) { out += items[i] + (i + 1 < items.size() ? L",\n" : L"\n"); }
    return out + indent + L"}";
}

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
    // "pairs" and, for readability, "families" (entries of the second list default to "method": "family"), plus the
    // "animation_sets" rows (3.1).
    const Json* pairs = root.Find("pairs");
    const Json* families = root.Find("families");
    const Json* sets = root.Find("animation_sets");
    if (const Json* cutscenes = root.Find("cutscene_proportions"))
    {
        if (cutscenes->type == Json::Type::Bool) { cfg.CutsceneProportions = cfg.CutsceneProportions && cutscenes->boolean; }
        else { Detail::Note(cfg, origin, L"cutscene_proportions must be true or false; ignored"); }
    }
    const Json* kawaii = root.Find("kawaii");   // (3.14.0)
    const Json* characters = root.Find("characters");   // (3.16.0)
    // (3.18.0) a file of KawaiiPhysics sets alone
    const bool kawaiiSets = root.Find("kawaii_limits_sets") || root.Find("kawaii_bone_constraints_sets") || root.Find("kawaii_presets") ||
                            root.Find("kawaii_wind_presets");
    if ((!pairs || pairs->type != Json::Type::Array) && (!families || families->type != Json::Type::Array) &&
        (!sets || sets->type != Json::Type::Array) && (!kawaii || kawaii->type != Json::Type::Array) &&
        (!characters || characters->type != Json::Type::Array) && !kawaiiSets)
    {
        Detail::Note(cfg, origin, L"missing \"pairs\", \"families\", \"animation_sets\", \"kawaii\" or \"characters\" array, file skipped");
        return false;
    }
    Detail::ParseKawaiiSets(root, origin, cfg);   // (3.18.0: before the file's own entries use them)
    Detail::ParseKawaii(kawaii, origin, cfg);
    Detail::ParseCharacters(characters, origin, cfg);
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
        pair.KeepProportions = Detail::ProportionsOf(entry, false);
        if (const Json* bones = entry.Find("proportion_bones"))   // (3.8.2)
        {
            bool fine = bones->type == Json::Type::Array;
            std::vector<std::wstring> names;
            for (size_t k = 0; fine && k < bones->array.size(); ++k)
            {
                const std::wstring name = Trim(Detail::StringOf(&bones->array[k]));
                fine = Detail::IsPlainName(name);
                if (fine) { names.push_back(name); }
            }
            if (!fine) { Detail::Note(cfg, origin, where + L" proportion_bones must be a list of bone names (\"R_Feather*\": every bone starting with R_Feather); ignored"); }
            else
            {
                pair.ProportionBones = std::move(names);
                if (!pair.KeepProportions && !pair.ProportionBones.empty())
                {
                    Detail::Note(cfg, origin, where + L" proportion_bones only work with \"proportions\": true; they wait for it");
                }
            }
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
                existing.KeepProportions = existing.KeepProportions || one.KeepProportions; // one skeleton: on for every pair of it
                for (const auto& b : one.ProportionBones) { Detail::AddUniqueName(existing.ProportionBones, b); }
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
    if (sets && sets->type == Json::Type::Array)
    {
        for (size_t k = 0; k < sets->array.size(); ++k)
        {
            Detail::ParseAnimSetRow(sets->array[k], origin, L"animation_sets[" + std::to_wstring(k) + L"]", cfg);
        }
    }
    else if (sets)
    {
        Detail::Note(cfg, origin, L"\"animation_sets\" must be an array; ignored");
    }
    return true; // rules between pairs are applied once every file is read (FinishConfig)
}

// Rows whose requires_paks are not all installed switch off; then the rows of one character become one row (sources
// in file order, the first move per name, the first field_actions). "override" rows go first.
template <class IsInstalled>
inline void FinishAnimSetRows(Config& cfg, IsInstalled&& isInstalled)
{
    std::stable_partition(cfg.AnimSets.begin(), cfg.AnimSets.end(), [](const AnimSetRow& row) { return row.Override; });
    std::vector<AnimSetRow> result;
    for (const auto& row : cfg.AnimSets)
    {
        std::wstring missing;
        for (const auto& name : row.RequiresPaks)
        {
            if (!isInstalled(name)) { missing += (missing.empty() ? L"" : L", ") + name; }
        }
        if (!missing.empty())
        {
            cfg.Messages.push_back(L"animation set row for " + Detail::Joined(row.Characters) + L" is off: it requires " + missing +
                                   L", which is not installed");
            continue;
        }
        for (const auto& character : row.Characters)
        {
            auto it = std::find_if(result.begin(), result.end(), [&](const AnimSetRow& r) { return PathEquals(r.Characters.front(), character); });
            if (it == result.end())
            {
                AnimSetRow one = row;
                one.Characters = {character};
                result.push_back(std::move(one));
                continue;
            }
            AnimSetRow& existing = *it;
            for (const auto* lists : {&row.Battle, &row.Field})
            {
                auto& target = lists == &row.Battle ? existing.Battle : existing.Field;
                for (const auto& source : *lists) { Detail::AddSource(target, source); }
            }
            if (existing.Skeleton.empty()) { existing.Skeleton = row.Skeleton; }
            else if (!row.Skeleton.empty() && !PathEquals(existing.Skeleton, row.Skeleton))
            {
                Detail::Note(cfg, row.Origin, L"skeleton " + row.Skeleton + L" for " + character + L" ignored: an earlier row names " + existing.Skeleton +
                                                  (row.Sockets.empty() ? std::wstring{} : L" (its sockets go to " + existing.Skeleton + L" too)"));
            }
            for (const auto& socket : row.Sockets)
            {
                if (std::none_of(existing.Sockets.begin(), existing.Sockets.end(), [&](const auto& s) { return NameEquals(s.first, socket.first); }))
                {
                    existing.Sockets.push_back(socket);
                    for (const auto& place : row.SocketPlacements)   // (3.8.1: its placement comes along)
                    {
                        if (NameEquals(place.first, socket.first)) { existing.SocketPlacements.push_back(place); }
                    }
                }
            }
            existing.KeepProportions = existing.KeepProportions || row.KeepProportions;
            for (const auto& name : row.Sets)
            {
                if (std::none_of(existing.Sets.begin(), existing.Sets.end(), [&](const std::wstring& n) { return NameEquals(n, name); }))
                {
                    existing.Sets.push_back(name);
                }
            }
            for (const auto& move : row.Moves)
            {
                const bool known = std::any_of(existing.Moves.begin(), existing.Moves.end(), [&](const AnimMove& m) {
                    return NameEquals(m.Set, move.Set) && NameEquals(m.Key, move.Key);
                });
                if (!known) { existing.Moves.push_back(move); }
            }
            if (existing.FieldActions.empty()) { existing.FieldActions = row.FieldActions; }
            else if (!row.FieldActions.empty() && !NameEquals(existing.FieldActions, row.FieldActions))
            {
                Detail::Note(cfg, row.Origin, L"field_actions " + row.FieldActions + L" for " + character + L" ignored: an earlier row asks for " +
                                                  existing.FieldActions);
            }
            // 3.6.16: the first row's cutscene socket wins
            // 3.8: the first row's anim_blueprints_from wins (with its skeleton)
            if (existing.AnimBlueprintsFrom.empty() && !row.AnimBlueprintsFrom.empty())
            {
                existing.AnimBlueprintsFrom = row.AnimBlueprintsFrom;
                if (existing.Skeleton.empty()) { existing.Skeleton = row.Skeleton; }
            }
            else if (!row.AnimBlueprintsFrom.empty() && !PathEquals(existing.AnimBlueprintsFrom, row.AnimBlueprintsFrom))
            {
                Detail::Note(cfg, row.Origin, L"anim_blueprints_from " + row.AnimBlueprintsFrom + L" for " + character + L" ignored: an earlier row asks for " +
                                                  existing.AnimBlueprintsFrom);
            }
            if (existing.CutsceneWeaponSocket.empty()) { existing.CutsceneWeaponSocket = row.CutsceneWeaponSocket; }
            else if (!row.CutsceneWeaponSocket.empty() && !NameEquals(existing.CutsceneWeaponSocket, row.CutsceneWeaponSocket))
            {
                Detail::Note(cfg, row.Origin, L"cutscene_weapon_socket " + row.CutsceneWeaponSocket + L" for " + character + L" ignored: an earlier row asks for " +
                                                  existing.CutsceneWeaponSocket);
            }
            for (const auto& path : row.Preload) { Detail::AddUnique(existing.Preload, path); }
            for (const auto& path : row.PackAssets) { Detail::AddUnique(existing.PackAssets, path); }
            // 3.3: the first row's player row wins; packs the earlier rows do not list are added. Any row can turn the
            // status recalculation off.
            if (!row.RefreshAbilities) { existing.RefreshAbilities = false; }
            if (row.Pages.Set && !existing.Pages.Set) { existing.Pages = row.Pages; }   // (3.9.3: the first row's pages)
            if (!row.Abilities.empty())
            {
                if (existing.Player.empty()) { existing.Player = row.Player; }
                if (!NameEquals(existing.Player, row.Player))
                {
                    Detail::Note(cfg, row.Origin, L"abilities for " + character + L" ignored: they are for player row " + row.Player + L", an earlier row uses " +
                                                      existing.Player);
                }
                else
                {
                    for (const auto& entry : row.Abilities)
                    {
                        if (std::none_of(existing.Abilities.begin(), existing.Abilities.end(),
                                         [&](const PackAbilities& a) { return NameEquals(a.Pack, entry.Pack); }))
                        {
                            existing.Abilities.push_back(entry);
                        }
                    }
                }
            }
            // 3.7: the first row's shooter is the character's (a row with only "shooter" in it gives it one).
            if (row.Shooting.On)
            {
                if (!existing.Shooting.On) { existing.Shooting = row.Shooting; }
                else { Detail::Note(cfg, row.Origin, L"shooter for " + character + L" ignored: an earlier row makes it a shooter"); }
            }
            // 3.9.0: the first row's voice is the character's.
            if (row.Speaks.Set)
            {
                if (!existing.Speaks.Set) { existing.Speaks = row.Speaks; }
                else { Detail::Note(cfg, row.Origin, L"voice for " + character + L" ignored: an earlier row gives it one"); }
            }
            if (!row.LooksFrom.empty())   // (3.9.1)
            {
                if (existing.LooksFrom.empty()) { existing.LooksFrom = row.LooksFrom; }
                else if (!PathEquals(existing.LooksFrom, row.LooksFrom)) { Detail::Note(cfg, row.Origin, L"looks_from for " + character + L" ignored: an earlier row gives it its looks"); }
            }
            // 3.6: the first row's forms are the character's.
            if (row.Forms.HasList())
            {
                if (!existing.Forms.HasList()) { existing.Forms = row.Forms; }
                else { Detail::Note(cfg, row.Origin, L"forms for " + character + L" ignored: an earlier row gives it forms"); }
            }
            if (existing.Origin.find(row.Origin) == std::wstring::npos) { existing.Origin += L", " + row.Origin; }
            Detail::Note(cfg, row.Origin, L"animation set row for " + character + L" joined with an earlier row for the same character");
        }
    }
    cfg.AnimSets = std::move(result);
    // 3.7.7: a form's own shooter, made now: the character's (its joined row's: the shooter and the forms may come from
    // different rows) with the form's settings over it. What the settings get wrong is said once (each of the characters
    // a row lists has the same forms).
    std::vector<const Json*> said;
    for (auto& row : cfg.AnimSets)
    {
        for (auto& form : row.Forms.List)
        {
            if (!form.ShooterJson) { continue; }
            auto set = std::make_shared<Shooter::Settings>();
            const bool first = std::find(said.begin(), said.end(), form.ShooterJson.get()) == said.end();
            if (first)
            {
                said.push_back(form.ShooterJson.get());
                Detail::ParseShooter(form.ShooterJson.get(), row.Origin, L"form " + form.Name, cfg, *set, &row.Shooting);
            }
            else
            {
                Config quiet;
                Detail::ParseShooter(form.ShooterJson.get(), row.Origin, L"form " + form.Name, quiet, *set, &row.Shooting);
            }
            form.ShooterSet = std::move(set);
        }
    }
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
        bool KeepProportions = false;         // any entry asking for it: the hub's settings serve every member
        std::vector<std::wstring> ProportionBones; // (3.8.2) every entry's
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
            f.KeepProportions = f.KeepProportions || p.KeepProportions;
            for (const auto& b : p.ProportionBones) { AddUniqueName(f.ProportionBones, b); }
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
        f.KeepProportions = f.KeepProportions || m.KeepProportions;
        for (const auto& b : m.ProportionBones) { AddUniqueName(f.ProportionBones, b); }
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
            hub.KeepProportions = f.KeepProportions;
            hub.ProportionBones = f.ProportionBones;
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
                mesh.KeepProportions = f.KeepProportions;
                mesh.ProportionBones = f.ProportionBones;
                mesh.FamilyHub = f.Hub;
                mesh.Origin = origin;
                result.push_back(std::move(mesh));
            }
            Note(cfg, origin, L"family of " + f.Hub + L" (hub: " + f.HubWhy + L"): " + Joined(f.Members) +
                                  L" and " + f.Hub + L" play each other's animations. The animations of the others are adopted onto " + f.Hub +
                                  L" and their meshes are rebound to it" +
                                  (f.KeepProportions ? L"; every character keeps its own proportions (\"proportions\")" : L""));
        }
    }
    cfg.Pairs = std::move(result);
}
} // namespace Detail

// Settles the pairs once every file is read, in this order (each step only sees the pairs the steps before kept):
//  0. animation set rows: rows whose requires_paks are missing switch off, then one row per character (FinishAnimSetRows);
//  1. pairs whose requires_paks are not all installed switch off (`isInstalled(name)` answers for one name);
//  2. families are formed (Detail::BuildFamilies): "family" entries, and "animations" pairs that would otherwise
//     fight over the same animations or chain. Each becomes one "animations" pair onto the hub plus a "mesh" pair per
//     member. Other "animations" pairs keep moving animations onto their receiving skeleton (KH3 mode);
//  3. "mesh" pairs follow adopted animations (FollowAdoption), then mesh chains are dropped.
// Every change is explained in cfg.Messages.
template <class IsInstalled>
inline void FinishConfig(Config& cfg, IsInstalled&& isInstalled)
{
    if (!cfg.AnimSets.empty()) { FinishAnimSetRows(cfg, isInstalled); }
    // (3.14.0) "kawaii" entries whose paks are not all installed switch off
    for (auto it = cfg.Kawaii.begin(); it != cfg.Kawaii.end();)
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
        cfg.Messages.push_back(it->Origin + L": kawaii for " + Detail::Joined(it->Models) + L" is off: it requires " + missing + L", which is not installed");
        it = cfg.Kawaii.erase(it);
    }
    Detail::ResolveKawaiiSets(cfg);   // (3.18.0) the sets the nodes name
    // (3.16.0) "characters" whose paks are not all installed are left out
    for (auto it = cfg.Characters.begin(); it != cfg.Characters.end();)
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
        cfg.Messages.push_back(it->Origin + L": the character " + it->Name + L" (for " + it->Slot + L"'s place) is off: it requires " + missing + L", which is not installed");
        it = cfg.Characters.erase(it);
    }
    if (std::any_of(cfg.Pairs.begin(), cfg.Pairs.end(), [](const Pair& p) { return !p.RequiresPaks.empty(); }))
    {
        for (auto& note : DropPairsMissingPaks(cfg, isInstalled)) { cfg.Messages.push_back(std::move(note)); }
    }
    // A row's "proportions" switches them on for every pair and family its character's skeleton takes part in.
    for (const auto& row : cfg.AnimSets)
    {
        if (!row.KeepProportions || row.Skeleton.empty()) { continue; }
        bool used = false;
        for (auto& p : cfg.Pairs)
        {
            if (PathEquals(p.Receiving, row.Skeleton) || Detail::Lists(p.Animation, row.Skeleton) || (!p.Hub.empty() && PathEquals(p.Hub, row.Skeleton)))
            {
                p.KeepProportions = true;
                used = true;
            }
        }
        if (!used)
        {
            Detail::Note(cfg, row.Origin, L"proportions for " + row.Skeleton + L": no pair or family uses that skeleton, so there is nothing to keep");
        }
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
// 3.10.0 skins. A skin is a folder ue4ss\Mods\RebirthSkelCompat\skins\<folder>\ that the editor's Build Skins makes
// (editor 1.15): skin.json, and the skin's packages in the game's own format under Content\ (a model on its own
// skeleton). Every skin folder's packages reach the game through one container the editor writes from all of them,
// ~mods\CreateACharacterSkins_P (SkinsContainer): skins are off while it is not installed. skin.json names the CharaSpec
// rows whose characters wear the skin ("characters"), the skeleton family its skeleton joins ("family": the hub, e.g.
// Sephiroth's PC0010_00_Skeleton, so the model plays every animation of the family) and what comes with it: "voice" (as
// a row's: "own" for the animations' own banks, a bank, or {"bank", "replaces"}; empty: the row's), "weapon" (a weapon
// blueprint) and "anim_blueprint" (empty: the character's own, the model going on the game's way as a form's "as_look").
// ---------------------------------------------------------------------------------------
inline constexpr wchar_t SkinsContainer[] = L"CreateACharacterSkins_P";

// "/Game/DataAsset/Game/CharaSpec/CharaSpec_PC0000_00_Cloud_Standard.CharaSpec_..." -> "PC0000_00_Cloud_Standard".
inline std::wstring RowNameOfPack(std::wstring_view pack)
{
    std::wstring name = ObjectNameOfPath(pack);
    if (StartsWithFolded(name, L"CharaSpec_")) { name.erase(0, 10); }
    return name;
}

// Reads one skin.json (before FinishConfig): the skin goes into cfg.Skins, and its skeleton's family entry (hub
// "family", needing SkinsContainer) into cfg.Pairs. False when the file is not a usable skin.
inline bool AppendSkin(std::string_view text, std::wstring_view folder, Config& cfg)
{
    const std::wstring origin = L"skins\\" + std::wstring(folder) + L"\\skin.json";
    Json root;
    std::string error;
    if (!ParseJson(text, root, error) || root.type != Json::Type::Object)
    {
        Detail::Note(cfg, origin, L"is not a skin (" + (error.empty() ? std::wstring(L"not a JSON object") : Widen(error)) + L"); skipped");
        return false;
    }
    if (!StartsWithFolded(Detail::StringOf(root.Find("schema")), L"CreateACharacterSkin/"))
    {
        Detail::Note(cfg, origin, L"has no \"schema\": \"CreateACharacterSkin/1\" (not a skin the editor made); skipped");
        return false;
    }
    Skin skin;
    skin.Folder = std::wstring(folder);
    skin.Origin = origin;
    skin.Name = Detail::StringOf(root.Find("name"));
    if (skin.Name.empty()) { skin.Name = skin.Folder; }
    if (const Json* on = root.Find("enabled"); on && on->type == Json::Type::Bool) { skin.Enabled = on->boolean; }
    if (const Json* worn = root.Find("worn"); worn && worn->type == Json::Type::Bool) { skin.Worn = worn->boolean; }
    bool ok = true;
    for (const Json* item : Detail::Items(root.Find("characters"), ok))
    {
        const std::wstring pack = CharacterPackPath(Detail::StringOf(item));
        if (pack.empty()) { ok = false; continue; }
        Detail::AddUnique(skin.Characters, pack);
    }
    if (!ok) { Detail::Note(cfg, origin, L"\"characters\" has entries that are not CharaSpec rows (PC0000_00_Cloud_Standard); they are left out"); }
    skin.Model = NormalizeObjectPath(Detail::StringOf(root.Find("model")));
    skin.Skeleton = NormalizeObjectPath(Detail::StringOf(root.Find("skeleton")));
    skin.Family = NormalizeObjectPath(Detail::StringOf(root.Find("family")));
    if (const Json* keep = root.Find("proportions"); keep && keep->type == Json::Type::Bool) { skin.KeepProportions = keep->boolean; }
    bool bonesOk = true;
    for (const Json* item : Detail::Items(root.Find("proportion_bones"), bonesOk))
    {
        if (const std::wstring bone = Detail::StringOf(item); !bone.empty()) { Detail::AddUniqueName(skin.ProportionBones, bone); }
    }
    // "voice": "" (or none) is the row's; anything else as a row's "voice"
    if (const Json* voice = root.Find("voice"); voice && !(voice->type == Json::Type::String && Trim(Widen(voice->string)).empty()) && voice->type != Json::Type::Null)
    {
        if (!Detail::ParseVoice(voice, skin.Speaks))
        {
            Detail::Note(cfg, origin, L"\"voice\" is not \"own\", a voice bank or {\"bank\", \"replaces\"}; the row's voice is kept");
            skin.Speaks = Voice{};
        }
    }
    for (auto [key, out] : {std::pair<const char*, std::wstring*>{"weapon", &skin.Weapon}, {"anim_blueprint", &skin.AnimClass}})
    {
        std::wstring path = NormalizeObjectPath(Detail::StringOf(root.Find(key)));
        if (path.empty())
        {
            if (!Detail::StringOf(root.Find(key)).empty()) { Detail::Note(cfg, origin, L"\"" + Widen(key) + L"\" is not an object path; left out"); }
            continue;
        }
        if (path.size() < 2 || path.compare(path.size() - 2, 2, L"_C") != 0) { path += L"_C"; }   // (a blueprint's class)
        *out = std::move(path);
    }
    if (const std::wstring socket = Detail::StringOf(root.Find("weapon_field_socket")); !socket.empty())   // (3.15.1)
    {
        if (Detail::IsPlainName(socket)) { skin.WeaponFieldSocket = socket; }
        else { Detail::Note(cfg, origin, L"\"weapon_field_socket\" must be a socket name like \"Attach_Weapon01\"; left out"); }
    }
    bool meshesOk = true;   // (3.11.2)
    for (const Json* part : Detail::Items(root.Find("meshes"), meshesOk))
    {
        FormMesh mesh;
        if (part->type == Json::Type::String) { mesh.Mesh = NormalizeObjectPath(Widen(part->string)); }
        else
        {
            mesh.Mesh = NormalizeObjectPath(Detail::StringOf(part->Find("mesh")));
            mesh.Socket = Detail::StringOf(part->Find("socket"));
            if (const Json* follow = part->Find("follow_pose"); follow && follow->type == Json::Type::Bool) { mesh.FollowPose = follow->boolean; }
        }
        if (mesh.Mesh.empty() || (!mesh.Socket.empty() && !Detail::IsPlainName(mesh.Socket))) { meshesOk = false; continue; }
        skin.Meshes.push_back(std::move(mesh));
    }
    if (!meshesOk) { Detail::Note(cfg, origin, L"\"meshes\" has entries that are not meshes ({\"mesh\", \"socket\", \"follow_pose\"} or a path); they are left out"); }
    // (3.18.0) "pack" and "sets": the moves it carries
    if (const std::wstring pack = Detail::StringOf(root.Find("pack")); !pack.empty())
    {
        if (Detail::IsPlainName(pack)) { skin.Pack = pack; }
        else { Detail::Note(cfg, origin, L"\"pack\" must be an animation pack's name like \"Battle10\"; left out"); }
    }
    if (const Json* sets = root.Find("sets"))
    {
        bool setsOk = sets->type == Json::Type::Object;
        if (setsOk)
        {
            for (const auto& [from, to] : sets->object)
            {
                const std::wstring f = Trim(Widen(from)), t = Detail::StringOf(&to);
                const bool twice = std::any_of(skin.Sets.begin(), skin.Sets.end(), [&](const auto& p) { return NameEquals(p.first, f); });
                if (!Detail::IsPlainName(f) || !Detail::IsPlainName(t) || NameEquals(f, t) || twice || skin.Sets.size() >= MaxFormSets)
                {
                    setsOk = false;
                    continue;
                }
                skin.Sets.emplace_back(f, t);
            }
        }
        if (!setsOk)
        {
            Detail::Note(cfg, origin, L"\"sets\": each entry must be a set name -> another set name (\"Neutral00\": \"Neutral10\"), each name once, " +
                                          std::to_wstring(MaxFormSets) + L" at most; bad entries left out");
        }
    }
    if (const Json* packages = root.Find("packages"); packages && packages->type == Json::Type::Array)
    {
        for (const auto& item : packages->array)
        {
            if (const std::wstring name = Detail::StringOf(item.Find("package")); !name.empty()) { skin.Packages.push_back(name); }
        }
    }
    if (skin.Model.empty())
    {
        Detail::Note(cfg, origin, L"has no \"model\"; skipped");
        return false;
    }
    if (skin.Characters.empty()) { Detail::Note(cfg, origin, L"names no \"characters\": no one wears skin " + skin.Name); }
    // its skeleton joins the family of the hub (only while its packages are installed)
    if (skin.Enabled && !skin.Family.empty() && !skin.Skeleton.empty() && !PathEquals(skin.Family, skin.Skeleton))
    {
        Pair family;
        family.Use = Method::Family;
        family.Receiving = skin.Family;
        family.Animation = {skin.Skeleton};
        family.Hub = skin.Family;
        family.RequiresPaks = {SkinsContainer};
        family.KeepProportions = skin.KeepProportions;
        family.ProportionBones = skin.ProportionBones;
        family.Origin = origin;
        cfg.Pairs.push_back(std::move(family));
    }
    cfg.Skins.push_back(std::move(skin));
    return true;
}

// After FinishConfig (one row per character): each enabled skin goes on the rows of its "characters"; a character with
// no row gets one made for the skin (SkinOnly). The first skin (in folder order) for a character wins. `installed`:
// SkinsContainer is installed (else every skin is off: its packages are not in the game).
inline void AttachSkins(Config& cfg, bool installed)
{
    if (cfg.Skins.empty()) { return; }
    for (size_t s = 0; s < cfg.Skins.size(); ++s)
    {
        const Skin& skin = cfg.Skins[s];
        if (!skin.Enabled)
        {
            Detail::Note(cfg, skin.Origin, L"skin " + skin.Name + L" is off (\"enabled\": false)");
            continue;
        }
        if (!installed)
        {
            Detail::Note(cfg, skin.Origin, L"skin " + skin.Name + L" is off: its packages are not in the game (" + std::wstring(SkinsContainer) +
                                                L" is not in ~mods; the editor's Build Skins installs it)");
            continue;
        }
        std::wstring on;
        for (const auto& character : skin.Characters)
        {
            AnimSetRow* row = nullptr;
            for (auto& r : cfg.AnimSets)
            {
                if (!r.Characters.empty() && PathEquals(r.Characters.front(), character))
                {
                    row = &r;
                    break;
                }
            }
            if (!row)
            {
                AnimSetRow made;
                made.Characters = {character};
                Form normal;
                normal.Name = skin.Name;
                made.Forms.List.push_back(std::move(normal));
                made.SkinOnly = true;
                made.Origin = skin.Origin;
                cfg.AnimSets.push_back(std::move(made));
                row = &cfg.AnimSets.back();
            }
            if (!skin.Worn)
            {
                on += (on.empty() ? L"" : L", ") + RowNameOfPack(character);   // (3.11.1: a choice for the row, not worn)
                continue;
            }
            if (row->Skin >= 0)
            {
                const Skin& first = cfg.Skins[static_cast<size_t>(row->Skin)];
                Detail::Note(cfg, skin.Origin, L"skin " + skin.Name + L" for " + RowNameOfPack(character) + L" ignored: it wears " + first.Name + L" (" + first.Folder + L")");
                continue;
            }
            row->Skin = static_cast<int>(s);
            row->SkinSpeaks = skin.Speaks;
            on += (on.empty() ? L"" : L", ") + RowNameOfPack(character);
        }
        Detail::Note(cfg, skin.Origin, L"skin " + skin.Name + (on.empty() ? std::wstring(L" is on no row") : (skin.Worn ? L" on " : L" a choice for ") + on));
    }
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
