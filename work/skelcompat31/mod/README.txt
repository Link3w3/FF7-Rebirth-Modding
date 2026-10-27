RebirthSkelCompat 3.2.2 - KH3-style skeleton compatibility for FINAL FANTASY VII REBIRTH
UE4SS C++ mod (built against the installed UE4SS 3.0.1 c0a8d4c)

WHAT IT DOES
  A pair says: this receiving skeleton plays the animations of these animation skeletons.
  Any number of pairs, in any direction. Three ways to set one up, chosen with "method":

  "animations" (default, KH3 mode)
    Every animation authored on an animation skeleton is rewritten while it loads onto the
    receiving skeleton: each track moves to the receiving bone with the same name, curves are
    matched by name, and the animation then belongs to the receiving skeleton. Characters keep
    their own skeleton, AnimBlueprint, physics and own animations, and can also play the adopted
    ones (for example Cloud's Neutral20 swim/climb/chocobo set listed in Sephiroth's CharaSpec).
    Bones placed under a different parent in the two rigs (hair, belts, coat tails) and bones the
    receiving skeleton lacks are not driven: they keep their own pose or physics.
    An animation belongs to one skeleton at a time, so an adopted animation leaves the animation
    skeleton: this is the method for a swap pak (Sephiroth over Cloud), where the original character
    is not around. Use "adopt_paths" to adopt only some folders. When skeletons need to SHARE
    animations instead, the mod makes a family (below) by itself.
    Montages, composites and blend spaces move only after every animation they play has moved
    (those animations follow them even outside adopt_paths); until then the log says "Waiting".
    Animations that were already loaded before the pair became active move at a safe moment
    (the next map load, or right after the world tick of a frame).

  "mesh"
    Meshes on the receiving skeleton are bound, while they load, to the animation skeleton and
    run its AnimBlueprints (for a custom mesh spawned by a character Blueprint of the animation
    skeleton, such as a Dresscode outfit). Nothing on disk is changed.
    A rebound mesh keeps the sockets of its own skeleton (weapons and effects stay on the sockets
    made for its body); switch that off with "carry_sockets": false.
    The meshes follow adopted animations: when an "animations" pair or a family takes all animations
    of the animation skeleton, they are bound to the skeleton that has them now, and the log says
    "follow the animations of ... to ...". So an outfit pair made for Cloud keeps working under a
    swap mod.
    When the receiving skeleton is a game character's own skeleton, that character's game meshes
    change everywhere the game uses them: if the character shows up in the story with its own
    AnimBlueprint, it T-poses (its animations stay on its own skeleton). Use a family for that, or
    your own copy of the mesh and skeleton.

  "family" (new in 3.0: unlimited, both ways)
    Every listed skeleton plays the animations of every other one, and its own: "Vincent and
    Sephiroth play Cloud's animations, and Cloud plays theirs". The family gathers on one HUB
    skeleton: every animation of the other members is adopted onto the hub, and every mesh of the
    other members is rebound to the hub. Then any member's character can play any member's
    animations, with its own AnimBlueprint or with the hub's (a member in the hub character's slot).
    The hub's own characters and animations are untouched, so make the main character the hub.
    Bones of a member that the hub lacks (or places under another parent) are not driven by any
    animation: they keep their own pose or physics. For Rebirth's player characters these are
    almost only physics, helper and accessory bones (_Phy, _Spo, _End, _Kdi); the body, fingers and
    face carry over. A member mesh keeps the sockets of its own skeleton.
    The engine runs an AnimBlueprint only on meshes of the skeleton it was made for, so the AnimBlueprints
    made for a member move to the hub as well (3.2.1): a member character that keeps its own Blueprint and
    AnimBlueprint (Vincent's Blueprint in Cloud's slot) animates on the hub instead of standing in a T-pose.
    The log says "AnimBlueprint ... now runs on <hub>".
    You can write a family directly, or just write the pairs you want: "animations" pairs that would
    otherwise fight over the same animations become a family by themselves:
      * reverse pairs (Sephiroth plays Cloud's, Cloud plays Sephiroth's) and chains;
      * two pairs that want the same animations of one skeleton (Vincent and Sephiroth both take
        Cloud's; with adopt_paths, only when their folders overlap);
      * "receiving_skeletons" with several skeletons on an "animations" pair.
    Every pair connected to those through a shared skeleton joins the same family. The log says
    "family of <hub>" and lists the members.
    The hub: the one named with "hub" (or the first skeleton of a "family" entry); otherwise the
    skeleton whose animations the most pairs want, then one that receives none, then the receiving
    skeleton of the first pair. The hub may also be a skeleton of your own that is not a member
    (a "union" skeleton with the bones of every member), then nothing stays on its own skeleton.

  The methods combine: a custom Sephiroth mesh on its own skeleton can be rebound ("mesh") onto
  Sephiroth's skeleton, which in turn adopts Cloud's animations ("animations") or is a family member.

ANIMATION SET ROWS (new in 3.1): which animations a character uses
  Pairs and families decide which skeleton can play which animations. Which animations a character
  actually plays comes from its animation sets: the game asks for animations by name ("B_Atk01_0",
  "N_Idle01_1", ...) in the sets its CharaSpec pack lists (Battle00, Battle01, Neutral00, Neutral20,
  Emotion00, Facial00, ...). A character put in another one's slot (Vincent over Cloud) is asked for
  the names of the character whose slot it took; every name its own sets lack plays nothing (T-pose,
  attacks that never start, no swimming or climbing animations).
  An "animation_sets" row rebuilds a character's sets while its pack loads:
    "battle"   where the Battle* sets come from, in order of preference: the first source that has an
               animation name wins. A folder (/Game/Motion/Player/PC0011_Vincent: each set of that
               folder fills the set of the same name) or one set (/Game/.../Battle00.Battle00).
    "field"    the same for every other set (Neutral*, Emotion*, Facial*): walking, running, swimming,
               emotes, faces.
    "moves"    one chosen animation under one name, for moves whose names differ between characters,
               e.g. Rufus's or Biggs's gun animations for Cloud's attacks:
                 { "key": "B_NAttack01_0", "animation": "/Game/Motion/.../B_Shot01" }
                     every set that has that name
                 { "set": "Battle00", "key": "B_NAttack01_0", "animation": "/Game/Motion/.../B_Shot01" }
                     that set only (may also add the name)
               "animation" may be an array: those animations play one after another as one move (3.2),
               e.g. the aim, fire and recover pieces of a shot.
               A move may also carry "build": { "from": ..., "shot": true, "hit_at": 0.05 } and the row
               "build_folder" / "shot_effects": those are for the editor's Build Moves (it makes the
               animation "animation" names, with the game's notifies for that name); the mod skips them.
    Whatever the pack listed fills in after your sources, so nothing it had is lost.
  The animations still have to be playable by the character's mesh: animations of another skeleton
  need a pair or a family (Vincent over Cloud: a family of Cloud and Vincent with Cloud as hub).
  "cutscene": cutscenes play the slot owner's animations directly on the mesh, so the mesh has to sit
  on that skeleton. "skeleton": "<the character's own skeleton>", "cutscene": "<the skeleton whose
  cutscenes it plays>" makes that family (the cutscene skeleton is the hub).
  "field_actions" (ladders, crawl spaces, ledges, ...): the game picks those by the CharaSpec row's
  AnimationSetParentFolder (PC0000_Cloud, PC0011_Vincent, ...). A character with no field-action
  animations of its own needs another character's folder there. That value lives in the CharaSpec, so
  the Skeleton Compatibility data object writes it into your CharaSpec table; at run time the row only
  records it.
  The sources and move animations are loaded when the first map loads and stay in memory, so a row
  with many big folders costs memory. The log ("Animation sets ...") and the F9 report say what each
  row found and what each pack got.

AUTO MATCH, LIMIT BREAKS, SOCKETS, PROPORTIONS (new in 3.2)
  "auto": use another character's set without listing moves one by one. A battle or field source with
  "auto" fills the character's attack names from that set:
      { "from": "/Game/Motion/Enemy/EB2020_Elena/Battle00", "auto": true, "only": ["Shot"] }
  The names the game asks for are those of the row's ordinary sources (the character's own set, the slot
  owner's, the pack's). For each attack name still open when the auto source's turn comes:
    1. the same name;
    2. another variant of the same move (B_Walk01_0_L0 <- B_Walk01_0);
    3. an attack of the same kind (ground for ground, air for air) with the closest length. Every attack
       of the source is used once before any is used again. A move cut into short pieces (aim, fire,
       recover: B_AtkShot02_0, _1, _2) is offered whole: its pieces play one after another.
  "auto": true / "attacks"  normal and mode attacks, counters, air attacks, abilities (B_AtkBurst*) and
                            limit breaks (B_AtkLimit*)
          "basic"           normal and mode attacks, counters and air attacks; abilities and limits stay
          "all"             the whole set: every name it has wins (walking, damage, idles, ...), then the
                            attacks it lacks are matched as above
          false             same names only (3.1)
  "only": ["Shot", "Gun"]   the auto match uses only the source's animations with one of these words in
                            their name (any case), e.g. to keep a gunner's kicks and tonfa swings out
  Put the auto source BEFORE the character's own folder: a source only fills names no source before it
  filled. A motion folder as auto source fills a set it lacks (Battle01) from its Battle00; a single set
  fills its own name, or the one named with "as". "moves" and "limit_breaks" win over auto picks. The
  log lists every pick ("auto-matched"); copy one into "moves" to change it.

  "limit_breaks": [ <limit 1>, <limit 2>, ... ]  the animation each limit break plays (B_AtkLimit01_0,
  B_AtkLimit02_0, ...): an animation path, or an array of them played one after another; null keeps that
  limit as it is (its own, or what "auto" picks). A move of the same name wins.

  "sockets": [ { "socket": "Attach_Weapon01", "use": "Attach_Weapon_Right01" } ]  socket stand-ins on the
  character's meshes (needs "skeleton"). The game attaches weapons and props to sockets by name; a body
  that lacks one gets the weapon at its feet. A stand-in is a copy of "use" (a socket of the character,
  or one of its bones) under the missing name, made while each mesh loads. For a character in Cloud's
  slot: Attach_Weapon01 (Cloud's back holster) -> Attach_Weapon_Right01 (in the right hand) or
  Attach_Weapon_Right02 (a hip holster, where the body has one).

  "proportions": true  every body keeps its own bone lengths while it plays animations made for another
  body: spine, arms, legs and fingers take their length from the character's own mesh, the pelvis height
  is scaled per body (feet stay on the ground; 3.2.2 - 3.2.1 left it as animated), everything else (root,
  face, weapons, physics and helper bones) plays as animated. On a row it applies to every pair and family of the row's "skeleton"; on a
  family, to every member (the hub skeleton gets the settings). Takes effect from the next map load.

  "override": true  puts the row before the character's rows from other files (a test file over a mod's
  own row): its sources come first, and its moves, field actions and sockets win.

