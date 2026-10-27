#include "AnimGraphNode_EndCharacterMovementExpression.h"

#include "EndAnimGraphNodeUtils.h"

#define LOCTEXT_NAMESPACE "AnimGraphNode_EndCharacterMovementExpression"

FText UAnimGraphNode_EndCharacterMovementExpression::GetControllerDescription() const
{
	return LOCTEXT("ControllerDescription", "The game's character movement expression (FAnimNode_EndCharacterMovementExpression): the body's lean and sway from the character's movement.");
}

FText UAnimGraphNode_EndCharacterMovementExpression::GetNodeTitle(ENodeTitleType::Type TitleType) const
{
	return LOCTEXT("NodeTitle", "End Character Movement Expression");
}

FLinearColor UAnimGraphNode_EndCharacterMovementExpression::GetNodeTitleColor() const
{
	return FLinearColor(0.75f, 0.75f, 0.10f);
}

FString UAnimGraphNode_EndCharacterMovementExpression::GetNodeCategory() const
{
	return EndAnimGraphNodes::Category();
}

#undef LOCTEXT_NAMESPACE
