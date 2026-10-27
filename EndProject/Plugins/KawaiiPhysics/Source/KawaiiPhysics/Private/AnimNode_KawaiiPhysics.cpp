// Kawaii Dynamic Motions (KawaiiPhysics for UE 4.26 with the newest KawaiiPhysics' features, (1.9) its own motions,
// (1.10) KawaiiPhysics' sync bones, (1.11) the rest of KawaiiPhysics 1.21: external forces, wind, sets, physics asset
// and mirrored shapes, shared and world collision, the entry's animation triggers, and (1.12) the motions of animation
// sets (EndAnimSet) and solid floors): the node runs the game mod's simulation (KawaiiSolver.hpp, Create a Character
// System 3.20.0), so the End editor's preview moves the bones as the game will (the world's parts but the level's wind
// are the game's: the preview has none).
// KawaiiPhysics is pafuhana1213's (https://github.com/pafuhana1213/KawaiiPhysics), MIT License.
#include "AnimNode_KawaiiPhysics.h"

#include "KawaiiPhysics.h"
#include "KawaiiPhysicsLimitsDataAsset.h"
#include "AnimationRuntime.h"
#include "Animation/AnimClassInterface.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimNode_AssetPlayerBase.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSequenceDecompressionContext.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/Skeleton.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Engine/SkeletalMesh.h"
#include "Misc/Crc.h"
#include "PhysicsEngine/BodySetup.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "SceneInterface.h"

#include <atomic>
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
	uint64 NodeSerial = 0;                   // (1.12) which simulation Node is (a new one plays the sets' motion again)
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

// ---- (1.12) the motions of animation sets, as the preview plays them -------------------------------
struct FKawaiiAnimSetPreview
{
	// a motion made from an animation of the sets (the node's bones' tracks)
	struct FMade
	{
		TWeakObjectPtr<const UAnimSequence> Anim;
		FString Name;
		bool bReference = false;
		int32 Loop = -1;
		uint32 Bones = 0;
		std::shared_ptr<const Kawaii::Node::Motion> Motion;
		FString Why;
	};
	// the sets' animations by name (the first set with a name wins; null: in a set, not an animation the node plays)
	TArray<TPair<FName, TWeakObjectPtr<UAnimationAsset>>> Entries;
	FString SetsNote;
	// what the preview plays
	FString Playing, WasPlaying;
	float Time = -1.0f, WasTime = -1.0f;
	bool bBattle = false, bMoving = false;
	float Speed = 0.0f;
	FVector LastPosition = FVector::ZeroVector;
	double LastSeconds = -1.0;
	// the pick, played by the evaluation (a new Serial: from its start, cross-faded from the one before)
	FString Pick;
	bool bPicked = false;
	std::shared_ptr<const Kawaii::Node::Motion> Motion;
	uint32 Serial = 0;
	bool bSynced = false;
	bool bRestart = false;
	float SyncTime = -1.0f;
	FString Why;
	FString Text;
	TArray<FMade> Made;
	// (the evaluation's own: what it played last, on which simulation)
	uint32 PlayedSerial = 0;
	uint64 PlayedOn = 0;
};

