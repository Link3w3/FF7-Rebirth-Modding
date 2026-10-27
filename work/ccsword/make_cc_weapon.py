"""The CRISIS CORE skins' weapon blueprint: the game's playable (cut-scale) Masamune blueprint copied to
/Game/BluePrint/Character/Weapon/WE1021_16_CrisisCore_Masamune/WE1021_10_SephirothIllusion_MasamuneCutScale (class name and
parent kept) and pointed at Reunion's Masamune (/Game/Character/Weapon/WE1021_16_CrisisCore_Masamune/Model/WE001021_16,
cooked into the CRISIS CORE skins by the editor's skin build), as the skin folder CrisisCoreWeapon ("part": true: nobody
wears it; its package goes into the skins container for those skins' weapon). As make_seraph_weapon.py and
make_weapon_part.py did for Seraph Sephiroth's Essence Shard.
    make_cc_weapon.py <out dir> <skin folder>"""
import json, os, shutil, sys, time
sys.path[:0] = ['/work/anime1025/masamune', '/work/iostore', '/work/cs', '/work/weap1012/tools',
                '/work/fpys/tools', '/work/evilboss1016/data', '/work/swap1012/tools']
import make_anime_masamune as mam
import hdr

BP_NEW = '/Game/BluePrint/Character/Weapon/WE1021_16_CrisisCore_Masamune/WE1021_10_SephirothIllusion_MasamuneCutScale'
MESH_OLD = mam.MESH_OLD + '.' + mam.MESH_OBJ
MESH_NEW = '/Game/Character/Weapon/WE1021_16_CrisisCore_Masamune/Model/WE001021_16.WE001021_16'
src = open('/work/anime1025/masamune/make_part_skin.py').read()
exec(src[src.index('def q('):src.index('entries = json.load')])


def main(out_dir, skin_dir):
    _, retail = hdr.parse_header(open(mam.RETAIL_HEADER, 'rb').read())
    bp, entry, bz = mam.copy_package(open(mam.SRC_BP, 'rb').read(), mam.BP_OLD, BP_NEW, {mam.BP_OLD: BP_NEW}, {MESH_OLD: MESH_NEW}, retail)
    rel = 'Content/' + BP_NEW[len('/Game/'):] + '.uasset'
    os.makedirs(os.path.dirname(os.path.join(out_dir, rel)), exist_ok=True)
    open(os.path.join(out_dir, rel), 'wb').write(bp)
    e = dict(package=entry['package'], file=rel, size=entry['size'], export_count=entry['export_count'],
             export_bundle_count=entry['export_bundle_count'], load_order=entry['load_order'], imports=entry['imports'], bulk=[])
    json.dump([e], open(os.path.join(out_dir, 'store_entries.json'), 'w'), indent=1)
    skin = dict(name='Crisis Core Masamune', author='',
                description="Crisis Core Reunion's Masamune: the game's playable (cut-scale) Masamune blueprint holding Reunion's own "
                            "sword (its model, cooked into the Crisis Core Sephiroth skins). Its package only: the weapon of the "
                            "Crisis Core Sephiroth skins.",
                characters=[], model='', skeleton='', family='', voice='', weapon='', worn=False, part=True,
                packages=[e], built=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                built_with="make_cc_weapon.py (the game's package copied to a new path)")
    if os.path.isdir(skin_dir):
        shutil.rmtree(skin_dir)
    os.makedirs(os.path.dirname(os.path.join(skin_dir, rel)), exist_ok=True)
    shutil.copyfile(os.path.join(out_dir, rel), os.path.join(skin_dir, rel))
    open(os.path.join(skin_dir, 'skin.json'), 'w', newline='\n').write(write_skin_json(skin))
    print(json.dumps(e, indent=1))
    print('imports', [hex(int(i, 16)) if isinstance(i, str) else hex(i) for i in e['imports']])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
