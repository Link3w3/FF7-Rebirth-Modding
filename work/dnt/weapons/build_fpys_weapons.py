"""FullyPlayableYoungSephirothDataAssets_P with Cloud's weapon packs naming their own Masamunes (task #610/#660), built on
the INSTALLED container (build_form_data.py's way: its blocks stay, the changed chunks go after them in the .tail that
install_data_rebase.py appends to the installed .ucas, checked by size and MD5):

  CharaSpec_WE0000_00_Cloud_BusterSword   Buster Sword      Dissidia NT's Masamune (w_sev200_00)
  CharaSpec_WE0000_11_Cloud_END2Weapon1   Sleek Saber       Dissidia NT's 2p1c Masamune
  CharaSpec_WE0000_12_Cloud_END2Weapon2   Rune Blade        Dissidia NT's 5p1c Masamune
  CharaSpec_WE0000_13_Cloud_END2Weapon3   Umbral Blade      Dissidia NT's 3p1c Masamune
  CharaSpec_WE0000_14_Cloud_END2Weapon4   Crystal Sword     FF7 Remake's Masamune (the REMAKE skin's blueprint)
  CharaSpec_WE0000_15_Cloud_END2Weapon5   Igneous Saber     Dissidia NT's 4p1c Masamune
  CharaSpec_WE0000_16_Cloud_END2Weapon6   Slipstream Saber  Crisis Core Reunion's Masamune (CrisisCoreWeapon's)
  (CharaSpec_WE0000_17_Cloud_Umbrella keeps the Masamune's blueprint: the Nameless.)

Each pack named the Masamune's blueprint (/Game/BluePrint/Character/Weapon/WE1021_00_SephirothIllusion_Masamune: its class,
its default object, the default object's SkeletalMeshComponent0 and the class's DefaultSceneRoot_GEN_VARIABLE, FPS's way):
those four imports now name the same objects of the sword's blueprint (a copy of the cut-scale Masamune's, class
WE1021_10_SephirothIllusion_MasamuneCutScale_C, or the Remake skin's WE1021_00_SephirothIllusion_Masamune_C), each checked to be
one of that blueprint's exports; the pack's graph names the blueprint's package in the Masamune's place (its arcs wait for
the package's last export bundle, as the copied blueprints' own arcs do), and so does its header entry. Every other byte of
every pack is as it was; the container keeps its name and id.

Chunks are read from the v8 build's .ucas (the installed .ucas begins with it: checked by MD5 before) or the installed
build's own tail, each checked against the container's hash.
    build_fpys_weapons.py <installed .utoc> <installed build's .tail> <v8 .ucas> <out dir (new)>"""
import hashlib, json, os, struct, sys
sys.path[:0] = ['/work/dnt/form', '/work/fpys/tools', '/work/sephatb/tools', '/work/iostore',
                '/work/cs', '/work/tools', '/work/evil1013/tools', '/work/swap1012/tools',
                '/work/vincentfix', '/work/weap1012/tools', '/work/evilboss1016/data',
                '/work/sephforms/tools']
import build_form_data as F
import build_fpys_data as B
from iostore import Toc
from zen import Zen
import iostore_write as W
import hdr

