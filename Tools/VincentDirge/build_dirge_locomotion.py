# Vincent's Dirge of Cerberus walk and run in battle, moving him: the Create a Character System editor plugin 1.12.4's
# Build Moves. Run by run_dirge_locomotion.cmd (End editor closed); the plan is dirge_locomotion_plan.json next to this
# file (made by make_plan.py).
#
# The game moves a character in battle by the root motion of its walk and run animations, and the Dirge of Cerberus
# motions stand in place: given to his walk and run as they are (3.7.2), they left him walking on the spot. So each of his
# battle walk, run and strafe animation names (Battle00: B_Run01_*, B_Walk01_*, B_WalkF/B/L/R/FL/FR/BL/BR01_*) becomes a
# move built in Vincent_Moves' row for Cloud's slot:
#   Base       his Dirge of Cerberus motion for it (p000_m001_h_*_remap: run, walk, aimed walk, back / left / right runs,
#              stand, aimed stand): his whole body moves as in Dirge of Cerberus,
#   Animation  Cloud's animation of that name (the project has Cloud's battle animations; Vincent's own in the game move
#              the same): Retarget "Keep the character's own pose" with the Bone Map "Trans=Trans", so only the root
#              follows it, and its root motion moves him (editor 1.12.2),
#   Base Loop  a loop as long as the Dirge of Cerberus motion with Cloud's animation once in it (a start shorter than
#              that played slower to fill it), so the body and the root both loop without a jump; a stop plays Cloud's
#              stop over his Dirge of Cerberus stand,
#   notifies   Cloud's (Notifies From the same animation): footsteps, sounds, state changes; its play settings (root
#              motion on).
# The prologue's Cloud rows (his SOLDIER uniform) go in the row's characters too, as in the installed Vincent_Moves.json.
# One move at a time (Build One Move), each saved as it is built, with progress.json saying which one: a move that stops
# the editor is left out when run_dirge_locomotion.ps1 runs the editor again, and the moves built already are kept.
#
# Results: Saved\RebirthSkelCompat\DirgeLocomotion\ (build_result.json, progress.json, sources.json, build_moves.txt,
# built.json, root_motion.json, export_json.txt, validate.txt) and the compat file
# Saved\RebirthSkelCompat\Vincent_Moves.skelcompat.json. The moves are saved in /Game/RebirthSkelCompat/Built/Vincent
# (pakchunk46).
import hashlib, json, os, shutil, struct, time, traceback
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN_FILE = os.path.join(HERE, 'dirge_locomotion_plan.json')
PLAN = json.load(open(PLAN_FILE))
PLAN_MD5 = hashlib.md5(open(PLAN_FILE, 'rb').read()).hexdigest()
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
CONTENT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'DirgeLocomotion')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'build_result.json')
PROGRESS = os.path.join(OUT, 'progress.json')
NEEDED_PLUGIN = '1.12.4'
results = {'steps': []}


def write_json(path, value):
    temp = path + '.tmp'
    with open(temp, 'w') as f:
        json.dump(value, f, indent=1)
    os.replace(temp, path)


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('DIRGE LOCOMOTION %s: %s' % (key, str(value)[:2000]))
    write_json(RESULT, results)   # after every step, so a stop shows where it was


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


def package_file(object_path):
    """The .uasset of a /Game/... object path."""
    package = object_path.split('.', 1)[0]
    return os.path.join(CONTENT, package[len('/Game/'):].replace('/', os.sep) + '.uasset')


def object_path(path):
    """/Game/A/B -> /Game/A/B.B (an object path as the editor loads it)."""
    return path if '.' in path.rsplit('/', 1)[-1] else path + '.' + path.rsplit('/', 1)[-1]


# This engine's memory-mapped Anim Sequence layout: a saved animation whose recorded count and compressed bytes disagree
# stops the editor and the cooker when they load it, so every one is checked before packaging (build_evilcloud_boss.py).
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


def describe(paths):
    try:
        out = {}
        for item in json.loads(unreal.EndSkeletonCompatDataObject.describe_animations(paths)):
            out[item.get('path', '')] = item
        return out
    except Exception as ex:
        unreal.log_warning('DIRGE LOCOMOTION: DescribeAnimations failed (%s)' % ex)
        return {}


