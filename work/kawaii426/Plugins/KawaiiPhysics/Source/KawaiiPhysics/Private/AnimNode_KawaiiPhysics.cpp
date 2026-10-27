// KawaiiPhysics for UE 4.26 with the newest KawaiiPhysics' features: the node runs the game mod's simulation
// (KawaiiSolver.hpp, Create a Character System), so the End editor's preview moves the bones as the game will.
// KawaiiPhysics is pafuhana1213's (https://github.com/pafuhana1213/KawaiiPhysics), MIT License.
#include "AnimNode_KawaiiPhysics.h"

#include "KawaiiPhysics.h"
#include "KawaiiPhysicsLimitsDataAsset.h"
#include "AnimationRuntime.h"
#include "Animation/AnimInstanceProxy.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"

#include <memory>
#include <string>
#include <vector>

THIRD_PARTY_INCLUDES_START
#include "SkelCompatCore.hpp"
#include "KawaiiSolver.hpp"
THIRD_PARTY_INCLUDES_END

// ---- the simulation, held by the node ---------------------------------------------------
struct FKawaiiPhysicsSolver
{
	SkelCompat::KawaiiNode Config;
	std::wstring ConfigText;                 // (the config as the game's JSON: a change makes a new simulation, or retunes it)
	std::wstring ChainText;                  // (what its chains are made from: as long as this stays, an edit retunes it)
	std::unique_ptr<Kawaii::Node> Node;
	Kawaii::Skeleton Skeleton;
	const USkeletalMesh* SkeletonMesh = nullptr;   // the mesh (or skeleton) the bone table was made for
	const USkeleton* SkeletonAsset = nullptr;
	int32 SkeletonBones = 0;
	std::vector<Kawaii::Xf> RefLocal;        // the reference pose (local)
	std::vector<Kawaii::Xf> Pose;            // this frame's, component space
	std::vector<uint8_t> Changed;
	std::vector<Kawaii::Node::DebugBone> Debug;
	FString Problem;
};

FKawaiiPhysicsSolverHolder::FKawaiiPhysicsSolverHolder() = default;
FKawaiiPhysicsSolverHolder::FKawaiiPhysicsSolverHolder(const FKawaiiPhysicsSolverHolder&) {}
FKawaiiPhysicsSolverHolder& FKawaiiPhysicsSolverHolder::operator=(const FKawaiiPhysicsSolverHolder&)
{
	Reset();
	return *this;
}
FKawaiiPhysicsSolverHolder::~FKawaiiPhysicsSolverHolder() { Reset(); }
void FKawaiiPhysicsSolverHolder::Reset(FKawaiiPhysicsSolver* InSolver)
{
	if (Solver != InSolver)
	{
		delete Solver;
		Solver = InSolver;
	}
}

