# Your playable Sephiroth's KH2 form (animation pack Battle04): imports the KH2 animations (key animations made from the
# retargeted FBXs in H:\Exported\Projects\SephiAnims\Kh2Rebirth\Remap) onto his skeleton with Create a Character System's
# Import Key Animations, puts them in the SephirothForms data object as Battle04 moves (with the KH2 swing times as hits)
# on top of his own Battle00 set, and builds them (each with his own animation's gameplay notifies, lined up on the hits).
# His other forms keep their moves; every form casts Meteor with the KH2 sword raise. Run by run_kh2_moves.cmd (editor closed).
# Results: Saved\RebirthSkelCompat\SephirothForms\kh2_result.json, kh2_import.txt, kh2_build.txt, export_json.txt, validate.txt
# Needs Create a Character System editor 1.10.1: this engine can save an Anim Sequence broken when an earlier one is
# deleted as an asset (the editor and the cooker then stop when they load it), so 1.10.1 replaces earlier imports and
# builds without loading or deleting them as assets, and every saved animation is checked here before packaging.
import json, os, struct, traceback
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


# This engine's memory-mapped Anim Sequence layout: a header {frozen size, 65536, 16, padding}, the padding, two pointers
# {offset, count, max}, 16 marker bytes, then the compressed bytes and the curve bytes, each padded to 16.
MARKER = bytes([0x30, 0xAF, 0x2F, 0x90, 0x54, 0x94, 0xF4, 0x06, 0x59, 0x00, 0x49, 0x00, 0x49, 0x00, 0x53, 0x00])


def saved_animation_problem(path):
    """What is wrong with a saved Anim Sequence package, if anything: one whose recorded count and compressed bytes disagree
    stops the editor ("Unexpected array element size") and the cooker ("SerializeNum >= 0") when they load it."""
    data = open(path, 'rb').read()
    at = data.find(MARKER, 44)
    if at < 0:
        return None   # not an animation in that layout
    pointers = at - 32
    count = struct.unpack_from('<i', data, pointers + 8)[0]
    packed, curves = struct.unpack_from('<Qi', data, pointers + 16)
    curves = curves if packed >> 1 else 0

    def padded(n):
        return n + (16 - n % 16) % 16 if n > 0 else 0
    for pad in range(16):
        header = pointers - pad - 12
        if header < 0:
            break
        frozen, size, idk, padding = struct.unpack_from('<IIHH', data, header)
        if padding == pad and idk == 16 and size == 65536:
            if count < 0 or curves < 0 or frozen != 48 + padded(count) + padded(curves):
                return 'records %d compressed bytes but holds %d' % (count, frozen - 48 - padded(curves))
            return None
    return None


def broken_animations(folders):
    content = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
    broken, checked = [], 0
    for folder in folders:
        if not folder or not folder.startswith('/Game/'):
            continue
        root = os.path.join(content, folder[len('/Game/'):].replace('/', os.sep))
        for dirpath, _, files in os.walk(root):
            for name in sorted(files):
                if name.endswith('.uasset'):
                    path = os.path.join(dirpath, name)
                    checked += 1
                    problem = saved_animation_problem(path)
                    if problem:
                        broken.append('%s (%s)' % (os.path.relpath(path, content), problem))
    return checked, broken


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
    # his field sets (Neutral00, Neutral20, Emotion00, Facial00): his own first, then Cloud's (Neutral20 and Emotion00 are Cloud's)
    field = []
    for item in PLAN.get('field', []):
        source = unreal.EndAnimSetSource()
        setp(source, 'path', item['path'])
        setp(source, ['as_', 'as', 'As'], item.get('as_', ''))
        field.append(source)
    setp(row, 'field', field)
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

    # Every animation of the imports and the builds loads back (the cooker would stop on one this engine saved broken).
    checked, broken = broken_animations([KH2['import_folder'], FLIGHT.get('import_folder'), PLAN['build_folder']])
    log('checked', '%d package(s), %s' % (checked, ('%d BROKEN: ' % len(broken)) + '; '.join(broken[:8]) if broken else 'all load back'))
    if broken:
        raise RuntimeError('%d saved animation(s) would stop the cooker: %s' % (len(broken), '; '.join(broken)))

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
