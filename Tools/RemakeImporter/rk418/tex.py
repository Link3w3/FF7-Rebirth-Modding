"""Remake (UE 4.18 SQEX) cooked Texture2D: platform data, mips, BC1/BC3/BC4/BC5 decode, PNG out."""
import sys, os, struct
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkg418, uprops
from binr import B

BULK_SEPARATE = 0x100
BULK_INLINE = 0x40
BULK_UNUSED = 0x20

def mip_entry(r):
    cooked = r.u32()
    flags, count, size, off = r.un('<IiiQ')
    data = None
    if flags & BULK_INLINE and not flags & BULK_SEPARATE and size > 0:
        data = r.raw(size)
    sx, sy = r.un('<ii')
    return dict(cooked=cooked, flags=flags, count=count, size=size, offset=off, data=data, x=sx, y=sy)

def platform(pkg, schema, i=0):
    cls, v, end = uprops.read_export(schema, pkg, i)
    e = pkg.exports[i]
    r = B(pkg.d, end, pkg.names, e['off'] + e['size'])
    r.u32()                     # object guid flag
    r.un('<BB'); r.un('<BB')    # strip flags (UTexture, UTexture2D)
    cooked = r.u32()
    pf_name = r.name()
    skip = r.i32()
    sx, sy, packed = r.un('<iiI')
    pf = r.fstr()
    a, b, n_streamed, d_, n_mips = r.un('<5i')
    tail = mip_entry(r)
    f_, n_tail = r.un('<ii')
    mips = [mip_entry(r) for _ in range(n_mips)]
    return dict(props=v.py(), format=pf, x=sx, y=sy, packed=packed, n_streamed=n_streamed, tail=tail, n_tail=n_tail, mips=mips, end=r.p)

def mip_bytes(pd, path, k=0):
    m = pd['mips'][k]
    if m['flags'] & BULK_SEPARATE:
        with open(path[:-7] + '.ubulk', 'rb') as f:
            f.seek(m['offset']); return f.read(m['size'])
    if m['data'] is not None:
        return m['data']
    # in the packed tail: mips n_streamed.. back to back
    off = 0
    for j in range(pd['n_streamed'], k):
        off += block_size(pd['format'], pd['mips'][j]['x'], pd['mips'][j]['y'])
    return pd['tail']['data'][off:off + block_size(pd['format'], m['x'], m['y'])]

BPB = {'PF_DXT1': 8, 'PF_BC4': 8, 'PF_DXT5': 16, 'PF_BC5': 16, 'PF_DXT3': 16, 'PF_BC7': 16, 'PF_BC6H': 16}
def block_size(fmt, x, y):
    if fmt in BPB:
        return max(1, (x + 3) // 4) * max(1, (y + 3) // 4) * BPB[fmt]
    if fmt == 'PF_B8G8R8A8': return x * y * 4
    if fmt == 'PF_G8': return x * y
    raise NotImplementedError(fmt)

def _rgb565(c):
    r = ((c >> 11) & 31).astype(np.uint32); g = ((c >> 5) & 63).astype(np.uint32); b = (c & 31).astype(np.uint32)
    return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], -1).astype(np.int32)

def _unblock(px, bw, bh, x, y, ch):
    # px: (bh, bw, 16, ch) -> image (y, x, ch)
    img = px.reshape(bh, bw, 4, 4, ch).transpose(0, 2, 1, 3, 4).reshape(bh * 4, bw * 4, ch)
    return img[:y, :x]

