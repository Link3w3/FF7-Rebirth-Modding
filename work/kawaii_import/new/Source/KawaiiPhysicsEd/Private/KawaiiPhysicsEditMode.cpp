// KawaiiPhysics' viewport mode (End editor, UE 4.26): KawaiiPhysics 1.7.0's, with the tapered capsules and boxes of the
// newest KawaiiPhysics, the shapes drawn in the preview mesh's space, and the node's problem shown when it does not run.
// KawaiiPhysics is pafuhana1213's (https://github.com/pafuhana1213/KawaiiPhysics), MIT License.
#include "KawaiiPhysicsEditMode.h"
#include "SceneManagement.h"
#include "EngineUtils.h"
#include "IPersonaPreviewScene.h"
#include "Animation/DebugSkelMeshComponent.h"
#include "EditorModeManager.h"
#include "CanvasItem.h"
#include "CanvasTypes.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "AnimationRuntime.h"
#include "KawaiiPhysicsLimitsDataAsset.h"

#define LOCTEXT_NAMESPACE "KawaiiPhysicsEditMode"

struct HKawaiiPhysicsHitProxy : public HHitProxy
{
	DECLARE_HIT_PROXY()

	HKawaiiPhysicsHitProxy(ECollisionLimitType InType, int32 InIndex, bool InFromDataAsset = false)
		: HHitProxy(HPP_Wireframe)
		, CollisionType(InType)
		, CollisionIndex(InIndex)
		, bFromDataAsset(InFromDataAsset)
	{
	}

	virtual EMouseCursor::Type GetMouseCursor() override
	{
		return EMouseCursor::Crosshairs;
	}

	ECollisionLimitType CollisionType;
	int32 CollisionIndex;
	bool bFromDataAsset;
};
IMPLEMENT_HIT_PROXY(HKawaiiPhysicsHitProxy, HHitProxy);

namespace
{
const FMaterialRenderProxy* ShapeMaterial(bool bFromDataAsset)
{
	UMaterialInterface* Material = bFromDataAsset ? GEngine->ConstraintLimitMaterialZ : GEngine->ConstraintLimitMaterialPrismatic;
	return Material ? Material->GetRenderProxy() : nullptr;
}
} // namespace

FKawaiiPhysicsEditMode::FKawaiiPhysicsEditMode()
	: RuntimeNode(nullptr)
	, GraphNode(nullptr)
	, CurWidgetMode(FWidget::WM_Translate)
{
}

void FKawaiiPhysicsEditMode::EnterMode(UAnimGraphNode_Base* InEditorNode, FAnimNode_Base* InRuntimeNode)
{
	RuntimeNode = static_cast<FAnimNode_KawaiiPhysics*>(InRuntimeNode);
	GraphNode = CastChecked<UAnimGraphNode_KawaiiPhysics>(InEditorNode);

	GraphNode->Node.SphericalLimitsData = RuntimeNode->SphericalLimitsData;
	GraphNode->Node.CapsuleLimitsData = RuntimeNode->CapsuleLimitsData;
	GraphNode->Node.TaperedCapsuleLimitsData = RuntimeNode->TaperedCapsuleLimitsData;
	GraphNode->Node.BoxLimitsData = RuntimeNode->BoxLimitsData;
	GraphNode->Node.PlanarLimitsData = RuntimeNode->PlanarLimitsData;

	NodePropertyDelegateHandle = GraphNode->OnNodePropertyChanged().AddSP(this, &FKawaiiPhysicsEditMode::OnExternalNodePropertyChange);

	FKawaiiPhysicsEditModeBase::EnterMode(InEditorNode, InRuntimeNode);
}

void FKawaiiPhysicsEditMode::ExitMode()
{
	if (GraphNode)
	{
		GraphNode->OnNodePropertyChanged().Remove(NodePropertyDelegateHandle);
	}
	GraphNode = nullptr;
	RuntimeNode = nullptr;

	FKawaiiPhysicsEditModeBase::ExitMode();
}

FTransform FKawaiiPhysicsEditMode::ComponentToWorld() const
{
	const USkeletalMeshComponent* SkelComp = GetAnimPreviewScene().GetPreviewMeshComponent();
	return SkelComp ? SkelComp->GetComponentTransform() : FTransform::Identity;
}

