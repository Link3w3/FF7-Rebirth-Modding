import struct, numpy as np
def read(path):
    d = open(path, 'rb').read()
    assert d[:8] == b'CACANIM1'
    ver, fps, frames, flags, ntr = struct.unpack_from('<IfiIi', d, 8)
    p = 28
    tracks = {}
    for _ in range(ntr):
        n = struct.unpack_from('<H', d, p)[0]; p += 2
        name = d[p:p+n].decode(); p += n
        k = struct.unpack_from('<i', d, p)[0]; p += 4
        v = np.frombuffer(d, '<f4', k * 10, p).reshape(k, 10).astype(np.float64); p += k * 40
        if k == 1: v = np.repeat(v, frames, 0)
        tracks[name] = v
    return fps, frames, flags, tracks
