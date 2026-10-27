#include "CoreMinimal.h"
#include "EndAssetToolsIntegration.h"
#include "EndCatalogTools.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformProcess.h"
#include "HAL/FileManager.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "ToolMenus.h"

DEFINE_LOG_CATEGORY_STATIC(LogEndAssetIntegration, Log, All);

namespace
{
    FDelegateHandle MenuHandle;
    void LaunchCookedTools()
    {
        const TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("EndAssetTools"));
        if (!Plugin.IsValid()) { return; }
        const FString Directory = FPaths::ConvertRelativePathToFull(FPaths::Combine(Plugin->GetBaseDir(), TEXT("Tools/UAssetGUI")));
        const FString Executable = FPaths::Combine(Directory, TEXT("UAssetGUI.exe"));
        if (!IFileManager::Get().FileExists(*Executable))
        {
            UE_LOG(LogEndAssetIntegration, Error, TEXT("Bundled UAssetGUI is missing: %s"), *Executable);
            return;
        }
        // The archive has no verified command-line asset handoff contract. Open
        // its original GUI; choosing an input and output stays inside that tool.
        uint32 ProcessId = 0;
        FProcHandle Process = FPlatformProcess::CreateProc(*Executable, TEXT(""), true, false, false, &ProcessId, 0, *Directory, nullptr);
        if (Process.IsValid())
        {
            UE_LOG(LogEndAssetIntegration, Display, TEXT("Opened bundled cooked-package tools, process=%u"), ProcessId);
            FPlatformProcess::CloseProc(Process);
        }
        else
        {
            UE_LOG(LogEndAssetIntegration, Error, TEXT("Unable to start UAssetGUI; the tool requires Microsoft Windows Desktop Runtime 8."));
        }
    }
    void RegisterMenus()
    {
        FToolMenuOwnerScoped Owner(TEXT("EndAssetTools"));
        UToolMenu* Menu = UToolMenus::Get()->ExtendMenu(TEXT("LevelEditor.MainMenu.Window"));
        FToolMenuSection& Section = Menu->AddSection(TEXT("EndAssetTools"), FText::FromString(TEXT("FFVII Rebirth Tools")));
        Section.AddMenuEntry(TEXT("EndAssetTools.Open"), FText::FromString(TEXT("FFVII Rebirth Asset Tools")),
            FText::FromString(TEXT("Notify editors, EndAnimSet animation references, skeleton and effect catalogs.")), FSlateIcon(),
            FUIAction(FExecuteAction::CreateStatic(&EndAssetTools::OpenCatalogTools)));
        Section.AddMenuEntry(TEXT("EndAssetTools.UAssetGUI"), FText::FromString(TEXT("UAssetGUI Cooked Package Tools")),
            FText::FromString(TEXT("Open the supplied UAssetGUI tools for cooked package, mapping, row, notify and effect payload editing.")), FSlateIcon(),
            FUIAction(FExecuteAction::CreateStatic(&LaunchCookedTools)));
        UE_LOG(LogEndAssetIntegration, Display, TEXT("End asset tools registered in Window > FFVII Rebirth Tools."));
    }
    void TestIntegration()
    {
        if (!IsInGameThread() || !FParse::Param(FCommandLine::Get(), TEXT("EndAssetToolsOwnedProbe"))) { return; }
        const TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
        UToolMenu* Menu = UToolMenus::Get()->FindMenu(TEXT("LevelEditor.MainMenu.Window"));
        const bool NativeEntry = Menu && Menu->ContainsEntry(TEXT("EndAssetTools.Open"));
        const bool CookedEntry = Menu && Menu->ContainsEntry(TEXT("EndAssetTools.UAssetGUI"));
        const TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("EndAssetTools"));
        bool RuntimePresent = Plugin.IsValid();
        for (const TCHAR* File : { TEXT("UAssetGUI.exe"), TEXT("UAssetGUI.dll"), TEXT("UAssetGUI.dll.config"), TEXT("UAssetGUI.deps.json"), TEXT("UAssetGUI.runtimeconfig.json"), TEXT("LICENSE"), TEXT("NOTICE.md") })
        {
            RuntimePresent = RuntimePresent && IFileManager::Get().FileExists(*FPaths::Combine(Plugin->GetBaseDir(), TEXT("Tools/UAssetGUI"), File));
        }
        Report->SetBoolField(TEXT("native_window_menu_entry"), NativeEntry);
        Report->SetBoolField(TEXT("cooked_tools_window_menu_entry"), CookedEntry);
        Report->SetBoolField(TEXT("bundled_original_runtime_and_notices_present"), RuntimePresent);
        Report->SetBoolField(TEXT("passed"), NativeEntry && CookedEntry && RuntimePresent);
        Report->SetBoolField(TEXT("standalone_application_executed_by_test"), false);
        FString Json; FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json));
        const FString Directory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("EndAssetTools"));
        IFileManager::Get().MakeDirectory(*Directory, true);
        FFileHelper::SaveStringToFile(Json, *FPaths::Combine(Directory, TEXT("IntegrationSelfTest.json")));
    }
    FAutoConsoleCommand OpenCommand(TEXT("EndAssetTools.Open"), TEXT("Open native FFVII Rebirth Asset Tools."), FConsoleCommandDelegate::CreateStatic(&EndAssetTools::OpenCatalogTools));
    FAutoConsoleCommand LaunchCommand(TEXT("EndAssetTools.UAssetGUI"), TEXT("Open bundled UAssetGUI cooked-package tools."), FConsoleCommandDelegate::CreateStatic(&LaunchCookedTools));
    FAutoConsoleCommand TestCommand(TEXT("EndAssetTools.IntegrationSelfTest"), TEXT("Check owned tool menu/resource integration; requires -EndAssetToolsOwnedProbe."), FConsoleCommandDelegate::CreateStatic(&TestIntegration));
}
namespace EndAssetTools
{
    void RegisterIntegration() { MenuHandle = UToolMenus::RegisterStartupCallback(FSimpleMulticastDelegate::FDelegate::CreateStatic(&RegisterMenus)); }
    void UnregisterIntegration()
    {
        UToolMenus::UnRegisterStartupCallback(MenuHandle);
        UToolMenus::UnregisterOwner(TEXT("EndAssetTools"));
    }
}
