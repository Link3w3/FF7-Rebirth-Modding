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

**Editor only.** The game has no KawaiiPhysics module: an AnimBlueprint with this node must not be cooked into a game
pak. Keep the nodes in an AnimBlueprint you only preview with (a copy of the character's), and let the game run them
from the exported file.

Built for the End editor with `Tools\RebirthSkelCompat\run_kawaii_plugin_build.cmd` (close the editor first).
