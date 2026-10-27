"""The Meteor cinematic's data (MeteorStrike.lua plays it):
    build_meteor2.py <out dir> <json in> <json out>
  * FullyPlayableSephirothDataAssets_P (the installed Skewer / Meteor ATB build) plus, in BattleDamageSource:
      PC0010_Meteor        the call: his cast makes it when his hand goes up (its damage notify names no damage source of
                           its own, so the move's ReplaceDamageSourceID PC0010_Meteor itself); it hits nothing, it only
                           tells MeteorStrike.lua to bring the meteor down,
      PC0010_Meteor_Impact the impact: on his target, 45 m around, a big blow and a heavy camera shake;
  * compat\\SephirothForms.json: his spell cast (PC0010_Sephiroth Battle00 B_MagAttack01_0/_1/_2: he raises his hand)
    under B_AtkLimit03_0 (the Meteor limit and the Meteor ATB move) in every form, and the cinematic's assets preloaded."""
import json, os, shutil, sys, io, contextlib
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools']
import build_atb as B
from iostore import Toc
import iostore_write as W
from hdr import parse_header

NAME = B.NAME
BASE = '/work/stab1014/out1/' + NAME          # what is installed
MOUNT = B.MOUNT
KEY = 'B_AtkLimit03_0'
CAST = ['/Game/Motion/Player/PC0010_Sephiroth/Battle00/B_MagAttack01_%d.B_MagAttack01_%d' % (i, i) for i in range(3)]
PRELOAD = [
    '/Game/BluePrint/Character/Property/FA0260_01_SephirothMeteor_Battle.FA0260_01_SephirothMeteor_Battle_C',
    '/Game/Effect/Character/Property/FA0260_01_SephirothMeteor_Battle/Particle/FX_FA0260_01_Meteor_01.FX_FA0260_01_Meteor_01',
    '/Game/Effect/Character/Summon/SU2000_Titan/Particle/FX_SU2000_WeightBomb_Exp_01.FX_SU2000_WeightBomb_Exp_01',
    '/Game/Effect/Character/Summon/SU2000_Titan/Particle/FX_SU2000_Stamp_Shock_01.FX_SU2000_Stamp_Shock_01',
    '/Game/Effect/Character/Summon/SU2050_NeoBahamut/Particle/FX_SU2050_BombBullet_Exp_01.FX_SU2050_BombBullet_Exp_01',
    '/Game/Effect/Character/Summon/SU2050_NeoBahamut/Particle/FX_SU2050_Cmn_GroundHit_01.FX_SU2050_Cmn_GroundHit_01',
    '/Game/Effect/Character/Summon/SU0000_Ifrit/Particle/FX_SU0000_Drop_Exp_01.FX_SU0000_Drop_Exp_01',
    '/Game/Effect/Ability/Fire01/Particle/FX_Fire03_Hit_01.FX_Fire03_Hit_01',
    '/Game/Environment/Building/Material/M_Decal_B_GroundCrack_01A.M_Decal_B_GroundCrack_01A',
]
SIGNAL = {   # hits nothing, harmless, lives a second
    'Power': 0, 'BPAttackDamageCoefficient': 0.0, 'CollisionParameter_Array': [1.0], 'LifeTime': 1.0, 'HitTarget2': 0,
    'HitTarget3': 0, 'EnemyHitCategoryTypeBit': 0, 'HitEffectResourceName_Array': [], 'HitEffectResourceCategory_Array': [],
    'BindEffectResourceName': None, 'HitCameraShakeDataID': None, 'CreateBasePos': 0, 'TargetBase': 0,
    'HitReactionType_Array': [2], 'HitReactionParam_Array': [], 'AerialHitReactionParam_Array': [], 'CutValue': 0,
    'HitEffectAttachHitLocation_Array': [],
}
IMPACT = {
    'CreateBasePos': 10, 'TargetBase': 10, 'CollisionParameter_Array': [4500.0], 'Power': 3000, 'LifeTime': 0.8,
    'HitReactionParam_Array': [2500.0], 'AerialHitReactionParam_Array': [2500.0], 'CutValue': 90,
    'HitCameraShakeDataID': 'shake_04', 'CreateCameraShakeDataID': 'shake_04',
}


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def main():
    out_dir, json_in, json_out = sys.argv[1:4]
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
    k = paths.index(B.DAMAGE_TABLE) + 1
    dm = quiet(B.Table, chunks[k]['data'])
    for key, over in (('PC0010_Meteor', SIGNAL), ('PC0010_Meteor_Impact', IMPACT)):
        assert key not in dm.at, key
        row = list(dm.row('PC0010_Meteor_Burst'))
        for field, v in over.items():
            dm.set(row, field, v)
        dm.add(key, row)
        print('%s: %s' % (key, ', '.join('%s=%s' % (f, dm.get(row, f)) for f in over)))
    data = dm.encode()
    chunks[k]['data'] = data
    entries[k - 1]['size'] = len(data)
    cid2 = W.container_id_from_name(NAME)
    assert cid2 == cid
    chunks[0] = dict(id64=cid2, type=10, data=W.container_header(cid2, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    outb = os.path.join(out_dir, NAME)
    W.write_container(outb, NAME, chunks, mount=MOUNT)
    shutil.copy(BASE + '.pak', outb + '.pak')
    back = Toc(outb + '.utoc')
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
    dm0 = quiet(B.Table, base.read([i for i in range(base.entries) if base.files.get(i) == MOUNT + B.DAMAGE_TABLE][0]))
    dm1 = quiet(B.Table, back.read(k))
    assert dm1.keys == dm0.keys + [B.name_tuple('PC0010_Meteor'), B.name_tuple('PC0010_Meteor_Impact')]
    assert all(dm1.row(n) == dm0.row(n) for n in dm0.at)

    raw = open(json_in, encoding='utf-8').read()
    j = json.loads(raw)
    s = j['animation_sets'][0]
    changed = 0
    for m in s['moves']:
        if m.get('key') == KEY:
            m['animation'] = list(CAST)
            changed += 1
    assert changed == 3, changed
    for p in PRELOAD:
        if p not in s['preload']:
            s['preload'].append(p)
    print('json: %s -> his spell cast in %d sets; preload %d' % (KEY, changed, len(s['preload'])))
    open(json_out, 'w', encoding='utf-8').write(json.dumps(j, indent=1, ensure_ascii=False) + ('\n' if raw.endswith('\n') else ''))


if __name__ == '__main__':
    main()
