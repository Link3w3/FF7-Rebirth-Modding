// Off-target unit tests for SkelCompatCore.hpp (g++ -std=c++20).
#include "../src/SkelCompatCore.hpp"

#include <cstdio>
#include <cstdlib>
#include <string>

using namespace SkelCompat;

static int Failures = 0;
#define CHECK(cond)                                                                 \
    do                                                                              \
    {                                                                               \
        if (!(cond)) { std::printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond); ++Failures; } \
    } while (0)

static BoneTable Table(std::initializer_list<std::pair<const wchar_t*, int>> bones, int raw = -1)
{
    BoneTable t;
    for (const auto& [n, p] : bones) { t.Names.emplace_back(n); t.Parents.push_back(p); }
    t.RawCount = raw;
    return t;
}

static void TestJson()
{
    Json j;
    std::string e;
    CHECK(ParseJson("\xEF\xBB\xBF{\"a\":[1,2.5e1,-3],\"b\":\"x\\u00e9\\ud83d\\ude00\\n\",\"c\":true,\"d\":null}", j, e));
    CHECK(j.Find("a") && j.Find("a")->array.size() == 3 && j.Find("a")->array[1].number == 25.0);
    CHECK(j.Find("b") && j.Find("b")->string == "x\xC3\xA9\xF0\x9F\x98\x80\n");
    CHECK(j.Find("c") && j.Find("c")->boolean);
    CHECK(j.Find("d") && j.Find("d")->type == Json::Type::Null);
    CHECK(!ParseJson("{\"a\":1,}", j, e));
    CHECK(!ParseJson("{\"a\" 1}", j, e));
    CHECK(!ParseJson("[1,2", j, e));
    CHECK(!ParseJson("\"bad\\q\"", j, e));
    CHECK(!ParseJson("{} x", j, e));
    CHECK(!ParseJson("\"\\ud83d\"", j, e));
    std::string deep(100, '[');
    CHECK(!ParseJson(deep, j, e));
    CHECK(ParseJson("  [ ]  ", j, e) && j.type == Json::Type::Array && j.array.empty());
}

static void TestStrings()
{
    const std::wstring w = Widen("caf\xC3\xA9 \xF0\x9F\x98\x80");
    CHECK(Narrow(w) == "caf\xC3\xA9 \xF0\x9F\x98\x80");
    CHECK(NameEquals(L"C_Hip_Jnt", L"c_hip_jnt"));
    CHECK(!NameEquals(L"C_Hip", L"C_Hip2"));
}

static void TestPaths()
{
    CHECK(NormalizeObjectPath(L"/Game/A/B") == L"/Game/A/B.B");
    CHECK(NormalizeObjectPath(L"  /Game/A/B.B ") == L"/Game/A/B.B");
    CHECK(NormalizeObjectPath(L"Skeleton'/Game/A/B.B'") == L"/Game/A/B.B");
    CHECK(NormalizeObjectPath(L"Skeleton /Game/A/B.B") == L"/Game/A/B.B");
    CHECK(NormalizeObjectPath(L"\\Game\\A\\B") == L"/Game/A/B.B");
    CHECK(NormalizeObjectPath(L"/FirstClassSora/Char/Sora_Skel/") == L"/FirstClassSora/Char/Sora_Skel.Sora_Skel");
    CHECK(NormalizeObjectPath(L"Game/A/B").empty());
    CHECK(NormalizeObjectPath(L"").empty());
    CHECK(PathEquals(L"/Game/A/B.B", L"/game/a/b.b"));
}

static void TestConfig()
{
    Config cfg;
    const char* fileA = R"({
      "schema": "RebirthSkelCompat/1",
      "pairs": [
        { "receiving_skeleton": "/Game/Mods/Sora/SK_Sora_Skeleton",
          "animation_skeletons": ["/Game/Character/Player/PC0000/PC0000_Skeleton", "/Game/Mods/Sora/SK_Sora_Skeleton"] },
        { "receiving_skeleton": "/Game/Mods/Off/Skel", "animation_skeleton": "/Game/X/Y", "enabled": false },
        { "receiving_skeleton": 5 },
        { "receiving_skeleton": "/Game/Mods/Riku/Skel", "animation_skeleton": "/Game/Mods/Sora/SK_Sora_Skeleton" },
        { "receiving_skeleton": "/Game/Mods/Kairi/Skel", "animation_skeleton": "/Game/Character/Player/PC0002/PC0002_Skeleton",
          "receiving_meshes": ["/Game/Mods/Kairi/SK_Kairi"], "repair_live_components": false, "fix_hierarchy": false }
      ]
    })";
    CHECK(AppendConfig(fileA, L"a.json", cfg));
    CHECK(cfg.FindForSkeleton(L"/Game/Mods/Sora/SK_Sora_Skeleton.SK_Sora_Skeleton") != nullptr); // parsing keeps every entry
    FinishConfig(cfg, [](const std::wstring&) { return true; });
    // Sora takes Cloud's animations and hands its own to Riku: a chain, so the three share on one hub. Cloud's skeleton
    // is the hub (its animations are wanted and it wants none); Sora and Riku are rebound to it.
    const std::wstring cloudSkel = L"/Game/Character/Player/PC0000/PC0000_Skeleton.PC0000_Skeleton";
    const Pair* hub = cfg.FindForSkeleton(cloudSkel);
    CHECK(hub && hub->Use == Method::Animations && hub->FamilyHub == cloudSkel && hub->Animation.size() == 2 &&
          hub->Animation[0] == L"/Game/Mods/Sora/SK_Sora_Skeleton.SK_Sora_Skeleton" && hub->Animation[1] == L"/Game/Mods/Riku/Skel.Skel");
    const Pair* sora = cfg.FindForSkeleton(L"/Game/Mods/Sora/SK_Sora_Skeleton.SK_Sora_Skeleton");
    CHECK(sora && sora->Use == Method::Mesh && sora->Animation.size() == 1 && sora->Animation[0] == cloudSkel);
    const Pair* riku = cfg.FindForSkeleton(L"/game/mods/riku/skel.skel");
    CHECK(riku && riku->Use == Method::Mesh && riku->Animation.size() == 1 && riku->Animation[0] == cloudSkel);
    CHECK(riku && riku->FixHierarchy && riku->CarrySockets);
    CHECK(cfg.FindForSkeleton(L"/Game/Mods/Off/Skel.Skel") == nullptr);
    const Pair* kairi = cfg.FindForSkeleton(L"/Game/Mods/Kairi/Skel.Skel");
    CHECK(kairi && !kairi->RepairLiveComponents && kairi->Meshes.size() == 1);
    CHECK(kairi && MeshAllowed(*kairi, L"/Game/Mods/Kairi/SK_Kairi.SK_Kairi") && !MeshAllowed(*kairi, L"/Game/Mods/Kairi/Other.Other"));
    CHECK(cfg.IsAnimationSkeleton(L"/Game/Character/Player/PC0002/PC0002_Skeleton.PC0002_Skeleton"));
    CHECK(!cfg.Messages.empty());

    // second file merges into Kairi and widens its mesh filter
    const char* fileB = R"({"schema":"RebirthSkelCompat/1","pairs":[
        {"receiving_skeleton":"/Game/Mods/Kairi/Skel","animation_skeletons":["/Game/Character/Player/PC0003/PC0003_Skeleton"]}]})";
    CHECK(AppendConfig(fileB, L"b.json", cfg));
    kairi = cfg.FindForSkeleton(L"/Game/Mods/Kairi/Skel.Skel");
    CHECK(kairi && kairi->Animation.size() == 2 && kairi->Meshes.empty());
    CHECK(kairi && !kairi->FixHierarchy); // any entry switching it off wins

    Config bad;
    CHECK(!AppendConfig("{\"pairs\":[]}", L"c.json", bad));
    CHECK(!AppendConfig("not json", L"d.json", bad));
    CHECK(bad.Pairs.empty() && bad.Messages.size() == 2);
}

static void TestHierarchy()
{
    // Rebirth-like skeleton
    const BoneTable skel = Table({{L"Root", -1}, {L"C_Hip", 0}, {L"C_Spine", 1}, {L"C_Neck", 2}, {L"C_Head", 3},
                                  {L"L_Thigh", 1}, {L"R_Thigh", 1}, {L"VB_FootTarget", 0}},
                                 7);
    // Same chain plus mesh-only hair/hood bones hanging under shared bones -> compatible
    const BoneTable good = Table({{L"root", -1}, {L"C_Hip", 0}, {L"C_Spine", 1}, {L"C_Neck", 2}, {L"C_Head", 3},
                                  {L"Hair_01", 4}, {L"Hair_02", 5}, {L"L_Thigh", 1}});
    MeshCheck r = CheckMeshAgainstSkeleton(good, skel);
    CHECK(r.Compatible);
    CHECK(r.Matched == 6 && r.MeshOnly == 2 && r.SkeletonOnly == 1);

    // KH3-style extra bone inserted inside a shared chain -> refused, names the bone
    const BoneTable inserted = Table({{L"Root", -1}, {L"C_Hip", 0}, {L"C_Spine", 1}, {L"C_Spine2", 2}, {L"C_Neck", 3}, {L"C_Head", 4}});
    r = CheckMeshAgainstSkeleton(inserted, skel);
    CHECK(!r.Compatible);
    CHECK(r.Problem.find(L"C_Spine2") != std::wstring::npos || r.Problem.find(L"C_Neck") != std::wstring::npos);

    // Root renamed -> refused with a root message
    const BoneTable rootRenamed = Table({{L"KH_Root", -1}, {L"C_Hip", 0}, {L"C_Spine", 1}});
    r = CheckMeshAgainstSkeleton(rootRenamed, skel);
    CHECK(!r.Compatible && r.Problem.find(L"root") != std::wstring::npos);

    // Nothing in common
    const BoneTable alien = Table({{L"bone000", -1}, {L"bone001", 0}});
    r = CheckMeshAgainstSkeleton(alien, skel);
    CHECK(!r.Compatible && r.Matched == 0);

    // Invalid tables are rejected, never indexed
    BoneTable broken = Table({{L"Root", -1}, {L"A", 5}});
    r = CheckMeshAgainstSkeleton(broken, skel);
    CHECK(!r.Compatible && r.Problem == L"bone table unreadable");

    // Virtual bone on the skeleton is matchable by name like the engine's FindBoneIndex
    const BoneTable withVb = Table({{L"Root", -1}, {L"VB_FootTarget", 0}});
    r = CheckMeshAgainstSkeleton(withVb, skel);
    CHECK(r.Compatible && r.Matched == 2);
}

static void TestRenamePlan()
{
    // Cloud-like skeleton (raw bones + one virtual bone)
    const BoneTable cloud = Table({{L"Trans", -1}, {L"C_Hip_a", 0}, {L"C_Spine_a", 1}, {L"C_SpineBelt_Spo", 1}, {L"C_SpineBeltA_Spo", 3},
                                   {L"C_Spine_d", 2}, {L"C_Neck_a", 5}, {L"C_Head_a", 6}, {L"C_HairBase_a", 7}, {L"L_HairC_a_Phy", 8},
                                   {L"L_HairC_b_Phy", 9}, {L"L_Thigh_a", 1}, {L"VB Foot", 11}},
                                  12);
    // Sephiroth-like mesh: the belt bone hangs under the spine, the hair chain has an extra bone
    const BoneTable seph = Table({{L"Trans", -1}, {L"C_Hip_a", 0}, {L"C_Spine_a", 1}, {L"C_SpineBeltA_Spo", 2}, {L"C_SpineBeltA_End", 3},
                                  {L"C_Spine_d", 2}, {L"C_Neck_a", 5}, {L"C_Head_a", 6}, {L"C_HairBase_a", 7}, {L"L_HairC_Spo", 8},
                                  {L"L_HairC_a_Phy", 9}, {L"L_HairC_b_Phy", 10}, {L"l_thigh_A", 1}, {L"R_Coat_a", 1}});
    CHECK(!CheckMeshAgainstSkeleton(seph, cloud).Compatible);
    const RenamePlan plan = PlanConflictRenames(seph, cloud);
    CHECK(plan.Possible);
    CHECK((plan.Bones == std::vector<int32_t>{3, 10, 11}));
    const BoneTable fixed = ApplyRenamePlan(seph, plan);
    const MeshCheck after = CheckMeshAgainstSkeleton(fixed, cloud);
    CHECK(after.Compatible);
    CHECK(after.Matched == 8 && after.MeshOnly == 6);
    CHECK(fixed.Names[10] == L"L_HairC_a_Phy_900010");
    CHECK(fixed.Find(L"L_HairC_a_Phy") < 0 && fixed.Find(L"l_haircb_phy") < 0 && fixed.Find(L"c_spine_a") == 2);
    CHECK(PlanConflictRenames(fixed, cloud).Bones.empty()); // idempotent

    // A family member also runs its own AnimBlueprint: its own skeleton has every mesh bone, so the bone left under a
    // renamed hair bone (L_HairC_b_Phy under L_HairC_a_Phy) fails there. The closed plan renames the whole subtree.
    const BoneTable sephSkeleton = seph; // the member's own skeleton: same bones as its mesh
    CHECK(!CheckMeshAgainstSkeleton(fixed, sephSkeleton).Compatible || plan.Bones.size() == CloseRenamePlan(seph, plan).Bones.size());
    const RenamePlan closed = CloseRenamePlan(seph, plan);
    CHECK((closed.Bones == std::vector<int32_t>{3, 4, 10, 11}));
    const BoneTable both = ApplyRenamePlan(seph, closed);
    CHECK(CheckMeshAgainstSkeleton(both, cloud).Compatible && CheckMeshAgainstSkeleton(both, sephSkeleton).Compatible);
    CHECK(CloseRenamePlan(seph, RenamePlan{}).Bones.empty());

    // Nothing to do on a compatible mesh; impossible when the roots differ
    CHECK(PlanConflictRenames(Table({{L"Trans", -1}, {L"C_Hip_a", 0}}), cloud).Bones.empty());
    CHECK(!PlanConflictRenames(Table({{L"Root", -1}, {L"C_Hip_a", 0}}), cloud).Possible);

    // A bone inserted into the core chain: everything above it leaves the shared set, the rest animates
    const BoneTable inserted = Table({{L"Trans", -1}, {L"C_Hip_a", 0}, {L"C_Spine_a", 1}, {L"C_Spine_b", 2}, {L"C_Spine_d", 3},
                                      {L"C_Neck_a", 4}, {L"C_Head_a", 5}, {L"L_Thigh_a", 1}});
    const RenamePlan p2 = PlanConflictRenames(inserted, cloud);
    CHECK((p2.Bones == std::vector<int32_t>{4, 5, 6}));
    CHECK(CheckMeshAgainstSkeleton(ApplyRenamePlan(inserted, p2), cloud).Compatible);

    // A mesh bone named like a skeleton virtual bone follows the same rule
    const BoneTable vbMesh = Table({{L"Trans", -1}, {L"C_Hip_a", 0}, {L"VB Foot", 1}});
    const RenamePlan p3 = PlanConflictRenames(vbMesh, cloud);
    CHECK((p3.Bones == std::vector<int32_t>{2}));
    CHECK(CheckMeshAgainstSkeleton(ApplyRenamePlan(vbMesh, p3), cloud).Compatible);

    // Randomised: on any tree the plan makes the engine's test pass and never renames a bone that already passes
    uint32_t seed = 12345;
    auto next = [&]() { seed = seed * 1664525u + 1013904223u; return seed >> 8; };
    for (int round = 0; round < 300; ++round)
    {
        BoneTable skel, mesh;
        const int sn = 2 + static_cast<int>(next() % 40);
        for (int i = 0; i < sn; ++i)
        {
            skel.Names.push_back(L"B" + std::to_wstring(i));
            skel.Parents.push_back(i == 0 ? -1 : static_cast<int32_t>(next() % static_cast<uint32_t>(i)));
        }
        const int mn = 2 + static_cast<int>(next() % 40);
        for (int i = 0; i < mn; ++i)
        {
            const uint32_t pick = next() % 60u;
            mesh.Names.push_back(i == 0 ? L"B0" : (L"B" + std::to_wstring(pick)));
            mesh.Parents.push_back(i == 0 ? -1 : static_cast<int32_t>(next() % static_cast<uint32_t>(i)));
        }
        // mesh names must be unique, like a real reference skeleton
        for (int i = 1; i < mn; ++i)
        {
            for (int j = 0; j < i; ++j)
            {
                if (mesh.Names[static_cast<size_t>(j)] == mesh.Names[static_cast<size_t>(i)]) { mesh.Names[static_cast<size_t>(i)] = L"M" + std::to_wstring(i); break; }
            }
        }
        const RenamePlan p = PlanConflictRenames(mesh, skel);
        CHECK(p.Possible);
        const BoneTable result = ApplyRenamePlan(mesh, p);
        const MeshCheck check = CheckMeshAgainstSkeleton(result, skel);
        CHECK(check.Compatible);
        // The closed plan passes against the target and against the mesh's own skeleton (which has all its bones).
        const BoneTable closedResult = ApplyRenamePlan(mesh, CloseRenamePlan(mesh, p));
        CHECK(CheckMeshAgainstSkeleton(closedResult, skel).Compatible);
        CHECK(CheckMeshAgainstSkeleton(closedResult, mesh).Compatible);
        // Several skeletons at once (an outfit made for another skeleton follows its animations to this one).
        BoneTable other;
        const int on = 2 + static_cast<int>(next() % 40);
        for (int i = 0; i < on; ++i)
        {
            std::wstring n = i == 0 ? L"B0" : L"B" + std::to_wstring(next() % 60u);
            for (const auto& e : other.Names) { if (e == n) { n = L"Y" + std::to_wstring(i); break; } }
            other.Names.push_back(n);
            other.Parents.push_back(i == 0 ? -1 : static_cast<int32_t>(next() % static_cast<uint32_t>(i)));
        }
        const BoneTable forAll = ApplyRenamePlan(mesh, PlanConflictRenamesFor(mesh, skel, {&other, &mesh}));
        CHECK(CheckMeshAgainstSkeleton(forAll, skel).Compatible);
        CHECK(CheckMeshAgainstSkeleton(forAll, mesh).Compatible);
        CHECK(CheckMeshAgainstSkeleton(forAll, other).Compatible); // same root bone, so it can always be satisfied
        for (size_t k = 0; k < p.Bones.size(); ++k)
        {
            // minimal: leaving out any one rename makes the engine refuse the mesh again
            RenamePlan less = p;
            less.Bones.erase(less.Bones.begin() + static_cast<std::ptrdiff_t>(k));
            CHECK(!CheckMeshAgainstSkeleton(ApplyRenamePlan(mesh, less), skel).Compatible);
        }
        if (!check.Compatible || Failures) { break; }
    }
}

static void TestAdoption()
{
    // Track remap: Cloud-like source, Sephiroth-like target
    const BoneTable cloud = Table({{L"Trans", -1}, {L"C_Hip_a", 0}, {L"C_Spine_a", 1}, {L"C_SpineBelt_Spo", 1}, {L"C_SpineBeltA_Spo", 3},
                                   {L"C_Spine_d", 2}, {L"C_Neck_a", 5}, {L"C_Head_a", 6}, {L"C_HairBase_a", 7}, {L"L_HairC_a_Phy", 8},
                                   {L"L_HairC_b_Phy", 9}, {L"L_Thigh_a", 1}, {L"Cloud_Only", 7}, {L"VB Foot", 11}},
                                  13);
    const BoneTable seph = Table({{L"Trans", -1}, {L"C_Hip_a", 0}, {L"C_Spine_a", 1}, {L"C_SpineBeltA_Spo", 2}, {L"C_Spine_d", 2},
                                  {L"C_Neck_a", 4}, {L"C_Head_a", 5}, {L"C_HairBase_a", 6}, {L"L_HairC_Spo", 7}, {L"L_HairC_a_Phy", 8},
                                  {L"L_HairC_b_Phy", 9}, {L"l_thigh_A", 1}, {L"Seph_Coat", 1}, {L"VB Foot", 11}},
                                 13);
    const std::vector<int32_t> map = BuildTrackRemap(cloud, seph);
    CHECK(map.size() == cloud.Names.size());
    CHECK(map[0] == 0 && map[1] == 1 && map[2] == 2 && map[5] == 4 && map[6] == 5 && map[7] == 6 && map[8] == 7 && map[11] == 11);
    CHECK(map[3] == -1);  // C_SpineBelt_Spo missing on the target
    CHECK(map[4] == -1);  // C_SpineBeltA_Spo: different parent
    CHECK(map[9] == -1 && map[10] == -1); // hair chain has an extra bone on the target
    CHECK(map[12] == -1); // source-only bone
    CHECK(map[13] == 13); // virtual bone with a matching source bone
    // Every mapping keeps names and parent links
    for (size_t a = 0; a < map.size(); ++a)
    {
        if (map[a] < 0) { continue; }
        CHECK(NameEquals(cloud.Names[a], seph.Names[static_cast<size_t>(map[a])]));
        if (a > 0) { CHECK(map[static_cast<size_t>(cloud.Parents[a])] == seph.Parents[static_cast<size_t>(map[a])]); }
    }
    CHECK(BuildTrackRemap(cloud, Table({{L"Root", -1}, {L"C_Hip_a", 0}})).empty()); // roots differ

    // Randomised: mappings are name- and parent-consistent and maximal
    uint32_t seed = 777;
    auto next = [&]() { seed = seed * 1664525u + 1013904223u; return seed >> 8; };
    for (int round = 0; round < 300; ++round)
    {
        BoneTable a, b;
        const int an = 2 + static_cast<int>(next() % 40), bn = 2 + static_cast<int>(next() % 40);
        for (int i = 0; i < an; ++i) { a.Names.push_back(L"B" + std::to_wstring(i)); a.Parents.push_back(i ? static_cast<int32_t>(next() % static_cast<uint32_t>(i)) : -1); }
        for (int i = 0; i < bn; ++i)
        {
            std::wstring n = i ? L"B" + std::to_wstring(next() % 50u) : L"B0";
            for (const auto& e : b.Names) { if (e == n) { n = L"X" + std::to_wstring(i); break; } }
            b.Names.push_back(n);
            b.Parents.push_back(i ? static_cast<int32_t>(next() % static_cast<uint32_t>(i)) : -1);
        }
        const std::vector<int32_t> m = BuildTrackRemap(a, b);
        CHECK(m.size() == a.Names.size() && m[0] == 0);
        std::vector<int32_t> back(b.Names.size(), -1);
        for (size_t i = 0; i < m.size(); ++i)
        {
            if (m[i] < 0) { continue; }
            CHECK(back[static_cast<size_t>(m[i])] == -1);
            back[static_cast<size_t>(m[i])] = static_cast<int32_t>(i);
            CHECK(a.Names[i] == b.Names[static_cast<size_t>(m[i])]);
            if (i > 0) { CHECK(m[static_cast<size_t>(a.Parents[i])] == b.Parents[static_cast<size_t>(m[i])]); }
        }
        for (size_t r = 1; r < b.Names.size(); ++r)
        {
            // maximal: an unmapped target bone has no same-named source bone whose parent maps to its parent
            if (back[r] >= 0) { continue; }
            const int32_t s = a.Find(b.Names[r]);
            if (s > 0) { CHECK(!(m[static_cast<size_t>(a.Parents[static_cast<size_t>(s)])] == b.Parents[r] && b.Parents[r] >= 0)); }
        }
        if (Failures) { break; }
    }

    // Path prefixes
    CHECK(NormalizePathPrefix(L"/Game/Motion/Player/PC0000_Cloud/Neutral20.Neutral20") == L"/Game/Motion/Player/PC0000_Cloud/Neutral20");
    CHECK(NormalizePathPrefix(L" \\Game\\Motion\\Player\\PC0000_Cloud\\ ") == L"/Game/Motion/Player/PC0000_Cloud");
    CHECK(NormalizePathPrefix(L"Game/X").empty() && NormalizePathPrefix(L"/").empty());
    const std::vector<std::wstring> prefixes{L"/Game/Motion/Player/PC0000_Cloud/Neutral20"};
    CHECK(PathUnder(prefixes, L"/Game/Motion/Player/PC0000_Cloud/Neutral20/N_SwimIdle01_1.N_SwimIdle01_1"));
    CHECK(PathUnder(prefixes, L"/game/motion/player/pc0000_cloud/neutral20.Neutral20"));
    CHECK(!PathUnder(prefixes, L"/Game/Motion/Player/PC0000_Cloud/Neutral200/N_X.N_X"));
    CHECK(!PathUnder(prefixes, L"/Game/Motion/Player/PC0000_Cloud/Battle00/B_X.B_X"));
    CHECK(PathUnder({}, L"/Game/Anything.Anything"));

    // Config: method and adopt_paths
    Config cfg;
    CHECK(AppendConfig(R"({"schema":"RebirthSkelCompat/1","pairs":[
        {"receiving_skeleton":"/Game/S/Seph_Skel","animation_skeleton":"/Game/C/Cloud_Skel","adopt_paths":["/Game/Motion/C/Neutral20.Neutral20"]},
        {"receiving_skeleton":"/Game/M/Custom_Skel","animation_skeleton":"/Game/C/Other_Skel","method":"mesh"},
        {"receiving_skeleton":"/Game/B/Bad","animation_skeleton":"/Game/C/Third","method":"sideways"}]})", L"m.json", cfg));
    const Pair* seph2 = cfg.FindForSkeleton(L"/Game/S/Seph_Skel.Seph_Skel");
    CHECK(seph2 && seph2->Use == Method::Animations && seph2->AdoptPaths.size() == 1 && seph2->AdoptPaths[0] == L"/Game/Motion/C/Neutral20");
    const Pair* custom = cfg.FindForSkeleton(L"/Game/M/Custom_Skel.Custom_Skel");
    CHECK(custom && custom->Use == Method::Mesh);
    const Pair* bad = cfg.FindForSkeleton(L"/Game/B/Bad.Bad");
    CHECK(bad && bad->Use == Method::Animations);
    CHECK(AppendConfig(R"({"schema":"RebirthSkelCompat/1","pairs":[
        {"receiving_skeleton":"/Game/S/Seph_Skel","animation_skeleton":"/Game/C/Cloud_Skel"}]})", L"n.json", cfg));
    seph2 = cfg.FindForSkeleton(L"/Game/S/Seph_Skel.Seph_Skel");
    CHECK(seph2 && seph2->AdoptPaths.empty()); // an entry without adopt_paths widens to everything
}

static void TestRequiredPaks()
{
    CHECK(PakStem(L"SephirothOverCloud_P.pak") == L"SephirothOverCloud_P");
    CHECK(PakStem(L"~mods\\Seph\\SephirothOverCloud_P.utoc") == L"SephirothOverCloud_P");
    CHECK(PakStem(L"  Dresscode  ") == L"Dresscode");
    CHECK(PakStem(L"My.Mod.v2") == L"My.Mod.v2");
    CHECK(PakStem(L"").empty());

    Config cfg;
    const char* fileA = R"({"schema":"RebirthSkelCompat/1","pairs":[
        {"receiving_skeleton":"/Game/S/Seph_Skel","animation_skeletons":["/Game/C/Cloud_Skel"],
         "requires_paks":["SephirothOverCloud_P.pak"]},
        {"receiving_skeleton":"/Game/T/Tifa_Skel","animation_skeletons":["/Game/B/Barret_Skel"],"requires_pak":"TifaOverBarret_P"},
        {"receiving_skeleton":"/Game/A/Aerith_Skel","animation_skeletons":["/Game/Y/Yuffie_Skel"]},
        {"receiving_skeleton":"/Game/R/Red_Skel","animation_skeletons":["/Game/V/Vin_Skel"],"requires_paks":[3, ""]}]})";
    CHECK(AppendConfig(fileA, L"a.json", cfg));
    const Pair* seph = cfg.FindForSkeleton(L"/Game/S/Seph_Skel.Seph_Skel");
    CHECK(seph && seph->RequiresPaks.size() == 1 && seph->RequiresPaks[0] == L"SephirothOverCloud_P");
    const Pair* red = cfg.FindForSkeleton(L"/Game/R/Red_Skel.Red_Skel");
    CHECK(red && red->RequiresPaks.empty()); // unusable entries are ignored (with a message)
    // A second file for the same receiving skeleton adds its requirement.
    const char* fileB = R"({"schema":"RebirthSkelCompat/1","pairs":[
        {"receiving_skeleton":"/Game/S/Seph_Skel","animation_skeletons":["/Game/C/Cloud_Skel"],"requires_paks":"sephirothovercloud_p"},
        {"receiving_skeleton":"/Game/S/Seph_Skel","animation_skeletons":["/Game/C/Cloud_Skel"],"requires_paks":["Extra_P"]}]})";
    CHECK(AppendConfig(fileB, L"b.json", cfg));
    seph = cfg.FindForSkeleton(L"/Game/S/Seph_Skel.Seph_Skel");
    CHECK(seph && seph->RequiresPaks.size() == 2);

    const auto installed = [](const std::wstring& name) { return NameEquals(name, L"SephirothOverCloud_P") || NameEquals(name, L"Extra_P"); };
    const auto notes = DropPairsMissingPaks(cfg, installed);
    CHECK(notes.size() == 1); // Tifa's pak is missing
    CHECK(cfg.FindForSkeleton(L"/Game/T/Tifa_Skel.Tifa_Skel") == nullptr);
    CHECK(cfg.FindForSkeleton(L"/Game/S/Seph_Skel.Seph_Skel") != nullptr);
    CHECK(cfg.FindForSkeleton(L"/Game/A/Aerith_Skel.Aerith_Skel") != nullptr); // no requirement: always on
    const auto none = [](const std::wstring&) { return false; };
    const auto notes2 = DropPairsMissingPaks(cfg, none);
    CHECK(notes2.size() == 1 && cfg.FindForSkeleton(L"/Game/S/Seph_Skel.Seph_Skel") == nullptr);
}

