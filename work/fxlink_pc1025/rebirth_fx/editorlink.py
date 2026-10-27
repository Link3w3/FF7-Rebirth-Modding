"""Editor link: lets a tool (Sandalphon, working in this project with you) run Python in this editor while it is open.

Off until you turn it on (Rebirth FX > Editor Link On/Off); it stays on across editor restarts until you turn it off
(Saved/RebirthEditorLink/enabled). While on, every half second it looks at Saved/RebirthEditorLink/command.py:

    # seq = 1792310000000
    result = unreal.SystemLibrary.get_engine_version()

A new seq runs once, on the editor's main thread, with `unreal` and `result` in scope; what it printed, `result` and
any error go to Saved/RebirthEditorLink/status.json (and log.txt). Code taking long blocks the editor meanwhile.
"""
import io, json, os, sys, time, traceback

import unreal

_state = {'tick': None, 'last_seq': None, 'next_check': 0.0}


def _dir():
    return os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'RebirthEditorLink')


def _flag():
    return os.path.join(_dir(), 'enabled')


def enabled():
    return os.path.isfile(_flag())


def _log(text):
    try:
        with open(os.path.join(_dir(), 'log.txt'), 'a', encoding='utf-8') as f:
            f.write(time.strftime('[%H:%M:%S] ') + text + '\n')
    except Exception:
        pass


def _write_status(status):
    path = os.path.join(_dir(), 'status.json')
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(status, f, indent=1, default=str)
    os.replace(tmp, path)


def _read_command():
    path = os.path.join(_dir(), 'command.py')
    try:
        with open(path, encoding='utf-8') as f:
            code = f.read()
    except OSError:
        return None, None
    first = code.split('\n', 1)[0].strip()
    if not first.startswith('# seq'):
        return None, None
    try:
        seq = int(first.split('=', 1)[1].strip())
    except (IndexError, ValueError):
        return None, None
    return seq, code


def _run(seq, code):
    out = io.StringIO()
    scope = {'unreal': unreal, 'result': None, '__name__': '__rebirth_editor_link__'}
    started = time.time()
    status = {'seq': seq, 'ok': True}
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = out
    try:
        exec(compile(code, 'editor_link_%d' % seq, 'exec'), scope)
    except Exception:
        status['ok'] = False
        status['error'] = traceback.format_exc()
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    status['result'] = scope.get('result')
    status['output'] = out.getvalue()[-200000:]
    status['seconds'] = round(time.time() - started, 3)
    status['time'] = time.time()
    try:
        json.dumps(status['result'])
    except (TypeError, ValueError):
        status['result'] = repr(status['result'])
    _write_status(status)
    _log('#%d %s (%.2f s)' % (seq, 'ok' if status['ok'] else 'failed', status['seconds']))


def _tick(delta):
    now = time.time()
    if now < _state['next_check']:
        return
    _state['next_check'] = now + 0.5
    if not enabled():
        return
    seq, code = _read_command()
    if seq is None or seq == _state['last_seq']:
        return
    _state['last_seq'] = seq
    try:
        _run(seq, code)
    except Exception:
        _log('#%d could not run: %s' % (seq, traceback.format_exc()))


def start():
    """Starts watching (when the link is on). The menu calls this at editor start."""
    if _state['tick'] is None:
        # a command left from before this editor started does not run again
        seq, _ = _read_command()
        _state['last_seq'] = seq
        _state['tick'] = unreal.register_slate_post_tick_callback(_tick)


def toggle():
    os.makedirs(_dir(), exist_ok=True)
    if enabled():
        os.remove(_flag())
        _log('turned off')
        message = 'Editor link is OFF. Tools can no longer run code in this editor.'
    else:
        with open(_flag(), 'w') as f:
            f.write('on\n')
        start()
        _log('turned on')
        message = ('Editor link is ON: tools working in this project with you (Sandalphon) can run Python in this editor '
                   'through Saved\\RebirthEditorLink. It stays on across restarts until you turn it off here.')
    unreal.log('[Rebirth FX] ' + message)
    try:
        unreal.EditorDialog.show_message('Rebirth FX', message, unreal.AppMsgType.OK)
    except Exception:
        pass
