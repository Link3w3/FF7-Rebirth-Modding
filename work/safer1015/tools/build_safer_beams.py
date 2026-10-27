"""Create a Character System 3.6: the Safer form's attacks as beams and orbs, in FullyPlayableSephirothDataAssets_P (the
installed container as it is, every other package and every other row byte for byte).

His Battle06 moves name their hits PC0010_SF_* (make_safer_moves.py). Those rows were his own move's row struck from
Safer's wing, hand or body (build_safer_data.py). Here each becomes a shot instead:
  * an orb: Bizarro Sephiroth's Shadow Flare orb (EB2210_00_ShadowFlare_01: its sphere, effects, sounds), homing on
    the target like the transformed Sephiroth's Shadow Flare (PC0010_10_ShadowFlare_01), from Safer's left hand
    (his casts: skill_003, skill_004) or right hand (his wing swing: skill_005),
  * a beam: Bizarro's eye beam (EB2210_00_EyeMagic_01) from Safer's left hand at the target (his lunge: skill_002,
    his slow cast: skill_006),
  * a great beam: Bizarro's Stigma beam (EB2210_00_Stigma_01) from Safer's left hand at the target (his limit's eight
    blows and its last one).
The damage stays his own move's (as installed: buffed): power, stagger, reactions, critical, bonus, element, status.
His row's player settings stay too (its flags, reflect, shield and execution types: a player's, not the boss's).
Only how the hit is made (where it starts, where it goes, how it flies, its size, its effects and sounds) is the shot's.
The effects are Bizarro's, in his effect pack, which his rows already load (the Bizarro form).
    build_safer_beams.py <installed container dir> <out dir>"""
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
MOVES = '/work/safer1015/json/safer_moves.json'
SKELETON = '/tmp/scratch/look365/safer_PC0010_999_Skeleton.json'

# How a hit is made: these fields come from the shot's row; everything else (the damage) stays his move's.
SHOT_FIELDS = [
    'ConditionCreateDamageSourceID_Array', 'ConditionCreateDamageSourceType_Array', 'CreateDamageSourceParameter_Array',
    'CreateDamageSourceFloat_Array', 'CreateDamageSourceConditionType_Array',
    'ControlName_Array', 'ExtControlName_Array', 'ControlParameter_Array', 'ExtControlParameter_Array', 'ExtControlFlag_Array',
    'ExtControlType_Array', 'ControlType', 'ControlFlag',
    'HitEffectResourceName_Array', 'HitEffectResourceCategory_Array', 'HitEffectAttachCharacter_Array',
    'HitEffectAttachHitLocation_Array', 'HitEffectIntervalTime_Array',
    'CollisionParameter_Array', 'CollisionType', 'CollisionFaceGuardScale', 'HitGroupName', 'HitSlowID',
    'CreateEffectResourceName', 'CreateEffectResourceCategory', 'CreateSoundResourceName', 'CreateSoundResourceCategory',
    'HitSoundResourceName', 'HitSoundResourceCategory', 'GuardEffectResourceName', 'GuardEffectResourceCategory',
    'GuardSoundResourceName', 'GuardSoundResourceCategory',
    'BindEffectResourceName', 'BindEffectResourceCategory', 'BindEffectAttachSocket', 'BindEffectDelayTime',
    'BindEffectOffsetX', 'BindEffectOffsetY', 'BindEffectOffsetZ', 'BindEffectOffsetPitch', 'BindEffectOffsetYaw',
    'BindEffectOffsetRoll', 'BindSoundResourceName', 'BindSoundResourceCategory',
    'Property',
    'HitInterval', 'HitCount', 'HitCountTotal', 'HitDestroyType', 'HitDestroyTargetType',
    'CreateDelayTime', 'DisableHitTime', 'DisableHitOnlyTime', 'LifeTime', 'LifeTimeNotify', 'DestroyDelayTime',
    'PhysicsVelocityScaleCharacter', 'PhysicsVelocityScaleBackground', 'PhysicsVelocityScaleDamageSource',
    'CreatePhysicsObjectDelay', 'CreatePhysicsObjectForce', 'CreatePhysicsObjectForceRandom', 'CreatePhysicsObjectCharaSpecID',
    'CreatePhysicsObjectPartName', 'CreatePhysicsObjectBasePos', 'PushCollisionRadiusReachTime', 'PushCollisionEnable',
    'DangerRange', 'DangerLengthCoefficient', 'DangerDamageDestroyDelayTime', 'DangerDamageDodgeDirectionType',
    'DangerDamageReflectType', 'HitDamageSourceEffectType', 'DisableHitBackground', 'MoveOnTerrain',
    'CreatePartOffsetDirectionType', 'TargetOffsetDirectionType', 'DirectionType', 'RecalcMoveDir',
    'ProgressDirectionType', 'RotationType', 'CharaSpecType', 'PhysicsType',
    'CharaSpecID', 'CharaSpecMotionName', 'HitCharaSpecID', 'DisableLookAtCheck', 'DisableMoveHitPosition', 'CutValue',
]
# where it starts and where it goes (Safer's bones; at the target)
PLACE_FIELDS = ['CreateBasePos', 'CreatePartName', 'TargetBase', 'TargetName', 'CreatePartOffsetX', 'CreatePartOffsetY',
                'CreatePartOffsetZ', 'CreatePartOffsetPitch', 'CreatePartOffsetYaw', 'CreatePartOffsetRoll',
                'TargetOffsetX', 'TargetOffsetY', 'TargetOffsetZ']
