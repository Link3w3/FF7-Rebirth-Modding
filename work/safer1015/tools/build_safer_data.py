"""Create a Character System 3.6: Safer Sephiroth's data, in FullyPlayableSephirothDataAssets_P (the installed container as
it is, every other package byte for byte):
  * BattleDamageSource: the Safer form's hits (PC0010_SF_*: his Battle06 moves name them on their hits): his own move's
    row (as installed: buffed), struck from where Safer's body strikes (his great right wing, his left hand, his body in a
    lunge, around him, or on the target) instead of from his sword, which the form hides,
  * CharaSpec: his rows list the Safer form's set (Battle06).
    build_safer_data.py <installed container dir> <out dir>"""
import io, contextlib, json, os, shutil, sys
sys.path[:0] = ['/work/forms36/tools', '/work/sephatb/tools', '/work/iostore',
                '/work/cs', '/work/tools', '/work/evil1013/tools', '/work/swap1012/tools',
                '/work/vincentfix', '/work/weap1012/tools']
import build_atb as B
from iostore import Toc
import iostore_write as W
from hdr import parse_header

NAME = B.NAME
MOUNT = B.MOUNT
DAMAGE = 'DataObject/Resident/BattleDamageSource.uasset'
CHARASPEC = 'DataObject/Resident/CharaSpec.uasset'
MOVES = '/work/safer1015/json/safer_moves.json'
SKELETON = '/tmp/scratch/look365/safer_PC0010_999_Skeleton.json'

# Safer's body (PC0010_999_Skeleton; his model at 0.4: the wing from its root to its tip is about 2.3 m, his left forearm
# 0.4 m, his hips 3.3 m up)
GEOMETRY = {
    # skill_005, his wing slash (the wing's tip is the fastest thing in any of his animations)
    'WingR': {'CreateBasePos': 0, 'TargetBase': 0, 'CreatePartName': 'R_HandWing_a', 'TargetName': 'R_HandWing_e', 'CollisionType': 3,
              'CollisionParameter_Array': [200.0, 0.0, 100.0]},
    # skill_003 / skill_004, his left hand
    'HandL': {'CreateBasePos': 0, 'TargetBase': 0, 'CreatePartName': 'L_Forearm_a', 'TargetName': 'L_Hand_a', 'CollisionType': 3,
              'CollisionParameter_Array': [150.0, 0.0, 100.0]},
    # skill_002, his lunge: his body and the hand he leads with
    'Lunge': {'CreateBasePos': 0, 'TargetBase': 0, 'CreatePartName': 'C_Hip_a', 'TargetName': 'L_Hand_a', 'CollisionType': 3,
              'CollisionParameter_Array': [250.0, 0.0, 100.0]},
    # skill_006, his slow cast: a burst around him
    'Around': {'CreateBasePos': 0, 'TargetBase': 0, 'CreatePartName': 'C_Hip_a', 'TargetName': None, 'CollisionType': 2,
               'CollisionParameter_Array': [600.0]},
    # on the target itself (Octaslash's blows, as his own land)
    'Direct': {'CreateBasePos': 10, 'TargetBase': 10, 'CreatePartName': None, 'TargetName': None, 'CollisionType': 0,
               'CollisionParameter_Array': []},
}
OFFSETS = ['CreatePartOffsetX', 'CreatePartOffsetY', 'CreatePartOffsetZ', 'CreatePartOffsetPitch', 'CreatePartOffsetYaw', 'CreatePartOffsetRoll',
           'TargetOffsetX', 'TargetOffsetY', 'TargetOffsetZ']
