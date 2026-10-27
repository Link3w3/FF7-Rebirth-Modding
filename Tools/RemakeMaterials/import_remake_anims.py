# FF7 Remake's Sephiroth animations (enemy EB0021) in the End editor, read from the game's own files (anim_fbx.py wrote
# the FBX files and manifest.json in _build\remake_anims\EB0021_Sephiroth, convert_remake_anims.py drives it):
#   /Game/GameContents/Motion/Enemy/EB0021_Sephiroth/<Folder>/<Anim>      AnimSequences, at the game's paths, on
#   /Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00_Skeleton   (the skeleton his three
#   models share; its bones and rest pose are left as they are: no mesh, no new skeleton, no reference pose update)
# Each one: the FBX imported at the game's frame rate (its keys are the game's frames), then only the bones the game's
# sequence has tracks for keep theirs (the others fall back to the mesh's reference pose, as in the game), its float
# curves (the game's keys), the game's root motion settings (on unless the sequence turns it off; root lock forced
# where the game forces it), its rate scale; the additive ones (B_*_Add) made additive again against their base
# sequence's frame, as in the game. The curve names are added to the skeleton (it is saved when that changed it).
# Run in the OPEN editor (each batch blocks the editor while it runs; about a second an animation):
#   Output Log > Cmd:  py "C:/FF7R2UProj/Tools/RemakeMaterials/import_remake_anims.py"              (all of them)
#                      py "C:/FF7R2UProj/Tools/RemakeMaterials/import_remake_anims.py" Battle00 0 40  (a batch)
#   or from Python:    import import_remake_anims as m; m.run(folder='Battle00', start=0, count=40)
# Results (merged over runs): Saved\RemakeMaterials\sephiroth_anims_result.json. Running it again re-imports in place.
import json
import os
import sys
import time
import traceback
import unreal

try:
    HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
except NameError:
    HERE = 'C:/FF7R2UProj/Tools/RemakeMaterials'
ANIMS = HERE + '/_build/remake_anims/EB0021_Sephiroth'
MANIFEST = ANIMS + '/manifest.json'
DEST = '/Game/GameContents/Motion/Enemy/EB0021_Sephiroth'
SKELETON = '/Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00_Skeleton'
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RemakeMaterials')
RESULT = os.path.join(OUT, 'sephiroth_anims_result.json')
AL = unreal.AnimationLibrary
EAL = unreal.EditorAssetLibrary
STEP = 0.001          # (a constant key becomes a linear key pair: the next value starts this long before its key)


def _load_results():
    try:
        with open(RESULT, encoding='utf-8') as f:
            r = json.load(f)
        if isinstance(r, dict) and isinstance(r.get('anims'), dict):
            return r
    except Exception:
        pass
    return {'anims': {}, 'runs': []}


def _save_results(r):
    os.makedirs(OUT, exist_ok=True)
    tmp = RESULT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(r, f, indent=1)
    os.replace(tmp, RESULT)


def _import_options(skeleton, rate):
    ui = unreal.FbxImportUI()
    for k, v in (('import_mesh', False), ('import_as_skeletal', False), ('import_animations', True), ('import_materials', False),
                 ('import_textures', False), ('create_physics_asset', False), ('automated_import_should_detect_type', False),
                 ('mesh_type_to_import', unreal.FBXImportType.FBXIT_ANIMATION),
                 ('original_import_type', unreal.FBXImportType.FBXIT_ANIMATION), ('skeleton', skeleton)):
        ui.set_editor_property(k, v)
    ad = ui.get_editor_property('anim_sequence_import_data')
    for k, v in (('animation_length', unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME),
                 ('use_default_sample_rate', False), ('custom_sample_rate', int(rate)),     # (the game's frames)
                 ('import_bone_tracks', True), ('import_custom_attribute', False),         # (curves: below)
                 # (not True: that would flatten a track whose keys all stay within about 0.1 degree of its first)
                 ('remove_redundant_keys', False), ('do_not_import_curve_with_zero', False),
                 ('delete_existing_morph_target_curves', False), ('preserve_local_transform', False),
                 ('convert_scene', True), ('force_front_x_axis', False), ('convert_scene_unit', False),
                 ('import_meshes_in_bone_hierarchy', False)):
        ad.set_editor_property(k, v)
    return ui


