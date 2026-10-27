import sys, json, re
sys.path.insert(0, '/work/iostore')
from iostore import Toc
want = {
 'pakchunk11': [r'/Motion/Enemy/EB0016_Rufus/Battle00\.uasset$', r'/Motion/Enemy/EB0016_Rufus/Battle00/[^/]+\.uasset$'],
 'pakchunk9':  [r'/Motion/NonPlayer/NP0000_Biggs/Battle00\.uasset$', r'/Motion/NonPlayer/NP0000_Biggs/Battle00/[^/]+\.uasset$'],
 'pakchunk4':  [r'/Motion/Player/PC0000_Cloud/Battle0[01]/B_(NAttack|SAttack|SSAttack|AAttack|WAttack)[^/]*\.uasset$',
                r'/Motion/Player/PC0011_Vincent/Battle00/B_(NAttack|AAttack|WAttack)[^/]*\.uasset$'],
}
plan = []
total = 0
for chunk, pats in want.items():
    t = Toc(chunk + '-WindowsNoEditor.utoc')
    for i, path in t.files.items():
        if not any(re.search(p, path) for p in pats): continue
        off, ln = t.offlen[i]
        first = off // t.blocksz; last = (off + ln - 1) // t.blocksz
        blocks = [list(t.blocks[b]) for b in range(first, last + 1)]
        csz = sum((b[1] + 15) & ~15 for b in blocks)
        total += csz
        plan.append(dict(chunk=chunk, path=path, index=i, offset=off, length=ln, first_block=first, blocks=blocks))
print(len(plan), 'packages', total, 'compressed bytes')
from collections import Counter
print(Counter(p['chunk'] for p in plan))
json.dump(plan, open('plan.json', 'w'))
# reads: merged per chunk (offset, size) ranges
reads = {}
for p in plan:
    for b in p['blocks']:
        reads.setdefault(p['chunk'], set()).add((b[0], (b[1] + 15) & ~15))
reads = {c: sorted(v) for c, v in reads.items()}
json.dump(reads, open('reads.json', 'w'))
print({c: (len(v), sum(s for _, s in v)) for c, v in reads.items()})
