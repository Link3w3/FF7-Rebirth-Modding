"""Chaos's Death Penalty shots: beams of light from the gun's muzzle, as BattleDamageSource rows of the installed
FullyPlayableVincentAssets_P (every other package and every other row byte for byte as installed).

Each row is Vincent's Griffon bullet row (PC0011_Dirge_Griffon: a player's gun row, every kind of enemy, its heavy
reaction) with a beam's flight and look (the shot fields of a beam row of the game's: ControlType 7, its effect, its hit
effect), from the Death Penalty's muzzle (CreateBasePos 1: the weapon; VFX_Muzzle01) to the target, once:
  PC0011_Chaos_DeathPenalty            Aerith's light beam (her cast normal attack, FX_PC0003_Burst08_NAttackBeam_01): the default
  PC0011_Chaos_DeathPenalty_Alexander  Alexander's laser (FX_SU2030_Laser_01)
  PC0011_Chaos_DeathPenalty_Feeler     the transformed Sephiroth's feeler laser (FX_PC0010_10_FeelerLaser_Bullet_01)
  PC0011_Chaos_DeathPenalty_Barret     Barret's limit beam (FX_PC0001_Limit02_Beam_01)
  PC0011_Chaos_DeathPenalty_Cloud      Cloud's charged magic beam (FX_PC0000_ChainChargeMagic_Beam_01)
A beam's effects are its character's effect pack's (the row's "pack_assets" loads the one it uses).
    build_chaos_beams.py <installed container dir> <out dir (new)>"""
import contextlib, io, json, os, sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools', '/work/shooter1016/tools', '/work/prologue1016/tools',
                '/work/sephforms/tools']
import build_atb as B
import build_dirge_paks as P
from iostore import Toc

NAME = 'FullyPlayableVincentAssets_P'
DAMAGE = 'DataObject/Resident/BattleDamageSource.uasset'
BASE_ROW = 'PC0011_Dirge_Griffon'
# the fields that make the hit a beam (its flight, look, size, effects, sounds): the beam row's (build_safer_beams.py's list)
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
PLACE_FIELDS = ['CreatePartOffsetX', 'CreatePartOffsetY', 'CreatePartOffsetZ', 'CreatePartOffsetPitch', 'CreatePartOffsetYaw',
                'CreatePartOffsetRoll', 'TargetOffsetX', 'TargetOffsetY', 'TargetOffsetZ']
CHAIN = ['ConditionCreateDamageSourceID_Array', 'ConditionCreateDamageSourceType_Array', 'CreateDamageSourceParameter_Array',
         'CreateDamageSourceFloat_Array', 'CreateDamageSourceConditionType_Array']
PACKS = {
    'PC0003': '/Game/Effect/Character/Player/PC0003_Aerith/Build/PC0003_Aerith_Effect__Pack.PC0003_Aerith_Effect__Pack',
    'SU2030': '/Game/Effect/Character/Summon/SU2030_Alexander/Build/SU2030_Alexander_Effect__Pack.SU2030_Alexander_Effect__Pack',
    'PC0010_10': '/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Build/PC0010_10_Sephiroth_Transform_Effect__Pack.PC0010_10_Sephiroth_Transform_Effect__Pack',
    'PC0001': '/Game/Effect/Character/Player/PC0001_Barret/Build/PC0001_Barret_Effect__Pack.PC0001_Barret_Effect__Pack',
    'PC0000': '/Game/Effect/Character/Player/PC0000_Cloud/Build/PC0000_Cloud_Effect__Pack.PC0000_Cloud_Effect__Pack',
}
BEAMS = [
    # row, the beam row its shot is, its effect pack
    ('PC0011_Chaos_DeathPenalty', 'PC0003_NAtk_CastMagic_1_01', 'PC0003'),
    ('PC0011_Chaos_DeathPenalty_Alexander', 'SU2030_01_AtkLaserCRot01', 'SU2030'),
    ('PC0011_Chaos_DeathPenalty_Feeler', 'PC0010_10_FeelerLaser_01', 'PC0010_10'),
    ('PC0011_Chaos_DeathPenalty_Barret', 'PC0001_Limit002_01', 'PC0001'),
    ('PC0011_Chaos_DeathPenalty_Cloud', 'PC0000_ChainCharge2_UC_02', 'PC0000'),
]
SPEED, LENGTH = 15000.0, 20000.0   # cm/s the beam reaches out, cm at most
LIFE = 0.6                          # s it lasts
RADIUS = 30.0
POWER, BONUS = 30, 80


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def make_rows(ds):
    names = [f[0][0] for f in ds.fields]
    for f in SHOT_FIELDS + PLACE_FIELDS + ['CreateBasePos', 'CreatePartName', 'TargetBase', 'TargetName', 'Power', 'HitBonusParameter', 'Flag0']:
        assert f in names, f
    base = ds.row(BASE_ROW)
    assert ds.get(base, 'Flag0') == 0 and ds.get(base, 'EnemyHitCategoryTypeBit') == 31 and ds.get(base, 'CreatePartName') == 'VFX_Muzzle01'
    out = []
    for key, beam, pack in BEAMS:
        assert key not in ds.at, key
        tpl = ds.row(beam)
        assert ds.get(tpl, 'ControlType') == 7, beam
        row = list(base)
        for f in SHOT_FIELDS:
            ds.set(row, f, ds.get(tpl, f))
        for f in CHAIN:                     # (no damage sources of its own made after it)
            ds.set(row, f, [])
        ds.set(row, 'CreateBasePos', 1)     # the weapon's
        ds.set(row, 'CreatePartName', 'VFX_Muzzle01')
        ds.set(row, 'TargetBase', 10)       # at the target
        ds.set(row, 'TargetName', None)
        for f in PLACE_FIELDS:
            ds.set(row, f, 0.0)
        control = list(ds.get(tpl, 'ControlParameter_Array'))
        while len(control) < 2:
            control.append(0.0)
        control[0], control[1] = SPEED, LENGTH
        ds.set(row, 'ControlParameter_Array', control)
        ds.set(row, 'Property', ds.get(base, 'Property'))   # (a gun's: the physical)
        ds.set(row, 'HitCount', 1)
        ds.set(row, 'HitInterval', 0.0)
        ds.set(row, 'LifeTime', LIFE)
        ds.set(row, 'LifeTimeNotify', 0)
        ds.set(row, 'MoveOnTerrain', 0)
        ds.set(row, 'HitGroupName', None)
        ds.set(row, 'HitSlowID', None)
        ds.set(row, 'DangerRange', 0.0)
        ds.set(row, 'CollisionParameter_Array', [RADIUS])
        ds.set(row, 'Power', POWER)
        ds.set(row, 'HitBonusParameter', BONUS)
        ds.add(key, row)
        out.append(dict(row=key, beam=beam, effect=ds.get(row, 'BindEffectResourceName'), hit=(ds.get(row, 'HitEffectResourceName_Array') or [None])[0],
                        pack=PACKS[pack]))
    return out


