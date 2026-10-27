"""Toonier textures, second way: regions instead of a global palette. The texture is smoothed keeping its edges (domain
transform), cut into superpixels (SLIC, in Lab), neighbouring superpixels of near colours merged (region adjacency graph,
cut at a Lab distance), and each region filled with its own median colour (a touch more saturated), with a little of the
smoothed texture blended back so large shapes keep a hint of their shading."""
import sys, time
import numpy as np
import cv2
from skimage import segmentation, graph


def toon_regions(rgb, seg_px=20, compact=12.0, thresh=9.0, sat=1.12, keep=0.15, sigma_s=40, sigma_r=0.35, mask=None):
    h, w = rgb.shape[:2]
    sm = cv2.edgePreservingFilter(rgb, flags=cv2.RECURS_FILTER, sigma_s=sigma_s, sigma_r=sigma_r)
    sm = cv2.edgePreservingFilter(sm, flags=cv2.RECURS_FILTER, sigma_s=sigma_s // 2, sigma_r=sigma_r)
    lab = cv2.cvtColor(sm, cv2.COLOR_RGB2LAB).astype(np.float32)
    n = max(64, (h * w) // (seg_px * seg_px))
    labels = segmentation.slic(lab, n_segments=n, compactness=compact, channel_axis=-1, convert2lab=False, start_label=0,
                               enforce_connectivity=True)
    rag = graph.rag_mean_color(lab, labels, mode='distance')
    merged = graph.cut_threshold(labels, rag, thresh)
    # each region: its median Lab colour
    flat_l = merged.ravel()
    order = np.argsort(flat_l, kind='stable')
    lab_flat = lab.reshape(-1, 3)[order]
    bounds = np.flatnonzero(np.diff(flat_l[order])) + 1
    starts = np.r_[0, bounds]
    ends = np.r_[bounds, flat_l.size]
    ids = flat_l[order][starts]
    med = np.zeros((merged.max() + 1, 3), np.float32)
    for i, s, e in zip(ids, starts, ends):
        med[i] = np.median(lab_flat[s:e], axis=0)
    med[:, 1:] = 128.0 + (med[:, 1:] - 128.0) * sat
    out_lab = med[merged]
    out_lab = out_lab * (1.0 - keep) + lab * keep
    out = cv2.cvtColor(np.clip(out_lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB)
    return out, merged


if __name__ == '__main__':
    from PIL import Image
    src, dst = sys.argv[1], sys.argv[2]
    kw = {}
    for a in sys.argv[3:]:
        k, v = a.split('=')
        kw[k] = float(v) if '.' in v else int(v)
    t = time.time()
    im = Image.open(src)
    alpha = im.getchannel('A') if im.mode == 'RGBA' else None
    rgb = np.array(im.convert('RGB'))
    out, merged = toon_regions(rgb, **kw)
    o = Image.fromarray(out)
    o.save(dst)
    print('%s -> %s: %d regions (%.1f s)' % (src, dst, len(np.unique(merged)), time.time() - t))
