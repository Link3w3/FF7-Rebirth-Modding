"""Rebirth Materials: the End editor's tools for FINAL FANTASY VII REBIRTH material instances, in the Rebirth FX menu.

  Open Game Material...            one of the game's material instances becomes an editable Material Instance in
                                   /Game/RebirthMat/<name> (its parent, values and textures; the Material Instance Editor)
  Materials On My Character...     the same, picked from what the character you play wears right now (game running)
  Material Live Edits On/Off       while on, value and texture changes go to the running game as you make them
  Reset Materials In Game          the character's materials back as the game had them
  Export Materials To Game         every changed material into one mod, RebirthMat_P, installed in ~mods

Python: import rebirth_fx.materials as mats; mats.open_material('/Game/Character/Player/PC0000_00_Cloud_Standard/Material/PC0000_00_TopsA')
"""
import json, os, time, traceback

import unreal

from . import fxcore, livelink, matcore

ROOT = '/Game/RebirthMat'
MOD_NAME = 'RebirthMat_P'
_state = {'current': None, 'live': False, 'tick': None, 'pushed': {}, 'next_check': 0.0}
MEL = unreal.MaterialEditingLibrary


def _saved_dir():
    return os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'RebirthMat')


def _message(text, title='Rebirth Materials'):
    unreal.log('[Rebirth Materials] ' + text.replace('\n', ' | '))
    try:
        unreal.EditorDialog.show_message(title, text, unreal.AppMsgType.OK)
    except Exception:
        pass


def _paks():
    return unreal.RebirthFxLibrary.get_game_paks_directory()


def _short(package_name):
    return package_name.rsplit('/', 1)[-1].split('.')[0]


def _package_of(object_path):
    return object_path.split('.', 1)[0]


def _manifest_path(short):
    return os.path.join(_saved_dir(), short, 'manifest.json')


def _load_manifest(short):
    try:
        return json.load(open(_manifest_path(short), encoding='utf-8'))
    except Exception:
        return None


def _workspaces():
    d = _saved_dir()
    if not os.path.isdir(d):
        return []
    out = []
    for name in sorted(os.listdir(d)):
        m = _load_manifest(name)
        if m:
            out.append(m)
    return out


def _game_package(package_name, work):
    """(bytes, header file, container) of a game package, saved into `work`."""
    if not os.path.isdir(work):
        os.makedirs(work)
    short = _short(package_name)
    path = os.path.join(work, short + '.uasset')
    err = unreal.RebirthFxLibrary.save_game_package_to_file(package_name, path)
    if err:
        raise RuntimeError(err)
    header = os.path.join(work, short + '.container_header.bin')
    result = unreal.RebirthFxLibrary.save_game_container_header_to_file(package_name, header)
    err, container = (result if isinstance(result, tuple) else (result, ''))
    if err:
        raise RuntimeError(err)
    return open(path, 'rb').read(), header, container, path


def _editor_parent(mi, work):
    """The nearest material up the game's parent chain that the editor can load (the game's RMI_* instances are not all in
    the project; the base materials are). Returns (asset, [chain of game paths])."""
    chain = []
    parent = mi.parent
    for _ in range(6):
        if not parent or parent in chain:
            break
        chain.append(parent)
        asset = unreal.load_asset(parent.split('.')[0])
        if asset is not None:
            return asset, chain
        try:
            data, _, _, _ = _game_package(_package_of(parent), os.path.join(work, 'parents'))
            parent = matcore.MaterialInstance(data, _short(parent)).parent
        except Exception:
            break
    return None, chain


def _texture_asset(object_path):
    if not object_path:
        return None
    try:
        return unreal.load_asset(object_path.split('.')[0])
    except Exception:
        return None


def _param_names(material):
    """{'scalar': [...], 'vector': [...], 'texture': [...]} of a material (what its instances can set)."""
    out = {'scalar': [], 'vector': [], 'texture': []}
    for kind, fn in (('scalar', 'get_scalar_parameter_names'), ('vector', 'get_vector_parameter_names'),
                     ('texture', 'get_texture_parameter_names')):
        try:
            out[kind] = [str(n) for n in getattr(MEL, fn)(material)]
        except Exception:
            pass
    return out


def _read_values(mic, names):
    vals = {}
    for n in names.get('scalar', []):
        try:
            vals['scalar:' + n] = float(MEL.get_material_instance_scalar_parameter_value(mic, n))
        except Exception:
            pass
    for n in names.get('vector', []):
        try:
            c = MEL.get_material_instance_vector_parameter_value(mic, n)
            vals['vector:' + n] = [c.r, c.g, c.b, c.a]
        except Exception:
            pass
    for n in names.get('texture', []):
        try:
            t = MEL.get_material_instance_texture_parameter_value(mic, n)
            vals['texture:' + n] = t.get_path_name() if t is not None else ''
        except Exception:
            pass
    return vals


