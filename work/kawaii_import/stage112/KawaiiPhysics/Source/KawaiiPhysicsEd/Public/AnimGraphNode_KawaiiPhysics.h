// Kawaii Dynamic Motions (1.9: KawaiiPhysics' new name, in text; the code keeps KawaiiPhysics' names): KawaiiPhysics'
// AnimGraph node (End editor, UE 4.26), with the newest KawaiiPhysics' features fused in and (1.9) its own motions (waves
// and a key animation of its bones, the physics on top); its preview runs
// Create a Character System's own simulation, so it moves the bones as FINAL FANTASY VII REBIRTH will. "Export For Game"
// writes the AnimBlueprint's KawaiiPhysics nodes as one of the game mod's "kawaii" entries (compat\*.json): the game runs
// them from that file. An AnimBlueprint with this node is for the editor only: the game has no KawaiiPhysics module, so
// it must not be cooked into a game pak.
// KawaiiPhysics is pafuhana1213's (https://github.com/pafuhana1213/KawaiiPhysics), MIT License.
#pragma once

#include "CoreMinimal.h"
#include "AnimGraphNode_SkeletalControlBase.h"
#include "AnimNode_KawaiiPhysics.h"
#include "EdGraph/EdGraphNodeUtils.h"

#include "AnimGraphNode_KawaiiPhysics.generated.h"

class FCompilerResultsLog;
class IDetailLayoutBuilder;

UCLASS()
class KAWAIIPHYSICSED_API UAnimGraphNode_KawaiiPhysics : public UAnimGraphNode_SkeletalControlBase
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, Category = Settings)
	FAnimNode_KawaiiPhysics Node;

	UPROPERTY(EditAnywhere, Category = Debug)
	bool bEnableDebugDrawBone = true;
	UPROPERTY(EditAnywhere, Category = Debug)
	bool bEnableDebugBoneLengthRate = true;
	UPROPERTY(EditAnywhere, Category = Debug)
	bool bEnableDebugDrawAngleLimit = true;
	UPROPERTY(EditAnywhere, Category = Debug)
	bool bEnableDebugDrawSphereLimit = true;
	UPROPERTY(EditAnywhere, Category = Debug)
	bool bEnableDebugDrawCapsuleLimit = true;
	UPROPERTY(EditAnywhere, Category = Debug)
	bool bEnableDebugDrawTaperedCapsuleLimit = true;
	UPROPERTY(EditAnywhere, Category = Debug)
	bool bEnableDebugDrawBoxLimit = true;
	UPROPERTY(EditAnywhere, Category = Debug)
	bool bEnableDebugDrawPlanerLimit = true;
	UPROPERTY(EditAnywhere, Category = Debug)
	bool bEnableDebugDrawBoneConstraint = true;
	/** (1.10) Each sync bone (a white diamond) and lines to its target roots */
	UPROPERTY(EditAnywhere, Category = Debug)
	bool bEnableDebugDrawSyncBone = true;

	// ---- Export For Game (the button is in this category): the entry's settings come from the node you click it on --
	/** The entry's name in the game's log (empty: the AnimBlueprint's) */
	UPROPERTY(EditAnywhere, Category = "Create a Character|Export For Game")
	FString ExportEntryName;

	/** The models it is for, object paths ("/Game/.../PC0010_13.PC0010_13"; one ending in * for every model under it).
	 *  Empty: the AnimBlueprint's preview mesh */
	UPROPERTY(EditAnywhere, Category = "Create a Character|Export For Game")
	TArray<FString> ExportModels;

	/** Paks (or mods) the models come in: the entry is off when one is not installed */
	UPROPERTY(EditAnywhere, Category = "Create a Character|Export For Game")
	TArray<FString> ExportRequiresPaks;

	/** Turn the model's Bonamik (its BNMs) off while it shows the model */
	UPROPERTY(EditAnywhere, Category = "Create a Character|Export For Game")
	bool bExportDisableBonamik = false;

	/** Only these BNMs (their names: "PC0010_13_BNM"); empty: all of the model's */
	UPROPERTY(EditAnywhere, Category = "Create a Character|Export For Game", meta = (EditCondition = "bExportDisableBonamik"))
	TArray<FString> ExportDisableBonamikAssets;

	/** (1.11) Take the model's KineDriver (its KDIs) off it as it loads (the game's "disable_kinedriver") */
	UPROPERTY(EditAnywhere, Category = "Create a Character|Export For Game")
	bool bExportDisableKineDriver = false;

	/** Only these KDIs ("PC0010_00_KDI_Extra1"); empty: all of the model's */
	UPROPERTY(EditAnywhere, Category = "Create a Character|Export For Game", meta = (EditCondition = "bExportDisableKineDriver"))
	TArray<FString> ExportDisableKineDriverAssets;

	/** (1.11) KawaiiPhysics' AnimNotifies for the game: by the montage the character plays and its time in it (the game's
	 *  "animation_triggers", Create a Character System 3.18.0; the editor's preview does not run them) */
	UPROPERTY(EditAnywhere, Category = "Create a Character|Export For Game", meta = (TitleProperty = "Type"))
	TArray<FKawaiiPhysicsAnimationTrigger> ExportAnimationTriggers;

	/** (1.11) The entry's shared winds (the game's "shared_winds") */
	UPROPERTY(EditAnywhere, Category = "Create a Character|Export For Game", meta = (TitleProperty = "SharedWindTag"))
	TArray<FKawaiiPhysicsSharedWind> ExportSharedWinds;

	/** (1.11) The entry's own wind source (the game's "world_wind") */
	UPROPERTY(EditAnywhere, Category = "Create a Character|Export For Game")
	FKawaiiPhysicsWorldWind ExportWorldWind;

public:
	// UEdGraphNode interface
	virtual FText GetNodeTitle(ENodeTitleType::Type TitleType) const override;
	virtual FText GetTooltipText() const override;
	virtual FText GetKeywords() const override;
	// UObject interface
	virtual void PostEditChangeProperty(struct FPropertyChangedEvent& PropertyChangedEvent) override;

	/** Writes every KawaiiPhysics node of this AnimBlueprint as one of the game's "kawaii" entries (Saved\KawaiiPhysics\
	 *  <AnimBlueprint>Kawaii.json, and the clipboard). False, with OutMessage saying why, when it could not. */
	bool ExportForGame(FString& OutPath, FString& OutMessage);

protected:
	// UAnimGraphNode_Base interface
	virtual FEditorModeID GetEditorMode() const override;
	virtual void ValidateAnimNodePostCompile(FCompilerResultsLog& MessageLog, UAnimBlueprintGeneratedClass* CompiledClass, int32 CompiledNodeIndex) override;
	virtual void CopyNodeDataToPreviewNode(FAnimNode_Base* InPreviewNode) override;
	virtual void CustomizeDetails(IDetailLayoutBuilder& DetailBuilder) override;
	virtual void Draw(FPrimitiveDrawInterface* PDI, USkeletalMeshComponent* PreviewSkelMeshComp) const override;
	// UAnimGraphNode_SkeletalControlBase interface
	virtual FText GetControllerDescription() const override;
	virtual const FAnimNode_SkeletalControlBase* GetNode() const override { return &Node; }

private:
	void ExportWithNotification();

	/** Constructing FText strings can be costly, so we cache the node's title */
	FNodeTitleTextTable CachedNodeTitles;
};
