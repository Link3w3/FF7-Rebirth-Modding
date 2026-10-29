"""Add non-overwriting Zack outfit CharaSpec rows to the extracted CACS table.

Run in the End editor through RebirthEditorLink after backing up the staged
CharaSpec_FromMergedMod package. The rows continue to use Zack's native model
and native CharaSpec data assets, so this does not clone or replace game assets.
"""
import json, os, traceback
import unreal

TABLE = "/Game/DataObject/Resident/CharaSpec_FromMergedMod"
DEST = {
    "PC0009_00_Zack_Standard_ZACK": "PC0009_00_Zack_Standard",
    "PC0009_00_Zack_NoBattle_ZACK": "PC0009_00_Zack_NoBattle",
    "PC0009_00_Zack_Reserve_ZACK": "PC0009_00_Zack_Reserve",
    "PC0009_01_Zack_AerithRibbon_ZACK": "PC0009_01_Zack_AerithRibbon",
    "PC0009_02_Zack_Dirty_ZACK": "PC0009_02_Zack_Dirty",
    "PC0009_03_Zack_StandardWet_ZACK": "PC0009_03_Zack_StandardWet",
}


def main():
    lib = unreal.RebirthDataObjectLibrary
    existing = {str(n) for n in lib.get_data_object_row_names(TABLE)}
    collisions = sorted(set(DEST) & existing)
    missing_sources = sorted(set(DEST.values()) - existing)
    if collisions or missing_sources:
        return {"ok": False, "error": "Preflight failed; no rows were changed.", "collisions": collisions, "missing_sources": missing_sources}

    created = []
    for target, source in DEST.items():
        message = lib.duplicate_data_object_row(TABLE, source, target)
        if message:
            created.append({"source": source, "target": target, "message": str(message)})
        else:
            return {"ok": False, "error": "Row duplication stopped; inspect the table and backup before retrying.", "created": created, "failed_source": source, "failed_target": target}

    field_changes = []
    links = {
        "PC0009_00_Zack_Standard_ZACK": {
            "NoBattleCharaSpec": "PC0009_00_Zack_NoBattle_ZACK",
            "ReserveCharaSpec": "PC0009_00_Zack_Reserve_ZACK",
        },
    }
    for row, fields in links.items():
        for field, value in fields.items():
            result = lib.set_data_object_row_field(TABLE, row, field, value)
            field_changes.append({"row": row, "field": field, "value": value, "message": str(result) if result else ""})

    save_message = lib.save_data_object(TABLE)
    row_names = sorted(DEST)
    check = [str(x) for x in lib.check_chara_spec_rows(TABLE, row_names)]
    return {
        "ok": not check,
        "table": TABLE,
        "created_rows": created,
        "field_changes": field_changes,
        "save_message": str(save_message) if save_message else "",
        "check_problems": check,
        "row_count_after": len(lib.get_data_object_row_names(TABLE)),
    }


try:
    result = main()
except Exception:
    result = {"ok": False, "error": traceback.format_exc()}

project = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
report_path = os.path.join(project, "Saved", "RebirthSkelCompat", "PartyPlayableBuild", "zack_charspec_rows_build.json")
os.makedirs(os.path.dirname(report_path), exist_ok=True)
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
