// KawaiiPhysics' AnimGraph node (End editor, UE 4.26): its title, its viewport drawing (the simulated bones, their angle
// limits and bone constraints), live edits of the preview, and Export For Game (the AnimBlueprint's KawaiiPhysics nodes
// as one of Create a Character System's "kawaii" entries).
// KawaiiPhysics is pafuhana1213's (https://github.com/pafuhana1213/KawaiiPhysics), MIT License.
#include "AnimGraphNode_KawaiiPhysics.h"

#include "Animation/AnimBlueprint.h"
#include "Animation/AnimBlueprintGeneratedClass.h"
#include "Animation/AnimInstance.h"
#include "Animation/Skeleton.h"
#include "Components/SkeletalMeshComponent.h"
#include "DetailCategoryBuilder.h"
#include "DetailLayoutBuilder.h"
#include "DetailWidgetRow.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphPin.h"
#include "Engine/SkeletalMesh.h"
#include "Framework/Notifications/NotificationManager.h"
#include "HAL/PlatformApplicationMisc.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/CompilerResultsLog.h"
#include "Misc/DateTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "SceneManagement.h"
#include "UObject/UnrealType.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Notifications/SNotificationList.h"
#include "Widgets/Text/STextBlock.h"

#define LOCTEXT_NAMESPACE "KawaiiPhysics"

DEFINE_LOG_CATEGORY_STATIC(LogKawaiiPhysicsEd, Log, All);

namespace
{
FString JsonString(const FString& In)
{
	FString Out;
	Out.Reserve(In.Len() + 2);
	Out += TEXT("\"");
	for (const TCHAR C : In)
	{
		switch (C)
		{
		case TEXT('"'): Out += TEXT("\\\""); break;
		case TEXT('\\'): Out += TEXT("\\\\"); break;
		case TEXT('\n'): Out += TEXT("\\n"); break;
		case TEXT('\r'): Out += TEXT("\\r"); break;
		case TEXT('\t'): Out += TEXT("\\t"); break;
		default:
			if (C < 0x20) { Out += FString::Printf(TEXT("\\u%04x"), int32(C)); }
			else { Out.AppendChar(C); }
		}
	}
	Out += TEXT("\"");
	return Out;
}

FString JsonStrings(const TArray<FString>& Items)
{
	TArray<FString> Parts;
	for (const FString& Item : Items)
	{
		const FString Trimmed = Item.TrimStartAndEnd();
		if (!Trimmed.IsEmpty()) { Parts.Add(JsonString(Trimmed)); }
	}
	return TEXT("[") + FString::Join(Parts, TEXT(", ")) + TEXT("]");
}

// The KawaiiPhysics nodes a node's input poses come from (through any node), so the nodes can be written in the order the
// graph runs them: the game runs an entry's nodes in order, each on the pose the ones before it left.
void Upstream(const UEdGraphNode* Node, TSet<const UEdGraphNode*>& Seen)
{
	for (const UEdGraphPin* Pin : Node->Pins)
	{
		if (!Pin || Pin->Direction != EGPD_Input) { continue; }
		for (const UEdGraphPin* Linked : Pin->LinkedTo)
		{
			const UEdGraphNode* From = Linked ? Linked->GetOwningNode() : nullptr;
			if (From && !Seen.Contains(From))
			{
				Seen.Add(From);
				Upstream(From, Seen);
			}
		}
	}
}
} // namespace

// ----------------------------------------------------------------------------
FText UAnimGraphNode_KawaiiPhysics::GetControllerDescription() const
{
	return LOCTEXT("Kawaii Physics", "Kawaii Physics");
}

FText UAnimGraphNode_KawaiiPhysics::GetTooltipText() const
{
	return LOCTEXT("KawaiiPhysicsTooltip",
		"KawaiiPhysics: the bones from the root bone down swing with the character's motion. Its preview runs the game mod's "
		"own simulation (Create a Character System). The game runs it from compat\\*.json: Export For Game (Create a "
		"Character) writes this AnimBlueprint's KawaiiPhysics nodes as one of its \"kawaii\" entries. Keep this AnimBlueprint "
		"out of the game's paks (the game has no KawaiiPhysics module).");
}

FText UAnimGraphNode_KawaiiPhysics::GetNodeTitle(ENodeTitleType::Type TitleType) const
{
	if (TitleType == ENodeTitleType::ListView || TitleType == ENodeTitleType::MenuTitle)
	{
		return GetControllerDescription();
	}
	FFormatNamedArguments Args;
	Args.Add(TEXT("ControllerDescription"), GetControllerDescription());
	Args.Add(TEXT("RootBoneName"), FText::FromName(Node.RootBone.BoneName));
	Args.Add(TEXT("Name"), FText::FromString(Node.NodeName.IsEmpty() ? FString() : FString::Printf(TEXT(" (%s)"), *Node.NodeName)));
	CachedNodeTitles.SetCachedTitle(TitleType, FText::Format(LOCTEXT("AnimGraphNode_KawaiiPhysics_Title", "{ControllerDescription}{Name}\nRoot: {RootBoneName}"), Args), this);
	return CachedNodeTitles[TitleType];
}

