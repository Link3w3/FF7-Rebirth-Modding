"""Koei Tecmo G1T texture containers (Dissidia Final Fantasy NT, GT1G0600, Windows): every texture's top mip as PNG.

Layout (Project G1M's G1T.h): header {magic 'GT1G', version, size, table offset, count, platform, ASTC info size};
offsets (from the table offset) per texture; each texture {mip/sub nibbles, format, log2 height/width nibbles, 4 bytes,
extra header version}, an extra header (u32 size, ...; width/height when it is >= 0x10/0x14) when the version > 0,
then the data, top mip first. Formats here: 0x59 DXT1, 0x5B DXT5 (also 0x5C BC4, 0x5D BC5, 0x5F BC7, 0x00 RGBA8,
0x01 BGRA8).
    g1t.py list <file.g1t>
    g1t.py png <file.g1t> <out dir> [prefix]      writes <prefix><index>.png (RGBA, top mip)"""
import os
import struct
import sys

import numpy as np
import texture2ddecoder as t2d
from PIL import Image

FORMATS = {0x00: ('rgba8', 32), 0x01: ('bgra8', 32), 0x06: ('bc1', 4), 0x07: ('bc2', 8), 0x08: ('bc3', 8),
           0x59: ('bc1', 4), 0x5B: ('bc3', 8), 0x5C: ('bc4', 4), 0x5D: ('bc5', 8), 0x5F: ('bc7', 8), 0x5E: ('bc6', 8)}


def entries(b):
    magic, ver, size, table, count, platform, astc = struct.unpack_from('<4s4sIIIII', b, 0)
    assert magic == b'GT1G', magic
    offs = struct.unpack_from('<%dI' % count, b, table)
    out = []
    for i, o in enumerate(offs):
        p = table + o
        mipsys, fmt, dxdy, u1, u2, u3, u4, extra = struct.unpack_from('<8B', b, p)
        w, h = 1 << (dxdy & 15), 1 << (dxdy >> 4)
        hdr = 8
        if extra:
            es = struct.unpack_from('<I', b, p + 8)[0]
            hdr += es
            if es >= 0x10:
                w = struct.unpack_from('<I', b, p + 20)[0]
            if es >= 0x14:
                h = struct.unpack_from('<I', b, p + 24)[0]
        end = (table + offs[i + 1]) if i + 1 < count else len(b)
        out.append(dict(index=i, format=fmt, width=w, height=h, mips=mipsys >> 4, data=p + hdr, end=end))
    return out


def decode(b, e):
    name, bpp = FORMATS[e['format']]
    w, h = e['width'], e['height']
    if name in ('rgba8', 'bgra8'):
        a = np.frombuffer(b, np.uint8, w * h * 4, e['data']).reshape(h, w, 4)
        if name == 'bgra8':
            a = a[:, :, [2, 1, 0, 3]]
        return Image.fromarray(a.copy(), 'RGBA')
    bw, bh = max(1, (w + 3) // 4), max(1, (h + 3) // 4)
    n = bw * bh * (8 if bpp == 4 else 16)
    raw = b[e['data']:e['data'] + n]
    fn = {'bc1': t2d.decode_bc1, 'bc2': getattr(t2d, 'decode_bc2', None), 'bc3': t2d.decode_bc3, 'bc4': t2d.decode_bc4,
          'bc5': t2d.decode_bc5, 'bc7': t2d.decode_bc7, 'bc6': t2d.decode_bc6}[name]
    out = fn(raw, w, h)                      # BGRA bytes
    a = np.frombuffer(out, np.uint8).reshape(h, w, 4)[:, :, [2, 1, 0, 3]]
    return Image.fromarray(a.copy(), 'RGBA')


def main():
    cmd, path = sys.argv[1:3]
    b = open(path, 'rb').read()
    es = entries(b)
    if cmd == 'list':
        for e in es:
            print('%2d fmt %#04x %s %dx%d mips %d' % (e['index'], e['format'], FORMATS.get(e['format'], ('?',))[0],
                                                      e['width'], e['height'], e['mips']))
        return
    out = sys.argv[3]
    prefix = sys.argv[4] if len(sys.argv) > 4 else ''
    os.makedirs(out, exist_ok=True)
    for e in es:
        img = decode(b, e)
        img.save(os.path.join(out, '%s%02d.png' % (prefix, e['index'])))
    print(len(es), 'textures')


if __name__ == '__main__':
    main()
