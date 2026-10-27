// KawaiiPhysics' viewport mode in the AnimBlueprint editor (End editor, UE 4.26): the node's collision shapes (spheres,
// capsules, tapered capsules, boxes, planes; its own and its Limits Data Asset's) drawn, picked and moved, turned and sized
// with the widget. KawaiiPhysics is pafuhana1213's (https://github.com/pafuhana1213/KawaiiPhysics), MIT License.
#pragma once

#include "CoreMinimal.h"
#include "UnrealWidget.h"
#include "KawaiiPhysicsEditModeBase.h"
#include "AnimGraphNode_KawaiiPhysics.h"
#include "AnimNode_KawaiiPhysics.h"

class FEditorViewportClient;
class FPrimitiveDrawInterface;
class USkeletalMeshComponent;
struct FViewportClick;

class FKawaiiPhysicsEditMode : public FKawaiiPhysicsEditModeBase
{
public:
	FKawaiiPhysicsEditMode();

	/** IAnimNodeEditMode interface */
	virtual void EnterMode(class UAnimGraphNode_Base* InEditorNode, struct FAnimNode_Base* InRuntimeNode) override;
	virtual void ExitMode() override;
	virtual FVector GetWidgetLocation() const override;
	virtual FWidget::EWidgetMode GetWidgetMode() const override;
	virtual ECoordSystem GetWidgetCoordinateSystem() const override;
	virtual void DoTranslation(FVector& InTranslation) override;
	virtual void DoRotation(FRotator& InRotation) override;
	virtual void DoScale(FVector& InScale) override;

	/** FEdMode interface */
	virtual void Render(const FSceneView* View, FViewport* Viewport, FPrimitiveDrawInterface* PDI) override;
	virtual bool HandleClick(FEditorViewportClient* InViewportClient, HHitProxy* HitProxy, const FViewportClick& Click) override;
	virtual bool GetCustomDrawingCoordinateSystem(FMatrix& InMatrix, void* InData) override;
	virtual bool InputKey(FEditorViewportClient* InViewportClient, FViewport* InViewport, FKey InKey, EInputEvent InEvent) override;
	virtual bool ShouldDrawWidget() const override;
	virtual void DrawHUD(FEditorViewportClient* ViewportClient, FViewport* Viewport, const FSceneView* View, FCanvas* Canvas) override;

protected:
	void OnExternalNodePropertyChange(FPropertyChangedEvent& InPropertyEvent);
	FDelegateHandle NodePropertyDelegateHandle;

private:
	/** Render each kind of shape */
	void RenderSphericalLimits(FPrimitiveDrawInterface* PDI);
	void RenderCapsuleLimits(FPrimitiveDrawInterface* PDI);
	void RenderTaperedCapsuleLimits(FPrimitiveDrawInterface* PDI);
	void RenderBoxLimits(FPrimitiveDrawInterface* PDI);
	void RenderPlanarLimits(FPrimitiveDrawInterface* PDI);

	/** The preview mesh's transform (the shapes are kept in its space) */
	FTransform ComponentToWorld() const;

	// a valid widget mode for the gizmo
	FWidget::EWidgetMode FindValidWidgetMode(FWidget::EWidgetMode InWidgetMode) const;

	/** Checking if a collision is selected and the collision is valid */
	bool IsValidSelectCollision() const;

	FCollisionLimitBase* GetSelectCollisionLimitRuntime() const;
	FCollisionLimitBase* GetSelectCollisionLimitGraph() const;

	/** Draw text for DrawHUD */
	void DrawTextItem(FText Text, FCanvas* Canvas, float X, float& Y, float FontHeight);
	void Draw3DTextItem(FText Text, FCanvas* Canvas, const FSceneView* View, FViewport* Viewport, FVector Location);

private:
	/** Cache the typed nodes */
	struct FAnimNode_KawaiiPhysics* RuntimeNode;
	UAnimGraphNode_KawaiiPhysics* GraphNode;

	/** The current selection */
	ECollisionLimitType SelectCollisionType = ECollisionLimitType::None;
	int32 SelectCollisionIndex = -1;
	bool SelectCollisionIsFromDataAsset = false;

	// storing current widget mode
	mutable FWidget::EWidgetMode CurWidgetMode;
};
