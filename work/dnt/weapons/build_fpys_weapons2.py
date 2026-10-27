"""FullyPlayableYoungSephirothDataAssets_P with Cloud's weapons spawning their own Masamunes, v2 (task #660).

v1 (2df9b604) pointed the 7 weapon packs at blueprints in folders of their own and left the CharaSpec table as it was: the
game spawns a weapon row's blueprint by the row's ContentsModel, a NAME under /Game/BluePrint/Character/Weapon/ (every one
of the game's 187 weapon blueprints sits right there, named so; FPS's rows name WE1021_00_SephirothIllusion_Masamune), and
finds it among what the row's pack loaded: with the packs no longer loading WE1021_00's, nothing was spawned at all (as
with v3 in October: "never showed on him"). So, on the build before v1 (5487bb62, the Dissidia NT form's):

  * seven blueprints of their own right in /Game/BluePrint/Character/Weapon/, each a copy of the game's playable
    (cut-scale) Masamune blueprint (a child of WE1021_00's) renamed to its sword (package, class and default object) and
    holding that sword's model, added to the container:
        WE1021_60_DNT_Masamune      Dissidia NT's Masamune            (Buster Sword)
        WE1021_62_DNT_Masamune2p    Dissidia NT's 2p1c Masamune       (Sleek Saber)
        WE1021_65_DNT_Masamune5p    Dissidia NT's 5p1c Masamune       (Rune Blade)
        WE1021_63_DNT_Masamune3p    Dissidia NT's 3p1c Masamune       (Umbral Blade)
        WE1021_67_Remake_Masamune   FF7 Remake's Masamune             (Crystal Sword)
        WE1021_64_DNT_Masamune4p    Dissidia NT's 4p1c Masamune       (Igneous Saber)
        WE1021_66_CC_Masamune       Crisis Core Reunion's Masamune    (Slipstream Saber)
    (the models: the Dissidia NT skins carry the DNT ones, the CRISIS CORE skins the CC one, the REMAKE skin the Remake one);
  * CharaSpec (the table): those 7 weapon rows' ContentsModel names its blueprint (everything else of the rows as it was:
    the Masamune's effect pack, its shared spec);
  * the 7 weapon packs: their 4 imports of WE1021_00's blueprint (class, default object, its SkeletalMeshComponent0, the
    class's DefaultSceneRoot_GEN_VARIABLE) name the same objects of the row's blueprint; graph and header entry likewise;
  * the header: those and the 7 blueprints' entries. CharaSpec_WE0000_17_Cloud_Umbrella keeps the Nameless.
    build_fpys_weapons2.py <installed base .utoc> <its tail> <v8 .ucas> <out dir (new)>"""
import contextlib, hashlib, io, json, os, struct, sys
sys.path[:0] = ['/work/dnt/weapons', '/work/dnt/form', '/work/fpys/tools', '/work/sephatb/tools',
                '/work/iostore', '/work/cs', '/work/tools', '/work/evil1013/tools',
                '/work/swap1012/tools', '/work/vincentfix', '/work/weap1012/tools',
                '/work/evilboss1016/data', '/work/sephforms/tools', '/work/anime1025/masamune']
import build_form_data as F
import build_fpys_data as B
import build_fpys_weapons as V1
import build_atb as T
import make_anime_masamune as mam
from iostore import Toc
from zen import Zen
import zenrename
import iostore_write as W
import gameids
import hdr

