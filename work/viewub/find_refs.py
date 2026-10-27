import pefile, struct, sys, re
EXE = "/data/uploads/FINAL FANTASY VII REBIRTH/End/Binaries/Win64/ff7rebirth_.exe"
pe = pefile.PE(EXE, fast_load=True)
data = open(EXE, 'rb').read()
base = pe.OPTIONAL_HEADER.ImageBase
secs = [(s.Name.rstrip(b'\0').decode(), s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData) for s in pe.sections]
for s in secs: print(s)
def off_to_rva(off):
    for n, va, vs, raw, rs in secs:
        if raw <= off < raw + rs: return va + off - raw
def rva_to_off(rva):
    for n, va, vs, raw, rs in secs:
        if va <= rva < va + rs: return raw + rva - va
name = sys.argv[1] if len(sys.argv) > 1 else 'SVPositionToTranslatedWorld'
pat = name.encode('utf-16-le') + b'\0\0'
hits = [m.start() for m in re.finditer(re.escape(pat), data)]
print(name, 'string at offsets', [hex(h) for h in hits][:10])
targets = {off_to_rva(h): h for h in hits if (h % 2) == 0 and data[h-2:h] == b'\0\0'}
print('string RVAs', [hex(t) for t in targets])
text = [s for s in secs if s[0] == '.text'][0]
n, va, vs, raw, rs = text
code = data[raw:raw+rs]
refs = []
for t in targets:
    # lea r64, [rip+disp32]: (48|4C) 8D modrm(00 reg 101) disp32 ; rip = insn_end
    for m in re.finditer(rb'[\x48\x4C]\x8D[\x05\x0D\x15\x1D\x25\x2D\x35\x3D]', code):
        i = m.start()
        disp = struct.unpack_from('<i', code, i + 3)[0]
        if va + i + 7 + disp == t:
            refs.append((va + i, t))
print('lea refs', [(hex(a), hex(t)) for a, t in refs][:20])