def main(base_dir, out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    chunks, store = P.read(os.path.join(base_dir, NAME + '.utoc'))
    k = [i for i, c in enumerate(chunks) if c['path'] == DAMAGE]
    assert len(k) == 1
    k = k[0]
    ds = quiet(B.Table, chunks[k]['data'])
    keys0 = list(ds.at)
    rows0 = {key: list(ds.row(key)) for key in keys0}
    made = make_rows(ds)
    table = quiet(ds.encode)
    # read back: every row as it was, the new ones as made, each one's effects named
    t2 = quiet(B.Table, table)
    assert list(t2.at)[:len(keys0)] == keys0 and len(t2.at) == len(keys0) + len(BEAMS)
    for key in keys0:
        assert t2.row(key) == rows0[key], key
    for m in made:
        r = t2.row(m['row'])
        assert t2.get(r, 'ControlType') == 7 and t2.get(r, 'CreateBasePos') == 1 and t2.get(r, 'CreatePartName') == 'VFX_Muzzle01'
        assert t2.get(r, 'BindEffectResourceName') == m['effect'] and t2.get(r, 'Power') == POWER and t2.get(r, 'Flag0') == 0
    chunks[k] = dict(chunks[k], data=table)
    entries = [P.entry(c, store[c['id64']]) for c in chunks if c['type'] == 2]
    for e in entries:
        if e['id'] == chunks[k]['id64']:
            e['size'] = len(table)
    os.makedirs(out)
    cid, files = P.write(out, NAME, chunks, entries, os.path.join(base_dir, NAME + '.pak'))
    # every other package as installed
    back, old = Toc(os.path.join(out, NAME + '.utoc')), Toc(os.path.join(base_dir, NAME + '.utoc'))
    old_by = {(old.chunk_id64(i), old.chunk_type(i)): i for i in range(old.entries)}
    same = 0
    for i in range(back.entries):
        key = (back.chunk_id64(i), back.chunk_type(i))
        if key[1] == 10:
            continue
        if back.files.get(i, '').endswith(DAMAGE):
            assert back.read(i) == table
        else:
            assert back.read(i) == old.read(old_by[key]), key
            same += 1
    report = ['%s -> %s (beam from VFX_Muzzle01 at the target, %.0f cm/s, %.0f cm, %.1f s, radius %.0f, power %d, ATB bonus %d); its effect pack %s'
              % (m['row'], m['effect'], SPEED, LENGTH, LIFE, RADIUS, POWER, BONUS, m['pack'].rsplit('.', 1)[-1]) for m in made]
    report.append('container %s: %d packages (%d as installed, the damage table: %d rows, %d bytes); %s' % (NAME, len(entries), same, len(t2.at), len(table), files))
    open(os.path.join(out, 'beams_report.txt'), 'w').write('\n'.join(report) + '\n')
    json.dump(made, open(os.path.join(out, 'beams.json'), 'w'), indent=1)
    print('\n'.join(report))


if __name__ == '__main__':
    main(*sys.argv[1:3])
