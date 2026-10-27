import numpy as np
INVERT = [14,14,14,14,14,14,13,13, 13,13,13,13,12,12,12,12,
          12,12,11,11,11,11,11,11, 10,10,10,10,10,10,10, 9,
           9, 9, 9, 9, 9, 8, 8, 8,  8, 8, 8, 7, 6, 6, 5, 4,
           4, 4, 3, 3, 3, 2, 2, 2,  2, 1, 1, 1, 1, 1, 1, 1,
           1, 1]
assert len(INVERT) == 66
def scale(sf):
    return np.sqrt(128) * 2.0 ** ((sf - 63) * 53 / 128)
def rng(r):
    if r == 0: return 0.0
    if r <= 7: return 2.0 / (2 * r + 1)
    return 2.0 / ((1 << (r - 3)) - 1)
def levels(r):
    """largest |q| at resolution r"""
    if r == 0: return 0
    if r <= 7: return r
    return (1 << (r - 4)) - 1
