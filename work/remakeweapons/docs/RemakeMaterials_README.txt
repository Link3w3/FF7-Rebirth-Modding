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

Material instances (run_import_remake_mis.cmd, editor closed; about 20-40 minutes):
  1. rebuilds the RebirthMaterialPreview plugin: it now sets static switches on saved instances
     (Python: unreal.RebirthMaterialDiagnosticsLibrary.set_material_instance_static_parameters)
  2. /Game/GameContents/Renderer/MaterialInstance/*   the game's 385 renderer instances on the Remake masters
     /Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Material and EB0021_01_Sephiroth_Transform/Material:
       Sephiroth's 21 instances, children of those, and their 37 textures at the game's paths
  Status: build\status_mis.txt   Results: C:\FF7R2UProj\Saved\RemakeMaterials\mis_result.json
  The game's overrides this engine has no setting for (extra scene depth, custom render passes, volumetric lighting
  modes, vertex modifier, velocity) are listed per instance in the results as not_in_this_engine.
  Normal maps the masters unpack themselves (sampled as Linear Color in the game's masters) are imported as BC7 linear
  textures with the game's two channels (blue 0), not as normal maps.

Sephiroth's models (run_import_remake_sephiroth.cmd, editor closed; a few minutes):
  /Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00 (+ EB0021_00_Skeleton, shared)
  /Game/GameContents/Character/Enemy/EB0021_01_Sephiroth_Transform/Model/EB0021_01_Body and EB0021_01_Wing
  from _build\remake_models\*.fbx (LOD 0), with his material instances on their slots.
  Status: build\status_seph.txt   Results: C:\FF7R2UProj\Saved\RemakeMaterials\sephiroth_result.json
  With the editor open instead: Output Log > Cmd:
    py "C:/FF7R2UProj/Tools/RemakeMaterials/reimport_remake_sephiroth.py"
  (closes those meshes' editor tabs, re-imports the three models, puts the instances back, keeps the editor open)
  2026-10-21: the first FBX files had their normals and UVs under a mapping word the FBX reader does not know, so the
  imported meshes sampled one texel of every texture (flat colours, hair clipped away). Fixed files replaced them;
  the old ones are in _build\remake_models\_old_bycontrolpoint_20261021. Re-import once to pick up the fix.

Master fixes (2026-10-21), in build_remake_materials.py / remake_editor_spec.json, so a full rebuild keeps them:
  EndMaterial_Skin, EndMaterial_Blood (Preintegrated Skin): Subsurface Color wired to black. The game's shader stores
    no subsurface colour (its custom data is 0, 0, 0, 1); left unwired, this engine uses white and adds it to the skin
    under sky and bounce light, so the skin came out white.
  EndMaterial_Hair (Hair): a "Rebirth Hair Data" output (the RebirthMaterialPreview plugin) fed the game's UV1 bent
    normal (world, * 0.5 + 0.5), which is what the game stores in custom data for hair; the End engine's recovered hair
    lighting reads it. (Left out, with a note in the results, in an editor without the plugin.)
  To apply them to the masters already in the project without a full rebuild:
    with the editor open: Output Log > Cmd:  py "C:/FF7R2UProj/Tools/RemakeMaterials/patch_remake_masters.py"
    or with it closed:    run_patch_remake_masters.cmd
  (rebuilds those three masters in place, puts the game's static switches back on their renderer instances, compiles
   those and Sephiroth's; Results: Saved\RemakeMaterials\patch_result.json and patch_build_result.json)
  The previous builder and spec: C:\FF7R2UProj\_mod_backups\RemakeMaterials_20261021_215604

Other characters (remake_character.py, 2026-10-22): one job file per character, run in the OPEN editor
  remake_<who>_job.json names the material data (remake_<who>_mis.json: its textures and material instances), its
  models (FBX in _build\remake_models) and its Bonamik (the game's file, in Saved\RemakeBonamik). The steps:
    textures   the PNGs (made from the game's textures) imported at the game's paths, with the game's settings
    instances  its material instances on the Remake renderer instances above, each compile-checked
    models     its models (LOD 0, the root resting flat), its instances on their slots
    bonamik    its Bonamik converted to Rebirth's and put on its model's Bonamik Data List
  Output Log > Cmd:
    py "C:/FF7R2UProj/Tools/RemakeMaterials/remake_character.py" "C:/FF7R2UProj/Tools/RemakeMaterials/remake_cloud_job.json"
  Results: Saved\RemakeMaterials\<job name>_result.json. Running it again re-imports in place.
  Remake Cloud (PC0000_00, his standard look): /Game/GameContents/Character/Player/PC0000_00_Cloud_Standard
    Model\PC0000_00 (+ PC0000_00_Skeleton, 547 bones) with his 12 instances, Material\*, Texture\* (25 of his + the
    common Common_Detail_Fabric_N; his other common textures came with Sephiroth's), Model\PC0000_00_BNM.
  The files a job reads (the PNGs, the FBX, the material data, the Bonamik file) are made from the game's own files
  outside the editor for now.

Sephiroth's animations (import_remake_anims.py, 2026-10-22): FF7 Remake's EB0021 animations, run in the OPEN editor
  /Game/GameContents/Motion/Enemy/EB0021_Sephiroth/<Folder>/<Anim>   all 281 of the game's AnimSequences (Battle00 185,
    Battle01 19, Facial00 23, Neutral00 15, Reaction00 39) on EB0021_00_Skeleton (no mesh, no new skeleton, its rest
    pose as it was; only the curve names below were added to it)
  Output Log > Cmd:
    py "C:/FF7R2UProj/Tools/RemakeMaterials/import_remake_anims.py"                all of them (about 5 minutes)
    py "C:/FF7R2UProj/Tools/RemakeMaterials/import_remake_anims.py" Battle00 0 40  a batch (folder, first, how many)
  Results: Saved\RemakeMaterials\sephiroth_anims_result.json (merged over runs). Running it again re-imports in place.
  The files it reads are made from the game's own files outside the editor: _build\tools\convert_remake_anims.py
  (Python 3 + numpy, anim_fbx.py and the game file readers next to it; REMAKE_GAME = the folder holding the game's
  extracted GameContents, REMAKE_ANIMS_OUT = where the files go; --force writes them all again) decodes the game's
  frames (ACL) into _build\remake_anims\EB0021_Sephiroth\<Folder>\<Anim>.fbx and manifest.json, the way skm_fbx.py
  wrote the models (mirrored in y, the root resting flat), so the frames fit the skeleton above.
  Each animation has the game's frames (30 a second, the same frame count and length), tracks only for the bones the
  game's sequence animates (the others follow the mesh's rest pose, as in the game), the root bone's motion as
  authored, root motion on as in the game (off for the 28 that turn it off; root lock forced for the 27 that force
  it), its rate scale and its float curves (AutoSaccadeX/Y, Attach_Item_0, blendOrient1, blendPoint1: the game's
  linear keys; a constant key holds until just before the next). The six B_*_Add are additive (local space) again,
  against their base sequence's first frame, as in the game.
  Checked against the game's frames (Saved\RemakeMaterials\sephiroth_anims_verify.json): every tracked bone of every
  animation within 0.0003 cm and 0.0002 degrees, the key bones (root, pelvis, head, hands, feet, weapons, face)
  within 0.003 cm, the additive deltas within 0.00002.
  Not brought over: the game's notifies (sounds, effects, hit and correction windows: 1243 on 198 sequences), its five
  blend spaces (F_Brow, F_Emotion01, F_Eyelid_move01, B_Walk01_Straf, N_Walk01_Turn), its five EndAnimSet packages
  (Battle00, Battle01, Facial00, Neutral00, Reaction00: which animation plays for what) and BeginBlendTime (a
  setting this engine does not have, on PC0002_00_B_AtkBlowAwayD02_0).
  The skeleton as it was before: C:\FF7R2UProj\_mod_backups\sephiroth_anims_20261022T090912Z

Remake characters straight from the game (the Remake Importer, 2026-10-22): run in the OPEN editor
  Rebirth FX > Import FF7 Remake Character...   (Content\Python\rebirth_fx\remake_import.py; the entry is in the menu
  from the next editor start; before that, Output Log > Cmd, Python: import rebirth_fx.remake_import as ri; ri.menu())
  It opens the Remake Importer's window (Tools\RemakeImporter\remake_importer.py, run with your own Python 3: py -3):
    1. FINAL FANTASY VII REMAKE folder: C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REMAKE by
       default (the folder is remembered in Saved\RemakeImporter\importer_settings.json; nothing else is)
    2. Your AES key (hex): Remake's pak key, typed into that window only. It stays in that program's memory for that run:
       it is never written to a file, a log, the settings or a command line, and the editor never sees it.
       Load characters reads the 25 paks' file lists (about 10 s)
    3. Find / the list: the 294 folders of Character/Player and Character/Enemy with a Model folder (type Tifa, PC0003,
       Sephiroth...). [in the project] marks the ones already here: importing one again replaces it in place
    4. Import (or double-click): its packages are extracted and converted (Tifa: under a minute). The editor then
       imports the job by itself: remake_character.py's four steps (textures, instances, models, bonamik), then the game's
       instances go on the slots whose names are not their instance's (Aerith's PC0003_00_HairCore gets PC0003_00_Hair),
       a summary shows and the Content Browser goes to the character. The editor stays usable while the window is open.
  First run:
    numpy: installed for your Python if it is missing (pip install --user numpy, once; the window says so)
    ooz.dll: Remake's paks are Oodle-compressed and the game ships no Oodle DLL. Build it once: the window's Build
      ooz.dll button, or Tools\RemakeImporter\build_ooz.cmd (Visual Studio 2022's C++ compiler, about a minute; log:
      ooz\build\build.log; it checks the result with remake_importer.py --check). An oo2core_9_win64.dll copied into
      Tools\RemakeImporter works too.
    No tkinter in your Python: the menu entry asks the same questions in a console window instead.
  What an import makes (the files of Remake Cloud's job, in the same places):
    Saved\RemakeImporter\<folder>\remake_<who>_job.json      the job (remake_character.py's format; extra "slots" per
                                                            model and an "importer" section it does not read)
    Saved\RemakeImporter\<folder>\remake_<who>_mis.json      its material data (remake_cloud_mis.json's format)
    Saved\RemakeImporter\<folder>\extracted\End\Content\...   the folder's packages and every one its meshes and instances
                                                            use from elsewhere (Tifa 83 MB; delete when not needed)
    _build\remake_textures\GameContents\...\<texture>.png      mip 0 of each texture its instances use; .exr (half floats)
                                                            for the HDR BC6H ones (the enemies' _EH emissive maps, Red
                                                            XIII's). Common textures already in the project are left out
    _build\remake_models\<mesh>.fbx                           each skeletal mesh of its Model folder: LOD 0, by skm_fbx.py
    Saved\RemakeBonamik\<name>_BNM.uasset/.uexp               each mesh's Bonamik (checked with kh3bonamik.py)
    Saved\RemakeImporter\skeletons.json                       which skeleton of the project each game skeleton became
    Saved\RemakeImporter\result_<time>.json                 what the window handed to the editor (importer_log_<time>.txt:
                                                            its output)
  Skeletons: a mesh whose game skeleton is <mesh>_Skeleton gets it under that name (Tifa, Aerith, Cloud). Other meshes of
    the folder go on the same skeleton. A game skeleton named after no mesh (Guard Scorpion's EB0000_00_Skeleton) is named
    after its first mesh (EB0000_00_Barrier_Skeleton), as the FBX import names new skeletons. A variant goes on its
    standard folder's skeleton when that one is in the project (Cloud's Zack costume on PC0000_00_Skeleton); otherwise
    it gets its own and the summary says to import the standard one first.
  Without the editor: Tools\RemakeImporter\run_remake_importer.cmd (the same window; --console asks in the console;
    --check shows what your Python has), then in the editor, Output Log > Cmd:
      py "C:/FF7R2UProj/Tools/RemakeMaterials/remake_character.py" "<the job it names>"
    or, with the slot fix and the summary:
      import rebirth_fx.remake_import as ri; ri.run_job(r"<the job it names>")
  Remake Tifa (PC0002_00_Tifa_Standard) is converted already, ready to import (Output Log > Cmd, Python):
      import rebirth_fx.remake_import as ri; ri.run_job(r"C:\FF7R2UProj\Saved\RemakeImporter\PC0002_00_Tifa_Standard\remake_tifa_job.json")
    PC0002_00 (481 bones, 89072 vertices, 103206 triangles, 10 slots), 10 instances, 25 textures (+ 9 common ones the
    project has), PC0002_00_BNM. Results: Saved\RemakeMaterials\Remake_Tifa_result.json
  Checked (outside the editor): for Remake Cloud the importer makes his job again exactly: the same FBX byte for byte, the
  same 12 instances, the same 25 texture entries with the same pixels, the same Bonamik files. All 294 folders read
  (387 skeletal meshes, every material instance and texture). Tifa, Aerith, Guard Scorpion (18 meshes, BC6H maps), Cloud's
  Zack costume and Yuffie's Moogle outfit convert without errors. The BC6H decoder gives Pillow's values (to its
  rounding) in all 14 modes.
  Not brought over (as for Cloud): LODs 1 and up, the skeletons' sockets (they come with the importer 1.1, below), the
  physics and capsule shadow assets, KineDriver data, the meshes' EndEmissiveColorUserData, animations. remake_character.py does not apply an instance's
  own static switches or property overrides (none of the game's character instances has any).
  The importer: Tools\RemakeImporter (remake_importer.py the window and command line, remake_paks.py the paks: AES via
  Windows' bcrypt, else the cryptography package, else numpy, each self-tested; remake_convert.py the conversion;
  remake_textures.py PNG/EXR and BC6H; rk418\ the game file readers; ooz\ the decompressor's source).
  Rebirth FX's editor.py and this README as they were before: C:\FF7R2UProj\_mod_backups\remake_importer_20261022T110810Z

Remake weapons (the Remake Importer 1.1, 2026-10-22): the same window, with Show: All / Characters / Weapons
  Rebirth FX > Import FF7 Remake Character or Weapon...   (the menu entry's new name, from the next editor start)
  The list has the 122 folders of Character/Weapon with a Model folder too: Cloud's six swords (WE0000_00 - _05), Barret's
  guns (WE0001), Tifa's gloves (WE0002), Aerith's rods (WE0003), Red XIII's (WE0004), Yuffie's shuriken (WE0005), Sonon's
  sticks (WE0006), the Masamune (WE1021_00_SephirothIllusion_Masamune), the enemies' and the story's weapons. Find takes a
  weapon's name too (BusterSword, Masamune, WE0003).
  A weapon imports the way a character does, at its game path (/Game/GameContents/Character/Weapon/<folder>/Model,
  Material, Texture): its skeletal mesh (LOD 0, the root resting flat) and skeleton, its material instances on the
  Remake renderer instances, its textures, its Bonamik (Tifa's gloves, Sonon's stick, Jessie's gun, Reno's rod...).
  Sockets: every import now brings the game skeleton's sockets onto the imported skeleton (and a mesh's own onto the
    mesh): a weapon's Attach_Chara01 (where the hand holds it), Body_Center01, VFX_Muzzle01 / VFX_EjectionPort01 (the
    guns), Icon_Name01...; a character's Body_Hand_Right01, Face_Eyes01... (Cloud has 28). Sockets on the root bone are
    placed for the flat root, so each stays where it was on the model (the Icon_ sockets were on Remake's turned root).
    They need the Create a Character System editor plugin 1.16 (RebirthRemakeImportLibrary.AddSockets): close the
    editor and run Tools\RebirthSkelCompat\run_build_plugin.cmd once. Until then the summary says the sockets were not
    added and everything else imports as before; import again after the build to add them.
  Shared skeletons: Cloud's swords are all on WE0000_00_Skeleton, Barret's guns on WE0001_00's, Tifa's gloves on
    WE0002_00's, Aerith's rods on WE0003_00's: import the _00 weapon first, then the others go on its skeleton (otherwise
    each gets its own and the summary says so, as for a character's variant).
  Not imported: the four cartridges that are static meshes (WE9000_01, WE9000_02, WE9002_01, WE9004_01: the importer
    brings in skeletal meshes only), and as for characters LODs 1 and up, the physics and capsule shadow assets,
    KineDriver data (Aerith's rods, Yuffie's shuriken), EndEmissiveColorUserData and animations. To carry one in game a
    weapon still needs a blueprint (a copy of one of the game's weapon blueprints with this mesh on it) for a CharaSpec
    row, a weapon swap or a skin's "weapon".
  Checked (outside the editor): the Masamune, the Buster Sword, the Iron Blade, Tifa's Leather Glove (and its Bonamik),
    Aerith's Guard Rod, Barret's Gatling Gun and Yuffie's Shuriken convert without notes, and Cloud as before (now with
    his 28 sockets); the window lists 294 characters and 122 weapons and imports the Buster Sword from Show: Weapons; the
    socket placement matches the engine's FRotator / FQuat math; the FBX files check out (normals, tangents, 2-3 UV
    sets, slots). The files as they were before: C:\FF7R2UProj\_mod_backups\remake_importer_weapons_20261022
