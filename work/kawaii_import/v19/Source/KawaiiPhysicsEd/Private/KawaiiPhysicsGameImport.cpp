// (1.8) Import From Game: a "kawaii" entry of the game (compat\*.json) back into an AnimBlueprint's Kawaii Dynamic Motions
// (KawaiiPhysics) nodes, or every entry of a file, each into an AnimBlueprint of its model's; (1.9) their motions too.
// KawaiiPhysics is pafuhana1213's (https://github.com/pafuhana1213/KawaiiPhysics), MIT License.
#include "KawaiiPhysicsGameImport.h"

#include "AnimGraphNode_ComponentToLocalSpace.h"
#include "AnimGraphNode_KawaiiPhysics.h"
#include "AnimGraphNode_LocalToComponentSpace.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_SequencePlayer.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimBlueprintGeneratedClass.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimNodeBase.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "ARFilter.h"
#include "AssetRegistryModule.h"
#include "DesktopPlatformModule.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraph/EdGraphSchema.h"
#include "EdGraphSchema_K2.h"
#include "Editor.h"
#include "Engine/SkeletalMesh.h"
#include "Framework/Application/SlateApplication.h"
#include "Framework/Docking/TabManager.h"
#include "Framework/Notifications/NotificationManager.h"
#include "HAL/FileManager.h"
#include "IDesktopPlatform.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/CompilerResultsLog.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Misc/FileHelper.h"
#include "Misc/FeedbackContext.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Misc/ScopedSlowTask.h"
#include "ScopedTransaction.h"
#include "Subsystems/AssetEditorSubsystem.h"
#include "UObject/Package.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Notifications/SNotificationList.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SWindow.h"
#include "Widgets/Text/STextBlock.h"

#define LOCTEXT_NAMESPACE "KawaiiPhysicsGameImport"

DEFINE_LOG_CATEGORY_STATIC(LogKawaiiPhysicsImport, Log, All);

