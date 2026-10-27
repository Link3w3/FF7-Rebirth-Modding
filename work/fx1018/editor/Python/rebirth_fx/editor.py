"""Rebirth FX: the End editor's menu for FINAL FANTASY VII REBIRTH effects (and the live link to the running game).

  Rebirth FX > Open Game Effect...        pick one of the game's effects; its colour and float curves become Curve assets
                                          in /Game/RebirthFx/<effect> (gradient view, colour pickers, Hue/Saturation/
                                          Brightness adjustments, the curve editor)
  Rebirth FX > Recolour Effect...         every colour curve of the open effect to a hue (keeps brightness and saturation)
  Rebirth FX > Play Effect In Game        the running game plays it in front of your character, again every few seconds
  Rebirth FX > Live Edits On/Off          while on, curve changes go to the running game as you make them
  Rebirth FX > Export Effects To Game     every changed effect into one mod, RebirthFx_P, installed in ~mods
Python: import rebirth_fx.editor as fx; fx.import_effect('/Game/Effect/...')
"""
import json, os, struct, time, traceback

import unreal

from . import fxcore, livelink

ROOT = '/Game/RebirthFx'
MOD_NAME = 'RebirthFx_P'
_state = {'current': None, 'live': False, 'tick': None, 'pushed': {}, 'next_check': 0.0}


# ---------------------------------------------------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------------------------------------------------

def _saved_dir():
    return os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'RebirthFx')


def _message(text, title='Rebirth FX'):
    unreal.log('[Rebirth FX] ' + text.replace('\n', ' | '))
    try:
        unreal.EditorDialog.show_message(title, text, unreal.AppMsgType.OK)
    except Exception:
        pass


def _paks():
    return unreal.RebirthFxLibrary.get_game_paks_directory()


def _short(package_name):
    return package_name.rsplit('/', 1)[-1]


def _asset_name(emitter, curve):
    """'Main.ColorFromCurve002.ColorCurve' -> 'Main_ColorFromCurve002' (the curve names already start with their emitter)."""
    base = curve
    for suffix in ('.ColorCurve', '.FloatCurve'):
        if base.endswith(suffix):
            base = base[:-len(suffix)]
    out = ''.join(ch if ch.isalnum() else '_' for ch in base)
    while '__' in out:
        out = out.replace('__', '_')
    return out.strip('_') or 'Curve'


def _enum_member(enum_type, *needles):
    for name in dir(enum_type):
        upper = name.upper()
        if all(n in upper for n in needles):
            return getattr(enum_type, name)
    raise AttributeError('%s has no member with %s' % (enum_type, needles))


def _import_curve_csv(csv_path, folder, name, color):
    """A CurveLinearColor (color) or CurveFloat from a csv of rows time,values... (linear keys)."""
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', csv_path)
    task.set_editor_property('destination_path', folder)
    task.set_editor_property('destination_name', name)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('automated', True)
    task.set_editor_property('save', False)
    factory = unreal.CSVImportFactory()
    settings = factory.get_editor_property('automated_import_settings')
    settings.set_editor_property('import_type', _enum_member(unreal.CSVImportType, 'LINEAR', 'COLOR') if color else _enum_member(unreal.CSVImportType, 'CURVE', 'FLOAT'))
    settings.set_editor_property('import_curve_interp_mode', _enum_member(unreal.RichCurveInterpMode, 'LINEAR'))
    factory.set_editor_property('automated_import_settings', settings)
    task.set_editor_property('factory', factory)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    path = folder + '/' + name
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError('could not make the curve asset ' + path)
    return asset


def _sample(asset, kind, times):
    out = []
    if kind == 'color':
        for t in times:
            c = asset.get_linear_color_value(t)
            out += [c.r, c.g, c.b, c.a]
    else:
        for t in times:
            out.append(asset.get_float_value(t))
    return out


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


# ---------------------------------------------------------------------------------------------------------------------
# open an effect
# ---------------------------------------------------------------------------------------------------------------------

