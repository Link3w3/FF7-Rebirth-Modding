// RebirthSkelCompat AnimBlueprint Maker (editor 1.18): a character's AnimBlueprint for the game, made from one of the
// game's own for the character's skeleton, in a window of its own.
#include "EndAnimBlueprintMaker.h"

#include "Animation/AnimBlueprint.h"
#include "Animation/Skeleton.h"
#include "Dom/JsonObject.h"
#include "Editor.h"
#include "EndAnimBlueprintTemplate.h"
#include "Misc/PackageName.h"
#include "Subsystems/AssetEditorSubsystem.h"
#include "Framework/Docking/TabManager.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformApplicationMisc.h"
#include "HAL/PlatformProcess.h"
#include "IDetailsView.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "PropertyEditorModule.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/Package.h"
#include "UObject/StrongObjectPtr.h"
#include "Widgets/Docking/SDockTab.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SCompoundWidget.h"

#define LOCTEXT_NAMESPACE "RebirthAnimBlueprintMaker"

// Named, not anonymous: the module may be compiled as one unity file with the other sources.
namespace RebirthAnimBlueprintMakerUtil
{
// (1.19) The templates: RebirthAnimTemplate::Templates (the four built in, then abp\templates\templates.json's: the
// other characters' AnimBlueprints, with no new build).
FString FirstTemplateLabel()
{
	const TArray<RebirthAnimTemplate::FTemplateInfo> List = RebirthAnimTemplate::Templates();
	return List.Num() ? List[0].Label : FString(TEXT("cloud"));
}

FString Quoted(const FString& Text)
{
	return TEXT("\"") + Text + TEXT("\"");
}

// Tools\RebirthSkelCompat\abp under the project (where make_cacs_abp.py, its templates and its output are).
FString ToolDir()
{
	return FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectDir(), TEXT("Tools"), TEXT("RebirthSkelCompat"), TEXT("abp")));
}

bool IsNameText(const FString& Text)
{
	if (Text.IsEmpty() || Text.Len() > 120)
	{
		return false;
	}
	for (const TCHAR Ch : Text)
	{
		if (!FChar::IsAlnum(Ch) && Ch != TEXT('_'))
		{
			return false;
		}
	}
	return true;
}

// Runs the tool with Python (the py launcher, else the Python 3.9 the build scripts find, else python on the PATH).
// False: no Python started.
bool RunTool(const FString& Arguments, int32& OutCode, FString& OutText)
{
	const FString Script = Quoted(FPaths::Combine(ToolDir(), TEXT("make_cacs_abp.py")));
	TArray<TPair<FString, FString>> Pythons;
	Pythons.Add(TPair<FString, FString>(TEXT("py"), TEXT("-3 ")));
	const FString LocalAppData = FPlatformMisc::GetEnvironmentVariable(TEXT("LOCALAPPDATA"));
	if (!LocalAppData.IsEmpty())
	{
		for (const TCHAR* Folder : {TEXT("Python399"), TEXT("Python39")})
		{
			const FString Python39 = FPaths::Combine(LocalAppData, TEXT("Programs"), TEXT("Python"), Folder, TEXT("python.exe"));
			if (FPaths::FileExists(Python39))
			{
				Pythons.Add(TPair<FString, FString>(Python39, FString()));
			}
		}
	}
	Pythons.Add(TPair<FString, FString>(TEXT("python"), FString()));
	for (const TPair<FString, FString>& Python : Pythons)
	{
		FString Out, Err;
		int32 Code = -1;
		if (FPlatformProcess::ExecProcess(*Python.Key, *(Python.Value + Script + TEXT(" ") + Arguments), &Code, &Out, &Err) && Code != 9009)
		{
			OutCode = Code;
			OutText = Out + (Err.IsEmpty() ? FString() : TEXT("\n") + Err);
			return true;
		}
	}
	return false;
}
} // namespace RebirthAnimBlueprintMakerUtil

using namespace RebirthAnimBlueprintMakerUtil;

