"""KawaiiPhysics for the End editor: puts the plugin's files (stage_kawaii_plugin\\KawaiiPhysics, checked against its
manifest.json) into C:\\FF7R2UProj\\Plugins\\KawaiiPhysics. A KawaiiPhysics plugin already there is moved whole to
Tools\\RebirthSkelCompat\\_mod_backups\\KawaiiPhysics_<time>\\ first (outside Plugins: UnrealBuildTool would find two).
    install_kawaii_plugin.py <stage folder> <project Plugins folder> <backups folder>
Exit 0: in place, 1: a problem (nothing changed when the files did not check out)."""
import hashlib
import json
import os
import shutil
import sys
import time


def md5(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def main():
    if len(sys.argv) != 4:
        print('usage: install_kawaii_plugin.py <stage folder> <project Plugins folder> <backups folder>')
        return 2
    stage, plugins, backups = sys.argv[1:4]
    source = os.path.join(stage, 'KawaiiPhysics')
    manifest_path = os.path.join(stage, 'manifest.json')
    if not os.path.isfile(manifest_path):
        print('   FAILED: %s is missing (tell Sandalphon)' % manifest_path)
        return 1
    manifest = json.load(open(manifest_path, encoding='utf-8'))
    for rel, want in manifest['files'].items():
        path = os.path.join(source, *rel.split('/'))
        if not os.path.isfile(path) or md5(path) != want:
            print('   FAILED: %s is missing or not the file made for this (MD5; tell Sandalphon)' % path)
            return 1
    target = os.path.join(plugins, 'KawaiiPhysics')
    if os.path.isdir(target):
        backup = os.path.join(backups, 'KawaiiPhysics_' + time.strftime('%Y%m%d_%H%M%S'))
        os.makedirs(backups, exist_ok=True)
        shutil.move(target, backup)
        print('   the KawaiiPhysics plugin there is kept in %s' % backup)
    for rel in manifest['files']:
        src = os.path.join(source, *rel.split('/'))
        dst = os.path.join(target, *rel.split('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    for rel, want in manifest['files'].items():
        if md5(os.path.join(target, *rel.split('/'))) != want:
            print('   FAILED: %s did not copy whole' % rel)
            return 1
    print('   KawaiiPhysics %s: %d files in %s' % (manifest['version'], len(manifest['files']), target))
    return 0


if __name__ == '__main__':
    sys.exit(main())
