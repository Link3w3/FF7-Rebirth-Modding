"""Fully Playable Young Sephiroth's Create a Character System files, from the Fully Playable Sephiroth's (installed copies):
  * YoungSephirothForms.json      <- SephirothForms.json: Cloud's rows with FPS's forms menu (NORMAL, WINGED, FLYING, KH2,
    BIZARRO, SAFER); NORMAL's abilities are his base two plus wing and flying ones (the user's pick): commands
    PC0010_AtkBurst01, PC0010_AtkBurst02, PC0010_T_ShadowFlare, PC0010_T_HardCombo, PC0010_T_WarpStab; Cloud's weapon
    abilities -> T_Blizzaga, W3_InfernalGate, T_Aeroga, W3_SwordDance, T_OctaslashPrime, W2_ZanshinRising, T_Thundaga.
    The animations those play that Sephiroth's Battle00 lacks (the casts B_AtkMag01_0-2, the warp stab B_AtkStab01) go
    into Battle00 from the transformed Sephiroth's sets;
  * PlayableYoungSephiroth_Swap.json <- PlayableSephiroth_Swap.json: Young Sephiroth's skeleton PC0010_13_Skeleton joins
    the family of Sephiroth's (with Cloud's and Evil Cloud's; "proportions": everyone keeps his own build) and the
    Nameless's skeleton WE1021_49_Skeleton the weapons' family (the Buster Sword's hub, with the Masamune's);
  * EvilCloudBoss_FPYS.json, BizarroSummon_FPYS.json: as FPS's, on this package's data pak.
Every row and pair needs FullyPlayableYoungSephirothDataAssets_P (and YoungSephiroth_P where his models are named), so
with FPS's paks in instead these switch off by themselves, and FPS's files switch off without theirs.
    make_fpys_json.py <installed compat json dir> <out dir>"""
import copy, json, os, sys

DA, MODELS = 'FullyPlayableYoungSephirothDataAssets_P', 'YoungSephiroth_P'
FPS_DA = 'FullyPlayableSephirothDataAssets_P'
YS_SKEL = '/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13_Skeleton.PC0010_13_Skeleton'
NAMELESS_SKEL = '/Game/Character/Weapon/WE1021_49_Nameless/Model/WE1021_49_Skeleton.WE1021_49_Skeleton'
WING_BONES = ['R_Feather*']                       # his wing (x0.8) keeps its own size: proportion_bones (3.8.2)
KH2_MODEL = '/Game/Character/Player/PC0010_14_Sephiroth_KH2/Model/PC0010_14.PC0010_14'   # KH2Sephiroth_P's copy for his KH2 form
MASAMUNE_BP = '/Game/BluePrint/Character/Weapon/WE1021_00_SephirothIllusion_Masamune.WE1021_00_SephirothIllusion_Masamune_C'
TR = '/Game/Motion/Player/PC0010_Sephiroth_Transform/'
NORMAL = {'pack': 'Battle00',
          'commands': ['PC0010_AtkBurst01', 'PC0010_AtkBurst02', 'PC0010_T_ShadowFlare', 'PC0010_T_HardCombo', 'PC0010_T_WarpStab'],
          'weapon_abilities': {'PC0000_AtkBurst02': 'PC0010_T_Blizzaga', 'PC0000_AtkBurst04': 'PC0010_W3_InfernalGate',
                               'PC0000_AtkBurst05': 'PC0010_T_Aeroga', 'PC0000_AtkBurst06': 'PC0010_W3_SwordDance',
                               'PC0000_AtkBurst07': 'PC0010_T_OctaslashPrime', 'PC0000_AtkBurst08': 'PC0010_W2_ZanshinRising',
                               'PC0000_AtkBurst09': 'PC0010_T_Thundaga'}}
NORMAL_MOVES = [('B_AtkMag01_0', TR + 'Battle00/B_AtkMag01_0.B_AtkMag01_0'), ('B_AtkMag01_1', TR + 'Battle00/B_AtkMag01_1.B_AtkMag01_1'),
                ('B_AtkMag01_2', TR + 'Battle00/B_AtkMag01_2.B_AtkMag01_2'), ('B_AtkStab01', TR + 'Battle01/B_AtkStab01.B_AtkStab01')]


