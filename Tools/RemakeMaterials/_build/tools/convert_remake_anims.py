"""FF7 Remake's animations of one character -> FBX files + manifest.json for import_remake_anims.py (End editor).

    python3 convert_remake_anims.py [--budget SECONDS] [--force] [--only Folder/Anim ...]

Reads the game's extracted (decrypted) files:
    <game>/GameContents/Motion/Enemy/EB0021_Sephiroth/<Folder>/<Anim>.uasset        the AnimSequences
    <game>/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00_Skeleton.uasset   their USkeleton
    and the models' reference skeletons (EB0021_00, EB0021_01_Body, EB0021_01_Wing: the bones the End skeleton has)
Writes (anim_fbx.py: the conventions skm_fbx.py gave the models):
    <out>/<Folder>/<Anim>.fbx     one animation stack, the game's frames
    <out>/manifest.json           what the import needs: tracked bones, curves, additive base, root motion settings
and lists the packages that are not AnimSequences (blend spaces, the game's anim sets) under "skipped".
Resumable: an FBX newer than its game file is kept (--force writes them all again); --budget stops after that many
seconds (run it again to go on); progress in <out>/convert_progress.json."""
import sys, os, io, json, time, contextlib, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anim, anim_fbx, pkg418, uprops, skm

HOME = os.path.expanduser('~')
GAME = os.environ.get('REMAKE_GAME', os.path.join(HOME, 'rk', 'out'))
MOTION = os.path.join(GAME, 'GameContents', 'Motion', 'Enemy', 'EB0021_Sephiroth')
CHAR = os.path.join(GAME, 'GameContents', 'Character', 'Enemy')
SKELETON = os.path.join(CHAR, 'EB0021_00_Sephiroth_Standard', 'Model', 'EB0021_00_Skeleton.uasset')
MODELS = [os.path.join(CHAR, 'EB0021_00_Sephiroth_Standard', 'Model', 'EB0021_00.uasset'),
          os.path.join(CHAR, 'EB0021_01_Sephiroth_Transform', 'Model', 'EB0021_01_Body.uasset'),
          os.path.join(CHAR, 'EB0021_01_Sephiroth_Transform', 'Model', 'EB0021_01_Wing.uasset')]
OUT = os.environ.get('REMAKE_ANIMS_OUT', os.path.join(HOME, 'mnt', 'FF7R2UProj', 'Tools', 'RemakeMaterials', '_build', 'remake_anims', 'EB0021_Sephiroth'))


def model_bones(paths):
    """the bones of the models' reference skeletons (the End skeleton was made from them), in first-seen order"""
    S = anim.schema()
    names = []
    for path in paths:
        p = pkg418.Package(path)
        k = next(i for i, e in enumerate(p.exports) if p.classname(e) == 'SkeletalMesh')
        cls, v, end = uprops.read_export(S, p, k)
        with contextlib.redirect_stdout(io.StringIO()):
            M, r = skm.read(p, k, end)
        for b in M['ref']['bones']:
            if b[0] not in names:
                names.append(b[0])
    return names


def packages(root):
    """(folder, name, path, class) of every package below the character's motion folder"""
    out = []
    for folder in sorted(os.listdir(root)):
        d = os.path.join(root, folder)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith('.uasset'):
                p = pkg418.Package(os.path.join(d, f))
                cls = sorted(set(p.classname(e) for e in p.exports))
                out.append((folder, f[:-7], os.path.join(d, f), cls))
    for f in sorted(os.listdir(root)):     # (the folders' own anim set packages)
        if f.endswith('.uasset'):
            p = pkg418.Package(os.path.join(root, f))
            out.append(('', f[:-7], os.path.join(root, f), sorted(set(p.classname(e) for e in p.exports))))
    return out


def main(argv):
    budget = float(argv[argv.index('--budget') + 1]) if '--budget' in argv else 1e9
    force = '--force' in argv
    only = set(argv[argv.index('--only') + 1:]) if '--only' in argv else None
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    man_path = os.path.join(OUT, 'manifest.json')
    try:
        man = json.load(open(man_path, encoding='utf-8'))
    except Exception:
        man = {}
    old = {'%s/%s' % (e['folder'], e['name']): e for e in man.get('anims', [])}
    skel = anim.skeleton(SKELETON)
    bones = model_bones(MODELS)
    pk = packages(MOTION)
    anims, skipped, failed = [], [], []
    done = written = 0
    stopped = False
    for folder, name, path, cls in pk:
        key = '%s/%s' % (folder, name)
        if folder == '' or 'AnimSequence' not in cls:
            skipped.append(dict(package=key if folder else name, classes=cls))
            continue
        fbx_rel = '%s/%s.fbx' % (folder, name)
        fbx = os.path.join(OUT, folder, name + '.fbx')
        src_time = max(os.path.getmtime(path), os.path.getmtime(path[:-7] + '.uexp'))
        fresh = (key in old and os.path.isfile(fbx) and os.path.getmtime(fbx) >= src_time and not force
                 and (only is None or key not in only))
        if fresh:
            anims.append(old[key]); done += 1
            continue
        if only is not None and key not in only:
            if key in old:
                anims.append(old[key])
            continue
        if time.time() - t0 > budget:
            stopped = True
            if key in old:
                anims.append(old[key])
            continue
        try:
            os.makedirs(os.path.dirname(fbx), exist_ok=True)
            info = anim_fbx.write(path, skel, fbx, bones, GAME, name)
            e = dict(folder=folder, name=name, fbx=fbx_rel)
            e.update({k: v for k, v in info.items() if k not in ('name', 'written', 'game_tracks')})
            e['fbx_bytes'] = os.path.getsize(fbx)
            anims.append(e); written += 1; done += 1
        except Exception:
            failed.append(dict(anim=key, error=traceback.format_exc()[-1200:]))
    total = sum(1 for f, n, p, c in pk if f and 'AnimSequence' in c)
    man = dict(source='FINAL FANTASY VII REMAKE, %s' % os.path.relpath(MOTION, GAME).replace('\\', '/'),
               skeleton='/Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00_Skeleton',
               destination='/Game/GameContents/Motion/Enemy/EB0021_Sephiroth', bones_in_skeleton=len(bones),
               anims=sorted(anims, key=lambda e: (e['folder'], e['name'])), skipped=skipped, failed=failed,
               complete=(done == total and not failed), written=time.strftime('%Y-%m-%d %H:%M:%S'))
    tmp = man_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(man, f, indent=1)
    os.replace(tmp, man_path)
    prog = dict(total=total, done=done, written_now=written, failed=len(failed), stopped_by_budget=stopped,
                skipped=len(skipped), seconds=round(time.time() - t0, 1))
    with open(os.path.join(OUT, 'convert_progress.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(prog, f, indent=1)
    print(json.dumps(prog))
    for x in failed[:5]:
        print('FAILED', x['anim'], x['error'][-400:])
    return prog


if __name__ == '__main__':
    main(sys.argv[1:])
