// RebirthSkelCompat Weapon Blueprint Maker (editor 1.20): a weapon Blueprint for the game, made from one of the game's
// weapon blueprints for a model of this project, in a window of its own.
#include "EndWeaponBlueprintMaker.h"

#include "Editor.h"
#include "Engine/Blueprint.h"
#include "Engine/SkeletalMesh.h"
#include "EndWeaponBlueprintTemplate.h"
#include "Framework/Docking/TabManager.h"
#include "HAL/PlatformApplicationMisc.h"
#include "IDetailsView.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "PropertyEditorModule.h"
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

#define LOCTEXT_NAMESPACE "RebirthWeaponBlueprintMaker"

// Named, not anonymous: the module may be compiled as one unity file with the other sources.
namespace RebirthWeaponBlueprintMakerUtil
{
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

// The first player's weapon: the default template.
FString FirstTemplateLabel()
{
	const TArray<RebirthWeaponTemplate::FTemplateInfo> List = RebirthWeaponTemplate::Templates();
	return List.Num() ? List[0].Label : FString();
}
} // namespace RebirthWeaponBlueprintMakerUtil

// ------------------------------------------------------------------------------------------------
// The form
// ------------------------------------------------------------------------------------------------
TArray<FString> UEndWeaponBlueprintMaker::GetTemplateOptions() const
{
	TArray<FString> Out;
	for (const RebirthWeaponTemplate::FTemplateInfo& Choice : RebirthWeaponTemplate::Templates())
	{
		Out.Add(Choice.Label);
	}
	return Out;
}

FString UEndWeaponBlueprintMaker::TemplateKey() const
{
	RebirthWeaponTemplate::FTemplateInfo Info;
	if (RebirthWeaponTemplate::FindTemplate(Template.IsEmpty() ? RebirthWeaponBlueprintMakerUtil::FirstTemplateLabel() : Template, Info))
	{
		return Info.Key;
	}
	return FString();
}

FString UEndWeaponBlueprintMaker::MeshPath() const
{
	return Mesh.IsNull() ? FString() : Mesh.ToSoftObjectPath().ToString();
}

FString UEndWeaponBlueprintMaker::FinalName() const
{
	const FString Mine = Name.TrimStartAndEnd();
	return Mine.IsEmpty() ? TemplateKey() : Mine;
}

FString UEndWeaponBlueprintMaker::FinalFolder() const
{
	FString Dir = Folder.TrimStartAndEnd().Replace(TEXT("\\"), TEXT("/"));
	if (Dir.IsEmpty())
	{
		Dir = RebirthWeaponTemplate::DefaultFolder(MeshPath());
	}
	while (Dir.EndsWith(TEXT("/")))
	{
		Dir.LeftChopInline(1);
	}
	if (!Dir.StartsWith(TEXT("/")))
	{
		Dir = TEXT("/") + Dir;
	}
	return Dir;
}

FString UEndWeaponBlueprintMaker::PackagePath() const
{
	return FinalFolder() + TEXT("/") + FinalName();
}

void UEndWeaponBlueprintMaker::StartFrom(USkeletalMesh* InMesh)
{
	if (InMesh)
	{
		Mesh = InMesh;
		Name.Empty();
		Folder.Empty();
		WeaponClass.Empty();
	}
	Describe();
}

