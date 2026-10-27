"""Rebirth FX > Import FF7 Remake Character...: a FINAL FANTASY VII REMAKE character into this project.

The menu entry starts the Remake Importer (Tools/RemakeImporter/remake_importer.py) with your own Python 3 (py -3). Its
window asks for the Remake folder and your AES key (kept in that program's memory for its run only: this editor never
sees it) and lets you pick a character; it extracts the character's packages, converts them (textures to PNG/EXR, its
material instances to the material data, its models to FBX, its Bonamik) and writes a job. This editor waits for the
job without blocking (a Slate tick looks every half second), then runs Tools/RemakeMaterials/remake_character.py on it
(textures, instances, models, Bonamik), puts the game's instances on the material slots whose names differ from their
instances' names, and shows a summary.

Python:  import rebirth_fx.remake_import as ri
         ri.menu()                                      what the menu entry does
         ri.run_job(r'C:/FF7R2UProj/Saved/RemakeImporter/PC0002_00_Tifa_Standard/remake_tifa_job.json')   a job made before
"""
import importlib
import json
import os
import shutil
import subprocess
import sys
import time
import traceback

import unreal

TOOL = 'Import FF7 Remake Character'
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_CONSOLE = 0x00000010
_state = {'proc': None, 'result': None, 'log': None, 'tick': None, 'next': 0.0, 'busy': False, 'started': 0.0}


def _log(text):
    unreal.log('[%s] %s' % (TOOL, text.replace('\n', ' | ')))


def _message(text, title=TOOL):
    _log(text)
    try:
        unreal.EditorDialog.show_message(title, text, unreal.AppMsgType.OK)
    except Exception:
        pass


def _project():
    return os.path.normpath(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))


def _saved():
    path = os.path.join(os.path.normpath(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())), 'RemakeImporter')
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def _helper():
    return os.path.join(_project(), 'Tools', 'RemakeImporter', 'remake_importer.py')


def _python():
    """Your own Python 3 (the py launcher, else python on the PATH): never this editor's embedded Python."""
    py = shutil.which('py')
    if py:
        return [py, '-3']
    for name in ('python3', 'python'):
        p = shutil.which(name)
        if p and 'windowsapps' not in p.lower():
            return [p]
    return None


