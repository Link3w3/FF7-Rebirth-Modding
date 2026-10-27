"""rip-relative references (lea/mov/cmp with [rip+disp32]) to target VAs, in the exe's code sections.
   riprefs.py <hex va>..."""
import sys, struct
sys.path.insert(0, '/work/grab1014/refl')
sys.path.insert(0, '/work/kh2data1014/re')
from ff7dis import p, md
import numpy as np
targets = [int(x, 16) for x in sys.argv[1:]]
data = p.data
for sec in [s for s in p.sections if s['code']]:
    start, end = sec['off'], sec['off'] + sec['rsize']
    blob = np.frombuffer(data[start:end], dtype=np.uint8)
    n = len(blob) - 4
    disp = (blob[:n].astype(np.int64) | (blob[1:n+1].astype(np.int64) << 8) | (blob[2:n+2].astype(np.int64) << 16) | (blob[3:n+3].astype(np.int64) << 24))
    disp = np.where(disp >= 2**31, disp - 2**32, disp)
    pos_va = sec['va'] + np.arange(n, dtype=np.int64)
    for t in targets:
        # the instruction ends 4 bytes after the disp (no immediate) for most lea/mov forms: target = disp_va + 4 + disp
        idx = np.nonzero(pos_va + 4 + disp == t)[0]
        for i in idx[:50]:
            va = int(pos_va[i])
            # decode from a few bytes back
            for back in (3, 2, 4, 5, 6):
                ins = list(md.disasm(data[start + i - back:start + i - back + 16], va - back, 1))
                if ins and ins[0].address + ins[0].size == va + 4:
                    print('%x -> %x: %s %s' % (ins[0].address, t, ins[0].mnemonic, ins[0].op_str))
                    break
