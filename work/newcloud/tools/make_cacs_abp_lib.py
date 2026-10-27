"""Create a Character System: Rebirth AnimBlueprint Maker.

Makes a character's AnimBlueprint from one of the game's own (a template: Cloud's player AnimBlueprint by default), made
for the character's skeleton, ready for the game: the template's cooked package under the new name, with its skeleton
the character's. Everything the template does stays: its locomotion state machines (field and battle), the moves
player (the game's actions and abilities play through it), inertialization, the slots, facial, the movement and sword
expressions. The animations come from the character's animation sets (CharaSpec packs) by name, as for the game's own
characters, so nothing in it names an animation of the template's character.

    make_cacs_abp.py --skeleton /Game/Character/Player/PC0099_00_Hero/Model/PC0099_00_Skeleton
                     [--name PC0099_00_Hero_Standard_Animation] [--folder /Game/BluePrint/Animation/Player]
                     [--template cloud | sephiroth | vincent | monster | tifa ... (--list) | <a cooked AnimBlueprint .uasset>]
                     [--control-rig off | keep] [--container NAME] [--out DIR]
                     [--install] [--mods-folder CACS_AnimBlueprints] [--game "C:\\...\\FINAL FANTASY VII REBIRTH"]
    make_cacs_abp.py --list            (the templates)

--skeleton   the character's skeleton (its package path, as the editor shows it; the object is the last part, or give
             package.object). The skeleton must be in the game (cooked into the character's mod).
--name       the AnimBlueprint's name (default: the skeleton's folder + _Animation, as the game names them).
--template   which of the game's AnimBlueprints it is made from (see --list); default cloud.
--control-rig  the template's Control Rig node (the game's common human rig: it places the hips and feet by the legs of
             a Rebirth human skeleton): off (default: the node passes the pose through) or keep (only for a character on
             a Rebirth human skeleton, with the game's bone names).
--container  the mod container's name (default CACS_<name>_P); --out where it is written (default .\\out).
--install    also copies it into the game's ~mods\\<mods-folder> (refused while the game runs).

The new AnimBlueprint's class (for a form's "anim_class", a skin's "anim_blueprint", a character blueprint's AnimClass):
    <folder>/<name>.<name>_C
"""
import argparse, hashlib, json, os, shutil, struct, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'lib'))
from zen import Zen                    # noqa: E402
import zenrename                       # noqa: E402
import iostore_write as W              # noqa: E402
from hdr import parse_header           # noqa: E402
from cityhash import CityHash64        # noqa: E402

VERSION = '1.0.0'
NULL = 0xFFFFFFFFFFFFFFFF
MOUNT = '../../../End/Content/'
GAME = r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH'
TEMPLATES = {
    'cloud': ('PC0000_00_Cloud_Standard_Animation.uasset',
              "Cloud's player AnimBlueprint: field and battle locomotion, the moves player, slots, facial, the movement "
              "and sword expressions, the common human Control Rig (the default)"),
    'sephiroth': ('PC0010_00_Sephiroth_Standard_Animation.uasset', "Sephiroth's player AnimBlueprint (the same parts, made for him)"),
    'vincent': ('PC0011_00_Vincent_Standard_Animation.uasset', "Vincent's player AnimBlueprint (a gun user's)"),
    'monster': ('SU0004_00_Leviathan_Standard_Animation.uasset',
                "the bosses' and summons' AnimBlueprint (Leviathan's: their locomotion state machine, the moves player, "
                "inertialization, the move slot, facial and movement expression; no Control Rig)"),
}


def more_templates():
    """templates\\templates.json: more templates, the other characters' AnimBlueprints (as the editor's AnimBlueprint
    Maker lists them): {"templates": [{"key", "package", "label"}]}; a key already here takes its package and label."""
    try:
        with open(os.path.join(HERE, 'templates', 'templates.json'), encoding='utf-8') as f:
            data = json.load(f)
    except (IOError, OSError, ValueError):
        return
    for t in data.get('templates', []) if isinstance(data, dict) else []:
        key = str(t.get('key', '')).strip().lower()
        pkg = str(t.get('package', '')).strip()
        if not key or not pkg or ':' in key:
            continue
        label = str(t.get('label', '') or pkg).strip()
        if label.lower().startswith(key + ':'):
            label = label[len(key) + 1:].strip()
        TEMPLATES[key] = (pkg + '.uasset', label)


