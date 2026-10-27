"""The REMAKE and REMAKE WINGED forms' data, in a Fully Playable (Young) Sephiroth data container (FPS's or FPYS's: the
two have the same tables), the old container's blocks as they are, the changed and new chunks after them:
  * BattleAbility: his Remake commands, player versions of the abilities he has as their models (each the copy of one of
    his forms' abilities, its animations the REMAKE packs' keys, its name the game's own name for Remake Sephiroth's
    attack, $bt_Sephiroth_*):
      PC0010_RM_Octaslash   (BZ_Octaslash's: B_AtkHattou01, a chain of the charge, the dash and the eight slashes)
      PC0010_RM_Scintilla   (W3_SwordDance's: B_AtkSenkou02)
      PC0010_RM_ShadowFlare (T_ShadowFlare's: B_AtkSFlare01_0 / _1 / _2, its raise, charge and orbs; T_ShadowFlare's orbs)
      PC0010_RM_HellsGate   (BZ_HellsGate's: B_AtkGokumon01, a chain of the crouch, leap, plunge and impact)
    (Heartless Angel is PC0010_T_HeartlessAngel as it is: the REMAKE packs' B_AtkTenshi01_0 / _1 are Remake's.)
  * BattleDamageSource: their hits, PC0010_RM_Hattou_01 - 08 (Bizarro's Octaslash hits, which strike the target itself),
    PC0010_RM_Senkou_01 - 06 (likewise, Scintilla's flash and its storm of slashes), PC0010_RM_Gokumon_01 (the plunge, on
    the target) and _02 (the shockwave, 6 m around him), PC0010_RM_NPAtk_1_01 / _02 (his hold Square's two Zanshin
    waves, Bizarro's right and left ones),
  * Text/US: their help texts,
  * CharaSpec: Cloud's 9 rows (his) list Battle08 and Battle09,
  * the built moves (RebirthSkelCompat/Built/SephirothForms/Battle08, Battle09) from the moves container, each laid out
    the way the game reads its own animations (align_moves.realign, checked against the game's reader).
    build_remake_forms_data.py <base .utoc> <moves .utoc, or - for none> <out dir (new)>"""
import contextlib, hashlib, io, os, shutil, struct, sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools', '/work/evilboss1016/data', '/work/sephforms/tools']
import build_atb as B
from iostore import Toc
import iostore_write as W
import hdr
import txtres
import build_evilcloud_data as BED
import align_moves as A

MOUNT = '../../../End/Content/'
ABILITY = 'DataObject/Resident/BattleAbility.uasset'
DAMAGE = 'DataObject/Resident/BattleDamageSource.uasset'
CHARASPEC = 'DataObject/Resident/CharaSpec.uasset'
TEXT = 'Text/US/Resident_TxtRes.uasset'
MOVES_PREFIX = ('RebirthSkelCompat/Built/SephirothForms/Battle08/', 'RebirthSkelCompat/Built/SephirothForms/Battle09/')
ROWS = ['PC0000_00_Cloud_Standard', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing', 'PC0000_10_Cloud_CostaClothing2',
        'PC0000_04_Cloud_ZackCostume', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
        'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']
ADD_SETS = ['Battle08', 'Battle09']

# new ability -> (model ability, name, ATB, animations, damage, help, more overrides)
ABILITIES = {
    'PC0010_RM_Octaslash': ('PC0010_BZ_Octaslash', '$bt_Sephiroth_Hattou01', 2, ['B_AtkHattou01'], 'PC0010_RM_Hattou',
                            'Gather your strength, close in on an enemy in a flash and cut it down with eight lightning-fast strikes.',
                            {'AnimationSelectType_Array': [], 'AnimationParameter_Array': [], 'ShowNameSecond': 9.0}),
    'PC0010_RM_Scintilla': ('PC0010_W3_SwordDance', '$bt_Sephiroth_Senkou01', 1, ['B_AtkSenkou02'], 'PC0010_RM_Senkou',
                            'Flash through an enemy and leave it in a storm of blades.', {'ShowNameSecond': 3.0}),
    'PC0010_RM_ShadowFlare': ('PC0010_T_ShadowFlare', '$bt_Sephiroth_Flare01', 1, ['B_AtkSFlare01_0', 'B_AtkSFlare01_1', 'B_AtkSFlare01_2'],
                              'PC0010_P_ShadowFlare', 'Unleash orbs of dark energy that hound an enemy and explode.', {'ShowNameSecond': 3.0}),
    'PC0010_RM_HellsGate': ('PC0010_BZ_HellsGate', '$bt_Sephiroth_Gokumon01', 2, ['B_AtkGokumon01'], 'PC0010_RM_Gokumon',
                            'Leap high and plunge the Masamune into an enemy, sending a shockwave through all around.', {'ShowNameSecond': 4.0}),
}
# new damage row -> (model row, overrides)
DAMAGE_ROWS = {}
for k in range(1, 9):
    DAMAGE_ROWS['PC0010_RM_Hattou_%02d' % k] = ('EB2210_00_Hattou_%02d' % k, {})
