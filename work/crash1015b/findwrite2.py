import dis2, re, struct, sys
d = dis2.d
text = [s for s in dis2.secs if s[0] == '.text'][0]
name, va, vsz, rp, rs = text
blob = d[rp:rp + rs]
targets = set(int(a, 16) for a in sys.argv[1:])
# any rip-relative operand: scan for modrm with rip (mod=00, rm=101) in common encodings; brute-force: every position i where disp32 at i+k gives target
hits = []
for k in range(2, 8):
    pass
# brute force: for each offset i, compute rva of next-instruction assuming instruction ends at i+4+t for t in 0..4 (imm bytes)
import array
for i in range(0, len(blob) - 4):
    disp = struct.unpack_from('<i', blob, i)[0]
    for tail in (0, 1, 4):
        t = va + i + 4 + tail + disp
        if t in targets:
            hits.append((va + i, t, tail))
for a, t, tail in hits[:80]:
    f = dis2.func_of(a)
    print('%x (disp at) -> %x tail %d in %s' % (a, t, tail, ('%x-%x' % f) if f else '?'))