more_templates()


def objhash(path):
    s = ''.join('/' if c in '.:' else c.lower() for c in path)
    return CityHash64(s.encode('utf-16-le')) & ~(3 << 62)


def imp(path):
    """FPackageObjectIndex of an imported object (a package's object: /Game/A/B.B, a class: /Game/A/B.B_C)."""
    return (2 << 62) | objhash(path)


def export_path(exports, i, pkg):
    chain = []
    while True:
        e = exports[i]
        chain.append(e['name'])
        if e['outer'] == NULL:
            break
        i = e['outer']
    chain.reverse()
    path = pkg + '.' + chain[0]
    if len(chain) > 1:
        path += ':' + chain[1]
    for sub in chain[2:]:
        path += '.' + sub
    return path


def graph(d):
    z = Zen(d)
    o = z.graph_off
    n = struct.unpack_from('<i', d, o)[0]
    o += 4
    out = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', d, o)
        out.append((pid, list(struct.unpack_from('<%di' % (2 * na), d, o + 12)) if na else []))
        o += 12 + 8 * na
    assert o == z.graph_off + z.graph_size
    return out


def graph_bytes(g):
    gb = bytearray(struct.pack('<i', len(g)))
    for pid, arcs in g:
        gb += struct.pack('<Qi', pid, len(arcs) // 2) + struct.pack('<%di' % len(arcs), *arcs)
    return bytes(gb)


class Fail(Exception):
    pass


def leaf(path):
    return path.rsplit('/', 1)[1]


def read_template(src):
    """The template's package path, base name, generated class, skeleton and Control Rig (from its name map and imports)."""
    z = Zen(src)
    pkg = z.mapped(z.name_mapped)
    base = leaf(pkg)
    if base + '_C' not in [e['name'] for e in z.exports]:
        raise Fail('the template is not an AnimBlueprint (no class %s_C in it)' % base)
    # its skeleton: a /Game/... name whose object (package.leaf) it imports and whose leaf ends with _Skeleton
    skels = [n for n in z.names if n.startswith('/Game/') and leaf(n).lower().endswith('_skeleton') and imp(n + '.' + leaf(n)) in z.imports]
    if len(skels) != 1:
        raise Fail('the template\'s skeleton was not found (%s)' % (skels or 'none'))
    # Control Rig classes it imports (a /Game/... rig whose class and class default object it imports)
    rigs = []
    for n in z.names:
        if n.startswith('/Game/') and imp(n + '.' + leaf(n) + '_C') in z.imports:
            rigs.append(n)
    rigs = [r for r in rigs if 'rig' in leaf(r).lower()]
    return dict(z=z, pkg=pkg, base=base, skeleton=skels[0], rigs=rigs)


def make(src, new_pkg, skel_pkg, skel_obj, control_rig):
    t = read_template(src)
    z = t['z']
    src_pkg, src_base, src_skel = t['pkg'], t['base'], t['skeleton']
    new_base = leaf(new_pkg)
    for i, e in enumerate(z.exports):
        if e['global_import'] != NULL and imp(export_path(z.exports, i, src_pkg)) != e['global_import']:
            raise Fail('the template\'s public export %s is not where its name says (not a package this tool knows)' % e['name'])
    renames = {src_pkg: new_pkg}
    for n in z.names:
        if src_base in n and n not in renames:
            renames[n] = n.replace(src_base, new_base)
    same_skeleton = skel_pkg.lower() == src_skel.lower() and skel_obj.lower() == leaf(src_skel).lower()
    if not same_skeleton:
        renames[src_skel] = skel_pkg
        if skel_obj != leaf(src_skel):
            renames[leaf(src_skel)] = skel_obj
    names_after = [renames.get(n, n) for n in z.names]
    dup = sorted({n for n in names_after if names_after.count(n) > 1})
    if dup:
        raise Fail('the new names clash with names the template has: %s (choose another name)' % ', '.join(dup))
    renamed = [dict(e, name=renames.get(e['name'], e['name'])) for e in z.exports]
    gis = {i: imp(export_path(renamed, i, new_pkg)) for i, e in enumerate(z.exports) if e['global_import'] != NULL}
    d = bytearray(zenrename.rebuild(src, renames, gis))
    nz = Zen(bytes(d))
    notes = []
    if not same_skeleton:
        old_skel, new_skel = imp(src_skel + '.' + leaf(src_skel)), imp(skel_pkg + '.' + skel_obj)
        hits = [i for i, v in enumerate(nz.imports) if v == old_skel]
        if len(hits) != 1:
            raise Fail('the template imports its skeleton %d times' % len(hits))
        struct.pack_into('<Q', d, nz.imp_off + 8 * hits[0], new_skel)
        old_pid, new_pid = W.package_id(src_skel), W.package_id(skel_pkg)
        g = graph(bytes(d))
        if sum(1 for pid, _ in g if pid == old_pid) != 1:
            raise Fail('the template\'s dependency graph does not list its skeleton once')
        if any(pid == new_pid for pid, _ in g):
            raise Fail('the template already depends on the new skeleton\'s package')
        g = sorted([(new_pid if pid == old_pid else pid, arcs) for pid, arcs in g], key=lambda x: x[0])
        gb = graph_bytes(g)
        assert len(gb) == nz.graph_size
        d[nz.graph_off:nz.graph_off + nz.graph_size] = gb
    # Control Rig: its class and class default object imports nulled (the node then runs no rig: the pose passes through)
    if control_rig == 'off':
        for rig in t['rigs']:
            cls, cdo = imp(rig + '.' + leaf(rig) + '_C'), imp(rig + '.Default__' + leaf(rig) + '_C')
            hits = [i for i, v in enumerate(nz.imports) if v in (cls, cdo)]
            for i in hits:
                struct.pack_into('<Q', d, nz.imp_off + 8 * i, NULL)
            notes.append('Control Rig %s off (%d import(s) emptied)' % (leaf(rig), len(hits)))
    elif t['rigs']:
        notes.append('Control Rig %s kept' % ', '.join(leaf(r) for r in t['rigs']))
    out = bytes(d)
    # checks: the new package parses, has the new names, the template's export data unchanged, its public exports at
    # the indices their paths give
    c = Zen(out)
    assert c.mapped(c.name_mapped) == new_pkg and c.mapped(c.srcname_mapped) == new_pkg
    assert [e['name'] for e in c.exports] == [renames.get(e['name'], e['name']) for e in z.exports]
    assert out[c.header_end:] == src[z.header_end:], 'export data changed'
    assert c.cooked_header_size == z.cooked_header_size
    for i, e in enumerate(c.exports):
        if e['global_import'] != NULL:
            assert e['global_import'] == imp(export_path(c.exports, i, new_pkg))
    left = [n for n in c.names if src_base in n]
    assert not left, left
    if not same_skeleton:
        assert imp(skel_pkg + '.' + skel_obj) in c.imports and imp(src_skel + '.' + leaf(src_skel)) not in c.imports
    entry = dict(id=W.package_id(new_pkg), size=len(out), export_count=len(c.exports),
                 export_bundle_count=(c.graph_off - c.eb_off - 16 * len(c.exports)) // 8, load_order=0,
                 imports=[pid for pid, _ in graph(out)])
    return out, entry, t, notes


def write_container(out_dir, name, pkg, data, entry):
    rel = pkg[len('/Game/'):] + '.uasset'
    cid = W.container_id_from_name(name)
    chunks = [dict(id64=cid, type=10, data=W.container_header(cid, [entry]), path=None),
              dict(id64=entry['id'], type=2, data=data, path=rel)]
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, name)
    W.write_container(base, name, chunks, mount=MOUNT)
    shutil.copyfile(os.path.join(HERE, 'stub.pak'), base + '.pak')
    check_container(base, chunks, entry, rel)
    return [base + ext for ext in ('.utoc', '.ucas', '.pak')]