namespace
{
std::wstring Wide(const FName& Name) { return Name.IsNone() ? std::wstring() : std::wstring(*Name.ToString()); }

Kawaii::Xf ToKawaii(const FTransform& T)
{
	Kawaii::Xf X;
	const FQuat Q = T.GetRotation();
	const FVector L = T.GetLocation();
	const FVector S = T.GetScale3D();
	X.R = {Q.X, Q.Y, Q.Z, Q.W};
	X.T = {L.X, L.Y, L.Z};
	X.S = {S.X, S.Y, S.Z};
	return X;
}

FTransform ToUnreal(const Kawaii::Xf& X)
{
	FQuat Q(X.R.X, X.R.Y, X.R.Z, X.R.W);
	Q.Normalize();
	return FTransform(Q, FVector(X.T.X, X.T.Y, X.T.Z), FVector(X.S.X, X.S.Y, X.S.Z));
}

void Triple(const FVector& V, float (&Out)[3])
{
	Out[0] = V.X;
	Out[1] = V.Y;
	Out[2] = V.Z;
}

// A curve as the game's linear keys (a curve with no keys: none, the setting as it is)
void CurveOf(const FRuntimeFloatCurve& Curve, SkelCompat::KawaiiCurve& Out)
{
	Out.Keys.clear();
	const FRichCurve* Rich = Curve.GetRichCurveConst();
	if (!Rich || Rich->GetNumKeys() == 0)
	{
		return;
	}
	bool bLinear = true;
	for (auto It = Rich->GetKeyIterator(); It; ++It)
	{
		bLinear &= It->InterpMode == RCIM_Linear;
	}
	if (bLinear && Rich->GetNumKeys() <= int32(SkelCompat::MaxKawaiiCurveKeys))
	{
		float Last = -1.0f;
		for (auto It = Rich->GetKeyIterator(); It; ++It)
		{
			const float Time = FMath::Clamp(It->Time, 0.0f, 1.0f);
			if (Time > Last)
			{
				Out.Keys.push_back({Time, It->Value});
				Last = Time;
			}
		}
		return;
	}
	// (cubic or constant keys: sampled)
	for (int32 i = 0; i <= 32; ++i)
	{
		const float Time = float(i) / 32.0f;
		Out.Keys.push_back({Time, Rich->Eval(Time)});
	}
}

void LimitBase(const FCollisionLimitBase& In, SkelCompat::KawaiiLimit& Out)
{
	Out.Bone = Wide(In.DrivingBone.BoneName);
	Triple(In.OffsetLocation, Out.Offset);
	Out.Rotation[0] = In.OffsetRotation.Pitch;
	Out.Rotation[1] = In.OffsetRotation.Yaw;
	Out.Rotation[2] = In.OffsetRotation.Roll;
}

SkelCompat::KawaiiCompliance ComplianceOf(EXPBDComplianceType Type)
{
	switch (Type)
	{
	case EXPBDComplianceType::Concrete: return SkelCompat::KawaiiCompliance::Concrete;
	case EXPBDComplianceType::Wood: return SkelCompat::KawaiiCompliance::Wood;
	case EXPBDComplianceType::Leather: return SkelCompat::KawaiiCompliance::Leather;
	case EXPBDComplianceType::Tendon: return SkelCompat::KawaiiCompliance::Tendon;
	case EXPBDComplianceType::Rubber: return SkelCompat::KawaiiCompliance::Rubber;
	case EXPBDComplianceType::Muscle: return SkelCompat::KawaiiCompliance::Muscle;
	case EXPBDComplianceType::Fat: return SkelCompat::KawaiiCompliance::Fat;
	}
	return SkelCompat::KawaiiCompliance::Leather;
}

// The node's settings as the game mod's node (the same structure its JSON makes)
void ConfigOf(const FAnimNode_KawaiiPhysics& N, SkelCompat::KawaiiNode& C)
{
	C = SkelCompat::KawaiiNode();
	C.RootBone = Wide(N.RootBone.BoneName);
	C.Name = N.NodeName.IsEmpty() ? C.RootBone : std::wstring(*N.NodeName);
	for (const FBoneReference& Bone : N.ExcludeBones)
	{
		if (!Bone.BoneName.IsNone()) { C.ExcludeBones.push_back(Wide(Bone.BoneName)); }
	}
	for (const FKawaiiPhysicsRootBoneSetting& Root : N.AdditionalRootBones)
	{
		if (Root.RootBone.BoneName.IsNone()) { continue; }
		SkelCompat::KawaiiRoot R;
		R.Bone = Wide(Root.RootBone.BoneName);
		R.OverrideExcludeBones = Root.bUseOverrideExcludeBones;
		for (const FBoneReference& Bone : Root.OverrideExcludeBones)
		{
			if (!Bone.BoneName.IsNone()) { R.ExcludeBones.push_back(Wide(Bone.BoneName)); }
		}
		C.AdditionalRootBones.push_back(R);
	}
	C.Damping = FMath::Clamp(N.PhysicsSettings.Damping, 0.0f, 1.0f);
	C.Stiffness = FMath::Clamp(N.PhysicsSettings.Stiffness, 0.0f, 1.0f);
	C.WorldDampingLocation = FMath::Clamp(N.PhysicsSettings.WorldDampingLocation, 0.0f, 1.0f);
	C.WorldDampingRotation = FMath::Clamp(N.PhysicsSettings.WorldDampingRotation, 0.0f, 1.0f);
	C.Radius = FMath::Max(N.PhysicsSettings.Radius, 0.0f);
	C.LimitAngle = FMath::Clamp(N.PhysicsSettings.LimitAngle, 0.0f, 360.0f);
	CurveOf(N.DampingCurveData, C.DampingCurve);
	CurveOf(N.StiffnessCurveData, C.StiffnessCurve);
	CurveOf(N.WorldDampingLocationCurveData, C.WorldDampingLocationCurve);
	CurveOf(N.WorldDampingRotationCurveData, C.WorldDampingRotationCurve);
	CurveOf(N.RadiusCurveData, C.RadiusCurve);
	CurveOf(N.LimitAngleCurveData, C.LimitAngleCurve);
	C.DummyBoneLength = FMath::Max(N.DummyBoneLength, 0.0f);
	C.BoneForwardAxis = static_cast<SkelCompat::KawaiiAxis>(N.BoneForwardAxis);
	C.BoneSubdivisionCount = FMath::Clamp(N.BoneSubdivisionCount, 0, 10);
	C.BoneSubdivisionCollisionOnly = N.bBoneSubdivisionCollisionOnly;
	C.BoneSubdivisionDensifyByRadius = N.bBoneSubdivisionDensifyByRadius;
	C.PlanarConstraint = static_cast<SkelCompat::KawaiiPlanar>(N.PlanarConstraint);
	C.SimulationSpace = static_cast<SkelCompat::KawaiiSpace>(N.SimulationSpace);
	C.SimulationBaseBone = Wide(N.SimulationBaseBone.BoneName);
	if (C.SimulationSpace == SkelCompat::KawaiiSpace::BaseBone && C.SimulationBaseBone.empty())
	{
		C.SimulationSpace = SkelCompat::KawaiiSpace::Component;
	}
	C.TargetFramerate = FMath::Clamp(N.TargetFramerate, 1, 1000);
	C.UseFixedSubstepping = N.bUseFixedSubstepping;
	C.MaxSubsteps = FMath::Clamp(N.MaxSubsteps, 1, 64);
	C.NeedWarmUp = N.bNeedWarmUp;
	C.WarmUpFrames = FMath::Clamp(N.WarmUpFrames, 0, 1000);
	C.UseWarmUpWhenResetDynamics = N.bUseWarmUpWhenResetDynamics;
	C.TeleportDistanceThreshold = FMath::Max(N.TeleportDistanceThreshold, 0.0f);
	C.TeleportRotationThreshold = FMath::Clamp(N.TeleportRotationThreshold, 0.0f, 360.0f);
	Triple(N.SkelCompMoveScale, C.SkelCompMoveScale);
	// shapes (the node's and its data asset's)
	for (const TArray<FSphericalLimit>* List : {&N.SphericalLimits, &N.SphericalLimitsData})
	{
		for (const FSphericalLimit& L : *List)
		{
			SkelCompat::KawaiiLimit K;
			LimitBase(L, K);
			K.Radius = L.Radius;
			K.Inner = L.LimitType == ESphericalLimitType::Inner;
			if (!K.Bone.empty()) { C.Spheres.push_back(K); }
		}
	}
	for (const TArray<FCapsuleLimit>* List : {&N.CapsuleLimits, &N.CapsuleLimitsData})
	{
		for (const FCapsuleLimit& L : *List)
		{
			SkelCompat::KawaiiLimit K;
			LimitBase(L, K);
			K.Radius = L.Radius;
			K.Length = L.Length;
			if (!K.Bone.empty()) { C.Capsules.push_back(K); }
		}
	}
	for (const TArray<FTaperedCapsuleLimit>* List : {&N.TaperedCapsuleLimits, &N.TaperedCapsuleLimitsData})
	{
		for (const FTaperedCapsuleLimit& L : *List)
		{
			SkelCompat::KawaiiLimit K;
			LimitBase(L, K);
			K.Radius0 = L.Radius0;
			K.Radius1 = L.Radius1;
			K.Length = L.Length;
			if (!K.Bone.empty()) { C.TaperedCapsules.push_back(K); }
		}
	}
	for (const TArray<FBoxLimit>* List : {&N.BoxLimits, &N.BoxLimitsData})
	{
		for (const FBoxLimit& L : *List)
		{
			SkelCompat::KawaiiLimit K;
			LimitBase(L, K);
			Triple(L.Extent, K.Extent);
			if (!K.Bone.empty()) { C.Boxes.push_back(K); }
		}
	}
	for (const TArray<FPlanarLimit>* List : {&N.PlanarLimits, &N.PlanarLimitsData})
	{
		for (const FPlanarLimit& L : *List)
		{
			SkelCompat::KawaiiLimit K;
			LimitBase(L, K);
			C.Planes.push_back(K);   // (without a bone: in the component's space, a floor)
		}
	}
	// bone constraints
	C.BoneConstraintGlobalCompliance = ComplianceOf(N.BoneConstraintGlobalComplianceType);
	C.BoneConstraintIterationsBeforeCollision = FMath::Clamp(N.BoneConstraintIterationCountBeforeCollision, 0, 64);
	C.BoneConstraintIterationsAfterCollision = FMath::Clamp(N.BoneConstraintIterationCountAfterCollision, 0, 64);
	C.AutoAddChildDummyBoneConstraint = N.bAutoAddChildDummyBoneConstraint;
	C.BoneConstraintSubdivisionCount = FMath::Clamp(N.BoneConstraintSubdivisionCount, 0, 10);
	C.BoneConstraintSubdivisionFeedbackScale = FMath::Clamp(N.BoneConstraintSubdivisionFeedbackScale, 0.0f, 2.0f);
	for (const FModifyBoneConstraint& B : N.BoneConstraints)
	{
		if (B.Bone1.BoneName.IsNone() || B.Bone2.BoneName.IsNone() || B.Bone1.BoneName == B.Bone2.BoneName) { continue; }
		SkelCompat::KawaiiBoneConstraint K;
		K.Bone1 = Wide(B.Bone1.BoneName);
		K.Bone2 = Wide(B.Bone2.BoneName);
		K.OverrideCompliance = B.bOverrideCompliance;
		K.Compliance = ComplianceOf(B.ComplianceType);
		K.ExcludeFromSubdivision = B.bExcludeFromSubdivision;
		C.BoneConstraints.push_back(K);
	}
	// forces
	Triple(N.Gravity, C.Gravity);
	C.UseLegacyGravity = N.bUseLegacyGravity;
	C.UseDefaultGravityZ = N.bUseDefaultGravityZProjectSetting;
	C.UseWorldSpaceGravity = N.bUseWorldSpaceGravity;
	Triple(N.SimpleExternalForce, C.SimpleExternalForce);
	C.UseWorldSpaceSimpleExternalForce = N.bUseWorldSpaceSimpleExternalForce;
	C.SkipBonamikBones = N.bSkipBonamikBones;
}
// What the node's chains are made from (the bones, dummy and inserted points, the space, the bone constraints, the
// warm-up): the config with everything else at its defaults. Two configs with the same of this make the same chains, so
// an edit of the rest (values, curves, forces, limits, shapes) retunes the running simulation (Kawaii::Node::Retune: the
// bones go on from where they are) instead of starting it again.
SkelCompat::KawaiiNode ChainsOf(const SkelCompat::KawaiiNode& C)
{
	const SkelCompat::KawaiiNode D;
	SkelCompat::KawaiiNode K = C;
	K.Name = D.Name;
	K.Damping = D.Damping;
	K.Stiffness = D.Stiffness;
	K.WorldDampingLocation = D.WorldDampingLocation;
	K.WorldDampingRotation = D.WorldDampingRotation;
	K.LimitAngle = D.LimitAngle;
	K.DampingCurve = D.DampingCurve;
	K.StiffnessCurve = D.StiffnessCurve;
	K.WorldDampingLocationCurve = D.WorldDampingLocationCurve;
	K.WorldDampingRotationCurve = D.WorldDampingRotationCurve;
	K.LimitAngleCurve = D.LimitAngleCurve;
	if (C.BoneSubdivisionCount == 0 && C.BoneConstraintSubdivisionCount == 0)
	{
		K.Radius = D.Radius;                 // (with inserted points, the radius places them: part of the chains)
		K.RadiusCurve = D.RadiusCurve;
	}
	K.TargetFramerate = D.TargetFramerate;
	K.UseFixedSubstepping = D.UseFixedSubstepping;
	K.MaxSubsteps = D.MaxSubsteps;
	K.TeleportDistanceThreshold = D.TeleportDistanceThreshold;
	K.TeleportRotationThreshold = D.TeleportRotationThreshold;
	K.PlanarConstraint = D.PlanarConstraint;
	for (int i = 0; i < 3; ++i)
	{
		K.SkelCompMoveScale[i] = D.SkelCompMoveScale[i];
		K.Gravity[i] = D.Gravity[i];
		K.SimpleExternalForce[i] = D.SimpleExternalForce[i];
	}
	K.Spheres.clear();
	K.Capsules.clear();
	K.TaperedCapsules.clear();
	K.Boxes.clear();
	K.Planes.clear();
	K.BoneConstraintGlobalCompliance = D.BoneConstraintGlobalCompliance;
	K.BoneConstraintIterationsBeforeCollision = D.BoneConstraintIterationsBeforeCollision;
	K.BoneConstraintIterationsAfterCollision = D.BoneConstraintIterationsAfterCollision;
	K.BoneConstraintSubdivisionFeedbackScale = D.BoneConstraintSubdivisionFeedbackScale;
	K.UseLegacyGravity = D.UseLegacyGravity;
	K.UseDefaultGravityZ = D.UseDefaultGravityZ;
	K.UseWorldSpaceGravity = D.UseWorldSpaceGravity;
	K.UseWorldSpaceSimpleExternalForce = D.UseWorldSpaceSimpleExternalForce;
	return K;
}
} // namespace

