#include "AnimGraphNode_EndLocomotionBlendSpacePlayer.h"

#include "Animation/AnimBlueprint.h"
#include "Animation/BlendSpaceBase.h"
#include "EdGraph/EdGraphPin.h"
#include "EndAnimGraphNodeUtils.h"

#define LOCTEXT_NAMESPACE "AnimGraphNode_EndLocomotionBlendSpacePlayer"

FText UAnimGraphNode_EndLocomotionBlendSpacePlayer::GetNodeTitle(ENodeTitleType::Type TitleType) const
{
	const FText State = EndAnimGraphNodes::EnumValueText(StaticEnum<EEndLocomotionState>(), static_cast<int64>(Node.LocomotionState));
	if (TitleType == ENodeTitleType::ListView || TitleType == ENodeTitleType::MenuTitle)
	{
		return LOCTEXT("ListTitle", "End Locomotion Blend Space Player");
	}
	if (UAnimationAsset* Asset = GetAnimationAsset())
	{
		return FText::Format(LOCTEXT("NodeTitleAsset", "End Locomotion Blend Space\n{0} ({1})"), State, FText::FromString(Asset->GetName()));
	}
	return FText::Format(LOCTEXT("NodeTitle", "End Locomotion Blend Space\n{0}"), State);
}

FText UAnimGraphNode_EndLocomotionBlendSpacePlayer::GetTooltipText() const
{
	return LOCTEXT("NodeTooltip", "The game's locomotion blend space player (FAnimNode_EndLocomotionBlendSpacePlayer): plays the blend space its Locomotion State has in the character's animation set, at X and Y.");
}

FLinearColor UAnimGraphNode_EndLocomotionBlendSpacePlayer::GetNodeTitleColor() const
{
	return FLinearColor(0.2f, 0.8f, 0.2f);
}

FString UAnimGraphNode_EndLocomotionBlendSpacePlayer::GetNodeCategory() const
{
	return EndAnimGraphNodes::Category();
}

void UAnimGraphNode_EndLocomotionBlendSpacePlayer::CustomizePinData(UEdGraphPin* Pin, FName SourcePropertyName, int32 ArrayIndex) const
{
	Super::CustomizePinData(Pin, SourcePropertyName, ArrayIndex);
	// with a blend space set, X/Y/Z are named after its parameters (as the engine's Blend Space Player)
	UBlendSpaceBase* BlendSpace = Cast<UBlendSpaceBase>(GetAnimationAsset());
	if (!Pin || !BlendSpace)
	{
		return;
	}
	if (SourcePropertyName == TEXT("X"))
	{
		Pin->PinFriendlyName = FText::FromString(BlendSpace->GetBlendParameter(0).DisplayName);
	}
	else if (SourcePropertyName == TEXT("Y"))
	{
		Pin->PinFriendlyName = FText::FromString(BlendSpace->GetBlendParameter(1).DisplayName);
	}
	else if (SourcePropertyName == TEXT("Z"))
	{
		Pin->PinFriendlyName = FText::FromString(BlendSpace->GetBlendParameter(2).DisplayName);
	}
}

void UAnimGraphNode_EndLocomotionBlendSpacePlayer::BakeDataDuringCompilation(FCompilerResultsLog& MessageLog)
{
	// as the engine's Blend Space Player: the node's sync group from its Sync Group setting
	UAnimBlueprint* AnimBlueprint = GetAnimBlueprint();
	AnimBlueprint->FindOrAddGroup(SyncGroup.GroupName);
	Node.GroupName = SyncGroup.GroupName;
	Node.GroupRole = SyncGroup.GroupRole;
	Node.GroupScope = SyncGroup.GroupScope;
}

bool UAnimGraphNode_EndLocomotionBlendSpacePlayer::DoesSupportTimeForTransitionGetter() const
{
	return true;
}

UAnimationAsset* UAnimGraphNode_EndLocomotionBlendSpacePlayer::GetAnimationAsset() const
{
	UBlendSpaceBase* BlendSpace = Node.BlendSpace;
	UEdGraphPin* BlendSpacePin = FindPin(GET_MEMBER_NAME_STRING_CHECKED(FAnimNode_BlendSpacePlayer, BlendSpace));
	if (BlendSpacePin && !BlendSpace)
	{
		BlendSpace = Cast<UBlendSpaceBase>(BlendSpacePin->DefaultObject);
	}
	return BlendSpace;
}

const TCHAR* UAnimGraphNode_EndLocomotionBlendSpacePlayer::GetTimePropertyName() const
{
	return TEXT("InternalTimeAccumulator");
}

UScriptStruct* UAnimGraphNode_EndLocomotionBlendSpacePlayer::GetTimePropertyStruct() const
{
	return FAnimNode_EndLocomotionBlendSpacePlayer::StaticStruct();
}

void UAnimGraphNode_EndLocomotionBlendSpacePlayer::GetAllAnimationSequencesReferred(TArray<UAnimationAsset*>& AnimationAssets) const
{
	if (Node.BlendSpace)
	{
		HandleAnimReferenceCollection(Node.BlendSpace, AnimationAssets);
	}
}

void UAnimGraphNode_EndLocomotionBlendSpacePlayer::ReplaceReferredAnimations(const TMap<UAnimationAsset*, UAnimationAsset*>& AnimAssetReplacementMap)
{
	HandleAnimReferenceReplacement(Node.BlendSpace, AnimAssetReplacementMap);
}

void UAnimGraphNode_EndLocomotionBlendSpacePlayer::OnProcessDuringCompilation(IAnimBlueprintCompilationContext& InCompilationContext, IAnimBlueprintGeneratedClassCompiledData& OutCompiledData)
{
	EndAnimGraphNodes::RecordAssetPlayerForLayerGraphs(this, OutCompiledData);
}

void UAnimGraphNode_EndLocomotionBlendSpacePlayer::SetAnimationAsset(UAnimationAsset* Asset)
{
	if (UBlendSpaceBase* BlendSpace = Cast<UBlendSpaceBase>(Asset))
	{
		Node.BlendSpace = BlendSpace;
	}
}

#undef LOCTEXT_NAMESPACE
