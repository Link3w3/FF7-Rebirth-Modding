// One field Apply To CharaSpec writes into a row.
struct FWeaponFieldChange
{
	const TCHAR* Field = nullptr;
	FString Current; // the field's text now
	FString Value;   // the text Apply writes
};
using FFieldChange = FWeaponFieldChange;

// The items of a field's copy text in order, "None" kept (slots, e.g. Override Weapon Socket Names lined up with the
// equipment list): (None,None,Attach_Tonfa01) or ("A","B").
TArray<FString> SlotsInText(FString Text)
{
	Text.TrimStartAndEndInline();
	Text.RemoveFromStart(TEXT("("));
	Text.RemoveFromEnd(TEXT(")"));
	TArray<FString> Parts;
	Text.ParseIntoArray(Parts, TEXT(","), true);
	TArray<FString> Items;
	for (FString Part : Parts)
	{
		Part.TrimStartAndEndInline();
		Part.TrimQuotesInline();
		Items.Add(Part.IsEmpty() ? FString(TEXT("None")) : Part);
	}
	return Items;
}

// ------------------------------------------------------------------------------------------------
// Game assets for packs to point at (editor 1.7): RebirthGameObjectLibrary of the Rebirth Cooked Asset Preview plugin finds
// them in the game's paks, and for the ones this project does not have it makes in-memory stand-ins (never saved or cooked;
// in game the reference resolves to the game's own asset).
// ------------------------------------------------------------------------------------------------
const TCHAR* const GameObjectLibrary = TEXT("RebirthGameObjectLibrary");
const TCHAR* const GameObjectToolsMissing = TEXT("the Rebirth Cooked Asset Preview plugin of this project has no RebirthGameObjectLibrary yet (it is older than RebirthSkelCompat 1.7): rebuild the editor plugins (Tools\\EndEditorPlugins\\run_build_editor_plugins.cmd)");

bool GameObjectToolsLoaded() { return static_cast<bool>(FDataObjectCall(TEXT("GetGameObject"), GameObjectLibrary)); }

// Packages with this short name in the game's paks, e.g. VO_PC0000_02_Cloud_Insanity (empty without the tools).
TArray<FString> GamePackagesNamed(const FString& ShortName)
{
	FDataObjectCall Call(TEXT("FindGamePackages"), GameObjectLibrary);
	if (!Call || !Call.SetString(TEXT("ShortName"), ShortName))
	{
		return {};
	}
	Call.Run();
	return Call.ResultStrings();
}

// The object path of the game asset ShortName under Folder (with Suffix, _C for a blueprint class), or empty. Of several,
// the one under a /JP/ folder: the game's packs list the Japanese voice and lip sync (the game finds the voice language's).
FString GameObjectPathOf(const FString& ShortName, const TCHAR* Folder, const TCHAR* Suffix = TEXT(""))
{
	FString Best;
	for (const FString& Package : GamePackagesNamed(ShortName))
	{
		if (!Package.StartsWith(Folder, ESearchCase::IgnoreCase))
		{
			continue;
		}
		if (Best.IsEmpty() || (Package.Contains(TEXT("/JP/")) && !Best.Contains(TEXT("/JP/"))))
		{
			Best = Package;
		}
	}
	return Best.IsEmpty() ? FString() : Best + TEXT(".") + ShortName + Suffix;
}

// The game asset at ObjectPath (this project's when it has it, else a stand-in), of the class at ClassPath.
UObject* GameObject(const FString& ObjectPath, const FString& ClassPath, FString& Error)
{
	FDataObjectCall Call(TEXT("GetGameObject"), GameObjectLibrary);
	if (!Call || !Call.SetString(TEXT("ObjectPath"), ObjectPath) || !Call.SetString(TEXT("ClassPath"), ClassPath))
	{
		Error = GameObjectToolsMissing;
		return nullptr;
	}
	Call.Run();
	Error = Call.ResultString(TEXT("Message"));
	return Call.ResultObject();
}

// The folder of a character's kind under /Game/Character, /Game/BluePrint/Character and /Game/Motion: Player (PC...),
// Weapon (WE...), Enemy (EN..., EB...), NonPlayer (NP...).
const TCHAR* KindFolderOf(const FString& Name)
{
	if (Name.StartsWith(TEXT("WE"), ESearchCase::IgnoreCase))
	{
		return TEXT("Weapon");
	}
	if (Name.StartsWith(TEXT("EN"), ESearchCase::IgnoreCase) || Name.StartsWith(TEXT("EB"), ESearchCase::IgnoreCase))
	{
		return TEXT("Enemy");
	}
	if (Name.StartsWith(TEXT("NP"), ESearchCase::IgnoreCase))
	{
		return TEXT("NonPlayer");
	}
	return TEXT("Player");
}

// The skeleton in a model's folder: /Game/Character/<kind>/<model>/Model/<id>_Skeleton.<id>_Skeleton.
FString ModelSkeletonPathOf(const FString& Model)
{
	const FString Skeleton = ModelIdOf(Model) + TEXT("_Skeleton");
	return FString::Printf(TEXT("/Game/Character/%s/%s/Model/%s.%s"), KindFolderOf(Model), *Model, *Skeleton, *Skeleton);
}

// "PC0000_00_Cloud_Standard" -> "PC0000_": what every model and blueprint of that character starts with.
FString CharacterIdOf(const FString& Name)
{
	int32 Underscore = INDEX_NONE;
	return Name.FindChar(TEXT('_'), Underscore) ? Name.Left(Underscore + 1) : Name;
}

bool IsBlueprintOf(const FString& Blueprint, const FString& Character)
{
	return !Character.IsEmpty() && Blueprint.StartsWith(CharacterIdOf(Character), ESearchCase::IgnoreCase);
}

// "PC0000_00_Cloud_Standard" -> "/Game/Motion/Player/PC0000_Cloud": the motion folder named the way the game names them.
FString MotionFolderByName(const FString& Model)
{
	TArray<FString> Parts;
	Model.ParseIntoArray(Parts, TEXT("_"), true);
	return Parts.Num() >= 3 ? FString::Printf(TEXT("/Game/Motion/%s/%s_%s"), KindFolderOf(Model), *Parts[0], *Parts[2]) : FString();
}

// The class path of the blueprint that spawns this CharaSpec row's model (the game names a blueprint like its model's row).
FString BlueprintClassPathOf(const FString& Row)
{
	const FString Found = GameObjectPathOf(Row, TEXT("/Game/BluePrint/Character/"), TEXT("_C"));
	return !Found.IsEmpty() ? Found : FString::Printf(TEXT("/Game/BluePrint/Character/%s/%s.%s_C"), KindFolderOf(Row), *Row, *Row);
}

// "/Game/BluePrint/Character/Player/PC0000_00_Cloud_Standard.PC0000_00_Cloud_Standard_C" -> "PC0000_00_Cloud_Standard"
FString AssetNameOf(const FString& ObjectPath)
{
	FString Name = ShortName(ObjectPath);
	Name.RemoveFromEnd(TEXT("_C"));
	return Name;
}

// ------------------------------------------------------------------------------------------------
// Pack edits (editor 1.7). A CharaSpec pack (CharaSpec_<row>, End Asset Data Asset) spawns the classes in its Asset Class
// List (the character or weapon blueprint, the AI blueprint) and loads the objects in its Asset Data List (motion sets,
// effect packs, sound banks, voice, lip sync, battle camera). A swap points them at the new character or weapon.
// ------------------------------------------------------------------------------------------------
struct FPackEdit
{
	FString Blueprint; // class to spawn in place of its character or weapon blueprint (object path)
	FString Voice;     // voice bank in place of its voice banks
	FString LipSync;   // lip sync in place of its lip syncs
	FString Effect;    // effect pack in place of its effect packs (weapons)
	bool HasWork() const { return !Blueprint.IsEmpty() || !Voice.IsEmpty() || !LipSync.IsEmpty() || !Effect.IsEmpty(); }
};

TArray<FString> PackEditLines(const FPackEdit& Edit, const FPackContents& Pack)
{
	TArray<FString> Lines;
	const auto Was = [](const TArray<FString>& Items) { return Items.Num() > 0 ? FString::Join(Items, TEXT(", ")) : FString(TEXT("nothing")); };
	if (!Edit.Blueprint.IsEmpty())
	{
		Lines.Add(FString::Printf(TEXT("spawn %s (was %s)"), *AssetNameOf(Edit.Blueprint), *Was(Pack.Blueprints)));
	}
	if (!Edit.Voice.IsEmpty())
	{
		Lines.Add(FString::Printf(TEXT("voice %s (was %s)"), *AssetNameOf(Edit.Voice), *Was(Pack.Voices)));
	}
	if (!Edit.LipSync.IsEmpty())
	{
		Lines.Add(FString::Printf(TEXT("lip sync %s (was %s)"), *AssetNameOf(Edit.LipSync), *Was(Pack.LipSyncs)));
	}
	if (!Edit.Effect.IsEmpty())
	{
		Lines.Add(FString::Printf(TEXT("effects %s (was %s)"), *AssetNameOf(Edit.Effect), *Was(Pack.Effects)));
	}
	return Lines;
}

UObject* LoadPack(const FString& Row)
{
	return LoadObject<UObject>(nullptr, *(PackPackageOf(Row) + TEXT(".CharaSpec_") + Row), nullptr, LOAD_NoWarn | LOAD_Quiet);
}

bool InFolder(const UObject* Object, const TCHAR* Folder)
{
	return Object && Object->GetOutermost()->GetName().StartsWith(Folder, ESearchCase::IgnoreCase);
}

bool IsEffectPack(const UObject* Object)
{
	return Object && Object->GetName().EndsWith(TEXT("_Effect__Pack"), ESearchCase::IgnoreCase);
}

