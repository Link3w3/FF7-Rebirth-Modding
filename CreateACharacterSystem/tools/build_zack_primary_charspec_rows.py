"""Add Zack's custom outfit/state and Buster rows to Resident CharaSpec."""
import json, os, traceback
import unreal

TABLE = "/Game/DataObject/Resident/CharaSpec"
ROWS = {
    "PC0009_00_Zack_Standard_ZACK": "PC0009_00_Zack_Standard",
    "PC0009_00_Zack_NoBattle_ZACK": "PC0009_00_Zack_NoBattle",
    "PC0009_00_Zack_Reserve_ZACK": "PC0009_00_Zack_Reserve",
    "PC0009_01_Zack_AerithRibbon_ZACK": "PC0009_01_Zack_AerithRibbon",
    "PC0009_02_Zack_Dirty_ZACK": "PC0009_02_Zack_Dirty",
    "PC0009_03_Zack_StandardWet_ZACK": "PC0009_03_Zack_StandardWet",
    "WE0000_00_Cloud_BusterSword_ZACK": "WE0000_00_Cloud_BusterSword",
}


def main():
    lib = unreal.RebirthDataObjectLibrary
    existing = {str(n) for n in lib.get_data_object_row_names(TABLE)}
    collisions = sorted(set(ROWS) & existing)
    missing = sorted(set(ROWS.values()) - existing)
    if collisions or missing:
        return {"ok": False, "error": "Preflight failed; no rows were changed.", "collisions": collisions, "missing_sources": missing}

    created = []
    for target, source in ROWS.items():
        message = lib.duplicate_data_object_row(TABLE, source, target)
        if not message:
            return {"ok": False, "error": "Duplication stopped; restore from backup before retrying.", "created": created, "failed_source": source, "failed_target": target}
        created.append({"source": source, "target": target, "message": str(message)})

    links = {
        "PC0009_00_Zack_Standard_ZACK": {
            "NoBattleCharaSpec": "PC0009_00_Zack_NoBattle_ZACK",
            "ReserveCharaSpec": "PC0009_00_Zack_Reserve_ZACK",
        },
    }
    changed = []
    for row, fields in links.items():
        for field, value in fields.items():
            result = lib.set_data_object_row_field(TABLE, row, field, value)
            changed.append({"row": row, "field": field, "value": value, "message": str(result) if result else ""})

    saved = lib.save_data_object(TABLE)
    pc_rows = sorted(row for row in ROWS if row.startswith("PC0009_"))
    weapon_rows = sorted(row for row in ROWS if row.startswith("WE0000_"))
    return {
        "ok": not lib.check_chara_spec_rows(TABLE, pc_rows),
        "table": TABLE,
        "created_rows": created,
        "field_changes": changed,
        "save_message": str(saved) if saved else "",
        "character_check_problems": [str(x) for x in lib.check_chara_spec_rows(TABLE, pc_rows)],
        "weapon_check_problems": {row: [str(x) for x in lib.check_chara_spec_rows(TABLE, [row])] for row in weapon_rows},
        "row_count_after": len(lib.get_data_object_row_names(TABLE)),
    }


try:
    result = main()
except Exception:
    result = {"ok": False, "error": traceback.format_exc()}

project = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
path = os.path.join(project, "Saved", "RebirthSkelCompat", "PartyPlayableBuild", "zack_primary_charspec_rows_build.json")
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
