# KawaiiPhysics for the End editor (UE 4.26), with Create a Character System

KawaiiPhysics (pafuhana1213, MIT License: see LICENSE) 1.7.0 for UE 4.26, with the newest KawaiiPhysics' features fused in,
for FINAL FANTASY VII REBIRTH modding with Create a Character System.

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
* **Export For Game.** In the node's details, Create a Character > Export For Game writes every KawaiiPhysics node of the
  AnimBlueprint (in the order the graph runs them) as one of the game mod's `"kawaii"` entries:
  `Saved\KawaiiPhysics\<AnimBlueprint>Kawaii.json`, and to the clipboard. Put it in the game mod's `compat` folder
  (`End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat`). The entry's models (empty: the AnimBlueprint's preview
  mesh), paks and Bonamik switch come from the node you click it on (Export For Game settings). The game mod (3.14.2 or
  later) runs up to 64 nodes on a model.
* **Import From Game** (1.8). The other way: a `"kawaii"` entry of a compat file (the game mod's `compat` folder, or one
  exported) made back into KawaiiPhysics nodes, every setting, curve, shape and bone constraint as the game reads them
  (the game mod's own parser reads the file), with the entry's Export For Game settings on each node, so you can preview,
  tune and export it again.
  * Right-click a skeletal mesh > **Import KawaiiPhysics From Game...**: pick the file; the entry listing that mesh (or
    the file's only one; else you pick it) goes into `<Mesh>_KawaiiPhysics`, an AnimBlueprint beside the mesh (made, or
    updated when it is there), after an animation of the skeleton when it has one, then opened.
  * Right-click an AnimBlueprint > **Import KawaiiPhysics From Game...**, or **Import From Game...** in a KawaiiPhysics
    node's details: its KawaiiPhysics nodes (one chain of them) are replaced by the entry's, linked where they were;
    an AnimBlueprint without any gets them before its Output Pose.
  * **Window > Import KawaiiPhysics From Game (every entry)...**: pick the file; every entry goes into an AnimBlueprint
    of its model's, `<Model>_KawaiiPhysics` beside the model (made, or updated when it is there; a second entry for
    the same model into `<Model>_KawaiiPhysics_2`), its model being the first of the entry's models the project has
    (one ending in `*`: the first skeletal mesh whose path starts so and whose skeleton has the entry's bones). An
    entry whose models are not in the project is said and left out: right-click a model of yours > Import KawaiiPhysics
    From Game... and pick it. The AnimBlueprints are shown in the Content Browser.
  * Compiled and saved; the notification (and the Output Log, LogKawaiiPhysicsImport) says what was done and names the
    bones the entry has that the skeleton has not.
  * For scripts (Python: `unreal.KawaiiPhysicsGameImport`): `list_game_entries(json_path)`,
    `import_from_game(json_path, mesh, anim_blueprint_path, entry_index)`, `import_into_anim_blueprint(json_path,
    anim_blueprint, entry_index)`, `import_all_from_game(json_path, folder)` (folder empty: beside each model) and
    `export_anim_blueprint_for_game(anim_blueprint)`.

**Editor only.** The game has no KawaiiPhysics module: an AnimBlueprint with this node must not be cooked into a game
pak. Keep the nodes in an AnimBlueprint you only preview with (a copy of the character's), and let the game run them
from the exported file.

Built for the End editor with `Tools\RebirthSkelCompat\run_kawaii_plugin_build.cmd` (close the editor first).
