"""Names for Crisis Core zen import indices: package imports hash '/game/<path>/<name>' (lowercase, '.' -> '/'),
script imports hash '/script/<module>/<class>'. Built from the container file lists."""
import os, sys, struct, json
sys.path.insert(0, os.path.expanduser('~/tools/py'))
from cityhash import CityHash64
HERE = os.path.dirname(os.path.abspath(__file__))
def h(path):
    s = path.replace('.', '/').replace(':', '/').lower()
    return CityHash64(s.encode('utf-16-le')) & ~(3 << 62)
SCRIPT = {
 'CoreUObject': ['Object', 'Class', 'Package', 'ScriptStruct', 'Function', 'Enum'],
 'Engine': ['SkeletalMesh', 'Skeleton', 'PhysicsAsset', 'SkeletalBodySetup', 'BodySetup', 'PhysicsConstraintTemplate', 'MaterialInstanceConstant',
            'Material', 'MaterialFunction', 'Texture2D', 'TextureCube', 'AnimSequence', 'SkeletalMeshSocket', 'AssetUserData', 'SubsurfaceProfile',
            'BlueprintGeneratedClass', 'SkeletalMeshComponent', 'SceneComponent', 'Actor', 'AnimBlueprintGeneratedClass', 'CurveFloat', 'AnimMontage',
            'PoseAsset', 'BlendSpace', 'AnimNotify', 'AnimNotifyState', 'SkeletalMeshLODSettings', 'MaterialInstanceDynamic', 'StaticMesh',
            'SimpleConstructionScript', 'SCS_Node', 'Default__SkeletalMesh', 'Default__Skeleton', 'Default__PhysicsAsset', 'Default__SkeletalBodySetup',
            'Default__PhysicsConstraintTemplate', 'Default__MaterialInstanceConstant', 'Default__Texture2D', 'Default__AnimSequence',
            'Default__SkeletalMeshSocket', 'NodeMappingContainer', 'Default__NodeMappingContainer', 'MaterialExpression', 'ClothingAssetBase'],
}
def build(lists_dir):
    m = {}
    for fn in os.listdir(lists_dir):
        if not fn.endswith('.txt') or fn == 'all.txt':
            continue
        for line in open(os.path.join(lists_dir, fn), encoding='utf-8', errors='replace'):
            parts = line.split()
            if not parts: continue
            p = parts[-1]
            if not p.endswith('.uasset') and not p.endswith('.umap'): continue
            if '/Content/' in p:
                rel = p.split('/Content/', 1)[1].rsplit('.', 1)[0]
                root = '/Engine/' if '/Engine/Content/' in p else '/Game/'
                pkg = root + rel
            else:
                continue
            name = pkg.rsplit('/', 1)[1]
            m[h(pkg)] = pkg
            m[h(pkg + '.' + name)] = pkg + '.' + name
            m[h(pkg + '.' + name + '_C')] = pkg + '.' + name + '_C'
            m[h(pkg + '.Default__' + name + '_C')] = pkg + '.Default__' + name + '_C'
    for mod, classes in SCRIPT.items():
        m[h('/Script/' + mod)] = '/Script/' + mod
        for c in classes:
            m[h('/Script/%s.%s' % (mod, c))] = '/Script/%s.%s' % (mod, c)
    return m
_cache = None
def names():
    global _cache
    if _cache is None:
        p = os.path.join(HERE, 'ccnames_cache.json')
        if os.path.exists(p):
            _cache = {int(k): v for k, v in json.load(open(p)).items()}
        else:
            _cache = build(os.path.join(HERE, '..', 'lists'))
            json.dump({str(k): v for k, v in _cache.items()}, open(p, 'w'))
    return _cache
def imp(v):
    t = v >> 62
    if t == 3: return None
    idx = v & ~(3 << 62)
    s = names().get(idx)
    kind = {0: 'export', 1: 'script', 2: 'pkg'}[t]
    return '%s:%s' % (kind, s if s else '#%016x' % idx)
