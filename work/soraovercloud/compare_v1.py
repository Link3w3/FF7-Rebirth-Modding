"""The 1296 riding / field-action / level packages of SoraOverCloudMotion_P against Cloud's originals (soraanim1018/pkgs):
which settings, notifies and user data Cloud's have that Sora's lack."""
import sys, glob, os, collections
sys.path[:0]=['/work/iostore','/work/cs','/work/weap1012/tools','/work/swap1012/tools','/work/fx1018/editor/Python']
from iostore import Toc
from zen import Zen
import gameids
from rebirth_fx.fxcore import Package
t = Toc(sys.argv[1])
ours = {t.chunk_id64(i): i for i in range(1, t.entries)}
def info(d, label):
    p = Package(d, label)
    main = None
    kinds = collections.Counter()
    for i, (cls, v, b) in p.exports.items():
        kinds[cls] += 1
        if cls in ('AnimSequence', 'BlendSpace', 'BlendSpace1D', 'AimOffsetBlendSpace', 'AnimComposite', 'AnimMontage', 'EndAnimSet'):
            main = (cls, {k: x.value for k, x in v.value.items()})
    return main, kinds
stats = collections.Counter(); ex = collections.defaultdict(list)
for f in sorted(glob.glob('/work/soraanim1018/pkgs/*.uasset')):
    rel = os.path.basename(f)[:-7].replace('__', '/')
    pid = gameids.pkgid('/Game/' + rel)
    if pid not in ours: continue
    (cc, vc), kc = info(open(f, 'rb').read(), rel)
    (co, vo), ko = info(t.read(ours[pid]), rel)
    if cc != co: stats['class %s->%s' % (cc, co)] += 1; continue
    if cc != 'AnimSequence': stats['other ' + cc] += 1; continue
    stats['anims'] += 1
    for k in sorted(set(vc) - set(vo)):
        stats['only Cloud: ' + k] += 1; ex['only Cloud: ' + k].append(rel)
    for k in sorted(set(vo) - set(vc)):
        stats['only Sora: ' + k] += 1; ex['only Sora: ' + k].append(rel)
    for k in ('bPoseAnimation', 'OverrideBehaviorActionBlendTime', 'bEnableRootMotion', 'RootMotionRootLock', 'bForceRootLock', 'RateScale', 'AdditiveAnimType', 'RefPoseType', 'RefFrameIndex'):
        if k in vc and k in vo and str(vc[k]) != str(vo[k]):
            stats['differs: ' + k] += 1; ex['differs: ' + k].append((rel, vc[k], vo[k]))
    nc = len(vc.get('Notifies') or []); no = len(vo.get('Notifies') or [])
    if nc != no:
        stats['notify count differs'] += 1; ex['notify count differs'].append((rel, nc, no))
    kc2 = {k: v for k, v in kc.items() if k != 'AnimSequence'}; ko2 = {k: v for k, v in ko.items() if k != 'AnimSequence'}
    if kc2 != ko2:
        stats['notify objects differ'] += 1; ex['notify objects differ'].append((rel, dict(collections.Counter(kc2) - collections.Counter(ko2))))
for k, v in sorted(stats.items(), key=lambda x: -x[1]): print(v, k)
for k in ex:
    print('==', k, ex[k][:4])
