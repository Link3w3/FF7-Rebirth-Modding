// RebirthSkelCompat Parts Builder (editor 1.17): make a Customization part, see it on a character playing its animations
// the way the game plays them, put it in the game's Customization catalog and build its own assets into the game.
//
// What the game does with a part (Create a Character System 3.11, Customization: PutOnPart, Align, MoveParts), and so
// what the preview does:
//   * the part's model goes on a skeletal mesh component snapped to the character's Bone (a bone or a socket);
//   * every frame its own bone Anchor (default: Bone) is kept on that bone: the component is placed by the inverse of the
//     anchor's transform in the part's own space, then moved by Offset (in the bone's axes) and sized by Scale;
//   * sections not in Sections are hidden; a tint goes on the shown ones (a vector and/or a texture parameter);
//   * it plays: with Sync, its own motion of the name of the one the character plays (Sync Folder/<set>/<name>), at the
//     character's time; else its motion for the ability the character uses (Moves); else Idle, looping.
#include "EndPartsBuilder.h"
#include "EndSkinBuild.h"

#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "AssetRegistryModule.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Editor.h"
#include "EditorViewportClient.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SkeletalMeshSocket.h"
#include "Engine/Texture.h"
#include "Framework/Docking/TabManager.h"
#include "HAL/FileManager.h"
#include "IDetailsView.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "PreviewScene.h"
#include "PropertyEditorModule.h"
#include "SceneManagement.h"
#include "SEditorViewport.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Subsystems/AssetEditorSubsystem.h"
#include "UObject/Package.h"
#include "UObject/StrongObjectPtr.h"
#include "Widgets/Docking/SDockTab.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SSplitter.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/Text/STextBlock.h"

#define LOCTEXT_NAMESPACE "RebirthPartsBuilder"

// Named, not anonymous: the module may be compiled as one unity file with the other sources.
namespace RebirthPartsUtil
{
const TCHAR* const ConfigSection = TEXT("RebirthSkelCompat.PartsBuilder");
const TCHAR* const NoMove = TEXT("(none: its idle, or with Sync its motion of the preview animation's name)");
const TCHAR* const SameAsBone = TEXT("(the same name as Bone)");
// the set folders the game looks in for a synced part's motion when the character's own folder does not have it
const TCHAR* const SyncFolders[] = {TEXT("Battle00"), TEXT("Battle01"), TEXT("Battle00_Comp"), TEXT("Battle02"), TEXT("Battle03"), TEXT("Reaction00"),
									TEXT("Neutral00"), TEXT("Emotion00"), TEXT("Event00"), TEXT("FieldAction00")};

// "/Game/A/B" or "/Game/A/B.B" -> "/Game/A/B.B".
FString ObjectPathOf(FString Path)
{
	Path.TrimStartAndEndInline();
	if (!Path.IsEmpty() && !Path.Contains(TEXT(".")))
	{
		Path += TEXT(".") + FPackageName::GetShortName(Path);
	}
	return Path;
}

// A name as a catalog id: letters and digits, the rest _ (lower case): Sephiroth's wing -> sephiroth_s_wing.
FString IdFromName(const FString& Name)
{
	FString Out;
	for (const TCHAR C : Name.ToLower())
	{
		const bool bWord = (C >= TEXT('a') && C <= TEXT('z')) || (C >= TEXT('0') && C <= TEXT('9'));
		if (bWord)
		{
			Out.AppendChar(C);
		}
		else if (!Out.IsEmpty() && !Out.EndsWith(TEXT("_")))
		{
			Out.AppendChar(TEXT('_'));
		}
	}
	Out.RemoveFromEnd(TEXT("_"));
	return Out;
}

bool ValidId(const FString& Id)
{
	if (Id.IsEmpty() || Id.Len() > 64)
	{
		return false;
	}
	for (const TCHAR C : Id)
	{
		if (!FChar::IsAlnum(C) && C != TEXT('_') && C != TEXT('-'))
		{
			return false;
		}
	}
	return true;
}

// ".../Battle00/B_Idle01_1.B_Idle01_1" -> "Battle00/B_Idle01_1" (the game's RelOf: the folder and name under the motions).
FString RelOf(const FString& ObjectPath)
{
	const FString Package = FPackageName::ObjectPathToPackageName(ObjectPath);
	int32 Last = INDEX_NONE;
	if (!Package.FindLastChar(TEXT('/'), Last) || Last <= 0)
	{
		return FString();
	}
	const int32 Before = Package.Find(TEXT("/"), ESearchCase::CaseSensitive, ESearchDir::FromEnd, Last - 1);
	return Before == INDEX_NONE ? FString() : Package.Mid(Before + 1);
}

IAssetRegistry& Registry() { return FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry")).Get(); }

// The asset at an object path, when the project has it (looked up first: nothing is loaded for one that is not there).
template <typename T>
T* LoadIfThere(const FString& ObjectPath)
{
	if (ObjectPath.IsEmpty() || !Registry().GetAssetByObjectPath(FName(*ObjectPath)).IsValid())
	{
		return nullptr;
	}
	return Cast<T>(FSoftObjectPath(ObjectPath).TryLoad());
}

bool OpenInEditor(UObject* Asset)
{
	UAssetEditorSubsystem* Editors = GEditor ? GEditor->GetEditorSubsystem<UAssetEditorSubsystem>() : nullptr;
	return Asset && Editors && Editors->OpenEditorForAsset(Asset);
}

// ---- the catalog --------------------------------------------------------------------------------------------------
FString CatalogFolder(const FDirectoryPath& GameDirectory)
{
	const FString Mod = RebirthSkelCompatSkins::GameModFolderOf(GameDirectory);
	return Mod.IsEmpty() ? FString() : FPaths::Combine(Mod, TEXT("customization"));
}

bool ReadJson(const FString& File, TSharedPtr<FJsonObject>& Out, FString& Problem)
{
	Out.Reset();
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *File))
	{
		Problem = File + TEXT(" does not read");
		return false;
	}
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Out) || !Out.IsValid())
	{
		Problem = File + TEXT(" is not a JSON object (") + Reader->GetErrorMessage() + TEXT(")");
		return false;
	}
	return true;
}

