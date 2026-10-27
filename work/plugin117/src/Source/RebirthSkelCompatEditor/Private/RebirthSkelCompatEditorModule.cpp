// RebirthSkelCompat editor module: the data object, the Move Maker tab (Window > Rebirth Move Maker), and (editor 1.17)
// the Skin Maker and Parts Builder tabs (Window > Rebirth Skin Maker / Rebirth Parts Builder; right-click a Skeletal
// Mesh in the Content Browser > Create a Character Skin... / Make a Customization Part...).
#include "EndMoveMaker.h"
#include "EndPartsBuilder.h"
#include "EndSkinMaker.h"
#include "ContentBrowserMenuContexts.h"
#include "Engine/SkeletalMesh.h"
#include "Framework/Application/SlateApplication.h"
#include "Framework/Docking/TabManager.h"
#include "Misc/CoreDelegates.h"
#include "Modules/ModuleManager.h"
#include "UObject/UObjectGlobals.h"
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
		FGlobalTabmanager::Get()->RegisterNomadTabSpawner(RebirthSkelCompatEditor::SkinMakerTabName, FOnSpawnTab::CreateStatic(&RebirthSkelCompatEditor::SpawnSkinMakerTab))
			.SetDisplayName(LOCTEXT("SkinMakerTab", "Rebirth Skin Maker"))
			.SetTooltipText(LOCTEXT("SkinMakerTabTip", "Make a skin (a model a character wears in game) from a model and build it into the game (RebirthSkelCompat)."))
			.SetMenuType(ETabSpawnerMenuType::Hidden);
		FGlobalTabmanager::Get()->RegisterNomadTabSpawner(RebirthSkelCompatEditor::PartsBuilderTabName, FOnSpawnTab::CreateStatic(&RebirthSkelCompatEditor::SpawnPartsBuilderTab))
			.SetDisplayName(LOCTEXT("PartsBuilderTab", "Rebirth Parts Builder"))
			.SetTooltipText(LOCTEXT("PartsBuilderTabTip", "Make a Customization part (a model on a character's bone playing motions of its own), see it play, and put it in the game (RebirthSkelCompat)."))
			.SetMenuType(ETabSpawnerMenuType::Hidden);
		UToolMenus::RegisterStartupCallback(FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FRebirthSkelCompatEditorModule::RegisterMenus));
		// 1.11.1: ACL's safety fallback off for the game's settings, in the editor and in the cooker (which compresses the
		// moves again): see TurnOffAclSafetyFallback
		PostEngineInit = FCoreDelegates::OnPostEngineInit.AddLambda([]() { RebirthSkelCompatEditor::TurnOffAclSafetyFallback(); });
		AssetLoaded = FCoreUObjectDelegates::OnAssetLoaded.AddStatic(&RebirthSkelCompatEditor::TurnOffAclSafetyFallbackOnLoad);
	}

	virtual void ShutdownModule() override
	{
		FCoreDelegates::OnPostEngineInit.Remove(PostEngineInit);
		FCoreUObjectDelegates::OnAssetLoaded.Remove(AssetLoaded);
		UToolMenus::UnRegisterStartupCallback(this);
		UToolMenus::UnregisterOwner(this);
		if (FSlateApplication::IsInitialized())
		{
			FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(RebirthSkelCompatEditor::MoveMakerTabName);
			FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(RebirthSkelCompatEditor::SkinMakerTabName);
			FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(RebirthSkelCompatEditor::PartsBuilderTabName);
		}
	}

