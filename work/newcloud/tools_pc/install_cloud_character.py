"""CLOUD (Create a Character System 3.16's CHARACTER page) and the CLOUD moveset into the game, run by
run_cacs3161_install.cmd (3.16.0: run_cacs3160_install.cmd) with the game closed, after the game mod is in:
  1. the containers: CreateACharacterCloud_P (CLOUD's own CharaSpec packs, blueprints and AnimBlueprint) into
     ~mods\\CreateACharacterCloud\\, CloudMovesetMoves_P (the CLOUD moveset's 123 moves) into
     ~mods\\FullyPlayableSephirothPaks\\CloudMoveset\\ (one found in any folder under ~mods, moved there, counts; a copy
     there already of another build goes to the game's _mod_backups\\Paks first);
  2. the Fully Playable Young Sephiroth data container with CLOUD's rows (install_data_rebase.py: the installed .ucas and
     the new blocks after it, the new .utoc; the old files to the game's _mod_backups\\Paks first);
  3. compat\\CloudCharacter.json into the mod's compat folder (one there already of another content goes to the game's
     _mod_backups\\ue4ss\\CloudCharacter_<time>\\ first);
  4. the CLOUD moveset in compat\\YoungSephirothForms.json and compat\\SephirothForms.json (pack Battle11, offered on the
     MOVESET page) and the Buster Sword on Cloud's back outside battle in skins\\RebirthCloud and skins\\RemakeCloud: each
     installed file must be the one the change was made from (else nothing at all is changed); it goes to the game's
     _mod_backups\\ue4ss\\<name>_<time>\\ first.
Every file is checked (size and MD5) before and after. Nothing is deleted.
    install_cloud_character.py --check | --install"""
import hashlib, json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH'
PAKS = os.path.join(GAME, 'End', 'Content', 'Paks')
MODS = os.path.join(PAKS, '~mods')
MOD = os.path.join(GAME, 'End', 'Binaries', 'Win64', 'ue4ss', 'Mods', 'RebirthSkelCompat')
BACKUPS = os.path.join(GAME, '_mod_backups')
MANIFEST = json.load(open(os.path.join(HERE, 'manifest.json')))
STAMP = time.strftime('%Y%m%d_%H%M%S')


def md5(path, chunk=1 << 24):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def same(path, want):
    return os.path.isfile(path) and os.path.getsize(path) == want['size'] and md5(path) == want['md5']


def staged(rel):
    return os.path.join(HERE, *rel.split('/'))


def target(rel):
    return os.path.join(MOD, *rel.split('/'))


def check():
    """The staged files are the ones made; the installed data container and the files the changes are for are the ones
    they were made for."""
    problems = []
    for rel, want in MANIFEST['files'].items():
        if not same(staged(rel), want):
            problems.append('%s is not the file made (size or MD5)' % rel)
    fp = MANIFEST['fpys']
    found = []
    for root, dirs, files in os.walk(MODS):
        dirs[:] = [d for d in dirs if not d.lower().startswith('_mod_backups')]
        if fp['name'] + '.utoc' in files:
            found.append(root)
    if not found:
        problems.append('%s is not installed under ~mods (CLOUD\'s rows go into it)' % fp['name'])
    for folder in found:
        utoc = os.path.join(folder, fp['name'] + '.utoc')
        ucas = os.path.join(folder, fp['name'] + '.ucas')
        have = md5(utoc)
        if have == fp['new_utoc_md5']:
            continue   # (the update is in already)
        if have not in fp['accepted_utoc_md5s'] or not os.path.isfile(ucas) or os.path.getsize(ucas) != fp['base_size']:
            problems.append('%s in %s is another build than the one the update is for (its .utoc MD5 %s): tell Sandalphon' % (fp['name'], folder, have))
    if not os.path.isdir(os.path.join(MOD, 'compat')):
        problems.append('the mod\'s compat folder is not there (%s)' % os.path.join(MOD, 'compat'))
    for r in MANIFEST['replace']:
        path = target(r['target'])
        if not os.path.isfile(path):
            problems.append('%s is not there (the change is made for it): tell Sandalphon' % r['target'])
        elif not any(same(path, b) for b in bases(r)) and not same(path, MANIFEST['files'][r['file']]):
            problems.append('%s was changed after the change was made for it (its MD5 %s): tell Sandalphon' % (r['target'], md5(path)))
    return problems


def bases(r):
    """The files a change is made for: the one there before it, or an earlier build of the change ("bases")."""
    return r.get('bases') or [r['base']]