void FKawaiiPhysicsEditMode::Render(const FSceneView* View, FViewport* Viewport, FPrimitiveDrawInterface* PDI)
{
	USkeletalMeshComponent* SkelMeshComp = GetAnimPreviewScene().GetPreviewMeshComponent();
	if (RuntimeNode && GraphNode && SkelMeshComp && SkelMeshComp->SkeletalMesh && SkelMeshComp->SkeletalMesh->Skeleton)
	{
		RenderSphericalLimits(PDI);
		RenderCapsuleLimits(PDI);
		RenderTaperedCapsuleLimits(PDI);
		RenderBoxLimits(PDI);
		RenderPlanarLimits(PDI);
		PDI->SetHitProxy(nullptr);

		if (IsValidSelectCollision())
		{
			FCollisionLimitBase* Collision = GetSelectCollisionLimitRuntime();
			if (Collision)
			{
				const FTransform ToWorld = ComponentToWorld();
				FTransform BoneTransform = FTransform::Identity;
				if (Collision->DrivingBone.BoneIndex >= 0 && RuntimeNode->ForwardedPose.GetPose().IsValid())
				{
					const FBoneContainer& Bones = RuntimeNode->ForwardedPose.GetPose().GetBoneContainer();
					if (Collision->DrivingBone.IsValidToEvaluate(Bones))
					{
						BoneTransform = RuntimeNode->ForwardedPose.GetComponentSpaceTransform(Collision->DrivingBone.GetCompactPoseIndex(Bones));
					}
				}
				const FVector BoneAt = ToWorld.TransformPosition(BoneTransform.GetLocation());
				PDI->DrawPoint(BoneAt, FLinearColor::White, 10.0f, SDPG_Foreground);
				DrawDashedLine(PDI, ToWorld.TransformPosition(Collision->Location), BoneAt, FLinearColor::White, 1.0f, SDPG_Foreground);
				DrawCoordinateSystem(PDI, BoneAt, (ToWorld.GetRotation() * Collision->Rotation).Rotator(), 20.0f, SDPG_World + 1);
			}
		}
	}
	FKawaiiPhysicsEditModeBase::Render(View, Viewport, PDI);
}

void FKawaiiPhysicsEditMode::RenderSphericalLimits(FPrimitiveDrawInterface* PDI)
{
	if (!GraphNode->bEnableDebugDrawSphereLimit) { return; }
	const FTransform ToWorld = ComponentToWorld();
	const float Scale = ToWorld.GetMaximumAxisScale();
	for (const bool bData : {false, true})
	{
		const TArray<FSphericalLimit>& List = bData ? RuntimeNode->SphericalLimitsData : RuntimeNode->SphericalLimits;
		for (int32 i = 0; i < List.Num(); i++)
		{
			const FSphericalLimit& Sphere = List[i];
			if (Sphere.Radius <= 0.0f) { continue; }
			const FVector At = ToWorld.TransformPosition(Sphere.Location);
			const FRotator Rotation = (ToWorld.GetRotation() * Sphere.Rotation).Rotator();
			PDI->SetHitProxy(new HKawaiiPhysicsHitProxy(ECollisionLimitType::Spherical, i, bData));
			if (const FMaterialRenderProxy* Material = ShapeMaterial(bData))
			{
				DrawSphere(PDI, At, FRotator::ZeroRotator, FVector(Sphere.Radius * Scale), 24, 6, Material, SDPG_World);
			}
			DrawWireSphere(PDI, At, FLinearColor::Black, Sphere.Radius * Scale, 24, SDPG_World);
			DrawCoordinateSystem(PDI, At, Rotation, Sphere.Radius * Scale, SDPG_World + 1);
		}
	}
}

void FKawaiiPhysicsEditMode::RenderCapsuleLimits(FPrimitiveDrawInterface* PDI)
{
	if (!GraphNode->bEnableDebugDrawCapsuleLimit) { return; }
	const FTransform ToWorld = ComponentToWorld();
	const float Scale = ToWorld.GetMaximumAxisScale();
	for (const bool bData : {false, true})
	{
		const TArray<FCapsuleLimit>& List = bData ? RuntimeNode->CapsuleLimitsData : RuntimeNode->CapsuleLimits;
		for (int32 i = 0; i < List.Num(); i++)
		{
			const FCapsuleLimit& Capsule = List[i];
			if (Capsule.Radius <= 0.0f || Capsule.Length <= 0.0f) { continue; }
			const FQuat Rotation = ToWorld.GetRotation() * Capsule.Rotation;
			const FVector At = ToWorld.TransformPosition(Capsule.Location);
			const FVector XAxis = Rotation.GetAxisX(), YAxis = Rotation.GetAxisY(), ZAxis = Rotation.GetAxisZ();
			const float Radius = Capsule.Radius * Scale, Half = 0.5f * Capsule.Length * Scale;
			PDI->SetHitProxy(new HKawaiiPhysicsHitProxy(ECollisionLimitType::Capsule, i, bData));
			if (const FMaterialRenderProxy* Material = ShapeMaterial(bData))
			{
				DrawCylinder(PDI, At, XAxis, YAxis, ZAxis, Radius, Half, 25, Material, SDPG_World);
				DrawSphere(PDI, At + ZAxis * Half, Rotation.Rotator(), FVector(Radius), 24, 6, Material, SDPG_World);
				DrawSphere(PDI, At - ZAxis * Half, Rotation.Rotator(), FVector(Radius), 24, 6, Material, SDPG_World);
			}
			DrawWireCapsule(PDI, At, XAxis, YAxis, ZAxis, FLinearColor::Black, Radius, Half + Radius, 25, SDPG_World);
			DrawCoordinateSystem(PDI, At, Rotation.Rotator(), Radius, SDPG_World + 1);
		}
	}
}