static const Pair* MeshPairTo(const Config& cfg, const wchar_t* receiving, const std::wstring& target)
{
    const Pair* p = cfg.FindForSkeleton(receiving);
    return (p && p->Use == Method::Mesh && p->Animation.size() == 1 && PathEquals(p->Animation[0], target)) ? p : nullptr;
}

static void TestSharedAnimationSkeleton()
{
    // Three swap pairs want Cloud's animations: instead of the first one taking all of them, everything gathers on
    // Cloud's skeleton (wanted by the most pairs). Vincent also wants Barret's, so Barret joins too.
    const char* seph = R"({"schema":"RebirthSkelCompat/1","pairs":[
        {"receiving_skeleton":"/Game/S/Seph_Skel","animation_skeletons":["/Game/C/Cloud_Skel"],"requires_paks":["SephirothOverCloud_P"]}]})";
    const char* later = R"({"schema":"RebirthSkelCompat/1","pairs":[
        {"receiving_skeleton":"/Game/V/Vin_Skel","animation_skeletons":["/Game/C/Cloud_Skel","/Game/B/Barret_Skel"]},
        {"receiving_skeleton":"/Game/R/Red_Skel","animation_skeletons":["/Game/C/Cloud_Skel"]}]})";
    const auto sephInstalled = [](const std::wstring& name) { return NameEquals(name, L"SephirothOverCloud_P"); };
    const std::wstring cloud = L"/Game/C/Cloud_Skel.Cloud_Skel";
    {
        Config cfg;
        CHECK(AppendConfig(seph, L"a.json", cfg) && AppendConfig(later, L"b.json", cfg));
        CHECK(cfg.Messages.empty()); // parsing alone says nothing about other pairs
        FinishConfig(cfg, sephInstalled);
        const Pair* hub = cfg.FindForSkeleton(cloud);
        CHECK(hub && hub->Use == Method::Animations && hub->FamilyHub == cloud &&
              (hub->Animation == std::vector<std::wstring>{L"/Game/S/Seph_Skel.Seph_Skel", L"/Game/V/Vin_Skel.Vin_Skel",
                                                            L"/Game/B/Barret_Skel.Barret_Skel", L"/Game/R/Red_Skel.Red_Skel"}));
        CHECK(MeshPairTo(cfg, L"/Game/S/Seph_Skel.Seph_Skel", cloud) && MeshPairTo(cfg, L"/Game/V/Vin_Skel.Vin_Skel", cloud));
        CHECK(MeshPairTo(cfg, L"/Game/B/Barret_Skel.Barret_Skel", cloud) && MeshPairTo(cfg, L"/Game/R/Red_Skel.Red_Skel", cloud));
        CHECK(cfg.Pairs.size() == 5 && cfg.Messages.size() == 1);
        CHECK(FollowAdoption(cfg, L"/Game/B/Barret_Skel.Barret_Skel") == cloud);
    }
    {
        // Without the Sephiroth swap pak that pair is off; Vincent and Red XIII still share Cloud's animations.
        Config cfg;
        CHECK(AppendConfig(seph, L"a.json", cfg) && AppendConfig(later, L"b.json", cfg));
        FinishConfig(cfg, [](const std::wstring&) { return false; });
        CHECK(cfg.FindForSkeleton(L"/Game/S/Seph_Skel.Seph_Skel") == nullptr);
        const Pair* hub = cfg.FindForSkeleton(cloud);
        CHECK(hub && hub->Animation.size() == 3);
        CHECK(MeshPairTo(cfg, L"/Game/V/Vin_Skel.Vin_Skel", cloud) && MeshPairTo(cfg, L"/Game/R/Red_Skel.Red_Skel", cloud));
        CHECK(cfg.Messages.size() == 2); // the missing pak, the family
    }
    {
        // adopt_paths on the first pair shares the skeleton; mesh pairs never take animations away.
        Config cfg;
        CHECK(AppendConfig(R"({"schema":"RebirthSkelCompat/1","pairs":[
            {"receiving_skeleton":"/Game/S/Seph_Skel","animation_skeleton":"/Game/C/Cloud_Skel","adopt_paths":["/Game/Motion/C/Neutral20"]},
            {"receiving_skeleton":"/Game/V/Vin_Skel","animation_skeleton":"/Game/C/Cloud_Skel"},
            {"receiving_skeleton":"/Game/M/Mesh_Skel","animation_skeleton":"/Game/C/Cloud_Skel","method":"mesh"}]})", L"c.json", cfg));
        FinishConfig(cfg, [](const std::wstring&) { return true; });
        CHECK(cfg.Pairs.size() == 3 && cfg.Messages.empty());
    }
    {
        // A chain broken by a missing pak is no chain.
        Config cfg;
        CHECK(AppendConfig(R"({"schema":"RebirthSkelCompat/1","pairs":[
            {"receiving_skeleton":"/Game/X/X_Skel","animation_skeleton":"/Game/Y/Y_Skel","requires_paks":"Missing_P"},
            {"receiving_skeleton":"/Game/Y/Y_Skel","animation_skeleton":"/Game/Z/Z_Skel"}]})", L"d.json", cfg));
        FinishConfig(cfg, [](const std::wstring&) { return false; });
        CHECK(cfg.Pairs.size() == 1 && cfg.FindForSkeleton(L"/Game/Y/Y_Skel.Y_Skel") != nullptr);
    }
}

static void TestMeshFollowsAdoption()
{
    // Sephiroth plays Cloud's animations while the swap pak is in; a Vincent outfit is set up for Cloud.
    const char* file = R"({"schema":"RebirthSkelCompat/1","pairs":[
        {"receiving_skeleton":"/Game/S/Seph_Skel","animation_skeletons":["/Game/C/Cloud_Skel"],"method":"animations","requires_paks":["SephirothOverCloud_P"]},
        {"receiving_skeleton":"/Game/V/Vin_Skel","animation_skeletons":["/Game/C/Cloud_Skel","/Game/T/Tifa_Skel"],"method":"mesh"}]})";
    const auto sephInstalled = [](const std::wstring& name) { return NameEquals(name, L"SephirothOverCloud_P"); };
    {
        Config cfg;
        CHECK(AppendConfig(file, L"a.json", cfg));
        FinishConfig(cfg, sephInstalled);
        const Pair* vin = cfg.FindForSkeleton(L"/Game/V/Vin_Skel.Vin_Skel");
        // Cloud's animations belong to Sephiroth's skeleton now, so the meshes go there; Tifa's skeleton stays.
        CHECK(vin && vin->Animation.size() == 2 && vin->Animation[0] == L"/Game/S/Seph_Skel.Seph_Skel" &&
              vin->Animation[1] == L"/Game/T/Tifa_Skel.Tifa_Skel");
        CHECK(cfg.Messages.size() == 1);
        CHECK(FollowAdoption(cfg, L"/Game/C/Cloud_Skel.Cloud_Skel") == L"/Game/S/Seph_Skel.Seph_Skel");
    }
    {
        // Without the swap pak Cloud keeps his animations and the outfit stays on Cloud's skeleton.
        Config cfg;
        CHECK(AppendConfig(file, L"a.json", cfg));
        FinishConfig(cfg, [](const std::wstring&) { return false; });
        const Pair* vin = cfg.FindForSkeleton(L"/Game/V/Vin_Skel.Vin_Skel");
        CHECK(vin && vin->Animation.size() == 2 && vin->Animation[0] == L"/Game/C/Cloud_Skel.Cloud_Skel");
    }
    {
        // Only some of Cloud's animations moved (adopt_paths): the meshes stay where most of them are.
        Config cfg;
        CHECK(AppendConfig(R"({"schema":"RebirthSkelCompat/1","pairs":[
            {"receiving_skeleton":"/Game/S/Seph_Skel","animation_skeleton":"/Game/C/Cloud_Skel","adopt_paths":"/Game/Motion/C/Neutral20"},
            {"receiving_skeleton":"/Game/V/Vin_Skel","animation_skeleton":"/Game/C/Cloud_Skel","method":"mesh"}]})", L"b.json", cfg));
        FinishConfig(cfg, [](const std::wstring&) { return true; });
        const Pair* vin = cfg.FindForSkeleton(L"/Game/V/Vin_Skel.Vin_Skel");
        CHECK(vin && vin->Animation.size() == 1 && vin->Animation[0] == L"/Game/C/Cloud_Skel.Cloud_Skel");
        CHECK(cfg.Messages.empty());
    }
    {
        // A mesh pair onto the adopting skeleton itself is left alone (the KH2 outfit); one for Cloud follows the adoption.
        Config cfg;
        CHECK(AppendConfig(R"({"schema":"RebirthSkelCompat/1","pairs":[
            {"receiving_skeleton":"/Game/S/Seph_Skel","animation_skeleton":"/Game/C/Cloud_Skel"},
            {"receiving_skeleton":"/Game/K/Kh2_Skel","animation_skeleton":"/Game/S/Seph_Skel","method":"mesh"},
            {"receiving_skeleton":"/Game/X/X_Skel","animation_skeleton":"/Game/C/Cloud_Skel","method":"mesh"}]})", L"c.json", cfg));
        FinishConfig(cfg, [](const std::wstring&) { return true; });
        const Pair* kh2 = cfg.FindForSkeleton(L"/Game/K/Kh2_Skel.Kh2_Skel");
        CHECK(kh2 && kh2->Animation.size() == 1 && kh2->Animation[0] == L"/Game/S/Seph_Skel.Seph_Skel"); // not adopted: unchanged
        const Pair* x = cfg.FindForSkeleton(L"/Game/X/X_Skel.X_Skel");
        CHECK(x && x->Animation.size() == 1 && x->Animation[0] == L"/Game/S/Seph_Skel.Seph_Skel");
    }
}

static Config Finished(const char* json, bool installed = true)
{
    Config cfg;
    CHECK(AppendConfig(json, L"f.json", cfg));
    FinishConfig(cfg, [installed](const std::wstring&) { return installed; });
    return cfg;
}

static void TestFamilies()
{
    const std::wstring cloud = L"/Game/C/Cloud_Skel.Cloud_Skel";
    const std::wstring vin = L"/Game/V/Vin_Skel.Vin_Skel";
    const std::wstring seph = L"/Game/S/Seph_Skel.Seph_Skel";
    const auto hubOf = [](const Config& cfg, const std::wstring& hub, std::vector<std::wstring> members) {
        const Pair* p = cfg.FindForSkeleton(hub);
        return p && p->Use == Method::Animations && p->FamilyHub == hub && p->AdoptPaths.empty() && p->Animation == members;
    };
    {
        // Vincent and Sephiroth both play Cloud's animations, and Cloud plays theirs.
        const Config cfg = Finished(R"({"schema":"RebirthSkelCompat/1","pairs":[
            {"receiving_skeleton":"/Game/V/Vin_Skel","animation_skeletons":["/Game/C/Cloud_Skel"]},
            {"receiving_skeleton":"/Game/S/Seph_Skel","animation_skeletons":["/Game/C/Cloud_Skel"]},
            {"receiving_skeleton":"/Game/C/Cloud_Skel","animation_skeletons":["/Game/V/Vin_Skel","/Game/S/Seph_Skel"]}]})");
        CHECK(hubOf(cfg, cloud, {vin, seph}));
        CHECK(MeshPairTo(cfg, L"/Game/V/Vin_Skel.Vin_Skel", cloud) && MeshPairTo(cfg, L"/Game/S/Seph_Skel.Seph_Skel", cloud));
        CHECK(cfg.Pairs.size() == 3 && cfg.Messages.size() == 1);
        CHECK(FollowAdoption(cfg, vin) == cloud && FollowAdoption(cfg, cloud) == cloud);
    }
    {
        // The same as one family entry (the first skeleton is the hub), or with an explicit hub, or under "families".
        Config a = Finished(R"({"schema":"RebirthSkelCompat/1","pairs":[
            {"method":"family","skeletons":["/Game/C/Cloud_Skel","/Game/V/Vin_Skel","/Game/S/Seph_Skel"]}]})");
        CHECK(hubOf(a, cloud, {vin, seph}) && a.Pairs.size() == 3);
        Config b = Finished(R"({"schema":"RebirthSkelCompat/1","families":[
            {"skeletons":["/Game/V/Vin_Skel","/Game/S/Seph_Skel","/Game/C/Cloud_Skel"],"hub":"/Game/C/Cloud_Skel","fix_hierarchy":false}]})");
        CHECK(hubOf(b, cloud, {vin, seph}));
        const Pair* m = MeshPairTo(b, L"/Game/V/Vin_Skel.Vin_Skel", cloud);
        CHECK(m && !m->FixHierarchy && m->CarrySockets && m->FamilyHub == cloud);
        Config c = Finished(R"({"schema":"RebirthSkelCompat/1","pairs":[
            {"method":"both","receiving_skeleton":"/Game/C/Cloud_Skel","animation_skeletons":["/Game/V/Vin_Skel"]}]})");
        CHECK(hubOf(c, cloud, {vin}) && MeshPairTo(c, L"/Game/V/Vin_Skel.Vin_Skel", cloud));
        // Several receiving skeletons for one animation skeleton: they share it.
        Config d = Finished(R"({"schema":"RebirthSkelCompat/1","pairs":[
            {"receiving_skeletons":["/Game/V/Vin_Skel","/Game/S/Seph_Skel"],"animation_skeleton":"/Game/C/Cloud_Skel"}]})");
        CHECK(hubOf(d, cloud, {vin, seph}));
        // receiving_skeletons with mesh pairs: one pair per receiving skeleton, no family.
        Config e = Finished(R"({"schema":"RebirthSkelCompat/1","pairs":[
            {"receiving_skeletons":["/Game/V/Vin_Skel","/Game/S/Seph_Skel"],"animation_skeleton":"/Game/C/Cloud_Skel","method":"mesh"}]})");
        CHECK(MeshPairTo(e, L"/Game/V/Vin_Skel.Vin_Skel", cloud) && MeshPairTo(e, L"/Game/S/Seph_Skel.Seph_Skel", cloud) &&
              e.Pairs.size() == 2 && e.Pairs[0].FamilyHub.empty() && e.Messages.empty());
    }
    {
        // Two swaps both ways (Sephiroth over Cloud, Cloud over Sephiroth): the receiving skeleton of the first pair is the hub.
        const Config cfg = Finished(R"({"schema":"RebirthSkelCompat/1","pairs":[
            {"receiving_skeleton":"/Game/S/Seph_Skel","animation_skeletons":["/Game/C/Cloud_Skel"],"requires_paks":"SephirothOverCloud_P"},
            {"receiving_skeleton":"/Game/C/Cloud_Skel","animation_skeletons":["/Game/S/Seph_Skel"],"requires_paks":"CloudOverSephiroth_P"}]})");
        CHECK(hubOf(cfg, seph, {cloud}) && MeshPairTo(cfg, L"/Game/C/Cloud_Skel.Cloud_Skel", seph));
        CHECK(cfg.FindForSkeleton(seph)->RequiresPaks.size() == 2);
        // Only one of the swap paks: the classic pair, no family.
        Config one;
        CHECK(AppendConfig(R"({"schema":"RebirthSkelCompat/1","pairs":[
            {"receiving_skeleton":"/Game/S/Seph_Skel","animation_skeletons":["/Game/C/Cloud_Skel"],"requires_paks":"SephirothOverCloud_P"},
            {"receiving_skeleton":"/Game/C/Cloud_Skel","animation_skeletons":["/Game/S/Seph_Skel"],"requires_paks":"CloudOverSephiroth_P"}]})",
                           L"g.json", one));
        FinishConfig(one, [](const std::wstring& n) { return NameEquals(n, L"SephirothOverCloud_P"); });
        const Pair* p = one.FindForSkeleton(seph);
        CHECK(p && p->FamilyHub.empty() && p->Animation.size() == 1 && one.Pairs.size() == 1);
    }
    {
        // A union skeleton as hub: every original skeleton is a member, nothing stays on its own skeleton.
        const Config cfg = Finished(R"({"schema":"RebirthSkelCompat/1","families":[
            {"hub":"/MyMod/Union/Union_Skel","skeletons":["/Game/C/Cloud_Skel","/Game/V/Vin_Skel","/Game/S/Seph_Skel"]}]})");
        const std::wstring uni = L"/MyMod/Union/Union_Skel.Union_Skel";
        CHECK(hubOf(cfg, uni, {cloud, vin, seph}));
        CHECK(MeshPairTo(cfg, L"/Game/C/Cloud_Skel.Cloud_Skel", uni) && MeshPairTo(cfg, L"/Game/V/Vin_Skel.Vin_Skel", uni) &&
              MeshPairTo(cfg, L"/Game/S/Seph_Skel.Seph_Skel", uni));
    }
    {
        // Mesh pairs around a family: a member's own mesh pair joins the family, an outfit for a member follows to the
        // hub, a mesh pair that would pull the hub's meshes away is dropped, an unrelated one stays.
        const Config cfg = Finished(R"({"schema":"RebirthSkelCompat/1","pairs":[
            {"receiving_skeleton":"/Game/V/Vin_Skel","animation_skeleton":"/Game/T/Tifa_Skel","method":"mesh","fix_hierarchy":false},
            {"method":"family","skeletons":["/Game/C/Cloud_Skel","/Game/V/Vin_Skel","/Game/S/Seph_Skel"]},
            {"receiving_skeleton":"/Game/K/Kh2_Skel","animation_skeleton":"/Game/S/Seph_Skel","method":"mesh"},
            {"receiving_skeleton":"/Game/C/Cloud_Skel","animation_skeleton":"/Game/X/X_Skel","method":"mesh"},
            {"receiving_skeleton":"/Game/O/Outfit_Skel","animation_skeleton":"/Game/T/Tifa_Skel","method":"mesh"}]})");
        CHECK(hubOf(cfg, cloud, {vin, seph}));
        const Pair* v = MeshPairTo(cfg, L"/Game/V/Vin_Skel.Vin_Skel", cloud);
        CHECK(v && !v->FixHierarchy); // the member's mesh options carry over
        CHECK(v && v->KeepCompatible == std::vector<std::wstring>{vin}); // its own AnimBlueprints must still accept it
        const Pair* k = MeshPairTo(cfg, L"/Game/K/Kh2_Skel.Kh2_Skel", cloud);
        CHECK(k && k->KeepCompatible == std::vector<std::wstring>{seph}); // the outfit is still shown by Sephiroth's characters
        const Pair* o = MeshPairTo(cfg, L"/Game/O/Outfit_Skel.Outfit_Skel", L"/Game/T/Tifa_Skel.Tifa_Skel");
        CHECK(o && o->KeepCompatible.empty());
        const Pair* c = cfg.FindForSkeleton(cloud);
        CHECK(c && c->Use == Method::Animations); // not the dropped mesh pair
        CHECK(cfg.Pairs.size() == 5);
        bool hubNote = false, notTifa = false;
        for (const auto& m : cfg.Messages)
        {
            hubNote = hubNote || m.find(L"it is the hub of a family") != std::wstring::npos;
            notTifa = notTifa || m.find(L"not to /Game/T/Tifa_Skel.Tifa_Skel") != std::wstring::npos;
        }
        CHECK(hubNote && notTifa);
    }
    {
        // adopt_paths: separate folders still split one skeleton's animations without a family; overlapping ones share.
        const Config split = Finished(R"({"schema":"RebirthSkelCompat/1","pairs":[
            {"receiving_skeleton":"/Game/S/Seph_Skel","animation_skeleton":"/Game/C/Cloud_Skel","adopt_paths":"/Game/Motion/C/Neutral20"},
            {"receiving_skeleton":"/Game/V/Vin_Skel","animation_skeleton":"/Game/C/Cloud_Skel","adopt_paths":"/Game/Motion/C/Battle00"}]})");
        CHECK(split.Pairs.size() == 2 && split.Pairs[0].FamilyHub.empty() && split.Pairs[1].AdoptPaths.size() == 1 && split.Messages.empty());
        const Config overlap = Finished(R"({"schema":"RebirthSkelCompat/1","pairs":[
            {"receiving_skeleton":"/Game/S/Seph_Skel","animation_skeleton":"/Game/C/Cloud_Skel","adopt_paths":"/Game/Motion/C"},
            {"receiving_skeleton":"/Game/V/Vin_Skel","animation_skeleton":"/Game/C/Cloud_Skel","adopt_paths":"/Game/Motion/C/Battle00"}]})");
        CHECK(hubOf(overlap, cloud, {seph, vin}) && overlap.Messages.size() == 3); // two "adopt_paths not used" notes + the family
    }
    {
        // A family whose pak is missing is off; one with too few skeletons is skipped.
        const Config off = Finished(R"({"schema":"RebirthSkelCompat/1","families":[
            {"skeletons":["/Game/C/Cloud_Skel","/Game/V/Vin_Skel"],"requires_paks":"Missing_P"}]})", false);
        CHECK(off.Pairs.empty() && off.Messages.size() == 1);
        Config tiny;
        CHECK(AppendConfig(R"({"schema":"RebirthSkelCompat/1","families":[{"skeletons":["/Game/C/Cloud_Skel"]}]})", L"t.json", tiny));
        CHECK(tiny.Pairs.empty() && tiny.Messages.size() == 1);
    }

    // Randomised: whatever the pairs, the result has one entry per receiving skeleton, no "animations" chains, no two
    // pairs taking all animations of one skeleton, no mesh chains, and every family member is rebound to its hub.
    uint32_t seed = 4242;
    auto next = [&]() { seed = seed * 1664525u + 1013904223u; return seed >> 8; };
    const wchar_t* names[] = {L"/Game/A/A", L"/Game/B/B", L"/Game/C/C", L"/Game/D/D", L"/Game/E/E", L"/Game/F/F", L"/Game/G/G"};
    for (int round = 0; round < 400; ++round)
    {
        std::string json = R"({"schema":"RebirthSkelCompat/1","pairs":[)";
        const int pairs = 1 + static_cast<int>(next() % 6);
        for (int k = 0; k < pairs; ++k)
        {
            const uint32_t kind = next() % 10;
            const std::string method = kind < 6 ? "animations" : (kind < 9 ? "mesh" : "family");
            std::string receiving = SkelCompat::Narrow(names[next() % 7]);
            std::string list;
            const int count = 1 + static_cast<int>(next() % 3);
            for (int a = 0; a < count; ++a) { list += std::string(a ? "," : "") + "\"" + SkelCompat::Narrow(names[next() % 7]) + "\""; }
            json += std::string(k ? "," : "") + "{\"method\":\"" + method + "\",\"receiving_skeleton\":\"" + receiving + "\",\"animation_skeletons\":[" + list + "]";
            if (method == "animations" && next() % 4 == 0) { json += std::string(",\"adopt_paths\":\"/Game/Motion/") + static_cast<char>('a' + next() % 3) + "\""; }
            json += "}";
        }
        json += "]}";
        Config cfg;
        CHECK(AppendConfig(json, L"r.json", cfg));
        FinishConfig(cfg, [](const std::wstring&) { return true; });
        for (size_t i = 0; i < cfg.Pairs.size(); ++i)
        {
            const Pair& p = cfg.Pairs[i];
            CHECK(p.Use != Method::Family && !p.Animation.empty());
            for (size_t j = 0; j < cfg.Pairs.size(); ++j)
            {
                if (i == j) { continue; }
                const Pair& q = cfg.Pairs[j];
                CHECK(!PathEquals(p.Receiving, q.Receiving));
                if (p.Use == q.Use && std::any_of(q.Animation.begin(), q.Animation.end(), [&](const std::wstring& a) { return PathEquals(a, p.Receiving); }))
                {
                    CHECK(false); // a chain survived
                }
                if (p.Use == Method::Animations && q.Use == Method::Animations && i < j && p.AdoptPaths.empty())
                {
                    for (const auto& a : p.Animation)
                    {
                        CHECK(std::none_of(q.Animation.begin(), q.Animation.end(), [&](const std::wstring& b) { return PathEquals(a, b); }));
                    }
                }
            }
            if (p.Use == Method::Animations && !p.FamilyHub.empty())
            {
                for (const auto& member : p.Animation)
                {
                    const Pair* m = cfg.FindForSkeleton(member);
                    CHECK(m && m->Use == Method::Mesh && m->Animation.size() == 1 && PathEquals(m->Animation[0], p.Receiving));
                    // No other "animations" pair moves a member's animations, and every mesh bound for a member goes to the hub.
                    for (const auto& q : cfg.Pairs)
                    {
                        if (&q == &p) { continue; }
                        const bool lists = std::any_of(q.Animation.begin(), q.Animation.end(), [&](const std::wstring& a) { return PathEquals(a, member); });
                        CHECK(!lists);
                    }
                }
            }
        }
        if (Failures) { std::printf("random config: %s\n", json.c_str()); break; }
    }
}

