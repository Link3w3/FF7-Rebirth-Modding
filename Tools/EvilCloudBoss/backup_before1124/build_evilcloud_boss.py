# Evil Cloud's boss fights, step 2: his moves (the final battle's and the VR battle's Sephiroth, PC0010_10_Sephiroth_Transform
# and PC0010_20_Sephiroth_VRHard: every animation of the boss's sets made of Cloud's, with the boss's own gameplay notifies:
# damage, AI messages, cancel windows, super armor, warps, phase changes), with the Create a Character System editor plugin
# 1.12.3's Build Moves. Run by run_evilcloud_boss.cmd (End editor closed); the plan is evilcloud_boss_moves.json next to
# this file (made by make_evilcloud_moves.py from the survey).
# Results: Saved\RebirthSkelCompat\EvilCloudBoss\ (build_result.json, sources.json, build_moves.txt, built.json,
# export_json.txt, validate.txt). The moves are saved in /Game/RebirthSkelCompat/Built/EvilCloudBoss (pakchunk52).
import json, os, struct, traceback
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = json.load(open(os.path.join(HERE, 'evilcloud_boss_moves.json')))
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'EvilCloudBoss')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'build_result.json')
results = {'steps': []}


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('EVILCLOUD BUILD %s: %s' % (key, str(value)[:2000]))
    json.dump(results, open(RESULT, 'w'), indent=1)   # after every step, so a stop shows where it was


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


# This engine's memory-mapped Anim Sequence layout: a saved animation whose recorded count and compressed bytes disagree
# stops the editor and the cooker when they load it, so every one is checked before packaging (as build_safer_update.py).
MARKER = bytes([0x30, 0xAF, 0x2F, 0x90, 0x54, 0x94, 0xF4, 0x06, 0x59, 0x00, 0x49, 0x00, 0x49, 0x00, 0x53, 0x00])
ACL_TAG = struct.pack('<I', 0xAC10AC10)
ROTATION_FORMATS = {0: 'Quat_128', 1: 'QuatDropW_96', 2: 'QuatDropW_48', 3: 'QuatDropW_32', 4: 'QuatDropW_Variable'}


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


def saved_compression(path):
    data = open(path, 'rb').read()
    at = data.find(MARKER, 44)
    if at < 0:
        return 'no compressed data'
    tag = data.find(ACL_TAG, at + 16, at + 64)
    if tag < 0:
        return 'not ACL'
    return 'ACL ' + ROTATION_FORMATS.get(data[tag + 12], str(data[tag + 12]))


def make_move(item):
    move = unreal.EndAnimSetMove()
    setp(move, 'name', item['name'])
    setp(move, 'set', item['set'])
    setp(move, 'animation', item['animation'])
    setp(move, ['build', 'b_build'], bool(item['build']))
    if item['build']:
        setp(move, 'notifies_from', item.get('notifies_from', ''))
        setp(move, 'retarget', unreal.EndMoveRetarget.PROPORTIONS)
        setp(move, ['keep_source_effects', 'b_keep_source_effects'], True)   # Cloud's own sword sounds, trails and effects
        hits = []
        for t in item.get('hits', []):
            hit = unreal.EndMoveHit()
            setp(hit, 'time', float(t))
            hits.append(hit)
        setp(move, 'hits', hits)
        if item.get('clip'):
            setp(move, 'clip_start', float(item['clip'][0]))
            setp(move, 'clip_end', float(item['clip'][1]))
        if item.get('speed'):
            setp(move, 'speed', float(item['speed']))
    return move


def describe(paths):
    try:
        out = {}
        for item in json.loads(unreal.EndSkeletonCompatDataObject.describe_animations(paths)):
            out[item.get('path', '')] = item
        return out
    except Exception as ex:
        unreal.log_warning('EVILCLOUD BUILD: DescribeAnimations failed (%s)' % ex)
        return {}