// Written to <File>.new first, then over the old one (kept as <File>.partsbuilder.bak).
bool WriteJson(const FString& File, const TSharedRef<FJsonObject>& Root, FString& Problem)
{
	FString Text;
	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Text);
	if (!FJsonSerializer::Serialize(Root, Writer))
	{
		Problem = TEXT("the JSON of ") + File + TEXT(" could not be written");
		return false;
	}
	Text += TEXT("\n");
	const FString Temp = File + TEXT(".new");
	if (!FFileHelper::SaveStringToFile(Text, *Temp, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
	{
		Problem = TEXT("cannot write ") + Temp;
		return false;
	}
	if (FPaths::FileExists(File))
	{
		IFileManager::Get().Copy(*(File + TEXT(".partsbuilder.bak")), *File, true, true);
	}
	if (!IFileManager::Get().Move(*File, *Temp, true, true))
	{
		Problem = TEXT("cannot replace ") + File;
		return false;
	}
	return true;
}

FString IdOf(const TSharedPtr<FJsonObject>& Entry)
{
	FString Id, Name;
	if (!Entry.IsValid())
	{
		return Id;
	}
	if (!Entry->TryGetStringField(TEXT("id"), Id) || Id.IsEmpty())
	{
		Entry->TryGetStringField(TEXT("name"), Name);
		Id = Name;   // (the game's: an entry without an id is known by its name)
	}
	return Id;
}

// The catalog's parts: catalog.extra.json's first (what you made), then catalog.json's others. Sources: where each is.
TArray<TSharedPtr<FJsonObject>> CatalogParts(const FDirectoryPath& GameDirectory, TArray<FString>* Sources)
{
	TArray<TSharedPtr<FJsonObject>> Parts;
	const FString Folder = CatalogFolder(GameDirectory);
	if (Folder.IsEmpty())
	{
		return Parts;
	}
	TArray<FString> Seen;
	for (const TCHAR* File : {TEXT("catalog.extra.json"), TEXT("catalog.json")})
	{
		TSharedPtr<FJsonObject> Root;
		FString Problem;
		const FString Path = FPaths::Combine(Folder, File);
		if (!FPaths::FileExists(Path) || !ReadJson(Path, Root, Problem))
		{
			continue;
		}
		const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
		if (!Root->TryGetArrayField(TEXT("parts"), List))
		{
			continue;
		}
		for (const TSharedPtr<FJsonValue>& Value : *List)
		{
			const TSharedPtr<FJsonObject>* Entry = nullptr;
			if (!Value.IsValid() || !Value->TryGetObject(Entry))
			{
				continue;
			}
			const FString Id = IdOf(*Entry);
			if (Id.IsEmpty() || Seen.ContainsByPredicate([&](const FString& Other) { return Other.Equals(Id, ESearchCase::IgnoreCase); }))
			{
				continue;
			}
			Seen.Add(Id);
			Parts.Add(*Entry);
			if (Sources)
			{
				Sources->Add(File);
			}
		}
	}
	return Parts;
}

// In one catalog file: the entries of that id taken out, Entry (when given) put first. A file that is not there is made
// with Entry (catalog.extra.json) or left alone (catalog.json: the game's catalog maker makes it).
bool PutInFile(const FString& Path, const FString& Id, const TSharedPtr<FJsonObject>& Entry, bool bMakeIfMissing, FString& Report)
{
	TSharedPtr<FJsonObject> Root;
	FString Problem;
	if (FPaths::FileExists(Path))
	{
		if (!ReadJson(Path, Root, Problem))
		{
			Report += TEXT("    NOT changed: ") + Problem + TEXT("\n");
			return false;
		}
	}
	else if (!bMakeIfMissing || !Entry.IsValid())
	{
		return true;
	}
	else
	{
		Root = MakeShared<FJsonObject>();
	}
	TArray<TSharedPtr<FJsonValue>> Parts;
	const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
	int32 Removed = 0;
	if (Root->TryGetArrayField(TEXT("parts"), List))
	{
		for (const TSharedPtr<FJsonValue>& Value : *List)
		{
			const TSharedPtr<FJsonObject>* Other = nullptr;
			if (Value.IsValid() && Value->TryGetObject(Other) && IdOf(*Other).Equals(Id, ESearchCase::IgnoreCase))
			{
				++Removed;
				continue;
			}
			Parts.Add(Value);
		}
	}
	if (!Entry.IsValid() && Removed == 0)
	{
		return true;   // (nothing to take out)
	}
	if (Entry.IsValid())
	{
		Parts.Insert(MakeShared<FJsonValueObject>(Entry), 0);
	}
	Root->SetArrayField(TEXT("parts"), Parts);
	if (!WriteJson(Path, Root.ToSharedRef(), Problem))
	{
		Report += TEXT("    NOT changed: ") + Problem + TEXT("\n");
		return false;
	}
	Report += FString::Printf(TEXT("    %s: %s\n"), *FPaths::GetCleanFilename(Path),
		Entry.IsValid() ? (Removed > 0 ? TEXT("the part updated") : TEXT("the part added")) : TEXT("the part taken out"));
	return true;
}

// The part into catalog.extra.json (what the catalog maker merges in every time) and catalog.json (what the game reads
// as it starts), or (Entry null) out of both.
bool PutInCatalog(const FDirectoryPath& GameDirectory, const FString& Id, const TSharedPtr<FJsonObject>& Entry, FString& Report)
{
	const FString Folder = CatalogFolder(GameDirectory);
	if (Folder.IsEmpty() || !IFileManager::Get().DirectoryExists(*FPaths::GetPath(Folder)))
	{
		Report += TEXT("NOT saved: Game Directory has no Create a Character System (") + Folder + TEXT(")\n");
		return false;
	}
	IFileManager::Get().MakeDirectory(*Folder, true);
	Report += TEXT("The Customization catalog (") + Folder + TEXT("):\n");
	bool bOk = PutInFile(FPaths::Combine(Folder, TEXT("catalog.extra.json")), Id, Entry, true, Report);
	bOk &= PutInFile(FPaths::Combine(Folder, TEXT("catalog.json")), Id, Entry, false, Report);
	return bOk;
}

TArray<TSharedPtr<FJsonValue>> NumberList(std::initializer_list<double> Values)
{
	TArray<TSharedPtr<FJsonValue>> Out;
	for (const double Value : Values)
	{
		Out.Add(MakeShared<FJsonValueNumber>(Value));
	}
	return Out;
}

// The form as the game's catalog entry (Custom::ReadCatalog's fields; what is at its default left out).
TSharedRef<FJsonObject> PartToJson(const UEndPartsBuilder& Form)
{
	TSharedRef<FJsonObject> Entry = MakeShared<FJsonObject>();
	Entry->SetStringField(TEXT("id"), Form.PartId());
	Entry->SetStringField(TEXT("name"), Form.Name.TrimStartAndEnd().IsEmpty() ? Form.PartId() : Form.Name.TrimStartAndEnd());
	Entry->SetStringField(TEXT("model"), Form.Model.ToSoftObjectPath().ToString());
	Entry->SetStringField(TEXT("bone"), Form.Bone.TrimStartAndEnd());
	if (!Form.Anchor.TrimStartAndEnd().IsEmpty() && !Form.Anchor.TrimStartAndEnd().Equals(Form.Bone.TrimStartAndEnd()))
	{
		Entry->SetStringField(TEXT("anchor"), Form.Anchor.TrimStartAndEnd());
	}
	if (Form.Sections.Num() > 0)
	{
		TArray<TSharedPtr<FJsonValue>> Shown;
		for (const int32 Section : Form.Sections)
		{
			if (Section >= 0 && Section < 256)
			{
				Shown.Add(MakeShared<FJsonValueNumber>(Section));
			}
		}
		Entry->SetArrayField(TEXT("sections"), Shown);
	}
	if (!Form.Idle.IsNull())
	{
		Entry->SetStringField(TEXT("idle"), Form.Idle.ToSoftObjectPath().ToString());
	}
	if (!Form.ComponentClass.TrimStartAndEnd().IsEmpty())
	{
		Entry->SetStringField(TEXT("component_class"), Form.ComponentClass.TrimStartAndEnd());
	}
	if (Form.bSync)
	{
		const FString Folder = Form.SyncFolder.TrimStartAndEnd();
		if (Folder.IsEmpty())
		{
			Entry->SetBoolField(TEXT("sync"), true);   // (the game takes the folder two above the idle's)
		}
		else
		{
			Entry->SetStringField(TEXT("sync"), Folder);
		}
	}
	TSharedRef<FJsonObject> Moves = MakeShared<FJsonObject>();
	for (const FEndPartMove& Move : Form.Moves)
	{
		if (!Move.Ability.TrimStartAndEnd().IsEmpty() && !Move.Motion.IsNull())
		{
			Moves->SetStringField(Move.Ability.TrimStartAndEnd(), Move.Motion.ToSoftObjectPath().ToString());
		}
	}
	if (Moves->Values.Num() > 0)
	{
		Entry->SetObjectField(TEXT("moves"), Moves);
	}
	if (Form.bTint)
	{
		Entry->SetArrayField(TEXT("tint"), NumberList({Form.TintColor.R, Form.TintColor.G, Form.TintColor.B, Form.TintColor.A}));
		if (!Form.TintParameter.TrimStartAndEnd().IsEmpty() && Form.TintParameter.TrimStartAndEnd() != TEXT("Color"))
		{
			Entry->SetStringField(TEXT("tint_param"), Form.TintParameter.TrimStartAndEnd());
		}
	}
	if (!Form.TintTexture.IsNull())
	{
		Entry->SetStringField(TEXT("tint_texture"), Form.TintTexture.ToSoftObjectPath().ToString());
		Entry->SetStringField(TEXT("tint_texture_param"), Form.TintTextureParameter.TrimStartAndEnd());
	}
	if (!Form.Offset.IsNearlyZero(0.001f))
	{
		Entry->SetArrayField(TEXT("offset"), NumberList({Form.Offset.X, Form.Offset.Y, Form.Offset.Z}));
	}
	if (!FMath::IsNearlyEqual(Form.Scale, 1.f, 0.0001f))
	{
		Entry->SetNumberField(TEXT("scale"), Form.Scale);
	}
	TArray<TSharedPtr<FJsonValue>> For;
	for (const FString& Pattern : Form.For)
	{
		if (!Pattern.TrimStartAndEnd().IsEmpty())
		{
			For.Add(MakeShared<FJsonValueString>(Pattern.TrimStartAndEnd()));
		}
	}
	if (For.Num() > 0)
	{
		Entry->SetArrayField(TEXT("for"), For);
	}
	// (3.13.0) its own effects
	TArray<TSharedPtr<FJsonValue>> Effects;
	for (const FEndPartEffect& Effect : Form.Effects)
	{
		if (Effect.Effect.IsNull())
		{
			continue;
		}
		TSharedRef<FJsonObject> One = MakeShared<FJsonObject>();
		One->SetStringField(TEXT("effect"), Effect.Effect.ToString());
		if (!Effect.Socket.TrimStartAndEnd().IsEmpty())
		{
			One->SetStringField(TEXT("socket"), Effect.Socket.TrimStartAndEnd());
		}
		if (!FMath::IsNearlyEqual(Effect.Scale, 1.f, 0.0001f))
		{
			One->SetNumberField(TEXT("scale"), Effect.Scale);
		}
		Effects.Add(MakeShared<FJsonValueObject>(One));
	}
	if (Effects.Num() > 0)
	{
		Entry->SetArrayField(TEXT("effects"), Effects);
	}
	return Entry;
}

FString StringField(const TSharedPtr<FJsonObject>& Entry, const TCHAR* Field)
{
	FString Value;
	Entry->TryGetStringField(Field, Value);
	return Value.TrimStartAndEnd();
}

// A catalog entry into the form.
void PartFromJson(const TSharedPtr<FJsonObject>& Entry, UEndPartsBuilder& Form)
{
	Form.Id = IdOf(Entry);
	Form.Name = StringField(Entry, TEXT("name"));
	const FString Model = StringField(Entry, TEXT("model"));
	Form.Model = Model.IsEmpty() ? TSoftObjectPtr<USkeletalMesh>() : TSoftObjectPtr<USkeletalMesh>(FSoftObjectPath(ObjectPathOf(Model)));
	Form.Bone = StringField(Entry, TEXT("bone"));
	if (Form.Bone.IsEmpty())
	{
		Form.Bone = StringField(Entry, TEXT("socket"));
	}
	Form.Anchor = StringField(Entry, TEXT("anchor"));
	Form.Sections.Reset();
	const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
	if (Entry->TryGetArrayField(TEXT("sections"), List))
	{
		for (const TSharedPtr<FJsonValue>& Value : *List)
		{
			double Number = 0.0;
			if (Value.IsValid() && Value->TryGetNumber(Number) && Number >= 0.0 && Number < 256.0)
			{
				Form.Sections.Add(static_cast<int32>(Number));
			}
		}
	}
	const FString Idle = StringField(Entry, TEXT("idle"));
	Form.Idle = Idle.IsEmpty() ? TSoftObjectPtr<UAnimSequence>() : TSoftObjectPtr<UAnimSequence>(FSoftObjectPath(ObjectPathOf(Idle)));
	Form.ComponentClass = StringField(Entry, TEXT("component_class"));
	Form.bSync = false;
	Form.SyncFolder.Reset();
	if (const TSharedPtr<FJsonValue> Sync = Entry->TryGetField(TEXT("sync")))
	{
		bool bOn = false;
		FString Folder;
		if (Sync->TryGetBool(bOn))
		{
			Form.bSync = bOn;
		}
		else if (Sync->TryGetString(Folder) && !Folder.TrimStartAndEnd().IsEmpty())
		{
			Form.bSync = true;
			Form.SyncFolder = Folder.TrimStartAndEnd();
		}
	}
	Form.Moves.Reset();
	const TSharedPtr<FJsonObject>* Moves = nullptr;
	if (Entry->TryGetObjectField(TEXT("moves"), Moves))
	{
		for (const TPair<FString, TSharedPtr<FJsonValue>>& Pair : (*Moves)->Values)
		{
			FString Motion;
			if (Pair.Value.IsValid() && Pair.Value->TryGetString(Motion) && !Motion.IsEmpty())
			{
				FEndPartMove Move;
				Move.Ability = Pair.Key;
				Move.Motion = TSoftObjectPtr<UAnimSequence>(FSoftObjectPath(ObjectPathOf(Motion)));
				Form.Moves.Add(Move);
			}
		}
	}
	Form.bTint = false;
	Form.TintColor = FLinearColor::White;
	if (Entry->TryGetArrayField(TEXT("tint"), List) && List->Num() >= 3)
	{
		float C[4] = {1.f, 1.f, 1.f, 1.f};
		bool bNumbers = true;
		for (int32 Index = 0; Index < List->Num() && Index < 4; ++Index)
		{
			double Number = 0.0;
			bNumbers &= (*List)[Index].IsValid() && (*List)[Index]->TryGetNumber(Number);
			C[Index] = static_cast<float>(Number);
		}
		if (bNumbers)
		{
			Form.bTint = true;
			Form.TintColor = FLinearColor(C[0], C[1], C[2], C[3]);
		}
	}
	const FString Param = StringField(Entry, TEXT("tint_param"));
	Form.TintParameter = Param.IsEmpty() ? TEXT("Color") : Param;
	const FString Texture = StringField(Entry, TEXT("tint_texture"));
	Form.TintTexture = Texture.IsEmpty() ? TSoftObjectPtr<UTexture>() : TSoftObjectPtr<UTexture>(FSoftObjectPath(ObjectPathOf(Texture)));
	Form.TintTextureParameter = StringField(Entry, TEXT("tint_texture_param"));
	Form.Offset = FVector::ZeroVector;
	if (Entry->TryGetArrayField(TEXT("offset"), List) && List->Num() == 3)
	{
		double X = 0.0, Y = 0.0, Z = 0.0;
		(*List)[0]->TryGetNumber(X);
		(*List)[1]->TryGetNumber(Y);
		(*List)[2]->TryGetNumber(Z);
		Form.Offset = FVector(static_cast<float>(X), static_cast<float>(Y), static_cast<float>(Z));
	}
	double Size = 1.0;
	Form.Scale = Entry->TryGetNumberField(TEXT("scale"), Size) && Size > 0.01 && Size < 100.0 ? static_cast<float>(Size) : 1.f;
	// (3.13.0) its own effects: [{"effect", "socket", "scale"}] (or paths)
	Form.Effects.Reset();
	if (Entry->TryGetArrayField(TEXT("effects"), List))
	{
		for (const TSharedPtr<FJsonValue>& Value : *List)
		{
			if (!Value.IsValid())
			{
				continue;
			}
			FEndPartEffect Effect;
			FString Path;
			const TSharedPtr<FJsonObject>* One = nullptr;
			if (Value->TryGetString(Path))
			{
				Effect.Effect = FSoftObjectPath(ObjectPathOf(Path.TrimStartAndEnd()));
			}
			else if (Value->TryGetObject(One) && One && One->IsValid())
			{
				Path = StringField(*One, TEXT("effect"));
				if (Path.IsEmpty())
				{
					Path = StringField(*One, TEXT("path"));
				}
				Effect.Effect = Path.IsEmpty() ? FSoftObjectPath() : FSoftObjectPath(ObjectPathOf(Path));
				Effect.Socket = StringField(*One, TEXT("socket"));
				double EffectSize = 1.0;
				Effect.Scale = (*One)->TryGetNumberField(TEXT("scale"), EffectSize) && EffectSize > 0.01 && EffectSize < 100.0 ? static_cast<float>(EffectSize) : 1.f;
			}
			if (!Effect.Effect.IsNull())
			{
				Form.Effects.Add(Effect);
			}
		}
	}
	Form.For.Reset();
	if (Entry->TryGetArrayField(TEXT("for"), List))
	{
		for (const TSharedPtr<FJsonValue>& Value : *List)
		{
			FString Pattern;
			if (Value.IsValid() && Value->TryGetString(Pattern) && !Pattern.TrimStartAndEnd().IsEmpty())
			{
				Form.For.Add(Pattern.TrimStartAndEnd());
			}
		}
	}
	Form.AddFor.Reset();
	Form.PickBone.Reset();
	Form.PickAnchor.Reset();
	Form.PreviewMove.Reset();
}

// The motion a synced part plays while the character plays Playing (the game's PartMotion): <root>/<its folder and
// name>, else <root>/<a set folder>/<its name>. Empty: none in this project.
FString SyncedMotion(const FString& Root, const UAnimSequence* Playing)
{
	if (Root.IsEmpty() || !Playing)
	{
		return FString();
	}
	const FString Name = Playing->GetName();
	TArray<FString> Paths;
	const FString Rel = RelOf(Playing->GetPathName());
	if (!Rel.IsEmpty())
	{
		Paths.Add(Root + TEXT("/") + Rel + TEXT(".") + Name);
	}
	for (const TCHAR* Folder : SyncFolders)
	{
		Paths.AddUnique(Root + TEXT("/") + Folder + TEXT("/") + Name + TEXT(".") + Name);
	}
	for (const FString& Path : Paths)
	{
		if (Registry().GetAssetByObjectPath(FName(*Path)).IsValid())
		{
			return Path;
		}
	}
	return FString();
}

// An asset Build Part builds: one of this project (not a cooked copy of a game asset, not one the game has).
bool IsOwnAsset(const FSoftObjectPath& Path)
{
	if (Path.IsNull() || !Path.GetLongPackageName().StartsWith(TEXT("/Game/")))
	{
		return false;
	}
	const FAssetData Asset = Registry().GetAssetByObjectPath(FName(*Path.ToString()));
	if (Asset.IsValid() && (Asset.PackageFlags & PKG_Cooked) != 0)
	{
		return false;   // (a cooked copy: the game's own, or one that cannot be cooked again)
	}
	return !RebirthSkelCompatSkins::IsGamePackage(Path.GetLongPackageName());
}

// The animations of this project under a folder (for a synced part's build), not loaded.
TArray<FSoftObjectPath> AnimationsUnder(const FString& Folder)
{
	TArray<FSoftObjectPath> Out;
	if (Folder.IsEmpty() || !Folder.StartsWith(TEXT("/Game/")))
	{
		return Out;
	}
	TArray<FAssetData> Assets;
	Registry().GetAssetsByPath(FName(*Folder), Assets, true);
	for (const FAssetData& Asset : Assets)
	{
		if (Asset.AssetClass == UAnimSequence::StaticClass()->GetFName() && (Asset.PackageFlags & PKG_Cooked) == 0)
		{
			Out.Add(Asset.ToSoftObjectPath());
		}
	}
	return Out;
}
} // namespace RebirthPartsUtil

