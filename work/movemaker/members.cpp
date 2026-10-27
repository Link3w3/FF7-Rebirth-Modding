// ------------------------------------------------------------------------------------------------
// The Move Maker's view of this data object (editor 1.8)
// ------------------------------------------------------------------------------------------------
void UEndSkeletonCompatDataObject::OpenMoveMaker()
{
	RebirthSkelCompatEditor::OpenMoveMakerTab(this);
}

TArray<FString> UEndSkeletonCompatDataObject::MoveMakerRowLabels() const
{
	TArray<FString> Labels;
	for (int32 Index = 0; Index < AnimationSets.Num(); ++Index)
	{
		const TArray<FString> Characters = CleanList(AnimationSets[Index].Characters, false);
		Labels.Add(FString::Printf(TEXT("%d: %s"), Index, Characters.Num() > 0 ? *ListText(Characters) : TEXT("(no character yet)")));
	}
	return Labels;
}

TArray<FString> UEndSkeletonCompatDataObject::MoveMakerSlots(int32 RowIndex, EEndMoveSlotKind Kind) const
{
	TArray<FString> Out;
	if (!AnimationSets.IsValidIndex(RowIndex))
	{
		return Out;
	}
	const FEndAnimSetRow& Row = AnimationSets[RowIndex];
	TMap<FString, float> Lengths;
	const auto Take = [&Lengths](UObject* Set)
	{
		FSetContents Contents;
		if (!Set || !ReadEndAnimSet(Set, Contents))
		{
			return;
		}
		for (const SkelCompat::MatchAnim& Anim : Contents.Anims)
		{
			const FString Name = FromWide(Anim.Name);
			if (!Lengths.Contains(Name))
			{
				Lengths.Add(Name, Anim.Length);
			}
		}
	};
	// The battle sets the character plays: the row's battle sources, the slot owner's (last) first, then the packs' own.
	static const TCHAR* const SetNames[] = {TEXT("Battle00"), TEXT("Battle01"), TEXT("Battle02"), TEXT("Battle00_Comp"), TEXT("Battle01_Comp")};
	for (int32 K = Row.Battle.Num() - 1; K >= 0; --K)
	{
		SkelCompat::SetSource Parsed;
		if (!SkelCompat::ParseSetSource(Wide(Row.Battle[K].Path), Parsed))
		{
			continue;
		}
		if (Parsed.Folder)
		{
			for (const TCHAR* SetName : SetNames)
			{
				const FString Path = FromWide(Parsed.Path) + TEXT("/") + SetName + TEXT(".") + SetName;
				if (InProject(Path))
				{
					Take(LoadObject<UObject>(nullptr, *Path));
				}
			}
		}
		else if (InProject(FromWide(Parsed.Path)))
		{
			Take(LoadObject<UObject>(nullptr, *FromWide(Parsed.Path)));
		}
	}
	for (const FString& Character : CleanList(Row.Characters, false))
	{
		const FString Pack = FromWide(SkelCompat::CharacterPackPath(Wide(Character)));
		for (const TCHAR* SetName : SetNames)
		{
			Take(PackOwnSet(Pack, SetName));
		}
	}
	// The row's own moves (names the sets do not have included).
	for (const FEndAnimSetMove& Move : Row.Moves)
	{
		const FString Name = Move.Name.TrimStartAndEnd();
		if (!Name.IsEmpty() && !Lengths.Contains(Name))
		{
			Lengths.Add(Name, 0.f);
		}
	}
	TArray<FString> Names;
	Lengths.GetKeys(Names);
	Names.Sort();
	for (const FString& Name : Names)
	{
		if (!SlotIsKind(Name, Kind))
		{
			continue;
		}
		const float Length = Lengths[Name];
		Out.Add(Length > 0.f ? FString::Printf(TEXT("%s (%.2f s)"), *Name, Length) : Name);
	}
	return Out;
}

int32 UEndSkeletonCompatDataObject::FindMove(int32 RowIndex, const FString& Name, const FString& Set) const
{
	if (!AnimationSets.IsValidIndex(RowIndex))
	{
		return INDEX_NONE;
	}
	const TArray<FEndAnimSetMove>& Moves = AnimationSets[RowIndex].Moves;
	for (int32 Index = 0; Index < Moves.Num(); ++Index)
	{
		if (Moves[Index].Name.TrimStartAndEnd().Equals(Name.TrimStartAndEnd(), ESearchCase::IgnoreCase) &&
			Moves[Index].Set.TrimStartAndEnd().Equals(Set.TrimStartAndEnd(), ESearchCase::IgnoreCase))
		{
			return Index;
		}
	}
	return INDEX_NONE;
}

const FEndAnimSetMove* UEndSkeletonCompatDataObject::GetMove(int32 RowIndex, int32 MoveIndex) const
{
	return AnimationSets.IsValidIndex(RowIndex) && AnimationSets[RowIndex].Moves.IsValidIndex(MoveIndex) ? &AnimationSets[RowIndex].Moves[MoveIndex] : nullptr;
}

void UEndSkeletonCompatDataObject::SetMove(int32 RowIndex, const FEndAnimSetMove& Move)
{
	if (!AnimationSets.IsValidIndex(RowIndex) || Move.Name.TrimStartAndEnd().IsEmpty())
	{
		return;
	}
	Modify();
	const int32 Index = FindMove(RowIndex, Move.Name, Move.Set);
	if (Index == INDEX_NONE)
	{
		AnimationSets[RowIndex].Moves.Add(Move);
	}
	else
	{
		AnimationSets[RowIndex].Moves[Index] = Move;
	}
	PostEditChange();
	MarkPackageDirty();
}

FString UEndSkeletonCompatDataObject::BuiltMoveObjectPath(int32 RowIndex, const FEndAnimSetMove& Move) const
{
	return AnimationSets.IsValidIndex(RowIndex) && !Move.Name.TrimStartAndEnd().IsEmpty() ? BuiltObjectPathOf(AnimationSets[RowIndex], Move) : FString();
}

FString UEndSkeletonCompatDataObject::MoveNotifySourcePath(int32 RowIndex, const FEndAnimSetMove& Move, FString& OutLookedFor) const
{
	OutLookedFor.Reset();
	if (!AnimationSets.IsValidIndex(RowIndex) || (Move.Name.TrimStartAndEnd().IsEmpty() && Move.NotifiesFrom.TrimStartAndEnd().IsEmpty()))
	{
		return FString();
	}
	const UAnimSequenceBase* From = FindNotifySource(AnimationSets[RowIndex], Move, OutLookedFor);
	return From ? From->GetPathName() : FString();
}

USkeleton* UEndSkeletonCompatDataObject::CharacterSkeletonOf(int32 RowIndex) const
{
	return AnimationSets.IsValidIndex(RowIndex) && !AnimationSets[RowIndex].CharacterSkeleton.IsNull() ? AnimationSets[RowIndex].CharacterSkeleton.LoadSynchronous() : nullptr;
}

