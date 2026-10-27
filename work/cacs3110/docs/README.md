# Create a Character System

Make playable characters for FINAL FANTASY VII REBIRTH (formerly RebirthSkelCompat; folders, files and code
keep that name). At its core, KH3-style skeleton compatibility: meshes on a *receiving skeleton* play the
animations (and AnimBlueprints) of an *animation skeleton*, for any number of skeletons, in any direction.

| Part | Where | What |
|---|---|---|
| UE4SS C++ mod | `src/` -> game `ue4ss\Mods\RebirthSkelCompat\dlls\main.dll` | Adopts animations onto receiving skeletons (`"animations"`), rebinds receiving meshes inside `USkeletalMesh::PostLoad` (`"mesh"`), gathers skeletons that share animations on a hub (`"family"`, 3.0), rebuilds a character's animation sets from other characters' sets (`"animation_sets"`, 3.1), gives each animation pack its own ATB commands, limits and weapon abilities (3.3, 3.4), changes a character's form in battle through the forms menu (`"forms"`, 3.6), late-rebinds meshes that were already loaded, repairs refused AnimBlueprints, F9 report. |
| Editor data object | `C:\FF7R2UProj\Plugins\RebirthSkelCompat` | `Skeleton Compatibility Data Object` (Add New > Animation): Validate, Apply To Skeletons (Asset User Data that cooks with your pak), Export Json. |
| Setup | `setup/` -> `Tools\Share\CreateACharacterSystem-Setup-<version>.exe` | One-click installer for testers: installs the UE4SS mod into the game and the editor plugin into an End project (see below). |

## Setup (one-click installer)

`setup/` builds `CreateACharacterSystem-Setup-<version>.exe`: a small Win32 program (`setup/src/Setup.cpp`) with the
files of both parts appended to it (`setup/tools/make_setup.py`). It finds the game (Steam's registry and
`libraryfolders.vdf`, Epic's manifests, or Browse) and End projects (UE's recent projects, `C:\FF7R2UProj`, two folder
levels of each fixed drive and of the user's folders); checks that UE4SS is build c0a8d4c and that the project's
engine has the plugin's BuildId; refuses a project that already has the plugin in another folder (or in the engine).
It moves every file it replaces into a backup folder first (`<mod>\Backups\<stamp>`,
`<project>\CreateACharacterSystem-Backups\<stamp>`), moves away plugin sources and module DLLs an earlier version
left, never touches compat files, writes `CreateACharacterSystem.install.txt` and a log
(`CreateACharacterSystem-Setup.log` in the mod folder and `%TEMP%`). Uninstall needs that install record, deletes
only files that are unchanged and moves edited ones to the backup folder. Replacing works on a DLL the running game
or editor has loaded (rename, then write). `/S` runs it without a window (`/game:`, `/project:`, `/nogame`,
`/noplugin`, `/uninstall`; a silent uninstall only touches the parts given).

- Stub: `setup/build_stub.sh` (zig 0.17 from PyPI: clang + mingw-w64, x86_64-windows-gnu); the PC copy is
  `Tools\CreateACharacterSystemSetup\Setup.stub.exe`.
- Pack: `Tools\CreateACharacterSystemSetup\run_make_setup.cmd` packs the latest DLL build, `mod\README.txt`,
  `mod\compat\example.json.txt` and `Plugins\RebirthSkelCompat` into `Tools\Share` (warns when a DLL is older
  than its sources).
- Tests: `setup/tests/setup_tests.cpp` (payload, inflate, parsers; Linux) and `setup/tests/wine_test.sh` (installs,
  backups, uninstall, detection and damaged payloads under wine).
- Inflate: `setup/third_party/puff` (Mark Adler, zlib license).

## Families (3.0)

An animation asset belongs to one skeleton, and retail Rebirth compares skeletons by pointer, so two
skeletons cannot both play one animation as is. A family gathers its skeletons on one hub: every
animation of the other members is adopted onto the hub and every mesh of the other members is
rebound to it. `SkelCompat::FinishConfig` (in `src/SkelCompatCore.hpp`) builds families from
`"family"` entries and from `"animations"` pairs that would otherwise fight over the same animations
(reverse pairs, chains, several receivers of one skeleton), and turns each into one `"animations"`
pair plus one `"mesh"` pair per member, so the run-time code only knows those two methods.
A family member's mesh gets a hierarchy fix that passes the engine's test for the hub's
AnimBlueprints and for its own (`SkelCompat::CloseRenamePlan`), and keeps its own skeleton's sockets.
The engine only runs an AnimBlueprint on meshes of the skeleton it targets (`USkeleton::IsCompatible` is a pointer
test in 4.26), so the AnimBlueprints made for a member (`UAnimBlueprintGeneratedClass::TargetSkeleton`) are pointed
at the hub too (3.2.1: PostLoad hook on the class, a pass at every map load, and live components that were refused
are re-initialised).

## Animation set rows (3.1)

A character's CharaSpec pack (`UEndAssetDataAsset`, `/Game/DataAsset/Game/CharaSpec/CharaSpec_<row>`) lists in
`AssetDataList[].AssetUserData` the `UEndAnimSet`s (`DisplayName`, `TMap<FName, UAnimationAsset*> AnimationAssets`)
its character looks animations up in, by set name. An `"animation_sets"` row names the sets' sources:
`"battle"` for `Battle*` sets, `"field"` for the others, each an array of motion folders or single sets, first source
with an animation name wins, plus `"moves"` (one animation, or an array played one after another, under one name). The mod hooks
`UEndAssetDataAsset::PostLoad` (same verified slot as the mesh hook) and, before the engine's PostLoad, replaces or
adds the pack's sets with merged ones: new `UEndAnimSet`s inside the pack, constructed with the first source as
template (every other setting is that set's), whose `AnimationAssets` map the mod writes itself
(`SkelCompat::BuildNameObjectMap`, the layout `TSet` gets from adding the elements one by one). The buckets need
`GetTypeHash(FName)`; UE 4.23+ hashes the name-entry handle (`SkelCompat::NameEntryHash`), and the mod checks
that form against every map it reads (`SkelCompat::ReadNameObjectMap`) before it builds any. The pack's own sets
fill in after the row's sources. Source sets and move animations are loaded at the first map load and rooted.
A row's `"skeleton"` + `"cutscene"` add a family (cutscene skeleton as hub); `"field_actions"` (the CharaSpec
`AnimationSetParentFolder`) is recorded for the editor data object, which writes CharaSpec values.

## Auto match, chains, limit breaks, sockets, proportions (3.2)

- **Auto match** (`SkelCompat::MergeSetSources`, `SkelCompat::AutoMatch`): a source with `"auto"` fills the attack
  names the row's ordinary sources ask for: same name, else another variant of the same move (lead, body and number
  equal, closest suffix), else an attack of the same kind (ground / air) by closest length, each used once before any
  is used again. Split moves (pieces under 0.6 s) are offered whole and played as a runtime `UAnimComposite`
  (`FAnimSegment` fields found by reflection, `bValid` right after `bTriggerAnimReferenceNotify`). `"only"`
  restricts every pick of that source to names containing one of the words.
- **Chained moves / limit breaks**: `"animation": [...]` on a move, `"limit_breaks": [...]` (limit *n* =
  `B_AtkLimit0n_0`); built as composites outered to the pack, rooted.
- **Socket stand-ins** (`"sockets"`): new `USkeletalMeshSocket`s in the mesh's `Sockets` before the engine's
  `PostLoad` builds the socket map (mesh sockets win over skeleton sockets there).
- **Proportions** (`"proportions"`): `BoneTree[i].TranslationRetargetingMode` on the hub (body chains Skeleton,
  pelvis AnimationScaled), a retarget pose per member in `USkeleton::AnimRetargetSources` (native map, read with
  `SkelCompat::ReadNameKeyedMap`, rebuilt with `SkelCompat::BuildNameKeyedMap`), and `RetargetSource` set on every
  adopted sequence. Applied at safe points only (map load, after the world tick). Rebirth keeps 0x30 bytes of its
  own between `AnimRetargetSources` and `SmartNames`, so the map is placed right after `Sockets` and every skeleton's
  map header is read back (`SkelCompat::ReadNameKeyedMap`) before the pelvis is set to AnimationScaled (3.2.2; 3.2.1
  left the pelvis as animated).
