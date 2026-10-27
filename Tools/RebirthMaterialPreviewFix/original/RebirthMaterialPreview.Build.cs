using UnrealBuildTool;

public class RebirthMaterialPreview : ModuleRules
{
    public RebirthMaterialPreview(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PrivateDependencyModuleNames.AddRange(new[] {
            "Core", "CoreUObject", "Engine", "UnrealEd", "AssetTools", "AssetRegistry",
            "Slate", "SlateCore", "ContentBrowser", "InputCore", "EditorStyle", "ToolMenus", "Niagara", "NiagaraCore",
            "RenderCore", "RHI", "Json", "JsonUtilities", "EndDataObject", "PropertyEditor", "BonamikRt", "Persona", "AdvancedPreviewScene", "AnimationEditor", "SkeletonEditor", "SkeletalMeshEditor", "AnimGraph", "AnimGraphRuntime", "Kismet"
        });
    }
}
