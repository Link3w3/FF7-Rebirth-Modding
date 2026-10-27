# Self-test of data asset and blueprint editing, step 1: a cooked copy of the project's CharaSpec_PC0000_00_Cloud_Standard
# is made editable (its references to game assets that are not in the project must survive), duplicated as a new
# character's CharaSpec that points at a new child blueprint of the game's Vincent blueprint, saved, and cooked to files.
import json, os, traceback
import unreal

A = unreal.RebirthAssetLibrary
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RebirthDataObjectTests')
os.makedirs(OUT, exist_ok=True)
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
BARRET = '/Game/BluePrint/Character/Player/PC0001_00_Barret_Standard'
NEW = '/Game/RebirthDataObjectTests/DataAssets/CharaSpec_PC0100_00_TestChar_Standard'
PARENT = '/Game/BluePrint/Character/Player/PC0011_00_Vincent_Standard'
CHILD = '/Game/RebirthDataObjectTests/BP/PC0100_00_TestChar_Standard'
VINCENT_CLASS = PARENT + '.PC0011_00_Vincent_Standard_C'
CHILD_CLASS = CHILD + '.PC0100_00_TestChar_Standard_C'

try:
    log('header_copy', A.describe_package_header(COPY))
    log('header_vincent', A.describe_package_header(PARENT))
    # A game blueprint loaded with its game references kept, then cooked again (compared with the game's file offline).
    log('barret_stand_ins', A.ensure_game_references(BARRET))
    log('barret_parent', A.get_blueprint_parent(BARRET))
    log('barret_references', list(A.get_asset_references(BARRET)))
    log('cook_barret', call(A.cook_asset_to_file, BARRET, os.path.join(OUT, 'BarretBP_roundtrip.uasset')))
    log('game_reference_packages_barret', list(A.get_game_reference_packages()))

    log('cooked_references', list(A.get_asset_references(COPY)))
    log('make_editable', call(A.make_asset_editable, COPY))
    log('editable_references', list(A.get_asset_references(COPY)))
    log('game_reference_packages', list(A.get_game_reference_packages()))
    class_list = A.get_asset_property(COPY, 'AssetClassList')
    log('asset_class_list', class_list)
    log('asset_data_list', A.get_asset_property(COPY, 'AssetDataList'))
    log('cook_editable', call(A.cook_asset_to_file, COPY, os.path.join(OUT, 'CharaSpecDA_Cloud.uasset')))

    blueprints = list(A.list_game_blueprints('/Game/BluePrint/Character/Player'))
    log('game_blueprints', len(blueprints))
    log('game_blueprints_sample', blueprints[:5])
    log('vincent_parent', A.get_blueprint_parent(PARENT))
    log('create_child', call(A.create_child_blueprint, PARENT, CHILD))
    log('child_parent', A.get_blueprint_parent(CHILD))
    log('child_eye_height_before', A.get_asset_property(CHILD, 'BaseEyeHeight'))
    log('child_set_eye_height', call(A.set_asset_property, CHILD, 'BaseEyeHeight', '71.5'))
    log('child_save', call(A.save_asset, CHILD))
    log('cook_child', call(A.cook_asset_to_file, CHILD, os.path.join(OUT, 'TestCharBP.uasset')))
    # Vincent was loaded (as a reference of the CharaSpec copy) before anything kept its game references.
    log('cook_vincent_without_stand_ins', call(A.cook_asset_to_file, PARENT, os.path.join(OUT, 'VincentBP_nostandins.uasset')))

    log('duplicate', call(A.duplicate_asset, COPY, NEW))
    new_class_list = class_list.replace(VINCENT_CLASS, CHILD_CLASS)
    log('class_list_changed', new_class_list != class_list)
    log('set_class_list', call(A.set_asset_property, NEW, 'AssetClassList', new_class_list))
    log('new_asset_class_list', A.get_asset_property(NEW, 'AssetClassList'))
    log('save_new', call(A.save_asset, NEW))
    log('new_references', list(A.get_asset_references(NEW)))
    log('cook_new', call(A.cook_asset_to_file, NEW, os.path.join(OUT, 'CharaSpecDA_TestChar.uasset')))
    results['ok'] = True
except Exception:
    results['exception'] = traceback.format_exc()
    unreal.log_error(results['exception'])

with open(os.path.join(OUT, 'asset_step1.json'), 'w') as f:
    json.dump(results, f, indent=1)
