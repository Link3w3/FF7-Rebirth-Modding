"""A stand-in for the editor's unreal module, enough to run build_safer_update.py's Python off the editor."""
import json, os

PROPS = {
    'EndAnimSetMove': ['name', 'animation', 'set', 'then_play', 'build', 'shot', 'hit_at', 'hits', 'notifies_from', 'retarget', 'keep_source_effects',
                       'source_sounds_only', 'clip_start', 'clip_end', 'speed', 'base', 'base_loop', 'motion_from', 'lean_bone', 'lean', 'bone_map',
                       'source_turn', 'keep_base_root'],
    'EndMoveHit': ['time', 'window', 'damage_source_id', 'effect', 'effect_socket', 'effect_on', 'effect_time', 'sound_bank', 'sound', 'weapon'],
    'EndAnimSetRow': ['enabled', 'characters', 'battle', 'moves', 'field', 'field_actions', 'cutscene', 'character_skeleton', 'sockets', 'limit_breaks',
                      'keep_proportions', 'override', 'player_parameter', 'abilities', 'refresh_abilities', 'preload', 'pack_assets', 'forms', 'build_folder',
                      'shot_effects', 'more_set_names', 'requires_paks'],
    'EndAnimSetSource': ['path', 'as_', 'auto_match', 'only_names_with'],
    'EndLimitBreak': ['animation', 'then_play'],
    'FilePath': ['file_path'],
    'DirectoryPath': ['path'],
    'Data': ['animation_sets', 'build_chunk', 'game_directory', 'import_file', 'last_result'],
    'Forms': ['list'],
    'Form': ['name'],
}
LOG = []
STATE = {'built': [], 'describe_calls': 0}
ROOT = os.environ.get('MOCK_ROOT', '/tmp/mockroot')


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
        return self._p.get(name, {'list': None}.get(name, ''))


def _kind(k):
    return type(k, (_Obj,), {'kind': k})


EndAnimSetMove = _kind('EndAnimSetMove')
EndMoveHit = _kind('EndMoveHit')
EndAnimSetRow = _kind('EndAnimSetRow')
EndAnimSetSource = _kind('EndAnimSetSource')
EndLimitBreak = _kind('EndLimitBreak')
FilePath = _kind('FilePath')
DirectoryPath = _kind('DirectoryPath')


class EndMoveRetarget:
    PROPORTIONS, AS_IS, MOTION, LEAN = 'proportions', 'as_is', 'motion', 'lean'


class _Form(_Obj):
    kind = 'Form'


class _Forms(_Obj):
    kind = 'Forms'


class _Data(_Obj):
    kind = 'Data'

    def call_method(self, name):
        if name == 'ImportFromGameJson':
            row = self._p['animation_sets'][0]
            forms = _Forms()
            lst = []
            for n in ['NORMAL', 'WINGED', 'FLYING', 'KH2', 'BIZARRO', 'SAFER']:
                f = _Form()
                f.set_editor_property('name', n)
                lst.append(f)
            forms.set_editor_property('list', lst)
            PROPS['EndAnimSetRow']  # (forms is a row property)
            row._p['forms'] = forms
        self._p['last_result'] = '%s: ok (mock)\nmore' % name

    def build_one_move(self, row, name, set_):
        moves = self._p['animation_sets'][row]._p['moves']
        move = [m for m in moves if m._p['name'] == name and m._p['set'] == set_]
        assert len(move) == 1, (name, len(move))
        m = move[0]._p
        STATE['built'].append(dict(m))
        folder = os.path.join(ROOT, 'Content', 'RebirthSkelCompat', 'Built', 'SephirothForms', set_)
        os.makedirs(folder, exist_ok=True)
        open(os.path.join(folder, name + '.uasset'), 'wb').write(b'\0' * 64)
        text = '%s/%s: built ...' % (set_, name)
        if m.get('bone_map'):
            text += ", its Bone Map's 13 bone(s)"
        return True, text


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


_DATA = _Data()


class EditorAssetLibrary:
    @staticmethod
    def load_asset(path):
        return _DATA

    @staticmethod
    def save_loaded_asset(asset, only_dirty):
        return True


def load_asset(path):
    return 'asset:' + path


class EndSkeletonCompatDataObject:
    @staticmethod
    def describe_animations(paths):
        STATE['describe_calls'] += 1
        out = []
        for p in paths:
            name = p.rsplit('.', 1)[-1]
            length = 3.0 if 'status_001_02' in p else 3.7 if 'skill_006' in p else 1.07 if 'status_001_03' in p else 1.8 if 'status_001_01' in p else 8.0 if ('idle' in p or 'enter' in p) else 4.5
            if 'Gokumon' in name:
                length = 6.0 if 'Long' in name else 4.0 if 'Short' in name else 2.0
            out.append({'path': p, 'class': 'AnimSequence', 'length': length})
        return json.dumps(out)


def log(text):
    LOG.append(text)


def log_warning(text):
    LOG.append('WARNING ' + text)
