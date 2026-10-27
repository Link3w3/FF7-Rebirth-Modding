"""Reading the game's frozen FMaterialShaderMapContent (UE 4.26 memory image, Windows layout)."""
import struct
def ptr(fz, at):
    v = struct.unpack_from('<q', fz, at)[0]
    if v == 0: return None
    assert v & 1, ('not frozen', at, v)
    return at + (v >> 1)
def arr(fz, at):
    p = ptr(fz, at); n, m = struct.unpack_from('<ii', fz, at + 8)
    return p, n
SHADER_TYPE, SHADER_VF, SHADER_TARGET, SHADER_RESOURCE, SHADER_NUMINSTR = 0xb0, 0xb8, 0xc0, 0xc4, 0xc8
def content(fz, at):
    """FShaderMapContent at `at`: (shader type hashes, permutations, [shader offsets], pipelines count, platform)."""
    tp, tn = arr(fz, at + 0x18)
    pp, pn = arr(fz, at + 0x28)
    sp, sn = arr(fz, at + 0x38)
    lp, ln = arr(fz, at + 0x48)
    types = [struct.unpack_from('<Q', fz, tp + 8 * k)[0] for k in range(tn)] if tn else []
    perms = [struct.unpack_from('<i', fz, pp + 4 * k)[0] for k in range(pn)] if pn else []
    shaders = [ptr(fz, sp + 8 * k) for k in range(sn)] if sn else []
    return types, perms, shaders, ln, fz[at + 0x58]
def shader(fz, at):
    t, vf = struct.unpack_from('<QQ', fz, at + SHADER_TYPE)
    target, res, ni = struct.unpack_from('<IiI', fz, at + SHADER_TARGET)
    return dict(type=t, vf=vf, target=target, resource=res, instructions=ni)

TYPE_FIELD, VF_FIELD = 0xd8, 0xe0
TARGET_FIELD, RESOURCE_FIELD = 0xe8, 0xec

def material_shaders(fz, types_tab, vfs_tab):
    """[(vf hash, shader type hash, permutation, frequency, platform, resource index, object offset)] of a frozen
    FMaterialShaderMapContent (the game's layout: mesh shader maps at +0x60)."""
    out = []
    mp, mn = arr(fz, 0x60)
    for k in range(mn):
        m = ptr(fz, mp + 8 * k)
        types, perms, shaders, nl, plat = content(fz, m)
        vf = struct.unpack_from('<Q', fz, m + 0x60)[0]
        for t, perm, s in zip(types, perms, shaders):
            ti, vi = struct.unpack_from('<qq', fz, s + TYPE_FIELD)
            target, res = struct.unpack_from('<Ii', fz, s + TARGET_FIELD)
            assert types_tab[ti >> 1] == t, (hex(t), ti)
            assert vfs_tab[vi >> 1] == vf, (hex(vf), vi)
            out.append((vf, t, perm, target & 0xf, target >> 4, res, s))
    return out
