// RebirthSkelCompat Skin Maker (editor 1.17): make a character skin from a model, in a window of its own.
#include "EndSkinMaker.h"
#include "EndSkinBuild.h"

#include "Animation/Skeleton.h"
#include "AssetRegistryModule.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Editor.h"
#include "Engine/SkeletalMesh.h"
#include "FileHelpers.h"
#include "Framework/Docking/TabManager.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformProcess.h"
#include "IDetailsView.h"
#include "Misc/DateTime.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "PropertyEditorModule.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Subsystems/AssetEditorSubsystem.h"
#include "UObject/Package.h"
#include "UObject/StrongObjectPtr.h"
#include "Widgets/Docking/SDockTab.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SCompoundWidget.h"

#define LOCTEXT_NAMESPACE "RebirthSkinMaker"

// Named, not anonymous: the module may be compiled as one unity file with the other sources.
namespace RebirthSkinMakerUtil
{
const TCHAR* const NoVoice = TEXT("(none: the character's own voice)");
const TCHAR* const OwnVoice = TEXT("own (the voice its animations name: the model's own character's)");
const TCHAR* const NoWeapon = TEXT("(none: the character's own weapon)");
const TCHAR* const PickerSeparator = TEXT("   |   ");

// "Young Sephiroth   |   /Game/Sound/..." -> "/Game/Sound/..."; the none and own lines -> "" and "own".
FString PickedValue(const FString& Line)
{
	const int32 Game = Line.Find(TEXT("/Game/"));
	if (Game != INDEX_NONE)
	{
		return Line.Mid(Game).TrimStartAndEnd();
	}
	if (Line.StartsWith(TEXT("own")))
	{
		return TEXT("own");
	}
	return FString();
}

// A row name: PC0000_00_Cloud_Standard (two letters, four digits, _).
bool LooksLikeRow(const FString& Text)
{
	return Text.Len() > 7 && FChar::IsAlpha(Text[0]) && FChar::IsAlpha(Text[1]) && FChar::IsDigit(Text[2]) && FChar::IsDigit(Text[3]) && FChar::IsDigit(Text[4]) &&
		   FChar::IsDigit(Text[5]) && Text[6] == TEXT('_') && !Text.Contains(TEXT("/")) && !Text.Contains(TEXT(" "));
}

// The game's Customization catalog (customization\catalog.json, written by make_customization_catalog.py): its voices
// and weapons as picker lines, read again when the file changes.
struct FCatalogLists
{
	FString File;
	FDateTime Stamp;
	TArray<FString> Voices;
	TArray<FString> Weapons;
};

FCatalogLists& CatalogOf(const FDirectoryPath& GameDirectory)
{
	static FCatalogLists Lists;
	const FString Mod = RebirthSkelCompatSkins::GameModFolderOf(GameDirectory);
	const FString File = Mod.IsEmpty() ? FString() : FPaths::Combine(Mod, TEXT("customization"), TEXT("catalog.json"));
	const FDateTime Stamp = File.IsEmpty() ? FDateTime::MinValue() : IFileManager::Get().GetTimeStamp(*File);
	if (File == Lists.File && Stamp == Lists.Stamp)
	{
		return Lists;
	}
	Lists = FCatalogLists();
	Lists.File = File;
	Lists.Stamp = Stamp;
	FString Text;
	if (File.IsEmpty() || !FFileHelper::LoadFileToString(Text, *File))
	{
		return Lists;
	}
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		return Lists;
	}
	const TArray<TSharedPtr<FJsonValue>>* Voices = nullptr;
	if (Root->TryGetArrayField(TEXT("voices"), Voices))
	{
		for (const TSharedPtr<FJsonValue>& Value : *Voices)
		{
			const TSharedPtr<FJsonObject>* Entry = nullptr;
			FString Bank, Name, Note;
			if (Value.IsValid() && Value->TryGetObject(Entry) && (*Entry)->TryGetStringField(TEXT("bank"), Bank) && Bank.StartsWith(TEXT("/Game/")))
			{
				(*Entry)->TryGetStringField(TEXT("name"), Name);
				(*Entry)->TryGetStringField(TEXT("note"), Note);
				Lists.Voices.Add((Name.IsEmpty() ? FPackageName::GetShortName(Bank) : Name) + (Note.IsEmpty() ? FString() : TEXT(" (") + Note + TEXT(")")) + PickerSeparator + Bank);
			}
		}
	}
	const TArray<TSharedPtr<FJsonValue>>* Weapons = nullptr;
	if (Root->TryGetArrayField(TEXT("weapons"), Weapons))
	{
		for (const TSharedPtr<FJsonValue>& Value : *Weapons)
		{
			const TSharedPtr<FJsonObject>* Entry = nullptr;
			if (!Value.IsValid() || !Value->TryGetObject(Entry))
			{
				continue;
			}
			FString Class, Path, Name;
			(*Entry)->TryGetStringField(TEXT("class"), Class);
			(*Entry)->TryGetStringField(TEXT("path"), Path);
			(*Entry)->TryGetStringField(TEXT("name"), Name);
			if (Class.IsEmpty() && Path.StartsWith(TEXT("/Game/")) && !Path.Contains(TEXT(".")))
			{
				const FString Leaf = FPackageName::GetShortName(Path);
				Class = Path + TEXT(".") + Leaf + TEXT("_C");   // (a blueprint's class, as the game mod reads "path")
			}
			if (Class.StartsWith(TEXT("/Game/")))
			{
				Lists.Weapons.Add((Name.IsEmpty() ? FPackageName::GetShortName(Class) : Name) + PickerSeparator + Class);
			}
		}
	}
	return Lists;
}

