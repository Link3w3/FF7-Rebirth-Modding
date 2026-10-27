"""Mirrors RebirthSkelCompat PackSets::Install: functions of the lookup's shape, their calls and the lea before each call."""
import sys, struct, re
sys.path.insert(0, '/work/grab1014/refl')
sys.path.insert(0, '/work/kh2data1014/re')
from ff7dis import p, md
import numpy as np
data = p.data
pat = re.compile(rb'\x40\x53\xB8\x20\x00\x00\x00\xE8....\x48\x2B\xE0\x48\x8D\x99(....)\x4C\x8B\xC2\x48\x8B\xCB\x48\x8D\x54\x24\x30\xE8....\x83\x38\xFF', re.S)
cands = []
for sec in [s for s in p.sections if s['code']]:
    start, end = sec['off'], sec['off'] + sec['rsize']
    for m in pat.finditer(data, start, end):
        va = sec['va'] + (m.start() - start)
        mp = struct.unpack('<i', m.group(1))[0]
        cands.append((va, mp))
print(len(cands), 'candidates')
for sec in [s for s in p.sections if s['code']]:
    start, end = sec['off'], sec['off'] + sec['rsize']
    blob = np.frombuffer(data[start:end], dtype=np.uint8)
    n = len(blob) - 5
    op = blob[:n]
    disp = (blob[1:n+1].astype(np.int64) | (blob[2:n+2].astype(np.int64) << 8) | (blob[3:n+3].astype(np.int64) << 16) | (blob[4:n+4].astype(np.int64) << 24))
    disp = np.where(disp >= 2**31, disp - 2**32, disp)
    vas = sec['va'] + np.arange(n, dtype=np.int64)
    tgt = vas + 5 + disp
    for va, mp in cands:
        idx = np.nonzero((op == 0xE8) & (tgt == va))[0]
        conts = []
        for i in idx:
            o = start + int(i)
            lea = data[o - 7:o]
            c = None
            if lea[0] == 0x48 and lea[1] == 0x8D and (lea[2] & 0xF8) == 0x88 and (lea[2] & 7) != 4:
                c = struct.unpack('<i', lea[3:7])[0]
            conts.append((int(vas[i]), c))
        print('%x map +%x: %d calls; lea containers: %s' % (va, mp, len(idx), ', '.join('%x:%s' % (a, hex(c) if c is not None else '-') for a, c in conts)))