// One of a pack's lists (AssetDataList or AssetClassList): each entry's AssetUserData array of objects (classes).
struct FPackList
{
	FArrayProperty* List = nullptr;
	FArrayProperty* Items = nullptr;
	FObjectPropertyBase* Item = nullptr;

	FPackList(UObject* Pack, const TCHAR* Name)
	{
		List = Pack ? FindFProperty<FArrayProperty>(Pack->GetClass(), Name) : nullptr;
		FStructProperty* Entry = List ? CastField<FStructProperty>(List->Inner) : nullptr;
		Items = Entry ? FindFProperty<FArrayProperty>(Entry->Struct, TEXT("AssetUserData")) : nullptr;
		Item = Items ? CastField<FObjectPropertyBase>(Items->Inner) : nullptr;
	}

	explicit operator bool() const { return Item != nullptr; }

	// Every object, entry by entry.
	void ForEach(UObject* Pack, TFunctionRef<void(UObject*)> Visit) const
	{
		FScriptArrayHelper Entries(List, List->ContainerPtrToValuePtr<void>(Pack));
		for (int32 E = 0; E < Entries.Num(); ++E)
		{
			FScriptArrayHelper Objects(Items, Items->ContainerPtrToValuePtr<void>(Entries.GetRawPtr(E)));
			for (int32 I = 0; I < Objects.Num(); ++I)
			{
				Visit(Item->GetObjectPropertyValue(Objects.GetRawPtr(I)));
			}
		}
	}

	// The objects Match picks are replaced by New: in each entry the first one becomes New, the others are taken out.
	int32 Replace(UObject* Pack, TFunctionRef<bool(const UObject*)> Match, UObject* New) const
	{
		int32 Picked = 0;
		FScriptArrayHelper Entries(List, List->ContainerPtrToValuePtr<void>(Pack));
		for (int32 E = 0; E < Entries.Num(); ++E)
		{
			FScriptArrayHelper Objects(Items, Items->ContainerPtrToValuePtr<void>(Entries.GetRawPtr(E)));
			bool bPlaced = false;
			for (int32 I = 0; I < Objects.Num(); ++I)
			{
				bPlaced = bPlaced || Item->GetObjectPropertyValue(Objects.GetRawPtr(I)) == New;
			}
			for (int32 I = 0; I < Objects.Num(); ++I)
			{
				UObject* Current = Item->GetObjectPropertyValue(Objects.GetRawPtr(I));
				if (!Current || Current == New || !Match(Current))
				{
					continue;
				}
				++Picked;
				if (!bPlaced)
				{
					Item->SetObjectPropertyValue(Objects.GetRawPtr(I), New);
					bPlaced = true;
				}
				else
				{
					Objects.RemoveValues(I, 1);
					--I;
				}
			}
		}
		return Picked;
	}
};

// Makes a pack of this project match an edit (the package is marked dirty and added to Dirty; saving is the caller's).
bool ApplyPackEdit(const FString& Row, const FPackEdit& Edit, TArray<UPackage*>& Dirty, FString& Report)
{
	UObject* Pack = LoadPack(Row);
	if (!Pack)
	{
		Report += FString::Printf(TEXT("CharaSpec_%s: ERROR: the pack does not load\n"), *Row);
		return false;
	}
	if (IsCookedAsset(Pack))
	{
		Report += FString::Printf(TEXT("CharaSpec_%s: ERROR: a cooked game copy cannot be saved; make it editable first\n"), *Row);
		return false;
	}
	const FPackList Classes(Pack, TEXT("AssetClassList"));
	const FPackList Datas(Pack, TEXT("AssetDataList"));
	if (!Classes || !Datas)
	{
		Report += FString::Printf(TEXT("CharaSpec_%s: ERROR: %s is not an End Asset Data Asset (no Asset Class List / Asset Data List)\n"), *Row, *Pack->GetClass()->GetName());
		return false;
	}
	bool bOk = true;
	bool bModified = false;
	const auto Put = [&](const FString& Path, const FPackList& List, const TCHAR* What, TFunctionRef<bool(const UObject*)> Match)
	{
		if (Path.IsEmpty())
		{
			return;
		}
		// The new asset is one of a kind with what it replaces.
		UObject* Old = nullptr;
		List.ForEach(Pack, [&](UObject* Object) { if (!Old && Object && Match(Object)) { Old = Object; } });
		if (!Old)
		{
			Report += FString::Printf(TEXT("CharaSpec_%s: no %s to replace\n"), *Row, What);
			return;
		}
		FString Error;
		UObject* New = GameObject(Path, Old->GetClass()->GetPathName(), Error);
		if (!New)
		{
			Report += FString::Printf(TEXT("CharaSpec_%s: ERROR: %s %s not set: %s\n"), *Row, What, *Path, Error.IsEmpty() ? TEXT("not found") : *Error);
			bOk = false;
			return;
		}
		if (!bModified)
		{
			Pack->Modify();
			bModified = true;
		}
		const int32 Picked = List.Replace(Pack, Match, New);
		Report += FString::Printf(TEXT("CharaSpec_%s: %s %s (in place of %d)\n"), *Row, What, *New->GetPathName(), Picked);
	};
	Put(Edit.Blueprint, Classes, TEXT("blueprint"), [](const UObject* Object) { return InFolder(Object, TEXT("/Game/BluePrint/Character/")); });
	Put(Edit.Voice, Datas, TEXT("voice"), [](const UObject* Object) { return InFolder(Object, TEXT("/Game/Sound/Voice/")); });
	Put(Edit.LipSync, Datas, TEXT("lip sync"), [](const UObject* Object) { return InFolder(Object, TEXT("/Game/LipSync/")); });
	Put(Edit.Effect, Datas, TEXT("effect pack"), [](const UObject* Object) { return IsEffectPack(Object); });
	if (bModified)
	{
		Pack->PostEditChange();
		Pack->MarkPackageDirty();
		Dirty.AddUnique(Pack->GetOutermost());
	}
	return bOk;
}

// ------------------------------------------------------------------------------------------------
// Weapon swaps (editor 1.6; packs and socket stand-ins 1.7)
// ------------------------------------------------------------------------------------------------
struct FWeaponRowPlan
{
	FString Row;
	bool bNamed = false;     // named in Weapons itself, not only through a name ending in *
	FPackContents Pack;      // the pack as it is
	FPackContents After;     // the pack once Apply has edited it
	FPackEdit Edit;
	bool bSpawnsNew = false; // its pack spawns the new weapon's blueprint (once edited)
	TArray<FString> Notes;
	TArray<FWeaponFieldChange> Changes;
};

struct FWeaponSwapPlan
{
	FString NewWeapon;         // CharaSpec row
	FString NewModel;          // its model: a weapon's model and blueprint are named like its row
	FString NewRowModel;       // what the new weapon's own row says now (another swap may have changed it)
	FString Error;             // the swap cannot be applied
	TArray<FString> Unknown;   // Weapons entries that name no row
	TArray<FString> RowNames;  // the replaced rows
	TArray<FWeaponRowPlan> Rows;
	FString WeaponSkeleton;    // the family's member (object path)
	FString NewWeaponSkeleton; // the family's hub (object path)
	bool bWeaponSkeletonFromFolder = false;
	bool bNewSkeletonFromFolder = false;
};

// The rows a swap replaces: exact row names (also put in Named), or every row that starts with a name ending in * (never
// the new one).
TArray<FString> SwapRowsOf(const TArray<FString>& Items, const FString& New, const FCharaSpecTable& Table, TArray<FString>& Unknown, TArray<FString>& Named)
{
	TArray<FString> Rows;
	for (const FString& Item : CleanList(Items, false))
	{
		if (Item.EndsWith(TEXT("*")))
		{
			const FString Prefix = Item.LeftChop(1).TrimStartAndEnd();
			int32 Found = 0;
			for (const FName& Name : Table.Rows)
			{
				const FString Row = Name.ToString();
				if (!Prefix.IsEmpty() && Row.StartsWith(Prefix, ESearchCase::IgnoreCase) && !Row.Equals(New, ESearchCase::IgnoreCase))
				{
					Rows.AddUnique(Row);
					++Found;
				}
			}
			if (Found == 0)
			{
				Unknown.Add(Item);
			}
			continue;
		}
		const FString Row = CharaSpecRowName(Item);
		if (Row.IsEmpty() || (Table.bAvailable && !Table.Has(Row)))
		{
			Unknown.Add(Item);
			continue;
		}
		if (!Row.Equals(New, ESearchCase::IgnoreCase))
		{
			Rows.AddUnique(Row);
			Named.AddUnique(Row);
		}
	}
	Rows.Sort();
	return Rows;
}