bool OpenInEditor(UObject* Asset)
{
	UAssetEditorSubsystem* Editors = GEditor ? GEditor->GetEditorSubsystem<UAssetEditorSubsystem>() : nullptr;
	return Asset && Editors && Editors->OpenEditorForAsset(Asset);
}

// The data object at DefaultSkinsDataObject: loaded, or made (and saved) the first time.
UEndSkeletonCompatDataObject* SkinsDataObject(const FDirectoryPath& GameDirectory, FString& OutNote)
{
	const FString ObjectPath = RebirthSkelCompatEditor::DefaultSkinsDataObject;
	const FString PackageName = FPackageName::ObjectPathToPackageName(ObjectPath);
	if (UEndSkeletonCompatDataObject* Found = LoadObject<UEndSkeletonCompatDataObject>(nullptr, *ObjectPath, nullptr, LOAD_NoWarn | LOAD_Quiet))
	{
		return Found;
	}
	if (FPackageName::DoesPackageExist(PackageName))
	{
		OutNote = PackageName + TEXT(" is there but is not a Skeleton Compatibility Data Object: pick a data object (Data Object)");
		return nullptr;
	}
	UPackage* Package = CreatePackage(*PackageName);
	if (!Package)
	{
		OutNote = PackageName + TEXT(" could not be made");
		return nullptr;
	}
	Package->FullyLoad();
	UEndSkeletonCompatDataObject* Made = NewObject<UEndSkeletonCompatDataObject>(Package, FName(*FPackageName::GetShortName(PackageName)), RF_Public | RF_Standalone | RF_Transactional);
	if (!GameDirectory.Path.TrimStartAndEnd().IsEmpty())
	{
		Made->GameDirectory = GameDirectory;
	}
	FAssetRegistryModule::AssetCreated(Made);
	Package->MarkPackageDirty();
	OutNote = TEXT("Made the data object ") + PackageName + TEXT(" for your skins (Save Skin keeps them there).");
	return Made;
}

bool SavePackageOf(UObject* Object, FString& OutProblem)
{
	UPackage* Package = Object ? Object->GetOutermost() : nullptr;
	if (!Package)
	{
		OutProblem = TEXT("nothing to save");
		return false;
	}
	TArray<UPackage*> NotSaved;
	FEditorFileUtils::PromptForCheckoutAndSave({Package}, false, false, &NotSaved);
	if (NotSaved.Num() > 0)
	{
		OutProblem = Package->GetName() + TEXT(" could not be saved");
		return false;
	}
	return true;
}
} // namespace RebirthSkinMakerUtil

// ------------------------------------------------------------------------------------------------
// The form
// ------------------------------------------------------------------------------------------------
const TCHAR* UEndSkinMaker::NewSkinLabel() { return TEXT("(new skin)"); }

