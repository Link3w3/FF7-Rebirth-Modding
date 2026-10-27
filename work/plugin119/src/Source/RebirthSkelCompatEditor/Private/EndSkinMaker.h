// RebirthSkelCompat Skin Maker (editor 1.17): make a character skin from a model, in a window of its own (Window > Rebirth
// Skin Maker, or right-click a Skeletal Mesh > Create a Character Skin...), kept in a data object's Skins and built
// there.
#pragma once

#include "CoreMinimal.h"
#include "Engine/EngineTypes.h"
#include "UObject/Object.h"
#include "UObject/SoftObjectPtr.h"
#include "EndSkeletonCompatDataObject.h"
#include "EndSkinMaker.generated.h"

class SDockTab;
class FSpawnTabArgs;
class USkeletalMesh;
class USkeleton;

namespace RebirthSkelCompatEditor
{
/** The Skin Maker's tab (Window > Rebirth Skin Maker). */
extern const FName SkinMakerTabName;

TSharedRef<SDockTab> SpawnSkinMakerTab(const FSpawnTabArgs& Args);

/** Opens the Skin Maker (or brings it to the front): on DataObject when one is given, making a skin of Model when one is given. */
void OpenSkinMakerTab(UEndSkeletonCompatDataObject* DataObject, USkeletalMesh* Model);

/** The data object the Skin Maker keeps new skins in when none is picked: /Game/RebirthSkelCompat/Skins/DO_Skins. */
extern const TCHAR* const DefaultSkinsDataObject;
}

/**
 * The Skin Maker's form, shown in its details panel: one skin (a model a character wears in game, on the Customization
 * screen's SKINS page), kept in a Skeleton Compatibility Data Object's Skins. Save Skin puts it there, Build Skin builds
 * it the way Build Skins does (cooked into the game's package format, installed into the game, the skins container made
 * anew).
 */
UCLASS(Transient)
class UEndSkinMaker : public UObject
{
	GENERATED_BODY()

public:
	/** The Skeleton Compatibility Data Object the skin is kept in (its Skins). Empty: Save Skin keeps it in /Game/RebirthSkelCompat/Skins/DO_Skins (made the first time). */
	UPROPERTY(EditAnywhere, Category = "Skin")
	UEndSkeletonCompatDataObject* DataObject = nullptr;

	/** Which of the data object's skins this is: pick one to edit it (the form is filled from it), or (new skin). Save Skin also finds the data object's skin of the same folder. */
	UPROPERTY(EditAnywhere, Category = "Skin", meta = (GetOptions = "GetSkinOptions"))
	FString Skin;

	/** The skin's name on the Customization screen's SKINS page, e.g. Remake Sephiroth. */
	UPROPERTY(EditAnywhere, Category = "Skin")
	FString Name;

	/** The model: a Skeletal Mesh of this project (an imported one, or the game's). Its skeleton and physics asset go into the skin with it (the game's stay the game's). Its materials have to be in the game, in Extra Assets or in a mod. */
	UPROPERTY(EditAnywhere, Category = "Skin")
	TSoftObjectPtr<USkeletalMesh> Model;

	/** Its folder in the game (skins\<Folder> in the Create a Character System folder): letters, digits, _ and -. Empty: the Name's letters and digits (Remake Sephiroth: RemakeSephiroth). */
	UPROPERTY(EditAnywhere, AdvancedDisplay, Category = "Skin")
	FString Folder;

	/** The CharaSpec rows whose character can wear it, e.g. PC0000_00_Cloud_Standard. For a character playing in another one's slot, that slot's rows (the Fully Playable Sephiroth plays in Cloud's: Cloud's rows). Add them with Add Character. */
	UPROPERTY(EditAnywhere, Category = "Characters")
	TArray<FString> Characters;

	/** Pick a character to add it to Characters: one CharaSpec row, or every row of a character (all of its outfits). */
	UPROPERTY(EditAnywhere, Category = "Characters", meta = (GetOptions = "GetCharacterOptions"))
	FString AddCharacter;

	/** Its characters wear it as soon as the game starts. Off: it is one of their choices on the Customization screen's SKINS page, worn once picked there. */
	UPROPERTY(EditAnywhere, Category = "Characters")
	bool bWornAtOnce = false;

	/** The skeleton family the model's skeleton joins, so it plays every animation of the character: the character's own skeleton, e.g. PC0010_00_Skeleton (Sephiroth's). Empty: the model is on the character's own skeleton. */
	UPROPERTY(EditAnywhere, Category = "Skeleton")
	TSoftObjectPtr<USkeleton> Family;

	/** The model keeps its own proportions while it plays the family's animations. */
	UPROPERTY(EditAnywhere, Category = "Skeleton")
	bool bKeepProportions = false;

