// RebirthSkelCompat weapon Blueprints (editor 1.20): a weapon Blueprint for the game made as a real Blueprint of this
// editor from one of the game's own weapon blueprints (a template: Tools\RebirthSkelCompat\weapon\templates.json, read
// from the game's cooked weapon blueprints by make_weapon_templates.py). The game's weapon blueprints are data only: a
// native parent class (EndWeaponSkeletalMeshActor, EndWeaponSyncPoseSkeletalMeshActor), their class defaults, their mesh
// component's settings (SkeletalMeshComponent0: collision, tick) and, for a few, components of their own (a gun's
// cartridges, a light). The made Blueprint has the template's native class as its parent (the End project's), every one
// of those values put on it as text (FProperty::ImportText), its components made in its construction script, and the
// user's model on its mesh component. It compiles and saves like any Blueprint and can be edited (components, effects,
// values); a skin's Weapon names its class, and the skin build cooks it with its model.
#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "EndWeaponBlueprintTemplate.generated.h"

class UBlueprint;
class USkeletalMesh;

namespace RebirthWeaponTemplate
{
/** A template the Weapon Blueprint Maker offers: one of the game's weapon blueprints. */
struct FTemplateInfo
{
	FString Key;         // the game's blueprint's name (WE0000_00_Cloud_BusterSword): the made Blueprint's name by default
	FString Package;     // its package (/Game/BluePrint/Character/Weapon/WE0000_00_Cloud_BusterSword)
	FString Label;       // "Cloud: Buster Sword (WE0000_00)"
	FString Character;   // "Cloud"
	FString Parent;      // its native class (/Script/EndGame.EndWeaponSkeletalMeshActor)
	FString Mesh;        // the game's model it holds (for reference)
};

/** What the maker made, and what it could not. */
struct FBuildReport
{
	bool bOk = false;
	FString Template;
	FString Asset;          // the Blueprint's object path
	FString WeaponClass;    // its class's path (a skin's "weapon", a form's weapon)
	FString Compile;        // the compile's result: up to date / with warnings / error
	int32 Defaults = 0;     // class default values put on it
	int32 Settings = 0;     // values put on its native components (SkeletalMeshComponent0 ...)
	int32 Components = 0;   // components of its own made in its construction script
	TArray<FString> Errors;
	TArray<FString> Warnings;
	TArray<FString> Notes;
	TArray<FString> Compiler;

	FString ToJson() const;
	FString ToText() const;
};

/** Tools\RebirthSkelCompat\weapon under the project (its templates.json). */
FString ToolDir();

/** Tools\RebirthSkelCompat\weapon\templates.json. */
FString TemplatesFile();

/** The templates (the players' weapons first), read from TemplatesFile (again when it changes). Empty when it is not there. */
TArray<FTemplateInfo> Templates();

/** The template for a key (WE0000_00_Cloud_BusterSword) or a label; false when there is none. */
bool FindTemplate(const FString& KeyOrLabel, FTemplateInfo& Out);

/** The folder a weapon Blueprint of a model (its package or object path) goes in by default:
 *  /Game/BluePrint/Character/Weapon/<the model's weapon folder> (/Game/Character/Weapon/WE1021_15_Essence_Shard/Model/
 *  WE001021_15 -> .../Weapon/WE1021_15_Essence_Shard), else /Game/BluePrint/Character/Weapon/<the model's name>. */
FString DefaultFolder(const FString& MeshPath);

/**
 * Makes the weapon Blueprint PackagePath (/Game/.../Name) from the template TemplateKey, holding the model MeshPath
 * (an object or package path), compiles and saves it. bReplaceExisting: an asset already there is deleted first (else
 * the making stops).
 */
FBuildReport MakeWeaponBlueprint(const FString& TemplateKey, const FString& MeshPath, const FString& PackagePath, bool bReplaceExisting,
	UBlueprint** OutBlueprint = nullptr);

/**
 * The packages a weapon Blueprint of this project brings into a skin: the Blueprint's, then every package it needs
 * (hard, in game: its models, their skeletons and physics assets, materials, textures ...) that is this project's (under
 * /Game and not one IsGamePackage says the game has: the game's own stay the game's), found through the asset registry.
 * (1.20.1) A cooked package of this project the game does not have that a material uses (the renderer's default textures
 * a material instance keeps of its parent) is not one of them: it is said in OutNotes, as the skin's model leaves it out.
 * False with the reason when the class is not a Blueprint of this project.
 */
bool WeaponPackages(const FString& WeaponClassPath, TFunctionRef<bool(const FString&)> IsGamePackage, TArray<FString>& OutPackages,
	TArray<FString>& OutNotes, FString& OutProblem);
}

/** The weapon Blueprint maker for Python (the editor's scripts) and Blueprints. */
UCLASS()
class UEndWeaponBlueprintTemplateLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Makes the weapon Blueprint PackagePath (/Game/.../Name) from Template (a template's key, WE0000_00_Cloud_BusterSword,
	 * or its label) holding the model Mesh, compiles and saves it. A JSON report ("ok", "asset", "weapon_class", "errors"...).
	 */
	UFUNCTION(BlueprintCallable, Category = "Rebirth|Weapon")
	static FString MakeWeaponBlueprint(const FString& Template, const FString& Mesh, const FString& PackagePath, bool bReplaceExisting);

	/** The templates as JSON: [{"key", "label", "character", "parent", "package", "mesh"}]. */
	UFUNCTION(BlueprintCallable, Category = "Rebirth|Weapon")
	static FString WeaponTemplates();
};