static void TestAnimSetRows()
{
    // Names and paths.
    CHECK(CharacterPackPath(L"PC0000_00_Cloud_Standard") ==
          L"/Game/DataAsset/Game/CharaSpec/CharaSpec_PC0000_00_Cloud_Standard.CharaSpec_PC0000_00_Cloud_Standard");
    CHECK(CharacterPackPath(L" CharaSpec_PC0011_00_Vincent_Standard ") ==
          L"/Game/DataAsset/Game/CharaSpec/CharaSpec_PC0011_00_Vincent_Standard.CharaSpec_PC0011_00_Vincent_Standard");
    CHECK(CharacterPackPath(L"EndAssetDataAsset'/Game/DataAsset/Game/CharaSpec/CharaSpec_X.CharaSpec_X'") == L"/Game/DataAsset/Game/CharaSpec/CharaSpec_X.CharaSpec_X");
    CHECK(CharacterPackPath(L"PC0000 Cloud").empty());
    CHECK(CharacterPackPath(L"").empty());
    CHECK(IsBattleSetName(L"Battle00") && IsBattleSetName(L"battle01_Comp") && !IsBattleSetName(L"Neutral00") && !IsBattleSetName(L"Bat"));
    CHECK(LooksLikeSetName(L"Battle00") && LooksLikeSetName(L"Neutral20") && LooksLikeSetName(L"Facial01_X") && !LooksLikeSetName(L"PC0000_Cloud") &&
          !LooksLikeSetName(L"Battle") && !LooksLikeSetName(L"BattleCamera"));
    CHECK(ObjectNameOfPath(L"/Game/A/Battle00.Battle00") == L"Battle00");
    SetSource s;
    CHECK(ParseSetSource(L"/Game/Motion/Player/PC0000_Cloud/", s) && s.Folder && s.Path == L"/Game/Motion/Player/PC0000_Cloud");
    CHECK(ParseSetSource(L"\\Game\\Motion\\Player\\PC0000_Cloud\\Battle00", s) && !s.Folder && s.Path == L"/Game/Motion/Player/PC0000_Cloud/Battle00.Battle00");
    CHECK(ParseSetSource(L"EndAnimSet'/Game/Motion/NPC/Rufus/Gun.Gun'", s) && !s.Folder && s.Path == L"/Game/Motion/NPC/Rufus/Gun.Gun");
    CHECK(ParseSetSource(L"/Game/Motion/NPC/Rufus/Gun.Gun", s) && !s.Folder);
    CHECK(!ParseSetSource(L"Motion/Player", s));

    // Parsing: sources go by set name, moves, sets, field actions, cutscene family, requires_paks.
    Config cfg;
    const char* file = R"({
      "schema": "RebirthSkelCompat/1",
      "animation_sets": [
        { "character": "PC0000_00_Cloud_Standard",
          "battle": [ "/Game/Motion/Player/PC0011_Vincent",
                      { "from": "/Game/Motion/NPC/Rufus/Battle00_Gun.Battle00_Gun", "as": "Battle00" },
                      "/Game/Motion/Player/PC0000_Cloud/Neutral20.Neutral20",
                      "/Game/Motion/Player/PC0000_Cloud" ],
          "field": [ "/Game/Motion/Player/PC0011_Vincent", "/Game/Motion/Player/PC0000_Cloud" ],
          "sets": [ "Neutral03", "bad/name" ],
          "moves": { "B_Atk01_0": "/Game/Motion/NPC/Rufus/Battle00/B_Shot01", "Battle01/B_Atk02": "/Game/Motion/NPC/Rufus/Battle00/B_Shot02.B_Shot02",
                     "bad key": "/Game/X", "B_Atk01_0": "/Game/Y" },
          "field_actions": "/Game/Motion/Player/PC0000_Cloud/",
          "skeleton": "/Game/Character/Player/PC0011_00_Vincent_Standard/Model/PC0011_00_Skeleton",
          "cutscene": "/Game/Character/Player/PC0000_00_Cloud_Standard/Model/PC0000_00_Skeleton",
          "requires_paks": "FullyPlayableVincentAssets_P.pak" },
        { "characters": [ "PC0000_00_Cloud_Standard", "PC0000_00_Cloud_Standard_NoBattle" ],
          "battle": [ "/Game/Motion/Player/PC0010_Sephiroth", "/Game/Motion/Player/PC0011_Vincent" ],
          "moves": [ { "key": "B_Atk01_0", "animation": "/Game/Z" }, { "set": "Battle00", "key": "B_Guard01", "animation": "/Game/G" } ],
          "field_actions": "PC0010_Sephiroth" },
        { "character": "PC0005_00_Yuffie_Standard", "field": "/Game/Motion/Player/PC0002_Tifa", "requires_paks": ["NotInstalled"] },
        { "character": "PC0001_00_Barret_Standard" },
        { "battle": "/Game/Motion/Player/PC0000_Cloud" },
        { "character": "PC0002_00_Tifa_Standard", "field": "/Game/Motion/Player/PC0003_Aerith", "enabled": false }
      ]
    })";
    CHECK(AppendConfig(file, L"rows.json", cfg));
    CHECK(cfg.AnimSets.size() == 3);
    CHECK(cfg.Pairs.size() == 1 && cfg.Pairs[0].Use == Method::Family && cfg.Pairs[0].Hub.find(L"PC0000_00_Skeleton") != std::wstring::npos &&
          cfg.Pairs[0].Receiving.find(L"PC0011_00_Skeleton") != std::wstring::npos && cfg.Pairs[0].RequiresPaks.size() == 1);
    {
        const AnimSetRow& row = cfg.AnimSets[0];
        CHECK(row.Characters.size() == 1 && row.Characters[0].find(L"CharaSpec_PC0000_00_Cloud_Standard.") != std::wstring::npos);
        CHECK(row.Battle.size() == 3 && row.Battle[0].Folder && !row.Battle[1].Folder && row.Battle[1].As == L"Battle00" && row.Battle[2].Folder);
        CHECK(row.Field.size() == 3 && !row.Field[0].Folder && row.Field[0].Path == L"/Game/Motion/Player/PC0000_Cloud/Neutral20.Neutral20"); // moved over
        CHECK(row.Sets.size() == 1 && row.Sets[0] == L"Neutral03");
        CHECK(row.Moves.size() == 2 && row.Moves[0].Key == L"B_Atk01_0" && row.Moves[0].Set.empty() &&
              row.Moves[0].Animation == L"/Game/Motion/NPC/Rufus/Battle00/B_Shot01.B_Shot01" && row.Moves[1].Set == L"Battle01" && row.Moves[1].Key == L"B_Atk02");
        CHECK(row.FieldActions == L"PC0000_Cloud");
        CHECK(row.RequiresPaks.size() == 1 && row.RequiresPaks[0] == L"FullyPlayableVincentAssets_P");
        // Which sets the row reads from where.
        const auto battle00 = SetSourcePaths(row, L"Battle00");
        CHECK(battle00.size() == 3 && battle00[0] == L"/Game/Motion/Player/PC0011_Vincent/Battle00.Battle00" &&
              battle00[1] == L"/Game/Motion/NPC/Rufus/Battle00_Gun.Battle00_Gun" && battle00[2] == L"/Game/Motion/Player/PC0000_Cloud/Battle00.Battle00");
        const auto neutral20 = SetSourcePaths(row, L"neutral20");
        CHECK(neutral20.size() == 2 && neutral20[0] == L"/Game/Motion/Player/PC0000_Cloud/Neutral20.Neutral20" &&
              neutral20[1] == L"/Game/Motion/Player/PC0011_Vincent/neutral20.neutral20"); // Cloud's folder adds nothing new
        const auto names = RowSetNames(row);
        CHECK(std::find(names.begin(), names.end(), L"Battle00") != names.end() && std::find(names.begin(), names.end(), L"Neutral03") != names.end() &&
              std::find(names.begin(), names.end(), L"Facial00") != names.end() && std::find(names.begin(), names.end(), L"Battle01") != names.end());
        const auto moves = MovesFor(row, L"battle01");
        CHECK(moves.size() == 2 && moves[0]->Key == L"B_Atk02" && moves[1]->Key == L"B_Atk01_0");
        CHECK(MovesFor(row, L"Battle00").size() == 1);
    }
    // A row with only battle folders builds no field sets.
    {
        const auto names = RowSetNames(cfg.AnimSets[1]);
        CHECK(!names.empty() && std::all_of(names.begin(), names.end(), [](const std::wstring& n) { return IsBattleSetName(n); }));
        CHECK(cfg.AnimSets[1].Characters.size() == 2);
    }
    const size_t parseMessages = cfg.Messages.size();
    CHECK(parseMessages >= 5); // bad set name, bad/duplicate moves, a Battle row's field set, Barret without sources, no character

    // FinishConfig: Yuffie's pak is missing; the two Cloud rows join (first sources first, first move wins).
    FinishConfig(cfg, [](const std::wstring& name) { return NameEquals(name, L"FullyPlayableVincentAssets_P"); });
    CHECK(cfg.AnimSets.size() == 2);
    const AnimSetRow* cloud = cfg.FindAnimSetRow(L"/game/dataasset/game/charaspec/charaspec_pc0000_00_cloud_standard.charaspec_pc0000_00_cloud_standard");
    const AnimSetRow* noBattle = cfg.FindAnimSetRow(CharacterPackPath(L"PC0000_00_Cloud_Standard_NoBattle"));
    CHECK(cloud && noBattle && cloud != noBattle);
    if (cloud)
    {
        CHECK(cloud->Battle.size() == 4 && cloud->Battle[3].Path == L"/Game/Motion/Player/PC0010_Sephiroth"); // Vincent's folder only once
        CHECK(cloud->Moves.size() == 3 && cloud->Moves[0].Animation.find(L"B_Shot01") != std::wstring::npos && cloud->Moves[2].Key == L"B_Guard01");
        CHECK(cloud->FieldActions == L"PC0000_Cloud");
    }
    if (noBattle) { CHECK(noBattle->FieldActions == L"PC0010_Sephiroth" && noBattle->Battle.size() == 2 && noBattle->Moves.size() == 2); }
    CHECK(!cfg.FindAnimSetRow(CharacterPackPath(L"PC0005_00_Yuffie_Standard")));
    // The cutscene family went through the families step: Vincent's meshes go to Cloud's skeleton.
    const Pair* vincent = cfg.FindForSkeleton(L"/Game/Character/Player/PC0011_00_Vincent_Standard/Model/PC0011_00_Skeleton.PC0011_00_Skeleton");
    CHECK(vincent && vincent->Use == Method::Mesh && vincent->Animation.size() == 1 && vincent->Animation[0].find(L"PC0000_00_Skeleton") != std::wstring::npos);

    // A file with only rows is a valid file; one without any list is not.
    Config only;
    CHECK(AppendConfig(R"({"schema":"RebirthSkelCompat/1","animation_sets":[{"character":"PC0011_00_Vincent_Standard","field":"/Game/Motion/Player/PC0000_Cloud"}]})",
                       L"a.json", only));
    CHECK(only.AnimSets.size() == 1 && only.Pairs.empty());
    CHECK(!AppendConfig(R"({"schema":"RebirthSkelCompat/1"})", L"b.json", only));

    // First source wins.
    const std::vector<std::vector<std::pair<uint64_t, int>>> lists{{{1, 10}, {2, 20}}, {{2, 99}, {3, 30}}, {{1, 77}, {4, 40}}};
    const auto merged = MergeFirstWins(lists);
    CHECK(merged.size() == 4 && merged[0].second == 10 && merged[1].second == 20 && merged[2].second == 30 && merged[3].second == 40);
}

static void TestSetImage()
{
    CHECK(HashBuckets(0) == 1 && HashBuckets(3) == 1 && HashBuckets(4) == 16 && HashBuckets(17) == 16 && HashBuckets(18) == 32 &&
          HashBuckets(326) == 256 && HashBuckets(500) == 512);
    // GetTypeHash(FNameEntryId): block in the high bits, offset spread over the low ones.
    CHECK(NameEntryHash(0) == 0);
    CHECK(NameEntryHash(1) == (1u << 16) + 1u);
    CHECK(NameEntryHash(0x10000) == (1u << 19) + 1u);
    CHECK(NameEntryHash(0x20030) == (2u << 19) + 2u + (0x30u << 16) + 0x30u + 3u);
    CHECK(NameHash(0x20030, 5, true) == NameEntryHash(0x20030) + 5 && NameHash(0x20030, 5, false) == 0x20035);
    // Build images of every size up to 300 and look every key up the way TSet::FindId does.
    uint32_t seed = 12345;
    for (int n = 1; n <= 300; n += (n < 20 ? 1 : 7))
    {
        std::vector<uint32_t> hashes;
        for (int i = 0; i < n; ++i)
        {
            seed = seed * 1664525u + 1013904223u;
            hashes.push_back(NameHash(seed >> 8, static_cast<uint32_t>(i % 3), true));
        }
        const SetImage image = BuildSetImage(hashes);
        CHECK(image.HashSize == HashBuckets(n) && image.MaxBits % 32 == 0 && image.MaxBits >= std::max(128, n) &&
              static_cast<int32_t>(image.Words.size()) == image.MaxBits / 32);
        for (int i = 0; i < n; ++i)
        {
            int found = -1;
            for (int e = image.Heads[hashes[static_cast<size_t>(i)] & static_cast<uint32_t>(image.HashSize - 1)]; e != -1; e = image.Next[static_cast<size_t>(e)])
            {
                if (e == i) { found = e; break; }
            }
            CHECK(found == i);
            CHECK((image.Words[static_cast<size_t>(i / 32)] >> (i % 32)) & 1u);
        }
        const std::vector<uint8_t> allocated(static_cast<size_t>(n), 1);
        CHECK(SetChainsMatch(image.Heads, image.Next, image.Bucket, allocated, hashes));
        // Another hash function does not check out (with more than a handful of keys).
        if (n >= 8 && image.HashSize > 1)
        {
            std::vector<uint32_t> other;
            for (uint32_t h : hashes) { other.push_back(h ^ 0x5A5A5A5Au); }
            CHECK(!SetChainsMatch(image.Heads, image.Next, image.Bucket, allocated, other));
        }
        if (n > 1)
        {
            // A free slot that a chain still names, or an element no chain reaches, fails.
            std::vector<uint8_t> holes = allocated;
            holes[0] = 0;
            CHECK(!SetChainsMatch(image.Heads, image.Next, image.Bucket, holes, hashes));
            std::vector<int32_t> heads = image.Heads;
            const size_t bucket = static_cast<size_t>(image.Bucket[static_cast<size_t>(n - 1)]);
            heads[bucket] = image.Next[static_cast<size_t>(heads[bucket])];
            CHECK(!SetChainsMatch(heads, image.Next, image.Bucket, allocated, hashes));
        }
    }
}

// TMap<FName, UObject*> written and read back the way the runtime does, with plain memory standing in for the game's.
static void TestNameObjectMaps()
{
    const auto read = [](void* to, const void* from, size_t size) { std::memcpy(to, from, size); return true; };
    std::vector<void*> blocks;
    const auto alloc = [&](size_t size) { void* p = std::malloc(size); blocks.push_back(p); return p; };
    const auto release = [&](void* p) { blocks.erase(std::find(blocks.begin(), blocks.end(), p)); std::free(p); };
    uint32_t seed = 777;
    const auto key = [&](int i) {
        seed = seed * 1664525u + 1013904223u;
        // Comparison indices like the game's (block << 16 | offset), numbers mostly 0, sometimes a "_N" suffix.
        const uint64_t comparison = ((seed >> 20) & 0x3F) << 16 | ((seed >> 4) & 0xFFFE);
        return comparison | (static_cast<uint64_t>(i % 5 == 0 ? (i % 7) + 1 : 0) << 32);
    };
    for (const int n : {1, 2, 3, 4, 7, 31, 32, 33, 127, 128, 129, 200, 326, 600})
    {
        std::vector<NameObjectPair> entries;
        std::vector<uint64_t> seen;
        while (static_cast<int>(entries.size()) < n)
        {
            const uint64_t k = key(static_cast<int>(entries.size()));
            if (std::find(seen.begin(), seen.end(), k) != seen.end()) { continue; }
            seen.push_back(k);
            entries.push_back({k, reinterpret_cast<void*>(static_cast<uintptr_t>(0x10000 + 16 * entries.size()))});
        }
        for (const bool handle : {true, false})
        {
            SetHeader header;
            CHECK(BuildNameObjectMap(entries, handle, alloc, release, header));
            CHECK(header.Num == n && header.Max == n && header.NumBits == n && header.NumFree == 0 && header.FirstFree == -1);
            CHECK((n > 128) == (header.HeapFlags != nullptr) && (header.HashSize > 1) == (header.HeapHash != nullptr));
            std::vector<NameObjectPair> back;
            int forms = 0;
            std::wstring why;
            CHECK(ReadNameObjectMap(header, read, back, forms, why));
            CHECK(back.size() == entries.size());
            for (size_t i = 0; i < back.size() && i < entries.size(); ++i) { CHECK(back[i].Key == entries[i].Key && back[i].Value == entries[i].Value); }
            CHECK((forms & (handle ? 2 : 1)) != 0);
            if (n >= 33) { CHECK(forms == (handle ? 2 : 1)); } // the other form does not check out
            for (int i = 0; i < n; ++i) { CHECK(FindInNameObjectMap(header, read, entries[static_cast<size_t>(i)].Key, handle) == i); }
            CHECK(FindInNameObjectMap(header, read, 0xDEADBEEFull, handle) == -1);

            if (n >= 8)
            {
                // The engine removed an element: free slot, unlinked from its bucket, counted in NumFree.
                const int32_t gone = n / 2;
                auto* elements = static_cast<uint8_t*>(header.Elements);
                int32_t next = 0, bucket = 0;
                std::memcpy(&next, elements + gone * NameObjectStride + 16, 4);
                std::memcpy(&bucket, elements + gone * NameObjectStride + 20, 4);
                int32_t* head = header.HeapHash ? header.HeapHash + bucket : &header.InlineHash;
                if (*head == gone) { *head = next; }
                else
                {
                    for (int32_t e = *head; e != -1;)
                    {
                        int32_t after = 0;
                        std::memcpy(&after, elements + e * NameObjectStride + 16, 4);
                        if (after == gone)
                        {
                            std::memcpy(elements + e * NameObjectStride + 16, &next, 4);
                            break;
                        }
                        e = after;
                    }
                }
                uint32_t* words = header.HeapFlags ? header.HeapFlags : header.InlineFlags;
                words[gone / 32] &= ~(1u << (gone % 32));
                header.NumFree = 1;
                header.FirstFree = gone;
                CHECK(ReadNameObjectMap(header, read, back, forms, why));
                CHECK(static_cast<int>(back.size()) == n - 1 && (forms & (handle ? 2 : 1)) != 0);
                CHECK(std::none_of(back.begin(), back.end(), [&](const NameObjectPair& p) { return p.Key == entries[static_cast<size_t>(gone)].Key; }));
                // A broken layout is refused: an element filed under the wrong bucket, or flags that do not add up.
                if (header.HashSize > 1)
                {
                    const int32_t victim = gone == 0 ? 1 : 0;
                    int32_t wrong = 0;
                    std::memcpy(&wrong, elements + victim * NameObjectStride + 20, 4);
                    ++wrong;
                    std::memcpy(elements + victim * NameObjectStride + 20, &wrong, 4);
                    CHECK(!ReadNameObjectMap(header, read, back, forms, why) && back.empty());
                    --wrong;
                    std::memcpy(elements + victim * NameObjectStride + 20, &wrong, 4);
                }
                header.NumFree = 2;
                CHECK(!ReadNameObjectMap(header, read, back, forms, why));
            }
            for (void* block : {header.Elements, static_cast<void*>(header.HeapFlags), static_cast<void*>(header.HeapHash)})
            {
                if (block) { release(block); }
            }
        }
    }
    CHECK(blocks.empty());
    // Allocation failure hands back what it got.
    int calls = 0;
    SetHeader header;
    std::vector<NameObjectPair> many(300);
    for (size_t i = 0; i < many.size(); ++i) { many[i].Key = i + 1; }
    CHECK(!BuildNameObjectMap(many, true, [&](size_t size) -> void* { return ++calls == 2 ? nullptr : alloc(size); }, release, header));
    CHECK(blocks.empty());
    CHECK(!BuildNameObjectMap({}, true, alloc, release, header));
    // An empty map reads as empty.
    std::vector<NameObjectPair> back;
    int forms = 0;
    std::wstring why;
    CHECK(ReadNameObjectMap(SetHeader{}, read, back, forms, why) && back.empty());
}

// 3.2: auto match, socket stand-ins, proportions, chained moves.
static MatchAnim Anim(const wchar_t* name, float length, bool additive = false) { return MatchAnim{name, length, additive}; }

static void TestAutoMatch()
{
    // Names.
    CHECK(IsAttackName(L"B_NAttack01_0") && IsAttackName(L"B_SAttack02_2_1") && IsAttackName(L"B_CounterAttack01") && IsAttackName(L"B_NAttackJ01_0") &&
          IsAttackName(L"B_AAttack02_2") && IsAttackName(L"B_AtkBurst03_0_1") && IsAttackName(L"B_AtkLimit01_0") && IsAttackName(L"B_AtkBurstJ06_0"));
    CHECK(!IsAttackName(L"B_Walk01_0") && !IsAttackName(L"B_DmgB01") && !IsAttackName(L"B_MagAttack01_0") && !IsAttackName(L"N_Atk01") &&
          !IsAttackName(L"B_ChainRangeAtk_A06_0") && !IsAttackName(L"B_Ability01_0"));
    CHECK(IsAttackName(L"B_NAttackJ01_0", true) && !IsAttackName(L"B_AtkBurst01_0", true) && !IsAttackName(L"B_AtkBurstJ01_0", true));
    {
        const auto n = Detail::ParseAnimName(L"B_NAttack01_1_2");
        CHECK(n.Lead == L"b_" && n.Body == L"nattack" && n.Num == L"01" && n.Rest == (std::vector<std::wstring>{L"1", L"2"}) && n.Stem == L"b_nattack01_1" &&
              n.Phase == 2);
        const auto r = Detail::ParseAnimName(L"pc0000_00_B_DmgF01");
        CHECK(r.Lead == L"b_" && r.Body == L"dmgf" && r.Num == L"01" && r.Phase == -1);
    }

    // A player set asks for these; another character's set offers others.
    const std::vector<MatchAnim> own{Anim(L"B_Idle01_1", 2.0f),        Anim(L"B_NAttack01_0", 1.43f), Anim(L"B_NAttack01_1", 1.8f),
                                     Anim(L"B_NAttack01_1_0", 0.27f),  Anim(L"B_NAttack01_1_1", 0.53f), Anim(L"B_NAttack01_1_2", 1.27f),
                                     Anim(L"B_NAttackJ01_0", 0.87f),   Anim(L"B_AtkBurst01_0", 3.23f), Anim(L"B_Dmg01_Add", 1.0f, true),
                                     Anim(L"B_Walk01_0", 1.0f)};
    const std::vector<MatchAnim> rufus{Anim(L"B_Idle01_1", 4.0f),       Anim(L"B_AtkSpeedShot01", 1.67f), Anim(L"B_AtkNearShot01", 1.47f),
                                       Anim(L"B_AtkShotGun01", 2.5f),   Anim(L"B_AtkFireBreak01_0", 3.13f), Anim(L"B_AtkFireBreak01_1", 0.23f),
                                       Anim(L"B_AtkAerialTwinShot01", 1.9f), Anim(L"B_AtkShot01_Add", 1.0f, true), Anim(L"B_Reload01", 1.5f),
                                       Anim(L"B_DmgB01", 1.0f),         Anim(L"B_Walk01_0", 1.2f)};
    const auto keyed = [](const std::vector<MatchAnim>& anims, uint64_t base) {
        MergeSource source;
        for (size_t i = 0; i < anims.size(); ++i)
        {
            // Same name -> same key across sources.
            uint64_t key = 0;
            for (const wchar_t c : FoldedKey(anims[i].Name)) { key = key * 131 + static_cast<uint64_t>(c); }
            source.Keys.push_back(key);
            source.Anims.push_back(anims[i]);
        }
        (void)base;
        return source;
    };
    const auto find = [](const std::vector<MergedEntry>& merged, const std::vector<MergeSource>& sources, const wchar_t* name) -> const MatchAnim* {
        uint64_t key = 0;
        for (const wchar_t c : FoldedKey(name)) { key = key * 131 + static_cast<uint64_t>(c); }
        for (const auto& e : merged)
        {
            if (e.Key == key) { return &sources[e.Source].Anims[e.Entry]; }
        }
        return nullptr;
    };
    {
        // "auto": true (attacks) first: attacks, air attacks and abilities come from Rufus by kind and length; the rest stays.
        std::vector<MergeSource> sources{keyed(rufus, 0), keyed(own, 0)};
        sources[0].Auto = AutoMatchMode::Attacks;
        const auto merged = MergeSetSources(sources);
        CHECK(merged.size() == own.size()); // only names the game asks for
        const MatchAnim* a = find(merged, sources, L"B_NAttack01_0");
        CHECK(a && a->Name == L"B_AtkNearShot01"); // 1.47 is closest to 1.43
        const MatchAnim* b = find(merged, sources, L"B_NAttack01_1");
        CHECK(b && b->Name == L"B_AtkSpeedShot01"); // closest unused to 1.8
        const MatchAnim* c = find(merged, sources, L"B_NAttack01_1_2");
        CHECK(c && c->Name == L"B_AtkShotGun01"); // the leader of a phased move; then the pool is used up
        const MatchAnim* air = find(merged, sources, L"B_NAttackJ01_0");
        CHECK(air && air->Name == L"B_AtkAerialTwinShot01");
        const MatchAnim* burst = find(merged, sources, L"B_AtkBurst01_0");
        CHECK(burst && burst->Name == L"B_AtkFireBreak01_0");
        CHECK(find(merged, sources, L"B_NAttack01_1_0")->Name == L"B_NAttack01_1_0"); // short pieces keep the character's own
        CHECK(find(merged, sources, L"B_Idle01_1")->Length == 2.0f);                 // not an attack: Rufus's same name is not taken
        CHECK(find(merged, sources, L"B_Walk01_0")->Length == 1.0f);
        CHECK(find(merged, sources, L"B_Dmg01_Add")->Additive);
    }
    {
        // "basic": abilities and limits stay the character's own.
        std::vector<MergeSource> sources{keyed(rufus, 0), keyed(own, 0)};
        sources[0].Auto = AutoMatchMode::Basic;
        const auto merged = MergeSetSources(sources);
        CHECK(find(merged, sources, L"B_AtkBurst01_0")->Name == L"B_AtkBurst01_0");
        CHECK(find(merged, sources, L"B_NAttack01_0")->Name == L"B_AtkNearShot01");
    }
    {
        // "all": the whole set first (same names win: idle, walk), attacks matched as above.
        std::vector<MergeSource> sources{keyed(rufus, 0), keyed(own, 0)};
        sources[0].Auto = AutoMatchMode::All;
        const auto merged = MergeSetSources(sources);
        CHECK(merged.size() == own.size() + 9); // every Rufus name too
        CHECK(find(merged, sources, L"B_Idle01_1")->Length == 4.0f && find(merged, sources, L"B_Walk01_0")->Length == 1.2f);
        CHECK(find(merged, sources, L"B_NAttack01_0")->Name == L"B_AtkNearShot01");
    }
    {
        // The character's own set first: it has every attack, so the auto source fills nothing.
        std::vector<MergeSource> sources{keyed(own, 0), keyed(rufus, 0)};
        sources[1].Auto = AutoMatchMode::Attacks;
        const auto merged = MergeSetSources(sources);
        CHECK(merged.size() == own.size() && std::all_of(merged.begin(), merged.end(), [](const MergedEntry& e) { return e.Source == 0; }));
    }
    {
        // Variants: a player source with another suffix of the same move.
        const std::vector<MatchAnim> target{Anim(L"B_Walk01_0_L0", 1.0f), Anim(L"B_Turn01", 1.0f)};
        const std::vector<MatchAnim> offer{Anim(L"B_Walk01_0", 1.3f), Anim(L"B_Turn01_L90", 1.0f)};
        const auto picks = AutoMatch(target, {1, 1}, offer);
        CHECK(picks.size() == 2 && picks[0].Target == 0 && picks[0].Source == 0 && picks[0].Tier == 2 && picks[1].Target == 1 && picks[1].Source == 1);
        CHECK(AutoMatch(target, {1, 0}, offer).size() == 1); // names that are not open are left alone
    }
    // A split move is offered whole: aim, fire and recover pieces played one after another.
    {
        const std::vector<MatchAnim> target{Anim(L"B_NAttack01_0", 2.5f), Anim(L"B_NAttack02_0", 0.8f)};
        const std::vector<MatchAnim> offer{Anim(L"B_AtkShot02_0", 0.73f), Anim(L"B_AtkShot02_1", 0.4f), Anim(L"B_AtkShot02_2", 1.4f),
                                           Anim(L"B_AtkKick01", 0.9f), Anim(L"B_AtkShot01_Add", 1.0f, true)};
        const auto picks = AutoMatch(target, {1, 1}, offer);
        CHECK(picks.size() == 2);
        if (picks.size() == 2)
        {
            CHECK(picks[0].Target == 0 && picks[0].Source == 0 && (picks[0].Chain == std::vector<size_t>{0, 1, 2}));
            CHECK(picks[1].Target == 1 && picks[1].Source == 3 && picks[1].Chain.empty());
        }
        // Through the merge: the entry carries the chain.
        MergeSource mine, theirs;
        theirs.Auto = AutoMatchMode::Attacks;
        for (size_t i = 0; i < target.size(); ++i) { mine.Keys.push_back(100 + i); mine.Anims.push_back(target[i]); }
        for (size_t i = 0; i < offer.size(); ++i) { theirs.Keys.push_back(200 + i); theirs.Anims.push_back(offer[i]); }
        const auto merged = MergeSetSources({theirs, mine});
        CHECK(merged.size() == 2 && merged[0].Key == 100 && merged[0].Source == 0 && merged[0].Chain.size() == 3 && merged[1].Chain.empty());
    }
    // Every attack used once before any is used again.
    {
        const std::vector<MatchAnim> target{Anim(L"B_SAttack01_0", 1.0f), Anim(L"B_SAttack02_0", 1.0f), Anim(L"B_SAttack03_0", 1.0f)};
        const std::vector<MatchAnim> offer{Anim(L"B_AtkKick01", 1.0f), Anim(L"B_AtkShot01_1", 5.0f)};
        const auto picks = AutoMatch(target, {1, 1, 1}, offer);
        CHECK(picks.size() == 3 && picks[0].Source == 0 && picks[1].Source == 1 && picks[2].Source == 0);
    }
    // "only": the source offers only animations with one of the words in their name.
    {
        CHECK(NameHasAny(L"B_AtkSpeedShot01", {L"shot"}) && NameHasAny(L"B_AtkShotGun01", {L"Gun", L"Kick"}) && !NameHasAny(L"B_AtkKick01", {L"Shot"}) &&
              NameHasAny(L"B_AtkKick01", {}));
        const std::vector<MatchAnim> target{Anim(L"B_SAttack01_0", 1.0f), Anim(L"B_SAttack02_0", 1.0f), Anim(L"B_SAttack03_0", 1.0f)};
        const std::vector<MatchAnim> offer{Anim(L"B_AtkKick01", 1.0f), Anim(L"B_AtkShot01_1", 5.0f), Anim(L"B_AtkTonfa01", 1.1f)};
        const auto picks = AutoMatch(target, {1, 1, 1}, offer, {L"Shot"});
        CHECK(picks.size() == 3 && std::all_of(picks.begin(), picks.end(), [](const AutoMatchPick& p) { return p.Source == 1; }));
        CHECK(AutoMatch(target, {1, 1, 1}, offer, {L"Sword"}).empty());
        // Variants honour it too.
        const std::vector<MatchAnim> walk{Anim(L"B_Walk01_0_L0", 1.0f)};
        CHECK(AutoMatch(walk, {1}, {Anim(L"B_Walk01_0", 1.3f)}, {L"Shot"}).empty());
        // Through the merge, same names too: Rufus's B_Idle01_1 is not taken by "all" when it lacks the word.
        std::vector<MergeSource> sources{keyed(rufus, 0), keyed(own, 0)};
        sources[0].Auto = AutoMatchMode::All;
        sources[0].Only = {L"Shot"};
        const auto merged = MergeSetSources(sources);
        CHECK(find(merged, sources, L"B_Idle01_1")->Length == 2.0f);
        CHECK(find(merged, sources, L"B_NAttack01_0")->Name == L"B_AtkNearShot01");
        CHECK(find(merged, sources, L"B_AtkBurst01_0")->Name != L"B_AtkFireBreak01_0"); // no "Shot" in the name
        CHECK(find(merged, sources, L"B_AtkSpeedShot01") != nullptr && find(merged, sources, L"B_Reload01") == nullptr);
    }
}