def _has_tkinter(py):
    try:
        return subprocess.run(py + ['-c', 'import tkinter'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              creationflags=CREATE_NO_WINDOW, timeout=60).returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------------------------------------------------
# the menu entry: start the importer, wait for its job
# ---------------------------------------------------------------------------------------------------------------------

def menu():
    try:
        p = _state['proc']
        if p is not None and p.poll() is None:
            _message('The Remake Importer is already open (its window may be behind this one).')
            return
        if _state['busy']:
            _message('A Remake character is being imported right now.')
            return
        helper = _helper()
        if not os.path.isfile(helper):
            _message('The Remake Importer is not there:\n%s' % helper)
            return
        py = _python()
        if py is None:
            _message('The Remake Importer runs with your own Python 3, and none was found (no "py" and no "python" on the '
                     'PATH).\n\nInstall Python 3 from python.org (with the py launcher, and tcl/tk for its window), then '
                     'try again.')
            return
        saved = _saved()
        stamp = time.strftime('%Y%m%d_%H%M%S')
        result = os.path.join(saved, 'result_%s.json' % stamp)
        window = _has_tkinter(py)
        args = py + [helper, '--project', _project(), '--result', result]
        if window:
            log_path = os.path.join(saved, 'importer_log_%s.txt' % stamp)
            log = open(log_path, 'w')
            proc = subprocess.Popen(args, cwd=os.path.dirname(helper), stdin=subprocess.DEVNULL, stdout=log,
                                    stderr=subprocess.STDOUT, creationflags=CREATE_NO_WINDOW)
            log.close()
        else:
            log_path = None             # (its console window shows everything)
            proc = subprocess.Popen(args + ['--console'], cwd=os.path.dirname(helper), creationflags=CREATE_NEW_CONSOLE)
        _state.update(proc=proc, result=result, log=log_path, next=time.time() + 1.0, started=time.time())
        if _state['tick'] is None:
            _state['tick'] = unreal.register_slate_post_tick_callback(_tick)
        _log('the Remake Importer is open (%s, %s): this editor imports the character once it has made the job' % (
            ' '.join(py), 'window' if window else 'console'))
    except Exception:
        _message('The Remake Importer did not start:\n' + traceback.format_exc())


def _tick(delta):
    if _state['busy'] or _state['result'] is None:
        return
    now = time.time()
    if now < _state['next']:
        return
    _state['next'] = now + 0.5
    result = _state['result']
    if os.path.isfile(result):
        try:
            with open(result, encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return                      # (being written: next time)
        _state['result'] = None
        _state['busy'] = True           # (dialogs and imports tick Slate again: nothing runs twice)
        try:
            _handle(data)
        except Exception:
            _message('Importing the Remake character failed:\n' + traceback.format_exc())
        finally:
            _state['busy'] = False
        return
    p = _state['proc']
    if p is not None and p.poll() is not None:
        _state['result'] = None
        where = ('\nIts log: %s' % _state['log']) if _state['log'] else ''
        _message('The Remake Importer closed without making a job (exit code %s).%s' % (p.returncode, where))


def _handle(data):
    if not data.get('ok'):
        if data.get('cancelled'):
            _log('the Remake Importer was closed: nothing to import')
        else:
            _message('The Remake Importer stopped: %s' % (data.get('error') or 'no job was made'))
        return
    run_job(data['job'], data.get('summary'))


# ---------------------------------------------------------------------------------------------------------------------
# the import (remake_character.py)
# ---------------------------------------------------------------------------------------------------------------------

def _remake_character():
    folder = os.path.join(_project(), 'Tools', 'RemakeMaterials')
    if folder not in sys.path:
        sys.path.insert(0, folder)
    import remake_character
    importlib.reload(remake_character)
    return remake_character


def _assign_slots(spec):
    """The game's instance on each material slot whose name is not its instance's (remake_character.py looks slots up
    by name in the model's Material folder)."""
    eal = unreal.EditorAssetLibrary
    done, missing = [], []
    for m in spec.get('models', []):
        want = dict((s, p) for s, p in m.get('slots') or [])
        if not want:
            continue
        path = '%s/%s' % (m['folder'], m['name'])
        sm = unreal.load_asset(path) if eal.does_asset_exist(path) else None
        if not isinstance(sm, unreal.SkeletalMesh):
            continue
        mats = sm.get_editor_property('materials')
        changed = False
        for i in range(len(mats)):
            slot = mats[i]                                  # (a copy: change it, then put it back)
            name = str(slot.get_editor_property('material_slot_name'))
            if name not in want:
                continue
            mi = unreal.load_asset(want[name]) if eal.does_asset_exist(want[name]) else None
            if mi is None:
                missing.append('%s: %s' % (name, want[name]))
                continue
            slot.set_editor_property('material_interface', mi)
            mats[i] = slot
            changed = True
            done.append('%s.%s <- %s' % (m['name'], name, want[name].rsplit('/', 1)[-1]))
        if changed:
            sm.set_editor_property('materials', mats)
            eal.save_loaded_asset(sm)
    return done, missing


def run_job(job_path, conversion=None):
    """Runs remake_character.py on a job (every step), assigns the remapped slots and shows what was imported."""
    job_path = os.path.normpath(job_path)
    with open(job_path, encoding='utf-8') as f:
        spec = json.load(f)
    name = spec.get('name', os.path.basename(job_path))
    rc = _remake_character()
    said = {}
    t0 = time.time()
    with unreal.ScopedSlowTask(len(rc.STEPS) + 1, 'Importing %s' % name) as task:
        task.make_dialog(False)
        for step in rc.STEPS:
            task.enter_progress_frame(1, 'Importing %s: %s' % (name, step))
            said.update(rc.run(job_path, steps=[step]))
        task.enter_progress_frame(1, 'Importing %s: material slots' % name)
        try:
            slots, slots_missing = _assign_slots(spec)
        except Exception:
            slots, slots_missing = [], ['the slots were not assigned: ' + traceback.format_exc()[-400:]]
    result_file = os.path.join(rc.OUT, name.replace(' ', '_') + '_result.json')
    try:
        with open(result_file, encoding='utf-8') as f:
            results = json.load(f)
    except Exception:
        results = {}
    lines = ['%s (%.0f s)' % (name, time.time() - t0), spec.get('source', '')]
    for step in rc.STEPS:
        lines.append('  %-9s  %s' % (step, str(said.get(step, '-')).splitlines()[0][:300]))
    models = results.get('models', {})
    for m in spec.get('models', []):
        r = models.get(m['name'], {})
        if 'error' in r:
            lines.append('  model %s FAILED (see the result file)' % m['name'])
            continue
        remapped = set(s for s, p in m.get('slots') or [])
        still = [s for s in r.get('materials_missing', []) if s not in remapped]
        if still:
            lines.append('  %s: no material for slot%s %s' % (m['name'], '' if len(still) == 1 else 's', ', '.join(still)))
        if r.get('skeleton'):
            lines.append('  %s: %s bones, on %s' % (m['name'], r.get('bones'), r['skeleton'].split('.')[0]))
    if slots:
        lines.append('  slots named differently from their instances, assigned: ' + '; '.join(slots))
    if slots_missing:
        lines.append('  slots not assigned: ' + '; '.join(slots_missing))
    for k, v in (results.get('instances') or {}).items():
        if v.get('made') == 'FAILED':
            lines.append('  instance %s FAILED' % k)
        elif (v.get('compile') or {}).get('ok') is False:
            lines.append('  instance %s does not compile: %s' % (k, '; '.join((v['compile'].get('errors') or [])[:2])))
    notes = (spec.get('importer') or {}).get('warnings') or []
    if notes:
        lines.append('From the conversion:')
        lines += ['  ' + n for n in notes[:12]] + (['  ... %d more (the job file lists them)' % (len(notes) - 12)] if len(notes) > 12 else [])
    lines.append('Results: %s' % result_file)
    lines.append('Job: %s' % job_path)
    text = '\n'.join(lines)
    try:
        folder = spec['models'][0]['folder'].rsplit('/', 1)[0] if spec.get('models') else None
        if folder:
            unreal.EditorAssetLibrary.sync_browser_to_objects([folder])
    except Exception:
        pass
    _message(text, TOOL + ': done')
    return dict(said=said, slots=slots, slots_missing=slots_missing, text=text)


def add_menu_entries(menu_object, section='Tools'):
    entry = unreal.ToolMenuEntry(name='RebirthRemakeImport', type=unreal.MultiBlockType.MENU_ENTRY)
    entry.set_label('Import FF7 Remake Character...')
    entry.set_tool_tip('Pick a FINAL FANTASY VII REMAKE character (your Remake install and your AES key, asked for by the '
                       'Remake Importer window): its textures, material instances, models and Bonamik come into this project')
    entry.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, '', 'import rebirth_fx.remake_import as ri; ri.menu()')
    menu_object.add_menu_entry(section, entry)
