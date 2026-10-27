#include "RebirthBlendableCustomization.h"

#include "DetailLayoutBuilder.h"
#include "DetailWidgetRow.h"
#include "Engine/Scene.h"
#include "IPropertyTypeCustomization.h"
#include "Modules/ModuleManager.h"
#include "PropertyCustomizationHelpers.h"
#include "PropertyEditorModule.h"
#include "PropertyHandle.h"
#include "ScopedTransaction.h"
#include "Widgets/Input/SNumericEntryBox.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"

#ifdef LOCTEXT_NAMESPACE
#undef LOCTEXT_NAMESPACE
#endif
#define LOCTEXT_NAMESPACE "RebirthBlendableCustomization"

namespace RebirthBlendableCustomization
{
namespace
{
const FName BlendableTypeName(TEXT("WeightedBlendable"));
bool bBlendableRowRegistered = false;

class FWeightedBlendableRow final : public IPropertyTypeCustomization
{
public:
    static TSharedRef<IPropertyTypeCustomization> MakeInstance()
    {
        return MakeShareable(new FWeightedBlendableRow);
    }

    virtual void CustomizeHeader(TSharedRef<IPropertyHandle> StructHandle, FDetailWidgetRow& HeaderRow, IPropertyTypeCustomizationUtils& Utils) override
    {
        StructProperty = StructHandle;
        WeightProperty = ValidChild(StructHandle, GET_MEMBER_NAME_CHECKED(FWeightedBlendable, Weight));
        const TSharedPtr<IPropertyHandle> ObjectProperty = ValidChild(StructHandle, GET_MEMBER_NAME_CHECKED(FWeightedBlendable, Object));
        if (ObjectProperty.IsValid())
        {
            // A material picked into a new entry (the engine makes them with weight -1, "not set") gets full weight.
            ObjectProperty->SetOnPropertyValueChanged(FSimpleDelegate::CreateSP(this, &FWeightedBlendableRow::OnObjectChanged));
        }

        HeaderRow.NameContent()
        [
            SNew(SBox)
            .MinDesiredWidth(60.0f)
            .MaxDesiredWidth(60.0f)
            [
                SNew(SNumericEntryBox<float>)
                .AllowSpin(false)
                .MinValue(0.0f)
                .MaxValue(1.0f)
                .Font(IDetailLayoutBuilder::GetDetailFont())
                .UndeterminedString(LOCTEXT("MultipleWeights", "Multiple"))
                .ToolTipText(LOCTEXT("WeightTip", "Weight of this post process material: 0 no effect, 1 full effect"))
                .Value(this, &FWeightedBlendableRow::GetWeight)
                .OnValueCommitted(this, &FWeightedBlendableRow::OnWeightCommitted)
            ]
        ];

        TSharedPtr<SWidget> ValueWidget;
        if (ObjectProperty.IsValid())
        {
            const TSharedPtr<FAssetThumbnailPool> Pool = Utils.GetThumbnailPool();
            ValueWidget = SNew(SObjectPropertyEntryBox)
                .PropertyHandle(ObjectProperty)
                .ThumbnailPool(Pool)
                .DisplayThumbnail(Pool.IsValid());
        }
        else
        {
            ValueWidget = SNew(STextBlock)
                .Font(IDetailLayoutBuilder::GetDetailFont())
                .Text(LOCTEXT("NoObjectRow", "(this entry's material has no details row)"));
        }
        HeaderRow.ValueContent()
        .MinDesiredWidth(250.0f)
        .MaxDesiredWidth(0.0f)
        [
            ValueWidget.ToSharedRef()
        ];
    }

    virtual void CustomizeChildren(TSharedRef<IPropertyHandle> StructHandle, IDetailChildrenBuilder& ChildBuilder, IPropertyTypeCustomizationUtils& Utils) override
    {
        // Weight and material are both in the header row.
    }

private:
    static TSharedPtr<IPropertyHandle> ValidChild(const TSharedRef<IPropertyHandle>& StructHandle, const FName Name)
    {
        const TSharedPtr<IPropertyHandle> Child = StructHandle->GetChildHandle(Name);
        if (Child.IsValid() && Child->IsValidHandle() && Child->GetProperty() != nullptr)
        {
            return Child;
        }
        return TSharedPtr<IPropertyHandle>();
    }