// ------------------------------------------------------------------------------------------------
// The form
// ------------------------------------------------------------------------------------------------
TArray<FString> UEndAnimBlueprintMaker::GetTemplateOptions() const
{
	TArray<FString> Out;
	for (const RebirthAnimTemplate::FTemplateInfo& Choice : RebirthAnimTemplate::Templates())
	{
		Out.Add(Choice.Label);
	}
	return Out;
}

FString UEndAnimBlueprintMaker::TemplateKey() const
{
	FString Key = Template;
	Template.Split(TEXT(":"), &Key, nullptr);
	Key = Key.TrimStartAndEnd().ToLower();
	for (const RebirthAnimTemplate::FTemplateInfo& Choice : RebirthAnimTemplate::Templates())
	{
		if (Key == Choice.Key)
		{
			return Key;
		}
	}
	return TEXT("cloud");
}

FString UEndAnimBlueprintMaker::SkeletonPath() const
{
	return Skeleton.IsNull() ? FString() : Skeleton.ToSoftObjectPath().ToString();
}

FString UEndAnimBlueprintMaker::FinalName() const
{
	if (!Name.TrimStartAndEnd().IsEmpty())
	{
		return Name.TrimStartAndEnd();
	}
	const FString Path = SkeletonPath();
	if (Path.IsEmpty())
	{
		return FString();
	}
	FString Package = Path, Object;
	Path.Split(TEXT("."), &Package, &Object);
	TArray<FString> Parts;
	Package.ParseIntoArray(Parts, TEXT("/"), true);
	if (Parts.Num() >= 3 && Parts[Parts.Num() - 2].Equals(TEXT("Model"), ESearchCase::IgnoreCase))
	{
		return Parts[Parts.Num() - 3] + TEXT("_Animation");
	}
	if (Object.IsEmpty() && Parts.Num() > 0)
	{
		Object = Parts.Last();
	}
	return Object.Replace(TEXT("_Skeleton"), TEXT("")) + TEXT("_Animation");
}

FString UEndAnimBlueprintMaker::PackagePath() const
{
	FString Dir = Folder.TrimStartAndEnd().Replace(TEXT("\\"), TEXT("/"));
	while (Dir.EndsWith(TEXT("/")))
	{
		Dir.LeftChopInline(1);
	}
	if (!Dir.StartsWith(TEXT("/")))
	{
		Dir = TEXT("/") + Dir;
	}
	return Dir + TEXT("/") + FinalName();
}

FString UEndAnimBlueprintMaker::ContainerName() const
{
	const FString Mine = Container.TrimStartAndEnd();
	if (!Mine.IsEmpty())
	{
		return Mine;
	}
	const FString MyName = FinalName();
	return MyName.IsEmpty() ? FString() : TEXT("CACS_") + MyName + TEXT("_P");
}

void UEndAnimBlueprintMaker::StartFrom(USkeleton* InSkeleton)
{
	if (InSkeleton)
	{
		Skeleton = InSkeleton;
		Name.Empty();
		AnimClass.Empty();
	}
	Describe();
}

void UEndAnimBlueprintMaker::Describe()
{
	TArray<FString> Lines;
	const FString MyName = FinalName();
	if (Skeleton.IsNull())
	{
		Lines.Add(TEXT("Skeleton: pick the character's skeleton (or right-click a Skeleton or Skeletal Mesh > Make a Rebirth AnimBlueprint...)"));
	}
	else
	{
		Lines.Add(TEXT("Skeleton: ") + SkeletonPath() + TEXT(" (the game needs it at this path: cook it into the character's mod)"));
	}
	if (!MyName.IsEmpty())
	{
		Lines.Add(IsNameText(MyName) ? TEXT("AnimBlueprint: ") + PackagePath() : TEXT("Name: \"") + MyName + TEXT("\" may only have letters, digits and _"));
		Lines.Add(TEXT("Its class (a form's \"anim_class\", a skin's \"anim_blueprint\"): ") + PackagePath() + TEXT(".") + MyName + TEXT("_C"));
	}
	Lines.Add(TEXT("Made from: ") + (Template.IsEmpty() ? FirstTemplateLabel() : Template) + TEXT("; its Control Rig ") + (bKeepControlRig ? TEXT("kept") : TEXT("off")));
	const FString MyContainer = ContainerName();
	if (!MyContainer.IsEmpty())
	{
		Lines.Add(TEXT("Container: ") + MyContainer + (bInstall ? TEXT(", installed into ~mods\\") + ModsFolder : FString(TEXT(" (not installed: it stays in Tools\\RebirthSkelCompat\\abp\\out)"))));
	}
	Lines.Add(TEXT("It plays the character's animations by name from its animation sets (CharaSpec packs), as the game's own characters do."));
	Lines.Add(TEXT("Make AnimBlueprint: the game's own AnimBlueprint under the new name (not editable). Make Editable AnimBlueprint: the same built as an AnimBlueprint of this project at ") +
		(MyName.IsEmpty() ? FString(TEXT("Folder/Name")) : PackagePath()) + TEXT(" (its graphs, states and rules as nodes, to edit), then Cook For Game writes it as the container. (Without its Control Rig: this editor cannot make the game's rig.)"));
	About = FString::Join(Lines, TEXT("\n"));
}

