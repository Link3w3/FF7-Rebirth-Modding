"""After run_safer_form.cmd (the Safer form, editor 1.12.1): Safer Sephiroth's containers and the compat file.
  1. SephirothForms_P: pakchunk47 laid out like the game's animations (align_only.py: only RebirthSkelCompat/Built/
     SephirothForms/): every form's built moves, with Bizarro's built movement (Battle05) and Safer's moves (Battle06);
     checks: every package of the installed container is still there, every move the editors built is there, all ACL,
  2. SaferSephiroth_P: the packages of pakchunk49 the game does not have (his model folder: the model, skeleton, physics,
     materials and textures, and what they use that is not the game's), as cooked, with their bulk data, plus his own
     AnimBlueprint (make_safer_abp.py); checks: every package they import is in it, in the game or in his moves,
  3. SephirothForms.json: the installed one with Battle05's movement moves pointing at the built ones, Battle06's moves
     (the built ones) and the SAFER form (safer\\forms_import.json's).
    post_safer.py <staged dir: pakchunk47 / pakchunk49-WindowsNoEditor.{pak,ucas,utoc}, safer_result.json> <out dir (new)>"""
import gzip, json, os, shutil, struct, subprocess, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools', '/work/sephforms/tools',
                '/work/vincentfix', '/work/weap1012/tools', '/work/evil1013/tools',
                '/work/safer1015/tools']
from iostore import Toc
import iostore_write as W
import hdr
from zen import Zen

ALIGN = '/work/bizsum1015/tools/align_only.py'
INSTALLED_MOVES = '/work/forms36/post2/out/moves/SephirothForms_P.utoc'   # = the game's ~mods copy (md5 bc69b41c)
INSTALLED_JSON = '/work/forms36/post3/SephirothForms.json'                # = the game's compat copy (md5 9ca02001)
BIZARRO_MOVES = '/work/bizmoves1015/bizarro_moves.json'                    # (the PC's bizarro\bizarro_moves.json)
SAFER_MOVES = '/work/safer1015/json/safer_moves.json'
SAFER_FORMS = '/work/safer1015/json/forms_import.json'
ABP = '/work/safer1015/abp/PC0010_999_Safer_Sephiroth_Standard_Animation.uasset'
ABP_PKG = '/Game/BluePrint/Animation/Player/PC0010_999_Safer_Sephiroth_Standard_Animation'
GAME_FILES = '/work/gamelist/gamefiles.txt.gz'
MOUNT = '../../../End/Content/'
MARKER = bytes([0x30, 0xAF, 0x2F, 0x90, 0x54, 0x94, 0xF4, 0x06, 0x59, 0x00, 0x49, 0x00, 0x49, 0x00, 0x53, 0x00])
ACL_TAG = (0xAC10AC10).to_bytes(4, 'little')
PREFIX = 'RebirthSkelCompat/Built/SephirothForms/'
BUILT = '/Game/' + PREFIX
SAFER_PREFIX = 'Character/Player/PC0010_999_Safer_Sephiroth/'
MODEL_NAME = 'SaferSephiroth_P'
MOVES_NAME = 'SephirothForms_P'
SOURCE_ADD = (" The sixth form is SAFER (Battle06: he becomes Safer Sephiroth, his model and his own AnimBlueprint from "
              "SaferSephiroth_P, his moves made of Safer's animations with his hits struck from Safer's wing, hand and body, his "
              "walks and runs Safer's idle leaning into Sephiroth's flying locomotion; super armor; it lasts 60 s, then 30 s before "
              "it can be chosen again).")


def packages(utoc):
    t = Toc(utoc)
    return {p[len(MOUNT):] for p in t.files.values() if p and p.startswith(MOUNT)}


def game_packages():
    out = set()
    for line in gzip.open(GAME_FILES, 'rt'):
        p = line.rstrip('\n').split('\t')[-1]
        if p.startswith(MOUNT):
            out.add(p[len(MOUNT):])
    return out