// ------------------------------------------------------------------------------------------------
// The form
// ------------------------------------------------------------------------------------------------
const TCHAR* UEndPartsBuilder::NewPartLabel() { return TEXT("(new part)"); }

FString UEndPartsBuilder::PartId() const
{
	const FString Mine = Id.TrimStartAndEnd();
	return Mine.IsEmpty() ? RebirthPartsUtil::IdFromName(Name) : Mine;
}

FString UEndPartsBuilder::AnchorName() const
{
	const FString Mine = Anchor.TrimStartAndEnd();
	return Mine.IsEmpty() ? Bone.TrimStartAndEnd() : Mine;
}

FString UEndPartsBuilder::SyncRoot() const
{
	FString Folder = SyncFolder.TrimStartAndEnd();
	if (Folder.IsEmpty() && !Idle.IsNull())
	{
		// (the game's: two folders above the idle's package)
		Folder = FPackageName::ObjectPathToPackageName(Idle.ToSoftObjectPath().ToString());
		for (int32 Up = 0; Up < 2; ++Up)
		{
			int32 Slash = INDEX_NONE;
			if (!Folder.FindLastChar(TEXT('/'), Slash))
			{
				break;
			}
			Folder = Folder.Left(Slash);
		}
	}
	while (Folder.EndsWith(TEXT("/")))
	{
		Folder.LeftChopInline(1);
	}
	return Folder;
}

