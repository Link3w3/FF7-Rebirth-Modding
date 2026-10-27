"""Seraph Sephiroth's KawaiiPhysics entry (the Seraph Sephiroth skins' model, /Game/Character/Player/
PC0010_15_Seraph_Sephiroth_Transformed/Model/PC0010_15): his model is painted to Rebirth's winged Sephiroth's bones
(PC0010_10's) but for his hair, so the winged entry's nodes are his (its coat, belts, collar and wing: copied as they
are), and his hair's nodes are made for him by the Rebirth preset from his own rig and mesh (make_kawaii_preset.py on his
rig: its hair, front hair and long hair nodes, colliders fitted to his reference pose).

Each copied node's bones (its chains and its colliders' bones) must be where the winged model has them (his reference
pose against the winged rig's, component space): a bone more than --tolerance cm or degrees off stops it.

    make_seraph_kawaii.py --rig seraph_rig.json --mesh seraph.npz --winged-rig PC0010_10.json --winged out/e_pc0010_10.json
                          --model PATH --out e_seraph.json [--tolerance 0.05]
The model has no Bonamik or KineDriver of its own (no SQEX_KBD_AssetUserData): nothing to take off."""
import argparse
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAIR_KINDS = ('hair', 'front hair', 'long hair')


def bones_of_node(n, kids):
    out = set()
    for root in [n['root_bone']] + [r if isinstance(r, str) else r.get('root_bone') or r.get('bone') for r in n.get('additional_root_bones', [])]:
        stack = [root]
        while stack:
            b = stack.pop()
            out.add(b)
            stack.extend(k for k in kids.get(b, []) if k.endswith('_Phy'))
    for key in ('spheres', 'capsules', 'tapered_capsules', 'boxes', 'planes'):
        for sh in n.get(key, []):
            if sh.get('bone'):
                out.add(sh['bone'])
    for c in n.get('bone_constraints', []):
        out.update(c if isinstance(c, list) else [c.get('bone1'), c.get('bone2')])
    return out


def qang(p, q):
    return math.degrees(2 * math.acos(min(1.0, abs(sum(a * b for a, b in zip(p, q))))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rig', required=True)
    ap.add_argument('--mesh', required=True)
    ap.add_argument('--winged-rig', required=True)
    ap.add_argument('--winged', required=True)
    ap.add_argument('--model', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--tolerance', type=float, default=0.05)
    a = ap.parse_args()
    rig = json.load(open(a.rig))['bones']
    wrig = json.load(open(a.winged_rig))['bones']
    by = {b['name']: b for b in rig}
    wby = {b['name']: b for b in wrig}
    kids = {}
    for b in rig:
        if b['parent']:
            kids.setdefault(b['parent'], []).append(b['name'])
    winged = json.load(open(a.winged, encoding='utf-8'))['kawaii'][0]
    copied, bad = [], []
    for n in winged['nodes']:
        if any(n['name'].startswith(k + ' ') for k in HAIR_KINDS):
            continue
        shapes = [sh for key in ('spheres', 'capsules', 'tapered_capsules', 'boxes', 'planes') for sh in n.get(key, [])]
        shape_bones = {sh['bone'] for sh in shapes if sh.get('bone')}
        if n['name'].startswith('wing ') and not shapes:
            copied.append(n)   # (no colliders: its chain swings wherever its bones are; his wing's feathers are placed his own way)
            continue
        for b in sorted(bones_of_node(n, kids)):
            if b not in by or b not in wby:
                bad.append('%s: bone %s missing' % (n['name'], b))
                continue
            dt = math.dist(by[b]['t'], wby[b]['t'])
            dq = qang(by[b]['q'], wby[b]['q'])
            # a collider's bone exactly (its shapes' offsets are in its space), a chain's bones closely
            tol_t, tol_q = (a.tolerance, a.tolerance) if b in shape_bones else (1.0, 2.0)
            if dt > tol_t or dq > tol_q:
                bad.append('%s: bone %s %.3f cm, %.3f degrees off the winged rig' % (n['name'], b, dt, dq))
        copied.append(n)
    if bad:
        print('FAILED: the copied nodes\' bones are not where the winged model has them:\n  ' + '\n  '.join(bad[:40]))
        return 1
    # his own hair: the preset on his rig and mesh (the hair kinds only)
    full = a.out[:-5] + '.preset.json'
    r = subprocess.run([sys.executable, os.path.join(HERE, 'make_kawaii_preset.py'), '--rig', a.rig, '--mesh', a.mesh, '--model', a.model,
                        '--bonamik', 'false', '--kinedriver', 'false', '--name', 'Seraph Sephiroth (preset)', '--out', full],
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stdout, r.stderr)
        return 1
    print(r.stdout.strip())
    preset = json.load(open(full, encoding='utf-8'))['kawaii'][0]
    hair = [n for n in preset['nodes'] if any(n['name'].startswith(k + ' ') for k in HAIR_KINDS)]
    # only the hair chains his hair is skinned to (a chain none of his vertices follow moves nothing)
    import numpy as np
    m = np.load(a.mesh)
    names = [str(b) for b in m['bones']]
    weighted = {names[b] for b, w in zip(m['w_bone'], m['w_weight']) if w > 0.02}
    unused = [n['name'] for n in hair if not (bones_of_node(dict(n, spheres=[], capsules=[], tapered_capsules=[]), kids) & weighted)]
    hair = [n for n in hair if n['name'] not in unused]
    if unused:
        print('left out (no vertex follows them): ' + ', '.join(unused))
    nodes = hair + copied
    assert len(nodes) <= 64, len(nodes)
    entry = {'name': 'Seraph Sephiroth (PC0010_15_Seraph_Sephiroth_Transformed): his own hair; coat, belts, collar, wing as the '
                     'winged Sephiroth\'s', 'models': [a.model], 'preset': 'rebirth', 'nodes': nodes}
    doc = {'schema': 'RebirthSkelCompat/1', 'note': 'KawaiiPhysics for Seraph Sephiroth: the winged Sephiroth\'s nodes (PC0010_10\'s bones) '
                                                    'and his own hair\'s from the Rebirth preset', 'kawaii': [entry]}
    with open(a.out, 'w', encoding='utf-8', newline='\r\n') as f:
        json.dump(doc, f, indent=1)
        f.write('\n')
    print('%s: %d nodes: %d of his hair (%s), %d copied from the winged entry (%s)' % (
        a.out, len(nodes), len(hair), ', '.join(n['name'] for n in hair), len(copied), ', '.join(n['name'] for n in copied)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