namespace
{
FString LastFolder;

UEdGraph* FindAnimGraph(UAnimBlueprint* Blueprint)
{
	for (UEdGraph* Graph : Blueprint->FunctionGraphs)
	{
		if (Graph && Graph->GetFName() == UEdGraphSchema_K2::GN_AnimGraph)
		{
			return Graph;
		}
	}
	return nullptr;
}

bool IsPose(const UEdGraphPin* Pin)
{
	const UObject* Type = Pin ? Pin->PinType.PinSubCategoryObject.Get() : nullptr;
	return Type == FPoseLink::StaticStruct() || Type == FComponentSpacePoseLink::StaticStruct();
}

UEdGraphPin* PosePin(UEdGraphNode* Node, EEdGraphPinDirection Direction)
{
	if (!Node)
	{
		return nullptr;
	}
	for (UEdGraphPin* Pin : Node->Pins)
	{
		if (Pin && Pin->Direction == Direction && IsPose(Pin))
		{
			return Pin;
		}
	}
	return nullptr;
}

// A link as the editor makes one (the nodes told, as the graph editor tells them after a drag)
bool Link(UEdGraphPin* From, UEdGraphPin* To)
{
	if (!From || !To)
	{
		return false;
	}
	UEdGraphNode* FromNode = From->GetOwningNode();
	UEdGraphNode* ToNode = To->GetOwningNode();
	const UEdGraphSchema* Schema = ToNode->GetSchema();
	if (!Schema || !Schema->TryCreateConnection(From, To))
	{
		return false;
	}
	FromNode->NodeConnectionListChanged();
	ToNode->NodeConnectionListChanged();
	return true;
}

// A node added as the editor adds one (its pins made after its settings are in)
void AddToGraph(UEdGraph* Graph, UEdGraphNode* Node, int32 X, int32 Y)
{
	Node->SetFlags(RF_Transactional);
	Graph->AddNode(Node, /*bUserAction*/ false, /*bSelectNewNode*/ false);
	Node->CreateNewGuid();
	Node->PostPlacedNewNode();
	if (Node->Pins.Num() == 0)
	{
		Node->AllocateDefaultPins();
	}
	Node->NodePosX = X;
	Node->NodePosY = Y;
}

UAnimGraphNode_KawaiiPhysics* MakeKawaii(UEdGraph* Graph, const FKawaiiPhysicsGameEntry& Entry, int32 Index, int32 X, int32 Y)
{
	UAnimGraphNode_KawaiiPhysics* Node = NewObject<UAnimGraphNode_KawaiiPhysics>(Graph, NAME_None, RF_Transactional);
	Node->Node = Entry.Nodes[Index];
	// (every node carries the entry's export settings: Export For Game on any of them writes the entry again)
	Node->ExportEntryName = Entry.Name;
	Node->ExportModels = Entry.Models;
	Node->ExportRequiresPaks = Entry.RequiresPaks;
	Node->bExportDisableBonamik = Entry.bDisableBonamik;
	Node->ExportDisableBonamikAssets = Entry.DisableBonamikAssets;
	AddToGraph(Graph, Node, X, Y);
	return Node;
}

// The bones an entry names that the skeleton has not (its nodes do nothing with them)
TArray<FString> MissingBones(const FKawaiiPhysicsGameEntry& Entry, const USkeleton* Skeleton)
{
	TSet<FName> Names;
	for (const FAnimNode_KawaiiPhysics& N : Entry.Nodes)
	{
		Names.Add(N.RootBone.BoneName);
		for (const FBoneReference& B : N.ExcludeBones) { Names.Add(B.BoneName); }
		for (const FKawaiiPhysicsRootBoneSetting& R : N.AdditionalRootBones)
		{
			Names.Add(R.RootBone.BoneName);
			for (const FBoneReference& B : R.OverrideExcludeBones) { Names.Add(B.BoneName); }
		}
		Names.Add(N.SimulationBaseBone.BoneName);
		for (const FSphericalLimit& L : N.SphericalLimits) { Names.Add(L.DrivingBone.BoneName); }
		for (const FCapsuleLimit& L : N.CapsuleLimits) { Names.Add(L.DrivingBone.BoneName); }
		for (const FTaperedCapsuleLimit& L : N.TaperedCapsuleLimits) { Names.Add(L.DrivingBone.BoneName); }
		for (const FBoxLimit& L : N.BoxLimits) { Names.Add(L.DrivingBone.BoneName); }
		for (const FPlanarLimit& L : N.PlanarLimits) { Names.Add(L.DrivingBone.BoneName); }
		for (const FModifyBoneConstraint& C : N.BoneConstraints)
		{
			Names.Add(C.Bone1.BoneName);
			Names.Add(C.Bone2.BoneName);
		}
		for (const FKawaiiPoseKeyTrack& T : N.PoseAnimation.Tracks)
		{
			Names.Add(T.Bone.BoneName);
		}
	}
	Names.Remove(FName());
	TArray<FString> Out;
	if (!Skeleton)
	{
		return Out;
	}
	for (const FName& Name : Names)
	{
		if (Skeleton->GetReferenceSkeleton().FindBoneIndex(Name) == INDEX_NONE)
		{
			Out.Add(Name.ToString());
		}
	}
	Out.Sort();
	return Out;
}

// An animation of the skeleton for the preview: a run, else a walk, else an idle, else the first (by name); null: none
UAnimSequenceBase* PreviewAnimation(USkeleton* Skeleton)
{
	if (!Skeleton)
	{
		return nullptr;
	}
	FAssetRegistryModule& Registry = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
	FARFilter Filter;
	Filter.ClassNames.Add(UAnimSequence::StaticClass()->GetFName());
	Filter.bRecursiveClasses = true;
	Filter.TagsAndValues.Add(TEXT("Skeleton"), FAssetData(Skeleton).GetExportTextName());
	TArray<FAssetData> Found;
	Registry.Get().GetAssets(Filter, Found);
	if (Found.Num() == 0)
	{
		return nullptr;
	}
	Found.Sort([](const FAssetData& A, const FAssetData& B) { return A.AssetName.LexicalLess(B.AssetName); });
	for (const TCHAR* Word : {TEXT("Run"), TEXT("Walk"), TEXT("Idle")})
	{
		for (const FAssetData& Each : Found)
		{
			if (Each.AssetName.ToString().Contains(Word))
			{
				if (UAnimSequenceBase* Anim = Cast<UAnimSequenceBase>(Each.GetAsset()))
				{
					return Anim;
				}
			}
		}
	}
	return Cast<UAnimSequenceBase>(Found[0].GetAsset());
}

bool SaveBlueprint(UAnimBlueprint* Blueprint, FString& OutProblem)
{
	UPackage* Package = Blueprint->GetOutermost();
	Package->MarkPackageDirty();
	const FString Filename = FPackageName::LongPackageNameToFilename(Package->GetName(), FPackageName::GetAssetPackageExtension());
	IFileManager::Get().MakeDirectory(*FPaths::GetPath(Filename), true);
	if (!UPackage::SavePackage(Package, Blueprint, RF_Public | RF_Standalone, *Filename, GWarn, nullptr, false, true, SAVE_NoError))
	{
		OutProblem = TEXT("could not be saved to ") + Filename;
		return false;
	}
	return true;
}

// The entry's nodes into the AnimBlueprint: its KawaiiPhysics nodes (one chain) replaced, else put before its Output
// Pose (an animation player first when nothing feeds it: Animation, else one of the skeleton's). Compiled and saved.
FString ImportEntry(UAnimBlueprint* Blueprint, const FKawaiiPhysicsGameEntry& Entry, const FString& From, UAnimSequenceBase* Animation = nullptr)
{
	if (Entry.Nodes.Num() == 0)
	{
		return TEXT("FAILED: the entry has no nodes");
	}
	const FScopedTransaction Transaction(LOCTEXT("ImportTransaction", "Import Kawaii Dynamic Motions From Game"));
	Blueprint->Modify();
	TArray<UAnimGraphNode_KawaiiPhysics*> Old;
	FBlueprintEditorUtils::GetAllNodesOfClass<UAnimGraphNode_KawaiiPhysics>(Blueprint, Old);
	Old.RemoveAll([](const UAnimGraphNode_KawaiiPhysics* N) { return N == nullptr; });
	UEdGraph* Graph = nullptr;
	UEdGraphPin* InFrom = nullptr;          // what fed the old chain (a component space pose)
	TArray<UEdGraphPin*> OutTo;            // what the old chain fed
	int32 X = 0, Y = 0;
	FString How;
	if (Old.Num() > 0)
	{
		Graph = Old[0]->GetGraph();
		for (const UAnimGraphNode_KawaiiPhysics* N : Old)
		{
			if (N->GetGraph() != Graph)
			{
				return TEXT("FAILED: the AnimBlueprint's Kawaii Dynamic Motions nodes are in more than one graph: import into an AnimBlueprint of their own (right-click the mesh > Import Kawaii Dynamic Motions From Game...)");
			}
		}
		// the chain: from the node no KawaiiPhysics node feeds, each feeding the next
		auto Feeder = [](UAnimGraphNode_KawaiiPhysics* N) -> UAnimGraphNode_KawaiiPhysics*
		{
			UEdGraphPin* In = PosePin(N, EGPD_Input);
			return In && In->LinkedTo.Num() == 1 && In->LinkedTo[0] ? Cast<UAnimGraphNode_KawaiiPhysics>(In->LinkedTo[0]->GetOwningNode()) : nullptr;
		};
		TArray<UAnimGraphNode_KawaiiPhysics*> Firsts = Old.FilterByPredicate([&Feeder](UAnimGraphNode_KawaiiPhysics* N) { return Feeder(N) == nullptr; });
		if (Firsts.Num() != 1)
		{
			return TEXT("FAILED: the AnimBlueprint's KawaiiPhysics nodes are not one chain: import into an AnimBlueprint of their own");
		}
		TArray<UAnimGraphNode_KawaiiPhysics*> Chain = {Firsts[0]};
		for (;;)
		{
			UAnimGraphNode_KawaiiPhysics* Last = Chain.Last();
			UAnimGraphNode_KawaiiPhysics* Next = nullptr;
			for (UAnimGraphNode_KawaiiPhysics* N : Old)
			{
				if (!Chain.Contains(N) && Feeder(N) == Last)
				{
					Next = N;
					break;
				}
			}
			if (!Next)
			{
				break;
			}
			Chain.Add(Next);
		}
		if (Chain.Num() != Old.Num())
		{
			return TEXT("FAILED: the AnimBlueprint's KawaiiPhysics nodes are not one chain: import into an AnimBlueprint of their own");
		}
		UEdGraphPin* FirstIn = PosePin(Chain[0], EGPD_Input);
		InFrom = FirstIn && FirstIn->LinkedTo.Num() > 0 ? FirstIn->LinkedTo[0] : nullptr;
		if (UEdGraphPin* LastOut = PosePin(Chain.Last(), EGPD_Output))
		{
			OutTo = LastOut->LinkedTo;
		}
		X = Chain[0]->NodePosX;
		Y = Chain[0]->NodePosY;
		Graph->Modify();
		for (UAnimGraphNode_KawaiiPhysics* N : Chain)
		{
			FBlueprintEditorUtils::RemoveNode(Blueprint, N, /*bDontRecompile*/ true);
		}
		TArray<UAnimGraphNode_KawaiiPhysics*> Made;
		for (int32 k = 0; k < Entry.Nodes.Num(); ++k)
		{
			Made.Add(MakeKawaii(Graph, Entry, k, X + 320 * k, Y));
		}
		bool bLinked = true;
		if (InFrom)
		{
			bLinked &= Link(InFrom, PosePin(Made[0], EGPD_Input));
		}
		for (int32 k = 1; k < Made.Num(); ++k)
		{
			bLinked &= Link(PosePin(Made[k - 1], EGPD_Output), PosePin(Made[k], EGPD_Input));
		}
		for (UEdGraphPin* To : OutTo)
		{
			bLinked &= Link(PosePin(Made.Last(), EGPD_Output), To);
		}
		How = FString::Printf(TEXT("its %d Kawaii Dynamic Motions node(s) replaced by the entry's %d%s"), Old.Num(), Made.Num(),
			bLinked ? TEXT("") : TEXT(" (NOT every link was made again: check the AnimGraph)"));
	}
	else
	{
		Graph = FindAnimGraph(Blueprint);
		UAnimGraphNode_Root* Root = nullptr;
		if (Graph)
		{
			for (UEdGraphNode* N : Graph->Nodes)
			{
				if (UAnimGraphNode_Root* Each = Cast<UAnimGraphNode_Root>(N))
				{
					Root = Each;
					break;
				}
			}
		}
		if (!Graph || !Root)
		{
			return TEXT("FAILED: the AnimBlueprint has no AnimGraph with an Output Pose");
		}
		Graph->Modify();
		UEdGraphPin* Result = PosePin(Root, EGPD_Input);
		UEdGraphPin* Source = Result && Result->LinkedTo.Num() > 0 ? Result->LinkedTo[0] : nullptr;
		const int32 N = Entry.Nodes.Num();
		X = Root->NodePosX - 320 * (N + 2);
		Y = Root->NodePosY;
		FString Played;
		if (Result)
		{
			Result->BreakAllPinLinks();
		}
		if (!Source)
		{
			// an animation of the skeleton to see them swing (a player without one is a compile error); none: the
			// nodes start from the reference pose
			UAnimSequenceBase* Anim = Animation && Animation->GetSkeleton() == Blueprint->TargetSkeleton ? Animation : PreviewAnimation(Blueprint->TargetSkeleton);
			if (Anim)
			{
				UAnimGraphNode_SequencePlayer* Player = NewObject<UAnimGraphNode_SequencePlayer>(Graph, NAME_None, RF_Transactional);
				Player->Node.Sequence = Anim;
				AddToGraph(Graph, Player, X - 320, Y);
				Source = PosePin(Player, EGPD_Output);
				Played = FString::Printf(TEXT(" (after an animation player playing %s: pick another in it if you like)"), *Anim->GetName());
			}
			else
			{
				Played = TEXT(" (the skeleton has no animations: they start from the reference pose; put one of its animations before them to see them swing)");
			}
		}
		UAnimGraphNode_LocalToComponentSpace* ToComponent = NewObject<UAnimGraphNode_LocalToComponentSpace>(Graph, NAME_None, RF_Transactional);
		AddToGraph(Graph, ToComponent, X, Y);
		TArray<UAnimGraphNode_KawaiiPhysics*> Made;
		for (int32 k = 0; k < N; ++k)
		{
			Made.Add(MakeKawaii(Graph, Entry, k, X + 320 * (k + 1), Y));
		}
		UAnimGraphNode_ComponentToLocalSpace* ToLocal = NewObject<UAnimGraphNode_ComponentToLocalSpace>(Graph, NAME_None, RF_Transactional);
		AddToGraph(Graph, ToLocal, X + 320 * (N + 1), Y);
		bool bLinked = !Source || Link(Source, PosePin(ToComponent, EGPD_Input));
		bLinked &= Link(PosePin(ToComponent, EGPD_Output), PosePin(Made[0], EGPD_Input));
		for (int32 k = 1; k < N; ++k)
		{
			bLinked &= Link(PosePin(Made[k - 1], EGPD_Output), PosePin(Made[k], EGPD_Input));
		}
		bLinked &= Link(PosePin(Made.Last(), EGPD_Output), PosePin(ToLocal, EGPD_Input));
		bLinked &= Link(PosePin(ToLocal, EGPD_Output), Result);
		How = FString::Printf(TEXT("the entry's %d node(s) put before its Output Pose%s%s"), N, *Played,
			bLinked ? TEXT("") : TEXT(" (NOT every link was made: check the AnimGraph)"));
	}
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
	FCompilerResultsLog Log;
	FKismetEditorUtilities::CompileBlueprint(Blueprint, EBlueprintCompileOptions::None, &Log);
	TArray<FString> Compiler;
	for (const TSharedRef<FTokenizedMessage>& Message : Log.Messages)
	{
		if (Message->GetSeverity() == EMessageSeverity::Error || Message->GetSeverity() == EMessageSeverity::CriticalError ||
			Message->GetSeverity() == EMessageSeverity::Warning)
		{
			Compiler.Add(Message->ToText().ToString());
		}
	}
	FString Problem;
	const bool bSaved = SaveBlueprint(Blueprint, Problem);
	const TArray<FString> Missing = MissingBones(Entry, Blueprint->TargetSkeleton);
	FString Report = FString::Printf(TEXT("%s: \"%s\" from %s: %s; compiled %s; %s"), *Blueprint->GetPathName(),
		*(Entry.Name.IsEmpty() ? FString(TEXT("(no name)")) : Entry.Name), *From, *How,
		Blueprint->Status == BS_Error ? TEXT("with ERRORS") : Blueprint->Status == BS_UpToDateWithWarnings ? TEXT("with warnings") : TEXT("OK"),
		bSaved ? TEXT("saved") : *Problem);
	if (Missing.Num() > 0)
	{
		Report += FString::Printf(TEXT("\nthe skeleton has none of these bones the entry names (%d): %s"), Missing.Num(),
			*FString::Join(TArray<FString>(Missing.GetData(), FMath::Min(Missing.Num(), 24)), TEXT(", ")));
	}
	for (const FString& Line : Compiler)
	{
		Report += TEXT("\ncompiler: ") + Line;
	}
	UE_LOG(LogKawaiiPhysicsImport, Log, TEXT("Import From Game: %s"), *Report);
	return Report;
}

FString DefaultBlueprintPath(const USkeletalMesh* Mesh)
{
	return FPackageName::GetLongPackagePath(Mesh->GetOutermost()->GetName()) / (Mesh->GetName() + TEXT("_KawaiiPhysics"));
}

// An entry into the AnimBlueprint at AnimBlueprintPath (empty: <Mesh>_KawaiiPhysics beside the mesh), made for the mesh
// when it is not there
FString ImportEntryForMesh(const FKawaiiPhysicsGameEntry& Entry, USkeletalMesh* Mesh, const FString& AnimBlueprintPath, const FString& From,
	UAnimBlueprint** OutBlueprint, UAnimSequenceBase* Animation = nullptr)
{
	if (!Mesh || !Mesh->Skeleton)
	{
		return TEXT("FAILED: no mesh (or the mesh has no skeleton)");
	}
	FString Package = AnimBlueprintPath.TrimStartAndEnd();
	if (Package.IsEmpty())
	{
		Package = DefaultBlueprintPath(Mesh);
	}
	if (Package.Contains(TEXT(".")))
	{
		Package = FPackageName::ObjectPathToPackageName(Package);
	}
	FText Reason;
	if (!FPackageName::IsValidLongPackageName(Package, false, &Reason))
	{
		return TEXT("FAILED: not a package path: ") + Package + TEXT(" (") + Reason.ToString() + TEXT(")");
	}
	const FString AssetName = FPackageName::GetLongPackageAssetName(Package);
	const FString ObjectPath = Package + TEXT(".") + AssetName;
	UAnimBlueprint* Blueprint = nullptr;
	if (FPackageName::DoesPackageExist(Package) || FindObject<UObject>(nullptr, *ObjectPath))
	{
		UObject* Existing = LoadObject<UObject>(nullptr, *ObjectPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
		Blueprint = Cast<UAnimBlueprint>(Existing);
		if (!Blueprint)
		{
			return TEXT("FAILED: ") + ObjectPath + TEXT(" is there already and is not an AnimBlueprint");
		}
	}
	else
	{
		UPackage* Outer = CreatePackage(*Package);
		Outer->FullyLoad();
		Blueprint = Cast<UAnimBlueprint>(FKismetEditorUtilities::CreateBlueprint(UAnimInstance::StaticClass(), Outer, FName(*AssetName), BPTYPE_Normal,
			UAnimBlueprint::StaticClass(), UAnimBlueprintGeneratedClass::StaticClass(), FName(TEXT("KawaiiPhysicsImport"))));
		if (!Blueprint)
		{
			return TEXT("FAILED: the AnimBlueprint could not be made");
		}
		// (as the AnimBlueprint factory: the skeleton on the blueprint and its classes, the preview mesh)
		Blueprint->TargetSkeleton = Mesh->Skeleton;
		if (UAnimBlueprintGeneratedClass* Class = Cast<UAnimBlueprintGeneratedClass>(Blueprint->GeneratedClass))
		{
			Class->TargetSkeleton = Mesh->Skeleton;
		}
		if (UAnimBlueprintGeneratedClass* Class = Cast<UAnimBlueprintGeneratedClass>(Blueprint->SkeletonGeneratedClass))
		{
			Class->TargetSkeleton = Mesh->Skeleton;
		}
		Blueprint->SetPreviewMesh(Mesh);
		FAssetRegistryModule::AssetCreated(Blueprint);
	}
	if (Blueprint->TargetSkeleton != Mesh->Skeleton)
	{
		return TEXT("FAILED: ") + ObjectPath + TEXT(" is for another skeleton (") + GetNameSafe(Blueprint->TargetSkeleton) + TEXT(")");
	}
	if (OutBlueprint)
	{
		*OutBlueprint = Blueprint;
	}
	return ImportEntry(Blueprint, Entry, From, Animation);
}

FString ImportForMesh(const FString& JsonPath, USkeletalMesh* Mesh, const FString& AnimBlueprintPath, int32 EntryIndex, UAnimBlueprint** OutBlueprint,
	UAnimSequenceBase* Animation = nullptr)
{
	if (!Mesh || !Mesh->Skeleton)
	{
		return TEXT("FAILED: no mesh (or the mesh has no skeleton)");
	}
	TArray<FKawaiiPhysicsGameEntry> Entries;
	FString Problem;
	if (!UKawaiiPhysicsGameImport::ReadFile(JsonPath, Entries, Problem))
	{
		return TEXT("FAILED: ") + Problem;
	}
	const int32 Index = UKawaiiPhysicsGameImport::EntryFor(Entries, Mesh, EntryIndex);
	if (Index == INDEX_NONE)
	{
		return FString::Printf(TEXT("FAILED: %s has %d entries and none lists %s: give the entry's index (List Game Entries)"),
			*FPaths::GetCleanFilename(JsonPath), Entries.Num(), *Mesh->GetPathName());
	}
	return ImportEntryForMesh(Entries[Index], Mesh, AnimBlueprintPath, FPaths::GetCleanFilename(JsonPath), OutBlueprint, Animation);
}

// Every entry of the file, each into its model's AnimBlueprint (in Folder, else beside the model); OutImported: how many
// went in. The report: a line saying how many, then a line per entry.
FString ImportAll(const FString& JsonPath, const FString& Folder, TArray<UObject*>* OutBlueprints, int32& OutImported, int32& OutEntries)
{
	OutImported = 0;
	OutEntries = 0;
	TArray<FKawaiiPhysicsGameEntry> Entries;
	FString Problem;
	if (!UKawaiiPhysicsGameImport::ReadFile(JsonPath, Entries, Problem))
	{
		return TEXT("FAILED: ") + Problem;
	}
	const FString From = FPaths::GetCleanFilename(JsonPath);
	if (Entries.Num() == 0)
	{
		return TEXT("FAILED: ") + From + TEXT(" has no \"kawaii\" entries");
	}
	FString Into = Folder.TrimStartAndEnd();
	while (Into.EndsWith(TEXT("/")))
	{
		Into.LeftChopInline(1);
	}
	FText Reason;
	if (!Into.IsEmpty() && !FPackageName::IsValidLongPackageName(Into / TEXT("KawaiiPhysics"), false, &Reason))
	{
		return TEXT("FAILED: not a folder of the project's: ") + Into + TEXT(" (") + Reason.ToString() + TEXT(")");
	}
	OutEntries = Entries.Num();
	TMap<USkeletalMesh*, int32> Uses;   // (a second entry for a model gets an AnimBlueprint of its own)
	TArray<FString> Lines;
	FScopedSlowTask Progress(static_cast<float>(Entries.Num()), FText::Format(LOCTEXT("ImportAllProgress", "Importing Kawaii Dynamic Motions from {0}"), FText::FromString(From)));
	Progress.MakeDialog();
	for (int32 k = 0; k < Entries.Num(); ++k)
	{
		const FKawaiiPhysicsGameEntry& Entry = Entries[k];
		const FString Label = FString::Printf(TEXT("entry %d \"%s\""), k, *(Entry.Name.IsEmpty() ? FString(TEXT("(no name)")) : Entry.Name));
		Progress.EnterProgressFrame(1.0f, FText::FromString(Label));
		USkeletalMesh* Mesh = UKawaiiPhysicsGameImport::MeshForEntry(Entry);
		if (!Mesh)
		{
			Lines.Add(Label + TEXT(": NOT imported: this project has none of its models (") +
				(Entry.Models.Num() > 0 ? FString::Join(Entry.Models, TEXT(", ")) : FString(TEXT("it lists none"))) +
				TEXT("): right-click a model of yours > Import Kawaii Dynamic Motions From Game... and pick this entry"));
			continue;
		}
		int32& Count = Uses.FindOrAdd(Mesh);
		++Count;
		const FString Name = Mesh->GetName() + TEXT("_KawaiiPhysics") + (Count > 1 ? FString::Printf(TEXT("_%d"), Count) : FString());
		const FString Path = (Into.IsEmpty() ? FPackageName::GetLongPackagePath(Mesh->GetOutermost()->GetName()) : Into) / Name;
		UAnimBlueprint* Blueprint = nullptr;
		const FString Report = ImportEntryForMesh(Entry, Mesh, Path, From, &Blueprint);
		if (Report.StartsWith(TEXT("FAILED")))
		{
			Lines.Add(Label + TEXT(": NOT imported: ") + Report.RightChop(8));
			continue;
		}
		++OutImported;
		Lines.Add(Label + TEXT(" (") + Mesh->GetName() + TEXT("): ") + Report);
		if (OutBlueprints && Blueprint)
		{
			OutBlueprints->Add(Blueprint);
		}
	}
	const FString Out = FString::Printf(TEXT("%s: %d of its %d entries imported\n"), *From, OutImported, Entries.Num()) + FString::Join(Lines, TEXT("\n"));
	UE_LOG(LogKawaiiPhysicsImport, Log, TEXT("Import From Game (every entry): %s"), *Out);
	return Out;
}

void Notify(bool bOk, const FString& Text)
{
	FNotificationInfo Info(FText::FromString(Text.Left(600)));
	Info.ExpireDuration = bOk ? 8.0f : 10.0f;
	Info.bUseLargeFont = false;
	FSlateNotificationManager::Get().AddNotification(Info);
}
} // namespace

// ----------------------------------------------------------------------------
bool UKawaiiPhysicsGameImport::ReadFile(const FString& JsonPath, TArray<FKawaiiPhysicsGameEntry>& OutEntries, FString& OutProblem)
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *JsonPath))
	{
		OutProblem = TEXT("could not read ") + JsonPath;
		return false;
	}
	FString Messages;
	if (!ReadKawaiiGameEntries(Text, OutEntries, Messages))
	{
		OutProblem = FPaths::GetCleanFilename(JsonPath) + TEXT(": ") + Messages.TrimStartAndEnd();
		return false;
	}
	if (!Messages.IsEmpty())
	{
		UE_LOG(LogKawaiiPhysicsImport, Warning, TEXT("%s: the game's parser says:\n%s"), *JsonPath, *Messages);
	}
	return true;
}

