"""Which functions of a COFF object (MSVC, /Gy) refer to the given symbols: coffrefs.py <obj> <substring>..."""
import struct, sys, subprocess

def load(path):
    d = open(path, 'rb').read()
    # bigobj or regular
    if d[:4] == b'\x00\x00\xff\xff':
        (sig1, sig2, ver, machine, ts) = struct.unpack_from('<HHHHI', d, 0)
        nsec, ptrsym, nsym = struct.unpack_from('<III', d, 44)
        hdr = 56; symsz = 20; big = True
    else:
        machine, nsec, ts, ptrsym, nsym, opt, ch = struct.unpack_from('<HHIIIHH', d, 0)
        hdr = 20 + opt; symsz = 18; big = False
    strtab = ptrsym + nsym * symsz
    def name8(raw):
        if raw[:4] == b'\0\0\0\0':
            off = struct.unpack_from('<I', raw, 4)[0]
            e = d.index(b'\0', strtab + off)
            return d[strtab + off:e].decode('latin1')
        return raw.rstrip(b'\0').decode('latin1')
    secs = []
    for i in range(nsec):
        o = hdr + i * 40
        nm = d[o:o + 8]
        vsize, vaddr, rawsize, rawptr, relptr, lnptr, nrel, nln, ch = struct.unpack_from('<IIIIIIHHI', d, o + 8)
        if ch & 0x01000000 and nrel == 0xFFFF:   # extended relocs
            nrel = struct.unpack_from('<I', d, relptr)[0]
            relptr += 10; nrel -= 1
        secs.append(dict(relptr=relptr, nrel=nrel, ch=ch))
    syms = []
    i = 0
    while i < nsym:
        o = ptrsym + i * symsz
        raw = d[o:o + 8]
        if big:
            val, sec = struct.unpack_from('<Ii', d, o + 8)
            typ, cls, aux = struct.unpack_from('<HBB', d, o + 16)
        else:
            val, sec = struct.unpack_from('<Ih', d, o + 8)
            typ, cls, aux = struct.unpack_from('<HBB', d, o + 14)
        syms.append((name8(raw), sec, cls, typ, val))
        for _ in range(aux):
            syms.append(None)
        i += 1 + aux
    return d, secs, syms

def main(path, needles):
    d, secs, syms = load(path)
    targets = {i for i, s in enumerate(syms) if s and any(n in s[0] for n in needles)}
    owner = {}
    for i, s in enumerate(syms):
        if s and s[1] > 0 and s[2] in (2, 3) and s[3] == 0x20:   # function symbols (type 0x20) defined in a section
            owner.setdefault(s[1], []).append(s[0])
    hits = {}
    for si, sec in enumerate(secs, 1):
        for r in range(sec['nrel']):
            va, symi, typ = struct.unpack_from('<IIH', d, sec['relptr'] + r * 10)
            if symi in targets:
                hits.setdefault(si, 0)
                hits[si] += 1
    names = []
    for si, n in sorted(hits.items()):
        fn = owner.get(si, ['<section %d>' % si])
        names.append((fn, n))
    out = subprocess.run(['llvm-cxxfilt'], input='\n'.join(f[0] for f, n in names), capture_output=True, text=True).stdout.split('\n')
    for (fn, n), dm in zip(names, out):
        print('%3d refs  %s\n          %s' % (n, fn[0], dm))

main(sys.argv[1], sys.argv[2:])
