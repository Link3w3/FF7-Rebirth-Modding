"""SephirothForms.json with his KH2 moves: every move of kh2_moves.json points his normal form (Battle00) at its built
animation (/Game/RebirthSkelCompat/Built/SephirothForms/Battle00/<name>), and the Meteor cast (B_AtkLimit03_0) plays the
KH2 hand raise in every form.
    update_json.py <json in> <kh2_moves.json> <json out> [<kh2_result.json>]   (moves the build reports as not built are left out)"""
import json, sys

BUILT = '/Game/RebirthSkelCompat/Built/SephirothForms/%s/%s.%s'


def main(src, manifest, dst, result=None):
    raw = open(src, encoding='utf-8').read()
    j = json.loads(raw)
    s = j['animation_sets'][0]
    kh2 = json.load(open(manifest))
    moves = s['moves']
    index = {(m['set'], m['key']): i for i, m in enumerate(moves)}
    added = replaced = 0
    failed = set(json.load(open(result)).get('failed', [])) if result else set()
    wanted = [(m['set'], m['name']) for m in kh2['moves'] if m['name'] not in failed]
    if failed:
        print('left out (not built):', ', '.join(sorted(failed)))
    if 'B_AtkLimit03_0' in failed:
        raise SystemExit('the Meteor cast was not built')
    # the Meteor cast in the winged and flying forms too
    cast = BUILT % ('Battle00', 'B_AtkLimit03_0', 'B_AtkLimit03_0')
    for set_name, key in wanted + [('Battle02', 'B_AtkLimit03_0'), ('Battle03', 'B_AtkLimit03_0')]:
        path = BUILT % (set_name, key, key) if set_name == 'Battle00' else cast
        entry = {'set': set_name, 'key': key, 'animation': path}
        if (set_name, key) in index:
            moves[index[(set_name, key)]] = entry
            replaced += 1
        else:
            index[(set_name, key)] = len(moves)
            moves.append(entry)
            added += 1
    s['moves'] = moves
    j['source'] = j['source'].rstrip('.') + ". His normal form plays his KH2 moves (idle, run, battle walk, combo, air combo, guard, dodge, damage, items, victory; built from the retargeted KH2 animations) and every form casts Meteor with the KH2 hand raise."
    open(dst, 'w', encoding='utf-8').write(json.dumps(j, indent=1, ensure_ascii=False) + ('\n' if raw.endswith('\n') else ''))
    print('moves: %d replaced, %d added, %d in all' % (replaced, added, len(moves)))


if __name__ == '__main__':
    main(*sys.argv[1:5])
