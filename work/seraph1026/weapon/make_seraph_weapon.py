"""Seraph Sephiroth's weapon for Rebirth: the game's playable (cut-scale) Masamune blueprint copied to a path of its own
and pointed at the Essence Shard (the user's /Game/Character/Weapon/WE1021_15_Essence_Shard/Model/WE001021_15: the
Masamune's bones and sockets, cooked into the Seraph Sephiroth skins by the editor's skin build).

  blueprint: /Game/BluePrint/Character/Weapon/WE1021_10_SephirothIllusion_MasamuneCutScale copied to
        /Game/BluePrint/Character/Weapon/WE1021_15_Essence_Shard/WE1021_10_SephirothIllusion_MasamuneCutScale (the class
        keeps its name, WE1021_10_SephirothIllusion_MasamuneCutScale_C, and its parent, the game's WE1021_00 Masamune), its
        mesh's import pointed at the Essence Shard
Every other byte is the game's (the export data unchanged). Writes <out>/Content/... and <out>/store_entries.json.
    make_seraph_weapon.py <out dir>"""
import json, os, sys
sys.path[:0] = ['/work/anime1025/masamune', '/work/iostore', '/work/cs', '/work/weap1012/tools',
                '/work/fpys/tools', '/work/evilboss1016/data', '/work/swap1012/tools']
import make_anime_masamune as mam
import hdr

SRC_BP = mam.SRC_BP
BP_OLD = mam.BP_OLD
BP_NEW = '/Game/BluePrint/Character/Weapon/WE1021_15_Essence_Shard/WE1021_10_SephirothIllusion_MasamuneCutScale'
MESH_OLD = mam.MESH_OLD + '.' + mam.MESH_OBJ
MESH_NEW = '/Game/Character/Weapon/WE1021_15_Essence_Shard/Model/WE001021_15.WE001021_15'


def main(out_dir):
    _, retail = hdr.parse_header(open(mam.RETAIL_HEADER, 'rb').read())
    bp, entry, bz = mam.copy_package(open(SRC_BP, 'rb').read(), BP_OLD, BP_NEW, {BP_OLD: BP_NEW}, {MESH_OLD: MESH_NEW}, retail)
    rel = 'Content/' + BP_NEW[len('/Game/'):] + '.uasset'
    path = os.path.join(out_dir, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(bp)
    e = dict(package=entry['package'], file=rel, size=entry['size'], export_count=entry['export_count'],
             export_bundle_count=entry['export_bundle_count'], load_order=entry['load_order'], imports=entry['imports'], bulk=[])
    json.dump([e], open(os.path.join(out_dir, 'store_entries.json'), 'w'), indent=1)
    print(json.dumps(e, indent=1))
    print('names:', bz.names[:3])


if __name__ == '__main__':
    main(sys.argv[1])
