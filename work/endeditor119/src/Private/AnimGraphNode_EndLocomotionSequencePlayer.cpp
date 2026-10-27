#include "AnimGraphNode_EndLocomotionSequencePlayer.h"

#include "Animation/AnimBlueprint.h"
#include "Animation/AnimSequenceBase.h"
#include "EdGraph/EdGraphPin.h"
#include "EndAnimGraphNodeUtils.h"

#define LOCTEXT_NAMESPACE "AnimGraphNode_EndLocomotionSequencePlayer"

FText UAnimGraphNode_EndLocomotionSequencePlayer::GetNodeTitle(ENodeTitleType::Type TitleType) const
{
	const FText State = EndAnimGraphNodes::EnumValueText(StaticEnum<EEndLocomotionState>(), static_cast<int64>(Node.LocomotionState));
	if (TitleType == ENodeTitleType::ListView || TitleType == ENodeTitleType::MenuTitle)
	{
		return LOCTEXT("ListTitle", "End Locomotion Sequence Player");
	}
	if (UAnimationAsset* Asset = GetAnimationAsset())
	{
		return FText::Format(LOCTEXT("NodeTitleAsset", "End Locomotion Sequence\n{0} ({1})"), State, FText::FromString(Asset->GetName()));
	}
	return FText::Format(LOCTEXT("NodeTitle", "End Locomotion Sequence\n{0}"), State);
}

FText UAnimGraphNode_EndLocomotionSequencePlayer::GetTooltipText() const
{
	return LOCTEXT("NodeTooltip", "The game's locomotion sequence player (FAnimNode_EndLocomotionSequencePlayer): plays the animation its Locomotion State has in the character's animation set.");
}

FLinearColor UAnimGraphNode_EndLocomotionSequencePlayer::GetNodeTitleColor() const
{
	return FLinearColor(0.10f, 0.20f, 0.65f);
}

FString UAnimGraphNode_EndLocomotionSequencePlayer::GetNodeCategory() const
{
	return EndAnimGraphNodes::Category();
}

void UAnimGraphNode_EndLocomotionSequencePlayer::BakeDataDuringCompilation(FCompilerResultsLog& MessageLog)
{
	// as the engine's Sequence Player: the node's sync group from its Sync Group setting
	UAnimBlueprint* AnimBlueprint = GetAnimBlueprint();
	AnimBlueprint->FindOrAddGroup(SyncGroup.GroupName);
	Node.GroupName = SyncGroup.GroupName;
	Node.GroupRole = SyncGroup.GroupRole;
	Node.GroupScope = SyncGroup.GroupScope;
}

bool UAnimGraphNode_EndLocomotionSequencePlayer::DoesSupportTimeForTransitionGetter() const
{
	return true;
}

UAnimationAsset* UAnimGraphNode_EndLocomotionSequencePlayer::GetAnimationAsset() const
{
	UAnimSequenceBase* Sequence = Node.Sequence;
	UEdGraphPin* SequencePin = FindPin(GET_MEMBER_NAME_STRING_CHECKED(FAnimNode_SequencePlayer, Sequence));
	if (SequencePin && !Sequence)
	{
		Sequence = Cast<UAnimSequenceBase>(SequencePin->DefaultObject);
	}
	return Sequence;
}

const TCHAR* UAnimGraphNode_EndLocomotionSequencePlayer::GetTimePropertyName() const
{
	return TEXT("InternalTimeAccumulator");
}

UScriptStruct* UAnimGraphNode_EndLocomotionSequencePlayer::GetTimePropertyStruct() const
{
	return FAnimNode_EndLocomotionSequencePlayer::StaticStruct();
}

void UAnimGraphNode_EndLocomotionSequencePlayer::GetAllAnimationSequencesReferred(TArray<UAnimationAsset*>& AnimationAssets) const
{
	if (Node.Sequence)
	{
		HandleAnimReferenceCollection(Node.Sequence, AnimationAssets);
	}
}

void UAnimGraphNode_EndLocomotionSequencePlayer::ReplaceReferredAnimations(const TMap<UAnimationAsset*, UAnimationAsset*>& AnimAssetReplacementMap)
{
	HandleAnimReferenceReplacement(Node.Sequence, AnimAssetReplacementMap);
}

void UAnimGraphNode_EndLocomotionSequencePlayer::OnProcessDuringCompilation(IAnimBlueprintCompilationContext& InCompilationContext, IAnimBlueprintGeneratedClassCompiledData& OutCompiledData)
{
	EndAnimGraphNodes::RecordAssetPlayerForLayerGraphs(this, OutCompiledData);
}

void UAnimGraphNode_EndLocomotionSequencePlayer::SetAnimationAsset(UAnimationAsset* Asset)
{
	if (UAnimSequenceBase* Sequence = Cast<UAnimSequenceBase>(Asset))
	{
		Node.Sequence = Sequence;
	}
}

#undef LOCTEXT_NAMESPACE
