// Kawaii Dynamic Motions (1.9: KawaiiPhysics' new name, in text; the code keeps KawaiiPhysics' names) for UE 4.26 (the
// End editor): the node of KawaiiPhysics 1.7.0 with the newest KawaiiPhysics' (1.21) features fused in, as Create a
// Character System runs it in FINAL FANTASY VII REBIRTH, and (1.9) its own motions: waves and a looping key animation
// that move its bones' pose before the physics runs (Dynamic Motions). (1.10) KawaiiPhysics' sync bones: an animated
// bone whose move the chains' pose follows (a coat's strips a knee). (1.11) The rest of KawaiiPhysics 1.21: external
// forces and wind, the game's sets, the physics asset's bodies as shapes, mirrored shapes, shared and world collision (the
// game runs them: Create a Character System 3.18.0), and the entry's animation triggers, shared winds and wind source
// (Export / Import For Game). (1.12) The bones' motion from animation sets: an EndAnimSet's motion of the name of what the
// character plays (or a pair's), as Create a Character System 3.20.0 plays it ("pose_animset"; KH3-style in step with it
// with Sync), the preview playing the sets' motions for what the preview plays; planes as solid floors ("one_sided").
// The simulation is the game mod's (KawaiiSolver.hpp), so the editor's preview moves the bones as the game will.
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
class UPhysicsAsset;
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

	/** (1.12) A solid floor: the chains' bones are kept on its up side (as far as their radius), not only stopped while
	 *  they cross it, so a motion that swings a tail or a wing down cannot push them through it (the bones keep their
	 *  lengths). The game's "one_sided" (Create a Character System 3.20.0) */
	UPROPERTY(EditAnywhere, Category = CollisionLimitBase)
	bool bOneSided = false;

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

/** (1.9, Dynamic Motions) A wave that turns the node's bones to and fro in their pose, the place the physics pulls each
 *  one back to, so the chain moves on its own with the physics on top: a tail's sway, a wing's slow beat. Each bone
 *  turns about Axis by Degrees * sin(360 * time / Seconds + Phase - Phase Per Bone * its steps from its root - Phase Per
 *  Root * its chain's number - Root Phases[its chain's number]), times Degrees Curve at its place along the chain. The
 *  game's "pose_waves". */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPoseWave
{
	GENERATED_BODY()

	/** The axis each bone turns about: the model's (+X its front, +Y its right, +Z up) at the bone, as the animation
	 *  has it; with Local Axis, the bone's own. Z: side to side (a tail), X: up and down for a wing out to the side */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dynamic Motions")
	FVector Axis = FVector(0.0f, 0.0f, 1.0f);

	/** Axis in each bone's own space instead of the model's */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dynamic Motions")
	bool bLocalAxis = false;

	/** The turn of each bone at the wave's crest (degrees, -180 - 180). The turns add up down a chain: a few degrees a
	 *  bone sway a long tail far */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dynamic Motions", meta = (ClampMin = "-180", ClampMax = "180"))
	float Degrees = 5.0f;

	/** A whole wave, there and back (seconds) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dynamic Motions", meta = (ClampMin = "0.05", ClampMax = "600"))
	float Seconds = 3.0f;

	/** Where in its wave it starts (degrees: 360 a whole wave) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dynamic Motions")
	float Phase = 0.0f;

	/** Each bone a step further from its root this far behind (degrees): the sway travels down the chain */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dynamic Motions")
	float PhasePerBone = 0.0f;

	/** Each chain (Root Bone 0, then the Additional Root Bones in order) this far behind the one before (degrees): a ripple
	 *  over many chains (the blades of a wing) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dynamic Motions")
	float PhasePerRoot = 0.0f;

	/** Each chain this far behind, chain by chain (degrees: Root Bone first, then the Additional Root Bones), added to
	 *  Phase Per Root's */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dynamic Motions")
	TArray<float> RootPhases;

	/** Along each chain (0 its root, 1 its end), the part of Degrees each bone turns (no keys: all of it) */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions", meta = (DisplayName = "Degrees Rate by Bone Length Rate"))
	FRuntimeFloatCurve DegreesCurve;
};

/** (1.9, Dynamic Motions) One bone's track of the node's key animation: its local rotation (under its parent), a key
 *  a frame */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPoseKeyTrack
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Dynamic Motions")
	FBoneReference Bone;

	/** Its local rotation each frame (every track as long, or one key) */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions")
	TArray<FQuat> Keys;
};

/** (1.9, Dynamic Motions) A looping key animation of the node's bones, played on their pose before the waves and the
 *  physics (a creature's wing beat put on another model's wing). The game's "pose_animation". */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPoseAnimation
{
	GENERATED_BODY()

	/** The tracks' frames a second */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dynamic Motions", meta = (ClampMin = "1", ClampMax = "1000"))
	float Fps = 30.0f;

	/** How fast it plays (negative: backwards) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dynamic Motions", meta = (ClampMin = "-100", ClampMax = "100"))
	float Speed = 1.0f;

	/** How much of it (0 - 1) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dynamic Motions", meta = (ClampMin = "0", ClampMax = "1"))
	float Weight = 1.0f;

	/** The turn from its first frame added to the pose (its first frame changes nothing); off: its rotations take the
	 *  place of the pose's */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dynamic Motions")
	bool bAdditive = true;

	/** A track a bone (up to 256 bones and 6000 frames; Import From Game reads them from a compat file) */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions", meta = (TitleProperty = "Bone"))
	TArray<FKawaiiPoseKeyTrack> Tracks;
};