private:
	FDelegateHandle PostEngineInit;
	FDelegateHandle AssetLoaded;

	void RegisterMenus()
	{
		FToolMenuOwnerScoped Owner(this);
		if (UToolMenu* Menu = UToolMenus::Get()->ExtendMenu(TEXT("LevelEditor.MainMenu.Window")))
		{
			FToolMenuSection& Section = Menu->AddSection(TEXT("RebirthSkelCompat"), LOCTEXT("RebirthSection", "Rebirth"));
			Section.AddMenuEntry(TEXT("RebirthMoveMaker"), LOCTEXT("MoveMakerMenu", "Rebirth Move Maker"),
				LOCTEXT("MoveMakerMenuTip", "Make a character's attacks, abilities and limit breaks from any animation, with their hits, effects and sounds."),
				FSlateIcon(), FUIAction(FExecuteAction::CreateStatic(&FRebirthSkelCompatEditorModule::OpenMoveMaker)));
			Section.AddMenuEntry(TEXT("RebirthSkinMaker"), LOCTEXT("SkinMakerMenu", "Rebirth Skin Maker"),
				LOCTEXT("SkinMakerMenuTip", "Make a skin from a model: the characters that wear it, its family, voice and weapon; built into the game's skins."),
				FSlateIcon(), FUIAction(FExecuteAction::CreateStatic(&FRebirthSkelCompatEditorModule::OpenSkinMaker)));
			Section.AddMenuEntry(TEXT("RebirthPartsBuilder"), LOCTEXT("PartsBuilderMenu", "Rebirth Parts Builder"),
				LOCTEXT("PartsBuilderMenuTip", "Make a Customization part (a wing, a tail): its bone, its idle and synced motions, seen playing on a character; put in the game's Customization catalog."),
				FSlateIcon(), FUIAction(FExecuteAction::CreateStatic(&FRebirthSkelCompatEditorModule::OpenPartsBuilder)));
		}
		// (editor 1.17) right-click a Skeletal Mesh in the Content Browser
		if (UToolMenu* Menu = UToolMenus::Get()->ExtendMenu(TEXT("ContentBrowser.AssetContextMenu.SkeletalMesh")))
		{
			FToolMenuSection& Section = Menu->AddSection(TEXT("RebirthSkelCompat"), LOCTEXT("RebirthAssetSection", "Rebirth"));
			Section.AddMenuEntry(TEXT("RebirthCreateSkin"), LOCTEXT("CreateSkinMenu", "Create a Character Skin..."),
				LOCTEXT("CreateSkinMenuTip", "Open the Skin Maker on this model: a skin characters wear in game (the Customization screen's SKINS page)."),
				FSlateIcon(), FToolUIActionChoice(FToolMenuExecuteAction::CreateStatic(&FRebirthSkelCompatEditorModule::CreateSkinOf)));
			Section.AddMenuEntry(TEXT("RebirthMakePart"), LOCTEXT("MakePartMenu", "Make a Customization Part..."),
				LOCTEXT("MakePartMenuTip", "Open the Parts Builder on this model: a part worn on a character's bone, playing its own motions (the Customization screen's PARTS page)."),
				FSlateIcon(), FToolUIActionChoice(FToolMenuExecuteAction::CreateStatic(&FRebirthSkelCompatEditorModule::MakePartOf)));
		}
	}

	static USkeletalMesh* PickedMesh(const FToolMenuContext& Context)
	{
		const UContentBrowserAssetContextMenuContext* Menu = Context.FindContext<UContentBrowserAssetContextMenuContext>();
		if (!Menu)
		{
			return nullptr;
		}
		for (UObject* Object : Menu->GetSelectedObjects())
		{
			if (USkeletalMesh* Mesh = Cast<USkeletalMesh>(Object))
			{
				return Mesh;
			}
		}
		return nullptr;
	}

	static void OpenMoveMaker()
	{
		RebirthSkelCompatEditor::OpenMoveMakerTab(nullptr);
	}

	static void OpenSkinMaker()
	{
		RebirthSkelCompatEditor::OpenSkinMakerTab(nullptr, nullptr);
	}

	static void OpenPartsBuilder()
	{
		RebirthSkelCompatEditor::OpenPartsBuilderTab(nullptr);
	}

	static void CreateSkinOf(const FToolMenuContext& Context)
	{
		RebirthSkelCompatEditor::OpenSkinMakerTab(nullptr, PickedMesh(Context));
	}

	static void MakePartOf(const FToolMenuContext& Context)
	{
		RebirthSkelCompatEditor::OpenPartsBuilderTab(PickedMesh(Context));
	}
};

IMPLEMENT_MODULE(FRebirthSkelCompatEditorModule, RebirthSkelCompatEditor)

#undef LOCTEXT_NAMESPACE
