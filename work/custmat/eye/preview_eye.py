"""CPU preview of anime_eye.hlsl's math on a sphere eyeball (UE axes: Z up; the eye looks along +X; UV planar on its
front: u to the eye's right (-Y), v down (-Z); the iris disc of UV radius 0.25 at the centre)."""
import numpy as np
from PIL import Image

def normalize(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)

def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)

def iris_tex(uv):
    # synthetic iris: green with radial streaks, a vertical slit pupil, dark rim; a white marker at the top (v small)
    c = uv - 0.5
    rr = np.linalg.norm(c, axis=-1) * 2
    ang = np.arctan2(c[..., 1], c[..., 0])
    base = np.stack([0.15 + 0.1 * np.sin(ang * 24), 0.55 + 0.15 * np.sin(ang * 24), 0.45 + 0.1 * np.cos(ang * 13)], -1)
    pupil = (np.abs(c[..., 0]) < 0.06 * np.sqrt(np.clip(1 - (c[..., 1] / 0.42) ** 2, 0, 1))) & (rr < 0.85)
    base[pupil] = 0.02
    base[rr > 0.92] *= 0.3
    marker = (np.abs(c[..., 0]) < 0.04) & (c[..., 1] < -0.38) & (c[..., 1] > -0.46)
    base[marker] = [1.0, 0.2, 0.2]
    return np.clip(base, 0, 1)

def sclera_tex(uv):
    return np.full(uv.shape[:-1] + (3,), 0.78)

P = dict(RefractionIndex=1.49, IrisDepth=1.0, IrisRimDarken=0.35, LidShadow=0.3, LidSoftness=0.04, ShadowIntensity=0.4,
         MidIntensity=0.8, ShadowTint=np.array([0.75, 0.85, 1.1]), HighlightIntensity=0.45, HighlightSize=0.05,
         HighlightX=0.7, HighlightY=0.7)

