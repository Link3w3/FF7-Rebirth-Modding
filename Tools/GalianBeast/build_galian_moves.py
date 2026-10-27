# Vincent's Galian Beast form: its moves (animation packs Battle07 and Battle08) made of the Galian boss's animations
# (EB2160, the Shinra Manor fight), with the Create a Character System editor plugin 1.12.4's Build Moves. Run by
# run_galian_moves.cmd (End editor and game closed); the plan is galian_moves.json next to this file (make_galian_moves.py),
# the forms the build needs galian_forms_import.json.
#
# The moves are built on the beast's skeleton (EB2160_00_Skeleton): the data object's row has two forms, GALIAN (Battle07)
# and GALIAN PUNISHER (Battle08), wearing the beast's model, which is not in this project, so Build Moves builds their moves
# on their Base's or their animation's skeleton, the beast's (every built move is checked for it).
#   attacks      the part of the beast's attack around its blow (a clip, a speed) with the gameplay notifies of Cloud's
#                move of that name (combo and cancel windows, dodge and guard cancels), its blows striking with the
#                PC0011_GB_* damage rows (each hit's Damage Source ID),
#   pieces       a piece of the beast's matching animation as long as Cloud's move; its dodges, steps and dashes the
#                beast's body (Base) moving with Cloud's root (Retarget "Keep the character's own pose", Bone Map
#                Trans=Trans: the beast's own go 6 to 12 m),
#   locomotion   the beast's own walks, runs, starts, turns and stops as they are (their root moves it, as the boss
#                moves); its strafes and its run's stops its walk or run with Cloud's root,
#   copies       ten of the boss's attacks as they are, for the commands (their trails and smoke without the boss's
#                ability check),
# and after the build, in the built moves: the voice lines of Cloud's moves taken out (the beast does not talk; its
# growls are its own sounds and stay) and the boss's ability check taken off the beast's effects (m_BranchConditionType:
# they play for the beast's own abilities too).
# One move at a time (Build One Move), each saved as it is built, with progress.json saying which one: a move that stops
# the editor is left out when run_galian_moves.ps1 runs the editor again, and the moves built already are kept.
# Results: Saved\RebirthSkelCompat\VincentGalian\ (build_result.json, progress.json, sources.json, build_moves.txt,
# edits.json, built.json, root_motion.json, export_json.txt, validate.txt), the compat file
# Saved\RebirthSkelCompat\DO_VincentGalian.skelcompat.json. The moves are saved in /Game/RebirthSkelCompat/Built/VincentGalian
# (pakchunk55).
import hashlib, json, math, os, struct, time, traceback
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN_FILE = os.path.join(HERE, 'galian_moves.json')
FORMS_FILE = os.path.join(HERE, 'galian_forms_import.json')
PLAN = json.load(open(PLAN_FILE))
PLAN_MD5 = hashlib.md5(open(PLAN_FILE, 'rb').read()).hexdigest()
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
CONTENT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'VincentGalian')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'build_result.json')
PROGRESS = os.path.join(OUT, 'progress.json')
NEEDED_PLUGIN = '1.12.4'
BEAST_SKELETON = PLAN['beast_skeleton']
results = {'steps': []}


def write_json(path, value):
    temp = path + '.tmp'
    with open(temp, 'w') as f:
        json.dump(value, f, indent=1)
    os.replace(temp, path)


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('GALIAN BUILD %s: %s' % (key, str(value)[:2000]))
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


def built_path(item):
    return '%s/%s/%s.%s' % (PLAN['build_folder'], item['set'], item['name'], item['name'])


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
    out = {}
    for start in range(0, len(paths), 200):   # (in parts: a long list is one long call)
        try:
            for item in json.loads(unreal.EndSkeletonCompatDataObject.describe_animations(paths[start:start + 200])):
                out[item.get('path', '')] = item
        except Exception as ex:
            unreal.log_warning('GALIAN BUILD: DescribeAnimations failed (%s)' % ex)
    return out


