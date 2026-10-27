"""Puts a new build of a Fully Playable (Young) Sephiroth data container into the game (run by the install .cmd, the game
closed). The new container is the installed one's .ucas with new blocks after it (the .tail made with it), a new .utoc and
the same .pak: so only the tail and the .utoc come over.
For each installed copy of the container under ~mods (not under _mod_backups) whose .utoc and .ucas are the build the
new one was made from (MD5): the new .ucas (the old one + the tail) is written next to it, checked (size and MD5), then
the old three files go into the game's _mod_backups\\Paks\\<name>_<time>\\ and the new ones take their place. A copy of another
build is left as it is (and said).
The old files go to <game>\\_mod_backups\\Paks\\<name>_<time>\\, outside End\\Content\\Paks: the game mounts every .pak
anywhere under Paks, so a backup there with its .pak is mounted too, and the old container (the same name and container
id) wins over the new one (3.12.0's install did that: the new moves were not found).
    install_data_tail.py <game Paks folder> <stage folder> <name> <old utoc md5> <old ucas md5> <old ucas size>
                         <new utoc md5> <new ucas md5> <new ucas size>
Exit 0: installed (or none installed to update), 1: a problem (nothing half done: the old files stay until the new are
checked)."""
import hashlib, os, shutil, sys, time


def md5(path, chunk=1 << 24):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    paks, stage, name = sys.argv[1], sys.argv[2], sys.argv[3]
    old_utoc_md5, old_ucas_md5, old_ucas_size = sys.argv[4], sys.argv[5], int(sys.argv[6])
    new_utoc_md5, new_ucas_md5, new_ucas_size = sys.argv[7], sys.argv[8], int(sys.argv[9])
    tail = os.path.join(stage, name + '.ucas.tail')
    utoc_new = os.path.join(stage, name + '.utoc')
    for f in (tail, utoc_new):
        if not os.path.isfile(f):
            print('FAILED: %s is missing' % f)
            return 1
    if md5(utoc_new) != new_utoc_md5:
        print('FAILED: %s is not the new build (MD5)' % utoc_new)
        return 1
    if os.path.getsize(tail) != new_ucas_size - old_ucas_size:
        print('FAILED: %s is %d bytes, not %d' % (tail, os.path.getsize(tail), new_ucas_size - old_ucas_size))
        return 1
    mods = os.path.join(paks, '~mods')
    found = []
    for root, dirs, files in os.walk(mods):
        dirs[:] = [d for d in dirs if not d.lower().startswith('_mod_backups')]
        if name + '.utoc' in files and name + '.ucas' in files:
            found.append(root)
    if not found:
        print('   %s: not installed (nothing to update)' % name)
        return 0
    stamp = time.strftime('%Y%m%d_%H%M%S')
    problems = 0
    for folder in found:
        utoc, ucas, pak = (os.path.join(folder, name + ext) for ext in ('.utoc', '.ucas', '.pak'))
        have_utoc = md5(utoc)
        if have_utoc == new_utoc_md5 and os.path.getsize(ucas) == new_ucas_size:
            print('   %s: the new build is there already (%s)' % (name, folder))
            continue
        if have_utoc != old_utoc_md5 or os.path.getsize(ucas) != old_ucas_size or md5(ucas) != old_ucas_md5:
            print('   %s in %s is another build than the one the update was made from: left as it is' % (name, folder))
            problems += 1
            continue
        # the new .ucas next to the old, checked before anything is moved
        temp = ucas + '.new'
        with open(temp, 'wb') as out:
            with open(ucas, 'rb') as f:
                shutil.copyfileobj(f, out, 1 << 24)
            with open(tail, 'rb') as f:
                shutil.copyfileobj(f, out, 1 << 24)
        if os.path.getsize(temp) != new_ucas_size or md5(temp) != new_ucas_md5:
            os.replace(temp, temp + '.bad')
            print('FAILED: the new %s.ucas did not come out right (kept as %s.bad); the installed files are unchanged' % (name, temp))
            return 1
        # (not under Paks: the game would mount the old copy's .pak too, and its old container wins)
        game = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(paks))))
        backup = os.path.join(game, '_mod_backups', 'Paks', '%s_%s' % (name, stamp))
        os.makedirs(backup, exist_ok=True)
        for f in (utoc, ucas):
            shutil.move(f, os.path.join(backup, os.path.basename(f)))
        if os.path.isfile(pak):
            shutil.copy2(pak, os.path.join(backup, os.path.basename(pak)))
        os.replace(temp, ucas)
        shutil.copy2(utoc_new, utoc)
        if md5(utoc) != new_utoc_md5 or os.path.getsize(ucas) != new_ucas_size:
            print('FAILED: %s did not go in right (the old files are in %s)' % (name, backup))
            return 1
        print('   %s updated in %s (the old files: %s)' % (name, folder, backup))
    return 1 if problems and len(found) == problems else 0


if __name__ == '__main__':
    sys.exit(main())
