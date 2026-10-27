#include "AnimGraphNode_EndBehaviorAction.h"

#include "EndAnimGraphNodeUtils.h"

#define LOCTEXT_NAMESPACE "AnimGraphNode_EndBehaviorAction"

FText UAnimGraphNode_EndBehaviorAction::GetNodeTitle(ENodeTitleType::Type TitleType) const
{
	return LOCTEXT("NodeTitle", "End Behavior Action");
}

FText UAnimGraphNode_EndBehaviorAction::GetTooltipText() const
{
	return LOCTEXT("NodeTooltip", "The game's behavior action node (FAnimNode_EndBehaviorAction): plays the character's behavior actions over the input pose.");
}

FLinearColor UAnimGraphNode_EndBehaviorAction::GetNodeTitleColor() const
{
	return FLinearColor(0.55f, 0.15f, 0.65f);
}

FString UAnimGraphNode_EndBehaviorAction::GetNodeCategory() const
{
	return EndAnimGraphNodes::Category();
}

#undef LOCTEXT_NAMESPACE