def _curve_keys(keys):
    """the game's keys (time, value, interp mode: 0 linear, 1 constant) -> linear keys: a constant key holds its value
    until STEP before the next key"""
    times, values = [], []
    for i, (t, v, mode) in enumerate(keys):
        times.append(float(t)); values.append(float(v))
        if int(mode) == 1 and i + 1 < len(keys):
            t1 = float(keys[i + 1][0])
            if t1 - STEP > float(t) + 2e-4:
                times.append(t1 - STEP); values.append(float(v))
    return times, values


def _import_one(e, skeleton, warnings):
    fbx = '%s/%s' % (ANIMS, e['fbx'])
    if not os.path.isfile(fbx):
        raise RuntimeError('no FBX ' + fbx)
    folder = '%s/%s' % (DEST, e['folder'])
    path = '%s/%s' % (folder, e['name'])
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', fbx)
    task.set_editor_property('destination_path', folder)
    task.set_editor_property('destination_name', e['name'])
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('automated', True)
    task.set_editor_property('save', False)
    task.set_editor_property('options', _import_options(skeleton, e['rate']))
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    a = unreal.load_asset(path)
    if a is None or not isinstance(a, unreal.AnimSequence):
        raise RuntimeError('the import made no AnimSequence at %s (see the editor log)' % path)
    sk = a.get_editor_property('skeleton')
    if sk is None or sk.get_path_name() != skeleton.get_path_name():
        raise RuntimeError('%s is on %s, not the EB0021 skeleton' % (path, sk.get_path_name() if sk else None))
    # only the bones the game's sequence has tracks for keep theirs
    keep = set(e['tracks'])
    names = [str(n) for n in AL.get_animation_track_names(a)]
    for n in names:
        if n not in keep:
            AL.remove_bone_animation(a, n, False, False)
    lost = sorted(keep - set(names))
    if lost:
        warnings.append('%s: no track came in for %s' % (e['name'], ', '.join(lost[:8])))
    AL.finalize_bone_animation(a)
    # float curves (the game's keys)
    AL.remove_all_curve_data(a)
    curves = []
    for c in e.get('curves', []):
        if not c['keys']:
            continue
        AL.add_curve(a, c['name'], unreal.RawCurveTrackTypes.RCT_FLOAT, False)
        times, values = _curve_keys(c['keys'])
        AL.add_float_curve_keys(a, c['name'], times, values)
        curves.append(c['name'])
    # the game's root motion settings (its sequences have root motion on unless they turn it off)
    AL.set_root_motion_enabled(a, bool(e['enable_root_motion']) if e.get('enable_root_motion') is not None else True)
    AL.set_is_root_motion_lock_forced(a, bool(e.get('force_root_lock')))
    if e.get('rate_scale') is not None:
        AL.set_rate_scale(a, float(e['rate_scale']))
    out = dict(path=path, frames=AL.get_num_frames(a), length=round(AL.get_sequence_length(a), 6),
               tracks=len(AL.get_animation_track_names(a)), curves=curves,
               root_motion=AL.is_root_motion_enabled(a), root_lock_forced=AL.is_root_motion_lock_forced(a))
    if out['frames'] != e['frames'] or abs(out['length'] - e['length']) > 1e-4:
        warnings.append('%s: %d frames %.4f s here, the game %d frames %.4f s' % (e['name'], out['frames'], out['length'], e['frames'], e['length']))
    return a, out


def _make_additive(a, e, out):
    """additive against the game's base again: the FBX holds the full pose (the game's deltas on that base)"""
    b = e['base']
    if b.get('type') == 'ABPT_AnimFrame':
        base_path = b['sequence'].split('.')[0]
        base = unreal.load_asset(base_path)
        if base is None:
            raise RuntimeError('the base sequence %s is not imported' % base_path)
        a.set_editor_property('ref_pose_seq', base)
        a.set_editor_property('ref_frame_index', int(b.get('frame') or 0))
        AL.set_additive_base_pose_type(a, unreal.AdditiveBasePoseType.ABPT_ANIM_FRAME)
        out['base'] = '%s frame %d' % (base_path, int(b.get('frame') or 0))
    else:
        AL.set_additive_base_pose_type(a, unreal.AdditiveBasePoseType.ABPT_REF_POSE)
        out['base'] = 'reference pose'
    AL.set_additive_animation_type(a, unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE)
    out['additive'] = str(AL.get_additive_animation_type(a))