/** (1.12, Dynamic Motions) What the character plays -> the motion of the animation sets its bones play then (the game's
 *  "motions" pairs; the first that matches wins) */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPoseAnimSetMotion
{
	GENERATED_BODY()

	/** The character's animation (wildcards: * any letters, ? one letter; case aside), e.g. B_NAttack0* */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dynamic Motions")
	FString Playing;

	/** The motion of the sets the bones play then, e.g. B_AtkBladeCombo01_0. Empty: none of the sets' while it plays (the
	 *  node's own pose animation, if any) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dynamic Motions")
	FString Motion;
};

/** (1.12) What a motion of the sets turns the bones by */
UENUM()
enum class EKawaiiPoseAnimSetBase : uint8
{
	/** The turn of each bone from the motion's first frame (its first frame changes nothing) */
	FirstFrame,
	/** The turn from the motion's skeleton's reference pose: the motion's own pose, on bones that are in that skeleton's
	 *  reference pose (a model made with another character's wings in that character's reference pose) */
	ReferencePose,
};

/** (1.12) How a motion of the sets plays on */
UENUM()
enum class EKawaiiPoseAnimSetLoop : uint8
{
	/** On a loop when its last frame meets its first, else holding its end */
	Auto,
	/** On a loop */
	Loop,
	/** Holding its end */
	HoldEnd,
};

/** (1.12, the editor's preview) In battle or not, for the preview's pick */
UENUM()
enum class EKawaiiPoseAnimSetPreviewState : uint8
{
	/** In battle while the preview plays an animation whose name starts with B_ */
	Auto,
	Field,
	Battle,
};

/** (1.12, Dynamic Motions) The bones' motion taken from animation sets (EndAnimSet assets: the game's sets of an animation
 *  pack, a name for each animation, as a character's Battle00 or Neutral00; the game's own, or ones a skin cooks in): the
 *  motion of the name of what the character plays. Each evaluation the node plays the motion picked for what the character
 *  plays now: the first of Motions whose Playing matches it, else (Same Names) a motion of that very name in the sets,
 *  else the moving one while the character moves, else its idle (in battle the battle ones first). A new pick cross-fades
 *  over Blend Seconds from the one before. While a motion of the sets plays, the node's own Pose Animation waits; its
 *  waves still run. The game's "pose_animset" (Create a Character System 3.20.0). In this editor the preview plays them:
 *  what the preview plays (the animation editor's animation, the montage, or the AnimBlueprint's animation player of the
 *  most weight) is what the character plays; the sets must be in this project at their game paths. */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPoseAnimSet
{
	GENERATED_BODY()

	/** The EndAnimSet assets (up to 16), searched in order, e.g. Neo Bahamut's /Game/Motion/Summon/SU2050_NeoBahamut/Battle00
	 *  (none: off). The game loads them at these paths */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions", meta = (AllowedClasses = "EndAnimSet"))
	TArray<TSoftObjectPtr<UObject>> Sets;

	/** What the character plays -> the sets' motion its bones play (up to 512; the first that matches wins) */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions", meta = (TitleProperty = "Playing"))
	TArray<FKawaiiPoseAnimSetMotion> Motions;

	/** A motion of the sets of the very name of what the character plays plays then */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions")
	bool bSameNames = true;

	/** The sets' motion when nothing else is picked (and Moving is not, or the character does not move), e.g. N_Idle01_1 */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions")
	FString Idle;

	/** The same in battle (none: Idle), e.g. B_Idle01_1 */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions")
	FString BattleIdle;

	/** The sets' motion while the character moves (faster than Moving Speed) with nothing else picked */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions")
	FString Moving;

	/** The same in battle (none: Moving) */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions")
	FString BattleMoving;

	/** (cm/s) */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions", meta = (ClampMin = "0", ClampMax = "10000"))
	float MovingSpeed = 40.0f;

	/** A new pick's cross-fade from the one before (seconds) */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions", meta = (ClampMin = "0", ClampMax = "5"))
	float BlendSeconds = 0.25f;

	/** How fast the motions play (negative: backwards) */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions", meta = (ClampMin = "-100", ClampMax = "100"))
	float Speed = 1.0f;

	/** How much of them (0 - 1; 0: off) */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions", meta = (ClampMin = "0", ClampMax = "1"))
	float Weight = 1.0f;

	/** Their turns added to the pose; off: their rotations take the place of the pose's */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions")
	bool bAdditive = true;

	/** What an additive motion's turn is taken from */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions", meta = (EditCondition = "bAdditive"))
	EKawaiiPoseAnimSetBase AdditiveBase = EKawaiiPoseAnimSetBase::FirstFrame;

	UPROPERTY(EditAnywhere, Category = "Dynamic Motions")
	EKawaiiPoseAnimSetLoop Loop = EKawaiiPoseAnimSetLoop::Auto;

	/** KH3-style sync (as the Customization parts' synced motions): a motion picked for what the character plays (its own
	 *  name in the sets, or a pair's) plays in step with it, at the time the character is at in its animation, instead of
	 *  from its start */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions")
	bool bSync = false;

	/** (the editor) The sets' motion the preview plays whatever the preview plays (empty: the one picked for it). The game
	 *  leaves it out */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions|Preview")
	FString PreviewMotion;

	/** (the editor) The character's animation the preview's pick is made for, as if the character played it (e.g. one of
	 *  Sephiroth's, B_NAttack01_0, to see the motion its pair gives; empty: what the preview plays). The game leaves it out */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions|Preview")
	FString PreviewPlaying;

	/** (the editor) In battle or not, for the preview's pick */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions|Preview")
	EKawaiiPoseAnimSetPreviewState PreviewState = EKawaiiPoseAnimSetPreviewState::Auto;
};

/** (1.10, KawaiiPhysics' SyncBone) Which way of an axis a sync bone's move is let through */
UENUM()
enum class ESyncBoneDirection : uint8
{
	/** Both ways */
	Both,
	/** Only as the bone goes the axis' way */
	Positive,
	/** Only as it goes against it */
	Negative,
	/** None of the move along this axis */
	None,
};

/** (1.10) A target of a sync bone: a bone of the node's chains and, with Include Child Bones, the chain's bones below it */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPhysicsSyncTargetRoot
{
	GENERATED_BODY()

	/** A bone of the node's chains (its chain's root follows its animation: a root here is not moved) */
	UPROPERTY(EditAnywhere, Category = "Sync Bone")
	FBoneReference Bone;

	/** The chain's bones below it too */
	UPROPERTY(EditAnywhere, Category = "Sync Bone")
	bool bIncludeChildBones = true;

	/** The part of the move each bone gets by its place below this bone (0: this bone, 1: the farthest below it); no
	 *  keys: all of it */
	UPROPERTY(EditAnywhere, Category = "Sync Bone", meta = (XAxisName = "LengthRate", YAxisName = "Scale"))
	FRuntimeFloatCurve ScaleCurveByBoneLengthRate;
};

/** (1.10, KawaiiPhysics' SyncBone) An animated bone (a knee) whose move from its reference pose goes onto the pose of
 *  the target roots' chain bones, each kept at its length from its parent, before the physics runs: the physics pulls
 *  them toward it, so a coat's strips follow the leg instead of the leg going through them. The game's "sync_bones"
 *  (Create a Character System 3.17.0) */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPhysicsSyncBone
{
	GENERATED_BODY()

	/** The bone followed (one the animation moves, not a bone of the node's chains) */
	UPROPERTY(EditAnywhere, Category = "Sync Bone")
	FBoneReference Bone;

	/** The bones that follow it (up to 64) */
	UPROPERTY(EditAnywhere, Category = "Sync Bone", meta = (TitleProperty = "Bone"))
	TArray<FKawaiiPhysicsSyncTargetRoot> TargetRoots;

	/** How much of its move along each axis of the component (+X the model's front, +Y its right, +Z up), 0 - 1 */
	UPROPERTY(EditAnywhere, Category = "Sync Bone", meta = (ClampMin = "0", ClampMax = "1"))
	FVector GlobalScale = FVector::OneVector;

	/** The move times this at its length (cm); no keys: all of it */
	UPROPERTY(EditAnywhere, Category = "Sync Bone", meta = (XAxisName = "Distance", YAxisName = "Scale"))
	FRuntimeFloatCurve ScaleCurveByDeltaDistance;

	UPROPERTY(EditAnywhere, Category = "Sync Bone")
	ESyncBoneDirection ApplyDirectionX = ESyncBoneDirection::Both;

	UPROPERTY(EditAnywhere, Category = "Sync Bone")
	ESyncBoneDirection ApplyDirectionY = ESyncBoneDirection::Both;

	UPROPERTY(EditAnywhere, Category = "Sync Bone")
	ESyncBoneDirection ApplyDirectionZ = ESyncBoneDirection::Both;

	/** Less of the move the farther a bone is from the synced bone */
	UPROPERTY(EditAnywhere, Category = "Sync Bone|Distance Attenuation", meta = (InlineEditConditionToggle))
	bool bEnableDistanceAttenuation = false;

	/** Nearer than this: all of the move (cm) */
	UPROPERTY(EditAnywhere, Category = "Sync Bone|Distance Attenuation", meta = (EditCondition = "bEnableDistanceAttenuation", ClampMin = "0"))
	float AttenuationInnerRadius = 0.0f;

	/** Farther than this: the move less Max Attenuation Rate of it (cm) */
	UPROPERTY(EditAnywhere, Category = "Sync Bone|Distance Attenuation", meta = (EditCondition = "bEnableDistanceAttenuation", ClampMin = "0"))
	float AttenuationOuterRadius = 0.0f;

	/** 0: no attenuation, 1: none of the move out there */
	UPROPERTY(EditAnywhere, Category = "Sync Bone|Distance Attenuation", meta = (EditCondition = "bEnableDistanceAttenuation", ClampMin = "0", ClampMax = "1"))
	float MaxAttenuationRate = 1.0f;
};

// ---- (1.11) the rest of KawaiiPhysics 1.21 (Create a Character System 3.18.0) ------------------------------------

/** (1.11) The kind of an external force (KawaiiPhysics' ExternalForces; UE 4.26 has no instanced structs: one struct and
 *  its kind) */
UENUM()
enum class EKawaiiPhysicsExternalForceType : uint8
{
	/** A push on the bones' places (Force Dir, cm/s; with an Interval, once each interval) */
	Basic,
	/** A pull down, added to the bones' speed */
	Gravity,
	/** A push that changes over time (Force Curve, looping) */
	Curve,
	/** The level's wind on each bone (its Wind Directional Sources; in the game also the entry's World Wind) */
	Wind,
	/** A wind of its own: a constant push, a sway, a ripple down the chains, a slow swell, noise and gusts */
	ProceduralWind,
};

/** (1.11) The space an external force's push is in */
UENUM()
enum class EKawaiiPhysicsExternalForceSpace : uint8
{
	WorldSpace,
	ComponentSpace,
	BoneSpace,
};

/** (1.11) How a Curve force reads its curve over a frame */
UENUM()
enum class EKawaiiPhysicsCurveEvaluateType : uint8
{
	/** At the frame's time */
	Single,
	/** The average over the frame's parts (Substep Count) */
	Average,
	Max,
	Min,
};

/** (1.11) Where a Procedural Wind's settings, clock and gusts come from */
UENUM()
enum class EKawaiiPhysicsWindSource : uint8
{
	/** Its own */
	Local,
	/** The character's shared wind of its Shared Wind Tag (an entry's Shared Winds) */
	Shared,
	/** That when the character has one, else its own */
	Auto,
};

/** (1.11) A key of a Curve force: its push (cm/s) at a time (s) */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPhysicsVectorKey
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "ExternalForce", meta = (ClampMin = "0"))
	float Time = 0.0f;

	UPROPERTY(EditAnywhere, Category = "ExternalForce")
	FVector Value = FVector::ZeroVector;
};

