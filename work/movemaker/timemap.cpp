// Times of the original on the new animation: piecewise linear through anchors (an original hit -> its new time), and in
// proportion to the lengths before the first anchor, between anchors and after the last one (no anchor: in proportion).
struct FBuildTimeMap
{
	float OldLength = 0.f;
	float NewLength = 0.f;
	TArray<TPair<float, float>> Anchors; // (time in the original, time in the new animation), both increasing

	float Map(float Time) const
	{
		Time = FMath::Clamp(Time, 0.f, OldLength);
		float PrevOld = 0.f;
		float PrevNew = 0.f;
		for (const TPair<float, float>& Anchor : Anchors)
		{
			if (Time <= Anchor.Key)
			{
				const float Span = Anchor.Key - PrevOld;
				return Span > KINDA_SMALL_NUMBER ? PrevNew + (Time - PrevOld) * (Anchor.Value - PrevNew) / Span : Anchor.Value;
			}
			PrevOld = Anchor.Key;
			PrevNew = Anchor.Value;
		}
		const float Span = OldLength - PrevOld;
		return Span > KINDA_SMALL_NUMBER ? PrevNew + (Time - PrevOld) * (NewLength - PrevNew) / Span : PrevNew;
	}
};

