# Merge C: the compat set, built (2026-10-27)

Builder: merge1027/build/build_compat.py <out> <built CharaSpec.uasset> (the CharaSpec Merge D built: bt2/pkgs/
DataObject__Resident__CharaSpec.uasset). Sources: cj/ (the installed compat, skins, customization, Lua, read-only copies),
c/FullyPlayableSora.skelcompat.json, lvl/scan.json (the levels' planner sets), the game's and FPYS's tables.
Output (cloud): scratchpad cmp3; PC staging: C:\FF7R2UProj\Saved\ModExtract\merge1027\compat (not installed).
Checks: build/checks/check_compat.cpp (the DLL core's parser on the folder as it will be: cj's files with these over
them, the paks of checks/paks_after.txt), build/checks/assets_exist.py (every /Game/ path the files name is in the game,
the merged container or a pak left installed), cacs3210/tests/owners_sim.sh (whose abilities play, per character).

## Files
compat/ (replace or add; same names as the installed ones where they exist)
- FullyPlayableCreateACharacterSystemExperience.json (new): the CHARACTER page's YOUNG SEPHIROTH, SEPHIROTH, VINCENT, SORA
  for Cloud's place (Cloud the place's own). Each: charaspecs (R9 + _NoBattle/_Reserve -> the row, 8 weapons; SORA also
  06/07/11; both Sephiroths also Sephiroth's 6 rows + WE1021_00/01/02/10 -> _EVILCLOUD, Alexander -> _BIZARRO), names
  (13 OA pack names of the levels' planner sets -> the row's own; AnimSet_Hofuku00_PC0000_Cloud -> the folder's for
  YS/SEPH/SORA), names_in_add (Item CharaSpecID, 9 levels' PlannerLevelSet LevelList_Array optional; Sephiroths also
  BattleCharaSpec, CharaSpecUseList, EnemyBookBattleCharaSpec, 3120-CAPTL BattleCharaSpec optional), battle voice
  (106 BT_BVCLD rows; Sephiroths FPYS's + its 3 voice-list rows), Sephiroths' rows (pt_Cloud, 11 abilities keep
  UniqueId, 78 damage, pt_Sephiroth, 9 Bizarro abilities) and values (W_TSW_9001 / key_collection_07 back to the game's
  weapons, summon choices 08-10 Probability 50, 10 Bizarro text keys). requires_paks: the merged pak (+ YoungSephiroth_P
  and both voice paks for YS, the voice paks for SEPH, SoraAssets_P / SoraFace_P / SoraFaceRig_P / SoraKH3_Materials_P
  for SORA).
- YoungSephirothForms.json, SephirothForms.json: on YS's / SEPH's 9 rows. PlayableYoungSephiroth_Swap.json,
  EvilCloudBoss_FPYS.json: Evil Cloud on the _EVILCLOUD rows. BizarroSummon_FPYS.json: on Alexander's _BIZARRO row.
  VincentDirge / VincentGalian / Vincent_Moves.json: on VINCENT's 9 rows. FullyPlayableSora.skelcompat.json: SORA's 12
  rows + 8 weapons (Cloud's cutscene rows dropped). VincentGun_WeaponCompat_TEST.json as it was.
  Every requires_paks (animation sets, pairs) naming FullyPlayableYoungSephirothDataAssets_P, FullyPlayableSephirothDataAssets_P,
  FullyPlayableVincentAssets_P or FullyPlayableSoraInRebirth -> the merged pak.
- Left as they are (off by themselves: their paks are not installed): CloudCharacter.json (CreateACharacterCloud_P;
  move it aside at the install: the merge drops CLOUD's copy), PlayableSephiroth_Swap.json, EvilCloudBoss.json,
  BizarroSummon.json (FPS's data pak), SephirothCloudSwap_TEST.json. Kawaii, outfits, SaferSephiroth, SeraphWeaponFamily,
  VincentChaos, VIncenttoChaosSkelCompat: by model / skeleton, unchanged.
skins/<name>.json -> skins\<name>\skin.json: the 25 skins that were on Cloud's 9 rows (FPYS made them Young Sephiroth's)
  on both Sephiroths' 18 rows; Cloud's looks (RebirthCloud, RemakeCloud) on Cloud's own 9 rows too. The *Seph skins (the
  game's Sephiroth rows) unchanged.
customization/saved.json: the choices made on Cloud's rows (Young Sephiroth's then) on YS's rows; the CLOUD copy's
  (_CACS) voice choice dropped.
SephirothForms/Scripts/main.lua: CONFIG.rows = both Sephiroths' 18 rows (the Lua forms mod until 3.22 has it).

## Check results (cmp3, 2026-10-27)
- check_compat: YOUNG SEPHIROTH / SEPHIROTH specs 44, names 14, names_in 18, rows 100, values 18; VINCENT 33/13/14/0/1;
  SORA 42/14/14/0/1; 59 animation-set rows; 40 skins. Notes only the expected: FPS-pak / TEST / CloudCharacter /
  outfit entries off, joined rows, skins without a model, ability pages.
- Families: one body family on Sephiroth's skeleton (PC0010_00, the hub PlayableYoungSephiroth_Swap.json names, as the
  skins already do: Cloud's, Evil Cloud's, Young Sephiroth's, Vincent's, Chaos's and every Sephiroth skin's skeleton are
  members); VincentChaos.json and Vincent_Moves.json ask for Cloud's skeleton as hub (noted; it is a member). Weapons:
  one family on the Buster Sword (Masamune, Nameless, Essence Shard, Quicksilver members).
- assets_exist: every path resolves after the install but the two editor "source" entries.
- owners_sim: YS -> pt_Cloud YoungSephirothForms' row, pt_Sephiroth Evil Cloud's; SEPH -> SephirothForms', Evil
  Cloud's; VINCENT -> his row; SORA, nobody -> the rows' own. Needed the 3.21.0 fix (below): before it, Evil Cloud's
  pt_Sephiroth abilities (Sephiroth's AtkBurst02 -> PC0000_EvilCloud_AtkBurst02) never played with either Sephiroth.

## DLL 3.21.0 (cacs3210; fixed 2026-10-27 after the review)
- OwnsRow / OwnerOfRow / OwnersOfRow / HolderOfRow / PlayersOf: a row several characters own plays while any of them has
  a place; a character's rows may list abilities for another player row (Evil Cloud's pt_Sephiroth), whose lists,
  weapon abilities and pages go when it leaves and whose status is recalculated. Syntax check (chk.sh) clean; core tests
  pass. README.txt / README.md: 3.21.0 (names, names_in_add / optional, several characters per place, owners).

## Install (Merge I, with the user, the game closed)
- ue4ss\Mods\RebirthSkelCompat\compat: back up the replaced files (game's _mod_backups), copy compat/*.json;
  CloudCharacter.json moved aside. skins: skins\<name>\skin.json for each. customization\saved.json.
- ue4ss\Mods\SephirothForms\Scripts\main.lua (until 3.22 folds it into the DLL).
- DLL 3.21.0 (built on the PC first). Paks: see MERGE_D_DONE.md.
