// KawaiiPhysics for UE 4.26 (the End editor): the node of KawaiiPhysics 1.7.0 with the newest KawaiiPhysics' (1.21)
// features fused in, as Create a Character System runs it in FINAL FANTASY VII REBIRTH. The simulation is the game
// mod's (KawaiiSolver.hpp), so the editor's preview moves the bones as the game will.
// KawaiiPhysics is pafuhana1213's (https://github.com/pafuhana1213/KawaiiPhysics), MIT License.
#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimNodeBase.h"
#include "BoneContainer.h"
#include "BonePose.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"
#include "BoneControllers/AnimNode_AnimDynamics.h"
#include "Curves/CurveFloat.h"

#include "AnimNode_KawaiiPhysics.generated.h"

class UKawaiiPhysicsLimitsDataAsset;
struct FKawaiiPhysicsSolver;   // (the shared simulation: AnimNode_KawaiiPhysics.cpp)

UENUM()
enum class EPlanarConstraint : uint8
{
	None,
	X,
	Y,
	Z,
};

UENUM()
enum class EBoneForwardAxis : uint8
{
	X_Positive,
	X_Negative,
	Y_Positive,
	Y_Negative,
	Z_Positive,
	Z_Negative,
};

UENUM()
enum class ECollisionLimitType : uint8
{
	None,
	Spherical,
	Capsule,
	Planar,
	TaperedCapsule,
	Box,
};

/** The space the bones are simulated in */
UENUM()
enum class EKawaiiPhysicsSimulationSpace : uint8
{
	ComponentSpace,
	WorldSpace,
	BaseBoneSpace,
};

/** How hard a bone constraint holds (XPBD compliance) */
UENUM()
enum class EXPBDComplianceType : uint8
{
	Concrete,
	Wood,
	Leather,
	Tendon,
	Rubber,
	Muscle,
	Fat,
};

USTRUCT()
struct KAWAIIPHYSICS_API FCollisionLimitBase
{
	GENERATED_BODY()

	/** Bone to attach the shape to */
	UPROPERTY(EditAnywhere, Category = CollisionLimitBase)
	FBoneReference DrivingBone;

	UPROPERTY(EditAnywhere, Category = CollisionLimitBase)
	FVector OffsetLocation = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, Category = CollisionLimitBase, meta = (ClampMin = "-360", ClampMax = "360"))
	FRotator OffsetRotation = FRotator::ZeroRotator;

	/** (where the shape is now, in the component's space: for the editor's drawing) */
	UPROPERTY()
	FVector Location = FVector::ZeroVector;

	UPROPERTY()
	FQuat Rotation = FQuat::Identity;

#if WITH_EDITORONLY_DATA
	UPROPERTY()
	bool bFromDataAsset = false;

	UPROPERTY(VisibleAnywhere, Category = Debug, meta = (IgnoreForMemberInitializationTest))
	FGuid Guid = FGuid::NewGuid();

	UPROPERTY()
	ECollisionLimitType Type = ECollisionLimitType::None;
#endif
};

USTRUCT()
struct KAWAIIPHYSICS_API FSphericalLimit : public FCollisionLimitBase
{
	GENERATED_BODY()

	FSphericalLimit()
	{
#if WITH_EDITORONLY_DATA
		Type = ECollisionLimitType::Spherical;
#endif
	}

	/** Radius of the sphere */
	UPROPERTY(EditAnywhere, Category = SphericalLimit, meta = (ClampMin = "0"))
	float Radius = 5.0f;

	/** Whether to lock bodies inside or outside of the sphere */
	UPROPERTY(EditAnywhere, Category = SphericalLimit)
	ESphericalLimitType LimitType = ESphericalLimitType::Outer;
};

USTRUCT()
struct KAWAIIPHYSICS_API FCapsuleLimit : public FCollisionLimitBase
{
	GENERATED_BODY()

	FCapsuleLimit()
	{
#if WITH_EDITORONLY_DATA
		Type = ECollisionLimitType::Capsule;
#endif
	}

