#include "AnimGraphNode_EndFacialSecondary.h"

#include "EndAnimGraphNodeUtils.h"

#define LOCTEXT_NAMESPACE "AnimGraphNode_EndFacialSecondary"

FText UAnimGraphNode_EndFacialSecondary::GetNodeTitle(ENodeTitleType::Type TitleType) const
{
	return LOCTEXT("NodeTitle", "End Facial Secondary (Lip Sync)");
}

FText UAnimGraphNode_EndFacialSecondary::GetTooltipText() const
{
	return LOCTEXT("NodeTooltip", "The game's lip sync node (FAnimNode_EndFacialSecondary): the character's lip sync shapes over the input pose.");
}

FLinearColor UAnimGraphNode_EndFacialSecondary::GetNodeTitleColor() const
{
	return FLinearColor(0.75f, 0.35f, 0.45f);
}

FString UAnimGraphNode_EndFacialSecondary::GetNodeCategory() const
{
	return EndAnimGraphNodes::Category();
}

#undef LOCTEXT_NAMESPACE
