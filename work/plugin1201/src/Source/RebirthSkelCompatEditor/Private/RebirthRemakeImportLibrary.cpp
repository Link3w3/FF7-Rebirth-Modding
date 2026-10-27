// The Remake Importer's editor functions (editor 1.16).
#include "RebirthRemakeImportLibrary.h"

#include "Animation/AnimSequence.h"   // (1.16.2) ExportAnimationsFbx
#include "Animation/Skeleton.h"
#include "AssetExportTask.h"
#include "Exporters/Exporter.h"
#include "Exporters/FbxExportOption.h"
#include "HAL/FileManager.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SkeletalMeshSocket.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "ReferenceSkeleton.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace
{
	FString RemakeImportJsonText(const TSharedRef<FJsonObject>& Object)
	{
		FString Out;
		const TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Out);
		FJsonSerializer::Serialize(Object, Writer);
		return Out;
	}

	FString RemakeImportFailed(const FString& Why)
	{
		const TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
		Report->SetStringField(TEXT("error"), Why);
		return RemakeImportJsonText(Report);
	}

	// [x, y, z] (or [pitch, yaw, roll]); Fallback when the field is not there
	FVector RemakeImportTriple(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field, const FVector& Fallback)
	{
		const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
		if (Object->TryGetArrayField(Field, Values) && Values && Values->Num() == 3)
		{
			return FVector((float)(*Values)[0]->AsNumber(), (float)(*Values)[1]->AsNumber(), (float)(*Values)[2]->AsNumber());
		}
		return Fallback;
	}
}

FString URebirthRemakeImportLibrary::AddSockets(UObject* SkeletonOrMesh, const FString& SocketsJson)
{
	USkeleton* Skeleton = Cast<USkeleton>(SkeletonOrMesh);
	USkeletalMesh* Mesh = Cast<USkeletalMesh>(SkeletonOrMesh);
	if (!Skeleton && !Mesh)
	{
		return RemakeImportFailed(SkeletonOrMesh ? FString::Printf(TEXT("%s is not a skeleton or a skeletal mesh"), *SkeletonOrMesh->GetPathName())
		                                         : FString(TEXT("no skeleton or skeletal mesh was given")));
	}
	TArray<TSharedPtr<FJsonValue>> Items;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(SocketsJson);
	if (!FJsonSerializer::Deserialize(Reader, Items))
	{
		return RemakeImportFailed(TEXT("the sockets are not a JSON array"));
	}
	const FReferenceSkeleton& Bones = Skeleton ? Skeleton->GetReferenceSkeleton() : Mesh->RefSkeleton;
	TArray<USkeletalMeshSocket*>& List = Skeleton ? Skeleton->Sockets : Mesh->GetMeshOnlySocketList();
	TArray<TSharedPtr<FJsonValue>> Added, Replaced, Skipped;
	bool bChanged = false;
	for (const TSharedPtr<FJsonValue>& Item : Items)
	{
		const TSharedPtr<FJsonObject>* Object = nullptr;
		if (!Item.IsValid() || !Item->TryGetObject(Object) || !Object || !Object->IsValid())
		{
			Skipped.Add(MakeShared<FJsonValueString>(TEXT("(not a socket)")));
			continue;
		}
		FString Name, Bone;
		(*Object)->TryGetStringField(TEXT("name"), Name);
		(*Object)->TryGetStringField(TEXT("bone"), Bone);
		Name.TrimStartAndEndInline();
		Bone.TrimStartAndEndInline();
		if (Name.IsEmpty() || Bone.IsEmpty() || Bones.FindBoneIndex(FName(*Bone)) == INDEX_NONE)
		{
			Skipped.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("%s (no bone %s)"), Name.IsEmpty() ? TEXT("?") : *Name,
			                                                         Bone.IsEmpty() ? TEXT("given") : *Bone)));
			continue;
		}
		const FName SocketName(*Name);
		const int32 At = List.IndexOfByPredicate([&SocketName](const USkeletalMeshSocket* One) { return One && One->SocketName == SocketName; });
		if (!bChanged)
		{
			SkeletonOrMesh->Modify();
			bChanged = true;
		}
		USkeletalMeshSocket* Socket = At != INDEX_NONE ? List[At] : NewObject<USkeletalMeshSocket>(SkeletonOrMesh, NAME_None, RF_Transactional);
		Socket->Modify();
		Socket->SocketName = SocketName;
		Socket->BoneName = FName(*Bone);
		Socket->RelativeLocation = RemakeImportTriple(*Object, TEXT("location"), FVector::ZeroVector);
		const FVector Rotation = RemakeImportTriple(*Object, TEXT("rotation"), FVector::ZeroVector);
		Socket->RelativeRotation = FRotator(Rotation.X, Rotation.Y, Rotation.Z);
		Socket->RelativeScale = RemakeImportTriple(*Object, TEXT("scale"), FVector::OneVector);
		bool bAlways = true;
		if ((*Object)->TryGetBoolField(TEXT("always_animated"), bAlways))
		{
			Socket->bForceAlwaysAnimated = bAlways;
		}
		if (At == INDEX_NONE)
		{
			List.Add(Socket);
			Added.Add(MakeShared<FJsonValueString>(Name));
		}
		else
		{
			Replaced.Add(MakeShared<FJsonValueString>(Name));
		}
	}
	if (bChanged)
	{
		if (Mesh)
		{
			Mesh->RebuildSocketMap();
		}
		SkeletonOrMesh->MarkPackageDirty();
	}
	const TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
	Report->SetStringField(TEXT("on"), SkeletonOrMesh->GetPathName());
	Report->SetArrayField(TEXT("added"), Added);
	Report->SetArrayField(TEXT("replaced"), Replaced);
	Report->SetArrayField(TEXT("skipped"), Skipped);
	return RemakeImportJsonText(Report);
}

