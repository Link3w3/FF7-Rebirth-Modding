"""A stand-in for the End editor's unreal module, enough to run build_galian_moves.py's Python off the editor."""
import json, os, struct

PROPS = {
    'EndAnimSetMove': ['name', 'animation', 'set', 'then_play', 'build', 'shot', 'hit_at', 'hits', 'notifies_from', 'retarget', 'keep_source_effects',
                       'source_sounds_only', 'clip_start', 'clip_end', 'speed', 'base', 'base_loop', 'motion_from', 'lean_bone', 'lean', 'bone_map',
                       'source_turn', 'keep_base_root'],
    'EndMoveHit': ['time', 'window', 'damage_source_id', 'effect', 'effect_socket', 'effect_on', 'effect_time', 'sound_bank', 'sound', 'weapon'],
    'EndAnimSetRow': ['enabled', 'characters', 'battle', 'moves', 'field', 'field_actions', 'cutscene', 'character_skeleton', 'sockets', 'limit_breaks',
                      'keep_proportions', 'override', 'player_parameter', 'abilities', 'refresh_abilities', 'preload', 'pack_assets', 'forms', 'build_folder',
                      'shot_effects', 'more_set_names', 'requires_paks'],
    'EndAnimSetSource': ['path', 'as_', 'auto_match', 'only_names_with'],
    'FilePath': ['file_path'],
    'DirectoryPath': ['path'],
    'Data': ['animation_sets', 'build_chunk', 'game_directory', 'import_file', 'last_result'],
    'Forms': ['list'],
    'Form': ['name', 'pack', 'model'],
    'Anim': ['skeleton', 'sequence_length'],
    'Event': ['notify', 'notify_state_class', 'notify_name'],
    'Notify': ['m_branch_condition_type', 'm_branch_condition_name'],
}
LOG = []
STATE = {'built': [], 'describe_calls': 0, 'saved': [], 'removed': [], 'created': 0}
ROOT = os.environ.get('MOCK_ROOT', '/tmp/mockroot')
BEAST = '/Game/Character/Enemy/EB2160_00_VincentValentine_Standard/Model/EB2160_00_Skeleton.EB2160_00_Skeleton'
MARKER = bytes([0x30, 0xAF, 0x2F, 0x90, 0x54, 0x94, 0xF4, 0x06, 0x59, 0x00, 0x49, 0x00, 0x49, 0x00, 0x53, 0x00])


class _Obj:
    kind = None

    def __init__(self, **kw):
        object.__setattr__(self, '_p', {})
        for k, v in kw.items():
            self._p[k] = v

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
EndMoveHit = _kind('EndMoveHit')
EndAnimSetRow = _kind('EndAnimSetRow')
EndAnimSetSource = _kind('EndAnimSetSource')
FilePath = _kind('FilePath')
DirectoryPath = _kind('DirectoryPath')


class EnumBase:
    def __init__(self, name, value):
        self.name, self.value = name, value

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, self.name)


class BranchCondition(EnumBase):
    pass


BranchCondition.NONE = BranchCondition('NONE', 0)
BranchCondition.ABILITY_ID = BranchCondition('ABILITY_ID', 1)


class EndMoveRetarget:
    PROPORTIONS, AS_IS, MOTION, LEAN = 'proportions', 'as_is', 'motion', 'lean'


class _Form(_Obj):
    kind = 'Form'


class _Forms(_Obj):
    kind = 'Forms'


class _Class:
    def __init__(self, n):
        self.n = n

    def get_name(self):
        return self.n


class _Notify(_Obj):
    kind = 'Notify'

    def __init__(self, cls, cond=None):
        _Obj.__init__(self)
        self.cls = cls
        if cond is not None:
            self._p['m_branch_condition_type'] = cond

    def get_class(self):
        return _Class(self.cls)

    def get_editor_property(self, name):
        if name not in self._p:
            raise AttributeError('%s has no property %s' % (self.cls, name))
        return self._p[name]


class _Event(_Obj):
    kind = 'Event'


class _Skeleton:
    def __init__(self, p):
        self.p = p

    def get_path_name(self):
        return self.p


class _Anim(_Obj):
    kind = 'Anim'

    def __init__(self, path, length=1.0):
        _Obj.__init__(self)
        self.path = path
        self._p['skeleton'] = _Skeleton(BEAST)
        self._p['sequence_length'] = length
        name = path.rsplit('.', 1)[-1]
        self.events = [_Event(notify=_Notify('EndAnimNotifyPlayVoice'), notify_state_class=None, notify_name='EndAnimNotifyPlayVoice'),
                       _Event(notify=None, notify_state_class=_Notify('AnimNotifyState_EndTimedNiagaraEffect', BranchCondition.ABILITY_ID),
                              notify_name='EndTimedNiagaraEffect'),
                       _Event(notify=_Notify('EndAnimNotifyPlayCharacterSound'), notify_state_class=None, notify_name='EndAnimNotifyPlayCharacterSound')]


