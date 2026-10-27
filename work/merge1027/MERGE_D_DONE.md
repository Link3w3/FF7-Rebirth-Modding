# Merge D: built (2026-10-27)

Builder: merge1027/build — build_pkgs.py <build dir> (packages + tables), assemble.py <build dir> <out> (the container's
index + new part + PC plan), companions.py <out> (companion paks), check_deps.py <build dir> (every import resolves).
PC staging: C:\FF7R2UProj\Saved\ModExtract\merge1027\out (FullyPlayableCreateACharacterSystemExperience_P .utoc/.ucas/.pak,
assembled there by assemble_pc.py from FPYS's .ucas in FullyPlayableSephirothPaks.zip: 239161744 bytes, md5 ccde33fd...,
every chunk read back) and ...\merge1027\companions (KH2Sephiroth_P md5 17d25b6a..., SoraFace_P, SoraFaceRig_P,
zzVincentGunShop_P). Nothing installed.

## The container (2513 chunks)
- FPYS's 1148 chunks (its new paths; its Sephiroth Neutral00 kept: the game's set + N_Atk01/N_Avoid01, a superset), 36 of
  FPYS's game-path overrides left out (Cloud's / Sephiroth's / Alexander's / weapons' packs, PC0010_00 + WE1021_00/01/02/10
  BPs, Equipment, PlannerEvent), 15 made anew (8 tables, FPYS's 7 swords WE1021_60..67 re-parented to
  WE1021_00_SephirothIllusion_Masamune_YOUNGSEPHIROTH = FPYS's Nameless, so they keep its sword trail; names kept).
- 1364 new: 38 BPs (YS/SEPH/VINCENT BP + weapon BP, 4 AIBPs, Sora's 12 BPs + 8 Kingdom Keys + ABP, FPYS swords), Sora's 3
  lip maps, 82 packs, 1168 OA packs (CharaSpec_<row>OA<i>: YS/SEPH 9x34 -> Motion/Level/<set>/PC0010_Sephiroth, VINCENT
  9x20 -> PC0000_Cloud, SORA 12x20 -> PC0000_00_Sora_KH2, EVIL 4x34 -> PC0000_EvilCloud), 2 voice banks, Vincent's 61
  motions (Built/Vincent + Vincent's 4 strafing walks), 10 tables.
- Voice: /Game/Sound/Voice/JP/Character/Player/VO_PC0000_00_Cloud_VINCENT / _SORA, one package each (the mods' US bank;
  no localization record, so every language loads it), SEAD bank renamed, bank id 24256 / 24168 (tracks too), new GUID.

## Tables (the game's + rows)
- CharaSpec +83: YS/SEPH 9 rows + 8 weapons (FPYS's; ContentsModel/AI/NB/RS their own), VINCENT 9 + 8 + PC0011_10_Chaos
  (Vincent's; 08/09/10 made like his others; voice his bank, no story voice packs), SORA 12 + 8 (the game's rows; folder
  PC0000_00_Sora_KH2; BPs his), EVILCLOUD 6 + 4, BIZARRO 1; fixes: PC0009_03, EN0000_33 (FPYS), PC0010_01 (Vincent).
- BattleAbility: FPYS's 49, Vincent's 17, PC0000_* x11 as <ID>_SEPHIROTH, SU2030_00_* x9 as <ID>_BIZARRO (new UniqueIds;
  Name/Explanation -> the _BIZARRO text keys). BattleDamageSource: FPYS's 145, Vincent's 211, FPYS's 78 changed as
  <row>_SEPHIROTH. BattlePlayerParameter: pt_Cloud_SEPHIROTH, pt_Sephiroth_EVILCLOUD. BattleSummonAbilityChoice:
  SU2030_00_AbilityChoice_08/09/10 with Probability 0 (FPYS: 50.0; Bizarro's entry restores it).
- PlannerEventVoiceList: VO_PC0000_00_Cloud_VINCENT / _SORA -> Character/Player/<bank>. US text: FPYS's 54 keys, the 10
  Bizarro texts as <key>_BIZARRO, the gun shop's 47.
- Effect2SoundTable: every new row/weapon pack next to its source pack (FPYS's table for YS/SEPH/EVIL/BIZ, the game's for
  VINCENT/SORA). CharaPopPack +1418 (packs, OA packs, AnimSet_<set>_<folder> for the new folders' level and field-action
  sets: no packages, as most of the game's), CharaPopAsset +225.

## Merge C needs (CHARACTER entries)
- charaspecs: R9 (+ their _NoBattle/_Reserve -> the row), weapons; SORA + 06/07/11; EVIL: Sephiroth's 6 + WE1021_00/01/02/10;
  BIZ: Alexander.
- names: CharaSpec_<row>OA<i> -> CharaSpec_<row>_<TAG>OA<i> (the levels list 13); AnimSet_Hofuku00_PC0000_Cloud ->
  AnimSet_Hofuku00_<folder> (YS/SEPH PC0010_Sephiroth, SORA PC0000_00_Sora_KH2).
- rows: pt_Cloud <- pt_Cloud_SEPHIROTH, Cloud's 11 abilities <- _SEPHIROTH (keep UniqueId), 78 damage <- _SEPHIROTH;
  EVIL: pt_Sephiroth <- pt_Sephiroth_EVILCLOUD; BIZ: 9 abilities <- _BIZARRO (keep UniqueId).
- values: Equipment W_TSW_9001 / key_collection_07 back to the game's weapon rows; voice (PlannerEventVoiceList / PlannerEvent
  VoicePack) per character; BIZ: SummonChoice 08-10 Probability 50.0, Item/menu text keys -> _BIZARRO.
- requires_paks: the merged container; YoungSephiroth_P, YoungSephirothVoice_P, ClassicSephirothVoice_P, KH2Sephiroth_P
  (rebuilt), SoraAssets_P, SoraFace_P / SoraFaceRig_P (rebuilt), SoraKH3_Materials_P, Vincent's Chaos / DeathPenalty /
  DirgeMotions / Galian paks, zzVincentGunShop_P (rebuilt); not installed: FPYS's and Vincent's data containers,
  CreateACharacterCloud_P, SoraOverCloud_P, SoraOverCloudMotion_P, SoraVoice_P, VincentVoice_P.
