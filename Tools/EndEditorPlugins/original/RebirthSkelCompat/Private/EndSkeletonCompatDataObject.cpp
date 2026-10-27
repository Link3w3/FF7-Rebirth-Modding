// RebirthSkelCompat: KH3-style compatible skeletons for FINAL FANTASY VII REBIRTH mods.
#include "EndSkeletonCompatDataObject.h"

#include "Animation/Skeleton.h"
#include "AssetRegistryModule.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "EdGraphSchema_K2.h"
#include "Engine/AssetUserData.h"
#include "Engine/Blueprint.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Engine/SkeletalMesh.h"
#include "FileHelpers.h"
#include "HAL/FileManager.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Misc/FileHelper.h"
#include "Misc/MessageDialog.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "ReferenceSkeleton.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UObject/Package.h"
#include "UObject/StructOnScope.h"
#include "UObject/UObjectGlobals.h"
#include "UObject/UnrealType.h"

DEFINE_LOG_CATEGORY_STATIC(LogRebirthSkelCompat, Log, All);

namespace RebirthSkelCompatEditor
{
// The Blueprint the UE4SS mod reads in game. Parent is the native AssetUserData, which the retail game has.
const TCHAR* const CarrierPackage = TEXT("/Game/RebirthSkelCompat/BP_SkelCompatUserData");
const TCHAR* const CarrierName = TEXT("BP_SkelCompatUserData");
const TCHAR* const AnimationSkeletonsVariable = TEXT("AnimationSkeletons");
const TCHAR* const ReceivingMeshesVariable = TEXT("ReceivingMeshes");
const TCHAR* const DefaultGameDirectory = TEXT("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII REBIRTH");
constexpr int32 MaxMeshesPerPair = 32;

FString PathOf(const UObject* Object) { return Object ? Object->GetPathName() : FString(TEXT("None")); }

// Assets loaded from the game's cooked files. Saving one from the editor turns it into an editor copy of a
// retail file, and rebinding a game mesh changes it everywhere the game shows it.
bool IsCookedAsset(const UObject* Object)
{
	const UPackage* Package = Object ? Object->GetOutermost() : nullptr;
	return Package && Package->HasAnyPackageFlags(PKG_Cooked);
}

// ------------------------------------------------------------------------------------------------
// Bone hierarchy test. Port of UE 4.26 USkeleton::IsCompatibleMesh / DoesParentChainMatch: the
// game only spawns an AnimBlueprint on a mesh when this passes against the AnimBlueprint's
// skeleton. In game the mesh is bound to the animation skeleton, so test against that one.
// ------------------------------------------------------------------------------------------------
struct FBoneCheck
{
	bool bCompatible = false;
	int32 Matched = 0;
	int32 MeshOnly = 0;
	int32 AnimationOnly = 0;
	FString Problem;
};

FString Chain(const FReferenceSkeleton& Skeleton, int32 Bone)
{
	FString Text;
	for (int32 Guard = 0; Bone != INDEX_NONE && Guard < 6; ++Guard)
	{
		Text += (Text.IsEmpty() ? TEXT("") : TEXT(" < ")) + Skeleton.GetBoneName(Bone).ToString();
		Bone = Skeleton.GetParentIndex(Bone);
	}
	return Bone == INDEX_NONE ? Text : Text + TEXT(" < ...");
}

bool ParentChainMatches(int32 SkeletonBone, const FReferenceSkeleton& Skeleton, const FReferenceSkeleton& Mesh)
{
	if (SkeletonBone == 0)
	{
		return Skeleton.GetBoneName(0) == Mesh.GetBoneName(0);
	}
	int32 MeshBone = Mesh.FindBoneIndex(Skeleton.GetBoneName(SkeletonBone));
	if (MeshBone == INDEX_NONE)
	{
		return false;
	}
	for (;;)
	{
		const int32 SkeletonParent = Skeleton.GetParentIndex(SkeletonBone);
		const int32 MeshParent = Mesh.GetParentIndex(MeshBone);
		if (SkeletonParent == INDEX_NONE || MeshParent == INDEX_NONE)
		{
			return SkeletonParent == MeshParent;
		}
		if (Skeleton.GetBoneName(SkeletonParent) != Mesh.GetBoneName(MeshParent))
		{
			return false;
		}
		SkeletonBone = SkeletonParent;
		MeshBone = MeshParent;
	}
}

FBoneCheck CheckMesh(const FReferenceSkeleton& Mesh, const FReferenceSkeleton& Skeleton)
{
	FBoneCheck Result;
	for (int32 Bone = 0; Bone < Skeleton.GetRawBoneNum(); ++Bone)
	{
		if (Mesh.FindBoneIndex(Skeleton.GetBoneName(Bone)) == INDEX_NONE)
		{
			++Result.AnimationOnly;
		}
	}
	const int32 RawBones = Mesh.GetRawBoneNum();
	for (int32 MeshBone = 0; MeshBone < RawBones; ++MeshBone)
	{
		const FName Name = Mesh.GetBoneName(MeshBone);
		int32 SkeletonBone = Skeleton.FindBoneIndex(Name);
		if (SkeletonBone != INDEX_NONE)
		{
			++Result.Matched;
		}
		else
		{
			++Result.MeshOnly;
			int32 Current = MeshBone;
			while (SkeletonBone == INDEX_NONE && Current != INDEX_NONE)
			{
				const int32 Parent = Mesh.GetParentIndex(Current);
				if (Parent != INDEX_NONE)
				{
					SkeletonBone = Skeleton.FindBoneIndex(Mesh.GetBoneName(Parent));
				}
				if (Parent == 0)
				{
					break;
				}
				Current = Parent;
			}
			if (SkeletonBone == INDEX_NONE)
			{
				Result.Problem = MeshBone == 0
					? FString::Printf(TEXT("root bone '%s' is not on the animation skeleton (its root is '%s')"), *Name.ToString(), *Skeleton.GetBoneName(0).ToString())
					: FString::Printf(TEXT("bone '%s' has no ancestor on the animation skeleton"), *Name.ToString());
				return Result;
			}
		}
		if (!ParentChainMatches(SkeletonBone, Skeleton, Mesh))
		{
			const int32 InMesh = Mesh.FindBoneIndex(Skeleton.GetBoneName(SkeletonBone));
			Result.Problem = SkeletonBone == 0
				? FString::Printf(TEXT("root bone names differ: mesh '%s', animation skeleton '%s'"), *Mesh.GetBoneName(0).ToString(), *Skeleton.GetBoneName(0).ToString())
				: FString::Printf(TEXT("parent chain of '%s' differs. Mesh: %s. Animation skeleton: %s"), *Skeleton.GetBoneName(SkeletonBone).ToString(),
					*Chain(Mesh, InMesh), *Chain(Skeleton, SkeletonBone));
			return Result;
		}
	}
	Result.bCompatible = Result.Matched > 0;
	if (!Result.bCompatible)
	{
		Result.Problem = TEXT("no bone names in common");
	}
	return Result;
}

// ------------------------------------------------------------------------------------------------
// Assets
// ------------------------------------------------------------------------------------------------
TArray<USkeletalMesh*> MeshesFor(const FEndSkeletonCompatPair& Pair, USkeleton* Receiving, FString& Report)
{
	TArray<USkeletalMesh*> Meshes;
	if (Pair.ReceivingMeshes.Num() > 0)
	{
		for (const TSoftObjectPtr<USkeletalMesh>& Soft : Pair.ReceivingMeshes)
		{
			if (Soft.IsNull())
			{
				continue;
			}
			USkeletalMesh* Mesh = Soft.LoadSynchronous();
			if (!Mesh)
			{
				Report += FString::Printf(TEXT("    ! mesh %s could not be loaded\n"), *Soft.ToString());
				continue;
			}
			if (Mesh->Skeleton != Receiving)
			{
				Report += FString::Printf(TEXT("    ! %s uses %s, not the receiving skeleton: the game will not rebind it\n"),
					*Mesh->GetName(), *PathOf(Mesh->Skeleton));
			}
			Meshes.Add(Mesh);
		}
		return Meshes;
	}

	IAssetRegistry& Registry = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry")).Get();
	FARFilter Filter;
	Filter.ClassNames.Add(USkeletalMesh::StaticClass()->GetFName());
	Filter.bRecursiveClasses = true;
	Filter.TagsAndValues.Add(FName(TEXT("Skeleton")), FAssetData(Receiving).GetExportTextName());
	TArray<FAssetData> Assets;
	Registry.GetAssets(Filter, Assets);
	for (const FAssetData& Asset : Assets)
	{
		if (Meshes.Num() >= MaxMeshesPerPair)
		{
			Report += FString::Printf(TEXT("    (only the first %d meshes were checked)\n"), MaxMeshesPerPair);
			break;
		}
		if (USkeletalMesh* Mesh = Cast<USkeletalMesh>(Asset.GetAsset()))
		{
			Meshes.Add(Mesh);
		}
	}
	return Meshes;
}

bool CheckPair(const FEndSkeletonCompatPair& Pair, int32 Index, const TArray<FEndSkeletonCompatPair>& All, FString& Report)
{
	Report += FString::Printf(TEXT("Pair %d: %s\n"), Index, Pair.ReceivingSkeleton.IsNull() ? TEXT("(no receiving skeleton)") : *Pair.ReceivingSkeleton.ToString());
	if (!Pair.bEnabled)
	{
		Report += TEXT("    disabled\n");
		return true;
	}
	USkeleton* Receiving = Pair.ReceivingSkeleton.LoadSynchronous();
	if (!Receiving)
	{
		Report += TEXT("    ERROR: receiving skeleton not set or not found\n");
		return false;
	}
	if (IsCookedAsset(Receiving))
	{
		Report += TEXT("    note: the receiving skeleton is a game asset, so Apply To Skeletons leaves it alone; use Export Json\n");
	}
	bool bOk = true;
	TArray<USkeleton*> Animation;
	for (const TSoftObjectPtr<USkeleton>& Soft : Pair.AnimationSkeletons)
	{
		if (Soft.IsNull())
		{
			continue;
		}
		USkeleton* Skeleton = Soft.LoadSynchronous();
		if (!Skeleton)
		{
			Report += FString::Printf(TEXT("    ERROR: animation skeleton %s not found\n"), *Soft.ToString());
			bOk = false;
		}
		else if (Skeleton == Receiving)
		{
			Report += TEXT("    ERROR: the receiving skeleton is listed as its own animation skeleton\n");
			bOk = false;
		}
		else
		{
			Animation.AddUnique(Skeleton);
		}
	}
	if (Animation.Num() == 0)
	{
		Report += TEXT("    ERROR: no usable animation skeleton\n");
		return false;
	}
	for (int32 Other = 0; Other < All.Num(); ++Other)
	{
		if (Other == Index || !All[Other].bEnabled)
		{
			continue;
		}
		for (const TSoftObjectPtr<USkeleton>& Soft : All[Other].AnimationSkeletons)
		{
			if (Soft.ToSoftObjectPath() == Pair.ReceivingSkeleton.ToSoftObjectPath())
			{
				Report += FString::Printf(TEXT("    ERROR: pair %d uses this receiving skeleton as an animation skeleton; the mod ignores chained pairs\n"), Other);
				bOk = false;
			}
		}
		if (Other < Index && All[Other].ReceivingSkeleton.ToSoftObjectPath() == Pair.ReceivingSkeleton.ToSoftObjectPath())
		{
			Report += FString::Printf(TEXT("    note: same receiving skeleton as pair %d; the mod merges both lists\n"), Other);
		}
	}

	const TArray<USkeletalMesh*> Meshes = MeshesFor(Pair, Receiving, Report);
	if (Meshes.Num() == 0)
	{
		Report += TEXT("    no meshes found on the receiving skeleton to check\n");
	}
	for (USkeletalMesh* Mesh : Meshes)
	{
		if (IsCookedAsset(Mesh))
		{
			Report += FString::Printf(TEXT("    note: %s is a game mesh. While this pair is active it uses the animation skeleton everywhere the game shows it, so its own AnimBlueprints stop working there. For a replacement character, list your own copy of the mesh instead.\n"), *Mesh->GetName());
		}
		for (USkeleton* Skeleton : Animation)
		{
			const FBoneCheck Check = CheckMesh(Mesh->RefSkeleton, Skeleton->GetReferenceSkeleton());
			Report += FString::Printf(TEXT("    %s -> %s: %d shared, %d mesh-only, %d animation-only. %s\n"), *Mesh->GetName(), *Skeleton->GetName(),
				Check.Matched, Check.MeshOnly, Check.AnimationOnly,
				Check.bCompatible ? TEXT("OK, AnimBlueprints for this skeleton will run")
				                  : *(FString(TEXT("REFUSED by the game (T-pose): ")) + Check.Problem));
			bOk &= Check.bCompatible;
		}
	}
	return bOk;
}

// ------------------------------------------------------------------------------------------------
// Carrier Blueprint (AssetUserData) and its two array variables. The arrays hold object paths as
// strings, not soft references: soft references would make the cooker pull the (retail) animation
// skeleton into your mod's cook. The mod also accepts Name or soft/hard reference arrays.
// ------------------------------------------------------------------------------------------------
bool IsPathArrayType(const FEdGraphPinType& Type)
{
	return Type.ContainerType == EPinContainerType::Array &&
		(Type.PinCategory == UEdGraphSchema_K2::PC_String || Type.PinCategory == UEdGraphSchema_K2::PC_Name ||
		 Type.PinCategory == UEdGraphSchema_K2::PC_SoftObject);
}

bool EnsureArrayVariable(UBlueprint* Blueprint, const FName Name, bool& bChanged, FString& Report)
{
	const int32 Existing = FBlueprintEditorUtils::FindNewVariableIndex(Blueprint, Name);
	if (Existing != INDEX_NONE)
	{
		if (!IsPathArrayType(Blueprint->NewVariables[Existing].VarType))
		{
			Report += FString::Printf(TEXT("ERROR: %s.%s exists but is not an array of strings\n"), CarrierName, *Name.ToString());
			return false;
		}
		return true;
	}
	FEdGraphPinType Type;
	Type.PinCategory = UEdGraphSchema_K2::PC_String;
	Type.ContainerType = EPinContainerType::Array;
	if (!FBlueprintEditorUtils::AddMemberVariable(Blueprint, Name, Type))
	{
		Report += FString::Printf(TEXT("ERROR: could not add %s to %s\n"), *Name.ToString(), CarrierName);
		return false;
	}
	FBlueprintEditorUtils::SetBlueprintOnlyEditableFlag(Blueprint, Name, false); // editable on the skeleton's instance
	bChanged = true;
	return true;
}

UClass* FindOrCreateCarrier(bool bCreate, TArray<UPackage*>& Dirty, FString& Report)
{
	const FString ObjectPath = FString(CarrierPackage) + TEXT(".") + CarrierName;
	UBlueprint* Blueprint = LoadObject<UBlueprint>(nullptr, *ObjectPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	bool bChanged = false;
	if (!Blueprint && !bCreate)
	{
		Report += ObjectPath + TEXT(" does not exist, so no skeleton carries a list\n");
		return nullptr;
	}
	if (!Blueprint)
	{
		UPackage* Package = CreatePackage(CarrierPackage);
		Blueprint = FKismetEditorUtilities::CreateBlueprint(UAssetUserData::StaticClass(), Package, FName(CarrierName), BPTYPE_Normal,
			UBlueprint::StaticClass(), UBlueprintGeneratedClass::StaticClass(), FName(TEXT("RebirthSkelCompat")));
		if (!Blueprint)
		{
			Report += TEXT("ERROR: could not create ") + ObjectPath + TEXT("\n");
			return nullptr;
		}
		FAssetRegistryModule::AssetCreated(Blueprint);
		Report += TEXT("Created ") + ObjectPath + TEXT("\n");
		bChanged = true;
	}
	if (Blueprint->ParentClass != UAssetUserData::StaticClass())
	{
		Report += TEXT("ERROR: ") + ObjectPath + TEXT(" must have AssetUserData as its parent class\n");
		return nullptr;
	}
	if (!EnsureArrayVariable(Blueprint, AnimationSkeletonsVariable, bChanged, Report) ||
		!EnsureArrayVariable(Blueprint, ReceivingMeshesVariable, bChanged, Report))
	{
		return nullptr;
	}
	if (bChanged || !Blueprint->GeneratedClass || Blueprint->Status != BS_UpToDate)
	{
		FKismetEditorUtilities::CompileBlueprint(Blueprint);
		Blueprint->MarkPackageDirty();
		Dirty.AddUnique(Blueprint->GetOutermost());
	}
	UClass* Generated = Blueprint->GeneratedClass;
	if (!Generated || !Generated->IsChildOf(UAssetUserData::StaticClass()))
	{
		Report += TEXT("ERROR: ") + ObjectPath + TEXT(" did not compile\n");
		return nullptr;
	}
	return Generated;
}

bool SetPathArray(UObject* Target, const FName Name, const TArray<FSoftObjectPath>& Paths)
{
	FArrayProperty* Array = FindFProperty<FArrayProperty>(Target->GetClass(), Name);
	if (!Array)
	{
		return false;
	}
	FStrProperty* AsString = CastField<FStrProperty>(Array->Inner);
	FNameProperty* AsName = CastField<FNameProperty>(Array->Inner);
	FSoftObjectProperty* AsSoft = CastField<FSoftObjectProperty>(Array->Inner);
	if (!AsString && !AsName && !AsSoft)
	{
		return false;
	}
	FScriptArrayHelper Helper(Array, Array->ContainerPtrToValuePtr<void>(Target));
	Helper.EmptyValues();
	for (const FSoftObjectPath& Path : Paths)
	{
		const int32 Index = Helper.AddValue();
		if (AsString)
		{
			AsString->SetPropertyValue(Helper.GetRawPtr(Index), Path.ToString());
		}
		else if (AsName)
		{
			AsName->SetPropertyValue(Helper.GetRawPtr(Index), FName(*Path.ToString()));
		}
		else
		{
			AsSoft->SetPropertyValue(Helper.GetRawPtr(Index), FSoftObjectPtr(Path));
		}
	}
	return true;
}

// Optional: RebirthMaterialPreview's editor-side registry (RegisterCompatibleSkeletons), called by reflection so this
// plugin does not depend on that module.
bool RegisterForEditorPreview(USkeleton* Receiving, USkeleton* Animation, FString& Diagnostic)
{
	UClass* Library = FindObject<UClass>(ANY_PACKAGE, TEXT("RebirthSkeletonCompatibilityEditorLibrary"));
	UFunction* Function = Library ? Library->FindFunctionByName(TEXT("RegisterCompatibleSkeletons")) : nullptr;
	if (!Function)
	{
		Diagnostic = TEXT("RebirthMaterialPreview editor registry not loaded");
		return false;
	}
	FStructOnScope Params(Function);
	uint8* Memory = Params.GetStructMemory();
	FObjectProperty* A = FindFProperty<FObjectProperty>(Function, TEXT("A"));
	FObjectProperty* B = FindFProperty<FObjectProperty>(Function, TEXT("B"));
	FStrProperty* Out = FindFProperty<FStrProperty>(Function, TEXT("OutDiagnostic"));
	FBoolProperty* Persist = FindFProperty<FBoolProperty>(Function, TEXT("bPersistManifest"));
	FBoolProperty* Return = FindFProperty<FBoolProperty>(Function, TEXT("ReturnValue"));
	if (!A || !B || !Return)
	{
		Diagnostic = TEXT("unexpected RegisterCompatibleSkeletons signature");
		return false;
	}
	A->SetObjectPropertyValue_InContainer(Memory, Receiving);
	B->SetObjectPropertyValue_InContainer(Memory, Animation);
	if (Persist)
	{
		Persist->SetPropertyValue_InContainer(Memory, true);
	}
	Library->GetDefaultObject()->ProcessEvent(Function, Memory);
	if (Out)
	{
		Diagnostic = Out->GetPropertyValue_InContainer(Memory);
	}
	return Return->GetPropertyValue_InContainer(Memory);
}
} // namespace RebirthSkelCompatEditor

using namespace RebirthSkelCompatEditor;

UEndSkeletonCompatDataObject::UEndSkeletonCompatDataObject()
{
	GameDirectory.Path = DefaultGameDirectory;
}

bool UEndSkeletonCompatDataObject::ValidatePairs(FString& OutReport) const
{
	OutReport.Reset();
	bool bOk = Pairs.Num() > 0;
	if (!bOk)
	{
		OutReport += TEXT("No pairs.\n");
	}
	for (int32 Index = 0; Index < Pairs.Num(); ++Index)
	{
		bOk &= CheckPair(Pairs[Index], Index, Pairs, OutReport);
	}
	return bOk;
}

FString UEndSkeletonCompatDataObject::ToRuntimeJson() const
{
	TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
	Root->SetStringField(TEXT("schema"), TEXT("RebirthSkelCompat/1"));
	Root->SetStringField(TEXT("source"), GetPathName());
	TArray<TSharedPtr<FJsonValue>> PairValues;
	for (const FEndSkeletonCompatPair& Pair : Pairs)
	{
		if (Pair.ReceivingSkeleton.IsNull())
		{
			continue;
		}
		TSharedRef<FJsonObject> Entry = MakeShared<FJsonObject>();
		Entry->SetStringField(TEXT("receiving_skeleton"), Pair.ReceivingSkeleton.ToSoftObjectPath().ToString());
		TArray<TSharedPtr<FJsonValue>> Animation;
		for (const TSoftObjectPtr<USkeleton>& Soft : Pair.AnimationSkeletons)
		{
			if (!Soft.IsNull())
			{
				Animation.Add(MakeShared<FJsonValueString>(Soft.ToSoftObjectPath().ToString()));
			}
		}
		Entry->SetArrayField(TEXT("animation_skeletons"), Animation);
		TArray<TSharedPtr<FJsonValue>> Meshes;
		for (const TSoftObjectPtr<USkeletalMesh>& Soft : Pair.ReceivingMeshes)
		{
			if (!Soft.IsNull())
			{
				Meshes.Add(MakeShared<FJsonValueString>(Soft.ToSoftObjectPath().ToString()));
			}
		}
		if (Meshes.Num() > 0)
		{
			Entry->SetArrayField(TEXT("receiving_meshes"), Meshes);
		}
		Entry->SetBoolField(TEXT("repair_live_components"), Pair.bRepairLiveComponents);
		Entry->SetBoolField(TEXT("enabled"), Pair.bEnabled);
		PairValues.Add(MakeShared<FJsonValueObject>(Entry));
	}
	Root->SetArrayField(TEXT("pairs"), PairValues);
	FString Text;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Text);
	FJsonSerializer::Serialize(Root, Writer);
	return Text;
}