void FKawaiiPhysicsEditMode::RenderTaperedCapsuleLimits(FPrimitiveDrawInterface* PDI)
{
	if (!GraphNode->bEnableDebugDrawTaperedCapsuleLimit) { return; }
	const FTransform ToWorld = ComponentToWorld();
	const float Scale = ToWorld.GetMaximumAxisScale();
	for (const bool bData : {false, true})
	{
		const TArray<FTaperedCapsuleLimit>& List = bData ? RuntimeNode->TaperedCapsuleLimitsData : RuntimeNode->TaperedCapsuleLimits;
		for (int32 i = 0; i < List.Num(); i++)
		{
			const FTaperedCapsuleLimit& Capsule = List[i];
			if (Capsule.Radius0 <= 0.0f && Capsule.Radius1 <= 0.0f) { continue; }
			const FQuat Rotation = ToWorld.GetRotation() * Capsule.Rotation;
			const FVector At = ToWorld.TransformPosition(Capsule.Location);
			const FVector XAxis = Rotation.GetAxisX(), YAxis = Rotation.GetAxisY(), ZAxis = Rotation.GetAxisZ();
			const float Half = 0.5f * Capsule.Length * Scale;
			const float R0 = Capsule.Radius0 * Scale, R1 = Capsule.Radius1 * Scale;
			const FVector Top = At + ZAxis * Half, Bottom = At - ZAxis * Half;
			PDI->SetHitProxy(new HKawaiiPhysicsHitProxy(ECollisionLimitType::TaperedCapsule, i, bData));
			if (const FMaterialRenderProxy* Material = ShapeMaterial(bData))
			{
				if (R0 > 0.0f) { DrawSphere(PDI, Top, Rotation.Rotator(), FVector(R0), 24, 6, Material, SDPG_World); }
				if (R1 > 0.0f) { DrawSphere(PDI, Bottom, Rotation.Rotator(), FVector(R1), 24, 6, Material, SDPG_World); }
			}
			if (R0 > 0.0f) { DrawWireSphere(PDI, Top, FLinearColor::Black, R0, 24, SDPG_World); }
			if (R1 > 0.0f) { DrawWireSphere(PDI, Bottom, FLinearColor::Black, R1, 24, SDPG_World); }
			// (the cone between them: lines along its sides)
			for (int32 k = 0; k < 8; ++k)
			{
				const float Angle = 2.0f * PI * float(k) / 8.0f;
				const FVector Out = XAxis * FMath::Cos(Angle) + YAxis * FMath::Sin(Angle);
				PDI->DrawLine(Top + Out * R0, Bottom + Out * R1, FLinearColor::Black, SDPG_World);
			}
			DrawCoordinateSystem(PDI, At, Rotation.Rotator(), FMath::Max(R0, R1), SDPG_World + 1);
		}
	}
}

void FKawaiiPhysicsEditMode::RenderBoxLimits(FPrimitiveDrawInterface* PDI)
{
	if (!GraphNode->bEnableDebugDrawBoxLimit) { return; }
	const FTransform ToWorld = ComponentToWorld();
	for (const bool bData : {false, true})
	{
		const TArray<FBoxLimit>& List = bData ? RuntimeNode->BoxLimitsData : RuntimeNode->BoxLimits;
		for (int32 i = 0; i < List.Num(); i++)
		{
			const FBoxLimit& Box = List[i];
			if (Box.Extent.X <= 0.0f || Box.Extent.Y <= 0.0f || Box.Extent.Z <= 0.0f) { continue; }
			const FTransform Place = FTransform(Box.Rotation, Box.Location) * ToWorld;
			const FMatrix Matrix = Place.ToMatrixWithScale();
			PDI->SetHitProxy(new HKawaiiPhysicsHitProxy(ECollisionLimitType::Box, i, bData));
			if (const FMaterialRenderProxy* Material = ShapeMaterial(bData))
			{
				DrawBox(PDI, Matrix, Box.Extent, Material, SDPG_World);
			}
			DrawWireBox(PDI, Matrix, FBox(-Box.Extent, Box.Extent), FLinearColor::Black, SDPG_World);
			DrawCoordinateSystem(PDI, Place.GetLocation(), Place.Rotator(), Box.Extent.GetMax(), SDPG_World + 1);
		}
	}
}

