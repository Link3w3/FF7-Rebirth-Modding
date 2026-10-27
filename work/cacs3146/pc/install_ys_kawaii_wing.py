"""Young Sephiroth on KawaiiPhysics only (Create a Character System 3.14.0; run by run_ys_kawaii_wing_install.cmd, the game
closed):
  1. YoungSephiroth_P: his model PC0010_13 without its two BNMs (PC0010_13_BNM, his body's, and PC0010_13_Wing_BNM, his
     wing's: its Bonamik list emptied) and with its KDI (PC0010_13_KDI, the wing's KineDriver) kept. The new .ucas is
     the installed one with one span replaced (stage_yswing\\YoungSephiroth_P.ucas.mid); the .utoc is new, the .pak the
     same. The old .utoc and .ucas go to <game>\\_mod_backups\\Paks\\YoungSephiroth_P_<time>\\ (outside End\\Content\\Paks:
     the game mounts every .pak under Paks, and an old copy there would win).
  2. compat\\YoungSephirothKawaii.json: his hair, coat, collar and wing on KawaiiPhysics, each swinging about the pose the
     KDI gives it (the one there is kept as YoungSephirothKawaii.json.before_wing first).
Only a YoungSephiroth_P that is the build this was made from (MD5) is changed; another is left as it is (and said).
    install_ys_kawaii_wing.py <game Paks folder> <compat folder>
Exit 0: done, 1: a problem (nothing half done: the old files stay until the new ones are checked)."""
import hashlib
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.join(HERE, 'stage_yswing')
NAME = 'YoungSephiroth_P'
OLD_UTOC_MD5 = '81e25c777e8828c9d85d096e80705fff'
OLD_UCAS_MD5 = '2a5db30d5413842acb8b7d24aafd6498'
OLD_UCAS_SIZE = 52957184
NEW_UTOC_MD5 = '377d16549b3189fbea235b4f6d086857'
NEW_UCAS_MD5 = 'd6076857593fa3e7aed45322a177b8de'
NEW_UCAS_SIZE = 52957168
SPAN_FROM, SPAN_TO = 308608, 5164400          # the old .ucas's bytes [from, to) give way to the .mid
MID_MD5 = 'b91285e6bfb9398073331f59600c764e'
MID_SIZE = 4855776
KAWAII = 'YoungSephirothKawaii.json'
KAWAII_MD5 = '48c7a199a2bb4a6e643da6a47637dbaf'   # (each node simulated every frame: no fixed steps; the wing looser)


def md5(path, chunk=1 << 24):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def update_container(paks):
    mid = os.path.join(STAGE, NAME + '.ucas.mid')
    utoc_new = os.path.join(STAGE, NAME + '.utoc')
    for f, want, size in ((mid, MID_MD5, MID_SIZE), (utoc_new, NEW_UTOC_MD5, None)):
        if not os.path.isfile(f):
            print('   FAILED: %s is missing (tell Sandalphon)' % f)
            return False
        if (size is not None and os.path.getsize(f) != size) or md5(f) != want:
            print('   FAILED: %s is not the file made for this (MD5; tell Sandalphon)' % f)
            return False
    mods = os.path.join(paks, '~mods')
    found = []
    for root, dirs, files in os.walk(mods):
        dirs[:] = [d for d in dirs if not d.lower().startswith('_mod_backups')]
        if NAME + '.utoc' in files and NAME + '.ucas' in files:
            found.append(root)
    if not found:
        print('   FAILED: %s is not installed under %s' % (NAME, mods))
        return False
    stamp = time.strftime('%Y%m%d_%H%M%S')
    game = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(paks))))
    ok = True
    for folder in found:
        utoc, ucas, pak = (os.path.join(folder, NAME + ext) for ext in ('.utoc', '.ucas', '.pak'))
        if md5(utoc) == NEW_UTOC_MD5 and os.path.getsize(ucas) == NEW_UCAS_SIZE and md5(ucas) == NEW_UCAS_MD5:
            print('   %s: already the one without BNMs (%s)' % (NAME, folder))
            continue
        if md5(utoc) != OLD_UTOC_MD5 or os.path.getsize(ucas) != OLD_UCAS_SIZE or md5(ucas) != OLD_UCAS_MD5:
            print('   FAILED: %s in %s is another build than the one this was made from: left as it is (tell Sandalphon)' % (NAME, folder))
            ok = False
            continue
        temp = ucas + '.new'
        with open(temp, 'wb') as out:
            with open(ucas, 'rb') as f:
                out.write(f.read(SPAN_FROM))
                with open(mid, 'rb') as m:
                    shutil.copyfileobj(m, out, 1 << 24)
                f.seek(SPAN_TO)
                shutil.copyfileobj(f, out, 1 << 24)
        if os.path.getsize(temp) != NEW_UCAS_SIZE or md5(temp) != NEW_UCAS_MD5:
            os.replace(temp, temp + '.bad')
            print('   FAILED: the new %s.ucas did not come out right (kept as %s.bad); the installed files are unchanged' % (NAME, temp))
            return False
        backup = os.path.join(game, '_mod_backups', 'Paks', '%s_%s' % (NAME, stamp))
        os.makedirs(backup, exist_ok=True)
        for f in (utoc, ucas):
            shutil.move(f, os.path.join(backup, os.path.basename(f)))
        if os.path.isfile(pak):
            shutil.copy2(pak, os.path.join(backup, os.path.basename(pak)))
        os.replace(temp, ucas)
        shutil.copy2(utoc_new, utoc)
        if md5(utoc) != NEW_UTOC_MD5 or os.path.getsize(ucas) != NEW_UCAS_SIZE:
            print('   FAILED: %s did not go in right (the old files are in %s)' % (NAME, backup))
            return False
        print('   %s: his model without its BNMs, its KDI kept (%s; the old files: %s)' % (NAME, folder, backup))
    return ok


def put_kawaii(compat):
    source = os.path.join(STAGE, KAWAII)
    if not os.path.isfile(source) or md5(source) != KAWAII_MD5:
        print('   FAILED: %s is missing or not the file made for this (tell Sandalphon)' % source)
        return False
    if not os.path.isdir(compat):
        print('   FAILED: the compat folder %s was not found' % compat)
        return False
    target = os.path.join(compat, KAWAII)
    if os.path.isfile(target):
        if md5(target) == KAWAII_MD5:
            print('   %s: already in place' % KAWAII)
            return True
        backup = target + '.before_wing'
        if not os.path.exists(backup):
            shutil.copy2(target, backup)
            print('   the %s there is kept as %s' % (KAWAII, os.path.basename(backup)))
    shutil.copy2(source, target)
    if md5(target) != KAWAII_MD5:
        print('   FAILED: %s was not copied whole' % KAWAII)
        return False
    print('   %s in place: his hair, coat, collar and wing on KawaiiPhysics' % KAWAII)
    return True


def main():
    if len(sys.argv) != 3:
        print('usage: install_ys_kawaii_wing.py <game Paks folder> <compat folder>')
        return 2
    paks, compat = sys.argv[1], sys.argv[2]
    print('1/2 his model without its BNMs (YoungSephiroth_P)...')
    if not update_container(paks):
        return 1
    print('2/2 his KawaiiPhysics file...')
    if not put_kawaii(compat):
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
