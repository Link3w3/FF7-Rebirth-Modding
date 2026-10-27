# REMAKE and REMAKE WINGED (Battle08, Battle09), the editor step of run_remake_forms.cmd: builds every move of
# Saved/RebirthSkelCompat/RemakeForms/cmd/plan.json with Create a Character System's Build Moves in an editor commandlet
# (End editor closed: an open editor renders a thumbnail of each saved move, which stopped it on 2026-10-22), adds Remake's
# sounds and effects from each move's carrier (rf_build.py). make_container.py cooks and packs them after.
# One move at a time, each saved as it is built; progress.json says which one is being built, so a move that stops the
# editor is left out when run_remake_forms.ps1 runs this again, and the moves built already are kept.
# Results in Saved/RebirthSkelCompat/RemakeForms: build_result.json, progress.json, built.json.
import hashlib, json, os, time, traceback
import unreal

SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'RemakeForms')
RESULT = os.path.join(OUT, 'build_result.json')
WORK = os.path.join(OUT, '_work')
results = {'steps': []}


def write_json(path, value):
    temp = path + '.tmp'
    with open(temp, 'w') as f:
        json.dump(value, f, indent=1)
    os.replace(temp, path)


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('REMAKE FORMS BUILD %s: %s' % (key, str(value)[:2000]))
    write_json(RESULT, results)


try:
    if os.path.exists(RESULT):
        os.replace(RESULT, RESULT + '.previous')
    ns = {}
    exec(open(os.path.join(OUT, 'cmd', 'rf_build.py')).read(), ns)
    plugin = json.load(open(os.path.join(os.path.dirname(os.path.normpath(SAVED)), 'Plugins', 'RebirthSkelCompat', 'RebirthSkelCompat.uplugin')))
    log('plugin', plugin.get('VersionName'))

    # progress of earlier commandlet runs: a move that was being built when the editor stopped is left out
    plan_md5 = hashlib.md5(open(os.path.join(OUT, 'cmd', 'plan.json'), 'rb').read()).hexdigest()
    state = ns['progress']()
    if 'commandlet_runs' not in state or state.get('plan') != plan_md5:
        # (a new plan, or the open editor's attempt: every move is built again)
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
    registry.scan_paths_synchronous(['/Game/GameContents/Motion/Enemy/EB0021_Sephiroth', '/Game/RebirthSkelCompat',
                                     '/Game/Character/Player/PC0010_00_Sephiroth_Standard'], True)
    log('setup', ns['setup']())

    keys = [m['set'] + '/' + m['name'] for m in ns['PLAN']['moves']]
    started, made = time.time(), 0
    for key in keys:
        state = ns['progress']()
        m = ns['MOVES'][key]
        if key in state.get('stopped', {}):
            continue
        done = state.get('done', {}).get(key)
        if done and key in state.get('run_built', {}) and not done.get('error'):
            continue   # (built by an earlier run of this go, the one the editor stopped in)
        unreal.log('REMAKE FORMS BUILD move %s' % key)
        ns['build']([key])
        state = ns['progress']()
        state.setdefault('run_built', {})[key] = state['commandlet_runs']
        ns['write_json'](ns['PROGRESS'], state)
        made += 1
    log('built_now', '%d move(s) in %.0f s' % (made, time.time() - started))

    state = ns['progress']()
    good = [k for k in keys if k in state['done'] and not state['done'][k].get('error') and k not in state['stopped']]
    failed = {k: (state['stopped'].get(k) or state['done'].get(k, {}).get('error', 'not built'))[:400] for k in keys if k not in good}
    log('failed', failed)
    log('adjust', {k: {x: state['done'][k]['adjust'].get(x) for x in ('matched', 'of', 'placed', 'attached', 'unmatched', 'missing')}
                   for k in good if 'adjust' in state['done'][k]})
    paths = [ns['object_path'](ns['REAL_FOLDER'], ns['MOVES'][k]) for k in good]
    write_json(os.path.join(OUT, 'built.json'), ns['summary'](paths))
    log('described', len(paths))

    # (the moves are cooked by the engine's cook commandlet in make_container.py: tagged properties, as Package Project cooks)
    log('done', len(good))
except Exception:
    log('error', traceback.format_exc())
