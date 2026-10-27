"""Vincent's guns as a player's: three BattleDamageSource rows of his own in FullyPlayableVincentAssets_P.

His guns fired rows of Elena's (EB2020_03_AtkShot_Renkei, EB2020_00_AtkShot01_Bullet, EB2020_03_AtkFollowShot_Renkei).
Those are the rows of an enemy's attack on the party: Flag0 0x40000000 (the game's enemy rows have it; the ally versions it
made of the same attacks, the *_NPC_* rows, do not), and the two Renkei rows hit one kind of character only
(EnemyHitCategoryTypeBit 2, where every player row has 31). Owned by Vincent, they hurt nothing.

The new rows are Barret's normal shot (PC0001_NAtk_1_01, a player's bullet: no Flag0, every kind of enemy) with
  * the bullet from VFX_Muzzle01 (the Quicksilver's muzzle; Barret's VFX_Muzzle02 is on his gun-arm),
  * no cartridge (WE9000_00_Gun_Cartridge, Barret's pack's), no muzzle effect or sounds of Barret's (the shooter plays
    Vincent's own gunshot and muzzle flash), the common gun hit effect (FX_R_Common_HitGun_01, as Elena's bullets have),
  * each gun's power, ATB bonus on a hit and reaction.
Everything else of the game's table is as it is (the game's own Resident table, pakchunk3, checked by its hash).
    build_gun_rows.py <out dir (new)> <base dir with FullyPlayableVincentAssets_P>"""
import contextlib, hashlib, io, json, os, struct, sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools', '/work/shooter1016/tools', '/work/prologue1016/tools',
                '/work/sephforms/tools']
import build_atb as B
import build_dirge_paks as P
import iostore_write as W
from iostore import Toc

NAME = 'FullyPlayableVincentAssets_P'
DAMAGE = 'DataObject/Resident/BattleDamageSource.uasset'
GAME_DAMAGE = '/work/seph1013/tables/game_BattleDamageSource.uasset'
GAME_TOC = '/work/seph1013/pakchunk3-WindowsNoEditor.utoc'   # (the PC's, md5 4d6164d1...)
TEMPLATE = 'PC0001_NAtk_1_01'
STRONG = 'PC0001_NAtk_1_03'   # Barret's finishing shot: a heavier reaction
GUNS = {
    # row: (power, ATB bonus on a hit, reaction from, bullet speed cm/s, life s)
    'PC0011_Dirge_Cerberus': dict(power=12, bonus=40, reaction=TEMPLATE, speed=12000.0, life=1.0),
    'PC0011_Dirge_Hydra': dict(power=5, bonus=15, reaction=TEMPLATE, speed=12000.0, life=1.0),
    'PC0011_Dirge_Griffon': dict(power=45, bonus=120, reaction=STRONG, speed=16000.0, life=1.0),
}


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def gun_rows(ds):
    """The rows added to the table (in place); returns a description of each."""
    names = [f[0][0] for f in ds.fields]
    base = list(ds.row(TEMPLATE))
    t = {n: ds.get(base, n) for n in names}
    assert t['Flag0'] == 0 and t['EnemyHitCategoryTypeBit'] == 31 and t['ControlType'] == 3 and t['CreateBasePos'] == 1, t
    assert t['CreatePartName'] == 'VFX_Muzzle02' and t['BindEffectResourceName'] == 'FX_R_Common_Bullet_01' and t['BindEffectResourceCategory'] == 30
    hit = ds.row('EB2020_00_AtkShot01_Bullet')
    assert ds.get(hit, 'HitEffectResourceName_Array') == ['FX_R_Common_HitGun_01'] and ds.get(hit, 'HitEffectResourceCategory_Array') == [30]
    out = []
    for key, g in GUNS.items():
        assert key not in ds.at, key
        row = list(base)
        ds.set(row, 'CreatePartName', 'VFX_Muzzle01')
        for f in ('CreatePhysicsObjectCharaSpecID', 'CreatePhysicsObjectPartName', 'CreateEffectResourceName', 'CreateSoundResourceName',
                  'HitSoundResourceName', 'BindSoundResourceName'):
            ds.set(row, f, None)
        for f in ('CreatePhysicsObjectForce', 'CreatePhysicsObjectForceRandom'):
            ds.set(row, f, 0.0)
        for f in ('CreatePhysicsObjectBasePos', 'CreateEffectResourceCategory', 'CreateSoundResourceCategory', 'HitSoundResourceCategory',
                  'BindSoundResourceCategory'):
            ds.set(row, f, 0)
        ds.set(row, 'HitEffectResourceName_Array', ['FX_R_Common_HitGun_01'])
        ds.set(row, 'HitEffectResourceCategory_Array', [30])
        ds.set(row, 'CollisionParameter_Array', [25.0])
        control = ds.get(row, 'ControlParameter_Array')
        control[0] = g['speed']
        ds.set(row, 'ControlParameter_Array', control)
        ds.set(row, 'LifeTime', g['life'])
        ds.set(row, 'Power', g['power'])
        ds.set(row, 'HitBonusParameter', g['bonus'])
        if g['reaction'] != TEMPLATE:
            src = ds.row(g['reaction'])
            for f in ('HitReactionType_Array', 'HitReactionParam_Array', 'AerialHitReactionParam_Array', 'BPAttack', 'BPAttackDamageCoefficient',
                      'HitForceFeedbackFileName'):
                ds.set(row, f, ds.get(src, f))
        ds.add(key, row)
        v = {n: ds.get(row, n) for n in names}
        out.append('%s: power %d, ATB bonus %d, reaction %s, from %s at %.0f cm/s for %.1f s, hit %s; Flag0 %d, hits every kind (%d), targets %s' % (
            key, v['Power'], v['HitBonusParameter'], v['HitReactionType_Array'], v['CreatePartName'], v['ControlParameter_Array'][0], v['LifeTime'],
            v['HitEffectResourceName_Array'][0], v['Flag0'], v['EnemyHitCategoryTypeBit'],
            ''.join(str(v['HitTarget%d' % k]) for k in range(7))))
    return out