def open_effect():
    """Menu: pick a game effect and open it."""
    try:
        names = unreal.RebirthFxLibrary.find_game_packages_matching('/Game/Effect/ FX_', 60000)
        names = [n for n in names if '/Particle/' in n or '/Niagara/' in n or n.rsplit('/', 1)[-1].startswith('FX_')]
        if not names:
            _message('The game\'s packages were not found. Is FINAL FANTASY VII REBIRTH installed, and is its folder known to the '
                     'Rebirth tools (Rebirth > Data Objects asks for it once)?')
            return None
        current = _state['current']
        choice = unreal.RebirthFxLibrary.pick_from_list('Open Game Effect', 'Type part of a name (for example CrossSlash, PC0000, '
                                                        'Limit). Double-click or Open to bring its curves into the editor.', names,
                                                        _short(current) if current else 'CrossSlash')
        if not choice:
            return None
        return import_effect(choice)
    except Exception:
        _message('Opening the effect failed:\n' + traceback.format_exc())
        return None


def import_effect(package_name, reimport=False):
    """Brings a game effect's curves into /Game/RebirthFx/<effect>. Returns the manifest."""
    short = _short(package_name)
    work = os.path.join(_saved_dir(), short)
    folder = ROOT + '/' + short
    existing = _load_manifest(short)
    if existing and not reimport and unreal.EditorAssetLibrary.does_directory_exist(folder):
        _state['current'] = package_name
        unreal.EditorAssetLibrary.sync_browser_to_objects([folder])
        _message('%s is already open in %s (its curves keep your edits).\nUse Recolour, Play Effect In Game or Export Effects To '
                 'Game from the Rebirth FX menu.' % (short, folder))
        return existing
    if not os.path.isdir(work):
        os.makedirs(work)
    original = os.path.join(work, 'original.uasset')
    err = unreal.RebirthFxLibrary.save_game_package_to_file(package_name, original)
    if err:
        raise RuntimeError(err)
    header_file = os.path.join(work, 'container_header.bin')
    result = unreal.RebirthFxLibrary.save_game_container_header_to_file(package_name, header_file)
    err, container = (result if isinstance(result, tuple) else (result, ''))
    if err:
        raise RuntimeError(err)
    pkg = fxcore.Package(open(original, 'rb').read(), short)
    if not pkg.is_niagara_system():
        raise RuntimeError('%s is not a Niagara effect (its classes: %s)' % (package_name, ', '.join(sorted(set(pkg.classes().values())))))
    curves = fxcore.curves(pkg)
    manifest = dict(package=package_name, short=short, folder=folder, original=original, header=header_file, container=container,
                    parse_errors=pkg.errors, curves=[])
    with unreal.ScopedSlowTask(max(1, len(curves)), 'Bringing %s into the editor' % short) as task:
        task.make_dialog(True)
        used = set()
        for c in curves:
            task.enter_progress_frame(1)
            name = _asset_name(c['emitter'], c['name'])
            n = name
            k = 2
            while n in used:
                n = '%s_%d' % (name, k)
                k += 1
            used.add(n)
            times = fxcore.sample_times(c['samples'], c['tmin'], c['tmax'])
            if c['kind'] == 'color':
                vals = [tuple(c['floats'][j:j + 4]) for j in range(0, len(c['floats']), 4)]
            elif c['kind'] == 'float':
                vals = [(v,) for v in c['floats']]
            else:
                continue   # (vector curves: not editable yet)
            keep = fxcore.reduce_keys(times, vals, 0.002) if len(times) > 2 else list(range(len(times)))
            csv_path = os.path.join(work, n + '.csv')
            with open(csv_path, 'w') as f:
                for j in keep:
                    f.write(','.join(['%.7g' % times[j]] + ['%.7g' % x for x in vals[j]]) + '\n')
            asset = _import_curve_csv(csv_path, folder, n, c['kind'] == 'color')
            sampled = _sample(asset, c['kind'], times)
            manifest['curves'].append(dict(asset=folder + '/' + n, emitter=c['emitter'], name=c['name'], kind=c['kind'],
                                           samples=c['samples'], tmin=c['tmin'], tmax=c['tmax'], original=c['floats'],
                                           imported=sampled, copies=c['copies']))
    unreal.EditorAssetLibrary.save_directory(folder, only_if_is_dirty=False, recursive=True)
    json.dump(manifest, open(_manifest_path(short), 'w', encoding='utf-8'), indent=1)
    _state['current'] = package_name
    unreal.EditorAssetLibrary.sync_browser_to_objects([folder])
    colours = sum(1 for c in manifest['curves'] if c['kind'] == 'color')
    _message('%s is open in %s: %d colour curves and %d float curves.\n\nDouble-click a colour curve: its gradient shows the colour '
             'over the particles\' life; edit keys, or use Adjust Hue / Saturation / Brightness. Then Rebirth FX > Export Effects To '
             'Game (or Play Effect In Game to watch it).' % (short, folder, colours, len(manifest['curves']) - colours))
    return manifest


