import pefile, capstone, struct, sys
dll=sys.argv[1]; target=int(sys.argv[2],16); before=int(sys.argv[3],16) if len(sys.argv)>3 else 0x200; after=int(sys.argv[4],16) if len(sys.argv)>4 else 0x20
pe=pefile.PE(dll, fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXCEPTION'],pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
raw=open(dll,'rb').read()
base=pe.OPTIONAL_HEADER.ImageBase
def rva2off(rva):
    for s in pe.sections:
        if s.VirtualAddress<=rva<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):
            return s.PointerToRawData+rva-s.VirtualAddress
imports={}
for e in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
    for imp in e.imports:
        imports[imp.address-base]=(e.dll.decode(), imp.name.decode() if imp.name else str(imp.ordinal))
# function start from pdata
fs=None
for rf in pe.DIRECTORY_ENTRY_EXCEPTION:
    if rf.struct.BeginAddress<=target<rf.struct.EndAddress:
        fs=(rf.struct.BeginAddress, rf.struct.EndAddress); break
print('function', [hex(x) for x in fs] if fs else None)
def s_at(rva):
    off=rva2off(rva)
    if off is None: return None
    b=raw[off:off+160]
    if len(b)>4 and b[1]==0 and b[3]==0 and 32<=b[0]<127:
        s=b.decode('utf-16-le','ignore').split('\x00')[0]
        if len(s)>=2: return 'u"'+s+'"'
    s=b.split(b'\x00')[0]
    if len(s)>=4 and all(32<=c<127 for c in s): return '"'+s.decode()+'"'
    return None
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64); md.detail=True
start = fs[0] if fs and len(sys.argv)<=3 else target-before
end = fs[1] if fs and len(sys.argv)<=3 else target+after
off=rva2off(start)
for ins in md.disasm(raw[off:off+(end-start)], start):
    extra=''
    for op in ins.operands:
        if op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP:
            t=ins.address+ins.size+op.mem.disp
            if t in imports: extra='   ; '+imports[t][1]
            else:
                s=s_at(t); extra='   ; [%x]%s'%(t,' '+s if s else '')
    print('%x: %-7s %s%s%s'%(ins.address, ins.mnemonic, ins.op_str, extra, ' <==' if ins.address+ins.size==target else ''))
