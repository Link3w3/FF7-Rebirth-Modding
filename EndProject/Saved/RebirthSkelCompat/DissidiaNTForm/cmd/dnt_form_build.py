# DISSIDIA NT (Battle12): Dissidia NT Sephiroth's motions (retargeted onto Rebirth Sephiroth's skeleton,
# /Game/Motion/Player/PC0010_19_DissidiaNT_Sephiroth/DNTRoot) as his player moves, built in the End editor with Create a
# Character System's Build Moves, in an editor commandlet (build_dnt_form.py): setup(), then build([...]) per move.
# (Made from the CRISIS CORE form's cc_build.py: the same steps, its own data object, folders and plan.)
#
# Each move is built twice from the same Dissidia NT animation:
#   row 0, the move itself (Built/SephirothForms/<set>/<name>): Rebirth Sephiroth's gameplay notifies (damage, combo and
#          cancel windows, states) from Notifies From, its damage re-timed onto Dissidia NT's blows;
#   row 1, a carrier (Built/DissidiaNTFormCarriers/<set>/<name>): one hit per sound and effect the move adds (trails, swing sounds) (no
#          damage), so the plugin writes their notifies with the links to the game's sound bank and effects.
# The carrier's effects then get their placement (location and rotation offsets) and its sounds their attach bone, and
# Copy Notifies Onto puts them on the move (and saves it the plugin's way). Nothing is duplicated (DuplicateAsset of an
# FBX-imported animation stopped this editor on 2026-10-22).
import json, os, re, struct, time, traceback
import unreal

SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
CONTENT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'DissidiaNTForm')
PLAN = json.load(open(os.path.join(OUT, 'cmd', 'plan.json')))
PROGRESS = os.path.join(OUT, 'progress.json')
DATA_PATH = '/Game/RebirthSkelCompat/DissidiaNTForm/DissidiaNTForm_Data'
REAL_FOLDER = '/Game/RebirthSkelCompat/Built/SephirothForms'
CARRIER_FOLDER = '/Game/RebirthSkelCompat/Built/DissidiaNTFormCarriers'
SKELETON = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00_Skeleton.PC0010_00_Skeleton'
CHARACTERS = ['/Game/DataAsset/Game/CharaSpec/CharaSpec_PC0000_00_Cloud_Standard.CharaSpec_PC0000_00_Cloud_Standard']
SOURCES = [('/Game/Motion/Player/PC0010_Sephiroth/Battle00.Battle00', 'Battle12')]
MOVES = {m['set'] + '/' + m['name']: m for m in PLAN['moves']}
EFFECT_CLASS = 'AnimNotifyState_EndTimedNiagaraEffect'
SOUND_CLASSES = ('EndAnimNotifyPlayCharacterSound', 'EndAnimNotifyPlayWeaponSound')


def write_json(path, value):
    temp = path + '.tmp'
    with open(temp, 'w') as f:
        json.dump(value, f, indent=1)
    os.replace(temp, path)


def setp(obj, names, value):
    last = None
    for name in names if isinstance(names, (list, tuple)) else [names]:
        try:
            obj.set_editor_property(name, value)
            return
        except Exception as ex:
            last = ex
    raise last


def split(result):
    if isinstance(result, tuple):
        return result[0], (result[1] if len(result) > 1 else '')
    return result, ''


def object_path(folder, m):
    return '%s/%s/%s.%s' % (folder, m['set'], m['name'], m['name'])


def package_file(folder, m):
    return os.path.join(CONTENT, folder[len('/Game/'):].replace('/', os.sep), m['set'], m['name'] + '.uasset')


def extras_of(m):
    """The move's sounds and effects in time order, each once."""
    seen, out = set(), []
    for e in sorted(m.get('extras', []), key=lambda e: e['time']):
        key = (e['kind'], round(e['time'], 3), e.get('effect', ''), e.get('socket', ''), e.get('cue', ''),
               tuple(e.get('loc') or ()), tuple(e.get('rot') or ()))
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


