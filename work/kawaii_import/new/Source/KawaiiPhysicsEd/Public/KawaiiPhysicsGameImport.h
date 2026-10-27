// (1.8) Import From Game: one of Create a Character System's "kawaii" entries (a compat\*.json file of the game) made
// back into an AnimBlueprint's KawaiiPhysics nodes, every setting, curve, shape and bone constraint as the game reads
// them, so a setup made for the game (by hand, by a tool, or exported before) can be previewed, tuned and exported again.
// Every entry of a file at once, too: each into an AnimBlueprint of its model's (Window > Import KawaiiPhysics From Game
// (every entry)...).
// KawaiiPhysics is pafuhana1213's (https://github.com/pafuhana1213/KawaiiPhysics), MIT License.
#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "AnimNode_KawaiiPhysics.h"

#include "KawaiiPhysicsGameImport.generated.h"

class UAnimBlueprint;
class USkeletalMesh;

UCLASS()
class KAWAIIPHYSICSED_API UKawaiiPhysicsGameImport : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** The "kawaii" entries of a compat file, one line each: "index: name | models | nodes". Empty when it is not one. */
	UFUNCTION(BlueprintCallable, Category = "KawaiiPhysics|Create a Character")
	static TArray<FString> ListGameEntries(const FString& JsonPath);

	/** Import From Game into an AnimBlueprint of its own: the entry of the compat file at JsonPath (EntryIndex, or -1:
	 *  the entry listing Mesh, else the file's only entry) as KawaiiPhysics nodes one after another (an animation
	 *  player first, empty: pick an animation of the mesh's skeleton to see them swing). AnimBlueprintPath: the
	 *  AnimBlueprint to make or update (a package path such as /Game/Character/X/X_KawaiiPhysics; empty: <Mesh>_KawaiiPhysics
	 *  beside the mesh). One there already keeps its graph, its KawaiiPhysics nodes replaced. Compiled and saved.
	 *  Returns a report (FAILED: ... when it could not). */
	UFUNCTION(BlueprintCallable, Category = "KawaiiPhysics|Create a Character")
	static FString ImportFromGame(const FString& JsonPath, USkeletalMesh* Mesh, const FString& AnimBlueprintPath, int32 EntryIndex = -1);

	/** Import From Game into an AnimBlueprint: its KawaiiPhysics nodes (one chain of them) replaced by the entry's, linked
	 *  where they were; without any, the entry's go before its Output Pose. EntryIndex -1: the entry listing the
	 *  AnimBlueprint's preview mesh, else the file's only entry. Compiled and saved. Returns a report. */
	UFUNCTION(BlueprintCallable, Category = "KawaiiPhysics|Create a Character")
	static FString ImportIntoAnimBlueprint(const FString& JsonPath, UAnimBlueprint* AnimBlueprint, int32 EntryIndex = -1);

	/** Import From Game, every entry of the compat file at JsonPath: each into an AnimBlueprint of its own for its model
	 *  (the first of its Models this project has; one ending in *: the first skeletal mesh of the project whose path
	 *  starts so and whose skeleton has the entry's root bones), <Model>_KawaiiPhysics beside the model, or in Folder (a
	 *  package path such as /Game/KawaiiImports; empty: beside each model). A second entry for the same model goes into
	 *  <Model>_KawaiiPhysics_2, and so on. One there already keeps its graph, its KawaiiPhysics nodes replaced. Each is
	 *  compiled and saved. Returns a report: how many were imported, then a line per entry (NOT imported: why). */
	UFUNCTION(BlueprintCallable, Category = "KawaiiPhysics|Create a Character")
	static FString ImportAllFromGame(const FString& JsonPath, const FString& Folder);

	/** Export For Game of an AnimBlueprint (as its nodes' button does, with the first node's export settings), for
	 *  scripts. Returns the file written (empty when it could not: OutMessage says why). */
	UFUNCTION(BlueprintCallable, Category = "KawaiiPhysics|Create a Character")
	static FString ExportAnimBlueprintForGame(UAnimBlueprint* AnimBlueprint, FString& OutMessage);

	// ---- for the editor's button and menu ------------------------------------------------------------------------
	/** Reads the file's entries (FAILED text in OutProblem when it cannot) */
	static bool ReadFile(const FString& JsonPath, TArray<FKawaiiPhysicsGameEntry>& OutEntries, FString& OutProblem);
	/** The entry for a model: EntryIndex when >= 0, else the one listing the model (an exact object path, or a path
	 *  ending in * that it starts with), else the only one; INDEX_NONE when it cannot choose */
	static int32 EntryFor(const TArray<FKawaiiPhysicsGameEntry>& Entries, const USkeletalMesh* Mesh, int32 EntryIndex);
	/** Asks for a compat file (a file dialog); false when none was picked */
	static bool AskForCompatFile(FString& OutPath);
	/** Asks which entry (a small window listing them); INDEX_NONE when none was picked */
	static int32 AskForEntry(const TArray<FKawaiiPhysicsGameEntry>& Entries, const FString& Why);
	/** The editor's way: a file asked for, its entry for the mesh (asked when it cannot tell), imported, a notification;
	 *  the AnimBlueprint opened. Either an AnimBlueprint to import into, or a mesh to make one for. */
	static void ImportWithDialogs(UAnimBlueprint* Into, USkeletalMesh* ForMesh);
	/** The editor's way for every entry (Window > Import KawaiiPhysics From Game (every entry)...): a file asked for,
	 *  every entry imported beside its model, a notification, the AnimBlueprints shown in the Content Browser. */
	static void ImportAllWithDialogs();
	/** The model of an entry this project has (see ImportAllFromGame); null when it has none of them */
	static USkeletalMesh* MeshForEntry(const FKawaiiPhysicsGameEntry& Entry);
};
