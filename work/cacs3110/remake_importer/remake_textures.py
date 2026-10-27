"""FF7 Remake textures to image files for the End editor's import: PNG (8 bits) for BC1/BC3/BC4/BC5/BGRA8/G8 (rk418's
tex.py decoders), OpenEXR (half floats) for the HDR BC6H textures (their emissive _EH maps). Written without PIL.

The game's cooked Texture2D platform data comes in two layouts: with the "has opt data" bit of its packed word (the
streamed textures: 3 more ints before the mip count) and without it (the small ones, 4x4 and 1x1, all mips in the
tail); tex.platform reads the first only, platform() here both."""
import os
import struct
import zlib

import numpy as np

import tex
import uprops
from binr import B


def platform(pkg, schema, i=0):
    cls, v, end = uprops.read_export(schema, pkg, i)
    e = pkg.exports[i]
    r = B(pkg.d, end, pkg.names, e['off'] + e['size'])
    r.u32()                     # object guid flag
    r.un('<BB'); r.un('<BB')    # strip flags (UTexture, UTexture2D)
    r.u32()                     # cooked
    r.name()                    # the pixel format's name
    r.i32()                     # skip offset
    sx, sy, packed = r.un('<iiI')
    pf = r.fstr()
    if packed & 0x40000000:
        _a, _b, n_streamed, _d, n_mips = r.un('<5i')
    else:
        n_streamed, n_mips = r.un('<2i')
    tail = tex.mip_entry(r)
    _f, n_tail = r.un('<ii')
    mips = [tex.mip_entry(r) for _ in range(n_mips)]
    if not mips:
        raise ValueError('the texture has no mips')
    return dict(props=v.py(), format=pf, x=sx, y=sy, packed=packed, n_streamed=n_streamed, tail=tail, n_tail=n_tail,
                mips=mips, end=r.p)


def mip0(pkg, schema, uasset_path):
    """(platform data, mip 0's bytes)"""
    pd = platform(pkg, schema)
    tex.BPB.setdefault('PF_BC6H', 16)
    return pd, tex.mip_bytes(pd, uasset_path, 0)


def decode(fmt, data, x, y):
    """-> (image, mode, file extension): uint8 for PNG, float16 RGB for EXR (BC6H)"""
    if fmt == 'PF_BC6H':
        return bc6h(data, x, y), 'RGB16F', '.exr'
    img, mode = tex.decode(fmt, data, x, y)
    return img, mode, '.png'


# ---------------------------------------------------------------------------------------------------------------------
# PNG and EXR
# ---------------------------------------------------------------------------------------------------------------------

def _atomic(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp%d' % os.getpid()
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, path)


def png_bytes(img):
    """uint8 (h, w) or (h, w, 1-4) -> PNG (8 bits per channel, Paeth-filtered rows)"""
    img = np.ascontiguousarray(img)
    if img.ndim == 2:
        img = img[:, :, None]
    h, w, c = img.shape
    ctype = {1: 0, 2: 4, 3: 2, 4: 6}[c]
    x = img.reshape(h, w * c).astype(np.int16)
    a = np.zeros_like(x)
    a[:, c:] = x[:, :-c]                                    # left
    b = np.zeros_like(x)
    b[1:] = x[:-1]                                          # up
    cc = np.zeros_like(x)
    cc[1:, c:] = x[:-1, :-c]                                # up-left
    pa, pb, pc = np.abs(b - cc), np.abs(a - cc), np.abs(a + b - 2 * cc)
    pred = np.where((pa <= pb) & (pa <= pc), a, np.where(pb <= pc, b, cc))
    rows = np.empty((h, w * c + 1), np.uint8)
    rows[:, 0] = 4
    rows[:, 1:] = ((x - pred) & 255).astype(np.uint8)

    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xFFFFFFFF)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, ctype, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(rows.tobytes(), 6)) + chunk(b'IEND', b''))