def game_package_ids():
    """Package ids of every package of the game's own containers: its content (/Game), the engine's (/Engine) and its
    plugins' (/<Plugin>)."""
    out = set()
    for line in gzip.open(GAME_FILES, 'rt'):
        p = line.rstrip('\n').split('\t')[-1]
        if not p.endswith(('.uasset', '.umap')) or not p.startswith('../../../'):
            continue
        top, sub = p[len('../../../'):].split('/', 1)
        if sub.startswith('Content/'):
            mount = '/Game/' if top == 'End' else '/' + top + '/'
            out.add(W.package_id(mount + sub[len('Content/'):].rsplit('.', 1)[0]))
        elif '/Content/' in sub:
            plugin = sub.split('/Content/')[0].split('/')[-1]
            out.add(W.package_id('/' + plugin + '/' + sub.split('/Content/', 1)[1].rsplit('.', 1)[0]))
    return out


def content_to_package(path):
    return '/Game/' + path.rsplit('.', 1)[0]


def build_entry(m, retarget_lean):
    build = {'from': m['animation'], 'notifies_from': m['notifies_from']}
    if m.get('hits'):
        build['hits'] = [dict({'time': h['time']}, **({'damage': h['damage']} if h.get('damage') else {})) for h in m['hits']]
    if m.get('clip'):
        build['clip'] = m['clip']
    if m.get('speed'):
        build['speed'] = m['speed']
    if retarget_lean:
        build['retarget'] = 'lean'
        build['base'] = m['base']
        if m.get('base_loop'):
            build['base_loop'] = True
        if m.get('lean_bone'):
            build['lean_bone'] = m['lean_bone']
        build['lean'] = m.get('lean', 18.0)
    return {'set': m['set'], 'key': m['name'], 'animation': BUILT + m['set'] + '/' + m['name'] + '.' + m['name'], 'build': build}


def moves_container(staged, out, failed, bizarro_lean, safer_built):
    chunk = os.path.join(staged, 'pakchunk47-WindowsNoEditor')
    moves_dir = os.path.join(out, 'moves')
    skip_path = os.path.join(out, 'left_out_packages.json')   # (moves the editor could not build stay out)
    json.dump([PREFIX + 'Battle06/%s.uasset' % name for name in sorted(failed)], open(skip_path, 'w'))
    subprocess.check_call([sys.executable, ALIGN, chunk + '.utoc', moves_dir, MOVES_NAME, chunk + '.pak', PREFIX, skip_path])
    new = packages(os.path.join(moves_dir, MOVES_NAME + '.utoc'))
    old = packages(INSTALLED_MOVES)
    lost = sorted(old - new)
    assert not lost, '%d package(s) of the installed container are missing: %s' % (len(lost), ', '.join(lost[:10]))
    want = {PREFIX + 'Battle05/%s.uasset' % m['name'] for m in bizarro_lean} | {PREFIX + 'Battle06/%s.uasset' % m['name'] for m in safer_built}
    missing = sorted(w for w in want if w not in new)
    assert not missing, '%d built move(s) are not in the container: %s' % (len(missing), ', '.join(missing[:10]))
    toc = Toc(os.path.join(moves_dir, MOVES_NAME + '.utoc'))
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
    extra = sorted(p for p in new - old if p not in want)
    print('moves: %d packages (%d before; Battle06 %d, Battle05 movement %d; other new: %s); ACL: every package'
          % (len(new), len(old), sum(1 for p in new if p.startswith(PREFIX + 'Battle06/')), len(bizarro_lean), ', '.join(extra[:12]) or 'none'))
    return new


