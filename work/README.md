# work/

The development archive: one folder per task, step or version, kept as it was worked on (code, configs, notes and
small data only). The newest versions of the game mod, editor plugins, game configs and PC tools are in the repo's
top-level folders.

Some useful starting points:

| Folder | What |
|---|---|
| `cacs3210/` | Create a Character System 3.21.0 (the newest; `cacs*` and `skelcompat*` are the earlier versions) |
| `plugin121/`, `endeditor119/`, `kawaii426/`, `kdm_install/` | Editor plugin versions: RebirthSkelCompat editor, ENDEditor nodes, Kawaii Dynamic Motions |
| `iostore/`, `cs/`, `tools/`, `charaspecmod/` | IoStore container and zen package reader and writer, CharaSpec frozen-format codec, text resources |
| `merge1027/` | FullyPlayableCreateACharacterSystemExperience: the merged data container, compat files and installer |
| `youngvoice/`, `sorav1018/`, `vinsnd1016/` | SEAD sound bank maker, HCA encoder, bank reader |
| `nconv/`, `remakefx/`, `kh3fx/`, `kh3fx_limit/` | Niagara / Cascade effect converters |
| `remake_mat/`, `rmsurf/`, `custmat/`, `matconv/` | Material and shader tools (RM_Surface, Remake EndMaterials, custom materials) |
| `kawaii_preset/`, `bfs17/`, `pc18/`, `cloudkawaii/` | Kawaii Dynamic Motions presets and character setups |
| `title/` | The Sephiroth title screen builder |

Scripts expect this folder at `/work` and the PC paths of `C:\FF7R2UProj` and the game.
