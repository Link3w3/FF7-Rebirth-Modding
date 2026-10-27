#pragma once

#include "CoreMinimal.h"

// The details row of a post process material (FWeightedBlendable). The engine's own row (FWeightedBlendableCustomization)
// takes the struct's Weight row for granted, but this engine declares FWeightedBlendable::Weight without EditAnywhere, so
// that row is never made and every details panel showing a post process material stopped on check(IsValid())
// (SharedPointer.h line 890): the model editors' Preview Scene Settings as soon as their profile has a post process
// material, post process volumes, cameras. This row edits the weight through the struct's memory when the engine gives
// it no row of its own, and the material through the material's row.
namespace RebirthBlendableCustomization
{
    void Register();
    void Unregister();
}