def root_motion(anim):
    """How the root (Trans) of a built move travels over it, its length and its root motion setting."""
    out = {}
    try:
        length = float(getp(anim, 'sequence_length'))
    except Exception as ex:
        return {'error': 'no length (%s)' % ex}
    out['length'] = round(length, 4)
    for key, names in (('root_motion', ['enable_root_motion', 'b_enable_root_motion']), ('force_root_lock', ['force_root_lock', 'b_force_root_lock'])):
        try:
            out[key] = bool(getp(anim, names))
        except Exception:
            pass
    samples = []
    for k in range(9):
        t = length * k / 8.0
        try:
            pose = unreal.AnimationLibrary.get_bone_pose_for_time(anim, 'Trans', t, False)
        except Exception as ex:
            out['error'] = 'the root not sampled (%s)' % ex
            return out
        loc = pose.translation
        samples.append([round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)])
    first, last = samples[0], samples[-1]
    travel = [round(last[i] - first[i], 1) for i in range(3)]
    out['travel'] = travel
    out['distance'] = round((travel[0] ** 2 + travel[1] ** 2 + travel[2] ** 2) ** 0.5, 1)
    out['samples'] = samples
    return out


def plugin_version():
    project = os.path.dirname(os.path.normpath(SAVED))
    try:
        return json.load(open(os.path.join(project, 'Plugins', 'RebirthSkelCompat', 'RebirthSkelCompat.uplugin'))).get('VersionName', '')
    except Exception:
        return ''


def load_progress(version):
    """The moves built (and saved) by an earlier run of this plan with this plugin, and those that stopped the editor."""
    try:
        progress = json.load(open(PROGRESS))
    except Exception:
        progress = {}
    if progress.get('plan') != PLAN_MD5 or progress.get('plugin') != version:
        progress = {'plan': PLAN_MD5, 'plugin': version, 'done': {}, 'stopped': {}, 'runs': 0}
    progress.setdefault('done', {})
    progress.setdefault('stopped', {})
    progress['runs'] = progress.get('runs', 0) + 1
    if progress.get('current'):
        # the editor stopped while it built this move: it is left out from now on (his Rebirth animation stays for it)
        progress['stopped'][progress['current']] = 'stopped the editor in run %d' % (progress['runs'] - 1)
    progress['current'] = None
    write_json(PROGRESS, progress)
    return progress


def set_move(move, item, bone_map):
    setp(move, 'name', item['name'])
    setp(move, 'set', item['set'])
    setp(move, 'animation', item['animation'])
    setp(move, ['build', 'b_build'], True)
    setp(move, ['shot', 'b_shot'], False)
    setp(move, 'hit_at', 0.0)
    setp(move, 'hits', [])
    setp(move, 'notifies_from', item['notifies_from'])
    setp(move, 'retarget', unreal.EndMoveRetarget.MOTION)
    setp(move, ['keep_source_effects', 'b_keep_source_effects'], True)    # Cloud's footsteps and dust
    setp(move, ['source_sounds_only', 'b_source_sounds_only'], False)
    setp(move, 'clip_start', 0.0)
    setp(move, 'clip_end', 0.0)
    setp(move, 'speed', float(item['speed']))
    setp(move, 'base', item['base'])
    setp(move, ['base_loop', 'b_base_loop'], bool(item['base_loop']))
    setp(move, 'motion_from', '')
    setp(move, 'bone_map', bone_map)
    setp(move, 'source_turn', 0.0)
    setp(move, ['keep_base_root', 'b_keep_base_root'], False)
    try:
        setp(move, 'then_play', [])
    except Exception:
        pass