const TArray<FString>& UEndSkinMaker::CharacterRows() const
{
	if (bRowsRead && RowsOf.Get() == DataObject)
	{
		return Rows;
	}
	Rows.Reset();
	RowsOf = DataObject;
	bRowsRead = true;
	if (DataObject)
	{
		Rows = DataObject->PlayableCharaSpecRows();
		// (the data object's own characters too: without the game's object tools those are all there is)
		for (const FEndCharacterSkin& Other : DataObject->Skins)
		{
			for (const FString& Row : Other.Characters)
			{
				if (RebirthSkinMakerUtil::LooksLikeRow(Row.TrimStartAndEnd()))
				{
					Rows.AddUnique(Row.TrimStartAndEnd());
				}
			}
		}
		for (const FEndAnimSetRow& Set : DataObject->AnimationSets)
		{
			for (const FString& Row : Set.Characters)
			{
				if (RebirthSkinMakerUtil::LooksLikeRow(Row.TrimStartAndEnd()))
				{
					Rows.AddUnique(Row.TrimStartAndEnd());
				}
			}
		}
		Rows.Sort();
	}
	return Rows;
}

TArray<FString> UEndSkinMaker::GetSkinOptions() const
{
	TArray<FString> Options;
	Options.Add(NewSkinLabel());
	if (DataObject)
	{
		for (int32 Index = 0; Index < DataObject->Skins.Num(); ++Index)
		{
			const FEndCharacterSkin& Other = DataObject->Skins[Index];
			Options.Add(FString::Printf(TEXT("%d: %s"), Index, Other.Name.TrimStartAndEnd().IsEmpty() ? *RebirthSkelCompatSkins::SkinFolderOf(Other) : *Other.Name.TrimStartAndEnd()));
		}
	}
	return Options;
}

TArray<FString> UEndSkinMaker::GetCharacterOptions() const
{
	TArray<FString> Options;
	const TArray<FString>& Known = CharacterRows();
	// every row of a character first (all of its outfits): PC0000_* (9 rows)
	TMap<FString, int32> Counts;
	for (const FString& Row : Known)
	{
		Counts.FindOrAdd(Row.Left(6))++;
	}
	Counts.KeySort([](const FString& A, const FString& B) { return A < B; });
	for (const TPair<FString, int32>& Count : Counts)
	{
		if (Count.Value > 1)
		{
			Options.Add(FString::Printf(TEXT("%s_*   (every %s row: %d)"), *Count.Key, *Count.Key, Count.Value));
		}
	}
	Options.Append(Known);
	if (Options.Num() == 0)
	{
		Options.Add(TEXT("PC0000_00_Cloud_Standard"));
	}
	return Options;
}

TArray<FString> UEndSkinMaker::GetVoiceOptions() const
{
	TArray<FString> Options;
	Options.Add(RebirthSkinMakerUtil::NoVoice);
	Options.Add(RebirthSkinMakerUtil::OwnVoice);
	Options.Append(RebirthSkinMakerUtil::CatalogOf(GameDirectory).Voices);
	return Options;
}

TArray<FString> UEndSkinMaker::GetWeaponOptions() const
{
	TArray<FString> Options;
	Options.Add(RebirthSkinMakerUtil::NoWeapon);
	Options.Append(RebirthSkinMakerUtil::CatalogOf(GameDirectory).Weapons);
	return Options;
}

FString UEndSkinMaker::FolderName() const
{
	FEndCharacterSkin Probe;
	Probe.Name = Name;
	Probe.Folder = Folder;
	return RebirthSkelCompatSkins::SkinFolderOf(Probe);
}

int32 UEndSkinMaker::SkinIndex() const
{
	if (!DataObject)
	{
		return INDEX_NONE;
	}
	FString Left;
	if (Skin.Split(TEXT(":"), &Left, nullptr) && Left.TrimStartAndEnd().IsNumeric())
	{
		const int32 Index = FCString::Atoi(*Left.TrimStartAndEnd());
		if (DataObject->Skins.IsValidIndex(Index))
		{
			return Index;
		}
	}
	const FString Mine = FolderName();
	if (Mine.IsEmpty())
	{
		return INDEX_NONE;
	}
	return DataObject->Skins.IndexOfByPredicate([&](const FEndCharacterSkin& Other) { return RebirthSkelCompatSkins::SkinFolderOf(Other).Equals(Mine, ESearchCase::IgnoreCase); });
}

