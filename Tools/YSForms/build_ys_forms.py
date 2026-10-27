# The editor step of run_ys_forms.cmd (Fully Playable (Young) Sephiroth forms, Create a Character System 3.12): builds every
# move of Saved/RebirthSkelCompat/YSForms/cmd/plan.json with Create a Character System's Build Moves in an editor commandlet
# (End editor closed: an open editor renders a thumbnail of each saved move, which stopped it on 2026-10-22): YOUNG
# SEPHIROTH's Ever Crisis moves (Battle07) with Sephiroth's sounds and effects on his blows, and WINGED's moves (Battle02)
# with the transformed Sephiroth's feelers (ysf_build.py). make_container.py cooks and packs them after.
# One move at a time, each saved as it is built; progress.json says which one is being built, so a move that stops the
# editor is left out when run_ys_forms.ps1 runs this again, and the moves built already are kept.
# Results in Saved/RebirthSkelCompat/YSForms: build_result.json, progress.json, built.json.
import hashlib, json, os, time, traceback
import unreal

SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'YSForms')
RESULT = os.path.join(OUT, 'build_result.json')
results = {'steps': []}


def write_json(path, value):
    temp = path + '.tmp'
    with open(temp, 'w') as f:
        json.dump(value, f, indent=1)
    os.replace(temp, path)


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('YS FORMS BUILD %s: %s' % (key, str(value)[:2000]))
    write_json(RESULT, results)


try:
    if os.path.exists(RESULT):
        os.replace(RESULT, RESULT + '.previous')
    ns = {}
    exec(open(os.path.join(OUT, 'cmd', 'ysf_build.py')).read(), ns)
    plugin = json.load(open(os.path.join(os.path.dirname(os.path.normpath(SAVED)), 'Plugins', 'RebirthSkelCompat', 'RebirthSkelCompat.uplugin')))
    log('plugin', plugin.get('VersionName'))

    # progress of earlier commandlet runs: a move that was being built when the editor stopped is left out
    plan_md5 = hashlib.md5(open(os.path.join(OUT, 'cmd', 'plan.json'), 'rb').read()).hexdigest()
    state = ns['progress']()
    if 'commandlet_runs' not in state or state.get('plan') != plan_md5:
        state = {'done': {}, 'stopped': {}, 'commandlet_runs': 0, 'plan': plan_md5}
    state.setdefault('stopped', {})
    state['commandlet_runs'] += 1
    if state.get('current'):
        state['stopped'][state['current']] = 'stopped the editor in commandlet run %d' % (state['commandlet_runs'] - 1)
        state['current'] = None
    ns['write_json'](ns['PROGRESS'], state)
    log('run', 'run %d: %d move(s) built before, %d left out%s' % (
        state['commandlet_runs'], len([k for k, v in state['done'].items() if not v.get('error')]), len(state['stopped']),
        (': ' + ', '.join(sorted(state['stopped']))) if state['stopped'] else ''))

    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.scan_paths_synchronous(['/Game/Motion/Player/PC0010_Sephiroth', '/Game/Motion/Player/PC0010_Sephiroth_Transform',
                                     '/Game/Motion/Player/PC0010_Sephiroth_CH049', '/Game/Motion/Player/PC0000_Cloud',
                                     '/Game/RebirthSkelCompat', '/Game/Character/Player/PC0010_00_Sephiroth_Standard',
                                     '/Game/Animation/CompressionSettings'], True)
    log('setup', ns['setup']())

    keys = [m['set'] + '/' + m['name'] for m in ns['PLAN']['moves']]
    started, made = time.time(), 0
    for key in keys:
        state = ns['progress']()
        if key in state.get('stopped', {}):
            continue
        done = state.get('done', {}).get(key)
        if done and key in state.get('run_built', {}) and not done.get('error'):
            continue   # (built by an earlier run of this go, the one the editor stopped in)
        unreal.log('YS FORMS BUILD move %s' % key)
        ns['build']([key])
        state = ns['progress']()
        state.setdefault('run_built', {})[key] = state['commandlet_runs']
        ns['write_json'](ns['PROGRESS'], state)
        made += 1
    log('built_now', '%d move(s) in %.0f s' % (made, time.time() - started))

    state = ns['progress']()
    # a move whose feelers did not go on is still a good move (built again as it was): it is packed, and listed
    good = [k for k in keys if k in state['done'] and k not in state['stopped'] and
            (not state['done'][k].get('error') or state['done'][k].get('post', {}).get('rebuilt'))]
    failed = {k: (state['stopped'].get(k) or state['done'].get(k, {}).get('error', 'not built'))[:400] for k in keys
              if k not in good or state['done'].get(k, {}).get('error')}
    log('failed', failed)
    log('adjust', {k: {x: state['done'][k]['adjust'].get(x) for x in ('matched', 'of', 'placed', 'attached', 'unmatched', 'missing')}
                   for k in good if 'adjust' in state['done'][k]})
    log('post', {k: state['done'][k]['post'] for k in good if 'post' in state['done'][k]})
    paths = [ns['object_path'](ns['REAL_FOLDER'], ns['MOVES'][k]) for k in good]
    write_json(os.path.join(OUT, 'built.json'), ns['summary'](paths))
    log('described', len(paths))
    log('done', len(good))
except Exception:
    log('error', traceback.format_exc())