bool UEndSkeletonCompatDataObject::WriteRuntimeJson(FString& OutReport) const
{
	OutReport.Reset();
	const FString Json = ToRuntimeJson();
	bool bOk = true;
	auto Write = [&](const FString& File)
	{
		const FString Full = FPaths::ConvertRelativePathToFull(File);
		IFileManager::Get().MakeDirectory(*FPaths::GetPath(Full), true);
		if (FFileHelper::SaveStringToFile(Json, *Full, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
		{
			OutReport += TEXT("Wrote ") + Full + TEXT("\n");
		}
		else
		{
			OutReport += TEXT("ERROR: could not write ") + Full + TEXT("\n");
			bOk = false;
		}
	};
	const FString Directory = ExportDirectory.Path.IsEmpty() ? FPaths::ProjectSavedDir() / TEXT("RebirthSkelCompat") : ExportDirectory.Path;
	Write(Directory / GetName() + TEXT(".skelcompat.json"));
	if (!GameDirectory.Path.IsEmpty())
	{
		const FString ModDirectory = GameDirectory.Path / TEXT("End/Binaries/Win64/ue4ss/Mods/RebirthSkelCompat");
		if (IFileManager::Get().DirectoryExists(*ModDirectory))
		{
			Write(ModDirectory / TEXT("compat") / GetName() + TEXT(".json"));
		}
		else
		{
			OutReport += TEXT("RebirthSkelCompat is not installed under ") + GameDirectory.Path + TEXT(" (game copy skipped)\n");
		}
	}
	OutReport += TEXT("\n") + Json;
	return bOk;
}

bool UEndSkeletonCompatDataObject::ApplyPairsToSkeletons(bool bRemove, FString& OutReport)
{
	OutReport.Reset();
	TArray<UPackage*> Dirty;
	UClass* Carrier = FindOrCreateCarrier(!bRemove, Dirty, OutReport);
	if (!Carrier)
	{
		return bRemove;
	}
	// Several pairs may name the same receiving skeleton: one list per skeleton, merged like the mod merges JSON.
	struct FMerged
	{
		bool bEnabled = false;
		bool bAllMeshes = false;
		TArray<FSoftObjectPath> Animation;
		TArray<FSoftObjectPath> Meshes;
	};
	TArray<USkeleton*> Order;
	TMap<USkeleton*, FMerged> Merged;
	bool bOk = true;
	for (int32 Index = 0; Index < Pairs.Num(); ++Index)
	{
		const FEndSkeletonCompatPair& Pair = Pairs[Index];
		if (Pair.ReceivingSkeleton.IsNull())
		{
			continue;
		}
		USkeleton* Receiving = Pair.ReceivingSkeleton.LoadSynchronous();
		if (!Receiving)
		{
			OutReport += FString::Printf(TEXT("Pair %d: ERROR: %s not found\n"), Index, *Pair.ReceivingSkeleton.ToString());
			bOk = false;
			continue;
		}
		FMerged& Entry = Merged.FindOrAdd(Receiving);
		Order.AddUnique(Receiving);
		if (bRemove || !Pair.bEnabled)
		{
			continue;
		}
		Entry.bEnabled = true;
		for (const TSoftObjectPtr<USkeleton>& Soft : Pair.AnimationSkeletons)
		{
			if (!Soft.IsNull() && Soft.ToSoftObjectPath() != Pair.ReceivingSkeleton.ToSoftObjectPath())
			{
				Entry.Animation.AddUnique(Soft.ToSoftObjectPath());
			}
		}
		int32 Listed = 0;
		for (const TSoftObjectPtr<USkeletalMesh>& Soft : Pair.ReceivingMeshes)
		{
			if (!Soft.IsNull())
			{
				Entry.Meshes.AddUnique(Soft.ToSoftObjectPath());
				++Listed;
			}
		}
		Entry.bAllMeshes |= Listed == 0;
	}

	for (USkeleton* Receiving : Order)
	{
		FMerged& Entry = Merged[Receiving];
		if (IsCookedAsset(Receiving))
		{
			OutReport += FString::Printf(TEXT("%s: NOT changed. It is a cooked game asset, and saving it from the editor would replace it with an editor copy. Use Export Json, or make the receiving skeleton your own skeleton asset.\n"), *Receiving->GetName());
			if (!bRemove)
			{
				bOk = false;
			}
			continue;
		}
		if (!Entry.bEnabled)
		{
			if (Receiving->GetAssetUserDataOfClass(Carrier))
			{
				Receiving->Modify();
				Receiving->RemoveUserDataOfClass(Carrier);
				Receiving->MarkPackageDirty();
				Dirty.AddUnique(Receiving->GetOutermost());
				OutReport += FString::Printf(TEXT("%s: list removed\n"), *Receiving->GetName());
			}
			continue;
		}
		if (Entry.Animation.Num() == 0)
		{
			OutReport += FString::Printf(TEXT("%s: ERROR: no animation skeleton\n"), *Receiving->GetName());
			bOk = false;
			continue;
		}
		if (Entry.bAllMeshes)
		{
			Entry.Meshes.Reset();
		}
		Receiving->Modify();
		UAssetUserData* Data = Receiving->GetAssetUserDataOfClass(Carrier);
		if (!Data)
		{
			Data = NewObject<UAssetUserData>(Receiving, Carrier, NAME_None, RF_Transactional);
			Receiving->AddAssetUserData(Data);
		}
		Data->Modify();
		if (!SetPathArray(Data, AnimationSkeletonsVariable, Entry.Animation) || !SetPathArray(Data, ReceivingMeshesVariable, Entry.Meshes))
		{
			OutReport += FString::Printf(TEXT("%s: ERROR: %s has unexpected variables\n"), *Receiving->GetName(), CarrierName);
			bOk = false;
			continue;
		}
		Receiving->MarkPackageDirty();
		Dirty.AddUnique(Receiving->GetOutermost());
		OutReport += FString::Printf(TEXT("%s: lists %d animation skeleton(s), %s\n"), *Receiving->GetName(), Entry.Animation.Num(),
			Entry.Meshes.Num() ? *FString::Printf(TEXT("%d mesh(es)"), Entry.Meshes.Num()) : TEXT("all its meshes"));
		if (bRegisterForEditorPreview)
		{
			for (const FSoftObjectPath& Path : Entry.Animation)
			{
				FString Diagnostic;
				USkeleton* AnimationSkeleton = Cast<USkeleton>(Path.TryLoad());
				const bool bRegistered = AnimationSkeleton && RegisterForEditorPreview(Receiving, AnimationSkeleton, Diagnostic);
				OutReport += FString::Printf(TEXT("    editor preview with %s: %s%s%s\n"), *Path.GetAssetName(),
					bRegistered ? TEXT("registered") : TEXT("not registered"), Diagnostic.IsEmpty() ? TEXT("") : TEXT(" - "), *Diagnostic);
			}
		}
	}
	if (Dirty.Num() > 0)
	{
		FEditorFileUtils::PromptForCheckoutAndSave(Dirty, false, true);
		OutReport += TEXT("\nSave the changed packages (you were prompted), then cook and pak them with your mod. ")
			TEXT("BP_SkelCompatUserData cooks along with the skeleton; the game reads the list from it.\n");
	}
	return bOk;
}

void UEndSkeletonCompatDataObject::ShowResult(const FString& Title, const FString& Report, bool bOk)
{
	LastResult = Title + (bOk ? TEXT(": OK\n\n") : TEXT(": PROBLEMS\n\n")) + Report;
	UE_LOG(LogRebirthSkelCompat, Log, TEXT("%s"), *LastResult);
	FMessageDialog::Open(EAppMsgType::Ok, FText::FromString(LastResult.Left(6000)));
}

void UEndSkeletonCompatDataObject::Validate()
{
	FString Report;
	const bool bOk = ValidatePairs(Report);
	ShowResult(TEXT("Validate"), Report, bOk);
}

void UEndSkeletonCompatDataObject::ApplyToSkeletons()
{
	FString Report;
	const bool bOk = ApplyPairsToSkeletons(false, Report);
	ShowResult(TEXT("Apply To Skeletons"), Report, bOk);
}

void UEndSkeletonCompatDataObject::RemoveFromSkeletons()
{
	FString Report;
	const bool bOk = ApplyPairsToSkeletons(true, Report);
	ShowResult(TEXT("Remove From Skeletons"), Report, bOk);
}

void UEndSkeletonCompatDataObject::ExportJson()
{
	FString Report;
	const bool bOk = WriteRuntimeJson(Report);
	ShowResult(TEXT("Export Json"), Report, bOk);
}
