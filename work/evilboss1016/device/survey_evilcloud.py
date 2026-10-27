# Evil Cloud's boss fights, step 1: what the boss Sephiroth's animations (PC0010_Sephiroth_Transform: the final battle's and
# the VR fights' Sephiroth) and Cloud's animations have (lengths, notifies, hits, the sets' names), for planning Evil Cloud's
# moves (Cloud's moves on the boss's timing and damage). Run by run_evilcloud_survey.cmd (End editor closed).
# Writes Saved\RebirthSkelCompat\EvilCloudBoss\survey.json (and survey_result.json: how it went). Nothing is changed.
import json, os, traceback
import unreal

SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'EvilCloudBoss')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'survey_result.json')
results = {'steps': []}


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('EVILCLOUD %s: %s' % (key, str(value)[:2000]))
    json.dump(results, open(RESULT, 'w'), indent=1)


try:
    if os.path.exists(RESULT):
        os.replace(RESULT, RESULT + '.previous')
    results = {'steps': []}
    if not hasattr(unreal.EndSkeletonCompatDataObject, 'describe_animations'):
        raise RuntimeError('this editor has no Describe Animations: build the Create a Character System plugin 1.10.2 or later first')
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    # the battle animations (Cloud's field, mount and event folders are left out) and the sets at the folders' tops
    roots = ['/Game/Motion/Player/PC0010_Sephiroth_Transform', '/Game/Motion/Player/PC0000_Cloud']
    battle = ['/Game/Motion/Player/PC0010_Sephiroth_Transform/Battle00', '/Game/Motion/Player/PC0010_Sephiroth_Transform/Battle00_Comp',
              '/Game/Motion/Player/PC0010_Sephiroth_Transform/Battle01', '/Game/Motion/Player/PC0000_Cloud/Battle00',
              '/Game/Motion/Player/PC0000_Cloud/Battle01']
    folders = roots + ['/Game/Character/Player/PC0010_00_Sephiroth_Standard', '/Game/Character/Player/PC0000_00_Cloud_Standard',
                       '/Game/Animation/CompressionSettings']
    registry.scan_paths_synchronous(folders, True)
    paths = []
    for folder in battle:
        for asset in registry.get_assets_by_path(folder, True):
            paths.append('%s.%s' % (asset.package_name, asset.asset_name))
    for folder in roots:
        for asset in registry.get_assets_by_path(folder, False):
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
