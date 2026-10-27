Avalanche Sephiroth - an optional outfit for the playable Sephiroth (Create a Character System)

Sephiroth in the Avalanche clothes, with the transformed Sephiroth's wing (PC0010_12_Avalanche_Sephiroth_Transformed).
He wears it everywhere his own model shows: the field, battle, cutscenes and the menus. Every form works with it:
NORMAL hides the wing, WINGED, FLYING and KH2 fade it in (the material slot PC0010_10_Wing, the forms' wing part),
BIZARRO and SAFER put on their own models and come back to the outfit.

Install (game closed):
  1. AvalancheSephirothOutfit_P.pak, AvalancheSephirothOutfit_P.ucas and AvalancheSephirothOutfit_P.utoc into
     FINAL FANTASY VII REBIRTH\End\Content\Paks\~mods
  2. AvalancheSephirothOutfit.json into
     FINAL FANTASY VII REBIRTH\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat
  Needs Create a Character System 3.6 or later, FullyPlayableSephirothDataAssets_P and SephirothForms.json.

Remove: take the three AvalancheSephirothOutfit_P files out of ~mods. He wears his own model again (the json does
nothing without them).

What is in it:
  * the outfit (PC0010_12) and its skeleton (PC0010_11_Skeleton);
  * Sephiroth's character blueprint (PC0010_00_Sephiroth_Standard, the one Cloud's rows spawn) with its mesh set to the
    outfit; everything else in it is the game's own;
  * the skeleton compatibility (AvalancheSephirothOutfit.json): PC0010_11_Skeleton is Sephiroth's skeleton with 187 more
    bones for the clothes (jacket, hood, collar, belt, more hair), so it joins his skeleton family and plays all of his
    animations; the clothes' bones are moved by the outfit's own cloth physics.