def model_container(staged, out, game, moves_packages):
    src_path = os.path.join(staged, 'pakchunk49-WindowsNoEditor.utoc')
    src = Toc(src_path)
    heads = [i for i in range(src.entries) if src.chunk_type(i) == 10]
    assert len(heads) == 1
    _, store = hdr.parse_header(src.read(heads[0]))
    by_pid = {}
    for i in range(src.entries):
        if src.chunk_type(i) == 2:
            path = src.files.get(i)
            assert path and path.startswith(MOUNT), path
            by_pid[src.chunk_id64(i)] = path[len(MOUNT):]
    kept, dropped, odd, elsewhere = set(), [], [], []
    for pid, path in by_pid.items():
        if path.startswith(('RebirthSkelCompat/', 'Motion/')) or path in moves_packages:
            elsewhere.append(path)   # (moves are SephirothForms_P's; his own animations are only what moves are built from)
        elif path.startswith(SAFER_PREFIX) or path not in game:
            kept.add(pid)
            if not path.startswith(SAFER_PREFIX):
                odd.append(path)
        else:
            dropped.append(path)
    assert kept, 'pakchunk49 has none of his packages'
    if elsewhere:
        print('  left out (moves, animations): %d (e.g. %s)' % (len(elsewhere), ', '.join(sorted(elsewhere)[:6])))
    chunks, entries, kinds = [None], [], {}
    for i in range(src.entries):
        kind = src.chunk_type(i)
        if kind == 10:
            continue
        pid = src.chunk_id64(i)
        if pid not in kept:
            continue
        raw = src.chunk_ids[i]
        assert raw[8:11] == b'\0\0\0', ('a chunk index this writer does not keep', src.files.get(i), raw.hex())
        path = src.files.get(i)
        chunks.append(dict(id64=pid, type=kind, data=src.read(i), path=path[len(MOUNT):] if path else None))
        kinds[kind] = kinds.get(kind, 0) + 1
        if kind == 2:
            se = store[pid]
            entries.append(dict(id=pid, size=se['size'], export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                                load_order=se['load_order'], imports=list(se['imports'])))
    # his AnimBlueprint
    import make_safer_abp
    abp, abp_entry = make_safer_abp.make()
    assert abp == open(ABP, 'rb').read(), 'the AnimBlueprint differs from ' + ABP
    abp_pid = W.package_id(ABP_PKG)
    assert abp_pid not in kept and abp_entry['id'] == abp_pid
    chunks.append(dict(id64=abp_pid, type=2, data=abp, path=ABP_PKG[len('/Game/'):] + '.uasset'))
    entries.append(abp_entry)
    # every package they import: here, the game's or his moves'
    here = {e['id'] for e in entries}
    game_ids = game_package_ids()
    moves_ids = {W.package_id(content_to_package(p)) for p in moves_packages}
    unknown = sorted({'%016x (imported by %s)' % (imp, by_pid.get(e['id'], ABP_PKG)) for e in entries for imp in e['imports']
                      if imp not in here and imp not in game_ids and imp not in moves_ids})
    assert not unknown, '%d imported package(s) are nowhere: %s' % (len(unknown), '; '.join(unknown[:10]))
    assert all(W.package_id('/Game/' + SAFER_PREFIX + 'Model/PC0010_999_Skeleton') in here for _ in [0]), 'his skeleton is not in it'
    cid = W.container_id_from_name(MODEL_NAME)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    model_dir = os.path.join(out, 'model')
    os.makedirs(model_dir)
    base = os.path.join(model_dir, MODEL_NAME)
    W.write_container(base, MODEL_NAME, chunks, mount=MOUNT)
    shutil.copy(os.path.join(staged, 'pakchunk49-WindowsNoEditor.pak'), base + '.pak')
    back = Toc(base + '.utoc')
    assert back.entries == len(chunks)
    _, ents = hdr.parse_header(back.read(0))
    assert set(ents) == here
    for i in range(1, back.entries):
        c = chunks[i]
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        if c['path']:
            assert back.files.get(i) == MOUNT + c['path'], (back.files.get(i), c['path'])
    names = sorted(by_pid[p] for p in kept)
    classes = {}
    for p in names:
        folder = p[len(SAFER_PREFIX):].split('/')[0] if p.startswith(SAFER_PREFIX) else '(elsewhere)'
        classes[folder] = classes.get(folder, 0) + 1
    print('model: %d packages of his (%s) + his AnimBlueprint; chunks by type %s; left out (the game\'s): %d%s'
          % (len(kept), ', '.join('%s %d' % kv for kv in sorted(classes.items())), kinds, len(dropped),
             (' (e.g. ' + ', '.join(sorted(dropped)[:6]) + ')') if dropped else ''))
    if odd:
        print('  not in his folder but not the game\'s (kept): ' + ', '.join(sorted(odd)[:20]))
    json.dump({'kept': names, 'dropped': sorted(dropped), 'outside_his_folder': sorted(odd)}, open(os.path.join(out, 'model_packages.json'), 'w'), indent=1)
    return names


