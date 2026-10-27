"""KH3 cooked textures (.uasset + .uexp [+ .ubulk]) -> PNG (the largest mip), through a DDS the image library decodes.

    python3 kh3tex.py <tex folder> <out folder>
"""
import glob
import io
import os
import struct
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, '/work/kh3bnm/src/rebirth_fx']
import kh3bonamik as k   # noqa: E402
import tagged            # noqa: E402

DXGI = {'PF_BC4': 80, 'PF_BC5': 83, 'PF_BC7': 98, 'PF_DXT1': 71, 'PF_DXT3': 74, 'PF_DXT5': 77, 'PF_B8G8R8A8': 87,
        'PF_BC6H': 95}
SETTING_DEFAULTS = dict(SRGB=True, CompressionSettings='TC_Default', LODGroup='TEXTUREGROUP_World', AddressX='TA_Wrap',
                        AddressY='TA_Wrap', Filter='TF_Default')
BLOCK = {'PF_BC4': 8, 'PF_BC5': 16, 'PF_BC7': 16, 'PF_DXT1': 8, 'PF_DXT3': 16, 'PF_DXT5': 16}


def read_texture(uasset, uexp, ubulk=b''):
    pk = k.Package(uasset, uexp)
    e = [x for x in pk.exports if pk.class_name(x) == 'Texture2D'][0]
    props = tagged.parse(pk.data, e['offset'], e['offset'] + e['size'], pk.names)
    d = pk.data
    p = props.end
    p += 4                                   # UObject guid flag
    p += 4                                   # strip flags (texture, texture2d)
    cooked = struct.unpack_from('<i', d, p)[0]
    p += 4
    if not cooked:
        raise ValueError('not cooked')
    fmt_name = pk.names[struct.unpack_from('<i', d, p)[0]]
    p += 8
    skip = struct.unpack_from('<i', d, p)[0]
    p += 4
    sx, sy, slices = struct.unpack_from('<iii', d, p)
    p += 12
    r = tagged  # noqa
    n = struct.unpack_from('<i', d, p)[0]
    pf = d[p + 4:p + 4 + n - 1].decode()
    p += 4 + n
    first_mip, nmips = struct.unpack_from('<ii', d, p)
    p += 8
    mips = []
    ubulk_base = None
    for _ in range(nmips):
        mcooked = struct.unpack_from('<i', d, p)[0]
        p += 4
        flags, count, size, off = struct.unpack_from('<IiiQ', d, p)
        p += 20
        off = struct.unpack_from('<q', d, p - 8)[0]
        if flags & 0x100:                    # in the .ubulk
            if ubulk_base is None:
                ubulk_base = -off
            data = ubulk[off + ubulk_base:off + ubulk_base + size]
        elif flags & 0x40 or not flags & 0x1:  # inline
            data = d[p:p + size]
            p += size
        else:                                # at the end of the .uexp
            data = d[off:off + size]
        mx, my = struct.unpack_from('<ii', d, p)
        p += 8
        mips.append(dict(w=mx, h=my, data=data, flags=flags))
    return dict(name=e['name'], format=pf, w=sx, h=sy, mips=mips, srgb=bool(tagged.find(props, 'SRGB') is None or
                                                                            pk.data[tagged.find(props, 'SRGB').value_start - 2]))


def settings(uasset, uexp):
    """The texture's import settings as KH3 kept them (defaults filled in)."""
    pk = k.Package(uasset, uexp)
    e = [x for x in pk.exports if pk.class_name(x) == 'Texture2D'][0]
    props = tagged.parse(pk.data, e['offset'], e['offset'] + e['size'], pk.names)
    out = dict(SETTING_DEFAULTS)
    for p in props:
        if p.name in out:
            if p.type == 'BoolProperty':
                out[p.name] = bool(p.bool)
            elif p.type in ('ByteProperty', 'EnumProperty') and p.size == 8:
                out[p.name] = tagged._name(pk.data, p.value_start, pk.names)
    return out


def import_image(t, comp):
    """An RGBA image to import: single-channel formats go into every channel (TC_Alpha builds from alpha); two-channel
    normal maps get their blue back."""
    img = to_image(t)
    if img.mode == 'L':
        img = Image.merge('RGBA', (img, img, img, img))
    elif t['format'] == 'PF_BC5':
        import math
        r, g = img.convert('RGB').split()[:2]
        rb, gb = r.tobytes(), g.tobytes()
        bb = bytes(int(255 * (0.5 + 0.5 * math.sqrt(max(0.0, 1 - ((x / 127.5 - 1) ** 2) - ((y / 127.5 - 1) ** 2)))))
                   for x, y in zip(rb, gb))
        img = Image.merge('RGBA', (r, g, Image.frombytes('L', r.size, bb), Image.new('L', r.size, 255)))
    elif img.mode != 'RGBA':
        img = img.convert('RGBA')
    return img


def to_image(t):
    m = t['mips'][0]
    if t['format'] == 'PF_B8G8R8A8':
        img = Image.frombytes('RGBA', (m['w'], m['h']), m['data'], 'raw', 'BGRA')
        return img
    if t['format'] in ('PF_G8', 'PF_A8'):
        return Image.frombytes('L', (m['w'], m['h']), m['data'][:m['w'] * m['h']])
    dxgi = DXGI[t['format']]
    hdr = bytearray(128)
    struct.pack_into('<4sIIIIIII', hdr, 0, b'DDS ', 124, 0x1 | 0x2 | 0x4 | 0x1000 | 0x80000, m['h'], m['w'], len(m['data']), 0, 1)
    struct.pack_into('<II4s', hdr, 76, 32, 0x4, b'DX10')
    struct.pack_into('<I', hdr, 108, 0x1000)
    dx10 = struct.pack('<IIIII', dxgi, 3, 0, 1, 0)
    img = Image.open(io.BytesIO(bytes(hdr) + dx10 + m['data']))
    img.load()
    if t['format'] == 'PF_BC4':
        img = img.convert('L')
    return img


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    for p in sorted(glob.glob(os.path.join(src, '*.uasset'))):
        base = p[:-7]
        ub = open(base + '.ubulk', 'rb').read() if os.path.isfile(base + '.ubulk') else b''
        t = read_texture(open(p, 'rb').read(), open(base + '.uexp', 'rb').read(), ub)
        img = to_image(t)
        out = os.path.join(dst, os.path.basename(base) + '.png')
        img.save(out)
        print(os.path.basename(base), t['format'], t['w'], 'x', t['h'], 'mips', len(t['mips']), img.mode, '->', out)
