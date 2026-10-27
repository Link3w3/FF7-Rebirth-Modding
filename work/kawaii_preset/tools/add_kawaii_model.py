"""Put one more model on a "kawaii" entry of a compat file: the entry that lists a model already (its nodes, colliders and
Bonamik / KineDriver switches) is used for the new one too. For a model on the same bones and body as that one: the
Anime Sephiroth skin's PC0010_01 is the winged Sephiroth's PC0010_10 brought back from an FBX (the same 777 bones in
the same reference pose, the same vertices, the same PC0010_10_BNM / KDI / KDI_Extra1 in its asset user data).

    add_kawaii_model.py <compat.json> <model listed> <model to add> [--name TEXT] [--note TEXT]

The file is written as make_kawaii_preset.py / merge_kawaii.py write it (indent 1, CRLF); run it again after those
remake the file. A model already listed is left as it is."""
import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('compat')
    ap.add_argument('listed')
    ap.add_argument('add')
    ap.add_argument('--name', help="the entry's new name (the mod does not read it: for whoever reads the file)")
    ap.add_argument('--note', help="text added to the file's note (before its last sentence, \"Needs the game mod ...\")")
    a = ap.parse_args()
    doc = json.load(open(a.compat, encoding='utf-8'))
    hits = [e for e in doc.get('kawaii', []) if any(m.lower() == a.listed.lower() for m in e.get('models', []))]
    if len(hits) != 1:
        print('FAILED: %d entries list %s (one expected)' % (len(hits), a.listed))
        return 1
    entry = hits[0]
    others = [e for e in doc['kawaii'] if e is not entry and any(m.lower() == a.add.lower() for m in e.get('models', []))]
    if others:
        print('FAILED: %s is on another entry already (%s)' % (a.add, others[0].get('name')))
        return 1
    if not any(m.lower() == a.add.lower() for m in entry['models']):
        entry['models'].append(a.add)
    if a.name:
        entry['name'] = a.name
    if a.note and a.note not in doc.get('note', ''):
        note = doc.get('note', '')
        cut = note.rfind(' Needs the game mod ')
        doc['note'] = (note[:cut] + ' ' + a.note + note[cut:]) if cut >= 0 else (note + ' ' + a.note).strip()
    with open(a.compat, 'w', encoding='utf-8', newline='\r\n') as f:
        json.dump(doc, f, indent=1)
        f.write('\n')
    print('%s: %s on "%s" (models: %s)' % (a.compat, a.add, entry['name'], ', '.join(entry['models'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
