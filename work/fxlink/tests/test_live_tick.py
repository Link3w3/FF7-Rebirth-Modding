"""The editor's live edits against a simulated game (no Unreal): answers, retries, a game restart, old mods.

    python3 test_live_tick.py <folder holding the rebirth_fx_link (or rebirth_fx) package> <package name>
"""
import os
import sys
import time
import types

root, pkg_name = sys.argv[1], sys.argv[2]

# ---------------------------------------------------------------------------------------------------------------------
# a mock unreal module
# ---------------------------------------------------------------------------------------------------------------------
unreal = types.ModuleType('unreal')
LOG = []
DIALOGS = []
unreal.log = lambda s: LOG.append(('log', s))
unreal.log_warning = lambda s: LOG.append(('warning', s))


class _Dialog(object):
    @staticmethod
    def show_message(title, text, kind):
        DIALOGS.append(text)


unreal.EditorDialog = _Dialog
unreal.AppMsgType = types.SimpleNamespace(OK=0)
TICKS = []
unreal.register_slate_post_tick_callback = lambda fn: TICKS.append(fn) or len(TICKS)
unreal.load_asset = lambda path: object()
unreal.Paths = types.SimpleNamespace(convert_relative_path_to_full=lambda p: p, project_saved_dir=lambda: '/tmp/scratch/livetick')
unreal.RebirthFxLinkLibrary = types.SimpleNamespace(get_game_paks_directory=lambda: '/tmp/scratch/livetick/game/End/Content/Paks')
unreal.RebirthFxLibrary = unreal.RebirthFxLinkLibrary
sys.modules['unreal'] = unreal
sys.path.insert(0, root)
editor = __import__(pkg_name + '.editor', fromlist=['editor'])

# ---------------------------------------------------------------------------------------------------------------------
# a simulated game behind livelink.send / status
# ---------------------------------------------------------------------------------------------------------------------
NOW = [1000.0]
time.time = lambda: NOW[0]
editor.time.time = time.time


class Game(object):
    def __init__(self, version='1.6'):
        self.version = version
        self.running = True
        self.started = 1
        self.seq = 0
        self.looping = None
        self.sent = []          # every command the editor wrote
        self.answers = []       # queued behaviours for set_lut: 'ok', 'loading', 'error', 'none'
        self.status_ = dict(seq=0, result=dict(ok=True, info='ready'), started=self.started, version=version)

    def send(self, paks, op, **fields):
        seq = max(int(NOW[0] * 1000), self.seq + 1)
        self.seq = seq
        cmd = dict(seq=seq, op=op)
        cmd.update(fields)
        self.sent.append(cmd)
        if not self.running:
            return seq
        if op == 'set_lut':
            how = self.answers.pop(0) if self.answers else 'ok'
            if how == 'none':
                return seq
            if how == 'ok':
                r = dict(ok=True, written=2, op='set_lut')
                if self.version >= '1.6':
                    r['play'] = 'replayed' if self.looping == fields['path'] else 'started'
                    self.looping = fields['path']
            elif how == 'loading':
                r = dict(ok=False, loading=True, error='the effect is not loaded yet (loading it; edit again)', op='set_lut')
            else:
                r = dict(ok=False, error='no copy of X found in the game', op='set_lut')
        elif op == 'spawn':
            self.looping = fields['path']
            r = dict(ok=True, op='spawn')
        else:
            r = dict(ok=True, op=op)
        st = dict(seq=seq, result=r, looping=self.looping, version=self.version)
        if self.version >= '1.6':
            st['started'] = self.started
        self.status_ = st
        return seq

    def status(self, paks):
        return self.status_ if self.running else None

    def restart(self):
        self.started += 1
        self.looping = None
        self.status_ = dict(seq=self.seq, result=dict(ok=True, info='ready'), started=self.started, version=self.version)


PACKAGE = '/Game/Effect/X/FX_Test'
CURVES = [dict(asset='/Game/RebirthFx/FX_Test/A', name='Main.A.ColorCurve', kind='color', samples=2, tmin=0.0, tmax=1.0,
               imported=[0.0] * 8),
          dict(asset='/Game/RebirthFx/FX_Test/B', name='Main.B.FloatCurve', kind='float', samples=2, tmin=0.0, tmax=1.0,
               imported=[0.0, 0.0])]
VALUES = {c['asset']: list(c['imported']) for c in CURVES}
editor._load_manifest = lambda short: dict(package=PACKAGE, curves=CURVES)
editor._sample = lambda asset, kind, times: list(VALUES[CURVES[0]['asset']] if kind == 'color' else VALUES[CURVES[1]['asset']])


