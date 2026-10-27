// ------------------------------------------------------------
// 1. Normalize vectors
// ------------------------------------------------------------
float3 N = normalize(NormalWS);
float3 L = normalize(-LightDirWS);
float3 V = normalize(ViewDirWS);

// ------------------------------------------------------------
// 2. Hair Masks (two independent channels)
// ------------------------------------------------------------
float HairMaskA_local = saturate(HairMaskA_input);   // Texture R
float HairMaskB_local = saturate(HairMaskB_input);   // Texture G
float HairMaskCombined = saturate(max(HairMaskA_local, HairMaskB_local));

// ------------------------------------------------------------
// 3. Hair Dye A
// ------------------------------------------------------------
float HairAWeight = saturate(HairMaskA_local * HairIntensityA);
float3 DyedA = lerp(BaseColor, HairColorA, HairAWeight);

// ------------------------------------------------------------
// 4. Hair Dye B
// ------------------------------------------------------------
float HairBWeight = saturate(HairMaskB_local * HairIntensityB);
float3 DyedAB = lerp(DyedA, HairColorB, HairBWeight);

// ------------------------------------------------------------
// 5. Global Dye (does NOT affect hair)
// ------------------------------------------------------------
float DyeWeight = saturate(DyeMask * DyeStrength);
float NonHairDyeWeight = DyeWeight * (1.0 - HairMaskCombined);
float3 BC = lerp(DyedAB, DyeColor, NonHairDyeWeight);

// ------------------------------------------------------------
// 6. NdotL
// ------------------------------------------------------------
float NdotL = saturate(dot(N, L));

// ------------------------------------------------------------
// 7. Blue‑Tinted Shadows (Bleach color grade)
// ------------------------------------------------------------
float3 ShadowTint = float3(0.75, 0.85, 1.10); // subtle blue
float3 ColShadow = BC * ShadowIntensity * ShadowTint;
float3 ColMid    = BC * MidIntensity;
float3 ColLit    = BC * LitIntensity;

// ------------------------------------------------------------
// 8. 3‑Band Toon Shading
// ------------------------------------------------------------
float3 ToonCol = ColShadow;
if (NdotL >= ShadowThreshold && NdotL < MidThreshold) ToonCol = ColMid;
if (NdotL >= MidThreshold) ToonCol = ColLit;

// ------------------------------------------------------------
// 9. Specular
// ------------------------------------------------------------
float3 H = normalize(L + V);
float NdotH = saturate(dot(N, H));
float Spec = pow(NdotH, SpecPower) * SpecIntensity;

// ------------------------------------------------------------
// 10. Directional Rim Light
// ------------------------------------------------------------
float Fres = 1.0 - saturate(dot(N, V));

// Top‑rim bias
float TopMask = saturate(dot(N, float3(0,1,0)));

// Back‑rim bias
float BackMask = saturate(dot(N, -L));

// Final directional rim mask
float DirRimMask = saturate(TopMask * 0.6 + BackMask * 0.4);

// Colored rim
float RimColoredRaw = pow(Fres, RimPower) * RimStrength * DirRimMask;
float3 RimColored = RimColoredRaw * RimMask * RimColor;

// Hair rim (white)
float HairRimRaw = pow(Fres, HairRimPower) * HairRimStrength * DirRimMask;
float3 RimHair = HairRimRaw * HairMaskCombined * HairRimColor;

// Base rim fallback
float RimBaseRaw = pow(Fres, RimPower) * (RimStrength * 0.25);
float3 RimBase = RimBaseRaw * (1.0 - RimMask);

// Final rim
float3 Rim = RimColored + RimHair + RimBase;

// ------------------------------------------------------------
// 11. Hair Shine Strip (ROS‑style) WITH TOGGLE
// ------------------------------------------------------------
float3 HairNormal = normalize(N);
float ShineDot = saturate(dot(HairNormal, normalize(float3(0,1,0))));
float ShineBand = smoothstep(ShineCenter - ShineWidth, ShineCenter + ShineWidth, ShineDot);

// Toggle: 1 = ON, 0 = OFF
float3 HairShine = (UseHairShine > 0.5)
    ? (ShineBand * HairShineIntensity * HairMaskCombined)
    : 0;

// ------------------------------------------------------------
// 12. Face Shadow Cutoff (Bleach style)
// ------------------------------------------------------------
float FaceMask = saturate(FaceMaskR); // face + neck + ears
float FaceCut = saturate(dot(N, L));
float FaceShadow = smoothstep(FaceCutoff - FaceSoftness, FaceCutoff + FaceSoftness, FaceCut);
float3 FaceShade = lerp(ColShadow, BC, FaceShadow);
float3 FaceResult = lerp(ToonCol, FaceShade, FaceMask);

// ------------------------------------------------------------
// 13. Colored internal outline
// ------------------------------------------------------------
float OutlineFactor = pow(1.0 - saturate(dot(N, V)), OutlineWidth);
OutlineFactor *= OutlineStrength;
float3 OutlineCol = OutlineColor * OutlineFactor;

// ------------------------------------------------------------
// 14. Combine lighting
// ------------------------------------------------------------
float3 Final = FaceResult + Spec + Rim + HairShine;
Final -= OutlineCol;

// ------------------------------------------------------------
// 15. ROS forced fold shading
// ------------------------------------------------------------
Final = lerp(Final, ColShadow, saturate(ShadowMask));

// ------------------------------------------------------------
// 16. Output
// ------------------------------------------------------------
return saturate(Final);
