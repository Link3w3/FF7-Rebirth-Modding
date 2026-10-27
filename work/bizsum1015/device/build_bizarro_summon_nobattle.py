# Bizarro Sephiroth as a summon, in Alexander's place: builds the summon's moves with Create a Character System's move
# builder. Every animation name Alexander's summon plays (his Battle00 and Battle00_Comp sets) gets a new animation made from
# one of Bizarro Sephiroth's (on his own skeleton, with his own effects and sounds) carrying the gameplay notifies of
# Alexander's animation of that name (damage, AI messages, cancel windows, warps), lined up on its hits. The summon keeps
# Alexander's AI and abilities, so his attacks work the way Alexander's do. Run by run_bizarro_summon.cmd (editor closed).
# Plan: bizarro_summon_plan.json next to this file. Results: Saved\RebirthSkelCompat\BizarroSummon\summon_result.json,
# summon_build.txt, export_json.txt, validate.txt. Needs Create a Character System editor 1.10.1 or later.
import json, os, struct, traceback
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = json.load(open(os.path.join(HERE, 'bizarro_summon_plan.json')))
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'BizarroSummon')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'summon_result.json')
results = {'steps': []}


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('BIZARROSUMMON %s: %s' % (key, str(value)[:2000]))
    json.dump(results, open(RESULT, 'w'), indent=1)  # after every step, so a stop shows where it was


def setp(obj, names, value):
    """set_editor_property under the first name that works (Python names differ for keywords such as As)."""
    last = None
    for name in names if isinstance(names, (list, tuple)) else [names]:
        try:
            obj.set_editor_property(name, value)
            return
        except Exception as ex:
            last = ex
    raise last


def split(result):
    """A UFUNCTION with an out FString comes back as (return value, out) or just the return value."""
    if isinstance(result, tuple):
        return result[0], (result[1] if len(result) > 1 else '')
    return result, ''


# This engine's memory-mapped Anim Sequence layout: a header {frozen size, 65536, 16, padding}, the padding, two pointers
# {offset, count, max}, 16 marker bytes, then the compressed bytes and the curve bytes, each padded to 16.
MARKER = bytes([0x30, 0xAF, 0x2F, 0x90, 0x54, 0x94, 0xF4, 0x06, 0x59, 0x00, 0x49, 0x00, 0x49, 0x00, 0x53, 0x00])


def saved_animation_problem(path):
    """What is wrong with a saved Anim Sequence package, if anything: one whose recorded count and compressed bytes disagree
    stops the editor ("Unexpected array element size") and the cooker ("SerializeNum >= 0") when they load it."""
    data = open(path, 'rb').read()
    at = data.find(MARKER, 44)
    if at < 0:
        return None   # not an animation in that layout
    pointers = at - 32
    count = struct.unpack_from('<i', data, pointers + 8)[0]
    packed, curves = struct.unpack_from('<Qi', data, pointers + 16)
    curves = curves if packed >> 1 else 0

    def padded(n):
        return n + (16 - n % 16) % 16 if n > 0 else 0
    for pad in range(16):
        header = pointers - pad - 12
        if header < 0:
            break
        frozen, size, idk, padding = struct.unpack_from('<IIHH', data, header)
        if padding == pad and idk == 16 and size == 65536:
            if count < 0 or curves < 0 or frozen != 48 + padded(count) + padded(curves):
                return 'records %d compressed bytes but holds %d' % (count, frozen - 48 - padded(curves))
            return None
    return None


def broken_animations(folders):
    content = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
    broken, checked = [], 0
    for folder in folders:
        root = os.path.join(content, folder[len('/Game/'):].replace('/', os.sep))
        for dirpath, _, files in os.walk(root):
            for name in sorted(files):
                if name.endswith('.uasset'):
                    path = os.path.join(dirpath, name)
                    checked += 1
                    problem = saved_animation_problem(path)
                    if problem:
                        broken.append('%s (%s)' % (os.path.relpath(path, content), problem))
    return checked, broken