def found_container(c):
    """A folder under ~mods (not under _mod_backups) that holds the container as made (moved there or not)."""
    names = [c['name'] + ext for ext in ('.utoc', '.ucas', '.pak')]
    for root, dirs, files in os.walk(MODS):
        dirs[:] = [d for d in dirs if not d.lower().startswith('_mod_backups')]
        if all(n in files for n in names) and all(same(os.path.join(root, n), MANIFEST['files'][n]) for n in names):
            return root
    return None


def install_container(c):
    folder = os.path.join(MODS, *c['folder'].split('/'))
    names = [c['name'] + ext for ext in ('.utoc', '.ucas', '.pak')]
    there = found_container(c)
    if there:
        print('   %s: already there (%s)' % (c['name'], there))
        return True
    there = [n for n in names if os.path.isfile(os.path.join(folder, n))]
    if there:
        backup = os.path.join(BACKUPS, 'Paks', '%s_%s' % (c['name'], STAMP))
        os.makedirs(backup, exist_ok=True)
        for n in there:
            shutil.move(os.path.join(folder, n), os.path.join(backup, n))
        print('   %s: the copy there before is in %s' % (c['name'], backup))
    os.makedirs(folder, exist_ok=True)
    for n in names:
        shutil.copy2(staged(n), os.path.join(folder, n))
    bad = [n for n in names if not same(os.path.join(folder, n), MANIFEST['files'][n])]
    if bad:
        print('FAILED: %s did not go in right (%s)' % (c['name'], ', '.join(bad)))
        return False
    print('   %s installed in %s' % (c['name'], folder))
    return True


def install_fpys():
    fp = MANIFEST['fpys']
    stage = staged(fp['stage'])
    args = [sys.executable, os.path.join(HERE, 'install_data_rebase.py'), PAKS, stage, fp['name'], str(fp['base_size']), fp['base_md5'],
            fp['new_utoc_md5'], fp['new_ucas_md5'], str(fp['new_ucas_size']), ','.join(fp['accepted_utoc_md5s'])]
    return subprocess.call(args) == 0


def put(entry, accepted=None):
    """One file of the mod's folder: the staged file in its place, the one there before (if another) backed up first."""
    want = MANIFEST['files'][entry['file']]
    path = target(entry['target'])
    if same(path, want):
        print('   %s: already there' % entry['target'])
        return True
    if accepted is not None and not any(same(path, b) for b in accepted):
        print('FAILED: %s was changed after the change was made for it: tell Sandalphon' % entry['target'])
        return False
    if os.path.isfile(path):
        backup = os.path.join(BACKUPS, 'ue4ss', '%s_%s' % (entry['backup'], STAMP))
        os.makedirs(backup, exist_ok=True)
        shutil.copy2(path, os.path.join(backup, os.path.basename(path)))
        if not same(os.path.join(backup, os.path.basename(path)), {'size': os.path.getsize(path), 'md5': md5(path)}):
            print('FAILED: the backup of %s did not come out right; it is unchanged' % entry['target'])
            return False
        print('   %s: the one there before is in %s' % (entry['target'], backup))
    temp = path + '.new_tmp'
    shutil.copy2(staged(entry['file']), temp)
    if not same(temp, want):
        print('FAILED: %s did not copy right; it is unchanged' % entry['target'])
        return False
    os.replace(temp, path)
    if not same(path, want):
        print('FAILED: %s did not go in right' % entry['target'])
        return False
    print('   %s installed' % entry['target'])
    return True


def main():
    if sys.argv[1:] not in (['--check'], ['--install']):
        # (started on its own, e.g. by a double click: the install .cmd runs it, after the game mod is built)
        print('install_cloud_character.py --check | --install: run the install .cmd instead (Tools\\CloudCharacter\\run_cacs3161_install.cmd); nothing was changed')
        if not sys.argv[1:]:
            input('Press Enter to close this window')
        return 2
    problems = check()
    if problems:
        for p in problems:
            print('FAILED: ' + p)
        print('   nothing was changed')
        return 1
    if sys.argv[1:] == ['--check']:
        print('   the files are the ones made; the installed data container and the files the changes are for are the ones they were made for')
        return 0
    ok = all(install_container(c) for c in MANIFEST['containers'])
    ok = ok and install_fpys()
    ok = ok and all(put(e) for e in MANIFEST['new'])
    ok = ok and all(put(r, bases(r)) for r in MANIFEST['replace'])
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
