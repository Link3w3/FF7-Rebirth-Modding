"""DXBC/DXIL container parsing for UE 4.26 D3D shader code blobs (FINAL FANTASY VII REBIRTH, PCD3D_SM6)."""
import struct
KINDS = {0: 'Pixel', 1: 'Vertex', 2: 'Geometry', 3: 'Hull', 4: 'Domain', 5: 'Compute', 6: 'Library', 7: 'RayGen', 8: 'Intersection',
         9: 'AnyHit', 10: 'ClosestHit', 11: 'Miss', 12: 'Callable', 13: 'Mesh', 14: 'Amplification'}

def container(blob, at):
    assert blob[at:at + 4] == b'DXBC', blob[at:at+4]
    digest = blob[at + 4:at + 20]
    major, minor, total, nparts = struct.unpack_from('<HHII', blob, at + 20)
    offs = struct.unpack_from('<%dI' % nparts, blob, at + 32)
    parts = []
    for o in offs:
        fourcc = blob[at + o:at + o + 4].decode('latin1')
        size = struct.unpack_from('<I', blob, at + o + 4)[0]
        parts.append((fourcc, at + o + 8, size))
    return dict(at=at, total=total, digest=digest, parts=parts)

def program(blob, c):
    for fourcc, o, size in c['parts']:
        if fourcc == 'DXIL':
            ver, sz = struct.unpack_from('<II', blob, o)
            kind = ver >> 16; major = (ver >> 4) & 0xf; minor = ver & 0xf
            return KINDS.get(kind, kind), '%d.%d' % (major, minor)
    return None, None

def signature(blob, o):
    """ISG1/OSG1/PSG1 parts: list of (semantic, index, register, mask, sysvalue, comptype, stream)."""
    n, first = struct.unpack_from('<II', blob, o)
    out = []
    for i in range(n):
        e = o + first + i * 32
        stream, nameoff, semidx, sysval, comptype, reg, mask, rwmask, minprec = struct.unpack_from('<IIIIIIBBxxI', blob, e)[:9]
        end = blob.index(b'\0', o + nameoff)
        name = blob[o + nameoff:end].decode('latin1')
        out.append((name, semidx, reg, mask, sysval, comptype, stream))
    return out

RES_TYPES = {0: 'Invalid', 1: 'Sampler', 2: 'CBV', 3: 'SRVTyped', 4: 'SRVRaw', 5: 'SRVStructured', 6: 'UAVTyped', 7: 'UAVRaw',
             8: 'UAVStructured', 9: 'UAVStructuredWithCounter'}

def psv0_resources(blob, c):
    """[(type, space, lower, upper)] resource bindings from the PSV0 part."""
    for fourcc, o, size in c['parts']:
        if fourcc != 'PSV0':
            continue
        rt_size = struct.unpack_from('<I', blob, o)[0]
        p = o + 4 + rt_size
        n = struct.unpack_from('<I', blob, p)[0]; p += 4
        out = []
        if n:
            esz = struct.unpack_from('<I', blob, p)[0]; p += 4
            for k in range(n):
                t, sp, lo, hi = struct.unpack_from('<IIII', blob, p + k * esz)
                out.append((RES_TYPES.get(t, t), sp, lo, hi))
        return out
    return []
