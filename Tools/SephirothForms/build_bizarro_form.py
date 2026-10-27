# Your playable Sephiroth's Bizarro form (animation pack Battle05): puts his forms (the forms menu, Create a Character
# System 3.6) and Bizarro's moves (bizarro\bizarro_moves.json, made by make_bizarro_moves.py) in the SephirothForms data
# object, on top of his other forms' moves, and builds Bizarro's moves (each from one of Bizarro Sephiroth's animations,
# the part around its blow, with his own move's gameplay notifies lined up on Bizarro's blows, on Bizarro's skeleton).
# His other forms' moves are already in the project and are not built again. Run by run_bizarro_form.cmd (editor closed).
# Results: Saved\RebirthSkelCompat\SephirothForms\bizarro_result.json, bizarro_build.txt, import_forms.txt, export_json.txt,
# validate.txt
# Needs Create a Character System editor 1.11 (forms, clips and speed of built moves); 1.11.1 keeps ACL's safety fallback off
# (Bizarro's 54 m skeleton trips it on short clips, and what it leaves the game cannot read). Editor 1.12: his locomotion
# (walks, runs, their starts, stops and turns) is his idle leaning into the root motion of Sephiroth's flying locomotion
# ("retarget": "lean" over a "base"; the walk and run loops as long as his idle, "base_loop").
# bizarro\only.json (a list of move names), when there: only those are built again (the others are in the project already).
import json, os, struct, traceback
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = json.load(open(os.path.join(HERE, 'sephiroth_forms_plan.json')))
KH2 = json.load(open(os.path.join(HERE, 'kh2', 'kh2_moves.json')))
FLIGHT_JSON = os.path.join(HERE, 'flight', 'flight_moves.json')
FLIGHT = json.load(open(FLIGHT_JSON)) if os.path.exists(FLIGHT_JSON) else {'moves': []}
BIZARRO = json.load(open(os.path.join(HERE, 'bizarro', 'bizarro_moves.json')))
FORMS_FILE = os.path.join(HERE, 'bizarro', 'forms_import.json')
ONLY_FILE = os.path.join(HERE, 'bizarro', 'only.json')
ONLY = set(json.load(open(ONLY_FILE))) if os.path.exists(ONLY_FILE) else None
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'SephirothForms')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'bizarro_result.json')
results = {'steps': []}


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('BIZARRO %s: %s' % (key, str(value)[:2000]))
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


def getp(obj, names):
    last = None
    for name in names if isinstance(names, (list, tuple)) else [names]:
        try:
            return obj.get_editor_property(name)
        except Exception as ex:
            last = ex
    raise last


def split(result):
    """A UFUNCTION with an out FString comes back as (return value, out) or just the return value."""
    if isinstance(result, tuple):
        return result[0], (result[1] if len(result) > 1 else '')
    return result, ''


# This engine's memory-mapped Anim Sequence layout (see build_kh2_moves.py): a saved animation whose recorded count and
# compressed bytes disagree stops the editor and the cooker when they load it, so every one is checked before packaging.
MARKER = bytes([0x30, 0xAF, 0x2F, 0x90, 0x54, 0x94, 0xF4, 0x06, 0x59, 0x00, 0x49, 0x00, 0x49, 0x00, 0x53, 0x00])


def saved_animation_problem(path):
    data = open(path, 'rb').read()
    at = data.find(MARKER, 44)
    if at < 0:
        return None
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


# The ACL clip a saved move holds (this engine's memory-mapped layout: the compressed bytes follow MARKER). The game reads every
# animation as ACL (AnimBoneCompressionCodec_ACL_0, hard-coded in its loader): a move without an ACL clip does not play right.
ACL_TAG = struct.pack('<I', 0xAC10AC10)
ROTATION_FORMATS = {0: 'Quat_128', 1: 'QuatDropW_96', 2: 'QuatDropW_48', 3: 'QuatDropW_32', 4: 'QuatDropW_Variable'}


