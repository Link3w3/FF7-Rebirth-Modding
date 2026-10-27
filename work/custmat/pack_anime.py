"""Packs AnimeShader on Cloud: one carrier package per RMI_Surface_* parent Cloud's materials use (its shader map inline,
the skinned base pass pixel shaders replaced by AnimeShader's), and Cloud's materials pointing at them."""
import hashlib, json, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lz4.block
from custom_mi import rename_package, with_inline_shaders, unique_shader_map_id, wrap_shader, replace_import, find_frozen, parse_shader_map_tail
from carriers import Carrier, PKGS
sys.path.insert(0, '/work/fx1018/editor/Python')
from rebirth_fx import matcore, fxcore

B = '/data/uploads/FF7R2UProj/Saved/ModExtract/shlib/anime/'
PS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'anime', 'ps')
NEW_ROOT = '/Game/RebirthCustom/AnimeShader/'
CLOUD = {   # Cloud's materials -> their parent (the carrier); eyes and the petrified (Rock) variants keep their own
    'PC0000_00_ArmA': 'RMI_Surface_Standard_Wide', 'PC0000_00_Bottms': 'RMI_Surface_Standard_Wide',
    'PC0000_00_Eyelash': 'RMI_Surface_Standard_Wide', 'PC0000_00_Shoulder': 'RMI_Surface_Standard_Wide',
    'PC0000_00_TopsB': 'RMI_Surface_Standard_Wide',
    'PC0000_00_ArmB': 'RMI_Surface_Standard_Coverage_Wide', 'PC0000_00_Eyebrow': 'RMI_Surface_Standard_Coverage_Wide',
    'PC0000_00_Hair': 'RMI_Surface_Hair_Wide',
    'PC0000_00_Head': 'RMI_Surface_Skin_Wide_Detail', 'PC0000_00_Skin': 'RMI_Surface_Skin_Wide_Detail',
    'PC0000_00_Pants': 'RMI_Surface_Fabric_Wide', 'PC0000_00_TopsA': 'RMI_Surface_Fabric_Wide',
}


def raw_bundle(path):
    raw = open(path, 'rb').read()
    p = 0
    out = []
    while p < len(raw):
        index, size, usize, freq = struct.unpack_from('<IIIB', raw, p); p += 13
        hsh = raw[p:p + 20]; p += 20
        out.append(dict(index=index, hash=hsh, code=raw[p:p + size], usize=usize, freq=freq)); p += size
    return out


def carrier_package(rmi, new_name, report):
    path = PKGS + 'Renderer__MaterialInstance__Surface__%s.uasset' % rmi
    data = open(path, 'rb').read()
    c = Carrier(path)
    bundle = raw_bundle(B + rmi + '.bundle')
    assert [b['index'] for b in bundle] == c.order, 'bundle order differs from the shader map'
    built = json.load(open(os.path.join(PS, 'report.json')))[rmi]
    replace = {int(k): v for k, v in built.items()}
    shaders = []
    for res, s in enumerate(bundle):
        if res in replace:
            assert not replace[res]['problems'], replace[res]['problems']
            blob = lz4.block.decompress(s['code'], uncompressed_size=s['usize']) if len(s['code']) != s['usize'] else s['code']
            new = wrap_shader(blob, open(replace[res]['dxbc'], 'rb').read())
            assert s['freq'] == 5
            shaders.append(dict(hash=hashlib.sha1(new).digest(), code=new, usize=len(new), freq=s['freq']))
        else:
            shaders.append(dict(hash=s['hash'], code=s['code'], usize=s['usize'], freq=s['freq']))
    mi = rename_package(data, new_name)
    mi, at = unique_shader_map_id(mi, new_name)
    mi = with_inline_shaders(mi, shaders)
    check = matcore.MaterialInstance(mi, 'check')
    assert not check.pkg.errors, check.pkg.errors
    s1, z1 = check.z.bundle_positions()[check.index]
    s0, z0 = c.mi.z.bundle_positions()[c.mi.index]
    assert mi[s1:s1 + check.v.size] == data[s0:s0 + c.mi.v.size], 'the property block changed'
    report[new_name] = dict(carrier=rmi, replaced=sorted(replace), size=len(mi), shaders=len(shaders))
    return mi


def main(out_dir, mod_name='AnimeShaderCloud_P'):
    report = {}
    packages, like = [], {}
    carriers = {}
    for rmi in sorted(set(CLOUD.values())):
        new_name = NEW_ROOT + 'AnimeShader_' + rmi.replace('RMI_Surface_', '')
        packages.append(carrier_package(rmi, new_name, report))
        like[new_name] = '/Game/Renderer/MaterialInstance/Surface/' + rmi
        carriers[rmi] = new_name
    for mat, rmi in sorted(CLOUD.items()):
        path = PKGS + 'Character__Player__PC0000_00_Cloud_Standard__Material__%s.uasset' % mat
        data = open(path, 'rb').read()
        old = '/Game/Renderer/MaterialInstance/Surface/%s.%s' % (rmi, rmi)
        new = carriers[rmi] + '.' + carriers[rmi].rsplit('/', 1)[-1]
        out = replace_import(data, old, new)
        mi = matcore.MaterialInstance(out, mat)
        assert not mi.pkg.errors and mi.parent == new, (mi.parent, mi.pkg.errors)
        packages.append(out)
        report['/Game/Character/Player/PC0000_00_Cloud_Standard/Material/' + mat] = dict(parent=new, size=len(out))
    headers = [open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pakchunk%d_container_header.bin' % n), 'rb').read() for n in (3, 4)]
    files = fxcore.build_mod(packages, headers, out_dir, mod_name, like=like)
    json.dump(report, open(os.path.join(out_dir, mod_name + '.report.json'), 'w'), indent=1)
    return files, report


if __name__ == '__main__':
    files, report = main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'anime', 'out'))
    for f in files:
        print(f, os.path.getsize(f))
    for k, v in report.items():
        print(k, v)
