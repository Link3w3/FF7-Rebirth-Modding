exec(open('tables.py').read().split("for p in sorted")[0])
bc = load('p3/pkgs/DataObject__Resident__BattleCharaSpec.uasset')
from collections import defaultdict
by = defaultdict(list)
for k in bc.at:
    r = bc.row(k)
    by[bc.get(r, 'FlagBit0')].append(k)
for v in sorted(by):
    ks = by[v]
    print('%-10s %4d  %s' % (hex(v), len(ks), ', '.join(ks[:8])))
