# Cook Young Sephiroth's model with its hair core and the core's material instance for the game (Create a Character
# System's Cook For Game): PC0010_13 (mesh) and PC0010_13_HairCore (material instance), to
# Saved/ModExtract/ys13/cook3/End/Content. Everything else the mesh uses is already in YoungSephiroth_P (skeleton,
# Bonamik, wing Bonamik, the fixed KineDriver, his other material instances and textures) or the game's: listed, not
# cooked. Checks first that nothing is unsaved. Writes nothing in Content.
import unreal, json, os
HERE = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'ModExtract', 'ys13')
OUT = os.path.join(HERE, 'cook3', 'End', 'Content')
EAL = unreal.EditorAssetLibrary
AR = unreal.AssetRegistryHelpers.get_asset_registry()
YS = '/Game/Character/Player/PC0010_13_Young_Sephiroth/'
pk = [YS + 'Model/PC0010_13', YS + 'Material/PC0010_13_HairCore']
out = {'packages': pk}
dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
assert not dirty, 'unsaved: ' + ', '.join(dirty)
opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=False, include_hard_package_references=True,
                                             include_searchable_names=False, include_soft_management_references=False,
                                             include_hard_management_references=False)
deps = {}
for p in pk:
    deps[p] = sorted(str(d) for d in (AR.get_dependencies(p, opts) or []) if not str(d).startswith('/Script/'))
out['deps'] = deps
mi = unreal.load_asset(YS + 'Material/PC0010_13_HairCore')
out['core_mi'] = dict(parent=mi.get_editor_property('parent').get_path_name().split('.')[0],
                      textures={str(tp.get_editor_property('parameter_info').get_editor_property('name')):
                                tp.get_editor_property('parameter_value').get_path_name().split('.')[0]
                                for tp in mi.get_editor_property('texture_parameter_values')})
r = unreal.EndSkeletonCompatDataObject.cook_packages_for_game(pk, OUT)
out['cook'] = r
files = []
for dp, dn, fn in os.walk(OUT):
    for f in fn:
        files.append([os.path.relpath(os.path.join(dp, f), OUT).replace('\\', '/'), os.path.getsize(os.path.join(dp, f))])
out['files'] = sorted(files)
json.dump(out, open(os.path.join(HERE, 'cook3.out'), 'w'), indent=1)
result = json.dumps(out, indent=1)