ANIMS = {}


class _Data(_Obj):
    kind = 'Data'

    def call_method(self, name):
        if name == 'ImportFromGameJson':
            row = self._p['animation_sets'][0]
            spec = json.load(open(self._p['import_file']._p['file_path']))
            forms = _Forms()
            lst = []
            for f in spec['animation_sets'][0]['forms']['list']:
                form = _Form()
                form.set_editor_property('name', f['name'])
                form.set_editor_property('pack', f.get('pack', ''))
                lst.append(form)
            forms.set_editor_property('list', lst)
            row._p['forms'] = forms
        if name == 'ExportJson':
            os.makedirs(os.path.join(ROOT, 'Saved', 'RebirthSkelCompat'), exist_ok=True)
            open(os.path.join(ROOT, 'Saved', 'RebirthSkelCompat', 'DO_VincentGalian.skelcompat.json'), 'w').write('{}')
        self._p['last_result'] = '%s: ok (mock)\nmore' % name

    def build_one_move(self, row, name, set_):
        moves = self._p['animation_sets'][row]._p['moves']
        move = [m for m in moves if m._p['name'] == name and m._p['set'] == set_]
        assert len(move) == 1, (name, len(move))
        m = move[0]._p
        assert m['build'], name
        STATE['built'].append(dict(m))
        folder = os.path.join(ROOT, 'Content', 'RebirthSkelCompat', 'Built', 'VincentGalian', set_)
        os.makedirs(folder, exist_ok=True)
        open(os.path.join(folder, name + '.uasset'), 'wb').write(b'\0' * 64 + MARKER + b'\0' * 16 + struct.pack('<I', 0xAC10AC10) + b'\0' * 8 + b'\x04' + b'\0' * 40)
        return True, '%s/%s: built (mock) %s' % (set_, name, m['retarget'])


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


class _AssetData:
    def __init__(self, package, name):
        self.package_name, self.asset_name = package, name


class _Registry:
    def scan_paths_synchronous(self, folders, force):
        pass

    def get_assets_by_class(self, cls, sub):
        return [_AssetData('/Game/RebirthSkelCompat/EvilCloudBoss/DO_EvilCloudBoss', 'DO_EvilCloudBoss'),
                _AssetData('/Game/RebirthSkelCompat/VincentGalian/DO_VincentGalian', 'DO_VincentGalian')]


class AssetRegistryHelpers:
    @staticmethod
    def get_asset_registry():
        return _Registry()


_DATA = _Data()


class _OtherData(_Obj):
    kind = 'Data'


_OTHER = _OtherData()
_OTHER._p['build_chunk'] = 52


class EditorAssetLibrary:
    @staticmethod
    def load_asset(path):
        if 'DO_VincentGalian' in path:
            return _DATA
        if 'DO_' in path:
            return _OTHER
        if path not in ANIMS:
            ANIMS[path] = _Anim(path)
        return ANIMS[path]

    @staticmethod
    def does_asset_exist(path):
        return False

    @staticmethod
    def save_loaded_asset(asset, only_dirty):
        STATE['saved'].append(getattr(asset, 'path', 'data'))
        return True


class _Tools:
    def create_asset(self, name, folder, cls, factory):
        STATE['created'] += 1
        return _DATA


class AssetToolsHelpers:
    @staticmethod
    def get_asset_tools():
        return _Tools()


class _Vec:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z


class _Xf:
    def __init__(self, t):
        self.translation = t


class AnimationLibrary:
    @staticmethod
    def get_animation_notify_events(anim):
        return list(anim.events)

    @staticmethod
    def remove_animation_notify_events_by_name(anim, name):
        before = len(anim.events)
        anim.events = [e for e in anim.events if e._p['notify_name'] != name]
        STATE['removed'].append((anim.path, name, before - len(anim.events)))

    @staticmethod
    def get_bone_pose_for_time(anim, bone, t, extract):
        return _Xf(_Vec(100.0 * t, 0.0, 0.0))


class EndSkeletonCompatDataObject:
    @staticmethod
    def describe_animations(paths):
        STATE['describe_calls'] += 1
        out = []
        for p in paths:
            d = {'path': p, 'class': 'AnimSequence', 'length': 1.0}
            if '/EB2160_VincentValentine/' in p:
                d['skeleton'] = BEAST
            out.append(d)
        return json.dumps(out)


def load_asset(path):
    return 'asset:' + path


def log(text):
    LOG.append(text)


def log_warning(text):
    LOG.append('WARNING ' + text)
