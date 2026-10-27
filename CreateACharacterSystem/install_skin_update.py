"""Create a Character System: installs a skin folder made outside the editor (its skin.json and its packages) into the game
the way the editor's Build Skins does with Install Skins on:
  * the folder goes into <game>\\End\\Binaries\\Win64\\ue4ss\\Mods\\RebirthSkelCompat\\skins\\<its folder name>,
  * ~mods\\CreateACharacterSkins_P is written again from every skin folder (in name order, a package only once),
  * with --gm <folder>, the Game Materials mod in that folder (RebirthGameMaterials_P.utoc/.ucas/.pak) goes into ~mods too.
The new skins container is built (in <project>\\Saved\\RebirthSkelCompat\\Skins\\_work\\_install_<UTC time>) before anything
in the game is touched. What it replaces is moved first to <project>\\_mod_backups\\<name>_<UTC time>\\; if a step fails,
what was there is put back. Close the game first (the .cmd that runs this checks). Python 3, no editor needed:
    py install_skin_update.py --skin <skin folder> [--gm <folder>] [--name <backup name>] [--game ...] [--project ...] [--dry-run]"""
import argparse, filecmp, json, os, shutil, sys, time

DEFAULT_GAME = r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH'
DEFAULT_PROJECT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CACHE = 'CreateACharacterSkins_P'
GM = 'RebirthGameMaterials_P'
EXTS = ('.utoc', '.ucas', '.pak')
SIZE_MASK = (1 << 60) - 1


def fail(msg):
    print('FAILED: ' + msg)
    sys.exit(1)


def load_skin(folder):
    with open(os.path.join(folder, 'skin.json'), encoding='utf-8') as f:
        return json.load(f)


def check_skin(folder):
    skin = load_skin(folder)
    if not skin.get('packages'):
        fail(folder + '\\skin.json has no packages')
    for p in skin['packages']:
        f = os.path.join(folder, p['file'])
        if not os.path.isfile(f):
            fail(f + ' is missing')
        if os.path.getsize(f) != p['size'] & SIZE_MASK:
            fail('%s is %d bytes, skin.json says %d' % (f, os.path.getsize(f), p['size'] & SIZE_MASK))
        for b in p.get('bulk', []):
            if not os.path.isfile(os.path.join(folder, b['file'])):
                fail(os.path.join(folder, b['file']) + ' is missing')
    return skin


def read(path):
    with open(path, 'rb') as f:
        return f.read()