FEndCharacterSkin UEndSkinMaker::MakeSkin() const
{
	FEndCharacterSkin Out;
	const int32 Index = SkinIndex();
	if (DataObject && Index != INDEX_NONE)
	{
		Out = DataObject->Skins[Index];   // (keeps its Preview and Enabled)
	}
	Out.Name = Name.TrimStartAndEnd();
	Out.Folder = Folder.TrimStartAndEnd();
	Out.Model = Model;
	Out.Characters.Reset();
	for (const FString& Row : Characters)
	{
		const FString Trimmed = Row.TrimStartAndEnd();
		if (!Trimmed.IsEmpty())
		{
			Out.Characters.AddUnique(Trimmed);
		}
	}
	Out.bWornAtOnce = bWornAtOnce;
	Out.Family = Family;
	Out.bKeepProportions = bKeepProportions;
	Out.ProportionBones = ProportionBones;
	Out.AnimBlueprint = AnimBlueprint.TrimStartAndEnd();
	Out.Voice = Voice.TrimStartAndEnd();
	Out.Weapon = Weapon.TrimStartAndEnd();
	Out.Meshes = Meshes;
	Out.ExtraAssets = ExtraAssets;
	Out.Author = Author.TrimStartAndEnd();
	Out.Description = Description.TrimStartAndEnd();
	return Out;
}

void UEndSkinMaker::TakeSkin(const FEndCharacterSkin& From)
{
	Name = From.Name;
	Folder = From.Folder;
	Model = From.Model;
	Characters = From.Characters;
	bWornAtOnce = From.bWornAtOnce;
	Family = From.Family;
	bKeepProportions = From.bKeepProportions;
	ProportionBones = From.ProportionBones;
	AnimBlueprint = From.AnimBlueprint;
	Voice = From.Voice;
	Weapon = From.Weapon;
	Meshes = From.Meshes;
	ExtraAssets = From.ExtraAssets;
	Author = From.Author;
	Description = From.Description;
	AddCharacter.Reset();
	PickVoice.Reset();
	PickWeapon.Reset();
}

void UEndSkinMaker::StartFrom(USkeletalMesh* InModel)
{
	const FEndCharacterSkin Blank;
	TakeSkin(Blank);
	Skin = NewSkinLabel();
	if (!InModel)
	{
		return;
	}
	Model = InModel;
	// its name from the model's: EB0021_00_Sephiroth -> EB0021 00 Sephiroth (a name to change)
	Name = InModel->GetName().Replace(TEXT("_"), TEXT(" "));
	// the characters and the family of the data object's last skin: a new skin of a data object of a character's skins
	// is most likely one more of them
	if (DataObject && DataObject->Skins.Num() > 0)
	{
		const FEndCharacterSkin& Last = DataObject->Skins.Last();
		Characters = Last.Characters;
		Family = Last.Family;
	}
	if (!Family.IsNull() && InModel->Skeleton && Family.ToSoftObjectPath() == FSoftObjectPath(InModel->Skeleton))
	{
		Family.Reset();   // (the model is on that skeleton itself)
	}
}

bool UEndSkinMaker::TakePickers()
{
	bool bChanged = false;
	const FString Pick = AddCharacter.TrimStartAndEnd();
	if (!Pick.IsEmpty())
	{
		FString Left;
		if (Pick.Split(TEXT("_*"), &Left, nullptr) && Left.Len() == 6)
		{
			for (const FString& Row : CharacterRows())
			{
				if (Row.StartsWith(Left + TEXT("_")))
				{
					Characters.AddUnique(Row);
				}
			}
		}
		else
		{
			Characters.AddUnique(Pick);
		}
		AddCharacter.Reset();
		bChanged = true;
	}
	if (!PickVoice.IsEmpty())
	{
		Voice = RebirthSkinMakerUtil::PickedValue(PickVoice);
		PickVoice.Reset();
		bChanged = true;
	}
	if (!PickWeapon.IsEmpty())
	{
		Weapon = RebirthSkinMakerUtil::PickedValue(PickWeapon);
		PickWeapon.Reset();
		bChanged = true;
	}
	return bChanged;
}