FString UEndPartsBuilder::AssetsFolderName() const
{
	const FString Mine = AssetsFolder.TrimStartAndEnd();
	if (!Mine.IsEmpty())
	{
		return Mine;
	}
	FString Folder = TEXT("Part_");
	for (const TCHAR C : PartId())
	{
		Folder.AppendChar(FChar::IsAlnum(C) || C == TEXT('-') ? C : TEXT('_'));
	}
	return Folder.Left(64);
}

TArray<FString> UEndPartsBuilder::GetPartOptions() const
{
	TArray<FString> Options;
	Options.Add(NewPartLabel());
	TArray<FString> Sources;
	const TArray<TSharedPtr<FJsonObject>> Parts = RebirthPartsUtil::CatalogParts(GameDirectory, &Sources);
	for (int32 Index = 0; Index < Parts.Num(); ++Index)
	{
		const FString Shown = RebirthPartsUtil::StringField(Parts[Index], TEXT("name"));
		Options.Add(FString::Printf(TEXT("%s: %s   [%s]"), *RebirthPartsUtil::IdOf(Parts[Index]), Shown.IsEmpty() ? TEXT("no name") : *Shown, *Sources[Index]));
	}
	return Options;
}

TArray<FString> UEndPartsBuilder::GetForOptions() const
{
	TArray<FString> Options;
	if (!PreviewCharacter.IsNull())
	{
		const FString Leaf = FPackageName::GetShortName(PreviewCharacter.ToSoftObjectPath().GetLongPackageName());
		int32 Cut = INDEX_NONE;
		if (Leaf.FindChar(TEXT('_'), Cut) && Cut > 0)
		{
			Options.Add(Leaf.Left(Cut + 1) + TEXT("*"));   // PC0010_* (every model of that character)
		}
		Options.Add(Leaf);
		Options.Add(PreviewCharacter.ToSoftObjectPath().ToString());
	}
	if (!Model.IsNull())
	{
		const FString Leaf = FPackageName::GetShortName(Model.ToSoftObjectPath().GetLongPackageName());
		int32 Cut = INDEX_NONE;
		if (Leaf.FindChar(TEXT('_'), Cut) && Cut > 0)
		{
			Options.AddUnique(Leaf.Left(Cut + 1) + TEXT("*"));
		}
	}
	return Options;
}

TArray<FString> UEndPartsBuilder::GetBoneOptions() const
{
	TArray<FString> Options;
	USkeletalMesh* Character = PreviewCharacter.LoadSynchronous();
	if (!Character)
	{
		return Options;
	}
	for (int32 Bone2 = 0; Bone2 < Character->RefSkeleton.GetNum(); ++Bone2)
	{
		Options.Add(Character->RefSkeleton.GetBoneName(Bone2).ToString());
	}
	TArray<USkeletalMeshSocket*> Sockets = Character->GetActiveSocketList();
	for (const USkeletalMeshSocket* Socket : Sockets)
	{
		if (Socket)
		{
			Options.AddUnique(Socket->SocketName.ToString());
		}
	}
	return Options;
}

TArray<FString> UEndPartsBuilder::GetAnchorOptions() const
{
	TArray<FString> Options;
	Options.Add(RebirthPartsUtil::SameAsBone);
	if (USkeletalMesh* Mesh = Model.LoadSynchronous())
	{
		for (int32 Index = 0; Index < Mesh->RefSkeleton.GetNum(); ++Index)
		{
			Options.Add(Mesh->RefSkeleton.GetBoneName(Index).ToString());
		}
	}
	return Options;
}

TArray<FString> UEndPartsBuilder::GetPreviewMoveOptions() const
{
	TArray<FString> Options;
	Options.Add(RebirthPartsUtil::NoMove);
	for (const FEndPartMove& Move : Moves)
	{
		if (!Move.Ability.TrimStartAndEnd().IsEmpty())
		{
			Options.AddUnique(Move.Ability.TrimStartAndEnd());
		}
	}
	return Options;
}

bool UEndPartsBuilder::TakePickers()
{
	bool bChanged = false;
	if (!AddFor.TrimStartAndEnd().IsEmpty())
	{
		For.AddUnique(AddFor.TrimStartAndEnd());
		AddFor.Reset();
		bChanged = true;
	}
	if (!PickBone.TrimStartAndEnd().IsEmpty())
	{
		Bone = PickBone.TrimStartAndEnd();
		PickBone.Reset();
		bChanged = true;
	}
	if (!PickAnchor.TrimStartAndEnd().IsEmpty())
	{
		Anchor = PickAnchor.StartsWith(TEXT("(")) ? FString() : PickAnchor.TrimStartAndEnd();
		PickAnchor.Reset();
		bChanged = true;
	}
	if (PreviewMove.StartsWith(TEXT("(")))
	{
		PreviewMove.Reset();
		bChanged = true;
	}
	return bChanged;
}