def shade(cam_dir, size=512, gaze_tilt=(0.0, 0.0), ea=0.2, brightness=0.7):
    """cam_dir: direction from the eye to the camera (orthographic)."""
    ys, zs = np.meshgrid(np.linspace(1.1, -1.1, size), np.linspace(1.1, -1.1, size))
    # screen plane spanned by the camera's right/up; for simplicity the camera looks along -cam_dir with Z up
    V = normalize(np.array(cam_dir, float))
    up = np.array([0, 0, 1.0]) - V * V[2]; up = normalize(up)
    right = np.cross(up, V)
    pts_dir = ys[..., None] * right + zs[..., None] * up
    # ray: origin far along V, direction -V; sphere radius 1 at origin
    o = pts_dir + V * 5
    d = -V
    b = np.sum(o * d, -1); c = np.sum(o * o, -1) - 1
    disc = b * b - c
    hit = disc > 0
    t = -b - np.sqrt(np.maximum(disc, 0))
    X = o + d * t[..., None]
    Nn = normalize(X)
    front = Nn[..., 0] > 0.15
    # planar UV from the front: u = 0.5 + 0.5 * (-y) / 1? The eyeball's front half maps to UV 0..1 at radius 1
    u = 0.5 + 0.5 * (-X[..., 1])
    v = 0.5 + 0.5 * (-X[..., 2])
    UV = np.stack([u, v], -1)
    T = np.zeros_like(Nn); T[..., 1] = -1.0          # +u along -Y
    B = np.zeros_like(Nn); B[..., 2] = -1.0          # +v along -Z
    # orthonormalise against the normal
    T = normalize(T - Nn * np.sum(T * Nn, -1, keepdims=True))
    B = normalize(B - Nn * np.sum(B * Nn, -1, keepdims=True))
    s = np.where(np.sum(np.cross(Nn, T) * B, -1) < 0, -1.0, 1.0)[..., None]
    Vv = np.broadcast_to(V, Nn.shape)
    # gaze normal map: flat (the eye's axis = the mesh normal); optional tilt
    g = normalize(np.broadcast_to(np.array([gaze_tilt[0], gaze_tilt[1], 1.0]), Nn.shape))
    G = g[..., 0:1] * T + g[..., 1:2] * B + g[..., 2:3] * Nn
    Bg = normalize(np.cross(G, T)) * s
    Tg = normalize(np.cross(Bg, G)) * s
    p = UV * 4 - 2
    r2 = np.sum(p * p, -1); r = np.sqrt(r2)
    t0 = np.clip((r - 0.9) * 5, 0, 1); scleraW = t0 * t0 * (3 - 2 * t0)
    nc = normalize(np.concatenate([0.9115 * p, np.ones(p.shape[:-1] + (1,))], -1))
    nw = nc[..., 0:1] * Tg + nc[..., 1:2] * Bg + nc[..., 2:3] * G
    cosI = np.sum(nw * Vv, -1, keepdims=True)
    eta = 1 / P['RefractionIndex']
    k = 1 - eta * eta * (1 - cosI * cosI)
    tr = normalize(eta * (cosI * nw - Vv) - np.sqrt(np.maximum(k, 0)) * nw)
    depth = np.maximum(0.3735 - r2 * 0.2795, 0) * 0.4077 * P['IrisDepth']
    tz = np.sum(tr * G, -1)
    tz = np.where(np.abs(tz) > 1e-4, tz, -1e-4)
    uvi = UV - np.stack([np.sum(tr * Tg, -1), np.sum(tr * Bg, -1)], -1) / tz[..., None] * depth[..., None]
    q = uvi * 4 - 2
    qr = np.linalg.norm(q, axis=-1)
    irisUV = 0.5 + 0.5 * np.clip(qr, 0, 1)[..., None] * q / np.maximum(qr, 1e-4)[..., None]
    iris = iris_tex(irisUV) * (1 - P['IrisRimDarken'] * smoothstep(0.8, 1.0, qr))[..., None]
    col = iris + (sclera_tex(UV) - iris) * scleraW[..., None]
    upd = Nn[..., 2]
    lid = smoothstep(P['LidShadow'] - P['LidSoftness'], P['LidShadow'] + P['LidSoftness'], upd)[..., None]
    band = P['MidIntensity'] + (P['ShadowIntensity'] * P['ShadowTint'] - P['MidIntensity']) * lid
    toon = col * np.clip(col * band, 0, 1)
    upS = normalize(np.array([0, 0, 1.0]) - Vv * Vv[..., 2:3])
    rightS = np.cross(upS, Vv)
    R = 2 * np.sum(nw * Vv, -1, keepdims=True) * nw - Vv     # reflect(-V, n) = -V + 2 dot(n,V) n
    L1 = normalize(Vv + P['HighlightX'] * rightS + P['HighlightY'] * upS)
    L2 = normalize(Vv - 0.7 * P['HighlightX'] * rightS - 0.7 * P['HighlightY'] * upS)
    hs = P['HighlightSize']
    h1 = smoothstep(1 - hs, 1 - hs * 0.5, np.sum(R * L1, -1))
    h2 = smoothstep(1 - hs * 0.3, 1 - hs * 0.15, np.sum(R * L2, -1))
    out = toon + ((h1 + 0.6 * h2) * P['HighlightIntensity'] * (1 - scleraW))[..., None]
    lin = out * brightness / ea                      # on screen, as the game shows it (editor exposure ea)
    img = np.where(hit[..., None] & front[..., None], lin, 0.05)
    disp = np.where(img <= 0.0031308, img * 12.92, 1.055 * np.power(np.clip(img, 0, None), 1 / 2.4) - 0.055)
    return (np.clip(disp, 0, 1) * 255).astype(np.uint8)

views = [((1, 0, 0), 'front'), ((0.8, -0.5, 0.1), 'from the right'), ((0.8, 0.0, 0.5), 'from above')]
tiles = [shade(v, 360) for v, _ in views] + [shade((1, 0, 0), 360, gaze_tilt=(0.0, 0.0)), ]
Image.fromarray(np.concatenate(tiles[:3], 1)).save('preview/eye_views.png')
print('ok')
