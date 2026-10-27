"""Minimal DXBC reader: chunks, program type, RDEF (constant buffers with their variables, bound resources),
input/output signatures. (D3D11 shader model 5 blobs as Dissidia NT's SPKG packages hold them.)"""
import struct

PROG = {0: 'ps', 1: 'vs', 2: 'gs', 3: 'hs', 4: 'ds', 5: 'cs'}
RES_TYPE = {0: 'cbuffer', 1: 'tbuffer', 2: 'texture', 3: 'sampler', 4: 'uav_rwtyped', 5: 'structured', 6: 'uav_rwstructured',
            7: 'byteaddress', 8: 'uav_rwbyteaddress', 9: 'uav_append', 10: 'uav_consume', 11: 'uav_rwstructured_counter'}
DIM = {0: 'unknown', 1: 'buffer', 2: 'tex1d', 3: 'tex1darray', 4: 'tex2d', 5: 'tex2darray', 6: 'tex2dms', 7: 'tex2dmsarray',
       8: 'tex3d', 9: 'texcube', 10: 'texcubearray', 11: 'bufferex'}


def size_of(b, at):
    assert b[at:at + 4] == b'DXBC'
    return struct.unpack_from('<I', b, at + 24)[0]


def chunks(blob):
    n = struct.unpack_from('<I', blob, 28)[0]
    offs = struct.unpack_from('<%dI' % n, blob, 32)
    out = {}
    for o in offs:
        tag, size = struct.unpack_from('<4sI', blob, o)
        out[tag.decode('latin-1')] = blob[o + 8:o + 8 + size]
    return out


def cstr(b, o):
    e = b.index(b'\0', o)
    return b[o:e].decode('latin-1')


def program(blob):
    c = chunks(blob)
    code = c.get('SHEX') or c.get('SHDR')
    ver = struct.unpack_from('<I', code, 0)[0]
    return PROG.get(ver >> 16, '?%d' % (ver >> 16)), (ver >> 4) & 0xF, ver & 0xF


def rdef(blob):
    c = chunks(blob).get('RDEF')
    if c is None:
        return None
    ncb, cboff, nres, resoff, minor, major, prog, flags, creator = struct.unpack_from('<IIIIBBHII', c, 0)
    res = []
    for i in range(nres):
        nameoff, typ, ret, dim, nsamp, bind, count, rflags = struct.unpack_from('<8I', c, resoff + 32 * i)
        res.append(dict(name=cstr(c, nameoff), type=RES_TYPE.get(typ, typ), dim=DIM.get(dim, dim), bind=bind, count=count))
    cbs = []
    for i in range(ncb):
        nameoff, nvar, varoff, size, cflags, ctype = struct.unpack_from('<6I', c, cboff + 24 * i)
        vs = []
        stride = 40 if major >= 5 else 24
        for k in range(nvar):
            vn, start, vsize, vflags, typeoff, defoff = struct.unpack_from('<6I', c, varoff + stride * k)
            cls, vtype, rows, cols, elems, members, moff = struct.unpack_from('<HHHHHHI', c, typeoff)
            vs.append(dict(name=cstr(c, vn), offset=start, size=vsize, used=bool(vflags & 2), rows=rows, cols=cols, elements=elems,
                           cls=cls, vtype=vtype))
        cbs.append(dict(name=cstr(c, nameoff), size=size, variables=vs))
    return dict(resources=res, cbuffers=cbs, creator=cstr(c, creator) if creator else '')


def signature(blob, tag):
    c = chunks(blob).get(tag)
    if c is None:
        return []
    n = struct.unpack_from('<I', c, 0)[0]
    out = []
    for i in range(n):
        nameoff, sidx, sv, ctype, reg, mask, rw = struct.unpack_from('<IIIIIBB', c, 8 + 24 * i)
        out.append(dict(name=cstr(c, nameoff), index=sidx, sv=sv, reg=reg, mask=mask, rw=rw))
    return out