for k, power in enumerate((600, 1500, 450, 450, 450, 450), 1):
    DAMAGE_ROWS['PC0010_RM_Senkou_%02d' % k] = ('EB2210_00_Hattou_01', {'Power': power})
DAMAGE_ROWS['PC0010_RM_Gokumon_01'] = ('EB2210_00_Hattou_08', {'Power': 3000})
DAMAGE_ROWS['PC0010_RM_Gokumon_02'] = ('PC0010_AtkBurst02_02', {'Power': 2400})
# his hold Square's Zanshin waves (Ichijin's two slashes, on the ground and in the air): Bizarro Sephiroth's right and left
# waves (the ones the BIZARRO form's Zanshin looses, his effects from Bizarro's effect pack, which his rows load), made at
# his chest (Bizarro's are made at sockets of his own, Attack_ZanshinR / L, which no other model has; C_Spine_d is a bone
# of Rebirth's and Remake's Sephiroth alike), at the power of his first combo hit (PC0010_NAtk_1_01) each
for key, src in (('PC0010_RM_NPAtk_1_01', 'EB2210_00_Zanshin1_R01'), ('PC0010_RM_NPAtk_1_02', 'EB2210_00_Zanshin1_L01')):
    DAMAGE_ROWS[key] = (src, {'CreatePartName': 'C_Spine_d', 'Power': 180})


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def fields(t):
    return [f[0][0] for f in t.fields]


def moves_from(utoc):
    """The built moves of the moves container: (chunk, store entry), each package laid out like the game's animations."""
    src = Toc(utoc)
    heads = [i for i in range(src.entries) if src.chunk_type(i) == 10]
    assert len(heads) == 1
    _, store = hdr.parse_header(src.read(heads[0]))
    out, left = [], []
    for i in range(src.entries):
        if src.chunk_type(i) == 10:
            continue
        path = src.files.get(i, '')
        assert path.startswith(MOUNT), path
        rel = path[len(MOUNT):]
        if not rel.startswith(MOVES_PREFIX):
            left.append(rel)
            continue
        assert src.chunk_type(i) == 2, (rel, src.chunk_type(i))
        pid = src.chunk_id64(i)
        se = store[pid]
        data = A.realign(src.read(i))
        A.verify(data, rel)
        out.append((dict(id64=pid, type=2, data=data, path=rel),
                    dict(id=pid, size=len(data) | (A.SHIFT << 60), export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                         load_order=se['load_order'], imports=list(se['imports']))))
    return out, left