void UEndSkinMaker::Describe()
{
	TArray<FString> Lines;
	const int32 Index = SkinIndex();
	if (!DataObject)
	{
		Lines.Add(FString::Printf(TEXT("Data object: none picked: Save Skin keeps the skin in %s (made the first time)."),
			*FPackageName::ObjectPathToPackageName(FString(RebirthSkelCompatEditor::DefaultSkinsDataObject))));
	}
	else
	{
		Lines.Add(FString::Printf(TEXT("Data object: %s (%d skin(s)): %s"), *DataObject->GetPathName(), DataObject->Skins.Num(),
			Index == INDEX_NONE ? TEXT("Save Skin adds this one") : *FString::Printf(TEXT("this is its skin %d: Save Skin updates it"), Index)));
	}
	USkeletalMesh* Mesh = Model.LoadSynchronous();
	if (!Mesh)
	{
		Lines.Add(Model.IsNull() ? FString(TEXT("Model: pick the model (or right-click a Skeletal Mesh > Create a Character Skin...)")) : TEXT("Model: ") + Model.ToString() + TEXT(" does not load"));
	}
	else
	{
		const USkeleton* Bones = Mesh->Skeleton;
		Lines.Add(FString::Printf(TEXT("Model: %s, %d bones, %d material slot(s), skeleton %s"), *Mesh->GetPathName(), Mesh->RefSkeleton.GetNum(), Mesh->Materials.Num(),
			Bones ? *Bones->GetPathName() : TEXT("none")));
		if (USkeleton* Hub = Family.LoadSynchronous())
		{
			if (Hub == Bones)
			{
				Lines.Add(TEXT("Family: the model's own skeleton (not needed: clear it)"));
			}
			else
			{
				int32 Missing = 0;
				for (int32 Bone = 0; Bone < Mesh->RefSkeleton.GetNum(); ++Bone)
				{
					Missing += Hub->GetReferenceSkeleton().FindBoneIndex(Mesh->RefSkeleton.GetBoneName(Bone)) == INDEX_NONE ? 1 : 0;
				}
				Lines.Add(FString::Printf(TEXT("Family: %s: the model plays its family's animations (%d of its bones are not in it%s)"), *Hub->GetName(), Missing,
					Missing > 0 ? TEXT(": no animation of the family moves them, physics bones are fine") : TEXT("")));
			}
		}
		else if (Family.IsNull())
		{
			const bool bCharacters = Bones && Bones->GetPathName().StartsWith(TEXT("/Game/Character/"));
			Lines.Add(bCharacters ? TEXT("Family: none: the model is on its character's own skeleton")
								  : TEXT("Family: none: the model plays only the animations of its own skeleton; to play the character's, set Family to the character's skeleton (Sephiroth's: PC0010_00_Skeleton)"));
		}
		else
		{
			Lines.Add(TEXT("Family: ") + Family.ToString() + TEXT(" does not load here (the game still joins the model's skeleton to it)"));
		}
	}
	const FString MyFolder = FolderName();
	const FString Mod = RebirthSkelCompatSkins::GameModFolderOf(GameDirectory);
	const bool bInstalled = !Mod.IsEmpty() && !MyFolder.IsEmpty() && FPaths::FileExists(FPaths::Combine(Mod, TEXT("skins"), MyFolder, TEXT("skin.json")));
	Lines.Add(MyFolder.IsEmpty() ? FString(TEXT("Folder: give it a Name (or a Folder)"))
			  : !RebirthSkelCompatSkins::IsValidSkinFolder(MyFolder) ? TEXT("Folder: \"") + MyFolder + TEXT("\" is not 1-64 letters, digits, _ or -: change the Folder")
			  : FString::Printf(TEXT("Folder: skins\\%s%s"), *MyFolder, bInstalled ? TEXT(" (installed in the game: Build Skin replaces it)") : TEXT("")));
	Lines.Add(Characters.Num() == 0 ? FString(TEXT("Characters: none yet: add the rows that wear it (Add Character)"))
									: FString::Printf(TEXT("Characters: %d row(s)%s"), Characters.Num(), bWornAtOnce ? TEXT(", worn as the game starts") : TEXT(", a choice on the SKINS page")));
	Lines.Add(FString::Printf(TEXT("Voice: %s; weapon: %s"), Voice.IsEmpty() ? TEXT("the character's") : *Voice, Weapon.IsEmpty() ? TEXT("the character's") : *Weapon));
	if (Meshes.Num() > 0)
	{
		Lines.Add(FString::Printf(TEXT("%d model part(s) worn with it"), Meshes.Num()));
	}
	if (Mod.IsEmpty() || !IFileManager::Get().DirectoryExists(*Mod))
	{
		Lines.Add(TEXT("Game Directory: no Create a Character System there: Build Skin builds the skin but does not install it"));
	}
	About = FString::Join(Lines, TEXT("\n"));
}

