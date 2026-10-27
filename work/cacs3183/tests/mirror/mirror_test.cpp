// Off-target test of the game mod's TableCopies (3.16.2's in-place mirror and its restore): the mod's own code, cut out
// of RebirthSkelCompat.cpp by make_mirror_test.py, with stand-ins for the Windows and engine calls below.
#include "../../src/SkelCompatCore.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cwchar>
#include <map>
#include <memory>
#include <string>
#include <vector>

// ---- Windows stand-ins: addresses in [ReadOnlyBegin, ReadOnlyEnd) are read-only and cannot be made writable
typedef uint32_t DWORD;
typedef int64_t LONG64;
typedef size_t SIZE_T;
constexpr DWORD PAGE_READONLY = 0x02, PAGE_READWRITE = 0x04, PAGE_WRITECOPY = 0x08, PAGE_EXECUTE_READWRITE = 0x40, PAGE_EXECUTE_WRITECOPY = 0x80;
constexpr DWORD MEM_COMMIT = 0x1000, MEM_MAPPED = 0x40000, MEM_IMAGE = 0x1000000, MEM_PRIVATE = 0x20000;
struct MEMORY_BASIC_INFORMATION
{
    void* BaseAddress;
    void* AllocationBase;
    DWORD AllocationProtect;
    SIZE_T RegionSize;
    DWORD State;
    DWORD Protect;
    DWORD Type;
};
uintptr_t ReadOnlyBegin = 0, ReadOnlyEnd = 0;
int ProtectCalls = 0;
bool InReadOnly(uintptr_t a, size_t n) { return a < ReadOnlyEnd && a + n > ReadOnlyBegin; }
SIZE_T VirtualQuery(const void* at, MEMORY_BASIC_INFORMATION* info, SIZE_T)
{
    std::memset(info, 0, sizeof(*info));
    info->State = MEM_COMMIT;
    info->Protect = InReadOnly(reinterpret_cast<uintptr_t>(at), 1) ? PAGE_READONLY : PAGE_READWRITE;
    info->Type = InReadOnly(reinterpret_cast<uintptr_t>(at), 1) ? MEM_MAPPED : MEM_PRIVATE;
    return sizeof(*info);
}
bool VirtualProtect(void* at, SIZE_T size, DWORD, DWORD* old)
{
    ++ProtectCalls;
    if (InReadOnly(reinterpret_cast<uintptr_t>(at), size)) { return false; }
    *old = PAGE_READWRITE;
    return true;
}
DWORD GetLastError() { return 5; }
LONG64 InterlockedExchange64(volatile LONG64* at, LONG64 value)
{
    const LONG64 old = *at;
    *at = value;
    return old;
}

// ---- engine and mod stand-ins
std::wstring Hex(uintptr_t value)
{
    wchar_t buffer[32]{};
    swprintf(buffer, 32, L"0x%llX", static_cast<unsigned long long>(value));
    return buffer;
}
bool SafeCopy(void* destination, const void* source, size_t size)
{
    if (!source) { return false; }
    std::memcpy(destination, source, size);
    return true;
}
template <class T>
bool ReadAt(const void* base, size_t offset, T& out)
{
    return base && SafeCopy(&out, static_cast<const uint8_t*>(base) + offset, sizeof(T));
}
struct RawName
{
    uint32_t Comparison = 0;
    uint32_t Number = 0;
};
bool SameName(const RawName& a, const RawName& b) { return a.Comparison == b.Comparison && a.Number == b.Number; }
uint64_t KeyOf(const RawName& raw)
{
    uint64_t key = 0;
    std::memcpy(&key, &raw, sizeof(key));
    return key;
}
std::map<uint32_t, std::wstring> NameTexts;
std::wstring NameText(uint64_t key)
{
    const auto it = NameTexts.find(static_cast<uint32_t>(key));
    return it == NameTexts.end() ? std::wstring(L"?") : it->second;
}
namespace FMemory
{
void* Malloc(size_t size, size_t align) { return std::aligned_alloc(align, (size + align - 1) / align * align); }
void Free(void* p) { std::free(p); }
}
struct UObject
{
};
UObject TheObject;
uintptr_t TheHolder = 0;
UObject* FindDataObject(const wchar_t*) { return &TheObject; }
uintptr_t DataObjectHolder(UObject*, std::wstring& why)
{
    if (!TheHolder) { why = L"no table loaded"; }
    return TheHolder;
}
namespace LuaPump
{
bool RangeOk(uintptr_t, size_t, bool) { return true; }
}
constexpr wchar_t PlayerTablePath[] = L"/Game/DataObject/Resident/BattlePlayerParameter.BattlePlayerParameter";

struct FrozenTable
{
    uintptr_t Root = 0;
    uintptr_t Rows = 0;
    int32_t Count = 0;
    int32_t RowSize = 0;
    std::vector<uint8_t> Elements;                     // copy of the row map's elements (20 bytes each)
    std::vector<SkelCompat::Frozen::Field> Fields;
};

// A frozen array {ptr, num, max} at `at`.
bool ReadFrozenArray(uintptr_t at, uintptr_t& data, int32_t& num)
{
    int64_t value = 0;
    int32_t count = 0;
    const void* where = reinterpret_cast<const void*>(at);
    if (!ReadAt(where, 0, value) || !ReadAt(where, 8, count) || count < 0) { return false; }
    data = SkelCompat::Frozen::Resolve(at, value);
    num = count;
    return count == 0 || data != 0;
}
// (3.16.0) The table whose frozen root is at `root`.
bool OpenTableAt(uintptr_t root, FrozenTable& table, std::wstring& why)
{
    table = FrozenTable{};
    uintptr_t elements = 0, definition = 0;
    int32_t fields = 0, rows = 0;
    if (!ReadFrozenArray(root, elements, table.Count) || !ReadFrozenArray(root + 56, definition, fields) || !ReadFrozenArray(root + 72, table.Rows, rows))
    {
        why = L"table root unreadable";
        return false;
    }
    if (table.Count <= 0 || table.Count != rows || table.Count > 1000000 || fields <= 0 || fields > 1024)
    {
        why = L"the root does not look like a table (" + std::to_wstring(table.Count) + L" keys, " + std::to_wstring(rows) + L" rows, " +
              std::to_wstring(fields) + L" fields)";
        return false;
    }
    std::vector<uint8_t> defs(static_cast<size_t>(fields) * 12);
    table.Elements.resize(static_cast<size_t>(table.Count) * 20);
    if (!SafeCopy(defs.data(), reinterpret_cast<const void*>(definition), defs.size()) ||
        !SafeCopy(table.Elements.data(), reinterpret_cast<const void*>(elements), table.Elements.size()))
    {
        why = L"table unreadable";
        return false;
    }
    for (int32_t k = 0; k < fields; ++k)
    {
        RawName name{};
        int32_t code = 0;
        std::memcpy(&name, defs.data() + k * 12, sizeof(name));
        std::memcpy(&code, defs.data() + k * 12 + 8, sizeof(code));
        table.Fields.push_back(SkelCompat::Frozen::Field{NameText(KeyOf(name)), code});
    }
    if (!SkelCompat::Frozen::Layout(table.Fields, table.RowSize))
    {
        why = L"a field has an unknown type";
        return false;
    }
    table.Root = root;
    return true;
}

