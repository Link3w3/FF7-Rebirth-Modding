"""After run_bizarro_form.cmd: his moves container (SephirothForms_P, every form's built moves, Battle05 now among them)
and the compat file (SephirothForms.json without the Bizarro moves the editor could not build).
  1. pakchunk47 laid out like the game's animations (align_only.py: only RebirthSkelCompat/Built/SephirothForms/, so
     game packages the cooker put in the chunk stay out),
  2. checks: every package of the installed container is still there, every Battle05 move the editor built is there,
  3. compose_forms36.py with the editor's failed list.
    post_bizarro.py <staged dir: pakchunk47-WindowsNoEditor.{pak,ucas,utoc}, bizarro_result.json> <out dir (new)>"""
import json, os, subprocess, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools', '/work/sephforms/tools']
from iostore import Toc

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ALIGN = '/work/bizsum1015/tools/align_only.py'
INSTALLED_MOVES = '/work/kh2data1015b/moves/SephirothForms_P.utoc'   # = the game's ~mods copy (md5 b1a7aac0)
INSTALLED_JSON = '/work/forms1015/in/SephirothForms.json'             # = the game's compat copy (md5 9719dd87)
MOVES_JSON = os.path.join(ROOT, 'json', 'bizarro_moves.json')
MOUNT = '../../../End/Content/'
MARKER = bytes([0x30, 0xAF, 0x2F, 0x90, 0x54, 0x94, 0xF4, 0x06, 0x59, 0x00, 0x49, 0x00, 0x49, 0x00, 0x53, 0x00])
ACL_TAG = (0xAC10AC10).to_bytes(4, 'little')
PREFIX = 'RebirthSkelCompat/Built/SephirothForms/'


def packages(utoc):
    t = Toc(utoc)
    return {p[len(MOUNT):] for p in t.files.values() if p and p.startswith(MOUNT)}


def main(staged, out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    os.makedirs(out)
    result = json.load(open(os.path.join(staged, 'bizarro_result.json')))
    assert 'error' not in result, result['error']
    assert result.get('done'), 'the editor step did not finish'
    failed = result.get('failed', [])
    failed_path = os.path.join(out, 'failed.json')
    json.dump(failed, open(failed_path, 'w'))
    print('editor: %s; failed: %s' % (result.get('build'), ', '.join(failed) or 'none'))

    chunk = os.path.join(staged, 'pakchunk47-WindowsNoEditor')
    moves_dir = os.path.join(out, 'moves')
    plan = json.load(open(MOVES_JSON))
    skip_path = os.path.join(out, 'left_out_packages.json')   # (moves the editor could not build stay out of the container)
    json.dump([PREFIX + '%s/%s.uasset' % (m['set'], m['name']) for m in plan['moves'] if m['build'] and m['name'] in failed], open(skip_path, 'w'))
    subprocess.check_call([sys.executable, ALIGN, chunk + '.utoc', moves_dir, 'SephirothForms_P', chunk + '.pak', PREFIX, skip_path])

    new = packages(os.path.join(moves_dir, 'SephirothForms_P.utoc'))
    old = packages(INSTALLED_MOVES)
    lost = sorted(old - new)
    assert not lost, '%d package(s) of the installed container are missing: %s' % (len(lost), ', '.join(lost[:10]))
    want = {PREFIX + 'Battle05/%s.uasset' % m['name'] for m in plan['moves'] if m['build'] and m['name'] not in failed}
    missing = sorted(w for w in want if w not in new)
    assert not missing, '%d built Battle05 move(s) are not in the container: %s' % (len(missing), ', '.join(missing[:10]))
    # every move the container holds is an ACL clip (the game reads every animation as ACL_0)
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
    extra = sorted(p for p in new - old if not p.startswith(PREFIX + 'Battle05/'))
    print('container: %d packages (%d before; Battle05: %d; other new: %s)'
          % (len(new), len(old), sum(1 for p in new if p.startswith(PREFIX + 'Battle05/')), ', '.join(extra[:12]) or 'none'))

    json_dir = os.path.join(out, 'json')
    os.makedirs(json_dir)
    subprocess.check_call([sys.executable, os.path.join(HERE, 'compose_forms36.py'), INSTALLED_JSON, MOVES_JSON,
                           os.path.join(json_dir, 'SephirothForms.json'), os.path.join(json_dir, 'forms_import.json'), failed_path])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