NULL = 0xFFFFFFFFFFFFFFFF
BLOCK = F.BLOCK
MASAMUNE_PKG = '/Game/BluePrint/Character/Weapon/WE1021_00_SephirothIllusion_Masamune'
MASAMUNE_CLS = 'WE1021_00_SephirothIllusion_Masamune'
CUT_CLS = 'WE1021_10_SephirothIllusion_MasamuneCutScale'
DNT = '/Game/BluePrint/Character/Weapon/WE1021_19_DissidiaNT_Masamune/%s/' + CUT_CLS
DNT_SKIN = '/work/dnt/weapons/skin1/DissidiaNTWeapons/Content/BluePrint/Character/Weapon/WE1021_19_DissidiaNT_Masamune/%s/' + CUT_CLS + '.uasset'
CC_PKG = '/Game/BluePrint/Character/Weapon/WE1021_16_CrisisCore_Masamune/' + CUT_CLS
CC_FILE = '/work/ccsword/out1/skins/CrisisCoreWeapon/Content/BluePrint/Character/Weapon/WE1021_16_CrisisCore_Masamune/' + CUT_CLS + '.uasset'
GC_PKG = '/Game/GameContents/BluePrint/Character/Weapon/' + MASAMUNE_CLS
GC_FILE = '/data/uploads/FF7R2UProj/Saved/ModExtract/stage1027/gc_WE1021_00_bp.uasset'
# pack -> (the weapon's name, the blueprint package, its class name, its file)
TARGETS = [
    ('WE0000_00_Cloud_BusterSword', 'Buster Sword', DNT % 'WE001021_19_00', CUT_CLS, DNT_SKIN % 'WE001021_19_00'),
    ('WE0000_11_Cloud_END2Weapon1', 'Sleek Saber', DNT % 'WE001021_19_02', CUT_CLS, DNT_SKIN % 'WE001021_19_02'),
    ('WE0000_12_Cloud_END2Weapon2', 'Rune Blade', DNT % 'WE001021_19_05', CUT_CLS, DNT_SKIN % 'WE001021_19_05'),
    ('WE0000_13_Cloud_END2Weapon3', 'Umbral Blade', DNT % 'WE001021_19_03', CUT_CLS, DNT_SKIN % 'WE001021_19_03'),
    ('WE0000_14_Cloud_END2Weapon4', 'Crystal Sword', GC_PKG, MASAMUNE_CLS, GC_FILE),
    ('WE0000_15_Cloud_END2Weapon5', 'Igneous Saber', DNT % 'WE001021_19_04', CUT_CLS, DNT_SKIN % 'WE001021_19_04'),
    ('WE0000_16_Cloud_END2Weapon6', 'Slipstream Saber', CC_PKG, CUT_CLS, CC_FILE),
]


class Reader(F.Installed):
    """the installed container's chunks: from the v8 .ucas (its first bytes) or the installed build's tail"""

    def __init__(self, utoc, tail, v8_ucas):
        super().__init__(utoc, tail)
        self.v8 = open(v8_ucas, 'rb').read()

    def read(self, i):
        t = self.t
        off, ln = t.offlen[i]
        first, last = off // BLOCK, (off + ln - 1) // BLOCK
        out = bytearray()
        for bi in range(first, last + 1):
            pos, cs, us, m = t.blocks[bi]
            assert m == 0 and cs == us, 'compressed block'
            if pos + cs <= len(self.v8):
                out += self.v8[pos:pos + cs]
            else:
                assert pos >= self.tail_at, 'chunk %d (%s) is neither in the v8 .ucas nor in the tail' % (i, t.files.get(i))
                out += self.tail[pos - self.tail_at:pos - self.tail_at + cs]
        s = off - first * BLOCK
        data = bytes(out[s:s + ln])
        assert hashlib.sha1(data).digest() == self.sha(i), 'chunk %d is not what the container says' % i
        return data


def swap(data, row, new_pkg, new_cls, target_objs):
    """the pack's imports of the Masamune blueprint's objects -> the same objects of new_pkg (class name new_cls)"""
    z = Zen(data)
    table, names = {}, []
    for v in z.imports:
        if v == NULL:
            continue
        path = MASAMUNE_OBJS.get(v & ~(3 << 62))
        if not path:
            continue
        assert path.startswith(MASAMUNE_PKG + '.'), path
        to = new_pkg + '.' + path[len(MASAMUNE_PKG) + 1:].replace(MASAMUNE_CLS, new_cls)
        assert B.imp(to) & ~(3 << 62) in target_objs, (row, 'not an export of the new blueprint', to)
        table[v] = B.imp(to)
        names.append((path[len(MASAMUNE_PKG) + 1:], to[len(new_pkg) + 1:]))
    assert len(table) == 4, (row, 'names %d objects of the Masamune blueprint, not 4' % len(table))
    d = bytearray(data)
    for i, v in enumerate(z.imports):
        if v in table:
            struct.pack_into('<Q', d, z.imp_off + 8 * i, table[v])
    left = [v for v in Zen(bytes(d)).imports if v != NULL and (v & ~(3 << 62)) in MASAMUNE_OBJS]
    assert not left, (row, 'still names the Masamune blueprint')
    old_pid, new_pid = W.package_id(MASAMUNE_PKG), W.package_id(new_pkg)
    g = B.graph_entries(bytes(d))
    assert sum(1 for pid, _ in g if pid == old_pid) == 1, (row, 'the graph does not name the Masamune blueprint once')
    assert all(pid != new_pid for pid, _ in g), (row, 'the graph names the new blueprint already')
    out_g = []
    for pid, rest in g:
        if pid == old_pid:
            n = struct.unpack_from('<i', rest, 0)[0]
            arcs = list(struct.unpack_from('<%di' % (2 * n), rest, 4))
            arcs = [(-1 if k % 2 == 0 else a) for k, a in enumerate(arcs)]
            rest = struct.pack('<i', n) + struct.pack('<%di' % (2 * n), *arcs)
            pid = new_pid
        out_g.append((pid, rest))
    out_g.sort(key=lambda x: x[0])
    gb = bytearray(struct.pack('<i', len(out_g)))
    for pid, rest in out_g:
        gb += struct.pack('<Q', pid) + rest
    assert len(gb) == z.graph_size
    d[z.graph_off:z.graph_off + z.graph_size] = gb
    out = bytes(d)
    assert out[z.header_end:] == data[z.header_end:] and len(out) == len(data), (row, 'the export data changed')
    return out, names