def check_container(base, chunks, entry, rel):
    """Reads the container back (uncompressed: the table of contents, each chunk, the header entry)."""
    toc = open(base + '.utoc', 'rb').read()
    ucas = open(base + '.ucas', 'rb').read()
    hsize, n_chunks, n_blocks, _, _, _, block, dsize, _ = struct.unpack_from('<IIIIIIIII', toc, 20)
    assert toc[:16] == b'-==--==--==--==-' and n_chunks == len(chunks)
    p = hsize
    ids = [struct.unpack_from('<QHBB', toc, p + 12 * i) for i in range(n_chunks)]
    p += 12 * n_chunks
    offlen = [(int.from_bytes(toc[p + 10 * i:p + 10 * i + 5], 'big'), int.from_bytes(toc[p + 10 * i + 5:p + 10 * i + 10], 'big')) for i in range(n_chunks)]
    p += 10 * n_chunks
    blocks = []
    for i in range(n_blocks):
        b = toc[p + 12 * i:p + 12 * i + 12]
        blocks.append((int.from_bytes(b[0:5], 'little'), int.from_bytes(b[5:8], 'little'), int.from_bytes(b[8:11], 'little'), b[11]))
    p += 12 * n_blocks
    for k, c in enumerate(chunks):
        off, ln = offlen[k]
        got = bytearray()
        first = off // block
        while len(got) < ln:
            pos, cs, us, m = blocks[first]
            assert m == 0 and cs == us
            got += ucas[pos:pos + cs]
            first += 1
        got = bytes(got[:ln])
        assert got == c['data'] and ids[k][0] == c['id64'] and ids[k][3] == c['type'], 'chunk %d reads back wrong' % k
    assert (MOUNT + rel).encode('ascii') in toc or rel.split('/')[-1].encode('ascii') in toc
    _, ents = parse_header(chunks[0]['data'])
    got = ents[entry['id']]
    assert all(got[f] == entry[f] for f in ('size', 'export_count', 'export_bundle_count', 'imports'))


