"""SoraAssets_P's Sora-path animations against Cloud's originals of the same set and name (soraanim1018/pkgs): which of
Cloud's serialized settings Sora's lack or have different."""
import sys, glob, os, collections
sys.path[:0]=['/work/iostore','/work/cs','/work/weap1012/tools','/work/swap1012/tools','/work/fx1018/editor/Python']
from iostore import Toc
import gameids
from rebirth_fx.fxcore import Package
SYNC = ('bPoseAnimation', 'OverrideBehaviorActionBlendTime', 'OverrideBehaviorActionBlendOutTime', 'RootMotionScale',
        'bEnableRootMotion', 'RootMotionRootLock', 'bForceRootLock', 'bUseNormalizedRootMotionScale', 'RateScale', 'Interpolation',
        'OverrideBehaviorActionBlendOutSequence', 'OverrideBehaviorActionBlendOutSequenceFilter', 'AdditiveAnimType', 'RefPoseType', 'RefFrameIndex', 'RefPoseSeq')
t = Toc(sys.argv[1])
by = {}
for i in range(t.entries):
    p = t.files.get(i)
    if p and p.endswith('.uasset'): by[p.split('Content/')[1][:-7]] = i
def vals(d, label):
    p = Package(d, label)
    for i, (cls, v, b) in p.exports.items():
        if cls == 'AnimSequence':
            return {k: x for k, x in v.value.items() if k in SYNC}
    return None
stats = collections.Counter(); ex = collections.defaultdict(list)
for f in sorted(glob.glob('/work/soraanim1018/pkgs/*.uasset')):
    rel = os.path.basename(f)[:-7].replace('__', '/')
    srel = rel.replace('PC0000_Cloud', 'PC0000_00_Sora_KH2')
    cand = [srel, srel.replace('/Battle00/', '/Battle00/FromCloud/')]
    hit = [c for c in cand if c in by]
    if not hit: stats['no Sora version'] += 1; continue
    vc = vals(open(f, 'rb').read(), rel)
    vo = vals(t.read(by[hit[0]]), hit[0])
    if vc is None or vo is None: stats['not an anim sequence'] += 1; continue
    stats['compared'] += 1
    kind = rel.split('/')[1] if rel.split('/')[1] != 'Player' else rel.split('/')[3]
    for k in SYNC:
        a = None if k not in vc else ('0' if vc[k].zero else str(vc[k].value))
        b = None if k not in vo else ('0' if vo[k].zero else str(vo[k].value))
        if a != b:
            stats['%s %s' % (kind, k)] += 1; ex['%s %s' % (kind, k)].append((rel.rsplit('/', 1)[1], a, b))
for k, v in sorted(stats.items()): print(v, k)
for k in ex: print('==', k, ex[k][:3])
