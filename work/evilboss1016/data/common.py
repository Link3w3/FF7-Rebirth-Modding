import sys, contextlib, io
sys.path[:0] = ['/work/safer1016/tools', '/work/sephatb/tools', '/work/iostore', '/work/cs',
                '/work/tools', '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools', '/work/gunmoves', '/work/sephforms/tools', '/work/neutral20/tools']
import merge_fullyplayable as M
import build_atb as B
BASE = '/work/levelsets1016/out1/FullyPlayableSephirothDataAssets_P.utoc'
ABILITY = 'DataObject/Resident/BattleAbility.uasset'
DAMAGE = 'DataObject/Resident/BattleDamageSource.uasset'


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def tables(base=BASE):
    chunks, store = M.read(base)
    by = {c['path']: c for c in chunks if c['path']}
    return chunks, store, quiet(B.Table, by[ABILITY]['data']), quiet(B.Table, by[DAMAGE]['data'])
