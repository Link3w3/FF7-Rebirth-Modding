"""Rebirth FX > Materials > Game Materials: your own materials (custom shaders) in the game, looking as they do in the
editor. See gamemat/convert.py for how a material is made.

  Make Game Materials (Selected)   the materials you selected in the Content Browser (or the materials on the meshes you
                                   selected) compiled for the game; every material made so far goes into one mod,
                                   RebirthGameMaterials_P, installed in the game's ~mods folder
  Install Game Materials           copies the last built mod into ~mods again (after closing the game)
  Remove A Game Material...        takes one out of the mod

Python: import rebirth_fx.gamematerials as gm; gm.make(['/Game/Shader/KadeMats/Material_Instances/Taken_Inst'])

A material made here can be live-edited in the running game (Rebirth FX > Materials > Material Live Edits): its textures
at once, and its values (scalars, colours) when it was made with live values (every material made from now on that has
a free texture parameter for them; one made before needs making once more).
"""
import json
import os
import traceback

import unreal

from .gamemat import env

TITLE = 'Game Materials'
_QUIET = [False]


def _message(text, title=TITLE):
    unreal.log('[Game Materials] ' + text.replace('\n', ' | '))
    if _QUIET[0]:
        return
    try:
        unreal.EditorDialog.show_message(title, text, unreal.AppMsgType.OK)
    except Exception:
        pass


def _native():
    for name in ('RebirthFxLinkLibrary', 'RebirthFxLibrary'):
        found = getattr(unreal, name, None)
        if found is not None and hasattr(found, 'export_material_for_game'):
            return found
    raise RuntimeError('The Rebirth FX Live Link editor plugin (with Export Material For Game) is not loaded: Edit > Plugins > '
                       'Rebirth FX Live Link')


class _Editor(object):
    def __init__(self, native):
        self.native = native

    def export(self, material_path, folder):
        m = unreal.load_asset(material_path)
        if m is None:
            return 'the editor could not load %s' % material_path
        err = self.native.export_material_for_game(m, folder)
        if err:
            # the usual reason: a parent that is not in the project (the editor loads a stand-in without shaders)
            p = m.get_editor_property('parent') if isinstance(m, unreal.MaterialInstance) else None
            for _ in range(16):
                if p is None:
                    break
                if not self.on_disk(p.get_path_name()):
                    return 'its material %s is not in the project (missing, or never saved), so it has no shaders here (%s)' % (
                        p.get_name(), err)
                p = p.get_editor_property('parent') if isinstance(p, unreal.MaterialInstance) else None
        return err

    @staticmethod
    def on_disk(object_path):
        """A /Game asset that is saved in the project's Content folder (other mount points: assumed so)."""
        package = object_path.split('.', 1)[0]
        if not package.startswith('/Game/'):
            return True
        content = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
        return os.path.isfile(os.path.join(content, package[len('/Game/'):] + '.uasset'))

    def asset_exists(self, object_path):
        """A saved asset of the project: the cook reads packages from disk, so one that is only in memory (made in this
        session and never saved) does not cook."""
        package = object_path.split('.', 1)[0]
        return bool(unreal.EditorAssetLibrary.does_asset_exist(package)) and self.on_disk(package)

    def split_channels(self, texture_path, wanted):
        """(fused hair) Single-channel textures made from channels of a packed one, next to it: EB0021_00_Hair_M ->
        EB0021_00_Hair_Mr (its R) and EB0021_00_Hair_Mg (its G), as the game's own hair has them. From the packed
        texture's source file (or an export of it), made again when that file is newer. wanted: [(channel 'r', 'g', 'b'
        or 'a', suffix)]. Returns their object paths."""
        env.vendor()
        from PIL import Image
        package = texture_path.split('.')[0]
        folder, name = package.rsplit('/', 1)
        tex = unreal.load_asset(package)
        if tex is None:
            raise RuntimeError('no texture ' + package)
        src = ''
        data = tex.get_editor_property('asset_import_data')
        if data is not None:
            try:
                src = data.get_first_filename()
            except Exception:
                src = ''
        if not src or not os.path.isfile(src):
            src = self._export_image(tex, name)
        img = Image.open(src)
        img.load()
        bands = dict(zip('RGBA', img.convert('RGBA').split()))
        stamp = os.path.getmtime(src)
        out = []
        for ch, suffix in wanted:
            new = (name[:-1] + suffix) if name.endswith('_M') else '%s_%s' % (name, suffix)
            path = '%s/%s' % (folder, new)
            png = env.work('split', new + '.png')
            os.makedirs(os.path.dirname(png), exist_ok=True)
            fresh = (unreal.EditorAssetLibrary.does_asset_exist(path) and os.path.isfile(png) and
                     os.path.getmtime(png) >= stamp)
            if not fresh:
                bands[ch.upper()].save(png)
                task = unreal.AssetImportTask()
                for k, v in (('filename', png), ('destination_path', folder), ('destination_name', new),
                             ('replace_existing', True), ('automated', True), ('save', False)):
                    task.set_editor_property(k, v)
                unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
                made = unreal.load_asset(path)
                if made is None:
                    raise RuntimeError('%s did not import' % new)
                made.set_editor_property('srgb', False)
                made.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_ALPHA)
                made.set_editor_property('lod_group', tex.get_editor_property('lod_group'))
                unreal.EditorAssetLibrary.save_loaded_asset(made, False)
            out.append('%s.%s' % (path, new))
        return out

    @staticmethod
    def _export_image(tex, name):
        path = env.work('split', name + '_source.tga')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        task = unreal.AssetExportTask()
        for k, v in (('object', tex), ('filename', path), ('automated', True), ('replace_identical', True), ('prompt', False)):
            task.set_editor_property(k, v)
        if not unreal.Exporter.run_asset_export_task(task) or not os.path.isfile(path):
            raise RuntimeError('could not export %s to split it' % name)
        return path

    def cook(self, packages, content_dir):
        lib = getattr(unreal, 'EndSkeletonCompatDataObject', None)
        if lib is None or not hasattr(lib, 'cook_packages_for_game'):
            raise RuntimeError('cooking textures needs Create a Character System\'s editor plugin (Cook For Game)')
        return lib.cook_packages_for_game(packages, content_dir)