// bRows: also read each replaced weapon's pack and work out what Apply writes into it and its row. bPackEdits: Apply may
// edit the packs (Apply To Packs on).
FWeaponSwapPlan PlanWeaponSwap(const FEndWeaponSwap& Swap, const FCharaSpecTable& Table, bool bRows, bool bPackEdits)
{
	FWeaponSwapPlan Plan;
	Plan.NewWeapon = CharaSpecRowName(Swap.NewWeapon);
	if (Plan.NewWeapon.IsEmpty())
	{
		Plan.Error = TEXT("New Weapon is empty: name the CharaSpec row of the weapon that takes their place, e.g. WE0011_00_Vincent_Quiksilver");
	}
	else if (Table.bAvailable && !Table.Has(Plan.NewWeapon))
	{
		Plan.Error = Plan.NewWeapon + TEXT(" is not a row of ") + Table.Package;
	}
	// The game names a weapon's model (and its blueprint) like its CharaSpec row. The row itself is not asked: another
	// swap may have changed it (Cloud's Buster Sword row describing Vincent's gun, while Sephiroth's Masamune becomes the
	// Buster Sword).
	Plan.NewModel = Plan.NewWeapon;
	if (Plan.Error.IsEmpty() && Table.bAvailable)
	{
		Plan.NewRowModel = Table.Field(Plan.NewWeapon, TEXT("ContentsModel"));
	}
	TArray<FString> Named;
	Plan.RowNames = SwapRowsOf(Swap.Weapons, Plan.NewWeapon, Table, Plan.Unknown, Named);

	// Skeletons of the cutscene family: as set, or the ones in the model folders.
	if (!Swap.NewWeaponSkeleton.IsNull())
	{
		Plan.NewWeaponSkeleton = SoftPath(Swap.NewWeaponSkeleton);
	}
	else if (!Plan.NewModel.IsEmpty())
	{
		Plan.NewWeaponSkeleton = WeaponSkeletonPathOf(Plan.NewModel);
		Plan.bNewSkeletonFromFolder = true;
	}
	if (!Swap.WeaponSkeleton.IsNull())
	{
		Plan.WeaponSkeleton = SoftPath(Swap.WeaponSkeleton);
	}
	else
	{
		// The base weapon (id ending in _00) has the skeleton its variants share: WE0000_00's for every one of Cloud's.
		FString Base;
		for (const FString& Row : Plan.RowNames)
		{
			if (ModelIdOf(Row).EndsWith(TEXT("_00")))
			{
				Base = Row;
				break;
			}
		}
		if (Base.IsEmpty() && Plan.RowNames.Num() > 0)
		{
			Base = Plan.RowNames[0];
		}
		if (!Base.IsEmpty())
		{
			Plan.WeaponSkeleton = WeaponSkeletonPathOf(Base);
			Plan.bWeaponSkeletonFromFolder = true;
		}
	}
	if (!bRows || !Plan.Error.IsEmpty() || !Table.bAvailable)
	{
		return Plan;
	}
	const bool bTools = bPackEdits && GameObjectToolsLoaded();
	FString NewBlueprint;  // looked up once
	FString NewEffect;
	bool bEffectLooked = false;
	for (const FString& Row : Plan.RowNames)
	{
		FWeaponRowPlan RowPlan;
		RowPlan.Row = Row;
		RowPlan.bNamed = Named.Contains(Row);
		RowPlan.Pack = ReadPack(Row);
		RowPlan.After = RowPlan.Pack;
		RowPlan.bSpawnsNew = RowPlan.Pack.Blueprints.ContainsByPredicate([&](const FString& Blueprint) { return Blueprint.Equals(Plan.NewWeapon, ESearchCase::IgnoreCase); });
		const bool bEditable = RowPlan.Pack.bInProject && !RowPlan.Pack.bCooked;
		if (!RowPlan.bSpawnsNew && bEditable && bPackEdits)
		{
			if (!bTools)
			{
				RowPlan.Notes.Add(GameObjectToolsMissing);
			}
			else
			{
				if (NewBlueprint.IsEmpty())
				{
					NewBlueprint = BlueprintClassPathOf(Plan.NewWeapon);
				}
				RowPlan.Edit.Blueprint = NewBlueprint;
				RowPlan.After.Blueprints = {Plan.NewWeapon};
				RowPlan.bSpawnsNew = true;
			}
		}
		// The new weapon's own effects in place of the old weapon's (the effect pack is named like the weapon's row).
		const FString EffectName = Plan.NewWeapon + TEXT("_Effect__Pack");
		if (RowPlan.bSpawnsNew && bEditable && bTools && RowPlan.Pack.Effects.Num() > 0 &&
			!(RowPlan.Pack.Effects.Num() == 1 && RowPlan.Pack.Effects[0].Equals(EffectName, ESearchCase::IgnoreCase)))
		{
			if (!bEffectLooked)
			{
				NewEffect = GameObjectPathOf(EffectName, TEXT("/Game/Effect/"));
				bEffectLooked = true;
			}
			if (!NewEffect.IsEmpty())
			{
				RowPlan.Edit.Effect = NewEffect;
				RowPlan.After.Effects = {EffectName};
			}
			else
			{
				RowPlan.Notes.Add(FString::Printf(TEXT("the game has no %s: the pack keeps loading %s"), *EffectName, *FString::Join(RowPlan.Pack.Effects, TEXT(", "))));
			}
		}
		if (RowPlan.bSpawnsNew)
		{
			const FString Model = Table.Field(Row, TEXT("ContentsModel"));
			if (!Model.Equals(Plan.NewModel, ESearchCase::IgnoreCase))
			{
				RowPlan.Changes.Add({TEXT("ContentsModel"), Model, Plan.NewModel});
			}
			// The new weapon's own spec loads alongside (as SephirothOverCloud does it), unless another swap made that spec
			// load a different weapon.
			const bool bNewRowIsItself = Plan.NewRowModel.IsEmpty() || Plan.NewRowModel.Equals(Plan.NewWeapon, ESearchCase::IgnoreCase) ||
				Plan.NewRowModel.Equals(TEXT("None"), ESearchCase::IgnoreCase);
			const FString SharedText = Table.Field(Row, TEXT("SharedCharaSpecList_Array"));
			TArray<FString> Shared = NamesInText(SharedText);
			if (bNewRowIsItself && !Shared.Contains(Plan.NewWeapon))
			{
				Shared.Add(Plan.NewWeapon);
				RowPlan.Changes.Add({TEXT("SharedCharaSpecList_Array"), SharedText, ArrayText(Shared)});
			}
			struct FLoaded
			{
				const TCHAR* Field;
				const TArray<FString>* Items;
			};
			const FLoaded Loaded[] = {
				{TEXT("ContentsEffect_Array"), &RowPlan.After.Effects},
				{TEXT("ContentsSoundSE_Array"), &RowPlan.After.SoundSE},
				{TEXT("ContentsSoundAutoSE_Array"), &RowPlan.After.SoundAutoSE},
			};
			for (const FLoaded& Field : Loaded)
			{
				const FString Text = Table.Field(Row, Field.Field);
				if (!SameNames(NamesInText(Text), *Field.Items))
				{
					RowPlan.Changes.Add({Field.Field, Text, ArrayText(*Field.Items)});
				}
			}
		}
		Plan.Rows.Add(MoveTemp(RowPlan));
	}
	return Plan;
}

// A row matched only through a name ending in * whose pack is the game's own: the swap does not include that weapon.
bool LeftOut(const FWeaponRowPlan& Row) { return !Row.bNamed && !Row.Pack.bInProject; }

// Why a replaced weapon's row is left as it is, or empty when Apply can write it.
FString WeaponRowProblem(const FWeaponRowPlan& Row, const FString& NewWeapon)
{
	if (!Row.Pack.bInProject)
	{
		return FString::Printf(TEXT("CharaSpec_%s is not in this project, so the game's own pack spawns the old weapon. Make that pack editable in this project, then press Apply To CharaSpec again"),
			*Row.Row);
	}
	if (!Row.bSpawnsNew)
	{
		if (Row.Pack.bCooked)
		{
			return FString::Printf(TEXT("CharaSpec_%s in this project is a cooked game copy, which cannot be saved: make it editable first"), *Row.Row);
		}
		return FString::Printf(TEXT("its pack spawns %s, not %s. Set Asset Class List > 0 > Asset User Data of CharaSpec_%s to %s_C (or turn Apply To Packs on)"),
			Row.Pack.Blueprints.Num() > 0 ? *FString::Join(Row.Pack.Blueprints, TEXT(", ")) : TEXT("no blueprint"), *NewWeapon, *Row.Row, *NewWeapon);
	}
	return FString();
}

// Report lines for a weapon's socket stand-ins: the old weapon's sockets the new one lacks, and each stand-in's socket.
void ReportWeaponSockets(const FEndWeaponSwap& Swap, const FWeaponSwapPlan& Plan, FString& Report, bool& bOk)
{
	USkeleton* New = Plan.NewWeaponSkeleton.IsEmpty() ? nullptr : Cast<USkeleton>(FSoftObjectPath(Plan.NewWeaponSkeleton).TryLoad());
	USkeleton* Old = Plan.WeaponSkeleton.IsEmpty() ? nullptr : Cast<USkeleton>(FSoftObjectPath(Plan.WeaponSkeleton).TryLoad());
	if (Old && New && Old != New)
	{
		TArray<FString> Lacks;
		for (const USkeletalMeshSocket* Socket : Old->Sockets)
		{
			if (Socket && !New->FindSocket(Socket->SocketName) && New->GetReferenceSkeleton().FindBoneIndex(Socket->SocketName) == INDEX_NONE &&
				!Swap.Sockets.ContainsByPredicate([&](const FEndSocketStandIn& Mine) { return Mine.Socket.TrimStartAndEnd().Equals(Socket->SocketName.ToString(), ESearchCase::IgnoreCase); }))
			{
				Lacks.Add(Socket->SocketName.ToString());
			}
		}
		if (Lacks.Num() > 0)
		{
			Report += FString::Printf(TEXT("    sockets of %s that %s lacks (moves made for the old weapon that hit with them do no damage; give each a stand-in under Sockets): %s\n"),
				*Old->GetName(), *New->GetName(), *ListText(Lacks));
		}
	}
	else if (!Old && Swap.Sockets.Num() == 0)
	{
		Report += FString::Printf(TEXT("    note: %s is not in this project, so its sockets are not compared (moves that hit with sockets the new weapon lacks need Sockets stand-ins)\n"),
			Plan.WeaponSkeleton.IsEmpty() ? TEXT("the old weapon's skeleton") : *ShortName(Plan.WeaponSkeleton));
	}
	for (const FEndSocketStandIn& Socket : Swap.Sockets)
	{
		const FString Wanted = Socket.Socket.TrimStartAndEnd();
		const FString Use = Socket.Use.TrimStartAndEnd();
		if (Wanted.IsEmpty() || Use.IsEmpty())
		{
			Report += TEXT("    WARNING: a socket stand-in without Socket or Use is left out\n");
			continue;
		}
		FString State = TEXT("checked in game");
		if (New)
		{
			if (const USkeletalMeshSocket* Found = New->FindSocket(FName(*Use)))
			{
				State = TEXT("socket on bone ") + Found->BoneName.ToString();
			}
			else if (New->GetReferenceSkeleton().FindBoneIndex(FName(*Use)) != INDEX_NONE)
			{
				State = TEXT("a bone");
			}
			else
			{
				State = TEXT("WARNING: neither a socket nor a bone of ") + New->GetName() + TEXT(" (a socket only the mesh has still works)");
			}
		}
		Report += FString::Printf(TEXT("    socket stand-in (Export Json): %s -> %s (%s)\n"), *Wanted, *Use, *State);
		if (Wanted.Equals(Use, ESearchCase::IgnoreCase))
		{
			Report += TEXT("    WARNING: a socket cannot stand in for itself; this one is left out\n");
		}
	}
	if (Swap.Sockets.Num() > 0 && Plan.NewWeaponSkeleton.IsEmpty())
	{
		Report += TEXT("    ERROR: socket stand-ins need New Weapon Skeleton (Advanced)\n");
		bOk = false;
	}
}

