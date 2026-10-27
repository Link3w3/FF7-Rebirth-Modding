# which animations sit next to the new ones in Flatten Root's order (the pass took one of them too)
import re
ar = unreal.AssetRegistryHelpers.get_asset_registry()
sk = unreal.load_asset(SKEL)
tag = "Skeleton'%s'" % sk.get_path_name()
found = [a for a in ar.get_assets(unreal.ARFilter(class_names=['AnimSequence'], recursive_classes=True)) if str(a.get_tag_value('Skeleton')) == tag]
def fname_key(s):
    m = re.match(r'^(.*)_(0|[1-9][0-9]{0,8})$', s)
    return (m.group(1).lower(), int(m.group(2)) + 1) if m else (s.lower(), 0)
def additive(a):
    t = str(a.get_tag_value('AdditiveAnimType') or '')
    return t not in ('', 'AAT_None', 'None')
found.sort(key=lambda a: (additive(a), fname_key(str(a.object_path))))
paths = [str(a.object_path) for a in found]
new = set(s for k in range(len(JOBS)) for c, s in pairs(k))
out = []
for i in list(range(0, 3)) + list(range(100, 106)) + list(range(550, 560)) + list(range(764, 774)) + list(range(2194, 2202)) + list(range(2318, 2326)):
    p = paths[i]
    a = unreal.load_asset(p)
    out.append('%d %s %s done=%s' % (i, 'NEW' if p in new else 'old', p, unreal.EditorAssetLibrary.get_metadata_tag(a, 'CaC.FlattenRoot.Done')[:12]))
result = '\n'.join(out)