WEAPONS: another weapon in a character's hands (editor 1.6)
  A weapon has a CharaSpec pack (CharaSpec_WE0000_00_Cloud_BusterSword: the blueprint that spawns, plus the
  effects and sounds that load with it) and a CharaSpec row (its model, and the same effects and sounds). A swap
  pak that changes only the packs (Cloud's swords spawn Vincent's gun) leaves the rows describing the old weapon,
  and then every cutscene with that weapon waits for ever before it starts. Like a character's blueprint and
  model, a weapon's pack and row have to agree. That is not a skeleton problem, so this mod cannot fix it in game;
  the Skeleton Compatibility data object fixes the rows in your project:
    Weapon Swaps: Weapons = the replaced weapons' CharaSpec rows ("WE0000_*" is every one of Cloud's),
                  New Weapon = the weapon that takes their place (WE0011_00_Vincent_Quiksilver),
                  Requires Paks = your swap pak.
    Apply To CharaSpec (Apply To Skeletons does it too) writes each replaced row: the new weapon's model, the new
    weapon in its SharedCharaSpecList, and the effects and sounds its pack loads. Each replaced weapon's pack in
    your project must spawn the new weapon (Asset Class List); rows whose pack does not are left alone and listed.
    Cook the CharaSpec table with your pak.
  Cutscenes that move the weapon itself (sheathing, throwing, handing it over) play animations made for the old
  weapon's skeleton. Export Json adds a weapon family for each swap, so the new weapon plays them:
    { "receiving_skeleton": "/Game/Character/Weapon/WE0011_00_Vincent_Quiksilver/Model/WE0011_00_Skeleton",
      "animation_skeletons": ["/Game/Character/Weapon/WE0000_00_Cloud_BusterSword/Model/WE0000_00_Skeleton"],
      "method": "family", "requires_paks": ["<your swap pak>"] }
  The new weapon is the hub, so it keeps its own animated parts (hammer, trigger); every one of Cloud's weapons
  is on WE0000_00_Skeleton.

