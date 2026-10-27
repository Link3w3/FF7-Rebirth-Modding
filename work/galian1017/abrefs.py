import sys, io, contextlib
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix', '/work/weap1012/tools']
import build_atb as B
with contextlib.redirect_stdout(io.StringIO()):
    ab = B.Table(open('/work/seph1013/tables/game_BattleAbility.uasset', 'rb').read())
    ds = B.Table(open('/work/seph1013/tables/game_BattleDamageSource.uasset', 'rb').read())
an = [f[0][0] for f in ab.fields]
print('ability fields:', an)
want = sys.argv[1:]
for key in ab.at:
    r = ab.row(key)
    vals = {n: ab.get(r, n) for n in an}
    flat = str(vals)
    if any(w in flat for w in want) or key in want:
        print('==', key, {k: v for k, v in vals.items() if v not in (None, [], '', 0, 0.0, False)})
dn = [f[0][0] for f in ds.fields]
for key in ['PC0000_NAtk_1_01', 'PC0000_NAtk_2_01', 'PC0000_NAtk_3_01', 'PC0000_NAtk_4_01', 'PC0000_NAtk_5_01', 'PC0001_NAtk_1_02', 'PC0001_NAtk_1_03', 'EB2020_03_AtkFollowShot_Renkei', 'PC0001_SAtk_1_01']:
    if key in ds.at:
        r = ds.row(key); v = {n: ds.get(r, n) for n in dn}
        print(key, 'Power', v['Power'], 'Flag0', v['Flag0'], 'HitReaction', v['HitReactionType_Array'], v['HitReactionParam_Array'], 'Cut', v['CutValue'], 'Stun', v['StunValue'], 'Coll', v['CollisionParameter_Array'], 'Ctl', v['ControlType'], v['ControlParameter_Array'][:3], 'Prop', v['Property'], 'EHB', v['EnemyHitCategoryTypeBit'], 'HitBonus', v['HitBonusType'], v['HitBonusParameter'], 'Crit', v['CriticalHitRate'], 'BurstBonus?', v.get('BurstValue'))
    else:
        print(key, 'not found')