bool CheckWeaponSwap(const FEndWeaponSwap& Swap, int32 Index, const FCharaSpecTable& Table, bool bPackEdits, FString& Report)
{
	Report += FString::Printf(TEXT("Weapon swap %d: %s -> %s\n"), Index, *ListText(CleanList(Swap.Weapons, false)), *Swap.NewWeapon.TrimStartAndEnd());
	if (!Swap.bEnabled)
	{
		Report += TEXT("    disabled\n");
		return true;
	}
	bool bOk = true;
	const FWeaponSwapPlan Plan = PlanWeaponSwap(Swap, Table, true, bPackEdits);
	if (!Plan.Error.IsEmpty())
	{
		Report += TEXT("    ERROR: ") + Plan.Error + TEXT("\n");
		bOk = false;
	}
	for (const FString& Item : Plan.Unknown)
	{
		Report += FString::Printf(TEXT("    WARNING: %s names no row of %s\n"), *Item, *Table.Package);
	}
	if (!Table.bAvailable)
	{
		Report += TEXT("    note: the Rebirth data object tools (Rebirth Cooked Asset Preview plugin) are not loaded, so the CharaSpec rows and packs are not checked\n");
	}
	else if (Plan.Error.IsEmpty())
	{
		Report += FString::Printf(TEXT("    new weapon: blueprint and model %s\n"), *Plan.NewModel);
		if (!Plan.NewRowModel.IsEmpty() && !Plan.NewRowModel.Equals(Plan.NewWeapon, ESearchCase::IgnoreCase))
		{
			Report += FString::Printf(TEXT("    note: %s's own row describes %s now (another swap); the replaced weapons still get %s's own model\n"),
				*Plan.NewWeapon, *Plan.NewRowModel, *Plan.NewWeapon);
		}
		if (Plan.RowNames.Num() == 0)
		{
			Report += TEXT("    ERROR: no weapon rows to replace (Weapons)\n");
			bOk = false;
		}
		int32 Swapped = 0;
		for (const FWeaponRowPlan& Row : Plan.Rows)
		{
			if (LeftOut(Row))
			{
				Report += FString::Printf(TEXT("    %s: left out (its pack is the game's own, so it stays the old weapon)\n"), *Row.Row);
				continue;
			}
			for (const FString& Note : Row.Notes)
			{
				Report += FString::Printf(TEXT("    %s: note: %s\n"), *Row.Row, *Note);
			}
			const FString Problem = WeaponRowProblem(Row, Plan.NewWeapon);
			if (!Problem.IsEmpty())
			{
				Report += FString::Printf(TEXT("    %s: ERROR: %s\n"), *Row.Row, *Problem);
				bOk = false;
				continue;
			}
			++Swapped;
			if (Row.Edit.HasWork())
			{
				Report += FString::Printf(TEXT("    %s: Apply To CharaSpec makes its pack %s\n"), *Row.Row, *FString::Join(PackEditLines(Row.Edit, Row.Pack), TEXT("; ")));
			}
			TArray<FString> Loads = Row.After.Effects;
			Loads.Append(Row.After.SoundSE);
			Loads.Append(Row.After.SoundAutoSE);
			const FString Spawns = FString::Printf(TEXT("pack spawns %s%s%s"), *Plan.NewWeapon, Loads.Num() > 0 ? TEXT(" and loads ") : TEXT(""), *FString::Join(Loads, TEXT(", ")));
			if (Row.Changes.Num() == 0)
			{
				Report += FString::Printf(TEXT("    %s: %s; the row describes it\n"), *Row.Row, *Spawns);
				continue;
			}
			Report += FString::Printf(TEXT("    %s: %s, but the row still describes the old weapon: press Apply To CharaSpec\n"), *Row.Row, *Spawns);
			for (const FWeaponFieldChange& Change : Row.Changes)
			{
				Report += FString::Printf(TEXT("        %s: %s -> %s\n"), Change.Field, *FieldShown(Change.Field, Change.Current), *FieldShown(Change.Field, Change.Value));
			}
		}
		if (Plan.RowNames.Num() > 0 && Swapped == 0 && bOk)
		{
			Report += TEXT("    ERROR: none of these weapons' packs is in this project, so none of them spawns the new weapon\n");
			bOk = false;
		}
	}
	if (Swap.bCutsceneFamily)
	{
		if (Plan.NewWeaponSkeleton.IsEmpty() || Plan.WeaponSkeleton.IsEmpty())
		{
			Report += TEXT("    ERROR: cutscene family: the skeletons are not known; set Weapon Skeleton and New Weapon Skeleton (Advanced)\n");
			bOk = false;
		}
		else if (SamePath(Plan.NewWeaponSkeleton, Plan.WeaponSkeleton))
		{
			Report += TEXT("    cutscene family: not needed, both weapons are on ") + ShortName(Plan.NewWeaponSkeleton) + TEXT("\n");
		}
		else
		{
			Report += FString::Printf(TEXT("    cutscene family (Export Json): hub %s%s, member %s%s\n"), *Plan.NewWeaponSkeleton,
				Plan.bNewSkeletonFromFolder ? TEXT(" (its model folder's)") : TEXT(""), *Plan.WeaponSkeleton,
				Plan.bWeaponSkeletonFromFolder ? TEXT(" (the model folder's of the base weapon; set Weapon Skeleton if its cutscene animations use another)") : TEXT(""));
		}
	}
	ReportWeaponSockets(Swap, Plan, Report, bOk);
	return bOk;
}

// The weapon family a swap adds to the JSON, or null.
TSharedPtr<FJsonObject> WeaponFamilyJson(const FEndWeaponSwap& Swap, const FCharaSpecTable& Table)
{
	if (!Swap.bEnabled || !Swap.bCutsceneFamily)
	{
		return nullptr;
	}
	const FWeaponSwapPlan Plan = PlanWeaponSwap(Swap, Table, false, false);
	if (Plan.NewWeaponSkeleton.IsEmpty() || Plan.WeaponSkeleton.IsEmpty() || SamePath(Plan.NewWeaponSkeleton, Plan.WeaponSkeleton))
	{
		return nullptr;
	}
	TSharedRef<FJsonObject> Entry = MakeShared<FJsonObject>();
	Entry->SetStringField(TEXT("receiving_skeleton"), NormalizedObjectPath(Plan.NewWeaponSkeleton));
	Entry->SetArrayField(TEXT("animation_skeletons"), JsonStrings({NormalizedObjectPath(Plan.WeaponSkeleton)}));
	Entry->SetStringField(TEXT("method"), TEXT("family"));
	Entry->SetStringField(TEXT("hub"), NormalizedObjectPath(Plan.NewWeaponSkeleton));
	const TArray<FString> Requires = CleanList(Swap.RequiresPaks, true);
	if (Requires.Num() > 0)
	{
		Entry->SetArrayField(TEXT("requires_paks"), JsonStrings(Requires));
	}
	// The data object makes this entry from the swap again on every export (Import From Game Json skips it).
	Entry->SetStringField(TEXT("from_weapon_swap"), Plan.NewWeapon.IsEmpty() ? Swap.NewWeapon.TrimStartAndEnd() : Plan.NewWeapon);
	Entry->SetBoolField(TEXT("enabled"), true);
	return Entry;
}

