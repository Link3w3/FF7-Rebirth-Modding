exec(open('tables.py').read().split("for p in sorted")[0])
bc = load('p3/pkgs/DataObject__Resident__BattleCharaSpec.uasset')
from collections import Counter
c = Counter(bc.get(bc.row(k), 'KeepValue') for k in bc.at)
print('BattleCharaSpec KeepValue:', sorted(c.items()))
for k in ['EN0000_00_SecuritySoldier_Standard', 'EN2000_00_GuardHound_Standard', 'EN2015_00_Bomb_Standard', 'PC0010_20_Sephiroth_VRHard']:
    if k in bc.at: print(k, bc.get(bc.row(k), 'KeepValue'))
print([k for k in bc.at if 'GuardHound' in k][:5])
dm = B.Table(open(B.GAME_DAMAGE, 'rb').read())
c2 = Counter(dm.get(dm.row(k), 'CutValue') for k in dm.at)
print('damage source CutValue:', sorted(c2.items())[:40])
pc = Counter(dm.get(dm.row(k), 'CutValue') for k in dm.at if k.startswith('PC00'))
print('player damage CutValue:', sorted(pc.items()))