def exr_bytes(img):
    """float16 (h, w, 3) RGB -> OpenEXR 2.0 scanline file, HALF channels B, G, R, no compression"""
    img = np.ascontiguousarray(img, dtype=np.float16)
    h, w, c = img.shape
    names = ['B', 'G', 'R'] if c == 3 else ['A', 'B', 'G', 'R']
    order = {'R': 0, 'G': 1, 'B': 2, 'A': 3}

    def attr(name, kind, payload):
        return name.encode() + b'\0' + kind.encode() + b'\0' + struct.pack('<i', len(payload)) + payload
    chlist = b''.join(n.encode() + b'\0' + struct.pack('<iB3xii', 1, 0, 1, 1) for n in names) + b'\0'
    box = struct.pack('<iiii', 0, 0, w - 1, h - 1)
    head = (b'\x76\x2f\x31\x01' + struct.pack('<I', 2) + attr('channels', 'chlist', chlist) +
            attr('compression', 'compression', b'\0') + attr('dataWindow', 'box2i', box) + attr('displayWindow', 'box2i', box) +
            attr('lineOrder', 'lineOrder', b'\0') + attr('pixelAspectRatio', 'float', struct.pack('<f', 1.0)) +
            attr('screenWindowCenter', 'v2f', struct.pack('<ff', 0.0, 0.0)) + attr('screenWindowWidth', 'float', struct.pack('<f', 1.0)) +
            b'\0')
    line = 2 * w * len(names)
    first = len(head) + 8 * h
    offsets = np.arange(h, dtype=np.uint64) * np.uint64(8 + line) + np.uint64(first)
    planes = np.stack([img[:, :, order[n]] for n in names], 1)            # (h, channels, w)
    rows = np.empty((h, 8 + line), np.uint8)
    rows[:, 0:4] = np.arange(h, dtype='<i4').view(np.uint8).reshape(h, 4)
    rows[:, 4:8] = np.full(h, line, dtype='<i4').view(np.uint8).reshape(h, 4)
    rows[:, 8:] = planes.astype('<f2').view(np.uint8).reshape(h, line)
    return head + offsets.astype('<u8').tobytes() + rows.tobytes()


def write_image(path, img):
    _atomic(path, exr_bytes(img) if path.lower().endswith('.exr') else png_bytes(img))


# ---------------------------------------------------------------------------------------------------------------------
# BC6H (unsigned, DXGI_FORMAT_BC6H_UF16: what UE4 cooks TC_HDR_Compressed to)
# ---------------------------------------------------------------------------------------------------------------------