// ---- the node -------------------------------------------------------------------------------
FAnimNode_KawaiiPhysics::FAnimNode_KawaiiPhysics() {}

void FAnimNode_KawaiiPhysics::Initialize_AnyThread(const FAnimationInitializeContext& Context)
{
	FAnimNode_SkeletalControlBase::Initialize_AnyThread(Context);
	const FBoneContainer& RequiredBones = Context.AnimInstanceProxy->GetRequiredBones();
	ApplyLimitsDataAsset(RequiredBones);
	InitializeBoneReferences(RequiredBones);
	Solver.Reset();
	PendingTeleport = ETeleportType::None;
#if WITH_EDITORONLY_DATA
	bEditing = false;
	if (const USkeletalMeshComponent* Mesh = Context.AnimInstanceProxy->GetSkelMeshComponent())
	{
		if (const UWorld* World = Mesh->GetWorld())
		{
			bEditing = World->WorldType == EWorldType::Editor || World->WorldType == EWorldType::EditorPreview;
		}
	}
#endif
}

void FAnimNode_KawaiiPhysics::ResetDynamics(ETeleportType InTeleportType)
{
	if (InTeleportType == ETeleportType::ResetPhysics || PendingTeleport == ETeleportType::None)
	{
		PendingTeleport = InTeleportType;
	}
}