# ---------------------------------------------------------------------------------------------------------------------
# recolour every colour curve of the open effect
# ---------------------------------------------------------------------------------------------------------------------

PRESETS = [('Blue', 215.0), ('Cyan', 185.0), ('Green', 125.0), ('Purple', 275.0), ('Pink', 320.0), ('Red', 5.0), ('Gold', 45.0)]


def recolour(hue=None, short=None):
    """Every colour curve of the effect (the open one by default) to `hue` (degrees), keeping brightness and saturation."""
    try:
        if short is None:
            if not _state['current']:
                _message('Open an effect first (Rebirth FX > Open Game Effect...).')
                return
            short = _short(_state['current'])
        m = _load_manifest(short)
        if not m:
            _message('%s is not open.' % short)
            return
        if hue is None:
            names = ['%s (%d)' % (n, h) for n, h in PRESETS]
            choice = unreal.RebirthFxLibrary.pick_from_list('Recolour ' + short, 'Every colour curve of %s goes to this hue; '
                                                            'brightness and saturation stay. (Undo: re-open the effect.)' % short, names, '')
            if not choice:
                return
            hue = dict(PRESETS)[choice.split(' (')[0]]
        work = os.path.join(_saved_dir(), short)
        for c in m['curves']:
            if c['kind'] != 'color':
                continue
            times = fxcore.sample_times(c['samples'], c['tmin'], c['tmax'])
            asset = unreal.load_asset(c['asset'])
            if asset is None:
                continue
            cur = _sample(asset, 'color', times)
            vals = []
            for j in range(0, len(cur), 4):
                r, g, b = fxcore.to_hue(cur[j], cur[j + 1], cur[j + 2], hue=hue)
                vals.append((r, g, b, cur[j + 3]))
            keep = fxcore.reduce_keys(times, vals, 0.002)
            name = c['asset'].rsplit('/', 1)[-1]
            csv_path = os.path.join(work, name + '.csv')
            with open(csv_path, 'w') as f:
                for j in keep:
                    f.write(','.join(['%.7g' % times[j]] + ['%.7g' % x for x in vals[j]]) + '\n')
            _import_curve_csv(csv_path, m['folder'], name, True)
        unreal.EditorAssetLibrary.save_directory(m['folder'], only_if_is_dirty=False, recursive=True)
        _message('%s: every colour curve is now hue %.0f. Export Effects To Game to put it in the game.' % (short, hue))
    except Exception:
        _message('Recolouring failed:\n' + traceback.format_exc())


# ---------------------------------------------------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------------------------------------------------

def _edited_package(m):
    """(new package bytes, number of changed curves) of a workspace."""
    data = open(m['original'], 'rb').read()
    writes = []
    changed = 0
    for c in m['curves']:
        asset = unreal.load_asset(c['asset'])
        if asset is None:
            continue
        times = fxcore.sample_times(c['samples'], c['tmin'], c['tmax'])
        now = _sample(asset, c['kind'], times)
        if all(abs(a - b) < 1e-6 for a, b in zip(now, c['imported'])):
            continue   # untouched: the game's own values stay exactly
        changed += 1
        for cp in c['copies']:
            if cp['samples'] == c['samples'] and abs(cp['tmin'] - c['tmin']) < 1e-6 and abs(cp['tmax'] - c['tmax']) < 1e-6:
                writes.append((cp['at'], now))
            else:
                writes.append((cp['at'], _sample(asset, c['kind'], fxcore.sample_times(cp['samples'], cp['tmin'], cp['tmax']))))
    return fxcore.patch(data, writes), changed


