import pefile, struct, sys, re
exe='/data/uploads/FINAL FANTASY VII REBIRTH/End/Binaries/Win64/ff7rebirth_.exe'
pe=pefile.PE(exe, fast_load=True)
raw=open(exe,'rb').read()
IMG=0x140000000
targets=[int(a,16) for a in sys.argv[1:]]
text=[s for s in pe.sections if s.Name.startswith(b'.text')][0]
base=text.VirtualAddress; off=text.PointerToRawData; size=text.SizeOfRawData
data=raw[off:off+size]
# brute force: any 4-byte disp at position p such that rva(p)+4+disp+k == target for instruction ending at p+4(+imm)
import collections
hits=collections.defaultdict(list)
for t in targets:
    for p in range(0, len(data)-4):
        disp=struct.unpack_from('<i',data,p)[0]
        for extra in (0,1,4):
            if base+p+4+extra+disp==t:
                hits[t].append(base+p)
for t,l in hits.items():
    print(hex(t), len(l), ' '.join(hex(x) for x in l[:80]))