try:
    if os.path.exists(RESULT):
        os.replace(RESULT, RESULT + '.previous')
    results = {'steps': []}
    try:
        probe = unreal.EndAnimSetMove()
        probe.get_editor_property('clip_start')
        probe.get_editor_property('bone_map')
    except Exception:
        raise RuntimeError('this editor has no Clip Start or Bone Map on moves: the Create a Character System plugin 1.12.3 is needed')

    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    folders = ['/Game/Motion/Player/PC0010_Sephiroth_Transform', '/Game/Motion/Player/PC0000_Cloud', '/Game/RebirthSkelCompat',
               '/Game/Animation/CompressionSettings', '/Game/Character/Player/PC0000_00_Cloud_Standard',
               '/Game/Character/Player/PC0010_00_Sephiroth_Standard', '/Game/DataAsset/Game/CharaSpec']
    registry.scan_paths_synchronous(folders, True)
    log('scanned', folders)

    # 1. Every animation the moves are made of and take their notifies from loads in this editor.
    seen = describe(PLAN['describe'])
    json.dump(seen, open(os.path.join(OUT, 'sources.json'), 'w'), indent=1)
    missing = sorted(p for p in PLAN['describe'] if 'error' in seen.get(p, {'error': 'not described'}))
    log('sources', '%d of %d described%s' % (len(PLAN['describe']) - len(missing), len(PLAN['describe']),
                                             (', NOT loading: ' + ', '.join(missing)) if missing else ''))

    # 2. The data object and its one row: the boss's two characters, the boss's own sets, the moves.
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
    skeleton = unreal.load_asset(PLAN['character_skeleton'])
    if skeleton is None:
        raise RuntimeError('the character skeleton does not load: ' + PLAN['character_skeleton'])
    setp(row, 'character_skeleton', skeleton)
    setp(row, 'build_folder', PLAN['build_folder'])
    setp(row, 'requires_paks', PLAN['requires_paks'])
    moves = [make_move(item) for item in PLAN['moves']]
    setp(row, 'moves', moves)
    setp(data, 'animation_sets', [row])
    setp(data, 'build_chunk', PLAN['build_chunk'])
    game_dir = unreal.DirectoryPath()
    setp(game_dir, 'path', '')
    setp(data, 'game_directory', game_dir)   # the compat file goes to Saved; the mod's own is made from the results
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)
    todo = [m for m in PLAN['moves'] if m['build']]
    log('row', '%d moves (%d to build, %d Cloud\'s as they are)' % (len(moves), len(todo), len(moves) - len(todo)))

    # 3. Build every move with Build on, then check every saved file.
    try:
        data.call_method('BuildMoves')
        report = data.get_editor_property('last_result')
    except Exception as ex:
        value = data.build_move_animations()
        report = 'call_method BuildMoves failed (%s)\nbuild_move_animations: %s' % (ex, 'FAILED (see the log)' if value is None else value)
    open(os.path.join(OUT, 'build_moves.txt'), 'w', encoding='utf-8').write(report)
    log('build_report', report.strip().split('\n')[-1][:400])
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)
    content = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
    base = os.path.join(content, PLAN['build_folder'][len('/Game/'):].replace('/', os.sep))
    compression, broken, failed, failed_keys = {}, [], [], set()
    for item in todo:
        key = item['set'] + '/' + item['name']
        package = os.path.join(base, item['set'], item['name'] + '.uasset')
        if not os.path.exists(package):
            failed.append(key + ' (not built)')
            failed_keys.add(key)
            continue
        saved = saved_compression(package)
        compression[saved] = compression.get(saved, 0) + 1
        if not saved.startswith('ACL '):
            failed.append(key + ' (' + saved + ')')
            failed_keys.add(key)
        problem = saved_animation_problem(package)
        if problem:
            broken.append(item['set'] + '/' + item['name'] + ' (' + problem + ')')
    log('compression', compression)
    log('failed', failed)   # these are left out of the compat file (the boss's own animation stays for them)
    log('build', '%d of %d built' % (len(todo) - len(failed), len(todo)))
    log('checked', '%d package(s), %s' % (len(todo) - len(failed), ('%d BROKEN: ' % len(broken)) + '; '.join(broken[:8]) if broken else 'all load back'))
    if broken:
        raise RuntimeError('%d saved animation(s) would stop the cooker: %s' % (len(broken), '; '.join(broken)))

    # 4. What the built moves hold (lengths, hits), the compat file and the checks.
    made = describe(['%s/%s/%s.%s' % (PLAN['build_folder'], m['set'], m['name'], m['name']) for m in todo
                     if (m['set'] + '/' + m['name']) not in failed_keys])
    json.dump(made, open(os.path.join(OUT, 'built.json'), 'w'), indent=1)
    log('built_described', len(made))
    for function, label in (('ExportJson', 'export_json'), ('Validate', 'validate')):
        try:
            data.call_method(function)
            report = data.get_editor_property('last_result')
        except Exception as ex:
            report = 'call_method %s failed (%s)' % (function, ex)
        open(os.path.join(OUT, label + '.txt'), 'w', encoding='utf-8').write(report)
        log(label, report.split('\n', 1)[0])
    log('done', len(todo) - len(failed) > 0)   # packaging goes on when anything was built
except Exception:
    log('error', traceback.format_exc())
