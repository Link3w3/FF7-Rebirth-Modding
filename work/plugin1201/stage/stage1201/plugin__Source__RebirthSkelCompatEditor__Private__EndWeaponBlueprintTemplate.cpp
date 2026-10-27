// RebirthSkelCompat weapon Blueprints (editor 1.20, 1.20.1): see EndWeaponBlueprintTemplate.h.
#include "EndWeaponBlueprintTemplate.h"

#include "AssetRegistryModule.h"
#include "Components/ActorComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkinnedMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Blueprint.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "HAL/FileManager.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/CompilerResultsLog.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FeedbackContext.h"
#include "Misc/FileHelper.h"
#include "Misc/OutputDeviceNull.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "ObjectTools.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UObject/Package.h"
#include "UObject/UObjectHash.h"
#include "UObject/UnrealType.h"

DEFINE_LOG_CATEGORY_STATIC(LogRebirthWeaponTemplate, Log, All);

// Named, not anonymous, and inside RebirthWeaponTemplate: the module may be compiled as one unity file with the other
// sources, whose helpers of the same names are brought in by using-directives of their own.
namespace RebirthWeaponTemplate
{
namespace Util
{
using FJsonObj = TSharedPtr<FJsonObject>;

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

FString ObjectPathOf(const FString& Path)
{
	FString Out = Path.TrimStartAndEnd();
	if (Out.StartsWith(TEXT("/")) && !Out.Contains(TEXT(".")))
	{
		Out += TEXT(".") + FPackageName::GetShortName(Out);
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

FString Join(const TArray<FString>& Lines, const TCHAR* Prefix)
{
	FString Out;
	for (const FString& Line : Lines)
	{
		Out += Prefix + Line + TEXT("\n");
	}
	return Out;
}

// The templates file, read once and again when it changes on disk.
struct FTemplatesCache
{
	FDateTime Stamp;
	TSharedPtr<FJsonObject> Root;
	TArray<TSharedPtr<FJsonObject>> Entries;
};

FTemplatesCache& Cache()
{
	static FTemplatesCache Instance;
	return Instance;
}

const TArray<TSharedPtr<FJsonObject>>& TemplateEntries()
{
	FTemplatesCache& Templates = Cache();
	const FString File = RebirthWeaponTemplate::TemplatesFile();
	const FDateTime Stamp = IFileManager::Get().GetTimeStamp(*File);
	if (Stamp == FDateTime::MinValue())
	{
		Templates.Root.Reset();
		Templates.Entries.Reset();
		Templates.Stamp = Stamp;
		return Templates.Entries;
	}
	if (Templates.Root.IsValid() && Stamp == Templates.Stamp)
	{
		return Templates.Entries;
	}
	Templates.Stamp = Stamp;
	Templates.Root.Reset();
	Templates.Entries.Reset();
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *File))
	{
		return Templates.Entries;
	}
	TSharedPtr<FJsonObject> Root;
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	int32 Version = 0;
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid() || !Root->TryGetNumberField(TEXT("version"), Version) || Version != 1)
	{
		UE_LOG(LogRebirthWeaponTemplate, Warning, TEXT("%s does not read as weapon templates of version 1: no templates"), *File);
		return Templates.Entries;
	}
	Templates.Root = Root;
	if (const TArray<TSharedPtr<FJsonValue>>* List = Arr(Root, TEXT("templates")))
	{
		for (const TSharedPtr<FJsonValue>& Value : *List)
		{
			const TSharedPtr<FJsonObject> Entry = Value.IsValid() ? Value->AsObject() : nullptr;
			if (Entry.IsValid() && !Str(Entry, TEXT("key")).IsEmpty())
			{
				Templates.Entries.Add(Entry);
			}
		}
	}
	return Templates.Entries;
}

TSharedPtr<FJsonObject> TemplateEntry(const FString& KeyOrLabel)
{
	const FString Want = KeyOrLabel.TrimStartAndEnd();
	for (const TSharedPtr<FJsonObject>& Entry : TemplateEntries())
	{
		if (Str(Entry, TEXT("key")).Equals(Want, ESearchCase::IgnoreCase) || Str(Entry, TEXT("label")).Equals(Want, ESearchCase::IgnoreCase))
		{
			return Entry;
		}
	}
	return nullptr;
}

// ImportText into a property of an object; false with the reason when the text did not read (a warning with a value
// read is kept, as the AnimBlueprint templates do).
bool ImportInto(FProperty* Property, UObject* Owner, const FString& Text, FString& OutProblem)
{
	FStringOutputDevice Errors;
	const TCHAR* End = Property->ImportText(*Text, Property->ContainerPtrToValuePtr<void>(Owner), PPF_None, Owner, &Errors);
	if (!End || !Errors.IsEmpty())
	{
		OutProblem = Errors.IsEmpty() ? FString(TEXT("the text does not read")) : FString(Errors).TrimStartAndEnd().Left(300);
		return End != nullptr;
	}
	return true;
}

// The object paths a value's text names ("/Game/..." in quotes): those not in this project come out empty.
TArray<FString> PathsIn(const FString& Text)
{
	TArray<FString> Out;
	int32 At = 0;
	while (true)
	{
		const int32 Open = Text.Find(TEXT("\"/"), ESearchCase::CaseSensitive, ESearchDir::FromStart, At);
		if (Open == INDEX_NONE)
		{
			break;
		}
		const int32 Close = Text.Find(TEXT("\""), ESearchCase::CaseSensitive, ESearchDir::FromStart, Open + 1);
		if (Close == INDEX_NONE)
		{
			break;
		}
		Out.Add(Text.Mid(Open + 1, Close - Open - 1));
		At = Close + 1;
	}
	return Out;
}

// Every {property, text} of a list put on Object; counts what went on, says what did not.
int32 ApplyValues(UObject* Object, const TArray<TSharedPtr<FJsonValue>>* Values, const FString& Where, RebirthWeaponTemplate::FBuildReport& Report,
	const TSet<FName>& Skip = TSet<FName>())
{
	int32 Count = 0;
	if (!Object || !Values)
	{
		return 0;
	}
	for (const TSharedPtr<FJsonValue>& Value : *Values)
	{
		const TSharedPtr<FJsonObject> Entry = Value.IsValid() ? Value->AsObject() : nullptr;
		const FString Name = Str(Entry, TEXT("property"));
		const FString Text = Str(Entry, TEXT("text"));
		if (Name.IsEmpty() || Skip.Contains(FName(*Name)))
		{
			continue;
		}
		FProperty* Property = FindFProperty<FProperty>(Object->GetClass(), FName(*Name));
		if (!Property)
		{
			Report.Warnings.Add(FString::Printf(TEXT("%s: this editor's %s has no %s (the game's value left out: %s)"), *Where, *Object->GetClass()->GetName(), *Name, *Text.Left(200)));
			continue;
		}
		FString Problem;
		if (!ImportInto(Property, Object, Text, Problem))
		{
			Report.Warnings.Add(FString::Printf(TEXT("%s.%s did not take the game's value %s (%s)"), *Where, *Name, *Text.Left(200), *Problem));
			continue;
		}
		// (an object the game has but this project does not: a hard reference to it comes out empty; a soft one, a path,
		// stays and the game finds it)
		TArray<FString> Missing;
		FString Now;
		Property->ExportTextItem(Now, Property->ContainerPtrToValuePtr<void>(Object), nullptr, Object, PPF_None);
		for (const FString& Path : PathsIn(Text))
		{
			if (Path.StartsWith(TEXT("/Game/")) && !Now.Contains(Path))
			{
				Missing.Add(Path);
			}
		}
		if (Missing.Num() > 0)
		{
			Report.Warnings.Add(FString::Printf(TEXT("%s.%s: not in this project, so left empty: %s (in game the template's blueprint has it)"), *Where, *Name, *FString::Join(Missing, TEXT(", "))));
		}
		else if (!Problem.IsEmpty())
		{
			Report.Notes.Add(FString::Printf(TEXT("%s.%s: %s"), *Where, *Name, *Problem));
		}
		++Count;
	}
	return Count;
}

bool SaveAsset(UPackage* Package, UObject* Asset, FString& OutProblem)
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

// A native component of the parent class's default object by name (SkeletalMeshComponent0).
USceneComponent* NativeComponent(UClass* Parent, const FString& Name)
{
	AActor* Defaults = Parent ? Cast<AActor>(Parent->GetDefaultObject()) : nullptr;
	if (!Defaults)
	{
		return nullptr;
	}
	TInlineComponentArray<UActorComponent*> Components;
	Defaults->GetComponents(Components);
	for (UActorComponent* Component : Components)
	{
		if (Component && Component->GetName() == Name)
		{
			return Cast<USceneComponent>(Component);
		}
	}
	return Cast<USceneComponent>(Defaults->GetDefaultSubobjectByName(FName(*Name)));
}
} // namespace Util

