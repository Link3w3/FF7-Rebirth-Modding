# Create a Character System

Make playable characters for FINAL FANTASY VII REBIRTH (formerly RebirthSkelCompat; folders, files and code
keep that name). At its core, KH3-style skeleton compatibility: meshes on a *receiving skeleton* play the
animations (and AnimBlueprints) of an *animation skeleton*, for any number of skeletons, in any direction.

| Part | Where | What |
|---|---|---|
| UE4SS C++ mod | `src/` -> game `ue4ss\Mods\RebirthSkelCompat\dlls\main.dll` | Adopts animations onto receiving skeletons (`"animations"`), rebinds receiving meshes inside `USkeletalMesh::PostLoad` (`"mesh"`), gathers skeletons that share animations on a hub (`"family"`, 3.0), rebuilds a character's animation sets from other characters' sets (`"animation_sets"`, 3.1), late-rebinds meshes that were already loaded, repairs refused AnimBlueprints, F9 report. |
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
