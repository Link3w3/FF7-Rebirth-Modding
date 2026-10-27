# Vincent, the Dirge of Cerberus shooter, step 1b (the editor's part). Run by run_dirge_motions.cmd with the End editor
# closed (an editor commandlet); the plan is dirge_motions_plan.json next to this file.
#
# The project never cooks /Game/Motion (Project Settings > Packaging > Directories To Never Cook), so step 1's labels in
# the motion folders packaged nothing: pakchunk53 and 54 were not made. Here every Dirge of Cerberus motion of Vincent
# (/Game/Motion/Player/PC0011_00_Vincent/Battle00/p000_*) and of Chaos (/Game/Motion/Player/PC0011_10_Chaos/Battle00/p007_*)
# is made anew by the Create a Character System plugin (Build One Move: an animation is never duplicated in this engine,
# the plugin makes a new one with the motion's keys as they are, on the motion's own skeleton, compressed with the game's
# ACL settings: the game reads every animation with them) under its own name in /Game/RebirthSkelCompat/Dirge/Vincent
# (labeled for pakchunk53) and /Game/RebirthSkelCompat/Dirge/Chaos (pakchunk54). Two data objects hold those moves
# (Vincent_DirgeMotions, Chaos_DirgeMotions in /Game/RebirthSkelCompat/Dirge); nothing of theirs goes in the game's compat
# files. Chaos's model gets a label of its own name (step 1's had the name of the one in Chaos's motion folder, and the
# project keeps only one of two labels of one name); step 1's labels are emptied (nothing is deleted).
#
# Results: Saved\RebirthSkelCompat\VincentDirge\ (motions_result.json, motions_progress.json, motions_built.json,
# motions_build.txt).
import hashlib, json, os, struct, time, traceback
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN_FILE = os.path.join(HERE, 'dirge_motions_plan.json')
PLAN = json.load(open(PLAN_FILE))
PLAN_MD5 = hashlib.md5(open(PLAN_FILE, 'rb').read()).hexdigest()
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
CONTENT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'VincentDirge')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'motions_result.json')
PROGRESS = os.path.join(OUT, 'motions_progress.json')
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
    unreal.log('DIRGE MOTIONS %s: %s' % (key, str(value)[:2000]))
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
        unreal.log_warning('DIRGE MOTIONS: DescribeAnimations failed (%s)' % ex)
        return {}


def plugin_version():
    project = os.path.dirname(os.path.normpath(SAVED))
    try:
        return json.load(open(os.path.join(project, 'Plugins', 'RebirthSkelCompat', 'RebirthSkelCompat.uplugin'))).get('VersionName', '')
    except Exception:
        return ''


def new_asset(folder, name, cls, factory_class=None):
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    made = None
    try:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property('data_asset_class', factory_class or cls)
        made = tools.create_asset(name, folder, cls, factory)
    except Exception:
        made = None
    if made is None:
        made = tools.create_asset(name, folder, cls, None)
    return made


def set_label(path, chunk, assets, cook=True):
    """The Primary Asset Label at path (made when missing) puts exactly `assets` in chunk at pack time; chunk -1 with no
    assets: a label that does nothing."""
    folder, name = path.rsplit('/', 1)
    label = unreal.EditorAssetLibrary.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if label is None:
        if not cook:
            return '%s: not there' % path
        label = new_asset(folder, name, unreal.PrimaryAssetLabel)
    if label is None:
        raise RuntimeError('the label %s could not be made' % path)
    rules = label.get_editor_property('rules')
    setp(rules, 'chunk_id', chunk)
    setp(rules, 'priority', max(1, int(getp(rules, 'priority'))))
    setp(rules, 'cook_rule', unreal.PrimaryAssetCookRule.ALWAYS_COOK if cook else unreal.PrimaryAssetCookRule.UNKNOWN)
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
    """The motions made by an earlier run of this plan with this plugin, and any that stopped the editor."""
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


def data_object_for(spec, moves):
    """The set's data object: one row, its moves the motions (each made from itself: its keys, its notifies, if any)."""
    path = spec['data_object']
    folder, name = path.rsplit('/', 1)
    data = unreal.EditorAssetLibrary.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if data is None:
        data = new_asset(folder, name, unreal.EndSkeletonCompatDataObject)
    if data is None:
        raise RuntimeError('the data object %s could not be made' % path)
    skeleton = unreal.EditorAssetLibrary.load_asset(spec['skeleton'])
    if skeleton is None:
        raise RuntimeError('the skeleton does not load: ' + spec['skeleton'])
    row = unreal.EndAnimSetRow()
    setp(row, ['enabled', 'b_enabled'], True)
    setp(row, 'characters', [])
    setp(row, 'build_folder', spec['build_folder'])
    try:
        setp(row, 'character_skeleton', skeleton)
    except Exception:
        setp(row, 'character_skeleton', unreal.SoftObjectPath(spec['skeleton']))
    list_ = []
    for anim_name, anim_path in moves:
        move = unreal.EndAnimSetMove()
        setp(move, 'name', anim_name)
        setp(move, 'set', '')
        setp(move, 'animation', anim_path)
        setp(move, ['build', 'b_build'], True)
        setp(move, ['shot', 'b_shot'], False)
        setp(move, 'hit_at', 0.0)
        setp(move, 'hits', [])
        setp(move, 'notifies_from', anim_path)   # (its own: a motion has no gameplay notifies to take)
        setp(move, 'clip_start', 0.0)
        setp(move, 'clip_end', 0.0)
        setp(move, 'speed', 1.0)
        list_.append(move)
    setp(row, 'moves', list_)
    setp(data, 'animation_sets', [row])
    setp(data, 'build_chunk', int(spec['chunk']))
    empty = unreal.DirectoryPath()
    setp(empty, 'path', '')
    try:
        setp(data, 'game_directory', empty)   # (never exported to the game)
    except Exception:
        pass
    if not unreal.EditorAssetLibrary.save_loaded_asset(data, False):
        raise RuntimeError('the data object %s could not be saved' % path)
    return data


