"""A stand-in for the editor's unreal module, enough to run build_dirge_locomotion.py off the editor."""
import json, os, struct
ROOT = os.environ.get('MOCK_ROOT', '/tmp/mockloco')
LOG = []
STATE = {'built': []}
PROPS = {
    'EndAnimSetMove': ['name', 'animation', 'set', 'then_play', 'build', 'shot', 'hit_at', 'hits', 'notifies_from', 'retarget', 'keep_source_effects',
                       'source_sounds_only', 'clip_start', 'clip_end', 'speed', 'base', 'base_loop', 'motion_from', 'lean_bone', 'lean', 'bone_map',
                       'source_turn', 'keep_base_root'],
    'EndAnimSetRow': ['enabled', 'characters', 'battle', 'moves', 'field', 'build_folder', 'character_skeleton'],
    'DirectoryPath': ['path'],
    'Data': ['animation_sets', 'build_chunk', 'game_directory', 'last_result'],
    'Anim': ['skeleton', 'sequence_length', 'enable_root_motion', 'force_root_lock'],
}
SKELETON = '/Game/Character/Player/PC0011_00_Vincent_Standard/Model/PC0011_00_Skeleton.PC0011_00_Skeleton'
CLOUD_SKELETON = '/Game/Character/Player/PC0000_00_Cloud_Standard/Model/PC0000_00_Skeleton.PC0000_00_Skeleton'


class _Obj:
    kind = None

    def __init__(self):
        object.__setattr__(self, '_p', {})

    def set_editor_property(self, name, value):
        if name not in PROPS[self.kind]:
            raise AttributeError('%s has no property %s' % (self.kind, name))
        self._p[name] = value

    def get_editor_property(self, name):
        if name not in PROPS[self.kind]:
            raise AttributeError('%s has no property %s' % (self.kind, name))
        return self._p.get(name, '')


def _kind(k):
    return type(k, (_Obj,), {'kind': k})


EndAnimSetMove = _kind('EndAnimSetMove')
EndAnimSetRow = _kind('EndAnimSetRow')
DirectoryPath = _kind('DirectoryPath')


class EndMoveRetarget:
    PROPORTIONS, AS_IS, MOTION, LEAN = 'proportions', 'as_is', 'motion', 'lean'


class _Skel:
    def __init__(self, p):
        self.p = p

    def get_path_name(self):
        return self.p


class _Anim(_Obj):
    kind = 'Anim'

    def __init__(self, path, length, travel, rm=True):
        _Obj.__init__(self)
        self.path = path
        self.travel = travel
        self._p.update(skeleton=_Skel(SKELETON if '/PC0011_00_Vincent/' in path or '/Built/' in path else CLOUD_SKELETON),
                       sequence_length=length, enable_root_motion=rm, force_root_lock=False)


def _marker():
    return bytes([0x30, 0xAF, 0x2F, 0x90, 0x54, 0x94, 0xF4, 0x06, 0x59, 0x00, 0x49, 0x00, 0x49, 0x00, 0x53, 0x00])


def _acl_package():
    return b'\0' * 64 + _marker() + b'\0' * 16 + bytes.fromhex('10ac10ac') + b'\0' * 8 + bytes([4]) + b'\0' * 32


class _Data(_Obj):
    kind = 'Data'

    def build_one_move(self, row, name, set_):
        moves = self._p['animation_sets'][row]._p['moves']
        move = [m for m in moves if m._p['name'] == name and m._p['set'] == set_]
        assert len(move) == 1, (name, set_, len(move))
        p = move[0]._p
        for k in ('base', 'base_loop', 'bone_map', 'retarget', 'notifies_from', 'speed', 'keep_base_root'):
            assert k in p, (name, k)
        assert p['retarget'] == 'motion' and p['bone_map'] == 'Trans=Trans' and p['notifies_from'] == p['animation']
        STATE['built'].append(set_ + '/' + name)
        if os.environ.get('MOCK_CRASH_ON') == set_ + '/' + name:
            os._exit(3)
        folder = os.path.join(ROOT, 'Content', 'RebirthSkelCompat', 'Built', 'Vincent', set_)
        os.makedirs(folder, exist_ok=True)
        open(os.path.join(folder, name + '.uasset'), 'wb').write(_acl_package())
        _BUILT[name] = p
        return True, '%s/%s: built /Game/RebirthSkelCompat/Built/Vincent/%s/%s from %s (0.63 s), over %s, a loop ...' % (
            set_, name, set_, name, p['animation'].rsplit('/', 1)[-1], p['base'].rsplit('/', 1)[-1])

    def call_method(self, name):
        if name == 'ExportJson':
            row = self._p['animation_sets'][0]
            out = {'animation_sets': [{'characters': list(row._p['characters']),
                                       'moves': [{'set': m._p['set'], 'key': m._p['name']} for m in row._p['moves']]}]}
            path = os.path.join(ROOT, 'Saved', 'RebirthSkelCompat', 'Vincent_Moves.skelcompat.json')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            json.dump(out, open(path, 'w'), indent=1)
        self._p['last_result'] = '%s: ok (mock)\nmore' % name