FKawaiiAnimSetPreviewHolder::FKawaiiAnimSetPreviewHolder() = default;
FKawaiiAnimSetPreviewHolder::FKawaiiAnimSetPreviewHolder(const FKawaiiAnimSetPreviewHolder&) {}
FKawaiiAnimSetPreviewHolder& FKawaiiAnimSetPreviewHolder::operator=(const FKawaiiAnimSetPreviewHolder&)
{
	Reset();
	return *this;
}
FKawaiiAnimSetPreviewHolder::~FKawaiiAnimSetPreviewHolder() { Reset(); }
void FKawaiiAnimSetPreviewHolder::Reset(FKawaiiAnimSetPreview* InPreview)
{
	if (Preview != InPreview)
	{
		delete Preview;
		Preview = InPreview;
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

// (1.10) A curve whose times are not 0 - 1 (a sync bone's scale by its move's length, cm): its keys as they are when linear,
// else sampled over its keys' times
void CurveOfRange(const FRuntimeFloatCurve& Curve, SkelCompat::KawaiiCurve& Out, float MaxTime)
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
			const float Time = FMath::Clamp(It->Time, 0.0f, MaxTime);
			if (Time > Last)
			{
				Out.Keys.push_back({Time, FMath::Clamp(It->Value, -1.0e4f, 1.0e4f)});
				Last = Time;
			}
		}
		return;
	}
	float First = 0.0f, Final = 1.0f;
	Rich->GetTimeRange(First, Final);
	First = FMath::Clamp(First, 0.0f, MaxTime);
	Final = FMath::Clamp(Final, First, MaxTime);
	if (Final <= First)
	{
		Out.Keys.push_back({First, FMath::Clamp(Rich->Eval(First), -1.0e4f, 1.0e4f)});
		return;
	}
	for (int32 i = 0; i <= 32; ++i)
	{
		const float Time = First + (Final - First) * float(i) / 32.0f;
		Out.Keys.push_back({Time, FMath::Clamp(Rich->Eval(Time), -1.0e4f, 1.0e4f)});
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

// (1.11) A gameplay tag's name as the game's parser takes it (else empty)
std::wstring TagOf(const FString& Text)
{
	const FString Trimmed = Text.TrimStartAndEnd();
	const std::wstring Tag(*Trimmed);
	return SkelCompat::Detail::IsTagName(Tag) ? Tag : std::wstring();
}

// (1.11) An external force as the game's, within its parser's limits
void ForceOf(const FKawaiiPhysicsExternalForce& F, SkelCompat::KawaiiExternalForce& K)
{
	K = SkelCompat::KawaiiExternalForce();
	K.Type = static_cast<SkelCompat::KawaiiForceType>(F.Type);   // (Basic, Gravity, Curve, Wind, ProceduralWind: the same order)
	K.Enabled = F.bIsEnabled;
	for (const FBoneReference& Bone : F.ApplyBoneFilter)
	{
		if (!Bone.BoneName.IsNone()) { K.ApplyBoneFilter.push_back(Wide(Bone.BoneName)); }
	}
	for (const FBoneReference& Bone : F.IgnoreBoneFilter)
	{
		if (!Bone.BoneName.IsNone()) { K.IgnoreBoneFilter.push_back(Wide(Bone.BoneName)); }
	}
	switch (F.ExternalForceSpace)
	{
	case EKawaiiPhysicsExternalForceSpace::ComponentSpace: K.Space = SkelCompat::KawaiiForceSpace::Component; break;
	case EKawaiiPhysicsExternalForceSpace::BoneSpace: K.Space = SkelCompat::KawaiiForceSpace::Bone; break;
	default: K.Space = SkelCompat::KawaiiForceSpace::World; break;
	}
	if (K.Type == SkelCompat::KawaiiForceType::Gravity || K.Type == SkelCompat::KawaiiForceType::Wind) { K.Space = SkelCompat::KawaiiForceSpace::World; }
	const float Low = FMath::Clamp(FMath::Min(F.RandomForceScaleRange.Min, F.RandomForceScaleRange.Max), -1.0e6f, 1.0e6f);
	const float High = FMath::Clamp(FMath::Max(F.RandomForceScaleRange.Min, F.RandomForceScaleRange.Max), -1.0e6f, 1.0e6f);
	K.RandomForceScaleRange[0] = Low;
	K.RandomForceScaleRange[1] = High;
	CurveOf(F.ForceRateByBoneLengthRate, K.ForceRateByBoneLengthRate);
	K.ForceDir[0] = FMath::Clamp(F.ForceDir.X, -1.0e7f, 1.0e7f);
	K.ForceDir[1] = FMath::Clamp(F.ForceDir.Y, -1.0e7f, 1.0e7f);
	K.ForceDir[2] = FMath::Clamp(F.ForceDir.Z, -1.0e7f, 1.0e7f);
	K.Interval = FMath::Clamp(F.Interval, 0.0f, 1.0e5f);
	K.UseCharacterGravityDirection = F.bUseCharacterGravityDirection;
	K.UseCharacterGravityScale = F.bUseCharacterGravityScale;
	K.UseOverrideGravityDirection = F.bUseOverrideGravityDirection;
	K.OverrideGravityDirection[0] = FMath::Clamp(F.OverrideGravityDirection.X, -1.0e6f, 1.0e6f);
	K.OverrideGravityDirection[1] = FMath::Clamp(F.OverrideGravityDirection.Y, -1.0e6f, 1.0e6f);
	K.OverrideGravityDirection[2] = FMath::Clamp(F.OverrideGravityDirection.Z, -1.0e6f, 1.0e6f);
	// (the curve's keys in time order, each later than the one before, as the parser takes them)
	TArray<FKawaiiPhysicsVectorKey> Keys = F.ForceCurve;
	Keys.StableSort([](const FKawaiiPhysicsVectorKey& A, const FKawaiiPhysicsVectorKey& B) { return A.Time < B.Time; });
	for (const FKawaiiPhysicsVectorKey& Key : Keys)
	{
		if (K.ForceCurve.Keys.size() >= SkelCompat::MaxKawaiiCurveKeys) { break; }
		const float Time = FMath::Clamp(Key.Time, 0.0f, 1.0e4f);
		if (!K.ForceCurve.Keys.empty() && Time <= K.ForceCurve.Keys.back()[0]) { continue; }
		K.ForceCurve.Keys.push_back({Time, FMath::Clamp(Key.Value.X, -1.0e6f, 1.0e6f), FMath::Clamp(Key.Value.Y, -1.0e6f, 1.0e6f), FMath::Clamp(Key.Value.Z, -1.0e6f, 1.0e6f)});
	}
	K.CurveEvaluateType = static_cast<SkelCompat::KawaiiCurveEvaluate>(F.CurveEvaluateType);   // (Single, Average, Max, Min)
	K.SubstepCount = FMath::Clamp(F.SubstepCount, 1, 1000);
	K.TimeScale = FMath::Clamp(F.TimeScale, 0.0f, 1.0e3f);
	K.WindDirectionNoiseAngle = FMath::Clamp(F.WindDirectionNoiseAngle, 0.0f, 180.0f);
	K.WindSource = static_cast<SkelCompat::KawaiiWindSource>(F.WindSource);   // (Local, Shared, Auto)
	const std::wstring Tag = TagOf(F.SharedWindTag);
	if (!Tag.empty()) { K.SharedWindTag = Tag; }
	K.WindDirection[0] = FMath::Clamp(F.WindDirection.X, -1.0e6f, 1.0e6f);
	K.WindDirection[1] = FMath::Clamp(F.WindDirection.Y, -1.0e6f, 1.0e6f);
	K.WindDirection[2] = FMath::Clamp(F.WindDirection.Z, -1.0e6f, 1.0e6f);
	K.WindDirectionNoisePeriod = FMath::Clamp(F.WindDirectionNoisePeriod, 0.01f, 1.0e4f);
	K.ConstantForce = FMath::Clamp(F.ConstantForce, 0.0f, 1.0e6f);
	K.SwayForce = FMath::Clamp(F.SwayForce, 0.0f, 1.0e6f);
	K.SwayPeriod = FMath::Clamp(F.SwayPeriod, 0.01f, 1.0e4f);
	K.SwayPhaseOffset = FMath::Clamp(F.SwayPhaseOffset, -1.0e5f, 1.0e5f);
	K.RippleForce = FMath::Clamp(F.RippleForce, 0.0f, 1.0e6f);
	K.RipplePeriod = FMath::Clamp(F.RipplePeriod, 0.01f, 1.0e4f);
	K.RipplePhaseOffset = FMath::Clamp(F.RipplePhaseOffset, -1.0e5f, 1.0e5f);
	K.RippleTipPhaseDelay = FMath::Clamp(F.RippleTipPhaseDelay, -1.0e5f, 1.0e5f);
	K.StrengthCycleRange[0] = FMath::Clamp(FMath::Min(F.StrengthCycleRange.Min, F.StrengthCycleRange.Max), 0.0f, 1.0e4f);
	K.StrengthCycleRange[1] = FMath::Clamp(FMath::Max(F.StrengthCycleRange.Min, F.StrengthCycleRange.Max), 0.0f, 1.0e4f);
	K.StrengthCyclePeriod = FMath::Clamp(F.StrengthCyclePeriod, 0.01f, 1.0e5f);
	K.StrengthCyclePhaseOffset = FMath::Clamp(F.StrengthCyclePhaseOffset, -1.0e5f, 1.0e5f);
	K.RandomForce = FMath::Clamp(F.RandomForce, 0.0f, 1.0e6f);
	K.RandomForcePeriod = FMath::Clamp(F.RandomForcePeriod, 0.01f, 1.0e4f);
	K.Seed = F.Seed;
}

// (1.11) The node's mirroring as the game's (no pairs or name parts given: the game's own L_ / R_ and _L / _R)
void MirrorOf(const FKawaiiPhysicsMirrorLimits& M, SkelCompat::KawaiiMirror& K)
{
	K = SkelCompat::KawaiiMirror();
	switch (M.MirrorAxis)
	{
	case EKawaiiPhysicsMirrorAxis::X: K.Axis = SkelCompat::KawaiiMirrorAxis::X; break;
	case EKawaiiPhysicsMirrorAxis::Y: K.Axis = SkelCompat::KawaiiMirrorAxis::Y; break;
	case EKawaiiPhysicsMirrorAxis::Z: K.Axis = SkelCompat::KawaiiMirrorAxis::Z; break;
	default: return;
	}
	for (const FKawaiiPhysicsMirrorBonePair& Pair : M.BonePairs)
	{
		if (!Pair.Left.IsNone() && !Pair.Right.IsNone()) { K.Pairs.emplace_back(Wide(Pair.Left), Wide(Pair.Right)); }
	}
	for (const FKawaiiPhysicsMirrorNamePart& Part : M.Prefixes)
	{
		if (!Part.Left.IsEmpty() && !Part.Right.IsEmpty()) { K.Prefixes.emplace_back(std::wstring(*Part.Left), std::wstring(*Part.Right)); }
	}
	for (const FKawaiiPhysicsMirrorNamePart& Part : M.Suffixes)
	{
		if (!Part.Left.IsEmpty() && !Part.Right.IsEmpty()) { K.Suffixes.emplace_back(std::wstring(*Part.Left), std::wstring(*Part.Right)); }
	}
	if (K.Pairs.empty() && K.Prefixes.empty() && K.Suffixes.empty())
	{
		K.Prefixes = {{L"L_", L"R_"}};
		K.Suffixes = {{L"_L", L"_R"}};
	}
	K.SkipExisting = M.bSkipMirroredBoneWithExistingCollision;
}

// (1.11) KawaiiPhysics' ApplyPhysicsAsset for the preview: the bodies of a physics asset (the preview mesh's own, or the
// node's) as shapes on their bones (a bone the mesh lacks: left out), in the node's Data* lists, as the game puts them
void PhysicsShapesOf(const UPhysicsAsset* Asset, const FReferenceSkeleton& Ref, SkelCompat::KawaiiNode& C)
{
	C.DataSpheres.clear();
	C.DataCapsules.clear();
	C.DataTaperedCapsules.clear();
	C.DataBoxes.clear();
	if (!Asset || !C.PhysicsAssetForLimits) { return; }
	for (const USkeletalBodySetup* Body : Asset->SkeletalBodySetups)
	{
		if (!Body || Body->BoneName.IsNone() || Ref.FindBoneIndex(Body->BoneName) == INDEX_NONE) { continue; }
		const std::wstring Bone = Wide(Body->BoneName);
		const FKAggregateGeom& Geom = Body->AggGeom;
		const auto Place = [&Bone](const FVector& Center, const FRotator& Rotation, SkelCompat::KawaiiLimit& L) {
			L.Bone = Bone;
			Triple(Center, L.Offset);
			L.Rotation[0] = Rotation.Pitch;
			L.Rotation[1] = Rotation.Yaw;
			L.Rotation[2] = Rotation.Roll;
		};
		for (const FKSphereElem& E : Geom.SphereElems)
		{
			SkelCompat::KawaiiLimit L;
			Place(E.Center, FRotator::ZeroRotator, L);
			L.Radius = E.Radius;
			C.DataSpheres.push_back(L);
		}
		for (const FKSphylElem& E : Geom.SphylElems)
		{
			SkelCompat::KawaiiLimit L;
			Place(E.Center, E.Rotation, L);
			L.Radius = E.Radius;
			L.Length = E.Length;
			C.DataCapsules.push_back(L);
		}
		for (const FKTaperedCapsuleElem& E : Geom.TaperedCapsuleElems)
		{
			SkelCompat::KawaiiLimit L;
			Place(E.Center, E.Rotation, L);
			L.Radius0 = E.Radius0;
			L.Radius1 = E.Radius1;
			L.Length = E.Length;
			C.DataTaperedCapsules.push_back(L);
		}
		for (const FKBoxElem& E : Geom.BoxElems)
		{
			SkelCompat::KawaiiLimit L;
			Place(E.Center, E.Rotation, L);
			L.Extent[0] = E.X * 0.5f;
			L.Extent[1] = E.Y * 0.5f;
			L.Extent[2] = E.Z * 0.5f;
			C.DataBoxes.push_back(L);
		}
	}
}

// The node's settings as the game mod's node (the same structure its JSON makes). bTracks false: the key animation's
// settings without its tracks (the editor's check of an edit; it puts them in when something changed). bGame: (1.11) its
// alpha as the game's "alpha" (the editor's own node blends by its alpha itself: the preview's simulation runs at 1)
// (1.12) The animation sets' settings as the game's "pose_animset", within its parser's limits (the sets' paths as the game
// loads them; pairs and names the parser would refuse left out)
void AnimSetOf(const FKawaiiPoseAnimSet& A, SkelCompat::KawaiiPoseAnimSet& K)
{
	K = SkelCompat::KawaiiPoseAnimSet();
	for (const TSoftObjectPtr<UObject>& Set : A.Sets)
	{
		if (K.Sets.size() >= SkelCompat::MaxKawaiiAnimSets) { break; }
		const std::wstring Path = SkelCompat::NormalizeObjectPath(std::wstring(*Set.ToSoftObjectPath().ToString()));
		if (!Path.empty() && Path[0] == L'/') { SkelCompat::Detail::AddUniqueName(K.Sets, Path); }
	}
	const auto Name = [](const FString& Text) {
		const FString Trimmed = Text.TrimStartAndEnd();
		const std::wstring Wide(*Trimmed);
		return SkelCompat::Detail::IsPlainName(Wide) ? Wide : std::wstring();
	};
	for (const FKawaiiPoseAnimSetMotion& M : A.Motions)
	{
		if (K.Motions.size() >= SkelCompat::MaxKawaiiMotionPairs) { break; }
		const FString From = M.Playing.TrimStartAndEnd();
		const FString To = M.Motion.TrimStartAndEnd();
		if (From.IsEmpty() || From.Len() > 128 || (!To.IsEmpty() && Name(To).empty())) { continue; }
		SkelCompat::KawaiiMotionPair Pair;
		Pair.From = std::wstring(*From);
		Pair.To = To.IsEmpty() ? std::wstring() : std::wstring(*To);
		K.Motions.push_back(std::move(Pair));
	}
	K.SameNames = A.bSameNames;
	K.Idle = Name(A.Idle);
	K.BattleIdle = Name(A.BattleIdle);
	K.Moving = Name(A.Moving);
	K.BattleMoving = Name(A.BattleMoving);
	K.MovingSpeed = FMath::Clamp(A.MovingSpeed, 0.0f, 10000.0f);
	K.BlendSeconds = FMath::Clamp(A.BlendSeconds, 0.0f, 5.0f);
	K.Speed = FMath::Clamp(A.Speed, -100.0f, 100.0f);
	K.Weight = FMath::Clamp(A.Weight, 0.0f, 1.0f);
	K.Additive = A.bAdditive;
	K.FromReference = A.AdditiveBase == EKawaiiPoseAnimSetBase::ReferencePose;
	K.Loop = A.Loop == EKawaiiPoseAnimSetLoop::Auto ? -1 : (A.Loop == EKawaiiPoseAnimSetLoop::Loop ? 1 : 0);
	K.Sync = A.bSync;
	K.Preview = Name(A.PreviewMotion);
}

void ConfigOf(const FAnimNode_KawaiiPhysics& N, SkelCompat::KawaiiNode& C, bool bTracks = true, bool bGame = false)
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
	C.InterpolateLimitsInSubsteps = N.bInterpolateLimitsInSubsteps;   // (1.10)
	C.KeepCollisionSide = N.bKeepCollisionSide;
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
			K.OneSided = L.bOneSided;   // (1.12: a solid floor)
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
	// (1.10) sync bones, within the game's parser's limits
	for (const FKawaiiPhysicsSyncBone& B : N.SyncBones)
	{
		if (C.SyncBones.size() >= SkelCompat::MaxKawaiiSyncBones) { break; }
		if (B.Bone.BoneName.IsNone()) { continue; }
		SkelCompat::KawaiiSyncBone K;
		K.Bone = Wide(B.Bone.BoneName);
		for (const FKawaiiPhysicsSyncTargetRoot& T : B.TargetRoots)
		{
			if (T.Bone.BoneName.IsNone() || K.Targets.size() >= SkelCompat::MaxKawaiiSyncTargets) { continue; }
			SkelCompat::KawaiiSyncTarget Target;
			Target.Bone = Wide(T.Bone.BoneName);
			Target.IncludeChildBones = T.bIncludeChildBones;
			CurveOf(T.ScaleCurveByBoneLengthRate, Target.ScaleCurve);
			K.Targets.push_back(Target);
		}
		if (K.Targets.empty()) { continue; }   // (the game's parser leaves out a sync bone without targets)
		K.GlobalScale[0] = FMath::Clamp(B.GlobalScale.X, 0.0f, 1.0f);
		K.GlobalScale[1] = FMath::Clamp(B.GlobalScale.Y, 0.0f, 1.0f);
		K.GlobalScale[2] = FMath::Clamp(B.GlobalScale.Z, 0.0f, 1.0f);
		CurveOfRange(B.ScaleCurveByDeltaDistance, K.ScaleCurveByDeltaDistance, 1.0e4f);
		K.Direction[0] = static_cast<SkelCompat::KawaiiSyncDirection>(B.ApplyDirectionX);
		K.Direction[1] = static_cast<SkelCompat::KawaiiSyncDirection>(B.ApplyDirectionY);
		K.Direction[2] = static_cast<SkelCompat::KawaiiSyncDirection>(B.ApplyDirectionZ);
		K.DistanceAttenuation = B.bEnableDistanceAttenuation;
		K.AttenuationInnerRadius = FMath::Clamp(B.AttenuationInnerRadius, 0.0f, 1.0e5f);
		K.AttenuationOuterRadius = FMath::Clamp(B.AttenuationOuterRadius, 0.0f, 1.0e5f);
		K.MaxAttenuationRate = FMath::Clamp(B.MaxAttenuationRate, 0.0f, 1.0f);
		C.SyncBones.push_back(K);
	}
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
	AnimSetOf(N.PoseAnimSet, C.PoseAnimSet);   // (1.12)
	// (1.11) the rest of KawaiiPhysics 1.21, within the game's parser's limits
	C.EnableWind = N.bEnableWind;
	C.WindScale = FMath::Clamp(N.WindScale, -1.0e4f, 1.0e4f);
	C.WindDirectionNoiseAngle = FMath::Clamp(N.WindDirectionNoiseAngle, 0.0f, 180.0f);
	for (const FKawaiiPhysicsExternalForce& F : N.ExternalForces)
	{
		if (C.ExternalForces.size() >= SkelCompat::MaxKawaiiExternalForces) { break; }
		SkelCompat::KawaiiExternalForce K;
		ForceOf(F, K);
		C.ExternalForces.push_back(std::move(K));
	}
	if (bGame)
	{
		// (the base node's alpha as it is set: a float through its scale and bias, a bool on or off; a curve's: 1)
		float Alpha = 1.0f;
		if (N.AlphaInputType == EAnimAlphaInputType::Float) { Alpha = N.AlphaScaleBias.ApplyTo(N.Alpha); }
		else if (N.AlphaInputType == EAnimAlphaInputType::Bool) { Alpha = N.bAlphaBoolEnabled ? 1.0f : 0.0f; }
		C.Alpha = FMath::Clamp(Alpha, 0.0f, 1.0f);
	}
	C.Tag = TagOf(N.KawaiiPhysicsTag);
	for (const FString& Name : N.GameLimitsSets)
	{
		const std::wstring Set = TagOf(Name);
		if (!Set.empty()) { SkelCompat::Detail::AddUniqueName(C.LimitsSets, Set); }
	}
	for (const FString& Name : N.GameBoneConstraintsSets)
	{
		const std::wstring Set = TagOf(Name);
		if (!Set.empty()) { SkelCompat::Detail::AddUniqueName(C.BoneConstraintsSets, Set); }
	}
	if (N.bUseModelPhysicsAssetForLimits) { C.PhysicsAssetForLimits = true; }
	else if (!N.PhysicsAssetForLimits.IsNull())
	{
		C.PhysicsAssetPath = SkelCompat::NormalizeObjectPath(std::wstring(*N.PhysicsAssetForLimits.ToSoftObjectPath().ToString()));
		C.PhysicsAssetForLimits = !C.PhysicsAssetPath.empty();
	}
	MirrorOf(N.MirrorLimits, C.MirrorLimits);
	C.SharedCollisionSource = N.bSharedCollisionSource;
	C.UseSharedCollision = N.bUseSharedCollision;
	const std::wstring Group = TagOf(N.SharedCollisionGroupTag);
	if (!Group.empty()) { C.SharedCollisionGroupTag = Group; }
	C.World.AllowWorldCollision = N.bAllowWorldCollision;
	C.World.IgnoreSelfComponent = N.bIgnoreSelfComponent;
	C.World.MaxSweepsPerFrame = FMath::Clamp(N.WorldCollisionMaxSweepsPerFrame, 0, 4096);
	C.World.UseSimpleWorldCollision = N.bUseSimpleWorldCollision;
	C.World.GatherInterval = FMath::Clamp(N.SimpleWorldCollisionGatherInterval, 0.0f, 60.0f);
	C.World.OverrideGatherRadius = N.bOverrideSimpleWorldCollisionGatherRadius;
	C.World.GatherRadius = FMath::Clamp(N.SimpleWorldCollisionGatherRadius, 1.0f, 1.0e5f);
	C.World.GroundCollision = N.bSimpleWorldCollisionGroundCollision;
	C.World.GroundOnly = N.bGroundCollision;
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
	K.PoseAnimSet = D.PoseAnimSet;           // (1.12: nor the sets' motions)
	K.SyncBones.clear();                     // (1.10: nor the sync bones, nor the shapes' handling)
	K.InterpolateLimitsInSubsteps = D.InterpolateLimitsInSubsteps;
	K.KeepCollisionSide = D.KeepCollisionSide;
	// (1.11: forces, wind, alpha, tag, shapes from sets, physics asset and mirroring, shared and world collision are not
	// what the chains are made from; the bone constraints' sets are)
	K.EnableWind = D.EnableWind;
	K.WindScale = D.WindScale;
	K.WindDirectionNoiseAngle = D.WindDirectionNoiseAngle;
	K.ExternalForces.clear();
	K.Alpha = D.Alpha;
	K.Tag = D.Tag;
	K.LimitsSets.clear();
	K.PhysicsAssetForLimits = D.PhysicsAssetForLimits;
	K.PhysicsAssetPath = D.PhysicsAssetPath;
	K.MirrorLimits = D.MirrorLimits;
	K.SharedCollisionSource = D.SharedCollisionSource;
	K.UseSharedCollision = D.UseSharedCollision;
	K.SharedCollisionGroupTag = D.SharedCollisionGroupTag;
	K.World = D.World;
	K.DataSpheres.clear();
	K.DataCapsules.clear();
	K.DataTaperedCapsules.clear();
	K.DataBoxes.clear();
	K.DataPlanes.clear();
	return K;
}
} // namespace

