// RebirthSkelCompat editable AnimBlueprints (editor 1.19): see EndAnimBlueprintTemplate.h.
#include "EndAnimBlueprintTemplate.h"

#include "AnimGraphNode_AssetPlayerBase.h"
#include "AnimGraphNode_Base.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_StateMachineBase.h"
#include "AnimGraphNode_TransitionResult.h"
#include "AnimStateConduitNode.h"
#include "AnimStateEntryNode.h"
#include "AnimStateNode.h"
#include "AnimStateNodeBase.h"
#include "AnimStateTransitionNode.h"
#include "AnimationStateMachineGraph.h"
#include "AnimationTransitionGraph.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimBlueprintGeneratedClass.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimNodeBase.h"
#include "Animation/Skeleton.h"
#include "AssetRegistryModule.h"
#include "Dom/JsonObject.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraph/EdGraphSchema.h"
#include "EdGraphSchema_K2.h"
#include "Engine/Blueprint.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformProcess.h"
#include "Interfaces/ITargetPlatform.h"
#include "Interfaces/ITargetPlatformManagerModule.h"
#include "K2Node_AnimGetter.h"
#include "K2Node_CallFunction.h"
#include "K2Node_CommutativeAssociativeBinaryOperator.h"
#include "K2Node_EnumEquality.h"
#include "K2Node_EnumInequality.h"
#include "K2Node_Select.h"
#include "K2Node_VariableGet.h"
#include "Kismet/KismetMathLibrary.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/CompilerResultsLog.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Misc/App.h"
#include "Misc/FeedbackContext.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "ObjectTools.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "ShaderCompiler.h"
#include "UObject/Package.h"
#include "UObject/UObjectHash.h"
#include "UObject/UnrealType.h"

#define LOCTEXT_NAMESPACE "RebirthAnimBlueprintTemplate"

DEFINE_LOG_CATEGORY_STATIC(LogRebirthAnimTemplate, Log, All);

// Named, not anonymous: the module may be compiled as one unity file with the other sources.
namespace RebirthAnimTemplateUtil
{
using FJsonObj = TSharedPtr<FJsonObject>;

const TCHAR* const TemplateKeys[][2] = {
	{TEXT("cloud"), TEXT("PC0000_00_Cloud_Standard_Animation")},
	{TEXT("sephiroth"), TEXT("PC0010_00_Sephiroth_Standard_Animation")},
	{TEXT("vincent"), TEXT("PC0011_00_Vincent_Standard_Animation")},
	{TEXT("monster"), TEXT("SU0004_00_Leviathan_Standard_Animation")},
};

// Tools\RebirthSkelCompat\abp under the project (its templates folder and the stub .pak).
FString TemplateToolDir()
{
	return FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectDir(), TEXT("Tools"), TEXT("RebirthSkelCompat"), TEXT("abp")));
}

FString ObjectPathOf(const FString& Path)
{
	FString Out = Path.TrimStartAndEnd();
	if (Out.StartsWith(TEXT("/")) && !Out.Contains(TEXT(".")))
	{
		Out += TEXT(".") + FPackageName::GetShortName(Out);
	}
	return Out;
}

// The shortest text that reads back as the same float (0.7, not 0.699999988079071).
FString FloatText(double Value)
{
	const float Want = static_cast<float>(Value);
	for (int32 Digits = 0; Digits <= 9; ++Digits)
	{
		const FString Text = FString::Printf(TEXT("%.*f"), Digits, static_cast<double>(Want));
		if (FCString::Atof(*Text) == Want)
		{
			return Text.Contains(TEXT(".")) ? Text : Text + TEXT(".0");
		}
	}
	return FString::Printf(TEXT("%.9g"), static_cast<double>(Want));
}

FString Str(const FJsonObj& Object, const TCHAR* Field)
{
	FString Out;
	if (Object.IsValid())
	{
		Object->TryGetStringField(Field, Out);
	}
	return Out;
}

const TArray<TSharedPtr<FJsonValue>>* Arr(const FJsonObj& Object, const TCHAR* Field)
{
	const TArray<TSharedPtr<FJsonValue>>* Out = nullptr;
	if (Object.IsValid() && Object->TryGetArrayField(Field, Out))
	{
		return Out;
	}
	return nullptr;
}

FJsonObj Obj(const FJsonObj& Object, const TCHAR* Field)
{
	const TSharedPtr<FJsonObject>* Out = nullptr;
	if (Object.IsValid() && Object->TryGetObjectField(Field, Out) && Out)
	{
		return *Out;
	}
	return nullptr;
}

FVector2D Pos(const FJsonObj& Object, const FVector2D& Default)
{
	const TArray<TSharedPtr<FJsonValue>>* P = Arr(Object, TEXT("pos"));
	if (P && P->Num() == 2)
	{
		return FVector2D((*P)[0]->AsNumber(), (*P)[1]->AsNumber());
	}
	return Default;
}

void Place(UEdGraphNode* Node, const FVector2D& Where)
{
	Node->NodePosX = FMath::RoundToInt(Where.X);
	Node->NodePosY = FMath::RoundToInt(Where.Y);
}

// A node added to Graph as the editor adds one (its pins made after the caller has set it up).
void AddToGraph(UEdGraph* Graph, UEdGraphNode* Node, const FVector2D& Where)
{
	Node->SetFlags(RF_Transactional);
	Graph->AddNode(Node, /*bUserAction*/ false, /*bSelectNewNode*/ false);
	Node->CreateNewGuid();
	Node->PostPlacedNewNode();
	if (Node->Pins.Num() == 0)
	{
		Node->AllocateDefaultPins();
	}
	Place(Node, Where);
}

// The anim node a graph node carries (its first FAnimNode_Base struct property).
FStructProperty* AnimNodeProperty(UClass* Class)
{
	for (TFieldIterator<FStructProperty> It(Class, EFieldIteratorFlags::IncludeSuper); It; ++It)
	{
		if (It->Struct && It->Struct->IsChildOf(FAnimNode_Base::StaticStruct()))
		{
			return *It;
		}
	}
	return nullptr;
}

// The pose a graph node puts out (its "Pose" pin).
UEdGraphPin* PoseOutput(UEdGraphNode* Node)
{
	if (!Node)
	{
		return nullptr;
	}
	if (UEdGraphPin* Pin = Node->FindPin(TEXT("Pose"), EGPD_Output))
	{
		return Pin;
	}
	for (UEdGraphPin* Pin : Node->Pins)
	{
		const UObject* Type = Pin ? Pin->PinType.PinSubCategoryObject.Get() : nullptr;
		if (Pin && Pin->Direction == EGPD_Output && (Type == FPoseLink::StaticStruct() || Type == FComponentSpacePoseLink::StaticStruct()))
		{
			return Pin;
		}
	}
	return nullptr;
}

UEnum* EnumOfProperty(const FProperty* Property)
{
	if (const FEnumProperty* EnumProperty = CastField<FEnumProperty>(Property))
	{
		return EnumProperty->GetEnum();
	}
	if (const FByteProperty* ByteProperty = CastField<FByteProperty>(Property))
	{
		return ByteProperty->Enum;
	}
	return nullptr;
}

UEnum* EnumOfPin(const UEdGraphPin* Pin)
{
	return Pin ? Cast<UEnum>(Pin->PinType.PinSubCategoryObject.Get()) : nullptr;
}

FString EnumEntryText(const UEnum* Enum, int64 Value)
{
	const int32 Index = Enum ? Enum->GetIndexByValue(Value) : INDEX_NONE;
	return Index == INDEX_NONE ? FString::Printf(TEXT("%lld"), Value) : Enum->GetNameStringByIndex(Index);
}

// ImportText into a property of an object (or of a struct in it); false with the reason when the text did not read.
bool ImportInto(FProperty* Property, void* Container, UObject* Owner, const FString& Text, FString& OutProblem)
{
	FStringOutputDevice Errors;
	const TCHAR* End = Property->ImportText(*Text, Property->ContainerPtrToValuePtr<void>(Container), PPF_None, Owner, &Errors);
	if (!End || !Errors.IsEmpty())
	{
		OutProblem = Errors.IsEmpty() ? FString(TEXT("the text does not read")) : FString(Errors).TrimStartAndEnd().Left(300);
		return End != nullptr;   // (a warning with a value read is kept)
	}
	return true;
}

// The graph node classes a template names (End's AnimGraphNode_End* are ENDEditor's; the rest are the engine's).
UClass* FindNodeClass(const FString& Name)
{
	UClass* Class = FindObject<UClass>(ANY_PACKAGE, *Name);
	if (!Class)
	{
		for (const TCHAR* Module : {TEXT("/Script/ENDEditor."), TEXT("/Script/AnimGraph."), TEXT("/Script/EndEditor.")})
		{
			Class = FindObject<UClass>(nullptr, *(FString(Module) + Name));
			if (Class)
			{
				break;
			}
		}
	}
	return Class;
}

// ------------------------------------------------------------------------------------------------
struct FMachine
{
	UAnimGraphNode_StateMachineBase* Node = nullptr;
	UAnimationStateMachineGraph* Graph = nullptr;
	TMap<FString, UAnimStateNodeBase*> States;
};