def plugin_version():
    project = os.path.dirname(os.path.normpath(SAVED))
    try:
        return json.load(open(os.path.join(project, 'Plugins', 'RebirthSkelCompat', 'RebirthSkelCompat.uplugin'))).get('VersionName', '')
    except Exception:
        return ''


def signature(item):
    """What a move is built from (a move built from other settings is built again)."""
    keys = ('animation', 'notifies_from', 'hits', 'clip', 'speed', 'base', 'base_loop', 'mode', 'kind')
    return hashlib.md5(json.dumps({k: item.get(k) for k in keys}, sort_keys=True).encode()).hexdigest()[:12]


def load_progress(version):
    """The moves built (and saved) by an earlier run with this plugin, those that stopped the editor, the edits made."""
    try:
        progress = json.load(open(PROGRESS))
    except Exception:
        progress = {}
    if progress.get('plugin') != version:
        progress = {'plugin': version, 'done': {}, 'stopped': {}, 'edited': {}, 'runs': 0}
    for key in ('done', 'stopped', 'edited'):
        progress.setdefault(key, {})
    progress['plan'] = PLAN_MD5
    progress['runs'] = progress.get('runs', 0) + 1
    if progress.get('current'):
        # the editor stopped while it built this move: it is left out from now on (the beast's own animation stays for it)
        progress['stopped'][progress['current']] = 'stopped the editor in run %d' % (progress['runs'] - 1)
    if progress.get('editing'):
        progress['edited'][progress['editing']] = {'error': 'stopped the editor in run %d while its notifies were edited' % (progress['runs'] - 1)}
    progress['current'] = None
    progress['editing'] = None
    write_json(PROGRESS, progress)
    return progress


def make_move(item):
    move = unreal.EndAnimSetMove()
    setp(move, 'name', item['name'])
    setp(move, 'set', item['set'])
    setp(move, 'animation', item['animation'])
    if item.get('then'):
        setp(move, 'then_play', item['then'])
    setp(move, ['build', 'b_build'], bool(item['build']))
    if not item['build']:
        return move
    setp(move, 'notifies_from', item['notifies_from'])
    hits = []
    for h in item.get('hits', []):
        hit = unreal.EndMoveHit()
        setp(hit, 'time', float(h['time']))
        if h.get('damage'):
            setp(hit, 'damage_source_id', h['damage'])
        hits.append(hit)
    setp(move, 'hits', hits)
    setp(move, ['shot', 'b_shot'], False)
    setp(move, 'hit_at', 0.0)
    setp(move, ['keep_source_effects', 'b_keep_source_effects'], True)    # the beast's own growls, steps, trails and smoke
    setp(move, ['source_sounds_only', 'b_source_sounds_only'], False)
    setp(move, 'speed', float(item.get('speed') or 1.0))
    setp(move, 'motion_from', '')
    setp(move, 'source_turn', 0.0)      # (the beast faces +X as Cloud does: its walk, run and steps go that way)
    setp(move, ['keep_base_root', 'b_keep_base_root'], False)
    if item.get('mode') == 'root':
        # the beast's body (Base) moving with Cloud's root: only Trans follows his animation
        setp(move, 'retarget', unreal.EndMoveRetarget.MOTION)
        setp(move, 'base', item['base'])
        setp(move, ['base_loop', 'b_base_loop'], bool(item.get('base_loop')))
        setp(move, 'bone_map', PLAN['bone_map'])
        setp(move, 'clip_start', 0.0)
        setp(move, 'clip_end', 0.0)
    else:
        # the beast's animation on its own skeleton, as it is (a clip of it, at a speed)
        setp(move, 'retarget', unreal.EndMoveRetarget.AS_IS)
        setp(move, 'base', '')
        setp(move, ['base_loop', 'b_base_loop'], False)
        setp(move, 'bone_map', '')
        clip = item.get('clip') or [0.0, 0.0]
        if item['kind'] == 'copy':
            clip = [0.0, 0.0]
        setp(move, 'clip_start', float(clip[0]))
        setp(move, 'clip_end', float(clip[1]))
    return move


