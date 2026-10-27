# UKingMat — Breath of the Wild `uking_mat` for Unreal 4.26 (End project)

A re-implementation of Breath of the Wild's main material shader (`uking_mat`, Wii U
`uking_mat.product.bfsha`) as Unreal Engine 4.26 materials, plus an importer that turns the
materials of a BotW model (`.sbfres`) into material instances. Built for the End project
(FF7R2UProj / UnrealEngine-CE). It is a content-only plugin: there is nothing to compile or run by hand —
it sets itself up when the editor starts.

The shader logic was recovered by decompiling the Wii U shader microcode in the archive and checking
the re-implementation numerically against the decompiled programs (see "Accuracy").

## Quick start (no commands)

1. **Open the End project** (`C:\FF7R2UProj`) in the editor as usual. The plugin is in `Plugins\UKingMat` and
   switches itself on.
2. **First start only:** once the editor has loaded, a progress bar builds the BotW materials and a message
   lists what was made (`/Game/UKing/Materials`). Unreal then compiles their shaders in the background — the
   "Compiling Shaders" counter at the bottom right; the first time this takes a few minutes. Nothing to click
   besides OK. (After a plugin update the materials are rebuilt the same way.)
3. A new menu, **UKing (BotW)**, is in the editor's top menu bar (next to File, Edit, Window, Help).

## Importing a BotW model

1. **Export from Switch Toolbox** (or similar): the model as FBX, and the textures of
   `<Model>.Tex1.sbfres` / `.Tex2.sbfres` as PNG/DDS. **Keep the original texture names.**
