"""Sockets of a cooked (Zen) USkeleton or USkeletalMesh package, tagged (versioned) properties: each SkeletalMeshSocket
export's SocketName, BoneName, RelativeLocation, RelativeRotation, RelativeScale.
    sockets.py <package.uasset>   |   import: sockets(data) -> [(socket, bone, loc, rot, scale)]"""
import struct, sys
sys.path.insert(0, '/work/cs')
from zen import Zen


def fname(z, d, p):
    ni, num = struct.unpack_from('<II', d, p)
    s = z.names[ni] if ni < len(z.names) else '?%d' % ni
    return (s if num == 0 else '%s_%d' % (s, num - 1)), p + 8


def tagged(z, d, p, end):
    out = {}
    while p < end:
        name, p = fname(z, d, p)
        if name == 'None':
            break
        typ, p = fname(z, d, p)
        size, idx = struct.unpack_from('<ii', d, p)
        p += 8
        extra = None
        if typ == 'StructProperty':
            extra, p = fname(z, d, p)
            p += 16  # struct guid
        elif typ in ('BoolProperty',):
            extra = d[p]
            p += 1
        elif typ in ('ByteProperty', 'EnumProperty'):
            extra, p = fname(z, d, p)
        elif typ in ('ArrayProperty', 'SetProperty'):
            extra, p = fname(z, d, p)
        elif typ == 'MapProperty':
            extra, p = fname(z, d, p)
            _, p = fname(z, d, p)
        hasguid = d[p]
        p += 1
        if hasguid:
            p += 16
        val = d[p:p + size]
        if typ == 'NameProperty':
            val = fname(z, d, p)[0]
        elif typ == 'StructProperty' and extra in ('Vector', 'Rotator'):
            val = struct.unpack_from('<3f', d, p)
        elif typ == 'BoolProperty':
            val = bool(extra)
        out[name] = val
        p += size
    return out


def sockets(d):
    z = Zen(d)
    pos = z.bundle_positions()
    out = []
    for k, e in enumerate(z.exports):
        if not e['name'].startswith('SkeletalMeshSocket'):
            continue
        p, size = pos[k]
        v = tagged(z, d, p, p + size)
        out.append((v.get('SocketName'), v.get('BoneName'), v.get('RelativeLocation'), v.get('RelativeRotation'), v.get('RelativeScale')))
    return out


if __name__ == '__main__':
    for s in sockets(open(sys.argv[1], 'rb').read()):
        print(s)
