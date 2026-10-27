"""The CulturePackageMap and PackageRedirects of a UE4.26 container header: after its PackageIds (int32 n, n ids) and
StoreEntries (int32 size, bytes), found the way hdr.parse_header finds them.
    culture_map.py <header .bin> [...]"""
import struct, sys


def parse(data):
    cid, n = struct.unpack_from('<QI', data, 0)
    for start in range(12, len(data) - 4, 4):
        if struct.unpack_from('<i', data, start)[0] == n and start + 4 + 8 * n + 4 <= len(data):
            o = start + 4 + 8 * n
            size = struct.unpack_from('<i', data, o)[0]
            if size >= 32 * n and o + 4 + size <= len(data):
                o += 4 + size
                break
    else:
        raise ValueError('no package id array')
    cultures = {}
    nc = struct.unpack_from('<i', data, o)[0]; o += 4
    for _ in range(nc):
        sl = struct.unpack_from('<i', data, o)[0]; o += 4
        if sl < 0:
            name = data[o:o + 2 * (-sl) - 2].decode('utf-16-le'); o += 2 * (-sl)
        else:
            name = data[o:o + sl - 1].decode('latin1'); o += sl
        np_ = struct.unpack_from('<i', data, o)[0]; o += 4
        cultures[name] = [struct.unpack_from('<QQ', data, o + 16 * k) for k in range(np_)]
        o += 16 * np_
    nr = struct.unpack_from('<i', data, o)[0]; o += 4
    redirects = [struct.unpack_from('<QQ', data, o + 16 * k) for k in range(nr)]
    o += 16 * nr
    return cid, cultures, redirects, o


if __name__ == '__main__':
    for f in sys.argv[1:]:
        data = open(f, 'rb').read()
        cid, cultures, redirects, end = parse(data)
        print(f, hex(cid), 'cultures:', {k: len(v) for k, v in cultures.items()}, 'redirects:', len(redirects), 'parsed to', end, 'of', len(data))
