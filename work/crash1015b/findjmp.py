import dis2, re, struct, sys
d = dis2.d
text = [s for s in dis2.secs if s[0] == '.text'][0]
name, va, vsz, rp, rs = text
blob = d[rp:rp + rs]
targets = set(int(a, 16) for a in sys.argv[1:])
out = []
# e8/e9 rel32
for op in (b'\xe8', b'\xe9'):
    i = blob.find(op)
    while i >= 0:
        if i + 5 <= len(blob):
            rel = struct.unpack_from('<i', blob, i + 1)[0]
            t = va + i + 5 + rel
            if t in targets: out.append((va + i, t, op.hex()))
        i = blob.find(op, i + 1)
# 0f 8x rel32
i = blob.find(b'\x0f')
while i >= 0:
    if i + 6 <= len(blob) and 0x80 <= blob[i+1] <= 0x8f:
        rel = struct.unpack_from('<i', blob, i + 2)[0]
        t = va + i + 6 + rel
        if t in targets: out.append((va + i, t, 'jcc'))
    i = blob.find(b'\x0f', i + 1)
for a, t, k in out[:60]:
    f = dis2.func_of(a)
    print('%s at %x -> %x in %s' % (k, a, t, ('%x-%x' % f) if f else '?'))