// Where the next rule node goes: columns to the left of the result node, rows per column.
struct FRuleContext
{
	UEdGraph* Graph = nullptr;
	FMachine* Machine = nullptr;
	FString Where;
	FVector2D Origin = FVector2D::ZeroVector;
	TMap<int32, int32> Rows;
};

class FBuilder
{
public:
	FBuilder(UAnimBlueprint* InBlueprint, UClass* InParent, RebirthAnimTemplate::FBuildReport& InReport)
		: Blueprint(InBlueprint), Parent(InParent), Report(InReport)
	{
		Native = Parent;
		while (Native && !Native->HasAnyClassFlags(CLASS_Native))
		{
			Native = Native->GetSuperClass();
		}
	}

	bool Build(const FJsonObj& Template)
	{
		UEdGraph* AnimGraph = nullptr;
		for (UEdGraph* Graph : Blueprint->FunctionGraphs)
		{
			if (Graph && Graph->GetFName() == UEdGraphSchema_K2::GN_AnimGraph)
			{
				AnimGraph = Graph;
				break;
			}
		}
		if (!AnimGraph)
		{
			Error(TEXT("the new AnimBlueprint has no AnimGraph"));
			return false;
		}
		UAnimGraphNode_Root* Root = nullptr;
		for (UEdGraphNode* Node : AnimGraph->Nodes)
		{
			if (UAnimGraphNode_Root* Each = Cast<UAnimGraphNode_Root>(Node))
			{
				Root = Each;
				break;
			}
		}
		if (!Root)
		{
			Error(TEXT("the new AnimBlueprint's AnimGraph has no Output Pose node"));
			return false;
		}
		// 1. the AnimGraph
		const FJsonObj Main = Obj(Template, TEXT("anim_graph"));
		if (!MakeGraph(AnimGraph, Main, TEXT("AnimGraph")))
		{
			return false;
		}
		const FString First = Str(Main, TEXT("result"));
		if (!First.IsEmpty())
		{
			LinkPose(First, Root->FindPin(TEXT("Result"), EGPD_Input), TEXT("AnimGraph: Output Pose"));
		}
		Report.AnimGraphNodes = Nodes.Num();
		// 2. the state machines (their nodes are in the graphs above)
		if (const TArray<TSharedPtr<FJsonValue>>* MachineList = Arr(Template, TEXT("machines")))
		{
			for (const TSharedPtr<FJsonValue>& Value : *MachineList)
			{
				MakeMachine(Value->AsObject());
			}
		}
		return Report.Errors.Num() == 0;
	}

	// The class defaults (on the compiled class's default object).
	void ApplyDefaults(const FJsonObj& Template)
	{
		const FJsonObj Defaults = Obj(Template, TEXT("defaults"));
		UClass* Class = Blueprint->GeneratedClass;
		UObject* CDO = Class ? Class->GetDefaultObject() : nullptr;
		if (!Defaults.IsValid() || !CDO)
		{
			return;
		}
		CDO->Modify();
		for (const TPair<FString, TSharedPtr<FJsonValue>>& Pair : Defaults->Values)
		{
			FProperty* Property = FindFProperty<FProperty>(Class, *Pair.Key);
			if (!Property)
			{
				Warn(FString::Printf(TEXT("class default %s: the class has no such property (left out)"), *Pair.Key));
				continue;
			}
			FString Problem;
			if (!ImportInto(Property, CDO, CDO, Pair.Value->AsString(), Problem))
			{
				Warn(FString::Printf(TEXT("class default %s = %s: %s (left as the parent's)"), *Pair.Key, *Pair.Value->AsString().Left(120), *Problem));
				continue;
			}
			if (!Problem.IsEmpty())
			{
				Warn(FString::Printf(TEXT("class default %s: %s"), *Pair.Key, *Problem));
			}
			++Report.Defaults;
		}
	}

private:
	UAnimBlueprint* Blueprint;
	UClass* Parent;
	UClass* Native = nullptr;
	RebirthAnimTemplate::FBuildReport& Report;
	TMap<FString, UAnimGraphNode_Base*> Nodes;        // by the template's node ids
	TMap<FString, FJsonObj> NodeDescs;
	TMap<FString, FMachine> Machines;                 // by their machine node's id

	void Error(const FString& Text) { Report.Errors.Add(Text); }
	void Warn(const FString& Text) { Report.Warnings.Add(Text); }

	// --- anim nodes
	UAnimGraphNode_Base* MakeAnimNode(UEdGraph* Graph, const FJsonObj& Desc, const FString& Where)
	{
		const FString Id = Str(Desc, TEXT("id"));
		const FString ClassName = Str(Desc, TEXT("cls"));
		UClass* Class = FindNodeClass(ClassName);
		if (!Class || !Class->IsChildOf(UAnimGraphNode_Base::StaticClass()) || Class->HasAnyClassFlags(CLASS_Abstract))
		{
			Error(FString::Printf(TEXT("%s: %s needs the AnimGraph node %s, which this editor does not have%s"), *Where, *Id, *ClassName,
				ClassName.StartsWith(TEXT("AnimGraphNode_End")) ? TEXT(" (End's editor module: build it with Tools\\RebirthSkelCompat\\run_build_editor119.cmd)") : TEXT("")));
			return nullptr;
		}
		UAnimGraphNode_Base* Node = NewObject<UAnimGraphNode_Base>(Graph, Class, NAME_None, RF_Transactional);
		// the node's settings before its pins: a pin shown takes its default from the node
		FStructProperty* NodeProperty = AnimNodeProperty(Class);
		if (NodeProperty)
		{
			void* NodeData = NodeProperty->ContainerPtrToValuePtr<void>(Node);
			if (const FJsonObj Values = Obj(Desc, TEXT("values")))
			{
				for (const TPair<FString, TSharedPtr<FJsonValue>>& Pair : Values->Values)
				{
					FProperty* Member = NodeProperty->Struct->FindPropertyByName(FName(*Pair.Key));
					if (!Member)
					{
						Warn(FString::Printf(TEXT("%s: %s has no setting %s (left out)"), *Where, *Id, *Pair.Key));
						continue;
					}
					FString Problem;
					if (!ImportInto(Member, NodeData, Node, Pair.Value->AsString(), Problem) || !Problem.IsEmpty())
					{
						Warn(FString::Printf(TEXT("%s: %s.%s = %s: %s"), *Where, *Id, *Pair.Key, *Pair.Value->AsString().Left(120), *Problem));
					}
				}
			}
			// an asset player's sync group is its Sync Group setting (copied into the node as it compiles)
			if (FStructProperty* SyncGroup = FindFProperty<FStructProperty>(Class, TEXT("SyncGroup")))
			{
				void* SyncData = SyncGroup->ContainerPtrToValuePtr<void>(Node);
				for (const TCHAR* Member : {TEXT("GroupName"), TEXT("GroupRole"), TEXT("GroupScope")})
				{
					FProperty* From = NodeProperty->Struct->FindPropertyByName(Member);
					FProperty* To = SyncGroup->Struct->FindPropertyByName(Member);
					if (From && To && From->SameType(To))
					{
						To->CopyCompleteValue(To->ContainerPtrToValuePtr<void>(SyncData), From->ContainerPtrToValuePtr<void>(NodeData));
					}
				}
			}
		}
		AddToGraph(Graph, Node, Pos(Desc, FVector2D::ZeroVector));
		Nodes.Add(Id, Node);
		NodeDescs.Add(Id, Desc);
		return Node;
	}

	bool MakeGraph(UEdGraph* Graph, const FJsonObj& Desc, const FString& Where)
	{
		const TArray<TSharedPtr<FJsonValue>>* List = Arr(Desc, TEXT("nodes"));
		if (!List)
		{
			return true;
		}
		TArray<FJsonObj> Made;
		for (const TSharedPtr<FJsonValue>& Value : *List)
		{
			const FJsonObj NodeDesc = Value->AsObject();
			if (MakeAnimNode(Graph, NodeDesc, Where))
			{
				Made.Add(NodeDesc);
			}
		}
		// the pose links, then the pins bound to the class's variables
		for (const FJsonObj& NodeDesc : Made)
		{
			const FString Id = Str(NodeDesc, TEXT("id"));
			UAnimGraphNode_Base* Node = Nodes.FindRef(Id);
			if (const FJsonObj Links = Obj(NodeDesc, TEXT("links")))
			{
				for (const TPair<FString, TSharedPtr<FJsonValue>>& Pair : Links->Values)
				{
					LinkPose(Pair.Value->AsString(), Node->FindPin(FName(*Pair.Key), EGPD_Input), FString::Printf(TEXT("%s: %s.%s"), *Where, *Id, *Pair.Key));
				}
			}
			if (const TArray<TSharedPtr<FJsonValue>>* Bindings = Arr(NodeDesc, TEXT("bindings")))
			{
				int32 Row = 0;
				for (const TSharedPtr<FJsonValue>& Binding : *Bindings)
				{
					Bind(Graph, Node, Binding->AsObject(), Row++, Where);
				}
			}
		}
		return true;
	}