def repaks(o, models=False):
    """Every requires_paks naming FPS's data pak -> this package's (plus its models pak where asked)."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k == 'requires_paks':
                assert FPS_DA in v, v
                o[k] = [DA if p == FPS_DA else p for p in v] + ([MODELS] if models else [])
            else:
                repaks(v, models)
    elif isinstance(o, list):
        for v in o:
            repaks(v, models)


def count_paks(o):
    n = 0
    if isinstance(o, dict):
        for k, v in o.items():
            n += (1 if k == 'requires_paks' and FPS_DA in v else 0) + count_paks(v)
    elif isinstance(o, list):
        n += sum(count_paks(v) for v in o)
    return n


def main(src, out):
    os.makedirs(out, exist_ok=True)
    written = {}
    # the forms
    d = json.load(open(os.path.join(src, 'SephirothForms.json')))
    assert len(d['animation_sets']) == 1 and not d['pairs']
    row = d['animation_sets'][0]
    n = count_paks(d)
    repaks(d, models=True)
    packs = [a['pack'] for a in row['abilities']]
    assert packs[0] == 'Battle00'
    row['abilities'][0] = copy.deepcopy(NORMAL)
    have = {(m['set'], m['key']) for m in row['moves']}
    for key, anim in NORMAL_MOVES:
        assert ('Battle00', key) not in have, key
        row['moves'].append({'set': 'Battle00', 'key': key, 'animation': anim})
    d['source'] = ('Fully Playable Young Sephiroth (Create a Character System 3.8): Young Sephiroth in Cloud\'s slot, on his own skeleton '
                   '(PC0010_13_Skeleton, Rebirth\'s bone names) in the family of Sephiroth\'s, with Sephiroth\'s moves and the Fully Playable '
                   'Sephiroth\'s forms menu (hold Triangle: NORMAL, WINGED, FLYING, KH2, BIZARRO, SAFER). NORMAL has his base abilities plus wing '
                   'and flying ones: PC0010_AtkBurst01, PC0010_AtkBurst02, PC0010_T_ShadowFlare, PC0010_T_HardCombo, PC0010_T_WarpStab; his '
                   'weapons give T_Blizzaga, W3_InfernalGate, T_Aeroga, W3_SwordDance, T_OctaslashPrime, W2_ZanshinRising and T_Thundaga '
                   '(the casts and the warp stab come from the transformed Sephiroth\'s sets). Goes with ' + DA + ' and ' + MODELS +
                   '; the Fully Playable Sephiroth\'s SephirothForms.json switches off by itself without its pak. Based on: ' + d.get('source', ''))
    kh2 = [f for f in row['forms']['list'] if f['name'] == 'KH2'] if isinstance(row['forms'], dict) and 'list' in row['forms'] else None
    if kh2 is None:
        kh2 = [f for k, v in row['forms'].items() if isinstance(v, list) for f in v if isinstance(f, dict) and f.get('name') == 'KH2']
    assert len(kh2) == 1, 'one KH2 form'
    kh2[0]['model'] = KH2_MODEL          # he turns into KH2 Sephiroth (the game's look change, his own AnimBlueprint)
    kh2[0]['as_look'] = True
    # the Masamune in his winged forms (a true weapon swap, Create a Character System 3.8.2 "weapon"); the Nameless in the rest
    for f in row['forms']['list']:
        if f['name'] in ('WINGED', 'FLYING', 'KH2'):
            f['weapon'] = MASAMUNE_BP
    d['source'] += (' (Young Sephiroth: his wing is part of his own model, the PC0010_10_Wing slot the forms show in WINGED, FLYING and KH2; '
                    'in KH2 he turns into KH2 Sephiroth, ' + KH2_MODEL.rsplit('.', 1)[0] + ' from KH2Sephiroth_P: without it he keeps his own model; '
                    'he fights with the Nameless, and with the Masamune in WINGED, FLYING and KH2: "weapon", Create a Character System 3.8.2.)')
    written['YoungSephirothForms.json'] = (d, n)
    # the swap: his skeleton in Sephiroth's family, the Nameless in the weapons'
    s = json.load(open(os.path.join(src, 'PlayableSephiroth_Swap.json')))
    n = count_paks(s)
    repaks(s)
    fam = [p for p in s['pairs'] if p.get('method') == 'family' and p['hub'].endswith('PC0010_00_Skeleton.PC0010_00_Skeleton')]
    weap = [p for p in s['pairs'] if p.get('method') == 'family' and p['hub'].endswith('WE0000_00_Skeleton.WE0000_00_Skeleton')]
    assert len(fam) == 1 and len(weap) == 1
    fam[0]['animation_skeletons'].append(YS_SKEL)
    fam[0]['requires_paks'].append(MODELS)
    assert fam[0].get('proportions') is True
    fam[0]['proportion_bones'] = WING_BONES
    weap[0]['animation_skeletons'].append(NAMELESS_SKEL)
    weap[0]['requires_paks'].append(MODELS)
    s['source'] = ('Fully Playable Young Sephiroth\'s swap (from the Fully Playable Sephiroth\'s): Young Sephiroth\'s skeleton '
                   'PC0010_13_Skeleton joins Sephiroth\'s family (his mesh plays every animation made for Sephiroth, keeping his own build: '
                   '"proportions"; his wing, R_Feather*, keeps its own smaller size too: "proportion_bones", Create a Character System 3.8.2), '
                   'the Nameless\'s WE1021_49_Skeleton the weapons\' family; Evil Cloud in Sephiroth\'s place as in FPS. '
                   'Goes with ' + DA + ' and ' + MODELS + '. Based on: ' + s.get('source', ''))
    written['PlayableYoungSephiroth_Swap.json'] = (s, n)
    for name, new in (('EvilCloudBoss.json', 'EvilCloudBoss_FPYS.json'), ('BizarroSummon.json', 'BizarroSummon_FPYS.json')):
        e = json.load(open(os.path.join(src, name)))
        n = count_paks(e)
        repaks(e)
        e['source'] = 'Fully Playable Young Sephiroth\'s copy (on ' + DA + ') of ' + name + ': ' + e.get('source', '')
        written[new] = (e, n)
    for name, (obj, n) in written.items():
        p = os.path.join(out, name)
        json.dump(obj, open(p, 'w'), indent=1, ensure_ascii=False)
        print('%-36s %8d bytes, %d requires_paks moved to %s' % (name, os.path.getsize(p), n, DA))


if __name__ == '__main__':
    main(*sys.argv[1:])
