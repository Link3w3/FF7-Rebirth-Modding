"""The Galian Beast form's blend spaces: Vincent's own (his four locked-on strafes and his turn in place, Zen packages of the
game's) under the form's build folder (RebirthSkelCompat/Built/VincentGalian/<set>/<name>), made for the beast's skeleton
and sampling the form's moves of those names (galian_moves.json):
  * Battle07: the built Battle07 walks and turns, the beast's own idle (B_Idle01_1 of the set: Battle00/B_Idle01_1),
  * Battle08 (Punisher mode): Battle08's own walks and turns where it has them (Cloud's Battle01 names), Battle07's
    otherwise, and its idle (the beast's Battle00/B_Idle02_1).
Each blend space: its package name, its export's global id, its skeleton import and every sample import (and the import
graph's packages) changed; its export data as it was.
    make_galian_blendspaces.py <out dir> [plan json]"""
import json, os, struct, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/vincentfix', '/work/weap1012/tools',
                '/work/evil1013/tools']
from zen import Zen
import zenrename
import iostore_write as W
import make_bp

NULL = 0xFFFFFFFFFFFFFFFF
imp = make_bp.imp
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN = os.path.join(HERE, 'plan', 'galian_moves.json')
VINCENT = '/Game/Motion/Player/PC0011_Vincent/Battle00/'
FILES = {'B_StrafingWalk01_0': '/work/galian1016/pkgs/Motion__Player__PC0011_Vincent__Battle00__B_StrafingWalk01_0.uasset',
         'B_StrafingWalk01_1': '/work/galian1016/pkgs/Motion__Player__PC0011_Vincent__Battle00__B_StrafingWalk01_1.uasset',
         'B_StrafingWalk01_2l': '/work/galian1016/pkgs/Motion__Player__PC0011_Vincent__Battle00__B_StrafingWalk01_2l.uasset',
         'B_StrafingWalk01_2r': '/work/galian1016/pkgs/Motion__Player__PC0011_Vincent__Battle00__B_StrafingWalk01_2r.uasset',
         'B_Turn01': '/work/galian1017/pkgs/Motion__Player__PC0011_Vincent__Battle00__B_Turn01.uasset'}
SRC_SKEL = '/Game/Character/Player/PC0011_00_Vincent_Standard/Model/PC0011_00_Skeleton'
NEW_SKEL = '/Game/Character/Enemy/EB2160_00_VincentValentine_Standard/Model/EB2160_00_Skeleton'
SETS = ('Battle07', 'Battle08')


def split(name):
    """'B_StrafingWalk01_2l' -> ('B_StrafingWalk01', 0, '2l')? A name's FName base and number as the cook stores it."""
    base, _, tail = name.rpartition('_')
    if tail.isdigit() and not (len(tail) > 1 and tail[0] == '0'):
        return base, int(tail) + 1
    return name, 0


def sample_target(plan, set_name, sample):
    """The form's animation a sample of Vincent's plays in `set_name`: (object path, how)."""
    moves = {(m['set'], m['name']): m for m in plan['moves']}
    built = plan['build_folder']
    for s in ((set_name,) if set_name == 'Battle07' else (set_name, 'Battle07')):
        m = moves.get((s, sample))
        if m and m['build']:
            return '%s/%s/%s.%s' % (built, s, sample, sample), 'built %s' % s
    m = moves.get((set_name, sample))
    if m and m['kind'] == 'as_is':
        return m['animation'], 'the beast\'s own (%s)' % m['animation'].split('EB2160_VincentValentine/')[1].split('.')[0]
    raise AssertionError((set_name, sample, 'no move of the form plays it'))


def graph(d, z):
    o = z.graph_off
    n = struct.unpack_from('<i', d, o)[0]
    o += 4
    out = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', d, o)
        out.append((pid, bytes(d[o + 8:o + 12 + 8 * na])))
        o += 12 + 8 * na
    assert o == z.graph_off + z.graph_size
    return out


