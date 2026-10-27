// KawaiiPhysics' editor module (End editor, UE 4.26): the AnimGraph node's edit mode (its shapes' handles), and (1.8)
// Import From Game: right-click a Skeletal Mesh in the Content Browser > Import KawaiiPhysics From Game... (an
// AnimBlueprint of its own made with a game entry's nodes), or an AnimBlueprint > Import KawaiiPhysics From Game...
// (its KawaiiPhysics nodes replaced by an entry's); Window > Import KawaiiPhysics From Game (every entry)... (each entry
// of a file into an AnimBlueprint of its model's).

#include "KawaiiPhysicsEd.h"
#include "Animation/AnimBlueprint.h"
#include "ContentBrowserMenuContexts.h"
#include "Engine/SkeletalMesh.h"
#include "KawaiiPhysicsEditMode.h"
#include "KawaiiPhysicsGameImport.h"
#include "Modules/ModuleManager.h"
#include "Textures/SlateIcon.h"
#include "ToolMenus.h"

#define LOCTEXT_NAMESPACE "FKawaiiPhysicsModuleEd"

void FKawaiiPhysicsEdModule::StartupModule()
{
	FEditorModeRegistry::Get().RegisterMode<FKawaiiPhysicsEditMode>("AnimGraph.SkeletalControl.KawaiiPhysics", LOCTEXT("FKawaiiPhysicsEditMode", "Kawaii Physics"), FSlateIcon(), false);
	UToolMenus::RegisterStartupCallback(FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FKawaiiPhysicsEdModule::RegisterMenus));
}

void FKawaiiPhysicsEdModule::ShutdownModule()
{
	UToolMenus::UnRegisterStartupCallback(this);
	UToolMenus::UnregisterOwner(this);
	FEditorModeRegistry::Get().UnregisterMode("AnimGraph.SkeletalControl.KawaiiPhysics");
}

void FKawaiiPhysicsEdModule::RegisterMenus()
{
	FToolMenuOwnerScoped Owner(this);
	if (UToolMenu* Menu = UToolMenus::Get()->ExtendMenu(TEXT("ContentBrowser.AssetContextMenu.SkeletalMesh")))
	{
		FToolMenuSection& Section = Menu->AddSection(TEXT("KawaiiPhysics"), LOCTEXT("KawaiiSection", "KawaiiPhysics"));
		Section.AddMenuEntry(TEXT("KawaiiPhysicsImportFromGame"), LOCTEXT("ImportForMeshMenu", "Import KawaiiPhysics From Game..."),
			LOCTEXT("ImportForMeshMenuTip", "Make an AnimBlueprint of this model's (<Model>_KawaiiPhysics beside it) with the KawaiiPhysics of a game compat file's \"kawaii\" entry (the one listing this model, else you pick one), to preview, tune and Export For Game again."),
			FSlateIcon(), FToolUIActionChoice(FToolMenuExecuteAction::CreateStatic(&FKawaiiPhysicsEdModule::ImportForPickedMesh)));
	}
	if (UToolMenu* Menu = UToolMenus::Get()->ExtendMenu(TEXT("ContentBrowser.AssetContextMenu.AnimBlueprint")))
	{
		FToolMenuSection& Section = Menu->AddSection(TEXT("KawaiiPhysics"), LOCTEXT("KawaiiSection", "KawaiiPhysics"));
		Section.AddMenuEntry(TEXT("KawaiiPhysicsImportIntoAnimBlueprint"), LOCTEXT("ImportIntoMenu", "Import KawaiiPhysics From Game..."),
			LOCTEXT("ImportIntoMenuTip", "Put a game compat file's \"kawaii\" entry into this AnimBlueprint in place of its KawaiiPhysics nodes (before its Output Pose when it has none)."),
			FSlateIcon(), FToolUIActionChoice(FToolMenuExecuteAction::CreateStatic(&FKawaiiPhysicsEdModule::ImportIntoPickedAnimBlueprint)));
	}
	// every entry of a file at once, each into an AnimBlueprint of its model's
	if (UToolMenu* Menu = UToolMenus::Get()->ExtendMenu(TEXT("LevelEditor.MainMenu.Window")))
	{
		FToolMenuSection& Section = Menu->AddSection(TEXT("KawaiiPhysics"), LOCTEXT("KawaiiSection", "KawaiiPhysics"));
		Section.AddMenuEntry(TEXT("KawaiiPhysicsImportAllFromGame"), LOCTEXT("ImportAllMenu", "Import KawaiiPhysics From Game (every entry)..."),
			LOCTEXT("ImportAllMenuTip", "Pick a game compat file: each of its \"kawaii\" entries goes into an AnimBlueprint of its model's (<Model>_KawaiiPhysics beside the model, made or updated), its chains, shapes and settings as the game reads them, to preview, tune and Export For Game again."),
			FSlateIcon(), FUIAction(FExecuteAction::CreateStatic(&UKawaiiPhysicsGameImport::ImportAllWithDialogs)));
	}
}

void FKawaiiPhysicsEdModule::ImportForPickedMesh(const FToolMenuContext& Context)
{
	const UContentBrowserAssetContextMenuContext* Menu = Context.FindContext<UContentBrowserAssetContextMenuContext>();
	if (!Menu)
	{
		return;
	}
	for (UObject* Object : Menu->GetSelectedObjects())
	{
		if (USkeletalMesh* Mesh = Cast<USkeletalMesh>(Object))
		{
			UKawaiiPhysicsGameImport::ImportWithDialogs(nullptr, Mesh);
			return;
		}
	}
}

void FKawaiiPhysicsEdModule::ImportIntoPickedAnimBlueprint(const FToolMenuContext& Context)
{
	const UContentBrowserAssetContextMenuContext* Menu = Context.FindContext<UContentBrowserAssetContextMenuContext>();
	if (!Menu)
	{
		return;
	}
	for (UObject* Object : Menu->GetSelectedObjects())
	{
		if (UAnimBlueprint* Blueprint = Cast<UAnimBlueprint>(Object))
		{
			UKawaiiPhysicsGameImport::ImportWithDialogs(Blueprint, nullptr);
			return;
		}
	}
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FKawaiiPhysicsEdModule, KawaiiPhysicsEd)