using namespace Util;

FString FBuildReport::ToJson() const
{
	TSharedRef<FJsonObject> Out = MakeShared<FJsonObject>();
	Out->SetBoolField(TEXT("ok"), bOk);
	Out->SetStringField(TEXT("template"), Template);
	Out->SetStringField(TEXT("asset"), Asset);
	Out->SetStringField(TEXT("weapon_class"), WeaponClass);
	Out->SetStringField(TEXT("compile"), Compile);
	Out->SetNumberField(TEXT("defaults"), Defaults);
	Out->SetNumberField(TEXT("settings"), Settings);
	Out->SetNumberField(TEXT("components"), Components);
	Out->SetArrayField(TEXT("errors"), JsonList(Errors));
	Out->SetArrayField(TEXT("warnings"), JsonList(Warnings));
	Out->SetArrayField(TEXT("notes"), JsonList(Notes));
	Out->SetArrayField(TEXT("compiler"), JsonList(Compiler));
	return JsonText(Out);
}

FString FBuildReport::ToText() const
{
	FString Out = bOk ? FString::Printf(TEXT("Made %s (compile: %s).\nIts class (a skin's Weapon): %s\n"), *Asset, *Compile, *WeaponClass)
					  : FString(TEXT("The weapon Blueprint was NOT made.\n"));
	Out += FString::Printf(TEXT("From %s: %d class default(s), %d mesh component setting(s), %d component(s) of its own.\n"), *Template, Defaults, Settings, Components);
	Out += Join(Errors, TEXT("ERROR: "));
	Out += Join(Compiler, TEXT("compiler: "));
	Out += Join(Warnings, TEXT("warning: "));
	Out += Join(Notes, TEXT("note: "));
	return Out;
}

