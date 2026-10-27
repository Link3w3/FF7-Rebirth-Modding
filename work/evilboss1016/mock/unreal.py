"""The Safer mock (unreal_base) plus what build_evilcloud_boss.py calls: does_asset_exist, create_asset, BuildMoves."""
import os, json
from unreal_base import *            # noqa
import unreal_base as _b


class _DataEC(_b._Data):
    def call_method(self, name):
        if name == 'BuildMoves':
            row = self._p['animation_sets'][0]
            n = 0
            for m in row._p['moves']:
                p = m._p
                if not p.get('build'):
                    continue
                for k in ('name', 'set', 'animation', 'notifies_from', 'retarget', 'keep_source_effects', 'hits'):
                    assert k in p, (p.get('name'), k)
                folder = os.path.join(_b.ROOT, 'Content', 'RebirthSkelCompat', 'Built', 'EvilCloudBoss', p['set'])
                os.makedirs(folder, exist_ok=True)
                # an ACL clip, as the real build saves (the marker, then the ACL tag; QuatDropW_Variable)
                blob = b'\0' * 64 + bytes(_b_marker()) + b'\0' * 16 + bytes.fromhex('10ac10ac') + b'\0' * 8 + bytes([4]) + b'\0' * 32
                open(os.path.join(folder, p['name'] + '.uasset'), 'wb').write(blob)
                n += 1
            self._p['last_result'] = 'mock build\n%d of %d move(s) built and saved.' % (n, n)
            return
        return _b._Data.call_method(self, name)

    def build_one_move(self, row, name, set_):
        moves = self._p['animation_sets'][row]._p['moves']
        move = [m for m in moves if m._p['name'] == name and m._p['set'] == set_]
        assert len(move) == 1, (name, set_, len(move))
        p = move[0]._p
        assert p.get('build'), name
        for k in ('name', 'set', 'animation', 'notifies_from', 'retarget', 'keep_source_effects', 'hits'):
            assert k in p, (p.get('name'), k)
        _b.STATE['built'].append(set_ + '/' + name)
        if os.environ.get('MOCK_CRASH_ON') == set_ + '/' + name:
            os._exit(3)   # the editor stopping in the middle of this move
        folder = os.path.join(_b.ROOT, 'Content', 'RebirthSkelCompat', 'Built', 'EvilCloudBoss', set_)
        os.makedirs(folder, exist_ok=True)
        blob = b'\0' * 64 + bytes(_b_marker()) + b'\0' * 16 + bytes.fromhex('10ac10ac') + b'\0' * 8 + bytes([4]) + b'\0' * 32
        open(os.path.join(folder, name + '.uasset'), 'wb').write(blob)
        text = '%s/%s: built /Game/RebirthSkelCompat/Built/EvilCloudBoss/%s/%s from %s (1.00 s)' % (set_, name, set_, name, p['animation'].rsplit('.', 1)[-1])
        if 'AtkBurst02' in name:
            text += ", 4 effect parameter(s) of the game's that this editor cannot write taken out of the effects copied (they play with their own values)"
        text += '\n\n1 of 1 move(s) built and saved. Package the project: they go in pakchunk52.'
        return True, text


def _b_marker():
    return [0x30, 0xAF, 0x2F, 0x90, 0x54, 0x94, 0xF4, 0x06, 0x59, 0x00, 0x49, 0x00, 0x49, 0x00, 0x53, 0x00]


_DATA = _DataEC()


class EditorAssetLibrary:
    @staticmethod
    def does_asset_exist(path):
        return False

    @staticmethod
    def load_asset(path):
        return _DATA

    @staticmethod
    def save_loaded_asset(asset, only_dirty):
        return True


class _Tools:
    def create_asset(self, name, folder, cls, factory):
        return _DATA


class AssetToolsHelpers:
    @staticmethod
    def get_asset_tools():
        return _Tools()


class EndSkeletonCompatDataObject(_b.EndSkeletonCompatDataObject):
    pass
