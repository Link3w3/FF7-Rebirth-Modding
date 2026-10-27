"""Instructions using a given disp32 (memory operand displacement) in the exe's code.  dispscan.py <hex disp> [limit]"""
import sys, struct
sys.path.insert(0, '/work/grab1014/refl')
sys.path.insert(0, '/work/kh2data1014/re')
from ff7dis import p, md
disp = int(sys.argv[1], 16)
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 400
pat = struct.pack('<I', disp)
data = p.data
out = []
for sec in [s for s in p.sections if s['code']]:
    start, end = sec['off'], sec['off'] + sec['rsize']
    o = data.find(pat, start, end)
    while o >= 0 and len(out) < limit:
        for back in (2, 3, 4, 5):
            va = sec['va'] + (o - back - start)
            ins = list(md.disasm(data[o - back:o - back + 15], va, 1))
            if ins and hex(disp) in ins[0].op_str and ins[0].address + ins[0].size in (va + back + 4, va + back + 5, va + back + 8):
                out.append('%x  %s %s' % (ins[0].address, ins[0].mnemonic, ins[0].op_str))
                break
        o = data.find(pat, o + 1, end)
print('\n'.join(out))
print(len(out))