int32 UKawaiiPhysicsGameImport::EntryFor(const TArray<FKawaiiPhysicsGameEntry>& Entries, const USkeletalMesh* Mesh, int32 EntryIndex)
{
	if (EntryIndex >= 0)
	{
		return Entries.IsValidIndex(EntryIndex) ? EntryIndex : INDEX_NONE;
	}
	if (Mesh)
	{
		const FString Path = Mesh->GetPathName();
		for (int32 k = 0; k < Entries.Num(); ++k)
		{
			for (const FString& Model : Entries[k].Models)
			{
				const bool bHit = Model.EndsWith(TEXT("*")) ? Path.StartsWith(Model.LeftChop(1), ESearchCase::IgnoreCase)
					: Path.Equals(Model, ESearchCase::IgnoreCase);
				if (bHit)
				{
					return k;
				}
			}
		}
	}
	return Entries.Num() == 1 ? 0 : INDEX_NONE;
}

TArray<FString> UKawaiiPhysicsGameImport::ListGameEntries(const FString& JsonPath)
{
	TArray<FString> Out;
	TArray<FKawaiiPhysicsGameEntry> Entries;
	FString Problem;
	if (!ReadFile(JsonPath, Entries, Problem))
	{
		return Out;
	}
	for (int32 k = 0; k < Entries.Num(); ++k)
	{
		Out.Add(FString::Printf(TEXT("%d: %s | %s | %d node(s)"), k, *Entries[k].Name, *FString::Join(Entries[k].Models, TEXT(", ")), Entries[k].Nodes.Num()));
	}
	return Out;
}