// ------------------------------------------------------------------------------------------------
// The window
// ------------------------------------------------------------------------------------------------
class SEndAnimBlueprintMaker : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SEndAnimBlueprintMaker) {}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs)
	{
		Form.Reset(NewObject<UEndAnimBlueprintMaker>(GetTransientPackage(), NAME_None, RF_Transient));
		Form->Template = FirstTemplateLabel();
		Form->GameDirectory.Path = TEXT("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY VII REBIRTH");
		FPropertyEditorModule& PropertyEditor = FModuleManager::LoadModuleChecked<FPropertyEditorModule>(TEXT("PropertyEditor"));
		FDetailsViewArgs Args;
		Args.bAllowSearch = false;
		Args.bHideSelectionTip = true;
		Args.NameAreaSettings = FDetailsViewArgs::HideNameArea;
		Details = PropertyEditor.CreateDetailView(Args);
		Details->SetObject(Form.Get());
		Details->OnFinishedChangingProperties().AddSP(this, &SEndAnimBlueprintMaker::OnFormChanged);
		Form->Describe();
		Report = LOCTEXT("Start", "Pick the character's skeleton (or right-click a Skeleton or Skeletal Mesh in the Content Browser > Make a Rebirth AnimBlueprint...), then Make AnimBlueprint. It is one of the game's own AnimBlueprints made for that skeleton, written as a ~mods container.");

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
				+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("Make", "Make AnimBlueprint"), LOCTEXT("MakeTip", "Make the AnimBlueprint for the skeleton and write its container (and install it into ~mods: close the game first)."), &SEndAnimBlueprintMaker::OnMake)]
				+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("MakeEditable", "Make Editable AnimBlueprint"), LOCTEXT("MakeEditableTip", "Build the template as an AnimBlueprint of this project (Folder/Name) for the skeleton: its AnimGraph, state machine, states and transition rules as nodes you can edit. Compiled and saved; then Cook For Game."), &SEndAnimBlueprintMaker::OnMakeEditable)]
				+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("Cook", "Cook For Game"), LOCTEXT("CookTip", "Cook the project's AnimBlueprint at Folder/Name (an editable one) for the game and write it as the container (and install it into ~mods: close the game first)."), &SEndAnimBlueprintMaker::OnCookEditable)]
				+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("Copy", "Copy Class Path"), LOCTEXT("CopyTip", "Copy the AnimBlueprint's class path (for a form's \"anim_class\" or a skin's \"anim_blueprint\")."), &SEndAnimBlueprintMaker::OnCopy)]
				+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("Show", "Show Container"), LOCTEXT("ShowTip", "Open the folder the containers are written to (Tools\\RebirthSkelCompat\\abp\\out)."), &SEndAnimBlueprintMaker::OnShow)]
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
					.Text(this, &SEndAnimBlueprintMaker::GetReport)
				]
			]
		];
	}

	void Open(USkeleton* InSkeleton)
	{
		if (!Form.IsValid())
		{
			return;
		}
		if (InSkeleton)
		{
			Form->StartFrom(InSkeleton);
			SetReport(FString::Printf(TEXT("An AnimBlueprint for %s: check its name and template, then Make AnimBlueprint."), *InSkeleton->GetName()));
		}
		Refresh();
	}