- **Proportions in cutscenes** (3.6.7): Rebirth's cutscene animations have `bIgnoreTranslationRetargeting` set (a
  `UAnimSequence` bool of Rebirth's, right after `RetargetSource`), so they played their own bone lengths whatever the
  hub's modes: a body of the family took the animation's build and height in cutscenes. The mod clears it (the
  property's byte and mask found by reflection) on every sequence it adopts into a family with `"proportions"` and on
  the hub's own sequences as they load, so every body keeps its build there as in gameplay. A top-level
  `"cutscene_proportions": false` (any compat file) leaves the flag as the game has it. The log says the offset
  (`AnimSequence.bIgnoreTranslationRetargeting`), the first cleared sequences and the count in the report.
- **Override rows** (`"override": true`) are joined before the character's other rows.

## Editor 1.5: Build Moves

A move with **Build** on is made in the editor from an animation of the project (an imported or retargeted one,
e.g. Vincent's DoC moves): a new Anim Sequence `<Build Folder>/<Set>/<Name>` on the same skeleton gets its keys,
curves, notifies and settings (`UAnimSequence::CreateAnimation(Source)` plus the settings it leaves out). Since
editor 1.5.1 it is not duplicated (1.5.0 was, and crashed): RebirthEngineV5's `UAnimSequence::Serialize` writes the
game's memory-mapped layout, and `FCompressedAnimSequence::SerializeCompressedData` writes a bulk-data flag there that
it does not read back, so an in-memory copy reads past the sequence (`FDuplicateDataReader Overread`). For the same
reason the built sequence is kept out of the undo history. Then the notifies of the
character's own animation of that name (found in the row's folder sources from the last one up, or **Notifies From**)
are duplicated onto it, except the original motion's own sounds, effects and cloth settings. Times are mapped
piecewise around the first hit (`EndAnimNotify*BattleDamage`): it lands at **Hit At** (or in proportion), the rest
scales before and after it; damage windows keep their length. With **Shot**, every hit also gets the row's
**Shot Effects**: an `AnimNotifyState_EndTimedNiagaraEffect` (`m_Template` is a soft path, attach type `WeaponN`, the
weapon socket, as the game's own muzzle notifies set them) and an `EndAnimNotifyPlayWeaponSound` (`SoundRef` + cue).
Root motion and the `OverrideBehaviorAction*` blend settings come from the original. The build folder gets a
`UPrimaryAssetLabel` (Label Assets In My Directory, Chunk ID = **Build Chunk**, 46 by default) so packaging puts the
built animations in that pakchunk. Export Json points such moves at the built animation and keeps
`"build": {...}` (and the row's `build_folder` / `shot_effects`) for Import From Game Json; the mod skips those keys.
The label covers only the built animations (`bApplyRecursively` off): the skeleton and compression settings they use
stay out of the mod's chunk, since the game or another pak has them. A Build Folder inside Project Settings > Packaging >
Directories To Never Cook is refused (Build Moves and Validate say so): it would never be packaged (editor 1.5.2).
Import From Game Json keeps a row's own moves and Build Folder when the file's differ, and now lists them.
Built moves always get the game's compression settings, `/Game/Animation/CompressionSettings/AnimBoneCompressionSettingsACL`
and `AnimCurveCompressionSettingsACL` (not the source animation's): RebirthEngineV5's loader always decompresses a
memory-mapped animation with `AnimBoneCompressionCodec_ACL_0` and the ACL curve codec. (The game's own loader also reads
Unreal's own codecs: a few retail animations use them, e.g. Sephiroth's `B_Run01_0_R90`, and those copies fail to load in
this editor with "Invalid boolean", which fails a cook that loads them.) Build Moves compresses each move right away
and reports an error if any other codec was picked (editor 1.5.3).
**Import File** lets Import From Game Json read any compat JSON, and the import now also adds the file's pairs and
families the data object does not have.

## Editor 1.6: Weapon swaps

A weapon's CharaSpec pack (`CharaSpec_WE0000_00_Cloud_BusterSword`, `UEndAssetDataAsset`) names the blueprint that spawns
(`AssetClassList`) and what loads with it (`AssetDataList`: effect pack, sound bank); its CharaSpec row names the model
(`ContentsModel`) and lists the same effects and sounds (`ContentsEffect`, `ContentsSoundSE`, `ContentsSoundAutoSE`).
Swap paks that change only the packs (FullyPlayableVincentAssets: Cloud's swords spawn Vincent's gun) leave the rows
describing the old weapon, and every cutscene whose ID table names that weapon (`EV_*_IDTable`, `PachiCharaName`
Cloud_Weapon, `PachiCharaSpec` WE0000_00_Cloud_BusterSword) then never starts: the cut level is never streamed in. Rows
that describe the gun (as SephirothOverCloud's rows describe its Masamune: the new weapon's model, the new weapon in
`SharedCharaSpecList`, the pack's own effects and sounds) make them play (tested on Gongaga, chapter 9). It is the
weapon form of the character rule found earlier: a character's blueprint on another character's model keeps the game on
its loading screen.

`WeaponSwaps` (`FEndWeaponSwap`: Weapons, with `WE0000_*` standing for every row with that prefix; New Weapon; Cutscene
Family; Weapon Skeleton / New Weapon Skeleton; Requires Paks):
- **Apply To CharaSpec** (and **Apply To Skeletons**, which now also does Apply To CharaSpec when there is CharaSpec work)
  writes each replaced row through `SetDataObjectRowField`. What the pack loads comes from its package dependencies in the
  asset registry (`/Game/BluePrint/Character/...` = the spawned blueprint, `*_Effect__Pack`, `SE_*`, `AS_*` banks), so
  the game assets it names need not be in the project. A row whose pack is not in the project, or still spawns another
  blueprint, is never changed (that would make the same mismatch the other way round); a row matched only through `*`
  whose pack is the game's own is left out.
- **Export Json** adds a weapon family per swap: hub = the new weapon's skeleton, member = the replaced weapon's
  (by default the skeletons in the model folders, `/Game/Character/Weapon/<model>/Model/<id>_Skeleton`; every one of
  Cloud's weapons is on `WE0000_00_Skeleton`), with `"from_weapon_swap"` so Import From Game Json does not turn it into a
  pair, and the swaps themselves under `"weapon_swaps"` (the mod skips that key). In game the sword's cutscene animations
  are adopted onto the gun's skeleton and the gun keeps its own animated parts.
- **Validate** shows per replaced row what its pack spawns and loads and what Apply would write, and the family; for
  animation set rows it now also flags a character pack in the project whose blueprint is not the row's model.


## Editor 1.7: Character swaps

`CharacterSwaps` (`FEndCharacterSwap`: Characters (rows, `PC0010_*` for every row with that prefix), New Character,
Moveset, Voice, Weapon Socket, Replaced Skeleton / New Skeleton, Requires Paks) put another character in some rows' place,
the way the CloudOverSephiroth test pak did it by hand:
- **Apply To CharaSpec**, with **Apply To Packs** on (default), first edits each replaced row's pack in the project
  (`UEndAssetDataAsset` through reflection: `AssetClassList[].AssetUserData`, `AssetDataList[].AssetUserData`): a pack that
  spawns none of the new character's blueprints (names starting with his id, `PC0000_`) gets his
  (`/Game/BluePrint/Character/<kind>/<row>.<row>_C`), and with a **Voice** (`VO_PC0000_02_Cloud_Insanity`) its voice bank and
  lip sync (`LSD_...`) are replaced. Game assets the project does not have come from `RebirthGameObjectLibrary` in the Rebirth
  Cooked Asset Preview plugin (`GetGameObject`, `FindGamePackages`): this project's copy, else an in-memory stand-in of
  `RebirthGameReferences::FindOrStandIn` (never saved or cooked; the reference resolves to the game's asset in game). The
  packs are saved, then each row is made to describe what its pack spawns and loads (as planned from the edited pack):
  `ContentsModel` (the spawned blueprint's name), `ContentSoundVoice_Array` (and the story-flag voice packs
  `SoundVoisePack_Array` / `SoundVoisePackEnableStoryFlag_Array` cleared when they are the old character's), effects, SE and
  AS banks, `End2AIList_Array`, his spec added to `SharedCharaSpecList_Array` (his own row while it still describes him,
  else his `_Reserve` row: SephirothOverCloud changes Cloud's own), **Weapon Socket** in `OverrideWeaponSocketNames_Array`
  slot 0 (`Attach_Weapon_Left01` for Sephiroth's left-handed swings), and with **Moveset** "New character's own" his
  `AnimationSetParentFolder` (and `OverrideAnimationSetString_Array` cleared, its sets are the old folder's). A row whose pack
  could not be edited is left alone; a shared list that would make specs load each other in a loop is not written.
- **Export Json** adds a family (hub: the skeleton of the moves played, by default the model folders'
  `/Game/Character/Player/<model>/Model/<id>_Skeleton`) and one animation set row per group of swapped rows with the same
  motion folders (what their packs list): `battle` and `field` = the moveset's folders first, then the other character's,
  so the first one with an animation name wins. Both carry `"from_character_swap"` (Import From Game Json skips them, the
  data object makes them again); the swaps go under `"character_swaps"`.
- **Weapon swaps** now also edit their packs (the new weapon's blueprint, and its effect pack `<row>_Effect__Pack` in place
  of the old ones) and have **Sockets**: socket stand-ins exported as a row with `"skeleton"` = the new weapon's skeleton
  (e.g. NAttack1..4 / NAttackBoss of the Masamune on the Buster Sword's `C_TrailA_a`, `C_TrailA_b`, `SAttack_Zack`,
  `ChainCharge_Sephiroth`, without which Sephiroth's moves with the Buster Sword do no damage). Validate lists the old
  weapon's sockets the new one lacks when both skeletons are in the project.
- **Validate** shows the plan per row (pack edits, field changes), what Export Json adds, rows left out (packs that are the
  game's own: make them editable to swap them too), shared-spec loops, and with **Fix Pack Models** every pack of the
  project that disagrees with its row; Apply To CharaSpec gives such a row the model of the blueprint its pack spawns.
- **Keep Proportions** (1.7.1, on by default): the swap's family gets `"proportions": true`, so the new character keeps
  his own height and bone lengths while he plays the replaced character's moves (Cloud does not grow to Sephiroth's
  height), and the other way round. The mod applies it to the whole family the entry ends up in (3.2 proportions).

### Custom models in a swap (by hand, 2026-10-13)

A character the game has no blueprint for (the user's Evil Cloud: `PC0000_10_Evil_Cloud/Model/PC0000_10` and
`PC0000_11_EvilCloud_Transformed/Model/PC0000_11`, both on `PC0000_10_Skeleton` = Cloud's bones + Sephiroth's) needs a
blueprint named like its model folder, since `ContentsModel` names the blueprint the pack spawns
(`/Game/BluePrint/Character/Player/<ContentsModel>`; 32 retail Player rows name a model folder that does not exist,
none a missing blueprint). The blueprints were made from Cloud's cooked one (Zen copy: package, class and default object
renamed, public export indices recomputed, the mesh import and its graph package pointed at the custom mesh), merged
with the cooked models into `FullyPlayableSephirothDataAssets_P`; Sephiroth's packs spawn them and his rows name them.
The custom skeleton joins the Sephiroth family in `PlayableSephiroth_Swap.json`, with `"proportions": true`.

## Editor 1.8: Move Maker

**Window > Rebirth Move Maker** (or **Open Move Maker** on a data object, under Animation Sets) opens a tab that makes one
move at a time: pick the **Data Object** and the **Character** (one of its animation set rows), what **Slot** lists
(**Show**: Attacks, Abilities, Limit Breaks or Everything: the animation names of the character's battle sets in this
project, with their lengths, plus the row's own moves; **New Name** for a name the sets do not have) and the
**Animation** to make it from. Picking a slot loads the row's move of that name. **Open Animation** opens it in the
animation editor: stop the playhead on each strike and press **Add Hit At Playhead**. **Save Move** puts the form in the
row's Moves with Build on; **Build** saves it and builds that move only (`BuildOneMove`), then saves the data object with
the built animation. **Open Built Move** shows the result; About and the report under the buttons say what the move is
made from, where its gameplay notifies come from and what the build did.

- **Any animation** (another character's, one of the game's, an imported one): a move whose animation is on another
  skeleton, or has no keys in this project (a cooked game animation), is sampled frame by frame onto the row's
  **Character Skeleton** (`GetBoneTransform` from the keys, or from the compressed data with the game's ACL codec).
  Rotations are taken as they are (Square Enix bodies share bone names and axes); translations follow **Retarget**:
  *Keep the character's build* uses the mod's proportions rules (`SkelCompat::ProportionModes`: body chain = the
  character's bone lengths, pelvis scaled to its height, every other bone moved from its own rest pose as the animation
  moves it), *Animation's own bone lengths* keeps them all. Bones the character lacks are left out; curves carry over by
  name where its skeleton has the name (none is added: the skeleton is the game's). **Keep Source Effects** keeps the
  animation's own sounds and effects (swings, trails) on a "Source" track. An animation of this project on the character's
  own skeleton is still made with `CreateAnimation` as in 1.5.
- **Hits** (`FEndMoveHit`, per hit): Time (seconds of Animation), Window (a damage window's length; 0 = as copied),
  Damage Source ID, Effect (a Niagara system, soft path) with Effect Socket on the weapon or the character and Effect
  Time, Sound Bank + Sound, Weapon. The damage notifies of the move the notifies come from are grouped into hits (less than
  0.05 s apart = one hit) and the n-th group lands at the n-th time; the rest of its notifies follow a piecewise time map
  through those anchors. More hits than it has repeat its last hit; fewer leave its last ones out. A Damage Source ID
  replaces the copied notify's (`DamageSourceID`, `DamageSourceIDs` cleared). With nothing to copy from (no Notifies From
  and no move of that name), each hit with a Damage Source ID gets a new `EndAnimNotifyBattleDamage` with the game's
  defaults (check its Create Position settings). The hits' effects and sounds go on a "Hits" track as
  `AnimNotifyState_EndTimedNiagaraEffect` (attach `WeaponN` or `Character`) and `EndAnimNotifyPlayWeaponSound` /
  `EndAnimNotifyPlayCharacterSound`. No Hits: Hit At as in 1.5.
- **Abilities and limit breaks** are built like attacks, under their own names (`B_Ability01_0`, `B_AtkLimit01_0`); for
  one the character has no animation of, set **Notifies From** to a move of his that hits the way it should, or give each
  hit a Damage Source ID.
- The data object's **Build Moves** builds the same way. Export Json keeps the new settings under the move's `"build"`:
  `"hits"` (time, window, damage, effect, socket, on, effect_time, sound_bank, sound, weapon), `"retarget": "as_is"` and
  `"source_effects": false` (only when not the default); Import From Game Json reads them back. The mod skips `"build"`.
- Validate's build lines now say how each move is made (put on which skeleton, sampled from a game animation), its hits
  and their effects, and whether the hits name damage when there is nothing to copy it from.

## Abilities per pack (3.3, 3.4), every set switchable (3.5)

A row's `"abilities"` give each animation pack (`Battle02`, ... switched with EndBattleAPI `SetPrimaryAnimPack`) its own
ATB commands and limit breaks (`"player"`: the BattlePlayerParameter row, `pt_Cloud` for Cloud's slot), through the
game's own list getters (their read-only table slots point at the mod's getters, which answer for switched rows only);
after a switch the mod has the game recalculate the character's status (`BPSetPlayerExperience` with the EXP it has,
checked afterwards). 3.4 `"weapon_abilities"` switch the abilities equipped weapons give (the game's lookups of a
weapon's Equipment row, found by their code, go through the mod's). 3.5 makes every set of a pack switchable: the game
takes sets only from some slots of a CharaSpec row's `AnimationSetList`, so its calls of the set lookup go through the
mod's, which gives the pack's own set when the game took none of that name. 3.5.3 adds the Lua pump: the Lua mods it
names get their `RebirthSkelCompatPump` called every frame on the game thread (UE4SS 3.0.1's `ExecuteInGameThread` is
neither safe nor always on the game thread); `RebirthSkelCompatIsGameThread()` tells any Lua mod where it runs.
`pack_assets` (3.3.1) put another character's effect pack into a character's CharaSpec pack, so the damage sources of
borrowed abilities find their effects.

## Editor 1.9 - 1.10

- **1.9**: the data object's rows list each pack's commands, limits and weapon abilities (Export Json / Import From Game
  Json, Validate).
- **1.10 Import Key Animations** (`ImportKeyAnimations`): Anim Sequences on a skeleton from `.cacanim` key files (each
  bone's local keys per frame, in Unreal's axes), with the game's ACL compression settings, so Build Moves can make moves
  from another game's animations (the KH2 Sephiroth set).
- **1.10.1**: Import Key Animations, Build Moves and Make Chain Assets put an earlier asset out of the way without loading
  or force-deleting it (RebirthEngineV5's `UAnimSequence::Serialize` runs its loading half for every archive that does not
  save, so a reference-finding archive emptied the compressed bytes of every Anim Sequence in memory), compress each Anim
  Sequence anew right before saving and check each saved file.
- **1.10.2 Describe Animations** (`DescribeAnimations`): an animation's or a pack's lengths, frames, root motion and
  notifies (whether Build Moves counts each as a hit or as the motion's own sound or effect) as JSON, for planning moves.
- **1.10.3**: a game animation stored as ACL Quat_128 (whole quaternions) is reported as not built instead of stopping
  the editor in the ACL plugin.

## Forms (3.6 - 3.6.14) and editor 1.11

A row's `"forms"` (up to 13, the normal one first) are what the character changes into in battle. Hold the row's
button (Triangle; a tap stays the game's) and the **forms menu** opens: a command window in the game's own menu art
(the Paper2D sprites of `/Game/Menu/Resident/Texture`, drawn with UMG widgets the mod builds), 7 forms at a time, the
list scrolling; up and down on the stick, the D-pad or the arrow keys, let go to switch. A form plays its animation pack
(`SetPrimaryAnimPack`; the normal form `ResetPrimaryAnimPack`), so its moves and its pack's `"abilities"` come with it,
and changes what goes with it:

| Key | What |
|---|---|
| `pack`, `name` | its animation pack (in the character's CharaSpec `AnimationSetList`) and its name on the menu |
| `show` | material slots of the model (the forms' `"parts"`) shown in this form; the others are hidden (with `fade_seconds`) |
| `model`, `anim_class`, `scale`, `meshes` | another model, with its AnimBlueprint (a model on another skeleton), size and added parts |
| `hide_weapon` | the weapons are hidden |
| `effects`, `keep_effects`, `sounds` | Niagara or Cascade effects (socket, scale, seconds) and sound bank cues (`{language}` voice banks) as it switches; effects kept while it lasts |
| `ability_effects` | effects while some abilities run in the form (`"PC0010_NAtk_*"` patterns): a conjured sword in sword attacks |
| `fly` | real flying, hovering above where it started (height, speed, max, up / down keys) |
| `after` | switches to this form by itself when that ability ends (a transforming limit break) |
| `super_armor` | hits do not make it flinch or stagger (EndBattleAPI `SetDisableReaction`, set again every second) |
| `seconds`, `cooldown`, `revert_to` | a time limit (game time, `GameplayStatics.GetTimeSeconds`; the time left on screen at `timer_at`, orange in the last 10 s; it turns back once the ability it runs ends, 8 s more at most), then a cooldown before it can be chosen again (the menu shows `ready in 0:25`), and the form it turns back into |
| `entrance` | (3.6.6) played as the character in charge switches to it: its animation over everything else, a white flash, a descent from above, effects and a cinematic camera (below); (3.6.7) or a cutscene's shots, some before the switch |

Knocked out in a form with super armor or a time limit, the character loses the armor and its time stops; back on its
feet, it turns back. A pack switch made by anything else (a Lua mod, the game) changes the form too, and every character
is back in its normal form when the battle ends. `RebirthSkelCompatHasForms()` tells a Lua mod that the mod changes
forms. Everything runs on the game thread from the frame work (actor ticks and ProcessEvent: this game's UE4SS calls no
viewport tick).

3.6.1:

- **A form's AnimBlueprint no longer crashes the game.** EndGame gives a character a C++ animation controller (at
  character + 0x1420, not reflected) when it is made, and the controller sets up the anim instance the mesh has then
  (its weak +0x160, the instance's +0xCC0 back to it, the instance's set-up flag +0xCA5 and its rotation updater at
  +0x1088 with the instance as owner). `SetAnimClass`, or a model on another skeleton, gives the mesh a new
  `UEndCharacterAnimInstance` that nothing sets up, and the game's rotation update (anim vtable slot 103) read the
  updater's empty owner a few frames later. The mod now finds the controller before a model change (the one of this
  mesh, holding the instance the mesh has, its slot 1 the start that calls slots 3, 4 and 5) and after it calls the
  controller's slot 3, the game's own attach step, under an SEH guard; it checks the controller took the new instance.
  A character whose controller is not found that way keeps its own model in the form.
- The forms menu's words and the time left were blank: `TextBlock.SetText` takes a `TextProperty`, now passed as one
  (`Arg::Tx`).
- Voice banks with `{language}` that the game does not load itself (a cutscene's line) are loaded in the game's voice
  language (the language folder of a party member's loaded voice bank) and kept, when a character with forms is first
  tracked or the menu opens (taken out again in 3.6.3).

3.6.2:

- **Moves after a model change.** A character's animation sets (its CharaSpec's, and each pack a switch puts on) are
  layers the game registers into the anim instance (its set container at +0x12D0: the instance at +0x28, the layers at
  +0x230, 32 bytes each; a layer keeps what it was made from at +0x2B8: `{ FName, TArray<8 bytes>, int32, uint8,
  FWeakObjectPtr set }`). A new instance had only its AnimBlueprint's resident blends, so every move fell back to one
  pose. Before the change the mod copies the old instance's layers that came from a set, and after it registers them
  into the new one with the game's own layer registration (found by its code: the function the pack switch calls with
  the controller), in their order. The controller is now started with its slot 1 (attach, then its bone indices of the
  mesh: slots 4 and 5), not slot 3 alone.
- **The mesh tick.** A character's tick at +0xF40 reads bone tables built from its mesh (+0xCC the component, +0xD4 the
  asset they were built from, +0xDC what it runs for, +0xE4 / +0xEC a re-build asked for). After Bizarro's mesh it read
  Bizarro's bone indices on Sephiroth's mesh (a crash 90 s later). After a model change the mod stops a tick whose tables
  are of another mesh (unless a re-build is asked for), and back on the character's own model asks for a re-build with
  what it ran for before.
- Voice lines: every voice language is tried (the game's first), and a cutscene's line also through the cutscene's voice
  packs; at the first map load and once more in battle. The log says what loaded. (Taken out in 3.6.3: it crashed.)

3.6.3:

- **No more crash half a minute into the game** (`Crash in runnable thread FAsyncLoadingThread`, an access violation
  writing in the loader's archive reader). The crash dump has the game thread in the mod's `LoadAsset_Blocking` of
  Sephiroth's voice bank (`Track` -> `PreloadVoices` -> `VoiceBank` -> `Need(path, true)`), from the frame work, while
  the loading thread died serializing it. Voice banks are localized packages (the US one names the JP one as its
  source) that the game's sound system loads; the mod no longer loads any (not at map load, not in battle, not through
  a cutscene's voice packs). A `{language}` line plays while the game has its bank loaded (any language folder, the
  bank fully loaded), else the log says `Forms: voice line ... left out` once a session.

3.6.4:

- **Kept anim instances.** 3.6.1 - 3.6.3 let the engine make a new anim instance at each model change; the controller
  took it, but moves did not play on it, the character's own AnimBlueprint included once it was back. At spawn the game
  does more than the attach: the controller is made by `+e1ef4c`, which then copies two lists from the instance
  (`+0xB08`, `+0xB18`, 16-byte entries) into the character (`+0x1488`, `+0x1498`, once: `+0x1480`), and every set put on
  the character (its set map at `+0x11B8`, `TMap<uint8, TArray<0x1C-byte entry>>`) is registered into the instance by
  the call the pack switch makes after adding the entry (`+0xB9` in the pack switch, the anim set interface's slot 2),
  followed by a pose change (`+0x10C7`, `+0x10C8`). Now a model change keeps the instance on the mesh (rooted; let go
  before a map load), clears the mesh with `SetAnimClass(None)` (the engine waits for the mesh's animation work) and puts
  back a kept instance of the form's AnimBlueprint (`AnimClass` and `AnimScriptInstance` written, then
  `SetSkeletalMesh(model, false)`: `InitAnim` keeps an instance of the right class and skeleton), the controller bound
  to it again without the set-up it ran when the instance was made (its attach's first step, `+0x160` / `+0xCC0`, its
  last step, slots 4 and 5). A form's instance made the first time gets the controller's start, then every set of the
  character through the game's registration (the form's pack last) and the pose change; either way the two lists are
  copied again from the instance now on. Linked anim instances of a kept instance are taken out of the mesh's
  `LinkedInstances` while it is off. Leaving a form's model, the own instance goes back on before the pack switch.
- **The mesh tick** (`+0xF40`) is asked to build its bone tables for the mesh now on (its re-build pair `+0xE4` /
  `+0xEC`, which its work handles before the `+0xDC` gate), with the instance now on when it ran for the character's own;
  3.6.2 stopped it while another mesh was on, and nothing started it again after the switch back.
- The log lists the layers of the instance before and after each change, what of the character and its controller
  refers to the instance the game made, and, in another model, the montage the anim instance plays 0.4 s into each
  ability.

3.6.5:

- **A form's model goes on as one of the game's looks** (the Toad status's way), when it has an AnimBlueprint of its own
  (another than the character's) and the character is an `EndChangeAppearanceCharacter` (every playable one). Its look
  list `ChangeAppearanceSettings` (`FEndChangeAppearanceSetting`, 0x68 bytes: mesh, material pack, AnimBlueprint, anim
  sets, body control rig, two SE banks, effect pack, `RootCapsuleSize`, `bDisableChangeCapsuleSize`, hit-body shapes;
  the frog is entry 0), the kept look `AppearanceResetSetting` and two unreflected indexes (the look asked for, the look
  on, -1 the character's own) drive it: the frog's status stops the controller's moves (its first step), asks for its
  look and runs the apply, which keeps the character's own look (and hit body) when its own is on, then
  `SetAnimClass(None)`, the mesh, the material pack, the look's AnimBlueprint and, the mesh being another, **destroys the
  character's animation controller and makes a new one** for the new instance (`+e1dccc`, then the character's
  `vfunc 0x8A0`: the controller's making, start and bindings), sets the mesh tick up for the mesh (`+bfc4d8`) and puts the
  look's hit body on (`EndBodyCollisionPrimitive`s on the mesh). -1 puts the kept look back the same way. 3.6.1 - 3.6.4
  kept the controller the game made for the old instance, and moves did not play through it.
- The mod's entry is **just past the list's count**: while a look of the list is on the game treats the character as a
  toad (the camera takes the `"Toad"` setting, sync actions the frog's damage source, a party check for a toad), so it is
  counted only while the game puts it on (the controller is then made as for any look: no body control rig or facial
  set-up of the character's own skeleton) and not again (the change waited for the mesh's animation work). The entry:
  the model, its AnimBlueprint, no material pack (the mesh's own materials), the capsule the character has
  (`bDisableChangeCapsuleSize`: no capsule change). The look's hit body (one capsule, on the mesh) gets an absolute scale
  and the middle of the character's capsule, so a model made smaller (`"scale"`) does not make it smaller. The new
  instance is given the character's sets (as 3.6.4 gave them: the game's registration), when the game left it without
  layers. Found once: reflection (the list, the look's fields, where the game's code reads them), then
  `RequestChangeAppearance`'s exec -> its C++ -> the apply -> its work (each checked by its code and against the
  reflection), and the moves' stop from `RequestChangeAppearance_ForceFinishAbility`'s C++.
- A look of the game's (a status) put on over the form's: the game keeps the form's look as the character's own then;
  the mod puts the kept look (and kept hit body) back as it was when the form's went on, so the game puts the
  character's own back as the status ends, and the form's goes on again then. The parts' fade materials of the mesh are
  forgotten at each look change (the look's material pack replaces the mesh's materials).

3.6.6:

- **A form's entrance** (`"entrance"`), played as the character in charge switches to the form (with its switch
  effects: not as the battle ends or when another mod switches it):

  ```json
  "entrance": { "animation": "/Game/RebirthSkelCompat/Built/SephirothForms/Battle06/B_SaferEnter01", "slot": "DefaultSlot",
                "rate": 1, "seconds": 0, "flash": 1.5, "flash_color": [1, 1, 1], "descend": 1200, "descend_seconds": 5.5,
                "effects": [ { "effect": "/Game/Effect/...", "socket": "C_Spine_c", "scale": 2.5 } ],
                "camera": { "face": "C_Nose_A", "distance": 900, "side": 150, "height": 40, "fov": 70, "close_at": 0.65,
                            "close": 180, "close_fov": 30, "hold": 0.6, "blend_back": 1, "bars": 2.39 },
                "hold_input": true, "skip": true, "invincible": true }
  ```

  `animation` plays as a slot montage of the form's AnimBlueprint (`PlaySlotAnimationAsDynamicMontage` in `slot`, once
  the form's anim instance runs; the shot lasts its length at `rate`, or `seconds`). `flash`: the screen starts white
  (`flash_color`) and fades back in that many seconds (`PlayerCameraManager.StartCameraFade`), hiding the model change.
  `descend`: the model starts that many cm up and comes down in `descend_seconds` (70% of the shot when 0), easing in and
  out: its mesh is raised under its capsule (`K2_SetRelativeLocation`; the first raise a teleport, so the hair and
  feathers start up there), so nothing of the game's movement changes. `effects` play on the model for the whole shot
  (an effect's own `seconds` win). `camera` (or `false`): a `CameraActor` the mod spawns and makes the view target at
  once (`SetViewTargetWithBlend`, under the flash): `distance` in front of the character, `side` to its right, `height`
  above the ground, looking up at the `face` bone (followed smoothly), moving in a little while it comes down; from
  `close_at` of the shot it moves in to `close` cm in front of the face while the field of view goes from `fov` to
  `close_fov`, stays there `hold` seconds, then blends back to the view target the game had in `blend_back` seconds
  (ease in and out). `bars`: the picture's shape while it is on (2.39: cinema bars; `false` or 0: the screen's).
  `hold_input`: the sticks do nothing meanwhile (`SetIgnoreMoveInput` / `SetIgnoreLookInput`; the buttons still work).
  `skip`: an ability the character starts (an attack, a command) ends it early: its animation stops, the camera blends
  back in 0.5 s, the model comes down in 0.35 s. `invincible`: the character takes no damage while it plays (EndBattleAPI
  `SetDisableDamageHit`, as the Meteor cinematic does it). Another form, another character in charge or the battle's end cut it
  (0.3 s); the game taking the view back leaves the rest playing. The log says what played, whether the game shows the
  mod's camera (the camera manager's view 0.3 s in) and how it ended. `"entrance": true` is the flash and the camera.

3.6.7:

- **An entrance of shots** (`"entrance": { "shots": [...] }`): a cutscene's own shots, one after another, each with its
  camera keys, animation, effects and sounds; the shots marked `before_switch` play first, on the model the character
  has, and the switch to the form comes when they are over (its switch effects and sounds then):

  ```json
  "entrance": { "shots": [
      { "name": "C0130", "seconds": 7.1, "before_switch": true,
        "animation": "/Game/Cut/Game/8800-FOREE/EV_FOREE_8630/Motion/EV_FOREE_8630_PC0010_10_C0130.EV_FOREE_8630_PC0010_10_C0130",
        "animation_start": 5.433, "rate": 1, "scale": 1, "flash": 0, "flash_color": [1, 1, 1],
        "camera": [ [0, -55.26, 108.93, 187.14, -21.202, -48.223, -3.863, 46.218], ... ],
        "effects": [ { "effect": "/Game/Effect/Cut/...", "at": 5.433, "seconds": 1.667, "offset": [-0.2, 0.1, 88.1], "yaw": 0, "scale": 1 } ],
        "sounds": [ { "voice": "/Game/Sound/Voice/{language}/Cut/.../C3510_MAIN_3400_0400_00_sep.C3510_MAIN_3400_0400_00_sep",
                      "cue": "C3510_MAIN_3400_0400_00_sep", "at": 1.133 },
                    { "bank": "/Game/Sound/SE/Cut/...", "cue": "EV_FOREE_8630_0465f", "at": 0, "start": 14.1, "stop_at_end": true } ] },
      { "name": "C0160", "seconds": 8.7, "scale": 1, "flash": 1.2, ... } ],
    "camera": { "hold": 0.2, "blend_back": 1.2, "bars": 0 }, "hold_input": true, "skip": true, "invincible": true }
  ```

  A shot's `camera` keys are `[t, forward, right, up, pitch, yaw, roll, fov]` (seconds into the shot; cm and degrees
  relative to where the model stands, its mesh component's place, turned with the character), followed in a straight
  line from one to the next; the offsets are for a character of the shot's `scale` and are scaled by the model's size in
  the world (Bizarro's 0.1 model gets a full-size cutscene's camera at 0.1). `animation` plays in the entrance's `slot`
  from `animation_start` (`PlaySlotAnimationAsDynamicMontage`'s start time), after the switch once the form's
  AnimBlueprint runs (1.5 s at most). `effects`: at `at` seconds into the shot, on a `socket` or placed at `offset`
  `[forward, right, up]` from the model, turned `yaw` (`SpawnSystemAtLocation` / `SpawnEmitterAtLocation`), for
  `seconds` (to the shot's end when 0). `sounds`: a `bank` or `voice` ({language}) cue at `at`, from `start` seconds into
  it (SEAD `StartTime`; also as late as the shot is); `stop_at_end` stops it when the shot ends. `flash`: the screen white
  as the shot starts, fading back in that many seconds. The first shots are left out (the switch happens at once and the
  entrance starts after them) when their animation is not for the model's skeleton (the form it comes from has another
  model) or not loaded. A skip (an ability) during them, or another character taking charge, still makes the switch,
  without the rest; another form chosen meanwhile cuts it. The mod preloads the shots' animations, effects and sound
  banks (not `{language}` voice banks). The log says each shot as it starts, where the model stands (`its model stands X
  cm below the character's middle, size S`) and whether its animation played.
- **Bizarro's entrance from his transformation cutscene** (EV_FOREE_8630, in SephirothForms.json): from NORMAL, WINGED,
  FLYING or KH2 (Sephiroth's model), the end of cut C0130: Sephiroth's close-up with the cutscene's camera and
  animation as he says "Alone at last. Shall we?", the darkness taking him (`FX_EV_FOREE_8630_Transform_01`) and the
  cutscene's sound; a white flash and the switch; then cut C0160 to 51.4 s: Bizarro revealed, the camera rising along
  him, his cutscene animation, the sphere and the shockwave as he appears (`Transform_02`,
  `Transform_Shockwave_01`), his aura (`Transform_03`), the sound from there (about 16 s; any ability skips it). From
  SAFER (another model) only the second shot plays. The line plays from the cutscene's voice: the data pak
  (FullyPlayableSephirothDataAssets_P) has Cloud's slot's CharaSpec packs load it with the character (imported by its
  JP path and in their graph in every voice language, as the game's own packs have their voices, so the game loads the
  voice language's), and the mod finds it loaded; the line is no longer one of BIZARRO's switch sounds.
- **Proportions in cutscenes** (see 3.2 above): the bodies of a family with `"proportions"` keep their build and height
  in cutscenes too.

3.6.8 (no more hitches in the entrances):

- **Object checks in constant time** (`IsLive`): UE4SS's `UObject::IsReal` walks every slot of the object array (tens of
  milliseconds in this game), and the mod called it once a second during an entrance, for every effect and sound it
  stopped, for every voice line and in its paths for the log. `IsLive` takes the object array's slot that the object's
  own index names (UE4SS's `UObjectBase::GetObjectItem`, which reads the index and checks it is in the array; under SEH,
  the pointer may be stale) and checks that it holds that very pointer and is not unreachable (`FUObjectItem::GetUObject`,
  `IsUnreachable`: what `IsReal` checks). Tried on two live objects at start; if it did not name them, `IsReal` again. The
  log: `Object checks: in constant time, from UE4SS's object items (each object's index names its slot)`. Only what
  UE4SS.dll exports: its versioned container (`Container::UnrealVC`) is not, and the first build of 3.6.8, which called
  it, did not link.
- **Other copies of a model** (the parts hidden on cutscene and menu copies) are looked for a few blocks of 2048 slots of
  the object array a frame (UE4SS's `ForEachUObjectInRange`; all of it in about 120 frames, at most a quarter of a
  millisecond a frame) instead of UE4SS's `FindAllOf` every 3 s (a hitch every 3 s, in battle and in the field).
- **Cinema bars drawn by the mod** (two black UMG `Border`s anchored to the top and the bottom of the screen, the height
  from `WidgetLayoutLibrary.GetViewportSize`), retracting with the camera's blend back. 3.6.6 - 3.6.7 constrained the
  entrance camera's aspect ratio: the game renders a smaller picture then, so its render targets (and an upscaler's) were
  made again as the bars came and went. The camera's own constraint is off (a `CameraActor`'s camera keeps 16:9 unless
  told) unless the bars cannot be made.
- **The log says how smoothly an entrance played** as it is over: `...'s entrance played at N fps (frames in s; M fps
  before it); its longest frame X ms (t s in); K frame(s) over 50 ms, ...; frames in each second: ...; the mod's own work
  ...`, and the mod's slow steps (12 ms or more: `starting effect ...`, `playing sound ...`, `putting on ...'s model`,
  `the switch to ... (all of it)`).

3.6.9 (the log, for the T-pose in chapter 1's burning Nibelheim):

- **What the character you control is and plays** (`Watch: you control ...`, once a second, logged when it changes): its
  model, AnimBlueprint, anim instance and the montage it plays; the sets the game took into its map with their objects
  (`Watch: ...'s sets (the game's map): Neutral00 = /Game/Motion/..., ...`); and every set name the game's set lookup
  was asked for it, with whether the game had it, the mod gave it or neither had it (`Watch: set lookups for ...`).
- **The calls**: the UFunctions of animation, actions, montages, motion, movement and input the game calls outside battle
  on that character (its mesh, its anim instance) or with one of them as a parameter, with their parameters (`Watch:
  call ...`; the first 4 of each, 300 lines at most).
- **A level set the game has none of**: when the game's lookup is asked, for a character with forms, for a set neither the
  game nor the mod has, the set of that name in its row's folders (`/Game/Motion/Level/<name>/<folder>`,
  `/Game/Motion/FieldAction/<name>/<folder>`) is found, or loaded from a tick, and the mod's lookup gives it from then on.

3.6.10 (more of the log, for the same T-pose): every set name the game's set lookup is asked for any character, from
the start (`Watch: set lookup <name> (the game had it / the mod gave it / NEITHER had it), last for <character>`); the
character's set entries (its +0x11B8 map: per key, each entry's name and set) and its anim instance's set layers (+0x1500)
when they change; the calls watched for any character of the classes of the character you control and of those with forms
(a character spawned again is watched from its start), without the mod's own montage question and the per-frame
AnimBlueprint events; the montage it plays with its animations and their skeletons, looked at four times a second; and,
once, the game's functions whose names speak of animation sets, actions or locomotion.

3.6.11 (the T-pose in burning Nibelheim): there the game puts a level set on the character you control (DmgWalk00, the
damaged walk: an entry of the character's set map under key 2, named after the set's object, `PC0010_Sephiroth` for
Sephiroth's folder) and the entry stays empty: nothing to stand or walk with, and the walk is what moves him. The mod fills
such an entry (`FillEmptyEntries`): the level set it is for is the one of the row's level sets (its
`OverrideAnimationSetString_Array`) or of the gimmicks' field-action sets whose name the character, its anim instance or
its controller holds, else the set of the montage the character played as the entry was made
(`/Game/Motion/Level/DmgWalk00/PC0000_Cloud/N_Idle01_1`: DmgWalk00); that set of the entry's folder
(`/Game/Motion/Level/DmgWalk00/PC0010_Sephiroth`, the data pak's copy) is found or loaded (from a tick; a path that cannot
be loaded is not tried again) and given to the entry with the game's own registration and pose change, as the forms' kept
instances are given their sets. The log: `Level sets: <row>'s set entry [key] <name> (entry bytes) ...; GIVEN <path>`.

3.6.12 (the same T-pose): 3.6.11 found the set but loaded it from a tick only, and there no tick callback ran (the frame
work ran from ProcessEvent: `... not loaded yet (waits for a tick)`), so it was never given. Now:

- **The set the entry is for**: entry +0x10 was taken for an FName naming it and matched against the names of the row's
  `OverrideAnimationSetString_Array` and of the gimmicks' field-action sets; else, as before, the one name the character
  holds, else the set of the montage it played. (In the test +0x10 was `0x3E3260`, the time before `0x3E403F`, neither
  one of those names: it is not the set's name. The montage named it: `the set of the montage it played: Level/DmgWalk00`.)
- **Which object**: that set of the entry's folder (the data pak's copy), then of the row's field folders (Cloud's
  `/Game/Motion/Level/DmgWalk00/PC0000_Cloud`: the level plays his animations of it), the first that is loaded and done
  loading (`InPipeline`, `FlagsReady`) and is an `EndAnimSet` (`FindOrLoadSet`).
- **When none is loaded**: from a tick a blocking load as before; anywhere else each is asked to load in the background
  (`LoadInBackground`: `KismetSystemLibrary.LoadAsset`, what a Blueprint's Async Load Asset node calls, with no callback,
  a latent action of the character that the world finishes; its parameters and `LatentActionInfo` are checked by
  reflection, and it is used only when the engine has an asset manager, whose streamable manager the load may go
  through). A later look (four times a second) gives the first that has loaded. Each is asked again after 3 s while not
  found (a set loaded in the background and not kept goes with the next garbage collection), 5 times at most per map. The
  log: `... asked to load in the background (n)`, then `... GIVEN <path>`; once, `Background loads: through the engine's
  asset manager ...` or `Background loads unavailable: ...`.
- The 3.6.9 lookup of a set neither the game nor the mod has (`GiveFolderSet`) finds or loads its set the same way.

The test: Cloud's set was loaded (the level loads it), and the mod gave it 0.4 s after the entry was seen (`GIVEN
/Game/Motion/Level/DmgWalk00/PC0000_Cloud.PC0000_Cloud`): Sephiroth stood and walked on. Nothing was loaded in the
background.

3.6.13 (the log the T-pose needed, trimmed): what 3.6.9 - 3.6.11 logged to find it is gone, and the work it took each
frame with it:

- **The calls** the game makes on the character you control (`CallWatch`: on every ProcessEvent outside battle, a look at
  the function and its parameters, up to 300 lines a session).
- **Every set lookup** of every character (`SetWatch`'s table of all names and outcomes, written on each call of the
  game's lookup, on its animation threads too). The lookup now notes only what it has no set for, of the character you
  control (`NoteMissed`): what `GiveFolderSet` gives.
- **Four times a second**: the sets in the character's map with their paths, its set entries and anim instance layers,
  the montage with its animations and skeletons, and once the game's animation set functions.
- **In `FillEmptyEntries`**: what found nothing in either test: the row's level set names looked for in the character, its
  anim instance and its controller (16 KB each, four times a second while an entry is empty), and entry +0x10. The set is
  the montage's (`MontageLevelSet`: the level or field-action folder of the montage or of its animations, looked at four
  times a second outside battle), taken for an entry when it was seen at most 5 s before the entry was or 2 s after (an
  older montage's set, a ladder's say, is not given to a later entry; an entry once given is forgotten, so a later empty
  one of the same name, another level set's, goes by its own montage). The log: `Level sets: <row>'s set entry [key]
  <name>: <set> (the set of the montage it played); GIVEN <path>`, or `no level set to go by`.

What stays in the log: `Watch: you control <character> (<row>): model ..., AnimBlueprint ...` once per character, model
and AnimBlueprint; `Level sets: ...` once per entry and outcome; `Watch: <row> was asked for set <name> ...` when the
mod gives (or has no) set the game lacks; `Background loads: ...` once.

3.6.14 (the T-pose in the chocobo wrangling): there the game made an empty level set entry (`[0] PC0010_Sephiroth`) while
no montage played (`no level set to go by`), so 3.6.13 had nothing to choose the set by. A level loads the version of
its set made for the character the level was made for (Cloud's, `/Game/Motion/Level/<set>/PC0000_Cloud`), not the one of
Sephiroth's folder (the data pak's copies exist, but nothing loads them), which is why the entry stays empty. So:

- **Which level sets loaded** (`LevelLoads`): every animation of a level or field-action folder that loads (the
  animation PostLoad hook, any thread; `/Game/Motion/Level/<set>/<folder>/<animation>`) notes its set, folder and time
  under a lock; the log says each set once (`Level sets: <set> of <folder> (Level) loaded (its animations)`).
- **In `FillEmptyEntries`**, when no montage named the set (none 5 s before the entry or 2 s after) and the entry has
  been empty 2 s (the game had its chance): the level set of the row's other field folders (Cloud's) whose animations
  loaded last, no later than 2 s after the entry, and whose set object is still loaded (`NewestLevelLoad`; a set of the
  game's 83 level sets that was loaded before the mod noted loads counts as the oldest). It is given as before (the
  entry's folder's copy when loaded, else Cloud's). The log: `Level sets: <row>'s set entry [key] <folder>: <set> (the
  level set that loaded last: <set> of <folder> (n s ago), ...); GIVEN <path>`, or `no level set to go by (...; level
  sets loaded: ...)` with what had loaded, newest first.

The test: the wrangling's set was Capture00 (the chocobo catching set, `/Game/Motion/Level/Capture00/PC0000_Cloud`, loaded
with the area 38.6 s before the entry); the mod gave it and he stood and walked on. 3.6.14's first build did not link
(its `NowMs` was declared outside the forms' namespace, where it is defined): the clang check only compiles, so
`linkcheck.sh` now also lists the anonymous-namespace symbols an object uses but does not define.

Editor 1.12 - 1.12.4 (Build Moves):

- 1.12: **Base** (an animation of the character's own played under the move, its idle; **Base Loop** makes the move a
  loop as long as it) and two more **Retarget** ways for an animation of another skeleton: **Keep the character's own
  pose** (Motion: each bone's change from the animation's first frame (Motion From's) added to Base's pose, relative to
  the nearest bone above it both skeletons have) and **Lean** (Base leaning into the animation's root motion by **Lean**
  degrees at a run, from **Lean Bone** down).
- 1.12.1: a form's **Model Turn** and **Model Lift**: its moves are built with the model turned and lifted (its root
  held at its reference pose), for a model made facing another way or standing elsewhere (an imported one).
- 1.12.2: a move over Base moves the character as the animation does (its root motion; scaled to the form's model).
- 1.12.3: **Bone Map** (Motion only): which bones of the animation move which of the character's, `"Src=Tgt, ...,
  @Anchor"` (`@`: the bone of the animation the motion is taken relative to where no mapped bone is above, so the body
  under a figure is left out), e.g. the little Sephiroth on Bizarro's head moving Safer's upper body; with a map only the
  mapped bones move and the animation's curves are left out. **Source Turn**: the animation's skeleton faces that many
  degrees from the character's (about up). **Keep Base Root**: no root motion (the character stays where Base has it).
  **Source Sounds Only**: of the animation's own sounds and effects, only its sounds. Notifies From can be one of the
  game's composites (its `_Comp` animations): its notifies and those of the animations it plays, in its time. JSON:
  `"bone_map"`, `"source_turn"`, `"keep_root"`, `"source_sounds_only"` in a move's `"build"`.
- 1.12.4: an effect of the game's whose Niagara parameters this editor cannot write is copied without them. Rebirth
  Material Preview's VFX1 load adapter reads the game's own Niagara variables (an effect notify's user parameters,
  `m_UserParams`) with their names and no native type, and refuses to write one (it would come out lossy) when a package
  is saved or cooked and in `DuplicateObject`, which writes the object and reads it back: so a move made with Keep Source
  Effects from one of Cloud's animations stopped the editor (`FDuplicateDataReader Overread ... VFXNiagaraUserParameter:
  m_Variable`, Evil Cloud's Hell's Gate from Focused Thrust). Every notify a move copies (the animation's own sounds and
  effects, the gameplay notifies, a copy's notifies) goes through `CopyNotifyObject`: `DuplicateObject` as before, or,
  for a notify holding such a variable (`UnwritableNiagara`: named, with no native type, the adapter's own test), a copy
  made in memory (`NewObject` with the notify as its template) with the list elements holding them taken out (the effect
  plays with its own values for them); a notify with one outside a list is left out. The build report says how many
  (`n effect parameter(s) of the game's that this editor cannot write taken out of the effects copied`). The plugin
  depends on Niagara for the test.

Editor 1.11.1: ACL's safety fallback is off for the game's bone compression settings (`SafetyFallbackThreshold` 0 on
load), so a move built on a huge skeleton (Bizarro's) is saved with the game's ACL codec instead of the editor's
fallback, which the game cannot read.

Editor 1.11:

- Animation set rows get **Forms** (Button, Key, Hold Seconds, Title, Parts, fades, show/hide effects, Show Timer and
  Timer At; each form's Pack, Show, Model, Anim Class, Scale, Meshes, Hide Weapon, Effects, Keep Effects, Sounds, Fly,
  After, Ability Effects, Super Armor, Seconds, Cooldown, Revert To). Export Json writes them; Import From Game Json reads
  them back (the data object's own win when it has some). Validate shows the menu and every form as the game mod reads
  them, the sets of each form's pack, its Abilities entry, and checks models, AnimBlueprints, parts, effects and sound
  banks against the asset registry (nothing is loaded).
- **Build Moves** builds the moves of a form's pack on the skeleton of the model that form wears (a model of the game's
  that is not in the project: on its animation's skeleton). **Clip Start / Clip End / Speed** (advanced) make a move of
  part of an animation, played faster or slower; its hits are times in the clip as played, and the animation's own sounds
  and effects follow (JSON `"clip": [start, end]`, `"speed"`).

Sephiroth (FullyPlayableSephiroth, in Cloud's slot) has five: NORMAL, WINGED (Battle02: the one wing, feathers), FLYING
(Battle03: flies; also after his Limit 2), KH2 (Battle04: moves built from Kingdom Hearts II animations) and BIZARRO
(Battle05: Bizarro Sephiroth's model at 0.1, his transformation cutscene's ending as he turns (3.6.7: "Alone at last. Shall we?", the darkness, the reveal), his attacks built from Bizarro's animations with Sephiroth's damage and
Bizarro-shaped hit volumes, his conjured sword in the sword attacks, super armor, 60 s, 30 s cooldown).

## Skins (editor 1.15)

A skin is another model a character wears in game, kept as a folder of the game's own (zen) packages and a
`skin.json` in place of a pak, so any number of skins can be installed at once (an outfit pak replaces a blueprint:
one at a time). Needs Create a Character System 3.10 in the game.

```
ue4ss\Mods\RebirthSkelCompat\skins\<Folder>\skin.json
ue4ss\Mods\RebirthSkelCompat\skins\<Folder>\Content\<path under /Game>.uasset   (+ .ubulk / .uptnl / .m.ubulk)
ue4ss\Mods\RebirthSkelCompat\skins\<Folder>\preview.png                         (optional)
End\Content\Paks\~mods\CreateACharacterSkins_P.utoc/.ucas/.pak                  every installed skin's packages
```

The game only loads zen packages from a mounted container, so every installed skin's packages also go into one ~mods
container, `CreateACharacterSkins_P` (made anew from `skins\*\skin.json` each time; a skin whose skin.json says
`"enabled": false` is left out; of two skins with the same package the first by folder name keeps it).

**Skins** on the data object (one entry per skin): Name (the skins menu), Folder (empty: the Name's letters and
digits), Model, Characters (the CharaSpec rows that wear it: Cloud's rows for the Fully Playable Sephiroth and Young
Sephiroth), Family (the hub skeleton the model's skeleton joins, e.g. PC0010_00_Skeleton), Keep Proportions and
Proportion Bones, Voice (`own`: the original banks, e.g. adult Sephiroth's; a voice bank with `{language}`; empty: the
row's), Weapon (a weapon blueprint class), AnimBlueprint (advanced; empty: the character's own), Extra Assets (more
packages of the project cooked into the skin: materials or textures the game and your mods do not have), Author,
Description, Preview (.png). **Skins Output Folder** (empty: `Saved\RebirthSkelCompat\Skins`), **Install Skins**.

**Build Skins**, per skin that is on (`EndSkins.cpp`, `SkinCore.hpp`):

1. The skin's packages: the model, its skeleton and its physics asset, and Extra Assets, leaving out any package the
   game has (RebirthGameObjectLibrary's FindGamePackages: the game's own `Paks\pakchunk*` containers) and anything not
   under /Game. Reported: material slots whose material is neither in the skin nor in the game (it has to come from a
   mod, e.g. the game materials mod, else the slot shows the default material) and the model's bones its Family lacks.
2. Dirty packages saved, then cooked here for WindowsNoEditor the way the cooker saves them: each object's
   `BeginCacheForCookedPlatformData` first (waiting for it, shaders included), `PKG_FilterEditorOnly`, `SAVE_Async`
   (the exports in a .uexp, the bulk data in a .ubulk; `UPackage::WaitForAsyncFileWrites`), versioned with tagged
   properties as Package Project cooks the project's mods (no `SAVE_Unversioned`: tagged properties do not depend on
   the editor's classes matching the game's), into `<Output>\_work\<Folder>\Cooked\End\Content`. A .uasset that still
   comes out whole is split at its summary's TotalHeaderSize.
3. The engine's own IoStore commandlet makes the game's package format, as packaging does for a mod chunk, into a
   container of its own (uncompressed): `UE4Editor-Cmd.exe End.uproject -run=IoStore -CreateGlobalContainer=<work>\Global\global.utoc
   -CookedDirectory=<work>\Cooked -Commands=<work>\IoStoreCommands.txt -TargetPlatform=WindowsNoEditor
   -ddc=InstalledDerivedDataBackendGraph -unattended -NoLogTimes -UTF8Output -abslog=<work>\iostore.log`, run hidden
   (about 20 s; Cancel stops it). Imports of packages it does not have (the materials) become the base game's kind
   (arcs to the imported package's last bundle). The commandlet's exit code is 1 whenever the project logs an error
   of its own while it starts (an asset with a malformed tag), so the commandlet's own result in its log
   (`finished execution (result 0)`) and the container on disk decide.
4. The container read back (`CacsSkin::ReadToc`, `ExtractPackages`): each package's zen chunk and bulk chunks go to
   `<Output>\<Folder>\Content\...` and its store entry (size, export and bundle counts, load order, imported package
   ids) into skin.json; the files the last build listed and this one lacks are removed.
5. Install Skins (Game Directory set and the game mod there): the folder copied into the game's
   `ue4ss\Mods\RebirthSkelCompat\skins\<Folder>`, then `~mods\CreateACharacterSkins_P` made anew from every installed
   skin (written to `.new` files first and moved over the old ones only once all three can be written: close the game).

skin.json (`"schema": "CreateACharacterSkin/1"`): `name`, `author`, `description`, `characters`, `model`, `skeleton`,
`family` (object paths), `proportions`, `proportion_bones`, `voice`, `weapon`, `anim_blueprint`, `enabled`, `preview`,
`packages` (`package`, `file`, `size` as an exact integer, `export_count`, `export_bundle_count`, `load_order`,
`imports`: 16-digit hex package ids, `bulk`: `{file, type}` with the chunk type 3 .ubulk, 4 .uptnl, 5 .m.ubulk),
`built` (UTC), `built_with`. `SkinCore.hpp` (portable C++17, no engine types, no exceptions) reads and writes it and
makes the skins container, for the editor and the game mod alike.

Tests: `tests/skin_core_test.cpp` checks SkinCore against the Python prototype (`skinpack.py`): the engine-made
container of Remake Sephiroth read into the same packages and store entries as the prototype's skin folder, and the
skins container byte for byte the prototype's, plus skin.json round trips, JSON escapes, duplicates, a skin that is
off, and a compressed or damaged container refused:

```
g++ -std=c++17 -O2 -I<plugin>/Source/RebirthSkelCompatEditor/Private tests/skin_core_test.cpp -o skin_core_test
./skin_core_test <work>/Container/RemakeSephiroth.utoc Saved/RebirthSkelCompat/Skins/RemakeSephiroth <prototype cache folder>
```

## Customization (3.11)

The game's main menu (the field's pause menu) gets a **Customization** item, the last one on its list. It opens a
screen for the character you control, with a little preview of it, and six pages:

| Page | What it changes |
|---|---|
| MATERIALS | each material slot of the model it shows. Left / Right: the next or last of the materials the catalog has for that slot ("Original" first). Cross: the slot's list of them (the one under the cursor goes on once the cursor rests there; Left / Right or L1 / R1 a page at a time; Cross keeps it, Triangle keeps it and saves, Square: Original, Circle puts back the one there before) |
| MODELS | another model worn over its own (its own model's sections hidden, the other one following its bones) |
| SKINS | the skins installed for its CharaSpec row (Skins, editor 1.15), or its own model |
| VOICES | (3.11.1) the voice its lines play in: one of the catalog's voices (any party member's, Young Sephiroth's, Classic Sephiroth's), or its own. A voice speaks while the game has its bank loaded (the line says "not loaded now" otherwise: it speaks once the game loads it); the mod never loads a voice bank itself (3.6.3). A chosen voice wins over the forms' and the skin's voices, in every form |
| PARTS | another model on one of its bones, playing motions of its own (Sephiroth's wing, a white wing). A part with `sync` plays its own motion of the name of the one the character plays, in step with it (KH3's sync parts) |
| PRESETS | looks kept by name for the character's model: Cross on the first line saves the look as "Preset 1", "Preset 2", ...; Cross on a preset puts it on (its materials, the model worn over it, its parts); Square twice deletes it |

A choice goes on the character at once. **Save** keeps it: from then on the mod puts that look on the character
whenever it is in the game (the field and battle). Characters: the one you control and the party in the field.

| | Controller | Keyboard |
|---|---|---|
| choose | Up / Down (D-pad or left stick) | Up / Down, W / S, mouse wheel |
| change (materials), on / off (parts) | Left / Right | Left / Right, A / D |
| a slot's list (materials), wear (models, skins), speak with it (voices), on / off (parts) | Cross | Enter, Space |
| back to its own | Square | R, Delete |
| save | Triangle | F |
| page | L1 / R1 | Q / E, Page Up / Page Down |
| other character of the party | L2 / R2 | Z / X |
| turn the preview | right stick | C / V |
| back to the main menu | Circle | Esc, Backspace |

While the screen is open the game sees none of the controller (every button held back, both sticks in the middle) and
none of the keyboard and mouse buttons (the game window's messages are the mod's; F1 - F12, Alt+F4, Print Screen and
the Windows keys still go through), so the main menu under it stays as it was. A button or key still held as the
screen closes stays the screen's until it is let go (the Circle that closed it does not close the main menu too).

How it works (`src/RebirthSkelCompat.cpp`, `namespace Forms::Custom`):

* The item: the main menu's top window (`EndMainMenuTopWindow`) keeps the kinds of its items in two arrays of its own
  (not reflected: the kinds at +0x4a0, a byte each at +0x4b0); once the window has set up its list, the mod adds one
  more entry (a copy of System's kind) and one more count on its list (`EndVirtualScrollBox:SetItemCount`), and writes
  the 13th item's title. The window's handler of a pressed item (`OnLeftMenuPressedItem`) is the mod's for that item
  (its native function swapped; the game's own handling of the copied kind never runs for it).
* The preview: the game's `EndMenuViewport` widget (a world of its own) with a copy of the character: its model,
  materials, hidden sections, the model worn over it and its parts, its idle motion (`/Game/Motion/Player/<PCxxxx_Name>/
  Event00/NT_Idle01_1`, else `Emotion00/E_Idle01_1`, else `Battle00/B_Idle01_1`; a skin of another skeleton keeps the
  character's own pose), lit at the menu preview world's scale (3.11.1: three directional lights of 1.5 / 0.45 / 1.1 lux:
  the preview world's own light is 3 lux and its exposure is for that; at the game's daylight scale, 60000 / 18000 / 45000
  as 3.11.0 had them, everything burned out white). The main menu's window is hidden while the screen is open (the game
  draws its menus into every view).
* Parts are kept on their bone every frame (the part's own bone, `anchor`, placed where the character's `bone` is),
  play their `idle`, and in battle the motion their `moves` give the character's ability.
* Sync parts (`"sync": true`, or the folder of the part's motions): each frame the mod looks at what the character
  plays: its anim instance's montage (the sequence under the montage's position and the time in it), else in battle
  the action the battle plays on it (`EndBattleAPI:GetPlayingExtraActionSequenceNames`, by name). The part plays its
  own motion of that name, `<sync folder>/<the same folder>/<the same name>` (else the same name in Battle00, Battle01,
  Battle00_Comp, Battle02, Battle03, Reaction00, Neutral00, Emotion00, Event00, FieldAction00): a montage's at the same
  time each frame, an action's from its start. None of that name: its idle. The wing's sync folder is the winged
  Sephiroth's, `/Game/Motion/Player/PC0010_Sephiroth_Transform` (115 of Sephiroth's 183 Battle00 motions have one of the
  same name there). The log says the first dozen it found or did not ("Customization: sync: ...").
* Loading: what a choice needs (a material; a model; a part's model, motions and texture; a skin's model, AnimBlueprint
  and weapon) is loaded first. With the game in its paused menu the mod asks for it in the background (the screen says
  "Loading <name> ..." and the choice goes on once it is there, 10 s at most); from the world's tick it loads at once.
  A path that does not load, or is not what it should be (a material, a skeletal mesh, a motion, a texture), is not
  asked for again until the next map (the log names the first 20: "... (not tried again until the next map)"). The
  saved looks load the same way: a look goes on once what it needs is there.
* What the game changes: another model on the character's mesh (a skin, a form, a costume of the game's) takes off the
  model the screen put over it and gives the slots the screen changed back to that model's own materials; then the
  saved look for the new model goes on. While a model is worn over its own, the forms leave its own model's sections
  alone (they go back as the form wants them when it comes off), and the sections the screen hid are not the forms' to
  show. A saved model or part the game took off goes on again.
* Map loads: what the screen put on goes with the old map (nothing of the screen's runs until the new map is there,
  a minute at most when the load's end is not seen); on the new map the saved looks go on the characters again. A
  main menu window the game keeps across the load keeps its one Customization item.

Files, in the game's `ue4ss\Mods\RebirthSkelCompat\customization\`:

* `catalog.json`: what the screen offers. `make_customization_catalog.py` (Tools\RebirthSkelCompat, Python 3, no editor)
  writes it from the game's own containers (every playable character's models and their materials), your Game
  Materials (`Saved\RebirthGameMaterials\made\manifest.json`), the skins and the models your compat files' forms wear,
  plus two parts (the wing, white and as it is). Run it again after making materials or skins
  (`run_cacs3110_game_install.cmd` does). Without a catalog the screen still shows each character's own slots, models
  and skins.
* `catalog.extra.json` (optional, yours): entries in the same form, merged in first every time the catalog is written.
* `saved.json`: what Save kept (written by the mod; the old one replaced only once the new one is written). One that
  cannot be read (broken by hand) is never written over: at the next save it is moved aside as
  `saved.unreadable-<number>.json` (the log and the F9 report say so).

```
catalog.json
{
  "materials": [ {"name": "Young Sephiroth: hair", "path": "/Game/Character/Player/.../mat_ch049_001_hair.mat_ch049_001_hair", "for": ["PC0010_*"], "slots": ["Hair"]} ],
  "models":    [ {"name": "Cloud: Soldier", "path": "/Game/Character/Player/PC0000_06_Cloud_Soldier/Model/PC0000_06.PC0000_06", "for": ["PC0000_*"]} ],
  "parts":     [ {"id": "sephiroth_wing", "name": "Sephiroth's wing", "model": "/Game/Character/Player/PC0010_10_Sephiroth_Transform/Model/PC0010_10.PC0010_10",
                  "bone": "C_Spine_d", "anchor": "C_Spine_d", "sections": [10],
                  "idle": "/Game/Motion/Player/PC0010_Sephiroth_Transform/Battle00/B_Idle01_1.B_Idle01_1",
                  "moves": {"<ability id>": "<motion path>"}, "tint": [1, 1, 1, 1], "tint_param": "Color",
                  "tint_texture": "/Game/Renderer/Texture/FFFFFFFF_sRGB", "tint_texture_param": "Color",
                  "offset": [0, 0, 0], "scale": 1.0, "component_class": "/Script/EndGame.EndSkeletalMeshComponent"} ],
  "voices":    [ {"name": "Classic Sephiroth", "bank": "/Game/Sound/Voice/{language}/Character/Player/VO_PC0010_15_ClassicSephiroth", "note": "ClassicSephirothVoice_P"} ],
  "preview":   {"key_lux": 1.5, "fill_lux": 0.45, "rim_lux": 1.1, "zoom": 1.0, "background": [0.012, 0.016, 0.03, 1],
                "exposure": 0.0}
}
```

`for`: model names (`PC0000_00`), the start of one (`PC0010_*`) or object paths; empty or left out: every model (the
catalog the script writes leaves it out: every material for every slot, the ones named for the slot's part first, e.g.
the hair materials for a `..._Hair` slot).
`slots`: slot names (`PC0000_00_Hair`), their end (`Hair`: a slot ending in `_Hair`) or `*` and an end. `exposure` (a
bias): the preview's exposure fixed (left out: it adapts by itself). A part: `bone` (or `socket`) the character's bone
it goes on, `anchor` the part's own bone kept there (default: `bone`), `sections` the part model's sections shown (all
when left out), `idle` its looping motion, `moves` (in battle) the motion it plays for an ability of the character's,
`tint` a color put on its materials' `tint_param` (default `Color`), `tint_texture` a texture put on their
`tint_texture_param`, `offset` (cm) and `scale`, `component_class` (default the game's EndSkeletalMeshComponent),
`sync` (true: the folder above its idle's folder; or a folder) its motions named like the character's.
A voice (3.11.1): `bank` the voice bank (its language folder `{language}`), `name`, `note` (shown on its line). The
script writes every playable character's voice bank of the game and the mod's voices whose containers are in ~mods
(ClassicSephirothVoice_P, YoungSephirothVoice_P).

```
saved.json
{
  "looks": [ {"mesh": "<the model it is for>", "materials": {"3": "<material>"}, "model": "<model worn over it>", "parts": ["wing"]} ],
  "skins": {"<CharaSpec row>": "<skin folder>"},      ("-": its own model)
  "voices": {"<CharaSpec row>": "<voice bank>"},      ("-": its own voice; 3.11.1)
  "presets": [ {"name": "Preset 1", "for": "<its own model>", "model": "", "parts": ["sephiroth_wing"], "materials": {"3": "<material>"}} ]
}
```

The model and the parts are kept for the character's own model, the materials for the model they are on (the one worn
over it, else its own), the skin for its CharaSpec row (put on its row when the compat files are read, before the
game's characters load). The F9 report has a "Customization:" part (the item, the catalog, what was saved).

Install: close the game, run `run_cacs3113_game_install.cmd` (builds main.dll 3.11.3, installs it, writes the catalog
again). The log says `Customization: the main menu gets a "Customization" item` at the first frames,
`the main menu's item 13 is "Customization"` when the main menu opens, and `the screen opened for ...` / `the preview
shows ...` when it is chosen. A main menu laid out other than this version knows switches the item off (the log says
why); an error in the screen's work switches it off for the session.

Skins (3.11.0): a skin's model (or a form's) that the mesh runs no anim instance on a moment after it went on (its
skeleton runs none of the character's AnimBlueprints: it would stand in its bind pose while the game's animation code
expects an instance) comes off again: the character's own model goes back on, and the skin stays off for that
character until the next map (choosing it again on the Customization screen tries again). The log: "Forms: WARNING:
<row>: <model> runs no anim instance ...". It is looked at twice, 2 s apart, only while the world runs (a look the game
puts on while it is paused makes its instance as it runs again).

### 3.11.1 - 3.11.3

* The frame work (the forms, the voices, the screen) runs from the engine's own tick (3.11.3: `UEngine::Tick`, its
  vtable slot 0x2C0 checked against UEngine's table first; the log says "Engine tick hook installed"), once a frame,
  also in the paused main menu: the main menu ticks no actor and this game's UE4SS calls no viewport tick, so the
  screen ran only when the menu ran game code (3.11.0), then about 4 times a second from its widget's own Tick
  (3.11.1). Without the hook it runs from actor ticks, ProcessEvent and the screen's widget as before. The log says,
  as the screen closes, how often its frame work ran and how long a frame of it took.
* The screen opens for the character you controlled until it opened (the paused menu reports no player character),
  and the party is found from it.
* A CharaSpec row's field twin (`<row>_NoBattle`, Young Sephiroth's in the field) is the row's: its skins and voices.
* VOICES (above). The saved voice goes on its row when the compat files are read (a row is made for a character that
  has none); the mod never loads a voice bank: the Fully Playable Young Sephiroth's data (v8) lists the Young and
  Classic Sephiroth voices in Cloud's 9 packs, so the game loads them with him.
* skin.json `"worn": false`: the skin is a choice for its characters on the SKINS page, not worn until chosen there.
  `"meshes"` (3.11.2): more meshes worn with the skin's model, as a form's (`{"mesh", "socket", "follow_pose"}` or a
  path), e.g. Remake Sephiroth's black wing beside his winged body.

### REMAKE and REMAKE WINGED (3.11.4: forms files and data; the game mod stays 3.11.3)

Sephiroth's last two forms on his forms menu (SephirothForms.json and YoungSephirothForms.json) are FINAL FANTASY VII
REMAKE's Sephiroth:

* **REMAKE** (pack Battle08) wears the Remake boss's model (`EB0021_00`, from CreateACharacterSkins_P; without it he
  keeps his own); **REMAKE WINGED** (Battle09) his winged body and black wing (`EB0021_01_Body` + `EB0021_01_Wing`).
* Their moves are built from the Remake boss's own animations (Battle08 24, Battle09 5; the rest of each pack is his
  Battle00 / Battle00_Comp): Rebirth Sephiroth's damage on Remake's hit times, and Rebirth's own Sephiroth effects
  (`FX_PC0010_*`) and sounds at the times and places Remake's animations have theirs.
* ATB commands: Octaslash (`PC0010_RM_Octaslash`, 2 ATB), Scintilla (`PC0010_RM_Scintilla`, 1), Shadow Flare
  (`PC0010_RM_ShadowFlare`, 1), Hell's Gate (`PC0010_RM_HellsGate`, 2) and Heartless Angel (`PC0010_T_HeartlessAngel`);
  their names are the game's own for Remake Sephiroth's attacks. Damage rows `PC0010_RM_Hattou_01` - `08`,
  `PC0010_RM_Senkou_01` - `06`, `PC0010_RM_Gokumon_01` - `02`.
* The moves, the abilities, their damage and help texts, and Battle08 / Battle09 in Cloud's 9 CharaSpec rows are in
  the data containers (FullyPlayableYoungSephirothDataAssets_P, FullyPlayableSephirothDataAssets_P).

Building the moves again (End project, editor and game closed): `Tools\RemakeForms\run_remake_forms.cmd`. It builds
the moves of `Saved\RebirthSkelCompat\RemakeForms\cmd\plan.json` with Build Moves in an editor commandlet (an open
editor renders a thumbnail of each saved move, which stopped it), puts Remake's sounds and effects on each from a
carrier build of the same animation (`Built/RemakeFormsCarriers`: one hit per sound and effect, their offsets and
attach points set, then Copy Notifies Onto), cooks them with the engine's cook commandlet (tagged properties, as
Package Project cooks; the editor's own save for the game writes unversioned ones when the project allows them) and
packs them with IoStore into `Saved\RebirthSkelCompat\RemakeForms\_work\Container\RemakeFormsMoves.utoc` / `.ucas`.
A move that stops the editor is left out and the others go on. Status: `Tools\RemakeForms\build\remake_status.txt`.

## Editor 1.16: sockets for the Remake Importer

`URebirthRemakeImportLibrary::AddSockets(SkeletonOrMesh, SocketsJson)` (Python:
`unreal.RebirthRemakeImportLibrary.add_sockets`) puts sockets on a skeleton (shared by its meshes) or on one mesh: a
JSON array of `{"name", "bone", "location": [x, y, z], "rotation": [pitch, yaw, roll], "scale": [x, y, z],
"always_animated"}`, a socket of the same name set anew, one on a bone the target lacks left out. It returns a JSON report
(`added`, `replaced`, `skipped`) and marks the asset changed. The Remake Importer 1.1 (Rebirth FX > Import FF7 Remake
Character or Weapon...) uses it: every model it imports, a character's or a weapon's (Remake's 122 weapon folders, from
Cloud's swords to the Masamune), gets its game skeleton's sockets (a weapon's `Attach_Chara01`, `Body_Center01`,
`VFX_Muzzle01`, ...), the ones on the root bone placed for the root resting flat. Without 1.16 the import says the
sockets were not added and does the rest. Details: `Tools\RemakeMaterials\README.txt`.

## Build

```
python build_dll.py --install     # compile + verify imports against the installed UE4SS.dll + install
python build_plugin.py            # UnrealBuildTool, EndEditor target, only the plugin module
```

`build_dll.py` uses the same MSVC 14.44 / Windows SDK 10.0.26100 / UE4SS c0a8d4c SDK as the
RebirthSkeletonObserver build. Outputs and logs go to `build\<UTC stamp>\`.

## Runtime pair sources

1. `ue4ss\Mods\RebirthSkelCompat\compat\*.json`
2. `End\Content\Paks\~mods\**\*.skelcompat.json` (next to a mod's pak)
3. `BP_SkelCompatUserData` (parent: AssetUserData) on the receiving skeleton's or mesh's Asset User Data,
   array variable `AnimationSkeletons` (+ optional `ReceivingMeshes`).

`tests/core_tests.cpp` covers the portable core (JSON, paths, config merging and families, the port of
`USkeleton::IsCompatibleMesh`, the hierarchy fix, animation set rows, the TMap reader/writer):
`g++ -std=c++20 tests/core_tests.cpp && ./a.out`.
