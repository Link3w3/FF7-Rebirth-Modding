"""His KH2 form's data: FullyPlayableSephirothDataAssets_P (the installed Meteor build, meteor1014c/out1) with 'Battle04' in
the AnimationSetList of his 9 CharaSpec rows (a free slot), so the game makes the KH2 form's pack, and SephirothForms.json
with the KH2 form (his Battle00 + Battle00_Comp as Battle04, its built moves), the Meteor cast (KH2 MASAFINISH, built in
Battle04) in every form and his body aura preloaded (MeteorStrike.lua turns it pink while he flies).
    build_kh2data.py <out dir> <installed json> <editor export json> <kh2_result.json>"""
import json, os, shutil, sys, io, contextlib
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools']
import build_atb as B
from iostore import Toc
import iostore_write as W
from hdr import parse_header

NAME = B.NAME
BASE = '/work/kh2data1014/out1/' + NAME   # the installed KH2 build (Battle04 in slot 9)
MOUNT = B.MOUNT
SET = 'Battle04'
SLOTS = [5, 3]
ROWS = ['PC0000_00_Cloud_Standard', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing', 'PC0000_10_Cloud_CostaClothing2',
        'PC0000_04_Cloud_ZackCostume', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
        'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']
CAST_KEY = 'B_AtkLimit03_0'
CAST = '/Game/RebirthSkelCompat/Built/SephirothForms/Battle04/B_AtkLimit03_0.B_AtkLimit03_0'
CAST_SETS = ['Battle00', 'Battle02', 'Battle03']   # (Battle04 has it from the export)
PRELOAD = ['/Game/Effect/Character/Player/PC0010_Sephiroth/Particle/FX_PC0010_Aura_Body_01.FX_PC0010_Aura_Body_01',
           # the Meteor crater from Titan (MeteorStrike.lua): his rocks, the game's ground crack, his rock burst, shock and smoke
           '/Game/Effect/Character/Summon/SU2000_Titan/Model/FX_SU2000_Rock_01.FX_SU2000_Rock_01',
           '/Game/Effect/Character/Summon/SU2000_Titan/Model/FX_SU2000_Rock_Red_01.FX_SU2000_Rock_Red_01',
           '/Game/Effect/Character/Summon/SU2000_Titan/Model/FX_SU2000_Rock_Red_02.FX_SU2000_Rock_Red_02',
           '/Game/Environment/Building/Model/Decal_B_GroundCrack_01A.Decal_B_GroundCrack_01A',
           '/Game/Effect/Character/Summon/SU2000_Titan/Particle/FX_SU2000_RockThrow_Storm_01.FX_SU2000_RockThrow_Storm_01',
           '/Game/Effect/Character/Summon/SU2000_Titan/Particle/FX_SU2000_JumpPunch_Shock_01.FX_SU2000_JumpPunch_Shock_01',
           '/Game/Effect/Character/Summon/SU2000_Titan/Particle/FX_SU2000_Common_Smoke_01.FX_SU2000_Common_Smoke_01']