FString UKawaiiPhysicsGameImport::ImportFromGame(const FString& JsonPath, USkeletalMesh* Mesh, const FString& AnimBlueprintPath, int32 EntryIndex)
{
	return ImportForMesh(JsonPath, Mesh, AnimBlueprintPath, EntryIndex, nullptr);
}

FString UKawaiiPhysicsGameImport::ImportFromGameWithAnimation(const FString& JsonPath, USkeletalMesh* Mesh, const FString& AnimBlueprintPath, int32 EntryIndex,
	UAnimSequenceBase* Animation)
{
	return ImportForMesh(JsonPath, Mesh, AnimBlueprintPath, EntryIndex, nullptr, Animation);
}

USkeletalMesh* UKawaiiPhysicsGameImport::MeshForEntry(const FKawaiiPhysicsGameEntry& Entry)
{
	// (a mesh for a model "...*": its skeleton has every bone a node starts from)
	auto HasRoots = [&Entry](const USkeletalMesh* Mesh)
	{
		if (!Mesh || !Mesh->Skeleton)
		{
			return false;
		}
		const FReferenceSkeleton& Bones = Mesh->Skeleton->GetReferenceSkeleton();
		for (const FAnimNode_KawaiiPhysics& N : Entry.Nodes)
		{
			if (!N.RootBone.BoneName.IsNone() && Bones.FindBoneIndex(N.RootBone.BoneName) == INDEX_NONE)
			{
				return false;
			}
		}
		return true;
	};
	for (const FString& Each : Entry.Models)
	{
		FString Model = Each.TrimStartAndEnd();
		if (Model.IsEmpty())
		{
			continue;
		}
		if (Model.EndsWith(TEXT("*")))
		{
			const FString Prefix = Model.LeftChop(1);
			const FString Under = FPackageName::GetLongPackagePath(Prefix.Contains(TEXT(".")) ? FPackageName::ObjectPathToPackageName(Prefix) : Prefix);
			if (!FPackageName::IsValidLongPackageName(Under / TEXT("KawaiiPhysics")))
			{
				continue;
			}
			FAssetRegistryModule& Registry = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
			FARFilter Filter;
			Filter.ClassNames.Add(USkeletalMesh::StaticClass()->GetFName());
			Filter.bRecursiveClasses = true;
			Filter.PackagePaths.Add(FName(*Under));
			Filter.bRecursivePaths = true;
			TArray<FAssetData> Found;
			Registry.Get().GetAssets(Filter, Found);
			Found.Sort([](const FAssetData& A, const FAssetData& B) { return A.ObjectPath.LexicalLess(B.ObjectPath); });
			for (const FAssetData& Asset : Found)
			{
				if (Asset.ObjectPath.ToString().StartsWith(Prefix, ESearchCase::IgnoreCase))
				{
					USkeletalMesh* Mesh = Cast<USkeletalMesh>(Asset.GetAsset());
					if (HasRoots(Mesh))
					{
						return Mesh;
					}
				}
			}
			continue;
		}
		if (!Model.Contains(TEXT(".")))
		{
			Model += TEXT(".") + FPackageName::GetShortName(Model);   // (a package path: its asset)
		}
		const FString Package = FPackageName::ObjectPathToPackageName(Model);
		if (!FPackageName::IsValidLongPackageName(Package) || (!FindObject<UObject>(nullptr, *Model) && !FPackageName::DoesPackageExist(Package)))
		{
			continue;
		}
		if (USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *Model, nullptr, LOAD_NoWarn | LOAD_Quiet))
		{
			return Mesh;
		}
	}
	return nullptr;
}

