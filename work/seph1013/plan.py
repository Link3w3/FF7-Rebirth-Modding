import sys, json, re
sys.path.insert(0, '/work/iostore')
from iostore import Toc
want = {
 'pakchunk10': [r'/Motion/Player/PC0010_Sephiroth_Transform/[^/]+\.uasset$',
                r'/Motion/Player/PC0010_Sephiroth_Transform/Battle0[01](_Comp)?/[^/]+\.uasset$',
                r'/BluePrint/AI/Enemy/PC0010_10_Sephiroth_Transform/.*\.uasset$',
                r'/BluePrint/Character/Player/PC0010_10_Sephiroth_Transform\.uasset$'],
 'pakchunk4': [r'/Motion/Player/PC0010_Sephiroth/[^/]+\.uasset$',
               r'/Motion/Player/PC0010_Sephiroth/Battle0[01](_Comp)?/[^/]+\.uasset$',
               r'/BluePrint/Character/Player/PC0010_00_Sephiroth_Standard\.uasset$'],
}
plan = []; total = 0
for chunk, pats in want.items():
    t = Toc(chunk + '-WindowsNoEditor.utoc')
    for i, path in t.files.items():
        if not any(re.search(p, path) for p in pats): continue
        off, ln = t.offlen[i]
        first = off // t.blocksz; last = (off + ln - 1) // t.blocksz
        blocks = [list(t.blocks[b]) for b in range(first, last + 1)]
        total += sum((b[1] + 15) & ~15 for b in blocks)
        plan.append(dict(chunk=chunk, path=path, index=i, offset=off, length=ln, first_block=first, blocks=blocks))
print(len(plan), 'packages', total, 'compressed bytes')
json.dump(plan, open('plan.json', 'w'))
reads = {}
for p in plan:
    for b in p['blocks']:
        reads.setdefault(p['chunk'], set()).add((b[0], (b[1] + 15) & ~15))
reads = {c: sorted(v) for c, v in reads.items()}
# merge adjacent ranges to keep the device script small
merged = {}
for c, rs in reads.items():
    m = []
    for off, size in rs:
        if m and m[-1][0] + m[-1][1] == off: m[-1][1] += size
        else: m.append([off, size])
    merged[c] = m
json.dump(reads, open('reads.json', 'w')); json.dump(merged, open('merged.json', 'w'))
print({c: (len(v), sum(s for _, s in v)) for c, v in merged.items()})
from collections import Counter
print(Counter(re.sub(r'/[^/]+$', '', p['path'].split('/Content/')[1]) for p in plan))
