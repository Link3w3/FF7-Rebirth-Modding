"""After run_safer_update.cmd (editor 1.12.3, game mod 3.6.6): Safer Sephiroth's containers and compat files.
  1. SephirothForms_P: pakchunk47 laid out like the game's animations (align_only.py: only RebirthSkelCompat/Built/
     SephirothForms/): every form's moves, with the 78 walks and runs of the lean fix and Safer's 27 new moves; checks:
     every package of the installed container is still there, every move the editors built is there, all ACL,
  2. SaferSephiroth_P: the packages of pakchunk49 the game does not have (his model folder: the model with his regular
     Bonamik PC0010_999_BNM_Regular, the skeleton, the materials and textures, and what they use that is not the game's),
     plus his AnimBlueprint v3 (make_safer_abp_v3.py); checks: every package they import is in it, in the game or in his
     moves; the Bonamik is in it,
  3. SephirothForms.json: the installed one with Battle06's new moves (Bizarro's abilities' names; the gates chained with
     their end), Battle06's abilities (Battle05's: Bizarro's), the SAFER form's entrance and its conjured swords,
  4. SaferSephiroth.json: the installed one with stand-ins for the sockets Bizarro's damage sources and attacks use.
    post_update.py <staged dir: pakchunk47 / pakchunk49-WindowsNoEditor.{pak,ucas,utoc}, safer_update_result.json> <out dir (new)>"""
import copy, gzip, json, os, shutil, subprocess, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools', '/work/sephforms/tools',
                '/work/vincentfix', '/work/weap1012/tools', '/work/evil1013/tools',
                '/work/safer1015/tools']
from iostore import Toc
import iostore_write as W
import hdr
import post_safer as P

INSTALLED_MOVES = '/work/safer1015/post1/moves/SephirothForms_P.utoc'      # = the game's ~mods copy (utoc f9d77e52)
INSTALLED_JSON = '/work/safer1015/post1/json/SephirothForms.json'          # = the game's compat copy (ad382678)
INSTALLED_SOCKETS = '/work/safer1016/json/SaferSephiroth.installed.json'   # = the game's compat copy (5da4ac56)
ATB_MOVES = '/work/safer1016/json/safer_atb_moves.json'                    # (the PC's safer\\safer_atb_moves.json)
ABP3 = '/work/safer1015/abp3/PC0010_999_Safer_Sephiroth_Standard_Animation.uasset'
BONAMIK = 'Character/Player/PC0010_999_Safer_Sephiroth/Model/PC0010_999_BNM_Regular.uasset'
BUILT = P.BUILT
EB = '/Game/Effect/Character/Enemy/EB2210_BizarroSephiroth/Particle/'
SAFER_ENTRANCE = {
    'animation': BUILT + 'Battle06/B_SaferEnter01.B_SaferEnter01',
    'slot': 'DefaultSlot',
    'flash': 1.6,
    'descend': 1200,
    'descend_seconds': 5.6,
    'effects': [
        {'effect': '/Game/Effect/Character/Player/PC0010_Sephiroth/Particle/FX_PC0010_Warp_FadeApp_01.FX_PC0010_Warp_FadeApp_01', 'socket': 'C_Spine_c', 'scale': 2.5, 'seconds': 3.0},
        {'effect': '/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Particle/FX_PC0010_10_Tenshi_Area_01.FX_PC0010_10_Tenshi_Area_01', 'scale': 1.5, 'seconds': 4.0},
    ],
    'camera': {'face': 'C_Nose_A', 'distance': 900, 'side': 150, 'height': 40, 'fov': 70, 'close_at': 0.65, 'close': 180, 'close_fov': 30,
               'hold': 0.6, 'blend_back': 1.0, 'bars': 2.39},
    'hold_input': True,
    'skip': True,
}
# his conjured swords in Bizarro's sword abilities (as the BIZARRO form has them; his model is 0.4 of its size, Bizarro's 0.1)
SAFER_ABILITY_EFFECTS = [
    {'abilities': ['PC0010_BZ_Octaslash'], 'effects': [{'effect': EB + 'FX_EB2210_OmniSlash_Sword_01.FX_EB2210_OmniSlash_Sword_01', 'socket': 'Attack_Sword', 'scale': 0.25}]},
    {'abilities': ['PC0010_BZ_Zanshin', 'PC0010_BZ_ZanshinProfaned'],
     'effects': [{'effect': EB + 'FX_EB2210_LongSword_Sword_01.FX_EB2210_LongSword_Sword_01', 'socket': 'Attack_Sword', 'scale': 0.25}]},
]
# the sockets Bizarro's damage sources and attacks are made at, on Safer's bones
SOCKETS_ADD = {
    'Attack_Sword': 'L_Weapon_a', 'Attack_RightHand': 'R_Hand_a', 'Attack_LeftHand': 'L_Hand_a',
    'Attack_ZanshinL': 'L_Hand_a', 'Attack_ZanshinR': 'R_Hand_a', 'Attack_ZanshinCenter': 'C_Spine_d',
    'Attack_Angel': 'C_HaloFront_a', 'Attack_Claw_EndR': 'R_Hand_a', 'Attack_Claw_EndL': 'L_Hand_a',
    'R_Claw_a': 'R_Hand_a', 'L_Claw_a': 'L_Hand_a', 'Gokumon_Attach': 'C_Hip_a',
    'C_SmlSpine_c': 'C_Spine_c', 'C_SmlHead_a': 'C_Head_a',
    'Core_Laser': 'C_Spine_d', 'Core_Smoke1': 'C_Spine_c', 'EyeLaser': 'C_Head_a', 'Stigma': 'C_Spine_d',
    'WingTornado1': 'L_WingA_c', 'WingTornado2': 'R_WingA_c', 'WingTornado3': 'L_WingB_c', 'WingTornado4': 'R_WingB_c',
}
SOURCE_ADD = (" In SAFER his commands are Bizarro's abilities (Bizarro's animations moving his upper body as the little "
              "Sephiroth on Bizarro's head moves), and switching to it plays his entrance: a white flash, he comes down from the "
              "sky in his cutscene animation, the camera low and looking up at him, ending close on his face.")