	UPROPERTY(EditAnywhere, Category = CapsuleLimit, meta = (ClampMin = "0"))
	float Radius = 5.0f;

	/** Along the shape's Z axis */
	UPROPERTY(EditAnywhere, Category = CapsuleLimit, meta = (ClampMin = "0"))
	float Length = 10.0f;
};

USTRUCT()
struct KAWAIIPHYSICS_API FTaperedCapsuleLimit : public FCollisionLimitBase
{
	GENERATED_BODY()

	FTaperedCapsuleLimit()
	{
#if WITH_EDITORONLY_DATA
		Type = ECollisionLimitType::TaperedCapsule;
#endif
	}

	/** Radius of the end at +Z */
	UPROPERTY(EditAnywhere, Category = TaperedCapsuleLimit, meta = (ClampMin = "0"))
	float Radius0 = 5.0f;

	/** Radius of the end at -Z */
	UPROPERTY(EditAnywhere, Category = TaperedCapsuleLimit, meta = (ClampMin = "0"))
	float Radius1 = 5.0f;

	/** Distance between the two end spheres' centers. At most |Radius0 - Radius1|: the larger end sphere alone */
	UPROPERTY(EditAnywhere, Category = TaperedCapsuleLimit, meta = (ClampMin = "0"))
	float Length = 10.0f;
};

USTRUCT()
struct KAWAIIPHYSICS_API FBoxLimit : public FCollisionLimitBase
{
	GENERATED_BODY()

	FBoxLimit()
	{
#if WITH_EDITORONLY_DATA
		Type = ECollisionLimitType::Box;
#endif
	}

	/** Half sizes */
	UPROPERTY(EditAnywhere, Category = BoxLimit)
	FVector Extent = FVector(5.0f, 5.0f, 5.0f);
};

USTRUCT()
struct KAWAIIPHYSICS_API FPlanarLimit : public FCollisionLimitBase
{
	GENERATED_BODY()

	FPlanarLimit()
	{
#if WITH_EDITORONLY_DATA
		Type = ECollisionLimitType::Planar;
#endif
	}

	/** (the plane now, in the component's space) */
	UPROPERTY()
	FPlane Plane = FPlane(0, 0, 0, 0);
};

USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPhysicsSettings
{
	GENERATED_BODY()

	/** How fast a bone's swing dies down (0 - 1) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta = (ClampMin = "0", ClampMax = "1"), Category = "KawaiiPhysics")
	float Damping = 0.1f;

	/** How little the bones lag behind the character's moves (0 - 1; 1: not at all) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta = (ClampMin = "0", ClampMax = "1"), Category = "KawaiiPhysics")
	float WorldDampingLocation = 0.8f;

	/** How little the bones lag behind the character's turns (0 - 1; 1: not at all) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta = (ClampMin = "0", ClampMax = "1"), Category = "KawaiiPhysics")
	float WorldDampingRotation = 0.8f;

	/** How hard a bone is pulled back to its animated place (0 - 1) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta = (ClampMin = "0", ClampMax = "1"), Category = "KawaiiPhysics")
	float Stiffness = 0.05f;

	/** Each bone's size against the collision shapes (cm) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta = (ClampMin = "0"), Category = "KawaiiPhysics")
	float Radius = 3.0f;

	/** Degrees a bone may swing from its animated direction (0: no limit) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta = (PinHiddenByDefault, ClampMin = "0", ClampMax = "360"), Category = "KawaiiPhysics")
	float LimitAngle = 0.0f;
};

/** Another chain in the same node */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPhysicsRootBoneSetting
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "KawaiiPhysics")
	FBoneReference RootBone;

	/** Its own exclude bones instead of the node's */
	UPROPERTY(EditAnywhere, Category = "KawaiiPhysics", meta = (InlineEditConditionToggle))
	bool bUseOverrideExcludeBones = false;

	UPROPERTY(EditAnywhere, Category = "KawaiiPhysics", meta = (EditCondition = "bUseOverrideExcludeBones"))
	TArray<FBoneReference> OverrideExcludeBones;
};