// ------------------------------------------------------------------------------------------------
// The window
// ------------------------------------------------------------------------------------------------
class SEndSkinMaker : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SEndSkinMaker) {}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs)
	{
		Form.Reset(NewObject<UEndSkinMaker>(GetTransientPackage(), NAME_None, RF_Transient));
		Form->Skin = UEndSkinMaker::NewSkinLabel();
		Form->GameDirectory.Path = TEXT("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII REBIRTH");
		FPropertyEditorModule& PropertyEditor = FModuleManager::LoadModuleChecked<FPropertyEditorModule>(TEXT("PropertyEditor"));
		FDetailsViewArgs Args;
		Args.bAllowSearch = false;
		Args.bHideSelectionTip = true;
		Args.NameAreaSettings = FDetailsViewArgs::HideNameArea;
		Details = PropertyEditor.CreateDetailView(Args);
		Details->SetObject(Form.Get());
		Details->OnFinishedChangingProperties().AddSP(this, &SEndSkinMaker::OnFormChanged);
		Form->Describe();
		Report = LOCTEXT("Start", "Pick the model (or right-click a Skeletal Mesh in the Content Browser > Create a Character Skin...), give the skin a name and the characters that wear it, then Build Skin. It is kept in the data object's Skins.");

		ChildSlot
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
				+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("Load", "Load Skin"), LOCTEXT("LoadTip", "Fill the form from the data object's skin picked in Skin (picking one does it too)."), &SEndSkinMaker::OnLoad)]
				+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("New", "New Skin"), LOCTEXT("NewTip", "Start a new skin of the model in the form."), &SEndSkinMaker::OnNew)]
				+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("Save", "Save Skin"), LOCTEXT("SaveTip", "Put the skin in the data object's Skins (a skin of the same folder is updated) and save the data object."), &SEndSkinMaker::OnSave)]
				+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("Build", "Build Skin"), LOCTEXT("BuildTip", "Save Skin, then build it: cooked into the game's package format, installed into the game and the skins container made anew (close the game first)."), &SEndSkinMaker::OnBuild)]
				+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("OpenModel", "Open Model"), LOCTEXT("OpenModelTip", "Open the model in the mesh editor."), &SEndSkinMaker::OnOpenModel)]
				+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("OpenData", "Open Data Object"), LOCTEXT("OpenDataTip", "Open the data object (every skin, Build Skins)."), &SEndSkinMaker::OnOpenDataObject)]
				+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("ShowFolder", "Show In Game"), LOCTEXT("ShowFolderTip", "Open the skin's folder in the game (skins\\<Folder>)."), &SEndSkinMaker::OnShowFolder)]
			]
			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(4.f)
			[
				SNew(SBox)
				.HeightOverride(220.f)
				[
					SNew(SMultiLineEditableTextBox)
					.IsReadOnly(true)
					.AutoWrapText(true)
					.Text(this, &SEndSkinMaker::GetReport)
				]
			]
		];
	}

	void Open(UEndSkeletonCompatDataObject* Object, USkeletalMesh* Mesh)
	{
		if (!Form.IsValid())
		{
			return;
		}
		if (Object)
		{
			Form->DataObject = Object;
			Form->GameDirectory = Object->GameDirectory;
			Form->bInstall = Object->bInstallSkins;
		}
		if (Mesh)
		{
			Form->StartFrom(Mesh);
			SetReport(FString::Printf(TEXT("A new skin of %s: give it its name and its characters (they and its Family are the data object's last skin's, if it has one), then Build Skin."), *Mesh->GetName()));
		}
		Refresh();
	}

