"""The game's cooked textures (Texture2D / TextureCube / VolumeTexture, inline or .ubulk mips) -> float or 8-bit arrays,
and writers the editor imports: DDS cubemaps (RGBA16F, legacy header: UE 4.26 imports those as TextureCube), Radiance
.hdr, PNG; plus a tonemapped preview for looking at an HDR image."""
import os, struct, subprocess, sys, zlib
import numpy as np
sys.path[:0] = ['/work/iostore', '/work/cs']
from zen import Zen

HERE = os.path.dirname(os.path.abspath(__file__))
BCDECODE = os.path.join(HERE, 'bcdecode')
BLOCK = {'PF_DXT1': ('bc1', 8), 'PF_DXT5': ('bc3', 16), 'PF_BC4': ('bc4', 8), 'PF_BC5': ('bc5', 16), 'PF_BC6H': ('bc6h', 16),
         'PF_BC7': ('bc7', 16)}


def platform_data(blob, names):
    """Every FTexturePlatformData in `blob` (an export's bytes), found by its pixel format FName."""
    out = []
    for idx, n in enumerate(names):
        if not n.startswith('PF_'):
            continue
        key = struct.pack('<II', idx, 0)
        start = 0
        while True:
            at = blob.find(key, start)
            if at < 0:
                break
            start = at + 1
            try:
                out.append(_parse(blob, at))
            except Exception:
                pass
    return out


def _parse(d, at):
    p = at + 8 + 8                      # FName pixel format, int64 skip offset
    sx, sy, packed = struct.unpack_from('<iiI', d, p); p += 12
    n = struct.unpack_from('<i', d, p)[0]; p += 4
    if not 0 < n < 64:
        raise ValueError('no format string')
    fmt = d[p:p + n - 1].decode(); p += n
    if not fmt.startswith('PF_'):
        raise ValueError('format string ' + fmt)
    slices = packed & 0x3fffffff
    if packed & 0x40000000:
        p += 8
    first, nmips = struct.unpack_from('<ii', d, p); p += 8
    if not 0 < nmips < 20:
        raise ValueError('%d mips' % nmips)
    mips = []
    for k in range(nmips):
        cooked = struct.unpack_from('<I', d, p)[0]; p += 4
        flags = struct.unpack_from('<I', d, p)[0]; p += 4
        if flags & 0x2000:
            count, size = struct.unpack_from('<qq', d, p); p += 16
        else:
            count, size = struct.unpack_from('<ii', d, p); p += 8
        off = struct.unpack_from('<q', d, p)[0]; p += 8
        data = None
        if not flags & 0x1 and size > 0 and not flags & 0x20:   # inline (not end of file, not unused)
            data = d[p:p + size]; p += size
        mx, my, mz = struct.unpack_from('<iii', d, p); p += 12
        mips.append(dict(flags=flags, size=size, offset=off, data=data, x=mx, y=my, z=mz))
    return dict(fmt=fmt, x=sx, y=sy, slices=slices, packed=packed, first=first, mips=mips, at=at)