void FKawaiiPhysicsEditMode::RenderPlanarLimits(FPrimitiveDrawInterface* PDI)
{
	if (!GraphNode->bEnableDebugDrawPlanerLimit) { return; }
	const FTransform ToWorld = ComponentToWorld();
	for (const bool bData : {false, true})
	{
		const TArray<FPlanarLimit>& List = bData ? RuntimeNode->PlanarLimitsData : RuntimeNode->PlanarLimits;
		for (int32 i = 0; i < List.Num(); i++)
		{
			const FPlanarLimit& Plane = List[i];
			FTransform PlaneTransform = FTransform(Plane.Rotation, Plane.Location) * ToWorld;
			PlaneTransform.NormalizeRotation();
			PDI->SetHitProxy(new HKawaiiPhysicsHitProxy(ECollisionLimitType::Planar, i, bData));
			if (const FMaterialRenderProxy* Material = ShapeMaterial(bData))
			{
				DrawPlane10x10(PDI, PlaneTransform.ToMatrixWithScale(), 200.0f, FVector2D(0.0f, 0.0f), FVector2D(1.0f, 1.0f), Material, SDPG_World);
			}
			DrawDirectionalArrow(PDI, FRotationMatrix(FRotator(90.0f, 0.0f, 0.0f)) * PlaneTransform.ToMatrixWithScale(), FLinearColor::Blue, 50.0f, 20.0f, SDPG_Foreground, 0.5f);
		}
	}
}

FVector FKawaiiPhysicsEditMode::GetWidgetLocation() const
{
	FCollisionLimitBase* Collision = GetSelectCollisionLimitRuntime();
	if (Collision)
	{
		return ComponentToWorld().TransformPosition(Collision->Location);
	}
	return ComponentToWorld().GetLocation();
}

bool FKawaiiPhysicsEditMode::GetCustomDrawingCoordinateSystem(FMatrix& InMatrix, void* InData)
{
	FCollisionLimitBase* Collision = GetSelectCollisionLimitRuntime();
	if (!Collision)
	{
		return false;
	}
	InMatrix = FTransform(ComponentToWorld().GetRotation() * Collision->Rotation).ToMatrixNoScale();
	return true;
}

FWidget::EWidgetMode FKawaiiPhysicsEditMode::GetWidgetMode() const
{
	if (GetSelectCollisionLimitRuntime())
	{
		CurWidgetMode = FindValidWidgetMode(CurWidgetMode);
		return CurWidgetMode;
	}
	return FWidget::WM_Translate;
}

FWidget::EWidgetMode FKawaiiPhysicsEditMode::FindValidWidgetMode(FWidget::EWidgetMode InWidgetMode) const
{
	if (InWidgetMode == FWidget::WM_None)
	{
		return FWidget::WM_Translate;
	}
	switch (InWidgetMode)
	{
	case FWidget::WM_Translate:
		return FWidget::WM_Rotate;
	case FWidget::WM_Rotate:
		return FWidget::WM_Scale;
	case FWidget::WM_Scale:
		return FWidget::WM_Translate;
	default:
		break;
	}
	return FWidget::WM_None;
}

bool FKawaiiPhysicsEditMode::HandleClick(FEditorViewportClient* InViewportClient, HHitProxy* HitProxy, const FViewportClick& Click)
{
	const bool bResult = FKawaiiPhysicsEditModeBase::HandleClick(InViewportClient, HitProxy, Click);

	if (HitProxy != nullptr && HitProxy->IsA(HKawaiiPhysicsHitProxy::StaticGetType()))
	{
		HKawaiiPhysicsHitProxy* KawaiiPhysicsHitProxy = static_cast<HKawaiiPhysicsHitProxy*>(HitProxy);
		SelectCollisionType = KawaiiPhysicsHitProxy->CollisionType;
		SelectCollisionIndex = KawaiiPhysicsHitProxy->CollisionIndex;
		SelectCollisionIsFromDataAsset = KawaiiPhysicsHitProxy->bFromDataAsset;
		return true;
	}

	SelectCollisionType = ECollisionLimitType::None;
	SelectCollisionIndex = -1;
	SelectCollisionIsFromDataAsset = false;
	return bResult;
}

