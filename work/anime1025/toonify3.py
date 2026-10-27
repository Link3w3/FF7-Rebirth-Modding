"""Toonier textures (third way): the fine detail smoothed away keeping the edges (domain transform), the shading inside
each shape flattened toward the shape's own colour (a wide edge-aware smoothing: luminance pulled most of the way,
colour all the way, a touch more saturated), so the texture keeps its shapes and features (lips, brows, seams, trims)
without the noise, the pores and the baked shading."""
import sys, time
import numpy as np
import cv2


def toon_flat(rgb, detail_s=30, detail_r=0.25, wide_s=160, wide_r=0.12, flatten=0.65, sat=1.15, passes=2):
    base = rgb
    for i in range(passes):
        base = cv2.edgePreservingFilter(base, flags=cv2.RECURS_FILTER, sigma_s=detail_s, sigma_r=detail_r)
    wide = base
    for i in range(passes):
        wide = cv2.edgePreservingFilter(wide, flags=cv2.RECURS_FILTER, sigma_s=wide_s, sigma_r=wide_r)
    lb = cv2.cvtColor(base, cv2.COLOR_RGB2LAB).astype(np.float32)
    lw = cv2.cvtColor(wide, cv2.COLOR_RGB2LAB).astype(np.float32)
    out = np.empty_like(lb)
    out[..., 0] = lb[..., 0] * (1.0 - flatten) + lw[..., 0] * flatten
    out[..., 1:] = 128.0 + (lw[..., 1:] - 128.0) * sat
    return cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB)


if __name__ == '__main__':
    from PIL import Image
    src, dst = sys.argv[1], sys.argv[2]
    kw = {}
    for a in sys.argv[3:]:
        k, v = a.split('=')
        kw[k] = float(v) if '.' in v else int(v)
    t = time.time()
    im = Image.open(src)
    rgb = np.array(im.convert('RGB'))
    out = toon_flat(rgb, **kw)
    Image.fromarray(out).save(dst)
    print('%s -> %s (%.1f s)' % (src, dst, time.time() - t))
