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
#include <cstring>
#include <cwctype>
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

struct AnimSetRow
{
    std::vector<std::wstring> Characters;  // CharaSpec pack object paths (one per row after FinishConfig)
    std::vector<SetSource> Battle;         // sources of the Battle* sets, in order of preference
    std::vector<SetSource> Field;          // sources of every other set
    std::vector<std::wstring> Sets;        // set names to build besides the standard ones
    std::vector<AnimMove> Moves;
    std::wstring FieldActions;             // AnimationSetParentFolder the character's CharaSpec row should use (field actions)
    std::wstring Skeleton;                 // the character's own skeleton ("skeleton"), whose meshes get Sockets
    std::vector<std::pair<std::wstring, std::wstring>> Sockets; // 3.2: socket the game asks for -> socket or bone of this
                                                                // character that stands in for it (weapon in hand, ...)
    bool KeepProportions = false;          // 3.2 "proportions": the pairs and families of Skeleton keep every body's proportions
    bool Override = false;                 // 3.2 "override": joined before the other rows of its character (its sources, moves,
                                           // field actions and sockets win), e.g. a test file over a mod's own row
    std::wstring Player;                   // 3.3 "player": the character's BattlePlayerParameter row ("pt_Cloud")
    std::vector<PackAbilities> Abilities;  // 3.3 "abilities": commands and limits per primary animation pack
    bool RefreshAbilities = true;          // 3.3 "refresh_abilities": after a switch the mod has the game recalculate the
                                           // party member's status, which rebuilds its ability lists; false: they show
                                           // when the game next does
    std::vector<std::wstring> PackAssets;  // 3.3.1 "pack_assets": objects added to the character's CharaSpec pack (another
                                           // character's effect pack, a sound bank): loaded at the first map load, each goes
                                           // into the pack entry that lists an object of its class
    std::vector<std::wstring> Preload;     // 3.3 "preload": objects loaded and kept at the first map load (a CharaSpec pack a
                                           // damage source spawns, ...)
    std::vector<std::wstring> RequiresPaks;
    std::wstring Origin;

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

// Mode for every bone of a skeleton (names and parent indices of its reference skeleton).
inline std::vector<RetargetMode> ProportionModes(const std::vector<std::wstring>& names, const std::vector<int32_t>& parents)
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
        else if (Detail::IsBodyBone(names[i])) { modes[i] = RetargetMode::Skeleton; }
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
    return out;
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

struct Config
{
    std::vector<Pair> Pairs;
    std::vector<AnimSetRow> AnimSets;  // one row per character after FinishConfig
    std::vector<std::wstring> Messages;

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
            if (count > most)
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

// One "animation_sets" entry. Its "cutscene" entry becomes a family pair.
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
            AnimMove move{set, key, {}, {}};
            bool pathsOk = !animations.empty();
            for (const auto& animation : animations)
            {
                const std::wstring path = NormalizeObjectPath(animation);
                if (path.empty()) { pathsOk = false; }
                move.Chain.push_back(path);
            }
            if (pathsOk) { move.Animation = move.Chain.front(); }
            if (move.Chain.size() < 2) { move.Chain.clear(); }
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
    // "sockets": [{"socket": "Attach_Weapon01", "use": "Attach_Weapon_Right01"}]: the socket the game asks for -> the socket
    // (or bone) of this character that stands in for it (an object {"Attach_Weapon01": "Attach_Weapon_Right01"} works too).
    if (const Json* sockets = entry.Find("sockets"))
    {
        bool socketsOk = sockets->type == Json::Type::Object || sockets->type == Json::Type::Array;
        const auto addSocket = [&](const std::wstring& name, const std::wstring& use) {
            if (name.empty() || use.empty() || name.find_first_of(L"/.:'\"") != std::wstring::npos || use.find_first_of(L"/.:'\"") != std::wstring::npos)
            {
                socketsOk = false;
                return;
            }
            if (NameEquals(name, use)) { return; }
            if (std::any_of(row.Sockets.begin(), row.Sockets.end(), [&](const auto& s) { return NameEquals(s.first, name); }))
            {
                Note(cfg, origin, where + L" sockets: " + name + L" is listed twice; the first one is kept");
                return;
            }
            row.Sockets.emplace_back(name, use);
        };
        if (sockets->type == Json::Type::Object)
        {
            for (const auto& [key, value] : sockets->object) { addSocket(Trim(Widen(key)), StringOf(&value)); }
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
                addSocket(name, use);
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
    if (row.Battle.empty() && row.Field.empty() && row.Moves.empty() && row.FieldActions.empty() && row.Sockets.empty() && !row.KeepProportions &&
        row.Abilities.empty() && row.Preload.empty() && row.PackAssets.empty())
    {
        if (!entry.Find("cutscene"))
        {
            Note(cfg, origin, where + L" has no \"battle\", \"field\", \"moves\", \"sockets\", \"proportions\", \"abilities\", \"pack_assets\" or \"preload\", skipped");
        }
        return;
    }
    cfg.AnimSets.push_back(std::move(row));
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
    // "pairs" and, for readability, "families" (entries of the second list default to "method": "family"), plus the
    // "animation_sets" rows (3.1).
    const Json* pairs = root.Find("pairs");
    const Json* families = root.Find("families");
    const Json* sets = root.Find("animation_sets");
    if ((!pairs || pairs->type != Json::Type::Array) && (!families || families->type != Json::Type::Array) &&
        (!sets || sets->type != Json::Type::Array))
    {
        Detail::Note(cfg, origin, L"missing \"pairs\", \"families\" or \"animation_sets\" array, file skipped");
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
        pair.KeepProportions = Detail::ProportionsOf(entry, false);
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
            for (const auto& path : row.Preload) { Detail::AddUnique(existing.Preload, path); }
            for (const auto& path : row.PackAssets) { Detail::AddUnique(existing.PackAssets, path); }
            // 3.3: the first row's player row wins; packs the earlier rows do not list are added. Any row can turn the
            // status recalculation off.
            if (!row.RefreshAbilities) { existing.RefreshAbilities = false; }
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
            if (existing.Origin.find(row.Origin) == std::wstring::npos) { existing.Origin += L", " + row.Origin; }
            Detail::Note(cfg, row.Origin, L"animation set row for " + character + L" joined with an earlier row for the same character");
        }
    }
    cfg.AnimSets = std::move(result);
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