def _material_path(m):
    return m.get_path_name()


def selected_materials():
    """The material paths of the Content Browser selection: materials themselves, and the materials of selected meshes."""
    out = []
    for a in unreal.EditorUtilityLibrary.get_selected_assets():
        mats = []
        if isinstance(a, unreal.MaterialInterface):
            mats = [a]
        elif isinstance(a, unreal.SkeletalMesh):
            mats = [x.get_editor_property('material_interface') for x in a.get_editor_property('materials')]
        elif isinstance(a, unreal.StaticMesh):
            mats = [x.get_editor_property('material_interface') for x in a.get_editor_property('static_materials')]
        for m in mats:
            if m is not None:
                p = _material_path(m)
                if p not in out:
                    out.append(p)
    return out


def _skip_reason(path):
    """Materials that are the game's own (its RMI_* families and the character instances on them) stay as they are."""
    if path.startswith('/Game/Renderer/'):
        return 'one of the game\'s material families'
    m = unreal.load_asset(path)
    p = m
    for _ in range(8):
        if not isinstance(p, unreal.MaterialInstance):
            break
        p = p.get_editor_property('parent')
        if p is not None and p.get_path_name().startswith('/Game/Renderer/MaterialInstance/'):
            return 'already a game material (its parent is %s)' % p.get_name()
    return None