def make_move(m, carrier):
    move = unreal.EndAnimSetMove()
    setp(move, 'name', m['name'])
    setp(move, 'set', m['set'])
    setp(move, 'animation', m['animation'])
    setp(move, ['build', 'b_build'], True)
    setp(move, 'retarget', unreal.EndMoveRetarget.PROPORTIONS)
    hits = []
    if carrier:
        # its own animation as Notifies From: the Dissidia NT key animations have no notifies, so the carrier has only the hits' own
        setp(move, 'notifies_from', m['animation'])
        setp(move, ['keep_source_effects', 'b_keep_source_effects'], False)
        for e in extras_of(m):
            hit = unreal.EndMoveHit()
            setp(hit, 'time', float(e['time']))
            if e['kind'] == 'effect':
                on = e.get('on', 'Character')
                setp(hit, 'effect', e['effect'])
                setp(hit, 'effect_socket', e['socket'])
                setp(hit, 'effect_on', unreal.EndMoveEffectAttach.WEAPON if on.startswith('Weapon') else unreal.EndMoveEffectAttach.CHARACTER)
                setp(hit, 'effect_time', max(0.01, float(e.get('duration', 0.3))))
                if on.startswith('Weapon') and on[6:].isdigit():
                    setp(hit, 'weapon', int(on[6:]))
            else:
                setp(hit, 'sound_bank', e['bank'])
                setp(hit, 'sound', e['cue'])
                setp(hit, 'effect_on', unreal.EndMoveEffectAttach.CHARACTER)   # a character sound
            hits.append(hit)
    else:
        setp(move, 'notifies_from', m['notifies_from'])
        setp(move, ['keep_source_effects', 'b_keep_source_effects'], True)
        for h in m.get('hits', []):
            hit = unreal.EndMoveHit()
            setp(hit, 'time', float(h['time']))
            if h.get('window'):
                setp(hit, 'window', float(h['window']))
            if h.get('damage'):
                setp(hit, 'damage_source_id', h['damage'])
            hits.append(hit)
    setp(move, 'hits', hits)
    if m.get('clip'):
        setp(move, 'clip_start', float(m['clip'][0]))
        setp(move, 'clip_end', float(m['clip'][1]))
    if m.get('speed'):
        setp(move, 'speed', float(m['speed']))
    return move


def make_row(folder, moves, skeleton):
    row = unreal.EndAnimSetRow()
    setp(row, ['enabled', 'b_enabled'], True)
    setp(row, 'characters', CHARACTERS)
    sources = []
    for path, as_ in SOURCES:
        source = unreal.EndAnimSetSource()
        setp(source, 'path', path)
        setp(source, ['as_', 'as', 'As'], as_)
        sources.append(source)
    setp(row, 'battle', sources)
    setp(row, 'character_skeleton', skeleton)
    setp(row, 'build_folder', folder)
    setp(row, 'moves', moves)
    return row


def load_data():
    if unreal.EditorAssetLibrary.does_asset_exist(DATA_PATH):
        return unreal.EditorAssetLibrary.load_asset(DATA_PATH)
    return None


def progress():
    try:
        return json.load(open(PROGRESS))
    except Exception:
        return {'done': {}}


def setup():
    """The data object: row 0 the moves, row 1 their carriers."""
    skeleton = unreal.load_asset(SKELETON)
    if skeleton is None:
        raise RuntimeError('the character skeleton does not load: ' + SKELETON)
    data = load_data()
    made = data is None
    if made:
        folder, name = DATA_PATH.rsplit('/', 1)
        data = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.EndSkeletonCompatDataObject, None)
    if data is None:
        raise RuntimeError('the data object could not be made')
    real = [make_move(m, False) for m in PLAN['moves']]
    carriers = [make_move(m, True) for m in PLAN['moves'] if extras_of(m)]
    setp(data, 'animation_sets', [make_row(REAL_FOLDER, real, skeleton), make_row(CARRIER_FOLDER, carriers, skeleton)])
    setp(data, 'build_chunk', 0)   # no Primary Asset Label: these are cooked with Cook For Game, not Package Project
    game_dir = unreal.DirectoryPath()
    setp(game_dir, 'path', '')
    setp(data, 'game_directory', game_dir)
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)
    return {'data_object': ('made ' if made else 'updated ') + DATA_PATH, 'moves': len(real), 'carriers': len(carriers)}


def _text_field(text, field):
    found = re.search(field + r'=("?)([^,")]*)\1', text)
    return found.group(2) if found else ''


