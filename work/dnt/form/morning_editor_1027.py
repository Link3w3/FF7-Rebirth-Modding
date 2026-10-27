"""The open End editor's part of the night's work, in one go (Output Log, Cmd:
    py "C:/FF7R2UProj/Tools/Dissidia/morning_editor_1027.py"
with the game closed: the skin builds put the skins into the game):

  1. Dissidia NT Sephiroth (Tools/Dissidia/pipeline/dnt_import.py): his nine outfits' textures, material instances and
     models, eighteen skins built and installed, his KawaiiPhysics file into the game;
  2. Crisis Core's Masamune (Tools/CrisisCore/masamune/cc_masamune.py): its textures, material instance and model, then
     the CRISIS CORE skins get it as their weapon and are built and installed again.

Each part writes its own result file (Saved/ModExtract/dnt/dnt_import_result.json,
Saved/ModExtract/cc16/masamune/cc_masamune_result.json); this one writes Saved/ModExtract/morning_1027.json.
Run it again to redo what failed (what was made is kept)."""
import importlib.util
import json
import os
import time
import traceback

import unreal

PROJECT = os.path.dirname(os.path.normpath(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())))
SAVED = os.path.normpath(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()))
PARTS = [('dissidia', os.path.join(PROJECT, 'Tools', 'Dissidia', 'pipeline', 'dnt_import.py'), 'dnt_import'),
         ('crisis_core_masamune', os.path.join(PROJECT, 'Tools', 'CrisisCore', 'masamune', 'cc_masamune.py'), 'cc_masamune')]
RESULT = os.path.join(SAVED, 'ModExtract', 'morning_1027.json')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LISTS = ('errors', 'notes', 'failed', 'not_set', 'materials_missing')   # (what went wrong or is worth a look, as lists)


def problems(value, where='', found=None):
    """what went wrong in a part's result (its errors, notes, failed textures and parameters, missing materials, builds
    that did not work), as 'where: what' lines for the one-page result"""
    found = [] if found is None else found
    if isinstance(value, dict):
        for k, v in value.items():
            here = '%s/%s' % (where, k) if where else str(k)
            if k == 'error' and v:
                found.append('%s: %s' % (where or 'error', str(v)[-400:]))
            elif k in LISTS and isinstance(v, list) and v:
                found.append('%s: %s' % (here, '; '.join(str(x)[-300:] for x in v)[-1200:]))
            elif k == 'ok' and v is False:
                found.append('%s: FAILED' % (where or 'ok'))
            elif k == 'built' and v is False:
                found.append('%s: NOT BUILT' % (where or 'built'))
            elif isinstance(v, (dict, list)):
                problems(v, here, found)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            if isinstance(v, (dict, list)):
                label = v.get('skin') if isinstance(v, dict) and v.get('skin') else str(i)
                problems(v, '%s[%s]' % (where, label), found)
    return found


def run():
    os.makedirs(os.path.dirname(RESULT), exist_ok=True)
    out = {'started': time.strftime('%Y-%m-%d %H:%M:%S')}
    for key, path, name in PARTS:
        started = time.time()
        unreal.log('MORNING 1027: %s (%s)' % (key, path))
        try:
            module = load(path, name)
            result = module.run()
            found = problems(result)
            out[key] = {'seconds': round(time.time() - started), 'problems': found or 'none'}
            unreal.log('MORNING 1027: %s done, %s' % (key, ('%d problem(s), see %s' % (len(found), RESULT)) if found else 'no problems'))
        except Exception:
            out[key] = {'error': traceback.format_exc()[-1500:]}
            unreal.log_error('MORNING 1027: %s FAILED: %s' % (key, out[key]['error'][-300:]))
        with open(RESULT, 'w') as f:
            json.dump(out, f, indent=1)
    out['finished'] = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(RESULT, 'w') as f:
        json.dump(out, f, indent=1)
    unreal.log('MORNING 1027 done: ' + RESULT)
    return out


run()
