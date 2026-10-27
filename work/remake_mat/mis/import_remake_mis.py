# FF7 Remake's material instances for the End editor, on the rebuilt Remake masters (build_remake_materials.py):
#   /Game/GameContents/Renderer/MaterialInstance/<name>       the game's 385 renderer instances: each master's static
#                                                             permutations (static switches, blend / shading overrides)
#   /Game/GameContents/Character/Enemy/EB0021_0x_.../Material Sephiroth's 21 instances (Standard and Transform), children
#                                                             of those, with their textures
#   their 37 textures, at the game's own paths and names, with the game's texture settings
# from remake_mis.json (read from the game's files). The game's overrides this engine has no setting for (its extra scene
# depth, custom render passes, volumetric lighting modes, vertex modifier, velocity) are listed per instance in the result.
# Run in the End editor: run_import_remake_mis.cmd starts it (UE4Editor.exe -ExecutePythonScript), editor closed.
# Results: Saved\RemakeMaterials\mis_result.json
import json
import os
import re
import time
import traceback
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, 'remake_mis.json')))
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RemakeMaterials')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'mis_result.json')
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
LIB = getattr(unreal, 'RebirthMaterialDiagnosticsLibrary', None)
results = {'steps': [], 'warnings': [], 'textures': {}, 'renderer': {}, 'character': {}}


def save_results():
    json.dump(results, open(RESULT, 'w'), indent=1)


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('REMAKEMIS %s: %s' % (key, str(value)[:2000]))
    save_results()


def warn(text):
    results['warnings'].append(text)
    unreal.log_warning('REMAKEMIS ' + text)
    save_results()