	void LinkPose(const FString& FromId, UEdGraphPin* To, const FString& Where)
	{
		UAnimGraphNode_Base* From = Nodes.FindRef(FromId);
		UEdGraphPin* Out = PoseOutput(From);
		if (!To || !Out)
		{
			Error(FString::Printf(TEXT("%s: no pose link from %s (%s)"), *Where, *FromId, !To ? TEXT("no such input pin") : TEXT("no such node")));
			return;
		}
		if (!Link(Out, To))
		{
			Error(FString::Printf(TEXT("%s: the editor does not link %s's pose there (%s space)"), *Where, *FromId,
				Out->PinType.PinSubCategoryObject.Get() == FComponentSpacePoseLink::StaticStruct() ? TEXT("component") : TEXT("local")));
		}
	}

	// A link as the editor makes one (the nodes told, as the graph editor tells them after a drag).
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

	// A node's pin bound to one of the class's variables (the game's "property access" copies): a variable get linked to it.
	void Bind(UEdGraph* Graph, UAnimGraphNode_Base* Node, const FJsonObj& Binding, int32 Row, const FString& Where)
	{
		const FString PinName = Str(Binding, TEXT("pin"));
		const FString Var = Str(Binding, TEXT("var"));
		UEdGraphPin* Pin = Node->FindPin(FName(*PinName), EGPD_Input);
		if (!Pin)
		{
			// a hidden pin: shown first
			for (FOptionalPinFromProperty& Option : Node->ShowPinForProperties)
			{
				if (Option.PropertyName == FName(*PinName))
				{
					Option.bShowPin = true;
				}
			}
			Node->ReconstructNode();
			Pin = Node->FindPin(FName(*PinName), EGPD_Input);
		}
		FProperty* Property = FindFProperty<FProperty>(Parent, *Var);
		if (!Pin || !Property || Var.Contains(TEXT(".")))
		{
			Warn(FString::Printf(TEXT("%s: %s.%s is not bound to %s (%s)"), *Where, *Node->GetName(), *PinName, *Var,
				!Pin ? TEXT("no such pin") : TEXT("no such variable")));
			return;
		}
		UK2Node_VariableGet* Get = NewObject<UK2Node_VariableGet>(Graph);
		Get->SetFromProperty(Property, /*bSelfContext*/ true, Property->GetOwnerClass());
		AddToGraph(Graph, Get, FVector2D(Node->NodePosX - 260, Node->NodePosY + 60 + 60 * Row));
		if (!Link(Get->GetValuePin(), Pin))
		{
			Warn(FString::Printf(TEXT("%s: %s.%s could not be linked to %s"), *Where, *Node->GetName(), *PinName, *Var));
			return;
		}
		++Report.Bindings;
	}

	// --- state machines
	void MakeMachine(const FJsonObj& Desc)
	{
		const FString NodeId = Str(Desc, TEXT("node"));
		const FString Name = Str(Desc, TEXT("name"));
		UAnimGraphNode_StateMachineBase* MachineNode = Cast<UAnimGraphNode_StateMachineBase>(Nodes.FindRef(NodeId));
		if (!MachineNode || !MachineNode->EditorStateMachineGraph)
		{
			Error(FString::Printf(TEXT("state machine %s: its node %s is not in the AnimGraph"), *Name, *NodeId));
			return;
		}
		FMachine& Machine = Machines.Add(NodeId);
		Machine.Node = MachineNode;
		Machine.Graph = MachineNode->EditorStateMachineGraph;
		MachineNode->OnRenameNode(Name);
		UEdGraph* Graph = Machine.Graph;
		// the states and conduits
		const TArray<TSharedPtr<FJsonValue>>* States = Arr(Desc, TEXT("states"));
		if (States)
		{
			for (const TSharedPtr<FJsonValue>& Value : *States)
			{
				const FJsonObj State = Value->AsObject();
				const FString StateName = Str(State, TEXT("name"));
				const bool bConduit = State->GetBoolField(TEXT("conduit"));
				UAnimStateNodeBase* Node = bConduit ? static_cast<UAnimStateNodeBase*>(NewObject<UAnimStateConduitNode>(Graph))
					: static_cast<UAnimStateNodeBase*>(NewObject<UAnimStateNode>(Graph));
				AddToGraph(Graph, Node, Pos(State, FVector2D::ZeroVector));
				Node->OnRenameNode(StateName);
				if (Node->GetStateName() != StateName)
				{
					Warn(FString::Printf(TEXT("%s: the state %s is named %s here"), *Name, *StateName, *Node->GetStateName()));
				}
				Machine.States.Add(StateName, Node);
				if (bConduit)
				{
					++Report.Conduits;
				}
				else
				{
					++Report.States;
				}
			}
			// what is in them (the states' graphs; the conduits' rules)
			for (const TSharedPtr<FJsonValue>& Value : *States)
			{
				const FJsonObj State = Value->AsObject();
				const FString StateName = Str(State, TEXT("name"));
				UAnimStateNodeBase* Base = Machine.States.FindRef(StateName);
				const FString Where = Name + TEXT("/") + StateName;
				if (UAnimStateNode* StateNode = Cast<UAnimStateNode>(Base))
				{
					MakeGraph(StateNode->BoundGraph, State, Where);
					const FString Result = Str(State, TEXT("result"));
					if (!Result.IsEmpty())
					{
						LinkPose(Result, StateNode->GetPoseSinkPinInsideState(), Where + TEXT(": Output Animation Pose"));
					}
					StateNode->bAlwaysResetOnEntry = State->GetBoolField(TEXT("reset_on_entry"));
					SetNotify(StateNode->StateEntered, State, TEXT("entered"));
					SetNotify(StateNode->StateLeft, State, TEXT("left"));
					SetNotify(StateNode->StateFullyBlended, State, TEXT("fully_blended"));
				}
				else if (UAnimStateConduitNode* Conduit = Cast<UAnimStateConduitNode>(Base))
				{
					MakeRule(Conduit->BoundGraph, Obj(State, TEXT("rule")), &Machine, Where);
				}
			}
		}
		// the entry
		const FString Initial = Str(Desc, TEXT("initial"));
		UAnimStateNodeBase* First = Machine.States.FindRef(Initial);
		UEdGraphPin* EntryPin = Machine.Graph->EntryNode && Machine.Graph->EntryNode->Pins.Num() > 0 ? Machine.Graph->EntryNode->Pins[0] : nullptr;
		if (!First || !EntryPin || !Link(EntryPin, First->GetInputPin()))
		{
			Error(FString::Printf(TEXT("state machine %s: its entry is not linked to %s"), *Name, *Initial));
		}
		// the transitions, each with its rule
		if (const TArray<TSharedPtr<FJsonValue>>* Transitions = Arr(Desc, TEXT("transitions")))
		{
			for (const TSharedPtr<FJsonValue>& Value : *Transitions)
			{
				MakeTransition(Machine, Value->AsObject(), Name);
			}
		}
	}

	void SetNotify(FAnimNotifyEvent& Event, const FJsonObj& Desc, const TCHAR* Field)
	{
		FString Name;
		if (Desc->TryGetStringField(Field, Name) && !Name.IsEmpty())
		{
			Event.NotifyName = FName(*Name);
		}
	}

	void MakeTransition(FMachine& Machine, const FJsonObj& Desc, const FString& MachineName)
	{
		const FString Source = Str(Desc, TEXT("source"));
		const FString Target = Str(Desc, TEXT("target"));
		const FString Where = FString::Printf(TEXT("%s: %s -> %s"), *MachineName, *Source, *Target);
		UAnimStateNodeBase* From = Machine.States.FindRef(Source);
		UAnimStateNodeBase* To = Machine.States.FindRef(Target);
		if (!From || !To)
		{
			Error(Where + TEXT(": no such state"));
			return;
		}
		UAnimStateTransitionNode* Transition = NewObject<UAnimStateTransitionNode>(Machine.Graph);
		AddToGraph(Machine.Graph, Transition, FVector2D((From->NodePosX + To->NodePosX) / 2, (From->NodePosY + To->NodePosY) / 2));
		Transition->CreateConnections(From, To);
		// its settings (by the properties' own names, as the details panel sets them)
		auto Set = [this, Transition, &Where](const TCHAR* Property, const FString& Text)
		{
			FProperty* P = FindFProperty<FProperty>(UAnimStateTransitionNode::StaticClass(), Property);
			FString Problem;
			if (!P || !ImportInto(P, Transition, Transition, Text, Problem) || !Problem.IsEmpty())
			{
				Warn(FString::Printf(TEXT("%s: %s = %s: %s"), *Where, Property, *Text, P ? *Problem : TEXT("no such setting")));
			}
		};
		double Number = 0.0;
		if (Desc->TryGetNumberField(TEXT("priority"), Number))
		{
			Set(TEXT("PriorityOrder"), FString::FromInt(static_cast<int32>(Number)));
		}
		if (Desc->TryGetNumberField(TEXT("crossfade"), Number))
		{
			Set(TEXT("CrossfadeDuration"), FloatText(Number));
		}
		FString Text;
		if (Desc->TryGetStringField(TEXT("blend_mode"), Text) && !Text.IsEmpty())
		{
			Set(TEXT("BlendMode"), Text);
		}
		if (Desc->TryGetStringField(TEXT("logic"), Text) && !Text.IsEmpty())
		{
			Set(TEXT("LogicType"), Text);
		}
		if (Desc->TryGetStringField(TEXT("custom_curve"), Text) && !Text.IsEmpty())
		{
			Set(TEXT("CustomBlendCurve"), Text);
		}
		if (Desc->TryGetStringField(TEXT("blend_profile"), Text) && !Text.IsEmpty())
		{
			Set(TEXT("BlendProfile"), Text);
		}
		bool bAutomatic = false;
		Desc->TryGetBoolField(TEXT("automatic"), bAutomatic);
		Transition->bAutomaticRuleBasedOnSequencePlayerInState = bAutomatic;
		SetNotify(Transition->TransitionStart, Desc, TEXT("start"));
		SetNotify(Transition->TransitionEnd, Desc, TEXT("end"));
		SetNotify(Transition->TransitionInterrupt, Desc, TEXT("interrupt"));
		if (!bAutomatic)
		{
			MakeRule(Transition->BoundGraph, Obj(Desc, TEXT("rule")), &Machine, Where, From);
		}
		++Report.Transitions;
	}

