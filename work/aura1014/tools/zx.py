"""Zen package exports sliced in export bundle (serialize) order."""
import struct, sys
sys.path.insert(0, '/work/cs')
from zen import Zen

def load(path):
    d = open(path, 'rb').read()
    z = Zen(d)
    eb = d[z.eb_off:z.graph_off]
    # bundle headers then entries: several bundles possible; headers count = ? (4.26: one header per bundle, entries after all headers)
    # find number of bundles: entries total = 2 * exports
    n_exp = len(z.exports)
    total = 2 * n_exp
    # headers are (first, count); assume headers until their counts sum to total
    headers = []
    o = 0; s = 0
    while s < total:
        first, count = struct.unpack_from('<II', eb, o); o += 8
        headers.append((first, count)); s += count
    ents = [struct.unpack_from('<II', eb, o + 8 * k) for k in range(total)]
    order = []
    for first, count in headers:
        for k in range(first, first + count):
            idx, cmd = ents[k]
            if cmd == 1:
                order.append(idx)
    pos = z.header_end
    spans = {}
    for idx in order:
        size = z.exports[idx]['serial_size']
        spans[idx] = (pos, size)
        pos += size
    z.spans = spans
    z.order = order
    z.data_end = pos
    def exp(i):
        p, s = spans[i]
        return d[p:p + s]
    z.exp = exp
    return z