def main(base_utoc, moves_utoc, out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    name = os.path.basename(base_utoc)[:-len('.utoc')]
    base_ucas = base_utoc[:-len('.utoc')] + '.ucas'
    old = Toc(base_utoc)
    assert [i for i in range(old.entries) if old.chunk_type(i) == 10] == [0]
    cid, store = hdr.parse_header(old.read(0))
    assert cid == W.container_id_from_name(name), 'the container is not called ' + name
    order = [old.chunk_id64(i) for i in range(old.entries) if old.chunk_type(i) == 2]
    entries = [dict(id=p, size=store[p]['size'], export_count=store[p]['export_count'], export_bundle_count=store[p]['export_bundle_count'],
                    load_order=store[p]['load_order'], imports=list(store[p]['imports'])) for p in order]
    assert W.container_header(cid, entries) == old.read(0), 'the header does not write back as it is'
    entry_of = {e['id']: e for e in entries}
    by_path = {old.files[i][len(MOUNT):]: i for i in old.files}
    changes, report = {}, []

    def put(path, data):
        i = by_path[path]
        e = entry_of[old.chunk_id64(i)]
        assert e['size'] >> 60 == 0
        if e['size']:
            e['size'] = len(data)
        changes[i] = data

    ab = quiet(B.Table, old.read(by_path[ABILITY]))
    ds = quiet(B.Table, old.read(by_path[DAMAGE]))
    cs = quiet(B.Table, old.read(by_path[CHARASPEC]))
    ab0 = {k: list(ab.row(k)) for k in ab.at}
    ds0 = {k: list(ds.row(k)) for k in ds.at}
    cs0 = {k: list(cs.row(k)) for k in cs.at}

    # ---- damage
    report.append('BattleDamageSource (%d rows):' % len(DAMAGE_ROWS))
    for key, (src, over) in DAMAGE_ROWS.items():
        assert key not in ds.at and src in ds.at, (key, src)
        row = list(ds.row(src))
        for f, v in over.items():
            ds.set(row, f, v)
        ds.add(key, row)
        report.append('  %-22s from %-22s power %5d  %s %s (%s)' % (key, src, ds.get(row, 'Power'), ds.get(row, 'CreatePartName'),
                                                                 ds.get(row, 'CollisionParameter_Array'), 'on the target' if ds.get(row, 'TargetBase') == 10 else 'around him'))

    # ---- abilities
    ids = iter(B.unique_ids(ab, len(ABILITIES), 1022))
    sort = 1 + max(ab.get(ab.row(k), 'SortId') for k in ab.at if k.startswith('PC0010_'))
    helps = {}
    report.append('BattleAbility (%d rows):' % len(ABILITIES))
    for key, (src, nm, atb, anims, damage, help_text, over) in ABILITIES.items():
        assert key not in ab.at and src in ab.at, (key, src)
        row = list(ab.row(src))
        ab.set(row, 'Name', nm)
        ab.set(row, 'ATB', float(atb))
        ab.set(row, 'AnimationString_Array', list(anims))
        ab.set(row, 'ReplaceDamageSourceID', damage)
        help_key = '$%s_help' % key
        ab.set(row, 'Explanation', help_key)
        helps[help_key] = help_text
        ab.set(row, 'UniqueId', next(ids))
        ab.set(row, 'SortId', sort)
        sort += 1
        for f, v in over.items():
            ab.set(row, f, v)
        ab.add(key, row)
        assert any(k == damage or k.startswith(damage + '_') for k in ds.at), (key, 'no damage rows', damage)
        report.append('  %-22s from %-22s %-26s ATB %d  %s  damage %s' % (key, src, nm, atb, anims, damage))
    put(ABILITY, quiet(ab.encode))
    put(DAMAGE, quiet(ds.encode))

    # ---- text
    tdata = old.read(by_path[TEXT])
    have = {k: v for k, v, _ in txtres.parse(tdata)[0]}
    for key, (src, nm, *_rest) in ABILITIES.items():
        assert nm in have, (key, 'no name text', nm)
    for k in helps:
        assert k not in have, k
    text = txtres.add(tdata, sorted(helps.items()))
    t2 = {k: v for k, v, _ in txtres.parse(text)[0]}
    assert all(t2[k] == v for k, v in helps.items()) and len(t2) == len(have) + len(helps)
    put(TEXT, text)
    report.append('Text/US: %d help texts; names: %s' % (len(helps), ', '.join('%s = %s' % (ABILITIES[k][1], have[ABILITIES[k][1]]) for k in ABILITIES)))

    # ---- CharaSpec: his rows list the REMAKE packs
    report.append('CharaSpec:')
    for row_name in ROWS:
        row = cs.row(row_name)
        sets = cs.get(row, 'AnimationSetList_Array')
        used = {cs.get(row, f) for f in ('GroundAnimationBattlePackIndex', 'GroundAnimationFieldPackIndex', 'FlyAnimationBattlePackIndex',
                                         'FlyAnimationFieldPackIndex')}
        for want in ADD_SETS:
            if want in sets:
                continue
            free = [i for i, v in enumerate(sets) if v is None and i not in used]
            if free:
                sets[free[0]] = want
            else:
                sets.append(want)
        cs.set(row, 'AnimationSetList_Array', sets)
        report.append('  %s: %s' % (row_name, sets))
    put(CHARASPEC, quiet(cs.encode))

    # ---- read back the tables: every other row as it was
    ab2 = quiet(B.Table, changes[by_path[ABILITY]])
    ds2 = quiet(B.Table, changes[by_path[DAMAGE]])
    cs2 = quiet(B.Table, changes[by_path[CHARASPEC]])
    for k, r in ab0.items():
        assert ab2.row(k) == r, k
    for k, r in ds0.items():
        assert ds2.row(k) == r, k
    for k, r in cs0.items():
        if k not in ROWS:
            assert cs2.row(k) == r, k
    assert set(ab2.at) == set(ab0) | set(ABILITIES) and set(ds2.at) == set(ds0) | set(DAMAGE_ROWS)
    uids = [ab2.get(ab2.row(k), 'UniqueId') for k in ab2.at]
    assert len(uids) == len(set(uids)), 'unique ids repeat'
    for key in ABILITIES:
        assert ab2.get(ab2.row(key), 'Name') == ABILITIES[key][1] and ab2.get(ab2.row(key), 'AnimationString_Array') == ABILITIES[key][3]

    # ---- the built moves
    additions = []
    if moves_utoc != '-':
        moves, left = moves_from(moves_utoc)
        have_ids = {old.chunk_id64(i) for i in range(old.entries)}
        for chunk, entry in moves:
            assert chunk['id64'] not in have_ids, ('already in the container', chunk['path'])
            additions.append(chunk)
            entries.append(entry)
        report.append('Moves: %d packages (Battle08 %d, Battle09 %d), laid out like the game\'s animations; left out of the moves container: %s' % (
            len(moves), sum(1 for c, _ in moves if '/Battle08/' in c['path']), sum(1 for c, _ in moves if '/Battle09/' in c['path']),
            ', '.join(left) or 'nothing'))
    changes[0] = W.container_header(cid, entries)

    # ---- the container: the old blocks, then the new
    os.makedirs(out)
    path = os.path.join(out, name)
    BED.append_container(old, base_ucas, changes, additions, path + '.utoc', path + '.ucas.tail')
    with open(path + '.ucas', 'wb') as f:
        with open(base_ucas, 'rb') as g:
            shutil.copyfileobj(g, f, 1 << 24)
        f.write(open(path + '.ucas.tail', 'rb').read())
    shutil.copy(base_utoc[:-len('.utoc')] + '.pak', path + '.pak')
    new = Toc(path + '.utoc')
    assert new.container_id == cid and new.entries == old.entries + len(additions)
    same = 0
    for k in range(new.entries):
        d = new.read(k)
        assert hashlib.sha1(d).digest() == new.b[new.metas_off + 33 * k:new.metas_off + 33 * k + 20], k
        if k < old.entries:
            assert new.files.get(k) == old.files.get(k) and new.chunk_id64(k) == old.chunk_id64(k)
            if k in changes:
                assert d == changes[k]
            else:
                assert d == old.read(k)
                same += 1
        else:
            c = additions[k - old.entries]
            assert d == c['data'] and new.chunk_id64(k) == c['id64'] and new.files.get(k) == MOUNT + c['path']
            A.verify(d, c['path'])
    cid2, ents = hdr.parse_header(new.read(0))
    assert cid2 == cid and len(ents) == len(entries)
    for e in entries:
        b = ents[e['id']]
        for key in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert b[key] == e[key], key
    report.append('%s: %d chunks (%d before; %d byte for byte the old ones; the 4 tables and the header changed; %d added); .ucas +%d bytes' % (
        name, new.entries, old.entries, same, len(additions), os.path.getsize(path + '.ucas.tail')))
    open(os.path.join(out, 'report.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        if f.endswith('.tail'):
            continue
        print('  %-48s %10d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:4])
