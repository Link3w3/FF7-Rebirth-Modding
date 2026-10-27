"""Create a Character System 3.12.0's files into the game (run by run_cacs3120_game_install.cmd, the game closed, after
main.dll 3.12.0 is built and installed): the forms files, the Lua mods and the mod's README (stage3120\\manifest.json
"files": each checked by MD5 first; a file in the game that differs goes into ue4ss\\_mod_backups\\cacs3120_<time>\\
first), then the Fully Playable (Young) Sephiroth data containers ("data": install_data_tail.py, which updates each
installed copy of the build they were made from).
    install_cacs3120_files.py <game folder> <stage folder>
Exit 0: all in; 1: something was not (the status says what; a file is either the old one or the new one)."""
import hashlib, json, os, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


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
    game, stage = sys.argv[1], sys.argv[2]
    manifest = json.load(open(os.path.join(stage, 'manifest.json'), encoding='utf-8'))
    ue4ss = os.path.join(game, 'End', 'Binaries', 'Win64', 'ue4ss')
    paks = os.path.join(game, 'End', 'Content', 'Paks')
    stamp = time.strftime('%Y%m%d_%H%M%S')
    backup = os.path.join(ue4ss, '_mod_backups', 'cacs3120_' + stamp)
    bad = 0
    # every staged file checked before anything changes
    for f in manifest['files']:
        src = os.path.join(stage, f['src'])
        if not os.path.isfile(src) or md5(src) != f['md5']:
            print('FAILED: %s is missing or not the one staged (MD5); nothing was changed' % src)
            return 1
    for f in manifest['files']:
        src = os.path.join(stage, f['src'])
        dst = os.path.join(ue4ss, f['dst'])
        if os.path.isfile(dst) and md5(dst) == f['md5']:
            print('   %s: already the new one' % f['dst'])
            continue
        if not os.path.isdir(os.path.dirname(dst)):
            print('   %s NOT copied: its folder is not there (is that mod installed?)' % f['dst'])
            bad += 1
            continue
        if os.path.isfile(dst):
            keep = os.path.join(backup, f['dst'])
            os.makedirs(os.path.dirname(keep), exist_ok=True)
            shutil.copy2(dst, keep)
        temp = dst + '.new3120'
        shutil.copy2(src, temp)
        if md5(temp) != f['md5']:
            os.remove(temp)
            print('   %s NOT copied: the copy did not come out right' % f['dst'])
            bad += 1
            continue
        os.replace(temp, dst)
        print('   %s copied%s' % (f['dst'], ' (the old one: _mod_backups\\cacs3120_%s)' % stamp if os.path.isdir(backup) else ''))
    import install_data_tail as T
    for d in manifest.get('data', []):
        sys.argv = ['install_data_tail.py', paks, os.path.join(stage, d['stage']), d['name'], d['old_utoc'], d['old_ucas'], str(d['old_size']),
                    d['new_utoc'], d['new_ucas'], str(d['new_size'])]
        if T.main() != 0:
            bad += 1
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