def model_container(staged, out, game, moves_packages):
    """pakchunk49's packages of his (not the game's, not moves) and his AnimBlueprint v3, as SaferSephiroth_P."""
    src = Toc(os.path.join(staged, 'pakchunk49-WindowsNoEditor.utoc'))
    heads = [i for i in range(src.entries) if src.chunk_type(i) == 10]
    assert len(heads) == 1
    _, store = hdr.parse_header(src.read(heads[0]))
    by_pid = {}
    for i in range(src.entries):
        if src.chunk_type(i) == 2:
            path = src.files.get(i)
            assert path and path.startswith(P.MOUNT), path
            by_pid[src.chunk_id64(i)] = path[len(P.MOUNT):]
    kept, dropped, odd, elsewhere = set(), [], [], []
    for pid, path in by_pid.items():
        if path.startswith(('RebirthSkelCompat/', 'Motion/')) or path in moves_packages:
            elsewhere.append(path)
        elif path.startswith(P.SAFER_PREFIX) or path not in game:
            kept.add(pid)
            if not path.startswith(P.SAFER_PREFIX):
                odd.append(path)
        else:
            dropped.append(path)
    assert kept, 'pakchunk49 has none of his packages'
    assert BONAMIK in {by_pid[p] for p in kept}, 'his regular Bonamik is not in pakchunk49'
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
        chunks.append(dict(id64=pid, type=kind, data=src.read(i), path=path[len(P.MOUNT):] if path else None))
        kinds[kind] = kinds.get(kind, 0) + 1
        if kind == 2:
            se = store[pid]
            entries.append(dict(id=pid, size=se['size'], export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                                load_order=se['load_order'], imports=list(se['imports'])))
    import make_safer_abp_v3
    abp, abp_entry = make_safer_abp_v3.make()
    assert abp == open(ABP3, 'rb').read(), 'the AnimBlueprint differs from ' + ABP3
    abp_pid = W.package_id(P.ABP_PKG)
    assert abp_pid not in kept and abp_entry['id'] == abp_pid
    chunks.append(dict(id64=abp_pid, type=2, data=abp, path=P.ABP_PKG[len('/Game/'):] + '.uasset'))
    entries.append(abp_entry)
    here = {e['id'] for e in entries}
    game_ids = P.game_package_ids()
    moves_ids = {W.package_id(P.content_to_package(p)) for p in moves_packages}
    unknown = sorted({'%016x (imported by %s)' % (imp, by_pid.get(e['id'], P.ABP_PKG)) for e in entries for imp in e['imports']
                      if imp not in here and imp not in game_ids and imp not in moves_ids})
    assert not unknown, '%d imported package(s) are nowhere: %s' % (len(unknown), '; '.join(unknown[:10]))
    assert W.package_id('/Game/' + P.SAFER_PREFIX + 'Model/PC0010_999_Skeleton') in here, 'his skeleton is not in it'
    cid = W.container_id_from_name(P.MODEL_NAME)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    model_dir = os.path.join(out, 'model')
    os.makedirs(model_dir)
    base = os.path.join(model_dir, P.MODEL_NAME)
    W.write_container(base, P.MODEL_NAME, chunks, mount=P.MOUNT)
    shutil.copy(os.path.join(staged, 'pakchunk49-WindowsNoEditor.pak'), base + '.pak')
    back = Toc(base + '.utoc')
    assert back.entries == len(chunks)
    _, ents = hdr.parse_header(back.read(0))
    assert set(ents) == here
    for i in range(1, back.entries):
        c = chunks[i]
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        if c['path']:
            assert back.files.get(i) == P.MOUNT + c['path'], (back.files.get(i), c['path'])
    names = sorted(by_pid[p] for p in kept)
    print('model: %d packages of his + his AnimBlueprint v3; chunks by type %s; left out (the game\'s): %d; elsewhere (moves): %d%s'
          % (len(kept), kinds, len(dropped), len(elsewhere), ('; not in his folder but not the game\'s: ' + ', '.join(sorted(odd)[:12])) if odd else ''))
    json.dump({'kept': names, 'dropped': sorted(dropped), 'outside_his_folder': sorted(odd)}, open(os.path.join(out, 'model_packages.json'), 'w'), indent=1)
    return names