void UEndPartsBuilder::StartFrom(USkeletalMesh* InModel)
{
	const FDirectoryPath Game = GameDirectory;
	const TSoftObjectPtr<USkeletalMesh> Character = PreviewCharacter;
	const TSoftObjectPtr<UAnimSequence> Playing = PreviewAnimation;
	const float Speed = PreviewSpeed;
	// every field to its default, but the preview and the game folder
	Name.Reset();
	Id.Reset();
	Model = InModel;
	For.Reset();
	AddFor.Reset();
	Bone.Reset();
	PickBone.Reset();
	Anchor.Reset();
	PickAnchor.Reset();
	Offset = FVector::ZeroVector;
	Scale = 1.f;
	Sections.Reset();
	Idle.Reset();
	bSync = false;
	SyncFolder.Reset();
	Moves.Reset();
	bTint = false;
	TintColor = FLinearColor::White;
	TintParameter = TEXT("Color");
	TintTexture.Reset();
	TintTextureParameter.Reset();
	Effects.Reset();   // (3.13.0)
	ComponentClass.Reset();
	PreviewMove.Reset();
	AssetsFolder.Reset();
	Part = NewPartLabel();
	GameDirectory = Game;
	PreviewCharacter = Character;
	PreviewAnimation = Playing;
	PreviewSpeed = Speed;
	if (InModel)
	{
		Name = InModel->GetName().Replace(TEXT("_"), TEXT(" "));
		// a model of a character's own skeleton lines up bone for bone on the root: its bones are the character's
		if (USkeletalMesh* On = PreviewCharacter.LoadSynchronous(); On && On->Skeleton == InModel->Skeleton && InModel->RefSkeleton.GetNum() > 1)
		{
			Bone = InModel->RefSkeleton.GetBoneName(1).ToString();
		}
	}
}

void UEndPartsBuilder::Describe()
{
	TArray<FString> Lines;
	const FString MyId = PartId();
	Lines.Add(MyId.IsEmpty() ? FString(TEXT("Id: give the part a Name (or an Id)"))
			  : RebirthPartsUtil::ValidId(MyId) ? TEXT("Id: ") + MyId
												: TEXT("Id: \"") + MyId + TEXT("\" is not 1-64 letters, digits, _ or -: change the Id"));
	USkeletalMesh* Mesh = Model.LoadSynchronous();
	USkeletalMesh* Character = PreviewCharacter.LoadSynchronous();
	if (!Mesh)
	{
		Lines.Add(Model.IsNull() ? FString(TEXT("Model: pick the part's model (or right-click a Skeletal Mesh > Make a Customization Part...)")) : TEXT("Model: ") + Model.ToString() + TEXT(" does not load"));
	}
	else
	{
		TArray<FString> Slots;
		for (int32 Slot = 0; Slot < Mesh->Materials.Num(); ++Slot)
		{
			const FName SlotName = Mesh->Materials[Slot].MaterialSlotName;
			Slots.Add(FString::Printf(TEXT("%d %s"), Slot, SlotName.IsNone() ? TEXT("") : *SlotName.ToString()));
		}
		Lines.Add(FString::Printf(TEXT("Model: %s, %d bones, skeleton %s"), *Mesh->GetName(), Mesh->RefSkeleton.GetNum(), Mesh->Skeleton ? *Mesh->Skeleton->GetName() : TEXT("none")));
		Lines.Add(TEXT("    its sections (Sections): ") + FString::Join(Slots, TEXT(", ")));
		const FString Own = AnchorName();
		if (!Own.IsEmpty())
		{
			Lines.Add(Mesh->RefSkeleton.FindBoneIndex(FName(*Own)) != INDEX_NONE ? TEXT("    Anchor: its bone ") + Own + TEXT(" is kept on the character's ") + Bone.TrimStartAndEnd()
																				: TEXT("    Anchor: it has no bone ") + Own + TEXT(": its root goes on the character's bone"));
		}
	}
	const FString OnBone = Bone.TrimStartAndEnd();
	if (!Character)
	{
		Lines.Add(TEXT("Preview: pick a Preview Character (a model of a character the part is for) to see it on one"));
	}
	else if (OnBone.IsEmpty())
	{
		Lines.Add(TEXT("Bone: pick the character's bone it goes on (Pick Bone)"));
	}
	else
	{
		const bool bBone = Character->RefSkeleton.FindBoneIndex(FName(*OnBone)) != INDEX_NONE;
		const bool bSocket = Character->FindSocket(FName(*OnBone)) != nullptr;
		Lines.Add(bBone || bSocket ? FString::Printf(TEXT("Bone: %s, a %s of %s"), *OnBone, bSocket ? TEXT("socket") : TEXT("bone"), *Character->GetName())
								   : FString::Printf(TEXT("Bone: %s has no bone or socket %s: in game the part goes on the character's root"), *Character->GetName(), *OnBone));
	}
	if (UAnimSequence* Loop = Idle.LoadSynchronous())
	{
		const bool bSame = Mesh && Loop->GetSkeleton() == Mesh->Skeleton;
		Lines.Add(FString::Printf(TEXT("Idle: %s (%.2f s)%s"), *Loop->GetName(), Loop->SequenceLength,
			bSame || !Mesh ? TEXT("") : *FString::Printf(TEXT(": an animation of %s, not of the part's skeleton"), Loop->GetSkeleton() ? *Loop->GetSkeleton()->GetName() : TEXT("none"))));
	}
	if (bSync)
	{
		const FString Root = SyncRoot();
		UAnimSequence* Playing = PreviewAnimation.LoadSynchronous();
		const FString Found = RebirthPartsUtil::SyncedMotion(Root, Playing);
		Lines.Add(Root.IsEmpty() ? FString(TEXT("Sync: no folder: set Sync Folder (or an Idle: the folder two above its)"))
								 : TEXT("Sync: its motions of the character's names from ") + Root +
									   (Playing ? (Found.IsEmpty() ? TEXT(" (none of ") + Playing->GetName() + TEXT(": its idle)") : TEXT(" (now ") + RebirthPartsUtil::RelOf(Found) + TEXT(")")) : FString()));
	}
	if (Moves.Num() > 0)
	{
		Lines.Add(FString::Printf(TEXT("%d move(s) for abilities"), Moves.Num()));
	}
	const FString Folder = RebirthPartsUtil::CatalogFolder(GameDirectory);
	Lines.Add(Folder.IsEmpty() ? FString(TEXT("Game Directory: set it (the catalog is in its Create a Character System folder)"))
							   : TEXT("Catalog: ") + FPaths::Combine(Folder, TEXT("catalog.extra.json")) + TEXT(" and catalog.json; its own assets: skins\\") + AssetsFolderName());
	About = FString::Join(Lines, TEXT("\n"));
}

// ------------------------------------------------------------------------------------------------
// The preview
// ------------------------------------------------------------------------------------------------
class FEndPartsViewportClient : public FEditorViewportClient
{
public:
	FEndPartsViewportClient(FPreviewScene& InScene, const TSharedRef<SEditorViewport>& InWidget)
		: FEditorViewportClient(nullptr, &InScene, StaticCastSharedRef<SEditorViewport>(InWidget))
	{
		SetRealtime(true);
		bSetListenerPosition = false;
		EngineShowFlags.SetGrid(false);
		SetViewLocation(FVector(260.f, 160.f, 120.f));
		SetViewRotation(FRotator(-10.f, -150.f, 0.f));
	}

	TFunction<void(float)> OnTicked;
	TFunction<void(FPrimitiveDrawInterface*)> OnDraw;

	virtual void Tick(float DeltaSeconds) override
	{
		FEditorViewportClient::Tick(DeltaSeconds);
		if (!GIntraFrameDebuggingGameThread && PreviewScene && PreviewScene->GetWorld())
		{
			PreviewScene->GetWorld()->Tick(LEVELTICK_All, DeltaSeconds);
		}
		if (OnTicked)
		{
			OnTicked(DeltaSeconds);
		}
	}

	virtual void Draw(const FSceneView* View, FPrimitiveDrawInterface* PDI) override
	{
		FEditorViewportClient::Draw(View, PDI);
		if (OnDraw)
		{
			OnDraw(PDI);
		}
	}

	virtual FLinearColor GetBackgroundColor() const override { return FLinearColor(0.018f, 0.022f, 0.035f); }
};

class SEndPartsViewport : public SEditorViewport
{
public:
	SLATE_BEGIN_ARGS(SEndPartsViewport) {}
	SLATE_END_ARGS()

	SEndPartsViewport() : Scene(FPreviewScene::ConstructionValues()) {}

	virtual ~SEndPartsViewport() override
	{
		if (PartsClient.IsValid())
		{
			PartsClient->OnTicked = nullptr;
			PartsClient->OnDraw = nullptr;
			PartsClient->Viewport = nullptr;
		}
	}

	void Construct(const FArguments& InArgs)
	{
		SEditorViewport::Construct(SEditorViewport::FArguments());
	}