void UAnimGraphNode_KawaiiPhysics::PostEditChangeProperty(struct FPropertyChangedEvent& PropertyChangedEvent)
{
	Super::PostEditChangeProperty(PropertyChangedEvent);
	CachedNodeTitles.MarkDirty();
	ReconstructNode();
}

FEditorModeID UAnimGraphNode_KawaiiPhysics::GetEditorMode() const
{
	return "AnimGraph.SkeletalControl.KawaiiPhysics";
}

// The preview's node takes the edited settings (the details panel's edits, without a compile): every property of the
// node's own struct; the base node's (its pose link, alpha, LOD) stay. Its bone references are made again for the
// preview's mesh at its next evaluation.
void UAnimGraphNode_KawaiiPhysics::CopyNodeDataToPreviewNode(FAnimNode_Base* InPreviewNode)
{
	FAnimNode_KawaiiPhysics* Preview = static_cast<FAnimNode_KawaiiPhysics*>(InPreviewNode);
	if (!Preview) { return; }
	UScriptStruct* Struct = FAnimNode_KawaiiPhysics::StaticStruct();
	for (TFieldIterator<FProperty> It(Struct, EFieldIteratorFlags::ExcludeSuper); It; ++It)
	{
		It->CopyCompleteValue_InContainer(Preview, &Node);
	}
	Preview->MarkBonesDirty();
}

void UAnimGraphNode_KawaiiPhysics::CustomizeDetails(IDetailLayoutBuilder& DetailBuilder)
{
	Super::CustomizeDetails(DetailBuilder);
	TWeakObjectPtr<UAnimGraphNode_KawaiiPhysics> Self(this);
	IDetailCategoryBuilder& Category = DetailBuilder.EditCategory(TEXT("Create a Character"));
	Category.AddCustomRow(LOCTEXT("ExportForGameRow", "Export For Game"))
	.WholeRowContent()
	[
		SNew(SButton)
		.Text(LOCTEXT("ExportForGame", "Export For Game"))
		.ToolTipText(LOCTEXT("ExportForGameTooltip",
			"Writes this AnimBlueprint's KawaiiPhysics nodes (in the order the graph runs them) as one of Create a Character "
			"System's \"kawaii\" entries: Saved\\KawaiiPhysics\\<AnimBlueprint>Kawaii.json, and to the clipboard. Put the file "
			"in the game mod's compat folder. The entry's models, paks and Bonamik switch come from this node's Export For "
			"Game settings."))
		.OnClicked_Lambda([Self]()
		{
			if (Self.IsValid()) { Self->ExportWithNotification(); }
			return FReply::Handled();
		})
	];
}

void UAnimGraphNode_KawaiiPhysics::ValidateAnimNodePostCompile(FCompilerResultsLog& MessageLog, UAnimBlueprintGeneratedClass* CompiledClass, int32 CompiledNodeIndex)
{
	Super::ValidateAnimNodePostCompile(MessageLog, CompiledClass, CompiledNodeIndex);
	USkeleton* Skeleton = CompiledClass ? CompiledClass->TargetSkeleton : nullptr;
	if (!Skeleton) { return; }
	FBoneReference Root = Node.RootBone;
	Root.Initialize(Skeleton);
	if (Root.BoneIndex < 0)
	{
		MessageLog.Warning(TEXT("@@ has no root bone (the skeleton has no bone of that name)"), this);
		return;
	}
	for (const FBoneReference& Exclude : Node.ExcludeBones)
	{
		if (Exclude.BoneName == Node.RootBone.BoneName)
		{
			MessageLog.Warning(TEXT("@@: Exclude Bones has the root bone (nothing would swing)"), this);
		}
	}
	for (const FKawaiiPhysicsRootBoneSetting& Extra : Node.AdditionalRootBones)
	{
		FBoneReference Bone = Extra.RootBone;
		if (!Bone.BoneName.IsNone() && !Bone.Initialize(Skeleton))
		{
			MessageLog.Warning(*FString::Printf(TEXT("@@: the skeleton has no bone %s (an additional root bone)"), *Bone.BoneName.ToString()), this);
		}
	}
	if (Node.SimulationSpace == EKawaiiPhysicsSimulationSpace::BaseBoneSpace && Node.SimulationBaseBone.BoneName.IsNone())
	{
		MessageLog.Note(TEXT("@@: Base Bone Space without a Simulation Base Bone simulates in component space"), this);
	}
}