def main(out, base_dir):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    game = open(GAME_DAMAGE, 'rb').read()
    toc = Toc(GAME_TOC)
    i = [k for k, p in toc.files.items() if p.endswith('/' + DAMAGE)][0]
    assert toc.b[toc.metas_off + 33 * i:toc.metas_off + 33 * i + 20] == hashlib.sha1(game).digest(), 'not the game\'s table'
    ds = quiet(B.Table, game)
    keys0 = list(ds.at)
    report = gun_rows(ds)
    table = quiet(ds.encode)
    # read back: the game's rows as they were, the new ones as made
    t2 = quiet(B.Table, table)
    g2 = quiet(B.Table, game)
    assert list(t2.at)[:len(keys0)] == keys0 and len(t2.at) == len(keys0) + len(GUNS)
    for k in keys0:
        assert t2.row(k) == g2.row(k), k
    for k in GUNS:
        assert t2.row(k) == ds.row(k), k
    # the container: the base's packages as they are, the table added
    chunks, store = P.read(os.path.join(base_dir, NAME + '.utoc'))
    entries = [P.entry(c, store[c['id64']]) for c in chunks if c['type'] == 2]
    assert not any(c['path'] == DAMAGE for c in chunks), 'the base has a damage table already'
    pid = W.package_id('/Game/' + DAMAGE[:-len('.uasset')])
    assert pid not in store
    chunks.append(dict(id64=pid, type=2, data=table, path=DAMAGE))
    entries.append(dict(id=pid, size=len(table), export_count=1, export_bundle_count=1, load_order=0, imports=[]))
    os.makedirs(out)
    cid, files = P.write(out, NAME, chunks, entries, os.path.join(base_dir, NAME + '.pak'))
    back = Toc(os.path.join(out, NAME + '.utoc'))
    old = Toc(os.path.join(base_dir, NAME + '.utoc'))
    old_by = {(old.chunk_id64(k), old.chunk_type(k)): k for k in range(old.entries)}
    same = 0
    for k in range(back.entries):
        key = (back.chunk_id64(k), back.chunk_type(k))
        if key[1] == 10:
            continue
        if key in old_by:
            assert back.read(k) == old.read(old_by[key]), key
            same += 1
        else:
            assert key == (pid, 2) and back.read(k) == table and back.files[k].endswith(DAMAGE)
    assert same == len([k for k in range(old.entries) if old.chunk_type(k) != 10])
    report.append('container %s: %d packages (%d of the base as they were, the damage table added: %d rows, %d bytes); %s' % (
        NAME, len(entries), same, len(t2.at), len(table), files))
    open(os.path.join(out, 'gun_report.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))


if __name__ == '__main__':
    main(*sys.argv[1:3])
