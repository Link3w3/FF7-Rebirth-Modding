"""Puts a new build of a Fully Playable (Young) Sephiroth data container into the game (run by the install .cmd, the game
closed). The new container is a base build's .ucas with new blocks after it (the .tail made with it), a new .utoc and the
same .pak. The installed copy can be the base build itself or a later build made on it (the same base blocks, then blocks
of its own): its first <base size> bytes are the base's (checked by MD5), and the new .ucas is those bytes and the tail
(a later build's own blocks are not kept: the new .utoc does not use them).
For each installed copy under ~mods (not under _mod_backups) whose .utoc is one of the accepted builds: the new .ucas
is written next to it, checked (size and MD5), then the old three files go into the game's
_mod_backups\\Paks\\<name>_<time>\\ (outside End\\Content\\Paks: the game mounts every .pak anywhere under Paks) and the
new ones take their place. A copy of another build is left as it is (and said).
    install_data_rebase.py <game Paks folder> <stage folder> <name> <base ucas size> <base ucas md5>
                           <new utoc md5> <new ucas md5> <new ucas size> <accepted installed utoc md5s, comma separated>
Exit 0: installed (or none installed to update), 1: a problem (nothing half done: the old files stay until the new are
checked)."""
import hashlib, os, shutil, sys, time


def md5(path, limit=None, chunk=1 << 24):
    h = hashlib.md5()
    left = limit
    with open(path, 'rb') as f:
        while left is None or left > 0:
            b = f.read(chunk if left is None else min(chunk, left))
            if not b:
                break
            h.update(b)
            if left is not None:
                left -= len(b)
    return h.hexdigest()


def copy_prefix(src, out, size, chunk=1 << 24):
    left = size
    with open(src, 'rb') as f:
        while left > 0:
            b = f.read(min(chunk, left))
            if not b:
                raise IOError('%s ends before %d bytes' % (src, size))
            out.write(b)
            left -= len(b)


def main():
    paks, stage, name = sys.argv[1], sys.argv[2], sys.argv[3]
    base_size, base_md5 = int(sys.argv[4]), sys.argv[5]
    new_utoc_md5, new_ucas_md5, new_ucas_size = sys.argv[6], sys.argv[7], int(sys.argv[8])
    accepted = [x.strip() for x in sys.argv[9].split(',') if x.strip()]
    tail = os.path.join(stage, name + '.ucas.tail')
    utoc_new = os.path.join(stage, name + '.utoc')
    for f in (tail, utoc_new):
        if not os.path.isfile(f):
            print('FAILED: %s is missing' % f)
            return 1
    if md5(utoc_new) != new_utoc_md5:
        print('FAILED: %s is not the new build (MD5)' % utoc_new)
        return 1
    if os.path.getsize(tail) != new_ucas_size - base_size:
        print('FAILED: %s is %d bytes, not %d' % (tail, os.path.getsize(tail), new_ucas_size - base_size))
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
        if have_utoc not in accepted or os.path.getsize(ucas) < base_size or md5(ucas, base_size) != base_md5:
            print('   %s in %s is another build than the ones the update was made for: left as it is' % (name, folder))
            problems += 1
            continue
        temp = ucas + '.new'
        with open(temp, 'wb') as out:
            copy_prefix(ucas, out, base_size)
            with open(tail, 'rb') as f:
                shutil.copyfileobj(f, out, 1 << 24)
        if os.path.getsize(temp) != new_ucas_size or md5(temp) != new_ucas_md5:
            os.replace(temp, temp + '.bad')
            print('FAILED: the new %s.ucas did not come out right (kept as %s.bad); the installed files are unchanged' % (name, temp))
            return 1
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
