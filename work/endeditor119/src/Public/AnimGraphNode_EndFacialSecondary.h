#pragma once

#include "CoreMinimal.h"
#include "AnimGraphNode_Base.h"
#include "AnimNode_EndFacialSecondary.h"
#include "AnimGraphNode_EndFacialSecondary.generated.h"

/** The game's lip sync node (FAnimNode_EndFacialSecondary, an HSF lip sync node over its input pose). */
UCLASS()
class ENDEDITOR_API UAnimGraphNode_EndFacialSecondary : public UAnimGraphNode_Base
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, Category = Settings)
	FAnimNode_EndFacialSecondary Node;

	//~ Begin UEdGraphNode Interface
	virtual FText GetNodeTitle(ENodeTitleType::Type TitleType) const override;
	virtual FText GetTooltipText() const override;
	virtual FLinearColor GetNodeTitleColor() const override;
	//~ End UEdGraphNode Interface

	//~ Begin UAnimGraphNode_Base Interface
	virtual FString GetNodeCategory() const override;
	//~ End UAnimGraphNode_Base Interface
};