def other_chunk_users(registry):
    """Other data objects that build into the plan's chunk."""
    users = []
    for asset in registry.get_assets_by_class('EndSkeletonCompatDataObject', True):
        package = str(asset.package_name)
        if package == PLAN['data_object']:
            continue
        obj = unreal.EditorAssetLibrary.load_asset('%s.%s' % (package, asset.asset_name))
        try:
            if obj is not None and int(getp(obj, 'build_chunk')) == int(PLAN['build_chunk']):
                users.append(package)
        except Exception:
            pass
    return users


def skeleton_of(anim):
    try:
        skeleton = getp(anim, 'skeleton')
        return skeleton.get_path_name() if skeleton else ''
    except Exception as ex:
        return 'unreadable (%s)' % ex


def root_motion(anim):
    """How the root (Trans) of a built move travels over it, and its length."""
    out = {}
    try:
        length = float(getp(anim, 'sequence_length'))
    except Exception as ex:
        return {'error': 'no length (%s)' % ex}
    out['length'] = round(length, 4)
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
    travel = [round(samples[-1][i] - samples[0][i], 1) for i in range(3)]
    out['travel'] = travel
    out['distance'] = round(math.hypot(travel[0], travel[1]), 1)
    out['samples'] = samples
    return out


def zero_of(value):
    """The first (0) value of an enum like `value` (None: not found)."""
    cls = type(value)
    for attr in dir(cls):
        if attr.startswith('_'):
            continue
        try:
            x = getattr(cls, attr)
        except Exception:
            continue
        if isinstance(x, cls):
            for get in (lambda v: v.value, lambda v: int(v), lambda v: v.get_value()):
                try:
                    if int(get(x)) == 0:
                        return x
                    break
                except Exception:
                    continue
    return None


def enum_number(value):
    for get in (lambda v: v.value, lambda v: int(v), lambda v: v.get_value()):
        try:
            return int(get(value))
        except Exception:
            continue
    return None


CONDITION = ['m_branch_condition_type', 'm_BranchConditionType']


def edit_notifies(path, voice, conditions):
    """Takes the voice lines out (`voice`) and the ability checks off the effects (`conditions`) of a built move; saves it."""
    did = {'voice': 0, 'conditions': 0}
    anim = unreal.EditorAssetLibrary.load_asset(path)
    if anim is None:
        return dict(did, error='does not load')
    events = unreal.AnimationLibrary.get_animation_notify_events(anim)
    by_name = {}
    changed = False
    for event in events:
        obj = None
        for prop in ('notify', 'notify_state_class'):
            try:
                obj = getp(event, prop)
            except Exception:
                obj = None
            if obj is not None:
                break
        cls = obj.get_class().get_name() if obj is not None else ''
        try:
            name = str(getp(event, 'notify_name'))
        except Exception:
            name = ''
        by_name.setdefault(name, set()).add(cls)
        if conditions and obj is not None:
            for prop in CONDITION:
                try:
                    current = obj.get_editor_property(prop)
                except Exception:
                    continue
                number = enum_number(current)
                if number:   # (an ability check: the effect plays for its own ability only)
                    zero = zero_of(current)
                    if zero is None:
                        did.setdefault('problems', []).append('%s: no "none" value for its check' % cls)
                    else:
                        obj.set_editor_property(prop, zero)
                        did['conditions'] += 1
                        changed = True
                break
    if voice:
        for name, classes in by_name.items():
            if classes and all('PlayVoice' in c for c in classes):
                before = len(unreal.AnimationLibrary.get_animation_notify_events(anim))
                unreal.AnimationLibrary.remove_animation_notify_events_by_name(anim, name)
                gone = before - len(unreal.AnimationLibrary.get_animation_notify_events(anim))
                did['voice'] += gone
                changed = changed or gone > 0
    if changed:
        unreal.EditorAssetLibrary.save_loaded_asset(anim, False)
    did['saved'] = changed
    return did