	// --- rules: an expression tree into a transition (or conduit) graph's result
	void MakeRule(UEdGraph* Graph, const FJsonObj& Rule, FMachine* Machine, const FString& Where, UAnimStateNodeBase* SourceState = nullptr)
	{
		UAnimationTransitionGraph* RuleGraph = Cast<UAnimationTransitionGraph>(Graph);
		UAnimGraphNode_TransitionResult* Result = RuleGraph ? RuleGraph->GetResultNode() : nullptr;
		UEdGraphPin* Pin = Result ? Result->FindPin(TEXT("bCanEnterTransition"), EGPD_Input) : nullptr;
		if (!Pin)
		{
			Error(Where + TEXT(": its rule graph has no result"));
			return;
		}
		FRuleContext Context;
		Context.Graph = Graph;
		Context.Machine = Machine;
		Context.Where = Where;
		Context.Origin = FVector2D(Result->NodePosX, Result->NodePosY);
		if (!Rule.IsValid())
		{
			SetDefault(Pin, TEXT("true"));
			return;
		}
		CurrentSource = SourceState;
		Connect(Rule, Pin, Context, 0);
		CurrentSource = nullptr;
	}

	UAnimStateNodeBase* CurrentSource = nullptr;

	FVector2D NextSpot(FRuleContext& Context, int32 Depth)
	{
		int32& Row = Context.Rows.FindOrAdd(Depth);
		const FVector2D Spot(Context.Origin.X - 320.f * (Depth + 1), Context.Origin.Y + 130.f * Row);
		++Row;
		return Spot;
	}

	void SetDefault(UEdGraphPin* Pin, const FString& Value)
	{
		if (const UEdGraphSchema* Schema = Pin->GetOwningNode()->GetSchema())
		{
			Schema->TrySetDefaultValue(*Pin, Value);
		}
		else
		{
			Pin->DefaultValue = Value;
		}
	}

	// A constant as Pin's value: an enum pin takes the entry's name.
	void SetConstant(const FJsonObj& Expr, UEdGraphPin* Pin, FRuleContext& Context)
	{
		const FString Type = Str(Expr, TEXT("type"));
		const TSharedPtr<FJsonValue> Value = Expr->TryGetField(TEXT("value"));
		if (!Value.IsValid())
		{
			return;
		}
		const FName Category = Pin->PinType.PinCategory;
		FString Text;
		if (Type == TEXT("bool"))
		{
			Text = Value->AsBool() ? TEXT("true") : TEXT("false");
		}
		else if (Type == TEXT("name"))
		{
			Text = Value->AsString();
		}
		else if (Category == UEdGraphSchema_K2::PC_Float)
		{
			Text = FloatText(Value->AsNumber());
		}
		else if (UEnum* Enum = EnumOfPin(Pin))
		{
			Text = EnumEntryText(Enum, static_cast<int64>(Value->AsNumber()));
		}
		else if (Category == UEdGraphSchema_K2::PC_Boolean)
		{
			Text = Value->AsNumber() != 0.0 ? TEXT("true") : TEXT("false");
		}
		else if (Type == TEXT("float"))
		{
			Text = FloatText(Value->AsNumber());
		}
		else
		{
			Text = FString::Printf(TEXT("%lld"), static_cast<int64>(Value->AsNumber()));
		}
		SetDefault(Pin, Text);
	}

	// The enum an expression's value has (a variable's, a function's return value's), if any.
	UEnum* EnumOf(const FJsonObj& Expr)
	{
		const FString Op = Str(Expr, TEXT("op"));
		if (Op == TEXT("var"))
		{
			return EnumOfProperty(FindFProperty<FProperty>(Parent, *Str(Expr, TEXT("name"))));
		}
		if (Op == TEXT("call"))
		{
			if (UFunction* Function = FindFunction(Expr))
			{
				return EnumOfProperty(Function->GetReturnProperty());
			}
		}
		if (Op == TEXT("select"))
		{
			if (const TArray<TSharedPtr<FJsonValue>>* Options = Arr(Expr, TEXT("options")))
			{
				for (const TSharedPtr<FJsonValue>& Option : *Options)
				{
					const TArray<TSharedPtr<FJsonValue>>& Pair = Option->AsArray();
					if (Pair.Num() == 2)
					{
						if (UEnum* Enum = EnumOf(Pair[1]->AsObject()))
						{
							return Enum;
						}
					}
				}
			}
		}
		return nullptr;
	}

	UFunction* FindFunction(const FJsonObj& Expr)
	{
		const FString Class = Str(Expr, TEXT("cls"));
		const FName Name(*Str(Expr, TEXT("func")));
		if (Class == TEXT("self"))
		{
			return Parent->FindFunctionByName(Name);
		}
		if (Class == TEXT("KismetMathLibrary"))
		{
			return UKismetMathLibrary::StaticClass()->FindFunctionByName(Name);
		}
		UClass* Library = FindObject<UClass>(ANY_PACKAGE, *Class);
		return Library ? Library->FindFunctionByName(Name) : nullptr;
	}

	// Expr's value into Pin: a constant as its default value, anything else as nodes linked to it.
	void Connect(const FJsonObj& Expr, UEdGraphPin* Pin, FRuleContext& Context, int32 Depth)
	{
		if (!Expr.IsValid() || !Pin)
		{
			return;
		}
		const FString Op = Str(Expr, TEXT("op"));
		if (Op == TEXT("const"))
		{
			SetConstant(Expr, Pin, Context);
			return;
		}
		UEdGraphPin* Out = MakeValue(Expr, Pin, Context, Depth);
		if (Out && !Out->LinkedTo.Contains(Pin) && !Link(Out, Pin))
		{
			Warn(FString::Printf(TEXT("%s: a %s could not be linked to %s"), *Context.Where, *Op, *Pin->PinName.ToString()));
		}
	}

	// The nodes for a value; their output pin (null when Expr linked itself to Target, as a select does).
	UEdGraphPin* MakeValue(const FJsonObj& Expr, UEdGraphPin* Target, FRuleContext& Context, int32 Depth)
	{
		const FString Op = Str(Expr, TEXT("op"));
		UEdGraph* Graph = Context.Graph;
		if (Op == TEXT("var"))
		{
			const FString Name = Str(Expr, TEXT("name"));
			FProperty* Property = FindFProperty<FProperty>(Parent, *Name);
			if (!Property)
			{
				Error(FString::Printf(TEXT("%s: the class has no variable %s"), *Context.Where, *Name));
				return nullptr;
			}
			UK2Node_VariableGet* Get = NewObject<UK2Node_VariableGet>(Graph);
			Get->SetFromProperty(Property, /*bSelfContext*/ true, Property->GetOwnerClass());
			AddToGraph(Graph, Get, NextSpot(Context, Depth));
			++Report.RuleNodes;
			return Get->GetValuePin();
		}
		if (Op == TEXT("time"))
		{
			return MakeGetter(Expr, Context, Depth);
		}
		if (Op == TEXT("select"))
		{
			MakeSelect(Expr, Target, Context, Depth);
			return nullptr;
		}
		if (Op == TEXT("call"))
		{
			return MakeCall(Expr, Context, Depth);
		}
		Error(FString::Printf(TEXT("%s: the builder cannot make a rule part %s"), *Context.Where, *Op));
		return nullptr;
	}

