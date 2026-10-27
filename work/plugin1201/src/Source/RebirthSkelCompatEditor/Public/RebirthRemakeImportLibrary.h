// The Remake Importer's editor functions (editor 1.16): what Tools/RemakeMaterials/remake_character.py needs that the
// editor's Python cannot do itself.
#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "RebirthRemakeImportLibrary.generated.h"

UCLASS()
class REBIRTHSKELCOMPATEDITOR_API URebirthRemakeImportLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** Sockets (editor 1.16, the Remake Importer): puts each socket of Sockets Json, a JSON array of
	 * {"name", "bone", "location": [x, y, z], "rotation": [pitch, yaw, roll], "scale": [x, y, z], "always_animated"},
	 * on Skeleton Or Mesh: a Skeleton (its sockets, which every mesh of it has) or a Skeletal Mesh (that mesh's own).
	 * A socket of the same name is set anew; one whose bone the skeleton (or the mesh) does not have is left out. Marks the
	 * asset changed (the caller saves it) and returns a JSON report: {"on", "added": [...], "replaced": [...],
	 * "skipped": [...]}, or {"error": "..."}. */
	UFUNCTION(BlueprintCallable, Category = "Remake Importer")
	static FString AddSockets(UObject* SkeletonOrMesh, const FString& SocketsJson);

	/** FBX (editor 1.16.2, the Remake Importer): each animation of Animation Paths written as a binary FBX file (its
	 * skeleton's bones and the animation, no mesh) with the engine's FBX exporter, to the file at the same place in Files.
	 * The exporter needs a preview mesh: an animation that has none uses Preview Mesh Path (a skeletal mesh of its
	 * skeleton) for the export, in memory only (nothing is saved). Returns a JSON report: {"exported": [files],
	 * "failed": [{"animation", "why"}]}, or {"error": "..."}. */
	UFUNCTION(BlueprintCallable, Category = "Remake Importer")
	static FString ExportAnimationsFbx(const TArray<FString>& AnimationPaths, const TArray<FString>& Files, const FString& PreviewMeshPath);
};
