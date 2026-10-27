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
  replaces the copied notify's: 1.16.1 puts it in `DamageSourceIDs`, alone, as the game's own animations name theirs
  (`DamageSourceID` left empty; before 1.16.1 it went into `DamageSourceID` with its quotes). With nothing to copy from (no Notifies From
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
| `state_effects`, `watch_damage` | (3.12.2) the game's special state effects on it in battle (`"BossSephiroth_FeelerSword"`, `{"state": ..., "needs": a socket or bone}`); damage source rows the log counts in its abilities |
| `ability_effects` | effects while some abilities run in the form (`"PC0010_NAtk_*"` patterns): a conjured sword in sword attacks |
| `fly` | real flying, hovering above where it started (height, speed, max, up / down keys) |
| `after` | switches to this form by itself when that ability ends (a transforming limit break) |
| `super_armor` | hits do not make it flinch or stagger (EndBattleAPI `SetDisableReaction`, set again every second) |
| `seconds`, `cooldown`, `revert_to` | a time limit (game time, `GameplayStatics.GetTimeSeconds`; the time left on screen at `timer_at`, orange in the last 10 s; it turns back once the ability it runs ends, 8 s more at most), then a cooldown before it can be chosen again (the menu shows `ready in 0:25`), and the form it turns back into |
| `entrance` | (3.6.6) played as the character in charge switches to it: its animation over everything else, a white flash, a descent from above, effects and a cinematic camera (below); (3.6.7) or a cutscene's shots, some before the switch |

The forms' `"movesets"` (3.15.1): `[{"name": "CLOUD", "pack": "Battle11"}]`, movesets the MOVESET page offers besides
the forms' (another character's motions built for this one), each its pack's set (one the row builds: a `"battle"`
source `"as"` it, with the `"moves"` that make the moveset). Not forms: never on the forms menu, no commands of their
own; up to 8. (3.16.1) An entry's `"weapon_socket"`: in battle, while a form plays that moveset, the weapon in its
hands sits on that socket of its model (CLOUD's: `"Attach_Weapon_Right01"`, Cloud's sword hand; Sephiroth's rules put
his weapon in his left); out of battle and in cutscenes, where the game puts it.

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
`family` (object paths), `proportions`, `proportion_bones`, `voice`, `weapon`, `anim_blueprint`,
`weapon_field_socket` (3.15.1: outside battle the weapon sits on this socket of the model, `"Attach_Weapon01"`: Cloud's
Buster Sword on his back; in battle it goes back where the game puts it, the hand; not in cutscenes), `enabled`, `preview`,
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
screen for the character you control, with a little preview of it, and eleven pages (3.16.0):

