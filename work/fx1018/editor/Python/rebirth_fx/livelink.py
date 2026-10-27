"""The End editor's side of the live link to the running game (the game side is the RebirthLiveLink UE4SS mod).

A command is a Lua table literal written to <game>\\End\\Binaries\\Win64\\ue4ss\\Mods\\RebirthLiveLink\\link\\command.lua;
the mod runs each new one (higher seq) and writes link\\status.json.
"""
import json, os, time

_last_seq = [0]


def mod_dir(paks_dir):
    """The mod's folder from the game's Content\\Paks folder."""
    if not paks_dir:
        return None
    end = os.path.dirname(os.path.dirname(os.path.normpath(paks_dir)))     # ...\End
    return os.path.join(end, 'Binaries', 'Win64', 'ue4ss', 'Mods', 'RebirthLiveLink')


def link_dir(paks_dir):
    d = mod_dir(paks_dir)
    return os.path.join(d, 'link') if d else None


def _dirs(paks_dir):
    """Where commands go: link\\, and Scripts\\link\\ too when it is there (the mod's first version read that one)."""
    d = mod_dir(paks_dir)
    if not d:
        return []
    out = [os.path.join(d, 'link')]
    old = os.path.join(d, 'Scripts', 'link')
    if os.path.isdir(old):
        out.append(old)
    return out


def installed(paks_dir):
    d = mod_dir(paks_dir)
    return bool(d) and os.path.isdir(d)


def _lua(v):
    if v is None:
        return 'nil'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, (int, float)):
        return repr(float(v)) if isinstance(v, float) else str(v)
    if isinstance(v, str):
        return '"' + v.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
    if isinstance(v, (list, tuple)):
        return '{' + ', '.join(_lua(x) for x in v) + '}'
    if isinstance(v, dict):
        return '{' + ', '.join('%s = %s' % (k, _lua(x)) for k, x in v.items()) + '}'
    raise TypeError(type(v))


def send(paks_dir, op, **fields):
    """Writes a command; returns its seq."""
    if not installed(paks_dir):
        raise RuntimeError('the RebirthLiveLink mod is not installed in the game (ue4ss\\Mods\\RebirthLiveLink)')
    seq = max(int(time.time() * 1000), _last_seq[0] + 1)
    _last_seq[0] = seq
    cmd = dict(seq=seq, op=op)
    cmd.update(fields)
    text = 'return ' + _lua(cmd) + '\n'
    for d in _dirs(paks_dir):
        if not os.path.isdir(d):
            os.makedirs(d)
        path = os.path.join(d, 'command.lua')
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(text)
        os.replace(tmp, path)
    return seq


def status(paks_dir):
    """The newest status the mod wrote."""
    best = None
    for d in _dirs(paks_dir):
        try:
            s = json.load(open(os.path.join(d, 'status.json'), encoding='utf-8'))
        except Exception:
            continue
        if best is None or s.get('seq', -1) > best.get('seq', -1):
            best = s
    return best


def wait(paks_dir, seq, seconds=3.0):
    """The status once the game has run command `seq` (None when it did not answer in time: game closed, in a loading
    screen, or the mod not running)."""
    end = time.time() + seconds
    while time.time() < end:
        s = status(paks_dir)
        if s and s.get('seq', -1) >= seq:
            return s
        time.sleep(0.1)
    return None


def floats_hex(values):
    import struct
    return struct.pack('<%df' % len(values), *values).hex()
