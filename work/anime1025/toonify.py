"""Toonier textures: a colour texture flattened into a few clean tones (mean-shift smoothing keeps the edges and drops the
fine detail, then a palette of K colours picked in Lab space, the speckles cleaned up, the colours a touch more saturated);
a normal map softened (blurred, flattened) so the toon light's step makes clean shadow shapes."""
import sys, time
import numpy as np
import cv2
from sklearn.cluster import MiniBatchKMeans


def toon_color(rgb, k=16, sp=10, sr=16, sat=1.15, clean=5, levels=2, seed=1):
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    sm = cv2.pyrMeanShiftFiltering(bgr, sp, sr, maxLevel=levels)
    sm = cv2.medianBlur(sm, clean)
    lab = cv2.cvtColor(sm, cv2.COLOR_BGR2LAB)
    flat = lab.reshape(-1, 3).astype(np.float32)
    rng = np.random.default_rng(seed)
    pick = flat[rng.choice(flat.shape[0], size=min(200000, flat.shape[0]), replace=False)]
    km = MiniBatchKMeans(n_clusters=k, random_state=seed, n_init=3, batch_size=8192).fit(pick)
    labels = km.predict(flat).reshape(lab.shape[:2]).astype(np.uint8)
    labels = cv2.medianBlur(labels, clean)          # the small islands of a label go to their neighbours'
    centers = km.cluster_centers_.copy()
    centers[:, 1:] = 128.0 + (centers[:, 1:] - 128.0) * sat
    centers = np.clip(centers, 0, 255).astype(np.uint8)
    out_lab = centers[labels]
    out = cv2.cvtColor(out_lab, cv2.COLOR_LAB2RGB)
    return out, labels, centers


def soft_normal(rg, sigma=4.0, flatten=0.6):
    """rg: uint8 (H, W, 2) BC5 normal x/y. Returns uint8 RGB (x, y, z) softened."""
    xy = rg.astype(np.float32) / 127.5 - 1.0
    xy = cv2.GaussianBlur(xy, (0, 0), sigma) * flatten
    z = np.sqrt(np.clip(1.0 - (xy ** 2).sum(-1), 0.0, 1.0))
    n = np.dstack([xy, z])
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-6
    return np.clip((n * 0.5 + 0.5) * 255.0 + 0.5, 0, 255).astype(np.uint8)


if __name__ == '__main__':
    from PIL import Image
    src, dst = sys.argv[1], sys.argv[2]
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    t = time.time()
    im = np.array(Image.open(src).convert('RGB'))
    out, _, _ = toon_color(im, k=k)
    Image.fromarray(out).save(dst)
    print('%s -> %s (%.1f s)' % (src, dst, time.time() - t))