def enum_value(cls_name, name):
    """a UE enum value from its C++ name (TC_Normalmap, TEXTUREGROUP_Character, ...), Python's spelling or not"""
    cls = getattr(unreal, cls_name)
    name = name.split('::')[-1]
    for cand in (name, re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', name).upper(), name.upper()):
        if hasattr(cls, cand):
            return getattr(cls, cand)
    flat = name.replace('_', '').upper()
    for k in dir(cls):
        if k.replace('_', '').upper() == flat:
            return getattr(cls, k)
    raise KeyError('%s.%s' % (cls_name, name))


def setp(obj, prop, value):
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception as ex:
        warn('could not set %s.%s: %s' % (obj.get_name(), prop, ex))
        return False


# ---- textures ------------------------------------------------------------------------------------------------------
def import_file(path, folder, name):
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', path)
    task.set_editor_property('destination_path', folder)
    task.set_editor_property('destination_name', name)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('automated', True)
    task.set_editor_property('save', False)
    AT.import_asset_tasks([task])
    return unreal.load_asset('%s/%s.%s' % (folder, name, name))


def build_texture(t):
    if not os.path.exists(t['png']):
        raise RuntimeError('missing ' + t['png'])
    tex = import_file(t['png'], t['folder'], t['name'])
    if tex is None:
        raise RuntimeError('did not import')
    setp(tex, 'srgb', bool(t['srgb']))
    for key, prop, enum in (('compression', 'compression_settings', 'TextureCompressionSettings'), ('lod_group', 'lod_group', 'TextureGroup'),
                            ('filter', 'filter', 'TextureFilter'), ('address_x', 'address_x', 'TextureAddress'),
                            ('address_y', 'address_y', 'TextureAddress')):
        if t.get(key):
            try:
                setp(tex, prop, enum_value(enum, t[key]))
            except KeyError:
                warn('%s: this engine has no %s %s' % (t['name'], enum, t[key]))
    EAL.save_loaded_asset(tex)
    return '%s %dx%d' % (t['format'], t['size'][0], t['size'][1])


# ---- instances -----------------------------------------------------------------------------------------------------
def instance_for(path):
    folder, name = path.rsplit('/', 1)
    if EAL.does_asset_exist(path):
        a = unreal.load_asset(path)
        if isinstance(a, unreal.MaterialInstanceConstant):
            return a, False
        raise RuntimeError('%s exists and is not a material instance' % path)
    a = AT.create_asset(name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    if a is None:
        raise RuntimeError('could not create ' + path)
    return a, True


def build_instance(item, static):
    parent = unreal.load_asset(item['parent'])
    if parent is None:
        raise RuntimeError('no parent ' + item['parent'])
    mi, new = instance_for(item['path'])
    if not new:
        MEL.clear_all_material_instance_parameters(mi)
    MEL.set_material_instance_parent(mi, parent)
    notes = []
    # (this engine's setters always return False; what the instance then holds is checked instead)
    for n, v in item['scalars']:
        MEL.set_material_instance_scalar_parameter_value(mi, n, float(v))
    for n, v in item['vectors']:
        MEL.set_material_instance_vector_parameter_value(mi, n, unreal.LinearColor(*v))
    for n, p in item['textures']:
        t = unreal.load_asset(p)
        if t is None:
            notes.append('texture %s: no %s' % (n, p))
            continue
        MEL.set_material_instance_texture_parameter_value(mi, n, t)
        got = MEL.get_material_instance_texture_parameter_value(mi, n)
        if got is None or got.get_path_name() != t.get_path_name():
            notes.append('texture %s: the instance holds %s' % (n, got.get_path_name() if got else None))
    out = {'made': 'made' if new else 'remade'}
    if static:
        receipt = LIB.set_material_instance_static_parameters(
            mi, [s[0] for s in item['switches']], [bool(s[1]) for s in item['switches']], [m[0] for m in item['masks']],
            [m[1] for m in item['masks']], item['blend'], item['shading'], int(item['two_sided']), float(item['clip']))
        r = json.loads(receipt)
        if r.get('error'):
            raise RuntimeError(r['error'])
        if r.get('unknown'):
            notes.append('not in the master: ' + ', '.join(r['unknown']))
        out['switches'] = len(item['switches'])
        out['overrides'] = r.get('overrides', [])
        if item.get('dropped'):
            out['not_in_this_engine'] = item['dropped']
    else:
        MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi)
    if notes:
        out['notes'] = notes
    return mi, out


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
        raise RuntimeError('the RebirthMaterialPreview plugin has no set_material_instance_static_parameters: '
                           'run_import_remake_mis.cmd builds it first; was that step skipped or did it fail?')
    for m in sorted(set(r['parent'] for r in DATA['renderer'])):
        if not EAL.does_asset_exist(m):
            raise RuntimeError('no %s: build the Remake masters first (run_build_remake_materials.cmd)' % m)
    start = time.time()
    # 1. textures
    for t in DATA['textures']:
        try:
            results['textures'][t['name']] = build_texture(t)
        except Exception:
            results['textures'][t['name']] = 'FAILED: ' + traceback.format_exc()[-800:]
            warn('texture %s failed' % t['name'])
    log('textures_imported', '%d of %d imported' % (sum(1 for v in results['textures'].values() if not v.startswith('FAILED')), len(DATA['textures'])))
    # 2. the renderer instances Sephiroth's are children of, then his
    first = set(DATA['character_parents'])
    order = [r for r in DATA['renderer'] if r['path'] in first] + [r for r in DATA['renderer'] if r['path'] not in first]
    made = {}
    for item in order[:len(first)]:
        try:
            made[item['path']], results['renderer'][item['name']] = build_instance(item, True)
        except Exception:
            results['renderer'][item['name']] = {'made': 'FAILED', 'error': traceback.format_exc()[-1500:]}
            warn('renderer instance %s failed' % item['name'])
    for item in DATA['character']:
        try:
            made[item['path']], results['character'][item['name']] = build_instance(item, False)
        except Exception:
            results['character'][item['name']] = {'made': 'FAILED', 'error': traceback.format_exc()[-1500:]}
            warn('instance %s failed' % item['name'])
        save_results()
    log('sephiroth_made', '%d of %d instances made (%.0f s)' % (sum(1 for v in results['character'].values() if v['made'] != 'FAILED'),
                                                         len(DATA['character']), time.time() - start))
    # 3. compile Sephiroth's (and their parents) and list any errors
    bad = 0
    for item in order[:len(first)] + DATA['character']:
        mi = made.get(item['path'])
        if mi is None:
            continue
        d = diagnose(mi)
        (results['renderer'] if item in order else results['character'])[item['name']]['compile'] = d
        bad += 0 if d.get('ok') else 1
        save_results()
    log('sephiroth_compiled', '%d of %d without errors (%.0f s)' % (len(first) + len(DATA['character']) - bad,
                                                                  len(first) + len(DATA['character']), time.time() - start))
    # 4. every other renderer instance
    for k, item in enumerate(order[len(first):]):
        try:
            made[item['path']], results['renderer'][item['name']] = build_instance(item, True)
        except Exception:
            results['renderer'][item['name']] = {'made': 'FAILED', 'error': traceback.format_exc()[-1500:]}
            warn('renderer instance %s failed' % item['name'])
        if k % 25 == 0:
            unreal.log('REMAKEMIS renderer instance %d/%d' % (k + 1, len(order) - len(first)))
            save_results()
    log('renderer_made', '%d of %d instances made (%.0f s)' % (sum(1 for v in results['renderer'].values() if v['made'] != 'FAILED'),
                                                        len(DATA['renderer']), time.time() - start))
    if os.environ.get('REMAKEMIS_CHECK_ALL', '0') == '1':
        bad = 0
        for item in order[len(first):]:
            mi = made.get(item['path'])
            if mi is None:
                continue
            d = diagnose(mi)
            results['renderer'][item['name']]['compile'] = d
            bad += 0 if d.get('ok') else 1
        log('renderer_compiled', '%d of %d without errors' % (len(order) - len(first) - bad, len(order) - len(first)))


try:
    run()
    results['done'] = True
    log('finished', True)
except Exception:
    results['error'] = traceback.format_exc()
    results['done'] = False
    save_results()
    unreal.log_error('REMAKEMIS failed: ' + results['error'])
finally:
    if os.environ.get('REMAKEMIS_QUIT', '1') == '1':
        # (quit a few seconds after the script has returned: quitting from inside it crashed the editor on its way out)
        _quit = {'t': 0.0, 'h': None}

        def _quit_later(dt):
            _quit['t'] += dt
            if _quit['t'] > 3.0 and _quit['h'] is not None:
                unreal.unregister_slate_post_tick_callback(_quit['h'])
                _quit['h'] = None
                unreal.SystemLibrary.quit_editor()

        _quit['h'] = unreal.register_slate_post_tick_callback(_quit_later)
