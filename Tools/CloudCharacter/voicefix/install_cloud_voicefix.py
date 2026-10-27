"""CLOUD's voice fix (run by Tools\\CloudCharacter\\run_cloud_voicefix.cmd with the game closed): CreateACharacterCloud_P
again, with the store entries the game's own packages have.

Its packages (CLOUD's CharaSpec packs) listed, besides Cloud's voice and lip sync (/Game/Sound/Voice/JP/...,
/Game/LipSync/Lsd/JP/...), the English, French and German copies of them as packages to load. The game's own packs list
the JP ones only. The game then loaded every language of Cloud's voice into the one voice package it plays: his voice
came out in another language, and the loads landing on top of each other crashed the game (on his first voice line
after the CHARACTER page swap, and while loading a save with CLOUD chosen). The packages themselves are the same
bytes; only the container's header changed.

  1. finds the installed CreateACharacterCloud_P under ~mods (any folder but _mod_backups): it must be the build this
     fix is for (or the fixed one already: then nothing is done);
  2. moves its three files to the game's _mod_backups\\Paks\\CreateACharacterCloud_P_<time>\\, puts the fixed ones in
     the same folder, and checks them (size and MD5);
  3. puts the fixed files in Tools\\CloudCharacter too (with manifest.json), so the CLOUD installer counts the fixed
     build as the one made (the older files there go to Tools\\CloudCharacter\\_old\\voicefix_<time>\\).
Nothing is deleted.
    install_cloud_voicefix.py --check | --install"""
import hashlib, json, os, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)                       # Tools\CloudCharacter
GAME = r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH'
MODS = os.path.join(GAME, 'End', 'Content', 'Paks', '~mods')
BACKUPS = os.path.join(GAME, '_mod_backups')
STAMP = time.strftime('%Y%m%d_%H%M%S')
NAME = 'CreateACharacterCloud_P'
EXTS = ('.utoc', '.ucas', '.pak')
OLD = {'.utoc': (65861, '8b560696690af1702ab14456d3b247c2'), '.ucas': (4072000, '5253dae857fbed33a060f892d72206b0'),
       '.pak': (347, '797a546e664c558fd47fb30b4be7bad5')}
NEW = {'.utoc': (65861, 'b3309c00953944aee69b6cf2cbadc9c4'), '.ucas': (4069904, '867ecc5e492c9299d5081123f732ee0e'),
       '.pak': (347, '797a546e664c558fd47fb30b4be7bad5')}


def md5(path, chunk=1 << 24):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def is_build(folder, build):
    for ext in EXTS:
        p = os.path.join(folder, NAME + ext)
        if not os.path.isfile(p) or os.path.getsize(p) != build[ext][0] or md5(p) != build[ext][1]:
            return False
    return True


def installed():
    """The folders under ~mods holding a CreateACharacterCloud_P (not under _mod_backups)."""
    found = []
    for root, dirs, files in os.walk(MODS):
        dirs[:] = [d for d in dirs if not d.lower().startswith('_mod_backups')]
        if NAME + '.utoc' in files:
            found.append(root)
    return found


def check():
    problems = []
    for ext in EXTS:
        p = os.path.join(HERE, NAME + ext)
        if not os.path.isfile(p) or os.path.getsize(p) != NEW[ext][0] or md5(p) != NEW[ext][1]:
            problems.append('%s%s here is not the fixed build (size or MD5)' % (NAME, ext))
    found = installed()
    if not found:
        problems.append('%s is not installed under ~mods' % NAME)
    elif len(found) > 1:
        problems.append('%s is installed in more than one folder under ~mods (%s): tell Sandalphon' % (NAME, '; '.join(found)))
    else:
        folder = found[0]
        if not is_build(folder, NEW) and not is_build(folder, OLD):
            problems.append('the %s in %s is another build than the one the fix is for: tell Sandalphon' % (NAME, folder))
    return problems, found


def put_tools_copy():
    """The fixed files and their manifest entries in Tools\\CloudCharacter (the CLOUD installer's own copies)."""
    manifest_path = os.path.join(TOOLS, 'manifest.json')
    manifest = json.load(open(manifest_path))
    if all(os.path.isfile(os.path.join(TOOLS, NAME + ext)) and md5(os.path.join(TOOLS, NAME + ext)) == NEW[ext][1] for ext in EXTS) and \
            all(manifest['files'].get(NAME + ext) == {'size': NEW[ext][0], 'md5': NEW[ext][1]} for ext in EXTS):
        print('   Tools\\CloudCharacter: the fixed files are there already')
        return True
    old = os.path.join(TOOLS, '_old', 'voicefix_' + STAMP)
    os.makedirs(old, exist_ok=True)
    shutil.copy2(manifest_path, os.path.join(old, 'manifest.json'))
    for ext in EXTS:
        p = os.path.join(TOOLS, NAME + ext)
        if os.path.isfile(p):
            shutil.move(p, os.path.join(old, NAME + ext))
        shutil.copy2(os.path.join(HERE, NAME + ext), p)
        if md5(p) != NEW[ext][1]:
            print('FAILED: Tools\\CloudCharacter\\%s%s did not copy right' % (NAME, ext))
            return False
        manifest['files'][NAME + ext] = {'size': NEW[ext][0], 'md5': NEW[ext][1]}
    temp = manifest_path + '.new_tmp'
    json.dump(manifest, open(temp, 'w'), indent=1)
    os.replace(temp, manifest_path)
    print('   Tools\\CloudCharacter: the fixed files and manifest.json are in (the older ones in %s)' % old)
    return True


def main():
    if sys.argv[1:] not in (['--check'], ['--install']):
        print('install_cloud_voicefix.py --check | --install: run Tools\\CloudCharacter\\run_cloud_voicefix.cmd instead; nothing was changed')
        if not sys.argv[1:]:
            input('Press Enter to close this window')
        return 2
    problems, found = check()
    if problems:
        for p in problems:
            print('FAILED: ' + p)
        print('   nothing was changed')
        return 1
    folder = found[0]
    if sys.argv[1:] == ['--check']:
        print('   the fixed build is here; the installed one (%s) is %s' % (folder, 'the fixed one already' if is_build(folder, NEW) else 'the one the fix is for'))
        return 0
    if is_build(folder, NEW):
        print('   %s in %s: the fixed build is in already' % (NAME, folder))
    else:
        backup = os.path.join(BACKUPS, 'Paks', '%s_%s' % (NAME, STAMP))
        os.makedirs(backup, exist_ok=True)
        for ext in EXTS:
            shutil.move(os.path.join(folder, NAME + ext), os.path.join(backup, NAME + ext))
        if not is_build(backup, OLD):
            print('FAILED: the backup of the old %s in %s did not come out right: tell Sandalphon' % (NAME, backup))
            return 1
        print('   the old %s is in %s' % (NAME, backup))
        for ext in EXTS:
            shutil.copy2(os.path.join(HERE, NAME + ext), os.path.join(folder, NAME + ext))
        if not is_build(folder, NEW):
            print('FAILED: the fixed %s did not go in right in %s: the old one is in %s: tell Sandalphon' % (NAME, folder, backup))
            return 1
        print('   the fixed %s is in %s' % (NAME, folder))
    return 0 if put_tools_copy() else 1


if __name__ == '__main__':
    sys.exit(main())
