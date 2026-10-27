"""Name every import of a CharaSpec pack (the game's object table, then the blueprint's subobjects by their names)."""
import sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/hang1012/tools', '/work/evil1013/tools',
                '/work/swap1012/tools', '/work/vincentfix', '/work/weap1012/tools']
from zen import Zen
import gameids
import cityhash
PKG, OBJ = gameids.load()
NULL = 0xFFFFFFFFFFFFFFFF
BPDIR = '/Game/BluePrint/Character/Player/'
SUBS = ['DefaultSceneRoot_GEN_VARIABLE', 'EndBodySubCollisionSetting_GEN_VARIABLE', 'BattleTalk_Cloud_GEN_VARIABLE']
DEF_SUBS = ['CharMoveComp', 'CollisionCylinder', 'CharacterMesh0']


def import_index(path):
    s = ''.join('/' if c in '.:' else c.lower() for c in path)
    return (2 << 62) | (cityhash.CityHash64(s.encode('utf-16-le')) & ~(3 << 62))


def bp_names(bp):
    p = BPDIR + bp
    out = {import_index(p + '.' + bp + '_C'): p + '.' + bp + '_C', import_index(p + '.Default__' + bp + '_C'): p + '.Default__' + bp + '_C'}
    for s in SUBS:
        out[import_index(p + '.' + bp + '_C:' + s)] = p + '.' + bp + '_C:' + s
    for s in DEF_SUBS:
        out[import_index(p + '.Default__' + bp + '_C:' + s)] = p + '.Default__' + bp + '_C:' + s
    return out


def names(data, bps):
    z = Zen(data)
    known = {}
    for bp in bps:
        known.update(bp_names(bp))
    out = []
    for v in z.imports:
        if v == NULL:
            out.append(None); continue
        n = OBJ.get(v & ~(3 << 62)) or known.get(v)
        out.append(n or '%016x' % v)
    return out


if __name__ == '__main__':
    import glob
    for f in sys.argv[1:]:
        d = open(f, 'rb').read()
        z = Zen(d)
        bps = [n.split('/')[-1] for n in z.names if n.startswith(BPDIR)]
        print(f.split('__')[-1], 'blueprints named:', bps)
        for i, n in enumerate(names(d, bps + ['PC0000_00_Cloud_Standard', 'PC0011_00_Vincent_Standard'])):
            if n is not None: print('   %2d %s' % (i, n))
