# Vincent, the Dirge of Cerberus shooter, step 1 (the editor's part). Run by run_vincent_dirge_cook.cmd with the End editor
# closed (an editor commandlet); the plan is vincent_dirge_plan.json next to this file.
#
#  1. Vincent's Dirge of Cerberus motions (/Game/Motion/Player/PC0011_00_Vincent/Battle00/p000_*) go in pakchunk53 and
#     Chaos's (/Game/Motion/Player/PC0011_10_Chaos/Battle00/p007_*) in pakchunk54, as they are (Primary Asset Labels with
#     the motions listed: nothing else in those folders, not the skeletons they use): the mod plays them for the shooter.
#     Chaos's model (/Game/Character/Player/PC0011_10_Chaos, but not the editor's data objects there) goes in pakchunk54 too.
#  2. Square becomes his Dirge of Cerberus melee combo: Vincent_Moves' B_NAttack01_0 .. B_NAttack07_0, the dash attack's
#     strike B_NAttack01_1_2 and the field attack N_Atk01, built (Build One Move) from the melee motions p000_m000_c_atk_*
#     with Cloud's damage and combo windows, in place of the shots they were. The other moves stay as they are.
#  3. Says what every motion is like (length, frames, root motion, how far its root and its hips travel) for the mod.
#
# Results: Saved\RebirthSkelCompat\VincentDirge\ (cook_result.json, progress.json, motions.json, build_moves.txt,
# export_json.txt, validate.txt) and the new compat file Saved\RebirthSkelCompat\Vincent_Moves.skelcompat.json.
import hashlib, json, os, shutil, struct, time, traceback
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN_FILE = os.path.join(HERE, 'vincent_dirge_plan.json')
PLAN = json.load(open(PLAN_FILE))
PLAN_MD5 = hashlib.md5(open(PLAN_FILE, 'rb').read()).hexdigest()
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
CONTENT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'VincentDirge')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'cook_result.json')
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
    unreal.log('VINCENT DIRGE %s: %s' % (key, str(value)[:2000]))
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


# This engine's memory-mapped Anim Sequence layout: a saved animation whose recorded count and compressed bytes disagree
# stops the editor and the cooker when they load it (build_evilcloud_boss.py's check), so every motion is checked first.
MARKER = bytes([0x30, 0xAF, 0x2F, 0x90, 0x54, 0x94, 0xF4, 0x06, 0x59, 0x00, 0x49, 0x00, 0x49, 0x00, 0x53, 0x00])
ACL_TAG = struct.pack('<I', 0xAC10AC10)


def saved_animation_problem(path):
    try:
        data = open(path, 'rb').read()
    except Exception as ex:
        return 'not readable (%s)' % ex
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
    return 'ACL' if tag >= 0 else 'not ACL'


def describe(paths):
    try:
        out = {}
        for item in json.loads(unreal.EndSkeletonCompatDataObject.describe_animations(paths)):
            out[item.get('path', '')] = item
        return out
    except Exception as ex:
        unreal.log_warning('VINCENT DIRGE: DescribeAnimations failed (%s)' % ex)
        return {}


def bone_travel(anim, length):
    """How far the first track's bone (the root) and the hips move over the motion, in its own space (cm)."""
    out = {}
    try:
        tracks = [str(n) for n in unreal.AnimationLibrary.get_animation_track_names(anim)]
    except Exception:
        tracks = []
    if tracks:
        out['first_track'] = tracks[0]
    wanted = []
    for bone in ([tracks[0]] if tracks else []) + ['C_CharaA_a', 'C_Hip_a']:
        if bone not in wanted and (not tracks or bone in tracks):
            wanted.append(bone)
    for bone in wanted:
        samples = []
        for k in range(5):
            t = length * k / 4.0
            try:
                pose = unreal.AnimationLibrary.get_bone_pose_for_time(anim, bone, t, False)
            except Exception as ex:
                out[bone] = 'not sampled (%s)' % ex
                samples = None
                break
            loc = pose.translation
            samples.append([round(loc.x, 2), round(loc.y, 2), round(loc.z, 2)])
        if samples:
            first, last = samples[0], samples[-1]
            out[bone] = {'start': first, 'end': last,
                         'travel': [round(last[i] - first[i], 2) for i in range(3)], 'samples': samples}
    return out


def plugin_version():
    project = os.path.dirname(os.path.normpath(SAVED))
    try:
        return json.load(open(os.path.join(project, 'Plugins', 'RebirthSkelCompat', 'RebirthSkelCompat.uplugin'))).get('VersionName', '')
    except Exception:
        return ''