# each mode: its bits after the mode bits, in order: <endpoint><component><first bit>[:<count>][r: bits reversed]
#   endpoints w x (region 0), y z (region 1); d = the partition
_BC6H_MODES = {
    0b00: (10, (5, 5, 5), True, 'gy4 by4 bz4 rw0:10 gw0:10 bw0:10 rx0:5 gz4 gy0:4 gx0:5 bz0 gz0:4 bx0:5 bz1 by0:4 ry0:5 bz2 rz0:5 bz3 d0:5'),
    0b01: (7, (6, 6, 6), True, 'gy5 gz4 gz5 rw0:7 bz0 bz1 by4 gw0:7 by5 bz2 gy4 bw0:7 bz3 bz5 bz4 rx0:6 gy0:4 gx0:6 gz0:4 bx0:6 by0:4 ry0:6 rz0:6 d0:5'),
    0b00010: (11, (5, 4, 4), True, 'rw0:10 gw0:10 bw0:10 rx0:5 rw10 gy0:4 gx0:4 gw10 bz0 gz0:4 bx0:4 bw10 bz1 by0:4 ry0:5 bz2 rz0:5 bz3 d0:5'),
    0b00110: (11, (4, 5, 4), True, 'rw0:10 gw0:10 bw0:10 rx0:4 rw10 gz4 gy0:4 gx0:5 gw10 gz0:4 bx0:4 bw10 bz1 by0:4 ry0:4 bz0 bz2 rz0:4 gy4 bz3 d0:5'),
    0b01010: (11, (4, 4, 5), True, 'rw0:10 gw0:10 bw0:10 rx0:4 rw10 by4 gy0:4 gx0:4 gw10 bz0 gz0:4 bx0:5 bw10 by0:4 ry0:4 bz1 bz2 rz0:4 bz4 bz3 d0:5'),
    0b01110: (9, (5, 5, 5), True, 'rw0:9 by4 gw0:9 gy4 bw0:9 bz4 rx0:5 gz4 gy0:4 gx0:5 bz0 gz0:4 bx0:5 bz1 by0:4 ry0:5 bz2 rz0:5 bz3 d0:5'),
    0b10010: (8, (6, 5, 5), True, 'rw0:8 gz4 by4 gw0:8 bz2 gy4 bw0:8 bz3 bz4 rx0:6 gy0:4 gx0:5 bz0 gz0:4 bx0:5 bz1 by0:4 ry0:6 rz0:6 d0:5'),
    0b10110: (8, (5, 6, 5), True, 'rw0:8 bz0 by4 gw0:8 gy5 gy4 bw0:8 gz5 bz4 rx0:5 gz4 gy0:4 gx0:6 gz0:4 bx0:5 bz1 by0:4 ry0:5 bz2 rz0:5 bz3 d0:5'),
    0b11010: (8, (5, 5, 6), True, 'rw0:8 bz1 by4 gw0:8 by5 gy4 bw0:8 bz5 bz4 rx0:5 gz4 gy0:4 gx0:5 bz0 gz0:4 bx0:6 by0:4 ry0:5 bz2 rz0:5 bz3 d0:5'),
    0b11110: (6, (6, 6, 6), False, 'rw0:6 gz4 bz0 bz1 by4 gw0:6 gy5 by5 bz2 gy4 bw0:6 gz5 bz3 bz5 bz4 rx0:6 gy0:4 gx0:6 gz0:4 bx0:6 by0:4 ry0:6 rz0:6 d0:5'),
    0b00011: (10, (10, 10, 10), False, 'rw0:10 gw0:10 bw0:10 rx0:10 gx0:10 bx0:10'),
    0b00111: (11, (9, 9, 9), True, 'rw0:10 gw0:10 bw0:10 rx0:9 rw10 gx0:9 gw10 bx0:9 bw10'),
    0b01011: (12, (8, 8, 8), True, 'rw0:10 gw0:10 bw0:10 rx0:8 rw10:2r gx0:8 gw10:2r bx0:8 bw10:2r'),
    0b01111: (16, (4, 4, 4), True, 'rw0:10 gw0:10 bw0:10 rx0:4 rw10:6r gx0:4 gw10:6r bx0:4 bw10:6r'),
}
_P2 = [
    '0011001100110011', '0001000100010001', '0111011101110111', '0001001100110111', '0000000100010011', '0011011101111111',
    '0001001101111111', '0000000100110111', '0000000000010011', '0011011111111111', '0000000101111111', '0000000000010111',
    '0001011111111111', '0000000011111111', '0000111111111111', '0000000000001111', '0000100011101111', '0111000100000000',
    '0000000010001110', '0111001100010000', '0011000100000000', '0000100011001110', '0000000010001100', '0111001100110001',
    '0011000100010000', '0000100010001100', '0110011001100110', '0011011001101100', '0001011111101000', '0000111111110000',
    '0111000110001110', '0011100110011100']
_ANCHOR2 = [15] * 16 + [15, 2, 8, 2, 2, 8, 8, 15, 2, 8, 2, 2, 8, 8, 2, 2]
_W3 = np.array([0, 9, 18, 27, 37, 46, 55, 64], np.int64)
_W4 = np.array([0, 4, 9, 13, 17, 21, 26, 30, 34, 38, 43, 47, 51, 55, 60, 64], np.int64)


def _layout(text):
    out = []
    for tok in text.split():
        rev = tok.endswith('r')
        tok = tok.rstrip('r')
        head, _, count = tok.partition(':')
        out.append((head[:2] if head[0] != 'd' else 'd', int(head[2:] if head[0] != 'd' else head[1:]), int(count or 1), rev))
    return out


def _unquantize(c, bits):
    if bits >= 15:
        return c
    top = (1 << bits) - 1
    return np.where(c == 0, 0, np.where(c == top, 0xFFFF, ((c << 16) + 0x8000) >> bits))