/** (1.11) One of KawaiiPhysics' external forces (the game's "external_forces"): it moves the bones it applies to every
 *  step, in its space, times its rate along the chain */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPhysicsExternalForce
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "ExternalForce")
	EKawaiiPhysicsExternalForceType Type = EKawaiiPhysicsExternalForceType::Basic;

	UPROPERTY(EditAnywhere, Category = "ExternalForce")
	bool bIsEnabled = true;

	/** Only these bones (none: every bone of the node) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce")
	TArray<FBoneReference> ApplyBoneFilter;

	/** Never these bones */
	UPROPERTY(EditAnywhere, Category = "ExternalForce")
	TArray<FBoneReference> IgnoreBoneFilter;

	/** The space its push is in (Gravity and Wind: always the world's) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce", meta = (EditCondition = "Type != EKawaiiPhysicsExternalForceType::Gravity && Type != EKawaiiPhysicsExternalForceType::Wind"))
	EKawaiiPhysicsExternalForceSpace ExternalForceSpace = EKawaiiPhysicsExternalForceSpace::WorldSpace;

	/** A scale drawn between these each frame (not for a Procedural Wind) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce")
	FFloatInterval RandomForceScaleRange = FFloatInterval(1.0f, 1.0f);

	/** Along each chain (0 its root, 1 its end), the part of the force each bone gets (no keys: all of it) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce", meta = (XAxisName = "LengthRate", YAxisName = "Rate"))
	FRuntimeFloatCurve ForceRateByBoneLengthRate;

	/** Basic: the push (cm/s on the bones' places) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce|Basic", meta = (EditCondition = "Type == EKawaiiPhysicsExternalForceType::Basic"))
	FVector ForceDir = FVector::ZeroVector;

	/** Basic: more than 0, once each interval (s) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce|Basic", meta = (ClampMin = "0", EditCondition = "Type == EKawaiiPhysicsExternalForceType::Basic"))
	float Interval = 0.0f;

	/** Gravity: the character's gravity direction (down in the game: it has no other) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce|Gravity", meta = (EditCondition = "Type == EKawaiiPhysicsExternalForceType::Gravity"))
	bool bUseCharacterGravityDirection = false;

	/** Gravity: times the size of the character's gravity (980; the game's character, none in the editor's preview) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce|Gravity", meta = (EditCondition = "Type == EKawaiiPhysicsExternalForceType::Gravity"))
	bool bUseCharacterGravityScale = false;

	UPROPERTY(EditAnywhere, Category = "ExternalForce|Gravity", meta = (EditCondition = "Type == EKawaiiPhysicsExternalForceType::Gravity"))
	bool bUseOverrideGravityDirection = false;

	UPROPERTY(EditAnywhere, Category = "ExternalForce|Gravity", meta = (EditCondition = "Type == EKawaiiPhysicsExternalForceType::Gravity && bUseOverrideGravityDirection"))
	FVector OverrideGravityDirection = FVector::ZeroVector;

	/** Curve: its push over time (keys in time order, straight lines between them; it loops) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce|Curve", meta = (EditCondition = "Type == EKawaiiPhysicsExternalForceType::Curve"))
	TArray<FKawaiiPhysicsVectorKey> ForceCurve;

	UPROPERTY(EditAnywhere, Category = "ExternalForce|Curve", meta = (EditCondition = "Type == EKawaiiPhysicsExternalForceType::Curve"))
	EKawaiiPhysicsCurveEvaluateType CurveEvaluateType = EKawaiiPhysicsCurveEvaluateType::Single;

	/** Curve: the frame cut in this many parts for Average, Max and Min */
	UPROPERTY(EditAnywhere, Category = "ExternalForce|Curve", meta = (ClampMin = "1", ClampMax = "1000", EditCondition = "Type == EKawaiiPhysicsExternalForceType::Curve"))
	int32 SubstepCount = 10;

	/** Curve, Procedural Wind: how fast its time runs */
	UPROPERTY(EditAnywhere, Category = "ExternalForce", meta = (ClampMin = "0", ClampMax = "1000"))
	float TimeScale = 1.0f;

	/** Wind, Procedural Wind: the noise of its direction (degrees) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce", meta = (ClampMin = "0", ClampMax = "180"))
	float WindDirectionNoiseAngle = 0.0f;

	/** Procedural Wind: its own, or the character's shared wind */
	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	EKawaiiPhysicsWindSource WindSource = EKawaiiPhysicsWindSource::Local;

	/** Procedural Wind: the shared wind's tag (a gameplay tag's name) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	FString SharedWindTag = TEXT("KawaiiPhysics.Shared.Default");

	/** Procedural Wind: its direction (zero: +X) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	FVector WindDirection = FVector(1.0f, 0.0f, 0.0f);

	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (ClampMin = "0.01", EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	float WindDirectionNoisePeriod = 1.0f;

	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (ClampMin = "0", EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	float ConstantForce = 0.0f;

	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (ClampMin = "0", EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	float SwayForce = 0.0f;

	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (ClampMin = "0.01", EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	float SwayPeriod = 1.0f;

	/** (degrees) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	float SwayPhaseOffset = 0.0f;

	/** A wave down the chains */
	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (ClampMin = "0", EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	float RippleForce = 0.0f;

	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (ClampMin = "0.01", EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	float RipplePeriod = 1.0f;

	/** (degrees) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	float RipplePhaseOffset = 0.0f;

	/** (degrees at the chains' ends) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	float RippleTipPhaseDelay = 180.0f;

	/** A slow swell between these */
	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	FFloatInterval StrengthCycleRange = FFloatInterval(1.0f, 1.0f);

	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (ClampMin = "0.01", EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	float StrengthCyclePeriod = 10.0f;

	/** (degrees) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	float StrengthCyclePhaseOffset = 0.0f;

	/** Seeded smooth noise */
	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (ClampMin = "0", EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	float RandomForce = 0.0f;

	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (ClampMin = "0.01", EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	float RandomForcePeriod = 0.5f;

	UPROPERTY(EditAnywhere, Category = "ExternalForce|Procedural Wind", meta = (EditCondition = "Type == EKawaiiPhysicsExternalForceType::ProceduralWind"))
	int32 Seed = 0;
};

/** (1.11) The axis a node's shapes are mirrored across (None: no mirroring) */
UENUM()
enum class EKawaiiPhysicsMirrorAxis : uint8
{
	None,
	X,
	/** The model's left and right */
	Y,
	Z,
};

/** (1.11) Two bones that mirror each other */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPhysicsMirrorBonePair
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Mirror")
	FName Left;

	UPROPERTY(EditAnywhere, Category = "Mirror")
	FName Right;
};

/** (1.11) Two name parts that mirror each other ("L_" and "R_") */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPhysicsMirrorNamePart
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Mirror")
	FString Left;

	UPROPERTY(EditAnywhere, Category = "Mirror")
	FString Right;
};

/** (1.11) KawaiiPhysics' MirrorDataTableForLimits: each shape of the node (its own, its sets', its physics asset's) on a
 *  bone with a mirror bone copied onto that bone, mirrored across the axis (the game's "mirror_data_table_for_limits") */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPhysicsMirrorLimits
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Mirror")
	EKawaiiPhysicsMirrorAxis MirrorAxis = EKawaiiPhysicsMirrorAxis::None;

	UPROPERTY(EditAnywhere, Category = "Mirror", meta = (EditCondition = "MirrorAxis != EKawaiiPhysicsMirrorAxis::None"))
	TArray<FKawaiiPhysicsMirrorBonePair> BonePairs;

	/** Name prefixes (none of these and no pairs: L_ / R_ and _L / _R) */
	UPROPERTY(EditAnywhere, Category = "Mirror", meta = (EditCondition = "MirrorAxis != EKawaiiPhysicsMirrorAxis::None"))
	TArray<FKawaiiPhysicsMirrorNamePart> Prefixes;

	UPROPERTY(EditAnywhere, Category = "Mirror", meta = (EditCondition = "MirrorAxis != EKawaiiPhysicsMirrorAxis::None"))
	TArray<FKawaiiPhysicsMirrorNamePart> Suffixes;

	/** A bone that has a shape of its own gets no mirrored one */
	UPROPERTY(EditAnywhere, Category = "Mirror", meta = (EditCondition = "MirrorAxis != EKawaiiPhysicsMirrorAxis::None"))
	bool bSkipMirroredBoneWithExistingCollision = true;
};

/** (1.11) A KawaiiPhysics settings multiplier: each physics setting times its factor (1: as it is) */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPhysicsSettingsMultiplier
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Settings Multiplier", meta = (ClampMin = "0"))
	float Damping = 1.0f;

	UPROPERTY(EditAnywhere, Category = "Settings Multiplier", meta = (ClampMin = "0"))
	float Stiffness = 1.0f;

	UPROPERTY(EditAnywhere, Category = "Settings Multiplier", meta = (ClampMin = "0"))
	float WorldDampingLocation = 1.0f;

	UPROPERTY(EditAnywhere, Category = "Settings Multiplier", meta = (ClampMin = "0"))
	float WorldDampingRotation = 1.0f;

	UPROPERTY(EditAnywhere, Category = "Settings Multiplier", meta = (ClampMin = "0"))
	float Radius = 1.0f;

	UPROPERTY(EditAnywhere, Category = "Settings Multiplier", meta = (ClampMin = "0"))
	float LimitAngle = 1.0f;
};

