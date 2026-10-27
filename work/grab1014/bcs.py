exec(open('tables.py').read().split("for p in sorted")[0])
bc = load('p3/pkgs/DataObject__Resident__BattleCharaSpec.uasset')
keys = list(bc.at)
print(len(keys), keys[:12], keys[-5:])
from collections import Counter
sr = Counter(); cats = Counter()
for k in keys:
    r = bc.row(k)
    sr[tuple(bc.get(r, 'SpecialResist_Array'))] += 1
    cats[bc.get(r, 'EnemyCategory')] += 1
print('SpecialResist variants:', len(sr))
for v, n in sr.most_common(25): print('  %4d  %r' % (n, v))
print('EnemyCategory:', cats.most_common())
for k in ['PC0000_00_Cloud_Standard', 'PC0010_20_Sephiroth_VRHard', 'EN0000_00_SecuritySoldier_Standard'] + keys[:3]:
    if k in bc.at:
        r = bc.row(k)
        print(k, 'special', bc.get(r, 'SpecialResist_Array'), 'status', bc.get(r, 'StatusChangeResist_Array'), 'cat', bc.get(r, 'EnemyCategory'), 'flag', hex(bc.get(r, 'FlagBit0')))
