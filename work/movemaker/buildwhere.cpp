bool UEndSkeletonCompatDataObject::BuildMoveAnimations(FString& OutReport)
{
	return BuildMovesWhere([](int32, const FEndAnimSetMove&) { return true; }, OutReport);
}

bool UEndSkeletonCompatDataObject::BuildOneMove(int32 RowIndex, const FString& Name, const FString& Set, FString& OutReport)
{
	if (!AnimationSets.IsValidIndex(RowIndex))
	{
		OutReport = FString::Printf(TEXT("ERROR: this data object has no animation set row %d\n"), RowIndex);
		return false;
	}
	const FString WantName = Name.TrimStartAndEnd();
	const FString WantSet = Set.TrimStartAndEnd();
	return BuildMovesWhere([&](int32 Row, const FEndAnimSetMove& Move)
	{
		return Row == RowIndex && Move.Name.TrimStartAndEnd().Equals(WantName, ESearchCase::IgnoreCase) &&
			   Move.Set.TrimStartAndEnd().Equals(WantSet, ESearchCase::IgnoreCase);
	}, OutReport);
}

bool UEndSkeletonCompatDataObject::BuildMovesWhere(TFunctionRef<bool(int32, const FEndAnimSetMove&)> Pick, FString& OutReport)
{
	OutReport.Reset();
	bool bOk = true;
	int32 Asked = 0;
	int32 Built = 0;
	TArray<UPackage*> ToSave;
	TMap<FString, TArray<UObject*>> ByFolder;
	for (int32 RowIndex = 0; RowIndex < AnimationSets.Num(); ++RowIndex)
	{
		const FEndAnimSetRow& Row = AnimationSets[RowIndex];
		if (!Row.bEnabled)
		{
			continue;
		}
		int32 RowMoves = 0;
		for (const FEndAnimSetMove& Move : Row.Moves)
		{
			RowMoves += Move.bBuild && Pick(RowIndex, Move) ? 1 : 0;
		}
		if (RowMoves == 0)
		{
			continue;
		}
		// A folder the project never cooks would build animations that are never packaged.
		const FString NeverCook = NeverCookDirectoryOf(BuildFolderOf(Row));
		if (!NeverCook.IsEmpty())
		{
			Asked += RowMoves;
			OutReport += FString::Printf(TEXT("ERROR: %d move(s) not built: Build Folder %s is in %s, which Project Settings > Packaging > Directories To Never Cook lists, ")
										 TEXT("so they would never be packaged. Set Build Folder outside it (for example /Game/RebirthSkelCompat/Built/<Character>).\n"),
				RowMoves, *BuildFolderOf(Row), *NeverCook);
			bOk = false;
			continue;
		}
		// The skeleton the moves are built on: the character's own (an animation of another skeleton is put on it).
		USkeleton* CharacterSkeleton = Row.CharacterSkeleton.IsNull() ? nullptr : Row.CharacterSkeleton.LoadSynchronous();
		if (!Row.CharacterSkeleton.IsNull() && !CharacterSkeleton)
		{
			OutReport += FString::Printf(TEXT("ERROR: %d move(s) not built: Character Skeleton %s does not load\n"), RowMoves, *SoftPath(Row.CharacterSkeleton));
			Asked += RowMoves;
			bOk = false;
			continue;
		}
		for (const FEndAnimSetMove& Move : Row.Moves)
		{
			if (!Move.bBuild || !Pick(RowIndex, Move))
			{
				continue;
			}
			++Asked;
			const FString Name = Move.Name.TrimStartAndEnd();
			const FString Label = (Move.Set.TrimStartAndEnd().IsEmpty() ? FString() : Move.Set.TrimStartAndEnd() + TEXT("/")) + Name;
			const FString SourcePath = Move.Animation.TrimStartAndEnd();
			UAnimSequence* Source = SourcePath.IsEmpty() ? nullptr : Cast<UAnimSequence>(FSoftObjectPath(NormalizedObjectPath(SourcePath)).TryLoad());
			if (Name.IsEmpty() || !Source)
			{
				OutReport += FString::Printf(TEXT("%s: ERROR: %s\n"), *Label,
					Name.IsEmpty() ? TEXT("the move has no Name") : *(TEXT("Animation ") + SourcePath + TEXT(" is not an Anim Sequence that loads in this editor")));
				bOk = false;
				continue;
			}
			USkeleton* Target = CharacterSkeleton ? CharacterSkeleton : Source->GetSkeleton();
			FString NotifyPath;
			UAnimSequenceBase* From = FindNotifySource(Row, Move, NotifyPath);
			const bool bHitsNameDamage = Move.Hits.ContainsByPredicate([](const FEndMoveHit& Hit) { return !Hit.DamageSourceID.TrimStartAndEnd().IsEmpty(); });
			if (!From && !bHitsNameDamage)
			{
				OutReport += FString::Printf(TEXT("%s: ERROR: no animation to take the gameplay notifies from (%s is not in this project). Set Notifies From to a move of the character that hits the way this one should, or give each hit a Damage Source ID\n"),
					*Label, *NotifyPath);
				bOk = false;
				continue;
			}
			const FString Package = BuiltPackageOf(Row, Move);
			if (!FPackageName::IsValidLongPackageName(Package))
			{
				OutReport += FString::Printf(TEXT("%s: ERROR: %s is not in a content folder (Build Folder must start with /Game/ or a plugin's folder)\n"), *Label, *Package);
				bOk = false;
				continue;
			}
			// An earlier build is made anew.
			if (UObject* Old = StaticLoadObject(UObject::StaticClass(), nullptr, *(Package + TEXT(".") + Name), nullptr, LOAD_NoWarn | LOAD_Quiet))
			{
				if (IsCookedAsset(Old))
				{
					OutReport += FString::Printf(TEXT("%s: ERROR: %s is a cooked game asset; choose another Build Folder\n"), *Label, *Package);
					bOk = false;
					continue;
				}
				if (ObjectTools::ForceDeleteObjects(TArray<UObject*>{Old}, false) == 0)
				{
					OutReport += FString::Printf(TEXT("%s: ERROR: the earlier build %s could not be replaced (close it, then build again)\n"), *Label, *Package);
					bOk = false;
					continue;
				}
			}
			// Made new, not duplicated (duplicating an Anim Sequence crashes this engine), and not put in the undo history
			// (undoing it would read it back the same broken way). An animation of another skeleton, or one of the game's
			// (only compressed data in this project), is sampled onto the character's skeleton.
			FString Error;
			FBakeResult Bake;
			const bool bSample = Target != Source->GetSkeleton() || IsCookedAsset(Source) || Source->GetRawAnimationData().Num() == 0;
			UAnimSequence* Sequence = bSample ? MakeAnimationBySampling(Source, Target, Package, Name, Move.Retarget, Move.bKeepSourceEffects, Bake, Error)
											  : MakeAnimationFrom(Source, Package, Name, Error);
			if (!Sequence)
			{
				OutReport += FString::Printf(TEXT("%s: ERROR: %s could not be made: %s\n"), *Label, *Package, *Error);
				bOk = false;
				continue;
			}
			FString Notes;
			if (CleanList(Move.ThenPlay, false).Num() > 0)
			{
				Notes += TEXT("; Then Play is not built (only Animation)");
			}
			const FBuildResult Result = BuildNotifies(Sequence, From, Move, Row.ShotEffects, Notes);
			CopyPlaySettings(From ? From : static_cast<UAnimSequenceBase*>(Source), Sequence);
			Sequence->RefreshCacheData();
			Sequence->PostEditChange();
			// Compressed now, so the report can say which codec it got: the game decompresses with GameBoneCodec only.
			Sequence->RequestSyncAnimRecompression(false);
			const UAnimBoneCompressionCodec* Codec = Sequence->CompressedData.BoneCompressionCodec;
			const FString CodecName = Codec ? Codec->GetCodecDDCHandle() : FString(TEXT("no codec"));
			if (!CodecName.Equals(GameBoneCodec, ESearchCase::IgnoreCase))
			{
				Notes += FString::Printf(TEXT("; ERROR: compressed with %s, but the game reads it with %s (it would not play right)"), *CodecName, GameBoneCodec);
				bOk = false;
			}
			Sequence->MarkPackageDirty();
			ToSave.AddUnique(Sequence->GetOutermost());
			ByFolder.FindOrAdd(BuildFolderOf(Row)).Add(Sequence);
			++Built;
			OutReport += FString::Printf(TEXT("%s: built %s from %s (%.2f s)"), *Label, *Package, *Source->GetName(), Sequence->SequenceLength);
			if (bSample)
			{
				OutReport += Bake.bRetargeted
					? FString::Printf(TEXT(", put on %s from %s (%s; %d bone(s), %d the character lacks left out, %d curve(s))"), *Target->GetName(), *Source->GetSkeleton()->GetName(),
						  Move.Retarget == EEndMoveRetarget::Proportions ? TEXT("the character's build kept") : TEXT("the animation's bone lengths"), Bake.Bones, Bake.Dropped, Bake.Curves)
					: FString::Printf(TEXT(", sampled from the game animation (%d bone(s), %d curve(s))"), Bake.Bones, Bake.Curves);
				if (Bake.SourceEffects > 0)
				{
					OutReport += FString::Printf(TEXT(", %d of its own sounds and effects kept"), Bake.SourceEffects);
				}
				if (Bake.CurvesDropped > 0)
				{
					OutReport += FString::Printf(TEXT(", %d curve(s) the character's skeleton has no name for left out"), Bake.CurvesDropped);
				}
			}
			if (From)
			{
				OutReport += FString::Printf(TEXT(", %d gameplay notifies from %s (%.2f s)"), Result.Copied, *From->GetName(), From->SequenceLength);
			}
			if (Result.OldHit >= 0.f)
			{
				OutReport += FString::Printf(TEXT(", first hit %.2f s -> %.2f s (%d hit(s))"), Result.OldHit, Result.NewHit, Result.Hits);
			}
			else if (Result.HitsMade > 0)
			{
				OutReport += FString::Printf(TEXT(", %d new hit(s) with their Damage Source IDs"), Result.HitsMade);
			}
			else if (From)
			{
				OutReport += TEXT(", the original has no hit");
			}
			if (Result.HitsRepeated > 0)
			{
				OutReport += FString::Printf(TEXT(", %d more hit(s) made from its last one"), Result.HitsRepeated);
			}
			if (Result.HitsLeftOut > 0)
			{
				OutReport += FString::Printf(TEXT(", its last %d hit(s) left out (the move has fewer)"), Result.HitsLeftOut);
			}
			if (Result.Effects > 0)
			{
				OutReport += FString::Printf(TEXT(", %d hit effect(s) and sound(s)"), Result.Effects);
			}
			if (Result.Shots > 0)
			{
				OutReport += FString::Printf(TEXT(", %d shot(s) with muzzle flash and gunshot"), Result.Shots);
			}
			if (Result.Left > 0)
			{
				OutReport += FString::Printf(TEXT("; left out %d of the original's own sounds and effects (%s)"), Result.Left, *FString::Join(Result.LeftClasses, TEXT(", ")));
			}
			OutReport += Notes + TEXT("\n");
		}
	}
	if (Asked == 0)
	{
		OutReport += TEXT("No move with Build on to build. Turn on Build on the moves to make (Animation: the animation to make each from).\n");
		return false;
	}
	if (BuildChunk > 0)
	{
		for (const TPair<FString, TArray<UObject*>>& Folder : ByFolder)
		{
			LabelForChunk(Folder.Key, BuildChunk, Folder.Value, ToSave, OutReport);
		}
	}
	if (ToSave.Num() > 0)
	{
		// The data object too, when its moves changed (the Move Maker's Build), so the build and its settings stay together.
		if (GetOutermost()->IsDirty())
		{
			ToSave.AddUnique(GetOutermost());
		}
		TArray<UPackage*> Failed;
		FEditorFileUtils::PromptForCheckoutAndSave(ToSave, false, false, &Failed);
		OutReport += FString::Printf(TEXT("\n%d of %d move(s) built and saved%s. Package the project: they go in pakchunk%d. Export Json points the moves at them.\n"),
			Built, Asked, Failed.Num() > 0 ? *FString::Printf(TEXT(" (%d package(s) NOT saved)"), Failed.Num()) : TEXT(""), BuildChunk);
		bOk &= Failed.Num() == 0;
	}
	return bOk && Built == Asked;
}

