"""numpy BC3 (DXT5) decoder."""
import numpy as np
def decode_bc3(data, w, h):
    bw, bh = (w + 3) // 4, (h + 3) // 4
    blk = np.frombuffer(data, dtype=np.uint8, count=bw * bh * 16).reshape(bh * bw, 16)
    # alpha
    a0 = blk[:, 0].astype(np.int32); a1 = blk[:, 1].astype(np.int32)
    abits = np.zeros(len(blk), dtype=np.uint64)
    for i in range(6):
        abits |= blk[:, 2 + i].astype(np.uint64) << np.uint64(8 * i)
    aidx = np.stack([((abits >> np.uint64(3 * k)) & np.uint64(7)).astype(np.int32) for k in range(16)], 1)
    pal = np.zeros((len(blk), 8), dtype=np.int32)
    pal[:, 0] = a0; pal[:, 1] = a1
    big = a0 > a1
    for k in range(1, 7):
        pal[:, 1 + k] = np.where(big, ((7 - k) * a0 + k * a1) // 7, 0)
    for k in range(1, 5):
        pal[:, 1 + k] = np.where(big, pal[:, 1 + k], ((5 - k) * a0 + k * a1) // 5)
    pal[:, 6] = np.where(big, pal[:, 6], 0); pal[:, 7] = np.where(big, pal[:, 7], 255)
    alpha = np.take_along_axis(pal, aidx, 1)
    # color
    c0 = blk[:, 8].astype(np.int32) | (blk[:, 9].astype(np.int32) << 8)
    c1 = blk[:, 10].astype(np.int32) | (blk[:, 11].astype(np.int32) << 8)
    def rgb(c):
        r = (c >> 11) & 31; g = (c >> 5) & 63; b = c & 31
        return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], 1)
    p0, p1 = rgb(c0), rgb(c1)
    cols = np.stack([p0, p1, (2 * p0 + p1) // 3, (p0 + 2 * p1) // 3], 1)   # BC3 always 4-color mode
    cbits = blk[:, 12].astype(np.uint32) | (blk[:, 13].astype(np.uint32) << 8) | (blk[:, 14].astype(np.uint32) << 16) | (blk[:, 15].astype(np.uint32) << 24)
    cidx = np.stack([((cbits >> np.uint32(2 * k)) & np.uint32(3)).astype(np.int32) for k in range(16)], 1)
    color = np.take_along_axis(cols, cidx[:, :, None].repeat(3, 2), 1)
    px = np.concatenate([color, alpha[:, :, None]], 2).astype(np.uint8)   # (blocks, 16, 4)
    img = px.reshape(bh, bw, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(bh * 4, bw * 4, 4)
    return img[:h, :w]