	/** Shows the form's part on its preview character (made anew). Returns a line about what it plays. */
	FString Show(const UEndPartsBuilder& Form)
	{
		Clear();
		FString Said;
		USkeletalMesh* CharacterMesh = Form.PreviewCharacter.LoadSynchronous();
		USkeletalMesh* PartMesh = Form.Model.LoadSynchronous();
		Speed = Form.PreviewSpeed;
		Anchor = FName(*Form.AnchorName());
		BoneName = FName(*Form.Bone.TrimStartAndEnd());
		Offset = Form.Offset;
		Size = Form.Scale;
		if (CharacterMesh)
		{
			Character = MakeComponent(CharacterMesh);
			if (UAnimSequence* Playing = Form.PreviewAnimation.LoadSynchronous())
			{
				Character->PlayAnimation(Playing, true);
				Character->SetPlayRate(bPaused ? 0.f : Speed);
				Said += TEXT("The character plays ") + Playing->GetName() + TEXT(". ");
			}
		}
		if (PartMesh)
		{
			Part = MakeComponent(PartMesh);
			if (Character)
			{
				Part->AttachToComponent(Character, FAttachmentTransformRules::SnapToTargetIncludingScale, BoneName);
			}
			// sections
			if (Form.Sections.Num() > 0)
			{
				for (int32 Lod = 0; Lod < PartMesh->GetLODNum(); ++Lod)
				{
					for (int32 Slot = 0; Slot < PartMesh->Materials.Num(); ++Slot)
					{
						if (!Form.Sections.Contains(Slot))
						{
							Part->ShowMaterialSection(Slot, -1, false, Lod);
						}
					}
				}
			}
			// the tint
			UTexture* Texture = Form.TintTexture.LoadSynchronous();
			if (Form.bTint || Texture)
			{
				for (int32 Slot = 0; Slot < PartMesh->Materials.Num(); ++Slot)
				{
					if (Form.Sections.Num() > 0 && !Form.Sections.Contains(Slot))
					{
						continue;
					}
					UMaterialInstanceDynamic* Mid = Part->CreateDynamicMaterialInstance(Slot);
					if (!Mid)
					{
						continue;
					}
					if (Form.bTint)
					{
						Mid->SetVectorParameterValue(FName(*Form.TintParameter.TrimStartAndEnd()), Form.TintColor);
					}
					if (Texture && !Form.TintTextureParameter.TrimStartAndEnd().IsEmpty())
					{
						Mid->SetTextureParameterValue(FName(*Form.TintTextureParameter.TrimStartAndEnd()), Texture);
					}
				}
			}
			// what it plays: synced, else the move picked, else its idle
			FString Motion;
			bFollow = false;
			if (Form.bSync)
			{
				Motion = RebirthPartsUtil::SyncedMotion(Form.SyncRoot(), Form.PreviewAnimation.LoadSynchronous());
				bFollow = !Motion.IsEmpty() && Character && Character->GetAnimationMode() == EAnimationMode::AnimationSingleNode;
			}
			if (Motion.IsEmpty() && !Form.PreviewMove.IsEmpty())
			{
				for (const FEndPartMove& Move : Form.Moves)
				{
					if (Move.Ability.TrimStartAndEnd().Equals(Form.PreviewMove, ESearchCase::IgnoreCase) && !Move.Motion.IsNull())
					{
						Motion = Move.Motion.ToSoftObjectPath().ToString();
						break;
					}
				}
			}
			if (Motion.IsEmpty() && !Form.Idle.IsNull())
			{
				Motion = Form.Idle.ToSoftObjectPath().ToString();
			}
			if (UAnimSequence* Own = RebirthPartsUtil::LoadIfThere<UAnimSequence>(Motion))
			{
				Part->PlayAnimation(Own, true);
				Part->SetPlayRate(bFollow || bPaused ? 0.f : Speed);
				Said += TEXT("The part plays ") + Own->GetName() + (bFollow ? TEXT(" in step with it.") : TEXT("."));
			}
			else if (!Motion.IsEmpty())
			{
				Said += TEXT("The part's motion ") + Motion + TEXT(" is not in this project.");
			}
			Align();
		}
		if (bFrameNext && (Character || Part))
		{
			Frame();
			bFrameNext = false;
		}
		return Said;
	}

	void Frame()
	{
		USkeletalMeshComponent* Subject = Character ? Character : Part;
		if (Subject && PartsClient.IsValid())
		{
			Subject->UpdateBounds();
			PartsClient->FocusViewportOnBox(Subject->Bounds.GetBox(), true);
		}
	}

	bool TogglePause()
	{
		bPaused = !bPaused;
		if (Character)
		{
			Character->SetPlayRate(bPaused ? 0.f : Speed);
		}
		if (Part)
		{
			Part->SetPlayRate(bPaused || bFollow ? 0.f : Speed);
		}
		return bPaused;
	}

	void Restart()
	{
		if (Character)
		{
			Character->SetPosition(0.f, false);
		}
		if (Part)
		{
			Part->SetPosition(0.f, false);
		}
	}

protected:
	virtual TSharedRef<FEditorViewportClient> MakeEditorViewportClient() override
	{
		PartsClient = MakeShareable(new FEndPartsViewportClient(Scene, SharedThis(this)));
		PartsClient->OnTicked = [this](float) { Follow(); Align(); };
		PartsClient->OnDraw = [this](FPrimitiveDrawInterface* PDI) { DrawMarks(PDI); };
		return PartsClient.ToSharedRef();
	}

private:
	FPreviewScene Scene;
	TSharedPtr<FEndPartsViewportClient> PartsClient;
	USkeletalMeshComponent* Character = nullptr;   // (the scene keeps them: FPreviewScene's components are referenced)
	USkeletalMeshComponent* Part = nullptr;
	FName Anchor;
	FName BoneName;
	FVector Offset = FVector::ZeroVector;
	float Size = 1.f;
	float Speed = 1.f;
	bool bFollow = false;
	bool bPaused = false;
	bool bFrameNext = true;

	USkeletalMeshComponent* MakeComponent(USkeletalMesh* Mesh)
	{
		USkeletalMeshComponent* Component = NewObject<USkeletalMeshComponent>(GetTransientPackage(), NAME_None, RF_Transient);
		Component->SetSkeletalMesh(Mesh);
		Component->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
		Component->SetAnimationMode(EAnimationMode::AnimationSingleNode);
		Scene.AddComponent(Component, FTransform::Identity);
		return Component;
	}

	void Clear()
	{
		for (USkeletalMeshComponent* Component : {Part, Character})
		{
			if (Component)
			{
				Scene.RemoveComponent(Component);
			}
		}
		Part = nullptr;
		Character = nullptr;
	}

	// (the game's sync) the part's motion where the character's is
	void Follow()
	{
		if (bFollow && Part && Character)
		{
			Part->SetPosition(Character->GetPosition(), false);
		}
	}

	// (the game's Align) the part's anchor kept on the character's bone, then Offset and Scale
	void Align()
	{
		if (!Part || !Character || Anchor.IsNone())
		{
			return;
		}
		const FTransform Own = Part->GetSocketTransform(Anchor, RTS_Component);
		const FQuat Back = Own.GetRotation().Inverse();
		const FVector Place = -Back.RotateVector(Own.GetTranslation()) * Size + Offset;
		Part->SetRelativeTransform(FTransform(Back, Place, FVector(Size)));
	}

	void DrawMarks(FPrimitiveDrawInterface* PDI)
	{
		if (Character && !BoneName.IsNone())
		{
			DrawWireSphere(PDI, Character->GetSocketLocation(BoneName), FLinearColor(1.f, 0.8f, 0.1f), 2.5f, 12, SDPG_Foreground);
		}
		if (Part && !Anchor.IsNone() && Part->GetBoneIndex(Anchor) != INDEX_NONE)
		{
			DrawWireSphere(PDI, Part->GetSocketLocation(Anchor), FLinearColor(0.2f, 0.85f, 1.f), 1.5f, 12, SDPG_Foreground);
		}
	}
};

