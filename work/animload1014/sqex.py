import sys, struct
sys.path.insert(0, '/work/run1013/tools')
from pkg426 import Pkg, read_props
def analyze(path, verbose=True):
    d = open(path, 'rb').read()
    P = Pkg(d)
    out = {}
    for e in P.exports:
        cls = P.import_path(e['cls']) if e['cls'] < 0 else ''
        if not cls.endswith('AnimSequence'): continue
        off, size = e['offset'], e['size']
        props = []
        p = read_props(P, d, off, off + size, 0, props)
        q = p
        hasguid = struct.unpack_from('<i', d, q)[0]; q += 4
        if hasguid: q += 16
        skelguid = d[q:q+16]; q += 16
        PM_START = off
        fcs, sz, idk, pad = struct.unpack_from('<IIHH', d, q); q += 12
        q += pad
        PM_POINTER1 = q
        off1, num, mx = struct.unpack_from('<Qii', d, q); q += 16
        PM_POINTER2 = q
        off2, num2, mx2 = struct.unpack_from('<Qii', d, q); q += 16
        ddc = d[q:q+8]; q += 8; sig = d[q:q+8]; q += 8
        data = q
        # ACL clip header, if present
        acl = None
        if d[data+8:data+12] == b'\x10\xac\x10\xac':
            acl = struct.unpack_from('<I', d, data)[0]
        # frozen content size says where the stream ends (relative to PM_POINTER1)
        stream_end = PM_POINTER1 + fcs
        # after stream: unk1..3 then strip flags (2 bytes) then RawAnimationData count
        r = stream_end
        unk = struct.unpack_from('<iii', d, r); r += 12
        strip = d[r:r+2]; r += 2
        ntracks = struct.unpack_from('<i', d, r)[0]
        out = dict(name=e['name'], flags=P.flags, frozen=fcs, size=sz, idk=idk, pad=pad, off1=off1, num=num, max=mx, off2=off2, num2=num2,
                   sig=sig, acl_size=acl, data_rel=data - PM_POINTER1, unk=unk, strip=strip.hex(), ntracks=ntracks, export_size=size)
        if verbose:
            print(path.split('/')[-1], out)
    return out
if __name__ == '__main__':
    for f in sys.argv[1:]:
        analyze(f)