SOURCES = ['/Game/Motion/Player/PC0010_Sephiroth/Battle00.Battle00', '/Game/Motion/Player/PC0010_Sephiroth/Battle00_Comp.Battle00_Comp']


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def build_container(out_dir):
    base = Toc(BASE + '.utoc')
    head = [i for i in range(base.entries) if base.chunk_type(i) == 10]
    cid, base_entries = parse_header(base.read(head[0]))
    chunks, entries = [None], []
    for i in range(base.entries):
        if base.chunk_type(i) != 2:
            continue
        path = base.files[i].replace(MOUNT, '', 1)
        pid = base.chunk_id64(i)
        e = base_entries[pid]
        chunks.append(dict(id64=pid, type=2, data=base.read(i), path=path))
        entries.append(dict(id=pid, size=e['size'], export_count=e['export_count'], export_bundle_count=e['export_bundle_count'],
                            load_order=e['load_order'], imports=e['imports']))
    paths = [c['path'] for c in chunks[1:]]
    k = paths.index(B.CHARASPEC_TABLE) + 1
    cs = quiet(B.Table, chunks[k]['data'])
    for name in ROWS:
        row = cs.row(name)
        sets = cs.get(row, 'AnimationSetList_Array')
        used = {cs.get(row, f) for f in ('GroundAnimationBattlePackIndex', 'GroundAnimationFieldPackIndex', 'FlyAnimationBattlePackIndex',
                                         'FlyAnimationFieldPackIndex')}
        before = list(sets)
        # Slot 9 is one the game never uses (no row of the game has a set there) and a set there is not taken: the
        # KH2 form goes in a free slot the game does use for battle sets (5, else 3).
        sets = [None if v == SET else v for v in sets]
        free = [i for i in SLOTS if i < len(sets) and sets[i] is None and i not in used]
        if not free:
            raise SystemExit('%s: no free slot among %s: %s' % (name, SLOTS, sets))
        sets[free[0]] = SET
        cs.set(row, 'AnimationSetList_Array', sets)
        print('%s: %s -> %s' % (name, before, sets))
    data = cs.encode()
    chunks[k]['data'] = data
    entries[k - 1]['size'] = len(data)
    cid2 = W.container_id_from_name(NAME)
    assert cid2 == cid
    chunks[0] = dict(id64=cid2, type=10, data=W.container_header(cid2, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    outb = os.path.join(out_dir, NAME)
    W.write_container(outb, NAME, chunks, mount=MOUNT)
    shutil.copy(BASE + '.pak', outb + '.pak')
    # read back: every chunk as written, the CharaSpec rows as wanted, every other row and table unchanged
    back = Toc(outb + '.utoc')
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
    cs0 = quiet(B.Table, base.read([i for i in range(base.entries) if base.files.get(i) == MOUNT + B.CHARASPEC_TABLE][0]))
    cs1 = quiet(B.Table, back.read(k))
    assert cs1.keys == cs0.keys
    for key in cs0.at:
        r0, r1 = cs0.row(key), cs1.row(key)
        if key in ROWS:
            s0, s1 = cs0.get(r0, 'AnimationSetList_Array'), cs1.get(r1, 'AnimationSetList_Array')
            assert all(x == y or (x in (None, SET) and y in (None, SET)) for x, y in zip(s0, s1)) and s1.count(SET) == 1, (key, s0, s1)
            fi = cs1.fi['AnimationSetList_Array']
            assert [v for j, v in enumerate(r1) if j != fi] == [v for j, v in enumerate(r0) if j != fi], key
        else:
            assert r1 == r0, key
    print('container: %s (%d chunks), CharaSpec rows with %s: %d' % (outb, len(chunks), SET, len(ROWS)))


def build_json(out_dir, installed, exported, result):
    raw = open(installed, encoding='utf-8').read()
    j = json.loads(raw)
    s = j['animation_sets'][0]
    exp = json.load(open(exported, encoding='utf-8'))['animation_sets'][0]
    failed = set(json.load(open(result)).get('failed', []))
    # the KH2 form's sources (his own Battle00 underneath)
    have = {(b['from'], b['as']) for b in s['battle']}
    for b in exp['battle']:
        if b['as'] == SET and (b['from'], b['as']) not in have:
            s['battle'].append(b)
            have.add((b['from'], b['as']))
    assert all((src, SET) in have for src in SOURCES), 'the KH2 form sources are not in the export'
    # its moves (the ones the build made); moves of the other sets stay as installed
    moves = [m for m in s['moves'] if m['set'] != SET]
    kh2 = [m for m in exp['moves'] if m['set'] == SET and m['key'] not in failed]
    left = sorted(m['key'] for m in exp['moves'] if m['set'] == SET and m['key'] in failed)
    if CAST_KEY in failed:
        raise SystemExit('the Meteor cast was not built')
    moves += kh2
    # the Meteor cast in every form: the KH2 sword raise (built in Battle04, with his spell cast's notifies)
    changed = 0
    for m in moves:
        if m['key'] == CAST_KEY and m['set'] in CAST_SETS:
            m['animation'] = CAST
            m.pop('then_play', None)
            changed += 1
    for set_name in CAST_SETS:
        if not any(m['key'] == CAST_KEY and m['set'] == set_name for m in moves):
            moves.append({'set': set_name, 'key': CAST_KEY, 'animation': CAST})
            changed += 1
    s['moves'] = moves
    for p in PRELOAD:
        if p not in s['preload']:
            s['preload'].append(p)
    j['source'] = j['source'].rstrip('.') + '. KH2 form (Battle04): his Kingdom Hearts II moves; Meteor is cast with the KH2 sword raise in every form.'
    out = os.path.join(out_dir, 'SephirothForms.json')
    open(out, 'w', encoding='utf-8').write(json.dumps(j, indent=1, ensure_ascii=False) + ('\n' if raw.endswith('\n') else ''))
    print('json: %d KH2 moves (left out, not built: %s), the cast in %d sets, preload %d -> %s' % (len(kh2), ', '.join(left) or 'none', changed, len(s['preload']), out))


if __name__ == '__main__':
    if sys.argv[1] == '--json-only':   # the JSON alone (the container as it was)
        out_dir, installed, exported, result = sys.argv[2:6]
        os.makedirs(out_dir, exist_ok=True)
        build_json(out_dir, installed, exported, result)
    else:
        out_dir, installed, exported, result = sys.argv[1:5]
        build_container(out_dir)
        build_json(out_dir, installed, exported, result)
