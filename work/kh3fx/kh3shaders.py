"""The compiled shaders inside a KH3 cooked material (UE 4.17 + SQEX, D3D11): every DXBC blob with its shader type,
vertex factory, the names of the uniform buffers bound at each constant buffer slot (from the shader's optional data,
key 'u') and the bind slots of the uniform buffers' textures and samplers (the D3D11 resource table written just
before the bytecode).

    shaders(pk) -> [Shader]
"""
import struct
import sys

sys.path[:0] = ['/work/kh3fx', '/work/kh3bnm/src/rebirth_fx']
import kh3dxbc   # noqa: E402

TYPE_PREFIXES = ('TBasePass', 'TShadowDepth', 'FDepthOnly', 'TDepthOnly', 'FHitProxy', 'FVelocity', 'FFPostProcess',
                 'FPostProcess', 'TLightMapDensity', 'FDebugView', 'FConvertToUniform', 'FEvaluateSurfel',
                 'TTranslucency', 'FOnePass', 'FMeshDecal', 'TDeferredDecal', 'FDeferredDecal', 'FDistortion',
                 'TDistortion', 'FTranslucent', 'TMobile', 'FSelfShadow', 'FSqex', 'FSQEX', 'TSqex', 'TSQEX')


class Shader(object):
    def __init__(self, type_name, vf, blob, offset, ubs, textures, samplers, counts):
        self.type, self.vf, self.blob, self.offset = type_name, vf, blob, offset
        self.ubs = ubs              # [name] by constant buffer slot
        self.textures = textures    # {(ub slot, resource index): t slot}
        self.samplers = samplers    # {(ub slot, resource index): s slot}
        self.counts = counts        # (samplers, srvs, cbs, uavs)
        self.program = blob and kh3dxbc.blobs(blob)[0]['program']

    def __repr__(self):
        return '<%s %s %s ubs=%s>' % (self.type, self.vf, self.program, self.ubs)


def _u32(d, p):
    return struct.unpack_from('<I', d, p)[0]


def _resource_map(arr):
    """A resource table map (TArray<uint32>): per uniform buffer slot an offset, then each slot's entries
    (ub << 24 | resource << 8 | bind) up to 0xffffffff."""
    out = {}
    if not arr:
        return out
    head = None
    for i, v in enumerate(arr):
        if v != 0:
            head = v
            break
    if head is None or head > len(arr):
        return out
    for slot in range(head):
        start = arr[slot]
        if not start:
            continue
        j = start
        while j < len(arr) and arr[j] != 0xFFFFFFFF:
            v = arr[j]
            out[(v >> 24, (v >> 8) & 0xFFFF)] = v & 0xFF
            j += 1
    return out


def _valid_map(arr):
    """A resource table map: offsets for the first H uniform buffer slots (0 = none), then each slot's entries ending
    with 0xffffffff."""
    if not arr:
        return True
    if arr[-1] == 0xFFFFFFFF and all(v == 0 for v in arr[:-1]):
        return True                          # no entries for any slot
    head = next((v for v in arr if v != 0), None)
    if head is None or head > len(arr) or arr[-1] != 0xFFFFFFFF:
        return False
    for v in arr[:head]:
        if v != 0 and not head <= v < len(arr):
            return False
    return all(v != 0xFFFFFFFF for v in arr[:head])


def _array_ending_at(d, pos, check, prefer=None):
    """The TArray<uint32> ending at pos whose entries pass check (smallest count that does)."""
    counts = [prefer] if prefer is not None else []
    counts += list(range(0, 512))
    for count in counts:
        p = pos - 4 - 4 * count
        if p < 0:
            continue
        if _u32(d, p) != count:
            continue
        arr = [_u32(d, p + 4 + 4 * i) for i in range(count)]
        if check(arr):
            return p, arr
    return None


def _arrays_before(d, end, n_arrays=5):
    """SRV map, sampler map, UAV map, layout hashes and texture map of the D3D11 resource table that ends right before
    the bytecode at end."""
    tex = _array_ending_at(d, end, _valid_map)
    if tex is None:
        return None
    p, texmap = tex
    head = next((v for v in texmap if v != 0), 0) if texmap else None
    hashes = _array_ending_at(d, p, lambda a: True, prefer=head)
    if hashes is None:
        return None
    p, hs = hashes
    out = [texmap, hs]
    for _ in range(3):
        m = _array_ending_at(d, p, _valid_map)
        if m is None:
            return None
        p, arr = m
        out.append(arr)
    texmap, hs, uav, sampler, srv = out
    return (srv, sampler, uav, hs, texmap), p


def _optional(d, p, limit):
    """Optional shader data after the bytecode: (key u8, size u32, bytes) entries."""
    out = {}
    while p + 5 <= limit:
        key = d[p]
        size = _u32(d, p + 1)
        if size > 4096 or not (0x20 <= key < 0x7F):
            break
        out[chr(key)] = d[p + 5:p + 5 + size]
        p += 5 + size
        if len(out) >= 4:
            break
    return out


def _ub_names(data):
    if not data or len(data) < 4:
        return []
    n = _u32(data, 0)
    p = 4
    names = []
    for _ in range(n):
        ln = struct.unpack_from('<i', data, p)[0]
        p += 4
        names.append(data[p:p + ln - 1].decode('latin1'))
        p += ln
    return names


def shaders(pk):
    data = pk.data
    want = {}
    for i, s in enumerate(pk.names):
        if 'VertexFactory' in s or s.startswith(TYPE_PREFIXES):
            want[i] = s
    out = []
    prev = 0
    for b in kh3dxbc.blobs(data):
        t = vf = None
        q = b['offset'] - 8
        while q >= prev:
            i, n = struct.unpack_from('<ii', data, q)
            if n == 0 and i in want:
                s = want[i]
                if 'VertexFactory' in s:
                    if vf is None:
                        vf = s
                elif t is None:
                    t = s
            if t is not None and vf is not None:
                break
            q -= 1
        end = b['offset'] + b['size']
        opt = _optional(data, end, end + 4096)
        ubs = _ub_names(opt.get('u'))
        counts = tuple(opt['p'][1:5]) if 'p' in opt and len(opt['p']) >= 5 else None
        tex, smp = {}, {}
        got = _arrays_before(data, b['offset'], 5)
        if got:
            srv, sampler, uav, hashes, texmap = got[0]
            tex = _resource_map(texmap)
            smp = _resource_map(sampler)
        out.append(Shader(t, vf, b['blob'], b['offset'], ubs, tex, smp, counts))
        prev = end
    return out


def pick(shs, type_name, vfs):
    for vf in vfs:
        for s in shs:
            if s.type == type_name and s.vf == vf:
                return s
    return None
