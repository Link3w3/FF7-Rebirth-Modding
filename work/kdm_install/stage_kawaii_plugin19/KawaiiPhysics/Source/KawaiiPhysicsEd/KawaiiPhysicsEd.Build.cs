// KawaiiPhysics' editor module (End editor, UE 4.26): the AnimGraph node, its viewport tools (the collision shapes'
// handles), its export to Create a Character System's "kawaii" entries and (1.8) its import from them.

using UnrealBuildTool;

public class KawaiiPhysicsEd : ModuleRules
{
	public KawaiiPhysicsEd(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PrivateDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "ApplicationCore", "KawaiiPhysics" });
		PrivateDependencyModuleNames.AddRange(new string[] { "AnimGraph", "AnimGraphRuntime", "BlueprintGraph", "Persona", "UnrealEd",
			"Slate", "SlateCore", "EditorStyle", "PropertyEditor" });
		// (1.8) Import From Game: the new AnimBlueprint's registration, the file dialog, the Content Browser menus
		PrivateDependencyModuleNames.AddRange(new string[] { "AssetRegistry", "DesktopPlatform", "ToolMenus", "ContentBrowser" });
	}
}
