# Cook Young Sephiroth's model and the Nameless for the game (Create a Character System's Cook For Game):
# PC0010_13 (mesh, skeleton, Bonamik, 6 materials, 16 textures) and WE1021_49 (mesh, skeleton, material, 4 textures), to
# Saved/ModExtract/ys13/cook1/End/Content. Checks first that nothing is unsaved and that everything they depend on is
# either in this list or outside the project's own folders (the game's). Writes nothing in Content.
import unreal, json, os
HERE = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'ModExtract', 'ys13')
OUT = os.path.join(HERE, 'cook1', 'End', 'Content')
EAL = unreal.EditorAssetLibrary
AR = unreal.AssetRegistryHelpers.get_asset_registry()
YS = '/Game/Character/Player/PC0010_13_Young_Sephiroth/'
NM = '/Game/Character/Weapon/WE1021_49_Nameless/'
pk = [YS + 'Model/PC0010_13', YS + 'Model/PC0010_13_Skeleton', YS + 'Model/PC0010_13_BNM'] + \
     [YS + 'Material/PC0010_13_' + n for n in ('Body', 'Head', 'Hair', 'Eyelash', 'EyeShadow', 'Eye')] + \
     [a.split('.')[0] for a in EAL.list_assets(YS + 'Texture', recursive=False, include_folder=False)] + \
     [NM + 'Model/WE1021_49', NM + 'Model/WE1021_49_Skeleton', NM + 'Material/WE1021_49_Body'] + \
     [NM + 'Texture/WE1021_49_Body_' + n for n in ('C', 'N', 'Mr', 'Mg')]
out = {'packages': len(pk)}
dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
bad = [d for d in dirty if d in pk]
assert not bad, 'unsaved: ' + ', '.join(bad)
# hard dependencies: ours or the game's
opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=False, include_hard_package_references=True,
                                             include_searchable_names=False, include_soft_management_references=False,
                                             include_hard_management_references=False)
deps, outside = {}, set()
for p in pk:
    ds = [str(d) for d in (AR.get_dependencies(p, opts) or [])]
    deps[p] = ds
    for d in ds:
        if d in pk or d.startswith('/Script/') or d.startswith('/Engine/'):
            continue
        outside.add(d)
out['outside'] = sorted(outside)
mine = [d for d in outside if d.startswith(YS) or d.startswith(NM) or '/PC0010_10_Young_Sephiroth' in d or '/Shader/' in d or '/CH049' in d]
assert not mine, 'depends on project-only assets not cooked here: ' + ', '.join(mine)
r = unreal.EndSkeletonCompatDataObject.cook_packages_for_game(pk, OUT)
out['cook'] = r
files = []
for dp, dn, fn in os.walk(OUT):
    for f in fn:
        files.append(os.path.relpath(os.path.join(dp, f), OUT).replace('\\', '/'))
out['files'] = sorted(files)
json.dump(deps, open(os.path.join(HERE, 'cook1_deps.json'), 'w'), indent=1)
result = json.dumps(out, indent=1)
