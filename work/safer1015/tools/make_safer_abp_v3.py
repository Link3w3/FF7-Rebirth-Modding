"""Safer's AnimBlueprint v3: v2 (Vincent's player AnimBlueprint on his skeleton) with its Control Rig node given no rig (the
common human rig places a person's hips by their legs; Safer has none), so the node passes the pose through."""
import struct, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/vincentfix', '/work/weap1012/tools',
                '/work/evil1013/tools', '/work/safer1015/tools']
from zen import Zen
import make_bp
import make_safer_abp_v2 as v2

NULL = 0xFFFFFFFFFFFFFFFF
RIG = ('/Game/Character/Common/ControlRig/CommonHuman00_Rig.CommonHuman00_Rig_C', '/Game/Character/Common/ControlRig/CommonHuman00_Rig.Default__CommonHuman00_Rig_C')


def make():
    data, entry = v2.make()
    z = Zen(data)
    d = bytearray(data)
    rig = {make_bp.imp(p) for p in RIG}
    hits = [i for i, v in enumerate(z.imports) if v in rig]
    assert len(hits) == 2, hits
    for i in hits:
        struct.pack_into('<Q', d, z.imp_off + 8 * i, NULL)
    return bytes(d), entry
