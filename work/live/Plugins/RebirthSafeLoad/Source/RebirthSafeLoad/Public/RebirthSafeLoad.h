#pragma once

#include "CoreMinimal.h"

/**
 * Guards the editor against cooked "unversioned" packages whose objects were saved with more properties than this
 * project's classes have (game classes in the End project that are missing properties). The engine reads such data
 * past the end of the class's property list and crashes. With the guard, the object loads with default values from
 * that point, the package is listed here, and a warning names it.
 */
namespace RebirthSafeLoad
{
	/** True when the guard is installed (RebirthEngineV5's UE4Editor-CoreUObject.dll was recognised). */
	REBIRTHSAFELOAD_API bool IsActive();

	/** Why the guard is not installed (empty when it is). */
	REBIRTHSAFELOAD_API FString GetInactiveReason();

	/** True when an object of this package could not be read in full (OutDetails says which and why). */
	REBIRTHSAFELOAD_API bool WasPackageDamaged(FName PackageName, FString* OutDetails = nullptr);

	/** Every package with an object that could not be read in full since the editor started. */
	REBIRTHSAFELOAD_API TArray<FName> GetDamagedPackages();
}
