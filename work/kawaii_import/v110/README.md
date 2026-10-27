# Kawaii Dynamic Motions for the End editor (UE 4.26), with Create a Character System

Kawaii Dynamic Motions (1.10) is KawaiiPhysics (pafuhana1213, MIT License: see LICENSE) 1.7.0 for UE 4.26, with the newest
KawaiiPhysics' features fused in and motions of its own, for FINAL FANTASY VII REBIRTH modding with Create a Character
System. The name is new in text only: the plugin's folder, its modules, the node's class (AnimGraphNode_KawaiiPhysics) and
the compat files' `"kawaii"` keys keep KawaiiPhysics' names, so AnimBlueprints made with it before keep working.

* **Sync Bone** (1.10; the game mod 3.17.0 runs them, KawaiiPhysics' SyncBone). An animated bone (a knee) whose move
  from its reference pose goes onto the pose of chain bones before the physics runs, so a coat's strips follow the leg
  instead of the leg going through them. In the node's details, **Sync Bone** (up to 16; the game's `"sync_bones"`): its
  **Bone**, its **Target Roots** (bones of the node's chains, with **Include Child Bones** and **Scale Curve By Bone
  Length Rate**: the part of the move each bone gets by its place below the target root), **Global Scale** (0 - 1 per
  axis of the component: +X the model's front, +Y its right, +Z up), **Scale Curve By Delta Distance** (by the move's
  length, cm), **Apply Direction X / Y / Z** (Both, Positive, Negative, None) and **Distance Attenuation** (inner and
  outer radius, max rate). A chain's root follows its animation (a target root there is not moved); a bone the sync moved
  is turned toward its child from its animated direction. The preview runs them as the game will, Export For Game writes
  them, Import From Game reads them; the Debug draw shows each sync bone and lines to its target roots. With them
  (Advanced Physics Settings): **Interpolate Limits In Substeps** (on: each fixed step's collision shapes between their
  places at the last frame's end and this frame's, so a fast leg no longer jumps past the cloth) and **Keep Collision
  Side** (a bone a shape moved past in one step put back out on the side it was on).
