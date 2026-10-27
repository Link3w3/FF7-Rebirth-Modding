# Your playable Sephiroth's KH2 form (animation pack Battle04): imports the KH2 animations (key animations made from the
# retargeted FBXs in H:\Exported\Projects\SephiAnims\Kh2Rebirth\Remap) onto his skeleton with Create a Character System's
# Import Key Animations, puts them in the SephirothForms data object as Battle04 moves (with the KH2 swing times as hits)
# on top of his own Battle00 set, and builds them (each with his own animation's gameplay notifies, lined up on the hits).
# His other forms keep their moves; every form casts Meteor with the KH2 sword raise. Run by run_kh2_moves.cmd (editor closed).
# Results: Saved\RebirthSkelCompat\SephirothForms\kh2_result.json, kh2_import.txt, kh2_build.txt, export_json.txt, validate.txt
import json, os, traceback
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = json.load(open(os.path.join(HERE, 'sephiroth_forms_plan.json')))
KH2 = json.load(open(os.path.join(HERE, 'kh2', 'kh2_moves.json')))
KEYS = os.path.join(HERE, 'kh2', 'keys')
# his flying form's locomotion (Battle03), made from the flight in the game's final cutscenes (optional)
FLIGHT_JSON = os.path.join(HERE, 'flight', 'flight_moves.json')
FLIGHT = json.load(open(FLIGHT_JSON)) if os.path.exists(FLIGHT_JSON) else {'moves': []}
FLIGHT_KEYS = os.path.join(HERE, 'flight', 'keys')
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'SephirothForms')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'kh2_result.json')
results = {'steps': []}


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('KH2MOVES %s: %s' % (key, str(value)[:2000]))
    json.dump(results, open(RESULT, 'w'), indent=1)  # after every step, so a stop shows where it was


def setp(obj, names, value):
    last = None
    for name in names if isinstance(names, (list, tuple)) else [names]:
        try:
            obj.set_editor_property(name, value)
            return
        except Exception as ex:
            last = ex
    raise last


def split(result):
    """A UFUNCTION with an out FString comes back as (return value, out) or just the return value."""
    if isinstance(result, tuple):
        return result[0], (result[1] if len(result) > 1 else '')
    return result, ''


try:
    if os.path.exists(RESULT):
        os.replace(RESULT, RESULT + '.previous')
    results = {'steps': []}

    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    folders = ['/Game/Motion/Player/PC0010_Sephiroth', '/Game/Motion/Player/PC0010_Sephiroth_Transform', '/Game/Motion/Player/PC0000_Cloud',
               '/Game/RebirthSkelCompat', '/Game/Animation/CompressionSettings', '/Game/Character/Player/PC0010_00_Sephiroth_Standard',
               '/Game/DataAsset/Game/CharaSpec']
    registry.scan_paths_synchronous(folders, True)
    log('scanned', folders)

    # 1. The KH2 animations onto his skeleton (made anew every run).
    if not hasattr(unreal.EndSkeletonCompatDataObject, 'import_key_animations'):
        raise RuntimeError('this editor has no Import Key Animations: build the Create a Character System plugin 1.10 first')
    ok, report = split(unreal.EndSkeletonCompatDataObject.import_key_animations(KEYS, KH2['skeleton'], KH2['import_folder']))
    open(os.path.join(OUT, 'kh2_import.txt'), 'w', encoding='utf-8').write(report)
    log('import', ('OK ' if ok else 'PROBLEMS ') + report.strip().split('\n')[-1])
    if FLIGHT['moves']:
        ok, report = split(unreal.EndSkeletonCompatDataObject.import_key_animations(FLIGHT_KEYS, FLIGHT['skeleton'], FLIGHT['import_folder']))
        open(os.path.join(OUT, 'flight_import.txt'), 'w', encoding='utf-8').write(report)
        log('flight_import', ('OK ' if ok else 'PROBLEMS ') + report.strip().split('\n')[-1])

    # 2. The data object's row: the forms' moves as before, plus his KH2 moves in Battle00.
    path = PLAN['data_object']
    data = unreal.EditorAssetLibrary.load_asset(path)
    if data is None:
        raise RuntimeError('the data object %s does not load (run run_build_sephiroth_forms.cmd once first)' % path)
    row = unreal.EndAnimSetRow()
    setp(row, ['enabled', 'b_enabled'], True)
    setp(row, 'characters', PLAN['characters'])
    sources = []
    for item in PLAN['battle'] + KH2.get('sources', []):
        source = unreal.EndAnimSetSource()
        setp(source, 'path', item['path'])
        setp(source, ['as_', 'as', 'As'], item['as_'])
        sources.append(source)
    setp(row, 'battle', sources)
    setp(row, 'character_skeleton', unreal.load_asset(PLAN['character_skeleton']))
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
    mine = KH2['moves'] + KH2.get('extra', []) + FLIGHT['moves']
    kh2_names = {(m['set'], m['name']) for m in mine}
    for item in [m for m in PLAN['moves'] if (m['set'], m['name']) not in kh2_names] + mine:
        move = unreal.EndAnimSetMove()
        setp(move, 'name', item['name'])
        setp(move, 'set', item['set'])
        setp(move, 'animation', item['animation'])
        if item.get('then'):
            setp(move, 'then_play', item['then'])
        setp(move, ['build', 'b_build'], bool(item['build']))
        if item['build']:
            setp(move, 'notifies_from', item.get('notifies_from', ''))
            setp(move, 'retarget', unreal.EndMoveRetarget.PROPORTIONS)
            setp(move, ['keep_source_effects', 'b_keep_source_effects'], True)
            hits = []
            for t in item.get('hits', []):
                hit = unreal.EndMoveHit()
                setp(hit, 'time', float(t))
                hits.append(hit)
            setp(move, 'hits', hits)
        moves.append(move)
    setp(row, 'moves', moves)
    setp(data, 'animation_sets', [row])
    setp(data, 'build_chunk', PLAN['build_chunk'])
    game_dir = unreal.DirectoryPath()
    setp(game_dir, 'path', '')
    setp(data, 'game_directory', game_dir)
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)
    log('row', '%d moves, %d of them his KH2 form\'s (Battle04), %d his flying form\'s flight (Battle03)' % (len(moves), len(KH2['moves']), len(FLIGHT['moves'])))

    # 3. Build only the KH2 moves and the flight (the forms' other built moves are already in the project).
    lines, built, failed = [], 0, []
    for item in KH2['moves'] + FLIGHT['moves']:
        ok, report = split(data.build_one_move(0, item['name'], item['set']))
        lines.append(report.strip())
        if ok:
            built += 1
        else:
            failed.append(item['name'])
    open(os.path.join(OUT, 'kh2_build.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    log('failed', failed)   # these stay as they are in game (the compat file is updated without them)
    log('build', '%d of %d built%s' % (built, len(KH2['moves']) + len(FLIGHT['moves']), (', not built: ' + ', '.join(failed)) if failed else ''))
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)

    # 4. The compat file (a reference: the installed one is updated from it) and the checks.
    for function, label in (('ExportJson', 'export_json'), ('Validate', 'validate')):
        try:
            data.call_method(function)
            report = data.get_editor_property('last_result')
        except Exception as ex:
            report = 'call_method %s failed (%s)' % (function, ex)
        open(os.path.join(OUT, label + '.txt'), 'w', encoding='utf-8').write(report)
        log(label, report.split('\n', 1)[0])
    log('done', built > 0)   # packaging goes on when anything was built
except Exception:
    log('error', traceback.format_exc())