def export_to_game(install=True):
    """Every open effect with changes into one mod (RebirthFx_P), written to Saved/RebirthFx/Mod and copied to ~mods."""
    try:
        packages, headers, report = [], [], []
        for m in _workspaces():
            data, changed = _edited_package(m)
            if not changed:
                continue
            check = fxcore.Package(data, m['short'])
            if check.errors:
                raise RuntimeError('%s no longer reads back: %s' % (m['short'], check.errors))
            packages.append(data)
            headers.append(open(m['header'], 'rb').read())
            report.append('%s: %d curves changed' % (m['short'], changed))
        if not packages:
            _message('Nothing to export: no curve of an open effect has changed.')
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
        others = _other_mods_with(packages)
        warn = ('\n\nAlso in ~mods, with the same effects (one of them wins): ' + ', '.join(others)) if others else ''
        _message('%s is in %s:\n%s\n\nRestart the game to see it.%s' % (MOD_NAME, where, '\n'.join(report), warn))
        return files
    except Exception:
        _message('Exporting failed:\n' + traceback.format_exc())
        return None


def _other_mods_with(packages):
    """Names of other ~mods containers holding one of these packages (they would fight over it)."""
    paks = _paks()
    mods = os.path.join(paks, '~mods') if paks else None
    if not mods or not os.path.isdir(mods):
        return []
    from .iostore_write import package_id
    from .zen import Zen
    want = set()
    for data in packages:
        z = Zen(data)
        want.add(package_id(z.mapped(z.name_mapped)))
    found = []
    for name in sorted(os.listdir(mods)):
        if not name.endswith('.utoc') or name == MOD_NAME + '.utoc':
            continue
        try:
            raw = open(os.path.join(mods, name), 'rb').read()
            hdr_size, entries = struct.unpack_from('<II', raw, 20)
            for k in range(entries):
                cid = struct.unpack_from('<Q', raw, hdr_size + 12 * k)[0]
                if cid in want:
                    found.append(name[:-5])
                    break
        except Exception:
            pass
    return found


# ---------------------------------------------------------------------------------------------------------------------
# live link
# ---------------------------------------------------------------------------------------------------------------------

def play_in_game(package_name=None, every=4.0):
    try:
        package_name = package_name or _state['current']
        if not package_name:
            _message('Open an effect first (Rebirth FX > Open Game Effect...).')
            return
        paks = _paks()
        if not livelink.installed(paks):
            _message('The RebirthLiveLink mod is not in the game (ue4ss\\Mods\\RebirthLiveLink).')
            return
        seq = livelink.send(paks, 'spawn', path=package_name, loop=True, every=float(every), forward=300.0, up=50.0)
        s = livelink.wait(paks, seq, 4.0)
        if s is None:
            _message('The game did not answer. Is it running, past the title screen, with the RebirthLiveLink mod?')
            return
        r = s.get('result', {})
        if r.get('ok'):
            _message('The game plays %s in front of your character, again every %.0f s.\nRebirth FX > Stop Effect In Game ends it.' % (_short(package_name), every))
        else:
            _message('The game: %s' % r.get('error'))
    except Exception:
        _message('Play in game failed:\n' + traceback.format_exc())


def stop_in_game():
    try:
        paks = _paks()
        seq = livelink.send(paks, 'stop')
        livelink.wait(paks, seq, 2.0)
    except Exception:
        _message('Stop failed:\n' + traceback.format_exc())


def _live_tick(delta):
    if not _state['live'] or not _state['current']:
        return
    now = time.time()
    if now < _state['next_check']:
        return
    _state['next_check'] = now + 0.5
    try:
        m = _load_manifest(_short(_state['current']))
        if not m:
            return
        paks = _paks()
        changed = []
        for c in m['curves']:
            asset = unreal.load_asset(c['asset'])
            if asset is None:
                continue
            times = fxcore.sample_times(c['samples'], c['tmin'], c['tmax'])
            vals = _sample(asset, c['kind'], times)
            last = _state['pushed'].get(c['asset'], c['imported'])
            if all(abs(a - b) < 1e-6 for a, b in zip(vals, last)):
                continue
            _state['pushed'][c['asset']] = vals
            changed.append(dict(curve=c['name'], hex=livelink.floats_hex(vals), samples=c['samples'], tmin=c['tmin'], tmax=c['tmax']))
        if changed:
            # one command with every changed curve (the game runs the newest command only)
            seq = livelink.send(paks, 'set_lut', path=m['package'], curves=changed)
            _state['last_live'] = seq
    except Exception:
        unreal.log_warning('[Rebirth FX] live edit: ' + traceback.format_exc())


