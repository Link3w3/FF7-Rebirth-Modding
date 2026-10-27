// KawaiiPhysics' editor module (End editor, UE 4.26): the AnimGraph node's edit mode, and (1.8) Import From Game on a
// Skeletal Mesh's and an AnimBlueprint's Content Browser menu.

#pragma once

#include "CoreMinimal.h"

#include "Modules/ModuleManager.h"

struct FToolMenuContext;

class FKawaiiPhysicsEdModule : public IModuleInterface
{
public:

	/** IModuleInterface implementation */
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

private:
	void RegisterMenus();
	static void ImportForPickedMesh(const FToolMenuContext& Context);
	static void ImportIntoPickedAnimBlueprint(const FToolMenuContext& Context);
};
