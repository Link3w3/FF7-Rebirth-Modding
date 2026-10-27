"""After a new KawaiiPhysics plugin did not build: the new one (Plugins\\KawaiiPhysics) is moved to
<backups>\\KawaiiPhysics_failed_<time>\\ and the plugin install_kawaii_plugin.py kept just before it (the newest
<backups>\\KawaiiPhysics_<time>\\ with its built modules, made in the last two hours) is put back, so the editor opens with
the plugin it had. Nothing is deleted.
    restore_kawaii_plugin.py <project Plugins folder> <backups folder>
Exit 0: put back, 1: a problem (said)."""
import os
import re
import shutil
import sys
import time


def main():
    if len(sys.argv) != 3:
        print('usage: restore_kawaii_plugin.py <project Plugins folder> <backups folder>')
        return 2
    plugins, backups = sys.argv[1:3]
    target = os.path.join(plugins, 'KawaiiPhysics')
    kept = []
    for name in os.listdir(backups) if os.path.isdir(backups) else []:
        path = os.path.join(backups, name)
        if not re.fullmatch(r'KawaiiPhysics_\d{8}_\d{6}', name) or not os.path.isfile(os.path.join(path, 'Binaries', 'Win64', 'UE4Editor-KawaiiPhysics.dll')):
            continue
        made = time.mktime(time.strptime(name[len('KawaiiPhysics_'):], '%Y%m%d_%H%M%S'))   # (its name: when it was kept)
        if 0 <= time.time() - made < 7200:
            kept.append(name)
    if not kept:
        print('   FAILED: no plugin kept in the last two hours in %s: the new plugin stays (tell Sandalphon)' % backups)
        return 1
    source = os.path.join(backups, sorted(kept)[-1])
    if os.path.isdir(target):
        aside = os.path.join(backups, 'KawaiiPhysics_failed_' + time.strftime('%Y%m%d_%H%M%S'))
        shutil.move(target, aside)
        print('   the plugin that did not build is kept in %s' % aside)
    shutil.move(source, target)
    print('   the plugin from before is back in %s (from %s)' % (target, source))
    return 0


if __name__ == '__main__':
    sys.exit(main())
