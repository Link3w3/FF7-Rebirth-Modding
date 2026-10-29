"""Add a non-overwriting Zack-specific Buster Sword row to the extracted CACS table."""
import json, os, traceback
import unreal

TABLE = "/Game/DataObject/Resident/CharaSpec_FromMergedMod"
SOURCE = "WE0000_00_Cloud_BusterSword"
TARGET = "WE0000_00_Cloud_BusterSword_ZACK"


def main():
    lib = unreal.RebirthDataObjectLibrary
    rows = {str(n) for n in lib.get_data_object_row_names(TABLE)}
    if TARGET in rows:
        return {"ok": False, "error": "Target Zack Buster row already exists; no changes made.", "target": TARGET}
    if SOURCE not in rows:
        return {"ok": False, "error": "Source Buster row is missing; no changes made.", "source": SOURCE}
    message = lib.duplicate_data_object_row(TABLE, SOURCE, TARGET)
    if not message:
        return {"ok": False, "error": "Row duplication failed.", "source": SOURCE, "target": TARGET}
    saved = lib.save_data_object(TABLE)
    problems = [str(x) for x in lib.check_chara_spec_rows(TABLE, [TARGET])]
    return {
        "ok": not problems,
        "table": TABLE,
        "source": SOURCE,
        "target": TARGET,
        "duplicate_message": str(message),
        "save_message": str(saved) if saved else "",
        "check_problems": problems,
        "row_count_after": len(lib.get_data_object_row_names(TABLE)),
    }


try:
    result = main()
except Exception:
    result = {"ok": False, "error": traceback.format_exc()}

project = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
path = os.path.join(project, "Saved", "RebirthSkelCompat", "PartyPlayableBuild", "zack_buster_charspec_build.json")
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