// The animation set row with a weapon swap's socket stand-ins (on the new weapon's meshes), or null.
TSharedPtr<FJsonObject> WeaponSocketsJson(const FEndWeaponSwap& Swap, const FCharaSpecTable& Table)
{
	if (!Swap.bEnabled)
	{
		return nullptr;
	}
	TArray<TSharedPtr<FJsonValue>> Sockets;
	for (const FEndSocketStandIn& Socket : Swap.Sockets)
	{
		const FString Wanted = Socket.Socket.TrimStartAndEnd();
		const FString Use = Socket.Use.TrimStartAndEnd();
		if (!Wanted.IsEmpty() && !Use.IsEmpty() && !Wanted.Equals(Use, ESearchCase::IgnoreCase))
		{
			TSharedRef<FJsonObject> Object = MakeShared<FJsonObject>();
			Object->SetStringField(TEXT("socket"), Wanted);
			Object->SetStringField(TEXT("use"), Use);
			Sockets.Add(MakeShared<FJsonValueObject>(Object));
		}
	}
	const FWeaponSwapPlan Plan = PlanWeaponSwap(Swap, Table, false, false);
	if (Sockets.Num() == 0 || Plan.NewWeaponSkeleton.IsEmpty())
	{
		return nullptr;
	}
	// The mod puts a row's sockets on the meshes of its "skeleton"; its characters only have to be CharaSpec rows.
	TArray<FString> Characters = Plan.RowNames;
	if (Characters.Num() == 0 && !Plan.NewWeapon.IsEmpty())
	{
		Characters.Add(Plan.NewWeapon);
	}
	if (Characters.Num() == 0)
	{
		return nullptr;
	}
	TSharedRef<FJsonObject> Entry = MakeShared<FJsonObject>();
	Entry->SetArrayField(TEXT("characters"), JsonStrings(Characters));
	Entry->SetStringField(TEXT("skeleton"), NormalizedObjectPath(Plan.NewWeaponSkeleton));
	Entry->SetArrayField(TEXT("sockets"), Sockets);
	const TArray<FString> Requires = CleanList(Swap.RequiresPaks, true);
	if (Requires.Num() > 0)
	{
		Entry->SetArrayField(TEXT("requires_paks"), JsonStrings(Requires));
	}
	Entry->SetStringField(TEXT("from_weapon_swap"), Plan.NewWeapon.IsEmpty() ? Swap.NewWeapon.TrimStartAndEnd() : Plan.NewWeapon);
	Entry->SetBoolField(TEXT("enabled"), true);
	return Entry;
}

// ------------------------------------------------------------------------------------------------
// Character swaps (editor 1.7): another character in some CharaSpec rows' place (Cloud in Sephiroth's). Each replaced
// row's pack spawns the new character's blueprint and loads its voice; the row describes what its pack spawns and loads
// (model, voice, effects, sounds, AI), shares his spec, and holds his weapon where Weapon Socket says. The two skeletons
// become a family, and the rows' animation sets come from both characters' motion folders, the moveset's first.
// ------------------------------------------------------------------------------------------------
const TCHAR* MovesetText(EEndSwapMoveset Moveset) { return Moveset == EEndSwapMoveset::NewCharacter ? TEXT("new") : TEXT("replaced"); }

EEndSwapMoveset ParseMoveset(const FString& Text)
{
	for (const TCHAR* Own : {TEXT("new"), TEXT("new_character"), TEXT("own"), TEXT("his"), TEXT("hers")})
	{
		if (Text.TrimStartAndEnd().Equals(Own, ESearchCase::IgnoreCase))
		{
			return EEndSwapMoveset::NewCharacter;
		}
	}
	return EEndSwapMoveset::Replaced;
}

TSharedRef<FJsonObject> CharacterSwapToJson(const FEndCharacterSwap& Swap)
{
	TSharedRef<FJsonObject> Entry = MakeShared<FJsonObject>();
	Entry->SetArrayField(TEXT("characters"), JsonStrings(CleanList(Swap.Characters, false)));
	Entry->SetStringField(TEXT("new_character"), Swap.NewCharacter.TrimStartAndEnd());
	Entry->SetStringField(TEXT("moveset"), MovesetText(Swap.Moveset));
	if (!Swap.Voice.TrimStartAndEnd().IsEmpty())
	{
		Entry->SetStringField(TEXT("voice"), Swap.Voice.TrimStartAndEnd());
	}
	if (!Swap.WeaponSocket.TrimStartAndEnd().IsEmpty())
	{
		Entry->SetStringField(TEXT("weapon_socket"), Swap.WeaponSocket.TrimStartAndEnd());
	}
	if (!Swap.ReplacedSkeleton.IsNull())
	{
		Entry->SetStringField(TEXT("replaced_skeleton"), SoftPath(Swap.ReplacedSkeleton));
	}
	if (!Swap.NewSkeleton.IsNull())
	{
		Entry->SetStringField(TEXT("new_skeleton"), SoftPath(Swap.NewSkeleton));
	}
	const TArray<FString> Requires = CleanList(Swap.RequiresPaks, true);
	if (Requires.Num() > 0)
	{
		Entry->SetArrayField(TEXT("requires_paks"), JsonStrings(Requires));
	}
	Entry->SetBoolField(TEXT("enabled"), Swap.bEnabled);
	return Entry;
}

bool CharacterSwapFromJson(const TSharedPtr<FJsonObject>& Entry, FEndCharacterSwap& Swap)
{
	if (!Entry.IsValid())
	{
		return false;
	}
	Swap.Characters = CleanList(StringsOf(Entry->TryGetField(TEXT("characters"))), false);
	Swap.NewCharacter = StringField(Entry, TEXT("new_character"));
	Swap.Moveset = ParseMoveset(StringField(Entry, TEXT("moveset")));
	Swap.Voice = StringField(Entry, TEXT("voice"));
	Swap.WeaponSocket = StringField(Entry, TEXT("weapon_socket"));
	const FString Replaced = StringField(Entry, TEXT("replaced_skeleton"));
	const FString New = StringField(Entry, TEXT("new_skeleton"));
	if (!Replaced.IsEmpty())
	{
		Swap.ReplacedSkeleton = TSoftObjectPtr<USkeleton>(FSoftObjectPath(NormalizedObjectPath(Replaced)));
	}
	if (!New.IsEmpty())
	{
		Swap.NewSkeleton = TSoftObjectPtr<USkeleton>(FSoftObjectPath(NormalizedObjectPath(New)));
	}
	Swap.RequiresPaks = CleanList(StringsOf(Entry->TryGetField(TEXT("requires_paks"))), true);
	BoolField(Entry, TEXT("enabled"), Swap.bEnabled);
	return !Swap.NewCharacter.IsEmpty() || Swap.Characters.Num() > 0;
}

// The same swap as far as Import From Game Json matches them: the same new character, and a replaced row in common.
bool SameCharacterSwap(const FEndCharacterSwap& A, const FEndCharacterSwap& B)
{
	if (!CharaSpecRowName(A.NewCharacter).Equals(CharaSpecRowName(B.NewCharacter), ESearchCase::IgnoreCase))
	{
		return false;
	}
	const TArray<FString> Theirs = CleanList(B.Characters, false);
	for (const FString& Mine : CleanList(A.Characters, false))
	{
		if (Theirs.Contains(Mine))
		{
			return true;
		}
	}
	return A.Characters.Num() == 0 || B.Characters.Num() == 0;
}

struct FCharacterRowPlan
{
	FString Row;
	bool bNamed = false;           // named in Characters itself, not only through a name ending in *
	FPackContents Pack;            // the pack as it is
	FPackContents After;           // the pack once Apply has edited it
	FPackEdit Edit;
	TArray<FString> Folders;       // the replaced character's motion folders for this row
	FString Problem;               // why Apply leaves the row as it is (empty: it can write it)
	TArray<FString> Notes;
	TArray<FFieldChange> Changes;
};

struct FCharacterSwapPlan
{
	FString NewCharacter;          // CharaSpec row
	FString Error;                 // the swap cannot be applied
	TArray<FString> Unknown;       // Characters entries that name no row
	TArray<FString> RowNames;      // the replaced rows
	TArray<FCharacterRowPlan> Rows;
	FString ReplacedId;            // "PC0010_": the replaced character's models and blueprints start with it
	FString ReplacedSkeleton;      // object paths
	FString NewSkeleton;
	bool bReplacedSkeletonFromFolder = false;
	bool bNewSkeletonFromFolder = false;
	TArray<FString> NewFolders;    // the new character's motion folders
	FString NewFoldersFrom;        // where they come from (for the report)
	FString FieldActions;          // AnimationSetParentFolder for his own moveset, e.g. PC0000_Cloud
	FString NewSpec;               // his row that goes into the Shared CharaSpec Lists (empty: none)
	FString NewSpecNote;
	FString VoiceName, VoicePath;  // the swap's voice and where the game has it
	FString LipSyncName, LipSyncPath;
	TArray<FString> Equipment;     // the weapons the replaced rows equip
};

// A row of his that still describes him: its model is his, and its pack (when this project has it) spawns him.
bool RowDescribes(const FString& Row, const FString& Character, const FCharaSpecTable& Table)
{
	if (!Table.Has(Row) || !Table.Field(Row, TEXT("ContentsModel")).Equals(Character, ESearchCase::IgnoreCase))
	{
		return false;
	}
	const FPackContents Pack = ReadPack(Row);
	return !Pack.bInProject || Pack.Blueprints.ContainsByPredicate([&](const FString& Blueprint) { return IsBlueprintOf(Blueprint, Character); });
}

// The motion folders a row's pack lists sets of, else the row's field-action folder.
TArray<FString> RowFoldersOf(const FString& Row, const FPackContents& Pack, const FCharaSpecTable& Table)
{
	if (Pack.MotionFolders.Num() > 0)
	{
		return Pack.MotionFolders;
	}
	const FString Folder = Table.bAvailable ? Table.Field(Row, TEXT("AnimationSetParentFolder")) : FString();
	if (!Folder.IsEmpty() && !Folder.Equals(TEXT("None"), ESearchCase::IgnoreCase))
	{
		return {FString::Printf(TEXT("/Game/Motion/%s/%s"), KindFolderOf(Row), *Folder)};
	}
	return {};
}