FString UKawaiiPhysicsGameImport::ImportAllFromGame(const FString& JsonPath, const FString& Folder)
{
	int32 Imported = 0, Entries = 0;
	return ImportAll(JsonPath, Folder, nullptr, Imported, Entries);
}

FString UKawaiiPhysicsGameImport::ImportIntoAnimBlueprint(const FString& JsonPath, UAnimBlueprint* AnimBlueprint, int32 EntryIndex)
{
	if (!AnimBlueprint)
	{
		return TEXT("FAILED: no AnimBlueprint");
	}
	TArray<FKawaiiPhysicsGameEntry> Entries;
	FString Problem;
	if (!ReadFile(JsonPath, Entries, Problem))
	{
		return TEXT("FAILED: ") + Problem;
	}
	const int32 Index = EntryFor(Entries, AnimBlueprint->GetPreviewMesh(), EntryIndex);
	if (Index == INDEX_NONE)
	{
		return FString::Printf(TEXT("FAILED: %s has %d entries and none lists the AnimBlueprint's preview mesh: give the entry's index (List Game Entries)"),
			*FPaths::GetCleanFilename(JsonPath), Entries.Num());
	}
	return ImportEntry(AnimBlueprint, Entries[Index], FPaths::GetCleanFilename(JsonPath));
}