// Address of a row, 0 when the table has no such row.
uintptr_t TableRow(const FrozenTable& table, const RawName& key)
{
    if (key.Comparison == 0 && key.Number == 0) { return 0; }
    for (int32_t k = 0; k < table.Count; ++k)
    {
        RawName name{};
        int32_t row = -1;
        std::memcpy(&name, table.Elements.data() + k * 20, sizeof(name));
        std::memcpy(&row, table.Elements.data() + k * 20 + 8, sizeof(row));
        if (SameName(name, key)) { return row >= 0 && row < table.Count ? table.Rows + static_cast<uintptr_t>(row) * table.RowSize : 0; }
    }
    return 0;
}

// Why the last WriteTableArray failed (for the log).
std::wstring TableWriteProblem;

// Writes {pointer, num, max} at `at` (a table array): readers see the old or the new list, never a pointer past its count.
bool WriteTableArray(uintptr_t at, int64_t pointer, int32_t num, int32_t max)
{
    MEMORY_BASIC_INFORMATION info{};
    if (!VirtualQuery(reinterpret_cast<void*>(at), &info, sizeof(info)) || info.State != MEM_COMMIT)
    {
        TableWriteProblem = L"the row's memory is not committed";
        return false;
    }
    const DWORD writable = PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY;
    DWORD old = 0;
    const bool protect = (info.Protect & writable) == 0;
    if (protect && !VirtualProtect(reinterpret_cast<void*>(at), 16, PAGE_READWRITE, &old) && !VirtualProtect(reinterpret_cast<void*>(at), 16, PAGE_WRITECOPY, &old))
    {
        const DWORD error = GetLastError();
        TableWriteProblem = L"the row's memory is read-only (" + std::wstring(info.Type == MEM_MAPPED ? L"a mapped file" : info.Type == MEM_IMAGE ? L"an image" : L"private") +
                            L", protection " + Hex(info.Protect) + L", error " + std::to_wstring(error) + L")";
        return false;
    }
    int32_t oldMax = 0;
    std::memcpy(&oldMax, reinterpret_cast<const void*>(at + 12), sizeof(oldMax));
    const auto counts = [](int32_t n, int32_t m) { return static_cast<int64_t>(static_cast<uint64_t>(static_cast<uint32_t>(n)) | (static_cast<uint64_t>(static_cast<uint32_t>(m)) << 32)); };
    const int64_t closed = counts(0, oldMax), opened = counts(num, max);
    auto* header = reinterpret_cast<volatile uint8_t*>(at);
    // the count first (no reader walks past it), then the pointer, then the new count; memcpy: rows need not be 8-aligned
    std::memcpy(const_cast<uint8_t*>(header) + 8, &closed, 8);
    std::memcpy(const_cast<uint8_t*>(header), &pointer, 8);
    std::memcpy(const_cast<uint8_t*>(header) + 8, &opened, 8);
    if (protect) { VirtualProtect(reinterpret_cast<void*>(at), 16, old, &old); }
    return true;
}

