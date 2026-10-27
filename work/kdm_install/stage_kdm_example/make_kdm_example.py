# Kawaii Dynamic Motions, the editor step of run_kawaii_dynamic_motions_install.cmd: run in an End editor commandlet by
# run_kdm_example.py (the End editor closed), it makes the example AnimBlueprint of Bahamut Fused Sephiroth:
#   1. his key animations (anims\*.cacanim, made from the game's walk sampled in the editor: standing, breathing, and a
#      walk in place) made on PC0010_17_Compat_Skeleton in /Game/KawaiiDynamicMotions/Examples/BahamutFusedSephiroth
#      (Create a Character System's Import Key Animations);
#   2. ABP_BahamutFusedSephiroth_KawaiiDynamicMotions made there from BahamutFusedSephirothKawaii.json's entry (the one
#      installed in the game: his tail, mantles, blade wings and hair, the tail's sway and the wings' beat) with Kawaii
#      Dynamic Motions' Import From Game, playing the standing animation; compiled and saved.
# Result: Saved/KawaiiDynamicMotions/example_result.json ("done", or "error" with what went wrong).
import json
import os
import traceback

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'KawaiiDynamicMotions')
RESULT = os.path.join(OUT, 'example_result.json')
MODEL = '/Game/Character/Player/PC0010_17_Bahumunt_Fused_Sephiroth/Model'
MESH = MODEL + '/PC0010_17_Compat.PC0010_17_Compat'
SKELETON = MODEL + '/PC0010_17_Compat_Skeleton.PC0010_17_Compat_Skeleton'
DEST = '/Game/KawaiiDynamicMotions/Examples/BahamutFusedSephiroth'
ANIM_BLUEPRINT = DEST + '/ABP_BahamutFusedSephiroth_KawaiiDynamicMotions'
STAND = DEST + '/Bahamut_KDM_Stand.Bahamut_KDM_Stand'
COMPAT = os.path.join(HERE, 'BahamutFusedSephirothKawaii.json')
results = {'steps': []}


def write_json(path, value):
    temp = path + '.tmp'
    with open(temp, 'w') as f:
        json.dump(value, f, indent=1)
    os.replace(temp, path)


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('KAWAII DYNAMIC MOTIONS EXAMPLE %s: %s' % (key, str(value)[:2000]))
    write_json(RESULT, results)


try:
    os.makedirs(OUT, exist_ok=True)
    if os.path.exists(RESULT):
        os.replace(RESULT, RESULT + '.previous')
    importer = getattr(unreal, 'KawaiiPhysicsGameImport', None)
    if importer is None or not hasattr(importer, 'import_from_game_with_animation'):
        raise RuntimeError('Kawaii Dynamic Motions 1.9 (the KawaiiPhysics plugin) is not in this editor: its build did not go in')
    plugin = json.load(open(os.path.join(os.path.dirname(os.path.normpath(SAVED)), 'Plugins', 'KawaiiPhysics', 'KawaiiPhysics.uplugin'), encoding='utf-8'))
    log('plugin', '%s %s' % (plugin.get('FriendlyName'), plugin.get('VersionName')))
    mesh = unreal.load_asset(MESH)
    if not mesh:
        raise RuntimeError('his model %s does not load in this editor' % MESH)
    log('model', mesh.get_path_name())
    report = unreal.EndSkeletonCompatDataObject.import_key_animations(os.path.join(HERE, 'anims'), SKELETON, DEST)
    log('animations', (report or 'NOT ALL MADE (the report comes back only when every one went in: see the log)')[-1500:])
    if not report:
        raise RuntimeError('his key animations did not all go in')
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([DEST], True)
    stand = unreal.load_asset(STAND)
    if not stand:
        raise RuntimeError('the standing animation %s does not load' % STAND)
    made = unreal.KawaiiPhysicsGameImport.import_from_game_with_animation(COMPAT, mesh, ANIM_BLUEPRINT, -1, stand)
    log('anim_blueprint', made[-3000:])
    if made.startswith('FAILED'):
        raise RuntimeError(made)
    if 'compiled with ERRORS' in made:
        raise RuntimeError('the AnimBlueprint compiled with errors: ' + made)
    if '; saved' not in made:
        raise RuntimeError('the AnimBlueprint was not saved: ' + made)
    log('done', ANIM_BLUEPRINT)
except Exception:
    results['error'] = traceback.format_exc()
    unreal.log_error('KAWAII DYNAMIC MOTIONS EXAMPLE FAILED: ' + results['error'])
    write_json(RESULT, results)
