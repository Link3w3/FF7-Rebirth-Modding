// A Niagara effect (AnimNotifyState_EndTimedNiagaraEffect) at Socket, attached as AttachType says (Weapon1..Weapon8 or
// Character). Only the settings the game's own effect notifies set are set; everything else keeps the game's defaults.
bool AddEffectNotify(UAnimSequenceBase* Sequence, const FString& Effect, FName Socket, const FString& AttachType, float Time, float Duration, int32 Track, FString& Notes)
{
	UClass* Class = FindObject<UClass>(ANY_PACKAGE, TEXT("AnimNotifyState_EndTimedNiagaraEffect"));
	if (!Class || !Class->IsChildOf(UAnimNotifyState::StaticClass()))
	{
		Notes += TEXT("; no effect: AnimNotifyState_EndTimedNiagaraEffect (EndGame) is not loaded");
		return false;
	}
	UAnimNotifyState* State = NewObject<UAnimNotifyState>(Sequence, Class, NAME_None, RF_Transactional);
	const FString Params = FString::Printf(TEXT("(m_NiagaraParameterInfo=(m_Template=\"%s\"),m_SocketName=\"%s\")"), *NormalizedObjectPath(Effect), *Socket.ToString());
	if (!SetPropertyText(State, TEXT("m_NiagaraCreateParams"), Params, Notes) || !SetPropertyText(State, TEXT("m_AttachType"), AttachType, Notes))
	{
		return false;
	}
	FAnimNotifyEvent Event;
	Event.NotifyStateClass = State;
	Event.NotifyName = FName(*State->GetNotifyName());
	PlaceNotify(Sequence, Event, Time, FMath::Max(Duration, 0.01f), Track);
	Sequence->Notifies.Add(Event);
	return true;
}

// A sound of a game sound bank: a weapon sound (EndAnimNotifyPlayWeaponSound, of weapon N) or a character sound
// (EndAnimNotifyPlayCharacterSound).
bool AddSoundNotify(UAnimSequenceBase* Sequence, const FString& Bank, FName Sound, bool bWeapon, int32 Weapon, float Time, int32 Track, FString& Notes)
{
	const TCHAR* ClassName = bWeapon ? TEXT("EndAnimNotifyPlayWeaponSound") : TEXT("EndAnimNotifyPlayCharacterSound");
	UClass* Class = FindObject<UClass>(ANY_PACKAGE, ClassName);
	if (!Class || !Class->IsChildOf(UAnimNotify::StaticClass()))
	{
		Notes += FString::Printf(TEXT("; no sound: %s (EndGame) is not loaded"), ClassName);
		return false;
	}
	UAnimNotify* Notify = NewObject<UAnimNotify>(Sequence, Class, NAME_None, RF_Transactional);
	bool bSet = SetPropertyText(Notify, TEXT("SoundRef"), TEXT("\"") + NormalizedObjectPath(Bank) + TEXT("\""), Notes) &&
				SetPropertyText(Notify, TEXT("SoundName"), Sound.ToString(), Notes);
	if (bSet && bWeapon && Weapon != 1)
	{
		bSet = SetPropertyText(Notify, TEXT("WeaponSlot"), FString::Printf(TEXT("EWeaponSlot_%d"), Weapon), Notes);
	}
	if (!bSet)
	{
		return false;
	}
	FAnimNotifyEvent Event;
	Event.Notify = Notify;
	Event.NotifyName = FName(*Notify->GetNotifyName());
	PlaceNotify(Sequence, Event, Time, 0.f, Track);
	Sequence->Notifies.Add(Event);
	return true;
}

// Muzzle flash (a Niagara notify state at the weapon's socket) and gunshot (a weapon sound) at one hit.
int32 AddShotEffects(UAnimSequenceBase* Sequence, const FEndShotEffects& Shot, float Time, int32 Track, FString& Notes)
{
	int32 Added = 0;
	const int32 Weapon = FMath::Clamp(Shot.Weapon, 1, 8);
	const FString Muzzle = Shot.MuzzleEffect.TrimStartAndEnd();
	if (!Muzzle.IsEmpty() && AddEffectNotify(Sequence, Muzzle, Shot.MuzzleSocket, FString::Printf(TEXT("Weapon%d"), Weapon), Time, Shot.MuzzleTime, Track, Notes))
	{
		++Added;
	}
	const FString Bank = Shot.SoundBank.TrimStartAndEnd();
	if (!Bank.IsEmpty() && !Shot.Sound.IsNone() && AddSoundNotify(Sequence, Bank, Shot.Sound, true, Weapon, Time, Track, Notes))
	{
		++Added;
	}
	return Added;
}

