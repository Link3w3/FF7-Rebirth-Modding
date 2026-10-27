// RebirthSkelCompat AnimBlueprint Maker (editor 1.18): a character's AnimBlueprint for the game, made from one of the
// game's own (Cloud's player AnimBlueprint by default) for the character's skeleton, in a window of its own (Window >
// Rebirth AnimBlueprint Maker, or right-click a Skeleton or Skeletal Mesh > Make a Rebirth AnimBlueprint...). The making
// is Tools\RebirthSkelCompat\abp\make_cacs_abp.py's (the template's cooked package under the new name, its skeleton the
// character's, written as a ~mods container).
// (editor 1.19) Make Editable AnimBlueprint builds the template as an AnimBlueprint of this editor instead (its graphs,
// states and rules as nodes: EndAnimBlueprintTemplate.h), and Cook For Game writes that one as the ~mods container.
#pragma once

#include "CoreMinimal.h"
#include "Engine/EngineTypes.h"
#include "UObject/Object.h"
#include "UObject/SoftObjectPtr.h"
#include "EndAnimBlueprintMaker.generated.h"

class SDockTab;
class FSpawnTabArgs;
class USkeleton;

namespace RebirthSkelCompatEditor
{
/** The AnimBlueprint Maker's tab (Window > Rebirth AnimBlueprint Maker). */
extern const FName AnimBlueprintMakerTabName;

TSharedRef<SDockTab> SpawnAnimBlueprintMakerTab(const FSpawnTabArgs& Args);

/** Opens the AnimBlueprint Maker (or brings it to the front), for Skeleton when one is given. */
void OpenAnimBlueprintMakerTab(USkeleton* Skeleton);
}

/**
 * The AnimBlueprint Maker's form, shown in its details panel: the character's skeleton, the AnimBlueprint's name and the
 * game's AnimBlueprint it is made from. Make AnimBlueprint writes it as a ~mods container (and installs it).
 */
UCLASS(Transient)
class UEndAnimBlueprintMaker : public UObject
{
	GENERATED_BODY()

public:
	/** The character's skeleton (of this project, cooked into the character's mod: the game needs it at this path). */
	UPROPERTY(EditAnywhere, Category = "AnimBlueprint")
	TSoftObjectPtr<USkeleton> Skeleton;

	/** The AnimBlueprint's name (letters, digits and _). Empty: the skeleton's character folder + _Animation, as the game names them (PC0099_00_Hero_Animation for /Game/Character/Player/PC0099_00_Hero/Model/PC0099_00_Skeleton). */
	UPROPERTY(EditAnywhere, Category = "AnimBlueprint")
	FString Name;

	/** The folder it goes in, in the game. */
	UPROPERTY(EditAnywhere, Category = "AnimBlueprint")
	FString Folder = TEXT("/Game/BluePrint/Animation/Player");

	/** Which of the game's AnimBlueprints it is made from. Cloud's (a player: field and battle locomotion, the moves player, slots, facial, the movement and sword expressions) suits most characters; each party member's own (Barret, Tifa, Aerith, Yuffie, Zack, Cid; Red XIII and Cait Sith with their own locomotion) as the game made it for them; the bosses' and summons' (Leviathan's) suits monsters. More: Tools\RebirthSkelCompat\abp\templates\templates.json. */
	UPROPERTY(EditAnywhere, Category = "AnimBlueprint", meta = (GetOptions = "GetTemplateOptions"))
	FString Template;

	/** Keep the template's Control Rig node working (the game's common human rig: it places the hips and feet by the legs). Only for a character on a Rebirth human skeleton (the game's bone names); off, the node passes the pose through. */
	UPROPERTY(EditAnywhere, Category = "AnimBlueprint")
	bool bKeepControlRig = false;

	/** (Make Editable AnimBlueprint) An AnimBlueprint already at its path in this project is deleted first; off, the making stops there. */
	UPROPERTY(EditAnywhere, Category = "Editable AnimBlueprint")
	bool bReplaceExisting = false;

	/** (Make Editable AnimBlueprint) Open it in the AnimBlueprint editor once made. */
	UPROPERTY(EditAnywhere, Category = "Editable AnimBlueprint")
	bool bOpenWhenMade = true;

	/** The ~mods container's name. Empty: CACS_<Name>_P. */
	UPROPERTY(EditAnywhere, AdvancedDisplay, Category = "Container")
	FString Container;

	/** Make AnimBlueprint also copies the container into the game's ~mods (in the Mods Folder below). Close the game first. */
	UPROPERTY(EditAnywhere, Category = "Container")
	bool bInstall = true;

	/** The folder in ~mods it goes in (empty: ~mods itself). */
	UPROPERTY(EditAnywhere, Category = "Container", meta = (EditCondition = "bInstall"))
	FString ModsFolder = TEXT("CACS_AnimBlueprints");

	/** The FINAL FANTASY VII REBIRTH folder. */
	UPROPERTY(EditAnywhere, Category = "Container", meta = (EditCondition = "bInstall"))
	FDirectoryPath GameDirectory;

	/** The AnimBlueprint's class once made: a form's "anim_class", a skin's "anim_blueprint" (Copy Class Path copies it). */
	UPROPERTY(VisibleAnywhere, Transient, Category = "Result")
	FString AnimClass;

	/** What it makes and where it goes. */
	UPROPERTY(VisibleAnywhere, Transient, Category = "Result", meta = (MultiLine = "true"))
	FString About;

	UFUNCTION()
	TArray<FString> GetTemplateOptions() const;

	/** The template's key for the tool (cloud, sephiroth, vincent, monster) from Template. */
	FString TemplateKey() const;

	/** Name, else the default from the skeleton. */
	FString FinalName() const;

	/** The AnimBlueprint's package (Folder/Name). */
	FString PackagePath() const;

	/** The ~mods container's name (Container, else CACS_<Name>_P). */
	FString ContainerName() const;

	/** The skeleton's object path (package.object), empty when none is picked. */
	FString SkeletonPath() const;

	/** Fills About. */
	void Describe();

	/** The form for Skeleton (its Name cleared, so the default follows the skeleton). */
	void StartFrom(USkeleton* InSkeleton);
};
