# Self-test step 2 (a fresh editor process): the saved editable CharaSpec loads back with its rows and cooks the same.
import json, os, traceback
import unreal

L = unreal.RebirthDataObjectLibrary
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RebirthDataObjectTests')
results = {}

def log(key, value):
    results[key] = value
    unreal.log('RRDO-TEST %s: %s' % (key, value))

def call(fn, *args):
    r = fn(*args)
    if r is None:
        return 'FAILED (see log)'
    return list(r) if isinstance(r, (tuple, list)) else r

RETAIL = '/Game/RebirthDataObjectTests/CharaSpecRetail'
PROJECT = '/Game/DataObject/Resident/CharaSpec'
COOKED = '/Game/RebirthDataObjectTests/Cooked/CharaSpec'
NEW_ROW = 'PC0100_00_TestChar_Standard'

try:
    names = L.get_data_object_row_names(COOKED)
    log('reloaded_rows', len(names))
    log('reloaded_has_new_rows', [str(n) for n in names if str(n).startswith('PC0100')])
    log('reloaded_new_model', L.get_data_object_row_field(COOKED, NEW_ROW, 'ContentsModel'))
    log('reloaded_new_id', L.get_data_object_row_field(COOKED, NEW_ROW, 'CharaID'))
    log('reloaded_new_ai', L.get_data_object_row_field(COOKED, NEW_ROW, 'End2AIList_Array'))
    log('reloaded_new_scale', L.get_data_object_row_field(COOKED, NEW_ROW, 'ScaleMax'))
    log('reloaded_retail_rows', len(L.get_data_object_row_names(RETAIL)))
    log('cook_edited_again', call(L.cook_data_object_to_file, COOKED, os.path.join(OUT, 'CharaSpecEdited2.uasset')))
    log('cook_retail_again', call(L.cook_data_object_to_file, RETAIL, os.path.join(OUT, 'CharaSpecRetail2.uasset')))
    log('cook_project_again', call(L.cook_data_object_to_file, PROJECT, os.path.join(OUT, 'CharaSpecProject2.uasset')))
    results['ok'] = True
except Exception:
    results['exception'] = traceback.format_exc()
    unreal.log_error(results['exception'])

with open(os.path.join(OUT, 'step2.json'), 'w') as f:
    json.dump(results, f, indent=1)
