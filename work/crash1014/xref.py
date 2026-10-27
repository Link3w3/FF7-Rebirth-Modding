import struct, sys, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
exec(open('dis.py').read().split("if __name__ == '__main__':")[0])
targets = [int(x, 16) for x in sys.argv[1:]]
text = [s for s in secs if s[0] == '.text'][0]
code = d[text[3]:text[3] + text[2]]
# quick scan: rip-relative disp32 references
hits = {t: [] for t in targets}
for i in range(len(code) - 7):
    # check every 4-byte window as a rip-relative disp ending an instruction of len L (we test L from 5..10)
    pass
md = Cs(CS_ARCH_X86, CS_MODE_64)
md.skipdata = True
for b, e in funcs:
    if not (text[1] <= b < text[1] + text[2]): continue
    seg = d[off(b):off(b) + (e - b)]
    if not any(struct.pack('<i', 0) for _ in [0]): pass
    for ins in md.disasm(seg, b):
        if 'rip' in ins.op_str:
            m = re.search(r'rip ([+-]) 0x([0-9a-f]+)', ins.op_str)
            if m:
                t = ins.address + ins.size + (int(m.group(2), 16) if m.group(1) == '+' else -int(m.group(2), 16))
                if t in hits: hits[t].append((b, ins.address, ins.mnemonic + ' ' + ins.op_str))
for t, h in hits.items():
    print('== %x: %d refs' % (t, len(h)))
    for x in h[:40]: print('   func %x at %x: %s' % x)
