// What the Move Maker lists of a character's animation names (editor 1.8).
bool SlotIsKind(const FString& Name, EEndMoveSlotKind Kind)
{
	if (Kind == EEndMoveSlotKind::Everything)
	{
		return true;
	}
	const SkelCompat::Detail::AnimName Parsed = SkelCompat::Detail::ParseAnimName(Wide(Name));
	const FString Body = FromWide(Parsed.Body);
	const bool bLimit = Body.StartsWith(TEXT("atklimit"));
	const bool bAbility = !bLimit && (Body.StartsWith(TEXT("atkburst")) || Body.Contains(TEXT("ability")));
	switch (Kind)
	{
	case EEndMoveSlotKind::LimitBreaks:
		return bLimit;
	case EEndMoveSlotKind::Abilities:
		return bAbility;
	case EEndMoveSlotKind::Attacks:
	{
		const int Kind2 = SkelCompat::Detail::TargetKind(Parsed);
		return Kind2 == 1 || Kind2 == 2;
	}
	default:
		return true;
	}
}

