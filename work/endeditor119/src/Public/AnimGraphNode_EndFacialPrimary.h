#pragma once

#include "CoreMinimal.h"
#include "AnimGraphNode_Base.h"
#include "AnimNode_EndFacialPrimary.h"
#include "AnimGraphNode_EndFacialPrimary.generated.h"

/** The game's facial slot node (FAnimNode_EndFacialPrimary, a montage slot: FacialSlot in the game's characters). */
UCLASS()
class ENDEDITOR_API UAnimGraphNode_EndFacialPrimary : public UAnimGraphNode_Base
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, Category = Settings)
	FAnimNode_EndFacialPrimary Node;

	//~ Begin UEdGraphNode Interface
	virtual FText GetNodeTitle(ENodeTitleType::Type TitleType) const override;
	virtual FText GetTooltipText() const override;
	virtual FLinearColor GetNodeTitleColor() const override;
	//~ End UEdGraphNode Interface

	//~ Begin UAnimGraphNode_Base Interface
	virtual FString GetNodeCategory() const override;
	virtual void BakeDataDuringCompilation(class FCompilerResultsLog& MessageLog) override;
	//~ End UAnimGraphNode_Base Interface
};
