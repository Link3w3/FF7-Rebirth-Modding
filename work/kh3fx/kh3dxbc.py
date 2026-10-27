"""DXBC shaders inside KH3 cooked materials: finds every DXBC container in a package, with its program type and the
shader/vertex-factory type names written next to it.

    python3 kh3dxbc.py <material .uasset> [out folder]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, '/work/kh3bnm/src/rebirth_fx']
import kh3bonamik as k   # noqa: E402

PROGRAM = {0: 'ps', 1: 'vs', 2: 'gs', 3: 'hs', 4: 'ds', 5: 'cs'}


def blobs(data):
    out = []
    p = data.find(b'DXBC')
    while p >= 0:
        try:
            ver, total, count = struct.unpack_from('<III', data, p + 20)
            if ver == 1 and 32 < total <= len(data) - p and 0 < count < 32:
                blob = data[p:p + total]
                chunks = {}
                for i in range(count):
                    off = struct.unpack_from('<I', blob, 32 + 4 * i)[0]
                    tag = blob[off:off + 4].decode('latin1')
                    size = struct.unpack_from('<I', blob, off + 4)[0]
                    chunks[tag] = (off + 8, size)
                prog = None
                for tag in ('SHEX', 'SHDR'):
                    if tag in chunks:
                        tok = struct.unpack_from('<I', blob, chunks[tag][0])[0]
                        prog = PROGRAM.get(tok >> 16, '?%d' % (tok >> 16))
                out.append(dict(offset=p, size=total, program=prog, chunks=sorted(chunks), blob=blob))
                p = data.find(b'DXBC', p + total)
                continue
        except struct.error:
            pass
        p = data.find(b'DXBC', p + 4)
    return out


def names_near(pk, data, start, end):
    """FName references (index, number) between start and end that point at shader / vertex factory type names."""
    found = []
    for q in range(max(0, start), min(len(data) - 8, end), 1):
        i, n = struct.unpack_from('<ii', data, q)
        if 0 <= i < len(pk.names) and n == 0:
            s = pk.names[i]
            if s.startswith(('T', 'F')) and ('Policy' in s or 'VertexFactory' in s or 'PS' in s or 'VS' in s):
                found.append((q, s))
    return found


if __name__ == '__main__':
    path = sys.argv[1]
    base = path[:-7] if path.endswith('.uasset') else path
    ua, ue = open(base + '.uasset', 'rb').read(), open(base + '.uexp', 'rb').read()
    pk = k.Package(ua, ue)
    data = pk.data
    bl = blobs(data)
    prev = 0
    out_dir = sys.argv[2] if len(sys.argv) > 2 else None
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    for i, b in enumerate(bl):
        near = names_near(pk, data, prev, b['offset'])
        print('%3d @%7d size %6d %s %s  %s' % (i, b['offset'], b['size'], b['program'], ','.join(b['chunks']),
                                              [s for _, s in near[-4:]]))
        prev = b['offset'] + b['size']
        if out_dir:
            open(os.path.join(out_dir, '%02d_%s_%d.dxbc' % (i, b['program'], b['offset'])), 'wb').write(b['blob'])