static void TestV32Config()
{
    const std::wstring cloudSkel = L"/Game/Character/Player/PC0000_00_Cloud_Standard/Model/PC0000_00_Skeleton.PC0000_00_Skeleton";
    const std::wstring vincentSkel = L"/Game/Character/Player/PC0011_00_Vincent_Standard/Model/PC0011_00_Skeleton.PC0011_00_Skeleton";
    Config cfg;
    const char* file = R"({
      "schema": "RebirthSkelCompat/1",
      "families": [ { "skeletons": [ "/Game/Character/Player/PC0000_00_Cloud_Standard/Model/PC0000_00_Skeleton",
                                     "/Game/Character/Enemy/EB2020_00_Elena_Standard/Model/EB2020_00_Skeleton" ],
                      "hub": "/Game/Character/Player/PC0000_00_Cloud_Standard/Model/PC0000_00_Skeleton" } ],
      "animation_sets": [
        { "character": "PC0000_00_Cloud_Standard",
          "battle": [ { "from": "/Game/Motion/Enemy/EB0016_Rufus", "auto": true },
                      { "from": "/Game/Motion/NonPlayer/NP0000_Biggs/Battle00", "as": "Battle01", "match": "auto" },
                      { "from": "/Game/Motion/Enemy/EB2020_Elena", "auto": "basic" },
                      { "from": "/Game/Motion/Enemy/EB0000_X", "auto": "all" },
                      { "from": "/Game/Motion/Enemy/EB0001_Y", "auto": "sideways" },
                      "/Game/Motion/Player/PC0011_Vincent", "/Game/Motion/Player/PC0000_Cloud",
                      { "from": "/Game/Motion/Enemy/EB0016_Rufus", "auto": "all" } ],
          "moves": { "Neutral00/N_Atk01": [ "/Game/Motion/Enemy/EB2020_Elena/Battle00/B_AtkShot02_0",
                                             "/Game/Motion/Enemy/EB2020_Elena/Battle00/B_AtkShot02_1",
                                             "/Game/Motion/Enemy/EB2020_Elena/Battle00/B_AtkShot02_2" ],
                     "B_Single": [ "/Game/Motion/Enemy/EB2020_Elena/Battle00/B_AtkShot01_1" ],
                     "B_Bad": [ "/Game/Ok/A", 5 ] },
          "skeleton": "/Game/Character/Player/PC0011_00_Vincent_Standard/Model/PC0011_00_Skeleton",
          "cutscene": "/Game/Character/Player/PC0000_00_Cloud_Standard/Model/PC0000_00_Skeleton",
          "sockets": { "Attach_Weapon01": "Attach_Weapon_Right01", "Attach_Weapon_Left02": "L_Weapon_a", "bad.socket": "x", "Same": "same" },
          "proportions": true },
        { "character": "PC0002_00_Tifa_Standard", "sockets": [ { "socket": "Attach_Item", "use": "R_Hand_a" } ] },
        { "character": "PC0003_00_Aerith_Standard", "skeleton": "/Game/A/Aerith_Skeleton", "sockets": [ { "socket": "Attach_Item", "bone": "R_Hand_a" } ] }
      ]
    })";
    CHECK(AppendConfig(file, L"v32.json", cfg));
    CHECK(cfg.AnimSets.size() == 2); // Tifa's row has nothing left once its sockets (no skeleton) are dropped
    const AnimSetRow& row = cfg.AnimSets[0];
    CHECK(row.Battle.size() == 7);
    CHECK(row.Battle[0].Folder && row.Battle[0].Auto == AutoMatchMode::All); // listed again with "all": widened
    CHECK(!row.Battle[1].Folder && row.Battle[1].As == L"Battle01" && row.Battle[1].Auto == AutoMatchMode::Attacks);
    CHECK(row.Battle[2].Auto == AutoMatchMode::Basic && row.Battle[3].Auto == AutoMatchMode::All && row.Battle[4].Auto == AutoMatchMode::Attacks);
    CHECK(row.Battle[5].Auto == AutoMatchMode::Off && row.Battle[6].Auto == AutoMatchMode::Off);
    // Sources of Battle01: Rufus's folder falls back to its Battle00, Biggs's set fills Battle01, the folders add theirs.
    {
        const auto refs = SetSourcesFor(row, L"Battle01");
        CHECK(refs.size() == 7);
        CHECK(refs[0].Paths.size() == 2 && refs[0].Paths[0] == L"/Game/Motion/Enemy/EB0016_Rufus/Battle01.Battle01" &&
              refs[0].Paths[1] == L"/Game/Motion/Enemy/EB0016_Rufus/Battle00.Battle00" && refs[0].Auto == AutoMatchMode::All);
        CHECK(refs[1].Paths.size() == 1 && refs[1].Paths[0] == L"/Game/Motion/NonPlayer/NP0000_Biggs/Battle00.Battle00");
        CHECK(refs[4].Paths.size() == 2 && refs[4].Auto == AutoMatchMode::Attacks);
        CHECK(refs[5].Paths.size() == 1 && refs[5].Auto == AutoMatchMode::Off); // ordinary folders have no fallback
        const auto comp = SetSourcesFor(row, L"Battle01_Comp");
        CHECK(!comp.empty() && comp[0].Paths.size() == 1); // no fallback for _Comp sets
        CHECK(FirstSetOfKind(L"Battle01") == L"Battle00" && FirstSetOfKind(L"Neutral20") == L"Neutral00" && FirstSetOfKind(L"Battle00").empty() &&
              FirstSetOfKind(L"Battle01_Comp").empty());
    }
    // Chained moves.
    CHECK(row.Moves.size() == 2);
    CHECK(row.Moves[0].Set == L"Neutral00" && row.Moves[0].Key == L"N_Atk01" && row.Moves[0].Chain.size() == 3 &&
          row.Moves[0].Animation == L"/Game/Motion/Enemy/EB2020_Elena/Battle00/B_AtkShot02_0.B_AtkShot02_0" &&
          MoveAnimations(row.Moves[0]).size() == 3);
    CHECK(row.Moves[1].Key == L"B_Single" && row.Moves[1].Chain.empty() && MoveAnimations(row.Moves[1]).size() == 1);
    // Sockets.
    CHECK(row.Skeleton == vincentSkel);
    CHECK(row.Sockets.size() == 2 && row.Sockets[0].first == L"Attach_Weapon01" && row.Sockets[0].second == L"Attach_Weapon_Right01" &&
          row.Sockets[1].second == L"L_Weapon_a");
    CHECK(cfg.AnimSets[1].Sockets.size() == 1 && cfg.AnimSets[1].Sockets[0].second == L"R_Hand_a");
    CHECK(row.KeepProportions);
    // The cutscene family carries the row's proportions.
    const auto family = std::find_if(cfg.Pairs.begin(), cfg.Pairs.end(), [&](const Pair& p) { return p.Use == Method::Family && PathEquals(p.Receiving, vincentSkel); });
    CHECK(family != cfg.Pairs.end() && family->KeepProportions);

    FinishConfig(cfg, [](const std::wstring&) { return true; });
    // One family (Cloud hub; Elena and Vincent), proportions on for the whole family.
    const Pair* hub = cfg.FindForSkeleton(cloudSkel);
    CHECK(hub && hub->Use == Method::Animations && hub->KeepProportions && hub->Animation.size() == 2);
    const Pair* vincent = cfg.FindForSkeleton(vincentSkel);
    CHECK(vincent && vincent->Use == Method::Mesh && vincent->KeepProportions);
    const auto skeletons = cfg.ProportionSkeletons();
    CHECK(skeletons.size() == 1 && PathEquals(skeletons[0], cloudSkel));
    const auto aliases = cfg.SocketAliasesFor(L"/game/character/player/pc0011_00_vincent_standard/model/pc0011_00_skeleton.pc0011_00_skeleton");
    CHECK(aliases.size() == 2 && aliases[0].first == L"Attach_Weapon01");
    CHECK(cfg.SocketAliasesFor(cloudSkel).empty());
    CHECK(std::any_of(cfg.Messages.begin(), cfg.Messages.end(), [](const std::wstring& m) { return m.find(L"\"auto\" must be true") != std::wstring::npos; }));
    CHECK(std::any_of(cfg.Messages.begin(), cfg.Messages.end(), [](const std::wstring& m) { return m.find(L"sockets need") != std::wstring::npos; }));

    // An "override" row from a later file goes before the character's other rows.
    Config joined;
    CHECK(AppendConfig(R"({"schema":"RebirthSkelCompat/1","animation_sets":[{"character":"PC0000_00_Cloud_Standard",
        "battle":["/Game/Motion/Player/PC0011_Vincent","/Game/Motion/Player/PC0000_Cloud"],"field_actions":"PC0000_Cloud",
        "moves":{"B_X":"/Game/Base/X"}}]})", L"a_base.json", joined));
    CHECK(AppendConfig(R"({"schema":"RebirthSkelCompat/1","animation_sets":[{"character":"PC0000_00_Cloud_Standard","override":true,
        "battle":[{"from":"/Game/Motion/Enemy/EB0016_Rufus/Battle00","auto":true},"/Game/Motion/Player/PC0011_Vincent"],"field_actions":"PC0011_Vincent",
        "moves":{"B_X":"/Game/Test/X"}}]})", L"b_test.json", joined));
    FinishConfig(joined, [](const std::wstring&) { return true; });
    CHECK(joined.AnimSets.size() == 1);
    if (joined.AnimSets.size() == 1)
    {
        const AnimSetRow& j = joined.AnimSets[0];
        CHECK(j.Battle.size() == 3 && j.Battle[0].Auto == AutoMatchMode::Attacks && j.Battle[1].Path == L"/Game/Motion/Player/PC0011_Vincent" &&
              j.Battle[2].Path == L"/Game/Motion/Player/PC0000_Cloud");
        CHECK(j.FieldActions == L"PC0011_Vincent" && j.Moves.size() == 1 && j.Moves[0].Animation == L"/Game/Test/X.X");
    }

    // Limit breaks: by number or name, one animation or a chain; moves of the same name win.
    Config limits;
    CHECK(AppendConfig(R"({"schema":"RebirthSkelCompat/1","animation_sets":[
        {"character":"PC0000_00_Cloud_Standard","moves":{"B_AtkLimit03_0":"/Game/M/Three"},
         "limit_breaks":{"1":"/Game/L/One","2":["/Game/L/TwoA","/Game/L/TwoB"],"3":"/Game/L/Other","B_AtkLimit04_0":"/Game/L/Four","x":"/Game/L/Bad"}},
        {"character":"PC0001_00_Barret_Standard","limits":[null,"","/Game/B/Two"]}]})", L"limits.json", limits));
    CHECK(limits.AnimSets.size() == 2);
    if (limits.AnimSets.size() == 2)
    {
        const auto& m = limits.AnimSets[0].Moves;
        CHECK(m.size() == 4 && m[0].Key == L"B_AtkLimit03_0" && m[0].Animation == L"/Game/M/Three.Three");
        CHECK(m[1].Key == L"B_AtkLimit01_0" && m[1].Chain.empty() && m[2].Key == L"B_AtkLimit02_0" && m[2].Chain.size() == 2 && m[3].Key == L"B_AtkLimit04_0");
        const auto& b = limits.AnimSets[1].Moves;
        CHECK(b.size() == 1 && b[0].Key == L"B_AtkLimit03_0" && b[0].Animation == L"/Game/B/Two.Two" && b[0].Set.empty()); // the third entry
    }
    CHECK(std::any_of(limits.Messages.begin(), limits.Messages.end(), [](const std::wstring& m) { return m.find(L"also in \"moves\"") != std::wstring::npos; }));
    CHECK(std::any_of(limits.Messages.begin(), limits.Messages.end(), [](const std::wstring& m) { return m.find(L"limit_breaks: entries must") != std::wstring::npos; }));

    // Arrays everywhere: characters, sources with "only", moves, limit breaks, sockets, paks.
    Config arrays;
    CHECK(AppendConfig(R"({"schema":"RebirthSkelCompat/1","animation_sets":[
        {"characters":["PC0000_00_Cloud_Standard","PC0000_01_Cloud_Soldier"],
         "battle":[{"from":"/Game/Motion/Enemy/EB0016_Rufus/Battle00","auto":true,"only":["Shot","Gun"]},
                   {"from":"/Game/Motion/NonPlayer/NP0000_Biggs/Battle00","as":"Battle01","auto":"attacks","only":"Tonfa"},
                   {"from":"/Game/Motion/Enemy/EB2020_Elena","only":["Shot"]},
                   {"from":"/Game/Motion/Enemy/EB0016_Rufus/Battle00","auto":true,"only":["shot","Rifle"]},
                   {"from":"/Game/Motion/Enemy/EB0017_Z","auto":true,"only":[3]},
                   "/Game/Motion/Player/PC0011_Vincent"],
         "moves":[{"set":"Neutral00","key":"N_Atk01","animation":["/Game/E/B_AtkShot02_0","/Game/E/B_AtkShot02_1"]},
                  {"key":"B_Y","animation":"/Game/E/Y"},
                  {"set":"Battle00","key":"B_AtkLimit02_0","animation":"/Game/E/Mine"}],
         "limit_breaks":["/Game/R/One",["/Game/R/TwoA","/Game/R/TwoB"]],
         "skeleton":"/Game/Character/Player/PC0011_00_Vincent_Standard/Model/PC0011_00_Skeleton",
         "sockets":[{"socket":"Attach_Weapon01","use":"Attach_Weapon_Right01"},{"socket":"Attach_Weapon01","use":"Other"}],
         "requires_paks":["FullyPlayableVincentAssets_P"]}]})", L"arrays.json", arrays));
    CHECK(arrays.AnimSets.size() == 1);
    if (arrays.AnimSets.size() == 1)
    {
        const AnimSetRow& a = arrays.AnimSets[0];
        CHECK(a.Characters.size() == 2);
        CHECK(a.Battle.size() == 5);
        if (a.Battle.size() == 5)
        {
            // Rufus listed twice: either list's words count.
            CHECK(a.Battle[0].Only == (std::vector<std::wstring>{L"Shot", L"Gun", L"Rifle"}));
            CHECK(a.Battle[1].Only == std::vector<std::wstring>{L"Tonfa"} && a.Battle[1].As == L"Battle01");
            CHECK(a.Battle[2].Only.empty() && a.Battle[2].Auto == AutoMatchMode::Off); // "only" without "auto" is dropped
            CHECK(a.Battle[3].Only.empty() && a.Battle[3].Auto == AutoMatchMode::Attacks); // bad words dropped: every name
            const auto refs = SetSourcesFor(a, L"Battle00");
            CHECK(!refs.empty() && refs[0].Only.size() == 3);
        }
        CHECK(a.Moves.size() == 4);
        if (a.Moves.size() == 4)
        {
            CHECK(a.Moves[0].Set == L"Neutral00" && a.Moves[0].Key == L"N_Atk01" && a.Moves[0].Chain.size() == 2);
            CHECK(a.Moves[1].Set.empty() && a.Moves[1].Key == L"B_Y" && a.Moves[1].Animation == L"/Game/E/Y.Y");
            // "limit_breaks": limit 2 is already in "moves" (the move wins), so only limit 1 is added.
            CHECK(a.Moves[2].Set == L"Battle00" && a.Moves[2].Key == L"B_AtkLimit02_0");
            CHECK(a.Moves[3].Key == L"B_AtkLimit01_0" && a.Moves[3].Animation == L"/Game/R/One.One");
        }
        CHECK(a.Sockets.size() == 1 && a.Sockets[0].second == L"Attach_Weapon_Right01");
        CHECK(a.RequiresPaks.size() == 1);
    }
    CHECK(std::any_of(arrays.Messages.begin(), arrays.Messages.end(), [](const std::wstring& m) { return m.find(L"has no \"auto\"") != std::wstring::npos; }));
    CHECK(std::any_of(arrays.Messages.begin(), arrays.Messages.end(), [](const std::wstring& m) { return m.find(L"\"only\" must be") != std::wstring::npos; }));
    CHECK(std::any_of(arrays.Messages.begin(), arrays.Messages.end(), [](const std::wstring& m) { return m.find(L"sockets: Attach_Weapon01 is listed twice") != std::wstring::npos; }));

    // A family entry asking for proportions; a mesh pair outside a family.
    Config other;
    CHECK(AppendConfig(R"({"schema":"RebirthSkelCompat/1",
        "families":[{"skeletons":["/Game/A/A_Skel","/Game/B/B_Skel"],"keep_proportions":true}],
        "pairs":[{"method":"mesh","receiving_skeleton":"/Game/C/C_Skel","animation_skeleton":"/Game/D/D_Skel","proportions":true},
                 {"receiving_skeleton":"/Game/E/E_Skel","animation_skeleton":"/Game/F/F_Skel"}]})", L"o.json", other));
    FinishConfig(other, [](const std::wstring&) { return true; });
    const auto more = other.ProportionSkeletons();
    CHECK(more.size() == 2 && Detail::Lists(more, L"/Game/A/A_Skel.A_Skel") && Detail::Lists(more, L"/Game/D/D_Skel.D_Skel"));
}

static void TestProportions()
{
    // FF7R-style bones: Trans root, C_Hip_a pelvis, body chains, helpers, face, weapon.
    const std::vector<std::wstring> names{L"Trans",        L"C_Hip_a",      L"C_Spine_a",  L"C_Spine_b",   L"C_Neck_a",     L"C_Head_a",
                                          L"C_FaceBase",   L"L_Eye_a",      L"L_Shoulder_a", L"L_UpperArm_a", L"L_Forearm_a", L"L_Hand_a",
                                          L"L_Index_b",    L"R_Weapon_a",   L"L_UpperArm_a_Spo", L"C_HipW_End", L"L_UpperLeg_a", L"L_Foreleg_a",
                                          L"L_Foot_a",     L"L_Toe_a",      L"C_CharaA_a"};
    const std::vector<int32_t> parents{-1, 0, 1, 2, 3, 4, 5, 6, 3, 8, 9, 10, 11, 11, 9, 1, 1, 16, 17, 18, 0};
    const auto modes = ProportionModes(names, parents);
    CHECK(modes.size() == names.size());
    CHECK(modes[0] == RetargetMode::Keep && modes[1] == RetargetMode::AnimationScaled);
    for (size_t i : {2u, 3u, 4u, 5u, 8u, 9u, 10u, 11u, 12u, 16u, 17u, 18u, 19u}) { CHECK(modes[i] == RetargetMode::Skeleton); }
    for (size_t i : {6u, 7u, 13u, 14u, 15u, 20u}) { CHECK(modes[i] == RetargetMode::Keep); }
    // Without a hip name the root child with the most bones below it is the pelvis.
    const auto other = ProportionModes({L"root", L"prop", L"pelvis_x", L"spine"}, {-1, 0, 0, 2});
    CHECK(other[2] == RetargetMode::AnimationScaled);
    const auto plain = ProportionModes({L"root", L"a", L"b", L"c"}, {-1, 0, 2, 0});
    CHECK(plain[2] == RetargetMode::AnimationScaled || plain[1] == RetargetMode::AnimationScaled); // ties: either is fine
    CHECK(ProportionModes({L"root"}, {}).size() == 1);
    CHECK(DescribeModes(modes).find(L"13 body bone") != std::wstring::npos);

    // Retarget pose: the receiving pose with every carried-over bone replaced.
    const size_t stride = 8;
    std::vector<uint8_t> receiving(4 * stride), animation(3 * stride);
    for (size_t i = 0; i < receiving.size(); ++i) { receiving[i] = static_cast<uint8_t>(i); }
    for (size_t i = 0; i < animation.size(); ++i) { animation[i] = static_cast<uint8_t>(200 + i); }
    const auto pose = BuildRetargetPose(receiving, animation, {0, 2, -1}, stride);
    CHECK(pose.size() == receiving.size());
    CHECK(pose[0] == 200 && pose[stride] == receiving[stride] && pose[2 * stride] == 200 + stride && pose[3 * stride] == receiving[3 * stride]);
    CHECK(BuildRetargetPose(receiving, animation, {0, 1}, stride).empty());
    CHECK(BuildRetargetPose(receiving, animation, {0, 9, 1}, stride)[stride] == 200 + 2 * stride);
}

static void TestNameKeyedMaps()
{
    const auto read = [](void* to, const void* from, size_t size) { std::memcpy(to, from, size); return true; };
    std::vector<void*> blocks;
    const auto alloc = [&](size_t size) { void* p = std::malloc(size); blocks.push_back(p); return p; };
    const auto release = [&](void* p) { blocks.erase(std::find(blocks.begin(), blocks.end(), p)); std::free(p); };
    for (const int n : {1, 2, 5, 40, 129})
    {
        std::vector<uint64_t> keys;
        std::vector<uint8_t> values;
        for (int i = 0; i < n; ++i)
        {
            keys.push_back((static_cast<uint64_t>(i * 37 + 5) << 16) | static_cast<uint64_t>(i * 3 + 1));
            for (int b = 0; b < 24; ++b) { values.push_back(static_cast<uint8_t>(i + b)); }
        }
        for (const bool handle : {true, false})
        {
            SetHeader header;
            CHECK(BuildNameKeyedMap(keys, values, 24, handle, alloc, release, header));
            std::vector<uint64_t> backKeys;
            std::vector<uint8_t> backValues;
            std::wstring why;
            CHECK(ReadNameKeyedMap(header, 24, handle, read, backKeys, backValues, why) && backKeys == keys && backValues == values);
            if (n >= 40) { CHECK(!ReadNameKeyedMap(header, 24, !handle, read, backKeys, backValues, why)); } // the other hash form does not fit
            for (void* block : {header.Elements, static_cast<void*>(header.HeapFlags), static_cast<void*>(header.HeapHash)})
            {
                if (block) { release(block); }
            }
        }
    }
    CHECK(blocks.empty());
    std::vector<uint64_t> k;
    std::vector<uint8_t> v;
    std::wstring why;
    SetHeader empty{};
    empty.InlineHash = -1;
    CHECK(IsEmptyMapHeader(SetHeader{}) && IsEmptyMapHeader(empty));
    CHECK(ReadNameKeyedMap(SetHeader{}, 24, true, read, k, v, why) && k.empty());
    SetHeader junk{};
    junk.Num = 3;
    CHECK(!ReadNameKeyedMap(junk, 24, true, read, k, v, why));
    CHECK(!BuildNameKeyedMap({1}, {1, 2, 3}, 24, true, alloc, release, junk));
}

