# Merge D: the data container (decisions, 2026-10-27)

Base: the game's own tables; Cloud and Sephiroth and Alexander rows stay the game's. Each character's own rows, packs,
blueprints, AI blueprints, weapon blueprints and voice; the CHARACTER page renames (names_in) and mirrors (rows/values).

Tags: YOUNGSEPHIROTH, SEPHIROTH, VINCENT, SORA; EVILCLOUD (Sephiroth's 6 rows + WE1021_00/01/02/10, with either
Sephiroth character), BIZARRO (SU2030_00_Alexander_Standard, with either Sephiroth character).

Rows: R9 = Cloud 00,04,08,09,10,12,18,19,23 for every character; SORA also 06,07,11 (EventCharaSpec). NoBattle/Reserve:
the row itself (FPYS / Vincent did that). Weapons: WE0000_00, 11-16, 17 (05 Nail Bat: nothing names it; skipped).
  YS / SEPH rows: FPYS's values; ContentsModel = BP copy; AI = AIBP copy.
  VINCENT rows: Vincent mod's (08/09/10 made like them on the game's rows); BP copy of PC0011_00; voice bank copy.
  SORA rows: the game's Cloud rows; folder PC0000_00_Sora_KH2; BP copies of SoraOverCloud_P's; voice bank copy.
  EVILCLOUD: FPYS's 6 Sephiroth rows; NoBattle/Reserve/Equipment names to the _EVILCLOUD ones.
Packs: every new row's pack (renamed from FPYS / Vincent / the game's, imports remapped: BP, AIBP, voice, motion sets for
Sora's folder); OA packs for every index of a row's OverrideAnimationSetString_Array (Motion/Level/<set>/<folder>); SFV
packs none (SoundVoisePack_Array emptied, as FPYS).
CharaPopPack rows for every new pack (list: the pack's own BP / Effect / LipSync / Motion / Sound imports + the source
list's transitive keys, model key per character); CharaPopAsset rows for every new key (copied from the analogous asset,
else the package size).
BP copies: PC0010_00_Sephiroth_Standard_YOUNGSEPHIROTH (FPYS's PC0010_00 override), _SEPHIROTH (the game's),
PC0011_00_Vincent_Standard_VINCENT (the game's), Sora's 12 (SoraOverCloud_P's, parent -> PC0000_00_Cloud_Standard_SORA),
Sora's ABP PC0000_00_Cloud_Standard_SORA_Animation (SoraFaceRig_P's, lip maps -> renamed copies of SoraFace_P's).
Weapon BP copies: WE1021_00_..._YOUNGSEPHIROTH (FPYS's Nameless), WE1021_00_..._SEPHIROTH (the game's),
WE0011_00_Vincent_Quiksilver_VINCENT (the game's), Sora's WE0000_xx_..._SORA (SoraOverCloud_P's Kingdom Keys).
AIBP copies: PC0010_00_Sephiroth_Standard_<YS|SEPH>_AIBP, PC0000_00_Cloud_Standard_<VINCENT|SORA>_AIBP.
Voice: VO_PC0000_00_Cloud_VINCENT, VO_PC0000_00_Cloud_SORA (JP/DE/FR/US, the mods' US banks renamed: package, export,
SEAD bank name and id); localization record as the game's (04 03 02 04 0b, DE FR US).

Tables (the game's + additions):
  CharaSpec: new rows; PC0009_03 / EN0000_33 / PC0010_01 wet-row battle fixes (both mods had them).
  BattlePlayerParameter: pt_Cloud_SEPHIROTH (FPYS pt_Cloud), pt_Sephiroth_EVILCLOUD (FPYS pt_Sephiroth).
  BattleAbility: FPYS's 49 new abilities; Cloud's 11 as <ID>_SEPHIROTH; Alexander's 9 as <ID>_BIZARRO; Vincent's 17.
  BattleDamageSource: FPYS's 145 new + 78 as <row>_SEPHIROTH; Vincent's 211.
  BattleSummonAbilityChoice: FPYS's +3 (check Alexander without Bizarro).
  Effect2SoundTable: each new pack next to its source pack wherever FPYS's (YS/SEPH/EVIL/BIZ) or the game's
  (VINCENT/SORA) table lists the source.
  PlannerEventVoiceList: + VO_PC0000_00_Cloud_VINCENT / _SORA rows.
  CharaPopPack / CharaPopAsset: as above.  Text: the game's + FPYS's 54 + Bizarro's names as new keys + gun shop's.
  Equipment, PlannerEvent: the game's (values in the character entries).
CHARACTER entries (Merge C): charaspecs (R9, weapons, + Sephiroth's for EVILCLOUD, Alexander for BIZARRO), names (OA pack
names of the levels' planner sets), names_in_add: BattleCharaSpec CharaSpecID, CharaSpecUseList UseCharaSpec,
EnemyBookBattleCharaSpec CharaSpecID, Item CharaSpecID, 11 levels' PlannerLevelSet LevelList_Array (optional),
3120-CAPTL BattleCharaSpec CharaSpecID (optional); values: W_TSW_9001 / key_collection_07 back to the game's weapons,
voice lists; rows: pt_Cloud, abilities (keep UniqueId), damage, pt_Sephiroth.

Container: FPYS's .ucas as it is + a tail (new header, tables, packages, Vincent's new-path files); the new .utoc lists
FPYS's chunks but the 45 game-path overrides. Assembled on the PC (prefix MD5 checked); read back in the cloud.
