Create a Character System 3.7.1 - make playable characters for FINAL FANTASY VII REBIRTH
(formerly RebirthSkelCompat: its folders and files keep that name)
Game mod: UE4SS C++ mod in End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat (built against UE4SS 3.0.1 c0a8d4c)
Editor plugin: Plugins\RebirthSkelCompat in your End project

INSTALL
  Run CreateACharacterSystem-Setup-<version>.exe. It finds the game (Steam or Epic; Browse for
  another folder) and your End project, then installs the game mod and the editor plugin (untick
  either one). Every file it replaces is moved to a Backups folder first (the mod's Backups folder,
  and Saved\CreateACharacterSystem\Backups in the project); it never touches your compat files.
  Uninstall removes only the files Setup installs. Setup's log is CreateACharacterSystem-Setup.log
  in the mod folder and in %TEMP%.
  The game mod needs UE4SS 3.0.1 (c0a8d4c) in End\Binaries\Win64\ue4ss: Setup warns when it is
  missing or a different build. The editor plugin is built for the RebirthEngineV5 editor
  (engine build 17c11882-043f-4330-9e21-2efa519533c5); with another build the editor offers to
  rebuild it, which needs Visual Studio 2019.
  By hand: copy the mod folder to ue4ss\Mods\RebirthSkelCompat (dlls\main.dll, enabled.txt) and the
  plugin folder to <project>\Plugins\RebirthSkelCompat.

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

  "cutscene_weapon_socket": "Attach_Weapon_Left01" (3.6.16)  the socket of the character's mesh its weapons go to while
  it plays a cutscene (its anim instance's bPlayingCutScene). For a character that plays another's cutscenes with an
  AnimBlueprint of its own: Evil Cloud in Sephiroth's place holds the sword in his right hand in battle and on his back
  outside it (Cloud's AnimBlueprint), while Sephiroth's cutscenes hold the Masamune in the left hand. During the
  cutscene a weapon the game puts back on a socket of its own rules goes there again; one the cutscene puts elsewhere
  stays. When the cutscene ends, each goes where the game's rules put it now (EndSceneAPI AttachWeapon), else back where
  it was. The log says each move ("Cutscene weapons: ...").

  "proportions": true  every body keeps its own bone lengths while it plays animations made for another
  body: spine, arms, legs and fingers take their length from the character's own mesh, the pelvis height
  is scaled per body (feet stay on the ground; 3.2.2 - 3.2.1 left it as animated), everything else (root,
  face, weapons, physics and helper bones) plays as animated. On a row it applies to every pair and family of the row's "skeleton"; on a
  family, to every member (the hub skeleton gets the settings). Takes effect from the next map load.
  3.6.7: in cutscenes too. The game's cutscene animations are marked to skip this (bIgnoreTranslationRetargeting), so a
  body played the animation's own bone lengths there and took the other body's height and build. The mod clears that
  mark on the cutscene animations of a family with "proportions" as they load, so every body keeps its build and height
  in cutscenes as in gameplay. "cutscene_proportions": false (at the top of any compat file) leaves them as the game
  has them.

  "override": true  puts the row before the character's rows from other files (a test file over a mod's
  own row): its sources come first, and its moves, field actions and sockets win.

ABILITIES PER ANIMATION PACK (new in 3.3): a moveset with its own ATB commands and limits
  The game switches a character's animation pack in battle with EndBattleAPI SetPrimaryAnimPack (a Lua mod
  or Blueprint can call it: Battle02, Battle03, ...) and goes back to its own with ResetPrimaryAnimPack. A row
  can give each pack its own command menu and limit breaks:
      "player": "pt_Cloud",
      "abilities": [ { "pack": "Battle00", "commands": [ "PC0010_AtkBurst01", "PC0010_AtkBurst02" ],
                                           "limits": [ "PC0010_Limit001", "PC0010_Limit002" ] },
                     { "pack": "Battle02", "commands": [ "PC0010_T_ShadowFlare", "PC0010_T_Firaga" ] } ]
  "player" is the character's BattlePlayerParameter row (pt_Cloud for anyone in Cloud's slot, pt_Barret, ...).
  A character only takes the sets its CharaSpec row's AnimationSetList names from its pack, so every pack it switches
  to (Battle02, ...) has to be in that list (CharaSpec table, in your pak); the log says so when a switch goes to a
  pack the row does not name. The game also takes a set only from some slots of that list (a set in Neutral20's slot
  8, or in slot 5 or 9 of a player row, is in the pack but never switched to); 3.5 makes every set of the pack
  switchable: when the game has no set of the name a switch asks for, the mod gives the character its pack's own (the
  log names the sets the game took, the first time).
  When one of the row's characters gets a pack, the mod points that row's CommandAbilityID_Array (the ATB
  abilities in the menu, in menu order) and LimitAbilityID_Array (limit 1, 2, ...) at the pack's lists:
    - a pack without its own "commands" (or "limits") uses Battle00's, else the table's own list;
    - "Battle00" is also what every map load and ResetPrimaryAnimPack put back;
    - an empty list ([]) empties that menu.
  Every entry must be a row of the resident BattleAbility table (yours, in your pak, or the game's); anything
  else is left out and named in the log. The tables are edited in memory only. The game lists the first 5
  commands and the first 3 limits of a player row (then the character's weapon and materia abilities), so
  keep each pack to 5 commands and 3 limits; the mod writes that many and logs the rest as left out. The anim
  keys the abilities play must be in the pack's sets (sources or "moves"). The log ("Abilities: ...") and the
  F9 report show each switch.
  The lists reach the game through its own list getters (3.3.1: their table slots point at the mod's, which answer
  for the switched rows only), since the tables can sit in memory the game keeps read-only.
  The game copies a character's lists out of the row when it recalculates the character's status, so after a
  switch the mod has it recalculate (3.4: EndMenuBPAPI BPSetPlayerExperience with the EXP the character already
  has; nothing else changes, and the mod checks the level and EXP afterwards and stops recalculating for the session
  if either changed) and the menu shows the new lists.
  WARNING about 3.3 and 3.3.1: they used BPSetPlayerLevel with the character's level, but the game's BPSetPlayerLevel
  sets EXP (it is the same function as BPSetPlayerExperience), so a switch set the character's EXP to its level
  (level 70 -> 70 EXP -> level 1). Do not keep a save made after a switch with 3.3 / 3.3.1; 3.4 fixes it.
  A switch made while the mod is busy (for example a script that switches packs from inside a call of the mod's)
  is applied right after (the log line says "after the mod's work"). That needs a party member's row (pt_Cloud, pt_Barret,
  pt_Tifa, pt_Aerith, pt_RedXIII, pt_Yuffie, pt_CaitSith, pt_Zack, pt_Sephiroth, pt_Vincent, pt_Cid). With
  "refresh_abilities": false on the row the mod leaves that out, and switched lists show when the game next
  recalculates (a new area, a level up).
  An object works too: "abilities": { "Battle02": { "commands": [...], "limits": [...] }, "Battle03": [...] }
  (an array alone is the commands).

  "weapon_abilities" (3.4) in a pack's entry: the abilities the character's weapons give switch with the pack too.
      { "pack": "Battle02", "commands": [...],
        "weapon_abilities": { "PC0000_AtkBurst02": "PC0010_T_Blizzaga", "PC0000_AtkBurst08": "PC0010_W2_ZanshinRising" } }
  Each key is the ability a weapon gives (its Equipment row's BurstAbilityID: Cloud's Buster Sword gives
  PC0000_AtkBurst02, Focused Thrust), each value the BattleAbility row it gives while the pack plays. The game still
  decides whether a weapon's ability shows (learned through the weapon's proficiency, or the weapon equipped), so a
  character's progress carries over. A pack without "weapon_abilities" uses Battle00's, else the weapons' own; {}
  gives the weapons' own. The game rebuilds the list with the others (the status recalculation above). The mod finds
  the game's lookups of a weapon's row by their code (checked against the Equipment table) and points them at its own:
  the log says "Abilities: the game's weapon ability lookups point at the mod's (2 call(s) ...)" and lists each switch
  ("weapon abilities PC0000_AtkBurst02 -> PC0010_T_Blizzaga, ...").
  Moves on another character's ability IDs: a character's limit and weapon ability rows (PC0000_Limit001-003,
  PC0000_AtkBurst02, ...) can hold another character's moves (in your BattleAbility table): their IDs keep the unlocks
  your save has for them (limit levels, weapon proficiency), which new IDs do not have.

  "preload": [ "/Game/DataAsset/Game/CharaSpec/CharaSpec_FA0260_01_SephirothMeteor_Battle" ]  objects loaded
  at the first map load and kept for the session (for example the CharaSpec pack of a prop that one of the
  abilities' damage sources spawns).

  "pack_assets" (3.3.1): [ "/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Build/
  PC0010_10_Sephiroth_Transform_Effect__Pack" ]  objects put into the row's CharaSpec packs, next to what the
  pack already lists (the AssetDataList entry holding objects of the same class). A damage source names its
  effects (CreateEffectResourceName, BindEffectResourceName, HitEffectResourceName_Array, category 10) and the
  game looks them up in the effect packs of the attacker's CharaSpec pack, so abilities of another character
  (the transformed Sephiroth's feelers, lasers, ...) only show their effects when his effect pack is in the
  pack too. Each object is loaded at the first map load (like "preload") and the log says
  "pack asset <name> added to entry N" when the pack merges.

FORMS (new in 3.6): a character that changes form in battle (the forms menu)
  Hold the row's button in battle (Triangle by default; a tap stays the game's) and the forms menu opens: a command
  window in the game's own menu art with the character's forms, 7 at a time (up to 13, its normal one first: the list
  scrolls), the one it is in marked. Up and down on the left stick, the D-pad or the arrow keys move the cursor; let go of
  the button to switch to the form under it. A form is an animation pack of the character (Battle02, ...: its moves,
  switched with EndBattleAPI SetPrimaryAnimPack; the normal form ResetPrimaryAnimPack) and what changes with it:
      "forms": { "button": "Gamepad_FaceButton_Top", "title": "FORMS", "parts": [ "Wing" ],
                 "list": [ { "name": "NORMAL" },
                           { "name": "WINGED", "pack": "Battle02", "show": [ "Wing" ],
                             "effects": [ { "effect": "/Game/Effect/.../FX_Feathers_01", "socket": "R_Shoulder_a" } ],
                             "sounds": [ { "bank": "/Game/Sound/SE/.../SE_PC0010_00_Sephiroth_Standard",
                                           "cue": "SE_..." } ] },
                           { "name": "BIZARRO", "pack": "Battle05",
                             "model": "/Game/Character/Enemy/EB2210_00_BizarroSephiroth_Standard/Model/EB2210_00_Body",
                             "anim_class": "/Game/Character/Enemy/.../EB2210_00_BizarroSephiroth_Standard_Animation",
                             "scale": 0.1, "hide_weapon": true,
                             "super_armor": true, "seconds": 60, "cooldown": 30 } ] }
  ("forms" can also be just the list.) The menu's settings, all optional:
    "button"           the input key held to open it ("Gamepad_FaceButton_Top" is Triangle, "Gamepad_LeftShoulder"
                       L1, ...)
    "key"              a keyboard key that opens it too ("T")
    "hold_seconds"     how long the button is held before it opens (0.35; at least 0.1, as a tap is the game's)
    "title"            its heading ("FORMS")
    "parts"            material slots of the character's model that the forms show or hide (each form's "show")
    "fade_seconds"     parts fade in and out this long (0: at once), with "fade_parameter", a scalar of their materials
                       (NativePrimitiveCoverage)
    "show_effects", "hide_effects"  effects played as parts come out and go
    "effect_seconds"   how long a switch's effects play (2.5; an effect can give its own "seconds")
    "hide_on_others"   other copies of the character's model (cutscenes, the menus) keep the parts hidden (true)
    "timer_at"         [x, y], fractions of the screen: where a timed form's time left shows ([0.97, 0.55]; right of the
                       middle, its right edge is there); false: not shown
  A form (a plain string is a pack):
    "name"             on the menu (the pack's name when it has none)
    "pack"             its animation pack (none or Battle00: the character's own). As for abilities per pack (above), it
                       has to be in the character's CharaSpec row's AnimationSetList, and the row's "abilities" entry
                       for that pack gives the form its commands, limits and weapon abilities.
    "show"             the parts shown in this form (the other "parts" are hidden)
    "model"            a skeletal mesh worn in this form (none: the character's own); "anim_class" its AnimBlueprint
                       (needed for a model on another skeleton: the model's own), "scale" its size (0.01 to 50), "meshes"
                       model parts added (a mesh, or { "mesh": ..., "socket": ..., "follow_pose": true }). A new
                       AnimBlueprint (or a model on another skeleton) gives the mesh a new anim instance: the game's
                       animation controller of the character takes it, as it took the first one (3.6.1; the log says
                       "the game's animation controller took its new anim instance"). A character whose controller the
                       mod does not find keeps its own model in the form ("keeps its own model in ...: ...").
    "hide_weapon"      the character's weapons are hidden in this form
    "effects"          played as it switches to this form; "keep_effects": played for as long as it is in it (an aura).
                       Each { "effect": a Niagara or Cascade system, "socket": a socket or bone, "scale": 1,
                       "seconds": 0 }
    "sounds"           [ { "bank": a sound bank, "cue": one of its cues } ]; "voice" in place of "bank", with {language}
                       in its path (/Game/Sound/Voice/{language}/...), plays the bank of the game's voice language
                       while the game has it loaded (a party member's voices). The mod does not load voice banks
                       (3.6.3): a cutscene's line (/Game/Sound/Voice/{language}/Cut/8800-FOREE/EV_FOREE_8630/
                       C3510_MAIN_3400_0400_00_sep) plays only while the game has that cutscene's voices loaded, else
                       the log says "Forms: voice line ... left out" once
    "fly"              true (or { "height": 250, "speed": 600, "max": 3000, "up": ..., "down": ... }): the character
                       flies in this form, hovering above where it started; up and down (the D-pad) raise and lower it
    "after"            an ability (a BattleAbility row): when it ends, the character switches to this form by itself
                       (a limit break that transforms it)
    "ability_effects"  effects played while some abilities run in this form, stopped when they end (a sword it conjures
                       in its sword attacks): [ { "abilities": [ "PC0010_BZ_Octaslash", "PC0010_NAtk_*" ],
                       "effects": [ ... ] } ] (a name ending in * is every ability that starts with it)
    "super_armor"      true: hits do not make the character flinch or stagger in this form (EndBattleAPI
                       SetDisableReaction); it still takes their damage
    "camera"           (3.6.16) the battle camera while the character in charge is in this form, for a big body:
                       { "distance": 400, "height": 100, "fov": 0, "blend": 0.8 } moves the game's camera that many cm
                       further back along its view and up, and widens it that many degrees, getting there (and back)
                       in "blend" seconds; a number alone is the distance. A wall between keeps it in front of the wall.
    "ability_cameras"  (3.6.16) the camera while some abilities run in this form instead: [ { "abilities": [ "M_SMN_*" ],
                       "distance": 1500, "height": 500 } ] (M_SMN_* are the summons' calls; a name ending in * is every
                       ability that starts with it). The log says each change ("Forms camera: ...").
    "seconds"          the form lasts this long (game time: pauses stretch it), then the character turns back by itself,
                       once the ability it is running ends (8 s more at most). Its time left shows on screen, orange in
                       the last 10 s. The normal form has no time limit.
    "cooldown"         once the character leaves the form, it can be chosen again only this many seconds later: the menu
                       shows "ready in 0:25" by it, and picking it before then says so
    "revert_to"        the form it turns back into, by its name on the menu (none: the normal one)
    "entrance"         (3.6.6) played as the character in charge switches to the form from the menu (not when the battle
                       ends): { "animation": "/Game/.../B_SaferEnter01" (played over everything else, in the form's
                       AnimBlueprint's "slot", DefaultSlot; the shot lasts its length at "rate", or "seconds"),
                       "flash": 1.5 (the screen starts white, "flash_color" [1, 1, 1], and fades back in that many
                       seconds: the model change happens under it), "descend": 1200 (the model starts that many cm up
                       and comes down in "descend_seconds", 70% of the shot when 0), "effects": [ ... ] (on the model
                       for the whole shot), "camera": { "face": "C_Head_a" (the bone it looks at), "distance": 900,
                       "side": 150, "height": 40 (where it starts: in front of the character, to its right, above the
                       ground, looking up), "fov": 70, "close_at": 0.65 (the part of the shot after which it moves in),
                       "close": 180 (cm in front of the face it ends), "close_fov": 30, "hold": 0.6, "blend_back": 1
                       (seconds back to the game's camera), "bars": 2.39 (cinema bars; false: none) } (or false),
                       "hold_input": true (the sticks do nothing meanwhile), "skip": true (an attack or a command ends
                       it early), "invincible": true (no damage while it plays) }. true: the flash and the camera only
                       (3.6.7) or a cutscene's own shots: { "shots": [ { "name": "C0130", "seconds": 7.1,
                       "before_switch": true (played first, on the model the character has; the switch to the form
                       comes when these shots are over), "animation": "/Game/Cut/.../...C0130" (played from
                       "animation_start" seconds into it, at "rate"), "scale": 1 (the size of the character the
                       camera and offsets are for: they are scaled by the model's size), "flash": 1.2 (the screen white
                       as the shot starts, fading back), "camera": [ [t, forward, right, up, pitch, yaw, roll, fov],
                       ... ] (seconds into the shot; cm and degrees from where the model stands, turned with the
                       character), "effects": [ { "effect": "...", "at": 5.4, "seconds": 1.7, "offset": [forward,
                       right, up] or "socket": "...", "yaw": 0, "scale": 1 } ], "sounds": [ { "bank" or "voice": "...",
                       "cue": "...", "at": 1.1, "start": 14.1 (seconds into the sound), "stop_at_end": true } ] }, ... ],
                       "camera": { "hold": 0.2, "blend_back": 1.2 }, "hold_input", "skip", "invincible" }. When the
                       first shots cannot play on the model the character has (another skeleton), the switch happens
                       at once and the rest plays. Skipping during the first shots still switches.
  Knocked out in a form with super armor or a time limit, the character loses its super armor and its time stops (the
  game's knock-out plays as usual); back on its feet (Phoenix Down, Raise) it turns back.
  A pack switch made by anything else (a Lua mod, a Blueprint, the game) changes the character's form too, and every
  character is back in its normal form when the battle ends. The log says "Forms: ..." for each switch, effect and sound,
  and the F9 report lists every row's forms. A Lua mod can call RebirthSkelCompatHasForms() (true while this mod changes
  forms) to leave them to it.
  3.6.1: a form with its own AnimBlueprint (Bizarro Sephiroth's) no longer crashes the game a moment after the switch
  (the new anim instance had not been set up by the game's animation controller); the forms menu's words and a timed
  form's time left show again (they were blank: TextBlock SetText's text argument); cutscene voice lines play in forms.
  3.6.2: after a model change the character's moves play again (the new anim instance is given the animation sets the
  old one had: before, every move fell back to one pose); the game's mesh tick no longer runs on bone tables of the
  other model (the crash a while after a form's model came off); voice lines are tried in every voice language and
  through their cutscene's voice packs (the log says what loaded).
  3.6.3: no more crash half a minute into the game ("Crash in runnable thread FAsyncLoadingThread"): 3.6.2 loaded voice
  banks itself, in every language, and the game's loading thread crashed in one. The mod no longer loads voice banks
  at all; a form's voice line plays while the game has its bank loaded.
  3.6.4: a form with its own model and AnimBlueprint (Bizarro Sephiroth) no longer has the engine make a new anim
  instance at each switch: the character's own anim instance (the one the game set up when it spawned) is kept while
  the form's model is on and put back when it turns back, so its moves play again after the switch back; the form's
  instance is kept too once made (set up once). A form's instance made for the first time is given the character's
  animation sets with the game's own registration and the lists the game copies from it when the character spawns.
  The mesh tick builds its bone tables for whichever model is on (3.6.2 stopped it, and it stayed off after the switch
  back). The log lists each instance's layers and, in another model, what its anim instance plays in each ability.
  3.6.5: a form's model with an AnimBlueprint of its own (Bizarro Sephiroth) goes on the way the game puts the Toad
  status on: as a look of the character's own (EndChangeAppearanceCharacter's ChangeAppearanceSettings), so the game
  makes a new animation controller for the new anim instance, sets the mesh tick and the hit body up for the model, and
  puts the character's own look back the same way when the form ends. Moves play through that controller (3.6.1 - 3.6.4
  kept the one made for the old instance). The form's look is an entry of its own just past the character's list, so
  the game never treats the character as a toad (no Toad camera); the hit body is one capsule of the character's size
  at its middle whatever the model's size. A Toad status put on over the form's look is let be: the character's own
  look comes back after it, then the form's. When the game's code is not the one this mod knows, the log says so and
  the model goes on 3.6.4's way.
  3.6.6: a form's entrance ("entrance"): as you switch to it, the screen flashes white, the form's animation plays (a
  cutscene's), the model comes down from the sky, and a camera of the mod's starts low in front of the character
  looking up at it and ends close on its face, then blends back to the game's camera. An attack or a command skips it.
  3.6.7: an entrance can be a cutscene's own shots ("shots": the cutscene's cameras, animations, effects and sounds),
  some of them before the switch. Sephiroth's BIZARRO plays the end of his transformation cutscene (EV_FOREE_8630):
  his close-up as he says "Alone at last. Shall we?" and the darkness takes him, a white flash, then Bizarro Sephiroth
  rising into view with the cutscene's camera, animation, effects and sound (about 16 s; an attack or a command skips
  it and he still turns; from SAFER only the reveal plays). The line comes from the cutscene's voice, which the
  Fully Playable Sephiroth data pak now loads with him. And "proportions" now also works in cutscenes (see above).
  3.6.8: no more hitches in the entrances (Safer's above all): the mod's checks that an object is still there no longer
  go through every object of the game (tens of milliseconds each time, once a second and for every effect and sound),
  the search for other copies of a model is spread over the frames, and the cinema bars are drawn on the screen instead
  of being the camera's shape (which made the game remake its render buffers as they came and went). The log says how
  smoothly each entrance played ("...'s entrance played at N fps ...").
  3.6.9: the log says what the character you control is and plays, the animation sets the game looks up for it (and
  whether it has them), and the animation and movement calls the game makes on it ("Watch: ..."); a level set the game
  looks up for a character with forms and has none of is given from the character's own folders.
  3.6.10: more of that log (the set names looked up for any character from the start, the character's set entries and
  its anim instance's set layers).
  3.6.11: the T-pose in chapter 1's burning Nibelheim: the game puts the damaged walk on Sephiroth but leaves it empty;
  the mod fills it with the walk from his folder ("Level sets: ... GIVEN ...").
  3.6.12: the same T-pose: 3.6.11 waited to load that walk until a moment that never came there. The mod now gives the
  walk the game asks for at once when it is loaded (his folder's, else Cloud's, whose animations the level plays), and
  otherwise has the game load it in the background and gives it as soon as it is there ("Level sets: ... GIVEN ...").
  3.6.13: the extra log 3.6.9 - 3.6.11 kept to find that T-pose is gone (the calls the game makes on the character you
  control, every animation set it looks up, what the character holds four times a second), and with it the work it
  took every frame. The log still says who you control and when the mod gives a character a set the game left out.
  3.6.14: the T-pose in the chocobo wrangling: the game put a level set on Sephiroth there with nothing playing that
  named it. The mod now notes which level sets load (the level loads Cloud's) and, when nothing else names the set,
  gives the one that loaded last ("Level sets: ... (the level set that loaded last: ...); GIVEN ...").
  3.6.15: the forms work again: 3.6.14 took a form's moves (its animation pack, which the game keeps by name only) for
  a level set the game had left empty and gave it the level set that had loaded last, so the form's attacks stopped
  playing about 10 s after every switch, and the entrances of Bizarro and Safer froze the game for a few seconds while it
  did. Only the game's level set entries (named after one of the character's motion folders) are filled now.
  3.6.16: "cutscene_weapon_socket" (see ANIMATION SET ROWS): a row's characters hold their weapons on a socket of your
  choosing in cutscenes (Evil Cloud: in his left hand there, as Sephiroth's cutscenes have it, in his right in battle).
  A form's "camera" and "ability_cameras" (see FORMS): the battle camera further back for a big body (Bizarro), and
  further still while it calls a summon.

SHOOTER (new in 3.7): a character that fights as Vincent does in Dirge of Cerberus
  A row's "shooter" (true: every setting its default; or an object of settings; false: none) makes its characters a
  third-person shooter in battle ("in_field": true: outside battle too). While the character is the one you control:
    the camera goes behind its right shoulder; the right stick still turns it. Aiming pulls it in closer and narrower
      over the shoulder and slows the stick; zoom (while aiming) narrows it more and shows the scope. While a spell, a
      limit break or a summon runs the game's camera has the view ("camera_abilities": the abilities the shooter's
      camera stays on through; ["*NAtk*", "*Avoid*", "*Dodge*", "*Guard*"]: the normal attacks and dodges).
    the gun in hand's reticle is in the middle of the screen (red over an enemy, gold as a shot connects) and its bullet
      counter at the bottom right.
    a shot is one of the game's own: a gunner's bullet damage source ("damage_source") made at the enemy under the
      reticle (with "assist" degrees of aim assist), with a muzzle flash ("muzzle") and a gunshot ("sound") at the gun.
      The bullet starts where its damage source row says: the rows the guns use start at the weapon's VFX_Muzzle01 (the
      row's CreateBasePos 1: the weapon; CreatePartName: the socket on it), the muzzle of Vincent's gun.
    the gun is in its right hand while the shooter is on ("gun_socket": the socket of the character's model it goes on,
      Attach_Weapon_Right01; false: where the game puts it); a limit break, spell or summon and the shooter going off
      put it back where the game's rules want it.
    each gun has a clip ("clip") that reloads by itself when it is empty or with the reload button ("reload": seconds);
      the ammo never runs out. The switch button goes to the next gun (each keeps its clip).
    while it aims or shoots it turns where it aims ("turn_actor"), on the move too (it strafes: the movement's
      turn-where-it-goes is off meanwhile; when the game still turns it, it faces where it goes and runs forward).
    Dirge of Cerberus' motions of the gun in hand play ("motions"): its stance standing still, its walk and run (aiming:
      the aim stance, and the run forward, back, left or right of where it faces, as fast as it goes), and its shot,
      reload (on the move too) and switch motions over them.
    the gunshot is Vincent's own (3.7.1): two slices of his shot in the cutscene EV_FOREE_0630, where he fires through a
      scope (the sound tracks EV_FOREE_0630_01 from 10.59 s and EV_FOREE_0630_0319f from 0.035 s).
    a DualSense's triggers pull like the gun in hand ("fire_trigger", "kick"; "aim_trigger"; "triggers": false: off).
  Its buttons ("controls"): "triggers" (the default): R2 fire, L2 aim, R1 reload, L1 switch gun, R3 zoom.
    "dirge": R1 fire, L1 aim, R2 reload, L2 switch, R3 zoom. Or each by name: "fire", "aim", "reload", "switch",
    "zoom": "R2", "L1", "Square", "Up"... (false: none). The game does not see the shooter's buttons while it is on
    ("block": the list; by default the five buttons), so their own jobs (guard, lock-on, shortcuts) are off then. In
    menus, in the battle menu's slow motion, with another character in charge and outside battle it sees them again.
    The mod reads the controller where the game reads it (a DualSense or DualShock 4 over USB or Bluetooth, or an XInput
    pad); without a report of it the buttons come from the game's input, and the game sees them too.
  "camera": "distance", "side", "height" (cm behind, right of and above the pivot), "aim_distance", "aim_side",
    "aim_height" (aiming), "pivot" (cm above the middle of the character), "fov" (0: the game's), "aim_fov", "zoom_fov",
    "blend" (s between them), "aim_scale" and "zoom_scale" (the stick's speed then), "pitch_min", "pitch_max",
    "camera_abilities". A wall between the character and the camera brings the camera in front of it.
  "reticle": "ui_folder" (a folder in the mod's folder, "dirge_ui": the HUD's PNG files: reticle_cross, reticle_round,
    reticle_ornate (each gun's "reticle"), scope_ring, counter_frame, bullet_icon, digit_0 .. digit_9; without them a
    "+" and the count in words), "scale" (the reticle's size), "hud_scale" (all of it), "color", "enemy_color",
    "hit_color" ([r, g, b] or [r, g, b, a], 0 to 1), "hit_seconds", "ammo" (false: no counter).
  "motions": "folder" (the motions, /Game/RebirthSkelCompat/Dirge/Vincent: the VincentDirgeMotions_P pak), "prefix",
    "suffix" (p000_ and _remap: <folder>/<prefix><gun's set>_<motion><suffix>), "stand" (st), "idle" (st_a: aiming),
    "walking" (wk), "running" (rn), "walk" (wk_a), "run" (rn_a), "back" (brn_a), "left" (lrn_a), "right" (rrn_a: aiming),
    "shot" (st_f), "reload" (st_rd), "walk_reload" (wk_rd), "run_reload" (rn_rd), "switch" (swtch), "walk_speed" (160)
    and "run_speed" (500: cm/s the walk and run are made for), "slot" (DefaultSlot: the AnimBlueprint slot they play in),
    "turn_actor"; false: none. A motion's false or "" leaves the game's own there.
  "weapons": the guns, in switching order (none given: CERBERUS, HYDRA and GRIFFON). Each: "name" (one of those three
    starts from its settings), "set" (its Dirge of Cerberus motions: m001_h handgun, m002_m machine gun, m003_r rifle),
    "damage_source", "ability" (the ability the damage counts as), "clip", "interval" (s between shots), "automatic"
    (holding fire keeps firing), "reload", "spread", "recoil" (degrees), "range" (cm), "fire_at" (how far the trigger
    is pulled when it fires, 0 to 1), "aim_fov", "muzzle", "impact" (an effect where a shot at no one lands), "sound"
    (a sound, or a list of sounds that play together: {"bank": path, "cue": name, "start": s, "length": s, "volume": v};
    "start" and "length": a slice of a longer sound, such as a cutscene's sound track), "reload_sound", "reticle",
    "fire_trigger", "kick" (a trigger effect: {"mode": "weapon", "start": 4, "end": 6,
    "strength": 6}, "feedback" with "start" and "strength", "vibration" with "start", "strength" and "frequency", or
    "off"), "kick_seconds".
  A form's "shooter": false turns it off while the character is in that form (GALIAN, CHAOS).
  The log says when the shooter comes on and goes off, the controller it reads, the gun it finds and whether it has
  its muzzle socket (the muzzle flash plays at the character when there is no gun), the gun going into its hand and
  back, the first motions and shots and what they hit, the abilities it sees, and whether the game's camera goes
  through the mod ("Shooter: ..."); ten seconds after it comes on and as it goes off, what the controller hooks saw
  ("Pad: ..."). The report ("Shooter: ...") has the shots, the clips and the controller.

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
  player                optional (3.3): the character's BattlePlayerParameter row, e.g. "pt_Cloud"
  abilities             optional (3.3): [ { "pack": "<pack>", "commands": [ <BattleAbility rows> ],
                        "limits": [ <BattleAbility rows> ] } ] (needs "player"; at most 5 commands and 3
                        limits per pack; see above)
                        a pack's "weapon_abilities" (3.4): { "<the ability a weapon gives>": "<BattleAbility row>" }
  refresh_abilities     optional (3.3): false: no status recalculation after a switch
  preload               optional (3.3): [ <object paths> ] loaded and kept from the first map load
  pack_assets           optional (3.3.1): [ <object paths> ] put into the characters' CharaSpec packs (another
                        character's effect pack, a sound bank; see above)
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
    "Proportions: ..."        the retarget poses and bone settings a skeleton got, and (3.6.7) the cutscene animations
                              that keep every body's build
    "Abilities: ..."          a pack's commands, limits and weapon abilities as it switches
    "Forms: ..."              the forms menu, each switch (and why), super armor, time limits, effects and sounds
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
    character on it, in cutscenes too (3.6.7; "cutscene_proportions": false keeps cutscenes as the game has them).
  * If anything inside the mod fails it switches itself off for that session (see the log) instead
    of stopping the game. To keep it off, create an empty nohook.txt in this folder; to remove it,
    delete this folder (or enabled.txt).
