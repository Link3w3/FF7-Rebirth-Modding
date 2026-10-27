// RebirthSkelCompat Parts Builder (editor 1.17): make a Customization part (another model on one of a character's bones,
// playing motions of its own: a wing, a tail, a halo), see it on the character playing its animations, and put it in the
// game's Customization catalog (customization\catalog.extra.json and catalog.json), its model and animations of this
// project built into the skins container.
#pragma once

#include "CoreMinimal.h"
#include "Engine/EngineTypes.h"
#include "UObject/Object.h"
#include "UObject/SoftObjectPtr.h"
#include "EndPartsBuilder.generated.h"

class SDockTab;
class FSpawnTabArgs;
class UAnimSequence;
class USkeletalMesh;
class UTexture;

namespace RebirthSkelCompatEditor
{
/** The Parts Builder's tab (Window > Rebirth Parts Builder). */
extern const FName PartsBuilderTabName;

TSharedRef<SDockTab> SpawnPartsBuilderTab(const FSpawnTabArgs& Args);

/** Opens the Parts Builder (or brings it to the front), making a part of Model when one is given. */
void OpenPartsBuilderTab(USkeletalMesh* Model);
}

/** A motion the part plays while the character uses one of its abilities. */
USTRUCT()
struct FEndPartMove
{
	GENERATED_BODY()

	/** The character's ability, as the battle names it (its ability ID), e.g. PC0010_10_Zanshin01. */
	UPROPERTY(EditAnywhere, Category = "Part")
	FString Ability;

	/** The part's motion while the character uses it: an Anim Sequence of the part's skeleton. */
	UPROPERTY(EditAnywhere, Category = "Part")
	TSoftObjectPtr<UAnimSequence> Motion;
};

/** (3.13.0) An effect kept on the part while it is worn (the game's EFFECTS page shows it as the part's own). */
USTRUCT()
struct FEndPartEffect
{
	GENERATED_BODY()

	/** A Niagara system (or a Cascade particle system) of the game's or of this project's (Build Part builds it in). */
	UPROPERTY(EditAnywhere, Category = "Part", meta = (AllowedClasses = "NiagaraSystem,ParticleSystem"))
	FSoftObjectPath Effect;

	/** A socket or bone of the part it goes on, e.g. R_FeatherD_b_Phy (empty, or one it does not have: its root). */
	UPROPERTY(EditAnywhere, Category = "Part")
	FString Socket;

	/** Its size (1: as made). */
	UPROPERTY(EditAnywhere, Category = "Part", meta = (ClampMin = "0.02", ClampMax = "50"))
	float Scale = 1.f;
};

/**
 * The Parts Builder's form, shown in its details panel: one part of the Customization screen's PARTS page (Create a
 * Character System 3.11): a model put on one of the character's bones, its own bone (Anchor) kept on it, playing its own
 * idle, or the motion of the name of the one the character plays (Sync, KH3-style), or a motion for an ability.
 */
UCLASS(Transient)
class UEndPartsBuilder : public UObject
{
	GENERATED_BODY()

public:
	/** Which part of the game's catalog this is: pick one to edit it (the form is filled from it), or (new part). */
	UPROPERTY(EditAnywhere, Category = "Part", meta = (GetOptions = "GetPartOptions"))
	FString Part;

	/** The part's name on the PARTS page, e.g. Sephiroth's wing. */
	UPROPERTY(EditAnywhere, Category = "Part")
	FString Name;

	/** Its id in the catalog (what the game saves a character's choice by): letters, digits and _. Empty: the Name's, in lower case (sephiroth_s_wing). */
	UPROPERTY(EditAnywhere, AdvancedDisplay, Category = "Part")
	FString Id;

	/** The part's model: a Skeletal Mesh (the game's, or one of this project: Build Part builds it into the game). */
	UPROPERTY(EditAnywhere, Category = "Part")
	TSoftObjectPtr<USkeletalMesh> Model;

	/** The models it is offered for, as patterns of their names or paths: PC0010_* is every model whose name starts with PC0010_ (Sephiroth's). Empty: every character. */
	UPROPERTY(EditAnywhere, Category = "Part")
	TArray<FString> For;

	/** Pick a pattern to add to For (from the preview character's model). */
	UPROPERTY(EditAnywhere, Category = "Part", meta = (GetOptions = "GetForOptions"))
	FString AddFor;

	/** The character's bone (or socket) the part goes on, e.g. C_Spine_d. Pick Bone lists the preview character's. */
	UPROPERTY(EditAnywhere, Category = "Placement")
	FString Bone;

	/** Pick a bone or socket of the preview character for Bone. */
	UPROPERTY(EditAnywhere, Category = "Placement", meta = (GetOptions = "GetBoneOptions"))
	FString PickBone;

	/** The part's own bone kept on the character's Bone while the part plays its motions (a wing's root on the back). Empty: Bone (a part of the character's own skeleton lines up bone for bone). A name the part does not have: the part's root, on Bone. */
	UPROPERTY(EditAnywhere, Category = "Placement")
	FString Anchor;

	/** Pick a bone of the part for Anchor. */
	UPROPERTY(EditAnywhere, Category = "Placement", meta = (GetOptions = "GetAnchorOptions"))
	FString PickAnchor;

	/** Moved this far from the bone, in the bone's own axes (cm). */
	UPROPERTY(EditAnywhere, Category = "Placement")
	FVector Offset = FVector::ZeroVector;

	/** Its size (1: as made). */
	UPROPERTY(EditAnywhere, Category = "Placement", meta = (ClampMin = "0.02", ClampMax = "50"))
	float Scale = 1.f;