DECLARING PAIRS (any mix; a JSON pair wins over Asset User Data for the same skeleton)
  1. compat\*.json in this folder.
  2. <anything>.skelcompat.json next to your pak in End\Content\Paks\~mods, or inside your plugin mod's
     folder in End\Mods (up to 3 folders deep), so the pair ships with that mod.
  3. In the End project: Add New > Animation > Skeleton Compatibility Data Object. Fill in the pairs
     (Method, Requires Paks, Adopt Paths and the rest match the JSON fields below), press "Validate",
     then "Export Json", which writes option 1 and/or 2 for you. "Mesh" pairs can instead be stamped
     into the receiving skeleton's Asset User Data with "Apply To Skeletons" (BP_SkelCompatUserData),
     which cooks into your pak with the skeleton.
     Method "Family": Receiving Skeleton is the hub, Animation Skeletons and More Receiving Skeletons are
     the other members. More Receiving Skeletons = "receiving_skeletons", Carry Sockets = "carry_sockets".
     Validate reads every compat file the game reads (with your installed paks, when Game Directory is
     set) and shows how this mod settles them: families it makes, outfits that follow animations,
     pairs that switch off, files it skips.

JSON (see compat\example.json.txt, rename it to .json to use it)
  receiving_skeleton    animations: the skeleton that takes the animations over; mesh: the skeleton
                        your meshes use
  receiving_skeletons   several of them at once: each one gets the same pair
  animation_skeletons   skeletons the animations are authored on (mesh: in priority order, the first
                        loaded one wins)
  method                "animations" (default), "mesh" or "family"
  skeletons             family: the members (receiving_skeleton(s) and animation_skeletons count too)
  hub                   family: optional, the skeleton the family gathers on (naming a hub on any
                        entry makes it a family)
  adopt_paths           animations: optional, only assets under these paths (packages or folders,
                        e.g. /Game/Motion/Player/PC0000_Cloud/Neutral20); default: all of them
  receiving_meshes      mesh: optional, limit to these meshes
  repair_live_components mesh, family: optional (default true)
  fix_hierarchy         mesh, family: optional (default true), see HIERARCHY FIX below
  carry_sockets         mesh, family: optional (default true), a rebound mesh keeps the sockets of its
                        own skeleton
  proportions           optional (3.2): every body keeps its own bone lengths (see above)
  requires_paks         optional: the entry is only on while these paks / mods are installed, e.g.
                        ["SephirothOverCloud_P"] (a pak's file name without extension, or a mod folder
                        name in ~mods or End\Mods). Use it for the swap pak that puts the receiving character
                        in the other one's place: take that pak out and the pair switches off by itself, so
                        the original character keeps its animations.
  enabled               optional (default true)
  Families can also go in a "families" list next to "pairs" (its entries are families by default).
  Paths are object paths (/Game/Folder/Asset or /Game/Folder/Asset.Asset).
  Entries for the same receiving skeleton in several files merge into one pair (lists are combined).

  "animation_sets" (an array next to "pairs"; a file may hold only this array). Every list is a JSON
  array; the 3.1 object forms of "moves" and "sockets" are still read.
  characters            CharaSpec rows whose packs get the sets, e.g. ["PC0000_00_Cloud_Standard"]
                        (its pack is /Game/DataAsset/Game/CharaSpec/CharaSpec_PC0000_00_Cloud_Standard)
  battle                sources of the Battle* sets, first wins: folders like
                        "/Game/Motion/Player/PC0011_Vincent" or sets like
                        "/Game/Motion/Player/PC0011_Vincent/Battle00.Battle00". A set fills the set of its
                        own name; an object entry adds options:
                          { "from": "/Game/.../Battle00_Gun", "as": "Battle00" }  fills another set
                          "auto": true / "basic" / "all", "only": ["Shot"]        auto match (3.2)
  field                 the same for the other sets
  moves                 [ { "set": "<Set>" (optional), "key": "<name>", "animation": "<animation>" or
                        [ "<animation>", "<played next>", ... ] } ]
  limit_breaks          optional (3.2): [ <limit 1>, <limit 2>, ... ], each an animation or an array of them;
                        null keeps one
  sets                  optional: more set names to look for in folders (always looked for: Battle00,
                        Battle01, Battle02, Battle00_Comp, Battle01_Comp, Neutral00, Neutral01, Neutral10,
                        Neutral20, Emotion00, Facial00, Facial01)
  skeleton              the character's own skeleton (for "cutscene", "sockets" and "proportions")
  cutscene              optional: the skeleton whose cutscenes it plays (makes a family with "skeleton")
  sockets               optional (3.2): [ { "socket": "<the game's socket>", "use": "<socket or bone>" } ]
  proportions           optional (3.2): true
  override              optional (3.2): true puts this row first
  field_actions         optional: the AnimationSetParentFolder its CharaSpec row should use (written by the
                        data object)
  requires_paks, enabled  as for pairs
  Rows for the same character join (sources in file order, "override" rows first; the first move of a
  name wins).

  "weapon_swaps" (written by the data object's Export Json, next to "pairs"): the data object's weapon swaps,
  read back by Import From Game Json. This mod skips the key; the swaps reach the game as the CharaSpec rows in
  your pak and as the weapon families in "pairs" (marked "from_weapon_swap").

IN GAME
  F9 writes RebirthSkelCompat.report.txt in this folder: the adoption plans and their counts,
  containers still waiting, every rebound mesh, the result of the bone-hierarchy test the game
  runs before it lets an AnimBlueprint drive a mesh, and the live components.
  RebirthSkelCompat.log is the log of the current session. Look for:
    "Family (hub ...)"        a family and its members
    "Adoption ready"          how many bones carry over, and which curve names of the animation skeleton
                              the receiving skeleton lacks (those curve tracks are left out)
    "Adopted (...)" / "Not adopted ... : reason"
    "Rebound ..."             a rebound mesh, with the sockets it kept
    "Check ..."               the hierarchy test; for a family member also that its own AnimBlueprints moved to the hub
    "AnimBlueprint ... now runs on ..."  an AnimBlueprint made for a family member, moved to the hub
    "Config: ..."             how the pairs were settled (families made, pairs switched off and why)
    "Animation sets: Row ..." the sets each row found, with their animation counts, and its moves
    "Animation sets of <pack>:" what a character's pack got: per set the animation count and where
                              they came from, sets replaced / added
    "FName hash: ..."         the mod builds the merged sets' name maps itself, with the hash the game's
                              own maps were checked to use; "NOT CONFIRMED" means nothing is merged
    "auto-matched"            under "Animation sets of <pack>": every auto pick, name <- animation
    "Chained move ..."        a move or limit break played as several animations, and its length
    "Socket stand-ins: ..."   the stand-ins a mesh got while it loaded
    "Proportions: ..."        the retarget poses and bone settings a skeleton got
  A pair switched off by requires_paks logs "pair for ... is off: it requires ...".

HIERARCHY FIX ("mesh" pairs and family members)
  Before the game lets an AnimBlueprint drive a mesh it checks that every bone the mesh shares
  with the animation skeleton has the same parent chain. Rigs from different characters usually
  differ in a few accessory chains (belts, hair, coat tails), and one such bone is enough for a
  T-pose. The mod renames exactly those bones on the rebound mesh (they become "<name>_9xxxxx"),
  plus shared bones under them whose chain then no longer matches. For a family member, and for an
  outfit that followed its character's animations to another skeleton, it also renames every bone
  under them, so the test passes for the new skeleton's AnimBlueprints and for the ones the mesh was
  made for (the member's own, the outfit character's). Renamed bones keep the mesh's own pose relative to their parent; everything else
  animates. The log lists the renamed bones. Things that look bones up by name (physics bodies,
  hair physics) no longer find a renamed bone. Set "fix_hierarchy": false to switch this off.

LIMITS
  * The root bone must have the same name on the mesh and the animation skeleton; nothing else
    about the hierarchy has to match. If the game still refuses the AnimBlueprint (T-pose), the
    log and the report name the first bad bone.
  * A mesh that was already loaded when the mod first saw its pair is rebound late. Refused
    AnimBlueprints are re-initialised; the animation skeleton's virtual bones only appear on
    that mesh after it is loaded again. A family member's character that is already on screen with
    its own skeleton keeps its animations until it is loaded again.
  * "mesh" pairs do not chain (a receiving skeleton cannot also be the animation skeleton of
    another "mesh" pair); "animations" pairs that chain become a family.
  * Pose assets and streamable animations are not moved. In a family a member's AnimBlueprint
    blend profiles and per-bone settings refer to its own skeleton and may blend a little
    differently on the hub.
  * Asset User Data pairs (BP_SkelCompatUserData) always use the "mesh" method.
  * Another character's animations keep their own notifies: an enemy attack hits with the enemy's
    damage IDs (it may deal little or no damage when a player plays it) and plays the enemy's sounds
    and effects; a field attack made from a battle shot does not break crates (Cloud's N_Atk01 carries
    the crate-breaking hit). Check the log's picks and swap any odd one with "moves".
  * Socket stand-ins are made while a mesh loads: a mesh that was already loaded gets them the next
    time it loads.
  * "proportions" changes the hub skeleton's retarget settings for the whole session, for every
    character on it.
  * If anything inside the mod fails it switches itself off for that session (see the log) instead
    of stopping the game. To keep it off, create an empty nohook.txt in this folder; to remove it,
    delete this folder (or enabled.txt).
