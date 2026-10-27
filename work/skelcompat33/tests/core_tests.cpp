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

int main()
{
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
    if (Failures) { std::printf("%d failure(s)\n", Failures); return 1; }
    std::printf("all core tests passed\n");
    return 0;
}
