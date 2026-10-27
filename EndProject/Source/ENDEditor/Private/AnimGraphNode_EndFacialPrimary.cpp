#include "AnimGraphNode_EndFacialPrimary.h"

#include "Animation/AnimBlueprint.h"
#include "Animation/Skeleton.h"
#include "EndAnimGraphNodeUtils.h"

#define LOCTEXT_NAMESPACE "AnimGraphNode_EndFacialPrimary"

FText UAnimGraphNode_EndFacialPrimary::GetNodeTitle(ENodeTitleType::Type TitleType) const
{
	if (Node.SlotName == NAME_None)
	{
		return LOCTEXT("NodeTitleNoSlot", "End Facial Primary (no slot name)");
	}
	return FText::Format(LOCTEXT("NodeTitle", "End Facial Primary\nSlot '{0}'"), FText::FromName(Node.SlotName));
}

FText UAnimGraphNode_EndFacialPrimary::GetTooltipText() const
{
	return LOCTEXT("NodeTooltip", "The game's facial slot node (FAnimNode_EndFacialPrimary): plays facial montages in its slot over the input pose.");
}

FLinearColor UAnimGraphNode_EndFacialPrimary::GetNodeTitleColor() const
{
	return FLinearColor(0.7f, 0.7f, 0.7f);
}

FString UAnimGraphNode_EndFacialPrimary::GetNodeCategory() const
{
	return EndAnimGraphNodes::Category();
}

void UAnimGraphNode_EndFacialPrimary::BakeDataDuringCompilation(FCompilerResultsLog& MessageLog)
{
	// as the engine's Slot node: the slot is registered with the target skeleton (not while cooking)
	UAnimBlueprint* AnimBlueprint = GetAnimBlueprint();
	if (!GIsCookerLoadingPackage && AnimBlueprint && AnimBlueprint->TargetSkeleton && Node.SlotName != NAME_None)
	{
		AnimBlueprint->TargetSkeleton->RegisterSlotNode(Node.SlotName);
	}
}

#undef LOCTEXT_NAMESPACE
