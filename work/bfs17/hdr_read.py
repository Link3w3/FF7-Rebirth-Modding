"""Radiance .hdr (RGBE, run-length encoded scanlines) -> float32 array (H, W, 3)."""
import numpy as np

def read_hdr(path):
    data = open(path, 'rb').read()
    i = 0
    while True:
        j = data.index(b'\n', i)
        line = data[i:j]
        i = j + 1
        if line.startswith(b'-Y') or line.startswith(b'+Y'):
            parts = line.split()
            H, W = int(parts[1]), int(parts[3])
            flip = line.startswith(b'+Y')
            break
    img = np.zeros((H, W, 4), np.uint8)
    p = i
    for y in range(H):
        if data[p] == 2 and data[p + 1] == 2 and (data[p + 2] << 8 | data[p + 3]) == W:
            p += 4
            for c in range(4):
                x = 0
                row = img[y, :, c]
                while x < W:
                    n = data[p]; p += 1
                    if n > 128:
                        n -= 128
                        row[x:x + n] = data[p]; p += 1
                    else:
                        row[x:x + n] = np.frombuffer(data, np.uint8, n, p); p += n
                    x += n
        else:
            img[y] = np.frombuffer(data, np.uint8, W * 4, p).reshape(W, 4); p += W * 4
    e = img[..., 3].astype(np.int32)
    f = np.where(e > 0, np.ldexp(1.0, e - 136), 0.0).astype(np.float32)
    rgb = img[..., :3].astype(np.float32) * f[..., None]
    return rgb[::-1] if flip else rgb
