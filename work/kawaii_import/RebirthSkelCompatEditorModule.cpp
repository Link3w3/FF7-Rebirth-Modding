// RebirthSkelCompat editor module: the data object, the Move Maker tab (Window > Rebirth Move Maker), (editor 1.17)
// the Skin Maker and Parts Builder tabs (Window > Rebirth Skin Maker / Rebirth Parts Builder; right-click a Skeletal
// Mesh in the Content Browser > Create a Character Skin... / Make a Customization Part...), and (editor 1.18) the
// AnimBlueprint Maker tab (Window > Rebirth AnimBlueprint Maker; right-click a Skeleton or Skeletal Mesh > Make a
// Rebirth AnimBlueprint...), and (editor 1.20) the Weapon Blueprint Maker tab (Window > Rebirth Weapon Blueprint Maker;
// right-click a Skeletal Mesh > Make a Rebirth Weapon Blueprint...).
#include "EndAnimBlueprintMaker.h"
#include "EndWeaponBlueprintMaker.h"
#include "EndMoveMaker.h"
#include "EndPartsBuilder.h"
#include "EndSkinMaker.h"
#include "Animation/Skeleton.h"
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
		FGlobalTabmanager::Get()->RegisterNomadTabSpawner(RebirthSkelCompatEditor::AnimBlueprintMakerTabName, FOnSpawnTab::CreateStatic(&RebirthSkelCompatEditor::SpawnAnimBlueprintMakerTab))
			.SetDisplayName(LOCTEXT("AnimBlueprintMakerTab", "Rebirth AnimBlueprint Maker"))
			.SetTooltipText(LOCTEXT("AnimBlueprintMakerTabTip", "Make a character's AnimBlueprint for the game from one of the game's own, for the character's skeleton (RebirthSkelCompat)."))
			.SetMenuType(ETabSpawnerMenuType::Hidden);
		FGlobalTabmanager::Get()->RegisterNomadTabSpawner(RebirthSkelCompatEditor::WeaponBlueprintMakerTabName, FOnSpawnTab::CreateStatic(&RebirthSkelCompatEditor::SpawnWeaponBlueprintMakerTab))
			.SetDisplayName(LOCTEXT("WeaponBlueprintMakerTab", "Rebirth Weapon Blueprint Maker"))
			.SetTooltipText(LOCTEXT("WeaponBlueprintMakerTabTip", "Make a weapon Blueprint for the game from one of the game's own weapon blueprints, holding a model of this project (RebirthSkelCompat)."))
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
			FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(RebirthSkelCompatEditor::AnimBlueprintMakerTabName);
			FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(RebirthSkelCompatEditor::WeaponBlueprintMakerTabName);
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
			Section.AddMenuEntry(TEXT("RebirthAnimBlueprintMaker"), LOCTEXT("AnimBlueprintMakerMenu", "Rebirth AnimBlueprint Maker"),
				LOCTEXT("AnimBlueprintMakerMenuTip", "Make a character's AnimBlueprint for the game: one of the game's own (Cloud's player AnimBlueprint by default) made for the character's skeleton, as a ~mods container."),
				FSlateIcon(), FUIAction(FExecuteAction::CreateStatic(&FRebirthSkelCompatEditorModule::OpenAnimBlueprintMaker)));
			// (editor 1.20)
			Section.AddMenuEntry(TEXT("RebirthWeaponBlueprintMaker"), LOCTEXT("WeaponBlueprintMakerMenu", "Rebirth Weapon Blueprint Maker"),
				LOCTEXT("WeaponBlueprintMakerMenuTip", "Make a weapon Blueprint for the game: a real Blueprint of this project made from one of the game's weapon blueprints, holding your model; a skin's Weapon names it."),
				FSlateIcon(), FUIAction(FExecuteAction::CreateStatic(&FRebirthSkelCompatEditorModule::OpenWeaponBlueprintMaker)));
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
			// (editor 1.18)
			Section.AddMenuEntry(TEXT("RebirthMakeAnimBlueprint"), LOCTEXT("MakeAnimBlueprintMenu", "Make a Rebirth AnimBlueprint..."),
				LOCTEXT("MakeAnimBlueprintMenuTip", "Open the AnimBlueprint Maker on this model's skeleton: one of the game's own AnimBlueprints made for it."),
				FSlateIcon(), FToolUIActionChoice(FToolMenuExecuteAction::CreateStatic(&FRebirthSkelCompatEditorModule::MakeAnimBlueprintOf)));
			// (editor 1.20)
			Section.AddMenuEntry(TEXT("RebirthMakeWeaponBlueprint"), LOCTEXT("MakeWeaponBlueprintMenu", "Make a Rebirth Weapon Blueprint..."),
				LOCTEXT("MakeWeaponBlueprintMenuTip", "Open the Weapon Blueprint Maker on this model: a weapon Blueprint for the game holding it, made from one of the game's weapon blueprints."),
				FSlateIcon(), FToolUIActionChoice(FToolMenuExecuteAction::CreateStatic(&FRebirthSkelCompatEditorModule::MakeWeaponBlueprintOf)));
		}
		// (editor 1.18) right-click a Skeleton in the Content Browser
		if (UToolMenu* Menu = UToolMenus::Get()->ExtendMenu(TEXT("ContentBrowser.AssetContextMenu.Skeleton")))
		{
			FToolMenuSection& Section = Menu->AddSection(TEXT("RebirthSkelCompat"), LOCTEXT("RebirthSkeletonSection", "Rebirth"));
			Section.AddMenuEntry(TEXT("RebirthMakeAnimBlueprint"), LOCTEXT("MakeAnimBlueprintMenu", "Make a Rebirth AnimBlueprint..."),
				LOCTEXT("MakeAnimBlueprintSkeletonMenuTip", "Open the AnimBlueprint Maker on this skeleton: one of the game's own AnimBlueprints made for it."),
				FSlateIcon(), FToolUIActionChoice(FToolMenuExecuteAction::CreateStatic(&FRebirthSkelCompatEditorModule::MakeAnimBlueprintOf)));
		}
	}

	// The skeleton picked in the Content Browser: a Skeleton, or a Skeletal Mesh's.
	static USkeleton* PickedSkeleton(const FToolMenuContext& Context)
	{
		const UContentBrowserAssetContextMenuContext* Menu = Context.FindContext<UContentBrowserAssetContextMenuContext>();
		if (!Menu)
		{
			return nullptr;
		}
		for (UObject* Object : Menu->GetSelectedObjects())
		{
			if (USkeleton* Skeleton = Cast<USkeleton>(Object))
			{
				return Skeleton;
			}
			if (USkeletalMesh* Mesh = Cast<USkeletalMesh>(Object))
			{
				if (Mesh->Skeleton)
				{
					return Mesh->Skeleton;
				}
			}
		}
		return nullptr;
	}

	static void OpenAnimBlueprintMaker()
	{
		RebirthSkelCompatEditor::OpenAnimBlueprintMakerTab(nullptr);
	}

	static void MakeAnimBlueprintOf(const FToolMenuContext& Context)
	{
		RebirthSkelCompatEditor::OpenAnimBlueprintMakerTab(PickedSkeleton(Context));
	}

	static void OpenWeaponBlueprintMaker()
	{
		RebirthSkelCompatEditor::OpenWeaponBlueprintMakerTab(nullptr);
	}

	static void MakeWeaponBlueprintOf(const FToolMenuContext& Context)
	{
		RebirthSkelCompatEditor::OpenWeaponBlueprintMakerTab(PickedMesh(Context));
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