private:
	TStrongObjectPtr<UEndAnimBlueprintMaker> Form;
	TSharedPtr<IDetailsView> Details;
	FText Report;

	TSharedRef<SWidget> MakeButton(const FText& Label, const FText& Tip, FReply (SEndAnimBlueprintMaker::*Handler)())
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

	void OnFormChanged(const FPropertyChangedEvent& Event)
	{
		const FName Member = Event.MemberProperty ? Event.MemberProperty->GetFName() : Event.GetPropertyName();
		if (Member == GET_MEMBER_NAME_CHECKED(UEndAnimBlueprintMaker, Skeleton))
		{
			Form->AnimClass.Empty();
		}
		Refresh();
	}

	FReply OnMake()
	{
		const FString Skeleton = Form->SkeletonPath();
		const FString MyName = Form->FinalName();
		if (Skeleton.IsEmpty())
		{
			SetReport(TEXT("Pick the character's skeleton first (Skeleton)."));
			return FReply::Handled();
		}
		if (!IsNameText(MyName))
		{
			SetReport(TEXT("The name may only have letters, digits and _ (Name)."));
			return FReply::Handled();
		}
		const FString Tool = FPaths::Combine(ToolDir(), TEXT("make_cacs_abp.py"));
		if (!FPaths::FileExists(Tool))
		{
			SetReport(TEXT("The AnimBlueprint Maker's tool is not installed: ") + Tool + TEXT(" (run Tools\\RebirthSkelCompat\\run_build_plugin118.cmd again)."));
			return FReply::Handled();
		}
		FString Dir = Form->Folder.TrimStartAndEnd();
		if (Dir.IsEmpty())
		{
			Dir = TEXT("/Game/BluePrint/Animation/Player");
		}
		const FString ResultFile = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("RebirthSkelCompat"), TEXT("abp_result.json")));
		IFileManager::Get().MakeDirectory(*FPaths::GetPath(ResultFile), true);
		IFileManager::Get().Delete(*ResultFile, false, true, true);
		FString Arguments = TEXT("--skeleton ") + Quoted(Skeleton) + TEXT(" --name ") + MyName + TEXT(" --folder ") + Quoted(Dir) +
							TEXT(" --template ") + Form->TemplateKey() + TEXT(" --control-rig ") + (Form->bKeepControlRig ? TEXT("keep") : TEXT("off")) +
							TEXT(" --out ") + Quoted(FPaths::Combine(ToolDir(), TEXT("out"))) + TEXT(" --result ") + Quoted(ResultFile);
		if (!Form->Container.TrimStartAndEnd().IsEmpty())
		{
			Arguments += TEXT(" --container ") + Form->Container.TrimStartAndEnd();
		}
		if (Form->bInstall)
		{
			Arguments += TEXT(" --install --mods-folder ") + Quoted(Form->ModsFolder.TrimStartAndEnd()) + TEXT(" --game ") +
						 Quoted(FPaths::ConvertRelativePathToFull(Form->GameDirectory.Path).Replace(TEXT("/"), TEXT("\\")));
		}
		int32 Code = -1;
		FString Text;
		if (!RunTool(Arguments, Code, Text))
		{
			SetReport(TEXT("Python did not start: the AnimBlueprint Maker runs Tools\\RebirthSkelCompat\\abp\\make_cacs_abp.py with Python 3 (the py launcher or python on the PATH, as the build scripts do)."));
			return FReply::Handled();
		}
		FString Json;
		TSharedPtr<FJsonObject> Result;
		if (FFileHelper::LoadFileToString(Json, *ResultFile))
		{
			TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Json);
			FJsonSerializer::Deserialize(Reader, Result);
		}
		bool bOk = false;
		if (Result.IsValid() && Result->TryGetBoolField(TEXT("ok"), bOk) && bOk)
		{
			Form->AnimClass = Result->GetStringField(TEXT("anim_class"));
		}
		SetReport(FString::Printf(TEXT("%s\n(exit code %d)"), *Text.TrimStartAndEnd(), Code));
		Refresh();
		return FReply::Handled();
	}

	// (editor 1.19) the template built as an AnimBlueprint of this project
	FReply OnMakeEditable()
	{
		const FString Skeleton = Form->SkeletonPath();
		const FString MyName = Form->FinalName();
		if (Skeleton.IsEmpty())
		{
			SetReport(TEXT("Pick the character's skeleton first (Skeleton)."));
			return FReply::Handled();
		}
		if (!IsNameText(MyName))
		{
			SetReport(TEXT("The name may only have letters, digits and _ (Name)."));
			return FReply::Handled();
		}
		const FString TemplateFile = RebirthAnimTemplate::TemplateFile(Form->TemplateKey());
		if (!FPaths::FileExists(TemplateFile))
		{
			SetReport(TEXT("The template is not installed: ") + TemplateFile + TEXT(" (run Tools\\RebirthSkelCompat\\run_build_editor119.cmd again)."));
			return FReply::Handled();
		}
		SetReport(TEXT("Making ") + Form->PackagePath() + TEXT("..."));
		UAnimBlueprint* Blueprint = nullptr;
		const RebirthAnimTemplate::FBuildReport Result = RebirthAnimTemplate::MakeEditableAnimBlueprint(TemplateFile, Skeleton, Form->PackagePath(), Form->bReplaceExisting, &Blueprint);
		if (Result.bOk)
		{
			Form->AnimClass = Result.AnimClass;
		}
		FString Text = Result.ToText();
		if (Result.bOk)
		{
			Text += TEXT("\nNext: edit it as you like, then Cook For Game (it writes the container") + FString(Form->bInstall ? TEXT(" and installs it") : TEXT("")) + TEXT(").");
		}
		SetReport(Text);
		if (Blueprint && Form->bOpenWhenMade && GEditor)
		{
			GEditor->GetEditorSubsystem<UAssetEditorSubsystem>()->OpenEditorForAsset(Blueprint);
		}
		Refresh();
		return FReply::Handled();
	}

	// (editor 1.19) the project's AnimBlueprint at Folder/Name cooked for the game, as the container
	FReply OnCookEditable()
	{
		const FString MyName = Form->FinalName();
		if (!IsNameText(MyName))
		{
			SetReport(TEXT("Pick the skeleton (or give a Name) first: the AnimBlueprint is Folder/Name."));
			return FReply::Handled();
		}
		const FString Package = Form->PackagePath();
		if (!FPackageName::DoesPackageExist(Package))
		{
			SetReport(TEXT("There is no ") + Package + TEXT(" in this project: Make Editable AnimBlueprint first."));
			return FReply::Handled();
		}
		const FString OutDir = FPaths::Combine(ToolDir(), TEXT("out"));
		const FString ContainerName = Form->ContainerName();
		const FString Json = RebirthAnimTemplate::CookToContainer({Package}, ContainerName, OutDir);
		TSharedPtr<FJsonObject> Result;
		TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Json);
		FJsonSerializer::Deserialize(Reader, Result);
		bool bOk = false;
		TArray<FString> Lines;
		if (Result.IsValid())
		{
			Result->TryGetBoolField(TEXT("ok"), bOk);
			const TArray<TSharedPtr<FJsonValue>>* Errors = nullptr;
			if (Result->TryGetArrayField(TEXT("errors"), Errors))
			{
				for (const TSharedPtr<FJsonValue>& Error : *Errors)
				{
					Lines.Add(TEXT("ERROR: ") + Error->AsString());
				}
			}
		}
		if (!bOk)
		{
			Lines.Insert(TEXT("NOT cooked:"), 0);
			SetReport(FString::Join(Lines, TEXT("\n")));
			return FReply::Handled();
		}
		Lines.Add(FString::Printf(TEXT("Cooked %s into %s.utoc/.ucas/.pak in %s"), *Package, *ContainerName, *OutDir));
		Form->AnimClass = Package + TEXT(".") + MyName + TEXT("_C");
		if (Form->bInstall)
		{
			const FString Mods = FPaths::Combine(FPaths::ConvertRelativePathToFull(Form->GameDirectory.Path), TEXT("End"), TEXT("Content"), TEXT("Paks"), TEXT("~mods"));
			if (FPlatformProcess::IsApplicationRunning(TEXT("ff7rebirth_.exe")) || FPlatformProcess::IsApplicationRunning(TEXT("ff7rebirth.exe")))
			{
				Lines.Add(TEXT("NOT INSTALLED: the game is running. Close it and Cook For Game again (or copy the three files from the out folder)."));
			}
			else if (!IFileManager::Get().DirectoryExists(*Mods))
			{
				Lines.Add(TEXT("NOT INSTALLED: the game's ~mods folder is not at ") + Mods + TEXT(" (Game Directory)."));
			}
			else
			{
				const FString Dest = Form->ModsFolder.TrimStartAndEnd().IsEmpty() ? Mods : FPaths::Combine(Mods, Form->ModsFolder.TrimStartAndEnd());
				IFileManager::Get().MakeDirectory(*Dest, true);
				bool bAll = true;
				for (const TCHAR* Extension : {TEXT(".utoc"), TEXT(".ucas"), TEXT(".pak")})
				{
					bAll &= IFileManager::Get().Copy(*FPaths::Combine(Dest, ContainerName + Extension), *FPaths::Combine(OutDir, ContainerName + Extension)) == COPY_OK;
				}
				Lines.Add(bAll ? TEXT("Installed into ") + Dest : TEXT("NOT all of it could be copied into ") + Dest);
			}
		}
		Lines.Add(TEXT("Its class (a form's \"anim_class\", a skin's \"anim_blueprint\"): ") + Form->AnimClass);
		SetReport(FString::Join(Lines, TEXT("\n")));
		Refresh();
		return FReply::Handled();
	}

	FReply OnCopy()
	{
		const FString Class = !Form->AnimClass.IsEmpty() ? Form->AnimClass : (Form->FinalName().IsEmpty() ? FString() : Form->PackagePath() + TEXT(".") + Form->FinalName() + TEXT("_C"));
		if (Class.IsEmpty())
		{
			SetReport(TEXT("Pick the skeleton first: the class path comes from its name."));
			return FReply::Handled();
		}
		FPlatformApplicationMisc::ClipboardCopy(*Class);
		SetReport(TEXT("Copied: ") + Class);
		return FReply::Handled();
	}

	FReply OnShow()
	{
		const FString Out = FPaths::Combine(ToolDir(), TEXT("out"));
		IFileManager::Get().MakeDirectory(*Out, true);
		FPlatformProcess::ExploreFolder(*Out);
		return FReply::Handled();
	}
};

