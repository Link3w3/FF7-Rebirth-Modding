import pefile,struct,sys
EXE="/data/uploads/FINAL FANTASY VII REBIRTH/End/Binaries/Win64/ff7rebirth_.exe"
pe=pefile.PE(EXE, fast_load=True)
raw=open(EXE,'rb').read()
IMG=0x140000000
def off(rva):
    for s in pe.sections:
        if s.VirtualAddress<=rva<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):
            return s.PointerToRawData+rva-s.VirtualAddress
def q(rva): return struct.unpack_from('<Q',raw,off(rva))[0]
def d(rva): return struct.unpack_from('<I',raw,off(rva))[0]
def cname(vt):
    col=q(vt-8)-IMG
    td=d(col+12)
    o=off(td+16); n=raw[o:o+200].split(b'\0')[0]
    return n.decode()
for a in sys.argv[1:]:
    vt=int(a,16)
    try:
        print(hex(vt), cname(vt))
        print('  slots:', ' '.join(hex(q(vt+8*i)-IMG) for i in range(0,40)))
    except Exception as e: print(hex(vt),'err',e)
