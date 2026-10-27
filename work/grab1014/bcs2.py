exec(open('tables.py').read().split("for p in sorted")[0])
bc = load('p3/pkgs/DataObject__Resident__BattleCharaSpec.uasset')
for k in bc.at:
    r = bc.row(k)
    s = bc.get(r, 'SpecialResist_Array')
    if not s or s[0] != 5:
        print('%-50s special %-12s cat %d flag %s' % (k, s, bc.get(r, 'EnemyCategory'), hex(bc.get(r, 'FlagBit0'))))
