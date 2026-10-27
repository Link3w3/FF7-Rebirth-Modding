"""Reads a UE4.26 pak (v11) index; lists files and extracts entries' raw stored data.
   pakidx.py list <pak> [regex]
   pakidx.py raw <pak> <out dir> <regex>   -> <out dir>/<name>.raw + <name>.json (method, blocks, sizes)"""
import struct, sys, os, re, json

def fstring(b, o):
    n = struct.unpack_from('<i', b, o)[0]; o += 4
    if n == 0: return '', o
    if n < 0:
        s = b[o:o - 2 * n].decode('utf-16-le').rstrip('\0'); o += -2 * n
    else:
        s = b[o:o + n].decode('latin-1').rstrip('\0'); o += n
    return s, o

def read_index(path):
    size = os.path.getsize(path)
    f = open(path, 'rb')
    f.seek(size - 4096); t = f.read()
    i = t.rfind(b'\xe1\x12\x6f\x5a')
    magic, ver, idx_off, idx_size = struct.unpack_from('<IIqq', t, i)
    methods = []
    mo = i + 4 + 4 + 8 + 8 + 20
    for k in range(5):
        nm = t[mo + 32 * k: mo + 32 * k + 32].split(b'\0')[0].decode()
        methods.append(nm)
    f.seek(idx_off); b = f.read(idx_size)
    mount, o = fstring(b, 0)
    num, = struct.unpack_from('<i', b, o); o += 4
    seed, = struct.unpack_from('<Q', b, o); o += 8
    has_phi, = struct.unpack_from('<i', b, o); o += 4
    if has_phi: o += 8 + 8 + 20
    has_fdi, = struct.unpack_from('<i', b, o); o += 4
    fdi_off = fdi_size = None
    if has_fdi:
        fdi_off, fdi_size = struct.unpack_from('<qq', b, o); o += 16 + 20
    enc_size, = struct.unpack_from('<i', b, o); o += 4
    enc = b[o:o + enc_size]; o += enc_size
    nfiles, = struct.unpack_from('<i', b, o); o += 4
    f.seek(fdi_off); fd = f.read(fdi_size)
    files = {}
    p = 0
    ndirs, = struct.unpack_from('<i', fd, p); p += 4
    for _ in range(ndirs):
        d, p = fstring(fd, p)
        nf, = struct.unpack_from('<i', fd, p); p += 4
        for _ in range(nf):
            fn, p = fstring(fd, p)
            eo, = struct.unpack_from('<i', fd, p); p += 4
            files[mount + d + fn] = eo
    return dict(path=path, mount=mount, enc=enc, files=files, methods=methods)

def decode(enc, eo):
    v, = struct.unpack_from('<I', enc, eo); p = eo + 4
    bsz = (v & 0x3f)
    if bsz == 0x3f:
        bsz, = struct.unpack_from('<I', enc, p); p += 4
    else:
        bsz <<= 11
    nblocks = (v >> 6) & 0xffff
    encrypted = (v >> 22) & 1
    method = (v >> 23) & 0x3f
    off32 = (v >> 31) & 1; usz32 = (v >> 30) & 1; sz32 = (v >> 29) & 1
    if off32: off, = struct.unpack_from('<I', enc, p); p += 4
    else: off, = struct.unpack_from('<Q', enc, p); p += 8
    if usz32: usz, = struct.unpack_from('<I', enc, p); p += 4
    else: usz, = struct.unpack_from('<Q', enc, p); p += 8
    if method:
        if sz32: csz, = struct.unpack_from('<I', enc, p); p += 4
        else: csz, = struct.unpack_from('<Q', enc, p); p += 8
    else:
        csz = usz
    blocks = []
    if method and (nblocks > 1 or encrypted):
        for _ in range(nblocks):
            s, = struct.unpack_from('<I', enc, p); p += 4
            blocks.append(s)
    elif method and nblocks == 1:
        blocks = [csz]
    return dict(offset=off, usize=usz, csize=csz, method=method, nblocks=nblocks, block_size=bsz, blocks=blocks, encrypted=encrypted)

if __name__ == '__main__':
    ix = read_index(sys.argv[2])
    if sys.argv[1] == 'list':
        pat = sys.argv[3] if len(sys.argv) > 3 else '.'
        for k, eo in sorted(ix['files'].items()):
            if re.search(pat, k):
                if eo < 0:
                    print(k, 'non-encoded entry', eo); continue
                e = decode(ix['enc'], eo)
                print(k, e['usize'], e['csize'], ix['methods'][e['method'] - 1] if e['method'] else 'none', e['nblocks'])
    else:
        out = sys.argv[3]; pat = sys.argv[4]
        os.makedirs(out, exist_ok=True)
        f = open(sys.argv[2], 'rb')
        for k, eo in sorted(ix['files'].items()):
            if not re.search(pat, k) or eo < 0: continue
            e = decode(ix['enc'], eo)
            # entry header in the data: FPakEntry serialized before the data (v11: 8+8+8+4+20+[blocks]+1+4 ...)
            f.seek(e['offset'])
            hdr_and = f.read(min(e['csize'] + 4096, e['csize'] + 64 + 16 * max(1, e['nblocks'])))
            name = os.path.basename(k)
            open(os.path.join(out, name + '.raw'), 'wb').write(hdr_and)
            e['methods'] = ix['methods']; e['path'] = k
            json.dump(e, open(os.path.join(out, name + '.json'), 'w'))
            print('raw', k, e)