void FAnimNode_KawaiiPhysics::UpdateInternal(const FAnimationUpdateContext& Context)
{
	FAnimNode_SkeletalControlBase::UpdateInternal(Context);
	DeltaTime = Context.GetDeltaTime();
}

bool FAnimNode_KawaiiPhysics::IsValidToEvaluate(const USkeleton* Skeleton, const FBoneContainer& RequiredBones)
{
	if (bBonesDirty)
	{
		// (new settings copied in by the editor: their bone references were made for the skeleton, not this mesh)
		bBonesDirty = false;
		ApplyLimitsDataAsset(RequiredBones);
		InitializeBoneReferences(RequiredBones);
	}
	return RootBone.IsValidToEvaluate(RequiredBones);
}

void FAnimNode_KawaiiPhysics::InitializeBoneReferences(const FBoneContainer& RequiredBones)
{
	RootBone.Initialize(RequiredBones);
	for (FBoneReference& Bone : ExcludeBones) { Bone.Initialize(RequiredBones); }
	for (FKawaiiPhysicsRootBoneSetting& Root : AdditionalRootBones)
	{
		Root.RootBone.Initialize(RequiredBones);
		for (FBoneReference& Bone : Root.OverrideExcludeBones) { Bone.Initialize(RequiredBones); }
	}
	SimulationBaseBone.Initialize(RequiredBones);
	auto InitShapes = [&](auto& List) {
		for (auto& Limit : List) { Limit.DrivingBone.Initialize(RequiredBones); }
	};
	InitShapes(SphericalLimits);
	InitShapes(CapsuleLimits);
	InitShapes(TaperedCapsuleLimits);
	InitShapes(BoxLimits);
	InitShapes(PlanarLimits);
	InitShapes(SphericalLimitsData);
	InitShapes(CapsuleLimitsData);
	InitShapes(TaperedCapsuleLimitsData);
	InitShapes(BoxLimitsData);
	InitShapes(PlanarLimitsData);
	for (FModifyBoneConstraint& Constraint : BoneConstraints)
	{
		Constraint.Bone1.Initialize(RequiredBones);
		Constraint.Bone2.Initialize(RequiredBones);
	}
}

