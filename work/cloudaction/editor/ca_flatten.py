# step 2: Flatten Root's animation pass over the new imports (they were made on the keys of Sora's skeleton as it was before
# its root was flattened, like every earlier import of his): the plugin's own pass, run on the index ranges of its sorted
# list (additive last, then by object path as FName sorts) that hold the new ones; K = the most to run in this call.
import re
ar = unreal.AssetRegistryHelpers.get_asset_registry()
sk = unreal.load_asset(SKEL)
tag = "Skeleton'%s'" % sk.get_path_name()
found = [a for a in ar.get_assets(unreal.ARFilter(class_names=['AnimSequence'], recursive_classes=True))
         if str(a.get_tag_value('Skeleton')) == tag]


def fname_key(s):
    m = re.match(r'^(.*)_(0|[1-9][0-9]{0,8})$', s)
    return (m.group(1).lower(), int(m.group(2)) + 1) if m else (s.lower(), 0)


def additive(a):
    t = str(a.get_tag_value('AdditiveAnimType') or '')
    return t not in ('', 'AAT_None', 'None')


found.sort(key=lambda a: (additive(a), fname_key(str(a.object_path))))
paths = [str(a.object_path) for a in found]
new = set(s for k in range(len(JOBS)) for c, s in pairs(k))
idx = sorted(i for i, p in enumerate(paths) if p in new)
missing = sorted(new - set(paths))
done_meta = lambda p: bool(unreal.EditorAssetLibrary.get_metadata_tag(unreal.load_asset(p), 'CaC.FlattenRoot.Done'))
todo = [i for i in idx if not done_meta(paths[i])]
out = dict(skeleton_anims=len(paths), new=len(new), in_registry=len(idx), not_in_registry=missing[:5], todo=len(todo))
# contiguous ranges of what is left, at most K animations in this call
ranges, budget = [], K
for i in todo:
    if budget <= 0:
        break
    if ranges and i <= ranges[-1][1] + 1:
        ranges[-1][1] = i
    else:
        ranges.append([i, i])
    budget -= 1
reports = []
for a, b in ranges:
    first, count = max(a - 2, 0), (b - a + 1) + 4
    r = LIB.flatten_skeleton_root(SKEL, {}, True, first, count)
    reports.append('[%d +%d] %s' % (first, count, r.strip().splitlines()[-1][:200] if r.strip() else ''))
out['ranges'] = ranges
out['reports'] = reports
out['left'] = sum(1 for i in todo if not done_meta(paths[i]))
result = json.dumps(out, indent=1)