def run(folder=None, start=0, count=None, names=None):
    """import the manifest's animations (folder: one folder; start/count: a slice of them, in manifest order;
    names: only these 'Folder/Anim' or 'Anim'); additive ones after their base"""
    t0 = time.time()
    with open(MANIFEST, encoding='utf-8') as f:
        man = json.load(f)
    entries = [e for e in man['anims'] if folder in (None, '', 'all') or e['folder'] == folder]
    if names:
        names = set(names)
        entries = [e for e in entries if e['name'] in names or '%s/%s' % (e['folder'], e['name']) in names]
    start = int(start or 0)
    entries = entries[start:start + int(count)] if count is not None else entries[start:]
    by_seq = {'%s/%s/%s' % (DEST, e['folder'], e['name']): e for e in man['anims']}
    # (an additive one needs its base imported first: put any missing base in front)
    todo, seen = [], set()
    for e in sorted(entries, key=lambda x: x.get('base') is not None):
        if e.get('base') and e['base'].get('type') == 'ABPT_AnimFrame':
            bp = e['base']['sequence'].split('.')[0]
            be = by_seq.get(bp)
            if be is not None and id(be) not in seen and not EAL.does_asset_exist(bp):
                todo.append(be); seen.add(id(be))
        if id(e) not in seen:
            todo.append(e); seen.add(id(e))
    skeleton = unreal.load_asset(SKELETON)
    if skeleton is None:
        raise RuntimeError('no skeleton ' + SKELETON)
    R = _load_results()
    run_info = dict(started=time.strftime('%Y-%m-%d %H:%M:%S'), folder=folder, start=start, count=count, asked=len(entries), imported=0, failed=0, warnings=[])
    with unreal.ScopedSlowTask(len(todo), 'FF7 Remake Sephiroth animations') as slow:
        slow.make_dialog(True)
        for e in todo:
            key = '%s/%s' % (e['folder'], e['name'])
            if slow.should_cancel():
                run_info['cancelled_before'] = key
                break
            slow.enter_progress_frame(1, 'FF7 Remake Sephiroth animations: ' + key)
            t1 = time.time()
            warnings = []
            try:
                a, out = _import_one(e, skeleton, warnings)
                if e.get('base'):
                    _make_additive(a, e, out)
                if not EAL.save_loaded_asset(a, False):
                    warnings.append('%s: could not save' % key)
                out['seconds'] = round(time.time() - t1, 2)
                if warnings:
                    out['warnings'] = warnings
                R['anims'][key] = out
                run_info['imported'] += 1
            except Exception:
                R['anims'][key] = {'error': traceback.format_exc()[-1500:], 'seconds': round(time.time() - t1, 2)}
                run_info['failed'] += 1
            run_info['warnings'] += warnings
    # (adding curves puts their names on the skeleton: save it when that changed it; its bones and rest pose stay)
    dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    if SKELETON in dirty:
        run_info['skeleton_saved'] = bool(EAL.save_loaded_asset(skeleton, False))
    run_info['seconds'] = round(time.time() - t0, 1)
    R['runs'].append(run_info)
    R['manifest'] = MANIFEST
    R['skipped_packages'] = man.get('skipped', [])
    R['count'] = dict(in_manifest=len(man['anims']), imported=sum(1 for v in R['anims'].values() if 'error' not in v),
                      failed=sum(1 for v in R['anims'].values() if 'error' in v))
    _save_results(R)
    unreal.log('REMAKEANIMS %d imported, %d failed in %.1f s (%s)' % (run_info['imported'], run_info['failed'], run_info['seconds'], RESULT))
    return run_info


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if a]
    run(folder=args[0] if args else None, start=int(args[1]) if len(args) > 1 else 0,
        count=int(args[2]) if len(args) > 2 else None)
