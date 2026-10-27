import dis2, re, struct, sys
d = dis2.d
text = [s for s in dis2.secs if s[0] == '.text'][0]
name, va, vsz, rp, rs = text
blob = d[rp:rp + rs]
targets = set(int(a, 16) for a in sys.argv[1:])
pat = re.compile(rb'[\x48\x4c][\x8d\x8b\x89][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]', re.S)
hits = []
for m in pat.finditer(blob):
    i = m.start()
    disp = struct.unpack_from('<i', blob, i + 3)[0]
    rva = va + i + 7 + disp
    if rva in targets:
        hits.append((va + i, rva))
for h, t in hits[:40]:
    f = dis2.func_of(h)
    print('%x -> %x  in function %s' % (h, t, ('%x-%x' % f) if f else '?'))