private:
	TStrongObjectPtr<UEndSkinMaker> Form;
	TSharedPtr<IDetailsView> Details;
	FText Report;

	TSharedRef<SWidget> MakeButton(const FText& Label, const FText& Tip, FReply (SEndSkinMaker::*Handler)())
	{
		return SNew(SButton).Text(Label).ToolTipText(Tip).OnClicked(this, Handler);
	}

	FText GetReport() const { return Report; }

	void SetReport(const FString& Text) { Report = FText::FromString(Text); }

	void Refresh()
	{
		Form->Describe();
		Details->ForceRefresh();
	}

	bool LoadPicked()
	{
		FString Left;
		if (!Form->DataObject || !Form->Skin.Split(TEXT(":"), &Left, nullptr) || !Left.TrimStartAndEnd().IsNumeric())
		{
			return false;
		}
		const int32 Index = FCString::Atoi(*Left.TrimStartAndEnd());
		if (!Form->DataObject->Skins.IsValidIndex(Index))
		{
			return false;
		}
		Form->TakeSkin(Form->DataObject->Skins[Index]);
		return true;
	}

	void OnFormChanged(const FPropertyChangedEvent& Event)
	{
		const FName Member = Event.MemberProperty ? Event.MemberProperty->GetFName() : Event.GetPropertyName();
		if (Member == GET_MEMBER_NAME_CHECKED(UEndSkinMaker, DataObject) && Form->DataObject)
		{
			Form->GameDirectory = Form->DataObject->GameDirectory;
			Form->bInstall = Form->DataObject->bInstallSkins;
			Form->Skin = UEndSkinMaker::NewSkinLabel();
		}
		if (Member == GET_MEMBER_NAME_CHECKED(UEndSkinMaker, Skin))
		{
			if (LoadPicked())
			{
				SetReport(FString::Printf(TEXT("Loaded the data object's skin %s."), *Form->Skin));
			}
		}
		if (Form->TakePickers())
		{
			SetReport(FString::Printf(TEXT("%d character(s); voice: %s; weapon: %s."), Form->Characters.Num(), Form->Voice.IsEmpty() ? TEXT("the character's") : *Form->Voice,
				Form->Weapon.IsEmpty() ? TEXT("the character's") : *Form->Weapon));
		}
		Refresh();
	}

	FReply OnLoad()
	{
		SetReport(LoadPicked() ? FString::Printf(TEXT("Loaded the data object's skin %s."), *Form->Skin)
							   : FString(TEXT("Pick one of the data object's skins in Skin first (the data object has to have one).")));
		Refresh();
		return FReply::Handled();
	}

	FReply OnNew()
	{
		USkeletalMesh* Mesh = Form->Model.LoadSynchronous();
		Form->StartFrom(Mesh);
		SetReport(Mesh ? FString::Printf(TEXT("A new skin of %s."), *Mesh->GetName()) : FString(TEXT("A new skin: pick its model.")));
		Refresh();
		return FReply::Handled();
	}

	// The skin into the data object (made when there is none), saved. OutIndex: its index there.
	bool SaveSkin(int32& OutIndex, FString& OutMessage)
	{
		OutIndex = INDEX_NONE;
		const FString Folder = Form->FolderName();
		if (Form->Model.IsNull())
		{
			OutMessage = TEXT("Pick the model first (Model).");
			return false;
		}
		if (Folder.IsEmpty() || !RebirthSkelCompatSkins::IsValidSkinFolder(Folder))
		{
			OutMessage = TEXT("Give the skin a Name (its folder is the name's letters and digits), or a Folder of 1-64 letters, digits, _ or -.");
			return false;
		}
		FString Note;
		if (!Form->DataObject)
		{
			Form->DataObject = RebirthSkinMakerUtil::SkinsDataObject(Form->GameDirectory, Note);
			if (!Form->DataObject)
			{
				OutMessage = Note;
				return false;
			}
		}
		UEndSkeletonCompatDataObject* Object = Form->DataObject;
		const FEndCharacterSkin Made = Form->MakeSkin();
		int32 Index = Form->SkinIndex();
		Object->Modify();
		if (Index == INDEX_NONE)
		{
			Index = Object->Skins.Add(Made);
		}
		else
		{
			Object->Skins[Index] = Made;
		}
		if (!Form->GameDirectory.Path.TrimStartAndEnd().IsEmpty())
		{
			Object->GameDirectory = Form->GameDirectory;
		}
		Object->bInstallSkins = Form->bInstall;
		Object->MarkPackageDirty();
		Form->Skin = FString::Printf(TEXT("%d: %s"), Index, Made.Name.IsEmpty() ? *Folder : *Made.Name);
		FString Problem;
		const bool bSaved = RebirthSkinMakerUtil::SavePackageOf(Object, Problem);
		OutIndex = Index;
		OutMessage = (Note.IsEmpty() ? FString() : Note + TEXT("\n")) +
					 FString::Printf(TEXT("Skin %d (%s) saved in %s%s."), Index, *Folder, *Object->GetPathName(), bSaved ? TEXT("") : *(TEXT(" (NOT saved to disk: ") + Problem + TEXT(")")));
		return true;
	}

	FReply OnSave()
	{
		int32 Index = INDEX_NONE;
		FString Message;
		SaveSkin(Index, Message);
		SetReport(Message);
		Refresh();
		return FReply::Handled();
	}

	FReply OnBuild()
	{
		int32 Index = INDEX_NONE;
		FString Message;
		if (SaveSkin(Index, Message))
		{
			FString Built;
			const bool bOk = Form->DataObject->BuildOneSkinTo(Index, Built);
			SetReport(Message + TEXT("\n") + (bOk ? TEXT("") : TEXT("Not everything went right:\n")) + Built);
		}
		else
		{
			SetReport(Message);
		}
		Refresh();
		return FReply::Handled();
	}

	FReply OnOpenModel()
	{
		USkeletalMesh* Mesh = Form->Model.LoadSynchronous();
		SetReport(RebirthSkinMakerUtil::OpenInEditor(Mesh) ? FString::Printf(TEXT("Opened %s."), *Mesh->GetName()) : FString(TEXT("Pick a model that loads (Model) first.")));
		return FReply::Handled();
	}

	FReply OnOpenDataObject()
	{
		SetReport(RebirthSkinMakerUtil::OpenInEditor(Form->DataObject) ? FString(TEXT("Opened the data object."))
																		: FString(TEXT("No data object yet: Save Skin makes one (or pick one in Data Object).")));
		return FReply::Handled();
	}

	FReply OnShowFolder()
	{
		const FString Mod = RebirthSkelCompatSkins::GameModFolderOf(Form->GameDirectory);
		const FString Folder = Form->FolderName();
		const FString Path = Mod.IsEmpty() || Folder.IsEmpty() ? FString() : FPaths::Combine(Mod, TEXT("skins"), Folder);
		if (!Path.IsEmpty() && IFileManager::Get().DirectoryExists(*Path))
		{
			FPlatformProcess::ExploreFolder(*Path);
			SetReport(TEXT("Opened ") + Path + TEXT("."));
		}
		else
		{
			SetReport(Path.IsEmpty() ? FString(TEXT("Set Game Directory and give the skin a name first.")) : Path + TEXT(" is not there yet: Build Skin installs it."));
		}
		return FReply::Handled();
	}
};