try:
    if os.path.exists(RESULT):
        os.replace(RESULT, RESULT + '.previous')
    results = {'steps': []}
    try:
        probe = unreal.EndAnimSetMove()
        probe.get_editor_property('base')
        probe.get_editor_property('bone_map')
    except Exception:
        raise RuntimeError('this editor has no Base or Bone Map on moves: the Create a Character System plugin %s is needed' % NEEDED_PLUGIN)
    version = plugin_version()
    if version != NEEDED_PLUGIN:
        raise RuntimeError('the project\'s Create a Character System plugin is %s and this needs %s' % (version or 'not found', NEEDED_PLUGIN))
    progress = load_progress(version)
    log('run', 'run %d with the plugin %s: %d move(s) built before, %d left out (they stopped the editor)%s' % (
        progress['runs'], version, len(progress['done']), len(progress['stopped']),
        (': ' + ', '.join(sorted(progress['stopped']))) if progress['stopped'] else ''))

    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    folders = ['/Game/Motion/Player/PC0011_00_Vincent', '/Game/Motion/Player/PC0000_Cloud', '/Game/RebirthSkelCompat/Built/Vincent',
               '/Game/Character/Player/PC0011_00_Vincent_Standard', '/Game/Character/Player/PC0000_00_Cloud_Standard',
               '/Game/Animation/CompressionSettings']
    registry.scan_paths_synchronous(folders, True)
    log('scanned', folders)

    # 1. Every motion and animation the moves are made of loads here, the motions on Vincent's skeleton.
    seen = describe([object_path(p) for p in PLAN['describe']])
    with open(os.path.join(OUT, 'sources.json'), 'w') as f:
        json.dump(seen, f, indent=1)
    problems = []
    for path in PLAN['describe']:
        anim = unreal.EditorAssetLibrary.load_asset(object_path(path))
        if anim is None:
            problems.append(path + ' does not load')
            continue
        if '/PC0011_00_Vincent/' in path:
            skeleton = getp(anim, 'skeleton')
            skeleton_path = skeleton.get_path_name() if skeleton else ''
            if skeleton_path != PLAN['skeleton']:
                problems.append('%s is on %s, not %s' % (path, skeleton_path or 'no skeleton', PLAN['skeleton']))
                continue
            problem = saved_animation_problem(package_file(object_path(path)))
            if problem:
                problems.append('%s: %s' % (path, problem))
    if problems:
        raise RuntimeError('the motions and animations the moves are made of: ' + '; '.join(problems))
    log('sources', '%d motion(s) and animation(s), all load' % len(PLAN['describe']))

    # 2. Vincent_Moves' row for Cloud's slot: the moves (others kept as they are) and the prologue's characters.
    data = unreal.EditorAssetLibrary.load_asset(PLAN['data_object'])
    if data is None:
        raise RuntimeError('the data object does not load: ' + PLAN['data_object'])
    content_file = package_file(PLAN['data_object'])
    backup = content_file + '.before_locomotion'
    if os.path.exists(content_file) and not os.path.exists(backup):
        shutil.copy2(content_file, backup)
    rows = list(getp(data, 'animation_sets'))
    row_index = -1
    for index, row in enumerate(rows):
        if PLAN['row_character'] in [str(c) for c in getp(row, 'characters')]:
            row_index = index
            break
    if row_index < 0:
        raise RuntimeError('Vincent_Moves has no row for ' + PLAN['row_character'])
    row = rows[row_index]
    characters = [str(c) for c in getp(row, 'characters')]
    added_characters = [c for c in PLAN['add_characters'] if c not in characters]
    setp(row, 'characters', characters + added_characters)
    moves = list(getp(row, 'moves'))
    replaced, added = [], []
    for item in PLAN['moves']:
        move = None
        for m in moves:
            if str(getp(m, 'name')) == item['name'] and str(getp(m, 'set')) == item['set']:
                move = m
                break
        if move is None:
            move = unreal.EndAnimSetMove()
            moves.append(move)
            added.append(item['name'])
        else:
            replaced.append(item['name'])
        set_move(move, item, PLAN['bone_map'])
    # the moves back into the row, the row into the data object (the editor hands out copies of its structs)
    setp(row, 'moves', moves)
    rows[row_index] = row
    setp(data, 'animation_sets', rows)
    game_directory = getp(data, 'game_directory')
    kept_game_directory = str(getp(game_directory, 'path'))
    empty = unreal.DirectoryPath()
    setp(empty, 'path', '')
    setp(data, 'game_directory', empty)       # the compat file goes to Saved; Sandalphon puts it in the game
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)
    log('row', 'row %d: %d moves (%d replaced, %d added), characters %s (%s added)' % (
        row_index, len(moves), len(replaced), len(added), len(characters) + len(added_characters), ', '.join(added_characters) or 'none'))

    # 3. Build every move, one at a time (each is saved as it is built), then check every saved file.
    build_folder = str(getp(row, 'build_folder')) or PLAN['build_folder']
    if build_folder != PLAN['build_folder']:
        raise RuntimeError('the row builds into %s, the plan into %s' % (build_folder, PLAN['build_folder']))
    base = os.path.join(CONTENT, build_folder[len('/Game/'):].replace('/', os.sep))
    started, made_now = time.time(), 0
    todo = PLAN['moves']
    for number, item in enumerate(todo, 1):
        key = item['set'] + '/' + item['name']
        package = os.path.join(base, item['set'], item['name'] + '.uasset')
        if key in progress['stopped']:
            continue
        if key in progress['done'] and os.path.exists(package):
            continue
        progress['current'] = key
        write_json(PROGRESS, progress)
        unreal.log('DIRGE LOCOMOTION move %d/%d: %s over %s from %s' % (number, len(todo), key, item['base'], item['animation']))
        ok, report = split(data.build_one_move(row_index, item['name'], item['set']))
        if not report:
            report = str(getp(data, 'last_result'))
        lines = [line for line in report.strip().split('\n') if line.strip()]
        progress['done'][key] = {'ok': bool(ok), 'report': ' | '.join(lines[:6])[:3000]}
        progress['current'] = None
        write_json(PROGRESS, progress)
        made_now += 1
    log('built_now', '%d move(s) in %.0f s' % (made_now, time.time() - started))

    reports, compression, broken, failed, failed_keys = [], {}, [], [], set()
    for item in todo:
        key = item['set'] + '/' + item['name']
        package = os.path.join(base, item['set'], item['name'] + '.uasset')
        if key in progress['stopped']:
            failed.append(key + ' (' + progress['stopped'][key] + ')')
            failed_keys.add(key)
            reports.append('%s: LEFT OUT: %s' % (key, progress['stopped'][key]))
            continue
        done = progress['done'].get(key, {'ok': False, 'report': 'not built'})
        reports.append(done['report'])
        if not os.path.exists(package):
            failed.append(key + ' (not built)')
            failed_keys.add(key)
            continue
        saved = saved_compression(package)
        compression[saved] = compression.get(saved, 0) + 1
        if not saved.startswith('ACL '):
            failed.append(key + ' (' + saved + ')')
            failed_keys.add(key)
        elif not done['ok']:
            failed.append(key + ' (the build reported an error: build_moves.txt)')
            failed_keys.add(key)
        problem = saved_animation_problem(package)
        if problem:
            broken.append(key + ' (' + problem + ')')
    with open(os.path.join(OUT, 'build_moves.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(reports) + '\n')
    log('compression', compression)
    log('failed', failed)   # these keep his Rebirth animation (the compat file points at the animation they were made from)
    log('build', '%d of %d built' % (len(todo) - len(failed), len(todo)))
    log('checked', '%d package(s), %s' % (len(todo) - len(failed), ('%d BROKEN: ' % len(broken)) + '; '.join(broken[:8]) if broken else 'all load back'))
    if broken:
        raise RuntimeError('%d saved animation(s) would stop the cooker: %s' % (len(broken), '; '.join(broken)))

    # 4. What the built moves are: lengths, notifies (DescribeAnimations), and how far each one moves him.
    built_paths = ['%s/%s/%s.%s' % (build_folder, m['set'], m['name'], m['name']) for m in todo if (m['set'] + '/' + m['name']) not in failed_keys]
    with open(os.path.join(OUT, 'built.json'), 'w') as f:
        json.dump(describe(built_paths), f, indent=1)
    motion, still, off = {}, [], []
    for item in todo:
        key = item['set'] + '/' + item['name']
        if key in failed_keys:
            continue
        anim = unreal.EditorAssetLibrary.load_asset('%s/%s/%s.%s' % (build_folder, item['set'], item['name'], item['name']))
        info = root_motion(anim) if anim is not None else {'error': 'does not load'}
        info['expect'] = item['expect']
        motion[key] = info
        want = item['expect']['root_travel']
        got = info.get('distance')
        if got is None:
            off.append('%s (%s)' % (item['name'], info.get('error', 'not sampled')))
        elif want > 5.0 and got < 0.5 * want:
            still.append('%s (%.0f cm, Cloud\'s %.0f)' % (item['name'], got, want))
        elif want > 5.0 and abs(got - want) > 0.1 * want + 5.0:
            off.append('%s (%.0f cm, Cloud\'s %.0f)' % (item['name'], got, want))
        if want > 5.0 and info.get('root_motion') is False:
            still.append('%s (root motion off)' % item['name'])
    with open(os.path.join(OUT, 'root_motion.json'), 'w') as f:
        json.dump(motion, f, indent=1)
    log('root_motion', '%d move(s) sampled; %s%s' % (len(motion), ('NOT MOVING: ' + ', '.join(still)) if still else 'every moving one moves',
                                                     ('; differs: ' + ', '.join(off)) if off else ''))

    # 5. The compat file (to Saved), the checks, then the data object's game folder as it was.
    for function, label in (('ExportJson', 'export_json'), ('Validate', 'validate')):
        try:
            data.call_method(function)
            text = str(getp(data, 'last_result'))
        except Exception as ex:
            text = 'call_method %s failed (%s)' % (function, ex)
        with open(os.path.join(OUT, label + '.txt'), 'w', encoding='utf-8') as f:
            f.write(text)
        log(label, text.split('\n', 1)[0])
    kept = unreal.DirectoryPath()
    setp(kept, 'path', kept_game_directory)
    setp(data, 'game_directory', kept)
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)
    exported = os.path.join(SAVED, 'RebirthSkelCompat', 'Vincent_Moves.skelcompat.json')
    log('compat_file', exported if os.path.exists(exported) else 'NOT written: ' + exported)
    log('done', len(todo) - len(failed) > 0)   # packaging goes on when anything was built
except Exception:
    log('error', traceback.format_exc())