bool FKawaiiPhysicsEditMode::InputKey(FEditorViewportClient* InViewportClient, FViewport* InViewport, FKey InKey, EInputEvent InEvent)
{
	bool bHandled = false;

	if ((InEvent == IE_Pressed) && !bManipulating)
	{
		if (InKey == EKeys::SpaceBar)
		{
			GetModeManager()->SetWidgetMode(GetWidgetMode());
			bHandled = true;
			InViewportClient->Invalidate();
		}
		else if (InKey == EKeys::Q)
		{
			const ECoordSystem CoordSystem = GetModeManager()->GetCoordSystem();
			GetModeManager()->SetCoordSystem(CoordSystem == COORD_Local ? COORD_World : COORD_Local);
		}
		else if (InKey == EKeys::Delete && IsValidSelectCollision() && !SelectCollisionIsFromDataAsset)
		{
			// (the node's own shapes; a Limits Data Asset's are edited in the asset)
			GraphNode->Modify();
			switch (SelectCollisionType)
			{
			case ECollisionLimitType::Spherical:
				RuntimeNode->SphericalLimits.RemoveAt(SelectCollisionIndex);
				GraphNode->Node.SphericalLimits.RemoveAt(SelectCollisionIndex);
				break;
			case ECollisionLimitType::Capsule:
				RuntimeNode->CapsuleLimits.RemoveAt(SelectCollisionIndex);
				GraphNode->Node.CapsuleLimits.RemoveAt(SelectCollisionIndex);
				break;
			case ECollisionLimitType::TaperedCapsule:
				RuntimeNode->TaperedCapsuleLimits.RemoveAt(SelectCollisionIndex);
				GraphNode->Node.TaperedCapsuleLimits.RemoveAt(SelectCollisionIndex);
				break;
			case ECollisionLimitType::Box:
				RuntimeNode->BoxLimits.RemoveAt(SelectCollisionIndex);
				GraphNode->Node.BoxLimits.RemoveAt(SelectCollisionIndex);
				break;
			case ECollisionLimitType::Planar:
				RuntimeNode->PlanarLimits.RemoveAt(SelectCollisionIndex);
				GraphNode->Node.PlanarLimits.RemoveAt(SelectCollisionIndex);
				break;
			default:
				break;
			}
			SelectCollisionType = ECollisionLimitType::None;
			SelectCollisionIndex = -1;
			bHandled = true;
		}
	}

	return bHandled;
}

ECoordSystem FKawaiiPhysicsEditMode::GetWidgetCoordinateSystem() const
{
	return COORD_Local;
}

void FKawaiiPhysicsEditMode::OnExternalNodePropertyChange(FPropertyChangedEvent& InPropertyEvent)
{
	if (!IsValidSelectCollision())
	{
		SelectCollisionIndex = -1;
		SelectCollisionType = ECollisionLimitType::None;
		CurWidgetMode = FWidget::WM_None;
	}
}

bool FKawaiiPhysicsEditMode::IsValidSelectCollision() const
{
	if (RuntimeNode == nullptr || GraphNode == nullptr || SelectCollisionIndex < 0 || SelectCollisionType == ECollisionLimitType::None)
	{
		return false;
	}
	const bool bData = SelectCollisionIsFromDataAsset;
	switch (SelectCollisionType)
	{
	case ECollisionLimitType::Spherical:
		return (bData ? RuntimeNode->SphericalLimitsData : RuntimeNode->SphericalLimits).IsValidIndex(SelectCollisionIndex) &&
			(bData ? GraphNode->Node.SphericalLimitsData : GraphNode->Node.SphericalLimits).IsValidIndex(SelectCollisionIndex);
	case ECollisionLimitType::Capsule:
		return (bData ? RuntimeNode->CapsuleLimitsData : RuntimeNode->CapsuleLimits).IsValidIndex(SelectCollisionIndex) &&
			(bData ? GraphNode->Node.CapsuleLimitsData : GraphNode->Node.CapsuleLimits).IsValidIndex(SelectCollisionIndex);
	case ECollisionLimitType::TaperedCapsule:
		return (bData ? RuntimeNode->TaperedCapsuleLimitsData : RuntimeNode->TaperedCapsuleLimits).IsValidIndex(SelectCollisionIndex) &&
			(bData ? GraphNode->Node.TaperedCapsuleLimitsData : GraphNode->Node.TaperedCapsuleLimits).IsValidIndex(SelectCollisionIndex);
	case ECollisionLimitType::Box:
		return (bData ? RuntimeNode->BoxLimitsData : RuntimeNode->BoxLimits).IsValidIndex(SelectCollisionIndex) &&
			(bData ? GraphNode->Node.BoxLimitsData : GraphNode->Node.BoxLimits).IsValidIndex(SelectCollisionIndex);
	case ECollisionLimitType::Planar:
		return (bData ? RuntimeNode->PlanarLimitsData : RuntimeNode->PlanarLimits).IsValidIndex(SelectCollisionIndex) &&
			(bData ? GraphNode->Node.PlanarLimitsData : GraphNode->Node.PlanarLimits).IsValidIndex(SelectCollisionIndex);
	default:
		break;
	}
	return false;
}

