// Create a Character System Setup (Win32, x64).
//
// One exe that installs the two parts of the system, both carried in its payload (tools/make_setup.py):
//   game    the UE4SS mod     -> <game>\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\
//   plugin  the editor plugin -> <End project>\Plugins\RebirthSkelCompat\
// It finds the game (Steam, Epic or Browse) and the End project, checks UE4SS and the engine build,
// moves every file it replaces to a backup folder first, and can uninstall what it installed:
// only files it installed and that are unchanged are deleted; edited ones go to the backup folder.
//
// Command line: /S (no window) /game:<folder> /project:<.uproject> /nogame /noplugin /install /uninstall
// A silent uninstall only acts on the parts given with /game: or /project:.
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <commctrl.h>
#include <shellapi.h>
#include <shlobj.h>
#include <shobjidl.h>
#include <tlhelp32.h>

#include <algorithm>
#include <memory>
#include <set>
#include <string>
#include <vector>

#include "SetupCore.hpp"
#include "resource.h"

namespace
{
using SetupCore::FileEntry;

const wchar_t* const ModFolderName = L"RebirthSkelCompat";     // folder names stay; only the text says Create a Character System
const wchar_t* const PluginFolderName = L"RebirthSkelCompat";
const wchar_t* const PluginFileName = L"RebirthSkelCompat.uplugin";
const wchar_t* const RecordName = L"CreateACharacterSystem.install.txt";
const wchar_t* const LogName = L"CreateACharacterSystem-Setup.log";
const wchar_t* const PluginBackups = L"CreateACharacterSystem-Backups"; // in the project folder (not Saved, which people clear)
const wchar_t* const AppTitle = L"Create a Character System Setup";

// ---------------------------------------------------------------- strings and paths

std::wstring Widen(const std::string& text)
{
    if (text.empty()) { return {}; }
    const int n = MultiByteToWideChar(CP_UTF8, 0, text.data(), static_cast<int>(text.size()), nullptr, 0);
    std::wstring out(static_cast<size_t>(n > 0 ? n : 0), L'\0');
    if (n > 0) { MultiByteToWideChar(CP_UTF8, 0, text.data(), static_cast<int>(text.size()), out.data(), n); }
    return out;
}

std::string Narrow(const std::wstring& text)
{
    if (text.empty()) { return {}; }
    const int n = WideCharToMultiByte(CP_UTF8, 0, text.data(), static_cast<int>(text.size()), nullptr, 0, nullptr, nullptr);
    std::string out(static_cast<size_t>(n > 0 ? n : 0), '\0');
    if (n > 0) { WideCharToMultiByte(CP_UTF8, 0, text.data(), static_cast<int>(text.size()), out.data(), n, nullptr, nullptr); }
    return out;
}

std::wstring Lower(std::wstring text)
{
    if (!text.empty()) { CharLowerBuffW(text.data(), static_cast<DWORD>(text.size())); }
    return text;
}

bool SamePath(const std::wstring& a, const std::wstring& b) { return Lower(a) == Lower(b); }

std::wstring Trim(std::wstring text)
{
    const wchar_t* space = L" \t\r\n\"";
    const size_t first = text.find_first_not_of(space);
    if (first == std::wstring::npos) { return {}; }
    const size_t last = text.find_last_not_of(space);
    return text.substr(first, last - first + 1);
}

// Backslashes, no doubled separators (except a leading \\ of a share), no trailing separator (except a drive root).
std::wstring CleanPath(std::wstring path)
{
    path = Trim(path);
    std::replace(path.begin(), path.end(), L'/', L'\\');
    std::wstring out;
    for (size_t i = 0; i < path.size(); ++i)
    {
        if (path[i] == L'\\' && !out.empty() && out.back() == L'\\' && i > 1) { continue; }
        out += path[i];
    }
    while (out.size() > 3 && out.back() == L'\\') { out.pop_back(); }
    return out;
}

std::wstring FullPath(const std::wstring& path)
{
    const std::wstring clean = CleanPath(path);
    if (clean.empty()) { return {}; }
    DWORD n = GetFullPathNameW(clean.c_str(), 0, nullptr, nullptr);
    if (!n) { return clean; }
    std::wstring out(n, L'\0');
    n = GetFullPathNameW(clean.c_str(), n, out.data(), nullptr);
    out.resize(n);
    return CleanPath(out);
}

std::wstring Join(const std::wstring& a, const std::wstring& b)
{
    if (a.empty()) { return b; }
    return (a.back() == L'\\' ? a : a + L"\\") + b;
}

std::wstring Parent(const std::wstring& path)
{
    const size_t slash = path.find_last_of(L'\\');
    if (slash == std::wstring::npos) { return {}; }
    if (slash == 2 && path.size() > 1 && path[1] == L':') { return path.size() > 3 ? path.substr(0, 3) : std::wstring{}; }
    return path.substr(0, slash);
}

std::wstring FileName(const std::wstring& path)
{
    const size_t slash = path.find_last_of(L'\\');
    return slash == std::wstring::npos ? path : path.substr(slash + 1);
}

std::wstring Native(const std::string& relative)
{
    std::wstring out = Widen(relative);
    std::replace(out.begin(), out.end(), L'/', L'\\');
    return out;
}

bool FileExists(const std::wstring& path)
{
    const DWORD a = GetFileAttributesW(path.c_str());
    return a != INVALID_FILE_ATTRIBUTES && !(a & FILE_ATTRIBUTE_DIRECTORY);
}

bool DirExists(const std::wstring& path)
{
    const DWORD a = GetFileAttributesW(path.c_str());
    return a != INVALID_FILE_ATTRIBUTES && (a & FILE_ATTRIBUTE_DIRECTORY);
}

bool IsReparsePoint(const std::wstring& path)
{
    const DWORD a = GetFileAttributesW(path.c_str());
    return a != INVALID_FILE_ATTRIBUTES && (a & FILE_ATTRIBUTE_REPARSE_POINT);
}

std::wstring ErrorText(DWORD error)
{
    wchar_t* text = nullptr;
    FormatMessageW(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS, nullptr, error, 0,
                   reinterpret_cast<wchar_t*>(&text), 0, nullptr);
    std::wstring out = text ? Trim(text) : L"error " + std::to_wstring(error);
    if (text) { LocalFree(text); }
    while (!out.empty() && (out.back() == L'.' || out.back() == L'\r' || out.back() == L'\n')) { out.pop_back(); }
    return out + L" (" + std::to_wstring(error) + L")";
}

bool InUse(DWORD error) { return error == ERROR_SHARING_VIOLATION || error == ERROR_LOCK_VIOLATION || error == ERROR_USER_MAPPED_FILE || error == ERROR_ACCESS_DENIED; }

bool MakeDirs(const std::wstring& path)
{
    if (path.empty() || DirExists(path)) { return true; }
    const int result = SHCreateDirectoryExW(nullptr, path.c_str(), nullptr);
    return result == ERROR_SUCCESS || result == ERROR_ALREADY_EXISTS || DirExists(path);
}

std::wstring Stamp()
{
    SYSTEMTIME t{};
    GetLocalTime(&t);
    wchar_t text[32];
    wsprintfW(text, L"%04u%02u%02u-%02u%02u%02u", t.wYear, t.wMonth, t.wDay, t.wHour, t.wMinute, t.wSecond);
    return text;
}

std::wstring KnownFolder(REFKNOWNFOLDERID id)
{
    PWSTR path = nullptr;
    std::wstring out;
    if (SUCCEEDED(SHGetKnownFolderPath(id, KF_FLAG_DEFAULT, nullptr, &path)) && path) { out = path; }
    if (path) { CoTaskMemFree(path); }
    return out;
}

std::wstring TempDir()
{
    wchar_t buffer[MAX_PATH + 2];
    const DWORD n = GetTempPathW(MAX_PATH + 1, buffer);
    return n ? CleanPath(std::wstring(buffer, n)) : std::wstring(L".");
}

// ---------------------------------------------------------------- files

bool ReadAll(const std::wstring& path, std::vector<uint8_t>& out, uint64_t limit = 512ull << 20)
{
    out.clear();
    HANDLE file = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING,
                              FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN, nullptr);
    if (file == INVALID_HANDLE_VALUE) { return false; }
    LARGE_INTEGER size{};
    bool ok = GetFileSizeEx(file, &size) && size.QuadPart >= 0 && static_cast<uint64_t>(size.QuadPart) <= limit;
    if (ok)
    {
        out.resize(static_cast<size_t>(size.QuadPart));
        size_t done = 0;
        while (ok && done < out.size())
        {
            DWORD got = 0;
            const DWORD want = static_cast<DWORD>(std::min<size_t>(out.size() - done, 1u << 24));
            ok = ReadFile(file, out.data() + done, want, &got, nullptr) && got > 0;
            done += got;
        }
    }
    CloseHandle(file);
    if (!ok) { out.clear(); }
    return ok;
}

// A text file as UTF-8 (UTF-16 with a BOM, as UE writes some .ini files, is converted).
std::string ReadText(const std::wstring& path, uint64_t limit = 16u << 20)
{
    std::vector<uint8_t> bytes;
    if (!ReadAll(path, bytes, limit)) { return {}; }
    if (bytes.size() >= 2 && bytes[0] == 0xFF && bytes[1] == 0xFE)
    {
        std::wstring wide((bytes.size() - 2) / 2, L'\0');
        std::memcpy(wide.data(), bytes.data() + 2, wide.size() * 2);
        return Narrow(wide);
    }
    size_t skip = (bytes.size() >= 3 && bytes[0] == 0xEF && bytes[1] == 0xBB && bytes[2] == 0xBF) ? 3 : 0;
    return std::string(bytes.begin() + static_cast<std::ptrdiff_t>(skip), bytes.end());
}

bool WriteAll(const std::wstring& path, const uint8_t* data, size_t size, DWORD& error)
{
    HANDLE file = CreateFileW(path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE)
    {
        error = GetLastError();
        return false;
    }
    size_t done = 0;
    bool ok = true;
    while (ok && done < size)
    {
        DWORD wrote = 0;
        const DWORD want = static_cast<DWORD>(std::min<size_t>(size - done, 1u << 24));
        ok = WriteFile(file, data + done, want, &wrote, nullptr) && wrote == want;
        done += wrote;
    }
    if (!ok) { error = GetLastError(); }
    if (!CloseHandle(file) && ok)
    {
        error = GetLastError();
        ok = false;
    }
    if (!ok) { DeleteFileW(path.c_str()); }
    return ok;
}