def move_entry(m, made):
    """The compat file's entry of a built move (its "build": what the editor made it of, for reference)."""
    build = {'from': m['animation'], 'notifies_from': m['notifies_from']}
    for key in ('clip', 'speed', 'base', 'bone_map', 'source_turn'):
        if m.get(key):
            build[key] = m[key]
    if m.get('retarget'):
        build['retarget'] = m['retarget']
    if m.get('keep_base_root'):
        build['keep_root'] = True
    if m.get('source_sounds_only'):
        build['source_sounds_only'] = True
    path = BUILT + m['set'] + '/' + m['name'] + '.' + m['name']
    if made and path in made:
        build['length'] = round(made[path].get('length', 0.0), 4)
    return {'set': m['set'], 'key': m['name'], 'animation': path, 'build': build}


def compat(out, failed, atb, made):
    j = json.load(open(INSTALLED_JSON))
    row = j['animation_sets'][0]
    keys = {(m['set'], m['key']) for m in row['moves']}
    added, chained, left = [], [], []
    by_name = {m['name']: m for m in atb['moves']}
    for m in atb['moves']:
        if m['kind'] in ('gate_end', 'entrance'):
            continue   # (played by chains and the entrance, not by name)
        if m['name'] in failed:
            left.append(m['name'])
            continue
        assert (m['set'], m['name']) not in keys, ('the installed compat file has', m['set'], m['name'])
        entry = move_entry(m, made)
        then = atb['chains'].get(m['name'])
        if then:
            if any(t in failed for t in then):
                left.append(m['name'] + ' (its end did not build)')
                continue
            entry['animation'] = [entry['animation']] + [BUILT + by_name[t]['set'] + '/' + t + '.' + t for t in then]
            chained.append(m['name'])
        added.append(entry)
    row['moves'] += added
    # Battle06's abilities: Bizarro's (Battle05's)
    packs = [a['pack'] for a in row['abilities']]
    assert 'Battle05' in packs and 'Battle06' not in packs, packs
    b6 = copy.deepcopy([a for a in row['abilities'] if a['pack'] == 'Battle05'][0])
    b6['pack'] = 'Battle06'
    row['abilities'].append(b6)
    # the SAFER form: its entrance (when its animation built) and its conjured swords
    safer = [f for f in row['forms']['list'] if f.get('name') == 'SAFER']
    assert len(safer) == 1
    entrance = copy.deepcopy(SAFER_ENTRANCE)
    if atb['entrance'] in failed:
        del entrance['animation']   # (the flash, the descent and the camera, without the animation)
    safer[0]['entrance'] = entrance
    safer[0]['ability_effects'] = copy.deepcopy(SAFER_ABILITY_EFFECTS)
    for key in ('model_turn', 'model_lift'):
        safer[0].pop(key, None)   # (editor only: the moves are built turned and lifted)
    if SOURCE_ADD.strip() not in j['source']:
        j['source'] += SOURCE_ADD
    json_dir = os.path.join(out, 'json')
    os.makedirs(json_dir, exist_ok=True)
    path = os.path.join(json_dir, 'SephirothForms.json')
    json.dump(j, open(path, 'w'), indent=1)
    sets = {}
    for m in row['moves']:
        sets[m['set']] = sets.get(m['set'], 0) + 1
    print('compat: %d moves (%s); Battle06 +%d (%d chained: %s); left out: %s; abilities: %s; SAFER entrance %s'
          % (len(row['moves']), sets, len(added), len(chained), ', '.join(chained), ', '.join(left) or 'none',
             [a['pack'] for a in row['abilities']], 'with its animation' if 'animation' in entrance else 'WITHOUT its animation'))
    return path