// bRows: also work out what Apply To CharaSpec does to each replaced row and its pack. bPackEdits: Apply may edit packs.
FCharacterSwapPlan PlanCharacterSwap(const FEndCharacterSwap& Swap, const FCharaSpecTable& Table, bool bRows, bool bPackEdits)
{
	FCharacterSwapPlan Plan;
	Plan.NewCharacter = CharaSpecRowName(Swap.NewCharacter);
	if (Plan.NewCharacter.IsEmpty())
	{
		Plan.Error = TEXT("New Character is empty: name the CharaSpec row of the character that takes their place, e.g. PC0000_00_Cloud_Standard");
	}
	else if (Table.bAvailable && !Table.Has(Plan.NewCharacter))
	{
		Plan.Error = Plan.NewCharacter + TEXT(" is not a row of ") + Table.Package;
	}
	TArray<FString> Named;
	Plan.RowNames = SwapRowsOf(Swap.Characters, Plan.NewCharacter, Table, Plan.Unknown, Named);
	// Rows of the new character himself are never replaced by him.
	Plan.RowNames.RemoveAll([&](const FString& Row) { return IsBlueprintOf(Row, Plan.NewCharacter); });
	FString Base;
	for (const FString& Row : Plan.RowNames)
	{
		if (Named.Contains(Row) && ModelIdOf(Row).EndsWith(TEXT("_00")))
		{
			Base = Row;
			break;
		}
	}
	for (const FString& Row : Plan.RowNames)
	{
		if (Base.IsEmpty() && ModelIdOf(Row).EndsWith(TEXT("_00")))
		{
			Base = Row;
		}
	}
	if (Base.IsEmpty() && Plan.RowNames.Num() > 0)
	{
		Base = Plan.RowNames[0];
	}
	Plan.ReplacedId = Base.IsEmpty() ? FString() : CharacterIdOf(Base);
	if (!Swap.ReplacedSkeleton.IsNull())
	{
		Plan.ReplacedSkeleton = SoftPath(Swap.ReplacedSkeleton);
	}
	else if (!Base.IsEmpty())
	{
		Plan.ReplacedSkeleton = ModelSkeletonPathOf(Base);
		Plan.bReplacedSkeletonFromFolder = true;
	}
	if (!Swap.NewSkeleton.IsNull())
	{
		Plan.NewSkeleton = SoftPath(Swap.NewSkeleton);
	}
	else if (!Plan.NewCharacter.IsEmpty())
	{
		Plan.NewSkeleton = ModelSkeletonPathOf(Plan.NewCharacter);
		Plan.bNewSkeletonFromFolder = true;
	}
	// His motion folders: what his own pack lists, else his row's field-action folder while it still describes him, else
	// the folder named the way the game names them.
	if (!Plan.NewCharacter.IsEmpty())
	{
		const FPackContents His = ReadPack(Plan.NewCharacter);
		if (His.MotionFolders.Num() > 0)
		{
			Plan.NewFolders = His.MotionFolders;
			Plan.NewFoldersFrom = TEXT("the sets his pack in this project lists");
		}
		else if (Table.bAvailable && RowDescribes(Plan.NewCharacter, Plan.NewCharacter, Table) && RowFoldersOf(Plan.NewCharacter, His, Table).Num() > 0)
		{
			Plan.NewFolders = RowFoldersOf(Plan.NewCharacter, His, Table);
			Plan.NewFoldersFrom = TEXT("his CharaSpec row");
		}
		else if (!MotionFolderByName(Plan.NewCharacter).IsEmpty())
		{
			Plan.NewFolders = {MotionFolderByName(Plan.NewCharacter)};
			Plan.NewFoldersFrom = TEXT("his name");
		}
		Plan.FieldActions = Plan.NewFolders.Num() > 0 ? FPackageName::GetShortName(Plan.NewFolders[0]) : FString();
	}
	for (const FString& Row : Plan.RowNames)
	{
		FCharacterRowPlan RowPlan;
		RowPlan.Row = Row;
		RowPlan.bNamed = Named.Contains(Row);
		RowPlan.Pack = ReadPack(Row);
		RowPlan.After = RowPlan.Pack;
		RowPlan.Folders = RowFoldersOf(Row, RowPlan.Pack, Table);
		Plan.Rows.Add(MoveTemp(RowPlan));
	}
	if (!bRows || !Plan.Error.IsEmpty() || !Table.bAvailable)
	{
		return Plan;
	}

	// His spec in their Shared CharaSpec Lists, so what his blueprint needs loads with them: his own row while it still
	// describes him, else his _Reserve row (another swap may have changed his own, as SephirothOverCloud does).
	for (const FString& Candidate : {Plan.NewCharacter, Plan.NewCharacter + TEXT("_Reserve")})
	{
		if (RowDescribes(Candidate, Plan.NewCharacter, Table))
		{
			Plan.NewSpec = Candidate;
			break;
		}
	}
	if (Plan.NewSpec.IsEmpty())
	{
		Plan.NewSpecNote = FString::Printf(TEXT("neither %s nor %s_Reserve describes %s any more (another swap?), so no spec of his is shared"),
			*Plan.NewCharacter, *Plan.NewCharacter, *Plan.NewCharacter);
	}

	const bool bTools = bPackEdits && GameObjectToolsLoaded();
	const FString VoiceText = Swap.Voice.TrimStartAndEnd();
	if (!VoiceText.IsEmpty())
	{
		Plan.VoiceName = ShortName(NormalizedObjectPath(VoiceText));
		if (Plan.VoiceName.StartsWith(TEXT("VO_"), ESearchCase::IgnoreCase))
		{
			Plan.LipSyncName = TEXT("LSD_") + Plan.VoiceName.Mid(3);
		}
		if (bTools)
		{
			Plan.VoicePath = GameObjectPathOf(Plan.VoiceName, TEXT("/Game/Sound/Voice/"));
			Plan.LipSyncPath = Plan.LipSyncName.IsEmpty() ? FString() : GameObjectPathOf(Plan.LipSyncName, TEXT("/Game/LipSync/"));
		}
	}
	FString NewBlueprint; // looked up once
	for (FCharacterRowPlan& R : Plan.Rows)
	{
		const FString& Row = R.Row;
		for (const FString& Weapon : NamesInText(Table.Field(Row, TEXT("EquipmentCharaSpecList_Array"))))
		{
			Plan.Equipment.AddUnique(Weapon);
		}
		if (!R.Pack.bInProject)
		{
			if (R.bNamed)
			{
				R.Problem = FString::Printf(TEXT("CharaSpec_%s is not in this project, so the game's own pack spawns %s. Make that pack editable in this project, then press Apply To CharaSpec again"),
					*Row, *Row);
			}
			continue;
		}
		const bool bEditable = !R.Pack.bCooked;
		const bool bHis = R.Pack.Blueprints.ContainsByPredicate([&](const FString& Blueprint) { return IsBlueprintOf(Blueprint, Plan.NewCharacter); });
		if (!bHis)
		{
			if (!bEditable)
			{
				R.Problem = FString::Printf(TEXT("CharaSpec_%s in this project is a cooked game copy, which cannot be saved: make it editable first"), *Row);
			}
			else if (!bPackEdits)
			{
				R.Problem = FString::Printf(TEXT("its pack spawns %s, not %s. Set Asset Class List > 0 > Asset User Data of CharaSpec_%s to %s_C (or turn Apply To Packs on)"),
					R.Pack.Blueprints.Num() > 0 ? *FString::Join(R.Pack.Blueprints, TEXT(", ")) : TEXT("no blueprint"), *Plan.NewCharacter, *Row, *Plan.NewCharacter);
			}
			else if (!bTools)
			{
				R.Problem = FString::Printf(TEXT("its pack spawns %s, and %s"), R.Pack.Blueprints.Num() > 0 ? *FString::Join(R.Pack.Blueprints, TEXT(", ")) : TEXT("no blueprint"),
					GameObjectToolsMissing);
			}
			else
			{
				if (NewBlueprint.IsEmpty())
				{
					NewBlueprint = BlueprintClassPathOf(Plan.NewCharacter);
				}
				R.Edit.Blueprint = NewBlueprint;
				R.After.Blueprints = {Plan.NewCharacter};
			}
		}
		if (!Plan.VoiceName.IsEmpty() && bEditable && bPackEdits)
		{
			if (R.Pack.Voices.Num() == 0)
			{
				R.Notes.Add(TEXT("its pack loads no voice, so it gets none (the Voice replaces a pack's voice)"));
			}
			else if (!(R.Pack.Voices.Num() == 1 && R.Pack.Voices[0].Equals(Plan.VoiceName, ESearchCase::IgnoreCase)))
			{
				if (!bTools)
				{
					R.Notes.Add(FString::Printf(TEXT("Voice not set: %s"), GameObjectToolsMissing));
				}
				else if (Plan.VoicePath.IsEmpty())
				{
					R.Notes.Add(FString::Printf(TEXT("Voice not set: the game's paks have no %s under /Game/Sound/Voice/"), *Plan.VoiceName));
				}
				else
				{
					R.Edit.Voice = Plan.VoicePath;
					R.After.Voices = {Plan.VoiceName};
					if (!Plan.LipSyncPath.IsEmpty() && R.Pack.LipSyncs.Num() > 0)
					{
						R.Edit.LipSync = Plan.LipSyncPath;
						R.After.LipSyncs = {Plan.LipSyncName};
					}
					else if (R.Pack.LipSyncs.Num() > 0)
					{
						R.Notes.Add(FString::Printf(TEXT("the game's paks have no lip sync %s for that voice: the pack keeps %s"),
							*Plan.LipSyncName, *FString::Join(R.Pack.LipSyncs, TEXT(", "))));
					}
				}
			}
		}
		if (!R.Problem.IsEmpty())
		{
			continue;
		}

		// The row describes what its pack spawns and loads.
		const auto Want = [&](const TCHAR* Field, const FString& Value, bool bSet)
		{
			const FString Current = Table.Field(Row, Field);
			const bool bSame = bSet ? SameNames(NamesInText(Current), NamesInText(Value)) : SlotsInText(Current) == SlotsInText(Value);
			if (!bSame && !(Current.IsEmpty() && Value == TEXT("()")))
			{
				R.Changes.Add({Field, Current, Value});
			}
		};
		TArray<FString> Models;
		for (const FString& Blueprint : R.After.Blueprints)
		{
			if (IsBlueprintOf(Blueprint, Plan.NewCharacter))
			{
				Models.AddUnique(Blueprint);
			}
		}
		if (Models.Num() == 1)
		{
			const FString Model = Table.Field(Row, TEXT("ContentsModel"));
			if (!Model.Equals(Models[0], ESearchCase::IgnoreCase))
			{
				R.Changes.Add({TEXT("ContentsModel"), Model, Models[0]});
			}
		}
		else if (Models.Num() > 1)
		{
			R.Notes.Add(TEXT("its pack spawns several of his blueprints, so its model is left as it is: ") + FString::Join(Models, TEXT(", ")));
		}
		if (R.After.Voices.Num() > 0)
		{
			Want(TEXT("ContentSoundVoice_Array"), ArrayText(R.After.Voices), true);
			// A voice that switches with story flags (Cloud's past and insanity lines) is the old character's: it goes.
			const TArray<FString> Packs = NamesInText(Table.Field(Row, TEXT("SoundVoisePack_Array")));
			if (Packs.Num() > 0 && !Packs.Contains(R.After.Voices[0]))
			{
				Want(TEXT("SoundVoisePack_Array"), TEXT("()"), true);
				Want(TEXT("SoundVoisePackEnableStoryFlag_Array"), TEXT("()"), true);
			}
		}
		Want(TEXT("ContentsEffect_Array"), ArrayText(R.After.Effects), true);
		Want(TEXT("ContentsSoundSE_Array"), ArrayText(R.After.SoundSE), true);
		Want(TEXT("ContentsSoundAutoSE_Array"), ArrayText(R.After.SoundAutoSE), true);
		if (R.After.AIBlueprints.Num() > 0)
		{
			Want(TEXT("End2AIList_Array"), ArrayText(R.After.AIBlueprints), true);
		}
		if (!Plan.NewSpec.IsEmpty())
		{
			const FString SharedText = Table.Field(Row, TEXT("SharedCharaSpecList_Array"));
			TArray<FString> Shared = NamesInText(SharedText);
			if (!Shared.Contains(Plan.NewSpec))
			{
				Shared.Add(Plan.NewSpec);
				R.Changes.Add({TEXT("SharedCharaSpecList_Array"), SharedText, ArrayText(Shared)});
			}
		}
		const FString Socket = Swap.WeaponSocket.TrimStartAndEnd();
		if (!Socket.IsEmpty())
		{
			const FString Current = Table.Field(Row, TEXT("OverrideWeaponSocketNames_Array"));
			TArray<FString> Slots = SlotsInText(Current);
			if (Slots.Num() == 0)
			{
				Slots.Add(Socket);
			}
			else
			{
				Slots[0] = Socket;
			}
			Want(TEXT("OverrideWeaponSocketNames_Array"), ArrayText(Slots), false);
		}
		if (Swap.Moveset == EEndSwapMoveset::NewCharacter && !Plan.FieldActions.IsEmpty())
		{
			const FString Current = Table.Field(Row, TEXT("AnimationSetParentFolder"));
			if (!Current.Equals(Plan.FieldActions, ESearchCase::IgnoreCase))
			{
				R.Changes.Add({TEXT("AnimationSetParentFolder"), Current, Plan.FieldActions});
			}
			// Sets the old character's folder has for special scenes (Cloud's bike, piano, ...) are not in his.
			if (NamesInText(Table.Field(Row, TEXT("OverrideAnimationSetString_Array"))).Num() > 0)
			{
				Want(TEXT("OverrideAnimationSetString_Array"), TEXT("()"), true);
			}
		}
	}
	return Plan;
}