void UAnimGraphNode_KawaiiPhysics::Draw(FPrimitiveDrawInterface* PDI, USkeletalMeshComponent* SkelMeshComp) const
{
	if (!SkelMeshComp || !PDI) { return; }
	FAnimNode_KawaiiPhysics* ActiveNode = GetActiveInstanceNode<FAnimNode_KawaiiPhysics>(SkelMeshComp->GetAnimInstance());
	if (!ActiveNode) { return; }
	const FTransform ToWorld = SkelMeshComp->GetComponentTransform();
	TArray<FKawaiiPhysicsDebugBone> Bones;
	ActiveNode->GetDebugBones(Bones);

	if (bEnableDebugDrawBone)
	{
		for (const FKawaiiPhysicsDebugBone& Bone : Bones)
		{
			const FVector At = ToWorld.TransformPosition(Bone.Location);
			PDI->DrawPoint(At, FLinearColor::White, 5.0f, SDPG_Foreground);
			if (Bone.Radius > 0.0f)
			{
				DrawWireSphere(PDI, At, Bone.bDummy ? FColor::Red : FColor::Yellow, Bone.Radius * ToWorld.GetMaximumAxisScale(), 16, SDPG_Foreground);
			}
			if (Bones.IsValidIndex(Bone.Parent))
			{
				DrawDashedLine(PDI, ToWorld.TransformPosition(Bones[Bone.Parent].Location), At, FLinearColor::White, 1.0f, SDPG_Foreground);
			}
		}
	}

	if (bEnableDebugDrawAngleLimit)
	{
		for (const FKawaiiPhysicsDebugBone& Bone : Bones)
		{
			if (!Bones.IsValidIndex(Bone.Parent) || Bone.LimitAngle <= 0.0f) { continue; }
			const FKawaiiPhysicsDebugBone& Parent = Bones[Bone.Parent];
			const FVector Pose = Bone.PoseLocation - Parent.PoseLocation;
			if (Pose.IsNearlyZero()) { continue; }
			const FTransform Cone(FQuat::FindBetween(FVector::ForwardVector, ToWorld.TransformVectorNoScale(Pose)), ToWorld.TransformPosition(Parent.Location));
			TArray<FVector> Verts;
			DrawWireCone(PDI, Verts, Cone, Pose.Size() * ToWorld.GetMaximumAxisScale(), Bone.LimitAngle, 16, FColor::Green, SDPG_World);
		}
	}

	if (bEnableDebugDrawBoneConstraint)
	{
		for (const FModifyBoneConstraint& Constraint : ActiveNode->BoneConstraints)
		{
			const int32 A = SkelMeshComp->GetBoneIndex(Constraint.Bone1.BoneName);
			const int32 B = SkelMeshComp->GetBoneIndex(Constraint.Bone2.BoneName);
			if (A == INDEX_NONE || B == INDEX_NONE) { continue; }
			PDI->DrawLine(SkelMeshComp->GetBoneLocation(Constraint.Bone1.BoneName), SkelMeshComp->GetBoneLocation(Constraint.Bone2.BoneName),
				FLinearColor(0.2f, 0.6f, 1.0f), SDPG_Foreground, 0.5f);
		}
	}
}