def make_label(folder, name, chunk, assets):
    """A Primary Asset Label in folder that puts exactly `assets` (loaded objects) in chunk, at pack time."""
    path = folder + '/' + name
    label = None
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        label = unreal.EditorAssetLibrary.load_asset(path)
    if label is None:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        try:
            factory = unreal.DataAssetFactory()
            factory.set_editor_property('data_asset_class', unreal.PrimaryAssetLabel)
            label = tools.create_asset(name, folder, unreal.PrimaryAssetLabel, factory)
        except Exception:
            label = None
        if label is None:
            label = tools.create_asset(name, folder, unreal.PrimaryAssetLabel, None)
    if label is None:
        raise RuntimeError('the label %s could not be made' % path)
    rules = label.get_editor_property('rules')
    setp(rules, 'chunk_id', chunk)
    setp(rules, 'priority', max(1, int(getp(rules, 'priority'))))
    setp(rules, 'cook_rule', unreal.PrimaryAssetCookRule.ALWAYS_COOK)
    setp(rules, ['apply_recursively', 'b_apply_recursively'], False)
    setp(label, 'rules', rules)
    setp(label, ['label_assets_in_my_directory', 'b_label_assets_in_my_directory'], False)
    try:
        setp(label, 'explicit_assets', assets)
    except Exception:
        setp(label, 'explicit_assets', [unreal.SoftObjectPath(a.get_path_name()) for a in assets])
    held = len(getp(label, 'explicit_assets'))
    if not unreal.EditorAssetLibrary.save_loaded_asset(label, False):
        raise RuntimeError('the label %s could not be saved' % path)
    return '%s: chunk %d, %d asset(s)' % (path, chunk, held)


def load_progress(version):
    """The melee moves built by an earlier run of this plan with this plugin, and any that stopped the editor."""
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
        progress['stopped'][progress['current']] = 'stopped the editor in run %d' % (progress['runs'] - 1)
    progress['current'] = None
    write_json(PROGRESS, progress)
    return progress


