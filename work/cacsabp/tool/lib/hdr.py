"""Read a container header (the type-10 chunk) written by the game's / the editor's IoStore writer."""
import struct

def parse_header(data):
    cid, n = struct.unpack_from('<QI', data, 0)
    # find the package id array: int32 n followed by n ids
    for start in range(12, len(data) - 4, 4):
        if struct.unpack_from('<i', data, start)[0] == n and start + 4 + 8 * n + 4 <= len(data):
            ids = list(struct.unpack_from('<%dQ' % n, data, start + 4))
            o = start + 4 + 8 * n
            size = struct.unpack_from('<i', data, o)[0]
            if size >= 32 * n and o + 4 + size <= len(data):
                store = data[o + 4:o + 4 + size]
                entries = {}
                for i in range(n):
                    fp = i * 32
                    sz, ec, bc, lo, pad, ni, off = struct.unpack_from('<QiiIIII', store, fp)
                    imps = []
                    if ni:
                        dp = fp + 24 + off
                        imps = list(struct.unpack_from('<%dQ' % ni, store, dp))
                    entries[ids[i]] = dict(id=ids[i], size=sz, export_count=ec, export_bundle_count=bc, load_order=lo, pad=pad, imports=imps)
                return cid, entries
    raise ValueError('no package id array found')
