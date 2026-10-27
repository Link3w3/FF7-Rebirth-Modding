// Build Skins for the editor's other tools (editor 1.17): the Skin Maker builds one skin, the Parts Builder builds a
// Customization part's own assets (its model and animations of this project) into a skin folder of their own.
#pragma once

#include "CoreMinimal.h"
#include "EndSkeletonCompatDataObject.h"

class UAnimSequence;

namespace RebirthSkelCompatSkins
{
/** What a build of skins is for. */
struct FSkinBuildOptions
{
	/** Only these skins (indexes into the list); empty: every skin that is on. */
	TArray<int32> Only;
	/** The packages of a Customization part: its animations go in too (with the game's compression), and skin.json says
	 * "part": true (no one wears it: the part's catalog entry names its model and motions). */
	bool bPart = false;
	/** The progress dialog's title. */
	FString Title = TEXT("Build Skins");
};

/** Build Skins of a list of skins: built into OutputFolder (empty: <Project>/Saved/RebirthSkelCompat/Skins); with bInstall,
 * copied into GameDirectory's Create a Character System folder and the skins container made anew from every installed
 * skin. Report gets what happened; false: something was not built or installed. */
bool BuildSkinList(const TArray<FEndCharacterSkin>& Skins, const FDirectoryPath& OutputFolder, const FDirectoryPath& GameDirectory, bool bInstall,
	const FSkinBuildOptions& Options, FString& OutReport);

/** A skin's folder name: its Folder, else its Name's letters and digits. */
FString SkinFolderOf(const FEndCharacterSkin& Skin);

/** A folder name a skin can have (1-64 letters, digits, _ or -, not starting with _). */
bool IsValidSkinFolder(const FString& Folder);

/** The game's Create a Character System folder (<game>/End/Binaries/Win64/ue4ss/Mods/RebirthSkelCompat), or empty when
 * GameDirectory is empty. */
FString GameModFolderOf(const FDirectoryPath& GameDirectory);

/** A directory property as a full path (a relative one from the project folder), no closing slash. */
FString FullPathOfFolder(const FDirectoryPath& Directory);

/** The game has this package (/Game/...), as Build Skins finds out (the game's object tools: Rebirth Cooked Asset
 * Preview); false without them. */
bool IsGamePackage(const FString& PackageName);
}

namespace RebirthSkelCompatEditor
{
/** (editor 1.17, EndSkeletonCompatDataObject.cpp) The game's ACL compression settings on an animation of this project
 * that has others (the game reads every animation with them: one compressed otherwise plays wrong), compressed anew
 * (bOutChanged: they were put on, the package is dirty). False: the game's settings are not in this project. */
bool UseGameCompression(UAnimSequence* Sequence, bool& bOutChanged);

/** (editor 1.17) An animation's compressed bytes made ready for a cook, as Cook For Game does (compressed anew when
 * needed, its compressed data bound and written out the way the save reads it). */
void ReadyAnimationForGameCook(UAnimSequence* Sequence);
}