void UEndWeaponBlueprintMaker::Describe()
{
	TArray<FString> Lines;
	const TArray<RebirthWeaponTemplate::FTemplateInfo> List = RebirthWeaponTemplate::Templates();
	if (List.Num() == 0)
	{
		Lines.Add(TEXT("The weapon templates are not installed: ") + RebirthWeaponTemplate::TemplatesFile());
	}
	if (Mesh.IsNull())
	{
		Lines.Add(TEXT("Mesh: pick the weapon's model (or right-click a Skeletal Mesh > Make a Rebirth Weapon Blueprint...)"));
	}
	else
	{
		Lines.Add(TEXT("Mesh: ") + MeshPath() + TEXT(" (cooked with the Blueprint into the skin that holds it)"));
	}
	RebirthWeaponTemplate::FTemplateInfo Info;
	if (RebirthWeaponTemplate::FindTemplate(Template.IsEmpty() ? RebirthWeaponBlueprintMakerUtil::FirstTemplateLabel() : Template, Info))
	{
		Lines.Add(TEXT("Made from: ") + Info.Label + TEXT(" (") + Info.Package + TEXT("; its parent class ") + Info.Parent + TEXT(")"));
	}
	const FString MyName = FinalName();
	if (!MyName.IsEmpty())
	{
		Lines.Add(RebirthWeaponBlueprintMakerUtil::IsNameText(MyName) ? TEXT("Blueprint: ") + PackagePath() : TEXT("Name: \"") + MyName + TEXT("\" may only have letters, digits and _"));
		Lines.Add(TEXT("Its class (a skin's Weapon): ") + PackagePath() + TEXT(".") + MyName + TEXT("_C"));
	}
	Lines.Add(TEXT("It is a Blueprint of this project like any other: add components (effects, lights), change its values, then build the skin whose Weapon it is (the skin build cooks it with its model, materials and textures)."));
	About = FString::Join(Lines, TEXT("\n"));
}

// ------------------------------------------------------------------------------------------------
// The window
// ------------------------------------------------------------------------------------------------
class SEndWeaponBlueprintMaker : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SEndWeaponBlueprintMaker) {}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs)
	{
		Form.Reset(NewObject<UEndWeaponBlueprintMaker>(GetTransientPackage(), NAME_None, RF_Transient));
		Form->Template = RebirthWeaponBlueprintMakerUtil::FirstTemplateLabel();
		FPropertyEditorModule& PropertyEditor = FModuleManager::LoadModuleChecked<FPropertyEditorModule>(TEXT("PropertyEditor"));
		FDetailsViewArgs Args;
		Args.bAllowSearch = false;
		Args.bHideSelectionTip = true;
		Args.NameAreaSettings = FDetailsViewArgs::HideNameArea;
		Details = PropertyEditor.CreateDetailView(Args);
		Details->SetObject(Form.Get());
		Details->OnFinishedChangingProperties().AddSP(this, &SEndWeaponBlueprintMaker::OnFormChanged);
		Form->Describe();
		Report = LOCTEXT("Start", "Pick the weapon's model (or right-click a Skeletal Mesh in the Content Browser > Make a Rebirth Weapon Blueprint...) and the game's weapon it is made from, then Make Weapon Blueprint. It is a real Blueprint of this project: a skin's Weapon names its class.");

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
				+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("Make", "Make Weapon Blueprint"), LOCTEXT("MakeTip", "Make the weapon Blueprint (Folder/Name) from the template, holding the model: compiled and saved."), &SEndWeaponBlueprintMaker::OnMake)]
				+ SWrapBox::Slot().Padding(2.f)[MakeButton(LOCTEXT("Copy", "Copy Class Path"), LOCTEXT("CopyTip", "Copy the Blueprint's class path (for a skin's Weapon)."), &SEndWeaponBlueprintMaker::OnCopy)]
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
					.Text(this, &SEndWeaponBlueprintMaker::GetReport)
				]
			]
		];
	}

	void Open(USkeletalMesh* InMesh)
	{
		if (!Form.IsValid())
		{
			return;
		}
		if (InMesh)
		{
			Form->StartFrom(InMesh);
			SetReport(FString::Printf(TEXT("A weapon Blueprint holding %s: check its template, name and folder, then Make Weapon Blueprint."), *InMesh->GetName()));
		}
		Refresh();
	}

