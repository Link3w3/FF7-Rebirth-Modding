"""Kawaii Dynamic Motions (Create a Character System 3.15.0), step 2 of run_kawaii_dynamic_motions_install.cmd: Bahamut
Fused Sephiroth's compat file with his tail's sway and his blade wings' beat ("pose_waves") into the game mod's compat
folder. The file there, when it is another, is kept first in the game's
_mod_backups\\ue4ss\\BahamutFusedSephirothKawaii_<time>\\ (outside the compat folder: the mod reads every .json there).
    install_kdm_compat.py <stage folder (stage_kdm_example)>
Exit 0: in place (or there already), 1: a problem (the file there is unchanged)."""
import hashlib
import os
import shutil
import sys
import time

GAME = r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH'
COMPAT = os.path.join(GAME, 'End', 'Binaries', 'Win64', 'ue4ss', 'Mods', 'RebirthSkelCompat', 'compat')
NAME = 'BahamutFusedSephirothKawaii.json'
EXPECTED = 'b328c4b09fd5c95a356ec7ac6bf73345'


def md5(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def main():
    if len(sys.argv) != 2:
        print('usage: install_kdm_compat.py <stage folder>')
        return 2
    source = os.path.join(sys.argv[1], NAME)
    if not os.path.isfile(source) or md5(source) != EXPECTED:
        print('   FAILED: %s is missing or not the file made for this (MD5; tell Sandalphon)' % source)
        return 1
    if not os.path.isdir(COMPAT):
        print('   FAILED: the game mod\'s compat folder %s was not found' % COMPAT)
        return 1
    target = os.path.join(COMPAT, NAME)
    if os.path.isfile(target):
        if md5(target) == EXPECTED:
            print('   %s: there already' % NAME)
            return 0
        backup = os.path.join(GAME, '_mod_backups', 'ue4ss', 'BahamutFusedSephirothKawaii_' + time.strftime('%Y%m%d_%H%M%S'))
        os.makedirs(backup, exist_ok=True)
        shutil.copy2(target, os.path.join(backup, NAME))
        if md5(os.path.join(backup, NAME)) != md5(target):
            print('   FAILED: the file there could not be kept in %s; it is unchanged' % backup)
            return 1
        print('   the file there is kept in %s' % backup)
    temp = target + '.new'
    shutil.copyfile(source, temp)
    if md5(temp) != EXPECTED:
        os.replace(temp, temp + '.bad')
        print('   FAILED: the new %s did not copy whole (kept as %s.bad); the file there is unchanged' % (NAME, temp))
        return 1
    os.replace(temp, target)
    print('   %s: Bahamut Fused Sephiroth\'s tail sway and blade wing beat in compat' % NAME)
    return 0


if __name__ == '__main__':
    sys.exit(main())