FString UKawaiiPhysicsGameImport::ExportAnimBlueprintForGame(UAnimBlueprint* AnimBlueprint, FString& OutMessage)
{
	OutMessage.Reset();
	if (!AnimBlueprint)
	{
		OutMessage = TEXT("no AnimBlueprint");
		return FString();
	}
	TArray<UAnimGraphNode_KawaiiPhysics*> Nodes;
	FBlueprintEditorUtils::GetAllNodesOfClass<UAnimGraphNode_KawaiiPhysics>(AnimBlueprint, Nodes);
	Nodes.RemoveAll([](const UAnimGraphNode_KawaiiPhysics* N) { return N == nullptr; });
	if (Nodes.Num() == 0)
	{
		OutMessage = TEXT("the AnimBlueprint has no Kawaii Dynamic Motions node");
		return FString();
	}
	FString Path;
	return Nodes[0]->ExportForGame(Path, OutMessage) ? Path : FString();
}

bool UKawaiiPhysicsGameImport::AskForCompatFile(FString& OutPath)
{
	IDesktopPlatform* Desktop = FDesktopPlatformModule::Get();
	if (!Desktop)
	{
		return false;
	}
	if (LastFolder.IsEmpty())
	{
		LastFolder = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("KawaiiPhysics"));
	}
	TArray<FString> Files;
	const void* Parent = FSlateApplication::Get().FindBestParentWindowHandleForDialogs(nullptr);
	const bool bPicked = Desktop->OpenFileDialog(Parent, TEXT("Import Kawaii Dynamic Motions From Game: a compat file (the game mod's compat folder, or one exported)"),
		LastFolder, TEXT(""), TEXT("Create a Character System compat file (*.json)|*.json"), EFileDialogFlags::None, Files);
	if (!bPicked || Files.Num() == 0)
	{
		return false;
	}
	OutPath = FPaths::ConvertRelativePathToFull(Files[0]);
	LastFolder = FPaths::GetPath(OutPath);
	return true;
}

