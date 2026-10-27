"""Render sections of each LOD of a cooked FF7 Rebirth skeletal mesh export (UE 4.26 as Square Enix cooks it): an int32
count, then per section: strip flags (2), MaterialIndex u16, BaseIndex u32, NumTriangles u32, bRecomputeTangent u32,
mask channel u8, bCastShadow u32, BaseVertexIndex u32, ClothMappingData count u32 (0), u32, BoneMap (count + u16s),
NumVertices u32, MaxBoneInfluences u32, ..."""
import struct


def parse_sections(x, o):
    n = struct.unpack_from('<i', x, o)[0]
    p = o + 4
    out = []
    for k in range(n):
        st = p
        strip, mat, base, ntri, rec = struct.unpack_from('<HHIII', x, p); p += 14
        mask = x[p]; p += 1
        shadow, bvi, ncloth, extra, nb = struct.unpack_from('<IIIII', x, p); p += 20
        if ncloth != 0 or nb > 1000:
            return None
        bonemap = list(struct.unpack_from('<%dH' % nb, x, p)); p += 2 * nb
        nv, maxinf, clothidx = struct.unpack_from('<IIh', x, p); p += 10
        p += 16 + 4           # clothing data guid + lod index
        out.append(dict(at=st, mat=mat, base=base, ntri=ntri, shadow=shadow, base_vertex=bvi, bonemap=bonemap, nverts=nv,
                        maxinf=maxinf))
        # the rest (duplicated vertices, flags) up to the next section's strip flags: found by scanning
        if k + 1 < n:
            q = p
            nb_ = base + 3 * ntri
            found = None
            for q in range(p, p + 4000):
                s2, m2, b2 = struct.unpack_from('<HHI', x, q)
                if m2 == mat + 1 or (m2 > mat and m2 < 64):
                    if b2 == nb_:
                        found = q
                        break
            if found is None:
                return None
            out[-1]['tail'] = x[p:found].hex(' ')
            p = found
    return out


def find_lods(x):
    """[(offset of the count, sections)] for every section list found."""
    res = []
    for o in range(0, len(x) - 24):
        n = struct.unpack_from('<i', x, o)[0]
        if not (1 <= n <= 64):
            continue
        strip, mat, base = struct.unpack_from('<HHI', x, o + 4)
        if mat != 0 or base != 0:
            continue
        try:
            s = parse_sections(x, o)
        except struct.error:
            continue
        if s and len(s) == n and s[0]['nverts'] > 0:
            res.append((o, s))
    return res
