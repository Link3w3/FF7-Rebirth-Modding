FF7 Remake materials for the End editor
=======================================

run_build_remake_materials.cmd     (close the End editor first) builds, at FF7 Remake's own paths and names:
    /Game/GameContents/Renderer/Texture           the masters' default textures (4x4 single colours) and a noise volume
    /Game/GameContents/Renderer/MaterialFunction  Remake's 22 material functions (+ LocalPosition, a helper)
    /Game/GameContents/Renderer/Material          the 21 EndMaterial masters, each compiled
  The editor opens, builds and closes by itself. build\status.txt says how it went;
  C:\FF7R2UProj\Saved\RemakeMaterials\build_result.json has the details (compile errors, notes).
run_check_remake_permutations.cmd  the same, then every one of the game's 385 static permutations compiled in the
  editor (Saved\RemakeMaterials\permutations.json). Takes longer.

Every graph was checked against FF7 Remake's own compiled shaders (every permutation of every master). Their
parameters and static switches have the game's names, so Remake's material instances can use them as parents.

What this editor has no counterpart for:
  - the game's own passes (glass/tear/thin/jewel/water compositing, the distortion): the masters compile and show their
    surface values; the passes are the game's
  - the vertex animation (RigidBody / SoftBody / FluidBody), the PixelContextVector and VertexContextVector values:
    kept in the graph on boxed reroutes labelled "Remake pin ...", not connected
  - the engine values the game gives its materials: blue noise (a per-pixel hash here), the baking flag (rendering a
    reflection capture), its 3D noise textures (RemakeEditorVolumeNoise), the conditional emissive (1)
Running it again rebuilds the same assets in place.
