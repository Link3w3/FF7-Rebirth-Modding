# Self-test step 2 (a fresh editor process): the editable data assets and the child blueprint load back with every
# reference (stand-ins for game assets that are not in the project are created again) and cook the same.
import json, os, traceback
import unreal

A = unreal.RebirthAssetLibrary
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RebirthDataObjectTests')
results = {}

def log(key, value):
    results[key] = value
    unreal.log('RRDA-TEST %s: %s' % (key, value))

def call(fn, *args):
    r = fn(*args)
    if r is None:
        return 'FAILED (see log)'
    return list(r) if isinstance(r, (tuple, list)) else r

COPY = '/Game/RebirthDataObjectTests/DataAssets/CharaSpec_PC0000_00_Cloud_Standard'
NEW = '/Game/RebirthDataObjectTests/DataAssets/CharaSpec_PC0100_00_TestChar_Standard'
CHILD = '/Game/RebirthDataObjectTests/BP/PC0100_00_TestChar_Standard'

try:
    log('reloaded_references', list(A.get_asset_references(COPY)))
    log('reloaded_new_references', list(A.get_asset_references(NEW)))
    log('reloaded_new_class_list', A.get_asset_property(NEW, 'AssetClassList'))
    log('reloaded_child_parent', A.get_blueprint_parent(CHILD))
    log('reloaded_child_eye_height', A.get_asset_property(CHILD, 'BaseEyeHeight'))
    log('game_reference_packages', list(A.get_game_reference_packages()))
    log('cook_editable_again', call(A.cook_asset_to_file, COPY, os.path.join(OUT, 'CharaSpecDA_Cloud2.uasset')))
    log('cook_new_again', call(A.cook_asset_to_file, NEW, os.path.join(OUT, 'CharaSpecDA_TestChar2.uasset')))
    log('cook_child_again', call(A.cook_asset_to_file, CHILD, os.path.join(OUT, 'TestCharBP2.uasset')))
    results['ok'] = True
except Exception:
    results['exception'] = traceback.format_exc()
    unreal.log_error(results['exception'])

with open(os.path.join(OUT, 'asset_step2.json'), 'w') as f:
    json.dump(results, f, indent=1)
