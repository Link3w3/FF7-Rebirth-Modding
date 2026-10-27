# Sora's KH2 moves (2026-10-19, unattended; optional pack, not installed)

## What the project had
- /Game/Motion/Player/PC0000_00_Sora_KH2/Battle00/<n> (47): FBX imports (H:/Exported/Projects/KH2Sora/Motion/*.fbx) on
  Sora's skeleton, 244 tracks, 24 fps as the files say. KH2 plays them at 60 fps (as the Sephiroth KH2 form found).
- They use /Engine/Animation/DefaultAnimBoneCompressionSettings (classic per-track codec: 24 more bytes of codec data,
  02 06 06 06 + byte stream / offsets counts), which is why verify_anim left 26 bytes and the game cannot read them
  (RebirthEngineV5 / the game read every animation as AnimBoneCompressionCodec_ACL_0).
- Root convention of the imports: kh_sk rotation (-0.707,0,0,0.707) (R0) and travel on comp +Y. The game's (Cloud's,
  FromCloud's): GAME_ROOT_Q (-0.5,0.5,-0.5,0.5) and travel on comp +X. In root-local terms both are forward = local +Z,
  up = local -Y; the body under the root is the same (Z up, facing +X with the root's rotation left out). Converted
  anyway to exactly the game's convention (tools/make_keys.py: rotation turn*G, travel (y, -x, z)).
- Duplicates in the export: 1301=1359=1361, 1302=1305=1360, 1311=1363=1365, 1308=1312=1315=1364.

## Identification (stick-figure sheets: tools/render_kh2.py, features: tools/features.py)
- 1015 battle idle (loop), 1017/L/R run loop (in place), 0034 landing, 0039/0291 flips, 0040/0042 air poses, 0041 air
  spin, 0055 dash 12.5 m, 1283/1284/1294 air (magic?), 1292 ?
- ground combo 1301 (lunge overhead, hit 0.15), 1302 (lunge thrust + upward, 0.33), 1303 (spin sweep, 0.28),
  1319 (lunging horizontal, 0.16), 1304 (finisher leap + slam, 0.26), 1362 (backstep slash), 1320 (multi-hit, air?)
- air combo 1311 (0.12), 1312 (0.13), 1313 (0.12), finisher 1314 (0.28, 0.69); 1309 air spin; 1366/1367 air moves
- named: AirSpiral (air somersault), DodgeSlash, FinishRise (Finishing Leap: rises 2.7 m), FlashStep (dash 5 m +
  rising slash), MagnetBurst (air 1.5 s), ReflegaCounter, SlapShot, SlideDash (8 m), VicinityBreak (360)

## Pipeline (all new assets in the End project)
1. editor/dump_kh2_raw.py -> raw keys; tools/make_keys.py -> keys/KH2_*.cacanim (60 fps, game root)
2. Import Key Animations -> /Game/RebirthSkelCompat/Imported/KH2Sora/KH2_* (ACL)
3. editor/build_kh2_moves_v2.py: DO_SoraKH2 (/Game/RebirthSkelCompat/SoraKH2), Build Move Animations (no dialog!) ->
   /Game/RebirthSkelCompat/Built/SoraKH2v2/Battle00 (Cloud's notifies on the KH2 hits, Cloud's swing sound per hit)
   (CallInEditor BuildMoves/ExportJson/Validate open a MODAL dialog: never call them through the link.)
4. editor/cook_kh2_moves_v2.py -> split_cooked -> retoc -> build_sora_assets.main(utoc, out, 'SoraKH2Moves_P')
   (verify_anim: 10 anims, 10 ACL blocks)
5. JSON = installed FullyPlayableSora.skelcompat.json + "moves" (Battle00), checked with jsoncheck/check (the DLL's
   own parser, SkelCompatCore.hpp): 0 messages, 48 rows with the 10 moves.
Optional pack: FINAL FANTASY VII REBIRTH/_mod_optional/SoraKH2Moves_v1 (README). Backup of the installed JSON:
_mod_backups/SoraKH2Moves_before_v1.

## v1 as delivered (optional folder SoraKH2Moves_v1, updated in place)
- 11 moves in Built/SoraKH2v2/Battle00: the 9 attacks (each hit with Cloud's swing cue from SE_WE0000_00_BusterSword),
  B_Idle01_1 (1015) and B_Run01_1 (KH2_1017_Run: 1017 + 700 cm/s root travel, tools/make_run.py; Build One Move).
- Built/SoraKH2 (first build, no sounds) is unused.
- Files: SoraKH2Moves_P utoc e943d6e8, ucas 584fb187, pak 797a546e; JSON 092e970f (= installed 5ec3e549 + moves).
