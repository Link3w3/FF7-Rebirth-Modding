# Self-test of the Rebirth data object tools, step 1: every game data object, the CharaSpec import, the project's
# CharaSpec, and a cooked copy made editable, edited (new rows), saved and cooked to files.
import json, os, traceback
import unreal

L = unreal.RebirthDataObjectLibrary
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RebirthDataObjectTests')
os.makedirs(OUT, exist_ok=True)
results = {}

def log(key, value):
    results[key] = value
    unreal.log('RRDO-TEST %s: %s' % (key, value))

def call(fn, *args):
    # A bool function with out parameters returns its out parameters when it succeeds and None when it fails
    # (the failure message is in the log).
    r = fn(*args)
    if r is None:
        return 'FAILED (see log)'
    return list(r) if isinstance(r, (tuple, list)) else r

RETAIL = '/Game/RebirthDataObjectTests/CharaSpecRetail'
PROJECT = '/Game/DataObject/Resident/CharaSpec'
COOKED = '/Game/RebirthDataObjectTests/Cooked/CharaSpec'
NEW_ROW = 'PC0100_00_TestChar_Standard'

try:
    # 1. Every data object in the game, through this project's code.
    log('verify_all', call(L.verify_game_data_objects, '', os.path.join(OUT, 'all_dataobjects.json')))

    # 2. The game's CharaSpec imported to a test path and cooked to a file.
    log('import_retail', call(L.import_data_object_from_game, '/Game/DataObject/Resident/CharaSpec', '', RETAIL))
    log('import_retail_rows', len(L.get_data_object_row_names(RETAIL)))
    log('cook_retail', call(L.cook_data_object_to_file, RETAIL, os.path.join(OUT, 'CharaSpecRetail.uasset')))

    # 3. The project's own CharaSpec (made editable in the editor): cooked to a file only, the asset is not changed.
    log('project_rows', len(L.get_data_object_row_names(PROJECT)))
    log('project_cloud_model', L.get_data_object_row_field(PROJECT, 'PC0000_00_Cloud_Standard', 'ContentsModel'))
    log('cook_project', call(L.cook_data_object_to_file, PROJECT, os.path.join(OUT, 'CharaSpecProject.uasset')))

    # 4. A cooked copy of CharaSpec: loads with every row, becomes editable, cooks back to the same bytes.
    log('cooked_rows', len(L.get_data_object_row_names(COOKED)))
    log('cooked_cloud_model', L.get_data_object_row_field(COOKED, 'PC0000_00_Cloud_Standard', 'ContentsModel'))
    log('make_editable', call(L.make_data_object_editable, COOKED))
    log('editable_rows', len(L.get_data_object_row_names(COOKED)))
    log('cook_roundtrip', call(L.cook_data_object_to_file, COOKED, os.path.join(OUT, 'CharaSpecRoundtrip.uasset')))

    # 5. New rows (a new character), edited, saved, cooked.
    log('duplicate', call(L.duplicate_data_object_row, COOKED, 'PC0000_00_Cloud_Standard', NEW_ROW))
    log('set_model', call(L.set_data_object_row_field, COOKED, NEW_ROW, 'ContentsModel', NEW_ROW))
    log('set_id', call(L.set_data_object_row_field, COOKED, NEW_ROW, 'CharaID', 'PC0100_00'))
    log('set_scale', call(L.set_data_object_row_field, COOKED, NEW_ROW, 'ScaleMax', '1.250000'))
    log('set_ai', call(L.set_data_object_row_field, COOKED, NEW_ROW, 'End2AIList_Array', '("PC0100_00_TestChar_Standard_AIBP","PC0000_00_Cloud_Standard_AIBP")'))
    log('duplicate_numbered', call(L.duplicate_data_object_row, COOKED, 'PC0000_00_Cloud_Standard', 'PC0100_01_TestChar_7'))
    log('edited_rows', len(L.get_data_object_row_names(COOKED)))
    log('new_row_model', L.get_data_object_row_field(COOKED, NEW_ROW, 'ContentsModel'))
    log('save', call(L.save_data_object, COOKED))
    log('cook_edited', call(L.cook_data_object_to_file, COOKED, os.path.join(OUT, 'CharaSpecEdited.uasset')))
    results['ok'] = True
except Exception:
    results['exception'] = traceback.format_exc()
    unreal.log_error(results['exception'])

with open(os.path.join(OUT, 'step1.json'), 'w') as f:
    json.dump(results, f, indent=1)
