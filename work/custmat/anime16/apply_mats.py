"""Custom material sets on the controlled character's Sephiroth (PC0010_00) slots through RebirthLiveLink, or the
original materials back. Prints what the game answered.

    python3 apply_mats.py anime        # AnimeShader on every part (each part keeps its own colour, normals, cut-outs),
                                       # AnimeShaderEye on his eyes
    python3 apply_mats.py taken        # Taken on every part
    python3 apply_mats.py reset        # the original materials back
    python3 apply_mats.py list         # only list what the character wears

A set goes on over the original materials: whatever set is on is taken off first.
"""
import json
import os
import sys
import time

LINK = os.path.expanduser('~/mnt/FINAL FANTASY VII REBIRTH/End/Binaries/Win64/ue4ss/Mods/RebirthLiveLink/link')
PARTS = ['PC0010_00_BodyA', 'PC0010_00_Head', 'PC0010_00_Skin', 'PC0010_00_Eyelash',
         'PC0010_00_BodyB', 'PC0010_00_Eyebrow', 'PC0010_00_Hair', 'PC0010_00_HairCore', 'PC0010_00_Eye']
T = '/Game/RebirthCustom/Taken/MI_Taken_'
SETS = {
    'anime': dict((p, '/Game/RebirthCustom/Anime/MI_Anime_' + p) for p in PARTS),
    'taken': {
        'PC0010_00_BodyA': T + 'PC0010_00_BodyA', 'PC0010_00_Head': T + 'PC0010_00_BodyA',
        'PC0010_00_Skin': T + 'PC0010_00_BodyA', 'PC0010_00_Eyelash': T + 'PC0010_00_BodyA',
        'PC0010_00_BodyB': T + 'PC0010_00_BodyB', 'PC0010_00_Eyebrow': T + 'PC0010_00_Hair',
        'PC0010_00_Hair': T + 'PC0010_00_Hair', 'PC0010_00_HairCore': T + 'PC0010_00_Hair',
    },
}
_last = [0]


def lua(v):
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if isinstance(v, dict):
        return '{' + ', '.join('%s = %s' % (k, lua(x)) for k, x in v.items()) + '}'
    raise TypeError(type(v))


def send(op, **fields):
    seq = max(int(time.time() * 1000), _last[0] + 1)
    _last[0] = seq
    cmd = dict(seq=seq, op=op)
    cmd.update(fields)
    path = os.path.join(LINK, 'command.lua')
    with open(path + '.tmp', 'w') as f:
        f.write('return ' + lua(cmd) + '\n')
    os.replace(path + '.tmp', path)
    end = time.time() + 6.0
    while time.time() < end:
        try:
            s = json.load(open(os.path.join(LINK, 'status.json')))
            if s.get('seq') == seq:
                return s
        except Exception:
            pass
        time.sleep(0.1)
    return None


def part_of(slot):
    """The Sephiroth material this slot wears (its own name or one up its parent chain)."""
    names = [slot.get('material') or ''] + list(slot.get('chain') or [])
    for n in names:
        short = n.rsplit('.', 1)[-1].rsplit(' ', 1)[-1]
        for part in sorted(PARTS, key=len, reverse=True):
            if short == part or short.startswith(part + '_') and short[len(part) + 1:].isdigit():
                return part
    return None


def main(mode):
    if mode not in SETS and mode not in ('reset', 'list'):
        print('which set? %s, reset or list' % ', '.join(sorted(SETS)))
        return 2
    if mode != 'list':
        s = send('reset_materials')
        if s is None:
            print('the game did not answer (is it running, with RebirthLiveLink?)')
            return 1
        print('originals back on %s slot(s)' % (s.get('result') or {}).get('reset'))
        if mode == 'reset':
            return 0
    s = send('materials')
    if s is None:
        print('the game did not answer (is it running, with RebirthLiveLink?)')
        return 1
    r = s.get('result', {})
    if not r.get('ok'):
        print('materials: %s' % r.get('error'))
        return 1
    print('character: %s' % r.get('character'))
    todo = []
    for comp in r.get('components', []):
        print('component %s %s (%s)' % (comp['index'], comp['name'], comp.get('mesh')))
        for slot in comp.get('slots', []):
            part = part_of(slot)
            if part and mode in SETS and part not in SETS[mode]:
                part = None                    # a part this set leaves as it is
            print('   slot %2d %-70s %s' % (slot['slot'], (slot.get('material') or '')[-70:], part or ''))
            if part:
                todo.append((comp['index'], slot['slot'], part))
    if mode == 'list':
        return 0
    if not todo:
        print('no Sephiroth (PC0010_00) material on the controlled character')
        return 1
    wear = SETS[mode]
    failed = 0
    for comp, slot, part in todo:
        res = {}
        for attempt in range(10):
            s = send('slot_material', component=comp, slot=slot, path=wear[part])
            res = (s or {}).get('result', {})
            if res.get('ok') or 'not loaded yet' not in str(res.get('error')):
                break
            time.sleep(0.6)
        failed += 0 if res.get('ok') else 1
        print('component %s slot %d (%s) -> %s: %s' % (comp, slot, part, wear[part].rsplit('/', 1)[-1],
                                                       'ok' if res.get('ok') else res.get('error')))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'list'))