static void TestAbilities()
{
    Config cfg;
    const char* file = R"({
      "schema": "RebirthSkelCompat/1",
      "animation_sets": [
        { "characters": [ "PC0000_00_Cloud_Standard", "PC0000_08_Cloud_SoldierNoHelmet" ],
          "player": "pt_Cloud",
          "abilities": [ { "pack": "Battle00", "commands": [ "PC0010_AtkBurst01", "PC0010_AtkBurst02" ], "limits": [ "PC0010_Limit001" ] },
                         { "pack": "Battle02", "commands": [ "PC0010_W_Tenshi", "PC0010_W_Tenshi", "bad name" ] },
                         { "pack": "Battle03", "limits": [] },
                         { "pack": "Battle02", "commands": [ "PC0010_AtkBurst01" ] },
                         { "pack": "Battle70" } ] },
        { "character": "PC0000_00_Cloud_Standard", "player": "pt_Cloud",
          "preload": [ "/Game/DataAsset/Game/CharaSpec/CharaSpec_FA0260_01_SephirothMeteor_Battle" ],
          "pack_assets": "/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Build/PC0010_10_Sephiroth_Transform_Effect__Pack",
          "abilities": { "Battle03": [ "Ignored_Earlier_Row_Wins" ], "Battle70": { "atb": [ "KH2_Sin_Harvest" ], "limit": "KH2_Meteor" } } },
        { "character": "PC0003_00_Aerith_Standard", "preload": "/Game/A/B", "refresh_abilities": false },
        { "character": "PC0004_00_RedXIII_Standard", "pack_assets": [ "/Game/E/P", 3 ] },
        { "character": "PC0005_00_Yuffie_Standard", "pack_assets": [ "/Game/E/Q" ] },
        { "character": "PC0003_00_Aerith_Standard", "refresh_abilities": "no" },
        { "character": "PC0001_00_Barret_Standard", "abilities": [ { "pack": "Battle00", "commands": [ "PC0001_AtkBurst01" ] } ] },
        { "character": "PC0002_00_Tifa_Standard", "player": "pt Tifa", "moves": { "B_X": "/Game/A/B" } }
      ]
    })";
    CHECK(AppendConfig(file, L"abilities.json", cfg));
    FinishConfig(cfg, [](const std::wstring&) { return true; });
    const AnimSetRow* cloud = cfg.FindAnimSetRow(CharacterPackPath(L"PC0000_00_Cloud_Standard"));
    CHECK(cloud && cloud->Player == L"pt_Cloud");
    CHECK(cloud && cloud->Abilities.size() == 4); // Battle00, Battle02, Battle03 from the first row; Battle70 from the second
    if (cloud && cloud->Abilities.size() == 4)
    {
        const PackAbilities& normal = cloud->Abilities[0];
        CHECK(normal.Pack == L"Battle00" && normal.HasCommands && normal.HasLimits);
        CHECK(normal.Commands.size() == 2 && normal.Commands[1] == L"PC0010_AtkBurst02" && normal.Limits.size() == 1);
        const PackAbilities& winged = cloud->Abilities[1];
        CHECK(winged.Commands.size() == 1 && winged.Commands[0] == L"PC0010_W_Tenshi" && !winged.HasLimits); // twice + a bad name
        const PackAbilities& flying = cloud->Abilities[2];
        CHECK(flying.HasLimits && flying.Limits.empty() && !flying.HasCommands); // an empty list empties the limits
        const PackAbilities& kh2 = cloud->Abilities[3];
        CHECK(kh2.Pack == L"Battle70" && kh2.Commands.size() == 1 && kh2.Limits.size() == 1 && kh2.Limits[0] == L"KH2_Meteor");
        CHECK(cloud->AbilitiesFor(L"battle02") == &winged);
        CHECK(cloud->AbilitiesFor(L"Battle05") == &normal); // no entry: the default pack's
        std::wstring from;
        CHECK(cloud->ListFor(L"Battle02", false, &from) == &winged.Commands && from == L"Battle02");
        CHECK(cloud->ListFor(L"Battle02", true, &from) == &normal.Limits && from == L"Battle00"); // Battle02 lists no limits
        CHECK(cloud->ListFor(L"Battle03", true) == &flying.Limits && cloud->ListFor(L"Battle03", false) == &normal.Commands);
        CHECK(cloud->ListFor(L"Battle99", false) == &normal.Commands);
    }
    {
        AnimSetRow none;
        none.Abilities.push_back(PackAbilities{L"Battle02", {L"A"}, {}, true, false, {}, false});
        CHECK(none.ListFor(L"Battle00", false) == nullptr && none.ListFor(L"Battle02", true) == nullptr);
        CHECK(none.ListFor(L"Battle02", false) && none.ListFor(L"Battle02", false)->front() == L"A");
    }
    CHECK(cloud && cloud->Preload.size() == 1 &&
          cloud->Preload[0] == L"/Game/DataAsset/Game/CharaSpec/CharaSpec_FA0260_01_SephirothMeteor_Battle.CharaSpec_FA0260_01_SephirothMeteor_Battle");
    const AnimSetRow* aerith = cfg.FindAnimSetRow(CharacterPackPath(L"PC0003_00_Aerith_Standard"));
    CHECK(aerith && aerith->Preload.size() == 1 && aerith->Preload[0] == L"/Game/A/B.B"); // a row may only preload
    CHECK(aerith && !aerith->RefreshAbilities && cloud && cloud->RefreshAbilities);
    CHECK(cloud && cloud->PackAssets.size() == 1 &&
          cloud->PackAssets[0] == L"/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Build/PC0010_10_Sephiroth_Transform_Effect__Pack."
                                  L"PC0010_10_Sephiroth_Transform_Effect__Pack");
    CHECK(!cfg.FindAnimSetRow(CharacterPackPath(L"PC0004_00_RedXIII_Standard"))); // a bad list: nothing left in the row
    const AnimSetRow* yuffie = cfg.FindAnimSetRow(CharacterPackPath(L"PC0005_00_Yuffie_Standard"));
    CHECK(yuffie && yuffie->PackAssets.size() == 1 && yuffie->PackAssets[0] == L"/Game/E/Q.Q"); // a row may only add pack assets
    const AnimSetRow* soldier = cfg.FindAnimSetRow(CharacterPackPath(L"PC0000_08_Cloud_SoldierNoHelmet"));
    CHECK(soldier && soldier->Player == L"pt_Cloud" && soldier->Abilities.size() == 3 && soldier->Preload.empty());
    CHECK(soldier && soldier->PackAssets.empty()); // only the second row's character gets them
    CHECK(!cfg.FindAnimSetRow(CharacterPackPath(L"PC0001_00_Barret_Standard"))); // abilities without a player row: nothing left
    const AnimSetRow* tifa = cfg.FindAnimSetRow(CharacterPackPath(L"PC0002_00_Tifa_Standard"));
    CHECK(tifa && tifa->Player.empty() && tifa->Abilities.empty());
    const auto mentions = [&](const wchar_t* text) {
        return std::any_of(cfg.Messages.begin(), cfg.Messages.end(), [&](const std::wstring& m) { return m.find(text) != std::wstring::npos; });
    };
    CHECK(mentions(L"PC0010_W_Tenshi is listed twice"));
    CHECK(mentions(L"pack Battle02 is listed twice"));
    CHECK(mentions(L"abilities need the character's \"player\" row"));
    CHECK(mentions(L"must be a BattlePlayerParameter row"));
    CHECK(mentions(L"refresh_abilities must be true or false"));
    CHECK(mentions(L"pack_assets: entries must be object paths"));
    CHECK(!mentions(L"the game takes the first"));
    {
        Config many;
        CHECK(AppendConfig(R"({"schema": "RebirthSkelCompat/1", "animation_sets": [{"character": "PC0000_00_Cloud_Standard", "player": "pt_Cloud",
            "abilities": {"Battle02": {"commands": ["A1", "A2", "A3", "A4", "A5", "A6"], "limits": ["L1", "L2", "L3", "L4"]}}}]})",
                           L"many.json", many));
        FinishConfig(many, [](const std::wstring&) { return true; });
        const auto said = [&](const wchar_t* text) {
            return std::any_of(many.Messages.begin(), many.Messages.end(), [&](const std::wstring& m) { return m.find(text) != std::wstring::npos; });
        };
        CHECK(said(L"pack Battle02 lists 6 commands; the game takes the first 5"));
        CHECK(said(L"pack Battle02 lists 4 limits; the game takes the first 3"));
        const AnimSetRow* row = many.FindAnimSetRow(CharacterPackPath(L"PC0000_00_Cloud_Standard"));
        CHECK(row && row->Abilities.size() == 1 && row->Abilities[0].Commands.size() == 6); // kept whole; the mod writes the first 5
    }
    // 3.4: weapon abilities per pack (the ability a weapon gives -> the ability it gives in that pack)
    {
        Config w;
        CHECK(AppendConfig(R"({"schema": "RebirthSkelCompat/1", "animation_sets": [{"character": "PC0000_00_Cloud_Standard", "player": "pt_Cloud",
            "abilities": [
              {"pack": "Battle00", "weapon_abilities": {"PC0000_AtkBurst02": "PC0000_AtkBurst02"}},
              {"pack": "Battle02", "commands": ["PC0010_T_ShadowFlare"],
               "weapon_abilities": {"PC0000_AtkBurst02": "PC0010_W2_Blizzaga", "PC0000_AtkBurst08": "PC0010_W2_ZanshinRising", "bad name": "X",
                                    "PC0000_AtkBurst07": 5}},
              {"pack": "Battle03", "weapons": [["PC0000_AtkBurst02", "PC0010_W3_DoubleBlizzaga"],
                                              {"weapon": "PC0000_AtkBurst08", "ability": "PC0010_W3_DoubleFiraga"},
                                              {"from": "PC0000_AtkBurst02", "to": "Twice"}, 7]},
              {"pack": "Battle04", "weapon_abilities": {}}]}]})",
                           L"weapons.json", w));
        FinishConfig(w, [](const std::wstring&) { return true; });
        const auto said = [&](const wchar_t* text) {
            return std::any_of(w.Messages.begin(), w.Messages.end(), [&](const std::wstring& m) { return m.find(text) != std::wstring::npos; });
        };
        const AnimSetRow* row = w.FindAnimSetRow(CharacterPackPath(L"PC0000_00_Cloud_Standard"));
        CHECK(row && row->Abilities.size() == 4);
        if (row && row->Abilities.size() == 4)
        {
            const auto& normal = row->Abilities[0];
            const auto& winged = row->Abilities[1];
            const auto& flying = row->Abilities[2];
            const auto& empty = row->Abilities[3];
            CHECK(normal.HasWeapons && !normal.HasCommands && !normal.HasLimits && normal.Weapons.size() == 1); // weapons alone make an entry
            CHECK(winged.Weapons.size() == 2 && winged.Weapons[0].first == L"PC0000_AtkBurst02" && winged.Weapons[0].second == L"PC0010_W2_Blizzaga");
            CHECK(winged.Weapons[1].second == L"PC0010_W2_ZanshinRising" && winged.HasCommands);
            CHECK(flying.Weapons.size() == 2 && flying.Weapons[1].first == L"PC0000_AtkBurst08" && flying.Weapons[1].second == L"PC0010_W3_DoubleFiraga");
            CHECK(empty.HasWeapons && empty.Weapons.empty());
            std::wstring from;
            CHECK(row->WeaponsFor(L"battle02", &from) == &winged.Weapons && from == L"Battle02");
            CHECK(row->WeaponsFor(L"Battle05", &from) == &normal.Weapons && from == L"Battle00"); // no entry: the default pack's
            CHECK(row->WeaponsFor(L"Battle04") == &empty.Weapons);                              // its own (empty): the weapons' own
            CHECK(row->ListFor(L"Battle04", false) == nullptr);                                  // weapons only: no command list
        }
        CHECK(said(L"weapon_abilities must map"));
        CHECK(said(L"weapon_abilities lists PC0000_AtkBurst02 twice"));
        AnimSetRow plain;
        plain.Abilities.push_back(PackAbilities{L"Battle02", {L"A"}, {}, true, false, {}, false});
        CHECK(plain.WeaponsFor(L"Battle02") == nullptr && plain.WeaponsFor(L"Battle00") == nullptr);
    }
    // EPlayerType of the party's player rows
    CHECK(PlayerTypeOf(L"pt_Cloud") == 0 && PlayerTypeOf(L"PT_CLOUD") == 0 && PlayerTypeOf(L"pt_RedXIII") == 4);
    CHECK(PlayerTypeOf(L"pt_CaitSith") == 6 && PlayerTypeOf(L"pt_Sephiroth") == 8 && PlayerTypeOf(L"pt_AerithAge7") == 11);
    CHECK(PlayerTypeOf(L"pt_Toad") == -1 && PlayerTypeOf(L"Cloud") == -1 && PlayerTypeOf(L"pt_") == -1 && PlayerTypeOf(L"") == -1);

    // Frozen tables: the game's BattlePlayerParameter and BattleAbility rows.
    const auto fields = [](std::initializer_list<std::pair<const wchar_t*, int32_t>> list) {
        std::vector<Frozen::Field> out;
        for (const auto& [name, type] : list) { out.push_back(Frozen::Field{name, type}); }
        return out;
    };
    auto player = fields({{L"UniqueAbilityParameterName_Array", 11}, {L"KeyAssignAbilityID_Array", 11}, {L"CombinationTableID_Array", 11},
                          {L"GuardParameterName_Array", 11}, {L"DodgeReactionInfluenceID_Array", 11}, {L"DodgeParameterName_Array", 11},
                          {L"LimitAbilityID_Array", 11}, {L"LimitAbilityUseableFlag_Array", 11}, {L"FirstLimitAbilityUseableFlag_Array", 11},
                          {L"CommandAbilityID_Array", 11}, {L"GuardParameterValue_Array", 9}, {L"DodgeParameterValue_Array", 9},
                          {L"UniqueAbilityParameterValue_Array", 9}, {L"DodgeType_Array", 2}, {L"KeyAssignGuardAbilityID0", 11},
                          {L"DodgeNeutralAbilityID1", 11}, {L"MugAbilityID", 11}, {L"ControlCharacterChangeAbilityID", 11},
                          {L"KeyDownEffectSocketName", 11}, {L"KeyDownEffectCreateTime", 9}, {L"KeyDownTime", 9}, {L"UniqueAbilityType0", 2},
                          {L"EnableKeyAssiginGuardAbility0", 2}, {L"GuardType0", 2}, {L"EnableAerialShortCut", 2}});
    int32_t rowSize = 0;
    CHECK(Frozen::Layout(player, rowSize) && rowSize == 280);
    CHECK(Frozen::Find(player, L"CommandAbilityID_Array") && Frozen::Find(player, L"CommandAbilityID_Array")->Offset == 144);
    CHECK(Frozen::Find(player, L"LimitAbilityID_Array")->Offset == 96 && Frozen::Find(player, L"LimitAbilityID_Array")->Array);
    CHECK(Frozen::Find(player, L"EnableAerialShortCut")->Offset == 275 && !Frozen::Find(player, L"EnableAerialShortCut")->Array);
    auto ability = fields({{L"AddAnimationName_Array", 11}, {L"ReactionParameterString_Array", 11}, {L"ResourceID_Array", 11}, {L"ResourceName_Array", 11},
                           {L"AnimationString_Array", 11}, {L"AddAnimationPlayInterval_Array", 9}, {L"ReactionConditionParameterValue_Array", 9},
                           {L"ReactionParameterValue_Array", 9}, {L"AnimationParameter_Array", 9}, {L"AnimationSelectType_Array", 2},
                           {L"AddAnimationIndex_Array", 2}, {L"AddAnimationPlayCount_Array", 2}, {L"AddAnimationEndBase_Array", 2},
                           {L"ReactionCondition_Array", 2}, {L"ReactionConditionNotifyIndex_Array", 2}, {L"ReactionType_Array", 2},
                           {L"CancelNumber_Array", 2}, {L"Explanation", 10}, {L"ReplaceDamageSourceID", 10}, {L"Name", 10},
                           {L"AnimResourceReferenceBattleCharaSpecID", 11}, {L"AnimationUpperBodyName", 11}, {L"CameraSequenceID", 11},
                           {L"UseSoundResourceName", 11}, {L"ReactionInfluenceID", 11}, {L"Flag0", 8}, {L"MP", 7}, {L"SortId", 7}, {L"UniqueId", 7},
                           {L"InputBufferTime", 9}, {L"ATB", 9}, {L"Range", 9}, {L"SameCharacterDamageHitDamageCoefficient", 9},
                           {L"SameCharacterDamageHitDamageCoefficientMin", 9}, {L"TeleportParam", 9}, {L"TeleportMinDistance", 9}, {L"ShowNameSecond", 9},
                           {L"ShowName", 2}, {L"CommandType", 2}, {L"CommandTargetType", 2}, {L"UsePlace", 2}, {L"CastMagicEffectType", 2},
                           {L"AnimationBoneFilterIndexBits0", 2}, {L"SkeletonControlType", 2}, {L"TargetCount", 2}, {L"TargetAimPosition", 2},
                           {L"TargetCloseMove", 2}, {L"TargetCorrectionDirectionImmediatelyType", 2}, {L"DamageCreateMoveCollisionObjectOff", 2},
                           {L"CameraSequenceNotify", 2}, {L"KeepValue", 2}, {L"DistFeelType", 2}, {L"UseSoundResourceCategory", 2}, {L"AfterWalkType", 2},
                           {L"TeleportType", 2}, {L"AfterTeleportRotationType", 2}, {L"ActionCategory", 2}, {L"ForceDamageDisplayToOne", 2},
                           {L"StrengthenNumber", 2}});
    CHECK(Frozen::Layout(ability, rowSize) && rowSize == 440);
    CHECK(Frozen::Find(ability, L"Name")->Offset == 304 && Frozen::Find(ability, L"Flag0")->Offset == 360 && Frozen::Find(ability, L"ATB")->Offset == 384);
    auto bad = fields({{L"X", 12}});
    CHECK(!Frozen::Layout(bad, rowSize));
    // 3.4: the game's Equipment rows (weapons): BurstAbilityID, the ability a weapon gives, at 0x158.
    auto equipment = fields({{L"SkillTextLabel_Array", 10}, {L"SkillEffectName_Array", 11}, {L"SkillEffectTextInfoID_Array", 11}, {L"CharaSpecID_Array", 11},
        {L"CanEquip_Array", 11}, {L"SkillEffectValue_Array", 9}, {L"SkillConditionValue_Array", 9}, {L"LearningConditionValue_Array", 7},
        {L"SkillCoreSlotMax_Array", 7}, {L"SkillEffectType_Array", 7}, {L"StatusChangeResist_Array", 2}, {L"SpecialResist_Array", 2},
        {L"SkillConditionType_Array", 2}, {L"MateriaSlotModify_Array", 2}, {L"ModelMateriaIndex_Array", 2}, {L"LearningConditionType_Array", 2},
        {L"AttributeResist_Array", 2}, {L"OverrideBurstAbilityHelpText", 10}, {L"LearningConditionText", 10}, {L"OverrideBurstAbilityText", 10},
        {L"OverrideGuardBeginSequeceName", 11}, {L"OverrideGuardLoopSequeceName", 11}, {L"OverrideGuardEndSequeceName", 11}, {L"BurstAbilityID", 11},
        {L"LearningCounterID", 11}, {L"LearningFlag", 11}, {L"FieldAttackStateTriggerId", 11}, {L"MovieName", 11}, {L"UpgradeID", 11}, {L"AttackScale", 7},
        {L"MagicAttackAdd", 7}, {L"MagicAttackScale", 7}, {L"DefenseAdd", 7}, {L"DefenseScale", 7}, {L"MagicDefenseAdd", 7}, {L"MagicDefenseScale", 7},
        {L"StrengthAdd", 7}, {L"StrengthScale", 7}, {L"MagicAdd", 7}, {L"MagicScale", 7}, {L"VitalityAdd", 7}, {L"VitalityScale", 7}, {L"SpiritAdd", 7},
        {L"SpiritScale", 7}, {L"LuckAdd", 7}, {L"LuckScale", 7}, {L"DexterityAdd", 7}, {L"DexterityScale", 7}, {L"HPMaxAdd", 7}, {L"HPMaxScale", 7},
        {L"MPMaxAdd", 7}, {L"MPMaxScale", 7}, {L"CriticalHitRateAdd", 7}, {L"CriticalHitRateScale", 7}, {L"LearningCondAddPoint", 7},
        {L"LearningCondUseCount", 7}, {L"SkillCoreSlotNum", 7}, {L"AttackAdd", 7}, {L"LongAttackRange", 9}, {L"MateriaGrowScale", 9},
        {L"PropertyResist1", 2}, {L"BreakDead", 2}, {L"MateriaSlotDouble", 2}, {L"MateriaSlotSingle", 2}, {L"NormalAttackReach", 2}, {L"PropertyResist0", 2}});
    CHECK(Frozen::Layout(equipment, rowSize) && rowSize == 0x210);
    CHECK(Frozen::Find(equipment, L"BurstAbilityID")->Offset == 0x158 && Frozen::Find(equipment, L"LearningCounterID")->Offset == 0x160);
    // The game's two weapon ability lookups (ff7rebirth_.exe 7ffde5 in the status recalculation's list, 7ff227 in the
    // menus' list): the Equipment table, the row lookup, BurstAbilityID.
    {
        const uint8_t site1[] = {0x48, 0x8D, 0x0D, 0x04, 0x1D, 0x86, 0x08, 0xE8, 0x3F, 0xA5, 0xF6, 0xFF, 0x4C, 0x8B, 0xE8, 0x48, 0x85, 0xC0, 0x0F, 0x84,
                                 0x0C, 0x01, 0x00, 0x00, 0x48, 0x8B, 0x88, 0x58, 0x01, 0x00, 0x00};
        const uint8_t site2[] = {0x48, 0x8D, 0x0D, 0xC2, 0x28, 0x86, 0x08, 0xE8, 0xFD, 0xB0, 0xF6, 0xFF, 0x4C, 0x8B, 0xE8, 0x48, 0x85, 0xC0, 0x0F, 0x84,
                                 0x95, 0x00, 0x00, 0x00, 0x48, 0x8B, 0x88, 0x58, 0x01, 0x00, 0x00};
        static_assert(sizeof(site1) == Frozen::WeaponRowCallSize && sizeof(site2) == Frozen::WeaponRowCallSize, "one match each");
        Frozen::WeaponRowCall one{}, two{};
        CHECK(Frozen::IsWeaponRowCall(site1, sizeof(site1), &one) && Frozen::IsWeaponRowCall(site2, sizeof(site2), &two));
        CHECK(one.Field == 0x158 && two.Field == 0x158 && one.Call == 7 && two.Call == 7);
        CHECK(0x7ffde5 + one.Table == 0x9061af0 && 0x7ff227 + two.Table == 0x9061af0); // the Equipment table, from both
        CHECK(0x7ffde5 + one.Lookup == 0x76a330 && 0x7ff227 + two.Lookup == 0x76a330); // the same lookup
        uint8_t broken[sizeof(site1)];
        std::memcpy(broken, site1, sizeof(site1));
        broken[14] = 0xE0; // mov r12,rax
        CHECK(!Frozen::IsWeaponRowCall(broken, sizeof(broken)));
        CHECK(!Frozen::IsWeaponRowCall(site1, sizeof(site1) - 1));
        std::memcpy(broken, site1, sizeof(site1));
        broken[27] = 0x5C; // a field off 8 bytes
        CHECK(!Frozen::IsWeaponRowCall(broken, sizeof(broken)));
        std::memcpy(broken, site1, sizeof(site1));
        broken[26] = 0x90; // mov rdx,[rax+..]
        CHECK(!Frozen::IsWeaponRowCall(broken, sizeof(broken)));
    }
    // The game's getters of BattlePlayerParameter list entries (ff7rebirth_.exe): commands (array at 0x90), limits (0x60)
    // and limit flags (0x70).
    {
        const auto hex = [](const char* text) {
            std::vector<uint8_t> out;
            for (size_t i = 0; text[i] && text[i + 1]; i += 2)
            {
                const auto nibble = [](char c) { return static_cast<uint8_t>(c <= '9' ? c - '0' : c - 'a' + 10); };
                out.push_back(static_cast<uint8_t>(nibble(text[i]) << 4 | nibble(text[i + 1])));
            }
            return out;
        };
        const char* commands[] = {
            "488b490883b998000000007f0c488b0550cd8508488902eb204881c190000000488b01a801740648d1f84803c1488b00890248c1e820894204488bc2c3cccccc",
            "488b490883b998000000017f0c488b0590cd8508488902eb214881c190000000488b01a801740648d1f84803c1488b4008890248c1e820894204488bc2c3cccc",
            "488b490883b998000000027f0c488b05e8ce8508488902eb214881c190000000488b01a801740648d1f84803c1488b4010890248c1e820894204488bc2c3cccc",
            "488b490883b998000000037f0c488b0568cf8508488902eb214881c190000000488b01a801740648d1f84803c1488b4018890248c1e820894204488bc2c3cccc",
            "488b490883b998000000047f0c488b0528cf8508488902eb214881c190000000488b01a801740648d1f84803c1488b4020890248c1e820894204488bc2c3cccc"};
        const char* limits[] = {
            "488b4908837968007f0c488b0567406b08488902eb1d4883c160488b01a801740648d1f84803c1488b00890248c1e820894204488bc2c3cc803d72855808000f",
            "488b4908837968017f0c488b054b862d08488902eb1e4883c160488b01a801740648d1f84803c1488b4008890248c1e820894204488bc2c348895c241048897c",
            "488b4908837968027f0c488b0583862d08488902eb1e4883c160488b01a801740648d1f84803c1488b4010890248c1e820894204488bc2c3488b490883796801"};
        const auto flag0 = hex("488b4908837978007f0c488b056f5d7008488902eb1d4883c170488b01a801740648d1f84803c1488b00890248c1e820894204488bc2c3cc488b490883793803");
        for (int32_t k = 0; k < 5; ++k)
        {
            const auto code = hex(commands[k]);
            size_t none = 0;
            CHECK(Frozen::IsNameEntryGetter(code.data(), code.size(), 0x90, k, &none) && none == 16);
            for (int32_t other = 0; other < 5; ++other)
            {
                if (other != k) { CHECK(!Frozen::IsNameEntryGetter(code.data(), code.size(), 0x90, other)); }
            }
            CHECK(!Frozen::IsNameEntryGetter(code.data(), code.size(), 0x60, k) && !Frozen::IsNameEntryGetter(code.data(), 40, 0x90, k));
        }
        for (int32_t k = 0; k < 3; ++k)
        {
            const auto code = hex(limits[k]);
            size_t none = 0;
            CHECK(Frozen::IsNameEntryGetter(code.data(), code.size(), 0x60, k, &none) && none == 13);
            CHECK(!Frozen::IsNameEntryGetter(code.data(), code.size(), 0x70, k) && !Frozen::IsNameEntryGetter(code.data(), code.size(), 0x90, k));
        }
        CHECK(Frozen::IsNameEntryGetter(flag0.data(), flag0.size(), 0x70, 0) && !Frozen::IsNameEntryGetter(flag0.data(), flag0.size(), 0x60, 0));
        auto broken = hex(commands[2]);
        broken[48] ^= 0xFF; // the element load
        CHECK(!Frozen::IsNameEntryGetter(broken.data(), broken.size(), 0x90, 2));
    }
    // Frozen pointers are relative to where they are stored, both ways.
    const uintptr_t at = 0x10000, target = 0x8000;
    CHECK(Frozen::Resolve(at, Frozen::Encode(at, target)) == target);
    CHECK(Frozen::Resolve(at, Frozen::Encode(at, 0x123450)) == 0x123450);
    CHECK(Frozen::Resolve(at, 0x5000) == 0x5000 && Frozen::Resolve(at, 0) == 0);
}

static bool HasMessage(const Config& cfg, const wchar_t* part)
{
    return std::any_of(cfg.Messages.begin(), cfg.Messages.end(), [&](const std::wstring& m) { return m.find(part) != std::wstring::npos; });
}

