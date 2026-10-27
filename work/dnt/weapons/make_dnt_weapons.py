"""Dissidia NT's Masamunes' weapon blueprints: the game's playable (cut-scale) Masamune blueprint copied once per sword to
/Game/BluePrint/Character/Weapon/WE1021_19_DissidiaNT_Masamune/<sword>/WE1021_10_SephirothIllusion_MasamuneCutScale (class
name and parent kept: the game's WE1021_00 Masamune) and pointed at that sword's model
(/Game/Character/Weapon/WE1021_19_DissidiaNT_Masamune/Model/<sword>, cooked into the Dissidia NT skins by the editor's skin
build: dnt_import.py's _skin_assets), as make_cc_weapon.py did for Crisis Core's. All five go in the skin folder
DissidiaNTWeapons ("part": true: nobody wears it; its packages go into the skins container for Cloud's weapon packs of the
Fully Playable Young Sephiroth's data, which name these blueprints).
    make_dnt_weapons.py <out dir> <skin folder>"""
import json, os, shutil, sys, time
sys.path[:0] = ['/work/anime1025/masamune', '/work/iostore', '/work/cs', '/work/weap1012/tools',
                '/work/fpys/tools', '/work/evilboss1016/data', '/work/swap1012/tools']
import make_anime_masamune as mam
import hdr

SWORDS = ['WE001021_19_00', 'WE001021_19_02', 'WE001021_19_03', 'WE001021_19_04', 'WE001021_19_05']
BP_FOLDER = '/Game/BluePrint/Character/Weapon/WE1021_19_DissidiaNT_Masamune/'
BP_NAME = 'WE1021_10_SephirothIllusion_MasamuneCutScale'
MESH_ROOT = '/Game/Character/Weapon/WE1021_19_DissidiaNT_Masamune/Model/'
MESH_OLD = mam.MESH_OLD + '.' + mam.MESH_OBJ
src = open('/work/anime1025/masamune/make_part_skin.py').read()
exec(src[src.index('def q('):src.index('entries = json.load')])


def bp_of(sword):
    return BP_FOLDER + sword + '/' + BP_NAME


def main(out_dir, skin_dir):
    _, retail = hdr.parse_header(open(mam.RETAIL_HEADER, 'rb').read())
    src_bp = open(mam.SRC_BP, 'rb').read()
    entries = []
    for sword in SWORDS:
        new = bp_of(sword)
        mesh_new = MESH_ROOT + sword + '.' + sword
        bp, entry, bz = mam.copy_package(src_bp, mam.BP_OLD, new, {mam.BP_OLD: new}, {MESH_OLD: mesh_new}, retail)
        rel = 'Content/' + new[len('/Game/'):] + '.uasset'
        os.makedirs(os.path.dirname(os.path.join(out_dir, rel)), exist_ok=True)
        open(os.path.join(out_dir, rel), 'wb').write(bp)
        entries.append(dict(package=entry['package'], file=rel, size=entry['size'], export_count=entry['export_count'],
                            export_bundle_count=entry['export_bundle_count'], load_order=entry['load_order'],
                            imports=entry['imports'], bulk=[]))
    json.dump(entries, open(os.path.join(out_dir, 'store_entries.json'), 'w'), indent=1)
    skin = dict(name='Dissidia NT Masamunes', author='',
                description="Dissidia NT's five Masamunes (w_sev200_00 and its 2p1c-5p1c looks, at Rebirth's 2.38 m): the "
                            "game's playable (cut-scale) Masamune blueprint once per sword, each holding its sword (the "
                            "models are cooked into the Dissidia NT skins). Their packages only: the weapons Cloud's weapon "
                            "packs name in the Fully Playable Young Sephiroth's data.",
                characters=[], model='', skeleton='', family='', voice='', weapon='', worn=False, part=True,
                packages=entries, built=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                built_with="make_dnt_weapons.py (the game's package copied to new paths)")
    if os.path.isdir(skin_dir):
        shutil.rmtree(skin_dir)
    for e in entries:
        os.makedirs(os.path.dirname(os.path.join(skin_dir, e['file'])), exist_ok=True)
        shutil.copyfile(os.path.join(out_dir, e['file']), os.path.join(skin_dir, e['file']))
    open(os.path.join(skin_dir, 'skin.json'), 'w', newline='\n').write(write_skin_json(skin))
    for e in entries:
        print(e['package'], e['size'], e['export_count'], e['export_bundle_count'], e['load_order'], e['imports'])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
