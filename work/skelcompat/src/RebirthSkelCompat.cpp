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
//   * LoadMap post-callback (game thread): the first call finishes initialisation (class lookups,
//     offsets, hooks), then scans already-loaded assets and preloads + roots the configured skeletons.
//   * GameViewportClient::Tick post-callback (game thread, after the world tick): late adoption of
//     animations that were loaded before their plan existed.
//   * ProcessEvent post-callback (game thread only, throttled): late rebinds, repair of components
//     whose AnimBlueprint was refused before the rebind, diagnostics, F9 report.
// Any error inside the mod switches the mod off for the session instead of taking the game down.

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include <algorithm>
#include <array>
#include <atomic>
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

constexpr wchar_t ModVersionText[] = L"3.0.0";
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
    if (!pair) { return false; }

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

// GetTypeHash(FName) in UE 4.26: comparison index + number. Only trusted after every chain of a map checked out.
uint32_t NameHash(const RawName& name) { return name.Comparison + name.Number; }

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
    std::vector<uint8_t> seen(static_cast<size_t>(count), 0);
    int32_t visited = 0;
    for (int32_t bucket = 0; bucket < size; ++bucket)
    {
        for (int32_t e = heads[static_cast<size_t>(bucket)]; e != -1; e = elements[static_cast<size_t>(e)].Next)
        {
            if (e < 0 || e >= count || seen[static_cast<size_t>(e)]) { return true; }
            const NameMapElement& element = elements[static_cast<size_t>(e)];
            if (element.Bucket != bucket || static_cast<int32_t>(NameHash(element.Key) & static_cast<uint32_t>(size - 1)) != bucket) { return true; }
            seen[static_cast<size_t>(e)] = 1;
            ++visited;
        }
    }
    if (visited != count) { return true; }
    out.Hash = hash;
    out.HashSize = size;
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
    const int32_t to = static_cast<int32_t>(NameHash(renamed) & static_cast<uint32_t>(map.HashSize - 1));
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
                SkelCompat::BoneTable keepBones;
                if (!Alive(keepSkeleton) || !ReadSkeletonBones(keepSkeleton, keepBones)) { continue; }
                const SkelCompat::MeshCheck keep = SkelCompat::CheckMeshAgainstSkeleton(meshBones, keepBones);
                result += keep.Compatible ? L" AnimBlueprints made for " + ShortName(keepSkeleton) + L" run on it too."
                                          : L" AnimBlueprints made for " + ShortName(keepSkeleton) + L" are REFUSED: " + keep.Problem;
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
                    std::to_wstring(plan->CurvesDropped.load()) + L" in " + std::to_wstring(plan->AssetsDroppingCurves.load()) + L" adopted asset(s)\n";
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
        text += L"  " + ObjectPath(view.Component) + L"\n    AnimClass " + (view.AnimClass ? PathOf(view.AnimClass) : L"none") +
                L", AnimBlueprint instance " + (view.AnimInstance ? L"running" : L"NONE (refused or not using an AnimBlueprint)") + L"\n";
    }
    text += L"\nAnimBlueprints re-initialised so far: " + std::to_wstring(State.Repaired) + L"\n";
    text += L"PostLoad hook: " + PostLoadStats() + L"\n";
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
        }
        State.NextPumpMs = GetTickCount64() + PumpIntervalMs;
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
void OnViewportTickPost(UGameViewportClient*, float)
{
    if (!State.Active.load(std::memory_order_relaxed)) { return; }
    if (!State.ViewportSafePoint.load(std::memory_order_relaxed))
    {
        if (GetCurrentThreadId() != State.GameThread.load(std::memory_order_relaxed)) { return; }
        State.ViewportSafePoint.store(true, std::memory_order_relaxed);
        Log.Line(L"Frame safe point available (after the world tick): late adoption runs there");
    }
    const bool waiting = State.WaitingCount.load(std::memory_order_relaxed) > 0;
    if ((!State.LatePassWanted.load(std::memory_order_relaxed) && !waiting) || State.Busy) { return; }
    if (GetCurrentThreadId() != State.GameThread.load(std::memory_order_relaxed)) { return; }
    BusyScope busy;
    try
    {
        CheckWaiting(true);
        if (State.LatePassWanted.load(std::memory_order_relaxed) && GetTickCount64() >= State.LatePassNotBefore) { LatePass(true); }
    }
    catch (...)
    {
        Fault(L"late adoption (frame safe point)");
    }
}

void OnProcessEventPost(UObject*, UFunction*, void*)
{
    if (!State.Active.load(std::memory_order_relaxed)) { return; }
    if (GetCurrentThreadId() != State.GameThread.load(std::memory_order_relaxed)) { return; }
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
        }
        else
        {
            line = L"Pair (mesh): meshes on " + pair.Receiving + L" are rebound to and play animations of";
            for (const auto& a : pair.Animation) { line += L"\n    " + a; }
            if (!pair.Meshes.empty()) { line += L"\n    (limited to " + std::to_wstring(pair.Meshes.size()) + L" mesh(es))"; }
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
    if (State.Config.Pairs.empty())
    {
        Log.Line(L"No JSON pairs. Pairs declared in AssetUserData (BP_SkelCompatUserData) on skeletons or meshes still apply.");
    }

    PinModule();
    State.Enabled.store(true, std::memory_order_release);
    Hook::RegisterLoadMapPostCallback(&OnLoadMapPost);
    Log.Line(L"Waiting for the first map load to finish setting up on the game thread");
    return true;
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
        State.OffSeqBlendOut = FieldOffset(sequenceBase, L"OverrideBehaviorActionBlendOutSequence", {L"ObjectProperty"}, 8);
    }
    if (State.AnimSequenceClass)
    {
        State.OffSeqRefPose = FieldOffset(State.AnimSequenceClass, L"RefPoseSeq", {L"ObjectProperty"}, 8);
        const int32_t curveSettings = FieldOffset(State.AnimSequenceClass, L"CurveCompressionSettings", {L"ObjectProperty"}, 8);
        const int32_t additive = FieldOffset(State.AnimSequenceClass, L"AdditiveAnimType", {L"ByteProperty", L"EnumProperty"}, 1);
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
    // Registered here, on the game thread and outside any ProcessEvent or viewport tick, so UE4SS's callback
    // lists are never extended while the game walks them.
    Hook::RegisterProcessEventPostCallback(&OnProcessEventPost);
    if (adoptionWanted) { Hook::RegisterGameViewportClientTickPostCallback(&OnViewportTickPost); }
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

    ~RebirthSkelCompatMod() override
    {
        // Hooks cannot be removed in this UE4SS build; the pinned module keeps them valid.
        // Rebinds already made stay in place until the meshes are unloaded.
    }
};
} // namespace

extern "C" __declspec(dllexport) RC::CppUserModBase* start_mod() { return new RebirthSkelCompatMod(); }
extern "C" __declspec(dllexport) void uninstall_mod(RC::CppUserModBase* mod) { delete mod; }