// A hit's own effect and sound (editor 1.8).
int32 AddHitEffects(UAnimSequenceBase* Sequence, const FEndMoveHit& Hit, float Time, int32 Track, FString& Notes)
{
	int32 Added = 0;
	const int32 Weapon = FMath::Clamp(Hit.Weapon, 1, 8);
	const bool bOnWeapon = Hit.EffectOn == EEndMoveEffectAttach::Weapon;
	const FString Effect = Hit.Effect.TrimStartAndEnd();
	if (!Effect.IsEmpty() &&
		AddEffectNotify(Sequence, Effect, Hit.EffectSocket, bOnWeapon ? FString::Printf(TEXT("Weapon%d"), Weapon) : FString(TEXT("Character")), Time, Hit.EffectTime, Track, Notes))
	{
		++Added;
	}
	const FString Bank = Hit.SoundBank.TrimStartAndEnd();
	if (!Bank.IsEmpty() && !Hit.Sound.IsNone() && AddSoundNotify(Sequence, Bank, Hit.Sound, bOnWeapon, Weapon, Time, Track, Notes))
	{
		++Added;
	}
	return Added;
}

struct FBuildResult
{
	int32 Copied = 0;
	int32 Left = 0;
	TArray<FString> LeftClasses;
	int32 Hits = 0;          // hits the built move has
	float OldHit = -1.f;
	float NewHit = -1.f;
	int32 Shots = 0;
	int32 HitsLeftOut = 0;   // hits of the original after the move's last hit (Hits shorter than the original's)
	int32 HitsRepeated = 0;  // hits of the move after the original's last one, made from it
	int32 HitsMade = 0;      // new damage notifies (a Damage Source ID and nothing to copy the damage from)
	int32 Effects = 0;       // the hits' own effects and sounds
};

// The times of the original's hits: damage notifies less than 0.05 s apart are one hit.
TArray<float> HitGroupTimes(const UAnimSequenceBase* From)
{
	TArray<float> Times;
	if (From)
	{
		for (const FAnimNotifyEvent& Event : From->Notifies)
		{
			if (IsHitNotify(NotifyObject(Event)))
			{
				Times.Add(Event.GetTime());
			}
		}
	}
	Times.Sort();
	TArray<float> Groups;
	for (const float Time : Times)
	{
		if (Groups.Num() == 0 || Time - Groups.Last() >= 0.05f)
		{
			Groups.Add(Time);
		}
	}
	return Groups;
}

// The hit a damage notify of the original belongs to: the last group that starts at or before it.
int32 HitGroupOf(const TArray<float>& Groups, float Time)
{
	int32 Group = 0;
	for (int32 Index = 0; Index < Groups.Num(); ++Index)
	{
		if (Groups[Index] <= Time + 0.0001f)
		{
			Group = Index;
		}
	}
	return Group;
}

// A hit's own damage source on a damage notify (DamageSourceID; a list of them is replaced by this one).
void ApplyHitDamage(UObject* Object, const FEndMoveHit& Hit, FString& Notes)
{
	const FString Id = Hit.DamageSourceID.TrimStartAndEnd();
	if (!Object || Id.IsEmpty())
	{
		return;
	}
	SetPropertyText(Object, TEXT("DamageSourceID"), TEXT("\"") + Id + TEXT("\""), Notes);
	if (FindFProperty<FProperty>(Object->GetClass(), TEXT("DamageSourceIDs")))
	{
		SetPropertyText(Object, TEXT("DamageSourceIDs"), TEXT("()"), Notes);
	}
}

