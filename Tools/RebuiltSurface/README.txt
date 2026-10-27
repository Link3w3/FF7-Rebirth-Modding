RM_Surface rebuilt - the editable RM_Surface for the End editor

What it is
  /Game/Renderer/Material/RM_Surface, in the game's own place: Final Fantasy VII Rebirth's RM_Surface rebuilt from the game's
  own compiled shaders. Its code was run side by side with all 104 of the game's RMI_Surface_* shaders on the same inputs
  and gives the same results. It declares every RM_Surface parameter and static switch under its own name, so every
  material instance (the game's and yours) has it as its parent with nothing to replace.

What changes in the editor
  Editable instances of RM_Surface compile against it directly. The game's cooked instances (the RMI_Surface_* and the
  characters' own) compile from it too: the RebirthMaterialPreview plugin compiles each one's own static permutation from
  RM_Surface the ordinary way, with its own parent, switches and overrides - nothing is copied or redirected, and their
  packages stay cooked (in memory only). The first time they load that is a few minutes of shader compiling; the shaders
  are cached after that. Console: Rebirth.RecoveredSurfaces.Status (how many are ready or failed);
  Rebirth.RecoveredSurfaces.CompileCooked 0 turns it off (they then render with the default material).
  (Rebirth.RecoveredSurfaces 1 is the older preview that gave each cooked instance a temporary copy instead; it is off in
  Config\DefaultEngine.ini.)

One rule for the graph
  Never use an Unlit Shading Model node in it. UE adds every Shading Model node in a material to its list of shading
  models, and one Unlit among them makes UE treat the whole material as unlit: it then compiles Base Color, Metallic,
  Specular, Roughness, Normal and Ambient Occlusion as constants in every permutation (black, with a plain 0.5 specular).
  The game's Unlit_ switch is Default Lit here with no base colour, metal or reflectance (emissive only, as in game);
  build_rm_surface.py refuses a graph with Unlit in it.

Cooking
  Cooks leave the rebuilt RM_Surface out (the RebirthMaterialPreview plugin's cook skip, the same one that leaves out the
  game's cooked textures; the cook log says "The rebuilt RM_Surface ... is left out of this cook"). Mods keep referencing
  RM_Surface and the game loads its own, so everything that uses it is unchanged in game.
  An instance whose static switches (or blend mode) differ from the game instance it is made from - or one made
  directly from RM_Surface with switches of its own - won't render right in game yet: the game's shaders for a new
  permutation have to come from the game's own base pass, which is the next step. Instances of the game's
  RMI_Surface_* that only change parameter values and textures (the usual way) work in game as before.

The built material (no build needed)
  This folder has the built RM_Surface and everything it uses, in the folders they go in:
    Content\Renderer\Material\RM_Surface.uasset    the material      -> <End project>\Content\Renderer\Material\
    Content\Renderer\Texture\  (13 textures)        its parameters' default textures (the game's own small solid-colour
                                                    ones, cooked)     -> <End project>\Content\Renderer\Texture\
    Engine\Content\EngineResources\SpatiotemporalBlueNoiseVolumeSource   the game's blue noise texture its code samples
                                                    (cooked)          -> <engine>\Engine\Content\EngineResources\
  Close the End editor first. If the game's cooked RM_Surface (RM_Surface.uasset with an RM_Surface.uexp) is in
  Content\Renderer\Material, move both out of Content (keep them to go back), then copy RM_Surface.uasset in. Textures
  you already have can stay. <engine> is the engine the End editor runs from (its log, Saved\Logs\End.log, names it on
  the "Base Directory" line).
  It also needs, from this repo: the RebirthMaterialPreview plugin (EndProject\Plugins; its Rebirth Surface, Hair and Eye
  output nodes are in the graph, and it compiles the cooked instances), RebirthSafeLoad and EndProject\Config (the
  editor loads the cooked textures with them). The engine's own DefaultBuffer comes with the community engine.
  The first time the editor opens it, the shaders compile for a few minutes.

How to build it
  Close the End editor, run run_build_rebuilt_surface.cmd. It rebuilds the plugin, moves the game's cooked RM_Surface into
  C:\FF7R2UProj\_mod_backups, opens the editor once to build the material and compile the game's 104 permutations of
  it, and closes the editor. Status: build\status.txt.
  restore_cooked_rm_surface.cmd puts the cooked RM_Surface back.

Your own version
  Duplicate RM_Surface to your own folder and change the graph or the code of its "RMS" node. For now that is for the
  editor: a new material needs the same next step (the game's own base pass) to render right in game.
