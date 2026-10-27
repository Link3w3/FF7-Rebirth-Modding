#pragma once

#include "CoreMinimal.h"
#include "AnimGraphNode_Base.h"
#include "AnimNode_EndBehaviorAction.h"
#include "AnimGraphNode_EndBehaviorAction.generated.h"

/** The game's behavior action node (FAnimNode_EndBehaviorAction): the character's actions over its input pose. */
UCLASS()
class ENDEDITOR_API UAnimGraphNode_EndBehaviorAction : public UAnimGraphNode_Base
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, Category = Settings)
	FAnimNode_EndBehaviorAction Node;

	//~ Begin UEdGraphNode Interface
	virtual FText GetNodeTitle(ENodeTitleType::Type TitleType) const override;
	virtual FText GetTooltipText() const override;
	virtual FLinearColor GetNodeTitleColor() const override;
	//~ End UEdGraphNode Interface

	//~ Begin UAnimGraphNode_Base Interface
	virtual FString GetNodeCategory() const override;
	//~ End UAnimGraphNode_Base Interface
};