_BUILT = {}
_DATA = _Data()


def _setup():
    row = EndAnimSetRow()
    row.set_editor_property('characters', ['PC0000_00_Cloud_Standard'])
    row.set_editor_property('build_folder', '/Game/RebirthSkelCompat/Built/Vincent')
    melee = EndAnimSetMove()
    melee.set_editor_property('name', 'B_NAttack01_0')
    melee.set_editor_property('set', 'Battle00')
    row.set_editor_property('moves', [melee])
    _DATA.set_editor_property('animation_sets', [row])
    gd = DirectoryPath()
    gd.set_editor_property('path', 'C:/Game/compat')
    _DATA.set_editor_property('game_directory', gd)
    f = os.path.join(ROOT, 'Content', 'Character', 'Player', 'PC0011_00_Vincent_Standard', 'Model')
    os.makedirs(f, exist_ok=True)
    open(os.path.join(f, 'Vincent_Moves.uasset'), 'wb').write(b'data object')
    d = os.path.join(ROOT, 'Content', 'Motion', 'Player', 'PC0011_00_Vincent', 'Battle00')
    os.makedirs(d, exist_ok=True)
    for n in ('rn', 'wk', 'wk_a', 'brn_a', 'lrn_a', 'rrn_a', 'st', 'st_a'):
        open(os.path.join(d, 'p000_m001_h_%s_remap.uasset' % n), 'wb').write(_acl_package())
    up = os.path.join(ROOT, 'Plugins', 'RebirthSkelCompat')
    os.makedirs(up, exist_ok=True)
    json.dump({'VersionName': os.environ.get('MOCK_PLUGIN', '1.12.4')}, open(os.path.join(up, 'RebirthSkelCompat.uplugin'), 'w'))


_setup()
PLAN = json.load(open(os.environ['MOCK_PLAN']))
EXPECT = {m['name']: m['expect'] for m in PLAN['moves']}


class Paths:
    @staticmethod
    def project_saved_dir():
        return os.path.join(ROOT, 'Saved')

    @staticmethod
    def project_content_dir():
        return os.path.join(ROOT, 'Content')

    @staticmethod
    def convert_relative_path_to_full(p):
        return p


class _Registry:
    def scan_paths_synchronous(self, folders, force):
        pass


class AssetRegistryHelpers:
    @staticmethod
    def get_asset_registry():
        return _Registry()


class EditorAssetLibrary:
    @staticmethod
    def load_asset(path):
        if path.startswith(PLAN['data_object']):
            return _DATA
        name = path.rsplit('.', 1)[-1]
        if '/Built/Vincent/' in path:
            if name not in _BUILT:
                return None
            e = EXPECT[name]
            travel = 0.0 if os.environ.get('MOCK_STILL') == name else e['root_travel']
            return _Anim(path, e['length'], travel)
        if os.environ.get('MOCK_MISSING') and os.environ['MOCK_MISSING'] in path:
            return None
        return _Anim(path, 1.0, 0.0)

    @staticmethod
    def save_loaded_asset(asset, only_dirty):
        return True


class _Vec:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z


class _Pose:
    def __init__(self, t):
        self.translation = t


class AnimationLibrary:
    @staticmethod
    def get_bone_pose_for_time(anim, bone, t, extract):
        assert bone == 'Trans'
        L = anim._p['sequence_length']
        f = t / L if L else 0
        return _Pose(_Vec(anim.travel * f, 0.0, 0.0))


class EndSkeletonCompatDataObject:
    @staticmethod
    def describe_animations(paths):
        return json.dumps([{'path': p, 'class': 'AnimSequence', 'length': 1.0} for p in paths])


def log(text):
    LOG.append(text)


def log_warning(text):
    LOG.append('WARNING ' + text)
