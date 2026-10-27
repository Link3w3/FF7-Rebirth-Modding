"""Kawaii compat files into the game mod's compat folder (Create a Character System 3.17.0 on: run by
run_cacs3170_install.cmd): each staged file (<stage>\\manifest.json "files": its MD5 and the MD5 of the file it was made
from) replaces the one in ue4ss\\Mods\\RebirthSkelCompat\\compat when that is still the file it was made from (one you
have changed since is left as it is: the status says so). The file there is kept first in the game's
_mod_backups\\ue4ss\\kawaii_<tag>_<time>\\ (outside the compat folder: the mod reads every .json there).
    install_kawaii_jsons.py <stage folder>
Exit 0: all in place (or there already), 1: one or more not (each file is either the old one or the new one)."""
import hashlib
import json
import os
import shutil
import sys
import time

GAME = r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH'
COMPAT = os.path.join(GAME, 'End', 'Binaries', 'Win64', 'ue4ss', 'Mods', 'RebirthSkelCompat', 'compat')


def md5(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def main():
    if len(sys.argv) != 2:
        print('usage: install_kawaii_jsons.py <stage folder>')
        return 2
    stage = sys.argv[1]
    manifest = json.load(open(os.path.join(stage, 'manifest.json'), encoding='utf-8'))
    tag = manifest.get('tag', 'new')
    if not os.path.isdir(COMPAT):
        print('   FAILED: the game mod\'s compat folder %s was not found' % COMPAT)
        return 1
    # every staged file checked before anything changes
    for name, f in manifest['files'].items():
        src = os.path.join(stage, name)
        if not os.path.isfile(src) or md5(src) != f['md5']:
            print('   FAILED: %s is missing or not the file made for this (MD5; tell Sandalphon); nothing was changed' % src)
            return 1
    backup = os.path.join(GAME, '_mod_backups', 'ue4ss', 'kawaii_%s_%s' % (tag, time.strftime('%Y%m%d_%H%M%S')))
    bad = 0
    for name, f in manifest['files'].items():
        src = os.path.join(stage, name)
        target = os.path.join(COMPAT, name)
        if os.path.isfile(target):
            now = md5(target)
            if now == f['md5']:
                print('   %s: there already' % name)
                continue
            if f.get('from') and now != f['from']:
                print('   LEFT AS IT IS: %s there is not the file this was made from (changed since?): tell Sandalphon' % name)
                bad += 1
                continue
            os.makedirs(backup, exist_ok=True)
            shutil.copy2(target, os.path.join(backup, name))
            if md5(os.path.join(backup, name)) != now:
                print('   FAILED: %s could not be kept in %s; it is unchanged' % (name, backup))
                bad += 1
                continue
        temp = target + '.new'
        shutil.copyfile(src, temp)
        if md5(temp) != f['md5']:
            os.replace(temp, temp + '.bad')
            print('   FAILED: the new %s did not copy whole (kept as %s.bad); the file there is unchanged' % (name, temp))
            bad += 1
            continue
        os.replace(temp, target)
        print('   %s: %s' % (name, f.get('what', 'in place')))
    if os.path.isdir(backup):
        print('   the files there before are kept in %s' % backup)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
