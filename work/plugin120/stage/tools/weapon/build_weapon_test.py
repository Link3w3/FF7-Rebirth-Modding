# The weapon Blueprint Maker's test (Create a Character System editor 1.20), run in an End editor commandlet
# (UE4Editor-Cmd -run=pythonscript) by run_weapon_template_test.ps1: for each job in
# Saved\RebirthSkelCompat\WeaponTemplate\job.json, the weapon Blueprint from its template holding its model
# (EndWeaponBlueprintTemplateLibrary.MakeWeaponBlueprint: made, compiled, saved), then, for a job that asks, the
# Blueprint's package cooked for the game into a test ~mods container (CookAnimBlueprintContainer cooks any package; it
# is not installed: Sandalphon checks it first).
# Result: Saved\RebirthSkelCompat\WeaponTemplate\result.json ({"jobs": [...], "templates": n, "done": true}, or "error").
import json
import os
import traceback

import unreal

SAVED = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'RebirthSkelCompat', 'WeaponTemplate')
JOB = os.path.join(SAVED, 'job.json')
RESULT = os.path.join(SAVED, 'result.json')
OUT = {'jobs': []}


def write():
    os.makedirs(SAVED, exist_ok=True)
    with open(RESULT, 'w', encoding='utf-8') as f:
        json.dump(OUT, f, indent=1)


def main():
    write()
    jobs = json.load(open(JOB, encoding='utf-8'))['jobs']
    lib = unreal.EndWeaponBlueprintTemplateLibrary
    OUT['templates'] = len(json.loads(lib.weapon_templates()))
    write()
    for job in jobs:
        entry = {'job': job}
        OUT['jobs'].append(entry)
        write()
        if job.get('cook_only'):
            # (made before: cooked as it is)
            made = {'ok': unreal.EditorAssetLibrary.does_asset_exist(job['package']), 'compile': 'made before', 'defaults': 0, 'settings': 0,
                    'components': 0, 'errors': [], 'warnings': [], 'compiler': []}
        else:
            made = json.loads(lib.make_weapon_blueprint(job['template'], job['mesh'], job['package'], bool(job.get('replace', False))))
        entry['made'] = made
        write()
        if made.get('ok') and job.get('container'):
            entry['cooked'] = json.loads(unreal.EndAnimBlueprintTemplateLibrary.cook_anim_blueprint_container(job['package'], job['container'], job['out']))
            write()
    OUT['done'] = True
    write()


try:
    main()
except Exception:
    OUT['error'] = traceback.format_exc()
    write()