// ------------------------------------------------------------------------------------------------
// The window
// ------------------------------------------------------------------------------------------------
class SEndPartsBuilder : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SEndPartsBuilder) {}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs)
	{
		Form.Reset(NewObject<UEndPartsBuilder>(GetTransientPackage(), NAME_None, RF_Transient));
		Form->Part = UEndPartsBuilder::NewPartLabel();
		LoadSettings();
		FPropertyEditorModule& PropertyEditor = FModuleManager::LoadModuleChecked<FPropertyEditorModule>(TEXT("PropertyEditor"));
		FDetailsViewArgs Args;
		Args.bAllowSearch = false;
		Args.bHideSelectionTip = true;
		Args.NameAreaSettings = FDetailsViewArgs::HideNameArea;
		Details = PropertyEditor.CreateDetailView(Args);
		Details->SetObject(Form.Get());
		Details->OnFinishedChangingProperties().AddSP(this, &SEndPartsBuilder::OnFormChanged);
		Report = LOCTEXT("Start", "Pick the part's model (or right-click a Skeletal Mesh > Make a Customization Part...), a Preview Character to see it on, the bone it goes on and its idle. Save Part puts it in the game's Customization catalog; Build Part also builds its own assets of this project into the game.");

		ChildSlot
		[
			SNew(SSplitter)
			+ SSplitter::Slot()
			.Value(0.44f)
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot()
				.FillHeight(1.f)
				[
					Details.ToSharedRef()
				]
				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(4.f)
				[
					SNew(SWrapBox)
					.UseAllottedWidth(true)
					+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("Load", "Load Part"), LOCTEXT("LoadTip", "Fill the form from the catalog's part picked in Part (picking one does it too)."), &SEndPartsBuilder::OnLoad)]
					+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("New", "New Part"), LOCTEXT("NewTip", "Start a new part of the model in the form."), &SEndPartsBuilder::OnNew)]
					+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("Save", "Save Part"), LOCTEXT("SaveTip", "Put the part in the game's Customization catalog (catalog.extra.json, and catalog.json the game reads as it starts)."), &SEndPartsBuilder::OnSave)]
					+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("Build", "Build Part"), LOCTEXT("BuildTip", "Build the part's own assets of this project (its model, its animations) into the game's skins container, then Save Part. Close the game first."), &SEndPartsBuilder::OnBuild)]
					+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("Remove", "Remove Part"), LOCTEXT("RemoveTip", "Take the part of this id out of the game's Customization catalog."), &SEndPartsBuilder::OnRemove)]
					+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("OpenModel", "Open Model"), LOCTEXT("OpenModelTip", "Open the part's model in the mesh editor."), &SEndPartsBuilder::OnOpenModel)]
					+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("OpenIdle", "Open Idle"), LOCTEXT("OpenIdleTip", "Open the part's idle in the animation editor."), &SEndPartsBuilder::OnOpenIdle)]
				]
				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(4.f)
				[
					SNew(SBox)
					.HeightOverride(190.f)
					[
						SNew(SMultiLineEditableTextBox)
						.IsReadOnly(true)
						.AutoWrapText(true)
						.Text(this, &SEndPartsBuilder::GetReport)
					]
				]
			]
			+ SSplitter::Slot()
			.Value(0.56f)
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot()
				.FillHeight(1.f)
				[
					SAssignNew(Viewport, SEndPartsViewport)
				]
				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(4.f)
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)[MakeButton(LOCTEXT("Pause", "Play / Pause"), LOCTEXT("PauseTip", "Stop or go on playing the preview."), &SEndPartsBuilder::OnPause)]
					+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)[MakeButton(LOCTEXT("Restart", "Restart"), LOCTEXT("RestartTip", "Play the preview from its start."), &SEndPartsBuilder::OnRestart)]
					+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)[MakeButton(LOCTEXT("Frame", "Frame"), LOCTEXT("FrameTip", "Bring the camera to the character."), &SEndPartsBuilder::OnFrame)]
					+ SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center).Padding(6.f, 2.f)
					[
						SNew(STextBlock)
						.Text(this, &SEndPartsBuilder::GetPlaying)
						.AutoWrapText(true)
					]
				]
			]
		];
		ShowPreview();
	}

	void Open(USkeletalMesh* Mesh)
	{
		if (Mesh && Form.IsValid())
		{
			Form->StartFrom(Mesh);
			SetReport(FString::Printf(TEXT("A new part of %s: pick the bone it goes on (Pick Bone) and its idle, see it in the preview, then Save Part (or Build Part when its model or animations are this project's)."), *Mesh->GetName()));
			ShowPreview();
		}
	}

