# Remake Sephiroth's animations (FF7 Remake's EB0021 boss: Battle00, Battle01, Neutral00, Reaction00) on Rebirth
# Sephiroth's PC0010_00 skeleton, as FBX files: the editor step of run_remake_fbx.cmd (End editor closed).
# Each animation is retargeted with Create a Character System's Build Moves (Proportions, as the REMAKE forms' moves),
# saved in /Game/RebirthSkelCompat/Built/RemakeSephirothPC0010/Battle08/<Folder>_<Animation>, and exported with the
# engine's FBX exporter to Saved/RemakeSephirothFBX/<Folder>/<Animation>.fbx (then all of them in RemakeSephirothFBX.zip),
# with PC0010_00 as their preview mesh (the exporter needs one): RebirthRemakeImportLibrary.ExportAnimationsFbx, editor 1.16.2.
# One animation at a time, its progress in progress.json, so one that stops the editor is left out when
# run_remake_fbx.ps1 runs this again, and the ones built already are kept.
import json, os, time, traceback, zipfile
import unreal

SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RemakeSephirothFBX')
STATE = os.path.join(OUT, '_build')
RESULT = os.path.join(STATE, 'build_result.json')
PROGRESS = os.path.join(STATE, 'progress.json')
ZIP = os.path.join(SAVED, 'RemakeSephirothFBX.zip')
SOURCE = '/Game/GameContents/Motion/Enemy/EB0021_Sephiroth'
FOLDERS = ['Battle00', 'Battle01', 'Neutral00', 'Reaction00']
DATA_PATH = '/Game/RebirthSkelCompat/RemakeFbx/RemakeSephirothFbx_Data'
BUILD_FOLDER = '/Game/RebirthSkelCompat/Built/RemakeSephirothPC0010'
SET = 'Battle08'
SKELETON = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00_Skeleton.PC0010_00_Skeleton'
MESH = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00.PC0010_00'
EXPORT_BATCH = 20
CHARACTERS = ['/Game/DataAsset/Game/CharaSpec/CharaSpec_PC0000_00_Cloud_Standard.CharaSpec_PC0000_00_Cloud_Standard']
SOURCES = [('/Game/Motion/Player/PC0010_Sephiroth/Battle00.Battle00', SET)]
results = {'steps': []}


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp = path + '.tmp'
    with open(temp, 'w') as f:
        json.dump(value, f, indent=1)
    os.replace(temp, path)


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('REMAKE FBX %s: %s' % (key, str(value)[:2000]))
    write_json(RESULT, results)


def setp(obj, names, value):
    last = None
    for name in names if isinstance(names, (list, tuple)) else [names]:
        try:
            obj.set_editor_property(name, value)
            return True
        except Exception as ex:
            last = ex
    raise last


def try_set(obj, names, value):
    try:
        return setp(obj, names, value)
    except Exception:
        return False


def split(result):
    if isinstance(result, tuple):
        return result[0], (result[1] if len(result) > 1 else '')
    return result, ''


def progress():
    try:
        return json.load(open(PROGRESS))
    except Exception:
        return {}


def animations():
    """[(folder, animation name, object path)] of Remake Sephiroth's animations, in folder and name order."""
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    out = []
    for folder in FOLDERS:
        path = SOURCE + '/' + folder
        registry.scan_paths_synchronous([path], True)
        found = registry.get_assets(unreal.ARFilter(class_names=['AnimSequence'], package_paths=[path], recursive_paths=False))
        for a in sorted(found, key=lambda a: str(a.asset_name)):
            name = str(a.asset_name)
            out.append((folder, name, '%s.%s' % (str(a.package_name), name)))
    return out


def move_name(folder, name):
    return '%s_%s' % (folder, name)


def setup(anims):
    skeleton = unreal.load_asset(SKELETON)
    if skeleton is None:
        raise RuntimeError('the PC0010_00 skeleton does not load: ' + SKELETON)
    data = unreal.EditorAssetLibrary.load_asset(DATA_PATH) if unreal.EditorAssetLibrary.does_asset_exist(DATA_PATH) else None
    made = data is None
    if made:
        folder, name = DATA_PATH.rsplit('/', 1)
        data = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.EndSkeletonCompatDataObject, None)
    if data is None:
        raise RuntimeError('the data object could not be made')
    moves = []
    for folder, name, path in anims:
        move = unreal.EndAnimSetMove()
        setp(move, 'name', move_name(folder, name))
        setp(move, 'set', SET)
        setp(move, 'animation', path)
        setp(move, ['build', 'b_build'], True)
        setp(move, 'retarget', unreal.EndMoveRetarget.PROPORTIONS)
        setp(move, 'notifies_from', path)                 # (its own: Remake's FBX import has no gameplay notifies)
        try_set(move, ['keep_source_effects', 'b_keep_source_effects'], False)
        setp(move, 'hits', [])
        moves.append(move)
    row = unreal.EndAnimSetRow()
    setp(row, ['enabled', 'b_enabled'], True)
    setp(row, 'characters', CHARACTERS)
    sources = []
    for spath, as_ in SOURCES:
        source = unreal.EndAnimSetSource()
        setp(source, 'path', spath)
        setp(source, ['as_', 'as', 'As'], as_)
        sources.append(source)
    setp(row, 'battle', sources)
    setp(row, 'character_skeleton', skeleton)
    setp(row, 'build_folder', BUILD_FOLDER)
    setp(row, 'moves', moves)
    setp(data, 'animation_sets', [row])
    try_set(data, 'build_chunk', 0)
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)
    return data, ('made ' if made else 'updated ') + DATA_PATH