// ---- Export For Game ------------------------------------------------------------------------
bool UAnimGraphNode_KawaiiPhysics::ExportForGame(FString& OutPath, FString& OutMessage)
{
	UAnimBlueprint* AnimBP = Cast<UAnimBlueprint>(FBlueprintEditorUtils::FindBlueprintForNode(this));
	if (!AnimBP)
	{
		OutMessage = TEXT("this node is in no AnimBlueprint");
		return false;
	}
	TArray<UAnimGraphNode_KawaiiPhysics*> All;
	FBlueprintEditorUtils::GetAllNodesOfClass<UAnimGraphNode_KawaiiPhysics>(AnimBP, All);
	All.RemoveAll([](const UAnimGraphNode_KawaiiPhysics* N) { return N == nullptr || N->Node.RootBone.BoneName.IsNone(); });
	if (All.Num() == 0)
	{
		OutMessage = TEXT("no KawaiiPhysics node of this AnimBlueprint has a root bone");
		return false;
	}
	// the order the graph runs them: those fed by fewer KawaiiPhysics nodes first (then as they were placed)
	TMap<const UAnimGraphNode_KawaiiPhysics*, int32> Before;
	for (const UAnimGraphNode_KawaiiPhysics* N : All)
	{
		TSet<const UEdGraphNode*> Seen;
		Upstream(N, Seen);
		int32 Count = 0;
		for (const UAnimGraphNode_KawaiiPhysics* Other : All)
		{
			if (Other != N && Seen.Contains(Other)) { ++Count; }
		}
		Before.Add(N, Count);
	}
	All.StableSort([&Before](const UAnimGraphNode_KawaiiPhysics& A, const UAnimGraphNode_KawaiiPhysics& B) { return Before[&A] < Before[&B]; });

	// the models: this node's list, else the AnimBlueprint's preview mesh, else its skeleton's
	TArray<FString> Models = ExportModels;
	Models.RemoveAll([](const FString& M) { return M.TrimStartAndEnd().IsEmpty(); });
	if (Models.Num() == 0)
	{
		USkeletalMesh* Mesh = AnimBP->GetPreviewMesh();
		if (!Mesh && AnimBP->TargetSkeleton) { Mesh = AnimBP->TargetSkeleton->GetPreviewMesh(); }
		if (!Mesh)
		{
			OutMessage = TEXT("give the models (Export Models) or a preview mesh: the entry must name the models it is for");
			return false;
		}
		Models.Add(Mesh->GetPathName());
	}

	const FString EntryName = ExportEntryName.TrimStartAndEnd().IsEmpty() ? AnimBP->GetName() : ExportEntryName.TrimStartAndEnd();
	TArray<FString> NodeTexts;
	for (const UAnimGraphNode_KawaiiPhysics* N : All)
	{
		NodeTexts.Add(TEXT("    ") + N->Node.ToGameJson(TEXT("    ")));
	}
	FString Entry;
	Entry += TEXT("  {\n");
	Entry += TEXT("   \"name\": ") + JsonString(EntryName) + TEXT(",\n");
	Entry += TEXT("   \"models\": ") + JsonStrings(Models) + TEXT(",\n");
	if (ExportRequiresPaks.Num() > 0) { Entry += TEXT("   \"requires_paks\": ") + JsonStrings(ExportRequiresPaks) + TEXT(",\n"); }
	if (bExportDisableBonamik)
	{
		Entry += TEXT("   \"disable_bonamik\": ") + (ExportDisableBonamikAssets.Num() > 0 ? JsonStrings(ExportDisableBonamikAssets) : FString(TEXT("true"))) + TEXT(",\n");
	}
	Entry += TEXT("   \"nodes\": [\n") + FString::Join(NodeTexts, TEXT(",\n")) + TEXT("\n   ]\n");
	Entry += TEXT("  }");
	const FString Note = FString::Printf(TEXT("KawaiiPhysics of %s, from the End editor (%s). Create a Character System 3.14+: put it in the game mod's compat folder."),
		*AnimBP->GetPathName(), *FDateTime::Now().ToString(TEXT("%Y-%m-%d %H:%M")));
	FString Text;
	Text += TEXT("{\n");
	Text += TEXT(" \"schema\": \"RebirthSkelCompat/1\",\n");
	Text += TEXT(" \"note\": ") + JsonString(Note) + TEXT(",\n");
	Text += TEXT(" \"kawaii\": [\n") + Entry + TEXT("\n ]\n");
	Text += TEXT("}\n");
	Text.ReplaceInline(TEXT("\n"), TEXT("\r\n"));

	OutPath = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("KawaiiPhysics") / (AnimBP->GetName() + TEXT("Kawaii.json")));
	if (!FFileHelper::SaveStringToFile(Text, *OutPath, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
	{
		OutMessage = TEXT("could not write ") + OutPath;
		return false;
	}
	FPlatformApplicationMisc::ClipboardCopy(*Text);
	OutMessage = FString::Printf(TEXT("%d node(s) for %s"), All.Num(), *FString::Join(Models, TEXT(", ")));
	return true;
}

void UAnimGraphNode_KawaiiPhysics::ExportWithNotification()
{
	FString Path, Message;
	const bool bOk = ExportForGame(Path, Message);
	FNotificationInfo Info(bOk
		? FText::Format(LOCTEXT("Exported", "KawaiiPhysics for the game: {0}\n{1} (and the clipboard)"), FText::FromString(Message), FText::FromString(Path))
		: FText::Format(LOCTEXT("NotExported", "KawaiiPhysics: not exported: {0}"), FText::FromString(Message)));
	Info.ExpireDuration = bOk ? 8.0f : 6.0f;
	Info.bUseLargeFont = false;
	FSlateNotificationManager::Get().AddNotification(Info);
	if (bOk) { UE_LOG(LogKawaiiPhysicsEd, Log, TEXT("Export For Game: %s -> %s"), *Message, *Path); }
	else { UE_LOG(LogKawaiiPhysicsEd, Warning, TEXT("Export For Game: not exported: %s"), *Message); }
}

#undef LOCTEXT_NAMESPACE
