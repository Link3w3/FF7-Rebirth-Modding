"""Check Zack's CACS row mappings against the End resident tables and assets."""
import json, os
import unreal

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG = os.path.join(ROOT, "GameMods", "ue4ss", "Mods", "RebirthSkelCompat", "compat", "PlayableZack.json")
CHARSPEC = "/Game/DataObject/Resident/CharaSpec"
BATTLE = "/Game/DataObject/Resident/BattlePlayerParameter"
doc = json.load(open(CONFIG, encoding="utf-8-sig"))
character = doc["characters"][0]
lib = unreal.RebirthDataObjectLibrary
chara_rows = {str(x) for x in lib.get_data_object_row_names(CHARSPEC)}
battle_rows = {str(x) for x in lib.get_data_object_row_names(BATTLE)}
mappings = character["charaspecs"]
missing_sources = sorted(set(mappings) - chara_rows)
missing_targets = sorted(set(mappings.values()) - chara_rows)
targets = sorted(set(v for k, v in mappings.items() if k.startswith("PC0000_")))
problems = [str(x) for x in lib.check_chara_spec_rows(CHARSPEC, targets)]
weapon_targets = sorted(set(v for k, v in mappings.items() if k.startswith("WE0000_")))
row_jobs = character.get("rows", [])
missing_battle_rows = sorted({r[k] for r in row_jobs for k in ("row", "from") if r.get(k) not in battle_rows})
skeletons = [
    "/Game/Character/Player/PC0000_00_Cloud_Standard/Model/PC0000_00_Skeleton",
    "/Game/Character/Player/PC0009_00_Zack_Standard/Model/PC0009_00_Skeleton",
]
assets = {path: bool(unreal.load_asset(path)) for path in skeletons + [
    "/Game/Character/Weapon/Weapon/WE0000_00_Cloud_BusterSword/Model/WE0000_00"
]}
report = {
    "config": CONFIG,
    "character": character["name"],
    "mapping_count": len(mappings),
    "missing_source_rows": missing_sources,
    "missing_target_rows": missing_targets,
    "chara_spec_check_problems": problems,
    "base_game_weapon_rows_present": sorted(set(weapon_targets) & chara_rows),
    "base_game_weapon_rows": weapon_targets,
    "weapon_note": "The selected Buster Sword uses the existing base-game CharaSpec row; the editor's extracted DataAsset lacks cooked blueprint entries, so it is not included in the Zack mod pack.",
    "missing_battle_player_rows": missing_battle_rows,
    "loaded_assets": assets,
    "ok": not (missing_sources or missing_targets or problems or missing_battle_rows or not all(assets.values()) or set(weapon_targets) - chara_rows),
}
project = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
out = os.path.join(project, "Saved", "RebirthSkelCompat", "PartyPlayableBuild", "zack_config_validation.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump(report, open(out, "w", encoding="utf-8"), indent=2)
