import sys, json, re
sys.path.insert(0, '/work/iostore')
from iostore import Toc
want = {
 'pakchunk4': [r'/Character/Player/PC0000_00_Cloud_Standard/Model/PC0000_00_Skeleton\.uasset$',
               r'/Character/Player/PC0011_00_Vincent_Standard/Model/PC0011_00_Skeleton\.uasset$',
               r'/Character/Player/PC0011_00_Vincent_Standard/Model/PC0011_00\.uasset$',
               r'/Character/Weapon/WE0011_00_Vincent_Quiksilver/Model/WE0011_00_Skeleton\.uasset$',
               r'/BluePrint/Character/Weapon/WE0011_00_Vincent_Quiksilver\.uasset$',
               r'/BluePrint/Character/Weapon/WE0000_00_Cloud_BusterSword\.uasset$',
               r'/DataAsset/Game/CharaSpec/CharaSpec_WE0011_00_Vincent_Quiksilver\.uasset$',
               r'/DataAsset/Game/CharaSpec/CharaSpec_WE0000_00_Cloud_BusterSword\.uasset$',
               r'/BluePrint/Character/Player/PC0011_00_Vincent_Standard\.uasset$',
               r'/BluePrint/Character/Player/PC0000_00_Cloud_Standard\.uasset$',
               r'/Motion/Player/PC0000_Cloud/Battle00/B_(AtkBurst|AtkLimit|Ability)[^/]*\.uasset$',
               r'/Motion/Player/PC0011_Vincent/Battle00/B_(AtkBurst|AtkLimit|Ability|Idle01|Run01|Walk01)[^/]*\.uasset$',
               r'/Motion/Player/PC0000_Cloud/Battle00/B_(Idle01|Run01|Walk01|Guard01|Dmg)[^/]*\.uasset$'],
 'pakchunk10': [r'/Character/Enemy/EB0016_00_Rufus_Standard/Model/EB0016_00_Skeleton\.uasset$'],
 'pakchunk8': [r'/Character/NonPlayer/NP0000_00_Biggs_Standard/Model/NP0000_00_Skeleton\.uasset$',
               r'/Motion/NonPlayer/NP0000_Biggs/Neutral00\.uasset$'],
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
json.dump(plan, open('plan2.json', 'w'))
reads = {}
for p in plan:
    for b in p['blocks']:
        reads.setdefault(p['chunk'], set()).add((b[0], (b[1] + 15) & ~15))
reads = {c: sorted(v) for c, v in reads.items()}
json.dump(reads, open('reads2.json', 'w'))
print({c: (len(v), sum(s for _, s in v)) for c, v in reads.items()})
script = '''import json, os
reads = %s
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/gunmoves2")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size; o.write(d); n += size
    print(chunk, len(ranges), n)
''' % json.dumps(reads, separators=(',', ':'))
open('device_extract2.py', 'w').write(script)
print(len(script))