HOMING = 'PC0010_10_ShadowFlare_01'   # the transformed Sephiroth's homing Shadow Flare: its flight
SHOTS = {
    # orbs: Shadow Flare's orb, homing like the transformed Sephiroth's (his speed 6000 slowed so the orb is seen)
    'Orb': dict(row='EB2210_00_ShadowFlare_01', hand='L_Hand_a', homing=4000.0, life=3.0),
    'OrbR': dict(row='EB2210_00_ShadowFlare_01', hand='R_Hand_a', homing=4000.0, life=3.0),
    # beams: the eye beam and Stigma, at the target, lasting a moment and hitting once
    'Beam': dict(row='EB2210_00_EyeMagic_01', hand='L_Hand_a', beam=(6000.0, 4000.0), life=0.5),
    'GreatBeam': dict(row='EB2210_00_Stigma_01', hand='L_Hand_a', beam=(10000.0, 6000.0), life=0.4, radius=250.0),
}
# his hits -> the shot (by the animation each is in: make_safer_moves.py)
SF_SHOTS = {
    'PC0010_SF_NAtk_1_01': 'OrbR', 'PC0010_SF_NAtk_2_01': 'Orb', 'PC0010_SF_NAtk_3_01': 'Orb', 'PC0010_SF_NAtk_4_01': 'Beam',
    'PC0010_SF_JAtk_1_01': 'OrbR', 'PC0010_SF_JAtk_2_01': 'Orb', 'PC0010_SF_JAtk_3_01': 'Orb',
    'PC0010_SF_ChainChange01_01': 'OrbR', 'PC0010_SF_NPAtk_1_01': 'Beam',
    'PC0010_SF_Satk_1_01': 'Beam', 'PC0010_SF_Satk_2_01': 'OrbR', 'PC0010_SF_Satk_6_01': 'GreatBeam',
    'PC0010_SF_Satk_8_01': 'Orb', 'PC0010_SF_Satk_8_02': 'Orb', 'PC0010_SF_Satk_8_03': 'Orb',
    'PC0010_SF_SAtk_9_01': 'Beam', 'PC0010_SF_SAtk_9_02': 'Beam', 'PC0010_SF_SAtk_9_03': 'Orb',
    'PC0010_SF_PAtk_1_01': 'Orb', 'PC0010_SF_PAtk_2_01': 'OrbR',
}
for n in range(1, 9):
    SF_SHOTS['PC0010_SF_Limit_1_%02d' % n] = 'GreatBeam'
# the row each hit's damage is his move's (as build_safer_data.py made them)
SF_SOURCE = {
    'PC0010_SF_NAtk_1_01': 'PC0010_NAtk_1_01', 'PC0010_SF_NAtk_2_01': 'PC0010_NAtk_2_01', 'PC0010_SF_NAtk_3_01': 'PC0010_NAtk_3_01',
    'PC0010_SF_NAtk_4_01': 'PC0010_NAtk_4_01', 'PC0010_SF_JAtk_1_01': 'PC0010_JAtk_1_01', 'PC0010_SF_JAtk_2_01': 'PC0010_JAtk_2_01',
    'PC0010_SF_JAtk_3_01': 'PC0010_JAtk_3_01', 'PC0010_SF_ChainChange01_01': 'PC0010_ChainChange01_01',
    'PC0010_SF_NPAtk_1_01': 'PC0010_NPAtk_1_04', 'PC0010_SF_Satk_1_01': 'PC0010_Satk_1_01', 'PC0010_SF_Satk_2_01': 'PC0010_Satk_2_01',
    'PC0010_SF_Satk_6_01': 'PC0010_Satk_6_01', 'PC0010_SF_Satk_8_01': 'PC0010_Satk_8_01', 'PC0010_SF_Satk_8_02': 'PC0010_Satk_8_02',
    'PC0010_SF_Satk_8_03': 'PC0010_Satk_8_03', 'PC0010_SF_SAtk_9_01': 'PC0010_SAtk_9_01', 'PC0010_SF_SAtk_9_02': 'PC0010_SAtk_9_02',
    'PC0010_SF_SAtk_9_03': 'PC0010_SAtk_9_03', 'PC0010_SF_PAtk_1_01': 'PC0010_PAtk_1_01', 'PC0010_SF_PAtk_2_01': 'PC0010_PAtk_2_01',
}
for n in range(1, 9):
    SF_SOURCE['PC0010_SF_Limit_1_%02d' % n] = 'PC0010_Limit_1_%02d' % n


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def fields(t):
    return [f[0][0] for f in t.fields]