/** Two bones kept at their distance (cloth strips side by side) */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FModifyBoneConstraint
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "KawaiiPhysics")
	FBoneReference Bone1;

	UPROPERTY(EditAnywhere, Category = "KawaiiPhysics")
	FBoneReference Bone2;

	UPROPERTY(EditAnywhere, Category = "KawaiiPhysics", meta = (InlineEditConditionToggle))
	bool bOverrideCompliance = false;

	UPROPERTY(EditAnywhere, Category = "KawaiiPhysics", meta = (EditCondition = "bOverrideCompliance"))
	EXPBDComplianceType ComplianceType = EXPBDComplianceType::Leather;

	/** Leave this pair out of the bone constraint subdivision */
	UPROPERTY(EditAnywhere, Category = "KawaiiPhysics")
	bool bExcludeFromSubdivision = false;
};

/** One simulated bone, for the editor's drawing (component space) */
struct KAWAIIPHYSICS_API FKawaiiPhysicsDebugBone
{
	FVector Location = FVector::ZeroVector;
	FVector PoseLocation = FVector::ZeroVector;
	float Radius = 0.0f;
	float LimitAngle = 0.0f;
	float LengthRate = 0.0f;   // its place along its chain (0: the root, 1: the end)
	int32 Parent = INDEX_NONE;
	bool bDummy = false;
};

/** Holds the node's simulation; a copy of the node (its class default, a new instance) starts with none */
struct KAWAIIPHYSICS_API FKawaiiPhysicsSolverHolder
{
	FKawaiiPhysicsSolverHolder();
	FKawaiiPhysicsSolverHolder(const FKawaiiPhysicsSolverHolder&);
	FKawaiiPhysicsSolverHolder& operator=(const FKawaiiPhysicsSolverHolder&);
	~FKawaiiPhysicsSolverHolder();

	FKawaiiPhysicsSolver* Get() const { return Solver; }
	void Reset(FKawaiiPhysicsSolver* InSolver = nullptr);

private:
	FKawaiiPhysicsSolver* Solver = nullptr;
};

USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FAnimNode_KawaiiPhysics : public FAnimNode_SkeletalControlBase
{
	GENERATED_BODY()

	// ---- the bones -------------------------------------------------------------------
	/** The chain's top bone: it follows the animation, the bones below it swing */
	UPROPERTY(EditAnywhere, Category = ModifyTarget)
	FBoneReference RootBone;

	/** Bones left out of the chains (with the bones below them) */
	UPROPERTY(EditAnywhere, Category = ModifyTarget)
	TArray<FBoneReference> ExcludeBones;

	/** More chains in this node (its settings and shapes) */
	UPROPERTY(EditAnywhere, Category = ModifyTarget)
	TArray<FKawaiiPhysicsRootBoneSetting> AdditionalRootBones;

	// ---- physics ---------------------------------------------------------------------
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Physics Settings", meta = (PinHiddenByDefault))
	FKawaiiPhysicsSettings PhysicsSettings;

	/** The settings times these along the chain (0: its root, 1: its end) */
	UPROPERTY(EditAnywhere, Category = "Physics Settings", meta = (DisplayName = "Damping Rate by Bone Length Rate"))
	FRuntimeFloatCurve DampingCurveData;

	UPROPERTY(EditAnywhere, Category = "Physics Settings", meta = (DisplayName = "Stiffness Rate by Bone Length Rate"))
	FRuntimeFloatCurve StiffnessCurveData;

	UPROPERTY(EditAnywhere, Category = "Physics Settings", meta = (DisplayName = "World Damping Location Rate by Bone Length Rate"))
	FRuntimeFloatCurve WorldDampingLocationCurveData;

	UPROPERTY(EditAnywhere, Category = "Physics Settings", meta = (DisplayName = "World Damping Rotation Rate by Bone Length Rate"))
	FRuntimeFloatCurve WorldDampingRotationCurveData;

	UPROPERTY(EditAnywhere, Category = "Physics Settings", meta = (DisplayName = "Radius Rate by Bone Length Rate"))
	FRuntimeFloatCurve RadiusCurveData;

	UPROPERTY(EditAnywhere, Category = "Physics Settings", meta = (DisplayName = "LimitAngle Rate by Bone Length Rate"))
	FRuntimeFloatCurve LimitAngleCurveData;

	/** A point this far past each end bone, so the end bones turn too (0: none) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DummyBone", meta = (PinHiddenByDefault, ClampMin = "0"))
	float DummyBoneLength = 0.0f;

	/** The axis the bones point along (the game's bones: X+) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DummyBone", meta = (PinHiddenByDefault))
	EBoneForwardAxis BoneForwardAxis = EBoneForwardAxis::X_Positive;

	/** Points put between each two bones (0 - 10), for collisions on long bones */
	UPROPERTY(EditAnywhere, Category = "Bone Subdivision", meta = (ClampMin = "0", ClampMax = "10"))
	int32 BoneSubdivisionCount = 0;

	/** They only collide (placed between their bones), else they simulate */
	UPROPERTY(EditAnywhere, Category = "Bone Subdivision", meta = (EditCondition = "BoneSubdivisionCount > 0"))
	bool bBoneSubdivisionCollisionOnly = true;

	/** More of them where two bones are far apart for their radius */
	UPROPERTY(EditAnywhere, Category = "Bone Subdivision", meta = (EditCondition = "BoneSubdivisionCount > 0"))
	bool bBoneSubdivisionDensifyByRadius = false;

	/** Each bone stays in that plane of its parent */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Advanced Physics Settings", meta = (PinHiddenByDefault))
	EPlanarConstraint PlanarConstraint = EPlanarConstraint::None;

	UPROPERTY(EditAnywhere, Category = "Advanced Physics Settings")
	EKawaiiPhysicsSimulationSpace SimulationSpace = EKawaiiPhysicsSimulationSpace::ComponentSpace;

	UPROPERTY(EditAnywhere, Category = "Advanced Physics Settings", meta = (EditCondition = "SimulationSpace == EKawaiiPhysicsSimulationSpace::BaseBoneSpace"))
	FBoneReference SimulationBaseBone;

	/** Steps of 1/TargetFramerate s */
	UPROPERTY(EditAnywhere, Category = "Advanced Physics Settings", meta = (ClampMin = "1"))
	int32 TargetFramerate = 60;

	UPROPERTY(EditAnywhere, Category = "Advanced Physics Settings")
	bool bUseFixedSubstepping = true;

	UPROPERTY(EditAnywhere, Category = "Advanced Physics Settings", meta = (ClampMin = "1", ClampMax = "64", EditCondition = "bUseFixedSubstepping"))
	int32 MaxSubsteps = 4;

	/** Steps run before the first frame */
	UPROPERTY(EditAnywhere, Category = "Advanced Physics Settings", meta = (InlineEditConditionToggle))
	bool bNeedWarmUp = false;

	UPROPERTY(EditAnywhere, Category = "Advanced Physics Settings", meta = (EditCondition = "bNeedWarmUp", ClampMin = "0"))
	int32 WarmUpFrames = 0;

	UPROPERTY(EditAnywhere, Category = "Advanced Physics Settings", meta = (EditCondition = "bNeedWarmUp"))
	bool bUseWarmUpWhenResetDynamics = true;

	/** How much of the mesh's move the bones feel, per axis of the mesh */
	UPROPERTY(EditAnywhere, Category = "Advanced Physics Settings")
	FVector SkelCompMoveScale = FVector::OneVector;

	/** A move of the mesh longer than this in one frame is not felt (cm) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Teleport", meta = (PinHiddenByDefault))
	float TeleportDistanceThreshold = 300.0f;

	/** A turn of the mesh wider than this in one frame is not felt (degrees) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Teleport", meta = (PinHiddenByDefault))
	float TeleportRotationThreshold = 10.0f;

	// ---- collision shapes ------------------------------------------------------------
	UPROPERTY(EditAnywhere, Category = "Spherical Limits")
	TArray<FSphericalLimit> SphericalLimits;

	UPROPERTY(EditAnywhere, Category = "Capsule Limits")
	TArray<FCapsuleLimit> CapsuleLimits;

	UPROPERTY(EditAnywhere, Category = "Tapered Capsule Limits")
	TArray<FTaperedCapsuleLimit> TaperedCapsuleLimits;

	UPROPERTY(EditAnywhere, Category = "Box Limits")
	TArray<FBoxLimit> BoxLimits;

	UPROPERTY(EditAnywhere, Category = "Planar Limits")
	TArray<FPlanarLimit> PlanarLimits;

	/** Shapes shared by several nodes */
	UPROPERTY(EditAnywhere, Category = "Limits Data(Experimental)")
	UKawaiiPhysicsLimitsDataAsset* LimitsDataAsset = nullptr;

	UPROPERTY(VisibleAnywhere, AdvancedDisplay, Category = "Limits Data(Experimental)")
	TArray<FSphericalLimit> SphericalLimitsData;

	UPROPERTY(VisibleAnywhere, AdvancedDisplay, Category = "Limits Data(Experimental)")
	TArray<FCapsuleLimit> CapsuleLimitsData;

	UPROPERTY(VisibleAnywhere, AdvancedDisplay, Category = "Limits Data(Experimental)")
	TArray<FTaperedCapsuleLimit> TaperedCapsuleLimitsData;

	UPROPERTY(VisibleAnywhere, AdvancedDisplay, Category = "Limits Data(Experimental)")
	TArray<FBoxLimit> BoxLimitsData;

	UPROPERTY(VisibleAnywhere, AdvancedDisplay, Category = "Limits Data(Experimental)")
	TArray<FPlanarLimit> PlanarLimitsData;

	// ---- bone constraints ------------------------------------------------------------
	UPROPERTY(EditAnywhere, Category = "Bone Constraint (Experimental)")
	EXPBDComplianceType BoneConstraintGlobalComplianceType = EXPBDComplianceType::Leather;

	UPROPERTY(EditAnywhere, Category = "Bone Constraint (Experimental)", meta = (ClampMin = "0", ClampMax = "64"))
	int32 BoneConstraintIterationCountBeforeCollision = 1;

	UPROPERTY(EditAnywhere, Category = "Bone Constraint (Experimental)", meta = (ClampMin = "0", ClampMax = "64"))
	int32 BoneConstraintIterationCountAfterCollision = 1;

	/** Constrain the dummy points of two constrained end bones too */
	UPROPERTY(EditAnywhere, Category = "Bone Constraint (Experimental)")
	bool bAutoAddChildDummyBoneConstraint = true;

	UPROPERTY(EditAnywhere, Category = "Bone Constraint (Experimental)", meta = (TitleProperty = "{Bone1} - {Bone2}"))
	TArray<FModifyBoneConstraint> BoneConstraints;

	/** Collision points along each constrained pair (0 - 10) */
	UPROPERTY(EditAnywhere, Category = "Bone Constraint (Experimental)", meta = (ClampMin = "0", ClampMax = "10"))
	int32 BoneConstraintSubdivisionCount = 0;

	/** How much those points' pushes move the two bones (0 - 2) */
	UPROPERTY(EditAnywhere, Category = "Bone Constraint (Experimental)", meta = (ClampMin = "0", ClampMax = "2", EditCondition = "BoneConstraintSubdivisionCount > 0"))
	float BoneConstraintSubdivisionFeedbackScale = 1.0f;

	// ---- forces ----------------------------------------------------------------------
	/** cm/s/s (none by default) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "ExternalForce", meta = (PinHiddenByDefault))
	FVector Gravity = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, Category = "ExternalForce")
	bool bUseLegacyGravity = false;

	/** Gravity times the world's gravity (980) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce")
	bool bUseDefaultGravityZProjectSetting = false;

	/** Down in the world, however the character is turned */
	UPROPERTY(EditAnywhere, Category = "ExternalForce")
	bool bUseWorldSpaceGravity = true;

	/** A steady push (cm/s) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "ExternalForce", meta = (PinHiddenByDefault))
	FVector SimpleExternalForce = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, Category = "ExternalForce")
	bool bUseWorldSpaceSimpleExternalForce = true;

	// ---- the game (Create a Character System) ------------------------------------------
	/** In the game: the bones a BNM of the model still moves stay out of the chains */
	UPROPERTY(EditAnywhere, Category = "Create a Character")
	bool bSkipBonamikBones = true;

	/** A name for the game's log ("hair"); empty: the root bone's */
	UPROPERTY(EditAnywhere, Category = "Create a Character")
	FString NodeName;

public:
	FAnimNode_KawaiiPhysics();

	// FAnimNode_Base interface
	virtual void Initialize_AnyThread(const FAnimationInitializeContext& Context) override;
	virtual bool NeedsDynamicReset() const override { return true; }
	virtual void ResetDynamics(ETeleportType InTeleportType) override;
	// FAnimNode_SkeletalControlBase interface
	virtual void UpdateInternal(const FAnimationUpdateContext& Context) override;
	virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output, TArray<FBoneTransform>& OutBoneTransforms) override;
	virtual bool IsValidToEvaluate(const USkeleton* Skeleton, const FBoneContainer& RequiredBones) override;

	/** The simulated bones of the last evaluation (the editor's drawing) */
	void GetDebugBones(TArray<FKawaiiPhysicsDebugBone>& OutBones) const;
	/** Why the node does not run (empty: it runs) */
	FString GetProblem() const;
	/** The node as one of the game's "kawaii" nodes (JSON text, an object) */
	FString ToGameJson(const FString& Indent = TEXT("")) const;
	/** (the editor, after it copies new settings in) the bone references are made again at the next evaluation */
	void MarkBonesDirty() { bBonesDirty = true; }

