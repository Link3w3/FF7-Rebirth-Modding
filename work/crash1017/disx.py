import pefile, struct, capstone, sys
exe='/data/uploads/FINAL FANTASY VII REBIRTH/End/Binaries/Win64/ff7rebirth_.exe'
pe=pefile.PE(exe, fast_load=True)
raw=open(exe,'rb').read()
IMG=0x140000000
def rva2off(rva):
    for s in pe.sections:
        if s.VirtualAddress<=rva<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):
            return s.PointerToRawData+rva-s.VirtualAddress
    return None
def string_at(rva):
    off=rva2off(rva)
    if off is None: return None
    b=raw[off:off+200]
    # utf16?
    if len(b)>4 and b[1]==0 and b[3]==0 and 32<=b[0]<127:
        s=b.decode('utf-16-le','ignore').split('\x00')[0]
        if len(s)>=3: return 'u"'+s+'"'
    s=b.split(b'\x00')[0]
    if len(s)>=4 and all(32<=c<127 for c in s): return '"'+s.decode()+'"'
    return None
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64); md.detail=True
def dis(start, n, mark=None):
    off=rva2off(start)
    for ins in md.disasm(raw[off:off+n], IMG+start):
        rva=ins.address-IMG
        extra=''
        if 'rip' in ins.op_str:
            for op in ins.operands:
                if op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP:
                    t=ins.address+ins.size+op.mem.disp-IMG
                    s=string_at(t)
                    extra='   ; [%x]%s'%(t, ' '+s if s else '')
        print('%x: %-7s %s%s%s'%(rva, ins.mnemonic, ins.op_str, extra, ' <==' if mark and rva==mark else ''))
if __name__=='__main__':
    dis(int(sys.argv[1],16), int(sys.argv[2],16), int(sys.argv[3],16) if len(sys.argv)>3 else None)
