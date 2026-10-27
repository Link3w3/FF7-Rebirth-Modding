import sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix', '/work/weap1012/tools']
import build_atb as B
from iostore import Toc
retail = B.Table(open('/work/cs/raw/retail_CharaSpec.uasset', 'rb').read())
t = Toc('/work/sephatb/out4/FullyPlayableSephirothDataAssets_P.utoc')
idx = {v.replace(B.MOUNT, '', 1): k for k, v in t.files.items()}
mod = B.Table(t.read(idx[B.CHARASPEC_TABLE]))
fields = [f[0][0] for f in retail.fields]
print('rows retail', len(retail.keys), 'mod', len(mod.keys))
cloud_rows = sorted(k for k in retail.at if k.startswith('PC0000_'))
print('\n'.join(cloud_rows))
# fields the swap changed in each swapped row
for name in ['PC0000_00_Cloud_Standard', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing', 'PC0000_10_Cloud_CostaClothing2']:
    a, b = retail.row(name), mod.row(name)
    print('==', name)
    for f in fields:
        va, vb = retail.get(a, f), mod.get(b, f)
        if va != vb:
            print('   %-36s %r\n   %-36s -> %r' % (f, va, '', vb))
