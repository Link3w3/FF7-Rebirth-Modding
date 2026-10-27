"""Builds the first custom material test: RMC_MagentaGlow (RMI_Particle_Emit's shader map, its six Niagara base pass pixel
shaders replaced by hlsl/particle_magenta.hlsl) and FX_RebirthCustom_Test (Cross Slash using it in place of
RMI_Particle_Emit), packed as RebirthCustomTest_P."""
import sys, struct, json, hashlib, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lz4.block
from custom_mi import rename_package, with_inline_shaders, unique_shader_map_id, wrap_shader, replace_import, find_frozen, parse_shader_map_tail
from shlib import Library
sys.path.insert(0, '/work/fx1018/editor/Python')
from rebirth_fx import matcore, fxcore

def carrier_shaders(bundle_path, lib, resource_hash):
    i = lib.map_index[resource_hash]; off, num, _, _ = lib.map_entries[i]
    order = [lib.indices[off + k] for k in range(num)]
    raw = open(bundle_path, 'rb').read()
    p = 0; comp = {}
    while p < len(raw):
        index, size, usize, freq = struct.unpack_from('<IIIB', raw, p); p += 13
        hsh = raw[p:p+20]; p += 20
        comp[index] = dict(hash=hsh, code=raw[p:p+size], usize=usize, freq=freq); p += size
    return order, comp

def build(dxbc_path, name, targets=(69, 70, 75, 4, 50, 92), out='out_test'):
    os.makedirs(out, exist_ok=True)
    data = open('/work/fx1018/pkgs/Renderer__MaterialInstance__Particle__RMI_Particle_Emit.uasset', 'rb').read()
    lib = Library('/data/uploads/FF7R2UProj/Saved/ModExtract/shlib/End_header.bin', 'End')
    mi0 = matcore.MaterialInstance(data, 'carrier')
    s0, z0 = mi0.z.bundle_positions()[mi0.index]
    t = parse_shader_map_tail(data[s0:s0 + z0], find_frozen(data[s0:s0 + z0], mi0.v.at + mi0.v.size))
    order, comp = carrier_shaders('/data/uploads/FF7R2UProj/Saved/ModExtract/shlib/RMI_Particle_Emit.bundle', lib, t['resource_hash'])
    mine = open(dxbc_path, 'rb').read()
    shaders = []
    for res, g in enumerate(order):
        s = dict(comp[g])
        if res in targets:
            blob = lz4.block.decompress(s['code'], uncompressed_size=s['usize'])
            new = wrap_shader(blob, mine)
            s = dict(hash=hashlib.sha1(new).digest(), code=new, usize=len(new), freq=s['freq'])
        shaders.append(s)
    mi = rename_package(data, name)
    mi, at = unique_shader_map_id(mi, name)
    mi = with_inline_shaders(mi, shaders)
    check = matcore.MaterialInstance(mi, 'check')
    assert not check.pkg.errors, check.pkg.errors
    # the property block must be the carrier's, untouched
    s1, z1 = check.z.bundle_positions()[check.index]
    assert mi[s1:s1 + check.v.size] == data[s0:s0 + mi0.v.size], 'properties changed'
    fx = open('/work/fx1018/pkgs/Effect__Character__Player__PC0000_Cloud__Particle__FX_PC0000_Limit01_CrossSlash_01.uasset', 'rb').read()
    fxname = '/Game/RebirthCustom/FX_RebirthCustom_Test/FX_RebirthCustom_Test'
    fx2 = rename_package(fx, fxname)
    obj = name + '.' + name.rsplit('/', 1)[-1]
    fx2 = replace_import(fx2, '/Game/Renderer/MaterialInstance/Particle/RMI_Particle_Emit.RMI_Particle_Emit', obj)
    assert not fxcore.Package(fx2).errors
    headers = [open('pakchunk3_container_header.bin', 'rb').read(), open('pakchunk4_container_header.bin', 'rb').read()]
    like = {name: '/Game/Renderer/MaterialInstance/Particle/RMI_Particle_Emit',
            fxname: '/Game/Effect/Character/Player/PC0000_Cloud/Particle/FX_PC0000_Limit01_CrossSlash_01'}
    files = fxcore.build_mod([mi, fx2], headers, out, 'RebirthCustomTest_P', like=like)
    return files, at

if __name__ == '__main__':
    files, at = build('hlsl/particle_magenta.dxbc', '/Game/RebirthCustom/RMC_MagentaGlow/RMC_MagentaGlow')
    print('id hash at', at)
    for f in files: print(f, os.path.getsize(f))