bool SameContent(const std::wstring& path, const FileEntry& entry)
{
    WIN32_FILE_ATTRIBUTE_DATA info{};
    if (!GetFileAttributesExW(path.c_str(), GetFileExInfoStandard, &info) || (info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) { return false; }
    const uint64_t size = (static_cast<uint64_t>(info.nFileSizeHigh) << 32) | info.nFileSizeLow;
    if (size != entry.Size) { return false; }
    std::vector<uint8_t> bytes;
    return ReadAll(path, bytes) && SetupCore::Crc32(bytes.data(), bytes.size()) == entry.Crc;
}

// Does the file at `path` contain `needle` (UE4SS.dll and its build tag)?
bool FileContains(const std::wstring& path, const std::string& needle)
{
    HANDLE file = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING,
                              FILE_FLAG_SEQUENTIAL_SCAN, nullptr);
    if (file == INVALID_HANDLE_VALUE) { return false; }
    SetupCore::StreamSearch search(needle);
    std::vector<uint8_t> block(1u << 20);
    DWORD got = 0;
    while (ReadFile(file, block.data(), static_cast<DWORD>(block.size()), &got, nullptr) && got > 0)
    {
        if (search.Feed(block.data(), got)) { break; }
    }
    CloseHandle(file);
    return search.Matched();
}

// Every file under `dir` (recursive, not following links), as paths relative to `dir` with '/' separators.
void ListFiles(const std::wstring& dir, const std::wstring& prefix, std::vector<std::wstring>& out, int depth = 0)
{
    if (depth > 12) { return; }
    WIN32_FIND_DATAW data{};
    HANDLE find = FindFirstFileW(Join(dir, L"*").c_str(), &data);
    if (find == INVALID_HANDLE_VALUE) { return; }
    do
    {
        const std::wstring name = data.cFileName;
        if (name == L"." || name == L"..") { continue; }
        const std::wstring rel = prefix.empty() ? name : prefix + L"/" + name;
        if (data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)
        {
            if (!(data.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT)) { ListFiles(Join(dir, name), rel, out, depth + 1); }
        }
        else
        {
            out.push_back(rel);
        }
    } while (FindNextFileW(find, &data));
    FindClose(find);
}

std::vector<std::wstring> SubDirs(const std::wstring& dir)
{
    std::vector<std::wstring> out;
    WIN32_FIND_DATAW data{};
    HANDLE find = FindFirstFileExW(Join(dir, L"*").c_str(), FindExInfoBasic, &data, FindExSearchLimitToDirectories, nullptr, 0);
    if (find == INVALID_HANDLE_VALUE) { return out; }
    do
    {
        const std::wstring name = data.cFileName;
        if (name == L"." || name == L".." || !(data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) || (data.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT))
        {
            continue;
        }
        out.push_back(Join(dir, name));
    } while (FindNextFileW(find, &data) && out.size() < 4000);
    FindClose(find);
    return out;
}

// Files named `name` under `dir`, at most `depth` folders down (not following links).
void FindNamed(const std::wstring& dir, const std::wstring& name, int depth, std::vector<std::wstring>& out)
{
    if (FileExists(Join(dir, name))) { out.push_back(Join(dir, name)); }
    if (depth <= 0) { return; }
    for (const auto& sub : SubDirs(dir)) { FindNamed(sub, name, depth - 1, out); }
}

// ---------------------------------------------------------------- system

// A REG_SZ / REG_EXPAND_SZ value (expanded), or empty.
std::wstring RegString(HKEY root, const std::wstring& key, const std::wstring& value)
{
    HKEY opened = nullptr;
    if (RegOpenKeyExW(root, key.c_str(), 0, KEY_QUERY_VALUE, &opened) != ERROR_SUCCESS) { return {}; }
    DWORD type = 0, size = 0;
    std::wstring out;
    if (RegQueryValueExW(opened, value.c_str(), nullptr, &type, nullptr, &size) == ERROR_SUCCESS && (type == REG_SZ || type == REG_EXPAND_SZ) && size >= 2 &&
        size < (1u << 20))
    {
        std::vector<wchar_t> buffer(size / sizeof(wchar_t) + 1, L'\0');
        DWORD got = size;
        if (RegQueryValueExW(opened, value.c_str(), nullptr, &type, reinterpret_cast<BYTE*>(buffer.data()), &got) == ERROR_SUCCESS)
        {
            out.assign(buffer.data(), wcsnlen(buffer.data(), buffer.size()));
            if (type == REG_EXPAND_SZ)
            {
                const DWORD n = ExpandEnvironmentStringsW(out.c_str(), nullptr, 0);
                if (n)
                {
                    std::wstring expanded(n, L'\0');
                    ExpandEnvironmentStringsW(out.c_str(), expanded.data(), n);
                    out.assign(expanded.c_str());
                }
            }
        }
    }
    RegCloseKey(opened);
    return out;
}

// Every string value of a key (the registered engines under ...\Unreal Engine\Builds).
std::vector<std::wstring> RegStrings(HKEY root, const std::wstring& key)
{
    std::vector<std::wstring> out;
    HKEY opened = nullptr;
    if (RegOpenKeyExW(root, key.c_str(), 0, KEY_QUERY_VALUE, &opened) != ERROR_SUCCESS) { return out; }
    for (DWORD i = 0; i < 256; ++i)
    {
        wchar_t name[512];
        DWORD nameLength = 512, type = 0, size = 0;
        if (RegEnumValueW(opened, i, name, &nameLength, nullptr, &type, nullptr, &size) != ERROR_SUCCESS) { break; }
        if (type == REG_SZ || type == REG_EXPAND_SZ) { out.push_back(RegString(root, key, std::wstring(name, nameLength))); }
    }
    RegCloseKey(opened);
    return out;
}

// Is a process whose exe name starts with `prefix` running ("UE4Editor" also finds UE4Editor-Win64-DebugGame.exe)?
bool ProcessRunning(const wchar_t* prefix)
{
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snap == INVALID_HANDLE_VALUE) { return false; }
    PROCESSENTRY32W entry{};
    entry.dwSize = sizeof(entry);
    const std::wstring wanted = Lower(prefix);
    bool found = false;
    for (BOOL ok = Process32FirstW(snap, &entry); ok && !found; ok = Process32NextW(snap, &entry)) { found = Lower(entry.szExeFile).rfind(wanted, 0) == 0; }
    CloseHandle(snap);
    return found;
}

bool Elevated()
{
    HANDLE token = nullptr;
    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token)) { return false; }
    TOKEN_ELEVATION elevation{};
    DWORD size = 0;
    const bool ok = GetTokenInformation(token, TokenElevation, &elevation, sizeof(elevation), &size) && elevation.TokenIsElevated;
    CloseHandle(token);
    return ok;
}

// Can this process create files in `dir` (or in its nearest existing parent)?
bool CanWrite(const std::wstring& dir, DWORD& error)
{
    std::wstring at = dir;
    while (!at.empty() && !DirExists(at)) { at = Parent(at); }
    if (at.empty())
    {
        error = ERROR_PATH_NOT_FOUND;
        return false;
    }
    const std::wstring probe = Join(at, L".cacs-write-test-" + std::to_wstring(GetCurrentProcessId()) + L".tmp");
    HANDLE file = CreateFileW(probe.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW, FILE_ATTRIBUTE_TEMPORARY | FILE_FLAG_DELETE_ON_CLOSE, nullptr);
    if (file == INVALID_HANDLE_VALUE)
    {
        error = GetLastError();
        return error == ERROR_FILE_EXISTS; // someone else's probe: the folder is writable
    }
    CloseHandle(file);
    return true;
}

// ---------------------------------------------------------------- payload

struct Payload
{
    std::wstring Exe;
    SetupCore::Footer Foot{};
    SetupCore::Index Index;

