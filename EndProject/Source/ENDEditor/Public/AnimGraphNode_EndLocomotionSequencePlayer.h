#pragma once

#include "CoreMinimal.h"
#include "AnimGraphNode_AssetPlayerBase.h"
#include "AnimNode_EndLocomotionSequencePlayer.h"
#include "AnimGraphNode_EndLocomotionSequencePlayer.generated.h"

/**
 * The game's locomotion sequence player (FAnimNode_EndLocomotionSequencePlayer). In the game it plays the animation its
 * Locomotion State has in the character's animation set, so its Sequence is usually left empty. An asset player: the
 * state machine's "time remaining" rules use the one in each state.
 */
UCLASS()
class ENDEDITOR_API UAnimGraphNode_EndLocomotionSequencePlayer : public UAnimGraphNode_AssetPlayerBase
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, Category = Settings)
	FAnimNode_EndLocomotionSequencePlayer Node;

	//~ Begin UEdGraphNode Interface
	virtual FText GetNodeTitle(ENodeTitleType::Type TitleType) const override;
	virtual FText GetTooltipText() const override;
	virtual FLinearColor GetNodeTitleColor() const override;
	//~ End UEdGraphNode Interface

	//~ Begin UAnimGraphNode_Base Interface
	virtual FString GetNodeCategory() const override;
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