try:
    if os.path.exists(RESULT):
        os.replace(RESULT, RESULT + '.previous')
    version = plugin_version()
    if version != NEEDED_PLUGIN:
        raise RuntimeError('the project\'s Create a Character System plugin is %s and this needs %s' % (version or 'not found', NEEDED_PLUGIN))
    progress = load_progress(version)
    log('run', 'run %d with the plugin %s' % (progress['runs'], version))

    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    folders = [s['folder'] for s in PLAN['clip_sets']] + [PLAN['model_label']['folder'], '/Game/RebirthSkelCompat']
    registry.scan_paths_synchronous(folders, True)
    log('scanned', folders)

    # 1. Step 1's labels emptied (they are in folders the project never cooks, or have the name of another).
    emptied = []
    for path in PLAN['old_labels']:
        try:
            emptied.append(set_label(path, -1, [], cook=False))
        except Exception as ex:
            emptied.append('%s: not emptied (%s)' % (path, ex))
    log('old_labels', emptied)

    # 2. Chaos's model: everything in its folder (and under it) but the editor's own objects, under a label of its own name.
    spec = PLAN['model_label']
    found = [a for a in registry.get_assets_by_path(spec['folder'], True) if str(a.asset_class) not in spec['leave_out_classes']]
    assets, missing, classes = [], [], {}
    for asset in found:
        loaded = unreal.EditorAssetLibrary.load_asset(str(asset.object_path))
        (assets if loaded else missing).append(loaded if loaded else str(asset.object_path))
        classes[str(asset.asset_class)] = classes.get(str(asset.asset_class), 0) + 1
    label_text = set_label(spec['folder'] + '/' + spec['label'], spec['chunk'], assets)
    log('model_label', '%s (%s)%s' % (label_text, ', '.join('%s x%d' % kv for kv in sorted(classes.items())),
                                      ('; NOT loading: ' + ', '.join(missing)) if missing else ''))

    # 3. The motions, made anew in the Dirge folders (labeled for their chunks by the plugin as it builds).
    built_report = {}
    lines = []
    for spec in PLAN['clip_sets']:
        found = sorted([a for a in registry.get_assets_by_path(spec['folder'], False)
                        if str(a.asset_class) == 'AnimSequence' and str(a.asset_name).startswith(spec['prefix'])],
                       key=lambda a: str(a.asset_name))
        moves, bad = [], []
        for asset in found:
            path = str(asset.object_path)
            problem = saved_animation_problem(package_file(path))
            if problem:
                bad.append('%s (%s)' % (asset.asset_name, problem))
            else:
                moves.append((str(asset.asset_name), path))
        data = data_object_for(spec, moves)
        base = os.path.join(CONTENT, spec['build_folder'][len('/Game/'):].replace('/', os.sep))
        made, failed = [], []
        started = time.time()
        for index, (name, path) in enumerate(moves):
            key = spec['name'] + '/' + name
            package = os.path.join(base, name + '.uasset')
            if key in progress['stopped']:
                failed.append(name + ' (' + progress['stopped'][key] + ')')
                continue
            if key not in progress['done'] or not os.path.exists(package):
                progress['current'] = key
                write_json(PROGRESS, progress)
                ok, text = split(data.build_one_move(0, name, ''))
                if not text:
                    try:
                        text = str(getp(data, 'last_result'))
                    except Exception:
                        text = ''
                said = [line for line in text.strip().split('\n') if line.strip()]
                progress['done'][key] = {'ok': bool(ok), 'report': ' | '.join(said[:3])[:400]}
                progress['current'] = None
            done = progress['done'].get(key, {'ok': False, 'report': 'not made'})
            lines.append(key + ': ' + done['report'])
            if not os.path.exists(package):
                failed.append(name + ' (not made)')
                continue
            problem = saved_animation_problem(package)
            if problem:
                failed.append(name + ' (' + problem + ')')
            elif saved_compression(package) != 'ACL':
                failed.append(name + ' (' + saved_compression(package) + ')')
            elif not done['ok']:
                failed.append(name + ' (the plugin reported an error)')
            else:
                made.append(name)
        write_json(PROGRESS, progress)
        info = describe(['%s/%s.%s' % (spec['build_folder'], n, n) for n in made])
        clips = {}
        for name in made:
            item = info.get('%s/%s.%s' % (spec['build_folder'], name, name), {})
            clips[name] = {k: item.get(k) for k in ('length', 'frames', 'root_motion', 'notifies') if k in item}
            if isinstance(clips[name].get('notifies'), list):
                clips[name]['notifies'] = len(clips[name]['notifies'])
        built_report[spec['name']] = {'folder': spec['build_folder'], 'chunk': spec['chunk'], 'clips': clips}
        log('motions_' + spec['name'], '%d of %d made in %s for chunk %d (%.0f s)%s%s' % (
            len(made), len(found), spec['build_folder'], spec['chunk'], time.time() - started,
            ('; LEFT OUT (saved broken): ' + ', '.join(bad)) if bad else '', ('; FAILED: ' + '; '.join(failed[:40])) if failed else ''))
    with open(os.path.join(OUT, 'motions_build.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    write_json(os.path.join(OUT, 'motions_built.json'), built_report)
    log('done', True)
except Exception:
    log('error', traceback.format_exc())
