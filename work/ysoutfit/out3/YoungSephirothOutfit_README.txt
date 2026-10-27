Young Sephiroth - an optional outfit for the playable Sephiroth (Create a Character System)

Young Sephiroth's clothes and hair on Sephiroth (PC0010_10_Young_Sephiroth_Outfit_Transformed), with the transformed
Sephiroth's wing. He wears it on every Cloud row the Fully Playable Sephiroth takes over, everywhere his own model
shows: the field, battle, cutscenes and the menus. Every form works with it: NORMAL hides the wing, WINGED, FLYING and
KH2 fade it in (the material slot PC0010_10_Wing, the forms' wing part), BIZARRO and SAFER put on their own models and
come back to the outfit. His coat, hair, collar and shoulder pads swing with their own v3 Bonamik (PC0010_10_YS_BNM),
the wing and Sephiroth's own physics bones with the game's PC0010_10_BNM.

Install (game closed):
  1. YoungSephirothOutfit_P.pak, YoungSephirothOutfit_P.ucas and YoungSephirothOutfit_P.utoc into
     FINAL FANTASY VII REBIRTH\End\Content\Paks\~mods
  2. YoungSephirothOutfit.json into
     FINAL FANTASY VII REBIRTH\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat
  Needs Create a Character System 3.6 or later, FullyPlayableSephirothDataAssets_P and SephirothForms.json.
  One outfit at a time: take AvalancheSephirothOutfit_P's three files out of ~mods while this one is in (both dress the
  same blueprint).

Remove: take the three YoungSephirothOutfit_P files out of ~mods. He wears his own model again (the json does nothing
without them).

What is in it:
  * the outfit (PC0010_10), its skeleton (PC0010_10_Skeleton), its materials (CH049_001_Body, CH049_001_Hair: the game's
    own surface materials with Young Sephiroth's textures), their 8 textures and its Bonamik (PC0010_10_YS_BNM);
  * Sephiroth's character blueprint (PC0010_00_Sephiroth_Standard, the one Cloud's rows spawn) with its mesh set to the
    outfit; everything else in it is the game's own;
  * the skeleton compatibility (YoungSephirothOutfit.json): PC0010_10_Skeleton is Sephiroth's skeleton with 103 more
    bones for Young Sephiroth's coat, hair, collar and shoulder pads, so it joins his skeleton family and plays all of his
    animations.