	/** The part's material sections shown (their slot numbers, 0 first). Empty: all. A model of a whole character worn for one part of it (the winged Sephiroth's model for his wing: 10) shows only that part. */
	UPROPERTY(EditAnywhere, Category = "Placement")
	TArray<int32> Sections;

	/** The motion the part plays on its own (a loop): an Anim Sequence of the part's skeleton. */
	UPROPERTY(EditAnywhere, Category = "Animation")
	TSoftObjectPtr<UAnimSequence> Idle;

	/** KH3-style: the part plays its own motion of the name of the one the character plays (B_AtkTenshi01_1 while the character plays B_AtkTenshi01_1), at the same time, from Sync Folder. One it does not have: its idle. */
	UPROPERTY(EditAnywhere, Category = "Animation")
	bool bSync = false;

	/** Where the part's motions of the character's names are: a folder with the game's set folders in it (Battle00/B_Idle01_1 ...), e.g. /Game/Motion/Player/PC0010_Sephiroth_Transform. Empty: two folders above Idle's. */
	UPROPERTY(EditAnywhere, Category = "Animation", meta = (EditCondition = "bSync"))
	FString SyncFolder;

	/** Motions the part plays while the character uses an ability (in battle). */
	UPROPERTY(EditAnywhere, Category = "Animation")
	TArray<FEndPartMove> Moves;

	/** Tint the part's materials with Tint Color (a vector parameter of them). */
	UPROPERTY(EditAnywhere, Category = "Look")
	bool bTint = false;

	UPROPERTY(EditAnywhere, Category = "Look", meta = (EditCondition = "bTint"))
	FLinearColor TintColor = FLinearColor::White;

	/** The vector parameter Tint Color goes in. */
	UPROPERTY(EditAnywhere, AdvancedDisplay, Category = "Look", meta = (EditCondition = "bTint"))
	FString TintParameter = TEXT("Color");

	/** A texture put on the part's materials (Tint Texture Parameter), e.g. /Game/Renderer/Texture/FFFFFFFF_sRGB for a white wing. */
	UPROPERTY(EditAnywhere, Category = "Look")
	TSoftObjectPtr<UTexture> TintTexture;

	/** The texture parameter Tint Texture goes in, e.g. Color. */
	UPROPERTY(EditAnywhere, Category = "Look")
	FString TintTextureParameter;

	/** (3.13.0) Effects kept on the part while it is worn, e.g. the boss Sephiroth's feelers on a wing (FX_PC0010_10_SetFeeler_Wing_01 at R_FeatherD_b_Phy). Seen in the game (the preview here shows none). */
	UPROPERTY(EditAnywhere, Category = "Look")
	TArray<FEndPartEffect> Effects;

	/** The component class the game makes the part of (a skeletal mesh component's), e.g. /Script/EndGame.EndSkeletalMeshComponent. Empty: the game's EndSkeletalMeshComponent. */
	UPROPERTY(EditAnywhere, AdvancedDisplay, Category = "Look")
	FString ComponentClass;

	/** The character the preview shows the part on (a model of the character it is for). */
	UPROPERTY(EditAnywhere, Category = "Preview")
	TSoftObjectPtr<USkeletalMesh> PreviewCharacter;

	/** What the preview character plays (an Anim Sequence of its skeleton): with Sync, the part plays its own motion of that name. Empty: its pose at rest. */
	UPROPERTY(EditAnywhere, Category = "Preview")
	TSoftObjectPtr<UAnimSequence> PreviewAnimation;

	/** The part plays this one of its Moves in the preview (as in battle while the character uses that ability). Empty: its idle (or, with Sync, its motion of the preview animation's name). */
	UPROPERTY(EditAnywhere, Category = "Preview", meta = (GetOptions = "GetPreviewMoveOptions"))
	FString PreviewMove;

	/** How fast the preview plays (1: as in game). */
	UPROPERTY(EditAnywhere, Category = "Preview", meta = (ClampMin = "0", ClampMax = "4"))
	float PreviewSpeed = 1.f;

	/** The FINAL FANTASY VII REBIRTH folder whose Customization catalog the part goes in. */
	UPROPERTY(EditAnywhere, Category = "Install")
	FDirectoryPath GameDirectory;

	/** Build Part's folder for the part's assets of this project (skins\<Folder> in the game, in the skins container with the skins). Empty: Part_<Id>. */
	UPROPERTY(EditAnywhere, AdvancedDisplay, Category = "Install")
	FString AssetsFolder;

	/** What the part is and what the preview shows. */
	UPROPERTY(VisibleAnywhere, Transient, Category = "About", meta = (MultiLine = "true"))
	FString About;

	UFUNCTION()
	TArray<FString> GetPartOptions() const;

	UFUNCTION()
	TArray<FString> GetForOptions() const;

	UFUNCTION()
	TArray<FString> GetBoneOptions() const;

	UFUNCTION()
	TArray<FString> GetAnchorOptions() const;

	UFUNCTION()
	TArray<FString> GetPreviewMoveOptions() const;

	/** The part's id: Id, else from the Name. */
	FString PartId() const;

	/** Anchor, else Bone. */
	FString AnchorName() const;

	/** The folder of the part's motions for Sync: Sync Folder, else two folders above Idle's (empty: none). */
	FString SyncRoot() const;

	/** The part's assets folder: Assets Folder, else Part_<Id>. */
	FString AssetsFolderName() const;

	/** Moves the pickers' choices into their fields. True: something changed. */
	bool TakePickers();

	/** A new part of Model. */
	void StartFrom(USkeletalMesh* InModel);

	/** Fills About. */
	void Describe();

	/** "(new part)". */
	static const TCHAR* NewPartLabel();
};
