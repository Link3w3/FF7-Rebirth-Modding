"""(Editor link, once Epic's Cascade To Niagara Converter plugin is on.) Converts the KH3 Cascade effects in
/Game/KH3/w_so010/Cascade to Niagara systems next to them (<name>_Converted) and saves them. Systems that already
have a <name>_Converted are left alone, so running it again only does the ones still missing."""
import unreal

ROOT = '/Game/KH3/w_so010/Cascade'
result = {}
if not hasattr(unreal, 'ConvertCascadeToNiagaraResults'):
    raise RuntimeError('the Cascade To Niagara Converter plugin is not on in this editor')
import CascadeToNiagaraConverter as conv   # noqa: E402  (the plugin's Content/Python)

reg = unreal.AssetRegistryHelpers.get_asset_registry()
reg.scan_paths_synchronous([ROOT], True)
f = unreal.ARFilter(class_names=['ParticleSystem'], package_paths=[ROOT], recursive_paths=True)
for a in sorted(reg.get_assets(f), key=lambda a: str(a.asset_name)):
    name = str(a.asset_name)
    target = '%s_Converted' % str(a.package_name)
    if unreal.EditorAssetLibrary.does_asset_exist(target):
        result[name] = dict(ok=True, skipped='already converted')
        continue
    system = unreal.load_asset(str(a.package_name))
    results = unreal.new_object(unreal.ConvertCascadeToNiagaraResults, unreal.find_object(None, '/Engine/Transient'))
    try:
        conv.convert_cascade_to_niagara(system, results)
        out = unreal.load_asset(target)
        saved = bool(out) and unreal.EditorAssetLibrary.save_loaded_asset(out, False)
        result[name] = dict(ok=bool(out), saved=saved,
                            python_error=bool(results.get_editor_property('cancelled_by_python_error')))
    except Exception as e:
        result[name] = dict(ok=False, error=str(e)[:500])
