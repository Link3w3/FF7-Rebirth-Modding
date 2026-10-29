"""Validate Zack mappings against the edited, extracted CACS CharaSpec table.

Run this through RebirthEditorLink in End. A successful report means the rows
are ready in the editor table; the table still needs to be cooked into the CACS
pak before the profile is enabled in game.
"""
import json, os
import unreal

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG = os.path.join(ROOT, "GameMods", "ue4ss", "Mods", "RebirthSkelCompat", "compat", "PlayableZack.json")
CHARSPEC = "/Game/DataObject/Resident/CharaSpec_FromMergedMod"
BATTLE = "/Game/DataObject/Resident/BattlePlayerParameter"
document = json.load(open(CONFIG, encoding="utf-8-sig"))
character = document["characters"][0]
library = unreal.RebirthDataObjectLibrary
rows = {str(x) for x in library.get_data_object_row_names(CHARSPEC)}
mappings = character["charaspecs"]
missing_sources = sorted(set(mappings) - rows)
missing_targets = sorted(set(mappings.values()) - rows)
zack_rows = sorted({target for source, target in mappings.items() if source.startswith("PC0000_")})
zack_problems = [str(x) for x in library.check_chara_spec_rows(CHARSPEC, zack_rows)]
weapon_targets = sorted({target for source, target in mappings.items() if source.startswith("WE0000_")})
weapon_problems = {row: [str(x) for x in library.check_chara_spec_rows(CHARSPEC, [row])] for row in weapon_targets}
battle_rows = {str(x) for x in library.get_data_object_row_names(BATTLE)}
row_jobs = character.get("rows", [])
missing_battle_rows = sorted({r[k] for r in row_jobs for k in ("row", "from") if r.get(k) not in battle_rows})
assets = {
    path: bool(unreal.load_asset(path)) for path in [
        "/Game/Character/Player/PC0009_00_Zack_Standard/Model/PC0009_00_Skeleton",
        "/Game/Character/Weapon/Weapon/WE0000_00_Cloud_BusterSword/Model/WE0000_00",
    ]
}
report = {
    "config": CONFIG,
    "table": CHARSPEC,
    "character": character["name"],
    "mapping_count": len(mappings),
    "weapon_mapping_count": len(weapon_targets),
    "missing_source_rows": missing_sources,
    "missing_target_rows": missing_targets,
    "zack_costume_row_problems": zack_problems,
    "weapon_target_rows": weapon_targets,
    "weapon_row_diagnostics": weapon_problems,
    "missing_battle_player_rows": missing_battle_rows,
    "loaded_assets": assets,
    "ok": not (missing_sources or missing_targets or zack_problems or missing_battle_rows or not all(assets.values())),
    "cook_required": True,
}
project = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
output = os.path.join(project, "Saved", "RebirthSkelCompat", "PartyPlayableBuild", "zack_staged_config_validation.json")
os.makedirs(os.path.dirname(output), exist_ok=True)
json.dump(report, open(output, "w", encoding="utf-8"), indent=2)
