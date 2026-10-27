"""A small z-buffer rasterizer (numpy) for checking renders: orthographic, per-pixel depth, flat shading."""
import numpy as np

def view_matrix(yaw_deg, pitch_deg):
    """Camera looking at the model from yaw (0 = from +X, the front) and pitch (up positive): rows = screen x, screen y, toward camera"""
    y, p = np.radians(yaw_deg), np.radians(pitch_deg)
    fwd = np.array([np.cos(p) * np.cos(y), np.cos(p) * np.sin(y), np.sin(p)])   # from target toward camera
    up0 = np.array([0, 0, 1.0])
    right = np.cross(up0, fwd); right /= np.linalg.norm(right) + 1e-12
    up = np.cross(fwd, right)
    return np.stack([right, up, fwd])

def raster(pos, tri, cols, M, box, W=900):
    (x0, x1), (y0, y1) = box
    H = int(W * (y1 - y0) / (x1 - x0))
    P = pos @ M.T
    sx = (P[:, 0] - x0) / (x1 - x0) * (W - 1)
    sy = (y1 - P[:, 1]) / (y1 - y0) * (H - 1)
    sz = P[:, 2]
    img = np.ones((H, W, 3))
    zb = np.full((H, W), -np.inf)
    v = P[tri]
    n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    shade = 0.3 + 0.7 * np.abs(n @ np.array([0.3, 0.5, 0.8]) / np.linalg.norm([0.3, 0.5, 0.8]))
    X, Y, Z = sx[tri], sy[tri], sz[tri]
    xmin = np.clip(np.floor(X.min(1)).astype(int), 0, W - 1); xmax = np.clip(np.ceil(X.max(1)).astype(int), 0, W - 1)
    ymin = np.clip(np.floor(Y.min(1)).astype(int), 0, H - 1); ymax = np.clip(np.ceil(Y.max(1)).astype(int), 0, H - 1)
    vis = (X.max(1) >= 0) & (X.min(1) < W) & (Y.max(1) >= 0) & (Y.min(1) < H)
    for t in np.nonzero(vis)[0]:
        xs = np.arange(xmin[t], xmax[t] + 1); ys = np.arange(ymin[t], ymax[t] + 1)
        if len(xs) == 0 or len(ys) == 0:
            continue
        gx, gy = np.meshgrid(xs + 0.5, ys + 0.5)
        (ax, bx, cx), (ay, by, cy) = X[t], Y[t]
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
        l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
        l3 = 1 - l1 - l2
        m = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not m.any():
            continue
        z = l1 * Z[t, 0] + l2 * Z[t, 1] + l3 * Z[t, 2]
        iy, ix = (gy - 0.5).astype(int), (gx - 0.5).astype(int)
        sel = m & (z > zb[iy, ix])
        zb[iy[sel], ix[sel]] = z[sel]
        img[iy[sel], ix[sel]] = cols[t] * shade[t]
    return np.clip(img, 0, 1)


