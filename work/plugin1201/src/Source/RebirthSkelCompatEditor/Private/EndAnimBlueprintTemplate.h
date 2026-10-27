// RebirthSkelCompat editable AnimBlueprints (editor 1.19): one of the game's AnimBlueprints (Cloud's player AnimBlueprint
// by default) built again as an AnimBlueprint of this editor, for a character's skeleton, from a template (a JSON file
// Tools\RebirthSkelCompat\abp\templates\<AnimBlueprint>.template.json, decoded from the game's cooked AnimBlueprint):
// its AnimGraph (the game's End nodes are End's own AnimGraph nodes, ENDEditor's AnimGraphNode_End*), its state
// machines with their states, conduits and transitions, the transitions' rules as nodes, the pin bindings and the class
// defaults. It compiles in this editor and can be edited like any AnimBlueprint; Cook For Game writes it as a ~mods
// container.
#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "EndAnimBlueprintTemplate.generated.h"

class UAnimBlueprint;

namespace RebirthAnimTemplate
{
/** What the builder made, and what it could not. */
struct FBuildReport
{
	bool bOk = false;
	FString Template;
	FString Asset;          // the AnimBlueprint's object path
	FString AnimClass;      // its class's path (a form's "anim_class", a skin's "anim_blueprint")
	FString Compile;        // the compile's result: up to date / with warnings / error
	int32 AnimGraphNodes = 0;
	int32 States = 0;
	int32 Conduits = 0;
	int32 Transitions = 0;
	int32 RuleNodes = 0;
	int32 Bindings = 0;
	int32 Defaults = 0;
	TArray<FString> Errors;
	TArray<FString> Warnings;
	TArray<FString> Notes;
	TArray<FString> Compiler;   // the compiler's errors and warnings

	FString ToJson() const;
	FString ToText() const;
};

/** A template the makers offer: its key (cloud, tifa ...), the game's AnimBlueprint it is (its package name: the files
 *  Tools\RebirthSkelCompat\abp\templates\<Package>.template.json and <Package>.uasset) and its label in the Maker. */
struct FTemplateInfo
{
	FString Key;
	FString Package;
	FString Label;
};

/** The templates: the four built in (cloud, sephiroth, vincent, monster), then those abp\templates\templates.json lists
 *  ({"templates": [{"key", "package", "label"}]}: the other characters' AnimBlueprints, with no new build). */
TArray<FTemplateInfo> Templates();

/** The template file for a key (cloud, tifa ..., see Templates) or a template file's own path. */
FString TemplateFile(const FString& KeyOrPath);

/**
 * Makes the AnimBlueprint PackagePath (/Game/.../Name) for the skeleton (an object or package path) from the template file,
 * compiles and saves it. bReplaceExisting: an asset already there is deleted first (else the build stops).
 */
FBuildReport MakeEditableAnimBlueprint(const FString& TemplatePath, const FString& SkeletonPath, const FString& PackagePath, bool bReplaceExisting,
	UAnimBlueprint** OutBlueprint = nullptr);

/**
 * Cooks the package for the game (WindowsNoEditor, as the Parts Builder's skins: versioned) and writes it as a ~mods
 * container OutDir\ContainerName.utoc/.ucas/.pak (the engine's IoStore commandlet). A JSON report.
 */
FString CookToContainer(const TArray<FString>& PackageNames, const FString& ContainerName, const FString& OutDir);
}

/** The editable AnimBlueprint builder for Python (the editor's scripts) and Blueprints. */
UCLASS()
class UEndAnimBlueprintTemplateLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Makes the editable AnimBlueprint PackagePath (/Game/.../Name) for Skeleton from Template (a template's key: cloud,
	 * sephiroth, vincent, monster, tifa ... (see RebirthAnimTemplate::Templates), or a .template.json path), compiles and
	 * saves it. A JSON report ("ok", "asset", "anim_class", "errors"...).
	 */
	UFUNCTION(BlueprintCallable, Category = "Rebirth|AnimBlueprint")
	static FString MakeEditableAnimBlueprint(const FString& Template, const FString& Skeleton, const FString& PackagePath, bool bReplaceExisting);

	/** Cooks PackagePath for the game and writes it as the ~mods container OutDir\ContainerName (.utoc/.ucas/.pak). A JSON report. */
	UFUNCTION(BlueprintCallable, Category = "Rebirth|AnimBlueprint")
	static FString CookAnimBlueprintContainer(const FString& PackagePath, const FString& ContainerName, const FString& OutDir);
};