def toggle_live():
    _state['live'] = not _state['live']
    if _state['live'] and _state['tick'] is None:
        _state['tick'] = unreal.register_slate_post_tick_callback(_live_tick)
    if not _state['live']:
        _message('Live edits are off.')
        return
    answer = ''
    try:
        paks = _paks()
        if livelink.installed(paks):
            s = livelink.wait(paks, livelink.send(paks, 'ping'), 3.0)
            if s is None:
                answer = ('\n\nThe game did not answer yet (not running, or in a loading screen). The edits go to it once it '
                          'answers.')
            else:
                answer = '\n\nThe game answered (RebirthLiveLink %s).' % s.get('version', '?')
    except Exception:
        pass
    _message('Live edits are ON: curve changes go to the running game as you make them (Play Effect In Game replays the '
             'effect so you see them).\nGPU particles (sparks, splashes) keep the colours they loaded with until the next '
             'game start: Export Effects To Game for those.' + answer)


def probe_in_game(package_name=None, dump=False):
    """Diagnostics: what the game holds for the effect (emitters, scripts, data interfaces)."""
    package_name = package_name or _state['current']
    paks = _paks()
    seq = livelink.send(paks, 'probe', path=package_name, dump=bool(dump))
    return livelink.wait(paks, seq, 6.0)


# ---------------------------------------------------------------------------------------------------------------------
# menu
# ---------------------------------------------------------------------------------------------------------------------

def register_menus():
    menus = unreal.ToolMenus.get()
    main = menus.find_menu('LevelEditor.MainMenu')
    if main is None:
        unreal.log_warning('[Rebirth FX] the level editor main menu is not there; no menu')
        return
    sub = main.add_sub_menu(main.get_name(), 'RebirthFx', 'RebirthFx', 'Rebirth FX', 'FINAL FANTASY VII REBIRTH effect tools')

    def entry(name, label, tip, command, section='Effects'):
        e = unreal.ToolMenuEntry(name=name, type=unreal.MultiBlockType.MENU_ENTRY)
        e.set_label(label)
        e.set_tool_tip(tip)
        e.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, '', command)
        sub.add_menu_entry(section, e)

    entry('RebirthFxOpen', 'Open Game Effect...', 'Pick one of the game\'s effects: its curves become Curve assets you can edit',
          'import rebirth_fx.editor as fx; fx.open_effect()')
    entry('RebirthFxRecolour', 'Recolour Effect...', 'Every colour curve of the open effect to one hue', 'import rebirth_fx.editor as fx; fx.recolour()')
    entry('RebirthFxExport', 'Export Effects To Game', 'Every changed effect into the RebirthFx_P mod in ~mods',
          'import rebirth_fx.editor as fx; fx.export_to_game()')
    entry('RebirthFxPlay', 'Play Effect In Game', 'The running game plays the open effect in front of your character',
          'import rebirth_fx.editor as fx; fx.play_in_game()', 'LiveLink')
    entry('RebirthFxStop', 'Stop Effect In Game', 'Removes what Play Effect In Game spawned', 'import rebirth_fx.editor as fx; fx.stop_in_game()', 'LiveLink')
    entry('RebirthFxLive', 'Live Edits On/Off', 'While on, curve changes go to the running game as you make them',
          'import rebirth_fx.editor as fx; fx.toggle_live()', 'LiveLink')
    try:
        from . import materials
        materials.add_menu_entries(sub)
    except Exception:
        unreal.log_warning('[Rebirth FX] the material entries were not added: ' + traceback.format_exc())
    menus.refresh_all_widgets()
    unreal.log('[Rebirth FX] menu ready (Rebirth FX in the main menu)')
