RebirthSkelCompat 3.0.0 - KH3-style skeleton compatibility for FINAL FANTASY VII REBIRTH
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
  requires_paks         optional: the entry is only on while these paks / mods are installed, e.g.
                        ["SephirothOverCloud_P"] (a pak's file name without extension, or a mod folder
                        name in ~mods or End\Mods). Use it for the swap pak that puts the receiving character
                        in the other one's place: take that pak out and the pair switches off by itself, so
                        the original character keeps its animations.
  enabled               optional (default true)
  Families can also go in a "families" list next to "pairs" (its entries are families by default).
  Paths are object paths (/Game/Folder/Asset or /Game/Folder/Asset.Asset).
  Entries for the same receiving skeleton in several files merge into one pair (lists are combined).

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
    "Check ..."               the hierarchy test; for a family member also whether its own AnimBlueprints run
    "Config: ..."             how the pairs were settled (families made, pairs switched off and why)
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
  * If anything inside the mod fails it switches itself off for that session (see the log) instead
    of stopping the game. To keep it off, create an empty nohook.txt in this folder; to remove it,
    delete this folder (or enabled.txt).