	UEdGraphPin* MakeGetter(const FJsonObj& Expr, FRuleContext& Context, int32 Depth)
	{
		const FString Func = Str(Expr, TEXT("func"));
		const FString StateName = Str(Expr, TEXT("state"));
		UFunction* Getter = UAnimInstance::StaticClass()->FindFunctionByName(FName(*Func));
		UAnimStateNodeBase* State = Context.Machine ? Context.Machine->States.FindRef(StateName) : nullptr;
		if (!Getter || !State || !Context.Machine)
		{
			Error(FString::Printf(TEXT("%s: no %s for the state %s"), *Context.Where, *Func, *StateName));
			return nullptr;
		}
		if (CurrentSource && State != CurrentSource)
		{
			Warn(FString::Printf(TEXT("%s: %s asks about %s, not the state the transition leaves"), *Context.Where, *Func, *StateName));
		}
		UK2Node_AnimGetter* Node = NewObject<UK2Node_AnimGetter>(Context.Graph);
		Node->SourceNode = Context.Machine->Node;
		Node->SourceStateNode = State;
		Node->GetterClass = Native;
		Node->SourceAnimBlueprint = Blueprint;
		Node->SetFromFunction(Getter);
		Node->CachedTitle = FText::Format(LOCTEXT("GetterTitle", "{0} ({1})"), Getter->GetDisplayNameText(), FText::FromString(State->GetStateName()));
		Getter->GetMetaData(TEXT("GetterContext")).ParseIntoArray(Node->Contexts, TEXT("|"), true);
		AddToGraph(Context.Graph, Node, NextSpot(Context, Depth));
		++Report.RuleNodes;
		return Node->GetReturnValuePin();
	}

	UEdGraphPin* MakeCall(const FJsonObj& Expr, FRuleContext& Context, int32 Depth)
	{
		const FString Func = Str(Expr, TEXT("func"));
		const TArray<TSharedPtr<FJsonValue>>* ArgsPtr = Arr(Expr, TEXT("args"));
		TArray<FJsonObj> Args;
		if (ArgsPtr)
		{
			for (const TSharedPtr<FJsonValue>& Value : *ArgsPtr)
			{
				Args.Add(Value->AsObject());
			}
		}
		// == and != on enum values: the editor's enum compare nodes (they compile to EqualEqual_ByteByte / NotEqual_ByteByte)
		const bool bEqual = Func == TEXT("EqualEqual_ByteByte");
		const bool bNotEqual = Func == TEXT("NotEqual_ByteByte");
		if ((bEqual || bNotEqual) && Args.Num() == 2)
		{
			UEnum* Enum = EnumOf(Args[0]);
			if (!Enum)
			{
				Enum = EnumOf(Args[1]);
			}
			if (Enum)
			{
				UK2Node_EnumEquality* Node = bNotEqual ? NewObject<UK2Node_EnumInequality>(Context.Graph) : NewObject<UK2Node_EnumEquality>(Context.Graph);
				AddToGraph(Context.Graph, Node, NextSpot(Context, Depth));
				++Report.RuleNodes;
				// the non-constant side first: linking it gives both pins the enum
				const int32 Order[2] = {Str(Args[0], TEXT("op")) == TEXT("const") ? 1 : 0, Str(Args[0], TEXT("op")) == TEXT("const") ? 0 : 1};
				for (int32 Index : Order)
				{
					UEdGraphPin* Pin = Index == 0 ? Node->GetInput1Pin() : Node->GetInput2Pin();
					Connect(Args[Index], Pin, Context, Depth + 1);
				}
				return Node->GetReturnValuePin();
			}
		}
		UFunction* Function = FindFunction(Expr);
		if (!Function)
		{
			Error(FString::Printf(TEXT("%s: no function %s.%s"), *Context.Where, *Str(Expr, TEXT("cls")), *Func));
			return nullptr;
		}
		const bool bOperator = Function->HasMetaData(TEXT("CommutativeAssociativeBinaryOperator"));
		UK2Node_CallFunction* Node = bOperator ? NewObject<UK2Node_CommutativeAssociativeBinaryOperator>(Context.Graph) : NewObject<UK2Node_CallFunction>(Context.Graph);
		Node->SetFromFunction(Function);
		AddToGraph(Context.Graph, Node, NextSpot(Context, Depth));
		++Report.RuleNodes;
		int32 Index = 0;
		for (TFieldIterator<FProperty> It(Function); It && (It->PropertyFlags & CPF_Parm); ++It)
		{
			if (It->HasAnyPropertyFlags(CPF_ReturnParm) || (It->HasAnyPropertyFlags(CPF_OutParm) && !It->HasAnyPropertyFlags(CPF_ReferenceParm)))
			{
				continue;
			}
			if (!Args.IsValidIndex(Index))
			{
				break;
			}
			UEdGraphPin* Pin = Node->FindPin(It->GetFName(), EGPD_Input);
			if (!Pin)
			{
				Error(FString::Printf(TEXT("%s: %s has no pin %s"), *Context.Where, *Func, *It->GetName()));
			}
			else
			{
				Connect(Args[Index], Pin, Context, Depth + 1);
			}
			++Index;
		}
		if (Index != Args.Num())
		{
			Warn(FString::Printf(TEXT("%s: %s takes %d value(s), the template gives %d"), *Context.Where, *Func, Index, Args.Num()));
		}
		return Node->GetReturnValuePin();
	}

	// A select on an enum (the game's rules pick a value by the behavior mode): its index first (that names its option
	// pins), its output linked to Target (that gives the options their type), then the options.
	void MakeSelect(const FJsonObj& Expr, UEdGraphPin* Target, FRuleContext& Context, int32 Depth)
	{
		UK2Node_Select* Node = NewObject<UK2Node_Select>(Context.Graph);
		AddToGraph(Context.Graph, Node, NextSpot(Context, Depth));
		++Report.RuleNodes;
		Connect(Obj(Expr, TEXT("index")), Node->GetIndexPin(), Context, Depth + 1);
		UEnum* Enum = Node->GetEnum();
		if (!Enum)
		{
			Error(Context.Where + TEXT(": a select whose index is not an enum (the builder makes enum selects only)"));
			return;
		}
		if (!Link(Node->GetReturnValuePin(), Target))
		{
			Error(Context.Where + TEXT(": a select's value could not be linked"));
			return;
		}
		if (const TArray<TSharedPtr<FJsonValue>>* Options = Arr(Expr, TEXT("options")))
		{
			for (const TSharedPtr<FJsonValue>& Option : *Options)
			{
				const TArray<TSharedPtr<FJsonValue>>& Pair = Option->AsArray();
				if (Pair.Num() != 2)
				{
					continue;
				}
				const FString Entry = EnumEntryText(Enum, static_cast<int64>(Pair[0]->AsNumber()));
				UEdGraphPin* Pin = Node->FindPin(FName(*Entry), EGPD_Input);
				if (!Pin)
				{
					Error(FString::Printf(TEXT("%s: the select has no option %s"), *Context.Where, *Entry));
					continue;
				}
				Connect(Pair[1]->AsObject(), Pin, Context, Depth + 1);
			}
		}
	}
};

FString Join(const TArray<FString>& Lines, const TCHAR* Prefix)
{
	FString Out;
	for (const FString& Line : Lines)
	{
		Out += Prefix + Line + TEXT("\n");
	}
	return Out;
}

TArray<TSharedPtr<FJsonValue>> JsonList(const TArray<FString>& Lines)
{
	TArray<TSharedPtr<FJsonValue>> Out;
	for (const FString& Line : Lines)
	{
		Out.Add(MakeShared<FJsonValueString>(Line));
	}
	return Out;
}

FString JsonText(const TSharedRef<FJsonObject>& Object)
{
	FString Out;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Out);
	FJsonSerializer::Serialize(Object, Writer);
	return Out;
}

bool SavePackageAsset(UPackage* Package, UObject* Asset, FString& OutProblem)
{
	const FString Filename = FPackageName::LongPackageNameToFilename(Package->GetName(), FPackageName::GetAssetPackageExtension());
	IFileManager::Get().MakeDirectory(*FPaths::GetPath(Filename), true);
	if (!UPackage::SavePackage(Package, Asset, RF_Public | RF_Standalone, *Filename, GWarn, nullptr, false, true, SAVE_NoError))
	{
		OutProblem = TEXT("could not be saved to ") + Filename;
		return false;
	}
	return true;
}

// --- Cook For Game (as the Parts Builder's skins, EndSkins.cpp: a versioned cook, then the engine's IoStore commandlet)
bool CookOne(UPackage* Package, const ITargetPlatform* Platform, const FString& Filename, FString& OutProblem)
{
	Package->FullyLoad();
	TArray<UObject*> Objects;
	GetObjectsWithOuter(Package, Objects, true);
	for (UObject* Object : Objects)
	{
		Object->BeginCacheForCookedPlatformData(Platform);
	}
	const double Started = FPlatformTime::Seconds();
	for (;;)
	{
		bool bAll = true;
		for (UObject* Object : Objects)
		{
			if (!Object->IsCachedCookedPlatformDataLoaded(Platform))
			{
				bAll = false;
				break;
			}
		}
		if (bAll)
		{
			break;
		}
		if (GShaderCompilingManager)
		{
			GShaderCompilingManager->ProcessAsyncResults(true, false);
		}
		if (FPlatformTime::Seconds() - Started > 600.0)
		{
			OutProblem = TEXT("its platform data was not ready after 10 minutes");
			return false;
		}
		FPlatformProcess::Sleep(0.02f);
	}
	IFileManager::Get().MakeDirectory(*FPaths::GetPath(Filename), true);
	const uint32 Flags = Package->GetPackageFlags();
	Package->SetPackageFlags(PKG_FilterEditorOnly);
	const bool bSaved = UPackage::SavePackage(Package, nullptr, RF_Public, *Filename, GWarn, nullptr, false, false,
		SAVE_NoError | SAVE_KeepGUID | SAVE_Async, Platform, FDateTime::MinValue(), false);
	Package->SetPackageFlagsTo(Flags);
	for (UObject* Object : Objects)
	{
		Object->ClearAllCachedCookedPlatformData();
	}
	if (!bSaved)
	{
		OutProblem = TEXT("could not be cooked to ") + Filename;
	}
	return bSaved;
}