    bool Load(std::wstring& why)
    {
        wchar_t path[32768];
        const DWORD n = GetModuleFileNameW(nullptr, path, 32768);
        if (!n || n >= 32768)
        {
            why = L"Setup can't find its own file";
            return false;
        }
        Exe.assign(path, n);
        HANDLE file = CreateFileW(Exe.c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (file == INVALID_HANDLE_VALUE)
        {
            why = L"Setup can't read its own file: " + ErrorText(GetLastError());
            return false;
        }
        bool ok = false;
        LARGE_INTEGER size{};
        std::string text;
        if (GetFileSizeEx(file, &size) && static_cast<uint64_t>(size.QuadPart) > sizeof(SetupCore::Footer))
        {
            const uint64_t total = static_cast<uint64_t>(size.QuadPart);
            ok = ReadAt(file, total - sizeof(Foot), &Foot, sizeof(Foot)) && std::memcmp(Foot.Magic, SetupCore::FooterMagic, 8) == 0 && Foot.Version == 1 &&
                 Foot.PayloadOffset <= Foot.IndexOffset && Foot.IndexSize > 0 && Foot.IndexSize < (16u << 20) &&
                 Foot.IndexOffset + Foot.IndexSize + sizeof(Foot) == total;
            if (ok)
            {
                text.resize(static_cast<size_t>(Foot.IndexSize));
                ok = ReadAt(file, Foot.IndexOffset, text.data(), text.size()) &&
                     SetupCore::Crc32(reinterpret_cast<const uint8_t*>(text.data()), text.size()) == Foot.IndexCrc;
            }
        }
        CloseHandle(file);
        if (!ok)
        {
            why = L"This Setup file is damaged or incomplete (its payload is missing). Download it again.";
            return false;
        }
        std::string problem;
        if (!SetupCore::ParseIndex(text, Foot.IndexOffset - Foot.PayloadOffset, Index, problem))
        {
            why = L"This Setup file is damaged: " + Widen(problem) + L". Download it again.";
            return false;
        }
        return true;
    }

    bool Extract(const FileEntry& entry, std::vector<uint8_t>& out, std::wstring& why) const
    {
        HANDLE file = CreateFileW(Exe.c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (file == INVALID_HANDLE_VALUE)
        {
            why = L"Setup can't read its own file: " + ErrorText(GetLastError());
            return false;
        }
        std::vector<uint8_t> packed(static_cast<size_t>(entry.Packed));
        const bool read = packed.empty() || ReadAt(file, Foot.PayloadOffset + entry.Offset, packed.data(), packed.size());
        CloseHandle(file);
        std::string problem;
        if (!read || !SetupCore::Unpack(entry, packed.data(), packed.size(), out, problem))
        {
            why = read ? Widen(problem) : L"Setup can't read " + Widen(entry.Path) + L" from its own file";
            return false;
        }
        return true;
    }

    std::wstring Value(const char* key) const { return Widen(Index.Value(key)); }

private:
    static bool ReadAt(HANDLE file, uint64_t offset, void* into, size_t size)
    {
        auto* at = static_cast<uint8_t*>(into);
        while (size)
        {
            OVERLAPPED where{};
            where.Offset = static_cast<DWORD>(offset);
            where.OffsetHigh = static_cast<DWORD>(offset >> 32);
            DWORD got = 0;
            const DWORD want = static_cast<DWORD>(std::min<size_t>(size, 1u << 24));
            if (!ReadFile(file, at, want, &got, &where) || got == 0) { return false; }
            at += got;
            offset += got;
            size -= got;
        }
        return true;
    }
};

Payload ThePayload;

std::vector<const FileEntry*> FilesOf(const char* component)
{
    std::vector<const FileEntry*> out;
    for (const auto& f : ThePayload.Index.Files)
    {
        if (f.Component == component) { out.push_back(&f); }
    }
    return out;
}

// ---------------------------------------------------------------- the game

enum class Level { Ok, Warn, Error, Info };

struct GameInfo
{
    bool Valid = false;
    std::wstring Root, Win64, ModsDir, ModDir;
    int Ue4ss = 0;            // 0 not installed, 1 ue4ss\UE4SS.dll (3.x), 2 UE4SS.dll next to the game (old layout)
    bool Ue4ssMatches = false;
    bool Present = false;     // the mod's main.dll is there
    bool HasRecord = false;   // Setup installed it (what Uninstall needs)
    std::wstring PresentVersion;
    std::wstring Status;
    Level StatusLevel = Level::Info;
};

std::wstring GameExe(const std::wstring& win64)
{
    if (FileExists(Join(win64, L"ff7rebirth_.exe"))) { return L"ff7rebirth_.exe"; }
    WIN32_FIND_DATAW data{};
    HANDLE find = FindFirstFileW(Join(win64, L"ff7rebirth*.exe").c_str(), &data);
    if (find == INVALID_HANDLE_VALUE) { return {}; }
    FindClose(find);
    return data.cFileName;
}

// The game folder (the one holding End\) for any folder or file the user points at inside it.
std::wstring GameRootOf(const std::wstring& any)
{
    std::wstring at = FullPath(any);
    if (FileExists(at)) { at = Parent(at); }
    for (int up = 0; up < 8 && !at.empty(); ++up)
    {
        const std::wstring win64 = Join(at, L"End\\Binaries\\Win64");
        if (DirExists(win64) && !GameExe(win64).empty()) { return at; }
        const std::wstring parent = Parent(at);
        if (parent == at) { break; }
        at = parent;
    }
    return {};
}

std::string Ue4ssTag() { return ThePayload.Index.Value("ue4ss_tag").empty() ? std::string("c0a8d4c") : ThePayload.Index.Value("ue4ss_tag"); }

GameInfo InspectGame(const std::wstring& any)
{
    GameInfo g;
    if (Trim(any).empty())
    {
        g.Status = L"Pick the FINAL FANTASY VII REBIRTH folder (Browse).";
        g.StatusLevel = Level::Info;
        return g;
    }
    g.Root = GameRootOf(any);
    if (g.Root.empty())
    {
        g.Status = L"No FINAL FANTASY VII REBIRTH here (Setup looks for End\\Binaries\\Win64\\ff7rebirth_.exe).";
        g.StatusLevel = Level::Error;
        return g;
    }
    g.Win64 = Join(g.Root, L"End\\Binaries\\Win64");
    std::wstring ue4ssDll;
    if (FileExists(Join(g.Win64, L"ue4ss\\UE4SS.dll")))
    {
        g.Ue4ss = 1;
        g.ModsDir = Join(g.Win64, L"ue4ss\\Mods");
        ue4ssDll = Join(g.Win64, L"ue4ss\\UE4SS.dll");
    }
    else if (FileExists(Join(g.Win64, L"UE4SS.dll")))
    {
        g.Ue4ss = 2;
        g.ModsDir = Join(g.Win64, L"Mods");
        ue4ssDll = Join(g.Win64, L"UE4SS.dll");
    }
    else
    {
        g.ModsDir = Join(g.Win64, L"ue4ss\\Mods");
    }
    g.ModDir = Join(g.ModsDir, ModFolderName);
    if (IsReparsePoint(g.ModDir))
    {
        g.Status = L"ue4ss\\Mods\\" + std::wstring(ModFolderName) + L" is a link to another folder: Setup leaves it alone. Install by hand.";
        g.StatusLevel = Level::Error;
        return g;
    }
    g.Valid = true;
    if (g.Ue4ss)
    {
        // UE4SS.dll is ~24 MB: look again only when it changed.
        static std::wstring lastPath;
        static FILETIME lastTime{};
        static bool lastMatch = false;
        WIN32_FILE_ATTRIBUTE_DATA info{};
        GetFileAttributesExW(ue4ssDll.c_str(), GetFileExInfoStandard, &info);
        if (!SamePath(lastPath, ue4ssDll) || CompareFileTime(&lastTime, &info.ftLastWriteTime) != 0)
        {
            lastPath = ue4ssDll;
            lastTime = info.ftLastWriteTime;
            lastMatch = FileContains(ue4ssDll, Ue4ssTag());
        }
        g.Ue4ssMatches = lastMatch;
    }
    const std::wstring dll = Join(g.ModDir, L"dlls\\main.dll");
    g.HasRecord = FileExists(Join(g.ModDir, RecordName));
    if (FileExists(dll))
    {
        g.Present = true;
        std::vector<uint8_t> bytes;
        if (ReadAll(dll, bytes, 64u << 20))
        {
            const auto versions = SetupCore::DllVersions(bytes.data(), bytes.size());
            if (versions.size() == 1) { g.PresentVersion = Widen(versions.front()); }
        }
    }
    const std::wstring tag = Widen(Ue4ssTag());
    const std::wstring there = g.Present ? (g.PresentVersion.empty() ? L" Replaces the version there now." : L" Replaces " + g.PresentVersion + L" there now.")
                                         : std::wstring{};
    if (g.Ue4ss == 0)
    {
        g.Status = L"UE4SS isn't installed in this game. The mod needs UE4SS 3.0.1 (" + tag + L"): install it first, or now and UE4SS after.";
        g.StatusLevel = Level::Warn;
    }
    else if (!g.Ue4ssMatches)
    {
        g.Status = L"UE4SS found, but not build " + tag + L" this mod is built for. If the game crashes at start or the mod doesn't load, use UE4SS 3.0.1 (" + tag + L")." + there;
        g.StatusLevel = Level::Warn;
    }
    else
    {
        g.Status = L"UE4SS 3.0.1 (" + tag + L") found. Installs into ue4ss\\Mods\\" + ModFolderName + L"." + there;
        g.StatusLevel = Level::Ok;
    }
    if (g.Ue4ss == 2) { g.Status += L" (Old UE4SS layout: mods go in Win64\\Mods.)"; }
    return g;
}

void AddUnique(std::vector<std::wstring>& list, const std::wstring& item)
{
    if (item.empty()) { return; }
    for (const auto& o : list)
    {
        if (SamePath(o, item)) { return; }
    }
    list.push_back(item);
}

std::vector<std::wstring> FindGames()
{
    std::vector<std::wstring> candidates;
    std::vector<std::wstring> steams;
    AddUnique(steams, CleanPath(RegString(HKEY_CURRENT_USER, L"Software\\Valve\\Steam", L"SteamPath")));
    AddUnique(steams, CleanPath(RegString(HKEY_LOCAL_MACHINE, L"SOFTWARE\\WOW6432Node\\Valve\\Steam", L"InstallPath")));
    AddUnique(steams, CleanPath(RegString(HKEY_LOCAL_MACHINE, L"SOFTWARE\\Valve\\Steam", L"InstallPath")));
    AddUnique(steams, L"C:\\Program Files (x86)\\Steam");
    std::vector<std::wstring> libraries;
    for (const auto& steam : steams)
    {
        AddUnique(libraries, steam);
        for (const auto& lib : SetupCore::SteamLibraries(ReadText(Join(steam, L"steamapps\\libraryfolders.vdf")))) { AddUnique(libraries, CleanPath(Widen(lib))); }
        for (const auto& lib : SetupCore::SteamLibraries(ReadText(Join(steam, L"config\\libraryfolders.vdf")))) { AddUnique(libraries, CleanPath(Widen(lib))); }
    }
    for (const auto& lib : libraries)
    {
        const std::string dir = SetupCore::VdfValue(ReadText(Join(lib, L"steamapps\\appmanifest_2909400.acf")), "installdir");
        if (!dir.empty()) { AddUnique(candidates, Join(lib, L"steamapps\\common\\" + Widen(dir))); }
        AddUnique(candidates, Join(lib, L"steamapps\\common\\FINAL FANTASY VII REBIRTH"));
    }
    // Epic Games Store manifests
    const std::wstring manifests = Join(KnownFolder(FOLDERID_ProgramData), L"Epic\\EpicGamesLauncher\\Data\\Manifests");
    WIN32_FIND_DATAW data{};
    HANDLE find = FindFirstFileW(Join(manifests, L"*.item").c_str(), &data);
    if (find != INVALID_HANDLE_VALUE)
    {
        do
        {
            for (const auto& where : SetupCore::JsonStrings(ReadText(Join(manifests, data.cFileName), 4u << 20), "InstallLocation"))
            {
                AddUnique(candidates, CleanPath(Widen(where)));
            }
        } while (FindNextFileW(find, &data));
        FindClose(find);
    }
    std::vector<std::wstring> games;
    for (const auto& c : candidates)
    {
        const std::wstring root = DirExists(c) ? GameRootOf(c) : std::wstring{};
        if (!root.empty() && SamePath(root, FullPath(c))) { AddUnique(games, root); }
    }
    return games;
}

// ---------------------------------------------------------------- the End project

struct ProjectInfo
{
    bool Valid = false;
    std::wstring File, Dir, PluginDir;
    bool IsEnd = false;
    std::wstring EngineRoot, EngineBuild;
    int EngineMatch = 0;      // 1 same build as the plugin's, -1 different, 0 unknown
    bool Present = false;     // a RebirthSkelCompat.uplugin is in Plugins\RebirthSkelCompat
    bool HasRecord = false;   // Setup installed it
    std::wstring PresentVersion;
    std::vector<std::wstring> OtherCopies; // the plugin somewhere else in the project or the engine
    std::wstring Status;
    Level StatusLevel = Level::Info;
};

bool LooksLikeEndProject(const std::string& uproject, const std::wstring& file)
{
    return SamePath(FileName(file), L"End.uproject") || uproject.find("\"EndGame\"") != std::string::npos ||
           uproject.find("\"EndDataObject\"") != std::string::npos;
}

std::wstring EngineRootOf(const std::wstring& projectDir, const std::string& uproject)
{
    const std::wstring association = Widen(SetupCore::JsonString(uproject, "EngineAssociation"));
    std::wstring root;
    if (!association.empty() && association.front() == L'{')
    {
        root = RegString(HKEY_CURRENT_USER, L"SOFTWARE\\Epic Games\\Unreal Engine\\Builds", association);
    }
    else if (!association.empty())
    {
        root = RegString(HKEY_LOCAL_MACHINE, L"SOFTWARE\\EpicGames\\Unreal Engine\\" + association, L"InstalledDirectory");
    }
    if (root.empty())
    {
        // A project inside a source engine's tree: look upwards for Engine\Binaries.
        for (std::wstring at = projectDir; !at.empty(); at = Parent(at))
        {
            if (FileExists(Join(at, L"Engine\\Binaries\\Win64\\UE4Editor.modules")))
            {
                root = at;
                break;
            }
            if (Parent(at) == at) { break; }
        }
    }
    return root.empty() ? std::wstring{} : FullPath(root);
}

ProjectInfo InspectProject(const std::wstring& any)
{
    ProjectInfo p;
    std::wstring file = FullPath(any);
    if (Trim(any).empty())
    {
        p.Status = L"Only needed to make characters: pick your End project's End.uproject (Browse).";
        p.StatusLevel = Level::Info;
        return p;
    }
    if (DirExists(file))
    {
        // A folder: its End.uproject, or its only .uproject.
        if (FileExists(Join(file, L"End.uproject"))) { file = Join(file, L"End.uproject"); }
        else
        {
            WIN32_FIND_DATAW data{};
            HANDLE find = FindFirstFileW(Join(file, L"*.uproject").c_str(), &data);
            if (find != INVALID_HANDLE_VALUE)
            {
                file = Join(file, data.cFileName);
                FindClose(find);
            }
        }
    }
    if (!FileExists(file) || Lower(file).size() < 9 || Lower(file).substr(file.size() - 9) != L".uproject")
    {
        p.Status = L"Pick the End.uproject file of your End project.";
        p.StatusLevel = Level::Error;
        return p;
    }
    p.File = file;
    p.Dir = Parent(file);
    p.PluginDir = Join(p.Dir, L"Plugins\\" + std::wstring(PluginFolderName));
    if (IsReparsePoint(p.PluginDir) || IsReparsePoint(Join(p.PluginDir, L"Source")))
    {
        p.Status = L"Plugins\\" + std::wstring(PluginFolderName) + L" is a link to another folder: Setup leaves it alone. Install by hand.";
        p.StatusLevel = Level::Error;
        return p;
    }
    const std::string uproject = ReadText(file, 4u << 20);
    p.IsEnd = LooksLikeEndProject(uproject, file);
    p.EngineRoot = EngineRootOf(p.Dir, uproject);
    if (!p.EngineRoot.empty())
    {
        p.EngineBuild = Widen(SetupCore::JsonString(ReadText(Join(p.EngineRoot, L"Engine\\Binaries\\Win64\\UE4Editor.modules")), "BuildId"));
    }
    const std::wstring wanted = ThePayload.Value("engine_build");
    if (!p.EngineBuild.empty() && !wanted.empty()) { p.EngineMatch = SamePath(p.EngineBuild, wanted) ? 1 : -1; }
    const std::wstring uplugin = Join(p.PluginDir, PluginFileName);
    p.HasRecord = FileExists(Join(p.PluginDir, RecordName));
    if (FileExists(uplugin))
    {
        p.Present = true;
        p.PresentVersion = Widen(SetupCore::JsonString(ReadText(uplugin), "VersionName"));
    }
    // Another copy of the plugin (an older zip in another folder, or the engine's): UE would load only one of them.
    std::vector<std::wstring> copies;
    FindNamed(Join(p.Dir, L"Plugins"), PluginFileName, 3, copies);
    if (!p.EngineRoot.empty())
    {
        // the engine's plugins folder is big: search it once per engine
        static std::wstring searchedEngine;
        static std::vector<std::wstring> engineCopies;
        if (!SamePath(searchedEngine, p.EngineRoot))
        {
            searchedEngine = p.EngineRoot;
            engineCopies.clear();
            FindNamed(Join(p.EngineRoot, L"Engine\\Plugins"), PluginFileName, 3, engineCopies);
        }
        copies.insert(copies.end(), engineCopies.begin(), engineCopies.end());
    }
    for (const auto& c : copies)
    {
        if (!SamePath(Parent(c), p.PluginDir)) { p.OtherCopies.push_back(Parent(c)); }
    }
    if (!p.OtherCopies.empty())
    {
        p.Status = L"Another copy of the plugin is in " + p.OtherCopies.front() + L": remove it first (the editor would load only one of them).";
        p.StatusLevel = Level::Error;
        return p;
    }
    p.Valid = true;
    const std::wstring there = p.Present ? (p.PresentVersion.empty() ? L" Replaces the plugin there now." : L" Replaces " + p.PresentVersion + L" there now.")
                                         : std::wstring{};
    if (!p.IsEnd)
    {
        p.Status = L"This doesn't look like an End (FF7 Rebirth) project. The plugin is made for one." + there;
        p.StatusLevel = Level::Warn;
    }
    else if (p.EngineMatch == 1)
    {
        p.Status = L"Engine build matches the plugin's. Installs into Plugins\\" + std::wstring(PluginFolderName) + L"." + there;
        p.StatusLevel = Level::Ok;
    }
    else if (p.EngineMatch == -1)
    {
        p.Status = L"Your engine's build differs from the plugin's: the editor will offer to rebuild the plugin (needs Visual Studio 2019)." + there;
        p.StatusLevel = Level::Warn;
    }
    else
    {
        p.Status = L"Couldn't find this project's engine. If the editor says the plugin is missing, let it rebuild." + there;
        p.StatusLevel = Level::Warn;
    }
    return p;
}

void AddProjectsIn(const std::wstring& dir, std::vector<std::wstring>& out)
{
    const std::wstring end = Join(dir, L"End.uproject");
    if (FileExists(end)) { AddUnique(out, end); }
}

void AddRecentProjects(const std::wstring& configDir, std::vector<std::wstring>& out)
{
    for (const wchar_t* sub : {L"Windows\\EditorSettings.ini", L"WindowsEditor\\EditorSettings.ini"})
    {
        for (const auto& recent : SetupCore::RecentProjects(ReadText(Join(configDir, sub))))
        {
            const std::wstring path = CleanPath(Widen(recent));
            if (path.size() > 2 && path[1] == L':' && FileExists(path) && LooksLikeEndProject(ReadText(path, 4u << 20), path)) { AddUnique(out, path); }
        }
    }
}

std::vector<std::wstring> FindProjects()
{
    std::vector<std::wstring> out;
    // UE's recently opened projects: installed engines keep them in LocalAppData, source-built ones in the engine.
    for (const auto& version : SubDirs(Join(KnownFolder(FOLDERID_LocalAppData), L"UnrealEngine"))) { AddRecentProjects(Join(version, L"Saved\\Config"), out); }
    for (const auto& engine : RegStrings(HKEY_CURRENT_USER, L"SOFTWARE\\Epic Games\\Unreal Engine\\Builds"))
    {
        if (!engine.empty()) { AddRecentProjects(Join(CleanPath(engine), L"Engine\\Saved\\Config"), out); }
    }
    AddProjectsIn(L"C:\\FF7R2UProj", out);
    // Two levels under each fixed drive, and the usual places in the user's folder.
    const std::set<std::wstring> skip = {L"windows", L"program files", L"program files (x86)", L"programdata", L"$recycle.bin", L"system volume information",
                                         L"recovery", L"perflogs", L"msocache", L"users", L"$windows.~ws", L"$windows.~bt", L"windows.old"};
    const DWORD drives = GetLogicalDrives();
    for (int d = 2; d < 26; ++d)
    {
        if (!(drives & (1u << d))) { continue; }
        const std::wstring root = std::wstring(1, static_cast<wchar_t>(L'A' + d)) + L":\\";
        if (GetDriveTypeW(root.c_str()) != DRIVE_FIXED) { continue; }
        for (const auto& level1 : SubDirs(root))
        {
            if (skip.count(Lower(FileName(level1)))) { continue; }
            AddProjectsIn(level1, out);
            for (const auto& level2 : SubDirs(level1)) { AddProjectsIn(level2, out); }
        }
    }
    const std::wstring profile = KnownFolder(FOLDERID_Profile);
    for (const std::wstring& base : {profile, KnownFolder(FOLDERID_Documents), Join(KnownFolder(FOLDERID_Documents), L"Unreal Projects"),
                                     KnownFolder(FOLDERID_Desktop), KnownFolder(FOLDERID_Downloads)})
    {
        if (base.empty()) { continue; }
        for (const auto& level1 : SubDirs(base))
        {
            AddProjectsIn(level1, out);
            for (const auto& level2 : SubDirs(level1)) { AddProjectsIn(level2, out); }
        }
    }
    return out;
}

// ---------------------------------------------------------------- log

struct Logger
{
    std::wstring Text;
    size_t Saved = 0; // how much of Text the log files already have
    HWND Edit = nullptr;

    void Line(const std::wstring& line)
    {
        Text += line + L"\r\n";
        if (Edit)
        {
            const int length = GetWindowTextLengthW(Edit);
            SendMessageW(Edit, EM_SETSEL, length, length);
            SendMessageW(Edit, EM_REPLACESEL, FALSE, reinterpret_cast<LPARAM>((line + L"\r\n").c_str()));
            UpdateWindow(Edit);
        }
    }

    // Appends what's new since the last save to CreateACharacterSystem-Setup.log in each folder (and %TEMP%).
    void Save(std::vector<std::wstring> folders)
    {
        const std::string fresh = Narrow(Text.substr(std::min(Saved, Text.size())));
        Saved = Text.size();
        if (fresh.empty()) { return; }
        folders.push_back(TempDir());
        std::vector<std::wstring> done;
        for (const auto& folder : folders)
        {
            if (folder.empty() || !DirExists(folder)) { continue; }
            bool seen = false;
            for (const auto& d : done) { seen = seen || SamePath(d, folder); }
            if (seen) { continue; }
            done.push_back(folder);
            const std::wstring path = Join(folder, LogName);
            HANDLE file = CreateFileW(path.c_str(), FILE_APPEND_DATA, FILE_SHARE_READ, nullptr, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
            if (file == INVALID_HANDLE_VALUE) { continue; }
            LARGE_INTEGER size{};
            DWORD wrote = 0;
            if (GetFileSizeEx(file, &size) && size.QuadPart == 0) { WriteFile(file, "\xEF\xBB\xBF", 3, &wrote, nullptr); }
            WriteFile(file, fresh.data(), static_cast<DWORD>(fresh.size()), &wrote, nullptr);
            WriteFile(file, "\r\n", 2, &wrote, nullptr);
            CloseHandle(file);
        }
    }
};

Logger Log;

// ---------------------------------------------------------------- install / uninstall

struct Part
{
    const char* Component;      // "game" or "plugin"
    std::wstring Name;          // "Game mod", "Editor plugin"
    std::wstring Target;        // the folder the component's files go in
    std::wstring BackupRoot;    // moved-aside files: <BackupRoot>\<stamp>\... (same drive as Target)
};

struct Result
{
    int Installed = 0, Unchanged = 0, Kept = 0, BackedUp = 0, Removed = 0, Failed = 0;
    bool InUseError = false;
    std::wstring BackupFolder; // set when something was moved there
};

std::wstring BackupPath(const Part& part, const std::wstring& stamp, const std::wstring& rel) { return Join(Join(part.BackupRoot, stamp), rel); }

// Moves the file at <target>\rel into the backup folder. Renaming works even on a DLL the game has loaded;
// across drives it copies, then deletes the original. `moved` says whether the original is gone.
bool BackUp(const Part& part, const std::wstring& stamp, const std::wstring& rel, Result& result, bool& moved)
{
    moved = false;
    const std::wstring from = Join(part.Target, rel);
    const std::wstring to = BackupPath(part, stamp, rel);
    if (!MakeDirs(Parent(to)))
    {
        Log.Line(L"  ! can't make the backup folder " + Parent(to) + L": " + ErrorText(GetLastError()));
        return false;
    }
    if (MoveFileExW(from.c_str(), to.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) { moved = true; }
    else
    {
        const DWORD error = GetLastError();
        if (!CopyFileW(from.c_str(), to.c_str(), FALSE))
        {
            Log.Line(L"  ! can't back up " + rel + L": " + ErrorText(error));
            return false;
        }
        SetFileAttributesW(from.c_str(), FILE_ATTRIBUTE_NORMAL);
        moved = DeleteFileW(from.c_str()) != FALSE;
    }
    ++result.BackedUp;
    result.BackupFolder = Join(part.BackupRoot, stamp);
    return true;
}

// Puts a backed-up file back where it was (after a failed replace).
void Restore(const Part& part, const std::wstring& stamp, const std::wstring& rel)
{
    const std::wstring dest = Join(part.Target, rel);
    if (MoveFileExW(BackupPath(part, stamp, rel).c_str(), dest.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_COPY_ALLOWED | MOVEFILE_WRITE_THROUGH))
    {
        Log.Line(L"    (the old " + rel + L" is back in place)");
    }
    else
    {
        Log.Line(L"    ! the old " + rel + L" stays in the backup folder: " + ErrorText(GetLastError()));
    }
}

bool InstallFile(const Part& part, const FileEntry& entry, const std::vector<uint8_t>& data, const std::wstring& stamp, Result& result)
{
    const std::wstring rel = Native(entry.Path);
    const std::wstring dest = Join(part.Target, rel);
    if (FileExists(dest))
    {
        if (entry.Has("keep"))
        {
            ++result.Kept;
            return true;
        }
        if (SameContent(dest, entry))
        {
            ++result.Unchanged;
            return true;
        }
    }
    if (!MakeDirs(Parent(dest)))
    {
        Log.Line(L"  ! can't make " + Parent(dest) + L": " + ErrorText(GetLastError()));
        ++result.Failed;
        return false;
    }
    const std::wstring temp = dest + L".cacs-new";
    DWORD error = 0;
    if (!WriteAll(temp, data.data(), data.size(), error))
    {
        Log.Line(L"  ! can't write " + rel + L": " + ErrorText(error));
        ++result.Failed;
        return false;
    }
    bool backedUp = false, moved = false;
    if (FileExists(dest))
    {
        // Never replace a file without its backup.
        if (!BackUp(part, stamp, rel, result, moved))
        {
            DeleteFileW(temp.c_str());
            ++result.Failed;
            return false;
        }
        backedUp = true;
        if (!moved) { SetFileAttributesW(dest.c_str(), FILE_ATTRIBUTE_NORMAL); } // copied, still in place: replaced below
    }
    // Antivirus or a sync client may hold the new file for a moment.
    bool placed = false;
    for (int attempt = 0; attempt < 8 && !placed; ++attempt)
    {
        placed = MoveFileExW(temp.c_str(), dest.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != FALSE;
        if (!placed)
        {
            error = GetLastError();
            if (!InUse(error)) { break; }
            Sleep(250);
        }
    }
    if (!placed)
    {
        DeleteFileW(temp.c_str());
        Log.Line(L"  ! can't replace " + rel + L": " + ErrorText(error) + (InUse(error) ? L" (close the program using it)" : L""));
        result.InUseError = result.InUseError || InUse(error);
        if (backedUp && moved) { Restore(part, stamp, rel); }
        ++result.Failed;
        return false;
    }
    if (!SameContent(dest, entry))
    {
        Log.Line(L"  ! " + rel + L" doesn't read back as written (antivirus?)");
        if (backedUp) { Restore(part, stamp, rel); }
        ++result.Failed;
        return false;
    }
    Log.Line(L"  " + rel + (backedUp ? L" (replaced; the old one is in the backup folder)" : L""));
    ++result.Installed;
    return true;
}

// Plugin files of an earlier version that this one doesn't have (old sources would break a rebuild).
std::vector<std::wstring> StalePluginFiles(const std::wstring& pluginDir)
{
    std::set<std::wstring> wanted;
    for (const FileEntry* f : FilesOf("plugin")) { wanted.insert(Lower(Widen(f->Path))); }
    std::vector<std::wstring> found, stale;
    ListFiles(Join(pluginDir, L"Source"), L"Source", found);
    std::vector<std::wstring> binaries;
    ListFiles(Join(pluginDir, L"Binaries\\Win64"), L"Binaries/Win64", binaries);
    for (const auto& b : binaries)
    {
        const std::wstring name = Lower(b.substr(b.find_last_of(L'/') + 1));
        // the module DLL and its hot-reload copies; .pdb files stay
        if (name.rfind(L"ue4editor-rebirthskelcompateditor", 0) == 0 && name.size() > 4 && name.substr(name.size() - 4) == L".dll") { found.push_back(b); }
    }
    for (const auto& f : found)
    {
        if (!wanted.count(Lower(f)))
        {
            std::wstring native = f;
            std::replace(native.begin(), native.end(), L'/', L'\\');
            stale.push_back(native);
        }
    }
    return stale;
}

void WriteRecord(const Part& part)
{
    std::string text = "Create a Character System " + ThePayload.Index.Value("version") + " (" + std::string(part.Component) + ", editor plugin " +
                       ThePayload.Index.Value("plugin_version") + ", built " + ThePayload.Index.Value("built") + ")\r\n";
    text += "Installed by " + Narrow(FileName(ThePayload.Exe)) + " on " + Narrow(Stamp()) + "\r\n";
    for (const FileEntry* f : FilesOf(part.Component)) { text += f->Path + "\r\n"; }
    DWORD error = 0;
    WriteAll(Join(part.Target, RecordName), reinterpret_cast<const uint8_t*>(text.data()), text.size(), error);
}

std::wstring Summary(const Result& r, bool uninstall)
{
    std::wstring s = L"  ";
    if (uninstall) { s += std::to_wstring(r.Removed) + L" removed"; }
    else
    {
        s += std::to_wstring(r.Installed) + L" installed, " + std::to_wstring(r.Unchanged) + L" already up to date";
        if (r.Kept) { s += L", " + std::to_wstring(r.Kept) + L" kept"; }
    }
    if (r.BackedUp) { s += L"; " + std::to_wstring(r.BackedUp) + L" moved to " + r.BackupFolder; }
    if (r.Failed) { s += L"; " + std::to_wstring(r.Failed) + L" FAILED"; }
    return s;
}

Result InstallPart(const Part& part)
{
    Result result;
    const std::wstring stamp = Stamp();
    Log.Line(part.Name + L" -> " + part.Target);
    // Unpack and check every file first, so a damaged Setup changes nothing.
    std::vector<std::pair<const FileEntry*, std::vector<uint8_t>>> files;
    for (const FileEntry* f : FilesOf(part.Component))
    {
        std::vector<uint8_t> data;
        std::wstring why;
        if (!ThePayload.Extract(*f, data, why))
        {
            Log.Line(L"  ! " + why + L": nothing installed. Download Setup again.");
            ++result.Failed;
            return result;
        }
        files.emplace_back(f, std::move(data));
    }
    if (!MakeDirs(part.Target))
    {
        Log.Line(L"  ! can't make " + part.Target + L": " + ErrorText(GetLastError()));
        ++result.Failed;
        return result;
    }
    if (std::string(part.Component) == "plugin")
    {
        for (const auto& rel : StalePluginFiles(part.Target))
        {
            bool moved = false;
            if (!BackUp(part, stamp, rel, result, moved)) { ++result.Failed; }
            else if (!moved)
            {
                Log.Line(L"  ! " + rel + L" (left from an earlier version) was copied to the backup folder but couldn't be removed");
                ++result.Failed;
            }
            else { Log.Line(L"  " + rel + L" (left from an earlier version; moved to the backup folder)"); }
        }
    }
    for (const auto& [f, data] : files) { InstallFile(part, *f, data, stamp, result); }
    WriteRecord(part);
    Log.Line(Summary(result, false));
    return result;
}

// Removes what Setup installed: unchanged files are deleted, files changed since are moved to the backup
// folder, everything else (compat JSON, logs, your own sources) stays.
Result UninstallPart(const Part& part)
{
    Result result;
    const std::wstring stamp = Stamp();
    Log.Line(L"Removing the " + Lower(part.Name) + L" from " + part.Target);
    if (!FileExists(Join(part.Target, RecordName)))
    {
        Log.Line(L"  Setup didn't install the files there (no " + std::wstring(RecordName) + L"): nothing removed.");
        return result;
    }
    std::set<std::wstring> dirs;
    for (const FileEntry* f : FilesOf(part.Component))
    {
        const std::wstring rel = Native(f->Path);
        const std::wstring path = Join(part.Target, rel);
        for (std::wstring d = Parent(rel); !d.empty(); d = Parent(d)) { dirs.insert(d); }
        if (!FileExists(path)) { continue; }
        if (!SameContent(path, *f))
        {
            bool moved = false;
            if (BackUp(part, stamp, rel, result, moved) && moved) { Log.Line(L"  " + rel + L" was changed since Setup installed it: moved to the backup folder"); }
            else
            {
                Log.Line(L"  ! " + rel + L" was changed since Setup installed it and couldn't be moved: left in place");
                ++result.Failed;
            }
            continue;
        }
        SetFileAttributesW(path.c_str(), FILE_ATTRIBUTE_NORMAL);
        if (DeleteFileW(path.c_str()))
        {
            ++result.Removed;
            continue;
        }
        const DWORD error = GetLastError();
        Log.Line(L"  ! can't remove " + rel + L": " + ErrorText(error));
        result.InUseError = result.InUseError || InUse(error);
        ++result.Failed;
    }
    if (!result.Failed) { DeleteFileW(Join(part.Target, RecordName).c_str()); }
    // Empty folders only (RemoveDirectory fails on others), deepest first, never a link.
    std::vector<std::wstring> ordered(dirs.begin(), dirs.end());
    std::sort(ordered.begin(), ordered.end(), [](const std::wstring& a, const std::wstring& b) { return a.size() > b.size(); });
    for (const auto& d : ordered)
    {
        const std::wstring path = Join(part.Target, d);
        if (!IsReparsePoint(path)) { RemoveDirectoryW(path.c_str()); }
    }
    const bool gone = !IsReparsePoint(part.Target) && RemoveDirectoryW(part.Target.c_str()) != 0;
    Log.Line(Summary(result, true) + (gone ? L"; folder removed" : L"; files Setup didn't install stay"));
    return result;
}

// ---------------------------------------------------------------- the window

struct Options
{
    bool Silent = false, Install = false, Uninstall = false, NoGame = false, NoPlugin = false;
    std::wstring Game, Project;
};

Options Opt;
GameInfo Game;
ProjectInfo Project;
HFONT TitleFont = nullptr;
bool Busy = false;
bool Scanned = false;

COLORREF ColorOf(Level level)
{
    switch (level)
    {
    case Level::Ok: return RGB(0x1E, 0x7B, 0x34);
    case Level::Warn: return RGB(0xA8, 0x5A, 0x00);
    case Level::Error: return RGB(0xC4, 0x1E, 0x24);
    default: return GetSysColor(COLOR_GRAYTEXT);
    }
}

std::wstring ComboText(HWND dialog, int id)
{
    HWND combo = GetDlgItem(dialog, id);
    const int length = GetWindowTextLengthW(combo);
    std::wstring text(static_cast<size_t>(length) + 1, L'\0');
    GetWindowTextW(combo, text.data(), length + 1);
    text.resize(static_cast<size_t>(length));
    return text;
}

bool Ticked(HWND dialog, int id) { return IsDlgButtonChecked(dialog, id) == BST_CHECKED; }

void UpdateButtons(HWND dialog)
{
    const bool game = Ticked(dialog, IDC_GAME_CHECK), plugin = Ticked(dialog, IDC_PLUGIN_CHECK);
    const bool ready = Scanned && !Busy;
    EnableWindow(GetDlgItem(dialog, IDOK), ready && ((game && Game.Valid) || (plugin && Project.Valid)));
    EnableWindow(GetDlgItem(dialog, IDC_UNINSTALL), ready && ((game && Game.Valid && Game.HasRecord) || (plugin && Project.Valid && Project.HasRecord)));
    for (int id : {IDC_GAME_CHECK, IDC_GAME_PATH, IDC_GAME_BROWSE, IDC_PLUGIN_CHECK, IDC_PROJECT_PATH, IDC_PROJECT_BROWSE, IDC_README})
    {
        EnableWindow(GetDlgItem(dialog, id), ready);
    }
    EnableWindow(GetDlgItem(dialog, IDCANCEL), !Busy);
}

// Re-reads both paths; a part whose path just became valid gets ticked (as Browse does).
void Refresh(HWND dialog)
{
    const bool gameWas = Game.Valid, projectWas = Project.Valid;
    Game = InspectGame(ComboText(dialog, IDC_GAME_PATH));
    Project = InspectProject(ComboText(dialog, IDC_PROJECT_PATH));
    if (Game.Valid && !gameWas && !Opt.NoGame) { CheckDlgButton(dialog, IDC_GAME_CHECK, BST_CHECKED); }
    if (Project.Valid && !projectWas && !Opt.NoPlugin) { CheckDlgButton(dialog, IDC_PLUGIN_CHECK, BST_CHECKED); }
    SetDlgItemTextW(dialog, IDC_GAME_STATUS, Game.Status.c_str());
    SetDlgItemTextW(dialog, IDC_PROJECT_STATUS, Project.Status.c_str());
    InvalidateRect(GetDlgItem(dialog, IDC_GAME_STATUS), nullptr, TRUE);
    InvalidateRect(GetDlgItem(dialog, IDC_PROJECT_STATUS), nullptr, TRUE);
    UpdateButtons(dialog);
}

void FillCombo(HWND dialog, int id, const std::vector<std::wstring>& items, const std::wstring& preferred)
{
    HWND combo = GetDlgItem(dialog, id);
    SendMessageW(combo, CB_RESETCONTENT, 0, 0);
    for (const auto& item : items) { SendMessageW(combo, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(item.c_str())); }
    const std::wstring text = !preferred.empty() ? preferred : (items.empty() ? std::wstring{} : items.front());
    SetWindowTextW(combo, text.c_str());
}

template <typename T>
struct ComPtr
{
    T* P = nullptr;
    ~ComPtr()
    {
        if (P) { P->Release(); }
    }
    T** operator&() { return &P; }
    T* operator->() const { return P; }
    explicit operator bool() const { return P != nullptr; }
};

std::wstring Pick(HWND owner, bool folder, const std::wstring& start)
{
    ComPtr<IFileOpenDialog> dialog;
    if (FAILED(CoCreateInstance(CLSID_FileOpenDialog, nullptr, CLSCTX_INPROC_SERVER, IID_IFileOpenDialog, reinterpret_cast<void**>(&dialog)))) { return {}; }
    FILEOPENDIALOGOPTIONS options = 0;
    dialog->GetOptions(&options);
    dialog->SetOptions(options | FOS_FORCEFILESYSTEM | FOS_PATHMUSTEXIST | (folder ? FOS_PICKFOLDERS : FOS_FILEMUSTEXIST));
    if (folder) { dialog->SetTitle(L"Pick the FINAL FANTASY VII REBIRTH folder"); }
    else
    {
        static const COMDLG_FILTERSPEC types[] = {{L"Unreal project (*.uproject)", L"*.uproject"}};
        dialog->SetFileTypes(1, types);
        dialog->SetTitle(L"Pick your End project (End.uproject)");
    }
    std::wstring from = start;
    while (!from.empty() && !DirExists(from)) { from = Parent(from); }
    if (!from.empty())
    {
        ComPtr<IShellItem> item;
        if (SUCCEEDED(SHCreateItemFromParsingName(from.c_str(), nullptr, IID_IShellItem, reinterpret_cast<void**>(&item)))) { dialog->SetFolder(item.P); }
    }
    if (FAILED(dialog->Show(owner))) { return {}; }
    ComPtr<IShellItem> result;
    PWSTR path = nullptr;
    std::wstring out;
    if (SUCCEEDED(dialog->GetResult(&result)) && SUCCEEDED(result->GetDisplayName(SIGDN_FILESYSPATH, &path)) && path) { out = path; }
    if (path) { CoTaskMemFree(path); }
    return out;
}

// One command-line argument, quoted the way CommandLineToArgvW reads it back (backslashes before the closing quote doubled).
std::wstring Quote(const std::wstring& arg)
{
    size_t slashes = 0;
    while (slashes < arg.size() && arg[arg.size() - 1 - slashes] == L'\\') { ++slashes; }
    return L"\"" + arg + std::wstring(slashes, L'\\') + L"\"";
}

// Starts Setup again as administrator with the same choices (it then runs them by itself); true if it started.
bool RestartElevated(HWND dialog, bool game, bool plugin, bool uninstall)
{
    std::wstring args;
    args += game ? L"/game:" + Quote(Game.Root) + L" " : L"/nogame ";
    args += plugin ? L"/project:" + Quote(Project.File) + L" " : L"/noplugin ";
    args += uninstall ? L"/uninstall" : L"/install";
    SHELLEXECUTEINFOW info{};
    info.cbSize = sizeof(info);
    info.hwnd = dialog;
    info.lpVerb = L"runas";
    info.lpFile = ThePayload.Exe.c_str();
    info.lpParameters = args.c_str();
    info.nShow = SW_SHOWNORMAL;
    return ShellExecuteExW(&info) != FALSE;
}

std::wstring Readme()
{
    const std::string wanted = ThePayload.Index.Value("readme");
    for (const auto& f : ThePayload.Index.Files)
    {
        if (f.Component + "/" + f.Path == wanted)
        {
            std::vector<uint8_t> data;
            std::wstring why;
            if (!ThePayload.Extract(f, data, why)) { return {}; }
            const std::wstring path = Join(TempDir(), L"Create a Character System " + ThePayload.Value("version") + L" - README.txt");
            DWORD error = 0;
            return WriteAll(path, data.data(), data.size(), error) ? path : std::wstring{};
        }
    }
    return {};
}

// Runs the chosen parts; returns 0 (all done), 1 (something failed) or 2 (nothing to do).
int Run(HWND dialog, bool game, bool plugin, bool uninstall)
{
    std::vector<std::wstring> logFolders;
    struct SaveLog
    {
        std::vector<std::wstring>& Folders;
        ~SaveLog() { Log.Save(Folders); }
    } saveLog{logFolders};

    std::vector<Part> parts;
    if (game && Game.Valid) { parts.push_back(Part{"game", L"Game mod", Game.ModDir, Join(Game.ModDir, L"Backups")}); }
    if (plugin && Project.Valid) { parts.push_back(Part{"plugin", L"Editor plugin", Project.PluginDir, Join(Project.Dir, PluginBackups)}); }
    if (parts.empty()) { return 2; }

    // Administrator rights, only when a folder needs them.
    for (const auto& part : parts)
    {
        DWORD error = 0;
        if (CanWrite(part.Target, error) || error != ERROR_ACCESS_DENIED) { continue; }
        if (Elevated() || !dialog)
        {
            Log.Line(L"! Setup can't write to " + part.Target + L": " + ErrorText(error));
            return 1;
        }
        if (MessageBoxW(dialog, (L"Setup needs administrator rights to write to\n" + part.Target + L"\n\nStart Setup again as administrator?").c_str(), AppTitle,
                        MB_YESNO | MB_ICONQUESTION) == IDYES &&
            RestartElevated(dialog, game && Game.Valid, plugin && Project.Valid, uninstall))
        {
            Log.Line(L"Setup started again as administrator.");
            EndDialog(dialog, 0);
            return 0;
        }
        Log.Line(L"! Setup can't write to " + part.Target + L" without administrator rights.");
        return 1;
    }

    const bool gameRunning = ProcessRunning(L"ff7rebirth");
    const bool editorRunning = ProcessRunning(L"UE4Editor");
    if (uninstall && ((game && gameRunning) || (plugin && editorRunning)))
    {
        const std::wstring what = (game && gameRunning) ? L"FINAL FANTASY VII REBIRTH" : L"the Unreal editor";
        Log.Line(L"! Close " + what + L" before uninstalling.");
        if (dialog) { MessageBoxW(dialog, (L"Close " + what + L" first, then click Uninstall again.").c_str(), AppTitle, MB_OK | MB_ICONINFORMATION); }
        return 1;
    }

    Log.Line(std::wstring(uninstall ? L"Uninstalling" : L"Installing") + L" Create a Character System " + ThePayload.Value("version") + L" (" + Stamp() + L")");
    int failed = 0;
    bool inUse = false;
    std::vector<std::wstring> backups;
    for (const auto& part : parts)
    {
        const Result r = uninstall ? UninstallPart(part) : InstallPart(part);
        failed += r.Failed;
        inUse = inUse || r.InUseError;
        if (!r.BackupFolder.empty()) { backups.push_back(r.BackupFolder); }
        if (std::string(part.Component) == "game" && DirExists(part.Target)) { logFolders.push_back(part.Target); }
    }
    if (!uninstall && !failed)
    {
        if (game && Game.Valid && gameRunning) { Log.Line(L"The game is running: it loads the new mod the next time it starts."); }
        if (plugin && Project.Valid && editorRunning) { Log.Line(L"An Unreal editor is running: restart it to load the new plugin."); }
    }
    if (inUse) { Log.Line(L"A file was in use: close the game and the Unreal editor, then run Setup again."); }
    Log.Line(failed ? L"Finished with problems (see above)." : L"Done.");

    if (dialog)
    {
        std::wstring message;
        if (failed) { message = L"Some files couldn't be " + std::wstring(uninstall ? L"removed" : L"installed") + L". The list in Setup says what went wrong."; }
        else if (uninstall) { message = L"Create a Character System is removed. Files Setup didn't install (your compat JSON files, logs) stay where they are."; }
        else
        {
            message = L"Create a Character System " + ThePayload.Value("version") + L" is installed.\n";
            if (game && Game.Valid)
            {
                message += L"\nGame: start FINAL FANTASY VII REBIRTH. UE4SS loads the mod; its log is\n" + Join(Game.ModDir, L"RebirthSkelCompat.log") + L"\n";
                if (Game.Ue4ss == 0) { message += L"(Install UE4SS 3.0.1 first: the mod doesn't run without it.)\n"; }
            }
            if (plugin && Project.Valid) { message += L"\nEditor: open " + FileName(Project.File) + L"; the plugin is in Plugins\\" + PluginFolderName + L".\n"; }
            message += L"\nThe README explains how to make a character.";
        }
        if (!backups.empty())
        {
            message += L"\n\nFiles Setup replaced or moved aside are in:";
            for (const auto& b : backups) { message += L"\n" + b; }
        }
        MessageBoxW(dialog, message.c_str(), AppTitle, MB_OK | (failed ? MB_ICONWARNING : MB_ICONINFORMATION));
    }
    return failed ? 1 : 0;
}

void MakeTitleFont(HWND dialog)
{
    if (TitleFont)
    {
        DeleteObject(TitleFont);
        TitleFont = nullptr;
    }
    HFONT base = reinterpret_cast<HFONT>(SendMessageW(dialog, WM_GETFONT, 0, 0));
    LOGFONTW font{};
    if (!base || !GetObjectW(base, sizeof(font), &font)) { return; }
    font.lfHeight = font.lfHeight * 16 / 10;
    font.lfWeight = FW_SEMIBOLD;
    TitleFont = CreateFontIndirectW(&font);
    if (TitleFont) { SendDlgItemMessageW(dialog, IDC_TITLE, WM_SETFONT, reinterpret_cast<WPARAM>(TitleFont), TRUE); }
}

const UINT ScanMessage = WM_APP + 2;
const UINT FontMessage = WM_APP + 1;

void StartAction(HWND dialog, bool uninstall)
{
    KillTimer(dialog, 1);
    Refresh(dialog);
    const bool wantGame = Ticked(dialog, IDC_GAME_CHECK), wantPlugin = Ticked(dialog, IDC_PLUGIN_CHECK);
    // A ticked part that can't be done: say so instead of skipping it.
    std::wstring problems;
    if (wantGame && !Game.Valid) { problems += L"Game mod: " + Game.Status + L"\n"; }
    if (wantPlugin && !Project.Valid) { problems += L"Editor plugin: " + Project.Status + L"\n"; }
    if (!problems.empty())
    {
        MessageBoxW(dialog, (problems + L"\nFix the path or untick that part.").c_str(), AppTitle, MB_OK | MB_ICONWARNING);
        return;
    }
    bool game = wantGame && Game.Valid, plugin = wantPlugin && Project.Valid;
    if (uninstall)
    {
        // Setup only removes what it installed (its install record is there).
        if (game && !Game.HasRecord)
        {
            Log.Line(L"Game mod: Setup didn't install it in this game; left alone.");
            game = false;
        }
        if (plugin && !Project.HasRecord)
        {
            Log.Line(L"Editor plugin: Setup didn't install it in this project; left alone.");
            plugin = false;
        }
    }
    if (!game && !plugin) { return; }
    if (uninstall)
    {
        std::wstring what = game ? L"the game mod from\n" + Game.ModDir + L"\n" : L"";
        if (plugin) { what += std::wstring(game ? L"and " : L"") + L"the editor plugin from\n" + Project.PluginDir + L"\n"; }
        if (MessageBoxW(dialog, (L"Remove " + what + L"\nOnly files Setup installed and that are unchanged are deleted; changed ones go to the backup folder, and your compat JSON files and logs stay.").c_str(),
                        AppTitle, MB_OKCANCEL | MB_ICONQUESTION) != IDOK)
        {
            return;
        }
    }
    Busy = true;
    UpdateButtons(dialog);
    HCURSOR old = SetCursor(LoadCursorW(nullptr, IDC_WAIT));
    Log.Line(L"");
    Run(dialog, game, plugin, uninstall);
    SetCursor(old);
    Busy = false;
    if (IsWindow(dialog)) { Refresh(dialog); }
}

INT_PTR CALLBACK DialogProc(HWND dialog, UINT message, WPARAM wParam, LPARAM lParam)
{
    switch (message)
    {
    case WM_INITDIALOG:
    {
        HICON icon = static_cast<HICON>(LoadImageW(GetModuleHandleW(nullptr), MAKEINTRESOURCEW(IDI_APP), IMAGE_ICON, 0, 0, LR_DEFAULTSIZE | LR_SHARED));
        HICON smallIcon = static_cast<HICON>(LoadImageW(GetModuleHandleW(nullptr), MAKEINTRESOURCEW(IDI_APP), IMAGE_ICON, GetSystemMetrics(SM_CXSMICON),
                                                        GetSystemMetrics(SM_CYSMICON), LR_SHARED));
        SendMessageW(dialog, WM_SETICON, ICON_BIG, reinterpret_cast<LPARAM>(icon));
        SendMessageW(dialog, WM_SETICON, ICON_SMALL, reinterpret_cast<LPARAM>(smallIcon));
        MakeTitleFont(dialog);
        Log.Edit = GetDlgItem(dialog, IDC_LOG);
        SetDlgItemTextW(dialog, IDC_TITLE, L"Create a Character System");
        const std::wstring subtitle = L"Version " + ThePayload.Value("version") + L":  the game mod (UE4SS 3.0.1 " + Widen(Ue4ssTag()) +
                                      L") to play characters made with it, and the editor plugin " + ThePayload.Value("plugin_version") +
                                      L" to make them in your End project.";
        SetDlgItemTextW(dialog, IDC_SUBTITLE, subtitle.c_str());
        SetWindowTextW(dialog, (std::wstring(AppTitle) + L" " + ThePayload.Value("version")).c_str());
        SetDlgItemTextW(dialog, IDC_GAME_STATUS, L"Looking for the game...");
        SetDlgItemTextW(dialog, IDC_PROJECT_STATUS, L"Looking for your End project...");
        UpdateButtons(dialog);
        PostMessageW(dialog, ScanMessage, 0, 0); // after the window shows
        return TRUE;
    }
    case ScanMessage:
    {
        RedrawWindow(dialog, nullptr, nullptr, RDW_INVALIDATE | RDW_ALLCHILDREN | RDW_UPDATENOW);
        HCURSOR old = SetCursor(LoadCursorW(nullptr, IDC_WAIT));
        const auto games = FindGames();
        const auto projects = Opt.Project.empty() ? FindProjects() : std::vector<std::wstring>{};
        SetCursor(old);
        FillCombo(dialog, IDC_GAME_PATH, games, Opt.Game);
        FillCombo(dialog, IDC_PROJECT_PATH, projects, Opt.Project);
        Scanned = true;
        Refresh(dialog); // ticks the parts it found
        if (Opt.NoGame) { CheckDlgButton(dialog, IDC_GAME_CHECK, BST_UNCHECKED); }
        if (Opt.NoPlugin) { CheckDlgButton(dialog, IDC_PLUGIN_CHECK, BST_UNCHECKED); }
        UpdateButtons(dialog);
        Log.Line(L"Setup found " + std::to_wstring(games.size()) + L" game folder(s)" +
                 (Opt.Project.empty() ? L" and " + std::to_wstring(projects.size()) + L" End project(s)." : std::wstring(L".")));
        Log.Line(L"Game mod: " + std::to_wstring(ThePayload.Index.Count("game")) + L" files. Editor plugin: " + std::to_wstring(ThePayload.Index.Count("plugin")) +
                 L" files (built for engine " + ThePayload.Value("engine_build") + L").");
        Log.Line(L"Every file Setup replaces is moved to a backup folder first. Your compat JSON files are never touched.");
        if (Elevated()) { Log.Line(L"(Running as administrator.)"); }
        SetFocus(GetDlgItem(dialog, IsWindowEnabled(GetDlgItem(dialog, IDOK)) ? IDOK : IDC_GAME_PATH));
        if (Opt.Uninstall || Opt.Install) { StartAction(dialog, Opt.Uninstall); }
        return TRUE;
    }
    case WM_DPICHANGED:
        PostMessageW(dialog, FontMessage, 0, 0);
        return FALSE;
    case FontMessage:
        MakeTitleFont(dialog);
        return TRUE;
    case WM_CTLCOLORSTATIC:
    {
        const int id = GetDlgCtrlID(reinterpret_cast<HWND>(lParam));
        if (id != IDC_GAME_STATUS && id != IDC_PROJECT_STATUS) { break; }
        HDC dc = reinterpret_cast<HDC>(wParam);
        const Level level = !Scanned ? Level::Info : id == IDC_GAME_STATUS ? Game.StatusLevel : Project.StatusLevel;
        SetTextColor(dc, ColorOf(level));
        SetBkMode(dc, TRANSPARENT);
        return reinterpret_cast<INT_PTR>(GetSysColorBrush(COLOR_3DFACE));
    }
    case WM_TIMER:
        if (wParam == 1)
        {
            KillTimer(dialog, 1);
            Refresh(dialog);
        }
        return TRUE;
    case WM_COMMAND:
    {
        const int id = LOWORD(wParam);
        const int code = HIWORD(wParam);
        if ((id == IDC_GAME_PATH || id == IDC_PROJECT_PATH) && (code == CBN_EDITCHANGE || code == CBN_SELCHANGE))
        {
            if (code == CBN_SELCHANGE)
            {
                // the edit part shows the picked item only after this notification
                HWND combo = GetDlgItem(dialog, id);
                const LRESULT pick = SendMessageW(combo, CB_GETCURSEL, 0, 0);
                if (pick != CB_ERR)
                {
                    const LRESULT length = SendMessageW(combo, CB_GETLBTEXTLEN, static_cast<WPARAM>(pick), 0);
                    std::wstring text(static_cast<size_t>(length > 0 ? length : 0) + 1, L'\0');
                    SendMessageW(combo, CB_GETLBTEXT, static_cast<WPARAM>(pick), reinterpret_cast<LPARAM>(text.data()));
                    text.resize(wcsnlen(text.c_str(), text.size()));
                    SetWindowTextW(combo, text.c_str());
                }
            }
            SetTimer(dialog, 1, code == CBN_SELCHANGE ? 10 : 450, nullptr);
            return TRUE;
        }
        switch (id)
        {
        case IDC_GAME_CHECK:
        case IDC_PLUGIN_CHECK:
            UpdateButtons(dialog);
            return TRUE;
        case IDC_GAME_BROWSE:
        {
            const std::wstring picked = Pick(dialog, true, Game.Valid ? Game.Root : ComboText(dialog, IDC_GAME_PATH));
            if (!picked.empty())
            {
                const std::wstring root = GameRootOf(picked);
                SetDlgItemTextW(dialog, IDC_GAME_PATH, (root.empty() ? picked : root).c_str());
                Refresh(dialog);
                if (Game.Valid) { CheckDlgButton(dialog, IDC_GAME_CHECK, BST_CHECKED); }
                UpdateButtons(dialog);
            }
            return TRUE;
        }
        case IDC_PROJECT_BROWSE:
        {
            const std::wstring picked = Pick(dialog, false, Project.Valid ? Project.Dir : ComboText(dialog, IDC_PROJECT_PATH));
            if (!picked.empty())
            {
                SetDlgItemTextW(dialog, IDC_PROJECT_PATH, picked.c_str());
                Refresh(dialog);
                if (Project.Valid) { CheckDlgButton(dialog, IDC_PLUGIN_CHECK, BST_CHECKED); }
                UpdateButtons(dialog);
            }
            return TRUE;
        }
        case IDC_README:
        {
            const std::wstring path = Readme();
            if (path.empty() || reinterpret_cast<INT_PTR>(ShellExecuteW(dialog, L"open", path.c_str(), nullptr, nullptr, SW_SHOWNORMAL)) <= 32)
            {
                MessageBoxW(dialog, L"Setup couldn't open its README.", AppTitle, MB_OK | MB_ICONWARNING);
            }
            return TRUE;
        }
        case IDOK:
        case IDC_UNINSTALL:
            if (Scanned && !Busy) { StartAction(dialog, id == IDC_UNINSTALL); }
            return TRUE;
        case IDCANCEL:
            if (!Busy) { EndDialog(dialog, 0); }
            return TRUE;
        }
        break;
    }
    case WM_CLOSE:
        if (!Busy) { EndDialog(dialog, 0); }
        return TRUE;
    }
    return FALSE;
}

void ParseCommandLine()
{
    int count = 0;
    LPWSTR* args = CommandLineToArgvW(GetCommandLineW(), &count);
    if (!args) { return; }
    for (int i = 1; i < count; ++i)
    {
        const std::wstring arg = args[i];
        const std::wstring lower = Lower(arg);
        auto value = [&](const wchar_t* prefix) { return Trim(arg.substr(wcslen(prefix))); };
        if (lower == L"/s" || lower == L"-s" || lower == L"/silent") { Opt.Silent = true; }
        else if (lower == L"/install") { Opt.Install = true; }
        else if (lower == L"/uninstall") { Opt.Uninstall = true; }
        else if (lower == L"/nogame") { Opt.NoGame = true; }
        else if (lower == L"/noplugin") { Opt.NoPlugin = true; }
        else if (lower.rfind(L"/game:", 0) == 0) { Opt.Game = value(L"/game:"); }
        else if (lower.rfind(L"/project:", 0) == 0) { Opt.Project = value(L"/project:"); }
    }
    LocalFree(args);
}

int RunSilent()
{
    int problems = 0;
    // A silent uninstall only touches the parts it is given.
    const bool findGame = !Opt.NoGame && (!Opt.Uninstall || !Opt.Game.empty());
    const bool findProject = !Opt.NoPlugin && (!Opt.Uninstall || !Opt.Project.empty());
    if (findGame)
    {
        const auto games = Opt.Game.empty() ? FindGames() : std::vector<std::wstring>{Opt.Game};
        Game = InspectGame(games.empty() ? std::wstring{} : games.front());
        if (!games.empty()) { Log.Line(L"Game: " + games.front() + L" - " + Game.Status); }
        if (!Opt.Game.empty() && !Game.Valid) { ++problems; }
    }
    if (findProject)
    {
        const auto projects = Opt.Project.empty() ? FindProjects() : std::vector<std::wstring>{Opt.Project};
        Project = InspectProject(projects.empty() ? std::wstring{} : projects.front());
        if (!projects.empty()) { Log.Line(L"Project: " + projects.front() + L" - " + Project.Status); }
        if (!Opt.Project.empty() && !Project.Valid) { ++problems; }
    }
    if (Opt.Uninstall)
    {
        if (Game.Valid && !Game.HasRecord) { Log.Line(L"Game mod: Setup didn't install it there; left alone."); }
        if (Project.Valid && !Project.HasRecord) { Log.Line(L"Editor plugin: Setup didn't install it there; left alone."); }
    }
    const bool game = Game.Valid && (!Opt.Uninstall || Game.HasRecord), plugin = Project.Valid && (!Opt.Uninstall || Project.HasRecord);
    int result = Run(nullptr, game, plugin, Opt.Uninstall);
    if (result == 2)
    {
        Log.Line(L"Nothing to do: no game folder or End project to work on.");
        Log.Save({});
    }
    if (problems && result != 1)
    {
        Log.Line(L"A path given on the command line isn't usable (see above).");
        Log.Save({});
        result = 1;
    }
    return result;
}

} // namespace

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE, LPWSTR, int)
{
    // Load system DLLs only from System32 (Setup usually runs from a Downloads folder).
    SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_SYSTEM32);
    CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED | COINIT_DISABLE_OLE1DDE);
    INITCOMMONCONTROLSEX controls{sizeof(controls), ICC_STANDARD_CLASSES | ICC_WIN95_CLASSES};
    InitCommonControlsEx(&controls);
    ParseCommandLine();

    std::wstring why;
    if (!ThePayload.Load(why))
    {
        if (!Opt.Silent) { MessageBoxW(nullptr, why.c_str(), AppTitle, MB_OK | MB_ICONERROR); }
        else
        {
            Log.Line(why);
            Log.Save({});
        }
        return 3;
    }
    if (Opt.Silent) { return RunSilent(); }
    DialogBoxParamW(instance, MAKEINTRESOURCEW(IDD_MAIN), nullptr, DialogProc, 0);
    if (TitleFont) { DeleteObject(TitleFont); }
    CoUninitialize();
    return 0;
}