private:
	TStrongObjectPtr<UEndWeaponBlueprintMaker> Form;
	TSharedPtr<IDetailsView> Details;
	FText Report;

	TSharedRef<SWidget> MakeButton(const FText& Label, const FText& Tip, FReply (SEndWeaponBlueprintMaker::*Handler)())
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
		if (Member == GET_MEMBER_NAME_CHECKED(UEndWeaponBlueprintMaker, Mesh) || Member == GET_MEMBER_NAME_CHECKED(UEndWeaponBlueprintMaker, Template))
		{
			Form->WeaponClass.Empty();
		}
		Refresh();
	}

	FReply OnMake()
	{
		const FString MeshPath = Form->MeshPath();
		const FString Key = Form->TemplateKey();
		const FString MyName = Form->FinalName();
		if (MeshPath.IsEmpty())
		{
			SetReport(TEXT("Pick the weapon's model first (Mesh)."));
			return FReply::Handled();
		}
		if (Key.IsEmpty())
		{
			SetReport(TEXT("Pick the game's weapon it is made from (Template). The templates: ") + RebirthWeaponTemplate::TemplatesFile());
			return FReply::Handled();
		}
		if (!RebirthWeaponBlueprintMakerUtil::IsNameText(MyName))
		{
			SetReport(TEXT("The name may only have letters, digits and _ (Name)."));
			return FReply::Handled();
		}
		UBlueprint* Blueprint = nullptr;
		const RebirthWeaponTemplate::FBuildReport Result = RebirthWeaponTemplate::MakeWeaponBlueprint(Key, MeshPath, Form->PackagePath(), Form->bReplaceExisting, &Blueprint);
		if (Result.bOk)
		{
			Form->WeaponClass = Result.WeaponClass;
		}
		FString Text = Result.ToText();
		if (Result.bOk)
		{
			Text += TEXT("\nNext: put its class in a skin's Weapon (Copy Class Path) and build the skin; edit the Blueprint as you like first.");
		}
		SetReport(Text);
		if (Blueprint && Result.bOk && Form->bOpenWhenMade && GEditor)
		{
			GEditor->GetEditorSubsystem<UAssetEditorSubsystem>()->OpenEditorForAsset(Blueprint);
		}
		Refresh();
		return FReply::Handled();
	}

	FReply OnCopy()
	{
		const FString Class = !Form->WeaponClass.IsEmpty() ? Form->WeaponClass : (Form->FinalName().IsEmpty() ? FString() : Form->PackagePath() + TEXT(".") + Form->FinalName() + TEXT("_C"));
		if (Class.IsEmpty())
		{
			SetReport(TEXT("Pick the template first: the class path comes from the Blueprint's name."));
			return FReply::Handled();
		}
		FPlatformApplicationMisc::ClipboardCopy(*Class);
		SetReport(TEXT("Copied: ") + Class);
		return FReply::Handled();
	}
};

// ------------------------------------------------------------------------------------------------
namespace RebirthSkelCompatEditor
{
const FName WeaponBlueprintMakerTabName(TEXT("RebirthWeaponBlueprintMaker"));

namespace WeaponBlueprintMakerTab
{
TWeakPtr<SEndWeaponBlueprintMaker> Current;
TWeakObjectPtr<USkeletalMesh> PendingMesh;
}

TSharedRef<SDockTab> SpawnWeaponBlueprintMakerTab(const FSpawnTabArgs& Args)
{
	TSharedRef<SEndWeaponBlueprintMaker> Widget = SNew(SEndWeaponBlueprintMaker);
	WeaponBlueprintMakerTab::Current = Widget;
	Widget->Open(WeaponBlueprintMakerTab::PendingMesh.Get());
	return SNew(SDockTab)
		.TabRole(ETabRole::NomadTab)
		.Label(LOCTEXT("TabLabel", "Rebirth Weapon Blueprint Maker"))
		[
			Widget
		];
}

void OpenWeaponBlueprintMakerTab(USkeletalMesh* Mesh)
{
	WeaponBlueprintMakerTab::PendingMesh = Mesh;
	const bool bHad = WeaponBlueprintMakerTab::Current.IsValid();
	FGlobalTabmanager::Get()->TryInvokeTab(FTabId(WeaponBlueprintMakerTabName));
	if (TSharedPtr<SEndWeaponBlueprintMaker> Widget = WeaponBlueprintMakerTab::Current.Pin(); Widget.IsValid() && bHad)
	{
		Widget->Open(Mesh);   // (a tab spawned just now has been opened on it already)
	}
	WeaponBlueprintMakerTab::PendingMesh.Reset();
}
} // namespace RebirthSkelCompatEditor

#undef LOCTEXT_NAMESPACE