FCollisionLimitBase* FKawaiiPhysicsEditMode::GetSelectCollisionLimitRuntime() const
{
	if (!IsValidSelectCollision())
	{
		return nullptr;
	}
	const bool bData = SelectCollisionIsFromDataAsset;
	switch (SelectCollisionType)
	{
	case ECollisionLimitType::Spherical:
		return &(bData ? RuntimeNode->SphericalLimitsData : RuntimeNode->SphericalLimits)[SelectCollisionIndex];
	case ECollisionLimitType::Capsule:
		return &(bData ? RuntimeNode->CapsuleLimitsData : RuntimeNode->CapsuleLimits)[SelectCollisionIndex];
	case ECollisionLimitType::TaperedCapsule:
		return &(bData ? RuntimeNode->TaperedCapsuleLimitsData : RuntimeNode->TaperedCapsuleLimits)[SelectCollisionIndex];
	case ECollisionLimitType::Box:
		return &(bData ? RuntimeNode->BoxLimitsData : RuntimeNode->BoxLimits)[SelectCollisionIndex];
	case ECollisionLimitType::Planar:
		return &(bData ? RuntimeNode->PlanarLimitsData : RuntimeNode->PlanarLimits)[SelectCollisionIndex];
	default:
		break;
	}
	return nullptr;
}

FCollisionLimitBase* FKawaiiPhysicsEditMode::GetSelectCollisionLimitGraph() const
{
	if (!IsValidSelectCollision())
	{
		return nullptr;
	}
	const bool bData = SelectCollisionIsFromDataAsset;
	switch (SelectCollisionType)
	{
	case ECollisionLimitType::Spherical:
		return &(bData ? GraphNode->Node.SphericalLimitsData : GraphNode->Node.SphericalLimits)[SelectCollisionIndex];
	case ECollisionLimitType::Capsule:
		return &(bData ? GraphNode->Node.CapsuleLimitsData : GraphNode->Node.CapsuleLimits)[SelectCollisionIndex];
	case ECollisionLimitType::TaperedCapsule:
		return &(bData ? GraphNode->Node.TaperedCapsuleLimitsData : GraphNode->Node.TaperedCapsuleLimits)[SelectCollisionIndex];
	case ECollisionLimitType::Box:
		return &(bData ? GraphNode->Node.BoxLimitsData : GraphNode->Node.BoxLimits)[SelectCollisionIndex];
	case ECollisionLimitType::Planar:
		return &(bData ? GraphNode->Node.PlanarLimitsData : GraphNode->Node.PlanarLimits)[SelectCollisionIndex];
	default:
		break;
	}
	return nullptr;
}

void FKawaiiPhysicsEditMode::DoTranslation(FVector& InTranslation)
{
	if (InTranslation.IsNearlyZero())
	{
		return;
	}
	FCollisionLimitBase* CollisionRuntime = GetSelectCollisionLimitRuntime();
	FCollisionLimitBase* CollisionGraph = GetSelectCollisionLimitGraph();
	if (!CollisionRuntime || !CollisionGraph)
	{
		return;
	}
	// (the drag is in the world: into the mesh's space, then the driving bone's)
	FVector InComponent = ComponentToWorld().InverseTransformVector(InTranslation);
	FVector Offset = InComponent;
	if (CollisionRuntime->DrivingBone.BoneIndex >= 0 && RuntimeNode->ForwardedPose.GetPose().IsValid())
	{
		USkeletalMeshComponent* SkelComp = GetAnimPreviewScene().GetPreviewMeshComponent();
		Offset = ConvertCSVectorToBoneSpace(SkelComp, InComponent, RuntimeNode->ForwardedPose, CollisionRuntime->DrivingBone.BoneName, BCS_BoneSpace);
	}
	CollisionRuntime->OffsetLocation += Offset;
	CollisionGraph->OffsetLocation = CollisionRuntime->OffsetLocation;

	if (SelectCollisionIsFromDataAsset && RuntimeNode->LimitsDataAsset)
	{
		RuntimeNode->LimitsDataAsset->Modify();
		RuntimeNode->LimitsDataAsset->UpdateLimit(CollisionRuntime);
	}
}

void FKawaiiPhysicsEditMode::DoRotation(FRotator& InRotation)
{
	if (InRotation.IsNearlyZero())
	{
		return;
	}
	FCollisionLimitBase* CollisionRuntime = GetSelectCollisionLimitRuntime();
	FCollisionLimitBase* CollisionGraph = GetSelectCollisionLimitGraph();
	if (!CollisionRuntime || !CollisionGraph)
	{
		return;
	}
	// (the turn is about a world axis: that axis in the mesh's space, then in the driving bone's)
	FVector Axis;
	float Angle;
	InRotation.Quaternion().ToAxisAndAngle(Axis, Angle);
	FRotator InComponent = FQuat(ComponentToWorld().InverseTransformVectorNoScale(Axis).GetSafeNormal(), Angle).Rotator();
	USkeletalMeshComponent* SkelComp = GetAnimPreviewScene().GetPreviewMeshComponent();
	FQuat DeltaQuat = InComponent.Quaternion();
	if (CollisionRuntime->DrivingBone.BoneIndex >= 0 && RuntimeNode->ForwardedPose.GetPose().IsValid())
	{
		DeltaQuat = ConvertCSRotationToBoneSpace(SkelComp, InComponent, RuntimeNode->ForwardedPose, CollisionRuntime->DrivingBone.BoneName, BCS_BoneSpace);
	}
	CollisionRuntime->OffsetRotation = FRotator(DeltaQuat * CollisionRuntime->OffsetRotation.Quaternion());
	CollisionGraph->OffsetRotation = CollisionRuntime->OffsetRotation;

	if (SelectCollisionIsFromDataAsset && RuntimeNode->LimitsDataAsset)
	{
		RuntimeNode->LimitsDataAsset->Modify();
		RuntimeNode->LimitsDataAsset->UpdateLimit(CollisionRuntime);
	}
}