void FAnimNode_KawaiiPhysics::ApplyLimitsDataAsset(const FBoneContainer& RequiredBones)
{
	SphericalLimitsData.Reset();
	CapsuleLimitsData.Reset();
	TaperedCapsuleLimitsData.Reset();
	BoxLimitsData.Reset();
	PlanarLimitsData.Reset();
	if (!LimitsDataAsset)
	{
		return;
	}
	SphericalLimitsData = LimitsDataAsset->SphericalLimits;
	CapsuleLimitsData = LimitsDataAsset->CapsuleLimits;
	TaperedCapsuleLimitsData = LimitsDataAsset->TaperedCapsuleLimits;
	BoxLimitsData = LimitsDataAsset->BoxLimits;
	PlanarLimitsData = LimitsDataAsset->PlanarLimits;
	auto InitShapes = [&](auto& List) {
		for (auto& Limit : List) { Limit.DrivingBone.Initialize(RequiredBones); }
	};
	InitShapes(SphericalLimitsData);
	InitShapes(CapsuleLimitsData);
	InitShapes(TaperedCapsuleLimitsData);
	InitShapes(BoxLimitsData);
	InitShapes(PlanarLimitsData);
}

// Where each shape is now (component space), for the editor's drawing and its handles
void FAnimNode_KawaiiPhysics::UpdateShapePlaces(FComponentSpacePoseContext& Output, const FBoneContainer& BoneContainer)
{
	auto Place = [&](FCollisionLimitBase& Limit) -> bool {
		const FTransform Offset(Limit.OffsetRotation, Limit.OffsetLocation);
		if (Limit.DrivingBone.IsValidToEvaluate(BoneContainer))
		{
			const FTransform Bone = Output.Pose.GetComponentSpaceTransform(Limit.DrivingBone.GetCompactPoseIndex(BoneContainer));
			const FTransform Placed = Offset * Bone;
			Limit.Location = Placed.GetLocation();
			Limit.Rotation = Placed.GetRotation();
			return true;
		}
		Limit.Location = Offset.GetLocation();
		Limit.Rotation = Offset.GetRotation();
		return false;
	};
	for (auto* List : {&SphericalLimits, &SphericalLimitsData}) { for (auto& L : *List) { Place(L); } }
	for (auto* List : {&CapsuleLimits, &CapsuleLimitsData}) { for (auto& L : *List) { Place(L); } }
	for (auto* List : {&TaperedCapsuleLimits, &TaperedCapsuleLimitsData}) { for (auto& L : *List) { Place(L); } }
	for (auto* List : {&BoxLimits, &BoxLimitsData}) { for (auto& L : *List) { Place(L); } }
	for (auto* List : {&PlanarLimits, &PlanarLimitsData})
	{
		for (auto& L : *List)
		{
			Place(L);
			L.Rotation.Normalize();
			L.Plane = FPlane(L.Location, L.Rotation.GetUpVector());
		}
	}
}