def make(paths=None, install=True, quiet=False):
    """Makes the materials (paths, or the Content Browser selection) game materials, rebuilds the mod and installs it.
    quiet: no dialogs (the summary goes to the log and the returned report)."""
    _QUIET[0] = quiet
    env.vendor()
    from .gamemat import convert
    paths = paths or selected_materials()
    if not paths:
        _message('Select the materials (or the meshes wearing them) in the Content Browser first.')
        return None
    native = _native()
    game = convert.GameData(native)
    editor = _Editor(native)
    conv = convert.Converter(game, editor)
    store = convert.Store()
    made, failed, skipped = [], [], []
    try:
        env.dxc()
    except RuntimeError as e:
        _message(str(e))
        return None
    with unreal.ScopedSlowTask(len(paths) + 3, 'Making game materials...') as task:
        task.make_dialog(True)
        task.enter_progress_frame(1, 'Reading the game\'s shader library...')
        try:
            game.library()
        except Exception as e:
            _message('The game\'s shader library could not be read: %s' % e)
            return None
        for path in paths:
            if task.should_cancel():
                break
            short = path.rsplit('.', 1)[-1]
            task.enter_progress_frame(1, 'Compiling %s for the game...' % short)
            why = _skip_reason(path)
            if why:
                skipped.append((short, why))
                continue
            try:
                packages, info = conv.convert(path)
                store.put(path, packages, info)
                made.append((short, info))
            except Exception as e:
                failed.append((short, str(e)))
                unreal.log_warning('[Game Materials] %s: %s' % (path, traceback.format_exc()))
        task.enter_progress_frame(1, 'Cooking the textures and building %s...' % convert.MOD_NAME)
        try:
            mod_paths, entries, notes = convert.build_mod(store, game, editor.cook)
        except Exception as e:
            unreal.log_warning('[Game Materials] ' + traceback.format_exc())
            _message('The mod could not be built: %s' % e)
            return None
        installed, err = ([], None)
        if install:
            task.enter_progress_frame(1, 'Installing...')
            installed, err = convert.install(mod_paths, game.paks_dir)
    lines = []
    if made:
        lines.append('Made for the game (%d):' % len(made))
        for short, info in made:
            extra = ', two-sided' if info.get('two_sided') else ''
            if info.get('live'):
                extra += ', live values on %s' % info['live']['slot']
            lines.append('  %s  (%s on %s%s, %d texture(s))' % (short, info['kind'], info['carrier'], extra, len(info['textures'])))
            if info.get('missing'):
                lines.append('    plain white in the game, as these textures are not in the project (missing, or never saved): %s'
                             % ', '.join(m.rsplit('.', 1)[-1] for m in info['missing']))
    if skipped:
        lines.append('Left as they are:')
        lines += ['  %s: %s' % s for s in skipped]
    if failed:
        lines.append('Not made:')
        lines += ['  %s: %s' % (s, e.splitlines()[0][:300]) for s, e in failed]
    lines.append('')
    lines.append('%s holds %d material(s).' % (convert.MOD_NAME, len(store.manifest)))
    if install:
        lines.append(('Installed in %s.' % os.path.dirname(installed[0])) if installed and not err else err or 'Not installed.')
    lines.append('A model wears them in the game where its material slots point at these materials.')
    _message('\n'.join(lines))
    report = dict(made=[s for s, _ in made], failed=failed, skipped=skipped, mod=mod_paths, installed=installed, error=err,
                  summary='\n'.join(lines))
    with open(env.work('last_run.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1)
    return report


def install():
    env.vendor()
    from .gamemat import convert
    native = _native()
    paks = native.get_game_paks_directory()
    mod_dir = env.work('mod')
    paths = [os.path.join(mod_dir, convert.MOD_NAME + ext) for ext in ('.utoc', '.ucas', '.pak')]
    if not all(os.path.isfile(p) for p in paths):
        _message('There is no built mod yet: use Make Game Materials first.')
        return
    installed, err = convert.install(paths, paks)
    _message(err or 'Installed %s in %s.' % (convert.MOD_NAME, os.path.join(paks, '~mods')))


def remove():
    env.vendor()
    from .gamemat import convert
    native = _native()
    store = convert.Store()
    if not store.manifest:
        _message('No game materials made yet.')
        return
    names = sorted(store.manifest)
    choice = native.pick_from_list('Remove A Game Material', 'The material to take out of %s:' % convert.MOD_NAME, names, '')
    if not choice:
        return
    store.remove(choice)
    game = convert.GameData(native)
    editor = _Editor(native)
    if store.manifest:
        mod_paths, entries, notes = convert.build_mod(store, game, editor.cook)
        installed, err = convert.install(mod_paths, game.paks_dir)
        _message(err or '%s taken out; %s rebuilt and installed (%d left).' % (choice, convert.MOD_NAME, len(store.manifest)))
    else:
        mods = os.path.join(game.paks_dir, '~mods')
        _message('%s was the last one: delete %s.utoc/.ucas/.pak from %s to take the mod out.' % (choice, convert.MOD_NAME, mods))


def add_menu_entries(sub, section='Materials'):
    def entry(name, label, tip, command):
        e = unreal.ToolMenuEntry(name=name, type=unreal.MultiBlockType.MENU_ENTRY)
        e.set_label(label)
        e.set_tool_tip(tip)
        e.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, '', command)
        sub.add_menu_entry(section, e)

    entry('RebirthGameMatMake', 'Make Game Materials (Selected)',
          'The materials selected in the Content Browser (or on the selected meshes) compiled for the game with their own '
          'look, into the RebirthGameMaterials_P mod', 'import rebirth_fx.gamematerials as gm; gm.make()')
    entry('RebirthGameMatInstall', 'Install Game Materials', 'Copies the built RebirthGameMaterials_P into the game\'s ~mods '
          'folder (close the game first)', 'import rebirth_fx.gamematerials as gm; gm.install()')
    entry('RebirthGameMatRemove', 'Remove A Game Material...', 'Takes one material out of RebirthGameMaterials_P',
          'import rebirth_fx.gamematerials as gm; gm.remove()')
