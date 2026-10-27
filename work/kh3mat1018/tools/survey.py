"""Survey of KH3 Shader materials/instances: settings, uniform sets, shader maps."""
import os, sys, json, collections, glob
sys.path[:0] = ['/work/kh3fx', '/work/kh3bnm/src/rebirth_fx']
import kh3bonamik as k, tagged, kh3mat, kh3pick, kh3uniform

root = sys.argv[1]
classes = json.load(open(sys.argv[2]))
out = {}
for rel, cls in sorted(classes.items()):
    if cls not in ('Material', 'MaterialInstanceConstant'):
        continue
    base = os.path.join(root, rel)
    ua, ue = open(base + '.uasset', 'rb').read(), open(base + '.uexp', 'rb').read()
    pk = k.Package(ua, ue)
    info = kh3mat.read_material(ua, ue)
    e = [x for x in pk.exports if x['outer'] == 0 and pk.class_name(x) == cls][0]
    rec = dict(cls=cls, parent=info.get('parent'))
    pr = info['props']
    for kk in ('MaterialDomain', 'BlendMode', 'ShadingModel', 'TwoSided', 'SQEXDiscernment', 'bUseMaterialAttributes',
               'BlendableLocation', 'bUsedWithSkeletalMesh', 'bUsedWithStaticMeshes', 'bTangentSpaceNormal',
               'TranslucencyLightingMode', 'OpacityMaskClipValue', 'bUsedWithMorphTargets', 'bUsedWithClothing',
               'bUsedWithParticleSprites', 'bUsedWithMeshParticles', 'bDisableDepthTest', 'bGenerateSphericalParticleNormals'):
        if kk in pr:
            rec[kk] = pr[kk]
    if 'BasePropertyOverrides' in pr:
        rec['overrides'] = pr['BasePropertyOverrides']
    if 'StaticParameters' in pr:
        rec['static'] = pr['StaticParameters']
    rec['nparams'] = (len(info['scalars']), len(info['vectors']), len(info['textures']))
    sh = kh3pick.shaders(pk)
    rec['nshaders'] = len(sh)
    rec['types'] = sorted(set('%s|%s' % (t, v) for t, v, b in sh if t and ('BasePass' in t or 'PostProcess' in t or 'Decal' in t)))
    try:
        us = kh3uniform.read_set(pk, e) if cls == 'Material' or sh else None
        rec['uset'] = [len(us[x]) for x in ('vectors', 'scalars', 'textures2d', 'texturescube')] if us else None
    except Exception as ex:
        rec['uset'] = 'ERR ' + str(ex)[:80]
    out[rel] = rec
json.dump(out, open(sys.argv[3], 'w'), indent=1)
c = collections.Counter()
for rel, r in out.items():
    key = (r['cls'], r.get('MaterialDomain', 'MD_Surface') if r['cls'] == 'Material' else '-', r.get('BlendMode', '-'), r.get('ShadingModel', '-'), 'shaders' if r['nshaders'] else 'noshaders')
    c[key] += 1
for kk, n in sorted(c.items(), key=lambda x: -x[1]):
    print(n, kk)
