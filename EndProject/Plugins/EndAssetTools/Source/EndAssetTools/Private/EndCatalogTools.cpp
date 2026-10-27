#include "EndCatalogTools.h"

#include "CoreMinimal.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimBoneCompressionSettings.h"
#include "Animation/AnimCurveCompressionSettings.h"
#include "Animation/AnimBoneCompressionCodec.h"
#include "Animation/AnimCurveCompressionCodec.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "Animation/AnimNotifies/AnimNotifyState.h"
#include "Animation/AnimTypes.h"
#include "AssetRegistryModule.h"
#include "ContentBrowserModule.h"
#include "Dom/JsonObject.h"
#include "Editor.h"
#include "Framework/Docking/TabManager.h"
#include "HAL/PlatformApplicationMisc.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "IContentBrowserSingleton.h"
#include "IDetailsView.h"
#include "Interfaces/IPluginManager.h"
#include "JsonObjectConverter.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "PropertyEditorModule.h"
#include "ScopedTransaction.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UObject/GCObject.h"
#include "UObject/Package.h"
#include "UObject/UnrealType.h"
#include "UObject/StrongObjectPtr.h"
#include "Widgets/Docking/SDockTab.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SComboBox.h"
#include "Widgets/Input/SNumericEntryBox.h"
#include "Widgets/Input/SSearchBox.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSplitter.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Views/SListView.h"

#define LOCTEXT_NAMESPACE "EndAssetCatalogTools"

