# Vincent's Galian Beast form, step 1: what the Galian boss's animations (EB2160, the game's Nibelheim fight) and the
# transformation cutscene's (EV_NIBLE_8310: Vincent and the beast) have - lengths, notifies, hits - for planning the form's
# moves and entrance. Run by run_galian_survey.cmd (End editor closed). Writes Saved\RebirthSkelCompat\GalianBeast\survey.json
import json, os, traceback
import unreal

SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'GalianBeast')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'survey_result.json')
results = {'steps': []}


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('GALIAN %s: %s' % (key, str(value)[:2000]))
    json.dump(results, open(RESULT, 'w'), indent=1)


try:
    if os.path.exists(RESULT):
        os.replace(RESULT, RESULT + '.previous')
    results = {'steps': []}
    if not hasattr(unreal.EndSkeletonCompatDataObject, 'describe_animations'):
        raise RuntimeError('this editor has no Describe Animations: build the Create a Character System plugin first')
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    motion = ['/Game/Motion/Enemy/EB2160_VincentValentine', '/Game/Cut/Game/8700-NIBLE/EV_NIBLE_8310/Motion']
    folders = motion + ['/Game/Character/Enemy/EB2160_00_VincentValentine_Standard', '/Game/Character/Player/PC0011_00_Vincent_Standard',
                        '/Game/Animation/CompressionSettings']
    registry.scan_paths_synchronous(folders, True)
    paths = []
    for folder in motion:
        for asset in registry.get_assets_by_path(folder, True):
            paths.append('%s.%s' % (asset.package_name, asset.asset_name))
    paths = sorted(set(paths))
    log('found', len(paths))
    text = unreal.EndSkeletonCompatDataObject.describe_animations(paths)
    open(os.path.join(OUT, 'survey.json'), 'w', encoding='utf-8').write(text)
    data = json.loads(text)
    log('described', '%d, %d did not load' % (len(data), sum(1 for d in data if 'error' in d)))
    log('done', True)
except Exception:
    log('error', traceback.format_exc())
