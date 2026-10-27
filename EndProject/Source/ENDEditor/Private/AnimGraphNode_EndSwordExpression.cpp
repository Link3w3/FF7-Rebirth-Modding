#include "AnimGraphNode_EndSwordExpression.h"

#include "Animation/Skeleton.h"
#include "EndAnimGraphNodeUtils.h"
#include "Kismet2/CompilerResultsLog.h"

#define LOCTEXT_NAMESPACE "AnimGraphNode_EndSwordExpression"

FText UAnimGraphNode_EndSwordExpression::GetControllerDescription() const
{
	return LOCTEXT("ControllerDescription", "The game's sword expression (FAnimNode_EndSwordExpression): a sheathed weapon bone that swings with the character's movement and keeps clear of the contact bones.");
}

FText UAnimGraphNode_EndSwordExpression::GetNodeTitle(ENodeTitleType::Type TitleType) const
{
	if (Node.TargetBone.BoneName == NAME_None || TitleType == ENodeTitleType::ListView || TitleType == ENodeTitleType::MenuTitle)
	{
		return LOCTEXT("NodeTitle", "End Sword Expression");
	}
	return FText::Format(LOCTEXT("NodeTitleBone", "End Sword Expression\nBone: {0}"), FText::FromName(Node.TargetBone.BoneName));
}

FLinearColor UAnimGraphNode_EndSwordExpression::GetNodeTitleColor() const
{
	return FLinearColor(0.75f, 0.75f, 0.10f);
}

FString UAnimGraphNode_EndSwordExpression::GetNodeCategory() const
{
	return EndAnimGraphNodes::Category();
}

void UAnimGraphNode_EndSwordExpression::ValidateAnimNodeDuringCompilation(USkeleton* ForSkeleton, FCompilerResultsLog& MessageLog)
{
	Super::ValidateAnimNodeDuringCompilation(ForSkeleton, MessageLog);
	if (!ForSkeleton)
	{
		return;
	}
	// (a warning, not an error: the game skips a bone its skeleton does not have)
	const FReferenceSkeleton& Reference = ForSkeleton->GetReferenceSkeleton();
	if (Node.TargetBone.BoneName != NAME_None && Reference.FindBoneIndex(Node.TargetBone.BoneName) == INDEX_NONE)
	{
		MessageLog.Warning(*FText::Format(LOCTEXT("NoTargetBone", "@@ - the skeleton has no bone {0} (Target Bone)"), FText::FromName(Node.TargetBone.BoneName)).ToString(), this);
	}
	for (const FBoneReference& Bone : Node.ContactBones)
	{
		if (Bone.BoneName != NAME_None && Reference.FindBoneIndex(Bone.BoneName) == INDEX_NONE)
		{
			MessageLog.Warning(*FText::Format(LOCTEXT("NoContactBone", "@@ - the skeleton has no bone {0} (Contact Bones)"), FText::FromName(Bone.BoneName)).ToString(), this);
		}
	}
}

#undef LOCTEXT_NAMESPACE