DECLARE_CYCLE_STAT(TEXT("KawaiiPhysics_Eval"), STAT_KawaiiPhysics_Eval, STATGROUP_Anim);

void FAnimNode_KawaiiPhysics::EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output, TArray<FBoneTransform>& OutBoneTransforms)
{
	SCOPE_CYCLE_COUNTER(STAT_KawaiiPhysics_Eval);
	check(OutBoneTransforms.Num() == 0);

	const FBoneContainer& BoneContainer = Output.Pose.GetPose().GetBoneContainer();
#if WITH_EDITOR
	if (LimitsDataAsset)
	{
		ApplyLimitsDataAsset(BoneContainer);   // (edits of the data asset show at once)
	}
#endif
	UpdateShapePlaces(Output, BoneContainer);

	// the settings as the game's node; in the editor, an edit of the node retunes the simulation (values, curves, forces,
	// shapes: the bones go on from where they are) or, when it changes what the chains are made from, starts it again
	FKawaiiPhysicsSolver* S = Solver.Get();
	bool bCheck = !S;
#if WITH_EDITORONLY_DATA
	bCheck |= bEditing;
#endif
	if (bCheck)
	{
		SkelCompat::KawaiiNode Config;
		ConfigOf(*this, Config);
		const std::wstring Text = SkelCompat::KawaiiNodeJson(Config);
		if (!S || S->ConfigText != Text)
		{
			const std::wstring Chains = SkelCompat::KawaiiNodeJson(ChainsOf(Config));
			if (S && S->Node && S->ChainText == Chains)
			{
				S->Config = Config;
				S->ConfigText = Text;
				S->Node->Retune(S->Config);
			}
			else
			{
				S = new FKawaiiPhysicsSolver();
				S->Config = Config;
				S->ConfigText = Text;
				S->ChainText = Chains;
				S->Node = std::make_unique<Kawaii::Node>(S->Config);
				Solver.Reset(S);
			}
		}
	}

	// the bone table (the mesh's reference skeleton)
	const FReferenceSkeleton& Ref = BoneContainer.GetReferenceSkeleton();
	const int32 Count = Ref.GetNum();
	if (S->SkeletonMesh != BoneContainer.GetSkeletalMeshAsset() || S->SkeletonAsset != BoneContainer.GetSkeletonAsset() || S->SkeletonBones != Count)
	{
		S->Skeleton = Kawaii::Skeleton();
		S->RefLocal.assign(size_t(Count), Kawaii::Xf());
		const TArray<FTransform>& RefPose = Ref.GetRefBonePose();
		for (int32 i = 0; i < Count; ++i)
		{
			S->Skeleton.Names.push_back(Wide(Ref.GetBoneName(i)));
			S->Skeleton.Parents.push_back(Ref.GetParentIndex(i));
			S->Skeleton.RefLength.push_back(RefPose.IsValidIndex(i) ? RefPose[i].GetLocation().Size() : 0.0f);
			if (RefPose.IsValidIndex(i)) { S->RefLocal[size_t(i)] = ToKawaii(RefPose[i]); }
		}
		S->SkeletonMesh = BoneContainer.GetSkeletalMeshAsset();
		S->SkeletonAsset = BoneContainer.GetSkeletonAsset();
		S->SkeletonBones = Count;
		S->Node = std::make_unique<Kawaii::Node>(S->Config);   // (the chains are made from the bones again)
	}

	if (PendingTeleport == ETeleportType::ResetPhysics) { S->Node->ResetPhysics(); }
	else if (PendingTeleport == ETeleportType::TeleportPhysics) { S->Node->Teleport(); }
	PendingTeleport = ETeleportType::None;

	// this frame's pose, every bone in component space (bones this level of detail does not use: under their parent as
	// in the reference pose)
	S->Pose.resize(size_t(Count));
	for (int32 i = 0; i < Count; ++i)
	{
		const FCompactPoseBoneIndex Compact = BoneContainer.MakeCompactPoseIndex(FMeshPoseBoneIndex(i));
		if (Compact != INDEX_NONE)
		{
			S->Pose[size_t(i)] = ToKawaii(Output.Pose.GetComponentSpaceTransform(Compact));
			continue;
		}
		const int32 Parent = Ref.GetParentIndex(i);
		S->Pose[size_t(i)] = Parent >= 0 ? Kawaii::Multiply(S->RefLocal[size_t(i)], S->Pose[size_t(Parent)]) : S->RefLocal[size_t(i)];
	}

	const FTransform ComponentTransform = Output.AnimInstanceProxy->GetComponentTransform();
	S->Changed.assign(size_t(Count), 0);
	const bool bRan = S->Node->Evaluate(S->Skeleton, S->Pose, S->Changed, ToKawaii(ComponentTransform), FMath::Clamp(DeltaTime, 0.0f, 0.25f), nullptr);
	S->Problem = bRan ? FString() : FString(S->Node->Problem.c_str());
	S->Node->Debug(S->Debug);
	if (!bRan)
	{
		return;
	}
	for (int32 i = 0; i < Count; ++i)
	{
		if (!S->Changed[size_t(i)]) { continue; }
		const FCompactPoseBoneIndex Compact = BoneContainer.MakeCompactPoseIndex(FMeshPoseBoneIndex(i));
		if (Compact == INDEX_NONE) { continue; }
		const FTransform Out = ToUnreal(S->Pose[size_t(i)]);
		if (!Out.IsValid()) { continue; }
		OutBoneTransforms.Add(FBoneTransform(Compact, Out));
	}
	OutBoneTransforms.Sort(FCompareBoneTransformIndex());
}