def exports_of(path, pkg):
    data = open(path, 'rb').read()
    z = Zen(data)
    assert z.mapped(z.name_mapped) == pkg, (path, z.mapped(z.name_mapped), pkg)
    return set(B.bp_exports(data, pkg)), data


MASAMUNE_OBJS = {}


def main(utoc, tail, v8_ucas, out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    name = os.path.basename(utoc)[:-len('.utoc')]
    inst = Reader(utoc, tail, v8_ucas)
    old = inst.t
    assert [i for i in range(old.entries) if old.chunk_type(i) == 10] == [0]
    cid, store = hdr.parse_header(inst.read(0))
    assert cid == W.container_id_from_name(name), 'the container is not called ' + name
    order = [old.chunk_id64(i) for i in range(old.entries) if old.chunk_type(i) == 2]
    entries = [dict(id=p, size=store[p]['size'], export_count=store[p]['export_count'], export_bundle_count=store[p]['export_bundle_count'],
                    load_order=store[p]['load_order'], imports=list(store[p]['imports'])) for p in order]
    assert W.container_header(cid, entries) == inst.read(0), 'the header does not write back as it is'
    entry_of = {e['id']: e for e in entries}
    # the Masamune blueprint's objects (the installed one: FPYS's, wearing the Nameless)
    m_i = inst.by_path[MASAMUNE_PKG[len('/Game/'):] + '.uasset']
    MASAMUNE_OBJS.update(B.bp_exports(inst.read(m_i), MASAMUNE_PKG))
    changes, report = {}, []
    for row, weapon, pkg, cls, path in TARGETS:
        objs, bp = exports_of(path, pkg)
        i = inst.by_path[B.PACK % row]
        data = inst.read(i)
        new, names = swap(data, row, pkg, cls, objs)
        e = entry_of[old.chunk_id64(i)]
        old_pid, new_pid = W.package_id(MASAMUNE_PKG), W.package_id(pkg)
        assert old_pid in e['imports'] and new_pid not in e['imports'], (row, 'header entry')
        e['imports'] = [new_pid if x == old_pid else x for x in e['imports']]
        assert e['size'] in (0, len(data))
        changes[i] = new
        report.append('CharaSpec_%s (%s): its 4 imports of %s -> %s (%s)' % (row, weapon, MASAMUNE_CLS, pkg, ', '.join(b for a, b in names)))
    # the Umbrella keeps the Masamune
    left = []
    for row in B.WEAPON_PACKS:
        i = inst.by_path[B.PACK % row]
        if i not in changes:
            left.append(row)
    report.append('unchanged: ' + ', '.join(left))
    changes[0] = W.container_header(cid, entries)
    os.makedirs(out)
    path = os.path.join(out, name)
    tail_new = F.append(old, inst.size, changes, [], path + '.utoc', path + '.ucas.tail')
    new = Toc(path + '.utoc', ucas='/nonexistent')
    assert new.container_id == cid and new.entries == old.entries

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
        assert new.files.get(k) == old.files.get(k) and new.chunk_id64(k) == old.chunk_id64(k)
        if k in changes:
            d = new_read(k)
            assert d == changes[k] and hashlib.sha1(d).digest() == meta
        else:
            assert new.offlen[k] == old.offlen[k] and meta == inst.sha(k)
            same += 1
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
    report.append('%s: %d chunks (%d as they were; %d changed: %d weapon packs and the header); .ucas %d -> %d bytes' % (
        name, new.entries, same, len(changes), len(changes) - 1, inst.size, inst.size + len(tail_new)))
    open(os.path.join(out, 'report.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))
    print(json.dumps(sums))


if __name__ == '__main__':
    main(*sys.argv[1:5])
