# Rebuilds a few of FF7 Remake's EndMaterial masters in place from remake_editor_spec.json, with the full build's own
# code (build_remake_materials.py, reusing the default textures and material functions it made), then puts the game's
# static switches back on those masters' renderer instances and compiles them and the character instances under them.
# By default the masters the 2026-10-21 fixes changed:
#   EndMaterial_Skin, EndMaterial_Blood   no subsurface colour (the game stores none; this engine's default white
#                                         washed the skin out)
#   EndMaterial_Hair                      the game's hair data (UV1 bent normal) for the engine's recovered hair lighting
# Others: set REMAKEPATCH_MASTERS=EndMaterial_A,EndMaterial_B before running.
# In the open editor: Output Log > Cmd:  py "C:/FF7R2UProj/Tools/RemakeMaterials/patch_remake_masters.py"
#   (it closes those masters' and instances' editor tabs first; the editor stays open)
# Or with the editor closed: run_patch_remake_masters.cmd
# Results: Saved\RemakeMaterials\patch_result.json (and patch_build_result.json: the masters' own build results)
import json
import os
import runpy
import time
import traceback
import unreal

HERE = os.path.dirname(os.path.abspath(globals().get('__file__') or r'C:\FF7R2UProj\Tools\RemakeMaterials\patch_remake_masters.py'))
DEFAULT = 'EndMaterial_Skin,EndMaterial_Blood,EndMaterial_Hair'
MASTERS = [x.strip() for x in (os.environ.get('REMAKEPATCH_MASTERS') or DEFAULT).split(',') if x.strip()]
QUIT = os.environ.get('REMAKEPATCH_QUIT', '0') == '1'
ROOT = '/Game/GameContents/Renderer'
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RemakeMaterials')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'patch_result.json')
EAL = unreal.EditorAssetLibrary
LIB = getattr(unreal, 'RebirthMaterialDiagnosticsLibrary', None)
results = {'masters': MASTERS, 'steps': [], 'warnings': [], 'renderer': {}, 'character': {}}


def save_results():
    json.dump(results, open(RESULT, 'w'), indent=1)


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('REMAKEPATCH %s: %s' % (key, str(value)[:2000]))
    save_results()


def close_tabs(paths):
    closed = 0
    sub = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
    for path in paths:
        if EAL.does_asset_exist(path):
            asset = unreal.load_asset(path)
            if asset is not None:
                closed += sub.close_all_editors_for_asset(asset)
    return closed


def diagnose(material):
    try:
        d = json.loads(LIB.get_material_diagnostics(material, True))
    except Exception as ex:
        return {'ok': False, 'errors': [str(ex)]}
    errors, ok = [], True
    for key in ('resources', 'material_resources'):
        for r in d.get(key, []) or []:
            errors += r.get('compile_errors', []) or []
            if r.get('has_shader_map') and not r.get('compiled_successfully', True):
                ok = False
    return {'ok': ok and not errors, 'errors': sorted(set(errors))[:12]}


def run():
    if LIB is None or not hasattr(LIB, 'set_material_instance_static_parameters'):
        raise RuntimeError('the RebirthMaterialPreview plugin (set_material_instance_static_parameters) is not loaded')
    start = time.time()
    data = json.load(open(os.path.join(HERE, 'remake_mis.json')))
    renderer = [r for r in data['renderer'] if r['master'] in MASTERS]
    renderer_paths = set(r['path'] for r in renderer)
    character = [c for c in data['character'] if c['parent'] in renderer_paths]
    # (a material editor tab works on its own copy of the master and could write it back over the rebuilt one)
    log('tabs_closed', close_tabs(['%s/Material/%s' % (ROOT, m) for m in MASTERS] + sorted(renderer_paths)))
    # 1. the masters: the full build's code, these masters only, the default textures and functions as they are
    # (the settings are put back afterwards: the editor's Python keeps its environment for the rest of the session)
    settings = {'REMAKEMATERIALS_ONLY': ','.join(MASTERS), 'REMAKEMATERIALS_REUSE': '1', 'REMAKEMATERIALS_QUIT': '0',
                'REMAKEMATERIALS_RESULT': 'patch_build_result.json', 'REMAKEMATERIALS_PERMUTATIONS': '1'}
    before = {k: os.environ.get(k) for k in settings}
    os.environ.update(settings)
    try:
        runpy.run_path(os.path.join(HERE, 'build_remake_materials.py'), run_name='__main__')
    finally:
        for k, v in before.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    build = json.load(open(os.path.join(OUT, 'patch_build_result.json')))
    if not build.get('done'):
        raise RuntimeError('the masters did not build: %s' % str(build.get('error'))[-1200:])
    problems = [k for k, v in build.get('materials', {}).items()
                if v.get('built') == 'FAILED' or not (v.get('compile') or {}).get('ok', True)]
    results['warnings'] += build.get('warnings', [])
    log('masters', '%d rebuilt%s; %s' % (len(build.get('materials', {})), ('; problems: ' + ', '.join(problems)) if problems else '',
                                         build.get('permutations', 'permutations not compiled')))
    # 2. the game's static switches back on the masters' renderer instances (against the rebuilt masters' parameters)
    for r in renderer:
        try:
            mi = unreal.load_asset(r['path']) if EAL.does_asset_exist(r['path']) else None
            if mi is None:
                raise RuntimeError('no ' + r['path'])
            receipt = json.loads(LIB.set_material_instance_static_parameters(
                mi, [s[0] for s in r['switches']], [bool(s[1]) for s in r['switches']], [m[0] for m in r['masks']],
                [m[1] for m in r['masks']], r['blend'], r['shading'], int(r['two_sided']), float(r['clip'])))
            if receipt.get('error'):
                raise RuntimeError(receipt['error'])
            EAL.save_loaded_asset(mi)
            results['renderer'][r['name']] = {'switches': len(r['switches']), 'compile': diagnose(mi)}
        except Exception:
            results['renderer'][r['name']] = {'error': traceback.format_exc()[-1000:]}
        save_results()
    # 3. the character instances under them (Sephiroth's skin, head, hair): compiled as they are
    for c in character:
        mi = unreal.load_asset(c['path']) if EAL.does_asset_exist(c['path']) else None
        results['character'][c['name']] = {'compile': diagnose(mi)} if mi is not None else {'missing': c['path']}
        save_results()
    ok_r = sum(1 for v in results['renderer'].values() if (v.get('compile') or {}).get('ok'))
    ok_c = sum(1 for v in results['character'].values() if (v.get('compile') or {}).get('ok'))
    log('instances', 'renderer %d of %d, character %d of %d compile without errors (%.0f s)' % (
        ok_r, len(renderer), ok_c, len(character), time.time() - start))


try:
    run()
    results['done'] = True
    log('finished', True)
except Exception:
    results['error'] = traceback.format_exc()
    results['done'] = False
    save_results()
    unreal.log_error('REMAKEPATCH failed: ' + results['error'])
finally:
    if QUIT:
        # (quit a few seconds after the script has returned: quitting from inside it crashed the editor on its way out)
        _quit = {'t': 0.0, 'h': None}

        def _quit_later(dt):
            _quit['t'] += dt
            if _quit['t'] > 3.0 and _quit['h'] is not None:
                unreal.unregister_slate_post_tick_callback(_quit['h'])
                _quit['h'] = None
                unreal.SystemLibrary.quit_editor()

        _quit['h'] = unreal.register_slate_post_tick_callback(_quit_later)