int32 UKawaiiPhysicsGameImport::AskForEntry(const TArray<FKawaiiPhysicsGameEntry>& Entries, const FString& Why)
{
	int32 Chosen = INDEX_NONE;
	TSharedRef<SWindow> Window = SNew(SWindow)
		.Title(LOCTEXT("PickEntryTitle", "Import Kawaii Dynamic Motions From Game"))
		.SizingRule(ESizingRule::Autosized)
		.SupportsMinimize(false)
		.SupportsMaximize(false);
	TWeakPtr<SWindow> WeakWindow = Window;
	TSharedRef<SVerticalBox> List = SNew(SVerticalBox);
	for (int32 k = 0; k < Entries.Num(); ++k)
	{
		const FKawaiiPhysicsGameEntry& Entry = Entries[k];
		const FString Label = FString::Printf(TEXT("%s   (%d node(s): %s)"), *(Entry.Name.IsEmpty() ? FString::Printf(TEXT("entry %d"), k) : Entry.Name),
			Entry.Nodes.Num(), *FString::Join(Entry.Models, TEXT(", ")));
		List->AddSlot().AutoHeight().Padding(8.0f, 2.0f)
		[
			SNew(SButton)
			.Text(FText::FromString(Label))
			.OnClicked_Lambda([&Chosen, k, WeakWindow]()
			{
				Chosen = k;
				if (TSharedPtr<SWindow> Open = WeakWindow.Pin()) { Open->RequestDestroyWindow(); }
				return FReply::Handled();
			})
		];
	}
	Window->SetContent(
		SNew(SBox).MaxDesiredWidth(1000.0f).MaxDesiredHeight(700.0f)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().Padding(8.0f)
			[
				SNew(STextBlock).Text(FText::FromString(Why)).AutoWrapText(true)
			]
			+ SVerticalBox::Slot().FillHeight(1.0f)
			[
				SNew(SScrollBox) + SScrollBox::Slot()[List]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(8.0f).HAlign(HAlign_Right)
			[
				SNew(SButton)
				.Text(LOCTEXT("Cancel", "Cancel"))
				.OnClicked_Lambda([WeakWindow]()
				{
					if (TSharedPtr<SWindow> Open = WeakWindow.Pin()) { Open->RequestDestroyWindow(); }
					return FReply::Handled();
				})
			]
		]);
	FSlateApplication::Get().AddModalWindow(Window, FGlobalTabmanager::Get()->GetRootWindow());
	return Chosen;
}

