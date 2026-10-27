# FF7 Remake's Sephiroth models in the End editor, read from the game's own files (skm_fbx.py wrote the FBX files):
#   /Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00            his standard model
#   /Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00_Skeleton   the skeleton they share
#   /Game/GameContents/Character/Enemy/EB0021_01_Sephiroth_Transform/Model/EB0021_01_Body      his transformed body
#   /Game/GameContents/Character/Enemy/EB0021_01_Sephiroth_Transform/Model/EB0021_01_Wing      and its wing
# each with the game's material instances (import_remake_mis.py) on its slots. The highest detail (LOD 0) only for now.
# Run in the End editor: run_import_remake_sephiroth.cmd starts it (UE4Editor.exe -ExecutePythonScript), editor closed.
# Results: Saved\RemakeMaterials\sephiroth_result.json
import json
import os
import traceback
import unreal

MODELS = r'C:\FF7R2UProj\Tools\RemakeMaterials\_build\remake_models'
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RemakeMaterials')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'sephiroth_result.json')
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
STD = '/Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard'
TRN = '/Game/GameContents/Character/Enemy/EB0021_01_Sephiroth_Transform'
SKELETON = STD + '/Model/EB0021_00_Skeleton'
JOBS = [
    dict(fbx='EB0021_00.fbx', folder=STD + '/Model', name='EB0021_00', skeleton=None, materials=STD + '/Material'),
    dict(fbx='EB0021_01_Body.fbx', folder=TRN + '/Model', name='EB0021_01_Body', skeleton=SKELETON, materials=TRN + '/Material'),
    dict(fbx='EB0021_01_Wing.fbx', folder=TRN + '/Model', name='EB0021_01_Wing', skeleton=SKELETON, materials=TRN + '/Material'),
]
results = {'steps': [], 'warnings': [], 'meshes': {}}


def save_results():
    json.dump(results, open(RESULT, 'w'), indent=1)


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('REMAKESEPH %s: %s' % (key, str(value)[:2000]))
    save_results()


def setp(obj, prop, value):
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception as ex:
        results['warnings'].append('could not set %s: %s' % (prop, ex))
        return False


def import_mesh(job):
    ui = unreal.FbxImportUI()
    setp(ui, 'import_mesh', True)
    setp(ui, 'import_as_skeletal', True)
    setp(ui, 'mesh_type_to_import', unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    setp(ui, 'automated_import_should_detect_type', False)
    setp(ui, 'import_materials', False)
    setp(ui, 'import_textures', False)
    setp(ui, 'import_animations', False)
    setp(ui, 'create_physics_asset', False)
    # (on a re-import the standard model takes the skeleton it made the first time, so all three keep sharing it)
    skeleton = job['skeleton'] or (SKELETON if EAL.does_asset_exist(SKELETON) else None)
    if skeleton:
        sk = unreal.load_asset(skeleton)
        if sk is None:
            raise RuntimeError('no skeleton ' + skeleton)
        setp(ui, 'skeleton', sk)
    sd = ui.get_editor_property('skeletal_mesh_import_data')
    setp(sd, 'import_morph_targets', False)
    setp(sd, 'normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)
    setp(sd, 'use_t0_as_ref_pose', False)
    setp(sd, 'convert_scene', True)
    setp(sd, 'force_front_x_axis', False)
    setp(sd, 'update_skeleton_reference_pose', False)
    setp(sd, 'import_meshes_in_bone_hierarchy', True)
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', os.path.join(MODELS, job['fbx']))
    task.set_editor_property('destination_path', job['folder'])
    task.set_editor_property('destination_name', job['name'])
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('automated', True)
    task.set_editor_property('save', False)
    task.set_editor_property('options', ui)
    AT.import_asset_tasks([task])
    path = '%s/%s' % (job['folder'], job['name'])
    sm = unreal.load_asset(path)
    if sm is None or not isinstance(sm, unreal.SkeletalMesh):
        raise RuntimeError('the import made no skeletal mesh at %s (see the editor log)' % path)
    out = {'path': path}
    mats = sm.get_editor_property('materials')
    assigned, missing = [], []
    for i in range(len(mats)):
        m = mats[i]                      # a copy: change it, then put it back
        slot = str(m.get_editor_property('material_slot_name'))
        mi = unreal.load_asset('%s/%s' % (job['materials'], slot)) if EAL.does_asset_exist('%s/%s' % (job['materials'], slot)) else None
        if mi is None:
            missing.append(slot)
            continue
        m.set_editor_property('material_interface', mi)
        mats[i] = m
        assigned.append(slot)
    sm.set_editor_property('materials', mats)
    EAL.save_loaded_asset(sm)
    sk = sm.get_editor_property('skeleton')
    if sk is not None:
        EAL.save_loaded_asset(sk)
        out['skeleton'] = sk.get_path_name()
    out['materials'] = assigned
    if missing:
        out['materials_missing'] = missing
        results['warnings'].append('%s: no material instance for %s (run run_import_remake_mis.cmd first)' % (job['name'], ', '.join(missing)))
    return out


try:
    for job in JOBS:
        try:
            results['meshes'][job['name']] = import_mesh(job)
        except Exception:
            results['meshes'][job['name']] = {'error': traceback.format_exc()[-1500:]}
            results['warnings'].append('%s failed' % job['name'])
        save_results()
    log('meshes_imported', '%d of %d' % (sum(1 for v in results['meshes'].values() if 'error' not in v), len(JOBS)))
    results['done'] = True
    log('finished', True)
except Exception:
    results['error'] = traceback.format_exc()
    results['done'] = False
    save_results()
    unreal.log_error('REMAKESEPH failed: ' + results['error'])
finally:
    if os.environ.get('REMAKESEPH_QUIT', '1') == '1':
        _quit = {'t': 0.0, 'h': None}

        def _quit_later(dt):
            _quit['t'] += dt
            if _quit['t'] > 3.0 and _quit['h'] is not None:
                unreal.unregister_slate_post_tick_callback(_quit['h'])
                _quit['h'] = None
                unreal.SystemLibrary.quit_editor()

        _quit['h'] = unreal.register_slate_post_tick_callback(_quit_later)
