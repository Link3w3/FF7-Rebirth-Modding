// ------------------------------------------------------------
// 1. Base color & normals
// ------------------------------------------------------------
float3 BC   = BaseColor;
float3 Nrm  = normalize(NormalWS);
float3 Ldir = normalize(-LightDirWS);
float3 Vdir = normalize(ViewDirWS);

// ------------------------------------------------------------
// 2. Dye application (Storm-style)
// ------------------------------------------------------------
float3 DyedBC = lerp(BC, BC * DyeColor, saturate(DyeMask * DyeStrength));
BC = DyedBC;

// ------------------------------------------------------------
// 3. NdotL
// ------------------------------------------------------------
float NdotL = saturate(dot(Nrm, Ldir));

// ------------------------------------------------------------
// 4. Storm 4–style 3-band toon via ramp
// ------------------------------------------------------------
float ShadowMul = ShadowRampRGB.r;
float MidMul    = ShadowRampRGB.g;
float LitMul    = ShadowRampRGB.b;

float3 ColShadow = BC * ShadowMul;
float3 ColMid    = BC * MidMul;
float3 ColLit    = BC * LitMul;

float3 ToonCol = ColShadow;

if (NdotL >= ShadowThreshold && NdotL < MidThreshold)
    ToonCol = ColMid;

if (NdotL >= MidThreshold)
    ToonCol = ColLit;

// ------------------------------------------------------------
// 5. Specular band (Storm-style)
// ------------------------------------------------------------
float3 H = normalize(Ldir + Vdir);
float NdotH = saturate(dot(Nrm, H));
float SpecTerm = pow(NdotH, SpecSharpness) * SpecIntensity;

float SpecBand = step(SpecThreshold, SpecTerm) * SpecRampVal;
float3 SpecCol = SpecBand;

// ------------------------------------------------------------
// 6. Hair / metal anisotropic highlight
// ------------------------------------------------------------
float3 T = normalize(cross(float3(0,0,1), Nrm));
float HairDot = abs(dot(Vdir, T));
float HairStrip = smoothstep(1.0 - HairSpecWidth, 1.0, HairDot);
float HairSpec = HairStrip * HairSpecIntensity;

// ------------------------------------------------------------
// 7. Rim light
// ------------------------------------------------------------
float RimBase = 1.0 - saturate(dot(Vdir, Nrm));
float Rim = pow(RimBase, RimPower) * RimStrength;

// ------------------------------------------------------------
// 8. Internal outline darkening
// ------------------------------------------------------------
float OutlineMask = pow(1.0 - saturate(dot(Vdir, Nrm)), 3.0) * OutlineStrength;

// ------------------------------------------------------------
// 9. Combine
// ------------------------------------------------------------
float3 Final = ToonCol;
Final += SpecCol;
Final += HairSpec;
Final += Rim;
Final -= OutlineMask;

return Final;
