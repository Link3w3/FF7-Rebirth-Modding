"""VincentDeathPenalty_P: Chaos's Death Penalty (the user's model, /Game/Character/Weapon/WE011_10_Chaos_DeathPenialty) from the
End project's packaging (pakchunk56, its PrimaryAssetLabel), in a container of its own name (its id from that name, so it
clashes with no pakchunk of the game's or another mod's):
  * its muzzle (the bone C_VFXMuzzleA_a, the socket VFX_Muzzle01's: where the shots start and the flash plays) moved to the
    end of its barrel: the skeleton was the Quicksilver's, whose muzzle is 36 cm from the grip; the Death Penalty's barrel
    ends 96 cm out (the bone's place in the mesh's and the skeleton's reference pose, the same bytes in each, so nothing
    else in either moves),
  * the textures its material does not use (H, M, MA, MB, N_OpenGL: in its folder, cooked by the label) left out,
every chunk read back and checked.
    build_death_penalty_pak.py <out dir (new)> <pakchunk56 .utoc>"""
import os, struct, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools', '/work/sephforms/tools',
                '/work/shooter1016/tools']
import build_dirge_paks as P
import iostore_write as W
from zen import Zen

NAME = 'VincentDeathPenalty_P'
FOLDER = 'Character/Weapon/WE011_10_Chaos_DeathPenialty/'
MESH = FOLDER + 'Model/WE0011_10.uasset'
SKELETON = FOLDER + 'Model/WE0011_10_Skeleton.uasset'
UNUSED = ['Textures/9caf8138-6e9b-4850-ba87-ea5b100a3878_%s.uasset' % s for s in ('H', 'M', 'MA', 'MB', 'N_OpenGL')]
BONES = ['Trans', 'C_Body_a', 'C_Body_End', 'C_Trigger_a', 'C_Trigger_End', 'C_VFXMuzzleA_a', 'C_Hammer_a', 'C_Hammer_End', 'C_Barrel_a',
         'C_Barrel_End', 'C_CharaA_a']
MUZZLE = 5
OLD = (0.0, 0.3616, 0.0737)   # in C_Body_a (m, under the root's 100 scale): 36 cm down the barrel, 7 cm up
NEW = (0.012, 0.955, 0.06)    # the barrel's end: 95.5 cm out, 6 cm up, 1.2 cm to its side (the mesh's own middle there)


def bone_pose_at(data, names):
    """Where the reference skeleton's poses are: its bone list (name, parent) as BONES, then the poses."""
    trans = names.index('Trans')
    pat = struct.pack('<i', len(BONES)) + struct.pack('<iIi', trans, 0, -1)
    at = data.find(pat)
    found = []
    while at >= 0:
        k = at + 4
        ok = True
        for b, name in enumerate(BONES):
            ni, num, parent = struct.unpack_from('<iIi', data, k + 12 * b)
            ok = ok and 0 <= ni < len(names) and names[ni] == name and num == 0
        if ok and struct.unpack_from('<i', data, k + 12 * len(BONES))[0] == len(BONES):
            found.append(k + 12 * len(BONES) + 4)
        at = data.find(pat, at + 1)
    assert len(found) == 1, ('the reference skeleton', len(found))
    return found[0]


def move_muzzle(data, label):
    z = Zen(data)
    poses = bone_pose_at(data, z.names)
    at = poses + 40 * MUZZLE + 16   # (each pose: rotation 4 floats, translation 3, scale 3)
    was = struct.unpack_from('<3f', data, at)
    assert all(abs(a - b) < 0.01 for a, b in zip(was, OLD)), (label, was)
    out = bytearray(data)
    struct.pack_into('<3f', out, at, *NEW)
    return bytes(out), was


def main(out, utoc):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    os.makedirs(out)
    chunks, store = P.read(utoc)
    paths = {c['path'] for c in chunks}
    for p in [MESH, SKELETON] + [FOLDER + u for u in UNUSED]:
        assert p in paths, p
    # nothing imports the textures left out
    unused_ids = {W.package_id('/Game/' + (FOLDER + u)[:-len('.uasset')]) for u in UNUSED}
    for c in chunks:
        if c['type'] == 2:
            assert not unused_ids & set(store[c['id64']]['imports']), c['path']
    kept, moved = [], []
    for c in chunks:
        if c['path'] in {FOLDER + u for u in UNUSED}:
            continue
        c = dict(c)
        if c['path'] in (MESH, SKELETON):
            c['data'], was = move_muzzle(c['data'], c['path'])
            moved.append('%s %s -> %s' % (c['path'].rsplit('/', 1)[-1], tuple(round(v, 3) for v in was), NEW))
        kept.append(c)
    entries = [P.entry(c, store[c['id64']]) for c in kept if c['type'] == 2]
    cid, files = P.write(out, NAME, kept, entries, utoc[:-len('.utoc')] + '.pak')
    report = ('%s (%016x) from %s: %d packages (left out: %s); the muzzle moved: %s; %s' %
              (NAME, cid, os.path.basename(utoc), len(entries), ', '.join(u.rsplit('/', 1)[-1] for u in UNUSED), '; '.join(moved), files))
    open(os.path.join(out, 'pak_report.txt'), 'w').write(report + '\n')
    print(report)


if __name__ == '__main__':
    main(*sys.argv[1:])
