"""Decode mip 0 of a cooked UE 4.26 texture (.uexp + .ubulk, the large mips in .ubulk, largest first) to PNG."""
import re, sys, os
import numpy as np
import texture2ddecoder as td
from PIL import Image

BPP = {'PF_DXT1': 4, 'PF_BC1': 4, 'PF_DXT5': 8, 'PF_BC3': 8, 'PF_BC5': 8, 'PF_BC4': 4, 'PF_BC7': 8, 'PF_ATI2': 8}


def info(uexp):
    d = open(uexp, 'rb').read()
    fmts = [m.decode() for m in re.findall(rb'PF_[A-Z0-9_]+', d)]
    return fmts


def decode(base, w, h, out):
    fmts = info(base + '.uexp')
    fmt = fmts[0]
    bulk = open(base + '.ubulk', 'rb').read()
    n = w * h * BPP[fmt] // 8
    blob = bulk[:n]
    if fmt in ('PF_DXT1', 'PF_BC1'):
        px = td.decode_bc1(blob, w, h)
    elif fmt in ('PF_DXT5', 'PF_BC3'):
        px = td.decode_bc3(blob, w, h)
    elif fmt in ('PF_BC5', 'PF_ATI2'):
        px = td.decode_bc5(blob, w, h)
    elif fmt == 'PF_BC4':
        px = td.decode_bc4(blob, w, h)
    elif fmt == 'PF_BC7':
        px = td.decode_bc7(blob, w, h)
    else:
        raise ValueError(fmt)
    img = Image.frombytes('RGBA', (w, h), px, 'raw', 'BGRA')
    img.save(out)
    return fmt


if __name__ == '__main__':
    base, w, h, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    print(decode(base, w, h, out))
