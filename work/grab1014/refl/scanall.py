"""Every UFunction's FFunctionParams in the exe, grouped by class (named from the class's StaticClass code), as text."""
import struct, sys, json
import numpy as np
sys.path.insert(0, '/work/grab1014/refl')
from refl import Refl, signature

EXE = '/data/uploads/FINAL FANTASY VII REBIRTH/End/Binaries/Win64/ff7rebirth_.exe'
r = Refl(EXE)
p = r.p
text = [s for s in p.sections if s['code']][0]
code_lo, code_hi = text['va'], text['va'] + text['vsize']
data_secs = [s for s in p.sections if not s['code'] and s['name'] in ('.rdata', '.data', '_RDATA')]
data_lo = min(s['va'] for s in data_secs)
data_hi = max(s['va'] + s['vsize'] for s in data_secs)

found = []
for sec in [s for s in p.sections if s['name'] in ('.rdata', '.data')]:
    raw = p.data[sec['off']:sec['off'] + sec['rsize']]
    q = np.frombuffer(raw[:len(raw) // 8 * 8], dtype='<u8')
    n = len(q) - 9
    outer = q[:n]; sup = q[1:n + 1]; name = q[2:n + 2]; own = q[3:n + 3]; dele = q[4:n + 4]; size = q[5:n + 5]
    props = q[6:n + 6]; nprops = q[7:n + 7] & 0xFFFFFFFF
    is_code = lambda v: (v >= code_lo) & (v < code_hi)
    is_data = lambda v: (v >= data_lo) & (v < data_hi)
    m = is_code(outer) & ((sup == 0) | is_code(sup)) & is_data(name) & ((own == 0) | is_data(own)) & ((dele == 0) | is_data(dele))
    m &= (size < 0x10000) & (nprops < 200) & (((nprops == 0) & (props == 0)) | ((nprops > 0) & is_data(props)))
    for i in np.nonzero(m)[0]:
        va = sec['va'] + int(i) * 8
        f = r.function_params_at(va)
        if not f or not f['name'] or not f['name'].replace('__DelegateSignature', '').isidentifier():
            continue
        if any(prm['name'] is None for prm in f['params']):
            continue
        found.append(f)
print(len(found), 'functions', file=sys.stderr)

# class names: outer = Z_Construct_UClass_X; its code loads &ClassParams (lea rdx, [rip+d]); ClassParams[0] = X::StaticClass,
# whose code loads TEXT("UX") + 1 (lea r8 / rdx / rcx, [rip+d]).
def rip_targets(fn, limit=96, depth=0):
    """Targets of lea reg, [rip+d] in the first `limit` bytes of fn (a jmp thunk is followed)."""
    o = p.off(fn)
    if o is None or depth > 3:
        return []
    out = []
    b = p.data[o:o + limit]
    for i in range(len(b) - 7):
        if b[i] in (0x48, 0x4C) and b[i + 1] == 0x8D and (b[i + 2] & 0xC7) == 0x05:
            d = struct.unpack_from('<i', b, i + 3)[0]
            out.append((fn + i + 7 + d, b[i] == 0x48 and b[i + 2] == 0x15))
        if b[i] == 0xE9 and i < 40 and not out:   # a thunk: mov eax, n; call __chkstk; sub rsp, rax; add rsp, n; jmp
            d = struct.unpack_from('<i', b, i + 1)[0]
            out += rip_targets(fn + i + 5 + d, limit, depth + 1)
            break
        if b[i] == 0x0F and b[i + 1] in (0x84, 0x85) and depth < 2:   # je / jne to a cold block
            d = struct.unpack_from('<i', b, i + 2)[0]
            far = fn + i + 6 + d
            if not (fn <= far < fn + limit):
                out += rip_targets(far, 200, depth + 1)
        if b[i] == 0xC3:
            break
    return out

def wide(va, limit=128):
    o = p.off(va)
    if o is None:
        return None
    end = o
    while end < o + limit * 2 and p.data[end:end + 2] != b'\0\0':
        end += 2
    try:
        s = p.data[o:end].decode('utf-16le')
    except UnicodeDecodeError:
        return None
    return s if s and s.replace('_', 'a').isalnum() else None

names = {}
def class_name(outer):
    if outer in names:
        return names[outer]
    best = None
    for t, _ in rip_targets(outer):
        sc = p.u64(t)
        if sc and code_lo <= sc < code_hi:
            for w, is_rdx in rip_targets(sc, 260):
                if not is_rdx:
                    continue
                s = wide(w)
                if s and len(s) > 1:
                    best = s
                    break
        if best:
            break
    names[outer] = best or ('?' + hex(outer))
    return names[outer]

by_class = {}
for f in found:
    by_class.setdefault(class_name(f['outer']), []).append(f)
with open('sdk.txt', 'w') as out:
    for cls in sorted(by_class):
        out.write('class %s\n' % cls)
        for f in sorted(by_class[cls], key=lambda f: f['name']):
            out.write('    %s\n' % signature(f))
json.dump({cls: [dict(name=f['name'], flags=f['flags'], params=[dict(name=x['name'], kind=x['kind'], flags=x['flags'], offset=x['offset']) for x in f['params']], size=f['size']) for f in fs] for cls, fs in by_class.items()}, open('sdk.json', 'w'))
print(len(by_class), 'classes', file=sys.stderr)
