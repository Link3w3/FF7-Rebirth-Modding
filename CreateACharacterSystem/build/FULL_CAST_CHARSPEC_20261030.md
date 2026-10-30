# Full cast CharaSpec build — 2026-10-30

This build adds Barret, Tifa, Aerith, Red XIII, Yuffie, Cait Sith, and Cid as Cloud-slot CACS entries. Each character keeps Cloud's 26 costume/NoBattle rows. The six characters with weapons each get eight distinct Cloud weapon rows mapped to their existing in-game weapons; Cid has no weapon mappings. The resident CharaSpec table adds 230 rows total (34 per armed character and 26 for Cid), taking it from 3,649 to 3,879 rows.

The row-builder clones every source row from the matching Cloud row, preserving its CharaID and other Cloud values. It changes the model reference to the selected native character model; outfit slots without a matching native outfit fall back to that character's standard model. Base rows link to their own cloned NoBattle row. No reserve rows are created. For weapons, the Cloud slots reuse each character's existing weapon models and CharaSpec DataAssets. Red XIII and Cait Sith repeat their last native weapon for Cloud's eighth slot because each has seven weapon rows; Cid has no weapon rows.

Each party entry occupies Cloud's slot and patches pt_Cloud from that character's BattlePlayerParameter row. Cid has no pt_Cid row in the resident table, so Cid temporarily uses pt_Cloud. The CACS character list supplies the runtime PlayerTable additions; there is no separate PlayerTable asset in this project.

Red XIII and Cait Sith use their native ContentsModel assets. Their native AnimBlueprint templates import their character-specific ControlRig classes (`PC0004_00_Rig` and `PC0007_00_Rig`), while the skeleton-family compatibility keeps each receiving skeleton's proportions and sockets. This avoids replacing either animal rig with Cloud's human ControlRig.

Zack's field and hand weapon sockets were inspected from his mesh: `Attach_Weapon01` is on `C_Weapon_b`; `Attach_Weapon_Right01` is on `R_Weapon_a`. The prior socket stand-in remapped the hand socket to `R_Hand_a`, discarding Zack's weapon socket transform. That override and an ignored `weapon_field_socket` animation-set field were removed. His family hub now agrees with Cloud, and the native sockets are retained.

## Outputs

- `build/party_playable_plan_20261030.json`
- `tools/build_party_playable_charspec_rows.py`
- `tools/generate_party_playable_config.py`
- `tools/cook_full_cast_charspec_candidate.py`
- `tools/build_full_cast_charspec_container.py`
- `tools/build_full_cast_cacs_merge.py`
- Merged CACS candidate and report in `work/fixes/full_cast_charspec_20261030/merged_candidate_all_weapons_v2/`

The merge replaces the Resident CharaSpec package in the existing main CACS container and appends the 230 Cloud-slot row DataAssets plus 74 canonical model/weapon CharaSpec DataAssets. It preserves the other 2,726 original chunks. The merged container and matching CACS menu JSON are installed. The previous installed pak/ucas/utoc and JSON are backed up in `work/fixes/full_cast_charspec_20261030/installed_backup_before_full_cast_assets_20261030/`.

The package and config were structurally validated, but they have not been tested in gameplay. The latest reported Zack hit reaction caused a fatal error; the available UE4SS logs do not contain a crash stack for that event, so gameplay testing should start by checking whether Zack still crashes on hit with this update.
