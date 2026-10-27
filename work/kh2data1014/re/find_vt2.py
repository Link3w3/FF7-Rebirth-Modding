import sys, re, struct
sys.path.insert(0, '/work/kh2data1014/re')
from ff7dis import p, md, dis
data = p.data
from collections import Counter
cands = Counter()
for sec in [s for s in p.sections if s['code']]:
    start, end = sec['off'], sec['off'] + sec['rsize']
    blob = data[start:end]
    # lea rcx, [reg + 0x4d0] : 48 8D 8B D0 04 00 00 (rbx) / 48 8D 8F (rdi) / 48 8D 8E (rsi) / 49 8D 8E (r14) ...
    for m in re.finditer(rb'[\x48\x49]\x8d[\x88-\x8f]\xd0\x04\x00\x00\xe8', blob):
        o = start + m.start()
        va = sec['va'] + (o - start)
        call_va = va + 7
        rel = struct.unpack_from('<i', data, o + 8)[0]
        target = call_va + 5 + rel
        # in target: look for "lea rax, [rip+X]; mov [rcx], rax" in the first 20 instructions
        try:
            ins = dis(target, 25, stop_ret=True)
        except Exception:
            continue
        for i, x in enumerate(ins):
            if x.mnemonic == 'lea' and 'rip' in x.op_str:
                disp = int(x.op_str.split('rip + ')[1].rstrip(']'), 16) if 'rip + ' in x.op_str else None
                if disp is None: continue
                vt = x.address + x.size + disp
                # next store into [rcx] or [rbx]
                for y in ins[i + 1:i + 4]:
                    if y.mnemonic == 'mov' and y.op_str.startswith('qword ptr [r') and y.op_str.endswith(', rax') and '+' not in y.op_str:
                        cands[(vt, target)] += 1
                        break
for (vt, ctor), n in cands.most_common(20):
    ents = [p.u64(vt + 8 * i) for i in range(8)]
    print(hex(vt), 'ctor', hex(ctor), n, [hex(e) for e in ents])