# new row -> (his move's row, where Safer strikes): as make_safer_moves.py's attacks use his animations
SF_HITS = {
    'PC0010_SF_NAtk_1_01': ('PC0010_NAtk_1_01', 'WingR'),
    'PC0010_SF_NAtk_2_01': ('PC0010_NAtk_2_01', 'HandL'),
    'PC0010_SF_NAtk_3_01': ('PC0010_NAtk_3_01', 'HandL'),
    'PC0010_SF_NAtk_4_01': ('PC0010_NAtk_4_01', 'Lunge'),
    'PC0010_SF_JAtk_1_01': ('PC0010_JAtk_1_01', 'WingR'),
    'PC0010_SF_JAtk_2_01': ('PC0010_JAtk_2_01', 'HandL'),
    'PC0010_SF_JAtk_3_01': ('PC0010_JAtk_3_01', 'HandL'),
    'PC0010_SF_ChainChange01_01': ('PC0010_ChainChange01_01', 'WingR'),
    'PC0010_SF_NPAtk_1_01': ('PC0010_NPAtk_1_04', 'Around'),
    'PC0010_SF_Satk_1_01': ('PC0010_Satk_1_01', 'Lunge'),
    'PC0010_SF_Satk_2_01': ('PC0010_Satk_2_01', 'WingR'),
    'PC0010_SF_Satk_6_01': ('PC0010_Satk_6_01', 'Direct'),
    'PC0010_SF_Satk_8_01': ('PC0010_Satk_8_01', 'HandL'),
    'PC0010_SF_Satk_8_02': ('PC0010_Satk_8_02', 'HandL'),
    'PC0010_SF_Satk_8_03': ('PC0010_Satk_8_03', 'HandL'),
    'PC0010_SF_SAtk_9_01': ('PC0010_SAtk_9_01', 'Lunge'),
    'PC0010_SF_SAtk_9_02': ('PC0010_SAtk_9_02', 'Lunge'),
    'PC0010_SF_SAtk_9_03': ('PC0010_SAtk_9_03', 'HandL'),
    'PC0010_SF_PAtk_1_01': ('PC0010_PAtk_1_01', 'HandL'),
    'PC0010_SF_PAtk_2_01': ('PC0010_PAtk_2_01', 'WingR'),
}
for n in range(1, 9):
    SF_HITS['PC0010_SF_Limit_1_%02d' % n] = ('PC0010_Limit_1_%02d' % n, 'Direct')

# CharaSpec: his rows (Cloud's slot rows that are him)
ROWS = ['PC0000_00_Cloud_Standard', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing', 'PC0000_10_Cloud_CostaClothing2',
        'PC0000_04_Cloud_ZackCostume', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
        'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']
ADD_SETS = ['Battle06']


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def fields(t):
    return [f[0][0] for f in t.fields]