    TArray<FWeightedBlendable*> Entries() const
    {
        TArray<FWeightedBlendable*> Result;
        const TSharedPtr<IPropertyHandle> Handle = StructProperty.Pin();
        if (!Handle.IsValid() || !Handle->IsValidHandle())
        {
            return Result;
        }
        TArray<void*> RawData;
        Handle->AccessRawData(RawData);
        for (void* Data : RawData)
        {
            if (Data != nullptr)
            {
                Result.Add(static_cast<FWeightedBlendable*>(Data));
            }
        }
        return Result;
    }

    TOptional<float> GetWeight() const
    {
        if (WeightProperty.IsValid())
        {
            float Value = 0.0f;
            if (WeightProperty->GetValue(Value) == FPropertyAccess::Success)
            {
                return Value;
            }
            return TOptional<float>();
        }
        const TArray<FWeightedBlendable*> List = Entries();
        if (List.Num() == 0)
        {
            return TOptional<float>();
        }
        const float First = List[0]->Weight;
        for (const FWeightedBlendable* Entry : List)
        {
            if (Entry->Weight != First)
            {
                return TOptional<float>();
            }
        }
        return First;
    }

    // bOnlyUnset: only entries still at the engine's "not set" weight (below 0).
    void SetWeight(const float NewWeight, const bool bOnlyUnset)
    {
        if (WeightProperty.IsValid())
        {
            float Current = 0.0f;
            if (!bOnlyUnset || (WeightProperty->GetValue(Current) == FPropertyAccess::Success && Current < 0.0f))
            {
                WeightProperty->SetValue(NewWeight);
            }
            return;
        }
        const TSharedPtr<IPropertyHandle> Handle = StructProperty.Pin();
        if (!Handle.IsValid() || !Handle->IsValidHandle())
        {
            return;
        }
        const TArray<FWeightedBlendable*> List = Entries();
        bool bChange = false;
        for (const FWeightedBlendable* Entry : List)
        {
            bChange |= bOnlyUnset ? (Entry->Weight < 0.0f) : (Entry->Weight != NewWeight);
        }
        if (!bChange)
        {
            return;
        }
        const FScopedTransaction Transaction(LOCTEXT("SetBlendableWeight", "Set Post Process Material Weight"));
        Handle->NotifyPreChange();
        for (FWeightedBlendable* Entry : List)
        {
            if (!bOnlyUnset || Entry->Weight < 0.0f)
            {
                Entry->Weight = NewWeight;
            }
        }
        Handle->NotifyPostChange(EPropertyChangeType::ValueSet);
        Handle->NotifyFinishedChangingProperties();
    }

    void OnWeightCommitted(const float NewWeight, const ETextCommit::Type CommitType)
    {
        SetWeight(FMath::Clamp(NewWeight, 0.0f, 1.0f), false);
    }

    void OnObjectChanged()
    {
        SetWeight(1.0f, true);
    }

    TWeakPtr<IPropertyHandle> StructProperty;
    TSharedPtr<IPropertyHandle> WeightProperty;
};
}

void Register()
{
    if (bBlendableRowRegistered)
    {
        return;
    }
    // DetailCustomizations registers the engine's row for this type; a registration with no identifier replaces it.
    FModuleManager::LoadModuleChecked<IModuleInterface>(TEXT("DetailCustomizations"));
    FPropertyEditorModule& PropertyModule = FModuleManager::LoadModuleChecked<FPropertyEditorModule>(TEXT("PropertyEditor"));
    PropertyModule.RegisterCustomPropertyTypeLayout(BlendableTypeName, FOnGetPropertyTypeCustomizationInstance::CreateStatic(&FWeightedBlendableRow::MakeInstance));
    PropertyModule.NotifyCustomizationModuleChanged();
    bBlendableRowRegistered = true;
}

void Unregister()
{
    if (!bBlendableRowRegistered)
    {
        return;
    }
    bBlendableRowRegistered = false;
    if (FPropertyEditorModule* PropertyModule = FModuleManager::GetModulePtr<FPropertyEditorModule>(TEXT("PropertyEditor")))
    {
        PropertyModule->UnregisterCustomPropertyTypeLayout(BlendableTypeName);
        PropertyModule->NotifyCustomizationModuleChanged();
    }
}
}

#undef LOCTEXT_NAMESPACE
