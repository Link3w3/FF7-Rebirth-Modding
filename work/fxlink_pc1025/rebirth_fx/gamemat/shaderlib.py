"""The game's shader library (FSerializedShaderArchive, GShaderCodeArchiveVersion 2) read from its .ushaderbytecode in
pakchunk0: shader map hashes -> the shaders of each map (their code entries), and each shader's code."""
import struct

FREQ = {0: 'VS', 1: 'MS', 2: 'AS', 3: 'HS', 4: 'DS', 5: 'PS', 6: 'GS', 7: 'CS', 8: 'RayGen', 9: 'RayMiss',
        10: 'RayHitGroup', 11: 'RayCallable'}


def parse_header(h, prefixed=False):
    """(version, code offset in the file, arrays) from the library's header bytes. prefixed: the header as an older tool
    saved it (u32 version, u64 code offset, then the arrays)."""
    if prefixed:
        version, code_offset = struct.unpack_from('<IQ', h, 0)
        p = 12
    else:
        version = struct.unpack_from('<I', h, 0)[0]
        code_offset = None
        p = 4
    arrays = []
    for size in (20, 20, 16, 17, 16, 4):
        n = struct.unpack_from('<i', h, p)[0]
        p += 4
        if n < 0 or p + n * size > len(h):
            raise ValueError('the shader library header does not fit (array of %d x %d at %d)' % (n, size, p))
        arrays.append((n, h[p:p + n * size]))
        p += n * size
    if code_offset is None:
        code_offset = p
    return version, code_offset, arrays


class Library(object):
    def __init__(self, header, prefixed=False, read_code=None, name='End'):
        """header: the library's header bytes (from the start of the file, at least the whole header);
        read_code(offset in the file, size) -> bytes, for the shaders' code."""
        self.name = name
        self.version, self.code_offset, arrays = parse_header(header, prefixed)
        (n, b) = arrays[0]
        self.map_hashes = [b[i * 20:(i + 1) * 20] for i in range(n)]
        (n, b) = arrays[1]
        self.shader_hashes = [b[i * 20:(i + 1) * 20] for i in range(n)]
        (n, b) = arrays[2]
        self.map_entries = [struct.unpack_from('<4I', b, i * 16) for i in range(n)]
        (n, b) = arrays[3]
        self.shader_entries = [struct.unpack_from('<QIIB', b, i * 17) for i in range(n)]
        (n, b) = arrays[4]
        self.preloads = [struct.unpack_from('<qq', b, i * 16) for i in range(n)]
        (n, b) = arrays[5]
        self.indices = list(struct.unpack_from('<%dI' % n, b, 0))
        self.map_index = {hsh: i for i, hsh in enumerate(self.map_hashes)}
        self._read = read_code

    def order(self, map_hash):
        """The library shader indices of a shader map, in the map's resource order."""
        i = self.map_index[map_hash]
        off, num, _, _ = self.map_entries[i]
        return [self.indices[off + k] for k in range(num)]

    def shader(self, si):
        """dict(index, hash, code (as stored, maybe compressed), usize, freq) of library shader si."""
        o, size, usize, freq = self.shader_entries[si]
        code = self._read(self.code_offset + o, size)
        if len(code) != size:
            raise IOError('shader %d: read %d of %d bytes' % (si, len(code), size))
        return dict(index=si, hash=self.shader_hashes[si], code=code, usize=usize, freq=freq)


def library_from_pak(pak, path_suffix='ShaderArchive-End-PCD3D_SM6.ushaderbytecode', header_cache=None):
    """The library inside a Pak (pak.Pak). header_cache: a file path to keep the header in (it is ~4 MB to read)."""
    paths = pak.find(path_suffix)
    if len(paths) != 1:
        raise KeyError('%s: %d files end with %s' % (pak.path, len(paths), path_suffix))
    e = pak.entry(paths[0])
    start = pak.data_start(e)
    header = None
    if header_cache:
        try:
            with open(header_cache, 'rb') as f:
                cached = f.read()
            if cached[:12] == struct.pack('<Iq', e.offset & 0xFFFFFFFF, e.usize)[:12]:
                header = cached[12:]
        except (IOError, OSError):
            header = None
    if header is None:
        with open(pak.path, 'rb') as f:
            f.seek(start)
            head = f.read(64 << 20 if e.usize > (64 << 20) else e.usize)
        version, code_offset, arrays = parse_header(head)
        header = head[:code_offset]
        if header_cache:
            try:
                with open(header_cache, 'wb') as f:
                    f.write(struct.pack('<Iq', e.offset & 0xFFFFFFFF, e.usize) + header)
            except (IOError, OSError):
                pass

    def read_code(offset, size):
        with open(pak.path, 'rb') as f:
            f.seek(start + offset)
            return f.read(size)
    return Library(header, read_code=read_code, name=path_suffix.split('-')[1])