	/** More bones that keep the model's own length with Keep Proportions, as patterns: R_Feather* is every bone starting with R_Feather. */
	UPROPERTY(EditAnywhere, AdvancedDisplay, Category = "Skeleton", meta = (EditCondition = "bKeepProportions"))
	TArray<FString> ProportionBones;

	/** The AnimBlueprint the model runs (an AnimBlueprint asset or its _C class). Empty: the character's own (a model of the same body). */
	UPROPERTY(EditAnywhere, AdvancedDisplay, Category = "Skeleton")
	FString AnimBlueprint;

	/** Its voice while it is worn: empty (the character's), own (the banks its animations name), or a voice bank such as /Game/Sound/Voice/{language}/Character/Player/VO_PC0010_00_Sephiroth. Pick Voice fills it. */
	UPROPERTY(EditAnywhere, Category = "Voice and Weapon")
	FString Voice;

	/** Pick a voice for Voice: the voices the game's Customization catalog lists (the game's and the mod's own). */
	UPROPERTY(EditAnywhere, Category = "Voice and Weapon", meta = (GetOptions = "GetVoiceOptions"))
	FString PickVoice;

	/** The weapon it fights with while it is worn: a weapon blueprint class, e.g. /Game/BluePrint/Character/Weapon/WE1021_10_SephirothIllusion_MasamuneCutScale.WE1021_10_SephirothIllusion_MasamuneCutScale_C. Empty: the character's own. Pick Weapon fills it. */
	UPROPERTY(EditAnywhere, Category = "Voice and Weapon")
	FString Weapon;

	/** Pick a weapon for Weapon: the weapons the game's Customization catalog lists. */
	UPROPERTY(EditAnywhere, Category = "Voice and Weapon", meta = (GetOptions = "GetWeaponOptions"))
	FString PickWeapon;

	/** Model parts worn with the model (a wing or a cape of its own), each on a socket or bone of the model. */
	UPROPERTY(EditAnywhere, Category = "Assets")
	TArray<FEndSkinMesh> Meshes;

	/** More assets of this project cooked into the skin: materials and textures the game and your mods do not have. */
	UPROPERTY(EditAnywhere, Category = "Assets")
	TArray<FSoftObjectPath> ExtraAssets;

	/** Who made it (the SKINS page shows it). */
	UPROPERTY(EditAnywhere, Category = "About")
	FString Author;

	/** A line or two about it (the SKINS page shows it). */
	UPROPERTY(EditAnywhere, Category = "About", meta = (MultiLine = "true"))
	FString Description;

	/** The FINAL FANTASY VII REBIRTH folder Build Skin installs into (the data object's Game Directory). */
	UPROPERTY(EditAnywhere, Category = "Install")
	FDirectoryPath GameDirectory;

	/** Build Skin also copies the skin into the game and makes the skins container anew (the data object's Install Skins). Close the game first. */
	UPROPERTY(EditAnywhere, Category = "Install")
	bool bInstall = true;

	/** What the skin is and where it goes. */
	UPROPERTY(VisibleAnywhere, Transient, Category = "About", meta = (MultiLine = "true"))
	FString About;

	UFUNCTION()
	TArray<FString> GetSkinOptions() const;

	UFUNCTION()
	TArray<FString> GetCharacterOptions() const;

	UFUNCTION()
	TArray<FString> GetVoiceOptions() const;

	UFUNCTION()
	TArray<FString> GetWeaponOptions() const;

	/** The data object's skin this form is (by Skin, else by folder); INDEX_NONE: a new one. */
	int32 SkinIndex() const;

	/** The skin's folder: Folder, else the Name's letters and digits. */
	FString FolderName() const;

	/** The form as a skin of the data object (Enabled), keeping what the data object's skin has besides (its Preview, its Enabled). */
	FEndCharacterSkin MakeSkin() const;

	/** A skin into the form. */
	void TakeSkin(const FEndCharacterSkin& From);

	/** A new skin of Model: its Name and Folder from the model's name, its Family guessed (the model's own skeleton when that is a character's). */
	void StartFrom(USkeletalMesh* InModel);

	/** Adds AddCharacter's rows to Characters (then clears it); fills Voice and Weapon from their pickers. True: something changed. */
	bool TakePickers();

	/** Fills About. */
	void Describe();

	/** The rows GetCharacterOptions offers (the CharaSpec table's playable characters' rows, and the data object's own), looked up once per data object. */
	const TArray<FString>& CharacterRows() const;

	/** "(new skin)". */
	static const TCHAR* NewSkinLabel();

private:
	// (GetCharacterOptions' rows: looked up again when the data object changes)
	mutable TArray<FString> Rows;
	mutable TWeakObjectPtr<UEndSkeletonCompatDataObject> RowsOf;
	mutable bool bRowsRead = false;
};