namespace ListGetters
{
// (3.16.2) The rows of the mod's copies of the table (TableCopies) and the game's rows they stand for. A list is
// published for the game's row and handed out for it through a handle into any copy of its table as well: the game reads
// some rows through handles it found before a copy took the table's place (into its own rows), others through the copy.
struct Span
{
    uintptr_t Begin = 0, End = 0, Game = 0, RowSize = 0;
};
std::atomic<const std::vector<Span>*> Spans{nullptr};
std::vector<std::unique_ptr<std::vector<Span>>> SpanLists;   // every list of spans published (a getter may still read one)

// The game's row a row stands for (itself when it is not a copy's).
uintptr_t Canonical(uintptr_t row)
{
    const std::vector<Span>* spans = Spans.load(std::memory_order_acquire);
    if (!spans || !row) { return row; }
    for (const Span& s : *spans)
    {
        if (row >= s.Begin && row < s.End && (row - s.Begin) % s.RowSize == 0) { return s.Game + (row - s.Begin); }
    }
    return row;
}

// A copy's rows stand for the game's (game thread; kept for the session, as the copies are).
void AddSpan(uintptr_t copyRows, uintptr_t gameRows, int32_t rowSize, int32_t count)
{
    if (!copyRows || !gameRows || copyRows == gameRows || rowSize <= 0 || count <= 0) { return; }
    const std::vector<Span>* now = Spans.load(std::memory_order_acquire);
    if (now && std::any_of(now->begin(), now->end(), [&](const Span& s) { return s.Begin == copyRows; })) { return; }
    auto next = std::make_unique<std::vector<Span>>();
    if (now) { *next = *now; }
    const uintptr_t size = static_cast<uintptr_t>(rowSize);
    next->push_back(Span{copyRows, copyRows + size * static_cast<uintptr_t>(count), gameRows, size});
    Spans.store(next.get(), std::memory_order_release);
    SpanLists.push_back(std::move(next));
}

} // namespace ListGetters
namespace TableCopies
{
constexpr size_t RootSize = 88;
constexpr size_t RootPointers[] = {0, 16, 40, 56, 72};   // elements, allocation bits, hash, struct definition, rows
constexpr size_t RootSpace = 96;                         // (the rows after it, 16-byte aligned)

struct Copy
{
    std::wstring Path;
    uintptr_t Holder = 0;     // the game's table holder
    uintptr_t Original = 0;   // the game's root
    FrozenTable Table;        // the game's table (opened at its root): fields, row size, keys, rows
    uint8_t* Memory = nullptr;   // the root and the rows: the engine's allocator (never freed by the mod: the game may free
                                 // what its holder points at, e.g. as it exits, and does so with the engine's allocator)
    uintptr_t Root = 0;       // the copy's root and rows
    uintptr_t Rows = 0;
    bool Placed = false;
    bool EverPlaced = false;  // it was in the game's place (a reader may be in it: kept for the session)
    std::vector<std::unique_ptr<std::vector<uint64_t>>> Names;   // name lists its rows point at
    std::vector<std::unique_ptr<std::vector<wchar_t>>> Texts;    // texts its rows point at
    int32_t Edits = 0;
};

// every copy made (never destroyed at exit): one the game was given stays for the session, one it never was is freed
// (Discard)
std::vector<std::unique_ptr<Copy>>& All = *new std::vector<std::unique_ptr<Copy>>();
std::vector<Copy*> Live;                  // in the game's place now

// A frozen pointer stored at `from` (0: none), made for `to` (pointing at the same place).
int64_t Moved(uintptr_t from, uintptr_t to, int64_t value)
{
    if (value == 0) { return 0; }
    return SkelCompat::Frozen::Encode(to, SkelCompat::Frozen::Resolve(from, value));
}

// A field's bytes in a row (an array or a text: 16).
int32_t FieldSize(const SkelCompat::Frozen::Field& field)
{
    int32_t size = 0, align = 0;
    if (field.Array) { return 16; }
    return SkelCompat::Frozen::TypeSize(field.Type, size, align) ? size : 0;
}

bool HasPointer(const SkelCompat::Frozen::Field& field) { return field.Array || field.Type == 10; }

// The root the game's own table had before a copy of the mod's took its place (the holder's root otherwise).
uintptr_t GameRoot(uintptr_t holder, uintptr_t now)
{
    for (const Copy* c : Live)
    {
        if (c->Holder == holder && c->Root == now) { return c->Original; }
    }
    return now;
}

// Whether the table at `path` is there to copy: 1 yes (its holder and the root it points at now), 0 not yet (the
// object or its table not loaded: worth waiting for at the start), -1 not usable (`why` says why). Copies nothing.
int Probe(const std::wstring& path, std::wstring& why, uintptr_t* holderOut = nullptr, uintptr_t* nowOut = nullptr)
{
    UObject* object = FindDataObject(path.c_str());
    if (!object)
    {
        why = L"not loaded";
        return 0;
    }
    const uintptr_t holder = DataObjectHolder(object, why);
    if (!holder) { return why == L"no table loaded" ? 0 : -1; }
    uintptr_t now = 0;
    if (!ReadAt(reinterpret_cast<const void*>(holder), 8, now) || !now)
    {
        why = L"no table loaded";
        return 0;
    }
    if (holderOut) { *holderOut = holder; }
    if (nowOut) { *nowOut = now; }
    return 1;
}

// A writable copy of the table at `path` (not in the game's place yet: Place puts it there, Discard frees it).
Copy* Make(const std::wstring& path, std::wstring& why)
{
    uintptr_t holder = 0, now = 0;
    if (Probe(path, why, &holder, &now) != 1) { return nullptr; }
    auto copy = std::make_unique<Copy>();
    copy->Path = path;
    copy->Holder = holder;
    copy->Original = GameRoot(holder, now);
    if (!OpenTableAt(copy->Original, copy->Table, why)) { return nullptr; }
    const size_t bytes = static_cast<size_t>(copy->Table.Count) * static_cast<size_t>(copy->Table.RowSize);
    copy->Memory = static_cast<uint8_t*>(FMemory::Malloc(RootSpace + bytes, 16));
    if (!copy->Memory)
    {
        why = L"no memory for the copy";
        return nullptr;
    }
    std::memset(copy->Memory, 0, RootSpace + bytes);
    copy->Root = reinterpret_cast<uintptr_t>(copy->Memory);
    copy->Rows = copy->Root + RootSpace;
    if (!SafeCopy(reinterpret_cast<void*>(copy->Root), reinterpret_cast<const void*>(copy->Original), RootSize))
    {
        why = L"its root is unreadable";
        FMemory::Free(copy->Memory);   // (never the game's: freed)
        return nullptr;
    }
    for (const size_t at : RootPointers)
    {
        int64_t value = 0;
        std::memcpy(&value, reinterpret_cast<const void*>(copy->Root + at), sizeof(value));
        value = at == 72 ? SkelCompat::Frozen::Encode(copy->Root + at, copy->Rows) : Moved(copy->Original + at, copy->Root + at, value);
        std::memcpy(reinterpret_cast<void*>(copy->Root + at), &value, sizeof(value));
    }
    if (bytes && !SafeCopy(reinterpret_cast<void*>(copy->Rows), reinterpret_cast<const void*>(copy->Table.Rows), bytes))
    {
        why = L"its rows are unreadable";
        FMemory::Free(copy->Memory);
        return nullptr;
    }
    for (int32_t r = 0; r < copy->Table.Count; ++r)
    {
        const uintptr_t from = copy->Table.Rows + static_cast<uintptr_t>(r) * static_cast<uintptr_t>(copy->Table.RowSize);
        const uintptr_t to = copy->Rows + static_cast<uintptr_t>(r) * static_cast<uintptr_t>(copy->Table.RowSize);
        for (const auto& field : copy->Table.Fields)
        {
            if (!HasPointer(field)) { continue; }
            int64_t value = 0;
            std::memcpy(&value, reinterpret_cast<const void*>(to + field.Offset), sizeof(value));
            value = Moved(from + field.Offset, to + field.Offset, value);
            std::memcpy(reinterpret_cast<void*>(to + field.Offset), &value, sizeof(value));
        }
    }
    All.push_back(std::move(copy));
    return All.back().get();
}

// The copy's row of a key (0: none).
uintptr_t RowOf(const Copy& copy, const RawName& key)
{
    const uintptr_t game = TableRow(copy.Table, key);
    return game ? copy.Rows + (game - copy.Table.Rows) : 0;
}

const SkelCompat::Frozen::Field* FieldOf(const Copy& copy, std::wstring_view name) { return SkelCompat::Frozen::Find(copy.Table.Fields, name); }

// A name field's names (one, or its array's).
std::vector<RawName> NamesAt(uintptr_t row, const SkelCompat::Frozen::Field& field)
{
    std::vector<RawName> out;
    if (field.Type != 11) { return out; }
    if (!field.Array)
    {
        RawName name{};
        std::memcpy(&name, reinterpret_cast<const void*>(row + field.Offset), sizeof(name));
        out.push_back(name);
        return out;
    }
    int64_t value = 0;
    int32_t count = 0;
    std::memcpy(&value, reinterpret_cast<const void*>(row + field.Offset), sizeof(value));
    std::memcpy(&count, reinterpret_cast<const void*>(row + field.Offset + 8), sizeof(count));
    if (count <= 0 || count > 4096) { return out; }
    const uintptr_t data = SkelCompat::Frozen::Resolve(row + field.Offset, value);
    out.resize(static_cast<size_t>(count));
    if (!data || !SafeCopy(out.data(), reinterpret_cast<const void*>(data), out.size() * sizeof(RawName))) { out.clear(); }
    return out;
}

void SetNames(Copy& copy, uintptr_t row, const SkelCompat::Frozen::Field& field, const std::vector<RawName>& names)
{
    const uintptr_t at = row + field.Offset;
    if (!field.Array)
    {
        const RawName name = names.empty() ? RawName{} : names.front();
        std::memcpy(reinterpret_cast<void*>(at), &name, sizeof(name));
        ++copy.Edits;
        return;
    }
    auto list = std::make_unique<std::vector<uint64_t>>();
    for (const auto& name : names) { list->push_back(KeyOf(name)); }
    const int32_t count = static_cast<int32_t>(list->size());
    const int64_t pointer = count ? SkelCompat::Frozen::Encode(at, reinterpret_cast<uintptr_t>(list->data())) : 0;
    std::memcpy(reinterpret_cast<void*>(at), &pointer, sizeof(pointer));
    std::memcpy(reinterpret_cast<void*>(at + 8), &count, sizeof(count));
    std::memcpy(reinterpret_cast<void*>(at + 12), &count, sizeof(count));
    copy.Names.push_back(std::move(list));
    ++copy.Edits;
}

// A text field (a frozen TArray of TCHAR, its count with the terminating zero).
void SetText(Copy& copy, uintptr_t row, const SkelCompat::Frozen::Field& field, const std::wstring& text)
{
    const uintptr_t at = row + field.Offset;
    auto buffer = std::make_unique<std::vector<wchar_t>>(text.begin(), text.end());
    int32_t count = 0;
    int64_t pointer = 0;
    if (!text.empty())
    {
        buffer->push_back(L'\0');
        count = static_cast<int32_t>(buffer->size());
        pointer = SkelCompat::Frozen::Encode(at, reinterpret_cast<uintptr_t>(buffer->data()));
    }
    std::memcpy(reinterpret_cast<void*>(at), &pointer, sizeof(pointer));
    std::memcpy(reinterpret_cast<void*>(at + 8), &count, sizeof(count));
    std::memcpy(reinterpret_cast<void*>(at + 12), &count, sizeof(count));
    copy.Texts.push_back(std::move(buffer));
    ++copy.Edits;
}

// A number in a type's range (a value past it: its end; not a number: 0), for the casts below.
template <class T>
T InRange(double value)
{
    if (!(value == value)) { return T{}; }
    if constexpr (std::is_floating_point_v<T>)
    {
        const double most = static_cast<double>(std::numeric_limits<T>::max());
        return static_cast<T>(std::clamp(value, -most, most));
    }
    else
    {
        const double low = static_cast<double>(std::numeric_limits<T>::lowest());
        const double high = static_cast<double>(std::numeric_limits<T>::max());
        if (value <= low) { return std::numeric_limits<T>::lowest(); }
        if (value >= high) { return std::numeric_limits<T>::max(); }   // (high itself may not be a double: 2^63 - 1)
        return static_cast<T>(value);
    }
}

// A number field (bool, the integer types, float); false for any other.
bool SetNumber(Copy& copy, uintptr_t row, const SkelCompat::Frozen::Field& field, double value)
{
    if (field.Array) { return false; }
    void* at = reinterpret_cast<void*>(row + field.Offset);
    const auto put = [&](auto v) { std::memcpy(at, &v, sizeof(v)); };
    switch (field.Type)
    {
    case 1: put(static_cast<uint8_t>(value != 0.0 ? 1 : 0)); break;
    case 2: put(InRange<uint8_t>(value)); break;
    case 3: put(InRange<int8_t>(value)); break;
    case 4: put(InRange<uint16_t>(value)); break;
    case 5: put(InRange<int16_t>(value)); break;
    case 6: put(InRange<uint32_t>(value)); break;
    case 7: put(InRange<int32_t>(value)); break;
    case 8: put(InRange<int64_t>(value)); break;
    case 9: put(InRange<float>(value)); break;
    default: return false;
    }
    ++copy.Edits;
    return true;
}

// Row `to` gets row `from`'s content (both the copy's), but for the `keep` fields.
void CopyRow(Copy& copy, uintptr_t to, uintptr_t from, const std::vector<const SkelCompat::Frozen::Field*>& keep)
{
    const size_t size = static_cast<size_t>(copy.Table.RowSize);
    std::vector<uint8_t> own(size);
    std::memcpy(own.data(), reinterpret_cast<const void*>(to), size);
    std::memcpy(reinterpret_cast<void*>(to), reinterpret_cast<const void*>(from), size);
    for (const auto& field : copy.Table.Fields)
    {
        if (!HasPointer(field)) { continue; }
        int64_t value = 0;
        std::memcpy(&value, reinterpret_cast<const void*>(to + field.Offset), sizeof(value));
        value = Moved(from + field.Offset, to + field.Offset, value);
        std::memcpy(reinterpret_cast<void*>(to + field.Offset), &value, sizeof(value));
    }
    for (const SkelCompat::Frozen::Field* field : keep)
    {
        if (field) { std::memcpy(reinterpret_cast<void*>(to + field->Offset), own.data() + field->Offset, static_cast<size_t>(FieldSize(*field))); }
    }
    ++copy.Edits;
}

void Exchange(uintptr_t holder, uintptr_t root)
{
    const uintptr_t at = holder + 8;
    if ((at & 7) == 0) { InterlockedExchange64(reinterpret_cast<volatile LONG64*>(at), static_cast<LONG64>(root)); }
    else { std::memcpy(reinterpret_cast<void*>(at), &root, sizeof(root)); }
}

// Puts the copy in the game's place (in place of the game's root, or of another copy of the same table). The lists
// published for the game's rows are handed out for the copy's rows too (ListGetters::AddSpan; 3.16.0 moved them to the
// copy's rows, and the game's handles into its own rows lost them).
bool Place(Copy& copy, std::wstring& why)
{
    uintptr_t now = 0;
    if (!ReadAt(reinterpret_cast<const void*>(copy.Holder), 8, now) || !now)
    {
        why = L"its table is not loaded";
        return false;
    }
    if (GameRoot(copy.Holder, now) != copy.Original)
    {
        why = L"the game's table changed since the copy was made";
        return false;
    }
    if (!LuaPump::RangeOk(copy.Holder + 8, 8, true))
    {
        why = L"its table holder cannot be written";
        return false;
    }
    if (SkelCompat::PathEquals(copy.Path, PlayerTablePath)) { ListGetters::AddSpan(copy.Rows, copy.Table.Rows, copy.Table.RowSize, copy.Table.Count); }
    Exchange(copy.Holder, copy.Root);
    copy.EverPlaced = true;
    for (Copy* c : Live)
    {
        if (c->Holder == copy.Holder) { c->Placed = false; }
    }
    Live.erase(std::remove_if(Live.begin(), Live.end(), [&](const Copy* c) { return c->Holder == copy.Holder; }), Live.end());
    Live.push_back(&copy);
    copy.Placed = true;
    return true;
}

// (3.16.2) The game keeps some of the rows it found before a copy took its table's place: a party member's PlayerTable
// row, found as the game starts (it spawns the member's CharaSpec from that row, never from the table its holder points
// at by then: 3.16.1 put CLOUD's copies in at the first map load and the game still spawned Cloud's own CharaSpec row).
// So a placed copy's changes go into the game's own rows too, in place, where the game's memory lets them (its tables
// on the heap; a table it maps read-only keeps them in the copy alone): every field of a row the copy changed (a name or
// a number: its bytes; a list or a text: a pointer at the copy's, which stays for the session), the bytes there before
// kept for RestoreAll. A table is written whole or not at all. Game thread only.
struct Mirrored
{
    const Copy* Of = nullptr;
    uintptr_t At = 0;
    std::array<uint8_t, 16> Before{};
    int32_t Size = 0;     // a list or a text: 16 ({pointer, count, count}); else the field's bytes
    bool List = false;
};
std::vector<Mirrored> MirroredBytes;

// `size` bytes at `at` in a table's rows (made writable for the write when they are not).
bool WriteRaw(uintptr_t at, const void* bytes, size_t size)
{
    MEMORY_BASIC_INFORMATION info{};
    if (!VirtualQuery(reinterpret_cast<void*>(at), &info, sizeof(info)) || info.State != MEM_COMMIT)
    {
        TableWriteProblem = L"the row's memory is not committed";
        return false;
    }
    const DWORD writable = PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY;
    DWORD old = 0;
    const bool protect = (info.Protect & writable) == 0;
    if (protect && !VirtualProtect(reinterpret_cast<void*>(at), size, PAGE_READWRITE, &old) && !VirtualProtect(reinterpret_cast<void*>(at), size, PAGE_WRITECOPY, &old))
    {
        const DWORD error = GetLastError();
        TableWriteProblem = L"the row's memory is read-only (" + std::wstring(info.Type == MEM_MAPPED ? L"a mapped file" : info.Type == MEM_IMAGE ? L"an image" : L"private") +
                            L", protection " + Hex(info.Protect) + L", error " + std::to_wstring(error) + L")";
        return false;
    }
    std::memcpy(reinterpret_cast<void*>(at), bytes, size);
    if (protect)
    {
        DWORD unused = 0;
        VirtualProtect(reinterpret_cast<void*>(at), size, old, &unused);
    }
    return true;
}

// Whether a copy's table is still the one its rows were written for: its holder points at the copy or at the game's root
// the copy was made from (else the game has another table there now, and the old rows may be gone).
bool StillThere(const Copy& copy)
{
    uintptr_t now = 0;
    return ReadAt(reinterpret_cast<const void*>(copy.Holder), 8, now) && (now == copy.Root || now == copy.Original);
}

// The bytes there before back at the game's rows, the entries from `from` on (the last first).
void RestoreMirrored(size_t from = 0)
{
    if (from >= MirroredBytes.size()) { return; }
    for (size_t k = MirroredBytes.size(); k-- > from;)
    {
        const Mirrored& m = MirroredBytes[k];
        if (!m.Of || !StillThere(*m.Of)) { continue; }   // (another table in its place: not the game's rows any more)
        if (m.List)
        {
            int64_t pointer = 0;
            int32_t count = 0, most = 0;
            std::memcpy(&pointer, m.Before.data(), sizeof(pointer));
            std::memcpy(&count, m.Before.data() + 8, sizeof(count));
            std::memcpy(&most, m.Before.data() + 12, sizeof(most));
            WriteTableArray(m.At, pointer, count, most);
        }
        else { WriteRaw(m.At, m.Before.data(), static_cast<size_t>(m.Size)); }
    }
    MirroredBytes.erase(MirroredBytes.begin() + static_cast<std::ptrdiff_t>(from), MirroredBytes.end());
}

// A placed copy's changes into the game's own rows (see Mirrored). Returns how many fields were written; -1 when the
// table's rows could not be (`problem` says why; any written before it are taken back).
int32_t Mirror(const Copy& copy, std::wstring& problem)
{
    const size_t start = MirroredBytes.size();
    const size_t size = static_cast<size_t>(copy.Table.RowSize);
    const size_t bytes = static_cast<size_t>(copy.Table.Count) * size;
    if (!copy.Placed || !bytes) { return 0; }
    std::vector<uint8_t> game(bytes);   // (the game's rows as they are now: read once)
    if (!SafeCopy(game.data(), reinterpret_cast<const void*>(copy.Table.Rows), bytes))
    {
        problem = L"its rows are unreadable";
        return -1;
    }
    int32_t written = 0;
    for (int32_t r = 0; r < copy.Table.Count; ++r)
    {
        const size_t rowAt = static_cast<size_t>(r) * size;
        const uint8_t* mineRow = reinterpret_cast<const uint8_t*>(copy.Rows) + rowAt;
        if (std::memcmp(mineRow, game.data() + rowAt, size) == 0) { continue; }   // (no field moved or changed)
        for (const auto& field : copy.Table.Fields)
        {
            const size_t offset = static_cast<size_t>(field.Offset);
            const uintptr_t mine = copy.Rows + rowAt + offset;
            const uintptr_t at = copy.Table.Rows + rowAt + offset;
            Mirrored m;
            m.Of = &copy;
            m.At = at;
            m.List = HasPointer(field);
            m.Size = m.List ? 16 : FieldSize(field);
            if (m.Size <= 0 || m.Size > 16 || offset + static_cast<size_t>(m.Size) > size) { continue; }
            std::memcpy(m.Before.data(), game.data() + rowAt + offset, static_cast<size_t>(m.Size));
            bool ok = true;
            if (m.List)
            {
                int64_t mineValue = 0, gameValue = 0;
                int32_t mineCount = 0, mineMost = 0, gameCount = 0, gameMost = 0;
                std::memcpy(&mineValue, reinterpret_cast<const void*>(mine), 8);
                std::memcpy(&mineCount, reinterpret_cast<const void*>(mine + 8), 4);
                std::memcpy(&mineMost, reinterpret_cast<const void*>(mine + 12), 4);
                std::memcpy(&gameValue, m.Before.data(), 8);
                std::memcpy(&gameCount, m.Before.data() + 8, 4);
                std::memcpy(&gameMost, m.Before.data() + 12, 4);
                const uintptr_t mineData = SkelCompat::Frozen::Resolve(mine, mineValue);
                const uintptr_t gameData = SkelCompat::Frozen::Resolve(at, gameValue);
                if (mineData == gameData && mineCount == gameCount && mineMost == gameMost) { continue; }   // (the same list, its pointer made again)
                ok = WriteTableArray(at, mineData ? SkelCompat::Frozen::Encode(at, mineData) : 0, mineCount, mineMost);
            }
            else
            {
                if (std::memcmp(reinterpret_cast<const void*>(mine), m.Before.data(), static_cast<size_t>(m.Size)) == 0) { continue; }
                ok = WriteRaw(at, reinterpret_cast<const void*>(mine), static_cast<size_t>(m.Size));
            }
            if (!ok)
            {
                problem = TableWriteProblem.empty() ? std::wstring(L"its rows cannot be written") : TableWriteProblem;
                RestoreMirrored(start);
                return -1;
            }
            MirroredBytes.push_back(m);
            ++written;
        }
    }
    return written;
}

// The game's own tables back (each whose holder still points at the mod's copy). Returns how many. A copy whose holder
// cannot be written now stays live (a copy made next is still made from the game's own root, not from it). (3.16.2) What
// Mirror wrote into the game's own rows goes back first.
int32_t RestoreAll()
{
    RestoreMirrored();
    int32_t restored = 0;
    std::vector<Copy*> still;
    for (Copy* c : Live)
    {
        uintptr_t now = 0;
        if (!ReadAt(reinterpret_cast<const void*>(c->Holder), 8, now) || now != c->Root)
        {
            c->Placed = false;   // (the holder points at another table now: the copy is out of the game's place)
            continue;
        }
        if (!LuaPump::RangeOk(c->Holder + 8, 8, true))
        {
            still.push_back(c);
            continue;
        }
        Exchange(c->Holder, c->Original);
        c->Placed = false;
        ++restored;
    }
    Live = std::move(still);
    return restored;
}

// Frees a copy the game was never given (Place never put it in the game's place); one it was given stays for the session.
void Discard(Copy* copy)
{
    if (!copy || copy->EverPlaced) { return; }
    for (auto it = All.begin(); it != All.end(); ++it)
    {
        if (it->get() != copy) { continue; }
        if (copy->Memory) { FMemory::Free(copy->Memory); }
        All.erase(it);
        return;
    }
}

// Every copy still in the game's place.
bool AllInPlace()
{
    for (const Copy* c : Live)
    {
        uintptr_t now = 0;
        if (!ReadAt(reinterpret_cast<const void*>(c->Holder), 8, now) || now != c->Root) { return false; }
    }
    return true;
}
} // namespace TableCopies