| Page | What it changes |
|---|---|
| MATERIALS | each material slot of the model it shows. Left / Right: the next or last of the materials the catalog has for that slot ("Original" first). Cross: the slot's list of them (the one under the cursor goes on once the cursor rests there; Left / Right or L1 / R1 a page at a time; Cross keeps it, Triangle keeps it and saves, Square: Original, Circle puts back the one there before) |
| MODELS | another model worn over its own (its own model's sections hidden, the other one following its bones) |
| SKINS | the skins installed for its CharaSpec row (Skins, editor 1.15), or its own model |
| WEAPONS | (3.12.0) the weapon in its hands: its own, its skin's, or one of the catalog's (every weapon blueprint of the game's playable characters: `make_customization_catalog.py` writes them; an entry's `"for"` limits one to some characters). It goes in the slot of the character's own weapon the game's way (as a skin's weapon), in battle and in the field; a form with a weapon of its own fights with that one |
| VOICES | (3.11.1) the voice its lines play in: one of the catalog's voices (any party member's, Young Sephiroth's, Classic Sephiroth's), or its own. A voice speaks while the game has its bank loaded (the line says "not loaded now" otherwise: it speaks once the game loads it); the mod never loads a voice bank itself (3.6.3). A chosen voice wins over the forms' and the skin's voices, in every form |
| MOVESET | (3.15.1; the COMBO page before, see 3.15.1 below) the moveset a form plays: its own, another form's, or one of its row's `"movesets"` (CLOUD: Cloud's motions on Sephiroth). A moveset is every battle animation but the commands': idles, runs and walks, turns, dodges, guard, the Square chain and the air chain, specials, damage, downs, deaths, victory; abilities, limits, magic, items and synergies stay the form's own. A form at a time, as COMBO was (3.14.6): the first line says which form the page sets, Cross on a moveset asks for which forms (Cross, that form; Square, every form; Circle, no change), Square on the page gives that form its own. It goes on at once (the next move plays it); a form with a model of its own on another skeleton (Bizarro's, Safer's) keeps its own. Save keeps each form's (`saved.json` `"movesets"`; a combo saved before is that form's moveset now) |
| PARTS | another model on one of its bones, playing motions of its own (Sephiroth's wing, a white wing). A part with `sync` plays its own motion of the name of the one the character plays, in step with it (KH3's sync parts). (3.13.0) A part's own `effects` stay on it while it is worn ("Sephiroth's wing (feelers)") |
| EFFECTS | (3.13.0) effects kept on its weapon, its body or a part it wears. The first line says what they go on (Left / Right: its weapon, its body, each part on it; Square there: every effect on that off), the catalog's effects for that follow (Cross: on / off). An effect stays on in the field and in battle; on the weapon, it follows the weapon in its hands (a new weapon gets it; none in its hands: it goes on once there is one). The preview shows those on its body and parts (it shows no weapon) |
| PRESETS | looks kept by name for the character's model: Cross on the first line saves the look as "Preset 1", "Preset 2", ...; Cross on a preset puts it on (its materials, the model worn over it, its parts); Square twice deletes it |
| PARTY | (3.12.0) who leads the party in the field (the character you control): Cross on a member makes it the leader once you go back to the game (EndPartyAPI SetPartyLeaderType, the story's own switch: first asked, then forced; it waits while you are in battle, riding or in a cutscene, 10 minutes at most) |
| CHARACTER | (3.16.0) who plays in a party member's place: the place's own (what its CharaSpec rows spawn now: with Fully Playable (Young) Sephiroth, Sephiroth in Cloud's place) or a character of its own for that place (a compat file's `"characters"`: CLOUD, the game's own Cloud as a character of his own). One at a time; saved at once (saved.json `"characters"`), in at once (3.16.2; chosen in battle: once it is over): the game swaps the member as you close the menu, or else the next time it spawns the party (load a save, or go into another area). (3.16.3) The place's own goes back the same way (see [Characters](#characters-316)) |

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
  "effects":   [ {"name": "Feelers (Sephiroth's sword)", "effect": "/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Particle/FX_PC0010_10_SetFeeler_Sword_01.FX_PC0010_10_SetFeeler_Sword_01",
                  "on": "weapon", "socket": "C_Body_a", "scale": 1.0, "note": "the boss Sephiroth's feelers on his sword"} ],
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
`sync` (true: the folder above its idle's folder; or a folder) its motions named like the character's, (3.13.0)
`effects` its own effects, on while it is worn (`[{"effect": ..., "socket": a bone of the part's model, "scale": 1}]`, or
just the paths).
An effect (3.13.0): `effect` (or `path`) a Niagara or Cascade system (most of the game's are Cascade), `on` what the
EFFECTS page offers it for (`weapon`, `body`, `part` or `any`), `socket` (or `bone`) where on that it goes (one the thing
lacks, or none: its root), `scale`, `note` (shown on its line). The script writes 32 of the game's (the boss Sephiroth's
feelers on a sword's `C_Body_a` and on his wing's `R_FeatherD_b_Phy`, his aura, the party's limit and burst auras,
charged swords, Bizarro Sephiroth's), those the game has.
A voice (3.11.1): `bank` the voice bank (its language folder `{language}`), `name`, `note` (shown on its line). The
script writes every playable character's voice bank of the game and the mod's voices whose containers are in ~mods
(ClassicSephirothVoice_P, YoungSephirothVoice_P).

```
saved.json
{
  "looks": [ {"mesh": "<the model it is for>", "materials": {"3": "<material>"}, "model": "<model worn over it>", "parts": ["wing"]} ],
  "skins": {"<CharaSpec row>": "<skin folder>"},      ("-": its own model)
  "voices": {"<CharaSpec row>": "<voice bank>"},      ("-": its own voice; 3.11.1)
  "effects": {"<CharaSpec row>": [ {"on": "weapon", "effect": "<system>"}, {"on": "part:sephiroth_wing", "effect": "<system>"} ]},   (3.13.0)
  "presets": [ {"name": "Preset 1", "for": "<its own model>", "model": "", "parts": ["sephiroth_wing"], "materials": {"3": "<material>"}} ]
}
```

The model and the parts are kept for the character's own model, the materials for the model they are on (the one worn
over it, else its own), the skin for its CharaSpec row (put on its row when the compat files are read, before the
game's characters load). The F9 report has a "Customization:" part (the item, the catalog, what was saved).

Install: close the game, run `run_cacs3115_game_install.cmd` (builds main.dll 3.11.5, installs it, writes the catalog
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

### 3.11.5: no looks on rides

A vehicle or a mount you control (the rental bike, the scooter, the buggy, a chocobo, the Tiny Bronco, the motorcycles)
gets no looks. On one, the screen is for the one riding (the character you controlled before you got on), and the party
list leaves rides out. A ride is one of the game's ride classes (`EndChocoboCharacter`, `EndTinyBroncoCharacter`,
`EndSelfBalancingScooterCharacter`, `EndBikeCharacter`, `EndWheeledVehicle`) or a character whose own model is under
`/Game/Character/Property/` (the game's vehicles and props, `VE0025_00_RentalBike_Standard` among them). A saved look
for such a model is left out as saved.json is read (the log says so, and the next save leaves it out of the file), and
no model or part goes on a ride from anywhere (saved looks, presets, the screen). Why: Cloud's model, put over the rental
bike's by opening the screen while riding it, crashed the game whenever the game took control of the bike (the crash
was in the game's own code that takes over a ride, as it went over the bike's mesh components).

Install: close the game, run `run_cacs3115_game_install.cmd`. The log says `RebirthSkelCompat 3.11.5 starting`; the
screen opened on a ride says `Customization: you control <ride> (a vehicle or a mount): the screen is for <character>
instead`.

### 3.11.6: skins only where their model can run

A skin (or a form's model) goes on only when the AnimBlueprint it would run (the skin's own, else the character's)
targets the skeleton its model is on after the families (`RunsOn`: the AnimBlueprint's TargetSkeleton is the model's
Skeleton). Otherwise the character keeps its own model, the skin stays off until it is chosen again (it stays the saved
choice), its weapon stays off too, and the Customization screen's SKINS page shows it as "Can't be worn here" with the
two skeletons. Why: the Sephiroth skins on Cloud with Fully Playable Sephiroth not installed (Cloud runs his own
AnimBlueprint, on `PC0000_00_Skeleton`; the skins' models are on `PC0010_00_Skeleton`) went on with no anim instance,
and for the seconds before the 3.11.0 guard took them off again, the game's per-frame code for a mesh with an
AnimBlueprint and no instance (ff7rebirth_.exe 0x7B098C) ran its registry clean-up (0x21B52E0), which reads the outers
of objects already freed (0x104E8E4) and crashed (8 of the 9 dumps of 10/22-23). The guard stays for a model whose
skeleton matches but still runs no instance, and now also gives the character its own weapon back. The log names the
skin worn instead of the first skin of a row made for skins.

Install: close the game, run `run_cacs3116_game_install.cmd` (3.11.5's change is in it). The log says
`RebirthSkelCompat 3.11.6 starting`; a skin that can't run on a character says
`Skins: <row>: <skin> NOT put on: <AnimBlueprint> runs on <skeleton>, <model> is on <skeleton>`.

### 3.15.1: movesets instead of combos; CLOUD's moveset; the Buster Sword on Cloud's back

* **MOVESET** takes the COMBO page's place: a form plays another form's whole moveset, not only its Square chain. A
  moveset is every battle animation but the commands' (`B_Ability*`, `B_AtkBurst*`, `B_AtkLimit*`, `B_AtkMag*`, `B_Mag*`,
  `B_Item*`, `B_Chain*`, `B_BurstChain*`, `B_Comp*`, `B_EleBurst*`, `B_Summon*`): idles, runs and walks, turns, dodges,
  guard, the Square chain and the air chain, specials, damage, downs, deaths, victory. A form's commands keep their own
  animations. The page works as COMBO did (a form at a time); `saved.json` `"movesets"` (a `"combos"` entry saved before
  is read as that form's moveset).
* **Movesets that are not forms**: a row's forms can offer `"movesets": [{"name": "CLOUD", "pack": "Battle11"}]`, a pack
  the row builds (`"battle"` sources `"as"` it and the `"moves"` that make it). CLOUD, in the Sephiroth forms files: Cloud's
  own Rebirth battle motions on Sephiroth, 123 moves built with Build Moves (Retarget: proportions, Keep Source Effects:
  Cloud's swing sounds, trails and footsteps), each with the gameplay notifies of Sephiroth's move of that name (damage,
  combo, cancel and dodge windows, states, voice, face) and Sephiroth's damage moved onto Cloud's blows; his dodge is
  Cloud's roll in three pieces timed like Sephiroth's warp, his turns while guarding Cloud's guard. Cloud's strafing walks
  and turn on the spot are his own blend spaces (his skeleton is in Sephiroth's family, `"proportions"`). Sephiroth's
  Triangle, hold-Square and parry attacks, a few damage pieces Cloud has no motion for and the additive flinch stay his.
  The built moves are in `CloudMovesetMoves_P` (`~mods\FullyPlayableSephirothPaks\CloudMoveset`).
* A skin's **`"weapon_field_socket"`**: outside battle the weapon the skin fights with sits on that socket of its model;
  in battle it goes back where the game's rules put it (`AttachWeapon`: the hand); not while a cutscene plays (its rules
  place the weapons). The skins RebirthCloud and RemakeCloud have `"Attach_Weapon01"`: the Buster Sword on Cloud's back.
  A model without the socket keeps the weapon where the game puts it (the log says so once).

Install: with 3.16.0 (`Tools\CloudCharacter\run_cacs3160_install.cmd`: the game mod, the moves' container, the forms
files and the two skins; the files there before go to the game's `_mod_backups`).

### 3.14.8: no hitch as a map comes in or at a form switch

* 3.14.7 still looked a voice bank up by its path after a map change (the walk starting again) and at a plan asked for
  (a form, skin or voice changed): eleven looks for a bank the game had not loaded, `the voices 332 ms` as a map came
  in. A bank is now never looked for by its path but for a voice chosen on the Customization screen; the walk runs at its
  full pace for 20 s after a map change and for 5 s after a plan asked for, and meets a bank the game loads within a few
  seconds.

Install: close the game, run `run_cacs3148_game_install.cmd` (the log says `RebirthSkelCompat 3.14.8 starting`).

### 3.14.7: the voices no longer slow the game down

* **13 frames a second with a form's or a chosen voice (fixed).** The voices' plan, twice a second, looked for every
  voice bank it names by its path, and UE4SS finds an object by its path by going through the whole object array (it has
  none of the game's `StaticFindObject` here): some 20 ms a look. A bank the game had not loaded was looked for under
  eleven paths (its voice languages): 200 ms a plan, and 3.14.6's `Performance` line said `the voices 66.15 ms` of every
  frame, the game's own frame being 4 ms. Now the walk of the object array the voices make anyway (for the voice lines)
  keeps the sound banks (`SQEXSEADSound`) it meets by their names, and a bank is found among them, its path checked; a
  bank name the game's name table does not have is no bank loaded (no look at all); an object found at a path stays
  found while it is live and still that object; a path is looked for in the object array again only until the walk has
  met every object since the start or a map change, or when the plan was asked for (a form, skin or voice changed),
  and then at most once in 10 s. The log says `Voices: the walk has met every object: N sound bank(s) known ...`.
* SephirothForms (the Lua mod): the other copies of his model are looked for (FindAllOf, every 3 s, a hitch each time)
  only when his model has the wing.

Install: close the game, run `run_cacs3147_game_install.cmd` (builds main.dll 3.14.7 and installs it; the log says
`RebirthSkelCompat 3.14.7 starting`).

### 3.14.6: each form plays its own combo; a combo for each form

* **The wrong combo in WINGED, FLYING, REMAKE ... (fixed).** The game's `SetPrimaryAnimPack` *adds* a pack to the
  character's list of packs (its set map's key 3: `EndCharacter`'s pack adder, called with 3 by the Blueprint function),
  and the game's animation lookup walks that list from its first pack (keys 0 - 10, each key's packs in the order they
  were added) and takes the first pack that has the animation. Only a switch to a form on the character's own pack put
  the list back (`ResetPrimaryAnimPack`), so every other form switched to in a battle found the Square chain, and every
  animation of the same name, in the pack put on first: the normal form's own (Young Sephiroth's `Battle07`, put on as
  the battle starts), so WINGED and FLYING played his Ever Crisis combo. A form switch now puts the list back first,
  then puts the form's pack on: the form's pack is the only one in it. (That reset's ability switch is skipped: the
  form's pack's abilities go on right after it, as before.) The log, after each switch:
  `Forms: <character>: its packs now (the first that has an animation gives it): key 3: Battle02`.
* **COMBO**, a form at a time: the page's first line says which form it sets (Left / Right: the character's forms on its
  own AnimBlueprint), the combos for it follow ("Its own", then each other form's, with the forms that play it now),
  the last line the combos chosen. Cross on a combo asks for which forms: **Cross** again, that form only; **Square**,
  every form; **Circle**, no change (any other button, or 10 seconds, no change). Square on the page with no question
  asked: that form plays its own. A combo chosen for a form goes into that form's pack's set only (its B_NAttack
  animations); Save keeps each form's: `saved.json` `"combos": {"<CharaSpec row>": {"WINGED": "YOUNG SEPHIROTH"}}` (a
  combo saved by 3.12.0 - 3.14.5, `"<row>": "<form>"`, is every form's).
* The look sets' line no longer says "its set map is empty" when it left other forms' packs out (OLDER SEPHIROTH, a
  form on the character's own pack, worn as a look: `none of its own (N of other forms' packs left out)`).

Install: close the game, run `run_cacs3146_game_install.cmd` (builds main.dll 3.14.6 and installs it; the log says
`RebirthSkelCompat 3.14.6 starting`).

### 3.13.0: effects on weapons, bodies and parts

* **EFFECTS** page (see the table above): effects kept on a character's weapon, its body or a part it wears, picked from
  the catalog's `effects` (`make_customization_catalog.py` writes 32 of the game's, those the game has: the boss
  Sephiroth's feelers on a sword and on his wing, auras, charged swords). Save keeps them by the character's CharaSpec
  row (`saved.json` `"effects"`, read back as the game starts).
* A catalog part's own `effects` (a new part, "Sephiroth's wing (feelers)": the wing with the boss's wing feelers on
  its `R_FeatherD_b_Phy`) stay on it while it is worn.
* How: every half second the mod keeps each character's effects on what they are on now (`NiagaraFunctionLibrary:
  SpawnSystemAttached` / `GameplayStatics:SpawnEmitterAttached`, attached to the socket or bone, kept until taken off):
  one whose thing went (another weapon in its hands, a part taken off, a model change) goes on the new one; a one-shot
  system that ended starts again. The log: `Customization: <character>: effect FX_X on its weapon (<mesh>, C_Body_a)`.
* Editor 1.17's Parts Builder: a part's **Effects** (effect, socket, scale), saved into the part's catalog entry; an effect
  made in the project is built with the part.

Install: close the game, run `run_cacs3130_game_install.cmd` (builds main.dll 3.13.0, installs it, writes the catalog
again with the effects; the log says `RebirthSkelCompat 3.13.0 starting`).

### 3.12.2: combos in skin forms; the boss's feelers on WINGED

* **COMBO**: a combo chosen on the page reaches the forms worn with a skin too. With a skin on (Remake Sephiroth), each
  form plays from its look's sets, and their `Battle00` is a copy of the form's pack's set made the first time the form
  is worn in a session. 3.12.0 / 3.12.1 changed the packs' sets only, never those copies, so a form kept the combo it had
  when it was first worn (the saved combo of the session's start, or one picked before): the combo looked stuck. The
  copies take their sets' animations again every time a look goes on and after every combo change (the log:
  `combo: N animation(s) of the forms' looks changed with it`, `the look set ... took N animation(s) of it again`).
* **`state_effects`** (a form): the game's own special state effects (its `BattleSpecialStateEffect` table: effects the
  game keeps on a character at the sockets the row names), on the character while it is in that form in battle, off as
  it leaves it. The boss Sephiroth's AI puts his feelers on this way: `BossSephiroth_FeelerSword`
  (FX_PC0010_10_SetFeeler_Sword_01 on his sword's `C_Body_a`) and `BossSephiroth_FeelerWing` (FX_PC0010_10_SetFeeler_Wing_01
  on his wing's `R_FeatherD_b_Phy`). An entry can be `{"state": name, "needs": socket or bone}`: it goes on only while the
  character's model has it (Remake Sephiroth's model has no wing). The log: `the game's special state effects ... on`.
* **`watch_damage`** (a form): damage source rows the log counts 0.3 s and 1 s into each of the form's abilities
  (`damage sources live: ...`), to see whether a move's bullets are made (the feeler bullets of Zanshin, Hell's Gate, Grip
  of Fate and Ground Feeler).
* `patch_feelers_3122.py` gives both Sephiroth forms files (`YoungSephirothForms.json`, `SephirothForms.json`) WINGED's
  and FLYING's feelers and watch list (each file kept first as `<name>.before3122`).

Install: close the game, run `run_cacs3122_game_install.cmd` (builds main.dll 3.12.2, installs it, patches the forms
files; the log says `RebirthSkelCompat 3.12.2 starting`).

### 3.12.1: the COMBO page's choice at once

* **COMBO**: a combo chosen on the page (or "each form's own") goes into the character's packs at once. 3.12.0 changed
  only the packs the late pass merged (`MergedPacks`), not the character's own pack, which its PostLoad merges on the game
  thread as a map loads: a choice came in at the next start only, and the combo saved before stayed until then (the forms
  kept YOUNG SEPHIROTH's chain, WINGED its feeler slashes included, after "each form's own"). Now every loaded pack the
  row's sets went into takes it. The log says what changed (`combo: ...`, or `nothing to change`).
* The shared rules (`SkelCompatCore.hpp`, the editor's copy too) read a clip's times (`path@from-to`) without exceptions.
* The data containers' install keeps its backups in the game's `_mod_backups\Paks\` (see 3.12.0 below).

Install: close the game, run `run_cacs3121_game_install.cmd` (builds main.dll 3.12.1 and installs it; the log says
`RebirthSkelCompat 3.12.1 starting`).

### 3.12.0: WEAPONS, COMBO, PARTY; Skewer's carry; clipped chains; less frame work

* **WEAPONS**, **COMBO** and **PARTY** pages (see the table above). Save keeps the weapon and the combo by the
  character's CharaSpec row (`customization\saved.json`: `"weapons"`, `"combos"`); the leader is the game's own.
* **Impale** (the grabs' carry): Lua mods can put an enemy on a character's blade and throw it off
  (`RebirthSkelCompatImpale(holder, target, seconds)`, `RebirthSkelCompatImpaleRelease(target, push, up)`,
  `RebirthSkelCompatImpaled(target)`, addresses from `:GetAddress()`, game thread). The enemy is paused (the battle
  API's actor pause, else its time dilation), its capsule and the holder's ignore each other, and every frame it is
  put on the blade (the weapon's tip and base sockets; a point in front of the holder when there is no blade); it is
  let go when it, its holder or its time goes, or its HP runs out. ForceGrabs 2.0 uses it for Skewer (WarpStab): the
  stab's hit carries the enemy, the lift and the throw follow (every enemy, through every armor and defense).
* **Clipped chains**: a move's animation in a chain may name a part of it, `"<path>@<from>-<to>"` (seconds; `to`
  0: its end): Skewer's composite is the stab up to 1.5 s, then the lift (`B_AtkStab02`).
* **Less frame work**: the battle state is asked 4 times a second, the party looked for 4 times a second, the parts'
  copies seen as they tick (a slow sweep for the rest), the catalog's lists worked out once; every 2 minutes the log
  has a line of what the frame work cost (`Perf:`).
* Fixes from the 3.12.0 review: a weapon or voice chosen for a character whose row has no forms (a compat file's
  sets-only row) is tracked with a NORMAL form (no crash in battle); a catalog weapon that is not a blueprint class
  is refused; the carry checks what Lua hands it and never touches a holder that went; the engine's tick drives the
  frame work every frame (no 8 ms throttle); copies at a reused address get their parts hidden.

The **Fully Playable (Young) Sephiroth** forms files and data containers go with it: YOUNG SEPHIROTH plays his own
Ever Crisis moves (pack Battle07: 88 moves built from the CH049 clips on Sephiroth's skeleton, with Sephiroth's gameplay
notifies on his blows and Sephiroth's swings, trails and slashes moved onto them), and WINGED's moves play the
transformed Sephiroth's feelers ("whispers": the feeler slashes his animations play only for a feeler ability, and
Zanshin's and Hell's Gate's feeler bullets, out of the ground for Hell's Gate). Built by `Tools\YSForms\run_ys_forms.cmd`
(editor commandlet, the editor closed; `Saved\RebirthSkelCompat\YSForms\cmd\plan.json`).

Install: close the game, run `run_cacs3120_game_install.cmd`: it builds main.dll 3.12.0 and installs it, copies the
forms files (`compat\SephirothForms.json`, `compat\YoungSephirothForms.json`) and the Lua mods (SephirothForms'
`main.lua`, `ForceGrabs.lua`, `MeteorStrike.lua`; RebirthLiveLink's `main.lua`) into the game (the old ones into
`ue4ss\_mod_backups\cacs3120_<time>\`), updates the installed data containers (the old files into the game's
`_mod_backups\Paks\`), and writes the catalog. The log says `RebirthSkelCompat 3.12.0 starting`.

**The backups of the data containers** first went into `End\Content\Paks\_mod_backups\`, with their .pak: the game
mounts every .pak anywhere under `Paks`, so it mounted the old copy too, and the old container (the same name, the same
container id) won over the new one: the packages the new one added were not found (the log: `899 of 990 move
animation(s)`, YOUNG SEPHIROTH's moves and the casts `NOT FOUND: move ignored`) and the moves it made again were the old
ones (WINGED without the feelers). The old copy is now in the game's `_mod_backups\Paks\` (not mounted), and
`install_data_tail.py` puts its backups there. Keep every backup of a pak outside `End\Content\Paks`.

## Characters (3.16)

A compat file's `"characters"` are the characters the Customization screen's **CHARACTER** page offers: a character
of its own in a party member's place (its `"slot"`), one at a time. While it has the place, the game's tables are as
the character has them. A data object's table is a frozen memory image the game reads in place, from the root its
table holder points at, and its rows can sit in memory the game maps read-only (a container stored without
compression is mapped), so the mod never writes them: it puts a **copy** of each table it changes in the game's place
(the root and every row in the mod's memory, each frozen pointer made again for where it is now, pointing at the
game's image for everything else) and changes the copy. The place back to its own puts the game's root back. The
game spawns the party as a map loads, so the copies go in before a map loads: a choice shows from the next map load.

```json
{"schema": "RebirthSkelCompat/1",
 "characters": [{"name": "CLOUD", "slot": "Cloud", "player": "pt_Cloud", "requires_paks": ["CreateACharacterCloud_P"],
   "charaspecs": {"PC0000_00_Cloud_Standard": "PC0000_00_Cloud_Standard_CACS", "WE0000_00_Cloud_BusterSword": "WE0000_00_Cloud_BusterSword_CACS"},
   "rows": [{"table": "BattlePlayerParameter", "row": "pt_Cloud", "from": "pt_Cloud_CACS"},
            {"table": "BattleAbility", "row": "PC0000_Limit001", "from": "PC0000_Limit001_CACS", "keep": ["UniqueId"]}],
   "values": [{"table": "PlannerEvent", "rows": ["BT_BVCLD_STARTBTL_0000"], "field": "VoicePack", "value": "VO_PC0000_00_Cloud"}]}]}
```

| Key | |
|---|---|
| `name` | what the page shows; a place has each name once |
| `slot` | whose place it takes |
| `player` | its BattlePlayerParameter row (default: its `rows` entry of that table): compat rows' `abilities` for it stand down while it has the place, but its own (3.21.0: a compat row of one of its own CharaSpec rows plays its abilities while it has the place, and waits while it has not) |
| `charaspecs` | the place's CharaSpec rows and its own: its rows are spawned wherever the `names_in` tables name the place's (its own rows must be in the game's CharaSpec table, else "Can't play") |
| `names_in` | where the game names them; default PlayerTable's `PlayerCharaSpec_Array`, `EventCharaSpec_Array`, `ChangeWeaponCharaSpec_Array`, PlannerEventChara's `CharaSpecName`, BikeCharaSpec's `RiderCharaSpecID_Array`, Equipment's `CharaSpecID_Array` |
| `names_in_add` | (3.21.0) the same, added to the defaults (or to `names_in`); an entry's `"optional": true` is a table the character does without until the game loads it (a level's own: `/Game/DataObject/Field/<area>/PlannerLevelSet`, the final battle's BattleCharaSpec), put in alone once it is there, even in a battle |
| `names` | (3.21.0) `{"a name the game gives the place's things": "the character's own"}`, renamed where its charaspecs are, with no CharaSpec row check: the levels' planner sets load the place's override-animation packs by name (`CharaSpec_PC0000_00_Cloud_StandardOA04`) |
| `rows` | a row with another row's content, but its `keep` fields (an ability's UniqueId: the save's progress) |
| `values` | a field of rows set: a name or a text (as the field is), a number, a list of names |
| `requires_paks`, `note`, `enabled` | as elsewhere |

A table is a table's name (`PlayerTable`: `/Game/DataObject/Resident/PlayerTable`) or the object path of one of the
game's data objects (under `/Game/DataObject/`, its class one of the EndDataObject module's: the mod calls the
table getter of their vtable). A character plays with every table it needs or not at all: nothing is copied until
they are all loaded (twice a second at the start, 5 minutes at most; no copy is made again for each try), a table that
cannot be copied keeps the place its own (the page says why), and a copy the game was never given is freed. The
default `names_in` tables but PlayerTable are not waited for: one the game has not loaded keeps its names. Its
`player` must be a BattlePlayerParameter row. The lists the mod switched for a table's rows (compat rows'
`abilities`) follow the rows into a copy and back. Once the map has loaded, the status of the member whose place
changed hands is recalculated (its battle menu from the row its place plays now: the game's `BPSetPlayerExperience`
with its own EXP, as for a pack switch; not for a player row whose compat row says `"refresh_abilities": false`).

3.16.1: at the start a character also waits for the tables it reads (CharaSpec, BattlePlayerParameter for its
`player`), and a table it can do without that the game had not loaded yet goes in at the next map load once it is
there (3.16.0 left it out for the whole session). A data object not found is looked for again a second later at the
soonest (UE4SS finds an object by its path by going through the whole object array here, some 20 ms a look, and the
CHARACTER page builds its lines often). The CLOUD moveset's `"weapon_socket"`: the Buster Sword in Cloud's right hand
in battle. A skin's `weapon_field_socket` is looked at four times a second in the field (the game puts the weapon back
in the hand now and then, and it showed there for up to a second). Install: `Tools\CloudCharacter\run_cacs3161_install.cmd`
(the game mod, and the forms files with the moveset's socket).

3.16.2: a character's changes also go into the game's own rows, in place: the game spawns a party member from the
PlayerTable row it found as it started, before any copy of the mod's was there, so 3.16.0 and 3.16.1 put CLOUD's
copies in and the game still spawned Cloud's own CharaSpec row (Sephiroth). The bytes there before go back when the
place is its own again; a table whose rows the game maps read-only (a container stored without compression) keeps the
changes in the copy alone (the log: "the game's own rows have their changes too: PlayerTable 3 field(s), ..."). The
lists a compat row switches for a BattlePlayerParameter row are handed out through the game's own row and through any
copy of it alike (3.16.0 moved them into the copy). A CHARACTER page choice goes in at once (chosen in battle: once it
is over): the member spawns as it the next time the game spawns the party (load a save, or go into another area). When
the character you control plays a place a character has, the log says which CharaSpec row it spawned (a WARNING, with
what the place's PlayerTable row names, when it is the place's own). Install: `Tools\CloudCharacter\run_cacs3162_install.cmd`.

3.16.3: a place given back to its own on the CHARACTER page goes back at once: the game's rows get their bytes back
and the party member spawns as the place's own as you close the menu (3.16.0 - 3.16.2 kept CLOUD in Cloud's place:
"its own" looked like the choices already put in, so nothing went back). The first spawn there afterwards is in the
log ("Characters: Cloud's place is its own again (PC0000_00_Cloud_Standard, its own CharaSpec row)", or a WARNING
when the character's row still spawned). CreateACharacterCloud_P (its update with 3.16.3, installed by
`Tools\CloudCharacter\run_cloud_voicefix.cmd`) has CLOUD's packs load the game's own voice alone: the one before
loaded the English, French and German copies of Cloud's voice and lip sync with it (he spoke another language, and
the game could crash in its sound thread or as it started). Install: `Tools\CloudCharacter\run_cacs3163_install.cmd`.

3.21.0: several characters for one place, each with its own compat rows.
`FullyPlayableCreateACharacterSystemExperience.json` offers YOUNG SEPHIROTH, SEPHIROTH, VINCENT and SORA for Cloud's
place (Cloud is the place's own), each on CharaSpec rows, packs, blueprints, AI, weapons and voice of its own
(`FullyPlayableCreateACharacterSystemExperience_P`); picking either Sephiroth also puts Evil Cloud in Sephiroth's place
and Bizarro Sephiroth in Alexander's. A compat row of a character's own CharaSpec rows (its `charaspecs` values) plays
its abilities while the character has the place and waits while it has not (3.16 - 3.20 stood every compat row of the
place's player row down while any character had the place: `AbilityRowFor`, `OwnerOfRow`, `HoldingPlaces`); several
characters can own one row (both Sephiroths own Evil Cloud's): it plays while any of them has a place, and a
character's rows may list abilities for another player row than its place's (Evil Cloud's `pt_Sephiroth`:
`PlayersOf`). What a character's rows listed (lists, weapon abilities, pages) goes with it when it leaves. A level's own
table (`/Game/DataObject/Field/...`) never outlives its level: given back before a map loads
(`TableCopies::RestoreLevelTables`), let go without a write when the game unloads its area (`DropDeadLevelTables`), and
nothing is written to one whose data object is gone (`TableCopies::TableAlive`). `tests/owners_sim.sh` runs the
ability-row choice on a compat folder for each character.

**CLOUD** (CloudCharacter.json, CreateACharacterCloud_P, and the Fully Playable (Young) Sephiroth data container's
3.16.0 update): the game's own Cloud as a character of his own, so he can play again with Fully Playable (Young)
Sephiroth installed. CreateACharacterCloud_P holds the game's Cloud under new names: his AnimBlueprint
`PC0000_00_Cloud_Standard_CACS_Animation` (the AnimBlueprint Maker's copy of Cloud's, Control Rig kept), his character
blueprints (`PC0000_00_Cloud_Standard_CACS` with it, his outfits' 04, 08, 09, 10 and 12 with it as their parent), his
CharaSpec packs (each outfit's, its `_NoBattle` and `_Reserve`, their minigame `OA00`-`OA19` and voice `SFV00`-`SFV02`
packs: 432) and his weapons' (the game's own weapons), and the game's CharaPopPack and CharaPopAsset with rows for them.
The data container gets his CharaSpec rows (`PC0000_xx_..._CACS`), `pt_Cloud_CACS` (the game's own pt_Cloud) and the
`_CACS` rows of the 11 abilities it gives Sephiroth's moves (Cloud's weapon abilities and limits, the game's own), and
his packs in Effect2SoundTable. While CLOUD has the place: his CharaSpec rows wherever the game names Cloud's, pt_Cloud
and those abilities the game's own again (their UniqueIds kept), his battle voice (PlannerEvent's 106 battle lines,
PlannerEventVoiceList's three banks) and the weapon row the data container changed. The SephirothForms Lua mod and
Sephiroth's forms leave him alone (they are for Cloud's own rows). Not covered: the Zack-outfit Age21 and wet outfits
(18, 19, 23) and characters a map or a cutscene spawns by name instead of through those tables.

## KawaiiPhysics (3.14.0)

KawaiiPhysics (pafuhana1213's hair / cloth / accessory physics node, MIT) runs in the game through the UE4SS mod.
`src/KawaiiSolver.hpp` is the node itself, engine-free: KawaiiPhysics **1.7.0** (the UE 4.26 release) with the newest
KawaiiPhysics' features fused in (fixed substepping with pose interpolation, component / world / base-bone simulation
spaces, additional root bones, bone subdivision, XPBD bone constraints with bridge points and their feedback, tapered
capsules, boxes, warm-up, `TeleportPhysics` teleports, `SkelCompMoveScale`, the gravity options, the simple external
force). The same solver is meant for the editor's node (the preview then matches the game).

A file's `"kawaii"` entries (`SkelCompatCore.hpp` `KawaiiSet` / `KawaiiNode`, parsed with every KawaiiPhysics setting in
snake_case; README.txt lists them) name models and the nodes that run on every mesh showing one of them:

```json
{"schema": "RebirthSkelCompat/1", "kawaii": [{
  "models": ["/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13.PC0010_13"],
  "requires_paks": ["YoungSephiroth_P"],
  "disable_bonamik": ["PC0010_13_BNM"],
  "nodes": [{"name": "hair", "root_bone": "C_HairF_a_Phy", "additional_root_bones": ["C_HairB_a_Phy"],
             "damping": 0.15, "stiffness": 0.12, "radius": 0.75, "dummy_bone_length": 4,
             "spheres": [{"bone": "C_Head_a", "offset": [8.57, 2.27, 0], "radius": 6.51}]}]}]}
```

How it runs (`Forms::KawaiiRt`):

* `USkeletalMeshComponent::PostAnimEvaluation` calls the anim instance's `PostEvaluateAnimation`, which calls
  `BlueprintPostEvaluateAnimation` through `ProcessEvent` before `bNeedToFlipSpaceBaseBuffers` and the flip
  (`FinalizeAnimationUpdate`). The mod's ProcessEvent callback takes that call (the function, or an AnimBlueprint's own of
  that name: one 8-byte read of `NamePrivate` per ProcessEvent) for the component's own `AnimScriptInstance` only.
* The new pose is then in `ComponentSpaceTransformsArray[CurrentEditableComponentTransforms]`. The two arrays and the
  indices are found on the first mesh of a kawaii model: the two `TArray<FTransform>` of the mesh's bone count whose "read"
  one holds what `GetBoneLocation(bone, ComponentSpace)` answers (3.14.1: the buffer's own floats; 3.14.0 compared
  `GetSocketTransform(bone, RTS_Component)`, which goes through the world and back and, far from the map's origin, missed
  by more than it allowed, so KawaiiPhysics stayed off), with the editable / read indices after them (UE 4.26: arrays,
  `PreviousBoneVisibilityStates`, `PreviousComponentSpaceTransformsArray`, then the indices, +0x40). A search that finds
  nothing in 30 frames tries again 5 s later (3.14.0 gave up for good).
* The nodes read that buffer (all bones, 48 bytes each), run with `K2_GetComponentToWorld` and
  `GetWorldDeltaSeconds` x the actor's `CustomTimeDilation`, and write the buffer back; the bones below a moved bone keep
  their local transforms (`Kawaii::CarryToChildren`). The game then flips it to the renderer, the sockets' attachments and
  the physics bodies. A mesh not evaluated for 0.5 s of the game's time (`GetTimeSeconds`: a pause does not count) starts again from its pose.
* The bone table comes from the mesh's `FReferenceSkeleton` (final bone info, final ref pose: the bones' lengths).
* Bonamik: a model's BNMs are its `SQEX_KBD_AssetUserData.BonamikDataList`; the character's `SQEX_KBD_Component` (attached
  to the mesh, else the only one on the actor whose mesh this is) runs them. 3.14.4: `"disable_bonamik"` takes them off the
  model itself as it loads (the mesh's `PostLoad` hook: `BonamikDataList` and each `OverrideBonamikDataList[].BonamikDataList`
  in place, the named BNMs or all of them; `KineDriverDataList` and `PostKineDriverDataList` stay; the BNMs taken are rooted),
  so no `SQEX_KBD_Component` ever runs them on that model, as with Young Sephiroth's pak, whose model has none. A BNM the
  component runs writes its bones after `BlueprintPostEvaluateAnimation`, its groups on or off (3.14.3's log on Sephiroth's
  skins: "at the frame's end the result still in its buffer 0 of 99"), so the nodes' result never showed on such a model.
  Before 3.14.4, and still for a model loaded before the mod started, `"disable_bonamik"` turns off the groups of the
  named BNMs (`SQEX_BonamikAsset.mGroups[].m_GroupName` and its bodies' `mGroupName`; groups a BNM left on has too stay on)
  with `SQEX_Bonamik_TurnOff(false, Groups, 0)`, again every 250 ms (anim notifies turn groups on), and `TurnOn(Groups,
  0.2)` when the model goes. `"skip_bonamik_bones"` keeps the bones of the BNMs left on (their bodies that are not
  `m_IsKinematic`, by `mParentName`) out of the chains.
* Log `Kawaii: ...`; F9 report "KawaiiPhysics (3.14.0)".
* 3.14.1: the pose buffers found by `GetBoneLocation` (exact wherever the character is), and looked for again every 5 s
  when not found.
* 3.14.3: both pose buffers (`ComponentSpaceTransformsArray[2]`): the nodes read and write the one the game has just
  made, told by the bones they wrote into each ("marks"), the index learned from them; update rate optimizations off on a
  Kawaii mesh; a check line in the log every 2 s (then every minute).
* 3.14.4: the BNMs taken off the model as it loads (above); the log says "Kawaii: <model>: its Bonamik taken off the model
  as it loaded: <BNMs>", and the mesh's line "Bonamik: taken off the model as it loaded (<BNMs>)".
* 3.14.5: `"disable_kinedriver"` (true or KDI names) takes `KineDriverDataList` and `PostKineDriverDataList` off the model
  the same way. The `SQEX_KBD_Component` runs a model's KDIs after `BlueprintPostEvaluateAnimation` too: `PC0010_10_KDI`
  writes 60 `_Phy` bones (hair, collar, feathers) and some 200 helper bones (`*_Spo`, `*_Kdi`), its `_Extra1` (the post
  KineDriver) 40 long-hair `_Phy` bones (`TargetOricnsBody`). 3.14.4's log on the Sephiroth skins with their BNMs off:
  "the result still in its buffer 0 of 72". The check lines now also give the share of the written bones still as
  written at the frame's end.
* 3.14.2: 64 nodes a model (16 before). Fixed substeps (`"use_fixed_substepping"`, on by default): a frame shorter than a
  step runs none, and the bones are now shown carried by their pose's move since the last step (above the step rate the
  chains shook as they caught up with every step: 0.5 - 0.7 cm/frame^2 at 90 - 240 fps in `tests/ys_jitter.cpp`, now
  0.01 - 0.05; with `"use_fixed_substepping": false` it is 0). The log says why `GetBoneLocation` was not used when the
  buffers were found by `GetSocketTransform`.

* 3.17.0: KawaiiPhysics' **sync bones** (`"sync_bones"`, `AnimNode_KawaiiPhysicsSyncBone.cpp` ported: an animated bone
  whose move from its reference pose goes onto the pose of the chain bones below its target roots, each kept at its length
  from its parent, before the simulation; `Kawaii::Skeleton::RefLocation` is the reference pose in the component's space,
  built from the mesh's final ref pose). A chain's root is never moved (KawaiiPhysics skips it once it has simulated a
  frame; on its first frame it moved it), and a bone the sync moved is turned toward its child from its animated direction
  (KawaiiPhysics turns it from the moved pose's, which kinks a chain moved far). `"interpolate_limits_in_substeps"` (on):
  with fixed substeps, each step's collision shapes between their places at the last frame's end and this frame's (as the
  pose is); `"keep_collision_side"` (off): a bone found inside a shape on the other side of its axis than it was is put
  back out on its side. `tools/kawaii_feet_sync.py` / `make_kawaii_feet_sync.py` give the coats and mantles of the kawaii
  files sync bones (each chain the knee on its side, by where it hangs: front, side, back) and, below the knees, the feet
  as colliders; `tests/kick_run.cpp`, `kick_check.py` (the cloth's vertices in a leg, and through one between two frames),
  `kick_view.py` and `kick_trace.py` measure it (Rebirth Sephiroth's coat on Remake Sephiroth's run: through a leg in 82
  frames of 330, now 9). Install: `Tools\RebirthSkelCompat\run_cacs3170_install.cmd`.
* 3.18.0 (skins that carry their own moves): a skin.json's `"pack"` (an animation pack its compat file builds: a form's,
  a `"movesets"` entry's or a `"battle"` source `"as"` it, e.g. `Battle10`) plays in the normal form and each form with no
  pack of its own while the skin is worn, the battle's base pack too (`Forms::AsWorn`, `Forms::SkinPackUsable`), and its
  `"sets"` (`{"Neutral00": "Neutral10"}`) are a form's sets in the normal form and each form with no sets of its own; a field
  twin (`<row>_NoBattle`) finds such a set in its row's pack (`PackSets::Prepare`). Editor 1.21's data object skins have
  Pack and Sets and write them into skin.json (only when set: other skins keep their bytes). The CRISIS CORE skins carry
  Battle10 and Neutral10 (Crisis Core's field idle, walk, run and dash), the Dissidia NT skins Battle12.
* 3.18.0: the rest of **KawaiiPhysics 1.21**. `KawaiiSolver.hpp`: external forces (`"external_forces"`: basic, gravity,
  curve, wind, procedural wind with its gusts, presets and shared winds), the node's wind (`"enable_wind"`), settings
  multipliers, transient forces and gusts, the alpha blend (`"alpha"`), tags (`"kawaii_physics_tag"`), the reusable sets
  (`"kawaii_limits_sets"`, `"kawaii_bone_constraints_sets"` with their regex patterns, `"kawaii_presets"`,
  `"kawaii_wind_presets"`; `SkelCompatCore.hpp`'s `ResolveKawaiiSets` puts them on the nodes), mirrored shapes
  (`"mirror_data_table_for_limits"`), the shapes from outside a node (the floor, the level's simple collision with convex
  hulls, other meshes' shared shapes) and world collision sweeps. `KawaiiRt::World` in the game mod gives the nodes the
  game's world (`Kawaii::Environment`): the level's `WindDirectionalSource` actors (FScene::GetWindParameters) and the
  entry's `"world_wind"`, the character's gravity, the floor (`CharacterMovement.CurrentFloor`, else a trace), the static
  meshes' collision near the mesh (`SphereOverlapComponents`, each `UBodySetup`'s AggGeom), sphere sweeps
  (`SphereTraceSingleForObjects`, a budget a frame), shared shapes and winds within a character's family (its actor and
  what it is attached to), the model's physics asset's bodies (`"physics_asset_for_limits"`) and the entry's
  `"animation_triggers"` (KawaiiPhysics' AnimNotifies, by the montage the mesh's anim instance plays and its time). A mesh
  whose nodes use none of it runs as in 3.17.0 (no world passed). Where it differs from 1.21: the gravity force's
  character scale is the size of `GetGravityZ` (1.21 multiplies by the signed value: up), the random numbers are UE 5's
  `FRandomStream` seeded by each node's root bone, a convex hull in the level is its bounding box (1.21's BoundingBox
  fallback), instanced static meshes are not gathered, triggers go by montages (not the anim graph's own animations), and a
  physics asset by path is used when the game has loaded it. The End editor's KawaiiPhysics plugin 1.11 has all of it in
  the node (Export / Import For Game). Install: `Tools\RebirthSkelCompat\run_cacs3180_install.cmd` (it also runs
  3.17.0's kawaii JSON step, which was not installed yet).

Young Sephiroth: `compat/YoungSephirothKawaii.json`, made by `tools/make_ys_kawaii.py` from his rig (342 bones, the wing's
included) and his old BNMs' specs: hair (13 strands), coat (11 strips, leg capsules and the hip sphere), collar (4 pieces
with dummy points) and wing (its 11 feathers from their `a_Phy` bones down, the 36 bones the wing BNM swung). 3.14.2: a
node a chain (39), each chain's stiffness, damping, world damping, gravity and limit angle a little off its group's (an
MD5 of its root bone's name: the same every build), so the chains swing apart; nothing is tied (3.14.0's 30 coat ties
made the coat one sheet); every node simulated every frame. His model has no BNM: `YoungSephiroth_P`'s `PC0010_13` has its Bonamik list emptied (`fpys/tools/bnm_off.py`,
installed by `run_ys_kawaii_wing_install.cmd`; the End project's copy lists none either) and keeps `PC0010_13_KDI`, the
wing's KineDriver (it drives only wing bones: the spokes, helper bones and feathers A-D's bends). KawaiiPhysics runs on
the pose the game has made, the KDI's work included, so each chain swings about the pose the KDI gives it. `tests/kawaii_tests.cpp` checks the solver (math, rest, inertia,
teleports, gravity, every shape, exclude / skip, constraints, subdivision, spaces, substeps, warm-up, the config);
`tests/ys_sim.cpp` runs his entry on his reference pose while he runs, spins and jumps (finite, lengths kept, settles).

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

**1.16.1**: a hit's Damage Source ID goes into the damage notify's `DamageSourceIDs` (alone), the list the game's own
animations use for theirs, a `?_NN` or a full ID; the older single `DamageSourceID` is left empty (1.16 and before put
the ID there, with its quotes, and emptied the list). Build the plugin and rebuild a form's moves to give them the change.

## Editor 1.17: the Skin Maker and the Parts Builder

### Skin Maker

**Window > Rebirth Skin Maker**, **right-click a Skeletal Mesh in the Content Browser > Create a Character Skin...**, or
**Open Skin Maker** on a data object (under Skins) opens a tab that makes one skin at a time from a model (`EndSkinMaker.cpp`):

* **Data Object**: where the skin is kept (its Skins). None picked: Save Skin keeps it in
  `/Game/RebirthSkelCompat/Skins/DO_Skins`, made the first time. **Skin**: one of the data object's skins to edit (the form
  is filled from it), or (new skin); Save Skin also finds the data object's skin of the same folder and updates it.
* **Name**, **Model**, **Folder** (advanced; empty: the name's letters and digits).
* **Characters** with **Add Character**: one CharaSpec row, or every row of a character (`PC0000_*`: all of Cloud's outfits,
  the slot the Fully Playable Sephiroth plays in), from the project's CharaSpec table (the game's object tools) and the
  rows the data object names. A new skin of a data object that has skins starts with its last skin's Characters and Family.
* **Worn At Once** (new, also on the data object's skins): off (the default), the skin is one of its characters' choices on
  the Customization screen's SKINS page (`"worn": false`); on, they wear it as the game starts.
* **Family**, **Keep Proportions**, **Proportion Bones**, **AnimBlueprint**; **Voice** with **Pick Voice** and **Weapon**
  with **Pick Weapon** (the voices and the weapons of the game's Customization catalog).
* **Meshes** (new, also on the data object's skins): model parts worn with the model, as a form wears them (3.11.2:
  `"meshes"`: mesh, socket, follow pose): a wing of its own. Their models of the project go into the skin.
* **Extra Assets**, **Author**, **Description**, **Game Directory**, **Install** (the data object's).

**Save Skin** puts it in the data object and saves it; **Build Skin** saves it, then builds only this skin
(`BuildOneSkinTo`: Build Skins for one skin; installed, and the skins container made anew from every installed skin;
close the game first). Also **Load Skin**, **New Skin**, **Open Model**, **Open Data Object**, **Show In Game**.

### Parts Builder

**Window > Rebirth Parts Builder** or **right-click a Skeletal Mesh > Make a Customization Part...** opens a tab with a form
and a preview of the part on a character, playing its animations the way the game plays them (Customization 3.11:
PutOnPart, Align, MoveParts; `EndPartsBuilder.cpp`):

* the part's component snapped to the character's **Bone** (a bone or a socket; **Pick Bone** lists the preview
  character's); every frame the part's own bone **Anchor** (empty: Bone; **Pick Anchor** lists the part's) is kept on
  it: the component placed by the inverse of the anchor's transform in the part's own space, then **Offset** (cm, in the
  bone's axes) and **Scale**. A yellow mark shows the character's bone, a blue one the part's anchor;
* **Sections** (the material slots shown, their numbers; empty: all) and the tint (**Tint Color** into **Tint Parameter**,
  **Tint Texture** into **Tint Texture Parameter**, on the slots shown);
* what it plays: with **Sync**, its own motion of the name of the one the character plays (`<Sync Folder>/<the
  character's set>/<name>`, then the game's set folders; Sync Folder empty: two folders above Idle's, as the game takes
  it), at the character's time; else the motion of **Preview Move** (one of its **Moves**: ability ID -> motion, what the
  game plays while the character uses that ability in battle); else **Idle**, looping.
* **Preview Character**, **Preview Animation** (an animation of the preview character's skeleton), **Preview Speed**,
  **Play / Pause**, **Restart**, **Frame**. The game directory and the preview are remembered.
* **Part** (one of the catalog's parts to edit), **Name**, **Id** (empty: from the name), **Model**, **For** with **Add For**
  (the models it is offered for, as patterns: `PC0010_*`), **Component Class**, **Game Directory**, **Assets Folder**.

**Save Part** puts it in the game's `customization\catalog.extra.json` (what make_customization_catalog.py merges in first
each time; from 3.12.1 a part there takes the place of a made one of the same id) and in `catalog.json` (what the game
reads as it starts), the old files kept as `.partsbuilder.bak`; start the game again to see it on the PARTS page.
**Build Part** first builds the part's own assets of this project (its model with its skeleton and physics asset, its
idle, its moves' and its synced motions, its tint texture; the game's assets and cooked copies are left out) into a
skin folder of their own, `skins\Part_<id>` (`"part": true`: no one wears it, and the catalog maker leaves it out of
the models), and the skins container, the animations given the game's ACL compression settings first (the game reads
every animation with them; saved, and said); then Save Part. Close the game first. **Remove Part** takes it out of both
catalog files (its assets stay in `skins\Part_<id>`).

skin.json gains `"meshes"`, `"worn"` and, for a part's assets, `"part"`. The plugin's copy of the game mod's rules
(`SkelCompatCore.hpp`, what Validate shows) is 3.12's, its clip times read without exceptions.

Build: close the editor, run `Tools\RebirthSkelCompat\run_build_plugin117.cmd` (copies the 1.17 sources into
`Plugins\RebirthSkelCompat`, the old ones into its `_mod_backups\before_117_<time>\`, then `build_plugin.py`).

## Editor 1.18: the AnimBlueprint Maker

A character on a skeleton of its own needs an AnimBlueprint made for that skeleton (a form's `"anim_class"`, a skin's
`"anim_blueprint"`, a character blueprint's AnimClass). The AnimBlueprint Maker makes one from one of the game's own
AnimBlueprints, a **template**: the template's cooked package under the new name, its skeleton the character's.
Everything the template does stays: the field and battle locomotion state machines, the moves player the game's actions
and abilities play through, inertialization, the slots, facial, the movement and sword expressions. The game's
AnimBlueprints take every animation from the character's animation sets (CharaSpec packs) by name, so nothing in one
names an animation of the template's character, and the same graph runs any character whose sets have those names.

**Window > Rebirth AnimBlueprint Maker**, or **right-click a Skeleton or a Skeletal Mesh in the Content Browser > Make a
Rebirth AnimBlueprint...** opens a tab (`EndAnimBlueprintMaker.cpp`):

* **Skeleton**: the character's skeleton (of the project, cooked into the character's mod: the game needs it at that
  path). **Name** (empty: the skeleton's character folder + `_Animation`, as the game names them:
  `/Game/Character/Player/PC0099_00_Hero/Model/PC0099_00_Skeleton` -> `PC0099_00_Hero_Animation`) and **Folder**
  (`/Game/BluePrint/Animation/Player`).
* **Template**: `cloud` (Cloud's player AnimBlueprint: most characters), `sephiroth`, `vincent` (a gun user's), or
  `monster` (the bosses' and summons' AnimBlueprint, Leviathan's: their locomotion state machine, the moves player,
  inertialization, the move slot, facial and movement expression, no Control Rig).
* **Keep Control Rig**: the player templates run the game's common human Control Rig (it places the hips and feet by the
  legs of a Rebirth human skeleton). Off (the default) its class is emptied, so the node passes the pose through; keep it
  only for a character on a Rebirth human skeleton with the game's bone names.
* **Container** (empty: `CACS_<Name>_P`), **Install** into `~mods\<Mods Folder>` (`CACS_AnimBlueprints`; refused while
  the game runs), **Game Directory**.

**Make AnimBlueprint** runs `Tools\RebirthSkelCompat\abp\make_cacs_abp.py` (Python 3: the py launcher, or python on the
PATH), shows what it did and fills **Anim Class** (`<Folder>/<Name>.<Name>_C`); **Copy Class Path** copies it, **Show
Container** opens `abp\out`. The same tool runs on its own: `py -3 make_cacs_abp.py --skeleton <path> [--name N]
[--template cloud] [--control-rig off] [--install]` (`--list` lists the templates; `abp\README.txt`).

The tool checks what it makes the way the Safer form's AnimBlueprint was made by hand (2026-10-15): from Vincent's
template with Safer's skeleton and the rig off, it writes that package byte for byte. The templates in `abp\templates`
are the game's own packages (taken from your game, not for sharing); the AnimBlueprint they make is a copy of the
game's, so it is not editable in the editor (editor 1.19's Make Editable AnimBlueprint makes one that is).

Build: close the editor, run `Tools\RebirthSkelCompat\run_build_plugin118.cmd` (copies the 1.18 sources into
`Plugins\RebirthSkelCompat` and the tool into `Tools\RebirthSkelCompat\abp`, the old files into
`C:\FF7R2UProj\_mod_backups\before_118_<time>\`, outside the Plugins folder so the editor does not find a second
plugin there, then `build_plugin.py`).

## Editor 1.19: editable AnimBlueprints

**Make Editable AnimBlueprint** (in the AnimBlueprint Maker) builds the template again as an AnimBlueprint of the
project, at `<Folder>/<Name>`, for the skeleton: an AnimBlueprint like any other, to open, edit (add states, change a
transition's rule or blend, put nodes of your own in the AnimGraph) and compile in the editor
(`EndAnimBlueprintTemplate.cpp`). **Cook For Game** then cooks it for the game into the container (`CACS_<Name>_P`,
installed into `~mods\<Mods Folder>` as Make AnimBlueprint's), and the class path is the same as Make AnimBlueprint's,
so a form's `"anim_class"` or a skin's `"anim_blueprint"` takes either. **Replace Existing** deletes an AnimBlueprint
already at that path first (off: the making stops); **Open When Made** opens it.

What it is built from: the template's cooked AnimBlueprint, decoded (`abp\templates\<AnimBlueprint>.template.json`):
* the AnimGraph: the game's End anim nodes as End's own AnimGraph nodes (End's editor module, `Source\ENDEditor`:
  `AnimGraphNode_EndBehaviorAction`, `_EndFacialPrimary` (the facial slot), `_EndFacialSecondary` (lip sync),
  `_EndInertialization`, `_EndCharacterMovementExpression`, `_EndSwordExpression` (Cloud's sheathed sword; it warns
  when the skeleton has no such bone), `_EndLocomotionSequencePlayer` and `_EndLocomotionBlendSpacePlayer` (asset players,
  so the transitions' "time remaining" rules use them; in the game they play the animation their Locomotion State has
  in the character's animation set, so their Sequence and Blend Space stay empty)) with every setting, and the engine's
  own nodes (Slot, the space conversions, Local Ref Pose, the state machine);
* the state machine (Locomotion): its 17 states (each state's graph and player node), 11 conduits and every transition
  (73 in Cloud's) with its priority, crossfade, blend mode and Inertialization, and its rule as nodes: the requested and
  current locomotion state and behavior mode compared with enum == / !=, the relevant animation's time remaining and
  time fraction of the state the transition leaves, the animation groups the character's animation set gives
  (`GetLocomotionAnimGroupFromCache`), AND, OR, Select Float and selects on the behavior mode;
* the blend space's X and Y from Blend Input Direction and Blend Input Speed, the Idle state's SetStateIdle notify, and
  the class defaults (bone blend rate groups, idle and walk actions, weapon sockets, the lip maps of the project).

The templates (both Make AnimBlueprint and Make Editable AnimBlueprint): `cloud`, `sephiroth`, `vincent`, `monster`, and
those `abp\templates\templates.json` lists, each a character's own AnimBlueprint (its cooked package and its decoded
`.template.json` next to it): `barret`, `tifa`, `aerith`, `redxiii` (on four legs, with a Modify Bone node), `yuffie`,
`caitsith`, `moogle` (the big moogle Cait Sith rides), `zack`, `cid`. Every one uses only the AnimGraph nodes above;
Red XIII, Cait Sith and the moogle have their own locomotion (62 transitions, as the monsters'), the others Cloud's
(73). More: add `{"key", "package", "label"}` to templates.json with the two files (no new build).

Left out: the game's Control Rig node (its rig is one of the game's Control Rig blueprints, which the editor cannot make),
with the space conversion pair it leaves (Cloud's, Sephiroth's and Vincent's AnimGraphs end in it; off is Make
AnimBlueprint's default too).

From Python (an editor script): `unreal.EndAnimBlueprintTemplateLibrary.make_editable_anim_blueprint(template,
skeleton, package_path, replace_existing)` and `.cook_anim_blueprint_container(package_path, container, out_dir)` (JSON
reports); `abp\build_abp_template.py` runs a list of them in a commandlet.

Build: close the editor, run `Tools\RebirthSkelCompat\run_build_editor119.cmd`: it copies the 1.19 sources into the
plugin and into `Source\ENDEditor` (its new nodes, and its Build.cs with the AnimGraph modules), the tools into
`Tools\RebirthSkelCompat\abp`, the old files into `C:\FF7R2UProj\_mod_backups\before_119_<time>\`; builds ENDEditor
and the plugin (`build_editor_module.py`); then tests: Cloud's template made for Cloud's own skeleton at his
AnimBlueprint's own path and cooked into `abp\out\CACS_AnimTemplateTest_P` (not installed), and the other three
templates made and compiled in `/Game/RebirthSkelCompat/AnimTemplateTest`.

The test checked (`compare_abp.py`: the cooked test container decoded and compared with the game's AnimBlueprint):
the AnimGraph chain and every node's settings, the 28 states and conduits, the 73 transitions with their rules, the
bindings and the 15 class defaults are the game's. What differs: the left-out Control Rig node, and multithreaded
animation update is off (the editor sees `GetLocomotionAnimGroupFromCache` as not thread-safe: the warnings it gives).
How the templates write a setting, for the editor's ImportText: a name or a string on its own without quotes (quoted,
the quotes would be part of the name: a Slot node's `DefaultSlot`), an empty array as no text (`()` makes one empty
element), an empty map or set as `()`; a struct's Transient members (`InputAlphaBoolBlend`'s `bInitialized` and
`AlphaBlend`) not at all. `run_abp_template_retest.cmd` runs the test alone (the test's AnimBlueprints of a run before
are moved to `C:\FF7R2UProj\_mod_backups\abp_test_before_<time>\` first: an editor commandlet cannot delete them,
and Replace Existing refuses there); `run_abp_template_test_install.cmd` puts the checked test container into
`~mods` for the in-game test (its md5s checked first), `run_abp_template_test_remove.cmd` moves it out again.

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