// The gameplay notifies of From (none: the move's own hits only) on Sequence, after the sequence's own: shot effects and
// the hits' own effects on the first new track, the copied notifies on the tracks after it in the original's order.
// With Hits, the original's hits land at their times (more hits repeat its last one, fewer leave its last ones out);
// otherwise its first hit lands at Hit At and the rest in proportion.
FBuildResult BuildNotifies(UAnimSequenceBase* Sequence, const UAnimSequenceBase* From, const FEndAnimSetMove& Move, const FEndShotEffects& Shot, FString& Notes)
{
	FBuildResult Result;
	FBuildTimeMap Map;
	Map.OldLength = From ? From->SequenceLength : Sequence->SequenceLength;
	Map.NewLength = Sequence->SequenceLength;
	const TArray<float> OldGroups = HitGroupTimes(From);
	TArray<const FEndMoveHit*> Hits;
	for (const FEndMoveHit& Hit : Move.Hits)
	{
		Hits.Add(&Hit);
	}
	Hits.StableSort([](const FEndMoveHit& A, const FEndMoveHit& B) { return A.Time < B.Time; });
	TArray<float> NewTimes;
	for (const FEndMoveHit* Hit : Hits)
	{
		NewTimes.Add(FMath::Clamp(Hit->Time, 0.f, Map.NewLength));
	}
	if (OldGroups.Num() > 0)
	{
		Result.OldHit = OldGroups[0];
		if (Hits.Num() > 0)
		{
			for (int32 Index = 0; Index < FMath::Min(OldGroups.Num(), Hits.Num()); ++Index)
			{
				Map.Anchors.Emplace(OldGroups[Index], NewTimes[Index]);
			}
			Result.NewHit = NewTimes[0];
		}
		else
		{
			Result.NewHit = Move.HitAt > 0.f ? FMath::Min(Move.HitAt, Map.NewLength)
											 : (Map.OldLength > KINDA_SMALL_NUMBER ? OldGroups[0] * Map.NewLength / Map.OldLength : 0.f);
			Map.Anchors.Emplace(OldGroups[0], Result.NewHit);
		}
	}
	else if (Move.HitAt > 0.f && Hits.Num() == 0 && From)
	{
		Notes += TEXT("; Hit At not used: the original has no hit");
	}
	int32 ShotTrack = 0;
#if WITH_EDITORONLY_DATA
	ShotTrack = Sequence->AnimNotifyTracks.Num();
#endif
	int32 LastTrack = ShotTrack;
	TArray<float> NewHits;
	const auto Copy = [&](const FAnimNotifyEvent& Original, float Start, float Length, const FEndMoveHit* Hit)
	{
		FAnimNotifyEvent Event = Original;
		if (Original.Notify)
		{
			Event.Notify = DuplicateObject<UAnimNotify>(Original.Notify, Sequence);
		}
		if (Original.NotifyStateClass)
		{
			Event.NotifyStateClass = DuplicateObject<UAnimNotifyState>(Original.NotifyStateClass, Sequence);
		}
		if (Hit)
		{
			ApplyHitDamage(NotifyObject(Event), *Hit, Notes);
		}
		const int32 Track = ShotTrack + 1 + FMath::Clamp(Original.TrackIndex, 0, 30);
		LastTrack = FMath::Max(LastTrack, Track);
		PlaceNotify(Sequence, Event, Start, FMath::Max(Length, 0.f), Track);
		Sequence->Notifies.Add(Event);
		++Result.Copied;
	};
	if (From)
	{
		for (const FAnimNotifyEvent& Original : From->Notifies)
		{
			UObject* Object = NotifyObject(Original);
			if (IsMotionNotify(Object))
			{
				++Result.Left;
				Result.LeftClasses.AddUnique(Object->GetClass()->GetName());
				continue;
			}
			const bool bHit = IsHitNotify(Object);
			const int32 Group = bHit && OldGroups.Num() > 0 ? HitGroupOf(OldGroups, Original.GetTime()) : INDEX_NONE;
			if (bHit && Hits.Num() > 0 && Group >= Hits.Num())
			{
				continue; // a hit after the move's last one
			}
			const FEndMoveHit* Hit = bHit && Hits.Num() > 0 ? Hits[Group] : nullptr;
			const float Start = Hit ? NewTimes[Group] + (Original.GetTime() - OldGroups[Group]) : Map.Map(Original.GetTime());
			float Length = 0.f;
			if (Original.NotifyStateClass)
			{
				// A damage window keeps its length (a shorter one could miss) unless the hit sets one; other windows follow the time map.
				Length = bHit ? (Hit && Hit->Window > 0.f ? Hit->Window : Original.GetDuration()) : Map.Map(Original.GetTime() + Original.GetDuration()) - Start;
			}
			Copy(Original, Start, Length, Hit);
			if (bHit)
			{
				NewHits.Add(Start);
			}
		}
		if (Hits.Num() > 0 && OldGroups.Num() > Hits.Num())
		{
			Result.HitsLeftOut = OldGroups.Num() - Hits.Num();
		}
		// More hits than the original has: its last hit again at each later time.
		if (Hits.Num() > OldGroups.Num() && OldGroups.Num() > 0)
		{
			const int32 Last = OldGroups.Num() - 1;
			for (int32 Index = OldGroups.Num(); Index < Hits.Num(); ++Index)
			{
				for (const FAnimNotifyEvent& Original : From->Notifies)
				{
					UObject* Object = NotifyObject(Original);
					if (!IsHitNotify(Object) || IsMotionNotify(Object) || HitGroupOf(OldGroups, Original.GetTime()) != Last)
					{
						continue;
					}
					const float Start = NewTimes[Index] + (Original.GetTime() - OldGroups[Last]);
					const float Length = Original.NotifyStateClass ? (Hits[Index]->Window > 0.f ? Hits[Index]->Window : Original.GetDuration()) : 0.f;
					Copy(Original, Start, Length, Hits[Index]);
					NewHits.Add(Start);
				}
				++Result.HitsRepeated;
			}
		}
	}
	// Nothing to copy the damage from: new damage notifies for the hits that name a damage source.
	if (OldGroups.Num() == 0 && Hits.Num() > 0)
	{
		UClass* DamageClass = FindObject<UClass>(ANY_PACKAGE, TEXT("EndAnimNotifyBattleDamage"));
		for (int32 Index = 0; Index < Hits.Num(); ++Index)
		{
			if (Hits[Index]->DamageSourceID.TrimStartAndEnd().IsEmpty())
			{
				Notes += FString::Printf(TEXT("; hit %d (%.2f s) deals no damage: there is no move to copy it from and it has no Damage Source ID"), Index + 1, NewTimes[Index]);
				continue;
			}
			if (!DamageClass || !DamageClass->IsChildOf(UAnimNotify::StaticClass()))
			{
				Notes += TEXT("; no damage notify made: EndAnimNotifyBattleDamage (EndGame) is not loaded");
				break;
			}
			UAnimNotify* Notify = NewObject<UAnimNotify>(Sequence, DamageClass, NAME_None, RF_Transactional);
			ApplyHitDamage(Notify, *Hits[Index], Notes);
			FAnimNotifyEvent Event;
			Event.Notify = Notify;
			Event.NotifyName = FName(*Notify->GetNotifyName());
			LastTrack = FMath::Max(LastTrack, ShotTrack + 1);
			PlaceNotify(Sequence, Event, NewTimes[Index], 0.f, ShotTrack + 1);
			Sequence->Notifies.Add(Event);
			NewHits.Add(NewTimes[Index]);
			++Result.HitsMade;
		}
		if (Result.HitsMade > 0)
		{
			Notes += TEXT("; check the new damage notifies' Create Position settings in the animation editor (they keep the game's defaults)");
		}
	}
	NewHits.Sort();
	for (int32 Index = 0; Index < NewHits.Num(); ++Index)
	{
		if (Index == 0 || NewHits[Index] - NewHits[Index - 1] >= 0.05f)
		{
			++Result.Hits;
		}
	}
	for (int32 Index = 0; Index < Hits.Num(); ++Index)
	{
		Result.Effects += AddHitEffects(Sequence, *Hits[Index], NewTimes[Index], ShotTrack, Notes);
	}
	if (Move.bShot)
	{
		float Last = -1.f;
		for (const float Time : NewHits)
		{
			if (Last >= 0.f && Time - Last < 0.05f)
			{
				continue; // several damage notifies of one hit: one shot
			}
			Last = Time;
			if (AddShotEffects(Sequence, Shot, Time, ShotTrack, Notes) > 0)
			{
				++Result.Shots;
			}
		}
		if (NewHits.Num() == 0)
		{
			Notes += TEXT("; Shot: no hit to put the shot effects on");
		}
	}
#if WITH_EDITORONLY_DATA
	while (Sequence->AnimNotifyTracks.Num() <= LastTrack)
	{
		const int32 Index = Sequence->AnimNotifyTracks.Num();
		const FString TrackName = Index == ShotTrack ? FString(TEXT("Hits")) : FString::FromInt(Index + 1);
		Sequence->AnimNotifyTracks.Add(FAnimNotifyTrack(FName(*TrackName), FLinearColor::White));
	}
#endif
	return Result;
}