def make(plan, name, set_name):
    src = open(FILES[name], 'rb').read()
    z = Zen(src)
    assert len(z.exports) == 1 and z.exports[0]['global_import'] != NULL, name
    old_pkg = VINCENT + name
    new_pkg = '%s/%s/%s' % (plan['build_folder'], set_name, name)
    assert z.mapped(z.name_mapped) == old_pkg, (name, z.mapped(z.name_mapped))
    assert z.exports[0]['global_import'] == imp(old_pkg + '.' + name)
    base, number = split(name)
    old_base, new_base = VINCENT + base, '%s/%s/%s' % (plan['build_folder'], set_name, base)
    renames = {old_base: new_base, SRC_SKEL: NEW_SKEL}
    for old in renames:
        assert old in z.names, (name, old)
    assert new_base not in z.names and NEW_SKEL not in z.names
    d = bytearray(zenrename.rebuild(src, renames, {0: imp(new_pkg + '.' + name)}))
    nz = Zen(bytes(d))
    assert nz.mapped(nz.name_mapped) == new_pkg, (nz.mapped(nz.name_mapped), new_pkg)
    # imports: the skeleton and every sample
    changes, packages, report = {}, {}, []
    old_skel, new_skel = imp(SRC_SKEL + '.PC0011_00_Skeleton'), imp(NEW_SKEL + '.EB2160_00_Skeleton')
    for i, v in enumerate(nz.imports):
        if v == old_skel:
            changes[i] = new_skel
            packages[W.package_id(SRC_SKEL)] = W.package_id(NEW_SKEL)
    assert len(changes) == 1, (name, 'skeleton imports', changes)
    samples = []   # (the name map keeps each sample's package name without its number)
    for n in z.names:
        if n.startswith(VINCENT) and n != old_base:
            short = n[len(VINCENT):]
            for k in range(0, 12):
                full = short if k == 0 else '%s_%d' % (short, k - 1)
                if imp(VINCENT + full + '.' + full) in nz.imports:
                    samples.append(full)
    samples = sorted(set(samples))
    assert samples, name
    for s in samples:
        target, how = sample_target(plan, set_name, s)
        i = nz.imports.index(imp(VINCENT + s + '.' + s))
        assert i not in changes
        changes[i] = imp(target)
        packages[W.package_id(VINCENT + s)] = W.package_id(target.rsplit('.', 1)[0])
        report.append('%s -> %s' % (s, how))
    left = [i for i, v in enumerate(nz.imports) if v not in (NULL,) and i not in changes and (v >> 62) == 2]
    for i in left:   # (a package import left: it must be one of the engine's script objects, not Vincent's)
        raise AssertionError((name, 'an object import left', hex(nz.imports[i])))
    for i, v in changes.items():
        struct.pack_into('<Q', d, nz.imp_off + 8 * i, v)
    g = graph(bytes(d), nz)
    assert sum(1 for pid, _ in g if pid in packages) == len(packages), (name, 'graph packages')
    g = sorted([(packages.get(pid, pid), rest) for pid, rest in g], key=lambda x: x[0])
    gb = struct.pack('<i', len(g)) + b''.join(struct.pack('<Q', pid) + rest for pid, rest in g)
    assert len(gb) == nz.graph_size
    d[nz.graph_off:nz.graph_off + nz.graph_size] = gb
    out = bytes(d)
    c = Zen(out)
    assert out[c.header_end:] == src[z.header_end:], 'export data changed'
    assert c.cooked_header_size == z.cooked_header_size and c.flags == z.flags
    assert c.exports[0]['global_import'] == imp(new_pkg + '.' + name) and c.exports[0]['name'] == z.exports[0]['name']
    assert [k for k in range(len(z.imports)) if z.imports[k] != c.imports[k]] == sorted(changes)
    assert not any(pid in packages for pid, _ in graph(out, c))
    entry = dict(id=W.package_id(new_pkg), size=len(out), export_count=1, export_bundle_count=(c.graph_off - c.eb_off - 16) // 8, load_order=0,
                 imports=[pid for pid, _ in graph(out, c)])
    return out, entry, new_pkg, report


def main(out_dir, plan_file=PLAN):
    plan = json.load(open(plan_file))
    os.makedirs(out_dir, exist_ok=True)
    made = []
    for set_name in SETS:
        for name in FILES:
            data, entry, pkg, report = make(plan, name, set_name)
            rel = pkg[len('/Game/'):] + '.uasset'
            path = os.path.join(out_dir, rel.replace('/', '__'))
            open(path, 'wb').write(data)
            made.append(dict(path=rel, file=path, package=pkg, object=pkg + '.' + name, set=set_name, name=name, entry=entry))
            print('%s: %d bytes; %s' % (pkg, len(data), '; '.join(report)))
    json.dump(made, open(os.path.join(out_dir, 'blendspaces.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(*sys.argv[1:])
