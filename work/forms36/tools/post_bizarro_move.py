"""After run_bizarro_move.cmd (Bizarro's movement, editor 1.12 "leaning into the animation's root motion"): his moves
container (SephirothForms_P, every form's built moves) and the compat file with Bizarro's built movement moves.
  1. pakchunk47 laid out like the game's animations (align_only.py: only RebirthSkelCompat/Built/SephirothForms/),
  2. checks: every package of the installed container is still there, every movement move the editor built is there,
     every package is an ACL clip,
  3. the installed SephirothForms.json with the Battle05 movement moves pointing at the built ones (the others as they are).
    post_bizarro_move.py <staged dir: pakchunk47-WindowsNoEditor.{pak,ucas,utoc}, bizarro_result.json> <bizarro_moves.json>
                         <out dir (new)>"""
import json, os, subprocess, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools', '/work/sephforms/tools']
from iostore import Toc

ALIGN = '/work/bizsum1015/tools/align_only.py'
INSTALLED_MOVES = '/work/forms36/post2/out/moves/SephirothForms_P.utoc'   # = the game's ~mods copy (md5 bc69b41c)
INSTALLED_JSON = '/work/forms36/post3/SephirothForms.json'                # = the game's compat copy (md5 9ca02001)
MOUNT = '../../../End/Content/'
MARKER = bytes([0x30, 0xAF, 0x2F, 0x90, 0x54, 0x94, 0xF4, 0x06, 0x59, 0x00, 0x49, 0x00, 0x49, 0x00, 0x53, 0x00])
ACL_TAG = (0xAC10AC10).to_bytes(4, 'little')
PREFIX = 'RebirthSkelCompat/Built/SephirothForms/'
BUILT = '/Game/' + PREFIX
SET = 'Battle05'


def packages(utoc):
    t = Toc(utoc)
    return {p[len(MOUNT):] for p in t.files.values() if p and p.startswith(MOUNT)}


def main(staged, plan_path, out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    os.makedirs(out)
    result = json.load(open(os.path.join(staged, 'bizarro_result.json')))
    assert 'error' not in result, result['error']
    assert result.get('done'), 'the editor step did not finish'
    failed = set(result.get('failed', []))
    print('editor: %s; failed: %s' % (result.get('build'), ', '.join(sorted(failed)) or 'none'))
    plan = json.load(open(plan_path))
    moving = [m for m in plan['moves'] if m['build'] and m.get('retarget') == 'lean']
    built = [m for m in moving if m['name'] not in failed]
    print('movement moves: %d, built: %d' % (len(moving), len(built)))

    chunk = os.path.join(staged, 'pakchunk47-WindowsNoEditor')
    moves_dir = os.path.join(out, 'moves')
    skip_path = os.path.join(out, 'left_out_packages.json')   # (moves the editor could not build stay out of the container)
    json.dump([PREFIX + '%s/%s.uasset' % (m['set'], m['name']) for m in moving if m['name'] in failed], open(skip_path, 'w'))
    subprocess.check_call([sys.executable, ALIGN, chunk + '.utoc', moves_dir, 'SephirothForms_P', chunk + '.pak', PREFIX, skip_path])

    new = packages(os.path.join(moves_dir, 'SephirothForms_P.utoc'))
    old = packages(INSTALLED_MOVES)
    lost = sorted(old - new)
    assert not lost, '%d package(s) of the installed container are missing: %s' % (len(lost), ', '.join(lost[:10]))
    want = {PREFIX + '%s/%s.uasset' % (SET, m['name']) for m in built}
    missing = sorted(w for w in want if w not in new)
    assert not missing, '%d built movement move(s) are not in the container: %s' % (len(missing), ', '.join(missing[:10]))
    toc = Toc(os.path.join(moves_dir, 'SephirothForms_P.utoc'))
    not_acl = []
    for i in range(toc.entries):
        path = toc.files.get(i)
        if not path or not path.endswith('.uasset'):
            continue
        data = toc.read(i)
        at = data.find(MARKER)
        if at >= 0 and data.find(ACL_TAG, at + 16, at + 64) < 0:
            not_acl.append(path[len(MOUNT):])
    assert not not_acl, '%d package(s) are not ACL clips: %s' % (len(not_acl), ', '.join(not_acl[:10]))
    print('ACL: every package')
    extra = sorted(p for p in new - old if p not in want)
    print('container: %d packages (%d before; new movement moves: %d; other new: %s)'
          % (len(new), len(old), len(want - old), ', '.join(extra[:12]) or 'none'))

    j = json.load(open(INSTALLED_JSON))
    row = j['animation_sets'][0]
    by_key = {(m['set'], m['key']): i for i, m in enumerate(row['moves'])}
    changed = 0
    for m in built:
        build = {'from': m['animation'], 'notifies_from': m['notifies_from'], 'retarget': 'lean', 'base': m['base']}
        if m.get('base_loop'):
            build['base_loop'] = True
        if m.get('lean_bone'):
            build['lean_bone'] = m['lean_bone']
        build['lean'] = m.get('lean', 18.0)
        entry = {'set': SET, 'key': m['name'], 'animation': BUILT + SET + '/' + m['name'] + '.' + m['name'], 'build': build}
        at = by_key.get((SET, m['name']))
        assert at is not None, 'the installed compat file has no %s %s' % (SET, m['name'])
        row['moves'][at] = entry
        changed += 1
    json_dir = os.path.join(out, 'json')
    os.makedirs(json_dir)
    json.dump(j, open(os.path.join(json_dir, 'SephirothForms.json'), 'w'), indent=1)
    print('compat file: %d moves, %d of Battle05 now built movement moves' % (len(row['moves']), changed))


if __name__ == '__main__':
    main(*sys.argv[1:4])