FString ToolDir()
{
	return FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectDir(), TEXT("Tools"), TEXT("RebirthSkelCompat"), TEXT("weapon")));
}

FString TemplatesFile()
{
	return FPaths::Combine(ToolDir(), TEXT("templates.json"));
}

TArray<FTemplateInfo> Templates()
{
	TArray<FTemplateInfo> Out;
	for (const TSharedPtr<FJsonObject>& Entry : TemplateEntries())
	{
		FTemplateInfo Info;
		Info.Key = Str(Entry, TEXT("key"));
		Info.Package = Str(Entry, TEXT("package"));
		Info.Label = Str(Entry, TEXT("label"));
		Info.Character = Str(Entry, TEXT("character"));
		Info.Parent = Str(Entry, TEXT("parent"));
		Info.Mesh = Str(Entry, TEXT("mesh"));
		if (Info.Label.IsEmpty())
		{
			Info.Label = Info.Key;
		}
		Out.Add(Info);
	}
	return Out;
}

bool FindTemplate(const FString& KeyOrLabel, FTemplateInfo& Out)
{
	const FString Want = KeyOrLabel.TrimStartAndEnd();
	for (const FTemplateInfo& Info : Templates())
	{
		if (Info.Key.Equals(Want, ESearchCase::IgnoreCase) || Info.Label.Equals(Want, ESearchCase::IgnoreCase))
		{
			Out = Info;
			return true;
		}
	}
	return false;
}

FString DefaultFolder(const FString& MeshPath)
{
	const FString Root = TEXT("/Game/BluePrint/Character/Weapon");
	const FString Path = MeshPath.TrimStartAndEnd();
	if (Path.IsEmpty())
	{
		return Root;
	}
	const FString Package = Path.Contains(TEXT(".")) ? FPackageName::ObjectPathToPackageName(Path) : Path;
	TArray<FString> Parts;
	Package.ParseIntoArray(Parts, TEXT("/"), true);
	// /Game/Character/Weapon/<folder>/Model/<mesh>: the weapon's folder
	const int32 Weapon = Parts.IndexOfByPredicate([](const FString& Part) { return Part.Equals(TEXT("Weapon"), ESearchCase::IgnoreCase); });
	if (Weapon != INDEX_NONE && Weapon + 2 < Parts.Num())
	{
		return Root + TEXT("/") + Parts[Weapon + 1];
	}
	if (Parts.Num() >= 3 && Parts[Parts.Num() - 2].Equals(TEXT("Model"), ESearchCase::IgnoreCase))
	{
		return Root + TEXT("/") + Parts[Parts.Num() - 3];
	}
	return Root + TEXT("/") + FPackageName::GetShortName(Package);
}

