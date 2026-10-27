using UnrealBuildTool;

public class EndAssetTools : ModuleRules
{
    public EndAssetTools(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PrivateDependencyModuleNames.AddRange(new string[] {
            "Core", "CoreUObject", "Engine", "UnrealEd", "Slate", "SlateCore", "InputCore", "EditorStyle",
            "PropertyEditor", "Json", "JsonUtilities", "ContentBrowser", "Projects", "ToolMenus", "ApplicationCore"
        });
    }
}