static void TestForms()
{
    Config cfg;
    const char* file = R"({
      "schema": "RebirthSkelCompat/1",
      "animation_sets": [
        { "characters": [ "PC0000_00_Cloud_Standard", "PC0000_08_Cloud_SoldierNoHelmet" ],
          "battle": [ { "from": "/Game/Motion/Player/PC0010_Sephiroth_Transform/Battle00.Battle00", "as": "Battle02" } ],
          "forms": { "button": "Gamepad_FaceButton_Top", "key": "T", "hold_seconds": 0.5, "title": "MOVESET",
                     "parts": [ "PC0010_10_Wing", "Wing", "bad slot" ], "fade_seconds": 0.6, "effect_seconds": 3,
                     "show_effects": [ { "effect": "/Game/Effect/Cut/FX_Feather", "socket": "R_FeatherShoulder_a" } ],
                     "hide_effects": "/Game/Effect/Cut/FX_Feather",
                     "list": [
                       { "name": "NORMAL", "effects": "/Game/Effect/FX_Aura" },
                       { "name": "WINGED", "pack": "Battle02", "show": [ "PC0010_10_Wing", "Wing" ],
                         "effects": [ { "effect": "/Game/Effect/FX_Wing", "scale": 1.5, "seconds": 2 } ],
                         "sounds": [ { "bank": "/Game/Sound/SE/SE_PC0010", "cue": "SE_Whoosh" },
                                     { "voice": "/Game/Sound/Voice/{language}/Character/Player/VO_PC0010_00_Sephiroth", "cue": "Atk_Ability_02" } ] },
                       { "name": "FLYING", "pack": "Battle03", "show": "Cape", "fly": { "height": 300, "speed": 500, "up": "Gamepad_RightShoulder" },
                         "after": "PC0000_Limit002" },
                       { "name": "KH2", "pack": "Battle04", "model": "/Game/Character/Player/KH2/SK_KH2Sephiroth", "fly": true,
                         "anim_class": "/Game/BluePrint/Animation/Enemy/ABP_Big", "scale": 0.25, "hide_weapon": true,
                         "meshes": [ "/Game/Character/Enemy/W/Wing", { "mesh": "/Game/Character/Enemy/F/Face.Face", "socket": "C_Head_a", "follow_pose": false } ],
                         "keep_effects": { "effect": "/Game/Effect/FX_Sword", "socket": "R_Hand_a" },
                         "ability_effects": [ { "ability": "PC0010_BZ_Octaslash", "effects": { "effect": "/Game/Effect/FX_OmniSword", "socket": "Attack_Sword" } },
                                              { "abilities": [ "PC0010_NAtk_*", "bad name!" ], "effects": "/Game/Effect/FX_LongSword" },
                                              { "ability": "PC0010_Nothing" } ] },
                       { "name": "BAD", "pack": "Neutral00" },
                       "Battle05"
                     ] } },
        { "character": "PC0000_00_Cloud_Standard", "forms": [ { "name": "IGNORED" }, { "pack": "Battle09" } ] },
        { "character": "PC0002_00_Tifa_Standard", "forms": [ "Battle02" ] },
        { "character": "PC0001_00_Barret_Standard", "forms": [ { "name": "A" }, "Battle01", "Battle02", "Battle03", "Battle04", "Battle05",
                                                              "Battle06", "Battle07", "Battle08", "Battle09", "Battle10", "Battle11", "Battle12",
                                                              "Battle13", "Battle14" ] },
        { "character": "PC0003_00_Aerith_Standard", "forms": { "list": [ { "pack": "Battle02" }, { "name": "B", "pack": "Battle03" } ] } }
      ]
    })";
    CHECK(AppendConfig(file, L"forms.json", cfg));
    FinishConfig(cfg, [](const std::wstring&) { return true; });
    const AnimSetRow* cloud = cfg.FindAnimSetRow(CharacterPackPath(L"PC0000_00_Cloud_Standard"));
    CHECK(cloud && cloud->Forms.HasList());
    if (cloud && cloud->Forms.List.size() == 5)
    {
        const FormSettings& f = cloud->Forms;
        CHECK(f.Button == L"Gamepad_FaceButton_Top" && f.Key == L"T" && f.HoldSeconds == 0.5f && f.Title == L"MOVESET");
        CHECK(f.Parts.size() == 3 && f.Parts[0] == L"PC0010_10_Wing" && f.Parts[1] == L"Wing" && f.Parts[2] == L"Cape"); // a shown part is a part
        CHECK(f.FadeSeconds == 0.6f && f.EffectSeconds == 3.0f && f.HideOnOthers);
        CHECK(f.ShowEffects.size() == 1 && f.ShowEffects[0].Path == L"/Game/Effect/Cut/FX_Feather.FX_Feather" && f.ShowEffects[0].Socket == L"R_FeatherShoulder_a");
        CHECK(f.HideEffects.size() == 1 && f.HideEffects[0].Socket.empty());
        CHECK(f.List[0].Name == L"NORMAL" && f.List[0].Pack.empty() && f.List[0].Effects.size() == 1);
        const Form& winged = f.List[1];
        CHECK(winged.Pack == L"Battle02" && winged.Show.size() == 2 && winged.Effects.size() == 1 && winged.Effects[0].Scale == 1.5f &&
              winged.Effects[0].Seconds == 2.0f);
        CHECK(winged.Sounds.size() == 2 && winged.Sounds[0].Bank == L"/Game/Sound/SE/SE_PC0010.SE_PC0010" && winged.Sounds[0].Cue == L"SE_Whoosh");
        CHECK(winged.Sounds[1].Bank.find(L"{language}") != std::wstring::npos && winged.Sounds[1].Cue == L"Atk_Ability_02");
        const Form& flying = f.List[2];
        CHECK(flying.Fly.On && flying.Fly.Height == 300.0f && flying.Fly.Speed == 500.0f && flying.Fly.Up == L"Gamepad_RightShoulder" &&
              flying.Fly.Down == L"Gamepad_DPad_Down" && flying.After == L"PC0000_Limit002");
        const Form& kh2 = f.List[3];
        CHECK(kh2.Model == L"/Game/Character/Player/KH2/SK_KH2Sephiroth.SK_KH2Sephiroth" && kh2.Fly.On && kh2.Fly.Height == 250.0f);
        CHECK(kh2.AnimClass == L"/Game/BluePrint/Animation/Enemy/ABP_Big.ABP_Big_C" && kh2.Scale == 0.25f && kh2.HideWeapon);
        CHECK(kh2.Meshes.size() == 2 && kh2.Meshes[0].Mesh == L"/Game/Character/Enemy/W/Wing.Wing" && kh2.Meshes[0].FollowPose &&
              kh2.Meshes[1].Socket == L"C_Head_a" && !kh2.Meshes[1].FollowPose);
        CHECK(kh2.Keep.size() == 1 && kh2.Keep[0].Socket == L"R_Hand_a");
        // effects while abilities run: an exact row name, a prefix with *, a bad name left out, an entry without effects left out
        CHECK(kh2.AbilityEffects.size() == 2);
        if (kh2.AbilityEffects.size() == 2)
        {
            const FormAbilityEffects& sword = kh2.AbilityEffects[0];
            CHECK(sword.Abilities.size() == 1 && sword.Effects.size() == 1 && sword.Effects[0].Socket == L"Attack_Sword" &&
                  sword.Effects[0].Path == L"/Game/Effect/FX_OmniSword.FX_OmniSword");
            CHECK(sword.Matches(L"PC0010_BZ_Octaslash") && sword.Matches(L"pc0010_bz_octaslash") && !sword.Matches(L"PC0010_BZ_Octaslash2") && !sword.Matches(L""));
            const FormAbilityEffects& slashes = kh2.AbilityEffects[1];
            CHECK(slashes.Abilities.size() == 1 && slashes.Matches(L"PC0010_NAtk_1") && slashes.Matches(L"PC0010_NAtk_") && !slashes.Matches(L"PC0010_NPAtk_1"));
        }
        CHECK(f.List[1].AbilityEffects.empty());
        CHECK(f.List[1].AnimClass.empty() && f.List[1].Scale == 0.0f && !f.List[1].HideWeapon && f.List[1].Meshes.empty());
        CHECK(f.List[4].Name == L"Battle05" && f.List[4].Pack == L"Battle05"); // a string entry: its pack, named after it
        CHECK(f.IndexOfPack(L"Battle03") == 2 && f.IndexOfPack(L"Battle00") == 0 && f.IndexOfPack(L"") == 0 && f.IndexOfPack(L"Battle70") == -1);
        // every form pack is a set of the row; form packs nothing fills start from the character's own
        const std::vector<std::wstring> names = RowSetNames(*cloud);
        CHECK(std::any_of(names.begin(), names.end(), [](const std::wstring& n) { return n == L"Battle04"; }));
        CHECK(std::any_of(names.begin(), names.end(), [](const std::wstring& n) { return n == L"Battle05"; }));
        CHECK(IsFormPack(*cloud, L"Battle04") && !IsFormPack(*cloud, L"Battle00") && !IsFormPack(*cloud, L"Battle07"));
    }
    else
    {
        CHECK(false);
    }
    const AnimSetRow* soldier = cfg.FindAnimSetRow(CharacterPackPath(L"PC0000_08_Cloud_SoldierNoHelmet"));
    CHECK(soldier && soldier->Forms.List.size() == 5); // the same row
    CHECK(HasMessage(cfg, L"Neutral00 is not a battle animation pack")); // left out
    CHECK(HasMessage(cfg, L"forms for /Game/DataAsset/Game/CharaSpec/CharaSpec_PC0000_00_Cloud_Standard")); // the first row's forms win
    CHECK(HasMessage(cfg, L"material slot names")); // "bad slot"
    const AnimSetRow* tifa = cfg.FindAnimSetRow(CharacterPackPath(L"PC0002_00_Tifa_Standard"));
    CHECK(!tifa); // one form only: no menu, and nothing else in the row
    CHECK(HasMessage(cfg, L"two forms or more"));
    const AnimSetRow* barret = cfg.FindAnimSetRow(CharacterPackPath(L"PC0001_00_Barret_Standard"));
    CHECK(barret && barret->Forms.List.size() == MaxForms && barret->Forms.List.back().Pack == L"Battle12");
    CHECK(HasMessage(cfg, L"the menu takes 13 forms"));
    const AnimSetRow* aerith = cfg.FindAnimSetRow(CharacterPackPath(L"PC0003_00_Aerith_Standard"));
    CHECK(aerith && aerith->Forms.List.size() == 2 && aerith->Forms.List[0].Pack == L"Battle02" && aerith->Forms.Button == L"Gamepad_FaceButton_Top");
    CHECK(HasMessage(cfg, L"the first form is the character's normal one"));
    CHECK(aerith && aerith->Forms.Title == L"FORMS" && aerith->Forms.HoldSeconds == 0.35f);

    // bad shapes
    Config bad;
    CHECK(AppendConfig(R"({"schema": "RebirthSkelCompat/1", "animation_sets": [ { "character": "PC0000_00_Cloud_Standard", "forms": { "button": "bad key" } },
                                              { "character": "PC0002_00_Tifa_Standard", "forms": 3 } ]})", L"bad.json", bad));
    FinishConfig(bad, [](const std::wstring&) { return true; });
    CHECK(bad.AnimSets.empty());
    CHECK(HasMessage(bad, L"button must be a name"));
    CHECK(HasMessage(bad, L"needs a list of forms"));
}

// 3.6: super armor, time limits, cooldowns and the form a timed one turns back into.
static void TestFormTimes()
{
    Config cfg;
    const char* file = R"({
      "schema": "RebirthSkelCompat/1",
      "animation_sets": [
        { "character": "PC0000_00_Cloud_Standard",
          "forms": [ { "name": "NORMAL", "seconds": 10 },
                     { "name": "WINGED", "pack": "Battle02", "time_limit": 20, "revert_to": "flying" },
                     { "name": "FLYING", "pack": "Battle03", "revert_to": "FLYING", "cooldown": 5 },
                     { "name": "BIZARRO", "pack": "Battle05", "super_armor": true, "seconds": 60, "cooldown": 30 },
                     { "name": "LOST", "pack": "Battle06", "seconds": -5, "cooldown": 4000, "revert_to": "NOPE" },
                     { "name": "ODD", "pack": "Battle07", "super_armor": "yes" } ] }
      ]
    })";
    CHECK(AppendConfig(file, L"times.json", cfg));
    FinishConfig(cfg, [](const std::wstring&) { return true; });
    const AnimSetRow* row = cfg.FindAnimSetRow(CharacterPackPath(L"PC0000_00_Cloud_Standard"));
    CHECK(row && row->Forms.List.size() == 6);
    if (!row || row->Forms.List.size() != 6) { return; }
    const auto& list = row->Forms.List;
    CHECK(!list[0].Limited() && list[0].Seconds == 0.0f && !list[0].SuperArmor);      // the normal form has no time limit
    CHECK(HasMessage(cfg, L"NORMAL is the normal form, which has no time limit"));
    CHECK(list[1].Seconds == 20.0f && list[1].Limited() && list[1].RevertIndex == 2);  // "time_limit"; revert_to by name, any case
    CHECK(list[2].RevertIndex == 0 && list[2].RevertTo.empty() && list[2].Cooldown == 5.0f && !list[2].Limited());
    CHECK(HasMessage(cfg, L"FLYING revert_to FLYING is the form itself"));
    CHECK(list[3].SuperArmor && list[3].Seconds == 60.0f && list[3].Cooldown == 30.0f && list[3].RevertIndex == 0);
    CHECK(list[4].Seconds == 0.0f && list[4].Cooldown == 0.0f && list[4].RevertIndex == 0);
    CHECK(HasMessage(cfg, L"LOST seconds must be a number of seconds"));
    CHECK(HasMessage(cfg, L"LOST cooldown must be a number of seconds"));
    CHECK(HasMessage(cfg, L"LOST revert_to NOPE is not one of its forms"));
    CHECK(!list[5].SuperArmor); // not a true / false
}

// 3.6.6: a form's entrance (its animation, the flash, the descent, the camera).
static void TestFormEntrance()
{
    Config cfg;
    const char* file = R"({
      "schema": "RebirthSkelCompat/1",
      "animation_sets": [
        { "character": "PC0000_00_Cloud_Standard",
          "forms": [ { "name": "NORMAL" },
                     { "name": "SAFER", "pack": "Battle06",
                       "entrance": { "animation": "/Game/RebirthSkelCompat/Built/SephirothForms/Battle06/B_SaferEnter01", "rate": 0.9,
                                     "flash": 2, "flash_color": [1, 0.95, 0.8], "descend": 1200, "descend_seconds": 5.5,
                                     "effects": [ { "effect": "/Game/Effect/FX_Light", "socket": "C_Spine_c", "scale": 2.5 } ],
                                     "camera": { "face": "C_Nose_A", "distance": 1000, "side": -200, "height": 30, "fov": 65, "close_at": 0.6,
                                                 "close": 150, "close_fov": 25, "hold": 0.8, "blend_back": 1.5, "bars": true },
                                     "hold_input": false, "invincible": false } },
                     { "name": "WINGED", "pack": "Battle02", "entrance": true },
                     { "name": "KH2", "pack": "Battle04", "entrance": { "camera": false, "flash": 0 } },
                     { "name": "ODD", "pack": "Battle05",
                       "entrance": { "rate": 50, "slot": "bad slot", "flash_color": [2, 0, 0], "camera": { "fov": 1, "bars": 9, "face": "a/b" },
                                     "skip": "no", "descend": 600 } },
                     { "name": "OFF", "pack": "Battle07", "entrance": { "enabled": false, "descend": 300 } },
                     { "name": "NUMBER", "pack": "Battle08", "entrance": 5 } ] }
      ]
    })";
    CHECK(AppendConfig(file, L"entrance.json", cfg));
    FinishConfig(cfg, [](const std::wstring&) { return true; });
    const AnimSetRow* row = cfg.FindAnimSetRow(CharacterPackPath(L"PC0000_00_Cloud_Standard"));
    CHECK(row && row->Forms.List.size() == 7);
    if (!row || row->Forms.List.size() != 7) { return; }
    const auto& list = row->Forms.List;
    CHECK(!list[0].Entrance.On);   // none by default
    const FormEntrance& safer = list[1].Entrance;
    CHECK(safer.On && safer.Animation == L"/Game/RebirthSkelCompat/Built/SephirothForms/Battle06/B_SaferEnter01.B_SaferEnter01");
    CHECK(safer.Slot == L"DefaultSlot" && safer.Rate == 0.9f && safer.Seconds == 0.0f && safer.Flash == 2.0f);
    CHECK(safer.FlashColor[0] == 1.0f && safer.FlashColor[1] == 0.95f && safer.FlashColor[2] == 0.8f);
    CHECK(safer.Descend == 1200.0f && safer.DescendSeconds == 5.5f && !safer.HoldInput && safer.Skip && !safer.Invincible);
    CHECK(safer.Effects.size() == 1 && safer.Effects[0].Socket == L"C_Spine_c" && safer.Effects[0].Scale == 2.5f &&
          safer.Effects[0].Path == L"/Game/Effect/FX_Light.FX_Light");
    const FormEntranceCamera& c = safer.Camera;
    CHECK(c.On && c.Face == L"C_Nose_A" && c.Distance == 1000.0f && c.Side == -200.0f && c.Height == 30.0f && c.Fov == 65.0f);
    CHECK(c.CloseAt == 0.6f && c.Close == 150.0f && c.CloseFov == 25.0f && c.Hold == 0.8f && c.BlendBack == 1.5f && c.Bars == 2.39f);
    const FormEntrance& winged = list[2].Entrance;   // true: the flash and the camera, no animation, no descent
    CHECK(winged.On && winged.Animation.empty() && winged.Flash == 1.5f && winged.Descend == 0.0f && winged.Camera.On &&
          winged.Camera.Face == L"C_Head_a" && winged.HoldInput && winged.Skip && winged.Invincible);
    const FormEntrance& kh2 = list[3].Entrance;
    CHECK(kh2.On && !kh2.Camera.On && kh2.Flash == 0.0f);
    const FormEntrance& odd = list[4].Entrance;      // bad parts keep their defaults, the rest is read
    CHECK(odd.On && odd.Rate == 1.0f && odd.Slot == L"DefaultSlot" && odd.FlashColor[0] == 1.0f && odd.Camera.Fov == 70.0f &&
          odd.Camera.Bars == 2.39f && odd.Camera.Face == L"C_Head_a" && odd.Skip && odd.Descend == 600.0f);
    CHECK(HasMessage(cfg, L"ODD entrance: slot must be a slot name"));
    CHECK(HasMessage(cfg, L"rate must be a number from 0.05 to 10"));
    CHECK(HasMessage(cfg, L"flash_color must be [red, green, blue]"));
    CHECK(HasMessage(cfg, L"camera fov must be a number from 5 to 170"));
    CHECK(HasMessage(cfg, L"camera bars must be true, false"));
    CHECK(HasMessage(cfg, L"camera face must be a bone or socket name"));
    CHECK(HasMessage(cfg, L"skip must be true or false"));
    CHECK(!list[5].Entrance.On && list[5].Entrance.Descend == 300.0f);   // "enabled": false
    CHECK(!list[6].Entrance.On && HasMessage(cfg, L"NUMBER entrance: it must be true, false or an object"));
}

static void TestEntranceShots()
{
    Config cfg;
    const char* file = R"({
      "schema": "RebirthSkelCompat/1",
      "cutscene_proportions": false,
      "animation_sets": [
        { "character": "PC0000_00_Cloud_Standard",
          "forms": [ { "name": "NORMAL" },
                     { "name": "BIZARRO", "pack": "Battle05",
                       "entrance": { "camera": { "hold": 0, "blend_back": 1.2, "bars": 0 },
                                     "shots": [
                         { "name": "C0130", "seconds": 7.1, "before_switch": true,
                           "animation": "/Game/Cut/Game/EV/Motion/EV_PC0010_10_C0130", "animation_start": 5.4,
                           "camera": [[0, 80, 10, 60, -5, 190, 0, 46.2], [3.5, 70, 12, 64, -4, 185, -9.8, 46.2], [7.1, 200, 0, 40, 10, 180, -25, 62.7]],
                           "effects": [ { "effect": "/Game/Effect/FX_Transform_01", "at": 5.47, "seconds": 1.7, "offset": [0, 0, 88] } ],
                           "sounds": [ { "voice": "/Game/Sound/Voice/{language}/Cut/C3510_sep", "cue": "C3510_sep", "at": 1.17 },
                                       { "bank": "/Game/Sound/SE/Cut/EV_0465f", "cue": "EV_0465f", "start": 14.07, "stop_at_end": true } ] },
                         { "name": "C0160", "seconds": 9.4, "animation": "/Game/Cut/Game/EV/Motion/EV_EB2210_00_C0160", "scale": 1, "flash": 0.8,
                           "flash_color": [0, 0, 0],
                           "camera": [[0, 1136, 0, 95, 2, 180, 0, 81], [9.4, 1300, -40, 400, 67, 160, 0, 81]],
                           "effects": [ { "effect": "/Game/Effect/FX_Transform_03", "seconds": 9.4, "offset": [648, -26, 230], "scale": 0.5 },
                                        { "effect": "/Game/Effect/FX_Core", "socket": "C_Core_a", "at": 1 } ] },
                         { "name": "BAD", "seconds": 500 },
                         { "name": "KEYS", "seconds": 2, "before_switch": true,
                           "camera": [[0, 0, 0, 0, 0, 0, 0, 50], [5, 0, 0, 0, 0, 0, 0, 50], [1, 0, 0, 0], [0.5, 0, 0, 0, 0, 0, 0, 200], [1, 1, 1, 1, 1, 1, 1, 60]],
                           "effects": [ { "effect": "/Game/Effect/FX_X", "at": 9 }, { "effect": "/Game/Effect/FX_Y", "socket": "C_Hip_a", "offset": [1, 2, 3] } ],
                           "sounds": [ { "bank": "/Game/Sound/SE/X", "cue": "X", "stop_at_end": "yes" } ] } ] } },
                     { "name": "EMPTY", "pack": "Battle06", "entrance": { "shots": [ { "seconds": 0 } ] } } ] }
      ]
    })";
    CHECK(AppendConfig(file, L"shots.json", cfg));
    FinishConfig(cfg, [](const std::wstring&) { return true; });
    CHECK(!cfg.CutsceneProportions);
    const AnimSetRow* row = cfg.FindAnimSetRow(CharacterPackPath(L"PC0000_00_Cloud_Standard"));
    CHECK(row && row->Forms.List.size() == 3);
    if (!row || row->Forms.List.size() != 3) { return; }
    const FormEntrance& e = row->Forms.List[1].Entrance;
    CHECK(e.On && e.Shots.size() == 3);   // BAD left out
    if (e.Shots.size() != 3) { return; }
    const EntranceShot& a = e.Shots[0];
    CHECK(a.Name == L"C0130" && a.Seconds == 7.1f && a.BeforeSwitch && a.AnimationStart == 5.4f && a.Rate == 1.0f && a.Scale == 1.0f);
    CHECK(a.Animation == L"/Game/Cut/Game/EV/Motion/EV_PC0010_10_C0130.EV_PC0010_10_C0130");
    CHECK(a.Camera.size() == 3 && a.Camera[1].T == 3.5f && a.Camera[1].X == 70.0f && a.Camera[1].Roll == -9.8f && a.Camera[2].Fov == 62.7f);
    CHECK(a.Effects.size() == 1 && a.Effects[0].At == 5.47f && a.Effects[0].Offset[2] == 88.0f && a.Effects[0].Effect.Seconds == 1.7f &&
          a.Effects[0].Effect.Socket.empty() && a.Effects[0].Effect.Path == L"/Game/Effect/FX_Transform_01.FX_Transform_01");
    CHECK(a.Sounds.size() == 2 && a.Sounds[0].At == 1.17f && a.Sounds[0].Sound.Bank.find(L"{language}") != std::wstring::npos &&
          a.Sounds[1].Start == 14.07f && a.Sounds[1].StopAtEnd && a.Sounds[1].Sound.Cue == L"EV_0465f");
    const EntranceShot& b = e.Shots[1];
    CHECK(b.Name == L"C0160" && !b.BeforeSwitch && b.Flash == 0.8f && b.FlashColor[0] == 0.0f && b.Camera.size() == 2 && b.Effects.size() == 2);
    CHECK(b.Effects[0].Effect.Scale == 0.5f && b.Effects[0].Offset[0] == 648.0f && b.Effects[1].Effect.Socket == L"C_Core_a" && b.Effects[1].At == 1.0f);
    const EntranceShot& c = e.Shots[2];   // a "before_switch" shot after another: part of the main shots
    CHECK(c.Name == L"KEYS" && c.Camera.size() == 2 && c.Camera[1].T == 1.0f && c.Effects.empty() && c.Sounds.empty());
    CHECK(e.PreludeShots() == 1 && e.PreludeSeconds() == 7.1f && std::fabs(e.ShotsSeconds() - 18.5f) < 0.001f);
    CHECK(HasMessage(cfg, L"shots[2] (BAD) seconds must be a number from 0.05 to 120"));
    CHECK(HasMessage(cfg, L"shots[3] (KEYS) camera: 3 key(s) left out"));
    CHECK(HasMessage(cfg, L"shots[3] (KEYS) effects: entries must look like"));
    CHECK(HasMessage(cfg, L"shots[3] (KEYS) sounds: entries must look like"));
    const FormEntrance& empty = row->Forms.List[2].Entrance;
    CHECK(empty.On && empty.Shots.empty() && HasMessage(cfg, L"none of its shots is usable"));
    Config plain;
    CHECK(AppendConfig(R"({"schema": "RebirthSkelCompat/1", "animation_sets": [{"character": "PC0000_00_Cloud_Standard", "forms": [{"name": "A"}]}]})", L"p.json", plain));
    CHECK(plain.CutsceneProportions);
}

// 3.6.16 "cutscene_weapon_socket": parsed, a row of its own, the first row's wins when rows join.
static void TestCutsceneWeaponSocket()
{
    Config cfg;
    const std::string file = R"({
      "schema": "RebirthSkelCompat/1",
      "animation_sets": [
        { "characters": [ "PC0010_00_Sephiroth_Standard", "PC0010_20_Sephiroth_VRHard" ], "cutscene_weapon_socket": " Attach_Weapon_Left01 " },
        { "character": "PC0010_00_Sephiroth_Standard", "battle": "/Game/Motion/Player/PC0000_EvilCloud", "cutscene_weapon_socket": "Attach_Weapon01" },
        { "character": "PC0010_10_Sephiroth_Transform", "cutscene_weapon_socket": "bad/socket" },
        { "character": "PC0002_00_Tifa_Standard", "field": "/Game/Motion/Player/PC0002_Tifa" }
      ]
    })";
    CHECK(AppendConfig(file, L"cut.json", cfg));
    CHECK(cfg.AnimSets.size() == 3);   // (the bad socket's row has nothing else: skipped)
    CHECK(!cfg.AnimSets.empty() && cfg.AnimSets[0].CutsceneWeaponSocket == L"Attach_Weapon_Left01" && cfg.AnimSets[0].Battle.empty());
    const auto said = [&](const wchar_t* what) {
        return std::any_of(cfg.Messages.begin(), cfg.Messages.end(), [&](const std::wstring& m) { return m.find(what) != std::wstring::npos; });
    };
    CHECK(said(L"cutscene_weapon_socket must be a socket name"));
    FinishConfig(cfg, [](const std::wstring&) { return true; });
    const AnimSetRow* evil = cfg.FindAnimSetRow(CharacterPackPath(L"PC0010_00_Sephiroth_Standard"));
    const AnimSetRow* boss = cfg.FindAnimSetRow(CharacterPackPath(L"PC0010_20_Sephiroth_VRHard"));
    const AnimSetRow* tifa = cfg.FindAnimSetRow(CharacterPackPath(L"PC0002_00_Tifa_Standard"));
    CHECK(evil && evil->CutsceneWeaponSocket == L"Attach_Weapon_Left01" && evil->Battle.size() == 1);
    CHECK(boss && boss->CutsceneWeaponSocket == L"Attach_Weapon_Left01");
    CHECK(tifa && tifa->CutsceneWeaponSocket.empty());
    CHECK(said(L"cutscene_weapon_socket Attach_Weapon01 for"));
}

// 3.6.16: a form's "camera" and "ability_cameras".
static void TestFormCameras()
{
    Config cfg;
    const std::string file = R"({
      "schema": "RebirthSkelCompat/1",
      "animation_sets": [
        { "character": "PC0000_00_Cloud_Standard",
          "forms": [ { "name": "NORMAL" },
                     { "name": "BIZARRO", "pack": "Battle05", "camera": { "distance": 350, "height": 120, "blend": 0.8 },
                       "ability_cameras": [ { "abilities": [ "M_SMN_*" ], "distance": 2500, "height": 600, "fov": 10 },
                                            { "ability": "PC0010_BZ_HellsGate", "distance": 900 },
                                            { "abilities": [ "bad name!" ], "distance": 1 },
                                            { "ability": "PC0010_X", "distance": "far" } ] },
                     { "name": "KH2", "pack": "Battle04", "camera": 200 },
                     { "name": "SAFER", "pack": "Battle06", "camera": { "distance": 99999 } } ] }
      ]
    })";
    CHECK(AppendConfig(file, L"cam.json", cfg));
    FinishConfig(cfg, [](const std::wstring&) { return true; });
    const AnimSetRow* row = cfg.FindAnimSetRow(CharacterPackPath(L"PC0000_00_Cloud_Standard"));
    CHECK(row && row->Forms.List.size() == 4);
    if (!row || row->Forms.List.size() != 4) { return; }
    const Form& normal = row->Forms.List[0];
    const Form& bizarro = row->Forms.List[1];
    const Form& kh2 = row->Forms.List[2];
    const Form& safer = row->Forms.List[3];
    CHECK(!normal.Camera.Set && normal.AbilityCameras.empty());
    CHECK(bizarro.Camera.Set && bizarro.Camera.Distance == 350.0f && bizarro.Camera.Height == 120.0f && bizarro.Camera.Blend == 0.8f && bizarro.Camera.Fov == 0.0f);
    CHECK(bizarro.AbilityCameras.size() == 2);
    if (bizarro.AbilityCameras.size() == 2)
    {
        CHECK(bizarro.AbilityCameras[0].Matches(L"M_SMN_103_atk001_01") && !bizarro.AbilityCameras[0].Matches(L"PC0010_BZ_Swarm"));
        CHECK(bizarro.AbilityCameras[0].Camera.Distance == 2500.0f && bizarro.AbilityCameras[0].Camera.Height == 600.0f && bizarro.AbilityCameras[0].Camera.Fov == 10.0f);
        CHECK(bizarro.AbilityCameras[1].Matches(L"pc0010_bz_hellsgate") && bizarro.AbilityCameras[1].Camera.Distance == 900.0f && bizarro.AbilityCameras[1].Camera.Blend == 0.6f);
    }
    CHECK(kh2.Camera.Set && kh2.Camera.Distance == 200.0f && kh2.Camera.Height == 0.0f);
    CHECK(!safer.Camera.Set);   // (out of range: ignored, with a note)
    const auto said = [&](const wchar_t* what) {
        return std::any_of(cfg.Messages.begin(), cfg.Messages.end(), [&](const std::wstring& m) { return m.find(what) != std::wstring::npos; });
    };
    CHECK(said(L"SAFER camera must be a distance"));
    CHECK(said(L"BIZARRO ability_cameras entries must look like"));
}


