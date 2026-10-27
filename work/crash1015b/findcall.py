import dis2, re, struct, sys
d = dis2.d
text = [s for s in dis2.secs if s[0] == '.text'][0]
name, va, vsz, rp, rs = text
blob = d[rp:rp + rs]
targets = set(int(a, 16) for a in sys.argv[1:])
out = []
i = blob.find(b'\xe8')
while i >= 0:
    if i + 5 <= len(blob):
        rel = struct.unpack_from('<i', blob, i + 1)[0]
        t = va + i + 5 + rel
        if t in targets:
            out.append((va + i, t))
    i = blob.find(b'\xe8', i + 1)
for a, t in out[:30]:
    f = dis2.func_of(a)
    print('call at %x -> %x in %s' % (a, t, ('%x-%x' % f) if f else '?'))