def sockets(out):
    j = json.load(open(INSTALLED_SOCKETS))
    row = j['animation_sets'][0]
    have = row['sockets']
    added = {k: v for k, v in SOCKETS_ADD.items() if k not in have}
    have.update(added)
    if "Bizarro's" not in j['source']:
        j['source'] += " Bizarro Sephiroth's (his abilities' damage sources, swords and beams) stand in on his bones too."
    path = os.path.join(out, 'json', 'SaferSephiroth.json')
    json.dump(j, open(path, 'w'), indent=1)
    print('sockets: %d (+%d: %s)' % (len(have), len(added), ', '.join(sorted(added))))
    return path


def main(staged, out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    os.makedirs(out)
    result = json.load(open(os.path.join(staged, 'safer_update_result.json')))
    assert 'error' not in result, result['error']
    assert result.get('done'), 'the editor step did not finish'
    failed = set(result.get('failed', []))
    print('editor: %s; failed: %s' % (result.get('build'), ', '.join(sorted(failed)) or 'none'))
    made_path = os.path.join(staged, 'safer_atb_built.json')
    made = json.load(open(made_path)) if os.path.exists(made_path) else {}
    atb = json.load(open(ATB_MOVES))
    bizarro = json.load(open(P.BIZARRO_MOVES))
    bizarro_lean = [m for m in bizarro['moves'] if m['build'] and m.get('retarget') == 'lean']
    assert len(bizarro_lean) == 39, len(bizarro_lean)
    safer = json.load(open(P.SAFER_MOVES))['moves']
    safer_built = [m for m in safer if m['build']] + [m for m in atb['moves'] if m['build'] and m['name'] not in failed]
    P.INSTALLED_MOVES = INSTALLED_MOVES
    moves_packages = P.moves_container(staged, out, failed, bizarro_lean, safer_built)
    model_container(staged, out, P.game_packages(), moves_packages)
    compat(out, failed, atb, made)
    sockets(out)


if __name__ == '__main__':
    main(*sys.argv[1:3])
