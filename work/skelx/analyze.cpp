#include "../skelcompat/src/SkelCompatCore.hpp"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <set>
using namespace SkelCompat;
static BoneTable Load(const char* path)
{
    BoneTable t; std::ifstream f(path); std::string n; int p;
    while (f >> n >> p) { t.Names.push_back(Widen(n)); t.Parents.push_back(p); }
    return t;
}
static void Report(const char* memberName, const BoneTable& memberSkel, const BoneTable& memberMesh, const char* hubName, const BoneTable& hubSkel)
{
    const auto map = BuildTrackRemap(memberSkel, hubSkel);
    int carried = 0; for (int m : map) carried += m >= 0;
    // mesh bones of the member that the hub lacks entirely / places differently
    int meshOnly = 0, differ = 0;
    for (size_t i = 0; i < memberMesh.Names.size(); ++i)
    {
        const int s = hubSkel.Find(memberMesh.Names[i]);
        if (s < 0) ++meshOnly;
    }
    const RenamePlan plan = PlanConflictRenames(memberMesh, hubSkel);
    const RenamePlan forBoth = PlanConflictRenamesFor(memberMesh, hubSkel, {&memberSkel});
    std::printf("   PlanConflictRenamesFor: %zu bones; vs hub %s, vs own %s\n", forBoth.Bones.size(), CheckMeshAgainstSkeleton(ApplyRenamePlan(memberMesh, forBoth), hubSkel).Compatible ? "OK" : "REFUSED", CheckMeshAgainstSkeleton(ApplyRenamePlan(memberMesh, forBoth), memberSkel).Compatible ? "OK" : "REFUSED");
    const BoneTable renamed = ApplyRenamePlan(memberMesh, plan);
    const MeshCheck vsHubBefore = CheckMeshAgainstSkeleton(memberMesh, hubSkel);
    const MeshCheck vsHub = CheckMeshAgainstSkeleton(renamed, hubSkel);
    const MeshCheck vsOwn = CheckMeshAgainstSkeleton(renamed, memberSkel);
    const MeshCheck vsOwnBefore = CheckMeshAgainstSkeleton(memberMesh, memberSkel);
    // descendant-closed renames
    std::vector<int32_t> closed = plan.Bones;
    std::vector<char> mark(memberMesh.Names.size(), 0);
    for (int b : plan.Bones) mark[b] = 1;
    for (size_t i = 1; i < memberMesh.Names.size(); ++i) if (mark[memberMesh.Parents[i]] && !mark[i]) { mark[i] = 1; closed.push_back((int)i); }
    std::sort(closed.begin(), closed.end());
    RenamePlan cp; cp.Bones = closed;
    const BoneTable renamed2 = ApplyRenamePlan(memberMesh, cp);
    const MeshCheck c2Hub = CheckMeshAgainstSkeleton(renamed2, hubSkel), c2Own = CheckMeshAgainstSkeleton(renamed2, memberSkel);
    std::printf("%s -> hub %s: member skeleton %zu bones, %d carried over; member mesh %zu bones, %d not on hub at all\n",
                memberName, hubName, memberSkel.Names.size(), carried, memberMesh.Names.size(), meshOnly);
    std::printf("   mesh vs hub before renames: %s %s\n", vsHubBefore.Compatible ? "OK" : "REFUSED", Narrow(vsHubBefore.Problem).c_str());
    std::printf("   mesh vs own skeleton before: %s\n", vsOwnBefore.Compatible ? "OK" : Narrow(vsOwnBefore.Problem).c_str());
    std::printf("   rename plan: %zu bones; after: vs hub %s, vs own %s %s\n", plan.Bones.size(), vsHub.Compatible ? "OK" : "REFUSED",
                vsOwn.Compatible ? "OK" : "REFUSED", Narrow(vsOwn.Problem).c_str());
    std::printf("   descendant-closed renames: %zu bones; vs hub %s, vs own %s\n", closed.size(), c2Hub.Compatible ? "OK" : "REFUSED", c2Own.Compatible ? "OK" : "REFUSED");
    std::wstring sample; for (size_t k = 0; k < plan.Bones.size() && k < 25; ++k) sample += memberMesh.Names[plan.Bones[k]] + L" ";
    std::printf("   renamed: %s\n", Narrow(sample).c_str());
}
int main()
{
    const BoneTable cs = Load("PC0000_00_Skeleton.bones"), ss = Load("PC0010_00_Skeleton.bones"), vs = Load("PC0011_00_Skeleton.bones");
    const BoneTable cm = Load("PC0000_00.bones"), sm = Load("PC0010_00.bones"), vm = Load("PC0011_00.bones");
    Report("Vincent", vs, vm, "Cloud", cs);
    Report("Sephiroth", ss, sm, "Cloud", cs);
    Report("Cloud", cs, cm, "Sephiroth", ss);
    Report("Vincent", vs, vm, "Sephiroth", ss);
    Report("Cloud", cs, cm, "Vincent", vs);
    Report("Sephiroth", ss, sm, "Vincent", vs);
    // classic adoption: Cloud's animations onto Sephiroth / Vincent (receiver keeps its skeleton)
    for (auto [n, from, to] : {std::tuple{"Cloud->Seph", &cs, &ss}, std::tuple{"Cloud->Vincent", &cs, &vs}, std::tuple{"Seph->Cloud", &ss, &cs}, std::tuple{"Vincent->Cloud", &vs, &cs}})
    {
        const auto map = BuildTrackRemap(*from, *to); int c = 0; for (int m : map) c += m >= 0;
        std::printf("tracks %s: %d of %zu carry over\n", n, c, from->Names.size());
    }
}