def saved_compression(path):
    data = open(path, 'rb').read()
    at = data.find(MARKER, 44)
    if at < 0:
        return 'no compressed data'
    tag = data.find(ACL_TAG, at + 16, at + 64)
    if tag < 0:
        return 'not ACL'
    return 'ACL ' + ROTATION_FORMATS.get(data[tag + 12], str(data[tag + 12]))


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


def make_move(item):
    move = unreal.EndAnimSetMove()
    setp(move, 'name', item['name'])
    setp(move, 'set', item['set'])
    setp(move, 'animation', item['animation'])
    if item.get('then'):
        setp(move, 'then_play', item['then'])
    setp(move, ['build', 'b_build'], bool(item['build']))
    if item['build']:
        setp(move, 'notifies_from', item.get('notifies_from', ''))
        retarget = item.get('retarget', '')
        setp(move, 'retarget', unreal.EndMoveRetarget.LEAN if retarget == 'lean' else unreal.EndMoveRetarget.MOTION if retarget == 'motion'
             else unreal.EndMoveRetarget.AS_IS if retarget == 'as_is' else unreal.EndMoveRetarget.PROPORTIONS)
        if item.get('base'):   # (editor 1.12) his own animation under the move (his idle), a loop as long as it for loops
            setp(move, 'base', item['base'])
            setp(move, ['base_loop', 'b_base_loop'], bool(item.get('base_loop')))
        if item.get('motion_from'):
            setp(move, 'motion_from', item['motion_from'])
        if item.get('lean_bone'):
            setp(move, 'lean_bone', item['lean_bone'])
        if 'lean' in item:
            setp(move, 'lean', float(item['lean']))
        setp(move, ['keep_source_effects', 'b_keep_source_effects'], True)
        hits = []
        for h in item.get('hits', []):
            hit = unreal.EndMoveHit()
            setp(hit, 'time', float(h['time'] if isinstance(h, dict) else h))
            if isinstance(h, dict) and h.get('damage'):
                setp(hit, ['damage_source_id', 'damage_source_i_d'], h['damage'])
            hits.append(hit)
        setp(move, 'hits', hits)
        if item.get('clip'):
            setp(move, 'clip_start', float(item['clip'][0]))
            setp(move, 'clip_end', float(item['clip'][1]))
        if item.get('speed'):
            setp(move, 'speed', float(item['speed']))
    return move


