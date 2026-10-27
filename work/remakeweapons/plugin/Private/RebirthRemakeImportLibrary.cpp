// The Remake Importer's editor functions (editor 1.16).
#include "RebirthRemakeImportLibrary.h"

#include "Animation/Skeleton.h"
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
