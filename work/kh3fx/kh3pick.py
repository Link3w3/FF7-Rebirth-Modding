"""Picks a KH3 material's base pass pixel shader to translate (mesh particles first, then sprites, then static meshes)
and finds where the material's own code ends."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, '/work/kh3bnm/src/rebirth_fx']
import kh3bonamik as k   # noqa: E402
import kh3dxbc           # noqa: E402
import dxbcir            # noqa: E402

VF_ORDER = ['FMeshParticleVertexFactory', 'FParticleSpriteVertexFactory', 'FLocalVertexFactory',
            'FParticleBeamTrailVertexFactory', 'FGPUSpriteVertexFactory']
DEBUG_VIEW = {122, 123, 126}


def shaders(pk):
    """[(shader type, vertex factory, blob)] for every DXBC blob, typed from the names written before it."""
    data = pk.data
    out = []
    prev = 0
    for b in kh3dxbc.blobs(data):
        near = kh3dxbc.names_near(pk, data, prev, b['offset'])
        prev = b['offset'] + b['size']
        types = [s for _, s in near if not s.endswith('VertexFactory')]
        vfs = [s for _, s in near if s.endswith('VertexFactory')]
        out.append((types[-1] if types else None, vfs[-1] if vfs else None, b))
    return out


def pick(pk):
    sh = shaders(pk)
    for vf in VF_ORDER:
        for t, v, b in sh:
            if t == 'TBasePassPSFNoLightMapPolicy' and v == vf:
                return vf, b
    for t, v, b in sh:
        if t and t.startswith('TBasePassPS'):
            return v, b
    return None, None


def cut(code):
    """Index of the first instruction of the engine's code after the material: KH3's debug view block (View rows
    122/123/126) or, for opaque materials, the GBuffer's per-object flags (Primitive rows 17/18)."""
    for i, ins in enumerate(code):
        for o in ins.ops:
            if o.file == 'cb' and o.index and isinstance(o.index[1], int) and (
                    (o.index[0] == 0 and o.index[1] in DEBUG_VIEW) or (o.index[0] == 1 and o.index[1] in (17, 18))):
                return i
    return len(code)