try:
    if os.path.exists(RESULT):
        os.replace(RESULT, RESULT + '.previous')
    results = {'steps': []}

    # 1. The asset registry knows the folders the build looks in (a commandlet does not scan everything first).
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    folders = ['/Game/Motion/Enemy/EB2210_BizarroSephiroth', '/Game/Motion/Summon/SU2030_Alexander',
               '/Game/Character/Enemy/EB2210_00_BizarroSephiroth_Standard', '/Game/Character/Summon/SU2030_00_Alexander_Standard',
               '/Game/RebirthSkelCompat', '/Game/Animation/CompressionSettings']
    registry.scan_paths_synchronous(folders, True)
    log('scanned', folders)
    if not hasattr(unreal.EndSkeletonCompatDataObject, 'import_key_animations'):
        raise RuntimeError('this editor has an older Create a Character System: build the plugin (1.10.1 or later) first')

    # 2. The data object (made once, then updated).
    path = PLAN['data_object']
    folder, name = path.rsplit('/', 1)
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        data = unreal.EditorAssetLibrary.load_asset(path)
        log('data_object', 'loaded ' + path)
    else:
        data = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.EndSkeletonCompatDataObject, None)
        log('data_object', 'created ' + path)
    if data is None:
        raise RuntimeError('the data object could not be made')

    # 3. The animation set row: the summon's character (Alexander's row), Bizarro's skeleton, the moves.
    row = unreal.EndAnimSetRow()
    setp(row, ['enabled', 'b_enabled'], True)
    setp(row, 'characters', PLAN['characters'])
    skeleton = unreal.load_asset(PLAN['character_skeleton'])
    if skeleton is None:
        raise RuntimeError('does not load: ' + PLAN['character_skeleton'])
    setp(row, 'character_skeleton', skeleton)
    setp(row, 'build_folder', PLAN['build_folder'])
    setp(row, 'requires_paks', PLAN['requires_paks'])
    moves = []
    for item in PLAN['moves']:
        move = unreal.EndAnimSetMove()
        setp(move, 'name', item['name'])
        setp(move, 'set', item['set'])
        setp(move, 'animation', item['animation'])
        setp(move, ['build', 'b_build'], bool(item['build']))
        if item['build']:
            setp(move, 'notifies_from', item['notifies_from'])
            setp(move, 'retarget', unreal.EndMoveRetarget.AS_IS)
            setp(move, ['keep_source_effects', 'b_keep_source_effects'], True)
            hits = []
            for t in item.get('hits', []):
                hit = unreal.EndMoveHit()
                setp(hit, 'time', float(t))
                hits.append(hit)
            setp(move, 'hits', hits)
        moves.append(move)
    setp(row, 'moves', moves)
    setp(data, 'animation_sets', [row])
    setp(data, 'build_chunk', PLAN['build_chunk'])
    game_dir = unreal.DirectoryPath()
    setp(game_dir, 'path', '')
    setp(data, 'game_directory', game_dir)   # the compat file goes to Saved; it is installed with the pak
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)
    log('row', '%d moves (%d to build)' % (len(moves), sum(1 for m in PLAN['moves'] if m['build'])))

    # 4. Build every move with Build on, one at a time (each with its own report).
    lines, built, failed = [], 0, []
    for item in PLAN['moves']:
        if not item['build']:
            continue
        ok, report = split(data.build_one_move(0, item['name'], item['set']))
        lines.append(report.strip())
        if ok:
            built += 1
        else:
            failed.append(item['name'])
    open(os.path.join(OUT, 'summon_build.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    total = sum(1 for m in PLAN['moves'] if m['build'])
    log('failed', failed)
    log('build', '%d of %d built%s' % (built, total, (', not built: ' + ', '.join(failed)) if failed else ''))
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)

    # Every built animation loads back (the cooker would stop on one this engine saved broken).
    checked, broken = broken_animations([PLAN['build_folder']])
    log('checked', '%d package(s), %s' % (checked, ('%d BROKEN: ' % len(broken)) + '; '.join(broken[:8]) if broken else 'all load back'))
    if broken:
        raise RuntimeError('%d saved animation(s) would stop the cooker: %s' % (len(broken), '; '.join(broken)))

    # 5. The compat file (a reference: the installed one is made from it) and the checks.
    for function, label in (('ExportJson', 'export_json'), ('Validate', 'validate')):
        try:
            data.call_method(function)
            report = data.get_editor_property('last_result')
        except Exception as ex:
            report = 'call_method %s failed (%s)' % (function, ex)
        open(os.path.join(OUT, label + '.txt'), 'w', encoding='utf-8').write(report)
        log(label, report.split('\n', 1)[0])
    log('done', built == total)   # packaging goes on only when every move was built
except Exception:
    log('error', traceback.format_exc())