// ------------------------------------------------------------------------------------------------
namespace RebirthSkelCompatEditor
{
const FName AnimBlueprintMakerTabName(TEXT("RebirthAnimBlueprintMaker"));

namespace AnimBlueprintMakerTab
{
TWeakPtr<SEndAnimBlueprintMaker> Current;
TWeakObjectPtr<USkeleton> PendingSkeleton;
}

TSharedRef<SDockTab> SpawnAnimBlueprintMakerTab(const FSpawnTabArgs& Args)
{
	TSharedRef<SEndAnimBlueprintMaker> Widget = SNew(SEndAnimBlueprintMaker);
	AnimBlueprintMakerTab::Current = Widget;
	Widget->Open(AnimBlueprintMakerTab::PendingSkeleton.Get());
	return SNew(SDockTab)
		.TabRole(ETabRole::NomadTab)
		.Label(LOCTEXT("TabLabel", "Rebirth AnimBlueprint Maker"))
		[
			Widget
		];
}

void OpenAnimBlueprintMakerTab(USkeleton* Skeleton)
{
	AnimBlueprintMakerTab::PendingSkeleton = Skeleton;
	const bool bHad = AnimBlueprintMakerTab::Current.IsValid();
	FGlobalTabmanager::Get()->TryInvokeTab(FTabId(AnimBlueprintMakerTabName));
	if (TSharedPtr<SEndAnimBlueprintMaker> Widget = AnimBlueprintMakerTab::Current.Pin(); Widget.IsValid() && bHad)
	{
		Widget->Open(Skeleton);   // (a tab spawned just now has been opened on it already)
	}
	AnimBlueprintMakerTab::PendingSkeleton.Reset();
}
} // namespace RebirthSkelCompatEditor

#undef LOCTEXT_NAMESPACE