NULL = 0xFFFFFFFFFFFFFFFF
BLOCK = F.BLOCK
FOLDER = '/Game/BluePrint/Character/Weapon/'
CUT = 'WE1021_10_SephirothIllusion_MasamuneCutScale'
CHARASPEC = 'DataObject/Resident/CharaSpec.uasset'
DNT_MESH = '/Game/Character/Weapon/WE1021_19_DissidiaNT_Masamune/Model/%s.%s'
# (row, weapon, blueprint name, its sword's model object)
JOBS = [
    ('WE0000_00_Cloud_BusterSword', 'Buster Sword', 'WE1021_60_DNT_Masamune', DNT_MESH % ('WE001021_19_00', 'WE001021_19_00')),
    ('WE0000_11_Cloud_END2Weapon1', 'Sleek Saber', 'WE1021_62_DNT_Masamune2p', DNT_MESH % ('WE001021_19_02', 'WE001021_19_02')),
    ('WE0000_12_Cloud_END2Weapon2', 'Rune Blade', 'WE1021_65_DNT_Masamune5p', DNT_MESH % ('WE001021_19_05', 'WE001021_19_05')),
    ('WE0000_13_Cloud_END2Weapon3', 'Umbral Blade', 'WE1021_63_DNT_Masamune3p', DNT_MESH % ('WE001021_19_03', 'WE001021_19_03')),
    ('WE0000_14_Cloud_END2Weapon4', 'Crystal Sword', 'WE1021_67_Remake_Masamune',
     '/Game/GameContents/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Model/WE1021_00.WE1021_00'),
    ('WE0000_15_Cloud_END2Weapon5', 'Igneous Saber', 'WE1021_64_DNT_Masamune4p', DNT_MESH % ('WE001021_19_04', 'WE001021_19_04')),
    ('WE0000_16_Cloud_END2Weapon6', 'Slipstream Saber', 'WE1021_66_CC_Masamune',
     '/Game/Character/Weapon/WE1021_16_CrisisCore_Masamune/Model/WE001021_16.WE001021_16'),
]


def imp(path):
    return (2 << 62) | gameids.objhash(path)


