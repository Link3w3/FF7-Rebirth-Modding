import numpy as np
def morton_xy(n_bits):
    """index -> (x, y) for a 2^n x 2^n Morton tile (x in even bits, y in odd bits)."""
    size = 1 << (2 * n_bits)
    idx = np.arange(size)
    x = np.zeros(size, dtype=np.int64); y = np.zeros(size, dtype=np.int64)
    for b in range(n_bits):
        x |= ((idx >> (2 * b)) & 1) << b
        y |= ((idx >> (2 * b + 1)) & 1) << b
    return x, y
def deswizzle(blocks, bw, bh, tile_bits, xfirst=True):
    """blocks (bw*bh, 16) stored tile by tile (tiles row-major), Morton inside each 2^t x 2^t tile -> row-major."""
    t = 1 << tile_bits
    tx, ty = morton_xy(tile_bits)
    if not xfirst: tx, ty = ty, tx
    out = np.zeros_like(blocks)
    tiles_x = bw // t
    n = 0
    for tile in range(bw * bh // (t * t)):
        ox = (tile % tiles_x) * t; oy = (tile // tiles_x) * t
        dst = (oy + ty) * bw + (ox + tx)
        out[dst] = blocks[n:n + t * t]
        n += t * t
    return out
