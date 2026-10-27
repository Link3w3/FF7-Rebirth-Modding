"""UEnums in the exe (FEnumParams): name -> [(enumerator, value)]."""
import struct, sys, json
import numpy as np
sys.path.insert(0, '/work/grab1014/refl')
from pe import PE
p = PE('/data/uploads/FINAL FANTASY VII REBIRTH/End/Binaries/Win64/ff7rebirth_.exe')
text = [s for s in p.sections if s['code']][0]
code_lo, code_hi = text['va'], text['va'] + text['vsize']
data_lo = min(s['va'] for s in p.sections if s['name'] in ('.rdata', '.data'))
data_hi = max(s['va'] + s['vsize'] for s in p.sections if s['name'] in ('.rdata', '.data'))
enums = {}
for sec in [s for s in p.sections if s['name'] in ('.rdata', '.data')]:
    raw = p.data[sec['off']:sec['off'] + sec['rsize']]
    q = np.frombuffer(raw[:len(raw) // 8 * 8], dtype='<u8')
    n = len(q) - 6
    outer, disp, name, cpp, params, num = q[:n], q[1:n+1], q[2:n+2], q[3:n+3], q[4:n+4], q[5:n+5] & 0xFFFFFFFF
    isc = lambda v: (v >= code_lo) & (v < code_hi)
    isd = lambda v: (v >= data_lo) & (v < data_hi)
    m = isc(outer) & ((disp == 0) | isc(disp)) & isd(name) & isd(cpp) & isd(params) & (num > 0) & (num < 2000)
    for i in np.nonzero(m)[0]:
        nm = p.cstr(int(name[i])); cp = p.cstr(int(cpp[i]))
        if not nm or not cp or not nm.isidentifier():
            continue
        items = []
        ok = True
        for k in range(int(num[i])):
            e = int(params[i]) + 16 * k
            en = p.cstr(p.u64(e)); val = p.u64(e + 8)
            if en is None or val is None:
                ok = False; break
            if val >= 1 << 63: val -= 1 << 64
            items.append((en, val))
        if ok:
            enums[nm] = items
json.dump(enums, open('enums.json', 'w'), indent=0)
print(len(enums))
