"""UE 4.18 D3D11 shader code: the header in front of the DXBC (FD3D11ShaderResourceTable: resource table bits, SRV /
sampler / UAV maps, layout hashes, texture map) and the optional data after it ('u': the uniform buffer names by slot).
binding(code) -> {'cb': [names by cbuffer slot], 't': {slot: (buffer, resource index)}, 's': {slot: (buffer, resource index)}}
Each map entry packs (uniform buffer << 24) | (resource index << 8) | bind index; 0xffffffff ends a buffer's list."""
import struct


def _arr(d, p):
    n = struct.unpack_from('<i', d, p)[0]
    vals = list(struct.unpack_from('<%dI' % n, d, p + 4))
    return vals, p + 4 + 4 * n


def _entries(vals):
    out = {}
    for v in vals:
        if v == 0xffffffff or v == 0:
            continue
        ub, res, bind = v >> 24, (v >> 8) & 0xffff, v & 0xff
        if ub < 16:
            out[bind] = (ub, res)
    return out


def binding(code):
    dx = code.find(b'DXBC')
    p = 0
    bits = struct.unpack_from('<I', code, p)[0]; p += 4
    srv, p = _arr(code, p)
    samp, p = _arr(code, p)
    uav, p = _arr(code, p)
    hashes, p = _arr(code, p)
    tex, p = _arr(code, p)
    # the uniform buffer names: optional data 'u' after the DXBC
    n = struct.unpack_from('<I', code, dx + 24)[0]
    tail = code[dx + n:]
    names = []
    k = tail.find(b'u')
    while k >= 0:
        try:
            size = struct.unpack_from('<i', tail, k + 1)[0]
            blob = tail[k + 5:k + 5 + size]
            cnt = struct.unpack_from('<i', blob, 0)[0]
            q = 4
            got = []
            for _ in range(cnt):
                ln = struct.unpack_from('<i', blob, q)[0]; q += 4
                got.append(blob[q:q + ln - 1].decode('latin-1')); q += ln
            if 0 < cnt < 32 and q == len(blob):
                names = got
                break
        except Exception:
            pass
        k = tail.find(b'u', k + 1)
    return {'bits': bits, 'cb': names, 't': _entries(tex), 's': _entries(samp), 'srv': _entries(srv), 'hashes': hashes}


if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import shadermap418
    pk, sh = shadermap418.shaders(sys.argv[1])
    for s in sh:
        if s['type'] == 'TBasePassPSFNoLightMapPolicyNoSkylightNoPerObjectCoverage' and s['vf'] == 'FLocalVertexFactory':
            b = binding(s['code'])
            print('cbuffers:', b['cb'])
            print('textures:', {k: (b['cb'][u] if u < len(b['cb']) else u, r) for k, (u, r) in sorted(b['t'].items())})
            print('samplers:', {k: (b['cb'][u] if u < len(b['cb']) else u, r) for k, (u, r) in sorted(b['s'].items())})
            break