def game_running():
    if os.name != 'nt':
        return None
    try:
        out = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True, timeout=30).stdout.lower()
    except Exception:
        return None
    return any(exe in out for exe in ('"ff7rebirth_.exe"', '"ff7rebirth.exe"'))


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def main(argv=None):
    a = argparse.ArgumentParser(description='Create a Character System: Rebirth AnimBlueprint Maker ' + VERSION)
    a.add_argument('--skeleton')
    a.add_argument('--name')
    a.add_argument('--folder', default='/Game/BluePrint/Animation/Player')
    a.add_argument('--template', default='cloud')
    a.add_argument('--control-rig', choices=['off', 'keep'], default='off')
    a.add_argument('--container')
    a.add_argument('--out', default=os.path.join(HERE, 'out'))
    a.add_argument('--install', action='store_true')
    a.add_argument('--mods-folder', default='CACS_AnimBlueprints')
    a.add_argument('--game', default=GAME)
    a.add_argument('--list', action='store_true')
    a.add_argument('--result', help='also write the result (JSON) to this file (for the editor)')
    args = a.parse_args(argv)
    result = dict(ok=False, version=VERSION)

    def finish(code, message):
        result['message'] = message
        print(message)
        if args.result:
            json.dump(result, open(args.result, 'w'), indent=1)
        return code

    if args.list:
        for k, (f, about) in TEMPLATES.items():
            there = os.path.exists(os.path.join(HERE, 'templates', f))
            print('%-10s %s%s' % (k, about, '' if there else '  [its file is missing: templates\\' + f + ']'))
        return 0
    if not args.skeleton:
        return finish(2, 'STOPPED: --skeleton is needed (the character\'s skeleton, e.g. /Game/Character/Player/PC0099_00_Hero/Model/PC0099_00_Skeleton)')
    skel = args.skeleton.strip().replace('\\', '/')
    if skel.startswith("SkeletalMesh'") or skel.startswith("Skeleton'"):
        skel = skel.split("'", 1)[1].rstrip("'")
    if '.' in leaf(skel):
        skel_pkg, skel_obj = skel.rsplit('.', 1)
    else:
        skel_pkg, skel_obj = skel, leaf(skel)
    if not skel_pkg.startswith('/Game/'):
        return finish(2, 'STOPPED: the skeleton must be a /Game/... path (got %s)' % args.skeleton)
    folder = '/' + args.folder.strip().replace('\\', '/').strip('/')
    if not folder.startswith('/Game'):
        return finish(2, 'STOPPED: --folder must be under /Game (got %s)' % args.folder)
    name = args.name
    if not name:
        parts = skel_pkg.split('/')
        owner = parts[-3] if len(parts) >= 4 and parts[-2].lower() == 'model' else skel_obj.replace('_Skeleton', '')
        name = owner + '_Animation'
    if not all(ch.isalnum() or ch == '_' for ch in name):
        return finish(2, 'STOPPED: the name may only have letters, digits and _ (got %s)' % name)
    new_pkg = folder + '/' + name
    tpl = args.template
    if tpl in TEMPLATES:
        tpl_file = os.path.join(HERE, 'templates', TEMPLATES[tpl][0])
    else:
        tpl_file = tpl
    if not os.path.exists(tpl_file):
        return finish(2, 'STOPPED: the template file is missing: %s' % tpl_file)
    src = open(tpl_file, 'rb').read()
    try:
        t0 = read_template(src)
        if new_pkg.lower() == t0['pkg'].lower():
            return finish(2, 'STOPPED: %s is the template\'s own name (it would replace the game\'s AnimBlueprint); choose another name' % name)
        data, entry, t, notes = make(src, new_pkg, skel_pkg, skel_obj, args.control_rig)
    except Fail as e:
        return finish(1, 'FAILED: ' + str(e))
    container = args.container or ('CACS_' + name + '_P')
    files = write_container(args.out, container, new_pkg, data, entry)
    cls = new_pkg + '.' + name + '_C'
    result.update(ok=True, anim_class=cls, package=new_pkg, skeleton=skel_pkg + '.' + skel_obj, template=t['pkg'],
                  container=container, files={os.path.basename(f): md5(f) for f in files}, notes=notes)
    lines = ['made %s (%d bytes) from %s' % (new_pkg, len(data), t['pkg']),
             '   its skeleton: %s.%s (the template\'s: %s)' % (skel_pkg, skel_obj, t['skeleton'])]
    lines += ['   ' + n for n in notes]
    lines += ['   container %s: %s' % (container, ', '.join('%s %s' % (os.path.basename(f), md5(f)) for f in files)),
              '   its class (a form\'s "anim_class", a skin\'s "anim_blueprint"): ' + cls]
    if args.install:
        running = game_running()
        if running:
            result['installed'] = False
            return finish(3, '\n'.join(lines) + '\nNOT INSTALLED: the game is running; close it and run this again (the container is in %s)' % args.out)
        mods = os.path.join(args.game, 'End', 'Content', 'Paks', '~mods')
        if not os.path.isdir(mods):
            result['installed'] = False
            return finish(3, '\n'.join(lines) + '\nNOT INSTALLED: the game\'s ~mods folder is not at %s' % mods)
        dest = os.path.join(mods, args.mods_folder) if args.mods_folder else mods
        os.makedirs(dest, exist_ok=True)
        for f in files:
            shutil.copyfile(f, os.path.join(dest, os.path.basename(f)))
            if md5(os.path.join(dest, os.path.basename(f))) != md5(f):
                result['installed'] = False
                return finish(1, '\n'.join(lines) + '\nFAILED: %s did not copy right into %s' % (os.path.basename(f), dest))
        result['installed'] = dest
        lines.append('   installed into %s (checked)' % dest)
    return finish(0, '\n'.join(lines) + '\nDONE')


if __name__ == '__main__':
    sys.exit(main())
