import sys, struct, os, re, json; sys.path.insert(0,'.')
from tagged import *
def info(n):
    d = open('pkgs/'+n,'rb').read(); z = Zen(d); L = export_layout(z)
    short = n.rsplit('__',1)[-1][:-7]
    idx = [k for k,e in enumerate(z.exports) if e['name'] == short]
    if not idx: return None
    x = export_bytes(z, idx[0], L)
    p = x.find(struct.pack('<I', 0xac10ac10))
    dur = None; bones = None
    if p >= 0:
        ns = struct.unpack_from('<I', x, p+20)[0]; sr = struct.unpack_from('<f', x, p+24)[0]; bones = struct.unpack_from('<H', x, p+8)[0]
        dur = (ns-1)/sr if sr > 0 else None
    names = set(z.names)
    dmg = sorted(nm for nm in names if re.match(r'^(Atk_|EB0016_00_|NP0000_|PC00\d\d_\d\d_(?!Skeleton))', nm))
    flags = []
    if 'EndAnimNotifyStateBattleDamage' in names or 'DamageSourceIDs' in names or 'ReferenceDamageSourceId' in names: flags.append('DMG')
    if 'UseBullet' in names: flags.append('BULLET')
    if 'EndAnimNotifyBattleAbilityCancel' in names: flags.append('pcancel')
    if 'EndAIEnemyBattleAbilityCancel' in names: flags.append('aicancel')
    if 'Combo' in names: flags.append('combo')
    return dict(name=short, who=n.split('__')[2], set=n.split('__')[3], dur=dur, bones=bones, flags=flags, dmg=dmg)
rows = [info(n) for n in sorted(os.listdir('pkgs')) if not n.endswith('__Battle00.uasset')]
rows = [r for r in rows if r]
json.dump(rows, open('table.json','w'), indent=0)
for r in rows:
    if r['who'] in ('PC0000_Cloud','PC0011_Vincent') or re.search(r'Atk|Shot|Reload|Kick|Counter', r['name']):
        print(r['who'][:13].ljust(13), r['set'], r['name'].ljust(34), ('%.2fs' % r['dur']) if r['dur'] else '  ?  ', str(r['bones']).rjust(3), ' '.join(r['flags']).ljust(32), ','.join(r['dmg'])[:70])