def _same(a, b):
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(abs(x - y) < 1e-6 for x, y in zip(a, b))
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) < 1e-6
    return a == b


# ---------------------------------------------------------------------------------------------------------------------
# open
# ---------------------------------------------------------------------------------------------------------------------

def _looks_like_material(name):
    short = name.rsplit('/', 1)[-1]
    return ('/Material/' in name or '/MaterialInstance/' in name or short.startswith(('MI_', 'RMI_', 'M_', 'RM_', 'MID_')))


def open_material_menu():
    try:
        names = [n for n in unreal.RebirthFxLibrary.find_game_packages_matching('/Game/', 200000) if _looks_like_material(n)]
        if not names:
            _message('The game\'s packages were not found. Is FINAL FANTASY VII REBIRTH installed, and is its folder known to the '
                     'Rebirth tools?')
            return None
        current = _state['current']
        choice = unreal.RebirthFxLibrary.pick_from_list('Open Game Material', 'Type part of a name (for example PC0000_00, '
                                                        'TopsA, RMI_Surface). Double-click or Open to edit it.', names,
                                                        _short(current) if current else 'PC0000_00')
        if not choice:
            return None
        return open_material(choice)
    except Exception:
        _message('Opening the material failed:\n' + traceback.format_exc())
        return None


def open_material(package_name, reopen=False):
    """Brings a game material instance into /Game/RebirthMat/<name> as an editable Material Instance. Returns the manifest."""
    short = _short(package_name)
    work = os.path.join(_saved_dir(), short)
    folder = ROOT + '/' + short
    asset_path = folder + '/' + short
    existing = _load_manifest(short)
    if existing and not reopen and unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        _state['current'] = package_name
        unreal.EditorAssetLibrary.sync_browser_to_objects([asset_path])
        _message('%s is already open as %s (it keeps your edits).\nDouble-click it to edit; Rebirth FX > Export Materials To '
                 'Game puts it in the game.' % (short, asset_path))
        return existing
    data, header, container, original = _game_package(package_name, work)
    mi = matcore.MaterialInstance(data, short)
    parent, chain = _editor_parent(mi, work)
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        mic = unreal.load_asset(asset_path)
    else:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        mic = tools.create_asset(short, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    if mic is None:
        raise RuntimeError('could not make ' + asset_path)
    if parent is not None:
        MEL.set_material_instance_parent(mic, parent)
    missing = []
    for p in mi.params:
        try:
            if p['kind'] == 'scalar':
                MEL.set_material_instance_scalar_parameter_value(mic, p['name'], float(p['value']))
            elif p['kind'] == 'vector':
                v = p['value']
                MEL.set_material_instance_vector_parameter_value(mic, p['name'], unreal.LinearColor(v[0], v[1], v[2], v[3]))
            elif p['kind'] == 'texture':
                t = _texture_asset(p['value'])
                if t is not None:
                    MEL.set_material_instance_texture_parameter_value(mic, p['name'], t)
                else:
                    missing.append(p['value'])
        except Exception:
            missing.append('%s (%s)' % (p['name'], p['kind']))
    try:
        MEL.update_material_instance(mic)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
    names = _param_names(mic)
    for p in mi.params:                       # the game's own overrides are always tracked
        if p['name'] not in names[p['kind']]:
            names[p['kind']].append(p['name'])
    baseline = _read_values(mic, names)
    # textures the editor does not have: the game's paths are the baseline (the editor's instance shows none there)
    absent = []
    for p in mi.params:
        if p['kind'] == 'texture' and p['value'] and _texture_asset(p['value']) is None:
            baseline['texture:' + p['name']] = p['value']
            absent.append(p['name'])
    manifest = dict(package=package_name, short=short, folder=folder, asset=asset_path, original=original, header=header,
                    container=container, parent=mi.parent, editor_parent=parent.get_path_name() if parent else None,
                    chain=chain, names=names, baseline=baseline, absent_textures=absent,
                    game=dict(params=mi.params, static_switches=mi.static_switches, static_permutation=mi.has_static_permutation))
    json.dump(manifest, open(_manifest_path(short), 'w', encoding='utf-8'), indent=1)
    _state['current'] = package_name
    _state['pushed'][short] = dict(baseline)
    unreal.EditorAssetLibrary.sync_browser_to_objects([asset_path])
    lines = ['%s is open as %s.' % (short, asset_path), '',
             'In the game its parent is %s.' % (mi.parent or 'none')]
    if parent is None:
        lines.append('The editor has none of its parents, so it shows no preview; values and textures still export.')
    elif chain and parent.get_path_name().split('.')[0] != chain[0].split('.')[0]:
        lines.append('The editor previews it on %s (the nearest parent it has).' % parent.get_path_name().split('.')[0])
    if missing:
        lines.append('Not in the project (kept as the game has them): ' + ', '.join(sorted(set(m.rsplit('.', 1)[-1] for m in missing))))
    lines += ['', 'Double-click it and change values or textures. Material Live Edits shows them in the running game; Export '
              'Materials To Game makes the mod.']
    _message('\n'.join(lines))
    return manifest


def materials_on_character():
    """Menu: what the character you play wears in the running game; pick one to open it."""
    try:
        paks = _paks()
        if not livelink.installed(paks):
            _message('The RebirthLiveLink mod is not in the game (ue4ss\\Mods\\RebirthLiveLink).')
            return None
        s = livelink.wait(paks, livelink.send(paks, 'materials'), 5.0)
        if s is None:
            _message('The game did not answer. Is it running, past the title screen, with the RebirthLiveLink mod?')
            return None
        r = s.get('result', {})
        if not r.get('ok'):
            _message('The game: %s' % r.get('error'))
            return None
        items, by_item = [], {}
        for comp in r.get('components', []):
            mesh = (comp.get('mesh') or '').split('.')[-1]
            for slot in comp.get('slots', []):
                chain = [c.split(' ', 1)[-1] for c in slot.get('chain', [])]
                # the first material in the chain that is an asset (not a dynamic instance)
                asset = next((c for c in chain if c.startswith('/Game/') and ':' not in c), None)
                if not asset:
                    continue
                label = '%s  [%s slot %d]' % (asset.split('.')[0], mesh, slot.get('slot', 0))
                items.append(label)
                by_item[label] = asset.split('.')[0]
        if not items:
            _message('The game lists no materials on your character.')
            return None
        choice = unreal.RebirthFxLibrary.pick_from_list('Materials On My Character', 'What %s wears now. Pick one to edit it.'
                                                        % (r.get('character') or 'your character').split('.')[-1], items, '')
        if not choice:
            return None
        return open_material(by_item[choice])
    except Exception:
        _message('Listing the character\'s materials failed:\n' + traceback.format_exc())
        return None


# ---------------------------------------------------------------------------------------------------------------------
# changes
# ---------------------------------------------------------------------------------------------------------------------

def _current(m):
    mic = unreal.load_asset(m['asset'])
    if mic is None:
        return None
    vals = _read_values(mic, m['names'])
    absent = set(m.get('absent_textures', []))
    for key, base in m['baseline'].items():
        if not key.startswith('texture:'):
            continue
        # a game texture the editor does not have stays as the game has it until you put another texture there
        if key not in vals or (key[len('texture:'):] in absent and not vals[key]):
            vals[key] = base
    return vals


def _changes(m, vals=None):
    """[dict(kind, name, value)] where the editor's instance differs from the game's material."""
    vals = vals if vals is not None else _current(m)
    if vals is None:
        return []
    out = []
    for key, v in vals.items():
        base = m['baseline'].get(key)
        if base is None or _same(v, base):
            continue
        kind, name = key.split(':', 1)
        if kind == 'texture':
            v = _game_texture_path(v)
            if v is None:
                continue
        out.append(dict(kind=kind, name=name, value=v))
    return out


def _game_texture_path(path):
    """A texture's object path as the game knows it ('/Game/A/B.B'), or None for one the game cannot have."""
    if not path:
        return ''
    if not path.startswith('/Game/'):
        return None
    pkg = path.split('.')[0]
    return pkg + '.' + pkg.rsplit('/', 1)[-1]


def _live_tick(delta):
    if not _state['live']:
        return
    now = time.time()
    if now < _state['next_check']:
        return
    _state['next_check'] = now + 0.5
    try:
        paks = _paks()
        for m in _workspaces():
            vals = _current(m)
            if vals is None:
                continue
            last = _state['pushed'].setdefault(m['short'], dict(m['baseline']))
            params = []
            for key, v in vals.items():
                if key in last and _same(v, last[key]):
                    continue
                last[key] = v
                kind, name = key.split(':', 1)
                if kind == 'texture':
                    v = _game_texture_path(v)
                    if v is None:
                        continue
                params.append(dict(type=kind, name=name, value=v))
            if params:
                livelink.send(paks, 'material_params', path=m['package'], params=params)
                return     # one command per tick: the game runs the newest
    except Exception:
        unreal.log_warning('[Rebirth Materials] live edit: ' + traceback.format_exc())


def toggle_live():
    _state['live'] = not _state['live']
    if _state['live'] and _state['tick'] is None:
        _state['tick'] = unreal.register_slate_post_tick_callback(_live_tick)
    if not _state['live']:
        _message('Material live edits are off.')
        return
    # what the game shows now is the game's own material: start from the baselines
    for m in _workspaces():
        _state['pushed'][m['short']] = dict(m['baseline'])
    _message('Material live edits are ON: value and texture changes on the materials you opened go to the character you play '
             '(every slot that wears them) as you make them.\nReset Materials In Game puts the game\'s own back.')


def reset_in_game():
    try:
        paks = _paks()
        s = livelink.wait(paks, livelink.send(paks, 'reset_materials'), 4.0)
        for m in _workspaces():
            _state['pushed'][m['short']] = dict(m['baseline'])
        if s is None:
            _message('The game did not answer.')
        else:
            _message('The game: %d slots back to their own material.' % s.get('result', {}).get('reset', 0))
    except Exception:
        _message('Reset failed:\n' + traceback.format_exc())


# ---------------------------------------------------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------------------------------------------------

def export_to_game(install=True):
    """Every opened material with changes into one mod (RebirthMat_P), written to Saved/RebirthMat/Mod and copied to ~mods."""
    try:
        packages, headers, report = [], [], []
        for m in _workspaces():
            changes = _changes(m)
            if not changes:
                continue
            mi = matcore.MaterialInstance(open(m['original'], 'rb').read(), m['short'])
            data, lines = matcore.edit(mi, changes)
            check = matcore.MaterialInstance(data, m['short'])
            if check.pkg.errors:
                raise RuntimeError('%s no longer reads back: %s' % (m['short'], check.pkg.errors))
            packages.append(data)
            headers.append(open(m['header'], 'rb').read())
            report.append('%s: %s' % (m['short'], '; '.join(lines)))
        if not packages:
            _message('Nothing to export: no opened material has changes.')
            return None
        out = os.path.join(_saved_dir(), 'Mod')
        files = fxcore.build_mod(packages, headers, out, MOD_NAME)
        where = out
        if install:
            paks = _paks()
            mods = os.path.join(paks, '~mods') if paks else None
            if mods and os.path.isdir(mods):
                try:
                    import shutil
                    for f in files:
                        shutil.copy(f, os.path.join(mods, os.path.basename(f)))
                    where = mods
                except Exception as ex:
                    _message('The mod is built in %s but could not be copied to %s (%s).\nClose the game and export again.' % (out, mods, ex))
                    return files
        _message('%s is in %s:\n%s\n\nRestart the game to see it.' % (MOD_NAME, where, '\n'.join(report)))
        return files
    except Exception:
        _message('Exporting failed:\n' + traceback.format_exc())
        return None


# ---------------------------------------------------------------------------------------------------------------------
# menu (in the Rebirth FX menu)
# ---------------------------------------------------------------------------------------------------------------------

def add_menu_entries(sub):
    def entry(name, label, tip, command):
        e = unreal.ToolMenuEntry(name=name, type=unreal.MultiBlockType.MENU_ENTRY)
        e.set_label(label)
        e.set_tool_tip(tip)
        e.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, '', command)
        sub.add_menu_entry('Materials', e)

    entry('RebirthMatOpen', 'Open Game Material...', 'Pick one of the game\'s material instances: it becomes a Material Instance you can edit',
          'import rebirth_fx.materials as m; m.open_material_menu()')
    entry('RebirthMatCharacter', 'Materials On My Character...', 'What the character you play wears in the running game; pick one to edit it',
          'import rebirth_fx.materials as m; m.materials_on_character()')
    entry('RebirthMatLive', 'Material Live Edits On/Off', 'While on, material changes go to the running game as you make them',
          'import rebirth_fx.materials as m; m.toggle_live()')
    entry('RebirthMatReset', 'Reset Materials In Game', 'The character\'s materials back as the game had them',
          'import rebirth_fx.materials as m; m.reset_in_game()')
    entry('RebirthMatExport', 'Export Materials To Game', 'Every changed material into the RebirthMat_P mod in ~mods',
          'import rebirth_fx.materials as m; m.export_to_game()')
