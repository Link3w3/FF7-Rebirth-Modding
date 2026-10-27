import struct, lz4.block
def read_bundle(path):
    d = open(path, 'rb').read(); p = 0; out = []
    while p < len(d):
        index, size, usize, freq = struct.unpack_from('<IIIB', d, p); p += 13
        hsh = d[p:p+20].hex(); p += 20
        comp = d[p:p+size]; p += size
        code = lz4.block.decompress(comp, uncompressed_size=usize) if size != usize else comp
        out.append(dict(index=index, freq=freq, hash=hsh, code=code))
    return out
