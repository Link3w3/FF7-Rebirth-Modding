"""Ties the coat's strips of a compat file's "kawaii" entries made by another tool (Young Sephiroth's make_ys_kawaii.py):
make_kawaii_preset.py's tie_coat (COAT_TIES, COAT_BRIDGES, COAT_COMPLIANCE from the environment, the same defaults) on each
entry's coat nodes ("coat ..." with Coat or Skirt strips), with the model's rig for the strips' bones; optionally the coat
nodes' gravity scaled (--gravity-scale: the coat heavier hangs further in).

    tie_coat_file.py <rig.json> <in.json> <out.json> [--gravity-scale X] [--note TEXT]

Written as the game mod's tools write compat files (indent 1, CRLF). The other nodes are left as they are."""
import argparse
import json
import os
import sys

sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
import make_kawaii_preset as mk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rig')
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--gravity-scale', type=float, default=1.0)
    ap.add_argument('--note', help="text added to the file's note")
    a = ap.parse_args()
    rig = mk.Rig(a.rig)
    doc = json.load(open(a.src, encoding='utf-8'))
    for entry in doc.get('kawaii', []):
        nodes = entry.get('nodes', [])
        if a.gravity_scale != 1.0:
            for n in nodes:
                if n.get('name', '').startswith('coat') and 'gravity' in n:
                    n['gravity'] = [round(float(g) * a.gravity_scale, 1) for g in n['gravity']]
        tied_nodes, tied = mk.tie_coat(rig, nodes)
        entry['nodes'] = tied_nodes
        print('%s: %d nodes (was %d); tied: %s' % (entry.get('name'), len(tied_nodes), len(nodes), ', '.join(tied) or 'none'))
    if a.note and a.note not in doc.get('note', ''):
        doc['note'] = (doc.get('note', '') + ' ' + a.note).strip()
    with open(a.out, 'w', encoding='utf-8', newline='\r\n') as f:
        json.dump(doc, f, indent=1)
        f.write('\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
