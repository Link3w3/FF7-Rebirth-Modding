"""call/jmp rel32 sites to target VAs.  calls.py <hex va>..."""
import sys
sys.path.insert(0, '/work/grab1014/refl')
sys.path.insert(0, '/work/kh2data1014/re')
from ff7dis import p, md
import numpy as np
targets = [int(x, 16) for x in sys.argv[1:]]
data = p.data
for sec in [s for s in p.sections if s['code']]:
    start, end = sec['off'], sec['off'] + sec['rsize']
    blob = np.frombuffer(data[start:end], dtype=np.uint8)
    n = len(blob) - 5
    op = blob[:n]
    disp = (blob[1:n+1].astype(np.int64) | (blob[2:n+2].astype(np.int64) << 8) | (blob[3:n+3].astype(np.int64) << 16) | (blob[4:n+4].astype(np.int64) << 24))
    disp = np.where(disp >= 2**31, disp - 2**32, disp)
    va = sec['va'] + np.arange(n, dtype=np.int64)
    tgt = va + 5 + disp
    for t in targets:
        for i in np.nonzero(((op == 0xE8) | (op == 0xE9)) & (tgt == t))[0]:
            print('%x %s -> %x' % (int(va[i]), 'call' if op[i] == 0xE8 else 'jmp', t))