try:
    if os.path.exists(RESULT):
        os.replace(RESULT, RESULT + '.previous')
    results = {'steps': []}
    try:
        probe = unreal.EndAnimSetMove()
        probe.get_editor_property('base')
        probe.get_editor_property('bone_map')
        probe.get_editor_property('clip_start')
    except Exception:
        raise RuntimeError('this editor has no Base, Bone Map or Clip Start on moves: the Create a Character System plugin %s is needed' % NEEDED_PLUGIN)
    version = plugin_version()
    if version != NEEDED_PLUGIN:
        raise RuntimeError('the project\'s Create a Character System plugin is %s and this needs %s' % (version or 'not found', NEEDED_PLUGIN))
    progress = load_progress(version)
    log('run', 'run %d with the plugin %s: %d move(s) built before, %d left out (they stopped the editor)%s' % (
        progress['runs'], version, len(progress['done']), len(progress['stopped']),
        (': ' + ', '.join(sorted(progress['stopped']))) if progress['stopped'] else ''))

    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    folders = ['/Game/Motion/Enemy/EB2160_VincentValentine', '/Game/Motion/Player/PC0000_Cloud', '/Game/RebirthSkelCompat',
               '/Game/Character/Enemy/EB2160_00_VincentValentine_Standard', '/Game/Animation/CompressionSettings']
    registry.scan_paths_synchronous(folders, True)
    log('scanned', folders)

    # 0. The chunk the moves are packaged in is this data object's alone.
    users = other_chunk_users(registry)
    if users:
        raise RuntimeError('pakchunk%d is the build chunk of %s too: give this plan another chunk' % (PLAN['build_chunk'], ', '.join(users)))
    log('chunk', 'pakchunk%d: no other data object builds into it' % PLAN['build_chunk'])

    # 1. Every animation the moves are made of, take their notifies from or play over loads here.
    seen = describe(PLAN['describe'])
    write_json(os.path.join(OUT, 'sources.json'), seen)
    missing = sorted(p for p in PLAN['describe'] if 'error' in seen.get(p, {'error': 'not described'}))
    wrong = sorted(p for p, d in seen.items() if '/EB2160_VincentValentine/' in p and d.get('skeleton') and d.get('skeleton') != BEAST_SKELETON)
    log('sources', '%d of %d described%s%s' % (len(PLAN['describe']) - len(missing), len(PLAN['describe']),
                                               (', NOT loading: ' + ', '.join(missing)) if missing else '',
                                               (', NOT on the beast\'s skeleton: ' + ', '.join(wrong)) if wrong else ''))
    if len(missing) > 20:
        raise RuntimeError('%d of the animations the moves are made of do not load (sources.json): are the beast\'s animations in the project?' % len(missing))

    # 2. The data object and its row: the Galian rows of Vincent (Cloud's slot), the beast's sets, the moves.
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
    setp(row, 'build_folder', PLAN['build_folder'])
    setp(row, 'requires_paks', PLAN['requires_paks'])
    moves = [make_move(item) for item in PLAN['moves']]
    setp(row, 'moves', moves)
    setp(data, 'animation_sets', [row])
    setp(data, 'build_chunk', int(PLAN['build_chunk']))
    game_dir = unreal.DirectoryPath()
    setp(game_dir, 'path', '')
    setp(data, 'game_directory', game_dir)   # the compat file goes to Saved; the mod's own is made from the results
    todo = [m for m in PLAN['moves'] if m['build']]
    log('row', '%d moves (%d to build, %d the beast\'s own or the built ones as they are)' % (len(moves), len(todo), len(moves) - len(todo)))

    # 3. The forms (their model, the beast's, tells Build Moves which skeleton their packs' moves are built on).
    file_path = unreal.FilePath()
    setp(file_path, 'file_path', FORMS_FILE)
    setp(data, 'import_file', file_path)
    try:
        data.call_method('ImportFromGameJson')
        report = str(getp(data, 'last_result'))
    except Exception as ex:
        report = 'call_method ImportFromGameJson failed (%s)' % ex
    open(os.path.join(OUT, 'import_forms.txt'), 'w', encoding='utf-8').write(report)
    setp(data, 'import_file', unreal.FilePath())
    row = getp(data, 'animation_sets')[0]
    forms = getp(getp(row, 'forms'), 'list')
    names = [str(getp(f, 'name')) for f in forms]
    packs = [str(getp(f, 'pack')) for f in forms]
    log('forms', ['%s (%s)' % (n, p or 'its own') for n, p in zip(names, packs)])
    if 'Battle07' not in packs or 'Battle08' not in packs:
        raise RuntimeError('the forms did not come in from %s (import_forms.txt)' % FORMS_FILE)
    if len(list(getp(row, 'moves'))) != len(moves):
        raise RuntimeError('the forms import changed the row\'s moves (%d, not %d): import_forms.txt' % (len(list(getp(row, 'moves'))), len(moves)))
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)

    # 4. Build every move with Build on, one at a time (each is saved as it is built).
    base = os.path.join(CONTENT, PLAN['build_folder'][len('/Game/'):].replace('/', os.sep))
    started, made_now = time.time(), 0
    for number, item in enumerate(todo, 1):
        key = item['set'] + '/' + item['name']
        package = os.path.join(base, item['set'], item['name'] + '.uasset')
        sig = signature(item)
        if key in progress['stopped']:
            continue
        done = progress['done'].get(key)
        if done and done.get('sig') == sig and os.path.exists(package):
            continue
        progress['current'] = key
        progress['edited'].pop(key, None)   # (a move built again is edited again)
        write_json(PROGRESS, progress)
        unreal.log('GALIAN BUILD move %d/%d: %s from %s' % (number, len(todo), key, item['animation']))
        ok, report = split(data.build_one_move(0, item['name'], item['set']))
        if not report:
            report = str(getp(data, 'last_result'))
        lines = [line for line in report.strip().split('\n') if line.strip()]
        progress['done'][key] = {'ok': bool(ok), 'sig': sig, 'report': ' | '.join(lines[:6])[:3000]}
        progress['current'] = None
        write_json(PROGRESS, progress)
        made_now += 1
    log('built_now', '%d move(s) in %.0f s' % (made_now, time.time() - started))

    # 5. Each built move: on the beast's skeleton; the voice lines out and the effects' ability checks off.
    failed_keys, skeletons, edits = set(), {}, {}
    for item in todo:
        key = item['set'] + '/' + item['name']
        package = os.path.join(base, item['set'], item['name'] + '.uasset')
        if key in progress['stopped'] or not os.path.exists(package):
            failed_keys.add(key)
            continue
        anim = unreal.EditorAssetLibrary.load_asset(built_path(item))
        skeleton = skeleton_of(anim) if anim is not None else 'does not load'
        skeletons[skeleton] = skeletons.get(skeleton, 0) + 1
        if skeleton != BEAST_SKELETON:
            failed_keys.add(key)
            edits[key] = {'error': 'built on %s, not the beast\'s skeleton' % skeleton}
            continue
        if key in progress['edited']:
            edits[key] = progress['edited'][key]
            continue
        if progress.get('edits_off'):
            edits[key] = {'error': 'not edited: ' + progress['edits_off']}
            continue
        progress['editing'] = key
        write_json(PROGRESS, progress)
        try:
            did = edit_notifies(built_path(item), voice=item['kind'] != 'copy', conditions=item['kind'] in ('attack', 'piece', 'copy'))
        except Exception as ex:
            did = {'error': 'not edited (%s)' % ex}
        problem = saved_animation_problem(package) if did.get('saved') else None
        if problem:
            # saved this way the move would stop the cooker: it is built again as Build Moves makes it, and no other move
            # is edited (their voice lines stay, their effects keep the boss's checks)
            progress['edits_off'] = 'the edited %s would stop the cooker (%s)' % (key, problem)
            ok, report = split(data.build_one_move(0, item['name'], item['set']))
            did = {'error': 'edited, it would stop the cooker (%s): built again unedited (%s)' % (problem, 'ok' if ok else 'FAILED')}
        progress['edited'][key] = did
        progress['editing'] = None
        write_json(PROGRESS, progress)
        edits[key] = did
    write_json(os.path.join(OUT, 'edits.json'), edits)
    log('skeletons', skeletons)
    log('edits', '%d move(s): %d voice line(s) out, %d effect check(s) off, %d with problems%s' % (
        len(edits), sum(e.get('voice', 0) for e in edits.values()), sum(e.get('conditions', 0) for e in edits.values()),
        sum(1 for e in edits.values() if e.get('error') or e.get('problems')),
        ('; EDITS OFF: ' + progress['edits_off']) if progress.get('edits_off') else ''))

    # 6. Every saved file: ACL, and readable the way the cooker reads it.
    reports, compression, broken, failed = [], {}, [], []
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
        if edits.get(key, {}).get('error', '').startswith('built on'):
            failed.append(key + ' (' + edits[key]['error'] + ')')
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
    effects = sum(1 for line in reports if 'cannot write taken out' in line)
    log('effect_parameters', '%d move(s) with effect parameters left out (the plugin 1.12.4; they play with their own values)' % effects)
    log('compression', compression)
    log('failed', failed)   # these are left out of the compat file (the beast's own animation of that name plays)
    log('build', '%d of %d built' % (len(todo) - len(failed), len(todo)))
    log('checked', '%d package(s), %s' % (len(todo) - len(failed), ('%d BROKEN: ' % len(broken)) + '; '.join(broken[:8]) if broken else 'all load back'))
    if broken:
        raise RuntimeError('%d saved animation(s) would stop the cooker: %s' % (len(broken), '; '.join(broken)))

    # 7. What the built moves hold (lengths, notifies, hits) and how far each moving one moves the beast.
    ok_items = [m for m in todo if (m['set'] + '/' + m['name']) not in failed_keys]
    write_json(os.path.join(OUT, 'built.json'), describe([built_path(m) for m in ok_items]))
    motion, off = {}, []
    for item in ok_items:
        if item['kind'] not in ('locomotion',) and item.get('mode') != 'root':
            continue
        key = item['set'] + '/' + item['name']
        anim = unreal.EditorAssetLibrary.load_asset(built_path(item))
        info = root_motion(anim) if anim is not None else {'error': 'does not load'}
        info['expect'] = item.get('expect')
        motion[key] = info
        want = (item.get('expect') or {}).get('root_travel')
        got = info.get('distance')
        if got is None:
            off.append('%s (%s)' % (key, info.get('error', 'not sampled')))
        elif want and want > 20.0 and abs(got - want) > 0.25 * want + 20.0:
            off.append('%s (%.0f cm, %.0f wanted)' % (key, got, want))
    write_json(os.path.join(OUT, 'root_motion.json'), motion)
    log('root_motion', '%d move(s) sampled; %s' % (len(motion), ('differs: ' + ', '.join(off)) if off else 'each goes as far as planned'))

    # 8. The compat file (to Saved) and the checks.
    for function, label in (('ExportJson', 'export_json'), ('Validate', 'validate')):
        try:
            data.call_method(function)
            text = str(getp(data, 'last_result'))
        except Exception as ex:
            text = 'call_method %s failed (%s)' % (function, ex)
        with open(os.path.join(OUT, label + '.txt'), 'w', encoding='utf-8') as f:
            f.write(text)
        log(label, text.split('\n', 1)[0])
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)
    exported = os.path.join(SAVED, 'RebirthSkelCompat', name + '.skelcompat.json')
    log('compat_file', exported if os.path.exists(exported) else 'NOT written: ' + exported)
    log('done', len(todo) - len(failed) > 0)   # packaging goes on when anything was built
except Exception:
    log('error', traceback.format_exc())
