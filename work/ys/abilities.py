"""The installed data container's BattleAbility rows: name, animations, text (for picking Young Sephiroth's commands)."""
import io, contextlib, sys, json
sys.path[:0] = ['/work/forms36/tools', '/work/sephatb/tools', '/work/iostore',
                '/work/cs', '/work/tools', '/work/evil1013/tools', '/work/swap1012/tools',
                '/work/vincentfix', '/work/weap1012/tools']
import build_atb as B
from iostore import Toc
BASE = '/work/evilplay1016/out1/FullyPlayableSephirothDataAssets_P.utoc'
MOUNT = '../../../End/Content/'


def table(path):
    t = Toc(BASE)
    for i in range(t.entries):
        if t.files.get(i) == MOUNT + path:
            with contextlib.redirect_stdout(io.StringIO()):
                return B.Table(t.read(i))
    raise KeyError(path)


if __name__ == '__main__':
    ab = table('DataObject/Resident/BattleAbility.uasset')
    fields = [f[0][0] for f in ab.fields]
    print(len(ab.keys), 'rows; fields:', fields[:80])