// A row matched only through * whose pack is the game's own: the swap does not include it.
bool LeftOut(const FCharacterRowPlan& Row) { return !Row.bNamed && !Row.Pack.bInProject; }

// The family a character swap adds to the JSON (hub: the skeleton whose moves are played), or null.
TSharedPtr<FJsonObject> CharacterFamilyJson(const FEndCharacterSwap& Swap, const FCharacterSwapPlan& Plan)
{
	const bool bTheirs = Swap.Moveset == EEndSwapMoveset::Replaced;
	const FString Hub = bTheirs ? Plan.ReplacedSkeleton : Plan.NewSkeleton;
	const FString Member = bTheirs ? Plan.NewSkeleton : Plan.ReplacedSkeleton;
	if (!Swap.bEnabled || !Plan.Error.IsEmpty() || Hub.IsEmpty() || Member.IsEmpty() || SamePath(Hub, Member))
	{
		return nullptr;
	}
	TSharedRef<FJsonObject> Entry = MakeShared<FJsonObject>();
	Entry->SetStringField(TEXT("receiving_skeleton"), NormalizedObjectPath(Hub));
	Entry->SetArrayField(TEXT("animation_skeletons"), JsonStrings({NormalizedObjectPath(Member)}));
	Entry->SetStringField(TEXT("method"), TEXT("family"));
	Entry->SetStringField(TEXT("hub"), NormalizedObjectPath(Hub));
	const TArray<FString> Requires = CleanList(Swap.RequiresPaks, true);
	if (Requires.Num() > 0)
	{
		Entry->SetArrayField(TEXT("requires_paks"), JsonStrings(Requires));
	}
	// The data object makes this entry from the swap again on every export (Import From Game Json skips it).
	Entry->SetStringField(TEXT("from_character_swap"), Plan.NewCharacter);
	Entry->SetBoolField(TEXT("enabled"), true);
	return Entry;
}

// The animation set rows a character swap adds: the swapped rows grouped by their own motion folders, each with both
// characters' folders as battle and field sources, the moveset's first.
TArray<TSharedPtr<FJsonObject>> CharacterRowsJson(const FEndCharacterSwap& Swap, const FCharacterSwapPlan& Plan)
{
	TArray<TSharedPtr<FJsonObject>> Out;
	if (!Swap.bEnabled || !Plan.Error.IsEmpty())
	{
		return Out;
	}
	TArray<TPair<TArray<FString>, TArray<FString>>> Groups; // folders -> rows
	for (const FCharacterRowPlan& Row : Plan.Rows)
	{
		if (!Row.Pack.bInProject)
		{
			continue; // the game's own pack: the old character stays there
		}
		TPair<TArray<FString>, TArray<FString>>* Group = Groups.FindByPredicate([&](const TPair<TArray<FString>, TArray<FString>>& G) { return G.Key == Row.Folders; });
		if (!Group)
		{
			Group = &Groups.Emplace_GetRef(Row.Folders, TArray<FString>());
		}
		Group->Value.Add(Row.Row);
	}
	const TArray<FString> Requires = CleanList(Swap.RequiresPaks, true);
	for (const TPair<TArray<FString>, TArray<FString>>& Group : Groups)
	{
		TArray<FString> Sources = Swap.Moveset == EEndSwapMoveset::Replaced ? Group.Key : Plan.NewFolders;
		for (const FString& Folder : Swap.Moveset == EEndSwapMoveset::Replaced ? Plan.NewFolders : Group.Key)
		{
			Sources.AddUnique(Folder);
		}
		if (Sources.Num() == 0)
		{
			continue;
		}
		TSharedRef<FJsonObject> Entry = MakeShared<FJsonObject>();
		Entry->SetArrayField(TEXT("characters"), JsonStrings(Group.Value));
		Entry->SetArrayField(TEXT("battle"), JsonStrings(Sources));
		Entry->SetArrayField(TEXT("field"), JsonStrings(Sources));
		if (Requires.Num() > 0)
		{
			Entry->SetArrayField(TEXT("requires_paks"), JsonStrings(Requires));
		}
		Entry->SetStringField(TEXT("from_character_swap"), Plan.NewCharacter);
		Entry->SetBoolField(TEXT("enabled"), true);
		Out.Add(Entry);
	}
	return Out;
}

