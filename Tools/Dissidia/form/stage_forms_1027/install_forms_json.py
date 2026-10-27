"""Puts a forms file into the game's compat folder (run by install_cc_form.cmd, the game closed): only if the installed
one is the file the new one was made from (MD5); the old one goes to <game>\\_mod_backups\\ue4ss\\<name>_<time>\\.
    install_forms_json.py <game folder> <new json> <old md5> <new md5>"""
import hashlib, os, shutil, sys, time


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def main():
    game, new, old_md5, new_md5 = sys.argv[1:5]
    name = os.path.basename(new)
    dst = os.path.join(game, 'End', 'Binaries', 'Win64', 'ue4ss', 'Mods', 'RebirthSkelCompat', 'compat', name)
    if md5(new) != new_md5:
        print('FAILED: %s is not the new file (MD5)' % new)
        return 1
    if not os.path.isfile(dst):
        print('FAILED: %s is not installed' % dst)
        return 1
    have = md5(dst)
    if have == new_md5:
        print('   %s: the new one is there already' % name)
        return 0
    if have != old_md5:
        print('   %s: the installed one is not the one the update was made from (changed since?): left as it is' % name)
        return 1
    backup = os.path.join(game, '_mod_backups', 'ue4ss', '%s_%s' % (os.path.splitext(name)[0], time.strftime('%Y%m%d_%H%M%S')))
    os.makedirs(backup, exist_ok=True)
    shutil.copy2(dst, os.path.join(backup, name))
    shutil.copy2(new, dst)
    if md5(dst) != new_md5:
        print('FAILED: %s did not go in right (the old one is in %s)' % (name, backup))
        return 1
    print('   %s updated (the old one: %s)' % (name, backup))
    return 0


if __name__ == '__main__':
    sys.exit(main())