// A cooked .uasset written whole (no .uexp): split at its summary's TotalHeaderSize, as the cooker splits it.
bool SplitCooked(const FString& UAsset, FString& OutProblem)
{
	TArray<uint8> Data;
	if (!FFileHelper::LoadFileToArray(Data, *UAsset) || Data.Num() < 32)
	{
		OutProblem = TEXT("cannot read ") + UAsset;
		return false;
	}
	auto U32 = [&Data](int32 At) { return static_cast<uint32>(Data[At]) | (static_cast<uint32>(Data[At + 1]) << 8) | (static_cast<uint32>(Data[At + 2]) << 16) | (static_cast<uint32>(Data[At + 3]) << 24); };
	const int32 Legacy = static_cast<int32>(U32(4));
	if (U32(0) != 0x9E2A83C1u || (Legacy != -7 && Legacy != -6))
	{
		OutProblem = UAsset + TEXT(" is not a package this editor writes");
		return false;
	}
	const uint32 CustomVersions = U32(20);
	const int64 At = 24 + static_cast<int64>(CustomVersions) * 20;
	if (CustomVersions > 100000 || At + 4 > Data.Num())
	{
		OutProblem = UAsset + TEXT("'s summary does not read");
		return false;
	}
	const int32 HeaderSize = static_cast<int32>(U32(static_cast<int32>(At)));
	if (HeaderSize <= 0 || HeaderSize > Data.Num())
	{
		OutProblem = UAsset + TEXT("'s header size does not read");
		return false;
	}
	const TArray<uint8> Header(Data.GetData(), HeaderSize);
	const TArray<uint8> Exports(Data.GetData() + HeaderSize, Data.Num() - HeaderSize);
	if (!FFileHelper::SaveArrayToFile(Exports, *FPaths::ChangeExtension(UAsset, TEXT(".uexp"))) || !FFileHelper::SaveArrayToFile(Header, *UAsset))
	{
		OutProblem = TEXT("cannot write ") + FPaths::ChangeExtension(UAsset, TEXT(".uexp"));
		return false;
	}
	return true;
}

int32 CommandletResult(const FString& LogText)
{
	const TCHAR* const Marker = TEXT("finished execution (result ");
	const int32 At = LogText.Find(Marker, ESearchCase::CaseSensitive, ESearchDir::FromEnd);
	if (At == INDEX_NONE)
	{
		return -1;
	}
	return FCString::Atoi(*LogText.Mid(At + FCString::Strlen(Marker), 12));
}

FString LastErrorLines(const FString& LogText, int32 Count)
{
	TArray<FString> Lines, Errors;
	LogText.ParseIntoArrayLines(Lines);
	for (const FString& Line : Lines)
	{
		if (Line.Contains(TEXT("Error:")))
		{
			Errors.Add(Line.TrimStartAndEnd().Left(400));
		}
	}
	const int32 First = FMath::Max(0, Errors.Num() - Count);
	FString Out;
	for (int32 Index = First; Index < Errors.Num(); ++Index)
	{
		Out += Errors[Index] + TEXT("\n");
	}
	return Out;
}
} // namespace RebirthAnimTemplateUtil

using namespace RebirthAnimTemplateUtil;

// ------------------------------------------------------------------------------------------------
namespace RebirthAnimTemplate
{
FString FBuildReport::ToJson() const
{
	TSharedRef<FJsonObject> Out = MakeShared<FJsonObject>();
	Out->SetBoolField(TEXT("ok"), bOk);
	Out->SetStringField(TEXT("template"), Template);
	Out->SetStringField(TEXT("asset"), Asset);
	Out->SetStringField(TEXT("anim_class"), AnimClass);
	Out->SetStringField(TEXT("compile"), Compile);
	Out->SetNumberField(TEXT("anim_graph_nodes"), AnimGraphNodes);
	Out->SetNumberField(TEXT("states"), States);
	Out->SetNumberField(TEXT("conduits"), Conduits);
	Out->SetNumberField(TEXT("transitions"), Transitions);
	Out->SetNumberField(TEXT("rule_nodes"), RuleNodes);
	Out->SetNumberField(TEXT("bindings"), Bindings);
	Out->SetNumberField(TEXT("defaults"), Defaults);
	Out->SetArrayField(TEXT("errors"), JsonList(Errors));
	Out->SetArrayField(TEXT("warnings"), JsonList(Warnings));
	Out->SetArrayField(TEXT("notes"), JsonList(Notes));
	Out->SetArrayField(TEXT("compiler"), JsonList(Compiler));
	return JsonText(Out);
}

FString FBuildReport::ToText() const
{
	FString Out = bOk ? FString::Printf(TEXT("Made %s (compile: %s).\nIts class: %s\n"), *Asset, *Compile, *AnimClass)
					  : FString(TEXT("The AnimBlueprint was NOT made.\n"));
	Out += FString::Printf(TEXT("From %s: %d AnimGraph node(s), %d state(s), %d conduit(s), %d transition(s) with %d rule node(s), %d binding(s), %d class default(s).\n"),
		*FPaths::GetCleanFilename(Template), AnimGraphNodes, States, Conduits, Transitions, RuleNodes, Bindings, Defaults);
	Out += Join(Errors, TEXT("ERROR: "));
	Out += Join(Compiler, TEXT("compiler: "));
	Out += Join(Warnings, TEXT("warning: "));
	Out += Join(Notes, TEXT("note: "));
	return Out;
}

TArray<FTemplateInfo> Templates()
{
	TArray<FTemplateInfo> Out;
	for (const auto& Entry : TemplateKeys)
	{
		Out.Add(FTemplateInfo{Entry[0], Entry[1], FString()});
	}
	Out[0].Label = TEXT("cloud: Cloud's player AnimBlueprint (most characters)");
	Out[1].Label = TEXT("sephiroth: Sephiroth's player AnimBlueprint");
	Out[2].Label = TEXT("vincent: Vincent's player AnimBlueprint (a gun user)");
	Out[3].Label = TEXT("monster: the bosses' and summons' AnimBlueprint (Leviathan's; no Control Rig)");
	// (more templates without a new build: abp\templates\templates.json; a key already there takes its package and label)
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *FPaths::Combine(TemplateToolDir(), TEXT("templates"), TEXT("templates.json"))))
	{
		return Out;
	}
	TSharedPtr<FJsonObject> Root;
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid() || !Root->TryGetArrayField(TEXT("templates"), List) || !List)
	{
		UE_LOG(LogRebirthAnimTemplate, Warning, TEXT("abp\\templates\\templates.json does not read (its templates are left out)"));
		return Out;
	}
	for (const TSharedPtr<FJsonValue>& Value : *List)
	{
		const TSharedPtr<FJsonObject> Entry = Value.IsValid() ? Value->AsObject() : nullptr;
		FTemplateInfo Info;
		if (!Entry.IsValid() || !Entry->TryGetStringField(TEXT("key"), Info.Key) || !Entry->TryGetStringField(TEXT("package"), Info.Package))
		{
			continue;
		}
		Info.Key = Info.Key.TrimStartAndEnd().ToLower();
		Info.Package = Info.Package.TrimStartAndEnd();
		if (Info.Key.IsEmpty() || Info.Key.Contains(TEXT(":")) || Info.Package.IsEmpty())
		{
			continue;
		}
		FString Label;
		Entry->TryGetStringField(TEXT("label"), Label);
		Label = Label.TrimStartAndEnd();
		Info.Label = Label.IsEmpty() ? Info.Key + TEXT(": ") + Info.Package : (Label.StartsWith(Info.Key + TEXT(":")) ? Label : Info.Key + TEXT(": ") + Label);
		if (FTemplateInfo* Same = Out.FindByPredicate([&Info](const FTemplateInfo& T) { return T.Key == Info.Key; }))
		{
			*Same = Info;
		}
		else
		{
			Out.Add(Info);
		}
	}
	return Out;
}

FString TemplateFile(const FString& KeyOrPath)
{
	const FString Key = KeyOrPath.TrimStartAndEnd();
	const TArray<FTemplateInfo> List = Templates();
	for (const FTemplateInfo& Entry : List)
	{
		if (Key.Equals(Entry.Key, ESearchCase::IgnoreCase) || Key.Equals(Entry.Package, ESearchCase::IgnoreCase))
		{
			return FPaths::Combine(TemplateToolDir(), TEXT("templates"), Entry.Package + TEXT(".template.json"));
		}
	}
	if (Key.IsEmpty())
	{
		return FPaths::Combine(TemplateToolDir(), TEXT("templates"), List[0].Package + TEXT(".template.json"));
	}
	return FPaths::ConvertRelativePathToFull(Key);
}