try:
    if os.path.exists(RESULT):
        os.replace(RESULT, RESULT + '.previous')
    version = plugin_version()
    if version != NEEDED_PLUGIN:
        raise RuntimeError('the project\'s Create a Character System plugin is %s and this needs %s' % (version or 'not found', NEEDED_PLUGIN))
    progress = load_progress(version)
    log('run', 'run %d with the plugin %s' % (progress['runs'], version))

    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    folders = [m['folder'] for m in PLAN['motion_labels']] + [m['folder'] for m in PLAN['model_labels']] + \
              ['/Game/Motion/Player/PC0000_Cloud', '/Game/RebirthSkelCompat/Built/Vincent', '/Game/Character/Player/PC0011_00_Vincent_Standard']
    registry.scan_paths_synchronous(folders, True)
    log('scanned', folders)

    # 1. The motions: every p000_/p007_ animation of the two folders, each checked, then labeled for its chunk.
    report = {}
    labels = []
    for spec in PLAN['motion_labels']:
        found = [a for a in registry.get_assets_by_path(spec['folder'], False)
                 if str(a.asset_class) == 'AnimSequence' and str(a.asset_name).startswith(spec['prefix'])]
        good, bad = [], []
        for asset in sorted(found, key=lambda a: str(a.asset_name)):
            path = str(asset.object_path)
            problem = saved_animation_problem(package_file(path))
            if problem:
                bad.append('%s (%s)' % (asset.asset_name, problem))
                continue
            anim = unreal.EditorAssetLibrary.load_asset(path)
            if anim is None:
                bad.append('%s (does not load)' % asset.asset_name)
                continue
            skeleton = anim.get_editor_property('skeleton')
            skeleton_path = skeleton.get_path_name() if skeleton else ''
            if skeleton_path != spec['skeleton']:
                bad.append('%s (on %s, not %s)' % (asset.asset_name, skeleton_path or 'no skeleton', spec['skeleton']))
                continue
            length = float(anim.get_editor_property('sequence_length'))
            info = {'path': path, 'length': round(length, 4)}
            try:
                info['frames'] = int(unreal.AnimationLibrary.get_num_frames(anim))
            except Exception:
                pass
            for key, names in (('root_motion', ['enable_root_motion', 'b_enable_root_motion']),
                               ('force_root_lock', ['force_root_lock', 'b_force_root_lock']), ('rate_scale', 'rate_scale')):
                try:
                    info[key] = getp(anim, names)
                except Exception:
                    pass
            info.update(bone_travel(anim, length))
            report[str(asset.asset_name)] = info
            good.append(anim)
        labels.append(make_label(spec['folder'], spec['label'], spec['chunk'], good))
        log('motions_' + spec['prefix'].rstrip('_'), '%d of %d motion(s) labeled for chunk %d%s' % (
            len(good), len(found), spec['chunk'], ('; LEFT OUT: ' + ', '.join(bad)) if bad else ''))
    with open(os.path.join(OUT, 'motions.json'), 'w') as f:
        json.dump(report, f, indent=1, default=str)

    # 2. Chaos's model: everything in its folder (and under it) but the editor's own data objects.
    for spec in PLAN['model_labels']:
        found = [a for a in registry.get_assets_by_path(spec['folder'], True)
                 if str(a.asset_class) not in spec['leave_out_classes'] and str(a.asset_class) != 'PrimaryAssetLabel']
        assets, missing = [], []
        for asset in found:
            loaded = unreal.EditorAssetLibrary.load_asset(str(asset.object_path))
            (assets if loaded else missing).append(loaded if loaded else str(asset.object_path))
        labels.append(make_label(spec['folder'], spec['label'], spec['chunk'], assets))
        classes = {}
        for asset in found:
            classes[str(asset.asset_class)] = classes.get(str(asset.asset_class), 0) + 1
        log('model_' + str(spec['chunk']), '%d asset(s) of %s for chunk %d (%s)%s' % (
            len(assets), spec['folder'], spec['chunk'], ', '.join('%s x%d' % kv for kv in sorted(classes.items())),
            ('; NOT loading: ' + ', '.join(missing)) if missing else ''))
    log('labels', labels)

    # 3. Square: the melee combo, in Vincent_Moves' row for Cloud's slot.
    data = unreal.EditorAssetLibrary.load_asset(PLAN['data_object'])
    if data is None:
        raise RuntimeError('the data object does not load: ' + PLAN['data_object'])
    content_file = package_file(PLAN['data_object'])
    backup = content_file + '.before_dirge'
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
    moves = list(getp(row, 'moves'))
    replaced, added = [], []
    for item in PLAN['melee']:
        move = None
        for m in moves:
            if str(getp(m, 'name')) == item['name'] and str(getp(m, 'set')) == item['set']:
                move = m
                break
        if move is None:
            move = unreal.EndAnimSetMove()
            moves.append(move)
            added.append(item['set'] + '/' + item['name'])
        else:
            replaced.append(item['set'] + '/' + item['name'])
        setp(move, 'name', item['name'])
        setp(move, 'set', item['set'])
        setp(move, 'animation', item['animation'])
        setp(move, ['build', 'b_build'], True)
        setp(move, ['shot', 'b_shot'], False)
        setp(move, 'hit_at', float(item['hit_at']))
        setp(move, 'hits', [])
        setp(move, 'notifies_from', '')
        setp(move, 'clip_start', 0.0)
        setp(move, 'clip_end', 0.0)
        setp(move, 'speed', 1.0)
    # the moves back into the row, the row into the data object (the editor hands out copies of its structs)
    setp(row, 'moves', moves)
    rows[row_index] = row
    setp(data, 'animation_sets', rows)
    game_directory = getp(data, 'game_directory')
    kept_game_directory = str(getp(game_directory, 'path'))
    empty = unreal.DirectoryPath()
    setp(empty, 'path', '')
    setp(data, 'game_directory', empty)       # the compat file goes to Saved; the installer puts it in the game
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)
    log('row', 'row %d: %d moves (%s replaced, %s added)' % (row_index, len(moves), ', '.join(replaced) or 'none', ', '.join(added) or 'none'))

    build_folder = str(getp(row, 'build_folder')) or '/Game/RebirthSkelCompat/Built/Vincent'
    base = os.path.join(CONTENT, build_folder[len('/Game/'):].replace('/', os.sep))
    reports, failed = [], []
    for item in PLAN['melee']:
        key = item['set'] + '/' + item['name']
        package = os.path.join(base, item['set'], item['name'] + '.uasset')
        if key in progress['stopped']:
            failed.append(key + ' (' + progress['stopped'][key] + ')')
            continue
        if key not in progress['done'] or not os.path.exists(package):
            progress['current'] = key
            write_json(PROGRESS, progress)
            unreal.log('VINCENT DIRGE move %s from %s' % (key, item['animation']))
            ok, text = split(data.build_one_move(row_index, item['name'], item['set']))
            if not text:
                text = str(getp(data, 'last_result'))
            lines = [line for line in text.strip().split('\n') if line.strip()]
            progress['done'][key] = {'ok': bool(ok), 'report': ' | '.join(lines[:6])[:3000]}
            progress['current'] = None
            write_json(PROGRESS, progress)
        done = progress['done'].get(key, {'ok': False, 'report': 'not built'})
        reports.append(key + ': ' + done['report'])
        if not os.path.exists(package):
            failed.append(key + ' (not built)')
            continue
        problem = saved_animation_problem(package)
        if problem:
            failed.append(key + ' (' + problem + ')')
        elif saved_compression(package) != 'ACL':
            failed.append(key + ' (' + saved_compression(package) + ')')
        elif not done['ok']:
            failed.append(key + ' (the build reported an error)')
    with open(os.path.join(OUT, 'build_moves.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(reports) + '\n')
    log('melee', '%d of %d built%s' % (len(PLAN['melee']) - len(failed), len(PLAN['melee']), ('; FAILED: ' + '; '.join(failed)) if failed else ''))
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)

    made = describe(['%s/%s/%s.%s' % (build_folder, m['set'], m['name'], m['name']) for m in PLAN['melee']])
    with open(os.path.join(OUT, 'melee_built.json'), 'w') as f:
        json.dump(made, f, indent=1)

    # 4. The compat file (to Saved), the checks, then the data object's game folder as it was.
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
    log('melee_failed', failed)
    log('done', True)   # the motions and the model are labeled: packaging goes on (a melee move not built keeps its old one)
except Exception:
    log('error', traceback.format_exc())