def adjust_carrier(m):
    """The plan's placement on the carrier's effects and the attach bone on its sounds (in memory; saved below).

    Each carrier notify is matched to its sound or effect by what it is: Describe Animations gives every notify of the
    carrier in the order of its Notifies array (the order AnimationLibrary returns them in) with its class and settings
    (the effect's template and socket, the sound's name), and the nearest time picks among equal ones."""
    path = object_path(CARRIER_FOLDER, m)
    anim = unreal.load_asset(path)
    if anim is None:
        return {'error': 'the carrier does not load'}
    described = json.loads(unreal.EndSkeletonCompatDataObject.describe_animations([path]))[0].get('notifies', [])
    events = list(unreal.AnimationLibrary.get_animation_notify_events(anim))
    if len(described) != len(events):
        return {'error': 'the carrier has %d notifies but Describe Animations lists %d' % (len(events), len(described))}
    extras = extras_of(m)
    used = [False] * len(extras)
    placed, attached, matched, unmatched = 0, 0, 0, []

    def nearest(kind, when, same):
        best, gap = -1, 0.05
        for k, e in enumerate(extras):
            if not used[k] and e['kind'] == kind and same(e) and abs(e['time'] - when) < gap:
                best, gap = k, abs(e['time'] - when)
        return best

    for event, info in zip(events, described):
        notify = event.get_editor_property('notify_state_class') or event.get_editor_property('notify')
        kind = notify.get_class().get_name() if notify else ''
        when = float(info.get('time', 0.0))
        if kind != info.get('class'):
            unmatched.append('%s %.3f (described as %s)' % (kind or 'none', when, info.get('class')))
            continue
        settings = info.get('settings', {})
        if kind == EFFECT_CLASS:
            text = settings.get('m_NiagaraCreateParams', '')
            template = _text_field(text, 'm_Template').lower()
            socket = _text_field(text, 'm_SocketName').lower()
            pick = nearest('effect', when, lambda e: e['effect'].lower() == template and e['socket'].lower() == socket)
            if pick < 0:
                unmatched.append('%s %.3f %s @%s' % (kind, when, template.rsplit('.', 1)[-1], socket))
                continue
            used[pick] = True
            matched += 1
            e = extras[pick]
            if e.get('loc') or e.get('rot'):
                params = notify.get_editor_property('m_niagara_create_params')
                if e.get('loc'):
                    x, y, z = (float(v) for v in e['loc'])
                    params.set_editor_property('m_location_offset', unreal.Vector(x, y, z))
                if e.get('rot'):
                    pitch, yaw, roll = (float(v) for v in e['rot'])
                    params.set_editor_property('m_rotation_offset', unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw))
                notify.set_editor_property('m_niagara_create_params', params)
                placed += 1
        elif kind in SOUND_CLASSES:
            cue = settings.get('SoundName') or str(notify.get_editor_property('sound_name'))
            pick = nearest('sound', when, lambda e: e['cue'] == cue)
            if pick < 0:
                unmatched.append('%s %.3f %s' % (kind, when, cue))
                continue
            used[pick] = True
            matched += 1
            if extras[pick].get('attach'):
                notify.set_editor_property('attach_point_name', extras[pick]['attach'])
                attached += 1
        else:
            unmatched.append('%s %.3f' % (kind or 'none', when))
    missing = ['%s %.3f %s' % (e['kind'], e['time'], e.get('cue') or e.get('effect', '').rsplit('.', 1)[-1])
               for k, e in enumerate(extras) if not used[k]]
    return {'matched': matched, 'of': len(extras), 'placed': placed, 'attached': attached, 'unmatched': unmatched, 'missing': missing}


# This engine's memory-mapped Anim Sequence layout: a saved animation whose recorded count and compressed bytes disagree
# stops the editor and the cooker when they load it, so every saved file is checked (as build_evilcloud_boss.py does).
MARKER = bytes([0x30, 0xAF, 0x2F, 0x90, 0x54, 0x94, 0xF4, 0x06, 0x59, 0x00, 0x49, 0x00, 0x49, 0x00, 0x53, 0x00])
ACL_TAG = struct.pack('<I', 0xAC10AC10)


def saved_problem(path):
    if not os.path.exists(path):
        return 'not saved'
    data = open(path, 'rb').read()
    at = data.find(MARKER, 44)
    if at < 0:
        return 'no compressed data'
    if data.find(ACL_TAG, at + 16, at + 64) < 0:
        return 'not ACL'
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


