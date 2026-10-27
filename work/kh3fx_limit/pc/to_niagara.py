"""(Editor link) Converts KH3 Cascade effects to Niagara systems next to them (<name>_Converted), with Epic's Cascade To
Niagara Converter (its Python in the engine's plugin folder), and saves them. ROOT / NAMES / BUDGET are filled in by
the caller; a system that already has its _Converted is left alone, so running it again goes on where it stopped."""
import time
import unreal

ROOT = __ROOT__
NAMES = __NAMES__
BUDGET = __BUDGET__
result = {}
start = time.time()
if not hasattr(unreal, 'ConvertCascadeToNiagaraResults'):
    raise RuntimeError('the Cascade To Niagara Converter plugin is not on in this editor')
import CascadeToNiagaraConverter as conv   # noqa: E402  (the plugin's Content/Python)

for name in NAMES:
    if time.time() - start > BUDGET:
        result['_stopped'] = 'time budget (%d s)' % BUDGET
        break
    src = '%s/%s' % (ROOT, name)
    target = src + '_Converted'
    if unreal.EditorAssetLibrary.does_asset_exist(target):
        result[name] = dict(ok=True, skipped='already converted')
        continue
    system = unreal.load_asset(src)
    if system is None:
        result[name] = dict(ok=False, error='not loaded')
        continue
    results = unreal.new_object(unreal.ConvertCascadeToNiagaraResults, unreal.find_object(None, '/Engine/Transient'))
    t0 = time.time()
    try:
        conv.convert_cascade_to_niagara(system, results)
        out = unreal.load_asset(target)
        saved = bool(out) and unreal.EditorAssetLibrary.save_loaded_asset(out, False)
        info = dict(ok=bool(out), saved=saved, seconds=round(time.time() - t0, 1),
                    python_error=bool(results.get_editor_property('cancelled_by_python_error')))
        if out:
            try:
                info['emitters'] = len(out.get_editor_property('emitter_handles'))
            except Exception as e:
                info['emitters'] = 'n/a'
        result[name] = info
    except Exception as e:
        result[name] = dict(ok=False, error=str(e)[:600], seconds=round(time.time() - t0, 1))
