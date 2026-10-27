import sys
sys.path.insert(0,'/work/crash1018')
import unwind
from mdmp import Dump
EXE="/data/uploads/FINAL FANTASY VII REBIRTH/End/Binaries/Win64/ff7rebirth_.exe"
pe=unwind.PE(EXE)
dm=Dump(sys.argv[1])
ex=dm.exception()
print({k:(hex(v) if isinstance(v,int) else v) for k,v in ex.items() if k!='ctx'})
regs=dm.context(ex['ctx'])
print({k:hex(v) for k,v in regs.items() if k in ('Rip','Rsp','Rcx','Rdx','R8','R9','Rax','Rbx','Rsi','Rdi','R10','R11','R12','R13','R14','R15','Rbp')})
for r in [0xc22f3b,0x920a73,0xb202b7,0x91eab1,0x44e71b5,0xdad4b7,0xdaccda,0xb62fb3,0x921e3e,0x9219a4,0x795382,0x44d7f47,0x449907b,0x4496bc9]:
    f=pe.func(r)
    print(hex(r), ('func 0x%x +0x%x'%(f[0], r-f[0])) if f else None)