FString URebirthRemakeImportLibrary::ExportAnimationsFbx(const TArray<FString>& AnimationPaths, const TArray<FString>& Files, const FString& PreviewMeshPath)
{
	if (AnimationPaths.Num() != Files.Num())
	{
		return RemakeImportFailed(FString::Printf(TEXT("%d animations but %d files"), AnimationPaths.Num(), Files.Num()));
	}
	USkeletalMesh* PreviewMesh = nullptr;
	if (!PreviewMeshPath.IsEmpty())
	{
		PreviewMesh = LoadObject<USkeletalMesh>(nullptr, *PreviewMeshPath);
		if (!PreviewMesh)
		{
			return RemakeImportFailed(FString::Printf(TEXT("the preview mesh does not load: %s"), *PreviewMeshPath));
		}
	}
	// (the engine's UAnimSequenceExporterFBX is not exported from UnrealEd: found by name)
	UClass* FbxExporterClass = FindObject<UClass>(ANY_PACKAGE, TEXT("AnimSequenceExporterFBX"));
	UFbxExportOption* Options = NewObject<UFbxExportOption>();
	Options->bASCII = false;
	Options->bExportPreviewMesh = false;
	Options->MapSkeletalMotionToRoot = false;
	TArray<TSharedPtr<FJsonValue>> Exported;
	TArray<TSharedPtr<FJsonValue>> Failed;
	auto Fail = [&Failed](const FString& Animation, const FString& Why)
	{
		const TSharedRef<FJsonObject> Item = MakeShared<FJsonObject>();
		Item->SetStringField(TEXT("animation"), Animation);
		Item->SetStringField(TEXT("why"), Why);
		Failed.Add(MakeShared<FJsonValueObject>(Item));
	};
	for (int32 Index = 0; Index < AnimationPaths.Num(); ++Index)
	{
		const FString& Path = AnimationPaths[Index];
		const FString& File = Files[Index];
		UAnimSequence* Animation = LoadObject<UAnimSequence>(nullptr, *Path);
		if (!Animation)
		{
			Fail(Path, TEXT("does not load"));
			continue;
		}
		USkeleton* Skeleton = Animation->GetSkeleton();
		if (!Skeleton)
		{
			Fail(Path, TEXT("has no skeleton"));
			continue;
		}
		const bool bOwnPreview = Animation->GetPreviewMesh() != nullptr || Skeleton->GetPreviewMesh() != nullptr;
		if (!bOwnPreview)
		{
			if (!PreviewMesh || PreviewMesh->Skeleton != Skeleton)
			{
				Fail(Path, TEXT("has no preview mesh, and Preview Mesh Path is not a mesh of its skeleton"));
				continue;
			}
			Animation->SetPreviewMesh(PreviewMesh, false);
		}
		IFileManager::Get().MakeDirectory(*FPaths::GetPath(File), true);
		UAssetExportTask* Task = NewObject<UAssetExportTask>();
		Task->Object = Animation;
		Task->Exporter = FbxExporterClass ? NewObject<UExporter>(GetTransientPackage(), FbxExporterClass) : nullptr;   // (none: the engine picks the .fbx exporter)
		Task->Filename = File;
		Task->bSelected = false;
		Task->bReplaceIdentical = true;
		Task->bPrompt = false;
		Task->bAutomated = true;
		Task->Options = Options;
		const bool bWritten = UExporter::RunAssetExportTask(Task);
		if (!bOwnPreview)
		{
			Animation->SetPreviewMesh(nullptr, false);
		}
		if (bWritten && IFileManager::Get().FileSize(*File) > 0)
		{
			Exported.Add(MakeShared<FJsonValueString>(File));
		}
		else
		{
			Fail(Path, TEXT("the FBX exporter did not write the file"));
		}
	}
	const TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
	Report->SetArrayField(TEXT("exported"), Exported);
	Report->SetArrayField(TEXT("failed"), Failed);
	return RemakeImportJsonText(Report);
}