def main(base_dir, out_dir):
    assert not os.path.exists(os.path.join(out_dir, NAME + '.utoc')), out_dir + ' has a container already (use a new folder)'
    plan = json.load(open(MOVES))
    named = {h['damage'] for m in plan['moves'] for h in m.get('hits', []) if isinstance(h, dict) and h.get('damage')}
    assert named == set(SF_SHOTS) == set(SF_SOURCE), ('moves name', sorted(named ^ set(SF_SHOTS)))
    bones = {b['name'] for b in json.load(open(SKELETON))}
    for shot in SHOTS.values():
        assert shot['hand'] in bones, shot['hand']

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
    k = paths.index(DAMAGE) + 1
    ds = quiet(B.Table, chunks[k]['data'])
    names = fields(ds)
    for f in SHOT_FIELDS + PLACE_FIELDS:
        assert f in names, f
    kept = [f for f in names if f not in SHOT_FIELDS and f not in PLACE_FIELDS]
    ds0 = {key: list(ds.row(key)) for key in ds.at}
    for key in SF_SHOTS:
        assert key in ds.at, key + ' is not installed (build_safer_data.py makes it)'
    report = ['The Safer form\'s hits as shots (%d):' % len(SF_SHOTS)]
    for key, which in SF_SHOTS.items():
        shot = SHOTS[which]
        src = ds.row(SF_SOURCE[key])
        tpl = ds.row(shot['row'])
        row = list(ds.row(key))
        # his move's damage: every kept field as his move's own row (as installed, buffed)
        for f in kept:
            ds.set(row, f, ds.get(src, f))
        for f in SHOT_FIELDS:
            ds.set(row, f, ds.get(tpl, f))
        ds.set(row, 'CreateBasePos', 0)
        ds.set(row, 'CreatePartName', shot['hand'])
        ds.set(row, 'TargetBase', 10)
        ds.set(row, 'TargetName', None)
        for f in PLACE_FIELDS[4:]:
            ds.set(row, f, 0.0)
        if 'homing' in shot:
            homing = ds.row(HOMING)
            ds.set(row, 'ControlType', ds.get(homing, 'ControlType'))
            params = list(ds.get(homing, 'ControlParameter_Array'))
            params[0] = shot['homing']
            ds.set(row, 'ControlParameter_Array', params)
            ds.set(row, 'ProgressDirectionType', ds.get(homing, 'ProgressDirectionType'))
        if 'beam' in shot:
            ds.set(row, 'ControlParameter_Array', list(shot['beam']))
            ds.set(row, 'LifeTimeNotify', 0)
            ds.set(row, 'HitCount', 1)
            ds.set(row, 'HitInterval', 0.0)
        ds.set(row, 'LifeTime', shot['life'])
        if 'radius' in shot:
            ds.set(row, 'CollisionParameter_Array', [shot['radius']])
        ds.set(row, 'HitSlowID', None)
        ds.set(row, 'StatusChangeID_Array', ds.get(src, 'StatusChangeID_Array'))
        ds.rows[ds.at[key]] = row
        report.append('  %-28s %-9s from %-9s %-24s effect %-32s power %d (his %s)' % (
            key, which, shot['hand'], shot['row'], ds.get(row, 'BindEffectResourceName'), ds.get(row, 'Power'), SF_SOURCE[key]))
    data = quiet(ds.encode)
    chunks[k]['data'] = data
    if entries[k - 1]['size']:
        entries[k - 1]['size'] = len(data)

    # ---- read back: the shots as made, every other row as it was
    ds2 = quiet(B.Table, data)
    assert set(ds2.at) == set(ds0) and len(ds2.keys) == len(ds0)
    for key, r0 in ds0.items():
        if key not in SF_SHOTS:
            assert ds2.row(key) == r0, key
    for key, which in SF_SHOTS.items():
        shot = SHOTS[which]
        r, s, t = ds2.row(key), ds2.row(SF_SOURCE[key]), ds2.row(shot['row'])
        for f in kept:
            assert ds2.get(r, f) == ds2.get(s, f), (key, f)
        assert ds2.get(r, 'CreatePartName') == shot['hand'] and ds2.get(r, 'TargetBase') == 10, key
        assert ds2.get(r, 'BindEffectResourceName') == ds2.get(t, 'BindEffectResourceName'), key
        for f in ('HitDamageSourceID_Array', 'ConditionCreateDamageSourceID_Array'):
            for v in ds2.get(r, f) or []:
                assert v in ds2.at, (key, f, v)

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
    for c in chunks[1:]:
        if c['path'] != DAMAGE:
            j = [kk for kk, v in base.files.items() if v == MOUNT + c['path']][0]
            assert c['data'] == base.read(j), c['path']
    report.append('container: %s (%d packages; changed: %s)' % (outb, len(chunks) - 1, DAMAGE))
    print('\n'.join(report))
    open(os.path.join(out_dir, 'report.txt'), 'w').write('\n'.join(report) + '\n')
    json.dump({'shots': SF_SHOTS, 'kinds': {k: dict(v) for k, v in SHOTS.items()}}, open(os.path.join(out_dir, 'safer_shots.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