static void TestShooter()
{
    using namespace SkelCompat::Shooter;
    // buttons
    CHECK(ButtonOf(L"R2") == Button::R2 && ButtonOf(L"x") == Button::Cross && ButtonOf(L"Gamepad_FaceButton_Left") == Button::Square);
    CHECK(ButtonOf(L"r3") == Button::R3 && ButtonOf(L"bogus") == Button::None && ButtonOf(L"") == Button::None);
    CHECK(LabelsOf(Bit(Button::L2) | Bit(Button::R2)) == L"L2, R2" && std::wstring(KeyNameOf(Button::R1)) == L"Gamepad_RightShoulder");
    // trigger effects
    uint8_t e[11];
    EncodeTrigger(WeaponTrigger(4, 6, 6), e);
    CHECK(e[0] == 0x25 && e[1] == 0x50 && e[2] == 0x00 && e[3] == 5 && e[4] == 0);
    EncodeTrigger(FeedbackTrigger(2, 2), e);
    uint32_t forces = 0;
    for (int i = 2; i < 10; ++i) { forces |= 1u << (3 * i); }
    CHECK(e[0] == 0x21 && e[1] == 0xFC && e[2] == 0x03 && e[3] == (forces & 0xff) && e[6] == ((forces >> 24) & 0xff));
    EncodeTrigger(VibrationTrigger(3, 8, 35), e);
    CHECK(e[0] == 0x26 && e[9] == 35 && e[1] == 0xF8 && e[2] == 0x03);
    EncodeTrigger(TriggerEffect{}, e);
    CHECK(e[0] == 0x05 && e[1] == 0 && e[10] == 0);
    EncodeTrigger(WeaponTrigger(4, 6, 0), e);
    CHECK(e[0] == 0x05);
    // CRC-32: the standard check value, and a report's (seed byte first)
    const uint8_t digits[] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};
    CHECK(~Crc32(digits, 9) == 0xCBF43926u);
    CHECK(ReportCrc('1', digits + 1, 8) == 0xCBF43926u);
    // output reports
    uint8_t right[11], left[11];
    EncodeTrigger(WeaponTrigger(4, 6, 6), right);
    EncodeTrigger(FeedbackTrigger(2, 2), left);
    uint8_t usb[64];
    CHECK(TriggerReport(false, 0, right, left, usb, 48) == 48);
    CHECK(usb[0] == 0x02 && usb[1] == 0x0C && usb[2] == 0 && usb[11] == 0x25 && usb[22] == 0x21 && usb[47] == 0);
    CHECK(TriggerReport(false, 0, right, left, usb, 40) == 0);
    uint8_t bt[547];
    CHECK(TriggerReport(true, 5, right, left, bt, sizeof(bt)) == sizeof(bt));
    const uint32_t btCrc = static_cast<uint32_t>(bt[74]) | static_cast<uint32_t>(bt[75]) << 8 | static_cast<uint32_t>(bt[76]) << 16 | static_cast<uint32_t>(bt[77]) << 24;
    CHECK(bt[0] == 0x31 && bt[1] == 0x50 && bt[2] == 0x10 && bt[3] == 0x0C && bt[13] == 0x25 && bt[24] == 0x21 && btCrc == ReportCrc(0xA2, bt, 74) && bt[78] == 0);
    uint8_t game[48] = {0x02, 0x00, 0x04};   // the game's report: only its lightbar
    game[45] = 200;
    CHECK(PatchTriggerReport(game, sizeof(game), right, left) && game[1] == 0x0C && game[2] == 0x04 && game[45] == 200 && game[11] == 0x25 && game[22] == 0x21);
    uint8_t other[48] = {0x05};
    CHECK(!PatchTriggerReport(other, sizeof(other), right, left) && other[1] == 0);
    // input reports: a DualSense over USB
    uint8_t in[64] = {};
    in[0] = 0x01; in[5] = 200; in[6] = 255; in[8] = 0x18; in[9] = 0x0F; in[10] = 0x01;
    PadRead read;
    CHECK(ReadPadReport(in, sizeof(in), PadKind::DualSenseUsb, 0, read));
    CHECK(read.L2 > 0.78f && read.L2 < 0.79f && read.R2 == 1.0f);
    CHECK(read.Down == (Bit(Button::Square) | Bit(Button::L1) | Bit(Button::R1) | Bit(Button::L2) | Bit(Button::R2) | Bit(Button::PS)));
    const uint32_t block = Bit(Button::L1) | Bit(Button::R1) | Bit(Button::L2) | Bit(Button::R2) | Bit(Button::R3);
    CHECK(ReadPadReport(in, sizeof(in), PadKind::DualSenseUsb, block, read));
    CHECK(in[9] == 0 && in[5] == 0 && in[6] == 0 && in[8] == 0x18 && in[10] == 0x01 && (read.Down & Bit(Button::R2)));
    uint8_t up[64] = {0x01};
    up[8] = 0x01;   // the pad up and right
    CHECK(ReadPadReport(up, sizeof(up), PadKind::DualSenseUsb, Bit(Button::Right), read) && (up[8] & 0x0f) == 0 && (read.Down & Bit(Button::Right)));
    // a DualSense over Bluetooth: the checksum is made again
    uint8_t bin[78] = {};
    bin[0] = 0x31; bin[6] = 128; bin[7] = 90; bin[9] = 0x08; bin[10] = 0x82;
    StoreCrc(0xA1, bin, 78);
    CHECK(ReadPadReport(bin, sizeof(bin), PadKind::DualSenseBt, block, read));
    const uint32_t inCrc = static_cast<uint32_t>(bin[74]) | static_cast<uint32_t>(bin[75]) << 8 | static_cast<uint32_t>(bin[76]) << 16 | static_cast<uint32_t>(bin[77]) << 24;
    CHECK((read.Down & Bit(Button::R1)) && (read.Down & Bit(Button::R3)) && bin[10] == 0 && bin[6] == 0 && bin[7] == 0 && inCrc == ReportCrc(0xA1, bin, 74));
    CHECK(!ReadPadReport(bin, sizeof(bin), PadKind::DualSenseUsb, 0, read));   // (not a USB report)
    // a DualShock 4 over USB
    uint8_t ds4[64] = {0x01};
    ds4[5] = 0x28; ds4[6] = 0x04; ds4[8] = 255;
    CHECK(ReadPadReport(ds4, sizeof(ds4), PadKind::DualShock4Usb, Bit(Button::L2), read) && (read.Down & Bit(Button::Cross)) && ds4[6] == 0 && ds4[8] == 0 &&
          (ds4[5] & 0x0f) == 8);
    // XInput
    uint8_t pad[12] = {};
    const uint16_t w = 0x0100 | 0x1000;
    std::memcpy(pad, &w, 2);
    pad[2] = 255;
    ReadXInputPad(pad, Bit(Button::L1) | Bit(Button::L2), read);
    uint16_t after = 0;
    std::memcpy(&after, pad, 2);
    CHECK((read.Down & Bit(Button::L1)) && (read.Down & Bit(Button::Cross)) && (read.Down & Bit(Button::L2)) && !(read.Down & Bit(Button::R2)) && after == 0x1000 && pad[2] == 0);
    // the slower aim: the right stick moved toward its middle (and a Bluetooth report's checksum made again)
    uint8_t st[64] = {0x01};
    st[3] = 255; st[4] = 0;
    CHECK(ReadPadReport(st, sizeof(st), PadKind::DualSenseUsb, 0, read, 0.5f) && read.RX > 0.99f && read.RY > 0.99f && st[3] == 192 && st[4] == 64);
    uint8_t still[64] = {0x01};
    still[3] = 200;
    CHECK(ReadPadReport(still, sizeof(still), PadKind::DualSenseUsb, 0, read) && still[3] == 200 && read.RX > 0.56f && read.RX < 0.57f);
    uint8_t bst[78] = {0x31};
    bst[4] = 0; bst[5] = 128;
    StoreCrc(0xA1, bst, 78);
    CHECK(ReadPadReport(bst, sizeof(bst), PadKind::DualSenseBt, 0, read, 0.25f) && bst[4] == 96 && bst[5] == 128 && read.RX < -0.99f);
    const uint32_t stickCrc = static_cast<uint32_t>(bst[74]) | static_cast<uint32_t>(bst[75]) << 8 | static_cast<uint32_t>(bst[76]) << 16 | static_cast<uint32_t>(bst[77]) << 24;
    CHECK(stickCrc == ReportCrc(0xA1, bst, 74));
    uint8_t ds4bt[78] = {0x11};
    ds4bt[5] = 0; ds4bt[6] = 255; ds4bt[7] = 0x08;
    StoreCrc(0xA1, ds4bt, 78);
    CHECK(ReadPadReport(ds4bt, sizeof(ds4bt), PadKind::DualShock4Bt, 0, read, 0.5f) && ds4bt[5] == 64 && ds4bt[6] == 192 && read.RY < -0.99f);
    uint8_t xs[12] = {};
    const int16_t full = 32767, low = -32768;
    std::memcpy(xs + 8, &full, 2);
    std::memcpy(xs + 10, &low, 2);
    ReadXInputPad(xs, 0, read, 0.5f);
    int16_t sx = 0, sy = 0;
    std::memcpy(&sx, xs + 8, 2);
    std::memcpy(&sy, xs + 10, 2);
    CHECK(read.RX > 0.99f && read.RY < -0.99f && sx == 16384 && sy == -16384);
    // (3.7.3) a button held for the game: after the block (blocked R1 is still held), what the controller holds is read
    uint8_t fr[64] = {0x01};
    fr[8] = 0x08;   // the pad untouched, nothing held
    CHECK(ReadPadReport(fr, sizeof(fr), PadKind::DualSenseUsb, block, read, 1.0f, Bit(Button::R1)) && (fr[9] & 0x02) && !(read.Down & Bit(Button::R1)));
    uint8_t fr2[64] = {0x01};
    fr2[8] = 0x08; fr2[9] = 0x02;   // R1 held: blocked and held again
    CHECK(ReadPadReport(fr2, sizeof(fr2), PadKind::DualSenseUsb, block, read, 1.0f, Bit(Button::R1)) && fr2[9] == 0x02 && (read.Down & Bit(Button::R1)));
    uint8_t fr3[64] = {0x01};
    fr3[8] = 0x08; fr3[9] = 0x02;   // R1 held, nothing forced: blocked
    CHECK(ReadPadReport(fr3, sizeof(fr3), PadKind::DualSenseUsb, block, read, 1.0f, 0) && fr3[9] == 0);
    uint8_t fbt[78] = {0x31};
    fbt[9] = 0x08;
    StoreCrc(0xA1, fbt, 78);
    CHECK(ReadPadReport(fbt, sizeof(fbt), PadKind::DualSenseBt, block, read, 1.0f, Bit(Button::R1)) && (fbt[10] & 0x02));
    const uint32_t forcedCrc = static_cast<uint32_t>(fbt[74]) | static_cast<uint32_t>(fbt[75]) << 8 | static_cast<uint32_t>(fbt[76]) << 16 | static_cast<uint32_t>(fbt[77]) << 24;
    CHECK(forcedCrc == ReportCrc(0xA1, fbt, 74));
    uint8_t fx[12] = {};
    ReadXInputPad(fx, block, read, 1.0f, Bit(Button::R1));
    uint16_t fw = 0;
    std::memcpy(&fw, fx, 2);
    CHECK(fw == 0x0200 && !(read.Down & Bit(Button::R1)));
    // locomotion
    Locomotion m = LocomotionFor(0.0f, 0.0f, 160.0f, 500.0f);
    CHECK(m.Idle == 1.0f && m.Forward == 0.0f);
    m = LocomotionFor(500.0f, 0.0f, 160.0f, 500.0f);
    CHECK(m.Idle == 0.0f && m.Forward > 0.99f && m.Walk < 0.01f && m.Rate > 0.99f && m.Rate < 1.01f);
    m = LocomotionFor(500.0f, 90.0f, 160.0f, 500.0f);
    CHECK(m.Right > 0.99f && m.Forward < 0.01f);
    m = LocomotionFor(500.0f, -135.0f, 160.0f, 500.0f);
    CHECK(std::fabs(m.Left - 0.5f) < 0.01f && std::fabs(m.Back - 0.5f) < 0.01f);
    m = LocomotionFor(500.0f, 225.0f, 160.0f, 500.0f);
    CHECK(std::fabs(m.Left - 0.5f) < 0.01f && std::fabs(m.Back - 0.5f) < 0.01f);
    m = LocomotionFor(150.0f, 10.0f, 160.0f, 500.0f);
    CHECK(m.Walk > 0.5f && m.Idle < 0.01f);
    const float sum = m.Idle + m.Walk + m.Forward + m.Back + m.Left + m.Right;
    CHECK(std::fabs(sum - 1.0f) < 1e-4f);
    // pose math
    Xf parent;
    parent.R = AxisAngle(V3{0.3f, 1.0f, -0.2f}, 0.7f);
    parent.T = V3{10, -4, 3};
    parent.S = V3{1, 1, 1};
    Xf child;
    child.R = AxisAngle(V3{1, 0.2f, 0.5f}, -1.1f);
    child.T = V3{-2, 7, 11};
    const Xf local = Relative(child, parent);
    const Xf again = Compose(local, parent);
    CHECK(Length(again.T - child.T) < 1e-3f && std::fabs(std::fabs(QDot(again.R, child.R)) - 1.0f) < 1e-4f);
    const Xf undone = Compose(Compose(child, parent), Inverse(parent));
    CHECK(Length(undone.T - child.T) < 1e-3f && std::fabs(std::fabs(QDot(undone.R, child.R)) - 1.0f) < 1e-4f);
    const V3 a = Unit(V3{1, 2, 0.5f}), b = Unit(V3{-0.3f, 0.4f, 1.0f});
    CHECK(Length(Rotate(FromTo(a, b), a) - b) < 1e-4f);
    const Q4 turn = AxisAngle(V3{0, 0, 1}, 1.2f);
    const Q4 half = Part(turn, 0.5f);
    CHECK(std::fabs(std::fabs(QDot(Mul(half, half), turn)) - 1.0f) < 1e-4f && std::fabs(AngleOf(half) - 0.6f) < 1e-4f);
    CHECK(Length(Rotate(AxisAngle(V3{0, 0, 1}, 1.5707963f), V3{1, 0, 0}) - V3{0, 1, 0}) < 1e-5f);
    // the camera and the aim
    CHECK(Length(ForwardOf(90.0f, 0.0f) - V3{0, 1, 0}) < 1e-5f && Length(RightOf(0.0f) - V3{0, 1, 0}) < 1e-5f);
    const V3 cam = ShoulderCamera(V3{0, 0, 100}, 0.0f, 0.0f, 200.0f, 50.0f, 20.0f);
    CHECK(Length(cam - V3{-200, 50, 120}) < 1e-3f);
    float yaw = 0.0f, pitch = 0.0f;
    AnglesOf(V3{0, 1, 1}, yaw, pitch);
    CHECK(std::fabs(yaw - 90.0f) < 1e-3f && std::fabs(pitch - 45.0f) < 1e-3f);
    const std::vector<V3> points = {V3{1000, 10, 0}, V3{1000, 500, 0}, V3{-1000, 0, 0}, V3{900, -20, 0}};
    const std::vector<float> radii = {50, 50, 50, 1};
    CHECK(PickTarget(V3{}, V3{1, 0, 0}, points, radii, 2.5f, 8000.0f) == 0);
    CHECK(PickTarget(V3{}, Unit(V3{1000, 500, 0}), points, radii, 2.5f, 8000.0f) == 1);
    CHECK(PickTarget(V3{}, V3{0, 1, 0}, points, radii, 2.5f, 8000.0f) == -1);
    CHECK(PickTarget(V3{}, V3{1, 0, 0}, points, radii, 2.5f, 500.0f) == -1);
    // (3.7.6) hit zones: a body the line goes through, the nearest first; else within the assist of an edge; the crit spot
    {
        float gap = 0.0f, along = 0.0f;
        RayToSegment(V3{}, V3{1, 0, 0}, V3{1000, 50, -100}, V3{1000, 50, 100}, gap, along);
        CHECK(std::fabs(gap - 50.0f) < 1e-2f && std::fabs(along - 1000.0f) < 1e-2f);
        RayToSegment(V3{}, V3{1, 0, 0}, V3{1000, 0, 300}, V3{1000, 0, 500}, gap, along);   // above the line: its bottom end
        CHECK(std::fabs(gap - 300.0f) < 1e-2f && std::fabs(along - 1000.0f) < 1e-2f);
        RayToSegment(V3{}, V3{1, 0, 0}, V3{-500, 0, 0}, V3{-400, 0, 0}, gap, along);      // behind the eye
        CHECK(along == 0.0f && std::fabs(gap - 400.0f) < 1e-2f);
        HitZone near{V3{800, 0, -90}, V3{800, 0, 90}, 60.0f, V3{800, 0, 140}, 25.0f};
        HitZone far{V3{2000, 0, -300}, V3{2000, 0, 300}, 250.0f, V3{2000, 0, 450}, 30.0f};
        HitZone side{V3{1000, 900, -90}, V3{1000, 900, 90}, 60.0f, V3{}, 0.0f};
        const std::vector<HitZone> zones = {far, near, side};
        Picked p = PickZone(V3{}, V3{1, 0, 0}, zones, 2.5f, 8000.0f);
        CHECK(p.Index == 1 && !p.Crit);                                     // both bodies on the line: the nearer
        p = PickZone(V3{}, Unit(V3{800, 0, 140}), zones, 2.5f, 8000.0f);
        CHECK(p.Index == 1 && p.Crit);                                      // its head
        p = PickZone(V3{}, Unit(V3{2000, 0, 400}), zones, 2.5f, 8000.0f);
        CHECK(p.Index == 0 && !p.Crit);                                     // over the near one, into the big one
        p = PickZone(V3{}, Unit(V3{2000, 0, 450}), zones, 2.5f, 8000.0f);
        CHECK(p.Index == 0 && p.Crit);
        p = PickZone(V3{}, Unit(V3{1000, 820, 0}), zones, 2.5f, 8000.0f);
        CHECK(p.Index == 2);                                                // off its edge, within the assist
        p = PickZone(V3{}, Unit(V3{1000, 600, 0}), zones, 2.5f, 8000.0f);
        CHECK(p.Index == -1);
        p = PickZone(V3{}, V3{-1, 0, 0}, zones, 2.5f, 8000.0f);
        CHECK(p.Index == -1);
        CHECK(PickZone(V3{}, V3{1, 0, 0}, zones, 2.5f, 500.0f).Index == -1);   // out of range
    }
    // bones the game's pose keeps
    const std::vector<std::wstring> keep = {L"*_Phy", L"*Kdi*", L"C_Face*"};
    CHECK(BoneMatches(L"C_HairTopA_a_Phy", keep) && BoneMatches(L"C_HipWOsKdi", keep) && BoneMatches(L"c_facebase_a", keep) && !BoneMatches(L"C_Spine_b", keep));
    // the settings
    Config cfg;
    const std::string file = R"({
      "schema": "RebirthSkelCompat/1",
      "animation_sets": [
        { "character": "PC0000_00_Cloud_Standard", "battle": [ "/Game/Motion/Player/PC0011_Vincent" ],
          "forms": [ { "name": "NORMAL" }, { "name": "GALIAN", "pack": "Battle02", "shooter": false,
                                             "sets": { "Battle00": "Battle02", "Battle01": "Battle03", "Facial00": "Facial07", "battle00": "Battle09",
                                                       "Bad Name": "Battle04", "Neutral00": "Neutral00" } } ] },
        { "character": "PC0000_00_Cloud_Standard",
          "shooter": { "controls": "dirge", "assist": 4, "camera": { "distance": 300, "aim_fov": 40, "camera_abilities": [ "*NAtk*", "PC0000_Abl_Braver" ] }, "invert_y": true,
                       "hit_scale": 1.5, "crit": { "hits": 3, "scale": 2, "color": [0, 1, 0] },
                       "aim_trigger": { "mode": "feedback", "start": 1, "strength": 3 },
                       "reticle": { "color": [1, 0, 0], "size": 20, "scale": 0.8, "ui_folder": "my_ui" },
                       "motions": { "spine": [ "C_Spine_c", "C_Spine_d" ], "share": [ 0.5 ], "run_speed": 600, "stand": false }, "gun_socket": "Body_Hand_Right01",
                       "weapons": [ { "name": "HYDRA", "clip": 40 },
                                    { "name": "Death Penalty", "set": "m001_h", "damage_source": "EB2020_03_AtkFollowShot_Renkei", "clip": 1, "reticle": "reticle_ornate",
                                      "fire_trigger": { "mode": "weapon", "start": 5, "end": 8, "strength": 8 }, "muzzle": false,
                                      "sound": { "bank": "/Game/Sound/SE/Cut/X/EV_X_01", "cue": "EV_X_01", "start": 10.5, "length": 0.8, "volume": 0.7 } },
                                    { "name": "bad", "set": "a/b" } ] } },
        { "character": "PC0000_00_Cloud_Standard", "shooter": true }
      ]
    })";
    CHECK(AppendConfig(file, L"dirge.json", cfg));
    FinishConfig(cfg, [](const std::wstring&) { return true; });
    const AnimSetRow* row = cfg.FindAnimSetRow(CharacterPackPath(L"PC0000_00_Cloud_Standard"));
    CHECK(row != nullptr);
    if (!row) { return; }
    const Settings& s = row->Shooting;
    CHECK(s.On && s.Fire == Button::R1 && s.Aim == Button::L1 && s.Reload == Button::R2 && s.Switch == Button::L2 && s.Zoom == Button::R3);
    CHECK(s.Block == (Bit(Button::R1) | Bit(Button::L1) | Bit(Button::R2) | Bit(Button::L2) | Bit(Button::R3)));
    CHECK(s.Assist == 4.0f && s.Distance == 300.0f && s.AimFov == 40.0f && s.InvertY && s.RunSpeed == 600.0f);
    CHECK(s.AimTrigger == FeedbackTrigger(1, 3) && s.ReticleColor[0] == 1.0f && s.ReticleColor[1] == 0.0f && s.ReticleColor[3] == 0.9f && s.ReticleSize == 20.0f);
    CHECK(s.ReticleScale == 0.8f && s.Ui == L"my_ui" && s.Slot == L"DefaultSlot" && s.Folder == L"/Game/RebirthSkelCompat/Dirge/Vincent");
    CHECK(s.HitScale == 1.5f && s.Crit && s.CritHits == 3 && s.CritScale == 2.0f && s.CritColor[0] == 0.0f && s.CritColor[1] == 1.0f && s.CritColor[3] == 1.0f);
    {
        const Settings plain;
        CHECK(plain.HitScale == 1.0f && plain.Crit && plain.CritHits == 2 && plain.CritScale == 1.0f);
    }
    CHECK(s.Spine.size() == 2 && s.Share.size() == 2 && s.Share[0] == 0.5f && s.Share[1] == 0.5f);
    CHECK(s.Weapons.size() == 2);
    if (s.Weapons.size() == 2)
    {
        CHECK(s.Weapons[0].Name == L"HYDRA" && s.Weapons[0].Automatic && s.Weapons[0].Clip == 40 && s.Weapons[0].Set == L"m002_m");
        CHECK(s.Weapons[1].Name == L"Death Penalty" && !s.Weapons[1].Automatic && s.Weapons[1].Clip == 1 && s.Weapons[1].Muzzle.Path.empty() &&
              s.Weapons[1].FireTrigger == WeaponTrigger(5, 8, 8));
        // (3.7.1) a gunshot that is a slice of a longer sound; HYDRA keeps Vincent's shot (two slices of the cutscene's)
        CHECK(s.Weapons[1].Sounds.size() == 1 && s.Weapons[1].Sounds[0].Cue == L"EV_X_01" && s.Weapons[1].Sounds[0].Bank == L"/Game/Sound/SE/Cut/X/EV_X_01.EV_X_01" &&
              s.Weapons[1].Sounds[0].Start == 10.5f && s.Weapons[1].Sounds[0].Length == 0.8f && s.Weapons[1].Sounds[0].Volume == 0.7f);
        CHECK(s.Weapons[0].Sounds.size() == 2 && s.Weapons[0].Sounds[0].Cue == L"EV_FOREE_0630_01" && s.Weapons[0].Sounds[0].Start == 10.59f &&
              s.Weapons[0].Sounds[1].Cue == L"EV_FOREE_0630_0319f" && s.Weapons[0].Sounds[1].Length > 0.0f && s.Weapons[0].DamageSource == L"EB2020_00_AtkShot01_Bullet");
        CHECK(s.Clip(s.Weapons[1], s.Idle) == L"/Game/RebirthSkelCompat/Dirge/Vincent/p000_m001_h_st_a_remap.p000_m001_h_st_a_remap");
        CHECK(s.Weapons[0].Reticle == L"reticle_round" && s.Weapons[1].Reticle == L"reticle_ornate");
    }
    CHECK(row->Forms.List.size() == 2 && row->Forms.List[0].Shooting == -1 && row->Forms.List[1].Shooting == 0);
    // (3.7.5) a form's "sets": each name once (case folded), plain names, not to itself
    if (row->Forms.List.size() == 2)
    {
        const auto& sets = row->Forms.List[1].Sets;
        CHECK(row->Forms.List[0].Sets.empty() && sets.size() == 3);
        CHECK(sets.size() == 3 && sets[0] == std::make_pair(std::wstring(L"Battle00"), std::wstring(L"Battle02")) &&
              sets[1] == std::make_pair(std::wstring(L"Battle01"), std::wstring(L"Battle03")) && sets[2].first == L"Facial00" && sets[2].second == L"Facial07");
    }
    const auto said = [&](const wchar_t* what) {
        return std::any_of(cfg.Messages.begin(), cfg.Messages.end(), [&](const std::wstring& msg) { return msg.find(what) != std::wstring::npos; });
    };
    CHECK(said(L"weapon bad: set, fly_set, damage_source and ability must be names"));
    CHECK(said(L"GALIAN sets: each entry must be a set name -> another set name"));
    CHECK(said(L"shooter for /Game/DataAsset/Game/CharaSpec/CharaSpec_PC0000_00_Cloud_Standard") || said(L"shooter for"));
    // the defaults, and a row with only "shooter"
    Config plain;
    CHECK(AppendConfig(R"({"schema": "RebirthSkelCompat/1", "animation_sets": [ {"character": "PC0011_00_Vincent_Standard", "shooter": true} ]})", L"p.json", plain));
    FinishConfig(plain, [](const std::wstring&) { return true; });
    const AnimSetRow* only = plain.FindAnimSetRow(CharacterPackPath(L"PC0011_00_Vincent_Standard"));
    CHECK(only && only->Shooting.On && only->Shooting.Fire == Button::R2 && only->Shooting.Weapons.size() == 3 && only->Shooting.Weapons[2].Name == L"GRIFFON");
    CHECK(only && only->Shooting.Weapons[0].Reticle == L"reticle_cross" && only->Shooting.Weapons[1].Reticle == L"reticle_round" &&
          only->Shooting.Weapons[2].Reticle == L"reticle_ornate" && only->Shooting.Ui == L"dirge_ui");
    CHECK(BoneMatches(L"L_HairA_a_Phy_900123", Settings{}.Keep) && !BoneMatches(L"C_Spine_b", Settings{}.Keep));
    // the abilities the shooter's camera stays on through (a normal attack's: the melee combo)
    CHECK(s.CameraAbilities.size() == 2 && BoneMatches(L"PC0000_NAtk_1", s.CameraAbilities) && BoneMatches(L"pc0000_abl_braver", s.CameraAbilities) &&
          !BoneMatches(L"PC0000_LB_1", s.CameraAbilities));
    CHECK(BoneMatches(L"PC0000_NAtk_3", Settings{}.CameraAbilities) && !BoneMatches(L"M_SMN_Ifrit", Settings{}.CameraAbilities));
    // (3.7.1) the stance standing still and the gun's socket
    CHECK(s.Stand.empty() && s.GunSocket == L"Body_Hand_Right01");
    CHECK(only && only->Shooting.Stand == L"st" && only->Shooting.GunSocket == L"Attach_Weapon_Right01");
    CHECK(only && only->Shooting.Clip(only->Shooting.Weapons[0], only->Shooting.Stand) == L"/Game/RebirthSkelCompat/Dirge/Vincent/p000_m001_h_st_remap.p000_m001_h_st_remap");
    // (3.7.1) the motion for how it moves: standing, walking, running; aiming by the way it goes against the way it faces
    const Settings d;
    float rate = 0.0f;
    CHECK(LocomotionFor(d, false, 0.0f, 0.0f, 0.0f, rate) == L"st" && rate == 1.0f);
    CHECK(LocomotionFor(d, true, 10.0f, 0.0f, 0.0f, rate) == L"st_a");
    CHECK(LocomotionFor(d, false, 150.0f, 30.0f, 0.0f, rate) == L"wk" && rate > 0.9f && rate < 1.0f);
    CHECK(LocomotionFor(d, false, 500.0f, 30.0f, 0.0f, rate) == L"rn" && std::fabs(rate - 1.0f) < 1e-5f);
    CHECK(LocomotionFor(d, false, 2000.0f, 0.0f, 0.0f, rate) == L"rn" && rate == 1.5f);
    CHECK(LocomotionFor(d, true, 500.0f, 10.0f, 0.0f, rate) == L"rn_a" && LocomotionFor(d, true, 150.0f, -40.0f, 0.0f, rate) == L"wk_a");
    CHECK(LocomotionFor(d, true, 500.0f, 90.0f, 0.0f, rate) == L"rrn_a" && LocomotionFor(d, true, 500.0f, -90.0f, 0.0f, rate) == L"lrn_a");
    CHECK(LocomotionFor(d, true, 500.0f, 180.0f, 0.0f, rate) == L"brn_a" && LocomotionFor(d, true, 500.0f, 170.0f, -170.0f, rate) == L"rn_a");
    CHECK(LocomotionFor(d, true, 500.0f, 350.0f, 260.0f, rate) == L"rrn_a");
    CHECK(ReloadFor(d, 0.0f) == L"st_rd" && ReloadFor(d, 150.0f) == L"wk_rd" && ReloadFor(d, 520.0f) == L"rn_rd");
    Settings none;
    none.Walking.clear();
    CHECK(LocomotionFor(none, false, 150.0f, 0.0f, 0.0f, rate).empty());
    // (3.7.1) motions turned off in the settings, and a bad motion name
    Config moves;
    CHECK(AppendConfig(R"({"schema": "RebirthSkelCompat/1", "animation_sets": [ {"character": "PC0011_00_Vincent_Standard",
        "shooter": { "motions": { "walking": false, "running": "", "run": "rn_x", "back": "a/b" } } } ]})", L"m.json", moves));
    FinishConfig(moves, [](const std::wstring&) { return true; });
    const AnimSetRow* mrow = moves.FindAnimSetRow(CharacterPackPath(L"PC0011_00_Vincent_Standard"));
    CHECK(mrow && mrow->Shooting.Walking.empty() && mrow->Shooting.Running.empty() && mrow->Shooting.Run == L"rn_x" && mrow->Shooting.Back.empty());
    CHECK(std::any_of(moves.Messages.begin(), moves.Messages.end(), [](const std::wstring& m) { return m.find(L"motion a/b") != std::wstring::npos; }));
    // (3.7.3) aiming: the game's guard-walk (on by default, R1), its button and the guard's abilities
    CHECK(only && only->Shooting.Strafe && only->Shooting.StrafeButton == Button::R1 && BoneMatches(L"PC0000_Guard", only->Shooting.GuardAbilities) &&
          !BoneMatches(L"PC0000_NAtk_1", only->Shooting.GuardAbilities));
    Config strafe;
    CHECK(AppendConfig(R"({"schema": "RebirthSkelCompat/1", "animation_sets": [ {"character": "PC0011_00_Vincent_Standard",
        "shooter": { "strafe": false, "strafe_button": "L1", "guard_abilities": ["*Block*"] } },
        {"character": "PC0000_04_Cloud_ZackCostume", "shooter": { "strafe_button": "Up", "guard_abilities": "x" } } ]})", L"s.json", strafe));
    FinishConfig(strafe, [](const std::wstring&) { return true; });
    const AnimSetRow* srow = strafe.FindAnimSetRow(CharacterPackPath(L"PC0011_00_Vincent_Standard"));
    CHECK(srow && !srow->Shooting.Strafe && srow->Shooting.StrafeButton == Button::L1 && srow->Shooting.GuardAbilities.size() == 1 &&
          BoneMatches(L"PC0004_NAtk_SBlock", srow->Shooting.GuardAbilities));
    const AnimSetRow* brow = strafe.FindAnimSetRow(CharacterPackPath(L"PC0000_04_Cloud_ZackCostume"));
    CHECK(brow && brow->Shooting.Strafe && brow->Shooting.StrafeButton == Button::R1 && brow->Shooting.GuardAbilities.size() == 1);
    CHECK(std::any_of(strafe.Messages.begin(), strafe.Messages.end(), [](const std::wstring& m) { return m.find(L"strafe_button must be") != std::wstring::npos; }));
    CHECK(std::any_of(strafe.Messages.begin(), strafe.Messages.end(), [](const std::wstring& m) { return m.find(L"guard_abilities must be") != std::wstring::npos; }));
    // (3.7.4) upgrades: parts the player owns make a gun stronger
    Config ups;
    CHECK(AppendConfig(R"({"schema": "RebirthSkelCompat/1", "animation_sets": [ {"character": "PC0011_00_Vincent_Standard",
        "shooter": { "weapons": [
            {"name": "CERBERUS", "clip": 6, "interval": 0.22, "reload": 1.3, "range": 3000, "damage_source": "PC0011_Dirge_Cerberus",
             "upgrades": [
                {"item": "key_dirge_cerberus_power", "id": 3860, "row": "P", "levels": 5},
                {"item": "key_dirge_cerberus_barrel", "id": 3863, "row": "R", "range": [1.2, 1.4, 1.6, 1.8, 2.0]},
                {"item": "key_dirge_cerberus_trigger", "interval": [0.92, 0.84, 0.76, 0.68, 0.6]},
                {"item": "key_dirge_cerberus_magazine", "clip": [1, 2, 3, 4, 5], "reload": [0.92, 0.84, 0.76, 0.68, 0.6]},
                {"item": "bad/name", "levels": 3},
                {"item": "key_x", "levels": 0},
                {"item": "key_y", "interval": [0.5, "x"]},
                {"item": "key_z"} ]},
            {"name": "HYDRA", "damage_source": "PC0011_Dirge_Hydra", "upgrades": {"item": "key_dirge_hydra_power", "row": "P", "levels": 5}},
            {"name": "GRIFFON", "damage_source": "PC0011_Dirge_Griffon", "upgrades": 5} ] } } ]})", L"u.json", ups));
    FinishConfig(ups, [](const std::wstring&) { return true; });
    const AnimSetRow* urow = ups.FindAnimSetRow(CharacterPackPath(L"PC0011_00_Vincent_Standard"));
    CHECK(urow && urow->Shooting.Weapons.size() == 3);
    if (urow && urow->Shooting.Weapons.size() == 3)
    {
        const Weapon& c = urow->Shooting.Weapons[0];
        CHECK(c.Upgrades.size() == 4 && c.Upgrades[0].Item == L"key_dirge_cerberus_power" && c.Upgrades[0].Id == 3860 && c.Upgrades[0].Row == L"P" &&
              c.Upgrades[0].MaxLevel() == 5 && c.Upgrades[1].MaxLevel() == 5 && c.Upgrades[2].Id == 0 && c.Upgrades[2].Row.empty() &&
              c.Upgrades[3].Clip.size() == 5 && c.Upgrades[3].Reload.size() == 5);
        CHECK(urow->Shooting.Weapons[1].Upgrades.size() == 1 && urow->Shooting.Weapons[2].Upgrades.empty());
        for (const wchar_t* what : {L"upgrade bad/name", L"upgrade key_x", L"upgrade key_y", L"upgrade key_z", L"GRIFFON: upgrades must be"})
        {
            CHECK(std::any_of(ups.Messages.begin(), ups.Messages.end(), [&](const std::wstring& m) { return m.find(what) != std::wstring::npos; }));
        }
        // none owned: the gun as it is
        std::vector<int> levels;
        Weapon none = Upgraded(c, {0, 0, 0, 0}, &levels);
        CHECK(none.DamageSource == L"PC0011_Dirge_Cerberus" && none.Clip == 6 && std::fabs(none.Interval - 0.22f) < 1e-5f && levels == std::vector<int>({0, 0, 0, 0}));
        CHECK(Upgraded(c, {}).DamageSource == L"PC0011_Dirge_Cerberus" && Upgraded(c, {-1, -1}).Clip == 6);
        // some owned: the row with every tag, the multipliers and rounds of the levels owned
        Weapon some = Upgraded(c, {2, 0, 3, 5}, &levels);
        CHECK(some.DamageSource == L"PC0011_Dirge_Cerberus_P2R0" && levels == std::vector<int>({2, 0, 3, 5}));
        CHECK(std::fabs(some.Interval - 0.22f * 0.76f) < 1e-5f && some.Clip == 11 && std::fabs(some.Reload - 1.3f * 0.6f) < 1e-5f &&
              std::fabs(some.Range - 3000.0f) < 1e-3f);
        Weapon far = Upgraded(c, {0, 4, 0, 0});
        CHECK(far.DamageSource == L"PC0011_Dirge_Cerberus_P0R4" && std::fabs(far.Range - 3000.0f * 1.8f) < 1e-2f);
        // more than its levels: the last level
        Weapon most = Upgraded(c, {9, 7, 99, 6}, &levels);
        CHECK(most.DamageSource == L"PC0011_Dirge_Cerberus_P5R5" && levels == std::vector<int>({5, 5, 5, 5}) && most.Clip == 11 &&
              std::fabs(most.Interval - 0.22f * 0.6f) < 1e-5f);
        // a list shorter than the levels: its last value
        Weapon odd = c;
        odd.Upgrades[2].Levels = 8;
        CHECK(std::fabs(Upgraded(odd, {0, 0, 8, 0}).Interval - 0.22f * 0.6f) < 1e-5f && odd.Upgrades[2].MaxLevel() == 8);
    }
}

