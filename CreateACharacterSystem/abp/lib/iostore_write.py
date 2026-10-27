"""Write a small UE4.26 (FF7 Rebirth) IoStore container: .utoc + .ucas, uncompressed blocks, indexed."""
import struct, hashlib, os, sys
sys.path.insert(0, '/work/cs')
from cityhash import CityHash64

BLOCK = 65536

def fstring(s):
    b = s.encode('ascii') + b'\0'
    return struct.pack('<i', len(b)) + b

def container_id_from_name(name):
    return CityHash64(name.lower().encode('utf-16-le'))

def package_id(package_name):
    return CityHash64(package_name.lower().encode('utf-16-le'))

def container_header(container_id, packages):
    """packages: list of dict(id, size, export_count, export_bundle_count, imports=[ids], load_order)"""
    out = bytearray()
    out += struct.pack('<QII', container_id, len(packages), 0)
    out += struct.pack('<i', 0)                                   # Names (empty)
    out += struct.pack('<i', 8) + struct.pack('<Q', 0xC1640000)   # NameHashes: hash algorithm id only
    out += struct.pack('<i', len(packages)) + b''.join(struct.pack('<Q', p['id']) for p in packages)
    entries = bytearray()
    tail = bytearray()
    n = len(packages)
    for i, p in enumerate(packages):
        imports = p.get('imports', [])
        field_pos = i * 32 + 24
        if imports:
            data_pos = n * 32 + len(tail)
            off = data_pos - field_pos
            tail += b''.join(struct.pack('<Q', x) for x in imports)
        else:
            off = 0
        entries += struct.pack('<QiiIIII', p['size'], p['export_count'], p['export_bundle_count'], p.get('load_order', 0), 0xFFFFFFFF, len(imports), off)
    store = bytes(entries + tail)
    out += struct.pack('<i', len(store)) + store
    out += struct.pack('<i', 0)   # CulturePackageMap (empty TMap)
    out += struct.pack('<i', 0)   # PackageRedirects (empty)
    return bytes(out)

def directory_index(mount, files):
    """files: list of (relative path under mount, chunk index)"""
    strings = []
    def sidx(s):
        if s not in strings: strings.append(s)
        return strings.index(s)
    dirs = [[0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF]]   # root
    fents = []
    def child(di, name):
        c = dirs[di][1]
        last = None
        while c != 0xFFFFFFFF:
            if dirs[c][0] == sidx(name): return c
            last = c; c = dirs[c][2]
        dirs.append([sidx(name), 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF])
        ni = len(dirs) - 1
        if last is None: dirs[di][1] = ni
        else: dirs[last][2] = ni
        return ni
    for path, chunk in files:
        parts = path.split('/')
        di = 0
        for part in parts[:-1]:
            di = child(di, part)
        fents.append([sidx(parts[-1]), 0xFFFFFFFF, chunk])
        fi = len(fents) - 1
        f = dirs[di][3]
        if f == 0xFFFFFFFF: dirs[di][3] = fi
        else:
            while fents[f][1] != 0xFFFFFFFF: f = fents[f][1]
            fents[f][1] = fi
    out = bytearray(fstring(mount))
    out += struct.pack('<i', len(dirs)) + b''.join(struct.pack('<IIII', *d) for d in dirs)
    out += struct.pack('<i', len(fents)) + b''.join(struct.pack('<III', *f) for f in fents)
    out += struct.pack('<i', len(strings)) + b''.join(fstring(s) for s in strings)
    return bytes(out)

def write_container(base_path, container_name, chunks, mount='../../../End/Content/'):
    """chunks: list of dict(id64, type, data, path or None). Chunk 0 should be the container header."""
    cid = container_id_from_name(container_name)
    ucas = bytearray()
    blocks = []
    offlen = []
    upos = 0
    for c in chunks:
        data = c['data']
        offlen.append((upos, len(data)))
        for i in range(0, max(len(data), 1), BLOCK):
            piece = data[i:i + BLOCK]
            if not piece: break
            pos = len(ucas)
            ucas += piece
            while len(ucas) % 16: ucas.append(0)
            blocks.append((pos, len(piece), len(piece), 0))
        upos += ((len(data) + BLOCK - 1) // BLOCK) * BLOCK
    files = [(c['path'], i) for i, c in enumerate(chunks) if c.get('path')]
    dindex = directory_index(mount, files)
    toc = bytearray()
    toc += b'-==--==--==--==-'
    toc += struct.pack('<BBH', 2, 0, 0)
    # Same layout as the working mods made for this game: uncompressed, indexed, one partition.
    toc += struct.pack('<IIIIIIIII', 144, len(chunks), len(blocks), 12, 0, 32, BLOCK, len(dindex), 1)
    toc += struct.pack('<Q', cid)
    toc += b'\0' * 16                 # encryption key guid
    toc += bytes([8])                 # Indexed
    toc += b'\0' * 7
    toc += struct.pack('<Q', 0xFFFFFFFFFFFFFFFF)   # partition size
    toc += b'\0' * (144 - len(toc))
    for c in chunks:
        toc += struct.pack('<QHBB', c['id64'], 0, 0, c['type'])
    for off, ln in offlen:
        toc += off.to_bytes(5, 'big') + ln.to_bytes(5, 'big')
    for pos, cs, us, m in blocks:
        toc += pos.to_bytes(5, 'little') + cs.to_bytes(3, 'little') + us.to_bytes(3, 'little') + bytes([m])
    toc += dindex
    for c in chunks:
        toc += hashlib.sha1(c['data']).digest() + b'\0' * 12 + bytes([0])
    open(base_path + '.utoc', 'wb').write(toc)
    open(base_path + '.ucas', 'wb').write(ucas)
    return cid