// ---- (1.12) the motions of animation sets in the preview (the game thread) ---------------------------
namespace
{
std::atomic<uint64> NodeSerials{0};

// The node's bones on the model: its root bones and every bone below them (the bones a motion's tracks are kept for)
TSet<FName> NodeBoneNames(const FAnimNode_KawaiiPhysics& N, const FReferenceSkeleton& Ref)
{
	TArray<uint8> Mark;
	Mark.SetNumZeroed(Ref.GetNum());
	const auto Root = [&](const FName& Bone) {
		const int32 Index = Bone.IsNone() ? INDEX_NONE : Ref.FindBoneIndex(Bone);
		if (Index != INDEX_NONE) { Mark[Index] = 1; }
	};
	Root(N.RootBone.BoneName);
	for (const FKawaiiPhysicsRootBoneSetting& Extra : N.AdditionalRootBones) { Root(Extra.RootBone.BoneName); }
	TSet<FName> Out;
	for (int32 i = 0; i < Ref.GetNum(); ++i)
	{
		const int32 Parent = Ref.GetParentIndex(i);
		if (Parent >= 0 && Parent < i && Mark[Parent]) { Mark[i] = 1; }
		if (Mark[i]) { Out.Add(Ref.GetBoneName(i)); }
	}
	return Out;
}

// The sets' animations by name, as the game reads an EndAnimSet's AnimationAssets (the first set with a name wins; a set
// not in this project is looked for again every two seconds)
void ReadAnimSets(const FKawaiiPoseAnimSet& A, FKawaiiAnimSetPreview& P, double Now, double& NextLoad)
{
	P.Entries.Reset();
	P.SetsNote.Reset();
	TSet<FName> Seen;
	int32 Count = 0;
	for (const TSoftObjectPtr<UObject>& Ptr : A.Sets)
	{
		if (Ptr.IsNull() || ++Count > int32(SkelCompat::MaxKawaiiAnimSets)) { continue; }
		UObject* Set = Ptr.Get();
		if (!Set && Now >= NextLoad)
		{
			Set = Ptr.LoadSynchronous();
			if (!Set) { NextLoad = Now + 2.0; }
		}
		FMapProperty* Map = Set ? FindFProperty<FMapProperty>(Set->GetClass(), TEXT("AnimationAssets")) : nullptr;
		FObjectPropertyBase* Value = Map ? CastField<FObjectPropertyBase>(Map->ValueProp) : nullptr;
		if (!Map || !Value || !CastField<FNameProperty>(Map->KeyProp))
		{
			P.SetsNote += (P.SetsNote.IsEmpty() ? TEXT("") : TEXT(", ")) + Ptr.ToSoftObjectPath().GetAssetName() +
				(Set ? TEXT(" is not an EndAnimSet") : TEXT(" is not in this project"));
			continue;
		}
		FScriptMapHelper Helper(Map, Map->ContainerPtrToValuePtr<void>(Set));
		for (int32 Index = 0; Index < Helper.GetMaxIndex(); ++Index)
		{
			if (!Helper.IsValidIndex(Index)) { continue; }
			const FName Key = *reinterpret_cast<const FName*>(Helper.GetKeyPtr(Index));
			if (Key.IsNone() || Seen.Contains(Key)) { continue; }   // (FName: case aside, as the game's names)
			Seen.Add(Key);
			P.Entries.Emplace(Key, Cast<UAnimationAsset>(Value->GetObjectPropertyValue(Helper.GetValuePtr(Index))));
		}
	}
}

// What the preview plays, as the game's "what the character plays": a montage the mesh plays, else the animation editor's
// animation, else the AnimBlueprint's animation player of the most weight; its time in it (-1: not known)
void WhatThePreviewPlays(const UAnimInstance* InAnimInstance, FString& OutName, float& OutTime)
{
	OutName.Reset();
	OutTime = -1.0f;
	USkeletalMeshComponent* Mesh = InAnimInstance ? InAnimInstance->GetSkelMeshComponent() : nullptr;
	UAnimInstance* Main = Mesh ? Mesh->GetAnimInstance() : nullptr;
	if (!Main) { Main = const_cast<UAnimInstance*>(InAnimInstance); }
	if (!Main) { return; }
	if (FAnimMontageInstance* Montage = Main->GetActiveMontageInstance())
	{
		if (Montage->Montage)
		{
			OutName = Montage->Montage->GetName();
			OutTime = Montage->GetPosition();
			return;
		}
	}
	if (UAnimSingleNodeInstance* Single = Cast<UAnimSingleNodeInstance>(Main))
	{
		if (UAnimationAsset* Asset = Single->GetCurrentAsset())
		{
			OutName = Asset->GetName();
			OutTime = Single->GetCurrentTime();
		}
		return;
	}
	const IAnimClassInterface* Class = IAnimClassInterface::GetFromClass(Main->GetClass());
	if (!Class) { return; }
	float Best = 0.0f;
	for (FStructProperty* Property : Class->GetAnimNodeProperties())
	{
		if (!Property || !Property->Struct || !Property->Struct->IsChildOf(FAnimNode_AssetPlayerBase::StaticStruct())) { continue; }
		FAnimNode_AssetPlayerBase* Player = Property->ContainerPtrToValuePtr<FAnimNode_AssetPlayerBase>(Main);
		UAnimationAsset* Asset = Player ? Player->GetAnimAsset() : nullptr;
		const float Weight = Player ? Player->GetCachedBlendWeight() : 0.0f;
		if (Asset && Weight > Best)
		{
			Best = Weight;
			OutName = Asset->GetName();
			OutTime = Player->GetAccumulatedTime();
		}
	}
}

// An animation of the sets as the node plays it, as the game decodes it: its tracks of the node's bones (each bone's local
// rotation a frame, from its compressed data as the game evaluates it), the bases its skeleton's reference pose for
// "reference_pose"
std::shared_ptr<const Kawaii::Node::Motion> MotionOfSequence(const UAnimSequence* Seq, const TSet<FName>& Bones, const SkelCompat::KawaiiPoseAnimSet& Cfg,
	const FString& Name, FString& Why)
{
	if (Seq->AdditiveAnimType != AAT_None)
	{
		Why = TEXT("an additive animation (not a pose)");
		return nullptr;
	}
	const USkeleton* Skeleton = Seq->GetSkeleton();
	if (!Skeleton)
	{
		Why = TEXT("it has no skeleton");
		return nullptr;
	}
	const FReferenceSkeleton& Ref = Skeleton->GetReferenceSkeleton();
	const bool bCompressed = Seq->IsCompressedDataValid() && Seq->CompressedData.CompressedDataStructure.IsValid() && Seq->CompressedData.BoneCompressionCodec != nullptr;
	const bool bRaw = !bCompressed && Seq->GetRawAnimationData().Num() > 0;
	if (!bCompressed && !bRaw)
	{
		Why = TEXT("it has no animation data yet");
		return nullptr;
	}
	const TArray<FTrackToSkeletonMap>& Map = bCompressed ? Seq->GetCompressedTrackToSkeletonMapTable() : Seq->GetRawTrackToSkeletonMapTable();
	TArray<int32> TrackIndex, TrackBone;
	for (int32 T = 0; T < Map.Num(); ++T)
	{
		const int32 Bone = Map[T].BoneTreeIndex;
		if (Bone >= 0 && Bone < Ref.GetNum() && Bones.Contains(Ref.GetBoneName(Bone)))
		{
			TrackIndex.Add(T);
			TrackBone.Add(Bone);
		}
	}
	if (TrackIndex.Num() == 0)
	{
		Why = TEXT("it moves none of the node's bones");
		return nullptr;
	}
	const int32 Frames = FMath::Clamp(Seq->GetRawNumberOfFrames(), 1, 20000);
	const float Length = Seq->SequenceLength;
	const float Fps = (Frames > 1 && Length > KINDA_SMALL_NUMBER) ? float(Frames - 1) / Length : 30.0f;
	std::vector<SkelCompat::KawaiiKeyTrack> Tracks(size_t(TrackIndex.Num()));
	std::vector<std::array<float, 4>> Bases(size_t(TrackIndex.Num()));
	const TArray<FTransform>& RefPose = Ref.GetRefBonePose();
	for (int32 k = 0; k < TrackIndex.Num(); ++k)
	{
		Tracks[size_t(k)].Bone = Wide(Ref.GetBoneName(TrackBone[k]));
		Tracks[size_t(k)].Keys.reserve(size_t(Frames));
		const FQuat Base = RefPose.IsValidIndex(TrackBone[k]) ? RefPose[TrackBone[k]].GetRotation() : FQuat::Identity;
		Bases[size_t(k)] = {Base.X, Base.Y, Base.Z, Base.W};
	}
	const auto Add = [&](int32 k, const FTransform& Atom) {
		const FQuat Q = Atom.GetRotation();
		Tracks[size_t(k)].Keys.push_back({Q.X, Q.Y, Q.Z, Q.W});
	};
	if (bCompressed)
	{
		FAnimSequenceDecompressionContext Context(Seq->SequenceLength, Seq->Interpolation, Seq->GetFName(), *Seq->CompressedData.CompressedDataStructure);
		for (int32 F = 0; F < Frames; ++F)
		{
			Context.Seek(FMath::Min(float(F) / Fps, Length));
			for (int32 k = 0; k < TrackIndex.Num(); ++k)
			{
				FTransform Atom;
				Seq->GetBoneTransform(Atom, TrackIndex[k], Context, false);
				Add(k, Atom);
			}
		}
	}
	else
	{
		for (int32 F = 0; F < Frames; ++F)
		{
			for (int32 k = 0; k < TrackIndex.Num(); ++k)
			{
				FTransform Atom;
				Seq->GetBoneTransform(Atom, TrackIndex[k], FMath::Min(float(F) / Fps, Length), true);
				Add(k, Atom);
			}
		}
	}
	auto Motion = Kawaii::MakeMotion(std::move(Tracks), Cfg.FromReference ? &Bases : nullptr, Fps, Cfg.Loop, std::wstring(*Name));
	if (!Motion) { Why = TEXT("it moves none of the node's bones"); }
	return Motion;
}

// Each frame before the update: what the preview plays, the motion of the sets picked for it (made from its animation when
// it is picked: the evaluation plays it), its time for Sync, a start again when the preview's animation starts again
void PickAnimSetMotion(const FAnimNode_KawaiiPhysics& N, FKawaiiAnimSetPreview& P, const UAnimInstance* InAnimInstance, double& NextLoad)
{
	SkelCompat::KawaiiPoseAnimSet Cfg;
	AnimSetOf(N.PoseAnimSet, Cfg);
	if (!Cfg.Active())
	{
		if (P.bPicked || P.Motion)
		{
			P.Motion.reset();
			P.Pick.Reset();
			P.bPicked = false;
			++P.Serial;
		}
		P.bSynced = P.bRestart = false;
		P.Text.Reset();
		return;
	}
	const USkeletalMeshComponent* Mesh = InAnimInstance ? InAnimInstance->GetSkelMeshComponent() : nullptr;
	const UWorld* World = Mesh ? Mesh->GetWorld() : nullptr;
	ReadAnimSets(N.PoseAnimSet, P, FPlatformTime::Seconds(), NextLoad);
	// what the preview plays, in battle or not, moving or not (the mesh's speed over the ground)
	P.WasPlaying = P.Playing;
	P.WasTime = P.Time;
	WhatThePreviewPlays(InAnimInstance, P.Playing, P.Time);
	const FString AsPlaying = N.PoseAnimSet.PreviewPlaying.TrimStartAndEnd();
	const bool bAsPlaying = !AsPlaying.IsEmpty();
	if (bAsPlaying) { P.Playing = AsPlaying; }   // (Preview Playing: as if the character played it, at the preview's time)
	switch (N.PoseAnimSet.PreviewState)
	{
	case EKawaiiPoseAnimSetPreviewState::Field: P.bBattle = false; break;
	case EKawaiiPoseAnimSetPreviewState::Battle: P.bBattle = true; break;
	default: P.bBattle = P.Playing.StartsWith(TEXT("B_"), ESearchCase::IgnoreCase); break;
	}
	if (Mesh && World)
	{
		const double Now = World->GetTimeSeconds();
		const FVector At = Mesh->GetComponentLocation();
		if (P.LastSeconds >= 0.0 && Now > P.LastSeconds)
		{
			FVector Move = At - P.LastPosition;
			Move.Z = 0.0f;
			const float Seconds = float(Now - P.LastSeconds);
			const float Speed = Move.Size() / Seconds;
			if (Speed < 3000.0f) { P.Speed += (Speed - P.Speed) * FMath::Min(1.0f, Seconds / 0.15f); }   // (further: a teleport)
		}
		P.LastSeconds = Now;
		P.LastPosition = At;
	}
	P.bMoving = P.Speed > Cfg.MovingSpeed;
	// the pick (as the game's: the first matching pair, the same name, moving, idle; the preview's own motion first)
	TMap<FName, int32> Index;
	for (int32 k = 0; k < P.Entries.Num(); ++k) { Index.Add(P.Entries[k].Key, k); }
	const auto Find = [&](const std::wstring& Name) -> int32 {
		const FName Key(Name.c_str(), FNAME_Find);
		const int32* At = Key.IsNone() ? nullptr : Index.Find(Key);
		return At ? *At : INDEX_NONE;
	};
	bool bForPlaying = false;
	std::wstring Pick;
	if (!Cfg.Preview.empty() && Find(Cfg.Preview) != INDEX_NONE) { Pick = Cfg.Preview; }
	else
	{
		Pick = SkelCompat::KawaiiAnimSetMotion(Cfg, std::wstring(*P.Playing), P.bBattle, P.bMoving,
			[&](const std::wstring& Name) { return Find(Name) != INDEX_NONE; }, &bForPlaying);
	}
	const FString PickText(Pick.c_str());
	const int32 At = Pick.empty() ? INDEX_NONE : Find(Pick);
	const UAnimationAsset* Asset = At != INDEX_NONE ? P.Entries[At].Value.Get() : nullptr;
	const USkeletalMesh* Model = Mesh ? Mesh->SkeletalMesh : nullptr;
	uint32 Bones = GetTypeHash(N.RootBone.BoneName);
	for (const FKawaiiPhysicsRootBoneSetting& Extra : N.AdditionalRootBones) { Bones = HashCombine(Bones, GetTypeHash(Extra.RootBone.BoneName)); }
	Bones = HashCombine(Bones, GetTypeHash(Model));
	const bool bSame = P.bPicked && PickText.Equals(P.Pick, ESearchCase::IgnoreCase) && (P.Motion != nullptr || !P.Why.IsEmpty() || Pick.empty());
	bool bSameMotion = bSame;
	if (bSame && P.Motion)
	{
		// (the same pick: made again when its settings or its bones changed)
		bSameMotion = false;
		for (const FKawaiiAnimSetPreview::FMade& Made : P.Made)
		{
			if (Made.Motion == P.Motion) { bSameMotion = Made.Anim.Get() == Asset && Made.bReference == Cfg.FromReference && Made.Loop == Cfg.Loop && Made.Bones == Bones; break; }
		}
	}
	if (!bSameMotion)
	{
		P.Pick = PickText;
		P.bPicked = true;
		P.Motion.reset();
		P.Why.Reset();
		if (!Pick.empty())
		{
			const UAnimSequence* Seq = Cast<UAnimSequence>(Asset);
			if (!Asset) { P.Why = TEXT("in the sets with no animation of this project (in the game: not an animation the nodes play)"); }
			else if (!Seq) { P.Why = TEXT("not an AnimSequence"); }
			else if (!Model) { P.Why = TEXT("the preview has no model"); }
			else
			{
				FKawaiiAnimSetPreview::FMade* Found = nullptr;
				for (FKawaiiAnimSetPreview::FMade& Made : P.Made)
				{
					if (Made.Anim.Get() == Seq && Made.bReference == Cfg.FromReference && Made.Loop == Cfg.Loop && Made.Bones == Bones) { Found = &Made; break; }
				}
				if (!Found)
				{
					if (P.Made.Num() >= 24) { P.Made.RemoveAt(0); }
					FKawaiiAnimSetPreview::FMade& Made = P.Made.AddDefaulted_GetRef();
					Made.Anim = Seq;
					Made.Name = PickText;
					Made.bReference = Cfg.FromReference;
					Made.Loop = Cfg.Loop;
					Made.Bones = Bones;
					Made.Motion = MotionOfSequence(Seq, NodeBoneNames(N, Model->RefSkeleton), Cfg, PickText, Made.Why);
					Found = &Made;
				}
				P.Motion = Found->Motion;
				P.Why = Found->Why;
			}
		}
		++P.Serial;
	}
	// (KH3-style sync) at the time the preview is at in its animation; else a motion the preview starts again starts again
	P.bSynced = Cfg.Sync && bForPlaying && P.Time >= 0.0f && P.Motion != nullptr;
	P.SyncTime = P.Time;
	if (!P.bSynced && bForPlaying && P.Time >= 0.0f && P.WasTime >= 0.0f && P.Time + 0.05f < P.WasTime && P.Playing.Equals(P.WasPlaying, ESearchCase::IgnoreCase))
	{
		P.bRestart = true;
	}
	FString Text = FString(bAsPlaying ? TEXT("Animation sets: as if the character played ") : TEXT("Animation sets: the preview plays ")) +
		(P.Playing.IsEmpty() ? FString(TEXT("(nothing known)")) : P.Playing) +
		(P.bBattle ? TEXT(" in battle") : TEXT("")) + (P.bMoving ? TEXT(", moving") : TEXT("")) + TEXT(": ");
	if (P.Pick.IsEmpty()) { Text += TEXT("(none)"); }
	else if (!P.Motion) { Text += P.Pick + TEXT(" NOT played: ") + P.Why; }
	else
	{
		Text += P.Pick + FString::Printf(TEXT(" (%d bone(s), %d frame(s) at %.0f fps, %s)"), int32(P.Motion->Tracks->size()),
			int32(P.Motion->Tracks->front().Keys.size()), P.Motion->Fps, P.Motion->Loop ? TEXT("a loop") : TEXT("holds its end"));
		if (P.bSynced) { Text += TEXT(" in step"); }
		if (!Cfg.Preview.empty() && Pick == Cfg.Preview) { Text += TEXT(" (Preview Motion)"); }
	}
	if (!P.SetsNote.IsEmpty()) { Text += TEXT(" [") + P.SetsNote + TEXT("]"); }
	P.Text = Text;
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

// (1.11) On the game thread before the update: the level's wind at the mesh (FScene::GetWindParameters_GameThread; the
// preview's one sample for every bone), and the node's physics asset when it is loaded
void FAnimNode_KawaiiPhysics::PreUpdate(const UAnimInstance* InAnimInstance)
{
	FAnimNode_SkeletalControlBase::PreUpdate(InAnimInstance);
	// (1.12) the motion of the animation sets picked for what the preview plays
	if (PoseAnimSet.Sets.Num() > 0 && !AnimSetPreview.Get()) { AnimSetPreview.Reset(new FKawaiiAnimSetPreview()); }
	if (FKawaiiAnimSetPreview* P = AnimSetPreview.Get()) { PickAnimSetMotion(*this, *P, InAnimInstance, NextAnimSetLoad); }
	ResolvedPhysicsAsset = bUseModelPhysicsAssetForLimits ? nullptr : PhysicsAssetForLimits.Get();
	bPreviewWind = false;
	bool bWind = bEnableWind;
	for (const FKawaiiPhysicsExternalForce& Force : ExternalForces)
	{
		bWind |= Force.bIsEnabled && Force.Type == EKawaiiPhysicsExternalForceType::Wind;
	}
	const USkeletalMeshComponent* Mesh = (bWind && InAnimInstance) ? InAnimInstance->GetSkelMeshComponent() : nullptr;
	const UWorld* World = Mesh ? Mesh->GetWorld() : nullptr;
	if (!World || !World->Scene)
	{
		return;
	}
	FVector Direction(1.0f, 0.0f, 0.0f);
	float Speed = 0.0f, MinGust = 0.0f, MaxGust = 0.0f;
	World->Scene->GetWindParameters_GameThread(Mesh->GetComponentLocation(), Direction, Speed, MinGust, MaxGust);
	PreviewWindDirection = Direction.IsNearlyZero() ? FVector(1.0f, 0.0f, 0.0f) : Direction.GetSafeNormal();
	PreviewWindSpeed = Speed;
	PreviewWindMinGust = MinGust;
	PreviewWindMaxGust = MaxGust;
	bPreviewWind = Speed > 0.0f || MaxGust > 0.0f;
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
	for (FKawaiiPhysicsSyncBone& Sync : SyncBones)   // (1.10)
	{
		Sync.Bone.Initialize(RequiredBones);
		for (FKawaiiPhysicsSyncTargetRoot& Target : Sync.TargetRoots) { Target.Bone.Initialize(RequiredBones); }
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
		// (1.11) the physics asset whose bodies are its shapes (the mesh's own, or the node's when loaded)
		const UPhysicsAsset* Bodies = bUseModelPhysicsAssetForLimits ? (BoneContainer.GetSkeletalMeshAsset() ? BoneContainer.GetSkeletalMeshAsset()->PhysicsAsset : nullptr)
		                                                             : ResolvedPhysicsAsset.Get();
		const std::wstring Text = SkelCompat::KawaiiNodeJson(Config) + MotionText(PoseAnimation) + L"|bodies " + std::to_wstring(reinterpret_cast<uintptr_t>(Bodies));
		if (!S || S->ConfigText != Text)
		{
			Config.PoseAnimation.Tracks = TracksOf(PoseAnimation);   // (1.9: made only when something changed)
			PhysicsShapesOf(Bodies, BoneContainer.GetReferenceSkeleton(), Config);
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
				S->NodeSerial = ++NodeSerials;
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
		std::vector<Kawaii::Xf> RefComponent(static_cast<size_t>(Count));
		for (int32 i = 0; i < Count; ++i)
		{
			S->Skeleton.Names.push_back(Wide(Ref.GetBoneName(i)));
			S->Skeleton.Parents.push_back(Ref.GetParentIndex(i));
			S->Skeleton.RefLength.push_back(RefPose.IsValidIndex(i) ? RefPose[i].GetLocation().Size() : 0.0f);
			if (RefPose.IsValidIndex(i)) { S->RefLocal[size_t(i)] = ToKawaii(RefPose[i]); }
			// (1.10) the reference pose in the component's space (the sync bones start from it)
			const int32 Parent = Ref.GetParentIndex(i);
			RefComponent[size_t(i)] = Parent >= 0 && Parent < i ? Kawaii::Multiply(S->RefLocal[size_t(i)], RefComponent[size_t(Parent)]) : S->RefLocal[size_t(i)];
			S->Skeleton.RefLocation.push_back(RefComponent[size_t(i)].T);
			S->Skeleton.RefRotation.push_back(Kawaii::Normalized(RefComponent[size_t(i)].R));   // (1.11: the mirrored shapes)
		}
		S->SkeletonMesh = BoneContainer.GetSkeletalMeshAsset();
		S->SkeletonAsset = BoneContainer.GetSkeletonAsset();
		S->SkeletonBones = Count;
		if (S->Config.PhysicsAssetForLimits)   // (1.11: the new mesh's bodies)
		{
			const UPhysicsAsset* Bodies = bUseModelPhysicsAssetForLimits ? (S->SkeletonMesh ? S->SkeletonMesh->PhysicsAsset : nullptr) : ResolvedPhysicsAsset.Get();
			PhysicsShapesOf(Bodies, Ref, S->Config);
		}
		S->Node = std::make_unique<Kawaii::Node>(S->Config);   // (the chains are made from the bones again)
		S->NodeSerial = ++NodeSerials;
	}

	if (PendingTeleport == ETeleportType::ResetPhysics) { S->Node->ResetPhysics(); }
	else if (PendingTeleport == ETeleportType::TeleportPhysics) { S->Node->Teleport(); }
	PendingTeleport = ETeleportType::None;

	// (1.12) the animation sets' motion picked for what the preview plays (PreUpdate): a new pick cross-fades from the one
	// before; a new simulation plays it at once; Sync puts it at the preview's time
	if (FKawaiiAnimSetPreview* P = AnimSetPreview.Get())
	{
		if (P->PlayedOn != S->NodeSerial)
		{
			S->Node->PlayMotion(P->Motion, 0.0f);
			P->PlayedOn = S->NodeSerial;
			P->PlayedSerial = P->Serial;
		}
		else if (P->PlayedSerial != P->Serial)
		{
			S->Node->PlayMotion(P->Motion, S->Config.PoseAnimSet.BlendSeconds);
			P->PlayedSerial = P->Serial;
		}
		if (P->bSynced) { S->Node->SetMotionTime(double(P->SyncTime)); }
		else if (P->bRestart) { S->Node->SetMotionTime(0.0); }
		P->bRestart = false;
	}

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
	// (1.11) the world the preview's node sees: the level's wind (PreUpdate), nothing else of the game's world
	Kawaii::Environment World;
	const Kawaii::Environment* WorldSeen = nullptr;
	if (bPreviewWind)
	{
		Kawaii::WindSample Sample;
		Sample.Direction = {PreviewWindDirection.X, PreviewWindDirection.Y, PreviewWindDirection.Z};
		Sample.Speed = PreviewWindSpeed;
		Sample.MinGust = PreviewWindMinGust;
		Sample.MaxGust = PreviewWindMaxGust;
		World.Wind = [Sample](Kawaii::V3, Kawaii::WindSample& Out) {
			Out = Sample;
			return true;
		};
		WorldSeen = &World;
	}
	const bool bRan = S->Node->Evaluate(S->Skeleton, S->Pose, S->Changed, ToKawaii(ComponentTransform), FMath::Clamp(DeltaTime, 0.0f, 0.25f), nullptr, WorldSeen);
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

FString FAnimNode_KawaiiPhysics::GetAnimSetText() const
{
	const FKawaiiAnimSetPreview* P = AnimSetPreview.Get();
	return P ? P->Text : FString();
}

FString FAnimNode_KawaiiPhysics::ToGameJson(const FString& Indent) const
{
	SkelCompat::KawaiiNode Config;
	ConfigOf(*this, Config, /*bTracks*/ true, /*bGame*/ true);
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

// (1.11) The inverse of ForceOf
void ForceFrom(const SkelCompat::KawaiiExternalForce& K, FKawaiiPhysicsExternalForce& F)
{
	F = FKawaiiPhysicsExternalForce();
	F.Type = static_cast<EKawaiiPhysicsExternalForceType>(K.Type);
	F.bIsEnabled = K.Enabled;
	for (const std::wstring& Bone : K.ApplyBoneFilter) { F.ApplyBoneFilter.Add(BoneOf(Bone)); }
	for (const std::wstring& Bone : K.IgnoreBoneFilter) { F.IgnoreBoneFilter.Add(BoneOf(Bone)); }
	switch (K.Space)
	{
	case SkelCompat::KawaiiForceSpace::Component: F.ExternalForceSpace = EKawaiiPhysicsExternalForceSpace::ComponentSpace; break;
	case SkelCompat::KawaiiForceSpace::Bone: F.ExternalForceSpace = EKawaiiPhysicsExternalForceSpace::BoneSpace; break;
	default: F.ExternalForceSpace = EKawaiiPhysicsExternalForceSpace::WorldSpace; break;
	}
	F.RandomForceScaleRange = FFloatInterval(K.RandomForceScaleRange[0], K.RandomForceScaleRange[1]);
	CurveFrom(K.ForceRateByBoneLengthRate, F.ForceRateByBoneLengthRate);
	F.ForceDir = FVector(K.ForceDir[0], K.ForceDir[1], K.ForceDir[2]);
	F.Interval = K.Interval;
	F.bUseCharacterGravityDirection = K.UseCharacterGravityDirection;
	F.bUseCharacterGravityScale = K.UseCharacterGravityScale;
	F.bUseOverrideGravityDirection = K.UseOverrideGravityDirection;
	F.OverrideGravityDirection = FVector(K.OverrideGravityDirection[0], K.OverrideGravityDirection[1], K.OverrideGravityDirection[2]);
	for (const std::array<float, 4>& Key : K.ForceCurve.Keys)
	{
		FKawaiiPhysicsVectorKey Made;
		Made.Time = Key[0];
		Made.Value = FVector(Key[1], Key[2], Key[3]);
		F.ForceCurve.Add(Made);
	}
	F.CurveEvaluateType = static_cast<EKawaiiPhysicsCurveEvaluateType>(K.CurveEvaluateType);
	F.SubstepCount = K.SubstepCount;
	F.TimeScale = K.TimeScale;
	F.WindDirectionNoiseAngle = K.WindDirectionNoiseAngle;
	F.WindSource = static_cast<EKawaiiPhysicsWindSource>(K.WindSource);
	F.SharedWindTag = TextOf(K.SharedWindTag);
	F.WindDirection = FVector(K.WindDirection[0], K.WindDirection[1], K.WindDirection[2]);
	F.WindDirectionNoisePeriod = K.WindDirectionNoisePeriod;
	F.ConstantForce = K.ConstantForce;
	F.SwayForce = K.SwayForce;
	F.SwayPeriod = K.SwayPeriod;
	F.SwayPhaseOffset = K.SwayPhaseOffset;
	F.RippleForce = K.RippleForce;
	F.RipplePeriod = K.RipplePeriod;
	F.RipplePhaseOffset = K.RipplePhaseOffset;
	F.RippleTipPhaseDelay = K.RippleTipPhaseDelay;
	F.StrengthCycleRange = FFloatInterval(K.StrengthCycleRange[0], K.StrengthCycleRange[1]);
	F.StrengthCyclePeriod = K.StrengthCyclePeriod;
	F.StrengthCyclePhaseOffset = K.StrengthCyclePhaseOffset;
	F.RandomForce = K.RandomForce;
	F.RandomForcePeriod = K.RandomForcePeriod;
	F.Seed = K.Seed;
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
	N.bInterpolateLimitsInSubsteps = C.InterpolateLimitsInSubsteps;   // (1.10)
	N.bKeepCollisionSide = C.KeepCollisionSide;
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
		L.bOneSided = K.OneSided;   // (1.12)
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
	// (1.10) sync bones
	N.SyncBones.Reset();
	for (const SkelCompat::KawaiiSyncBone& K : C.SyncBones)
	{
		FKawaiiPhysicsSyncBone B;
		B.Bone = BoneOf(K.Bone);
		for (const SkelCompat::KawaiiSyncTarget& T : K.Targets)
		{
			FKawaiiPhysicsSyncTargetRoot Target;
			Target.Bone = BoneOf(T.Bone);
			Target.bIncludeChildBones = T.IncludeChildBones;
			CurveFrom(T.ScaleCurve, Target.ScaleCurveByBoneLengthRate);
			B.TargetRoots.Add(MoveTemp(Target));
		}
		B.GlobalScale = FVector(K.GlobalScale[0], K.GlobalScale[1], K.GlobalScale[2]);
		CurveFrom(K.ScaleCurveByDeltaDistance, B.ScaleCurveByDeltaDistance);
		B.ApplyDirectionX = static_cast<ESyncBoneDirection>(K.Direction[0]);
		B.ApplyDirectionY = static_cast<ESyncBoneDirection>(K.Direction[1]);
		B.ApplyDirectionZ = static_cast<ESyncBoneDirection>(K.Direction[2]);
		B.bEnableDistanceAttenuation = K.DistanceAttenuation;
		B.AttenuationInnerRadius = K.AttenuationInnerRadius;
		B.AttenuationOuterRadius = K.AttenuationOuterRadius;
		B.MaxAttenuationRate = K.MaxAttenuationRate;
		N.SyncBones.Add(MoveTemp(B));
	}
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
	// (1.12) the motions of animation sets
	N.PoseAnimSet = FKawaiiPoseAnimSet();
	{
		const SkelCompat::KawaiiPoseAnimSet& K = C.PoseAnimSet;
		FKawaiiPoseAnimSet& A = N.PoseAnimSet;
		for (const std::wstring& Path : K.Sets) { A.Sets.Add(TSoftObjectPtr<UObject>(FSoftObjectPath(FString(Path.c_str())))); }
		for (const SkelCompat::KawaiiMotionPair& Pair : K.Motions)
		{
			FKawaiiPoseAnimSetMotion M;
			M.Playing = TextOf(Pair.From);
			M.Motion = TextOf(Pair.To);
			A.Motions.Add(MoveTemp(M));
		}
		A.bSameNames = K.SameNames;
		A.Idle = TextOf(K.Idle);
		A.BattleIdle = TextOf(K.BattleIdle);
		A.Moving = TextOf(K.Moving);
		A.BattleMoving = TextOf(K.BattleMoving);
		A.MovingSpeed = K.MovingSpeed;
		A.BlendSeconds = K.BlendSeconds;
		A.Speed = K.Speed;
		A.Weight = K.Weight;
		A.bAdditive = K.Additive;
		A.AdditiveBase = K.FromReference ? EKawaiiPoseAnimSetBase::ReferencePose : EKawaiiPoseAnimSetBase::FirstFrame;
		A.Loop = K.Loop < 0 ? EKawaiiPoseAnimSetLoop::Auto : (K.Loop ? EKawaiiPoseAnimSetLoop::Loop : EKawaiiPoseAnimSetLoop::HoldEnd);
		A.bSync = K.Sync;
		A.PreviewMotion = TextOf(K.Preview);
	}
	// (1.11) the rest of KawaiiPhysics 1.21 (a set's shapes stay the files': its name is kept)
	N.bEnableWind = C.EnableWind;
	N.WindScale = C.WindScale;
	N.WindDirectionNoiseAngle = C.WindDirectionNoiseAngle;
	N.ExternalForces.Reset();
	for (const SkelCompat::KawaiiExternalForce& K : C.ExternalForces)
	{
		FKawaiiPhysicsExternalForce F;
		ForceFrom(K, F);
		N.ExternalForces.Add(MoveTemp(F));
	}
	N.AlphaInputType = EAnimAlphaInputType::Float;
	N.Alpha = C.Alpha;
	N.KawaiiPhysicsTag = TextOf(C.Tag);
	N.GameLimitsSets.Reset();
	for (const std::wstring& Name : C.LimitsSets) { N.GameLimitsSets.Add(TextOf(Name)); }
	N.GameBoneConstraintsSets.Reset();
	for (const std::wstring& Name : C.BoneConstraintsSets) { N.GameBoneConstraintsSets.Add(TextOf(Name)); }
	N.bUseModelPhysicsAssetForLimits = C.PhysicsAssetForLimits && C.PhysicsAssetPath.empty();
	N.PhysicsAssetForLimits = C.PhysicsAssetForLimits && !C.PhysicsAssetPath.empty() ? TSoftObjectPtr<UPhysicsAsset>(FSoftObjectPath(TextOf(C.PhysicsAssetPath))) : TSoftObjectPtr<UPhysicsAsset>();
	N.MirrorLimits = FKawaiiPhysicsMirrorLimits();
	if (C.MirrorLimits.Active())
	{
		switch (C.MirrorLimits.Axis)
		{
		case SkelCompat::KawaiiMirrorAxis::X: N.MirrorLimits.MirrorAxis = EKawaiiPhysicsMirrorAxis::X; break;
		case SkelCompat::KawaiiMirrorAxis::Z: N.MirrorLimits.MirrorAxis = EKawaiiPhysicsMirrorAxis::Z; break;
		default: N.MirrorLimits.MirrorAxis = EKawaiiPhysicsMirrorAxis::Y; break;
		}
		for (const auto& Pair : C.MirrorLimits.Pairs)
		{
			FKawaiiPhysicsMirrorBonePair Made;
			Made.Left = NameOf(Pair.first);
			Made.Right = NameOf(Pair.second);
			N.MirrorLimits.BonePairs.Add(Made);
		}
		for (const auto& Part : C.MirrorLimits.Prefixes)
		{
			FKawaiiPhysicsMirrorNamePart Made;
			Made.Left = TextOf(Part.first);
			Made.Right = TextOf(Part.second);
			N.MirrorLimits.Prefixes.Add(Made);
		}
		for (const auto& Part : C.MirrorLimits.Suffixes)
		{
			FKawaiiPhysicsMirrorNamePart Made;
			Made.Left = TextOf(Part.first);
			Made.Right = TextOf(Part.second);
			N.MirrorLimits.Suffixes.Add(Made);
		}
		N.MirrorLimits.bSkipMirroredBoneWithExistingCollision = C.MirrorLimits.SkipExisting;
	}
	N.bSharedCollisionSource = C.SharedCollisionSource;
	N.bUseSharedCollision = C.UseSharedCollision;
	N.SharedCollisionGroupTag = TextOf(C.SharedCollisionGroupTag);
	N.bAllowWorldCollision = C.World.AllowWorldCollision;
	N.bIgnoreSelfComponent = C.World.IgnoreSelfComponent;
	N.WorldCollisionMaxSweepsPerFrame = C.World.MaxSweepsPerFrame;
	N.bUseSimpleWorldCollision = C.World.UseSimpleWorldCollision;
	N.SimpleWorldCollisionGatherInterval = C.World.GatherInterval;
	N.bOverrideSimpleWorldCollisionGatherRadius = C.World.OverrideGatherRadius;
	N.SimpleWorldCollisionGatherRadius = C.World.GatherRadius;
	N.bSimpleWorldCollisionGroundCollision = C.World.GroundCollision;
	N.bGroundCollision = C.World.GroundOnly;
}

// (1.11) An entry's animation trigger as this editor's, and back as the game's (within its parser's limits; OutNotes:
// what it would leave out)
void TriggerFrom(const SkelCompat::KawaiiTrigger& K, FKawaiiPhysicsAnimationTrigger& T)
{
	T = FKawaiiPhysicsAnimationTrigger();
	T.Type = static_cast<EKawaiiPhysicsTriggerType>(K.Kind);   // (the same order)
	for (const std::wstring& Montage : K.Montages) { T.Montages.Add(TextOf(Montage)); }
	T.bPulse = K.Pulse;
	T.At = K.At;
	T.Start = K.Start;
	T.End = K.End;
	for (const std::wstring& Tag : K.FilterTags) { T.FilterTags.Add(TextOf(Tag)); }
	T.bFilterExactMatch = K.FilterExactMatch;
	for (const SkelCompat::KawaiiExternalForce& Force : K.Forces)
	{
		FKawaiiPhysicsExternalForce F;
		ForceFrom(Force, F);
		T.ExternalForces.Add(MoveTemp(F));
	}
	T.bAlphaFromCurve = K.AlphaFromCurve;
	T.ConstantAlpha = K.ConstantAlpha;
	T.CurveName = TextOf(K.CurveName);
	T.DefaultIfNoCurve = K.DefaultAlpha;
	T.SettingsScale.Damping = K.Scale.Damping;
	T.SettingsScale.Stiffness = K.Scale.Stiffness;
	T.SettingsScale.WorldDampingLocation = K.Scale.WorldDampingLocation;
	T.SettingsScale.WorldDampingRotation = K.Scale.WorldDampingRotation;
	T.SettingsScale.Radius = K.Scale.Radius;
	T.SettingsScale.LimitAngle = K.Scale.LimitAngle;
	T.bWeightFromCurve = K.WeightFromCurve;
	T.Duration = K.Duration;
	T.BlendInTime = K.BlendInTime;
	T.BlendOutTime = K.BlendOutTime;
	T.Strength = K.Strength;
	T.RiseTime = K.RiseTime;
	T.HoldTime = K.HoldTime;
	T.DecayTime = K.DecayTime;
	T.GustDirection = FVector(K.GustDirection[0], K.GustDirection[1], K.GustDirection[2]);
	T.bGustToSharedWind = K.SharedPublisher;
	T.SharedWindTag = TextOf(K.SharedWindTag);
	T.Preset = TextOf(K.Preset);
}

bool TriggerOf(const FKawaiiPhysicsAnimationTrigger& T, int32 Index, SkelCompat::KawaiiTrigger& K, FString& Notes)
{
	K = SkelCompat::KawaiiTrigger();
	K.Kind = static_cast<SkelCompat::KawaiiTriggerKind>(T.Type);
	for (const FString& Montage : T.Montages)
	{
		std::wstring Name(*Montage.TrimStartAndEnd());
		// (a path: its object's name, as the game's parser takes it)
		const size_t Cut = Name.find_last_of(L"./");
		if (Cut != std::wstring::npos && !Name.empty() && Name.back() != L'*') { Name = Name.substr(Cut + 1); }
		if (!Name.empty() && Name.size() <= 128) { SkelCompat::Detail::AddUniqueName(K.Montages, Name); }
	}
	if (K.Montages.empty())
	{
		Notes += FString::Printf(TEXT("animation trigger %d names no montage: left out\n"), Index);
		return false;
	}
	K.Pulse = T.bPulse;
	K.At = FMath::Clamp(T.At, 0.0f, 1.0e5f);
	K.Start = FMath::Clamp(T.Start, 0.0f, 1.0e5f);
	K.End = T.End < 0.0f ? -1.0f : FMath::Clamp(T.End, 0.0f, 1.0e5f);
	if (K.End >= 0.0f && K.End < K.Start)
	{
		Notes += FString::Printf(TEXT("animation trigger %d ends before it starts: to the montage's end\n"), Index);
		K.End = -1.0f;
	}
	if ((K.Kind == SkelCompat::KawaiiTriggerKind::TriggerGust || K.Kind == SkelCompat::KawaiiTriggerKind::WindPreset) && !K.Pulse)
	{
		K.Pulse = true;   // (a gust and a preset are pulses: at its start)
		K.At = K.Start;
	}
	if (K.Kind == SkelCompat::KawaiiTriggerKind::SetAlpha && K.Pulse)
	{
		Notes += FString::Printf(TEXT("animation trigger %d: Set Alpha is a state (Start - End), not a pulse\n"), Index);
		K.Pulse = false;
	}
	for (const FString& Tag : T.FilterTags)
	{
		const std::wstring Name = TagOf(Tag);
		if (!Name.empty()) { SkelCompat::Detail::AddUniqueName(K.FilterTags, Name); }
	}
	K.FilterExactMatch = T.bFilterExactMatch;
	for (const FKawaiiPhysicsExternalForce& Force : T.ExternalForces)
	{
		if (K.Forces.size() >= SkelCompat::MaxKawaiiExternalForces) { break; }
		SkelCompat::KawaiiExternalForce Made;
		ForceOf(Force, Made);
		K.Forces.push_back(std::move(Made));
	}
	if (K.Kind == SkelCompat::KawaiiTriggerKind::AddExternalForce && K.Forces.empty())
	{
		Notes += FString::Printf(TEXT("animation trigger %d (Add External Force) has no forces: left out\n"), Index);
		return false;
	}
	K.AlphaFromCurve = T.bAlphaFromCurve;
	K.ConstantAlpha = FMath::Clamp(T.ConstantAlpha, 0.0f, 1.0f);
	if (K.Kind == SkelCompat::KawaiiTriggerKind::SetAlpha || K.Kind == SkelCompat::KawaiiTriggerKind::SettingsMultiplier) { K.CurveName = std::wstring(*T.CurveName.TrimStartAndEnd()); }
	K.DefaultAlpha = FMath::Clamp(T.DefaultIfNoCurve, 0.0f, 1.0f);
	K.Scale.Damping = FMath::Clamp(T.SettingsScale.Damping, 0.0f, 1.0e3f);
	K.Scale.Stiffness = FMath::Clamp(T.SettingsScale.Stiffness, 0.0f, 1.0e3f);
	K.Scale.WorldDampingLocation = FMath::Clamp(T.SettingsScale.WorldDampingLocation, 0.0f, 1.0e3f);
	K.Scale.WorldDampingRotation = FMath::Clamp(T.SettingsScale.WorldDampingRotation, 0.0f, 1.0e3f);
	K.Scale.Radius = FMath::Clamp(T.SettingsScale.Radius, 0.0f, 1.0e3f);
	K.Scale.LimitAngle = FMath::Clamp(T.SettingsScale.LimitAngle, 0.0f, 1.0e3f);
	K.WeightFromCurve = T.bWeightFromCurve;
	K.Duration = FMath::Clamp(T.Duration, 0.0f, 1.0e4f);
	K.BlendInTime = FMath::Clamp(T.BlendInTime, 0.0f, 1.0e4f);
	K.BlendOutTime = FMath::Clamp(T.BlendOutTime, 0.0f, 1.0e4f);
	K.Strength = FMath::Clamp(T.Strength, -1.0e6f, 1.0e6f);
	K.RiseTime = FMath::Clamp(T.RiseTime, 0.0f, 1.0e4f);
	K.HoldTime = FMath::Clamp(T.HoldTime, 0.0f, 1.0e4f);
	K.DecayTime = FMath::Clamp(T.DecayTime, 0.0f, 1.0e4f);
	K.GustDirection[0] = FMath::Clamp(T.GustDirection.X, -1.0e6f, 1.0e6f);
	K.GustDirection[1] = FMath::Clamp(T.GustDirection.Y, -1.0e6f, 1.0e6f);
	K.GustDirection[2] = FMath::Clamp(T.GustDirection.Z, -1.0e6f, 1.0e6f);
	K.SharedPublisher = T.bGustToSharedWind;
	const std::wstring WindTag = TagOf(T.SharedWindTag);
	if (!WindTag.empty()) { K.SharedWindTag = WindTag; }
	K.Preset = std::wstring(*T.Preset.TrimStartAndEnd());
	if (K.Kind == SkelCompat::KawaiiTriggerKind::WindPreset)
	{
		SkelCompat::Config None;   // (the built-in presets; a file's own are checked by the game as it reads the file)
		if (K.Preset.empty())
		{
			Notes += FString::Printf(TEXT("animation trigger %d (Wind Preset) names no preset: left out\n"), Index);
			return false;
		}
		if (!SkelCompat::Detail::FindKawaiiWindPreset(None, K.Preset))
		{
			Notes += FString::Printf(TEXT("animation trigger %d: wind preset %s is not Breeze, Strong or Storm: it must be one of the compat files' \"kawaii_wind_presets\"\n"), Index, *T.Preset);
		}
	}
	return true;
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
		// (1.11) its KineDriver switch, animation triggers, shared winds and wind source
		Entry.bDisableKineDriver = Set.DisableKineDriver;
		for (const std::wstring& Asset : Set.DisableKineDriverAssets)
		{
			Entry.DisableKineDriverAssets.Add(TextOf(Asset));
		}
		for (const SkelCompat::KawaiiTrigger& Trigger : Set.Triggers)
		{
			FKawaiiPhysicsAnimationTrigger Made;
			TriggerFrom(Trigger, Made);
			Entry.AnimationTriggers.Add(MoveTemp(Made));
		}
		for (const SkelCompat::KawaiiSharedWind& Wind : Set.SharedWinds)
		{
			FKawaiiPhysicsSharedWind Made;
			Made.SharedWindTag = TextOf(Wind.Tag);
			Made.bIsEnabled = Wind.Enabled;
			ForceFrom(Wind.Wind, Made.Wind);
			Made.Wind.Type = EKawaiiPhysicsExternalForceType::ProceduralWind;
			Entry.SharedWinds.Add(MoveTemp(Made));
		}
		Entry.WorldWind.bEnabled = Set.WorldWind.Enabled;
		Entry.WorldWind.bOnlyWithoutLevelWind = Set.WorldWind.OnlyWithoutLevelWind;
		Entry.WorldWind.Direction = FVector(Set.WorldWind.Direction[0], Set.WorldWind.Direction[1], Set.WorldWind.Direction[2]);
		Entry.WorldWind.Speed = Set.WorldWind.Speed;
		Entry.WorldWind.Strength = Set.WorldWind.Strength;
		Entry.WorldWind.MinGustAmount = Set.WorldWind.MinGustAmount;
		Entry.WorldWind.MaxGustAmount = Set.WorldWind.MaxGustAmount;
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

FString KawaiiEntrySettingsJson(const TArray<FKawaiiPhysicsAnimationTrigger>& Triggers, const TArray<FKawaiiPhysicsSharedWind>& SharedWinds,
	const FKawaiiPhysicsWorldWind& WorldWind, const FString& Indent, FString& OutNotes)
{
	OutNotes.Reset();
	FString Out;
	if (WorldWind.bEnabled)
	{
		SkelCompat::KawaiiWorldWind W;
		W.Enabled = true;
		W.OnlyWithoutLevelWind = WorldWind.bOnlyWithoutLevelWind;
		W.Direction[0] = FMath::Clamp(WorldWind.Direction.X, -1.0e6f, 1.0e6f);
		W.Direction[1] = FMath::Clamp(WorldWind.Direction.Y, -1.0e6f, 1.0e6f);
		W.Direction[2] = FMath::Clamp(WorldWind.Direction.Z, -1.0e6f, 1.0e6f);
		W.Speed = FMath::Clamp(WorldWind.Speed, 0.0f, 1.0e5f);
		W.Strength = FMath::Clamp(WorldWind.Strength, 0.0f, 1.0e4f);
		W.MinGustAmount = FMath::Clamp(WorldWind.MinGustAmount, 0.0f, 1.0e4f);
		W.MaxGustAmount = FMath::Clamp(WorldWind.MaxGustAmount, 0.0f, 1.0e4f);
		Out += Indent + TEXT("\"world_wind\": ") + FString(SkelCompat::KawaiiWorldWindJson(W).c_str()) + TEXT(",\n");
	}
	TArray<FString> Winds;
	for (int32 i = 0; i < SharedWinds.Num() && Winds.Num() < 16; ++i)
	{
		const FKawaiiPhysicsSharedWind& Shared = SharedWinds[i];
		SkelCompat::KawaiiSharedWind W;
		const std::wstring Tag = TagOf(Shared.SharedWindTag);
		if (Tag.empty())
		{
			OutNotes += FString::Printf(TEXT("shared wind %d has no usable tag (a gameplay tag's name): left out\n"), i);
			continue;
		}
		W.Tag = Tag;
		W.Enabled = Shared.bIsEnabled;
		ForceOf(Shared.Wind, W.Wind);
		Winds.Add(FString(SkelCompat::KawaiiSharedWindJson(W).c_str()));
	}
	if (Winds.Num() > 0)
	{
		Out += Indent + TEXT("\"shared_winds\": [") + FString::Join(Winds, TEXT(", ")) + TEXT("],\n");
	}
	TArray<FString> Made;
	for (int32 i = 0; i < Triggers.Num() && Made.Num() < int32(SkelCompat::MaxKawaiiTriggers); ++i)
	{
		SkelCompat::KawaiiTrigger K;
		if (TriggerOf(Triggers[i], i, K, OutNotes)) { Made.Add(Indent + TEXT("  ") + FString(SkelCompat::KawaiiTriggerJson(K).c_str())); }
	}
	if (Made.Num() > 0)
	{
		Out += Indent + TEXT("\"animation_triggers\": [\n") + FString::Join(Made, TEXT(",\n")) + TEXT("\n") + Indent + TEXT("],\n");
	}
	return Out;
}