FBuildReport MakeEditableAnimBlueprint(const FString& TemplatePath, const FString& SkeletonPath, const FString& PackagePath, bool bReplaceExisting,
	UAnimBlueprint** OutBlueprint)
{
	FBuildReport Report;
	Report.Template = TemplatePath;
	if (OutBlueprint)
	{
		*OutBlueprint = nullptr;
	}
	// 1. the template
	FString Text;
	TSharedPtr<FJsonObject> Template;
	if (!FFileHelper::LoadFileToString(Text, *TemplatePath))
	{
		Report.Errors.Add(TEXT("no template ") + TemplatePath);
		return Report;
	}
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Template) || !Template.IsValid())
	{
		Report.Errors.Add(TEXT("the template does not read as JSON: ") + TemplatePath);
		return Report;
	}
	int32 Version = 0;
	Template->TryGetNumberField(TEXT("version"), Version);
	if (Version != 1)
	{
		Report.Errors.Add(FString::Printf(TEXT("the template is version %d; this editor reads version 1"), Version));
		return Report;
	}
	if (const TArray<TSharedPtr<FJsonValue>>* Notes = Arr(Template, TEXT("notes")))
	{
		for (const TSharedPtr<FJsonValue>& Note : *Notes)
		{
			Report.Notes.Add(TEXT("the template: ") + Note->AsString());
		}
	}
	// 2. its parent class and the skeleton
	const FString ParentPath = Str(Template, TEXT("parent"));
	UClass* Parent = LoadObject<UClass>(nullptr, *ParentPath);
	if (!Parent || !Parent->IsChildOf(UAnimInstance::StaticClass()))
	{
		Report.Errors.Add(TEXT("the template's parent class is not in this editor: ") + ParentPath);
		return Report;
	}
	USkeleton* Skeleton = LoadObject<USkeleton>(nullptr, *ObjectPathOf(SkeletonPath));
	if (!Skeleton)
	{
		Report.Errors.Add(TEXT("no skeleton ") + SkeletonPath);
		return Report;
	}
	// (the assets its class defaults name, loaded so they import: the lip maps)
	if (const TArray<TSharedPtr<FJsonValue>>* Refs = Arr(Template, TEXT("refs")))
	{
		for (const TSharedPtr<FJsonValue>& Ref : *Refs)
		{
			if (!LoadObject<UObject>(nullptr, *Ref->AsString(), nullptr, LOAD_NoWarn | LOAD_Quiet))
			{
				Report.Warnings.Add(TEXT("not in this project, so left empty in the class defaults: ") + Ref->AsString());
			}
		}
	}
	// 3. the package
	FString Package = PackagePath.TrimStartAndEnd();
	if (Package.Contains(TEXT(".")))
	{
		Package = FPackageName::ObjectPathToPackageName(Package);
	}
	FText Reason;
	if (!Package.StartsWith(TEXT("/Game/")) || !FPackageName::IsValidLongPackageName(Package, false, &Reason))
	{
		Report.Errors.Add(TEXT("not a package path under /Game/: ") + PackagePath + (Reason.IsEmpty() ? FString() : TEXT(" (") + Reason.ToString() + TEXT(")")));
		return Report;
	}
	const FString AssetName = FPackageName::GetLongPackageAssetName(Package);
	const FString ObjectPath = Package + TEXT(".") + AssetName;
	if (FPackageName::DoesPackageExist(Package) || FindObject<UObject>(nullptr, *ObjectPath))
	{
		if (!bReplaceExisting)
		{
			Report.Errors.Add(ObjectPath + TEXT(" is there already (Replace Existing deletes it first)"));
			return Report;
		}
		UObject* Existing = LoadObject<UObject>(nullptr, *ObjectPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
		if (Existing && !Existing->IsA<UAnimBlueprint>())
		{
			Report.Errors.Add(ObjectPath + TEXT(" is there already and is not an AnimBlueprint: it is left as it is"));
			return Report;
		}
		// (the editor's delete needs the editor's UI: an editor commandlet has none, and crashed in it)
		if (Existing && IsRunningCommandlet())
		{
			Report.Errors.Add(ObjectPath + TEXT(" is there already, and an editor commandlet cannot delete it: move it out of the project first"));
			return Report;
		}
		if (Existing && ObjectTools::ForceDeleteObjects({Existing}, /*ShowConfirmation*/ false) == 0)
		{
			Report.Errors.Add(ObjectPath + TEXT(" is there already and could not be deleted"));
			return Report;
		}
		CollectGarbage(GARBAGE_COLLECTION_KEEPFLAGS);
		if (FindObject<UObject>(nullptr, *ObjectPath))
		{
			Report.Errors.Add(ObjectPath + TEXT(" is still loaded after it was deleted: restart the editor and make it again"));
			return Report;
		}
		Report.Notes.Add(TEXT("the AnimBlueprint that was there was deleted first"));
	}
	UPackage* Outer = CreatePackage(*Package);
	Outer->FullyLoad();
	UAnimBlueprint* Blueprint = Cast<UAnimBlueprint>(FKismetEditorUtilities::CreateBlueprint(Parent, Outer, FName(*AssetName), BPTYPE_Normal,
		UAnimBlueprint::StaticClass(), UBlueprintGeneratedClass::StaticClass(), FName(TEXT("RebirthAnimBlueprintTemplate"))));
	if (!Blueprint)
	{
		Report.Errors.Add(TEXT("the AnimBlueprint could not be made"));
		return Report;
	}
	// (as the AnimBlueprint factory: the skeleton on the blueprint and its classes)
	Blueprint->TargetSkeleton = Skeleton;
	if (UAnimBlueprintGeneratedClass* Class = Cast<UAnimBlueprintGeneratedClass>(Blueprint->GeneratedClass))
	{
		Class->TargetSkeleton = Skeleton;
	}
	if (UAnimBlueprintGeneratedClass* Class = Cast<UAnimBlueprintGeneratedClass>(Blueprint->SkeletonGeneratedClass))
	{
		Class->TargetSkeleton = Skeleton;
	}
	FAssetRegistryModule::AssetCreated(Blueprint);
	// 4. its graphs
	FBuilder Builder(Blueprint, Parent, Report);
	Builder.Build(Template);
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
	// 5. compile, the class defaults, compile again
	{
		FCompilerResultsLog Log;
		FKismetEditorUtilities::CompileBlueprint(Blueprint, EBlueprintCompileOptions::None, &Log);
	}
	Builder.ApplyDefaults(Template);
	FCompilerResultsLog Log;
	FKismetEditorUtilities::CompileBlueprint(Blueprint, EBlueprintCompileOptions::None, &Log);
	for (const TSharedRef<FTokenizedMessage>& Message : Log.Messages)
	{
		if (Message->GetSeverity() == EMessageSeverity::Error || Message->GetSeverity() == EMessageSeverity::CriticalError ||
			Message->GetSeverity() == EMessageSeverity::Warning || Message->GetSeverity() == EMessageSeverity::PerformanceWarning)
		{
			Report.Compiler.Add(FString(Message->GetSeverity() == EMessageSeverity::Warning || Message->GetSeverity() == EMessageSeverity::PerformanceWarning
				? TEXT("warning: ") : TEXT("ERROR: ")) + Message->ToText().ToString());
		}
	}
	Report.Compile = Blueprint->Status == BS_UpToDate ? TEXT("up to date") : Blueprint->Status == BS_UpToDateWithWarnings ? TEXT("up to date, with warnings")
		: Blueprint->Status == BS_Error ? TEXT("ERROR") : TEXT("not compiled");
	Report.Asset = Blueprint->GetPathName();
	Report.AnimClass = Blueprint->GeneratedClass ? Blueprint->GeneratedClass->GetPathName() : FString();
	if (Skeleton->GetOutermost()->IsDirty())
	{
		Report.Notes.Add(TEXT("the skeleton gained slots the AnimBlueprint plays (Slot nodes): save it (it was not saved here)"));
	}
	// 6. saved
	Outer->MarkPackageDirty();
	FString Problem;
	if (!SavePackageAsset(Outer, Blueprint, Problem))
	{
		Report.Errors.Add(Report.Asset + TEXT(" ") + Problem);
	}
	Report.bOk = Report.Errors.Num() == 0 && Blueprint->Status != BS_Error;
	if (OutBlueprint)
	{
		*OutBlueprint = Blueprint;
	}
	UE_LOG(LogRebirthAnimTemplate, Log, TEXT("%s"), *Report.ToText());
	return Report;
}