def renamed_copy(src, retail, name, mesh_obj):
    """the retail cut-scale Masamune blueprint as FOLDER + name: package, class and default object renamed, its mesh
    import pointed at mesh_obj, every graph arc waiting for its imported package's last export bundle (as
    make_anime_masamune.copy_package's); (bytes, store entry)"""
    src_pkg, new_pkg = mam.BP_OLD, FOLDER + name
    z = Zen(src)
    re_ = retail[W.package_id(src_pkg)]
    assert re_['size'] == len(src) and re_['export_count'] == len(z.exports)
    renames = {src_pkg: new_pkg, CUT + '_C': name + '_C', 'Default__' + CUT + '_C': 'Default__' + name + '_C'}
    for old in renames:
        assert old in z.names, old
    renamed = [dict(e, name=renames.get(e['name'], e['name'])) for e in z.exports]

    class Z2:
        pass
    z2 = Z2()
    z2.exports = renamed
    gis = {i: imp(mam.export_path(z2, i, new_pkg)) for i, e in enumerate(z.exports) if e['global_import'] != NULL}
    d = bytearray(zenrename.rebuild(src, renames, gis))
    nz = Zen(bytes(d))
    old_mesh, new_mesh = imp(mam.MESH_OLD + '.' + mam.MESH_OBJ), imp(mesh_obj)
    hits = [i for i, v in enumerate(nz.imports) if v == old_mesh]
    assert len(hits) == 1, hits
    struct.pack_into('<Q', d, nz.imp_off + 8 * hits[0], new_mesh)
    pid_map = {W.package_id(mam.MESH_OLD): W.package_id(mesh_obj.split('.', 1)[0])}
    g = mam.graph(bytes(d))
    for old_pid in pid_map:
        assert sum(1 for pid, _ in g if pid == old_pid) == 1 and old_pid in re_['imports']
    g = sorted([(pid_map.get(pid, pid), arcs) for pid, arcs in g], key=lambda x: x[0])
    g = [(pid, [(-1 if k % 2 == 0 else a) for k, a in enumerate(arcs)]) for pid, arcs in g]
    gb = bytearray(struct.pack('<i', len(g)))
    for pid, arcs in g:
        gb += struct.pack('<Qi', pid, len(arcs) // 2) + struct.pack('<%di' % len(arcs), *arcs)
    assert len(gb) == nz.graph_size
    d[nz.graph_off:nz.graph_off + nz.graph_size] = gb
    out = bytes(d)
    c = Zen(out)
    assert c.mapped(c.name_mapped) == new_pkg and c.mapped(c.srcname_mapped) == new_pkg
    assert [e['name'] for e in c.exports] == [renames.get(e['name'], e['name']) for e in z.exports]
    assert out[c.header_end:] == src[z.header_end:], 'export data changed'
    for i, e in enumerate(c.exports):
        if e['global_import'] != NULL:
            assert e['global_import'] == imp(mam.export_path(c, i, new_pkg))
    assert new_mesh in c.imports and old_mesh not in c.imports
    assert not [n for n in c.names if CUT in n and 'Model' not in n], [n for n in c.names if CUT in n]
    entry = dict(id=W.package_id(new_pkg), size=len(out), export_count=len(c.exports), export_bundle_count=mam.bundle_count(c),
                 load_order=re_['load_order'], imports=[pid_map.get(x, x) for x in re_['imports']])
    return out, entry


def main(utoc, tail, v8_ucas, out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    name = os.path.basename(utoc)[:-len('.utoc')]
    inst = V1.Reader(utoc, tail, v8_ucas)
    old = inst.t
    cid, store = hdr.parse_header(inst.read(0))
    assert cid == W.container_id_from_name(name)
    order = [old.chunk_id64(i) for i in range(old.entries) if old.chunk_type(i) == 2]
    entries = [dict(id=p, size=store[p]['size'], export_count=store[p]['export_count'], export_bundle_count=store[p]['export_bundle_count'],
                    load_order=store[p]['load_order'], imports=list(store[p]['imports'])) for p in order]
    assert W.container_header(cid, entries) == inst.read(0), 'the header does not write back as it is'
    entry_of = {e['id']: e for e in entries}
    m_i = inst.by_path[V1.MASAMUNE_PKG[len('/Game/'):] + '.uasset']
    V1.MASAMUNE_OBJS.clear()
    V1.MASAMUNE_OBJS.update(B.bp_exports(inst.read(m_i), V1.MASAMUNE_PKG))
    _, retail = hdr.parse_header(open(mam.RETAIL_HEADER, 'rb').read())
    src_bp = open(mam.SRC_BP, 'rb').read()
    changes, additions, report = {}, [], []
    os.makedirs(out)
    # the blueprints
    made = {}
    for row, weapon, bp_name, mesh_obj in JOBS:
        data, e = renamed_copy(src_bp, retail, bp_name, mesh_obj)
        assert e['id'] not in entry_of, bp_name + ' is in the container already'
        rel = (FOLDER + bp_name)[len('/Game/'):] + '.uasset'
        additions.append(dict(id64=e['id'], type=2, data=data, path=rel))
        entries.append(e)
        made[bp_name] = data
        os.makedirs(os.path.join(out, 'bp'), exist_ok=True)
        open(os.path.join(out, 'bp', bp_name + '.uasset'), 'wb').write(data)
        report.append('%s%s: the cut-scale Masamune blueprint renamed, holding %s (%d bytes; imports %s)' % (
            FOLDER, bp_name, mesh_obj.split('.', 1)[0], len(data), ', '.join('%016x' % x for x in e['imports'])))
    # the CharaSpec table: each row's ContentsModel
    ci = inst.by_path[CHARASPEC]
    with contextlib.redirect_stdout(io.StringIO()):
        cs = T.Table(inst.read(ci))
    before = {k: list(cs.row(k)) for k in cs.at}
    for row, weapon, bp_name, mesh_obj in JOBS:
        r = cs.row(row)
        assert cs.get(r, 'ContentsModel') == 'WE1021_00_SephirothIllusion_Masamune', (row, cs.get(r, 'ContentsModel'))
        cs.set(r, 'ContentsModel', bp_name)
        report.append('CharaSpec %s (%s): ContentsModel WE1021_00_SephirothIllusion_Masamune -> %s' % (row, weapon, bp_name))
    with contextlib.redirect_stdout(io.StringIO()):
        cdata = cs.encode()
        cs2 = T.Table(cdata)
    for k, r in before.items():
        if k in [j[0] for j in JOBS]:
            want = dict(zip([f[0][0] for f in cs.fields], r))
            got = dict(zip([f[0][0] for f in cs.fields], cs2.row(k)))
            assert all(want[f] == got[f] for f in want if f != 'ContentsModel'), k
            assert cs2.get(cs2.row(k), 'ContentsModel') == [j[2] for j in JOBS if j[0] == k][0]
        else:
            assert cs2.row(k) == r, k
    e = entry_of[old.chunk_id64(ci)]
    assert e['size'] >> 60 == 0 and e['size'] in (0, len(inst.read(ci)))
    if e['size']:
        e['size'] = len(cdata)
    changes[ci] = cdata
    # the packs
    for row, weapon, bp_name, mesh_obj in JOBS:
        pkg = FOLDER + bp_name
        objs = set(B.bp_exports(made[bp_name], pkg))
        i = inst.by_path[B.PACK % row]
        data = inst.read(i)
        new, names = V1.swap(data, row, pkg, bp_name, objs)
        e = entry_of[old.chunk_id64(i)]
        old_pid, new_pid = W.package_id(V1.MASAMUNE_PKG), W.package_id(pkg)
        assert old_pid in e['imports'] and new_pid not in e['imports']
        e['imports'] = [new_pid if x == old_pid else x for x in e['imports']]
        assert e['size'] in (0, len(data))
        changes[i] = new
        report.append('CharaSpec_%s (%s): its 4 imports of WE1021_00_SephirothIllusion_Masamune -> %s (%s)' % (
            row, weapon, bp_name, ', '.join(b for a, b in names)))
    changes[0] = W.container_header(cid, entries)
    path = os.path.join(out, name)
    tail_new = F.append(old, inst.size, changes, additions, path + '.utoc', path + '.ucas.tail')
    new = Toc(path + '.utoc', ucas='/nonexistent')
    assert new.container_id == cid and new.entries == old.entries + len(additions)

    def new_read(k):
        off, ln = new.offlen[k]
        first, last = off // BLOCK, (off + ln - 1) // BLOCK
        buf = bytearray()
        for bi in range(first, last + 1):
            pos, csz, usz, m = new.blocks[bi]
            assert pos >= inst.size, (k, 'not in the new tail')
            buf += tail_new[pos - inst.size:pos - inst.size + csz]
        s = off - first * BLOCK
        return bytes(buf[s:s + ln])
    same = 0
    for k in range(new.entries):
        meta = new.b[new.metas_off + 33 * k:new.metas_off + 33 * k + 20]
        if k < old.entries:
            assert new.files.get(k) == old.files.get(k) and new.chunk_id64(k) == old.chunk_id64(k)
            if k in changes:
                d = new_read(k)
                assert d == changes[k] and hashlib.sha1(d).digest() == meta
            else:
                assert new.offlen[k] == old.offlen[k] and meta == inst.sha(k)
                same += 1
        else:
            a = additions[k - old.entries]
            d = new_read(k)
            assert d == a['data'] and hashlib.sha1(d).digest() == meta and new.files.get(k) == F.MOUNT + a['path']
    cid2, ents = hdr.parse_header(new_read(0))
    assert cid2 == cid and len(ents) == len(entries)
    for e in entries:
        bb = ents[e['id']]
        for key in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert bb[key] == e[key], key
    sums = dict(base_size=inst.size, base_utoc_md5=hashlib.md5(old.b).hexdigest(),
                utoc_md5=hashlib.md5(open(path + '.utoc', 'rb').read()).hexdigest(),
                tail_size=len(tail_new), tail_md5=hashlib.md5(tail_new).hexdigest(), ucas_size=inst.size + len(tail_new))
    json.dump(sums, open(os.path.join(out, 'build.json'), 'w'), indent=1)
    report.append('%s: %d chunks (%d before; %d as they were; %d changed: the CharaSpec table, 7 weapon packs and the header; %d '
                  'blueprints added); .ucas %d -> %d bytes' % (name, new.entries, old.entries, same, len(changes), len(additions),
                                                             inst.size, inst.size + len(tail_new)))
    open(os.path.join(out, 'report.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))
    print(json.dumps(sums))


if __name__ == '__main__':
    main(*sys.argv[1:5])