private:
	virtual void InitializeBoneReferences(const FBoneContainer& RequiredBones) override;
	void ApplyLimitsDataAsset(const FBoneContainer& RequiredBones);
	void UpdateShapePlaces(FComponentSpacePoseContext& Output, const FBoneContainer& BoneContainer);

	FKawaiiPhysicsSolverHolder Solver;
	float DeltaTime = 0.0f;
	ETeleportType PendingTeleport = ETeleportType::None;
	bool bBonesDirty = false;
#if WITH_EDITORONLY_DATA
	bool bEditing = false;
#endif
};

/** (1.8) One of the game's "kawaii" entries read back from a compat file (Import From Game): its models, paks and
 *  Bonamik switch, and its nodes as this editor's KawaiiPhysics nodes (every setting, shape and bone constraint). */
struct KAWAIIPHYSICS_API FKawaiiPhysicsGameEntry
{
	/** "name" (the game does not read it: for whoever reads the file) */
	FString Name;
	TArray<FString> Models;
	TArray<FString> RequiresPaks;
	bool bDisableBonamik = false;
	TArray<FString> DisableBonamikAssets;
	TArray<FAnimNode_KawaiiPhysics> Nodes;
};

/** (1.8) The "kawaii" entries of a Create a Character System compat file, read with the game mod's own parser (as the
 *  game reads them; every entry, whether its paks are installed or not). OutMessages: what the parser said of them.
 *  False when the text is not such a file. */
KAWAIIPHYSICS_API bool ReadKawaiiGameEntries(const FString& JsonText, TArray<FKawaiiPhysicsGameEntry>& OutEntries, FString& OutMessages);