/** (1.11) What an animation trigger does (KawaiiPhysics' AnimNotifies) */
UENUM()
enum class EKawaiiPhysicsTriggerType : uint8
{
	/** Its external forces on the nodes (a pulse: for one step; a state: while it lasts) */
	AddExternalForce,
	/** The nodes' alpha while it lasts (a state) */
	SetAlpha,
	/** The nodes' physics settings times its factors */
	SettingsMultiplier,
	/** A gust in the nodes' procedural winds (or the entry's shared wind) */
	TriggerGust,
	/** A wind preset on the nodes' procedural winds */
	WindPreset,
};

/** (1.11) One of an entry's animation triggers (the game's "animation_triggers"): KawaiiPhysics' AnimNotifies, by the
 *  montage the character's mesh plays and its time in it (the game runs them; the editor's preview does not) */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPhysicsAnimationTrigger
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Animation Trigger")
	EKawaiiPhysicsTriggerType Type = EKawaiiPhysicsTriggerType::AddExternalForce;

	/** The montages' names (case does not matter; "Name*" every name starting so) */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger")
	TArray<FString> Montages;

	/** Once, as the montage's time passes At (a pulse); else while it is from Start to End (a state). Trigger Gust and Wind
	 *  Preset are pulses (at Start when this is off); Set Alpha is a state */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger")
	bool bPulse = false;

	/** (s into the montage) */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger", meta = (ClampMin = "0", EditCondition = "bPulse"))
	float At = 0.0f;

	/** (s) */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger", meta = (ClampMin = "0", EditCondition = "!bPulse"))
	float Start = 0.0f;

	/** (s; below 0: to the montage's end) */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger", meta = (ClampMin = "-1", EditCondition = "!bPulse"))
	float End = -1.0f;

	/** The nodes whose Kawaii Physics Tag matches one of these (none: every node of the entry) */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger")
	TArray<FString> FilterTags;

	/** Off: a node tagged "Hair.Front" matches "Hair" too */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger")
	bool bFilterExactMatch = false;

	/** Add External Force: its forces */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger|Add External Force", meta = (EditCondition = "Type == EKawaiiPhysicsTriggerType::AddExternalForce"))
	TArray<FKawaiiPhysicsExternalForce> ExternalForces;

	/** Set Alpha: from the anim instance's curve (Curve Name), else Constant Alpha */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger|Set Alpha", meta = (EditCondition = "Type == EKawaiiPhysicsTriggerType::SetAlpha"))
	bool bAlphaFromCurve = false;

	UPROPERTY(EditAnywhere, Category = "Animation Trigger|Set Alpha", meta = (ClampMin = "0", ClampMax = "1", EditCondition = "Type == EKawaiiPhysicsTriggerType::SetAlpha"))
	float ConstantAlpha = 1.0f;

	/** Set Alpha, Settings Multiplier: the anim instance's curve */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger")
	FString CurveName;

	/** Set Alpha, Settings Multiplier: the alpha (weight) when the anim instance has no such curve */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger", meta = (ClampMin = "0", ClampMax = "1"))
	float DefaultIfNoCurve = 1.0f;

	/** Settings Multiplier: the factors */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger|Settings Multiplier", meta = (EditCondition = "Type == EKawaiiPhysicsTriggerType::SettingsMultiplier"))
	FKawaiiPhysicsSettingsMultiplier SettingsScale;

	/** Settings Multiplier (a state): its weight from the curve (Curve Name), else its blend in and out */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger|Settings Multiplier", meta = (EditCondition = "Type == EKawaiiPhysicsTriggerType::SettingsMultiplier"))
	bool bWeightFromCurve = false;

	/** Settings Multiplier (a pulse): how long it lasts (s) */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger|Settings Multiplier", meta = (ClampMin = "0", EditCondition = "Type == EKawaiiPhysicsTriggerType::SettingsMultiplier"))
	float Duration = 1.0f;

	UPROPERTY(EditAnywhere, Category = "Animation Trigger|Settings Multiplier", meta = (ClampMin = "0", EditCondition = "Type == EKawaiiPhysicsTriggerType::SettingsMultiplier"))
	float BlendInTime = 0.2f;

	UPROPERTY(EditAnywhere, Category = "Animation Trigger|Settings Multiplier", meta = (ClampMin = "0", EditCondition = "Type == EKawaiiPhysicsTriggerType::SettingsMultiplier"))
	float BlendOutTime = 0.2f;

	/** Trigger Gust: its strength and its rise, hold and decay (s) */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger|Trigger Gust", meta = (EditCondition = "Type == EKawaiiPhysicsTriggerType::TriggerGust"))
	float Strength = 0.0f;

	UPROPERTY(EditAnywhere, Category = "Animation Trigger|Trigger Gust", meta = (ClampMin = "0", EditCondition = "Type == EKawaiiPhysicsTriggerType::TriggerGust"))
	float RiseTime = 0.0f;

	UPROPERTY(EditAnywhere, Category = "Animation Trigger|Trigger Gust", meta = (ClampMin = "0", EditCondition = "Type == EKawaiiPhysicsTriggerType::TriggerGust"))
	float HoldTime = 0.0f;

	UPROPERTY(EditAnywhere, Category = "Animation Trigger|Trigger Gust", meta = (ClampMin = "0", EditCondition = "Type == EKawaiiPhysicsTriggerType::TriggerGust"))
	float DecayTime = 0.0f;

	/** Trigger Gust: the world's direction (zero: the winds' own) */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger|Trigger Gust", meta = (EditCondition = "Type == EKawaiiPhysicsTriggerType::TriggerGust"))
	FVector GustDirection = FVector::ZeroVector;

	/** Trigger Gust: the entry's shared wind of Shared Wind Tag (all its users), not the nodes' own winds */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger|Trigger Gust", meta = (EditCondition = "Type == EKawaiiPhysicsTriggerType::TriggerGust"))
	bool bGustToSharedWind = false;

	UPROPERTY(EditAnywhere, Category = "Animation Trigger|Trigger Gust", meta = (EditCondition = "Type == EKawaiiPhysicsTriggerType::TriggerGust"))
	FString SharedWindTag = TEXT("KawaiiPhysics.Shared.Default");

	/** Wind Preset: Breeze, Strong, Storm or one of the compat files' "kawaii_wind_presets" */
	UPROPERTY(EditAnywhere, Category = "Animation Trigger|Wind Preset", meta = (EditCondition = "Type == EKawaiiPhysicsTriggerType::WindPreset"))
	FString Preset;
};