def bc6h(data, x, y):
    """BC6H UF16 blocks -> float16 (y, x, 3)"""
    bw, bh = max(1, (x + 3) // 4), max(1, (y + 3) // 4)
    blocks = np.frombuffer(bytes(data), np.uint8, count=bw * bh * 16).reshape(-1, 16)
    bits = np.unpackbits(blocks, axis=1, bitorder='little').astype(np.int64)        # (n, 128), bit k of the block
    n = len(blocks)
    m2 = bits[:, 0] | (bits[:, 1] << 1)
    mode = np.where(m2 < 2, m2, m2 | (bits[:, 2] << 2) | (bits[:, 3] << 3) | (bits[:, 4] << 4))
    half = np.zeros((n, 16, 3), np.int64)                                            # (reserved modes stay 0)
    for mv, (wbits, dbits, transformed, layout) in _BC6H_MODES.items():
        sel = np.nonzero(mode == mv)[0]
        if not len(sel):
            continue
        b = bits[sel]
        e = {k: np.zeros(len(sel), np.int64) for k in ('rw', 'gw', 'bw', 'rx', 'gx', 'bx', 'ry', 'gy', 'by', 'rz', 'gz', 'bz', 'd')}
        pos = 2 if mv < 2 else 5
        for name, lo, count, rev in _layout(layout):
            seg = b[:, pos:pos + count]
            if rev:
                seg = seg[:, ::-1]
            e[name] |= (seg << np.arange(count, dtype=np.int64)).sum(1) << lo
            pos += count
        two = mv not in (0b00011, 0b00111, 0b01011, 0b01111)
        ends = []                                                                    # (w, x, y, z) of r, g, b
        for ci, ch in enumerate('rgb'):
            w = e[ch + 'w']
            comp = [w]
            for k in ('x', 'y', 'z') if two else ('x',):
                v = e[ch + k]
                if transformed:
                    db = dbits[ci]
                    v = np.where(v & (1 << (db - 1)), v - (1 << db), v)              # signed delta
                    v = (w + v) & ((1 << wbits) - 1)
                comp.append(v)
            ends.append([_unquantize(c, wbits) for c in comp])
        # the indices
        if two:
            part = e['d']
            p2 = np.array([[int(ch) for ch in s] for s in _P2], np.int64)[part]       # (m, 16) region of each pixel
            anchor = np.array(_ANCHOR2, np.int64)[part]
            pos = np.full(len(sel), 82, np.int64)
            weights = _W3
            nbits = 3
        else:
            p2 = np.zeros((len(sel), 16), np.int64)
            anchor = np.full(len(sel), -1, np.int64)
            pos = np.full(len(sel), 65, np.int64)
            weights = _W4
            nbits = 4
        idx = np.zeros((len(sel), 16), np.int64)
        for i in range(16):
            cnt = np.full(len(sel), nbits, np.int64)
            cnt = np.where((i == 0) | (anchor == i), nbits - 1, cnt)
            val = np.zeros(len(sel), np.int64)
            for k in range(nbits):
                bit = np.take_along_axis(b, np.minimum(pos + k, 127)[:, None], 1)[:, 0]
                val |= np.where(k < cnt, bit << k, 0)
            idx[:, i] = val
            pos += cnt
        wt = weights[idx]                                                            # (m, 16)
        for ci in range(3):
            c = ends[ci]
            if two:
                e0 = np.where(p2 == 0, c[0][:, None], c[2][:, None])
                e1 = np.where(p2 == 0, c[1][:, None], c[3][:, None])
            else:
                e0, e1 = c[0][:, None], c[1][:, None]
            v = (e0 * (64 - wt) + e1 * wt + 32) >> 6
            half[sel, :, ci] = (v * 31) >> 6
    img = half.astype(np.uint16).view(np.float16).reshape(bh, bw, 4, 4, 3).transpose(0, 2, 1, 3, 4).reshape(bh * 4, bw * 4, 3)
    return np.ascontiguousarray(img[:y, :x])
