import sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix', '/work/weap1012/tools']
from iostore import Toc
from zen import Zen
import gameids
PKG, OBJ = gameids.load()
t = Toc('/work/sephatb/out4/FullyPlayableSephirothDataAssets_P.utoc')
idx = {v.replace('../../../End/Content/', '', 1): k for k, v in t.files.items()}
mine = t.read(idx['DataAsset/Game/CharaSpec/CharaSpec_PC0000_00_Cloud_Standard.uasset'])
retail = open('/work/gameextract/CharaSpec_PC0000_00_Cloud_Standard.uasset', 'rb').read()
def show(label, d):
    z = Zen(d)
    print('==', label, len(d), 'names', len(z.names), 'imports', len(z.imports), 'exports', len(z.exports))
    for n in z.names: print('   name', n)
    for v in z.imports:
        print('   imp %016x %s' % (v, OBJ.get(v & ((1 << 62) - 1), OBJ.get(v, '?'))))
    for e in z.exports: print('   exp', e)
show('retail 00', retail)
show('mine 00', mine)