def build_cache(W, folders, base, empty_pak):
    """The skins container from (folder name, folder path) pairs in name order: the same as Build Skins writes."""
    chunks, entries, seen, report = [None], [], set(), []
    for folder, path in folders:
        if not os.path.isfile(os.path.join(path, 'skin.json')):
            continue
        skin = load_skin(path)
        if skin.get('enabled') is False:
            report.append('  %s: off' % folder)
            continue
        for p in skin.get('packages', []):
            pid = W.package_id(p['package'])
            if pid in seen:
                report.append('  %s: %s is in another skin too, left out' % (folder, p['package']))
                continue
            seen.add(pid)
            data = read(os.path.join(path, p['file']))
            chunks.append(dict(id64=pid, type=2, data=data, path=p['package'][len('/Game/'):] + '.uasset'))
            for b in p.get('bulk', []):
                chunks.append(dict(id64=pid, type=b['type'], data=read(os.path.join(path, b['file'])), path=b['file'][len('Content/'):]))
            flags = p['size'] & ~SIZE_MASK
            entries.append(dict(id=pid, size=len(data) | flags, export_count=p['export_count'], export_bundle_count=p['export_bundle_count'],
                                load_order=p['load_order'], imports=[int(x, 16) for x in p['imports']]))
        report.append('  %s: %d package(s)' % (folder, len(skin.get('packages', []))))
    cid = W.container_id_from_name(CACHE)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    W.write_container(base, CACHE, chunks)
    shutil.copyfile(empty_pak, base + '.pak')
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--skin', required=True, help='the skin folder to install (its name is the folder name in skins)')
    ap.add_argument('--gm', help='a folder with RebirthGameMaterials_P.utoc/.ucas/.pak to install too')
    ap.add_argument('--name', default='skin', help='the backup folder name')
    ap.add_argument('--game', default=DEFAULT_GAME)
    ap.add_argument('--project', default=DEFAULT_PROJECT)
    ap.add_argument('--dry-run', action='store_true', help='only build the new skins container, touch nothing in the game')
    a = ap.parse_args()
    project = os.path.normpath(a.project)
    skin_dir = os.path.normpath(a.skin)
    sys.path.insert(0, os.path.join(project, 'Content', 'Python'))
    from rebirth_fx import iostore_write as W
    mods = os.path.join(a.game, 'End', 'Content', 'Paks', '~mods')
    skins = os.path.join(a.game, 'End', 'Binaries', 'Win64', 'ue4ss', 'Mods', 'RebirthSkelCompat', 'skins')
    for d in (mods, skins):
        if not os.path.isdir(d):
            fail(d + ' was not found')
    folder = os.path.basename(skin_dir)
    skin = check_skin(skin_dir)
    print('skin %s (%s): %d package(s), weapon %s' % (skin.get('name', folder), folder, len(skin['packages']), skin.get('weapon', '-')))
    if a.gm:
        for ext in EXTS:
            if not os.path.isfile(os.path.join(a.gm, GM + ext)):
                fail(os.path.join(a.gm, GM + ext) + ' is missing')
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    work = os.path.join(project, 'Saved', 'RebirthSkelCompat', 'Skins', '_work', '_install_' + stamp)
    os.makedirs(work)
    names = sorted(set(n for n in os.listdir(skins) if os.path.isdir(os.path.join(skins, n))) | {folder})
    folders = [(n, skin_dir if n == folder else os.path.join(skins, n)) for n in names]
    print('the skins container, from every skin folder:')
    print('\n'.join(build_cache(W, folders, os.path.join(work, CACHE), os.path.join(project, 'Content', 'Python', 'rebirth_fx', 'data', 'empty_P.pak'))))
    if a.dry_run:
        print('dry run: built in %s, nothing in the game changed' % work)
        return
    backup = os.path.join(project, '_mod_backups', '%s_%s' % (a.name, stamp))
    os.makedirs(os.path.join(backup, 'mods'))
    moved = []

    def move_aside(src, dst):
        shutil.move(src, dst)
        moved.append((src, dst))

    try:
        if os.path.isdir(os.path.join(skins, folder)):
            move_aside(os.path.join(skins, folder), os.path.join(backup, folder))
        for name in [CACHE] + ([GM] if a.gm else []):
            for ext in EXTS:
                p = os.path.join(mods, name + ext)
                if os.path.isfile(p):
                    move_aside(p, os.path.join(backup, 'mods', name + ext))
        print('what was there is in %s' % backup)
        shutil.copytree(skin_dir, os.path.join(skins, folder))
        pairs = [(os.path.join(work, CACHE + ext), os.path.join(mods, CACHE + ext)) for ext in EXTS]
        if a.gm:
            pairs += [(os.path.join(a.gm, GM + ext), os.path.join(mods, GM + ext)) for ext in EXTS]
        for src, dst in pairs:
            shutil.copyfile(src, dst)
        for src, dst in pairs:
            if not filecmp.cmp(src, dst, shallow=False):
                raise RuntimeError(dst + ' is not the same as ' + src + ' after copying')
        if not filecmp.cmp(os.path.join(skin_dir, 'skin.json'), os.path.join(skins, folder, 'skin.json'), shallow=False):
            raise RuntimeError('skins\\' + folder + '\\skin.json is not the same after copying')
    except Exception as e:
        print('FAILED: %s; putting back what was there' % e)
        partial = os.path.join(backup, '_not_installed')
        for src, dst in reversed(moved):
            if os.path.exists(src):
                os.makedirs(partial, exist_ok=True)
                shutil.move(src, os.path.join(partial, os.path.basename(src)))
            shutil.move(dst, src)
        print('put back (what was copied in is in %s)' % partial)
        sys.exit(1)
    print('INSTALLED: skins\\%s, ~mods\\%s%s' % (folder, CACHE, (' and ~mods\\' + GM) if a.gm else ''))


if __name__ == '__main__':
    main()
