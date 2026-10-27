#pragma once

#include "CoreMinimal.h"

class UAnimGraphNode_Base;
class IAnimBlueprintGeneratedClassCompiledData;

/** Helpers the AnimGraph nodes of the game's End anim nodes (AnimGraphNode_End*.h) share. */
namespace EndAnimGraphNodes
{
	/** The menu category every End node is listed under in the AnimGraph's context menu. */
	FString Category();

	/** The game's name for a value of one of its enums (e.g. a locomotion state), for node titles. */
	FText EnumValueText(const UEnum* Enum, int64 Value);

	/**
	 * What UAnimGraphNode_AssetPlayerBase::OnProcessDuringCompilation does (AnimGraph does not export it, so the End
	 * asset players carry their own): an asset player in a layer graph (a function graph or an implemented AnimLayer
	 * interface graph) has its node index recorded for that graph, for the automatic transition rules of layer nodes.
	 */
	void RecordAssetPlayerForLayerGraphs(UAnimGraphNode_Base* Node, IAnimBlueprintGeneratedClassCompiledData& OutCompiledData);
}
