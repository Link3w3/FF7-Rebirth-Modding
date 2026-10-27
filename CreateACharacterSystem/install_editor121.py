"""Create a Character System editor 1.21.0's files into place (run by run_cacs3180_install.cmd, the End editor closed):
the plugin's sources into C:\\FF7R2UProj\\Plugins\\RebirthSkelCompat (the data object's skins get Pack and Sets: the moves a
skin carries, written into skin.json for the game mod 3.18.0). Every staged file
is checked by MD5 first (nothing changes if one is not right); a file that is there and differs goes into
<backup folder>\\before_121_<time>\\<plugin|tools>\\ first (outside the Plugins folder); each new file is written next to
the old one, checked, then put in its place.
    install_editor121.py <stage folder> <plugin folder> <tools folder> <backup folder>
Exit 0: all in; 1: something was not (said)."""
import hashlib, json, os, shutil, sys, time


def md5(path, chunk=1 << 22):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    stage, plugin, tools, backups = sys.argv[1:5]
    manifest = json.load(open(os.path.join(stage, 'manifest.json'), encoding='utf-8'))
    roots = {'plugin': plugin, 'tools': tools}
    for f in manifest['files']:
        src = os.path.join(stage, f['src'])
        if not os.path.isfile(src) or md5(src) != f['md5']:
            print('FAILED: %s is missing or not the one staged (MD5); nothing was changed' % src)
            return 1
        if f['root'] not in roots or not os.path.isdir(roots[f['root']]):
            print('FAILED: %s is not there; nothing was changed' % roots.get(f['root'], f['root']))
            return 1
    stamp = time.strftime('%Y%m%d_%H%M%S')
    bad = 0
    for f in manifest['files']:
        root = roots[f['root']]
        src = os.path.join(stage, f['src'])
        dst = os.path.join(root, f['dst'])
        if os.path.isfile(dst) and md5(dst) == f['md5']:
            print('   %s: already the new one' % f['dst'])
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        existed = os.path.isfile(dst)
        if existed:
            keep = os.path.join(backups, 'before_121_' + stamp, f['root'], f['dst'])
            os.makedirs(os.path.dirname(keep), exist_ok=True)
            shutil.copy2(dst, keep)
        temp = dst + '.new121'
        shutil.copyfile(src, temp)
        if md5(temp) != f['md5']:
            os.remove(temp)
            print('   %s NOT copied: the copy did not come out right' % f['dst'])
            bad += 1
            continue
        os.replace(temp, dst)
        print('   %s %s' % (f['dst'], 'in place (the old one: %s)' % os.path.join(backups, 'before_121_' + stamp, f['root']) if existed else 'added'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
