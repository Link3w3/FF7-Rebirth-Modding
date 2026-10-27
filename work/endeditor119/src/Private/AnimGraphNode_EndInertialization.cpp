#include "AnimGraphNode_EndInertialization.h"

#include "EndAnimGraphNodeUtils.h"

#define LOCTEXT_NAMESPACE "AnimGraphNode_EndInertialization"

FText UAnimGraphNode_EndInertialization::GetNodeTitle(ENodeTitleType::Type TitleType) const
{
	return LOCTEXT("NodeTitle", "End Inertialization");
}

FText UAnimGraphNode_EndInertialization::GetTooltipText() const
{
	return LOCTEXT("NodeTooltip", "The game's inertialization node (FAnimNode_EndInertialization): state machine transitions that use Inertialization blend here.");
}

FLinearColor UAnimGraphNode_EndInertialization::GetNodeTitleColor() const
{
	return FLinearColor(0.0f, 0.1f, 0.2f);
}

FString UAnimGraphNode_EndInertialization::GetNodeCategory() const
{
	return EndAnimGraphNodes::Category();
}

#undef LOCTEXT_NAMESPACE