def main(base_dir, out_dir):
    assert not os.path.exists(os.path.join(out_dir, NAME + '.utoc')), out_dir + ' has a container already (use a new folder)'
    # every hit his moves name is made here, every part it names is a bone of Safer's
    plan = json.load(open(MOVES))
    named = {h['damage'] for m in plan['moves'] for h in m.get('hits', []) if isinstance(h, dict) and h.get('damage')}
    assert named == set(SF_HITS), ('moves name', sorted(named - set(SF_HITS)), 'not named', sorted(set(SF_HITS) - named))
    bones = {b['name'] for b in json.load(open(SKELETON))}
    for shape in GEOMETRY.values():
        for f in ('CreatePartName', 'TargetName'):
            assert shape[f] is None or shape[f] in bones, shape[f]

    base_path = os.path.join(base_dir, NAME)
    base = Toc(base_path + '.utoc')
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
                            load_order=e['load_order'], imports=list(e['imports'])))
    paths = [c['path'] for c in chunks[1:]]
    report = []
    changed = set()

    def put(path, data):
        k = paths.index(path) + 1
        chunks[k]['data'] = data
        if entries[k - 1]['size']:
            entries[k - 1]['size'] = len(data)
        changed.add(path)

    def table(path):
        return quiet(B.Table, chunks[paths.index(path) + 1]['data'])

    # ---- 1. the Safer form's hits: his moves' rows struck from Safer's body
    ds = table(DAMAGE)
    ds0 = {k: list(ds.row(k)) for k in ds.at}
    report.append('Damage, the Safer form\'s hits (%d):' % len(SF_HITS))
    for key, (src, shape) in SF_HITS.items():
        assert key not in ds.at and src in ds.at, (key, src)
        row = list(ds.row(src))   # (his own row as installed: buffed)
        for f, v in GEOMETRY[shape].items():
            ds.set(row, f, v)
        for f in OFFSETS:
            ds.set(row, f, 0.0)
        ds.add(key, row)
        report.append('  %-28s %-6s from %-24s power %d' % (key, shape, src, ds.get(row, 'Power')))
    put(DAMAGE, quiet(ds.encode))

    # ---- 2. CharaSpec: his rows list Battle06
    cs = table(CHARASPEC)
    cs0 = {k: list(cs.row(k)) for k in cs.at}
    report.append('CharaSpec:')
    for name in ROWS:
        row = cs.row(name)
        sets = cs.get(row, 'AnimationSetList_Array')
        used = {cs.get(row, f) for f in ('GroundAnimationBattlePackIndex', 'GroundAnimationFieldPackIndex', 'FlyAnimationBattlePackIndex',
                                         'FlyAnimationFieldPackIndex')}
        for want in ADD_SETS:
            if want in sets:
                continue
            free = [i for i, v in enumerate(sets) if v is None and i not in used and i >= 7] or [i for i, v in enumerate(sets) if v is None and i not in used]
            if free:
                sets[free[0]] = want
            else:
                sets.append(want)
        cs.set(row, 'AnimationSetList_Array', sets)
        report.append('  %s: sets %s' % (name, sets))
    put(CHARASPEC, quiet(cs.encode))

    # ---- read back: every other row as it was
    ds2 = quiet(B.Table, chunks[paths.index(DAMAGE) + 1]['data'])
    for key, r0 in ds0.items():
        assert ds2.row(key) == r0, key
    assert set(ds2.at) == set(ds0) | set(SF_HITS) and len(ds2.keys) == len(ds0) + len(SF_HITS)
    for key, (src, shape) in SF_HITS.items():
        r, s = ds2.row(key), ds2.row(src)
        diff = {f for f in fields(ds2) if r[ds2.fi[f]] != s[ds2.fi[f]]}
        assert diff <= set(GEOMETRY[shape]) | set(OFFSETS), (key, diff)
        for f in ('HitDamageSourceID_Array', 'ConditionCreateDamageSourceID_Array'):
            for v in ds2.get(r, f) or []:
                assert v in ds2.at, (key, f, v)
    cs2 = quiet(B.Table, chunks[paths.index(CHARASPEC) + 1]['data'])
    for key, r0 in cs0.items():
        r2 = cs2.row(key)
        if key in ROWS:
            diff = [f for f in fields(cs2) if r2[cs2.fi[f]] != r0[cs2.fi[f]]]
            assert diff == ['AnimationSetList_Array'] or not diff, (key, diff)
            assert all(s in cs2.get(r2, 'AnimationSetList_Array') for s in ADD_SETS)
        else:
            assert r2 == r0, key

    # ---- the container
    cid2 = W.container_id_from_name(NAME)
    assert cid2 == cid
    chunks[0] = dict(id64=cid2, type=10, data=W.container_header(cid2, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    outb = os.path.join(out_dir, NAME)
    W.write_container(outb, NAME, chunks, mount=MOUNT)
    shutil.copy(base_path + '.pak', outb + '.pak')
    back = Toc(outb + '.utoc')
    assert back.container_id == cid2 and back.entries == len(chunks)
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        if c['path']:
            assert back.files.get(i) == MOUNT + c['path'], back.files.get(i)
    _, ents = parse_header(back.read(0))
    assert set(ents) == {c['id64'] for c in chunks[1:]}
    for c, e in zip(chunks[1:], entries):
        got = ents[c['id64']]
        assert (got['size'], got['export_count'], got['export_bundle_count'], got['imports'], got['load_order']) == \
               (e['size'], e['export_count'], e['export_bundle_count'], e['imports'], e['load_order'])
        if c['path'] not in changed:
            j = [kk for kk, v in base.files.items() if v == MOUNT + c['path']][0]
            assert c['data'] == base.read(j), c['path']
    report.append('container: %s (%d packages; changed: %s)' % (outb, len(chunks) - 1, ', '.join(sorted(changed))))
    print('\n'.join(report))
    open(os.path.join(out_dir, 'report.txt'), 'w').write('\n'.join(report) + '\n')
    json.dump({'sf_hits': {k: v[1] for k, v in SF_HITS.items()}, 'sets': ADD_SETS, 'rows': ROWS},
              open(os.path.join(out_dir, 'safer_data.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
