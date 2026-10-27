// RebirthSkelCompat editor module: the data object, and the Move Maker tab (Window > Rebirth Move Maker).
#include "EndMoveMaker.h"
#include "Framework/Application/SlateApplication.h"
#include "Framework/Docking/TabManager.h"
#include "Modules/ModuleManager.h"
#include "ToolMenus.h"
#include "Widgets/Docking/SDockTab.h"

#define LOCTEXT_NAMESPACE "RebirthSkelCompatEditorModule"

class FRebirthSkelCompatEditorModule : public IModuleInterface
{
public:
	virtual void StartupModule() override
	{
		FGlobalTabmanager::Get()->RegisterNomadTabSpawner(RebirthSkelCompatEditor::MoveMakerTabName, FOnSpawnTab::CreateStatic(&RebirthSkelCompatEditor::SpawnMoveMakerTab))
			.SetDisplayName(LOCTEXT("MoveMakerTab", "Rebirth Move Maker"))
			.SetTooltipText(LOCTEXT("MoveMakerTabTip", "Make a character's attacks, abilities and limit breaks from any animation (RebirthSkelCompat)."))
			.SetMenuType(ETabSpawnerMenuType::Hidden);
		UToolMenus::RegisterStartupCallback(FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FRebirthSkelCompatEditorModule::RegisterMenus));
	}

	virtual void ShutdownModule() override
	{
		UToolMenus::UnRegisterStartupCallback(this);
		UToolMenus::UnregisterOwner(this);
		if (FSlateApplication::IsInitialized())
		{
			FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(RebirthSkelCompatEditor::MoveMakerTabName);
		}
	}

private:
	void RegisterMenus()
	{
		FToolMenuOwnerScoped Owner(this);
		if (UToolMenu* Menu = UToolMenus::Get()->ExtendMenu(TEXT("LevelEditor.MainMenu.Window")))
		{
			FToolMenuSection& Section = Menu->AddSection(TEXT("RebirthSkelCompat"), LOCTEXT("RebirthSection", "Rebirth"));
			Section.AddMenuEntry(TEXT("RebirthMoveMaker"), LOCTEXT("MoveMakerMenu", "Rebirth Move Maker"),
				LOCTEXT("MoveMakerMenuTip", "Make a character's attacks, abilities and limit breaks from any animation, with their hits, effects and sounds."),
				FSlateIcon(), FUIAction(FExecuteAction::CreateStatic(&FRebirthSkelCompatEditorModule::OpenMoveMaker)));
		}
	}

	static void OpenMoveMaker()
	{
		RebirthSkelCompatEditor::OpenMoveMakerTab(nullptr);
	}
};

IMPLEMENT_MODULE(FRebirthSkelCompatEditorModule, RebirthSkelCompatEditor)

#undef LOCTEXT_NAMESPACE