void FAnimNode_KawaiiPhysics::GetDebugBones(TArray<FKawaiiPhysicsDebugBone>& OutBones) const
{
	OutBones.Reset();
	const FKawaiiPhysicsSolver* S = Solver.Get();
	if (!S) { return; }
	for (const auto& B : S->Debug)
	{
		FKawaiiPhysicsDebugBone D;
		D.Location = FVector(B.Location.X, B.Location.Y, B.Location.Z);
		D.PoseLocation = FVector(B.PoseLocation.X, B.PoseLocation.Y, B.PoseLocation.Z);
		D.Radius = B.Radius;
		D.LimitAngle = B.LimitAngle;
		D.LengthRate = B.LengthRate;
		D.Parent = B.Parent;
		D.bDummy = B.Dummy;
		OutBones.Add(D);
	}
}

FString FAnimNode_KawaiiPhysics::GetProblem() const
{
	const FKawaiiPhysicsSolver* S = Solver.Get();
	return S ? S->Problem : FString();
}

FString FAnimNode_KawaiiPhysics::ToGameJson(const FString& Indent) const
{
	SkelCompat::KawaiiNode Config;
	ConfigOf(*this, Config);
	return FString(SkelCompat::KawaiiNodeJson(Config, std::wstring(*Indent)).c_str());
}
