import sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix', '/work/weap1012/tools']
import build_atb as B
retail = B.Table(open('/work/cs/raw/retail_CharaSpec.uasset', 'rb').read())
fields = [f[0][0] for f in retail.fields]
base = retail.row('PC0000_00_Cloud_Standard')
for name in ['PC0000_04_Cloud_ZackCostume', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
             'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet', 'PC0000_22_Cloud_StandardWet']:
    r = retail.row(name)
    print('==', name, '(differs from retail PC0000_00_Cloud_Standard in:)')
    for f in fields:
        a, b = retail.get(base, f), retail.get(r, f)
        if a != b:
            print('   %-36s %r' % (f, b))