FBuildReport MakeWeaponBlueprint(const FString& TemplateKey, const FString& MeshPath, const FString& PackagePath, bool bReplaceExisting, UBlueprint** OutBlueprint)
{
	FBuildReport Report;
	Report.Template = TemplateKey;
	// 1. the template
	const TSharedPtr<FJsonObject> Template = TemplateEntry(TemplateKey);
	if (!Template.IsValid())
	{
		Report.Errors.Add(FPaths::FileExists(TemplatesFile()) ? TEXT("no template ") + TemplateKey + TEXT(" in ") + TemplatesFile()
															  : TEXT("the weapon templates are not installed: ") + TemplatesFile());
		return Report;
	}
	Report.Template = Str(Template, TEXT("label")).IsEmpty() ? Str(Template, TEXT("key")) : Str(Template, TEXT("label"));
	if (const TArray<TSharedPtr<FJsonValue>>* Notes = Arr(Template, TEXT("notes")))
	{
		for (const TSharedPtr<FJsonValue>& Note : *Notes)
		{
			Report.Notes.Add(TEXT("the template: ") + Note->AsString());
		}
	}
	// 2. its parent class (the End project's native class) and the model
	const FString ParentPath = Str(Template, TEXT("parent"));
	UClass* Parent = ParentPath.IsEmpty() ? nullptr : LoadObject<UClass>(nullptr, *ParentPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (!Parent || !Parent->IsChildOf(AActor::StaticClass()) || !FKismetEditorUtilities::CanCreateBlueprintOfClass(Parent))
	{
		Report.Errors.Add(TEXT("the template's parent class is not in this editor (or is not a Blueprintable actor): ") + ParentPath);
		return Report;
	}
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *ObjectPathOf(MeshPath));
	if (!Mesh)
	{
		Report.Errors.Add(TEXT("no skeletal mesh ") + MeshPath);
		return Report;
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
		if (Existing && !Existing->IsA<UBlueprint>())
		{
			Report.Errors.Add(ObjectPath + TEXT(" is there already and is not a Blueprint: it is left as it is"));
			return Report;
		}
		// (the editor's delete needs the editor's UI: an editor commandlet has none)
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
		Report.Notes.Add(TEXT("the Blueprint that was there was deleted first"));
	}
	UPackage* Outer = CreatePackage(*Package);
	Outer->FullyLoad();
	UBlueprint* Blueprint = FKismetEditorUtilities::CreateBlueprint(Parent, Outer, FName(*AssetName), BPTYPE_Normal, UBlueprint::StaticClass(),
		UBlueprintGeneratedClass::StaticClass(), FName(TEXT("RebirthWeaponBlueprintTemplate")));
	if (!Blueprint)
	{
		Report.Errors.Add(TEXT("the Blueprint could not be made"));
		return Report;
	}
	FAssetRegistryModule::AssetCreated(Blueprint);
	// 4. its own components (a gun's cartridges, a light ...): construction script nodes, their templates the game's values
	USimpleConstructionScript* Scs = Blueprint->SimpleConstructionScript;
	if (const TArray<TSharedPtr<FJsonValue>>* Components = Arr(Template, TEXT("components")))
	{
		for (const TSharedPtr<FJsonValue>& Value : *Components)
		{
			const TSharedPtr<FJsonObject> Entry = Value.IsValid() ? Value->AsObject() : nullptr;
			const FString Name = Str(Entry, TEXT("name"));
			const FString ClassPath = Str(Entry, TEXT("cls"));
			UClass* ComponentClass = ClassPath.IsEmpty() ? nullptr : LoadObject<UClass>(nullptr, *ClassPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
			if (!Scs || Name.IsEmpty() || !ComponentClass || !ComponentClass->IsChildOf(UActorComponent::StaticClass()))
			{
				Report.Warnings.Add(FString::Printf(TEXT("component %s left out: its class %s is not in this editor"), *Name, *ClassPath));
				continue;
			}
			USCS_Node* Node = Scs->CreateNode(ComponentClass, FName(*Name));
			if (!Node)
			{
				Report.Warnings.Add(TEXT("component ") + Name + TEXT(" could not be made"));
				continue;
			}
			const FString ParentName = Str(Entry, TEXT("parent"));
			bool bParentNative = false;
			Entry->TryGetBoolField(TEXT("parent_native"), bParentNative);
			bool bPlaced = false;
			if (!ParentName.IsEmpty() && Node->ComponentTemplate && Node->ComponentTemplate->IsA<USceneComponent>())
			{
				if (bParentNative)
				{
					if (USceneComponent* Native = NativeComponent(Parent, ParentName))
					{
						Node->SetParent(Native);
						Scs->AddNode(Node);
						bPlaced = true;
					}
				}
				else if (USCS_Node* ParentNode = Scs->FindSCSNode(FName(*ParentName)))
				{
					ParentNode->AddChildNode(Node);
					bPlaced = true;
				}
				if (!bPlaced)
				{
					Report.Warnings.Add(FString::Printf(TEXT("component %s: its parent %s is not there: put on the root instead"), *Name, *ParentName));
				}
			}
			if (!bPlaced)
			{
				Scs->AddNode(Node);
			}
			const FString Socket = Str(Entry, TEXT("socket"));
			if (!Socket.IsEmpty())
			{
				Node->AttachToName = FName(*Socket);
			}
			ApplyValues(Node->ComponentTemplate, Arr(Entry, TEXT("properties")), Name, Report);
			++Report.Components;
		}
	}
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
	{
		FCompilerResultsLog Log;
		FKismetEditorUtilities::CompileBlueprint(Blueprint, EBlueprintCompileOptions::None, &Log);
	}
	// 5. the class defaults and the native components' settings (the model on the mesh component), then compile again
	UObject* Defaults = Blueprint->GeneratedClass ? Blueprint->GeneratedClass->GetDefaultObject() : nullptr;
	if (!Defaults)
	{
		Report.Errors.Add(TEXT("the Blueprint has no class default object after its first compile"));
		return Report;
	}
	Report.Defaults = ApplyValues(Defaults, Arr(Template, TEXT("defaults")), TEXT("class defaults"), Report);
	bool bMeshSet = false;
	TArray<FString> SubobjectNames;
	if (const TArray<TSharedPtr<FJsonValue>>* Subobjects = Arr(Template, TEXT("subobjects")))
	{
		for (const TSharedPtr<FJsonValue>& Value : *Subobjects)
		{
			const TSharedPtr<FJsonObject> Entry = Value.IsValid() ? Value->AsObject() : nullptr;
			SubobjectNames.Add(Str(Entry, TEXT("name")));
		}
	}
	if (!SubobjectNames.Contains(TEXT("SkeletalMeshComponent0")))
	{
		SubobjectNames.Insert(TEXT("SkeletalMeshComponent0"), 0);
	}
	for (const FString& Name : SubobjectNames)
	{
		UObject* Subobject = Defaults->GetDefaultSubobjectByName(FName(*Name));
		const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
		if (const TArray<TSharedPtr<FJsonValue>>* Subobjects = Arr(Template, TEXT("subobjects")))
		{
			for (const TSharedPtr<FJsonValue>& Value : *Subobjects)
			{
				const TSharedPtr<FJsonObject> Entry = Value.IsValid() ? Value->AsObject() : nullptr;
				if (Str(Entry, TEXT("name")) == Name)
				{
					Values = Arr(Entry, TEXT("properties"));
				}
			}
		}
		if (!Subobject)
		{
			if (Values && Values->Num() > 0)
			{
				Report.Warnings.Add(TEXT("this editor's ") + Parent->GetName() + TEXT(" has no component ") + Name + TEXT(": its settings are left out"));
			}
			continue;
		}
		Subobject->Modify();
		Report.Settings += ApplyValues(Subobject, Values, Name, Report, {FName(TEXT("SkeletalMesh"))});
		if (USkinnedMeshComponent* MeshComponent = Cast<USkinnedMeshComponent>(Subobject); MeshComponent && !bMeshSet)
		{
			// (the template object's property, as the Blueprint editor's details panel sets it)
			if (FObjectProperty* MeshProperty = FindFProperty<FObjectProperty>(MeshComponent->GetClass(), TEXT("SkeletalMesh")))
			{
				MeshProperty->SetObjectPropertyValue_InContainer(MeshComponent, Mesh);
				bMeshSet = true;
			}
		}
	}
	if (!bMeshSet)
	{
		Report.Errors.Add(TEXT("the Blueprint has no skeletal mesh component (SkeletalMeshComponent0) to hold the model"));
	}
	Defaults->MarkPackageDirty();
	FBlueprintEditorUtils::MarkBlueprintAsModified(Blueprint);
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
	Report.WeaponClass = Blueprint->GeneratedClass ? Blueprint->GeneratedClass->GetPathName() : FString();
	// (the model held after the compile: the compile keeps the class default object's values)
	if (UObject* After = Blueprint->GeneratedClass ? Blueprint->GeneratedClass->GetDefaultObject() : nullptr)
	{
		USkinnedMeshComponent* Held = Cast<USkinnedMeshComponent>(After->GetDefaultSubobjectByName(TEXT("SkeletalMeshComponent0")));
		if (!Held || Held->SkeletalMesh != Mesh)
		{
			Report.Errors.Add(TEXT("the model is not on its mesh component after the compile"));
		}
	}
	Report.Notes.Add(TEXT("its model: ") + Mesh->GetPathName() + TEXT(" (the game's ") + Str(Template, TEXT("key")) + TEXT(" holds ") + Str(Template, TEXT("mesh")) + TEXT(")"));
	TArray<FString> Chain;
	if (const TArray<TSharedPtr<FJsonValue>>* Links = Arr(Template, TEXT("chain")))
	{
		for (const TSharedPtr<FJsonValue>& Link : *Links)
		{
			Chain.Add(FPackageName::GetShortName(Link->AsString()));
		}
	}
	Report.Notes.Add(TEXT("its parent: ") + Parent->GetPathName() + TEXT(" (the game's blueprints it is made of, flattened into it: ") + FString::Join(Chain, TEXT(", ")) + TEXT(")"));
	// 6. saved
	Outer->MarkPackageDirty();
	FString Problem;
	if (!SaveAsset(Outer, Blueprint, Problem))
	{
		Report.Errors.Add(Report.Asset + TEXT(" ") + Problem);
	}
	Report.bOk = Report.Errors.Num() == 0 && Blueprint->Status != BS_Error;
	if (OutBlueprint)
	{
		*OutBlueprint = Blueprint;
	}
	UE_LOG(LogRebirthWeaponTemplate, Log, TEXT("%s"), *Report.ToText());
	return Report;
}

bool WeaponPackages(const FString& WeaponClassPath, TFunctionRef<bool(const FString&)> IsGamePackage, TArray<FString>& OutPackages,
	TArray<FString>& OutNotes, FString& OutProblem)
{
	const FString ClassPath = WeaponClassPath.TrimStartAndEnd();
	const FString Package = FPackageName::ObjectPathToPackageName(ClassPath);
	if (!Package.StartsWith(TEXT("/Game/")) || IsGamePackage(Package))
	{
		OutProblem = ClassPath + TEXT(" is not a Blueprint of this project");
		return false;
	}
	UClass* Class = LoadObject<UClass>(nullptr, *ClassPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (!Class || !Cast<UBlueprint>(Class->ClassGeneratedBy))
	{
		OutProblem = ClassPath + TEXT(" does not load as a Blueprint's class (a Blueprint's class path ends in _C)");
		return false;
	}
	if (!Class->IsChildOf(AActor::StaticClass()))
	{
		OutProblem = ClassPath + TEXT(" is not an actor's class");
		return false;
	}
	IAssetRegistry& Registry = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry")).Get();
	// (editor 1.20.1) a material's package (a material instance keeps its parent's textures, the renderer's default ones
	// too, as references of its own) and a cooked package (one of this project that was cooked: it cannot be cooked again)
	auto IsMaterial = [&Registry](const FString& Name)
	{
		TArray<FAssetData> Assets;
		Registry.GetAssetsByPackageName(FName(*Name), Assets, true);
		return Assets.ContainsByPredicate([](const FAssetData& Asset)
		{
			const UClass* AssetClass = Asset.GetClass();
			return AssetClass && AssetClass->IsChildOf(UMaterialInterface::StaticClass());
		});
	};
	auto IsCooked = [](const FString& Name)
	{
		UPackage* Loaded = FindPackage(nullptr, *Name);
		if (!Loaded)
		{
			Loaded = LoadPackage(nullptr, *Name, LOAD_NoWarn | LOAD_Quiet);
		}
		return Loaded && Loaded->HasAnyPackageFlags(PKG_Cooked);
	};
	TArray<FString> LeftOut;
	TArray<FString> Queue{Package};
	TSet<FString> Seen{Package};
	while (Queue.Num() > 0)
	{
		const FString Next = Queue[0];
		Queue.RemoveAt(0);
		OutPackages.Add(Next);
		const bool bMaterial = IsMaterial(Next);
		TArray<FName> Dependencies;
		Registry.GetDependencies(FName(*Next), Dependencies, UE::AssetRegistry::EDependencyCategory::Package,
			UE::AssetRegistry::FDependencyQuery(UE::AssetRegistry::EDependencyQuery::Hard | UE::AssetRegistry::EDependencyQuery::Game));
		for (const FName& Dependency : Dependencies)
		{
			const FString Name = Dependency.ToString();
			if (Seen.Contains(Name))
			{
				continue;
			}
			Seen.Add(Name);
			if (!Name.StartsWith(TEXT("/Game/")))
			{
				continue;   // (the engine's and the game's native classes)
			}
			if (IsGamePackage(Name))
			{
				OutNotes.Add(TEXT("the weapon uses the game's ") + Name + TEXT(" (the game's own)"));
				continue;
			}
			// (editor 1.20.1) a cooked asset of this project the game does not have that a material uses (the renderer's
			// default textures its material instances keep of their parent, e.g. /Game/Renderer/Texture/FFFFFFFF_sRGB)
			// stays out as it does for the skin's model: in game the material takes them from its parent, the game's own
			if (bMaterial && IsCooked(Name))
			{
				LeftOut.Add(Name);
				continue;
			}
			Queue.Add(Name);
		}
	}
	if (LeftOut.Num() > 0)
	{
		const int32 Shown = FMath::Min(LeftOut.Num(), 4);
		OutNotes.Add(FString::Printf(TEXT("%d cooked asset(s) of this project the game does not have that the weapon's materials use stay out, as for the model (they cannot be cooked again; in game a material instance takes them from its parent): %s%s"),
			LeftOut.Num(), *FString::Join(TArrayView<const FString>(LeftOut.GetData(), Shown), TEXT(", ")), LeftOut.Num() > Shown ? TEXT(", ...") : TEXT("")));
	}
	return true;
}
} // namespace RebirthWeaponTemplate

// ------------------------------------------------------------------------------------------------
FString UEndWeaponBlueprintTemplateLibrary::MakeWeaponBlueprint(const FString& Template, const FString& Mesh, const FString& PackagePath, bool bReplaceExisting)
{
	return RebirthWeaponTemplate::MakeWeaponBlueprint(Template, Mesh, PackagePath, bReplaceExisting).ToJson();
}

FString UEndWeaponBlueprintTemplateLibrary::WeaponTemplates()
{
	TArray<TSharedPtr<FJsonValue>> List;
	for (const RebirthWeaponTemplate::FTemplateInfo& Info : RebirthWeaponTemplate::Templates())
	{
		TSharedRef<FJsonObject> Entry = MakeShared<FJsonObject>();
		Entry->SetStringField(TEXT("key"), Info.Key);
		Entry->SetStringField(TEXT("label"), Info.Label);
		Entry->SetStringField(TEXT("character"), Info.Character);
		Entry->SetStringField(TEXT("parent"), Info.Parent);
		Entry->SetStringField(TEXT("package"), Info.Package);
		Entry->SetStringField(TEXT("mesh"), Info.Mesh);
		List.Add(MakeShared<FJsonValueObject>(Entry));
	}
	FString Out;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Out);
	FJsonSerializer::Serialize(List, Writer);
	return Out;
}
