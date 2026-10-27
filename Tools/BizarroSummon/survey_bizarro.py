# Bizarro Sephiroth summon, step 1: what Bizarro's and Alexander's animations have (lengths, notifies, hits), for planning
# the summon's moves. Run by run_bizarro_survey.cmd (editor closed). Writes Saved\RebirthSkelCompat\BizarroSummon\survey.json
import json, os, traceback
import unreal

SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'BizarroSummon')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'survey_result.json')
results = {'steps': []}


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('BIZARRO %s: %s' % (key, str(value)[:2000]))
    json.dump(results, open(RESULT, 'w'), indent=1)


try:
    if os.path.exists(RESULT):
        os.replace(RESULT, RESULT + '.previous')
    results = {'steps': []}
    if not hasattr(unreal.EndSkeletonCompatDataObject, 'describe_animations'):
        raise RuntimeError('this editor has no Describe Animations: build the Create a Character System plugin 1.10.2 first')
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    motion = ['/Game/Motion/Enemy/EB2210_BizarroSephiroth', '/Game/Motion/Summon/SU2030_Alexander']
    folders = motion + ['/Game/Character/Enemy/EB2210_00_BizarroSephiroth_Standard', '/Game/Character/Summon/SU2030_00_Alexander_Standard',
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
