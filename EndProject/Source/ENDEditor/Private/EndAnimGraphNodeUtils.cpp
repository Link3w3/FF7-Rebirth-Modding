#include "EndAnimGraphNodeUtils.h"

#include "AnimGraphNode_Base.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimBlueprintGeneratedClass.h"
#include "Animation/AnimLayerInterface.h"
#include "EdGraph/EdGraph.h"
#include "IAnimBlueprintCompilationContext.h"
#include "IAnimBlueprintGeneratedClassCompiledData.h"

namespace EndAnimGraphNodes
{
FString Category()
{
	return TEXT("FINAL FANTASY VII REBIRTH (End)");
}

FText EnumValueText(const UEnum* Enum, int64 Value)
{
	if (!Enum)
	{
		return FText::AsNumber(Value);
	}
	const int32 Index = Enum->GetIndexByValue(Value);
	return Index == INDEX_NONE ? FText::AsNumber(Value) : Enum->GetDisplayNameTextByIndex(Index);
}

void RecordAssetPlayerForLayerGraphs(UAnimGraphNode_Base* Node, IAnimBlueprintGeneratedClassCompiledData& OutCompiledData)
{
	UBlueprint* Blueprint = Node ? Node->GetBlueprint() : nullptr;
	if (!Blueprint)
	{
		return;
	}
	const FGuid NodeGuid = Node->NodeGuid;
	auto ProcessGraph = [NodeGuid, &OutCompiledData](UEdGraph* Graph)
	{
		// (not the default AnimGraph, and not an empty stub graph)
		static const FName DefaultAnimGraphName(TEXT("AnimGraph"));
		if (!Graph || Graph->GetFName() == DefaultAnimGraphName)
		{
			return;
		}
		const FString GraphName = Graph->GetName();
		if (GraphName.Contains(ANIM_FUNC_DECORATOR))
		{
			return;
		}
		if (Graph->Nodes.ContainsByPredicate([NodeGuid](UEdGraphNode* Each) { return Each && Each->NodeGuid == NodeGuid; }))
		{
			if (int32* IndexPtr = OutCompiledData.GetAnimBlueprintDebugData().NodeGuidToIndexMap.Find(NodeGuid))
			{
				FGraphAssetPlayerInformation& Info = OutCompiledData.GetGraphAssetPlayerInformation().FindOrAdd(FName(*GraphName));
				Info.PlayerNodeIndices.AddUnique(*IndexPtr);
			}
		}
	};
	for (UEdGraph* Graph : Blueprint->FunctionGraphs)
	{
		ProcessGraph(Graph);
	}
	for (FBPInterfaceDescription& InterfaceDesc : Blueprint->ImplementedInterfaces)
	{
		if (InterfaceDesc.Interface && InterfaceDesc.Interface->IsChildOf<UAnimLayerInterface>())
		{
			for (UEdGraph* Graph : InterfaceDesc.Graphs)
			{
				ProcessGraph(Graph);
			}
		}
	}
}
} // namespace EndAnimGraphNodes