private:
	TStrongObjectPtr<UEndPartsBuilder> Form;
	TSharedPtr<IDetailsView> Details;
	TSharedPtr<SEndPartsViewport> Viewport;
	FText Report;
	FText Playing;

	TSharedRef<SWidget> MakeButton(const FText& Label, const FText& Tip, FReply (SEndPartsBuilder::*Handler)())
	{
		return SNew(SButton).Text(Label).ToolTipText(Tip).OnClicked(this, Handler);
	}

	FText GetReport() const { return Report; }
	FText GetPlaying() const { return Playing; }
	void SetReport(const FString& Text) { Report = FText::FromString(Text); }

	void LoadSettings()
	{
		FString Text;
		Form->GameDirectory.Path = GConfig && GConfig->GetString(RebirthPartsUtil::ConfigSection, TEXT("GameDirectory"), Text, GEditorPerProjectIni) && !Text.IsEmpty()
									   ? Text
									   : FString(TEXT("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII REBIRTH"));
		if (GConfig && GConfig->GetString(RebirthPartsUtil::ConfigSection, TEXT("PreviewCharacter"), Text, GEditorPerProjectIni) && !Text.IsEmpty())
		{
			Form->PreviewCharacter = TSoftObjectPtr<USkeletalMesh>(FSoftObjectPath(Text));
		}
		if (GConfig && GConfig->GetString(RebirthPartsUtil::ConfigSection, TEXT("PreviewAnimation"), Text, GEditorPerProjectIni) && !Text.IsEmpty())
		{
			Form->PreviewAnimation = TSoftObjectPtr<UAnimSequence>(FSoftObjectPath(Text));
		}
	}

	void SaveSettings()
	{
		if (!GConfig)
		{
			return;
		}
		GConfig->SetString(RebirthPartsUtil::ConfigSection, TEXT("GameDirectory"), *Form->GameDirectory.Path, GEditorPerProjectIni);
		GConfig->SetString(RebirthPartsUtil::ConfigSection, TEXT("PreviewCharacter"), *Form->PreviewCharacter.ToSoftObjectPath().ToString(), GEditorPerProjectIni);
		GConfig->SetString(RebirthPartsUtil::ConfigSection, TEXT("PreviewAnimation"), *Form->PreviewAnimation.ToSoftObjectPath().ToString(), GEditorPerProjectIni);
	}

	void ShowPreview()
	{
		Form->Describe();
		if (Details.IsValid())
		{
			Details->ForceRefresh();
		}
		if (Viewport.IsValid())
		{
			const FString Line = Viewport->Show(*Form);
			Playing = FText::FromString(Line);
		}
	}

	bool LoadPicked()
	{
		FString Left;
		if (!Form->Part.Split(TEXT(":"), &Left, nullptr))
		{
			return false;
		}
		const FString Wanted = Left.TrimStartAndEnd();
		for (const TSharedPtr<FJsonObject>& Entry : RebirthPartsUtil::CatalogParts(Form->GameDirectory, nullptr))
		{
			if (RebirthPartsUtil::IdOf(Entry).Equals(Wanted, ESearchCase::IgnoreCase))
			{
				RebirthPartsUtil::PartFromJson(Entry, *Form);
				return true;
			}
		}
		return false;
	}

	void OnFormChanged(const FPropertyChangedEvent& Event)
	{
		const FName Member = Event.MemberProperty ? Event.MemberProperty->GetFName() : Event.GetPropertyName();
		if (Member == GET_MEMBER_NAME_CHECKED(UEndPartsBuilder, Part) && LoadPicked())
		{
			SetReport(FString::Printf(TEXT("Loaded the catalog's part %s."), *Form->PartId()));
		}
		Form->TakePickers();
		if (Member == GET_MEMBER_NAME_CHECKED(UEndPartsBuilder, GameDirectory) || Member == GET_MEMBER_NAME_CHECKED(UEndPartsBuilder, PreviewCharacter) ||
			Member == GET_MEMBER_NAME_CHECKED(UEndPartsBuilder, PreviewAnimation))
		{
			SaveSettings();
		}
		ShowPreview();
	}

	FReply OnLoad()
	{
		SetReport(LoadPicked() ? FString::Printf(TEXT("Loaded the catalog's part %s."), *Form->PartId())
							   : FString(TEXT("Pick one of the catalog's parts in Part first (Game Directory has to be set).")));
		ShowPreview();
		return FReply::Handled();
	}

	FReply OnNew()
	{
		Form->StartFrom(Form->Model.LoadSynchronous());
		SetReport(TEXT("A new part."));
		ShowPreview();
		return FReply::Handled();
	}

	bool Ready(FString& OutProblem) const
	{
		const FString MyId = Form->PartId();
		if (Form->Model.IsNull())
		{
			OutProblem = TEXT("Pick the part's model first (Model).");
		}
		else if (!RebirthPartsUtil::ValidId(MyId))
		{
			OutProblem = TEXT("Give the part a Name (its id is made from it) or an Id of 1-64 letters, digits, _ or -.");
		}
		else if (Form->Bone.TrimStartAndEnd().IsEmpty())
		{
			OutProblem = TEXT("Pick the bone the part goes on (Bone).");
		}
		else if (RebirthPartsUtil::CatalogFolder(Form->GameDirectory).IsEmpty())
		{
			OutProblem = TEXT("Set Game Directory (the catalog is in its Create a Character System folder).");
		}
		return OutProblem.IsEmpty();
	}

	bool SavePart(FString& OutReport)
	{
		FString Problem;
		if (!Ready(Problem))
		{
			OutReport += Problem + TEXT("\n");
			return false;
		}
		const TSharedRef<FJsonObject> Entry = RebirthPartsUtil::PartToJson(*Form);
		const bool bOk = RebirthPartsUtil::PutInCatalog(Form->GameDirectory, Form->PartId(), Entry, OutReport);
		if (bOk)
		{
			OutReport += FString::Printf(TEXT("Part %s saved: start the game again to see it on the PARTS page (the game reads its catalog as it starts).\n"), *Form->PartId());
			Form->Part = FString::Printf(TEXT("%s: %s   [catalog.extra.json]"), *Form->PartId(), *Form->Name.TrimStartAndEnd());
		}
		return bOk;
	}

	FReply OnSave()
	{
		FString Text;
		SavePart(Text);
		SetReport(Text);
		ShowPreview();
		return FReply::Handled();
	}

	// The part's assets of this project (not the game's): its model, its motions, its tint texture, its effects.
	TArray<FSoftObjectPath> OwnAssets(FString& OutList) const
	{
		TArray<FSoftObjectPath> Candidates;
		Candidates.Add(Form->Model.ToSoftObjectPath());
		Candidates.Add(Form->Idle.ToSoftObjectPath());
		for (const FEndPartMove& Move : Form->Moves)
		{
			Candidates.Add(Move.Motion.ToSoftObjectPath());
		}
		if (Form->bSync)
		{
			Candidates.Append(RebirthPartsUtil::AnimationsUnder(Form->SyncRoot()));
		}
		Candidates.Add(Form->TintTexture.ToSoftObjectPath());
		for (const FEndPartEffect& Effect : Form->Effects)   // (3.13.0) an effect made in this project goes into the part's pak too
		{
			Candidates.Add(Effect.Effect);
		}
		TArray<FSoftObjectPath> Own;
		int32 Game = 0;
		for (const FSoftObjectPath& Path : Candidates)
		{
			if (Path.IsNull() || Own.Contains(Path))
			{
				continue;
			}
			if (!RebirthPartsUtil::IsOwnAsset(Path))
			{
				++Game;
				continue;
			}
			Own.Add(Path);
		}
		OutList = FString::Printf(TEXT("%d asset(s) of this project, %d of the game's"), Own.Num(), Game);
		return Own;
	}

	FReply OnBuild()
	{
		FString Text;
		FString Problem;
		if (!Ready(Problem))
		{
			SetReport(Problem);
			return FReply::Handled();
		}
		FString Counted;
		const TArray<FSoftObjectPath> Own = OwnAssets(Counted);
		bool bBuilt = true;
		if (Own.Num() == 0)
		{
			Text += TEXT("Every asset of the part is the game's (") + Counted + TEXT("): nothing to build.\n");
		}
		else
		{
			FEndCharacterSkin Assets;
			Assets.Name = Form->Name.TrimStartAndEnd().IsEmpty() ? Form->PartId() : Form->Name.TrimStartAndEnd();
			Assets.Folder = Form->AssetsFolderName();
			Assets.Model = Form->Model;
			Assets.Description = TEXT("The Customization part ") + Form->PartId() + TEXT("'s own assets (made by the Parts Builder)");
			for (const FSoftObjectPath& Path : Own)
			{
				if (Path != Form->Model.ToSoftObjectPath())
				{
					Assets.ExtraAssets.Add(Path);
				}
			}
			RebirthSkelCompatSkins::FSkinBuildOptions Options;
			Options.bPart = true;
			Options.Title = TEXT("Build Part");
			Text += TEXT("Building the part's own assets (") + Counted + TEXT(") into skins\\") + Assets.Folder + TEXT(":\n");
			bBuilt = RebirthSkelCompatSkins::BuildSkinList({Assets}, FDirectoryPath(), Form->GameDirectory, true, Options, Text);
		}
		if (bBuilt)
		{
			SavePart(Text);
		}
		else
		{
			Text += TEXT("\nThe part was NOT saved in the catalog: its assets did not build (above). Save Part saves it anyway.\n");
		}
		SetReport(Text);
		ShowPreview();
		return FReply::Handled();
	}

	FReply OnRemove()
	{
		const FString MyId = Form->PartId();
		FString Text;
		if (!RebirthPartsUtil::ValidId(MyId))
		{
			Text = TEXT("Pick the part to take out (Part), or give its Id.");
		}
		else if (RebirthPartsUtil::PutInCatalog(Form->GameDirectory, MyId, nullptr, Text))
		{
			Text += FString::Printf(TEXT("Part %s taken out of the catalog (its assets stay in skins\\%s). A part the catalog maker makes itself comes back when it runs again.\n"), *MyId,
				*Form->AssetsFolderName());
			Form->Part = UEndPartsBuilder::NewPartLabel();
		}
		SetReport(Text);
		ShowPreview();
		return FReply::Handled();
	}

	FReply OnOpenModel()
	{
		USkeletalMesh* Mesh = Form->Model.LoadSynchronous();
		SetReport(RebirthPartsUtil::OpenInEditor(Mesh) ? FString::Printf(TEXT("Opened %s."), *Mesh->GetName()) : FString(TEXT("Pick a model that loads (Model) first.")));
		return FReply::Handled();
	}

	FReply OnOpenIdle()
	{
		UAnimSequence* Loop = Form->Idle.LoadSynchronous();
		SetReport(RebirthPartsUtil::OpenInEditor(Loop) ? FString::Printf(TEXT("Opened %s."), *Loop->GetName()) : FString(TEXT("Pick an idle that loads (Idle) first.")));
		return FReply::Handled();
	}

	FReply OnPause()
	{
		if (Viewport.IsValid())
		{
			const bool bNow = Viewport->TogglePause();
			SetReport(bNow ? TEXT("The preview is paused.") : TEXT("The preview plays."));
		}
		return FReply::Handled();
	}

	FReply OnRestart()
	{
		if (Viewport.IsValid())
		{
			Viewport->Restart();
		}
		return FReply::Handled();
	}

	FReply OnFrame()
	{
		if (Viewport.IsValid())
		{
			Viewport->Frame();
		}
		return FReply::Handled();
	}
};

// ------------------------------------------------------------------------------------------------
// The tab
// ------------------------------------------------------------------------------------------------
namespace RebirthSkelCompatEditor
{
const FName PartsBuilderTabName(TEXT("RebirthPartsBuilder"));

namespace PartsBuilderTab
{
TWeakPtr<SEndPartsBuilder> Current;
TWeakObjectPtr<USkeletalMesh> PendingModel;
}

TSharedRef<SDockTab> SpawnPartsBuilderTab(const FSpawnTabArgs& Args)
{
	TSharedRef<SEndPartsBuilder> Widget = SNew(SEndPartsBuilder);
	PartsBuilderTab::Current = Widget;
	Widget->Open(PartsBuilderTab::PendingModel.Get());
	return SNew(SDockTab)
		.TabRole(ETabRole::NomadTab)
		.Label(LOCTEXT("TabLabel", "Rebirth Parts Builder"))
		[
			Widget
		];
}

void OpenPartsBuilderTab(USkeletalMesh* Model)
{
	PartsBuilderTab::PendingModel = Model;
	const bool bHad = PartsBuilderTab::Current.IsValid();
	FGlobalTabmanager::Get()->TryInvokeTab(FTabId(PartsBuilderTabName));
	if (TSharedPtr<SEndPartsBuilder> Widget = PartsBuilderTab::Current.Pin(); Widget.IsValid() && bHad)
	{
		Widget->Open(Model);
	}
	PartsBuilderTab::PendingModel.Reset();
}
} // namespace RebirthSkelCompatEditor

#undef LOCTEXT_NAMESPACE
