"""A cooked material instance with its base property overrides set to two-sided (bOverride_TwoSided, TwoSided): the
renderer then draws both faces of what wears it (cull mode none), as the editor material it was made from does. The
rest of the property block and the export (the inline shader map after it) are copied unchanged."""
import sys

sys.path.insert(0, '/work/fx1018/editor/Python')
from rebirth_fx import matcore, uwrite      # noqa: E402

STRUCT = 'MaterialInstanceBasePropertyOverrides'


def set_two_sided(data, label=''):
    mi = matcore.MaterialInstance(data, label)
    u = matcore.usmap()
    ex_start, ex_size = mi.z.bundle_positions()[mi.index]
    ex = data[ex_start:ex_start + ex_size]
    v = mi.v
    props = v.value
    fields = {key: (None if x.zero else ex[x.at:x.at + x.size]) for key, x in props.items()}
    bpo = props.get('BasePropertyOverrides')
    sub = {}
    if bpo is not None and not bpo.zero:
        sub = {key: (None if x.zero else ex[x.at:x.at + x.size]) for key, x in bpo.value.items()}
    sub['bOverride_TwoSided'] = b'\x01'
    sub['TwoSided'] = b'\x01'
    fields['BasePropertyOverrides'] = uwrite.struct_bytes(u, STRUCT, sub)
    block = uwrite.struct_bytes(u, mi.cls, fields)
    new_ex = block + ex[v.at + v.size:]
    out = matcore.replace_export(data, mi.index, new_ex)
    back = matcore.MaterialInstance(out, label)
    b = back.v.value['BasePropertyOverrides'].value
    if not (b['bOverride_TwoSided'].value and b['TwoSided'].value):
        raise ValueError('%s: two-sided did not read back' % label)
    for key, x in bpo.value.items() if bpo is not None and not bpo.zero else ():
        if b[key].value != x.value:
            raise ValueError('%s: %s changed (%r -> %r)' % (label, key, x.value, b[key].value))
    if back.parent != mi.parent or len(back.params) != len(mi.params):
        raise ValueError('%s: the rest of the instance changed' % label)
    # the inline shader map (after the property block) is byte for byte the same
    s1, z1 = back.z.bundle_positions()[back.index]
    if out[s1 + back.v.at + back.v.size:s1 + z1] != ex[v.at + v.size:]:
        raise ValueError('%s: the data after the properties changed' % label)
    return out