/** (1.11) One of an entry's shared winds (the game's "shared_winds", KawaiiPhysics' Shared Publisher): one procedural wind,
 *  its clock and gusts, for every Procedural Wind of the character's meshes whose Wind Source is Shared or Auto and whose
 *  Shared Wind Tag is its */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPhysicsSharedWind
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Shared Wind")
	FString SharedWindTag = TEXT("KawaiiPhysics.Shared.Default");

	UPROPERTY(EditAnywhere, Category = "Shared Wind")
	bool bIsEnabled = true;

	/** Its procedural wind's settings (its Type, filters and Wind Source are not used) */
	UPROPERTY(EditAnywhere, Category = "Shared Wind")
	FKawaiiPhysicsExternalForce Wind;
};

/** (1.11) An entry's own wind source (the game's "world_wind"), for the nodes' Enable Wind and their Wind forces: a
 *  directional source as UE's Wind Directional Source */
USTRUCT(BlueprintType)
struct KAWAIIPHYSICS_API FKawaiiPhysicsWorldWind
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "World Wind")
	bool bEnabled = false;

	/** Only where the level has no wind source of its own; off: mixed with the level's */
	UPROPERTY(EditAnywhere, Category = "World Wind", meta = (EditCondition = "bEnabled"))
	bool bOnlyWithoutLevelWind = true;

	/** The world's direction (zero: +X) */
	UPROPERTY(EditAnywhere, Category = "World Wind", meta = (EditCondition = "bEnabled"))
	FVector Direction = FVector(1.0f, 0.0f, 0.0f);

	/** (cm/s) */
	UPROPERTY(EditAnywhere, Category = "World Wind", meta = (ClampMin = "0", EditCondition = "bEnabled"))
	float Speed = 0.0f;

	/** Its weight against the level's sources */
	UPROPERTY(EditAnywhere, Category = "World Wind", meta = (ClampMin = "0", EditCondition = "bEnabled"))
	float Strength = 1.0f;

	UPROPERTY(EditAnywhere, Category = "World Wind", meta = (ClampMin = "0", EditCondition = "bEnabled"))
	float MinGustAmount = 0.0f;

	UPROPERTY(EditAnywhere, Category = "World Wind", meta = (ClampMin = "0", EditCondition = "bEnabled"))
	float MaxGustAmount = 0.0f;
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

