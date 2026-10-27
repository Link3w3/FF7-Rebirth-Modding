#include "/work/cacs3110/src/SkelCompatCore.hpp"
#include <cstdio>
#include <fstream>
using namespace SkelCompat;
static BoneTable Load(const char* path)
{
    BoneTable t; std::ifstream f(path); std::string n; int p;
    while (f >> n >> p) { t.Names.push_back(Widen(n)); t.Parents.push_back(p); }
    return t;
}
int main(int argc, char** argv)
{
    const BoneTable hub = Load(argv[1]), mesh = Load(argv[2]), own = Load(argv[3]);
    std::printf("hub %zu bones, mesh %zu, own skeleton %zu\n", hub.Names.size(), mesh.Names.size(), own.Names.size());
    const MeshCheck before = CheckMeshAgainstSkeleton(mesh, hub);
    std::printf("mesh vs hub before renames: %s %s\n", before.Compatible ? "OK" : "REFUSED", Narrow(before.Problem).c_str());
    const MeshCheck vsOwn = CheckMeshAgainstSkeleton(mesh, own);
    std::printf("mesh vs own: %s %s\n", vsOwn.Compatible ? "OK" : "REFUSED", Narrow(vsOwn.Problem).c_str());
    const RenamePlan plan = PlanConflictRenamesFor(mesh, hub, {&own});
    const BoneTable after = ApplyRenamePlan(mesh, plan);
    const MeshCheck a = CheckMeshAgainstSkeleton(after, hub), b = CheckMeshAgainstSkeleton(after, own);
    std::printf("plan possible %d, %zu renames; after: vs hub %s %s; vs own %s %s\n", plan.Possible, plan.Bones.size(), a.Compatible ? "OK" : "REFUSED", Narrow(a.Problem).c_str(), b.Compatible ? "OK" : "REFUSED", Narrow(b.Problem).c_str());
    int shown = 0;
    for (int i : plan.Bones) { if (shown++ < 40) std::printf("  rename %s (parent %s)\n", Narrow(mesh.Names[i]).c_str(), mesh.Parents[i] >= 0 ? Narrow(mesh.Names[mesh.Parents[i]]).c_str() : "-"); }
    // bones of the mesh on the hub under another parent
    int differ = 0, missing = 0;
    for (size_t i = 1; i < mesh.Names.size(); ++i)
    {
        const int h = hub.Find(mesh.Names[i]);
        if (h < 0) { ++missing; continue; }
        const std::wstring mp = mesh.Names[mesh.Parents[i]];
        const std::wstring hp = hub.Parents[h] >= 0 ? hub.Names[hub.Parents[h]] : L"-";
        if (!NameEquals(mp, hp)) { if (differ++ < 30) std::printf("  differ: %s mesh parent %s, hub parent %s\n", Narrow(mesh.Names[i]).c_str(), Narrow(mp).c_str(), Narrow(hp).c_str()); }
    }
    std::printf("mesh bones not on the hub: %d; on the hub under another parent: %d\n", missing, differ);
    const auto map = BuildTrackRemap(own, hub); int c = 0; for (int m : map) c += m >= 0;
    std::printf("tracks own->hub: %d of %zu carry over\n", c, own.Names.size());
}