// ------------------------------------------------------------------------------------------------
// The tab
// ------------------------------------------------------------------------------------------------
namespace RebirthSkelCompatEditor
{
const FName SkinMakerTabName(TEXT("RebirthSkinMaker"));
const TCHAR* const DefaultSkinsDataObject = TEXT("/Game/RebirthSkelCompat/Skins/DO_Skins.DO_Skins");

namespace SkinMakerTab
{
TWeakPtr<SEndSkinMaker> Current;
TWeakObjectPtr<UEndSkeletonCompatDataObject> PendingDataObject;
TWeakObjectPtr<USkeletalMesh> PendingModel;
}

TSharedRef<SDockTab> SpawnSkinMakerTab(const FSpawnTabArgs& Args)
{
	TSharedRef<SEndSkinMaker> Widget = SNew(SEndSkinMaker);
	SkinMakerTab::Current = Widget;
	Widget->Open(SkinMakerTab::PendingDataObject.Get(), SkinMakerTab::PendingModel.Get());
	return SNew(SDockTab)
		.TabRole(ETabRole::NomadTab)
		.Label(LOCTEXT("TabLabel", "Rebirth Skin Maker"))
		[
			Widget
		];
}

void OpenSkinMakerTab(UEndSkeletonCompatDataObject* DataObject, USkeletalMesh* Model)
{
	SkinMakerTab::PendingDataObject = DataObject;
	SkinMakerTab::PendingModel = Model;
	const bool bHad = SkinMakerTab::Current.IsValid();
	FGlobalTabmanager::Get()->TryInvokeTab(FTabId(SkinMakerTabName));
	if (TSharedPtr<SEndSkinMaker> Widget = SkinMakerTab::Current.Pin(); Widget.IsValid() && bHad)
	{
		Widget->Open(DataObject, Model);   // (a tab spawned just now has been opened on them already)
	}
	SkinMakerTab::PendingDataObject.Reset();
	SkinMakerTab::PendingModel.Reset();
}
} // namespace RebirthSkelCompatEditor

#undef LOCTEXT_NAMESPACE