struct FKawaiiAnimSetPreview;   // (1.12) the animation sets' motions as the preview plays them (AnimNode_KawaiiPhysics.cpp)

/** (1.12) Holds them (a copy of a node starts with none) */
struct KAWAIIPHYSICS_API FKawaiiAnimSetPreviewHolder
{
	FKawaiiAnimSetPreviewHolder();
	FKawaiiAnimSetPreviewHolder(const FKawaiiAnimSetPreviewHolder&);
	FKawaiiAnimSetPreviewHolder& operator=(const FKawaiiAnimSetPreviewHolder&);
	~FKawaiiAnimSetPreviewHolder();

	FKawaiiAnimSetPreview* Get() const { return Preview; }
	void Reset(FKawaiiAnimSetPreview* InPreview = nullptr);

private:
	FKawaiiAnimSetPreview* Preview = nullptr;
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

	/** (1.10) Each fixed step's collision shapes between their places at the last frame's end and this frame's, as the
	 *  bones' pose is (KawaiiPhysics puts them at this frame's places for every step: a fast leg jumped past the cloth) */
	UPROPERTY(EditAnywhere, Category = "Advanced Physics Settings", meta = (EditCondition = "bUseFixedSubstepping"))
	bool bInterpolateLimitsInSubsteps = true;

