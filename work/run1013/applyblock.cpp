bool UEndSkeletonCompatDataObject::ApplyRowsToCharaSpec(FString& OutReport)
{
	OutReport.Reset();
	const FCharaSpecTable Table(CharaSpecTable);
	if (!Table.bAvailable)
	{
		OutReport += TEXT("The Rebirth data object tools (Rebirth Cooked Asset Preview plugin) are not loaded, so the CharaSpec table cannot be edited here.\n");
		return false;
	}
	if (Table.Rows.Num() == 0)
	{
		OutReport += Table.Package + TEXT(" has no rows. Set CharaSpec Table (Advanced) to your project's editable CharaSpec.\n");
		return false;
	}
	bool bOk = true;
	bool bChanged = false;
	TSet<FString> Handled; // rows a swap writes (Fix Pack Models leaves them to it)
	const auto Set = [&](const FString& Row, const TCHAR* Field, const FString& Value, const FString& Why) {
		FString Message;
		if (Table.SetField(Row, Field, Value, Message))
		{
			OutReport += FString::Printf(TEXT("%s: %s = %s (%s)\n"), *Row, Field, *Value, *Why);
			bChanged = true;
		}
		else
		{
			OutReport += FString::Printf(TEXT("%s: ERROR: %s not set: %s\n"), *Row, Field, *Message);
			bOk = false;
		}
	};
	// A row's changes from a swap; a Shared CharaSpec List that would make specs load each other in a loop is left out.
	const auto Write = [&](const FString& Row, const TArray<FFieldChange>& Changes, const FString& Why) {
		for (const FFieldChange& Change : Changes)
		{
			if (FCString::Strcmp(Change.Field, TEXT("SharedCharaSpecList_Array")) == 0)
			{
				TMap<FString, TArray<FString>> One;
				One.Add(Row, NamesInText(Change.Value));
				const TArray<FString> Loops = SharedLoops(Table, One);
				if (Loops.Num() > 0)
				{
					OutReport += FString::Printf(TEXT("%s: ERROR: SharedCharaSpecList_Array left as it is: %s would load each other in a loop (%s)\n"), *Row,
						*FieldShown(Change.Field, Change.Value), *Loops[0]);
					bOk = false;
					continue;
				}
			}
			Set(Row, Change.Field, Change.Value, Why + TEXT(", was ") + FieldShown(Change.Field, Change.Current));
		}
	};

	// 1. The swaps' packs (Apply To Packs): the blueprint they spawn, a character's voice, a weapon's effects.
	TArray<UPackage*> DirtyPacks;
	TArray<FCharacterSwapPlan> CharacterPlans;
	for (const FEndCharacterSwap& Swap : CharacterSwaps)
	{
		CharacterPlans.Add(Swap.bEnabled ? PlanCharacterSwap(Swap, Table, true, bApplyToPacks) : FCharacterSwapPlan());
		for (const FCharacterRowPlan& Row : CharacterPlans.Last().Rows)
		{
			if (Row.Problem.IsEmpty() && Row.Pack.bInProject && Row.Edit.HasWork())
			{
				bOk &= ApplyPackEdit(Row.Row, Row.Edit, DirtyPacks, OutReport);
			}
		}
	}
	TArray<FWeaponSwapPlan> WeaponPlans;
	for (const FEndWeaponSwap& Swap : WeaponSwaps)
	{
		WeaponPlans.Add(Swap.bEnabled ? PlanWeaponSwap(Swap, Table, true, bApplyToPacks) : FWeaponSwapPlan());
		for (const FWeaponRowPlan& Row : WeaponPlans.Last().Rows)
		{
			if (!LeftOut(Row) && Row.Pack.bInProject && Row.Edit.HasWork())
			{
				bOk &= ApplyPackEdit(Row.Row, Row.Edit, DirtyPacks, OutReport);
			}
		}
	}
	if (DirtyPacks.Num() > 0)
	{
		if (FEditorFileUtils::PromptForCheckoutAndSave(DirtyPacks, false, false) == FEditorFileUtils::PR_Success)
		{
			OutReport += FString::Printf(TEXT("Saved %d pack(s). Cook them with your mod.\n\n"), DirtyPacks.Num());
		}
		else
		{
			OutReport += TEXT("ERROR: the changed packs were not all saved (save them by hand)\n\n");
			bOk = false;
		}
	}

	// 2. Animation set rows: field actions and references to rows that are not in the table.
	for (int32 Index = 0; Index < AnimationSets.Num(); ++Index)
	{
		const FEndAnimSetRow& Row = AnimationSets[Index];
		if (!Row.bEnabled)
		{
			continue;
		}
		const FString Folder = Row.FieldActions.TrimStartAndEnd();
		for (const FString& Character : CleanList(Row.Characters, false))
		{
			const FString Name = CharaSpecRowName(Character);
			if (Name.IsEmpty() || !Table.Has(Name))
			{
				OutReport += FString::Printf(TEXT("Row %d: %s is not a row of %s\n"), Index, *Character, *Table.Package);
				bOk = false;
				continue;
			}
			if (!Folder.IsEmpty())
			{
				const FString Current = Table.Field(Name, TEXT("AnimationSetParentFolder"));
				if (Current.Equals(Folder, ESearchCase::IgnoreCase))
				{
					OutReport += FString::Printf(TEXT("%s: AnimationSetParentFolder is already %s\n"), *Name, *Folder);
				}
				else
				{
					Set(Name, TEXT("AnimationSetParentFolder"), Folder, TEXT("field actions, was ") + (Current.IsEmpty() ? FString(TEXT("empty")) : Current));
				}
			}
			if (bFixMissingRowReferences)
			{
				for (const TCHAR* Field : {TEXT("NoBattleCharaSpec"), TEXT("ReserveCharaSpec")})
				{
					const FString Current = Table.Field(Name, Field);
					if (!Current.IsEmpty() && !Current.Equals(TEXT("None"), ESearchCase::IgnoreCase) && !Table.Has(Current))
					{
						Set(Name, Field, Name, Current + TEXT(" is not in the table"));
					}
				}
			}
		}
	}

	// 3. Character swaps: each replaced row describes what its pack spawns and loads. A row whose pack is the game's own,
	// or still spawns someone else, is left alone: describing a character the pack does not spawn keeps the game loading.
	for (int32 Index = 0; Index < CharacterSwaps.Num(); ++Index)
	{
		if (!CharacterSwaps[Index].bEnabled)
		{
			continue;
		}
		const FCharacterSwapPlan& Plan = CharacterPlans[Index];
		if (!Plan.Error.IsEmpty())
		{
			OutReport += FString::Printf(TEXT("Character swap %d: ERROR: %s\n"), Index, *Plan.Error);
			bOk = false;
			continue;
		}
		for (const FString& Item : Plan.Unknown)
		{
			OutReport += FString::Printf(TEXT("Character swap %d: %s names no row of %s\n"), Index, *Item, *Table.Package);
		}
		if (Plan.Rows.Num() == 0)
		{
			OutReport += FString::Printf(TEXT("Character swap %d: ERROR: no rows to replace\n"), Index);
			bOk = false;
		}
		if (!Plan.NewSpecNote.IsEmpty())
		{
			OutReport += FString::Printf(TEXT("Character swap %d: note: %s\n"), Index, *Plan.NewSpecNote);
		}
		for (const FCharacterRowPlan& Row : Plan.Rows)
		{
			if (LeftOut(Row))
			{
				OutReport += FString::Printf(TEXT("%s: left out (its pack is the game's own, so it stays the old character)\n"), *Row.Row);
				continue;
			}
			for (const FString& Note : Row.Notes)
			{
				OutReport += FString::Printf(TEXT("%s: note: %s\n"), *Row.Row, *Note);
			}
			if (!Row.Problem.IsEmpty())
			{
				OutReport += FString::Printf(TEXT("%s: NOT changed: %s\n"), *Row.Row, *Row.Problem);
				bOk = false;
				continue;
			}
			Handled.Add(Row.Row);
			if (Row.Changes.Num() == 0)
			{
				OutReport += FString::Printf(TEXT("%s: already describes %s\n"), *Row.Row, *ListText(Row.After.Blueprints));
				continue;
			}
			Write(Row.Row, Row.Changes, TEXT("character swap to ") + Plan.NewCharacter);
		}
	}

	// 4. Weapon swaps: each replaced weapon's row describes the weapon its pack spawns. A row whose pack still spawns the old
	// weapon (or is the game's own) is left alone: describing a weapon the pack does not spawn is the same mismatch.
	for (int32 Index = 0; Index < WeaponSwaps.Num(); ++Index)
	{
		if (!WeaponSwaps[Index].bEnabled)
		{
			continue;
		}
		const FWeaponSwapPlan& Plan = WeaponPlans[Index];
		if (!Plan.Error.IsEmpty())
		{
			OutReport += FString::Printf(TEXT("Weapon swap %d: ERROR: %s\n"), Index, *Plan.Error);
			bOk = false;
			continue;
		}
		for (const FString& Item : Plan.Unknown)
		{
			OutReport += FString::Printf(TEXT("Weapon swap %d: %s names no row of %s\n"), Index, *Item, *Table.Package);
		}
		if (Plan.Rows.Num() == 0)
		{
			OutReport += FString::Printf(TEXT("Weapon swap %d: ERROR: no weapon rows to replace\n"), Index);
			bOk = false;
		}
		for (const FWeaponRowPlan& Row : Plan.Rows)
		{
			if (LeftOut(Row))
			{
				OutReport += FString::Printf(TEXT("%s: left out (its pack is the game's own, so it stays the old weapon)\n"), *Row.Row);
				continue;
			}
			for (const FString& Note : Row.Notes)
			{
				OutReport += FString::Printf(TEXT("%s: note: %s\n"), *Row.Row, *Note);
			}
			const FString Problem = WeaponRowProblem(Row, Plan.NewWeapon);
			if (!Problem.IsEmpty())
			{
				OutReport += FString::Printf(TEXT("%s: NOT changed: %s\n"), *Row.Row, *Problem);
				bOk = false;
				continue;
			}
			Handled.Add(Row.Row);
			if (Row.Changes.Num() == 0)
			{
				OutReport += FString::Printf(TEXT("%s: already describes %s\n"), *Row.Row, *Plan.NewWeapon);
				continue;
			}
			Write(Row.Row, Row.Changes, TEXT("weapon swap to ") + Plan.NewWeapon);
		}
	}

	// 5. Fix Pack Models: every other pack of this project gets a row whose model is the blueprint it spawns.
	if (bFixPackModels)
	{
		for (const FPackCheck& Check : CheckProjectPacks(Table))
		{
			if (Check.Spawns.IsEmpty() || Check.Spawns.Equals(Check.Model, ESearchCase::IgnoreCase) || Handled.Contains(Check.Row))
			{
				continue;
			}
			if (!Table.Has(Check.Spawns))
			{
				OutReport += FString::Printf(TEXT("%s: note: its pack spawns %s, which is not a row of the table, so its model is left as %s\n"), *Check.Row, *Check.Spawns, *Check.Model);
				continue;
			}
			Set(Check.Row, TEXT("ContentsModel"), Check.Spawns, TEXT("Fix Pack Models: the blueprint its pack spawns, was ") + Check.Model);
		}
	}

	if (bChanged)
	{
		FString Message;
		if (Table.Save(Message))
		{
			OutReport += TEXT("\nSaved ") + Table.Package + TEXT(". Cook it with your mod (it replaces the game's CharaSpec).\n");
		}
		else
		{
			OutReport += TEXT("\nERROR: ") + Table.Package + TEXT(" not saved: ") + Message + TEXT("\n");
			bOk = false;
		}
	}
	else if (bOk && DirtyPacks.Num() == 0)
	{
		OutReport += TEXT("\nNothing to change.\n");
	}
	if (CharacterSwaps.ContainsByPredicate([](const FEndCharacterSwap& Swap) { return Swap.bEnabled; }) ||
		WeaponSwaps.ContainsByPredicate([](const FEndWeaponSwap& Swap) { return Swap.bEnabled && Swap.Sockets.Num() > 0; }))
	{
		OutReport += TEXT("Press Export Json too: the swaps' families, moves and socket stand-ins reach the game through it.\n");
	}
	return bOk;
}

