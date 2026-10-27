// Kawaii Dynamic Motions (KawaiiPhysics for UE 4.26 with the newest KawaiiPhysics' features, and (1.9) its own motions):
// the node runs the game mod's simulation (KawaiiSolver.hpp, Create a Character System 3.15.0), so the End editor's
// preview moves the bones as the game will, its waves and key animation too.
// KawaiiPhysics is pafuhana1213's (https://github.com/pafuhana1213/KawaiiPhysics), MIT License.
#include "AnimNode_KawaiiPhysics.h"

#include "KawaiiPhysics.h"
#include "KawaiiPhysicsLimitsDataAsset.h"
#include "AnimationRuntime.h"
#include "Animation/AnimInstanceProxy.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Misc/Crc.h"

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

// (1.9) The key animation's tracks as the game's (one shared copy), as the game's parser takes them: a track a bone (the
// first of a bone's), each with keys, at most 256 tracks and 6000 keys, every track with more than one key as long as the
// first such one (others left out, as the parser would refuse them); none: null
std::shared_ptr<const std::vector<SkelCompat::KawaiiKeyTrack>> TracksOf(const FKawaiiPoseAnimation& A)
{
	auto Out = std::make_shared<std::vector<SkelCompat::KawaiiKeyTrack>>();
	TSet<FName> Seen;
	int32 Frames = 0;
	for (const FKawaiiPoseKeyTrack& T : A.Tracks)
	{
		if (Out->size() >= SkelCompat::MaxKawaiiKeyTracks) { break; }
		const int32 Count = T.Keys.Num();
		if (T.Bone.BoneName.IsNone() || Count == 0 || Count > int32(SkelCompat::MaxKawaiiKeyFrames) || Seen.Contains(T.Bone.BoneName)) { continue; }
		if (Count > 1)
		{
			if (Frames == 0) { Frames = Count; }
			else if (Count != Frames) { continue; }
		}
		Seen.Add(T.Bone.BoneName);
		SkelCompat::KawaiiKeyTrack K;
		K.Bone = Wide(T.Bone.BoneName);
		K.Keys.reserve(size_t(Count));
		for (const FQuat& Key : T.Keys)
		{
			FQuat Q = Key;
			if (Q.SizeSquared() < 1.0e-8f) { Q = FQuat::Identity; }
			Q.Normalize();
			K.Keys.push_back({Q.X, Q.Y, Q.Z, Q.W});
		}
		Out->push_back(std::move(K));
	}
	if (Out->empty()) { return nullptr; }
	return Out;
}

// (1.9) What the key animation is, for the editor's check of an edit each frame (its settings, and a checksum of its
// tracks' bones and keys: its tracks are only made again when one of these changes)
std::wstring MotionText(const FKawaiiPoseAnimation& A)
{
	uint32 Crc = 0;
	for (const FKawaiiPoseKeyTrack& T : A.Tracks)
	{
		Crc = HashCombine(Crc, GetTypeHash(T.Bone.BoneName));
		const int32 Count = T.Keys.Num();
		Crc = FCrc::MemCrc32(&Count, sizeof(Count), Crc);
		if (Count > 0) { Crc = FCrc::MemCrc32(T.Keys.GetData(), Count * int32(sizeof(FQuat)), Crc); }
	}
	return L"|motion " + std::to_wstring(A.Fps) + L" " + std::to_wstring(A.Speed) + L" " + std::to_wstring(A.Weight) +
		(A.bAdditive ? L" additive " : L" override ") + std::to_wstring(A.Tracks.Num()) + L" " + std::to_wstring(Crc);
}

