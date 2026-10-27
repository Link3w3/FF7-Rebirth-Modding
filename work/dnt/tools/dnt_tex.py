"""Makes a Dissidia NT outfit's material textures for Rebirth's material instances (dnt_build.py's <Model>_tex.json):
per Dissidia NT material, from its G1T textures by type, as Dissidia NT's own shaders read them (PBB/PBS G-buffer and
forward passes: sSpMap R gloss, G reflectance, B metal flag; the normal map n = 2t - 1 on (cross(T, N) w, T, N)):
    _C  albedo (type 1, RGB, sRGB); where the metal flag is on, the metal's specular colour albedo (1 - reflectance)
        (in linear light), as Unreal's metallic base colour
    _A  its alpha (cut-outs: hair, lashes, torn cloth)
    _N  normal (type 3) in Unreal's tangent frame of the imported model: (n.y, -n.x, n.z)
    _R  roughness from gloss g (type 2 R): Dissidia NT's Blinn-Phong power 2^(10 g + 1) as GGX, (1 + 2^(10 g))^(-1/4)
    _M  metal (type 2 B >= 0.5: 0 or 1)
    _O  occlusion (type 5 R)
Grey maps are 8-bit greyscale PNGs. Also writes <job>_result.json: which materials' alpha is all opaque (their cloth
slots then take Rebirth's opaque BodyA instead of BodyB with Coverage).
    dnt_tex.py <outfit.g1t> <job.json> <out dir>"""
import json
import os
import struct
import sys

import numpy as np
import texture2ddecoder as t2d
from PIL import Image

FORMATS = {0x00: ('rgba8', 32), 0x01: ('bgra8', 32), 0x59: ('bc1', 4), 0x5B: ('bc3', 8), 0x5C: ('bc4', 4),
           0x5D: ('bc5', 8), 0x5F: ('bc7', 8), 0x06: ('bc1', 4), 0x08: ('bc3', 8)}


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
        out.append(dict(index=i, format=fmt, width=w, height=h, data=p + hdr))
    return out


def decode(b, e):
    name, bpp = FORMATS[e['format']]
    w, h = e['width'], e['height']
    if name in ('rgba8', 'bgra8'):
        a = np.frombuffer(b, np.uint8, w * h * 4, e['data']).reshape(h, w, 4)
        return a[:, :, [2, 1, 0, 3]].copy() if name == 'bgra8' else a.copy()
    bw, bh = max(1, (w + 3) // 4), max(1, (h + 3) // 4)
    n = bw * bh * (8 if bpp == 4 else 16)
    raw = b[e['data']:e['data'] + n]
    fn = {'bc1': t2d.decode_bc1, 'bc3': t2d.decode_bc3, 'bc4': t2d.decode_bc4, 'bc5': t2d.decode_bc5,
          'bc7': t2d.decode_bc7}[name]
    return np.frombuffer(fn(raw, w, h), np.uint8).reshape(h, w, 4)[:, :, [2, 1, 0, 3]].copy()


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(np.maximum(c, 0), 1 / 2.4) - 0.055)


def albedo_for_unreal(albedo, spec):
    """the albedo with the metal's specular colour where the metal flag is on (Dissidia NT: spec = albedo (1 - refl))"""
    if spec is None:
        return albedo[:, :, :3]
    if spec.shape[:2] != albedo.shape[:2]:
        spec = np.asarray(Image.fromarray(spec).resize((albedo.shape[1], albedo.shape[0]), Image.BILINEAR))
    metal = spec[:, :, 2] >= 128
    if not metal.any():
        return albedo[:, :, :3]
    lin = srgb_to_linear(albedo[:, :, :3].astype(np.float64) / 255)
    refl = spec[:, :, 1].astype(np.float64) / 255
    met = lin * (1 - refl)[:, :, None]
    out = np.where(metal[:, :, None], met, lin)
    return np.clip(np.round(linear_to_srgb(out) * 255), 0, 255).astype(np.uint8)


def normal_for_unreal(n):
    """(n.y, -n.x, n.z): Dissidia NT's x along cross(T, N) w, y along T; the imported model's tangent is T"""
    out = np.empty_like(n[:, :, :3])
    out[:, :, 0] = n[:, :, 1]
    out[:, :, 1] = 255 - n[:, :, 0]
    out[:, :, 2] = n[:, :, 2]
    return out


def roughness_for_unreal(gloss):
    g = gloss.astype(np.float64) / 255
    return np.round((1 + np.exp2(10 * g)) ** -0.25 * 255)


def main(g1t, job_path, out_dir):
    b = open(g1t, 'rb').read()
    es = entries(b)
    job = json.load(open(job_path))
    os.makedirs(out_dir, exist_ok=True)
    cache = {}

    def tex(i):
        if i not in cache:
            cache[i] = decode(b, es[i])
        return cache[i]
    result = {'opaque': [], 'written': []}
    for mi, spec in sorted(job['materials'].items(), key=lambda kv: int(kv[0])):
        t = {int(k): v for k, v in spec['textures'].items()}
        stem = spec['stem']
        maps = spec['maps']
        albedo = tex(t[1]) if 1 in t else None

        def save_rgb(a, suffix):
            p = os.path.join(out_dir, stem + suffix + '.png')
            Image.fromarray(a[:, :, :3]).save(p, optimize=False, compress_level=6)
            result['written'].append(os.path.basename(p))

        def save_grey(a, suffix):
            p = os.path.join(out_dir, stem + suffix + '.png')
            Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'L').save(p, optimize=False, compress_level=6)
            result['written'].append(os.path.basename(p))
        spec = tex(t[2]) if 2 in t else None
        if '_C' in maps and albedo is not None:
            save_rgb(albedo_for_unreal(albedo, spec), '_C')
        if '_A' in maps and albedo is not None:
            alpha = albedo[:, :, 3]
            if (alpha < 26).mean() < 0.002:      # (cut-outs are near 0; the coat's alpha 0.4 - 1 is a mask, not holes)
                result['opaque'].append(int(mi))
            save_grey(alpha, '_A')
        if '_N' in maps and 3 in t:
            save_rgb(normal_for_unreal(tex(t[3])), '_N')
        if spec is not None and ('_R' in maps or '_M' in maps):
            if '_R' in maps:
                save_grey(roughness_for_unreal(spec[:, :, 0]), '_R')
            if '_M' in maps:
                save_grey(np.where(spec[:, :, 2] >= 128, 255, 0), '_M')
        if '_O' in maps:
            if 5 in t:
                save_grey(tex(t[5])[:, :, 0], '_O')
            elif albedo is not None:
                save_grey(np.full(albedo.shape[:2], 255), '_O')
        print('material', mi, stem, 'done', flush=True)
    json.dump(result, open(os.path.join(out_dir, os.path.basename(job_path).replace('.json', '_result.json')), 'w'), indent=1)
    print(len(result['written']), 'files; opaque', result['opaque'])


if __name__ == '__main__':
    main(*sys.argv[1:4])
