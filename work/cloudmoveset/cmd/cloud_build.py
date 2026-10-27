# CLOUD moveset (Battle11): Cloud's own battle animations as Sephiroth's moves (retargeted onto Sephiroth's skeleton), built
# in the End editor with Create a Character System's Build Moves, in an editor commandlet (build_cloud_moveset.py): setup(),
# then build([...]) per move. (Made from the CRISIS CORE form's cc_build.py: the same steps without its carriers, since
# Cloud's own animations bring their sounds and effects with them: Keep Source Effects.)
#
# Each move: Cloud's animation of the name (or the one the plan says), Sephiroth's gameplay notifies from Notifies From (his
# move of that name: damage, combo and cancel windows, states, voice, face), his damage re-timed onto Cloud's blows (the
# plan's hits), Cloud's own swing sounds, trails and footsteps kept. Nothing is duplicated (DuplicateAsset of an
# FBX-imported animation stopped this editor on 2026-10-22).
import json, os, re, struct, time, traceback
import unreal

SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
CONTENT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'CloudMoveset')
PLAN = json.load(open(os.path.join(OUT, 'cmd', 'plan.json')))
PROGRESS = os.path.join(OUT, 'progress.json')
DATA_PATH = '/Game/RebirthSkelCompat/CloudMoveset/CloudMoveset_Data'
REAL_FOLDER = '/Game/RebirthSkelCompat/Built/SephirothForms'
SKELETON = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00_Skeleton.PC0010_00_Skeleton'
CHARACTERS = ['/Game/DataAsset/Game/CharaSpec/CharaSpec_PC0000_00_Cloud_Standard.CharaSpec_PC0000_00_Cloud_Standard']
SOURCES = [('/Game/Motion/Player/PC0010_Sephiroth/Battle00.Battle00', 'Battle11')]
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


def length_of(path):
    asset = unreal.load_asset(path)
    if asset is None:
        return None
    try:
        return float(asset.get_editor_property('sequence_length'))
    except Exception:
        return None


CLIPS = {}   # move key -> its clip, for moves cut to the length of their Notifies From (setup)


def make_move(m):
    move = unreal.EndAnimSetMove()
    setp(move, 'name', m['name'])
    setp(move, 'set', m['set'])
    setp(move, 'animation', m['animation'])
    setp(move, ['build', 'b_build'], True)
    setp(move, 'retarget', unreal.EndMoveRetarget.PROPORTIONS)
    setp(move, 'notifies_from', m['notifies_from'])
    setp(move, ['keep_source_effects', 'b_keep_source_effects'], True)
    hits = []
    for h in m.get('hits', []):
        hit = unreal.EndMoveHit()
        setp(hit, 'time', float(h['time']))
        if h.get('window'):
            setp(hit, 'window', float(h['window']))
        if h.get('damage'):
            setp(hit, 'damage_source_id', h['damage'])
        hits.append(hit)
    setp(move, 'hits', hits)
    clip = CLIPS.get(m['set'] + '/' + m['name']) or m.get('clip')
    if clip:
        setp(move, 'clip_start', float(clip[0]))
        setp(move, 'clip_end', float(clip[1]))
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
    """The data object: row 0, the moves. Every animation the plan names is checked to load first."""
    skeleton = unreal.load_asset(SKELETON)
    if skeleton is None:
        raise RuntimeError('the character skeleton does not load: ' + SKELETON)
    missing, cut = [], []
    for key, m in MOVES.items():
        for what in ('animation', 'notifies_from'):
            if length_of(m[what]) is None:
                missing.append('%s %s %s' % (key, what, m[what]))
        if m.get('clip_like_notifies_from'):
            # (Cloud's guard hold as long as Sephiroth's turn while guarding)
            want, have = length_of(m['notifies_from']), length_of(m['animation'])
            if want and have:
                CLIPS[key] = [0.0, round(min(want, have), 4)]
                cut.append('%s %.2f s' % (key, CLIPS[key][1]))
    if missing:
        raise RuntimeError('these do not load: ' + '; '.join(missing[:20]))
    data = load_data()
    made = data is None
    if made:
        folder, name = DATA_PATH.rsplit('/', 1)
        data = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.EndSkeletonCompatDataObject, None)
    if data is None:
        raise RuntimeError('the data object could not be made')
    real = [make_move(m) for m in PLAN['moves']]
    setp(data, 'animation_sets', [make_row(REAL_FOLDER, real, skeleton)])
    setp(data, 'build_chunk', 0)   # no Primary Asset Label: these are cooked with Cook For Game, not Package Project
    game_dir = unreal.DirectoryPath()
    setp(game_dir, 'path', '')
    setp(data, 'game_directory', game_dir)
    unreal.EditorAssetLibrary.save_loaded_asset(data, False)
    return {'data_object': ('made ' if made else 'updated ') + DATA_PATH, 'moves': len(real), 'cut to their turn': cut}


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
    """Builds the moves `keys` ("Battle11/B_NAttack01_0", ...), each saved as it is built."""
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
            ok, report = split(data.build_one_move(0, m['name'], m['set']))
            report = report or str(data.get_editor_property('last_result'))   # (the report as Last Result for scripts)
            entry['move'] = {'ok': bool(ok), 'report': ' | '.join(l for l in report.strip().split('\n') if l.strip())[:1500]}
            problem = saved_problem(package_file(REAL_FOLDER, m))
            if not ok or problem:
                entry['error'] = 'the move: ' + (problem or 'the build reported an error')
        except Exception:
            entry['error'] = traceback.format_exc()[-1500:]
        entry['seconds'] = round(time.time() - entry.pop('started'), 1)
        state.setdefault('done', {})[key] = entry
        state['current'] = None
        write_json(PROGRESS, state)
        out[key] = entry
    return out


def _text_field(text, field):
    found = re.search(field + r'=("?)([^,")]*)\1', text)
    return found.group(2) if found else ''


def summary(paths):
    """What the built moves hold: length, damage hits, and every sound and effect (time, what, where)."""
    out = {}
    for item in json.loads(unreal.EndSkeletonCompatDataObject.describe_animations(paths)):
        notes = []
        for n in item.get('notifies', []):
            s = n.get('settings', {})
            if n.get('class') == EFFECT_CLASS:
                text = s.get('m_NiagaraCreateParams', '')
                notes.append('%.3f fx %s @%s %s' % (n['time'], _text_field(text, 'm_Template').rsplit('.', 1)[-1],
                                                     _text_field(text, 'm_SocketName'), s.get('m_AttachType', '')))
            elif n.get('class') in SOUND_CLASSES:
                notes.append('%.3f snd %s %s' % (n['time'], s.get('SoundName', ''), s.get('AttachPointName', '')))
        out[item.get('path', '')] = {'length': item.get('length'), 'hits': item.get('hits'), 'notifies': len(item.get('notifies', [])),
                                     'classes': sorted(set(n.get('class', '') for n in item.get('notifies', []))),
                                     'extras': notes, 'error': item.get('error')}
    return out
