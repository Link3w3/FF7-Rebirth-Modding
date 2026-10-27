#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"
#include "EditorViewportCommands.h"
#include "Framework/Commands/InputBindingManager.h"
#include "Framework/Commands/UICommandInfo.h"
#include "EndCatalogTools.h"
#include "EndAssetToolsIntegration.h"

DEFINE_LOG_CATEGORY_STATIC(LogEndAssetTools, Log, All);

namespace EndAssetTools
{
    // CE's viewport binds these three SQEX modes, but its original command
    // registration omitted them. Repair only missing commands before a viewport
    // is constructed; keep the original binding context and any existing entries.
    static bool RegisterMissingViewportCommand(const TSharedRef<FBindingContext>& Context,
        TSharedPtr<FUICommandInfo>& Command, const TCHAR* Name, const TCHAR* Label, const TCHAR* Description)
    {
        if (Command.IsValid()) { return false; }
        Command = FInputBindingManager::Get().FindCommandInContext(Context->GetContextName(), FName(Name));
        if (!Command.IsValid())
        {
            FUICommandInfo::MakeCommandInfo(Context, Command, FName(Name),
                FText::FromString(Label), FText::FromString(Description), FSlateIcon(),
                EUserInterfaceActionType::RadioButton, FInputChord());
        }
        return Command.IsValid();
    }

    static void RepairViewportCommands()
    {
        check(IsInGameThread());
        FEditorViewportCommands::Register();
        const FEditorViewportCommands& Registered = FEditorViewportCommands::Get();
        TSharedPtr<FBindingContext> Context = FInputBindingManager::Get().GetContextByName(FName(TEXT("EditorViewport")));
        if (!Context.IsValid() || Context.Get() != static_cast<const FBindingContext*>(&Registered))
        {
            UE_LOG(LogEndAssetTools, Error, TEXT("EditorViewport command context identity mismatch; repair refused."));
            return;
        }
        FEditorViewportCommands& Commands = const_cast<FEditorViewportCommands&>(Registered);
        int32 Repaired = 0;
        Repaired += RegisterMissingViewportCommand(Context.ToSharedRef(), Commands.MassiveEnvironmentMode,
            TEXT("MassiveEnvironmentMode"), TEXT("Massive Environment"), TEXT("Visualize the SQEX massive environment view mode.")) ? 1 : 0;
        Repaired += RegisterMissingViewportCommand(Context.ToSharedRef(), Commands.MeshletColorationMode,
            TEXT("MeshletColorationMode"), TEXT("Meshlet Coloration"), TEXT("Visualize SQEX meshlets.")) ? 1 : 0;
        Repaired += RegisterMissingViewportCommand(Context.ToSharedRef(), Commands.StreamedTextureResolutionMode,
            TEXT("StreamedTextureResolutionMode"), TEXT("Streamed Texture Resolution"), TEXT("Visualize streamed texture resolution.")) ? 1 : 0;
        UE_LOG(LogEndAssetTools, Display, TEXT("SQEX viewport commands ready: repaired=%d valid=%d/%d/%d context=EditorViewport"),
            Repaired, Commands.MassiveEnvironmentMode.IsValid() ? 1 : 0,
            Commands.MeshletColorationMode.IsValid() ? 1 : 0, Commands.StreamedTextureResolutionMode.IsValid() ? 1 : 0);
    }
}

class FEndAssetToolsModule final : public IModuleInterface
{
public:
    virtual bool SupportsDynamicReloading() override { return false; }
    virtual void StartupModule() override
    {
        if (!IsRunningCommandlet())
        {
            EndAssetTools::RepairViewportCommands();
            EndAssetTools::RegisterCatalogTools();
            EndAssetTools::RegisterIntegration();
        }
    }
    virtual void ShutdownModule() override
    {
        if (!IsRunningCommandlet())
        {
            EndAssetTools::UnregisterIntegration();
            EndAssetTools::UnregisterCatalogTools();
        }
    }
    // Other editor viewports still own these binding-context entries at module
    // shutdown. They contain no delegates into this DLL and must remain valid.
};

IMPLEMENT_MODULE(FEndAssetToolsModule, EndAssetTools)