def raster_tex(pos, tri, cols, M, box, W=900, uv=None, textured=None, cov=None, color=None, thresh=0.5):
    """raster() with alpha-tested textured triangles: uv (per vertex, V x 2), textured (per triangle bool), cov (H x W
    coverage 0..1), color (H x W x 3, display colours). Pixels whose coverage is under thresh are not drawn."""
    (x0, x1), (y0, y1) = box
    H = int(W * (y1 - y0) / (x1 - x0))
    P = pos @ M.T
    sx = (P[:, 0] - x0) / (x1 - x0) * (W - 1)
    sy = (y1 - P[:, 1]) / (y1 - y0) * (H - 1)
    sz = P[:, 2]
    img = np.ones((H, W, 3))
    zb = np.full((H, W), -np.inf)
    v = P[tri]
    n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    L = np.array([0.3, 0.5, 0.8]); L /= np.linalg.norm(L)
    shade = 0.35 + 0.65 * np.abs(n @ L)
    X, Y, Z = sx[tri], sy[tri], sz[tri]
    xmin = np.clip(np.floor(X.min(1)).astype(int), 0, W - 1); xmax = np.clip(np.ceil(X.max(1)).astype(int), 0, W - 1)
    ymin = np.clip(np.floor(Y.min(1)).astype(int), 0, H - 1); ymax = np.clip(np.ceil(Y.max(1)).astype(int), 0, H - 1)
    vis = (X.max(1) >= 0) & (X.min(1) < W) & (Y.max(1) >= 0) & (Y.min(1) < H)
    if cov is not None:
        TH, TW = cov.shape
    for t in np.nonzero(vis)[0]:
        xs = np.arange(xmin[t], xmax[t] + 1); ys = np.arange(ymin[t], ymax[t] + 1)
        if len(xs) == 0 or len(ys) == 0:
            continue
        gx, gy = np.meshgrid(xs + 0.5, ys + 0.5)
        (ax, bx, cx), (ay, by, cy) = X[t], Y[t]
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
        l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
        l3 = 1 - l1 - l2
        m = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not m.any():
            continue
        z = l1 * Z[t, 0] + l2 * Z[t, 1] + l3 * Z[t, 2]
        iy, ix = (gy - 0.5).astype(int), (gx - 0.5).astype(int)
        sel = m & (z > zb[iy, ix])
        if textured is not None and textured[t]:
            a, b, c = tri[t]
            u = l1 * uv[a, 0] + l2 * uv[b, 0] + l3 * uv[c, 0]
            w = l1 * uv[a, 1] + l2 * uv[b, 1] + l3 * uv[c, 1]
            tu = np.clip(((u % 1.0) * TW).astype(int), 0, TW - 1)
            tv = np.clip(((w % 1.0) * TH).astype(int), 0, TH - 1)
            sel &= cov[tv, tu] >= thresh
            if not sel.any():
                continue
            zb[iy[sel], ix[sel]] = z[sel]
            img[iy[sel], ix[sel]] = color[tv[sel], tu[sel]] * (0.55 + 0.45 * shade[t])
        else:
            zb[iy[sel], ix[sel]] = z[sel]
            img[iy[sel], ix[sel]] = cols[t] * shade[t]
    return np.clip(img, 0, 1)


def raster_ids(pos, tri, M, box, W=600, uv=None, textured=None, cov=None, thresh=0.5):
    """The visible triangle per pixel (-1: none), alpha-tested as raster_tex."""
    (x0, x1), (y0, y1) = box
    H = int(W * (y1 - y0) / (x1 - x0))
    P = pos @ M.T
    sx = (P[:, 0] - x0) / (x1 - x0) * (W - 1)
    sy = (y1 - P[:, 1]) / (y1 - y0) * (H - 1)
    sz = P[:, 2]
    ids = np.full((H, W), -1, np.int64)
    zb = np.full((H, W), -np.inf)
    X, Y, Z = sx[tri], sy[tri], sz[tri]
    xmin = np.clip(np.floor(X.min(1)).astype(int), 0, W - 1); xmax = np.clip(np.ceil(X.max(1)).astype(int), 0, W - 1)
    ymin = np.clip(np.floor(Y.min(1)).astype(int), 0, H - 1); ymax = np.clip(np.ceil(Y.max(1)).astype(int), 0, H - 1)
    vis = (X.max(1) >= 0) & (X.min(1) < W) & (Y.max(1) >= 0) & (Y.min(1) < H)
    if cov is not None:
        TH, TW = cov.shape
    for t in np.nonzero(vis)[0]:
        xs = np.arange(xmin[t], xmax[t] + 1); ys = np.arange(ymin[t], ymax[t] + 1)
        if len(xs) == 0 or len(ys) == 0:
            continue
        gx, gy = np.meshgrid(xs + 0.5, ys + 0.5)
        (ax, bx, cx), (ay, by, cy) = X[t], Y[t]
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
        l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
        l3 = 1 - l1 - l2
        m = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not m.any():
            continue
        z = l1 * Z[t, 0] + l2 * Z[t, 1] + l3 * Z[t, 2]
        iy, ix = (gy - 0.5).astype(int), (gx - 0.5).astype(int)
        sel = m & (z > zb[iy, ix])
        if textured is not None and textured[t]:
            a, b, c = tri[t]
            u = l1 * uv[a, 0] + l2 * uv[b, 0] + l3 * uv[c, 0]
            w = l1 * uv[a, 1] + l2 * uv[b, 1] + l3 * uv[c, 1]
            tu = np.clip(((u % 1.0) * TW).astype(int), 0, TW - 1)
            tv = np.clip(((w % 1.0) * TH).astype(int), 0, TH - 1)
            sel &= cov[tv, tu] >= thresh
        zb[iy[sel], ix[sel]] = z[sel]
        ids[iy[sel], ix[sel]] = t
    return ids


