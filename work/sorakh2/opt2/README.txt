Sora's KH2 moves, version 1 - OPTIONAL, NOT INSTALLED

What it is: in Operator mode (Battle00) Sora's basic attacks and battle stance are his own KH2 animations instead of
Cloud's moves on his body:
  * ground combo:  1st B_NAttack01_0 <- KH2 1301 (lunge, overhead slash)
                   2nd B_NAttack02_0 <- KH2 1302 (lunge, low thrust then upward slash)
                   3rd B_NAttack03_0 <- KH2 1303 (spinning sweep)
                   4th B_NAttack04_0 <- KH2 1319 (lunging horizontal slash)
                   5th B_NAttack05_0 <- KH2 1304 (finisher: leap and slam)
  * air combo:     B_NAttackJ01_0..J03_0 <- KH2 1311, 1312, 1313; air finisher B_NAttackJ04_0 <- KH2 1314
  * battle stance: B_Idle01_1 <- KH2 1015
They play at KH2's speed (the FBX imports say 24 fps; KH2 plays them at 60). Each one has Cloud's gameplay notifies of
the same name (damage, combo and cancel windows, voice, expressions) moved onto the KH2 swing, so damage, combos and
Sora's attack shouts work as before, and the swing sound Cloud's move plays (his weapon bank, as Cloud's moves on Sora
use now) at the hit. Not in this version: weapon trails, Punisher mode (Battle01), abilities, the run.

Made in the End project (nothing existing was changed, only new assets):
  /Game/RebirthSkelCompat/Imported/KH2Sora/KH2_*   all 47 KH2 animations at 60 fps with the game's ACL compression
                                                   (the Battle00 ones use the engine's default codec, which the game
                                                   cannot read)
  /Game/RebirthSkelCompat/SoraKH2/DO_SoraKH2      the data object that builds the moves (Build Move Animations)
  /Game/RebirthSkelCompat/Built/SoraKH2v2/Battle00  the 10 built moves (in SoraKH2Moves_P; Built/SoraKH2 is an
                                                   earlier build without the swing sounds, not used)

To try it (game closed):
  1. copy SoraKH2Moves_P.utoc, SoraKH2Moves_P.ucas and SoraKH2Moves_P.pak into
     End\Content\Paks\~mods\FullyPlayableSoraInRebirth;
  2. replace FullyPlayableSora.skelcompat.json there with the one in this folder (the same file plus "moves");
  3. play a battle: Square combos on the ground and in the air.
To undo: delete the three SoraKH2Moves_P files and put back the JSON from _mod_backups\SoraKH2Moves_before_v1
(the installed one, unchanged).
