# Builds your playable Sephiroth's winged (Battle02) and flying (Battle03) moves with RebirthSkelCompat's move builder
# (the Move Maker's Build): every move made from the transformed Sephiroth's animation with your Sephiroth's own gameplay
# notifies (damage, combo and cancel windows), lined up on its hits. Run by run_build_sephiroth_forms.cmd (editor closed).
# Plan: sephiroth_forms_plan.json next to this file. Results: Saved\RebirthSkelCompat\SephirothForms\build_result.json.
import json, os, traceback
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = json.load(open(os.path.join(HERE, 'sephiroth_forms_plan.json')))
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'SephirothForms')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'build_result.json')
results = {'steps': []}


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('SEPHFORMS %s: %s' % (key, str(value)[:2000]))
    json.dump(results, open(RESULT, 'w'), indent=1)  # written after every step, so a stop shows where it was


def setp(obj, names, value):
    """set_editor_property under the first name that works (Python names differ for keywords such as As)."""
    last = None
    for name in names if isinstance(names, (list, tuple)) else [names]:
        try:
            obj.set_editor_property(name, value)
            return
        except Exception as ex:
            last = ex
    raise last


def soft_object(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError('does not load: ' + path)
    return asset


try:
    if os.path.exists(RESULT):
        os.replace(RESULT, RESULT + '.previous')
    results = {'steps': []}

    # 1. The asset registry knows the folders the build looks in (a commandlet does not scan everything first).
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    folders = ['/Game/Motion/Player/PC0010_Sephiroth', '/Game/Motion/Player/PC0010_Sephiroth_Transform', '/Game/Motion/Player/PC0000_Cloud',
               '/Game/RebirthSkelCompat', '/Game/Animation/CompressionSettings', '/Game/Character/Player/PC0010_00_Sephiroth_Standard',
               '/Game/DataAsset/Game/CharaSpec']
    registry.scan_paths_synchronous(folders, True)
    log('scanned', folders)

    # 2. The data object (made once, then updated).
    path = PLAN['data_object']
    folder, name = path.rsplit('/', 1)
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        data = unreal.EditorAssetLibrary.load_asset(path)
        log('data_object', 'loaded ' + path)
    else:
        data = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.EndSkeletonCompatDataObject, None)
        log('data_object', 'created ' + path)
    if data is None:
        raise RuntimeError('the data object could not be made')

    # 3. The animation set row: your Sephiroth's rows, two more battle packs from the transformed Sephiroth, the moves.
    row = unreal.EndAnimSetRow()
    setp(row, ['enabled', 'b_enabled'], True)
    setp(row, 'characters', PLAN['characters'])
    sources = []
    for item in PLAN['battle']:
        source = unreal.EndAnimSetSource()
        setp(source, 'path', item['path'])
        setp(source, ['as_', 'as', 'As'], item['as_'])
        sources.append(source)
    setp(row, 'battle', sources)
    setp(row, 'character_skeleton', soft_object(PLAN['character_skeleton']))
    setp(row, 'build_folder', PLAN['build_folder'])
    setp(row, 'requires_paks', PLAN['requires_paks'])
    limits = []
    for item in PLAN['limit_breaks']:
        limit = unreal.EndLimitBreak()
        setp(limit, 'animation', item['animation'])
        setp(limit, 'then_play', item['then'])
        limits.append(limit)
    setp(row, 'limit_breaks', limits)
    moves = []
    for item in PLAN['moves']:
        move = unreal.EndAnimSetMove()
        setp(move, 'name', item['name'])
        setp(move, 'set', item['set'])
        setp(move, 'animation', item['animation'])
        setp(move, ['build', 'b_build'], bool(item['build']))
        if item['build']:
            setp(move, 'notifies_from', item.get('notifies_from', ''))
            setp(move, 'retarget', unreal.EndMoveRetarget.PROPORTIONS)
            setp(move, ['keep_source_effects', 'b_keep_source_effects'], True)
        moves.append(move)
    setp(row, 'moves', moves)
    setp(data, 'animation_sets', [row])
    setp(data, 'build_chunk', PLAN['build_chunk'])
    game_dir = unreal.DirectoryPath()
    setp(game_dir, 'path', '')
    setp(data, 'game_directory', game_dir)  # the compat file goes to Saved; it is installed with the pak
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)
    log('row', '%d moves (%d to build)' % (len(moves), sum(1 for m in PLAN['moves'] if m['build'])))

    # 4. Build every move with Build on (the Move Maker's builder), then export the compat file and validate.
    def run(function, label):
        try:
            data.call_method(function)
            report = data.get_editor_property('last_result')
        except Exception as ex:
            report = 'call_method %s failed (%s)' % (function, ex)
            if function == 'BuildMoves':
                value = data.build_move_animations()
                report += '\nbuild_move_animations: ' + ('FAILED (see the log)' if value is None else str(value))
            elif function == 'ExportJson':
                value = data.write_runtime_json()
                report += '\nwrite_runtime_json: ' + ('FAILED (see the log)' if value is None else str(value))
        open(os.path.join(OUT, label + '.txt'), 'w', encoding='utf-8').write(report)
        first = report.split('\n', 1)[0]
        log(label, first)
        return report

    run('BuildMoves', 'build_moves')
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)
    run('ExportJson', 'export_json')
    run('Validate', 'validate')
    log('done', True)
except Exception:
    log('error', traceback.format_exc())
