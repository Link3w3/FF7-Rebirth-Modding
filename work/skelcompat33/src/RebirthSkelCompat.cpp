// RebirthSkelCompat - KH3-style skeleton compatibility for FINAL FANTASY VII REBIRTH (retail UE 4.26)
// UE4SS C++ mod, built against the installed UE4SS 3.0.1 c0a8d4c / UEPseudo b4a6e7 SDK.
//
// Retail Rebirth has no compatible-skeleton list (no SQEX_CompatibleSkeletonLists or UE5-style
// CompatibleSkeletons in the executable's reflection data) and its skeleton checks are inlined
// pointer comparisons. Instead of patching those checks, each pair uses one of two methods:
//
//   * "animations" (default, KH3 mode): every animation asset of the animation skeleton is rewritten
//     onto the receiving skeleton while it loads (track tables, curve UIDs, per-bone data, Skeleton
//     pointer). Characters keep their own skeleton, AnimBlueprint and physics; the adopted animations
//     simply belong to their skeleton now. See "Animation adoption" below for the safety rules.
//   * "mesh": a mesh whose skeleton is listed as a receiving skeleton is rebound to the animation
//     skeleton while it loads. The engine then builds the usual by-name mesh/skeleton linkup: shared
//     bones animate, mesh-only bones keep their reference pose (or physics), skeleton-only tracks are
//     ignored. Used for custom skeletons that should run another skeleton's AnimBlueprint.
//   * families (3.0): skeletons that share animations both ways, or that several pairs want animations
//     from, gather on one hub skeleton. SkelCompatCore's FinishConfig turns a family into an "animations"
//     pair (the hub adopts every member's animations) plus a "mesh" pair per member (its meshes are rebound
//     to the hub), so every member plays every member's animations with its own AnimBlueprint.
//   * animation set rows (3.1): which animations a character's animation sets hold. The CharaSpec pack's
//     sets are replaced, while the pack loads, by sets merged from the row's battle / field sources (first
//     source with an animation name wins, the pack's own sets fill in last) plus the row's moves.
//   * 3.2: "auto" sources (another character's attacks fill a set's attack names by kind and length), socket
//     stand-ins on a character's meshes (row "sockets": a weapon socket the character lacks -> its hand), and
//     "proportions" (every character keeps its own bone lengths: body bones take their translation from the
//     playing mesh, the pelvis is scaled per body, against a retarget pose of the body each animation was made for).
//   * 3.3: "abilities" per primary animation pack: when a character's pack switches (EndBattleAPI SetPrimaryAnimPack /
//     ResetPrimaryAnimPack), its BattlePlayerParameter row ("player") lists that pack's commands and limit breaks.
//     3.3.1: through the game's own list getters (their table slots point at the mod's), as the rows can be read-only.
//     3.3.1 "pack_assets": objects put into a character's CharaSpec pack (another character's effect pack).
//   * 3.4: "weapon_abilities" per pack: the abilities a character's weapons give switch with its pack.
//   * 3.5: every set of a character's pack can be switched to: the game's calls of its set lookup point at the mod's,
//     which gives the pack's own set when the game took none of that name (it takes sets only from some slots of the
//     row's AnimationSetList).
//     3.5.1: the lookup is told apart from the game's other functions of its shape by the container its calls pass.
//     3.5.2: the log says, for the first switch of each row to each pack, whether the game had that set, and how often the
//     mod's lookup answered with its sets.
//     3.5.3: the Lua pump: Lua mods named in LuaPump::Mods are called every frame on the game thread (UE4SS 3.0.1's
//     ExecuteInGameThread is neither safe nor always on the game thread); RebirthSkelCompatIsGameThread() for every Lua mod.
//     3.5.2: the weapon ability lookups are found again: their table global holds 3 lists of 16-byte entries (not one
//     list of weak pointers), so the Equipment table is looked for in all of them.
// Assets in the paks are untouched; everything happens in memory.
//
// Hook points
//   * USkeletalMesh::PostLoad (primary vtable slot, validated before patching): rebind before the
//     engine's PostLoad runs, so virtual bones of the animation skeleton are merged as usual.
//     This runs for every skeletal mesh the game loads, so it only does a few direct reads unless
//     the mesh is part of a pair (no object-array walks, no string building).
//   * PostLoad of every native animation-asset class (same slot): adoption, after the engine's own
//     PostLoad. Sequences post-load on the async loading thread; that path only reads published,
//     immutable plans and writes the asset being loaded (serialised by AdoptMutex).
//   * UEndAssetDataAsset::PostLoad (same slot, game thread): animation set rows merge the pack's sets
//     before the engine's PostLoad.
//   * LoadMap post-callback (game thread): the first call finishes initialisation (class lookups,
//     offsets, hooks), then scans already-loaded assets and preloads + roots the configured skeletons.
//   * GameViewportClient::Tick post-callback (game thread, after the world tick): late adoption of
//     animations that were loaded before their plan existed.
//   * ProcessEvent post-callback (game thread only, throttled): late rebinds, repair of components
//     whose AnimBlueprint was refused before the rebind, diagnostics, F9 report.
//   * 3.3.1: the slots of the game's read-only tables of list getters that read a BattlePlayerParameter row's command
//     and limit entries (found by their code, validated, ListGetters): the mod's getters answer for switched rows only.
//   * 3.4: the game's calls that look up a weapon's Equipment row to read its ability (found by their code; the table
//     and the field are checked against the Equipment table): a call (rel32) to a jump near the game's code, to the
//     mod's lookup, which calls the game's and hands out a stand-in row for a weapon whose ability the pack replaces.
// Any error inside the mod switches the mod off for the session instead of taking the game down.

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <cwchar>
#include <filesystem>
#include <fstream>
#include <memory>
#include <mutex>
#include <new>
#include <string>
#include <type_traits>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "SkelCompatCore.hpp"

// Parse fmt before Unreal's warning policy (same order as the existing RebirthSkeletonObserver build).
#include <fmt/chrono.h>
#include <Unreal/UFunction.hpp>
#include <Unreal/FURL.hpp>
#include <Mod/CppUserModBase.hpp>
#include <LuaMadeSimple/LuaMadeSimple.hpp>
#include <Unreal/Hooks.hpp>
#include <Unreal/UObject.hpp>
#include <Unreal/UObjectGlobals.hpp>
#include <Unreal/UClass.hpp>
#include <Unreal/FProperty.hpp>
#include <Unreal/Property/FArrayProperty.hpp>
#include <Unreal/Property/FStructProperty.hpp>
#include <Unreal/UScriptStruct.hpp>
#include <Unreal/UGameViewportClient.hpp>
#include <Unreal/FString.hpp>
#include <Unreal/FMemory.hpp>
#include <Unreal/NameTypes.hpp>

namespace
{
using namespace RC;
using namespace RC::Unreal;
namespace fs = std::filesystem;

static_assert(std::is_same_v<RC::StringType, std::wstring>, "Installed UE4SS uses wchar_t strings; do not define FORCE_U16.");
static_assert(_ITERATOR_DEBUG_LEVEL == 0, "Installed UE4SS uses release MSVC containers.");
static_assert(sizeof(RC::CppUserModBase) == 192, "CppUserModBase must match the installed UE4SS c0a8d4c layout.");
static_assert(sizeof(void*) == 8, "x64 only.");

constexpr wchar_t ModVersionText[] = L"3.5.3";
constexpr size_t PostLoadSlot = 0x78 / sizeof(void*); // UObject::PostLoad per Rebirth's VTableLayout.ini; verified below
constexpr uint64_t PumpIntervalMs = 250;
constexpr int32_t MaxBones = 8192;

const EObjectFlags DeadFlags = static_cast<EObjectFlags>(RF_BeginDestroyed | RF_FinishDestroyed);
const EObjectFlags TemplateFlags = static_cast<EObjectFlags>(RF_ClassDefaultObject | RF_ArchetypeObject);
const EObjectFlags NotReadyFlags = static_cast<EObjectFlags>(RF_ClassDefaultObject | RF_ArchetypeObject | RF_BeginDestroyed |
                                                             RF_FinishDestroyed | RF_NeedInitialization | RF_NeedLoad |
                                                             RF_NeedPostLoad | RF_NeedPostLoadSubobjects);

// ---------------------------------------------------------------------------------------
// Logging (own file next to the mod; UE4SS hot reload never truncates it mid-session)
// ---------------------------------------------------------------------------------------
class Logger
{
public:
    void Open(const fs::path& path)
    {
        std::lock_guard lock(Mutex);
        File.open(path, std::ios::binary | std::ios::trunc);
    }

    void Line(const std::wstring& text)
    {
        SYSTEMTIME t{};
        GetLocalTime(&t);
        wchar_t stamp[32]{};
        swprintf_s(stamp, L"[%02u:%02u:%02u.%03u] ", t.wHour, t.wMinute, t.wSecond, t.wMilliseconds);
        const std::string utf8 = SkelCompat::Narrow(std::wstring(stamp) + text + L"\n");
        {
            std::lock_guard lock(Mutex);
            if (File.is_open())
            {
                File.write(utf8.data(), static_cast<std::streamsize>(utf8.size()));
                File.flush();
            }
        }
        OutputDebugStringW((L"[RebirthSkelCompat] " + text + L"\n").c_str());
    }

private:
    std::mutex Mutex;
    std::ofstream File;
};

Logger Log;

std::wstring Hex(uintptr_t value)
{
    wchar_t buffer[32]{};
    swprintf_s(buffer, L"0x%llX", static_cast<unsigned long long>(value));
    return buffer;
}

// ---------------------------------------------------------------------------------------
// Guarded memory access for pointers that are not known to be live
// ---------------------------------------------------------------------------------------
bool SafeCopy(void* destination, const void* source, size_t size)
{
    SIZE_T copied = 0;
    return source && ReadProcessMemory(GetCurrentProcess(), source, destination, size, &copied) && copied == size;
}

template <class T>
bool ReadAt(const void* base, size_t offset, T& out)
{
    return base && SafeCopy(&out, static_cast<const uint8_t*>(base) + offset, sizeof(T));
}

// Direct read from an object the engine is currently handing us (known live).
template <class T>
T Field(const void* base, int32_t offset)
{
    T value{};
    std::memcpy(&value, static_cast<const uint8_t*>(base) + offset, sizeof(T));
    return value;
}

struct RawArray
{
    void* Data = nullptr;
    int32_t Num = 0;
    int32_t Max = 0;
};
static_assert(sizeof(RawArray) == 16);

struct ImageRange
{
    uintptr_t Begin = 0;
    uintptr_t End = 0;
    bool Contains(const void* p) const
    {
        const auto v = reinterpret_cast<uintptr_t>(p);
        return v >= Begin && v < End;
    }
};

ImageRange MainImage()
{
    ImageRange range;
    const auto* base = reinterpret_cast<const uint8_t*>(GetModuleHandleW(nullptr));
    IMAGE_DOS_HEADER dos{};
    IMAGE_NT_HEADERS64 nt{};
    if (!base || !SafeCopy(&dos, base, sizeof(dos)) || dos.e_magic != IMAGE_DOS_SIGNATURE ||
        !SafeCopy(&nt, base + dos.e_lfanew, sizeof(nt)) || nt.Signature != IMAGE_NT_SIGNATURE)
    {
        return range;
    }
    range.Begin = reinterpret_cast<uintptr_t>(base);
    range.End = range.Begin + nt.OptionalHeader.SizeOfImage;
    return range;
}

// ---------------------------------------------------------------------------------------
// Reflection and object helpers.
// UObject::IsReal walks the whole object array, so it is only used for pointers that may be
// stale (queues processed by the pump), never on the per-mesh load path.
// ---------------------------------------------------------------------------------------
FProperty* FindField(UStruct* owner, const wchar_t* name)
{
    if (!owner) { return nullptr; }
    int count = 0;
    for (FProperty* property : owner->ForEachPropertyInChain())
    {
        if (++count > 4096) { break; }
        if (property && property->GetName() == name) { return property; }
    }
    return nullptr;
}

std::wstring TypeOf(FProperty* property) { return property ? property->GetClass().GetName() : std::wstring{}; }

int32_t FieldOffset(UStruct* owner, const wchar_t* name, std::initializer_list<const wchar_t*> types, int32_t size)
{
    FProperty* property = FindField(owner, name);
    if (!property || property->GetArrayDim() != 1 || property->GetElementSize() != size) { return -1; }
    const std::wstring type = TypeOf(property);
    if (std::none_of(types.begin(), types.end(), [&](const wchar_t* t) { return type == t; })) { return -1; }
    const int32_t offset = property->GetOffset_Internal();
    const int32_t limit = owner->GetPropertiesSize();
    return (offset >= 0 && offset + size <= limit) ? offset : -1;
}

// Path of an object known to be live.
std::wstring ObjectPath(UObject* object) { return object ? object->GetPathName() : std::wstring{}; }

// Object name (no path): one FName::ToString, cheap.
std::wstring ShortName(UObject* object) { return object ? object->GetNamePrivate().ToString() : std::wstring{}; }

std::wstring ShortNameOfPath(const std::wstring& path)
{
    const size_t dot = path.find_last_of(L'.');
    const size_t slash = path.find_last_of(L'/');
    if (dot != std::wstring::npos && (slash == std::wstring::npos || dot > slash)) { return path.substr(dot + 1); }
    return slash == std::wstring::npos ? path : path.substr(slash + 1);
}

std::wstring Folded(const std::wstring& text) { return SkelCompat::FoldedKey(text); }

bool Alive(UObject* object) { return object && UObject::IsReal(object) && !object->HasAnyFlags(DeadFlags); }
bool FlagsReady(UObject* object) { return object && !object->HasAnyFlags(NotReadyFlags); }

// Path of an object that may be stale (pump / report only).
std::wstring PathOf(UObject* object)
{
    try
    {
        return (object && UObject::IsReal(object)) ? object->GetPathName() : std::wstring{};
    }
    catch (...)
    {
        return {};
    }
}

UObject* FindObjectByPath(const wchar_t* path)
{
    UObject* object = UObjectGlobals::StaticFindObject(nullptr, nullptr, path);
    return (object && UObject::IsReal(object)) ? object : nullptr;
}

UClass* FindClass(const wchar_t* path)
{
    UObject* object = FindObjectByPath(path);
    return (object && object->IsA<UClass>()) ? static_cast<UClass*>(object) : nullptr;
}

// ---------------------------------------------------------------------------------------
// FReferenceSkeleton reader. Layout in UE 4.26 shipping: four TArrays (raw/final bone info and
// poses), two TMaps, two TArrays, one bool. FMeshBoneInfo = { FName Name; int32 ParentIndex; }.
// ---------------------------------------------------------------------------------------
static_assert(sizeof(FName) == 8, "Retail Rebirth uses 8-byte FNames (ComparisonIndex + Number).");
constexpr size_t BoneInfoStride = (sizeof(FName) + sizeof(int32_t) + 3) & ~size_t{3};

bool ReadRefSkeleton(const void* owner, size_t offset, SkelCompat::BoneTable& out)
{
    RawArray raw{}, rawPose{}, finalInfo{}, finalPose{};
    if (!ReadAt(owner, offset, raw) || !ReadAt(owner, offset + 0x10, rawPose) || !ReadAt(owner, offset + 0x20, finalInfo) ||
        !ReadAt(owner, offset + 0x30, finalPose))
    {
        return false;
    }
    if (raw.Num <= 0 || raw.Num > MaxBones || raw.Max < raw.Num || !raw.Data) { return false; }
    if (rawPose.Num != raw.Num || rawPose.Max < rawPose.Num || !rawPose.Data) { return false; }
    if (finalInfo.Num < raw.Num || finalInfo.Num > raw.Num + 1024 || finalInfo.Max < finalInfo.Num || !finalInfo.Data) { return false; }
    if (finalPose.Num != finalInfo.Num || finalPose.Max < finalPose.Num || !finalPose.Data) { return false; }
    std::array<uint8_t, 16> probe{};
    if (!SafeCopy(probe.data(), rawPose.Data, probe.size()) || !SafeCopy(probe.data(), finalPose.Data, probe.size())) { return false; }

    std::vector<uint8_t> bytes(static_cast<size_t>(finalInfo.Num) * BoneInfoStride);
    if (!SafeCopy(bytes.data(), finalInfo.Data, bytes.size())) { return false; }

    // Validate the hierarchy before touching any name: random memory almost never forms a tree.
    std::vector<int32_t> parents(static_cast<size_t>(finalInfo.Num));
    for (int32_t i = 0; i < finalInfo.Num; ++i)
    {
        int32_t parent = 0;
        std::memcpy(&parent, bytes.data() + static_cast<size_t>(i) * BoneInfoStride + sizeof(FName), sizeof(parent));
        if ((i == 0 && parent != -1) || (i > 0 && (parent < 0 || parent >= i))) { return false; }
        parents[static_cast<size_t>(i)] = parent;
    }

    SkelCompat::BoneTable table;
    table.Parents = std::move(parents);
    table.RawCount = raw.Num;
    table.Names.reserve(static_cast<size_t>(finalInfo.Num));
    for (int32_t i = 0; i < finalInfo.Num; ++i)
    {
        FName name{};
        std::memcpy(static_cast<void*>(&name), bytes.data() + static_cast<size_t>(i) * BoneInfoStride, sizeof(FName));
        std::wstring text = name.ToString();
        if (text.empty() || text == L"None") { return false; }
        table.Names.push_back(std::move(text));
    }
    if (!table.Valid()) { return false; }
    out = std::move(table);
    return true;
}

// ---------------------------------------------------------------------------------------
// Mod state
// ---------------------------------------------------------------------------------------
struct VTablePatch
{
    void** Table = nullptr;
    void* Original = nullptr;
};

struct ReboundMesh
{
    UObject* Mesh = nullptr;
    UObject* Target = nullptr;
    std::vector<UObject*> KeepCompatible; // AnimBlueprints made for these skeletons must still accept the mesh
    bool Family = false;            // family member: the mesh may also run its own character's AnimBlueprint
    std::wstring MeshPath;
    std::wstring FromSkeleton;
    std::wstring ToSkeleton;
    bool Late = false;
    bool Diagnosed = false;
    int32_t Attempts = 0;
    std::wstring Diagnosis;
    bool FixHierarchy = true;
    int32_t Renamed = -1;           // bones renamed by the hierarchy fix; -1 = not applied
    std::wstring HierarchyNote;     // what the hierarchy fix did
    std::wstring SocketNote;        // sockets of the mesh's own skeleton kept on it
};

enum class PathKind : uint8_t
{
    None,
    Soft,
    Hard,
    String,
    Name
};

struct PathField
{
    int32_t Offset = -1;
    int32_t Stride = 0;
    PathKind Kind = PathKind::None;
};

// What an AssetUserData class offers (cached per class; validated by the class's FName).
struct CarrierInfo
{
    std::array<uint8_t, sizeof(FName)> ClassName{};
    bool IsCarrier = false;
    PathField Animation;
    PathField Meshes;
};

// One animation skeleton's animations adopted by one receiving skeleton (KH3 mode). Immutable once published,
// except the counters; read from the async loading thread.
struct AdoptionPlan
{
    UObject* From = nullptr;                          // animation skeleton (rooted)
    UObject* To = nullptr;                            // receiving skeleton (rooted)
    std::wstring FromPath;
    std::wstring ToPath;
    std::vector<int32_t> TrackMap;                    // from bone index -> to bone index, or -1 (track dropped)
    std::unordered_map<uint64_t, uint16_t> CurveUids; // raw FName of a receiving-skeleton curve -> its UID
    bool CurvesKnown = false;                         // false: curve UIDs could not be read, curves are dropped
    std::unordered_map<uint64_t, int32_t> ToBoneIndex;// raw FName of a receiving-skeleton bone -> its index
    std::vector<std::wstring> Paths;                  // adopt_paths (empty = every asset of From)
    size_t PairIndex = 0;                             // config order decides which pair gets an animation first
    bool Family = false;                              // From is a family member, To its hub (From's meshes are rebound to To)
    std::array<uint8_t, 16> ToVirtualBoneGuid{};      // receiving skeleton's VirtualBoneGuid, written into adopted assets
    bool WriteVirtualBoneGuid = false;
    std::wstring Summary;
    bool KeepProportions = false;                     // 3.2: adopted sequences name From's retarget pose on To (RetargetSource)
    uint64_t RetargetName = 0;                        // raw FName of From: the key of that pose
    mutable std::atomic<uint64_t> RetargetReplaced{0};// adopted sequences whose own RetargetSource was replaced
    mutable std::atomic<uint64_t> Adopted{0};
    mutable std::atomic<uint64_t> Refused{0};
    mutable std::atomic<uint64_t> CurvesDropped{0};        // curve tracks of adopted assets the receiving skeleton does not know
    mutable std::atomic<uint64_t> AssetsDroppingCurves{0}; // adopted assets with at least one such curve
    mutable std::atomic<bool> MemberMeshAlive{false};      // family: the last late pass saw a live mesh still on From
};

struct AdoptionTable
{
    std::vector<std::shared_ptr<AdoptionPlan>> Plans;
};

enum class AnimKind : uint8_t
{
    Other,      // not adopted (pose assets, streamable animations, ...)
    Sequence,
    Composite,
    Montage,
    BlendSpace
};

// A montage, composite or blend space whose animations are not all on the receiving skeleton yet. Rooted by the
// mod while it waits, so the pointer stays valid; adopted as soon as its last animation arrives.
struct WaitingContainer
{
    UObject* Asset = nullptr;
    AnimKind Kind = AnimKind::Other;
    const AdoptionPlan* Plan = nullptr;
    std::wstring Path;
    std::vector<UObject*> Children;
    bool RootedByMod = false;
};

struct ModState
{
    std::mutex Mutex;
    SkelCompat::Config Config;                               // immutable after Initialize
    std::unordered_set<std::wstring> ReceivingNames;         // folded short names of JSON receiving skeletons (immutable)
    fs::path ModDirectory;
    fs::path GameContentPaks;

    UClass* SkeletonClass = nullptr;
    UClass* MeshClass = nullptr;
    UClass* ComponentClass = nullptr;
    UFunction* SetAnimClass = nullptr;
    UFunction* MakeSoftObjectPath = nullptr;
    UFunction* ConvertSoftObjectPath = nullptr;
    UFunction* LoadAssetBlocking = nullptr;
    UObject* KismetSystemLibrary = nullptr;
    int32_t OffMeshSkeleton = -1;
    int32_t OffCompMesh = -1;
    int32_t OffCompAnimClass = -1;
    int32_t OffCompAnimInstance = -1;
    int32_t OffSkelRefLocalPoses = -1;
    int32_t OffSkelVirtualBones = -1;
    int32_t OffSkelUserData = -1;
    int32_t OffMeshUserData = -1;
    int32_t OffMeshSockets = -1;                             // USkeletalMesh::Sockets (TArray<USkeletalMeshSocket*>)
    int32_t OffSkelSockets = -1;                             // USkeleton::Sockets
    int32_t OffSocketName = -1;                              // USkeletalMeshSocket::SocketName
    int32_t OffSocketBone = -1;                              // USkeletalMeshSocket::BoneName
    std::atomic<int32_t> MeshRefSkeletonOffset{-1};

    std::array<VTablePatch, 16> Patches{};
    std::atomic<int32_t> PatchCount{0};

    std::atomic<bool> Enabled{false};                        // startup succeeded, waiting for / done with game-thread setup
    std::atomic<bool> Active{false};                         // fully set up on the game thread and not faulted
    std::atomic<bool> Faulted{false};
    std::atomic<DWORD> GameThread{0};
    std::atomic<bool> Work{false};
    std::atomic<bool> ReportRequested{false};
    bool LateInitDone = false;
    bool StartupScanDone = false;
    bool PreloadDone = false;
    uint64_t NextPumpMs = 0;

    // Animation skeletons. Rooted ones are kept alive by the mod, so their pointers stay valid.
    std::unordered_map<std::wstring, UObject*> Rooted;       // folded path -> rooted, fully loaded skeleton
    std::vector<std::wstring> LoadQueue;                     // paths the pump should find or load
    std::vector<std::wstring> LoadAttempted;                 // folded paths already loaded (or tried) by the mod
    std::vector<UObject*> Pending;                           // receiving meshes waiting for their animation skeleton
    uint64_t RootedVersion = 0;                              // bumped whenever a skeleton becomes resident (game thread)
    uint64_t PendingVersion = 0;                             // RootedVersion the pending list was last checked against
    std::vector<ReboundMesh> Rebound;
    int32_t Repaired = 0;

    std::mutex CarrierMutex;
    std::unordered_map<UClass*, CarrierInfo> Carriers;

    std::atomic<uint64_t> PostLoadCalls{0};
    std::atomic<uint64_t> PostLoadTicks{0};
    std::atomic<uint64_t> PostLoadMaxTicks{0};
    std::atomic<uint64_t> SkeletonNotLoaded{0};

    bool Busy = false;                                       // game thread re-entrancy guard
    bool HookInstalled = false;

    // Animation adoption (KH3 mode)
    UClass* AnimAssetClass = nullptr;                        // UAnimationAsset
    UClass* AnimSequenceClass = nullptr;                     // UAnimSequence
    UClass* AnimCompositeClass = nullptr;                    // UAnimComposite
    UClass* AnimMontageClass = nullptr;                      // UAnimMontage
    UClass* BlendSpaceBaseClass = nullptr;                   // UBlendSpaceBase
    int32_t OffAnimSkeleton = -1;                            // UAnimationAsset::Skeleton
    int32_t OffAnimVirtualBoneGuid = -1;                     // UAnimationAsset::SkeletonVirtualBoneGuid (not reflected)
    int32_t OffSkelVirtualBoneGuid = -1;                     // USkeleton::VirtualBoneGuid
    int32_t OffSeqBlendOut = -1;                             // UAnimSequenceBase::OverrideBehaviorActionBlendOutSequence (Rebirth)
    int32_t OffSeqRefPose = -1;                              // UAnimSequence::RefPoseSeq (additive base)
    int32_t OffSeqCompressed = -1;                           // UAnimSequence::CompressedData (track table, then curve names)
    int32_t OffSeqRawTracks = -1;                            // UAnimSequence::TrackToSkeletonMapTable
    int32_t OffSeqCustomAttrs = -1;                          // UAnimSequence::BakedPerBoneCustomAttributeData
    int32_t SeqCustomAttrStride = 0;
    int32_t AttrBone = -1;                                   // FBakedCustomAttributePerBoneData::BoneTreeIndex (-1: unknown)
    std::array<int32_t, 3> AttrArrays{-1, -1, -1};           // its String/Int/Float attribute arrays (-1: unknown)
    int32_t OffRawFloatCurves = -1;                          // UAnimSequenceBase::RawCurveData.FloatCurves
    int32_t FloatCurveStride = 0;
    int32_t FloatCurveName = -1;                             // FFloatCurve::Name (FSmartName)
    int32_t OffCompositeTrack = -1;                          // UAnimComposite::AnimationTrack (FAnimTrack)
    int32_t OffMontageSlots = -1;                            // UAnimMontage::SlotAnimTracks
    int32_t SlotStride = 0;
    int32_t SlotTrack = -1;                                  // FSlotAnimationTrack::AnimTrack
    int32_t TrackSegments = -1;                              // FAnimTrack::AnimSegments
    int32_t SegmentStride = 0;
    int32_t SegmentRef = -1;                                 // FAnimSegment::AnimReference
    int32_t OffBlendSamples = -1;                            // UBlendSpaceBase::SampleData
    int32_t SampleStride = 0;
    int32_t SampleAnim = -1;                                 // FBlendSample::Animation
    int32_t OffBlendPerBone = -1;                            // UBlendSpaceBase::PerBoneBlend
    int32_t BlendPerBoneStride = 0;
    int32_t PerBoneRef = -1;                                 // FPerBoneInterpolation::BoneReference (FName, then BoneIndex:31)
    int32_t OffSkelSmartNames = -1;                          // USkeleton::SmartNames, followed by AnimCurveMapping*
    std::array<VTablePatch, 64> AnimPatches{};
    std::atomic<int32_t> AnimPatchCount{0};
    bool AnimHooksInstalled = false;
    std::atomic<const AdoptionTable*> Adoption{nullptr};     // published plans (never freed during the session)
    std::vector<std::unique_ptr<AdoptionTable>> AdoptionTables;
    std::vector<std::wstring> AdoptionFailed;                // folded animation-skeleton paths that cannot be planned
    uint64_t AdoptionVersion = ~0ull;                        // RootedVersion the plans were last built for
    std::mutex AdoptMutex;                                   // guards adoption and Waiting (loading thread vs. game thread)
    std::vector<WaitingContainer> Waiting;                   // containers whose animations have not all arrived
    std::atomic<int32_t> WaitingCount{0};                    // Waiting.size(), readable without the lock
    uint64_t NextWaitingCheck = 0;
    std::atomic<bool> LatePassWanted{false};                 // already-loaded animations need the game-thread pass
    std::atomic<bool> ViewportSafePoint{false};              // the after-world-tick callback is running
    uint64_t LatePassNotBefore = 0;
    uint64_t LatePassBackoffMs = 0;
    int32_t LateFollowUps = 0;                               // extra passes after a plan is published (assets still loading)
    uint64_t LatePasses = 0;
    std::atomic<int32_t> FamilyGated{0};                     // family animations the last late pass left (member character alive)

    // Animation set rows (3.1)
    UClass* AnimSetClass = nullptr;                          // UEndAnimSet
    UClass* PackClass = nullptr;                             // UEndAssetDataAsset (CharaSpec packs)
    int32_t OffSetAssets = -1;                               // UEndAnimSet::AnimationAssets (TMap<FName, UAnimationAsset*>)
    int32_t OffSetDisplayName = -1;                          // UEndAnimSet::DisplayName
    int32_t OffPackList = -1;                                // UEndAssetDataAsset::AssetDataList (TArray<FEndAssetData>)
    int32_t PackEntryStride = 0;
    int32_t OffEntryObjects = -1;                            // FEndAssetData::AssetUserData (TArray<UObject*>)
    std::array<VTablePatch, 8> PackPatches{};
    std::atomic<int32_t> PackPatchCount{0};
    bool PackHookInstalled = false;

    // 3.2.1: AnimBlueprints made for a family member's skeleton follow the hub. The engine runs an AnimBlueprint only on
    // meshes of the skeleton it targets (USkeleton::IsCompatible), and a family rebinds every member mesh to the hub, so
    // a member character that keeps its own AnimBlueprint (Vincent's Blueprint in Cloud's slot) would T-pose.
    UClass* AbpClass = nullptr;                              // UAnimBlueprintGeneratedClass
    int32_t OffAbpTargetSkeleton = -1;                       // UAnimBlueprintGeneratedClass::TargetSkeleton
    std::unordered_map<std::wstring, std::wstring> AbpHubs;  // folded member skeleton path -> hub path (immutable)
    std::array<VTablePatch, 8> AbpPatches{};
    std::atomic<int32_t> AbpPatchCount{0};
    std::mutex AbpMutex;
    std::vector<UObject*> AbpMoved;                          // AnimBlueprint classes moved to a hub (AbpMutex)
    std::vector<std::wstring> AbpLines;                      // what was moved, for the report (AbpMutex)
    std::atomic<bool> AbpRepairWanted{false};                // live components may wait for a moved class (game thread)
    int32_t AbpRepaired = 0;
    bool SetsPreloaded = false;
    std::atomic<bool> SetsReady{false};                      // sources are resident: packs are merged from now on
    std::unordered_set<std::wstring> PackNames;              // folded object names of the packs rows name (immutable)
    std::unordered_map<std::wstring, UObject*> SetObjects;   // folded source set path -> resident set (null: not found)
    std::unordered_map<std::wstring, int32_t> SetKeys;       // folded source set path -> animations in it (-1: unreadable)
    std::unordered_map<std::wstring, UObject*> MoveObjects;  // folded animation path -> resident animation (null: not found)
    std::vector<std::wstring> SetLines;                      // what the rows found, for the report
    std::vector<std::wstring> MergeLines;                    // packs merged so far, for the report
    std::vector<UObject*> MergedPacks;                       // packs merged by the late pass (never merged twice)
    std::mutex PackMutex;
    std::vector<UObject*> PacksToMerge;                      // packs post-loaded off the game thread (merged by the pump)
    std::atomic<uint64_t> PacksMerged{0};

    // 3.2: auto match
    UClass* AnimSequenceBaseClass = nullptr;                 // UAnimSequenceBase
    int32_t OffSeqLength = -1;                               // UAnimSequenceBase::SequenceLength
    int32_t OffSeqAdditiveType = -1;                         // UAnimSequence::AdditiveAnimType
    // 3.2: chained moves (an AnimComposite built at run time)
    int32_t SegStartPos = -1;                                // FAnimSegment::StartPos
    int32_t SegAnimStart = -1;                               // FAnimSegment::AnimStartTime
    int32_t SegAnimEnd = -1;                                 // FAnimSegment::AnimEndTime
    int32_t SegPlayRate = -1;                                // FAnimSegment::AnimPlayRate
    int32_t SegLooping = -1;                                 // FAnimSegment::LoopingCount
    int32_t SegBlendTime = -1;                               // FAnimSegment::AnimBlendTime (Rebirth; -1 when absent)
    int32_t SegTriggerNotify = -1;                           // FAnimSegment::bTriggerAnimReferenceNotify (Rebirth; -1 when absent)
    int32_t SegValid = -1;                                   // FAnimSegment::bValid (private, unreflected: right after the last property)
    std::vector<uint8_t> SegmentTemplate;                    // a segment of a loaded montage, when one was seen (engine-made bytes)
    std::unordered_map<std::wstring, UObject*> ChainObjects; // folded chain paths -> composite built for it (null: could not)
    // 3.2: socket stand-ins
    UClass* SocketClass = nullptr;                           // USkeletalMeshSocket
    std::unordered_set<std::wstring> AliasSkeletonNames;     // folded short names of skeletons whose meshes get stand-ins (immutable)
    // 3.2: proportions
    int32_t OffSkelBoneTree = -1;                            // USkeleton::BoneTree (TArray<FBoneNode>)
    int32_t BoneNodeStride = 0;
    int32_t BoneNodeMode = -1;                               // FBoneNode::TranslationRetargetingMode
    int32_t OffSkelRetargetSources = -1;                     // USkeleton::AnimRetargetSources (native TMap right after Sockets)
    int32_t OffSeqRetargetSource = -1;                       // UAnimSequence::RetargetSource
    std::vector<std::wstring> ProportionSkeletons;           // skeletons that get the proportion modes (immutable)
    std::vector<UObject*> ProportionsDone;                   // skeletons whose modes are set (game thread)
    struct PoseToAdd
    {
        UObject* Skeleton = nullptr;                         // receiving skeleton (rooted)
        uint64_t Name = 0;                                   // raw FName key (the animation skeleton's name)
        std::vector<uint8_t> Pose;                           // FTransforms, one per receiving bone
        std::wstring Label;
    };
    std::vector<PoseToAdd> PosesToAdd;                       // retarget poses waiting for a safe point (game thread)
    std::atomic<bool> ProportionsWanted{false};              // modes or poses to apply at the next safe point
    uint64_t ProportionsVersion = ~0ull;                     // RootedVersion the configured skeletons were last looked for at
    std::vector<std::wstring> ProportionLines;               // for the report

    // 3.3: abilities per animation pack (game thread only)
    UFunction* SetPrimaryAnimPack = nullptr;                 // EndBattleAPI:SetPrimaryAnimPack
    UFunction* ResetPrimaryAnimPack = nullptr;               // EndBattleAPI:ResetPrimaryAnimPack
    UFunction* GetCharaSpecName = nullptr;                   // EndBattleAPI:GetCharaSpecName
    UObject* BattleApi = nullptr;                            // Default__EndBattleAPI
    UFunction* GetPlayerLevel = nullptr;                     // EndMenuBPAPI:BPGetPlayerLevel
    UFunction* GetPlayerExperience = nullptr;                // EndMenuBPAPI:BPGetPlayerExperience
    UFunction* SetPlayerExperience = nullptr;                // EndMenuBPAPI:BPSetPlayerExperience (EXP := value, recalculates the status)
    bool RefreshProblem = false;                             // a recalculation changed the level or EXP: no more this session
    std::wstring RefreshText;
    struct PackCall
    {
        UObject* Character = nullptr;
        std::wstring Pack;
        bool Reset = false;
    };
    std::vector<PackCall> QueuedPackCalls;                   // 3.4: pack switches made while the mod was busy (game thread)
    UObject* MenuApi = nullptr;                              // Default__EndMenuBPAPI
    bool AbilitiesWanted = false;                            // a row has "abilities" and the functions were found
    bool AbilitiesSwitched = false;                          // lists were written since the last map load
    std::vector<std::wstring> UnlistedPackWarnings;          // spec/pack pairs warned about (not in the row's AnimationSetList)
    struct TableArray
    {
        uintptr_t At = 0;                                    // the array {ptr, num, max} inside a table row
        std::array<uint8_t, 16> Original{};                  // as the game loaded it
    };
    std::vector<TableArray> AbilityOriginals;
    std::unordered_map<std::wstring, std::unique_ptr<std::vector<uint64_t>>> AbilityLists; // lists the rows point at (session)
    std::vector<std::wstring> AbilityLines;                  // for the report (last switches)
};

ModState State;

std::wstring PostLoadStats();

void RequestWork() { State.Work.store(true, std::memory_order_release); }

// Any error inside the mod: switch it off for the rest of the session, keep the game running.
void Fault(const wchar_t* where)
{
    if (!State.Active.exchange(false)) { return; }
    State.Faulted.store(true);
    try
    {
        Log.Line(std::wstring(L"ERROR inside ") + where + L". RebirthSkelCompat switched itself off for this session; the game continues unmodified.");
    }
    catch (...)
    {
    }
}

// Registers the animation skeletons of a pair as "of interest" and queues the ones not resident yet.
void WantPair(const SkelCompat::Pair& pair)
{
    std::lock_guard lock(State.Mutex);
    std::vector<std::wstring> wanted = pair.Animation;
    if (pair.Use == SkelCompat::Method::Animations) { wanted.push_back(pair.Receiving); } // adoption needs both skeletons resident
    for (const auto& path : wanted)
    {
        const std::wstring key = Folded(path);
        const bool rooted = State.Rooted.count(key) > 0;
        const bool tried = std::find(State.LoadAttempted.begin(), State.LoadAttempted.end(), key) != State.LoadAttempted.end();
        const bool queued = std::any_of(State.LoadQueue.begin(), State.LoadQueue.end(), [&](const std::wstring& q) { return Folded(q) == key; });
        if (!rooted && !tried && !queued) { State.LoadQueue.push_back(path); }
    }
}

// First animation skeleton of the pair that the mod holds (rooted and fully loaded). No slow lookups.
UObject* RootedAnimationSkeleton(const SkelCompat::Pair& pair, std::wstring* chosenPath)
{
    std::lock_guard lock(State.Mutex);
    for (const auto& path : pair.Animation)
    {
        const auto it = State.Rooted.find(Folded(path));
        if (it != State.Rooted.end() && FlagsReady(it->second))
        {
            if (chosenPath) { *chosenPath = path; }
            return it->second;
        }
    }
    return nullptr;
}

// ---------------------------------------------------------------------------------------
// Pairs declared inside the pak: an AssetUserData Blueprint (parent: native AssetUserData) on the
// receiving skeleton or on the mesh, with an array "AnimationSkeletons" (or "CompatibleSkeletons")
// of object paths (strings or names) or Skeleton soft/hard references, and an optional
// "ReceivingMeshes" array. Same place KH3 keeps SQEX_CompatibleSkeletonLists.
// ---------------------------------------------------------------------------------------
PathField DescribePathArray(UStruct* type, const wchar_t* name)
{
    PathField field;
    FProperty* property = FindField(type, name);
    if (!property || TypeOf(property) != L"ArrayProperty" || property->GetElementSize() != static_cast<int32_t>(sizeof(RawArray))) { return field; }
    FProperty* inner = static_cast<FArrayProperty*>(property)->GetInner();
    if (!inner) { return field; }
    const std::wstring innerType = TypeOf(inner);
    const int32_t stride = inner->GetElementSize();
    PathKind kind = PathKind::None;
    if (innerType == L"SoftObjectProperty" && stride == 40) { kind = PathKind::Soft; }
    else if (innerType == L"ObjectProperty" && stride == 8) { kind = PathKind::Hard; }
    else if (innerType == L"StrProperty" && stride == static_cast<int32_t>(sizeof(RawArray))) { kind = PathKind::String; }
    else if (innerType == L"NameProperty" && stride == static_cast<int32_t>(sizeof(FName))) { kind = PathKind::Name; }
    const int32_t offset = property->GetOffset_Internal();
    if (kind == PathKind::None || offset < 0 || offset + static_cast<int32_t>(sizeof(RawArray)) > type->GetPropertiesSize()) { return field; }
    field.Offset = offset;
    field.Stride = stride;
    field.Kind = kind;
    return field;
}

CarrierInfo CarrierInfoFor(UClass* type)
{
    CarrierInfo info;
    if (!type) { return info; }
    std::memcpy(info.ClassName.data(), &type->GetNamePrivate(), sizeof(FName));
    {
        std::lock_guard lock(State.CarrierMutex);
        const auto it = State.Carriers.find(type);
        if (it != State.Carriers.end() && it->second.ClassName == info.ClassName) { return it->second; }
    }
    info.Animation = DescribePathArray(type, L"AnimationSkeletons");
    if (info.Animation.Kind == PathKind::None) { info.Animation = DescribePathArray(type, L"CompatibleSkeletons"); }
    info.Meshes = DescribePathArray(type, L"ReceivingMeshes");
    info.IsCarrier = info.Animation.Kind != PathKind::None;
    std::lock_guard lock(State.CarrierMutex);
    State.Carriers[type] = info;
    return info;
}

std::wstring ReadFString(const uint8_t* at)
{
    RawArray header{};
    if (!SafeCopy(&header, at, sizeof(header)) || header.Num <= 1 || header.Num > 1024 || header.Max < header.Num || !header.Data)
    {
        return {};
    }
    std::wstring text(static_cast<size_t>(header.Num), L'\0');
    if (!SafeCopy(text.data(), header.Data, text.size() * sizeof(wchar_t))) { return {}; }
    text.resize(std::wcslen(text.c_str())); // FString counts its terminator
    return text;
}

std::vector<std::wstring> ReadPaths(UObject* owner, const PathField& field)
{
    std::vector<std::wstring> paths;
    if (field.Kind == PathKind::None) { return paths; }
    RawArray array{};
    if (!ReadAt(owner, static_cast<size_t>(field.Offset), array) || array.Num <= 0 || array.Num > 64 || !array.Data) { return paths; }
    for (int32_t i = 0; i < array.Num; ++i)
    {
        const auto* element = static_cast<const uint8_t*>(array.Data) + static_cast<size_t>(i) * static_cast<size_t>(field.Stride);
        std::wstring path;
        if (field.Kind == PathKind::Soft || field.Kind == PathKind::Name)
        {
            // TSoftObjectPtr = { FWeakObjectPtr (8); int32 Tag; pad; FSoftObjectPath { FName AssetPathName; FString SubPath; } }
            FName value{};
            if (SafeCopy(&value, element + (field.Kind == PathKind::Soft ? 16 : 0), sizeof(FName))) { path = value.ToString(); }
        }
        else if (field.Kind == PathKind::String)
        {
            path = ReadFString(element);
        }
        else
        {
            UObject* object = nullptr;
            if (ReadAt(element, 0, object) && object) { path = ObjectPath(object); }
        }
        path = SkelCompat::NormalizeObjectPath(path);
        if (!path.empty()) { paths.push_back(std::move(path)); }
    }
    return paths;
}

// Looks for a carrier among owner's AssetUserData. Direct reads only (owner is live).
bool CarrierPair(UObject* owner, int32_t userDataOffset, UObject* skeleton, std::wstring& skeletonPath, SkelCompat::Pair& out)
{
    if (userDataOffset < 0) { return false; }
    const RawArray array = Field<RawArray>(owner, userDataOffset);
    if (array.Num <= 0 || array.Num > 32 || !array.Data) { return false; }
    for (int32_t i = 0; i < array.Num; ++i)
    {
        UObject* data = static_cast<UObject* const*>(array.Data)[i];
        if (!data || data->HasAnyFlags(DeadFlags)) { continue; }
        const CarrierInfo info = CarrierInfoFor(data->GetClassPrivate());
        if (!info.IsCarrier) { continue; }
        if (skeletonPath.empty()) { skeletonPath = SkelCompat::NormalizeObjectPath(ObjectPath(skeleton)); }
        SkelCompat::Pair result;
        result.Use = SkelCompat::Method::Mesh; // carriers are found when a mesh loads: they always rebind that mesh
        result.Receiving = skeletonPath;
        result.Origin = L"AssetUserData on " + ShortName(owner);
        for (auto& listed : ReadPaths(data, info.Animation))
        {
            // Like JSON "mesh" pairs, the meshes follow animations an "animations" pair (or a family) took over
            // completely, and stay compatible with the AnimBlueprints of the skeleton they were made for.
            std::wstring path = SkelCompat::FollowAdoption(State.Config, listed);
            if (!SkelCompat::PathEquals(path, listed)) { SkelCompat::Detail::AddUnique(result.KeepCompatible, listed); }
            const bool duplicate = std::any_of(result.Animation.begin(), result.Animation.end(),
                                               [&](const std::wstring& a) { return SkelCompat::PathEquals(a, path); });
            if (!duplicate && !SkelCompat::PathEquals(path, skeletonPath)) { result.Animation.push_back(std::move(path)); }
        }
        result.Meshes = ReadPaths(data, info.Meshes);
        if (result.Animation.empty()) { continue; }
        out = std::move(result);
        return true;
    }
    return false;
}

// The pair this mesh takes part in, if any. Cheap when nothing applies: a few direct reads and,
// only if JSON pairs exist, one FName::ToString of the skeleton's name.
const SkelCompat::Pair* QuickPair(UObject* mesh, UObject* skeleton, std::wstring& skeletonPath, SkelCompat::Pair& storage)
{
    if (!State.ReceivingNames.empty() && State.ReceivingNames.count(Folded(ShortName(skeleton))) > 0)
    {
        skeletonPath = SkelCompat::NormalizeObjectPath(ObjectPath(skeleton));
        if (const SkelCompat::Pair* pair = State.Config.FindForSkeleton(skeletonPath))
        {
            // "animations" pairs never touch meshes; only "mesh" pairs rebind them.
            return pair->Use == SkelCompat::Method::Mesh ? pair : nullptr;
        }
    }
    if (CarrierPair(mesh, State.OffMeshUserData, skeleton, skeletonPath, storage)) { return &storage; }
    if (skeleton->HasAnyFlags(RF_NeedLoad))
    {
        State.SkeletonNotLoaded.fetch_add(1, std::memory_order_relaxed);
        return nullptr;
    }
    if (CarrierPair(skeleton, State.OffSkelUserData, skeleton, skeletonPath, storage)) { return &storage; }
    return nullptr;
}

UObject* RawMeshSkeleton(UObject* mesh) { return Field<UObject*>(mesh, State.OffMeshSkeleton); }

void WriteMeshSkeleton(UObject* mesh, UObject* skeleton)
{
    *reinterpret_cast<UObject**>(reinterpret_cast<uint8_t*>(mesh) + State.OffMeshSkeleton) = skeleton;
}

bool AddPending(UObject* mesh)
{
    std::lock_guard lock(State.Mutex);
    if (std::find(State.Pending.begin(), State.Pending.end(), mesh) != State.Pending.end()) { return false; }
    State.Pending.push_back(mesh);
    return true;
}

void RecordRebind(UObject* mesh, UObject* target, std::vector<UObject*> keep, bool family, std::wstring meshPath, std::wstring from, std::wstring to,
                  bool late, bool fixHierarchy, const std::wstring& note)
{
    ReboundMesh record;
    record.Mesh = mesh;
    record.Target = target;
    record.KeepCompatible = std::move(keep);
    record.Family = family;
    record.MeshPath = std::move(meshPath);
    record.FromSkeleton = std::move(from);
    record.ToSkeleton = std::move(to);
    record.Late = late;
    record.FixHierarchy = fixHierarchy;
    record.SocketNote = note;
    Log.Line(std::wstring(late ? L"Rebound (late) " : L"Rebound ") + record.MeshPath + L"\n    skeleton " + record.FromSkeleton +
             L"\n    -> " + record.ToSkeleton + (note.empty() ? std::wstring{} : L"\n    " + note));
    {
        std::lock_guard lock(State.Mutex);
        State.Rebound.erase(std::remove_if(State.Rebound.begin(), State.Rebound.end(),
                                           [&](const ReboundMesh& r) { return r.Mesh == mesh; }),
                            State.Rebound.end());
        State.Rebound.push_back(std::move(record));
    }
    RequestWork();
}

// Keeps the sockets of a mesh's own skeleton on a mesh rebound while it loads (defined further down).
int32_t CarrySockets(UObject* mesh, UObject* ownSkeleton, std::wstring& names);

// Socket stand-ins of a character's own skeleton (row "sockets") on one of its meshes (defined further down).
std::wstring AliasSockets(UObject* mesh, UObject* ownSkeleton, UObject* boundSkeleton);

// A skeleton the mod holds (rooted, fully loaded), or null (defined further down).
UObject* RootedSkeleton(const std::wstring& path);

// Decide for one live mesh. Returns true when the mesh was rebound now.
bool TryRebind(UObject* mesh, bool late)
{
    if (mesh->HasAnyFlags(TemplateFlags) || mesh->HasAnyFlags(DeadFlags)) { return false; }
    UObject* current = RawMeshSkeleton(mesh);
    if (!current) { return false; }
    std::wstring skeletonPath;
    SkelCompat::Pair storage;
    const SkelCompat::Pair* pair = QuickPair(mesh, current, skeletonPath, storage);
    if (!pair)
    {
        // A character's mesh that keeps its skeleton can still get socket stand-ins (before the engine builds its socket map).
        if (!late && !State.AliasSkeletonNames.empty() && State.AliasSkeletonNames.count(Folded(ShortName(current))) > 0)
        {
            const std::wstring note = AliasSockets(mesh, current, current);
            if (!note.empty()) { Log.Line(L"Sockets of " + SkelCompat::NormalizeObjectPath(ObjectPath(mesh)) + L": " + note); }
        }
        return false;
    }

    // From here on the mesh takes part in a pair (rare), so slower work is fine.
    if (skeletonPath.empty()) { skeletonPath = SkelCompat::NormalizeObjectPath(ObjectPath(current)); }
    const std::wstring meshPath = SkelCompat::NormalizeObjectPath(ObjectPath(mesh));
    if (!SkelCompat::MeshAllowed(*pair, meshPath)) { return false; }
    std::wstring targetPath;
    UObject* target = RootedAnimationSkeleton(*pair, &targetPath);
    if (!target)
    {
        WantPair(*pair);
        if (AddPending(mesh))
        {
            Log.Line(L"Deferred " + meshPath + L": its animation skeleton is not loaded yet (" + pair->Origin + L")");
        }
        RequestWork();
        return false;
    }
    if (target == current) { return false; }
    WriteMeshSkeleton(mesh, target);
    std::wstring note;
    if (!pair->FamilyHub.empty())
    {
        note = L"family of " + ShortNameOfPath(pair->FamilyHub) + L".";
        // Animations of this member that a late pass left behind (a character still on the member's skeleton was
        // alive) may be able to move now.
        if (State.FamilyGated.load(std::memory_order_relaxed) > 0) { State.LatePassWanted.store(true, std::memory_order_release); }
    }
    if (!late && pair->CarrySockets)
    {
        // Before the engine's PostLoad builds the socket map. A late rebind keeps the socket map built for the old
        // skeleton, which already holds that skeleton's sockets.
        std::wstring names;
        const int32_t carried = CarrySockets(mesh, current, names);
        if (carried > 0) { note += (note.empty() ? L"" : L" ") + std::wstring(L"Kept ") + std::to_wstring(carried) + L" socket(s) of its own skeleton: " + names; }
        else if (carried < 0) { note += (note.empty() ? L"" : L" ") + std::wstring(L"Sockets of its own skeleton not kept: ") + names; }
    }
    if (!State.AliasSkeletonNames.empty() && State.AliasSkeletonNames.count(Folded(ShortName(current))) > 0)
    {
        if (late)
        {
            note += (note.empty() ? L"" : L" ") + std::wstring(L"Socket stand-ins not made: the mesh was loaded before its skeleton could be "
                                                               L"rebound (its socket map is built); they apply from its next load.");
        }
        else if (const std::wstring aliased = AliasSockets(mesh, current, target); !aliased.empty())
        {
            note += (note.empty() ? L"" : L" ") + aliased;
        }
    }
    // Skeletons whose AnimBlueprints must still accept the mesh (its own, for a family member; the one an outfit was made
    // for, when it followed that skeleton's animations): the hierarchy fix keeps the mesh compatible with them too.
    std::vector<UObject*> keep;
    for (const auto& path : pair->KeepCompatible)
    {
        UObject* skeleton = SkelCompat::PathEquals(path, skeletonPath) ? current : RootedSkeleton(path);
        if (skeleton && skeleton != target && std::find(keep.begin(), keep.end(), skeleton) == keep.end()) { keep.push_back(skeleton); }
    }
    RecordRebind(mesh, target, std::move(keep), !pair->FamilyHub.empty(), meshPath, skeletonPath, targetPath, late, pair->FixHierarchy, note);
    return true;
}

// Renames the mesh bones the animation skeleton places under other parents (defined further down).
void FixHierarchy(UObject* mesh);

// ---------------------------------------------------------------------------------------
// USkeletalMesh::PostLoad vtable hook
// ---------------------------------------------------------------------------------------
using PostLoadFunction = void (*)(UObject*);

void* OriginalPostLoad(UObject* self)
{
    void** table = nullptr;
    std::memcpy(&table, self, sizeof(table));
    const int32_t count = State.PatchCount.load(std::memory_order_acquire);
    for (int32_t i = 0; i < count; ++i)
    {
        if (State.Patches[static_cast<size_t>(i)].Table == table) { return State.Patches[static_cast<size_t>(i)].Original; }
    }
    return count > 0 ? State.Patches[0].Original : nullptr;
}

void HookedPostLoad(UObject* self)
{
    bool rebound = false;
    if (State.Active.load(std::memory_order_acquire) && GetCurrentThreadId() == State.GameThread.load(std::memory_order_relaxed))
    {
        LARGE_INTEGER start{}, end{};
        QueryPerformanceCounter(&start);
        try
        {
            rebound = TryRebind(self, false);
        }
        catch (...)
        {
            Fault(L"SkeletalMesh PostLoad");
        }
        QueryPerformanceCounter(&end);
        const uint64_t ticks = static_cast<uint64_t>(end.QuadPart - start.QuadPart);
        State.PostLoadTicks.fetch_add(ticks, std::memory_order_relaxed);
        if (ticks > State.PostLoadMaxTicks.load(std::memory_order_relaxed)) { State.PostLoadMaxTicks.store(ticks, std::memory_order_relaxed); }
        const uint64_t calls = State.PostLoadCalls.fetch_add(1, std::memory_order_relaxed) + 1;
        if (calls <= 3 || calls % 1000 == 0)
        {
            try
            {
                Log.Line(L"PostLoad hook (thread " + std::to_wstring(GetCurrentThreadId()) + L"): " + PostLoadStats());
            }
            catch (...)
            {
            }
        }
    }
    if (auto* original = reinterpret_cast<PostLoadFunction>(OriginalPostLoad(self))) { original(self); }
    // After the mesh's own PostLoad, so everything it maps by bone name still sees the original names.
    if (rebound && State.Active.load(std::memory_order_acquire))
    {
        try
        {
            FixHierarchy(self);
        }
        catch (...)
        {
            Fault(L"hierarchy fix");
        }
    }
}

bool PatchSlot(void** table, size_t index, void* replacement, void*& original)
{
    void** slot = table + index;
    void* current = nullptr;
    if (!SafeCopy(&current, slot, sizeof(current))) { return false; }
    if (current == replacement) { return false; }
    DWORD oldProtect = 0;
    if (!VirtualProtect(slot, sizeof(void*), PAGE_READWRITE, &oldProtect)) { return false; }
    original = current;
    InterlockedExchangePointer(reinterpret_cast<PVOID volatile*>(slot), replacement);
    DWORD ignored = 0;
    VirtualProtect(slot, sizeof(void*), oldProtect, &ignored);
    return true;
}

void** VTableOf(UObject* object)
{
    void** table = nullptr;
    return (object && SafeCopy(&table, object, sizeof(table))) ? table : nullptr;
}

void* SlotOf(void** table, size_t index)
{
    void* entry = nullptr;
    return (table && SafeCopy(&entry, table + index, sizeof(entry))) ? entry : nullptr;
}

bool InstallPostLoadHook()
{
    const ImageRange image = MainImage();
    UObject* objectCdo = FindObjectByPath(L"/Script/CoreUObject.Default__Object");
    UObject* meshCdo = FindObjectByPath(L"/Script/Engine.Default__SkeletalMesh");
    UObject* skeletonCdo = FindObjectByPath(L"/Script/Engine.Default__Skeleton");
    UObject* libraryCdo = State.KismetSystemLibrary;
    const bool identities = meshCdo && meshCdo->GetClassPrivate() == State.MeshClass && skeletonCdo &&
                            skeletonCdo->GetClassPrivate() == State.SkeletonClass && objectCdo;
    void** objectTable = VTableOf(objectCdo);
    void** meshTable = VTableOf(meshCdo);
    void** skeletonTable = VTableOf(skeletonCdo);
    void** libraryTable = VTableOf(libraryCdo);
    void* objectPostLoad = SlotOf(objectTable, PostLoadSlot);
    void* meshPostLoad = SlotOf(meshTable, PostLoadSlot);
    void* skeletonPostLoad = SlotOf(skeletonTable, PostLoadSlot);
    void* libraryPostLoad = SlotOf(libraryTable, PostLoadSlot);
    // PostLoad is overridden by USkeletalMesh and USkeleton but not by a function library.
    // A wrong slot index fails at least one of these, and then nothing is patched.
    const bool verified = identities && image.Contains(objectPostLoad) && image.Contains(meshPostLoad) && image.Contains(skeletonPostLoad) &&
                          image.Contains(meshTable) && meshPostLoad != objectPostLoad && skeletonPostLoad != objectPostLoad &&
                          libraryPostLoad == objectPostLoad;
    Log.Line(L"PostLoad slot check: Object " + Hex(reinterpret_cast<uintptr_t>(objectPostLoad)) + L", SkeletalMesh " +
             Hex(reinterpret_cast<uintptr_t>(meshPostLoad)) + L", Skeleton " + Hex(reinterpret_cast<uintptr_t>(skeletonPostLoad)) +
             L", KismetSystemLibrary " + Hex(reinterpret_cast<uintptr_t>(libraryPostLoad)) + (verified ? L" -> verified" : L" -> REFUSED"));
    if (!verified) { return false; }

    // Patch SkeletalMesh and every native subclass that has its own vtable.
    std::vector<void**> tables{meshTable};
    UObjectGlobals::ForEachUObject([&](UObject* object, int32, int32) -> LoopAction {
        if (!object || !object->IsA<UClass>()) { return LoopAction::Continue; }
        auto* type = static_cast<UClass*>(object);
        if (type == State.MeshClass || !type->IsChildOf(State.MeshClass)) { return LoopAction::Continue; }
        UObject* cdo = type->GetClassDefaultObject();
        void** table = VTableOf(cdo);
        if (table && image.Contains(table) && std::find(tables.begin(), tables.end(), table) == tables.end()) { tables.push_back(table); }
        return LoopAction::Continue;
    });
    int32_t installed = 0;
    for (void** table : tables)
    {
        if (installed >= static_cast<int32_t>(State.Patches.size())) { break; }
        void* current = SlotOf(table, PostLoadSlot);
        if (!image.Contains(current)) { continue; }
        // Publish the original before the slot points at the hook, so the hook can always find it.
        auto& patch = State.Patches[static_cast<size_t>(installed)];
        patch.Table = table;
        patch.Original = current;
        State.PatchCount.store(installed + 1, std::memory_order_release);
        void* replaced = nullptr;
        if (PatchSlot(table, PostLoadSlot, reinterpret_cast<void*>(&HookedPostLoad), replaced))
        {
            // Once the slot points at the hook the record must stay (with whatever the slot held), or that class would
            // fall back to another class's PostLoad.
            patch.Original = replaced;
            ++installed;
        }
        else
        {
            State.PatchCount.store(installed, std::memory_order_release);
        }
    }
    Log.Line(L"PostLoad hook installed on " + std::to_wstring(installed) + L" SkeletalMesh vtable(s)");
    return installed > 0;
}

// ---------------------------------------------------------------------------------------
// Blocking load through KismetSystemLibrary (no FName construction on our side). Game thread,
// outside loading callbacks only.
// ---------------------------------------------------------------------------------------
struct ParamBlock
{
    UFunction* Function = nullptr;
    std::vector<uint8_t> Bytes;

    explicit ParamBlock(UFunction* function) : Function(function)
    {
        const size_t size = function ? static_cast<size_t>(function->GetParmsSize()) : 0;
        Bytes.assign(std::max<size_t>(size, 16) + 16, 0);
    }

    uint8_t* At(int32_t offset) { return Bytes.data() + offset; }
};

int32_t ParamOffset(UFunction* function, const wchar_t* name, int32_t& size)
{
    FProperty* property = FindField(function, name);
    if (!property) { return -1; }
    size = property->GetElementSize();
    const int32_t offset = property->GetOffset_Internal();
    return (offset >= 0 && size > 0 && offset + size <= function->GetParmsSize()) ? offset : -1;
}

void FreeStringAt(uint8_t* at)
{
    RawArray header{};
    std::memcpy(&header, at, sizeof(header));
    if (header.Data) { FMemory::Free(header.Data); }
    std::memset(at, 0, sizeof(header));
}

UObject* LoadBlocking(const std::wstring& path)
{
    UFunction* make = State.MakeSoftObjectPath;
    UFunction* convert = State.ConvertSoftObjectPath;
    UFunction* load = State.LoadAssetBlocking;
    UObject* library = State.KismetSystemLibrary;
    if (!make || !convert || !load || !library) { Log.Line(L"Loading unavailable: KismetSystemLibrary functions not found"); return nullptr; }

    int32_t pathSize = 0, madeSize = 0, inSize = 0, refSize = 0, assetSize = 0, resultSize = 0;
    const int32_t pathOffset = ParamOffset(make, L"PathString", pathSize);
    const int32_t madeOffset = ParamOffset(make, L"ReturnValue", madeSize);
    const int32_t inOffset = ParamOffset(convert, L"SoftObjectPath", inSize);
    const int32_t refOffset = ParamOffset(convert, L"ReturnValue", refSize);
    const int32_t assetOffset = ParamOffset(load, L"Asset", assetSize);
    const int32_t resultOffset = ParamOffset(load, L"ReturnValue", resultSize);
    if (pathOffset < 0 || madeOffset < 0 || inOffset < 0 || refOffset < 0 || assetOffset < 0 || resultOffset < 0 ||
        pathSize != static_cast<int32_t>(sizeof(RawArray)) || madeSize != inSize || refSize != assetSize ||
        resultSize != static_cast<int32_t>(sizeof(void*)) || madeSize < static_cast<int32_t>(sizeof(FName) + sizeof(RawArray)))
    {
        Log.Line(L"Loading unavailable: unexpected KismetSystemLibrary parameter layout");
        return nullptr;
    }

    ParamBlock first(make);
    new (first.At(pathOffset)) FString(path.c_str());
    library->ProcessEvent(make, first.Bytes.data());
    reinterpret_cast<FString*>(first.At(pathOffset))->~FString();

    ParamBlock second(convert);
    std::memcpy(second.At(inOffset), first.At(madeOffset), static_cast<size_t>(madeSize));
    library->ProcessEvent(convert, second.Bytes.data());

    ParamBlock third(load);
    std::memcpy(third.At(assetOffset), second.At(refOffset), static_cast<size_t>(refSize));
    library->ProcessEvent(load, third.Bytes.data());
    UObject* result = nullptr;
    std::memcpy(&result, third.At(resultOffset), sizeof(result));

    // FSoftObjectPath = { FName AssetPathName; FString SubPathString; } and TSoftObjectPtr ends with an
    // FSoftObjectPath, so in both results the FString is the last 16 bytes. Our buffers own those two
    // strings (the copy handed to LoadAsset_Blocking is an alias and is not freed again).
    FreeStringAt(first.At(madeOffset) + (madeSize - static_cast<int32_t>(sizeof(RawArray))));
    FreeStringAt(second.At(refOffset) + (refSize - static_cast<int32_t>(sizeof(RawArray))));
    return (result && UObject::IsReal(result)) ? result : nullptr;
}

void RootSkeleton(const std::wstring& key, UObject* skeleton, const wchar_t* how)
{
    skeleton->SetRootSet();
    {
        std::lock_guard lock(State.Mutex);
        State.Rooted[key] = skeleton;
        ++State.RootedVersion;
    }
    Log.Line(std::wstring(L"Skeleton resident (") + how + L"): " + ObjectPath(skeleton));
    RequestWork();
}

// Finds (or loads) and roots one animation skeleton, once per path.
void LoadAnimationSkeleton(const std::wstring& path)
{
    const std::wstring key = Folded(path);
    {
        std::lock_guard lock(State.Mutex);
        if (State.Rooted.count(key) > 0) { return; }
        if (std::find(State.LoadAttempted.begin(), State.LoadAttempted.end(), key) != State.LoadAttempted.end()) { return; }
        State.LoadAttempted.push_back(key);
    }
    UObject* found = FindObjectByPath(path.c_str());
    if (found && !found->IsA(State.SkeletonClass)) { found = nullptr; }
    if (!found || !FlagsReady(found))
    {
        UObject* loaded = LoadBlocking(path);
        if (loaded && loaded->IsA(State.SkeletonClass)) { found = loaded; }
    }
    if (found && FlagsReady(found))
    {
        RootSkeleton(key, found, L"loaded by RebirthSkelCompat");
    }
    else
    {
        Log.Line(L"Could not load " + path + L" (wrong path, or not a Skeleton); meshes wait until the game loads it");
    }
}

void PreloadAnimationSkeletons()
{
    for (const auto& pair : State.Config.Pairs)
    {
        for (const auto& path : pair.Animation) { LoadAnimationSkeleton(path); }
        if (pair.Use == SkelCompat::Method::Animations) { LoadAnimationSkeleton(pair.Receiving); }
    }
}

void LoadQueuedSkeletons()
{
    std::vector<std::wstring> queue;
    {
        std::lock_guard lock(State.Mutex);
        queue.swap(State.LoadQueue);
    }
    for (const auto& path : queue) { LoadAnimationSkeleton(path); }
}

// ---------------------------------------------------------------------------------------
// Startup scan, late rebinds and component repair (game thread only)
// ---------------------------------------------------------------------------------------
int32_t LateRebind(const std::vector<UObject*>& meshes, bool validate);

void StartupScan()
{
    std::vector<UObject*> meshes;
    int32_t skeletons = 0;
    UObjectGlobals::ForEachUObject([&](UObject* object, int32, int32) -> LoopAction {
        if (!object || object->HasAnyFlags(TemplateFlags) || object->HasAnyFlags(DeadFlags)) { return LoopAction::Continue; }
        UClass* type = object->GetClassPrivate();
        if (type == State.SkeletonClass)
        {
            ++skeletons;
        }
        else if (type && type->IsChildOf(State.MeshClass))
        {
            meshes.push_back(object);
        }
        return LoopAction::Continue;
    });
    const int32_t rebound = LateRebind(meshes, false);
    Log.Line(L"Scan: " + std::to_wstring(skeletons) + L" skeleton(s) and " + std::to_wstring(meshes.size()) +
             L" mesh(es) loaded, " + std::to_wstring(rebound) + L" mesh(es) rebound late");
}

struct ComponentView
{
    UObject* Component = nullptr;
    UObject* Mesh = nullptr;
    UObject* AnimClass = nullptr;
    UObject* AnimInstance = nullptr;
};

std::vector<ComponentView> ComponentsUsing(const std::vector<UObject*>& meshes)
{
    std::vector<ComponentView> found;
    if (meshes.empty() || !State.ComponentClass || State.OffCompMesh < 0) { return found; }
    UObjectGlobals::ForEachUObject([&](UObject* object, int32, int32) -> LoopAction {
        if (!object || object->HasAnyFlags(TemplateFlags) || object->HasAnyFlags(DeadFlags)) { return LoopAction::Continue; }
        UClass* type = object->GetClassPrivate();
        if (!type || !type->IsChildOf(State.ComponentClass)) { return LoopAction::Continue; }
        ComponentView view;
        view.Component = object;
        view.Mesh = Field<UObject*>(object, State.OffCompMesh);
        if (!view.Mesh || std::find(meshes.begin(), meshes.end(), view.Mesh) == meshes.end()) { return LoopAction::Continue; }
        if (State.OffCompAnimClass >= 0) { view.AnimClass = Field<UObject*>(object, State.OffCompAnimClass); }
        if (State.OffCompAnimInstance >= 0) { view.AnimInstance = Field<UObject*>(object, State.OffCompAnimInstance); }
        found.push_back(view);
        return LoopAction::Continue;
    });
    return found;
}

UObject* TargetSkeletonOf(UObject* animClass)
{
    if (!animClass || !UObject::IsReal(animClass)) { return nullptr; }
    const int32_t offset = FieldOffset(animClass->GetClassPrivate(), L"TargetSkeleton", {L"ObjectProperty"}, 8);
    UObject* skeleton = nullptr;
    return (offset >= 0 && ReadAt(animClass, static_cast<size_t>(offset), skeleton) && UObject::IsReal(skeleton)) ? skeleton : nullptr;
}

void CallSetAnimClass(UObject* component, UObject* animClass)
{
    struct
    {
        UObject* NewClass;
    } params{animClass};
    component->ProcessEvent(State.SetAnimClass, &params);
}

// Components that initialised before the rebind had their AnimBlueprint refused (no instance).
// Re-applying the same class makes the engine spawn it against the new skeleton.
void RepairComponents(const std::vector<std::pair<UObject*, UObject*>>& meshTargets)
{
    if (!State.SetAnimClass || meshTargets.empty()) { return; }
    std::vector<UObject*> meshes;
    for (const auto& [mesh, target] : meshTargets) { meshes.push_back(mesh); }
    for (const ComponentView& view : ComponentsUsing(meshes))
    {
        if (!view.AnimClass || view.AnimInstance) { continue; }
        UObject* target = nullptr;
        for (const auto& [mesh, t] : meshTargets)
        {
            if (mesh == view.Mesh) { target = t; }
        }
        UObject* animSkeleton = TargetSkeletonOf(view.AnimClass);
        if (!target || animSkeleton != target) { continue; }
        CallSetAnimClass(view.Component, nullptr);
        CallSetAnimClass(view.Component, view.AnimClass);
        UObject* instance = State.OffCompAnimInstance >= 0 ? Field<UObject*>(view.Component, State.OffCompAnimInstance) : nullptr;
        ++State.Repaired;
        Log.Line(L"Re-initialised AnimBlueprint on " + ObjectPath(view.Component) + (instance ? L" (instance spawned)" :
                 L" (still refused: see the hierarchy check for this mesh)"));
    }
}

// Rebinds meshes that may already be in use. A mesh is left alone (and logged) when a live
// component runs an AnimBlueprint authored for the mesh's current skeleton: rebinding would pull
// that skeleton out from under the running instance. Such meshes are rebound on their next load.
// validate = the pointers come from a queue and may be stale.
int32_t LateRebind(const std::vector<UObject*>& meshes, bool validate)
{
    std::vector<UObject*> candidates;
    for (UObject* mesh : meshes)
    {
        if (validate && !Alive(mesh)) { continue; }
        if (!FlagsReady(mesh) || !mesh->IsA(State.MeshClass)) { continue; } // still loading: its own PostLoad decides
        UObject* skeleton = RawMeshSkeleton(mesh);
        if (!skeleton) { continue; }
        std::wstring skeletonPath;
        SkelCompat::Pair storage;
        const SkelCompat::Pair* pair = QuickPair(mesh, skeleton, skeletonPath, storage);
        if (!pair || !SkelCompat::MeshAllowed(*pair, SkelCompat::NormalizeObjectPath(ObjectPath(mesh)))) { continue; }
        if (!RootedAnimationSkeleton(*pair, nullptr))
        {
            AddPending(mesh); // still waiting; checked again on a later pump
            WantPair(*pair);
            continue;
        }
        candidates.push_back(mesh);
    }
    if (candidates.empty()) { return 0; }
    const std::vector<ComponentView> views = ComponentsUsing(candidates);
    std::vector<std::pair<UObject*, UObject*>> repair;
    int32_t rebound = 0;
    for (UObject* mesh : candidates)
    {
        UObject* current = RawMeshSkeleton(mesh);
        const bool conflict = std::any_of(views.begin(), views.end(), [&](const ComponentView& view) {
            return view.Mesh == mesh && view.AnimInstance && TargetSkeletonOf(view.AnimClass) == current;
        });
        if (conflict)
        {
            Log.Line(L"Not rebinding " + ObjectPath(mesh) + L" now: a live component runs an AnimBlueprint made for its own skeleton. "
                     L"It is rebound the next time it loads.");
            continue;
        }
        std::wstring skeletonPath;
        SkelCompat::Pair storage;
        const SkelCompat::Pair* pair = QuickPair(mesh, current, skeletonPath, storage);
        const bool repairWanted = pair && pair->RepairLiveComponents;
        if (TryRebind(mesh, true))
        {
            ++rebound;
            FixHierarchy(mesh); // before the repair, so re-initialised AnimBlueprints pass the engine's test
            if (repairWanted) { repair.emplace_back(mesh, RawMeshSkeleton(mesh)); }
        }
    }
    RepairComponents(repair);
    return rebound;
}

// Pending meshes only change state when a new animation skeleton becomes resident.
void ProcessPending()
{
    std::vector<UObject*> pending;
    {
        std::lock_guard lock(State.Mutex);
        if (State.PendingVersion == State.RootedVersion) { return; }
        State.PendingVersion = State.RootedVersion;
        pending.swap(State.Pending);
    }
    if (!pending.empty()) { LateRebind(pending, true); }
}

bool ReadMeshBones(UObject* mesh, SkelCompat::BoneTable& table)
{
    const int32_t known = State.MeshRefSkeletonOffset.load();
    if (known >= 0 && ReadRefSkeleton(mesh, static_cast<size_t>(known), table)) { return true; }
    const int32_t size = State.MeshClass->GetPropertiesSize();
    for (int32_t offset = 0x30; offset + 0x108 <= size; offset += 8)
    {
        if (ReadRefSkeleton(mesh, static_cast<size_t>(offset), table))
        {
            State.MeshRefSkeletonOffset.store(offset);
            Log.Line(L"SkeletalMesh reference skeleton found at offset " + Hex(static_cast<uintptr_t>(offset)));
            return true;
        }
    }
    return false;
}

bool ReadSkeletonBones(UObject* skeleton, SkelCompat::BoneTable& table)
{
    return State.OffSkelRefLocalPoses >= 0 &&
           ReadRefSkeleton(skeleton, static_cast<size_t>(State.OffSkelRefLocalPoses) + sizeof(RawArray), table);
}

// ---------------------------------------------------------------------------------------
// Hierarchy fix (plan: SkelCompat::PlanConflictRenames). A renamed bone keeps its text and gets the
// FName number RenameDisplayBase + index + 1, so it reads "<name>_9xxxxx" and matches no skeleton
// bone. Four places hold a bone's name inside FReferenceSkeleton: the raw and final bone info arrays
// and the raw and final name-to-index maps. All four are validated against the bone list before
// anything is written, and only the aligned 4-byte FName number is written, so a reader on another
// thread sees either the old or the new name, never a torn one. Game thread only.
// ---------------------------------------------------------------------------------------
struct RawName
{
    uint32_t Comparison = 0;
    uint32_t Number = 0;
};
static_assert(sizeof(RawName) == sizeof(FName));

bool SameName(const RawName& a, const RawName& b) { return a.Comparison == b.Comparison && a.Number == b.Number; }

// GetTypeHash(FName) = GetTypeHash(ComparisonIndex) + Number. UE 4.23+ hashes the index through its name-entry handle
// (`handle`); the plain index form is kept as a fallback. Only trusted after every chain of a map checked out with it.
uint32_t NameHash(const RawName& name, bool handle) { return SkelCompat::NameHash(name.Comparison, name.Number, handle); }

// Which form the game's maps check out with: evidence counted from every map whose chains were verified.
std::atomic<int32_t> HandleHashMaps{0};
std::atomic<int32_t> PlainHashMaps{0};

void NoteNameHash(bool handle) { (handle ? HandleHashMaps : PlainHashMaps).fetch_add(1, std::memory_order_relaxed); }

// -1 unknown or contradicting, 0 plain index form, 1 entry-handle form.
int32_t NameHashForm()
{
    const int32_t handle = HandleHashMaps.load(std::memory_order_relaxed);
    const int32_t plain = PlainHashMaps.load(std::memory_order_relaxed);
    if (handle > 0 && plain == 0) { return 1; }
    if (plain > 0 && handle == 0) { return 0; }
    return -1;
}

// TMap<FName, int32> (UE 4.26 shipping), 0x50 bytes: TSparseArray (elements, inline bit array, free list),
// hash bucket heads (one inline slot or a heap block), hash size. Elements are TSetElement<TPair<FName,int32>>:
// key, value, next element in the bucket, bucket index.
struct NameMapHeader
{
    RawArray Elements;
    uint32_t InlineFlags[4];
    void* HeapFlags;
    int32_t NumBits;
    int32_t MaxBits;
    int32_t FirstFree;
    int32_t NumFree;
    int32_t InlineHash;
    int32_t Pad0;
    int32_t* HeapHash;
    int32_t HashSize;
    int32_t Pad1;
};
static_assert(sizeof(NameMapHeader) == 0x50);

struct NameMapElement
{
    RawName Key;
    int32_t Value;
    int32_t Next;
    int32_t Bucket;
};
static_assert(sizeof(NameMapElement) == 20);

constexpr size_t RefSkelRawInfo = 0x00;
constexpr size_t RefSkelFinalInfo = 0x20;
constexpr size_t RefSkelRawMap = 0x40;
constexpr size_t RefSkelFinalMap = RefSkelRawMap + sizeof(NameMapHeader);

struct NameMapView
{
    NameMapElement* Elements = nullptr;
    int32_t* Hash = nullptr;            // bucket heads; null when the hash could not be verified (keys still renamed)
    int32_t HashSize = 0;
    bool HandleHash = true;             // the GetTypeHash(FName) form the buckets follow
    std::vector<int32_t> ElementOfBone; // element holding each raw bone
};

bool ReadBoneNames(const RawArray& info, std::vector<RawName>& names)
{
    if (!info.Data || info.Num <= 0 || info.Num > MaxBones + 1024 || info.Max < info.Num) { return false; }
    std::vector<uint8_t> bytes(static_cast<size_t>(info.Num) * BoneInfoStride);
    if (!SafeCopy(bytes.data(), info.Data, bytes.size())) { return false; }
    names.resize(static_cast<size_t>(info.Num));
    for (size_t i = 0; i < names.size(); ++i) { std::memcpy(&names[i], bytes.data() + i * BoneInfoStride, sizeof(RawName)); }
    return true;
}

// A map built from a bone list: as many elements as bones, no free slots, every raw bone's element
// keyed by that bone's name. Virtual-bone elements (value >= rawCount) are left unchecked: the engine
// numbers them by skeleton position, which can skip.
bool ReadNameMap(uint8_t* at, const std::vector<RawName>& names, int32_t rawCount, NameMapView& out)
{
    NameMapHeader header{};
    if (!SafeCopy(&header, at, sizeof(header))) { return false; }
    const int32_t count = header.Elements.Num;
    if (!header.Elements.Data || count != static_cast<int32_t>(names.size()) || header.Elements.Max < count || header.NumFree != 0 ||
        header.NumBits != count || rawCount <= 0 || rawCount > count)
    {
        return false;
    }
    std::vector<NameMapElement> elements(static_cast<size_t>(count));
    if (!SafeCopy(elements.data(), header.Elements.Data, elements.size() * sizeof(NameMapElement))) { return false; }
    out.ElementOfBone.assign(static_cast<size_t>(rawCount), -1);
    for (int32_t e = 0; e < count; ++e)
    {
        const NameMapElement& element = elements[static_cast<size_t>(e)];
        if (element.Value < 0 || element.Value >= count) { return false; }
        if (element.Value >= rawCount) { continue; }
        int32_t& slot = out.ElementOfBone[static_cast<size_t>(element.Value)];
        if (slot >= 0 || !SameName(element.Key, names[static_cast<size_t>(element.Value)])) { return false; }
        slot = e;
    }
    if (std::find(out.ElementOfBone.begin(), out.ElementOfBone.end(), -1) != out.ElementOfBone.end()) { return false; }
    out.Elements = static_cast<NameMapElement*>(header.Elements.Data);

    // Relinking renamed keys into their new buckets needs the exact hash; verify it on every element.
    const int32_t size = header.HashSize;
    if (size <= 0 || (size & (size - 1)) != 0 || size > (1 << 22)) { return true; }
    int32_t* hash = header.HeapHash ? header.HeapHash : reinterpret_cast<int32_t*>(at + offsetof(NameMapHeader, InlineHash));
    if (!header.HeapHash && size != 1) { return true; }
    std::vector<int32_t> heads(static_cast<size_t>(size));
    if (!SafeCopy(heads.data(), hash, heads.size() * sizeof(int32_t))) { return true; }
    std::vector<int32_t> next(static_cast<size_t>(count)), bucket(static_cast<size_t>(count));
    for (size_t e = 0; e < elements.size(); ++e)
    {
        next[e] = elements[e].Next;
        bucket[e] = elements[e].Bucket;
    }
    const std::vector<uint8_t> allocated(static_cast<size_t>(count), 1);
    bool matches[2] = {false, false}; // [plain, handle]
    for (const bool handle : {true, false})
    {
        std::vector<uint32_t> hashes(static_cast<size_t>(count));
        for (size_t e = 0; e < elements.size(); ++e) { hashes[e] = NameHash(elements[e].Key, handle); }
        matches[handle ? 1 : 0] = SkelCompat::SetChainsMatch(heads, next, bucket, allocated, hashes);
    }
    if (!matches[0] && !matches[1]) { return true; }
    // Only a map with enough keys spread over enough buckets tells the two forms apart.
    if (matches[0] != matches[1] && size >= 8 && count >= 8) { NoteNameHash(matches[1]); }
    out.Hash = hash;
    out.HashSize = size;
    out.HandleHash = matches[1];
    return true;
}

void StoreNumber(void* name, uint32_t number)
{
    *reinterpret_cast<volatile uint32_t*>(static_cast<uint8_t*>(name) + offsetof(RawName, Number)) = number;
}

// New key first (readers walking the old bucket stop matching it), then unlink from the old bucket,
// then publish at the head of the new one. Every intermediate state is a valid chain.
void RenameInMap(NameMapView& map, int32_t bone, const RawName& renamed)
{
    const int32_t e = map.ElementOfBone[static_cast<size_t>(bone)];
    NameMapElement* element = map.Elements + e;
    StoreNumber(&element->Key, renamed.Number);
    if (!map.Hash) { return; }
    const int32_t from = element->Bucket;
    const int32_t to = static_cast<int32_t>(NameHash(renamed, map.HandleHash) & static_cast<uint32_t>(map.HashSize - 1));
    if (from == to) { return; }
    volatile int32_t* link = map.Hash + from;
    for (int32_t guard = 0; *link != -1 && *link != e && guard <= map.HashSize + static_cast<int32_t>(map.ElementOfBone.size()) + 1024; ++guard)
    {
        link = &map.Elements[*link].Next;
    }
    if (*link != e) { return; } // not found (cannot happen after validation): the key is renamed, the bucket stays
    *link = element->Next;
    element->Bucket = to;
    element->Next = map.Hash[to];
    *static_cast<volatile int32_t*>(map.Hash + to) = e;
}

// Writes the renames. Returns false and writes nothing when anything does not match the expected layout.
bool WriteBoneRenames(UObject* mesh, const std::vector<int32_t>& bones, std::wstring& why)
{
    const int32_t offset = State.MeshRefSkeletonOffset.load();
    if (offset < 0) { why = L"reference skeleton not located"; return false; }
    auto* ref = reinterpret_cast<uint8_t*>(mesh) + offset;
    RawArray rawInfo{}, finalInfo{};
    std::vector<RawName> rawNames, finalNames;
    if (!SafeCopy(&rawInfo, ref + RefSkelRawInfo, sizeof(rawInfo)) || !SafeCopy(&finalInfo, ref + RefSkelFinalInfo, sizeof(finalInfo)) ||
        !ReadBoneNames(rawInfo, rawNames) || !ReadBoneNames(finalInfo, finalNames) || finalNames.size() < rawNames.size())
    {
        why = L"bone lists not readable";
        return false;
    }
    for (size_t i = 0; i < rawNames.size(); ++i)
    {
        if (!SameName(rawNames[i], finalNames[i])) { why = L"raw and final bone lists differ"; return false; }
    }
    NameMapView rawMap, finalMap;
    if (!ReadNameMap(ref + RefSkelRawMap, rawNames, rawInfo.Num, rawMap)) { why = L"raw name map not recognised"; return false; }
    if (!ReadNameMap(ref + RefSkelFinalMap, finalNames, rawInfo.Num, finalMap)) { why = L"final name map not recognised"; return false; }

    std::vector<RawName> renamed;
    renamed.reserve(bones.size());
    for (int32_t bone : bones)
    {
        if (bone <= 0 || bone >= rawInfo.Num) { why = L"bone index out of range"; return false; }
        const RawName name{rawNames[static_cast<size_t>(bone)].Comparison, SkelCompat::RenameDisplayBase + static_cast<uint32_t>(bone) + 1};
        if (std::any_of(finalNames.begin(), finalNames.end(), [&](const RawName& n) { return SameName(n, name); }))
        {
            why = L"a renamed bone would collide with an existing name";
            return false;
        }
        renamed.push_back(name);
    }
    // The engine must print the new name with the expected number, else the FName layout is not what we think.
    {
        FName probe{};
        std::memcpy(static_cast<void*>(&probe), &renamed.front(), sizeof(RawName));
        const std::wstring text = probe.ToString();
        const std::wstring suffix = L"_" + std::to_wstring(SkelCompat::RenameDisplayBase + static_cast<uint32_t>(bones.front()));
        if (text.size() <= suffix.size() || text.compare(text.size() - suffix.size(), suffix.size(), suffix) != 0)
        {
            why = L"FName layout not recognised (" + text + L")";
            return false;
        }
    }
    for (size_t k = 0; k < bones.size(); ++k)
    {
        const size_t bone = static_cast<size_t>(bones[k]);
        StoreNumber(static_cast<uint8_t*>(rawInfo.Data) + bone * BoneInfoStride, renamed[k].Number);
        StoreNumber(static_cast<uint8_t*>(finalInfo.Data) + bone * BoneInfoStride, renamed[k].Number);
        RenameInMap(rawMap, bones[k], renamed[k]);
        RenameInMap(finalMap, bones[k], renamed[k]);
    }
    if (!rawMap.Hash || !finalMap.Hash) { why = L"name maps renamed without relinking"; }
    return true;
}

// Bone tables of the rooted animation skeletons (game thread only; rooted pointers stay valid).
const SkelCompat::BoneTable* TargetBones(UObject* target)
{
    static std::unordered_map<UObject*, SkelCompat::BoneTable> cache;
    const auto it = cache.find(target);
    if (it != cache.end()) { return &it->second; }
    SkelCompat::BoneTable table;
    if (!ReadSkeletonBones(target, table)) { return nullptr; }
    return &cache.emplace(target, std::move(table)).first->second;
}

void FixHierarchy(UObject* mesh)
{
    ReboundMesh record;
    {
        std::lock_guard lock(State.Mutex);
        const auto it = std::find_if(State.Rebound.begin(), State.Rebound.end(), [&](const ReboundMesh& r) { return r.Mesh == mesh; });
        if (it == State.Rebound.end()) { return; }
        record = *it;
    }
    int32_t renamed = -1;
    std::wstring note;
    SkelCompat::BoneTable meshBones;
    const SkelCompat::BoneTable* skeletonBones = record.FixHierarchy ? TargetBones(record.Target) : nullptr;
    if (!record.FixHierarchy)
    {
        note = L"hierarchy fix switched off for this pair (fix_hierarchy: false)";
    }
    else if (!skeletonBones || !ReadMeshBones(mesh, meshBones))
    {
        note = L"bone tables could not be read; hierarchy not fixed";
    }
    else
    {
        // AnimBlueprints made for other skeletons may still run on this mesh (its own, for a family member; the one an
        // outfit was made for): the renames keep it compatible with those too (whole subtrees renamed).
        std::vector<SkelCompat::BoneTable> keepTables;
        std::vector<std::wstring> keepNames;
        for (UObject* keepSkeleton : record.KeepCompatible)
        {
            SkelCompat::BoneTable table;
            if (keepSkeleton && keepSkeleton != record.Target && ReadSkeletonBones(keepSkeleton, table))
            {
                keepTables.push_back(std::move(table));
                keepNames.push_back(ShortName(keepSkeleton));
            }
        }
        std::vector<const SkelCompat::BoneTable*> keep;
        for (const auto& table : keepTables) { keep.push_back(&table); }
        const SkelCompat::RenamePlan plan = SkelCompat::PlanConflictRenamesFor(meshBones, *skeletonBones, keep);
        const SkelCompat::BoneTable after = SkelCompat::ApplyRenamePlan(meshBones, plan);
        std::wstring breaks; // skeletons that accepted the mesh before and would refuse it after
        for (size_t k = 0; k < keepTables.size(); ++k)
        {
            if (SkelCompat::CheckMeshAgainstSkeleton(meshBones, keepTables[k]).Compatible && !SkelCompat::CheckMeshAgainstSkeleton(after, keepTables[k]).Compatible)
            {
                breaks += (breaks.empty() ? L"" : L", ") + keepNames[k];
            }
        }
        std::wstring why;
        if (!plan.Possible)
        {
            note = L"root bone '" + meshBones.Names[0] + L"' differs from the skeleton's '" + skeletonBones->Names[0] +
                   L"'; renaming cannot fix that";
        }
        else if (plan.Bones.empty())
        {
            renamed = 0;
        }
        else if (!SkelCompat::CheckMeshAgainstSkeleton(after, *skeletonBones).Compatible)
        {
            note = L"rename plan would not satisfy the engine's test; nothing renamed";
        }
        else if (!breaks.empty())
        {
            note = L"renaming would make the engine refuse AnimBlueprints made for " + breaks + L"; nothing renamed";
        }
        else if (!WriteBoneRenames(mesh, plan.Bones, why))
        {
            note = L"bones not renamed: " + why;
        }
        else
        {
            renamed = static_cast<int32_t>(plan.Bones.size());
            note = std::to_wstring(renamed) + (keep.empty() ? L" bone(s) placed under other parents on the animation skeleton renamed on this mesh "
                                                              L"(they keep the mesh's own pose): "
                                                            : L" bone(s) placed under other parents on " + ShortName(record.Target) +
                                                                  L" renamed on this mesh, with the bones under them so AnimBlueprints made for " +
                                                                  SkelCompat::Detail::Joined(keepNames) + L" still run (they keep the mesh's own pose): ");
            const size_t shown = std::min<size_t>(plan.Bones.size(), 12);
            for (size_t k = 0; k < shown; ++k)
            {
                note += (k ? L", " : L"") + meshBones.Names[static_cast<size_t>(plan.Bones[k])];
            }
            if (plan.Bones.size() > shown) { note += L" (+" + std::to_wstring(plan.Bones.size() - shown) + L" more)"; }
            if (!why.empty()) { note += L" [" + why + L"]"; }
        }
    }
    if (!note.empty()) { Log.Line(L"Hierarchy fix for " + record.MeshPath + L": " + note); }
    std::lock_guard lock(State.Mutex);
    for (auto& stored : State.Rebound)
    {
        if (stored.Mesh == mesh)
        {
            stored.Renamed = renamed;
            stored.HierarchyNote = note;
        }
    }
}

// ---------------------------------------------------------------------------------------
// Sockets of a rebound mesh's own skeleton. USkeletalMesh::PostLoad ends with RebuildSocketMap: the mesh's own
// sockets, then those of its Skeleton. A mesh rebound before that would only find the sockets of the skeleton it was
// rebound to, so a weapon or effect attached to a socket defined on the character's own skeleton lands at the root.
// The old skeleton's sockets are appended to the mesh's own list first (they then also win over a socket of the same
// name on the new skeleton, which was placed for another body). Only sockets on a bone the mesh has, and only names
// the mesh does not define itself. Game thread, inside the mesh's PostLoad before the engine's.
// Returns the number kept, or -1 (with the reason in `names`) when a layout is not recognised.
// ---------------------------------------------------------------------------------------
int32_t CarrySockets(UObject* mesh, UObject* ownSkeleton, std::wstring& names)
{
    names.clear();
    if (State.OffMeshSockets < 0 || State.OffSkelSockets < 0 || State.OffSocketName < 0 || State.OffSocketBone < 0)
    {
        names = L"socket layout not recognised";
        return -1;
    }
    if (!ownSkeleton || ownSkeleton->HasAnyFlags(RF_NeedLoad)) { return 0; }
    RawArray skeletonSockets{};
    if (!ReadAt(ownSkeleton, static_cast<size_t>(State.OffSkelSockets), skeletonSockets) || skeletonSockets.Num < 0 || skeletonSockets.Num > 4096 ||
        skeletonSockets.Max < skeletonSockets.Num || (skeletonSockets.Num > 0 && !skeletonSockets.Data))
    {
        names = L"socket list of the skeleton not readable";
        return -1;
    }
    if (skeletonSockets.Num == 0) { return 0; }
    std::vector<UObject*> offered(static_cast<size_t>(skeletonSockets.Num));
    if (!SafeCopy(offered.data(), skeletonSockets.Data, offered.size() * sizeof(UObject*)))
    {
        names = L"socket list of the skeleton not readable";
        return -1;
    }

    auto* meshArray = reinterpret_cast<RawArray*>(reinterpret_cast<uint8_t*>(mesh) + State.OffMeshSockets);
    const RawArray meshSockets = *meshArray;
    if (meshSockets.Num < 0 || meshSockets.Num > 4096 || meshSockets.Max < meshSockets.Num || (meshSockets.Num > 0 && !meshSockets.Data))
    {
        names = L"socket list of the mesh not recognised";
        return -1;
    }
    std::vector<RawName> taken; // socket names the mesh already has
    for (int32_t i = 0; i < meshSockets.Num; ++i)
    {
        UObject* socket = static_cast<UObject* const*>(meshSockets.Data)[i];
        RawName name{};
        if (socket && ReadAt(socket, static_cast<size_t>(State.OffSocketName), name)) { taken.push_back(name); }
    }

    // Bones the mesh has (raw reference skeleton; the merged virtual bones are not there yet).
    SkelCompat::BoneTable located;
    if (State.MeshRefSkeletonOffset.load() < 0 && !ReadMeshBones(mesh, located))
    {
        names = L"reference skeleton of the mesh not located";
        return -1;
    }
    RawArray rawInfo{};
    std::vector<RawName> bones;
    if (!ReadAt(mesh, static_cast<size_t>(State.MeshRefSkeletonOffset.load()) + RefSkelRawInfo, rawInfo) || !ReadBoneNames(rawInfo, bones))
    {
        names = L"bones of the mesh not readable";
        return -1;
    }

    std::vector<UObject*> kept;
    for (UObject* socket : offered)
    {
        if (!socket || socket->HasAnyFlags(RF_NeedLoad) || socket->HasAnyFlags(DeadFlags)) { continue; }
        RawName name{}, bone{};
        if (!ReadAt(socket, static_cast<size_t>(State.OffSocketName), name) || !ReadAt(socket, static_cast<size_t>(State.OffSocketBone), bone)) { continue; }
        if (name.Comparison == 0 && name.Number == 0) { continue; } // None
        if (std::any_of(taken.begin(), taken.end(), [&](const RawName& t) { return SameName(t, name); })) { continue; }
        if (std::none_of(bones.begin(), bones.end(), [&](const RawName& b) { return SameName(b, bone); })) { continue; }
        taken.push_back(name);
        kept.push_back(socket);
        if (kept.size() <= 12)
        {
            FName text{};
            std::memcpy(static_cast<void*>(&text), &name, sizeof(RawName));
            names += (kept.size() > 1 ? L", " : L"") + text.ToString();
        }
    }
    if (kept.empty()) { return 0; }
    if (kept.size() > 12) { names += L" (+" + std::to_wstring(kept.size() - 12) + L" more)"; }

    const int32_t num = meshSockets.Num + static_cast<int32_t>(kept.size());
    void* data = meshSockets.Data;
    int32_t max = meshSockets.Max;
    if (num > max)
    {
        data = FMemory::Realloc(meshSockets.Data, static_cast<SIZE_T>(num) * sizeof(UObject*));
        if (!data)
        {
            names = L"out of memory";
            return -1;
        }
        max = num;
    }
    std::memcpy(static_cast<UObject**>(data) + meshSockets.Num, kept.data(), kept.size() * sizeof(UObject*));
    meshArray->Data = data;
    meshArray->Max = max;
    meshArray->Num = num;
    return static_cast<int32_t>(kept.size());
}

// ---------------------------------------------------------------------------------------
// Socket stand-ins (3.2, row "sockets"). The game attaches a character's weapon to sockets by name: the holster in the
// field ("Attach_Weapon01", on Cloud's back), the hand in battle ("Attach_Weapon_Right01"), ... A character whose body
// lacks the bone such a socket sits on gets the weapon at its feet (the engine falls back to the component). A stand-in
// is a new socket on the mesh under the name the game asks for, copied from the socket the row names instead (or placed
// on the bone of that name). Mesh sockets come first when the engine's PostLoad builds the socket map, so the stand-in
// wins over a skeleton socket of the same name. Game thread, inside the mesh's PostLoad before the engine's.
// Returns what was done, for the log (empty: the skeleton has no stand-ins).
// ---------------------------------------------------------------------------------------
// Copies a socket's placement onto another: its offset, rotation and scale from the bone (and whether it is always
// animated). Settings a socket class may have besides these keep their defaults.
void CopySocketSettings(UObject* to, UObject* from)
{
    struct Setting
    {
        const wchar_t* Name;
        const wchar_t* Type;
        int32_t Size;
    };
    static const Setting settings[] = {{L"RelativeLocation", L"StructProperty", 12}, {L"RelativeRotation", L"StructProperty", 12},
                                       {L"RelativeScale", L"StructProperty", 12}, {L"bForceAlwaysAnimated", L"BoolProperty", 1}};
    for (const Setting& setting : settings)
    {
        const int32_t at = FieldOffset(State.SocketClass, setting.Name, {setting.Type}, setting.Size);
        if (at >= 0) { std::memcpy(reinterpret_cast<uint8_t*>(to) + at, reinterpret_cast<const uint8_t*>(from) + at, static_cast<size_t>(setting.Size)); }
    }
}

std::wstring AliasSockets(UObject* mesh, UObject* ownSkeleton, UObject* boundSkeleton)
{
    const auto aliases = State.Config.SocketAliasesFor(SkelCompat::NormalizeObjectPath(ObjectPath(ownSkeleton)));
    if (aliases.empty()) { return {}; }
    if (!State.SocketClass || State.OffMeshSockets < 0 || State.OffSkelSockets < 0 || State.OffSocketName < 0 || State.OffSocketBone < 0)
    {
        return L"Socket stand-ins not made: the socket layout was not recognised.";
    }
    SkelCompat::BoneTable located;
    if (State.MeshRefSkeletonOffset.load() < 0 && !ReadMeshBones(mesh, located)) { return L"Socket stand-ins not made: the mesh's bones were not found."; }
    RawArray rawInfo{};
    std::vector<RawName> bones;
    if (!ReadAt(mesh, static_cast<size_t>(State.MeshRefSkeletonOffset.load()) + RefSkelRawInfo, rawInfo) || !ReadBoneNames(rawInfo, bones))
    {
        return L"Socket stand-ins not made: the mesh's bones are not readable.";
    }
    const auto hasBone = [&](const RawName& bone) { return std::any_of(bones.begin(), bones.end(), [&](const RawName& b) { return SameName(b, bone); }); };

    // Sockets on offer: the mesh's own (and any kept from its skeleton), its own skeleton's, the skeleton it is bound to.
    struct Offered
    {
        UObject* Socket;
        RawName Name;
        RawName Bone;
    };
    std::vector<Offered> offered;
    const auto collect = [&](const RawArray& list) {
        if (list.Num <= 0 || list.Num > 4096 || list.Max < list.Num || !list.Data) { return; }
        std::vector<UObject*> pointers(static_cast<size_t>(list.Num));
        if (!SafeCopy(pointers.data(), list.Data, pointers.size() * sizeof(UObject*))) { return; }
        for (UObject* socket : pointers)
        {
            if (!socket || socket->HasAnyFlags(RF_NeedLoad) || socket->HasAnyFlags(DeadFlags)) { continue; }
            RawName name{}, bone{};
            if (!ReadAt(socket, static_cast<size_t>(State.OffSocketName), name) || !ReadAt(socket, static_cast<size_t>(State.OffSocketBone), bone)) { continue; }
            offered.push_back({socket, name, bone});
        }
    };
    auto* meshArray = reinterpret_cast<RawArray*>(reinterpret_cast<uint8_t*>(mesh) + State.OffMeshSockets);
    if (meshArray->Num < 0 || meshArray->Num > 4096 || meshArray->Max < meshArray->Num || (meshArray->Num > 0 && !meshArray->Data))
    {
        return L"Socket stand-ins not made: the mesh's socket list was not recognised.";
    }
    collect(*meshArray);
    const auto collectSkeleton = [&](UObject* skeleton) {
        RawArray list{};
        if (skeleton && !skeleton->HasAnyFlags(RF_NeedLoad) && ReadAt(skeleton, static_cast<size_t>(State.OffSkelSockets), list)) { collect(list); }
    };
    collectSkeleton(ownSkeleton);
    if (boundSkeleton != ownSkeleton) { collectSkeleton(boundSkeleton); }

    const auto raw = [](const FName& name) {
        RawName out{};
        std::memcpy(&out, &name, sizeof(out));
        return out;
    };
    std::wstring done, failed;
    for (const auto& [wanted, use] : aliases)
    {
        const RawName wantedName = raw(FName(wanted.c_str(), FNAME_Add));
        const RawName useName = raw(FName(use.c_str(), FNAME_Find));
        UObject* model = nullptr;
        RawName bone{};
        if (useName.Comparison != 0 || useName.Number != 0)
        {
            for (const auto& o : offered)
            {
                if (SameName(o.Name, useName) && hasBone(o.Bone))
                {
                    model = o.Socket;
                    bone = o.Bone;
                    break;
                }
            }
            if (!model && hasBone(useName)) { bone = useName; }
        }
        if (!model && bone.Comparison == 0 && bone.Number == 0)
        {
            failed += (failed.empty() ? L"" : L", ") + wanted + L" -> " + use + L" (no socket or bone of that name on this mesh)";
            continue;
        }
        FStaticConstructObjectParameters params(State.SocketClass, mesh);
        params.SetFlags = RF_Transient;
        UObject* socket = UObjectGlobals::StaticConstructObject(params);
        if (!socket || !socket->IsA(State.SocketClass))
        {
            failed += (failed.empty() ? L"" : L", ") + wanted + L" (the engine did not create the socket)";
            continue;
        }
        if (model) { CopySocketSettings(socket, model); }
        std::memcpy(reinterpret_cast<uint8_t*>(socket) + State.OffSocketName, &wantedName, sizeof(wantedName));
        std::memcpy(reinterpret_cast<uint8_t*>(socket) + State.OffSocketBone, &bone, sizeof(bone));
        socket->SetRootSet(); // the mesh may sit in a garbage-collection cluster that does not know the new socket
        // Replace a mesh socket of that name, else add one.
        bool replaced = false;
        for (int32_t i = 0; i < meshArray->Num; ++i)
        {
            auto** slot = static_cast<UObject**>(meshArray->Data) + i;
            RawName name{};
            if (*slot && ReadAt(*slot, static_cast<size_t>(State.OffSocketName), name) && SameName(name, wantedName))
            {
                *slot = socket;
                replaced = true;
            }
        }
        if (!replaced)
        {
            const int32_t num = meshArray->Num + 1;
            if (num > meshArray->Max)
            {
                void* grown = FMemory::Realloc(meshArray->Data, static_cast<SIZE_T>(num) * sizeof(UObject*));
                if (!grown)
                {
                    failed += (failed.empty() ? L"" : L", ") + wanted + L" (out of memory)";
                    continue;
                }
                meshArray->Data = grown;
                meshArray->Max = num;
            }
            static_cast<UObject**>(meshArray->Data)[meshArray->Num] = socket;
            meshArray->Num = num;
        }
        FName boneText{};
        std::memcpy(static_cast<void*>(&boneText), &bone, sizeof(bone));
        done += (done.empty() ? L"" : L", ") + wanted + L" -> " + use + L" (bone " + boneText.ToString() + L")";
    }
    std::wstring out;
    if (!done.empty()) { out = L"Socket stand-ins: " + done + L"."; }
    if (!failed.empty()) { out += (out.empty() ? L"" : L" ") + std::wstring(L"Not made: ") + failed + L"."; }
    return out;
}

// ---------------------------------------------------------------------------------------
// Animation adoption (KH3 mode, method "animations"). Every animation asset authored on an animation skeleton
// is rewritten onto the receiving skeleton: AnimSequence track tables move each track to the receiving bone of the
// same name (SkelCompat::BuildTrackRemap; tracks of bones placed differently are dropped), curve UIDs are
// re-resolved by name against the receiving skeleton (unknown curves are dropped), per-bone data follows its bone,
// and the asset's Skeleton becomes the receiving skeleton. Every engine check then sees an animation of the
// receiving skeleton, so characters keep their own skeleton, AnimBlueprint and physics and play the adopted ones.
// Two rules keep this safe while the game runs:
//   * An asset is only rewritten while nothing can be playing it: inside its own PostLoad, while it is still in the
//     async loading pipeline (not handed to the game yet), at a safe point of the frame (map load, after the world
//     tick), or when no mesh component on its old skeleton exists.
//   * A montage, composite or blend space moves only after every animation it plays is on the receiving skeleton,
//     so the receiving skeleton never evaluates another skeleton's track table. Until then it waits (rooted).
// AnimSequence PostLoad runs on the async loading thread in cooked builds; containers PostLoad on the game thread.
// ---------------------------------------------------------------------------------------
constexpr size_t SmartNameStride = sizeof(FName) + 4; // FSmartName (cooked): FName DisplayName, uint16 UID, padding
constexpr uint16_t InvalidCurveUid = 0xFFFF;          // SmartName::MaxUID: ignored by FBlendedCurve
constexpr int32_t MaxChildren = 1024;
constexpr uint64_t LatePassSpacingMs = 2000;
constexpr uint64_t LatePassMaxBackoffMs = 60000;

uint64_t RawKey(const void* name)
{
    uint64_t raw = 0;
    std::memcpy(&raw, name, sizeof(raw));
    return raw;
}

AnimKind KindOf(UObject* asset)
{
    if (State.AnimSequenceClass && asset->IsA(State.AnimSequenceClass)) { return AnimKind::Sequence; }
    if (State.AnimMontageClass && asset->IsA(State.AnimMontageClass)) { return AnimKind::Montage; }
    if (State.AnimCompositeClass && asset->IsA(State.AnimCompositeClass)) { return AnimKind::Composite; }
    if (State.BlendSpaceBaseClass && asset->IsA(State.BlendSpaceBaseClass)) { return AnimKind::BlendSpace; }
    return AnimKind::Other;
}

bool IsContainer(AnimKind kind) { return kind == AnimKind::Composite || kind == AnimKind::Montage || kind == AnimKind::BlendSpace; }

// Still being loaded: not serialized or post-loaded yet, or its package has not been handed to the game.
bool InPipeline(UObject* object)
{
    return object->HasAnyFlags(static_cast<EObjectFlags>(RF_NeedLoad | RF_NeedPostLoad)) ||
           object->HasAnyInternalFlags(EInternalObjectFlags::AsyncLoading);
}

void RequestLatePass() { State.LatePassWanted.store(true, std::memory_order_release); }

// Receiving skeleton's curve names, indexed by UID (USkeleton::AnimCurveMapping->CurveNameList).
bool ReadCurveUids(UObject* skeleton, std::unordered_map<uint64_t, uint16_t>& out, std::wstring& why)
{
    if (State.OffSkelSmartNames < 0) { why = L"Skeleton.SmartNames not found"; return false; }
    // FSmartNameContainer (one TMap) is followed by the cached FSmartNameMapping* AnimCurveMapping, which points at
    // the value of the map pair keyed "AnimationCurves"; its first member is the UID-indexed CurveNameList.
    uint8_t* mapping = nullptr;
    if (!ReadAt(skeleton, static_cast<size_t>(State.OffSkelSmartNames) + sizeof(NameMapHeader), mapping) || !mapping)
    {
        why = L"no curve mapping on the receiving skeleton";
        return false;
    }
    FName key{};
    if (!SafeCopy(&key, mapping - sizeof(FName), sizeof(FName)) || key.ToString() != L"AnimationCurves")
    {
        why = L"curve mapping not recognised";
        return false;
    }
    RawArray list{};
    if (!SafeCopy(&list, mapping, sizeof(list)) || list.Num < 0 || list.Num >= InvalidCurveUid || list.Max < list.Num || (list.Num > 0 && !list.Data))
    {
        why = L"curve name list not recognised";
        return false;
    }
    std::vector<RawName> names(static_cast<size_t>(list.Num));
    if (list.Num > 0 && !SafeCopy(names.data(), list.Data, names.size() * sizeof(RawName))) { why = L"curve names unreadable"; return false; }
    for (size_t uid = 0; uid < names.size(); ++uid)
    {
        const uint64_t raw = RawKey(&names[uid]);
        if (raw != 0) { out.emplace(raw, static_cast<uint16_t>(uid)); } // first UID wins, like FSmartNameMapping::FindSmartName
    }
    return true;
}

// Offset and element size of an array property, or -1.
int32_t ArrayField(UStruct* owner, const wchar_t* name, int32_t& stride)
{
    stride = 0;
    FProperty* property = owner ? FindField(owner, name) : nullptr;
    if (!property || TypeOf(property) != L"ArrayProperty" || property->GetElementSize() != static_cast<int32_t>(sizeof(RawArray))) { return -1; }
    FProperty* inner = static_cast<FArrayProperty*>(property)->GetInner();
    if (!inner) { return -1; }
    stride = inner->GetElementSize();
    const int32_t offset = property->GetOffset_Internal();
    return (offset >= 0 && stride > 0 && offset + static_cast<int32_t>(sizeof(RawArray)) <= owner->GetPropertiesSize()) ? offset : -1;
}

// Offset of a TArray<UObject*> property, or -1.
int32_t ObjectArrayField(UStruct* owner, const wchar_t* name)
{
    int32_t stride = 0;
    const int32_t offset = ArrayField(owner, name, stride);
    if (offset < 0 || stride != static_cast<int32_t>(sizeof(void*))) { return -1; }
    FProperty* inner = static_cast<FArrayProperty*>(FindField(owner, name))->GetInner();
    return (inner && TypeOf(inner) == L"ObjectProperty") ? offset : -1;
}

// Struct type and offset of a struct property, or null.
UStruct* StructField(UStruct* owner, const wchar_t* name, int32_t& offset)
{
    offset = -1;
    FProperty* property = owner ? FindField(owner, name) : nullptr;
    if (!property || TypeOf(property) != L"StructProperty" || property->GetArrayDim() != 1) { return nullptr; }
    UStruct* type = static_cast<FStructProperty*>(property)->GetStruct();
    const int32_t at = property->GetOffset_Internal();
    if (!type || at < 0 || at + property->GetElementSize() > owner->GetPropertiesSize()) { return nullptr; }
    offset = at;
    return type;
}

// Element struct type, array offset and element size of an array-of-structs property, or null.
UStruct* ArrayStructField(UStruct* owner, const wchar_t* name, int32_t& offset, int32_t& stride)
{
    offset = -1;
    stride = 0;
    FProperty* property = owner ? FindField(owner, name) : nullptr;
    if (!property || TypeOf(property) != L"ArrayProperty" || property->GetElementSize() != static_cast<int32_t>(sizeof(RawArray))) { return nullptr; }
    FProperty* inner = static_cast<FArrayProperty*>(property)->GetInner();
    if (!inner || TypeOf(inner) != L"StructProperty") { return nullptr; }
    UStruct* type = static_cast<FStructProperty*>(inner)->GetStruct();
    const int32_t at = property->GetOffset_Internal();
    if (!type || at < 0 || at + static_cast<int32_t>(sizeof(RawArray)) > owner->GetPropertiesSize() || inner->GetElementSize() <= 0) { return nullptr; }
    offset = at;
    stride = inner->GetElementSize();
    return type;
}

// Copies the elements of the TArray at `at` (guarded header read). Empty arrays succeed with no bytes.
bool ReadArrayAt(const void* at, size_t stride, size_t limit, RawArray& header, std::vector<uint8_t>& bytes)
{
    bytes.clear();
    if (!SafeCopy(&header, at, sizeof(header))) { return false; }
    if (header.Num == 0) { return true; }
    if (header.Num < 0 || static_cast<size_t>(header.Num) > limit || header.Max < header.Num || !header.Data || stride == 0) { return false; }
    bytes.resize(static_cast<size_t>(header.Num) * stride);
    return SafeCopy(bytes.data(), header.Data, bytes.size());
}

bool ReadArray(UObject* owner, int32_t offset, size_t stride, size_t limit, RawArray& header, std::vector<uint8_t>& bytes)
{
    return ReadArrayAt(reinterpret_cast<const uint8_t*>(owner) + offset, stride, limit, header, bytes);
}

// The animations a container plays: montage and composite segments, blend space samples. False when unreadable.
bool ReadChildren(UObject* asset, AnimKind kind, std::vector<UObject*>& out)
{
    out.clear();
    const auto* base = reinterpret_cast<const uint8_t*>(asset);
    RawArray header{};
    std::vector<uint8_t> bytes;
    const auto collect = [&](size_t stride, int32_t field) {
        for (int32_t i = 0; i < header.Num; ++i)
        {
            UObject* child = nullptr;
            std::memcpy(&child, bytes.data() + static_cast<size_t>(i) * stride + static_cast<size_t>(field), sizeof(child));
            if (child && std::find(out.begin(), out.end(), child) == out.end()) { out.push_back(child); }
        }
    };
    const auto track = [&](const uint8_t* at) -> bool {
        if (State.TrackSegments < 0 || State.SegmentRef < 0) { return false; }
        if (!ReadArrayAt(at + State.TrackSegments, static_cast<size_t>(State.SegmentStride), MaxChildren, header, bytes)) { return false; }
        collect(static_cast<size_t>(State.SegmentStride), State.SegmentRef);
        return true;
    };
    switch (kind)
    {
    case AnimKind::Composite:
        return State.OffCompositeTrack >= 0 && track(base + State.OffCompositeTrack);
    case AnimKind::Montage:
    {
        if (State.OffMontageSlots < 0 || State.SlotTrack < 0) { return false; }
        RawArray slots{};
        std::vector<uint8_t> slotBytes;
        if (!ReadArrayAt(base + State.OffMontageSlots, static_cast<size_t>(State.SlotStride), 64, slots, slotBytes)) { return false; }
        for (int32_t s = 0; s < slots.Num; ++s)
        {
            const auto* slot = static_cast<const uint8_t*>(slots.Data) + static_cast<size_t>(s) * static_cast<size_t>(State.SlotStride);
            if (!track(slot + State.SlotTrack)) { return false; }
        }
        return true;
    }
    case AnimKind::BlendSpace:
        if (State.OffBlendSamples < 0 || State.SampleAnim < 0) { return false; }
        if (!ReadArray(asset, State.OffBlendSamples, static_cast<size_t>(State.SampleStride), MaxChildren, header, bytes)) { return false; }
        collect(static_cast<size_t>(State.SampleStride), State.SampleAnim);
        return true;
    default:
        return true;
    }
}

enum class ChildState : uint8_t
{
    Ready,   // none, or already on the receiving skeleton (or on no skeleton: plays the reference pose)
    Pending, // on the animation skeleton and still loading: its own PostLoad adopts it
    Blocked, // on the animation skeleton and already handed to the game: only the game-thread pass may adopt it
    Foreign  // on a third skeleton, or a kind that cannot be adopted: the container stays where it is
};

// Another member of plan's family: its animations also move to plan.To (published plans only).
bool MovesToSameHub(UObject* skeleton, const AdoptionPlan& plan)
{
    if (!plan.Family || !skeleton) { return false; }
    const AdoptionTable* table = State.Adoption.load(std::memory_order_acquire);
    return table && std::any_of(table->Plans.begin(), table->Plans.end(),
                                [&](const auto& p) { return p->Family && p->From == skeleton && p->To == plan.To; });
}

ChildState StateOfChild(UObject* child, UObject* container, const AdoptionPlan& plan)
{
    if (!child) { return ChildState::Ready; }
    if (child == container || !child->IsA(State.AnimAssetClass)) { return ChildState::Foreign; }
    if (child->HasAnyFlags(RF_NeedLoad)) { return ChildState::Pending; }
    UObject* skeleton = Field<UObject*>(child, State.OffAnimSkeleton);
    // RF_NeedLoad is cleared before serialisation starts: a null Skeleton may simply not be read yet.
    if (!skeleton) { return InPipeline(child) ? ChildState::Pending : ChildState::Ready; }
    if (skeleton == plan.To) { return ChildState::Ready; }
    // In a family a container may play animations of another member: they move to the same hub.
    if ((skeleton != plan.From && !MovesToSameHub(skeleton, plan)) || KindOf(child) == AnimKind::Other) { return ChildState::Foreign; }
    return InPipeline(child) ? ChildState::Pending : ChildState::Blocked;
}

struct AdoptStats
{
    int32_t Tracks = 0;     // tracks of bones the receiving skeleton lacks or places differently
    int32_t Curves = 0;     // curves the receiving skeleton does not know
    int32_t Attributes = 0; // baked attribute sets emptied (their bone is not carried over)
};

// Plans the UID rewrite of an FSmartName array (elements `stride` bytes apart, FSmartName at `nameAt`).
void PlanCurveNames(const RawArray& header, const std::vector<uint8_t>& bytes, size_t stride, size_t nameAt, const AdoptionPlan& plan,
                    std::vector<std::pair<uint16_t*, uint16_t>>& writes, int32_t& dropped)
{
    for (int32_t i = 0; i < header.Num; ++i)
    {
        const size_t at = static_cast<size_t>(i) * stride + nameAt;
        const uint64_t raw = RawKey(bytes.data() + at);
        const auto it = raw != 0 ? plan.CurveUids.find(raw) : plan.CurveUids.end();
        const uint16_t uid = (plan.CurvesKnown && it != plan.CurveUids.end()) ? it->second : InvalidCurveUid;
        if (uid == InvalidCurveUid) { ++dropped; }
        writes.emplace_back(reinterpret_cast<uint16_t*>(static_cast<uint8_t*>(header.Data) + at + sizeof(FName)), uid);
    }
}

// Rewrites one asset whose Skeleton is plan.From onto plan.To. Validates everything before writing anything.
// Caller holds AdoptMutex and guarantees nothing plays the asset right now; containers have every child ready.
bool AdoptAsset(UObject* asset, AnimKind kind, const AdoptionPlan& plan, std::wstring& why, AdoptStats& stats)
{
    std::vector<std::pair<int32_t*, int32_t>> intWrites;
    std::vector<std::pair<uint16_t*, uint16_t>> curveWrites;
    std::vector<uint8_t> perBone; // blend space: the re-resolved per-bone list, re-sorted
    void* perBoneData = nullptr;
    RawArray header{};
    std::vector<uint8_t> bytes;

    // Float curves of montages and composites (cooked sequences keep theirs in the compressed data).
    if (kind != AnimKind::BlendSpace && State.OffRawFloatCurves >= 0)
    {
        if (!ReadArray(asset, State.OffRawFloatCurves, static_cast<size_t>(State.FloatCurveStride), 4096, header, bytes))
        {
            why = L"curve list not recognised";
            return false;
        }
        PlanCurveNames(header, bytes, static_cast<size_t>(State.FloatCurveStride), static_cast<size_t>(State.FloatCurveName), plan, curveWrites,
                       stats.Curves);
    }

    if (kind == AnimKind::Sequence)
    {
        if (State.OffSeqCompressed < 0) { why = L"AnimSequence layout unknown"; return false; }
        // Track tables: entry = skeleton bone index of the track.
        const auto remap = [&](int32_t offset, bool count) -> bool {
            if (!ReadArray(asset, offset, sizeof(int32_t), MaxBones, header, bytes)) { return false; }
            for (int32_t i = 0; i < header.Num; ++i)
            {
                int32_t index = 0;
                std::memcpy(&index, bytes.data() + static_cast<size_t>(i) * sizeof(int32_t), sizeof(index));
                // Cooked tables only hold bones of the animation skeleton; anything else means the layout is not what we think.
                if (index < -1 || index >= static_cast<int32_t>(plan.TrackMap.size())) { return false; }
                const int32_t mapped = index >= 0 ? plan.TrackMap[static_cast<size_t>(index)] : -1;
                if (mapped < 0 && count) { ++stats.Tracks; }
                intWrites.emplace_back(static_cast<int32_t*>(header.Data) + i, mapped);
            }
            return true;
        };
        if (!remap(State.OffSeqCompressed, true)) { why = L"compressed track table not recognised"; return false; }
        if (State.OffSeqRawTracks >= 0 && !remap(State.OffSeqRawTracks, false)) { why = L"raw track table not recognised"; return false; }

        // Compressed curves: UIDs re-resolved by name on the receiving skeleton.
        if (!ReadArray(asset, State.OffSeqCompressed + static_cast<int32_t>(sizeof(RawArray)), SmartNameStride, 4096, header, bytes))
        {
            why = L"compressed curve list not recognised";
            return false;
        }
        PlanCurveNames(header, bytes, SmartNameStride, 0, plan, curveWrites, stats.Curves);

        // Baked custom attributes are keyed by skeleton bone index too. A set whose bone is not carried over is
        // emptied and parked on the root bone (an index the engine would look up unchecked must stay valid).
        if (State.OffSeqCustomAttrs >= 0)
        {
            const size_t stride = static_cast<size_t>(State.SeqCustomAttrStride);
            if (!ReadArray(asset, State.OffSeqCustomAttrs, stride, MaxBones, header, bytes))
            {
                why = L"baked attribute list not recognised";
                return false;
            }
            if (header.Num > 0 && State.AttrBone < 0) { why = L"baked attributes in an unknown layout"; return false; }
            const bool canEmpty = std::all_of(State.AttrArrays.begin(), State.AttrArrays.end(), [](int32_t a) { return a >= 0; });
            for (int32_t i = 0; i < header.Num; ++i)
            {
                const size_t at = static_cast<size_t>(i) * stride;
                int32_t index = 0;
                std::memcpy(&index, bytes.data() + at + static_cast<size_t>(State.AttrBone), sizeof(index));
                int32_t mapped = index >= 0 && index < static_cast<int32_t>(plan.TrackMap.size()) ? plan.TrackMap[static_cast<size_t>(index)] : -1;
                auto* entry = static_cast<uint8_t*>(header.Data) + at;
                if (mapped < 0)
                {
                    if (!canEmpty) { why = L"baked attributes on a bone that is not carried over"; return false; }
                    for (int32_t field : State.AttrArrays)
                    {
                        intWrites.emplace_back(reinterpret_cast<int32_t*>(entry + field + offsetof(RawArray, Num)), 0);
                    }
                    ++stats.Attributes;
                    mapped = 0;
                }
                intWrites.emplace_back(reinterpret_cast<int32_t*>(entry + State.AttrBone), mapped);
            }
        }
    }
    else if (kind == AnimKind::BlendSpace && State.OffBlendPerBone >= 0)
    {
        // Per-bone blend speeds cache a skeleton bone index (FBoneReference: FName, BoneIndex:31, bUseSkeletonIndex:1).
        const size_t stride = static_cast<size_t>(State.BlendPerBoneStride);
        if (!ReadArray(asset, State.OffBlendPerBone, stride, 1024, header, bytes))
        {
            why = L"per-bone blend list not recognised";
            return false;
        }
        if (header.Num > 0 && (State.PerBoneRef < 0 || stride < static_cast<size_t>(State.PerBoneRef) + 16))
        {
            why = L"per-bone blend settings in an unknown layout";
            return false;
        }
        std::vector<std::pair<int32_t, size_t>> order; // (new bone index, element)
        for (int32_t i = 0; i < header.Num; ++i)
        {
            uint8_t* reference = bytes.data() + static_cast<size_t>(i) * stride + static_cast<size_t>(State.PerBoneRef);
            const auto it = plan.ToBoneIndex.find(RawKey(reference));
            const int32_t index = it != plan.ToBoneIndex.end() ? it->second : -1;
            uint32_t packed = 0;
            std::memcpy(&packed, reference + sizeof(FName), sizeof(packed));
            packed = (packed & 0x80000000u) | (static_cast<uint32_t>(index) & 0x7FFFFFFFu);
            std::memcpy(reference + sizeof(FName), &packed, sizeof(packed));
            order.emplace_back(index, static_cast<size_t>(i));
        }
        // UBlendSpaceBase::InitializePerBoneBlend keeps the list sorted by bone index, highest first.
        std::stable_sort(order.begin(), order.end(), [](const auto& a, const auto& b) { return a.first > b.first; });
        perBone.resize(bytes.size());
        for (size_t k = 0; k < order.size(); ++k) { std::memcpy(perBone.data() + k * stride, bytes.data() + order[k].second * stride, stride); }
        perBoneData = header.Data;
    }

    for (const auto& [at, value] : intWrites) { *reinterpret_cast<volatile int32_t*>(at) = value; }
    for (const auto& [at, value] : curveWrites) { *reinterpret_cast<volatile uint16_t*>(at) = value; }
    if (perBoneData && !perBone.empty()) { std::memcpy(perBoneData, perBone.data(), perBone.size()); }
    if (plan.KeepProportions && kind == AnimKind::Sequence && State.OffSeqRetargetSource >= 0)
    {
        // "proportions": the sequence names the retarget pose of the body it was made for (added to plan.To), so
        // AnimationScaled bones scale by (playing body / that body). One aligned 8-byte store.
        auto* name = reinterpret_cast<volatile uint64_t*>(reinterpret_cast<uint8_t*>(asset) + State.OffSeqRetargetSource);
        const uint64_t before = *name;
        if (before != 0 && before != plan.RetargetName) { plan.RetargetReplaced.fetch_add(1, std::memory_order_relaxed); }
        *name = plan.RetargetName;
    }
    if (plan.WriteVirtualBoneGuid)
    {
        // UAnimSequence::UseRawDataForPoseExtraction compares this with the skeleton's VirtualBoneGuid; a mismatch
        // would send the sequence to its raw tracks, which cooked games strip (the reference pose would play).
        auto* guid = reinterpret_cast<volatile uint32_t*>(reinterpret_cast<uint8_t*>(asset) + State.OffAnimVirtualBoneGuid);
        for (size_t k = 0; k < 4; ++k)
        {
            uint32_t part = 0;
            std::memcpy(&part, plan.ToVirtualBoneGuid.data() + k * sizeof(uint32_t), sizeof(part));
            guid[k] = part;
        }
    }
    *reinterpret_cast<UObject* volatile*>(reinterpret_cast<uint8_t*>(asset) + State.OffAnimSkeleton) = plan.To;
    return true;
}

void LogAdopted(const AdoptionPlan& plan, const std::wstring& path, const wchar_t* how, const AdoptStats& stats)
{
    if (stats.Curves > 0)
    {
        plan.CurvesDropped.fetch_add(static_cast<uint64_t>(stats.Curves));
        plan.AssetsDroppingCurves.fetch_add(1);
    }
    const uint64_t n = plan.Adopted.fetch_add(1) + 1;
    if (n > 12 && n % 250 != 0) { return; }
    std::wstring line = L"Adopted (" + std::wstring(how) + L") " + path + L" -> " + ShortName(plan.To) + L": " + std::to_wstring(stats.Tracks) +
                        L" track(s) of bones it lacks or places differently skipped, " + std::to_wstring(stats.Curves) + L" curve(s) skipped";
    if (stats.Attributes > 0) { line += L", " + std::to_wstring(stats.Attributes) + L" baked attribute set(s) emptied"; }
    Log.Line(line + L" [" + std::to_wstring(n) + L" so far]");
}

void LogRefused(const AdoptionPlan& plan, const std::wstring& path, const std::wstring& why)
{
    const uint64_t n = plan.Refused.fetch_add(1) + 1;
    if (n <= 12 || n % 250 == 0) { Log.Line(L"Not adopted " + path + L": " + why + L" [" + std::to_wstring(n) + L" so far]"); }
}

bool OnGameThread() { return GetCurrentThreadId() == State.GameThread.load(std::memory_order_relaxed); }

// Game thread, AdoptMutex held. Keeps a container until its animations have arrived; rooted (by the mod, unless it
// already was) so the pointer stays valid. Root flags are only ever changed on the game thread: UE4SS updates them
// with a plain read-modify-write that must not race the engine's own flag updates.
void Park(UObject* asset, AnimKind kind, const AdoptionPlan& plan, const std::wstring& path, std::vector<UObject*> children, bool blocked)
{
    // Only the game-thread pass can finish a container the game already has, or adopt a blocked animation.
    if (blocked || !InPipeline(asset))
    {
        RequestLatePass();
        State.LatePassNotBefore = std::min(State.LatePassNotBefore, GetTickCount64() + 500); // soon, but coalesced
    }
    for (auto& entry : State.Waiting)
    {
        if (entry.Asset != asset) { continue; }
        entry.Plan = &plan;
        entry.Children = std::move(children);
        return;
    }
    State.Waiting.emplace_back();
    WaitingContainer& entry = State.Waiting.back();
    entry.Asset = asset;
    entry.Kind = kind;
    entry.Plan = &plan;
    entry.Path = path;
    entry.Children = std::move(children);
    State.WaitingCount.store(static_cast<int32_t>(State.Waiting.size()), std::memory_order_relaxed);
    if (!asset->HasAnyInternalFlags(EInternalObjectFlags::RootSet))
    {
        asset->SetRootSet();
        entry.RootedByMod = true;
    }
    if (State.Waiting.size() <= 12 || State.Waiting.size() % 100 == 0)
    {
        Log.Line(L"Waiting " + path + L": it plays animations that are not on " + ShortName(plan.To) + L" yet (" +
                 std::to_wstring(State.Waiting.size()) + L" waiting)");
    }
}

// Game thread, AdoptMutex held.
void Unpark(size_t index)
{
    WaitingContainer& entry = State.Waiting[index];
    if (entry.RootedByMod) { entry.Asset->ClearRootSet(); }
    State.Waiting.erase(State.Waiting.begin() + static_cast<std::ptrdiff_t>(index));
    State.WaitingCount.store(static_cast<int32_t>(State.Waiting.size()), std::memory_order_relaxed);
}

enum class Decision : uint8_t
{
    Adopted,
    Refused,
    Waiting
};

// AdoptMutex held, nothing plays `asset` right now (see the rules above), its Skeleton is plan.From.
// Containers are only decided on the game thread (their PostLoad runs there); elsewhere they are left to it.
Decision AdoptLocked(UObject* asset, AnimKind kind, const AdoptionPlan& plan, const std::wstring& path, const wchar_t* how)
{
    if (IsContainer(kind))
    {
        if (!OnGameThread())
        {
            RequestLatePass();
            return Decision::Waiting;
        }
        std::vector<UObject*> children;
        if (!ReadChildren(asset, kind, children))
        {
            LogRefused(plan, path, L"its animation list could not be read");
            return Decision::Refused;
        }
        bool waiting = false, blocked = false;
        for (UObject* child : children)
        {
            const ChildState state = StateOfChild(child, asset, plan);
            if (state == ChildState::Foreign)
            {
                LogRefused(plan, path, L"it plays " + ObjectPath(child) + L", which cannot move to " + ShortName(plan.To));
                return Decision::Refused;
            }
            waiting = waiting || state != ChildState::Ready;
            blocked = blocked || state == ChildState::Blocked;
        }
        if (waiting)
        {
            Park(asset, kind, plan, path, std::move(children), blocked);
            return Decision::Waiting;
        }
    }
    std::wstring why;
    AdoptStats stats;
    if (!AdoptAsset(asset, kind, plan, why, stats))
    {
        LogRefused(plan, path, why);
        return Decision::Refused;
    }
    LogAdopted(plan, path, how, stats);
    return Decision::Adopted;
}

// AdoptMutex held, any thread. Adopts waiting containers that are still in the loading pipeline (the game does not
// have them yet) once all their animations are on the receiving skeleton. Entries stay parked: the game thread
// unroots them later. Containers rooted by someone else are left to the game thread, which can validate them.
int32_t AdoptReadyInPipeline()
{
    int32_t adopted = 0;
    for (bool changed = true; changed;)
    {
        changed = false;
        for (const WaitingContainer& entry : State.Waiting)
        {
            if (!entry.RootedByMod) { continue; }
            UObject* asset = entry.Asset;
            const AdoptionPlan& plan = *entry.Plan;
            if (Field<UObject*>(asset, State.OffAnimSkeleton) != plan.From || !InPipeline(asset)) { continue; }
            const bool ready = std::all_of(entry.Children.begin(), entry.Children.end(),
                                           [&](UObject* child) { return StateOfChild(child, asset, plan) == ChildState::Ready; });
            if (!ready) { continue; }
            std::wstring why;
            AdoptStats stats;
            if (AdoptAsset(asset, entry.Kind, plan, why, stats))
            {
                ++adopted;
                changed = true; // a composite inside a montage may have been the last missing animation
                LogAdopted(plan, entry.Path, L"after its animations", stats);
            }
            else
            {
                LogRefused(plan, entry.Path, why);
            }
        }
    }
    return adopted;
}

// Game thread, AdoptMutex held. Finishes waiting containers: unparks the ones that moved (or can never move) and
// adopts those whose animations have all arrived. A container the game already has is only adopted when `released`
// allows its plan (safe point, or nothing on its old skeleton is alive).
template <class Allowed>
int32_t FinishWaiting(Allowed&& released)
{
    int32_t adopted = AdoptReadyInPipeline();
    for (bool changed = true; changed;)
    {
        changed = false;
        for (size_t i = 0; i < State.Waiting.size(); ++i)
        {
            WaitingContainer& entry = State.Waiting[i];
            UObject* asset = entry.Asset;
            // Kept alive by someone else's root, which may be gone: validate before touching it.
            if (!entry.RootedByMod && !Alive(asset))
            {
                State.Waiting.erase(State.Waiting.begin() + static_cast<std::ptrdiff_t>(i));
                State.WaitingCount.store(static_cast<int32_t>(State.Waiting.size()), std::memory_order_relaxed);
                changed = true;
                break;
            }
            const AdoptionPlan& plan = *entry.Plan;
            if (Field<UObject*>(asset, State.OffAnimSkeleton) != plan.From)
            {
                Unpark(i); // adopted, or moved elsewhere
                changed = true;
                break;
            }
            if (!InPipeline(asset) && !released(plan))
            {
                RequestLatePass(); // the game already has it: only a safe point or the gated pass may finish it
                continue;
            }
            bool ready = true, foreign = false;
            for (UObject* child : entry.Children)
            {
                const ChildState state = StateOfChild(child, asset, plan);
                foreign = foreign || state == ChildState::Foreign;
                ready = ready && state == ChildState::Ready;
            }
            if (!ready && !foreign) { continue; }
            if (foreign)
            {
                LogRefused(plan, entry.Path, L"it plays an animation that cannot move to " + ShortName(plan.To));
            }
            else
            {
                std::wstring why;
                AdoptStats stats;
                if (AdoptAsset(asset, entry.Kind, plan, why, stats))
                {
                    ++adopted;
                    LogAdopted(plan, entry.Path, L"after its animations", stats);
                }
                else
                {
                    LogRefused(plan, entry.Path, why);
                }
            }
            Unpark(i);
            changed = true;
            break;
        }
    }
    return adopted;
}

// Inside the asset's own PostLoad: adopts it if a published plan covers it (or a waiting container plays it).
void AdoptOnLoad(UObject* asset, const AdoptionTable& table)
{
    if (State.OffAnimSkeleton < 0) { return; }
    UObject* skeleton = Field<UObject*>(asset, State.OffAnimSkeleton);
    if (!skeleton || std::none_of(table.Plans.begin(), table.Plans.end(), [&](const auto& p) { return p->From == skeleton; })) { return; }
    const AnimKind kind = KindOf(asset);
    if (kind == AnimKind::Other) { return; }
    const std::wstring path = ObjectPath(asset);
    std::lock_guard lock(State.AdoptMutex);
    if (Field<UObject*>(asset, State.OffAnimSkeleton) != skeleton) { return; }
    const AdoptionPlan* plan = nullptr;
    for (const auto& candidate : table.Plans)
    {
        if (candidate->From == skeleton && SkelCompat::PathUnder(candidate->Paths, path))
        {
            plan = candidate.get();
            break;
        }
    }
    for (size_t i = 0; !plan && i < State.Waiting.size(); ++i)
    {
        // Outside adopt_paths, but a waiting container plays it: it follows the container.
        const WaitingContainer& entry = State.Waiting[i];
        if (entry.Plan->From == skeleton && std::find(entry.Children.begin(), entry.Children.end(), asset) != entry.Children.end()) { plan = entry.Plan; }
    }
    if (!plan) { return; }
    if (plan->Family && plan->MemberMeshAlive.load(std::memory_order_relaxed))
    {
        // A character of this family member is still on its own skeleton (loaded before its mesh could be rebound):
        // leave its animations where they are until the late pass sees it gone.
        RequestLatePass();
        return;
    }
    if (AdoptLocked(asset, kind, *plan, path, L"on load") != Decision::Adopted || State.Waiting.empty()) { return; }
    if (OnGameThread()) { FinishWaiting([](const AdoptionPlan&) { return false; }); }
    else { AdoptReadyInPipeline(); }
}

void* OriginalAnimPostLoad(UObject* self)
{
    void** table = nullptr;
    std::memcpy(&table, self, sizeof(table));
    const int32_t count = State.AnimPatchCount.load(std::memory_order_acquire);
    for (int32_t i = 0; i < count; ++i)
    {
        if (State.AnimPatches[static_cast<size_t>(i)].Table == table) { return State.AnimPatches[static_cast<size_t>(i)].Original; }
    }
    return nullptr;
}

void HookedAnimPostLoad(UObject* self)
{
    if (auto* original = reinterpret_cast<PostLoadFunction>(OriginalAnimPostLoad(self))) { original(self); }
    if (!State.Active.load(std::memory_order_acquire)) { return; }
    const AdoptionTable* table = State.Adoption.load(std::memory_order_acquire);
    if (!table || table->Plans.empty()) { return; }
    try
    {
        AdoptOnLoad(self, *table);
    }
    catch (...)
    {
        Fault(L"animation adoption");
    }
}

// Patches PostLoad on every native animation-asset class (each C++ class has its own vtable).
bool InstallAnimPostLoadHooks()
{
    if (!State.AnimAssetClass || State.OffAnimSkeleton < 0) { return false; }
    const ImageRange image = MainImage();
    std::vector<void**> tables;
    UObjectGlobals::ForEachUObject([&](UObject* object, int32, int32) -> LoopAction {
        if (!object || !object->IsA<UClass>()) { return LoopAction::Continue; }
        auto* type = static_cast<UClass*>(object);
        if (!type->IsChildOf(State.AnimAssetClass)) { return LoopAction::Continue; }
        void** table = VTableOf(type->GetClassDefaultObject());
        if (table && image.Contains(table) && std::find(tables.begin(), tables.end(), table) == tables.end()) { tables.push_back(table); }
        return LoopAction::Continue;
    });
    int32_t installed = 0;
    for (void** table : tables)
    {
        if (installed >= static_cast<int32_t>(State.AnimPatches.size())) { break; }
        void* current = SlotOf(table, PostLoadSlot);
        if (!image.Contains(current)) { continue; }
        auto& patch = State.AnimPatches[static_cast<size_t>(installed)];
        patch.Table = table;
        patch.Original = current;
        State.AnimPatchCount.store(installed + 1, std::memory_order_release);
        void* replaced = nullptr;
        if (PatchSlot(table, PostLoadSlot, reinterpret_cast<void*>(&HookedAnimPostLoad), replaced))
        {
            // Once the slot points at the hook the record must stay, or that class would lose its PostLoad.
            patch.Original = replaced;
            ++installed;
        }
        else
        {
            State.AnimPatchCount.store(installed, std::memory_order_release);
        }
    }
    Log.Line(L"Animation PostLoad hook installed on " + std::to_wstring(installed) + L" animation asset vtable(s)");
    return installed > 0;
}

UObject* RootedSkeleton(const std::wstring& path)
{
    std::lock_guard lock(State.Mutex);
    const auto it = State.Rooted.find(Folded(path));
    return (it != State.Rooted.end() && FlagsReady(it->second)) ? it->second : nullptr;
}

// ---------------------------------------------------------------------------------------
// Proportions (3.2, "proportions"). UE 4.26 retargets bone translations per bone of the skeleton an animation plays on
// (FBoneNode::TranslationRetargetingMode): Skeleton takes the translation from the playing mesh's reference pose (the
// bone keeps that body's length), AnimationScaled scales the animation's translation by (playing mesh / the retarget
// pose the animation names: USkeleton::GetRefLocalPoses(RetargetSource), else the skeleton's own pose). So the receiving
// skeleton's body bones get Skeleton and its pelvis AnimationScaled (SkelCompat::ProportionModes), every adopted
// sequence names the animation skeleton it came from as its RetargetSource, and the receiving skeleton gets that
// skeleton's pose under that name in AnimRetargetSources (its own pose with every bone that carries over replaced).
// The map and the modes are only written at a safe point (map load, after the world tick): animation evaluation reads
// them on worker threads.
// ---------------------------------------------------------------------------------------
constexpr size_t TransformStride = 48;     // FTransform (vectorised): rotation, translation, scale, 16 bytes each
constexpr size_t ReferencePoseSize = 24;   // FReferencePose (cooked): FName PoseName; TArray<FTransform> ReferencePose

// A skeleton's final reference pose (one FTransform per bone), checked to look like transforms.
bool ReadFinalPose(UObject* skeleton, size_t bones, std::vector<uint8_t>& out, std::wstring& why)
{
    RawArray pose{};
    if (State.OffSkelRefLocalPoses < 0 ||
        !ReadAt(skeleton, static_cast<size_t>(State.OffSkelRefLocalPoses) + sizeof(RawArray) + 0x30, pose) || pose.Num <= 0 ||
        static_cast<size_t>(pose.Num) != bones || pose.Max < pose.Num || !pose.Data)
    {
        why = L"reference pose of " + ShortName(skeleton) + L" not readable";
        return false;
    }
    out.resize(bones * TransformStride);
    if (!SafeCopy(out.data(), pose.Data, out.size()))
    {
        why = L"reference pose of " + ShortName(skeleton) + L" not readable";
        return false;
    }
    for (size_t i = 0; i < bones; ++i)
    {
        float v[12];
        std::memcpy(v, out.data() + i * TransformStride, sizeof(v));
        bool finite = true;
        for (const float f : v) { finite = finite && f == f && f < 1.0e7f && f > -1.0e7f; }
        const float q = v[0] * v[0] + v[1] * v[1] + v[2] * v[2] + v[3] * v[3];
        if (!finite || q < 0.98f || q > 1.02f)
        {
            why = L"reference pose of " + ShortName(skeleton) + L" is not in the expected FTransform layout";
            return false;
        }
    }
    return true;
}

float TranslationLength(const std::vector<uint8_t>& pose, size_t bone)
{
    if ((bone + 1) * TransformStride > pose.size()) { return 0.0f; }
    float t[3];
    std::memcpy(t, pose.data() + bone * TransformStride + 16, sizeof(t));
    return std::sqrt(t[0] * t[0] + t[1] * t[1] + t[2] * t[2]);
}

std::wstring Fixed(float value)
{
    wchar_t text[32];
    std::swprintf(text, 32, L"%.1f", static_cast<double>(value));
    return text;
}

// The FName hash form, confirmed if need be from the skeleton's own bone-name map (many keys over many buckets).
int32_t EnsureNameHashForm(UObject* skeleton)
{
    const int32_t form = NameHashForm();
    if (form >= 0 || State.OffSkelRefLocalPoses < 0) { return form; }
    const size_t base = static_cast<size_t>(State.OffSkelRefLocalPoses) + sizeof(RawArray);
    RawArray finalInfo{}, rawInfo{};
    std::vector<RawName> names;
    NameMapView view;
    if (ReadAt(skeleton, base + RefSkelFinalInfo, finalInfo) && ReadAt(skeleton, base + RefSkelRawInfo, rawInfo) && ReadBoneNames(finalInfo, names))
    {
        ReadNameMap(reinterpret_cast<uint8_t*>(skeleton) + base + RefSkelFinalMap, names, rawInfo.Num, view);
    }
    return NameHashForm();
}

// Adds retarget poses to a skeleton's AnimRetargetSources. The map is rebuilt with the entries it had (their pose
// arrays move over as they are) and the new ones, then swapped in. Safe point only. Returns what happened.
std::wstring AddRetargetPoses(UObject* skeleton, const std::vector<const ModState::PoseToAdd*>& poses)
{
    if (State.OffSkelRetargetSources < 0) { return L"NOT added: AnimRetargetSources was not located"; }
    const int32_t form = EnsureNameHashForm(skeleton);
    if (form < 0) { return L"NOT added: the game's FName hash form is not confirmed"; }
    auto* at = reinterpret_cast<uint8_t*>(skeleton) + State.OffSkelRetargetSources;
    SkelCompat::SetHeader old{};
    if (!SafeCopy(&old, at, sizeof(old))) { return L"NOT added: AnimRetargetSources unreadable"; }
    std::vector<uint64_t> keys;
    std::vector<uint8_t> values;
    std::wstring why;
    if (!SkelCompat::ReadNameKeyedMap(old, ReferencePoseSize, form == 1, [](void* to, const void* from, size_t size) { return SafeCopy(to, from, size); },
                                      keys, values, why))
    {
        return L"NOT added: AnimRetargetSources " + why;
    }
    const size_t had = keys.size();
    std::vector<void*> fresh;
    std::wstring added;
    for (const auto* pose : poses)
    {
        if (std::find(keys.begin(), keys.end(), pose->Name) != keys.end()) { continue; }
        const size_t bones = pose->Pose.size() / TransformStride;
        void* data = FMemory::Malloc(pose->Pose.size(), 16);
        if (!data) { continue; }
        std::memcpy(data, pose->Pose.data(), pose->Pose.size());
        fresh.push_back(data);
        uint8_t value[ReferencePoseSize]{};
        std::memcpy(value, &pose->Name, sizeof(uint64_t)); // PoseName
        const RawArray array{data, static_cast<int32_t>(bones), static_cast<int32_t>(bones)};
        std::memcpy(value + sizeof(uint64_t), &array, sizeof(array));
        keys.push_back(pose->Name);
        values.insert(values.end(), value, value + ReferencePoseSize);
        added += (added.empty() ? L"" : L", ") + pose->Label;
    }
    if (keys.size() == had) { return L"already there"; }
    SkelCompat::SetHeader built{};
    if (!SkelCompat::BuildNameKeyedMap(keys, values, ReferencePoseSize, form == 1, [](size_t size) { return FMemory::Malloc(size); },
                                       [](void* block) { FMemory::Free(block); }, built))
    {
        for (void* data : fresh) { FMemory::Free(data); }
        return L"NOT added: out of memory";
    }
    std::memcpy(at, &built, sizeof(built));
    if (old.Elements) { FMemory::Free(old.Elements); }
    if (old.HeapFlags) { FMemory::Free(old.HeapFlags); }
    if (old.HeapHash) { FMemory::Free(old.HeapHash); }
    return L"added " + added + (had ? L" (next to " + std::to_wstring(had) + L" it had)" : std::wstring{});
}

// Whether this skeleton's AnimRetargetSources reads as a map (empty or not) at the located offset.
bool RetargetSourcesUsable(UObject* skeleton)
{
    if (State.OffSkelRetargetSources < 0 || !skeleton) { return false; }
    const int32_t form = EnsureNameHashForm(skeleton);
    if (form < 0) { return false; }
    SkelCompat::SetHeader header{};
    if (!SafeCopy(&header, reinterpret_cast<uint8_t*>(skeleton) + State.OffSkelRetargetSources, sizeof(header))) { return false; }
    std::vector<uint64_t> keys;
    std::vector<uint8_t> values;
    std::wstring why;
    return SkelCompat::ReadNameKeyedMap(header, ReferencePoseSize, form == 1, [](void* to, const void* from, size_t size) { return SafeCopy(to, from, size); },
                                        keys, values, why);
}

// Proportion modes on one skeleton's bone tree. Safe point only. Returns what happened.
std::wstring SetProportionModes(UObject* skeleton)
{
    if (State.OffSkelBoneTree < 0 || State.BoneNodeMode < 0 || State.BoneNodeStride <= State.BoneNodeMode)
    {
        return L"NOT set: the bone tree layout was not recognised";
    }
    SkelCompat::BoneTable bones;
    if (!ReadSkeletonBones(skeleton, bones)) { return L"NOT set: the bones are not readable"; }
    std::vector<SkelCompat::RetargetMode> modes = SkelCompat::ProportionModes(bones.Names, bones.Parents);
    // Without retarget poses every animation would be scaled against the hub's own body, which is wrong for animations
    // made for the other bodies (Vincent's own would be scaled twice): the pelvis then keeps its animated height.
    const bool scalePelvis = RetargetSourcesUsable(skeleton);
    if (!scalePelvis)
    {
        for (auto& mode : modes)
        {
            if (mode == SkelCompat::RetargetMode::AnimationScaled) { mode = SkelCompat::RetargetMode::Keep; }
        }
    }
    RawArray tree{};
    std::vector<uint8_t> bytes;
    const size_t stride = static_cast<size_t>(State.BoneNodeStride);
    if (!ReadArray(skeleton, State.OffSkelBoneTree, stride, static_cast<size_t>(MaxBones) + 1024, tree, bytes) || tree.Num <= 0 ||
        (tree.Num != bones.RawCount && static_cast<size_t>(tree.Num) != bones.Names.size()))
    {
        return L"NOT set: the bone tree does not match the bones";
    }
    for (int32_t i = 0; i < tree.Num; ++i)
    {
        if (bytes[static_cast<size_t>(i) * stride + static_cast<size_t>(State.BoneNodeMode)] > 4) { return L"NOT set: the bone tree holds unknown modes"; }
    }
    int32_t changed = 0;
    size_t pelvis = 0;
    for (int32_t i = 0; i < tree.Num; ++i)
    {
        const SkelCompat::RetargetMode mode = modes[static_cast<size_t>(i)];
        if (mode == SkelCompat::RetargetMode::AnimationScaled) { pelvis = static_cast<size_t>(i); }
        if (mode == SkelCompat::RetargetMode::Keep) { continue; }
        auto* at = static_cast<uint8_t*>(tree.Data) + static_cast<size_t>(i) * stride + static_cast<size_t>(State.BoneNodeMode);
        const auto value = static_cast<uint8_t>(mode);
        if (*at != value)
        {
            *reinterpret_cast<volatile uint8_t*>(at) = value;
            ++changed;
        }
    }
    return SkelCompat::DescribeModes(modes) + (pelvis ? L" (pelvis: " + bones.Names[pelvis] + L")" : std::wstring{}) +
           (scalePelvis ? std::wstring{} : std::wstring(L"; pelvis left as animated (the retarget poses could not be placed)")) + L"; " +
           std::to_wstring(changed) + L" bone(s) changed";
}

// At a safe point: retarget poses waiting for their skeleton, then the modes of every configured skeleton now resident.
void ApplyProportions()
{
    State.ProportionsWanted.store(false, std::memory_order_release);
    if (!State.PosesToAdd.empty())
    {
        std::vector<UObject*> skeletons;
        for (const auto& pose : State.PosesToAdd)
        {
            if (std::find(skeletons.begin(), skeletons.end(), pose.Skeleton) == skeletons.end()) { skeletons.push_back(pose.Skeleton); }
        }
        for (UObject* skeleton : skeletons)
        {
            std::vector<const ModState::PoseToAdd*> list;
            for (const auto& pose : State.PosesToAdd)
            {
                if (pose.Skeleton == skeleton) { list.push_back(&pose); }
            }
            const std::wstring line = L"Proportions: retarget poses on " + ShortName(skeleton) + L": " + AddRetargetPoses(skeleton, list);
            Log.Line(line);
            State.ProportionLines.push_back(line);
        }
        State.PosesToAdd.clear();
    }
    for (const auto& path : State.ProportionSkeletons)
    {
        UObject* skeleton = RootedSkeleton(path);
        if (!skeleton || std::find(State.ProportionsDone.begin(), State.ProportionsDone.end(), skeleton) != State.ProportionsDone.end()) { continue; }
        State.ProportionsDone.push_back(skeleton);
        if (State.OffSkelRetargetSources < 0 && State.OffSkelSockets >= 0 && State.OffSkelSmartNames > State.OffSkelSockets &&
            State.OffSkelSmartNames - State.OffSkelSockets <= 0x100 && State.ProportionsDone.size() == 1)
        {
            // Where AnimRetargetSources sits in this build: the bytes between Sockets and SmartNames, for the next version.
            const size_t from = static_cast<size_t>(State.OffSkelSockets), to = static_cast<size_t>(State.OffSkelSmartNames);
            std::vector<uint8_t> bytes(to - from);
            if (SafeCopy(bytes.data(), reinterpret_cast<const uint8_t*>(skeleton) + from, bytes.size()))
            {
                std::wstring dump;
                wchar_t buffer[8]{};
                for (size_t k = 0; k < bytes.size(); ++k)
                {
                    if (k % 16 == 0) { dump += L"\n    +" + Hex(from + k) + L":"; }
                    swprintf_s(buffer, L" %02X", bytes[k]);
                    dump += buffer;
                }
                Log.Line(L"Proportions: skeleton bytes from Sockets to SmartNames (AnimRetargetSources not located):" + dump);
            }
        }
        const std::wstring line = L"Proportions: " + path + L": " + SetProportionModes(skeleton);
        Log.Line(line);
        State.ProportionLines.push_back(line);
    }
}

// Asks for ApplyProportions when a configured skeleton may have become resident since the last look.
void CheckProportions()
{
    if (State.ProportionSkeletons.empty() || State.ProportionsDone.size() >= State.ProportionSkeletons.size()) { return; }
    uint64_t version = 0;
    {
        std::lock_guard lock(State.Mutex);
        version = State.RootedVersion;
    }
    if (version == State.ProportionsVersion) { return; }
    State.ProportionsVersion = version;
    State.ProportionsWanted.store(true, std::memory_order_release);
}

std::shared_ptr<AdoptionPlan> BuildPlan(const SkelCompat::Pair& pair, size_t pairIndex, UObject* from, UObject* to, const std::wstring& fromPath)
{
    SkelCompat::BoneTable fromBones, toBones;
    if (!ReadSkeletonBones(from, fromBones) || !ReadSkeletonBones(to, toBones))
    {
        Log.Line(L"Adoption " + fromPath + L" -> " + pair.Receiving + L": bone tables could not be read; not adopted");
        return nullptr;
    }
    auto plan = std::make_shared<AdoptionPlan>();
    plan->From = from;
    plan->To = to;
    plan->FromPath = fromPath;
    plan->ToPath = pair.Receiving;
    plan->Paths = pair.AdoptPaths;
    plan->PairIndex = pairIndex;
    plan->Family = !pair.FamilyHub.empty();
    plan->TrackMap = SkelCompat::BuildTrackRemap(fromBones, toBones);
    if (plan->TrackMap.empty())
    {
        Log.Line(L"Adoption " + fromPath + L" -> " + pair.Receiving + L": root bones differ ('" + fromBones.Names[0] + L"' vs '" +
                 toBones.Names[0] + L"'); animations cannot be carried over");
        return nullptr;
    }
    // Adopted sequences must carry the receiving skeleton's VirtualBoneGuid, or the engine plays their (stripped) raw data.
    std::array<uint8_t, 16> fromGuid{};
    const bool guidsRead = State.OffSkelVirtualBoneGuid >= 0 && ReadAt(from, static_cast<size_t>(State.OffSkelVirtualBoneGuid), fromGuid) &&
                           ReadAt(to, static_cast<size_t>(State.OffSkelVirtualBoneGuid), plan->ToVirtualBoneGuid);
    if (!guidsRead)
    {
        Log.Line(L"Adoption " + fromPath + L" -> " + pair.Receiving + L": the skeletons' VirtualBoneGuid could not be read; not adopted");
        return nullptr;
    }
    plan->WriteVirtualBoneGuid = State.OffAnimVirtualBoneGuid >= 0;
    if (!plan->WriteVirtualBoneGuid && fromGuid != plan->ToVirtualBoneGuid)
    {
        Log.Line(L"Adoption " + fromPath + L" -> " + pair.Receiving + L": the skeletons have different virtual-bone GUIDs and the animation "
                 L"asset layout is not recognised, so adopted sequences could not play their compressed data; not adopted");
        return nullptr;
    }
    std::wstring why;
    plan->CurvesKnown = ReadCurveUids(to, plan->CurveUids, why);
    {
        // Raw bone FNames of the receiving skeleton (final list), for name-keyed data such as per-bone blend settings.
        RawArray finalInfo{};
        std::vector<RawName> toNames;
        if (State.OffSkelRefLocalPoses >= 0 &&
            ReadAt(to, static_cast<size_t>(State.OffSkelRefLocalPoses) + sizeof(RawArray) + RefSkelFinalInfo, finalInfo) &&
            ReadBoneNames(finalInfo, toNames))
        {
            for (size_t i = 0; i < toNames.size(); ++i) { plan->ToBoneIndex.emplace(RawKey(&toNames[i]), static_cast<int32_t>(i)); }
        }
    }
    int32_t mapped = 0;
    std::vector<std::wstring> differs;
    for (size_t a = 0; a < plan->TrackMap.size(); ++a)
    {
        if (plan->TrackMap[a] >= 0) { ++mapped; continue; }
        if (toBones.Find(fromBones.Names[a]) >= 0 && differs.size() < 10) { differs.push_back(fromBones.Names[a]); }
    }
    plan->Summary = std::to_wstring(mapped) + L" of " + std::to_wstring(plan->TrackMap.size()) + L" bones carry over (same name and parent chain)";
    if (!differs.empty())
    {
        plan->Summary += L"; placed differently, left to the receiving skeleton: ";
        for (size_t k = 0; k < differs.size(); ++k) { plan->Summary += (k ? L", " : L"") + differs[k]; }
        plan->Summary += L" ...";
    }
    plan->Summary += plan->CurvesKnown ? L"; " + std::to_wstring(plan->CurveUids.size()) + L" receiving curve name(s) known"
                                       : L"; curves dropped (" + why + L")";
    if (plan->CurvesKnown)
    {
        // Curve names of the animation skeleton the receiving skeleton lacks: such curve tracks are left out of
        // adopted animations (the receiving skeleton has no slot to evaluate them into).
        std::unordered_map<uint64_t, uint16_t> fromCurves;
        std::wstring fromWhy;
        if (ReadCurveUids(from, fromCurves, fromWhy))
        {
            std::vector<std::wstring> unknown;
            size_t unknownCount = 0;
            for (const auto& [raw, uid] : fromCurves)
            {
                if (plan->CurveUids.count(raw) > 0) { continue; }
                ++unknownCount;
                FName name{};
                std::memcpy(&name, &raw, sizeof(name));
                unknown.push_back(name.ToString());
            }
            std::sort(unknown.begin(), unknown.end());
            plan->Summary += L"; animation skeleton has " + std::to_wstring(fromCurves.size()) + L" curve name(s), " +
                             std::to_wstring(unknownCount) + L" of them unknown to the receiving skeleton";
            if (!unknown.empty())
            {
                plan->Summary += L" (their tracks are left out):";
                for (size_t k = 0; k < unknown.size() && k < 12; ++k) { plan->Summary += L" " + unknown[k]; }
                if (unknown.size() > 12) { plan->Summary += L" ..."; }
            }
        }
    }
    plan->Summary += plan->Paths.empty() ? L"; adopting every animation of this skeleton" : L"; adopting under " + std::to_wstring(plan->Paths.size()) + L" path(s)";
    plan->Summary += fromGuid == plan->ToVirtualBoneGuid ? L"; same virtual-bone GUID" : L"; virtual-bone GUID rewritten on adopted assets";
    if (plan->Family)
    {
        plan->Summary += L"; family member: its meshes are rebound to " + ShortNameOfPath(pair.Receiving) +
                         L", so its bones that do not carry over keep their own pose for every animation";
    }
    if (pair.KeepProportions)
    {
        // The pose of the body these animations were made for, on the receiving skeleton's bones (added at a safe point).
        std::wstring proportionsWhy;
        std::vector<uint8_t> toPose, fromPose, pose;
        if (State.OffSkelRetargetSources < 0 || State.OffSeqRetargetSource < 0)
        {
            proportionsWhy = L"the retarget source layout was not recognised";
        }
        else if (ReadFinalPose(to, toBones.Names.size(), toPose, proportionsWhy) && ReadFinalPose(from, fromBones.Names.size(), fromPose, proportionsWhy))
        {
            pose = SkelCompat::BuildRetargetPose(toPose, fromPose, plan->TrackMap, TransformStride);
            if (pose.empty()) { proportionsWhy = L"the poses do not fit"; }
        }
        if (!pose.empty())
        {
            const FName name = from->GetNamePrivate();
            std::memcpy(&plan->RetargetName, &name, sizeof(plan->RetargetName));
            plan->KeepProportions = plan->RetargetName != 0;
        }
        if (plan->KeepProportions)
        {
            const auto modes = SkelCompat::ProportionModes(toBones.Names, toBones.Parents);
            const auto pelvis = std::find(modes.begin(), modes.end(), SkelCompat::RetargetMode::AnimationScaled);
            plan->Summary += L"; proportions: every body keeps its own bone lengths, the pelvis is scaled against " + ShortName(from);
            if (pelvis != modes.end())
            {
                const auto bone = static_cast<size_t>(pelvis - modes.begin());
                plan->Summary += L" (" + toBones.Names[bone] + L" " + Fixed(TranslationLength(pose, bone)) + L" vs " + ShortName(to) + L" " +
                                 Fixed(TranslationLength(toPose, bone)) + L")";
            }
            State.PosesToAdd.push_back({to, plan->RetargetName, std::move(pose), ShortName(from)});
            State.ProportionsWanted.store(true, std::memory_order_release);
        }
        else
        {
            plan->Summary += L"; proportions NOT kept for these animations (" + proportionsWhy + L")";
        }
    }
    Log.Line(L"Adoption ready: animations of " + fromPath + L" now play on " + pair.Receiving + L"\n    " + plan->Summary);
    return plan;
}

// Game thread. Adopts animations that were already loaded when their plan was published, animations that must
// follow a container, and containers waiting for them. `safePoint`: nothing evaluates animations right now (map
// load, after the world tick). Otherwise only animation skeletons that no live mesh component uses are handled.
void LatePass(bool safePoint)
{
    State.LatePassWanted.store(false, std::memory_order_release);
    const AdoptionTable* table = State.Adoption.load(std::memory_order_acquire);
    if (!table || table->Plans.empty() || !State.AnimAssetClass || State.OffAnimSkeleton < 0) { return; }
    ++State.LatePasses;

    std::vector<UObject*> froms;
    for (const auto& plan : table->Plans)
    {
        if (std::find(froms.begin(), froms.end(), plan->From) == froms.end()) { froms.push_back(plan->From); }
    }
    const auto isFrom = [&](UObject* skeleton) { return skeleton && std::find(froms.begin(), froms.end(), skeleton) != froms.end(); };

    struct Candidate
    {
        UObject* Asset = nullptr;
        AnimKind Kind = AnimKind::Other;
        const AdoptionPlan* Plan = nullptr;
        std::wstring Path;
        bool Eligible = false;
        bool Done = false;
    };
    std::vector<Candidate> candidates;
    std::unordered_set<UObject*> inUse; // animation skeletons a live mesh component plays on
    std::unordered_map<UClass*, uint8_t> classes; // 0 other, 1 mesh component, 2 animation asset
    int32_t loading = 0;
    // Without a way to see mesh components the gate cannot be evaluated: then every skeleton counts as in use.
    const bool gateKnown = State.ComponentClass && State.OffCompMesh >= 0 && State.OffMeshSkeleton >= 0;
    if (!gateKnown) { inUse.insert(froms.begin(), froms.end()); }
    UObjectGlobals::ForEachUObject([&](UObject* object, int32, int32) -> LoopAction {
        if (!object || object->HasAnyFlags(TemplateFlags) || object->HasAnyFlags(DeadFlags)) { return LoopAction::Continue; }
        UClass* type = object->GetClassPrivate();
        if (!type) { return LoopAction::Continue; }
        auto known = classes.find(type);
        if (known == classes.end())
        {
            const uint8_t what = type->IsChildOf(State.AnimAssetClass) ? 2 : (State.ComponentClass && type->IsChildOf(State.ComponentClass) ? 1 : 0);
            known = classes.emplace(type, what).first;
        }
        if (known->second == 1)
        {
            if (!gateKnown) { return LoopAction::Continue; }
            UObject* mesh = nullptr;
            UObject* skeleton = nullptr;
            if (!ReadAt(object, static_cast<size_t>(State.OffCompMesh), mesh) || (mesh && !ReadAt(mesh, static_cast<size_t>(State.OffMeshSkeleton), skeleton)))
            {
                inUse.insert(froms.begin(), froms.end()); // unreadable: assume the worst
            }
            else if (isFrom(skeleton))
            {
                inUse.insert(skeleton);
            }
            return LoopAction::Continue;
        }
        if (known->second != 2) { return LoopAction::Continue; }
        UObject* skeleton = Field<UObject*>(object, State.OffAnimSkeleton);
        if (!isFrom(skeleton)) { return LoopAction::Continue; }
        if (InPipeline(object))
        {
            ++loading; // its own PostLoad, or a later pass, handles it
            return LoopAction::Continue;
        }
        Candidate candidate;
        candidate.Asset = object;
        candidate.Kind = KindOf(object);
        if (candidate.Kind == AnimKind::Other) { return LoopAction::Continue; }
        candidate.Path = ObjectPath(object);
        for (const auto& plan : table->Plans)
        {
            if (plan->From != skeleton) { continue; }
            if (SkelCompat::PathUnder(plan->Paths, candidate.Path))
            {
                candidate.Plan = plan.get();
                candidate.Eligible = true;
                break;
            }
            if (!candidate.Plan) { candidate.Plan = plan.get(); } // used if a container makes it follow
        }
        candidates.push_back(std::move(candidate));
        return LoopAction::Continue;
    });

    // Family members with a live mesh still on their own skeleton keep their animations, also on load (AdoptOnLoad).
    if (gateKnown)
    {
        for (const auto& plan : table->Plans)
        {
            if (plan->Family) { plan->MemberMeshAlive.store(inUse.count(plan->From) > 0, std::memory_order_relaxed); }
        }
    }

    // Animations played by an eligible container follow it (a few levels: composites inside montages), and so do
    // the animations an eligible asset names for later use (Rebirth's blend-out sequence, an additive base pose).
    std::unordered_map<UObject*, size_t> indexOf;
    for (size_t i = 0; i < candidates.size(); ++i) { indexOf.emplace(candidates[i].Asset, i); }
    std::vector<UObject*> children;
    const auto related = [&](const Candidate& candidate) {
        children.clear();
        if (IsContainer(candidate.Kind) && !ReadChildren(candidate.Asset, candidate.Kind, children)) { children.clear(); }
        UObject* extra = nullptr;
        if (candidate.Kind != AnimKind::BlendSpace && State.OffSeqBlendOut >= 0 && (extra = Field<UObject*>(candidate.Asset, State.OffSeqBlendOut)) != nullptr)
        {
            children.push_back(extra);
        }
        if (candidate.Kind == AnimKind::Sequence && State.OffSeqRefPose >= 0 && (extra = Field<UObject*>(candidate.Asset, State.OffSeqRefPose)) != nullptr)
        {
            children.push_back(extra);
        }
    };
    for (int32_t depth = 0; depth < 4; ++depth)
    {
        bool grew = false;
        for (size_t i = 0; i < candidates.size(); ++i)
        {
            if (!candidates[i].Eligible) { continue; }
            related(candidates[i]);
            for (UObject* child : children)
            {
                const auto it = indexOf.find(child);
                if (it == indexOf.end() || candidates[it->second].Eligible) { continue; }
                Candidate& follower = candidates[it->second];
                follower.Eligible = true;
                // It moves with the container's plan when it is on that plan's skeleton; an animation of another
                // family member keeps its own plan (same hub).
                if (Field<UObject*>(follower.Asset, State.OffAnimSkeleton) == candidates[i].Plan->From) { follower.Plan = candidates[i].Plan; }
                grew = true;
            }
        }
        if (!grew) { break; }
    }

    // A family member's animations only move once no live mesh is left on the member's skeleton (its meshes are rebound
    // to the hub when they load): a character still on it would lose them. Other plans move at a safe point.
    const auto allowed = [&](const AdoptionPlan& plan) { return plan.Family ? inUse.count(plan.From) == 0 : (safePoint || inUse.count(plan.From) == 0); };
    const wchar_t* how = safePoint ? L"late, safe point" : L"late";
    int32_t adopted = 0, gated = 0, gatedFamily = 0, waiting = 0;
    std::unordered_set<UObject*> refused; // animations that cannot move: containers playing them cannot either
    // Animations first, then containers in rounds (a container moves once its animations have).
    for (int32_t round = 0; round < 8; ++round)
    {
        bool progress = false;
        for (auto& candidate : candidates)
        {
            if (!candidate.Eligible || candidate.Done || (round == 0 && IsContainer(candidate.Kind))) { continue; }
            candidate.Done = true;
            if (!allowed(*candidate.Plan))
            {
                ++(candidate.Plan->Family ? gatedFamily : gated);
                continue;
            }
            std::lock_guard lock(State.AdoptMutex);
            if (Field<UObject*>(candidate.Asset, State.OffAnimSkeleton) != candidate.Plan->From) { continue; }
            if (IsContainer(candidate.Kind) && ReadChildren(candidate.Asset, candidate.Kind, children) &&
                std::any_of(children.begin(), children.end(), [&](UObject* child) { return refused.count(child) > 0; }))
            {
                for (size_t i = 0; i < State.Waiting.size(); ++i)
                {
                    if (State.Waiting[i].Asset == candidate.Asset)
                    {
                        Unpark(i);
                        break;
                    }
                }
                LogRefused(*candidate.Plan, candidate.Path, L"it plays an animation that could not be adopted");
                refused.insert(candidate.Asset);
                progress = true; // containers that play this one are decided in the next round
                continue;
            }
            const Decision decision = AdoptLocked(candidate.Asset, candidate.Kind, *candidate.Plan, candidate.Path, how);
            if (decision == Decision::Waiting)
            {
                candidate.Done = false; // its animations may move in a later round
            }
            else if (decision == Decision::Refused)
            {
                refused.insert(candidate.Asset);
                progress = true;
            }
            else
            {
                ++adopted;
                progress = true;
            }
        }
        if (round > 0 && !progress) { break; }
    }
    {
        std::lock_guard lock(State.AdoptMutex);
        adopted += FinishWaiting(allowed);
        waiting = static_cast<int32_t>(State.Waiting.size());
    }

    // Retry policy: soon after a plan is published (animations that were mid-load), back off while nothing moves.
    const uint64_t now = GetTickCount64();
    if (loading == 0) { State.LateFollowUps = 0; }
    if (adopted > 0 || State.LateFollowUps > 0) { State.LatePassBackoffMs = LatePassSpacingMs; }
    else { State.LatePassBackoffMs = std::min(LatePassMaxBackoffMs, std::max(LatePassSpacingMs, State.LatePassBackoffMs * 2)); }
    State.LatePassNotBefore = now + State.LatePassBackoffMs;
    // Family members wait for their characters to be reloaded (rebound): the next map load, or a member mesh rebound.
    State.FamilyGated.store(gatedFamily, std::memory_order_relaxed);
    if (gated > 0) { RequestLatePass(); }
    if (State.LateFollowUps > 0)
    {
        --State.LateFollowUps;
        RequestLatePass();
    }
    if (adopted > 0 || gated > 0 || gatedFamily > 0 || waiting > 0)
    {
        std::wstring line = L"Late adoption pass (" + std::wstring(safePoint ? L"safe point" : L"no character on the old skeleton") + L"): " +
                            std::to_wstring(adopted) + L" adopted, " + std::to_wstring(waiting) + L" container(s) waiting for their animations, " +
                            std::to_wstring(gated) + L" left for a safe point (a character on the old skeleton is alive)";
        if (gatedFamily > 0)
        {
            line += L", " + std::to_wstring(gatedFamily) + L" of family members left until their characters are loaded again (a mesh still on "
                    L"the member's own skeleton is alive)";
        }
        const bool classicInUse = std::any_of(table->Plans.begin(), table->Plans.end(), [&](const auto& p) { return !p->Family && inUse.count(p->From) > 0; });
        if (safePoint && classicInUse)
        {
            line += L". Note: characters on the animation skeleton are alive; they cannot play adopted animations any more";
        }
        Log.Line(line);
    }
}

// Game thread. Builds plans for animation-method pairs whose skeletons are resident and publishes them; the late
// pass then handles what is already loaded. Cheap when nothing changed.
void BuildAdoptionPlans()
{
    if (State.OffAnimSkeleton < 0 || !State.AnimAssetClass) { return; }
    uint64_t version = 0;
    {
        std::lock_guard lock(State.Mutex);
        version = State.RootedVersion;
    }
    if (version == State.AdoptionVersion) { return; }
    State.AdoptionVersion = version;

    const AdoptionTable* current = State.Adoption.load(std::memory_order_acquire);
    auto next = std::make_unique<AdoptionTable>();
    if (current) { next->Plans = current->Plans; }
    const size_t before = next->Plans.size();
    for (size_t index = 0; index < State.Config.Pairs.size(); ++index)
    {
        const auto& pair = State.Config.Pairs[index];
        if (pair.Use != SkelCompat::Method::Animations) { continue; }
        UObject* to = RootedSkeleton(pair.Receiving);
        if (!to) { continue; }
        for (const auto& fromPath : pair.Animation)
        {
            const std::wstring key = Folded(fromPath) + L"->" + Folded(pair.Receiving);
            if (std::find(State.AdoptionFailed.begin(), State.AdoptionFailed.end(), key) != State.AdoptionFailed.end()) { continue; }
            UObject* from = RootedSkeleton(fromPath);
            if (!from || from == to) { continue; }
            if (std::any_of(next->Plans.begin(), next->Plans.end(), [&](const auto& p) { return p->From == from && p->To == to; })) { continue; }
            if (auto plan = BuildPlan(pair, index, from, to, fromPath)) { next->Plans.push_back(std::move(plan)); }
            else { State.AdoptionFailed.push_back(key); }
        }
    }
    if (next->Plans.size() == before) { return; }
    // Config order decides which pair gets an animation when several could (stable: same-pair plans keep their order).
    std::stable_sort(next->Plans.begin(), next->Plans.end(), [](const auto& a, const auto& b) { return a->PairIndex < b->PairIndex; });
    const AdoptionTable* published = next.get();
    State.AdoptionTables.push_back(std::move(next));
    State.Adoption.store(published, std::memory_order_release);
    // Animations loaded before now are handled by the late pass at the next safe point.
    State.LateFollowUps = 2;
    State.LatePassNotBefore = 0;
    State.LatePassBackoffMs = LatePassSpacingMs;
    RequestLatePass();
}

// Game thread, every couple of seconds while containers wait: finishes those still loading whose animations have
// arrived, and hands the ones the game already has to the late pass.
void CheckWaiting(bool safePoint)
{
    if (State.WaitingCount.load(std::memory_order_relaxed) == 0) { return; }
    const uint64_t now = GetTickCount64();
    if (now < State.NextWaitingCheck) { return; }
    State.NextWaitingCheck = now + (safePoint ? 250 : LatePassSpacingMs);
    std::lock_guard lock(State.AdoptMutex);
    // Family containers the game already has are left to the late pass, which knows whether a member's character is alive.
    FinishWaiting([safePoint](const AdoptionPlan& plan) { return safePoint && !plan.Family; });
}

// Runs the late pass when one is wanted and due. `safePoint` as for LatePass.
void MaybeLatePass(bool safePoint)
{
    if (!State.LatePassWanted.load(std::memory_order_acquire)) { return; }
    if (!safePoint && State.ViewportSafePoint.load(std::memory_order_relaxed)) { return; } // the safe point runs it
    if (GetTickCount64() < State.LatePassNotBefore) { return; }
    LatePass(safePoint);
}

// ---------------------------------------------------------------------------------------
// Animation set rows (3.1)
// A CharaSpec pack (UEndAssetDataAsset) lists, in AssetDataList[].AssetUserData, the animation sets (UEndAnimSet) its
// character looks animations up in by set name. For a pack a row names, the mod puts merged sets into that list inside
// the pack's PostLoad, before the engine's own: the row's source sets for that set name in order, then the set the
// pack had, the first set that has an animation name winning, and the row's moves on top. A merged set is a new
// UEndAnimSet inside the pack, constructed from its first source (so every other setting is that set's), with an
// AnimationAssets map the mod builds itself. Its buckets use GetTypeHash(FName) in the form the game's own maps were
// seen to use; every source map is checked against it, and without that evidence nothing is built. Source sets and
// move animations are loaded at the first map load and kept resident.
// ---------------------------------------------------------------------------------------
// SkelCompat::SetHeader and NameMapHeader describe the same 0x50-byte TSet header, member for member.
static_assert(sizeof(SkelCompat::SetHeader) == sizeof(NameMapHeader));
static_assert(SkelCompat::NameObjectStride == sizeof(RawName) + sizeof(void*) + 2 * sizeof(int32_t));

using NameObjectEntry = SkelCompat::NameObjectPair;

RawName RawNameOf(const FName& name)
{
    RawName raw{};
    std::memcpy(&raw, &name, sizeof(raw));
    return raw;
}

RawName ObjectRawName(UObject* object) { return RawNameOf(object->GetNamePrivate()); }

uint64_t KeyOf(const RawName& raw) { return RawKey(&raw); }

// Text of a raw FName key (comparison index in the low half, number in the high half).
std::wstring NameText(uint64_t key)
{
    FName name{};
    std::memcpy(static_cast<void*>(&name), &key, sizeof(key));
    return name.ToString();
}

// "/Game/Motion/Player/PC0000_Cloud/Battle00.Battle00" -> "PC0000_Cloud/Battle00".
std::wstring SourceLabel(const std::wstring& path)
{
    std::wstring package = path.substr(0, path.find(L'.'));
    const size_t last = package.find_last_of(L'/');
    const size_t before = last == std::wstring::npos || last == 0 ? std::wstring::npos : package.find_last_of(L'/', last - 1);
    return before == std::wstring::npos ? package : package.substr(before + 1);
}

// Reads a TMap<FName, UObject*> (allocated elements in slot order) and checks its bucket chains with both forms of
// GetTypeHash(FName), counting the evidence. False when the memory does not look like such a map.
bool ReadNameObjectMap(const uint8_t* at, std::vector<NameObjectEntry>& out, std::wstring& why)
{
    SkelCompat::SetHeader header{};
    if (!SafeCopy(&header, at, sizeof(header))) { why = L"map unreadable"; return false; }
    int forms = 0;
    if (!SkelCompat::ReadNameObjectMap(header, [](void* to, const void* from, size_t size) { return SafeCopy(to, from, size); }, out, forms, why))
    {
        return false;
    }
    // Only a map with enough keys spread over enough buckets tells the two forms apart.
    if ((forms == 1 || forms == 2) && header.HashSize >= 8 && out.size() >= 8) { NoteNameHash(forms == 2); }
    return true;
}

// Writes a TMap<FName, UObject*> holding `entries` (in that order) over the map at `at`, which the caller owns (an
// engine-built map: its allocations are freed). Same layout as TSet builds by adding the elements one by one.
bool WriteNameObjectMap(uint8_t* at, const std::vector<NameObjectEntry>& entries, bool handleHash)
{
    SkelCompat::SetHeader fresh{};
    if (!SkelCompat::BuildNameObjectMap(entries, handleHash, [](size_t size) { return FMemory::Malloc(size); }, [](void* block) { FMemory::Free(block); }, fresh))
    {
        return false;
    }
    SkelCompat::SetHeader old{};
    std::memcpy(&old, at, sizeof(old));
    std::memcpy(at, &fresh, sizeof(fresh));
    if (old.Elements) { FMemory::Free(old.Elements); }
    if (old.HeapFlags) { FMemory::Free(old.HeapFlags); }
    if (old.HeapHash) { FMemory::Free(old.HeapHash); }
    return true;
}

// Copies an animation segment of a loaded montage for chained moves (defined further down).
void CaptureSegmentTemplate(UObject* asset);

// Source sets and move animations: found if loaded, else loaded, then kept resident. Game thread, map load.
void PreloadAnimationSets()
{
    std::vector<std::wstring> setPaths, movePaths;
    const auto add = [](std::vector<std::wstring>& list, const std::wstring& path) {
        if (std::none_of(list.begin(), list.end(), [&](const std::wstring& p) { return SkelCompat::PathEquals(p, path); })) { list.push_back(path); }
    };
    for (const auto& row : State.Config.AnimSets)
    {
        for (const auto& name : SkelCompat::RowSetNames(row))
        {
            for (const auto& path : SkelCompat::SetSourcePaths(row, name)) { add(setPaths, path); }
        }
        for (const auto& move : row.Moves)
        {
            for (const auto& path : SkelCompat::MoveAnimations(move)) { add(movePaths, path); }
        }
    }
    std::unordered_set<std::wstring> setKeys, moveKeys, moveNames;
    for (const auto& path : setPaths) { setKeys.insert(Folded(path)); }
    for (const auto& path : movePaths)
    {
        moveKeys.insert(Folded(path));
        moveNames.insert(Folded(SkelCompat::ObjectNameOfPath(path)));
    }
    std::unordered_map<std::wstring, UObject*> found;
    UObjectGlobals::ForEachUObject([&](UObject* object, int32, int32) -> LoopAction {
        if (!object || object->HasAnyFlags(TemplateFlags) || object->HasAnyFlags(DeadFlags)) { return LoopAction::Continue; }
        UClass* type = object->GetClassPrivate();
        if (!type) { return LoopAction::Continue; }
        if (type->IsChildOf(State.AnimSetClass))
        {
            const std::wstring key = Folded(object->GetPathName());
            if (setKeys.count(key) > 0) { found[key] = object; }
        }
        else if (!moveNames.empty() && State.AnimAssetClass && moveNames.count(Folded(ShortName(object))) > 0 && type->IsChildOf(State.AnimAssetClass))
        {
            const std::wstring key = Folded(object->GetPathName());
            if (moveKeys.count(key) > 0) { found[key] = object; }
        }
        if (State.SegmentTemplate.empty() && State.AnimMontageClass && type->IsChildOf(State.AnimMontageClass) && FlagsReady(object))
        {
            CaptureSegmentTemplate(object); // for chained moves
        }
        return LoopAction::Continue;
    });
    const auto resident = [&](const std::wstring& path, UClass* type) -> UObject* {
        const std::wstring key = Folded(path);
        const auto it = found.find(key);
        UObject* object = it == found.end() ? nullptr : it->second;
        if (!object || !FlagsReady(object))
        {
            UObject* loaded = LoadBlocking(path);
            object = (loaded && loaded->IsA(type)) ? loaded : nullptr;
        }
        if (!object || !FlagsReady(object)) { return nullptr; }
        object->SetRootSet();
        return object;
    };
    int32_t sets = 0, animations = 0, tried = 0;
    // Each source's paths in order until one is there: an auto source's fallback set is only loaded when its own is missing.
    const auto residentSet = [&](const std::wstring& path) -> UObject* {
        const std::wstring key = Folded(path);
        if (const auto it = State.SetObjects.find(key); it != State.SetObjects.end()) { return it->second; }
        ++tried;
        UObject* set = resident(path, State.AnimSetClass);
        State.SetObjects[key] = set;
        if (!set) { return nullptr; }
        ++sets;
        std::vector<NameObjectEntry> entries;
        std::wstring why;
        const bool read = ReadNameObjectMap(reinterpret_cast<const uint8_t*>(set) + State.OffSetAssets, entries, why);
        State.SetKeys[key] = read ? static_cast<int32_t>(entries.size()) : -1;
        if (!read) { Log.Line(L"Animation set " + path + L" not usable: " + why); }
        return set;
    };
    for (const auto& row : State.Config.AnimSets)
    {
        for (const auto& name : SkelCompat::RowSetNames(row))
        {
            for (const auto& ref : SkelCompat::SetSourcesFor(row, name))
            {
                for (const auto& path : ref.Paths)
                {
                    if (residentSet(path)) { break; }
                }
            }
        }
    }
    for (const auto& path : movePaths)
    {
        UObject* animation = State.AnimAssetClass ? resident(path, State.AnimAssetClass) : nullptr;
        State.MoveObjects[Folded(path)] = animation;
        if (animation) { ++animations; }
    }

    // What every row found, for the log and the report.
    const int32_t form = NameHashForm();
    State.SetLines.push_back(L"FName hash: " + std::wstring(form == 1 ? L"entry-handle form" : form == 0 ? L"plain index form" : L"NOT CONFIRMED") + L" (" +
                             std::to_wstring(HandleHashMaps.load()) + L" map(s) checked out with the entry-handle form, " +
                             std::to_wstring(PlainHashMaps.load()) + L" with the plain form)" +
                             (form < 0 ? L"; sets are not merged until the form is confirmed" : L""));
    for (const auto& row : State.Config.AnimSets)
    {
        std::wstring text = L"Row for " + row.Characters.front() + L"  [" + row.Origin + L"]";
        for (const auto& name : SkelCompat::RowSetNames(row))
        {
            std::wstring line;
            for (const auto& ref : SkelCompat::SetSourcesFor(row, name))
            {
                for (size_t k = 0; k < ref.Paths.size(); ++k)
                {
                    const std::wstring key = Folded(ref.Paths[k]);
                    if (!State.SetObjects[key]) { continue; }
                    const int32_t keys = State.SetKeys.count(key) ? State.SetKeys[key] : -1;
                    line += (line.empty() ? L"" : L", ") + SourceLabel(ref.Paths[k]) + L" (" + (keys >= 0 ? std::to_wstring(keys) : std::wstring(L"unreadable")) +
                            (ref.Auto == SkelCompat::AutoMatchMode::Off ? L"" : L", auto") + (k > 0 ? L", standing in for " + SourceLabel(ref.Paths[0]) : L"") + L")";
                    break;
                }
            }
            if (!line.empty()) { text += L"\n    " + name + L": " + line; }
        }
        for (const auto& move : row.Moves)
        {
            text += L"\n    move " + (move.Set.empty() ? std::wstring{} : move.Set + L"/") + move.Key + L" -> ";
            if (move.Chain.empty())
            {
                text += move.Animation + (State.MoveObjects[Folded(move.Animation)] ? L"" : L"  (NOT FOUND: move ignored)");
                continue;
            }
            text += L"chain of " + std::to_wstring(move.Chain.size()) + L":";
            for (const auto& path : move.Chain) { text += L" " + path + (State.MoveObjects[Folded(path)] ? L"" : L" (NOT FOUND)"); }
        }
        if (!row.Sockets.empty())
        {
            text += L"\n    socket stand-ins on meshes of " + row.Skeleton + L" (made while each mesh loads; see \"Socket stand-ins\" lines)";
        }
        if (!row.FieldActions.empty())
        {
            text += L"\n    field_actions " + row.FieldActions + L": field actions follow the CharaSpec row's AnimationSetParentFolder, which the "
                    L"Skeleton Compatibility data object (or the CharaSpec table) sets; nothing to do at run time";
        }
        State.SetLines.push_back(text);
    }
    for (const auto& line : State.SetLines) { Log.Line(L"Animation sets: " + line); }
    Log.Line(L"Animation sets: " + std::to_wstring(sets) + L" of " + std::to_wstring(tried) + L" source set path(s) looked for found, " +
             std::to_wstring(animations) + L" of " + std::to_wstring(movePaths.size()) + L" move animation(s); all kept resident" +
             (State.SegmentTemplate.empty() ? L"; chained moves build their segments from the reflected layout (no montage loaded yet)" : L""));
}

struct PackSlot
{
    int32_t Entry = -1;  // AssetDataList index
    int32_t Index = -1;  // AssetUserData index
    UObject* Set = nullptr;
    std::wstring Name;
};

// AssetUserData array of one AssetDataList entry (null when out of range).
RawArray* PackObjects(UObject* pack, int32_t entry)
{
    RawArray list{};
    std::memcpy(&list, reinterpret_cast<uint8_t*>(pack) + State.OffPackList, sizeof(list));
    if (entry < 0 || entry >= list.Num || !list.Data) { return nullptr; }
    return reinterpret_cast<RawArray*>(static_cast<uint8_t*>(list.Data) + static_cast<size_t>(entry) * static_cast<size_t>(State.PackEntryStride) +
                                       static_cast<size_t>(State.OffEntryObjects));
}

bool ReadPackSets(UObject* pack, std::vector<PackSlot>& slots, int32_t& entries, std::wstring& why)
{
    RawArray list{};
    std::vector<uint8_t> bytes;
    if (!ReadArray(pack, State.OffPackList, static_cast<size_t>(State.PackEntryStride), 4096, list, bytes)) { why = L"AssetDataList unreadable"; return false; }
    entries = list.Num;
    for (int32_t e = 0; e < list.Num; ++e)
    {
        RawArray objects{};
        std::vector<uint8_t> pointers;
        const auto* entry = bytes.data() + static_cast<size_t>(e) * static_cast<size_t>(State.PackEntryStride);
        RawArray header{};
        std::memcpy(&header, entry + State.OffEntryObjects, sizeof(header));
        if (header.Num == 0) { continue; }
        if (!ReadArrayAt(static_cast<const uint8_t*>(list.Data) + static_cast<size_t>(e) * static_cast<size_t>(State.PackEntryStride) + State.OffEntryObjects,
                         sizeof(void*), 4096, objects, pointers))
        {
            why = L"AssetUserData of entry " + std::to_wstring(e) + L" unreadable";
            return false;
        }
        for (int32_t i = 0; i < objects.Num; ++i)
        {
            UObject* object = nullptr;
            std::memcpy(&object, pointers.data() + static_cast<size_t>(i) * sizeof(void*), sizeof(object));
            if (!object || !object->IsA(State.AnimSetClass)) { continue; }
            slots.push_back({e, i, object, ShortName(object)});
        }
    }
    return true;
}

struct SetBuild
{
    UObject* Set = nullptr; // set for the pack's list (null: the pack keeps what it had)
    std::wstring Note;
};

// The set named `name` for a pack: the row's sources, then `own` (the pack's set of that name, may be null).
// What the auto match knows of one animation of a set: its name, length (seconds) and whether it is additive.
SkelCompat::MatchAnim MatchInfo(uint64_t key, UObject* animation)
{
    SkelCompat::MatchAnim info;
    info.Name = NameText(key);
    if (!animation || animation->HasAnyFlags(RF_NeedLoad) || animation->HasAnyFlags(DeadFlags)) { return info; }
    if (State.AnimSequenceBaseClass && State.OffSeqLength >= 0 && animation->IsA(State.AnimSequenceBaseClass))
    {
        float length = 0.0f;
        if (ReadAt(animation, static_cast<size_t>(State.OffSeqLength), length) && length > 0.0f && length < 3600.0f) { info.Length = length; }
    }
    if (State.AnimSequenceClass && State.OffSeqAdditiveType >= 0 && animation->IsA(State.AnimSequenceClass))
    {
        uint8_t type = 0;
        if (ReadAt(animation, static_cast<size_t>(State.OffSeqAdditiveType), type)) { info.Additive = type != 0; }
    }
    return info;
}

// Copies the first animation segment of a loaded montage or composite: chained moves start every segment from it, so
// the segment's unreflected bytes (bValid) are those of a segment the engine made.
void CaptureSegmentTemplate(UObject* asset)
{
    if (!State.SegmentTemplate.empty() || State.SegmentStride <= 0 || State.TrackSegments < 0 || State.SegmentRef < 0) { return; }
    const size_t stride = static_cast<size_t>(State.SegmentStride);
    const auto take = [&](const uint8_t* track) {
        RawArray segments{};
        std::vector<uint8_t> bytes;
        if (!ReadArrayAt(track + State.TrackSegments, stride, 64, segments, bytes) || segments.Num <= 0) { return false; }
        UObject* reference = nullptr;
        std::memcpy(&reference, bytes.data() + State.SegmentRef, sizeof(reference));
        if (!reference) { return false; }
        State.SegmentTemplate.assign(bytes.begin(), bytes.begin() + static_cast<std::ptrdiff_t>(stride));
        Log.Line(L"Animation segment layout taken from " + ObjectPath(asset) + L" (" + std::to_wstring(stride) + L" bytes, bValid at " +
                 Hex(static_cast<uintptr_t>(State.SegValid)) + L" reads " +
                 (State.SegValid >= 0 ? std::to_wstring(State.SegmentTemplate[static_cast<size_t>(State.SegValid)]) : std::wstring(L"?")) + L")");
        return true;
    };
    const auto* base = reinterpret_cast<const uint8_t*>(asset);
    if (State.AnimMontageClass && asset->IsA(State.AnimMontageClass) && State.OffMontageSlots >= 0 && State.SlotTrack >= 0 && State.SlotStride > 0)
    {
        RawArray slots{};
        std::vector<uint8_t> bytes;
        if (ReadArray(asset, State.OffMontageSlots, static_cast<size_t>(State.SlotStride), 64, slots, bytes) && slots.Num > 0)
        {
            take(static_cast<const uint8_t*>(slots.Data) + State.SlotTrack);
        }
    }
    else if (State.AnimCompositeClass && asset->IsA(State.AnimCompositeClass) && State.OffCompositeTrack >= 0)
    {
        take(base + State.OffCompositeTrack);
    }
}

// The AnimComposite of animations played one after another (a chained move, or a split move an auto match picked).
UObject* BuildComposite(const std::vector<UObject*>& animations, const std::vector<std::wstring>& labels, UObject* outer, std::wstring& why);

// The AnimComposite of a chained move: its animations one after another, built once and kept for the session.
UObject* BuildChain(const std::vector<std::wstring>& paths, UObject* outer, std::wstring& why)
{
    std::vector<UObject*> parts;
    for (const auto& path : paths)
    {
        const auto it = State.MoveObjects.find(Folded(path));
        UObject* animation = it == State.MoveObjects.end() ? nullptr : it->second;
        if (!animation) { why = path + L" was not found"; return nullptr; }
        parts.push_back(animation);
    }
    return BuildComposite(parts, paths, outer, why);
}

// The composite for a split move of an auto source, built once per set of pieces.
UObject* SplitMove(const std::vector<UObject*>& pieces, const std::vector<std::wstring>& labels, UObject* outer, std::wstring& why)
{
    std::wstring key = L"split|";
    for (UObject* piece : pieces) { key += Hex(reinterpret_cast<uintptr_t>(piece)) + L"|"; }
    if (const auto it = State.ChainObjects.find(key); it != State.ChainObjects.end())
    {
        if (!it->second) { why = L"could not be built before"; }
        return it->second;
    }
    UObject* composite = BuildComposite(pieces, labels, outer, why);
    State.ChainObjects[key] = composite;
    return composite;
}

UObject* BuildComposite(const std::vector<UObject*>& animations, const std::vector<std::wstring>& labels, UObject* outer, std::wstring& why)
{
    if (!State.AnimCompositeClass || State.OffCompositeTrack < 0 || State.TrackSegments < 0 || State.SegmentStride <= 0 || State.SegmentRef < 0 ||
        State.SegStartPos < 0 || State.SegAnimStart < 0 || State.SegAnimEnd < 0 || State.SegPlayRate < 0 || State.SegLooping < 0 || State.OffSeqLength < 0 ||
        State.OffAnimSkeleton < 0 || !State.AnimSequenceBaseClass)
    {
        why = L"the AnimComposite layout was not recognised";
        return nullptr;
    }
    const bool fromTemplate = State.SegmentTemplate.size() == static_cast<size_t>(State.SegmentStride);
    if (!fromTemplate && State.SegValid < 0)
    {
        why = L"the animation segment layout was not recognised";
        return nullptr;
    }
    std::vector<UObject*> parts;
    std::vector<float> lengths;
    UObject* skeleton = nullptr;
    for (size_t k = 0; k < animations.size(); ++k)
    {
        UObject* animation = animations[k];
        const std::wstring path = k < labels.size() ? labels[k] : std::to_wstring(k);
        if (!animation) { why = path + L" was not found"; return nullptr; }
        if (!animation->IsA(State.AnimSequenceBaseClass) || (State.AnimMontageClass && animation->IsA(State.AnimMontageClass)))
        {
            why = path + L" is not an animation sequence or composite";
            return nullptr;
        }
        float length = 0.0f;
        if (!ReadAt(animation, static_cast<size_t>(State.OffSeqLength), length) || !(length > 0.0f && length < 3600.0f)) { why = path + L" has no length"; return nullptr; }
        UObject* own = Field<UObject*>(animation, State.OffAnimSkeleton);
        if (!skeleton) { skeleton = own; }
        else if (own != skeleton)
        {
            why = L"its animations are on different skeletons (" + ShortName(skeleton) + L", " + ShortName(own) + L")";
            return nullptr;
        }
        parts.push_back(animation);
        lengths.push_back(length);
    }
    if (!skeleton) { why = L"its first animation has no skeleton"; return nullptr; }
    const size_t stride = static_cast<size_t>(State.SegmentStride);
    auto* data = static_cast<uint8_t*>(FMemory::Malloc(stride * parts.size()));
    if (!data) { why = L"out of memory"; return nullptr; }
    float position = 0.0f;
    const float one = 1.0f, zero = 0.0f;
    const int32_t once = 1;
    for (size_t k = 0; k < parts.size(); ++k)
    {
        uint8_t* segment = data + k * stride;
        if (fromTemplate) { std::memcpy(segment, State.SegmentTemplate.data(), stride); }
        else { std::memset(segment, 0, stride); }
        if (State.SegValid >= 0) { segment[State.SegValid] = 1; } // FAnimSegment::bValid
        std::memcpy(segment + State.SegmentRef, &parts[k], sizeof(UObject*));
        std::memcpy(segment + State.SegStartPos, &position, sizeof(float));
        std::memcpy(segment + State.SegAnimStart, &zero, sizeof(float));
        std::memcpy(segment + State.SegAnimEnd, &lengths[k], sizeof(float));
        std::memcpy(segment + State.SegPlayRate, &one, sizeof(float));
        std::memcpy(segment + State.SegLooping, &once, sizeof(int32_t));
        if (State.SegBlendTime >= 0) { std::memcpy(segment + State.SegBlendTime, &zero, sizeof(float)); }
        if (State.SegTriggerNotify >= 0) { segment[State.SegTriggerNotify] = 1; } // the pieces' sounds and effects still play
        position += lengths[k];
    }
    FStaticConstructObjectParameters params(State.AnimCompositeClass, outer);
    params.SetFlags = RF_Transient;
    UObject* composite = UObjectGlobals::StaticConstructObject(params);
    if (!composite || !composite->IsA(State.AnimCompositeClass))
    {
        FMemory::Free(data);
        why = L"the engine did not create the composite";
        return nullptr;
    }
    auto* track = reinterpret_cast<RawArray*>(reinterpret_cast<uint8_t*>(composite) + State.OffCompositeTrack + State.TrackSegments);
    if (track->Data || track->Num != 0)
    {
        FMemory::Free(data);
        why = L"a new composite came with segments";
        return nullptr;
    }
    track->Data = data;
    track->Num = static_cast<int32_t>(parts.size());
    track->Max = static_cast<int32_t>(parts.size());
    std::memcpy(reinterpret_cast<uint8_t*>(composite) + State.OffSeqLength, &position, sizeof(float));
    std::memcpy(reinterpret_cast<uint8_t*>(composite) + State.OffAnimSkeleton, &skeleton, sizeof(UObject*));
    composite->SetRootSet();
    return composite;
}

// The animation a move plays: its one animation, or the composite of its chain.
UObject* MoveAnimation(const SkelCompat::AnimMove& move, UObject* outer, std::wstring& notes)
{
    if (move.Chain.empty())
    {
        const auto it = State.MoveObjects.find(Folded(move.Animation));
        return it == State.MoveObjects.end() ? nullptr : it->second;
    }
    std::wstring key;
    for (const auto& path : move.Chain) { key += Folded(path) + L"|"; }
    if (const auto it = State.ChainObjects.find(key); it != State.ChainObjects.end()) { return it->second; }
    std::wstring why;
    UObject* composite = BuildChain(move.Chain, outer, why);
    State.ChainObjects[key] = composite;
    if (!composite) { notes += L"; chained move " + move.Key + L" NOT built (" + why + L")"; }
    else
    {
        float length = 0.0f;
        ReadAt(composite, static_cast<size_t>(State.OffSeqLength), length);
        Log.Line(L"Chained move " + move.Key + L": " + std::to_wstring(move.Chain.size()) + L" animations played one after another (" + Fixed(length) + L" s) as " +
                 ObjectPath(composite));
    }
    return composite;
}

SetBuild BuildSet(const SkelCompat::AnimSetRow& row, const std::wstring& name, UObject* own, UObject* pack, bool late, std::vector<uint8_t>& moveUsed)
{
    SetBuild result;
    struct Source
    {
        UObject* Set;
        std::wstring Label;
        SkelCompat::AutoMatchMode Auto;
        std::vector<std::wstring> Only;
    };
    std::vector<Source> sources;
    for (const auto& ref : SkelCompat::SetSourcesFor(row, name))
    {
        // The first of the source's paths that is resident (an auto folder source falls back to its first set of the kind).
        for (const auto& path : ref.Paths)
        {
            const auto it = State.SetObjects.find(Folded(path));
            UObject* set = it == State.SetObjects.end() ? nullptr : it->second;
            if (!set) { continue; }
            if (std::none_of(sources.begin(), sources.end(), [&](const Source& s) { return s.Set == set; }))
            {
                sources.push_back({set, SourceLabel(path) + (ref.Auto == SkelCompat::AutoMatchMode::Off ? L"" : L" (auto)"), ref.Auto, ref.Only});
            }
            break;
        }
    }
    std::wstring notes;
    if (own && std::none_of(sources.begin(), sources.end(), [&](const Source& s) { return s.Set == own; }))
    {
        if (own->HasAnyFlags(RF_NeedLoad)) { notes += L"; the pack's own " + name + L" was not loaded yet and is left out"; }
        else { sources.push_back({own, L"the pack's own " + SourceLabel(ObjectPath(own)), SkelCompat::AutoMatchMode::Off, {}}); }
    }
    const bool anyAuto = std::any_of(sources.begin(), sources.end(), [](const Source& s) { return s.Auto != SkelCompat::AutoMatchMode::Off; });
    const std::vector<const SkelCompat::AnimMove*> moves = SkelCompat::MovesFor(row, name);
    if (sources.empty())
    {
        if (std::any_of(moves.begin(), moves.end(), [](const SkelCompat::AnimMove* m) { return !m->Set.empty(); }))
        {
            result.Note = L"no source set found, so its moves are not applied";
        }
        return result;
    }
    // One source named like the set and no moves: the pack lists that set itself.
    if (!anyAuto && sources.size() == 1 && moves.empty())
    {
        if (sources[0].Set == own) { return result; }
        if (SkelCompat::NameEquals(ShortName(sources[0].Set), name))
        {
            result.Set = sources[0].Set;
            result.Note = L"uses " + sources[0].Label + notes;
            return result;
        }
    }
    std::vector<std::vector<NameObjectEntry>> read(sources.size());
    std::vector<size_t> usable;
    for (size_t k = 0; k < sources.size(); ++k)
    {
        std::wstring why;
        if (!ReadNameObjectMap(reinterpret_cast<const uint8_t*>(sources[k].Set) + State.OffSetAssets, read[k], why))
        {
            notes += L"; " + sources[k].Label + L" left out (" + why + L")";
            continue;
        }
        usable.push_back(k);
    }
    std::vector<NameObjectEntry> merged;
    std::wstring counts, picks;
    if (!anyAuto)
    {
        // First source wins per animation name.
        std::unordered_map<uint64_t, size_t> index;
        for (const size_t k : usable)
        {
            int32_t added = 0;
            for (const auto& entry : read[k])
            {
                if (index.emplace(entry.Key, merged.size()).second)
                {
                    merged.push_back(entry);
                    ++added;
                }
            }
            counts += (counts.empty() ? L"" : L", ") + std::to_wstring(added) + L" from " + sources[k].Label;
        }
    }
    else
    {
        // Ordinary sources: first wins; auto sources fill the names they are asked for (SkelCompat::MergeSetSources).
        std::vector<SkelCompat::MergeSource> inputs;
        for (const size_t k : usable)
        {
            SkelCompat::MergeSource input;
            input.Auto = sources[k].Auto;
            input.Only = sources[k].Only;
            for (const auto& entry : read[k])
            {
                input.Keys.push_back(entry.Key);
                input.Anims.push_back(MatchInfo(entry.Key, static_cast<UObject*>(entry.Value)));
            }
            inputs.push_back(std::move(input));
        }
        std::vector<int32_t> added(inputs.size(), 0), matched(inputs.size(), 0);
        for (const auto& e : SkelCompat::MergeSetSources(inputs))
        {
            const auto& entries = read[usable[e.Source]];
            void* value = entries[e.Entry].Value;
            std::wstring pickedName = inputs[e.Source].Anims[e.Entry].Name;
            float pickedLength = inputs[e.Source].Anims[e.Entry].Length;
            if (e.Chain.size() > 1)
            {
                // A split move: its pieces played one after another as one animation.
                std::vector<UObject*> pieces;
                std::vector<std::wstring> labels;
                pickedLength = 0.0f;
                for (const size_t piece : e.Chain)
                {
                    pieces.push_back(static_cast<UObject*>(entries[piece].Value));
                    labels.push_back(inputs[e.Source].Anims[piece].Name);
                    pickedLength += inputs[e.Source].Anims[piece].Length;
                }
                pickedName = labels.front();
                for (size_t k = 1; k < labels.size(); ++k) { pickedName += L" + " + labels[k]; }
                std::wstring why;
                if (UObject* composite = SplitMove(pieces, labels, pack, why)) { value = composite; }
                else { notes += L"; " + pickedName + L" played as its first piece (" + why + L")"; }
            }
            merged.push_back({e.Key, value});
            ++added[e.Source];
            if (e.Tier < 2) { continue; }
            ++matched[e.Source];
            const SkelCompat::MatchAnim picked{pickedName, pickedLength, false};
            float before = 0.0f;
            for (size_t i = 0; i < inputs.size() && before == 0.0f; ++i)
            {
                if (inputs[i].Auto != SkelCompat::AutoMatchMode::Off) { continue; }
                for (size_t j = 0; j < inputs[i].Keys.size(); ++j)
                {
                    if (inputs[i].Keys[j] == e.Key)
                    {
                        before = inputs[i].Anims[j].Length;
                        break;
                    }
                }
            }
            picks += L"\n        " + NameText(e.Key) + L" (" + Fixed(before) + L" s) <- " + picked.Name + L" (" + Fixed(picked.Length) + L" s, " +
                     (e.Tier == 2 ? L"another variant of the move" : L"same kind, closest length") + L")";
        }
        for (size_t i = 0; i < inputs.size(); ++i)
        {
            counts += (counts.empty() ? L"" : L", ") + std::to_wstring(added[i]) + L" from " + sources[usable[i]].Label +
                      (matched[i] ? L" (" + std::to_wstring(matched[i]) + L" auto-matched)" : std::wstring{});
        }
    }
    // Moves: replace an animation name wherever the set has it; a move naming this set may also add a name.
    int32_t applied = 0;
    if (!moves.empty() && !merged.empty())
    {
        std::vector<std::wstring> texts;
        texts.reserve(merged.size());
        for (const auto& entry : merged) { texts.push_back(NameText(entry.Key)); }
        for (const SkelCompat::AnimMove* move : moves)
        {
            const size_t moveIndex = static_cast<size_t>(move - row.Moves.data());
            UObject* animation = MoveAnimation(*move, pack, notes);
            if (!animation) { continue; } // reported once by the preload (or in the notes for a chain)
            bool done = false;
            for (size_t k = 0; k < texts.size(); ++k)
            {
                if (SkelCompat::NameEquals(texts[k], move->Key))
                {
                    merged[k].Value = animation;
                    done = true;
                    break;
                }
            }
            if (!done && !move->Set.empty())
            {
                // A name no source of this set has: only one the game already uses somewhere can be looked up.
                const RawName key = RawNameOf(FName(move->Key.c_str(), FNAME_Find));
                if (key.Comparison != 0 || key.Number != 0)
                {
                    merged.push_back({KeyOf(key), animation});
                    texts.push_back(move->Key);
                    done = true;
                }
                else
                {
                    notes += L"; move " + move->Key + L" skipped: the game uses no animation of that name";
                }
            }
            if (done)
            {
                ++applied;
                if (moveIndex < moveUsed.size()) { moveUsed[moveIndex] = 1; }
            }
        }
    }
    if (merged.empty())
    {
        result.Note = L"its sources hold no animations" + notes;
        return result;
    }
    if (!anyAuto && applied == 0 && sources.size() == 1 && SkelCompat::NameEquals(ShortName(sources[0].Set), name))
    {
        // No move named anything in it: as above, the one source serves as it is.
        if (sources[0].Set == own) { return result; }
        result.Set = sources[0].Set;
        result.Note = L"uses " + sources[0].Label + notes;
        return result;
    }
    const int32_t form = NameHashForm();
    if (form < 0)
    {
        result.Note = L"NOT built: the game's FName hash form is not confirmed (see the FName hash line)";
        return result;
    }
    // The set's name: the FName of a set already called that, else one the game knows.
    RawName setName{};
    bool named = false;
    for (UObject* candidate : {own, sources.front().Set})
    {
        if (candidate && SkelCompat::NameEquals(ShortName(candidate), name))
        {
            setName = ObjectRawName(candidate);
            named = true;
            break;
        }
    }
    for (size_t k = 0; !named && k < sources.size(); ++k)
    {
        if (SkelCompat::NameEquals(ShortName(sources[k].Set), name))
        {
            setName = ObjectRawName(sources[k].Set);
            named = true;
        }
    }
    if (!named)
    {
        setName = RawNameOf(FName(name.c_str(), FNAME_Find));
        named = setName.Comparison != 0 || setName.Number != 0;
    }
    if (!named)
    {
        result.Note = L"NOT built: no set of the game is called " + name;
        return result;
    }
    FStaticConstructObjectParameters params(State.AnimSetClass, pack);
    std::memcpy(static_cast<void*>(&params.Name), &setName, sizeof(setName));
    params.SetFlags = RF_Transient;
    params.Template = sources.front().Set; // every setting but the map comes from the first source
    UObject* set = UObjectGlobals::StaticConstructObject(params);
    if (!set || !set->IsA(State.AnimSetClass))
    {
        result.Note = L"NOT built: the engine did not create the set";
        return result;
    }
    if (State.OffSetDisplayName >= 0) { std::memcpy(reinterpret_cast<uint8_t*>(set) + State.OffSetDisplayName, &setName, sizeof(setName)); }
    if (!WriteNameObjectMap(reinterpret_cast<uint8_t*>(set) + State.OffSetAssets, merged, form == 1))
    {
        result.Note = L"NOT built: out of memory for its map";
        return result; // the new set is unreferenced and goes with the next garbage collection
    }
    // A pack that was already loaded may sit in a garbage-collection cluster that does not know the new set: keep it.
    if (late) { set->SetRootSet(); }
    result.Set = set;
    result.Note = std::to_wstring(merged.size()) + L" animations (" + counts + L")" +
                  (applied ? L", " + std::to_wstring(applied) + L" move(s)" : std::wstring{}) + notes +
                  (picks.empty() ? std::wstring{} : L"\n      auto-matched (\"moves\" can replace any of these):" + picks);
    return result;
}

// Appends `object` to the AssetUserData of AssetDataList entry `entry` of a pack.
bool AppendPackObject(UObject* pack, int32_t entry, UObject* object)
{
    RawArray* objects = PackObjects(pack, entry);
    if (!objects) { return false; }
    const int32_t wanted = objects->Num + 1;
    if (wanted > objects->Max)
    {
        void* grown = FMemory::Realloc(objects->Data, static_cast<size_t>(wanted) * sizeof(void*));
        if (!grown) { return false; }
        objects->Data = grown;
        objects->Max = wanted;
    }
    static_cast<UObject**>(objects->Data)[objects->Num] = object;
    objects->Num = wanted;
    return true;
}

// 3.3.1 "pack_assets": objects the row adds to the pack (another character's effect pack, a sound bank). Each goes into
// the AssetDataList entry that already lists an object of its class (else `fallbackEntry`, the entry of the sets), the
// way the game's own packs list them. They are loaded at the first map load. Returns lines for the log.
std::wstring AddPackAssets(UObject* pack, const SkelCompat::AnimSetRow& row, int32_t fallbackEntry)
{
    std::wstring text;
    RawArray list{};
    std::vector<uint8_t> bytes;
    if (row.PackAssets.empty()) { return text; }
    if (!ReadArray(pack, State.OffPackList, static_cast<size_t>(State.PackEntryStride), 4096, list, bytes))
    {
        return L"\n    pack assets NOT added: AssetDataList unreadable";
    }
    for (const auto& path : row.PackAssets)
    {
        UObject* asset = FindObjectByPath(path.c_str());
        if (!asset)
        {
            text += L"\n    pack asset " + path + L" NOT added: not loaded (pack assets load at the first map load)";
            continue;
        }
        UClass* type = asset->GetClassPrivate();
        int32_t entry = -1;
        bool already = false;
        for (int32_t e = 0; e < list.Num && !already; ++e)
        {
            RawArray* objects = PackObjects(pack, e);
            if (!objects) { continue; }
            for (int32_t i = 0; i < objects->Num; ++i)
            {
                UObject* object = static_cast<UObject**>(objects->Data)[i];
                if (object == asset) { already = true; break; }
                if (entry < 0 && object && object->GetClassPrivate() == type) { entry = e; }
            }
        }
        if (already) { continue; }
        if (entry < 0) { entry = fallbackEntry; }
        const bool added = AppendPackObject(pack, entry, asset);
        if (added) { asset->SetRootSet(); }
        text += L"\n    pack asset " + ShortNameOfPath(path) + (added ? L" added to entry " + std::to_wstring(entry) : std::wstring(L" NOT added: the pack has no such entry"));
    }
    return text;
}

// Puts the row's sets into a pack's list. `late`: the pack was loaded before (the game may already use its sets).
void MergePack(UObject* pack, bool late)
{
    const std::wstring path = ObjectPath(pack);
    const SkelCompat::AnimSetRow* row = State.Config.FindAnimSetRow(path);
    if (!row) { return; }
    std::wstring text = L"Animation sets of " + path + (late ? L" (already loaded)" : L"") + L":";
    std::vector<PackSlot> slots;
    int32_t entries = 0;
    std::wstring why;
    if (!ReadPackSets(pack, slots, entries, why))
    {
        text += L" left as they are: " + why;
    }
    else if (std::any_of(slots.begin(), slots.end(), [&](const PackSlot& s) { return s.Set->GetOuterPrivate() == pack; }))
    {
        return; // merged before
    }
    else
    {
        std::vector<std::wstring> names;
        const auto add = [&](const std::wstring& name) {
            if (std::none_of(names.begin(), names.end(), [&](const std::wstring& n) { return SkelCompat::NameEquals(n, name); })) { names.push_back(name); }
        };
        for (const auto& slot : slots) { add(slot.Name); }
        for (const auto& name : SkelCompat::RowSetNames(*row)) { add(name); }
        std::vector<uint8_t> moveUsed(row->Moves.size(), 0);
        std::vector<std::pair<std::wstring, UObject*>> changes;
        for (const auto& name : names)
        {
            UObject* own = nullptr;
            for (const auto& slot : slots)
            {
                if (SkelCompat::NameEquals(slot.Name, name))
                {
                    own = slot.Set;
                    break;
                }
            }
            const SetBuild build = BuildSet(*row, name, own, pack, late, moveUsed);
            if (!build.Note.empty()) { text += L"\n    " + name + L": " + build.Note; }
            if (build.Set && build.Set != own) { changes.emplace_back(name, build.Set); }
        }
        for (size_t m = 0; m < row->Moves.size(); ++m)
        {
            const auto& move = row->Moves[m];
            if (!moveUsed[m] && State.MoveObjects[Folded(move.Animation)])
            {
                text += L"\n    move " + (move.Set.empty() ? std::wstring{} : move.Set + L"/") + move.Key + L": no set of this pack has that name";
            }
        }
        // Replace every slot of a changed name; names the pack did not have go into the entry that lists its sets.
        std::vector<UObject*> appended;
        int32_t replaced = 0;
        for (const auto& [name, set] : changes)
        {
            bool found = false;
            for (const auto& slot : slots)
            {
                if (!SkelCompat::NameEquals(slot.Name, name)) { continue; }
                RawArray* objects = PackObjects(pack, slot.Entry);
                if (!objects || slot.Index >= objects->Num) { continue; }
                auto** at = static_cast<UObject**>(objects->Data) + slot.Index;
                if (late && *at) { (*at)->SetRootSet(); } // the game may still hold the set it had
                *reinterpret_cast<UObject* volatile*>(at) = set;
                found = true;
                ++replaced;
            }
            if (!found) { appended.push_back(set); }
        }
        if (!appended.empty())
        {
            const int32_t entry = slots.empty() ? 0 : slots.front().Entry;
            RawArray* objects = PackObjects(pack, entry);
            const int32_t wanted = objects ? objects->Num + static_cast<int32_t>(appended.size()) : 0;
            if (!objects)
            {
                text += L"\n    " + std::to_wstring(appended.size()) + L" set(s) not added: the pack has no AssetDataList entry";
                appended.clear();
            }
            else
            {
                if (wanted > objects->Max)
                {
                    void* grown = FMemory::Realloc(objects->Data, static_cast<size_t>(wanted) * sizeof(void*));
                    if (grown)
                    {
                        objects->Data = grown;
                        objects->Max = wanted;
                    }
                }
                if (wanted <= objects->Max)
                {
                    std::memcpy(static_cast<UObject**>(objects->Data) + objects->Num, appended.data(), appended.size() * sizeof(void*));
                    objects->Num = wanted;
                }
                else
                {
                    text += L"\n    " + std::to_wstring(appended.size()) + L" set(s) not added: out of memory";
                    appended.clear();
                }
            }
        }
        text += L"\n    -> " + std::to_wstring(replaced) + L" set(s) replaced, " + std::to_wstring(appended.size()) + L" added";
        text += AddPackAssets(pack, *row, slots.empty() ? 0 : slots.front().Entry);
        State.PacksMerged.fetch_add(1, std::memory_order_relaxed);
    }
    Log.Line(text);
    std::lock_guard lock(State.PackMutex);
    if (State.MergeLines.size() < 64) { State.MergeLines.push_back(text); }
}

// Packs loaded before the rows were ready (game thread).
void MergeLoadedPacks()
{
    std::vector<UObject*> packs;
    UObjectGlobals::ForEachUObject([&](UObject* object, int32, int32) -> LoopAction {
        if (!object || object->HasAnyFlags(TemplateFlags) || object->HasAnyFlags(DeadFlags)) { return LoopAction::Continue; }
        UClass* type = object->GetClassPrivate();
        if (type && type->IsChildOf(State.PackClass) && State.PackNames.count(Folded(ShortName(object))) > 0) { packs.push_back(object); }
        return LoopAction::Continue;
    });
    for (UObject* pack : packs)
    {
        if (!FlagsReady(pack)) { continue; } // still loading: its own PostLoad merges it
        if (std::find(State.MergedPacks.begin(), State.MergedPacks.end(), pack) != State.MergedPacks.end()) { continue; }
        State.MergedPacks.push_back(pack);
        MergePack(pack, true);
    }
}

// Packs whose PostLoad ran off the game thread, or that were still loading at the late pass (game thread).
void MergeQueuedPacks()
{
    std::vector<UObject*> queue;
    {
        std::lock_guard lock(State.PackMutex);
        queue.swap(State.PacksToMerge);
    }
    std::vector<UObject*> later;
    for (UObject* pack : queue)
    {
        if (!Alive(pack)) { continue; }
        if (!FlagsReady(pack))
        {
            later.push_back(pack);
            continue;
        }
        if (std::find(State.MergedPacks.begin(), State.MergedPacks.end(), pack) != State.MergedPacks.end()) { continue; }
        State.MergedPacks.push_back(pack);
        MergePack(pack, true);
    }
    if (!later.empty())
    {
        std::lock_guard lock(State.PackMutex);
        State.PacksToMerge.insert(State.PacksToMerge.end(), later.begin(), later.end());
        RequestWork();
    }
}

void* OriginalPackPostLoad(UObject* self)
{
    void** table = nullptr;
    std::memcpy(&table, self, sizeof(table));
    const int32_t count = State.PackPatchCount.load(std::memory_order_acquire);
    for (int32_t i = 0; i < count; ++i)
    {
        if (State.PackPatches[static_cast<size_t>(i)].Table == table) { return State.PackPatches[static_cast<size_t>(i)].Original; }
    }
    return nullptr;
}

// Before the engine's PostLoad, so anything the pack builds from its list already sees the merged sets.
void HookedPackPostLoad(UObject* self)
{
    if (State.Active.load(std::memory_order_acquire) && State.SetsReady.load(std::memory_order_acquire))
    {
        try
        {
            if (State.PackNames.count(Folded(ShortName(self))) > 0)
            {
                if (OnGameThread()) { MergePack(self, false); }
                else
                {
                    std::lock_guard lock(State.PackMutex);
                    State.PacksToMerge.push_back(self);
                    RequestWork();
                }
            }
        }
        catch (...)
        {
            Fault(L"animation set rows");
        }
    }
    if (auto* original = reinterpret_cast<PostLoadFunction>(OriginalPackPostLoad(self))) { original(self); }
}

// Patches PostLoad of the pack class and its native subclasses (slot verified by the mesh hook).
bool InstallPackPostLoadHook()
{
    const ImageRange image = MainImage();
    std::vector<void**> tables;
    UObjectGlobals::ForEachUObject([&](UObject* object, int32, int32) -> LoopAction {
        if (!object || !object->IsA<UClass>()) { return LoopAction::Continue; }
        auto* type = static_cast<UClass*>(object);
        if (!type->IsChildOf(State.PackClass)) { return LoopAction::Continue; }
        void** table = VTableOf(type->GetClassDefaultObject());
        if (table && image.Contains(table) && std::find(tables.begin(), tables.end(), table) == tables.end()) { tables.push_back(table); }
        return LoopAction::Continue;
    });
    int32_t installed = 0;
    for (void** table : tables)
    {
        if (installed >= static_cast<int32_t>(State.PackPatches.size())) { break; }
        void* current = SlotOf(table, PostLoadSlot);
        if (!image.Contains(current)) { continue; }
        auto& patch = State.PackPatches[static_cast<size_t>(installed)];
        patch.Table = table;
        patch.Original = current;
        State.PackPatchCount.store(installed + 1, std::memory_order_release);
        void* replaced = nullptr;
        if (PatchSlot(table, PostLoadSlot, reinterpret_cast<void*>(&HookedPackPostLoad), replaced))
        {
            patch.Original = replaced;
            ++installed;
        }
        else
        {
            State.PackPatchCount.store(installed, std::memory_order_release);
        }
    }
    Log.Line(L"CharaSpec pack PostLoad hook installed on " + std::to_wstring(installed) + L" vtable(s)");
    return installed > 0;
}

// ---------------------------------------------------------------------------------------
// AnimBlueprints of family members follow the hub (3.2.1)
// ---------------------------------------------------------------------------------------
// The hub of a family member's skeleton (resident), or null.
UObject* HubOfMember(UObject* skeleton)
{
    if (!skeleton || State.AbpHubs.empty() || !UObject::IsReal(skeleton)) { return nullptr; }
    const auto it = State.AbpHubs.find(Folded(ObjectPath(skeleton)));
    if (it == State.AbpHubs.end()) { return nullptr; }
    if (UObject* hub = RootedSkeleton(it->second)) { return hub; }
    if (!OnGameThread()) { return nullptr; } // the map-load pass picks the class up once the hub is resident
    UObject* found = UObjectGlobals::StaticFindObject<UObject*>(nullptr, nullptr, it->second);
    return (found && State.SkeletonClass && found->IsA(State.SkeletonClass)) ? found : nullptr;
}

// Points an AnimBlueprint class made for a family member at the hub: every mesh of the member is rebound to the hub and
// every animation of the member is adopted onto it, so the AnimBlueprint finds everything it plays there. Returns true
// when the class was moved.
bool MoveAnimBlueprint(UObject* abpClass, const wchar_t* how)
{
    if (!abpClass || State.OffAbpTargetSkeleton < 0 || State.AbpHubs.empty() || abpClass->HasAnyFlags(DeadFlags)) { return false; }
    UObject* target = nullptr;
    if (!ReadAt(abpClass, static_cast<size_t>(State.OffAbpTargetSkeleton), target) || !target) { return false; }
    UObject* hub = HubOfMember(target);
    if (!hub || hub == target) { return false; }
    *reinterpret_cast<UObject* volatile*>(reinterpret_cast<uint8_t*>(abpClass) + State.OffAbpTargetSkeleton) = hub;
    const std::wstring line = L"AnimBlueprint " + ObjectPath(abpClass) + L" (made for " + ShortName(target) + L") now runs on " + ShortName(hub) +
                              L", the hub its meshes are rebound to (" + how + L")";
    {
        std::lock_guard lock(State.AbpMutex);
        State.AbpMoved.push_back(abpClass);
        if (State.AbpLines.size() < 64) { State.AbpLines.push_back(line); }
    }
    State.AbpRepairWanted.store(true, std::memory_order_release);
    RequestWork();
    Log.Line(line);
    return true;
}

void* OriginalAbpPostLoad(UObject* self)
{
    void** table = nullptr;
    std::memcpy(&table, self, sizeof(table));
    const int32_t count = State.AbpPatchCount.load(std::memory_order_acquire);
    for (int32_t i = 0; i < count; ++i)
    {
        if (State.AbpPatches[static_cast<size_t>(i)].Table == table) { return State.AbpPatches[static_cast<size_t>(i)].Original; }
    }
    return nullptr;
}

// After the engine's PostLoad: the class is complete, and no component has spawned an instance of it yet.
void HookedAbpPostLoad(UObject* self)
{
    if (auto* original = reinterpret_cast<PostLoadFunction>(OriginalAbpPostLoad(self))) { original(self); }
    if (!State.Active.load(std::memory_order_acquire)) { return; }
    try
    {
        MoveAnimBlueprint(self, L"on load");
    }
    catch (...)
    {
        Fault(L"AnimBlueprints that follow the hub");
    }
}

// Patches PostLoad of UAnimBlueprintGeneratedClass and its native subclasses (slot verified by the mesh hook).
bool InstallAbpPostLoadHook()
{
    const ImageRange image = MainImage();
    std::vector<void**> tables;
    UObjectGlobals::ForEachUObject([&](UObject* object, int32, int32) -> LoopAction {
        if (!object || !object->IsA<UClass>()) { return LoopAction::Continue; }
        auto* type = static_cast<UClass*>(object);
        if (!type->IsChildOf(State.AbpClass)) { return LoopAction::Continue; }
        void** table = VTableOf(type->GetClassDefaultObject());
        if (table && image.Contains(table) && std::find(tables.begin(), tables.end(), table) == tables.end()) { tables.push_back(table); }
        return LoopAction::Continue;
    });
    int32_t installed = 0;
    for (void** table : tables)
    {
        if (installed >= static_cast<int32_t>(State.AbpPatches.size())) { break; }
        void* current = SlotOf(table, PostLoadSlot);
        if (!image.Contains(current)) { continue; }
        auto& patch = State.AbpPatches[static_cast<size_t>(installed)];
        patch.Table = table;
        patch.Original = current;
        State.AbpPatchCount.store(installed + 1, std::memory_order_release);
        void* replaced = nullptr;
        if (PatchSlot(table, PostLoadSlot, reinterpret_cast<void*>(&HookedAbpPostLoad), replaced))
        {
            patch.Original = replaced;
            ++installed;
        }
        else
        {
            State.AbpPatchCount.store(installed, std::memory_order_release);
        }
    }
    Log.Line(L"AnimBlueprint PostLoad hook installed on " + std::to_wstring(installed) + L" vtable(s)");
    return installed > 0;
}

// AnimBlueprint classes already loaded (game thread, safe point).
void MoveLoadedAnimBlueprints()
{
    if (!State.AbpClass || State.OffAbpTargetSkeleton < 0 || State.AbpHubs.empty()) { return; }
    std::vector<UObject*> classes;
    UObjectGlobals::ForEachUObject([&](UObject* object, int32, int32) -> LoopAction {
        if (!object || object->HasAnyFlags(DeadFlags)) { return LoopAction::Continue; }
        UClass* type = object->GetClassPrivate();
        if (type && type->IsChildOf(State.AbpClass)) { classes.push_back(object); }
        return LoopAction::Continue;
    });
    for (UObject* type : classes) { MoveAnimBlueprint(type, L"already loaded"); }
}

// Components whose AnimBlueprint the engine refused before its class was moved get it again (game thread).
void RepairMovedAnimBlueprints()
{
    if (!State.AbpRepairWanted.exchange(false, std::memory_order_acq_rel)) { return; }
    if (!State.SetAnimClass || !State.ComponentClass || State.OffCompMesh < 0 || State.OffCompAnimClass < 0 || State.OffCompAnimInstance < 0) { return; }
    std::vector<UObject*> moved;
    {
        std::lock_guard lock(State.AbpMutex);
        moved = State.AbpMoved;
    }
    if (moved.empty()) { return; }
    struct Waiting
    {
        UObject* Component;
        UObject* AnimClass;
        UObject* Mesh;
    };
    std::vector<Waiting> waiting;
    UObjectGlobals::ForEachUObject([&](UObject* object, int32, int32) -> LoopAction {
        if (!object || object->HasAnyFlags(TemplateFlags) || object->HasAnyFlags(DeadFlags)) { return LoopAction::Continue; }
        UClass* type = object->GetClassPrivate();
        if (!type || !type->IsChildOf(State.ComponentClass)) { return LoopAction::Continue; }
        UObject* animClass = Field<UObject*>(object, State.OffCompAnimClass);
        if (!animClass || Field<UObject*>(object, State.OffCompAnimInstance)) { return LoopAction::Continue; }
        if (std::find(moved.begin(), moved.end(), animClass) == moved.end()) { return LoopAction::Continue; }
        waiting.push_back({object, animClass, Field<UObject*>(object, State.OffCompMesh)});
        return LoopAction::Continue;
    });
    for (const Waiting& w : waiting)
    {
        UObject* meshSkeleton = w.Mesh ? RawMeshSkeleton(w.Mesh) : nullptr;
        if (!meshSkeleton || meshSkeleton != TargetSkeletonOf(w.AnimClass))
        {
            Log.Line(L"AnimBlueprint not re-initialised on " + ObjectPath(w.Component) + L": its mesh " + (w.Mesh ? ObjectPath(w.Mesh) : std::wstring(L"(none)")) +
                     L" is on " + (meshSkeleton ? ShortName(meshSkeleton) : std::wstring(L"no skeleton")) + L", not on the hub");
            continue;
        }
        CallSetAnimClass(w.Component, nullptr);
        CallSetAnimClass(w.Component, w.AnimClass);
        UObject* instance = Field<UObject*>(w.Component, State.OffCompAnimInstance);
        ++State.AbpRepaired;
        Log.Line(L"Re-initialised AnimBlueprint " + ShortName(w.AnimClass) + L" on " + ObjectPath(w.Component) +
                 (instance ? L" (instance spawned)" : L" (still refused: see the hierarchy check for " + ObjectPath(w.Mesh) + L")"));
    }
}

void Diagnose()
{
    std::vector<ReboundMesh> todo;
    {
        std::lock_guard lock(State.Mutex);
        for (const auto& record : State.Rebound)
        {
            if (!record.Diagnosed) { todo.push_back(record); }
        }
    }
    for (auto& record : todo)
    {
        std::wstring result;
        SkelCompat::BoneTable meshBones, skeletonBones;
        const bool meshAlive = Alive(record.Mesh);
        const bool targetAlive = Alive(record.Target);
        if (!meshAlive || !targetAlive)
        {
            result = L"unloaded before it could be checked";
        }
        else if (!FlagsReady(record.Mesh) || !FlagsReady(record.Target))
        {
            bool giveUp = false;
            {
                std::lock_guard lock(State.Mutex);
                for (auto& stored : State.Rebound)
                {
                    if (stored.Mesh == record.Mesh) { giveUp = ++stored.Attempts > 40; }
                }
            }
            if (!giveUp) { continue; } // still loading; diagnose on a later pump
            result = L"not checked: the mesh was still loading after 10 s";
        }
        else if (!ReadMeshBones(record.Mesh, meshBones) || !ReadSkeletonBones(record.Target, skeletonBones))
        {
            result = L"bone tables could not be read; hierarchy not checked";
        }
        else
        {
            const SkelCompat::MeshCheck check = SkelCompat::CheckMeshAgainstSkeleton(meshBones, skeletonBones);
            result = std::to_wstring(check.Matched) + L" shared bone(s), " + std::to_wstring(check.MeshOnly) +
                     L" mesh-only (reference pose / physics), " + std::to_wstring(check.SkeletonOnly) + L" animation-only (ignored). ";
            result += check.Compatible ? L"Hierarchy OK: AnimBlueprints for this skeleton will run."
                                       : L"Hierarchy REFUSED by the engine (T-pose): " + check.Problem;
            for (UObject* keepSkeleton : record.KeepCompatible)
            {
                // The engine runs an AnimBlueprint only on meshes of the skeleton it targets: one made for another
                // skeleton runs here only once it is moved to this mesh's skeleton (family members, 3.2.1).
                if (!Alive(keepSkeleton)) { continue; }
                const bool follows = State.OffAbpTargetSkeleton >= 0 && HubOfMember(keepSkeleton) == record.Target;
                result += follows ? L" AnimBlueprints made for " + ShortName(keepSkeleton) + L" are moved to " + ShortName(record.Target) + L" and run on it."
                                  : L" AnimBlueprints made for " + ShortName(keepSkeleton) + L" do NOT run on it (the engine needs the AnimBlueprint's own "
                                    L"skeleton): use one made for " + ShortName(record.Target) + L".";
            }
            if (record.Renamed > 0)
            {
                result += L" (" + std::to_wstring(record.Renamed) + L" bone(s) renamed by the hierarchy fix keep this mesh's own pose)";
            }
            else if (!check.Compatible && !record.HierarchyNote.empty())
            {
                result += L" Hierarchy fix: " + record.HierarchyNote;
            }
            RawArray virtualBones{};
            if (record.Late && State.OffSkelVirtualBones >= 0 &&
                ReadAt(record.Target, static_cast<size_t>(State.OffSkelVirtualBones), virtualBones) && virtualBones.Num > 0)
            {
                result += L" Note: rebound after load, so the skeleton's " + std::to_wstring(virtualBones.Num) +
                          L" virtual bone(s) are missing on this mesh until it is reloaded.";
            }
        }
        Log.Line(L"Check " + record.MeshPath + L": " + result);
        std::lock_guard lock(State.Mutex);
        for (auto& stored : State.Rebound)
        {
            if (stored.Mesh == record.Mesh)
            {
                stored.Diagnosed = true;
                stored.Diagnosis = result;
            }
        }
    }
}

std::wstring PostLoadStats()
{
    LARGE_INTEGER frequency{};
    QueryPerformanceFrequency(&frequency);
    const uint64_t calls = State.PostLoadCalls.load();
    const double perTick = frequency.QuadPart > 0 ? 1e6 / static_cast<double>(frequency.QuadPart) : 0.0;
    const double total = static_cast<double>(State.PostLoadTicks.load()) * perTick;
    wchar_t buffer[200]{};
    swprintf_s(buffer, L"%llu mesh load(s) checked, %.1f us average, %.1f us max, %llu with the skeleton still loading",
               static_cast<unsigned long long>(calls), calls ? total / static_cast<double>(calls) : 0.0,
               static_cast<double>(State.PostLoadMaxTicks.load()) * perTick, static_cast<unsigned long long>(State.SkeletonNotLoaded.load()));
    return buffer;
}

// ---------------------------------------------------------------------------------------
// 3.3: abilities per animation pack
// A player character's command menu and limit breaks are listed by its BattlePlayerParameter row (CommandAbilityID_Array,
// LimitAbilityID_Array) in the game's frozen data object, which the game reads in place. The object's table holder comes
// from its vtable slot 0x2C0 (0x2B8 while byte 0x54 is clear), as the game's own row lookup gets it; the holder's +8 is
// the frozen root (SkelCompat::Frozen). When a character's primary animation pack switches (EndBattleAPI
// SetPrimaryAnimPack / ResetPrimaryAnimPack, from a Lua mod or a Blueprint), the two arrays of its row are pointed at
// the lists the row's "abilities" give for the new pack: the pack's own list, else Battle00's, else the table's own.
// Map loads apply the Battle00 lists. Nothing is resized: the arrays point at lists the mod keeps for the session, and
// an ability that is not a row of the resident BattleAbility table is left out. Game thread only.
// The game copies a party member's lists out of the row (its first 5 commands and 3 limits, then its weapons' and
// materia's abilities) when it recalculates the member's status, so after a switch the mod has it recalculate:
// EndMenuBPAPI BPSetPlayerExperience(member, the EXP it already has), unless the row says "refresh_abilities": false.
// 3.3.1: the rows can sit in memory the game maps read-only, so the mod hands out the lists through the game's own list
// getters (ListGetters) and writes the rows only where it could not find those.
// ---------------------------------------------------------------------------------------
constexpr wchar_t PlayerTablePath[] = L"/Game/DataObject/Resident/BattlePlayerParameter.BattlePlayerParameter";
constexpr wchar_t AbilityTablePath[] = L"/Game/DataObject/Resident/BattleAbility.BattleAbility";

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

// The frozen root of an EndDataObject, found the way the game's row lookup finds it.
uintptr_t DataObjectRoot(UObject* object, std::wstring& why)
{
    UClass* type = object->GetClassPrivate();
    const std::wstring className = type ? type->GetName() : std::wstring{};
    if (className.find(L"DataObject") == std::wstring::npos)
    {
        why = L"not a data object (" + className + L")";
        return 0;
    }
    void** vtable = nullptr;
    uint8_t ready = 0;
    if (!ReadAt(object, 0, vtable) || !vtable || !ReadAt(object, 0x54, ready))
    {
        why = L"object unreadable";
        return 0;
    }
    void* slot = nullptr;
    if (!ReadAt(vtable, ready ? 0x2C0 : 0x2B8, slot) || !MainImage().Contains(slot))
    {
        why = L"its table getter is not in the game's code";
        return 0;
    }
    using GetTable = void* (*)(UObject*);
    void* holder = reinterpret_cast<GetTable>(slot)(object);
    uintptr_t root = 0;
    if (!holder || !ReadAt(holder, 8, root) || !root)
    {
        why = L"no table loaded";
        return 0;
    }
    return root;
}

bool OpenTable(const wchar_t* path, FrozenTable& table, std::wstring& why)
{
    table = FrozenTable{};
    UObject* object = FindObjectByPath(path);
    if (!object)
    {
        why = L"not loaded";
        return false;
    }
    const uintptr_t root = DataObjectRoot(object, why);
    if (!root) { return false; }
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

RawName ExistingName(const std::wstring& text) { return RawNameOf(FName(text.c_str(), FNAME_Find)); }

const ModState::TableArray& OriginalArray(uintptr_t at)
{
    for (const auto& entry : State.AbilityOriginals)
    {
        if (entry.At == at) { return entry; }
    }
    ModState::TableArray entry;
    entry.At = at;
    SafeCopy(entry.Original.data(), reinterpret_cast<const void*>(at), entry.Original.size());
    State.AbilityOriginals.push_back(entry);
    return State.AbilityOriginals.back();
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

// ---------------------------------------------------------------------------------------
// 3.3.1: the game copies a player's lists out of its BattlePlayerParameter row through small getters of its own, one per
// entry (SkelCompat::Frozen::IsNameEntryGetter), listed in tables of function pointers in its read-only data. The rows
// themselves can sit in memory the game maps read-only, so the mod points those table slots at getters of its own: for a
// row it switched they hand out the pack's list, for any other row (other tables share these getters) they call the game's.
// ---------------------------------------------------------------------------------------
namespace ListGetters
{
using Getter = uint64_t* (*)(void* handle, uint64_t* out);
constexpr int Commands = static_cast<int>(SkelCompat::MaxCommandAbilities);
constexpr int Limits = static_cast<int>(SkelCompat::MaxLimitAbilities);
constexpr int Count = Commands + Limits;

struct Entry
{
    std::atomic<Getter> Original{nullptr};
    int32_t Slots = 0;          // table slots pointing at the mod's getter for it
};
Entry Entries[Count];

struct Override
{
    std::atomic<uintptr_t> Row{0};                        // the row's address in the table
    std::atomic<const std::vector<uint64_t>*> Lists[2]{}; // commands, limits; null: the game's own
};
Override Overrides[8];
std::atomic<uint64_t> None{0};
bool Tried = false;
bool CommandsHooked = false;
bool LimitsHooked = false;
std::wstring Status = L"not looked for yet";

uint64_t* Answer(int slot, void* handle, uint64_t* out)
{
    const bool limit = slot >= Commands;
    const size_t index = static_cast<size_t>(limit ? slot - Commands : slot);
    uintptr_t row = 0;
    if (handle) { std::memcpy(&row, static_cast<const uint8_t*>(handle) + 8, sizeof(row)); }
    if (row)
    {
        for (const Override& entry : Overrides)
        {
            if (entry.Row.load(std::memory_order_acquire) != row) { continue; }
            const std::vector<uint64_t>* list = entry.Lists[limit ? 1 : 0].load(std::memory_order_acquire);
            if (!list) { break; }
            *out = index < list->size() ? (*list)[index] : None.load(std::memory_order_relaxed);
            return out;
        }
    }
    return Entries[slot].Original.load(std::memory_order_acquire)(handle, out);
}

template <int Slot>
uint64_t* Thunk(void* handle, uint64_t* out) { return Answer(Slot, handle, out); }

const Getter Thunks[Count] = {&Thunk<0>, &Thunk<1>, &Thunk<2>, &Thunk<3>, &Thunk<4>, &Thunk<5>, &Thunk<6>, &Thunk<7>};
static_assert(Count == 8, "one thunk per getter");

// Finds the getters of the entries of the command array (at commandOffset in a row) and the limit array (limitOffset)
// and points every read-only table slot that lists them at the mod's.
void Install(int32_t commandOffset, int32_t limitOffset)
{
    Tried = true;
    const auto* base = reinterpret_cast<const uint8_t*>(GetModuleHandleW(nullptr));
    IMAGE_DOS_HEADER dos{};
    IMAGE_NT_HEADERS64 nt{};
    if (!base || !SafeCopy(&dos, base, sizeof(dos)) || dos.e_magic != IMAGE_DOS_SIGNATURE || !SafeCopy(&nt, base + dos.e_lfanew, sizeof(nt)) ||
        nt.Signature != IMAGE_NT_SIGNATURE)
    {
        Status = L"the game's image headers are unreadable";
        return;
    }
    const uint8_t* sections = base + dos.e_lfanew + offsetof(IMAGE_NT_HEADERS64, OptionalHeader) + nt.FileHeader.SizeOfOptionalHeader;
    std::vector<std::pair<uintptr_t, uintptr_t>> code, data;
    for (WORD k = 0; k < nt.FileHeader.NumberOfSections; ++k)
    {
        IMAGE_SECTION_HEADER section{};
        if (!SafeCopy(&section, sections + k * sizeof(section), sizeof(section))) { continue; }
        const uintptr_t begin = reinterpret_cast<uintptr_t>(base) + section.VirtualAddress;
        const DWORD flags = section.Characteristics;
        if (flags & IMAGE_SCN_MEM_EXECUTE) { code.emplace_back(begin, begin + section.Misc.VirtualSize); }
        else if ((flags & IMAGE_SCN_MEM_READ) && (flags & IMAGE_SCN_CNT_INITIALIZED_DATA) && !(flags & IMAGE_SCN_MEM_WRITE) && !(flags & IMAGE_SCN_MEM_DISCARDABLE))
        {
            // read-only data, as far as the file holds it
            data.emplace_back(begin, begin + std::min<DWORD>(section.Misc.VirtualSize, section.SizeOfRawData));
        }
    }
    const auto codeEnd = [&](uintptr_t at) -> uintptr_t {
        for (const auto& [begin, end] : code)
        {
            if (at >= begin && at < end) { return end; }
        }
        return 0;
    };
    struct Found
    {
        uintptr_t Slot;
        int Getter;
    };
    std::vector<Found> found;
    uintptr_t functions[Count]{};
    size_t noneDisp[Count]{};
    for (const auto& [begin, end] : data)
    {
        for (uintptr_t at = (begin + 7) & ~static_cast<uintptr_t>(7); at + 8 <= end; at += 8)
        {
            const uintptr_t value = *reinterpret_cast<const uintptr_t*>(at);
            const uintptr_t limit = codeEnd(value);
            if (!limit || limit - value < 64) { continue; }
            const auto* bytes = reinterpret_cast<const uint8_t*>(value);
            if (bytes[0] != 0x48 || bytes[1] != 0x8B || bytes[2] != 0x49 || bytes[3] != 0x08) { continue; }
            const size_t size = static_cast<size_t>(std::min<uintptr_t>(limit - value, 96));
            for (int g = 0; g < Count; ++g)
            {
                const bool isLimit = g >= Commands;
                size_t none = 0;
                if (!SkelCompat::Frozen::IsNameEntryGetter(bytes, size, isLimit ? limitOffset : commandOffset, isLimit ? g - Commands : g, &none)) { continue; }
                if (!functions[g])
                {
                    functions[g] = value;
                    noneDisp[g] = none;
                }
                found.push_back(Found{at, g});
                break;
            }
        }
    }
    const auto all = [&](int from, int to) {
        for (int g = from; g < to; ++g)
        {
            if (!functions[g]) { return false; }
        }
        return true;
    };
    const bool commands = all(0, Commands), limits = all(Commands, Count);
    if (!commands)
    {
        Status = L"the game's command getters were not found";
        return;
    }
    // The None the game hands out past a list's end.
    int32_t rel = 0;
    uint64_t none = 0;
    if (SafeCopy(&rel, reinterpret_cast<const void*>(functions[0] + noneDisp[0]), sizeof(rel)))
    {
        SafeCopy(&none, reinterpret_cast<const void*>(functions[0] + noneDisp[0] + 4 + static_cast<intptr_t>(rel)), sizeof(none));
    }
    None.store(none, std::memory_order_relaxed);
    for (int g = 0; g < Count; ++g) { Entries[g].Original.store(reinterpret_cast<Getter>(functions[g]), std::memory_order_release); }
    // Every slot of a getter's shape goes to the mod's getter, which calls the first function found of that shape (any
    // other one does the same).
    int32_t patchedCommands = 0, patchedLimits = 0;
    for (const auto& entry : found)
    {
        if (entry.Getter >= Commands && !limits) { continue; }
        void* original = nullptr;
        if (!PatchSlot(reinterpret_cast<void**>(entry.Slot), 0, reinterpret_cast<void*>(Thunks[entry.Getter]), original)) { continue; }
        ++Entries[entry.Getter].Slots;
        (entry.Getter < Commands ? patchedCommands : patchedLimits) += 1;
    }
    CommandsHooked = patchedCommands > 0;
    LimitsHooked = limits && patchedLimits > 0;
    Status = L"the game's list getters point at the mod's (" + std::to_wstring(patchedCommands) + L" command slot(s), " +
             (limits ? std::to_wstring(patchedLimits) + L" limit slot(s)" : std::wstring(L"limit getters NOT found")) + L"; None " + Hex(none) + L")";
}

// Publishes `list` (null: the game's own) as the commands or limits of the row at `row`.
bool Publish(uintptr_t row, bool limits, const std::vector<uint64_t>* list)
{
    Override* slot = nullptr;
    for (Override& entry : Overrides)
    {
        if (entry.Row.load(std::memory_order_acquire) == row)
        {
            slot = &entry;
            break;
        }
    }
    for (Override& entry : Overrides)
    {
        if (!slot && entry.Row.load(std::memory_order_acquire) == 0) { slot = &entry; }
    }
    if (!slot) { return false; }
    slot->Lists[limits ? 1 : 0].store(list, std::memory_order_release);
    slot->Row.store(row, std::memory_order_release);
    return true;
}
} // namespace ListGetters

// ---------------------------------------------------------------------------------------
// 3.4: weapon abilities per pack. The game lists a character's weapon abilities (in the status recalculation, which
// fills the battle menu, and for the menus) by looking up each of its weapons' Equipment rows and reading the row's
// BurstAbilityID (SkelCompat::Frozen::IsWeaponRowCall). The mod points those calls at a lookup of its own: for a weapon
// whose ability the playing pack replaces ("weapon_abilities") it hands out a stand-in row that holds the replacement
// (the callers read nothing else from the row), for every other weapon the game's own row. Whether a weapon's ability
// shows (learned, or the weapon equipped) is the game's own check of the weapon, so that still decides.
// ---------------------------------------------------------------------------------------
constexpr wchar_t EquipmentTablePath[] = L"/Game/DataObject/Resident/Equipment.Equipment";

namespace WeaponAbilities
{
using Lookup = void* (*)(void* table, uint64_t key, void* out, void* found);

struct Entry
{
    uint64_t From = 0;              // the ability the weapon gives (FName)
    uint64_t To = 0;                // the ability it gives instead
    const uint8_t* Row = nullptr;   // stand-in row: To at Field
    std::wstring FromText, ToText;
};

std::atomic<Lookup> Original{nullptr};
int32_t Field = -1;
std::atomic<const std::vector<Entry>*> Map{nullptr};
std::vector<std::unique_ptr<std::vector<Entry>>> Maps;         // every map published (a lookup may still be reading one)
std::vector<std::unique_ptr<uint8_t[]>> StandIns;               // stand-in rows (kept)
std::unordered_map<uint64_t, const uint8_t*> StandInFor;        // replacement -> its stand-in row
std::unordered_map<std::wstring, std::vector<Entry>> Current;   // per player row (folded): its playing pack's replacements
bool Tried = false;
bool Hooked = false;
std::atomic<int32_t> Logged{0};
std::wstring Status = L"not looked for yet";

void* Thunk(void* table, uint64_t key, void* out, void* found)
{
    void* row = Original.load(std::memory_order_acquire)(table, key, out, found);
    const std::vector<Entry>* map = Map.load(std::memory_order_acquire);
    if (!row || !map || map->empty()) { return row; }
    uint64_t ability = 0;
    std::memcpy(&ability, static_cast<const uint8_t*>(row) + Field, sizeof(ability));
    for (const Entry& entry : *map)
    {
        if (entry.From != ability) { continue; }
        if (Logged.fetch_add(1, std::memory_order_relaxed) < 16) { Log.Line(L"Weapon abilities: a weapon giving " + entry.FromText + L" gives " + entry.ToText); }
        return const_cast<uint8_t*>(entry.Row);
    }
    return row;
}

// A jump to `target` within a rel32 call of `around` (`near` is a macro of the Windows headers).
uint8_t* JumpNear(uintptr_t around, const void* target)
{
    SYSTEM_INFO info{};
    GetSystemInfo(&info);
    const uintptr_t step = info.dwAllocationGranularity ? info.dwAllocationGranularity : 0x10000;
    constexpr uintptr_t reach = 0x60000000; // the image is far smaller than what a rel32 reaches past this
    const uintptr_t low = around > reach + step ? around - reach : step;
    const uintptr_t high = around + reach;
    uint8_t* stub = nullptr;
    for (uintptr_t at = low & ~(step - 1); !stub && at < high;)
    {
        MEMORY_BASIC_INFORMATION region{};
        if (!VirtualQuery(reinterpret_cast<void*>(at), &region, sizeof(region)))
        {
            at += step;
            continue;
        }
        const uintptr_t begin = reinterpret_cast<uintptr_t>(region.BaseAddress);
        const uintptr_t end = begin + region.RegionSize;
        if (region.State == MEM_FREE)
        {
            const uintptr_t start = (std::max(begin, at) + step - 1) & ~(step - 1);
            if (start + step <= end && start < high)
            {
                stub = static_cast<uint8_t*>(VirtualAlloc(reinterpret_cast<void*>(start), 4096, MEM_RESERVE | MEM_COMMIT, PAGE_EXECUTE_READWRITE));
            }
        }
        at = std::max(end, at + step);
    }
    if (!stub) { return nullptr; }
    // mov rax, target; jmp rax
    const uintptr_t value = reinterpret_cast<uintptr_t>(target);
    stub[0] = 0x48;
    stub[1] = 0xB8;
    std::memcpy(stub + 2, &value, sizeof(value));
    stub[10] = 0xFF;
    stub[11] = 0xE0;
    DWORD old = 0;
    VirtualProtect(stub, 4096, PAGE_EXECUTE_READ, &old);
    FlushInstructionCache(GetCurrentProcess(), stub, 12);
    return stub;
}

// Points the call (E8 rel32) at `call` to `target`.
bool PatchCall(uint8_t* call, const uint8_t* target)
{
    const intptr_t rel = reinterpret_cast<intptr_t>(target) - reinterpret_cast<intptr_t>(call + 5);
    if (call[0] != 0xE8 || rel < INT32_MIN || rel > INT32_MAX) { return false; }
    DWORD old = 0;
    if (!VirtualProtect(call, 5, PAGE_EXECUTE_READWRITE, &old)) { return false; }
    const int32_t value = static_cast<int32_t>(rel);
    std::memcpy(call + 1, &value, sizeof(value));
    DWORD unused = 0;
    VirtualProtect(call, 5, old, &unused);
    FlushInstructionCache(GetCurrentProcess(), call, 5);
    return true;
}

// Finds the game's lookups of weapons' rows that read BurstAbilityID and points them at the mod's (game thread).
void Install()
{
    Tried = true;
    FrozenTable equipment;
    std::wstring why;
    if (!OpenTable(EquipmentTablePath, equipment, why))
    {
        Status = L"the Equipment table is NOT usable (" + why + L")";
        return;
    }
    const SkelCompat::Frozen::Field* burst = SkelCompat::Frozen::Find(equipment.Fields, L"BurstAbilityID");
    UObject* table = FindObjectByPath(EquipmentTablePath);
    if (!burst || burst->Array || burst->Type != 11 || !table)
    {
        Status = L"the Equipment table has no BurstAbilityID";
        return;
    }
    const int32_t tableIndex = table->GetInternalIndex();
    const auto* base = reinterpret_cast<const uint8_t*>(GetModuleHandleW(nullptr));
    IMAGE_DOS_HEADER dos{};
    IMAGE_NT_HEADERS64 nt{};
    if (!base || !SafeCopy(&dos, base, sizeof(dos)) || dos.e_magic != IMAGE_DOS_SIGNATURE || !SafeCopy(&nt, base + dos.e_lfanew, sizeof(nt)) ||
        nt.Signature != IMAGE_NT_SIGNATURE)
    {
        Status = L"the game's image headers are unreadable";
        return;
    }
    const uint8_t* sections = base + dos.e_lfanew + offsetof(IMAGE_NT_HEADERS64, OptionalHeader) + nt.FileHeader.SizeOfOptionalHeader;
    struct Site
    {
        uint8_t* Call;
        uintptr_t Table;
        uintptr_t Lookup;
    };
    std::vector<Site> sites;
    int32_t shapes = 0, fieldMatches = 0;
    static constexpr uint8_t middle[] = {0x4C, 0x8B, 0xE8, 0x48, 0x85, 0xC0, 0x0F, 0x84};
    for (WORD k = 0; k < nt.FileHeader.NumberOfSections; ++k)
    {
        IMAGE_SECTION_HEADER section{};
        if (!SafeCopy(&section, sections + k * sizeof(section), sizeof(section)) || !(section.Characteristics & IMAGE_SCN_MEM_EXECUTE)) { continue; }
        const uint8_t* begin = base + section.VirtualAddress;
        const size_t size = std::min<DWORD>(section.Misc.VirtualSize, section.SizeOfRawData);
        for (size_t at = 12; at + SkelCompat::Frozen::WeaponRowCallSize <= size + 12;)
        {
            const void* hit = std::memchr(begin + at, 0x4C, size - at);
            if (!hit) { break; }
            at = static_cast<size_t>(static_cast<const uint8_t*>(hit) - begin);
            const uint8_t* match = begin + at - 12;
            ++at;
            if (at - 1 + sizeof(middle) > size || std::memcmp(begin + at - 1, middle, sizeof(middle)) != 0) { continue; }
            if (at - 1 - 12 + SkelCompat::Frozen::WeaponRowCallSize > size) { continue; }
            SkelCompat::Frozen::WeaponRowCall call{};
            if (!SkelCompat::Frozen::IsWeaponRowCall(match, SkelCompat::Frozen::WeaponRowCallSize, &call)) { continue; }
            ++shapes;
            if (call.Field != burst->Offset) { continue; }
            ++fieldMatches;
            const uintptr_t global = reinterpret_cast<uintptr_t>(match) + static_cast<uintptr_t>(call.Table);
            // The table global lists the data objects it looks rows up in: 3 lists (TArray each, the game's lookup walks
            // them in turn) of 16-byte entries that start with a weak pointer {index, serial}. One is the Equipment table's.
            bool equipmentTable = false;
            for (uintptr_t list = 0; list < 3 && !equipmentTable; ++list)
            {
                RawArray objects{};
                if (!SafeCopy(&objects, reinterpret_cast<const void*>(global + list * sizeof(RawArray)), sizeof(objects)) || !objects.Data || objects.Num <= 0 ||
                    objects.Num > 256)
                {
                    continue;
                }
                std::vector<int32_t> entries(static_cast<size_t>(objects.Num) * 4);
                if (!SafeCopy(entries.data(), objects.Data, entries.size() * sizeof(int32_t))) { continue; }
                for (int32_t w = 0; w < objects.Num; ++w) { equipmentTable = equipmentTable || entries[static_cast<size_t>(w) * 4] == tableIndex; }
            }
            if (!equipmentTable) { continue; }
            sites.push_back(Site{const_cast<uint8_t*>(match) + call.Call, global, reinterpret_cast<uintptr_t>(match) + static_cast<uintptr_t>(call.Lookup)});
        }
    }
    if (sites.empty())
    {
        Status = L"the game's weapon ability lookups were NOT found (" + std::to_wstring(shapes) + L" lookups of that shape, " + std::to_wstring(fieldMatches) +
                 L" reading +" + Hex(static_cast<uintptr_t>(burst->Offset)) + L", none in the Equipment table (object " + std::to_wstring(tableIndex) + L"))";
        return;
    }
    for (const Site& site : sites)
    {
        if (site.Lookup != sites.front().Lookup)
        {
            Status = L"the game's weapon ability lookups call different functions; left alone";
            return;
        }
    }
    uint8_t* stub = JumpNear(reinterpret_cast<uintptr_t>(sites.front().Call), reinterpret_cast<const void*>(&Thunk));
    if (!stub)
    {
        Status = L"no memory near the game's code for the mod's lookup";
        return;
    }
    Field = burst->Offset;
    Original.store(reinterpret_cast<Lookup>(sites.front().Lookup), std::memory_order_release);
    int32_t patched = 0;
    std::wstring where;
    for (const Site& site : sites)
    {
        if (!PatchCall(site.Call, stub)) { continue; }
        ++patched;
        where += (where.empty() ? L"" : L", ") + Hex(reinterpret_cast<uintptr_t>(site.Call) - reinterpret_cast<uintptr_t>(base));
    }
    Hooked = patched > 0;
    Status = Hooked ? L"the game's weapon ability lookups point at the mod's (" + std::to_wstring(patched) + L" call(s) at " + where + L"; BurstAbilityID +" +
                          Hex(static_cast<uintptr_t>(Field)) + L")"
                    : L"the game's weapon ability lookups could NOT be changed";
}

const uint8_t* StandIn(uint64_t ability)
{
    if (const auto it = StandInFor.find(ability); it != StandInFor.end()) { return it->second; }
    auto row = std::make_unique<uint8_t[]>(static_cast<size_t>(Field) + 16);
    std::memset(row.get(), 0, static_cast<size_t>(Field) + 16);
    std::memcpy(row.get() + Field, &ability, sizeof(ability));
    const uint8_t* at = row.get();
    StandIns.push_back(std::move(row));
    StandInFor[ability] = at;
    return at;
}

// Publishes `entries` as the replacements of a player row (game thread).
void Publish(const std::wstring& player, std::vector<Entry> entries)
{
    Current[SkelCompat::FoldedKey(player)] = std::move(entries);
    auto map = std::make_unique<std::vector<Entry>>();
    for (const auto& [key, list] : Current) { map->insert(map->end(), list.begin(), list.end()); }
    Map.store(map.get(), std::memory_order_release);
    Maps.push_back(std::move(map));
}
} // namespace WeaponAbilities

// The weapon abilities of a row's pack (3.4 "weapon_abilities") for the log line; `changed` tells whether they changed.
std::wstring ApplyWeaponAbilities(const SkelCompat::AnimSetRow& row, const std::wstring& pack, const FrozenTable* abilities, bool& changed)
{
    changed = false;
    const bool wanted = std::any_of(State.Config.AnimSets.begin(), State.Config.AnimSets.end(), [](const SkelCompat::AnimSetRow& r) {
        return std::any_of(r.Abilities.begin(), r.Abilities.end(), [](const SkelCompat::PackAbilities& a) { return a.HasWeapons; });
    });
    if (!wanted) { return {}; }
    if (!WeaponAbilities::Tried)
    {
        WeaponAbilities::Install();
        Log.Line(L"Abilities: " + WeaponAbilities::Status);
    }
    std::wstring from;
    const auto* list = row.WeaponsFor(pack, &from);
    if (!WeaponAbilities::Hooked) { return list && !list->empty() ? L"; weapon abilities NOT switched (" + WeaponAbilities::Status + L")" : std::wstring{}; }
    std::vector<WeaponAbilities::Entry> entries;
    std::wstring shown, skipped;
    if (list)
    {
        for (const auto& [weapon, ability] : *list)
        {
            const RawName given = ExistingName(weapon), replacement = ExistingName(ability);
            if ((given.Comparison == 0 && given.Number == 0) || (replacement.Comparison == 0 && replacement.Number == 0) ||
                (abilities && (!TableRow(*abilities, given) || !TableRow(*abilities, replacement))))
            {
                skipped += (skipped.empty() ? L"" : L", ") + weapon + L" -> " + ability;
                continue;
            }
            if (SameName(given, replacement)) { continue; }
            WeaponAbilities::Entry entry;
            entry.From = KeyOf(given);
            entry.To = KeyOf(replacement);
            entry.Row = WeaponAbilities::StandIn(entry.To);
            entry.FromText = weapon;
            entry.ToText = ability;
            entries.push_back(std::move(entry));
            shown += (shown.empty() ? L"" : L", ") + weapon + L" -> " + ability;
        }
    }
    const auto key = SkelCompat::FoldedKey(row.Player);
    const auto before = WeaponAbilities::Current.find(key);
    const auto same = [&](const std::vector<WeaponAbilities::Entry>& a) {
        return a.size() == entries.size() && std::equal(a.begin(), a.end(), entries.begin(), [](const auto& x, const auto& y) { return x.From == y.From && x.To == y.To; });
    };
    changed = before == WeaponAbilities::Current.end() ? !entries.empty() : !same(before->second);
    WeaponAbilities::Publish(row.Player, std::move(entries));
    return L"; weapon abilities " + (shown.empty() ? std::wstring(L"the weapons' own") : shown) +
           (list && !SkelCompat::NameEquals(from, pack) && !shown.empty() ? L" (" + from + L"'s)" : std::wstring{}) +
           (skipped.empty() ? std::wstring{} : L" [left out, not BattleAbility rows: " + skipped + L"]");
}

bool RestoreTableArray(const ModState::TableArray& original)
{
    int64_t pointer = 0;
    int32_t num = 0, max = 0;
    std::memcpy(&pointer, original.Original.data(), 8);
    std::memcpy(&num, original.Original.data() + 8, 4);
    std::memcpy(&max, original.Original.data() + 12, 4);
    return WriteTableArray(original.At, pointer, num, max);
}

// A list of names the mod keeps for the session (one per place and contents).
const std::vector<uint64_t>* NameListFor(uintptr_t place, const std::vector<RawName>& names)
{
    std::wstring key = Hex(place) + L":";
    for (const auto& name : names) { key += Hex(KeyOf(name)) + L","; }
    auto& list = State.AbilityLists[key];
    if (!list)
    {
        list = std::make_unique<std::vector<uint64_t>>();
        for (const auto& name : names) { list->push_back(KeyOf(name)); }
    }
    return list.get();
}

// Points the table array at `at` to a list of names the mod keeps for the session.
bool WriteNameList(uintptr_t at, const std::vector<RawName>& names)
{
    const std::vector<uint64_t>* list = NameListFor(at, names);
    const int32_t count = static_cast<int32_t>(list->size());
    const int64_t pointer = count ? SkelCompat::Frozen::Encode(at, reinterpret_cast<uintptr_t>(list->data())) : 0;
    return WriteTableArray(at, pointer, count, count);
}

// Applies a row's lists for `pack` to its BattlePlayerParameter row. Returns a line for the log; `wrote` tells whether
// the row's arrays were written.
std::wstring ApplyAbilities(const SkelCompat::AnimSetRow& row, const std::wstring& pack, bool& wrote)
{
    wrote = false;
    FrozenTable players;
    std::wstring why;
    if (!OpenTable(PlayerTablePath, players, why)) { return L"BattlePlayerParameter NOT usable: " + why; }
    FrozenTable abilities;
    std::wstring abilityWhy;
    const bool check = OpenTable(AbilityTablePath, abilities, abilityWhy);
    const uintptr_t at = TableRow(players, ExistingName(row.Player));
    if (!at) { return L"BattlePlayerParameter has no row " + row.Player; }
    const SkelCompat::Frozen::Field* commandField = SkelCompat::Frozen::Find(players.Fields, L"CommandAbilityID_Array");
    const SkelCompat::Frozen::Field* limitField = SkelCompat::Frozen::Find(players.Fields, L"LimitAbilityID_Array");
    if (!ListGetters::Tried && commandField && limitField)
    {
        ListGetters::Install(commandField->Offset, limitField->Offset);
        Log.Line(L"Abilities: " + ListGetters::Status);
    }
    std::wstring line = row.Player + L", pack " + pack + L":";
    for (const bool limits : {false, true})
    {
        const wchar_t* fieldName = limits ? L"LimitAbilityID_Array" : L"CommandAbilityID_Array";
        line += limits ? L"; limits " : L" commands ";
        const SkelCompat::Frozen::Field* field = limits ? limitField : commandField;
        if (!field || !field->Array || field->Type != 11)
        {
            line += L"(the table has no " + std::wstring(fieldName) + L")";
            continue;
        }
        const bool hooked = limits ? ListGetters::LimitsHooked : ListGetters::CommandsHooked;
        const uintptr_t arrayAt = at + static_cast<uintptr_t>(field->Offset);
        std::wstring from;
        const std::vector<std::wstring>* list = row.ListFor(pack, limits, &from);
        if (!list)
        {
            bool restored = false;
            if (hooked) { restored = ListGetters::Publish(at, limits, nullptr); }
            else { restored = RestoreTableArray(OriginalArray(arrayAt)); }
            wrote = wrote || restored;
            line += restored ? L"the table's own" : L"the table's own (NOT written back" + (TableWriteProblem.empty() ? std::wstring{} : L": " + TableWriteProblem) + L")";
            continue;
        }
        std::vector<RawName> names;
        std::wstring shown, skipped, extra;
        const size_t most = limits ? SkelCompat::MaxLimitAbilities : SkelCompat::MaxCommandAbilities;
        for (const auto& ability : *list)
        {
            const RawName name = ExistingName(ability);
            if ((name.Comparison == 0 && name.Number == 0) || (check && !TableRow(abilities, name)))
            {
                skipped += (skipped.empty() ? L"" : L", ") + ability;
                continue;
            }
            if (names.size() >= most)
            {
                extra += (extra.empty() ? L"" : L", ") + ability;
                continue;
            }
            names.push_back(name);
            shown += (shown.empty() ? L"" : L", ") + ability;
        }
        bool written = false;
        if (hooked)
        {
            written = ListGetters::Publish(at, limits, NameListFor(at + (limits ? 1 : 0), names));
            if (!written) { TableWriteProblem = L"no free slot for another switched row"; }
        }
        else
        {
            OriginalArray(arrayAt);
            written = WriteNameList(arrayAt, names);
        }
        wrote = wrote || written;
        line += (shown.empty() ? std::wstring(L"(none)") : shown) + (SkelCompat::NameEquals(from, pack) ? std::wstring{} : L" (" + from + L"'s)") +
                (skipped.empty() ? std::wstring{} : L" [left out, not BattleAbility rows: " + skipped + L"]") +
                (extra.empty() ? std::wstring{} : L" [left out, the game lists " + std::to_wstring(most) + (limits ? L" limits: " : L" commands: ") + extra + L"]") +
                (written ? L"" : L" (NOT written: " + (TableWriteProblem.empty() ? std::wstring(L"memory") : TableWriteProblem) + L")");
    }
    bool weaponsChanged = false;
    line += ApplyWeaponAbilities(row, pack, check ? &abilities : nullptr, weaponsChanged);
    wrote = wrote || weaponsChanged; // the game rebuilds the weapon list with the others
    if (!check) { line += L" (abilities not checked: BattleAbility " + abilityWhy + L")"; }
    return line;
}

// Calls an EndMenuBPAPI function that takes a player type (and optionally an int) and returns an int (or nothing).
// false when its parameters are not those.
bool CallMenuInt(UFunction* function, int type, const wchar_t* valueName, int32_t value, int32_t* result)
{
    if (!function || !Alive(State.MenuApi)) { return false; }
    int32_t typeSize = 0, valueSize = 0, resultSize = 0;
    const int32_t typeAt = ParamOffset(function, L"Type", typeSize);
    const int32_t valueAt = valueName ? ParamOffset(function, valueName, valueSize) : -1;
    const int32_t resultAt = result ? ParamOffset(function, L"ReturnValue", resultSize) : -1;
    if (typeAt < 0 || typeSize != 1 || (valueName && (valueAt < 0 || valueSize != 4)) || (result && (resultAt < 0 || resultSize != 4))) { return false; }
    ParamBlock block(function);
    *block.At(typeAt) = static_cast<uint8_t>(type);
    if (valueName) { std::memcpy(block.At(valueAt), &value, sizeof(value)); }
    State.MenuApi->ProcessEvent(function, block.Bytes.data());
    if (result) { std::memcpy(result, block.At(resultAt), sizeof(*result)); }
    return true;
}

// Has the game recalculate a party member's status, which rebuilds its ability lists from its BattlePlayerParameter
// row (see above). Returns a note for the log line.
// 3.4: the game's BPSetPlayerLevel sets EXP, not the level (it is the same native as BPSetPlayerExperience: EXP := the
// value, the level follows from it), so 3.3 / 3.3.1, which handed it the level, set a member's EXP to its level (level 70
// -> 70 EXP -> level 1). The mod now hands BPSetPlayerExperience the EXP the member has: nothing changes but the
// recalculation. It checks the level and EXP afterwards and stops recalculating for the session if either changed.
std::wstring RefreshAbilityLists(const SkelCompat::AnimSetRow& row)
{
    if (!row.RefreshAbilities) { return L"; status not recalculated (refresh_abilities is off)"; }
    if (State.RefreshProblem) { return L"; status not recalculated (switched off: " + State.RefreshText + L")"; }
    const int type = SkelCompat::PlayerTypeOf(row.Player);
    if (type < 0) { return L"; status not recalculated (" + row.Player + L" is not a party member's row)"; }
    UFunction* getLevel = State.GetPlayerLevel;
    UFunction* getExp = State.GetPlayerExperience;
    UFunction* setExp = State.SetPlayerExperience;
    if (!getLevel || !getExp || !setExp || !Alive(State.MenuApi)) { return L"; status not recalculated (EndMenuBPAPI BPGetPlayerExperience / BPSetPlayerExperience not found)"; }
    int32_t level = 0, exp = 0;
    if (!CallMenuInt(getLevel, type, nullptr, 0, &level) || !CallMenuInt(getExp, type, nullptr, 0, &exp))
    {
        return L"; status not recalculated (EndMenuBPAPI level / EXP functions take other parameters)";
    }
    // No status (the game hands out level 1 / EXP 0 then): nothing to recalculate, and the game's setter would read a null.
    if (level < 1 || level > 999 || exp <= 0) { return L"; status not recalculated (no status: level " + std::to_wstring(level) + L", EXP " + std::to_wstring(exp) + L")"; }
    CallMenuInt(setExp, type, L"Exp", exp, nullptr);
    int32_t levelAfter = 0, expAfter = 0;
    CallMenuInt(getLevel, type, nullptr, 0, &levelAfter);
    CallMenuInt(getExp, type, nullptr, 0, &expAfter);
    if (levelAfter != level || expAfter != exp)
    {
        State.RefreshProblem = true;
        State.RefreshText = L"level " + std::to_wstring(level) + L" -> " + std::to_wstring(levelAfter) + L", EXP " + std::to_wstring(exp) + L" -> " +
                            std::to_wstring(expAfter) + L" after a recalculation";
        Log.Line(L"Abilities: WARNING: " + State.RefreshText + L"; status recalculation switched off for this session");
        return L"; status recalculated, but " + State.RefreshText + L" (WARNING: switched off for this session)";
    }
    return L"; status recalculated (level " + std::to_wstring(level) + L", EXP " + std::to_wstring(exp) + L" kept) so the game rebuilds the lists";
}

void NoteAbilityLine(const std::wstring& line)
{
    State.AbilityLines.push_back(line);
    if (State.AbilityLines.size() > 40) { State.AbilityLines.erase(State.AbilityLines.begin()); }
}

// The CharaSpec row a character plays (EndBattleAPI GetCharaSpecName, without "CharaSpec_"); empty when unknown.
std::wstring CharaSpecRowOf(UObject* character)
{
    UFunction* get = State.GetCharaSpecName;
    if (!get || !State.BattleApi) { return {}; }
    int32_t objectAt = -1, resultAt = -1;
    std::wstring resultType;
    for (FProperty* property : get->ForEachPropertyInChain())
    {
        if (!property) { continue; }
        const std::wstring type = TypeOf(property);
        const int32_t offset = property->GetOffset_Internal();
        if (offset < 0 || offset + property->GetElementSize() > get->GetParmsSize()) { continue; }
        if (property->GetName() == L"ReturnValue")
        {
            resultAt = offset;
            resultType = type;
        }
        else if (objectAt < 0 && type == L"ObjectProperty") { objectAt = offset; }
    }
    if (objectAt < 0 || resultAt < 0 || (resultType != L"NameProperty" && resultType != L"StrProperty")) { return {}; }
    ParamBlock block(get);
    std::memcpy(block.At(objectAt), &character, sizeof(character));
    State.BattleApi->ProcessEvent(get, block.Bytes.data());
    std::wstring name;
    if (resultType == L"NameProperty")
    {
        RawName raw{};
        std::memcpy(&raw, block.At(resultAt), sizeof(raw));
        name = NameText(KeyOf(raw));
    }
    else
    {
        name = ReadFString(block.At(resultAt));
        FreeStringAt(block.At(resultAt));
    }
    if (SkelCompat::StartsWithFolded(name, L"CharaSpec_")) { name.erase(0, 10); }
    return name == L"None" ? std::wstring{} : name;
}

constexpr wchar_t CharaSpecTablePath[] = L"/Game/DataObject/Resident/CharaSpec.CharaSpec";

// Whether a CharaSpec row lists `set` in its AnimationSetList (the game takes only those sets from the character's pack,
// so SetPrimaryAnimPack can only switch to them): 1 yes, 0 no, -1 unknown.
int CharaSpecListsSet(const std::wstring& spec, const std::wstring& set)
{
    FrozenTable table;
    std::wstring why;
    if (!OpenTable(CharaSpecTablePath, table, why)) { return -1; }
    const uintptr_t at = TableRow(table, ExistingName(spec));
    const SkelCompat::Frozen::Field* field = SkelCompat::Frozen::Find(table.Fields, L"AnimationSetList_Array");
    if (!at || !field || !field->Array || field->Type != 11) { return -1; }
    uintptr_t data = 0;
    int32_t num = 0;
    if (!ReadFrozenArray(at + static_cast<uintptr_t>(field->Offset), data, num) || num > 64) { return -1; }
    std::vector<RawName> names(static_cast<size_t>(num));
    if (num > 0 && !SafeCopy(names.data(), reinterpret_cast<const void*>(data), names.size() * sizeof(RawName))) { return -1; }
    for (const auto& name : names)
    {
        if ((name.Comparison || name.Number) && SkelCompat::NameEquals(NameText(KeyOf(name)), set)) { return 1; }
    }
    return 0;
}

// ---------------------------------------------------------------------------------------
// 3.5: every set of a character's pack can be switched to. The game takes a character's sets from its pack into a map
// of set names only for some slots of its CharaSpec row's AnimationSetList (a set in another slot is in the pack but
// never in that map), so EndBattleAPI SetPrimaryAnimPack to it did nothing. The game looks a character's sets up by
// name in one function (its pack switch, its re-applies and its animation lookups call it); the mod points those calls
// at its own: the game's answer first, else the set of that name in the character's pack, which the mod found when the
// pack was switched to it (game thread) and keeps resident.
// ---------------------------------------------------------------------------------------
namespace PackSets
{
// The game's lookup takes the set's name by value (FName, 8 bytes: comparison index, number).
using Lookup = UObject* (*)(void* container, uint64_t name);

struct Entry
{
    void* Container = nullptr;  // the character's set container (character + ContainerOffset)
    uint64_t Name = 0;          // the set's name (raw FName)
    UObject* Set = nullptr;     // the pack's set of that name (rooted)
};

constexpr size_t MaxEntries = 64;
std::atomic<Lookup> Original{nullptr};
int32_t ContainerOffset = -1;   // character -> the container the game's lookup takes
int32_t MapOffset = -1;         // container -> its TMap<FName, TWeakObjectPtr<UEndAnimSet>>
SRWLOCK Lock = SRWLOCK_INIT;
Entry Entries[MaxEntries]{};
size_t Count = 0;
bool Tried = false;
bool Hooked = false;
std::wstring Status = L"not looked for yet";
std::vector<std::wstring> Said; // (row/pack) already logged
std::atomic<uint64_t> Calls{0};  // calls of the game's lookup (through the mod's)
std::atomic<uint64_t> Served{0}; // of them answered with one of the mod's sets

// The game's lookup, then the mod's sets (any thread: the game's animation lookups run on worker threads too).
UObject* Thunk(void* container, uint64_t key)
{
    Calls.fetch_add(1, std::memory_order_relaxed);
    const Lookup original = Original.load(std::memory_order_acquire);
    UObject* found = original ? original(container, key) : nullptr;
    if (found || !key) { return found; }
    AcquireSRWLockShared(&Lock);
    for (size_t i = 0; i < Count; ++i)
    {
        if (Entries[i].Container == container && Entries[i].Name == key)
        {
            found = Entries[i].Set;
            break;
        }
    }
    ReleaseSRWLockShared(&Lock);
    if (found) { Served.fetch_add(1, std::memory_order_relaxed); }
    return found;
}

std::wstring Counts()
{
    return L"the game's set lookup ran " + std::to_wstring(Calls.load(std::memory_order_relaxed)) + L" time(s), " +
           std::to_wstring(Served.load(std::memory_order_relaxed)) + L" of them answered with the mod's sets";
}

// The game's lookup function: push rbx; mov eax,0x20; call <probe>; sub rsp,rax; lea rbx,[rcx+map]; mov r8,rdx; mov rcx,rbx;
// lea rdx,[rsp+0x30]; call <FindId>; cmp dword ptr [rax],-1.
bool IsLookup(const uint8_t* at, int32_t& map)
{
    static constexpr uint8_t head[] = {0x40, 0x53, 0xB8, 0x20, 0x00, 0x00, 0x00, 0xE8};
    static constexpr uint8_t middle[] = {0x48, 0x2B, 0xE0, 0x48, 0x8D, 0x99};
    static constexpr uint8_t tail[] = {0x4C, 0x8B, 0xC2, 0x48, 0x8B, 0xCB, 0x48, 0x8D, 0x54, 0x24, 0x30, 0xE8};
    static constexpr uint8_t check[] = {0x83, 0x38, 0xFF};
    if (std::memcmp(at, head, sizeof(head)) != 0 || std::memcmp(at + 12, middle, sizeof(middle)) != 0 ||
        std::memcmp(at + 22, tail, sizeof(tail)) != 0 || std::memcmp(at + 38, check, sizeof(check)) != 0)
    {
        return false;
    }
    std::memcpy(&map, at + 18, sizeof(map));
    return map > 0 && map < 0x1000;
}

// Finds the game's lookup and its calls, and points the calls at Thunk (game thread, once).
void Install()
{
    Tried = true;
    const auto* base = reinterpret_cast<const uint8_t*>(GetModuleHandleW(nullptr));
    IMAGE_DOS_HEADER dos{};
    IMAGE_NT_HEADERS64 nt{};
    if (!base || !SafeCopy(&dos, base, sizeof(dos)) || dos.e_magic != IMAGE_DOS_SIGNATURE || !SafeCopy(&nt, base + dos.e_lfanew, sizeof(nt)) ||
        nt.Signature != IMAGE_NT_SIGNATURE)
    {
        Status = L"the game's image headers are unreadable";
        return;
    }
    const uint8_t* sections = base + dos.e_lfanew + offsetof(IMAGE_NT_HEADERS64, OptionalHeader) + nt.FileHeader.SizeOfOptionalHeader;
    struct Range
    {
        const uint8_t* Begin;
        size_t Size;
    };
    std::vector<Range> code;
    for (WORD k = 0; k < nt.FileHeader.NumberOfSections; ++k)
    {
        IMAGE_SECTION_HEADER section{};
        if (!SafeCopy(&section, sections + k * sizeof(section), sizeof(section)) || !(section.Characteristics & IMAGE_SCN_MEM_EXECUTE)) { continue; }
        code.push_back(Range{base + section.VirtualAddress, std::min<DWORD>(section.Misc.VirtualSize, section.SizeOfRawData)});
    }
    // Functions of that shape (the game has several: a lookup in a map of names at some offset of an object).
    struct Candidate
    {
        const uint8_t* At = nullptr;
        int32_t Map = -1;
        std::vector<uint8_t*> Calls;
        int32_t Container = -1; // the largest lea rcx,[reg+disp32] just before one of its calls
    };
    std::vector<Candidate> candidates;
    for (const Range& range : code)
    {
        for (size_t at = 0; at + 48 <= range.Size;)
        {
            const void* hit = std::memchr(range.Begin + at, 0x40, range.Size - 48 - at);
            if (!hit) { break; }
            at = static_cast<size_t>(static_cast<const uint8_t*>(hit) - range.Begin);
            int32_t found = -1;
            if (IsLookup(range.Begin + at, found))
            {
                Candidate candidate;
                candidate.At = range.Begin + at;
                candidate.Map = found;
                candidates.push_back(std::move(candidate));
            }
            ++at;
        }
    }
    if (candidates.empty())
    {
        Status = L"the game's set lookup was NOT found (no function of its shape)";
        return;
    }
    // their calls (E8 rel32), and the container each call is given: lea rcx,[reg+disp32] just before it
    for (const Range& range : code)
    {
        for (size_t at = 8; at + 5 <= range.Size;)
        {
            const void* hit = std::memchr(range.Begin + at, 0xE8, range.Size - 5 - at);
            if (!hit) { break; }
            at = static_cast<size_t>(static_cast<const uint8_t*>(hit) - range.Begin);
            const uint8_t* call = range.Begin + at;
            int32_t rel = 0;
            std::memcpy(&rel, call + 1, sizeof(rel));
            const uintptr_t target = reinterpret_cast<uintptr_t>(call) + 5 + static_cast<intptr_t>(rel);
            for (Candidate& candidate : candidates)
            {
                if (target != reinterpret_cast<uintptr_t>(candidate.At)) { continue; }
                candidate.Calls.push_back(const_cast<uint8_t*>(call));
                const uint8_t* lea = call - 7;
                if (lea[0] == 0x48 && lea[1] == 0x8D && (lea[2] & 0xF8) == 0x88 && (lea[2] & 0x07) != 0x04)
                {
                    int32_t disp = 0;
                    std::memcpy(&disp, lea + 3, sizeof(disp));
                    if (disp > candidate.Container) { candidate.Container = disp; }
                }
                break;
            }
            ++at;
        }
    }
    // The set lookup is the one a character's own container is passed to: +0xE38 in this build (the anim interface's
    // +0x968 at its +0x4D0), its map of sets at +0xB8.
    const Candidate* pick = nullptr;
    int32_t takers = 0;
    for (const Candidate& candidate : candidates)
    {
        if (!candidate.Calls.empty() && candidate.Container == 0xE38)
        {
            pick = &candidate;
            ++takers;
        }
    }
    if (takers != 1)
    {
        Status = L"the game's set lookup was NOT found (" + std::to_wstring(candidates.size()) + L" functions of its shape, " + std::to_wstring(takers) +
                 L" of them given a character's container +0xE38; this build of the game differs)";
        return;
    }
    const uint8_t* lookup = pick->At;
    const std::vector<uint8_t*>& calls = pick->Calls;
    const int32_t container = pick->Container;
    const int32_t map = pick->Map;
    uint8_t* stub = WeaponAbilities::JumpNear(reinterpret_cast<uintptr_t>(calls.front()), reinterpret_cast<const void*>(&Thunk));
    if (!stub)
    {
        Status = L"no memory near the game's code for the mod's set lookup";
        return;
    }
    ContainerOffset = container;
    MapOffset = map;
    Original.store(reinterpret_cast<Lookup>(const_cast<uint8_t*>(lookup)), std::memory_order_release);
    int32_t patched = 0;
    std::wstring where;
    for (uint8_t* call : calls)
    {
        if (!WeaponAbilities::PatchCall(call, stub)) { continue; }
        ++patched;
        where += (where.empty() ? L"" : L", ") + Hex(reinterpret_cast<uintptr_t>(call) - reinterpret_cast<uintptr_t>(base));
    }
    Hooked = patched > 0;
    Status = Hooked ? L"the game's set lookup points at the mod's (" + std::to_wstring(patched) + L" of " + std::to_wstring(calls.size()) + L" call(s) at " + where +
                          L"; container +" + Hex(static_cast<uintptr_t>(container)) + L", map +" + Hex(static_cast<uintptr_t>(map)) + L"; 1 of " +
                          std::to_wstring(candidates.size()) + L" functions of its shape)"
                    : L"the game's set lookup could NOT be changed";
}

// The names of the sets the game took into a character's map (for the log).
std::wstring GameSets(UObject* character)
{
    std::vector<NameObjectEntry> entries;
    std::wstring why;
    if (MapOffset < 0 || !ReadNameObjectMap(reinterpret_cast<const uint8_t*>(character) + ContainerOffset + MapOffset, entries, why))
    {
        return L"unreadable" + (why.empty() ? std::wstring{} : L": " + why);
    }
    std::wstring text;
    for (const auto& entry : entries) { text += (text.empty() ? L"" : L", ") + NameText(entry.Key); }
    return text.empty() ? L"none" : text;
}

void Remember(void* container, uint64_t name, UObject* set)
{
    AcquireSRWLockExclusive(&Lock);
    size_t at = Count;
    for (size_t i = 0; i < Count; ++i)
    {
        if (Entries[i].Container == container && Entries[i].Name == name)
        {
            at = i;
            break;
        }
    }
    if (at == Count)
    {
        if (Count == MaxEntries)
        {
            std::memmove(&Entries[0], &Entries[1], (MaxEntries - 1) * sizeof(Entry)); // the oldest goes
            at = MaxEntries - 1;
        }
        else
        {
            ++Count;
        }
    }
    Entries[at] = Entry{container, name, set};
    ReleaseSRWLockExclusive(&Lock);
}

// A map load: the characters (and their containers) are new.
void Clear()
{
    AcquireSRWLockExclusive(&Lock);
    Count = 0;
    ReleaseSRWLockExclusive(&Lock);
}

// SetPrimaryAnimPack(character, pack) is about to run (game thread): when the game's map has no set of that name, the
// set of that name in the character's pack is remembered for its container.
void Prepare(UObject* character, const std::wstring& pack)
{
    if (!Hooked || !character || pack.empty()) { return; }
    const Lookup original = Original.load(std::memory_order_acquire);
    const RawName name = ExistingName(pack);
    if (!original || (!name.Comparison && !name.Number)) { return; }
    void* container = reinterpret_cast<uint8_t*>(character) + ContainerOffset;
    UObject* had = original(container, KeyOf(name));
    const std::wstring spec = CharaSpecRowOf(character);
    if (had) // the game has it
    {
        const std::wstring key = SkelCompat::FoldedKey(spec + L"/" + pack + L"/had");
        if (std::find(Said.begin(), Said.end(), key) == Said.end())
        {
            Said.push_back(key);
            Log.Line(L"Animation sets: " + (spec.empty() ? std::wstring(L"a character") : spec) + L" was switched to " + pack +
                     L", a set the game has in its map (" + ObjectPath(had) + L"; it took: " + GameSets(character) + L"); " + Counts());
        }
        return;
    }
    UObject* set = nullptr;
    std::wstring why;
    UObject* packAsset = spec.empty() ? nullptr : FindObjectByPath(SkelCompat::CharacterPackPath(spec).c_str());
    if (!packAsset) { why = spec.empty() ? L"its CharaSpec row is unknown" : L"its pack is not loaded"; }
    else
    {
        std::vector<PackSlot> slots;
        int32_t entries = 0;
        if (!ReadPackSets(packAsset, slots, entries, why)) { why = L"its pack's sets are unreadable (" + why + L")"; }
        for (const auto& slot : slots)
        {
            if (slot.Set && SkelCompat::NameEquals(slot.Name, pack))
            {
                set = slot.Set;
                break;
            }
        }
        if (!set && why.empty()) { why = L"its pack has no set of that name"; }
    }
    if (set)
    {
        set->SetRootSet(); // it may be handed out after the pack's own references change
        Remember(container, KeyOf(name), set);
    }
    const std::wstring key = SkelCompat::FoldedKey(spec + L"/" + pack);
    if (std::find(Said.begin(), Said.end(), key) == Said.end())
    {
        Said.push_back(key);
        Log.Line(L"Animation sets: " + (spec.empty() ? std::wstring(L"a character") : spec) + L" was switched to " + pack +
                 L", a set the game did not take into its map (it took: " + GameSets(character) + L"): " +
                 (set ? L"the mod gives it its pack's own " + pack + L" (" + ObjectPath(set) + L")" : L"NOT given (" + why + L")") + L"; " + Counts());
    }
}

// After a pack switch (game thread): what the game's lookup did since, for the log (the first few switches).
void AfterSwitch(const std::wstring& pack)
{
    static int said = 0;
    if (!Hooked || said >= 12) { return; }
    ++said;
    Log.Line(L"Animation sets: switch to " + pack + L" done; " + Counts());
}
} // namespace PackSets

// EndBattleAPI SetPrimaryAnimPack(character, pack, ...) / ResetPrimaryAnimPack(character) just ran.
// The character and pack of a SetPrimaryAnimPack / ResetPrimaryAnimPack call (only reads its parameters).
bool ReadPackCall(UFunction* function, void* params, UObject*& character, std::wstring& pack, bool& reset)
{
    if (!params || !function) { return false; }
    reset = function == State.ResetPrimaryAnimPack;
    character = nullptr;
    pack = SkelCompat::DefaultAbilityPack();
    bool havePack = reset;
    for (FProperty* property : function->ForEachPropertyInChain())
    {
        if (!property) { continue; }
        const std::wstring type = TypeOf(property);
        const int32_t offset = property->GetOffset_Internal();
        if (offset < 0 || offset + property->GetElementSize() > function->GetParmsSize()) { continue; }
        if (!character && type == L"ObjectProperty") { std::memcpy(&character, static_cast<uint8_t*>(params) + offset, sizeof(character)); }
        else if (!havePack && type == L"NameProperty")
        {
            RawName raw{};
            std::memcpy(&raw, static_cast<uint8_t*>(params) + offset, sizeof(raw));
            pack = NameText(KeyOf(raw));
            havePack = true;
        }
    }
    return character && havePack;
}

void ApplyPackCall(UObject* character, const std::wstring& pack, bool reset, bool queued);

// A character's pack switched (now, or `queued` while the mod was busy): its abilities follow.
void ApplyPackCall(UObject* character, const std::wstring& pack, bool reset, bool queued)
{
    if (!Alive(character)) { return; }
    const std::wstring spec = CharaSpecRowOf(character);
    if (spec.empty()) { return; }
    const SkelCompat::AnimSetRow* row = State.Config.FindAnimSetRow(SkelCompat::CharacterPackPath(spec));
    if (!row) { return; }
    if (!reset && !SkelCompat::NameEquals(pack, SkelCompat::DefaultAbilityPack()) && CharaSpecListsSet(spec, pack) == 0)
    {
        const std::wstring key = SkelCompat::FoldedKey(spec + L"/" + pack);
        if (std::find(State.UnlistedPackWarnings.begin(), State.UnlistedPackWarnings.end(), key) == State.UnlistedPackWarnings.end())
        {
            State.UnlistedPackWarnings.push_back(key);
            const std::wstring warning = L"Animation sets: " + spec + L" was switched to " + pack + L", but its CharaSpec row's AnimationSetList does not name " +
                                         pack + L": a character only takes the sets its row names, so it keeps playing its pack (add " + pack +
                                         L" to the row's AnimationSetList in the CharaSpec table)";
            Log.Line(warning);
            NoteAbilityLine(warning);
        }
    }
    if (row->Abilities.empty()) { return; }
    bool wrote = false;
    std::wstring line = spec + (reset ? L" (pack reset)" : L"") + (queued ? L" (after the mod's work)" : L"") + L": " + ApplyAbilities(*row, pack, wrote);
    if (wrote)
    {
        line += RefreshAbilityLists(*row);
        State.AbilitiesSwitched = true;
    }
    Log.Line(L"Abilities: " + line);
    NoteAbilityLine(line);
}

// Every map load: the Battle00 lists (or the table's own) for each player row the rows name.
void ApplyDefaultAbilities()
{
    if (!State.AbilitiesWanted) { return; }
    std::vector<std::wstring> done;
    for (const auto& row : State.Config.AnimSets)
    {
        if (row.Abilities.empty() || std::any_of(done.begin(), done.end(), [&](const std::wstring& p) { return SkelCompat::NameEquals(p, row.Player); }))
        {
            continue;
        }
        done.push_back(row.Player);
        bool wrote = false;
        std::wstring line = L"map load: " + ApplyAbilities(row, SkelCompat::DefaultAbilityPack(), wrote);
        // the lists of a pack switched to before this map are still the game's until it recalculates
        if (wrote && State.AbilitiesSwitched) { line += RefreshAbilityLists(row); }
        Log.Line(L"Abilities: " + line);
        NoteAbilityLine(line);
    }
    State.AbilitiesSwitched = false;
}

// 3.3 "preload": objects the rows want resident (a CharaSpec pack a damage source spawns, ...): loaded at the first map
// load and kept for the session.
void PreloadRowAssets()
{
    std::vector<std::wstring> done;
    for (const auto& row : State.Config.AnimSets)
    {
        std::vector<std::wstring> paths = row.Preload;
        paths.insert(paths.end(), row.PackAssets.begin(), row.PackAssets.end());
        for (const auto& path : paths)
        {
            if (std::any_of(done.begin(), done.end(), [&](const std::wstring& p) { return SkelCompat::PathEquals(p, path); })) { continue; }
            done.push_back(path);
            UObject* object = FindObjectByPath(path.c_str());
            const bool found = object != nullptr;
            if (!object) { object = LoadBlocking(path); }
            if (object)
            {
                object->SetRootSet();
                Log.Line(L"Preload: " + path + (found ? L" (already loaded) kept" : L" loaded and kept"));
            }
            else
            {
                Log.Line(L"Preload: " + path + L" NOT found");
            }
        }
    }
}

void SetUpAbilities()
{
    std::wstring rows;
    for (const auto& row : State.Config.AnimSets)
    {
        if (row.Abilities.empty()) { continue; }
        std::wstring packs;
        for (const auto& entry : row.Abilities) { packs += (packs.empty() ? L"" : L", ") + entry.Pack; }
        rows += (rows.empty() ? L"" : L"; ") + ShortNameOfPath(row.Characters.front()) + L" (" + row.Player + L": " + packs + L")";
    }
    if (rows.empty()) { return; }
    State.SetPrimaryAnimPack = UObjectGlobals::StaticFindObject<UFunction*>(nullptr, nullptr, L"/Script/EndGame.EndBattleAPI:SetPrimaryAnimPack");
    State.ResetPrimaryAnimPack = UObjectGlobals::StaticFindObject<UFunction*>(nullptr, nullptr, L"/Script/EndGame.EndBattleAPI:ResetPrimaryAnimPack");
    State.GetCharaSpecName = UObjectGlobals::StaticFindObject<UFunction*>(nullptr, nullptr, L"/Script/EndGame.EndBattleAPI:GetCharaSpecName");
    State.BattleApi = FindObjectByPath(L"/Script/EndGame.Default__EndBattleAPI");
    State.AbilitiesWanted = State.SetPrimaryAnimPack && State.ResetPrimaryAnimPack && State.GetCharaSpecName && State.BattleApi;
    State.GetPlayerLevel = UObjectGlobals::StaticFindObject<UFunction*>(nullptr, nullptr, L"/Script/EndGame.EndMenuBPAPI:BPGetPlayerLevel");
    State.GetPlayerExperience = UObjectGlobals::StaticFindObject<UFunction*>(nullptr, nullptr, L"/Script/EndGame.EndMenuBPAPI:BPGetPlayerExperience");
    State.SetPlayerExperience = UObjectGlobals::StaticFindObject<UFunction*>(nullptr, nullptr, L"/Script/EndGame.EndMenuBPAPI:BPSetPlayerExperience");
    State.MenuApi = FindObjectByPath(L"/Script/EndGame.Default__EndMenuBPAPI");
    const bool recalculate = State.GetPlayerLevel && State.GetPlayerExperience && State.SetPlayerExperience && State.MenuApi;
    Log.Line(L"Abilities per animation pack: " + rows + L"; EndBattleAPI " +
             (State.AbilitiesWanted ? std::wstring(L"found, packs switch the lists")
                                    : std::wstring(L"functions NOT found (") + (State.SetPrimaryAnimPack ? L"" : L"SetPrimaryAnimPack ") +
                                          (State.ResetPrimaryAnimPack ? L"" : L"ResetPrimaryAnimPack ") + (State.GetCharaSpecName ? L"" : L"GetCharaSpecName ") +
                                          (State.BattleApi ? L"" : L"Default__EndBattleAPI") + L"): abilities stay as the tables have them") +
             L"; EndMenuBPAPI level / EXP functions " + (recalculate ? L"found (status recalculation after a switch, EXP and level kept)" : L"NOT found: switched lists show when the game next recalculates"));
}

std::wstring AbilityReport()
{
    std::wstring text;
    for (const auto& row : State.Config.AnimSets)
    {
        if (row.Abilities.empty()) { continue; }
        text += L"  " + ShortNameOfPath(row.Characters.front()) + L" -> " + row.Player +
                (row.RefreshAbilities ? std::wstring{} : std::wstring(L" (refresh_abilities off)")) + L"\n";
        for (const auto& entry : row.Abilities)
        {
            std::wstring weapons;
            for (const auto& [weapon, ability] : entry.Weapons) { weapons += (weapons.empty() ? L"" : L", ") + weapon + L" -> " + ability; }
            text += L"    " + entry.Pack + L": commands " +
                    (entry.HasCommands ? (entry.Commands.empty() ? std::wstring(L"(none)") : SkelCompat::Detail::Joined(entry.Commands)) : std::wstring(L"-")) +
                    L"; limits " + (entry.HasLimits ? (entry.Limits.empty() ? std::wstring(L"(none)") : SkelCompat::Detail::Joined(entry.Limits)) : std::wstring(L"-")) +
                    (entry.HasWeapons ? L"; weapon abilities " + (weapons.empty() ? std::wstring(L"the weapons' own") : weapons) : std::wstring{}) + L"\n";
        }
    }
    if (text.empty()) { return {}; }
    std::wstring out = L"\nAbilities per animation pack: " + std::wstring(State.AbilitiesWanted ? L"active" : L"OFF (EndBattleAPI functions not found)") +
                       (State.GetPlayerLevel && State.GetPlayerExperience && State.SetPlayerExperience && State.MenuApi
                            ? (State.RefreshProblem ? L", status recalculation SWITCHED OFF (" + State.RefreshText + L")" : std::wstring(L", status recalculation after a switch (EXP and level kept)"))
                            : std::wstring(L", no status recalculation (EndMenuBPAPI level / EXP functions not found)")) +
                       L" (the game lists 5 commands and 3 limits from a player row)\n  List getters: " + ListGetters::Status + L"\n  Weapon abilities: " +
                       WeaponAbilities::Status + L"\n" + text;
    out += L"  Last switches:\n";
    for (const auto& line : State.AbilityLines) { out += L"    " + line + L"\n"; }
    return out;
}

void WriteReport()
{
    std::vector<ReboundMesh> rebound;
    std::vector<UObject*> pending;
    std::vector<std::wstring> rooted;
    {
        std::lock_guard lock(State.Mutex);
        rebound = State.Rebound;
        pending = State.Pending;
        for (const auto& [key, skeleton] : State.Rooted) { rooted.push_back(key); }
    }
    std::wstring text = L"RebirthSkelCompat " + std::wstring(ModVersionText) + L" report\n\n";
    text += State.Faulted.load() ? L"STATE: switched off after an error (see RebirthSkelCompat.log)\n\n" : L"STATE: active\n\n";
    text += L"JSON pairs:\n";
    for (const auto& pair : State.Config.Pairs)
    {
        text += L"  " + std::wstring(pair.Use == SkelCompat::Method::Mesh ? L"mesh" : L"animations") + L", receiving " + pair.Receiving +
                (pair.FamilyHub.empty() ? std::wstring{} : L"  (family of " + ShortNameOfPath(pair.FamilyHub) + L")") + L"  [" + pair.Origin + L"]\n";
        for (const auto& animation : pair.Animation) { text += L"    animation " + animation + L"\n"; }
        for (const auto& name : pair.RequiresPaks) { text += L"    requires " + name + L" (installed)\n"; }
        if (pair.KeepProportions) { text += L"    proportions kept\n"; }
    }
    if (!State.ProportionSkeletons.empty())
    {
        text += L"\nProportions:\n";
        for (const auto& path : State.ProportionSkeletons) { text += L"  " + path + L"\n"; }
        for (const auto& line : State.ProportionLines) { text += L"  " + line + L"\n"; }
        if (!State.PosesToAdd.empty()) { text += L"  " + std::to_wstring(State.PosesToAdd.size()) + L" retarget pose(s) waiting for a safe point\n"; }
    }
    text += L"\nResident skeletons (" + std::to_wstring(rooted.size()) + L"):\n";
    for (const auto& key : rooted) { text += L"  " + key + L"\n"; }
    text += L"\nAnimation adoption (KH3 mode):\n";
    if (const AdoptionTable* table = State.Adoption.load(std::memory_order_acquire))
    {
        for (const auto& plan : table->Plans)
        {
            text += L"  " + plan->FromPath + L"\n    -> " + plan->ToPath + L"\n    " + plan->Summary + L"\n    adopted " +
                    std::to_wstring(plan->Adopted.load()) + L", refused " + std::to_wstring(plan->Refused.load()) + L"; curve tracks left out: " +
                    std::to_wstring(plan->CurvesDropped.load()) + L" in " + std::to_wstring(plan->AssetsDroppingCurves.load()) + L" adopted asset(s)" +
                    (plan->RetargetReplaced.load() ? L"; " + std::to_wstring(plan->RetargetReplaced.load()) + L" sequence(s) had their own retarget source replaced"
                                                   : std::wstring{}) +
                    L"\n";
        }
        std::vector<std::wstring> waiting;
        {
            std::lock_guard lock(State.AdoptMutex);
            for (const auto& entry : State.Waiting) { waiting.push_back(entry.Path); }
        }
        text += L"  Hooks: " + std::wstring(State.AnimHooksInstalled ? L"animation PostLoad hooked" : L"animation PostLoad NOT hooked (map loads only)") +
                L", frame safe point " + (State.ViewportSafePoint.load() ? L"available" : L"not seen (late passes only where nothing plays the old skeleton)") +
                L", late passes so far " + std::to_wstring(State.LatePasses) + L"\n";
        text += L"  Containers waiting for their animations (" + std::to_wstring(waiting.size()) + L"):\n";
        const size_t shown = std::min<size_t>(waiting.size(), 50);
        for (size_t k = 0; k < shown; ++k) { text += L"    " + waiting[k] + L"\n"; }
        if (waiting.size() > shown) { text += L"    (+" + std::to_wstring(waiting.size() - shown) + L" more)\n"; }
    }
    else
    {
        text += L"  none active\n";
    }
    text += L"\nRebound meshes (" + std::to_wstring(rebound.size()) + L"):\n";
    std::vector<UObject*> meshes;
    for (const auto& r : rebound)
    {
        text += L"  " + r.MeshPath + (r.Late ? L"  (late)" : L"") + L"\n    -> " + r.ToSkeleton + L"\n    " +
                (r.Diagnosed ? r.Diagnosis : L"(not checked yet)") + L"\n";
        if (!r.HierarchyNote.empty()) { text += L"    hierarchy fix: " + r.HierarchyNote + L"\n"; }
        if (!r.SocketNote.empty()) { text += L"    " + r.SocketNote + L"\n"; }
        if (Alive(r.Mesh)) { meshes.push_back(r.Mesh); }
    }
    text += L"\nWaiting for an animation skeleton (" + std::to_wstring(pending.size()) + L"):\n";
    for (UObject* mesh : pending) { text += L"  " + PathOf(mesh) + L"\n"; }
    text += L"\nLive components using rebound meshes:\n";
    for (const ComponentView& view : ComponentsUsing(meshes))
    {
        UObject* animSkeleton = view.AnimClass ? TargetSkeletonOf(view.AnimClass) : nullptr;
        UObject* meshSkeleton = view.Mesh ? RawMeshSkeleton(view.Mesh) : nullptr;
        text += L"  " + ObjectPath(view.Component) + L"\n    AnimClass " + (view.AnimClass ? PathOf(view.AnimClass) : L"none") +
                (animSkeleton ? L" (for " + ShortName(animSkeleton) + L")" : std::wstring{}) + L", mesh on " +
                (meshSkeleton ? ShortName(meshSkeleton) : std::wstring(L"?")) + L", AnimBlueprint instance " +
                (view.AnimInstance ? L"running" : (animSkeleton && meshSkeleton && animSkeleton != meshSkeleton
                                                       ? L"NONE (refused: the AnimBlueprint is made for another skeleton)"
                                                       : L"NONE (refused or not using an AnimBlueprint)")) +
                L"\n";
    }
    {
        std::lock_guard lock(State.AbpMutex);
        text += L"\nAnimBlueprints moved to their family's hub (" + std::to_wstring(State.AbpMoved.size()) + L"):\n";
        for (const auto& line : State.AbpLines) { text += L"  " + line + L"\n"; }
    }
    text += L"\nAnimBlueprints re-initialised so far: " + std::to_wstring(State.Repaired + State.AbpRepaired) + L"\n";
    text += L"PostLoad hook: " + PostLoadStats() + L"\n";
    if (!State.Config.AnimSets.empty())
    {
        text += L"\nAnimation set rows (" + std::to_wstring(State.Config.AnimSets.size()) + L"): " +
                (State.PackHookInstalled ? (State.SetsReady.load() ? std::wstring(L"active") : std::wstring(L"waiting for the first map load"))
                                         : std::wstring(L"OFF (see RebirthSkelCompat.log)")) +
                L", " + std::to_wstring(State.PacksMerged.load()) + L" pack load(s) merged\n";
        std::vector<std::wstring> merges;
        {
            std::lock_guard lock(State.PackMutex);
            merges = State.MergeLines;
        }
        for (const auto& line : State.SetLines) { text += L"  " + line + L"\n"; }
        text += L"  Packs merged (" + std::to_wstring(merges.size()) + L" shown):\n";
        for (const auto& line : merges) { text += L"  " + line + L"\n"; }
    }
    text += AbilityReport();
    if (!State.Config.Messages.empty())
    {
        text += L"\nConfig messages:\n";
        for (const auto& m : State.Config.Messages) { text += L"  " + m + L"\n"; }
    }
    const fs::path path = State.ModDirectory / L"RebirthSkelCompat.report.txt";
    std::ofstream file(path, std::ios::binary | std::ios::trunc);
    const std::string utf8 = SkelCompat::Narrow(text);
    file.write(utf8.data(), static_cast<std::streamsize>(utf8.size()));
    Log.Line(L"Report written to " + path.wstring());
}

struct BusyScope
{
    BusyScope() { State.Busy = true; }
    ~BusyScope() { State.Busy = false; }
};

// `mapLoad`: called from the map-load callback, a safe point for the late adoption pass.
void PumpBody(bool report, bool mapLoad)
{
    LoadQueuedSkeletons();
    BuildAdoptionPlans();
    CheckProportions();
    if (mapLoad && State.ProportionsWanted.load(std::memory_order_acquire)) { ApplyProportions(); }
    if (State.SetsReady.load(std::memory_order_acquire))
    {
        bool queued = false;
        {
            std::lock_guard lock(State.PackMutex);
            queued = !State.PacksToMerge.empty();
        }
        if (queued) { MergeQueuedPacks(); }
    }
    if (mapLoad)
    {
        // Every map load (behind a loading screen) also catches animations that slipped past the PostLoad hook.
        if (State.Adoption.load(std::memory_order_acquire)) { LatePass(true); }
    }
    else
    {
        CheckWaiting(false);
        MaybeLatePass(false);
    }
    ProcessPending();
    if (mapLoad) { MoveLoadedAnimBlueprints(); }
    RepairMovedAnimBlueprints();
    Diagnose();
    {
        std::lock_guard lock(State.Mutex);
        const bool more = (!State.Pending.empty() && State.PendingVersion != State.RootedVersion) || !State.LoadQueue.empty() ||
                          std::any_of(State.Rebound.begin(), State.Rebound.end(), [](const ReboundMesh& r) { return !r.Diagnosed; });
        if (more) { State.Work.store(true, std::memory_order_release); }
    }
    if (report) { WriteReport(); }
}

void Pump(bool force)
{
    if (State.Busy || GetCurrentThreadId() != State.GameThread.load(std::memory_order_acquire)) { return; }
    const bool report = State.ReportRequested.load(std::memory_order_acquire);
    // Without the frame safe point the late adoption pass runs from here (only for skeletons nothing plays on).
    const bool late = (State.LatePassWanted.load(std::memory_order_acquire) || State.WaitingCount.load(std::memory_order_relaxed) > 0) &&
                      !State.ViewportSafePoint.load(std::memory_order_relaxed);
    if (!force && !report && !late && !State.Work.load(std::memory_order_acquire)) { return; }
    const uint64_t now = GetTickCount64();
    if (!force && !report && now < State.NextPumpMs) { return; }
    if (!force && !report && late && !State.Work.load(std::memory_order_acquire) && now < State.LatePassNotBefore &&
        now < State.NextWaitingCheck)
    {
        return;
    }
    State.NextPumpMs = now + PumpIntervalMs;
    State.Work.store(false, std::memory_order_release);
    BusyScope busy;
    PumpBody(report && State.ReportRequested.exchange(false), false);
}

// ---------------------------------------------------------------------------------------
// UE4SS callbacks. They capture no mod object: UE4SS c0a8 cannot unregister them.
// ---------------------------------------------------------------------------------------
bool LateInit();

std::pair<bool, bool> OnLoadMapPost(UEngine*, FWorldContext&, FURL, UPendingNetGame*, FString&)
{
    if (!State.Enabled.load(std::memory_order_acquire) || State.Busy) { return {false, false}; }
    State.GameThread.store(GetCurrentThreadId(), std::memory_order_release);
    BusyScope busy;
    try
    {
        if (!State.LateInitDone)
        {
            State.LateInitDone = true;
            if (!LateInit())
            {
                State.Enabled.store(false);
                return {false, false};
            }
        }
        if (!State.Active.load(std::memory_order_acquire)) { return {false, false}; }
        PackSets::Clear(); // (a new map: new characters)
        // Without the PostLoad hook every map load is rescanned, so new meshes are still found.
        if (!State.StartupScanDone || !State.HookInstalled)
        {
            State.StartupScanDone = true;
            StartupScan();
        }
        if (!State.PreloadDone)
        {
            State.PreloadDone = true;
            PreloadAnimationSkeletons();
            PreloadRowAssets();
        }
        if (!State.SetsPreloaded && State.PackHookInstalled)
        {
            State.SetsPreloaded = true;
            // Plans first: the animations the source sets bring in are then adopted inside their own PostLoad.
            LoadQueuedSkeletons();
            BuildAdoptionPlans();
            PreloadAnimationSets();
            State.SetsReady.store(true, std::memory_order_release);
            MergeLoadedPacks();
        }
        State.NextPumpMs = GetTickCount64() + PumpIntervalMs;
        try
        {
            ApplyDefaultAbilities();
        }
        catch (...)
        {
            State.AbilitiesWanted = false;
            Log.Line(L"Abilities per animation pack switched off after an error at map load (the tables keep their own lists)");
        }
        PumpBody(State.ReportRequested.exchange(false), true);
        Log.Line(L"Map loaded. PostLoad hook so far: " + PostLoadStats());
    }
    catch (...)
    {
        Fault(L"map load callback");
    }
    return {false, false}; // keep the native LoadMap result
}

// After UGameViewportClient::Tick, i.e. after the world tick: every animation evaluation of the frame has finished
// and the next has not started, so already-loaded animations can be rewritten. Runs every frame: one atomic load
// unless there is work.
// ---------------------------------------------------------------------------------------
// 3.5.3: the Lua pump. UE4SS 3.0.1 runs a Lua mod's ExecuteInGameThread calls in whatever thread calls ProcessEvent next
// (not only the game thread), and every call makes a new Lua thread in a table its other threads read without a lock (a
// mod looping at frame rate crashes the game in time). For the Lua mods named here the mod calls their global function
// RebirthSkelCompatPump itself, every frame, on the game thread (after the world tick), on a Lua thread of their own;
// they stop their UE4SS loops once it runs. RebirthSkelCompatIsGameThread() tells a Lua mod whether it runs there.
// ---------------------------------------------------------------------------------------
namespace LuaPump
{
constexpr const wchar_t* Mods[] = {L"SephirothForms"};
constexpr const char* Function = "RebirthSkelCompatPump";

LuaMadeSimple::Lua* Target = nullptr; // the pumped mod's own Lua thread (game thread only after it is set)
std::wstring TargetMod;
int Failures = 0;
uint64_t Calls = 0;
bool Said = false;

int IsGameThread(const LuaMadeSimple::Lua& lua)
{
    const DWORD game = State.GameThread.load(std::memory_order_relaxed);
    lua.set_bool(game == 0 || GetCurrentThreadId() == game);
    return 1;
}

bool Pumped(StringViewType mod)
{
    for (const wchar_t* name : Mods)
    {
        if (mod == name) { return true; }
    }
    return false;
}

// A Lua mod started (UE4SS calls this for every one).
void Start(StringViewType mod, LuaMadeSimple::Lua& mainLua)
{
    try
    {
        mainLua.register_function("RebirthSkelCompatIsGameThread", &IsGameThread);
        if (!Pumped(mod)) { return; }
        // A Lua thread of the mod's own state for the pump (the main one is UE4SS's: its key binds run on it), kept
        // from the garbage collector by a registry reference.
        LuaMadeSimple::Lua& thread = mainLua.new_thread();
        mainLua.registry().make_ref();
        Target = &thread;
        TargetMod = std::wstring(mod);
        Failures = 0;
        Said = false;
        Log.Line(L"Lua pump: " + TargetMod + L" is called every frame on the game thread (" + SkelCompat::Widen(Function) + L")");
    }
    catch (const std::exception& e)
    {
        Target = nullptr;
        Log.Line(L"Lua pump: NOT set up for " + std::wstring(mod) + L" (" + SkelCompat::Widen(e.what()) + L")");
    }
}

void Stop(StringViewType mod)
{
    if (Target && mod == TargetMod)
    {
        Target = nullptr;
        Log.Line(L"Lua pump: " + TargetMod + L" stopped");
    }
}

// Game thread, every frame.
void Run()
{
    LuaMadeSimple::Lua* target = Target;
    if (!target) { return; }
    try
    {
        target->call_function(Function, 0, 0);
        ++Calls;
        Failures = 0;
        if (!Said)
        {
            Said = true;
            Log.Line(L"Lua pump: " + TargetMod + L"'s " + SkelCompat::Widen(Function) + L" runs");
        }
    }
    catch (const std::exception& e)
    {
        ++Failures;
        if (Failures <= 5 || Failures % 600 == 0) { Log.Line(L"Lua pump: " + TargetMod + L": " + SkelCompat::Widen(e.what())); }
        if (Failures >= 1200)
        {
            Target = nullptr;
            Log.Line(L"Lua pump: " + TargetMod + L" left alone after 1200 failed calls in a row");
        }
    }
    catch (...)
    {
        Target = nullptr;
        Log.Line(L"Lua pump: " + TargetMod + L" left alone after an error");
    }
}
} // namespace LuaPump

void OnViewportTickPost(UGameViewportClient*, float)
{
    if (!State.Active.load(std::memory_order_relaxed)) { return; }
    if (!State.ViewportSafePoint.load(std::memory_order_relaxed))
    {
        if (GetCurrentThreadId() != State.GameThread.load(std::memory_order_relaxed)) { return; }
        State.ViewportSafePoint.store(true, std::memory_order_relaxed);
        Log.Line(L"Frame safe point available (after the world tick): late adoption runs there");
    }
    if (LuaPump::Target && GetCurrentThreadId() == State.GameThread.load(std::memory_order_relaxed)) { LuaPump::Run(); }
    const bool waiting = State.WaitingCount.load(std::memory_order_relaxed) > 0;
    const bool proportions = State.ProportionsWanted.load(std::memory_order_relaxed);
    if ((!State.LatePassWanted.load(std::memory_order_relaxed) && !waiting && !proportions) || State.Busy) { return; }
    if (GetCurrentThreadId() != State.GameThread.load(std::memory_order_relaxed)) { return; }
    BusyScope busy;
    try
    {
        if (proportions) { ApplyProportions(); }
        CheckWaiting(true);
        if (State.LatePassWanted.load(std::memory_order_relaxed) && GetTickCount64() >= State.LatePassNotBefore) { LatePass(true); }
    }
    catch (...)
    {
        Fault(L"late adoption (frame safe point)");
    }
}

// 3.5: a pack switch is about to run: when the game's map of the character's sets has no set of that name, the mod
// finds it in the character's pack first (PackSets).
void OnProcessEventPre(UObject*, UFunction* function, void* params)
{
    if (!PackSets::Hooked || !function || function != State.SetPrimaryAnimPack) { return; }
    if (!State.Active.load(std::memory_order_relaxed)) { return; }
    if (GetCurrentThreadId() != State.GameThread.load(std::memory_order_relaxed)) { return; }
    UObject* character = nullptr;
    std::wstring pack;
    bool reset = false;
    if (!ReadPackCall(function, params, character, pack, reset) || reset) { return; }
    const bool wasBusy = State.Busy; // (the row lookup below runs a UFunction: nothing of the mod's runs inside it)
    State.Busy = true;
    try
    {
        PackSets::Prepare(character, pack);
    }
    catch (...)
    {
        Log.Line(L"Animation sets: the set of a pack switch could not be looked for (error)");
    }
    State.Busy = wasBusy;
}

void OnProcessEventPost(UObject*, UFunction* function, void* params)
{
    if (!State.Active.load(std::memory_order_relaxed)) { return; }
    if (GetCurrentThreadId() != State.GameThread.load(std::memory_order_relaxed))
    {
        if (function && (function == State.SetPrimaryAnimPack || function == State.ResetPrimaryAnimPack))
        {
            static std::atomic<int> said{0};
            if (said.fetch_add(1, std::memory_order_relaxed) < 8)
            {
                Log.Line(L"Animation sets: a pack switch ran on thread " + std::to_wstring(GetCurrentThreadId()) + L", not the game thread (" +
                         std::to_wstring(State.GameThread.load(std::memory_order_relaxed)) + L"): its abilities are left as they are");
            }
        }
        return;
    }
    // 3.3: a character's primary animation pack switched: its abilities follow. 3.4: a switch made while the mod is busy on
    // this thread (a call of the mod's ran a script that switched packs) is applied as soon as the mod is free.
    if (State.AbilitiesWanted && function && (function == State.SetPrimaryAnimPack || function == State.ResetPrimaryAnimPack))
    {
        UObject* character = nullptr;
        std::wstring pack;
        bool reset = false;
        if (!ReadPackCall(function, params, character, pack, reset)) { return; }
        PackSets::AfterSwitch(reset ? std::wstring(L"the default pack") : pack);
        if (State.Busy)
        {
            if (State.QueuedPackCalls.size() >= 16) { State.QueuedPackCalls.erase(State.QueuedPackCalls.begin()); }
            State.QueuedPackCalls.push_back(ModState::PackCall{character, pack, reset});
            return;
        }
        BusyScope busy;
        try
        {
            ApplyPackCall(character, pack, reset, false);
        }
        catch (...)
        {
            State.AbilitiesWanted = false;
            Log.Line(L"Abilities per animation pack switched off after an error (the tables keep the lists they had)");
        }
        return;
    }
    if (!State.QueuedPackCalls.empty() && !State.Busy)
    {
        BusyScope busy;
        std::vector<ModState::PackCall> calls;
        calls.swap(State.QueuedPackCalls);
        try
        {
            // only the last switch of each character counts
            for (size_t k = 0; k < calls.size(); ++k)
            {
                const bool later = std::any_of(calls.begin() + static_cast<std::ptrdiff_t>(k) + 1, calls.end(),
                                               [&](const ModState::PackCall& c) { return c.Character == calls[k].Character; });
                if (!later && State.AbilitiesWanted) { ApplyPackCall(calls[k].Character, calls[k].Pack, calls[k].Reset, true); }
            }
        }
        catch (...)
        {
            State.AbilitiesWanted = false;
            Log.Line(L"Abilities per animation pack switched off after an error (the tables keep the lists they had)");
        }
    }
    if (!State.Work.load(std::memory_order_relaxed) && !State.ReportRequested.load(std::memory_order_relaxed) &&
        !((State.LatePassWanted.load(std::memory_order_relaxed) || State.WaitingCount.load(std::memory_order_relaxed) > 0) &&
          !State.ViewportSafePoint.load(std::memory_order_relaxed)))
    {
        return;
    }
    try
    {
        Pump(false);
    }
    catch (...)
    {
        Fault(L"background work");
    }
}

// ---------------------------------------------------------------------------------------
// Configuration files
// ---------------------------------------------------------------------------------------
std::string ReadFileBytes(const fs::path& path)
{
    std::ifstream file(path, std::ios::binary);
    if (!file) { return {}; }
    std::string bytes((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    return bytes.size() > (1u << 20) ? std::string{} : bytes;
}

// Names a pair's requires_paks can match, folded: every .pak / .utoc under End\Content\Paks and End\Mods (file name
// without extension), plus the folders directly inside ~mods and End\Mods (a mod installed as a folder).
std::unordered_set<std::wstring> InstalledPaks()
{
    std::unordered_set<std::wstring> names;
    std::error_code ec;
    const auto scan = [&](const fs::path& root, int maxDepth, bool topFolders) {
        if (!fs::is_directory(root, ec)) { return; }
        for (auto it = fs::recursive_directory_iterator(root, fs::directory_options::skip_permission_denied, ec);
             it != fs::recursive_directory_iterator(); it.increment(ec))
        {
            if (ec) { break; }
            const fs::path& path = it->path();
            if (it->is_directory(ec))
            {
                if (topFolders && it.depth() == 0) { names.insert(Folded(path.filename().wstring())); }
                if (it.depth() >= maxDepth) { it.disable_recursion_pending(); }
                continue;
            }
            const std::wstring extension = Folded(path.extension().wstring());
            if (extension == L".pak" || extension == L".utoc") { names.insert(Folded(path.stem().wstring())); }
        }
    };
    const fs::path paks = State.GameContentPaks.parent_path(); // End\Content\Paks
    scan(paks, 3, false);
    scan(State.GameContentPaks, 3, true);
    scan(paks.parent_path().parent_path() / L"Mods", 5, true); // End\Mods (plugin mods)
    return names;
}

void LoadConfiguration()
{
    std::vector<fs::path> files;
    std::error_code ec;
    const fs::path compat = State.ModDirectory / L"compat";
    if (fs::is_directory(compat, ec))
    {
        for (const auto& entry : fs::directory_iterator(compat, ec))
        {
            if (entry.is_regular_file(ec) && SkelCompat::NameEquals(entry.path().extension().wstring(), L".json")) { files.push_back(entry.path()); }
        }
    }
    // Mods can ship "<anything>.skelcompat.json" next to their pak in ~mods, or inside their plugin folder in End\Mods.
    const fs::path pluginMods = State.GameContentPaks.parent_path().parent_path().parent_path() / L"Mods";
    for (const fs::path& root : {State.GameContentPaks, pluginMods})
    {
        if (!fs::is_directory(root, ec)) { continue; }
        for (auto it = fs::recursive_directory_iterator(root, fs::directory_options::skip_permission_denied, ec);
             it != fs::recursive_directory_iterator(); it.increment(ec))
        {
            if (ec) { break; }
            if (it.depth() > 3) { it.disable_recursion_pending(); continue; }
            const std::wstring name = it->path().filename().wstring();
            if (it->is_regular_file(ec) && name.size() > 16 &&
                SkelCompat::NameEquals(std::wstring_view(name).substr(name.size() - 16), L".skelcompat.json"))
            {
                files.push_back(it->path());
            }
        }
    }
    std::sort(files.begin(), files.end());
    for (const auto& file : files)
    {
        const std::string bytes = ReadFileBytes(file);
        SkelCompat::AppendConfig(bytes, file.filename().wstring(), State.Config);
        Log.Line(L"Read " + file.wstring());
    }
    // A pair tied to a swap pak (requires_paks) is only on while that pak is installed, so taking the pak out never
    // leaves the original character without its animations. Chains and shared animation skeletons are settled after
    // that, among the pairs that are on. The installed paks are only listed when a pair asks.
    bool listed = false;
    std::unordered_set<std::wstring> installed;
    SkelCompat::FinishConfig(State.Config, [&](const std::wstring& name) {
        if (!listed)
        {
            installed = InstalledPaks();
            listed = true;
        }
        return installed.count(Folded(name)) > 0;
    });
    for (const auto& message : State.Config.Messages) { Log.Line(L"Config: " + message); }
    for (const auto& pair : State.Config.Pairs)
    {
        std::wstring line;
        if (!pair.FamilyHub.empty())
        {
            // Pairs made for a family: one block for the family, the member mesh pairs only register their skeleton.
            if (pair.Use == SkelCompat::Method::Mesh)
            {
                State.ReceivingNames.insert(Folded(ShortNameOfPath(pair.Receiving)));
                WantPair(pair);
                continue;
            }
            line = L"Family (hub " + pair.Receiving + L"): these skeletons and the hub play each other's animations. Their animations are "
                   L"adopted onto the hub and their meshes are rebound to it:";
            for (const auto& a : pair.Animation) { line += L"\n    " + a; }
            if (pair.KeepProportions) { line += L"\n    proportions: every character keeps its own bone lengths"; }
            if (const SkelCompat::Pair* member = pair.Animation.empty() ? nullptr : State.Config.FindForSkeleton(pair.Animation.front()))
            {
                line += std::wstring(L"\n    hierarchy fix ") + (member->FixHierarchy ? L"on" : L"off") + L", own skeleton sockets " +
                        (member->CarrySockets ? L"kept" : L"not kept");
            }
        }
        else if (pair.Use == SkelCompat::Method::Animations)
        {
            line = L"Pair (animations, KH3 mode): " + pair.Receiving + L" adopts the animations of";
            for (const auto& a : pair.Animation) { line += L"\n    " + a; }
            if (!pair.AdoptPaths.empty())
            {
                line += L"\n    only under:";
                for (const auto& p : pair.AdoptPaths) { line += L" " + p; }
            }
            if (!pair.Meshes.empty()) { line += L"\n    (receiving_meshes only applies to \"mesh\" pairs and is ignored here)"; }
            if (pair.KeepProportions) { line += L"\n    proportions: the receiving characters keep their own bone lengths"; }
        }
        else
        {
            line = L"Pair (mesh): meshes on " + pair.Receiving + L" are rebound to and play animations of";
            for (const auto& a : pair.Animation) { line += L"\n    " + a; }
            if (!pair.Meshes.empty()) { line += L"\n    (limited to " + std::to_wstring(pair.Meshes.size()) + L" mesh(es))"; }
            if (pair.KeepProportions) { line += L"\n    proportions: the rebound characters keep their own bone lengths"; }
            State.ReceivingNames.insert(Folded(ShortNameOfPath(pair.Receiving)));
        }
        if (!pair.RequiresPaks.empty())
        {
            line += L"\n    on because these are installed:";
            for (const auto& name : pair.RequiresPaks) { line += L" " + name; }
        }
        Log.Line(line);
        WantPair(pair);
    }
    for (const auto& row : State.Config.AnimSets)
    {
        std::wstring line = L"Animation sets for " + row.Characters.front() + L"  [" + row.Origin + L"]";
        const auto sources = [&](const wchar_t* label, const std::vector<SkelCompat::SetSource>& list) {
            if (list.empty()) { return; }
            line += std::wstring(L"\n    ") + label + L" (first wins):";
            for (const auto& source : list)
            {
                line += L"\n      " + source.Path + (source.Folder ? L"  (folder)" : L"") + (source.As.empty() ? L"" : L"  as " + source.As);
                switch (source.Auto)
                {
                case SkelCompat::AutoMatchMode::Basic: line += L"  [auto: basic attacks]"; break;
                case SkelCompat::AutoMatchMode::Attacks: line += L"  [auto: attacks, abilities, limits]"; break;
                case SkelCompat::AutoMatchMode::All: line += L"  [auto: whole set + attacks]"; break;
                default: break;
                }
                if (source.Auto != SkelCompat::AutoMatchMode::Off && !source.Only.empty())
                {
                    line += L"  [only names with:";
                    for (const auto& word : source.Only) { line += L" " + word; }
                    line += L"]";
                }
            }
        };
        sources(L"battle sets from", row.Battle);
        sources(L"field sets from", row.Field);
        if (!row.Moves.empty())
        {
            const auto chains = std::count_if(row.Moves.begin(), row.Moves.end(), [](const SkelCompat::AnimMove& m) { return !m.Chain.empty(); });
            line += L"\n    " + std::to_wstring(row.Moves.size()) + L" move(s)" + (chains ? L", " + std::to_wstring(chains) + L" of them chained" : std::wstring{});
        }
        if (!row.Sockets.empty())
        {
            line += L"\n    socket stand-ins on meshes of " + row.Skeleton + L":";
            for (const auto& [wanted, use] : row.Sockets) { line += L" " + wanted + L" -> " + use + L";"; }
            State.AliasSkeletonNames.insert(Folded(ShortNameOfPath(row.Skeleton)));
        }
        if (row.KeepProportions) { line += L"\n    proportions: on for the pairs and families of " + row.Skeleton; }
        if (!row.FieldActions.empty()) { line += L"\n    field actions: " + row.FieldActions + L" (CharaSpec AnimationSetParentFolder)"; }
        if (!row.RequiresPaks.empty())
        {
            line += L"\n    on because these are installed:";
            for (const auto& name : row.RequiresPaks) { line += L" " + name; }
        }
        Log.Line(line);
        State.PackNames.insert(Folded(SkelCompat::ObjectNameOfPath(row.Characters.front())));
    }
    State.ProportionSkeletons = State.Config.ProportionSkeletons();
    for (const auto& path : State.ProportionSkeletons) { Log.Line(L"Proportions: " + path + L" gets the proportion modes once it is loaded"); }
    // Family members: their meshes go to the hub, and so do the AnimBlueprints made for them (3.2.1).
    State.AbpHubs.clear();
    for (const auto& pair : State.Config.Pairs)
    {
        if (pair.Use != SkelCompat::Method::Mesh || pair.FamilyHub.empty()) { continue; }
        State.AbpHubs[Folded(pair.Receiving)] = pair.FamilyHub;
        Log.Line(L"AnimBlueprints made for " + pair.Receiving + L" run on the hub " + pair.FamilyHub + L" (its meshes are rebound there)");
    }
}

fs::path ThisModuleDirectory()
{
    HMODULE module = nullptr;
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                       reinterpret_cast<LPCWSTR>(&ThisModuleDirectory), &module);
    std::vector<wchar_t> buffer(32768);
    const DWORD length = GetModuleFileNameW(module, buffer.data(), static_cast<DWORD>(buffer.size()));
    if (!length || length >= buffer.size()) { return {}; }
    return fs::path(std::wstring(buffer.data(), length)).parent_path(); // ...\Mods\RebirthSkelCompat\dlls
}

void PinModule()
{
    // Vtable and callback pointers outlive any UE4SS hot reload; never let this DLL unload.
    HMODULE pinned = nullptr;
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN, reinterpret_cast<LPCWSTR>(&PinModule), &pinned);
}

// Startup, on UE4SS's thread: files and callback registration only, no UObject access.
bool EarlyInit()
{
    const fs::path dlls = ThisModuleDirectory();
    State.ModDirectory = dlls.has_parent_path() ? dlls.parent_path() : dlls;
    Log.Open(State.ModDirectory / L"RebirthSkelCompat.log");
    Log.Line(L"RebirthSkelCompat " + std::wstring(ModVersionText) + L" starting (UE4SS c0a8d4c SDK)");

    if (fs::exists(State.ModDirectory / L"nohook.txt"))
    {
        Log.Line(L"nohook.txt present: mod stays off.");
        return false;
    }

    wchar_t exe[MAX_PATH]{};
    GetModuleFileNameW(nullptr, exe, MAX_PATH);
    State.GameContentPaks = fs::path(exe).parent_path().parent_path().parent_path() / L"Content" / L"Paks" / L"~mods";

    LoadConfiguration();
    if (State.Config.Pairs.empty() && State.Config.AnimSets.empty())
    {
        Log.Line(L"No JSON pairs. Pairs declared in AssetUserData (BP_SkelCompatUserData) on skeletons or meshes still apply.");
    }

    PinModule();
    State.Enabled.store(true, std::memory_order_release);
    Hook::RegisterLoadMapPostCallback(&OnLoadMapPost);
    Log.Line(L"Waiting for the first map load to finish setting up on the game thread");
    return true;
}

// Animation set rows: classes, layouts and the pack hook (the PostLoad slot was verified by the mesh hook).
void SetUpAnimationSetRows()
{
    State.AnimSetClass = FindClass(L"/Script/EndGame.EndAnimSet");
    State.PackClass = FindClass(L"/Script/EndGame.EndAssetDataAsset");
    UStruct* entryType = nullptr;
    if (State.AnimSetClass)
    {
        FProperty* assets = FindField(State.AnimSetClass, L"AnimationAssets");
        if (assets && TypeOf(assets) == L"MapProperty" && assets->GetArrayDim() == 1 && assets->GetElementSize() == static_cast<int32_t>(sizeof(NameMapHeader)) &&
            assets->GetOffset_Internal() >= 0 &&
            assets->GetOffset_Internal() + static_cast<int32_t>(sizeof(NameMapHeader)) <= State.AnimSetClass->GetPropertiesSize())
        {
            State.OffSetAssets = assets->GetOffset_Internal();
        }
        State.OffSetDisplayName = FieldOffset(State.AnimSetClass, L"DisplayName", {L"NameProperty"}, 8);
    }
    if (State.PackClass)
    {
        entryType = ArrayStructField(State.PackClass, L"AssetDataList", State.OffPackList, State.PackEntryStride);
        if (entryType) { State.OffEntryObjects = ObjectArrayField(entryType, L"AssetUserData"); }
        if (State.OffEntryObjects < 0 || State.OffEntryObjects + static_cast<int32_t>(sizeof(RawArray)) > State.PackEntryStride) { State.OffEntryObjects = -1; }
    }
    const bool layout = State.AnimSetClass && State.PackClass && State.OffSetAssets >= 0 && State.OffPackList >= 0 && State.OffEntryObjects >= 0;
    Log.Line(L"Animation set rows: EndAnimSet " + std::wstring(State.AnimSetClass ? L"found" : L"NOT found") + L", AnimationAssets " +
             Hex(static_cast<uintptr_t>(State.OffSetAssets)) + L", DisplayName " + Hex(static_cast<uintptr_t>(State.OffSetDisplayName)) +
             L"; EndAssetDataAsset " + (State.PackClass ? L"found" : L"NOT found") + L", AssetDataList " + Hex(static_cast<uintptr_t>(State.OffPackList)) +
             L" (stride " + std::to_wstring(State.PackEntryStride) + L", AssetUserData " + Hex(static_cast<uintptr_t>(State.OffEntryObjects)) + L")");
    if (!layout)
    {
        Log.Line(L"Animation set rows are off: the classes or their layout were not recognised");
        return;
    }
    if (!State.HookInstalled)
    {
        Log.Line(L"Animation set rows are off: the PostLoad slot could not be verified");
        return;
    }
    State.PackHookInstalled = InstallPackPostLoadHook();
    if (!State.PackHookInstalled) { Log.Line(L"Animation set rows are off: the CharaSpec pack hook could not be installed"); }
}

// First map load, on the game thread: class lookups, offsets and the PostLoad hook.
bool LateInit()
{
    State.SkeletonClass = FindClass(L"/Script/Engine.Skeleton");
    State.MeshClass = FindClass(L"/Script/Engine.SkeletalMesh");
    State.ComponentClass = FindClass(L"/Script/Engine.SkeletalMeshComponent");
    State.SetAnimClass = UObjectGlobals::StaticFindObject<UFunction*>(nullptr, nullptr, L"/Script/Engine.SkeletalMeshComponent:SetAnimClass");
    State.MakeSoftObjectPath = UObjectGlobals::StaticFindObject<UFunction*>(nullptr, nullptr, L"/Script/Engine.KismetSystemLibrary:MakeSoftObjectPath");
    State.ConvertSoftObjectPath = UObjectGlobals::StaticFindObject<UFunction*>(nullptr, nullptr, L"/Script/Engine.KismetSystemLibrary:Conv_SoftObjPathToSoftObjRef");
    State.LoadAssetBlocking = UObjectGlobals::StaticFindObject<UFunction*>(nullptr, nullptr, L"/Script/Engine.KismetSystemLibrary:LoadAsset_Blocking");
    State.KismetSystemLibrary = FindObjectByPath(L"/Script/Engine.Default__KismetSystemLibrary");
    if (!State.SkeletonClass || !State.MeshClass)
    {
        Log.Line(L"Disabled: Skeleton/SkeletalMesh classes not found");
        return false;
    }
    State.OffMeshSkeleton = FieldOffset(State.MeshClass, L"Skeleton", {L"ObjectProperty"}, 8);
    State.OffSkelRefLocalPoses = FieldOffset(State.SkeletonClass, L"RefLocalPoses", {L"ArrayProperty"}, 16);
    State.OffSkelVirtualBones = FieldOffset(State.SkeletonClass, L"VirtualBones", {L"ArrayProperty"}, 16);
    State.OffSkelUserData = FieldOffset(State.SkeletonClass, L"AssetUserData", {L"ArrayProperty"}, 16);
    State.OffMeshUserData = FieldOffset(State.MeshClass, L"AssetUserData", {L"ArrayProperty"}, 16);
    if (State.ComponentClass)
    {
        State.OffCompMesh = FieldOffset(State.ComponentClass, L"SkeletalMesh", {L"ObjectProperty"}, 8);
        State.OffCompAnimClass = FieldOffset(State.ComponentClass, L"AnimClass", {L"ClassProperty"}, 8);
        State.OffCompAnimInstance = FieldOffset(State.ComponentClass, L"AnimScriptInstance", {L"ObjectProperty"}, 8);
    }
    Log.Line(L"Offsets: SkeletalMesh.Skeleton " + Hex(static_cast<uintptr_t>(State.OffMeshSkeleton)) + L", Skeleton.RefLocalPoses " +
             Hex(static_cast<uintptr_t>(State.OffSkelRefLocalPoses)) + L", Component.SkeletalMesh " +
             Hex(static_cast<uintptr_t>(State.OffCompMesh)) + L", AnimClass " + Hex(static_cast<uintptr_t>(State.OffCompAnimClass)) +
             L", AnimScriptInstance " + Hex(static_cast<uintptr_t>(State.OffCompAnimInstance)) + L", AssetUserData skeleton " +
             Hex(static_cast<uintptr_t>(State.OffSkelUserData)) + L" / mesh " + Hex(static_cast<uintptr_t>(State.OffMeshUserData)) +
             (State.SetAnimClass ? L", SetAnimClass found" : L", SetAnimClass missing (no repair)") + L", game thread " +
             std::to_wstring(State.GameThread.load()));
    if (State.OffMeshSkeleton < 0)
    {
        Log.Line(L"Disabled: SkeletalMesh.Skeleton property not found");
        return false;
    }
    State.OffMeshSockets = ObjectArrayField(State.MeshClass, L"Sockets");
    State.OffSkelSockets = ObjectArrayField(State.SkeletonClass, L"Sockets");
    if (UClass* socketClass = FindClass(L"/Script/Engine.SkeletalMeshSocket"))
    {
        State.SocketClass = socketClass;
        State.OffSocketName = FieldOffset(socketClass, L"SocketName", {L"NameProperty"}, 8);
        State.OffSocketBone = FieldOffset(socketClass, L"BoneName", {L"NameProperty"}, 8);
    }
    Log.Line(L"Sockets: SkeletalMesh.Sockets " + Hex(static_cast<uintptr_t>(State.OffMeshSockets)) + L", Skeleton.Sockets " +
             Hex(static_cast<uintptr_t>(State.OffSkelSockets)) + L", SocketName " + Hex(static_cast<uintptr_t>(State.OffSocketName)) + L", BoneName " +
             Hex(static_cast<uintptr_t>(State.OffSocketBone)));

    // Animation adoption (KH3 mode): classes and layouts. UAnimSequence::CompressedData directly follows the
    // CurveCompressionSettings pointer (UE 4.26 AnimSequence.h) and is checked against the next property.
    // Everything else is located through reflection; a layout that does not check out disables that part.
    State.AnimAssetClass = FindClass(L"/Script/Engine.AnimationAsset");
    State.AnimSequenceClass = FindClass(L"/Script/Engine.AnimSequence");
    State.AnimCompositeClass = FindClass(L"/Script/Engine.AnimComposite");
    State.AnimMontageClass = FindClass(L"/Script/Engine.AnimMontage");
    State.BlendSpaceBaseClass = FindClass(L"/Script/Engine.BlendSpaceBase");
    if (State.AnimAssetClass)
    {
        State.OffAnimSkeleton = FieldOffset(State.AnimAssetClass, L"Skeleton", {L"ObjectProperty"}, 8);
        // UAnimationAsset: USkeleton* Skeleton; FGuid SkeletonGuid; FGuid SkeletonVirtualBoneGuid; TArray MetaData (reflected).
        const int32_t metaData = FieldOffset(State.AnimAssetClass, L"MetaData", {L"ArrayProperty"}, 16);
        if (State.OffAnimSkeleton >= 0 && metaData == State.OffAnimSkeleton + 0x28) { State.OffAnimVirtualBoneGuid = State.OffAnimSkeleton + 0x18; }
    }
    State.OffSkelVirtualBoneGuid = FieldOffset(State.SkeletonClass, L"VirtualBoneGuid", {L"StructProperty"}, 16);
    if (UClass* sequenceBase = FindClass(L"/Script/Engine.AnimSequenceBase"))
    {
        State.AnimSequenceBaseClass = sequenceBase;
        State.OffSeqBlendOut = FieldOffset(sequenceBase, L"OverrideBehaviorActionBlendOutSequence", {L"ObjectProperty"}, 8);
        State.OffSeqLength = FieldOffset(sequenceBase, L"SequenceLength", {L"FloatProperty"}, 4);
    }
    if (State.AnimSequenceClass)
    {
        State.OffSeqRefPose = FieldOffset(State.AnimSequenceClass, L"RefPoseSeq", {L"ObjectProperty"}, 8);
        const int32_t curveSettings = FieldOffset(State.AnimSequenceClass, L"CurveCompressionSettings", {L"ObjectProperty"}, 8);
        const int32_t additive = FieldOffset(State.AnimSequenceClass, L"AdditiveAnimType", {L"ByteProperty", L"EnumProperty"}, 1);
        State.OffSeqAdditiveType = additive;
        State.OffSeqRetargetSource = FieldOffset(State.AnimSequenceClass, L"RetargetSource", {L"NameProperty"}, 8);
        // FCompressedAnimSequence is about 0x78 bytes in a cooked 4.26 build; anything far off means a different layout.
        if (curveSettings >= 0 && additive > curveSettings + 0x48 && additive <= curveSettings + 0xC0) { State.OffSeqCompressed = curveSettings + 8; }
        State.OffSeqRawTracks = FieldOffset(State.AnimSequenceClass, L"TrackToSkeletonMapTable", {L"ArrayProperty"}, 16);
        if (UStruct* attrs = ArrayStructField(State.AnimSequenceClass, L"BakedPerBoneCustomAttributeData", State.OffSeqCustomAttrs, State.SeqCustomAttrStride))
        {
            // An unknown element layout keeps AttrBone at -1: sequences that carry baked attributes are then refused.
            State.AttrBone = FieldOffset(attrs, L"BoneTreeIndex", {L"IntProperty"}, 4);
            const wchar_t* lists[] = {L"StringAttributes", L"IntAttributes", L"FloatAttributes"};
            for (size_t k = 0; k < State.AttrArrays.size(); ++k) { State.AttrArrays[k] = FieldOffset(attrs, lists[k], {L"ArrayProperty"}, 16); }
        }
        else
        {
            State.OffSeqCustomAttrs = ArrayField(State.AnimSequenceClass, L"BakedPerBoneCustomAttributeData", State.SeqCustomAttrStride);
        }
        Log.Line(L"AnimSequence: CurveCompressionSettings " + Hex(static_cast<uintptr_t>(curveSettings)) + L", AdditiveAnimType " +
                 Hex(static_cast<uintptr_t>(additive)) + L" -> CompressedData " +
                 (State.OffSeqCompressed >= 0 ? Hex(static_cast<uintptr_t>(State.OffSeqCompressed)) : std::wstring(L"not recognised")));
    }
    // FSmartName must be { FName DisplayName; uint16 UID; } (12 bytes) for the curve tables.
    UObject* smartName = FindObjectByPath(L"/Script/Engine.SmartName");
    const bool smartNameOk = smartName && smartName->IsA<UScriptStruct>() &&
                             static_cast<UStruct*>(static_cast<UScriptStruct*>(smartName))->GetPropertiesSize() == static_cast<int32_t>(SmartNameStride) &&
                             FieldOffset(static_cast<UScriptStruct*>(smartName), L"DisplayName", {L"NameProperty"}, 8) == 0;
    if (!smartNameOk) { State.OffSeqCompressed = -1; }
    if (UClass* sequenceBase = FindClass(L"/Script/Engine.AnimSequenceBase"); sequenceBase && smartNameOk)
    {
        int32_t rawCurves = -1, floatCurves = -1;
        if (UStruct* rawType = StructField(sequenceBase, L"RawCurveData", rawCurves))
        {
            if (UStruct* floatType = ArrayStructField(rawType, L"FloatCurves", floatCurves, State.FloatCurveStride))
            {
                int32_t nameAt = -1;
                if (StructField(floatType, L"Name", nameAt) && nameAt >= 0 && nameAt + static_cast<int32_t>(SmartNameStride) <= State.FloatCurveStride)
                {
                    State.OffRawFloatCurves = rawCurves + floatCurves;
                    State.FloatCurveName = nameAt;
                }
            }
        }
    }
    int32_t trackSize = 0;
    UStruct* trackType = nullptr;
    if (State.AnimCompositeClass) { trackType = StructField(State.AnimCompositeClass, L"AnimationTrack", State.OffCompositeTrack); }
    if (State.AnimMontageClass)
    {
        if (UStruct* slotType = ArrayStructField(State.AnimMontageClass, L"SlotAnimTracks", State.OffMontageSlots, State.SlotStride))
        {
            UStruct* slotTrack = StructField(slotType, L"AnimTrack", State.SlotTrack);
            if (!trackType) { trackType = slotTrack; }
            if (slotTrack != trackType) { State.SlotTrack = -1; }
        }
    }
    if (trackType)
    {
        if (UStruct* segmentType = ArrayStructField(trackType, L"AnimSegments", State.TrackSegments, State.SegmentStride))
        {
            State.SegmentRef = FieldOffset(segmentType, L"AnimReference", {L"ObjectProperty"}, 8);
            State.SegStartPos = FieldOffset(segmentType, L"StartPos", {L"FloatProperty"}, 4);
            State.SegAnimStart = FieldOffset(segmentType, L"AnimStartTime", {L"FloatProperty"}, 4);
            State.SegAnimEnd = FieldOffset(segmentType, L"AnimEndTime", {L"FloatProperty"}, 4);
            State.SegPlayRate = FieldOffset(segmentType, L"AnimPlayRate", {L"FloatProperty"}, 4);
            State.SegLooping = FieldOffset(segmentType, L"LoopingCount", {L"IntProperty"}, 4);
            State.SegBlendTime = FieldOffset(segmentType, L"AnimBlendTime", {L"FloatProperty"}, 4);
            State.SegTriggerNotify = FieldOffset(segmentType, L"bTriggerAnimReferenceNotify", {L"BoolProperty"}, 1);
            // bValid is declared right after the last property (UE 4.26 AnimCompositeBase.h; Rebirth adds AnimBlendTime and
            // bTriggerAnimReferenceNotify before it).
            const int32_t valid = State.SegTriggerNotify >= 0 ? State.SegTriggerNotify + 1 : (State.SegLooping >= 0 ? State.SegLooping + 4 : -1);
            if (valid > 0 && valid < State.SegmentStride) { State.SegValid = valid; }
        }
        trackSize = trackType->GetPropertiesSize();
    }
    if (State.BlendSpaceBaseClass)
    {
        if (UStruct* sampleType = ArrayStructField(State.BlendSpaceBaseClass, L"SampleData", State.OffBlendSamples, State.SampleStride))
        {
            State.SampleAnim = FieldOffset(sampleType, L"Animation", {L"ObjectProperty"}, 8);
        }
        UStruct* perBoneType = ArrayStructField(State.BlendSpaceBaseClass, L"PerBoneBlend", State.OffBlendPerBone, State.BlendPerBoneStride);
        if (!perBoneType) { State.OffBlendPerBone = ArrayField(State.BlendSpaceBaseClass, L"PerBoneBlend", State.BlendPerBoneStride); }
        if (perBoneType)
        {
            int32_t reference = -1;
            UStruct* referenceType = StructField(perBoneType, L"BoneReference", reference);
            // FBoneReference: FName BoneName; int32 BoneIndex:31; uint32 bUseSkeletonIndex:1; FCompactPoseBoneIndex (16 bytes).
            if (referenceType && referenceType->GetPropertiesSize() == 16 && FieldOffset(referenceType, L"BoneName", {L"NameProperty"}, 8) == 0)
            {
                State.PerBoneRef = reference;
            }
        }
    }
    State.OffSkelSmartNames = FieldOffset(State.SkeletonClass, L"SmartNames", {L"StructProperty"}, static_cast<int32_t>(sizeof(NameMapHeader)));
    // 3.2 proportions: USkeleton::BoneTree (reflected) and AnimRetargetSources, a native TMap declared right after
    // Sockets and followed by the reflected SmartNames (UE 4.26 Skeleton.h); only trusted when those line up.
    if (UStruct* node = ArrayStructField(State.SkeletonClass, L"BoneTree", State.OffSkelBoneTree, State.BoneNodeStride))
    {
        State.BoneNodeMode = FieldOffset(node, L"TranslationRetargetingMode", {L"ByteProperty", L"EnumProperty"}, 1);
    }
    // UE 4.26 declares it right after Sockets; Rebirth keeps 0x30 bytes of its own after it, before SmartNames (seen in
    // 3.2.1's dump of Cloud's skeleton: an empty TMap at Sockets + 0x10). Each skeleton's map header is checked before
    // the map is read or written (RetargetSourcesUsable, AddRetargetPoses).
    if (State.OffSkelSockets >= 0 && State.OffSkelSmartNames >= State.OffSkelSockets + static_cast<int32_t>(sizeof(RawArray) + sizeof(NameMapHeader)))
    {
        State.OffSkelRetargetSources = State.OffSkelSockets + static_cast<int32_t>(sizeof(RawArray));
    }
    Log.Line(L"3.2 offsets: AnimSequenceBase.SequenceLength " + Hex(static_cast<uintptr_t>(State.OffSeqLength)) + L", AnimSequence.AdditiveAnimType " +
             Hex(static_cast<uintptr_t>(State.OffSeqAdditiveType)) + L", AnimSequence.RetargetSource " + Hex(static_cast<uintptr_t>(State.OffSeqRetargetSource)) +
             L", Skeleton.BoneTree " + Hex(static_cast<uintptr_t>(State.OffSkelBoneTree)) + L" (stride " + std::to_wstring(State.BoneNodeStride) +
             L", mode " + Hex(static_cast<uintptr_t>(State.BoneNodeMode)) + L"), Skeleton.AnimRetargetSources " +
             (State.OffSkelRetargetSources >= 0 ? Hex(static_cast<uintptr_t>(State.OffSkelRetargetSources)) : std::wstring(L"NOT located")) +
             L", SkeletalMeshSocket " + (State.SocketClass ? L"found" : L"NOT found"));
    Log.Line(L"Animation adoption offsets: AnimationAsset.Skeleton " + Hex(static_cast<uintptr_t>(State.OffAnimSkeleton)) +
             L", SkeletonVirtualBoneGuid " + Hex(static_cast<uintptr_t>(State.OffAnimVirtualBoneGuid)) + L", Skeleton.VirtualBoneGuid " +
             Hex(static_cast<uintptr_t>(State.OffSkelVirtualBoneGuid)) + L", blend-out sequence " + Hex(static_cast<uintptr_t>(State.OffSeqBlendOut)) +
             L", additive base " + Hex(static_cast<uintptr_t>(State.OffSeqRefPose)) +
             L", AnimSequence raw tracks " + Hex(static_cast<uintptr_t>(State.OffSeqRawTracks)) + L", baked attributes " +
             Hex(static_cast<uintptr_t>(State.OffSeqCustomAttrs)) + L" (stride " + std::to_wstring(State.SeqCustomAttrStride) +
             L"), curve tracks " + Hex(static_cast<uintptr_t>(State.OffRawFloatCurves)) + L" (stride " + std::to_wstring(State.FloatCurveStride) +
             L", name " + Hex(static_cast<uintptr_t>(State.FloatCurveName)) + L"), composite track " + Hex(static_cast<uintptr_t>(State.OffCompositeTrack)) +
             L", montage slots " + Hex(static_cast<uintptr_t>(State.OffMontageSlots)) + L" (stride " + std::to_wstring(State.SlotStride) + L", track " +
             Hex(static_cast<uintptr_t>(State.SlotTrack)) + L"), segments " + Hex(static_cast<uintptr_t>(State.TrackSegments)) + L" (stride " +
             std::to_wstring(State.SegmentStride) + L", animation " + Hex(static_cast<uintptr_t>(State.SegmentRef)) + L", track size " +
             std::to_wstring(trackSize) + L"), blend samples " + Hex(static_cast<uintptr_t>(State.OffBlendSamples)) + L" (stride " +
             std::to_wstring(State.SampleStride) + L", animation " + Hex(static_cast<uintptr_t>(State.SampleAnim)) + L"), per-bone blend " +
             Hex(static_cast<uintptr_t>(State.OffBlendPerBone)) + L" (stride " + std::to_wstring(State.BlendPerBoneStride) + L", bone " +
             Hex(static_cast<uintptr_t>(State.PerBoneRef)) + L"), Skeleton.SmartNames " + Hex(static_cast<uintptr_t>(State.OffSkelSmartNames)) +
             (smartNameOk ? L", FSmartName 12 bytes" : L", FSmartName layout NOT recognised (sequences are not adopted)"));

    State.Active.store(true, std::memory_order_release);
    State.HookInstalled = InstallPostLoadHook();
    if (!State.HookInstalled)
    {
        Log.Line(L"PostLoad hook not installed: meshes are rebound late on each map load instead (repair still applies)");
    }
    const bool adoptionWanted = std::any_of(State.Config.Pairs.begin(), State.Config.Pairs.end(),
                                            [](const SkelCompat::Pair& p) { return p.Use == SkelCompat::Method::Animations; });
    if (adoptionWanted)
    {
        // The slot index was verified by the mesh hook; without that check nothing else is patched.
        State.AnimHooksInstalled = State.HookInstalled && State.OffAnimSkeleton >= 0 && InstallAnimPostLoadHooks();
        if (!State.AnimHooksInstalled)
        {
            Log.Line(L"Animation PostLoad hook not installed: animations are adopted on each map load instead");
        }
    }
    if (!State.Config.AnimSets.empty())
    {
        SetUpAnimationSetRows();
        SetUpAbilities();
        // 3.5: every set of a character's pack can be switched to (not only those the game takes from its row's slots)
        if (!State.SetPrimaryAnimPack)
        {
            State.SetPrimaryAnimPack = UObjectGlobals::StaticFindObject<UFunction*>(nullptr, nullptr, L"/Script/EndGame.EndBattleAPI:SetPrimaryAnimPack");
            State.ResetPrimaryAnimPack = UObjectGlobals::StaticFindObject<UFunction*>(nullptr, nullptr, L"/Script/EndGame.EndBattleAPI:ResetPrimaryAnimPack");
            State.GetCharaSpecName = UObjectGlobals::StaticFindObject<UFunction*>(nullptr, nullptr, L"/Script/EndGame.EndBattleAPI:GetCharaSpecName");
            State.BattleApi = FindObjectByPath(L"/Script/EndGame.Default__EndBattleAPI");
        }
        if (State.SetPrimaryAnimPack && State.GetCharaSpecName && State.BattleApi)
        {
            PackSets::Install();
            Log.Line(L"Animation sets: " + PackSets::Status);
        }
        else
        {
            Log.Line(L"Animation sets: EndBattleAPI SetPrimaryAnimPack / GetCharaSpecName NOT found: only the sets the game takes from a row's slots can be switched to");
        }
    }
    if (!State.AbpHubs.empty())
    {
        State.AbpClass = FindClass(L"/Script/Engine.AnimBlueprintGeneratedClass");
        if (State.AbpClass) { State.OffAbpTargetSkeleton = FieldOffset(State.AbpClass, L"TargetSkeleton", {L"ObjectProperty"}, 8); }
        if (!State.AbpClass || State.OffAbpTargetSkeleton < 0)
        {
            Log.Line(L"AnimBlueprints of family members stay on their own skeleton: AnimBlueprintGeneratedClass.TargetSkeleton was not found "
                     L"(a member character that uses its own AnimBlueprint T-poses)");
        }
        else
        {
            Log.Line(L"AnimBlueprintGeneratedClass.TargetSkeleton " + Hex(static_cast<uintptr_t>(State.OffAbpTargetSkeleton)) +
                     L": AnimBlueprints of family members follow the hub");
            if (!State.HookInstalled || !InstallAbpPostLoadHook())
            {
                Log.Line(L"AnimBlueprint PostLoad hook not installed: AnimBlueprints are moved on each map load instead (live components are re-initialised)");
            }
        }
    }
    // Registered here, on the game thread and outside any ProcessEvent or viewport tick, so UE4SS's callback
    // lists are never extended while the game walks them.
    Hook::RegisterProcessEventPostCallback(&OnProcessEventPost);
    if (PackSets::Hooked) { Hook::RegisterProcessEventPreCallback(&OnProcessEventPre); }
    Hook::RegisterGameViewportClientTickPostCallback(&OnViewportTickPost); // (late adoption, proportions, 3.5.3 the Lua pump)
    Log.Line(L"Ready. Press F9 in game to write RebirthSkelCompat.report.txt");
    return true;
}

class RebirthSkelCompatMod final : public CppUserModBase
{
public:
    RebirthSkelCompatMod()
    {
        ModName = L"RebirthSkelCompat";
        ModVersion = ModVersionText;
        ModDescription = L"KH3-style skeleton compatibility: a skeleton adopts the animations of other skeletons, or meshes are rebound to them.";
        ModAuthors = L"Kade";
        ModIntendedSDKVersion = L"3.0.1-c0a8d4c / UEPseudo-b4a6e7";
    }

    void on_unreal_init() override
    {
        static std::atomic<bool> started{false};
        if (started.exchange(true)) { return; }
        bool ok = false;
        try
        {
            ok = EarlyInit();
        }
        catch (...)
        {
            Log.Line(L"Startup failed; mod disabled");
            State.Enabled.store(false);
            State.Active.store(false);
        }
        if (ok)
        {
            register_keydown_event(Input::Key::F9, [] { State.ReportRequested.store(true, std::memory_order_release); });
        }
    }

    // 3.5.3: every Lua mod gets RebirthSkelCompatIsGameThread; the ones in LuaPump::Mods are called every frame.
    void on_lua_start(StringViewType mod_name, LuaMadeSimple::Lua& lua, LuaMadeSimple::Lua& main_lua, LuaMadeSimple::Lua& async_lua,
                      std::vector<LuaMadeSimple::Lua*>& hook_luas) override
    {
        (void)lua;
        (void)async_lua;
        (void)hook_luas;
        LuaPump::Start(mod_name, main_lua);
    }

    void on_lua_stop(StringViewType mod_name, LuaMadeSimple::Lua& lua, LuaMadeSimple::Lua& main_lua, LuaMadeSimple::Lua& async_lua,
                     std::vector<LuaMadeSimple::Lua*>& hook_luas) override
    {
        (void)lua;
        (void)main_lua;
        (void)async_lua;
        (void)hook_luas;
        LuaPump::Stop(mod_name);
    }

    ~RebirthSkelCompatMod() override
    {
        // Hooks cannot be removed in this UE4SS build; the pinned module keeps them valid.
        // Rebinds already made stay in place until the meshes are unloaded.
    }
};
} // namespace

extern "C" __declspec(dllexport) RC::CppUserModBase* start_mod() { return new RebirthSkelCompatMod(); }
extern "C" __declspec(dllexport) void uninstall_mod(RC::CppUserModBase* mod) { delete mod; }
