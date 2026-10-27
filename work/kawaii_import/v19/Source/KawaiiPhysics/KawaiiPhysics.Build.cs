// KawaiiPhysics (pafuhana1213, MIT License) for UE 4.26, with the newest KawaiiPhysics' features fused in; its simulation
// is Create a Character System's (Private/Solver: SkelCompatCore.hpp and KawaiiSolver.hpp, the game mod's own files), so
// the End editor's preview moves the bones as FINAL FANTASY VII REBIRTH will.

using System.IO;
using UnrealBuildTool;

public class KawaiiPhysics : ModuleRules
{
	public KawaiiPhysics(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;
		// the solver (the game mod's files) needs C++17
		CppStandard = CppStandardVersion.Cpp17;

		PrivateIncludePaths.Add(Path.Combine(ModuleDirectory, "Private", "Solver"));

		PublicDependencyModuleNames.AddRange(
			new string[]
			{
				"Core",
				"AnimGraphRuntime",
			}
			);

		PrivateDependencyModuleNames.AddRange(
			new string[]
			{
				"CoreUObject",
				"Engine",
			}
			);
	}
}
