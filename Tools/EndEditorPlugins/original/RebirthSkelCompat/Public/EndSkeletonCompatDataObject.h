// RebirthSkelCompat: KH3-style compatible skeletons for FINAL FANTASY VII REBIRTH mods.
#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "Engine/EngineTypes.h"
#include "UObject/SoftObjectPtr.h"
#include "EndSkeletonCompatDataObject.generated.h"

class USkeleton;
class USkeletalMesh;

/** One compatibility entry: meshes on ReceivingSkeleton are driven by the animations of AnimationSkeletons. */
USTRUCT(BlueprintType)
struct REBIRTHSKELCOMPATEDITOR_API FEndSkeletonCompatPair
{
	GENERATED_BODY()

	/** Turn this pair off without deleting it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Skeleton Compatibility")
	bool bEnabled = true;

	/** The skeleton your meshes use. In game those meshes are rebound to an animation skeleton while they load. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Skeleton Compatibility")
	TSoftObjectPtr<USkeleton> ReceivingSkeleton;

	/** Skeletons whose AnimBlueprints and animations drive those meshes, in priority order (the first one loaded wins). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Skeleton Compatibility")
	TArray<TSoftObjectPtr<USkeleton>> AnimationSkeletons;

	/** Optional: only these meshes are rebound. Empty = every mesh on the receiving skeleton. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Skeleton Compatibility")
	TArray<TSoftObjectPtr<USkeletalMesh>> ReceivingMeshes;

	/** When a mesh is rebound after it is already in use, re-initialise AnimBlueprints the game refused for it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, AdvancedDisplay, Category = "Skeleton Compatibility")
	bool bRepairLiveComponents = true;
};

/**
 * Skeleton compatibility data object: the KH3 "compatible skeletons" list for Rebirth.
 *
 * Editor only (never cooked). The list reaches the game through the RebirthSkelCompat UE4SS mod, either
 * stamped into the receiving skeleton's Asset User Data (Apply To Skeletons; it cooks with your pak) or as
 * JSON (Export Json; no cook needed).
 */
UCLASS(BlueprintType, meta = (DisplayName = "Skeleton Compatibility Data Object"))
class REBIRTHSKELCOMPATEDITOR_API UEndSkeletonCompatDataObject : public UDataAsset
{
	GENERATED_BODY()

public:
	UEndSkeletonCompatDataObject();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Skeleton Compatibility")
	TArray<FEndSkeletonCompatPair> Pairs;

	/** Apply To Skeletons also registers each pair with this editor's skeleton compatibility (RebirthMaterialPreview), for Persona previews. */
	UPROPERTY(EditAnywhere, Category = "Skeleton Compatibility", AdvancedDisplay)
	bool bRegisterForEditorPreview = true;

	/** Export Json writes <AssetName>.skelcompat.json here. Empty = <Project>/Saved/RebirthSkelCompat. Ship it next to your pak in ~mods. */
	UPROPERTY(EditAnywhere, Category = "Export")
	FDirectoryPath ExportDirectory;

	/** FINAL FANTASY VII REBIRTH install folder. If RebirthSkelCompat is installed there, Export Json also writes its compat\<AssetName>.json. */
	UPROPERTY(EditAnywhere, Category = "Export")
	FDirectoryPath GameDirectory;

	/** Result of the last button press. */
	UPROPERTY(VisibleAnywhere, Transient, Category = "Skeleton Compatibility", meta = (MultiLine = "true"))
	FString LastResult;

	/** Check every pair: the assets load, and each receiving mesh passes the game's bone-hierarchy test against each animation skeleton. */
	UFUNCTION(CallInEditor, Category = "Skeleton Compatibility")
	void Validate();

	/** Put the list on each receiving skeleton's Asset User Data (BP_SkelCompatUserData), then save. Cook and pak as usual. */
	UFUNCTION(CallInEditor, Category = "Skeleton Compatibility")
	void ApplyToSkeletons();

	/** Remove BP_SkelCompatUserData from each receiving skeleton, then save. */
	UFUNCTION(CallInEditor, Category = "Skeleton Compatibility")
	void RemoveFromSkeletons();

	/** Write the runtime JSON the RebirthSkelCompat mod reads (no cook needed). */
	UFUNCTION(CallInEditor, Category = "Skeleton Compatibility")
	void ExportJson();

	UFUNCTION(BlueprintCallable, Category = "Skeleton Compatibility")
	bool ValidatePairs(FString& OutReport) const;

	UFUNCTION(BlueprintCallable, Category = "Skeleton Compatibility")
	FString ToRuntimeJson() const;

	UFUNCTION(BlueprintCallable, Category = "Skeleton Compatibility")
	bool WriteRuntimeJson(FString& OutReport) const;

	UFUNCTION(BlueprintCallable, Category = "Skeleton Compatibility")
	bool ApplyPairsToSkeletons(bool bRemove, FString& OutReport);

	virtual bool IsEditorOnly() const override { return true; }

private:
	void ShowResult(const FString& Title, const FString& Report, bool bOk);
};
