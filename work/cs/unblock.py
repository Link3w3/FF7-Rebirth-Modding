import struct, ctypes, sys, os
lib = ctypes.CDLL('/work/ooz/build/liblibooz.so')
lib.Ooz_Decompress.restype = ctypes.c_int
lib.Ooz_Decompress.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_size_t,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
def oodle(data, us):
    buf = ctypes.create_string_buffer(us + 64)
    r = lib.Ooz_Decompress(data, len(data), buf, us, 0,0,0,None,0,None,None,None,0,0)
    assert r == us, (r, us)
    return buf.raw[:us]
def read_blocks(path):
    d = open(path, 'rb').read(); p = 0; res = {}
    while p < len(d):
        (kl,) = struct.unpack_from('<I', d, p); p += 4
        key = d[p:p+kl].decode(); p += kl
        start, length, nb = struct.unpack_from('<QQI', d, p); p += 20
        out = bytearray()
        for _ in range(nb):
            m, us, cs = struct.unpack_from('<BII', d, p); p += 9
            data = d[p:p+cs]; p += cs
            out += data[:us] if m == 0 else oodle(data, us)
        res[key] = bytes(out[start:start+length])
    return res
if __name__ == '__main__':
    res = read_blocks(sys.argv[1])
    os.makedirs(sys.argv[2], exist_ok=True)
    for k, v in res.items():
        tag, p = k.split(':', 1)
        fn = os.path.join(sys.argv[2], tag + '_' + os.path.basename(p))
        open(fn, 'wb').write(v)
        print(fn, len(v))
