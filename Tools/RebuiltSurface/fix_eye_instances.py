# Eye fix (RM_Surface rebuilt): the editable eye material instances (their parent chain goes through one of the game's
# RMI_Surface_Eye_* instances) get the game's shared eye textures in the slots they left empty, as the game's own eye
# instances have them (PC0010_00_Eye_Large: Color, GazeNormal, Normal, ScrelaNormal):
#   Color <- Common_Eye_Player_C, GazeNormal <- Common_Eye_Player_NG, Normal <- Common_Eye_Player_NO,
#   ScrelaNormal <- Common_Eye_Player_NI      (/Game/Character/Common/Eye/Texture)
# An empty slot falls back to RMI_Surface_Eye_*'s generic textures; with a flat gaze normal the iris parallax pushes the
# iris off the front of the eye. Slots that already have a texture are left as they are.
# Run by fix_eyes.cmd (UE4Editor.exe -ExecutePythonScript). Result: Saved\RebirthSkelCompat\EyeFix\result.json
import json, os, traceback
import unreal

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
CONTENT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'EyeFix')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'result.json')
EYE = '/Game/Character/Common/Eye/Texture/'
FILL = {'Color': 'Common_Eye_Player_C', 'GazeNormal': 'Common_Eye_Player_NG', 'Normal': 'Common_Eye_Player_NO',
        'ScrelaNormal': 'Common_Eye_Player_NI'}
results = {'fixed': [], 'checked': 0, 'warnings': []}


def save():
    json.dump(results, open(RESULT, 'w'), indent=1)


def disk(package):
    return os.path.join(CONTENT, *package.split('/')[2:])


def editable(package):
    p = disk(package)
    return os.path.exists(p + '.uasset') and not os.path.exists(p + '.uexp')


def eye_parent(mi):
    cur = mi
    for _ in range(16):
        parent = cur.get_editor_property('parent')
        if parent is None:
            return None
        name = parent.get_name()
        if name.startswith('RMI_Surface_Eye'):
            return name
        if not isinstance(parent, unreal.MaterialInstance):
            return None
        cur = parent
    return None


def run():
    textures = {}
    for slot, name in FILL.items():
        t = unreal.load_asset(EYE + name)
        if t is None:
            raise RuntimeError('missing %s%s: fix_eyes.cmd copies the game textures there first' % (EYE, name))
        textures[slot] = t
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    ar.search_all_assets(True)
    assets = ar.get_assets_by_class('MaterialInstanceConstant', True)
    for a in assets:
        package = str(a.package_name)
        if not package.startswith('/Game/') or not editable(package):
            continue
        mi = unreal.load_asset(str(a.object_path))
        if mi is None:
            continue
        results['checked'] += 1
        parent = eye_parent(mi)
        if parent is None:
            continue
        filled = []
        for tp in mi.get_editor_property('texture_parameter_values'):
            slot = str(tp.get_editor_property('parameter_info').get_editor_property('name'))
            if slot in textures and tp.get_editor_property('parameter_value') is None:
                if MEL.set_material_instance_texture_parameter_value(mi, slot, textures[slot]):
                    filled.append(slot)
                else:
                    results['warnings'].append('%s: could not set %s' % (package, slot))
        if filled:
            MEL.update_material_instance(mi)
            EAL.save_loaded_asset(mi)
            results['fixed'].append({'instance': package, 'eye_parent': parent, 'filled': filled})
            unreal.log('EYEFIX %s: %s' % (package, ', '.join(filled)))
        save()


try:
    run()
    results['done'] = True
except Exception:
    results['error'] = traceback.format_exc()
    results['done'] = False
    unreal.log_error('EYEFIX failed: ' + results['error'])
finally:
    save()
    if os.environ.get('EYEFIX_QUIT', '1') == '1':
        _quit = {'t': 0.0, 'h': None}

        def _quit_later(dt):
            _quit['t'] += dt
            if _quit['t'] > 3.0 and _quit['h'] is not None:
                unreal.unregister_slate_post_tick_callback(_quit['h'])
                _quit['h'] = None
                unreal.SystemLibrary.quit_editor()

        _quit['h'] = unreal.register_slate_post_tick_callback(_quit_later)
