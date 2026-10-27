# The editable AnimBlueprints' editor step (Create a Character System editor 1.19), run in an End editor commandlet
# (UE4Editor-Cmd -run=pythonscript) by run_abp_template_test.ps1: for each job in
# Saved\RebirthSkelCompat\AnimTemplate\job.json, the editable AnimBlueprint from its template for its skeleton
# (EndAnimBlueprintTemplateLibrary.MakeEditableAnimBlueprint: built, compiled, saved), then, for a job that asks,
# cooked for the game into a ~mods container (CookAnimBlueprintContainer).
# Result: Saved\RebirthSkelCompat\AnimTemplate\result.json ({"jobs": [...], "done": true}, or with "error").
import json
import os
import traceback

import unreal

SAVED = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'RebirthSkelCompat', 'AnimTemplate')
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
    lib = unreal.EndAnimBlueprintTemplateLibrary
    for job in jobs:
        entry = {'job': job}
        OUT['jobs'].append(entry)
        write()
        made = json.loads(lib.make_editable_anim_blueprint(job['template'], job['skeleton'], job['package'], bool(job.get('replace', False))))
        entry['made'] = made
        write()
        if made.get('ok') and job.get('container'):
            entry['cooked'] = json.loads(lib.cook_anim_blueprint_container(job['package'], job['container'], job['out']))
            write()
    OUT['done'] = True
    write()


try:
    main()
except Exception:
    OUT['error'] = traceback.format_exc()
    write()
