# RebirthSkelCompat

KH3-style skeleton compatibility for FINAL FANTASY VII REBIRTH: meshes on a *receiving skeleton* play the
animations (and AnimBlueprints) of an *animation skeleton*, for any number of skeletons, in any direction.

| Part | Where | What |
|---|---|---|
| UE4SS C++ mod | `src/` -> game `ue4ss\Mods\RebirthSkelCompat\dlls\main.dll` | Adopts animations onto receiving skeletons (`"animations"`), rebinds receiving meshes inside `USkeletalMesh::PostLoad` (`"mesh"`), gathers skeletons that share animations on a hub (`"family"`, 3.0), late-rebinds meshes that were already loaded, repairs refused AnimBlueprints, F9 report. |
| Editor data object | `C:\FF7R2UProj\Plugins\RebirthSkelCompat` | `Skeleton Compatibility Data Object` (Add New > Animation): Validate, Apply To Skeletons (Asset User Data that cooks with your pak), Export Json. |

## Families (3.0)

An animation asset belongs to one skeleton, and retail Rebirth compares skeletons by pointer, so two
skeletons cannot both play one animation as is. A family gathers its skeletons on one hub: every
animation of the other members is adopted onto the hub and every mesh of the other members is
rebound to it. `SkelCompat::FinishConfig` (in `src/SkelCompatCore.hpp`) builds families from
`"family"` entries and from `"animations"` pairs that would otherwise fight over the same animations
(reverse pairs, chains, several receivers of one skeleton), and turns each into one `"animations"`
pair plus one `"mesh"` pair per member, so the run-time code only knows those two methods.
A family member's mesh gets a hierarchy fix that passes the engine's test for the hub's
AnimBlueprints and for its own (`SkelCompat::CloseRenamePlan`), and keeps its own skeleton's sockets.

## Build

```
python build_dll.py --install     # compile + verify imports against the installed UE4SS.dll + install
python build_plugin.py            # UnrealBuildTool, EndEditor target, only the plugin module
```

`build_dll.py` uses the same MSVC 14.44 / Windows SDK 10.0.26100 / UE4SS c0a8d4c SDK as the
RebirthSkeletonObserver build. Outputs and logs go to `build\<UTC stamp>\`.

## Runtime pair sources

1. `ue4ss\Mods\RebirthSkelCompat\compat\*.json`
2. `End\Content\Paks\~mods\**\*.skelcompat.json` (next to a mod's pak)
3. `BP_SkelCompatUserData` (parent: AssetUserData) on the receiving skeleton's or mesh's Asset User Data,
   array variable `AnimationSkeletons` (+ optional `ReceivingMeshes`).

`tests/core_tests.cpp` covers the portable core (JSON, paths, config merging and families, the port of
`USkeleton::IsCompatibleMesh`, the hierarchy fix): `g++ -std=c++20 tests/core_tests.cpp && ./a.out`.