	/** (1.10) A bone a shape moved past in one step (inside it, on the other side of its axis than it was) is put back out
	 *  on the side it was on, not pushed on through */
	UPROPERTY(EditAnywhere, Category = "Advanced Physics Settings")
	bool bKeepCollisionSide = false;

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

	// ---- (1.10) sync bones ----------------------------------------------------------------
	/** Animated bones whose moves the chains' pose follows (up to 16): a coat's strips follow a knee. The game's
	 *  "sync_bones" (Create a Character System 3.17.0) */
	UPROPERTY(EditAnywhere, Category = "Sync Bone", meta = (TitleProperty = "Bone"))
	TArray<FKawaiiPhysicsSyncBone> SyncBones;

	// ---- (1.9) Dynamic Motions: the bones' own motion, the physics on top -----------------------
	/** Waves that turn the bones to and fro in their pose before the physics runs (up to 8): a tail's sway, a wing's slow
	 *  beat. The physics pulls each bone toward its turned place, so the chain moves on its own and still swings with the
	 *  character's moves, collides and keeps its limits. The game's "pose_waves" (Create a Character System 3.15.0) */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions")
	TArray<FKawaiiPoseWave> PoseWaves;

	/** A looping key animation of the bones, played on their pose before the waves and the physics. The game's
	 *  "pose_animation" (Create a Character System 3.15.0) */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions")
	FKawaiiPoseAnimation PoseAnimation;

	/** (1.12) The bones' motion from animation sets (EndAnimSet assets): the sets' motion of the name of what the character
	 *  plays (or a pair's), played on their pose before the waves and the physics; KH3-style in step with it with Sync.
	 *  The game's "pose_animset" (Create a Character System 3.20.0) */
	UPROPERTY(EditAnywhere, Category = "Dynamic Motions")
	FKawaiiPoseAnimSet PoseAnimSet;

	// ---- (1.11) external forces and wind -------------------------------------------------------
	/** KawaiiPhysics' external forces (up to 16): Basic, Gravity, Curve, Wind, Procedural Wind. The game's "external_forces"
	 *  (Create a Character System 3.18.0) */
	UPROPERTY(EditAnywhere, Category = "ExternalForce", meta = (TitleProperty = "Type"))
	TArray<FKawaiiPhysicsExternalForce> ExternalForces;

	/** The level's wind on the bones (its Wind Directional Sources; in the game also the entry's World Wind) */
	UPROPERTY(EditAnywhere, Category = "Wind")
	bool bEnableWind = false;

	UPROPERTY(EditAnywhere, Category = "Wind", meta = (EditCondition = "bEnableWind"))
	float WindScale = 1.0f;

	/** (degrees) */
	UPROPERTY(EditAnywhere, Category = "Wind", meta = (ClampMin = "0", ClampMax = "180", EditCondition = "bEnableWind"))
	float WindDirectionNoiseAngle = 0.0f;

	// ---- (1.11) tag, sets, the physics asset, mirroring ------------------------------------------------
	/** A gameplay tag's name ("Hair.Front") the entry's animation triggers pick the node by */
	UPROPERTY(EditAnywhere, Category = "Tag")
	FString KawaiiPhysicsTag;

	/** The compat files' "kawaii_limits_sets" (by name) whose shapes the node gets in the game (the editor's preview has
	 *  not got them: they are in the files) */
	UPROPERTY(EditAnywhere, Category = "Limits Data(Experimental)")
	TArray<FString> GameLimitsSets;

	/** The compat files' "kawaii_bone_constraints_sets" (by name): their bone constraints and regex patterns, in the game */
	UPROPERTY(EditAnywhere, Category = "Bone Constraint (Experimental)")
	TArray<FString> GameBoneConstraintsSets;

	/** The bodies of the model's own physics asset as shapes on their bones (spheres, capsules, tapered capsules, boxes) */
	UPROPERTY(EditAnywhere, Category = "Physics Asset Limits")
	bool bUseModelPhysicsAssetForLimits = false;

	/** Or these bodies (a physics asset of the game: it must be loaded in the game when the mesh shows) */
	UPROPERTY(EditAnywhere, Category = "Physics Asset Limits", meta = (EditCondition = "!bUseModelPhysicsAssetForLimits"))
	TSoftObjectPtr<UPhysicsAsset> PhysicsAssetForLimits;

	/** Each shape on a bone with a mirror bone copied onto that bone, mirrored */
	UPROPERTY(EditAnywhere, Category = "Mirror Limits")
	FKawaiiPhysicsMirrorLimits MirrorLimits;

	// ---- (1.11) shared and world collision (the game runs them; the editor's preview has no world) ----------------------
	/** Its shapes go to the character's other meshes (and to what is attached to the character) by the group tag */
	UPROPERTY(EditAnywhere, Category = "Shared Collision")
	bool bSharedCollisionSource = false;

