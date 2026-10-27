import dis2, struct, sys, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
d = dis2.d
text = [s for s in dis2.secs if s[0] == '.text'][0]
name, va, vsz, rp, rs = text
blob = d[rp:rp + rs]
want = [int(a, 16) for a in sys.argv[1:]]
md = Cs(CS_ARCH_X86, CS_MODE_64)
seen = set()
for w in want:
    pat = struct.pack('<I', w)
    for m in re.finditer(re.escape(pat), blob):
        at = va + m.start()
        f = dis2.func_of(at)
        if not f: continue
        # disassemble the function and find the instruction containing this disp
        b, e = f
        key = (b, w)
        code = d[dis2.off(b):dis2.off(b) + (e - b)]
        for ins in md.disasm(code, b):
            if ins.address <= at < ins.address + ins.size and ('0x%x]' % w) in ins.op_str:
                print('%x  %-8s %-50s in %x-%x' % (ins.address, ins.mnemonic, ins.op_str, b, e))