def built_path(folder, name):
    n = move_name(folder, name)
    return '%s/%s/%s.%s' % (BUILD_FOLDER, SET, n, n)


def export_batch(items):
    """[(key, built object path, FBX file)] -> {key: error or None} with the plugin's exporter (editor 1.16.2)"""
    report = json.loads(unreal.RebirthRemakeImportLibrary.export_animations_fbx([p for k, p, f in items], [f for k, p, f in items], MESH))
    if report.get('error'):
        return {k: report['error'] for k, p, f in items}
    failed = {x.get('animation'): x.get('why') for x in report.get('failed', [])}
    out = {}
    for k, p, f in items:
        if p in failed:
            out[k] = failed[p]
        elif os.path.isfile(f) and os.path.getsize(f) > 0:
            out[k] = None
        else:
            out[k] = 'no file written'
    return out


try:
    os.makedirs(STATE, exist_ok=True)
    if os.path.exists(RESULT):
        os.replace(RESULT, RESULT + '.previous')
    anims = animations()
    log('animations', '%d: %s' % (len(anims), ', '.join('%s %d' % (f, sum(1 for a in anims if a[0] == f)) for f in FOLDERS)))
    if not anims:
        raise RuntimeError('no animations under ' + SOURCE)
    state = progress()
    state.setdefault('done', {})
    state.setdefault('stopped', {})
    state['runs'] = state.get('runs', 0) + 1
    if state.get('current'):
        cur = state['current']
        if cur.startswith('export: ') and cur[8:] in state['done']:
            # (the FBX export of that one stopped the editor: it is left out of the exports, the rest go on)
            state['done'][cur[8:]]['export_stopped'] = True
            state['done'][cur[8:]]['error'] = 'the FBX export stopped the editor'
        else:
            state['stopped'][cur] = 'stopped the editor in run %d' % (state['runs'] - 1)
        state['current'] = None
    write_json(PROGRESS, state)
    log('run', 'run %d: %d built before, %d left out%s' % (state['runs'], len(state['done']), len(state['stopped']),
                                                            (': ' + ', '.join(sorted(state['stopped']))) if state['stopped'] else ''))
    data, note = setup(anims)
    log('setup', note)

    started, made, failed = time.time(), 0, {}
    for folder, name, path in anims:
        key = folder + '/' + name
        state = progress()
        if key in state['stopped'] or key in state['done']:
            continue
        state['current'] = key
        write_json(PROGRESS, state)
        entry = {}
        t0 = time.time()
        try:
            ok, report = split(data.build_one_move(0, move_name(folder, name), SET))
            if not ok:
                report = report or str(data.get_editor_property('last_result'))
                entry['error'] = ' | '.join(l for l in report.strip().split('\n') if l.strip())[:1200]
            else:
                entry['built'] = built_path(folder, name)
        except Exception:
            entry['error'] = traceback.format_exc()[-1200:]
        entry['seconds'] = round(time.time() - t0, 1)
        state = progress()
        state['done'][key] = entry
        state['current'] = None
        write_json(PROGRESS, state)
        made += 1
        if entry.get('error'):
            failed[key] = entry['error']
    log('built_now', '%d animation(s) in %.0f s' % (made, time.time() - started))

    # the FBX files: every built animation not exported yet, a batch at a time (progress saved after each batch)
    if not hasattr(unreal, 'RebirthRemakeImportLibrary') or not hasattr(unreal.RebirthRemakeImportLibrary, 'export_animations_fbx'):
        raise RuntimeError('this editor plugin has no ExportAnimationsFbx: build Create a Character System editor 1.16.2 first')
    state = progress()
    todo = [(k, v['built'], os.path.join(OUT, k.split('/', 1)[0], k.split('/', 1)[1] + '.fbx'))
            for k, v in sorted(state['done'].items()) if v.get('built') and not v.get('fbx') and not v.get('export_stopped')]
    started = time.time()
    for at in range(0, len(todo), EXPORT_BATCH):
        batch = todo[at:at + EXPORT_BATCH]
        state = progress()
        state['current'] = 'export: ' + batch[0][0]
        write_json(PROGRESS, state)
        result = export_batch(batch)
        state = progress()
        for k, p, f in batch:
            if result.get(k):
                state['done'][k]['error'] = 'built, but the FBX export failed: ' + result[k]
            else:
                state['done'][k]['fbx'] = os.path.relpath(f, OUT).replace(os.sep, '/')
                state['done'][k].pop('error', None)
        state['current'] = None
        write_json(PROGRESS, state)
    log('exported_now', '%d animation(s) in %.0f s' % (len(todo), time.time() - started))

    state = progress()
    good = sorted(k for k, v in state['done'].items() if v.get('fbx'))
    bad = {k: v.get('error') for k, v in state['done'].items() if not v.get('fbx')}
    bad.update({k: v for k, v in state['stopped'].items()})
    with zipfile.ZipFile(ZIP + '.tmp', 'w', zipfile.ZIP_DEFLATED) as z:
        for k in good:
            folder, name = k.split('/', 1)
            z.write(os.path.join(OUT, folder, name + '.fbx'), '%s/%s.fbx' % (folder, name))
    os.replace(ZIP + '.tmp', ZIP)
    log('failed', bad)
    log('zip', '%s (%d FBX files)' % (ZIP, len(good)))
    log('done', '%d of %d animations as FBX in %s' % (len(good), len(anims), OUT))
except Exception:
    log('error', traceback.format_exc())