void FKawaiiPhysicsEditMode::DoScale(FVector& InScale)
{
	if (!IsValidSelectCollision() || InScale.IsNearlyZero() || SelectCollisionType == ECollisionLimitType::Planar)
	{
		return;
	}
	const bool bData = SelectCollisionIsFromDataAsset;
	FCollisionLimitBase* Changed = nullptr;
	if (SelectCollisionType == ECollisionLimitType::Spherical)
	{
		FSphericalLimit& R = (bData ? RuntimeNode->SphericalLimitsData : RuntimeNode->SphericalLimits)[SelectCollisionIndex];
		FSphericalLimit& G = (bData ? GraphNode->Node.SphericalLimitsData : GraphNode->Node.SphericalLimits)[SelectCollisionIndex];
		R.Radius = FMath::Max(R.Radius + InScale.X + InScale.Y + InScale.Z, 0.0f);
		G.Radius = R.Radius;
		Changed = &R;
	}
	else if (SelectCollisionType == ECollisionLimitType::Capsule)
	{
		FCapsuleLimit& R = (bData ? RuntimeNode->CapsuleLimitsData : RuntimeNode->CapsuleLimits)[SelectCollisionIndex];
		FCapsuleLimit& G = (bData ? GraphNode->Node.CapsuleLimitsData : GraphNode->Node.CapsuleLimits)[SelectCollisionIndex];
		R.Radius = FMath::Max(R.Radius + InScale.X + InScale.Y, 0.0f);
		R.Length = FMath::Max(R.Length + InScale.Z, 0.0f);
		G.Radius = R.Radius;
		G.Length = R.Length;
		Changed = &R;
	}
	else if (SelectCollisionType == ECollisionLimitType::TaperedCapsule)
	{
		// (X: the +Z end's radius, Y: the -Z end's, Z: the length)
		FTaperedCapsuleLimit& R = (bData ? RuntimeNode->TaperedCapsuleLimitsData : RuntimeNode->TaperedCapsuleLimits)[SelectCollisionIndex];
		FTaperedCapsuleLimit& G = (bData ? GraphNode->Node.TaperedCapsuleLimitsData : GraphNode->Node.TaperedCapsuleLimits)[SelectCollisionIndex];
		R.Radius0 = FMath::Max(R.Radius0 + InScale.X, 0.0f);
		R.Radius1 = FMath::Max(R.Radius1 + InScale.Y, 0.0f);
		R.Length = FMath::Max(R.Length + InScale.Z, 0.0f);
		G.Radius0 = R.Radius0;
		G.Radius1 = R.Radius1;
		G.Length = R.Length;
		Changed = &R;
	}
	else if (SelectCollisionType == ECollisionLimitType::Box)
	{
		FBoxLimit& R = (bData ? RuntimeNode->BoxLimitsData : RuntimeNode->BoxLimits)[SelectCollisionIndex];
		FBoxLimit& G = (bData ? GraphNode->Node.BoxLimitsData : GraphNode->Node.BoxLimits)[SelectCollisionIndex];
		R.Extent = (R.Extent + InScale).ComponentMax(FVector::ZeroVector);
		G.Extent = R.Extent;
		Changed = &R;
	}
	if (Changed && bData && RuntimeNode->LimitsDataAsset)
	{
		RuntimeNode->LimitsDataAsset->Modify();
		RuntimeNode->LimitsDataAsset->UpdateLimit(Changed);
	}
}

bool FKawaiiPhysicsEditMode::ShouldDrawWidget() const
{
	return IsValidSelectCollision();
}