def raster_multi(pos, tri, M, box, W, uv, tex_of_tri, textures, flat_cols, light=(0.3, 0.5, 0.8)):
    """Each triangle drawn with its texture (tex_of_tri: index into textures, -1: its flat colour), sampled at uv
    (per vertex, image convention: v down), nearest texel, wrapped."""
    (x0, x1), (y0, y1) = box
    H = int(W * (y1 - y0) / (x1 - x0))
    P = pos @ M.T
    sx = (P[:, 0] - x0) / (x1 - x0) * (W - 1)
    sy = (y1 - P[:, 1]) / (y1 - y0) * (H - 1)
    sz = P[:, 2]
    img = np.ones((H, W, 3)); zb = np.full((H, W), -np.inf)
    v = P[tri]
    n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    L = np.array(light); L /= np.linalg.norm(L)
    shade = 0.45 + 0.55 * np.abs(n @ L)
    X, Y, Z = sx[tri], sy[tri], sz[tri]
    xmin = np.clip(np.floor(X.min(1)).astype(int), 0, W - 1); xmax = np.clip(np.ceil(X.max(1)).astype(int), 0, W - 1)
    ymin = np.clip(np.floor(Y.min(1)).astype(int), 0, H - 1); ymax = np.clip(np.ceil(Y.max(1)).astype(int), 0, H - 1)
    vis = (X.max(1) >= 0) & (X.min(1) < W) & (Y.max(1) >= 0) & (Y.min(1) < H)
    for t in np.nonzero(vis)[0]:
        xs = np.arange(xmin[t], xmax[t] + 1); ys = np.arange(ymin[t], ymax[t] + 1)
        if len(xs) == 0 or len(ys) == 0:
            continue
        gx, gy = np.meshgrid(xs + 0.5, ys + 0.5)
        (ax, bx, cx), (ay, by, cy) = X[t], Y[t]
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
        l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
        l3 = 1 - l1 - l2
        m = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not m.any():
            continue
        z = l1 * Z[t, 0] + l2 * Z[t, 1] + l3 * Z[t, 2]
        iy, ix = (gy - 0.5).astype(int), (gx - 0.5).astype(int)
        sel = m & (z > zb[iy, ix])
        if not sel.any():
            continue
        zb[iy[sel], ix[sel]] = z[sel]
        k = tex_of_tri[t]
        if k >= 0:
            T = textures[k]; TH, TW = T.shape[:2]
            a, b, c = tri[t]
            u = (l1 * uv[a, 0] + l2 * uv[b, 0] + l3 * uv[c, 0])[sel]
            w = (l1 * uv[a, 1] + l2 * uv[b, 1] + l3 * uv[c, 1])[sel]
            tu = np.clip(((u % 1.0) * TW).astype(int), 0, TW - 1); tv = np.clip(((w % 1.0) * TH).astype(int), 0, TH - 1)
            img[iy[sel], ix[sel]] = T[tv, tu, :3] * shade[t]
        else:
            img[iy[sel], ix[sel]] = flat_cols[t] * shade[t]
    return np.clip(img, 0, 1)