void UKawaiiPhysicsGameImport::ImportWithDialogs(UAnimBlueprint* Into, USkeletalMesh* ForMesh)
{
	FString Path;
	if (!AskForCompatFile(Path))
	{
		return;
	}
	TArray<FKawaiiPhysicsGameEntry> Entries;
	FString Problem;
	if (!ReadFile(Path, Entries, Problem))
	{
		Notify(false, TEXT("Kawaii Dynamic Motions: not imported: ") + Problem);
		return;
	}
	USkeletalMesh* Mesh = ForMesh ? ForMesh : (Into ? Into->GetPreviewMesh() : nullptr);
	int32 Index = EntryFor(Entries, Mesh, INDEX_NONE);
	if (Index == INDEX_NONE)
	{
		Index = AskForEntry(Entries, FString::Printf(TEXT("%s has %d entries%s. Import which one?"), *FPaths::GetCleanFilename(Path), Entries.Num(),
			Mesh ? *FString::Printf(TEXT(" and none lists %s"), *Mesh->GetName()) : TEXT("")));
	}
	if (Index == INDEX_NONE)
	{
		return;
	}
	UAnimBlueprint* Blueprint = Into;
	const FString Report = Into ? ImportEntry(Into, Entries[Index], FPaths::GetCleanFilename(Path))
		: ImportForMesh(Path, ForMesh, FString(), Index, &Blueprint);
	const bool bOk = !Report.StartsWith(TEXT("FAILED"));
	Notify(bOk, (bOk ? TEXT("Kawaii Dynamic Motions imported: ") : TEXT("Kawaii Dynamic Motions: not imported: ")) + Report);
	if (bOk && Blueprint && GEditor)
	{
		if (UAssetEditorSubsystem* Editors = GEditor->GetEditorSubsystem<UAssetEditorSubsystem>())
		{
			Editors->OpenEditorForAsset(Blueprint);
		}
	}
}

void UKawaiiPhysicsGameImport::ImportAllWithDialogs()
{
	FString Path;
	if (!AskForCompatFile(Path))
	{
		return;
	}
	TArray<UObject*> Blueprints;
	int32 Imported = 0, Entries = 0;
	const FString Report = ImportAll(Path, FString(), &Blueprints, Imported, Entries);
	const bool bOk = !Report.StartsWith(TEXT("FAILED")) && Imported > 0;
	// (the notification: how many, and why each one that did not go in did not; the whole report in the Output Log)
	TArray<FString> Lines;
	Report.ParseIntoArrayLines(Lines);
	FString Short = Lines.Num() > 0 ? Lines[0] : Report;
	for (int32 k = 1; k < Lines.Num(); ++k)
	{
		if (Lines[k].Contains(TEXT(": NOT imported: ")))
		{
			Short += TEXT("\n") + Lines[k];
		}
	}
	if (Report.StartsWith(TEXT("FAILED")))
	{
		Short = TEXT("Kawaii Dynamic Motions: not imported: ") + Report;
	}
	else
	{
		Short = TEXT("Kawaii Dynamic Motions: ") + Short + TEXT("\n(each AnimBlueprint beside its model, <Model>_KawaiiPhysics; the Output Log has every one)");
	}
	Notify(bOk, Short);
	if (Blueprints.Num() > 0 && GEditor)
	{
		GEditor->SyncBrowserToObjects(Blueprints);
	}
}

#undef LOCTEXT_NAMESPACE
