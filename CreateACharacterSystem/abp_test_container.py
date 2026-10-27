"""The AnimBlueprint test container of Create a Character System editor 1.19 in the game's ~mods folder, for the in-game
test: CACS_AnimTemplateTest_P holds Cloud's player AnimBlueprint (/Game/BluePrint/Animation/Player/
PC0000_00_Cloud_Standard_Animation) rebuilt by the editor from its template, compiled and cooked.

    abp_test_container.py install   copies Tools\\RebirthSkelCompat\\abp\\out\\CACS_AnimTemplateTest_P.utoc/.ucas/.pak into
                                    ~mods, after checking them against the md5s of the container Sandalphon checked; a copy
                                    already in ~mods is moved to C:\\FF7R2UProj\\_mod_backups\\abp_test_<UTC time>\\ first
    abp_test_container.py remove    moves the three out of ~mods into C:\\FF7R2UProj\\_mod_backups\\abp_test_<UTC time>\\
                                    (the game's own Cloud AnimBlueprint plays again)
Exit 0: done; 1: nothing was changed (the reason printed).
"""
import hashlib
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'abp', 'out')
MODS = r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End\Content\Paks\~mods'
BACKUPS = r'C:\FF7R2UProj\_mod_backups'
NAME = 'CACS_AnimTemplateTest_P'
# the container Sandalphon decoded and compared with the game's AnimBlueprint (the one cooked by run_build_editor119.cmd on
# 25 Oct 19:02, with the 13 templates: the same graph, states, rules and settings as the one tested in the game at 18:32;
# only its nodes' new GUIDs differ)
EXPECTED = {'.utoc': '189fa4a1b9acb2b92521847cafe4451b', '.ucas': 'e0cd46af783db525b8ff45e08d93dfdb', '.pak': '978275e5395574cf363603d330e50a28'}


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def backup_dir():
    path = os.path.join(BACKUPS, 'abp_test_' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
    os.makedirs(path, exist_ok=True)
    return path


def move_out(why):
    """Moves the container's files out of ~mods (those there); returns [(from, to)]."""
    there = [os.path.join(MODS, NAME + ext) for ext in EXPECTED if os.path.isfile(os.path.join(MODS, NAME + ext))]
    if not there:
        return []
    dst = backup_dir()
    moved = []
    for src in there:
        to = os.path.join(dst, os.path.basename(src))
        shutil.move(src, to)
        moved.append((src, to))
    print('   %s: moved %d file(s) from ~mods to %s' % (why, len(moved), dst))
    return moved


def install():
    if not os.path.isdir(MODS):
        print('FAILED: the game\'s ~mods folder is not at %s' % MODS)
        return 1
    for ext, want in EXPECTED.items():
        src = os.path.join(OUT, NAME + ext)
        if not os.path.isfile(src):
            print('FAILED: %s is missing' % src)
            return 1
        got = md5(src)
        if got != want:
            print('FAILED: %s is not the container Sandalphon checked (md5 %s, expected %s). Nothing was changed: '
                  'tell Sandalphon' % (src, got, want))
            return 1
    moved = move_out('the copy installed before')
    try:
        for ext, want in EXPECTED.items():
            dst = os.path.join(MODS, NAME + ext)
            shutil.copy2(os.path.join(OUT, NAME + ext), dst)
            if md5(dst) != want:
                raise IOError('%s did not copy whole' % dst)
    except (IOError, OSError) as e:
        aside = backup_dir()
        for ext in EXPECTED:
            dst = os.path.join(MODS, NAME + ext)
            if os.path.isfile(dst):         # (a copy of this install: the ones there before were moved out first)
                shutil.move(dst, os.path.join(aside, os.path.basename(dst) + '.half'))
        for src, to in moved:
            shutil.move(to, src)
        print('FAILED: %s. ~mods is as it was.' % e)
        return 1
    print('   installed %s (.utoc/.ucas/.pak) in %s' % (NAME, MODS))
    return 0


def remove():
    if not os.path.isdir(MODS):
        print('FAILED: the game\'s ~mods folder is not at %s' % MODS)
        return 1
    if not move_out('taken out'):
        print('   %s is not in ~mods: nothing to take out' % NAME)
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('install', 'remove'):
        print(__doc__)
        sys.exit(1)
    sys.exit(install() if sys.argv[1] == 'install' else remove())
