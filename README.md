# FF7 Rebirth Modding

Source code, configs and tools for FINAL FANTASY VII REBIRTH mods by Kade (Link3w3), made with Sandalphon.

The main project is **Create a Character System** (CACS, formerly RebirthSkelCompat; folders, files and code keep that
name). It's a UE4SS C++ mod that makes new playable characters work in Rebirth. It covers skeleton compatibility,
animation sets, forms, skins, Kawaii Dynamic Motions physics, the Customization menu and character swaps on the
CHARACTER page. The End editor plugins and Python tools around it build the characters, moves, skins, sound banks
and game containers.

## Layout

| Folder | What it is |
|---|---|
| `CreateACharacterSystem/` | The game mod (UE4SS C++ DLL): `src/` (RebirthSkelCompat.cpp, SkelCompatCore.hpp, KawaiiSolver.hpp, AclDecode.hpp), `tests/`, `build_dll.py` and the build, install and test scripts. `README.md` documents the mod, and `mod/README.txt` is the README that ships with it. |
| `EndProject/Plugins/` | End editor plugins: **RebirthSkelCompat** (Skeleton Compatibility data object, Move Maker, Skin Maker, Parts Builder, AnimBlueprint Maker, sound banks), **RebirthMaterialPreview**, **RebirthSafeLoad**, **RebirthFxLiveLink**, **KawaiiPhysics** (the Kawaii Dynamic Motions fork, MIT), **EndAssetTools**, UKingMat (docs only). |
| `EndProject/Source/` | Edits to the End project's modules: the ENDEditor anim graph nodes for the game's End nodes, and the EndDataObject fixes. |
| `EndProject/Config/`, `EndProject/Mods/`, `EndProject/Saved/RebirthSkelCompat/` | The End project's edited config files, mod plugin descriptors, and the editor data the tools export (data objects, moves, surveys). |
| `GameMods/ue4ss/Mods/` | The game-side mods as installed: RebirthSkelCompat's compat, skins and customization JSONs and README; the Lua mods (SephirothForms with ForceGrabs and MeteorStrike, RebirthLiveLink, RebirthFPSBoost, CutsceneTrace, AutoUsmapDump). |
| `Tools/` | The PC-side tools: character and form builders (Bizarro, Safer, Galian Beast, Chaos, Dirge, Young Sephiroth, Remake, Crisis Core, Dissidia NT, Cloud moveset), the Remake importer and materials, the setup packers, voice tools, title screen and frame-gen scripts. `Tools/RebuiltSurface/` also has the rebuilt **RM_Surface** material itself, ready to copy into an End project with the textures it uses (see its `README.txt`). |
| `work/` | The whole development archive, one folder per task or version, as it was worked on. It includes every DLL version (`cacs*`, `skelcompat*`), editor plugin versions (`plugin*`, `endeditor*`, `kawaii*`), the IoStore / zen package reader and writer (`iostore`, `cs`, `tools`), the CharaSpec and data-table codecs, the SEAD sound bank maker and HCA encoder, the Niagara and Cascade converters (`nconv`, `remakefx`, `kh3fx`), the material and shader tools, Kawaii presets, and the merge build for FullyPlayableCreateACharacterSystemExperience (`merge1027`). |

The newest version of each part is at the top level. `work/` holds the history.

## Building

- **Game mod:** `CreateACharacterSystem/build_dll.py` builds `main.dll` against UE4SS (RE-UE4SS, the build named in
  `CreateACharacterSystem/README.md`) with MSVC. It installs to the game's `ue4ss\Mods\RebirthSkelCompat\dlls\`. The
  core logic (`SkelCompatCore.hpp`, `KawaiiSolver.hpp`) has offline tests in `tests/`.
- **Editor plugins:** copy a plugin folder into an End project's `Plugins\` and build it with the community engine
  the End project uses.
- **Tools:** Python 3. Scripts were run from a working folder called `/work` (the same layout as `work/`) and on the
  PC from `C:\FF7R2UProj`. Paths in them point there.

## Not included

- **Game files:** models, textures, animations, audio, paks, containers, or data extracted from FINAL FANTASY VII
  REBIRTH, REMAKE, Crisis Core, Kingdom Hearts or Dissidia NT. The tools read these from your own copy of the game.
  The one exception is the rebuilt RM_Surface's own requirements in `Tools/RebuiltSurface/`: the game's 13 small
  solid-colour default textures its parameters use and its blue noise texture, so the material opens as it is.
- **Engine changes:** edits to the Unreal Engine source live in the community engine's fork. Epic's license only
  allows engine source in forks of its own repository.
- **Third-party code:** UE4SS, ooz, retoc, UAssetGUI, Cethleann, PyCriCodecs, dlssg-to-fsr3 / FidelityFX, the
  community End project's own plugins, and Epic's engine and shader sources. Get these from their own projects.
- **Keys, logs and crash reports.** Tools that need a pak key read it from an environment variable or ask for it.

See `THIRD_PARTY_NOTICES.md` for the code included here that is based on other projects.

## License

MIT (see `LICENSE`). Code based on other projects keeps those projects' terms, listed in `THIRD_PARTY_NOTICES.md`.
FINAL FANTASY VII and its assets belong to Square Enix, including the RM_Surface textures above (the MIT license doesn't
cover them). Apart from those, this repo doesn't contain them. It isn't affiliated with Square Enix and isn't sold.