// (3.7.7) a form's own shooter: the character's (its joined row's) with the form's settings over it
static void TestFormShooter()
{
    using namespace SkelCompat::Shooter;
    Config cfg;
    // the shooter in one file, the forms in another (as Vincent's are: VincentDirge.json, VincentGalian.json)
    CHECK(AppendConfig(R"({"schema": "RebirthSkelCompat/1", "animation_sets": [ {"characters": ["PC0000_00_Cloud_Standard", "PC0000_04_Cloud_ZackCostume"],
        "shooter": { "assist": 3, "camera": { "distance": 250, "side": 55 }, "motions": { "folder": "/Game/RebirthSkelCompat/Dirge/Vincent", "stand": false },
                     "weapons": [ {"name": "CERBERUS", "clip": 6, "damage_source": "PC0011_Dirge_Cerberus", "upgrades": {"item": "key_power", "row": "P", "levels": 5}},
                                  {"name": "HYDRA", "damage_source": "PC0011_Dirge_Hydra"} ] } } ]})", L"VincentDirge.json", cfg));
    CHECK(AppendConfig(R"({"schema": "RebirthSkelCompat/1", "animation_sets": [ {"characters": ["PC0000_00_Cloud_Standard", "PC0000_04_Cloud_ZackCostume"],
        "forms": { "list": [ { "name": "NORMAL" },
            { "name": "GALIAN BEAST", "pack": "Battle07", "shooter": false },
            { "name": "CHAOS", "model": "/Game/Character/Player/PC0011_10_Chaos/Model/PC0011_10", "as_look": true,
              "fly": { "height": 250 },
              "shooter": { "camera": { "distance": 320 }, "gun_mesh": "/Game/Character/Weapon/WE011_10_Chaos_DeathPenialty/Model/WE0011_10",
                           "motions": { "folder": "/Game/RebirthSkelCompat/Dirge/Chaos", "prefix": "p007_", "fly_stance": "m004_cf_st_a" },
                           "weapons": [ { "name": "DEATH PENALTY", "set": "m001_h", "fly_set": "m004_hf", "damage_source": "PC0011_Chaos_DeathPenalty", "clip": 8,
                                          "interval": 0.35 } ] } },
            { "name": "CERBERUS ONLY", "shooter": { "weapons": [ { "name": "Cerberus", "clip": 12 } ] } },
            { "name": "BAD", "shooter": { "gun_mesh": "Model/WE0011_10", "motions": { "fly_stance": "a/b" },
                                          "weapons": [ { "name": "X", "fly_set": "m/4", "damage_source": "PC0011_X" } ] } },
            { "name": "OFF", "shooter": { "on": false } } ] } } ]})", L"VincentGalian.json", cfg));
    FinishConfig(cfg, [](const std::wstring&) { return true; });
    const AnimSetRow* row = cfg.FindAnimSetRow(CharacterPackPath(L"PC0000_00_Cloud_Standard"));
    const AnimSetRow* zack = cfg.FindAnimSetRow(CharacterPackPath(L"PC0000_04_Cloud_ZackCostume"));
    CHECK(row && zack && row->Forms.List.size() == 6 && zack->Forms.List.size() == 6);
    if (!row || !zack || row->Forms.List.size() != 6 || zack->Forms.List.size() != 6) { return; }
    const auto& forms = row->Forms.List;
    CHECK(forms[0].Shooting == -1 && !forms[0].ShooterSet && forms[1].Shooting == 0 && !forms[1].ShooterSet);
    CHECK(forms[2].Shooting == 1 && forms[2].ShooterSet && forms[5].Shooting == 0 && !forms[5].ShooterSet && !forms[5].ShooterJson);
    // (3.7.8) "as_look": CHAOS's model goes on the game's way with the character's own AnimBlueprint
    CHECK(forms[2].AsLook && forms[2].AnimClass.empty() && !forms[0].AsLook && !forms[1].AsLook && !forms[3].AsLook);
    // each character's row has its own (made from its own row's shooter)
    CHECK(zack->Forms.List[2].ShooterSet && zack->Forms.List[2].ShooterSet != forms[2].ShooterSet);
    if (forms[2].ShooterSet)
    {
        const Settings& c = *forms[2].ShooterSet;
        // the character's settings kept, the form's over them
        CHECK(c.On && c.Assist == 3.0f && c.Side == 55.0f && c.Distance == 320.0f && c.Stand.empty());
        CHECK(c.Folder == L"/Game/RebirthSkelCompat/Dirge/Chaos" && c.Prefix == L"p007_" && c.Suffix == L"_remap" && c.FlyStance == L"m004_cf_st_a");
        CHECK(c.GunMesh == L"/Game/Character/Weapon/WE011_10_Chaos_DeathPenialty/Model/WE0011_10.WE0011_10");
        CHECK(c.Weapons.size() == 1);
        if (c.Weapons.size() == 1)
        {
            const Weapon& w = c.Weapons[0];
            CHECK(w.Name == L"DEATH PENALTY" && w.Set == L"m001_h" && w.FlySet == L"m004_hf" && w.Clip == 8 && w.DamageSource == L"PC0011_Chaos_DeathPenalty" &&
                  w.Upgrades.empty());
            CHECK(c.Clip(w, c.Shot) == L"/Game/RebirthSkelCompat/Dirge/Chaos/p007_m001_h_st_f_remap.p007_m001_h_st_f_remap");
            CHECK(c.FlyClip(w, c.Shot) == L"/Game/RebirthSkelCompat/Dirge/Chaos/p007_m004_hf_st_f_remap.p007_m004_hf_st_f_remap");
            CHECK(c.FlyClip(w, c.Reloading) == L"/Game/RebirthSkelCompat/Dirge/Chaos/p007_m004_hf_st_rd_remap.p007_m004_hf_st_rd_remap");
            CHECK(c.Plain(c.FlyStance) == L"/Game/RebirthSkelCompat/Dirge/Chaos/p007_m004_cf_st_a_remap.p007_m004_cf_st_a_remap");
            CHECK(c.FlyClip(w, L"").empty() && c.Plain(L"").empty());
            Weapon ground = w;
            ground.FlySet.clear();
            CHECK(c.FlyClip(ground, c.Shot) == c.Clip(ground, c.Shot));
        }
    }
    // the character's own shooter is as it was
    CHECK(row->Shooting.Folder == L"/Game/RebirthSkelCompat/Dirge/Vincent" && row->Shooting.Prefix == L"p000_" && row->Shooting.Weapons.size() == 2 &&
          row->Shooting.GunMesh.empty() && row->Shooting.FlyStance.empty() && row->Shooting.Distance == 250.0f);
    // a form's gun of the character's name starts from the character's (its upgrades kept)
    if (forms[3].ShooterSet)
    {
        const Settings& c = *forms[3].ShooterSet;
        CHECK(c.Weapons.size() == 1 && c.Weapons[0].Name == L"Cerberus" && c.Weapons[0].Clip == 12 && c.Weapons[0].DamageSource == L"PC0011_Dirge_Cerberus" &&
              c.Weapons[0].Upgrades.size() == 1);
        CHECK(c.Folder == L"/Game/RebirthSkelCompat/Dirge/Vincent" && c.GunMesh.empty());
    }
    CHECK(forms[3].ShooterSet != nullptr);
    // bad settings: said once (not once per character), the rest kept
    if (forms[4].ShooterSet)
    {
        const Settings& c = *forms[4].ShooterSet;
        CHECK(c.GunMesh.empty() && c.FlyStance.empty() && c.Weapons.size() == 2 && c.Weapons[0].Name == L"CERBERUS");
    }
    const auto count = [&](const wchar_t* what) {
        return std::count_if(cfg.Messages.begin(), cfg.Messages.end(), [&](const std::wstring& m) { return m.find(what) != std::wstring::npos; });
    };
    CHECK(count(L"form BAD shooter") == 1 && count(L"gun_mesh must be a skeletal mesh") == 1 && count(L"motion a/b must be") == 1 &&
          count(L"weapon X: set, fly_set, damage_source and ability must be names") == 1);
    // (3.7.7) the form a pack switch leaves it in: one on the character's own pack stays when the game goes back to its pack
    const FormSettings& f = row->Forms;
    CHECK(f.Plays(0, L"") && f.Plays(0, L"Battle00") && f.Plays(2, L"") && f.Plays(2, L"battle00") && !f.Plays(1, L"") && f.Plays(1, L"Battle07"));
    {
        Config bad;
        CHECK(AppendConfig(R"({"schema": "RebirthSkelCompat/1", "animation_sets": [ {"characters": ["PC0000_00_Cloud_Standard"],
            "forms": [ { "name": "NORMAL" }, { "name": "CHAOS", "model": "/Game/X/Y", "as_look": "yes" } ] } ]})", L"bad.json", bad));
        FinishConfig(bad, [](const std::wstring&) { return true; });
        const AnimSetRow* r = bad.FindAnimSetRow(CharacterPackPath(L"PC0000_00_Cloud_Standard"));
        CHECK(r && r->Forms.List.size() == 2 && !r->Forms.List[1].AsLook);
        CHECK(std::any_of(bad.Messages.begin(), bad.Messages.end(), [](const std::wstring& m) { return m.find(L"bad parts of them ignored") != std::wstring::npos; }));
    }
    CHECK(!f.Plays(2, L"Battle07") && !f.Plays(-1, L"") && !f.Plays(9, L"") && f.IndexOfPack(L"") == 0 && f.IndexOfPack(L"Battle07") == 1);
}

// 3.10.0 skins: a skin.json (as the editor's Build Skins writes it) puts its skeleton in its family and its model on rows.
static void TestSkins()
{
    const std::wstring hub = L"/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00_Skeleton.PC0010_00_Skeleton";
    const std::wstring young = L"/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13_Skeleton.PC0010_13_Skeleton";
    const std::wstring remake = L"/Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00_Skeleton.EB0021_00_Skeleton";
    const char* compat = R"({"schema":"RebirthSkelCompat/1",
        "pairs":[{"method":"family","receiving_skeleton":"/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00_Skeleton.PC0010_00_Skeleton",
                  "animation_skeletons":["/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13_Skeleton.PC0010_13_Skeleton"],
                  "hub":"/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00_Skeleton.PC0010_00_Skeleton","proportions":true}],
        "animation_sets":[{"characters":["PC0000_00_Cloud_Standard"],"battle":["/Game/Motion/Player/PC0010_Sephiroth"],
            "forms":[{"name":"YOUNG"},{"name":"OLDER","model":"/Game/X/PC0010_15","as_look":true,"voice":"own"}],
            "voice":{"bank":"/Game/Sound/Voice/{language}/Character/Player/VO_PC0010_13_YoungSephiroth",
                     "replaces":["/Game/Sound/Voice/{language}/Character/Player/VO_PC0010_00_Sephiroth"]}}]})";
    const char* skin = R"({"schema":"CreateACharacterSkin/1","name":"Remake Sephiroth",
        "characters":["PC0000_00_Cloud_Standard","PC0000_08_Cloud_SoldierNoHelmet"],
        "model":"/Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00.EB0021_00",
        "skeleton":"/Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00_Skeleton.EB0021_00_Skeleton",
        "family":"/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00_Skeleton.PC0010_00_Skeleton",
        "voice":"own","weapon":"/Game/BluePrint/Character/Weapon/WE1021_10_SephirothIllusion_MasamuneCutScale.WE1021_10_SephirothIllusion_MasamuneCutScale_C",
        "anim_blueprint":"","packages":[{"package":"/Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00"}]})";
    const auto installed = [](const std::wstring& name) { return NameEquals(name, SkinsContainer); };
    {
        Config cfg;
        CHECK(AppendConfig(compat, L"fpys.json", cfg));
        CHECK(AppendSkin(skin, L"RemakeSephiroth", cfg));
        CHECK(cfg.Skins.size() == 1 && cfg.Skins[0].Folder == L"RemakeSephiroth" && cfg.Skins[0].Name == L"Remake Sephiroth" &&
              cfg.Skins[0].Speaks.Set && cfg.Skins[0].Speaks.Own && cfg.Skins[0].AnimClass.empty() &&
              cfg.Skins[0].Weapon == L"/Game/BluePrint/Character/Weapon/WE1021_10_SephirothIllusion_MasamuneCutScale.WE1021_10_SephirothIllusion_MasamuneCutScale_C" &&
              cfg.Skins[0].Characters.size() == 2 && cfg.Skins[0].Packages.size() == 1);
        FinishConfig(cfg, installed);
        AttachSkins(cfg, true);
        // the skin's skeleton joins Sephiroth's family (one family: the hub's pair lists both members)
        const Pair* h = cfg.FindForSkeleton(hub);
        CHECK(h && h->Use == Method::Animations && h->FamilyHub == hub && Detail::Lists(h->Animation, young) && Detail::Lists(h->Animation, remake));
        CHECK(MeshPairTo(cfg, remake.c_str(), hub));
        const AnimSetRow* cloud = cfg.FindAnimSetRow(CharacterPackPath(L"PC0000_00_Cloud_Standard"));
        CHECK(cloud && cloud->Skin == 0 && !cloud->SkinOnly && cloud->Forms.HasList());
        // its voice: the skin's ("own") in the field and in forms without one of their own; a form's own wins
        CHECK(cloud && cloud->VoiceOf(-1).Own && cloud->VoiceOf(0).Own && cloud->VoiceOf(1).Own && cloud->HasVoices());
        // a character with no row gets one made for the skin (no sets, no forms menu)
        const AnimSetRow* soldier = cfg.FindAnimSetRow(CharacterPackPath(L"PC0000_08_Cloud_SoldierNoHelmet"));
        CHECK(soldier && soldier->Skin == 0 && soldier->SkinOnly && soldier->Forms.List.size() == 1 && !soldier->Forms.HasList() &&
              soldier->Battle.empty() && soldier->Field.empty());
        CHECK(HasMessage(cfg, L"skin Remake Sephiroth on PC0000_00_Cloud_Standard, PC0000_08_Cloud_SoldierNoHelmet"));
    }
    {
        // its container not installed: the skin is off, its skeleton joins no family, its rows keep their own voice
        Config cfg;
        CHECK(AppendConfig(compat, L"fpys.json", cfg));
        CHECK(AppendSkin(skin, L"RemakeSephiroth", cfg));
        FinishConfig(cfg, [](const std::wstring&) { return false; });
        AttachSkins(cfg, false);
        const Pair* h = cfg.FindForSkeleton(hub);
        CHECK(h && !Detail::Lists(h->Animation, remake) && !cfg.FindForSkeleton(remake));
        const AnimSetRow* cloud = cfg.FindAnimSetRow(CharacterPackPath(L"PC0000_00_Cloud_Standard"));
        CHECK(cloud && cloud->Skin == -1 && cloud->VoiceOf(-1).Set && !cloud->VoiceOf(-1).Own);
        CHECK(!cfg.FindAnimSetRow(CharacterPackPath(L"PC0000_08_Cloud_SoldierNoHelmet")));
        CHECK(HasMessage(cfg, L"is off: its packages are not in the game"));
    }
    {
        // two skins for one character: the first (folder order) wins; files that are not skins are skipped
        Config cfg;
        CHECK(AppendSkin(skin, L"A", cfg));
        CHECK(AppendSkin(skin, L"B", cfg));
        CHECK(!AppendSkin("{\"name\":\"x\"}", L"C", cfg) && !AppendSkin("nope", L"D", cfg));
        CHECK(!AppendSkin(R"({"schema":"CreateACharacterSkin/1","characters":["PC0000_00_Cloud_Standard"]})", L"E", cfg));   // (no model)
        FinishConfig(cfg, installed);
        AttachSkins(cfg, true);
        const AnimSetRow* cloud = cfg.FindAnimSetRow(CharacterPackPath(L"PC0000_00_Cloud_Standard"));
        CHECK(cloud && cloud->Skin == 0 && cloud->SkinOnly && HasMessage(cfg, L"ignored: it wears Remake Sephiroth (A)"));
        CHECK(cfg.Skins.size() == 2 && HasMessage(cfg, L"not a skin the editor made") && HasMessage(cfg, L"is not a skin (") &&
              HasMessage(cfg, L"has no \"model\""));
        // "enabled": false: on no row; "voice": "" is the row's
        Config off;
        CHECK(AppendSkin(R"({"schema":"CreateACharacterSkin/1","name":"Off","enabled":false,"voice":"","model":"/Game/A/B",
                             "characters":["PC0000_00_Cloud_Standard"]})", L"Off", off));
        FinishConfig(off, installed);
        AttachSkins(off, true);
        CHECK(off.Skins.size() == 1 && !off.Skins[0].Speaks.Set && !off.FindAnimSetRow(CharacterPackPath(L"PC0000_00_Cloud_Standard")) &&
              HasMessage(off, L"skin Off is off"));
    }
}

int main()
{
    TestSkins();
    TestEntranceShots();
    TestFormEntrance();
    TestFormTimes();
    TestForms();
    TestAbilities();
    TestJson();
    TestStrings();
    TestPaths();
    TestConfig();
    TestHierarchy();
    TestRenamePlan();
    TestAdoption();
    TestRequiredPaks();
    TestSharedAnimationSkeleton();
    TestMeshFollowsAdoption();
    TestFamilies();
    TestAnimSetRows();
    TestSetImage();
    TestNameObjectMaps();
    TestAutoMatch();
    TestV32Config();
    TestProportions();
    TestNameKeyedMaps();
    TestCutsceneWeaponSocket();
    TestFormCameras();
    TestShooter();
    TestFormShooter();
    if (Failures) { std::printf("%d failure(s)\n", Failures); return 1; }
    std::printf("all core tests passed\n");
    return 0;
}