def bc1(data, x, y, alpha=True):
    bw, bh = max(1, (x + 3) // 4), max(1, (y + 3) // 4)
    a = np.frombuffer(data, dtype=np.uint8, count=bw * bh * 8).reshape(-1, 8)
    c0 = a[:, 0].astype(np.uint16) | (a[:, 1].astype(np.uint16) << 8)
    c1 = a[:, 2].astype(np.uint16) | (a[:, 3].astype(np.uint16) << 8)
    idx = (a[:, 4].astype(np.uint32) | (a[:, 5].astype(np.uint32) << 8) | (a[:, 6].astype(np.uint32) << 16) | (a[:, 7].astype(np.uint32) << 24))
    p0, p1 = _rgb565(c0), _rgb565(c1)
    four = (c0 > c1)[:, None]
    p2 = np.where(four, (2 * p0 + p1) // 3, (p0 + p1) // 2)
    p3 = np.where(four, (p0 + 2 * p1) // 3, 0)
    pal = np.stack([p0, p1, p2, p3], 1)                       # (n, 4, 3)
    alp = np.stack([np.full(len(a), 255), np.full(len(a), 255), np.full(len(a), 255), np.where(four[:, 0], 255, 0)], 1)
    sel = (idx[:, None] >> (2 * np.arange(16, dtype=np.uint32))[None, :]) & 3   # (n, 16)
    rgb = np.take_along_axis(pal, sel[:, :, None].astype(np.int64).repeat(3, 2), 1)
    al = np.take_along_axis(alp, sel.astype(np.int64), 1)
    px = np.concatenate([rgb, al[:, :, None]], 2).astype(np.uint8).reshape(bh, bw, 16, 4)
    return _unblock(px, bw, bh, x, y, 4)

def _bc4_blocks(a):
    """a: (n, 8) uint8 -> (n, 16) uint8"""
    r0 = a[:, 0].astype(np.int32); r1 = a[:, 1].astype(np.int32)
    bits = np.zeros(len(a), dtype=np.uint64)
    for k in range(6):
        bits |= a[:, 2 + k].astype(np.uint64) << np.uint64(8 * k)
    sel = ((bits[:, None] >> (np.uint64(3) * np.arange(16, dtype=np.uint64))[None, :]) & np.uint64(7)).astype(np.int64)
    eight = (r0 > r1)[:, None]
    k = np.arange(8)[None, :]
    pal8 = np.where(k == 0, r0[:, None], np.where(k == 1, r1[:, None], ((8 - k) * r0[:, None] + (k - 1) * r1[:, None]) // 7))
    pal6 = np.where(k == 0, r0[:, None], np.where(k == 1, r1[:, None], np.where(k == 6, 0, np.where(k == 7, 255, ((6 - k) * r0[:, None] + (k - 1) * r1[:, None]) // 5))))
    pal = np.where(eight, pal8, pal6)
    return np.take_along_axis(pal, sel, 1).astype(np.uint8)

def bc4(data, x, y):
    bw, bh = max(1, (x + 3) // 4), max(1, (y + 3) // 4)
    a = np.frombuffer(data, dtype=np.uint8, count=bw * bh * 8).reshape(-1, 8)
    return _unblock(_bc4_blocks(a).reshape(bh, bw, 16, 1), bw, bh, x, y, 1)

def bc5(data, x, y):
    bw, bh = max(1, (x + 3) // 4), max(1, (y + 3) // 4)
    a = np.frombuffer(data, dtype=np.uint8, count=bw * bh * 16).reshape(-1, 16)
    r = _bc4_blocks(a[:, :8]); g = _bc4_blocks(a[:, 8:])
    return _unblock(np.stack([r, g], -1).reshape(bh, bw, 16, 2), bw, bh, x, y, 2)

def bc3(data, x, y):
    bw, bh = max(1, (x + 3) // 4), max(1, (y + 3) // 4)
    a = np.frombuffer(data, dtype=np.uint8, count=bw * bh * 16).reshape(-1, 16)
    al = _bc4_blocks(a[:, :8])
    col = bc1(a[:, 8:].tobytes(), bw * 4, bh * 4)
    col[..., 3] = _unblock(al.reshape(bh, bw, 16, 1), bw, bh, bw * 4, bh * 4, 1)[..., 0]
    return col[:y, :x]

def decode(fmt, data, x, y):
    """-> (image uint8 (y, x, c), PIL mode)"""
    if fmt == 'PF_DXT1':
        im = bc1(data, x, y)
        return (im, 'RGBA') if (im[..., 3] < 255).any() else (np.ascontiguousarray(im[..., :3]), 'RGB')
    if fmt == 'PF_DXT5':
        return bc3(data, x, y), 'RGBA'
    if fmt == 'PF_BC4':
        return np.ascontiguousarray(bc4(data, x, y)[..., 0]), 'L'
    if fmt == 'PF_BC5':
        rg = bc5(data, x, y).astype(np.float32) / 255.0
        nx, ny = rg[..., 0] * 2 - 1, rg[..., 1] * 2 - 1
        nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
        b = np.clip((nz * 0.5 + 0.5) * 255 + 0.5, 0, 255).astype(np.uint8)
        return np.dstack([bc5(data, x, y), b]), 'RGB'
    if fmt == 'PF_B8G8R8A8':
        im = np.frombuffer(data, np.uint8).reshape(y, x, 4)[..., [2, 1, 0, 3]]
        return np.ascontiguousarray(im), 'RGBA'
    if fmt == 'PF_G8':
        return np.frombuffer(data, np.uint8).reshape(y, x), 'L'
    raise NotImplementedError(fmt)

def to_png(path, schema, out_png):
    from PIL import Image
    p = pkg418.Package(path)
    pd = platform(p, schema)
    data = mip_bytes(pd, path, 0)
    m0 = pd['mips'][0]
    im, mode = decode(pd['format'], data, m0['x'], m0['y'])
    Image.fromarray(im, mode).save(out_png, compress_level=6)
    return pd, mode

if __name__ == '__main__':
    from schema import Schema
    S = Schema()
    pd, mode = to_png(sys.argv[1], S, sys.argv[2])
    print(pd['format'], pd['x'], pd['y'], mode, {k: v for k, v in pd['props'].items() if k not in ('LightingGuid',)})