namespace
{
const FName CatalogTabName(TEXT("EndAssetTools.Catalog"));
struct FCatalogEntry
{
    FString Category, Name, Path, Search, Description;
    TSharedPtr<FJsonObject> Json;
};
using FEntryPtr=TSharedPtr<FCatalogEntry>;

FString JsonText(const TSharedPtr<FJsonObject>& Json)
{
    FString Text;
    if (Json.IsValid())
    {
        const TSharedRef<TJsonWriter<>> Writer=TJsonWriterFactory<>::Create(&Text);
        FJsonSerializer::Serialize(Json.ToSharedRef(),Writer);
    }
    return Text;
}
FString JsonString(const TSharedPtr<FJsonObject>& Json,const TCHAR* Key)
{
    FString Result;
    if (Json.IsValid()) Json->TryGetStringField(Key,Result);
    return Result;
}
bool IsEditableAuthored(UObject* Object)
{
    if (!IsValid(Object) || Object->HasAnyFlags(RF_ClassDefaultObject|RF_ArchetypeObject)) return false;
    const UPackage* Package=Object->GetOutermost();
    return Package && !Package->HasAnyPackageFlags(PKG_Cooked|PKG_FilterEditorOnly) && !Package->bIsCookedForEditor;
}
bool CanEditSequence(UAnimSequence* Sequence)
{
    // UAnimSequence transaction loading unconditionally validates both settings
    // objects before looking up codecs, even when the animation has no tracks.
    const auto Loaded=[](const UObject* Object){return IsValid(Object)&&!Object->HasAnyFlags(RF_NeedLoad|RF_NeedPostLoad);};
    if(!IsEditableAuthored(Sequence)||!Loaded(Sequence->BoneCompressionSettings)||!Loaded(Sequence->CurveCompressionSettings))return false;
    if(!Loaded(Sequence->CurveCompressionSettings->Codec)||!Loaded(Sequence->CompressedData.CurveCompressionCodec))return false;
    if(Sequence->CompressedData.BoneCompressionCodec&&(!Loaded(Sequence->CompressedData.BoneCompressionCodec)||!Sequence->CompressedData.CompressedDataStructure))return false;
    return true;
}
bool RelinkNestedEvents(FProperty* Property,void* Value,UObject* CloneRoot,UAnimSequence* Source,UAnimSequence* Target,int32 Depth,int32& Budget,TSet<UObject*>& Visited)
{
    if(Depth>24||--Budget<0)return false;
    if(FStructProperty* Struct=CastField<FStructProperty>(Property))
    {
        if(Struct->Struct==FAnimNotifyEvent::StaticStruct())
        {
            FAnimNotifyEvent& Event=*static_cast<FAnimNotifyEvent*>(Value);
            if(Event.GetLinkedSequence()==Source||Event.GetLinkedSequence()==Target)
            {
                const float Time=Event.GetTime(),Duration=Event.GetDuration();
                if(!FMath::IsFinite(Time)||!FMath::IsFinite(Duration)||Time<0||Duration<0||Time+Duration>Target->SequenceLength)return false;
                Event.Link(Target,Time);Event.TriggerTimeOffset=GetTriggerTimeOffsetForType(Target->CalculateOffsetForNotify(Time));
                if(Event.NotifyStateClass){Event.EndLink.Link(Target,Time+Duration);Event.SetDuration(Duration);Event.EndTriggerTimeOffset=GetTriggerTimeOffsetForType(Target->CalculateOffsetForNotify(Time+Duration));}
            }
            return true;
        }
        for(TFieldIterator<FProperty> It(Struct->Struct);It;++It)for(int32 I=0;I<It->ArrayDim;++I)if(!RelinkNestedEvents(*It,It->ContainerPtrToValuePtr<void>(Value,I),CloneRoot,Source,Target,Depth+1,Budget,Visited))return false;
    }
    else if(FArrayProperty* Array=CastField<FArrayProperty>(Property))
    {
        FScriptArrayHelper Helper(Array,Value);for(int32 I=0;I<Helper.Num();++I)if(!RelinkNestedEvents(Array->Inner,Helper.GetRawPtr(I),CloneRoot,Source,Target,Depth+1,Budget,Visited))return false;
    }
    else if(FMapProperty* Map=CastField<FMapProperty>(Property))
    {
        FScriptMapHelper Helper(Map,Value);for(int32 I=0;I<Helper.GetMaxIndex();++I)if(Helper.IsValidIndex(I))
            if(!RelinkNestedEvents(Map->KeyProp,Helper.GetKeyPtr(I),CloneRoot,Source,Target,Depth+1,Budget,Visited)||!RelinkNestedEvents(Map->ValueProp,Helper.GetValuePtr(I),CloneRoot,Source,Target,Depth+1,Budget,Visited))return false;
        Helper.Rehash();
    }
    else if(FSetProperty* Set=CastField<FSetProperty>(Property))
    {
        FScriptSetHelper Helper(Set,Value);for(int32 I=0;I<Helper.GetMaxIndex();++I)if(Helper.IsValidIndex(I)&&!RelinkNestedEvents(Set->ElementProp,Helper.GetElementPtr(I),CloneRoot,Source,Target,Depth+1,Budget,Visited))return false;
        Helper.Rehash();
    }
    else if(FObjectProperty* ObjectProperty=CastField<FObjectProperty>(Property))
    {
        UObject* Object=ObjectProperty->GetObjectPropertyValue(Value);
        if(Object&&Object->IsIn(CloneRoot)&&!Visited.Contains(Object))
        {
            Visited.Add(Object);for(TFieldIterator<FProperty> It(Object->GetClass());It;++It)for(int32 I=0;I<It->ArrayDim;++I)if(!RelinkNestedEvents(*It,It->ContainerPtrToValuePtr<void>(Object,I),CloneRoot,Source,Target,Depth+1,Budget,Visited))return false;
        }
    }
    return true;
}
UObject* CopyNotifyObject(UObject* Original,UAnimSequence* Source,UAnimSequence* Target)
{
    if(!Original)return nullptr;
    FObjectDuplicationParameters Params(Original,Target);Params.DuplicationSeed.Add(Source,Target);Params.ApplyFlags|=RF_Transactional;
    UObject* Clone=StaticDuplicateObjectEx(Params);if(!Clone)return nullptr;
    TSet<UObject*> Visited;Visited.Add(Clone);int32 Budget=32768;
    for(TFieldIterator<FProperty> It(Clone->GetClass());It;++It)for(int32 I=0;I<It->ArrayDim;++I)
        if(!RelinkNestedEvents(*It,It->ContainerPtrToValuePtr<void>(Clone,I),Clone,Source,Target,0,Budget,Visited))return nullptr;
    return Clone;
}
TArray<UObject*> SelectedAssets()
{
    TArray<FAssetData> Selected;
    FModuleManager::LoadModuleChecked<FContentBrowserModule>(TEXT("ContentBrowser")).Get().GetSelectedAssets(Selected);
    TArray<UObject*> Result;
    // Do not load unrelated cooked Blueprints or arbitrary object classes from a
    // multi-selection. These tools consume animation assets and EndAnimSet only.
    for(const FAssetData& Asset:Selected)
    {
        const FName Class=Asset.AssetClass;
        if(Class!=TEXT("AnimSequence")&&Class!=TEXT("AnimComposite")&&Class!=TEXT("AnimMontage")&&Class!=TEXT("BlendSpace")&&Class!=TEXT("BlendSpace1D")&&Class!=TEXT("AimOffsetBlendSpace")&&Class!=TEXT("AimOffsetBlendSpace1D")&&Class!=TEXT("EndAnimSet"))continue;
        if(UObject* Object=Asset.GetAsset()) Result.Add(Object);
    }
    return Result;
}

class SEndCatalogTools final : public SCompoundWidget,public FGCObject
{
public:
    SLATE_BEGIN_ARGS(SEndCatalogTools) {} SLATE_END_ARGS()
    void Construct(const FArguments&)
    {
        Categories.Add(MakeShared<FString>(TEXT("All")));
        Categories.Add(MakeShared<FString>(TEXT("Notifies")));
        Categories.Add(MakeShared<FString>(TEXT("Skeletons")));
        Categories.Add(MakeShared<FString>(TEXT("Effect parameters")));
        SelectedCategory=Categories[0];
        LoadCatalogs();
        FDetailsViewArgs DetailsArgs;
        DetailsArgs.bAllowSearch=true;
        DetailsArgs.bHideSelectionTip=true;
        DetailsArgs.bLockable=false;
        Details=FModuleManager::LoadModuleChecked<FPropertyEditorModule>(TEXT("PropertyEditor")).CreateDetailView(DetailsArgs);
        Details->SetIsPropertyEditingEnabledDelegate(FIsPropertyEditingEnabled::CreateLambda([this](){return CanEditSequence(TargetSequence)&&IsCurrentNotify(EditedNotify);}));
        ChildSlot
        [
            SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight().Padding(6)
            [SNew(STextBlock).Text(LOCTEXT("Intro","FFVII Rebirth Asset Tools — search original notify profiles, skeleton topology and observed effect parameters. Pin an authored sequence or EndAnimSet below to edit; cooked originals remain protected.")).AutoWrapText(true)]
            +SVerticalBox::Slot().AutoHeight().Padding(6)
            [SNew(SHorizontalBox)
                +SHorizontalBox::Slot().AutoWidth().Padding(0,0,8,0)
                [SNew(SComboBox<TSharedPtr<FString>>).OptionsSource(&Categories).InitiallySelectedItem(SelectedCategory)
                    .OnGenerateWidget_Lambda([](TSharedPtr<FString> Item){return SNew(STextBlock).Text(FText::FromString(*Item));})
                    .OnSelectionChanged_Lambda([this](TSharedPtr<FString> Item,ESelectInfo::Type){SelectedCategory=Item;Filter();})
                    [SNew(STextBlock).Text_Lambda([this](){return FText::FromString(*SelectedCategory);})]]
                +SHorizontalBox::Slot().FillWidth(1)
                [SNew(SSearchBox).HintText(LOCTEXT("Search","Search class, property, effect path or bone name"))
                    .OnTextChanged_Lambda([this](const FText& Text){Search=Text.ToString();Filter();})]
                +SHorizontalBox::Slot().AutoWidth().Padding(8,0,0,0)
                [SNew(SButton).Text(LOCTEXT("CopyEntry","Copy selected JSON/path")).OnClicked(this,&SEndCatalogTools::CopySelected)]
            ]
            +SVerticalBox::Slot().FillHeight(1).Padding(6)
            [SNew(SSplitter)
                +SSplitter::Slot().Value(.4f)
                [SAssignNew(List,SListView<FEntryPtr>).ListItemsSource(&Visible)
                    .OnGenerateRow_Lambda([](FEntryPtr Entry,const TSharedRef<STableViewBase>& Owner)
                    {return SNew(STableRow<FEntryPtr>,Owner)[SNew(STextBlock).Text(FText::FromString(Entry->Category+TEXT("  ")+Entry->Name)).ToolTipText(FText::FromString(Entry->Path))];})
                    .OnSelectionChanged_Lambda([this](FEntryPtr Entry,ESelectInfo::Type){Selected=Entry;})]
                +SSplitter::Slot().Value(.6f)
                [SNew(SScrollBox)+SScrollBox::Slot()[SNew(STextBlock).Text_Lambda([this](){return FText::FromString(Selected.IsValid()?Selected->Description:TEXT("Choose a catalog entry. Imported profiles describe observed data and native types; they do not prove every game-side behavior."));}).AutoWrapText(true)]]
            ]
            +SVerticalBox::Slot().AutoHeight().Padding(6)
            [SNew(SHorizontalBox)
                +SHorizontalBox::Slot().AutoWidth().Padding(0,0,6,0)[SNew(SButton).Text(LOCTEXT("PinSequence","Use selected sequence")).OnClicked(this,&SEndCatalogTools::PinSequence)]
                +SHorizontalBox::Slot().AutoWidth().Padding(0,0,6,0)[SNew(SButton).Text(LOCTEXT("AddNotify","Add catalog notify")).OnClicked(this,&SEndCatalogTools::AddNotify)]
                +SHorizontalBox::Slot().AutoWidth().Padding(0,0,6,0)[SNew(SButton).Text(LOCTEXT("CopyNotifies","Copy notifies from selected sequence")).OnClicked(this,&SEndCatalogTools::CopyNotifies)]
                +SHorizontalBox::Slot().AutoWidth().Padding(0,0,6,0)[SNew(STextBlock).Text(LOCTEXT("Time","Time (s)"))]
                +SHorizontalBox::Slot().AutoWidth()[SNew(SNumericEntryBox<float>).MinDesiredValueWidth(70).MinValue(0).Value_Lambda([this](){return TOptional<float>(NotifyTime);}).OnValueChanged_Lambda([this](float Value){NotifyTime=Value;})]
                +SHorizontalBox::Slot().AutoWidth().Padding(8,0,6,0)[SNew(STextBlock).Text(LOCTEXT("Duration","Duration (s)"))]
                +SHorizontalBox::Slot().AutoWidth()[SNew(SNumericEntryBox<float>).MinDesiredValueWidth(70).MinValue(0).Value_Lambda([this](){return TOptional<float>(NotifyDuration);}).OnValueChanged_Lambda([this](float Value){NotifyDuration=Value;})]
                +SHorizontalBox::Slot().AutoWidth().Padding(8,0,0,0)[SNew(SButton).Text(LOCTEXT("LastNotify","Edit last notify")).OnClicked(this,&SEndCatalogTools::EditLastNotify)]
                +SHorizontalBox::Slot().AutoWidth().Padding(8,0,0,0)[SNew(SButton).Text(LOCTEXT("NotifyPlan","Export notify import plan")).OnClicked(this,&SEndCatalogTools::ExportNotifyPlan)]
            ]
            +SVerticalBox::Slot().FillHeight(.55f).Padding(6)[Details.ToSharedRef()]
            +SVerticalBox::Slot().AutoHeight().Padding(6)
            [SNew(SHorizontalBox)
                +SHorizontalBox::Slot().AutoWidth().Padding(0,0,6,0)[SNew(SButton).Text(LOCTEXT("PinSet","Use selected EndAnimSet")).OnClicked(this,&SEndCatalogTools::PinAnimSet)]
                +SHorizontalBox::Slot().AutoWidth().Padding(0,0,6,0)[SNew(SButton).Text(LOCTEXT("PlanSet","Export selected-animation import plan")).OnClicked(this,&SEndCatalogTools::ExportAnimSetPlan)]
                +SHorizontalBox::Slot().AutoWidth()[SNew(SButton).Text(LOCTEXT("ImportSet","Add selected animations to authored set")).OnClicked(this,&SEndCatalogTools::ImportAnimSet)]
            ]
            +SVerticalBox::Slot().AutoHeight().Padding(6)[SNew(STextBlock).Text_Lambda([this](){return FText::FromString(Status);}).AutoWrapText(true)]
        ];
        Filter();
    }
    virtual void AddReferencedObjects(FReferenceCollector& Collector) override
    {
        Collector.AddReferencedObject(TargetSequence);
        Collector.AddReferencedObject(EditedNotify);
        Collector.AddReferencedObject(TargetAnimSet);
    }
    virtual FString GetReferencerName()const override{return TEXT("SEndCatalogTools");}
    TSharedRef<FJsonObject> RunOwnedSelfTest()
    {
        const TSharedRef<FJsonObject> Report=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Checks;bool Passed=true;
        auto Check=[&](const TCHAR* Name,bool Value){const TSharedRef<FJsonObject> Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("name"),Name);Row->SetBoolField(TEXT("passed"),Value);Checks.Add(MakeShared<FJsonValueObject>(Row));Passed&=Value;};
        int32 NotifyCount=0,SkeletonCount=0,EffectCount=0;for(const FEntryPtr& Entry:Entries){NotifyCount+=Entry->Category==TEXT("Notifies");SkeletonCount+=Entry->Category==TEXT("Skeletons");EffectCount+=Entry->Category==TEXT("Effect parameters");}
        Report->SetNumberField(TEXT("notify_classes"),NotifyCount);Report->SetNumberField(TEXT("skeletons"),SkeletonCount);Report->SetNumberField(TEXT("effect_prototypes"),EffectCount);
        Check(TEXT("exact_catalog_counts"),NotifyCount==406&&SkeletonCount==323&&EffectCount==770);
        Check(TEXT("owned_slate_widget_constructed"),Details.IsValid()&&List.IsValid());
        TStrongObjectPtr<UAnimSequence> Source(NewObject<UAnimSequence>(GetTransientPackage(),NAME_None,RF_Transient|RF_Transactional));
        TStrongObjectPtr<UAnimSequence> Target(NewObject<UAnimSequence>(GetTransientPackage(),NAME_None,RF_Transient|RF_Transactional));
        for(UAnimSequence* Sequence:{Source.Get(),Target.Get()})
        {
            Sequence->BoneCompressionSettings=NewObject<UAnimBoneCompressionSettings>(Sequence,NAME_None,RF_Transient);
            Sequence->CurveCompressionSettings=NewObject<UAnimCurveCompressionSettings>(Sequence,NAME_None,RF_Transient);
            Sequence->CompressedData.CurveCompressionCodec=Sequence->CurveCompressionSettings->Codec;
        }
        Check(TEXT("native_transaction_compression_settings_initialized"),CanEditSequence(Source.Get())&&CanEditSequence(Target.Get())&&Source->CompressedData.CurveCompressionCodec&&Target->CompressedData.CurveCompressionCodec);
        Source->SequenceLength=2;Target->SequenceLength=3;TargetSequence=Source.Get();NotifyTime=.25f;NotifyDuration=.5f;
        for(const FString& Name:{FString(TEXT("AnimNotify_PlaySound")),FString(TEXT("AnimNotifyState_TimedParticleEffect"))})
        {
            Selected=nullptr;for(const FEntryPtr& Entry:Entries)if(Entry->Category==TEXT("Notifies")&&Entry->Name==Name){Selected=Entry;break;}
            const int32 Before=Source->Notifies.Num();AddNotify();const FString CheckName=TEXT("native_add_")+Name;Check(*CheckName,Source->Notifies.Num()==Before+1);NotifyTime=.75f;
        }
        bool NativeEvents=Source->Notifies.Num()==2;
        if(NativeEvents)
        {
            const FAnimNotifyEvent& Single=Source->Notifies[0];const FAnimNotifyEvent& State=Source->Notifies[1];
            NativeEvents=Single.Notify&&State.NotifyStateClass&&Single.Notify->GetOuter()==Source.Get()&&State.NotifyStateClass->GetOuter()==Source.Get()&&FMath::IsNearlyEqual(Single.GetTime(),.25f)&&FMath::IsNearlyEqual(State.GetTime(),.75f)&&FMath::IsNearlyEqual(State.GetDuration(),.5f)&&FMath::IsNearlyEqual(State.EndLink.GetTime(),1.25f);
        }
        Check(TEXT("native_notify_objects_timing_state_end_link"),NativeEvents);
        TargetSequence=Target.Get();CopyNotifiesFrom(Source.Get());
        bool CopyPassed=Target->Notifies.Num()==Source->Notifies.Num()&&Source->Notifies.Num()==2;
        if(CopyPassed)for(int32 Index=0;Index<Source->Notifies.Num();++Index)
        {
            const FAnimNotifyEvent& A=Source->Notifies[Index];const FAnimNotifyEvent& B=Target->Notifies[Index];
            UObject* AO=A.Notify?static_cast<UObject*>(A.Notify):static_cast<UObject*>(A.NotifyStateClass);UObject* BO=B.Notify?static_cast<UObject*>(B.Notify):static_cast<UObject*>(B.NotifyStateClass);
            CopyPassed&=AO&&BO&&AO!=BO&&AO->GetClass()==BO->GetClass()&&BO->GetOuter()==Target.Get()&&FMath::IsNearlyEqual(A.GetTime(),B.GetTime())&&FMath::IsNearlyEqual(A.GetDuration(),B.GetDuration());
        }
        Check(TEXT("native_copy_distinct_objects_equal_classes_times_durations"),CopyPassed);
        if(Target->Notifies.Num())EditedNotify=Target->Notifies.Last().Notify?static_cast<UObject*>(Target->Notifies.Last().Notify):static_cast<UObject*>(Target->Notifies.Last().NotifyStateClass);
        const bool Undo=CopyPassed&&GEditor&&GEditor->UndoTransaction();Check(TEXT("native_undo_removes_copied_events"),Undo&&Target->Notifies.Num()==0&&Source->Notifies.Num()==2);
        Check(TEXT("orphan_notify_not_editable_after_undo"),!IsCurrentNotify(EditedNotify));
        const bool Redo=Undo&&GEditor&&GEditor->RedoTransaction();Check(TEXT("native_redo_restores_copied_events"),Redo&&Target->Notifies.Num()==2&&Source->Notifies.Num()==2);
        UClass* SetClass=FindObject<UClass>(nullptr,TEXT("/Script/EndGame.EndAnimSet"));
        TStrongObjectPtr<UObject> Set(SetClass?NewObject<UObject>(GetTransientPackage(),SetClass,NAME_None,RF_Transient|RF_Transactional):nullptr);
        TargetAnimSet=Set.Get();TArray<UAnimationAsset*> Inputs;Inputs.Add(Source.Get());Inputs.Add(Target.Get());const bool MapApplied=ApplyAnimSetAnimations(Inputs);
        FMapProperty* Map=Set.IsValid()?FindFProperty<FMapProperty>(Set->GetClass(),TEXT("AnimationAssets")):nullptr;
        int32 MapCount=Map?FScriptMapHelper(Map,Map->ContainerPtrToValuePtr<void>(Set.Get())).Num():0;
        Check(TEXT("native_endanimset_map_reference_import"),MapApplied&&MapCount==2);
        bool ExactReferences=MapApplied&&MapCount==2;
        if(ExactReferences)
        {
            FScriptMapHelper Helper(Map,Map->ContainerPtrToValuePtr<void>(Set.Get()));FObjectProperty* Property=CastField<FObjectProperty>(Map->ValueProp);
            for(UAnimationAsset* Animation:Inputs){const FName Key=Animation->GetFName();const int32 Index=Helper.FindMapIndexWithKey(&Key);ExactReferences&=Property&&Index!=INDEX_NONE&&Property->GetObjectPropertyValue(Helper.GetValuePtr(Index))==Animation;}
        }
        Check(TEXT("native_endanimset_exact_keys_and_object_references"),ExactReferences);
        const bool DuplicateAccepted=ApplyAnimSetAnimations(Inputs);Check(TEXT("endanimset_duplicate_keys_refused"),!DuplicateAccepted&&Map&&FScriptMapHelper(Map,Map->ContainerPtrToValuePtr<void>(Set.Get())).Num()==2);
        const bool UndoMap=MapApplied&&GEditor&&GEditor->UndoTransaction();Check(TEXT("native_undo_restores_empty_endanimset_map"),UndoMap&&Map&&FScriptMapHelper(Map,Map->ContainerPtrToValuePtr<void>(Set.Get())).Num()==0);
        const bool RedoMap=UndoMap&&GEditor&&GEditor->RedoTransaction();Check(TEXT("native_redo_restores_endanimset_references"),RedoMap&&Map&&FScriptMapHelper(Map,Map->ContainerPtrToValuePtr<void>(Set.Get())).Num()==2);
        bool NestedRelink=false;
        if(UClass* MoveClass=FindObject<UClass>(nullptr,TEXT("/Script/EndGame.AnimNotify_MoveActorTimeline")))
        {
            UAnimNotifyState* Original=NewObject<UAnimNotifyState>(Source.Get(),MoveClass,NAME_None,RF_Transient);
            FStructProperty* LocalProperty=FindFProperty<FStructProperty>(MoveClass,TEXT("LocalEvent"));
            if(LocalProperty&&LocalProperty->Struct==FAnimNotifyEvent::StaticStruct())
            {
                FAnimNotifyEvent* Local=LocalProperty->ContainerPtrToValuePtr<FAnimNotifyEvent>(Original);Local->NotifyStateClass=Original;Local->Link(Source.Get(),.1f);Local->EndLink.Link(Source.Get(),.5f);Local->SetDuration(.4f);
                UObject* Clone=CopyNotifyObject(Original,Source.Get(),Target.Get());
                if(Clone)
                {
                    FAnimNotifyEvent* Copied=LocalProperty->ContainerPtrToValuePtr<FAnimNotifyEvent>(Clone);
                    NestedRelink=Copied->GetLinkedSequence()==Target.Get()&&Copied->EndLink.GetLinkedSequence()==Target.Get()&&FMath::IsNearlyEqual(Copied->GetTime(),.1f)&&FMath::IsNearlyEqual(Copied->GetDuration(),.4f)&&Copied->NotifyStateClass==Clone&&Local->GetLinkedSequence()==Source.Get();
                }
            }
        }
        Check(TEXT("native_movetimeline_nested_event_owner_endlink_rebinding"),NestedRelink);
        TargetSequence=nullptr;TargetAnimSet=nullptr;EditedNotify=nullptr;Details->SetObject(nullptr);
        Report->SetBoolField(TEXT("passed"),Passed);Report->SetArrayField(TEXT("checks"),Checks);Report->SetStringField(TEXT("scope"),TEXT("Actual native transient authored notify/map editing and Undo/Redo. No cooked asset loads, disk asset saves, notify dispatch or in-game behavior tests."));
        Status=Passed?TEXT("Owned native catalog/edit selftest passed. Only transient fixture objects were used."):TEXT("Owned native catalog/edit selftest failed; inspect Saved/EndAssetTools/CatalogSelfTest.json.");return Report;
    }
private:
    bool IsCurrentNotify(UObject* Object)const
    {
        if(!TargetSequence||!IsValid(Object)||Object->GetOuter()!=TargetSequence)return false;
        for(const FAnimNotifyEvent& Event:TargetSequence->Notifies)if(Object==Event.Notify||Object==Event.NotifyStateClass)return true;
        return false;
    }
    void LoadCatalogs()
    {
        const TSharedPtr<IPlugin> Plugin=IPluginManager::Get().FindPlugin(TEXT("EndAssetTools"));
        if(!Plugin.IsValid()){Status=TEXT("EndAssetTools plugin resource root is unavailable.");return;}
        const FString Root=FPaths::Combine(Plugin->GetBaseDir(),TEXT("Resources"),TEXT("Catalogs"));
        auto Load=[&](const TCHAR* Filename)->TSharedPtr<FJsonObject>
        {
            FString Text;TSharedPtr<FJsonObject> Json;
            if(!FFileHelper::LoadFileToString(Text,*FPaths::Combine(Root,Filename))||Text.Len()>16*1024*1024||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Json)) return nullptr;
            return Json;
        };
        if(const TSharedPtr<FJsonObject> Json=Load(TEXT("NotifyCatalog.json")))
        {
            const TSharedPtr<FJsonObject>* Classes=nullptr;
            if(Json->TryGetObjectField(TEXT("classes"),Classes)&&Classes&&Classes->IsValid())
            for(const auto& Pair:(*Classes)->Values)
            {
                if(!Pair.Value.IsValid()||Pair.Value->Type!=EJson::Object)continue;const TSharedPtr<FJsonObject> Profile=Pair.Value->AsObject();if(!Profile.IsValid())continue;
                FEntryPtr Entry=MakeShared<FCatalogEntry>();Entry->Category=TEXT("Notifies");Entry->Name=Pair.Key;Entry->Json=Profile;
                Entry->Path=JsonString(Profile,TEXT("module"))+TEXT(".")+Entry->Name;
                Entry->Description=TEXT("Class: ")+Entry->Path+TEXT("\nKind: ")+JsonString(Profile,TEXT("kind"))+TEXT("\nBase: ")+JsonString(Profile,TEXT("base_class"))+TEXT("\n\n");
                const TArray<TSharedPtr<FJsonValue>>* Props=nullptr;
                if(Profile->TryGetArrayField(TEXT("properties"),Props))for(const TSharedPtr<FJsonValue>& PropValue:*Props)
                {
                    if(!PropValue.IsValid()||PropValue->Type!=EJson::Object)continue;const TSharedPtr<FJsonObject> Prop=PropValue->AsObject();if(!Prop.IsValid())continue;
                    Entry->Description+=JsonString(Prop,TEXT("name"))+TEXT("  [")+JsonString(Prop,TEXT("type_signature_1_005"))+TEXT("]  ")+JsonString(Prop,TEXT("ui_control"))+TEXT("\n");
                }
                Entry->Search=(Entry->Name+TEXT(" ")+Entry->Path+TEXT(" ")+Entry->Description).ToLower();Entries.Add(Entry);
            }
        }
        if(const TSharedPtr<FJsonObject> Json=Load(TEXT("SkeletonCatalog.json")))
        {
            const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;
            if(Json->TryGetArrayField(TEXT("skeletons"),Rows))for(const TSharedPtr<FJsonValue>& Value:*Rows)
            {
                if(!Value.IsValid()||Value->Type!=EJson::Object)continue;const TSharedPtr<FJsonObject> Row=Value->AsObject();if(!Row.IsValid())continue;
                FEntryPtr Entry=MakeShared<FCatalogEntry>();Entry->Category=TEXT("Skeletons");Entry->Name=JsonString(Row,TEXT("name"));Entry->Path=JsonString(Row,TEXT("object_path"));Entry->Json=Row;
                Entry->Description=Entry->Path+TEXT("\n\nBone topology from the1.004/1.005 catalog; cross-character compatibility is checked separately.\n");
                const TArray<TSharedPtr<FJsonValue>>* Bones=nullptr;const TArray<TSharedPtr<FJsonValue>>* Parents=nullptr;
                if(Row->TryGetArrayField(TEXT("bones"),Bones)&&Row->TryGetArrayField(TEXT("parents"),Parents)&&Bones->Num()==Parents->Num())
                    for(int32 Index=0;Index<Bones->Num();++Index)if((*Bones)[Index]->Type==EJson::String&&(*Parents)[Index]->Type==EJson::Number)Entry->Description+=FString::Printf(TEXT("%d  %s  (parent %d)\n"),Index,*(*Bones)[Index]->AsString(),int32((*Parents)[Index]->AsNumber()));
                Entry->Search=(Entry->Name+TEXT(" ")+Entry->Path+TEXT(" ")+Entry->Description).ToLower();Entries.Add(Entry);
            }
        }
        if(const TSharedPtr<FJsonObject> Json=Load(TEXT("EffectParameterCatalog.json")))
        {
            const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;
            if(Json->TryGetArrayField(TEXT("prototypes"),Rows))for(const TSharedPtr<FJsonValue>& Value:*Rows)
            {
                if(!Value.IsValid()||Value->Type!=EJson::Object)continue;const TSharedPtr<FJsonObject> Row=Value->AsObject();if(!Row.IsValid())continue;
                FEntryPtr Entry=MakeShared<FCatalogEntry>();Entry->Category=TEXT("Effect parameters");Entry->Name=JsonString(Row,TEXT("parameter_name"));Entry->Path=JsonString(Row,TEXT("effect_template"));Entry->Json=Row;
                Entry->Description=Entry->Path+TEXT("\nParameter: ")+Entry->Name+TEXT("\nObserved type: ")+JsonString(Row,TEXT("type"))+TEXT("\n\n")+JsonText(Row);
                Entry->Search=(Entry->Name+TEXT(" ")+Entry->Path+TEXT(" ")+Entry->Description).ToLower();Entries.Add(Entry);
            }
        }
        Entries.Sort([](const FEntryPtr& A,const FEntryPtr& B){return A->Category==B->Category?A->Name<B->Name:A->Category<B->Category;});
        Status=FString::Printf(TEXT("Loaded %d catalog records. Select an asset in the Content Browser, then pin it here. Changes use Undo and remain unsaved until you save the asset."),Entries.Num());
    }
    void Filter()
    {
        Visible.Reset();const FString Needle=Search.ToLower();
        for(const FEntryPtr& Entry:Entries)if((*SelectedCategory==TEXT("All")||*SelectedCategory==Entry->Category)&&(Needle.IsEmpty()||Entry->Search.Contains(Needle)))Visible.Add(Entry);
        if(List.IsValid())List->RequestListRefresh();
    }
    FReply CopySelected()
    {
        if(Selected.IsValid()){const FString Text=Selected->Category==TEXT("Skeletons")?Selected->Path:JsonText(Selected->Json);FPlatformApplicationMisc::ClipboardCopy(*Text);Status=TEXT("Selected catalog data copied to the clipboard.");}
        return FReply::Handled();
    }
    FReply PinSequence()
    {
        const TArray<UObject*> Assets=SelectedAssets();TargetSequence=nullptr;EditedNotify=nullptr;Details->SetObject(nullptr);
        for(UObject* Asset:Assets)if(UAnimSequence* Sequence=Cast<UAnimSequence>(Asset)){TargetSequence=Sequence;break;}
        Status=TargetSequence?FString::Printf(TEXT("Sequence: %s — %s"),*TargetSequence->GetPathName(),CanEditSequence(TargetSequence)?TEXT("authored with loaded codec settings; notify editing enabled"):TEXT("protected cooked asset or missing codec settings; inspection/import plans only")):TEXT("Select an animation sequence in the Content Browser first.");
        return FReply::Handled();
    }
    FReply AddNotify()
    {
        if(!CanEditSequence(TargetSequence)){Status=TEXT("Pin an authored animation sequence with loaded bone and curve compression settings. Cooked source packages and incomplete authored animations cannot be edited here.");return FReply::Handled();}
        if(!Selected.IsValid()||Selected->Category!=TEXT("Notifies")){Status=TEXT("Choose a notify class in the catalog first.");return FReply::Handled();}
        UClass* Class=FindObject<UClass>(nullptr,*Selected->Path);
        if(!Class||Class->HasAnyClassFlags(CLASS_Abstract|CLASS_Deprecated|CLASS_NewerVersionExists)||(!Class->IsChildOf(UAnimNotify::StaticClass())&&!Class->IsChildOf(UAnimNotifyState::StaticClass())))
        {Status=TEXT("This native notify class is unavailable or cannot be instantiated in the installed editor.");return FReply::Handled();}
        const bool IsState=Class->IsChildOf(UAnimNotifyState::StaticClass());
        if(!FMath::IsFinite(TargetSequence->SequenceLength)||!FMath::IsFinite(NotifyTime)||NotifyTime<0||NotifyTime>TargetSequence->SequenceLength||(IsState&&(!FMath::IsFinite(NotifyDuration)||NotifyDuration<0||NotifyTime+NotifyDuration>TargetSequence->SequenceLength)))
        {Status=TEXT("Notify time/duration must be finite and fit inside the animation.");return FReply::Handled();}
        const FScopedTransaction Transaction(LOCTEXT("AddNotifyTransaction","Add FFVII Rebirth notify"));TargetSequence->Modify();
        FAnimNotifyEvent Event;Event.NotifyName=Class->GetFName();
#if WITH_EDITORONLY_DATA
        Event.Guid=FGuid::NewGuid();
        if(!TargetSequence->AnimNotifyTracks.Num())TargetSequence->AnimNotifyTracks.Add(FAnimNotifyTrack(TEXT("1"),FLinearColor::White));
#endif
        if(Class->IsChildOf(UAnimNotifyState::StaticClass()))Event.NotifyStateClass=NewObject<UAnimNotifyState>(TargetSequence,Class,NAME_None,RF_Transactional);
        else Event.Notify=NewObject<UAnimNotify>(TargetSequence,Class,NAME_None,RF_Transactional);
        Event.Link(TargetSequence,NotifyTime);Event.TriggerTimeOffset=GetTriggerTimeOffsetForType(TargetSequence->CalculateOffsetForNotify(NotifyTime));
        if(Event.NotifyStateClass)
        {
            Event.EndLink.Link(TargetSequence,NotifyTime+NotifyDuration);Event.SetDuration(NotifyDuration);
            Event.EndTriggerTimeOffset=GetTriggerTimeOffsetForType(TargetSequence->CalculateOffsetForNotify(NotifyTime+NotifyDuration));
        }
        TargetSequence->Notifies.Add(Event);TargetSequence->RefreshCacheData();TargetSequence->MarkPackageDirty();
        EditedNotify=Event.Notify?static_cast<UObject*>(Event.Notify):static_cast<UObject*>(Event.NotifyStateClass);Details->SetObject(EditedNotify);
        Status=TEXT("Notify added using the installed native class defaults. Edit its typed properties below; save the animation when ready. No notify was executed.");return FReply::Handled();
    }
    FReply EditLastNotify()
    {
        EditedNotify=nullptr;
        if(TargetSequence&&TargetSequence->Notifies.Num())
        {
            const FAnimNotifyEvent& Event=TargetSequence->Notifies.Last();EditedNotify=Event.Notify?static_cast<UObject*>(Event.Notify):static_cast<UObject*>(Event.NotifyStateClass);
            NotifyTime=Event.GetTime();NotifyDuration=Event.GetDuration();
        }
        Details->SetObject(EditedNotify);Status=EditedNotify?TEXT("Native notify properties displayed. Editing is enabled only on authored sequences."):TEXT("Pinned sequence has no object-backed notify.");return FReply::Handled();
    }
    FReply CopyNotifies()
    {
        UAnimSequence* Source=nullptr;for(UObject* Asset:SelectedAssets())if(UAnimSequence* Candidate=Cast<UAnimSequence>(Asset)){if(Candidate!=TargetSequence){Source=Candidate;break;}}
        return CopyNotifiesFrom(Source);
    }
    FReply CopyNotifiesFrom(UAnimSequence* Source)
    {
        if(!CanEditSequence(TargetSequence)){Status=TEXT("Pin an authored target sequence with loaded bone and curve compression settings before copying notifies. Cooked sources stay unchanged.");return FReply::Handled();}
        if(!Source||!Source->Notifies.Num()){Status=TEXT("Select a different sequence containing notifies in the Content Browser.");return FReply::Handled();}
        for(const FAnimNotifyEvent& Event:Source->Notifies)
        {
            if(!FMath::IsFinite(Event.GetTime())||!FMath::IsFinite(Event.GetDuration())||Event.GetTime()<0||Event.GetDuration()<0||Event.GetTime()+Event.GetDuration()>TargetSequence->SequenceLength||Event.TrackIndex<0||Event.TrackIndex>20)
            {Status=TEXT("Copy refused: a source notify does not fit inside the target animation. Original timing was preserved.");return FReply::Handled();}
        }
        TArray<FAnimNotifyEvent> Copies;
        for(const FAnimNotifyEvent& Original:Source->Notifies)
        {
            FAnimNotifyEvent Copy=Original;
            if(Original.Notify){Copy.Notify=Cast<UAnimNotify>(CopyNotifyObject(Original.Notify,Source,TargetSequence));if(!Copy.Notify){Status=TEXT("Copy refused: nested notify links could not be remapped safely.");return FReply::Handled();}}
            if(Original.NotifyStateClass){Copy.NotifyStateClass=Cast<UAnimNotifyState>(CopyNotifyObject(Original.NotifyStateClass,Source,TargetSequence));if(!Copy.NotifyStateClass){Status=TEXT("Copy refused: nested notify-state links could not be remapped safely.");return FReply::Handled();}}
            Copies.Add(Copy);
        }
        const FScopedTransaction Transaction(LOCTEXT("CopyNotifiesTransaction","Copy FFVII Rebirth animation notifies"));TargetSequence->Modify();
#if WITH_EDITORONLY_DATA
        int32 RequiredTracks=1;for(const FAnimNotifyEvent& Event:Source->Notifies)RequiredTracks=FMath::Max(RequiredTracks,Event.TrackIndex+1);
        while(TargetSequence->AnimNotifyTracks.Num()<RequiredTracks)
        {
            const int32 Index=TargetSequence->AnimNotifyTracks.Num();
            const FName Name=Source->AnimNotifyTracks.IsValidIndex(Index)?Source->AnimNotifyTracks[Index].TrackName:FName(*FString::FromInt(Index+1));
            const FLinearColor Color=Source->AnimNotifyTracks.IsValidIndex(Index)?Source->AnimNotifyTracks[Index].TrackColor:FLinearColor::White;
            TargetSequence->AnimNotifyTracks.Add(FAnimNotifyTrack(Name,Color));
        }
#endif
        for(int32 Index=0;Index<Copies.Num();++Index)
        {
            const FAnimNotifyEvent& Original=Source->Notifies[Index];FAnimNotifyEvent Copy=Copies[Index];
            if(Copy.Notify)Copy.Notify->SetFlags(RF_Transactional);
            if(Copy.NotifyStateClass)Copy.NotifyStateClass->SetFlags(RF_Transactional);
            Copy.Link(TargetSequence,Original.GetTime());Copy.EndLink.Link(TargetSequence,Original.GetTime()+Original.GetDuration());Copy.SetDuration(Original.GetDuration());
            Copy.TriggerTimeOffset=GetTriggerTimeOffsetForType(TargetSequence->CalculateOffsetForNotify(Copy.GetTime()));
            if(Copy.NotifyStateClass)Copy.EndTriggerTimeOffset=GetTriggerTimeOffsetForType(TargetSequence->CalculateOffsetForNotify(Copy.GetTime()+Copy.GetDuration()));
#if WITH_EDITORONLY_DATA
            Copy.Guid=FGuid::NewGuid();
#endif
            TargetSequence->Notifies.Add(Copy);
        }
        TargetSequence->RefreshCacheData();TargetSequence->MarkPackageDirty();
        Status=FString::Printf(TEXT("Copied %d notifies with native object properties, timing and state durations. Source objects are unchanged; target changes are unsaved and support Undo."),Source->Notifies.Num());return FReply::Handled();
    }
    FReply ExportNotifyPlan()
    {
        if(!TargetSequence){Status=TEXT("Pin a sequence before exporting its notifies.");return FReply::Handled();}
        const TSharedRef<FJsonObject> Plan=MakeShared<FJsonObject>();Plan->SetStringField(TEXT("format"),TEXT("EndAssetTools.NotifyImportPlan.v1"));
        Plan->SetStringField(TEXT("source_animation"),TargetSequence->GetPathName());Plan->SetNumberField(TEXT("sequence_length"),TargetSequence->SequenceLength);
        Plan->SetStringField(TEXT("scope"),TEXT("Native reflected notify properties and event timing for review/import planning; not a UAssetAPI cooked-package wire-format patch."));
        TArray<TSharedPtr<FJsonValue>> Rows;
        for(const FAnimNotifyEvent& Event:TargetSequence->Notifies)
        {
            const TSharedRef<FJsonObject> Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("name"),Event.NotifyName.ToString());Row->SetNumberField(TEXT("time"),Event.GetTime());Row->SetNumberField(TEXT("duration"),Event.GetDuration());Row->SetNumberField(TEXT("track"),Event.TrackIndex);
            UObject* Object=Event.Notify?static_cast<UObject*>(Event.Notify):static_cast<UObject*>(Event.NotifyStateClass);
            Row->SetStringField(TEXT("kind"),Event.NotifyStateClass?TEXT("NotifyState"):TEXT("Notify"));
            if(Object)
            {
                Row->SetStringField(TEXT("class_path"),Object->GetClass()->GetPathName());const TSharedRef<FJsonObject> Properties=MakeShared<FJsonObject>();
                const FJsonObjectConverter::CustomExportCallback References=FJsonObjectConverter::CustomExportCallback::CreateLambda([](FProperty* Property,const void* Value)->TSharedPtr<FJsonValue>
                {
                    if(FObjectProperty* ObjectProperty=CastField<FObjectProperty>(Property))
                    {
                        const UObject* Reference=ObjectProperty->GetObjectPropertyValue(Value);
                        if(Reference){TSharedPtr<FJsonValue> Result=MakeShared<FJsonValueString>(Reference->GetPathName());return Result;}
                        TSharedPtr<FJsonValue> Result=MakeShared<FJsonValueNull>();return Result;
                    }
                    return nullptr;
                });
                if(!FJsonObjectConverter::UStructToJsonObject(Object->GetClass(),Object,Properties,0,CPF_Transient,&References))
                {Status=TEXT("Export refused: native notify properties could not be represented completely.");return FReply::Handled();}
                Row->SetObjectField(TEXT("properties"),Properties);
            }
            Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
        Plan->SetArrayField(TEXT("notifies"),Rows);
        const FString Directory=FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("EndAssetTools"));IFileManager::Get().MakeDirectory(*Directory,true);
        const FString Path=FPaths::Combine(Directory,TEXT("NotifyImportPlan.json"));
        Status=FFileHelper::SaveStringToFile(JsonText(Plan),*Path)?TEXT("Notify import plan exported: ")+Path:TEXT("Could not write the notify plan.");return FReply::Handled();
    }
    FReply PinAnimSet()
    {
        TargetAnimSet=nullptr;for(UObject* Asset:SelectedAssets())if(Asset->GetClass()->GetFName()==FName(TEXT("EndAnimSet"))){TargetAnimSet=Asset;break;}
        Status=TargetAnimSet?TEXT("EndAnimSet pinned: ")+TargetAnimSet->GetPathName():TEXT("Select an EndAnimSet in the Content Browser first.");return FReply::Handled();
    }
    TSharedPtr<FJsonObject> AnimSetPlan(TArray<UAnimationAsset*>& Animations)
    {
        const TSharedRef<FJsonObject> Plan=MakeShared<FJsonObject>();Plan->SetStringField(TEXT("format"),TEXT("EndAssetTools.EndAnimSetImportPlan.v1"));Plan->SetStringField(TEXT("target"),TargetAnimSet?TargetAnimSet->GetPathName():TEXT("None"));
        Plan->SetBoolField(TEXT("target_is_authored"),IsEditableAuthored(TargetAnimSet));TArray<TSharedPtr<FJsonValue>> Rows;
        for(UObject* Asset:SelectedAssets())if(UAnimationAsset* Animation=Cast<UAnimationAsset>(Asset))
        {
            Animations.Add(Animation);const TSharedRef<FJsonObject> Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("key"),Animation->GetName());Row->SetStringField(TEXT("object_path"),Animation->GetPathName());Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
        Plan->SetArrayField(TEXT("animations"),Rows);Plan->SetStringField(TEXT("scope"),TEXT("Reference-map edits only; cooked replacement packaging/preload dependencies are not synthesized by this native authored-asset tool."));return Plan;
    }
    FReply ExportAnimSetPlan()
    {
        TArray<UAnimationAsset*> Animations;const TSharedPtr<FJsonObject> Plan=AnimSetPlan(Animations);
        const FString Directory=FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("EndAssetTools"));IFileManager::Get().MakeDirectory(*Directory,true);
        const FString Path=FPaths::Combine(Directory,TEXT("EndAnimSetImportPlan.json"));
        Status=FFileHelper::SaveStringToFile(JsonText(Plan),*Path)?TEXT("Import plan exported: ")+Path:TEXT("Could not write the import plan.");return FReply::Handled();
    }
    FReply ImportAnimSet()
    {
        TArray<UAnimationAsset*> Animations;AnimSetPlan(Animations);ApplyAnimSetAnimations(Animations);return FReply::Handled();
    }
    bool ApplyAnimSetAnimations(const TArray<UAnimationAsset*>& Animations)
    {
        if(!IsEditableAuthored(TargetAnimSet)){Status=TEXT("Pin an authored EndAnimSet. Use an import plan for cooked sources.");return false;}
        FMapProperty* Map=FindFProperty<FMapProperty>(TargetAnimSet->GetClass(),TEXT("AnimationAssets"));
        if(!Map||!Map->KeyProp->IsA<FNameProperty>()) {Status=TEXT("Installed EndAnimSet AnimationAssets schema is unsupported.");return false;}
        FObjectProperty* ValueProperty=CastField<FObjectProperty>(Map->ValueProp);
        if(!ValueProperty||!ValueProperty->PropertyClass->IsChildOf(UAnimationAsset::StaticClass())){Status=TEXT("AnimationAssets does not have native animation-object values.");return false;}
        if(!Animations.Num()){Status=TEXT("Select one or more animation assets in the Content Browser.");return false;}
        FScriptMapHelper Helper(Map,Map->ContainerPtrToValuePtr<void>(TargetAnimSet));
        TSet<FName> NewKeys;
        for(UAnimationAsset* Animation:Animations){if(!IsValid(Animation)){Status=TEXT("Import refused because an animation reference is invalid.");return false;}const FName Key=Animation->GetFName();if(NewKeys.Contains(Key)||Helper.FindMapIndexWithKey(&Key)!=INDEX_NONE){Status=TEXT("Import refused because an animation key is duplicated or already exists: ")+Key.ToString();return false;}NewKeys.Add(Key);}
        const FScopedTransaction Transaction(LOCTEXT("ImportAnimSetTransaction","Add animations to FFVII Rebirth EndAnimSet"));TargetAnimSet->Modify();
        for(UAnimationAsset* Animation:Animations){const FName Key=Animation->GetFName();UObject* Value=Animation;Helper.AddPair(&Key,&Value);}
        TargetAnimSet->MarkPackageDirty();Status=FString::Printf(TEXT("Added %d animation references. Existing entries and source animations were preserved. Save the authored EndAnimSet when ready."),Animations.Num());return true;
    }
    TArray<FEntryPtr> Entries,Visible;
    TArray<TSharedPtr<FString>> Categories;
    TSharedPtr<FString> SelectedCategory;
    TSharedPtr<SListView<FEntryPtr>> List;
    TSharedPtr<IDetailsView> Details;
    FEntryPtr Selected;
    FString Search,Status;
    UAnimSequence* TargetSequence=nullptr;
    UObject* EditedNotify=nullptr;
    UObject* TargetAnimSet=nullptr;
    float NotifyTime=0,NotifyDuration=.2f;
};
TWeakPtr<SEndCatalogTools> LastCatalogTools;
void RunOwnedCatalogSelfTest()
{
    if(!IsInGameThread()||!GEditor||IsRunningCommandlet()||!FParse::Param(FCommandLine::Get(),TEXT("EndAssetToolsOwnedProbe")))return;
    EndAssetTools::OpenCatalogTools();const TSharedPtr<SEndCatalogTools> Widget=LastCatalogTools.Pin();if(!Widget.IsValid())return;
    const TSharedRef<FJsonObject> Report=Widget->RunOwnedSelfTest();
    const FString Directory=FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("EndAssetTools"));IFileManager::Get().MakeDirectory(*Directory,true);
    FFileHelper::SaveStringToFile(JsonText(Report),*FPaths::Combine(Directory,TEXT("CatalogSelfTest.json")));
}
FAutoConsoleCommand CatalogSelfTestCommand(TEXT("EndAssetTools.CatalogSelfTest"),TEXT("Run owned transient native catalog/edit tests; requires -EndAssetToolsOwnedProbe."),FConsoleCommandDelegate::CreateStatic(&RunOwnedCatalogSelfTest));
FAutoConsoleCommand CatalogCloseCommand(TEXT("EndAssetTools.CatalogClose"),TEXT("Close the FFVII Rebirth Asset Tools catalog tab."),FConsoleCommandDelegate::CreateStatic(&EndAssetTools::CloseCatalogTools));
}
namespace EndAssetTools
{
void RegisterCatalogTools()
{
    FGlobalTabmanager::Get()->RegisterNomadTabSpawner(CatalogTabName,FOnSpawnTab::CreateLambda([](const FSpawnTabArgs&){const TSharedRef<SEndCatalogTools> Widget=SNew(SEndCatalogTools);LastCatalogTools=Widget;return SNew(SDockTab).TabRole(ETabRole::NomadTab)[Widget];}))
        .SetDisplayName(LOCTEXT("CatalogTab","FFVII Rebirth Asset Tools")).SetMenuType(ETabSpawnerMenuType::Hidden);
}
void UnregisterCatalogTools(){CloseCatalogTools();FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(CatalogTabName);}
void OpenCatalogTools(){FGlobalTabmanager::Get()->TryInvokeTab(CatalogTabName);}
void CloseCatalogTools(){if(const TSharedPtr<SDockTab> Tab=FGlobalTabmanager::Get()->FindExistingLiveTab(CatalogTabName))Tab->RequestCloseTab();LastCatalogTools.Reset();}
}
#undef LOCTEXT_NAMESPACE