try:
    if os.path.exists(RESULT):
        os.replace(RESULT, RESULT + '.previous')
    results = {'steps': []}
    try:
        unreal.EndAnimSetMove().get_editor_property('clip_start')
    except Exception:
        raise RuntimeError('this editor has no clips on built moves: build the Create a Character System plugin 1.11 first')

    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    folders = ['/Game/Motion/Player/PC0010_Sephiroth', '/Game/Motion/Player/PC0010_Sephiroth_Transform', '/Game/Motion/Player/PC0000_Cloud',
               '/Game/Motion/Enemy/EB2210_BizarroSephiroth', '/Game/Character/Enemy/EB2210_00_BizarroSephiroth_Standard',
               '/Game/RebirthSkelCompat', '/Game/Animation/CompressionSettings', '/Game/Character/Player/PC0010_00_Sephiroth_Standard',
               '/Game/DataAsset/Game/CharaSpec']
    registry.scan_paths_synchronous(folders, True)
    log('scanned', folders)

    # 1. The data object's row: his forms' moves as before (the plan, KH2, the flight) plus Bizarro's (Battle05).
    path = PLAN['data_object']
    data = unreal.EditorAssetLibrary.load_asset(path)
    if data is None:
        raise RuntimeError('the data object %s does not load (run run_build_sephiroth_forms.cmd once first)' % path)
    row = unreal.EndAnimSetRow()
    setp(row, ['enabled', 'b_enabled'], True)
    setp(row, 'characters', PLAN['characters'])
    sources = []
    for item in PLAN['battle'] + KH2.get('sources', []) + BIZARRO['sources']:
        source = unreal.EndAnimSetSource()
        setp(source, 'path', item['path'])
        setp(source, ['as_', 'as', 'As'], item['as_'])
        sources.append(source)
    setp(row, 'battle', sources)
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
        moves.append(make_move(item))
    for item in BIZARRO['moves']:
        moves.append(make_move(item))
    setp(row, 'moves', moves)
    setp(data, 'animation_sets', [row])
    setp(data, 'build_chunk', PLAN['build_chunk'])
    game_dir = unreal.DirectoryPath()
    setp(game_dir, 'path', '')
    setp(data, 'game_directory', game_dir)
    log('row', '%d moves, %d of them the Bizarro form\'s (Battle05)' % (len(moves), len(BIZARRO['moves'])))

    # 2. His forms (the Bizarro form's model tells Build Moves which skeleton its moves are built on): from forms_import.json
    file_path = unreal.FilePath()
    setp(file_path, 'file_path', FORMS_FILE)
    setp(data, 'import_file', file_path)
    try:
        data.call_method('ImportFromGameJson')
        report = data.get_editor_property('last_result')
    except Exception as ex:
        report = 'call_method ImportFromGameJson failed (%s)' % ex
    open(os.path.join(OUT, 'import_forms.txt'), 'w', encoding='utf-8').write(report)
    empty = unreal.FilePath()
    setp(data, 'import_file', empty)
    row = data.get_editor_property('animation_sets')[0]
    forms = getp(getp(row, 'forms'), 'list')
    names = [str(getp(f, 'name')) for f in forms]
    log('forms', names)
    if 'BIZARRO' not in names:
        raise RuntimeError('the forms did not come in from %s (import_forms.txt)' % FORMS_FILE)
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)

    # 3. Build the Bizarro form's moves (the other forms' moves are in the project already).
    lines, built, failed = [], 0, []
    todo = [m for m in BIZARRO['moves'] if m['build'] and (ONLY is None or m['name'] in ONLY)]
    log('todo', '%d move(s)%s' % (len(todo), ' (only.json)' if ONLY is not None else ''))
    content = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
    compression = {}
    for item in todo:
        result = data.build_one_move(0, item['name'], item['set'])
        ok, report = split(result)
        if not report:
            report = str(data.get_editor_property('last_result'))   # (editor 1.11.1: the report as Last Result)
        package = os.path.join(content, PLAN['build_folder'][len('/Game/'):].replace('/', os.sep), item['set'], item['name'] + '.uasset')
        saved = saved_compression(package) if os.path.exists(package) else 'not saved'
        compression[item['name']] = saved
        if ok and not saved.startswith('ACL '):
            ok = False
            report += '\n%s: ERROR: its saved file holds %s (the game reads every animation as ACL)' % (item['name'], saved)
        lines.append(report.strip() + ' [' + saved + ']')
        if ok:
            built += 1
        else:
            failed.append(item['name'])
    open(os.path.join(OUT, 'bizarro_build.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    counts = {}
    for value in compression.values():
        counts[value] = counts.get(value, 0) + 1
    log('compression', counts)
    log('failed', failed)   # these are left out of the compat file
    log('build', '%d of %d built%s' % (built, len(todo), (', not built: ' + ', '.join(failed)) if failed else ''))
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)

    checked, broken = broken_animations([PLAN['build_folder'] + '/Battle05'])
    log('checked', '%d package(s), %s' % (checked, ('%d BROKEN: ' % len(broken)) + '; '.join(broken[:8]) if broken else 'all load back'))
    if broken:
        raise RuntimeError('%d saved animation(s) would stop the cooker: %s' % (len(broken), '; '.join(broken)))

    # 4. The compat file (a reference) and the checks.
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