FString CookToContainer(const TArray<FString>& PackageNames, const FString& ContainerName, const FString& OutDir)
{
	TSharedRef<FJsonObject> Out = MakeShared<FJsonObject>();
	TArray<FString> Errors, Cooked;
	auto Finish = [&]()
	{
		Out->SetBoolField(TEXT("ok"), Errors.Num() == 0);
		Out->SetArrayField(TEXT("errors"), JsonList(Errors));
		Out->SetArrayField(TEXT("cooked"), JsonList(Cooked));
		return JsonText(Out);
	};
	const ITargetPlatform* Platform = GetTargetPlatformManagerRef().FindTargetPlatform(TEXT("WindowsNoEditor"));
	if (!Platform)
	{
		Errors.Add(TEXT("the WindowsNoEditor target platform is not available in this editor"));
		return Finish();
	}
	bool bNameOk = !ContainerName.IsEmpty();
	for (const TCHAR Ch : ContainerName)
	{
		bNameOk &= FChar::IsAlnum(Ch) || Ch == TEXT('_') || Ch == TEXT('-');
	}
	if (!bNameOk)
	{
		Errors.Add(TEXT("the container's name may only have letters, digits, _ and -: ") + ContainerName);
		return Finish();
	}
	const FString Dest = FPaths::ConvertRelativePathToFull(OutDir);
	const FString Work = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("RebirthSkelCompat"), TEXT("AnimTemplate"), ContainerName));
	const FString CookedRoot = FPaths::Combine(Work, TEXT("Cooked"));
	const FString CookedContent = FPaths::Combine(CookedRoot, FApp::GetProjectName(), TEXT("Content"));
	IFileManager::Get().DeleteDirectory(*CookedRoot, false, true);
	FString Response;
	for (const FString& Name : PackageNames)
	{
		FString PackageName = Name.TrimStartAndEnd();
		if (PackageName.Contains(TEXT(".")))
		{
			PackageName = FPackageName::ObjectPathToPackageName(PackageName);
		}
		if (!PackageName.StartsWith(TEXT("/Game/")))
		{
			Errors.Add(PackageName + TEXT(" is not under /Game/"));
			continue;
		}
		UPackage* Package = LoadPackage(nullptr, *PackageName, LOAD_None);
		if (!Package)
		{
			Errors.Add(PackageName + TEXT(" does not load"));
			continue;
		}
		const FString Rel = PackageName.RightChop(6);
		const FString Base = FPaths::Combine(CookedContent, Rel);
		FString Problem;
		if (!CookOne(Package, Platform, Base + TEXT(".uasset"), Problem))
		{
			UPackage::WaitForAsyncFileWrites();
			Errors.Add(PackageName + TEXT(": ") + Problem);
			continue;
		}
		UPackage::WaitForAsyncFileWrites();
		if (!FPaths::FileExists(Base + TEXT(".uexp")) && !SplitCooked(Base + TEXT(".uasset"), Problem))
		{
			Errors.Add(PackageName + TEXT(": ") + Problem);
			continue;
		}
		Response += FString::Printf(TEXT("\"%s.uasset\" \"../../../%s/Content/%s.uasset\"\r\n"), *Base, FApp::GetProjectName(), *Rel);
		for (const TCHAR* Extension : {TEXT(".ubulk"), TEXT(".uptnl"), TEXT(".m.ubulk")})
		{
			if (FPaths::FileExists(Base + Extension))
			{
				Response += FString::Printf(TEXT("\"%s%s\" \"../../../%s/Content/%s%s\"\r\n"), *Base, Extension, FApp::GetProjectName(), *Rel, Extension);
			}
		}
		Cooked.Add(PackageName);
	}
	if (Errors.Num() > 0 || Cooked.Num() == 0)
	{
		if (Cooked.Num() == 0 && Errors.Num() == 0)
		{
			Errors.Add(TEXT("nothing to cook"));
		}
		return Finish();
	}
	// the game's package format: the engine's IoStore commandlet
	const FString ContainerDir = FPaths::Combine(Work, TEXT("Container"));
	const FString GlobalDir = FPaths::Combine(Work, TEXT("Global"));
	const FString Utoc = FPaths::Combine(ContainerDir, ContainerName + TEXT(".utoc"));
	const FString Ucas = FPaths::Combine(ContainerDir, ContainerName + TEXT(".ucas"));
	const FString IoStoreLog = FPaths::Combine(Work, TEXT("iostore.log"));   // (not "LogPath": the engine's log category of that name)
	const FString ResponseFile = FPaths::Combine(Work, TEXT("Packages.txt"));
	const FString CommandsFile = FPaths::Combine(Work, TEXT("IoStoreCommands.txt"));
	IFileManager::Get().MakeDirectory(*ContainerDir, true);
	IFileManager::Get().MakeDirectory(*GlobalDir, true);
	IFileManager::Get().Delete(*Utoc, false, true, true);
	IFileManager::Get().Delete(*Ucas, false, true, true);
	IFileManager::Get().Delete(*IoStoreLog, false, true, true);
	if (!FFileHelper::SaveStringToFile(Response, *ResponseFile, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM) ||
		!FFileHelper::SaveStringToFile(FString::Printf(TEXT("-Output=\"%s\" -ContainerName=%s -ResponseFile=\"%s\"\r\n"), *Utoc, *ContainerName, *ResponseFile),
			*CommandsFile, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
	{
		Errors.Add(TEXT("cannot write ") + ResponseFile);
		return Finish();
	}
	const FString Running = FPlatformProcess::ExecutablePath();
	const FString CmdExe = FPaths::Combine(FPaths::GetPath(Running), TEXT("UE4Editor-Cmd.exe"));
	const FString Executable = FPaths::FileExists(CmdExe) ? CmdExe : Running;
	const FString Project = FPaths::ConvertRelativePathToFull(FPaths::GetProjectFilePath());
	const FString Arguments = FString::Printf(TEXT("\"%s\" -run=IoStore -CreateGlobalContainer=\"%s\" -CookedDirectory=\"%s\" -Commands=\"%s\" -TargetPlatform=WindowsNoEditor -ddc=InstalledDerivedDataBackendGraph -unattended -NoLogTimes -UTF8Output -abslog=\"%s\""),
		*Project, *FPaths::Combine(GlobalDir, TEXT("global.utoc")), *CookedRoot, *CommandsFile, *IoStoreLog);
	uint32 ProcessId = 0;
	FProcHandle Process = FPlatformProcess::CreateProc(*Executable, *Arguments, false, true, true, &ProcessId, 0, nullptr, nullptr, nullptr);
	if (!Process.IsValid())
	{
		Errors.Add(TEXT("the IoStore commandlet did not start (") + Executable + TEXT(")"));
		return Finish();
	}
	const double Started = FPlatformTime::Seconds();
	while (FPlatformProcess::IsProcRunning(Process))
	{
		if (FPlatformTime::Seconds() - Started > 1200.0)
		{
			FPlatformProcess::TerminateProc(Process, true);
			Errors.Add(TEXT("the IoStore commandlet took over 20 minutes: stopped"));
			break;
		}
		FPlatformProcess::Sleep(0.25f);
	}
	FPlatformProcess::WaitForProc(Process);
	int32 ExitCode = -1;
	FPlatformProcess::GetProcReturnCode(Process, &ExitCode);
	FPlatformProcess::CloseProc(Process);
	FString LogText;
	FFileHelper::LoadFileToString(LogText, *IoStoreLog);
	const int32 Result = CommandletResult(LogText);
	Out->SetNumberField(TEXT("iostore_exit_code"), ExitCode);
	Out->SetStringField(TEXT("iostore_log"), IoStoreLog);
	if (Errors.Num() == 0 && (Result != 0 || !FPaths::FileExists(Utoc) || !FPaths::FileExists(Ucas)))
	{
		Errors.Add(FString::Printf(TEXT("the IoStore commandlet failed (exit code %d, result %d%s): %s"), ExitCode, Result,
			FPaths::FileExists(Utoc) ? TEXT("") : TEXT(", no container"), *LastErrorLines(LogText, 6)));
	}
	if (Errors.Num() > 0)
	{
		return Finish();
	}
	// the container where it is wanted, with the stub .pak the game wants beside a .utoc
	IFileManager::Get().MakeDirectory(*Dest, true);
	const FString Stub = FPaths::Combine(TemplateToolDir(), TEXT("stub.pak"));
	const bool bCopied = IFileManager::Get().Copy(*FPaths::Combine(Dest, ContainerName + TEXT(".utoc")), *Utoc) == COPY_OK &&
		IFileManager::Get().Copy(*FPaths::Combine(Dest, ContainerName + TEXT(".ucas")), *Ucas) == COPY_OK &&
		IFileManager::Get().Copy(*FPaths::Combine(Dest, ContainerName + TEXT(".pak")), *Stub) == COPY_OK;
	if (!bCopied)
	{
		Errors.Add(TEXT("the container could not be written to ") + Dest + (FPaths::FileExists(Stub) ? FString() : TEXT(" (no ") + Stub + TEXT(")")));
	}
	Out->SetStringField(TEXT("container"), FPaths::Combine(Dest, ContainerName + TEXT(".utoc")));
	Out->SetStringField(TEXT("cooked_dir"), CookedContent);
	return Finish();
}
} // namespace RebirthAnimTemplate

// ------------------------------------------------------------------------------------------------
FString UEndAnimBlueprintTemplateLibrary::MakeEditableAnimBlueprint(const FString& Template, const FString& Skeleton, const FString& PackagePath, bool bReplaceExisting)
{
	return RebirthAnimTemplate::MakeEditableAnimBlueprint(RebirthAnimTemplate::TemplateFile(Template), Skeleton, PackagePath, bReplaceExisting).ToJson();
}

FString UEndAnimBlueprintTemplateLibrary::CookAnimBlueprintContainer(const FString& PackagePath, const FString& ContainerName, const FString& OutDir)
{
	return RebirthAnimTemplate::CookToContainer({PackagePath}, ContainerName, OutDir);
}

#undef LOCTEXT_NAMESPACE