def use(game):
    editor.livelink.send = game.send
    editor.livelink.status = game.status
    editor.livelink.installed = lambda paks: True
    editor.livelink.wait = lambda paks, seq, seconds=3.0: game.status(paks) if game.running and game.status_.get('seq', -1) >= seq else None


def tick(n=1, dt=0.6):
    for _ in range(n):
        NOW[0] += dt
        editor._live_tick(0.0)


def set_lut_count(game):
    return len([c for c in game.sent if c['op'] == 'set_lut'])


failures = []


def check(what, ok):
    print(('ok    ' if ok else 'FAIL  ') + what)
    if not ok:
        failures.append(what)


# --- a 1.6 game: an edit goes, the game plays it; nothing pops up
game = Game('1.6')
use(game)
editor._state.update(current=PACKAGE, live=False, tick=None, pushed={}, next_check=0.0)
editor.toggle_live()
DIALOGS.clear()
tick()
check('no edit, nothing sent', set_lut_count(game) == 0)
VALUES['/Game/RebirthFx/FX_Test/A'] = [1.0] * 8
tick()
check('an edit is sent', set_lut_count(game) == 1)
check('with where to play it', game.sent[-1].get('every') == editor.PLAY_EVERY and game.sent[-1].get('forward') == editor.PLAY_FORWARD)
tick()
check('the 1.6 game plays it itself: no spawn from the editor', not [c for c in game.sent if c['op'] == 'spawn'])
check('no window', not DIALOGS)
tick(3)
check('nothing changed: nothing more sent', set_lut_count(game) == 1)

# --- the game restarts: the edit goes to it again
game.restart()
tick(2)
check('after a game restart the edit goes again', set_lut_count(game) == 2)

# --- loading: sent again until it goes in
VALUES['/Game/RebirthFx/FX_Test/B'] = [0.5, 0.5]
game.answers = ['loading', 'loading', 'ok']
n0 = set_lut_count(game)
tick(8)
check('an edit of a loading effect goes again until it goes in (%d sends)' % (set_lut_count(game) - n0), set_lut_count(game) - n0 == 3)
check('no window for loading', not DIALOGS)

# --- an error: one window, no endless resends
VALUES['/Game/RebirthFx/FX_Test/B'] = [0.7, 0.7]
game.answers = ['error']
n0 = set_lut_count(game)
tick(6)
check('an error is told once (%d windows)' % len(DIALOGS), len(DIALOGS) == 1 and 'no copy of X' in DIALOGS[0])
check('and not sent again (%d sends)' % (set_lut_count(game) - n0), set_lut_count(game) - n0 == 1)
VALUES['/Game/RebirthFx/FX_Test/B'] = [0.8, 0.8]
game.answers = ['error']
tick(4)
check('the same error is not shown twice', len(DIALOGS) == 1)

# --- no answer (game closed): sent again until it answers, one warning in the log
VALUES['/Game/RebirthFx/FX_Test/A'] = [0.25] * 8
game.running = False
n0 = set_lut_count(game)
tick(20)
warnings = [s for k, s in LOG if k == 'warning' and 'not answered' in s]
check('no answer: sent again every few seconds (%d sends)' % (set_lut_count(game) - n0), 2 <= set_lut_count(game) - n0 <= 5)
check('one warning about it (%d)' % len(warnings), len(warnings) == 1)
game.running = True
game.restart()
tick(3)
check('the game answers again: the edit is in', game.status_['result'].get('ok') and set_lut_count(game) - n0 >= 3)

# --- one edit in flight at a time
game2 = Game('1.6')
use(game2)
game2.answers = ['none', 'ok', 'ok']
VALUES['/Game/RebirthFx/FX_Test/A'] = [0.3] * 8
editor._state.update(pushed={}, live_wait=None)
tick()
VALUES['/Game/RebirthFx/FX_Test/A'] = [0.4] * 8
tick()
check('a second edit waits for the answer to the first', set_lut_count(game2) == 1)

# --- a 1.5 game: the editor asks it to play the effect
game3 = Game('1.5')
use(game3)
editor._state.update(pushed={}, live_wait=None, game_started=None)
VALUES['/Game/RebirthFx/FX_Test/A'] = [0.9] * 8
tick(3)
check('a 1.5 game gets a spawn after the edit', [c for c in game3.sent if c['op'] == 'spawn'] != [])
spawns = len([c for c in game3.sent if c['op'] == 'spawn'])
VALUES['/Game/RebirthFx/FX_Test/A'] = [0.95] * 8
tick(3)
check('but only when it is not playing already', len([c for c in game3.sent if c['op'] == 'spawn']) == spawns)

print('ALL PASSED' if not failures else '%d FAILED' % len(failures))
sys.exit(1 if failures else 0)
