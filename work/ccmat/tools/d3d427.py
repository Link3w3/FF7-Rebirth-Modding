"""UE 4.26/4.27 D3D11 shader code: the resource table in front of the DXBC (resource table bits; SRV, sampler and UAV
token streams; per-uniform-buffer layout hashes; texture token stream) and the optional data after it ('u': the
uniform buffer names by constant buffer slot).

A token stream starts with one offset per bound uniform buffer (as many as the layout hashes), then entries
(uniform buffer << 24 | resource index << 8 | bind index), then 0xffffffff.
    binding(code) -> {'cb': [names by slot], 't': {slot: (buffer name, resource index)}, 's': {...}, 'srv': {...}}"""
import struct


def _arr(d, p):
    n = struct.unpack_from('<i', d, p)[0]
    return list(struct.unpack_from('<%dI' % n, d, p + 4)), p + 4 + 4 * n


def _stream(vals, nbuf):
    out = {}
    for v in vals[nbuf:]:
        if v == 0xffffffff:
            continue
        out[v & 0xff] = (v >> 24, (v >> 8) & 0xffff)
    return out


def uniform_buffer_names(code):
    dx = code.find(b'DXBC')
    n = struct.unpack_from('<I', code, dx + 24)[0]
    tail = code[dx + n:]
    # optional data: (key byte, u32 size, data)..., then the u32 total size
    total = struct.unpack_from('<I', tail, len(tail) - 4)[0] if len(tail) >= 4 else 0
    p = 0
    end = len(tail) - 4
    while p + 5 <= end:
        key = tail[p]
        size = struct.unpack_from('<I', tail, p + 1)[0]
        blob = tail[p + 5:p + 5 + size]
        if key == ord('u'):
            cnt = struct.unpack_from('<i', blob, 0)[0]
            q = 4
            names = []
            for _ in range(cnt):
                ln = struct.unpack_from('<i', blob, q)[0]
                q += 4
                names.append(blob[q:q + ln - 1].decode('latin-1') if ln > 0 else '')
                q += max(ln, 0)
            return names
        p += 5 + size
    return []


def binding(code):
    p = 0
    bits = struct.unpack_from('<I', code, p)[0]
    p += 4
    srv, p = _arr(code, p)
    samp, p = _arr(code, p)
    uav, p = _arr(code, p)
    hashes, p = _arr(code, p)
    tex, p = _arr(code, p)
    nb = len(hashes)
    names = uniform_buffer_names(code)

    def nm(e):
        return {k: (names[u] if u < len(names) else 'ub%d' % u, r) for k, (u, r) in e.items()}
    return {'bits': bits, 'cb': names, 'layout_hashes': hashes, 't': nm(_stream(tex, nb)), 's': nm(_stream(samp, nb)),
            'srv': nm(_stream(srv, nb)), 'uav': nm(_stream(uav, nb))}