bool CheckCharacterSwap(const FEndCharacterSwap& Swap, int32 Index, const FCharaSpecTable& Table, bool bPackEdits, FString& Report)
{
	Report += FString::Printf(TEXT("Character swap %d: %s -> %s\n"), Index, *ListText(CleanList(Swap.Characters, false)), *Swap.NewCharacter.TrimStartAndEnd());
	if (!Swap.bEnabled)
	{
		Report += TEXT("    disabled\n");
		return true;
	}
	bool bOk = true;
	const FCharacterSwapPlan Plan = PlanCharacterSwap(Swap, Table, true, bPackEdits);
	if (!Plan.Error.IsEmpty())
	{
		Report += TEXT("    ERROR: ") + Plan.Error + TEXT("\n");
		return false;
	}
	for (const FString& Item : Plan.Unknown)
	{
		Report += FString::Printf(TEXT("    WARNING: %s names no row of %s\n"), *Item, *Table.Package);
	}
	if (Plan.RowNames.Num() == 0)
	{
		Report += TEXT("    ERROR: no rows to replace (Characters)\n");
		return false;
	}
	const bool bTheirs = Swap.Moveset == EEndSwapMoveset::Replaced;
	Report += FString::Printf(TEXT("    moves: %s (%s)\n"), bTheirs ? TEXT("the replaced character's, his own fill in") : TEXT("his own, the replaced character's fill in"),
		Plan.NewFolders.Num() > 0 ? *FString::Printf(TEXT("his motion folders from %s: %s"), *Plan.NewFoldersFrom, *ListText(Plan.NewFolders)) : TEXT("WARNING: his motion folders are not known"));
	if (!Table.bAvailable)
	{
		Report += TEXT("    note: the Rebirth data object tools (Rebirth Cooked Asset Preview plugin) are not loaded, so the CharaSpec rows and packs are not checked\n");
	}
	else
	{
		if (!Plan.VoiceName.IsEmpty())
		{
			Report += FString::Printf(TEXT("    voice: %s%s\n"), *Plan.VoiceName, Plan.VoicePath.IsEmpty() ? TEXT(" (not found in the game's paks yet)") :
				*FString::Printf(TEXT(" (%s%s)"), *Plan.VoicePath, Plan.LipSyncPath.IsEmpty() ? TEXT(", no lip sync of that name") : *(TEXT(", lip sync ") + Plan.LipSyncPath)));
		}
		Report += Plan.NewSpec.IsEmpty() ? TEXT("    WARNING: ") + Plan.NewSpecNote + TEXT("\n")
										 : FString::Printf(TEXT("    shared spec: %s (loads what his blueprint needs with the rows)\n"), *Plan.NewSpec);
		int32 Swapped = 0;
		for (const FCharacterRowPlan& Row : Plan.Rows)
		{
			if (LeftOut(Row))
			{
				Report += FString::Printf(TEXT("    %s: left out (its pack is the game's own, so it stays the old character; make CharaSpec_%s editable in this project to swap it too)\n"),
					*Row.Row, *Row.Row);
				continue;
			}
			for (const FString& Note : Row.Notes)
			{
				Report += FString::Printf(TEXT("    %s: note: %s\n"), *Row.Row, *Note);
			}
			if (!Row.Problem.IsEmpty())
			{
				Report += FString::Printf(TEXT("    %s: ERROR: %s\n"), *Row.Row, *Row.Problem);
				bOk = false;
				continue;
			}
			++Swapped;
			if (Row.Edit.HasWork())
			{
				Report += FString::Printf(TEXT("    %s: Apply To CharaSpec makes its pack %s\n"), *Row.Row, *FString::Join(PackEditLines(Row.Edit, Row.Pack), TEXT("; ")));
			}
			if (Row.Changes.Num() == 0)
			{
				Report += FString::Printf(TEXT("    %s: pack spawns %s; the row describes it\n"), *Row.Row, *ListText(Row.After.Blueprints));
				continue;
			}
			Report += FString::Printf(TEXT("    %s: pack spawns %s; Apply To CharaSpec writes:\n"), *Row.Row, *ListText(Row.After.Blueprints));
			for (const FFieldChange& Change : Row.Changes)
			{
				Report += FString::Printf(TEXT("        %s: %s -> %s\n"), Change.Field, *FieldShown(Change.Field, Change.Current), *FieldShown(Change.Field, Change.Value));
			}
		}
		if (Swapped == 0 && bOk)
		{
			Report += TEXT("    ERROR: none of these rows' packs is in this project, so none of them spawns him\n");
			bOk = false;
		}
		TArray<FString> Weapons;
		for (const FString& Weapon : Plan.Equipment)
		{
			if (!Weapon.StartsWith(CharacterIdOf(Plan.NewCharacter)))
			{
				Weapons.Add(Weapon);
			}
		}
		if (Weapons.Num() > 0)
		{
			Report += FString::Printf(TEXT("    note: these rows equip %s: add a weapon swap (New Weapon: his weapon, e.g. his _00 one) to put his weapon in his hands, with Sockets so the moves still hit\n"),
				*ListText(Weapons));
		}
		if (!Swap.WeaponSocket.TrimStartAndEnd().IsEmpty())
		{
			Report += FString::Printf(TEXT("    weapon socket: %s (slot 0, the equipped weapon)\n"), *Swap.WeaponSocket.TrimStartAndEnd());
		}
	}
	// What Export Json adds.
	const FString Hub = bTheirs ? Plan.ReplacedSkeleton : Plan.NewSkeleton;
	const FString Member = bTheirs ? Plan.NewSkeleton : Plan.ReplacedSkeleton;
	if (Hub.IsEmpty() || Member.IsEmpty())
	{
		Report += TEXT("    ERROR: family: the skeletons are not known; set Replaced Skeleton and New Skeleton (Advanced)\n");
		bOk = false;
	}
	else if (SamePath(Hub, Member))
	{
		Report += TEXT("    family: not needed, both characters are on ") + ShortName(Hub) + TEXT("\n");
	}
	else
	{
		for (const FString& Skeleton : {Hub, Member})
		{
			if (!FSoftObjectPath(Skeleton).TryLoad() && !InProject(Skeleton))
			{
				Report += FString::Printf(TEXT("    note: %s is not in this project (checked in game)%s\n"), *Skeleton,
					(SamePath(Skeleton, Plan.ReplacedSkeleton) ? Plan.bReplacedSkeletonFromFolder : Plan.bNewSkeletonFromFolder) ? TEXT("; it is the model folder's, set the skeleton (Advanced) if the animations use another") : TEXT(""));
			}
		}
		Report += FString::Printf(TEXT("    family (Export Json): hub %s, member %s\n"), *Hub, *Member);
	}
	for (const TSharedPtr<FJsonObject>& Row : CharacterRowsJson(Swap, Plan))
	{
		Report += FString::Printf(TEXT("    animation sets (Export Json) of %s: battle and field from %s\n"), *ListText(StringsOf(Row->TryGetField(TEXT("characters")))),
			*ListText(StringsOf(Row->TryGetField(TEXT("battle")))));
	}
	return bOk;
}

// Shared CharaSpec Lists that would load each other in a loop once Planned (row -> its new list) is written, as text.
TArray<FString> SharedLoops(const FCharaSpecTable& Table, const TMap<FString, TArray<FString>>& Planned)
{
	TMap<FString, TArray<FString>> Lists = Planned;
	const auto SharedOf = [&](const FString& Row) -> TArray<FString>
	{
		if (const TArray<FString>* Known = Lists.Find(Row))
		{
			return *Known;
		}
		TArray<FString> Read = Table.Has(Row) ? NamesInText(Table.Field(Row, TEXT("SharedCharaSpecList_Array"))) : TArray<FString>();
		Lists.Add(Row, Read);
		return Read;
	};
	TArray<FString> Loops;
	for (const TPair<FString, TArray<FString>>& Start : Planned)
	{
		TArray<TArray<FString>> Stack{{Start.Key}};
		TSet<FString> Seen;
		while (Stack.Num() > 0)
		{
			const TArray<FString> Path = Stack.Pop();
			for (const FString& Next : SharedOf(Path.Last()))
			{
				if (Next.Equals(Start.Key, ESearchCase::IgnoreCase))
				{
					Loops.AddUnique(FString::Join(Path, TEXT(" -> ")) + TEXT(" -> ") + Next);
				}
				else if (!Seen.Contains(Next) && Path.Num() < 16)
				{
					Seen.Add(Next);
					TArray<FString> Longer = Path;
					Longer.Add(Next);
					Stack.Add(Longer);
				}
			}
		}
	}
	return Loops;
}

// Every CharaSpec pack of this project against its row: the model of the blueprint it spawns (wrong ones are what Fix Pack
// Models changes), and the voice, effects, sounds and AI it loads.
struct FPackCheck
{
	FString Row;
	FString Model;    // the row's model now
	FString Spawns;   // the one blueprint the pack spawns (empty: none or several)
	TArray<FString> Differences;
};

TArray<FPackCheck> CheckProjectPacks(const FCharaSpecTable& Table)
{
	TArray<FPackCheck> Out;
	if (!Table.bAvailable)
	{
		return Out;
	}
	TArray<FAssetData> Assets;
	AssetRegistry().GetAssetsByPath(FName(TEXT("/Game/DataAsset/Game/CharaSpec")), Assets, false);
	Assets.Sort([](const FAssetData& A, const FAssetData& B) { return A.PackageName.LexicalLess(B.PackageName); });
	for (const FAssetData& Asset : Assets)
	{
		FString Row = Asset.AssetName.ToString();
		if (!Row.RemoveFromStart(TEXT("CharaSpec_")) || !Table.Has(Row))
		{
			continue;
		}
		const FPackContents Pack = ReadPack(Row);
		FPackCheck Check;
		Check.Row = Row;
		Check.Model = Table.Field(Row, TEXT("ContentsModel"));
		if (Pack.Blueprints.Num() == 1)
		{
			Check.Spawns = Pack.Blueprints[0];
		}
		const auto Compare = [&](const TCHAR* Field, const TArray<FString>& Loads, bool bOnlyWhenLoaded)
		{
			if (bOnlyWhenLoaded && Loads.Num() == 0)
			{
				return;
			}
			const TArray<FString> Lists = NamesInText(Table.Field(Row, Field));
			if (!SameNames(Lists, Loads))
			{
				Check.Differences.Add(FString::Printf(TEXT("%s lists %s, the pack loads %s"), Field, *ListText(Lists), *ListText(Loads)));
			}
		};
		Compare(TEXT("ContentSoundVoice_Array"), Pack.Voices, true);
		Compare(TEXT("ContentsEffect_Array"), Pack.Effects, false);
		Compare(TEXT("ContentsSoundSE_Array"), Pack.SoundSE, false);
		Compare(TEXT("ContentsSoundAutoSE_Array"), Pack.SoundAutoSE, false);
		Compare(TEXT("End2AIList_Array"), Pack.AIBlueprints, true);
		if (!Check.Spawns.IsEmpty() && !Check.Spawns.Equals(Check.Model, ESearchCase::IgnoreCase))
		{
			Check.Differences.Insert(FString::Printf(TEXT("ERROR: it spawns %s, but the row's model is %s"), *Check.Spawns, *Check.Model), 0);
		}
		if (Check.Differences.Num() > 0)
		{
			Out.Add(MoveTemp(Check));
		}
	}
	return Out;
}