void FKawaiiPhysicsEditMode::DrawHUD(FEditorViewportClient* ViewportClient, FViewport* Viewport, const FSceneView* View, FCanvas* Canvas)
{
	float FontWidth, FontHeight;
	GEngine->GetSmallFont()->GetCharSize(TEXT('L'), FontWidth, FontHeight);

	const float XOffset = 5.0f;
	float DrawPositionY = Viewport->GetSizeXY().Y / Canvas->GetDPIScale() - (3 + FontHeight) - 100 / Canvas->GetDPIScale();

	DrawTextItem(LOCTEXT("CycleCoords", "Q : Cycle Transform Coordinate System"), Canvas, XOffset, DrawPositionY, FontHeight);
	DrawTextItem(LOCTEXT("CycleModes", "Space : Cycle Between Translate, Rotate and Scale"), Canvas, XOffset, DrawPositionY, FontHeight);
	DrawTextItem(LOCTEXT("ScaleMode", "R : Scale Mode (tapered capsule: X the +Z end, Y the -Z end, Z the length)"), Canvas, XOffset, DrawPositionY, FontHeight);
	DrawTextItem(LOCTEXT("RotateMode", "E : Rotate Mode"), Canvas, XOffset, DrawPositionY, FontHeight);
	DrawTextItem(LOCTEXT("TranslateMode", "W : Translate Mode"), Canvas, XOffset, DrawPositionY, FontHeight);
	DrawTextItem(LOCTEXT("DeleteShape", "Delete : remove the selected shape (the node's own)"), Canvas, XOffset, DrawPositionY, FontHeight);
	DrawTextItem(LOCTEXT("Separator", "------------------"), Canvas, XOffset, DrawPositionY, FontHeight);

	FString CollisionDebugInfo = FString(TEXT("Select Collision : "));
	switch (SelectCollisionType)
	{
	case ECollisionLimitType::Spherical: CollisionDebugInfo.Append(TEXT("Spherical")); break;
	case ECollisionLimitType::Capsule: CollisionDebugInfo.Append(TEXT("Capsule")); break;
	case ECollisionLimitType::TaperedCapsule: CollisionDebugInfo.Append(TEXT("Tapered Capsule")); break;
	case ECollisionLimitType::Box: CollisionDebugInfo.Append(TEXT("Box")); break;
	case ECollisionLimitType::Planar: CollisionDebugInfo.Append(TEXT("Planar")); break;
	default: CollisionDebugInfo.Append(TEXT("None")); break;
	}
	if (SelectCollisionIndex >= 0)
	{
		CollisionDebugInfo.Append(FString::Printf(TEXT("[%d]%s"), SelectCollisionIndex, SelectCollisionIsFromDataAsset ? TEXT(" (Limits Data Asset)") : TEXT("")));
	}
	DrawTextItem(FText::FromString(CollisionDebugInfo), Canvas, XOffset, DrawPositionY, FontHeight);

	if (RuntimeNode)
	{
		const FString Problem = RuntimeNode->GetProblem();
		if (!Problem.IsEmpty())
		{
			DrawTextItem(FText::FromString(TEXT("KawaiiPhysics does NOT run: ") + Problem), Canvas, XOffset, DrawPositionY, FontHeight);
		}
	}

	if (GraphNode && RuntimeNode && GraphNode->bEnableDebugBoneLengthRate)
	{
		UDebugSkelMeshComponent* PreviewMeshComponent = GetAnimPreviewScene().GetPreviewMeshComponent();
		if (PreviewMeshComponent != nullptr && PreviewMeshComponent->MeshObject != nullptr)
		{
			TArray<FKawaiiPhysicsDebugBone> Bones;
			RuntimeNode->GetDebugBones(Bones);
			const FTransform ToWorld = PreviewMeshComponent->GetComponentTransform();
			for (const FKawaiiPhysicsDebugBone& Bone : Bones)
			{
				if (Bone.bDummy) { continue; }
				Draw3DTextItem(FText::AsNumber(Bone.LengthRate), Canvas, View, Viewport, ToWorld.TransformPosition(Bone.Location));
			}
		}
	}

	FKawaiiPhysicsEditModeBase::DrawHUD(ViewportClient, Viewport, View, Canvas);
}

void FKawaiiPhysicsEditMode::DrawTextItem(FText Text, FCanvas* Canvas, float X, float& Y, float FontHeight)
{
	FCanvasTextItem TextItem(FVector2D::ZeroVector, Text, GEngine->GetSmallFont(), FLinearColor::White);
	TextItem.EnableShadow(FLinearColor::Black);
	Canvas->DrawItem(TextItem, X, Y);
	Y -= (3 + FontHeight);
}

void FKawaiiPhysicsEditMode::Draw3DTextItem(FText Text, FCanvas* Canvas, const FSceneView* View, FViewport* Viewport, FVector Location)
{
	const int32 HalfX = Viewport->GetSizeXY().X / 2 / Canvas->GetDPIScale();
	const int32 HalfY = Viewport->GetSizeXY().Y / 2 / Canvas->GetDPIScale();

	const FPlane Proj = View->Project(Location);
	if (Proj.W > 0.f)
	{
		const int32 XPos = HalfX + (HalfX * Proj.X);
		const int32 YPos = HalfY + (HalfY * (Proj.Y * -1));
		FCanvasTextItem TextItem(FVector2D(XPos, YPos), Text, GEngine->GetSmallFont(), FLinearColor::White);
		TextItem.EnableShadow(FLinearColor::Black);
		Canvas->DrawItem(TextItem);
	}
}

#undef LOCTEXT_NAMESPACE
