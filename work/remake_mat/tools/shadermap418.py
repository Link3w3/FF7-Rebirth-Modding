"""FF7 Remake (UE 4.18) inline shader maps: every shader resource in a cooked material / material instance package.
Each resource: SpecificType (FName), Target (frequency, platform), OutputHash, NumInstructions, NumTextureSamplers,
UncompressedCodeSize, bCodeInSharedLocation, Code (zlib) = the D3D11 shader code (UE's header + DXBC).
The vertex factory of a mesh shader is the nearest vertex factory FName serialized before it (FShader::SerializeBase)."""
import struct, zlib, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkg418

FREQ = {0: 'VS', 1: 'HS', 2: 'DS', 3: 'PS', 4: 'GS', 5: 'CS'}


class Lite(pkg418.Package):
    def tagged(self, r, end):
        return []


def is_vf(name):
    return 'VertexFactory' in name


def is_shader_type(name):
    if is_vf(name) or name.startswith('FMaterialUniformExpression') or not name[:1] in ('T', 'F'):
        return False
    return any(t in name for t in ('PS', 'VS', 'GS', 'HS', 'DS', 'CS', 'Shader'))


def shaders(path):
    pk = Lite(path)
    d = pk.d
    names = pk.names
    out = []
    k = 0
    while True:
        k = d.find(b'\x78\x9c', k)
        if k < 0:
            break
        count = struct.unpack_from('<i', d, k - 4)[0]
        if count <= 0 or count > 4000000:
            k += 1
            continue
        try:
            o = zlib.decompressobj()
            code = o.decompress(d[k:k + count])
        except Exception:
            k += 1
            continue
        if not o.eof:
            k += 1
            continue
        shared, usize, nsamp, ninstr = struct.unpack_from('<iiii', d, k - 8 - 12)[::-1][0:4][::-1] if False else (None, None, None, None)
        shared = struct.unpack_from('<i', d, k - 8)[0]
        usize = struct.unpack_from('<i', d, k - 12)[0]
        nsamp = struct.unpack_from('<i', d, k - 16)[0]
        ninstr = struct.unpack_from('<i', d, k - 20)[0]
        ohash = d[k - 40:k - 20].hex()
        freq, plat = struct.unpack_from('<ii', d, k - 48)
        ti, tn = struct.unpack_from('<ii', d, k - 56)
        tname = names[ti] if 0 <= ti < len(names) else '?%d' % ti
        if len(code) != usize:
            k += 1
            continue
        # the vertex factory: the nearest preceding VF FName (within this shader's own record)
        vf = None
        p = k - 56
        lo = max(out[-1]['end'] if out else 0, k - 6000)
        q = p - 4
        while q > lo:
            i, n = struct.unpack_from('<ii', d, q)
            if 0 <= i < len(names) and n == 0 and is_vf(names[i]):
                vf = names[i]
                break
            q -= 1
        # the shader type: the nearest preceding shader type FName of this frequency (FShader::SerializeBase writes Type,
        # SourceHash, Target and the uniform buffer list right before the resource)
        fk = FREQ.get(freq, '')
        stype = None
        q = k - 60
        while q > lo:
            i, n = struct.unpack_from('<ii', d, q)
            if 0 <= i < len(names) and n == 0 and is_shader_type(names[i]) and fk in names[i]:
                stype = names[i]
                break
            q -= 1
        dx = code.find(b'DXBC')
        dxlen = struct.unpack_from('<I', code, dx + 24)[0] if dx >= 0 else 0
        out.append(dict(offset=k, end=k + count, type=stype, specific=tname, freq=FREQ.get(freq, freq), platform=plat, hash=ohash,
                        instructions=ninstr, samplers=nsamp, vf=vf, code=code, dxbc_at=dx, dxbc=code[dx:dx + dxlen] if dx >= 0 else b''))
        k += count
    return pk, out


if __name__ == '__main__':
    import collections
    pk, sh = shaders(sys.argv[1])
    print(len(sh), 'shaders')
    c = collections.Counter((s['freq'], s['type'], s['vf']) for s in sh)
    for (f, t, v), n in sorted(c.items(), key=lambda x: (str(x[0][2]), x[0][1])):
        print('%3d %-3s %-90s %s' % (n, f, t, v))
