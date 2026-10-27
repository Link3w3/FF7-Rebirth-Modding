import dis2, re, struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
md = Cs(CS_ARCH_X86, CS_MODE_64)
d = dis2.d
text = [s for s in dis2.secs if s[0] == '.text'][0]
name, va, vsz, rp, rs = text
blob = d[rp:rp + rs]
disp = int(sys.argv[1], 16)
needle = struct.pack('<I', disp)
hits = []
i = blob.find(needle)
while i >= 0:
    # try decoding instructions that start 2-4 bytes before the displacement
    for back in (2, 3, 4):
        s = i - back
        if s < 0: continue
        for ins in md.disasm(blob[s:s + 15], va + s):
            if ins.address == va + s and ('0x%x]' % disp) in ins.op_str and ins.mnemonic.startswith(('mov', 'lea', 'cmp')):
                hits.append((ins.address, ins.mnemonic, ins.op_str))
            break
    i = blob.find(needle, i + 1)
seen = set()
for a, m, o in hits:
    if a in seen: continue
    seen.add(a)
    f = dis2.func_of(a)
    print('%x: %s %s  (function %s)' % (a, m, o, ('%x' % f[0]) if f else '?'))
