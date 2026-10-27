"""Crisis Core Reunion's shader library (UE 4.27 FSerializedShaderArchive, ShaderArchive-CCFF7R_Chunk0-PCD3D_SM5): its
shader maps (by hash), their shaders, and each shader's code (LZ4 when compressed; the D3D11 shader code: the engine's
prefix, then the DXBC container).
    shaderlib.py info <archive>
    shaderlib.py find <archive> <package> [...]     the shader maps whose hash a package holds
    shaderlib.py dump <archive> <map hash> <out dir>  every shader of a map: .dxbc (the container) and .bin (the whole code)"""
import os
import struct
import sys

import lz4.block


class Archive:
    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        b = self.f.read(64 << 20)
        p = 0
        self.version = struct.unpack_from('<I', b, p)[0]; p += 4

        def arr(n_bytes):
            nonlocal p
            n = struct.unpack_from('<i', b, p)[0]; p += 4
            out = b[p:p + n * n_bytes]; p += n * n_bytes
            return n, out
        n, raw = arr(20)
        self.map_hashes = [raw[i * 20:(i + 1) * 20] for i in range(n)]
        n, raw = arr(20)
        self.shader_hashes = [raw[i * 20:(i + 1) * 20] for i in range(n)]
        n = struct.unpack_from('<i', b, p)[0]; p += 4
        self.maps = [struct.unpack_from('<IIII', b, p + 16 * i) for i in range(n)]   # indices offset, count, preload first, count
        p += 16 * n
        n = struct.unpack_from('<i', b, p)[0]; p += 4
        self.shaders = []
        for i in range(n):
            off, size, usize, freq = struct.unpack_from('<QIIB', b, p); p += 17
            self.shaders.append((off, size, usize, freq))
        n = struct.unpack_from('<i', b, p)[0]; p += 4
        self.preload = [struct.unpack_from('<qq', b, p + 16 * i) for i in range(n)]
        p += 16 * n
        n = struct.unpack_from('<i', b, p)[0]; p += 4
        self.indices = list(struct.unpack_from('<%dI' % n, b, p)); p += 4 * n
        self.code_start = p
        self.map_index = {h: i for i, h in enumerate(self.map_hashes)}

    def map_shaders(self, m):
        off, count, _, _ = self.maps[m]
        return self.indices[off:off + count]

    def code(self, s):
        off, size, usize, freq = self.shaders[s]
        self.f.seek(self.code_start + off)
        raw = self.f.read(size)
        if size != usize:
            raw = lz4.block.decompress(raw, uncompressed_size=usize)
        return raw, freq

    @staticmethod
    def dxbc(code):
        at = code.find(b'DXBC')
        if at < 0:
            return None, -1
        size = struct.unpack_from('<I', code, at + 24)[0]
        return code[at:at + size], at


FREQ = {0: 'vs', 1: 'hs', 2: 'ds', 3: 'ps', 4: 'gs', 5: 'cs'}


def main():
    cmd, path = sys.argv[1], sys.argv[2]
    a = Archive(path)
    if cmd == 'info':
        print('version %d, %d maps, %d shaders, %d indices, code at %d' % (a.version, len(a.maps), len(a.shaders), len(a.indices), a.code_start))
    elif cmd == 'find':
        for pkg in sys.argv[3:]:
            d = open(pkg, 'rb').read()
            hits = [(i, d.find(h)) for i, h in enumerate(a.map_hashes) if h in d]
            print(pkg, [(i, a.map_hashes[i].hex(), at, len(a.map_shaders(i))) for i, at in hits])
    elif cmd == 'dump':
        m = a.map_index[bytes.fromhex(sys.argv[3])]
        out = sys.argv[4]
        os.makedirs(out, exist_ok=True)
        for k, s in enumerate(a.map_shaders(m)):
            code, freq = a.code(s)
            dx, at = a.dxbc(code)
            base = os.path.join(out, '%03d_%s_%05d' % (k, FREQ.get(freq, 'f%d' % freq), s))
            open(base + '.bin', 'wb').write(code)
            if dx is not None:
                open(base + '.dxbc', 'wb').write(dx)
        print('map %d: %d shaders written to %s' % (m, len(a.map_shaders(m)), out))


if __name__ == '__main__':
    main()
