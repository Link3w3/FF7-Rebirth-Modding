// KawaiiPhysics' editor module (End editor, UE 4.26): the AnimGraph node, its viewport tools (the collision shapes'
// handles) and its export to Create a Character System's "kawaii" entries.

using UnrealBuildTool;

public class KawaiiPhysicsEd : ModuleRules
{
	public KawaiiPhysicsEd(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PrivateDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "ApplicationCore", "KawaiiPhysics" });
		PrivateDependencyModuleNames.AddRange(new string[] { "AnimGraph", "AnimGraphRuntime", "BlueprintGraph", "Persona", "UnrealEd",
			"Slate", "SlateCore", "EditorStyle", "PropertyEditor" });
	}
}