def build(keys):
    """Builds the moves `keys` ("Battle12/B_NAttack01_0", ...): the move, its carrier, the carrier's notifies onto it."""
    data = load_data()
    if data is None:
        raise RuntimeError('run setup() first')
    state = progress()
    out = {}
    for key in keys:
        m = MOVES[key]
        entry = {'started': time.time()}
        state['current'] = key
        write_json(PROGRESS, state)
        try:
            _build_one(data, m, entry)
        except Exception:
            entry['error'] = traceback.format_exc()[-1500:]
        entry['seconds'] = round(time.time() - entry.pop('started'), 1)
        state.setdefault('done', {})[key] = entry
        state['current'] = None
        write_json(PROGRESS, state)
        out[key] = entry
    return out


def _build_one(data, m, entry):
    ok, report = split(data.build_one_move(0, m['name'], m['set']))
    report = report or str(data.get_editor_property('last_result'))   # (the report as Last Result for scripts)
    entry['move'] = {'ok': bool(ok), 'report': ' | '.join(l for l in report.strip().split('\n') if l.strip())[:1500]}
    problem = saved_problem(package_file(REAL_FOLDER, m))
    if not ok or problem:
        entry['error'] = 'the move: ' + (problem or 'the build reported an error')
    elif extras_of(m):
        ok2, report2 = split(data.build_one_move(1, m['name'], m['set']))
        report2 = report2 or str(data.get_editor_property('last_result'))
        entry['carrier'] = {'ok': bool(ok2), 'report': ' | '.join(l for l in report2.strip().split('\n') if l.strip())[:1500]}
        if not ok2 or saved_problem(package_file(CARRIER_FOLDER, m)):
            entry['error'] = 'the carrier: ' + (saved_problem(package_file(CARRIER_FOLDER, m)) or 'the build reported an error')
        else:
            entry['adjust'] = adjust_carrier(m)
            carrier = unreal.load_asset(object_path(CARRIER_FOLDER, m))
            unreal.EditorAssetLibrary.save_loaded_asset(carrier, False)
            problem = saved_problem(package_file(CARRIER_FOLDER, m))
            if problem:
                entry['error'] = 'the carrier as saved: ' + problem
            else:
                copied = unreal.EndSkeletonCompatDataObject.copy_notifies_onto(
                    [object_path(CARRIER_FOLDER, m)], [object_path(REAL_FOLDER, m)], False)
                entry['copy'] = ' | '.join(l for l in copied.strip().split('\n') if l.strip())[:800]
                problem = saved_problem(package_file(REAL_FOLDER, m))
                if problem:
                    entry['error'] = 'the move after the copy: ' + problem


def summary(paths):
    """What the built moves hold: length, damage hits, and every sound and effect (time, what, where)."""
    out = {}
    for item in json.loads(unreal.EndSkeletonCompatDataObject.describe_animations(paths)):
        notes = []
        for n in item.get('notifies', []):
            s = n.get('settings', {})
            if n.get('class') == EFFECT_CLASS:
                text = s.get('m_NiagaraCreateParams', '')
                loc = re.search(r'm_LocationOffset=\(X=([-\d.]+),Y=([-\d.]+),Z=([-\d.]+)\)', text)
                rot = re.search(r'm_RotationOffset=\(Pitch=([-\d.]+),Yaw=([-\d.]+),Roll=([-\d.]+)\)', text)
                notes.append('%.3f fx %s @%s%s%s %s' % (n['time'], _text_field(text, 'm_Template').rsplit('.', 1)[-1],
                                                        _text_field(text, 'm_SocketName'),
                                                        (' loc(%g,%g,%g)' % tuple(float(v) for v in loc.groups())) if loc else '',
                                                        (' rot(%g,%g,%g)' % tuple(float(v) for v in rot.groups())) if rot else '',
                                                        s.get('m_AttachType', '')))
            elif n.get('class') in SOUND_CLASSES:
                notes.append('%.3f snd %s %s' % (n['time'], s.get('SoundName', ''), s.get('AttachPointName', '')))
        out[item.get('path', '')] = {'length': item.get('length'), 'hits': item.get('hits'), 'notifies': len(item.get('notifies', [])),
                                     'classes': sorted(set(n.get('class', '') for n in item.get('notifies', []))),
                                     'extras': notes, 'error': item.get('error')}
    return out
