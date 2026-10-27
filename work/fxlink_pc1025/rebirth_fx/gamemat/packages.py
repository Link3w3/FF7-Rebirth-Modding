"""The game packages of a custom material:

  carrier copy   one of the game's RMI_Surface_* material instances under a new name, its shader map carrying its shader
                 code inline with the material's own pixel shaders in place of the carrier's (custom_mi)
  material       a game material instance (a template: one of the game's character MIs) re-parented to the carrier copy,
                 under the editor material's own path, with the material's textures on the carrier's texture parameters
"""
import hashlib

from .. import matcore
from .. import uwrite
from .custom_mi import rename_package, with_inline_shaders, unique_shader_map_id, replace_import

BPO = 'MaterialInstanceBasePropertyOverrides'


def object_path(package):
    return package + '.' + package.rsplit('/', 1)[-1]


def carrier_package(new_name, carrier_data, raw_shaders, blobs, report=None):
    """The carrier copy: raw_shaders the carrier's library shaders in its shader map's order, blobs {resource index: new
    pixel shader blob}."""
    shaders = []
    for res, s in enumerate(raw_shaders):
        if res in blobs:
            if s['freq'] != 5:
                raise ValueError('resource %d is not a pixel shader' % res)
            new = blobs[res]
            shaders.append(dict(hash=hashlib.sha1(new).digest(), code=new, usize=len(new), freq=s['freq']))
        else:
            shaders.append(dict(hash=s['hash'], code=s['code'], usize=s['usize'], freq=s['freq']))
    old = matcore.MaterialInstance(carrier_data, 'carrier')
    mi = rename_package(carrier_data, new_name)
    mi, _ = unique_shader_map_id(mi, new_name)
    mi = with_inline_shaders(mi, shaders)
    check = matcore.MaterialInstance(mi, 'check')
    if check.pkg.errors:
        raise ValueError('the carrier copy does not read back: %s' % check.pkg.errors)
    s1, z1 = check.z.bundle_positions()[check.index]
    s0, z0 = old.z.bundle_positions()[old.index]
    if mi[s1:s1 + check.v.size] != carrier_data[s0:s0 + old.v.size]:
        raise ValueError('the carrier copy\'s property block changed')
    if report is not None:
        report.setdefault('carriers', {})[new_name] = dict(replaced=sorted(blobs), size=len(mi), shaders=len(shaders))
    return mi


def game_mi(new_name, template_data, carrier_name, slot_textures, report=None):
    """The material: template_data a game MI package, re-parented to carrier_name and renamed new_name;
    slot_textures {carrier parameter name: texture object path}."""
    template = matcore.MaterialInstance(template_data, 'template')
    if not template.parent:
        raise ValueError('the template material instance has no parent')
    out = replace_import(template_data, template.parent, object_path(carrier_name))
    out = rename_package(out, new_name)
    mi = matcore.MaterialInstance(out, new_name.rsplit('/', 1)[-1])
    changes = [dict(kind='texture', name=n, value=v) for n, v in sorted(slot_textures.items())]
    out, lines = matcore.edit(mi, changes)
    back = matcore.MaterialInstance(out, 'check')
    if back.pkg.errors or back.parent != object_path(carrier_name):
        raise ValueError('%s does not read back: %s %s' % (new_name, back.pkg.errors, back.parent))
    for n, v in slot_textures.items():
        p = back.find('texture', n)
        if p is None or p['value'] != v:
            raise ValueError('%s: %s is %s, wanted %s' % (new_name, n, p and p['value'], v))
    if report is not None:
        report.setdefault('mis', {})[new_name] = dict(parent=back.parent, textures=dict(slot_textures), edits=lines, size=len(out))
    return out


def set_two_sided(data, label=''):
    """A cooked material instance with bOverride_TwoSided / TwoSided set in its base property overrides (in the game's
    layout: the usmap's): the renderer then draws both faces of what wears it. Everything else stays as it was."""
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
    fields['BasePropertyOverrides'] = uwrite.struct_bytes(u, BPO, sub)
    block = uwrite.struct_bytes(u, mi.cls, fields)
    new_ex = block + ex[v.at + v.size:]
    out = matcore.replace_export(data, mi.index, new_ex)
    back = matcore.MaterialInstance(out, label)
    b = back.v.value['BasePropertyOverrides'].value
    if not (b['bOverride_TwoSided'].value and b['TwoSided'].value):
        raise ValueError('%s: two-sided did not read back' % label)
    if back.parent != mi.parent or len(back.params) != len(mi.params):
        raise ValueError('%s: the rest of the instance changed' % label)
    s1, z1 = back.z.bundle_positions()[back.index]
    if out[s1 + back.v.at + back.v.size:s1 + z1] != ex[v.at + v.size:]:
        raise ValueError('%s: the data after the properties changed' % label)
    return out