* **Dynamic Motions** (1.9; the game mod 3.15.0 plays them). A node's bones move on their own, the physics on top: its
  waves and its key animation turn the bones' pose (the place the physics pulls each bone back to) before the physics
  runs, so the chain sways or beats by itself and still swings with the character's moves, collides and keeps its limits.
  In the node's details, **Dynamic Motions**:
  * **Pose Waves** (up to 8; the game's `"pose_waves"`): each bone turns about **Axis** (the model's: +X its front, +Y
    its right, +Z up, at the bone; **Local Axis**: the bone's own) by **Degrees** x sin(360 x time / **Seconds** +
    **Phase** - **Phase Per Bone** x its steps from its root - **Phase Per Root** x its chain's number - **Root Phases**[its
    chain]), times **Degrees Rate by Bone Length Rate** along the chain. The turns add up down a chain (a few degrees a
    bone sway a long tail far); Phase Per Bone makes the sway travel down it; the chains are Root Bone (0), then the
    Additional Root Bones in order, so Phase Per Root or Root Phases ripple over many chains (the blades of a wing).
  * **Pose Animation** (the game's `"pose_animation"`): a looping key animation of the bones, each track a bone's local
    rotation (under its parent) a key a frame, every track as long (or one key), up to 256 bones and 6000 frames; **Fps**,
    **Speed**, **Weight**, **Additive** (the turn from its first frame added to the pose; off: its rotations take the
    pose's place). Import From Game reads its tracks from a compat file. Played before the waves.
  * The preview plays them as the game will (the same simulation), and Export For Game writes them.
  * **Example:** `Content/KawaiiDynamicMotions/Examples/BahamutFusedSephiroth/ABP_BahamutFusedSephiroth_KawaiiDynamicMotions`
    (made by `Tools\RebirthSkelCompat\run_kawaii_dynamic_motions_install.cmd`): Bahamut Fused Sephiroth (PC0010_17_Compat)
    standing, from `compat\BahamutFusedSephirothKawaii.json`: his tail sways side to side, a wave travelling to its tip
    (Tail1: Pose Waves, Axis Z, 4 degrees, 3.2 s, Phase Per Bone 16), and his blade wings beat slowly, a ripple from the
    top blade to the bottom (the six blade wings nodes: Axis X, 9 degrees, 3.5 s, Root Phases), the physics on top; his
    mantles and hair swing with him. A walk is there too (`Bahamut_KDM_Walk`: pick it in the animation player). Editor
    only, like every AnimBlueprint with these nodes.

* **The same simulation as the game.** The node runs Create a Character System's own KawaiiPhysics solver
  (`Source/KawaiiPhysics/Private/Solver`: the game mod's `SkelCompatCore.hpp` and `KawaiiSolver.hpp`), so the preview in
  the AnimBlueprint editor moves the bones as the game will.
* **Newest features:** additional root bones (each with its own exclude bones), curves for damping, stiffness, world
  damping, radius and limit angle (along each chain), dummy bones and bone forward axis, bone subdivision, simulation
  space (component, world, base bone), fixed substeps or per-frame steps, warm-up, teleport thresholds, mesh move scale,
  planar constraint, spheres, capsules, tapered capsules, boxes and planes (the node's own and a Limits Data Asset's),
  XPBD bone constraints with compliance, gravity and a simple external force.
* **Live edits.** An edit of the node's values, curves, forces or shapes takes effect in the preview at once, and the
  bones go on from where they are; an edit of what the chains are made from (bones, dummy points, space, constraints)
  starts them again.
* **Viewport tools.** Select the node in the AnimGraph: its shapes are drawn; click one to move (W), turn (E) or size (R)
  it with the widget (a tapered capsule: X the +Z end's radius, Y the -Z end's, Z the length); Delete removes the
  selected shape (the node's own). The simulated bones, their angle limits, bone constraints and each bone's place along
  its chain are drawn too (Debug), and the viewport says why the node does not run, when it does not.
* **Export For Game.** In the node's details, Create a Character > Export For Game writes every Kawaii Dynamic Motions node of the
  AnimBlueprint (in the order the graph runs them) as one of the game mod's `"kawaii"` entries:
  `Saved\KawaiiPhysics\<AnimBlueprint>Kawaii.json`, and to the clipboard. Put it in the game mod's `compat` folder
  (`End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat`). The entry's models (empty: the AnimBlueprint's preview
  mesh), paks and Bonamik switch come from the node you click it on (Export For Game settings). The game mod (3.14.2 or
  later) runs up to 64 nodes on a model.
* **Import From Game** (1.8). The other way: a `"kawaii"` entry of a compat file (the game mod's `compat` folder, or one
  exported) made back into nodes, every setting, curve, shape, bone constraint and (1.9) motion as the game reads them
  (the game mod's own parser reads the file), with the entry's Export For Game settings on each node, so you can preview,
  tune and export it again.
  * Right-click a skeletal mesh > **Import Kawaii Dynamic Motions From Game...**: pick the file; the entry listing that mesh (or
    the file's only one; else you pick it) goes into `<Mesh>_KawaiiPhysics`, an AnimBlueprint beside the mesh (made, or
    updated when it is there), after an animation of the skeleton when it has one, then opened.
  * Right-click an AnimBlueprint > **Import Kawaii Dynamic Motions From Game...**, or **Import From Game...** in a node's
    details (Create a Character): its nodes (one chain of them) are replaced by the entry's, linked where they were;
    an AnimBlueprint without any gets them before its Output Pose.
  * **Window > Import Kawaii Dynamic Motions From Game (every entry)...**: pick the file; every entry goes into an AnimBlueprint
    of its model's, `<Model>_KawaiiPhysics` beside the model (made, or updated when it is there; a second entry for
    the same model into `<Model>_KawaiiPhysics_2`), its model being the first of the entry's models the project has
    (one ending in `*`: the first skeletal mesh whose path starts so and whose skeleton has the entry's bones). An
    entry whose models are not in the project is said and left out: right-click a model of yours > Import Kawaii Dynamic
    Motions From Game... and pick it. The AnimBlueprints are shown in the Content Browser.
  * Compiled and saved; the notification (and the Output Log, LogKawaiiPhysicsImport) says what was done and names the
    bones the entry has that the skeleton has not.
  * For scripts (Python: `unreal.KawaiiPhysicsGameImport`): `list_game_entries(json_path)`,
    `import_from_game(json_path, mesh, anim_blueprint_path, entry_index)`, (1.9)
    `import_from_game_with_animation(json_path, mesh, anim_blueprint_path, entry_index, animation)`,
    `import_into_anim_blueprint(json_path,
    anim_blueprint, entry_index)`, `import_all_from_game(json_path, folder)` (folder empty: beside each model) and
    `export_anim_blueprint_for_game(anim_blueprint)`.

**Editor only.** The game has no KawaiiPhysics module: an AnimBlueprint with this node must not be cooked into a game
pak. Keep the nodes in an AnimBlueprint you only preview with (a copy of the character's), and let the game run them
from the exported file.

Built for the End editor with `Tools\RebirthSkelCompat\run_cacs3170_install.cmd` (1.10, with the game mod 3.17.0 and the
kawaii files' sync bones; close the editor and the game first; 1.9 came with
`Tools\RebirthSkelCompat\run_kawaii_dynamic_motions_install.cmd`).