def decode_surface(data, fmt, w, h, work):
    """One surface (a face, a 2D mip) -> float32 HxWx4 (BC6H / float formats) or uint8 HxWx4."""
    if fmt in BLOCK:
        kind, blk = BLOCK[fmt]
        need = ((w + 3) // 4) * ((h + 3) // 4) * blk
        src = os.path.join(work, '_bc.raw')
        dst = os.path.join(work, '_bc.out')
        open(src, 'wb').write(data[:need])
        r = subprocess.run([BCDECODE, kind, str(w), str(h), src, dst], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError('bcdecode %s: %s' % (kind, r.stderr))
        raw = open(dst, 'rb').read()
        if kind == 'bc6h':
            rgb = np.frombuffer(raw, np.float32).reshape(h, w, 3)
            return np.concatenate([rgb, np.ones((h, w, 1), np.float32)], axis=2)
        return np.frombuffer(raw, np.uint8).reshape(h, w, 4)
    if fmt == 'PF_FloatRGBA':
        return np.frombuffer(data[:w * h * 8], np.float16).reshape(h, w, 4).astype(np.float32)
    if fmt == 'PF_A32B32G32R32F':
        return np.frombuffer(data[:w * h * 16], np.float32).reshape(h, w, 4).copy()
    if fmt == 'PF_B8G8R8A8':
        return np.frombuffer(data[:w * h * 4], np.uint8).reshape(h, w, 4)[..., [2, 1, 0, 3]]
    if fmt == 'PF_G8':
        g = np.frombuffer(data[:w * h], np.uint8).reshape(h, w, 1)
        return np.concatenate([g, g, g, np.full_like(g, 255)], axis=2)
    if fmt == 'PF_R16F':
        r = np.frombuffer(data[:w * h * 2], np.float16).reshape(h, w, 1).astype(np.float32)
        return np.concatenate([r, r, r, np.ones_like(r)], axis=2)
    raise ValueError('format ' + fmt)


def surface_size(fmt, w, h):
    if fmt in BLOCK:
        return ((w + 3) // 4) * ((h + 3) // 4) * BLOCK[fmt][1]
    return w * h * {'PF_FloatRGBA': 8, 'PF_A32B32G32R32F': 16, 'PF_B8G8R8A8': 4, 'PF_G8': 1, 'PF_R16F': 2}[fmt]


def faces(t, work, mip=0, bulk=None):
    """A cube's 6 faces of mip `mip` (float32 6xHxWx4): +X -X +Y -Y +Z -Z."""
    m = t['mips'][mip]
    data = m['data'] if m['data'] is not None else (bulk[m['offset']:m['offset'] + m['size']] if bulk else None)
    if data is None:
        raise ValueError('mip %d is not inline' % mip)
    w, h = m['x'], m['y']
    step = surface_size(t['fmt'], w, h)
    out = []
    for f in range(6):
        out.append(decode_surface(data[f * step:(f + 1) * step], t['fmt'], w, h, work).astype(np.float32))
    return np.stack(out)


def write_dds_cube(path, faces6):
    """RGBA16F cubemap DDS (legacy header, D3DFMT_A16B16G16R16F = 113), mip 0 only."""
    n, h, w, _ = faces6.shape
    hdr = bytearray(128)
    struct.pack_into('<4sIIIIIII', hdr, 0, b'DDS ', 124, 0x1 | 0x2 | 0x4 | 0x1000 | 0x8, h, w, w * 8, 0, 1)
    # pixel format at 76: size 32, flags DDPF_FOURCC, fourcc 113
    struct.pack_into('<II', hdr, 76, 32, 0x4)
    struct.pack_into('<I', hdr, 84, 113)
    struct.pack_into('<II', hdr, 108, 0x1000 | 0x8, 0x200 | 0x400 | 0x800 | 0x1000 | 0x2000 | 0x4000 | 0x8000)   # caps, caps2 cubemap + 6 faces
    body = b''.join(faces6[f].astype(np.float16).tobytes() for f in range(6))
    open(path, 'wb').write(bytes(hdr) + body)


def write_hdr(path, img):
    """Radiance RGBE (flat, no run-length encoding)."""
    h, w = img.shape[:2]
    rgb = np.maximum(img[..., :3].astype(np.float64), 0.0)
    mx = rgb.max(axis=2)
    e = np.zeros_like(mx)
    nz = mx > 1e-32
    m, ex = np.frexp(mx[nz])
    e[nz] = ex
    scale = np.zeros_like(mx)
    scale[nz] = m * 256.0 / mx[nz]
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = np.clip(rgb * scale[..., None], 0, 255).astype(np.uint8)
    out[..., 3] = np.where(nz, e + 128, 0).astype(np.uint8)
    with open(path, 'wb') as f:
        f.write(b'#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y %d +X %d\n' % (h, w))
        f.write(out.tobytes())


def png(path, img):
    img = np.ascontiguousarray(img)
    if img.ndim == 2:
        img = img[:, :, None]
    h, w, c = img.shape
    ctype = {1: 0, 2: 4, 3: 2, 4: 6}[c]
    raw = b''.join(b'\0' + img[y].tobytes() for y in range(h))
    def chunk(k, p):
        return struct.pack('>I', len(p)) + k + p + struct.pack('>I', zlib.crc32(k + p) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, ctype, 0, 0, 0)) +
                           chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def preview(img, exposure=None):
    """HDR -> sRGB 8-bit (exposure: the image's mean luminance to 0.18 unless given)."""
    rgb = np.maximum(img[..., :3], 0.0)
    if exposure is None:
        lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
        exposure = 0.18 / max(float(np.exp(np.mean(np.log(lum + 1e-6)))), 1e-6)
    x = rgb * exposure
    x = x / (1.0 + x)
    s = np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)
    return (np.clip(s, 0, 1) * 255 + 0.5).astype(np.uint8)


def cross(faces6):
    """Horizontal cross layout of +X -X +Y -Y +Z -Z (for previews)."""
    n, h, w, c = faces6.shape
    out = np.zeros((3 * h, 4 * w, c), faces6.dtype)
    pos = {2: (0, 1), 1: (1, 0), 4: (1, 1), 0: (1, 2), 5: (1, 3), 3: (2, 1)}   # +Y top; -X +Z +X -Z middle; -Y bottom
    for f, (r, col) in pos.items():
        out[r * h:(r + 1) * h, col * w:(col + 1) * w] = faces6[f]
    return out
