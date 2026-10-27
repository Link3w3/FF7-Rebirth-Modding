# FullyPlayableCreateACharacterSystemExperience: inventory (2026-10-27)

Sources: the installed FPYS folder (~mods\FullyPlayableSephirothPaks\FullyPlayableYoungSephirothPaks), the zips in ~mods
(FullyPlayableSephirothPaks.zip, FullyPlayableVincentPaks.zip, FullyPlayableSoraInRebirth.zip), their .utoc file lists
(inv/, inv_files.json), the tables decoded with build_atb.Table against the game's (owncloud/gx/van3).
Third-party paks were not read (Sephiroth Original-style Stats (MP Growth)_P sits in FullyPlayableSephirothPaks, active).

## Installed now
FPYS folder: FullyPlayableYoungSephirothDataAssets_P (271 MB, 1199 files), YoungSephiroth_P, YoungSephirothVoice_P,
ClassicSephirothVoice_P, KH2SephirothPaks\KH2Sephiroth_P, SephirothTitleScreen_P, CloudMoveset\CloudMovesetMoves_P,
CreateACharacterCloud\CreateACharacterCloud_P. Zipped (inactive): FPS data (10-22), Vincent (10-17), Sora (10-19), outfits.
UE4SS: RebirthSkelCompat (DLL 3.20.2), SephirothForms (Lua: main.lua rows = Cloud's 9 rows; ForceGrabs, MeteorStrike).

## What each mod overrides (the clashes)
| asset | FPYS | Vincent | Sora | CLOUD (CACS) |
|---|---|---|---|---|
| Cloud's 9 CharaSpec packs (00,04,08,09,10,12,18,19,23) | -> Sephiroth BP (PC0010_13 mesh) | 6 of them -> PC0011_00_Vincent_Standard | - | own copies _CACS (441) |
| Cloud's 9 weapon packs (WE0000_00,05,11-17) | -> Masamune BP (wearing Nameless) | -> WE0011_00_Vincent_Quiksilver | - | _CACS copies |
| CharaSpec table | 31 rows changed | 18 changed + PC0011_10_Chaos | - | _CACS rows (in FPYS) |
| BattleAbility | +49, 20 changed (11 Cloud IDs, 9 Alexander) | +17 (PC0011_GB_*) | - | +11 _CACS |
| BattleDamageSource | +145, 78 changed (PC0010_*) | +211 (PC0011_Dirge_* ...) | - | - |
| BattlePlayerParameter | pt_Cloud, pt_Sephiroth changed | - | - | pt_Cloud_CACS |
| Effect2SoundTable | 51 changed | - | - | his packs added |
| Equipment | W_TSW_9001 | - | - | (value) |
| PlannerEvent / VoiceList | 106 BT_BVCLD_* / 3 rows | - | - | (values) |
| BattleSummonAbilityChoice | +3 (Bizarro summon) | - | - | - |
| Resident_TxtRes | yes | gun shop (zz) | - | - |
| Item/ShopItem/ShopList | - | gun shop (on VR Simulator Overhaul's) | - | - |
| CharaPopPack/CharaPopAsset | - | - | - | CreateACharacterCloud_P |
| Cloud's 18 BPs + 13 weapon BPs | - | - | mesh swapped (SoraOverCloud_P) | own copies |
| Cloud's ABP | - | - | face rig (SoraFaceRig_P) | own copy |
| Cloud's lip maps | - | - | SoraFace_P | - |
| Cloud's field/level/mount sets (1296) | - | - | SoraOverCloudMotion_P | - |
| Cloud's 3 voice banks (US) | - | VincentVoice_P | SoraVoice_P | - |
| Sephiroth's BP PC0010_00 | mesh -> PC0010_13 | - | - | - |
| Sephiroth's mesh PC0010_00 | (KH2Sephiroth_P: KH2 model) | - | - | - |
| Sephiroth's 6 packs | -> Evil Cloud | 1 wet row | - | - |
No id clashes: FPYS's and Vincent's added BattleAbility UniqueIds differ; damage row names differ.

## Per character (now)
- YOUNG SEPHIROTH (FPYS): Cloud's rows ContentsModel PC0010_00_Sephiroth_Standard (BP wearing PC0010_13), parent folder
  PC0010_Sephiroth, AI PC0010_00_Sephiroth_Standard_AIBP, sets Battle00-10, voice VO_PC0010_13_YoungSephiroth (+Classic,
  +Sephiroth's for OLDER), weapons Nameless (WE1021_00 BP) / Masamune (WE1021_10 BP) / DNT, CC, Remake swords.
  Compat: YoungSephirothForms.json, PlayableYoungSephiroth_Swap.json, EvilCloudBoss_FPYS, BizarroSummon_FPYS, kawaii, skins.
- SEPHIROTH (FPS, older data): same rows idea, game's Sephiroth BP (FPS overrode PC0010_00 mesh), Masamune. SephirothForms.json.
- VINCENT: Cloud's 6 rows -> PC0011_00_Vincent_Standard, sets + Battle07/08, Facial07, Vincent effects/SE; AI Cloud's;
  weapon Quicksilver; abilities/damage added; VincentDirge.json (shooter), Vincent_Moves.json, VincentGalian.json
  (Galian, Chaos forms; player pt_Cloud), VincentChaos.json; gun shop; voice over Cloud's banks.
- SORA: Cloud's rows untouched; Cloud's BPs/ABP/lip maps/motion/voice overridden; FullyPlayableSora.skelcompat.json on
  48 Cloud rows (his folder PC0000_00_Sora_KH2 for battle/field; field actions from Cloud's folders); AI Cloud's.
- CLOUD: CreateACharacterCloud_P + _CACS rows in FPYS + CloudCharacter.json (charaspecs 27, rows 12, values).

## CHARACTER page facts (DLL 3.16-3.20)
- Lists the place's own, then every character of that place (several per place work).
- charaspecs: names rewritten in PlayerTable, PlannerEventChara, BikeCharaSpec, Equipment (the only resident tables that
  name Cloud's rows; non-resident level data not checked). rows/values: copies into the game's rows (Mirror).
- TakenBy: while any character has pt_Cloud's place, EVERY compat row's abilities for pt_Cloud stand down -> a
  character's own forms' abilities would stand down too (needs a 3.21 fix).
- A BP under a new name in a place needs CharaPopPack/CharaPopAsset rows (FPYS v1/v2 loaded forever without them).