def compat(out, failed, bizarro_lean, safer_moves):
    j = json.load(open(INSTALLED_JSON))
    row = j['animation_sets'][0]
    by_key = {(m['set'], m['key']): i for i, m in enumerate(row['moves'])}
    changed = 0
    for m in bizarro_lean:
        at = by_key.get(('Battle05', m['name']))
        assert at is not None, 'the installed compat file has no Battle05 ' + m['name']
        row['moves'][at] = build_entry(dict(m, set='Battle05'), True)
        changed += 1
    assert not any(m['set'] == 'Battle06' for m in row['moves']), 'already has Battle06 moves'
    added = [build_entry(m, m.get('retarget') == 'lean') for m in safer_moves if m['build'] and m['name'] not in failed]
    row['moves'] += added
    forms = json.load(open(SAFER_FORMS))['animation_sets'][0]['forms']
    names = [f['name'] for f in forms['list']]
    assert names == [f['name'] for f in row['forms']['list']] + ['SAFER'], names
    for a, b in zip(forms['list'][:-1], row['forms']['list']):
        assert a == b, ('a form differs from the installed one', a['name'])
    row['forms'] = forms
    if 'SAFER' not in j['source']:
        text = j['source'].replace('has five forms on the forms menu', 'has six forms on the forms menu', 1)
        j['source'] = text.replace(' His limits are', SOURCE_ADD + ' His limits are', 1) if ' His limits are' in text else text + SOURCE_ADD
    json_dir = os.path.join(out, 'json')
    os.makedirs(json_dir)
    path = os.path.join(json_dir, 'SephirothForms.json')
    json.dump(j, open(path, 'w'), indent=1)
    sets = {}
    for m in row['moves']:
        sets[m['set']] = sets.get(m['set'], 0) + 1
    print('compat: %d moves (%s); Battle05 movement now built: %d; Battle06: %d; forms %s' % (len(row['moves']), sets, changed, len(added), names))
    return path


def main(staged, out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    os.makedirs(out)
    result = json.load(open(os.path.join(staged, 'safer_result.json')))
    assert 'error' not in result, result['error']
    assert result.get('done'), 'the editor step did not finish'
    failed = set(result.get('failed', []))
    print('editor: %s; failed: %s; label: %s' % (result.get('build'), ', '.join(sorted(failed)) or 'none', result.get('label')))
    bizarro = json.load(open(BIZARRO_MOVES))
    bizarro_lean = [m for m in bizarro['moves'] if m['build'] and m.get('retarget') == 'lean']
    assert len(bizarro_lean) == 39, len(bizarro_lean)
    safer = json.load(open(SAFER_MOVES))['moves']
    safer_built = [m for m in safer if m['build'] and m['name'] not in failed]
    moves_packages = moves_container(staged, out, failed, bizarro_lean, safer_built)
    model_container(staged, out, game_packages(), moves_packages)
    compat(out, failed, bizarro_lean, safer)


if __name__ == '__main__':
    main(*sys.argv[1:3])