// The node's settings as the game mod's node (the same structure its JSON makes). bTracks false: the key animation's
// settings without its tracks (the editor's check of an edit; it puts them in when something changed)
void ConfigOf(const FAnimNode_KawaiiPhysics& N, SkelCompat::KawaiiNode& C, bool bTracks = true)
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
	// (1.9) Dynamic Motions, within the game's parser's limits
	for (const FKawaiiPoseWave& W : N.PoseWaves)
	{
		if (C.PoseWaves.size() >= SkelCompat::MaxKawaiiWaves) { break; }
		if (W.Axis.IsNearlyZero()) { continue; }   // (no axis: the game's parser leaves such a wave out)
		SkelCompat::KawaiiWave K;
		K.Axis[0] = FMath::Clamp(W.Axis.X, -1000.0f, 1000.0f);
		K.Axis[1] = FMath::Clamp(W.Axis.Y, -1000.0f, 1000.0f);
		K.Axis[2] = FMath::Clamp(W.Axis.Z, -1000.0f, 1000.0f);
		K.LocalAxis = W.bLocalAxis;
		K.Degrees = FMath::Clamp(W.Degrees, -180.0f, 180.0f);
		K.Seconds = FMath::Clamp(W.Seconds, 0.05f, 600.0f);
		K.Phase = FMath::Clamp(W.Phase, -1.0e5f, 1.0e5f);
		K.PhasePerBone = FMath::Clamp(W.PhasePerBone, -1.0e4f, 1.0e4f);
		K.PhasePerRoot = FMath::Clamp(W.PhasePerRoot, -1.0e4f, 1.0e4f);
		for (const float Phase : W.RootPhases)
		{
			if (K.RootPhases.size() > SkelCompat::MaxKawaiiRoots) { break; }
			K.RootPhases.push_back(FMath::Clamp(Phase, -1.0e5f, 1.0e5f));
		}
		CurveOf(W.DegreesCurve, K.DegreesCurve);
		C.PoseWaves.push_back(K);
	}
	C.PoseAnimation.Fps = FMath::Clamp(N.PoseAnimation.Fps, 1.0f, 1000.0f);
	C.PoseAnimation.Speed = FMath::Clamp(N.PoseAnimation.Speed, -100.0f, 100.0f);
	C.PoseAnimation.Weight = FMath::Clamp(N.PoseAnimation.Weight, 0.0f, 1.0f);
	C.PoseAnimation.Additive = N.PoseAnimation.bAdditive;
	if (bTracks)
	{
		C.PoseAnimation.Tracks = TracksOf(N.PoseAnimation);
	}
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
	K.PoseWaves.clear();                     // (1.9: the motions move the pose, not what the chains are made from)
	K.PoseAnimation = D.PoseAnimation;
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
		ConfigOf(*this, Config, /*bTracks*/ false);
		const std::wstring Text = SkelCompat::KawaiiNodeJson(Config) + MotionText(PoseAnimation);
		if (!S || S->ConfigText != Text)
		{
			Config.PoseAnimation.Tracks = TracksOf(PoseAnimation);   // (1.9: made only when something changed)
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


// ---- (1.8) Import From Game: the game's nodes back as this editor's ----------------------------
namespace
{
FName NameOf(const std::wstring& S)
{
	return S.empty() ? FName(NAME_None) : FName(S.c_str());
}

FString TextOf(const std::wstring& S)
{
	return FString(S.c_str());
}

FBoneReference BoneOf(const std::wstring& S)
{
	FBoneReference Bone;
	Bone.BoneName = NameOf(S);
	return Bone;
}

// A curve from the game's linear keys (none: a curve without keys, the setting as it is)
void CurveFrom(const SkelCompat::KawaiiCurve& In, FRuntimeFloatCurve& Out)
{
	Out.ExternalCurve = nullptr;
	FRichCurve* Rich = Out.GetRichCurve();
	if (!Rich)
	{
		return;
	}
	Rich->Reset();
	for (const std::pair<float, float>& Key : In.Keys)
	{
		const FKeyHandle Handle = Rich->AddKey(Key.first, Key.second);
		Rich->SetKeyInterpMode(Handle, RCIM_Linear);
	}
}

void LimitFrom(const SkelCompat::KawaiiLimit& In, FCollisionLimitBase& Out)
{
	Out.DrivingBone = BoneOf(In.Bone);
	Out.OffsetLocation = FVector(In.Offset[0], In.Offset[1], In.Offset[2]);
	Out.OffsetRotation = FRotator(In.Rotation[0], In.Rotation[1], In.Rotation[2]);
}

// The inverse of ConfigOf: the game's node as this node's settings (its own shapes; no data asset)
void NodeFromConfig(const SkelCompat::KawaiiNode& C, FAnimNode_KawaiiPhysics& N)
{
	N.RootBone = BoneOf(C.RootBone);
	N.NodeName = (C.Name.empty() || C.Name == C.RootBone) ? FString() : TextOf(C.Name);
	N.ExcludeBones.Reset();
	for (const std::wstring& Bone : C.ExcludeBones)
	{
		N.ExcludeBones.Add(BoneOf(Bone));
	}
	N.AdditionalRootBones.Reset();
	for (const SkelCompat::KawaiiRoot& Root : C.AdditionalRootBones)
	{
		FKawaiiPhysicsRootBoneSetting Setting;
		Setting.RootBone = BoneOf(Root.Bone);
		Setting.bUseOverrideExcludeBones = Root.OverrideExcludeBones;
		for (const std::wstring& Bone : Root.ExcludeBones)
		{
			Setting.OverrideExcludeBones.Add(BoneOf(Bone));
		}
		N.AdditionalRootBones.Add(Setting);
	}
	N.PhysicsSettings.Damping = C.Damping;
	N.PhysicsSettings.Stiffness = C.Stiffness;
	N.PhysicsSettings.WorldDampingLocation = C.WorldDampingLocation;
	N.PhysicsSettings.WorldDampingRotation = C.WorldDampingRotation;
	N.PhysicsSettings.Radius = C.Radius;
	N.PhysicsSettings.LimitAngle = C.LimitAngle;
	CurveFrom(C.DampingCurve, N.DampingCurveData);
	CurveFrom(C.StiffnessCurve, N.StiffnessCurveData);
	CurveFrom(C.WorldDampingLocationCurve, N.WorldDampingLocationCurveData);
	CurveFrom(C.WorldDampingRotationCurve, N.WorldDampingRotationCurveData);
	CurveFrom(C.RadiusCurve, N.RadiusCurveData);
	CurveFrom(C.LimitAngleCurve, N.LimitAngleCurveData);
	N.DummyBoneLength = C.DummyBoneLength;
	N.BoneForwardAxis = static_cast<EBoneForwardAxis>(C.BoneForwardAxis);
	N.BoneSubdivisionCount = C.BoneSubdivisionCount;
	N.bBoneSubdivisionCollisionOnly = C.BoneSubdivisionCollisionOnly;
	N.bBoneSubdivisionDensifyByRadius = C.BoneSubdivisionDensifyByRadius;
	N.PlanarConstraint = static_cast<EPlanarConstraint>(C.PlanarConstraint);
	N.SimulationSpace = static_cast<EKawaiiPhysicsSimulationSpace>(C.SimulationSpace);
	N.SimulationBaseBone = BoneOf(C.SimulationBaseBone);
	N.TargetFramerate = C.TargetFramerate;
	N.bUseFixedSubstepping = C.UseFixedSubstepping;
	N.MaxSubsteps = C.MaxSubsteps;
	N.bNeedWarmUp = C.NeedWarmUp;
	N.WarmUpFrames = C.WarmUpFrames;
	N.bUseWarmUpWhenResetDynamics = C.UseWarmUpWhenResetDynamics;
	N.TeleportDistanceThreshold = C.TeleportDistanceThreshold;
	N.TeleportRotationThreshold = C.TeleportRotationThreshold;
	N.SkelCompMoveScale = FVector(C.SkelCompMoveScale[0], C.SkelCompMoveScale[1], C.SkelCompMoveScale[2]);
	// shapes: the node's own (an exported node's data asset shapes are in its lists already)
	N.LimitsDataAsset = nullptr;
	N.SphericalLimitsData.Reset();
	N.CapsuleLimitsData.Reset();
	N.TaperedCapsuleLimitsData.Reset();
	N.BoxLimitsData.Reset();
	N.PlanarLimitsData.Reset();
	N.SphericalLimits.Reset();
	for (const SkelCompat::KawaiiLimit& K : C.Spheres)
	{
		FSphericalLimit L;
		LimitFrom(K, L);
		L.Radius = K.Radius;
		L.LimitType = K.Inner ? ESphericalLimitType::Inner : ESphericalLimitType::Outer;
		N.SphericalLimits.Add(L);
	}
	N.CapsuleLimits.Reset();
	for (const SkelCompat::KawaiiLimit& K : C.Capsules)
	{
		FCapsuleLimit L;
		LimitFrom(K, L);
		L.Radius = K.Radius;
		L.Length = K.Length;
		N.CapsuleLimits.Add(L);
	}
	N.TaperedCapsuleLimits.Reset();
	for (const SkelCompat::KawaiiLimit& K : C.TaperedCapsules)
	{
		FTaperedCapsuleLimit L;
		LimitFrom(K, L);
		L.Radius0 = K.Radius0;
		L.Radius1 = K.Radius1;
		L.Length = K.Length;
		N.TaperedCapsuleLimits.Add(L);
	}
	N.BoxLimits.Reset();
	for (const SkelCompat::KawaiiLimit& K : C.Boxes)
	{
		FBoxLimit L;
		LimitFrom(K, L);
		L.Extent = FVector(K.Extent[0], K.Extent[1], K.Extent[2]);
		N.BoxLimits.Add(L);
	}
	N.PlanarLimits.Reset();
	for (const SkelCompat::KawaiiLimit& K : C.Planes)
	{
		FPlanarLimit L;
		LimitFrom(K, L);
		N.PlanarLimits.Add(L);
	}
	// bone constraints
	N.BoneConstraintGlobalComplianceType = static_cast<EXPBDComplianceType>(C.BoneConstraintGlobalCompliance);
	N.BoneConstraintIterationCountBeforeCollision = C.BoneConstraintIterationsBeforeCollision;
	N.BoneConstraintIterationCountAfterCollision = C.BoneConstraintIterationsAfterCollision;
	N.bAutoAddChildDummyBoneConstraint = C.AutoAddChildDummyBoneConstraint;
	N.BoneConstraintSubdivisionCount = C.BoneConstraintSubdivisionCount;
	N.BoneConstraintSubdivisionFeedbackScale = C.BoneConstraintSubdivisionFeedbackScale;
	N.BoneConstraints.Reset();
	for (const SkelCompat::KawaiiBoneConstraint& K : C.BoneConstraints)
	{
		FModifyBoneConstraint B;
		B.Bone1 = BoneOf(K.Bone1);
		B.Bone2 = BoneOf(K.Bone2);
		B.bOverrideCompliance = K.OverrideCompliance;
		B.ComplianceType = static_cast<EXPBDComplianceType>(K.Compliance);
		B.bExcludeFromSubdivision = K.ExcludeFromSubdivision;
		N.BoneConstraints.Add(B);
	}
	// forces
	N.Gravity = FVector(C.Gravity[0], C.Gravity[1], C.Gravity[2]);
	N.bUseLegacyGravity = C.UseLegacyGravity;
	N.bUseDefaultGravityZProjectSetting = C.UseDefaultGravityZ;
	N.bUseWorldSpaceGravity = C.UseWorldSpaceGravity;
	N.SimpleExternalForce = FVector(C.SimpleExternalForce[0], C.SimpleExternalForce[1], C.SimpleExternalForce[2]);
	N.bUseWorldSpaceSimpleExternalForce = C.UseWorldSpaceSimpleExternalForce;
	N.bSkipBonamikBones = C.SkipBonamikBones;
	// (1.9) Dynamic Motions
	N.PoseWaves.Reset();
	for (const SkelCompat::KawaiiWave& K : C.PoseWaves)
	{
		FKawaiiPoseWave W;
		W.Axis = FVector(K.Axis[0], K.Axis[1], K.Axis[2]);
		W.bLocalAxis = K.LocalAxis;
		W.Degrees = K.Degrees;
		W.Seconds = K.Seconds;
		W.Phase = K.Phase;
		W.PhasePerBone = K.PhasePerBone;
		W.PhasePerRoot = K.PhasePerRoot;
		for (const float Phase : K.RootPhases)
		{
			W.RootPhases.Add(Phase);
		}
		CurveFrom(K.DegreesCurve, W.DegreesCurve);
		N.PoseWaves.Add(MoveTemp(W));
	}
	N.PoseAnimation = FKawaiiPoseAnimation();
	N.PoseAnimation.Fps = C.PoseAnimation.Fps;
	N.PoseAnimation.Speed = C.PoseAnimation.Speed;
	N.PoseAnimation.Weight = C.PoseAnimation.Weight;
	N.PoseAnimation.bAdditive = C.PoseAnimation.Additive;
	if (C.PoseAnimation.Tracks)
	{
		for (const SkelCompat::KawaiiKeyTrack& K : *C.PoseAnimation.Tracks)
		{
			FKawaiiPoseKeyTrack Track;
			Track.Bone = BoneOf(K.Bone);
			Track.Keys.Reserve(int32(K.Keys.size()));
			for (const std::array<float, 4>& Q : K.Keys)
			{
				Track.Keys.Add(FQuat(Q[0], Q[1], Q[2], Q[3]));
			}
			N.PoseAnimation.Tracks.Add(MoveTemp(Track));
		}
	}
}

// A raw entry's models, as the game's parser keeps them (object paths)
TArray<FString> RawModels(const SkelCompat::Json& Entry)
{
	TArray<FString> Out;
	auto Add = [&Out](const SkelCompat::Json& Item)
	{
		if (Item.type == SkelCompat::Json::Type::String)
		{
			const std::wstring Path = SkelCompat::NormalizeObjectPath(SkelCompat::Widen(Item.string));
			Out.Add(Path.empty() ? FString(UTF8_TO_TCHAR(Item.string.c_str())) : TextOf(Path));
		}
	};
	for (const char* Key : {"models", "model"})
	{
		if (const SkelCompat::Json* Models = Entry.Find(Key))
		{
			if (Models->type == SkelCompat::Json::Type::Array)
			{
				for (const SkelCompat::Json& Item : Models->array)
				{
					Add(Item);
				}
			}
			else
			{
				Add(*Models);
			}
		}
	}
	return Out;
}

bool SameModels(const TArray<FString>& A, const TArray<FString>& B)
{
	if (A.Num() != B.Num())
	{
		return false;
	}
	for (int32 i = 0; i < A.Num(); ++i)
	{
		if (!A[i].Equals(B[i], ESearchCase::IgnoreCase))
		{
			return false;
		}
	}
	return true;
}
} // namespace

bool ReadKawaiiGameEntries(const FString& JsonText, TArray<FKawaiiPhysicsGameEntry>& OutEntries, FString& OutMessages)
{
	OutEntries.Reset();
	OutMessages.Reset();
	const FTCHARToUTF8 Utf8(*JsonText);
	const std::string Text(Utf8.Get(), Utf8.Length());
	SkelCompat::Json Root;
	std::string Error;
	if (!SkelCompat::ParseJson(Text, Root, Error))
	{
		OutMessages = FString(TEXT("not JSON: ")) + UTF8_TO_TCHAR(Error.c_str());
		return false;
	}
	SkelCompat::Config Config;
	if (!SkelCompat::AppendConfig(Text, L"import", Config))
	{
		OutMessages = TEXT("not a Create a Character System compat file");
		for (const std::wstring& Message : Config.Messages)
		{
			OutMessages += TEXT("\n") + TextOf(Message);
		}
		return false;
	}
	for (const std::wstring& Message : Config.Messages)
	{
		OutMessages += TextOf(Message) + TEXT("\n");
	}
	// the raw entries, for their names (the parser keeps no name): matched by their models
	TArray<const SkelCompat::Json*> Raw;
	if (const SkelCompat::Json* List = Root.Find("kawaii"))
	{
		if (List->type == SkelCompat::Json::Type::Array)
		{
			for (const SkelCompat::Json& Item : List->array)
			{
				Raw.Add(&Item);
			}
		}
	}
	TSet<int32> Named;
	for (const SkelCompat::KawaiiSet& Set : Config.Kawaii)
	{
		FKawaiiPhysicsGameEntry Entry;
		for (const std::wstring& Model : Set.Models)
		{
			Entry.Models.Add(TextOf(Model));
		}
		for (const std::wstring& Pak : Set.RequiresPaks)
		{
			Entry.RequiresPaks.Add(TextOf(Pak));
		}
		Entry.bDisableBonamik = Set.DisableBonamik;
		for (const std::wstring& Asset : Set.DisableBonamikAssets)
		{
			Entry.DisableBonamikAssets.Add(TextOf(Asset));
		}
		for (int32 k = 0; k < Raw.Num(); ++k)
		{
			if (Named.Contains(k) || !SameModels(RawModels(*Raw[k]), Entry.Models))
			{
				continue;
			}
			Named.Add(k);
			if (const SkelCompat::Json* Name = Raw[k]->Find("name"))
			{
				if (Name->type == SkelCompat::Json::Type::String)
				{
					Entry.Name = UTF8_TO_TCHAR(Name->string.c_str());
				}
			}
			break;
		}
		for (const SkelCompat::KawaiiNode& Node : Set.Nodes)
		{
			FAnimNode_KawaiiPhysics& Made = Entry.Nodes.AddDefaulted_GetRef();
			NodeFromConfig(Node, Made);
		}
		OutEntries.Add(MoveTemp(Entry));
	}
	if (OutEntries.Num() == 0)
	{
		OutMessages += TEXT("the file has no \"kawaii\" entries");
		return false;
	}
	return true;
}