2. **Import into Unreal** as usual (drag and drop):
   - the mesh (Skeletal Mesh for characters). Keep the material slot names — they are the BotW material names.
   - the textures, anywhere under Content, with default settings (normal maps may stay as Unreal detects
     them; the shader decodes BotW normals itself). Keep `<Model>.Tex1.sbfres` next to the `.sbfres` you import
     in step 3: the importer reads it to give every texture the right sRGB setting (BotW's masks are linear).
3. In the Content Browser **click your mesh** (so it is selected), then
   **UKing (BotW) > Import BotW Model (.sbfres)...** and pick the model's `.sbfres` (e.g. `Link.sbfres`).

   Every BotW material becomes a material instance `MI_<material>` in `/Game/UKing/Instances/<model>`, with its
   textures, colours, values, texture transforms, alpha test, wind and two-sidedness, and the instances are put
   on the selected mesh's slots (matched by slot name). A message tells you how many slots were filled and which
   textures it could not find. Textures are found by name anywhere in the project.

   Missing textures? Import them (keeping their names) and run the import again — it updates the instances.

## The UKing (BotW) menu

| Entry | What it does |
|---|---|
| Import BotW Model (.sbfres)... | the import above (Default Lit, uses Rebirth's lighting) |
| Import BotW Model (Toon Look)... | the same with BotW's own toon lighting (Unlit, settings in `MPC_UKing`) |
| Assign Materials To Selected Mesh | puts already imported `MI_<slot name>` instances on the selected mesh(es) |
| Rebuild UKing Materials | rebuilds `M_UKing_Mat`, `M_UKing_Mat_Toon` and `MPC_UKing` |
| Open Guide | this file |

What gets built (`/Game/UKing/Materials`):
- `M_UKing_Mat` — Default Lit master; every `uking_mat` option is a parameter (good for experimenting).
- `M_UKing_Mat_Toon` — the same inputs with BotW-style toon lighting (Unlit).
- `MPC_UKing` — shared sun direction/colour, ambient, toon and wind settings.
- `Generated/M_UKing_<hash>` — made by the importer: a copy of the shader with one material's options baked in,
  so the shader compiler strips every feature that material does not use. Materials with the same options share one.

## If something goes wrong

- Errors show in a message box; the details are in the Output Log (Window > Developer Tools > Output Log) —
  type `UKingMat` in its search box. The log file is `C:\FF7R2UProj\Saved\Logs\End.log`.
- No **UKing (BotW)** menu: check Edit > Plugins that **Python Editor Script Plugin**, **Editor Scripting
  Utilities** and **UKingMat** are enabled, then restart the editor.
- Materials look black / show the default checker while shaders compile: wait for the shader counter to finish.
- BotW wind / vertex animation needs Unreal's World Position Offset input, which Python in UE 4.26 cannot reach;
  UKingMat connects it through the End project's **RebirthMaterialPreview** plugin. Without that plugin the
  materials still build, just without wind (the build message says so).

## Contents

```
Plugins/UKingMat/
  UKingMat.uplugin
  README.md                         this file
  Docs/uking_mat_reference.md       what every option / source / combiner does
  Content/Python/
    init_unreal.py                  run by the editor at startup: menu + first-start build
    ukingmat_menu.py                the UKing (BotW) menu
    ukingmat_build.py               builds the materials
    ukingmat_import.py              imports BotW materials as material instances
    UKingMatCore.hlsl               the shader itself (shared by every material)
    ukgen.py, ukpack.py             custom-node code generation / option packing
    bfres_wiiu.py                   Wii U BFRES material reader (also a command-line tool)
    uking_mat_options.json          option defaults from the shader archive
    textures/                       neutral default textures
```

## Advanced: Python

Everything the menu does is plain Python (Output Log, input box switched from `Cmd` to `Python`):

```python
import ukingmat_build; ukingmat_build.build_all()            # rebuild the masters

import ukingmat_import as uk
uk.import_bfres(r'D:/BotW/Model/Link.sbfres',
                texture_folder='/Game/Characters/Link/Textures',  # where to look for the textures
                dest='/Game/Characters/Link/Materials',           # where the MI_ assets go
                tex_bfres=[r'D:/BotW/Model/Link.Tex1.sbfres'],    # optional: sRGB + channel info
                mesh='/Game/Characters/Link/SK_Link')            # optional: fills the mesh's slots
```

Options: `specialized=False` (use `M_UKing_Mat` + option parameters instead — slower shaders, but everything
editable in the instance), `toon=True`, `model='Name'` (only one model of the file), `apply_wrap=False` (do not
touch texture address modes), `root='/YourModPlugin/UKing'` (keep the UKing materials inside a mod plugin so
Alpakit packages them; call `ukingmat_build.set_root('/YourModPlugin/UKing')` before `build_all()` too).

`uk.import_json(path_or_folder, ...)` accepts the JSON written by `python bfres_wiiu.py model.sbfres -o out.json`
or BfresLibrary material JSON (Switch Toolbox / Track Studio).

## How it maps to Unreal

| BotW | Unreal (M_UKing_Mat, Default Lit) |
|---|---|
| albedo (× vertex AO / bake shadow, as BotW stores it) | Base Color |
| normal (normal map(s), combiners, foliage sphere normals) | Normal (world space) |
| AO (non-vertex AO source) | Ambient Occlusion |
| emission | Emissive × `uk_emissive_scale` |
| specular mask (incl. toon-spec glint pattern) | Specular × `uk_specular_scale` |
| metal (behave 2) | Metallic |
| gloss + gloss intensity | Roughness, between `uk_roughness_rough` and `uk_roughness_gloss` |
| alpha test (`gsys_renderstate` 1) / translucent (2) | Masked / Translucent, `OpacityMask = alpha − gsys_alpha_test_ref_value + 0.5` |
| wind, vertex offset (modify type 1) | World Position Offset |

BotW's own lighting (deferred) is not in the shader archive; the lit master uses Rebirth's lighting with the
values above. `M_UKing_Mat_Toon` reproduces BotW's forward toon lighting instead (hard N·L step at
`ToonParams.x`, sharpness `ToonParams.y`, behave-1 skin glint) from `MPC_UKing` (no shadows: Unlit).

Material parameters of note: `uk_unit_scale` (Unreal units per BotW unit, 100), `uk_flip_green`
(if normal maps look inverted), `uk_object_random` (BotW per-object random for offset SRTs),
`uk_time_scale`. `MPC_UKing`: `SunDirection` (world direction the light travels), `SunColor`,
`AmbientColor`, `ToonParams`, `Wind0` (strength, direction x, direction y, time scale), `Wind1` (blend to a
second direction, x, y).

## Material parameters (instances)

Textures `_a0 _s0 _n0 _e0 _t0 _a1` (slots 0–5) and `_v0` (vertex texture) — same names as the BotW samplers.

BotW shader parameters keep their names; scalars are packed in fours:

| Unreal parameter | BotW parameters |
|---|---|
| `const_color0..5` | `const_color0..5` |
| `const_value0_3`, `const_value4_7` | `const_value0..3`, `const_value4..7` |
| `const_vector0`, `const_vector1` | `const_vector0/1` |
| `tex_srtK_m`, `tex_srtK_t` | `tex_srtK` as matrix: `u' = u·m.x + v·m.z + t.x`, `v' = u·m.y + v·m.w + t.y` (importer converts TexSrt, Maya/Max/Softimage modes) |
| `indirect_scale0..5` | `indirect_scale0..5` (xy) |
| `texture_array_index0_3`, `texture_array_index4_5` | `texture_array_index0..5` |
| `gsys_bake_st0/1` | `gsys_bake_st0/1` |
| `uking_wind` | `uking_wind_vtx_transform_intensity`, `_lie_intensity`, `_lie_height` |
| `gsys_alpha_test_ref_value` | `gsys_alpha_test_ref_value` |

### Options (only in `M_UKing_Mat` instances; baked into specialised parents)

Each `opt_*` vector parameter holds four BotW static options (integer values, exactly as in the
BFRES shader assign). `ukpack.pack_options(dict)` does the packing.

| Parameter | x, y, z, w |
|---|---|
| `opt_texcoord0` | `uking_enable_texcoord0`, `uking_texcoord0_mapping`, `uking_texcoord0_srt`, `uking_texcoord0_offset_srt` |
| `opt_texcoord1` | `uking_enable_texcoord1`, `uking_texcoord1_mapping`, `uking_texcoord1_srt`, `uking_texcoord1_offset_srt` |
| `opt_texcoord2` | `uking_enable_texcoord2`, `uking_texcoord2_mapping`, `uking_texcoord2_srt`, `uking_texcoord2_offset_srt` |
| `opt_texcoord3` | `uking_enable_texcoord3`, `uking_texcoord3_mapping`, `uking_texcoord3_srt`, `uking_texcoord3_offset_srt` |
| `opt_texcoord4` | `uking_enable_texcoord4`, `uking_texcoord4_mapping`, `uking_texcoord4_srt`, `uking_texcoord4_offset_srt` |
| `opt_texcoord5` | `uking_enable_texcoord5`, `uking_texcoord5_mapping`, `uking_texcoord5_srt`, `uking_texcoord5_offset_srt` |
| `opt_texcoord_toon` | `uking_texcoord_toon_spec_mapping`, `uking_texcoord_toon_spec_srt`, `uking_texcoord_toon_spec_offset_srt`, – |
| `opt_proctexcoord01` | `uking_enable_proctexcoord0`, `uking_proctexcoord0_mapping`, `uking_enable_proctexcoord1`, `uking_proctexcoord1_mapping` |
| `opt_proctexcoord2` | `uking_enable_proctexcoord2`, `uking_proctexcoord2_mapping`, –, – |
| `opt_texture0` | `uking_texture0_texcoord`, `uking_texture0_decode`, `uking_texture_array_texture0`, `uking_texture0_post` |
| `opt_texture1` | `uking_texture1_texcoord`, `uking_texture1_decode`, `uking_texture_array_texture1`, `uking_texture1_post` |
| `opt_texture2` | `uking_texture2_texcoord`, `uking_texture2_decode`, `uking_texture_array_texture2`, `uking_texture2_post` |
| `opt_texture3` | `uking_texture3_texcoord`, `uking_texture3_decode`, `uking_texture_array_texture3`, `uking_texture3_post` |
| `opt_texture4` | `uking_texture4_texcoord`, `uking_texture4_decode`, `uking_texture_array_texture4`, `uking_texture4_post` |
| `opt_texture5` | `uking_texture5_texcoord`, `uking_texture5_decode`, `uking_texture_array_texture5`, `uking_texture5_post` |
| `opt_texture6` | `uking_texture6_texcoord`, `uking_texture6_decode`, `uking_texture6_texture`, – |
| `opt_texture7` | `uking_texture7_texcoord`, `uking_texture7_decode`, `uking_texture7_texture`, – |
| `opt_indirect0` | `uking_enable_indirect0`, `uking_indirect0_texcoord`, `uking_indirect0_type`, `uking_indirect0_signed_fetch` |
| `opt_indirect1` | `uking_enable_indirect1`, `uking_indirect1_texcoord`, `uking_indirect1_type`, `uking_indirect1_signed_fetch` |
| `opt_indirect2` | `uking_enable_indirect2`, `uking_indirect2_texcoord`, `uking_indirect2_type`, `uking_indirect2_signed_fetch` |
| `opt_indirect3` | `uking_enable_indirect3`, `uking_indirect3_texcoord`, `uking_indirect3_type`, `uking_indirect3_signed_fetch` |
| `opt_indirect4` | `uking_enable_indirect4`, `uking_indirect4_texcoord`, `uking_indirect4_type`, `uking_indirect4_signed_fetch` |
| `opt_indirect5` | `uking_enable_indirect5`, `uking_indirect5_texcoord`, `uking_indirect5_type`, `uking_indirect5_signed_fetch` |
| `opt_indirect_world_scaling` | bitmask of `uking_enable_indirectK_world_scaling`, –, –, – |
| `opt_color0_cfg` | `uking_enable_calc_color0`, `uking_color0_calc_type`, `uking_color0_clamp01`, `uking_color0_before_normal` |
| `opt_color1_cfg` | `uking_enable_calc_color1`, `uking_color1_calc_type`, `uking_color1_clamp01`, `uking_color1_before_normal` |
| `opt_color2_cfg` | `uking_enable_calc_color2`, `uking_color2_calc_type`, `uking_color2_clamp01`, `uking_color2_before_normal` |
| `opt_color3_cfg` | `uking_enable_calc_color3`, `uking_color3_calc_type`, `uking_color3_clamp01`, `uking_color3_before_normal` |
| `opt_color4_cfg` | `uking_enable_calc_color4`, `uking_color4_calc_type`, `uking_color4_clamp01`, `uking_color4_before_normal` |
| `opt_color5_cfg` | `uking_enable_calc_color5`, `uking_color5_calc_type`, `uking_color5_clamp01`, `uking_color5_before_normal` |
| `opt_color6_cfg` | `uking_enable_calc_color6`, `uking_color6_calc_type`, `uking_color6_clamp01`, `uking_color6_before_normal` |
| `opt_color7_cfg` | `uking_enable_calc_color7`, `uking_color7_calc_type`, `uking_color7_clamp01`, `uking_color7_before_normal` |
| `opt_color8_cfg` | `uking_enable_calc_color8`, `uking_color8_calc_type`, `uking_color8_clamp01`, `uking_color8_before_normal` |
| `opt_color9_cfg` | `uking_enable_calc_color9`, `uking_color9_calc_type`, `uking_color9_clamp01`, `uking_color9_before_normal` |
| `opt_color10_cfg` | `uking_enable_calc_color10`, `uking_color10_calc_type`, `uking_color10_clamp01`, `uking_color10_before_normal` |
| `opt_color11_cfg` | `uking_enable_calc_color11`, `uking_color11_calc_type`, `uking_color11_clamp01`, `uking_color11_before_normal` |
| `opt_color0_src` | `uking_color0_A`, `uking_color0_B`, `uking_color0_C`, `uking_color0_D` |
| `opt_color1_src` | `uking_color1_A`, `uking_color1_B`, `uking_color1_C`, `uking_color1_D` |
| `opt_color2_src` | `uking_color2_A`, `uking_color2_B`, `uking_color2_C`, `uking_color2_D` |
| `opt_color3_src` | `uking_color3_A`, `uking_color3_B`, `uking_color3_C`, `uking_color3_D` |
| `opt_color4_src` | `uking_color4_A`, `uking_color4_B`, `uking_color4_C`, `uking_color4_D` |
| `opt_color5_src` | `uking_color5_A`, `uking_color5_B`, `uking_color5_C`, `uking_color5_D` |
| `opt_color6_src` | `uking_color6_A`, `uking_color6_B`, `uking_color6_C`, `uking_color6_D` |
| `opt_color7_src` | `uking_color7_A`, `uking_color7_B`, `uking_color7_C`, `uking_color7_D` |
| `opt_color8_src` | `uking_color8_A`, `uking_color8_B`, `uking_color8_C`, `uking_color8_D` |
| `opt_color9_src` | `uking_color9_A`, `uking_color9_B`, `uking_color9_C`, `uking_color9_D` |
| `opt_color10_src` | `uking_color10_A`, `uking_color10_B`, `uking_color10_C`, `uking_color10_D` |
| `opt_color11_src` | `uking_color11_A`, `uking_color11_B`, `uking_color11_C`, `uking_color11_D` |
| `opt_color0_ch` | `uking_color0_A_channel`, `uking_color0_B_channel`, `uking_color0_C_channel`, `uking_color0_D_channel` |
| `opt_color1_ch` | `uking_color1_A_channel`, `uking_color1_B_channel`, `uking_color1_C_channel`, `uking_color1_D_channel` |
| `opt_color2_ch` | `uking_color2_A_channel`, `uking_color2_B_channel`, `uking_color2_C_channel`, `uking_color2_D_channel` |
| `opt_color3_ch` | `uking_color3_A_channel`, `uking_color3_B_channel`, `uking_color3_C_channel`, `uking_color3_D_channel` |
| `opt_color4_ch` | `uking_color4_A_channel`, `uking_color4_B_channel`, `uking_color4_C_channel`, `uking_color4_D_channel` |
| `opt_color5_ch` | `uking_color5_A_channel`, `uking_color5_B_channel`, `uking_color5_C_channel`, `uking_color5_D_channel` |
| `opt_color6_ch` | `uking_color6_A_channel`, `uking_color6_B_channel`, `uking_color6_C_channel`, `uking_color6_D_channel` |
| `opt_color7_ch` | `uking_color7_A_channel`, `uking_color7_B_channel`, `uking_color7_C_channel`, `uking_color7_D_channel` |
| `opt_color8_ch` | `uking_color8_A_channel`, `uking_color8_B_channel`, `uking_color8_C_channel`, `uking_color8_D_channel` |
| `opt_color9_ch` | `uking_color9_A_channel`, `uking_color9_B_channel`, `uking_color9_C_channel`, `uking_color9_D_channel` |
| `opt_color10_ch` | `uking_color10_A_channel`, `uking_color10_B_channel`, `uking_color10_C_channel`, `uking_color10_D_channel` |
| `opt_color11_ch` | `uking_color11_A_channel`, `uking_color11_B_channel`, `uking_color11_C_channel`, `uking_color11_D_channel` |
| `opt_normal` | `uking_enable_normalmap`, `uking_normal_color`, `uking_enable_decode_normalmap`, `uking_enable_normalmap2` |
| `opt_normal2` | `uking_normal_color2`, `uking_normalmap_blend_ratio`, `uking_normalmap_blend_channel`, `uking_normalmap_blend_method` |
| `opt_out0` | `uking_albedo_color`, `uking_enable_emission`, `uking_emission_color`, `uking_material_behave` |
| `opt_out1` | `uking_enable_ao`, `uking_ao_color`, `uking_ao_channel`, `gsys_renderstate` |
| `opt_out2` | `uking_transparency_color`, `uking_transparency_channel`, `uking_specmask_scaler`, `uking_specular_channel` |
| `opt_out3` | `uking_metal_color`, `uking_metal_channel`, `uking_grossy_color`, `uking_grossy_channel` |
| `opt_out4` | `uking_grossy_intensity`, `uking_enable_transmission`, `uking_transmission_color`, `uking_transmission_channel` |
| `opt_out5` | `enable_bake_texture`, `bake_shadow_type`, `uking_texcoord_toon_spec_srt` ≥ 0, – |
| `opt_wind` | `uking_enable_wind_vtx_transform`, `uking_wind_vtx_transform_channel`, wind flags (1 normal_lock, 2 lie, 4 height, 8 coreinfo, 16 scale), – |
| `opt_vtxmod0` | `uking_modify_position_type`, `uking_vtx_position_modify_calc_type`, `uking_vtx_position_modify_shadow_only`, `uking_vtx_texture0_texcoord` |
| `opt_vtxmod1` | `uking_vtx_position_modify_A`, `uking_vtx_position_modify_B`, `uking_vtx_position_modify_C`, `uking_vtx_position_modify_D` |
| `opt_vtxmod2` | `uking_vtx_position_modify_A_channel`, `uking_vtx_position_modify_B_channel`, `uking_vtx_position_modify_C_channel`, `uking_vtx_position_modify_D_channel` |
| `opt_inner0` | `uking_enable_inner_light`, `uking_inner_light_mode`, `uking_enable_inner_light_line`, `uking_inner_light_source_position` |
| `opt_inner1` | `uking_inner_light_source_radius`, `uking_inner_light_diffusivity`, `uking_inner_light_source_position_end`, `uking_inner_light_source_radius_end` |
| `opt_normal_modify` | `uking_modify_normal_type`, `uking_vtx_normal_modify_A`, `uking_enable_backface_modify`, – |

## Accuracy

The core shader (`UKingMatCore.hlsl`) and the generated Unreal node code were compiled as GLSL and run
against the decompiled G-buffer programs of the archive (591 option sets, 2 random environments each,
identical pseudo-random textures and uniforms):

| output | matches |
|---|---|
| albedo | 1016 / 1028 |
| normal | 1086 / 1182 |
| emission | 276 / 286 |
| specular mask | 787 / 797 |
| alpha | 344 / 364 |

The remaining cases are translucent G-buffer programs (they blend with the existing G-buffer — Unreal's
translucency does that), screen-space sources (scene colour/depth), a vertex-binormal attribute variant,
and alpha that BotW writes as 1 because the test happens in a depth pre-pass.

## Not reproduced / approximations

- Screen-space sources 8/9 (scene colour) and 500 (scene depth difference) — 0 / constant.
- Procedural textures (`uking_enable_proctexture3..5`, water ripples), texture `post` processing, texture
  arrays (assign the right layer as a normal 2D texture), emission cubemap, proctexcoord 1/2.
- Wind: the gust lookup texture (`gsys_user1`) is replaced by a procedural one, the grass lie-down map is
  neutral, `coreinfo` needs a second vertex colour set that Unreal does not import.
- Gameplay effects (damage flash, mimicry, chemical ice, burning, dissolve) and BotW's deferred lighting.
- Calc type 26 (normal blend): the role of input C is inferred.
- Axes: BotW world/local (x, y, z) = Unreal (x, z, y) / `uk_unit_scale` (standard FBX import). This only
  matters for world-XZ texture mapping and wind direction.

Specialised parents compile quickly and are cheap; the dynamic master evaluates every feature at run time
and is meant for experimenting.