// ---- the test: a synthetic frozen table (the game's layout: root, elements, struct definition, rows, lists, texts)
int Failures = 0;
#define CHECK(c)                                                         \
    do                                                                   \
    {                                                                    \
        if (!(c))                                                        \
        {                                                                \
            ++Failures;                                                  \
            std::printf("FAIL line %d: %s\n", __LINE__, #c);             \
        }                                                                \
    } while (0)

enum : uint32_t
{
    NName = 1, NFlag, NLevel, NArray, NText, NScale,
    NA = 10, NB, NC, ND,
    S0 = 20, S1, S2, S3,
    NX = 30, NY
};

RawName R(uint32_t c) { return RawName{c, 0}; }

constexpr int32_t RowSize = 56;   // Name 0 (FName), Flag 8 (bool), Level 12 (int32), Array 16, Text 32, Scale 48 (float)

struct Image
{
    uint8_t* Base = nullptr;
    size_t Size = 0;
    uintptr_t Root = 0, Rows = 0;
};

void PutArray(uintptr_t at, uintptr_t target, int32_t num, int32_t max)
{
    const int64_t value = target ? SkelCompat::Frozen::Encode(at, target) : 0;
    std::memcpy(reinterpret_cast<void*>(at), &value, 8);
    std::memcpy(reinterpret_cast<void*>(at + 8), &num, 4);
    std::memcpy(reinterpret_cast<void*>(at + 12), &max, 4);
}

void PutRow(uintptr_t row, uint32_t name, uint8_t flag, int32_t level, uintptr_t list, const std::vector<uint32_t>& names, uintptr_t textAt,
            const std::wstring& text, float scale)
{
    const RawName n = R(name);
    std::memcpy(reinterpret_cast<void*>(row), &n, 8);
    std::memcpy(reinterpret_cast<void*>(row + 8), &flag, 1);
    std::memcpy(reinterpret_cast<void*>(row + 12), &level, 4);
    for (size_t k = 0; k < names.size(); ++k)
    {
        const uint64_t key = KeyOf(R(names[k]));
        std::memcpy(reinterpret_cast<void*>(list + k * 8), &key, 8);
    }
    PutArray(row + 16, names.empty() ? 0 : list, static_cast<int32_t>(names.size()), static_cast<int32_t>(names.size()));
    if (!text.empty())
    {
        std::memcpy(reinterpret_cast<void*>(textAt), text.c_str(), (text.size() + 1) * sizeof(wchar_t));
        PutArray(row + 32, textAt, static_cast<int32_t>(text.size() + 1), static_cast<int32_t>(text.size() + 1));
    }
    std::memcpy(reinterpret_cast<void*>(row + 48), &scale, 4);
}

Image Build()
{
    Image im;
    im.Size = 4096;
    im.Base = static_cast<uint8_t*>(std::aligned_alloc(16, im.Size));
    std::memset(im.Base, 0, im.Size);
    const uintptr_t b = reinterpret_cast<uintptr_t>(im.Base);
    const uintptr_t elements = b + 96, defs = b + 192, rows = b + 288, lists = b + 512, texts = b + 768;
    im.Root = b;
    im.Rows = rows;
    const std::pair<uint32_t, int32_t> keys[] = {{NB, 1}, {NA, 0}, {ND, 3}, {NC, 2}};   // (not in row order)
    for (int k = 0; k < 4; ++k)
    {
        const RawName key = R(keys[k].first);
        const int32_t row = keys[k].second, next = -1, bucket = 0;
        std::memcpy(reinterpret_cast<void*>(elements + k * 20), &key, 8);
        std::memcpy(reinterpret_cast<void*>(elements + k * 20 + 8), &row, 4);
        std::memcpy(reinterpret_cast<void*>(elements + k * 20 + 12), &next, 4);
        std::memcpy(reinterpret_cast<void*>(elements + k * 20 + 16), &bucket, 4);
    }
    PutArray(b + 0, elements, 4, 4);
    PutArray(b + 56, defs, 6, 6);
    PutArray(b + 72, rows, 4, 4);
    const std::pair<uint32_t, int32_t> fields[] = {{NName, 11}, {NFlag, 1}, {NLevel, 7}, {NArray, 11}, {NText, 10}, {NScale, 9}};
    for (int k = 0; k < 6; ++k)
    {
        const RawName name = R(fields[k].first);
        std::memcpy(reinterpret_cast<void*>(defs + k * 12), &name, 8);
        std::memcpy(reinterpret_cast<void*>(defs + k * 12 + 8), &fields[k].second, 4);
    }
    PutRow(rows + 0 * RowSize, S0, 1, 5, lists + 0, {S0, S1}, texts + 0, L"alpha", 1.0f);
    PutRow(rows + 1 * RowSize, S2, 0, 7, lists + 16, {S2}, texts + 64, L"beta", 2.0f);
    PutRow(rows + 2 * RowSize, S3, 1, 9, lists + 24, {}, texts + 128, L"", 3.0f);
    PutRow(rows + 3 * RowSize, S3, 0, 11, lists + 32, {S3, S0, S1}, texts + 192, L"delta", 4.0f);
    return im;
}

struct RowView
{
    RawName Name;
    uint8_t Flag = 0;
    int32_t Level = 0;
    std::vector<uint64_t> Array;
    std::wstring Text;
    float Scale = 0;
};

RowView Read(uintptr_t row)
{
    RowView v;
    std::memcpy(&v.Name, reinterpret_cast<const void*>(row), 8);
    std::memcpy(&v.Flag, reinterpret_cast<const void*>(row + 8), 1);
    std::memcpy(&v.Level, reinterpret_cast<const void*>(row + 12), 4);
    int64_t value = 0;
    int32_t count = 0;
    std::memcpy(&value, reinterpret_cast<const void*>(row + 16), 8);
    std::memcpy(&count, reinterpret_cast<const void*>(row + 24), 4);
    const uintptr_t list = SkelCompat::Frozen::Resolve(row + 16, value);
    for (int32_t k = 0; k < count; ++k)
    {
        uint64_t key = 0;
        std::memcpy(&key, reinterpret_cast<const void*>(list + static_cast<uintptr_t>(k) * 8), 8);
        v.Array.push_back(key);
    }
    std::memcpy(&value, reinterpret_cast<const void*>(row + 32), 8);
    std::memcpy(&count, reinterpret_cast<const void*>(row + 40), 4);
    const uintptr_t text = SkelCompat::Frozen::Resolve(row + 32, value);
    if (count > 0) { v.Text.assign(reinterpret_cast<const wchar_t*>(text), static_cast<size_t>(count - 1)); }
    std::memcpy(&v.Scale, reinterpret_cast<const void*>(row + 48), 4);
    return v;
}

bool Same(const RowView& a, const RowView& b)
{
    return SameName(a.Name, b.Name) && a.Flag == b.Flag && a.Level == b.Level && a.Array == b.Array && a.Text == b.Text && a.Scale == b.Scale;
}

std::vector<uint64_t> Keys(std::initializer_list<uint32_t> names)
{
    std::vector<uint64_t> out;
    for (const uint32_t n : names) { out.push_back(KeyOf(R(n))); }
    return out;
}

uintptr_t HolderRoot(const uint8_t* holder)
{
    uintptr_t now = 0;
    std::memcpy(&now, holder + 8, 8);
    return now;
}

// A copy with the test's changes (A's list, B's level and name, C's text, D as B but its level), in the game's place.
TableCopies::Copy* Changed(const wchar_t* path)
{
    std::wstring why;
    TableCopies::Copy* copy = TableCopies::Make(path, why);
    CHECK(copy != nullptr);
    if (!copy) { return nullptr; }
    const auto* fName = TableCopies::FieldOf(*copy, L"Name");
    const auto* fLevel = TableCopies::FieldOf(*copy, L"Level");
    const auto* fArray = TableCopies::FieldOf(*copy, L"PlayerCharaSpec_Array");
    const auto* fText = TableCopies::FieldOf(*copy, L"Text");
    CHECK(fName && fLevel && fArray && fText);
    CHECK(fArray && fArray->Array && fArray->Offset == 16 && fText && fText->Offset == 32 && copy->Table.RowSize == RowSize);
    const uintptr_t a = TableCopies::RowOf(*copy, R(NA)), b = TableCopies::RowOf(*copy, R(NB));
    const uintptr_t c = TableCopies::RowOf(*copy, R(NC)), d = TableCopies::RowOf(*copy, R(ND));
    CHECK(a == copy->Rows && b == copy->Rows + RowSize && c == copy->Rows + 2 * RowSize && d == copy->Rows + 3 * RowSize);
    TableCopies::SetNames(*copy, a, *fArray, {R(NX), R(NY)});
    TableCopies::SetNumber(*copy, b, *fLevel, 99);
    TableCopies::SetNames(*copy, b, *fName, {R(NY)});
    TableCopies::SetText(*copy, c, *fText, L"gamma");
    TableCopies::CopyRow(*copy, d, b, {fLevel});
    CHECK(TableCopies::Place(*copy, why));
    return copy;
}

int main()
{
    NameTexts = {{NName, L"Name"}, {NFlag, L"Flag"}, {NLevel, L"Level"}, {NArray, L"PlayerCharaSpec_Array"}, {NText, L"Text"}, {NScale, L"Scale"},
                 {NA, L"pt_A"}, {NB, L"pt_B"}, {NC, L"pt_C"}, {ND, L"pt_D"}, {S0, L"Spec_0"}, {S1, L"Spec_1"}, {S2, L"Spec_2"},
                 {S3, L"Spec_3"}, {NX, L"X"}, {NY, L"Y"}};
    Image im = Build();
    const std::vector<uint8_t> original(im.Base, im.Base + im.Size);
    alignas(16) uint8_t holder[16]{};
    TheHolder = reinterpret_cast<uintptr_t>(holder);
    std::memcpy(holder + 8, &im.Root, 8);
    const auto gameRow = [&](int r) { return im.Rows + static_cast<uintptr_t>(r) * RowSize; };
    const auto unchanged = [&]() { return std::memcmp(im.Base, original.data(), im.Size) == 0; };

    // 1. the changes in the copy, in the game's place, then in the game's own rows
    {
        TableCopies::Copy* copy = Changed(PlayerTablePath);
        CHECK(copy && HolderRoot(holder) == copy->Root);
        CHECK(unchanged());   // (a copy alone: the game's rows as they were)
        std::wstring why;
        const int32_t fields = copy ? TableCopies::Mirror(*copy, why) : -2;
        std::printf("1. mirrored %d field(s)%s\n", fields, why.empty() ? "" : " (a problem)");
        // A's list, B's level and name, C's text, D's name, flag (same), list, text, scale (D keeps its level): 4 + 4
        CHECK(fields == 8);
        for (int r = 0; copy && r < 4; ++r) { CHECK(Same(Read(gameRow(r)), Read(copy->Rows + static_cast<uintptr_t>(r) * RowSize))); }
        const RowView a = Read(gameRow(0)), b = Read(gameRow(1)), c = Read(gameRow(2)), d = Read(gameRow(3));
        CHECK(a.Array == Keys({NX, NY}) && a.Level == 5 && a.Text == L"alpha" && SameName(a.Name, R(S0)));
        CHECK(b.Level == 99 && SameName(b.Name, R(NY)) && b.Array == Keys({S2}) && b.Text == L"beta");
        CHECK(c.Text == L"gamma" && c.Array.empty() && c.Level == 9);
        CHECK(d.Level == 11 && SameName(d.Name, R(NY)) && d.Array == Keys({S2}) && d.Text == L"beta" && d.Flag == 0 && d.Scale == 2.0f);
        // the root, the elements, the struct definition, the game's lists and texts: untouched
        CHECK(std::memcmp(im.Base, original.data(), 288) == 0);
        CHECK(std::memcmp(im.Base + 512, original.data() + 512, im.Size - 512) == 0);
        // only the changed fields of the rows: A's name, flag, level, text, scale are the game's bytes
        CHECK(std::memcmp(im.Base + 288, original.data() + 288, 16) == 0);
        CHECK(std::memcmp(im.Base + 288 + 32, original.data() + 288 + 32, 24) == 0);
        // a copy's rows stand for the game's (BattlePlayerParameter's)
        CHECK(copy && ListGetters::Canonical(copy->Rows + 2 * RowSize) == gameRow(2));
        CHECK(ListGetters::Canonical(gameRow(1)) == gameRow(1));
        CHECK(copy && ListGetters::Canonical(copy->Rows + 1) == copy->Rows + 1);
        CHECK(ListGetters::Canonical(0) == 0);
        // back: every byte the game's own, the holder at the game's root
        CHECK(TableCopies::RestoreAll() == 1);
        CHECK(HolderRoot(holder) == im.Root);
        CHECK(unchanged());
        CHECK(TableCopies::MirroredBytes.empty());
    }
    // 2. the game's rows read-only: nothing written (the copy alone has the changes)
    {
        TableCopies::Copy* copy = Changed(L"/Game/DataObject/Resident/PlayerTable.PlayerTable");
        ReadOnlyBegin = im.Rows;
        ReadOnlyEnd = im.Rows + 4 * RowSize;
        std::wstring why;
        const int32_t fields = copy ? TableCopies::Mirror(*copy, why) : -2;
        std::printf("2. read-only: %d (%ls)\n", fields, why.c_str());
        CHECK(fields == -1 && why.find(L"read-only") != std::wstring::npos);
        CHECK(unchanged());
        CHECK(TableCopies::MirroredBytes.empty());
        ReadOnlyBegin = ReadOnlyEnd = 0;
        CHECK(copy && HolderRoot(holder) == copy->Root);
        CHECK(TableCopies::RestoreAll() == 1);
        CHECK(HolderRoot(holder) == im.Root && unchanged());
    }
    // 3. the last changed row read-only: the fields written before it are taken back
    {
        TableCopies::Copy* copy = Changed(L"/Game/DataObject/Resident/PlayerTable.PlayerTable");
        ReadOnlyBegin = gameRow(3);
        ReadOnlyEnd = gameRow(4);
        std::wstring why;
        const int calls = ProtectCalls;
        const int32_t fields = copy ? TableCopies::Mirror(*copy, why) : -2;
        std::printf("3. a row read-only: %d (%ls), %d protect call(s)\n", fields, why.c_str(), ProtectCalls - calls);
        CHECK(fields == -1);
        CHECK(unchanged());
        CHECK(TableCopies::MirroredBytes.empty());
        ReadOnlyBegin = ReadOnlyEnd = 0;
        CHECK(TableCopies::RestoreAll() == 1 && unchanged());
    }
    // 4. a table the game replaced since (its holder at another root): its old rows are left alone
    {
        TableCopies::Copy* copy = Changed(L"/Game/DataObject/Resident/PlayerTable.PlayerTable");
        std::wstring why;
        const int32_t fields = copy ? TableCopies::Mirror(*copy, why) : -2;
        CHECK(fields == 8);
        CHECK(!unchanged());
        Image other = Build();
        std::memcpy(holder + 8, &other.Root, 8);   // (the game's table loaded again elsewhere)
        CHECK(TableCopies::RestoreAll() == 0);
        CHECK(HolderRoot(holder) == other.Root);
        CHECK(TableCopies::MirroredBytes.empty());
        CHECK(!unchanged());   // (the old rows: not written again)
        std::printf("4. a table replaced: its old rows left alone\n");
        std::free(other.Base);
    }
    if (Failures)
    {
        std::printf("%d check(s) FAILED\n", Failures);
        return 1;
    }
    std::printf("all mirror tests passed\n");
    return 0;
}
