import pefile, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
EXE = "/data/uploads/FINAL FANTASY VII REBIRTH/End/Binaries/Win64/ff7rebirth_.exe"
data = open(EXE, 'rb').read()
pe = pefile.PE(EXE, fast_load=True)
secs = [(s.Name.rstrip(b'\0').decode(), s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData) for s in pe.sections]
def rva_to_off(rva):
    for n, va, vs, raw, rs in secs:
        if va <= rva < va + rs: return raw + rva - va
def wstr(rva, maxlen=200):
    o = rva_to_off(rva)
    if o is None: return None
    out = []
    for k in range(maxlen):
        c = data[o + 2*k] | (data[o + 2*k + 1] << 8)
        if c == 0: break
        if c < 32 or c > 126: return None
        out.append(chr(c))
    return ''.join(out) if out else None
start = int(sys.argv[1], 16); length = int(sys.argv[2], 16)
md = Cs(CS_ARCH_X86, CS_MODE_64); md.detail = False
o = rva_to_off(start)
for insn in md.disasm(data[o:o+length], start):
    extra = ''
    if 'rip +' in insn.op_str or 'rip -' in insn.op_str:
        import re
        m = re.search(r'rip ([+-]) (0x[0-9a-f]+|\d+)', insn.op_str)
        if m:
            d = int(m.group(2), 0) * (1 if m.group(1) == '+' else -1)
            t = insn.address + insn.size + d
            s = wstr(t)
            extra = '   ; %s' % (repr(s) if s else hex(t))
    print('%x: %-8s %s%s' % (insn.address, insn.mnemonic, insn.op_str, extra))
