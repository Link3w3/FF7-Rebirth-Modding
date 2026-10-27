"""(3.17.0) Puts the feet colliders and sync bones (kawaii_feet_sync.py) into the user's kawaii compat files: each entry
with its model's skeleton (and mesh, for the feet's sizes) from the offline data, the files written as they were (indent
1, their own line ends). Cloud's pants hang from his legs (they move with them already): his file is left as it is.
    python3 make_kawaii_feet_sync.py in_dir out_dir"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kawaii_feet_sync as kfs

W = '/work'
KP = W + '/kawaii_preset'
MODELS = {   # (file, entry): (rig, mesh)
    ('YoungSephirothKawaii.json', 0): (W + '/ys/rig/rig.json', W + '/ysskirt/body.npz'),
    ('SephirothKawaii.json', 0): (KP + '/rigs/PC0010_00.json', KP + '/meshes/PC0010_00.npz'),
    ('SephirothKawaii.json', 1): (KP + '/rigs/PC0010_10.json', KP + '/meshes/PC0010_10.npz'),
    ('SephirothKawaii.json', 2): (KP + '/rigs/EB0021_00.json', None),
    ('SephirothKawaii.json', 3): (KP + '/rigs/EB0021_01_Body.json', None),
    ('SephirothKawaii.json', 4): (KP + '/rigs/PC0010_15_Seraph.json', KP + '/meshes/PC0010_15_Seraph.npz'),
    ('CrisisCoreSephirothKawaii.json', 0): (W + '/ccseph/kawaii/pc0010_16_rig.json', W + '/ccseph/kawaii/pc0010_16_mesh.npz'),
    ('CrisisCoreSephirothKawaii.json', 1): (W + '/ccseph/kawaii/pc0010_16_rig.json', W + '/ccseph/kawaii/pc0010_16_mesh.npz'),
    ('BahamutFusedSephirothKawaii.json', 0): (W + '/bfs17/kawaii/rig.json', W + '/bfs17/kawaii/body.npz'),
}
NOTE = (' 3.17.0 (Kawaii Dynamic Motions\' sync bones): the coats\' and mantles\' chains follow the knees (KawaiiPhysics\' '
        'SyncBone: the chains in front of a leg when its knee comes forward and up, the ones behind it when it goes back, '
        'the side ones when it goes out), and the ones that reach below the knees have the feet as colliders, so a heel '
        'kicking back in a run or a kick no longer goes through the cloth as often. Needs the game mod 3.17.0 for the sync '
        'bones (an older one reads the feet and leaves the sync bones out).')


def main():
    src, dst = sys.argv[1:3]
    os.makedirs(dst, exist_ok=True)
    files = sorted({f for f, _ in MODELS})
    for name in files:
        raw = open(os.path.join(src, name), 'rb').read()
        crlf = b'\r\n' in raw
        text = raw.decode('utf-8-sig')
        data = json.loads(text)
        # (a file made again from its original: the earlier run's sync bones and feet replaced, not added twice)
        print(name)
        for i, entry in enumerate(data['kawaii']):
            key = (name, i)
            if key not in MODELS:
                print('  entry %d (%s): no model data, left as it is' % (i, entry.get('name', '')))
                continue
            rig_path, mesh = MODELS[key]
            print('  entry %d: %s' % (i, entry.get('name', '')))
            kfs.apply(entry, kfs.Rig(rig_path), mesh, log=print)
        note = data.get('note', '')
        if '3.17.0 (Kawaii Dynamic Motions' not in note:
            data['note'] = note.rstrip() + NOTE
        out = json.dumps(data, indent=1)
        if text.replace('\r\n', '\n').endswith('\n'):
            out += '\n'
        if crlf:
            out = out.replace('\n', '\r\n')
        open(os.path.join(dst, name), 'wb').write(out.encode('utf-8'))


if __name__ == '__main__':
    main()
