// RebirthSkelCompat Weapon Blueprint Maker (editor 1.20): a weapon Blueprint for the game, a real Blueprint of this
// project made from one of the game's weapon blueprints (a template: EndWeaponBlueprintTemplate.h) holding a model of
// this project, in a window of its own (Window > Rebirth Weapon Blueprint Maker, or right-click a Skeletal Mesh > Make a
// Rebirth Weapon Blueprint...). A skin's Weapon names its class; the skin build cooks it with its model.
#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "UObject/SoftObjectPtr.h"
#include "EndWeaponBlueprintMaker.generated.h"

class SDockTab;
class FSpawnTabArgs;
class USkeletalMesh;

namespace RebirthSkelCompatEditor
{
/** The Weapon Blueprint Maker's tab (Window > Rebirth Weapon Blueprint Maker). */
extern const FName WeaponBlueprintMakerTabName;

TSharedRef<SDockTab> SpawnWeaponBlueprintMakerTab(const FSpawnTabArgs& Args);

/** Opens the Weapon Blueprint Maker (or brings it to the front), on Mesh when one is given. */
void OpenWeaponBlueprintMakerTab(USkeletalMesh* Mesh);
}

/**
 * The Weapon Blueprint Maker's form, shown in its details panel: the weapon's model, the game's weapon blueprint it is
 * made from, its name and folder. Make Weapon Blueprint makes it, compiles and saves it.
 */
UCLASS(Transient)
class UEndWeaponBlueprintMaker : public UObject
{
	GENERATED_BODY()

public:
	/** The weapon's model (a skeletal mesh of this project: cooked with the Blueprint into the skin). */
	UPROPERTY(EditAnywhere, Category = "Weapon")
	TSoftObjectPtr<USkeletalMesh> Mesh;

	/** Which of the game's weapon blueprints it is made from: its parent class, class defaults, mesh component settings (collision, tick) and components of its own (a gun's cartridges) come with it. A player's weapon suits a weapon a player character holds (Cloud's Buster Sword for a sword in Cloud's place, Sephiroth's cut-scale Masamune for the playable Sephiroth's). Tools\RebirthSkelCompat\weapon\templates.json lists them. */
	UPROPERTY(EditAnywhere, Category = "Weapon", meta = (GetOptions = "GetTemplateOptions"))
	FString Template;

	/** The Blueprint's name (letters, digits and _). Empty: the template's own name, as the game names it (WE0000_00_Cloud_BusterSword): the game's blueprints keep their names. */
	UPROPERTY(EditAnywhere, Category = "Weapon")
	FString Name;

	/** The folder it goes in. Empty: /Game/BluePrint/Character/Weapon/<the model's weapon folder> (a folder of its own, so the game's blueprint of the same name stays the game's). */
	UPROPERTY(EditAnywhere, Category = "Weapon")
	FString Folder;

	/** A Blueprint already at its path in this project is deleted first; off, the making stops there. */
	UPROPERTY(EditAnywhere, Category = "Weapon")
	bool bReplaceExisting = false;

	/** Open it in the Blueprint editor once made. */
	UPROPERTY(EditAnywhere, Category = "Weapon")
	bool bOpenWhenMade = true;

	/** The Blueprint's class once made: a skin's Weapon (Copy Class Path copies it). */
	UPROPERTY(VisibleAnywhere, Transient, Category = "Result")
	FString WeaponClass;

	/** What it makes and where it goes. */
	UPROPERTY(VisibleAnywhere, Transient, Category = "Result", meta = (MultiLine = "true"))
	FString About;

	UFUNCTION()
	TArray<FString> GetTemplateOptions() const;

	/** The template's key (WE0000_00_Cloud_BusterSword) from Template (a label or a key); empty when there is none. */
	FString TemplateKey() const;

	/** Name, else the template's key. */
	FString FinalName() const;

	/** Folder, else the default from the model. */
	FString FinalFolder() const;

	/** The Blueprint's package (Folder/Name). */
	FString PackagePath() const;

	/** The model's object path, empty when none is picked. */
	FString MeshPath() const;

	/** Fills About. */
	void Describe();

	/** The form for Mesh (its Name and Folder cleared, so the defaults follow the model). */
	void StartFrom(USkeletalMesh* InMesh);
};
