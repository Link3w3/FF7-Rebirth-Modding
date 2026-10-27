#pragma once

#include "CoreMinimal.h"
#include "AnimGraphNode_AssetPlayerBase.h"
#include "AnimNode_EndLocomotionBlendSpacePlayer.h"
#include "AnimGraphNode_EndLocomotionBlendSpacePlayer.generated.h"

/**
 * The game's locomotion blend space player (FAnimNode_EndLocomotionBlendSpacePlayer). In the game it plays the blend
 * space its Locomotion State has in the character's animation set (its Blend Space is usually left empty) at X and Y,
 * which the game's player AnimBlueprints take from Blend Input Direction and Blend Input Speed. An asset player.
 */
UCLASS()
class ENDEDITOR_API UAnimGraphNode_EndLocomotionBlendSpacePlayer : public UAnimGraphNode_AssetPlayerBase
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, Category = Settings)
	FAnimNode_EndLocomotionBlendSpacePlayer Node;

	//~ Begin UEdGraphNode Interface
	virtual FText GetNodeTitle(ENodeTitleType::Type TitleType) const override;
	virtual FText GetTooltipText() const override;
	virtual FLinearColor GetNodeTitleColor() const override;
	//~ End UEdGraphNode Interface

	//~ Begin UAnimGraphNode_Base Interface
	virtual FString GetNodeCategory() const override;
	virtual void CustomizePinData(UEdGraphPin* Pin, FName SourcePropertyName, int32 ArrayIndex) const override;
	virtual void BakeDataDuringCompilation(class FCompilerResultsLog& MessageLog) override;
	virtual bool DoesSupportTimeForTransitionGetter() const override;
	virtual UAnimationAsset* GetAnimationAsset() const override;
	virtual const TCHAR* GetTimePropertyName() const override;
	virtual UScriptStruct* GetTimePropertyStruct() const override;
	virtual void GetAllAnimationSequencesReferred(TArray<UAnimationAsset*>& AnimationAssets) const override;
	virtual void ReplaceReferredAnimations(const TMap<UAnimationAsset*, UAnimationAsset*>& AnimAssetReplacementMap) override;
	//~ End UAnimGraphNode_Base Interface

	//~ Begin UAnimGraphNode_AssetPlayerBase Interface (AnimGraph does not export these two, so this class has its own)
	virtual void OnProcessDuringCompilation(IAnimBlueprintCompilationContext& InCompilationContext, IAnimBlueprintGeneratedClassCompiledData& OutCompiledData) override;
	virtual void SetAnimationAsset(UAnimationAsset* Asset) override;
	//~ End UAnimGraphNode_AssetPlayerBase Interface
};