	/** It collides with the shapes the character's other meshes share under the group tag */
	UPROPERTY(EditAnywhere, Category = "Shared Collision")
	bool bUseSharedCollision = false;

	UPROPERTY(EditAnywhere, Category = "Shared Collision")
	FString SharedCollisionGroupTag = TEXT("KawaiiPhysics.Shared.Default");

	/** A sphere sweep a bone a step through the level's static and dynamic objects */
	UPROPERTY(EditAnywhere, Category = "World Collision")
	bool bAllowWorldCollision = false;

	UPROPERTY(EditAnywhere, Category = "World Collision", meta = (EditCondition = "bAllowWorldCollision"))
	bool bIgnoreSelfComponent = true;

	/** The game's budget: at most this many sweeps a frame (and 256 for every mesh together) */
	UPROPERTY(EditAnywhere, Category = "World Collision", meta = (ClampMin = "0", ClampMax = "4096", EditCondition = "bAllowWorldCollision"))
	int32 WorldCollisionMaxSweepsPerFrame = 96;

	/** The level's simple collision near the mesh as shapes (its static meshes'; a convex hull as its bounding box) */
	UPROPERTY(EditAnywhere, Category = "World Collision")
	bool bUseSimpleWorldCollision = false;

	/** (s) */
	UPROPERTY(EditAnywhere, Category = "World Collision", meta = (ClampMin = "0", ClampMax = "60"))
	float SimpleWorldCollisionGatherInterval = 0.2f;

	/** Off: 1.5 times the mesh's bounds */
	UPROPERTY(EditAnywhere, Category = "World Collision")
	bool bOverrideSimpleWorldCollisionGatherRadius = false;

	/** (cm) */
	UPROPERTY(EditAnywhere, Category = "World Collision", meta = (ClampMin = "1", EditCondition = "bOverrideSimpleWorldCollisionGatherRadius"))
	float SimpleWorldCollisionGatherRadius = 200.0f;

	/** With the simple world collision: the floor as a box under the character too */
	UPROPERTY(EditAnywhere, Category = "World Collision", meta = (EditCondition = "bUseSimpleWorldCollision"))
	bool bSimpleWorldCollisionGroundCollision = true;

	/** The floor alone (no level shapes) */
	UPROPERTY(EditAnywhere, Category = "World Collision")
	bool bGroundCollision = false;

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
	// (1.11) the level's wind for the preview, read on the game thread
	virtual bool HasPreUpdate() const override { return true; }
	virtual void PreUpdate(const UAnimInstance* InAnimInstance) override;

	/** The simulated bones of the last evaluation (the editor's drawing) */
	void GetDebugBones(TArray<FKawaiiPhysicsDebugBone>& OutBones) const;
	/** Why the node does not run (empty: it runs) */
	FString GetProblem() const;
	/** The node as one of the game's "kawaii" nodes (JSON text, an object) */
	FString ToGameJson(const FString& Indent = TEXT("")) const;
	/** (1.12) What the preview plays and the animation sets' motion the node plays for it (empty: no sets) */
	FString GetAnimSetText() const;
	/** (the editor, after it copies new settings in) the bone references are made again at the next evaluation */
	void MarkBonesDirty() { bBonesDirty = true; }

private:
	virtual void InitializeBoneReferences(const FBoneContainer& RequiredBones) override;
	void ApplyLimitsDataAsset(const FBoneContainer& RequiredBones);
	void UpdateShapePlaces(FComponentSpacePoseContext& Output, const FBoneContainer& BoneContainer);

	FKawaiiPhysicsSolverHolder Solver;
	// (1.12) the animation sets' motions (picked in PreUpdate, the game thread; played in the evaluation)
	FKawaiiAnimSetPreviewHolder AnimSetPreview;
	double NextAnimSetLoad = 0.0;
	float DeltaTime = 0.0f;
	// (1.11) the level's wind at the mesh (PreUpdate)
	FVector PreviewWindDirection = FVector(1.0f, 0.0f, 0.0f);
	float PreviewWindSpeed = 0.0f;
	float PreviewWindMinGust = 0.0f;
	float PreviewWindMaxGust = 0.0f;
	bool bPreviewWind = false;
	// (1.11) the node's physics asset when loaded (PreUpdate, the game thread)
	TWeakObjectPtr<UPhysicsAsset> ResolvedPhysicsAsset;
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
	/** (1.11) "disable_kinedriver" */
	bool bDisableKineDriver = false;
	TArray<FString> DisableKineDriverAssets;
	/** (1.11) "animation_triggers", "shared_winds", "world_wind" */
	TArray<FKawaiiPhysicsAnimationTrigger> AnimationTriggers;
	TArray<FKawaiiPhysicsSharedWind> SharedWinds;
	FKawaiiPhysicsWorldWind WorldWind;
	TArray<FAnimNode_KawaiiPhysics> Nodes;
};

/** (1.8) The "kawaii" entries of a Create a Character System compat file, read with the game mod's own parser (as the
 *  game reads them; every entry, whether its paks are installed or not). OutMessages: what the parser said of them.
 *  False when the text is not such a file. */
KAWAIIPHYSICS_API bool ReadKawaiiGameEntries(const FString& JsonText, TArray<FKawaiiPhysicsGameEntry>& OutEntries, FString& OutMessages);

/** (1.11) An entry's animation triggers, shared winds and wind source as the game's keys ("world_wind", "shared_winds",
 *  "animation_triggers"), each line Indent first and ending in a comma (to go before its "nodes"); empty when it has none
 *  of them. OutNotes: what of them the game's parser would leave out. */
KAWAIIPHYSICS_API FString KawaiiEntrySettingsJson(const TArray<FKawaiiPhysicsAnimationTrigger>& Triggers, const TArray<FKawaiiPhysicsSharedWind>& SharedWinds,
	const FKawaiiPhysicsWorldWind& WorldWind, const FString& Indent, FString& OutNotes);
