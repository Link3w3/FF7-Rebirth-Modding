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

int main()
{
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
    if (Failures) { std::printf("%d failure(s)\n", Failures); return 1; }
    std::printf("all core tests passed\n");
    return 0;
}
