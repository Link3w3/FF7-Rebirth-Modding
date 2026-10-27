"""The game's shader library headers (FSerializedShaderArchive v2) as saved by the device-side reader."""
import struct
FREQ = {0: 'VS', 1: 'MS', 2: 'AS', 3: 'HS', 4: 'DS', 5: 'PS', 6: 'GS', 7: 'CS', 8: 'RayGen', 9: 'RayMiss', 10: 'RayHitGroup', 11: 'RayCallable'}
PAK_ENTRY = {'End': 2525184, 'Global': 534503424}

class Library:
    def __init__(self, path, name):
        h = open(path, 'rb').read()
        self.name = name
        self.version, self.code_offset = struct.unpack_from('<IQ', h, 0)
        p = 12
        def arr(sz):
            nonlocal p
            n, = struct.unpack_from('<i', h, p); p += 4
            b = h[p:p + n * sz]; p += n * sz
            return n, b
        n, b = arr(20); self.map_hashes = [b[i*20:(i+1)*20] for i in range(n)]
        n, b = arr(20); self.shader_hashes = [b[i*20:(i+1)*20] for i in range(n)]
        n, b = arr(16); self.map_entries = [struct.unpack_from('<4I', b, i*16) for i in range(n)]
        n, b = arr(17); self.shader_entries = [struct.unpack_from('<QIIB', b, i*17) for i in range(n)]
        n, b = arr(16); self.preloads = [struct.unpack_from('<qq', b, i*16) for i in range(n)]
        n, b = arr(4); self.indices = list(struct.unpack_from('<%dI' % n, b, 0))
        self.map_index = {hsh: i for i, hsh in enumerate(self.map_hashes)}

    def shaders_of(self, map_hash):
        i = self.map_index[map_hash]
        off, num, first_pre, num_pre = self.map_entries[i]
        out = []
        for k in range(num):
            si = self.indices[off + k]
            o, size, usize, freq = self.shader_entries[si]
            out.append(dict(index=si, offset=o, size=size, usize=usize, freq=freq, kind=FREQ.get(freq, freq), hash=self.shader_hashes[si].hex()))
        return out

    def file_offset(self, shader):
        """Absolute offset of a shader's (compressed) code in pakchunk0."""
        return PAK_ENTRY[self.name] + 53 + self.code_offset + shader['offset']
