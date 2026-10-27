import sys, re, struct
sys.path.insert(0, '/work/grab1014/refl')
sys.path.insert(0, '/work/kh2data1014/re')
from ff7dis import p, md
data = p.data
text = [s for s in p.sections if s['code']]
hits = []
for sec in text:
    start, end = sec['off'], sec['off'] + sec['rsize']
    blob = data[start:end]
    # mov qword ptr [reg + 0x4d0], reg  : REX.W 89 /r with mod=10 (disp32): 48/4C 89 [80-BF] d0 04 00 00
    for m in re.finditer(rb'[\x48\x4c\x49\x4d]\x89[\x80-\xbf]\xd0\x04\x00\x00', blob):
        o = start + m.start()
        va = sec['va'] + (o - start)
        # look back up to 24 bytes for a lea r, [rip+disp]
        back = data[o - 24:o]
        for k in range(len(back) - 7, -1, -1):
            if back[k] in (0x48, 0x4c) and back[k + 1] == 0x8d and (back[k + 2] & 0xc7) == 0x05:
                disp = struct.unpack_from('<i', back, k + 3)[0]
                lea_va = va - 24 + k
                target = lea_va + 7 + disp
                hits.append((va, target))
                break
print(len(hits))
from collections import Counter
c = Counter(t for _, t in hits)
for t, n in c.most_common(15):
    sec = p.section_of(t)
    # vtable: first entries should be code pointers
    ents = [p.u64(t + 8 * i) for i in range(8)]
    codeish = sum(1 for e in ents if e and p.section_of(e) and p.section_of(e)['code'])
    print(hex(t), n, sec['name'] if sec else None, 'code entries', codeish, [hex(e) for e in ents[:7]])
