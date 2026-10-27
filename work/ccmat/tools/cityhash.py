"""CityHash64 (v1.1, as Unreal's Core/Private/Hash/CityHash.cpp) and Unreal's FHashedName (4.26/4.27: CityHash64WithSeed
of the upper-cased ANSI name, seeded with the FName's number)."""
import struct

M64 = (1 << 64) - 1
k0 = 0xc3a5c85c97cb3127
k1 = 0xb492b66fbe98f273
k2 = 0x9ae16a3b2f90404f
kMul = 0x9ddfea08eb382d69


def _f64(s, i):
    return struct.unpack_from('<Q', s, i)[0]


def _f32(s, i):
    return struct.unpack_from('<I', s, i)[0]


def _rot(v, sh):
    return v if sh == 0 else ((v >> sh) | (v << (64 - sh))) & M64


def _smix(v):
    return v ^ (v >> 47)


def _bswap(v):
    return int.from_bytes(v.to_bytes(8, 'little'), 'big')


def _h16(u, v, mul=kMul):
    a = ((u ^ v) * mul) & M64
    a ^= a >> 47
    b = ((v ^ a) * mul) & M64
    b ^= b >> 47
    return (b * mul) & M64


def _len0to16(s, n):
    if n >= 8:
        mul = (k2 + n * 2) & M64
        a = (_f64(s, 0) + k2) & M64
        b = _f64(s, n - 8)
        c = (_rot(b, 37) * mul + a) & M64
        d = ((_rot(a, 25) + b) * mul) & M64
        return _h16(c, d, mul)
    if n >= 4:
        mul = (k2 + n * 2) & M64
        a = _f32(s, 0)
        return _h16((n + (a << 3)) & M64, _f32(s, n - 4), mul)
    if n > 0:
        a, b, c = s[0], s[n >> 1], s[n - 1]
        y = (a + (b << 8)) & 0xffffffff
        z = (n + (c << 2)) & 0xffffffff
        return (_smix(((y * k2) ^ (z * k0)) & M64) * k2) & M64
    return k2


def _len17to32(s, n):
    mul = (k2 + n * 2) & M64
    a = (_f64(s, 0) * k1) & M64
    b = _f64(s, 8)
    c = (_f64(s, n - 8) * mul) & M64
    d = (_f64(s, n - 16) * k2) & M64
    return _h16((_rot((a + b) & M64, 43) + _rot(c, 30) + d) & M64, (a + _rot((b + k2) & M64, 18) + c) & M64, mul)


def _len33to64(s, n):
    mul = (k2 + n * 2) & M64
    a = (_f64(s, 0) * k2) & M64
    b = _f64(s, 8)
    c = _f64(s, n - 24)
    d = _f64(s, n - 32)
    e = (_f64(s, 16) * k2) & M64
    f = (_f64(s, 24) * 9) & M64
    g = _f64(s, n - 8)
    h = (_f64(s, n - 16) * mul) & M64
    u = (_rot((a + g) & M64, 43) + ((_rot(b, 30) + c) & M64) * 9) & M64
    v = ((((a + g) & M64) ^ d) + f + 1) & M64
    w = (_bswap(((u + v) * mul) & M64) + h) & M64
    x = (_rot((e + f) & M64, 42) + c) & M64
    y = ((_bswap(((v + w) * mul) & M64) + g) * mul) & M64
    z = (e + f + c) & M64
    a = (_bswap(((x + z) * mul + y) & M64) + b) & M64
    b = (_smix(((z + a) * mul + d + h) & M64) * mul) & M64
    return (b + x) & M64


def _weak32(w, x, y, z, a, b):
    a = (a + w) & M64
    b = _rot((b + a + z) & M64, 21)
    c = a
    a = (a + x) & M64
    a = (a + y) & M64
    b = (b + _rot(a, 44)) & M64
    return (a + z) & M64, (b + c) & M64


def _weak32s(s, i, a, b):
    return _weak32(_f64(s, i), _f64(s, i + 8), _f64(s, i + 16), _f64(s, i + 24), a, b)


def cityhash64(s):
    n = len(s)
    if n <= 32:
        return _len0to16(s, n) if n <= 16 else _len17to32(s, n)
    if n <= 64:
        return _len33to64(s, n)
    x = _f64(s, n - 40)
    y = (_f64(s, n - 16) + _f64(s, n - 56)) & M64
    z = _h16((_f64(s, n - 48) + n) & M64, _f64(s, n - 24))
    v = _weak32s(s, n - 64, n, z)
    w = _weak32s(s, n - 32, (y + k1) & M64, x)
    x = (x * k1 + _f64(s, 0)) & M64
    left = (n - 1) & ~63
    p = 0
    while True:
        x = (_rot((x + y + v[0] + _f64(s, p + 8)) & M64, 37) * k1) & M64
        y = (_rot((y + v[1] + _f64(s, p + 48)) & M64, 42) * k1) & M64
        x ^= w[1]
        y = (y + v[0] + _f64(s, p + 40)) & M64
        z = (_rot((z + w[0]) & M64, 33) * k1) & M64
        v = _weak32s(s, p, (v[1] * k1) & M64, (x + w[0]) & M64)
        w = _weak32s(s, p + 32, (z + w[1]) & M64, (y + _f64(s, p + 16)) & M64)
        z, x = x, z
        p += 64
        left -= 64
        if left == 0:
            break
    return _h16((_h16(v[0], w[0]) + _smix(y) * k1 + z) & M64, (_h16(v[1], w[1]) + x) & M64)


def cityhash64_with_seed(s, seed):
    return _h16((cityhash64(s) - k2) & M64, seed & M64)


def hashed_name(name, number=0):
    """Unreal's FHashedName (4.26): 0 for None"""
    if name == '' or name.lower() == 'none':
        return 0
    return cityhash64_with_seed(name.upper().encode('ascii'), number)
