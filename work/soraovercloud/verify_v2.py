import sys, glob, os, collections
sys.path[:0]=['/work/iostore','/work/cs','/work/weap1012/tools','/work/swap1012/tools','/work/fx1018/editor/Python']
from iostore import Toc
from zen import Zen
import gameids, hdr
from rebirth_fx.fxcore import Package
PK, OB = gameids.load()
NULL = 0xFFFFFFFFFFFFFFFF
known = set(); pkgs = set()
for u in ['/work/soradata/out_assets_r4_summon/SoraAssets_P.utoc', sys.argv[1]]:
    t = Toc(u)
    for i in range(t.entries):
        if t.chunk_type(i) == 2:
            z = Zen(t.read(i)); pkgs.add(t.chunk_id64(i))
            for e in z.exports:
                if e['global_import'] != NULL: known.add(e['global_import'] & ~(3 << 62))
t = Toc(sys.argv[1])
_, store = hdr.parse_header(t.read(0))
ours = {t.chunk_id64(i): i for i in range(1, t.entries)}
c = collections.Counter(); bad = []
for i in range(1, t.entries):
    z = Zen(t.read(i))
    for h in z.imports:
        if h == NULL: continue
        if (h >> 62) == 1: c['script'] += 1; continue
        hh = h & ~(3 << 62)
        if hh in known: c['sora/ours'] += 1
        elif hh in OB: c['game:' + OB[hh].split('/')[2]] += 1
        else: c['unknown'] += 1; bad.append((t.files.get(i), hex(h)))
    for p in store[t.chunk_id64(i)]['imports']:
        c['pkg ' + ('sora/ours' if p in pkgs else 'game' if p in PK else 'UNKNOWN')] += 1
print(c); print(bad[:10])
# the 890 against Cloud's originals
diffs = collections.Counter(); notes = []
def props(d, label):
    p = Package(d, label)
    for i, (cls, v, b) in p.exports.items():
        if cls == 'AnimSequence':
            return {k: x.value for k, x in v.value.items()}, collections.Counter(cls for cls, v, b in p.exports.values())
for f in sorted(glob.glob('/work/cloudaction/pkgs/*.uasset')):
    rel = os.path.basename(f)[:-7].replace('__', '/')
    pid = gameids.pkgid('/Game/' + rel)
    if pid not in ours: diffs['MISSING'] += 1; continue
    dc = open(f, 'rb').read(); do = t.read(ours[pid])
    zc, zo = Zen(dc), Zen(do)
    pc = {e['global_import'] for e in zc.exports if e['global_import'] != NULL}
    po = {e['global_import'] for e in zo.exports if e['global_import'] != NULL}
    if not pc <= po: diffs['public export missing'] += 1; notes.append(rel)
    vc, kc = props(dc, rel); vo, ko = props(do, rel)
    for k in ('bPoseAnimation', 'OverrideBehaviorActionBlendTime'):
        if str(vc.get(k)) != str(vo.get(k)): diffs['prop ' + k] += 1; notes.append((rel, k, vc.get(k), vo.get(k)))
    if abs(float(vc['SequenceLength']) - float(vo['SequenceLength'])) > 0.05: diffs['length'] += 1; notes.append((rel, vc['SequenceLength'], vo['SequenceLength']))
    nc = len(vc.get('Notifies', []) or []); no = len(vo.get('Notifies', []) or [])
    if nc != no: diffs['notify count'] += 1; notes.append((rel, 'notifies', nc, no))
    if ('AssetUserData' in vc) != ('AssetUserData' in vo): diffs['user data'] += 1; notes.append((rel, 'userdata'))
    kc2 = {k: v for k, v in kc.items() if k != 'AnimSequence'}; ko2 = {k: v for k, v in ko.items() if k != 'AnimSequence'}
    if kc2 != ko2: diffs['notify classes'] += 1; notes.append((rel, dict(kc2 - ko2), dict(ko2 - kc2)))
    diffs['checked'] += 1
print(diffs); print(notes[:15])
